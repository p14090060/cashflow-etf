// router.js — Phase 3 history 協調（PHASE3_PLAN Rev.3.3 §7）
// 唯一呼叫 history.pushState／replaceState／back／go 的地方。
// 規則：
//   R1 popstate 只根據 history.state 渲染，不呼叫 back／go
//   R3 導航以 intent 表示，在執行當下依「已確認位置」(confirmed) 求值
//   R4 同一時間最多一個 traversal（inflight）
//   R5 inflight 為 active 時忽略導航；timeout 後（orphan）改為 park（last wins）
//   R6 完成時，只有位置吻合規劃前綴才執行 continuation（只 push／replace）
//   R7 完成只以 popstate 為準；timeout 與 3 秒「處理中」都不算完成
//   R8 有 inflight 時不寫 history
// Phase 2 語意（PHASE3_PLAN §6.1）：未開啟 Detail → push；已開啟切換另一檔 → replace；
// 相同代碼 → 不動；一次 Back 直接離開 Detail。
// ⚠ 傳統 <script>，不要 type="module"。

const Router = (function () {
  const BASES = ['home', 'cat', 'watch', 'tools'];
  const TIMEOUT_MS = 500;      // 逾時：取消 continuation，槽位仍佔用
  const PROCESSING_MS = 3000;  // 只顯示「處理中」，不改任何狀態
  const TOOL_PAGE = { div: 'page-div', rank: 'page-rank', yt: 'page-yt' };
  const BASE_PAGE = { home: 'page-today', cat: 'page-cat', watch: 'page-watch', tools: 'page-tools' };
  const BASE_NAV = { home: 'nav-today', cat: 'nav-cat', watch: 'nav-watch', tools: 'nav-tools' };

  let confirmed = { v: 2, base: 'home', stack: [] };  // 已確認位置（規劃唯一依據）
  let inflight = null;   // { state:'active'|'orphan', plannedBase, plannedStack, cont, t1, t2, processing }
  let parked = null;     // intent 函式（last wins）
  let layersPending = false;   // 首次載入前不渲染 folder／detail 層
  let lastPage = null;
  const deferred = [];         // 測試用：被延後的 traversal
  const stats = { traversals: 0, completions: 0, parkedRuns: 0 };

  function clone(x) { return JSON.parse(JSON.stringify(x)); }

  // Phase 2 格式（{etfDetail, code}）與 null 都 normalize 為 v2；只修正當前 entry，不新增
  function normalize(st) {
    if (st && st.v === 2 && BASES.indexOf(st.base) >= 0 && Array.isArray(st.stack)) return clone(st);
    if (st && st.etfDetail) return { v: 2, base: 'home', stack: [{ t: 'detail', code: st.code, ui: {} }] };
    return { v: 2, base: 'home', stack: [] };
  }

  function sameLayer(a, b) {
    if (a.t !== b.t) return false;
    if (a.t === 'folder') return a.key === b.key && a.view === b.view && ((a.ui && a.ui.code) || null) === ((b.ui && b.ui.code) || null);
    if (a.t === 'tool') return a.id === b.id;
    if (a.t === 'detail') return a.code === b.code;
    return false;
  }
  function sameStack(a, b) { return a.length === b.length && a.every((l, i) => sameLayer(l, b[i])); }
  function commonPrefix(a, b) { let i = 0; while (i < a.length && i < b.length && sameLayer(a[i], b[i])) i++; return i; }

  // R8：只在無 inflight 時呼叫
  function writeCurrent(st) { confirmed = clone(st); history.replaceState(clone(confirmed), ''); }
  function pushEntry(st) { confirmed = clone(st); history.pushState(clone(confirmed), ''); }

  function traverse(delta) {
    stats.traversals++;
    if (window.__routerDeferTraversal) { deferred.push(delta); return; }
    history.go(delta);
  }

  function showProcessing(on) {
    const el = document.getElementById('routerProc');
    if (el) el.hidden = !on;
  }

  // ── 畫面：只根據 confirmed 渲染 ──
  function applyBasePage(base, stack) {
    const tool = stack.find(l => l.t === 'tool');
    const pageId = (base === 'tools' && tool && TOOL_PAGE[tool.id]) ? TOOL_PAGE[tool.id] : BASE_PAGE[base];
    document.querySelectorAll('.pages > .page').forEach(p => p.classList.toggle('active', p.id === pageId));
    Object.keys(BASE_NAV).forEach(b => {
      const el = document.getElementById(BASE_NAV[b]);
      if (el) el.classList.toggle('active', b === base);
    });
    if (pageId !== lastPage) { window.scrollTo(0, 0); lastPage = pageId; }
  }

  function apply() {
    const st = confirmed;
    applyBasePage(st.base, st.stack);
    const folder = (!layersPending && st.base === 'cat') ? (st.stack.find(l => l.t === 'folder') || null) : null;
    if (typeof Category !== "undefined") Category.applyFolder(folder);
    const det = (!layersPending) ? (st.stack.filter(l => l.t === 'detail').pop() || null) : null;
    if (det) detailShow(det.code);
    else if (_detailOpen) hideDetail();
  }

  // ── intent：導航意圖（在執行當下依 confirmed 求值）──
  function intentDetail(code) {
    return function (c) {
      const top = c.stack[c.stack.length - 1];
      if (top && top.t === 'detail') {
        if (top.code === code) return null;                       // 相同：不動
        const rep = { t: 'detail', code: code, ui: {} };          // 切換另一檔：replace
        return { base: c.base, stack: c.stack.slice(0, -1).concat([rep]), replaceTop: rep };
      }
      return { base: c.base, stack: c.stack.concat([{ t: 'detail', code: code, ui: {} }]) };   // 未開啟：push
    };
  }
  function intentClose(type) {
    return function (c) {
      const top = c.stack[c.stack.length - 1];
      if (!top || top.t !== type) return null;
      return { base: c.base, stack: c.stack.slice(0, -1) };
    };
  }
  function intentFolder(key) {
    return function (c) {
      const f = { t: 'folder', key: key, view: 'list', ui: { sort: 'code', shown: 10, scrollTop: 0 } };
      const top = c.stack[c.stack.length - 1];
      if (c.base === 'cat' && c.stack.length === 1 && top.t === 'folder') {
        if (top.key === key) return null;
        return { base: 'cat', stack: [f], replaceTop: f };       // 切換資料夾：replace，不新增 entry
      }
      return { base: 'cat', stack: [f] };
    };
  }
  function intentView(view) {
    return function (c) {
      const top = c.stack[c.stack.length - 1];
      if (!top || top.t !== 'folder' || top.view === view) return null;
      const f = clone(top); f.view = view;
      return { base: c.base, stack: c.stack.slice(0, -1).concat([f]), replaceTop: f };
    };
  }
  function intentBase(spec) {
    return function (c) {
      if (spec.flow) {
        const f = { t: 'folder', key: 'active', view: 'flow', ui: { sort: 'code', shown: 10, scrollTop: 0, code: spec.code || null } };
        const top = c.stack[c.stack.length - 1];
        if (c.base === 'cat' && c.stack.length === 1 && top.t === 'folder' && top.key === 'active') {
          if (sameLayer(top, f)) return null;
          return { base: 'cat', stack: [f], replaceTop: f };
        }
        return { base: 'cat', stack: [f] };
      }
      if (spec.tool) return { base: 'tools', stack: [{ t: 'tool', id: spec.tool, ui: {} }] };
      return { base: spec.base, stack: [] };
    };
  }

  // ── traversal 計時器（測試時可用 hook 手動觸發）──
  function clearTimers(f) { clearTimeout(f.t1); clearTimeout(f.t2); }
  function startTimers(f) {
    if (window.__routerManualTimers) return;
    f.t1 = setTimeout(() => onTimeout(f), TIMEOUT_MS);
    f.t2 = setTimeout(() => onProcessingMark(f), PROCESSING_MS);
  }
  function onTimeout(f) {
    if (inflight !== f || f.state !== 'active') return;
    f.state = 'orphan';   // 只取消 continuation；traversal 仍在途，槽位仍佔用
    f.cont = null;
  }
  function onProcessingMark(f) {
    if (inflight !== f) return;
    f.processing = true;  // 只顯示處理中，不清除、不執行、不發新 traversal
    showProcessing(true);
  }

  // ── 執行 intent：有 inflight 時不得呼叫（呼叫端保證）──
  function execute(intent) {
    const t = intent(confirmed);
    if (!t) { apply(); return; }
    const c = confirmed;
    if (t.replaceTop) {
      const top = c.stack[c.stack.length - 1];
      if (c.base === t.base && top && top.t === t.replaceTop.t && c.stack.length === t.stack.length) {
        writeCurrent({ v: 2, base: t.base, stack: c.stack.slice(0, -1).concat([t.replaceTop]) });
        apply(); return;
      }
    }
    const sameBase = t.base === c.base;
    const p = sameBase ? commonPrefix(c.stack, t.stack) : 0;
    const k = c.stack.length - p;
    if (k === 0) {
      if (!sameBase) writeCurrent({ v: 2, base: t.base, stack: [] });   // k=0 且基底不同 ⇒ 已在 E0
      t.stack.slice(p).forEach(layer => pushEntry({ v: 2, base: t.base, stack: confirmed.stack.concat([layer]) }));
      apply(); return;
    }
    // k > 0：唯一一次 traversal。規劃只用 confirmed。
    apply();
    const f = {
      state: 'active',
      plannedBase: c.base,
      plannedStack: c.stack.slice(0, p),
      cont: { base: sameBase ? null : t.base, layers: t.stack.slice(p) },
      t1: null, t2: null, processing: false
    };
    inflight = f;
    startTimers(f);
    traverse(-k);
  }

  function navigate(intent) {
    if (inflight) {
      if (inflight.state === 'active') return;   // R5：active 階段忽略
      parked = intent;                           // R5：orphan 階段 park（last wins）
      return;
    }
    if (typeof Category !== "undefined") Category.snapshot();    // 關閉或切換前先把 ui 寫入當前 entry
    execute(intent);
  }

  function runContinuation(cont) {               // R6：只 push／replace，不 back
    if (cont.base) writeCurrent({ v: 2, base: cont.base, stack: [] });
    cont.layers.forEach(layer => pushEntry({ v: 2, base: confirmed.base, stack: confirmed.stack.concat([layer]) }));
  }

  function runParked() {
    if (!parked || inflight) return;
    const it = parked;
    parked = null;
    stats.parkedRuns++;
    execute(it);                                 // 依新的 confirmed 求值，只執行一次
  }

  // ── popstate：唯一入口（R1）──
  window.addEventListener('popstate', function (ev) {
    cancelPendingSearch();                        // Phase 2 Blocker：Back 後不得執行延遲中的搜尋送出
    const wasDetail = _detailOpen;
    const c = normalize(ev.state);
    if (!ev.state || ev.state.v !== 2) history.replaceState(clone(c), '');   // 修正當前 entry，不新增
    if (!inflight) {
      confirmed = c;
      apply();
      if (wasDetail && !_detailOpen) document.getElementById('gsearchList').hidden = true;   // Phase 2 Finding 2：Back 關 Detail 時一併收起下拉
      runParked();
      return;
    }
    const f = inflight;                           // 此 popstate 是 f 的完成事件（R7）
    inflight = null;
    clearTimers(f);
    showProcessing(false);
    stats.completions++;
    confirmed = c;
    if (f.state === 'active' && f.cont && c.base === f.plannedBase && sameStack(c.stack, f.plannedStack)) {
      runContinuation(f.cont);                   // R6：位置吻合才執行
    }                                            // orphan：永不執行 continuation
    if (parked) { runParked(); return; }
    apply();
    if (wasDetail && !_detailOpen) document.getElementById('gsearchList').hidden = true;
  });

  function updateUi(patch) {
    if (!confirmed.stack.length) return;
    const st = clone(confirmed);
    const top = st.stack[st.stack.length - 1];
    top.ui = Object.assign({}, top.ui || {}, patch);
    if (inflight) { confirmed = st; return; }     // R8：只留在記憶體
    writeCurrent(st);
  }

  function closeType(type) { navigate(intentClose(type)); }

  function onKey(e) {
    if (e.key !== 'Escape') return;
    const top = confirmed.stack[confirmed.stack.length - 1];
    if (top) closeType(top.t);                   // Esc 只退一層
  }

  function onMarketUpdate() {
    if (typeof Category !== "undefined") Category.refresh();   // 每次資料到達都重算分類（包含首次還原前）
    if (layersPending) { layersPending = false; apply(); return; }
    detailPatch();
  }
  function onDataError() {
    if (layersPending) { layersPending = false; apply(); }
  }

  function init() {
    confirmed = normalize(history.state);
    if (!history.state || history.state.v !== 2) history.replaceState(clone(confirmed), '');   // 不 push
    layersPending = confirmed.stack.length > 0;
    apply();
    document.addEventListener('keydown', onKey);
  }

  // ── 測試 hook（只在測試時呼叫；不影響正式行為）──
  window.__routerReleaseTraversal = function () {
    const ds = deferred.splice(0);
    ds.forEach(d => history.go(d));
  };
  window.__routerForceTimeout = function () { if (inflight && inflight.state === 'active') onTimeout(inflight); };
  window.__routerForceProcessingMark = function () { if (inflight) onProcessingMark(inflight); };
  window.__routerInflightState = function () { return inflight ? inflight.state : null; };
  window.__routerProcessing = function () { return !!(inflight && inflight.processing); };
  window.__routerDeferredCount = function () { return deferred.length; };
  Object.defineProperty(window, '__routerTraversalCount', { get: () => stats.traversals });
  Object.defineProperty(window, '__routerCompletions', { get: () => stats.completions });
  Object.defineProperty(window, '__routerParkedRuns', { get: () => stats.parkedRuns });

  return {
    init: init,
    normalize: normalize,
    state: function () { return clone(confirmed); },
    navigate: navigate,
    openDetail: function (code) { navigate(intentDetail(code)); },
    closeDetail: function () { closeType('detail'); },
    closeFolder: function () { closeType('folder'); },
    openFolder: function (key) { navigate(intentFolder(key)); },
    setFolderView: function (view) { navigate(intentView(view)); },
    toBase: function (spec) { navigate(intentBase(spec)); },
    openFlow: function (code) { navigate(intentBase({ flow: true, code: code })); },
    updateUi: updateUi,
    onMarketUpdate: onMarketUpdate,
    onDataError: onDataError
  };
})();
