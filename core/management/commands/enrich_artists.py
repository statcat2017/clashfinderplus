from django.core.management.base import BaseCommand

from core.similarity.lastfm import LastFMClient
from core.similarity.musicbrainz import MusicBrainzClient
from core.models import Artist, ArtistIdentifier, ArtistSignal, RawExternalData


class Command(BaseCommand):
    help = 'Enrich artists with external data from MusicBrainz and Last.fm'

    def add_arguments(self, parser):
        parser.add_argument('--artist-id', type=int, help='Enrich a specific artist')
        parser.add_argument('--all', action='store_true', help='Enrich all artists')
        parser.add_argument('--sources', default='musicbrainz', help='Comma-separated sources')

    def handle(self, *args, **options):
        if options['artist_id']:
            artists = Artist.objects.filter(id=options['artist_id'], is_active=True)
        elif options['all']:
            artists = Artist.objects.filter(is_active=True)
        else:
            artists = Artist.objects.filter(is_active=True)

        sources = [s.strip() for s in options['sources'].split(',')]
        mb = MusicBrainzClient() if 'musicbrainz' in sources else None
        lfm = LastFMClient() if 'lastfm' in sources else None

        enriched = 0
        errors = 0
        for artist in artists:
            try:
                if mb:
                    result = mb.search_artist(artist.canonical_name or artist.name)
                    if result:
                        ArtistIdentifier.objects.get_or_create(
                            source='musicbrainz',
                            external_id=result['id'],
                            defaults={
                                'artist': artist,
                                'url': f"https://musicbrainz.org/artist/{result['id']}",
                                'confidence': 1.0,
                            },
                        )
                        tags = mb.get_artist_tags(result['id'])
                        for tag in tags:
                            ArtistSignal.objects.update_or_create(
                                artist=artist,
                                source='musicbrainz',
                                key=f"tag:{tag['name']}",
                                defaults={
                                    'value': min(tag['count'] / 100, 1.0),
                                    'confidence': 0.8,
                                },
                            )
                        aliases = mb.get_artist_aliases(result['id'])
                        for alias in aliases:
                            artist.aliases.get_or_create(alias=alias, source='musicbrainz')

                        RawExternalData.objects.update_or_create(
                            artist=artist,
                            source='musicbrainz',
                            endpoint='artist/search',
                            defaults={'raw_data': result},
                        )

                if lfm:
                    tags = lfm.get_top_tags(artist.canonical_name or artist.name)
                    for tag_name, weight in tags.items():
                        ArtistSignal.objects.update_or_create(
                            artist=artist,
                            source='lastfm',
                            key=f"tag:{tag_name}",
                            defaults={'value': weight, 'confidence': 0.7},
                        )
                    RawExternalData.objects.update_or_create(
                        artist=artist,
                        source='lastfm',
                        endpoint='artist.getTopTags',
                        defaults={'raw_data': tags},
                    )

                enriched += 1
                if enriched % 10 == 0:
                    self.stdout.write(f"Enriched {enriched} artists...")
            except Exception as e:
                errors += 1
                self.stderr.write(f"Error enriching {artist}: {e}")

        self.stdout.write(f"Done. Enriched: {enriched}, Errors: {errors}")
