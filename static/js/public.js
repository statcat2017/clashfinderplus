(function() {
  'use strict';

  const SESSION_KEY = 'cf_session_id';
  const PRIVACY_KEY = 'cf_privacy_dismissed';
  const LIKES_PREFIX = 'cf_likes_';

  const MIN_ROW_HEIGHT = 36;
  const ROW_MINUTES = 30;

  const App = {
    sessionId: null,
    likedArtists: {},
    currentFestivalId: null,
    festivals: [],
    recsLoading: false,
    lineupData: null,
    activeDay: null,

    init() {
      this.sessionId = localStorage.getItem(SESSION_KEY);
      if (!this.sessionId) {
        this.sessionId = crypto.randomUUID();
        localStorage.setItem(SESSION_KEY, this.sessionId);
      }
      this._restoreLikes();
      this._initPrivacyBanner();
      this._initResetConfirm();
      this._loadFestivals();
    },

    // ── Privacy ──

    _initPrivacyBanner() {
      const banner = document.getElementById('privacy-banner');
      if (!banner) return;
      if (localStorage.getItem(PRIVACY_KEY)) {
        banner.classList.add('hidden');
        return;
      }
      setTimeout(() => banner.classList.remove('hidden'), 500);
      document.getElementById('privacy-dismiss')?.addEventListener('click', () => {
        localStorage.setItem(PRIVACY_KEY, 'true');
        banner.classList.add('hidden');
      });
      document.getElementById('privacy-reset')?.addEventListener('click', () => {
        document.getElementById('reset-confirm')?.classList.remove('hidden');
      });
    },

    _initResetConfirm() {
      document.getElementById('reset-confirm-btn')?.addEventListener('click', () => this._resetTaste());
      document.getElementById('reset-cancel-btn')?.addEventListener('click', () => {
        document.getElementById('reset-confirm')?.classList.add('hidden');
      });
    },

    _resetTaste() {
      fetch('/api/taste/reset/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session_id: this.sessionId}),
      }).then(() => {
        localStorage.removeItem(SESSION_KEY);
        localStorage.removeItem(PRIVACY_KEY);
        Object.keys(localStorage).forEach(k => {
          if (k.startsWith(LIKES_PREFIX)) localStorage.removeItem(k);
        });
        document.getElementById('reset-confirm')?.classList.add('hidden');
        location.reload();
      }).catch(() => {
        alert('Failed to reset taste profile.');
      });
    },

    // ── Festival List ──

    _loadFestivals() {
      fetch('/api/festivals/')
        .then(r => r.json())
        .then(data => {
          this.festivals = data;
          this._renderFestivalList();
          const initial = window.__initialFestivalSlug;
          if (initial) {
            const f = data.find(f => f.slug === initial);
            if (f) this.selectFestival(f.id);
          } else if (data.length > 0) {
            this.selectFestival(data[0].id);
          }
        });
    },

    _renderFestivalList() {
      const container = document.getElementById('festival-list-items');
      if (!container) return;
      container.innerHTML = this.festivals.map(f => `
        <div class="festival-item" data-festival-id="${f.id}" onclick="App.selectFestival(${f.id})">
          <div class="festival-item-name">${f.name}</div>
          <div class="festival-item-meta">${f.location} · ${f.start_date} – ${f.end_date} · ${f.artist_count} artists</div>
        </div>
      `).join('');
    },

    // ── Festival Selection ──

    selectFestival(festivalId) {
      this.currentFestivalId = festivalId;
      document.querySelectorAll('.festival-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.festivalId) === festivalId);
      });
      document.getElementById('empty-state')?.classList.add('hidden');
      const detail = document.getElementById('festival-detail');
      if (detail) detail.classList.remove('hidden');
      this._loadLineup(festivalId);
    },

    _loadLineup(festivalId) {
      fetch(`/api/festivals/${festivalId}/lineup/`)
        .then(r => r.json())
        .then(data => {
          this.lineupData = data;
          this._renderFestivalHeader(data.festival);
          this._renderDayTabs(data);
          this._renderTimetable(data);
          this._restoreFestivalLikes(festivalId);
          this._fetchRecs();
        });
    },

    _renderFestivalHeader(festival) {
      const el = document.getElementById('festival-header');
      if (!el) return;
      el.innerHTML = `
        <h2>${festival.name}</h2>
        <div class="festival-meta">${festival.location} · ${festival.start_date} – ${festival.end_date}</div>
      `;
    },

    // ── Day Tabs ──

    _renderDayTabs(data) {
      const container = document.getElementById('day-tabs');
      if (!container) return;
      const startDate = new Date(data.festival.start_date);
      container.innerHTML = data.days.map((day, i) => {
        const d = new Date(startDate);
        d.setDate(startDate.getDate() + day.day - 1);
        const label = d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
        return `<button class="day-tab${i === 0 ? ' active' : ''}" data-day="${day.day}" onclick="App.selectDay(${day.day})">${label}</button>`;
      }).join('');
      this.activeDay = data.days.length > 0 ? data.days[0].day : null;
    },

    selectDay(day) {
      this.activeDay = day;
      document.querySelectorAll('.day-tab').forEach(tab => {
        tab.classList.toggle('active', parseInt(tab.dataset.day) === day);
      });
      document.querySelectorAll('.timetable-day').forEach(td => {
        td.classList.toggle('hidden', parseInt(td.dataset.day) !== day);
      });
    },

    // ── Timetable ──

    _renderTimetable(data) {
      const container = document.getElementById('lineup-container');
      if (!container) return;
      if (!data.days || data.days.length === 0) {
        container.innerHTML = '<p class="empty-lineup">No lineup announced yet.</p>';
        return;
      }

      const startDate = new Date(data.festival.start_date);

      container.innerHTML = data.days.map(day => {
        const dayDate = new Date(startDate);
        dayDate.setDate(startDate.getDate() + day.day - 1);
        const stageNames = ['Apex', 'Opus', 'Dogtooth', 'Avalanche'].filter(s => s in day.stages);
        const allSlots = Object.values(day.stages).flat();
        const { minMinutes, maxMinutes } = this._getTimeRange(allSlots);
        const rowCount = Math.ceil((maxMinutes - minMinutes) / ROW_MINUTES);
        const totalHeight = Math.max(rowCount * MIN_ROW_HEIGHT, 200);

        const timeRows = this._generateTimeSlots(minMinutes, maxMinutes);

        return `
          <div class="timetable-day${this.activeDay === day.day ? '' : ' hidden'}" data-day="${day.day}">
            <div class="timetable-desktop">
              <div class="timetable-header-row">
                <div class="timetable-time-col"></div>
                ${stageNames.map(s => `<div class="timetable-stage-header">${s}</div>`).join('')}
              </div>
              <div class="timetable-scroll">
                <div class="timetable-body" style="height: ${totalHeight}px">
                  <div class="timetable-time-axis" style="height: ${totalHeight}px">
                    ${timeRows.map(t => {
                      const offset = ((t - minMinutes) / (maxMinutes - minMinutes)) * totalHeight;
                      const label = t % 60 === 0 ? this._minutesToTime(t) : '';
                      return `<div class="timetable-time-marker" style="top: ${offset}px">${label}</div>`;
                    }).join('')}
                  </div>
                  <div class="timetable-stage-cols">
                    ${stageNames.map(stage => `
                      <div class="timetable-stage-col">
                        ${(day.stages[stage] || []).map(a => {
                          if (!a.start_time) return '';
                          const top = this._getOffset(a, minMinutes, maxMinutes, totalHeight);
                          const height = this._getBlockHeight(a, minMinutes, maxMinutes, totalHeight);
                          if (height < 20) return '';
                          const duration = this._formatDuration(a);
                          return `
                            <div class="artist-card" data-artist-id="${a.artist.id}"
                                 style="top: ${top}px; height: ${height}px">
                              <div class="artist-card-inner">
                                <div class="artist-card-name">${a.artist.name}</div>
                                <div class="artist-card-time">${duration}</div>
                              </div>
                              <button class="heart-btn" data-artist-id="${a.artist.id}" onclick="event.stopPropagation();App.toggleLike(${a.artist.id})">♡</button>
                            </div>
                          `;
                        }).join('')}
                      </div>
                    `).join('')}
                  </div>
                </div>
              </div>
            </div>

            <div class="timetable-mobile">
              ${stageNames.map(stage => `
                <div class="mobile-stage-group">
                  <h4 class="stage-name">${stage}</h4>
                  ${(day.stages[stage] || []).map(a => {
                    const duration = this._formatDuration(a);
                    return `
                      <div class="artist-card" data-artist-id="${a.artist.id}">
                        <div class="artist-card-inner">
                          <div class="artist-card-name">${a.artist.name}</div>
                          <div class="artist-card-time">${duration}</div>
                          ${a.artist.genre_tags && a.artist.genre_tags.length > 0 ? `
                            <div class="artist-card-tags">
                              ${a.artist.genre_tags.slice(0, 2).map(t => `<span class="artist-tag">${t}</span>`).join('')}
                            </div>
                          ` : ''}
                        </div>
                        <button class="heart-btn" data-artist-id="${a.artist.id}" onclick="event.stopPropagation();App.toggleLike(${a.artist.id})">♡</button>
                      </div>
                    `;
                  }).join('')}
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }).join('');
    },

    _getTimeRange(slots) {
      let min = Infinity, max = -Infinity;
      slots.forEach(s => {
        if (s.start_time) {
          const [h, m] = s.start_time.split(':').map(Number);
          if (h * 60 + m < min) min = h * 60 + m;
        }
        if (s.end_time) {
          const [h, m] = s.end_time.split(':').map(Number);
          if (h * 60 + m > max) max = h * 60 + m;
        }
      });
      if (!isFinite(min)) min = 600;
      if (!isFinite(max)) max = 1380;
      min = Math.floor(min / ROW_MINUTES) * ROW_MINUTES;
      max = Math.ceil(max / ROW_MINUTES) * ROW_MINUTES;
      return { minMinutes: min, maxMinutes: max };
    },

    _generateTimeSlots(min, max) {
      const slots = [];
      for (let t = min; t <= max; t += ROW_MINUTES) {
        slots.push(t);
      }
      return slots;
    },

    _minutesToTime(m) {
      const h = Math.floor(m / 60);
      const min = m % 60;
      return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
    },

    _getOffset(artist, minMinutes, maxMinutes, totalHeight) {
      const [h, m] = artist.start_time.split(':').map(Number);
      const start = h * 60 + m;
      const total = maxMinutes - minMinutes;
      if (total <= 0) return 0;
      return ((start - minMinutes) / total) * totalHeight;
    },

    _getBlockHeight(artist, minMinutes, maxMinutes, totalHeight) {
      if (!artist.end_time) return MIN_ROW_HEIGHT;
      const [sh, sm] = artist.start_time.split(':').map(Number);
      const [eh, em] = artist.end_time.split(':').map(Number);
      const duration = (eh * 60 + em) - (sh * 60 + sm);
      const total = maxMinutes - minMinutes;
      if (total <= 0) return MIN_ROW_HEIGHT;
      return Math.max(MIN_ROW_HEIGHT, (duration / total) * totalHeight);
    },

    _formatDuration(artist) {
      if (!artist.start_time || !artist.end_time) return '';
      const fmt = (t) => t.slice(0, 5).replace(/^0/, '');
      return `${fmt(artist.start_time)} – ${fmt(artist.end_time)}`;
    },

    // ── Likes ──

    _restoreLikes() {
      const stored = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(LIKES_PREFIX)) {
          const festivalId = parseInt(key.slice(LIKES_PREFIX.length));
          try {
            stored[festivalId] = new Set(JSON.parse(localStorage.getItem(key)));
          } catch (e) {
            stored[festivalId] = new Set();
          }
        }
      }
      this.likedArtists = stored;
    },

    _restoreFestivalLikes(festivalId) {
      const liked = this.likedArtists[festivalId];
      if (!liked) return;
      document.querySelectorAll(`.heart-btn`).forEach(btn => {
        const id = parseInt(btn.dataset.artistId);
        if (liked.has(id)) {
          btn.textContent = '\u2665';
          btn.classList.add('liked');
        }
      });
    },

    toggleLike(artistId) {
      if (!this.currentFestivalId) return;
      if (!this.likedArtists[this.currentFestivalId]) {
        this.likedArtists[this.currentFestivalId] = new Set();
      }
      const liked = this.likedArtists[this.currentFestivalId];
      const btns = document.querySelectorAll(`.heart-btn[data-artist-id="${artistId}"]`);
      if (liked.has(artistId)) {
        liked.delete(artistId);
        btns.forEach(btn => { btn.textContent = '\u2661'; btn.classList.remove('liked'); });
        this._sendUnlike(artistId);
      } else {
        liked.add(artistId);
        btns.forEach(btn => { btn.textContent = '\u2665'; btn.classList.add('liked'); });
        this._sendLike(artistId);
      }
      this._saveLikes();
      this._fetchRecs();
    },

    _sendLike(artistId) {
      navigator.sendBeacon('/api/taste/like/', JSON.stringify({
        session_id: this.sessionId, festival_id: this.currentFestivalId, artist_id: artistId,
      }));
    },

    _sendUnlike(artistId) {
      navigator.sendBeacon('/api/taste/unlike/', JSON.stringify({
        session_id: this.sessionId, festival_id: this.currentFestivalId, artist_id: artistId,
      }));
    },

    _saveLikes() {
      Object.entries(this.likedArtists).forEach(([festivalId, artistSet]) => {
        localStorage.setItem(`${LIKES_PREFIX}${festivalId}`, JSON.stringify([...artistSet]));
      });
    },

    // ── Recommendations ──

    _fetchRecs() {
      const liked = this.likedArtists[this.currentFestivalId];
      if (!liked || liked.size === 0) {
        document.getElementById('recs-section')?.classList.add('hidden');
        return;
      }
      if (this.recsLoading) return;
      this.recsLoading = true;
      fetch('/api/recommendations/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          session_id: this.sessionId,
          festival_id: this.currentFestivalId,
          liked_artist_ids: [...liked],
          max_results: 10,
        }),
      })
        .then(r => r.json())
        .then(data => this._renderRecs(data.recommendations))
        .finally(() => { this.recsLoading = false; });
    },

    _renderRecs(recs) {
      const section = document.getElementById('recs-section');
      const list = document.getElementById('recs-list');
      const count = document.getElementById('recs-count');
      if (!section || !list) return;
      if (!recs || recs.length === 0) {
        section.classList.add('hidden');
        return;
      }
      section.classList.remove('hidden');
      if (count) count.textContent = `(${recs.length})`;
      list.innerHTML = recs.map(r => `
        <div class="rec-card" data-artist-id="${r.artist.id}">
          <div class="rec-match-bar" style="width: ${Math.round(r.score * 100)}%"></div>
          <div class="rec-body">
            <div class="rec-header">
              <span class="rec-artist-name">${r.artist.name}</span>
              <span class="rec-score">${Math.round(r.score * 100)}%</span>
            </div>
            <div class="rec-reason">${r.reason.evidence?.[0] || 'Recommended for you'}</div>
            ${r.festival_info.stage ? `<div class="rec-evidence">${r.festival_info.stage} · Day ${r.festival_info.day}</div>` : ''}
            <div class="rec-actions">
              <button onclick="App.sendFeedback(${r.artist.id}, 'good_shout', this)">Good shout</button>
              <button onclick="App.sendFeedback(${r.artist.id}, 'not_for_me', this)">Not for me</button>
              <button onclick="App.sendFeedback(${r.artist.id}, 'already_know', this)">Already know them</button>
            </div>
          </div>
        </div>
      `).join('');
    },

    sendFeedback(artistId, feedback, btn) {
      const liked = this.likedArtists[this.currentFestivalId];
      fetch('/api/feedback/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          session_id: this.sessionId,
          festival_id: this.currentFestivalId,
          recommended_artist_id: artistId,
          liked_artist_ids: liked ? [...liked] : [],
          feedback,
        }),
      }).then(() => {
        const card = btn.closest('.rec-card');
        if (card) {
          card.querySelectorAll('.rec-actions button').forEach(b => { b.disabled = true; });
          btn.classList.add('active');
        }
      }).catch(() => {
        btn.classList.add('active');
      });
    },
  };

  window.App = App;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
  } else {
    App.init();
  }
})();
