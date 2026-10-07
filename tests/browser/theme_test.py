"""Phase 5 CP7：Dark／Light 主題與 visual tokens（PHASE5_PLAN §7.1、§7.2；TH-1～TH-7）。

執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
共用 header 會把系統主題固定為 dark；本檔用 CDP Emulation.setEmulatedMedia 切換 dark／light 驗證。
"""
import sys, json
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

THEME_KEY = 'etfRadar.theme'
# CP7 fix：rendered contrast 掃描——文字色（含祖先 opacity）疊在「由 html 往下逐層混色」後的實際底色上計算對比；
# 正文 ≥ 4.5、大字（≥24px，或 ≥18.66px 粗體）≥ 3。純裝飾符號（emoji、箭頭、›）略過。
SCAN_JS = r'''window.__scan = function (rootSel, limit) {
  const P = c => { const m = String(c).match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?/); return m ? [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]] : null; };
  const over = (top, under) => { const a = top[3]; return [top[0] * a + under[0] * (1 - a), top[1] * a + under[1] * (1 - a), top[2] * a + under[2] * (1 - a), 1]; };
  const lum = v => { const f = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }; return 0.2126 * f(v[0]) + 0.7152 * f(v[1]) + 0.0722 * f(v[2]); };
  const cr = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const EMOJI = /^[\s\p{Extended_Pictographic}←-⇿⌀-⏿■-◿☀-➿›‹··|｜\-–—\/／,，.。:：()（）%+]*$/u;
  const out = []; const root = document.querySelector(rootSel); if (!root) return [{err: 'no root ' + rootSel}];
  const els = [root, ...root.querySelectorAll('*')];
  for (const el of els) {
    if (!el.offsetParent && getComputedStyle(el).position !== 'fixed') continue;
    if (el.closest('[aria-hidden="true"],[hidden],template,svg')) continue;
    if (el.disabled || (el.closest('button') && el.closest('button').disabled)) continue;
    const txt = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (!txt || EMOJI.test(txt)) continue;
    const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden') continue;
    // 背景：由 html 往下逐層混色
    const chain = []; let p = el; while (p) { chain.unshift(p); p = p.parentElement; }
    let bg = [255, 255, 255, 1], op = 1, img = false;
    for (const a of chain) {
      const s = getComputedStyle(a);
      const c = P(s.backgroundColor); if (c && c[3] > 0) bg = over(c, bg);
      if (s.backgroundImage && s.backgroundImage !== 'none' && !/mask/.test(s.backgroundImage)) img = true;
      op *= parseFloat(s.opacity);
    }
    const fgc = P(cs.color); if (!fgc) continue;
    const fg = over([fgc[0], fgc[1], fgc[2], fgc[3] * op], bg);
    const fs = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700;
    const need = (fs >= 24 || (fs >= 18.66 && bold)) ? 3 : 4.5;
    const v = cr(fg, bg);
    if (v < need) out.push({t: txt.slice(0, 18), cls: (el.className && el.className.baseVal === undefined ? el.className : el.tagName) + '', fs, cr: +v.toFixed(2), need, img});
    if (limit && out.length >= limit) break;
  }
  return out;
};
true;
'''
def media(v): cdp('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': v}]})
def theme(): return ev("document.documentElement.getAttribute('data-theme')")
def reload_page():
    n = load_page(); ev("clearInterval(_pollTimer); true"); return n

COLOR_JS = r"""window.__rgb = function (c) { const m = String(c).match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)/); return m ? [+m[1], +m[2], +m[3]] : null; };
window.__fam = function (c) { const v = __rgb(c); if (!v) return 'none'; const [r, g, b] = v;
  if (r > g + 60 && r > b + 30) return 'red'; if (g > r + 50 && g > b - 10) return 'green'; return 'neutral'; };
window.__lum = function (v) { return 0.2126 * f(v[0]) + 0.7152 * f(v[1]) + 0.0722 * f(v[2]); function f(c) { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); } };
window.__cr = function (a, b) { const x = __lum(__rgb(a)), y = __lum(__rgb(b)); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
window.__tok = function (n) { const d = document.createElement('span'); d.style.color = 'var(' + n + ')'; document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; };
true"""

