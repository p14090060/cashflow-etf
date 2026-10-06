"""Phase 5 CP6b（PO Change #2）：成交量排行第一屏——🔍／ⓘ 按需展開（PHASE5_PLAN §3.8；RK-1～RK-7）。

RK-4（定位行為不變）由 tools_test.py TC-6／TC-7／RF-3 與 regression_test.py「R rank find 0050」覆蓋（先展開 🔍 再操作）；
RK-8＝完整 regression。執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
"""
import sys, json
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

ev("clearInterval(_pollTimer); window.__routerManualTimers = true; true")
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowData||Date.now()-t>20000){clearInterval(i);r(true)}},100)})", True)

def st(): return ev("JSON.stringify(Router.state())")
def back(ms=400): ev("history.back(); true"); wait_ms(ms)

TOP_JS = """(()=>{const R=s=>document.querySelector(s).getBoundingClientRect(); const nav=R('.bottom-nav').top;
  const rows=[...document.querySelectorAll('#rankRows .rank-row')]; const fb=document.getElementById('rankFindBox'), ib=document.getElementById('rankInfo');
  return {sticky:Math.round(R('.rank-sticky').height), stickyTop:Math.round(R('.rank-sticky').top), first:Math.round(rows[0].getBoundingClientRect().top),
    full:rows.filter(x=>{const b=x.getBoundingClientRect(); return b.top>=R('.rank-sticky').bottom-1 && b.bottom<=nav}).length,
    fifthTop:Math.round(rows[4].getBoundingClientRect().top), nav:Math.round(nav),
    fbDisp:getComputedStyle(fb).display, ibDisp:getComputedStyle(ib).display, fbH:fb.getBoundingClientRect().height, ibH:ib.getBoundingClientRect().height,
    findBtn:{h:R('#rankFindBtn').height, w:R('#rankFindBtn').width, exp:document.getElementById('rankFindBtn').getAttribute('aria-expanded')},
    infoBtn:{h:R('#rankInfoBtn').height, w:R('#rankInfoBtn').width, exp:document.getElementById('rankInfoBtn').getAttribute('aria-expanded')},
    title:document.querySelector('.rank-title').textContent.trim(), scrollY:Math.round(scrollY),
    ov:document.documentElement.scrollWidth-document.documentElement.clientWidth}})()"""
def top(): return ev(TOP_JS)

cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
ev("switchPage('rank'); window.scrollTo(0,0); true"); wait_ms(500)
t0 = top()
print('   RK-1 measured (390x844):', {k: t0[k] for k in ('sticky', 'first', 'full', 'fifthTop', 'nav')})
check('RK-1 標題「成交量排行」、🔍／ⓘ 預設收起', t0['title'] == '成交量排行' and t0['findBtn']['exp'] == 'false' and t0['infoBtn']['exp'] == 'false', t0)
check('RK-1 sticky ≤ 120px', t0['sticky'] <= 120, t0['sticky'])
check('RK-1 第一屏完整可見 ≥ 4 列、第 5 列至少露出一部分', t0['full'] >= 4 and t0['fifthTop'] < t0['nav'], (t0['full'], t0['fifthTop'], t0['nav']))
check('RK-1 第一筆位置明顯提前（現況 395 → ≤ 313）', t0['first'] <= 313, t0['first'])
check('RK-1 收起的搜尋與說明 display:none、不佔高度', t0['fbDisp'] == 'none' and t0['ibDisp'] == 'none' and t0['fbH'] == 0 and t0['ibH'] == 0, t0)
ev("window.scrollTo(0, 1500); true"); wait_ms(300)
t1 = top()
check('RK-1 捲動後 sticky 黏在 Header 下方且仍 ≤ 120px', t1['sticky'] <= 120 and t1['stickyTop'] == ev("Math.round(document.querySelector('.app-hdr').getBoundingClientRect().bottom)"), t1)
ev("window.scrollTo(0, 0); true"); wait_ms(300)

# RK-4b（CP6b FIX-1）：定位後目標列實際可見、未被 Header／排行 sticky 遮住、可點進 Detail——不同名次都要成立
def locate_probe(code):
    ev("clearRankFind(); window.scrollTo(0,0); true"); wait_ms(250)
    ev("if(document.getElementById('rankFindBtn').getAttribute('aria-expanded')!=='true') document.getElementById('rankFindBtn').click(); true"); wait_ms(150)
    ev("{const f=document.getElementById('rankFind'); f.value=%s; f.dispatchEvent(new Event('input'));} true" % json.dumps(code)); wait_ms(300)
    # smooth scroll 距離長時要等它停下來（連續 3 次 scrollY 不變）
    ev("new Promise(r=>{let last=-1,same=0;const i=setInterval(()=>{const y=Math.round(scrollY); same=(y===last)?same+1:0; last=y; if(same>=3){clearInterval(i);r(y)}},120)})", True)
    return ev("""(()=>{const row=document.querySelector('#rankRows .rank-row[data-code="%s"]'); const r=row.getBoundingClientRect();
      const sb=document.querySelector('.rank-sticky').getBoundingClientRect().bottom, hb=document.querySelector('.app-hdr').getBoundingClientRect().bottom;
      const nav=document.querySelector('.bottom-nav').getBoundingClientRect().top; const cx=r.left+r.width/2, cy=(Math.max(r.top,sb)+Math.min(r.bottom,nav))/2;
      const hit=document.elementFromPoint(cx, cy);
      return {top:Math.round(r.top), bottom:Math.round(r.bottom), stickyBottom:Math.round(sb), hdrBottom:Math.round(hb), nav:Math.round(nav), scrollY:Math.round(scrollY),
              found:row.classList.contains('found'), hit:!!hit && hit.closest('.rank-row')===row}})()""" % code)

