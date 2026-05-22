import json
import math
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Artist, ArtistCluster, ArtistEmbedding, CanvasMove, Cluster,
    Festival, LineupSlot, RecFeedback, SimilarityEdge,
    TasteEdge, TasteSelection, TasteSession,
)
from .similarity.explanations import ExplanationGenerator
from .similarity.taste import TasteGraphBuilder


class JSONBodyView(View):
    """Base view that parses JSON request body."""

    def parse_body(self, request):
        if request.method == 'POST':
            return json.loads(request.body)
        return request.GET.dict()


class FestivalListAPI(View):
    def get(self, request):
        festivals = Festival.objects.filter(is_active=True)
        data = []
        for f in festivals:
            artist_count = LineupSlot.objects.filter(
                festival=f, status='confirmed'
            ).values('artist').distinct().count()
            data.append({
                'id': f.id,
                'name': f.name,
                'slug': f.slug,
                'start_date': f.start_date.isoformat(),
                'end_date': f.end_date.isoformat(),
                'location': f.location,
                'artist_count': artist_count,
            })
        return JsonResponse(data, safe=False)


class FestivalLineupAPI(View):
    def get(self, request, pk):
        try:
            festival = Festival.objects.get(pk=pk)
        except Festival.DoesNotExist:
            return JsonResponse({'error': 'Festival not found'}, status=404)

        slots = LineupSlot.objects.filter(
            festival=festival
        ).select_related('artist').order_by('day', 'start_time', 'position')

        days = {}
        for slot in slots:
            day_key = slot.day or 0
            if day_key not in days:
                days[day_key] = {'day': day_key, 'stages': {}}
            stage = slot.stage or 'Main'
            if stage not in days[day_key]['stages']:
                days[day_key]['stages'][stage] = []
            days[day_key]['stages'][stage].append({
                'slot_id': slot.id,
                'artist': {
                    'id': slot.artist.id,
                    'name': slot.artist.canonical_name or slot.artist.name,
                    'genre_tags': slot.artist.genre_tags,
                    'image_url': slot.artist.image_url,
                },
                'start_time': slot.start_time.isoformat() if slot.start_time else None,
                'end_time': slot.end_time.isoformat() if slot.end_time else None,
                'slot_name': slot.slot_name,
                'status': slot.status,
            })

        response = {
            'festival': {
                'id': festival.id,
                'name': festival.name,
                'slug': festival.slug,
                'start_date': festival.start_date.isoformat(),
                'end_date': festival.end_date.isoformat(),
                'location': festival.location,
            },
            'days': [
                {'day': k, 'stages': v['stages']}
                for k, v in sorted(days.items())
            ],
        }
        return JsonResponse(response)


