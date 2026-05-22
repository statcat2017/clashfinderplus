# Phase 04: Similarity Engine v1

## Goal

Add optional MusicBrainz and Last.fm enrichment to the similarity pipeline. Build the top-K similarity edge computation. Upgrade the recommendation endpoint to use centroid scoring. Add explanation generation. This phase makes the recommendations smarter without depending on Spotify.

**Note**: Last.fm enrichment is optional and terms-dependent. If Last.fm is not usable, the engine works on admin tags + festival co-occurrence only.

---

## Steps

### 4.1 — External API Clients

`core/similarity/musicbrainz.py`:

```python
class MusicBrainzClient:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent

    def search_artist(self, name: str) -> dict | None:
        """Search MusicBrainz for an artist.

        Returns first match with: id, name, type, country, tags, genres.
        """

    def get_artist_tags(self, mbid: str) -> list[dict]:
        """Get tags/genres for a MusicBrainz artist ID.
        Returns: [{name, count}]
        """

    def get_artist_aliases(self, mbid: str) -> list[str]:
        """Get known aliases for dedup."""
```

`core/similarity/lastfm.py`:

```python
class LastFMClient:
    API_URL = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_top_tags(self, artist_name: str) -> dict[str, float]:
        """Fetch top tags. Returns {tag: weight} normalized 0-1.
        Empty dict on 404/missing. Rate-limited to 1 req/sec.
        """
```

Store `LASTFM_API_KEY` in environment variables. Respect rate limits with `time.sleep(1)` between calls.

### 4.2 — RawExternalData Pipeline

On enrichment fetch, always store the raw response:

```
RawExternalData.objects.update_or_create(
    artist=artist,
    source="musicbrainz",
    endpoint="artist/search",
    defaults={"raw_data": response}
)
```

This allows re-running embedding computation without re-hitting APIs.

### 4.3 — Embedding Builder (MVP-lite, 50-dim)

`core/similarity/embeddings.py`:

```python
class EmbeddingBuilder:
    def build_embedding(self, artist: Artist) -> ArtistEmbedding:
        """
        1. Admin tag vector (20 dims)
           - From Artist.genre_tags (admin-curated)
           - If Last.fm available: merge with Last.fm tags
           - Normalize to unit vector

        2. Anchor affinity vector (20 dims)
           - For each active anchor artist:
             - Jaccard similarity: festivals(artist) ∩ festivals(anchor)
               / festivals(artist) ∪ festivals(anchor)
           - 20-dim vector of anchor affinities

        3. Festival metadata (2 dims)
           - [log(n_festivals + 1) / log(max_festivals + 1), is_anchor]

        4. Manual edge density (8 dims)
           - How strongly connected to each of 8 broad regions
           - Regions: metal, hardcore, indie, electronic, pop, hiphop, rock, heritage
           - Score = average SimilarityEdge.final_score to artists in that region

        5. Concatenate → 50-dim
        6. L2 normalize
        """
```

### 4.4 — Top-K Edge Computer

`core/similarity/edges.py`:

```python
class EdgeComputer:
    K = 20  # store top K edges per artist
    MIN_SCORE = 0.05
    STORE_THRESHOLD = 0.10

    def compute_edges_for_artist(self, artist: Artist):
        """Compute and store top-K edges for a single artist.

        1. Get all other artists with embeddings
        2. Compute cosine similarity
        3. Keep top K results above STORE_THRESHOLD
        4. Update/create SimilarityEdge records:
           - Set component scores (tag, cooccurrence, etc.)
           - Compute final_score using weight formula
           - Don't overwrite: manual_score, is_locked
        5. Remove existing edges below threshold (unless manual/locked)
        """

    def compute_all_edges(self, artists: QuerySet = None):
        """Batch version. Process in chunks of 500 to manage memory."""

    def _score_by_region(self, artist: Artist, region_artists: QuerySet) -> float:
        """Average edge score to artists in a given region."""
```

### 4.5 — Anchor Affinity Computation

`core/similarity/anchors.py`:

```python
class AnchorService:
    def get_active_anchors(self) -> list[Artist]:
        """Get currently active anchor artists from active AnchorSet."""

    def compute_affinity_vector(self, artist: Artist) -> list[float]:
        """Compute anchor affinity for an artist.

        For each active anchor:
          shared = len(festivals(artist) ∩ festivals(anchor))
          total = len(festivals(artist) ∪ festivals(anchor))
          affinity = shared / total if total > 0 else 0

        Returns 20-dim float vector.
        """

    def get_anchor_set_hash(self) -> str:
        """Hash of current active anchor set for embedding versioning."""
```

