/**
 * hub-weather.js — Weather widget with location dropdown
 */

function _weatherDropdownHtml(locations, currentQ) {
  const items = locations.map(loc => {
    const flag = loc.flag ? `<span class="hub-weather-dd-flag">${loc.flag}</span>` : '';
    return `<div class="hub-weather-dd-item${loc.q === currentQ ? ' hub-weather-dd-item--active' : ''}" data-q="${_esc(loc.q)}" data-label="${_esc(loc.label)}">${flag}${_esc(loc.label)}<span class="hub-weather-dd-country">${_esc(loc.country || '')}</span></div>`;
  }).join('');
  return `<div class="hub-weather-dd" style="display:none"><div class="hub-weather-dd-scroll">${items}</div></div>`;
}


class WeatherWidget extends HubWidget {
  constructor() {
    super('weather', {
      icon: 'cloud',
      titleKey: 'weather_title',
      titleDefault: 'Weather',
      priority: 4,
    });
    this.city = '';
    this.cityQ = '';
    this.dropdownOpen = false;
  }

  init(app) {
    super.init(app);
    this.city = app.config.weather_city_display || '';
    this.cityQ = app.config.weather_city || '';
    this._tzOffset = null; // seconds from UTC (null = use local)
  }

  _cityTime() {
    const now = new Date();
    if (this._tzOffset == null) return now;
    const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
    return new Date(utcMs + this._tzOffset * 1000);
  }

  renderInfoSlot() {
    const clockTime = this._cityTime().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return `<div class="hub-widget-info" id="hub-weather-clock"><span>${clockTime}</span></div>`;
  }

  bindEvents() {
    document.addEventListener('click', (e) => {
      if (this.dropdownOpen && !e.target.closest('.hub-weather-loc')) {
        this._closeDropdown();
      }
    });
  }

