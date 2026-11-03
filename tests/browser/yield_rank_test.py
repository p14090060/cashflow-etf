"""工具頁殖利率排行（YR）：入口、排序、榜外語意、Detail 共用數值、相容、手機與主題。
由 tests/browser/yield_offline_host.py 執行（候選 market 走真 writer 鏈；封外網）。"""
import base64, json, os, sys
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])

OUT = os.environ.get('YIELD_OUT', '.')
ev("clearInterval(_pollTimer); window.__routerManualTimers = true; window.yieldToday = () => '2026-11-04'; renderRank(); true")   # 候選資料固定在 11/04，日後重跑不因 14 天上限變空
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowData||Date.now()-t>8000){clearInterval(i);r(true)}},100)})", True)
cdp('Emulation.setDeviceMetricsOverride', {'width': 460, 'height': 850, 'deviceScaleFactor': 1, 'mobile': True})
def shot(name):
    r = cdp('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(OUT, name), 'wb').write(base64.b64decode(r['result']['data']))
def st(): return ev("JSON.stringify(Router.state())")
def rows(): return ev("[...document.querySelectorAll('#yieldRows .rank-row')].map(r=>r.dataset.code)")
def card(code, sel): return ev("(document.querySelector('#yieldRows .rank-row[data-code=\"%s\"] %s')||{}).textContent" % (code, sel))

ev("switchPage('tools'); true"); wait_ms(200)
check('YR-1 工具四卡順序', ev("[...document.querySelectorAll('#page-tools .tool-card b')].map(e=>e.textContent).join('|')") == '成交量排行|殖利率排行|配息日曆|主動式 ETF 持股異動')
shot('tools-mobile.png')
h0 = ev("history.length")
ev("document.getElementById('toolYield').click(); true"); wait_ms(300)
check('YR-2 直接進殖利率頁、無雙榜頁籤', ev("document.getElementById('page-yield').classList.contains('active') && !document.getElementById('page-rank').classList.contains('active')") and ev("document.querySelector('#page-yield .rank-title').textContent") == '殖利率排行' and ev("document.querySelectorAll('#page-yield [role=tab], #page-yield .sample-tabs').length") == 0)
check('YR-2b Router 是工具子頁', json.loads(st())['stack'][0].get('id') == 'yield')
shot('yield-mobile.png')

R = rows()
expect = ev("""ETFS.filter(e=>e.yield_basis&&e.price>0).sort((a,b)=>b.yield_basis.rate-a.yield_basis.rate||(a.code<b.code?-1:1)).slice(0,100).map(e=>e.code)""")
check('YR-3 最多 100 名，依未四捨五入比率降序（同值代號穩定）', 0 < len(R) <= 100 and R == expect, len(R))
check('YR-3b 不是先篩成交量前 100', ev("(()=>{const v=new Set(_rankSorted.map(e=>e.code));return _yieldSorted.some(e=>!v.has(e.code))||_yieldAll.length<=100})()"))
check('YR-4 新上市：~＋年化估算', card('00406A', '.yr-rate').startswith('~') and card('00406A', '.yr-label') == '年化估算', card('00406A', '.yr-rate'))
check('YR-5 成熟：數字＋近12月', not card('00927', '.yr-rate').startswith('~') and card('00927', '.yr-label') == '近12月')
check('YR-6 主卡不露期數／算式', not ev("/\\d+\\s*期|÷|除息/.test(document.getElementById('yieldRows').innerText)"))
check('YR-7 卡片欄位：名次／代號／名稱／價格／狀態／配息方式', all(ev("!!document.querySelector('#yieldRows .rank-row %s')" % s) for s in ('.rank-no', '.rank-code', '.rank-name', '.rank-price', '.rank-sig', '.yr-freq', '.yr-vol')))
vol = ev("""(()=>{const m=new Map(_rankSorted.map((e,i)=>[e.code,i+1]));const st=rankVolState(ETFS,_statusArgs);
  return [...document.querySelectorAll('#yieldRows .rank-row')].map(r=>{const c=r.dataset.code,t=r.querySelector('.yr-vol').textContent,e=ETFS.find(x=>x.code===c);
    const want=!rankVolReady(st,e)?'待確認':m.has(c)?((!st.valid||st.pending>0)?'暫':'')+m.get(c):((!st.valid||st.pending>0)?'待確認':'榜外');return t===want}).every(Boolean)})()""")
check('YR-8 成交量名次與成交量榜一致，榜外不造第 101', vol)
check('YR-8b 不產生第 101 名', ev("Math.max(...[...document.querySelectorAll('#yieldRows .rank-row')].map(r=>+r.dataset.rank))") <= 100)

# 互動零請求
ev("window.__res0 = performance.getEntriesByType('resource').length; true")
txt = card('00406A', '.yr-rate')
ev("window.scrollTo(0, 420); true"); wait_ms(200)
sy = ev("Math.round(scrollY)")
ev("document.querySelector('#yieldRows .rank-row[data-code=\"00406A\"] .rank-hit').click(); true"); wait_ms(500)
s1 = json.loads(st())
check('YR-9 點卡片直接開既有 Detail', ev("!!_detailOpen") and s1['stack'][-1]['t'] == 'detail' and s1['stack'][-1]['code'] == '00406A' and len(s1['stack']) == 2, s1)
ov = ev("document.querySelector('#gsPanelBody [data-slot=\"overview\"]').innerText")
div = ev("document.querySelector('#gsPanelBody [data-slot=\"dividend\"]').innerText")
check('YR-10 Detail 總覽與配息的新欄位與榜上同值、標籤一致', '年化配息率（年化估算）' in ov and txt in ov and '年化配息率（年化估算）' in div and txt in div, (txt, ov[-120:]))
e878 = ev("(()=>{const e=ETFS.find(x=>x.code==='00878');return {old:_dtYld(e),rows:_dtYieldRows(e),now:yieldView(e).text}})()")
check('YR-10b 舊口徑保留舊值且改名區隔，新值另列（F3）', '殖利率（原算法）' in e878['rows'] and '年化配息率（近12月）' in e878['rows'] and e878['old'] in e878['rows'] and e878['now'] in e878['rows'] and e878['old'] != e878['now'], e878)
check('YR-11 計算依據：期數／每期金額／日期／來源／算式', all(k in div for k in ('配息率計算依據', '4 期', '除息', '發放日', 'TWSE', '÷', '年化估算')), div[-300:])
ev("document.querySelector('#gsPanelBody [data-tab=\"dividend\"], #gsPanelBody .dt-tab:nth-child(2)').click(); true"); wait_ms(300); shot('detail-dividend.png')
check('YR-11b 計算依據用「來源日」並說明 14 天上限', '來源日' in div and '14 天' in div, div[-200:])
check('YR-12 估算不升格 yld_verified', ev("ETFS.find(e=>e.code==='00406A').yld_verified") is not True)
ev("history.back(); true"); wait_ms(500)
s2 = json.loads(st())
check('YR-13 返回排行：單層、捲動位置保留', len(s2['stack']) == 1 and s2['stack'][0].get('id') == 'yield' and abs(ev("Math.round(scrollY)") - sy) <= 2, (s2, sy, ev("Math.round(scrollY)")))
ev("window.scrollTo(0,0);document.getElementById('yieldFindBtn').click();const f=document.getElementById('yieldFind');f.value='00927';f.dispatchEvent(new Event('input'));true"); wait_ms(700)
check('YR-14 搜尋命中：定位名次、不過濾', '第 ' in ev("document.getElementById('yieldFindMsg').textContent") and len(rows()) == len(R) and ev("!!document.querySelector('#yieldRows .rank-row.found')"))
nc = ev("(ETFS.find(e=>!e.yield_basis)||{}).code")
ev("(()=>{const f=document.getElementById('yieldFind');f.value=%s;f.dispatchEvent(new Event('input'));})();true" % json.dumps(nc)); wait_ms(300)
check('YR-15 未可比較：只回報狀態、不插列', '沒有可比較' in ev("document.getElementById('yieldFindMsg').textContent") and len(rows()) == len(R) and nc not in rows())
ev("clearYieldFind(); true")
check('YR-16 點擊／搜尋／Detail 全程 0 新請求', ev("performance.getEntriesByType('resource').length") == ev("window.__res0"))

# 其他榜、首頁不受影響；同一批資料去掉欄位結果相同
snap = "JSON.stringify({rank:[...document.querySelectorAll('#rankRows .rank-row')].map(r=>r.innerText),home:document.getElementById('page-today').innerText})"
a = ev(snap)
ev("window.__ETFS=ETFS; window.__CAL=CALENDAR; renderAll(JSON.parse(JSON.stringify(ETFS)).map(e=>{delete e.yield_basis;return e}), CALENDAR, _lastOk, undefined, undefined, undefined, {}); true"); wait_ms(300)
check('YR-17 缺欄位相容：空狀態、不崩潰', ev("document.querySelectorAll('#yieldRows .rank-row').length") == 0 and '沒有可比較' in ev("document.getElementById('yieldState').textContent"))
check('YR-18 成交量榜不受 yield_basis 影響', json.loads(ev(snap))['rank'] == json.loads(a)['rank'])
ev("""renderAll(JSON.parse(JSON.stringify(window.__ETFS)).map(e=>{if(e.code==='00927')e.yield_basis.rate='x';if(e.code==='00406A')e.yield_basis='bad';return e}), CALENDAR, _lastOk, undefined, undefined, undefined, {}); true"""); wait_ms(300)
check('YR-19 壞欄位：該檔不進榜、其他照常', not {'00927', '00406A'} & set(rows()) and len(rows()) > 90)
ev("renderAll(window.__ETFS, CALENDAR, _lastOk, undefined, undefined, undefined, {}); true"); wait_ms(300)

# F2：前端拒絕未來／畸形／期間不符，與來源日範圍語意
RJ = lambda mut: ev("(()=>{const e=JSON.parse(JSON.stringify(ETFS.find(x=>x.code==='00927')));%s;return yieldView(e)===null})()" % mut)
check('YR-23 正例通過', not RJ('0'))
for name, mut in {'未來 as_of': "e.yield_basis.as_of='2099-01-01';e.yield_basis.window_start='2098-01-02'", '舊年度冒充': "e.yield_basis.window_start='2020-01-01'",
                  '畸形日期': "e.yield_basis.as_of='2026-13-45'", '事件缺欄位': "e.yield_basis.events=[{}]", '事件非物件': "e.yield_basis.events=[1]",
                  '比率不符': "e.yield_basis.rate=999", '價格不符': "e.yield_basis.price=1", '近12月含未來': "e.yield_basis.events[0].future=true",
                  '滿一年標估算': "e.yield_basis.method='annualized_estimate'", '新上市標近12月': "e.yield_basis.listing_date='2026-06-01'",
                  '分子不符': "e.yield_basis.annual_cash='99'", '來源日逾 14 天': "window.yieldToday=()=>'2026-12-30'"}.items():
    check('YR-24 拒絕 ' + name, RJ(mut), name)
    ev("window.yieldToday = () => '2026-11-04'; true")
ev("""(()=>{const a=JSON.parse(JSON.stringify(window.__ETFS));const e=a.find(x=>x.code==='00927');e.yield_basis.as_of='2026-10-28';e.yield_basis.window_start='2025-10-29';
  renderAll(a, CALENDAR, _lastOk, undefined, undefined, undefined, {});})();true"""); wait_ms(300)
st_txt = ev("document.getElementById('yieldState').textContent")
check('YR-25 部分沿用：狀態列列出來源日範圍與舊筆數，不以最新日掩蓋', '2026-10-28～' in st_txt and '1 支沿用舊資料' in st_txt and '14 天' in st_txt, st_txt)
ev("renderAll(window.__ETFS, CALENDAR, _lastOk, undefined, undefined, undefined, {}); true"); wait_ms(300)
off = ev("(_yieldAll[100]||{}).code")
if off:
    ev("(()=>{const f=document.getElementById('yieldFind');f.value=%s;f.dispatchEvent(new Event('input'));})();true" % json.dumps(off)); wait_ms(300)
    check('YR-26 榜外：回報未進前 100、不插列', '未進前 100 名' in ev("document.getElementById('yieldFindMsg').textContent") and off not in rows() and len(rows()) == 100)
    ev("clearYieldFind(); true")

for w in (390, 360):
    cdp('Emulation.setDeviceMetricsOverride', {'width': w, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}); wait_ms(250)
    check('YR-20 %dpx 無水平捲動、卡片內不溢出' % w, ev("document.documentElement.scrollWidth<=document.documentElement.clientWidth && [...document.querySelectorAll('#yieldRows .yr-cols')].every(c=>c.scrollWidth<=c.clientWidth+1)"), ev("document.documentElement.scrollWidth"))
shot('yield-360.png')
ev("(()=>{const b=document.querySelector('[onclick*=\"Theme\"], #themeBtn'); if(b) b.click();})(); true"); wait_ms(300)
t1 = ev("document.documentElement.dataset.theme")
ev("document.documentElement.dataset.theme = 'light'; true"); wait_ms(200); shot('yield-light.png')
check('YR-21 Light 主題文字可見', ev("getComputedStyle(document.querySelector('#yieldRows .yr-rate')).color") != ev("getComputedStyle(document.body).backgroundColor"), t1)
exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('YR-22 全程無未捕捉例外', not exc, str(exc)[:300])
print('\n%d passed, %d failed' % (sum(r[1] for r in results), sum(not r[1] for r in results)))
sys.exit(0 if all(r[1] for r in results) else 1)
