from ..models import AnchorSet, Festival


class AnchorService:
    REGIONS = ['metal', 'hardcore', 'indie/alt', 'electronic', 'pop', 'hiphop', 'rock', 'heritage']

    def get_active_anchors(self):
        anchor_set = AnchorSet.objects.filter(is_active=True).first()
        if not anchor_set:
            return []
        return list(anchor_set.anchors.select_related('artist').all())

    def get_anchor_artists(self):
        return [aa.artist for aa in self.get_active_anchors()]

    def compute_affinity_vector(self, artist):
        anchors = self.get_active_anchors()
        vector = []
        for aa in anchors:
            a_fests = set(Festival.objects.filter(
                lineup_slots__artist=artist
            ).distinct().values_list('id', flat=True))
            anchor_fests = set(Festival.objects.filter(
                lineup_slots__artist=aa.artist
            ).distinct().values_list('id', flat=True))
            intersection = a_fests & anchor_fests
            union = a_fests | anchor_fests
            affinity = len(intersection) / len(union) if union else 0.0
            vector.append(affinity)
        while len(vector) < 20:
            vector.append(0.0)
        return vector[:20]

    def get_anchor_set_hash(self):
        anchor_set = AnchorSet.objects.filter(is_active=True).first()
        if not anchor_set:
            return ''
        ids = sorted(
            aa.artist_id for aa in anchor_set.anchors.all()
        )
        import hashlib
        return hashlib.sha256(','.join(str(i) for i in ids).encode()).hexdigest()[:12]
