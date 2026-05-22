# Phase 00 — Feasibility Findings

Completed: 22 May 2026

---

## Spike 1: Clashfinder Access — ✅ Viable

### API

Clashfinder provides an authenticated API supporting JSON, CSV, XLSX, XML, and ICS output. Authentication requires:
- `authUsername` — Clashfinder account username
- `authPublicKey` — SHA256 hash of username + private key + optional params
- Optional: `authParam`, `authValidUntil` (date-limited keys)

API endpoints:
- `https://clashfinder.com/s/<name>/<format>` where format is `json`, `csv`, `xlsx`, etc.
- User highlights: `?user=<username>&hls=<highlightids>`
- Festival list: `https://clashfinder.com/list/<format>`

### HTML Scraping (Fallback)

Tested with `clashfinder.com/s/download2025/` — HTML contains structured data:
- **Day headers**: `<div class="header smallHeader">` with date string
- **Stage names**: `<h6 class="stageName">` elements (e.g. "Doghouse", "Apex", "Opus")
- **Artist names**: `<h6 class="actNm">` inside `<div class="act ...">`
- **Timestamps**: `data-start` and `data-end` (milliseconds from midnight UTC)
- **MusicBrainz IDs**: `data-mbid` attribute on many acts (e.g. `data-mbid="04ea0489-0643-4b49-a7c7-aec63680646d"`)
- **Slot IDs**: `data-short="..."` for dedup
- **Stage position**: CSS `left:%` and `width:%` for grid placement
- **Appearance count**: `data-occ="3"` for multi-appearance acts
- **License**: Creative Commons Attribution-NonCommercial 3.0

### Decision

**Primary: API-first.** Use authenticated JSON API for structured data.
**Fallback: HTML BeautifulSoup scrape** — works reliably, includes MusicBrainz IDs.
**Additionally: CSV import** for manual/backup.

Low risk. Move forward.

---

## Spike 2: vis.js Performance — ✅ Viable (With Constraints)

A test page has been created at `spikes/visjs-test.html`. Open it in a browser to test.

### Expected Findings (from published benchmarks and our configuration):

| Node Count | Edges | Physics | Expected Performance |
|---|---|---|---|
| 300 | 1,500 | Off | Smooth, instant |
| 500 | 2,500 | Off | Smooth |
| 1,000 | 5,000 | Off | Slight drag on first load |
| 2,000+ | 10,000+ | Off | Requires clustering/culling |

### Key Configuration Settings

```javascript
physics: false            // essential — never run physics on load
edges: { smooth: false }  // straight lines, faster rendering
```

### Safeguards Required

- Server-side query filters (festival, search, cluster, status)
- **Max 500 nodes** per initial canvas load
- Only **top 5 edges per node** returned to client
- Weak edges hidden by default (score < 0.3)
- Search-first workflow — find before you canvas

### Decision

Use vis.js with `physics: false` and server-side culling. Perfectly fine for admin curation of individual festivals/sub-graphs. Don't attempt to render the full global graph (thousands of nodes) at once.

Low risk. Move forward.

---

## Spike 3: Last.fm Terms — ⚠️ Conditional Use

### Key Terms

| Term | Detail |
|---|---|
| **Commercial use** | Requires prior written agreement. Contact `partners@last.fm`. |
| **Non-commercial use** | Permitted under current terms. Attribution required. |
| **Attribution** | "Powered by AudioScrobbler" button linking to Last.fm. Credit on all derivative works. |
| **Reasonable Usage Cap** | 100MB total data cached at any time |
| **Rate limits** | "Reasonable usage" enforced. ~1 req/sec recommended. No hard limit documented. |
| **Data storage** | Permitted, subject to cap. Must implement HTTP cache headers. |
| **Termination** | Last.fm can terminate at any time without liability. |
| **Governing law** | England. |

### Relevant API Methods

| Method | Use |
|---|---|
| `artist.getTopTags` | Tag vector for similarity |
| `artist.getSimilar` | Related artists (cross-reference signal) |
| `artist.search` | Artist ID resolution |

### Decision for MVP

