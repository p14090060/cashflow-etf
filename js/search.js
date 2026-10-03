// search.js — 全站搜尋（Phase 1，2026-10-03）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 與動態產生的字串裡有行內 onclick 需要這些函式掛在 window 上。
//
// 設計重點：
//   * 比對沿用 rank.js 的 _matchEtf()，卡片沿用 calc.js 的 renderSignalCard()，
//     不另外寫一套，避免同一件事有兩種結果。
//   * 只比對 ETFS 裡實際存在的檔。查無就說查無——不沿用 lookupToday() 那套
//     「用代碼數字推算價格」的估算，那跟剛移除的寫死備援是同一類問題。
//   * 結果面板之後會長成 ETF 詳細頁（Phase 2），所以版位先留好。

let _gsSel = -1;      // 下拉選取中的列（鍵盤上下鍵用）
let _gsRows = [];     // 目前下拉顯示的 ETF

// 表頭變高之後，排行頁自己的 .rank-sticky（top:0）會整塊躲到表頭後面。
// 高度會隨狀態列字數變動，寫死不準，所以量完寫進 CSS 變數。
function _syncHdrH() {
  const el = document.querySelector('.app-hdr');
  if (el) document.documentElement.style.setProperty('--hdr-h', el.offsetHeight + 'px');
}

function _gsFmtChg(e) {
  const p = e.change_pct;
  if (p == null) return '';
  const up = p >= 0;
  return '<span class="gs-chg" style="color:' + (up ? 'var(--up)' : 'var(--dn)') + '">'
       + (up ? '▲' : '▼') + Math.abs(p).toFixed(2) + '%</span>';
}

function gsSearch() {
  const input = document.getElementById('gsearch');
  const list  = document.getElementById('gsearchList');
  const q = (input.value || '').trim().toUpperCase();
  document.getElementById('gsearchClear').hidden = !q;
  _gsSel = -1;
  if (!q) { list.hidden = true; list.innerHTML = ''; _gsRows = []; return; }

  // _matchEtf 回傳 3/2/1/0（代碼全等 > 代碼開頭 > 包含 > 不符）
  // 同分再用成交量排，常被交易的排前面
  _gsRows = (ETFS || [])
    .map(e => ({ e, s: _matchEtf(e, q) }))
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s || (b.e.avg_vol || 0) - (a.e.avg_vol || 0))
    .slice(0, 8)
    .map(x => x.e);

  if (!_gsRows.length) {
    list.innerHTML = '<div class="gs-empty">找不到「' + input.value.trim() + '」'
                   + '<br><span>可以試試代碼（0050）或名稱（高股息）</span></div>';
    list.hidden = false;
    return;
  }
  list.innerHTML = _gsRows.map((e, i) =>
    '<div class="gs-row" data-i="' + i + '" onclick="gsPick(\'' + e.code + '\')">'
    + '<div class="gs-code">' + e.code + '</div>'
    + '<div class="gs-name">' + (e.name || '') + '</div>'
    + '<div class="gs-px">' + (e.price != null ? e.price : '--') + _gsFmtChg(e) + '</div>'
    + '</div>').join('');
  list.hidden = false;
}

function gsKey(ev) {
  const list = document.getElementById('gsearchList');
  if (ev.key === 'Escape') { gsClear(); return; }
  if (!_gsRows.length || list.hidden) {
    if (ev.key === 'Enter') gsSearch();
    return;
  }
  if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
    ev.preventDefault();
    _gsSel += (ev.key === 'ArrowDown' ? 1 : -1);
    if (_gsSel < 0) _gsSel = _gsRows.length - 1;
    if (_gsSel >= _gsRows.length) _gsSel = 0;
    [...list.querySelectorAll('.gs-row')].forEach((r, i) =>
      r.classList.toggle('on', i === _gsSel));
    return;
  }
  if (ev.key === 'Enter') {
    ev.preventDefault();
    // 沒用方向鍵選過就取第一筆——打完代碼直接按 Enter 是最常見的用法
    gsPick(_gsRows[_gsSel < 0 ? 0 : _gsSel].code);
  }
}

function gsClear() {
  const input = document.getElementById('gsearch');
  input.value = '';
  document.getElementById('gsearchClear').hidden = true;
  document.getElementById('gsearchList').hidden = true;
  _gsRows = []; _gsSel = -1;
}

function gsPick(code) {
  const etf = (ETFS || []).find(e => e.code === code);
  if (!etf) return;
  document.getElementById('gsearchList').hidden = true;
  document.getElementById('gsPanelTitle').innerHTML =
    '<b>' + etf.code + '</b>　' + (etf.name || '');

  // 有 PCF 持股資料的才給「看持股異動」，沒有的不要給一個點了沒東西的按鈕
  const hasFlow = !!(typeof _flowData !== 'undefined' && _flowData
                     && _flowData.etfs && _flowData.etfs[etf.code]);
  document.getElementById('gsPanelBody').innerHTML =
    renderSignalCard(etf, false)
    + (hasFlow
        ? '<button class="gs-flow-btn" onclick="gsGoFlow(\'' + etf.code + '\')">'
          + '看這檔的持股異動 ›</button>'
        : '')
    + '<div class="gs-note">Phase 1 先顯示價格訊號。完整的配息、績效、成分資料'
    + '將在 ETF 詳細頁（下一階段）提供。</div>';
  document.getElementById('gsPanel').hidden = false;
}

function gsClosePanel() {
  document.getElementById('gsPanel').hidden = true;
}

function gsGoFlow(code) {
  gsClosePanel();
  gsClear();
  openFlow(code);
}

// 點搜尋列以外的地方就收起下拉（面板不受影響，要按 ✕ 才關）
document.addEventListener('click', function (ev) {
  const bar = document.querySelector('.gsearch-bar');
  if (bar && !bar.contains(ev.target)) {
    const list = document.getElementById('gsearchList');
    if (list) list.hidden = true;
  }
});

window.addEventListener('resize', _syncHdrH);
_syncHdrH();
