// detail.js — ETF 詳細頁（Phase 2，依 PHASE2_PLAN.md Rev.3）
// ⚠ 傳統 <script>，不加 type="module"：行內 onclick 需要這些函式掛在 window 上。
// 頂層名稱一律 _dt / dt 開頭，避免和其他傳統 script 的全域 let/const 撞名。

let _curEtfCode = null;      // 目前 Detail 的代碼
let _detailOpen = false;     // 等同 #gsPanel 可見
let _detailTab = 'overview';
let _dtSkeleton = false;     // 骨架只在一次開啟中建一次，股數輸入框因此保留
let _dtLayerId = null;       // 面板目前代表的 Router detail 層 id（CP4 fix：[detail, flow, detail] 共用同一個面板）

const _DT_TABS = [['overview', '總覽'], ['dividend', '配息'], ['perf', '績效'], ['holdings', '成分']];
const _DT_SIG = { cheap: '便宜', fair: '合理✓', hot: '過熱', dear: '偏貴', bond: '債券型' };
const _DT_SIG_CLS = { cheap: 'sig-cheap', fair: 'sig-fair', hot: 'sig-hot', dear: 'sig-dear', bond: 'sig-bond' };

// ── 小工具 ───────────────────────────────────────────────
function _dtEsc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, ch =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
}
function _dtToday() { return new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10); }
function _dtDays(fromIso, toIso) {
  return Math.round((Date.parse(toIso + 'T00:00:00Z') - Date.parse(fromIso + 'T00:00:00Z')) / 86400000);
}
function _dtPct(v) {
  if (v == null || isNaN(v)) return '--';
  return (v > 0 ? '+' : '') + Number(v).toFixed(1) + '%';
}
function _dtNum(v, d) { return (v == null || isNaN(v)) ? '--' : Number(v).toFixed(d); }
function _dtRow(lbl, valHtml) {
  return '<div class="dt-row"><span class="dt-lbl">' + lbl + '</span><span class="dt-val">' + valHtml + '</span></div>';
}
function _dtEl(id) { return document.getElementById(id); }
function _dtEtf() { return ETFS.find(e => e.code === _curEtfCode) || null; }
function _dtCal() { return CALENDAR.find(c => c.code === _curEtfCode) || null; }
function _dtFlow() {
  if (_flowStatus !== 'ok' || !_flowData || !_flowData.etfs) return null;
  return _flowData.etfs[_curEtfCode] || null;
}
function _dtSlot(name, html) {
  const el = document.querySelector('#gsPanelBody [data-slot="' + name + '"]');
  if (el) el.innerHTML = html;
}

// 殖利率顯示：只有 yld_verified 才給數字，其餘照實說明狀態
function _dtYld(e) {
  if ((e.div_frequency || '') === '不配息') return '不配息';
  if (e.new_listing && !e.yld) return '未滿1歲';
  if (e.yld_pending) return '待公告';
  if (e.yld_verified === true && e.yld > 0) return e.yld.toFixed(1) + '%';
  if (e.yld > 0) return '待核實';
  return '--';
}

