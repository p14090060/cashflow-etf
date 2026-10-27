// render.js — renderMood、renderAll
// 從 index.html 行 1498–1686 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Mood card ──
// 有效行情時間 "YYYY-MM-DD[ HH:MM]" → "MM/DD[ HH:MM]"
function fmtQuoteTime(t) {
  return t ? t.slice(5, 7) + '/' + t.slice(8, 10) + t.slice(10) : '';
}

// meta：market.json 的 market_state／quote_date／quote_time；舊版檔沒有 meta.market_state
function renderMood(market, meta) {
  const pct = market ? market.change_pct : 0;
  const pt  = market ? market.change_pt  : 0;
  const pr  = market ? market.price      : 0;

  const MOODS = [
    { min:  1.0, emoji:'🚀', main:'大盤狂奔中',     sub:'追的人開心、沒上車的焦慮',     cta:'⚠️ 越漲越要冷靜，看看你想買的還合理嗎 ▼' },
    { min:  0.3, emoji:'😊', main:'大盤微微暖',     sub:'存股族笑笑看，跟風族先別急',   cta:'🔥 熱門排行更新囉 ▼' },
    { min: -0.3, emoji:'😐', main:'大盤裝睡中',     sub:'不漲不跌，適合慢慢挑',         cta:'🎯 來看看哪些 ETF 處於甜蜜點 ▼' },
    { min: -1.0, emoji:'🍂', main:'大盤小休息',     sub:'存股族的撿便宜時機到了？',     cta:'💧 合理價清單 ▼' },
    { min: -999, emoji:'🌧️', main:'大盤下雨天',     sub:'新聞會嚇人，但便宜貨可能來了', cta:'💎 跌出機會了嗎？來看合理價 ▼' },
  ];

  const m = MOODS.find(x => pct >= x.min) || MOODS[MOODS.length-1];
  document.getElementById('moodEmoji').textContent = m.emoji;
  document.getElementById('moodText').textContent  = m.main;
  document.getElementById('moodSub').textContent   = m.sub;
  document.getElementById('moodCta').textContent   = m.cta;

  const sign  = pt >= 0 ? '▲' : '▼';
  const cls   = pct > 0 ? 'up' : pct < 0 ? 'dn' : 'flat';   // CP7 Visual Gate：紅漲綠跌只看正負，0 為 neutral
  const arrow = pt >= 0 ? '+' : '';
  const idxEl = document.getElementById('moodIdx');
  idxEl.className = `mood-idx ${cls}`;
  idxEl.textContent = '';
  if (pr > 0) {
    const val = document.createElement('span');
    val.className = 'mi-val';
    val.textContent = `${pct === 0 ? '' : sign + ' '}${arrow}${pt.toFixed(1)} (${arrow}${pct.toFixed(2)}%)`;
    idxEl.append('加權 ', val);
    // 大盤與個股時效各自判斷：大盤不是本次即時報價時，標出大盤自己的資料時間（不明就寫不明），
    // 不讓個股 LIVE 掩蓋過期的指數；和頁面徽章同一個時間、或已休市時不重複標
    const st = meta && meta.market_state;
    if (st && st !== 'holiday' && market.is_live === false) {
      const mt = market.quote_date ? market.quote_date + (market.mis_time ? ' ' + market.mis_time : '') : '';
      if (!mt) idxEl.append(' · 大盤資料時間未知');
      else if (mt !== (meta.quote_time || '')) idxEl.append(' · 大盤資料 ' + fmtQuoteTime(mt));
    }
  }
}

// ── 配息日曆列 → Detail（CP6c，PHASE5_PLAN §3.5）：覆蓋整列的 .cal-hit 按鈕；delegated，renderAll 重畫後仍有效 ──
document.getElementById('calList').addEventListener('click', function (ev) {
  const row = ev.target.closest('.cal-item');
  if (row && ev.target.closest('.cal-hit')) openDetail(row.dataset.code);
});

// ── 首頁（入口大廳，PHASE5_PLAN §2）──
// 價格狀態文字：fair 為「合理」（不是「合理✓」）
const HOME_SIG_LABEL = { cheap:'便宜', fair:'合理', hot:'過熱', dear:'偏貴', bond:'債券型' };
const PZ_SHOW = 10;
let _pzList = [];          // 價格合理區全部符合者（已排序）
let _pzExpanded = false;   // 「查看全部」展開狀態：只在記憶體，30 秒輪詢重繪時保留

function _homeEsc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

