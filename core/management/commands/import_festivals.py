from django.core.management.base import BaseCommand, CommandError

from core.lineup_importers.clashfinder_api import ClashfinderAPIImporter
from core.lineup_importers.clashfinder_html import ClashfinderHTMLImporter
from core.lineup_importers.csv_importer import CSVImporter
from core.models import Festival


class Command(BaseCommand):
    help = 'Import lineup data for festivals'

    def add_arguments(self, parser):
        parser.add_argument('--festival-id', type=int, help='Import a specific festival by ID')
        parser.add_argument('--all', action='store_true', help='Import all active festivals')
        parser.add_argument('--importer', default='clashfinder_html',
                            choices=['clashfinder_api', 'clashfinder_html', 'csv'])
        parser.add_argument('--csv-file', help='Path to CSV file (for csv importer)')
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without writing')

    def handle(self, *args, **options):
        if options['festival_id']:
            festivals = Festival.objects.filter(id=options['festival_id'])
        elif options['all']:
            festivals = Festival.objects.filter(is_active=True)
        else:
            raise CommandError('Specify --festival-id=N or --all')

        for festival in festivals:
            if options['importer'] == 'clashfinder_api':
                importer = ClashfinderAPIImporter(festival, '', '')
            elif options['importer'] == 'clashfinder_html':
                importer = ClashfinderHTMLImporter(festival)
            elif options['importer'] == 'csv':
                if not options['csv_file']:
                    raise CommandError('--csv-file is required for csv importer')
                with open(options['csv_file']) as f:
                    importer = CSVImporter(festival, f)
            else:
                raise CommandError(f'Unknown importer: {options["importer"]}')

            if options['dry_run']:
                slots_data = importer.fetch()
                self.stdout.write(f"{festival.name}: found {len(slots_data)} slots (dry run)")
                continue

            log = importer.import_lineup()
            self.stdout.write(
                f"{festival.name}: found={log.artists_found} "
                f"new={log.artists_new} updated={log.artists_updated} "
                f"status={log.status}"
            )
