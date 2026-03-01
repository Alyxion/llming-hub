/**
 * hub-news.js — News feed widget with channel tabs
 */

class NewsWidget extends HubWidget {
  constructor() {
    super('news', {
      icon: 'feed',
      titleKey: 'news_title',
      titleDefault: 'News',
      canTall: true,
      priority: 3,
    });
    this.allArticles = [];
    this.channels = [];
    this.activeChannel = 'All';
    this.articles = [];
  }

  renderBadgeExtra() {
    const newsUrl = (this.config.branding && this.config.branding.newsExternalUrl) || '';
    if (!newsUrl) return '';
    return `<a class="hub-widget-open" href="${_esc(newsUrl)}" target="_blank" title="${_esc(this.i18n.news_open_external || 'Open News')}">
             <span class="material-icons">open_in_new</span>
           </a>`;
  }

  renderTabs() {
    return '<div class="hub-widget-tabs" id="hub-news-tabs" style="display:none"></div>';
  }

  cacheEls() {
    super.cacheEls();
    this.tabsEl = document.getElementById('hub-news-tabs');
  }

  onData(data) {
    if (!this.bodyEl) return;

    if (data.error) {
      this.showError(data.error);
      return;
    }

    this.allArticles = data.articles || [];
    this.channels = data.channels || [];

    // Render channel tabs if more than one channel
    if (this.channels.length > 1 && this.tabsEl) {
      this.tabsEl.style.display = 'flex';
      const _tabLabel = (ch) => {
        if (ch === 'All') return this.i18n.news_tab_all || ch;
        if (ch === 'Global') return this.i18n.news_tab_global || ch;
        return ch;
      };
      this.tabsEl.innerHTML = this.channels.map(ch =>
        `<button class="hub-widget-tab${this.activeChannel === ch ? ' hub-widget-tab--active' : ''}" data-channel="${_esc(ch)}">${_esc(_tabLabel(ch))}</button>`
      ).join('');
      this.tabsEl.querySelectorAll('.hub-widget-tab').forEach(btn => {
        btn.addEventListener('click', () => {
          this.activeChannel = btn.dataset.channel;
          this._renderList();
          this.tabsEl.querySelectorAll('.hub-widget-tab').forEach(b =>
            b.classList.toggle('hub-widget-tab--active', b.dataset.channel === this.activeChannel)
          );
        });
      });
    } else if (this.tabsEl) {
      this.tabsEl.style.display = 'none';
    }

    this._renderList();
  }

  _renderList() {
    if (!this.bodyEl) return;
    const ch = this.activeChannel || 'All';

    // Filter
    let articles;
    if (ch === 'All') {
      articles = this.allArticles;
    } else if (ch === 'Global') {
      articles = this.allArticles.filter(a => !a.channel);
    } else if (ch === 'Local') {
      articles = this.allArticles.filter(a => !!a.channel);
    } else {
      articles = this.allArticles.filter(a => a.channel === ch);
    }

    if (!articles.length) {
      this.bodyEl.innerHTML = `<div class="hub-cal-empty">${_esc(this.i18n.news_no_news || 'No news')}</div>`;
      return;
    }

    this.bodyEl.innerHTML = '<div class="hub-news-list hub-scroll">' + articles.map((a, i) => {
      const thumb = a.image
        ? `<img class="hub-news-thumb" src="${_esc(a.image)}" alt="" loading="lazy">` : '';
      const meta = [a.published, a.author].filter(Boolean).join(' \u00b7 ');
      const href = _safeHref(a.web_link) || '#';

      return `<a class="hub-news-item" href="${_esc(href)}" target="_blank" data-news-idx="${i}">` +
        `${thumb}` +
        `<div class="hub-news-text">` +
          `<div class="hub-news-title">${_esc(a.title)}</div>` +
          `<div class="hub-news-teaser">${_esc(a.teaser)}</div>` +
          `${meta ? `<div class="hub-news-meta">${_esc(meta)}</div>` : ''}` +
        `</div>` +
      `</a>`;
    }).join('') + '</div>';

    this.articles = articles;
    _hubBindHover(this.bodyEl, '.hub-news-item', (el) => this._buildPopup(el));
  }

  _buildPopup(item) {
    const idx = parseInt(item.dataset.newsIdx, 10);
    const a = this.articles[idx];
    if (!a) return null;

    const img = a.image ? `<img class="hub-popup-news-img" src="${_esc(a.image)}" alt="">` : '';
    const meta = [a.published, a.author].filter(Boolean).join(' \u00b7 ');

    return `
      ${img}
      <div class="hub-popup-body">
        <div class="hub-popup-title">${_esc(a.title)}</div>
        <div class="hub-popup-text">${_esc(a.teaser)}</div>
        ${meta ? `<div class="hub-popup-meta">${_esc(meta)}</div>` : ''}
      </div>
    `;
  }
}

HubFeatures.registerWidget(new NewsWidget());
