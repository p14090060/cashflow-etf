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

// ── 已核收益評價日（PO 2026-11-26 採用四檔方案；純顯示、不外連、不寫資料）──
// 只登錄已取得官方原件的四檔「此次適用評價日」。sha256 是本機保存原件的引用（可人工核對），前端不在線驗原件。
// 固定此次期別：過了評價日仍無結果就停在「待公告」，不自動滑到下一期／下一年。
// 00410A、009827 及其他未登錄商品不在此表，維持原本顯示。
const EVAL_DATE_REGISTRY = Object.freeze({
  '00954': Object.freeze({ code: '00954', name: '中國信託日本ETF傘型證券投資信託基金之中國信託日本半導體ETF證券投資信託基金',
    valuation_date: '2026-11-30', rule: '每年十一月最後日曆日（成立日起滿九十個日曆日後）',
    source_url: 'https://doc.twse.com.tw/pdf/202609_A00026_E70_4_20261126_152351.pdf',
    sha256: '353fe9a9ce8ec8bf4200ed7ce9f7a465bf00748e6db8840c905d2f20f35a9a5c', pages: '公開說明書 PDF p52',
    prior: 'https://www.twse.com.tw/zh/ETFortune/announcement?company=A00026&date=20251201&fund=00954&seq=1&type=distribution',
    prior_sha256: '431f30ffdbfc69c847741659d19336a48e458be950485d8f630ce4016041ff80' }),
  '009829': Object.freeze({ code: '009829', name: '大華銀韓國KOSPI 50 ETF證券投資信託基金',
    valuation_date: '2026-12-31', rule: '每年 6 月、12 月最後日曆日（成立日起屆滿九十日後）',
    source_url: 'https://doc.twse.com.tw/pdf/202609_A00049_E21_4_20261126_152156.pdf',
    sha256: '5bf3aef1cd2928bb1ddc09746613667791d3c7391c858cb4096debaf66b6893e', pages: '公開說明書 PDF p18', prior: null, prior_sha256: null }),
  '00983A': Object.freeze({ code: '00983A', name: '中國信託ARK創新主動式ETF證券投資信託基金',
    valuation_date: '2026-12-31', rule: '每年 12 月最後日曆日（成立日起滿九十個日曆日後）',
    source_url: 'https://doc.twse.com.tw/pdf/202609_A00026_E77_4_20261126_152533.pdf',
    sha256: '9a66dfb12caf76b372d27fad01f7a14119cfe10995d59a2c2fe1c5e56f6a2fd7', pages: '公開說明書 PDF p31',
    // 上一期（2025-12-31）不分配：只作上一期已結束的依據，不作本期「本期無」
    prior: 'https://www.twse.com.tw/zh/ETFortune/announcement?company=A00026&date=20260102&fund=00983A&seq=1&type=all',
    prior_sha256: '49a0051e6a4dabcc7e6bd75736a5a7297f1d33d4f614c49e23d6e312a49fe1ef' }),
  '00411A': Object.freeze({ code: '00411A', name: '統一股債傘型證券投資信託基金之統一前沿科技主動式ETF證券投資信託基金',
    valuation_date: '2027-03-31', rule: '每年三月最後日曆日（成立日 115/8/11 起屆滿一八○日後）；不適用同傘型美國公債子基金',
    source_url: 'https://www.ezmoney.com.tw/events/2026GFTA/00411A-prospectus.pdf',
    sha256: 'b5a93b8c6c0c9a3f641ee59996cbc277438b2d8f92e418383b3a94ed451ef8ce', pages: '完整公開說明書實體 PDF p35（印刷 33）、p73；成立日見簡式 p1／p2',
    prior: null, prior_sha256: null })
});
const EVAL_BEFORE_LABEL = '待配息評價', EVAL_AFTER_LABEL = '待公告';
const _EVAL_SHA = /^[0-9a-f]{64}$/;
// 登錄自身完整性：代號鍵＝內部代號、日期真實、來源網址 https、hash 格式正確。任一不符 → 不採用（回原行為）
function _evalEntry(code, reg) {
  try {
    const r = (reg || EVAL_DATE_REGISTRY)[code];
    if (!r || typeof r !== 'object' || r.code !== code) return null;
    if (_histDayNum(r.valuation_date) == null) return null;
    if (typeof r.sha256 !== 'string' || !_EVAL_SHA.test(r.sha256)) return null;
    if (typeof r.source_url !== 'string' || !/^https:\/\/[^\s]+$/.test(r.source_url)) return null;
    if (typeof r.pages !== 'string' || !r.pages || typeof r.name !== 'string' || !r.name) return null;
    if (r.prior != null && (typeof r.prior_sha256 !== 'string' || !_EVAL_SHA.test(r.prior_sha256))) return null;
    return r;
  } catch (_) { return null; }
}
// 本檔是否已有可能屬於當期的官方除息事件（CALENDAR source=official，日期在評價日之後）→ 登錄讓位，回原行為。
// 現有欄位無法證明金額是「本期官方公告金額」（見 detail.js D4），所以這裡只讓位、不宣稱已公告金額。
// 本檔事件日期壞掉 → 無法判斷，同樣讓位。
function _evalOfficialAfter(code, val, cal) {
  const list = Array.isArray(cal) ? cal : ((typeof CALENDAR !== 'undefined' && Array.isArray(CALENDAR)) ? CALENDAR : []);
  for (const c of list) {
    if (!c || typeof c !== 'object' || c.code !== code || c.source !== 'official') continue;
    if (_histDayNum(c.iso_date) == null) return true;
    if (c.iso_date > val) return true;
  }
  return false;
}
// 回傳「待配息評價」／「待公告」或 null（null＝不適用，呼叫端維持原本判斷）。
// 呼叫端須先處理：不配息、正殖利率、有效本期無。opts.today／opts.cal／opts.reg 供測試注入。
function evalDateLabel(e, opts) {
  try {
    if (!e || typeof e.code !== 'string') return null;
    const o = opts || {};
    const r = _evalEntry(e.code, o.reg);
    if (!r) return null;
    const td = o.today || histTodayIso();
    if (_histDayNum(td) == null) return null;
    // R1-F1：評價日已過 → 一律待公告。官方事件（只有日期、壞日期、未綁定當期的金額）不能把已過期的期別退回「待配息評價」；
    // 已核正殖利率／有效本期無／不配息由呼叫端先處理。
    if (td > r.valuation_date) return EVAL_AFTER_LABEL;
    // 評價日前（含當日）若已有評價日之後的官方事件，資料與此次期別不一致 → 讓位回原行為，不猜
    if (_evalOfficialAfter(e.code, r.valuation_date, o.cal)) return null;
    return EVAL_BEFORE_LABEL;
  } catch (_) { return null; }
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
  if (!e) return '--';
  const noDiv = (e.div_freq || e.div_frequency) === '不配息';
  // R1-F2：已登錄四檔的真缺值（null）也走已核評價日判斷；未登錄的 null 維持原本 '--'，null 不補 0
  if (e.yld == null) {
    const ev = (!noDiv && !(typeof distNoDistView === 'function' && distNoDistView(e))) ? evalDateLabel(e) : null;
    return ev || '--';
  }
  if (noDiv) return '不配息';
  if (!(e.yld > 0) && !(typeof distNoDistView === 'function' && distNoDistView(e))) {
    const ev = evalDateLabel(e);
    if (ev) return ev;
  }
  if (e.new_listing && !e.yld) return '待配息評價';
  if (e.yld_pending) return '待公告';
  if (e.yld_verified) return e.yld > 0 ? e.yld.toFixed(1) + '%' : '--';
  return e.yld > 0 ? '~' + e.yld.toFixed(1) + '%' : '--';
}
function yldBadge(e) { return ''; }

