// nav.js — switchPage 分頁切換
// 從 index.html 行 833–845 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Page switch ──
function switchPage(id) {
  cancelPendingSearch();
  closeDetail();
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-'+id).classList.add('active');
  document.getElementById('nav-'+id).classList.add('active');
  window.scrollTo(0,0);
  // treemap 要容器有寬度才排得出來，切到這頁才畫
  if (id === 'check') renderFlow();
}

// ══ 主動式 ETF 買賣超 treemap ══════════════════════════════════
// 資料來自 scripts/fetch_active_etf.py：各投信官網 PCF 兩日快照相減。
