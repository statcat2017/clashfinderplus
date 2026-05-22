from django.core.management.base import BaseCommand

from core.similarity.taste import TasteGraphBuilder


class Command(BaseCommand):
    help = 'Compute taste edges from TasteSelection data'

    def add_arguments(self, parser):
        parser.add_argument('--festival-id', type=int, help='Scope to a specific festival')

    def handle(self, *args, **options):
        from core.models import Festival
        builder = TasteGraphBuilder()

        if options['festival_id']:
            festival = Festival.objects.get(id=options['festival_id'])
            count = builder.update_all_edges(festival=festival)
            self.stdout.write(f"Computed {count} taste edges for {festival.name}")
        else:
            count = builder.update_all_edges()
            self.stdout.write(f"Computed {count} taste edges globally")
