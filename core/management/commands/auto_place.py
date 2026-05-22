from django.core.management.base import BaseCommand

from core.similarity.projection import CanvasProjector


class Command(BaseCommand):
    help = 'Auto-place unplaced artists using UMAP projection'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Include all artists')
        parser.add_argument('--festival-id', type=int, help='Artists in a specific festival')

    def handle(self, *args, **options):
        from core.models import Artist, Festival

        if options['festival_id']:
            festival = Festival.objects.get(id=options['festival_id'])
            artists = Artist.objects.filter(
                lineup_slots__festival=festival, is_active=True, canvas_status='unplaced'
            )
        elif options['all']:
            artists = Artist.objects.filter(is_active=True, canvas_status='unplaced')
        else:
            artists = Artist.objects.filter(is_active=True, canvas_status='unplaced')

        ids = list(artists.values_list('id', flat=True))
        if not ids:
            self.stdout.write("No unplaced artists to position")
            return

        projector = CanvasProjector()
        placed, skipped = projector.auto_place_unplaced()
        self.stdout.write(f"Placed: {placed}, Skipped: {skipped}")
