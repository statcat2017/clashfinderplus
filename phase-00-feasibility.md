# Phase 00: Feasibility Spike

## Goal

Validate the riskiest assumptions before committing to the full architecture. This phase is disposable — write spike code, throw it away, and make informed decisions for Phase 01 onwards.

---

## Spikes

### 1. Clashfinder Access

**Question**: Can we reliably import lineup data from Clashfinder?

**Tasks**:

1. Register/obtain Clashfinder API credentials (`authUsername`, `authPublicKey`)
2. Test the official API endpoint against 3-5 real festival pages
   - Does it return structured lineup data (artist, day, stage, time)?
   - What data is missing?
   - Rate limits?
3. If API works: document response format, build a mock client
4. If API fails or is limited: test HTML scraping fallback
   - Fetch 3-5 different clashfinder pages with httpx
   - Inspect DOM structure — is data in static HTML or JS-rendered?
   - Can BeautifulSoup extract artist names per day/stage?
   - How varied are templates across different festivals?
5. For each approach: note issues like "Special Guest", "TBC", duplicate entries

**Output**: Decision on primary import method + documented fallback strategy.

**Acceptance**:
- [ ] Clashfinder API credentials obtained and tested
- [ ] At least one import method successfully extracts structured lineup data
- [ ] Known parsing edge cases documented
- [ ] Recommendation: API-first, HTML fallback, CSV manual option

### 2. vis.js Performance Baseline

**Question**: Can vis.js Network handle our canvas requirements at realistic scale?

**Tasks**:

1. Build a standalone HTML page with vis.js
2. Generate 300 fake "artist" nodes with random positions
3. Draw edges for top-5 most-similar per node (1500 edges)
4. Test:
   - Load time with physics enabled vs disabled
   - Drag responsiveness
   - Zoom smoothness
   - Search + highlight performance
   - Cluster rendering
5. Repeat with 500 nodes, 1000 nodes
6. Identify at what point performance degrades unacceptably

**Output**: Node/edge limits for comfortable canvas use + configuration settings.

**Acceptance**:
- [ ] 300 nodes + 1500 edges renders smoothly with `physics: false`
- [ ] Drag, zoom, search all responsive
- [ ] Threshold identified for when server-side clustering/filtering becomes necessary

### 3. Last.fm Terms Review

**Question**: Can we legally use Last.fm API data in this project?

**Tasks**:

1. Read current Last.fm API Terms of Service
2. Read API documentation for `artist.getTopTags` and `artist.getSimilar`
3. Note: rate limits, attribution requirements, commercial use restrictions
4. Assess: is MVP usage (non-commercial, cache-friendly, attributed) acceptable?
5. Document fallback plan if Last.fm is not usable (admin tags only, MusicBrainz)

**Output**: Go/no-go on Last.fm + attribution requirements + rate limit budget.

**Acceptance**:
- [ ] Terms reviewed and documented
- [ ] Decision on whether Last.fm can be used for MVP
- [ ] Fallback path defined

### 4. Privacy Approach Validation

**Question**: What storage notice and consent mechanism do we actually need?

**Tasks**:

1. Review ICO guidance on localStorage and web storage technologies
2. Determine: is session UUID + taste selection data "personal data"?
3. Draft a privacy notice text covering: what's stored, why, retention, reset
4. Decide: consent banner needed, or just notice + reset?
5. Check: does GDPR apply to UK-only festival data?

**Output**: Privacy implementation requirements for Phase 02.

**Acceptance**:
- [ ] Privacy approach documented
- [ ] Notice text drafted
- [ ] Consent/opt-out mechanism decided
- [ ] Reset/delete flow specified

### 5. Brand Name Decision

**Question**: Should we ship under "Clashfinder+" or rename?

**Tasks**:

1. Review Clashfinder brand guidelines (if any)
2. Assess risk of name confusion / implied affiliation
3. Brainstorm 3-5 alternative names with .com/.io/.app availability
4. Decide: internal codename vs public name
5. If internal only: pick a codename for now, defer public name

**Output**: Brand name decision + naming conventions in code.

**Acceptance**:
- [ ] Brand name decision made
- [ ] If renamed: project files updated
- [ ] If codename: documented plan for public naming later

---

## Outcome

This phase produces a risk register and concrete architecture decisions:

| Risk | Mitigation | Decision |
|---|---|---|
| Clashfinder API unreliable | HTML scraping fallback + CSV import | |
| vis.js too slow at scale | `physics: false`, server-side filtering, top-K edges only | |
| Last.fm terms restrict use | Admin-only tags, MusicBrainz fallback | |
| Privacy requires consent | Consent banner + clear notice + reset | |
| Brand name risk | Rename before public launch | |

Each spike is timeboxed to a few hours of investigation. The goal is not production code — it's confidence that the architecture will work.

---

## Effort Estimate

~2-3 days total.
