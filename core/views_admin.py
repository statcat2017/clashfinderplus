import json

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from .lineup_importers.clashfinder_api import ClashfinderAPIImporter
from .lineup_importers.clashfinder_html import ClashfinderHTMLImporter
from .lineup_importers.csv_importer import CSVImporter
from .lineup_importers.matcher import ArtistMatcher
from .models import Artist, ArtistAlias, Festival, RecFeedback, TasteEdge, TasteSelection, TasteSession, ScrapeLog


@method_decorator(staff_member_required, name='dispatch')
class ImportDashboardView(TemplateView):
    template_name = 'admin/import_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['festivals'] = Festival.objects.all().order_by('-start_date')
        context['scrape_logs'] = ScrapeLog.objects.select_related('festival')[:50]
        return context


@method_decorator(staff_member_required, name='dispatch')
class ImportRunView(View):
    def post(self, request):
        festival_id = request.POST.get('festival_id')
        importer_type = request.POST.get('importer_type', 'clashfinder_html')
        festival = get_object_or_404(Festival, id=festival_id)

        try:
            if importer_type == 'clashfinder_api':
                importer = ClashfinderAPIImporter(
                    festival,
                    request.POST.get('username', ''),
                    request.POST.get('public_key', ''),
                )
            elif importer_type == 'csv':
                csv_file = request.FILES.get('csv_file')
                if not csv_file:
                    return JsonResponse({'error': 'CSV file required'}, status=400)
                importer = CSVImporter(festival, csv_file)
            else:
                importer = ClashfinderHTMLImporter(festival)

            log = importer.import_lineup()
            return JsonResponse({
                'status': log.status,
                'artists_found': log.artists_found,
                'artists_new': log.artists_new,
                'artists_updated': log.artists_updated,
                'errors': log.errors,
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(staff_member_required, name='dispatch')
class DedupView(TemplateView):
    template_name = 'admin/dedup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        matcher = ArtistMatcher()
        duplicates = []
        for artist in Artist.objects.filter(marked_for_merge=False)[:100]:
            matches = matcher.find_duplicates(artist)
            if matches:
                duplicates.append({'artist': artist, 'matches': matches})
        context['duplicates'] = duplicates[:50]
        return context


@method_decorator(staff_member_required, name='dispatch')
class MergeArtistsView(View):
    def post(self, request):
        source_id = request.POST.get('source_id')
        target_id = request.POST.get('target_id')
        source = get_object_or_404(Artist, id=source_id)
        target = get_object_or_404(Artist, id=target_id)

        matcher = ArtistMatcher()
        matcher.merge_artists(source, target)
        return JsonResponse({'status': 'ok', 'target_id': target.id})


@method_decorator(staff_member_required, name='dispatch')
class TagEditorView(TemplateView):
    template_name = 'admin/tag_editor.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        if query:
            context['artists'] = Artist.objects.filter(
                canonical_name__icontains=query
            )[:50]
        else:
            context['artists'] = Artist.objects.all()[:50]
        all_tags = set()
        for a in Artist.objects.exclude(genre_tags=[]):
            all_tags.update(a.genre_tags)
        context['all_tags'] = sorted(all_tags)
        return context


@method_decorator(staff_member_required, name='dispatch')
class TagUpdateView(View):
    def post(self, request):
        artist_id = request.POST.get('artist_id')
        tags_json = request.POST.get('tags', '[]')
        artist = get_object_or_404(Artist, id=artist_id)
        artist.genre_tags = json.loads(tags_json)
        artist.save()
        return JsonResponse({'status': 'ok'})


@method_decorator(staff_member_required, name='dispatch')
class BulkTagView(View):
    def post(self, request):
        artist_ids = request.POST.getlist('artist_ids')
        tag = request.POST.get('tag')
        if not tag:
            return JsonResponse({'error': 'Tag required'}, status=400)
        count = 0
        for artist in Artist.objects.filter(id__in=artist_ids):
            if tag not in artist.genre_tags:
                artist.genre_tags = artist.genre_tags + [tag]
                artist.save()
                count += 1
        return JsonResponse({'status': 'ok', 'updated': count})


@method_decorator(staff_member_required, name='dispatch')
class TasteDashboardView(TemplateView):
    template_name = 'admin/taste_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        total_sessions = TasteSession.objects.count()
        total_selections = TasteSelection.objects.count()
        total_edges = TasteEdge.objects.count()

        # Top cultural affinity edges
        top_edges = TasteEdge.objects.select_related(
            'source_artist', 'target_artist'
        ).order_by('-smoothed_lift')[:10]

        # Top co-selected pairs
        top_co = TasteEdge.objects.select_related(
            'source_artist', 'target_artist'
        ).order_by('-sample_size')[:10]

        # Session growth (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        session_growth = TasteSession.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()

        # Feedback summary
        feedback_counts = RecFeedback.objects.values('feedback').annotate(
            count=Count('id')
        )

        context.update({
            'total_sessions': total_sessions,
            'total_selections': total_selections,
            'total_edges': total_edges,
            'top_edges': top_edges,
            'top_co': top_co,
            'session_growth_30d': session_growth,
            'feedback_counts': {f['feedback']: f['count'] for f in feedback_counts},
        })
        return context


@method_decorator(staff_member_required, name='dispatch')
class CanvasAdminView(TemplateView):
    template_name = 'admin/canvas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['festivals'] = Festival.objects.filter(is_active=True)
        return context
