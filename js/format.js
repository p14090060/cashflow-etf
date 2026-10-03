// format.js — miniBars、fmtYld、yldBadge
// 從 index.html 行 1325–1356 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。

// ── Mini bar chart（全域，排行頁與持倉健檢共用）──────────────────
function miniBars(months) {
  if (!months || !months.length) return '<span style="color:var(--dim);font-size:11px">--</span>';
  const vals = months.map(v => v ?? 0);
  const maxAbs = Math.max(...vals.map(Math.abs), 2);
  return months.map(v => {
    const val = v ?? 0;
    const h   = v == null ? 2 : Math.max(2, Math.round(Math.abs(val) / maxAbs * 11));
    const tip = v != null ? (val >= 0 ? '+' : '') + val.toFixed(1) + '%' : '--';
    const col = v == null ? 'rgba(255,255,255,.15)' : val >= 0 ? '#ff6b6b' : '#00e5a0';
    const rad = val >= 0 ? '1px 1px 0 0' : '0 0 1px 1px';
    const pos = val >= 0 ? 'bottom:13px' : 'top:13px';
    return `<div style="position:relative;width:8px;height:26px;flex-shrink:0" title="${tip}">
      <div style="position:absolute;top:12px;left:0;right:0;height:1px;background:rgba(255,255,255,.12)"></div>
      <div style="position:absolute;width:8px;height:${h}px;${pos};background:${col};border-radius:${rad}"></div>
    </div>`;
  }).join('');
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

