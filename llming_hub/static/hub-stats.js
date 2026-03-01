/**
 * hub-stats.js — Statistics widget
 */

class StatsWidget extends HubWidget {
  constructor() {
    super('stats', {
      icon: 'bar_chart',
      titleKey: 'stats_title',
      titleDefault: 'Statistics',
      priority: 5,
    });
  }

  onData(data) {
    if (!this.bodyEl) return;

    if (data.error) {
      this.showError(data.error);
      return;
    }

    const rows = data.rows || [];
    const todayLabel = _esc(this.i18n.stats_today || 'Today');
    const weekLabel = _esc(this.i18n.stats_this_week || 'This Week');

    let html = `
      <div class="hub-stats-grid">
        <div class="hub-stats-header"></div>
        <div class="hub-stats-header hub-stats-center">${todayLabel}</div>
        <div class="hub-stats-header hub-stats-center">${weekLabel}</div>
    `;
    for (const row of rows) {
      html += `
        <div class="hub-stats-label">
          <span class="material-icons" style="font-size:16px;color:${_esc(row.color || '#888')}">${_esc(row.icon)}</span>
          <span>${_esc(row.label)}</span>
        </div>
        <div class="hub-stats-center">${row.today}</div>
        <div class="hub-stats-center">${row.week}</div>
      `;
    }
    html += '</div>';

    this.bodyEl.innerHTML = html;
  }
}

HubFeatures.registerWidget(new StatsWidget());