// ── 配息判定（PHASE2_PLAN.md Rev.3 第 2.2 節，依序檢查，命中即停止）──
function _dvView(e, c) {
  const today = _dtToday();
  const offIso = c && c.source === 'official' && c.iso_date ? c.iso_date : null;

  if (offIso && offIso >= today) {
    const amt = c.amt > 0 ? c.amt : null;
    return { st: 'O1', label: '官方公告', date: offIso, past: false, amount: amt,
             amtNote: amt != null ? '公告金額（來源：' + (c.amount_source || '未標示') + '）' : '金額待公告',
             calc: amt != null, calcNote: '依公告金額試算' };
  }
  if (offIso) {
    return { st: 'O2', label: '官方公告日已過', date: offIso, past: true, amount: null,
             amtNote: '—', calc: false, calcNote: '公告日已過，等待下次公告' };
  }
  if (e.div_frequency === '不配息') {
    return { st: 'N', label: '此檔不配息', date: null, dateNote: '—', amount: null,
             amtNote: '—', calc: false, calcNote: '不配息，無可試算的配息' };
  }
  if (e.yld_pending === true || (e.new_listing && e.div_next == null)) {
    return { st: 'P', label: '待公告', date: null, dateNote: '待公告', amount: null,
             amtNote: '待公告', calc: false, calcNote: '配息尚未公告' };
  }
  // est 與 div_next 同源：兩者都來自同一次 calc_div_forecast（div_next 有值），
  // 且沒有被官方金額覆寫（mis_fetcher.py:546-548）。此判斷是由 calendar 欄位推定。
  const paired = e.div_next != null && !(c && c.amount_source && c.amt > 0);
  if (e.div_next != null && e.div_next >= today) {
    const ok = paired && e.est > 0;
    return { st: 'E1', label: '依歷史推算', date: e.div_next, past: false,
             amount: ok ? e.est : null,
             amtNote: ok ? '歷史配息金額（yfinance，未經官方核實）' : '金額不可用（無法確認與日期同源）',
             calc: ok, calcNote: '依歷史配息金額試算，不代表下次實際配息' };
  }
  if (e.div_next != null) {
    return { st: 'E2', label: '推算日已過', date: null, dateNote: '推算日已過，資料待更新',
             amount: null, amtNote: '—', calc: false, calcNote: '推算日已過，資料待更新' };
  }
  return { st: 'U', label: '資料不足', date: null, dateNote: '資料不足', amount: null,
           amtNote: '—', calc: false, calcNote: '無可靠的除息日' };
}

// ── 各 Tab 內容 ──────────────────────────────────────────
function _dtHeadHtml(e) {
  const sig = '<span class="' + (_DT_SIG_CLS[e.signal] || 'sig-dear') + '">' + (_DT_SIG[e.signal] || '偏貴') + '</span>';
  return '<div class="dt-headrow"><span class="dt-px">' + _dtNum(e.price, 2) + '</span>' + sig + '</div>';
}

function _dtOverviewHtml(e) {
  const maD = e.maD == null ? '--'
    : '<span class="' + (e.maD >= 0 ? 'dt-up' : 'dt-dn') + '">' + _dtPct(e.maD) + '</span>';
  return _dtRow('60MA 偏離', maD)
    + _dtRow('20MA', _dtNum(e.ma20, 2))
    + _dtRow('60MA', _dtNum(e.ma60, 2))
    + _dtRow('RSI', _dtNum(e.rsi, 0))
    + _dtRow('量比', _dtNum(e.vol_ratio, 2))
    + _dtRow('熱度', _dtNum(e.heat, 0))
    + _dtRow('殖利率', _dtEsc(_dtYld(e)))
    + '<div class="dt-note">訊號依價格與均線等指標計算，為狀態描述，非買賣建議。</div>';
}

function _dtDivHtml(e) {
  const dv = _dvView(e, _dtCal());
  const today = _dtToday();
  let dateTxt = dv.date || dv.dateNote || '—';
  if (dv.date && !dv.past) {
    const d = _dtDays(today, dv.date);
    dateTxt += d === 0 ? '（今日）' : '（' + d + ' 天後）';
  }
  const verified = e.div_todo === false;
  let h = _dtRow('配息方式', _dtEsc(e.div_frequency || '--')
            + ' <span class="dt-tag">' + (verified ? '人工核實' : '依歷史推論，未核實') + '</span>')
        + _dtRow('除息日', _dtEsc(dateTxt) + ' <span class="dt-tag">' + _dtEsc(dv.label) + '</span>')
        + _dtRow('金額', (dv.amount != null ? '<b>' + dv.amount + ' 元／股</b>' : '—')
            + '<div class="dt-sub">' + _dtEsc(dv.amtNote) + '</div>')
        + _dtRow('殖利率', _dtEsc(_dtYld(e)));
  if ('div_months' in e) {
    const m = e.div_months;
    h += _dtRow('配息月份', m && m.length ? m.join('、') + ' 月' : '資料不足');
  }
  if ('div_avg_per_share' in e) {
    h += _dtRow('歷史平均每次配息', e.div_avg_per_share == null
          ? '資料不足（尚無足夠配息紀錄）' : e.div_avg_per_share + ' 元／股');
  }
  if ('div_category' in e) h += _dtRow('分類', _dtEsc(e.div_category || '--'));
  if (!('div_months' in e)) h += '<div class="dt-note">此檔未建立配息分類資料</div>';
  return h;
}

