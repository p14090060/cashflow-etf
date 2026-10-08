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
# CP6c：定位後在可見中心點擊整列 → 該檔 Detail（一般列與有 Flow 的列都一樣）；「持股異動 ›」另驗 → Flow
nof = ev("[...document.querySelectorAll('#rankRows .rank-row:not(.has-flow)')].map(r=>r.dataset.code)")
hf = ev("[...document.querySelectorAll('#rankRows .rank-row.has-flow')].map(r=>r.dataset.code)")
for code in [c for c in (nof[0], nof[-1], hf[0]) if c]:
    pr = locate_probe(code)
    ev("""(()=>{const row=document.querySelector('#rankRows .rank-row[data-code="%s"]'); const r=row.querySelector('.rank-code').getBoundingClientRect();
      const sb=document.querySelector('.rank-sticky').getBoundingClientRect().bottom; const y=Math.max(r.top+r.height/2, sb+2);
      document.elementFromPoint(r.left+r.width/2, y).click(); return true})()""" % code); wait_ms(450)
    check('RK-4b 第 %d 名 %s：定位後在可見位置點擊整列 → 該檔 Detail（未開 Flow）' % (ranked.index(code) + 1, code),
          pr['top'] >= pr['stickyBottom'] and pr['hit'] and ev("!document.getElementById('gsPanel').hidden && _curEtfCode") == code and ev("flowLayerVisible()") is False, (pr, ev("_curEtfCode")))
    back()
for code in [hf[0], hf[-1]]:
    pr = locate_probe(code)
    ev("""(()=>{const b=document.querySelector('#rankRows .rank-row[data-code="%s"] .rank-flow'); const r=b.getBoundingClientRect();
      document.elementFromPoint(r.left+r.width/2, r.top+r.height/2).click(); return true})()""" % code); wait_ms(450)
    check('RK-4b 第 %d 名 %s：定位後點「持股異動 ›」→ 該檔持股異動（未開 Detail）' % (ranked.index(code) + 1, code),
          ev("flowLayerVisible() && _flowSel") == code and ev("document.getElementById('gsPanel').hidden") is True, ev("_flowSel"))
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
fc = ev("(document.querySelector('#rankRows .rank-row.has-flow')||{dataset:{}}).dataset.code")
ev("openFlow(%s); true" % json.dumps(fc)); wait_ms(400)
back()
check('RK-6 Flow 往返：🔍 展開、內容、定位、捲動保留', top()['fbDisp'] != 'none' and ev("document.getElementById('rankFind').value") == '0056'
      and ev("!!document.querySelector('#rankRows .rank-row.found')") is True and abs(ev("window.scrollY") - y0) <= 2)
ev("clearRankFind(); document.getElementById('rankFindBtn').click(); window.scrollTo(0,0); true"); wait_ms(250)
check('RK-6 清除後可收起', top()['fbDisp'] == 'none')

# ════════ NV（CP6c，PHASE5_PLAN §3.5）：排行列 → Detail、「持股異動 ›」→ Flow、日曆列 → Detail ════════
HSPY = """(()=>{ window.__hc = {push:0, rep:0};
  if (!window.__hspy) { window.__hspy = 1; const P = history.pushState, Rp = history.replaceState;
    history.pushState = function () { window.__hc.push++; return P.apply(history, arguments); };
    history.replaceState = function () { window.__hc.rep++; return Rp.apply(history, arguments); }; }
  return true; })()"""
def types(): return ev("Router.state().stack.map(l=>l.t).join()")
def tap_row(code, part='.rank-code'):
    """在該列 part 元素的可見中心做真實點擊（elementFromPoint 命中什麼就點什麼）。"""
    return ev("""(()=>{const row=document.querySelector('#rankRows .rank-row[data-code="%s"]'); const el=row.querySelector('%s'); const r=el.getBoundingClientRect();
      const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); hit.click(); return hit.className})()""" % (code, part))
