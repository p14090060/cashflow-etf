// rank.js — 排行頁與站內搜尋
// 從 index.html 行 1687–1837 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Rank page ──────────────────────────────────────────────────────
function getEtfTag(code, name) {
  const c = code || '', n = name || '';
  if (c.endsWith('L') || /正2|2倍/.test(n))
    return { label:'槓桿', color:'var(--hot)', border:'rgba(var(--rgb-hot),.35)', bg:'rgba(var(--rgb-hot),.08)' };
  if (c.endsWith('R') || /反[12]|放空/.test(n))
    return { label:'反向', color:'var(--up)', border:'rgba(var(--rgb-up),.35)', bg:'rgba(var(--rgb-up),.08)' };
  if (c.endsWith('B') || n.includes('債'))
    return { label:'債券', color:'var(--bond)', border:'rgba(var(--rgb-link),.35)', bg:'rgba(var(--rgb-link),.08)' };
  if (c.endsWith('U') || /黃金|原油|黃豆|農產|白銀|天然氣/.test(n))
    return { label:'商品期貨', color:'var(--warn)', border:'rgba(var(--rgb-warn),.35)', bg:'rgba(var(--rgb-warn),.08)' };
  return null;
}

// ── D-053：官方確認「本期不分配」狀態（market.json 的可選欄位 distribution_status，由 mis_fetcher 依 D-052 判定產出）──
// 前端依台北當日再核一次：格式、代號／TWSE 公告網址、日期、有效期（不跨下一次評價日 9/30）、
// 正殖利率或評價日後的配息推翻。任何一項不成立 → null（顯示回到原本的待公告／待確認），不中止渲染。
function _dsIso(s) {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const d = new Date(s + 'T00:00:00Z');
  return (!isNaN(d) && d.toISOString().slice(0, 10) === s) ? s : null;
}
function distNoDistView(e) {
  try {
    const ds = e && e.distribution_status;
    if (!ds || typeof ds !== 'object' || ds.status !== 'no_distribution_this_period') return null;
    if (typeof e.yld === 'number' && e.yld > 0) return null;
    const val = _dsIso(ds.valuation_date), ann = _dsIso(ds.announced_date), until = _dsIso(ds.valid_until);
    if (!val || !ann || !until) return null;
    const plus31 = new Date(Date.parse(val + 'T00:00:00Z') + 31 * 86400000).toISOString().slice(0, 10);
    const nextVal = (Number(val.slice(0, 4)) + 1) + '-09-30';
    if (!(val <= ann && ann <= plus31 && ann <= until && until < nextVal)) return null;
    const today = new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10);   // 台北當日
    if (today < ann || today > until) return null;
    if (typeof ds.source_name !== 'string' || !ds.source_name.trim() || typeof ds.source_url !== 'string') return null;
    const u = new URL(ds.source_url);
    const funds = u.searchParams.getAll('fund'), dates = u.searchParams.getAll('date');
    if (u.protocol !== 'https:' || u.host !== 'www.twse.com.tw' || u.pathname !== '/zh/ETFortune/announcement' || u.hash
        || u.username || u.password || funds.length !== 1 || funds[0] !== e.code
        || dates.length !== 1 || dates[0] !== ann.replace(/-/g, '')) return null;
    const cals = (typeof CALENDAR !== 'undefined' && Array.isArray(CALENDAR)) ? CALENDAR : [];
    // R1：本檔的配息事件——日期無法比較 → 不採用；評價日之後的事件金額必須是有限、非負的真數字，
    //     null／缺欄位／字串／bool／NaN／Infinity／負數 → 未知，不採用；正數 → 已實際配息，推翻；真 0 → 維持。別檔資料不影響本檔。
    for (const c of cals) {
      if (!c || typeof c !== 'object' || c.code !== e.code) continue;
      const d = _dsIso(c.iso_date);
      if (!d) return null;
      if (d > val) {
        if (typeof c.amt !== 'number' || !isFinite(c.amt) || c.amt < 0) return null;
        if (c.amt > 0) return null;
      }
    }
    return { valuation: val, announced: ann, until: until, srcName: ds.source_name, srcUrl: u.href };
  } catch (_) {
    return null;
  }
}