function _dtPerfHtml(e) {
  const r1y = e.new_listing ? '上市以來（以面額 10 元計）' : '近一年';
  let h = _dtRow('近 5 個交易日', _dtPct(e.ret5d))
        + _dtRow('近約 1 個月（22 個交易日）', _dtPct(e.ret1m))
        + _dtRow(r1y, _dtPct(e.ret1y));
  const hasRange = e.low52 != null && e.high52 != null && e.price != null && e.high52 > e.low52;
  if (hasRange) {
    const pos = Math.min(97, Math.max(3, (e.price - e.low52) / (e.high52 - e.low52) * 100));
    h += '<div class="dt-sec">52 週區間</div>'
       + '<div class="range-track"><div class="range-fill" style="width:' + pos + '%"></div>'
       + '<div class="range-dot" style="left:' + pos + '%"></div></div>'
       + '<div class="range-lbl"><span>低 ' + e.low52 + '</span><span>高 ' + e.high52 + '</span></div>';
  } else {
    h += '<div class="dt-sec">52 週區間</div><div class="dt-note">資料不足</div>';
  }
  const months = e.ret_months || [];
  const allNull = !months.length || months.every(v => v == null);
  h += '<div class="dt-sec">近 6 段報酬</div>'
     + (allNull ? '<div class="dt-note">資料不足</div>'
                : '<div class="mini-bars dt-bars">' + miniBars(months) + '</div>')
     + '<div class="dt-note">每段約 22 個交易日（非日曆月），最右為最近一段；灰色短柱＝該段資料缺漏。</div>';
  return h;
}

function _dtHoldingsHtml(fe) {
  const flow = fe.flow || [];
  const np = _npRows(fe);
  const hasPrev = !!(flow.length || np.length);
  const notes = [];
  if (fe.fetched === false) {
    notes.push('本次未能取得新資料（投信網站異常）' + (hasPrev ? '，以下為先前結果' : ''));
  } else if (fe.flow_to && fe.data_date && fe.flow_to !== fe.data_date) {
    notes.push('最新 PCF（資料日 ' + fe.data_date + '）持股無異動，以下為最近一次有持股異動的紀錄');
  }
  if (fe.reason === 'not_updated' && fe.advanced === false) {
    notes.push((fe.data_date || '') + ' 之後尚未有新的 PCF');
  }
  if (fe.scale_pct != null) {
    notes.push('本期持股同步變動 ' + (fe.scale_pct > 0 ? '+' : '') + fe.scale_pct
              + '%，屬基金規模增減（申購／贖回），非經理人選股');
  }

  let state;
  if (fe.reason === 'no_basis') {
    state = '尚無前一份持股可比對';
  } else if (!flow.length) {
    state = np.length ? '本次異動皆為海外持股，無台股報價換算金額'
                      : '最新 PCF（資料日 ' + (fe.data_date || '--') + '）持股與前一份相同';
  } else {
    const up = flow.filter(x => x.amount > 0).length;
    state = '持股異動紀錄：' + flow.length + ' 檔台股（加碼 ' + up + ' 檔、減碼 ' + (flow.length - up) + ' 檔）';
  }

  const hasAmt = !!(fe.buy || fe.sell);
  let h = _dtRow('投信', _dtEsc(fe.issuer || '--'))
        + _dtRow('資料日', _dtEsc(fe.data_date || '--'))
        + (fe.price_date ? _dtRow('金額換算日', _dtEsc(fe.price_date)) : '')
        + _dtRow('加碼／減碼', hasAmt
            ? '<span class="dt-up">加碼 +' + _oku(fe.buy || 0) + '</span>　<span class="dt-dn">減碼 -' + _oku(fe.sell || 0) + '</span>'
            : '—')
        + (fe.last_change_date ? _dtRow('最近持股異動日', _dtEsc(fe.last_change_date)) : '')
        + _dtRow('持股檔數', _dtEsc(fe.holdings != null ? fe.holdings : '--'));
  h += '<div class="dt-note"><b>' + _dtEsc(state) + '</b></div>';
  notes.forEach(n => { h += '<div class="dt-note">⚠ ' + _dtEsc(n) + '</div>'; });
  if (hasAmt) h += '<div class="dt-note">金額為兩份 PCF 快照相減的推估值，不等同基金實際成交。</div>';
  if (np.length) h += '<div class="dt-note">另有 ' + np.length + ' 檔海外持股異動，無台股報價無法換算金額，完整清單見主動頁。</div>';
  h += '<button class="gs-flow-btn" onclick="detailGoFlow(\'' + _dtEsc(fe.code || _curEtfCode) + '\')">查看完整持股異動 ›</button>';
  return h;
}

