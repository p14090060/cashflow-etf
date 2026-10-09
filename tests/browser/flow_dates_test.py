"""持股異動日期提示（D1～D3）：flowTip／flowCover 的文案依 active_flow.json 欄位如實呈現。

執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
D1：flow_to 晚於 data_date 時，不得同時宣稱「最新 PCF 持股無異動」。
D2：fetched:false 保留「本次未抓到」的事實並標出沿用的資料日，不推測原因。
D3：金額換算日 price_date（YYYYMMDD）顯示為 YYYY-MM-DD。
"""
import sys, json, re
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

ev("clearInterval(_pollTimer); true")
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowData||Date.now()-t>15000){clearInterval(i);r(1)}},100)})", True)
ev("switchPage('tools'); true"); wait_ms(200)
codes = ev("Object.keys(_flowData.etfs).sort()")
ev("openFlow(%s); true" % json.dumps(codes[0])); wait_ms(500)

def view(code):
    ev("flowSelect(%s); true" % json.dumps(code)); wait_ms(80)
    return ev("({tip:document.getElementById('flowTip').textContent, cover:document.getElementById('flowCover').textContent,"
              " meta:document.getElementById('flowMeta').textContent, cells:document.querySelectorAll('#treemap .tm-cell').length})")

NOCHANGE = '持股無異動'
# ── 正式資料：逐檔依欄位判斷該出現的提示（不寫死代碼，資料變了也照欄位驗）
rows = ev("Object.fromEntries(Object.entries(_flowData.etfs).map(([k,e])=>[k,{dd:e.data_date,ft:e.flow_to,ff:e.flow_from,pd:e.price_date,f:e.fetched,adv:e.advanced,r:e.reason,n:(e.flow||[]).length}]))")
views = {c: view(c) for c in codes}
if '--dump' in sys.argv:
    for c in codes: print('DUMP', c, json.dumps(views[c], ensure_ascii=False))
bad_d1, bad_d2, bad_d3, bad_hist, bad_cells = [], [], [], [], []
for c in codes:
    r, v = rows[c], views[c]
    ahead = bool(r['ft'] and r['dd'] and r['ft'] > r['dd'])
    if ahead and (NOCHANGE in v['tip'] or '之後尚未有新的 PCF' in v['tip'] or '早於異動比較區間' not in v['tip']): bad_d1.append((c, v['tip']))
    if r['f'] is False and ('本次自動抓取未取得新資料' not in v['tip'] or ('資料日 %s' % r['dd']) not in v['tip'] or '異常' in v['tip']): bad_d2.append((c, v['tip']))
    if re.search(r'\d{8}', v['cover']) or (r['pd'] and ('%s-%s-%s' % (r['pd'][:4], r['pd'][4:6], r['pd'][6:])) not in v['cover'] and re.fullmatch(r'\d{8}', r['pd'])): bad_d3.append((c, v['cover']))
    if r['f'] is not False and not ahead and r['ft'] and r['dd'] and r['ft'] < r['dd'] and ('最新 PCF（%s）持股無異動' % r['dd']) not in v['tip']: bad_hist.append((c, v['tip']))
    if r['n'] and not v['cells']: bad_cells.append(c)
check('D1 正式資料：flow_to 晚於 data_date 的 %d 檔改中性提示、不宣稱無異動' % sum(1 for r in rows.values() if r['ft'] and r['dd'] and r['ft'] > r['dd']), not bad_d1, bad_d1)
check('D2 正式資料：fetched:false 的 %d 檔標「本次自動抓取未取得新資料」＋沿用資料日，不推測原因' % sum(1 for r in rows.values() if r['f'] is False), not bad_d2, bad_d2)
check('D3 正式資料：%d 檔封面金額換算日皆為 YYYY-MM-DD、無 8 位數日期' % len(codes), not bad_d3, bad_d3)
check('歷史異動：flow_to 早於 data_date 的檔照舊顯示「最新 PCF（資料日）持股無異動」', not bad_hist, bad_hist)
check('有 flow 的檔 treemap 照常畫出', not bad_cells, bad_cells)
if '00403A' in views: print('   00403A', json.dumps(views['00403A'], ensure_ascii=False))
if '00996A' in views: print('   00996A', json.dumps(views['00996A'], ensure_ascii=False))

# ── 合成情境：直接塞進 _flowData，驗每種組合的文案（不碰 JSON 檔）
BASE_E = {'name': '測試', 'issuer': '測試', 'holdings': 10, 'data_date': '2026-10-08', 'advanced': True, 'reason': 'ok', 'fetched': True,
          'flow_from': '2026-10-07', 'flow_to': '2026-10-08', 'price_date': '20261008', 'no_price': [], 'scale_pct': None,
          'buy': 3e8, 'sell': -2e8, 'changed': 2, 'flow': [{'code': '2330', 'name': '台積電', 'amount': 3e8}, {'code': '2317', 'name': '鴻海', 'amount': -2e8}]}
def synth(**kw):
    e = dict(BASE_E, **kw)
    ev("_flowData.etfs['ZZ99A'] = %s; true" % json.dumps(e, ensure_ascii=False))
    return view('ZZ99A')
v = synth()
check('情境 一般抓取成功（data_date＝flow_to）：無日期警示，金額日 2026-10-08', '⚠' not in v['tip'] and '⏳' not in v['tip'] and '2026-10-08 收盤價' in v['cover'] and v['cells'] == 2, v)
v = synth(fetched=False, data_date='2026-09-30', flow_from='2026-09-29', flow_to='2026-09-30', price_date='20260930')
check('情境 真正抓取失敗且資料舊：保留未抓到事實＋舊資料日，不出現「最新」「異常」推測', '本次自動抓取未取得新資料' in v['tip'] and '資料日 2026-09-30' in v['tip']
      and '最新 PCF' not in v['tip'] and '異常' not in v['tip'] and v['cells'] == 2, v)
v = synth(data_date='2026-10-08', flow_from='2026-10-01', flow_to='2026-10-02', advanced=False, reason='not_updated', price_date='20261002')
check('情境 歷史異動（flow_to 早於 data_date）：「最新 PCF（2026-10-08）持股無異動，以下為最近一次調整」', '最新 PCF（2026-10-08）持股無異動，以下為最近一次調整' in v['tip'] and '2026-10-02 收盤價' in v['cover'], v)
v = synth(data_date='2026-10-08', advanced=False, reason='not_updated')
check('情境 資料日未前進（flow_to＝data_date、not_updated）：「2026-10-08 之後尚未有新的 PCF」', '2026-10-08 之後尚未有新的 PCF' in v['tip'], v)
v = synth(data_date='2026-10-07', flow_from='2026-10-07', flow_to='2026-10-08', advanced=False, reason='not_updated')
check('情境 資料日落後於比較區間（D1）：中性並列日期，不說無異動也不說尚未有新 PCF', '早於異動比較區間（2026-10-07 → 2026-10-08）' in v['tip']
      and NOCHANGE not in v['tip'] and '尚未有新的 PCF' not in v['tip'] and v['cells'] == 2, v)
v = synth(fetched=False, data_date='2026-10-07', flow_from='2026-10-07', flow_to='2026-10-08')
check('情境 抓取失敗＋日期不一致：兩項事實都講', '本次自動抓取未取得新資料' in v['tip'] and '早於異動比較區間' in v['tip'], v)
v = synth(price_date='2026-10-08')
check('情境 price_date 已是 YYYY-MM-DD：原樣顯示', '2026-10-08 收盤價' in v['cover'], v)
ev("delete _flowData.etfs['ZZ99A']; true")

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'))
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
