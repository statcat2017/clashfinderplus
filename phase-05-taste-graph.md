# Phase 05: Taste Graph + Feedback

## Goal

Build the anonymous taste aggregation system. Collect user like/unlike events, compute directional Bayesian-smoothed lift edges, and incorporate cultural affinity into recommendation scoring. Add explicit feedback buttons to improve training data quality. Add privacy controls and data retention.

---

## Steps

### 5.1 — Aggregation Engine

`core/similarity/taste.py`:

```python
class TasteGraphBuilder:
    MIN_SAMPLES = 10  # minimum co-selections before storing lift
    CONFIDENCE_CURVE_SHARPNESS = 20  # higher = more samples needed for confidence

    def update_all_edges(self, festival: Festival = None):
        """Aggregate TasteSelection data into directional TasteEdge records.

        For each pair (A, B) where A != B, co-selected in the same session:
          1. Count: sessions_with_A, sessions_with_B, sessions_with_both
          2. If sessions_with_both < MIN_SAMPLES: skip
          3. raw_lift(A → B) = P(B|A) / P(B)
             P(B) = sessions_with_B / total_festival_sessions
             P(B|A) = sessions_with_both / sessions_with_A
          4. confidence = sample_size / (sample_size + CONFIDENCE_CURVE_SHARPNESS)
          5. smoothed_lift = 1 + ((raw_lift - 1) * confidence)
          6. Store TasteEdge(source_artist=A, target_artist=B, ...)
          7. Update SimilarityEdge.cultural_affinity_score:
             - Normalize smoothed_lift to 0-1: min(smoothed_lift / 5.0, 1.0)
             - Recomputed final_score
        """

    def update_edges_for_artist(self, artist: Artist):
        """Single-artist incremental update."""

    def _compute_lift(self, a_id: int, b_id: int, festival_id: int = None) -> dict:
        """Compute raw lift, confidence, smoothed lift for a pair.
        If festival_id is set, scope to that festival's sessions.
        Otherwise use global session data.
        """
```

### 5.2 — Recommendation Integration

Update `RecommendationsAPI` to include cultural affinity:

```python
def _cultural_affinity_score(liked_ids, candidate_id, festival_id):
    scores = []
    for liked_id in liked_ids:
        edge = TasteEdge.objects.filter(
            source_artist_id=liked_id,
            target_artist_id=candidate_id,
            festival_id=festival_id
        ).first()
        if edge and edge.confidence > 0.3:
            scores.append(edge.smoothed_lift)
    if not scores:
        # Fall back to global (festival-independent) edges
        for liked_id in liked_ids:
            edge = TasteEdge.objects.filter(
                source_artist_id=liked_id,
                target_artist_id=candidate_id,
                festival__isnull=True
            ).first()
            if edge:
                scores.append(edge.smoothed_lift)

    if not scores:
        return 0.0

    return min(sum(scores) / len(scores) / 5.0, 1.0)
```

### 5.3 — Festival-Specific vs Global Fallback

Rules:
1. If festival-specific `TasteEdge` exists with `confidence > 0.3`, use it
2. Else if global `TasteEdge` (festival=null) exists with `confidence > 0.3`, use it
3. Else: cultural affinity = 0 (no signal yet)

This solves the niche festival problem — small festivals don't have enough data for festival-specific edges, so they fall back to global patterns.

### 5.4 — Feedback Integration

`RecFeedback` data feeds back into taste edges:

```python
# When computing lift, weight "good_shout" feedback higher than passive likes
# "not_for_me" feedback can reduce or negate an edge weight
# "already_know" feedback can flag an artist as over-exposed for a user

def compute_adjusted_lift(session, artist_a, artist_b):
    base_lift = compute_lift_from_selections(artist_a, artist_b)

    # Positive feedback boosts lift
    good_shouts = RecFeedback.objects.filter(
        session__festival=session.festival,
        recommended_artist=artist_b,
        feedback="good_shout"
    ).count()

    # Negative feedback reduces lift
    rejections = RecFeedback.objects.filter(
        session__festival=session.festival,
        recommended_artist=artist_b,
        feedback="not_for_me"
    ).count()

    boost = good_shouts * 0.1
    penalty = rejections * 0.15

    return base_lift + boost - penalty
```

### 5.5 — Taste Dashboard (Admin)

`core/views_admin.py`:

```
TasteDashboardView(TemplateView):
    template_name = "admin/taste_dashboard.html"

    Context:
      - Total anonymized sessions
      - Total selections
      - TasteEdge count
      - Top 10 strongest cultural affinity edges (smoothed_lift × confidence)
      - Top 10 most co-selected pairs
      - Lift distribution chart data (histogram of lift values)
      - Session growth over time (last 30 days)
      - RecFeedback summary (good_shout vs not_for_me vs already_know)
```

### 5.6 — Privacy Controls

Add to the public site:

- `/api/taste/reset/` endpoint (already built in Phase 02)
- "Reset my taste profile" link in footer or settings area
- Confirmation dialog before reset

Privacy page (`/privacy`) updated with:

- What data we store (anonymous session UUID, artist likes, recommendation feedback)
- How long we keep it (raw data: 180 days, aggregated: indefinitely)
- Lawful basis (legitimate interest)
- How to reset (button + API endpoint)
- No personal data collected
- No third-party sharing
- Contact for data inquiries

### 5.7 — Data Retention Housekeeping

`core/management/commands/prune_taste_data.py`:

```
python manage.py prune_taste_data [--days=180]

Logic:
  - Delete TasteSession records older than N days
  - Cascade delete TasteSelection and RecFeedback for those sessions
  - Keep TasteEdge aggregates (they don't reference sessions directly)
  - Print summary: sessions removed, selections removed, feedback removed
```

Run via cron (daily/weekly) or admin trigger.

### 5.8 — Management Commands

`core/management/commands/compute_taste_edges.py`:

```
python manage.py compute_taste_edges [--festival-id=N]

Logic:
  - Aggregate TasteSelection → TasteEdge
  - Update SimilarityEdge.cultural_affinity_score
  - Apply confidence weighting
  - Print summary: edges created, updated, skipped (below threshold)
```

---

## Acceptance Criteria

- [ ] TasteSelection records accumulate from public site likes
- [ ] `compute_taste_edges` generates directional TasteEdge records with smoothed lift
- [ ] Lift values > 1.0 correctly indicate positive cultural affinity
- [ ] Confidence weighting prevents inflated scores from small samples (e.g. 2 co-selections)
- [ ] MIN_SAMPLES=10 prevents edges from noise-level data
- [ ] Festival-specific edges are preferred; global edges serve as fallback
- [ ] "good_shout" feedback boosts cultural affinity weight
- [ ] "not_for_me" feedback reduces edge weight
- [ ] Recommendation endpoint includes cultural affinity in scoring
- [ ] Admin taste dashboard renders with meaningful stats
- [ ] Reset taste profile clears all session data via API + localStorage
- [ ] `prune_taste_data` removes old raw data, keeps aggregate edges
- [ ] 10,000 sessions process in under 30 seconds