def tap_flow(code):
    return ev("""(()=>{const b=document.querySelector('#rankRows .rank-row[data-code="%s"] .rank-flow'); const r=b.getBoundingClientRect();
      const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); hit.click(); return hit.className})()""" % code)
def bring(code):
    ev("""(()=>{const row=document.querySelector('#rankRows .rank-row[data-code="%s"]'); const sb=document.querySelector('.rank-sticky').getBoundingClientRect().bottom;
      window.scrollTo(0, row.getBoundingClientRect().top + scrollY - sb - 20); return true})()""" % code); wait_ms(300)

cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
ev("switchPage('tools'); true"); wait_ms(250)
ev("switchPage('rank'); window.scrollTo(0,0); true"); wait_ms(400)
nof = ev("[...document.querySelectorAll('#rankRows .rank-row:not(.has-flow)')].map(r=>r.dataset.code)")
hf = ev("[...document.querySelectorAll('#rankRows .rank-row.has-flow')].map(r=>r.dataset.code)")
A0 = nof[min(6, len(nof) - 1)]          # 一般列（無 Flow 資料）
F0 = hf[0]                              # 有 Flow 資料的列

# NV-1 一般列 → Detail
ev("{const f=document.getElementById('rankFind'); if(document.getElementById('rankFindBtn').getAttribute('aria-expanded')!=='true') document.getElementById('rankFindBtn').click(); f.value=%s; f.dispatchEvent(new Event('input'));} true" % json.dumps(A0)); wait_ms(300)
ev("new Promise(r=>{let last=-1,same=0;const i=setInterval(()=>{const y=Math.round(scrollY); same=(y===last)?same+1:0; last=y; if(same>=3){clearInterval(i);r(y)}},120)})", True)
y0 = ev("window.scrollY"); s0 = json.loads(st())
ev(HSPY)
hitc = tap_row(A0); wait_ms(400)
s1 = json.loads(st())
check('NV-1 真實點擊一般排行列（%s，無 Flow 資料）→ 命中 .rank-hit' % A0, hitc == 'rank-hit', hitc)
check('NV-1 → 該檔 Detail、只多一層 detail、pushState 恰好 1 次',
      ev("!document.getElementById('gsPanel').hidden && _curEtfCode") == A0 and types() == 'tool,detail' and s1['stack'][-1]['code'] == A0
      and ev("window.__hc.push") == 1 and len(s1['stack']) == len(s0['stack']) + 1 and ev("flowLayerVisible()") is False, (types(), ev("window.__hc")))
check('NV-1 history.state 與 Router.state() 結構一致', ev("JSON.stringify(history.state.stack.map(l=>[l.t,l.code||null]))===JSON.stringify(Router.state().stack.map(l=>[l.t,l.code||null]))") is True)
back()
check('NV-1 Back → 原排行：stack [tool]、搜尋內容與定位、捲動保留', types() == 'tool' and ev("document.getElementById('rankFind').value") == A0
      and ev("!!document.querySelector('#rankRows .rank-row.found[data-code=\"%s\"]')" % A0) is True and abs(ev("window.scrollY") - y0) <= 2, (ev("window.scrollY"), y0))
ev("clearRankFind(); document.getElementById('rankFindBtn').click(); true"); wait_ms(150)

# NV-2 「持股異動 ›」→ Flow（不開 Detail）
nflow = ev("Object.keys(_flowData.etfs).filter(k=>_rankSorted.some(e=>e.code===k)).length")
nbtn = ev("document.querySelectorAll('#rankRows .rank-flow').length")
# _changedWithin()（flow.js）已在 CP8 隨死碼清理移除；測試自己算「7 天內沒換股」，斷言不變
stale = ev("Object.keys(_flowData.etfs).filter(k=>{const d=_flowData.etfs[k].last_change_date; const t=d?new Date(d+'T00:00:00').getTime():NaN;"
           " return _rankSorted.some(e=>e.code===k) && !(t && (Date.now()-t)/86400000<=7)})")
