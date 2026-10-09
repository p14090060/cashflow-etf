"""Detail 持股分頁日期提示（與 flow.js D1～D3 同一套語意）。

執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
- fetched:false：「本次自動抓取未取得新資料，以下沿用先前保存的資料（資料日 X）」，不推測原因
- flow_to 晚於 data_date：中性並列日期，不說「持股無異動」也不說「尚未有新的 PCF」
- 條件互斥；金額換算日 YYYY-MM-DD
- 舊快取 flow.js（沒有 _flowYmd）配新 detail.js：持股分頁不得掛掉
"""
import sys, json, re
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

ev("clearInterval(_pollTimer); true")
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowStatus==='ok'||Date.now()-t>15000){clearInterval(i);r(1)}},100)})", True)
codes = ev("Object.keys(_flowData.etfs).filter(k=>ETFS.some(e=>e.code===k)).sort()")

def detail(code):
    ev("openDetail(%s); detailTab('holdings'); true" % json.dumps(code)); wait_ms(150)
    r = ev("""(()=>{const p=document.querySelector('[data-pane=holdings]'); if(!p) return null;
      const rows={}; p.querySelectorAll('.dt-row').forEach(x=>{const k=x.firstElementChild&&x.firstElementChild.textContent.trim(); if(k) rows[k]=x.lastElementChild.textContent.trim()});
      return {notes:[...p.querySelectorAll('.dt-note')].map(x=>x.textContent.trim()), rows:rows, btn:!!p.querySelector('.gs-flow-btn')}})()""")
    ev("closeDetail(); true"); wait_ms(80)
    return r
def flowtip(code):
    ev("Router.openFlow(%s); true" % json.dumps(code)); wait_ms(250)
    ev("flowSelect(%s); true" % json.dumps(code)); wait_ms(80)
    t = ev("document.getElementById('flowTip').textContent")
    ev("history.back(); true"); wait_ms(250)
    return t

NOCHG, NOTUPD, D2, D1 = '持股無異動', '尚未有新的 PCF', '本次自動抓取未取得新資料，以下沿用先前保存的資料', '早於異動比較區間'
def semantic(text, r):
    """依欄位回傳該文字的問題清單（Detail 與 Flow 共用同一份語意規則）"""
    bad = []
    ahead = bool(r.get('flow_to') and r.get('data_date') and r['flow_to'] > r['data_date'])
    if r.get('fetched') is False:
        if D2 not in text or ('資料日 %s' % (r.get('data_date') or '-')) not in text: bad.append('D2 缺')
    if '異常' in text: bad.append('推測異常')
    if ahead:
        if D1 not in text: bad.append('D1 缺')
        if NOCHG in text or NOTUPD in text: bad.append('D1 矛盾')
    elif r.get('fetched') is not False:
        if r.get('flow_to') and r.get('data_date') and r['flow_to'] < r['data_date']:
            if NOCHG not in text or r['data_date'] not in text: bad.append('歷史異動缺')
            if NOTUPD in text: bad.append('歷史異動疊加')
        elif r.get('reason') == 'not_updated' and r.get('advanced') is False and NOTUPD not in text: bad.append('not_updated 缺')
    return bad

rows = ev("Object.fromEntries(Object.entries(_flowData.etfs).map(([k,e])=>[k,{data_date:e.data_date,flow_from:e.flow_from,flow_to:e.flow_to,price_date:e.price_date,fetched:e.fetched,advanced:e.advanced,reason:e.reason,last_change_date:e.last_change_date}]))")
dv = {c: detail(c) for c in codes}
if '--dump' in sys.argv:
    for c in codes: print('DUMP', c, json.dumps(dv[c], ensure_ascii=False))