// 排行殖利率欄文字（D-053 契約）：不配息→不適用；正殖利率→原百分比（未核實加 ~）；
// 有效官方本期不分配→本期無；yld_pending→待公告（優先於新上市）；新上市→未滿1歲；已核實的真 0→0.0%；其餘→待確認
function rankYldText(e) {
  const freq = e.div_freq || e.div_frequency || '?';
  if (freq === '不配息') return '不適用';
  const y = (typeof e.yld === 'number' && isFinite(e.yld)) ? e.yld : null;
  if (y != null && y > 0) return (e.yld_verified ? '' : '~') + y.toFixed(1) + '%';
  if (distNoDistView(e)) return '本期無';
  if (e.yld_pending === true) return '待公告';
  if (e.new_listing) return '未滿1歲';
  if (y === 0 && e.yld_verified === true) return '0.0%';
  return '待確認';
}

// ── 成交量就緒判定（2026-10-27 RANK_FRESHNESS）──
// 開盤前／舊日／未取得的成交量不能當成已確認的當日 0 量參與排名（09:00 快照把 00406A 08:59 的 0 量排到第 41 名）。
// a＝_statusArgs（updated／is_holiday）。成交量所屬交易日只取來源日期（逐檔 quote_date），不拿現在時間補。
// 新格式（有 quote_src）：MIS 須 quote_date＝該交易日、mis_time 在 09:00～13:30 且不晚於 updated；官方收盤（含官方 0 量）可用。
// 舊格式（無逐檔日期）：只能以 mis_time 在 09:00～13:30 且不晚於 updated 判定；休市日檔視為先前交易日資料。
// cur_vol 須是有限非負數；null／缺值＝未知。updated 缺／壞 → 全部未就緒。
const _RK_HM = /^([01]\d|2[0-3]):[0-5]\d$/;
function rankVolState(etfs, a) {
  const m = /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})$/.exec(String((a && a.updatedAt) || ''));
  const upDay = m ? _dsIso(m[1]) : null, upHm = (m && _RK_HM.test(m[2])) ? m[2] : null;
  const valid = !!(upDay && upHm);
  const holiday = !!(a && a.isHoliday === true);
  const isOff = s => s === 'TWSE_MI_INDEX' || s === 'TPEX_OTC';
  const sess = t => typeof t === 'string' && _RK_HM.test(t) && t >= '09:00' && t <= '13:30';
  const list = Array.isArray(etfs) ? etfs.filter(e => e && typeof e === 'object') : [];
  let day = null, newFmt = false;
  for (const e of list) {
    if (e.quote_src == null) continue;
    newFmt = true;
    const qd = _dsIso(e.quote_date);
    if (valid && qd && qd <= upDay && (e.quote_src === 'MIS' || isOff(e.quote_src)) && (!day || qd > day)) day = qd;
  }
  const ready = new Set();
  if (valid) for (const e of list) {
    if (!(typeof e.cur_vol === 'number' && isFinite(e.cur_vol) && e.cur_vol >= 0)) continue;
    let ok = false;
    if (e.quote_src != null) {
      const qd = _dsIso(e.quote_date);
      if (qd && qd === day) {
        if (e.quote_src === 'MIS') ok = sess(e.mis_time) && (qd < upDay || e.mis_time <= upHm);
        else ok = isOff(e.quote_src);
      }
    } else if (!newFmt && sess(e.mis_time)) {
      ok = holiday || e.mis_time <= upHm;
    }
    if (ok) ready.add(e.code);
  }
  const pending = list.filter(e => e.price > 0 && !ready.has(e.code)).length;
  // 標示文字：有來源交易日用它；舊格式休市檔不知道日期 → 只說先前交易日，不補日期
  let when = '';
  if (valid) {
    const d = day || (newFmt ? null : (holiday ? null : upDay));
    when = d ? d.slice(5).replace('-', '/') + (d === upDay ? ' ' + upHm : '') : (holiday ? '先前交易日' : '');
  }
  return { valid: valid, day: day, ready: ready, pending: pending, when: when };
}
function rankVolReady(st, e) { return !!(st && e && st.ready.has(e.code)); }

function _rankStateLine(st) {
  let el = document.getElementById('rankState');
  if (!el) {
    const rows = document.getElementById('rankRows');
    if (!rows) return;
    el = document.createElement('div');
    el.id = 'rankState';
    el.setAttribute('role', 'status');
    el.style.cssText = 'margin:6px 12px;font-size:12px;';
    rows.parentNode.insertBefore(el, rows);
  }
  let txt, warn = false;
  if (!st.valid) { txt = '⏳ 資料時間無法確認，成交量名次暫不排定'; warn = true; }
  else if (st.pending > 0) { txt = '⏳ 排行更新中：' + st.pending + ' 檔成交量尚未確認，名次暫定' + (st.when ? '（資料 ' + st.when + '）' : ''); warn = true; }
  else txt = st.when ? '成交量資料 ' + st.when : '成交量資料時間待確認';
  el.dataset.state = !st.valid ? 'invalid' : st.pending > 0 ? 'pending' : 'ready';
  el.style.color = warn ? 'var(--warn)' : 'var(--dim)';
  el.textContent = txt;
}

