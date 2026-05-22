from django.contrib import admin

from .models import (
    AnchorArtist, AnchorSet, Artist, ArtistAlias, ArtistCluster,
    ArtistEmbedding, ArtistIdentifier, ArtistSignal, CanvasMove,
    Cluster, Festival, LineupSlot, RawExternalData, RecFeedback,
    ScrapeLog, SimilarityEdge, TasteEdge, TasteSelection, TasteSession,
)


@admin.register(Festival)
class FestivalAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'location', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'location']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['-start_date']


class ArtistAliasInline(admin.TabularInline):
    model = ArtistAlias
    extra = 1


class ArtistIdentifierInline(admin.TabularInline):
    model = ArtistIdentifier
    extra = 1


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['name', 'canonical_name', 'is_anchor', 'canvas_status']
    list_filter = ['is_anchor', 'canvas_status']
    search_fields = ['name', 'canonical_name']
    inlines = [ArtistAliasInline, ArtistIdentifierInline]


@admin.register(ArtistAlias)
class ArtistAliasAdmin(admin.ModelAdmin):
    list_display = ['alias', 'artist', 'source']
    search_fields = ['alias', 'artist__name']
    list_filter = ['source']


@admin.register(ArtistIdentifier)
class ArtistIdentifierAdmin(admin.ModelAdmin):
    list_display = ['artist', 'source', 'external_id', 'confidence']
    list_filter = ['source']
    search_fields = ['external_id', 'artist__name']


@admin.register(LineupSlot)
class LineupSlotAdmin(admin.ModelAdmin):
    list_display = ['festival', 'artist', 'stage', 'day', 'start_time', 'status']
    list_filter = ['festival', 'status', 'stage']
    search_fields = ['artist__name', 'festival__name']
    raw_id_fields = ['artist', 'festival']


@admin.register(AnchorSet)
class AnchorSetAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'is_active']
    list_filter = ['is_active']


@admin.register(AnchorArtist)
class AnchorArtistAdmin(admin.ModelAdmin):
    list_display = ['anchor_set', 'artist', 'role', 'x_normalized', 'y_normalized']
    list_filter = ['anchor_set']
    autocomplete_fields = ['artist']


@admin.register(ArtistSignal)
class ArtistSignalAdmin(admin.ModelAdmin):
    list_display = ['artist', 'source', 'key', 'value', 'confidence']
    list_filter = ['source']
    search_fields = ['artist__name', 'key']


@admin.register(RawExternalData)
class RawExternalDataAdmin(admin.ModelAdmin):
    list_display = ['artist', 'source', 'endpoint', 'fetched_at']
    list_filter = ['source']
    search_fields = ['artist__name']
    readonly_fields = ['raw_data', 'fetched_at']


@admin.register(ArtistEmbedding)
class ArtistEmbeddingAdmin(admin.ModelAdmin):
    list_display = ['artist', 'version', 'embedding_schema_version', 'generated_at']
    readonly_fields = ['vector', 'generated_at', 'version']
    search_fields = ['artist__name']


@admin.register(SimilarityEdge)
class SimilarityEdgeAdmin(admin.ModelAdmin):
    list_display = ['artist_a', 'artist_b', 'final_score', 'is_locked', 'is_active']
    list_filter = ['is_locked', 'is_active']
    search_fields = ['artist_a__name', 'artist_b__name']
    autocomplete_fields = ['artist_a', 'artist_b']


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'color']
    list_filter = ['parent']
    search_fields = ['name']
    autocomplete_fields = ['anchor_artist']


@admin.register(ArtistCluster)
class ArtistClusterAdmin(admin.ModelAdmin):
    list_display = ['artist', 'cluster', 'strength']
    list_filter = ['cluster']
    autocomplete_fields = ['artist']


@admin.register(CanvasMove)
class CanvasMoveAdmin(admin.ModelAdmin):
    list_display = ['artist', 'admin_user', 'new_x', 'new_y', 'created_at']
    readonly_fields = ['artist', 'old_x', 'old_y', 'new_x', 'new_y', 'admin_user', 'created_at']
    list_filter = ['admin_user']


@admin.register(TasteSession)
class TasteSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'festival', 'created_at']
    readonly_fields = ['session_id', 'festival', 'created_at']
    list_filter = ['festival']


@admin.register(TasteSelection)
class TasteSelectionAdmin(admin.ModelAdmin):
    list_display = ['session', 'artist', 'selected_at']
    readonly_fields = ['session', 'artist', 'selected_at']
    search_fields = ['artist__name']
    autocomplete_fields = ['artist']


@admin.register(TasteEdge)
class TasteEdgeAdmin(admin.ModelAdmin):
    list_display = ['source_artist', 'target_artist', 'smoothed_lift', 'confidence', 'sample_size']
    list_filter = ['festival']
    search_fields = ['source_artist__name', 'target_artist__name']
    autocomplete_fields = ['source_artist', 'target_artist']


@admin.register(RecFeedback)
class RecFeedbackAdmin(admin.ModelAdmin):
    list_display = ['session', 'recommended_artist', 'feedback', 'created_at']
    list_filter = ['feedback']
    readonly_fields = ['session', 'recommended_artist', 'liked_artists', 'feedback', 'created_at']


@admin.register(ScrapeLog)
class ScrapeLogAdmin(admin.ModelAdmin):
    list_display = ['festival', 'importer_type', 'timestamp', 'status']
    list_filter = ['status', 'importer_type']
    readonly_fields = ['festival', 'importer_type', 'timestamp', 'artists_found', 'artists_new', 'errors']