// ── 骨架與更新 ───────────────────────────────────────────
function _dtBuild() {
  _dtEl('gsPanelBody').innerHTML =
    '<div data-slot="head"></div>' +
    '<div class="dt-tabs">' + _DT_TABS.map(t =>
      '<button class="dt-tab" data-tab="' + t[0] + '" onclick="detailTab(\'' + t[0] + '\')">' + t[1] + '</button>'
    ).join('') + '</div>' +
    '<section class="dt-pane" data-pane="overview"><div data-slot="overview"></div></section>' +
    '<section class="dt-pane" data-pane="dividend"><div data-slot="dividend"></div>' +
      '<div class="dt-calc"><div class="dt-sec">算算我可以領多少？</div>' +
      '<div class="input-row"><span class="input-lbl">我持有</span>' +
      '<input class="num-input" id="dtSharesIn" type="number" min="1" step="1" value="10">' +
      '<span class="input-lbl">張</span></div>' +
      '<div id="dtCalcOut" class="calc-out"></div></div>' +
      '<div class="dt-note">試算為參考值，未扣稅費，非投資建議。</div></section>' +
    '<section class="dt-pane" data-pane="perf"><div data-slot="perf"></div></section>' +
    '<section class="dt-pane" data-pane="holdings"><div data-slot="holdings"></div></section>' +
    '<div class="dt-foot">本站資訊僅供參考，非個別標的買賣建議。</div>';
  _dtEl('dtSharesIn').addEventListener('input', () => { _dtCalc(); _dtSaveUi(true); });   // 張數也記進該層 ui
  _dtEl('dtSharesIn').addEventListener('focus', () => {
    setTimeout(() => _dtEl('dtSharesIn').scrollIntoView({ block: 'center' }), 300);
  });
  _dtSkeleton = true;
}

// 往下捲超過一點就收起頂部區域；回到頂部才出現。
// 收合會讓捲動視窗變高（+頂部高度）、內容變短（−標題列）。若收合後的最大捲動量
// 小於目前位置，瀏覽器會把 scrollTop 壓回 0，接著又展開，形成閃動。
// 所以只有在收合後位置仍在範圍內時才收合；展開只看使用者真的回到頂部。
function _dtSyncCollapse() {
  if (!_detailOpen) return;
  const body = document.body;
  const panel = _dtEl('gsPanel');
  const st = panel.scrollTop;
  if (!body.classList.contains('dt-collapsed')) {
    if (st <= 4) return;
    const hdr = document.querySelector('.app-hdr');
    const ttl = panel.querySelector('.gs-panel-hd');
    const hdrH = hdr ? hdr.offsetHeight : 0;
    const ttlH = ttl ? ttl.offsetHeight : 0;
    const maxAfter = (panel.scrollHeight - ttlH) - (panel.clientHeight + hdrH);
    if (st <= maxAfter) body.classList.add('dt-collapsed');
  } else if (st <= 0) {
    body.classList.remove('dt-collapsed');
    _gsSyncAll();
  }
}

function _dtSyncTabs() {
  if (!_dtSkeleton) return;
  const hasFlow = !!_dtFlow();
  if (_detailTab === 'holdings' && !hasFlow) _detailTab = 'overview';
  const body = _dtEl('gsPanelBody');
  body.querySelectorAll('.dt-tab').forEach(b => {
    const k = b.getAttribute('data-tab');
    b.hidden = (k === 'holdings' && !hasFlow);
    b.classList.toggle('on', k === _detailTab);
  });
  body.querySelectorAll('.dt-pane').forEach(p => {
    p.hidden = p.getAttribute('data-pane') !== _detailTab;
  });
}

