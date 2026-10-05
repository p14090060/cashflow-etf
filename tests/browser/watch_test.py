# watch_test.py — Phase 4「我的 ETF」自選（PHASE4_PLAN Rev.2.1 §10.1）
# 收藏同步、localStorage 容錯、卡片內容、台股色彩（漲紅跌綠、0 中性、缺值灰）、取消／復原、拖曳／移動選單、
# 空狀態、Detail 收藏、Active Flow 保護（FL-*）。真機才能產生的條件照實 DEFER。
import sys, json, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0
cdp('Network.setCacheDisabled', {'cacheDisabled': True})

KEY = 'etfRadar.watch.v1'
UP, DN, DIM = 'rgb(255, 63, 94)', 'rgb(0, 200, 122)', 'rgb(139, 148, 158)'

def set_view(w, h, orient='portraitPrimary'):
    cdp('Emulation.setDeviceMetricsOverride', {'width': w, 'height': h, 'deviceScaleFactor': 1, 'mobile': True,
        'screenOrientation': {'type': orient, 'angle': 90 if orient.startswith('landscape') else 0}})
    wait_ms(400)

def reload_page():
    cdp('Page.reload'); time.sleep(1.8)
    ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if((typeof ETFS!=='undefined'&&ETFS.length>0)||Date.now()-t>30000){clearInterval(i);r(1)}},200)})", True)
    wait_ms(300)

def store_set(codes):
    ev("localStorage.setItem(%s, JSON.stringify({v:1,codes:%s})); WatchStore._reload(); Watch.render(); true" % (json.dumps(KEY), json.dumps(codes)))
    wait_ms(60)

def store(): return ev("WatchStore.list()")
def cards(): return ev("[...document.querySelectorAll('#watchList .wc')].map(c=>c.dataset.code)")
def go_watch():
    ev("Router.toBase({base:'watch'}); true"); wait_ms(250)
def js_color(sel): return ev("(function(){ const e=document.querySelector(%s); return e?getComputedStyle(e).color:null; })()" % json.dumps(sel))