function renderPriceZone() {
  const n = _pzList.length;
  const list = document.getElementById('pzList');
  const more = document.getElementById('pzMore');
  const cnt  = document.getElementById('pzCount');
  if (n === 0) {
    cnt.textContent = '';
    cnt.hidden = true;
    list.innerHTML = '<div class="home-empty">目前沒有 ETF 符合價格條件</div>';
    more.hidden = true;
    return;
  }
  cnt.hidden = false;
  cnt.textContent = '目前共有 ' + n + ' 檔 ETF 符合價格條件';
  const shown = (_pzExpanded || n <= PZ_SHOW) ? _pzList : _pzList.slice(0, PZ_SHOW);
  list.innerHTML = shown.map(e => {
    const code = _homeEsc(e.code);
    const cls = e.signal === 'cheap' ? 'sig-cheap' : 'sig-fair';
    return '<button class="home-row pz-row" type="button" data-code="' + code + '" onclick="openDetail(\'' + code + '\')">'
      + '<span class="wait-code">' + code + '</span>'
      + '<span class="wait-name">' + _homeEsc(e.name) + '</span>'
      + '<span class="' + cls + '">' + HOME_SIG_LABEL[e.signal] + '</span></button>';
  }).join('');
  more.hidden = n <= PZ_SHOW;
  more.textContent = _pzExpanded ? '收起' : '查看全部 ' + n + ' 檔';
  more.setAttribute('aria-expanded', _pzExpanded ? 'true' : 'false');
}

function homeTogglePz() {
  _pzExpanded = !_pzExpanded;
  renderPriceZone();
}

// ── 配息日曆來源標籤（D4）：除息日來源（source）與金額來源（amount_source）分開講 ──
// source=official 只證明「除息日」是 TWSE 公告。金額目前沒有任何欄位能證明是「本次」官方公告金額：
// amount_source='TWSE' 可能來自 TWSE 逐檔查詢（不綁除息日，可能是前次金額）；「TWSE × FinMind 核實」
// 只代表與 FinMind 最近一筆相差 ≤ 5%，不是同次公告核實；「（保留前值）」是舊金額沿用到新除息日。
// 所以一律講「金額來源」，不講公告金額或核實；來源資訊（差異比例、保留前值）照實改寫保留。
// amount_source 缺值時 mis_fetcher 會回填成 source（'official'／'manual'），那代表金額來源未標示。
function calAmtSrcText(c) {
  const raw = String(c.amount_source || '');
  const kept = /（保留前值）/.test(raw);
  let as = raw.replace(/（保留前值）/g, '');
  if (!as || as === c.source) as = '';
  let t;
  if (!as) t = '金額來源未標示';
  else if (as === 'TWSE × FinMind 核實') t = '金額來源：TWSE，與 FinMind 最近一筆相差 ≤ 5%';
  else if (as === 'FinMind（估算）') t = '金額：FinMind 估算';
  else t = '金額來源：' + as;           // TWSE、TWSE（FinMind 差異 N%）、MoneyDJ、未知來源：原文
  return t + (kept ? '（保留前值，可能是前次金額）' : '');
}
// 日曆標籤：估算照講估算；其餘證明不了本次官方公告的金額一律明示「參考金額」
// （calAmtSrcText 的字串 Detail 也在用，Detail 外層已包「參考金額（…）」，所以只在這裡改寫，不動共用函式）
function calSrcLabel(c) {
  const pre = c.source === 'official' ? '官方除息日｜' : '';
  const as = String(c.amount_source || '');
  if (c.source === 'manual' && (!as || as === 'manual')) return { cls: 'src-estimate', text: '✍ 人工提供資料（參考金額）' };
  if (c.source === 'estimate' && !as) return { cls: 'src-estimate', text: '📊 歷史平均估算' };
  if (as === 'FinMind（估算）') return { cls: 'src-estimate', text: '🔍 ' + pre + calAmtSrcText(c) };
  const t = calAmtSrcText(c).replace(/^金額來源未標示/, '參考金額，來源未標示').replace(/^金額來源：/, '參考金額來源：');
  return { cls: 'src-estimate', text: 'ℹ ' + pre + t };
}

