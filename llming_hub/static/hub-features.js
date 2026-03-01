/**
 * HubFeatures — Feature registry, widget base class, prototype accumulator
 *
 * Loaded FIRST (before any feature modules or hub-app-core.js).
 * Plain features use HubFeatures.register(name, descriptor).
 * Data widgets extend HubWidget and call HubFeatures.registerWidget(instance).
 * hub-app-core.js boots the app and routes widget_data via auto-dispatch.
 */

// Empty HubApp class — populated by hub-app-core.js
class HubApp {}
window.HubApp = HubApp;

/**
 * Feature + widget registry
 */
const HubFeatures = (() => {
  const _features = {};
  const _widgets = {};

  return {
    register(name, descriptor) {
      _features[name] = descriptor;
    },

    registerWidget(widget) {
      _widgets[widget.id] = widget;
      _features[widget.id] = {
        initState(app) { widget.init(app); },
        renderHTML()    { return widget.renderHTML(); },
        cacheEls()     { widget.cacheEls(); },
        bindEvents()   { widget.bindEvents(); },
        handleMessage:  {},
      };
    },

    getWidget(id) {
      return _widgets[id] || null;
    },

    all() {
      return _features;
    },

    get(name) {
      return _features[name] || null;
    },

    initAllState(app) {
      for (const [, feat] of Object.entries(_features)) {
        if (feat.initState) feat.initState(app);
      }
    },

    renderAllHTML(app) {
      let html = '';
      for (const [, feat] of Object.entries(_features)) {
        if (feat.renderHTML) html += feat.renderHTML(app);
      }
      return html;
    },

    bindAllEvents(app) {
      for (const [, feat] of Object.entries(_features)) {
        if (feat.bindEvents) feat.bindEvents(app);
      }
    },

    cacheAllEls(app) {
      for (const [, feat] of Object.entries(_features)) {
        if (feat.cacheEls) feat.cacheEls(app);
      }
    },

    messageHandlers() {
      const handlers = {};
      for (const [, feat] of Object.entries(_features)) {
        if (feat.handleMessage) {
          Object.assign(handlers, feat.handleMessage);
        }
      }
      return handlers;
    },
  };
})();

window.HubFeatures = HubFeatures;


// ── HubWidget base class ────────────────────────────────────────
class HubWidget {
  constructor(id, { icon, titleKey, titleDefault, canTall = false, priority = 99 }) {
    this.id = id;
    this.icon = icon;
    this.titleKey = titleKey;
    this.titleDefault = titleDefault;
    this.canTall = canTall;
    this.priority = priority;
  }

  // Lifecycle — called via HubFeatures orchestration
  init(app) { this.app = app; }

  renderHTML() {
    if (!this.app.config.activeWidgets.includes(this.id)) return '';
    const title = _esc(this.i18n[this.titleKey] || this.titleDefault);
    const scrollCls = this.bodyScrollable() ? ' hub-scroll' : '';
    return `
      <div class="hub-widget hub-widget-${this.id}" id="hub-${this.id}" data-widget="${this.id}" data-can-tall="${this.canTall}" data-priority="${this.priority}" style="order:${this.priority}">
        <div class="hub-widget-badge">
          <span class="material-icons">${_esc(this.icon)}</span>
          <span>${title}</span>
          ${this.renderBadgeExtra()}
        </div>
        ${this.renderInfoSlot()}
        ${this.renderTabs()}
        <div class="hub-widget-body${scrollCls}" id="hub-${this.id}-body">
          <div class="hub-weather-loading">
            <span class="material-icons hub-spin">refresh</span>
          </div>
        </div>
      </div>
    `;
  }

  cacheEls() {
    this.el = document.getElementById('hub-' + this.id);
    this.bodyEl = document.getElementById('hub-' + this.id + '-body');
  }

  bindEvents() {}

  // Slot methods — override to customise shell (default: '')
  renderBadgeExtra() { return ''; }
  renderInfoSlot()   { return ''; }
  renderTabs()       { return ''; }
  bodyScrollable()   { return false; }

  // Data — the core override point
  onData(data) {}

  // Built-in helpers
  showError(msg) {
    if (this.bodyEl) {
      this.bodyEl.innerHTML = `<div class="hub-widget-error">${_esc(msg)}</div>`;
    }
  }

  showLoading() {
    if (this.bodyEl) {
      this.bodyEl.innerHTML = '<div class="hub-weather-loading"><span class="material-icons hub-spin">refresh</span></div>';
    }
  }

  get i18n()   { return this.app.config.i18n || {}; }
  get config() { return this.app.config; }
}

window.HubWidget = HubWidget;


// ── XSS-safe href — only allows http(s), mailto, relative URLs ──
function _safeHref(url) {
  if (!url) return '';
  const s = String(url).trim();
  if (/^(https?:\/\/|mailto:|\/)/i.test(s)) return s;
  return '';
}


// ── Shared hover popup utility ──────────────────────────────────
let _hubPopup = null;
let _hubPopupTimer = null;

function _hubShowPopup(anchorEl, html, opts) {
  _hubHidePopup();
  const popup = document.createElement('div');
  popup.className = 'hub-popup' + (opts && opts.cls ? ' ' + opts.cls : '');
  popup.innerHTML = html;
  (document.getElementById('hub-app') || document.body).appendChild(popup);
  _hubPopup = popup;

  const rect = anchorEl.getBoundingClientRect();
  const pw = (opts && opts.width) || 340;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const gap = 8;

  const spaceRight = vw - rect.right - gap;
  const spaceLeft = rect.left - gap;
  let left;
  if (spaceRight >= pw) left = rect.right + gap;
  else if (spaceLeft >= pw) left = rect.left - pw - gap;
  else left = Math.max(gap, (vw - pw) / 2);

  const ph = popup.offsetHeight;
  let top = rect.top;
  if (top + ph > vh - gap) top = vh - ph - gap;
  if (top < gap) top = gap;

  popup.style.left = left + 'px';
  popup.style.top = top + 'px';

  popup.addEventListener('mouseenter', () => clearTimeout(_hubPopupTimer));
  popup.addEventListener('mouseleave', _hubHidePopup);
}

function _hubHidePopup() {
  clearTimeout(_hubPopupTimer);
  if (_hubPopup) { _hubPopup.remove(); _hubPopup = null; }
}

function _hubBindHover(container, selector, buildFn) {
  container.querySelectorAll(selector).forEach(el => {
    el.addEventListener('mouseenter', e => {
      const target = e.currentTarget;
      _hubPopupTimer = setTimeout(() => {
        const html = buildFn(target);
        if (html) _hubShowPopup(target, html);
      }, 400);
    });
    el.addEventListener('mouseleave', () => {
      clearTimeout(_hubPopupTimer);
      _hubHidePopup();
    });
  });
}