@method_decorator(csrf_exempt, name='dispatch')
class RecommendationsAPI(JSONBodyView):
    def post(self, request):
        body = self.parse_body(request)
        festival_id = body.get('festival_id')
        liked_ids = body.get('liked_artist_ids', [])
        max_results = body.get('max_results', 10)

        if not liked_ids:
            return JsonResponse({'recommendations': []})

        liked_artists = list(Artist.objects.filter(id__in=liked_ids))

        # Compute taste centroid from liked artist embeddings
        centroid = None
        liked_embs = ArtistEmbedding.objects.filter(artist_id__in=liked_ids)
        if liked_embs.exists():
            vectors = [e.vector for e in liked_embs]
            centroid = [sum(vals) / len(vals) for vals in zip(*vectors)]

        candidate_ids = LineupSlot.objects.filter(
            festival_id=festival_id,
            status='confirmed',
        ).exclude(
            artist_id__in=liked_ids
        ).values_list('artist_id', flat=True).distinct()

        candidates = LineupSlot.objects.filter(
            artist_id__in=candidate_ids,
            festival_id=festival_id,
            status='confirmed',
        ).select_related('artist')

        recs = {}
        for slot in candidates:
            artist = slot.artist
            if artist.id in recs:
                continue

            # Edge-based score
            edge_scores = []
            for liked_id in liked_ids:
                edge = SimilarityEdge.objects.filter(
                    Q(artist_a_id=liked_id, artist_b_id=artist.id)
                    | Q(artist_a_id=artist.id, artist_b_id=liked_id),
                    is_active=True,
                ).first()
                if edge and edge.final_score > 0.15:
                    edge_scores.append(edge.final_score)

            if not edge_scores:
                continue

            avg_edge_score = sum(edge_scores) / len(edge_scores)

            # Centroid similarity
            centroid_sim = 0.0
            if centroid:
                try:
                    emb = artist.embedding
                    centroid_sim = self._cosine(emb.vector, centroid)
                except Exception:
                    centroid_sim = 0.0

            # Cultural affinity
            cultural = self._cultural_affinity_score(liked_ids, artist.id, festival_id)

            # Combined score
            final_score = (
                avg_edge_score * 0.6
                + centroid_sim * 0.25
                + cultural * 0.15
            )

            # Generate explanation
            liked_artist_names = [a.canonical_name or a.name for a in liked_artists]
            expl_gen = ExplanationGenerator()
            explanation = expl_gen.generate(artist, liked_artists)

            recs[artist.id] = {
                'artist': {
                    'id': artist.id,
                    'name': artist.canonical_name or artist.name,
                    'genre_tags': artist.genre_tags,
                },
                'score': round(final_score, 2),
                'reason': explanation,
                'festival_info': {
                    'stage': slot.stage,
                    'day': slot.day,
                    'start_time': slot.start_time.isoformat() if slot.start_time else None,
                },
            }

        sorted_recs = sorted(recs.values(), key=lambda r: r['score'], reverse=True)
        return JsonResponse({'recommendations': sorted_recs[:max_results]})

    def _cosine(self, v1, v2):
        if not v1 or not v2:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def _cultural_affinity_score(self, liked_ids, candidate_id, festival_id):
        scores = []
        for liked_id in liked_ids:
            edge = TasteEdge.objects.filter(
                source_artist_id=liked_id,
                target_artist_id=candidate_id,
                festival_id=festival_id,
            ).first()
            if edge and edge.confidence > 0.3:
                scores.append(edge.smoothed_lift)
        if not scores:
            for liked_id in liked_ids:
                edge = TasteEdge.objects.filter(
                    source_artist_id=liked_id,
                    target_artist_id=candidate_id,
                    festival__isnull=True,
                ).first()
                if edge and edge.confidence > 0.3:
                    scores.append(edge.smoothed_lift)
        if not scores:
            return 0.0
        return min(sum(scores) / len(scores) / 5.0, 1.0)


