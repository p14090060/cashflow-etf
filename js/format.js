// format.js — miniBars、收藏按鈕、fmtYld、yldBadge
// 從 index.html 行 1325–1356 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。

// ── Mini bar chart（全域，排行頁、Detail、自選卡共用）──────────────────
// 台股語意（PO 硬規格，D1 全站）：漲＝紅、跌＝綠、0＝中性色、缺值＝灰。不得改成美股漲綠跌紅。
// opts.token：用 --up／--dn token（自選卡）；未指定時沿用原本排行頁的色值，只修正 0 的顏色。
function miniBars(months, opts) {
  if (!months || !months.length) return '<span style="color:var(--dim);font-size:11px">--</span>';
  const o = opts || {};
  const UP = o.token ? 'var(--up)' : '#ff6b6b', DN = o.token ? 'var(--dn)' : '#00e5a0';
  const vals = months.map(v => v ?? 0);
  const maxAbs = Math.max(...vals.map(Math.abs), 2);
  return months.map(v => {
    const val = v ?? 0;
    let h, pos, col, rad, kind;
    if (v == null) {            // 缺值：灰色短柱（中線上方）
      h = 2; pos = 'bottom:13px'; col = 'rgba(255,255,255,.15)'; rad = '1px 1px 0 0'; kind = 'na';
    } else if (val === 0) {     // 0：中性色短柱，壓在中線上
      h = 3; pos = 'top:11px'; col = 'var(--dim)'; rad = '1px'; kind = 'zero';
    } else {
      h = Math.max(2, Math.round(Math.abs(val) / maxAbs * 11));
      pos = val > 0 ? 'bottom:13px' : 'top:13px';
      col = val > 0 ? UP : DN;
      rad = val > 0 ? '1px 1px 0 0' : '0 0 1px 1px';
      kind = val > 0 ? 'up' : 'dn';
    }
    const tip = v == null ? '--' : (val > 0 ? '+' : '') + val.toFixed(1) + '%';
    return `<div class="mb" data-k="${kind}" style="position:relative;width:8px;height:26px;flex-shrink:0" title="${tip}">
      <div style="position:absolute;top:12px;left:0;right:0;height:1px;background:rgba(255,255,255,.12)"></div>
      <div class="mb-bar" style="position:absolute;width:8px;height:${h}px;${pos};background:${col};border-radius:${rad}"></div>
    </div>`;
  }).join('');
}

// ── 收藏 ♡／♥ 按鈕（分類列、Detail、自選卡共用；狀態只來自 WatchStore）──
function _favEsc(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function _favLabel(code, on) {
  const list = (typeof ETFS !== 'undefined' && ETFS) ? ETFS : [];
  const e = list.find(x => x.code === code);
  return (on ? '從自選移除：' : '加入自選：') + code + (e && e.name ? ' ' + e.name : '');
}
function favBtnHtml(code, extraId) {
  const on = WatchStore.has(code);
  return '<button class="fav-btn' + (on ? ' on' : '') + '" type="button"' + (extraId ? ' id="' + extraId + '"' : '') +
         ' aria-pressed="' + on + '" aria-label="' + _favEsc(_favLabel(code, on)) + '">' + (on ? '♥' : '♡') + '</button>';
}
function favBtnSync(btn, code) {
  if (!btn) return;
  const on = !!code && WatchStore.has(code);
  btn.classList.toggle('on', on);
  btn.textContent = on ? '♥' : '♡';
  btn.setAttribute('aria-pressed', String(on));
  btn.setAttribute('aria-label', code ? _favLabel(code, on) : '加入自選');
}

// ── 殖利率顯示：核對通過顯示數字，未通過加 ~ 提示待確認 ──
function fmtYld(e) {
  if (!e || e.yld == null) return '--';
  const noDiv = (e.div_freq || e.div_frequency) === '不配息';
  if (noDiv) return '不配息';
  if (e.new_listing && !e.yld) return '未滿1歲';
  if (e.yld_pending) return '待公告';
  if (e.yld_verified) return e.yld > 0 ? e.yld.toFixed(1) + '%' : '--';
  return e.yld > 0 ? '~' + e.yld.toFixed(1) + '%' : '--';
}
function yldBadge(e) { return ''; }

