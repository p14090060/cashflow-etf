import json, time, urllib.request, websocket

BASE = 'http://127.0.0.1:8765/index.html'
results = []
events = []

def targets():
    return json.load(urllib.request.urlopen('http://127.0.0.1:9223/json'))

page = [t for t in targets() if t['type'] == 'page'][0]
ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=40)
_id = 0

def cdp(method, params=None):
    global _id
    _id += 1
    mid = _id
    ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == mid:
            return msg
        events.append(msg)

def ev(expr, await_p=False):
    r = cdp('Runtime.evaluate', {'expression': expr, 'awaitPromise': await_p, 'returnByValue': True})
    if 'exceptionDetails' in r.get('result', {}):
        return ('EXC', r['result']['exceptionDetails'].get('text'))
    return r.get('result', {}).get('result', {}).get('value')

def check(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    print(('PASS ' if cond else 'FAIL ') + name + ('  -- ' + str(detail) if detail else ''))

def sleep_js(ms):
    return 'new Promise(r=>setTimeout(r,%d))' % ms

def wait_ms(ms):
    ev(sleep_js(ms), True)

cdp('Runtime.enable')
cdp('Page.enable')

def load_page():
    cdp('Page.navigate', {'url': BASE})
    time.sleep(1.5)
    n = ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if((typeof ETFS!=='undefined'&&ETFS.length>0)||Date.now()-t>30000){clearInterval(i);r(typeof ETFS!=='undefined'?ETFS.length:-1)}},200)})", True)
    ev("window.__pop=0; window.addEventListener('popstate',()=>{window.__pop++});")
    return n

n = load_page()
check('T0 data loaded', isinstance(n, int) and n > 0, 'ETFS=%s' % n)

exc_before = len([e for e in events if e.get('method') == 'Runtime.exceptionThrown'])

# ── T2 開啟 0050：3 個 tab（被動型無成分）
ev("gsPick('0050'); true")
wait_ms(300)
check('T2 detail open', ev("!document.getElementById('gsPanel').hidden") is True)
check('T2 title has 0050', 'NOT' != ev("document.getElementById('gsPanelTitle').textContent.includes('0050')") and ev("document.getElementById('gsPanelTitle').textContent.includes('0050')") is True)
check('T2 0050 has 3 tabs', ev("[...document.querySelectorAll('.dt-tab')].filter(b=>!b.hidden).length") == 3)

# ── T3 0050 配息：E1 依歷史推算，不得出現 fallback 0.30 / 90 天
ev("detailTab('dividend'); true")
wait_ms(200)
dv = ev("document.querySelector('[data-pane=dividend]').innerText")
print('   0050 dividend pane:\n   ' + str(dv).replace('\n', '\n   '))
check('T3 0050 no fallback 0.30 / 90天', dv and '0.30' not in dv and '90 天' not in dv)
check('T3 0050 labelled 依歷史推算 + 未經官方核實', '依歷史推算' in dv and '未經官方核實' in dv)

# ── T4 00939 官方公告 2026-10-05
ev("gsPick('00939'); detailTab('dividend'); true")
wait_ms(200)
dv = ev("document.querySelector('[data-pane=dividend]').innerText") or ''
check('T4 00939 official date 2026-10-05', '2026-10-05' in dv and '官方公告' in dv, dv[:120].replace('\n', ' | '))
check('T4 00939 date not from div_next 11-01', '2026-11-01' not in dv)

# ── T5 009818 資料不足，不得顯示 0.30
has5 = ev("ETFS.some(e=>e.code==='009818')")
if has5:
    ev("gsPick('009818'); detailTab('dividend'); true")
    wait_ms(200)
    dv = ev("document.querySelector('[data-pane=dividend]').innerText") or ''
    check('T5 009818 待公告/資料不足, no 0.30', ('待公告' in dv or '資料不足' in dv) and '0.30' not in dv and '90 天' not in dv, dv[:100].replace('\n', ' | '))
else:
    check('T5 009818 present in data', False, 'not in ETFS (data changed?)')

