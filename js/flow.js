// flow.js — 主動式 ETF 持股異動 treemap
// 從 index.html 行 846–1128 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
let _flowData = null, _flowCells = [], _flowSel = null;
let _rankSorted = [];   // 排行頁當前榜單，搜尋定位用

// 最後一次真的換檔是不是在 days 天內（排行頁標籤的有效期）
function _changedWithin(dateStr, days) {
  if (!dateStr) return false;
  const d = new Date(dateStr + 'T00:00:00');
  if (isNaN(d)) return false;
  return (Date.now() - d.getTime()) / 86400000 <= days;
}

// loading / ok / failed：成分 Tab 只在 ok 時出現，loading 與 failed 都不顯示
let _flowStatus = 'loading';

function fetchFlow() {
  // 先試同源相對路徑（GitHub Pages 上最新、本機開檔也能測），失敗再退 raw
  const ok = r => { if (!r.ok) throw 0; return r.json(); };
  return fetch('data/active_flow.json?t=' + Date.now()).then(ok)
    .catch(() => fetch('https://raw.githubusercontent.com/p14090060/cashflow-etf/main/data/active_flow.json?t=' + Date.now()).then(ok))
    .then(d => { _flowData = d; _flowStatus = 'ok'; detailOnFlowUpdate(); if (typeof Category !== "undefined") Category.onFlowData(); return d; })
    .catch(() => { _flowStatus = 'failed'; detailOnFlowUpdate(); return null; });
}

// Squarified treemap：把 items 依 value 填滿 (x,y,w,h)，盡量接近正方形
function squarify(items, x, y, w, h) {
  const out = [], total = items.reduce((s, i) => s + i.value, 0);
  if (!total || w <= 0 || h <= 0) return out;
  const scale = (w * h) / total;
  const nodes = items.map(i => Object.assign({}, i, { area: i.value * scale }));

  const worst = (row, len) => {
    const s = row.reduce((a, b) => a + b.area, 0);
    const mx = Math.max.apply(null, row.map(r => r.area));
    const mn = Math.min.apply(null, row.map(r => r.area));
    return Math.max((len * len * mx) / (s * s), (s * s) / (len * len * mn));
  };

  let rx = x, ry = y, rw = w, rh = h, i = 0;
  while (i < nodes.length && rw > 0.5 && rh > 0.5) {
    const vertical = rw >= rh;              // 寬 > 高：在左側疊一整欄
    const len = vertical ? rh : rw;
    const row = [nodes[i]];
    let j = i + 1;
    while (j < nodes.length && worst(row.concat([nodes[j]]), len) <= worst(row, len)) {
      row.push(nodes[j]); j++;
    }
    const thick = row.reduce((a, b) => a + b.area, 0) / len;
    let off = 0;
    for (const n of row) {
      const side = n.area / thick;
      out.push(Object.assign({}, n, vertical
        ? { x: rx, y: ry + off, w: thick, h: side }
        : { x: rx + off, y: ry, w: side, h: thick }));
      off += side;
    }
    if (vertical) { rx += thick; rw -= thick; }
    else          { ry += thick; rh -= thick; }
    i = j;
  }
  return out;
}

const _oku = v => (Math.abs(v) / 1e8).toFixed(1) + '億';

// 取前 keep 檔，其餘併成「其他 N 檔」
function _trim(list, keep) {
  if (list.length <= keep) return list.slice();
  const head = list.slice(0, keep), tail = list.slice(keep);
  const sum = tail.reduce((s, x) => s + Math.abs(x.amount), 0);
  head.push({ code: '', name: '其他 ' + tail.length + ' 檔', amount: sum, top_etf: '', _agg: true });
  return head;
}

function flowSelect(code) { _flowSel = code; if (typeof Category !== "undefined") Category.setFlowCode(code); renderFlow(); }

