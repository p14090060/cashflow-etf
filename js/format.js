// format.js — miniBars、收藏按鈕、fmtYld、yldBadge
// 從 index.html 行 1325–1356 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。

// ── 00662 R1：價格／歷史單位待確認（market price_unit_status＝unverified）──
// 訊號已如實 null，不可 fallback 成「偏貴」；顯示中性「待確認」。其他商品（含既有 null 訊號）行為不變。
function unitPending(e) { return !!e && e.price_unit_status === 'unverified'; }
const UNIT_PENDING_LABEL = '待確認', UNIT_PENDING_CLS = 'sig-pending';

// ── 歷史不足的價格訊號標籤（PO 2026-11-26：新上市／更新中；純顯示，不寫資料）──
// 只在 signal 為 null 且 indicator_status 嚴格等於 insufficient_history 時適用；price_unit 待確認由呼叫端先判斷。
// listing_date（行情既有欄位）為嚴格合法 ISO 日期，且距台北今天 0～30 個日曆日（含第 30 天）→ 新上市；
// 第 31 天起、缺少、型別錯、格式錯、不存在日期、未來日期 → 更新中。不使用 new_listing 的一年語意、不猜日期。
const HIST_NEW_LABEL = '新上市', HIST_UPDATING_LABEL = '更新中', HIST_LABEL_CLS = 'sig-new', HIST_NEW_DAYS = 30;
function _histDayNum(iso) {
  if (typeof iso !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
  const y = +iso.slice(0, 4), m = +iso.slice(5, 7), d = +iso.slice(8, 10);
  const t = Date.UTC(y, m - 1, d);
  const c = new Date(t);
  if (c.getUTCFullYear() !== y || c.getUTCMonth() !== m - 1 || c.getUTCDate() !== d) return null;
  return t / 86400000;
}
// 台北日曆日（UTC+8，無日光節約）；測試可設 window.ETF_FIXED_TODAY='YYYY-MM-DD' 固定今天
function histTodayIso() {
  const fx = (typeof window !== 'undefined') ? window.ETF_FIXED_TODAY : undefined;
  if (_histDayNum(fx) != null) return fx;
  return new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10);
}
function historyLabel(e, todayIso) {
  if (!e || e.signal != null || e.indicator_status !== 'insufficient_history') return null;
  const ld = _histDayNum(e.listing_date), td = _histDayNum(todayIso || histTodayIso());
  const age = (ld == null || td == null) ? null : td - ld;
  return (age != null && age >= 0 && age <= HIST_NEW_DAYS) ? HIST_NEW_LABEL : HIST_UPDATING_LABEL;
}

// ── Mini bar chart（全域，排行頁、Detail、自選卡共用）──────────────────
// 台股語意（PO 硬規格，D1 全站）：漲＝紅、跌＝綠、0＝中性色、缺值＝灰。不得改成美股漲綠跌紅。
// opts.token：用 --up／--dn token（自選卡）；未指定時沿用原本排行頁的色值，只修正 0 的顏色。
function miniBars(months, opts) {
  if (!months || !months.length) return '<span style="color:var(--dim);font-size:11px">--</span>';
  const o = opts || {};
  const UP = 'var(--up)', DN = 'var(--dn)';   // Phase 5 V2：全站 miniBars 統一用 token（0 中性、缺值灰規則不變）
  const vals = months.map(v => v ?? 0);
  const maxAbs = Math.max(...vals.map(Math.abs), 2);
  return months.map(v => {
    const val = v ?? 0;
    let h, pos, col, rad, kind;
    if (v == null) {            // 缺值：灰色短柱（中線上方）
      h = 2; pos = 'bottom:13px'; col = 'rgba(var(--rgb-veil),.15)'; rad = '1px 1px 0 0'; kind = 'na';
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
      <div style="position:absolute;top:12px;left:0;right:0;height:1px;background:rgba(var(--rgb-veil),.12)"></div>
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
  if (e.new_listing && !e.yld) return '待配息評價';
  if (e.yld_pending) return '待公告';
  if (e.yld_verified) return e.yld > 0 ? e.yld.toFixed(1) + '%' : '--';
  return e.yld > 0 ? '~' + e.yld.toFixed(1) + '%' : '--';
}
function yldBadge(e) { return ''; }

