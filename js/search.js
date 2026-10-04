// search.js — 全站搜尋（Phase 1，2026-10-03）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 與動態產生的字串裡有行內 onclick 需要這些函式掛在 window 上。
//
// 設計重點：
//   * 比對沿用 rank.js 的 _matchEtf()，卡片沿用 calc.js 的 renderSignalCard()，
//     不另外寫一套，避免同一件事有兩種結果。
//   * 只比對 ETFS 裡實際存在的檔。查無就說查無——不沿用 lookupToday() 那套
//     「用代碼數字推算價格」的估算，那跟剛移除的寫死備援是同一類問題。
//   * 選取後交給 detail.js 的 openDetail()，詳細頁共用 #gsPanel 容器。

let _gsSel = -1;      // 下拉選取中的列（鍵盤上下鍵用）
let _gsRows = [];     // 目前下拉顯示的 ETF

// 表頭變高之後，排行頁自己的 .rank-sticky（top:0）會整塊躲到表頭後面。
// 高度會隨狀態列字數變動，寫死不準，所以量完寫進 CSS 變數。
function _syncHdrH() {
  const el = document.querySelector('.app-hdr');
  if (el) document.documentElement.style.setProperty('--hdr-h', el.offsetHeight + 'px');
}

// 下拉的高度上限：量「表頭下緣」到「鍵盤或底部導覽列，誰先擋住」之間還剩多少。
//
// 原本寫 max-height:46vh，真機實測只看得到前 3 筆。兩個原因疊在一起：
//   1. vh 不會因為虛擬鍵盤跳出來而變小，下拉以為自己有半個螢幕可用
//   2. 底部導覽列是 position:fixed、z-index:100，直接壓在下拉上面
//
// 用 visualViewport 才量得到鍵盤佔掉多少。導覽列則直接量它自己的位置，
// 不去猜鍵盤會不會把它推上來——Android 各家瀏覽器行為不一致（實測這台會推上來，
// 但 resizes-visual 模式的瀏覽器不會），取兩者較小值兩種情況都成立。
// 不支援 visualViewport 時退回 innerHeight；CSS 那層也留著 46vh 當最後防線。
function _gsSyncListMax() {
  const list = document.getElementById('gsearchList');
  const hdr  = document.querySelector('.app-hdr');
  if (!list || !hdr) return;
  if (_gsCkmOn) {
    // 精簡模式：下拉用搜尋列以下的全部可視高度，不再留給標題與導覽
    const avail = _gsViewH() - hdr.getBoundingClientRect().bottom - 6;
    list.style.maxHeight = Math.max(40, Math.round(avail)) + 'px';
    return;
  }
  const vv = window.visualViewport;
  const viewH = (vv && vv.height) ? vv.height : window.innerHeight;
  const nav = document.querySelector('.bottom-nav');
  // fixed 元素的 rect 是對版面視窗算的，可能超出可視視窗，所以取小的那個
  const floor = nav ? Math.min(viewH, nav.getBoundingClientRect().top) : viewH;
  const avail = floor - hdr.getBoundingClientRect().bottom - 10;   // 留 10px 喘息
  list.style.maxHeight = Math.max(132, Math.round(avail)) + 'px';  // 至少露 3 筆
}

function _gsSyncAll() { _gsSyncCkm(); _syncHdrH(); _gsSyncListMax(); }

// ── 低高度搜尋模式 ─────────────────────────────────────────────
// 進入條件：搜尋框有焦點，而且實際可用高度（visualViewport）已放不下「完整搜尋列＋兩列結果」。
// 只看可用高度，不看機型、不看橫直向；直向螢幕夠高時不會進入。
// 進入後：隱藏標題與次要元件，搜尋框留在最上方，下拉用剩下的高度；鍵盤收起即恢復。
const _GS_MIN_LIST_H = 110;   // 兩列結果的高度，依列高估算
let _gsCkmOn = false;
let _gsNaturalHdrH = 0;       // 完整搜尋列（含標題）的高度，只在非低高度模式量測

