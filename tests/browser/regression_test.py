import sys, json
src=open('tests/browser/detail_ui_test.py',encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])
check('flow status ok', ev("_flowStatus") == 'ok', ev("_flowStatus"))
YT_URL = 'https://www.youtube.com/@CashFlowDataRecorder'
# ── YT-1／YT-2（PHASE5_PLAN §4、G1）：Header YouTube 外部連結；page-yt 與舊入口退役 ──
ev("switchPage('today'); true"); wait_ms(150)
yt = ev("""(()=>{const a=document.getElementById('hdrYt'); if(!a) return null; const r=a.getBoundingClientRect();
  return {tag:a.tagName, href:a.getAttribute('href'), target:a.target, rel:a.rel, aria:a.getAttribute('aria-label'), w:r.width, h:r.height,
          inHdr: !!a.closest('.app-hdr .topbar')}})()""")
check('YT-1 Header YouTube：a 連結、在 Header 標題列、≥ 44×44', yt and yt['tag'] == 'A' and yt['inHdr'] and yt['w'] >= 44 and yt['h'] >= 44, yt)
check('YT-1 href＝頻道、target=_blank、rel 含 noopener、aria-label', yt and yt['href'] == YT_URL and yt['target'] == '_blank' and 'noopener' in yt['rel'].split() and yt['aria'] == '金流黑盒子 YouTube 頻道', yt)
h0 = ev("history.length"); s0 = ev("JSON.stringify(Router.state())")
ev("window.__opened=[]; window.__origOpen=window.open; window.open=function(u,t,f){ window.__opened.push([u,t,f]); return null; }; true")
ev("document.getElementById('hdrYt').addEventListener('click', e=>{ window.__ytClick = {def: e.defaultPrevented}; e.preventDefault(); }, {once:true}); document.getElementById('hdrYt').click(); true"); wait_ms(150)
check('YT-1 點 Header YouTube 不經 Router：history 與 Router 狀態不變', ev("history.length") == h0 and ev("JSON.stringify(Router.state())") == s0 and ev("window.__ytClick && window.__ytClick.def === false") is True)
check('YT-1 不影響 #statusBadge 與 ↻', ev("!!document.getElementById('statusBadge').textContent && document.getElementById('refreshBtn').getAttribute('onclick') === 'reloadData()' && document.getElementById('refreshBtn').closest('.topbar') !== null") is True)
ev("switchPage('yt'); true"); wait_ms(150)
check('YT-2 switchPage(yt) 相容入口：開同一外部連結（新分頁、noopener）、不寫 history、不換頁',
      ev("JSON.stringify(window.__opened)") == json.dumps([[YT_URL, '_blank', 'noopener']]).replace(' ', '') and ev("history.length") == h0
      and ev("JSON.stringify(Router.state())") == s0 and ev("document.getElementById('page-today').classList.contains('active')") is True, ev("JSON.stringify(window.__opened)"))
ev("window.open=window.__origOpen; true")
check('YT-2 page-yt 不存在、首頁與工具頁無 YouTube 連結',
      ev("""!document.getElementById('page-yt') && !document.querySelector('#page-today a[href*=youtube], #page-tools a[href*=youtube]')
        && ![...document.querySelectorAll('#page-today button, #page-tools button')].some(b=>/YouTube/.test(b.textContent))
        && document.querySelectorAll('a[href*="youtube.com"]').length === 1""") is True)
