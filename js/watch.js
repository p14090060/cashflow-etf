// watch.js — Phase 4「我的 ETF」自選頁、移除提示（Toast）、拖曳／移動選單排序（PHASE4_PLAN Rev.2.1 §4、§5、§7）
// 收藏狀態只來自 WatchStore；卡片點擊走既有 openDetail（不建第二套 Detail）；不新增 Router 層。
// 台股色彩（PO 硬規格）：漲＝紅 --up、跌＝綠 --dn、0＝中性 --dim、缺值＝灰。不得改成美股漲綠跌紅。
// ⚠ 傳統 <script>，不要 type="module"。須在 detail.js 之後、router.js／boot.js 之前載入（載入即 init）。

// 分類、Detail、自選卡共用的收藏切換：移除時顯示可復原提示，新增不顯示（D4）
function watchToggle(code) {
  if (WatchStore.has(code)) {
    const r = WatchStore.remove(code);
    if (r) Watch.toastRemoved(r);
  } else {
    WatchStore.add(code);
  }
}

const Watch = (function () {
  const TOAST_MS = 5000;
  const DRAG_PX = 8;          // 移動超過才算拖曳；否則是「點一下」→ 移動選單
  const EDGE = 48;            // 距可視區上下緣多少 px 內開始自動捲動
  const MAX_SPEED = 12;       // 自動捲動每幀上限

  let drag = null;            // 拖曳狀態（見 startPress）
  let pendingRefresh = false; // 拖曳中延後的行情更新
  let toast = null;           // { code, index, timer }
  let menu = null;            // { code, el }
  let focusCode = null;       // 重繪後要把焦點還給哪一檔的把手
  let suppressClick = false;  // 拖曳放開後瀏覽器補發的 click 不得開選單

  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function etfOf(code) { return (typeof ETFS !== 'undefined' && ETFS) ? ETFS.find(e => e.code === code) || null : null; }
  function loaded() { return typeof ETFS !== 'undefined' && ETFS && ETFS.length > 0; }
  function reducedMotion() { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); }

  // ── 卡片內容 ──
  function num(v, d) { return (v == null || isNaN(v)) ? null : Number(v).toFixed(d); }
  // 漲跌額、漲跌幅各自依「自己顯示的值」判色與正負：四捨五入後為 0 → 中性，缺值 → 灰「--」，
  // 不拿另一欄的狀態來染色（例：額 −0.01、幅 0.00% 時，額是綠 ▼0.01、幅是中性 0.00%）。
  function chgPart(v, d, isPct) {
    if (v == null || isNaN(v)) return '<span class="wc-chg na" data-k="na">--</span>';
    const r = Number(Number(v).toFixed(d));
    const k = r > 0 ? 'up' : r < 0 ? 'dn' : 'flat';
    const mark = isPct ? (k === 'up' ? '+' : k === 'dn' ? '−' : '') : (k === 'up' ? '▲' : k === 'dn' ? '▼' : '');
    return '<span class="wc-chg ' + k + '" data-k="' + k + '">' + mark + Math.abs(r).toFixed(d) + (isPct ? '%' : '') + '</span>';
  }
  function chgHtml(e) {
    return '<span class="wc-chgs">' + chgPart(e.change_pt, 2, false) + chgPart(e.change_pct, 2, true) + '</span>';
  }
  function barsHtml(e) {
    const m = e.ret_months || [];
    const label = '<span class="wc-bl">近半年走勢</span>';
    if (!m.length || m.every(v => v == null)) return label + '<span class="wc-na">歷史資料不足</span>';
    const aria = '近半年走勢：' + m.map(v => v == null ? '資料不足' : (v > 0 ? '+' : '') + v.toFixed(1) + '%').join('、');
    return label + '<span class="mini-bars wc-bars" role="img" aria-label="' + esc(aria) + '">' + miniBars(m, { token: true }) + '</span>';
  }
  function tagsHtml(e) {
    const sig = (typeof _DT_SIG !== 'undefined' && _DT_SIG[e.signal]) || '';
    const cls = (typeof _DT_SIG_CLS !== 'undefined' && _DT_SIG_CLS[e.signal]) || '';
    const cat = (typeof catClassify === 'function') ? (catDefOf(catClassify(e)) || {}).label : '';
    const parts = [];
    if (sig) parts.push('<span class="' + cls + '">' + esc(sig) + '</span>');
    if (cat) parts.push('<span class="wc-tag">' + esc(cat) + '</span>');
    if (e.div_frequency) parts.push('<span class="wc-tag">' + esc(e.div_frequency) + '</span>');
    return parts.join('<span class="wc-dot">·</span>');
  }
  function mainHtml(code) {
    const e = etfOf(code);
    if (!e) {
      return '<span class="wc-row1"><span class="wc-code">' + esc(code) + '</span></span>' +
             '<span class="wc-na">' + (loaded() ? '目前無法取得這檔的資料' : '資料載入中…') + '</span>';
    }
    const px = num(e.price, 2);
    return '<span class="wc-row1"><span class="wc-code">' + esc(code) + '</span><span class="wc-name">' + esc(e.name || '') + '</span></span>' +
           '<span class="wc-row2"><span class="wc-px">' + (px == null ? '--' : px) + '</span>' + chgHtml(e) + '</span>' +
           '<span class="wc-row3">' + barsHtml(e) + '</span>' +
           '<span class="wc-row4">' + tagsHtml(e) + '</span>';
  }
  function handleLabel(code, i, n) {
    const e = etfOf(code);
    return '調整順序：' + code + (e && e.name ? ' ' + e.name : '') + '，第 ' + (i + 1) + ' 位，共 ' + n + ' 檔';
  }
  function cardHtml(code, i, n) {
    return '<div class="wc" data-code="' + esc(code) + '">' +
           '<button class="drag-handle" type="button" aria-label="' + esc(handleLabel(code, i, n)) + '">⠿</button>' +
           '<button class="wc-main" type="button">' + mainHtml(code) + '</button>' +
           favBtnHtml(code) + '</div>';
  }

  // ── 頁面 ──
  function syncNote() {
    const note = $('watchNote');
    if (!note) return;
    let t = '自選 ETF 僅儲存在此裝置與瀏覽器中。';
    if (!WatchStore.readOk()) t += '目前瀏覽器無法保存自選，重新整理後會遺失。';
    else if (!WatchStore.persistOk()) t += '這次的變更無法保存，重新整理後可能回到先前保存的內容。';
    note.textContent = t;
    note.classList.toggle('warn', !WatchStore.readOk() || !WatchStore.persistOk());
  }
  function render() {
    closeMenu(false);
    const codes = WatchStore.list(), list = $('watchList');
    list.innerHTML = codes.map((c, i) => cardHtml(c, i, codes.length)).join('');
    $('watchEmpty').hidden = codes.length > 0;
    $('watchHint').hidden = codes.length < 2;
    syncNote();
    if (focusCode) {
      const h = list.querySelector('.wc[data-code="' + focusCode + '"] .drag-handle');
      if (h) h.focus({ preventScroll: true });
      focusCode = null;
    }
  }
  // 行情更新：只換內容，不重排、不重建順序、不動捲動；拖曳中延後
  function refresh() {
    if (drag && drag.active) { pendingRefresh = true; return; }
    pendingRefresh = false;
    const codes = WatchStore.list();
    document.querySelectorAll('#watchList .wc').forEach(card => {
      const code = card.dataset.code, i = codes.indexOf(code);
      card.querySelector('.wc-main').innerHTML = mainHtml(code);
      card.querySelector('.drag-handle').setAttribute('aria-label', handleLabel(code, i, codes.length));
      favBtnSync(card.querySelector('.fav-btn'), code);
    });
  }
  function announce(t) { const l = $('watchLive'); if (l) { l.textContent = ''; setTimeout(() => { l.textContent = t; }, 30); } }

  // ── 移除提示（D4：只對移除、約 5 秒、只復原最近一次）──
  function toastRemoved(r) {
    if (!r) return;
    if (toast) clearTimeout(toast.timer);
    toast = { code: r.code, index: r.index, timer: setTimeout(hideToast, TOAST_MS) };
    $('watchToastMsg').textContent = '已從自選移除';
    $('watchToast').hidden = false;
  }
  function hideToast() {
    if (toast) clearTimeout(toast.timer);
    toast = null;
    $('watchToast').hidden = true;
  }
  function undo() {
    if (!toast) return;
    const t = toast;
    hideToast();
    WatchStore.restore(t.code, t.index);   // 冪等：已在清單中就不動
  }

  // ── 移動（拖曳、選單、鍵盤共用；一律以 code 規劃）──
  function moveBy(code, where) {
    const codes = WatchStore.list(), i = codes.indexOf(code);
    if (i < 0) return;
    const rest = codes.filter(c => c !== code);
    let to;
    if (where === 'top') to = 0;
    else if (where === 'bottom') to = rest.length;
    else if (where === 'up') to = Math.max(0, i - 1);
    else to = Math.min(rest.length, i + 1);
    if (to === i) return;
    focusCode = code;
    if (WatchStore.moveCode(code, rest[to] == null ? null : rest[to])) {
      const n = WatchStore.list().indexOf(code);
      announce(code + ' 移到第 ' + (n + 1) + ' 位，共 ' + codes.length + ' 檔');
    } else focusCode = null;
  }

  // ── 點一下 ⠿：移動選單 ──
  function openMenu(code) {
    closeMenu(false);
    const card = document.querySelector('#watchList .wc[data-code="' + code + '"]');
    if (!card) return;
    const codes = WatchStore.list(), i = codes.indexOf(code), last = codes.length - 1;
    const el = document.createElement('div');
    el.className = 'wc-menu';
    el.setAttribute('role', 'menu');
    el.setAttribute('aria-label', '移動 ' + code);
    const items = [['up', '上移一格', i === 0], ['down', '下移一格', i === last], ['top', '移到最上面', i === 0], ['bottom', '移到最下面', i === last]];
    el.innerHTML = items.map(x => '<button type="button" role="menuitem" data-m="' + x[0] + '"' + (x[2] ? ' disabled' : '') + '>' + x[1] + '</button>').join('');
    card.insertAdjacentElement('afterend', el);
    menu = { code: code, el: el };
    const first = el.querySelector('button:not([disabled])');
    if (first) first.focus({ preventScroll: true });
  }
  function closeMenu(returnFocus) {
    if (!menu) return;
    const code = menu.code;
    menu.el.remove();
    menu = null;
    if (returnFocus) {
      const h = document.querySelector('#watchList .wc[data-code="' + code + '"] .drag-handle');
      if (h) h.focus({ preventScroll: true });
    }
  }

  // ── 拖曳（原生 Pointer Events；只有把手 touch-action:none）──
  // 座標系：pointer clientY 與卡片 rect 都是 layout viewport 的 client 座標；卡片位置另存「文件座標」（rect.top + scrollY），
  // 捲動時不變，所以每幀都能以同一套數字重算插入位置。拖曳位移 = (pointerY − 起點) + (scrollY − 起點 scrollY)。
  function visibleBand() {
    const vv = window.visualViewport;
    let top = vv ? vv.offsetTop : 0, bottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
    const hdr = document.querySelector('.app-hdr'), nav = document.querySelector('.bottom-nav');
    if (hdr) { const r = hdr.getBoundingClientRect(); if (r.height && getComputedStyle(hdr).position === 'sticky') top = Math.max(top, r.bottom); }
    if (nav && getComputedStyle(nav).display !== 'none') bottom = Math.min(bottom, nav.getBoundingClientRect().top);
    return { top: top, bottom: bottom };
  }
  function startPress(ev, handle) {
    if (ev.button > 0 || drag) return;
    const card = handle.closest('.wc');
    // 按下時不動版面（輕點時手指下的把手不能移走）；已開的選單要等確定是拖曳（activate）才關閉。
    // yRaw：使用者實際按下的位置，只用來判斷是否移動 ≥ DRAG_PX；y0：跟手錨點（activate 時再加上版面補償）
    drag = { code: card.dataset.code, handle: handle, card: card, pid: ev.pointerId, yRaw: ev.clientY, y0: ev.clientY, y: ev.clientY,
             s0: window.scrollY, active: false, raf: 0, target: -1 };
    try { handle.setPointerCapture(ev.pointerId); } catch (e) { /* 不支援時仍可用 move 事件 */ }
  }
  function activate() {
    // 已開的移動選單占版面高度：先關閉再量測。選單在這張卡上方時，關閉會讓卡片上移 shift px；
    // 把跟手錨點 y0 同步上移，拖曳位移 (y − y0) 便包含這段差，卡片維持在手指下（PHASE4 Code Review #2）。
    if (menu) {
      const before = drag.card.getBoundingClientRect().top;
      closeMenu(false);
      drag.y0 -= before - drag.card.getBoundingClientRect().top;
    }
    const cards = Array.prototype.slice.call(document.querySelectorAll('#watchList .wc'));
    drag.cards = cards.map(c => { const r = c.getBoundingClientRect(); return { el: c, code: c.dataset.code, top: r.top + window.scrollY, h: r.height }; });
    drag.from = cards.indexOf(drag.card);
    drag.target = drag.from;
    const gap = cards.length > 1 ? drag.cards[1].top - drag.cards[0].top - drag.cards[0].h : 10;
    drag.step = drag.cards[drag.from].h + Math.max(0, gap);
    drag.active = true;
    document.body.classList.add('wt-dragging');
    drag.card.classList.add('lifting');
    drag.raf = requestAnimationFrame(frame);
  }
  function frame() {
    if (!drag || !drag.active) return;
    const band = visibleBand();
    let v = 0;
    if (drag.y < band.top + EDGE) v = -Math.min(MAX_SPEED, Math.ceil((band.top + EDGE - drag.y) / 4));
    else if (drag.y > band.bottom - EDGE) v = Math.min(MAX_SPEED, Math.ceil((drag.y - (band.bottom - EDGE)) / 4));
    if (v) window.scrollBy(0, v);
    const off = (drag.y - drag.y0) + (window.scrollY - drag.s0);
    const me = drag.cards[drag.from];
    const center = me.top + me.h / 2 + off;
    // 插入位置：排除自己之後，中心點在我上方的卡片數
    let t = 0;
    drag.cards.forEach((c, i) => { if (i !== drag.from && c.top + c.h / 2 < center) t++; });
    drag.target = t;
    drag.cards.forEach((c, i) => {
      if (i === drag.from) { c.el.style.transform = 'translateY(' + off + 'px)'; return; }
      let shift = 0;
      if (drag.from < t && i > drag.from && i <= t) shift = -drag.step;
      else if (drag.from > t && i < drag.from && i >= t) shift = drag.step;
      c.el.style.transform = shift ? 'translateY(' + shift + 'px)' : '';
    });
    drag.raf = requestAnimationFrame(frame);
  }
  // 所有終止路徑都走這裡：釋放 capture、清 transform、停 rAF、補延後的行情更新。commit=false 不寫入。
  function endDrag(commit) {
    if (!drag) return;
    const d = drag;
    drag = null;
    cancelAnimationFrame(d.raf);
    try { if (d.handle.hasPointerCapture && d.handle.hasPointerCapture(d.pid)) d.handle.releasePointerCapture(d.pid); } catch (e) { /* ignore */ }
    if (d.cards) d.cards.forEach(c => { c.el.style.transform = ''; });
    if (d.card) d.card.classList.remove('lifting');
    document.body.classList.remove('wt-dragging');
    if (d.active && commit && d.target !== d.from) {
      const rest = d.cards.map(c => c.code).filter(c => c !== d.code);
      WatchStore.moveCode(d.code, rest[d.target] == null ? null : rest[d.target]);   // 以 code 規劃，WatchStore 依目前清單找位置
    }
    if (pendingRefresh) refresh();
  }

  function bind() {
    const list = $('watchList');
    list.addEventListener('click', function (ev) {
      const fav = ev.target.closest('.wc .fav-btn');
      if (fav) { watchToggle(fav.closest('.wc').dataset.code); return; }
      const main = ev.target.closest('.wc .wc-main');
      if (main) { openDetail(main.closest('.wc').dataset.code); return; }
      // 把手的標準 activation（滑鼠、觸控 tap、Enter／Space、VoiceOver／TalkBack 合成 click）→ 開／關移動選單
      const h = ev.target.closest('.wc .drag-handle');
      if (h) {
        const code = h.closest('.wc').dataset.code;
        if (suppressClick) { suppressClick = false; return; }
        if (menu && menu.code === code) closeMenu(true); else openMenu(code);
        return;
      }
      const mi = ev.target.closest('.wc-menu button[data-m]');
      if (mi && menu) { const code = menu.code; closeMenu(false); moveBy(code, mi.dataset.m); return; }
    });
    list.addEventListener('pointerdown', function (ev) {
      const h = ev.target.closest('.drag-handle');
      if (h) startPress(ev, h);
    });
    list.addEventListener('pointermove', function (ev) {
      if (!drag || ev.pointerId !== drag.pid) return;
      drag.y = ev.clientY;
      if (!drag.active && Math.abs(drag.y - drag.yRaw) >= DRAG_PX) activate();   // 門檻只看手指實際移動，不含選單關閉的版面補償
    });
    // 放開：拖曳中 → 寫入順序，並吃掉接下來那個 click；沒拖動 → 交給標準 click（開／關選單）
    list.addEventListener('pointerup', function (ev) {
      if (!drag || ev.pointerId !== drag.pid) return;
      if (drag.active) {
        endDrag(true);
        suppressClick = true;
        setTimeout(function () { suppressClick = false; }, 400);
        return;
      }
      endDrag(false);
    });
    list.addEventListener('pointercancel', function (ev) { if (drag && ev.pointerId === drag.pid) endDrag(false); });
    list.addEventListener('lostpointercapture', function (ev) { if (drag && drag.active && ev.pointerId === drag.pid) endDrag(false); });
    // 把手：鍵盤 ↑／↓ 直接移動（不捲頁），Enter／Space 開選單
    list.addEventListener('keydown', function (ev) {
      const h = ev.target.closest('.drag-handle');
      if (h && (ev.key === 'ArrowUp' || ev.key === 'ArrowDown')) {
        ev.preventDefault();
        moveBy(h.closest('.wc').dataset.code, ev.key === 'ArrowUp' ? 'up' : 'down');
        return;
      }
      if (menu && ev.key === 'Escape') { ev.preventDefault(); closeMenu(true); }
    });
    // 選單：點外面、捲動頁面時關閉
    document.addEventListener('pointerdown', function (ev) {
      if (menu && !ev.target.closest('.wc-menu') && !ev.target.closest('.drag-handle')) closeMenu(false);
    }, true);
    window.addEventListener('scroll', function () { if (menu && !(drag && drag.active)) closeMenu(false); }, { passive: true });
    // 其他終止路徑：切到背景、離開頁面、離開自選頁、開啟 Detail
    document.addEventListener('visibilitychange', function () { if (document.hidden) { endDrag(false); closeMenu(false); } });
    window.addEventListener('pagehide', function () { endDrag(false); });
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(function () {
        if (!$('page-watch').classList.contains('active')) { endDrag(false); closeMenu(false); }
      }).observe($('page-watch'), { attributes: true, attributeFilter: ['class'] });
      new MutationObserver(function () {
        if (!$('gsPanel').hidden) { endDrag(false); closeMenu(false); }
      }).observe($('gsPanel'), { attributes: true, attributeFilter: ['hidden'] });
    }
    $('watchGoCat').addEventListener('click', function () { switchPage('cat'); });
    $('watchUndo').addEventListener('click', undo);
    // 收藏清單任何變動：拖曳中一律取消（不把舊意圖套到新清單），再依最新清單重畫
    WatchStore.subscribe(function () {
      if (drag) endDrag(false);
      render();
    });
  }

  function init() {
    bind();
    render();
  }
  init();

  return {
    refresh: refresh,
    render: render,
    toastRemoved: toastRemoved,
    _state: function () { return { dragging: !!(drag && drag.active), pendingRefresh: pendingRefresh, toast: toast ? { code: toast.code, index: toast.index } : null, menu: menu ? menu.code : null }; },
    _endDrag: endDrag
  };
})();
