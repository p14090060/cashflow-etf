// lookup.js — 單檔查詢（今日頁／配息頁）
// 從 index.html 行 1414–1497 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Lookup functions ──
function lookupCustom() {
  const raw = document.getElementById('customCode').value.trim().toUpperCase();
  const msgEl = document.getElementById('customMsg');
  if (!raw) { msgEl.style.display='none'; return; }
  const found = ETFS.find(e => e.code === raw);
  if (found) {
    msgEl.className = 'custom-msg ok';
    msgEl.textContent = `✓ ${found.code} ${found.name} 已在清單中，請直接點選上方晶片`;
    msgEl.style.display = 'block';
    selChip(found.code);
    return;
  }
  if (!/^\d{4,6}[A-Z]?$/.test(raw)) {
    msgEl.className = 'custom-msg err';
    msgEl.textContent = `✗ 「${raw}」不像是有效的 ETF 代碼`;
    msgEl.style.display = 'block';
    return;
  }
  msgEl.className = 'custom-msg warn';
  msgEl.textContent = `⚠ ${raw} 不在預設清單，以下為估算數值`;
  msgEl.style.display = 'block';
  const estPrice = 20 + Math.floor((parseInt(raw) % 100) * 0.6);
  const estYld   = 4.5 + (parseInt(raw.replace(/\D/g,'')) % 30) * 0.1;
  const estDays  = 30 + (parseInt(raw.replace(/\D/g,'')) % 60);
  selETF = {
    code: raw, name: `ETF ${raw}（估算）`,
    price: estPrice, ma60: estPrice * 0.98,
    low52: estPrice * 0.85, high52: estPrice * 1.12,
    yld: parseFloat(estYld.toFixed(1)),
    days: estDays, est: parseFloat(((estPrice * estYld / 100) / 4).toFixed(2)),
    signal: 'fair', maD: 0
  };
  const chips = document.getElementById('chips');
  const existing = chips.querySelector('.custom-chip');
  if (existing) existing.remove();
  const chip = document.createElement('div');
  chip.className = 'etf-chip on custom-chip';
  chip.textContent = raw;
  chips.appendChild(chip);
  chips.querySelectorAll('.etf-chip:not(.custom-chip)').forEach(c => c.classList.remove('on'));
  calcUpdate();
}

function lookupToday() {
  const raw = document.getElementById('todayCode').value.trim().toUpperCase();
  const msgEl = document.getElementById('todayMsg');
  const resEl = document.getElementById('todayResult');
  resEl.innerHTML = '';
  if (!raw) { msgEl.style.display = 'none'; return; }
  const found = ETFS.find(e => e.code === raw);
  if (found) {
    msgEl.style.display = 'none';
    resEl.innerHTML = renderSignalCard(found, false);
    return;
  }
  if (!/^\d{4,6}[A-Z]?$/.test(raw)) {
    msgEl.className = 'custom-msg err';
    msgEl.textContent = `✗ 「${raw}」不像是有效的 ETF 代碼`;
    msgEl.style.display = 'block';
    return;
  }
  msgEl.className = 'custom-msg warn';
  msgEl.textContent = `⚠ ${raw} 不在預設清單，以下為估算數值`;
  msgEl.style.display = 'block';
  const base = parseInt(raw.replace(/\D/g, ''));
  const estPrice = parseFloat((20 + (base % 100) * 0.6).toFixed(1));
  const estYld   = parseFloat((4.5 + (base % 30) * 0.1).toFixed(1));
  const estDays  = 30 + (base % 60);
  const estMaD   = parseFloat((((base % 20) - 10) * 0.3).toFixed(1));
  resEl.innerHTML = renderSignalCard({
    code: raw, name: `ETF ${raw}`,
    price: estPrice, ma60: estPrice * 0.98,
    low52: parseFloat((estPrice * 0.85).toFixed(1)),
    high52: parseFloat((estPrice * 1.15).toFixed(1)),
    yld: estYld, days: estDays,
    est: parseFloat(((estPrice * estYld / 100) / 4).toFixed(2)),
    signal: estMaD < -2 ? 'cheap' : estMaD > 2 ? 'dear' : 'fair', maD: estMaD
  }, true);
}

document.getElementById('customCode').addEventListener('keydown', e => { if (e.key==='Enter') lookupCustom(); });
document.getElementById('todayCode').addEventListener('keydown',  e => { if (e.key==='Enter') lookupToday();  });

