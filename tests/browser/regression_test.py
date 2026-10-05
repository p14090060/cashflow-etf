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
# Phase 5 §6.1：舊配息頁 B-1 計算機退役 → 配息頁只剩日曆；張數試算改驗正式入口 Detail 配息分頁
ev("switchPage('div'); true"); wait_ms(150)
check('R page-div calendar only (B-1 calculator removed)', ev("document.getElementById('page-div').classList.contains('active') && !document.getElementById('sharesIn') && !document.getElementById('calcOut') && !document.getElementById('chips') && document.getElementById('calList').children.length > 0") is True)
ev("switchPage('today'); true"); wait_ms(100)
ev("gsPick('0056'); true"); wait_ms(300)
ev("detailTab('dividend'); true"); wait_ms(150)
def calc_at(n):
    ev("{const i=document.getElementById('dtSharesIn'); i.value='%d'; i.dispatchEvent(new Event('input'));} true" % n); wait_ms(100)
    return ev("""(()=>{const e=ETFS.find(x=>x.code==='0056'); const dv=_dvView(e,_dtCal());
      const t=document.getElementById('dtCalcOut').innerText; const f=v=>Math.round(v).toLocaleString();
      return {calc:!!dv.calc, txt:t, once:f(dv.amount*%d*1000), mv:f(e.price*%d*1000),
              ann:(e.yld_verified===true&&e.yld>0)?f(e.yld/100*e.price*%d*1000):null};})()""" % (n, n, n))
c1, c7 = calc_at(1), calc_at(7)
check('R Detail 0056 dividend calc available (migrated from B-1)', c1['calc'] and c7['calc'], (c1, c7))
for lab, c, n in (('1', c1, 1), ('7', c7, 7)):
    check('R Detail 0056 calc %s 張: 單次可領＝amount×張×1000' % lab, ('單次可領' in c['txt']) and (c['once'] + ' 元') in c['txt'], c)
    check('R Detail 0056 calc %s 張: %d 張市值約＝price×張×1000' % (lab, n), ('%d 張市值約' % n) in c['txt'] and (c['mv'] + ' 元') in c['txt'], c)
    check('R Detail 0056 calc %s 張: 預估年化領回連動（有核實殖利率時）' % lab, c['ann'] is None or (c['ann'] + ' 元') in c['txt'], c)
check('R Detail 0056 calc 1 → 7 changes amounts', c1['once'] != c7['once'] and c1['mv'] != c7['mv'], (c1, c7))
cd = ev("""(()=>{const e=ETFS.find(x=>x.code==='0056'); const dv=_dvView(e,_dtCal());
  const t=document.getElementById('gsPanel').innerText; return {future: !!(dv.date && !dv.past), ok: /（\\d+ 天後）|（今日）/.test(t)};})()""")
check('R Detail 0056 配息資訊倒數（除息日在未來時顯示 N 天後／今日）', (not cd['future']) or cd['ok'], cd)
ev("closeDetail(); true"); wait_ms(300)
# MG-1／MG-3（LAZY_WATCHLIST 待首頁 checkpoint 移除後再加入 MG-3）
check('MG-3 retired globals are undefined (selETF/renderChips/calcUpdate/selChip/lookupToday/lookupCustom/renderSignalCard)',
      ev("['selETF','renderChips','calcUpdate','selChip','lookupToday','lookupCustom','renderSignalCard'].every(n=>{try{return eval('typeof '+n)==='undefined'}catch(e){return true}})") is True)
check('MG-1 ETFS／CALENDAR available from state.js', ev("Array.isArray(ETFS) && ETFS.length > 0 && Array.isArray(CALENDAR) && !!document.querySelector('script[src^=\\'js/state.js\\']') && !document.querySelector('script[src*=\\'calc.js\\'],script[src*=\\'lookup.js\\']')") is True)
check('MG home A-4 single-ETF lookup removed', ev("!document.getElementById('todayCode') && !document.getElementById('todayResult')") is True)
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