@method_decorator(csrf_exempt, name='dispatch')
class TasteLikeAPI(JSONBodyView):
    def post(self, request):
        body = self.parse_body(request)
        session_id = body.get('session_id')
        festival_id = body.get('festival_id')
        artist_id = body.get('artist_id')

        if not all([session_id, festival_id, artist_id]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        try:
            session = TasteSession.objects.get(
                session_id=session_id, festival_id=festival_id
            )
        except TasteSession.DoesNotExist:
            session = TasteSession.objects.create(
                session_id=session_id, festival_id=festival_id
            )

        TasteSelection.objects.get_or_create(
            session=session, artist_id=artist_id
        )

        return JsonResponse({'status': 'ok'})


@method_decorator(csrf_exempt, name='dispatch')
class TasteUnlikeAPI(JSONBodyView):
    def post(self, request):
        body = self.parse_body(request)
        session_id = body.get('session_id')
        festival_id = body.get('festival_id')
        artist_id = body.get('artist_id')

        if not all([session_id, festival_id, artist_id]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        deleted, _ = TasteSelection.objects.filter(
            session__session_id=session_id,
            session__festival_id=festival_id,
            artist_id=artist_id,
        ).delete()

        return JsonResponse({'status': 'ok', 'deleted': deleted})


@method_decorator(csrf_exempt, name='dispatch')
class TasteResetAPI(JSONBodyView):
    def post(self, request):
        body = self.parse_body(request)
        session_id = body.get('session_id')

        if not session_id:
            return JsonResponse({'error': 'Missing session_id'}, status=400)

        # Delete all taste data for this session
        sessions = TasteSession.objects.filter(session_id=session_id)
        for s in sessions:
            s.selections.all().delete()
            s.feedback.all().delete()
        sessions.delete()

        return JsonResponse({'status': 'ok'})


@method_decorator(csrf_exempt, name='dispatch')
class FeedbackAPI(JSONBodyView):
    def post(self, request):
        body = self.parse_body(request)
        session_id = body.get('session_id')
        festival_id = body.get('festival_id')
        recommended_artist_id = body.get('recommended_artist_id')
        liked_artist_ids = body.get('liked_artist_ids', [])
        feedback = body.get('feedback')

        if not all([session_id, festival_id, recommended_artist_id, feedback]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        try:
            session = TasteSession.objects.get(
                session_id=session_id, festival_id=festival_id
            )
        except TasteSession.DoesNotExist:
            session = TasteSession.objects.create(
                session_id=session_id, festival_id=festival_id
            )

        RecFeedback.objects.create(
            session=session,
            recommended_artist_id=recommended_artist_id,
            liked_artists=liked_artist_ids,
            feedback=feedback,
        )

        return JsonResponse({'status': 'ok'})


# ── Admin Canvas API ──

@method_decorator(staff_member_required, name='dispatch')
class CanvasDataAPI(View):
    def get(self, request):
        festival_id = request.GET.get('festival_id')
        cluster_id = request.GET.get('cluster_id')
        unplaced_only = request.GET.get('unplaced_only')
        query = request.GET.get('q')
        limit = int(request.GET.get('limit', 500))
        min_edge_score = float(request.GET.get('min_edge_score', 0.2))

        artists = Artist.objects.filter(is_active=True)
        if query:
            artists = artists.filter(canonical_name__icontains=query)
        if festival_id:
            artists = artists.filter(lineup_slots__festival_id=festival_id)
        if cluster_id:
            artists = artists.filter(cluster_memberships__cluster_id=cluster_id)
        if unplaced_only == 'true':
            artists = artists.filter(canvas_status='unplaced')

        artists = artists[:limit]

        nodes = []
        for a in artists:
            nodes.append({
                'id': a.id,
                'label': a.canonical_name or a.name,
                'x': a.canvas_x,
                'y': a.canvas_y,
                'group': a.canvas_status,
                'size': 12 + min(a.lineup_slots.count() * 2, 18),
                'color': self._node_color(a),
                'title': f"{a.canonical_name or a.name}<br>{', '.join(a.genre_tags[:5])}",
                'canvas_status': a.canvas_status,
                'is_anchor': a.is_anchor,
                'festivals_count': a.lineup_slots.values('festival').distinct().count(),
            })

        artist_ids = [a.id for a in artists]
        edges_data = SimilarityEdge.objects.filter(
            Q(artist_a_id__in=artist_ids, artist_b_id__in=artist_ids),
            is_active=True,
            final_score__gte=min_edge_score,
        )[:limit * 5]

        edges = []
        for e in edges_data:
            edges.append({
                'from': e.artist_a_id,
                'to': e.artist_b_id,
                'value': e.final_score,
                'color': self._edge_color(e),
                'dashes': e.final_score < 0.3,
                'title': f"Score: {e.final_score:.2f}<br>{e.explanation or ''}",
            })

        clusters_data = Cluster.objects.all()
        clusters = []
        for c in clusters_data:
            members = list(c.members.values_list('artist_id', flat=True))
            if members:
                clusters.append({
                    'id': c.id,
                    'label': c.name,
                    'nodes': members,
                    'color': c.color,
                })

        return JsonResponse({
            'nodes': nodes,
            'edges': edges,
            'clusters': clusters,
        })

    def _node_color(self, artist):
        if artist.is_anchor:
            return '#ffd700'
        if artist.canvas_status == 'locked':
            return '#dc3545'
        if artist.canvas_status == 'manual':
            return '#417690'
        if artist.canvas_status == 'auto':
            return '#6c757d'
        return '#adb5bd'

    def _edge_color(self, edge):
        if edge.manual_score and edge.manual_score > 0:
            return '#ff8c00'
        if edge.cultural_affinity_score and edge.cultural_affinity_score > 0:
            return '#28a745'
        if edge.final_score > 0.6:
            return '#417690'
        if edge.final_score > 0.3:
            return '#6c757d'
        return '#ced4da'


@method_decorator(staff_member_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class CanvasMoveAPI(JSONBodyView):
    def post(self, request):
        body = self.parse_body(request)
        artist_id = body.get('artist_id')
        x = float(body.get('x', 0))
        y = float(body.get('y', 0))

        artist = get_object_or_404(Artist, id=artist_id)
        old_x, old_y = artist.canvas_x, artist.canvas_y

        artist.canvas_x = max(-1.0, min(1.0, x))
        artist.canvas_y = max(-1.0, min(1.0, y))
        artist.canvas_status = 'manual'
        artist.save()

        CanvasMove.objects.create(
            artist=artist,
            old_x=old_x, old_y=old_y,
            new_x=artist.canvas_x, new_y=artist.canvas_y,
            admin_user=request.user,
        )

        affected = []
        for edge in SimilarityEdge.objects.filter(
            Q(artist_a=artist) | Q(artist_b=artist),
            is_active=True,
        ):
            other = edge.artist_b if edge.artist_a == artist else edge.artist_a
            dx = artist.canvas_x - other.canvas_x
            dy = artist.canvas_y - other.canvas_y
            distance = math.sqrt(dx * dx + dy * dy)
            edge.canvas_score = 1.0 / (1.0 + distance * 3.0)
            edge.save()
            affected.append({
                'from': edge.artist_a_id,
                'to': edge.artist_b_id,
                'new_canvas_score': edge.canvas_score,
            })

        return JsonResponse({'status': 'ok', 'updated_edges': affected})


@method_decorator(staff_member_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class CanvasEdgeAPI(JSONBodyView):
    def post(self, request):
        body = self.parse_body(request)
        a_id = int(body['artist_a_id'])
        b_id = int(body['artist_b_id'])
        score = float(body.get('score', 0))
        explanation = body.get('explanation', '')

        edge, _ = SimilarityEdge.objects.update_or_create(
            artist_a_id=min(a_id, b_id),
            artist_b_id=max(a_id, b_id),
            defaults={
                'manual_score': score,
                'final_score': score,
                'is_locked': True,
                'explanation': explanation,
            },
        )
        return JsonResponse({'status': 'ok', 'edge_id': edge.id})

    def delete(self, request):
        body = json.loads(request.body)
        a_id = int(body['artist_a_id'])
        b_id = int(body['artist_b_id'])
        edge = SimilarityEdge.objects.filter(
            artist_a_id=min(a_id, b_id),
            artist_b_id=max(a_id, b_id),
        ).first()
        if edge:
            edge.is_active = False
            edge.save()
        return JsonResponse({'status': 'ok'})


@method_decorator(staff_member_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class CanvasAutoLayoutAPI(View):
    def post(self, request):
        artists = Artist.objects.filter(
            canvas_status__in=['unplaced', 'auto'],
            is_active=True,
        )
        body = json.loads(request.body) if request.body else {}
        artist_ids = body.get('artist_ids')
        if artist_ids:
            artists = artists.filter(id__in=artist_ids)

        moves = []
        for artist in artists:
            if artist.canvas_status in ('manual', 'locked'):
                continue
            # Simple force-directed: place randomly
            import random
            artist.canvas_x = random.uniform(-0.8, 0.8)
            artist.canvas_y = random.uniform(-0.8, 0.8)
            artist.canvas_status = 'auto'
            artist.save()
            moves.append({
                'artist_id': artist.id,
                'new_x': artist.canvas_x,
                'new_y': artist.canvas_y,
            })

        return JsonResponse({'status': 'ok', 'moves': moves})


@method_decorator(staff_member_required, name='dispatch')
class CanvasNeighborsAPI(View):
    def get(self, request, pk):
        artist = get_object_or_404(Artist, id=pk)
        radius = float(request.GET.get('radius', 0.5))

        neighbors = []
        for other in Artist.objects.exclude(id=pk):
            dx = artist.canvas_x - other.canvas_x
            dy = artist.canvas_y - other.canvas_y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance <= radius:
                edge = SimilarityEdge.objects.filter(
                    Q(artist_a=artist, artist_b=other) | Q(artist_a=other, artist_b=artist),
                    is_active=True,
                ).first()
                neighbors.append({
                    'artist': {
                        'id': other.id,
                        'name': other.canonical_name or other.name,
                    },
                    'distance': round(distance, 3),
                    'edge_score': edge.final_score if edge else None,
                })

        neighbors.sort(key=lambda n: n['distance'])
        return JsonResponse({'artist_id': pk, 'neighbors': neighbors})


@method_decorator(staff_member_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class CanvasUndoAPI(View):
    def post(self, request):
        last_move = CanvasMove.objects.filter(
            admin_user=request.user
        ).first()
        if not last_move:
            return JsonResponse({'error': 'Nothing to undo'}, status=404)

        artist = last_move.artist
        artist.canvas_x = last_move.old_x
        artist.canvas_y = last_move.old_y
        artist.save()
        last_move.delete()

        return JsonResponse({'status': 'ok', 'reverted_artist_id': artist.id})
