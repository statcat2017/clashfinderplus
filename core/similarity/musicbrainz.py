import httpx
from django.conf import settings


class MusicBrainzClient:
    def __init__(self):
        self.base_url = "https://musicbrainz.org/ws/2/"
        self.user_agent = getattr(settings, 'MUSICBRAINZ_USER_AGENT', 'ClashfinderPlus/1.0')

    def _get(self, endpoint, params=None):
        headers = {'User-Agent': self.user_agent}
        if params is None:
            params = {}
        params['fmt'] = 'json'
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=30,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    def search_artist(self, name):
        data = self._get('artist', {'query': name})
        if data and data.get('artists'):
            artist = data['artists'][0]
            return {
                'id': artist['id'],
                'name': artist.get('name', ''),
                'type': artist.get('type', ''),
                'country': artist.get('country', ''),
                'tags': [t['name'] for t in artist.get('tags', [])],
                'genres': [g['name'] for g in artist.get('genres', [])],
            }
        return None

    def get_artist_tags(self, mbid):
        data = self._get(f'artist/{mbid}', {'inc': 'tags+genres'})
        if not data:
            return []
        tags = []
        for t in data.get('tags', []):
            tags.append({'name': t['name'], 'count': t.get('count', 0)})
        for g in data.get('genres', []):
            tags.append({'name': g['name'], 'count': g.get('count', 0)})
        return tags

    def get_artist_aliases(self, mbid):
        data = self._get(f'artist/{mbid}', {'inc': 'aliases'})
        if not data:
            return []
        return [a.get('name', '') for a in data.get('aliases', [])]
