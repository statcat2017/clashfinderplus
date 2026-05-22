import hashlib
import time
import uuid
from datetime import datetime

import httpx

from .base import BaseImporter
from ..models import RawExternalData


class ClashfinderAPIImporter(BaseImporter):
    API_BASE = "https://clashfinder.com/api/2025/"

    def __init__(self, festival, username, public_key):
        super().__init__(festival)
        self.username = username
        self.public_key = public_key

    @property
    def importer_type(self):
        return 'clashfinder_api'

    def _auth_params(self):
        nonce = uuid.uuid4().hex
        timestamp = int(time.time())
        to_sign = f"{nonce}{timestamp}{self.public_key}"
        signature = hashlib.sha256(to_sign.encode()).hexdigest()
        return {
            'authUsername': self.username,
            'authNonce': nonce,
            'authTimestamp': timestamp,
            'authSignature': signature,
        }

    def fetch(self):
        if not self.festival.clashfinder_url:
            raise ValueError("Festival has no clashfinder_url set")

        event_id = self.festival.clashfinder_url.strip('/').split('/')[-1]
        url = f"{self.API_BASE}e/{event_id}/"

        params = self._auth_params()
        response = httpx.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        RawExternalData.objects.update_or_create(
            artist=None,
            source='clashfinder_api',
            endpoint=f'e/{event_id}',
            defaults={'raw_data': data, 'fetched_at': datetime.now()},
        )

        slots = []
        for item in data.get('events', []):
            slots.append({
                'artist_name': item.get('artist', item.get('name', '')),
                'stage': item.get('stage', ''),
                'day': item.get('day'),
                'start_time': item.get('starttime'),
                'end_time': item.get('endtime'),
                'slot_name': item.get('slot_name', ''),
                'position': item.get('position', 0),
                'status': self._map_status(item.get('status', '')),
                'raw_label': item.get('note', ''),
                'source_url': self.festival.clashfinder_url,
                'source_ref': f"clashfinder-api-{event_id}",
            })
        return slots

    def _map_status(self, status):
        mapping = {
            'cancelled': 'cancelled',
            'tbc': 'tbc',
            'rumour': 'rumoured',
            'tba': 'tbc',
        }
        return mapping.get(status.lower(), 'confirmed')