// ── Header 資料狀態徽章（D-043）────────────────────────────────
// 「今天」一律用台北日期＋官方年度日曆（trading-calendar.js）判斷，不拿資料裡昨天的 is_holiday 猜今天。
// 只有資料本身是今天的（updated 日期＝台北今天）才沿用 live／收盤語意；舊資料不冒稱 LIVE、不把 updated 當今天的行情日。
// 資料載入失敗時由 boot.js 顯示錯誤，這裡的定時重畫不得蓋掉（_statusErr）。
// D-056 對齊休市日修復：新版 market.json 帶 market_state（live／stale／closed／holiday），
// 只在資料是台北今天產生的才採用；stale →「資料時間 MM/DD HH:MM」（不明寫「資料時間未知」、部分收盤確認加「· 收盤確認 n/N」），
// closed 只在 quote_date＝今天才寫「收盤資料」；沒有 market_state 的舊版檔沿用 updated 規則。
let _statusArgs = null;
let _statusErr = false;
// R1：trading-calendar.js 沒載入／壞掉時不得拋例外中斷 renderAll；台北時鐘自己算，交易日分類一律 unknown
function _twNowSafe(ms) {
  try { if (typeof twNow === 'function') { const r = twNow(ms); if (r && r.ymd) return r; } } catch (e) { /* 走下方純時鐘 */ }
  const t = new Date((ms == null ? Date.now() : ms) + 8 * 3600000);
  return { ymd: t.toISOString().slice(0, 10), min: t.getUTCHours() * 60 + t.getUTCMinutes(), dow: t.getUTCDay() };
}
function _twKindSafe(ymd) {
  try { if (typeof twDayKind === 'function') { const k = twDayKind(ymd); if (['trading', 'holiday', 'weekend', 'unknown'].indexOf(k) >= 0) return k; } }
  catch (e) { /* 視為未知 */ }
  return 'unknown';
}
function statusBadgeText(a, nowMs) {
  const tw = _twNowSafe(nowMs);
  const kind = _twKindSafe(tw.ymd);
  const dataDay = String(a.updatedAt || '').slice(0, 10);
  const dataHm = String(a.updatedAt || '').slice(11, 16);
  const fresh = dataDay === tw.ymd;            // 資料是台北今天產生的
  const short = dataDay ? ' · 資料 ' + dataDay.slice(5).replace('-', '/') : '';
  if (kind === 'weekend' || kind === 'holiday') return { cls: 'status-holiday', text: '今日休市' };
  // R1：未知年度／壞日曆優先於 LIVE——當天的 updated 不能代替「今天已確認是交易日」
  if (kind === 'unknown') return { cls: 'status-closed', text: '今日交易狀態待確認' + short };
  // LIVE 只在盤中（與 mis_fetcher is_trading_hour 相同 09:00～13:50）；盤後仍是盤中旗標 → 只標資料時間，不冒稱 LIVE
  if (tw.min < 9 * 60) return { cls: 'status-closed', text: '待今日開盤' + short };
  const meta = a.meta || null;
  const state = meta && meta.market_state;
  if (state && fresh) {
    if (state === 'stale') {
      let t = meta.quote_time ? '資料時間 ' + fmtQuoteTime(meta.quote_time) : '資料時間未知';
      // 部分 ETF 已有逐檔官方收盤：揭露數量，不把整頁說成已收盤
      const cc = meta.close_confirmed;
      if (cc && cc.etfs > 0) t += ' · 收盤確認 ' + cc.etfs + '/' + cc.total;
      return { cls: 'status-closed', text: t };
    }
    if (state === 'closed' && meta.quote_date === tw.ymd) return { cls: 'status-closed', text: '收盤資料 · ' + meta.quote_date };
    // live 只走下方盤中規則；holiday（官方日曆是交易日）、closed 但行情日不是今天 → 不沿用，落到中性文字
  }
  if (fresh && (!state || state === 'live') && !a.isClosed && !a.isHoliday && tw.min <= 13 * 60 + 50) return { cls: 'status-live', text: 'LIVE · 更新 ' + dataHm };
  if (fresh && (!state || state === 'live') && !a.isClosed && !a.isHoliday && tw.min > 13 * 60 + 50 && kind === 'trading') return { cls: 'status-closed', text: '資料時間 ' + dataDay.slice(5).replace('-', '/') + ' ' + dataHm };
  if (!state && fresh && a.isClosed && !a.isHoliday && dataHm >= '13:30') return { cls: 'status-closed', text: '收盤資料 · ' + dataDay };
  return { cls: 'status-closed', text: '待今日行情' + short };
}
function renderStatusBadge() {
  if (!_statusArgs || _statusErr) return;
  const badge = document.getElementById('statusBadge');
  const r = statusBadgeText(_statusArgs);
  badge.className = 'status-badge ' + r.cls;
  badge.textContent = r.text;
}

