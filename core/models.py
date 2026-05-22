import uuid
from django.conf import settings
from django.db import models


class Festival(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    website = models.URLField(blank=True)
    clashfinder_url = models.URLField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=200)
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return self.name


class Artist(models.Model):
    class CanvasStatus(models.TextChoices):
        UNPLACED = 'unplaced', 'Unplaced'
        AUTO = 'auto', 'Auto-placed'
        MANUAL = 'manual', 'Manually placed'
        LOCKED = 'locked', 'Locked'

    name = models.CharField(max_length=200)
    canonical_name = models.CharField(max_length=200)
    canvas_x = models.FloatField(default=0.0)
    canvas_y = models.FloatField(default=0.0)
    canvas_status = models.CharField(
        max_length=20, choices=CanvasStatus, default=CanvasStatus.UNPLACED
    )
    is_anchor = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    marked_for_merge = models.BooleanField(default=False)
    genre_tags = models.JSONField(default=list, blank=True)
    image_url = models.URLField(blank=True)
    last_imported = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.canonical_name or self.name


class ArtistAlias(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='aliases')
    alias = models.CharField(max_length=200)
    source = models.CharField(max_length=20, default='admin')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('artist', 'alias')

    def __str__(self):
        return f'{self.alias} → {self.artist.canonical_name}'


class ArtistIdentifier(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='identifiers')
    source = models.CharField(max_length=20)
    external_id = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    confidence = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('source', 'external_id')

    def __str__(self):
        return f'{self.source}:{self.external_id}'


class LineupSlot(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmed'
        RUMOURED = 'rumoured', 'Rumoured'
        CANCELLED = 'cancelled', 'Cancelled'
        TBC = 'tbc', 'TBC'

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='lineup_slots')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='lineup_slots')
    stage = models.CharField(max_length=100, blank=True)
    day = models.IntegerField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    slot_name = models.CharField(max_length=200, blank=True)
    position = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status, default=Status.CONFIRMED)
    raw_label = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    source_ref = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day', 'start_time', 'position']

    def __str__(self):
        return f'{self.artist} @ {self.festival} ({self.get_status_display()})'


class AnchorSet(models.Model):
    name = models.CharField(max_length=200)
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']

    def __str__(self):
        return f'{self.name} v{self.version}'


class AnchorArtist(models.Model):
    anchor_set = models.ForeignKey(AnchorSet, on_delete=models.CASCADE, related_name='anchors')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='anchor_assignments')
    role = models.CharField(max_length=100, blank=True)
    x_normalized = models.FloatField()
    y_normalized = models.FloatField()
    is_locked = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('anchor_set', 'artist')

    def __str__(self):
        return f'{self.artist} ({self.anchor_set.name})'


class ArtistSignal(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='signals')
    source = models.CharField(max_length=20)
    key = models.CharField(max_length=100)
    value = models.FloatField()
    confidence = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('artist', 'source', 'key')

    def __str__(self):
        return f'{self.artist} {self.source}:{self.key}={self.value}'


class RawExternalData(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='raw_data')
    source = models.CharField(max_length=20)
    endpoint = models.CharField(max_length=100)
    raw_data = models.JSONField()
    fetched_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'raw external data'
        ordering = ['-fetched_at']

    def __str__(self):
        return f'{self.artist} {self.source}/{self.endpoint}'


class ArtistEmbedding(models.Model):
    artist = models.OneToOneField(Artist, on_delete=models.CASCADE, related_name='embedding')
    version = models.IntegerField(default=1)
    embedding_schema_version = models.CharField(max_length=20, blank=True)
    anchor_set_hash = models.CharField(max_length=64, blank=True)
    vector = models.JSONField()
    source_summary = models.CharField(max_length=100, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.artist} v{self.version}'


class SimilarityEdge(models.Model):
    artist_a = models.ForeignKey(
        Artist, on_delete=models.CASCADE, related_name='sim_a'
    )
    artist_b = models.ForeignKey(
        Artist, on_delete=models.CASCADE, related_name='sim_b'
    )
    tag_score = models.FloatField(null=True, blank=True)
    audio_score = models.FloatField(null=True, blank=True)
    cooccurrence_score = models.FloatField(null=True, blank=True)
    canvas_score = models.FloatField(null=True, blank=True)
    cultural_affinity_score = models.FloatField(null=True, blank=True)
    manual_score = models.FloatField(null=True, blank=True)
    final_score = models.FloatField()
    is_locked = models.BooleanField(default=False)
    explanation = models.TextField(blank=True)
    model_version = models.CharField(max_length=50, blank=True)
    weights_version = models.CharField(max_length=50, blank=True)
    source_snapshot_id = models.CharField(max_length=50, blank=True)
    computed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('artist_a', 'artist_b')
        ordering = ['-final_score']

    def __str__(self):
        return f'{self.artist_a} ↔ {self.artist_b}: {self.final_score:.2f}'


class Cluster(models.Model):
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subclusters'
    )
    anchor_artist = models.ForeignKey(
        Artist, on_delete=models.SET_NULL, null=True, blank=True, related_name='leading_clusters'
    )
    color = models.CharField(max_length=7, default='#6366f1')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ArtistCluster(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='cluster_memberships')
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='members')
    strength = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('artist', 'cluster')

    def __str__(self):
        return f'{self.artist} ∈ {self.cluster}'


class CanvasMove(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='canvas_moves')
    old_x = models.FloatField()
    old_y = models.FloatField()
    new_x = models.FloatField()
    new_y = models.FloatField()
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.artist} moved by {self.admin_user}'


class TasteSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='taste_sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Session {self.session_id} @ {self.festival}'


class TasteSelection(models.Model):
    session = models.ForeignKey(
        TasteSession, on_delete=models.CASCADE, related_name='selections'
    )
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='taste_selections')
    selected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'artist')

    def __str__(self):
        return f'{self.session.session_id} → {self.artist}'


class TasteEdge(models.Model):
    source_artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, related_name='taste_source_edges'
    )
    target_artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, related_name='taste_target_edges'
    )
    festival = models.ForeignKey(
        Festival, on_delete=models.CASCADE, null=True, blank=True,
        related_name='taste_edges'
    )
    raw_lift = models.FloatField()
    smoothed_lift = models.FloatField()
    confidence = models.FloatField()
    sample_size = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('source_artist', 'target_artist', 'festival')

    def __str__(self):
        return f'{self.source_artist} → {self.target_artist}: {self.smoothed_lift:.2f}'


class RecFeedback(models.Model):
    class Feedback(models.TextChoices):
        GOOD_SHOUT = 'good_shout', 'Good Shout'
        NOT_FOR_ME = 'not_for_me', 'Not for Me'
        ALREADY_KNOW = 'already_know', 'Already Know'

    session = models.ForeignKey(TasteSession, on_delete=models.CASCADE, related_name='feedback')
    recommended_artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, related_name='rec_feedback'
    )
    liked_artists = models.JSONField()
    feedback = models.CharField(max_length=20, choices=Feedback)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.session.session_id} → {self.recommended_artist}: {self.feedback}'


class ScrapeLog(models.Model):
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='scrape_logs')
    importer_type = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    artists_found = models.IntegerField(default=0)
    artists_new = models.IntegerField(default=0)
    artists_updated = models.IntegerField(default=0)
    errors = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.festival} [{self.importer_type}] {self.status}'
