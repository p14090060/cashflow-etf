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
    list.innerHTML = sorted.slice(0, n).map(rowHtml).join('');
    const rest = sorted.length - n;
    more.hidden = rest <= 0;
    more.textContent = '查看更多（還有 ' + rest + ' 檔）';
    list.scrollTop = open.ui.scrollTop || 0;
  }

  function buildStrip() {
    $('catStrip').innerHTML = CAT_DEF
      .filter(d => d.key !== open.key)
      .map(d => '<button type="button" data-k="' + d.key + '">' + d.short + '</button>')
      .join('');
  }

  // 低高度讓位（PHASE3_PLAN §11）：量測實際可用高度，依序收合次要說明、再把次要標籤壓成單列
  function fit() {
    const list = $('catList'), main = $('catMain'), hint = $('catHint');
    if (!list || !open || state === 'overview') return;
    const vv = window.visualViewport;
    const visTop = vv ? vv.offsetTop : 0;
    const visBottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
    const nav = document.querySelector('.bottom-nav');
    const navOn = !!nav && getComputedStyle(nav).display !== 'none';
    const avail = () => {
      const bottom = Math.min(visBottom, navOn ? nav.getBoundingClientRect().top : visBottom);
      return Math.max(0, bottom - list.getBoundingClientRect().top - 8);
    };
    // 注意：不可先清空 max-height 再量測——內容完整展開時沒有捲動範圍，瀏覽器會把 scrollTop 夾成 0。
    // 清單頂端位置不受 max-height 影響，直接量測即可。
    main.classList.remove('cat-tight', 'cat-tight2');
    let a = avail();
    if (a < MIN_LIST_H) { main.classList.add('cat-tight'); a = avail(); }
    if (a < MIN_LIST_H) { main.classList.add('cat-tight2'); a = avail(); }
    list.style.maxHeight = a + 'px';
    if (hint) {
      hint.textContent = '收起鍵盤可看完整清單';
      hint.hidden = !(a < LINE_H && !list.hidden);
    }
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
      if (open) { open = null; closeUi(); }
      return;
    }
    const wasOpen = !!open;
    open = JSON.parse(JSON.stringify(layer));
    if (!wasOpen) openUi();
    else refreshAll();
  }

  // 導航前把捲動位置寫入當前 entry（Router.navigate 會呼叫）
  function snapshot() {
    if (!open || open.view !== 'list' || !$('catList')) return;
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
      if (ev.target.closest('#catMore')) {
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
        if (!open || open.view !== 'list') return;
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
