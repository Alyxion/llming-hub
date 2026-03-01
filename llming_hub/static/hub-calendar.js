/**
 * hub-calendar.js — Calendar widget
 */

/* ── show_as color map ─────────────────────────────── */
const _calShowAsColor = {
  busy:             'var(--hub-accent)',
  tentative:        'var(--hub-text-muted)',
  oof:              '#f97316',
  workingElsewhere: '#8b5cf6',
  free:             '#22c55e',
  unknown:          'var(--hub-text-muted)',
};

function _calDotStyle(showAs) {
  return `background:${_calShowAsColor[showAs] || _calShowAsColor.busy}`;
}

function _calEventHtml(ev, i18n) {
  const allDayLabel = i18n.calendar_all_day || 'All day';
  const dot = `<span class="hub-cal-dot" style="${_calDotStyle(ev.show_as)}"></span>`;

  // Time or all-day
  let timeStr;
  if (ev.is_all_day) {
    timeStr = `<span class="hub-cal-allday">${_esc(allDayLabel)}</span>`;
  } else {
    timeStr = `<span class="hub-cal-time">${_esc(ev.time_str)}</span>`;
  }

  // Subject
  const noSubject = i18n.calendar_no_subject || 'No Subject';
  const subjectText = (ev.subject && ev.subject !== 'No Subject') ? ev.subject : noSubject;
  const subject = `<span class="hub-cal-subject">${_esc(subjectText)}</span>`;

  // Indicator icons (no separate links)
  let icons = '';
  if (ev.is_private) {
    icons += `<span class="material-icons hub-cal-icon" title="${_esc(i18n.calendar_private || 'Private')}">lock</span>`;
  }
  if (ev.is_teams) {
    icons += `<span class="material-icons hub-cal-icon hub-cal-teams" title="${_esc(i18n.calendar_meeting || 'Meeting')}">videocam</span>`;
  }

  // Attendee avatars (with initials fallback)
  let avatarsHtml = '';
  const attendees = ev.attendees || [];
  if (attendees.length) {
    avatarsHtml = '<span class="hub-cal-avatars">' +
      attendees.map(a => {
        const ini = _esc(a.initials || '?');
        return `<span class="hub-cal-avatar-wrap" title="${_esc(a.name)}">` +
          `<img class="hub-cal-avatar" src="${_esc(a.avatar)}" alt="${_esc(a.name)}" ` +
            `onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">` +
          `<span class="hub-cal-avatar-initials" style="display:none">${ini}</span>` +
        `</span>`;
      }).join('') + '</span>';
  }

  const idx = ev._idx != null ? ev._idx : '';
  const href = _safeHref(ev.web_link) || '';
  const tag = href ? 'a' : 'div';
  const hrefAttr = href ? ` href="${_esc(href)}" target="_blank"` : '';

  return `<${tag} class="hub-cal-event${ev.is_all_day ? ' hub-cal-event--allday' : ''}"${hrefAttr} data-cal-idx="${idx}"><div class="hub-cal-event-main">${dot}${timeStr}${subject}${icons}</div>${avatarsHtml}</${tag}>`;
}


class CalendarWidget extends HubWidget {
  constructor() {
    super('calendar', {
      icon: 'calendar_today',
      titleKey: 'calendar_title',
      titleDefault: 'Calendar',
      canTall: true,
      priority: 1,
    });
    this.events = [];
  }

  renderBadgeExtra() {
    const calUrl = (this.config.branding && this.config.branding.calendarExternalUrl) || '';
    if (!calUrl) return '';
    return `<a class="hub-widget-open" href="${_esc(calUrl)}" target="_blank" title="${_esc(this.i18n.calendar_open_external || 'Open Calendar')}">
             <span class="material-icons">open_in_new</span>
           </a>`;
  }

  bodyScrollable() { return true; }

  onData(data) {
    if (!this.bodyEl) return;

    if (data.error) {
      this.showError(data.error);
      return;
    }

    const events = data.events || [];

    if (events.length === 0) {
      this.bodyEl.innerHTML = `<div class="hub-cal-empty">${_esc(this.i18n.calendar_no_events || 'No upcoming events')}</div>`;
      return;
    }

    let html = '';
    let lastDateLabel = null;

    for (const ev of events) {
      const dl = ev.date_label || '';
      if (dl !== lastDateLabel) {
        if (dl) {
          html += `<div class="hub-cal-day-label">${_esc(dl)}</div>`;
        }
        lastDateLabel = dl;
      }
      html += _calEventHtml(ev, this.i18n);
    }

    this.bodyEl.innerHTML = html;

    this.events = events;
    _hubBindHover(this.bodyEl, '.hub-cal-event', (el) => this._buildPopup(el));
  }

  _buildPopup(item) {
    const idx = parseInt(item.dataset.calIdx, 10);
    if (isNaN(idx)) return null;
    const ev = this.events[idx];
    if (!ev) return null;

    const noSubj = this.i18n.calendar_no_subject || 'No Subject';
    const subject = _esc((ev.subject && ev.subject !== 'No Subject') ? ev.subject : noSubj);
    const time = ev.is_all_day
      ? _esc(this.i18n.calendar_all_day || 'All day')
      : _esc(ev.time_str || '');
    const dateLabel = _esc(ev.date_label || '');
    const location = _esc(ev.location || '');
    const showAs = _esc(ev.show_as || 'busy');

    // Attendees list
    const attendees = ev.attendees || [];
    let attendeesHtml = '';
    if (attendees.length) {
      attendeesHtml = `
        <hr class="hub-popup-divider">
        <div class="hub-popup-cal-attendees">
          ${attendees.map(a => `<span class="hub-popup-cal-attendee">${_esc(a.name)}</span>`).join('')}
        </div>
      `;
    }

    // Meeting link
    const meetUrl = _safeHref(ev.online_meeting_url);
    const meetLabel = _esc(this.i18n.calendar_online_meeting || 'Online Meeting');
    const meetHtml = meetUrl
      ? `<div class="hub-popup-row"><span class="material-icons" style="color:#6264a7">videocam</span> ${meetLabel}</div>` : '';

    // Translate show_as
    const showAsKey = 'calendar_show_as_' + (ev.show_as || 'unknown');
    const showAsLabel = _esc(this.i18n[showAsKey] || showAs);

    return `
      <div class="hub-popup-body">
        <div class="hub-popup-cal-time">${dateLabel ? dateLabel + ' \u00b7 ' : ''}${time}</div>
        <div class="hub-popup-title">${subject}</div>
        ${location ? `<div class="hub-popup-row"><span class="material-icons">location_on</span> ${location}</div>` : ''}
        ${meetHtml}
        <div class="hub-popup-row">
          <span class="hub-cal-dot" style="${_calDotStyle(ev.show_as)};width:8px;height:8px;border-radius:50%;flex-shrink:0"></span>
          ${showAsLabel}
        </div>
        ${attendeesHtml}
      </div>
    `;
  }
}

HubFeatures.registerWidget(new CalendarWidget());
