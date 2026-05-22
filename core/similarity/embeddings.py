import math
from collections import Counter

from ..models import Artist, ArtistCluster, ArtistEmbedding, Cluster, Festival, SimilarityEdge
from .anchors import AnchorService


class EmbeddingBuilder:
    DIM = 50
    SCHEMA_VERSION = 'v1.0'

    def __init__(self):
        self.anchor_service = AnchorService()

    def build_all_tags(self):
        tags = set()
        for a in Artist.objects.exclude(genre_tags=[]):
            tags.update(a.genre_tags)
        return sorted(tags)

    def _tag_vector(self, artist, all_tags):
        tags = set(artist.genre_tags or [])
        return [1.0 if t in tags else 0.0 for t in all_tags]

    def _festival_metadata(self, artist):
        n_festivals = Festival.objects.filter(
            lineup_slots__artist=artist
        ).distinct().count()
        max_festivals = max(
            Festival.objects.filter(lineup_slots__artist__isnull=False)
            .distinct().count(), 1
        )
        return [
            math.log(n_festivals + 1) / math.log(max_festivals + 1),
            1.0 if artist.is_anchor else 0.0,
        ]

    def _manual_edge_density(self, artist):
        regions = AnchorService.REGIONS
        vectors = []
        for region in regions:
            region_artists = Artist.objects.filter(genre_tags__contains=[region])
            scores = []
            for ra in region_artists:
                edge = SimilarityEdge.objects.filter(
                    artist_a=artist, artist_b=ra, is_active=True
                ).first()
                if not edge:
                    edge = SimilarityEdge.objects.filter(
                        artist_a=ra, artist_b=artist, is_active=True
                    ).first()
                if edge and edge.final_score is not None:
                    scores.append(edge.final_score)
            avg = sum(scores) / len(scores) if scores else 0.0
            vectors.append(avg)
        while len(vectors) < 8:
            vectors.append(0.0)
        return vectors[:8]

    def build_embedding(self, artist):
        all_tags = self.build_all_tags()
        tag_vec = self._tag_vector(artist, all_tags)

        tag_dims = min(len(tag_vec), 20)
        tag_padded = tag_vec[:tag_dims] + [0.0] * (20 - tag_dims)

        anchor_vec = self.anchor_service.compute_affinity_vector(artist)

        meta = self._festival_metadata(artist)

        edge_density = self._manual_edge_density(artist)

        vector = tag_padded + anchor_vec + meta + edge_density
        vector = vector[:self.DIM]
        while len(vector) < self.DIM:
            vector.append(0.0)

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        anchor_hash = self.anchor_service.get_anchor_set_hash()

        emb, _ = ArtistEmbedding.objects.update_or_create(
            artist=artist,
            defaults={
                'version': 1,
                'embedding_schema_version': self.SCHEMA_VERSION,
                'anchor_set_hash': anchor_hash,
                'vector': vector,
                'source_summary': 'admin_tags+anchor_affinity+festival_metadata+edge_density',
            },
        )
        return emb

    def build_all_embeddings(self):
        count = 0
        for artist in Artist.objects.filter(is_active=True):
            try:
                self.build_embedding(artist)
                count += 1
            except Exception:
                pass
        return count
