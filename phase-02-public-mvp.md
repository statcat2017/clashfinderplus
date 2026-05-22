# Phase 02: Public MVP — Prove the Loop

## Goal

Build the thinnest possible version of the public recommendation loop. One festival. Manually entered lineup. Basic recommendations based on admin-defined tags and similarity edges. The product becomes useful now.

---

## Steps

### 2.1 — Public Views

`core/views.py`:

```
HomeView(TemplateView):
  template_name = "public/home.html"
  - List active festivals
  - JSON data embedded into page for JS

FestivalDetailView(TemplateView):
  template_name = "public/festival_detail.html"
  - Festival data + lineup (LineupSlot records grouped by day/stage)
```

### 2.2 — API Endpoints

`core/views_api.py`:

```
GET /api/festivals/
  → [{id, name, slug, start_date, end_date, location, artist_count}]

GET /api/festivals/<id>/lineup/
  → {festival: {...}, lineup: [{artist: {id, name, genre_tags, image_url},
                                 day, stage, start_time, end_time, slot_name, status}]}

POST /api/recommendations/
  Body: {session_id, festival_id, liked_artist_ids, max_results}
  Logic (MVP — no embeddings yet):
    1. Get SimilarityEdge for liked artists where final_score > 0.15
    2. Filter to candidates on this festival lineup
    3. Score = average final_score across all edges to liked artists
    4. Minimum threshold: score > 0.15
    5. Return top N with explanations
  Response: {recommendations: [{artist: {id, name}, score,
                                reason: {type, because_of, evidence}}]}

POST /api/taste/like/
  Body: {session_id, festival_id, artist_id}
  → Store TasteSelection (create TasteSession if needed)

POST /api/taste/unlike/
  Body: {session_id, festival_id, artist_id}
  → Remove TasteSelection

POST /api/taste/reset/
  Body: {session_id}
  → Delete TasteSession + all related TasteSelection + RecFeedback

POST /api/feedback/
  Body: {session_id, festival_id, recommended_artist_id,
         liked_artist_ids, feedback}
  → Store RecFeedback
```

### 2.3 — Templates

`templates/public/base.html`:
- Header with brand codename
- Privacy link in footer
- Loads `public.css` and `public.js`

`templates/public/home.html`:
- Two-panel layout on desktop (CSS grid)
- Left: scrollable festival list with search
- Right: selected festival lineup
- Mobile: single column, tap festival to view lineup

`templates/public/festival_detail.html`:
- Festival header: name, dates, location
- Day tabs (if multi-day)
- Stage columns (if stage data) or flat artist grid
- Artist cards: name, genre tag pills, heart toggle
- Recommendations section (loaded dynamically by JS)

### 2.4 — Privacy Banner

`templates/public/privacy_banner.html`:
- Only shown on first visit (check localStorage flag)
- Text: "We use local browser storage to remember artists you like and improve recommendations. No personal data is collected or stored on our servers. Read more / Dismiss"
- Links to `/privacy` page
- "Dismiss" button sets `localStorage` flag
- "Reset taste profile" link

`templates/public/privacy.html`:
- Full privacy notice: what's stored, why, retention, reset instructions, lawful basis

### 2.5 — Recommendation Cards

Each recommendation rendered as:

```html
<div class="rec-card" data-artist-id="88">
  <div class="rec-match-bar" style="width: 89%"></div>
  <div class="rec-info">
    <span class="rec-name">Korn</span>
    <span class="rec-score">89%</span>
    <span class="rec-reason">Similar sound to Slipknot, Deftones</span>
    <span class="rec-evidence">Main Stage · Sat Jun 14</span>
  </div>
  <div class="rec-actions">
    <button data-feedback="good_shout">Good shout</button>
    <button data-feedback="not_for_me">Not for me</button>
    <button data-feedback="already_know">Already know them</button>
  </div>
</div>
```

Feedback buttons POST to `/api/feedback/` and change appearance on click.

### 2.6 — Static Files

`static/css/public.css`:

- Clean & minimal design
- Color tokens: `--bg: #fff`, `--text: #1e293b`, `--accent: #6366f1`, `--muted: #94a3b8`
- Font: system-ui, 16px body, 1.5 line-height
- Artist grid: responsive CSS grid, cards with border + radius
- Heart toggle: outline → filled on click, 150ms transition
- Recommendation cards: stacked, match bar at top, feedback buttons at bottom
- Privacy banner: fixed bottom, dismissable
- Mobile: <768px single column, full-width

`static/js/public.js`:

```
App = {
  sessionId: localStorage.getItem('cf_session_id') || crypto.randomUUID(),
  likedArtists: {},  // {festival_id: Set(artist_ids)}
  currentFestivalId: null,

  init():
    - Load festivals from API
    - Restore likes from localStorage
    - Show privacy banner if first visit
    - Autoload first festival in list

  loadFestival(id):
    - Fetch lineup API
    - Render artist grid
    - Highlight already-liked artists
    - If likes exist, fetch recommendations

  toggleLike(artistId):
    - Toggle heart UI
    - Update localStorage
    - POST like/unlike

  fetchRecommendations():
    - POST to /api/recommendations/
    - Render recommendation cards below lineup

  sendFeedback(artistId, feedback):
    - POST to /api/feedback/
    - Update card UI (disable buttons, show confirmation)

  searchFestivals(query):
    - Filter festival list by name match

  resetTasteProfile():
    - POST /api/taste/reset/
    - Clear localStorage session data
    - Reload page
}
```

### 2.7 — localStorage Schema

```
Key: "cf_session_id"
Value: UUID string

Key: "cf_likes_{festival_id}"
Value: JSON array of artist IDs

Key: "cf_privacy_dismissed"
Value: "true" (set when user dismisses privacy banner)
```

---

## Acceptance Criteria

- [ ] Homepage loads with festival list
- [ ] Clicking a festival shows its lineup with artist cards
- [ ] Heart toggle works, persists across page reload
- [ ] Liking 1+ artists triggers recommendation fetch
- [ ] Recommendation cards show score bar, artist name, match reason
- [ ] Feedback buttons POST to API and show confirmation
- [ ] Privacy banner shows on first visit only
- [ ] Privacy page renders with full notice
- [ ] Reset taste profile clears data and reloads
- [ ] `/api/feedback/` receives and stores RecFeedback records
- [ ] Works on mobile (single column, touch-friendly)
- [ ] No console errors in Chrome, Firefox, Safari
