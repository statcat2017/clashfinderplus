from collections import Counter

from ..models import Artist, ArtistCluster, ArtistEmbedding, Cluster


class ClusterDetector:
    def __init__(self, min_cluster_size=5, min_samples=2):
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples

    def detect_clusters(self, artist_ids=None):
        if artist_ids:
            qs = ArtistEmbedding.objects.filter(artist_id__in=artist_ids)
        else:
            qs = ArtistEmbedding.objects.all()

        vectors = []
        ids = []
        for emb in qs:
            vectors.append(emb.vector)
            ids.append(emb.artist_id)

        if not vectors or len(vectors) < self.min_cluster_size:
            return {'clusters': {}, 'noise': ids}

        try:
            import numpy as np
            import hdbscan

            X = np.array(vectors, dtype=np.float64)
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=self.min_samples,
                prediction_data=True,
            )
            labels = clusterer.fit_predict(X)
            probabilities = clusterer.probabilities_

            clusters = {}
            noise = []
            for i, artist_id in enumerate(ids):
                label = int(labels[i])
                if label == -1:
                    noise.append(artist_id)
                else:
                    if label not in clusters:
                        clusters[label] = {
                            'artist_ids': [],
                            'membership_strengths': {},
                        }
                    clusters[label]['artist_ids'].append(artist_id)
                    clusters[label]['membership_strengths'][artist_id] = float(probabilities[i])

            return {
                'clusters': clusters,
                'noise': noise,
                'hierarchy': [],
            }

        except ImportError:
            return {'clusters': {}, 'noise': ids}

    def detect_subclusters(self, parent_cluster):
        member_ids = list(
            parent_cluster.members.values_list('artist_id', flat=True)
        )
        result = self.detect_clusters(artist_ids=member_ids)
        subclusters = []
        for label, data in result.get('clusters', {}).items():
            sub = Cluster.objects.create(
                name=f"{parent_cluster.name} ({label})",
                parent=parent_cluster,
                color=self._generate_color(),
            )
            for artist_id in data['artist_ids']:
                ArtistCluster.objects.get_or_create(
                    artist_id=artist_id,
                    cluster=sub,
                    defaults={'strength': data['membership_strengths'].get(artist_id, 1.0)},
                )
            subclusters.append(sub)
        return subclusters

    def name_cluster(self, artist_ids):
        artists = Artist.objects.filter(id__in=artist_ids)
        tag_counter = Counter()
        for a in artists:
            tag_counter.update(a.genre_tags or [])
        top_tags = [t for t, _ in tag_counter.most_common(5)]
        top_artists = [a.canonical_name or a.name for a in artists[:3]]
        if top_tags:
            return f"{' / '.join(top_tags[:3])} ({', '.join(top_artists)})"
        return f"Cluster ({', '.join(top_artists)})"

    def update_models(self, results):
        clusters_created = 0
        for label, data in results.get('clusters', {}).items():
            name = self.name_cluster(data['artist_ids'])
            cluster, created = Cluster.objects.get_or_create(
                name=name,
                defaults={'color': self._generate_color()},
            )
            for artist_id in data['artist_ids']:
                ArtistCluster.objects.get_or_create(
                    artist_id=artist_id,
                    cluster=cluster,
                    defaults={
                        'strength': data['membership_strengths'].get(artist_id, 1.0),
                    },
                )
            if created:
                clusters_created += 1
        return clusters_created

    def _generate_color(self):
        import hashlib
        import random
        colors = [
            '#6366f1', '#ef4444', '#22c55e', '#f59e0b', '#ec4899',
            '#14b8a6', '#8b5cf6', '#f97316', '#06b6d4', '#84cc16',
        ]
        return random.choice(colors)