function renderRank() {
  const SIG_LABEL = { cheap:'便宜', fair:'合理', hot:'過熱', dear:'偏貴', bond:'債券型' };
  const SIG_CLS   = { cheap:'sig-cheap', fair:'sig-fair', hot:'sig-hot', dear:'sig-dear', bond:'sig-bond' };   // PO Visual Polish 2：與首頁 TOP10 同一組方框標籤
  const fmtRet = v => (v == null) ? '--' : (v > 0 ? '+' : '') + v.toFixed(1) + '%';
  const retClr = v => (v == null || v === 0) ? 'var(--dim)' : v > 0 ? 'var(--vivid-up)' : 'var(--vivid-dn)';   // CP7：與漲跌柱同一組鮮明紅綠   // 台股：漲紅跌綠、0 中性（D1）

  // 開盤初期多數 ETF 當日成交量還是 0，只靠 cur_vol 過濾會只剩 20 幾支。
  // 有量的不足 100 支時放寬條件補滿，並以 avg_vol 當次要排序（未成交者依平時量排）。
  const byVol   = (a, b) => (b.cur_vol || 0) - (a.cur_vol || 0)
                         || (b.avg_vol || 0) - (a.avg_vol || 0);
  // RANK_FRESHNESS：只有成交量已就緒的才排名次；未就緒的保留在榜尾「待確認」，不給名次、不用 0 或平均量代替
  const st      = rankVolState(ETFS, typeof _statusArgs !== 'undefined' ? _statusArgs : null);
  const withVol = [...ETFS].filter(e => rankVolReady(st, e) && e.cur_vol > 0 && e.price > 0);
  const sorted  = (withVol.length >= 100 ? withVol
                                         : [...ETFS].filter(e => rankVolReady(st, e) && e.price > 0))
    .sort(byVol)
    .slice(0, 100);
  const waiting = [...ETFS].filter(e => e && e.price > 0 && !rankVolReady(st, e))
    .sort((a, b) => String(a.code).localeCompare(String(b.code)));
  const prov    = !st.valid || st.pending > 0;

  document.getElementById('rankTotal').textContent = sorted.length;
  _rankSorted = sorted;
  _rankWaiting = waiting;
  _rankStateLine(st);

  document.getElementById('rankRows').innerHTML = sorted.concat(waiting).map((e, i) => {
    const wait  = i >= sorted.length;
    const rank  = wait ? '' : i + 1;
    const cls   = (wait || prov) ? '' : rank===1?'gold':rank===2?'silver':rank===3?'bronze':'';   // 暫定名次不上獎牌色
    const freq   = e.div_freq || e.div_frequency || '?';
    const noDiv  = freq === '不配息';
    const yldTxt = rankYldText(e);   // D-053
    const yldClr = (e.yld > 0 && !noDiv)
                   ? 'var(--num-accent)'   // CP7 Visual Gate（PO）：殖利率數字 dark 黃／light 橘（不分已核實與否，~ 前綴仍標示未核實）
                   : 'var(--dim)';
    const ret1y = fmtRet(e.ret1y);
    const y1C   = retClr(e.ret1y);
    const _tag  = getEtfTag(e.code, e.name);
    const tagHtml = _tag ? `<div class="rank-tag" style="color:${_tag.color};border-color:${_tag.border};background:${_tag.bg}">${_tag.label}</div>` : '';
    // CP6c（PHASE5_PLAN §3.5）：整列 → Detail（覆蓋整列的 .rank-hit 按鈕）；列內「持股異動 ›」→ Active Flow（獨立按鈕，兩者是兄弟、不巢狀）。
    // 「持股異動 ›」只要有 Active Flow 資料就顯示（沿用既有判定 _flowData.etfs[code]）——近期沒換股≠沒有資料（Gate 決策 B），
    // 不再用最近 7 天有無換檔決定入口在不在。點擊由 #rankRows 的 delegated handler 分流，一次只走一條。
    const fe       = _flowData && _flowData.etfs && _flowData.etfs[e.code];
    const hasFlow  = !!fe;
    const code     = _rankEsc(e.code), name = _rankEsc(e.name);
    const flowHtml = hasFlow
                   ? `<button type="button" class="rank-flow" aria-label="查看 ${code} 持股異動">持股異動</button>` : '';
    const rankLbl  = wait ? '成交量待確認' : (prov ? '暫定第 ' + rank + ' 名' : '第 ' + rank + ' 名');
    return `<div class="rank-row${hasFlow ? ' has-flow' : ''}${wait ? ' rank-wait' : ''}" data-code="${code}" data-rank="${rank}">
      <button type="button" class="rank-hit" aria-label="${rankLbl} ${code} ${name}，查看詳細資料"></button>
      <div class="rank-main">
        <div class="rank-no ${cls}"${wait ? ' style="font-size:12px"' : ''}>${wait ? '待確認' : rank}</div>
        <div class="rank-etf">
          <div class="rank-code">${e.code}</div>
          <div class="rank-name">${e.name}</div>
        </div>
        <div class="rank-price">${e.price}</div>
        <div class="rank-sig ${SIG_CLS[e.signal] || ''}">${SIG_LABEL[e.signal]||'--'}</div>
      </div>
      <div class="rank-sub">
        <div class="rank-freq" style="${noDiv ? '' : 'color:var(--num-accent)'}">${freq}</div>
        <div class="rank-num" style="color:${y1C}">${ret1y}</div>
        <div class="rank-yld" style="color:${yldClr}">${yldTxt}</div>
        <div class="mini-bars">${miniBars((e.ret_months||[]).slice(-3))}</div>
        ${tagHtml}${flowHtml}
      </div>
    </div>`;
  }).join('');

  applyRankFind(false);   // 每 30 秒重畫一次，把使用者的搜尋高亮補回來（不重新捲動）
}

