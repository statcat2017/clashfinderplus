import json

from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from .models import Artist, Festival, LineupSlot


class HomeView(TemplateView):
    template_name = 'public/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        festivals = Festival.objects.filter(is_active=True)
        context['festivals_json'] = json.dumps([
            {
                'id': f.id,
                'name': f.name,
                'slug': f.slug,
                'start_date': f.start_date.isoformat(),
                'end_date': f.end_date.isoformat(),
                'location': f.location,
                'artist_count': LineupSlot.objects.filter(
                    festival=f, status='confirmed'
                ).values('artist').distinct().count(),
            }
            for f in festivals
        ])
        context['first_festival_id'] = festivals.first().id if festivals.exists() else None
        return context


class FestivalDetailView(TemplateView):
    template_name = 'public/festival_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        festival = get_object_or_404(Festival, slug=kwargs['slug'])
        context['festival'] = festival
        return context


class PrivacyView(TemplateView):
    template_name = 'public/privacy.html'
