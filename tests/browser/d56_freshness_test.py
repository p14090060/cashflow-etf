"""D5／D6 Phase 1：行情時效文字（不宣稱今日／最近交易日、不推算日期；數值與排序不變）。

執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
正式資料沒有逐檔 quote_date，updated 是抓取時間、is_holiday 本身有已知錯誤，
所以文字一律中性，並在 TOP10 與排行說明放同一段非即時提示；不依 is_holiday 切換。
情境以 renderAll 的旗標與資料副本模擬（一般交易日／週末／國定休市日／is_holiday 錯誤／無成交 ETF）。
"""
import sys, json
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0
ev("clearInterval(_pollTimer); true")

NOTE = '非即時資料；休市日可能顯示先前保存或更新的成交量，實際交易日期尚未確認。'
BAD = ('今日成交量', '當日成交量', '今天', '最近交易日', '即時成交', '今日 TOP', '今日合理價')
ev("window.__E0 = JSON.parse(JSON.stringify(ETFS)); window.__C0 = CALENDAR.slice(); window.__M0 = {price:49313.44, change_pt:-492.93, change_pct:-0.99}; true")

def expected():
    """與 rank.js／render.js 相同規則、在 Python 各自計算的預期（代碼、價格、成交量）"""
    E = ev("ETFS.map(e=>({code:e.code, price:e.price, cur_vol:e.cur_vol||0, avg_vol:e.avg_vol||0}))")
    wv = [e for e in E if e['cur_vol'] > 0 and e['price'] > 0]
    pool = wv if len(wv) >= 100 else [e for e in E if e['price'] > 0]
    rank = sorted(pool, key=lambda e: (-e['cur_vol'], -e['avg_vol']))[:100]   # sorted 穩定，與 JS sort 相同
    top = sorted(wv, key=lambda e: -e['cur_vol'])[:10]
    return [e['code'] for e in top], [e['code'] for e in rank], {e['code']: e['price'] for e in E}

def scenario(name, updated, closed, holiday, mutate=''):
    ev("ETFS = JSON.parse(JSON.stringify(__E0)); %s; renderAll(ETFS, __C0, %s, __M0, %s, %s); true"
       % (mutate or 'void 0', json.dumps(updated), 'true' if closed else 'false', 'true' if holiday else 'false')); wait_ms(150)
    ev("Router.toBase({base:'home'}); true"); wait_ms(200)
    home = ev("""({title:document.getElementById('tvTitle').textContent.trim(), note:(document.getElementById('tvNote')||{}).textContent||'',
      noteVis:!!(document.getElementById('tvNote')||{}).offsetParent, txt:document.getElementById('page-today').innerText,
      top:[...document.querySelectorAll('#waitItems .hot-item')].map(b=>({code:b.dataset.code, px:(b.querySelector('.hr-px')||{}).textContent||''}))})""")
    ev("switchPage('rank'); true"); wait_ms(300)
    ev("if (document.getElementById('rankInfo').hidden) rankToggleInfo(); true"); wait_ms(100)
    rank = ev("""({info:document.getElementById('rankInfo').innerText, hdr:document.querySelector('.rank-hdr').innerText, txt:document.getElementById('page-rank').innerText,
      rows:[...document.querySelectorAll('#rankRows .rank-row')].map(r=>({code:r.dataset.code, px:(r.querySelector('.rank-price')||{}).textContent}))})""")
    if not isinstance(home, dict): home = {'title': '', 'note': '', 'noteVis': False, 'txt': '', 'top': [], 'err': home}
    if not isinstance(rank, dict): rank = {'info': '', 'hdr': '', 'txt': '', 'rows': [], 'err': rank}
    ev("rankToggleInfo(); true"); wait_ms(80)
    ev("switchPage('tools'); true"); wait_ms(200)
    tools = ev("document.getElementById('page-tools').innerText")
    if not isinstance(tools, str): tools = ''
    top, rk, px = expected()
    pxs = ev("Object.fromEntries(ETFS.map(e=>[e.code, String(e.price)]))")
    allt = home['txt'] + rank['txt'] + rank['info'] + tools
    hits = [b for b in BAD if b in allt]
    check('%s：TOP10 標題「成交量 TOP 10」、提示可見' % name, home['title'] == '成交量 TOP 10' and home['note'] == NOTE and home['noteVis'], home['title'])
    check('%s：排行說明「依現有成交量資料排序」＋同一段非即時提示；表頭「參考價格」；工具卡「查看 ETF 成交量排行」' % name,
          '依現有成交量資料排序 · 共' in rank['info'] and NOTE in rank['info'] and '參考價格' in rank['hdr'] and '查看 ETF 成交量排行' in tools, rank['info'][:120])
    check('%s：首頁／排行／工具不再宣稱今日、當日、最近交易日' % name, not hits, hits)
    check('%s：TOP10 順序與價格不變（參考價格 x.xx）' % name, [t['code'] for t in home['top']] == top
          and all(t['px'] == '參考價格 %.2f' % px[t['code']] for t in home['top']), (home['top'][:3], top[:3]))
    check('%s：排行 %d 列順序與價格不變' % (name, len(rk)), [r['code'] for r in rank['rows']] == rk
          and all(r['px'] == pxs[r['code']] for r in rank['rows']),
          ([r['code'] for r in rank['rows']][:5], rk[:5]))
    return home, rank

