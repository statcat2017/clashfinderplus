import math

from django.db.models import Q

from ..models import Artist, ArtistEmbedding, SimilarityEdge


class EdgeComputer:
    K = 20
    MIN_SCORE = 0.05
    STORE_THRESHOLD = 0.10

    def compute_edges_for_artist(self, artist):
        emb_qs = ArtistEmbedding.objects.filter(
            artist__is_active=True
        ).exclude(artist=artist)

        scores = []
        for other_emb in emb_qs:
            sim = self._cosine_similarity(
                artist.embedding.vector if hasattr(artist, 'embedding') else [],
                other_emb.vector,
            )
            if sim > self.MIN_SCORE:
                scores.append((other_emb.artist, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_k = scores[:self.K]

        existing_edges = set()
        for edge in SimilarityEdge.objects.filter(
            Q(artist_a=artist) | Q(artist_b=artist), is_active=True
        ):
            if edge.is_locked:
                existing_edges.add(
                    (edge.artist_b_id if edge.artist_a_id == artist.id else edge.artist_a_id)
                )

        for other_artist, sim in top_k:
            if other_artist.id in existing_edges:
                continue
            a_id = min(artist.id, other_artist.id)
            b_id = max(artist.id, other_artist.id)
            SimilarityEdge.objects.update_or_create(
                artist_a_id=a_id,
                artist_b_id=b_id,
                defaults={
                    'tag_score': sim,
                    'final_score': sim,
                    'is_active': True,
                    'computed_at': __import__('django.utils.timezone', fromlist=['now']).now(),
                    'model_version': 'edge-v1',
                    'weights_version': 'v1',
                },
            )

        existing_edges_in_range = SimilarityEdge.objects.filter(
            Q(artist_a=artist) | Q(artist_b=artist),
            is_active=True,
            is_locked=False,
        )
        for edge in existing_edges_in_range:
            edge.is_active = False
            edge.save()

    def _cosine_similarity(self, v1, v2):
        if not v1 or not v2:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def compute_all_edges(self):
        count = 0
        for artist in Artist.objects.filter(is_active=True):
            try:
                self.compute_edges_for_artist(artist)
                count += 1
            except Exception:
                pass
        return count
