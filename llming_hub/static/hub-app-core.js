/**
 * hub-app-core.js — HubApp constructor, init, render, bindEvents, boot
 *
 * Loaded LAST — after hub-features.js, hub-ws.js, and all feature modules.
 * Defines core prototype, routes widget_data via HubWidget auto-dispatch, boots.
 */

// ── Build merged message handler dispatch table ──
const _hubMessageHandlers = HubFeatures.messageHandlers();

// ── Core prototype methods ──────────────────────────────────

Object.assign(HubApp.prototype, {

  _init_constructor(config) {
    this.config = config;
    this.ws = null;
    this.sessionId = config.sessionId;
    this.userName = config.userName || '';

    // Feature state
    HubFeatures.initAllState(this);
  },

  async init() {
    this.render();
    this.bindEvents();
    this._connectWS();
  },

  render() {
    const root = document.getElementById('hub-app');
    if (!root) return;

    // Build HTML from all registered features
    const featureHTML = HubFeatures.renderAllHTML(this);

    root.innerHTML = `
      <div class="hub-container">
        <div class="hub-bg"></div>
        <div class="hub-scroll">
          ${featureHTML}
          <div class="hub-widgets-wrap" id="hub-widgets-wrap">
            <button class="hub-scroll-hint hub-scroll-hint--left" id="hub-scroll-hint-left" aria-label="Scroll left">
              <span class="material-icons">chevron_left</span>
            </button>
            <div class="hub-widgets-viewport" id="hub-widgets-viewport">
              <section class="hub-widgets-section" id="hub-widgets-section"></section>
            </div>
            <button class="hub-scroll-hint hub-scroll-hint--right" id="hub-scroll-hint-right" aria-label="Scroll right">
              <span class="material-icons">chevron_right</span>
            </button>
          </div>
        </div>
      </div>
    `;

    // Apply theme (after innerHTML so .hub-bg exists)
    this._applyTheme(root);

    // Move widget elements into the widgets section sorted by priority
    const widgetsSection = document.getElementById('hub-widgets-section');
    if (widgetsSection) {
      const widgets = Array.from(root.querySelectorAll('.hub-widget'));
      widgets.sort((a, b) => {
        return (parseInt(a.dataset.priority, 10) || 99)
             - (parseInt(b.dataset.priority, 10) || 99);
      });
      for (const w of widgets) {
        widgetsSection.appendChild(w);
      }
    }

    // Cache DOM refs
    HubFeatures.cacheAllEls(this);

    // Run initial layout
    this._layoutWidgets();
  },

  bindEvents() {
    HubFeatures.bindAllEvents(this);

    // Theme toggle via keyboard (T key)
    document.addEventListener('keydown', (e) => {
      if (e.key === 't' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const target = e.target;
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;
        this._toggleTheme();
      }
    });

    // Scroll hint arrows
    const hintL = document.getElementById('hub-scroll-hint-left');
    const hintR = document.getElementById('hub-scroll-hint-right');
    if (hintR) hintR.addEventListener('click', () => this._scrollWidgets(1));
    if (hintL) hintL.addEventListener('click', () => this._scrollWidgets(-1));

    // Re-layout on resize (debounced)
    let resizeTimer = null;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => this._layoutWidgets(), 150);
    });
  },

  handleMessage(msg) {
    const type = msg.type;

    // Widget data dispatch — auto-route to HubWidget subclass
    if (type === 'widget_data') {
      const widget = HubFeatures.getWidget(msg.widget_id);
      if (widget) widget.onData(msg.data);
      return;
    }

    // hub_init — already handled on WS connect, but features may want it
    if (type === 'hub_init') {
      return;
    }

    // Feature handlers
    const handler = _hubMessageHandlers[type];
    if (typeof handler === 'function') return handler(this, msg);
    if (typeof handler === 'string' && typeof this[handler] === 'function') return this[handler](msg);

    console.debug('[HUB] Unknown message type:', type);
  },

  // ── WebSocket ───────────────────────────────────────────

  _connectWS() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}${this.config.wsPath}`;

    this.ws = new HubWebSocket(url, {
      onMessage: (msg) => this.handleMessage(msg),
      onOpen: () => {
        console.log('[HUB] WebSocket connected');
        this._setConnectionStatus('connected');
      },
      onClose: (e) => {
        console.log('[HUB] WebSocket closed:', e.code);
        this._setConnectionStatus('disconnected');
      },
      onError: () => {
        this._setConnectionStatus('error');
      },
    });
    this.ws.connect();
  },

  _setConnectionStatus(status) {
    const root = document.getElementById('hub-app');
    if (root) root.dataset.wsStatus = status;
  },

  // ── Layout Engine ─────────────────────────────────────────

  _layoutWidgets() {
    const wrap = document.getElementById('hub-widgets-wrap');
    const section = document.getElementById('hub-widgets-section');
    if (!section || !wrap) return;
    const widgets = Array.from(section.querySelectorAll('.hub-widget'));
    const N = widgets.length;
    if (!N) return;

    // Reset
    for (const el of widgets) el.classList.remove('hub-widget--tall');
    section.classList.remove('hub-widgets--mobile');
    section.style.transform = '';

    const W = 351;        // minimum widget width
    const GAP = 16;       // grid gap
    const MIN_H = 180;    // minimum widget height
    const MAX_H = 400;    // maximum single-row height
    const MIN_PAD = 24;   // minimum bottom padding

    const availW = wrap.clientWidth;
    const availH = wrap.clientHeight;

    // How many columns fit at minimum width?
    const visCols = Math.max(1, Math.floor((availW + GAP) / (W + GAP)));

    // Single column → mobile horizontal scroll (one widget at a time)
    if (visCols <= 1) {
      const mobileW = availW - 16;
      section.classList.add('hub-widgets--mobile');
      section.style.gridTemplateColumns = `repeat(${N}, ${mobileW}px)`;
      section.style.gridTemplateRows = `${availH}px`;

      // Constrain viewport to show one widget at a time
      const viewport = document.getElementById('hub-widgets-viewport');
      if (viewport) {
        viewport.style.width = `${mobileW}px`;
        viewport.style.overflow = 'hidden';
      }
      section.style.justifyContent = 'start';

      this._scrollState = {
        totalCols: N, visCols: 1, W: mobileW, GAP,
        offset: 0, maxOffset: N - 1,
      };
      this._updateScrollHints();
      return;
    }

    // Determine layout: prefer single row on desktop (≥3 visCols),
    // use multiple rows on narrower screens or when everything fits.
    let rows;
    if (visCols >= N) {
      // All widgets fit in one row — no scroll needed
      rows = 1;
    } else if (visCols >= 3) {
      // Desktop: prefer single row with horizontal scroll
      rows = 1;
    } else {
      // Narrow (2 visCols): use multiple rows if height allows
      rows = 1;
      for (let r = 2; r <= 3; r++) {
        const rowH = Math.floor((availH - MIN_PAD - (r - 1) * GAP) / r);
        if (rowH < MIN_H) break;
        rows = r;
        if (Math.ceil(N / r) <= visCols) break; // all fit — done
      }
    }

    const totalCols = Math.ceil(N / rows);

    // Compute row height to fill available space (capped)
    const H = Math.min(
      Math.floor((availH - MIN_PAD - (rows - 1) * GAP) / rows),
      MAX_H
    );

    section.style.gridTemplateColumns = `repeat(${totalCols}, ${W}px)`;
    section.style.gridTemplateRows = `repeat(${rows}, ${H}px)`;

    // Fill empty slots with double-height widgets (by priority order)
    if (rows >= 2) {
      const totalSlots = totalCols * rows;
      let empty = totalSlots - N;
      for (const el of widgets) {
        if (empty <= 0) break;
        if (el.dataset.canTall === 'true') {
          if (2 * H + GAP <= availH - MIN_PAD) {
            el.classList.add('hub-widget--tall');
            empty--;
          }
        }
      }
    }

    // Size the viewport to show exactly visCols whole widgets
    const hasOverflow = totalCols > visCols;
    const viewport = document.getElementById('hub-widgets-viewport');
    const showCols = Math.min(totalCols, visCols);
    const visibleW = showCols * W + (showCols - 1) * GAP;

    if (viewport) {
      if (hasOverflow) {
        viewport.style.width = `${visibleW}px`;
        viewport.style.overflow = 'hidden';
        section.style.justifyContent = 'start';
      } else {
        viewport.style.width = '';
        viewport.style.overflow = '';
        section.style.justifyContent = '';
      }
    }

    this._scrollState = hasOverflow ? {
      totalCols, visCols: showCols, W, GAP,
      offset: 0,
      maxOffset: totalCols - showCols,
    } : null;
    this._updateScrollHints();
  },

  _scrollWidgets(dir) {
    const s = this._scrollState;
    if (!s) return;
    const section = document.getElementById('hub-widgets-section');
    if (!section) return;

    s.offset = Math.max(0, Math.min(s.maxOffset, s.offset + dir));
    const px = s.offset * (s.W + s.GAP);
    section.style.transform = `translateX(-${px}px)`;
    this._updateScrollHints();
  },

  _updateScrollHints() {
    const s = this._scrollState;
    const hintL = document.getElementById('hub-scroll-hint-left');
    const hintR = document.getElementById('hub-scroll-hint-right');
    if (hintL) hintL.classList.toggle('hub-scroll-hint--visible', !!(s && s.offset > 0));
    if (hintR) hintR.classList.toggle('hub-scroll-hint--visible', !!(s && s.offset < s.maxOffset));
  },

  // ── Theme ───────────────────────────────────────────────

  _applyTheme(root) {
    const stored = localStorage.getItem('chat-color-mode');
    // Default to dark if no preference set
    const isDark = !stored || stored === 'dark' || stored === 'auto';
    root.classList.toggle('cv2-dark', isDark);

    // Apply branding CSS variables
    const branding = this.config.branding || {};
    if (branding.accentColor) {
      root.style.setProperty('--hub-accent', branding.accentColor);
    }

    // Set background image from config
    const bgEl = root.querySelector('.hub-bg');
    if (bgEl) {
      const darkUrl = branding.bgDarkUrl || '';
      const lightUrl = branding.bgLightUrl || '';
      const url = isDark ? darkUrl : lightUrl;
      bgEl.style.backgroundImage = url ? `url(${url})` : 'none';
    }
  },

  _toggleTheme() {
    const root = document.getElementById('hub-app');
    if (!root) return;
    const isDark = root.classList.toggle('cv2-dark');
    localStorage.setItem('chat-color-mode', isDark ? 'dark' : 'light');

    const branding = this.config.branding || {};
    const bgEl = root.querySelector('.hub-bg');
    if (bgEl) {
      const darkUrl = branding.bgDarkUrl || '';
      const lightUrl = branding.bgLightUrl || '';
      const url = isDark ? darkUrl : lightUrl;
      bgEl.style.backgroundImage = url ? `url(${url})` : 'none';
    }
  },
});


// ── Boot ─────────────────────────────────────────────────

(function boot() {
  const config = window.__HUB_CONFIG__;
  if (!config) {
    console.error('[HUB] No __HUB_CONFIG__ found');
    return;
  }
  delete window.__HUB_CONFIG__;

  const app = new HubApp();
  app._init_constructor(config);
  app.init();
  window._hubApp = app;
})();