scenario('一般交易日（LIVE）', '2026-10-09 11:20', False, False)
scenario('一般交易日收盤後', '2026-10-09 22:20', True, False)
scenario('週末（is_holiday=true，週日抓取）', '2026-10-04 14:25', True, True,
         "ETFS.forEach(e=>{e.change_pct=null; e.change_pt=null; if(e.cur_vol) e.cur_vol=e.cur_vol*1.059})")
scenario('國定休市日（10/10，is_holiday=true）', '2026-10-10 09:05', True, True)
scenario('is_holiday 資料錯誤（休市日卻標 false、closed=false）', '2026-10-10 10:00', False, False)
h, r = scenario('無成交 ETF（TOP 1 改為 cur_vol=0）', '2026-10-09 22:20', True, False,
                "(()=>{const t=[...ETFS].filter(e=>(e.cur_vol||0)>0&&e.price>0).sort((a,b)=>b.cur_vol-a.cur_vol)[0]; window.__z=t.code; t.cur_vol=0})()")
z = ev("__z")
check('無成交 ETF %s：不進 TOP10（與原規則相同）' % z, z not in [t['code'] for t in h['top']], z)

# 手機版不擠壓：提示在 390 寬不溢出、不與標題／清單重疊
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}); wait_ms(300)
ev("ETFS = JSON.parse(JSON.stringify(__E0)); renderAll(ETFS, __C0, '2026-10-09 22:20', __M0, true, false); Router.toBase({base:'home'}); true"); wait_ms(300)
lay = ev("""(()=>{const t=document.getElementById('tvTitle').getBoundingClientRect(), n=document.getElementById('tvNote').getBoundingClientRect(), l=document.getElementById('waitItems').getBoundingClientRect();
  return {tB:t.bottom, nT:n.top, nB:n.bottom, lT:l.top, nR:n.right, vw:document.documentElement.clientWidth, ov:document.documentElement.scrollWidth-document.documentElement.clientWidth}})()""")
check('手機 390：TOP10 提示在標題與清單之間、不重疊、無水平溢出', isinstance(lay, dict) and lay['nT'] >= lay['tB'] - 0.5 and lay['nB'] <= lay['lT'] + 0.5 and lay['nR'] <= lay['vw'] and lay['ov'] <= 0, lay)
ev("switchPage('rank'); true"); wait_ms(300)
h0 = ev("document.querySelector('.rank-top').getBoundingClientRect().height")
ev("rankToggleInfo(); true"); wait_ms(150)
lay2 = ev("""(()=>{const i=document.getElementById('rankInfo').getBoundingClientRect(), n=document.getElementById('rankNote').getBoundingClientRect(), h=document.querySelector('.rank-hdr').getBoundingClientRect();
  return {iB:i.bottom, nB:n.bottom, hT:h.top, nR:n.right, vw:document.documentElement.clientWidth, ov:document.documentElement.scrollWidth-document.documentElement.clientWidth}})()""")
check('手機 390：排行說明展開後提示在說明區內、不壓到表頭、無水平溢出', isinstance(lay2, dict) and lay2['nB'] <= lay2['iB'] + 0.5 and lay2['iB'] <= lay2['hT'] + 0.5 and lay2['nR'] <= lay2['vw'] and lay2['ov'] <= 0, lay2)
ev("rankToggleInfo(); true"); wait_ms(150)
check('手機 390：排行說明收起時標題列高度不變（提示不佔 sticky 高度）', abs(ev("document.querySelector('.rank-top').getBoundingClientRect().height") - h0) < 0.5, h0)
hdr = ev("(()=>{const c=[...document.querySelectorAll('.rank-hdr-main > div')].find(d=>d.textContent==='參考價格'); const r=c.getBoundingClientRect(); return {h:r.height, lh:parseFloat(getComputedStyle(c).lineHeight)||r.height}})()")
check('手機 390：表頭「參考價格」不換行', isinstance(hdr, dict) and hdr['h'] <= hdr['lh'] * 1.5, hdr)
cdp('Emulation.clearDeviceMetricsOverride')
ev("ETFS = JSON.parse(JSON.stringify(__E0)); renderAll(ETFS, __C0, '2026-10-09 22:20', __M0, true, false); true")

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'))
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
