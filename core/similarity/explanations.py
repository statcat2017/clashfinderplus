from ..models import Artist, SimilarityEdge


class ExplanationGenerator:
    def generate(self, artist, liked_artists):
        liked_names = [a.canonical_name or a.name for a in liked_artists[:3]]

        shared_tags = self._find_shared_tags(artist, liked_artists)
        if shared_tags:
            return {
                'type': 'shared_tags',
                'because_of': liked_names,
                'evidence': [f"same genre: {', '.join(shared_tags[:3])}"],
            }

        strong_edges = self._find_strong_edges(artist, liked_artists)
        if strong_edges:
            return {
                'type': 'similar_artist',
                'because_of': liked_names,
                'evidence': [f"similar sound to {', '.join(liked_names)}"],
            }

        manual = self._find_manual_edge(artist, liked_artists)
        if manual:
            return {
                'type': 'curated_pick',
                'because_of': liked_names,
                'evidence': ['curated pick — recommended by our editors'],
            }

        return {
            'type': 'similar_artist',
            'because_of': liked_names,
            'evidence': ['Recommended based on your likes'],
        }

    def _find_shared_tags(self, artist, liked_artists):
        artist_tags = set(artist.genre_tags or [])
        for liked in liked_artists:
            liked_tags = set(liked.genre_tags or [])
            shared = artist_tags & liked_tags
            if shared:
                return list(shared)
        return []

    def _find_strong_edges(self, artist, liked_artists):
        for liked in liked_artists:
            edge = SimilarityEdge.objects.filter(
                artist_a=liked, artist_b=artist, is_active=True
            ).first()
            if not edge:
                edge = SimilarityEdge.objects.filter(
                    artist_a=artist, artist_b=liked, is_active=True
                ).first()
            if edge and edge.final_score > 0.5:
                return [edge]
        return []

    def _find_manual_edge(self, artist, liked_artists):
        for liked in liked_artists:
            edge = SimilarityEdge.objects.filter(
                artist_a=liked, artist_b=artist,
                is_active=True, manual_score__isnull=False,
            ).first()
            if not edge:
                edge = SimilarityEdge.objects.filter(
                    artist_a=artist, artist_b=liked,
                    is_active=True, manual_score__isnull=False,
                ).first()
            if edge:
                return edge
        return None