// 海外持股（美股、日股…）查不到台股收盤價，算不出金額也畫不進 treemap。
// 但 PCF 本來就寫了增減股數，條列出來至少看得到「買賣了什麼、幾股」。
// 舊版 active_flow.json 的 no_price 是純字串陣列（只有代碼），要能一起吃，
// 否則 Action 還沒重跑之前這塊會整個爆掉。
// 彭博市場別代碼，**不是 ISO 國碼**，這兩套長得像但對不起來。
// 2026-10-02 實測全部持股共出現 14 種，每一種都拿成分股本身的身分核對過：
//   300757 CH = ROBOTECHNIK，深圳創業板的中國 A 股 → 陸，不是瑞士
//   （舊表照 ISO 把 CH 當瑞士，畫面上會把中國股標成「瑞」）
//   SDLF LN = 標準人壽（英）、UCG IM = 裕信（義）、ABN NA = 荷蘭銀行（荷）
//   AMUN FP = 東方匯理（法）、IFX GY = 英飛凌（德）、CABK SM = 凱克薩（西）
//   BOCHGR GA = 賽普勒斯銀行（掛雅典）、KBC BB = 比利時聯合金融（比）
//   009150 KS / KP = 三星電機，兩家投信寫法不同，都是韓國
// 舊表裡的 KR/GB/DE/FR/NL/CA/AU/SG/TW 是 ISO 碼，實測一次都沒出現過，已刪。
// 認不得的會原樣顯示代碼（見 _npList 的 || mkt），不會壞掉。
const _NP_MKT = { US:'美', JP:'日', HK:'港', CH:'陸', KS:'韓', KP:'韓',
                  LN:'英', GY:'德', FP:'法', IM:'義', NA:'荷', SM:'西',
                  GA:'希', BB:'比' };

function _npRows(e) {
  return (e.no_price || []).map(x =>
    (typeof x === 'string') ? { code: x, name: '', delta_shares: null } : x);
}

function _npList(rows) {
  const body = rows.map(r => {
    // 統一投信給 Bloomberg 格式「TWLO US」「285A JP」，摩根給純代號「NVDA」，
    // 兩種都要認得：結尾是兩個大寫字母才當市場別切掉。
    const sp = String(r.code || '').trim().split(' ');
    let mkt = '';
    if (sp.length > 1 && sp[sp.length - 1].length === 2) mkt = sp.pop();
    const tick = sp.join(' ');
    const d = r.delta_shares;
    // 台股慣例：紅=加碼、綠=減碼，與 treemap 同一套語言
    const clr = (d == null) ? 'var(--dim)' : (d > 0 ? 'var(--up)' : 'var(--dn)');
    // 只靠 +/- 和顏色太弱：字小、又跟金額的呈現方式不一樣。直接寫出來。
    const txt = (d == null) ? '有異動'
              : (d > 0 ? '加碼 +' : '減碼 -') + Math.abs(d).toLocaleString() + ' 股';
    return '<div class="np-row">' +
      '<div class="np-id">' + tick +
        (mkt ? '<span class="np-mkt">' + (_NP_MKT[mkt] || mkt) + '</span>' : '') + '</div>' +
      '<div class="np-name">' + (r.name || '') + '</div>' +
      '<div class="np-d" style="color:' + clr + '">' + txt + '</div>' +
      '</div>';
  }).join('');
  return '<div class="np-wrap">' +
    '<div class="np-hd">海外持股異動 <b>' + rows.length + '</b> 檔　' +
      '查無報價來源，只列增減股數（紅加碼、綠減碼）</div>' +
    '<div class="np-list">' + body + '</div></div>';
}

// 空狀態一律走這裡：順手把框框縮起來，免得每個 return 點都要記得加 class
function _tmEmpty(box, html, cls) {
  box.classList.add('tm-slim');
  box.innerHTML = '<div class="tm-empty' + (cls ? ' ' + cls : '') + '">' + html + '</div>';
}