# 舊 history entry 帶 tool yt（升級前開過頻道頁）→ 落回工具卡片頁，不壞
ev("history.pushState({v:2, base:'tools', stack:[{t:'tool', id:'yt', ui:{}}]}, ''); true"); wait_ms(50)
ev("history.back(); true"); wait_ms(300)
ev("history.forward(); true"); wait_ms(300)
check('YT-2 舊 entry（tool yt）經 popstate 還原 → 顯示工具卡片頁、無例外', ev("Router.state().stack.map(l=>l.t+':'+l.id.slice(0,2)).join()") is not None and ev("document.getElementById('page-tools').classList.contains('active')") is True, ev("JSON.stringify(Router.state())"))
# 390px 直向 Header 不擁擠：標題不截斷、狀態徽章完整、搜尋列寬度不縮、無水平溢出
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
ev("switchPage('today'); window.scrollTo(0,0); true"); wait_ms(300)
hd = ev("""(()=>{const t=document.querySelector('.topbar-title'), b=document.getElementById('statusBadge'), a=document.querySelector('.hdr-actions'), g=document.getElementById('gsearch');
  const tr=t.getBoundingClientRect(), br=b.getBoundingClientRect(), ar=a.getBoundingClientRect();
  // 2026-10-10 品牌 Header：手機為錯位兩列（標題獨占第一列、按鈕群在第二列靠右），重疊改以矩形相交判斷
  const hit=(p,q)=>p.left<q.right&&q.left<p.right&&p.top<q.bottom&&q.top<p.bottom;
  return {tTrunc:t.scrollWidth>t.clientWidth, bTrunc:b.scrollWidth>b.clientWidth, overlap: hit(tr, ar) || hit(br, ar),
          gw:g.getBoundingClientRect().width, ov:document.documentElement.scrollWidth-document.documentElement.clientWidth,
          hdrH:document.querySelector('.app-hdr').getBoundingClientRect().height, btnH:[...a.children].map(x=>x.getBoundingClientRect().height)}})()""")
check('YT-1 390px Header：標題與狀態徽章完整、不與右側按鈕重疊、無水平溢出', not hd['tTrunc'] and not hd['bTrunc'] and not hd['overlap'] and hd['ov'] <= 0, hd)
check('YT-1 390px 搜尋列仍為全寬（≥ 340px）、右側按鈕皆 44px', hd['gw'] >= 340 and all(h >= 44 for h in hd['btnH']), hd)
cdp('Emulation.clearDeviceMetricsOverride')
ev("switchPage('today'); true"); wait_ms(150)
for pg in ['today','div','check','rank','today']:
    ev("switchPage('%s'); true" % pg); wait_ms(150)
    if pg == 'check':   # Phase 5 G3：在目前 entry（前一步的配息日曆子頁）上開 Flow 層，來源頁留在下面
        check('R switch page check opens Flow layer over the source page (Phase 5 G3)', ev("flowLayerVisible() && Router.state().stack.map(l=>l.t).join() === 'tool,flow' && document.getElementById('page-div').classList.contains('active')") is True, ev("JSON.stringify(Router.state())"))
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
# MG-1／MG-3（LAZY_WATCHLIST 於 CP3 首頁改版後一併驗證，見 home_test.py）
check('MG-3 retired globals are undefined (selETF/renderChips/calcUpdate/selChip/lookupToday/lookupCustom/renderSignalCard)',
      ev("['selETF','renderChips','calcUpdate','selChip','lookupToday','lookupCustom','renderSignalCard'].every(n=>{try{return eval('typeof '+n)==='undefined'}catch(e){return true}})") is True)
check('MG-1 ETFS／CALENDAR available from state.js', ev("Array.isArray(ETFS) && ETFS.length > 0 && Array.isArray(CALENDAR) && !!document.querySelector('script[src^=\\'js/state.js\\']') && !document.querySelector('script[src*=\\'calc.js\\'],script[src*=\\'lookup.js\\']')") is True)
check('MG home A-4 single-ETF lookup removed', ev("!document.getElementById('todayCode') && !document.getElementById('todayResult')") is True)
ev("switchPage('rank'); true"); wait_ms(100)
check('R rank find: 先展開 🔍（PO Change #2：預設收起）', ev("(()=>{ if(document.getElementById('rankFindBtn').getAttribute('aria-expanded')!=='true') document.getElementById('rankFindBtn').click(); const i=document.getElementById('rankFind'); return i.offsetParent!==null && i.getBoundingClientRect().height>0; })()") is True)   # 只多「先展開」一步，原斷言不變
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