function _gsViewH() {
  const vv = window.visualViewport;
  return vv ? Math.min(vv.height, window.innerHeight) : window.innerHeight;
}

function _gsSyncCkm() {
  const hdr = document.querySelector('.app-hdr');
  const input = document.getElementById('gsearch');
  if (!hdr || !input) return;
  if (!_gsCkmOn && hdr.offsetHeight > 0) _gsNaturalHdrH = hdr.offsetHeight;
  const focused = document.activeElement === input;
  const on = focused && _gsViewH() < _gsNaturalHdrH + _GS_MIN_LIST_H;
  if (on === _gsCkmOn) return;
  _gsCkmOn = on;
  document.body.classList.toggle('gs-ckm', on);
  if (on) input.scrollIntoView({ block: 'start' });
}

function _gsFmtChg(e) {
  const p = e.change_pct;
  if (p == null) return '';
  const up = p >= 0;
  return '<span class="gs-chg" style="color:' + (up ? 'var(--up)' : 'var(--dn)') + '">'
       + (up ? '▲' : '▼') + Math.abs(p).toFixed(2) + '%</span>';
}

// 比對規則（刻意不共用 rank.js 的 _matchEtf）：
//   4 代碼完全相同 ／ 3 代碼開頭 ／ 2 代碼或名稱包含 ／ 1 只有分類包含
// 多比一個 div_category 的理由是實測出來的：台灣 ETF 名稱混用「高股息」與
// 「高息」，只比名稱的話搜「高股息」只有 8 檔，但分類是高股息的有 76 檔
// （00878 國泰永續高息、00919 群益台灣精選高息…全被漏掉）。
// 「債券」「海外」更極端——名稱 0 檔，分類分別有 3 檔與 10 檔。
// 代碼搜尋完全不受影響（0050 → 1 檔、00981A → 1 檔）。
// ⚠ 沒有直接改 rank.js 的 _matchEtf，是為了不動到排行頁既有行為。
//    等排行頁搜尋併入全站搜尋（後續階段）之後，這兩套就會收斂成一套。
function _gsMatch(e, q) {
  const code = (e.code || '').toUpperCase();
  const name = e.name || '';
  const cat  = e.div_category || '';
  if (code === q) return 4;
  if (code.startsWith(q)) return 3;
  if (code.includes(q) || name.includes(q)) return 2;
  if (cat.includes(q)) return 1;
  return 0;
}

function gsSearch() {
  cancelPendingSearch();
  const input = document.getElementById('gsearch');
  const list  = document.getElementById('gsearchList');
  const q = (input.value || '').trim().toUpperCase();
  document.getElementById('gsearchClear').hidden = !q;
  _gsSel = -1;
  if (!q) { list.hidden = true; list.innerHTML = ''; _gsRows = []; return; }
  _gsSyncListMax();   // 鍵盤可能已經開著，先量一次再顯示

  // 同分再用成交量排，常被交易的排前面
  const hits = (ETFS || [])
    .map(e => ({ e, s: _gsMatch(e, q) }))
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s || (b.e.avg_vol || 0) - (a.e.avg_vol || 0));
  _gsRows = hits.slice(0, 8).map(x => x.e);

  if (!_gsRows.length) {
    list.innerHTML = '<div class="gs-empty">找不到「' + input.value.trim() + '」'
                   + '<br><span>可以試試代碼（0050）、名稱（元大）或類型（高股息）</span></div>';
    list.hidden = false;
    return;
  }
  list.innerHTML = _gsRows.map((e, i) =>
    '<div class="gs-row" data-i="' + i + '" onclick="gsPick(\'' + e.code + '\')">'
    + '<div class="gs-code">' + e.code + '</div>'
    + '<div class="gs-name">' + (e.name || '') + '</div>'
    + '<div class="gs-px">' + (e.price != null ? e.price : '--') + _gsFmtChg(e) + '</div>'
    + '</div>').join('')
    // 截斷時一定要說還有多少，不然使用者會以為「只有這幾檔」
    + (hits.length > _gsRows.length
        ? '<div class="gs-more">共 ' + hits.length + ' 檔符合，先顯示前 '
          + _gsRows.length + ' 筆</div>' : '');
  list.hidden = false;
}

