// boot.js — 開場抓資料、30 秒輪詢、reloadData
// 從 index.html 行 1838–1858 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Bootstrap & reload ──
function reloadData() {
  window.location.href = window.location.pathname + '?v=' + Date.now();
}
let _pollTimer = null;
// 排行榜要知道哪幾檔有 PCF 持股資料才能決定可不可點，所以開場先抓一次，
// 回來後補畫一次排行（之後 30 秒輪詢的 renderRank 就都帶得到了）。
fetchFlow().then(d => { if (d) renderRank(); });

function openFlow(code) { _flowSel = code; switchPage('check'); }

function fetchData() {
  fetch('https://raw.githubusercontent.com/p14090060/cashflow-etf/main/data/market.json?t=' + Date.now())
    .then(r => r.json())
    .then(d => renderAll(d.etfs, d.calendar || STATIC_CAL, d.updated, d.market, d.is_closed, d.is_holiday))
    .catch(() => renderAll(STATIC_ETFS, STATIC_CAL, '示範資料', null, true, false));
  if (!_pollTimer) {
    _pollTimer = setInterval(fetchData, 30 * 1000);
  }
}
fetchData();