  onData(data) {
    if (!this.bodyEl) return;

    if (data.error) {
      this.bodyEl.innerHTML = `<div class="hub-weather-city-name">${_esc(data.city || this.city || '')}</div><div class="hub-weather-nodata">${_esc(this.i18n.weather_no_data || 'No data')}</div>`;
      return;
    }

    // Update tracked city and timezone
    if (data.city) this.city = data.city;
    if (data.timezone_offset != null) this._tzOffset = data.timezone_offset;

    const windRotation = ((data.wind_deg || 0) + 180) % 360;
    const detailsUrl = data.city_id ? `https://openweathermap.org/city/${data.city_id}` : '';
    const locations = this.config.weather_locations || [];
    const hasDropdown = locations.length > 1;

    // Upcoming hours with gradient temperature bars
    const upcoming = data.upcoming || [];
    const temps = upcoming.map(h => h.temp);
    const tMin = Math.min(...temps, 0);
    const tMax = Math.max(...temps, 30);
    const tRange = tMax - tMin || 1;
    const upcomingHtml = upcoming.map(h => {
      const pct = ((h.temp - tMin) / tRange);
      const alpha = 0.3 + pct * 0.7;
      const barColor = `rgba(60, 130, 200, ${alpha.toFixed(2)})`;
      return `<div class="hub-weather-hour"><span class="hub-weather-hour-time">${_esc(h.time)}</span><div class="hub-weather-hour-bar" style="background:${barColor}"></div><span class="material-icons hub-weather-hour-icon">${_esc(h.icon)}</span><span class="hub-weather-hour-temp">${h.temp}&deg;</span></div>`;
    }).join('');

    // Multi-day forecast
    const fcDays = data.forecast || [];
    const labelMap = {
      today: this.i18n.weather_today || 'Today',
      tomorrow: this.i18n.weather_tomorrow || 'Tomorrow',
      Mon: this.i18n.weather_mon || 'Mon', Tue: this.i18n.weather_tue || 'Tue',
      Wed: this.i18n.weather_wed || 'Wed', Thu: this.i18n.weather_thu || 'Thu',
      Fri: this.i18n.weather_fri || 'Fri', Sat: this.i18n.weather_sat || 'Sat',
      Sun: this.i18n.weather_sun || 'Sun',
    };
    const forecastHtml = fcDays.length ? `<div class="hub-weather-forecast">${fcDays.map(f => {
      const lbl = labelMap[f.label] || f.label;
      return `<div class="hub-weather-fc-day"><span class="hub-weather-fc-label">${_esc(lbl)}</span><span class="material-icons hub-weather-fc-icon">${_esc(f.icon || 'cloud')}</span><span>${f.min}&deg; – ${f.max}&deg;</span></div>`;
    }).join('')}</div>` : '';

    // Details link
    const safeUrl = _safeHref(detailsUrl);
    const detailsLink = safeUrl
      ? `<a href="${_esc(safeUrl)}" target="_blank" rel="noopener" class="hub-weather-details-link" title="${_esc(this.i18n.weather_details || 'Details')}"><span class="material-icons">open_in_new</span></a>`
      : '';

    // Timestamp in city's local time
    const now = this._cityTime();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Update header clock with city time
    const clockEl = document.getElementById('hub-weather-clock');
    if (clockEl) clockEl.innerHTML = `<span>${timeStr}</span>`;

    const conditionText = this._translateCondition(data.condition || '');
    this.bodyEl.innerHTML = `<div class="hub-weather-hero"><span class="material-icons hub-weather-main-icon">${_esc(data.condition_icon || 'cloud')}</span><span class="hub-weather-temp">${data.temp}&deg;C</span></div><div class="hub-weather-mid"><div class="hub-weather-loc${hasDropdown ? ' hub-weather-loc--has-dd' : ''}"><span class="hub-weather-city-name">${_esc(data.city || '')}</span>${hasDropdown ? '<span class="material-icons hub-weather-city-arrow">expand_more</span>' : ''}${hasDropdown ? _weatherDropdownHtml(locations, this.cityQ) : ''}</div><div class="hub-weather-right"><div class="hub-weather-condition">${_esc(conditionText)}${detailsLink}</div><div class="hub-weather-stats"><span class="hub-weather-stat"><span class="material-icons">water_drop</span>${data.humidity}%</span><span class="hub-weather-stat"><span class="material-icons">air</span>${data.wind_speed} km/h<span class="material-icons" style="transform:rotate(${windRotation}deg)">navigation</span></span></div></div></div>${upcomingHtml ? `<div class="hub-weather-upcoming">${upcomingHtml}</div>` : ''}${forecastHtml}<div class="hub-weather-updated">${_esc((this.i18n.weather_updated || 'Updated: {time}').replace('{time}', timeStr))}</div>`;

    // Bind dropdown toggle
    if (hasDropdown) {
      const locEl = this.bodyEl.querySelector('.hub-weather-loc');
      if (locEl) {
        locEl.addEventListener('click', (e) => {
          if (e.target.closest('.hub-weather-dd-item')) return;
          this.dropdownOpen = !this.dropdownOpen;
          const dd = locEl.querySelector('.hub-weather-dd');
          if (dd) dd.style.display = this.dropdownOpen ? 'block' : 'none';
          locEl.classList.toggle('hub-weather-loc--open', this.dropdownOpen);
        });
        // Bind item clicks
        locEl.querySelectorAll('.hub-weather-dd-item').forEach(item => {
          item.addEventListener('click', (e) => {
            e.stopPropagation();
            const q = item.dataset.q;
            const label = item.dataset.label;
            if (q && q !== this.cityQ) {
              this.cityQ = q;
              this.city = label;
              this.showLoading();
              // Request weather for new city
              if (this.app.ws) {
                this.app.ws.send({
                  type: 'request_data',
                  widget_id: 'weather',
                  params: { city: q, city_display: label },
                });
              }
            }
            this._closeDropdown();
          });
        });
      }
    }
  }

  _translateCondition(raw) {
    if (!raw) return '';
    const key = 'weather_condition_' + raw.toLowerCase().replace(/\s+/g, '_');
    return this.i18n[key] || raw;
  }

  _closeDropdown() {
    this.dropdownOpen = false;
    const locEl = this.bodyEl && this.bodyEl.querySelector('.hub-weather-loc');
    if (locEl) {
      locEl.classList.remove('hub-weather-loc--open');
      const dd = locEl.querySelector('.hub-weather-dd');
      if (dd) dd.style.display = 'none';
    }
  }
}

HubFeatures.registerWidget(new WeatherWidget());
