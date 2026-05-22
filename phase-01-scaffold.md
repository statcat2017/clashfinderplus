# Phase 01: Django Scaffold + Data Models

## Goal

Set up the Django project, define all data models with the reviewed changes (LineupSlot, ArtistIdentifier, directional TasteEdge, AnchorSet, etc.), register everything in the admin, and seed initial data.

---

## Steps

### 1.1 — Project Setup

```bash
django-admin startproject config .
python manage.py startapp core
```

Settings:
- SQLite for dev, PostgreSQL configurable for prod
- `INSTALLED_APPS`: `core`, `django.contrib.admin`
- Static files from `static/`
- Templates in `templates/`
- Environment variables via `python-decouple` or `django-environ`

### 1.2 — Define Models

Create all models in `core/models.py`:

- **Festival**: name, slug (unique), website, clashfinder_url (blank), start_date, end_date, location, image_url (blank), is_active (default True), created_at
- **Artist**: name, canonical_name, canvas_x (default 0), canvas_y (default 0), canvas_status (choices: unplaced/auto/manual/locked), is_anchor (default False), genre_tags (JSONField default list), image_url (blank), last_imported (nullable), created_at
- **ArtistAlias**: artist (FK), alias, source (CharField 20), created_at — unique_together = (artist, alias)
- **ArtistIdentifier**: artist (FK), source (CharField 20: musicbrainz/lastfm/spotify/wikidata/songkick), external_id, url (blank), confidence (FloatField default 1.0), created_at — unique_together = (source, external_id)
- **LineupSlot**: festival (FK), artist (FK), stage (blank), day (nullable Int), start_time (nullable TimeField), end_time (nullable TimeField), slot_name (blank), position (default 0), status (choices: confirmed/rumoured/cancelled/tbc), raw_label (blank), source_url (blank), source_ref (blank), created_at, updated_at
- **AnchorSet**: name, version (IntegerField), is_active (default True), description (TextField blank), created_at
- **AnchorArtist**: anchor_set (FK), artist (FK), role (CharField 100 blank), x_normalized (FloatField), y_normalized (FloatField), is_locked (default True), created_at — unique_together = (anchor_set, artist)
- **ArtistSignal**: artist (FK), source (CharField 20), key (CharField 100), value (FloatField), confidence (FloatField default 1.0), created_at — unique_together = (artist, source, key)
- **RawExternalData**: artist (FK), source (CharField 20), endpoint (CharField 100), raw_data (JSONField), fetched_at (auto), expires_at (nullable DateTimeField)
- **SimilarityEdge**: artist_a (FK), artist_b (FK), tag_score (nullable), audio_score (nullable), cooccurrence_score (nullable), canvas_score (nullable), cultural_affinity_score (nullable), manual_score (nullable), final_score (FloatField), is_locked (default False), explanation (TextField blank), model_version (CharField 50 blank), weights_version (CharField 50 blank), source_snapshot_id (CharField 50 blank), computed_at (nullable), is_active (default True), created_at, updated_at — unique_together = (artist_a, artist_b), constraint artist_a_id < artist_b_id
- **Cluster**: name, parent (FK self nullable), anchor_artist (FK Artist nullable), color (CharField 7), description (TextField blank), created_at
- **ArtistCluster**: artist (FK), cluster (FK), strength (FloatField default 1.0), created_at — unique_together = (artist, cluster)
- **CanvasMove**: artist (FK), old_x, old_y, new_x, new_y, admin_user (FK User), created_at
- **TasteSession**: session_id (UUIDField), festival (FK), created_at
- **TasteSelection**: session (FK), artist (FK), selected_at — unique_together = (session, artist)
- **TasteEdge**: source_artist (FK related_name=taste_source), target_artist (FK related_name=taste_target), festival (FK nullable), raw_lift, smoothed_lift, confidence, sample_size, created_at, updated_at — unique_together = (source_artist, target_artist, festival)
- **RecFeedback**: session (FK TasteSession), recommended_artist (FK), liked_artists (JSONField), feedback (CharField 20 choices: good_shout/not_for_me/already_know), created_at
- **ScrapeLog**: festival (FK), importer_type (CharField 20), timestamp (auto), artists_found, artists_new, artists_updated, errors (TextField blank), status (CharField 20)

### 1.3 — Admin Registration

Register all models in `core/admin.py`:

- **Festival**: list display (name, start_date, location, is_active), prepopulated slug, search by name
- **Artist**: list display (name, canonical_name, is_anchor, canvas_status), search by name/canonical_name, filters (is_anchor, canvas_status), inlines: ArtistAlias (tabular), ArtistIdentifier (tabular)
- **LineupSlot**: list display (festival, artist, stage, day, status), filters (festival, status, stage), search by artist name
- **SimilarityEdge**: list display (artist_a, artist_b, final_score, is_locked), filters (is_locked, is_active), search by artist name
- **AnchorSet**: list display (name, version, is_active)
- **AnchorArtist**: list display (anchor_set, artist, x_normalized, y_normalized)
- **Cluster**: list display (name, parent, color)
- **TasteSession**: read-only, list display (session_id, festival, created_at)
- **TasteSelection**: read-only, list display (session, artist, selected_at)
- **TasteEdge**: list display (source_artist, target_artist, smoothed_lift, confidence)
- **RecFeedback**: read-only, list display (session, recommended_artist, feedback)
- **ArtistSignal**: list display (artist, source, key, value)
- **RawExternalData**: read-only, list display (artist, source, endpoint)
- **ScrapeLog**: read-only, list display (festival, timestamp, importer_type, status)
- **CanvasMove**: read-only, list display (artist, admin_user, created_at)

### 1.4 — URL Config

- `config/urls.py`: admin at `admin/`, include `core.urls` at root
- `core/urls.py`: empty — Phase 02 adds public views

### 1.5 — Seed Data

`core/management/commands/seed_test_data.py`:

- 1 festival ("Download 2025")
- 30 artists across genres (Slipknot, Deftones, Korn, Turnstile, etc.)
- 1 AnchorSet with 5 anchor artists (Slipknot, Deftones, Turnstile, Radiohead, Taylor Swift)
- LineupSlot entries linking artists to the festival
- A few manual SimilarityEdge entries between obviously related artists
- A few admin-applied genre tags

### 1.6 — Base Templates + Static

- `templates/admin/base_site.html`: branded as project codename
- `templates/base.html`: viewport meta, CSS reset, base template for public site
- `static/css/base.css`: design tokens (colours, spacing, fonts)

---

## Acceptance Criteria

- [ ] `python manage.py runserver` starts cleanly
- [ ] All models registered in admin, browsable and editable
- [ ] LineupSlot allows multiple slots per artist per festival
- [ ] ArtistIdentifier stores multiple external IDs per artist
- [ ] TasteEdge is directional (source_artist → target_artist)
- [ ] SimilarityEdge has version/weight/snapshot metadata fields
- [ ] CanvasMove records admin user on move
- [ ] Seed data command populates test festival with artists
- [ ] `python manage.py check` passes
