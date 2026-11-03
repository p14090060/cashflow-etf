// yield-rank.js — 工具頁「殖利率排行」與 Detail 共用的比較數值
// 資料只讀 market.json 的 yield_basis（scripts/yield_comparison.py 產生）；本檔不發任何請求、不重算比率。
// ⚠ 傳統 <script> 載入，HTML 行內 onclick 需要這些函式掛在 window 上。
const YIELD_RANK_MAX = 100;

const YIELD_MAX_AGE_DAYS = 14;   // 與 yield_comparison.MAX_BASIS_AGE_DAYS 相同
const YIELD_PER_YEAR = { '月配':12, '雙月配':6, '季配':4, '半年配':2, '年配':1 };

function yieldToday() {
  return new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);   // 台北日期
}
// 合法 YYYY-MM-DD → UTC 毫秒；其餘 NaN（2026-02-30 這種也擋）
function _yieldDay(s) {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return NaN;
  const t = Date.parse(s + 'T00:00:00Z');
  return isFinite(t) && new Date(t).toISOString().slice(0, 10) === s ? t : NaN;
}
function _yieldWindowStart(asOf) {
  const y = +asOf.slice(0, 4) - 1, md = asOf.slice(5) === '02-29' ? '02-28' : asOf.slice(5);
  return new Date(Date.parse(y + '-' + md + 'T00:00:00Z') + 864e5).toISOString().slice(0, 10);
}
// 與 json_safe.check_yield_basis 同一語意：期間、方法、事件、分子、比率都要對得上
function _yieldBasisOk(e, b, est) {
  const asOf = _yieldDay(b.as_of), listed = _yieldDay(b.listing_date), today = _yieldDay(yieldToday());
  if (!isFinite(asOf) || !isFinite(listed) || asOf > today || (today - asOf) / 864e5 > YIELD_MAX_AGE_DAYS) return false;
  const start = _yieldWindowStart(b.as_of);
  if (b.window_start !== start || listed > asOf || (b.listing_date >= start) !== est) return false;
  if (typeof b.price !== 'number' || !(b.price > 0) || b.price !== e.price) return false;
  if (typeof b.rate !== 'number' || !isFinite(b.rate) || b.rate <= 0) return false;
  if (!Array.isArray(b.events) || !b.events.length) return false;
  const per = b.frequency == null ? null : YIELD_PER_YEAR[b.frequency];
  if (b.frequency != null ? per !== b.periods_per_year : b.periods_per_year != null) return false;
  let total = 0, prev = '';
  for (const x of b.events) {
    if (!x || typeof x !== 'object' || !isFinite(_yieldDay(x.ex_date)) || !isFinite(_yieldDay(x.pay_date))) return false;
    if (x.ex_date <= prev || x.ex_date < start || x.pay_date < x.ex_date) return false;
    if (typeof x.future !== 'boolean' || x.future !== (x.ex_date > b.as_of) || (!est && x.future)) return false;
    if (typeof x.source !== 'string' || !x.source) return false;
    const amt = typeof x.amount === 'string' && /^\d+(\.\d+)?$/.test(x.amount) ? +x.amount : 0;
    if (!(amt > 0)) return false;
    total += amt; prev = x.ex_date;
  }
  if (est && (!per || b.events.length > per)) return false;
  const annual = typeof b.annual_cash === 'string' && /^\d+(\.\d+)?$/.test(b.annual_cash) ? +b.annual_cash : 0;
  const want = est ? total / b.events.length * per : total;
  return annual > 0 && Math.abs(annual - want) < 1e-6 && Math.abs(b.rate - annual / b.price * 100) < 1e-6;
}

// 排行與 Detail 的唯一讀取點：同一個 rate、同一個標記。欄位缺／壞／期間不符 → null（未可比較），不造數。
function yieldView(e) {
  const b = e && e.yield_basis;
  if (!b || typeof b !== 'object') return null;
  const est = b.method === 'annualized_estimate';
  if (!est && b.method !== 'trailing_12m') return null;
  if (!_yieldBasisOk(e, b, est)) return null;
  return { rate: b.rate, text: (est ? '~' : '') + b.rate.toFixed(1) + '%', est: est, label: est ? '年化估算' : '近12月', basis: b };
}
function _yieldAmt(v) { return String(Number(Number(v).toFixed(6))); }

