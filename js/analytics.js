// 基本流量與工具入口統計；行情輪詢、ETF明細、輸入內容及自選資料不接入本模組。
(function () {
  'use strict';
  var ID = 'G-B5VC979GWE', KEY = 'etfRadar.analyticsDisabled';
  var allowed = location.hostname === 'p14090060.github.io' && location.pathname.indexOf('/cashflow-etf/') === 0;
  var disabled = true, canStore = true;
  try { disabled = localStorage.getItem(KEY) === '1'; } catch (_) { canStore = false; }
  var privacyOff = navigator.globalPrivacyControl === true || navigator.doNotTrack === '1';
  var choice = document.getElementById('analyticsChoice');
  window['ga-disable-' + ID] = disabled || privacyOff || !canStore || !allowed;
  if (choice) {
    choice.disabled = !canStore || privacyOff;
    choice.textContent = privacyOff ? '已依瀏覽器隱私設定停用統計' : !canStore ? '無法儲存偏好，統計未啟用' : disabled ? '啟用流量統計' : '停用流量統計';
    choice.addEventListener('click', function () {
      window['ga-disable-' + ID] = true;
      try { localStorage.setItem(KEY, disabled ? '0' : '1'); }
      catch (_) { choice.textContent = '已停用本次統計（無法儲存偏好）'; choice.disabled = true; return; }
      location.reload();
    });
  }
  if (!allowed || !canStore || disabled || privacyOff || window.__etfAnalyticsStarted) return;
  window.__etfAnalyticsStarted = true;
  try {
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    function cleanUrl(value) {
      try { var u = new URL(value); return /^https?:$/.test(u.protocol) ? u.origin + u.pathname : ''; }
      catch (_) { return ''; }
    }
    window.gtag('js', new Date());
    window.gtag('config', ID, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      page_location: cleanUrl(location.href),
      page_referrer: cleanUrl(document.referrer),
      cookie_path: '/cashflow-etf/'
    });
    var tag = document.createElement('script');
    tag.async = true;
    tag.src = 'https://www.googletagmanager.com/gtag/js?id=' + ID;
    document.head.appendChild(tag);
    // 固定事件名稱方便在GA4事件報表查看；不附代號、金額、清單或搜尋文字。
    var tools = { toolRank: 'open_volume_rank', toolYield: 'open_yield_rank', toolDiv: 'open_dividend_calendar', toolFlow: 'open_active_flow' };
    document.addEventListener('click', function (ev) {
      var target = ev.target && typeof ev.target.closest === 'function' ? ev.target.closest('.tool-card') : null;
      var name = target && tools[target.id];
      if (name && !window['ga-disable-' + ID]) window.gtag('event', name, { send_to: ID });
    });
  } catch (_) { /* 統計失敗不影響網站工具，也不重試。 */ }
}());