function renderFlow(code) {
  if (code) _flowSel = code;
  const box = document.getElementById('treemap');
  if (!box) return;
  const draw = () => {
    const d = _flowData;
    if (!d) { _tmEmpty(box, '持股異動資料載入失敗'); return; }

    const all = d.etfs || {};
    const codes = Object.keys(all).sort();
    if (!codes.length) { _tmEmpty(box, '目前沒有可用的主動式 ETF 資料'); return; }

    // 預設選異動金額最大的那檔，最有得看
    if (!_flowSel || !all[_flowSel]) {
      _flowSel = codes.slice().sort((a, b) =>
        (Math.abs(all[b].buy) + Math.abs(all[b].sell)) - (Math.abs(all[a].buy) + Math.abs(all[a].sell)))[0];
    }
    const e = all[_flowSel];

    document.getElementById('flowChips').innerHTML = codes.map(c =>
      '<div class="flow-chip' + (c === _flowSel ? ' active' : '') + '" onclick="flowSelect(\'' + c + '\')">' +
      c + '</div>').join('');

    const span = (e.flow_from && e.flow_to) ? e.flow_from + ' → ' + e.flow_to : '';
    document.getElementById('flowMeta').textContent =
      e.name + '　持股 ' + e.holdings + ' 檔' + (span ? '　' + span + ' 調整' : '');
    // 全海外持股的 ETF 換再多也算不出金額，顯示「+0.0億」會被讀成「沒動作」
    const hasAmt = !!(e.buy || e.sell);
    document.getElementById('flowBuy').textContent  = hasAmt ? '+' + _oku(e.buy || 0)  : '—';
    document.getElementById('flowSell').textContent = hasAmt ? '-' + _oku(e.sell || 0) : '—';
    // 各投信 PCF 公告有 1~2 天落差且各檔不同，資料日一定要標出來
    document.getElementById('flowCover').textContent =
      '資料來源：' + e.issuer + '投信官網公告 PCF（申購買回清單）　最新資料日 ' + (e.data_date || '-') +
      (e.price_date ? '　金額以 ' + e.price_date + ' 收盤價換算' : '') +
      '　PCF 公告通常落後行情 1~2 天';
    const npRows = _npRows(e), np = npRows.length;
    const tips = [];
    // 「以下為…」這種話只有在下面真的有東西時才能講。沿用的舊紀錄可能根本
    // 是空的——00983A 中信ARK 從 2026-09-23 開始追蹤起一次換股都沒記錄到
    // （flow 空、no_price 空、last_change_date 是 null），這幾條卻照樣宣告
    // 「以下為最近一次調整」，下面緊接著就是「目前沒有可顯示的調整紀錄」，
    // 自己打自己臉。Gavin 2026-10-02 截圖問「這是真的嗎」就是看到這個。
    const hasPrev = !!((e.flow && e.flow.length) || np);
    const andBelow = hasPrev ? '，以下為最近一次調整' : '';
    if (e.fetched === false)
      tips.push('⚠ 本次未能取得新資料（投信網站異常）'
                + (hasPrev ? '，以下為先前結果' : ''));
    else if (e.flow_to && e.data_date && e.flow_to !== e.data_date)
      // 最新 PCF 沒有調整，畫面保留最近一次真的換檔的內容，日期要講明白
      tips.push('⏳ 最新 PCF（' + e.data_date + '）持股無異動' + andBelow);
    else if (e.advanced === false && e.reason === 'not_updated')
      tips.push('⏳ ' + (e.data_date || '') + ' 之後尚未有新的 PCF' + andBelow);
    // 全池同步等比例增減＝申購贖回造成的規模變動，不是經理人換股，一定要講明
    if (e.scale_pct != null)
      tips.push('⚠ 本期幾乎所有持股同步變動 ' + (e.scale_pct > 0 ? '+' : '') + e.scale_pct +
                '%，屬基金規模增減（申購／贖回），非經理人選股');
    // 混合型 ETF（00997A 51 檔裡只有 4 檔台股）的金額只涵蓋台股那幾檔，
    // 不標的話會被當成整檔基金的動作。np 與 tips 都在上面才宣告，
    // 這段一定要放在它們之後——const 有 TDZ，寫前面是 ReferenceError 整頁掛掉。
    if (np && (e.changed || 0) > 0)
      tips.push('※ 上方金額僅計台股部分，海外持股見下方藍色清單');
    document.getElementById('flowTip').textContent = tips.join('　');
    // 一定要在所有 early return 之前畫。no_basis 與「rows 空」那兩條路徑都會
    // 提前 return，寫在後面的話，全海外持股那幾檔反而永遠看不到清單。
    document.getElementById('flowForeign').innerHTML = np ? _npList(npRows) : '';

    // 說明框跟著下面實際畫出來的東西走。什麼都沒有還留著「面積＝金額」，
    // 等於在解釋一張不存在的圖；全海外那幾檔連面積都沒有，只有股數。
    // 和 flowForeign 一樣，必須寫在所有 early return 之前。
    const hasTree = (e.flow || []).length > 0;
    const noteEl  = document.getElementById('flowNote');
    noteEl.hidden = !(hasTree || np);
    noteEl.innerHTML = hasTree
      ? '⚠ 金額為<b>兩份公開 PCF 快照相減的推估值</b>，不等同基金實際成交；'
        + '除權息、股票分割、成分股調整都可能造成假訊號。'
        + '面積＝金額，<b>紅加碼、綠減碼</b>（台股慣例）。'
      : '⚠ 增減股數為<b>兩份公開 PCF 快照相減的推估值</b>，不等同基金實際成交；'
        + '除權息、股票分割、成分股調整都可能造成假訊號。';

    if (e.reason === 'no_basis') {
      _tmEmpty(box, '這檔還沒有前一份持股可比對<br>' +
        '（' + e.issuer + '投信官網沒有歷史查詢，要等下一份 PCF 公告）');
      return;
    }
    const rows = e.flow || [];
    if (!rows.length) {
      // 全海外持股的 ETF（00989A、00402A…）換股時 rows 會是空的——不是沒動，
      // 是查不到台股收盤價算不出金額。這兩種要分開講，否則畫面會自相矛盾：
      // 上面提示「另有 N 檔海外持股有異動」，下面卻寫「持股與前一份相同」。
      if (np) {
        _tmEmpty(box, '這次異動的 ' + np + ' 檔都是海外持股，無台股報價換算不出金額<br>'
          + '明細見下方清單（PCF 資料日 ' + (e.data_date || '-') + '）', 'sea');
      } else {
        _tmEmpty(box, e.name + ' 目前沒有可顯示的調整紀錄<br>'
          + '（最新 PCF 資料日 ' + (e.data_date || '-') + '，持股與前一份相同）');
      }
      return;
    }

    // 一定要在量尺寸之前還原高度。還掛著 tm-slim 的話 height:auto，
    // clientHeight 量到的是上一次空狀態的高度，treemap 會被畫扁。
    box.classList.remove('tm-slim');
    const W = box.clientWidth, H = box.clientHeight;
    const buys  = _trim(rows.filter(s => s.amount > 0), 14);
    const sells = _trim(rows.filter(s => s.amount < 0).map(s => Object.assign({}, s, { amount: -s.amount })), 12);
    const bSum = buys.reduce((s, x) => s + x.amount, 0);
    const sSum = sells.reduce((s, x) => s + x.amount, 0);
    const tot  = bSum + sSum;
    if (!tot) { _tmEmpty(box, '今日無金額異動'); return; }

    let sellW = Math.round(W * sSum / tot);
    sellW = Math.max(0, Math.min(W, sellW));
    const cells = []
      .concat(squarify(sells.map(s => ({ d: s, value: s.amount })), 0, 0, sellW, H).map(c => (c.side = 'sell', c)))
      .concat(squarify(buys .map(s => ({ d: s, value: s.amount })), sellW, 0, W - sellW, H).map(c => (c.side = 'buy', c)));

    _flowCells = cells.map(c => c.d);          // 點擊時用索引查回原始資料
    box.innerHTML = cells.map((c, idx) => {
      const s = c.d, big = Math.min(c.w, c.h);
      // 台股慣例：紅=加碼(正)、綠=減碼(負)。與 App 其他頁的 --up/--dn、retClr 一致，
      // 不要改成歐美的綠漲紅跌，同一個 App 用兩套相反的顏色語言會讓人讀反。
      const bg = c.side === 'buy'
        ? 'rgba(255,63,94,'  + (0.30 + Math.min(0.55, c.w * c.h / (W * H) * 3)).toFixed(2) + ')'
        : 'rgba(0,200,122,' + (0.30 + Math.min(0.55, c.w * c.h / (W * H) * 3)).toFixed(2) + ')';
      const fs   = Math.max(11, Math.min(19, big / 4.0));   // 手機上 9px 太小，下限拉到 11
      const show = c.w > 42 && c.h > 26;
      const sub  = c.w > 58 && c.h > 46;
      return '<div class="tm-cell" style="left:' + c.x.toFixed(1) + 'px;top:' + c.y.toFixed(1) +
        'px;width:' + c.w.toFixed(1) + 'px;height:' + c.h.toFixed(1) + 'px;background:' + bg + '"' +
        ' onclick="flowTap(' + idx + ')">' +
        (show ? '<div class="tm-name" style="font-size:' + fs.toFixed(0) + 'px">' + s.name + '</div>' : '') +
        (sub  ? '<div class="tm-amt"  style="font-size:' + (fs * .78).toFixed(0) + 'px">' + _oku(s.amount) + '</div>' : '') +
        (sub && s.delta_shares ? '<div class="tm-etf" style="font-size:' + (fs * .66).toFixed(0) + 'px">' +
          (s.delta_shares > 0 ? '+' : '') + Math.round(s.delta_shares / 1000) + '張</div>' : '') +
        '</div>';
    }).join('');
  };

  if (_flowData) draw(); else fetchFlow().then(draw);
}

function flowTap(idx) {
  const s = _flowCells[idx];
  const tip = document.getElementById('flowTip');
  if (!s || !tip) return;
  if (s._agg) { tip.textContent = s.name + '　合計 ' + _oku(s.amount); return; }
  const dir = s.amount > 0 ? '加碼' : '減碼';
  tip.textContent = s.code + ' ' + s.name + '　' + dir + ' ' + _oku(s.amount) +
    '　' + (s.delta_shares > 0 ? '+' : '') + (s.delta_shares || 0).toLocaleString() + ' 股';
}

window.addEventListener('resize', () => {
  if (typeof Category !== "undefined" && Category.isFlowVisible()) renderFlow();
});