# ── TH-1 初始主題：無儲存值時依系統；未手動時系統改變會跟著變
ev("localStorage.removeItem('%s'); true" % THEME_KEY)
media('light'); reload_page()
check('TH-1 無儲存值＋系統 light → data-theme=light、按鈕 🌙／「切換為深色模式」', theme() == 'light' and ev("document.getElementById('themeBtn').textContent") == '🌙'
      and ev("document.getElementById('themeBtn').getAttribute('aria-label')") == '切換為深色模式', theme())
check('TH-1 light 下 body 背景＝淺色 token', ev("getComputedStyle(document.body).backgroundColor") == 'rgb(246, 248, 250)', ev("getComputedStyle(document.body).backgroundColor"))
media('dark'); wait_ms(300)
check('TH-1 未手動選擇時系統改為 dark → 跟著變 dark', theme() == 'dark', theme())
media('light'); wait_ms(300)
check('TH-1 系統再改回 light → 跟著變 light', theme() == 'light', theme())
media('dark'); reload_page()
check('TH-1 無儲存值＋系統 dark → data-theme=dark、按鈕 ☀', theme() == 'dark' and ev("document.getElementById('themeBtn').textContent") == '☀', theme())
hdr_order = ev("[...document.querySelectorAll('.hdr-actions > *')].map(x=>x.id)")
check('TH-1 Header 按鈕群：YouTube、主題、↻（YouTube 位置不變），各 ≥ 44×44', hdr_order == ['hdrYt', 'themeBtn', 'refreshBtn']
      and ev("[...document.querySelectorAll('.hdr-actions > *')].every(b=>{const r=b.getBoundingClientRect(); return r.width>=44 && r.height>=44})") is True, hdr_order)

# ── TH-2 切換與保存；手動後系統改變不覆寫
ev("document.getElementById('themeBtn').click(); true"); wait_ms(150)
check('TH-2 按主題鈕 → light、localStorage 寫入 light、aria-pressed=true', theme() == 'light' and ev("localStorage.getItem('%s')" % THEME_KEY) == 'light'
      and ev("document.getElementById('themeBtn').getAttribute('aria-pressed')") == 'true', theme())
media('dark'); wait_ms(300)
check('TH-2 手動選擇後，系統主題改變不覆寫（仍 light）', theme() == 'light', theme())
reload_page()
check('TH-2 重新整理後維持 light（系統為 dark）', theme() == 'light', theme())
check('TH-2 meta theme-color 跟著主題', ev("document.querySelector('meta[name=theme-color]').content") == '#f6f8fa')
h0 = ev("history.length"); s0 = ev("JSON.stringify(Router.state())")
ev("document.getElementById('themeBtn').click(); true"); wait_ms(150)
check('TH-2 再按 → dark、寫入 dark；切換不寫 history、不改 Router', theme() == 'dark' and ev("localStorage.getItem('%s')" % THEME_KEY) == 'dark'
      and ev("history.length") == h0 and ev("JSON.stringify(Router.state())") == s0)
ev("localStorage.removeItem('%s'); true" % THEME_KEY)