set_view(390, 844)
cdp('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 1})
reload_page()
ev("localStorage.removeItem(%s); WatchStore._reload(); Watch.render(); true" % json.dumps(KEY))
CODES = ev("ETFS.slice(0, 12).map(e=>e.code)")

# ── ST：WatchStore ──
r = ev("""(function(){ const s=WatchStore; s._reload();
  s.add('0050'); s.add('0056'); s.add('0050'); s.add('00878'); const a=s.list().join();
  const rm=s.remove('0056'); const b=s.list().join(); s.restore('0056', rm.index); const c=s.list().join();
  s.moveCode('00878', '0050'); const d=s.list().join(); s.moveCode('0050', null); const e=s.list().join();
  return [a,rm.index,b,c,d,e]; })()""")
check('ST-1 add／remove／restore／moveCode；重複 add 不重複', r == ['0050,0056,00878', 1, '0050,00878', '0050,0056,00878', '00878,0050,0056', '00878,0056,0050'], r)
store_set(['0056', '0050', '00878'])
reload_page()
check('ST-3 重新整理後收藏與順序保留', store() == ['0056', '0050', '00878'], store())
ev("localStorage.setItem(%s, '{bad json'); WatchStore._reload(); true" % json.dumps(KEY))
check('ST-2 壞 JSON → 清洗為空、無例外', store() == [], store())
ev("localStorage.setItem(%s, JSON.stringify({v:1,codes:['0050','0050',3,' 0056 ']})); WatchStore._reload(); true" % json.dumps(KEY))
check('ST-2 清洗：去重、去非字串、trim', store() == ['0050', '0056'], store())
store_set(['0050'])
ev("window.__setCalls=0; window.__origSet=Storage.prototype.setItem; Storage.prototype.setItem=function(){ window.__setCalls++; return window.__origSet.apply(this, arguments); }; true")
ev("window.__origSet.call(localStorage, %s, JSON.stringify({v:1,codes:['0050','0056']})); window.dispatchEvent(new StorageEvent('storage',{key:%s})); true" % (json.dumps(KEY), json.dumps(KEY)))
wait_ms(80)
check('ST-4 storage 事件 → 同步', store() == ['0050', '0056'], store())
check('ST-5 storage 同步不回寫（setItem 未被呼叫）', ev("window.__setCalls") == 0, ev("window.__setCalls"))
ev("Storage.prototype.setItem=window.__origSet; true")
# ST-6／ST-7：寫入失敗
store_set(['0050'])
ev("Storage.prototype.setItem=function(){ throw new Error('QuotaExceeded'); }; true")
ev("watchToggle('0056'); true"); go_watch()
check('ST-6 寫入失敗：畫面保留本次變更', store() == ['0050', '0056'] and cards() == ['0050', '0056'], (store(), cards()))
note = ev("document.getElementById('watchNote').textContent")
check('ST-6 寫入失敗提示（不宣稱已清空）', '這次的變更無法保存' in note and '清空' not in note, note)
ev("window.__origSet.call(localStorage, %s, JSON.stringify({v:1,codes:['00878']})); window.dispatchEvent(new StorageEvent('storage',{key:%s})); true" % (json.dumps(KEY), json.dumps(KEY)))
wait_ms(80)
check('ST-6 寫入失敗後收到舊資料的 storage 事件 → 不覆蓋記憶體狀態', store() == ['0050', '0056'], store())
ev("Storage.prototype.setItem=window.__origSet; true")
ev("window.__origSet.call(localStorage, %s, JSON.stringify({v:1,codes:['0050']})); true" % json.dumps(KEY))
reload_page()
check('ST-7 寫入失敗後 reload → 回到先前成功保存的內容（非全部清空）', store() == ['0050'], store())
# ST-8：讀取失敗
sid = cdp('Page.addScriptToEvaluateOnNewDocument', {'source': "Storage.prototype.getItem=function(){ throw new Error('SecurityError'); };"})['result']['identifier']
reload_page()
go_watch()
r8 = ev("({ok: WatchStore.readOk(), note: document.getElementById('watchNote').textContent})")
ev("watchToggle('0050'); true")
check('ST-8 讀取失敗 → 記憶體模式、提示「無法保存」、仍可收藏', r8['ok'] is False and '無法保存自選' in r8['note'] and store() == ['0050'], (r8, store()))
cdp('Page.removeScriptToEvaluateOnNewDocument', {'identifier': sid})
reload_page()
store_set([])

# ── SY：三處同步 ──
ev("Router.toBase({base:'cat'}); true"); wait_ms(200)
ev("Router.openFolder('mcap'); true"); wait_ms(450)
row = ev("""(function(){ const r=document.querySelector('#catList .cat-row'); const f=r.querySelector('.fav-btn'), m=r.querySelector('.cr-main');
  const fr=f.getBoundingClientRect(); return {code:r.dataset.code, w:Math.round(fr.width), h:Math.round(fr.height), pressed:f.getAttribute('aria-pressed'), label:f.getAttribute('aria-label'),
  yld: !!r.querySelector('.cr-yld'), nested: !!r.querySelector('button button')}; })()""")
c0 = row['code']
check('SY-2 分類列 ♡：44×44、aria-pressed=false、aria-label 加入自選、無殖利率、無巢狀 button', row['w'] >= 44 and row['h'] >= 44 and row['pressed'] == 'false' and row['label'].startswith('加入自選：' + c0) and not row['yld'] and not row['nested'], row)
ev("document.getElementById('catMore').click(); true"); wait_ms(200)   # 已展開 20 檔，清單可捲動
ev("document.getElementById('catList').scrollTop = 30; true"); wait_ms(250)
st0 = ev("JSON.stringify(Router.state().stack[0].ui)")
ev("document.querySelector('#catList .cat-row .fav-btn').click(); true"); wait_ms(150)
check('SY-2 點 ♡ 不開 Detail', ev("document.getElementById('gsPanel').hidden") is True)
check('SY-1 分類點 ♡ → Store 有、♡ 變 ♥（aria-pressed=true）', store() == [c0] and ev("document.querySelector('#catList .cat-row .fav-btn').getAttribute('aria-pressed')") == 'true', store())
check('SY-3 點 ♡ 後分類清單捲動／已展開數／排序不變', ev("JSON.stringify(Router.state().stack[0].ui)") == st0 and abs(ev("document.getElementById('catList').scrollTop") - 30) <= 1, (st0, ev("JSON.stringify(Router.state().stack[0].ui)")))
check('ES-2 新增收藏不顯示 Toast（D4）', ev("document.getElementById('watchToast').hidden") is True)
ev("document.querySelector('#catList .cat-row .cr-main').click(); true"); wait_ms(300)
check('SY-1 Detail 顯示 ♥', ev("document.getElementById('dtFav').getAttribute('aria-pressed')") == 'true' and ev("document.getElementById('dtFav').textContent") == '♥')
ev("document.getElementById('dtClose').click(); true"); wait_ms(320)
go_watch()
check('SY-1 自選頁出現卡片', cards() == [c0], cards())
ev("document.querySelector('#watchList .wc .fav-btn').click(); true"); wait_ms(100)
ev("Router.toBase({base:'cat'}); true"); wait_ms(200); ev("Router.openFolder('mcap'); true"); wait_ms(450)
check('SY-1 自選取消 → 分類回到 ♡', ev("document.querySelector('#catList .cat-row[data-code=\"%s\"] .fav-btn').getAttribute('aria-pressed')" % c0) == 'false')
ev("document.getElementById('catClose').click(); true"); wait_ms(320)

# ── CD：卡片內容、→ Detail → 返回 ──
store_set(CODES[:4])
go_watch()
cd = ev("""(function(){ const c=document.querySelector('#watchList .wc'); const e=ETFS.find(x=>x.code===c.dataset.code); const t=c.innerText;
  return {code:c.dataset.code, hasName:t.includes(e.name), hasPx:t.includes(Number(e.price).toFixed(2)), bars:c.querySelectorAll('.wc-bars .mb').length,
  label:t.includes('近半年走勢'), sig:!!c.querySelector('[class^=sig-]'), cat:t.includes(catDefOf(catClassify(e)).label), freq:t.includes(e.div_frequency),
  noYld:!t.includes('殖利率'), no52:!t.includes('52'), noRsi:!t.includes('RSI'), fav:c.querySelector('.fav-btn').textContent}; })()""")
check('CD-1 卡片內容：代碼名稱、現價、近半年走勢 6 柱、訊號、分類、配息頻率、♥', cd['hasName'] and cd['hasPx'] and cd['bars'] == 6 and cd['label'] and cd['sig'] and cd['cat'] and cd['freq'] and cd['fav'] == '♥', cd)
check('CD-1 卡片不含殖利率、52 週、RSI', cd['noYld'] and cd['no52'] and cd['noRsi'], cd)
check('ES-2 拖曳提示：≥ 2 檔時顯示（明文含 ⠿）', ev("!document.getElementById('watchHint').hidden && document.getElementById('watchHint').textContent.includes('按住 ⠿')") is True)
check('ES-2 儲存提示存在', '僅儲存在此裝置與瀏覽器中' in ev("document.getElementById('watchNote').textContent"))
store_set(CODES[:10])
go_watch()
ev("window.scrollTo(0, 400); true"); wait_ms(150)
y0 = ev("window.scrollY")
h0 = ev("history.length")
ev("document.querySelectorAll('#watchList .wc .wc-main')[5].click(); true"); wait_ms(320)
check('CD-2 卡片 → 既有 Detail（#gsPanel，同一套）', ev("!document.getElementById('gsPanel').hidden") is True and ev("Router.state().base") == 'watch' and ev("Router.state().stack.map(l=>l.t).join()") == 'detail')
ev("document.getElementById('dtClose').click(); true"); wait_ms(320)
check('CD-2 ✕ 返回：仍在自選頁、window 捲動位置不變', ev("document.getElementById('page-watch').classList.contains('active')") is True and abs(ev("window.scrollY") - y0) <= 2, (y0, ev("window.scrollY")))
ev("document.querySelectorAll('#watchList .wc .wc-main')[5].click(); true"); wait_ms(320)
ev("history.back(); true"); wait_ms(350)
check('CD-2 Back 返回：仍在自選頁、捲動位置不變', ev("document.getElementById('gsPanel').hidden") is True and abs(ev("window.scrollY") - y0) <= 2, ev("window.scrollY"))
code5 = cards()[5]
ev("document.querySelectorAll('#watchList .wc .wc-main')[5].click(); true"); wait_ms(320)
ev("document.getElementById('dtFav').click(); true"); wait_ms(120)
ev("document.getElementById('dtClose').click(); true"); wait_ms(320)
check('CD-3 Detail 取消收藏 → 返回後卡片消失、Toast 出現', code5 not in cards() and ev("document.getElementById('watchToast').hidden") is False, cards())
ev("document.getElementById('watchUndo').click(); true"); wait_ms(100)
check('CD-3 復原 → 回到原位置', cards()[5] == code5, cards())

# ── UN：取消／復原 ──
store_set(CODES[:4])
go_watch()
c = cards()
ev("document.querySelectorAll('#watchList .wc .fav-btn')[1].click(); true"); wait_ms(100)
check('UN-1 移除第 2 張 → Toast「已從自選移除　復原」', ev("document.getElementById('watchToast').hidden") is False and ev("document.getElementById('watchToastMsg').textContent") == '已從自選移除' and cards() == [c[0], c[2], c[3]])
ev("document.getElementById('watchUndo').click(); true"); wait_ms(100)
check('UN-1 復原 → 回到第 2 位、Toast 關閉', cards() == c and ev("document.getElementById('watchToast').hidden") is True, cards())
ev("document.querySelectorAll('#watchList .wc .fav-btn')[0].click(); true"); wait_ms(5300)
check('UN-1 約 5 秒後 Toast 自動消失', ev("document.getElementById('watchToast').hidden") is True)
# UN-5a
store_set(CODES[:5]); go_watch(); c = cards()
ev("watchToggle(%s); true" % json.dumps(c[2])); wait_ms(60)
ev("watchToggle(%s); true" % json.dumps(c[0])); wait_ms(60)
ev("document.getElementById('watchUndo').click(); true"); wait_ms(80)
check('UN-5a 連續移除：只復原最後一檔（回 index 0），先移除的不回來', cards() == [c[0], c[1], c[3], c[4]], cards())
# UN-5b
store_set(CODES[:5]); go_watch(); c = cards()
ev("watchToggle(%s); true" % json.dumps(c[4])); wait_ms(60)
ev("localStorage.setItem(%s, JSON.stringify({v:1,codes:%s})); window.dispatchEvent(new StorageEvent('storage',{key:%s})); true" % (json.dumps(KEY), json.dumps(c[:2]), json.dumps(KEY)))
wait_ms(80)
ev("document.getElementById('watchUndo').click(); true"); wait_ms(80)
check('UN-5b Toast 存續時清單縮短 → 復原插在 min(4, 2)=2', cards() == [c[0], c[1], c[4]], cards())
# UN-5c
store_set(CODES[:5]); go_watch(); c = cards()
ev("watchToggle(%s); true" % json.dumps(c[1])); wait_ms(60)
ev("WatchStore.moveCode(%s, null); true" % json.dumps(c[0])); wait_ms(60)
ev("document.getElementById('watchUndo').click(); true"); wait_ms(80)
check('UN-5c 移除後重排再復原 → 以原 index 1 夾限', cards() == [c[2], c[1], c[3], c[4], c[0]], cards())
# UN-2／UN-3／UN-4／UN-6
store_set(CODES[:1]); go_watch()
ev("watchToggle(%s); true" % json.dumps(CODES[0])); wait_ms(60)
check('UN-3 最後一檔移除 → 引導式空狀態', ev("!document.getElementById('watchEmpty').hidden") is True and '還沒有收藏 ETF' in ev("document.getElementById('watchEmpty').innerText") and cards() == [])
ev("document.getElementById('watchUndo').click(); true"); wait_ms(80)
check('UN-3 復原 → 回到 1 張', cards() == [CODES[0]] and ev("document.getElementById('watchEmpty').hidden") is True)
store_set(CODES[:3]); go_watch(); c = cards()
ev("watchToggle(%s); true" % json.dumps(c[0])); wait_ms(60)
ev("WatchStore.add(%s); true" % json.dumps(c[0])); wait_ms(60)
ev("document.getElementById('watchUndo').click(); true"); wait_ms(80)
check('UN-4 復原冪等：期間重新加入 → 不重複、位置不變', cards() == [c[1], c[2], c[0]], cards())
store_set(CODES[:3]); go_watch(); c = cards()
ev("watchToggle(%s); true" % json.dumps(c[1])); wait_ms(60)
ev("localStorage.setItem(%s, JSON.stringify({v:1,codes:%s})); window.dispatchEvent(new StorageEvent('storage',{key:%s})); true" % (json.dumps(KEY), json.dumps(c), json.dumps(KEY)))
wait_ms(80)
ev("document.getElementById('watchUndo').click(); true"); wait_ms(80)
check('UN-6 跨分頁重新加入後復原 → 不重複', cards() == c, cards())

# ── BR／CL：6 柱與今日漲跌（台股：漲紅、跌綠、0 中性、缺值灰）──
store_set(CODES[:1]); go_watch()
ev("window.__bk=JSON.stringify(ETFS[0]); ETFS[0].ret_months=[2.1,-1.5,0,null,3.0,-0.4]; ETFS[0].change_pt=0.5; ETFS[0].change_pct=1.2; Watch.refresh(); true")
br = ev("[...document.querySelectorAll('#watchList .wc .wc-bars .mb')].map(m=>({k:m.dataset.k, c:getComputedStyle(m.querySelector('.mb-bar')).backgroundColor, b:m.querySelector('.mb-bar').style.bottom, t:m.querySelector('.mb-bar').style.top}))")
check('BR-1 6 柱 kind：up／dn／zero／na／up／dn', [x['k'] for x in br] == ['up', 'dn', 'zero', 'na', 'up', 'dn'], br)
check('BR-1 正值紅（--up）向上、負值綠（--dn）向下', br[0]['c'] == UP and br[0]['b'] and br[1]['c'] == DN and br[1]['t'] == '13px' and br[5]['c'] == DN, br)
check('BR-1 0 為中性（--dim），缺值為灰（與 0 可區分）', br[2]['c'] == DIM and br[3]['c'] == 'rgba(255, 255, 255, 0.15)' and br[2]['c'] != br[3]['c'], br)
def chg(pt, pct):
    ev("ETFS[0].change_pt=%s; ETFS[0].change_pct=%s; Watch.refresh(); true" % (json.dumps(pt), json.dumps(pct)))
    return ev("[...document.querySelectorAll('#watchList .wc .wc-chg')].map(x=>[x.textContent, getComputedStyle(x).color])")
r = chg(0.5, 1.2)
check('CL-1 今日上漲：額紅 ▲0.50、幅紅 +1.20%', r == [['▲0.50', UP], ['+1.20%', UP]], r)
check('CL-2 反向守衛：上漲不是綠', all(x[1] != DN for x in r))
r = chg(-0.5, -1.2)
check('CL-1 今日下跌：額綠 ▼0.50、幅綠 −1.20%', r == [['▼0.50', DN], ['−1.20%', DN]], r)
check('CL-2 反向守衛：下跌不是紅', all(x[1] != UP for x in r))
r = chg(0, 0)
check('CL-1 今日 0：兩欄中性、無箭頭與正負號', r == [['0.00', DIM], ['0.00%', DIM]], r)
r = chg(None, None)
check('CL-1 今日缺值：兩欄「--」灰', r == [['--', DIM], ['--', DIM]], r)
# CL-3：兩欄各自判色（Code Review #3）——四捨五入後為 0、部分缺欄、正負不同號
r = chg(-0.01, 0)
check('CL-3 額 −0.01、幅 0 → 額綠 ▼0.01、幅中性 0.00%', r == [['▼0.01', DN], ['0.00%', DIM]], r)
r = chg(0, 0.01)
check('CL-3 額 0、幅 +0.01 → 額中性 0.00（不變紅、無 ▲）、幅紅 +0.01%', r == [['0.00', DIM], ['+0.01%', UP]], r)
r = chg(None, 1.2)
check('CL-3 額缺值、幅 +1.2 → 額灰「--」（不被染紅）、幅紅', r == [['--', DIM], ['+1.20%', UP]], r)
r = chg(0.3, None)
check('CL-3 額 +0.3、幅缺值 → 額紅 ▲0.30、幅灰「--」', r == [['▲0.30', UP], ['--', DIM]], r)
r = chg(0.004, -0.004)
check('CL-3 四捨五入為 0（+0.004／−0.004）→ 兩欄中性、無 −0.00', r == [['0.00', DIM], ['0.00%', DIM]], r)
r = chg(0.2, -0.1)
check('CL-3 正負不同號 → 額紅 ▲、幅綠 −', r == [['▲0.20', UP], ['−0.10%', DN]], r)
ev("ETFS[0].ret_months=[null,null,null,null,null,null]; Watch.refresh(); true")
check('BR-2 6 段全缺 → 不畫柱、顯示「歷史資料不足」', ev("document.querySelectorAll('#watchList .wc-bars').length") == 0 and '歷史資料不足' in ev("document.querySelector('#watchList .wc').innerText"))
ev("Object.assign(ETFS[0], JSON.parse(window.__bk)); Watch.refresh(); true")
part = ev("(ETFS.find(e=>e.ret_months && e.ret_months.some(v=>v==null) && e.ret_months.some(v=>v!=null))||{}).code")
if part:
    store_set([part]); go_watch()
    want = ev("ETFS.find(e=>e.code===%s).ret_months.filter(v=>v==null).length" % json.dumps(part))
    check('BR-3 新上市部分缺值（%s）：灰柱數量正確' % part, ev("document.querySelectorAll('#watchList .mb[data-k=na]').length") == want, want)
d1 = ev("(function(){ const h=miniBars([1.5,0,-2,null]); const d=document.createElement('div'); d.innerHTML=h; document.body.appendChild(d); const r=[...d.querySelectorAll('.mb')].map(m=>m.dataset.k+':'+getComputedStyle(m.querySelector('.mb-bar')).backgroundColor); d.remove(); return r; })()")
check('D1 全站 miniBars（排行／Detail 預設）：0 為中性、漲紅跌綠', d1[1] == 'zero:' + DIM and d1[0].startswith('up:rgb(255, 107, 107)') and d1[2].startswith('dn:rgb(0, 229, 160)'), d1)

# ── ES：空狀態 → 前往分類 ──
store_set([]); go_watch()
check('ES-1 空狀態文案', '還沒有收藏 ETF' in ev("document.getElementById('watchEmpty').innerText") and '按下 ♡ 就能加入這裡' in ev("document.getElementById('watchEmpty').innerText"))
check('ES-1 標題「我的 ETF」', ev("document.querySelector('#page-watch .wt-title').textContent") == '我的 ETF')
ev("document.getElementById('watchGoCat').click(); true"); wait_ms(300)
check('ES-1 ［前往分類］→ 分類總覽', ev("Router.state().base") == 'cat' and ev("document.getElementById('page-cat').dataset.state") == 'overview')

# ── DR：拖曳／移動選單／鍵盤 ──
def handle_xy(i):
    return ev("(function(){ const h=document.querySelectorAll('#watchList .drag-handle')[%d]; const r=h.getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2]; })()" % i)
def touch(t, x, y):
    cdp('Input.dispatchTouchEvent', {'type': t, 'touchPoints': [] if t in ('touchEnd', 'touchCancel') else [{'x': x, 'y': y}]})
def drag_to(i, dy, steps=8, hold_ms=0, end='touchEnd'):
    x, y = handle_xy(i)
    touch('touchStart', x, y)
    for k in range(1, steps + 1):
        touch('touchMove', x, y + dy * k / steps); wait_ms(16)
    if hold_ms: wait_ms(hold_ms)
    touch(end, x, y + dy)
    wait_ms(120)

store_set(CODES[:4]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
check('DR-3 把手 touch-action:none；卡片其他區域不是 none', ev("getComputedStyle(document.querySelector('.drag-handle')).touchAction") == 'none' and ev("getComputedStyle(document.querySelector('.wc-main')).touchAction") != 'none')
step = ev("(function(){ const a=document.querySelectorAll('#watchList .wc'); return a[1].getBoundingClientRect().top-a[0].getBoundingClientRect().top; })()")
drag_to(0, step * 1.6)
check('DR-1 把手拖曳：第 1 張拖到第 2 張之後 → 順序改變並寫入', cards() == [c[1], c[0], c[2], c[3]] and json.loads(ev("localStorage.getItem(%s)" % json.dumps(KEY)))['codes'] == [c[1], c[0], c[2], c[3]], cards())
check('DR-1 結束後無殘留 transform／拖曳狀態', ev("[...document.querySelectorAll('#watchList .wc')].every(x=>!x.style.transform)") is True and ev("Watch._state().dragging") is False)
store_set(CODES[:10]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
x0 = ev("(function(){ const r=document.querySelectorAll('#watchList .wc-main')[1].getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2]; })()")
cdp('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x0[0], 'y': x0[1] + 200}]})
for k in range(1, 13):
    cdp('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x0[0], 'y': x0[1] + 200 - 25 * k}]}); wait_ms(16)
cdp('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
wait_ms(400)
check('DR-2 卡片本體垂直滑動 → 頁面捲動、順序不變', ev("window.scrollY") > 100 and cards() == c, (ev("window.scrollY"), cards() == c))
# DR-9：頁面已捲動再拖曳
y_before = ev("window.scrollY")
idx = ev("(function(){ const a=[...document.querySelectorAll('#watchList .wc')]; return a.findIndex(x=>{const r=x.getBoundingClientRect(); return r.top>120 && r.bottom<600;}); })()")
c = cards()
drag_to(idx, step * 1.6)
exp = c[:idx] + [c[idx + 1], c[idx]] + c[idx + 2:]
check('DR-9 頁面已捲動時拖曳：位移與插入位置正確', cards() == exp, (idx, cards()))
# DR-8：10 檔上下緣連續拖曳（自動捲動）
store_set(CODES[:10]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
x, y = handle_xy(0)
bottom = ev("document.querySelector('.bottom-nav').getBoundingClientRect().top")
touch('touchStart', x, y)
for k in range(1, 11):
    touch('touchMove', x, y + (bottom - 10 - y) * k / 10); wait_ms(16)
wait_ms(3500)
scrolled = ev("window.scrollY")
touch('touchEnd', x, bottom - 10); wait_ms(150)
check('DR-8 拖到下緣停住 → 自動捲動直到最後，放下成為第 10', cards()[-1] == c[0] and scrolled > 300, (scrolled, cards().index(c[0]) if c[0] in cards() else None))
c = cards()
x, y = handle_xy(9)
top = ev("document.querySelector('.app-hdr').getBoundingClientRect().bottom")
touch('touchStart', x, y)
for k in range(1, 11):
    touch('touchMove', x, y + (top + 10 - y) * k / 10); wait_ms(16)
wait_ms(3500)
touch('touchEnd', x, top + 10); wait_ms(150)
check('DR-8 反向：拖到上緣停住 → 放下成為第 1', cards()[0] == c[9] and ev("window.scrollY") < 50, (ev("window.scrollY"), cards()[:2]))
# DR-11：自動捲動中 cancel
ev("window.scrollTo(0,0); true"); wait_ms(100)
x, y = handle_xy(0)
c = cards()
touch('touchStart', x, y)
for k in range(1, 11):
    touch('touchMove', x, y + (bottom - 10 - y) * k / 10); wait_ms(16)
wait_ms(600)
touch('touchCancel', x, bottom - 10); wait_ms(100)
s1 = ev("window.scrollY"); wait_ms(500); s2 = ev("window.scrollY")
check('DR-11 cancel → 停止自動捲動、清除 transform、不寫入', s1 == s2 and cards() == c and ev("[...document.querySelectorAll('#watchList .wc')].every(x=>!x.style.transform)") is True, (s1, s2))
# DR-7：拖曳中清單改變（另一分頁刪除 A）
store_set(CODES[:4]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
x, y = handle_xy(1)
touch('touchStart', x, y); touch('touchMove', x, y + 30); wait_ms(30); touch('touchMove', x, y + step * 1.6); wait_ms(60)
dragging = ev("Watch._state().dragging")
newlist = [c[1], c[2], c[3]]
ev("localStorage.setItem(%s, JSON.stringify({v:1,codes:%s})); window.dispatchEvent(new StorageEvent('storage',{key:%s})); true" % (json.dumps(KEY), json.dumps(newlist), json.dumps(KEY)))
wait_ms(80)
touch('touchEnd', x, y + step * 1.6); wait_ms(120)
check('DR-7 拖曳中清單改變 → 取消拖曳、不寫入、畫面＝Store', dragging is True and cards() == newlist and store() == newlist and ev("Watch._state().dragging") is False, (dragging, cards()))
# DR-6：拖曳中行情更新延後
c = cards()
x, y = handle_xy(0)
touch('touchStart', x, y); touch('touchMove', x, y + 30); wait_ms(60)
ev("Watch.refresh(); true")
pend = ev("Watch._state().pendingRefresh")
touch('touchCancel', x, y + 30); wait_ms(80)
check('DR-6 拖曳中 refresh 延後、放開後補畫', pend is True and ev("Watch._state().pendingRefresh") is False and cards() == c)
# DR-12：拖曳中導航
x, y = handle_xy(0)
touch('touchStart', x, y); touch('touchMove', x, y + 30); wait_ms(60)
ev("switchPage('cat'); true"); wait_ms(200)
check('DR-12 拖曳中換頁 → 拖曳結束、無殘留、未寫入', ev("Watch._state().dragging") is False and ev("document.body.classList.contains('wt-dragging')") is False and store() == c and ev("[...document.querySelectorAll('#watchList .wc')].every(x=>!x.style.transform)") is True)
touch('touchEnd', x, y + 30); wait_ms(60)
go_watch()
x, y = handle_xy(0)
touch('touchStart', x, y); touch('touchMove', x, y + 30); wait_ms(60)
ev("openDetail(%s); true" % json.dumps(c[2])); wait_ms(300)
check('DR-12 拖曳中開 Detail → 拖曳結束、未寫入', ev("Watch._state().dragging") is False and store() == c)
touch('touchEnd', x, y + 30); wait_ms(60)
ev("document.getElementById('dtClose').click(); true"); wait_ms(320)
# DR-13：連續鍵盤排序
store_set(CODES[:5]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
ev("document.querySelectorAll('#watchList .drag-handle')[0].focus(); true")
sy = ev("window.scrollY")
for _ in range(3):
    cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'ArrowDown', 'code': 'ArrowDown', 'windowsVirtualKeyCode': 40})
    cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'ArrowDown', 'code': 'ArrowDown', 'windowsVirtualKeyCode': 40})
    wait_ms(80)
check('DR-13 連按 ↓ 三次 → 下移三格、未捲頁、焦點仍在同一檔把手', cards() == [c[1], c[2], c[3], c[0], c[4]] and ev("window.scrollY") == sy and ev("document.activeElement.closest('.wc') && document.activeElement.closest('.wc').dataset.code") == c[0] and ev("document.activeElement.classList.contains('drag-handle')") is True, cards())
check('DR-5 鍵盤排序有 aria-live 播報', '移到第 4 位' in (ev("document.getElementById('watchLive').textContent") or ''), ev("document.getElementById('watchLive').textContent"))
# DR-14：點一下 ⠿ 開移動選單
store_set(CODES[:4]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
x, y = handle_xy(2)
touch('touchStart', x, y); touch('touchMove', x, y + 3); touch('touchEnd', x, y + 3); wait_ms(120)
check('DR-14 點一下 ⠿（移動 < 8px）→ 移動選單出現', ev("Watch._state().menu") == c[2] and ev("document.querySelectorAll('.wc-menu button').length") == 4)
ev("document.querySelector('.wc-menu button[data-m=top]').click(); true"); wait_ms(100)
check('DR-14「移到最上面」生效、選單關閉', cards() == [c[2], c[0], c[1], c[3]] and ev("Watch._state().menu") is None, cards())
x, y = handle_xy(0)
touch('touchStart', x, y); touch('touchEnd', x, y); wait_ms(120)
check('DR-14 第一檔：「上移一格／移到最上面」停用', ev("[...document.querySelectorAll('.wc-menu button')].filter(b=>b.disabled).map(b=>b.dataset.m).join()") == 'up,top')
cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27}); wait_ms(80)
check('DR-14 Esc 關閉選單、焦點回把手', ev("Watch._state().menu") is None and ev("document.activeElement.classList.contains('drag-handle')") is True)
# ── Code Review #1：把手的標準 click activation（VoiceOver／TalkBack 合成 click、Enter／Space）──
store_set(CODES[:4]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
ev("document.querySelectorAll('#watchList .drag-handle')[1].click(); true"); wait_ms(80)
check('DR-15 click-only（合成 click）→ 開啟移動選單', ev("Watch._state().menu") == c[1] and ev("document.querySelectorAll('.wc-menu').length") == 1)
ev("document.querySelectorAll('#watchList .drag-handle')[1].click(); true"); wait_ms(80)
check('DR-15 再 click 同一把手 → 關閉選單、焦點回把手', ev("Watch._state().menu") is None and ev("document.activeElement === document.querySelectorAll('#watchList .drag-handle')[1]") is True)
def key(k, code, vk, text=None):
    p = {'type': 'keyDown', 'key': k, 'code': code, 'windowsVirtualKeyCode': vk}
    if text: p['text'] = text
    cdp('Input.dispatchKeyEvent', p)
    cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': k, 'code': code, 'windowsVirtualKeyCode': vk})
    wait_ms(80)
ev("document.querySelectorAll('#watchList .drag-handle')[2].focus(); true")
key('Enter', 'Enter', 13, '\r')
check('DR-16 Enter → 開啟選單（只開一次）', ev("Watch._state().menu") == c[2] and ev("document.querySelectorAll('.wc-menu').length") == 1)
key('Escape', 'Escape', 27)
ev("document.querySelectorAll('#watchList .drag-handle')[2].focus(); true")
key(' ', 'Space', 32, ' ')
check('DR-16 Space → 開啟選單（只開一次）、未捲頁', ev("Watch._state().menu") == c[2] and ev("window.scrollY") == 0)
key('Escape', 'Escape', 27)
x, y = handle_xy(3)
touch('touchStart', x, y); touch('touchEnd', x, y); wait_ms(300)
check('DR-17 真實 tap → 選單開啟且只觸發一次（未立即關閉）', ev("Watch._state().menu") == c[3] and ev("document.querySelectorAll('.wc-menu').length") == 1)
ev("document.querySelectorAll('#watchList .drag-handle')[3].click(); true"); wait_ms(80)
drag_to(0, step * 1.6); wait_ms(300)
check('DR-18 拖曳放開 → 不開選單、順序已改', ev("Watch._state().menu") is None and cards() == [c[1], c[0], c[2], c[3]], cards())

# ── Code Review #2：已開選單時開始拖曳 → 先關選單再量測，卡片跟手 ──
def follow(i, dy):
    """按住第 i 檔把手往下 dy px，回傳（手指 y, 把手中心 y），之後 touchEnd 放開"""
    x, y = handle_xy(i)
    touch('touchStart', x, y)
    touch('touchMove', x, y + 10); wait_ms(30)
    touch('touchMove', x, y + dy); wait_ms(80)
    hy = ev("(function(){ const h=document.querySelector('#watchList .wc.lifting .drag-handle'); if(!h) return null; const r=h.getBoundingClientRect(); return r.top+r.height/2; })()")
    return x, y + dy, hy
store_set(CODES[:4]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
tx, ty = handle_xy(0); touch('touchStart', tx, ty); touch('touchEnd', tx, ty); wait_ms(250)   # 以真實 tap 開 A 的選單
menu_open = ev("Watch._state().menu") == c[0]
x, fy, hy = follow(0, 10)
check('DR-19 開 A 選單 → 拖 A：選單先關閉、卡片跟手（誤差 ≤ 3px）', menu_open and ev("Watch._state().menu") is None and hy is not None and abs(hy - fy) <= 3, (fy, hy))
touch('touchMove', x, fy + step * 1.6 - 10); wait_ms(80)
touch('touchEnd', x, fy + step * 1.6 - 10); wait_ms(150)
check('DR-19 放開 → A 移到 B 之後、不開選單', cards() == [c[1], c[0], c[2], c[3]] and ev("Watch._state().menu") is None, cards())
store_set(CODES[:4]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
c = cards()
tx, ty = handle_xy(0); touch('touchStart', tx, ty); touch('touchEnd', tx, ty); wait_ms(250)   # 以真實 tap 開 A 的選單
menu_open = ev("Watch._state().menu") == c[0]
x, fy, hy = follow(1, 10)        # B 在 A 的選單下方：關閉選單會讓 B 上移，卡片仍須在手指下
check('DR-20 開 A 選單 → 拖下方 B 10px：卡片跟手（誤差 ≤ 3px，不偏離選單高度）', menu_open and hy is not None and abs(hy - fy) <= 3, (fy, hy))
# 依「關閉選單後的新版面」計算：讓拖曳中的卡片中心落在 C 的中心再往下 10px（C 之後、D 之前）
d = ev(r"(function(){ const a=[...document.querySelectorAll('#watchList .wc')]; const me=a.find(x=>x.classList.contains('lifting')); const C=a[2]; const ty=v=>{const m=/translateY\((-?[\d.]+)px\)/.exec(v.style.transform||''); return m?parseFloat(m[1]):0;}; const rc=C.getBoundingClientRect(), rm=me.getBoundingClientRect(); return (rc.top+rc.height/2-ty(C)+10)-(rm.top+rm.height/2); })()")
touch('touchMove', x, fy + d); wait_ms(80)
touch('touchEnd', x, fy + d); wait_ms(150)
check('DR-20 放開 → B 移到 C 之後（最終順序正確）', cards() == [c[0], c[2], c[1], c[3]], cards())
# ── 6d2d9a3d 複審：選單在上方時，輕點下方把手（移動 < 8px）仍是 click，門檻只看手指實際移動 ──
def mouse(t, x, y):
    cdp('Input.dispatchMouseEvent', {'type': t, 'x': x, 'y': y, 'button': 'left', 'buttons': 1 if t != 'mouseReleased' else 0, 'clickCount': 1, 'pointerType': 'mouse'})
for (label, dev, dy) in [('觸控 3px', 'touch', 3), ('觸控 7px', 'touch', 7), ('滑鼠 1px', 'mouse', 1)]:
    store_set(CODES[:4]); go_watch(); ev("window.scrollTo(0,0); true"); wait_ms(100)
    c = cards()
    tx, ty = handle_xy(0); touch('touchStart', tx, ty); touch('touchEnd', tx, ty); wait_ms(250)
    a_open = ev("Watch._state().menu") == c[0]
    x, y = handle_xy(1)          # B 在 A 選單下方：按下時關閉選單會讓 B 上移約一個選單高
    if dev == 'touch':
        touch('touchStart', x, y); touch('touchMove', x, y + dy); wait_ms(60)
        mid = ev("Watch._state().dragging")
        touch('touchEnd', x, y + dy)
    else:
        mouse('mousePressed', x, y); mouse('mouseMoved', x, y + dy); wait_ms(60)
        mid = ev("Watch._state().dragging")
        mouse('mouseReleased', x, y + dy)
    wait_ms(250)
    check('DR-21 開 A 選單 → 輕點下方 B（%s，< 8px）：不開始拖曳、只開 B 選單、不重排' % label,
          a_open and mid is False and ev("Watch._state().menu") == c[1] and ev("document.querySelectorAll('.wc-menu').length") == 1 and cards() == c and store() == c,
          (a_open, mid, ev("Watch._state().menu"), cards() == c))
DEFER = []
DEFER.append('DR-R1 visualViewport.offsetTop > 0（鍵盤／瀏覽器 UI 造成可視區位移）時的拖曳與自動捲動：headless 無法產生，需 iPhone Chrome 真機')
DEFER.append('DR-R2 實際觸控拖曳手感、iOS 長按選字抑制、Samsung 左緣返回手勢：需真機')
DEFER.append('DR-R3 VoiceOver 點兩下 ⠿ 開移動選單、選單焦點：需真機')

# ── DF：Detail 收藏 ──
store_set([])
ev("Router.toBase({base:'home'}); true"); wait_ms(200)
ev("openDetail('0056'); true"); wait_ms(320)
ev("detailTab('dividend'); true"); wait_ms(150)
ev("(function(){ const i=document.getElementById('dtSharesIn'); if(i){ i.value='7'; i.dispatchEvent(new Event('input')); } return true; })()")
ev("document.getElementById('gsPanel').scrollTop = 40; true"); wait_ms(250)
before = ev("JSON.stringify({h:history.length, st:Router.state().stack.map(l=>l.t+':'+(l.code||'')), tab:_detailTab, sc:document.getElementById('gsPanel').scrollTop, n:(document.getElementById('dtSharesIn')||{}).value})")
ev("document.getElementById('dtFav').click(); true"); wait_ms(150)
after = ev("JSON.stringify({h:history.length, st:Router.state().stack.map(l=>l.t+':'+(l.code||'')), tab:_detailTab, sc:document.getElementById('gsPanel').scrollTop, n:(document.getElementById('dtSharesIn')||{}).value})")
check('DF-1 Detail 點 ♡：面板仍開、history／stack／tab／scroll／計算機輸入都不變', ev("!document.getElementById('gsPanel').hidden") is True and before == after and store() == ['0056'], (before, after))
check('DF-5 ✕ 為 #dtClose（原本的 ✕ 關閉），♡ 不是關閉控制', ev("document.getElementById('dtClose').textContent").startswith('✕') and ev("document.querySelector('#gsPanel .gs-panel-hd .fav-btn').id") == 'dtFav')
ev("openDetail('0050'); true"); wait_ms(300)
check('DF-2 Detail 換 ETF → ♡ 與 aria-label 更新', ev("document.getElementById('dtFav').getAttribute('aria-pressed')") == 'false' and ev("document.getElementById('dtFav').getAttribute('aria-label')").startswith('加入自選：0050'))
ev("openDetail('0056'); true"); wait_ms(300)
ev("history.back(); true"); wait_ms(350)
ev("history.forward(); true"); wait_ms(400)
check('DF-3 Back 關閉 → Forward 再開 → ♥ 仍正確', ev("!document.getElementById('gsPanel').hidden") is True and ev("document.getElementById('dtFav').getAttribute('aria-pressed')") == 'true', ev("_curEtfCode"))
ev("document.getElementById('dtClose').click(); true"); wait_ms(320)
ev("openDetail('ZZ999'); true"); wait_ms(320)
mf = ev("({p:document.getElementById('dtFav').getAttribute('aria-pressed'), l:document.getElementById('dtFav').getAttribute('aria-label')})")
ev("document.getElementById('dtFav').click(); true"); wait_ms(100)
check('DF-4 missing ETF：♡ 可切換、aria-label 帶代碼', mf['p'] == 'false' and 'ZZ999' in mf['l'] and ev("WatchStore.has('ZZ999')") is True, mf)
ev("document.getElementById('dtClose').click(); true"); wait_ms(320)
go_watch()
check('2.4 不在資料中的收藏：卡片顯示「目前無法取得這檔的資料」', '目前無法取得這檔的資料' in ev("document.querySelector('#watchList .wc[data-code=ZZ999]').innerText"))
ev("watchToggle('ZZ999'); true"); wait_ms(60)
ev("openDetail('0056'); true"); wait_ms(320)
ev("detailTab('perf'); true"); wait_ms(150)
ev("(function(){ const p=document.getElementById('gsPanel'); p.scrollTop = 0; p.scrollTop = p.scrollHeight; p.dispatchEvent(new Event('scroll')); return true; })()"); wait_ms(250)
col = ev("document.body.classList.contains('dt-collapsed')")
vis = ev("getComputedStyle(document.getElementById('dtFav')).display") != 'none' and ev("getComputedStyle(document.querySelector('.gs-panel-hd')).display") != 'none'
if col:
    check('DF-6 Detail 捲動收合：♡ 與 ✕ 同步隱藏（同屬標題列）', not vis)
else:
    DEFER.append('DF-6 Detail 內容在 headless 視窗未長到可收合：收合時 ♡ 與 ✕ 同屬標題列，需真機目視')
ev("document.getElementById('dtClose').click(); true"); wait_ms(320)

# ── LV：低高度／橫向 ──
store_set(CODES[:4]); go_watch()
for (w, h, o) in [(844, 390, 'landscapePrimary'), (390, 300, 'portraitPrimary')]:
    set_view(w, h, o)
    go_watch()
    lv = ev("({hx: document.documentElement.scrollWidth > document.documentElement.clientWidth, hw: Math.round(document.querySelector('.drag-handle').getBoundingClientRect().width)})")
    ev("watchToggle(%s); true" % json.dumps(CODES[3])); wait_ms(80)
    t = ev("(function(){ const t=document.getElementById('watchToast').getBoundingClientRect(), n=document.querySelector('.bottom-nav').getBoundingClientRect(), u=document.getElementById('watchUndo').getBoundingClientRect(); return {over: t.bottom > n.top + 0.5, undoH: Math.round(u.height), undoW: Math.round(u.width)}; })()")
    ev("document.getElementById('watchUndo').click(); true"); wait_ms(80)
    check('LV-1 %dx%d：無水平溢出、把手可用、Toast 不遮 nav、「復原」完整' % (w, h), not lv['hx'] and lv['hw'] >= 44 and not t['over'] and t['undoH'] >= 44 and t['undoW'] > 30, (lv, t))
set_view(390, 844)

# ── A11Y ──
go_watch()
a = ev("({fav: document.querySelector('#watchList .fav-btn').getAttribute('aria-label'), h: document.querySelector('#watchList .drag-handle').getAttribute('aria-label'), toast: document.getElementById('watchToast').getAttribute('role'), bars: (document.querySelector('#watchList .wc-bars')||{getAttribute:()=>''}).getAttribute('aria-label')})")
check('A11Y ♡／⠿ 有 accessible name、Toast role=status、6 柱有文字描述', a['fav'].startswith('從自選移除：') and a['h'].startswith('調整順序：') and '第 1 位' in a['h'] and a['toast'] == 'status' and a['bars'].startswith('近半年走勢：'), a)

# ── FL：Active Flow（持股異動）保護 ──
ev("Router.toBase({base:'cat'}); true"); wait_ms(200)
ev("Router.openFolder('active'); true"); wait_ms(450)
ev("Router.setFolderView('flow'); true"); wait_ms(400)
check('FL-1 分類 → 主動式 → 持股異動：顯示', ev("Category.isFlowVisible()") is True and ev("!!document.getElementById('treemap')") is True)
fake = {'name': '測試主動', 'issuer': '測試', 'holdings': 5, 'data_date': '2026-10-01', 'advanced': True, 'reason': '', 'fetched': True,
        'flow_from': '2026-09-30', 'flow_to': '2026-10-01', 'price_date': '2026-10-01', 'scale_pct': None, 'buy': 30000000, 'sell': 20000000, 'changed': 2,
        'flow': [{'code': '2330', 'name': '台積電', 'delta_shares': 30000, 'amount': 30000000.0}, {'code': '2317', 'name': '鴻海', 'delta_shares': -100000, 'amount': -20000000.0}],
        'no_price': [{'code': 'NVDA US', 'name': 'NVIDIA', 'delta_shares': 1200}, {'code': 'TSLA US', 'name': 'TESLA', 'delta_shares': -800}, {'code': 'AAPL US', 'name': 'APPLE', 'delta_shares': None}],
        'last_change_date': '2026-10-01'}
ev("_flowData.etfs['ZZ01A']=%s; flowSelect('ZZ01A'); true" % json.dumps(fake, ensure_ascii=False)); wait_ms(250)
cells = ev("[...document.querySelectorAll('#treemap .tm-cell')].map(c=>({n:c.innerText.split('\\n')[0], bg:getComputedStyle(c).backgroundColor}))")
buy = [x for x in cells if x['n'] == '台積電']; sell = [x for x in cells if x['n'] == '鴻海']
check('FL-2 treemap：加碼格紅系（255,63,94）、減碼格綠系（0,200,122）', buy and sell and buy[0]['bg'].startswith('rgba(255, 63, 94') and sell[0]['bg'].startswith('rgba(0, 200, 122'), cells)
check('FL-2 反向守衛：加碼不是綠、減碼不是紅', buy and sell and not buy[0]['bg'].startswith('rgba(0, 200') and not sell[0]['bg'].startswith('rgba(255, 63'))
np = ev("[...document.querySelectorAll('#flowForeign .np-d')].map(d=>({t:d.textContent, c:getComputedStyle(d).color}))")
check('FL-3 海外無報價：正值紅「加碼 +」、負值綠「減碼 -」、缺值中性', len(np) == 3 and np[0]['c'] == UP and np[0]['t'].startswith('加碼 +') and np[1]['c'] == DN and np[1]['t'].startswith('減碼 -') and np[2]['c'] == DIM, np)
for (patch, want) in [({'fetched': False}, '本次未能取得新資料'), ({'fetched': True, 'data_date': '2026-10-03'}, '持股無異動'), ({'fetched': True, 'data_date': '2026-10-01', 'flow_to': '2026-10-01', 'advanced': False, 'reason': 'not_updated'}, '尚未有新的 PCF')]:
    ev("Object.assign(_flowData.etfs['ZZ01A'], %s); renderFlow(); true" % json.dumps(patch)); wait_ms(150)
    check('FL-5 狀態語意：%s' % want, want in ev("document.getElementById('flowTip').textContent"), ev("document.getElementById('flowTip').textContent"))
sel0 = ev("_flowSel")
ev("watchToggle('0050'); Watch.render(); Watch.refresh(); true"); wait_ms(100)
check('FL-7 收藏／自選重繪不重設 Flow 選取與分段', ev("_flowSel") == sel0 and ev("Category.isFlowVisible()") is True, ev("_flowSel"))
ev("delete _flowData.etfs['ZZ01A']; true")
fcode = ev("Object.keys(_flowData.etfs).find(k=>(_flowData.etfs[k].flow||[]).length>0)")
for base in ['home', 'tools', 'cat', 'watch']:
    if base == 'tools':
        ev("switchPage('rank'); true"); wait_ms(250)
    else:
        ev("Router.toBase({base:%s}); true" % json.dumps(base)); wait_ms(250)
    ev("openDetail(%s); true" % json.dumps(fcode)); wait_ms(320)
    ev("detailTab('holdings'); true"); wait_ms(150)
    ok_btn = ev("!!document.querySelector('.gs-flow-btn')")
    ev("(function(){ const b=document.querySelector('.gs-flow-btn'); if(b) b.click(); return true; })()"); wait_ms(450)
    s1 = ev("({base:Router.state().base, t:Router.state().stack.map(l=>l.t+':'+(l.view||'')).join(), sel:_flowSel, vis:Category.isFlowVisible(), det:!document.getElementById('gsPanel').hidden})")
    ev("history.back(); true"); wait_ms(450)
    s2 = ev("({base:Router.state().base, n:Router.state().stack.length, st:document.getElementById('page-cat').dataset.state, det:!document.getElementById('gsPanel').hidden})")
    ev("history.forward(); true"); wait_ms(450)
    s3 = ev("({t:Router.state().stack.map(l=>l.t+':'+(l.view||'')).join(), sel:_flowSel, vis:Category.isFlowVisible()})")
    check('FL-4 [%s] Detail → 完整持股異動：同檔、只剩 folder(flow)、不留 Detail' % base, ok_btn and s1['base'] == 'cat' and s1['t'] == 'folder:flow' and s1['sel'] == fcode and s1['vis'] and not s1['det'], s1)
    check('FL-4 [%s] Back → 分類總覽（不回 Detail）；Forward → 同檔持股異動' % base, s2['base'] == 'cat' and s2['n'] == 0 and s2['st'] == 'overview' and not s2['det'] and s3['t'] == 'folder:flow' and s3['sel'] == fcode and s3['vis'], (s2, s3))
    ev("Router.toBase({base:'home'}); true"); wait_ms(250)
# FL-6（FD-1～FD-6）由 category_test.py 保留並執行

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, [e['params']['exceptionDetails'].get('exception', {}).get('description', '')[:160] for e in exc][:3])
ev("localStorage.removeItem(%s); true" % json.dumps(KEY))
fails = [r for r in results if r[1] is False]
print('\nTOTAL %d  PASS %d  FAIL %d  DEFER %d' % (len(results), len(results) - len(fails), len(fails), len(DEFER)))
for d in DEFER: print('  DEFER: ' + d)
ws.close()
