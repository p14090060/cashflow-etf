// category.js — Phase 3 分類分頁 UI（PHASE3_PLAN §3–§5、§9、§11、§12）
// 資料夾的開啟狀態由 Router 決定（confirmed 的 folder 層）；這裡只負責渲染與把使用者操作交給 Router。
// ⚠ 傳統 <script>，不要加 type="module"。頂層名稱一律 Category／catXxx 開頭。

const Category = (function () {
  const OPEN_MS = 240;       // 開啟過場
  const CLOSE_MS = 200;      // 收合過場
  const MIN_LIST_H = 110;    // 與 Phase 1 的 _GS_MIN_LIST_H 相同
  const LINE_H = 44;         // 一列的最小高度（觸控）
  const PAGE_ID = 'page-cat';

  let groups = null;         // catGroup(ETFS)；尚未載入時為 null
  let open = null;           // 目前開啟的 folder 層（router 狀態的複本）
  let state = 'overview';    // overview | opening | open | closing
  let timer = null;
  let scrollTimer = null;
  // 直向「店內／店門口」（PHASE3 Gate 核准）：stripOpen=false 為 inside（其他分類收合），true 為 doorway（其他分類顯示）。
  // 只存在 Category，不寫入 Router；不做回頂自動展開。
  let stripOpen = false;
  let lastKey = null, lastView = null;
  // 最近一次把清單畫到畫面上的分類與檢視（renderList 用來判斷「同一分類的重建」）
  let renderedKey = null, renderedView = null;

  function $(id) { return document.getElementById(id); }
  function reducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }
  function setState(s) {
    state = s;
    const pg = $(PAGE_ID);
    if (pg) pg.dataset.state = s;
  }
  function allETFs() { return (typeof ETFS !== 'undefined' && ETFS) ? ETFS : []; }

  // ── 建立 8 份文件夾（左右各 4）──
  function build() {
    const left = ['mcap', 'div', 'active', 'tech'];
    const right = ['overseas', 'theme', 'bond', 'other'];
    const band = (k, i) => {
      const d = catDefOf(k);
      return '<button class="cat-band" type="button" data-k="' + k + '" style="top:' + (i * 52) + 'px;--dx:' + (i % 2 ? 6 : 0) + 'px;z-index:' + (i + 1) + '">' +
             '<span class="cb-name">' + d.label + '</span><span class="cb-n" id="cbN-' + k + '">—</span></button>';
    };
    $('catStackL').innerHTML = left.map((k, i) => band(k, i)).join('');
    $('catStackR').innerHTML = right.map((k, i) => band(k, i)).join('');
  }

  function updateCounts() {
    CAT_DEF.forEach(d => {
      const el = $('cbN-' + d.key);
      if (el) el.textContent = groups ? (groups[d.key].length + ' 檔') : '—';
    });
  }

  function rowHtml(e) {
    return '<button class="cat-row" type="button" data-code="' + _dtEsc(e.code) + '">' +
           '<span class="cr-code">' + _dtEsc(e.code) + '</span>' +
           '<span class="cr-name">' + _dtEsc(e.name || '') + '</span>' +
           '<span class="cr-yld">' + fmtYld(e) + '</span></button>';
  }

  function renderList() {
    const list = $('catList'), more = $('catMore');
    if (!open || open.view !== 'list') return;
    if (!allETFs().length) {
      list.innerHTML = '<div class="cat-empty">資料暫時無法取得，請稍後按右上角 ↻ 重新整理。</div>';
      more.hidden = true;
      $('catCount').textContent = '';
      return;
    }
    const all = (groups && groups[open.key]) || [];
    $('catCount').textContent = all.length + ' 檔';
    if (!all.length) {
      list.innerHTML = '<div class="cat-empty">目前沒有符合這個分類的 ETF。</div>';
      more.hidden = true;
      return;
    }
    const sorted = all.slice().sort(open.ui.sort === 'name' ? catCompareName : catCompareCode);
    const n = Math.min(open.ui.shown || 10, sorted.length);
    // 重建前記下位置。同一分類（資料輪詢、Detail 關閉、排序、更多）以畫面上的 scrollTop 為準；
    // 換分類或檢視時以該層記住的位置為準。只有「同一分類」且原本在底部時才算底部（換分類時舊清單的底部不適用）。
    // 「cat-off」（LR-4 鍵盤 fallback）與隱藏時沒有可視高度，不判斷底部，只保留位置。
    const sameFolder = renderedKey === open.key && renderedView === open.view;
    const geomOK = !list.classList.contains('cat-off') && !list.hidden && list.scrollHeight > list.clientHeight;
    const atBottom = sameFolder && geomOK && (list.scrollHeight - list.clientHeight - list.scrollTop) <= 4;
    const keepVal = sameFolder ? list.scrollTop : (open.ui.scrollTop || 0);
    list.innerHTML = sorted.slice(0, n).map(rowHtml).join('');
    const rest = sorted.length - n;
    more.hidden = rest <= 0;
    more.textContent = '查看更多（還有 ' + rest + ' 檔）';
    // 先插回「查看更多」，之後的捲動範圍才包含它；再還原到完整內容的合法範圍（不可先設 scrollTop，否則會被夾到 0）
    syncInnerMore();
    const maxNow = Math.max(0, list.scrollHeight - list.clientHeight);
    const target = atBottom ? maxNow : Math.min(keepVal, maxNow);
    list.scrollTop = target;
    renderedKey = open.key; renderedView = open.view;
    // 同步記住的位置（夾制後的實際值）。這裡是程式性的還原，直接寫入，不依賴之後的 scroll 事件（防抖後才讀取）
    if (open.ui.scrollTop !== target) {
      open.ui = Object.assign({}, open.ui, { scrollTop: target });
      Router.updateUi({ scrollTop: target }, 'folder');
    }
  }

  function buildStrip() {
    $('catStrip').innerHTML = CAT_DEF
      .filter(d => d.key !== open.key)
      .map(d => '<button type="button" data-k="' + d.key + '">' + d.short + '</button>')
      .join('');
  }

  // 低高度讓位（PHASE3_PLAN §11）：量測實際可用高度，依序收合次要說明、再把次要標籤壓成單列
  // 「查看更多」在 cat-tight3 時移入清單底部（導覽列會蓋住清單外的按鈕）
  function syncInnerMore() {
    const list = $('catList'), more = $('catMore'), main = $('catMain');
    if (!list || !more || !main) return;
    let inner = list.querySelector('.cat-more-in');
    const want = (main.classList.contains('cat-tight3') || main.classList.contains('cat-ctl')) && !more.hidden && !list.hidden;
    if (!want) { if (inner) inner.remove(); return; }
    if (!inner) {
      inner = document.createElement('button');
      inner.type = 'button';
      inner.className = 'cat-more-in';
      list.appendChild(inner);
    }
    inner.textContent = more.textContent;
  }

  // 直向、列表檢視、非鍵盤模式才有 inside／doorway；其他情況（橫向、鍵盤、持股異動）完全維持原本版面
  function portraitNow() {
    return !!(window.matchMedia && window.matchMedia('(orientation: portrait)').matches);
  }
  function ctlActive() {
    return !!open && open.view === 'list' && portraitNow() && !document.body.classList.contains('gs-ckm');
  }
  function syncMode() {
    const main = $('catMain'), btn = $('catExpand');
    if (!main || !btn) return;
    const ctl = ctlActive();
    main.classList.toggle('cat-ctl', ctl);
    main.classList.toggle('cat-inside', ctl && !stripOpen);
    const pgEl = $(PAGE_ID);
    if (pgEl) pgEl.classList.toggle('cat-ctl', ctl);
    btn.textContent = (ctl && stripOpen) ? '切換分類 ▲' : '切換分類 ▼';
    btn.setAttribute('aria-expanded', String(ctl && stripOpen));
    btn.setAttribute('aria-label', (ctl && stripOpen) ? '切換分類，收合其他分類' : '切換分類，展開其他分類');
  }
  function toggleStrip() {
    if (!ctlActive()) return;
    stripOpen = !stripOpen;
    syncMode();
    fit();
  }

  function fit() {
    const list = $('catList'), main = $('catMain'), hint = $('catHint'), more = $('catMore');
    const pg = $(PAGE_ID);
    if (!list || !open || state === 'overview') return;
    // 底部錨定：visualViewport／工具列伸縮會改變清單的 max-height。清單若原本已捲到底，縮短後 scrollTop 不會跟著移到新底部，
    // 「查看更多」會被裁切在清單外框下方（真機 D4 消失）。改高度前先記下是否在底部（距底部 ≤ 4px、清單可見、未 cat-off）；
    // 只有這種情況，改高度後才回到新的底部。使用者原本在中段時不改動閱讀位置。cat-off（LR-4 鍵盤 fallback）時不錨定。
    const wasAtBottom = !list.classList.contains('cat-off') && !list.hidden &&
      list.scrollHeight > list.clientHeight && (list.scrollHeight - list.clientHeight - list.scrollTop) <= 4;
    syncMode();
    const ctl = ctlActive();
    const vv = window.visualViewport;
    const visTop = vv ? vv.offsetTop : 0;
    const visBottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
    const nav = document.querySelector('.bottom-nav');
    const navOn = !!nav && getComputedStyle(nav).display !== 'none';
    const avail = (pad) => {
      const bottom = Math.min(visBottom, navOn ? nav.getBoundingClientRect().top : visBottom);
      // 直向：清單頂端以「頁面未捲動」的位置計算。這樣清單底部固定在導覽列上方，頁面捲動時不會越過導覽列。
      const top = list.getBoundingClientRect().top + (ctl ? window.scrollY : 0);
      return Math.max(0, bottom - top - pad);
    };
    // 注意：不可先清空 max-height 再量測——內容完整展開時沒有捲動範圍，瀏覽器會把 scrollTop 夾成 0。
    // 清單頂端位置不受 max-height 影響，直接量測即可。
    main.classList.remove('cat-tight', 'cat-tight2', 'cat-tight3');
    if (pg) pg.classList.remove('cat-tight3');
    const kbd = document.body.classList.contains('gs-ckm');
    let a = avail(8);
    if (a < MIN_LIST_H) { main.classList.add('cat-tight'); a = avail(8); }
    if (a < MIN_LIST_H) { main.classList.add('cat-tight2'); a = avail(8); }
    // PHASE3_PLAN §11.4（PO／Codex blocker，844×390 無鍵盤）：仍不足一列時，標題與分段併成同一列、
    // 「查看更多」移入清單底部，把空間讓給清單。實際可見高度由 avail 量測，不靠 CSS 高度。
    if (!kbd && a < LINE_H) {
      main.classList.add('cat-tight3');
      if (pg) pg.classList.add('cat-tight3');
      a = avail(4);
    }
    // LR-4（PO 核准 responsive fallback，方案 B）：鍵盤開啟（gs-ckm）且可用高度不足一列（44px）時，
    // 不強制顯示清單，改顯示「收起鍵盤以查看 ETF 清單」。清單收合但仍留在版面中（不用 display:none），
    // scrollTop、排序、展開數都保留；鍵盤收起後自動展開。
    // 沒有鍵盤的低高度不走 fallback（提示文字是針對鍵盤）：清單至少 44px 並可捲動（PHASE3_PLAN §11.4）。
    const short = kbd && a < LINE_H && !list.hidden;
    list.classList.toggle('cat-off', short);
    more.classList.toggle('cat-gone', short);
    if (!short) {
      list.style.maxHeight = Math.max(LINE_H, a) + 'px';
      if (wasAtBottom) list.scrollTop = Math.max(0, list.scrollHeight - list.clientHeight);
    }
    if (hint) {
      hint.textContent = '收起鍵盤以查看 ETF 清單';
      hint.hidden = !short;
    }
    syncInnerMore();
  }

  function renderFlowFor() {
    if (!open || open.view !== 'flow' || typeof renderFlow !== 'function') return;
    renderFlow(open.ui.code || undefined);
  }

  function refreshAll() {
    if (!open) return;
    const def = catDefOf(open.key);
    $('catName').textContent = def.label;
    $('catSub').textContent = def.sub;
    $('catSortBtn').textContent = '排序：' + (open.ui.sort === 'name' ? '名稱' : '代碼');
    const isActive = open.key === 'active';
    $('catSeg').hidden = !isActive;
    $('catSeg').querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.v === open.view));
    buildStrip();
    syncMode();
    document.querySelectorAll('#catStackL .cat-band, #catStackR .cat-band')
      .forEach(b => b.classList.toggle('is-pulled', b.dataset.k === open.key));
    const isFlow = open.view === 'flow';
    $('catList').hidden = isFlow;
    $('catFlowHost').hidden = !isFlow;
    if (isFlow) {
      $('catMore').hidden = true;
      $('catCount').textContent = '';
      renderFlowFor();
    } else {
      renderList();
    }
    fit();
  }

  function openUi() {
    clearTimeout(timer);
    if (reducedMotion()) {
      setState('open');
      refreshAll();
      return;
    }
    setState('opening');
    refreshAll();
    timer = setTimeout(() => {
      setState('open');
      refreshAll();   // 過場結束後再量一次寬高（flow 的 treemap 依寬度畫）
    }, OPEN_MS);
  }

  function closeUi() {
    clearTimeout(timer);
    if (state === 'overview') return;
    if (reducedMotion()) { setState('overview'); return; }
    setState('closing');
    timer = setTimeout(() => setState('overview'), CLOSE_MS);
  }

  // Router 呼叫：依已確認的 folder 層更新畫面（不重設 ui）
  function applyFolder(layer) {
    if (!layer) {
      if (open) { open = null; lastKey = null; lastView = null; renderedKey = null; renderedView = null; closeUi(); }
      syncMode();
      return;
    }
    const wasOpen = !!open;
    open = JSON.parse(JSON.stringify(layer));
    // 進入分類、換分類、從持股異動回到清單：一律進入「店內」，其他分類立即收合（不需先捲動）。
    // Detail 開關、返回同一分類時 key 與 view 不變，保留目前模式。
    if (!wasOpen || open.key !== lastKey || (open.view === 'list' && lastView === 'flow')) stripOpen = false;
    // 分類或檢視改變：畫面上的清單不再代表這一層（例如持股異動隱藏清單時 scrollTop 不可靠），之後以該層記住的位置還原
    if (open.key !== lastKey || open.view !== lastView) { renderedKey = null; renderedView = null; }
    lastKey = open.key; lastView = open.view;
    if (!wasOpen) openUi();
    else refreshAll();
  }

  // 導航前把捲動位置寫入當前 entry（Router.navigate 會呼叫）
  function snapshot() {
    if (!open || open.view !== 'list' || !$('catList') || $('catList').classList.contains('cat-off')) return;
    const v = $('catList').scrollTop;
    open.ui.scrollTop = v;
    Router.updateUi({ scrollTop: v }, 'folder');
  }

  function refresh() {
    groups = allETFs().length ? catGroup(allETFs()) : null;
    updateCounts();
    if (open) refreshAll();
  }

  function isFlowVisible() {
    return !!(open && open.view === 'flow');
  }

  function onFlowData() {
    if (isFlowVisible() && state !== 'overview') renderFlowFor();
  }

  function setFlowCode(code) {
    if (!open) return;
    open.ui = Object.assign({}, open.ui, { code: code });
    Router.updateUi({ code: code }, 'folder');
  }

  function bind() {
    $('catStackL').addEventListener('click', onBand);
    $('catStackR').addEventListener('click', onBand);
    function onBand(ev) {
      const b = ev.target.closest('.cat-band');
      if (!b || state !== 'overview') return;
      Router.openFolder(b.dataset.k);
    }
    $('catMain').addEventListener('click', function (ev) {
      const row = ev.target.closest('.cat-row');
      if (row) { openDetail(row.dataset.code); return; }
      if (ev.target.closest('#catExpand, .cat-title')) { toggleStrip(); return; }
      const st = ev.target.closest('#catStrip button');
      if (st) { Router.openFolder(st.dataset.k); return; }
      const sg = ev.target.closest('#catSeg button');
      if (sg) { Router.setFolderView(sg.dataset.v); return; }
      if (ev.target.closest('#catSortBtn')) {
        if (!open) return;
        const next = open.ui.sort === 'name' ? 'code' : 'name';
        open.ui = Object.assign({}, open.ui, { sort: next, shown: 10 });
        Router.updateUi({ sort: next, shown: 10 }, 'folder');
        refreshAll();
        return;
      }
      if (ev.target.closest('#catMore, .cat-more-in')) {
        if (!open) return;
        const total = (groups && groups[open.key]) ? groups[open.key].length : 0;
        const shown = Math.min((open.ui.shown || 10) + 10, total);
        open.ui = Object.assign({}, open.ui, { shown: shown });
        Router.updateUi({ shown: shown }, 'folder');
        renderList();
        fit();
        return;
      }
      if (ev.target.closest('#catClose')) Router.closeFolder();
    });
    $('catList').addEventListener('scroll', function () {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(function () {
        if (!open || open.view !== 'list' || $('catList').classList.contains('cat-off')) return;
        const v = $('catList').scrollTop;
        open.ui.scrollTop = v;
        Router.updateUi({ scrollTop: v }, 'folder');
      }, 150);
    }, { passive: true });
    window.addEventListener('resize', fit);
    window.addEventListener('orientationchange', fit);
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', fit);
      window.visualViewport.addEventListener('scroll', fit);
    }
  }

  build();
  bind();
  updateCounts();
  // 鍵盤開合（gs-ckm 切換）時重算，不依賴 visualViewport 事件的先後順序
  if (typeof MutationObserver !== 'undefined') {
    new MutationObserver(fit).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  }

  return {
    applyFolder: applyFolder,
    snapshot: snapshot,
    refresh: refresh,
    isFlowVisible: isFlowVisible,
    onFlowData: onFlowData,
    setFlowCode: setFlowCode,
    fit: fit
  };
})();
