from django.test import TestCase

from core.lineup_importers.matcher import ArtistMatcher
from core.models import Artist, ArtistAlias


class MatcherTests(TestCase):
    def setUp(self):
        self.matcher = ArtistMatcher()
        self.artist = Artist.objects.create(
            name='Deftones', canonical_name='Deftones',
            genre_tags=['alternative metal', 'nu-metal'],
        )

    def test_exact_match(self):
        result = self.matcher.find_or_create('Deftones')
        self.assertEqual(result, self.artist)

    def test_case_insensitive_match(self):
        result = self.matcher.find_or_create('deftones')
        self.assertEqual(result, self.artist)

    def test_alias_match(self):
        ArtistAlias.objects.create(
            artist=self.artist, alias='Deftones Band', source='import'
        )
        result = self.matcher.find_or_create('Deftones Band')
        self.assertEqual(result, self.artist)

    def test_fuzzy_match(self):
        result = self.matcher.find_or_create('Deftonez')
        self.assertEqual(result, self.artist)

    def test_creates_new_artist(self):
        result = self.matcher.find_or_create('Completely Unknown Artist')
        self.assertIsNotNone(result)
        self.assertEqual(result.canonical_name, 'Completely Unknown Artist')
        self.assertEqual(result.canvas_status, 'unplaced')

    def test_find_duplicates(self):
        similar = Artist.objects.create(
            name='The Deftones', canonical_name='The Deftones',
        )
        duplicates = self.matcher.find_duplicates(self.artist)
        self.assertGreater(len(duplicates), 0)
        self.assertTrue(any(d['artist'].id == similar.id for d in duplicates))

    def test_merge_artists(self):
        source = Artist.objects.create(
            name='Source Artist', canonical_name='Source Artist'
        )
        target = Artist.objects.create(
            name='Target Artist', canonical_name='Target Artist'
        )
        from core.models import LineupSlot, Festival

        festival = Festival.objects.create(
            name='Test', slug='test',
            start_date='2025-06-01', end_date='2025-06-03',
            location='Test',
        )
        LineupSlot.objects.create(
            festival=festival, artist=source, status='confirmed'
        )

        self.matcher.merge_artists(source, target)

        self.assertEqual(LineupSlot.objects.filter(artist=source).count(), 0)
        self.assertEqual(LineupSlot.objects.filter(artist=target).count(), 1)
