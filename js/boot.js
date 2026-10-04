// boot.js — 開場抓資料、30 秒輪詢、reloadData
// 從 index.html 行 1838–1858 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Bootstrap & reload ──
function reloadData() {
  window.location.replace(window.location.pathname + '?v=' + Date.now());
}
// history 由 router.js 管理（Phase 3）：啟動時正規化當前 entry，不 push；資料到位後才渲染 folder／detail 層
Router.init();
let _pollTimer = null;
// 排行榜要知道哪幾檔有 PCF 持股資料才能決定可不可點，所以開場先抓一次，
// 回來後補畫一次排行（之後 30 秒輪詢的 renderRank 就都帶得到了）。
fetchFlow().then(d => { if (d) renderRank(); });

function openFlow(code) { _flowSel = code; Router.openFlow(code); }

// ── 資料載入失敗的處理（2026-10-03）────────────────────────────
// 以前抓失敗會改畫 STATIC_ETFS：0050 寫死 175.3、行事曆停在 5 月。
// 雖然更新時間欄位會寫「示範資料」，但價格、殖利率、訊號全是假的，
// 畫面上跟真的一模一樣——使用者沒有理由察覺自己在看假數字。
// 現在分兩種情況講清楚，一律不拿舊資料冒充現在的資料。
let _lastOk = '';     // 最近一次成功載入的資料時間，空字串＝從沒成功過

function showDataError(err) {
  const badge = document.getElementById('statusBadge');
  if (badge) {
    badge.className = 'status-badge status-error';
    badge.textContent = '資料載入失敗';
  }
  const box = document.getElementById('dataError');
  if (box) {
    box.innerHTML = _lastOk
      // 載入過了才失敗：畫面上的東西還有用，但要標明那是什麼時候的
      ? '⚠ 目前無法更新，以下是 <b>' + _lastOk + '</b> 的資料，不是現在的狀況。'
      // 從沒成功過：畫面本來就是空的，直接說拿不到
      : '⚠ 資料暫時無法取得。<br>可能是網路問題或資料來源暫時中斷，請稍後按右上角 ↻ 重新整理。';
    box.hidden = false;
  }
  console.warn('[ETF] market.json 載入失敗：', err);
  Router.onDataError();
}

function hideDataError() {
  const box = document.getElementById('dataError');
  if (box) box.hidden = true;
}

function fetchData() {
  fetch('https://raw.githubusercontent.com/p14090060/cashflow-etf/main/data/market.json?t=' + Date.now())
    // fetch 只有在網路層失敗才 reject，404/500 會進 then，所以要自己檢查
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(d => {
      _lastOk = d.updated || '';
      hideDataError();
      renderAll(d.etfs, d.calendar || [], d.updated, d.market, d.is_closed, d.is_holiday);
    })
    .catch(showDataError);
  if (!_pollTimer) {
    _pollTimer = setInterval(fetchData, 30 * 1000);
  }
}
fetchData();