# ── TH-3 storage 失敗：切換仍生效、無例外
r = cdp('Page.addScriptToEvaluateOnNewDocument', {'source': "(function(){ const t=()=>{ throw new Error('blocked'); }; Storage.prototype.getItem=t; Storage.prototype.setItem=t; Storage.prototype.removeItem=t; })();"})
sid = r.get('result', {}).get('identifier')
exc0 = len([e for e in events if e.get('method') == 'Runtime.exceptionThrown'])
media('dark'); cdp('Page.navigate', {'url': BASE}); time.sleep(2.5)
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if((typeof ETFS!=='undefined'&&ETFS.length>0)||Date.now()-t>20000){clearInterval(i);r(1)}},200)})", True)
t_before = theme()
ev("document.getElementById('themeBtn').click(); true"); wait_ms(150)
exc_th3 = [e for e in events[exc0:] if e.get('method') == 'Runtime.exceptionThrown' and 'blocked' in json.dumps(e)]
check('TH-3 localStorage 丟例外：初始依系統（dark）、切換仍生效（light）、主題程式無未捕捉例外', t_before == 'dark' and theme() == 'light' and not exc_th3, (t_before, theme(), len(exc_th3)))
if sid: cdp('Page.removeScriptToEvaluateOnNewDocument', {'identifier': sid})
# 只保留與主題無關的例外比對基準（WatchStore 自己的 storage 失敗處理不在本項範圍）
events[:] = [e for e in events if not (e.get('method') == 'Runtime.exceptionThrown' and 'blocked' in json.dumps(e))]

# ── TH-8（CP7 fix）：首次可見 paint 時主題鈕已與實際主題一致——暫停底部第一支 script（js/state.js），
#    parser 停在那裡、DOMContentLoaded 尚未觸發，Header 已畫出；此時檢查按鈕 icon／accessible label／aria-pressed
for mode, icon, label, pressed in (('light', '🌙', '切換為深色模式', 'true'), ('dark', '☀', '切換為淺色模式', 'false')):
    ev("localStorage.removeItem('%s'); true" % THEME_KEY)
    media(mode)
    cdp('Network.enable'); cdp('Network.setCacheDisabled', {'cacheDisabled': True})   # 快取命中的 script 不經 Fetch 攔截
    cdp('Fetch.enable', {'patterns': [{'urlPattern': '*js/state.js*', 'requestStage': 'Request'}]})
    cdp('Page.navigate', {'url': BASE}); time.sleep(1.5)
    fp = ev("""(()=>{const b=document.getElementById('themeBtn'); return {ready:document.readyState, theme:document.documentElement.getAttribute('data-theme'),
      icon:b&&b.textContent, label:b&&b.getAttribute('aria-label'), pressed:b&&b.getAttribute('aria-pressed'), vis:!!(b&&b.getBoundingClientRect().width),
      stateJs: typeof ETFS !== 'undefined'}})()""")
    cdp('Fetch.disable'); time.sleep(1.5)
    check('TH-8 [%s] 底部 script 暫停（readyState=loading、state.js 未執行）時主題鈕已同步：%s、「%s」、aria-pressed=%s' % (mode, icon, label, pressed),
          isinstance(fp, dict) and fp['ready'] == 'loading' and not fp['stateJs'] and fp['vis'] and fp['theme'] == mode and fp['icon'] == icon and fp['label'] == label and fp['pressed'] == pressed, fp)
media('dark'); reload_page()