check('NV-2 有 Active Flow 資料的排行 ETF 都有「持股異動 ›」（%d 檔；含 7 天內無換股者 %d 檔）' % (nflow, len(stale)),
      nbtn == nflow and nflow > 0 and all(ev("!!document.querySelector('#rankRows .rank-row[data-code=\"%s\"] .rank-flow')" % c) for c in stale), (nbtn, nflow, stale))
check('NV-2 無 Flow 資料的列沒有此按鈕', ev("document.querySelectorAll('#rankRows .rank-row:not(.has-flow) .rank-flow').length") == 0)
fb = ev("""(()=>{const b=document.querySelector('#rankRows .rank-row[data-code="%s"] .rank-flow'); const r=b.getBoundingClientRect();
  return {tag:b.tagName, h:r.height, aria:b.getAttribute('aria-label'), nested: !!b.closest('button:not(.rank-flow)') || !!document.querySelector('#rankRows button button')}})()""" % F0)
check('NV-2 「持股異動 ›」是 button、≥ 44px、aria-label 含代碼、無 button 巢狀', fb['tag'] == 'BUTTON' and fb['h'] >= 44 and F0 in fb['aria'] and not fb['nested'], fb)
bring(F0)
ev(HSPY)
hitc = tap_flow(F0); wait_ms(450)
check('NV-2 真實點擊「持股異動 ›」→ [tool, flow]、該檔、pushState 恰好 1 次、Detail 未開',
      hitc == 'rank-flow' and types() == 'tool,flow' and ev("_flowSel") == F0 and ev("window.__hc.push") == 1 and ev("document.getElementById('gsPanel').hidden") is True, (hitc, types(), ev("window.__hc")))
back()
check('NV-2 Back → 排行', types() == 'tool' and ev("flowLayerVisible()") is False)
# 同一有 Flow 的列，點列的其他區域 → Detail（不是 Flow）
ev(HSPY)
hitc = tap_row(F0); wait_ms(400)
check('NV-2 有 Flow 資料的列，點列其他區域 → Detail（不開 Flow）、pushState 1 次', hitc == 'rank-hit' and types() == 'tool,detail' and ev("_curEtfCode") == F0
      and ev("flowLayerVisible()") is False and ev("window.__hc.push") == 1, (hitc, types()))

# NV-3 三層返回：row → Detail → 查看完整持股異動 → Back → Detail → Back → 排行
ev("detailTab('holdings'); true"); wait_ms(250)
ev("document.querySelector('.gs-flow-btn').click(); true"); wait_ms(450)
check('NV-3 Detail → 查看完整持股異動：[tool, detail, flow]', types() == 'tool,detail,flow' and ev("_flowSel") == F0)
back()
check('NV-3 Back → Detail（同檔、持股分頁）', types() == 'tool,detail' and ev("_curEtfCode") == F0 and ev("_detailTab") == 'holdings')
back()
check('NV-3 再 Back → 排行', types() == 'tool' and ev("document.getElementById('page-rank').classList.contains('active')") is True)

# NV-4 重繪後仍有效；鍵盤 Enter／Space；Esc
ev("renderAll(ETFS, CALENDAR, '2026-10-07 10:00:00', null, true, false); renderRank(); true"); wait_ms(300)
bring(A0)
ev(HSPY)
tap_row(A0); wait_ms(400)
check('NV-4 renderAll／renderRank 重繪後點列仍開 Detail（pushState 1 次）', types() == 'tool,detail' and ev("_curEtfCode") == A0 and ev("window.__hc.push") == 1)
back()
bring(F0)
tap_flow(F0); wait_ms(400)
check('NV-4 重繪後點「持股異動 ›」仍開 Flow', types() == 'tool,flow' and ev("_flowSel") == F0)
back()
for key, kc in (('Enter', 'Enter'), (' ', 'Space')):
    ev("document.querySelector('#rankRows .rank-row[data-code=\"%s\"] .rank-hit').focus(); true" % A0)
    cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': key, 'code': kc, 'windowsVirtualKeyCode': 13 if kc == 'Enter' else 32, 'text': '\r' if kc == 'Enter' else ' '})
    cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': key, 'code': kc, 'windowsVirtualKeyCode': 13 if kc == 'Enter' else 32})
    wait_ms(400)
    check('NV-4 鍵盤 %s（焦點在列按鈕）→ Detail' % kc, types() == 'tool,detail' and ev("_curEtfCode") == A0, types())
    ev("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); true"); wait_ms(400)
    check('NV-4 Esc → 關 Detail、回排行（Router 不受影響）', types() == 'tool' and ev("document.getElementById('gsPanel').hidden") is True, types())
