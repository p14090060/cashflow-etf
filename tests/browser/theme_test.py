"""Phase 5 CP7：Dark／Light 主題與 visual tokens（PHASE5_PLAN §7.1、§7.2；TH-1～TH-7）。

執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
共用 header 會把系統主題固定為 dark；本檔用 CDP Emulation.setEmulatedMedia 切換 dark／light 驗證。
"""
import sys, json
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

THEME_KEY = 'etfRadar.theme'
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
    tm = ev("""(()=>{const fams=[...document.querySelectorAll('#treemap .tm-cell')].map(c=>({f:__fam(getComputedStyle(c).backgroundColor)}));
      return {n:fams.length, red:fams.filter(x=>x.f==='red').length, green:fams.filter(x=>x.f==='green').length,
              buy:__fam(getComputedStyle(document.getElementById('flowBuy')).color), sell:__fam(getComputedStyle(document.getElementById('flowSell')).color)}})()""")
    check('TH-5 [%s] treemap 加碼格紅系、減碼格綠系，且無其他色；加碼金額紅、減碼金額綠（%s）' % (mode, fc),
          tm['n'] > 0 and tm['red'] + tm['green'] == tm['n'] and tm['red'] > 0 and tm['green'] > 0 and tm['buy'] == 'red' and tm['sell'] == 'green', tm)
    np = ev("""(()=>{const d=document.createElement('div'); d.innerHTML=_npList([{code:'AAA US',name:'x',delta_shares:100},{code:'BBB US',name:'y',delta_shares:-50},{code:'CCC',name:'z',delta_shares:null}]);
      document.getElementById('flowForeign').appendChild(d); const r=[...d.querySelectorAll('.np-d')].map(x=>__fam(getComputedStyle(x).color)); d.remove(); return r})()""")
    check('TH-5 [%s] 海外清單：正值紅、負值綠、缺值中性' % mode, np == ['red', 'green', 'neutral'], np)
    ev("history.back(); true"); wait_ms(400)
    # TH-6 可讀性：token 對 --bg／--card 的對比（正文 ≥ 4.5、大字／圖形 ≥ 3）
    pairs = [('--bright', '--bg', 4.5), ('--bright', '--card', 4.5), ('--dim', '--bg', 4.5), ('--dim', '--card', 4.5), ('--dim', '--card2', 4.5),
             ('--up', '--card', 4.5), ('--dn', '--card', 4.5), ('--up', '--bg', 4.5), ('--dn', '--bg', 4.5),
             ('--cheap', '--card', 4.5), ('--fair', '--card', 4.5), ('--hot', '--card', 4.5), ('--warn', '--card', 4.5), ('--bond', '--card', 4.5),
             ('--cheap', '--card2', 4.5), ('--fair', '--card2', 4.5), ('--hot', '--card2', 4.5), ('--warn', '--card2', 4.5),
             ('--link', '--card', 4.5), ('--link', '--bg', 4.5), ('--gold', '--bg', 4.5), ('--brand', '--card', 4.5), ('--violet', '--card', 4.5),
             ('--silver', '--card', 4.5), ('--bronze', '--card', 4.5), ('--fair-dim', '--card', 4.5), ('--on-strong', '--sea', 4.5), ('--fair', '--bg', 4.5)]
    res = ev("%s.map(([a,b,m])=>[a,b,m,+__cr(__tok(a),__tok(b)).toFixed(2)])" % json.dumps(pairs))
    low = [x for x in res if x[3] < x[2]]
    print('   TH-6 [%s] contrast:' % mode, {('%s/%s' % (x[0], x[1])): x[3] for x in res})
    check('TH-6 [%s] 主文字、次要文字、價格狀態、漲跌、連結等 %d 組對比全部達標' % (mode, len(res)), not low, low)
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

ev("localStorage.removeItem('%s'); localStorage.removeItem('etfRadar.watch.v1'); true" % THEME_KEY)
media('dark')
exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'), (e['params']['exceptionDetails'].get('exception', {}) or {}).get('description', '')[:200])
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
