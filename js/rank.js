// rank.js — 排行頁與站內搜尋
// 從 index.html 行 1687–1837 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Rank page ──────────────────────────────────────────────────────
function getEtfTag(code, name) {
  const c = code || '', n = name || '';
  if (c.endsWith('L') || /正2|2倍/.test(n))
    return { label:'槓桿', color:'#ef4444', border:'rgba(239,68,68,.35)', bg:'rgba(239,68,68,.08)' };
  if (c.endsWith('R') || /反[12]|放空/.test(n))
    return { label:'反向', color:'#f87171', border:'rgba(248,113,113,.35)', bg:'rgba(248,113,113,.08)' };
  if (c.endsWith('B') || n.includes('債'))
    return { label:'債券', color:'#60a5fa', border:'rgba(96,165,250,.35)', bg:'rgba(96,165,250,.08)' };
  if (c.endsWith('U') || /黃金|原油|黃豆|農產|白銀|天然氣/.test(n))
    return { label:'商品期貨', color:'#fb923c', border:'rgba(251,146,60,.35)', bg:'rgba(251,146,60,.08)' };
  return null;
}

function renderRank() {
  const SIG_LABEL = { cheap:'便宜', fair:'合理✓', hot:'過熱', dear:'偏貴', bond:'債券型' };
  const SIG_COLOR = { cheap:'#4ade80', fair:'#fde047', hot:'#ef4444', dear:'#fb923c', bond:'var(--bond)' };
  const fmtRet = v => (v == null) ? '--' : (v > 0 ? '+' : '') + v.toFixed(1) + '%';
  const retClr = v => (v == null || v === 0) ? 'var(--dim)' : v > 0 ? '#ff6b6b' : '#00e5a0';   // 台股：漲紅跌綠、0 中性（D1）

  // 開盤初期多數 ETF 當日成交量還是 0，只靠 cur_vol 過濾會只剩 20 幾支。
  // 有量的不足 100 支時放寬條件補滿，並以 avg_vol 當次要排序（未成交者依平時量排）。
  const byVol   = (a, b) => (b.cur_vol || 0) - (a.cur_vol || 0)
                         || (b.avg_vol || 0) - (a.avg_vol || 0);
  const withVol = [...ETFS].filter(e => (e.cur_vol || 0) > 0 && e.price > 0);
  const sorted  = (withVol.length >= 100 ? withVol
                                         : [...ETFS].filter(e => e.price > 0))
    .sort(byVol)
    .slice(0, 100);

  document.getElementById('rankTotal').textContent = sorted.length;
  _rankSorted = sorted;

  document.getElementById('rankRows').innerHTML = sorted.map((e, i) => {
    const rank  = i + 1;
    const cls   = rank===1?'gold':rank===2?'silver':rank===3?'bronze':'';
    const sigC  = SIG_COLOR[e.signal] || '#8b949e';
    const freq   = e.div_freq || e.div_frequency || '?';
    const noDiv  = freq === '不配息';
    const yldTxt = noDiv                          ? '不適用'
                 : e.yld_verified && e.yld > 0   ? e.yld.toFixed(1) + '%'
                 : (e.new_listing && !e.yld)      ? '未滿1歲'
                 : e.yld_pending                  ? '待公告'
                 : e.yld > 0                      ? '~' + e.yld.toFixed(1) + '%'
                 : '--';
    const yldClr = (e.yld > 0 && !noDiv)
                   ? (e.yld_verified ? '#f5c842' : '#8b7020')
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
                   ? `<button type="button" class="rank-flow" aria-label="查看 ${code} 持股異動">持股異動 ›</button>` : '';
    return `<div class="rank-row${hasFlow ? ' has-flow' : ''}" data-code="${code}" data-rank="${rank}">
      <button type="button" class="rank-hit" aria-label="第 ${rank} 名 ${code} ${name}，查看詳細資料"></button>
      <div class="rank-main">
        <div class="rank-no ${cls}">${rank}</div>
        <div class="rank-etf">
          <div class="rank-code">${e.code}</div>
          <div class="rank-name">${e.name}</div>
        </div>
        <div class="rank-price">${e.price}</div>
        <div class="rank-sig" style="color:${sigC}">${SIG_LABEL[e.signal]||'--'}</div>
      </div>
      <div class="rank-sub">
        <div class="rank-freq" style="${noDiv ? '' : 'color:#ff9500'}">${freq}</div>
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
  if (ev.target.closest('.rank-hit')) openDetail(row.dataset.code);
});

// ── 排行頁：找自己的 ETF ──────────────────────────────────────
// 只定位不過濾——使用者要看的是「我在第幾名」，把其他 99 支藏掉就失去參照。
// PO Change #2（PHASE5_PLAN §3.8）：搜尋與說明改為 🔍／ⓘ 按需展開，預設收起。
// 展開狀態只在記憶體（不寫 Router／history）；有搜尋內容時不因 ⓘ、輪詢重繪、Detail／Flow 往返而收起。
let _rankFind = '';
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
      ? `${h.e.code} ${h.e.name} — 第 ${h.rank} 名 / 共 ${_rankSorted.length} 支`
      : `${hits.length} 支符合，已全部標示（最前面是 ${h.e.code} ${h.e.name}，第 ${h.rank} 名）`;
    const row = document.querySelector(`#rankRows .rank-row[data-code="${h.e.code}"]`);
    if (row && scroll) {
      const top = row.getBoundingClientRect().top + window.scrollY - _rankOccludedTop() - 12;
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }
    return;
  }

  // 榜外：要明講「有這支但沒進榜」，不然使用者會以為搜尋壞了
  const off = ETFS.filter(e => _matchEtf(e, q) > 0)
                  .sort((a, b) => _matchEtf(b, q) - _matchEtf(a, q));
  msg.className = 'rank-find-msg miss';
  msg.textContent = off.length
    ? `${off[0].code} ${off[0].name} — 不在今日 TOP ${_rankSorted.length}（成交量未進榜，不代表不好）`
    : `找不到「${_rankFind}」，試試代碼或名稱關鍵字`;
}

