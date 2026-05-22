# Phase 03: Importers + Admin Tools

## Goal

Make lineup ingestion repeatable and self-serve. Build the `lineup_importers` module supporting Clashfinder API (primary), HTML fallback, CSV import, and manual admin entry. Add admin tools for dedup, tagging, and import history.

---

## Steps

### 3.1 — Importer Module Structure

```
core/lineup_importers/
  __init__.py
  base.py          — BaseImporter abstract class
  clashfinder_api.py   — Clashfinder API import
  clashfinder_html.py  — BeautifulSoup fallback
  csv_importer.py      — CSV file import
  matcher.py           — Artist matching/dedup logic
```

### 3.2 — Base Importer

`core/lineup_importers/base.py`:

```python
class BaseImporter(ABC):
    def __init__(self, festival: Festival):
        self.festival = festival
        self.log = ScrapeLog(festival=festival, status="in_progress")
        self.artists_found = 0
        self.artists_new = 0
        self.errors = []

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Fetch raw lineup data. Returns list of slot dicts:
        [{artist_name, stage, day, start_time, end_time, slot_name, status, raw_label}]
        """

    def import_lineup(self) -> ScrapeLog:
        """Run the import pipeline:
        1. fetch() -> raw data
        2. For each slot: match or create Artist
        3. Create/update LineupSlot records
        4. Log and return ScrapeLog
        """

    def _match_artist(self, name: str) -> Artist:
        """Match artist name to existing records.
        1. Exact match (case-insensitive)
        2. ArtistAlias match
        3. Fuzzy match (Levenshtein < 2)
        4. Create new Artist with canvas_status='unplaced'
        """
```

### 3.3 — Clashfinder API Importer

`core/lineup_importers/clashfinder_api.py`:

```
ClashfinderAPIImporter(BaseImporter):
    API_BASE = "https://clashfinder.com/api/2025/"

    def __init__(self, festival, username, public_key):
        super().__init__(festival)
        self.username = username
        self.public_key = public_key

    def fetch(self):
        - Authenticate with authUsername + authPublicKey
        - Fetch festival lineup data from API
        - Parse JSON response into slot dicts
        - Handle TBC, Special Guest, cancelled placeholders
        - Return list of slot dicts
```

### 3.4 — Clashfinder HTML Fallback

`core/lineup_importers/clashfinder_html.py`:

```
ClashfinderHTMLImporter(BaseImporter):
    def fetch(self):
        - Fetch clashfinder.com page via httpx
        - Parse with BeautifulSoup
        - Identify day tabs, stage columns, artist cells
        - Extract: artist name, day, stage, time (if present)
        - Clean artist names (strip times, parenthetical notes)
        - Handle missing data gracefully
        - Return slot dicts
```

Store full raw HTML in `RawExternalData` for reprocessing.

### 3.5 — CSV Importer

`core/lineup_importers/csv_importer.py`:

```
CSVImporter(BaseImporter):
    def __init__(self, festival, csv_file):
        super().__init__(festival)
        self.csv_file = csv_file

    def fetch(self):
        - Parse CSV file
        - Expected columns: artist_name, stage, day, start_time, end_time
        - Flexible column naming via header mapping in admin UI
        - Return slot dicts
```

### 3.6 — Artist Matcher

`core/lineup_importers/matcher.py`:

```
ArtistMatcher:
    def find_or_create(self, name: str) -> Artist:
        """Matching priority:
        1. Exact name match (case-insensitive)
        2. ArtistAlias match
        3. Levenshtein distance < 2 match
        4. MusicBrainz identifier lookup (if available)
        5. Create new Artist
        """
        When creating: set canvas_status='unplaced'

    def find_duplicates(self, artist: Artist) -> list[Artist]:
        """Find potential duplicates for dedup review.
        Uses name similarity and shared aliases.
        """

    def merge_artists(self, source: Artist, target: Artist):
        """Merge source into target:
        - Move all LineupSlot, ArtistAlias, ArtistIdentifier, edges to target
        - Update TasteSelection, TasteEdge references
        - Soft-delete source
        """
```

### 3.7 — Admin Import View

`core/views_admin.py`:

```
ImportDashboardView(TemplateView):
    template_name = "admin/import_dashboard.html"
    - List of festivals
    - Per festival: last import status, [Import from Clashfinder API] button
    - [Import from CSV] button with file upload
    - [Manual entry] link to LineupSlot admin
    - ScrapeLog history table

ImportRunView(View):
    POST /admin/import/run/
    Body: {festival_id, importer_type}
    - Run selected importer
    - Return progress/result as JSON
    - Log to ScrapeLog
```

`templates/admin/import_dashboard.html`:
- Extends admin base
- Festival table with import controls
- Shows: last import date, artist count, status
- ScrapeLog history expandable per festival

### 3.8 — Dedup Admin Tool

`core/views_admin.py`:

```
DedupView(TemplateView):
    template_name = "admin/dedup.html"
    - Show potential duplicates found by ArtistMatcher.find_duplicates
    - Side-by-side comparison of name, aliases, identifiers, festivals
    - [Merge] button per pair
    - [Dismiss] to hide pair from suggestions

MergeArtistsView(View):
    POST /admin/dedup/merge/
    Body: {source_id, target_id}
    - Run merge_artists
    - Return result
```

### 3.9 — Tag Editor Admin View

`core/views_admin.py`:

```
TagEditorView(TemplateView):
    template_name = "admin/tag_editor.html"
    - Search/browse artists
    - Per artist: add/remove genre tags (tag-style input)
    - Bulk tag: select artists + apply tag to all
    - Auto-suggest tags from existing tags
```

### 3.10 — Management Commands

`core/management/commands/import_festivals.py`:

```
python manage.py import_festivals [--festival-id=N] [--all] [--importer=clashfinder_api] [--dry-run]

Logic:
  - Load festivals matching criteria
  - Run selected importer for each
  - Print summary
  - Dry-run: show what would change without writing
```

### 3.11 — RawExternalData Caching

When API/HTML data is fetched, store the raw response in `RawExternalData`:

```
RawExternalData.objects.update_or_create(
    artist=artist,
    source=source,
    endpoint=endpoint,
    defaults={'raw_data': response_json, 'fetched_at': now}
)
```

This allows re-parsing tag scores, embeddings, etc. without re-fetching external APIs.

---

## Acceptance Criteria

- [ ] Clashfinder API import produces LineupSlot records for a real festival
- [ ] HTML fallback import works for at least one live clashfinder.com page
- [ ] CSV import with correctly formatted file produces LineupSlot records
- [ ] Artist matching deduplicates correctly (same artist across sources maps to one record)
- [ ] Admin import dashboard shows festival list with import controls
- [ ] Import triggers create ScrapeLog entries with correct counts
- [ ] Dedup view shows potential duplicates with side-by-side comparison
- [ ] Merge artists correctly transfers all related records
- [ ] Tag editor allows add/remove/bulk tag operations
- [ ] RawExternalData stores raw API responses for later re-parsing
- [ ] `--dry-run` flag works without modifying data
- [ ] Failed import logs error without deleting existing lineup