// Detail「配息」分頁的計算依據；期數、每期金額／日期、來源與算式只放這裡，主卡片不顯示
function yieldBasisHtml(e) {
  const v = yieldView(e);
  if (!v) return '';
  const b = v.basis, esc = _rankEsc, annual = _yieldAmt(b.annual_cash);
  const formula = v.est
    ? b.events.length + ' 期平均 × ' + b.periods_per_year + ' 次／年 = ' + annual + ' 元；' + annual + ' ÷ ' + b.price + ' × 100 = ' + b.rate.toFixed(1) + '%'
    : '近12月已除息合計 ' + annual + ' 元；' + annual + ' ÷ ' + b.price + ' × 100 = ' + b.rate.toFixed(1) + '%';
  const items = b.events.map(x => '<li>' + esc(x.ex_date) + ' 除息：每單位 ' + esc(_yieldAmt(x.amount)) + ' 元'
    + (x.raw_amount ? '（原公告 ' + esc(x.raw_amount) + ' 元，依單位變更換算）' : '')
    + '<br>' + esc(x.source) + '｜發放日 ' + esc(x.pay_date) + (x.future ? '（尚未除息）' : '') + '</li>').join('');
  const hasFuture = b.events.some(x => x.future);
  return '<div class="yr-basis" data-yield-basis="' + esc(b.method) + '">'
    + '<div class="dt-sec">配息率計算依據</div>'
    + '<div class="dt-note"><span class="yr-label ' + (v.est ? 'estimate' : 'trailing') + '">' + v.label + '</span> 採用 ' + b.events.length + ' 期已公告配息金額</div>'
    + '<div class="dt-note" data-yield-formula>' + esc(formula) + '</div>'
    + '<ul class="yr-events">' + items + '</ul>'
    + '<div class="dt-note">配息資料來源日 ' + esc(b.as_of) + '，價格為最新參考價格。來源失敗時沿用前次資料，來源日超過 ' + YIELD_MAX_AGE_DAYS + ' 天即不列入排行。'
    + (v.est ? '年化估算' + (hasFuture ? '含尚未除息的正式公告，' : '') + '不代表已領金額或未來配息保證。' : '依除息事件計算，不代表已實際入帳，也不代表未來配息。')
    + '</div></div>';
}

let _yieldSorted = [], _yieldAll = [];
let _yieldFind = '', _yieldFindOpen = false, _yieldInfoOpen = false;

function renderYieldRank() {
  const rowsEl = document.getElementById('yieldRows');
  if (!rowsEl) return;
  const SIG_LABEL = { cheap:'便宜', fair:'合理', hot:'過熱', dear:'偏貴', bond:'債券型' };
  const SIG_CLS   = { cheap:'sig-cheap', fair:'sig-fair', hot:'sig-hot', dear:'sig-dear', bond:'sig-bond' };
  const esc = _rankEsc;
  _yieldAll = (Array.isArray(ETFS) ? ETFS : []).filter(e => e && e.price > 0 && yieldView(e))
    .sort((a, b) => b.yield_basis.rate - a.yield_basis.rate || (a.code < b.code ? -1 : a.code > b.code ? 1 : 0));
  _yieldSorted = _yieldAll.slice(0, YIELD_RANK_MAX);
  // 成交量名次沿用成交量榜當下的結果（renderRank 剛算完），不另排；未就緒者不造名次
  const st = rankVolState(ETFS, typeof _statusArgs !== 'undefined' ? _statusArgs : null);
  const prov = !st.valid || st.pending > 0;
  const volRank = new Map(_rankSorted.map((e, i) => [e.code, i + 1]));
  document.getElementById('yieldTotal').textContent = _yieldSorted.length;
  // 只寫最新日會掩蓋沿用舊資料的那幾檔，所以範圍與舊筆數都照實列
  const days = _yieldSorted.map(e => e.yield_basis.as_of).sort();
  const asOfNew = days[days.length - 1], oldN = days.filter(d => d !== asOfNew).length;
  const state = document.getElementById('yieldState');
  state.textContent = _yieldSorted.length
    ? '依年化配息率排序・前 ' + _yieldSorted.length + ' 名・配息來源日 ' + (oldN ? days[0] + '～' + asOfNew + '（' + oldN + ' 支沿用舊資料，超過 ' + YIELD_MAX_AGE_DAYS + ' 天下榜）' : asOfNew)
    : '目前沒有可比較的配息資料';
  rowsEl.innerHTML = _yieldSorted.map((e, i) => {
    const rank = i + 1, v = yieldView(e), code = esc(e.code), name = esc(e.name);
    const cls = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
    const vr = volRank.get(e.code);
    const volTxt = !rankVolReady(st, e) ? '待確認' : vr ? (prov ? '暫' : '') + vr : prov ? '待確認' : '榜外';
    return `<div class="rank-row" data-code="${code}" data-rank="${rank}">
      <button type="button" class="rank-hit" aria-label="第 ${rank} 名 ${code} ${name}，查看詳細資料"></button>
      <div class="rank-main">
        <div class="rank-no ${cls}">${rank}</div>
        <div class="rank-etf"><div class="rank-code">${code}</div><div class="rank-name">${name}</div></div>
        <div class="rank-price">${e.price}</div>
        <div class="rank-sig ${SIG_CLS[e.signal] || ''}">${SIG_LABEL[e.signal] || '--'}</div>
      </div>
      <div class="rank-sub yr-cols">
        <div class="yr-freq">${esc(e.div_frequency || e.div_freq || '不明')}</div>
        <div class="yr-rate" data-yield-rate>${v.text}</div>
        <div class="yr-vol">${volTxt}</div>
        <div class="yr-basis-cell"><span class="yr-label ${v.est ? 'estimate' : 'trailing'}">${v.label}</span></div>
      </div>
    </div>`;
  }).join('');
  _applyYieldFind(false);
}

