# Phase 08: Scale + Polish

## Goal

Harden the product for real use. Handle edge cases, optimize performance, add dark mode for the canvas, write tests, prepare for deployment, and document the project.

---

## Steps

### 8.1 — Edge Cases & Error Handling

#### Public Site

- **Empty festival list**: friendly message + illustration
- **Empty lineup**: "Lineup not yet announced"
- **No recommendations**: "Try selecting more artists for better matches"
- **Artist with missing data**: show limited card with "Info coming soon"
- **Broken import**: admin alert, public sees "Lineup data pending"
- **JavaScript disabled**: static message + link to minimal festival list
- **Offline**: graceful localStorage-based degradation
- **404**: styled page with festival-related joke + search
- **500**: friendly error page with auto-refresh suggestion

#### Admin Canvas

- **5000+ artists**: enforce server-side clustering of distant nodes
- **Concurrent admin edits**: last-write-wins, CanvasMove audit
- **Canvas bounds clamping**: prevent off-screen drags
- **Auto-layout with 0 unplaced**: "Nothing to arrange" message
- **API timeout**: spinner + retry button
- **Node/edge creation conflict**: toast error with details

#### Similarity Engine

- **Artist with no enrichment data**: zero-padded embedding, "low confidence" flag
- **API rate limits (Last.fm/MusicBrainz)**: exponential backoff, failed queue for retry
- **Rate limit warnings**: admin notification when approaching limits
- **Embedding version mismatch**: auto-recompute flag, admin notification
- **Memory on large batches**: process 500 at a time, log progress

### 8.2 — Loading States

- Festival list: skeleton loaders (3 placeholder rows)
- Lineup grid: skeleton cards (6 pulsing placeholders)
- Recommendations: skeleton cards (3 placeholders)
- Canvas initial load: "Loading artist graph..." with progress
- Taste aggregation: "Processing taste patterns..." indicator

### 8.3 — Performance Optimization

#### Database

- Indexes: `Artist.canonical_name`, `LineupSlot.festival_id`, `LineupSlot.artist_id`, `SimilarityEdge.final_score`, `SimilarityEdge(artist_a_id, artist_b_id)`
- `select_related` / `prefetch_related` on API views
- Paginate canvas data; maximum 500 nodes per request
- Batch edge computation: 500 artists at a time

#### Canvas

- `physics: false` always (no simulation)
- `vis.DataSet` (not arrays) for faster updates
- Debounce drag-end API calls (50ms)
- Lazy-load nodes outside viewport for massive graphs
- Server-side edge culling: top 5 edges per node only

#### API

- ETag/Last-Modified on festival list
- Cache recommendations for 5 min per session (same inputs)
- Use Django's `select_for_update` sparingly

#### Frontend

- Lazy-load artist images
- Debounce festival search (200ms)
- Preload lineup data on hover (desktop)

### 8.4 — Dark Mode (Admin Canvas)

Toggle in admin canvas toolbar:

- Stored in `localStorage` as `canvas_theme`
- Dark: background `#1a1a2e`, nodes lighter, edges more luminous
- Light: default clean theme
- Respects `prefers-color-scheme` if no stored preference

### 8.5 — Admin UX Improvements

- **Bulk actions**: select all checkbox for artist lists
- **CSV export**: edge data, artist data, lineup data
- **Improved filters**:
  - Artist admin: by canvas_status, is_anchor, has_embedding, has_edges
  - SimilarityEdge: by score range, source, lock status
  - Festival: by season, active/inactive
- **Inline editing**:
  - Festival admin: inline LineupSlot table
  - Artist admin: read-only SimilarityEdge list with link to canvas

### 8.6 — Tests

`core/tests/test_models.py`:
- All model creation, string methods, unique constraints
- SimilarityEdge artist_a_id < artist_b_id constraint
- LineupSlot multiple slots per artist per festival

`core/tests/test_api.py`:
- Festival list endpoint returns JSON
- Lineup endpoint returns correct structure
- Recommendations endpoint returns sorted results
- Like/unlike/reset endpoints work correctly
- Feedback endpoint stores RecFeedback

`core/tests/test_importers.py`:
- Artist matching: exact, alias, fuzzy, new
- Merge artists transfers records correctly
- CSV import parses correctly

