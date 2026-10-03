// archived-check.js — 健診頁邏輯（2026-09-23 下架，整塊註解保留）
// 從 index.html 行 1129–1324 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
/* ── 健診頁邏輯（2026-09-23 下架，整頁改放主動式 ETF 買賣超）──
   對應的 HTML 存在 <template id="archived-check"> 裡，兩邊要一起恢復。
── 以下原樣保留 ──
let _dcaOn = true, _rate = 8;

function setDCA(on) {
  _dcaOn = on;
  document.getElementById('dcaYes').classList.toggle('active', on);
  document.getElementById('dcaNo').classList.toggle('active', !on);
  document.getElementById('monthlyRow').style.display = on ? '' : 'none';
  document.getElementById('dcaTip').style.display = on ? '' : 'none';
}

function setRate(r) {
  _rate = r;
  document.getElementById('chkRate').value = r;
  document.getElementById('rateVal').textContent = r;
  [5, 8, 12].forEach(v => document.getElementById('rateBtn'+v).classList.toggle('active', v === r));
}

function updateRate(v) {
  _rate = parseFloat(v);
  document.getElementById('rateVal').textContent = parseFloat(v).toFixed(1).replace('.0','');
  [5, 8, 12].forEach(r => document.getElementById('rateBtn'+r).classList.remove('active'));
  if ([5, 8, 12].includes(_rate)) document.getElementById('rateBtn'+_rate).classList.add('active');
}

function runCalc() {
  const cap     = parseFloat(document.getElementById('chkCapital').value) || 0;
  const monthly = _dcaOn ? (parseFloat(document.getElementById('chkMonthly').value) || 0) : 0;
  const mr      = _rate / 100 / 12;

  const tbody = document.getElementById('projBody');
  tbody.innerHTML = [1, 3, 5, 10].map(yr => {
    const m  = yr * 12;
    const fv = cap * Math.pow(1+mr, m) + (monthly > 0 ? monthly * (Math.pow(1+mr, m)-1)/mr : 0);
    const md = Math.round(fv * (_rate/100) / 12);
    return `<tr>
      <td class="year-col">${yr} 年</td>
      <td>${(fv/10000).toFixed(1)} 萬</td>
      <td>${md.toLocaleString()} 元</td>
    </tr>`;
  }).join('');

  let risk, label, chips;
  if (_rate <= 6) {
    risk='C'; label='穩健保守型';
    chips=['0056 元大高股息','00878 國泰永續高息','00713 高息低波'];
  } else if (_rate <= 9) {
    risk='M'; label='均衡成長型';
    chips=['0050 元大台灣50','006208 富邦台50','00878 國泰永續高息'];
  } else {
    risk='A'; label='積極成長型';
    chips=['00929 復華科技優息','00940 台灣價值高息','00981A 統一台股增長'];
  }
  const badge = document.getElementById('riskBadge');
  badge.className = 'risk-badge risk-'+risk;
  badge.textContent = label;
  document.getElementById('suggestRow').innerHTML = chips.map(s=>`<span class="suggest-chip">${s}</span>`).join('');
  document.getElementById('calcResult').style.display = '';
}

function holdingHint(signal, profitPct) {
  const profit = profitPct !== null && profitPct > 0;
  const loss   = profitPct !== null && profitPct < 0;
  // 債券 ETF 的漲跌看利率，不是位置高低，給不出「便宜/偏貴」那種建議
  if (signal === 'bond')  return '債券型 ETF 主要看利率與配息，本頁不提供價格位置判斷';
  if (signal === 'hot')   return profit ? '目前位置偏熱，持倉已有獲利，可留意風險' : '目前追高風險偏高，宜觀察後再決定';
  if (signal === 'dear')  return profit ? '目前位置偏高，持倉已有獲利，可考慮分批調節' : '目前位置偏高，宜等待回落再評估';
  if (signal === 'fair')  return '目前處於合理區間，可安心持有';
  if (signal === 'cheap') return loss   ? '目前位置偏低，已有未實現虧損，可評估是否分批攤低成本' : '目前估值偏低，位置相對有利';
  return '';
}

function runHoldingCheck() {
  const code   = (document.getElementById('hldCode').value || '').trim().toUpperCase();
  const shares = parseFloat(document.getElementById('hldShares').value) || 0;
  const cost   = parseFloat(document.getElementById('hldCost').value)   || 0;
  const out    = document.getElementById('holdingResult');

  if (!code) { out.innerHTML = '<div class="health-miss">請輸入 ETF 代碼</div>'; return; }
  const etf = ETFS.find(e => e.code === code);
  if (!etf) { out.innerHTML = '<div class="health-miss">查無此代碼，可能不在今日成交量清單</div>'; return; }

  const price    = etf.price;
  const sigLabel = { cheap:'便宜', fair:'合理✓', hot:'過熱', dear:'偏貴', bond:'債券型' }[etf.signal] || '偏貴';
  const sigClass = { cheap:'sig-cheap', fair:'sig-fair', hot:'sig-hot', dear:'sig-dear', bond:'sig-bond' }[etf.signal] || 'sig-dear';

  // 損益
  const profitPct = cost > 0 ? (price - cost) / cost * 100 : null;
  const profitAmt = (cost > 0 && shares > 0) ? (price - cost) * 1000 * shares : null;
  const profitClr = profitPct === null ? 'var(--dim)' : profitPct >= 0 ? '#ff6b6b' : '#00e5a0';
  const profitTxt = profitPct === null ? '--'
    : `${profitPct >= 0 ? '+' : ''}${profitPct.toFixed(2)}%`
      + (profitAmt !== null ? `　${profitAmt >= 0 ? '+' : ''}NT$${Math.round(profitAmt).toLocaleString()}` : '');

  // 52週位置
  const pos = etf.high52 > etf.low52
    ? Math.min(97, Math.max(3, (price - etf.low52) / (etf.high52 - etf.low52) * 100)) : 50;

  // 配息
  const noDiv            = (etf.div_frequency || etf.div_freq) === '不配息';
  const divDays          = etf.days;
  const isNewUnannounced = etf.new_listing && !etf.yld;
  const divTxt  = noDiv             ? '不配息'
                : isNewUnannounced  ? '新上市待公告'
                : divDays === 0     ? '今日配息'
                : divDays           ? `${divDays} 天後配息`
                : '--';
  const estAmt  = (!noDiv && !isNewUnannounced && etf.est && shares > 0) ? (etf.est * 1000 * shares).toFixed(0) : null;

  // 近3月
  const bars = miniBars((etf.ret_months || []).slice(-3));

  // 暗示語
  const hint = holdingHint(etf.signal, profitPct);

  out.innerHTML = `
    <div class="buy-card" style="margin-top:4px">
      <div class="buy-top">
        <div>
          <div class="buy-code">${etf.code}</div>
          <div class="buy-name">${etf.name}</div>
        </div>
        <div class="${sigClass}">${sigLabel}</div>
      </div>

      <div class="health-grid" style="margin-top:10px">
        <div class="health-kv">
          <div class="k">現價</div>
          <div class="v">${price}</div>
        </div>
        <div class="health-kv">
          <div class="k">持倉損益</div>
          <div class="v" style="color:${profitClr}">${profitTxt}</div>
        </div>
        <div class="health-kv">
          <div class="k">年殖利率</div>
          <div class="v">${fmtYld(etf)}</div>
        </div>
        <div class="health-kv" style="grid-column:1/-1;display:flex;justify-content:space-between;align-items:baseline">
          <div class="k">配息</div>
          <div class="v" style="text-align:right">${divTxt}${estAmt ? `　預估 <span style="color:var(--fair)">NT$${parseInt(estAmt).toLocaleString()}</span>` : ''}</div>
        </div>
      </div>

      <div class="range-track" style="margin:12px 0 4px">
        <div class="range-fill" style="width:${pos}%"></div>
        <div class="range-dot"  style="left:${pos}%"></div>
      </div>
      <div class="range-lbl"><span>低 ${etf.low52}</span><span>高 ${etf.high52}</span></div>

      <div style="display:flex;align-items:center;gap:6px;margin-top:10px">
        <span style="font-size:15px;color:var(--dim)">近3月績效</span>
        <div class="mini-bars">${bars}</div>
        <span style="font-size:15px;color:var(--dim);margin-left:4px">
          ${(etf.ret_months||[]).slice(-3).map(v => v==null?'--':(v>=0?'+':'')+v.toFixed(1)+'%').join('　')}
        </span>
      </div>

      ${hint ? `<div style="margin-top:12px;padding:8px 10px;background:rgba(255,255,255,.04);border-radius:6px;font-size:15px;color:var(--dim)">📌 ${hint}</div>` : ''}
    </div>`;
}

function runETFCheck() {
  const codes = [0,1,2,3,4]
    .map(i => document.getElementById('etfInp'+i).value.trim().toUpperCase())
    .filter(Boolean);
  const out = document.getElementById('etfCheckResult');
  if (!codes.length) { out.innerHTML = '<div class="health-miss">請至少輸入一支 ETF 代碼</div>'; return; }

  const SIG_LABEL = { cheap:'便宜', fair:'合理✓', hot:'過熱', dear:'偏貴', bond:'債券型' };
  const SIG_COLOR = { cheap:'var(--cheap)', fair:'var(--fair)', hot:'#ef4444', dear:'#fb923c', bond:'var(--bond)' };

  out.innerHTML = codes.map(code => {
    const etf = ETFS.find(e => e.code.toUpperCase() === code);
    if (!etf) return `<div class="health-card"><div class="health-top"><div><div class="health-code">${code}</div><div class="health-name" style="color:var(--dear)">查無資料（不在今日清單）</div></div></div></div>`;
    const sigColor = SIG_COLOR[etf.signal] || 'var(--dear)';
    const fmt = v => (v == null || isNaN(v)) ? '0%' : (v >= 0 ? '+' : '') + v + '%';
    return `<div class="health-card">
      <div class="health-top">
        <div><div class="health-code">${etf.code}</div><div class="health-name">${etf.name}</div></div>
        <div style="font-size:16px;font-weight:700;color:${sigColor}">${SIG_LABEL[etf.signal]||'目前偏貴'}</div>
      </div>
      <div class="health-grid">
        <div class="health-kv"><div class="k">現價</div><div class="v">${etf.price}</div></div>
        <div class="health-kv"><div class="k">年化殖利率</div><div class="v">${fmtYld(etf)}</div></div>
        <div class="health-kv"><div class="k">溢折價</div><div class="v" style="color:${etf.premium>=0?'var(--dear)':'var(--cheap)'}">${fmt(etf.premium)}</div></div>
        <div class="health-kv"><div class="k">60MA偏離</div><div class="v" style="color:${etf.maD>=0?'var(--dear)':'var(--cheap)'}">${fmt(etf.maD)}</div></div>
        <div class="health-kv"><div class="k">5日漲跌</div><div class="v" style="color:${etf.ret5d>=0?'var(--dear)':'var(--cheap)'}">${fmt(etf.ret5d)}</div></div>
        <div class="health-kv"><div class="k">量比</div><div class="v">${etf.vol_ratio ?? 0}x</div></div>
      </div>
    </div>`;
  }).join('');
}
── 健診頁邏輯結束 ── */
