# Phase 07: Advanced Similarity

## Goal

Add full embeddings (replacing MVP-lite version with richer signals), UMAP projection for canvas auto-placement, and HDBSCAN clustering for automatic group detection. This is the deepest algorithmic layer, built on the data and curation from previous phases.

**Note**: This phase does NOT include Spotify audio features or related artists. Those remain future enrichment only.

---

## Steps

### 7.1 — Embedding v2 (Full)

`core/similarity/embeddings.py` — upgrade from MVP-lite:

```
EmbeddingBuilder v2:

1. Tag vector (20 dims)
   - If Last.fm enrichment was run: use Last.fm tag weights
   - Fallback: admin genre_tags from Artist model
   - Normalized to unit vector

2. Anchor affinity vector (20 dims)
   - Jaccard similarity against each active anchor artist
   - Same as v1

3. Festival metadata (2 dims)
   - [log(n_festivals + 1) / log(max_festivals + 1), is_anchor]
   - Same as v1

4. Manual edge profile (8 dims)
   - For 8 broad regions: average edge score to artists in that region
   - Regions defined by admin (configurable, defaults):
     metal, hardcore, indie/alt, electronic, pop, hiphop, rock, heritage
   - Same as v1

= 50 dims

- embedding_schema_version = "v2.0"
- anchor_set_hash = hash of current active AnchorSet
- source_summary = "admin+lastfm+anchor+manual" (or subset if Last.fm wasn't run)
```

### 7.2 — UMAP Projection

`core/similarity/projection.py`:

```python
class CanvasProjector:
    def __init__(self, n_neighbors=15, min_dist=0.1):
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist

    def project_all(self, artist_ids: list[int] = None) -> dict[int, tuple]:
        """Project all artists (or specified subset) to 2D using UMAP.

        Uses ArtistEmbedding.vector (base_score only, no canvas_score).

        Returns: {artist_id: (x_normalized, y_normalized)}
        Positions normalized to [-1.0, 1.0].
        """

    def project_new(self, artist: Artist) -> tuple:
        """Project a single new artist using existing UMAP model.
        Uses transform(), not fit().
        """

    def auto_place_unplaced(self):
        """Find all artists with canvas_status='unplaced',
        project them, set canvas_x, canvas_y, canvas_status='auto'.

        Skips artists with canvas_status='manual' or 'locked'.
        """
```

Requirements: `umap-learn` package.

### 7.3 — HDBSCAN Clustering

`core/similarity/clustering.py`:

```python
class ClusterDetector:
    def __init__(self, min_cluster_size=5, min_samples=2):
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples

    def detect_clusters(self, artist_ids: list[int] = None) -> dict:
        """Run HDBSCAN on artist embeddings.

        Returns: {
            clusters: {
                cluster_id: {
                    artist_ids: [...],
                    membership_strengths: {artist_id: 0.95, ...},
                    centroid_embedding: [...]
                }
            },
            noise: [artist_ids not in any cluster],
            hierarchy: [...]
        }
        """

    def detect_subclusters(self, parent_cluster: Cluster) -> list[Cluster]:
        """Run HDBSCAN on just the artists in a cluster to find sub-clusters.
        Creates child Cluster records with parent=parent_cluster.
        """

    def name_cluster(self, artist_ids: list[int]) -> str:
        """Generate descriptive name from most common tags and top artists."""
        # e.g. "Alt-Metal / Modern Metal (Deftones, Slipknot, Korn)"

    def update_models(self, results: dict):
        """Sync detection results to Cluster and ArtistCluster models."""
```

Requirements: `hdbscan` package.

### 7.4 — Auto-Placement Management Command

`core/management/commands/auto_place.py`:

```
python manage.py auto_place [--all] [--festival-id=N]

Logic:
  - Get artists to place (all unplaced, or by festival)
  - Run UMAP projection
  - Set canvas_x, canvas_y, canvas_status='auto'
  - Flag: do not overwrite 'manual' or 'locked' artists
  - Print summary: placed, skipped, errors
```

### 7.5 — Cluster Detection Management Command

`core/management/commands/detect_clusters.py`:

```
python manage.py detect_clusters [--min-size=5] [--recompute]

Logic:
  - Run HDBSCAN on all artists with embeddings
  - Create/update Cluster records
  - Create/update ArtistCluster records
  - Generate cluster names
  - Detect sub-clusters recursively (up to 3 levels deep)
  - Print summary: clusters found, artists clustered, noise points
```

### 7.6 — Embedding Recompute Management Command

`core/management/commands/compute_embeddings.py` (upgrade):

```
python manage.py compute_embeddings [--artist-id=N] [--all] [--version=v2.0]

Logic:
  - Build v2 embeddings for specified artists
  - Set embedding_schema_version and anchor_set_hash
  - Flag: if embedding_schema_version changed, mark existing edges for recompute
```

### 7.7 — Canvas Auto-Layout Upgrade

Update the canvas `/api/admin/canvas/auto-layout/` endpoint:

- If UMAP model exists and artists have embeddings: use UMAP
- If UMAP not available: fall back to simple force-directed layout
- Base contract maintained: uses `base_score` only, never `final_score`
- Skips locked/manual artists

### 7.8 — Canvas Cluster Integration

Update `static/js/admin-canvas.js`:

```
Cluster rendering:
  - Load cluster data from /api/admin/canvas-data/
  - Draw colored convex hull polygons behind each cluster's nodes
  - Sub-clusters appear at deeper zoom levels (threshold-based)
  - Legend in bottom-right corner: color swatch + cluster name
  - Noise points (unclustered) rendered in gray
  - Click cluster label to select all its members

Admin actions:
  - Right-click cluster → [Rename] [Merge] [Split] [Delete]
  - Drag artist from one cluster region to another → membership recalculated
  - [Lock cluster] → prevent auto-reassignment of member artists
```

### 7.9 — Admin Cluster Management

`core/views_admin.py`:

```
ClusterListView(ListView):
  model = Cluster
  template_name = "admin/clusters.html"
  - List with member count, parent, color, description
  - Sortable, searchable

ClusterEditView(UpdateView):
  model = Cluster
  fields = ["name", "parent", "color", "description"]
  template_name = "admin/cluster_edit.html"
  - Show member artists in grid
  - [Merge with...] select another cluster
  - [Split] multi-select artists → new sub-cluster
  - [Recompute] re-run HDBSCAN on just this cluster's artists
```

---

## Acceptance Criteria

- [ ] Embedding v2 creates 50-dim vectors with richer signal sources
- [ ] embedding_schema_version and anchor_set_hash are set correctly
- [ ] UMAP projection produces sensible 2D positions (similar artists cluster)
- [ ] Manual and locked canvas positions survive auto-place
- [ ] HDBSCAN detects meaningful clusters from embeddings
- [ ] Sub-clusters are detected within larger clusters
- [ ] Cluster names are generated from tag/artist data
- [ ] Canvas displays cluster halos with correct coloring
- [ ] Admin can rename, merge, split clusters
- [ ] Dragging an artist between clusters updates membership
- [ ] `auto_place` processes 200 artists in under 2 minutes
- [ ] `detect_clusters` processes 500 artists in under 30 seconds
