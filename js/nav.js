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
  yt:    { base: 'tools', tool: 'yt' },
  check: { base: 'cat', flow: true }
};

function switchPage(id) {
  cancelPendingSearch();
  const spec = _NAV_SPEC[id];
  if (!spec) return;
  if (spec.flow) Router.openFlow(_flowSel);
  else Router.toBase(spec);
}