### 4.6 — Recommendation Upgrade

Update `core/views_api.py` `RecommendationsAPI`:

```python
class RecommendationsAPI(View):
    def post(self, request):
        liked_ids = request.body.liked_artist_ids

        # Phase 4+: use centroid similarity
        liked_embeddings = ArtistEmbedding.objects.filter(artist_id__in=liked_ids)
        centroid = average(liked_embeddings)

        candidates = LineupSlot.objects.filter(
            festival_id=festival_id, status="confirmed"
        ).exclude(artist_id__in=liked_ids)

        results = []
        for slot in candidates:
            emb = slot.artist.embedding
            centroid_sim = cosine(emb.vector, centroid)

            # Pre-computed edge score
            edges = SimilarityEdge.objects.filter(
                Q(artist_a=liked_id, artist_b=slot.artist)
                | Q(artist_a=slot.artist, artist_b=liked_id)
                for liked_id in liked_ids
            )
            avg_edge = edges.aggregate(Avg("final_score"))["final_score__avg"] or 0

            combined = centroid_sim * 0.4 + avg_edge * 0.6

            # Apply bonuses
            # ...

            results.append((combined, slot))

        # Sort, deduplicate, return top N
```

### 4.7 — Explanation Generation

`core/similarity/explanations.py`:

```python
class ExplanationGenerator:
    def generate(self, artist: Artist, liked_artists: list[Artist]) -> dict:
        """Generate recommendation explanation.

        Logic:
        1. Check shared admin tags → type: "shared_tags"
        2. Check strong SimilarityEdge → type: "similar_artist"
        3. Check TasteEdge cultural affinity → type: "cultural_affinity"
        4. Check curated (manual_score > 0) → type: "curated_pick"

        Returns: {type, because_of: [artist_names], evidence: [strings]}
        """
```

Evidence examples:
- `"similar sound to Deftones, Turnstile"`
- `"same genre: alternative metal"`
- `"fans of your picks also like this"`
- `"curated pick — recommended by our editors"`

### 4.8 — Management Commands

`core/management/commands/enrich_artists.py`:

```
python manage.py enrich_artists [--artist-id=N] [--all] [--sources=musicbrainz,lastfm]

Logic:
  - For each artist:
    - Search MusicBrainz → store identifier, aliases, tags
    - If Last.fm: search + fetch tags
    - Update ArtistSignal records
    - Store RawExternalData
  - Print summary: enriched, skipped, errors, rate limit waits
```

`core/management/commands/compute_embeddings.py`:

```
python manage.py compute_embeddings [--artist-id=N] [--all]

Logic:
  - Build ArtistEmbedding for specified artists
  - Set embedding_schema_version, anchor_set_hash
```

`core/management/commands/compute_edges.py`:

```
python manage.py compute_edges [--artist-id=N] [--all] [--k=20]

Logic:
  - Compute top-K edges per artist
  - Skip locked edges
  - Set model_version, weights_version, source_snapshot_id, computed_at
```

`core/management/commands/update_similarity.py`:

```
python manage.py update_similarity [--all] [--artist-id=N]
Runs: enrich + compute_embeddings + compute_edges
```

### 4.9 — Signal for New Artists

```python
@receiver(post_save, sender=Artist)
def on_artist_created(sender, instance, created, **kwargs):
    if created:
        # Queue enrichment + embedding + edges
        update_similarity_for_artist.delay(instance.id)
```

For MVP, use synchronous call or simple task queue (Django-Q, Huey, or Celery).

---

## Acceptance Criteria

- [ ] MusicBrainz client searches artists and stores identifiers
- [ ] Last.fm client (if used) fetches tags with rate limit respect
- [ ] RawExternalData stores raw API responses
- [ ] Embedding builder creates 50-dim vectors from admin tags + anchor affinity
- [ ] Top-K edge computer stores only the strongest K edges per artist
- [ ] `compute_edges` does not overwrite locked edges
- [ ] Recommendation endpoint uses centroid + edge scoring
- [ ] Explanations are generated with type, because_of, evidence
- [ ] `enrich_artists` runs without crashing on missing data
- [ ] `update_similarity` runs full pipeline end-to-end
- [ ] 100 artists process in under 5 minutes (respecting rate limits)