function _dtCalc() {
  if (!_dtSkeleton) return;
  const out = _dtEl('dtCalcOut');
  const e = _dtEtf();
  if (!e) { out.innerHTML = '<div class="dt-note">計算停用：這檔目前不在清單中</div>'; return; }
  const dv = _dvView(e, _dtCal());
  if (!dv.calc) { out.innerHTML = '<div class="dt-note">計算停用：' + _dtEsc(dv.calcNote) + '</div>'; return; }
  const n = parseInt(_dtEl('dtSharesIn').value, 10) || 0;
  if (n <= 0) { out.innerHTML = '<div class="dt-note">請輸入持有張數</div>'; return; }
  const fmt = v => Math.round(v).toLocaleString();
  let h = '<div class="calc-row"><span class="calc-lbl">單次可領</span>'
        + '<span class="calc-val">' + fmt(dv.amount * n * 1000) + ' 元</span></div>'
        + '<div class="dt-note">' + _dtEsc(dv.calcNote) + '</div>';
  if (e.yld_verified === true && e.yld > 0) {
    h += '<div class="calc-row"><span class="calc-lbl">預估年化領回（殖利率 ' + e.yld + '%）</span>'
       + '<span class="calc-val sm">' + fmt(e.yld / 100 * e.price * n * 1000) + ' 元</span></div>';
  }
  h += '<div class="calc-row"><span class="calc-lbl">' + n + ' 張市值約</span>'
     + '<span class="calc-val sm">' + fmt(e.price * n * 1000) + ' 元</span></div>';
  out.innerHTML = h;
}

// Detail 標題列 ♡（PHASE4_PLAN §3.2）：獨立同步，不經 Router、不重建內容；missing ETF 也要更新
function _dtSyncFav() {
  favBtnSync(_dtEl('dtFav'), _detailOpen ? _curEtfCode : null);
}

function detailPatch() {
  if (!_detailOpen || !_dtSkeleton) return;
  _dtSyncFav();                                   // 在 !e 的 early return 之前
  const e = _dtEtf();
  _dtEl('gsPanelTitle').innerHTML = '<b>' + _dtEsc(_curEtfCode) + '</b>' + (e ? '　<span class="etf-name">' + _dtEsc(e.name) + '</span>' : '');
  if (!e) {
    const msg = '<div class="dt-note">' + (ETFS.length ? '這檔目前不在清單中' : '資料暫時無法取得，請稍後按右上角 ↻') + '</div>';
    _dtSlot('head', '');
    _dtSlot('overview', msg);
    _dtSlot('dividend', '');
    _dtSlot('perf', '');
    _dtSlot('holdings', '');
    _dtSyncTabs();
    _dtCalc();
    return;
  }
  _dtSlot('head', _dtHeadHtml(e));
  _dtSlot('overview', _dtOverviewHtml(e));
  _dtSlot('dividend', _dtDivHtml(e));
  _dtSlot('perf', _dtPerfHtml(e));
  const fe = _dtFlow();
  _dtSlot('holdings', fe ? _dtHoldingsHtml(fe) : '');
  _dtSyncTabs();
  _dtCalc();
  _dtSyncCollapse();
}

// ── 開啟／關閉（Phase 3：history 由 js/router.js 統一管理；語意與 Phase 2 相同）──
// openDetail：未開啟 → push 一層；已開啟且代碼不同 → replace 當前 Detail；相同 → 不動。
// closeDetail：關閉頂層 Detail（一次 back）。✕、Back、Esc 都走 router。
function openDetail(code) {
  cancelPendingSearch();
  Router.openDetail(code);
}

function closeDetail() {
  cancelPendingSearch();
  Router.closeDetail();
}

