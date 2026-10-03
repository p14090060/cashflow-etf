// render.js — renderMood、renderAll
// 從 index.html 行 1498–1686 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Mood card ──
function renderMood(market) {
  const pct = market ? market.change_pct : 0;
  const pt  = market ? market.change_pt  : 0;
  const pr  = market ? market.price      : 0;

  const MOODS = [
    { min:  1.0, emoji:'🚀', main:'大盤狂奔中',     sub:'追的人開心、沒上車的焦慮',     cta:'⚠️ 越漲越要冷靜，看看你想買的還合理嗎 ▼' },
    { min:  0.3, emoji:'😊', main:'大盤微微暖',     sub:'存股族笑笑看，跟風族先別急',   cta:'🔥 熱門排行更新囉 ▼' },
    { min: -0.3, emoji:'😐', main:'大盤裝睡中',     sub:'不漲不跌，適合慢慢挑',         cta:'🎯 來看看哪些 ETF 處於甜蜜點 ▼' },
    { min: -1.0, emoji:'🍂', main:'大盤小休息',     sub:'存股族的撿便宜時機到了？',     cta:'💧 今日合理價清單 ▼' },
    { min: -999, emoji:'🌧️', main:'大盤下雨天',     sub:'新聞會嚇人，但便宜貨可能來了', cta:'💎 跌出機會了嗎？來看今日合理價 ▼' },
  ];

  const m = MOODS.find(x => pct >= x.min) || MOODS[MOODS.length-1];
  document.getElementById('moodEmoji').textContent = m.emoji;
  document.getElementById('moodText').textContent  = m.main;
  document.getElementById('moodSub').textContent   = m.sub;
  document.getElementById('moodCta').textContent   = m.cta;

  const sign  = pt >= 0 ? '▲' : '▼';
  const cls   = pct >= 0.3 ? 'up' : pct <= -0.3 ? 'dn' : 'flat';
  const arrow = pt >= 0 ? '+' : '';
  const idxEl = document.getElementById('moodIdx');
  idxEl.className = `mood-idx ${cls}`;
  idxEl.textContent = pr > 0
    ? `加權 ${sign} ${arrow}${pt.toFixed(1)} (${arrow}${pct.toFixed(2)}%)`
    : '';
}

