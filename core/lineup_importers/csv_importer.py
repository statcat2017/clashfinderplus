import csv
import io

from .base import BaseImporter


class CSVImporter(BaseImporter):
    def __init__(self, festival, csv_file):
        super().__init__(festival)
        self.csv_file = csv_file

    @property
    def importer_type(self):
        return 'csv'

    def _detect_headers(self, headers):
        mapping = {}
        header_lower = {h: h.lower().replace(' ', '_') for h in headers}
        for header, lower in header_lower.items():
            if lower in ('artist_name', 'artist', 'name', 'act'):
                mapping[header] = 'artist_name'
            elif lower in ('stage', 'area', 'venue', 'tent'):
                mapping[header] = 'stage'
            elif lower in ('day', 'date', 'day_number'):
                mapping[header] = 'day'
            elif lower in ('start_time', 'start', 'time', 'from'):
                mapping[header] = 'start_time'
            elif lower in ('end_time', 'end', 'until', 'to'):
                mapping[header] = 'end_time'
            elif lower in ('slot_name', 'slot', 'type', 'set_type'):
                mapping[header] = 'slot_name'
            elif lower in ('status', 'confirmation'):
                mapping[header] = 'status'
        return mapping

    def fetch(self):
        if isinstance(self.csv_file, str):
            content = self.csv_file
        else:
            content = self.csv_file.read().decode('utf-8')

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise ValueError("CSV has no headers")

        mapping = self._detect_headers(reader.fieldnames)
        slots = []

        for row in reader:
            slot = {
                'artist_name': row.get(mapping.get('artist_name', 'artist_name'), ''),
                'stage': row.get(mapping.get('stage', 'stage'), ''),
                'day': self._parse_int(row.get(mapping.get('day', 'day'))),
                'start_time': row.get(mapping.get('start_time', 'start_time')),
                'end_time': row.get(mapping.get('end_time', 'end_time')),
                'slot_name': row.get(mapping.get('slot_name', 'slot_name'), ''),
                'position': self._parse_int(row.get('position', 0)),
                'status': row.get(mapping.get('status', 'status'), 'confirmed'),
                'raw_label': '',
                'source_url': '',
                'source_ref': 'csv-import',
            }
            if slot['artist_name']:
                slots.append(slot)

        return slots

    def _parse_int(self, value):
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