// 只由 router 的 apply() 呼叫：依已確認的 detail 層顯示。
// ui 是該層自己記住的狀態（tab、scrollTop、shares）。
// 以「層 id」判斷是不是同一層（CP4 fix）：Flow 上可再開 Detail 形成 [detail A, flow, detail B]，
// 面板只有一個，若只比代碼，回到 A 時會沿用 B 的張數與分頁（同一檔 A→Flow→A 也一樣）。
// 同一層 → 保留畫面上的即時狀態；不同層 → 依該層 ui 還原（ui 沒記張數時保留輸入框現值，Phase 2 語意）。
function detailShow(code, ui, layerId) {
  const u = ui || {};
  const lid = layerId || null;
  if (_detailOpen && code === _curEtfCode && lid === _dtLayerId) {
    detailPatch();
    _dtSyncCollapse();
    return;
  }
  _dtLayerId = lid;
  if (!_detailOpen) {
    _curEtfCode = code;
    _detailTab = u.tab || 'overview';
    _dtBuild();
    _dtEl('gsPanel').hidden = false;
    _detailOpen = true;
  } else {
    _curEtfCode = code;
    _detailTab = u.tab || 'overview';
  }
  if (u.shares != null) _dtEl('dtSharesIn').value = u.shares;
  _dtEl('gsPanel').scrollTop = 0;
  detailPatch();                                  // 內容要先長出來，捲動位置才夾得住
  _dtEl('gsPanel').scrollTop = u.scrollTop || 0;
  _dtSyncCollapse();
}

// 目前頂層是不是這一檔的 Detail 層（只有這時才寫 ui，避免把捲動寫到別的層）
function _dtIsMyLayer() {
  if (!_detailOpen || typeof Router === 'undefined') return false;
  const st = Router.state();
  const top = st.stack[st.stack.length - 1];
  return !!top && top.t === 'detail' && top.code === _curEtfCode && (!_dtLayerId || top.id === _dtLayerId);
}

// 把分頁與捲動記進目前 Detail 層，Back → Forward 時還原。
// 捲動是高頻事件：先更新記憶體快取（Router.setUi），history 寫入合併成 150ms 一次；
// flush=true 立即寫入（分頁切換、離開頁面前）。
let _dtSaveTimer = null;
function _dtSaveUi(flush) {
  if (!_dtIsMyLayer()) return;
  const patch = { tab: _detailTab, scrollTop: _dtEl('gsPanel').scrollTop };
  if (_dtSkeleton) patch.shares = _dtEl('dtSharesIn').value;
  if (flush) {
    clearTimeout(_dtSaveTimer); _dtSaveTimer = null;
    Router.updateUi(patch);
    return;
  }
  Router.setUi(patch);
  clearTimeout(_dtSaveTimer);
  _dtSaveTimer = setTimeout(() => _dtSaveUi(true), 150);
}

function hideDetail() {
  _detailOpen = false;
  _dtLayerId = null;
  _dtSkeleton = false;
  _dtEl('gsPanel').hidden = true;
  if (document.body.classList.contains('dt-collapsed')) {
    document.body.classList.remove('dt-collapsed');
    _gsSyncAll();
  }
}

function detailTab(k) {
  _detailTab = k;
  _dtSyncTabs();
  _dtSyncCollapse();
  _dtSaveUi(true);
}

function detailGoFlow(code) {
  _dtSaveUi(true);   // 進 Flow 前把這一層的分頁／捲動／張數寫定，Back 回來依此還原
  gsClear();
  openFlow(code);
}

// 資料更新時只補內容（Router.onMarketUpdate 會處理首次還原）
function detailOnMarketUpdate() {
  detailPatch();
}

function detailOnFlowUpdate() {
  if (!_detailOpen) return;
  detailPatch();
}

document.getElementById('dtFav').addEventListener('click', function () {
  if (_detailOpen && _curEtfCode) watchToggle(_curEtfCode);
});
WatchStore.subscribe(function () { if (_detailOpen) _dtSyncFav(); });

document.getElementById('gsPanel').addEventListener('scroll', function () {
  _dtSyncCollapse();
  _dtSaveUi(false);
}, { passive: true });
// 離開頁面（重新整理、關閉分頁）前，把還在等待合併的捲動寫入 history
window.addEventListener('pagehide', function () { if (_dtSaveTimer) _dtSaveUi(true); });
