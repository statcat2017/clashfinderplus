# Clashfinder+ — Specification

## Product Overview

A Django-based website that helps festival-goers discover artists they'll enjoy based on who else is playing the same festival. Users browse a lineup, tap to like artists, and get recommendations of other acts on that lineup they should check out.

The core product is a **three-layer artist similarity graph**: curated (human), cultural (anonymous co-selection), and musical (external data). The admin can manually place artists on a spatial similarity canvas to encode editorial judgement, and the system learns from user taste patterns over time.

**Current phase**: MVP-first build. Prove the user loop before building the graph brain.

**Brand note**: "Clashfinder+" is an internal codename only. A distinct public name will be chosen before launch.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Django 5.x |
| Database | PostgreSQL (prod), SQLite (dev) |
| Import | Clashfinder API (primary), BeautifulSoup (fallback), CSV (manual) |
| Similarity | numpy + scikit-learn (cosine, UMAP, HDBSCAN) |
| Admin Canvas | vis.js Network (vanilla JS) |
| Frontend | Django templates + vanilla JS + clean minimal CSS |
| Deploy | Docker (optional) |

---

## Data Models

### Festival

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| name | CharField(200) | e.g. "Glastonbury 2026" |
| slug | SlugField | unique, for URL |
| website | URLField | official festival site |
| clashfinder_url | URLField(blank) | Clashfinder page URL |
| start_date | DateField | |
| end_date | DateField | |
| location | CharField(200) | city/county |
| image_url | URLField(blank) | festival poster/logo |
| is_active | BooleanField | default True |
| created_at | DateTimeField | auto |

### Artist

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| name | CharField(200) | as imported originally |
| canonical_name | CharField(200) | deduplicated master name |
| canvas_x | FloatField(default=0) | normalized -1.0 to 1.0 |
| canvas_y | FloatField(default=0) | normalized -1.0 to 1.0 |
| canvas_status | CharField(20, choices) | `unplaced`, `auto`, `manual`, `locked` |
| is_anchor | BooleanField(default=False) | one of ~25 landmark artists |
| genre_tags | JSONField(default=list) | `["metal", "shoegaze", ...]` curated by admin |
| image_url | URLField(blank) | artist photo |
| last_imported | DateTimeField(null) | |
| created_at | DateTimeField | auto |

### ArtistAlias

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| artist | FK(Artist) | canonical artist |
| alias | CharField(200) | alternative name from imports |
| source | CharField(20) | `scrape`, `import`, `admin` |
| created_at | DateTimeField | auto |
| unique_together = (artist, alias) |

### ArtistIdentifier

External IDs moved out of the Artist model for cleaner dedup.

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| artist | FK(Artist) | |
| source | CharField(20) | `musicbrainz`, `lastfm`, `spotify`, `wikidata`, `songkick` |
| external_id | CharField(200) | |
| url | URLField(blank) | |
| confidence | FloatField(default=1.0) | how reliable this match is |
| created_at | DateTimeField | auto |
| unique_together = (source, external_id) |

### LineupSlot

Replaces FestivalLineup. Allows multiple slots per artist per festival (DJ sets, guest appearances, secret sets, cancellations).

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| festival | FK(Festival) | |
| artist | FK(Artist) | |
| stage | CharField(100, blank) | e.g. "Pyramid Stage" |
| day | IntegerField(null, blank) | 0-indexed or date-based |
| start_time | TimeField(null, blank) | |
| end_time | TimeField(null, blank) | |
| slot_name | CharField(200, blank) | e.g. "DJ Set", "Acoustic Session" |
| position | IntegerField(default=0) | ordering on lineup poster |
| status | CharField(20, choices) | `confirmed`, `rumoured`, `cancelled`, `tbc` |
| raw_label | CharField(200, blank) | original text from source (e.g. "Special Guest") |
| source_url | URLField(blank) | |
| source_ref | CharField(100, blank) | internal reference to import run |
| created_at | DateTimeField | auto |
| updated_at | DateTimeField | auto |

### AnchorSet

Versioned collection of anchor artist definitions.

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| name | CharField(200) | e.g. "V1 UK Festival Anchors" |
| version | IntegerField | incremented on change |
| is_active | BooleanField(default=True) | |
| description | TextField(blank) | |
| created_at | DateTimeField | auto |

### AnchorArtist

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| anchor_set | FK(AnchorSet) | |
| artist | FK(Artist) | |
| role | CharField(100, blank) | e.g. "genre", "scene", "era", "crossover" |
| x_normalized | FloatField | -1.0 to 1.0 |
| y_normalized | FloatField | -1.0 to 1.0 |
| is_locked | BooleanField(default=True) | anchors are fixed |
| created_at | DateTimeField | auto |
| unique_together = (anchor_set, artist) |

