import json
import uuid

from django.test import Client, TestCase
from django.urls import reverse

from core.models import (
    Artist, Festival, LineupSlot, RecFeedback, SimilarityEdge,
    TasteSelection, TasteSession,
)


class APITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.festival = Festival.objects.create(
            name='Test Fest',
            slug='test-fest',
            start_date='2025-06-01',
            end_date='2025-06-03',
            location='Test',
        )
        self.artists = []
        for i in range(5):
            a = Artist.objects.create(
                name=f'Artist {i}', canonical_name=f'Artist {i}',
                genre_tags=['rock'],
            )
            self.artists.append(a)
            LineupSlot.objects.create(
                festival=self.festival, artist=a, status='confirmed'
            )

        # Create similarity edges between some artists
        SimilarityEdge.objects.create(
            artist_a=self.artists[0], artist_b=self.artists[2],
            final_score=0.8, is_active=True,
        )
        SimilarityEdge.objects.create(
            artist_a=self.artists[1], artist_b=self.artists[3],
            final_score=0.7, is_active=True,
        )

    def test_festival_list(self):
        response = self.client.get('/api/festivals/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Test Fest')

    def test_festival_lineup(self):
        response = self.client.get(f'/api/festivals/{self.festival.id}/lineup/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['festival']['name'], 'Test Fest')
        self.assertIn('days', data)

    def test_recommendations(self):
        session_id = str(uuid.uuid4())
        response = self.client.post(
            '/api/recommendations/',
            json.dumps({
                'session_id': session_id,
                'festival_id': self.festival.id,
                'liked_artist_ids': [self.artists[0].id, self.artists[1].id],
                'max_results': 5,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('recommendations', data)

    def test_recommendations_empty_liked(self):
        session_id = str(uuid.uuid4())
        response = self.client.post(
            '/api/recommendations/',
            json.dumps({
                'session_id': session_id,
                'festival_id': self.festival.id,
                'liked_artist_ids': [],
                'max_results': 5,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['recommendations'], [])

    def test_taste_like(self):
        session_id = str(uuid.uuid4())
        response = self.client.post(
            '/api/taste/like/',
            json.dumps({
                'session_id': session_id,
                'festival_id': self.festival.id,
                'artist_id': self.artists[0].id,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_taste_unlike(self):
        session_id = str(uuid.uuid4())
        self.client.post(
            '/api/taste/like/',
            json.dumps({
                'session_id': session_id,
                'festival_id': self.festival.id,
                'artist_id': self.artists[0].id,
            }),
            content_type='application/json',
        )
        response = self.client.post(
            '/api/taste/unlike/',
            json.dumps({
                'session_id': session_id,
                'festival_id': self.festival.id,
                'artist_id': self.artists[0].id,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_taste_reset(self):
        session_id = str(uuid.uuid4())
        self.client.post(
            '/api/taste/like/',
            json.dumps({
                'session_id': session_id,
                'festival_id': self.festival.id,
                'artist_id': self.artists[0].id,
            }),
            content_type='application/json',
        )
        response = self.client.post(
            '/api/taste/reset/',
            json.dumps({'session_id': session_id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_feedback(self):
        session_id = str(uuid.uuid4())
        response = self.client.post(
            '/api/feedback/',
            json.dumps({
                'session_id': session_id,
                'festival_id': self.festival.id,
                'recommended_artist_id': self.artists[2].id,
                'liked_artist_ids': [self.artists[0].id],
                'feedback': 'good_shout',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RecFeedback.objects.count(), 1)

    def test_recommendations_excludes_liked(self):
        session_id = str(uuid.uuid4())
        liked_ids = [self.artists[0].id, self.artists[1].id]
        response = self.client.post(
            '/api/recommendations/',
            json.dumps({
                'session_id': session_id,
                'festival_id': self.festival.id,
                'liked_artist_ids': liked_ids,
                'max_results': 10,
            }),
            content_type='application/json',
        )
        data = response.json()
        returned_ids = [r['artist']['id'] for r in data['recommendations']]
        for lid in liked_ids:
            self.assertNotIn(lid, returned_ids)