# ── T6 00981A 有成分 tab
ev("gsPick('00981A'); true")
wait_ms(200)
check('T6 00981A has 4 tabs', ev("[...document.querySelectorAll('.dt-tab')].filter(b=>!b.hidden).length") == 4)
ev("detailTab('holdings'); true")
wait_ms(150)
hp = ev("document.querySelector('[data-pane=holdings]').innerText") or ''
check('T6 holdings pane has summary', ('持股' in hp or '投信' in hp), hp[:80].replace('\n', ' | '))

# ── T7 計算機股數保留 + 不污染 selETF
ev("gsPick('0050'); detailTab('dividend'); true")
wait_ms(200)
sel_before = ev("selETF && selETF.code")
ev("const i=document.getElementById('dtSharesIn'); i.value='7'; i.dispatchEvent(new Event('input')); true")
ev("detailOnMarketUpdate(); true")
wait_ms(150)
val = ev("document.getElementById('dtSharesIn').value")
out = ev("document.getElementById('dtCalcOut').innerText") or ''
check('T7 shares kept after refresh', val == '7', val)
check('T7 calc output updated to 7 張', '7 張市值' in out, out[:80].replace('\n', ' | '))
check('T7 selETF untouched', ev("selETF && selETF.code") == sel_before, sel_before)

# ── T8 ✕ 只產生一次 back；popstate 不再 back
ev("window.__pop=0; true")
ev("document.querySelector('#gsPanel .gs-panel-hd button').click(); true")
wait_ms(400)
check('T8 X button hides detail', ev("document.getElementById('gsPanel').hidden") is True)
check('T8 exactly one popstate', ev("window.__pop") == 1, ev("window.__pop"))
check('T8 pending back cleared', ev("_pendingPop") == 0)

# ── T9 Esc（input + document）只消耗一次
ev("gsPick('0050'); true")
wait_ms(200)
ev("window.__pop=0; true")
ev("const s=document.getElementById('gsearch'); s.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); true")
wait_ms(400)
check('T9 Esc closes', ev("document.getElementById('gsPanel').hidden") is True)
check('T9 Esc single pop', ev("window.__pop") == 1, ev("window.__pop"))

# ── T10 瀏覽器返回鍵：只關一次，不再 back
ev("gsPick('0050'); true")
wait_ms(200)
ev("window.__pop=0; true")
ev("history.back(); true")
wait_ms(500)
check('T10 system back closes detail', ev("document.getElementById('gsPanel').hidden") is True)
check('T10 single popstate, no extra back', ev("window.__pop") == 1, ev("window.__pop"))
check('T10 state null after back', ev("history.state === null || !history.state.etfDetail"))

# ── T11 底部導覽切頁：關閉 Detail，且只一次 back
ev("gsPick('0050'); true")
wait_ms(200)
ev("window.__pop=0; true")
ev("switchPage('div'); true")
wait_ms(400)
check('T11 nav closes detail', ev("document.getElementById('gsPanel').hidden") is True)
check('T11 nav opened page-div', ev("document.getElementById('page-div').classList.contains('active')") is True)
check('T11 nav single popstate', ev("window.__pop") == 1, ev("window.__pop"))
ev("switchPage('today'); true")

# ── T12 切換另一檔：replaceState，不新增 entry
ev("gsPick('0050'); true")
wait_ms(200)
L = ev("history.length")
ev("gsPick('0056'); true")
wait_ms(200)
check('T12 switch ETF no new entry', ev("history.length") == L, '%s vs %s' % (ev("history.length"), L))
check('T12 state code updated', ev("history.state && history.state.code") == '0056', ev("history.state && history.state.code"))
check('T12 title 0056', ev("document.getElementById('gsPanelTitle').textContent.includes('0056')") is True)
ev("document.querySelector('#gsPanel .gs-panel-hd button').click(); true")
wait_ms(400)

# ── T13 成分按鈕：關閉 Detail、跳主動頁，只一次 back
ev("gsPick('00981A'); true")
wait_ms(200)
ev("window.__pop=0; true")
ev("detailGoFlow('00981A'); true")
wait_ms(400)
check('T13 flow page active', ev("document.getElementById('page-check').classList.contains('active')") is True)
check('T13 detail closed', ev("document.getElementById('gsPanel').hidden") is True)
check('T13 single popstate', ev("window.__pop") == 1, ev("window.__pop"))
ev("switchPage('today'); true")