# ── TH-4／TH-5／TH-6／TH-7：兩種主題逐一驗
for mode in ('dark', 'light'):
    ev("localStorage.removeItem('%s'); true" % THEME_KEY)
    media(mode); reload_page(); ev(COLOR_JS)
    check('TH [%s] 主題套用' % mode, theme() == mode, theme())
    # TH-4 漲紅跌綠：miniBars、排行近一年報酬、我的 ETF 今日漲跌
    mb = ev("(()=>{const d=document.createElement('div'); d.innerHTML=miniBars([1.5,0,-2,null]); document.body.appendChild(d); const r=[...d.querySelectorAll('.mb')].map(m=>__fam(getComputedStyle(m.querySelector('.mb-bar')).backgroundColor)); d.remove(); return r})()")
    check('TH-4 [%s] miniBars：漲紅、0 中性、跌綠、缺值非紅綠' % mode, mb == ['red', 'neutral', 'green', 'neutral'] or (mb[:3] == ['red', 'neutral', 'green'] and mb[3] in ('neutral', 'none')), mb)
    ev("switchPage('rank'); true"); wait_ms(300)
    rk = ev("""(()=>{const out={up:[],dn:[],zero:[]}; _rankSorted.forEach(e=>{const row=document.querySelector('#rankRows .rank-row[data-code="'+e.code+'"] .rank-num'); if(!row||e.ret1y==null) return;
      const f=__fam(getComputedStyle(row).color); (e.ret1y>0?out.up:e.ret1y<0?out.dn:out.zero).push(f)}); return {up:[...new Set(out.up)], dn:[...new Set(out.dn)], zero:[...new Set(out.zero)]}})()""")
    check('TH-4 [%s] 排行近一年報酬：正值全紅、負值全綠（反向守衛）' % mode, rk['up'] in (['red'], []) and rk['dn'] in (['green'], []) and (rk['up'] or rk['dn']), rk)
    ev("localStorage.setItem('etfRadar.watch.v1', JSON.stringify({v:1,codes:[ETFS[0].code]})); WatchStore._reload(); Watch.render(); Router.toBase({base:'watch'}); true"); wait_ms(300)
    def chg(pt, pct):
        ev("ETFS[0].change_pt=%s; ETFS[0].change_pct=%s; Watch.refresh(); true" % (json.dumps(pt), json.dumps(pct)))
        return ev("[...document.querySelectorAll('#watchList .wc .wc-chg')].map(x=>__fam(getComputedStyle(x).color))")
    up, dn, zero, na = chg(0.5, 1.2), chg(-0.5, -1.2), chg(0, 0), chg(None, None)
    check('TH-4 [%s] 我的 ETF 今日漲跌：漲紅、跌綠、0 與缺值中性（上漲不是綠）' % mode, up == ['red', 'red'] and dn == ['green', 'green'] and zero == ['neutral', 'neutral'] and na == ['neutral', 'neutral'], (up, dn, zero, na))
    # TH-5 Active Flow
    ev("switchPage('tools'); true"); wait_ms(200)
    ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowData||Date.now()-t>15000){clearInterval(i);r(1)}},100)})", True)
    fc = ev("Object.keys(_flowData.etfs).find(k=>(_flowData.etfs[k].flow||[]).some(x=>x.amount>0) && (_flowData.etfs[k].flow||[]).some(x=>x.amount<0))")
    ev("openFlow(%s); true" % json.dumps(fc)); wait_ms(500)
    # CP7 fix：逐格以「原始資料 amount 的正負」核對實際 rendered 顏色（amount > 0 → 紅／加碼、< 0 → 綠／減碼）。
    # _flowCells[i] 是第 i 格的資料；減碼格的 amount 在畫圖時取了絕對值，所以用代碼回查原始 flow 的正負。
    tm = ev("""(()=>{const e=_flowData.etfs[_flowSel]; const orig={}; (e.flow||[]).forEach(x=>{orig[x.code+'|'+x.name]=x.amount});
      const cells=[...document.querySelectorAll('#treemap .tm-cell')]; const rows=cells.map((c,i)=>{const d=_flowCells[i]||{}; const a=orig[d.code+'|'+d.name];
        return {code:d.code, agg:!!d._agg, amount:a, fam:__fam(getComputedStyle(c).backgroundColor)}});
      const checked=rows.filter(x=>!x.agg && typeof x.amount==='number' && x.amount!==0);
      const bad=checked.filter(x=>(x.amount>0 && x.fam!=='red') || (x.amount<0 && x.fam!=='green'));
      return {n:cells.length, checked:checked.length, pos:checked.filter(x=>x.amount>0).length, neg:checked.filter(x=>x.amount<0).length, bad:bad.slice(0,5),
              aggOk: rows.filter(x=>x.agg).every(x=>x.fam==='red'||x.fam==='green'),
              buy:__fam(getComputedStyle(document.getElementById('flowBuy')).color), sell:__fam(getComputedStyle(document.getElementById('flowSell')).color)}})()""")
    check('TH-5 [%s] treemap 逐格：原始 amount > 0 的格為紅、< 0 的格為綠（%s，%d 格中核對 %d 格：正 %d／負 %d）' % (mode, fc, tm['n'], tm['checked'], tm['pos'], tm['neg']),
          tm['checked'] >= 4 and tm['pos'] > 0 and tm['neg'] > 0 and not tm['bad'] and tm['aggOk'], tm)
    check('TH-5 [%s] 加碼金額紅、減碼金額綠' % mode, tm['buy'] == 'red' and tm['sell'] == 'green', tm)
    np = ev("""(()=>{const d=document.createElement('div'); d.innerHTML=_npList([{code:'AAA US',name:'x',delta_shares:100},{code:'BBB US',name:'y',delta_shares:-50},{code:'CCC',name:'z',delta_shares:null}]);
      document.getElementById('flowForeign').appendChild(d); const r=[...d.querySelectorAll('.np-d')].map(x=>__fam(getComputedStyle(x).color)); d.remove(); return r})()""")
    check('TH-5 [%s] 海外清單：正值紅、負值綠、缺值中性' % mode, np == ['red', 'green', 'neutral'], np)
    ev("history.back(); true"); wait_ms(400)
    # TH-6 可讀性（CP7 fix）：以使用者實際看到的 rendered 組件為準——淡色底混色、透明度、文字 opacity 都算進去
    ev(SCAN_JS)
    scr = {}
    ev("Router.toBase({base:'home'}); window.scrollTo(0,0); true"); wait_ms(300); scr['首頁'] = ev("__scan('#page-today')")
    ev("switchPage('rank'); true"); wait_ms(400); scr['排行'] = ev("__scan('#page-rank')")
    ev("switchPage('tools'); true"); wait_ms(250); scr['工具'] = ev("__scan('#page-tools')")
    ev("openFlow(%s); true" % json.dumps(fc)); wait_ms(500); scr['持股異動 %s' % fc] = ev("__scan('#flowLayer')")
    npc = ev("Object.keys(_flowData.etfs).find(k=>(_flowData.etfs[k].no_price||[]).length>0)")
    if npc:
        ev("flowSelect(%s); true" % json.dumps(npc)); wait_ms(400); scr['持股異動海外 %s' % npc] = ev("__scan('#flowLayer')")
    for c in ev("Object.keys(_flowData.etfs)"):
        ev("flowSelect(%s); true" % json.dumps(c)); wait_ms(60)
        bad = ev("__scan('#treemap')")
        if bad: scr['treemap %s' % c] = bad
    ev("history.back(); true"); wait_ms(400)
    ev("Router.toBase({base:'cat'}); true"); wait_ms(300); scr['分類'] = ev("__scan('#page-cat')")
    ev("Router.openFolder('active'); true"); wait_ms(700); scr['分類清單'] = ev("__scan('#page-cat')")
    ev("Router.setFolderView('flow'); true"); wait_ms(500); scr['分類持股異動'] = ev("__scan('#page-cat')")
    ev("localStorage.setItem('etfRadar.watch.v1', JSON.stringify({v:1,codes:['0050','0056',%s]})); WatchStore._reload(); Watch.render(); Router.toBase({base:'watch'}); true" % json.dumps(fc)); wait_ms(400)
    scr['我的 ETF'] = ev("__scan('#page-watch')")
    for tab in ('overview', 'dividend', 'perf', 'holdings'):
        ev("openDetail(%s); detailTab('%s'); true" % (json.dumps(fc), tab)); wait_ms(350); scr['Detail %s' % tab] = ev("__scan('#gsPanel')")
    ev("closeDetail(); true"); wait_ms(300)
    scr['Header'] = ev("__scan('.app-hdr')"); scr['B6'] = ev("__scan('.disclaimer')"); scr['導覽列'] = ev("__scan('.bottom-nav')")
    worst = {k: v for k, v in scr.items() if v}
    print('   TH-6 [%s] rendered contrast fails:' % mode, json.dumps(worst, ensure_ascii=False)[:600])
    check('TH-6 [%s] rendered 對比：%d 個畫面（含全部 %d 檔 treemap）文字皆達標（正文 ≥ 4.5、大字 ≥ 3）' % (mode, len(scr), ev("Object.keys(_flowData.etfs).length")), not worst, worst)
    b6 = ev("""(()=>{const d=document.querySelector('.disclaimer'); const cs=getComputedStyle(d); return {fs:parseFloat(cs.fontSize), cr:__cr(cs.color, getComputedStyle(document.body).backgroundColor)}})()""")
    check('TH-6 [%s] B6 警示條文字對比 ≥ 4.5（%.2f）' % (mode, b6['cr']), b6['cr'] >= 4.5, b6)
    # TH-7 資訊層級
    ev("switchPage('cat'); true"); wait_ms(300)
    band = ev("getComputedStyle(document.querySelector('.cat-band')).boxShadow")
    check('TH-7 [%s] Phase 3 文件夾堆疊陰影存在' % mode, band and band != 'none', band)
    lay = ev("""(()=>{const d=getComputedStyle(document.querySelector('.disclaimer')); const t=getComputedStyle(document.querySelector('.topbar-title'));
      return {discFs:parseFloat(d.fontSize), titleFs:parseFloat(t.fontSize), discBg:d.backgroundColor}})()""")
    check('TH-7 [%s] B6 警示條為低調提示：字級不大於主標、底色為淡色（透明度 < 0.2）' % mode, lay['discFs'] <= lay['titleFs'] and ('rgba' in lay['discBg'] and float(lay['discBg'].split(',')[-1].strip(' )')) < 0.2), lay)
    ov = ev("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check('TH [%s] 無水平溢出' % mode, ov <= 0, ov)
    ev("Router.toBase({base:'home'}); true"); wait_ms(200)

# ── TH-9（CP7 final fix）：Flow treemap 開著時直接切換主題（不 reload、不 resize），雙向：
#    字色／底襯依新主題重算、rendered 對比達標；ETF、搜尋 query、選取、捲動、面積／透明度、Router／history 都不變
ev("localStorage.removeItem('%s'); true" % THEME_KEY)
media('dark'); reload_page(); ev(COLOR_JS); ev(SCAN_JS)
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}); wait_ms(300)
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowData||Date.now()-t>15000){clearInterval(i);r(1)}},100)})", True)
FLOW9 = ev("_flowData.etfs['00981A'] ? '00981A' : Object.keys(_flowData.etfs).find(k=>(_flowData.etfs[k].flow||[]).length>4)")
ev("switchPage('tools'); true"); wait_ms(250)
ev("document.getElementById('toolFlow').click(); true"); wait_ms(500)
ev("flowSelect(%s); true" % json.dumps(FLOW9)); wait_ms(400)
ev("flowQOpen(); {const i=document.getElementById('flowQ'); i.value='009'; i.dispatchEvent(new Event('input'));} true"); wait_ms(200)
ev("document.getElementById('flowChips').scrollLeft = 120; document.getElementById('flowLayer').scrollTop = 60; true"); wait_ms(200)
STATE9 = """(()=>{const cells=[...document.querySelectorAll('#treemap .tm-cell')]; const L=document.getElementById('flowLayer');
  return {theme:document.documentElement.getAttribute('data-theme'), sel:_flowSel, q:document.getElementById('flowQ').value, qOpen:!document.getElementById('flowQBox').hidden,
    items:[...document.querySelectorAll('#flowQList .flow-q-item')].map(x=>x.dataset.code).join(),
    active:(document.querySelector('#flowChips .flow-chip.active')||{}).dataset.code, chipsLeft:Math.round(document.getElementById('flowChips').scrollLeft), layerTop:Math.round(L.scrollTop), winY:Math.round(scrollY),
    geo:cells.map(c=>[c.style.left,c.style.top,c.style.width,c.style.height,c.dataset.side,c.dataset.a].join('/')).join('|'),
    alpha:cells.map(c=>(getComputedStyle(c).backgroundColor.match(/[\d.]+\)$/)||[''])[0]).join(), n:cells.length,
    ink:cells.map(c=>c.style.color).join(), router:JSON.stringify(Router.state()), hlen:history.length, flowOn:flowLayerVisible()}})()"""