check('NV-4 HTML 無 button 巢狀（排行、日曆）', ev("document.querySelectorAll('#rankRows button button, #calList button button').length") == 0)

# NV-6（CP6c fix）：近 3 月小柱狀圖不得被 .rank-hit 蓋住——hover 取得原 title 報酬提示；點柱狀圖 → Detail（單一 navigation）
cdp('Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 800, 'deviceScaleFactor': 1, 'mobile': False})   # 桌面 pointer
wait_ms(300)
MB = ev("""(()=>{const e=_rankSorted.find(x=>(x.ret_months||[]).slice(-3).filter(v=>v!=null&&v!==0).length===3 && !(_flowData.etfs||{})[x.code]); return e?e.code:null})()""")
check('NV-6 前提：有 3 根非零柱、且無 Flow 按鈕干擾的排行列', bool(MB), MB)
bring(MB)
exp = ev("_rankSorted.find(x=>x.code===%s).ret_months.slice(-3).map(v=>(v>0?'+':'')+v.toFixed(1)+'%%')" % json.dumps(MB))
bars = ev("""(()=>{const row=document.querySelector('#rankRows .rank-row[data-code="%s"]');
  return [...row.querySelectorAll('.mini-bars .mb')].map(b=>{const r=b.querySelector('.mb-bar').getBoundingClientRect(); const x=r.left+r.width/2, y=r.top+r.height/2;
    const hit=document.elementFromPoint(x,y); const mb=hit&&hit.closest('.mb');
    return {x:x, y:y, hit:hit?(hit.className||hit.tagName):null, title: mb?mb.getAttribute('title'):null, rowHit: !!hit && hit.classList.contains('rank-hit')}})})()""" % MB)
print('   NV-6 bars (expected %s):' % exp, bars)
check('NV-6 每根柱子的實際可見位置命中柱狀圖元素（不是 .rank-hit）', len(bars) == 3 and all(b['title'] is not None and not b['rowHit'] for b in bars), bars)
check('NV-6 命中元素的 title＝原報酬提示（%s）' % ' / '.join(exp or []), [b['title'] for b in bars] == exp, ([b['title'] for b in bars], exp))
b0 = bars[0]
cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': b0['x'], 'y': b0['y']}); wait_ms(150)
hov = ev("(()=>{const h=[...document.querySelectorAll(':hover')].pop(); const mb=h&&h.closest('.mb'); return mb?mb.getAttribute('title'):(h?h.className:null)})()")
check('NV-6 滑鼠移到柱子上：:hover 落在帶 title 的柱狀圖元素（瀏覽器 tooltip 來源）', hov == exp[0], hov)
ev(HSPY)
cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': b0['x'], 'y': b0['y'], 'button': 'left', 'clickCount': 1})
cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': b0['x'], 'y': b0['y'], 'button': 'left', 'clickCount': 1}); wait_ms(400)
check('NV-6 點柱狀圖 → 該檔 Detail、pushState 恰好 1 次、未開 Flow（單一 navigation）',
      types() == 'tool,detail' and ev("_curEtfCode") == MB and ev("window.__hc.push") == 1 and ev("flowLayerVisible()") is False, (types(), ev("window.__hc")))
back()
# 有 Flow 按鈕的列：柱狀圖與按鈕各自獨立
bring(F0)
fb = ev("""(()=>{const row=document.querySelector('#rankRows .rank-row[data-code="%s"]'); const b=row.querySelector('.rank-flow').getBoundingClientRect();
  const hit=document.elementFromPoint(b.left+b.width/2, b.top+b.height/2); const mbs=row.querySelector('.mini-bars .mb .mb-bar'); let mh=null;
  if(mbs){const r=mbs.getBoundingClientRect(); const h=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); mh=h&&!!h.closest('.mb');}
  return {flowHit: hit&&hit.className, barHit: mh}})()""" % F0)
check('NV-6 有 Flow 的列：「持股異動 ›」仍命中按鈕、柱狀圖仍命中柱子（互不遮擋）', fb['flowHit'] == 'rank-flow' and fb['barHit'] in (True, None), fb)
ev(HSPY)
tap_flow(F0); wait_ms(400)
check('NV-6 「持股異動 ›」仍只開 Flow（pushState 1 次、Detail 未開）', types() == 'tool,flow' and ev("window.__hc.push") == 1 and ev("document.getElementById('gsPanel').hidden") is True)
back()
ev("document.querySelector('#rankRows .rank-row[data-code=\"%s\"] .rank-hit').focus(); true" % A0)
fo = ev("(()=>{const b=document.activeElement; return {cls:b.className, outline:getComputedStyle(b).outlineStyle}})()")
cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13, 'text': '\r'})
cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13}); wait_ms(400)
check('NV-6 鍵盤：列按鈕可取得焦點、Enter → Detail', fo['cls'] == 'rank-hit' and types() == 'tool,detail' and ev("_curEtfCode") == A0, (fo, types()))
back()
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}); wait_ms(300)

