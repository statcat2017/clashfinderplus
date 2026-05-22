(function() {
  'use strict';

  window.CanvasApp = {
    network: null,
    nodes: null,
    edges: null,
    showClusters: false,
    showEdges: true,
    clusterData: [],
    currentData: null,

    init() {
      this.nodes = new vis.DataSet();
      this.edges = new vis.DataSet();
      this._initDarkMode();
      this._initEventListeners();
      this.loadData();
    },

    _initDarkMode() {
      const stored = localStorage.getItem('canvas_theme');
      if (stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.querySelector('#canvas-wrapper')?.classList.add('canvas-dark');
      }
    },

    _initEventListeners() {
      document.getElementById('filter-festival')?.addEventListener('change', () => this.loadData());
      document.getElementById('filter-status')?.addEventListener('change', () => this.loadData());
    },

    loadData() {
      const festivalId = document.getElementById('filter-festival')?.value || '';
      const status = document.getElementById('filter-status')?.value || '';
      const params = new URLSearchParams({ limit: '500' });
      if (festivalId) params.set('festival_id', festivalId);
      if (status) params.set('canvas_status', status);

      this._setStatus('Loading...');

      fetch(`/api/admin/canvas-data/?${params}`)
        .then(r => r.json())
        .then(data => {
          this.currentData = data;
          this.clusterData = data.clusters || [];
          this._renderNetwork(data);
          this._renderArtistList(data.nodes);
          this._setStatus(`${data.nodes.length} nodes, ${data.edges.length} edges`);
        })
        .catch(err => {
          this._setStatus('Error loading canvas data');
          console.error(err);
        });
    },

    _renderNetwork(data) {
      const container = document.getElementById('canvas');
      if (!container) return;

      this.nodes.clear();
      this.edges.clear();

      data.nodes.forEach(n => {
        this.nodes.add({
          id: n.id,
          label: n.label,
          x: n.x * 500,
          y: n.y * 500,
          size: n.size,
          color: {
            background: n.color,
            border: n.canvas_status === 'locked' ? '#dc3545' : n.canvas_status === 'manual' ? '#417690' : '#adb5bd',
          },
          borderWidth: n.canvas_status === 'locked' ? 3 : 1,
          shape: n.is_anchor ? 'star' : 'dot',
          title: n.title,
          group: n.canvas_status,
          fixed: n.canvas_status === 'locked',
        });
      });

      if (this.showEdges) {
        data.edges.forEach(e => {
          this.edges.add({
            from: e.from,
            to: e.to,
            value: e.value * 5,
            color: { color: e.color, opacity: Math.min(e.value + 0.3, 1) },
            dashes: e.dashes,
            title: e.title,
            width: Math.max(e.value * 4, 0.5),
          });
        });
      }

      const options = {
        physics: false,
        interaction: {
          dragNodes: true,
          dragView: true,
          zoomView: true,
          hover: true,
          tooltipDelay: 200,
        },
        manipulation: false,
        edges: { smooth: false },
        nodes: {
          font: { size: 11, face: 'system-ui' },
          scaling: { min: 8, max: 30 },
        },
      };

      if (this.network) {
        this.network.setData({ nodes: this.nodes, edges: this.edges });
        this.network.setOptions(options);
      } else {
        this.network = new vis.Network(container, { nodes: this.nodes, edges: this.edges }, options);
        this.network.on('dragEnd', params => this._onDragEnd(params));
        this.network.on('click', params => this._onClick(params));
        this.network.on('oncontext', params => {
          params.event.preventDefault();
          return false;
        });
      }
    },

    _onDragEnd(params) {
      if (!params.nodes || params.nodes.length === 0) return;
      const nodeId = params.nodes[0];
      const pos = this.network.getPosition(nodeId);

      fetch('/api/admin/canvas/move/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCSRF(),
        },
        body: JSON.stringify({
          artist_id: nodeId,
          x: pos.x / 500,
          y: pos.y / 500,
        }),
      })
      .then(r => r.json())
      .then(data => {
        this._showToast(`Moved artist — ${data.updated_edges.length} edges updated`);
      })
      .catch(err => this._showToast('Failed to save position'));
    },

    _onClick(params) {
      const inspector = document.getElementById('canvas-inspector');
      if (!inspector) return;

      if (params.nodes && params.nodes.length === 1) {
        const nodeId = params.nodes[0];
        const node = this.nodes.get(nodeId);
        if (!node) return;

        inspector.style.display = 'block';
        inspector.innerHTML = `
          <div class="inspector-section">
            <h4>${node.label}</h4>
            <p style="font-size:12px;color:#666;">Status: ${node.group} | Size: ${node.size}</p>
          </div>
          <div class="inspector-section">
            <h4>Neighbors</h4>
            <div id="neighbors-list">Loading...</div>
          </div>
        `;

        fetch(`/api/admin/canvas/artist/${nodeId}/neighbors/?radius=0.5`)
          .then(r => r.json())
          .then(data => {
            const list = document.getElementById('neighbors-list');
            if (!list) return;
            list.innerHTML = data.neighbors.slice(0, 10).map(n =>
              `<div style="font-size:12px;padding:3px 0;">${n.artist.name} — ${n.distance.toFixed(2)} ${n.edge_score ? '('+(n.edge_score*100).toFixed(0)+'%)' : ''}</div>`
            ).join('');
            if (data.neighbors.length === 0) list.innerHTML = '<span style="color:#999;">No nearby artists</span>';
          });
      } else {
        inspector.style.display = 'none';
      }

      if (params.edges && params.edges.length === 1) {
        const edgeId = params.edges[0];
        const edge = this.edges.get(edgeId);
        if (edge) {
          inspector.style.display = 'block';
          inspector.innerHTML = `
            <div class="inspector-section">
              <h4>Edge Details</h4>
              <div style="font-size:12px;">${edge.title || 'No details'}</div>
            </div>
          `;
        }
      }
    },

    autoLayout() {
      fetch('/api/admin/canvas/auto-layout/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCSRF(),
        },
        body: JSON.stringify({}),
      })
      .then(r => r.json())
      .then(data => {
        this._showToast(`Auto-laid out ${data.moves.length} artists`);
        this.loadData();
      })
      .catch(err => this._showToast('Auto-layout failed'));
    },

    toggleClusters() {
      this.showClusters = !this.showClusters;
      this._showToast(this.showClusters ? 'Showing clusters' : 'Hiding clusters');
    },

    toggleEdges() {
      this.showEdges = !this.showEdges;
      if (this.currentData) {
        this._renderNetwork(this.currentData);
      }
      this._showToast(this.showEdges ? 'Showing edges' : 'Hiding edges');
    },

    search() {
      const q = document.getElementById('search-input')?.value;
      if (!q) return;
      fetch(`/api/admin/canvas-data/?q=${encodeURIComponent(q)}&limit=10`)
        .then(r => r.json())
        .then(data => {
          if (data.nodes.length === 1) {
            const node = data.nodes[0];
            this.network.focus(node.id, { scale: 2, animation: true });
            this._showToast(`Found: ${node.label}`);
          } else if (data.nodes.length > 1) {
            this._showToast(`Found ${data.nodes.length} artists`);
          } else {
            this._showToast('No artists found');
          }
        });
    },

    undo() {
      fetch('/api/admin/canvas/undo/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCSRF(),
        },
      })
      .then(r => r.json())
      .then(data => {
        this._showToast('Undone last move');
        this.loadData();
      })
      .catch(err => this._showToast('Nothing to undo'));
    },

    exportPNG() {
      if (!this.network) return;
      const canvas = document.querySelector('#canvas canvas');
      if (!canvas) return;
      const link = document.createElement('a');
      link.download = 'canvas-export.png';
      link.href = canvas.toDataURL();
      link.click();
      this._showToast('Exported PNG');
    },

    _renderArtistList(nodes) {
      const container = document.getElementById('canvas-artist-list');
      if (!container) return;
      container.innerHTML = nodes.map(n =>
        `<div class="artist-list-item" onclick="CanvasApp.focusNode(${n.id})">${n.label} <span style="color:#999;font-size:11px;">${n.canvas_status}</span></div>`
      ).join('');
    },

    focusNode(id) {
      if (this.network) {
        this.network.focus(id, { scale: 2, animation: true });
        this.network.selectNodes([id]);
      }
    },

    _showToast(msg) {
      const toast = document.getElementById('canvas-toast');
      if (!toast) return;
      toast.textContent = msg;
      toast.classList.add('show');
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => toast.classList.remove('show'), 2500);
    },

    _setStatus(msg) {
      const el = document.getElementById('canvas-status');
      if (el) el.textContent = msg;
    },

    toggleDark() {
      const wrapper = document.querySelector('#canvas-wrapper');
      if (!wrapper) return;
      wrapper.classList.toggle('canvas-dark');
      const isDark = wrapper.classList.contains('canvas-dark');
      localStorage.setItem('canvas_theme', isDark ? 'dark' : 'light');
      this._showToast(isDark ? 'Dark mode' : 'Light mode');
    },

    _getCSRF() {
      const el = document.querySelector('[name=csrfmiddlewaretoken]');
      return el ? el.value : '';
    },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => CanvasApp.init());
  } else {
    CanvasApp.init();
  }
})();
