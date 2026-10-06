// nav.js — 底部導覽與分頁切換（Phase 3：經 Router；舊的 switchPage 名稱保留為相容入口）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：HTML 裡有行內 onclick 需要這些函式掛在 window 上。
// 導覽：首頁／分類／自選／工具。配息、排行、頻道 是「工具」的子頁；持股異動 是「分類 → 主動式」的分段。
const _NAV_SPEC = {
  today: { base: 'home' },
  cat:   { base: 'cat' },
  watch: { base: 'watch' },
  tools: { base: 'tools' },
  div:   { base: 'tools', tool: 'div' },
  rank:  { base: 'tools', tool: 'rank' },
  yt:    { external: 'https://www.youtube.com/@CashFlowDataRecorder' },   // Phase 5 G1：頻道頁退役，相容入口直接開外部頻道（新分頁、不寫 history）
  check: { flow: true }   // 主動式 ETF 持股異動：在目前 entry 上開 Flow 層（PHASE5_PLAN §3.4）
};

function switchPage(id) {
  cancelPendingSearch();
  const spec = _NAV_SPEC[id];
  if (!spec) return;
  if (spec.external) { window.open(spec.external, '_blank', 'noopener'); return; }
  if (spec.flow) Router.openFlow(_flowSel);
  else Router.toBase(spec);
}