// ── renderAll：用資料渲染整頁 ──
function renderAll(etfs, cal, updatedAt, market, isClosed, isHoliday) {
  ETFS = etfs;
  const badge = document.getElementById('statusBadge');
  if (isHoliday) {
    badge.className = 'status-badge status-holiday';
    badge.textContent = '今日休市';
  } else if (isClosed) {
    badge.className = 'status-badge status-closed';
    const twNow = new Date(new Date().getTime() + 8 * 3600000);
    const todayStr = twNow.toISOString().slice(0, 10);
    const dataDateStr = (updatedAt || '').slice(0, 10);
    let label;
    if (dataDateStr < todayStr) {
      label = '盤後資料';
    } else {
      const twMin = twNow.getUTCHours() * 60 + twNow.getUTCMinutes();
      label = twMin < 9 * 60 ? '盤前資料' : '收盤資料';
    }
    badge.textContent = label + ' · ' + dataDateStr;
  } else {
    badge.className = 'status-badge status-live';
    badge.textContent = 'LIVE · 更新 ' + (updatedAt || '').slice(11, 16);
  }
  renderMood(market);

  const SIG_LABEL = { cheap:'便宜', fair:'合理✓', hot:'過熱', dear:'偏貴', bond:'債券型' };
  const SIG_CLASS = { cheap:'sig-cheap', fair:'sig-fair', hot:'sig-hot', dear:'sig-dear', bond:'sig-bond' };

  // 只從成交量前 100 篩選，避免冷門 ETF 混入
  const TOP100 = [...ETFS]
    .filter(e => (e.cur_vol || 0) > 0 && e.price > 0)
    .sort((a, b) => (b.cur_vol || 0) - (a.cur_vol || 0))
    .slice(0, 100);

  // ── A-2：便宜全顯示 + 合理最多5支 ──
  const hasDividend = e => (e.div_frequency || '') !== '不配息';
  const cheapList = TOP100.filter(e => e.signal === 'cheap' && e.price > 0 && hasDividend(e));
  const a2Base    = e => LAZY_WATCHLIST.has(e.code) && e.price > 0 && hasDividend(e);
  const fairOnly  = TOP100.filter(e => e.signal === 'fair'  && a2Base(e)).slice(0, 5);
  const showList  = [...cheapList, ...fairOnly];

  const renderBuyCard = (e, note='') => {
    const hasRange = e.low52 != null && e.high52 != null && e.high52 > e.low52;
    const pos = hasRange
      ? Math.min(97, Math.max(3, (e.price - e.low52) / (e.high52 - e.low52) * 100))
      : 50;
    const maDStr = e.maD != null
      ? `<span class="${e.maD>=0?'pos':'neg'}">${e.maD>=0?'+':''}${e.maD.toFixed(1)}%</span>`
      : `<span style="color:var(--dim)">--</span>`;
    return `<div class="buy-card">
      <div class="buy-top">
        <div><div class="buy-code">${e.code}</div><div class="buy-name">${e.name}</div></div>
        <div class="${SIG_CLASS[e.signal] || 'sig-dear'}">${SIG_LABEL[e.signal] || '偏貴'}</div>
      </div>
      ${note}
      <div class="buy-stats">
        <span><span class="lbl">現價 </span><span class="val">${e.price}</span></span>
        <span><span class="lbl">年化殖利率 </span><span class="val">${fmtYld(e)}</span></span>
        <span><span class="lbl">60MA </span>${maDStr}</span>
      </div>
      ${hasRange ? `<div class="range-track"><div class="range-fill" style="width:${pos}%"></div><div class="range-dot" style="left:${pos}%"></div></div>
      <div class="range-lbl"><span>低 ${e.low52}</span><span>高 ${e.high52}</span></div>` : ''}
      <div class="div-pill">${(e.yld || 0) > 0
        ? `🎁 ${e.days === 0 ? '今日配息' : `<span class="div-num">${e.days ?? '--'}</span> 天後配息`} · 預估 <span class="div-num">${e.est != null ? e.est.toFixed(2) : '--'}</span> 元/張`
        : '🆕 新ETF 待首次配息公告'}</div>
    </div>`;
  };

  if (showList.length > 0) {
    document.getElementById('buyCount').textContent = showList.length + ' 支';
    document.getElementById('buyCards').innerHTML = showList.map(e => renderBuyCard(e)).join('');
  } else {
    // fallback：LAZY_WATCHLIST 中最接近合理價的 3 支（maD 絕對值最小）
    const closest = [...ETFS]
      .filter(e => LAZY_WATCHLIST.has(e.code) && e.price > 0 && typeof e.maD === 'number'
                && e.signal !== 'hot' && e.signal !== 'dear' && hasDividend(e))
      .sort((a, b) => Math.abs(a.maD) - Math.abs(b.maD))
      .slice(0, 3);
    document.getElementById('buyCount').textContent = '0 支';
    document.getElementById('buyCards').innerHTML =
      (closest.length > 0
        ? `<div class="empty-why" style="margin-bottom:10px">📊 今日無符合合理價條件的 ETF，以下為最接近門檻的標的，僅供參考</div>`
          + closest.map(e => renderBuyCard(e)).join('')
        : `<div class="empty-state">
            目前沒有 ETF 符合篩選條件<br>
            大盤偏熱，可參考下方熱門排行或自行搜尋
            <div class="empty-why">
              ℹ️ 為什麼今天沒有？<br>
              當 ETF 普遍溢價、追在均線上方時，就會出現 0 支符合條件的情況。<br>
              這代表今天不是好的進場時機。
            </div>
          </div>`
      );
  }

  // TOP 10 熱門：與排行頁相同，取成交量前 10
  const top10 = TOP100.slice(0, 10);
  const rankClass = i => i===0?'gold':i===1?'silver':i===2?'bronze':'';
  document.getElementById('waitItems').innerHTML = top10.map((e,i) => `
    <div class="hot-item">
      <div class="hot-rank ${rankClass(i)}">${i+1}</div>
      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:center;gap:6px">
          <span class="wait-code" style="font-size:16px">${e.code}</span>
          <span class="wait-name">${e.name}</span>
        </div>
        <div style="font-size:16px;margin-top:2px">
          <span style="color:#fb923c">現價 ${(+e.price).toFixed(2)}</span>
          <span style="color:var(--dim)"> · 年殖利率 </span><span style="color:#fbbf24">${(e.new_listing && !e.yld) ? '0%新上市' : fmtYld(e)}</span>
        </div>
      </div>
      <div class="${SIG_CLASS[e.signal]}">${SIG_LABEL[e.signal]}</div>
    </div>`).join('');

  selETF = ETFS.find(e => e.code==='0056') || ETFS[0];
  renderChips();
  calcUpdate();

  const todayStr = new Date().toLocaleDateString('sv-SE'); // YYYY-MM-DD（本地時間）
  const futureCal = cal.filter(c => !c.iso_date || c.iso_date >= todayStr);
  document.getElementById('calList').innerHTML = futureCal.map(c => {
    const isToday    = c.iso_date === todayStr || c.days_until === 0;
    const amtSrc = c.amount_source || c.source || '';
    const srcHtml = c.amt == null ? ''
      : amtSrc === 'TWSE' || amtSrc === 'official'
      ? `<div class="src-lbl src-official">🏛 TWSE 官方公告</div>`
      : amtSrc === 'FinMind（估算）'
      ? `<div class="src-lbl src-estimate">🔍 FinMind 估算</div>`
      : amtSrc === 'manual'
      ? `<div class="src-lbl src-official">✅ 人工核實</div>`
      : amtSrc === 'estimate'
      ? `<div class="src-lbl src-estimate">📊 歷史平均估算</div>`
      : '';
    const pill = isToday
      ? `<div class="soon-pill today-pill">今日配息</div>`
      : c.soon ? `<div class="soon-pill">快配息囉～</div>` : '';
    const amtHtml = c.amt != null
      ? `<div class="cal-amt">${c.amt.toFixed(2)} 元</div><div class="cal-ulbl">每單位</div>`
      : `<div class="cal-amt" style="color:var(--dim);font-size:14px;font-weight:400;">待公告</div>`;
    return `
    <div class="cal-item ${isToday?'today':c.soon?'soon':''}">
      <div class="cal-date"><span class="cal-day">${c.day}</span><span class="cal-mon">${c.mon}</span></div>
      <div class="cal-line"></div>
      <div class="cal-info">
        <div class="cal-code2">${c.code}</div>
        <div class="cal-name2">${c.name}</div>
        ${srcHtml}
      </div>
      <div class="cal-r">
        ${amtHtml}
        ${pill}
      </div>
    </div>`;
  }).join('');

  renderRank();
}