def scan_flow(): return ev("__scan('#treemap')") + ev("__scan('#flowLayer')")
s0 = ev(STATE9); bad0 = scan_flow()
check('TH-9 前置（dark）：%s treemap 對比達標、搜尋開著（query 009）' % FLOW9, not bad0 and s0['qOpen'] and s0['q'] == '009' and s0['n'] > 0, bad0)
seq = []
for step in ('light', 'dark'):
    ev("document.getElementById('themeBtn').click(); true"); wait_ms(250)
    st9 = ev(STATE9); bad = scan_flow()
    seq.append((step, st9['theme'], len(bad)))
    check('TH-9 直接切到 %s（不 reload／resize）：treemap 與 Flow 層 rendered 對比全部達標' % step, st9['theme'] == step and not bad, bad[:6])
    check('TH-9 切到 %s：格子顏色仍為紅（加碼）／綠（減碼）' % step,
          ev("[...document.querySelectorAll('#treemap .tm-cell')].every(c=>['red','green'].includes(__fam(getComputedStyle(c).backgroundColor)))") is True, st9['ink'][:80])
    keep = {k: (st9[k], s0[k]) for k in ('sel', 'q', 'qOpen', 'items', 'active', 'chipsLeft', 'layerTop', 'winY', 'geo', 'alpha', 'n', 'router', 'hlen', 'flowOn') if st9[k] != s0[k]}
    check('TH-9 切到 %s：ETF、搜尋 query 與結果、選取 chip、selector／Flow 層／頁面捲動、格子位置與透明度、Router／history 全部不變' % step, not keep, keep)
