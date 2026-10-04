import sys, json
src=open('tests/browser/detail_ui_test.py',encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])
check('flow status ok', ev("_flowStatus") == 'ok', ev("_flowStatus"))
for pg in ['today','div','yt','check','rank','today']:
    ev("switchPage('%s'); true" % pg); wait_ms(150)
    if pg == 'check':   # Phase 3：持股異動移入 分類 → 主動式
        check('R switch page check active (Phase 3: 分類 → 主動式 持股異動)', ev("document.getElementById('page-cat').classList.contains('active') && Category.isFlowVisible()") is True)
    else:
        check('R switch page %s active' % pg, ev("document.getElementById('page-%s').classList.contains('active')" % pg) is True)
ev("selChip('0056'); true"); wait_ms(100)
check('R page-div chip calc uses 0056', ev("selETF.code") == '0056' and '天後' in (ev("document.getElementById('calcOut').innerText") or ''))
ev("switchPage('rank'); true"); wait_ms(100)
ev("const f=document.getElementById('rankFind'); f.value='0050'; f.dispatchEvent(new Event('input')); true"); wait_ms(150)
check('R rank find 0050 message', '0050' in (ev("document.getElementById('rankFindMsg').innerText") or ''))
ev("switchPage('check'); true"); wait_ms(200)
check('R treemap drawn', (ev("document.getElementById('treemap').children.length") or 0) > 0)
ev("switchPage('today'); true"); wait_ms(100)
ev("const i=document.getElementById('gsearch'); i.value='高股息'; i.dispatchEvent(new Event('input')); true"); wait_ms(150)
check('R search dropdown shows results', (ev("document.querySelectorAll('#gsearchList .gs-row').length") or 0) > 0)
ev("gsPick('0050'); true"); wait_ms(200)
ev("const i=document.getElementById('gsearch'); i.value='0056'; i.dispatchEvent(new Event('input')); true"); wait_ms(150)
check('R typing keeps detail open (D2)', ev("!document.getElementById('gsPanel').hidden") is True)
ev("gsClear(); closeDetail(); true"); wait_ms(300)
exc=[e for e in events if e.get('method')=='Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'), (e['params']['exceptionDetails'].get('exception',{}) or {}).get('description','')[:160])
check('R no uncaught exceptions', len(exc)==0, len(exc))
fails=[r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results)-len(fails), len(fails)))
ws.close()