# ── T14 0% 不當缺資料
z = ev("(ETFS.find(e=>e.ret1y===0)||{}).code")
if z:
    ev("gsPick('%s'); detailTab('perf'); true" % z)
    wait_ms(200)
    pf = ev("document.querySelector('[data-pane=perf]').innerText") or ''
    check('T14 0%% shown as 0.0%% (%s)' % z, '0.0%' in pf, pf[:80].replace('\n', ' | '))
    ev("document.querySelector('#gsPanel .gs-panel-hd button').click(); true")
    wait_ms(300)
else:
    check('T14 no ret1y==0 ETF in current data (skipped)', True, 'n/a')

# ── T15 重整後還原 Detail（同一代碼，無幽靈 entry）
ev("gsPick('0050'); true")
wait_ms(300)
cdp('Page.reload', {'ignoreCache': False})
time.sleep(1.5)
n2 = ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if((typeof ETFS!=='undefined'&&ETFS.length>0)||Date.now()-t>30000){clearInterval(i);r(ETFS.length)}},200)})", True)
wait_ms(400)
ev("window.__pop=0; window.addEventListener('popstate',()=>{window.__pop++}); true")
check('T15 reload restores detail', ev("!document.getElementById('gsPanel').hidden") is True and ev("document.getElementById('gsPanelTitle').textContent.includes('0050')") is True)
ev("document.querySelector('#gsPanel .gs-panel-hd button').click(); true")
wait_ms(400)
check('T15 close after restore', ev("document.getElementById('gsPanel').hidden") is True)

# ── T16 還原後關閉，history.state 應為非 detail（基底）
check('T16 base state after restored close', ev("history.state === null || !history.state.etfDetail") is True)

# ── T17 / T18 假日期（記憶體內）：同一個同步 evaluate 內設定、檢查、還原
n3 = load_page()
check('T17 reloaded for fixtures', isinstance(n3, int) and n3 > 0)
r17 = ev("""(()=>{
  const c=CALENDAR.find(c=>c.code==='00939'); const orig=c.iso_date; c.iso_date='2026-10-01';
  gsPick('00939'); detailTab('dividend');
  const dv=document.querySelector('[data-pane=dividend]').innerText;
  const out=document.getElementById('dtCalcOut').innerText;
  c.iso_date=orig; detailOnMarketUpdate(); closeDetail();
  return JSON.stringify({dv, out});
})()""")
import json as _j
r17 = _j.loads(r17) if isinstance(r17, str) else {'dv':'','out':''}
check('T17 official expired shows 已過, no countdown', '已過' in r17['dv'] and '天後' not in r17['dv'])
check('T17 official expired calc disabled', '計算停用' in r17['out'], r17['out'][:40].replace('\n',' | '))

r18 = ev("""(()=>{
  const e=ETFS.find(e=>e.code==='0050'); const orig=e.div_next; e.div_next='2026-10-01';
  gsPick('0050'); detailTab('dividend');
  const dv=document.querySelector('[data-pane=dividend]').innerText;
  const out=document.getElementById('dtCalcOut').innerText;
  e.div_next=orig; detailOnMarketUpdate(); closeDetail();
  return JSON.stringify({dv, out});
})()""")
r18 = _j.loads(r18) if isinstance(r18, str) else {'dv':'','out':''}
check('T18 projected expired shows 推算日已過, calc disabled', '推算日已過' in r18['dv'] and '計算停用' in r18['out'])

# ── T19 closeDetail 重複呼叫只 back 一次
ev("gsPick('0050'); true")
wait_ms(200)
ev("window.__pop=0; true")
ev("closeDetail(); closeDetail(); closeDetail(); true")
wait_ms(400)
check('T19 repeated closeDetail => one popstate', ev("window.__pop") == 1, ev("window.__pop"))
check('T19 pending cleared', ev("_pendingPop") == 0)

# ── 錯誤蒐集
exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc[exc_before:]:
    print('   EXC:', e['params']['exceptionDetails'].get('text'), e['params']['exceptionDetails'].get('exception', {}).get('description', '')[:160])
check('no uncaught exceptions during tests', len(exc) - exc_before == 0, len(exc) - exc_before)

fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
