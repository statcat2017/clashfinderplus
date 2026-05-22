# Phase 06: Admin Canvas

## Goal

Build the drag-to-place similarity canvas for admin curation. This is the visual tool that lets the admin position artists on a 2D map, creating spatial proximity as a curation signal. Boring admin tables came first (Phase 03); this is the delightful visual layer.

---

## Steps

### 6.1 — Canvas API Endpoints

`core/views_api.py`:

```
GET /api/admin/canvas-data/
  Returns all artists (canvas-approved subset) + their edges.

  Query params:
    ?festival_id=5        — show artists in this festival only
    ?cluster_id=3         — show artists in this cluster only
    ?unplaced_only=true   — only unplaced artists
    ?q=deftones           — search by name
    ?limit=500            — maximum nodes to return
    ?min_edge_score=0.2   — minimum edge score to draw

  Response: {
    nodes: [{id, label, x, y, group, size, color, title, canvas_status, is_anchor, festivals_count}],
    edges: [{from, to, value, color, dashes, title, tag_score, canvas_score, manual_score}],
    clusters: [{id, label, nodes, color, center}]
  }

  Logic:
    - Filter artists based on query params
    - Server-side culling: only return top edges (top 5 per node for display)
    - Never return more than LIMIT nodes
    - Show locked, manual, auto, and unplaced artists
    - Unplaced artists rendered at (0,0) with distinct styling

POST /api/admin/canvas/move/
  Body: {artist_id, x, y}
  Logic:
    - Update Artist.canvas_x, Artist.canvas_y (normalized -1.0 to 1.0)
    - Set canvas_status = "manual"
    - Create CanvasMove record
    - Recalculate canvas_score for affected edges:
      distance = sqrt((x1-x2)^2 + (y1-y2)^2)
      canvas_score = 1 / (1 + distance * 3)
    - Return {ok: true, updated_edges: [{from, to, new_canvas_score, new_final_score}]}

POST /api/admin/canvas/edge/
  Body: {artist_a_id, artist_b_id, score, explanation}
  → Create/update SimilarityEdge with manual_score, is_locked=True

DELETE /api/admin/canvas/edge/
  Body: {artist_a_id, artist_b_id}
  → Soft-delete SimilarityEdge (is_active=False)

POST /api/admin/canvas/auto-layout/
  Body: {artist_ids: [...]} (optional, defaults to all unplaced + auto)
  Logic:
    - Run force-directed layout (or UMAP if available from Phase 07)
    - Uses base_score only (no canvas_score, no final_score)
    - Skips locked/manual artists
    - Returns {moves: [{artist_id, new_x, new_y}]}

GET /api/admin/canvas/artist/<id>/neighbors/
  Returns nearby artists within a radius + their edge scores.

POST /api/admin/canvas/undo/
  → Revert last CanvasMove for current admin user
```

### 6.2 — vis.js Canvas Implementation

`static/js/admin-canvas.js`:

```
CanvasApp = {
  network: null,
  nodes: new vis.DataSet(),
  edges: new vis.DataSet(),

  init():
    - Fetch canvas-data with sensible defaults
    - Build vis.js Network with:
      physics: false          // static layout, no live simulation
      interaction: {
        dragNodes: true,
        dragView: true,
        zoomView: true,
        hover: true
      }
      manipulation: false     // we handle edits via API
      edges: { smooth: false } // straight lines for performance
    - Bind events

  loadData(params):
    - GET /api/admin/canvas-data/ with filters
    - Update nodes + edges datasets
    - Recenter view

  onDragEnd(params):
    - Get new position from vis.js (convert pixel → normalized -1 to 1)
    - POST /api/admin/canvas/move/
    - Show toast: proximity changes
    - Update edge thickness/colors

  onSelectNode(params):
    - Open right panel: artist info, tags, top edges, actions

  onDeselectNode():
    - Close right panel

  onSelectEdge(params):
    - Open right panel: edge component breakdown (tag, canvas, manual, etc.)
    - Show actions: [Lock] [Adjust score] [Remove]

  onHoverNode(params):
    - Tooltip: artist name, top 3 festivals, top 3 similar artists

  renderClusters(data):
    - Draw colored halos behind cluster members
    - Legend in corner: cluster color → name

  autoLayout():
    - POST /api/admin/canvas/auto-layout/
    - Animate nodes to new positions

  searchArtist(query):
    - GET /api/admin/canvas-data/?q=query
    - Highlight matching nodes
    - Recenter if single result

  toggleUnplaced():
    - Filter to show only unplaced artists

  undo():
    - POST /api/admin/canvas/undo/
    - Revert last move
}
```