### ArtistSignal

Raw signal data from external sources (cached for re-parse without re-fetch).

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| artist | FK(Artist) | |
| source | CharField(20) | `lastfm`, `musicbrainz`, `admin` |
| key | CharField(100) | e.g. "tag:metal", "tag:alternative" |
| value | FloatField | normalized 0-1 |
| confidence | FloatField(default=1.0) | |
| created_at | DateTimeField | auto |
| unique_together = (artist, source, key) |

### RawExternalData

Raw JSON payloads from external API calls. Allows re-parsing without re-fetching, saving rate limits.

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| artist | FK(Artist) | |
| source | CharField(20) | `lastfm`, `musicbrainz`, `spotify` |
| endpoint | CharField(100) | e.g. "artist.getTopTags" |
| raw_data | JSONField | the raw API response |
| fetched_at | DateTimeField | auto |
| expires_at | DateTimeField | null = cache indefinitely |

### ArtistEmbedding

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| artist | FK(Artist, unique) | |
| version | IntegerField | |
| embedding_schema_version | CharField(20) | e.g. "v1.0" |
| anchor_set_hash | CharField(64, blank) | hash of anchor set used |
| vector | JSONField | 50-dim float array |
| source_summary | CharField(100) | e.g. "lastfm+cooccur+admin" |
| generated_at | DateTimeField | auto |

### SimilarityEdge

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| artist_a | FK(Artist, related_name="sim_a") | always lower ID |
| artist_b | FK(Artist, related_name="sim_b") | |
| tag_score | FloatField(null, blank) | 0-1 |
| audio_score | FloatField(null, blank) | 0-1 (future — not MVP) |
| cooccurrence_score | FloatField(null, blank) | 0-1 |
| canvas_score | FloatField(null, blank) | 0-1 |
| cultural_affinity_score | FloatField(null, blank) | 0-1 |
| manual_score | FloatField(null, blank) | 0-1 |
| final_score | FloatField() | weighted combination |
| is_locked | BooleanField(default=False) | survives recompute |
| explanation | TextField(blank) | admin-curated "why" |
| model_version | CharField(50, blank) | which model/weights version |
| weights_version | CharField(50, blank) | which weight config |
| source_snapshot_id | CharField(50, blank) | which data snapshot |
| computed_at | DateTimeField(null) | |
| is_active | BooleanField(default=True) | |
| created_at | DateTimeField | auto |
| updated_at | DateTimeField | auto |

unique_together = (artist_a, artist_b). Constraint: `artist_a_id < artist_b_id`.

### Cluster

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| name | CharField(200) | |
| parent | FK(Cluster, null, blank) | hierarchical sub-clusters |
| anchor_artist | FK(Artist, null, blank) | representative |
| color | CharField(7) | hex color |
| description | TextField(blank) | |
| created_at | DateTimeField | auto |

### ArtistCluster

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| artist | FK(Artist) | |
| cluster | FK(Cluster) | |
| strength | FloatField(default=1.0) | membership strength |
| created_at | DateTimeField | auto |
| unique_together = (artist, cluster) |

### CanvasMove

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| artist | FK(Artist) | |
| old_x | FloatField | |
| old_y | FloatField | |
| new_x | FloatField | |
| new_y | FloatField | |
| admin_user | FK(User) | |
| created_at | DateTimeField | auto |

### TasteSession

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| session_id | UUIDField | anonymous browser session |
| festival | FK(Festival) | |
| created_at | DateTimeField | auto |

### TasteSelection

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| session | FK(TasteSession) | |
| artist | FK(Artist) | |
| selected_at | DateTimeField | auto |
| unique_together = (session, artist) |

### TasteEdge

Directional smoothed lift edge. Replaces non-directional UserTasteEdge.

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| source_artist | FK(Artist, related_name="taste_source") | |
| target_artist | FK(Artist, related_name="taste_target") | |
| festival | FK(Festival, null, blank) | null = global |
| raw_lift | FloatField | |
| smoothed_lift | FloatField | Bayesian-smoothed |
| confidence | FloatField | 0-1, based on sample size |
| sample_size | IntegerField | number of co-selections |
| created_at | DateTimeField | auto |
| updated_at | DateTimeField | auto |

unique_together = (source_artist, target_artist, festival)

### RecFeedback

