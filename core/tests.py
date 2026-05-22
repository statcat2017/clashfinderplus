from django.test import TestCase

from core.models import (
    AnchorArtist, AnchorSet, Artist, ArtistAlias, ArtistCluster,
    ArtistEmbedding, ArtistIdentifier, CanvasMove, Cluster,
    Festival, LineupSlot, RecFeedback, ScrapeLog, SimilarityEdge,
    TasteEdge, TasteSelection, TasteSession,
)


class ModelTests(TestCase):
    def setUp(self):
        self.festival = Festival.objects.create(
            name='Test Festival',
            slug='test-festival',
            start_date='2025-06-01',
            end_date='2025-06-03',
            location='Test Location',
        )
        self.artist_a = Artist.objects.create(
            name='Artist A', canonical_name='Artist A',
            genre_tags=['rock', 'indie'],
        )
        self.artist_b = Artist.objects.create(
            name='Artist B', canonical_name='Artist B',
            genre_tags=['rock', 'metal'],
        )
        self.slot_a = LineupSlot.objects.create(
            festival=self.festival,
            artist=self.artist_a,
            stage='Main',
            day=1,
        )
        self.slot_b = LineupSlot.objects.create(
            festival=self.festival,
            artist=self.artist_b,
            stage='Second',
            day=1,
        )

    def test_festival_creation(self):
        self.assertEqual(str(self.festival), 'Test Festival')
        self.assertTrue(self.festival.is_active)

    def test_artist_creation(self):
        self.assertEqual(str(self.artist_a), 'Artist A')
        self.assertEqual(self.artist_a.canvas_status, 'unplaced')

    def test_artist_alias(self):
        alias = ArtistAlias.objects.create(
            artist=self.artist_a, alias='Artist A alias', source='import'
        )
        self.assertIn('Artist A alias', str(alias))

    def test_artist_identifier(self):
        ident = ArtistIdentifier.objects.create(
            artist=self.artist_a,
            source='musicbrainz',
            external_id='12345',
        )
        self.assertEqual(str(ident), 'musicbrainz:12345')

    def test_lineup_slot(self):
        self.assertEqual(str(self.slot_a), 'Artist A @ Test Festival (Confirmed)')
        self.assertEqual(self.slot_a.stage, 'Main')

    def test_multiple_slots_per_artist(self):
        slot2 = LineupSlot.objects.create(
            festival=self.festival, artist=self.artist_a, stage='Second', day=2,
        )
        self.assertEqual(self.artist_a.lineup_slots.count(), 2)

    def test_similarity_edge_ordering(self):
        edge = SimilarityEdge.objects.create(
            artist_a=self.artist_a,
            artist_b=self.artist_b,
            final_score=0.85,
            explanation='Test edge',
        )
        self.assertEqual(edge.final_score, 0.85)
        self.assertTrue(edge.is_active)

    def test_embedding(self):
        emb = ArtistEmbedding.objects.create(
            artist=self.artist_a,
            vector=[0.1] * 50,
            embedding_schema_version='v1.0',
        )
        self.assertEqual(len(emb.vector), 50)

    def test_taste_session(self):
        session = TasteSession.objects.create(
            session_id='550e8400-e29b-41d4-a716-446655440000',
            festival=self.festival,
        )
        self.assertEqual(str(session.festival), 'Test Festival')

    def test_taste_selection(self):
        session = TasteSession.objects.create(
            session_id='550e8400-e29b-41d4-a716-446655440001',
            festival=self.festival,
        )
        selection = TasteSelection.objects.create(
            session=session, artist=self.artist_a
        )
        self.assertEqual(selection.artist, self.artist_a)

    def test_taste_edge(self):
        session = TasteSession.objects.create(
            session_id='550e8400-e29b-41d4-a716-446655440002',
            festival=self.festival,
        )
        TasteSelection.objects.create(session=session, artist=self.artist_a)
        TasteSelection.objects.create(session=session, artist=self.artist_b)
        edge = TasteEdge.objects.create(
            source_artist=self.artist_a,
            target_artist=self.artist_b,
            raw_lift=1.5,
            smoothed_lift=1.3,
            confidence=0.8,
            sample_size=15,
            festival=self.festival,
        )
        self.assertGreater(edge.smoothed_lift, 1.0)

    def test_rec_feedback(self):
        session = TasteSession.objects.create(
            session_id='550e8400-e29b-41d4-a716-446655440003',
            festival=self.festival,
        )
        feedback = RecFeedback.objects.create(
            session=session,
            recommended_artist=self.artist_b,
            liked_artists=[self.artist_a.id],
            feedback='good_shout',
        )
        self.assertEqual(feedback.feedback, 'good_shout')

    def test_cluster(self):
        cluster = Cluster.objects.create(name='Rock', color='#ef4444')
        ac = ArtistCluster.objects.create(
            artist=self.artist_a, cluster=cluster, strength=0.9
        )
        self.assertEqual(ac.strength, 0.9)

    def test_canvas_move(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username='admin', password='admin')
        move = CanvasMove.objects.create(
            artist=self.artist_a,
            old_x=0.0, old_y=0.0,
            new_x=0.5, new_y=0.3,
            admin_user=user,
        )
        self.assertEqual(move.new_x, 0.5)

    def test_scrape_log(self):
        log = ScrapeLog.objects.create(
            festival=self.festival,
            importer_type='clashfinder_html',
            artists_found=10,
            artists_new=5,
            status='success',
        )
        self.assertEqual(log.artists_found, 10)
        self.assertEqual(log.status, 'success')

    def test_similarity_edge_constraint(self):
        a, b = self.artist_a.id, self.artist_b.id
        e1 = SimilarityEdge.objects.create(
            artist_a_id=min(a, b), artist_b_id=max(a, b), final_score=0.5
        )
        self.assertEqual(e1.artist_a_id, min(a, b))
        self.assertEqual(e1.artist_b_id, max(a, b))
