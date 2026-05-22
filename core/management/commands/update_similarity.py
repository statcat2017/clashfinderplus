from django.core.management.base import BaseCommand

from core.similarity.edges import EdgeComputer
from core.similarity.embeddings import EmbeddingBuilder


class Command(BaseCommand):
    help = 'Run full similarity pipeline: enrich + embeddings + edges'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true')
        parser.add_argument('--artist-id', type=int)

    def handle(self, *args, **options):
        from core.management.commands.enrich_artists import Command as EnrichCmd
        from core.management.commands.compute_embeddings import Command as EmbedCmd
        from core.management.commands.compute_edges import Command as EdgeCmd

        self.stdout.write("=== Step 1: Enrich artists ===")
        enrich = EnrichCmd()
        enrich.handle(artist_id=options['artist_id'], all=options['all'], sources='musicbrainz')

        self.stdout.write("\n=== Step 2: Compute embeddings ===")
        embed = EmbedCmd()
        embed.handle(artist_id=options['artist_id'], all=options['all'])

        self.stdout.write("\n=== Step 3: Compute edges ===")
        edge = EdgeCmd()
        edge.handle(artist_id=options['artist_id'], all=options['all'])

        self.stdout.write("\nDone! Full similarity pipeline complete.")