function _rankEsc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

// CP6c：排行列點擊分流（delegated；renderRank 每 30 秒重畫 innerHTML，事件掛在不重建的 #rankRows 上）。
// 先判斷「持股異動 ›」→ Flow 並結束；否則覆蓋整列的 .rank-hit → Detail。一次點擊只產生一種 navigation。
document.getElementById('rankRows').addEventListener('click', function (ev) {
  const row = ev.target.closest('.rank-row');
  if (!row) return;
  if (ev.target.closest('.rank-flow')) { openFlow(row.dataset.code); return; }
  if (ev.target.closest('.rank-hit, .mini-bars')) openDetail(row.dataset.code);   // 小柱狀圖可 hover 看報酬，點擊同整列 → Detail
});

// ── 排行頁：找自己的 ETF ──────────────────────────────────────
// 只定位不過濾——使用者要看的是「我在第幾名」，把其他 99 支藏掉就失去參照。
// PO Change #2（PHASE5_PLAN §3.8）：搜尋與說明改為 🔍／ⓘ 按需展開，預設收起。
// 展開狀態只在記憶體（不寫 Router／history）；有搜尋內容時不因 ⓘ、輪詢重繪、Detail／Flow 往返而收起。
let _rankFind = '';
let _rankWaiting = [];   // 成交量未就緒、不給名次的 ETF（RANK_FRESHNESS）
let _rankFindOpen = false, _rankInfoOpen = false;

function _rankSyncTop() {
  const fb = document.getElementById('rankFindBox'), ib = document.getElementById('rankInfo');
  if (!fb || !ib) return;
  fb.hidden = !_rankFindOpen;
  ib.hidden = !_rankInfoOpen;
  const f = document.getElementById('rankFindBtn'), i = document.getElementById('rankInfoBtn');
  f.setAttribute('aria-expanded', String(_rankFindOpen));
  f.classList.toggle('on', _rankFindOpen || !!_rankFind);
  i.setAttribute('aria-expanded', String(_rankInfoOpen));
  i.classList.toggle('on', _rankInfoOpen);
}
function rankToggleFind() {
  _rankFindOpen = !_rankFindOpen;
  _rankSyncTop();
  if (_rankFindOpen) document.getElementById('rankFind').focus({ preventScroll: true });
}
function rankToggleInfo() {
  _rankInfoOpen = !_rankInfoOpen;
  _rankSyncTop();
}

function findInRank() {
  const el = document.getElementById('rankFind');
  _rankFind = (el.value || '').trim();
  document.getElementById('rankFindClear').hidden = !_rankFind;
  if (_rankFind) _rankFindOpen = true;   // 有內容一定保持展開
  _rankSyncTop();
  applyRankFind(true);
}

function clearRankFind() {
  document.getElementById('rankFind').value = '';
  _rankFind = '';
  document.getElementById('rankFindClear').hidden = true;
  applyRankFind(false);
  _rankSyncTop();
}

