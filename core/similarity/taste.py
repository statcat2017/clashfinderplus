import math
from collections import Counter, defaultdict

from django.db.models import Count

from ..models import Artist, Festival, RecFeedback, SimilarityEdge, TasteEdge, TasteSelection, TasteSession


class TasteGraphBuilder:
    MIN_SAMPLES = 10
    CONFIDENCE_CURVE_SHARPNESS = 20

    def update_all_edges(self, festival=None):
        if festival:
            sessions = TasteSession.objects.filter(festival=festival)
        else:
            sessions = TasteSession.objects.all()

        counts = defaultdict(lambda: defaultdict(int))
        session_artist_map = defaultdict(set)

        for session in sessions.select_related('festival'):
            artist_ids = list(
                session.selections.values_list('artist_id', flat=True)
            )
            for a_id in artist_ids:
                session_artist_map[session.id].add(a_id)

        total_sessions = sessions.count()
        artist_freq = Counter()
        for artists in session_artist_map.values():
            for a_id in artists:
                artist_freq[a_id] += 1

        for session_id, artists in session_artist_map.items():
            artist_list = list(artists)
            for i in range(len(artist_list)):
                for j in range(i + 1, len(artist_list)):
                    a, b = artist_list[i], artist_list[j]
                    counts[a][b] += 1
                    counts[b][a] += 1

        edges_created = 0
        for a_id, targets in counts.items():
            for b_id, co_count in targets.items():
                if co_count < self.MIN_SAMPLES:
                    continue
                sessions_with_a = artist_freq.get(a_id, 0)
                sessions_with_b = artist_freq.get(b_id, 0)
                if sessions_with_a == 0 or sessions_with_b == 0:
                    continue

                p_b = sessions_with_b / total_sessions if total_sessions > 0 else 0
                p_b_given_a = co_count / sessions_with_a
                raw_lift = p_b_given_a / p_b if p_b > 0 else 1.0

                confidence = co_count / (co_count + self.CONFIDENCE_CURVE_SHARPNESS)
                smoothed_lift = 1.0 + ((raw_lift - 1.0) * confidence)

                TasteEdge.objects.update_or_create(
                    source_artist_id=a_id,
                    target_artist_id=b_id,
                    festival=festival,
                    defaults={
                        'raw_lift': raw_lift,
                        'smoothed_lift': smoothed_lift,
                        'confidence': confidence,
                        'sample_size': co_count,
                    },
                )

                cultural_score = min(smoothed_lift / 5.0, 1.0)
                a, b = min(a_id, b_id), max(a_id, b_id)
                edge = SimilarityEdge.objects.filter(
                    artist_a_id=a, artist_b_id=b
                ).first()
                if edge:
                    edge.cultural_affinity_score = cultural_score
                    self._recompute_final_score(edge)
                    edge.save()
                edges_created += 1

        return edges_created

    def update_edges_for_artist(self, artist):
        return self.update_all_edges()

    def _compute_lift(self, a_id, b_id, festival_id=None):
        if festival_id:
            sessions_with_a = TasteSession.objects.filter(
                festival_id=festival_id,
                selections__artist_id=a_id,
            ).distinct().count()
            sessions_with_b = TasteSession.objects.filter(
                festival_id=festival_id,
                selections__artist_id=b_id,
            ).distinct().count()
            sessions_with_both = TasteSession.objects.filter(
                festival_id=festival_id,
                selections__artist_id=a_id,
            ).filter(
                selections__artist_id=b_id,
            ).distinct().count()
            total = TasteSession.objects.filter(
                festival_id=festival_id
            ).count()
        else:
            sessions_with_a = TasteSelection.objects.filter(
                artist_id=a_id
            ).values('session').distinct().count()
            sessions_with_b = TasteSelection.objects.filter(
                artist_id=b_id
            ).values('session').distinct().count()
            sessions_with_both = TasteSelection.objects.filter(
                artist_id=a_id
            ).filter(
                artist_id=b_id
            ).values('session').distinct().count()
            total = TasteSession.objects.count()

        if sessions_with_a == 0 or sessions_with_b == 0 or total == 0:
            return {'raw_lift': 1.0, 'confidence': 0.0, 'smoothed_lift': 1.0}

        p_b = sessions_with_b / total
        p_b_given_a = sessions_with_both / sessions_with_a
        raw_lift = p_b_given_a / p_b if p_b > 0 else 1.0
        confidence = sessions_with_both / (sessions_with_both + self.CONFIDENCE_CURVE_SHARPNESS)
        smoothed_lift = 1.0 + ((raw_lift - 1.0) * confidence)

        return {
            'raw_lift': raw_lift,
            'confidence': confidence,
            'smoothed_lift': smoothed_lift,
        }

    def _recompute_final_score(self, edge):
        weights = {
            'manual_score': 0.30,
            'canvas_score': 0.20,
            'tag_score': 0.20,
            'cultural_affinity_score': 0.15,
            'cooccurrence_score': 0.10,
            'audio_score': 0.05,
        }
        if edge.is_locked:
            return

        total_weight = 0.0
        weighted_sum = 0.0
        for field, weight in weights.items():
            val = getattr(edge, field, None)
            if val is not None:
                weighted_sum += val * weight
                total_weight += weight
        edge.final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