document.getElementById('yieldRows').addEventListener('click', function (ev) {
  const row = ev.target.closest('.rank-row');
  if (row && ev.target.closest('.rank-hit')) openDetail(row.dataset.code);
});

function _yieldSyncTop() {
  document.getElementById('yieldFindBox').hidden = !_yieldFindOpen;
  document.getElementById('yieldInfo').hidden = !_yieldInfoOpen;
  const f = document.getElementById('yieldFindBtn'), i = document.getElementById('yieldInfoBtn');
  f.setAttribute('aria-expanded', String(_yieldFindOpen));
  f.classList.toggle('on', _yieldFindOpen || !!_yieldFind);
  i.setAttribute('aria-expanded', String(_yieldInfoOpen));
  i.classList.toggle('on', _yieldInfoOpen);
}
function yieldToggleFind() {
  _yieldFindOpen = !_yieldFindOpen;
  _yieldSyncTop();
  if (_yieldFindOpen) document.getElementById('yieldFind').focus({ preventScroll: true });
}
function yieldToggleInfo() { _yieldInfoOpen = !_yieldInfoOpen; _yieldSyncTop(); }
function findInYield() {
  _yieldFind = (document.getElementById('yieldFind').value || '').trim();
  document.getElementById('yieldFindClear').hidden = !_yieldFind;
  if (_yieldFind) _yieldFindOpen = true;
  _yieldSyncTop();
  _applyYieldFind(true);
}
function clearYieldFind() {
  document.getElementById('yieldFind').value = '';
  _yieldFind = '';
  document.getElementById('yieldFindClear').hidden = true;
  _applyYieldFind(false);
  _yieldSyncTop();
}
// 只定位不過濾；榜外與不可比較只回報狀態，不插入第 101 列
function _applyYieldFind(scroll) {
  const msg = document.getElementById('yieldFindMsg');
  document.querySelectorAll('#yieldRows .rank-row.found').forEach(r => r.classList.remove('found'));
  if (!_yieldFind) { msg.textContent = ''; msg.className = 'rank-find-msg'; return; }
  const q = _yieldFind.toUpperCase();
  const hits = _yieldSorted.map((e, i) => ({ e, rank: i + 1, score: _matchEtf(e, q) })).filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score || a.rank - b.rank);
  if (hits.length) {
    hits.forEach(h => {
      const r = document.querySelector(`#yieldRows .rank-row[data-code="${h.e.code}"]`);
      if (r) r.classList.add('found');
    });
    const h = hits[0];
    msg.className = 'rank-find-msg hit';
    msg.textContent = hits.length === 1
      ? `${h.e.code} ${h.e.name} — 第 ${h.rank} 名 / 共 ${_yieldSorted.length} 支`
      : `${hits.length} 支符合，已全部標示（最前面是 ${h.e.code} ${h.e.name}，第 ${h.rank} 名）`;
    const row = document.querySelector(`#yieldRows .rank-row[data-code="${h.e.code}"]`);
    if (row && scroll) {
      const hdr = document.querySelector('.app-hdr'), st = document.querySelector('#page-yield .rank-sticky');
      const hs = hdr ? getComputedStyle(hdr) : null, ss = st ? getComputedStyle(st) : null;
      let occ = (hs && hs.position === 'sticky' && hs.display !== 'none') ? hdr.offsetHeight : 0;
      if (ss && ss.position === 'sticky') occ = Math.max(occ, (parseFloat(ss.top) || 0) + st.offsetHeight);
      const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: Math.max(0, row.getBoundingClientRect().top + window.scrollY - occ - 12), behavior: reduce ? 'auto' : 'smooth' });
    }
    return;
  }
  const off = (Array.isArray(ETFS) ? ETFS : []).filter(e => _matchEtf(e, q) > 0).sort((a, b) => _matchEtf(b, q) - _matchEtf(a, q))[0];
  msg.className = 'rank-find-msg miss';
  if (!off) msg.textContent = `找不到「${_yieldFind}」，試試代碼或名稱關鍵字`;
  else if (yieldView(off) && _yieldAll.some(e => e.code === off.code)) msg.textContent = `${off.code} ${off.name} — 未進前 ${YIELD_RANK_MAX} 名`;
  else msg.textContent = `${off.code} ${off.name} — 目前沒有可比較的配息資料，未列入排行`;
}
