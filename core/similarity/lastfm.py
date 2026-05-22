import time

import httpx
from django.conf import settings


class LastFMClient:
    API_URL = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self):
        self.api_key = getattr(settings, 'LASTFM_API_KEY', '')
        self._last_call = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_call
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_call = time.time()

    def _get(self, method, params=None):
        if not self.api_key:
            return None
        self._rate_limit()
        if params is None:
            params = {}
        params.update({
            'method': method,
            'api_key': self.api_key,
            'format': 'json',
        })
        with httpx.Client() as client:
            response = client.get(self.API_URL, params=params, timeout=30)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    def get_top_tags(self, artist_name):
        data = self._get('artist.getTopTags', {'artist': artist_name})
        if not data or 'toptags' not in data:
            return {}
        tags = data['toptags'].get('tag', [])
        if not tags:
            return {}
        max_count = max(t.get('count', 0) for t in tags)
        if max_count == 0:
            return {}
        return {t['name']: t.get('count', 0) / max_count for t in tags}