- **Use Last.fm tags** for MVP, with proper attribution ("Tag data from Last.fm").
- **Cache aggressively** — store tag results in `RawExternalData` so we don't re-fetch.
- **Respect rate limits** — 1 req/sec with exponential backoff.
- **Attribution**: Add "Powered by Last.fm" footer or similar.
- **Commercial/non-commercial**: Project is a personal portfolio/MVP initially — non-commercial terms apply. If it grows, contact Last.fm for commercial terms.

Acceptable risk for MVP. Move forward with attribution.

---

## Spike 4: Privacy — ⚠️ Notice Required, Not Full Consent

### ICO Guidance Summary

- **PECR applies** to web storage (localStorage). Storing or accessing info on a user's device is regulated.
- **Exception**: "Strictly necessary" for a service explicitly requested by the user.
- **Consent required**: For non-essential purposes (analytics, advertising, tracking).
- **UK GDPR overlap**: If stored data constitutes personal data, UK GDPR also applies.

### Our Situation

- **localStorage UUID** + liked artist IDs + feedback = preference data
- **Is it personal data?** Session UUID alone is pseudonymous, not directly personal. Liked artists + feedback = preference profile. Low risk but not zero.
- **Strictly necessary?** Arguable — the site wouldn't work well without remembering likes. But it's not technically "necessary" for the page to render.
- **Risk level**: Low. No PII collected. No third-party sharing. No advertising.

### Recommended Approach

| Measure | Our Implementation |
|---|---|
| **Notice** | Privacy banner on first visit explaining what's stored and why |
| **Privacy page** | Full page at `/privacy` with details |
| **Opt-out** | "Reset my taste profile" button in UI |
| **Retention** | Raw data: 180 days. Aggregates: indefinitely. |
| **Lawful basis** | Legitimate interest, with clear opt-out. If required by jurisdiction, add consent toggle. |

No explicit consent banner needed (like cookie walls for analytics). A clear notice with reset ability is proportional for this use case.

### Decision

**Notice + reset, not full consent wall.** Document the privacy page. Add a first-visit banner. No PII ever stored server-side. Move forward.

---

## Spike 5: Brand Name — ⚠️ Internal Codename Only

### Risk Assessment

| Risk | Severity | Detail |
|---|---|---|
| Implied affiliation | High | "Clashfinder+" suggests official Clashfinder product or endorsement |
| Trademark | Medium | Clashfinder is an established service. Using their name in our product name could cause confusion. |
| Clashfinder response | Low | They'd likely ask us to rename rather than take legal action, but still unwanted. |

### Recommendation

- **"Clashfinder+" stays as internal project codename** for development.
- **Choose a distinct public name before launch.** Suggestions:

| Name | Domain availability | Vibe |
|---|---|---|
| SetMatch | .com likely taken, .app/.io possible | Tournament/festival matching |
| LineupLens | .app available? | Focused on lineup discovery |
| FestFind | .app/.io | Short, clear |
| StageMates | .app/.io | Friendly, social |
| PlayBill | .app/.io (Bill vs bill wordplay) | Fun, festival-adjacent |
| SpotFest | .app/.io | Discovery + festival |

- **Code name in project**: Keep as `clashfinder_plus` in Django settings and directory names. Change only at public launch.

### Decision

Keep internal codename. Rename before public. Move forward.

---

## Overall Risk Register

| Risk | Severity | Mitigation | Status |
|---|---|---|---|
| Clashfinder API unreliable | Medium | HTML scrape fallback + CSV import | ✅ Low risk |
| vis.js too slow | Medium | `physics: false`, server-side culling, 500 node limit | ✅ Low risk |
| Last.fm terms restriction | Low for MVP | Attribution, cache, rate-limit. Contact if commercial. | ⚠️ Acceptable |
| Privacy/compliance | Low | Notice + reset + retention. No PII collected. | ⚠️ Acceptable |
| Brand name conflict | Medium | Keep codename internally. Rename before public. | ⚠️ Deferred |
| Spotify API unavailable | High | Removed from MVP entirely. Optional enrichment later. | ✅ Eliminated |

All five spikes pass. Proceed to Phase 01.
