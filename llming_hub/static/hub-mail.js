/**
 * hub-mail.js — Mail overview widget
 */

class MailWidget extends HubWidget {
  constructor() {
    super('mail', {
      icon: 'mail',
      titleKey: 'mail_title',
      titleDefault: 'Mail',
      canTall: true,
      priority: 2,
    });
    this.messages = [];
  }

  renderBadgeExtra() {
    const mailUrl = (this.config.branding && this.config.branding.mailExternalUrl) || '';
    if (!mailUrl) return '';
    return `<a class="hub-widget-open" href="${_esc(mailUrl)}" target="_blank" title="${_esc(this.i18n.mail_open_external || 'Open Mail')}">
             <span class="material-icons">open_in_new</span>
           </a>`;
  }

  renderInfoSlot() {
    return '<div class="hub-widget-info" id="hub-mail-info"></div>';
  }

  cacheEls() {
    super.cacheEls();
    this.infoEl = document.getElementById('hub-mail-info');
  }

  onData(data) {
    if (!this.bodyEl) return;

    if (data.error) {
      this.showError(data.error);
      return;
    }

    // Stats in info area
    if (this.infoEl) {
      this.infoEl.innerHTML = `
        <span class="hub-widget-info-stat" title="${_esc(this.i18n.mail_total_tooltip || 'Total Mails')}">
          <span class="material-icons">inbox</span>${data.total || 0}
        </span>
        <span class="hub-widget-info-stat hub-widget-info-stat--accent" title="${_esc(this.i18n.mail_unread_tooltip || 'Unread')}">
          <span class="material-icons">mark_email_unread</span>${data.unread || 0}
        </span>
        <span class="hub-widget-info-stat" title="${_esc(this.i18n.mail_new_today_tooltip || 'New Today')}">
          <span class="material-icons">today</span>${data.new_today || 0}
        </span>
      `;
    }

    // Message list
    const msgs = data.messages || [];
    if (!msgs.length) {
      this.bodyEl.innerHTML = '';
      return;
    }

    this.bodyEl.innerHTML = '<div class="hub-mail-list hub-scroll">' + msgs.map((m, i) => {
      const unreadCls = m.is_read ? '' : ' hub-mail-item--unread';
      const sender = _esc(m.from_name || m.from_email || '');
      const _noSubj = this.i18n.mail_no_subject || 'No Subject';
      const subject = _esc((m.subject && m.subject !== 'No Subject') ? m.subject : _noSubj);
      const preview = _esc(m.body_preview || '');
      const time = _esc(m.timestamp || '');
      const importanceIcon = m.importance === 'high'
        ? '<span class="material-icons hub-mail-importance">priority_high</span>' : '';
      const attachIcon = m.has_attachments
        ? '<span class="material-icons hub-mail-attach">attach_file</span>' : '';
      const href = _safeHref(m.web_link) || '#';

      return `<a class="hub-mail-item${unreadCls}" href="${_esc(href)}" target="_blank" data-mail-idx="${i}">` +
        `<div class="hub-mail-item-top">` +
          `${m.is_read ? '' : '<span class="hub-mail-unread-dot"></span>'}` +
          `<span class="hub-mail-sender">${sender}</span>` +
          `<span class="hub-mail-meta">${importanceIcon}${attachIcon}<span class="hub-mail-time">${time}</span></span>` +
        `</div>` +
        `<div class="hub-mail-subject">${subject}</div>` +
        `<div class="hub-mail-preview">${preview}</div>` +
      `</a>`;
    }).join('') + '</div>';

    this.messages = msgs;
    _hubBindHover(this.bodyEl, '.hub-mail-item', (el) => this._buildPopup(el));
  }

  _buildPopup(item) {
    const idx = parseInt(item.dataset.mailIdx, 10);
    const m = this.messages[idx];
    if (!m) return null;

    const sender = _esc(m.from_name || '');
    const email = _esc(m.from_email || '');
    const _noSubjP = this.i18n.mail_no_subject || 'No Subject';
    const subject = _esc((m.subject && m.subject !== 'No Subject') ? m.subject : _noSubjP);
    const preview = _esc(m.body_preview || '');
    const time = _esc(m.timestamp || '');
    const importance = m.importance === 'high'
      ? `<span class="hub-popup-badge"><span class="material-icons" style="font-size:12px;color:#ef4444">priority_high</span> ${_esc(this.i18n.mail_high_importance || 'High')}</span>` : '';
    const attach = m.has_attachments
      ? `<span class="hub-popup-badge"><span class="material-icons" style="font-size:12px">attach_file</span> ${_esc(this.i18n.mail_attachment || 'Attachment')}</span>` : '';
    const unreadBadge = !m.is_read
      ? `<span class="hub-popup-badge" style="color:var(--hub-accent)"><span class="material-icons" style="font-size:12px">mark_email_unread</span> ${_esc(this.i18n.mail_unread_badge || 'Unread')}</span>` : '';

    return `
      <div class="hub-popup-body">
        <div class="hub-popup-mail-sender">${sender}</div>
        ${email ? `<div class="hub-popup-mail-email">${email}</div>` : ''}
        <hr class="hub-popup-divider">
        <div class="hub-popup-title">${subject}</div>
        <div class="hub-popup-text">${preview}</div>
        <div class="hub-popup-meta">
          <span class="material-icons">schedule</span> ${time}
          ${importance} ${attach} ${unreadBadge}
        </div>
      </div>
    `;
  }
}

HubFeatures.registerWidget(new MailWidget());