### 6.3 — Canvas Template

`templates/admin/canvas.html`:

- Full-page view, no Django sidebar
- Top bar: project logo, search input, toolbar buttons
- Left collapsible panel: artist list with filters
- Main canvas area (`<div id="canvas">`)
- Right slide-in panel: inspector (hidden by default)
- Bottom status bar: node count, edge count, last action

### 6.4 — Toolbar

| Button | Action |
|---|---|
| Auto-layout | Run force-directed layout for unplaced/auto nodes |
| Show clusters | Toggle cluster halo overlays |
| Show edges | Toggle edge visibility |
| Show unplaced | Filter to only unplaced artists |
| Search | Text input with autocomplete |
| Undo | Revert last canvas move |
| Filters | Festival, cluster, status dropdowns |
| Export PNG | Download canvas as image |

### 6.5 — Node Styling

| Status | Visual |
|---|---|
| Anchor | Large gold star, fixed, no drag |
| Manual (admin-placed) | Medium circle, solid border, full opacity |
| Auto (algorithm-placed) | Medium circle, dashed border, 0.7 opacity |
| Unplaced | Rendered at (0,0), small, pulsing border, faded |
| Selected | Highlighted ring |

Node size: base 12 + 2 per festival appearance, capped at 30.

### 6.6 — Edge Styling

| Score | Visual |
|---|---|
| > 0.6 | Thick solid line (width 4) |
| 0.3 – 0.6 | Medium solid line (width 2) |
| < 0.3 | Thin dashed line (width 1) |

Color:
- Blue: base similarity (tags + co-occurrence)
- Orange: manual/admin edge
- Green: cultural affinity
- Gray: low score

### 6.7 — Coordinate System

Canvas positions stored normalized `[-1.0, 1.0]` on both axes.

Conversion:
```
pixel_to_normalized:
  nx = (px - viewport_center_x) / (viewport_width / 2)
  ny = (py - viewport_center_y) / (viewport_height / 2)

normalized_to_pixel:
  px = nx * (viewport_width / 2) + viewport_center_x
  py = ny * (viewport_height / 2) + viewport_center_y
```

This keeps spatial relationships stable across screen sizes and zoom levels.

### 6.8 — Performance Safeguards

- Always use `physics: false`
- Server-side filtering via query params (festival, cluster, search)
- Max 500 nodes per load (raiseable)
- Top 5 edges per node displayed, not all
- Weak edges hidden by default
- Search-first workflow: find artist before you see millions of nodes

### 6.9 — Canvas Tour

First-time visitors get a brief overlay guide:

1. "This is your artist similarity map."
2. "Drag artists near similar ones to encode your editorial judgement."
3. "Click an edge to see why two artists are connected."
4. "Search for an artist to find and place them."

Dismissable, stored in `localStorage`.

### 6.10 — Status Badges

Nodes show small badges:
- "M" = manually placed
- "A" = auto-placed
- "🔒" = locked
- "★" = anchor

---

## Acceptance Criteria

- [ ] Canvas loads with filtered artist nodes at sensible positions
- [ ] Dragging a node saves position via API and shows proximity changes in toast
- [ ] Clicking a node opens inspector panel with artist info and edges
- [ ] Clicking an edge shows component score breakdown
- [ ] Search finds artists and centers view
- [ ] Auto-layout repositions unplaced/auto nodes using base_score only
- [ ] Locked and manual nodes are NOT moved by auto-layout
- [ ] Cluster halos render correctly when toggled
- [ ] Undo reverts the last canvas move
- [ ] Export PNG downloads the current view
- [ ] 300 nodes + 1500 edges load in under 3 seconds
- [ ] No physics simulation — positions are static and responsive