// ── renderAll：用資料渲染整頁 ──
// meta：market.json 的 market_state／quote_date／quote_time／close_confirmed（徽章規則見 statusBadgeText）
function renderAll(etfs, cal, updatedAt, market, isClosed, isHoliday, meta) {
  ETFS = etfs;
  CALENDAR = cal;
  _statusArgs = { updatedAt: updatedAt, isClosed: isClosed, isHoliday: isHoliday, meta: meta || null };
  renderStatusBadge();
  renderMood(market, meta);

  const SIG_LABEL = HOME_SIG_LABEL;
  const SIG_CLASS = { cheap:'sig-cheap', fair:'sig-fair', hot:'sig-hot', dear:'sig-dear', bond:'sig-bond' };

  // 只從成交量前 100 篩選，避免冷門 ETF 混入
  // RANK_FRESHNESS：只用已就緒的成交量（rank.js rankVolState）；有未就緒的檔時名次只是暫定，TOP10 不顯示名次數字
  const _vs = rankVolState(ETFS, _statusArgs);
  const TOP100 = [...ETFS]
    .filter(e => rankVolReady(_vs, e) && e.cur_vol > 0 && e.price > 0)
    .sort((a, b) => (b.cur_vol || 0) - (a.cur_vol || 0))
    .slice(0, 100);

  // ── H4 價格合理區（PHASE5_PLAN §2.4，PO 決策 3、5、8、12、13）──
  // 母體＝成交量前 100；cheap／fair 且有配息；cheap 在前、同狀態依 cur_vol。不用 LAZY_WATCHLIST、0 檔不給 fallback。
  _pzList = TOP100
    .filter(e => (e.signal === 'cheap' || e.signal === 'fair') && (e.div_frequency || '') !== '不配息')
    .sort((a, b) => (a.signal === b.signal ? 0 : a.signal === 'cheap' ? -1 : 1) || (b.cur_vol || 0) - (a.cur_vol || 0));
  renderPriceZone();

  // ── H5 成交量 TOP 10（不稱今日：沒有逐檔交易日）：與排行頁相同，取成交量前 10；整列開 Detail ──
  const top10 = TOP100.slice(0, 10);
  const _prov = !_vs.valid || _vs.pending > 0;
  const rankClass = i => _prov ? '' : i===0?'gold':i===1?'silver':i===2?'bronze':'';
  document.getElementById('waitItems').innerHTML = top10.map((e,i) => `
    <button class="hot-item home-row" type="button" data-code="${_homeEsc(e.code)}" onclick="openDetail('${_homeEsc(e.code)}')">
      <span class="hot-rank ${rankClass(i)}"${_prov ? ' title="成交量更新中，名次暫定"' : ''}>${_prov ? '·' : i+1}</span>
      <span class="hr-main">
        <span class="hr-line"><span class="wait-code">${_homeEsc(e.code)}</span><span class="wait-name">${_homeEsc(e.name)}</span></span>
        <span class="hr-sub">
          <span class="hr-px" style="color:var(--warn)">參考價格 ${(+e.price).toFixed(2)}</span>
          <span class="hr-ylbl" style="color:var(--dim)"> · 年殖利率 </span><span style="color:var(--fair)">${(e.new_listing && !e.yld) ? '0%<span class="hr-new">新上市</span>' : fmtYld(e)}</span>
        </span>
      </span>
      <span class="${SIG_CLASS[e.signal] || 'sig-dear'}">${SIG_LABEL[e.signal] || '偏貴'}</span>
    </button>`).join('');

  const todayStr = new Date().toLocaleDateString('sv-SE'); // YYYY-MM-DD（本地時間）
  const futureCal = cal.filter(c => !c.iso_date || c.iso_date >= todayStr);
  document.getElementById('calList').innerHTML = futureCal.map(c => {
    const isToday    = c.iso_date === todayStr || c.days_until === 0;
    const lbl = c.amt == null ? null : calSrcLabel(c);
    const srcHtml = lbl ? `<div class="src-lbl ${lbl.cls}">${_homeEsc(lbl.text)}</div>` : '';
    const pill = isToday
      ? `<div class="soon-pill today-pill">今日配息</div>`
      : c.soon ? `<div class="soon-pill">快配息囉～</div>` : '';
    const amtHtml = c.amt != null
      ? `<div class="cal-amt">${c.amt.toFixed(2)} 元</div><div class="cal-ulbl">每單位</div>`
      : `<div class="cal-amt" style="color:var(--dim);font-size:14px;font-weight:400;">待公告</div>`;
    return `
    <div class="cal-item ${isToday?'today':c.soon?'soon':''}" data-code="${_homeEsc(c.code)}">
      <button type="button" class="cal-hit" aria-label="${_homeEsc(c.code)} ${_homeEsc(c.name)} 配息，查看詳細資料"></button>
      <div class="cal-date"><span class="cal-day">${c.day}</span><span class="cal-mon">${c.mon}</span></div>
      <div class="cal-line"></div>
      <div class="cal-info">
        <div class="cal-code2">${c.code}</div>
        <div class="cal-name2">${c.name}</div>
        ${srcHtml}
      </div>
      <div class="cal-r">
        ${amtHtml}
        ${pill}
      </div>
    </div>`;
  }).join('');

  renderRank();
  Router.onMarketUpdate();
  if (typeof Watch !== 'undefined') Watch.refresh();   // 自選卡：只換內容，不重排
}

