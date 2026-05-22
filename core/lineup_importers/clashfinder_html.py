import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import BaseImporter
from ..models import RawExternalData


class ClashfinderHTMLImporter(BaseImporter):
    @property
    def importer_type(self):
        return 'clashfinder_html'

    def fetch(self):
        if not self.festival.clashfinder_url:
            raise ValueError("Festival has no clashfinder_url set")

        response = httpx.get(self.festival.clashfinder_url, timeout=30, follow_redirects=True)
        response.raise_for_status()

        RawExternalData.objects.update_or_create(
            artist=None,
            source='clashfinder_html',
            endpoint=self.festival.clashfinder_url,
            defaults={'raw_data': response.text, 'fetched_at': datetime.now()},
        )

        soup = BeautifulSoup(response.text, 'html.parser')
        slots = []

        day_tabs = soup.select('.daytab, .day-tab, [class*="day"]')
        if not day_tabs:
            day_tabs = soup.select('table') or [soup]

        for day_idx, day_el in enumerate(day_tabs, 1):
            day_num = self._parse_day_number(day_el, day_idx)
            stage_cols = day_el.select('.stage, .column, td')
            if not stage_cols:
                stage_cols = day_el.select('tr')

            for stage_el in stage_cols:
                stage_name = self._parse_stage_name(stage_el)
                artists = stage_el.select('.artist, li, td')
                for artist_el in artists:
                    raw = artist_el.get_text(strip=True)
                    if not raw or len(raw) < 2:
                        continue
                    artist_name, note = self._clean_artist_name(raw)
                    time_str = self._extract_time(artist_el)
                    slots.append({
                        'artist_name': artist_name,
                        'stage': stage_name,
                        'day': day_num,
                        'start_time': time_str,
                        'end_time': None,
                        'slot_name': note or '',
                        'position': 0,
                        'status': self._parse_status(raw),
                        'raw_label': raw,
                        'source_url': self.festival.clashfinder_url,
                        'source_ref': f"clashfinder-html-{self.festival.slug}",
                    })

        return slots

    def _parse_day_number(self, el, default):
        text = el.get_text()
        for m in re.finditer(r'(\d+)', text):
            return int(m.group(1))
        return default

    def _parse_stage_name(self, el):
        header = el.select_one('h3, h4, th, .stage-name')
        if header:
            return header.get_text(strip=True)
        return ''

    def _clean_artist_name(self, raw):
        cleaned = re.sub(r'\s+\d+:\d+.*$', '', raw)
        note = ''
        paren = re.search(r'\(([^)]+)\)', cleaned)
        if paren:
            note = paren.group(1)
        cleaned = re.sub(r'\([^)]+\)', '', cleaned).strip()
        return cleaned, note

    def _extract_time(self, el):
        time_match = re.search(r'(\d{1,2}:\d{2})', el.get_text())
        if time_match:
            return time_match.group(1)
        return None

    def _parse_status(self, raw):
        lower = raw.lower()
        if 'cancelled' in lower or 'canceled' in lower:
            return 'cancelled'
        if 'tbc' in lower or 'tba' in lower:
            return 'tbc'
        if 'rumour' in lower:
            return 'rumoured'
        return 'confirmed'