# NV-5 日曆列 → Detail
back()
ev("document.getElementById('toolDiv').click(); true"); wait_ms(350)
dcodes = ev("[...document.querySelectorAll('#calList .cal-item')].map(r=>r.dataset.code)")
check('NV-5 前提：日曆有列且帶代碼', isinstance(dcodes, list) and len(dcodes) > 0 and all(dcodes), dcodes)
for dc in [dcodes[0], dcodes[-1]]:
    ev("""(()=>{const row=document.querySelector('#calList .cal-item[data-code="%s"]'); row.scrollIntoView({block:'center'}); return true})()""" % dc); wait_ms(250)
    y0 = ev("window.scrollY")
    ev(HSPY)
    hitc = ev("""(()=>{const row=document.querySelector('#calList .cal-item[data-code="%s"]'); const r=row.querySelector('.cal-info').getBoundingClientRect();
      const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); hit.click(); return hit.className})()""" % dc); wait_ms(400)
    check('NV-5 真實點擊日曆列（%s）→ 該檔 Detail、pushState 恰好 1 次' % dc, hitc == 'cal-hit' and types() == 'tool,detail' and ev("_curEtfCode") == dc and ev("window.__hc.push") == 1, (hitc, types()))
    back()
    check('NV-5 Back → 回配息日曆、捲動保留', types() == 'tool' and ev("document.getElementById('page-div').classList.contains('active')") is True and abs(ev("window.scrollY") - y0) <= 2)
ev("renderAll(ETFS, CALENDAR, '2026-10-07 10:00:00', null, true, false); true"); wait_ms(300)
ev(HSPY)
ev("document.querySelector('#calList .cal-item').scrollIntoView({block:'center'}); true"); wait_ms(250)
hitc = ev("""(()=>{const r=document.querySelector('#calList .cal-item .cal-info').getBoundingClientRect(); const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); hit.click(); return hit.className})()"""); wait_ms(400)
check('NV-5 重繪後日曆列仍可點 → Detail', types() == 'tool,detail' and ev("window.__hc.push") == 1, (hitc, types()))
back(); back()
cdp('Emulation.clearDeviceMetricsOverride')
ev("switchPage('rank'); window.scrollTo(0,0); true"); wait_ms(300)

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