`core/tests/test_similarity.py`:
- Embedding builder creates 50-dim vectors
- Cosine similarity computation
- Top-K edge computation stores correct number
- Locked edges not overwritten

`core/tests/test_taste.py`:
- Lift calculation correct
- Confidence weighting works
- Festival-specific vs global fallback
- Feedback integration

`core/tests/test_recommendations.py`:
- Returns results within festival
- Excludes liked artists
- Returns explanations
- Handles empty liked list

Run: `python manage.py test`

### 8.7 — Deployment Preparation

- `requirements.txt` or `pyproject.toml` with pinned dependencies
- `config/settings/prod.py`:
  - PostgreSQL from env vars
  - `STATIC_ROOT`, `MEDIA_ROOT`
  - `DEBUG=False`, `ALLOWED_HOSTS` from env
  - `SECRET_KEY` from env
- `.env.example` with all required variables:
  - `DJANGO_SECRET_KEY`
  - `DATABASE_URL`
  - `LASTFM_API_KEY` (optional)
  - `CLASHFINDER_USERNAME` (optional)
  - `CLASHFINDER_PUBLIC_KEY` (optional)
- `Dockerfile` (optional)
- `collectstatic` succeeds
- Database migrations verified: `python manage.py makemigrations --check`

### 8.8 — Documentation

`README.md`:

```
# Clashfinder+

A festival lineup discovery tool.

## Setup
1. Clone
2. python -m venv venv
3. pip install -r requirements.txt
4. cp .env.example .env  # configure
5. python manage.py migrate
6. python manage.py seed_test_data
7. python manage.py runserver

## Commands
- import_festivals — import lineup data
- compute_embeddings — build artist embeddings
- compute_edges — compute top-K similarity edges
- auto_place — UMAP auto-placement
- detect_clusters — HDBSCAN clustering
- compute_taste_edges — taste graph aggregation
- prune_taste_data — data retention

## Phases
Phase 00: Feasibility (done)
Phase 01: Scaffold + Models (done)
Phase 02: Public MVP (done)
Phase 03: Importers (done)
Phase 04: Similarity v1 (done)
Phase 05: Taste Graph (done)
Phase 06: Admin Canvas (done)
Phase 07: Advanced Similarity (done)
Phase 08: Scale + Polish (done)
```

### 8.9 — Future Roadmap Section

Update `SPEC.md` future features with implementation-ready notes:

```
## Future Features

### Clash Resolution
When similar artists conflict:
  - Detect same-day/same-time slots with high SimilarityEdge scores
  - Add "Clash Alert" recommendation category
  - Suggest: "If you can't get into Artist X, don't miss Artist Y on Stage Z"

### Time-Decayed Taste
Add exponential decay to TasteEdge:
  - Sessions from last 3 months: 100% weight
  - Sessions from 3-12 months: 70% weight
  - Sessions older than 12 months: 40% weight
  - Configurable half-life

### Collaborative Admin Canvas (Django Channels)
  - WebSocket-based real-time node locking
  - If Admin A is dragging Turnstile, freeze that node for Admin B
  - Node locking state: idle, dragging, locked

### pgvector Migration
When needed:
  - Replace ArtistEmbedding.vector JSONField with pgvector column
  - Use KNN indexing for fast vector search
  - Remove all-vs-all Python computation
  - Migration path: parallel storage, dual writes, cutover

### Spotify Enrichment
When access is available:
  - Add audio features to embedding
  - Add Spotify related artists as SimilarityEdge enrichment
  - Requires API key, terms review, attribution
```

---

## Acceptance Criteria

- [ ] Empty states render correctly for festivals, lineups, recommendations
- [ ] Loading states appear during API calls (skeletons, spinners)
- [ ] 404 and 500 pages styled and friendly
- [ ] Canvas loads quickly with 500 nodes + edges
- [ ] All API endpoints return proper error JSON
- [ ] Admin filters and bulk actions work
- [ ] Dark mode works on admin canvas
- [ ] Tests pass: `python manage.py test`
- [ ] `python manage.py check --deploy` passes
- [ ] `collectstatic` succeeds
- [ ] `.env.example` documents all required variables
- [ ] README explains setup and management commands
- [ ] No console errors in Chrome, Firefox, Safari
