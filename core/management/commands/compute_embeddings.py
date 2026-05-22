from django.core.management.base import BaseCommand

from core.similarity.embeddings import EmbeddingBuilder


class Command(BaseCommand):
    help = 'Compute artist embeddings'

    def add_arguments(self, parser):
        parser.add_argument('--artist-id', type=int, help='Compute for a specific artist')
        parser.add_argument('--all', action='store_true', help='Compute for all artists')

    def handle(self, *args, **options):
        builder = EmbeddingBuilder()
        if options['artist_id']:
            from core.models import Artist
            artist = Artist.objects.get(id=options['artist_id'])
            builder.build_embedding(artist)
            self.stdout.write(f"Computed embedding for {artist}")
        elif options['all']:
            count = builder.build_all_embeddings()
            self.stdout.write(f"Computed embeddings for {count} artists")
        else:
            self.stdout.write("Specify --artist-id=N or --all")
