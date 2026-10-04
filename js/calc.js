// calc.js — ETFS 全域、配息 chips、計算機、訊號卡
// 從 index.html 行 1357–1413 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Mutable globals（renderAll 會更新）──
// 2026-10-03：初始值從 STATIC_ETFS（10 檔寫死假價格）改成空陣列。
// 抓不到資料時寧可畫面空著並明說，也不要拿假資料充數。
let ETFS = [];
let CALENDAR = [];
let selETF = ETFS.find(e => e.curated !== false) || ETFS[0];

// ── Chip & calculator（只顯示精選 ETF，有準確配息資料）──
function renderChips() {
  const curated = ETFS.filter(e => e.curated !== false);
  document.getElementById('chips').innerHTML = curated.map(e =>
    `<div class="etf-chip ${e.code===selETF?.code?'on':''}" onclick="selChip('${e.code}')">${e.code}</div>`
  ).join('');
}
// 2026-10-03：拿掉結尾的 revCalcUpdate() 呼叫。
// 那個函式整個專案都不存在（CSS 還留著 /* ── 逆向計算機 ── */，看來是當年移除
// 「逆向計算機」時漏清這個呼叫點），所以每點一次晶片就丟一次
// 「Uncaught ReferenceError: revCalcUpdate is not defined」。
// 因為它排在最後，前面三件事都做完了，畫面看起來正常，只有 console 有紅字——
// 最容易被當成「沒壞」而一直留著的那種。pre-split 第 1368 行一字不差，非拆檔造成。
function selChip(code) { selETF = ETFS.find(e => e.code===code); renderChips(); calcUpdate(); }
function calcUpdate() {
  const n = parseInt(document.getElementById('sharesIn').value) || 0;
  const next = (selETF.est * n * 1000).toFixed(0);
  const ann  = (selETF.yld / 100 * selETF.price * n * 1000).toFixed(0);
  const cost = (selETF.price * n * 1000).toFixed(0);
  document.getElementById('calcOut').innerHTML = `
    <div class="calc-row"><span class="calc-lbl"><span class="big-num">${selETF.days}</span> 天後可以領</span><span class="calc-val">${parseInt(next).toLocaleString()} 元</span></div>
    <div class="calc-row"><span class="calc-lbl">預估年化領回</span><span class="calc-val sm">${parseInt(ann).toLocaleString()} 元 (${selETF.yld}%)</span></div>
    <div class="calc-row"><span class="calc-lbl">${n} 張市值約</span><span class="calc-val sm">${parseInt(cost).toLocaleString()} 元</span></div>`;
}
document.getElementById('sharesIn').addEventListener('input', calcUpdate);

// ── Signal card renderer ──
function renderSignalCard(etf, estimated) {
  const hasRange = etf.low52 != null && etf.high52 != null && etf.high52 > etf.low52;
  const pos = hasRange ? Math.min(97, Math.max(3, (etf.price - etf.low52) / (etf.high52 - etf.low52) * 100)) : 50;
  const sigLabel = { cheap:'便宜', fair:'合理✓', hot:'過熱', dear:'偏貴', bond:'債券型' }[etf.signal] || '偏貴';
  const sigClass = { cheap:'sig-cheap', fair:'sig-fair', hot:'sig-hot', dear:'sig-dear', bond:'sig-bond' }[etf.signal] || 'sig-dear';
  const note = estimated ? `<div style="font-size:16px;color:var(--dim);margin-top:8px">⚠ 估算數值，每日更新後將顯示真實資料</div>` : '';
  const maDStr = etf.maD != null
    ? `<span class="${etf.maD>=0?'pos':'neg'}">${etf.maD>=0?'+':''}${etf.maD.toFixed(1)}%</span>`
    : `<span style="color:var(--dim)">--</span>`;
  const rangeHtml = hasRange
    ? `<div class="range-track"><div class="range-fill" style="width:${pos}%"></div><div class="range-dot" style="left:${pos}%"></div></div>
    <div class="range-lbl"><span>低 ${etf.low52}</span><span>高 ${etf.high52}</span></div>`
    : `<div style="color:var(--dim);font-size:14px;margin:8px 0">52週區間資料不足</div>`;
  const divPill = (etf.yld || 0) > 0
    ? `🎁 ${etf.days === 0 ? '今日配息' : `<span class="div-num">${etf.days ?? '--'}</span> 天後配息`}${etf.est != null ? ` · 預估 <span class="div-num">${etf.est.toFixed(2)}</span> 元/張` : ''}`
    : '🆕 新ETF 待首次配息公告';
  return `<div class="buy-card">
    <div class="buy-top">
      <div><div class="buy-code">${etf.code}</div><div class="buy-name">${etf.name}</div></div>
      <div class="${sigClass}">${sigLabel}</div>
    </div>
    <div class="buy-stats">
      <span><span class="lbl">現價 </span><span class="val">${etf.price}</span></span>
      <span><span class="lbl">年化殖利率 </span><span class="val">${fmtYld(etf)}</span></span>
      <span><span class="lbl">60MA </span>${maDStr}</span>
    </div>
    ${rangeHtml}
    <div class="div-pill">${divPill}</div>
    ${note}
  </div>`;
}

