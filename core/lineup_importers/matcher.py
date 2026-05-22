from Levenshtein import distance as lev_distance

from ..models import Artist, ArtistAlias, ArtistIdentifier, LineupSlot, SimilarityEdge, TasteSelection


class ArtistMatcher:
    def find_or_create(self, name):
        name = name.strip()
        if not name:
            return None

        alias = ArtistAlias.objects.filter(alias__iexact=name).first()
        if alias:
            return alias.artist

        artist = Artist.objects.filter(canonical_name__iexact=name).first()
        if artist:
            return artist

        closest = None
        closest_dist = float('inf')
        for a in Artist.objects.all():
            d = lev_distance(name.lower(), a.canonical_name.lower())
            if d < closest_dist:
                closest_dist = d
                closest = a
        if closest_dist < 2:
            ArtistAlias.objects.get_or_create(artist=closest, alias=name, source='import')
            return closest

        artist = Artist.objects.create(
            name=name, canonical_name=name, canvas_status='unplaced'
        )
        return artist

    def find_duplicates(self, artist):
        candidates = []
        name_parts = set(artist.canonical_name.lower().split())
        for a in Artist.objects.exclude(id=artist.id):
            a_parts = set(a.canonical_name.lower().split())
            overlap = len(name_parts & a_parts)
            if overlap >= max(1, len(name_parts) // 2):
                dist = lev_distance(artist.canonical_name.lower(), a.canonical_name.lower())
                shared_aliases = ArtistAlias.objects.filter(
                    artist__in=[artist, a]
                ).values_list('alias', flat=True)
                candidates.append({
                    'artist': a,
                    'levenshtein': dist,
                    'shared_aliases': list(shared_aliases),
                    'score': self._duplicate_score(overlap, len(name_parts), dist),
                })
        candidates.sort(key=lambda c: c['score'], reverse=True)
        return candidates[:10]

    def _duplicate_score(self, overlap, total_parts, dist):
        name_score = overlap / max(total_parts, 1)
        lev_score = max(0, 1 - dist / 10)
        return name_score * 0.4 + lev_score * 0.6

    def merge_artists(self, source, target):
        source.aliases.all().update(artist=target)
        source.identifiers.all().update(artist=target)
        LineupSlot.objects.filter(artist=source).update(artist=target)
        SimilarityEdge.objects.filter(artist_a=source).update(artist_a=target)
        SimilarityEdge.objects.filter(artist_b=source).update(artist_b=target)
        TasteSelection.objects.filter(artist=source).update(artist=target)
        source.signals.all().update(artist=target)
        source.raw_data.all().update(artist=target)
        source.cluster_memberships.all().update(artist=target)
        source.canvas_moves.all().update(artist=target)
        try:
            if source.embedding:
                source.embedding.delete()
        except Exception:
            pass
        source.is_active = False
        source.marked_for_merge = True
        source.canonical_name = f"{source.canonical_name} (merged into {target.canonical_name})"
        source.save()
