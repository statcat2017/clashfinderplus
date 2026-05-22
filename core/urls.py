from django.urls import path

from . import views, views_admin, views_api

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('festivals/<slug:slug>/', views.FestivalDetailView.as_view(), name='festival-detail'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    # API
    path('api/festivals/', views_api.FestivalListAPI.as_view(), name='api-festivals'),
    path('api/festivals/<int:pk>/lineup/', views_api.FestivalLineupAPI.as_view(), name='api-lineup'),
    path('api/recommendations/', views_api.RecommendationsAPI.as_view(), name='api-recs'),
    path('api/taste/like/', views_api.TasteLikeAPI.as_view(), name='api-taste-like'),
    path('api/taste/unlike/', views_api.TasteUnlikeAPI.as_view(), name='api-taste-unlike'),
    path('api/taste/reset/', views_api.TasteResetAPI.as_view(), name='api-taste-reset'),
    path('api/feedback/', views_api.FeedbackAPI.as_view(), name='api-feedback'),
    # Admin tools
    path('admin/import/', views_admin.ImportDashboardView.as_view(), name='admin-import'),
    path('admin/import/run/', views_admin.ImportRunView.as_view(), name='admin-import-run'),
    path('admin/dedup/', views_admin.DedupView.as_view(), name='admin-dedup'),
    path('admin/dedup/merge/', views_admin.MergeArtistsView.as_view(), name='admin-merge-artists'),
    path('admin/tags/', views_admin.TagEditorView.as_view(), name='admin-tags'),
    path('admin/tags/update/', views_admin.TagUpdateView.as_view(), name='admin-tag-update'),
    path('admin/tags/bulk/', views_admin.BulkTagView.as_view(), name='admin-bulk-tag'),
    # Canvas API
    path('api/admin/canvas-data/', views_api.CanvasDataAPI.as_view(), name='api-canvas-data'),
    path('api/admin/canvas/move/', views_api.CanvasMoveAPI.as_view(), name='api-canvas-move'),
    path('api/admin/canvas/edge/', views_api.CanvasEdgeAPI.as_view(), name='api-canvas-edge'),
    path('api/admin/canvas/auto-layout/', views_api.CanvasAutoLayoutAPI.as_view(), name='api-canvas-auto-layout'),
    path('api/admin/canvas/artist/<int:pk>/neighbors/', views_api.CanvasNeighborsAPI.as_view(), name='api-canvas-neighbors'),
    path('api/admin/canvas/undo/', views_api.CanvasUndoAPI.as_view(), name='api-canvas-undo'),
    # Taste dashboard
    path('admin/taste/', views_admin.TasteDashboardView.as_view(), name='admin-taste'),
    # Canvas
    path('admin/canvas/', views_admin.CanvasAdminView.as_view(), name='admin-canvas'),
]
