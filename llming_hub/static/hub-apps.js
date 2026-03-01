/**
 * hub-apps.js — Applications subapp
 *
 * Renders the app card grid and header. All branding from config.
 */

HubFeatures.register('apps', {
  initState(app) {
    app.apps = [];
  },

  renderHTML(app) {
    const cfg = app.config;
    const i18n = cfg.i18n || {};
    const branding = cfg.branding || {};

    // Dev overrides banner
    const devBannerUrl = branding.devOverridesUrl || '/admin/dev';
    const devBanner = cfg.devOverrides
      ? `<a href="${_esc(devBannerUrl)}" class="hub-dev-banner">${_esc(cfg.devOverridesLabel)}</a>`
      : '';

    // Maintenance banner
    const maintBanner = cfg.bannerHtml
      ? `<div class="hub-maint-banner">${cfg.bannerHtml}</div>`
      : '';

    // Admin + settings links
    const adminUrl = branding.adminUrl || '/admin';
    const settingsUrl = branding.settingsUrl || '/settings';
    const adminLink = cfg.isAdmin
      ? `<a href="${_esc(adminUrl)}" class="hub-header-icon" title="${_esc(i18n.admin_tooltip || '')}">
           <span class="material-icons">admin_panel_settings</span>
         </a>`
      : '';

    // Logo from config
    const logoHtml = branding.logoUrl
      ? `<img src="${_esc(branding.logoUrl)}" alt="" class="hub-logo">`
      : '';

    const titleText = i18n.dashboard_title || branding.appTitle || 'Hub';

    return `
      ${devBanner}
      ${maintBanner}
      <header class="hub-header">
        <div class="hub-header-left">
          <a href="/">
            ${logoHtml}
          </a>
          <span class="hub-title">${_esc(titleText)}</span>
        </div>
        <div class="hub-header-right">
          ${adminLink}
          <a href="${_esc(settingsUrl)}" class="hub-header-icon" title="${_esc(i18n.settings_tooltip || '')}">
            <span class="material-icons">settings</span>
          </a>
          <img src="${_esc(cfg.userAvatar || '')}" alt="" class="hub-avatar" onerror="this.style.display='none'">
        </div>
      </header>
      <div class="hub-greeting">
        ${branding.mascotUrl ? `<img src="${_esc(branding.mascotUrl)}" alt="" class="hub-greeting-mascot">` : ''}
        <span>${_esc(cfg.greeting || '')}</span>
      </div>
      <section class="hub-apps-section" id="hub-apps-grid">
        <div class="hub-apps-grid">
          ${(cfg.apps || []).map(a => `
            <a href="${_esc(a.route)}" class="hub-app-card">
              <div class="hub-app-icon-ring">
                <span class="material-icons hub-app-icon">${_esc(a.icon)}</span>
              </div>
              <div class="hub-app-text">
                <span class="hub-app-label">${_esc(a.name)}</span>
                ${a.desc ? `<span class="hub-app-desc">${_esc(a.desc)}</span>` : ''}
              </div>
            </a>
          `).join('')}
        </div>
      </section>
    `;
  },

  bindEvents(app) {
    // App cards already use <a href> — no JS binding needed
  },

  handleMessage: {
    // hub_init is handled by core; apps are static from config
  },
});


// Simple HTML escaper
function _esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