User feedback on recommendation cards.

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| session | FK(TasteSession) | |
| recommended_artist | FK(Artist) | |
| liked_artists | JSONField | snapshot of what they'd liked |
| feedback | CharField(20) | `good_shout`, `not_for_me`, `already_know` |
| created_at | DateTimeField | auto |

### ScrapeLog

| Field | Type | Notes |
|---|---|---|
| id | AutoField | |
| festival | FK(Festival) | |
| importer_type | CharField(20) | `clashfinder_api`, `clashfinder_html`, `csv`, `manual` |
| timestamp | DateTimeField | auto |
| artists_found | IntegerField | |
| artists_new | IntegerField | |
| artists_updated | IntegerField | |
| errors | TextField(blank) | |
| status | CharField(20) | `success`, `partial`, `failed` |

---

## Similarity Engine — The Three Graphs

### 1. Curated Graph (admin-defined)

Built from:
- Manual `SimilarityEdge` entries with `manual_score`
- Admin-defined genre tags
- Canvas spatial proximity (`canvas_score`)
- Anchor affinity overlap

This graph exists before any external API calls or ML. It is the seed intelligence.

### 2. Cultural Graph (anonymous co-selection)

Built from anonymous `TasteSelection` data. No accounts. No personal data.

**Lift with Bayesian smoothing**:

```
raw_lift = P(target | source) / P(target)
# Where:
#   P(target) = sessions_with_target / total_sessions
#   P(target | source) = sessions_with_both / sessions_with_source

confidence = sample_size / (sample_size + 20)
smoothed_lift = 1 + ((raw_lift - 1) * confidence)
```

Minimum sample size: 10 co-selections before lift is stored. Festival-specific edges preferred; global edges as fallback when festival-specific confidence is low.

### 3. Musical Graph (external data, optional enrichment)

Built from:
- Last.fm tag overlap (terms-dependent, non-commercial if not approved)
- Festival co-occurrence (Jaccard similarity)
- MusicBrainz genre metadata

**Spotify is NOT in the MVP.** Audio features and related artists are removed from the core similarity pipeline. If Spotify access is available and permitted later, it becomes optional enrichment.

### Combined Final Score

Stored as `SimilarityEdge.final_score`. Default weights (MVP before external enrichment):

```
final_score =
  manual_score      × 0.40  (admin-defined edges)
  tag_score         × 0.25  (admin tags + optional enrichment)
  canvas_score      × 0.25  (admin spatial placement)
  cooccurrence      × 0.10  (shared festivals)
```

When external enrichment is added later:

```
final_score =
  manual_score      × 0.30
  canvas_score      × 0.20
  tag_score         × 0.20
  cultural_affinity × 0.15
  cooccurrence      × 0.10
  audio_score       × 0.05  (future — Spotify)
```

Null components have their weight redistributed proportionally. Locked edges are never overwritten.

### Top-K Edge Storage

Not all-vs-all. Store only the top **K=20** most similar pairs per artist, plus any manual or locked edges.

This avoids O(N²) explosion and keeps the database lean.

---

## Canvas Circularity Contract

Critical: auto-layout and recommendation scoring must not create a feedback loop.

```
base_score = manual tags + admin tag overlap + optional external enrichment
  (used by auto-layout to generate initial positions)

canvas_score = human spatial curation only
  (derived from admin-placed canvas positions)

cultural_affinity_score = anonymous user co-selection lift

manual_score = explicit admin edge overrides

final_recommendation_score = base_score + canvas_score + cultural + manual
  (used by public recommendations only, NOT by auto-layout)
```

**Rules**:
1. Auto-layout (UMAP) uses `base_score` only — never `final_score`.
2. Canvas drag updates `canvas_score` but does NOT feed back into auto-layout.
3. Locked/manual nodes survive auto-layout entirely.
4. `final_score` is for recommendations, not layout generation.

---

## Artist Embedding (50-dim, MVP-lite)

Until external enrichment is added, embeddings use:

```
admin_tag_vector      × 20 dims  (normalized 0-1 from genre_tags)
cooccurrence_profile  × 20 dims  (overlap against each anchor)
festival_count        × 1 dim    (logged, normalized)
is_anchor             × 1 dim    (binary)
manual_edge_density   × 8 dims   (how strongly connected to each region)
= 50 dims total
```

When Last.fm enrichment is added later, `admin_tag_vector` is replaced by `lastfm_tag_vector`.

### Coordinate Normalization

Canvas positions are stored as normalized floats `[-1.0, 1.0]`, not raw pixel values. The frontend scales them to viewport coordinates. This keeps spatial relationships stable across screen sizes and zoom levels.

