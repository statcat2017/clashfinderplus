from django.core.management.base import BaseCommand

from core.similarity.edges import EdgeComputer


class Command(BaseCommand):
    help = 'Compute top-K similarity edges'

    def add_arguments(self, parser):
        parser.add_argument('--artist-id', type=int, help='Compute for a specific artist')
        parser.add_argument('--all', action='store_true', help='Compute for all artists')
        parser.add_argument('--k', type=int, default=20)

    def handle(self, *args, **options):
        computer = EdgeComputer()
        computer.K = options['k']

        if options['artist_id']:
            from core.models import Artist
            artist = Artist.objects.get(id=options['artist_id'])
            computer.compute_edges_for_artist(artist)
            self.stdout.write(f"Computed edges for {artist}")
        elif options['all']:
            count = computer.compute_all_edges()
            self.stdout.write(f"Computed edges for {count} artists")
        else:
            self.stdout.write("Specify --artist-id=N or --all")
