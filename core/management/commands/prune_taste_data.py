from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import RecFeedback, TasteSelection, TasteSession


class Command(BaseCommand):
    help = 'Prune old taste data for privacy retention policy'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=180)

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        old_sessions = TasteSession.objects.filter(created_at__lt=cutoff)

        session_count = old_sessions.count()
        selection_count = TasteSelection.objects.filter(
            session__in=old_sessions
        ).count()
        feedback_count = RecFeedback.objects.filter(
            session__in=old_sessions
        ).count()

        old_sessions.delete()

        self.stdout.write(
            f"Pruned: {session_count} sessions, "
            f"{selection_count} selections, "
            f"{feedback_count} feedback records "
            f"(older than {options['days']} days)"
        )