function gsKey(ev) {
  const list = document.getElementById('gsearchList');
  // Esc 一次收乾淨：下拉、輸入、結果面板都關掉
  if (ev.key === 'Escape') { gsClear(); closeDetail(); return; }
  if (ev.key === 'Enter' && _gsCkmOn) { ev.preventDefault(); gsSubmitKey(); return; }
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

// 鍵盤「搜尋」鍵（表單送出）。低高度模式才有作用；其餘情況維持 Phase 1 的 Enter 行為。
function gsFormSubmit(ev) {
  ev.preventDefault();
  if (_gsCkmOn) gsSubmitKey();
}

// 低高度模式按搜尋：唯一精確代碼直接開啟詳細頁；其他情況先收起鍵盤，再顯示結果列表。
// 送出後會延遲一下等鍵盤收起，期間若清除、改查、直接選取或切換分頁，舊的延遲操作必須作廢。
let _gsSubmitTimer = null;
let _gsSubmitSeq = 0;

function cancelPendingSearch() {
  _gsSubmitSeq++;
  clearTimeout(_gsSubmitTimer);
  _gsSubmitTimer = null;
}

function gsSubmitKey() {
  const input = document.getElementById('gsearch');
  const q = (input.value || '').trim().toUpperCase();
  if (!q) return;
  const exact = (ETFS || []).find(e => (e.code || '').toUpperCase() === q);
  cancelPendingSearch();
  const seq = _gsSubmitSeq;
  input.blur();
  _gsSubmitTimer = setTimeout(() => {
    _gsSubmitTimer = null;
    if (seq !== _gsSubmitSeq) return;
    if ((input.value || '').trim().toUpperCase() !== q) return;
    _gsSyncAll();
    if (exact) gsPick(exact.code);
    else gsSearch();
  }, 300);
}

function gsClear() {
  cancelPendingSearch();
  const input = document.getElementById('gsearch');
  input.value = '';
  document.getElementById('gsearchClear').hidden = true;
  document.getElementById('gsearchList').hidden = true;
  _gsRows = []; _gsSel = -1;
}

function gsPick(code) {
  cancelPendingSearch();
  if (!(ETFS || []).some(e => e.code === code)) return;
  document.getElementById('gsearchList').hidden = true;
  openDetail(code);
}

// 點搜尋列以外的地方就收起下拉（面板不受影響，要按 ✕ 才關）
// 延遲中的搜尋送出同樣要作廢，否則 300ms 後會把剛收起的下拉又叫出來
document.addEventListener('click', function (ev) {
  const bar = document.querySelector('.gsearch-bar');
  if (bar && !bar.contains(ev.target)) {
    cancelPendingSearch();
    const list = document.getElementById('gsearchList');
    if (list) list.hidden = true;
  }
});

// 旋轉時 resize 有機會在版面定下來之前就觸發，量到舊尺寸，
// 所以同一次事件算兩遍（當下一遍、下一個繪製影格再一遍）。
function _gsOnResize() { _gsSyncAll(); requestAnimationFrame(_gsSyncAll); }
window.addEventListener('resize', _gsOnResize);
window.addEventListener('orientationchange', _gsOnResize);
// 鍵盤開合只會動 visualViewport，window 的 resize 不一定會發
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', _gsSyncAll);
  window.visualViewport.addEventListener('scroll', _gsSyncAll);
}
_gsSyncAll();

// 焦點變化時重新判斷；離開時等鍵盤收起的動畫結束再判斷
const _gsInput = document.getElementById('gsearch');
_gsInput.addEventListener('focus', _gsSyncAll);
_gsInput.addEventListener('blur', () => setTimeout(_gsSyncAll, 250));