---

## Anchor System

Anchors are landmark artists that define the topology of the similarity space. They are stored as `AnchorSet` + `AnchorArtist` records.

### Suggested Initial Anchors (V1, ~25 artists)

```
Metal/heavy: Slipknot, Metallica, Deftones
Hardcore/punk cross: Turnstile, IDLES
Indie/alt: Radiohead, Arctic Monkeys, Fontaines D.C., The Cure
Electronic/rave: The Prodigy, Aphex Twin, Bicep, Fred again.., Skrillex
Pop/mainstream: Taylor Swift, Beyoncé, Charli XCX, Lana Del Rey
Hip-hop/rap: Kendrick Lamar, Tyler the Creator, Stormzy
Rock: Foo Fighters, Queens of the Stone Age
Heritage: The Rolling Stones, Paul McCartney
```

Anchors are NOT genres. They are landmarks. Turnstile sits between hardcore, alt-metal, and festival-mainstream crossover. The Prodigy sits between electronic and metal-culture crossover.

### Anchor Affinity Overlap

For any non-anchor artist:

```
anchor_affinity_vector = [overlap_with_anchor_1, overlap_with_anchor_2, ..., overlap_with_anchor_N]
```

Where overlap is Jaccard similarity of their festival appearances. This forms 20 of the 50 embedding dimensions.

---

## Recommendation Endpoint

### Request

```json
POST /api/recommendations/
{
  "session_id": "uuid",
  "festival_id": 5,
  "liked_artist_ids": [1, 32, 44],
  "max_results": 10
}
```

### Algorithm (MVP Phase 2 — before embeddings)

```
1. Get all SimilarityEdge where:
   - artist_a IN liked_ids AND artist_b is on this festival lineup
   - OR artist_b IN liked_ids AND artist_a is on this festival lineup
2. Aggregate per candidate artist:
   score = average(final_score across all edges to liked artists)
3. Deduplicate, ensure not in liked_ids
4. Apply minimum threshold (score > 0.15)
5. Sort descending
6. Return top max_results with explanation
```

### Algorithm (Phase 4+ — with embeddings)

```
1. Compute taste centroid = average(embedding of liked artists)
2. For each candidate on festival:
   centroid_similarity = cosine(candidate_embedding, centroid)
   edge_score = average SimilarityEdge.final_score to liked artists
   combined = centroid_score × 0.4 + edge_score × 0.6
3. Apply bonus:
   - festival_context_bonus (same day/stage = +0.05)
   - novelty_bonus (less popular = up to +0.10)
   - cluster_bridge_bonus (connects liked clusters = +0.10)
4. Score = combined × 0.80 + bonuses × 0.20
5. Return top results with explanations
```

### Response

```json
{
  "recommendations": [
    {
      "artist": {"id": 88, "name": "Korn"},
      "score": 0.89,
      "reason": {
        "type": "shared_tags",
        "because_of": ["Slipknot", "Deftones"],
        "evidence": ["nu-metal", "alternative metal", "Main Stage"]
      }
    }
  ]
}
```

Keys:
- `reason.type`: `shared_tags`, `similar_artist`, `cultural_affinity`, `clash_resolution`, `curated_pick`
- `reason.because_of`: which liked artists drove this recommendation
- `reason.evidence`: human-readable explanation fragments

---

## Recommendation Feedback

Every recommendation card includes:

```
[Good shout] [Not for me] [Already know them]
```

This is POSTed to `/api/feedback/` and stored in `RecFeedback`. This data is used to:
- Improve lift calculations (a "Good shout" is stronger than a passive like)
- Downrank artists that users reject
- Surface artists users already know (they may need deeper cuts)

---

## Pages & Routes

### Public Site

| URL | View | Description |
|---|---|---|
| `/` | `home` | Festival list (left) + lineup (right on desktop, full-width on mobile) |
| `/privacy` | `privacy` | Privacy notice, data retention, reset taste profile |

### API

| URL | Method | Description |
|---|---|---|
| `/api/festivals/` | GET | Active festivals |
| `/api/festivals/<id>/lineup/` | GET | Full lineup |
| `/api/recommendations/` | POST | Get recommendations |
| `/api/taste/like/` | POST | Like an artist |
| `/api/taste/unlike/` | POST | Unlike an artist |
| `/api/feedback/` | POST | Rec feedback (good_shout/etc) |
| `/api/taste/reset/` | POST | Delete this session's taste data |

### Admin