ranked = ev("_rankSorted.map(e=>e.code)")
n_all = ev("document.querySelectorAll('#rankRows .rank-row').length")
for idx in sorted({0, 4, len(ranked) // 3, len(ranked) // 2, (2 * len(ranked)) // 3, len(ranked) - 1}):
    code = ranked[idx]
    pr = locate_probe(code)
    print('   RK-4b rank %d %s:' % (idx + 1, code), pr)
    check('RK-4b 第 %d 名 %s：定位後整列在 sticky 下方、導覽列上方（不被遮住）' % (idx + 1, code),
          pr['found'] and pr['top'] >= pr['stickyBottom'] and pr['bottom'] <= pr['nav'], pr)
    check('RK-4b 第 %d 名 %s：列中心 elementFromPoint 命中該列（可點）' % (idx + 1, code), pr['hit'], pr)
    check('RK-4b 第 %d 名 %s：仍是定位不過濾（%d 列都在）' % (idx + 1, code, n_all), ev("document.querySelectorAll('#rankRows .rank-row').length") == n_all)
# 排行列的點擊行為是既有設計：有持股異動資料的列（.tappable）→ 開 Flow；其他列沒有點擊動作（PHASE5 未改）。
# 這裡驗「定位後在可見位置真的點得到」：挑一檔 tappable 的列定位，於列的可見中心點擊 → 開該檔 Flow。
tap = ev("[...document.querySelectorAll('#rankRows .rank-row.tappable')].map(r=>r.dataset.code)")
for code in [c for c in (tap[0], tap[len(tap) // 2], tap[-1])]:
    pr = locate_probe(code)
    ev("""(()=>{const row=document.querySelector('#rankRows .rank-row[data-code="%s"]'); const r=row.getBoundingClientRect();
      const sb=document.querySelector('.rank-sticky').getBoundingClientRect().bottom; const y=(Math.max(r.top,sb)+r.bottom)/2;
      document.elementFromPoint(r.left+r.width/2, y).click(); return true})()""" % code); wait_ms(450)
    check('RK-4b 第 %d 名 %s（可點列）：定位後在可見中心點擊 → 開該檔持股異動' % (ranked.index(code) + 1, code),
          pr['top'] >= pr['stickyBottom'] and pr['hit'] and ev("flowLayerVisible() && _flowSel") == code, (pr, ev("_flowSel")))
    back()
# 展開 ⓘ（sticky 變高）時也不被遮住
ev("if(document.getElementById('rankInfoBtn').getAttribute('aria-expanded')!=='true') document.getElementById('rankInfoBtn').click(); true"); wait_ms(150)
pr = locate_probe(ranked[len(ranked) // 2])
check('RK-4b ⓘ 展開（sticky 變高）時定位列仍完整可見、可點', pr['top'] >= pr['stickyBottom'] and pr['bottom'] <= pr['nav'] and pr['hit'], pr)
ev("document.getElementById('rankInfoBtn').click(); clearRankFind(); document.getElementById('rankFindBtn').click(); window.scrollTo(0,0); true"); wait_ms(300)

# RK-2 🔍
check('RK-2 🔍、ⓘ touch target ≥ 44×44', t0['findBtn']['h'] >= 44 and t0['findBtn']['w'] >= 44 and t0['infoBtn']['h'] >= 44 and t0['infoBtn']['w'] >= 44, (t0['findBtn'], t0['infoBtn']))
h0 = ev("history.length"); s0 = st()
ev("document.getElementById('rankFindBtn').click(); true"); wait_ms(200)
f = ev("""(()=>{const i=document.getElementById('rankFind'); return {exp:document.getElementById('rankFindBtn').getAttribute('aria-expanded'), vis:i.offsetParent!==null && i.getBoundingClientRect().height>0,
  focus:document.activeElement===i, ph:i.placeholder}})()""")
check('RK-2 按 🔍 展開：輸入框可見並取得焦點、placeholder「在排行中找 ETF」', f['exp'] == 'true' and f['vis'] and f['focus'] and f['ph'] == '在排行中找 ETF', f)
check('RK-2 文案不使用「篩選」', '篩選' not in (ev("document.querySelector('.rank-sticky').innerText + document.getElementById('rankFind').placeholder + document.getElementById('rankFindBtn').getAttribute('aria-label')") or ''))
ev("document.getElementById('rankFindBtn').click(); true"); wait_ms(150)
check('RK-2 再按 🔍 收起（無搜尋內容時）', top()['fbDisp'] == 'none')
ev("document.getElementById('rankFindBtn').click(); true"); wait_ms(150)
ev("{const f=document.getElementById('rankFind'); f.value='0056'; f.dispatchEvent(new Event('input'));} true"); wait_ms(300)
ev("document.getElementById('rankInfoBtn').click(); true"); wait_ms(150)
ev("document.getElementById('rankInfoBtn').click(); true"); wait_ms(150)
ev("renderAll(ETFS, CALENDAR, '2026-10-06 10:00:00', null, true, false); true"); wait_ms(300)
check('RK-2 有搜尋內容時：開關 ⓘ、輪詢重繪後 🔍 仍展開、內容與定位保留', top()['fbDisp'] != 'none' and ev("document.getElementById('rankFind').value") == '0056'
      and ev("!!document.querySelector('#rankRows .rank-row.found[data-code=\"0056\"]')") is True)

# RK-3 ⓘ
ev("document.getElementById('rankInfoBtn').click(); true"); wait_ms(150)
info = ev("""(()=>{const b=document.getElementById('rankInfo'); return {exp:document.getElementById('rankInfoBtn').getAttribute('aria-expanded'), disp:getComputedStyle(b).display, txt:b.innerText,
  total:document.getElementById('rankTotal').textContent, n:document.querySelectorAll('#rankRows .rank-row').length}})()""")
check('RK-3 按 ⓘ 展開：原說明逐字存在、筆數正確', info['exp'] == 'true' and info['disp'] != 'none' and ('依當日成交量排序 · 共 %s 支' % info['total']) in info['txt'] and info['total'] == str(info['n']), info)
check('RK-3 原警示逐字存在', '⚠ 排名高＝今天很多人在買賣，不代表比較好或比較適合存股' in info['txt'], info['txt'])
ev("document.getElementById('rankInfoBtn').click(); true"); wait_ms(150)
check('RK-3 再按 ⓘ 收起', top()['ibDisp'] == 'none')

# RK-5 不寫 history
check('RK-5 🔍／ⓘ 開關不寫 history、不改 Router 狀態', ev("history.length") == h0 and st() == s0, (ev("history.length"), h0))

# RK-6 往返保留（Detail、Flow）
ev("window.scrollTo(0, 600); true"); wait_ms(300)
y0 = ev("window.scrollY")
ev("openDetail('0050'); true"); wait_ms(350)
back()
r6a = top()
check('RK-6 Detail 往返：🔍 展開、內容、定位標示、捲動保留', r6a['fbDisp'] != 'none' and ev("document.getElementById('rankFind').value") == '0056'
      and ev("!!document.querySelector('#rankRows .rank-row.found')") is True and abs(ev("window.scrollY") - y0) <= 2, (r6a, y0))
fc = ev("(document.querySelector('#rankRows .rank-row.tappable')||{dataset:{}}).dataset.code")
ev("openFlow(%s); true" % json.dumps(fc)); wait_ms(400)
back()
check('RK-6 Flow 往返：🔍 展開、內容、定位、捲動保留', top()['fbDisp'] != 'none' and ev("document.getElementById('rankFind').value") == '0056'
      and ev("!!document.querySelector('#rankRows .rank-row.found')") is True and abs(ev("window.scrollY") - y0) <= 2)
ev("clearRankFind(); document.getElementById('rankFindBtn').click(); window.scrollTo(0,0); true"); wait_ms(250)
check('RK-6 清除後可收起', top()['fbDisp'] == 'none')

# RK-7 橫向／鍵盤
cdp('Emulation.setDeviceMetricsOverride', {'width': 844, 'height': 390, 'deviceScaleFactor': 2, 'mobile': True})
wait_ms(400)
ev("document.getElementById('rankFindBtn').click(); document.getElementById('rankInfoBtn').click(); true"); wait_ms(250)
l7 = top()
small = ev("""[...document.querySelectorAll('.rank-sticky *')].filter(el=>el.offsetParent!==null && [...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())).map(el=>parseFloat(getComputedStyle(el).fontSize)).filter(f=>f<13)""")
check('RK-7 橫向 844×390：🔍／ⓘ 可展開、無水平溢出、排行頂部文字 ≥ 13px', l7['fbDisp'] != 'none' and l7['ibDisp'] != 'none' and l7['ov'] <= 0 and small == [], (l7, small))
ev("document.body.classList.add('gs-ckm'); true"); wait_ms(250)
k7 = ev("({ov:document.documentElement.scrollWidth-document.documentElement.clientWidth, btn:document.getElementById('rankFindBtn').getBoundingClientRect().height})")
check('RK-7 鍵盤（gs-ckm）：無水平溢出、🔍 仍可操作', k7['ov'] <= 0 and k7['btn'] >= 44, k7)
ev("document.body.classList.remove('gs-ckm'); document.getElementById('rankFindBtn').click(); document.getElementById('rankInfoBtn').click(); true"); wait_ms(200)
cdp('Emulation.clearDeviceMetricsOverride')

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'), (e['params']['exceptionDetails'].get('exception', {}) or {}).get('description', '')[:200])
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