bad_sem, bad_fmt, bad_pair = {}, {}, {}
for c in codes:
    d = dv[c]; r = rows[c]; text = '　'.join(d['notes'])
    b = semantic(text, r)
    if b: bad_sem[c] = (b, d['notes'])
    pd = d['rows'].get('金額換算日')
    if r.get('price_date') and (pd is None or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', pd)): bad_fmt[c] = pd
check('Detail 持股：%d 檔提示依欄位語意正確（D1／D2／歷史異動／not_updated，互斥不矛盾）' % len(codes), not bad_sem, bad_sem)
check('Detail 持股：金額換算日皆為 YYYY-MM-DD', not bad_fmt, bad_fmt)
check('Detail 持股：資料日／最近持股異動日照原始欄位', all(dv[c]['rows'].get('資料日') == (rows[c]['data_date'] or '--') and
      (not rows[c]['last_change_date'] or dv[c]['rows'].get('最近持股異動日') == rows[c]['last_change_date']) for c in codes))
for c in ('00403A', '00996A'):
    if c not in codes: print('   SKIP 入口一致性 %s：正式資料已無此檔' % c); continue
    ft = flowtip(c); dt = '　'.join(dv[c]['notes'])
    print('   %s Detail：%s\n   %s Flow  ：%s' % (c, dt, c, ft))
    check('入口一致 %s：Detail 與持股異動頁都通過同一套語意規則' % c, not semantic(dt, rows[c]) and not semantic(ft, rows[c]), (semantic(dt, rows[c]), semantic(ft, rows[c])))

# ── 合成情境：借一檔真的主動式 ETF，暫時改它的 _flowData 欄位（不碰 JSON），測完還原
host = codes[0]
orig = ev("JSON.stringify(_flowData.etfs[%s])" % json.dumps(host))
BASE_E = {'name': '測試', 'issuer': '測試', 'holdings': 10, 'data_date': '2026-10-08', 'advanced': True, 'reason': 'ok', 'fetched': True,
          'flow_from': '2026-10-07', 'flow_to': '2026-10-08', 'price_date': '20261008', 'no_price': [], 'scale_pct': None,
          'buy': 3e8, 'sell': -2e8, 'changed': 2, 'last_change_date': '2026-10-08',
          'flow': [{'code': '2330', 'name': '台積電', 'amount': 3e8}, {'code': '2317', 'name': '鴻海', 'amount': -2e8}]}
def synth(**kw):
    e = dict(BASE_E, **kw)
    for k in [k for k, v in e.items() if v is None and k in ('data_date', 'flow_from', 'flow_to', 'price_date')]: e.pop(k)
    ev("_flowData.etfs[%s] = %s; true" % (json.dumps(host), json.dumps(e, ensure_ascii=False)))
    return detail(host), e
cases = [
    ('一般抓取成功', {}, lambda t, d: '⚠' not in t and d['rows'].get('金額換算日') == '2026-10-08'),
    ('真正抓取失敗（舊資料）', dict(fetched=False, data_date='2026-09-30', flow_from='2026-09-29', flow_to='2026-09-30', advanced=False, reason='not_updated'),
     lambda t, d: D2 in t and '資料日 2026-09-30' in t and NOTUPD not in t and NOCHG not in t and '異常' not in t),
    ('歷史異動', dict(data_date='2026-10-08', flow_from='2026-10-01', flow_to='2026-10-02', advanced=False, reason='not_updated', price_date='20261002'),
     lambda t, d: '最新 PCF（資料日 2026-10-08）持股無異動' in t and NOTUPD not in t and d['rows'].get('金額換算日') == '2026-10-02'),
    ('一般 not_updated', dict(advanced=False, reason='not_updated'), lambda t, d: '2026-10-08 之後尚未有新的 PCF' in t and NOCHG not in t),
    ('日期矛盾（D1）', dict(data_date='2026-10-07', flow_from='2026-10-07', flow_to='2026-10-08', advanced=False, reason='not_updated'),
     lambda t, d: '投信公告的資料日（2026-10-07）早於異動比較區間（2026-10-07 → 2026-10-08）' in t and NOCHG not in t and NOTUPD not in t),
    ('抓取失敗＋日期矛盾', dict(fetched=False, data_date='2026-10-07', flow_from='2026-10-07', flow_to='2026-10-08'), lambda t, d: D2 in t and D1 in t and NOCHG not in t),
    ('缺 data_date', dict(data_date=None, fetched=False), lambda t, d: D2 in t and '資料日 -' in t and d['rows'].get('資料日') == '--'),
    ('缺 flow_to／flow_from', dict(flow_to=None, flow_from=None, advanced=False, reason='not_updated'), lambda t, d: NOTUPD in t and D1 not in t),
    ('缺 price_date', dict(price_date=None), lambda t, d: '金額換算日' not in d['rows']),
    ('price_date 已是 YYYY-MM-DD', dict(price_date='2026-10-08'), lambda t, d: d['rows'].get('金額換算日') == '2026-10-08'),
]
for name, kw, ok in cases:
    d, e = synth(**kw); t = '　'.join(d['notes'])
    check('情境 %s' % name, d is not None and d['btn'] and ok(t, d), (d['notes'], d['rows'].get('金額換算日')))
ev("_flowData.etfs[%s] = JSON.parse(%s); true" % (json.dumps(host), json.dumps(orig)))

# ── 快取混用：新 detail.js 配上沒有 _flowYmd 的舊 flow.js（git 73b83734 版本），持股分頁仍要畫得出來
OLD_FLOW = __import__('subprocess').run(['git', 'show', '73b8373417ab0fa292528b36eaff4473d998a1e0:js/flow.js'], capture_output=True).stdout
if OLD_FLOW and b'_flowYmd' not in OLD_FLOW:
    import base64
    cdp('Network.enable'); cdp('Network.setCacheDisabled', {'cacheDisabled': True})
    cdp('Fetch.enable', {'patterns': [{'urlPattern': '*js/flow.js*', 'requestStage': 'Request'}]})
    exc0 = len([e for e in events if e.get('method') == 'Runtime.exceptionThrown'])
    ws.send(json.dumps({'id': 99001, 'method': 'Page.navigate', 'params': {'url': BASE}}))
    t0 = time.time(); served = False
    while time.time() - t0 < 20 and not served:
        m = json.loads(ws.recv())
        if m.get('method') == 'Fetch.requestPaused':
            ws.send(json.dumps({'id': 99002, 'method': 'Fetch.fulfillRequest', 'params': {'requestId': m['params']['requestId'], 'responseCode': 200,
                    'responseHeaders': [{'name': 'Content-Type', 'value': 'application/javascript'}], 'body': base64.b64encode(OLD_FLOW).decode()}}))
            served = True
        else:
            events.append(m)
    cdp('Fetch.disable')
    ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if((typeof ETFS!=='undefined'&&ETFS.length>0&&_flowStatus==='ok')||Date.now()-t>30000){clearInterval(i);r(1)}},200)})", True)
    ev("clearInterval(_pollTimer); true")
    has = ev("typeof _flowYmd")
    c = '00403A' if '00403A' in codes else codes[0]
    d = detail(c)
    exc = [e for e in events[exc0:] if e.get('method') == 'Runtime.exceptionThrown']
    check('快取混用（舊 flow.js 無 _flowYmd）：Detail 持股分頁正常、退回原始日期、無例外', served and has == 'undefined' and d is not None and d['btn']
          and d['rows'].get('金額換算日') == rows[c]['price_date'] and not exc, (served, has, d and d['rows'].get('金額換算日'), len(exc)))
    events[:] = [e for e in events if not (e.get('method') == 'Runtime.exceptionThrown' and e in exc)]
else:
    print('   SKIP 快取混用：取不到舊版 flow.js')

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'))
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