print('   TH-9 sequence:', seq)
# 反方向起點：在 light 下畫出 treemap，再直接切到 dark
ev("localStorage.removeItem('%s'); true" % THEME_KEY)
media('light'); reload_page(); ev(COLOR_JS); ev(SCAN_JS)
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowData||Date.now()-t>15000){clearInterval(i);r(1)}},100)})", True)
ev("switchPage('tools'); true"); wait_ms(250); ev("document.getElementById('toolFlow').click(); true"); wait_ms(500)
ev("flowSelect(%s); true" % json.dumps(FLOW9)); wait_ms(400)
l0 = ev(STATE9)
ev("document.getElementById('themeBtn').click(); true"); wait_ms(250)
l1 = ev(STATE9); bad = scan_flow()
check('TH-9 由 light 畫出後直接切到 dark：rendered 對比全部達標，ETF／格子位置與透明度／Router 不變', l1['theme'] == 'dark' and not bad
      and all(l1[k] == l0[k] for k in ('sel', 'geo', 'alpha', 'router', 'hlen')), bad[:6])
# 分類原生持股異動也一樣
ev("history.back(); true"); wait_ms(400)
ev("Router.toBase({base:'cat'}); true"); wait_ms(300); ev("Router.openFolder('active'); true"); wait_ms(700); ev("Router.setFolderView('flow'); true"); wait_ms(500)
for step in ('light', 'dark'):
    ev("document.getElementById('themeBtn').click(); true"); wait_ms(250)
    bad = ev("__scan('#catFlowHost')")
    check('TH-9 分類原生持股異動直接切到 %s：rendered 對比全部達標' % step, theme() == step and not bad, bad[:6])
ev("Router.toBase({base:'home'}); true"); wait_ms(200)
cdp('Emulation.clearDeviceMetricsOverride')

ev("localStorage.removeItem('%s'); localStorage.removeItem('etfRadar.watch.v1'); true" % THEME_KEY)
media('dark')
exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'), (e['params']['exceptionDetails'].get('exception', {}) or {}).get('description', '')[:200])
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
