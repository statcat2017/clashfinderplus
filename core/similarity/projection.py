import math
import random

from ..models import Artist, ArtistEmbedding


class CanvasProjector:
    def __init__(self, n_neighbors=15, min_dist=0.1):
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist

    def project_all(self, artist_ids=None):
        if artist_ids:
            qs = ArtistEmbedding.objects.filter(artist_id__in=artist_ids)
        else:
            qs = ArtistEmbedding.objects.all()

        positions = {}
        vectors = []
        ids = []
        for emb in qs:
            vectors.append(emb.vector)
            ids.append(emb.artist_id)

        if not vectors:
            return positions

        try:
            import numpy as np
            from sklearn.preprocessing import normalize
            from umap import UMAP

            X = np.array(vectors, dtype=np.float64)
            if X.shape[0] < 5:
                return self._fallback(ids, len(vectors[0]))

            reducer = UMAP(
                n_components=2,
                n_neighbors=min(self.n_neighbors, X.shape[0] - 1),
                min_dist=self.min_dist,
                random_state=42,
            )
            embedding = reducer.fit_transform(X)

            for i, artist_id in enumerate(ids):
                x = float(embedding[i, 0])
                y = float(embedding[i, 1])
                # Normalize to [-1, 1]
                positions[artist_id] = (self._normalize(x), self._normalize(y))

        except ImportError:
            positions = self._fallback(ids, len(vectors[0]) if vectors else 50)

        return positions

    def project_new(self, artist):
        return self.project_all(artist_ids=[artist.id])

    def auto_place_unplaced(self):
        unplaced = Artist.objects.filter(
            canvas_status='unplaced', is_active=True
        )
        ids = [a.id for a in unplaced]
        if not ids:
            return [], None

        positions = self.project_all(artist_ids=ids)
        placed = 0
        skipped = 0
        for a in unplaced:
            if a.canvas_status in ('manual', 'locked'):
                skipped += 1
                continue
            pos = positions.get(a.id)
            if pos:
                a.canvas_x, a.canvas_y = pos
                a.canvas_status = 'auto'
                a.save()
                placed += 1

        return placed, skipped

    def _normalize(self, val):
        return max(-1.0, min(1.0, val / 5.0))

    def _fallback(self, ids, dims):
        positions = {}
        for artist_id in ids:
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0.1, 0.9)
            positions[artist_id] = (
                radius * math.cos(angle),
                radius * math.sin(angle),
            )
        return positions