| URL | Description |
|---|---|
| `/admin/` | Standard Django admin |
| `/admin/import/` | Import controls (triggers + logs) |
| `/admin/dedup/` | Duplicate artist merge tool |
| `/admin/tags/` | Bulk tag editor |
| `/admin/canvas/` | Similarity canvas (Phase 6) |
| `/admin/taste/` | Taste data dashboard (Phase 5) |

---

## Privacy

**Not "no consent needed".** Privacy-respecting by design, but transparent.

- Anonymous session UUID stored in `localStorage` — not a cookie, but still persistent browser storage used to build preference profiles
- **Privacy notice** displayed on first visit (`/privacy` page + banner)
- **Reset button** in UI: "Delete my local taste profile" — clears `session_id` and POSTs to `/api/taste/reset/`
- **Retention**: raw `TasteSession`/`TasteSelection` rows purged after 180 days
- **Aggregation only**: `TasteEdge` and `RecFeedback` persist without direct session identifiers
- **Lawful basis**: legitimate interest with clear opt-out. If required by jurisdiction, add consent mechanism.
- No IP logged with taste data
- No personal data collected or stored

---

## Import Strategy (Replaces "Scraper")

The system supports four import methods, tried in order:

1. **Clashfinder API** — authenticated API call, structured data
2. **Clashfinder HTML** — BeautifulSoup fallback if API unavailable
3. **CSV import** — structured file upload via admin
4. **Manual admin entry** — inline form for individual slots

Module: `lineup_importers/` — not `scraper/`.

Each importer produces `LineupSlot` records and a `ScrapeLog` entry.

---

## Development Phases

| Phase | Name | Purpose |
|---|---|---|
| 00 | Feasibility Spike | Validate riskiest assumptions before committing to architecture |
| 01 | Scaffold + Data Models | Django project + all models + admin registration |
| 02 | Public MVP | One festival, manual data, hearts, simple recs |
| 03 | Importers + Admin Tools | Repeatable lineup ingestion, dedup, tagging |
| 04 | Similarity Engine v1 | Last.fm/MusicBrainz enrichment, top-K edges, explanations |
| 05 | Taste Graph | Anonymous sessions, directional lift, feedback, privacy controls |
| 06 | Admin Canvas | vis.js curation graph |
| 07 | Advanced Similarity | Embeddings, UMAP, HDBSCAN clustering |
| 08 | Scale + Polish | Performance, testing, deployment, docs |

---

## Future Features (Post-MVP, Not in Current Scope)

### Clash Resolution (from clashfinder's core purpose)
If two highly similar artists play at the same time, suggest: "If you can't get into Artist X, try Artist Y on Stage Z."

### Time-Based Cultural Decay
Older `TasteEdge` data weighted less than recent data using exponential decay factor.

### Collaborative Admin Canvas
Django Channels for real-time multi-admin node locking and collaborative curation.

### pgvector Migration
If artist count exceeds ~2,000 or live vector search becomes necessary, migrate `ArtistEmbedding.vector` from JSONField to pgvector.

### Spotify Enrichment
If Spotify API access is available and permitted, add `audio_score` and `spotify_related` to the similarity pipeline.

---

## Key Design Decisions (Updated)

1. **Canvas is an editor, not the source of truth.** `SimilarityEdge` and `ArtistEmbedding` are canonical. The canvas is a 2D projection. Auto-layout uses `base_score` only, not `final_score`, to prevent feedback loops.

2. **Top-K edges, not all-vs-all.** Store only the 20 strongest edges per artist. Prevents O(N²) scaling issues.

3. **Normalized coordinates.** Canvas positions stored in `[-1.0, 1.0]`, not pixels. Stable across viewport sizes.

4. **Directional smoothed taste edges.** Lift is directional. Bayesian smoothing prevents inflated scores from small samples.

5. **Recommendations within the current festival only (MVP).** The graph is global; the query filters to the current lineup. V2 can suggest outside.

6. **No user accounts.** Anonymous sessions via localStorage. Transparent privacy notice + reset.

7. **Human curation before algorithms.** Boring admin tables first. Canvas comes later. The recommendation loop works with manual data only.

8. **Explanations from day one.** Every recommendation includes `reason.type`, `because_of`, and `evidence`. Users trust "why" more than percentages.

9. **Feedback signals are different from passive likes.** Explicit "Good shout" / "Not for me" / "Already know them" buttons provide richer training data.

10. **Spotify is not in the MVP.** Dependencies on external audio features and related artists are removed from the core pipeline. Optional enrichment only if terms permit.