// 捲動定位時，畫面上方被「黏住」的區塊總高（CP6b FIX-1）：排行 sticky 黏在 Header 下方（top＝--hdr-h），
// 所以遮擋＝sticky 的實際 top＋高度，不是只有 sticky 自己的高度。Header 或 sticky 不黏時（gs-ckm、矮螢幕
// media query 讓它 static）就不算它。全部讀 computed style 與實際高度，不寫死尺寸。
function _rankOccludedTop() {
  const hdr = document.querySelector('.app-hdr');
  const hs = hdr ? getComputedStyle(hdr) : null;
  let occ = (hs && hs.position === 'sticky' && hs.display !== 'none') ? hdr.offsetHeight : 0;
  const st = document.querySelector('.rank-sticky');
  const ss = st ? getComputedStyle(st) : null;
  if (ss && ss.position === 'sticky') occ = Math.max(occ, (parseFloat(ss.top) || 0) + st.offsetHeight);
  return occ;
}

function _matchEtf(e, q) {
  const code = (e.code || '').toUpperCase();
  const name = e.name || '';
  if (code === q) return 3;                 // 代碼完全相同最優先
  if (code.startsWith(q)) return 2;
  if (code.includes(q) || name.includes(q)) return 1;
  return 0;
}

function applyRankFind(scroll) {
  const msg = document.getElementById('rankFindMsg');
  document.querySelectorAll('#rankRows .rank-row.found')
          .forEach(r => r.classList.remove('found'));
  if (!_rankFind) { msg.textContent = ''; msg.className = 'rank-find-msg'; return; }

  const q = _rankFind.toUpperCase();
  const hits = _rankSorted
    .map((e, i) => ({ e, rank: i + 1, score: _matchEtf(e, q) }))
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score || a.rank - b.rank);

  if (hits.length) {
    // 符合的全部標示，不只第一支——打「富邦」時使用者想看的可能是排在很後面的
    // 006208，只標最前面那支（00405A 第4名）等於找不到自己那支。
    hits.forEach(h => {
      const r = document.querySelector(`#rankRows .rank-row[data-code="${h.e.code}"]`);
      if (r) r.classList.add('found');
    });
    const h = hits[0];
    msg.className = 'rank-find-msg hit';
    msg.textContent = hits.length === 1
      ? `${h.e.code} ${h.e.name} — ${_rankWaiting.length ? '暫定' : ''}第 ${h.rank} 名 / 共 ${_rankSorted.length} 支`
      : `${hits.length} 支符合，已全部標示（最前面是 ${h.e.code} ${h.e.name}，第 ${h.rank} 名）`;
    const row = document.querySelector(`#rankRows .rank-row[data-code="${h.e.code}"]`);
    if (row && scroll) {
      const top = row.getBoundingClientRect().top + window.scrollY - _rankOccludedTop() - 12;
      const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: Math.max(0, top), behavior: reduce ? 'auto' : 'smooth' });   // V3：reduced-motion 不做平滑捲動
    }
    return;
  }

  // 成交量待確認：列在榜尾、沒有名次，要講清楚不是落榜
  const wq = _rankWaiting.filter(e => _matchEtf(e, q) > 0).sort((a, b) => _matchEtf(b, q) - _matchEtf(a, q));
  if (wq.length) {
    wq.forEach(e => {
      const r = document.querySelector(`#rankRows .rank-row[data-code="${e.code}"]`);
      if (r) r.classList.add('found');
    });
    msg.className = 'rank-find-msg hit';
    msg.textContent = `${wq[0].code} ${wq[0].name} — 成交量尚未確認，暫不排名次`;
    const row = document.querySelector(`#rankRows .rank-row[data-code="${wq[0].code}"]`);
    if (row && scroll) window.scrollTo({ top: Math.max(0, row.getBoundingClientRect().top + window.scrollY - _rankOccludedTop() - 12), behavior: 'auto' });
    return;
  }

  // 榜外：要明講「有這支但沒進榜」，不然使用者會以為搜尋壞了
  const off = ETFS.filter(e => _matchEtf(e, q) > 0)
                  .sort((a, b) => _matchEtf(b, q) - _matchEtf(a, q));
  msg.className = 'rank-find-msg miss';
  msg.textContent = off.length
    ? `${off[0].code} ${off[0].name} — 不在目前 TOP ${_rankSorted.length}（成交量未進榜，不代表不好）`
    : `找不到「${_rankFind}」，試試代碼或名稱關鍵字`;
}

