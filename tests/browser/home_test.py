"""Phase 5 CP3：首頁入口大廳（PHASE5_PLAN §2；HM-1～3、PZ-1～13、TV-1～3、MG-3 LAZY）。

以 fixture 方式驗：複製實際 ETFS，改寫 signal／cur_vol／div_frequency 後呼叫 renderAll()（與 30 秒輪詢同一入口）。
執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
"""
import sys, json
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

ev("clearInterval(_pollTimer); window.__routerManualTimers = true; true")   # 停輪詢，避免真資料蓋掉 fixture

def st(): return ev("JSON.stringify(Router.state())")

# fixture：實際 ETFS 的深拷貝，全部先設成 dear、配息型、低成交量
ev("""window.__base = JSON.parse(JSON.stringify(ETFS));
window.__mk = function (spec) {            // spec: {code: {signal, cur_vol, div_frequency, heat}}
  const arr = JSON.parse(JSON.stringify(window.__base));
  arr.forEach((e, i) => { e.signal = 'dear'; e.cur_vol = 1000 + i; e.div_frequency = e.div_frequency === '不配息' ? '季配' : (e.div_frequency || '季配'); if (!(e.price > 0)) e.price = 10; });
  arr.forEach(e => { if (spec[e.code]) Object.assign(e, spec[e.code]); });
  return arr;
};
window.__render = function (arr) { renderAll(arr, CALENDAR, '2026-10-06 10:00:00', null, true, false); };
true""")
codes = ev("window.__base.filter(e=>e.price>0).map(e=>e.code)")
check('fixture base has >= 130 ETFs', isinstance(codes, list) and len(codes) >= 130, len(codes or []))

def pz_codes(): return ev("[...document.querySelectorAll('#pzList .pz-row')].map(b=>b.dataset.code)")
def pz_tags(): return ev("[...document.querySelectorAll('#pzList .pz-row')].map(b=>{const t=b.lastElementChild; return t.className+'|'+t.textContent})")

# ── HM-1 首頁結構
ev("switchPage('today'); true"); wait_ms(150)
order = ev("""(()=>{const p=document.getElementById('page-today'); const ids=['moodText','homeGoCat','homeGoWatch','pzTitle','pzList','tvTitle','waitItems'];
  const els=ids.map(i=>document.getElementById(i)); if(els.some(e=>!e||!p.contains(e))) return 'missing';
  for(let i=1;i<els.length;i++) if(!(els[i-1].compareDocumentPosition(els[i]) & Node.DOCUMENT_POSITION_FOLLOWING)) return 'order@'+ids[i];
  return 'ok';})()""")
check('HM-1 order: A-1 → 兩大入口 → 價格合理區 → 今日成交量 TOP 10', order == 'ok', order)
check('HM-1 no A-4 / YouTube card / .buy-card / LAZY on home',
      ev("""(()=>{const p=document.getElementById('page-today'); return !document.getElementById('todayCode') && !document.getElementById('todayResult')
        && !p.querySelector('.buy-card,.range-track,.div-pill,.entry-card') && ![...p.querySelectorAll('button')].some(b=>/YouTube/.test(b.textContent))})()""") is True)
check('HM-1 no input box on home (single search = Header)', ev("document.getElementById('page-today').querySelectorAll('input,textarea,select').length") == 0)
check('MG-3 LAZY_WATCHLIST undefined in frontend (config.js retired)',
      ev("typeof LAZY_WATCHLIST === 'undefined' && !document.querySelector('script[src*=\"config.js\"]')") is True)

# ── HM-2 兩大入口：與底部導覽相同（replace E0，不新增 entry）
for btn, base, page in (('homeGoCat', 'cat', 'page-cat'), ('homeGoWatch', 'watch', 'page-watch')):
    ev("switchPage('today'); true"); wait_ms(150)
    h0 = ev("history.length")
    ev("document.getElementById('%s').click(); true" % btn); wait_ms(200)
    s = json.loads(st())
    check('HM-2 %s → %s：base=%s、stack []、history.length 不變' % (btn, page, base),
          s['base'] == base and s['stack'] == [] and ev("history.length") == h0
          and ev("document.getElementById('%s').classList.contains('active')" % page) is True, (s, h0, ev("history.length")))
ev("switchPage('today'); true"); wait_ms(100)
ev("document.getElementById('homeGoCat').click(); true"); wait_ms(200)
check('HM-2 分類為總覽狀態', ev("document.getElementById('page-cat').dataset.state") == 'overview')

# ── HM-3 首頁搜尋 = Header 全站搜尋；查無不估算
ev("switchPage('today'); true"); wait_ms(150)
ev("{const i=document.getElementById('gsearch'); i.value='9999'; i.dispatchEvent(new Event('input'));} true"); wait_ms(250)
dd = ev("document.getElementById('gsearchList').innerText") or ''
check('HM-3 Header search works on home; 查無 shown, no estimate', ('查無' in dd or '找不到' in dd) and '估算' not in dd, dd[:80])
ev("gsClear(); true"); wait_ms(100)

# ── PZ：fixture A（14 檔符合，> 10）
TOPN = codes[:120]
spec = {}
for i, c in enumerate(TOPN[:100]):
    spec[c] = {'cur_vol': 900000 - i * 1000}
cheaps = [TOPN[3], TOPN[20], TOPN[50], TOPN[7]]          # 4 檔 cheap（成交量順序：3,7,20,50）
fairs  = [TOPN[1], TOPN[2], TOPN[10], TOPN[11], TOPN[12], TOPN[30], TOPN[31], TOPN[40], TOPN[60], TOPN[99]]   # 10 檔 fair
for c in cheaps: spec[c]['signal'] = 'cheap'
for c in fairs:  spec[c]['signal'] = 'fair'
excl = {
    'hot': TOPN[4], 'dear': TOPN[5], 'bond': TOPN[6],
    'nodiv': TOPN[8], 'out_of_top100': TOPN[105],
}
spec[excl['hot']]['signal'] = 'hot'
spec[excl['bond']]['signal'] = 'bond'
spec[excl['nodiv']].update({'signal': 'cheap', 'div_frequency': '不配息'})
spec[excl['out_of_top100']] = {'signal': 'cheap', 'cur_vol': 500}          # 排在 100 名外
ev("window.__specA = %s; window.__render(window.__mk(window.__specA)); true" % json.dumps(spec)); wait_ms(150)
exp_order = [TOPN[i] for i in (3, 7, 20, 50)] + [TOPN[i] for i in (1, 2, 10, 11, 12, 30, 31, 40, 60, 99)]

shown = pz_codes()
check('PZ-6 count text = 全部符合檔數', ev("document.getElementById('pzCount').textContent") == '目前共有 14 檔 ETF 符合價格條件', ev("document.getElementById('pzCount').textContent"))
check('PZ-8 >10：預設只顯示前 10', shown == exp_order[:10], shown)
check('PZ-5 排序：cheap 在前、fair 在後；同狀態 cur_vol 由高到低', shown == exp_order[:10], (shown, exp_order[:10]))
check('PZ-8 「查看全部 14 檔」按鈕', ev("(()=>{const m=document.getElementById('pzMore'); return !m.hidden && m.textContent==='查看全部 14 檔'})()") is True, ev("document.getElementById('pzMore').textContent"))
ev("document.getElementById('pzMore').click(); true"); wait_ms(100)
check('PZ-8 展開 → 14 檔、按鈕變「收起」', pz_codes() == exp_order and ev("document.getElementById('pzMore').textContent") == '收起', pz_codes())
all_shown = set(pz_codes())
check('PZ-1 母體＝成交量前 100（100 名外的 cheap 不納入）', excl['out_of_top100'] not in all_shown)
check('PZ-2 hot／dear／bond 不納入', not ({excl['hot'], excl['dear'], excl['bond']} & all_shown))
check('PZ-3 不配息排除', excl['nodiv'] not in all_shown)
check('PZ-4 不用 LAZY：非舊白名單的 fair 也納入（%s、%s）' % (TOPN[30], TOPN[99]), {TOPN[30], TOPN[99]} <= all_shown)
# PZ-9 輪詢重繪保留展開
ev("window.__render(window.__mk(window.__specA)); true"); wait_ms(150)
check('PZ-9 輪詢重繪（renderAll）後仍為展開', len(pz_codes()) == 14 and ev("document.getElementById('pzMore').textContent") == '收起')
ev("document.getElementById('pzMore').click(); true"); wait_ms(100)
check('PZ-8 收起 → 回到 10 檔', len(pz_codes()) == 10)
tags = pz_tags()
check('PZ-13 標籤：便宜＝sig-cheap、合理＝sig-fair；無「合理✓」',
      all((t.startswith('sig-cheap|') and t.endswith('便宜')) or (t.startswith('sig-fair|') and t.endswith('合理')) for t in tags)
      and '✓' not in (ev("document.getElementById('page-today').innerText") or ''), tags)
row = ev("""(()=>{const b=document.querySelector('#pzList .pz-row'); const r=b.getBoundingClientRect(); return {tag:b.tagName, h:r.height,
  kids:b.children.length, code:b.children[0].textContent, name:b.children[1].textContent,
  ell:getComputedStyle(b.children[1]).textOverflow}})()""")
check('PZ-12 精簡列：button、代碼＋名稱（省略號）＋標籤、無大卡', row['tag'] == 'BUTTON' and row['kids'] == 3 and row['ell'] == 'ellipsis'
      and ev("document.querySelectorAll('#page-today .buy-card').length") == 0, row)

# PZ-11 整列點擊 → Detail；Back → 首頁
# CP6b FIX-2：forward entry 會被截斷，history.length 不能當證據 → 計 history.pushState 次數並比對 history.state
h0 = ev("history.length")
ev("""(()=>{ window.__hc = {push:0, rep:0};
  if (!window.__hspy) { window.__hspy = 1; const P = history.pushState, Rp = history.replaceState;
    history.pushState = function () { window.__hc.push++; return P.apply(history, arguments); };
    history.replaceState = function () { window.__hc.rep++; return Rp.apply(history, arguments); }; }
  return true; })()""")
ev("document.querySelector('#pzList .pz-row').click(); true"); wait_ms(300)
s = json.loads(st())
check('PZ-11 整列點擊開 Detail', ev("!document.getElementById('gsPanel').hidden") is True and s['stack'][-1]['t'] == 'detail'
      and s['stack'][-1]['code'] == exp_order[0] and ev("history.length") <= h0 + 1, s)
pk = ev("({push:window.__hc.push, same:JSON.stringify(history.state)===JSON.stringify(Router.state()), n:history.state.stack.length, t:history.state.stack.slice(-1)[0].t, code:history.state.stack.slice(-1)[0].code})")
check('PZ-11 push 防線：history.pushState 恰好 1 次、history.state＝Router.state()、頂層 detail＝%s' % exp_order[0],
      pk['push'] == 1 and pk['same'] and pk['n'] == 1 and pk['t'] == 'detail' and pk['code'] == exp_order[0], pk)
ev("history.back(); true"); wait_ms(400)
check('PZ-11 Back → 回首頁、Detail 關閉', ev("document.getElementById('gsPanel').hidden") is True and json.loads(st())['base'] == 'home'
      and json.loads(st())['stack'] == [] and ev("document.getElementById('page-today').classList.contains('active')") is True, st())

# PZ-7 ≤ 10：全部顯示、無按鈕
spec7 = {c: {'cur_vol': 900000 - i * 1000} for i, c in enumerate(TOPN[:100])}
for c in (TOPN[5], TOPN[15], TOPN[25]): spec7[c]['signal'] = 'fair'
spec7[TOPN[40]]['signal'] = 'cheap'
ev("window.__render(window.__mk(%s)); true" % json.dumps(spec7)); wait_ms(150)
check('PZ-7 ≤10：全部顯示、無「查看全部」', pz_codes() == [TOPN[40], TOPN[5], TOPN[15], TOPN[25]] and ev("document.getElementById('pzMore').hidden") is True
      and ev("document.getElementById('pzCount').textContent") == '目前共有 4 檔 ETF 符合價格條件', pz_codes())

# PZ-10 0 檔：只顯示一句、不補位
spec0 = {c: {'cur_vol': 900000 - i * 1000} for i, c in enumerate(TOPN[:100])}
spec0[TOPN[105]] = {'signal': 'cheap', 'cur_vol': 500}
ev("window.__render(window.__mk(%s)); true" % json.dumps(spec0)); wait_ms(150)
check('PZ-10 0 檔：只顯示「目前沒有 ETF 符合價格條件」、無列、無按鈕、無計數',
      ev("document.getElementById('pzList').innerText.trim()") == '目前沒有 ETF 符合價格條件' and len(pz_codes()) == 0
      and ev("document.getElementById('pzMore').hidden && document.getElementById('pzCount').hidden") is True)

# ── TV：今日成交量 TOP 10
specT = {c: {'cur_vol': 900000 - i * 1000, 'heat': 1} for i, c in enumerate(TOPN[:100])}
specT[TOPN[50]]['heat'] = 9999          # heat 最高但成交量第 51
specT[TOPN[2]]['signal'] = 'fair'
ev("window.__render(window.__mk(%s)); true" % json.dumps(specT)); wait_ms(150)
check('TV-1 標題「今日成交量 TOP 10」', ev("document.getElementById('tvTitle').textContent.trim()") == '今日成交量 TOP 10')
tv = ev("[...document.querySelectorAll('#waitItems .home-row')].map(b=>b.dataset.code)")
check('TV-2 cur_vol 前 10（heat 最高者不在內）', tv == TOPN[:10] and TOPN[50] not in tv, tv)
check('TV-1 價格狀態「合理」（無 ✓）', '合理' in (ev("document.querySelector('#waitItems .home-row:nth-child(3)').innerText") or '')
      and '✓' not in (ev("document.getElementById('waitItems').innerText") or ''))
h0 = ev("history.length")
ev("document.querySelector('#waitItems .home-row:nth-child(2)').click(); true"); wait_ms(300)
check('TV-3 整列點擊開 Detail', ev("!document.getElementById('gsPanel').hidden") is True and json.loads(st())['stack'][-1]['code'] == TOPN[1]
      and len(json.loads(st())['stack']) == 1 and ev("history.length") <= h0 + 1)   # 先前 Back 留下的 forward entry 會被 push 取代
ev("history.back(); true"); wait_ms(400)
check('TV-3 Back → 回首頁', ev("document.getElementById('gsPanel').hidden") is True and json.loads(st())['base'] == 'home' and json.loads(st())['stack'] == [])

# ── 390px 直向：可讀性與 touch target（不為塞第一屏縮字）
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
ev("window.__render(window.__mk(window.__specA)); window.scrollTo(0,0); true"); wait_ms(300)
lay = ev("""(()=>{const p=document.getElementById('page-today'); const fs=[];
  p.querySelectorAll('*').forEach(el=>{ if([...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())){ const f=parseFloat(getComputedStyle(el).fontSize); if(el.offsetParent!==null) fs.push([f, el.className||el.tagName, el.textContent.trim().slice(0,12)]); }});
  const small=fs.filter(x=>x[0]<14);
  const tgt=[...p.querySelectorAll('button')].filter(b=>b.offsetParent!==null).map(b=>b.getBoundingClientRect().height);
  return {small:small.slice(0,8), minBtn:Math.min(...tgt), entryMin:Math.min(...[...p.querySelectorAll('.home-entry')].map(b=>b.getBoundingClientRect().height)),
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          entriesTop: document.getElementById('homeGoWatch').getBoundingClientRect().bottom};})()""")
check('UI 390px：首頁可見文字皆 ≥ 14px', lay['small'] == [], lay['small'])
check('UI 390px：首頁按鈕 ≥ 44px、兩大入口 ≥ 64px', lay['minBtn'] >= 44 and lay['entryMin'] >= 64, (lay['minBtn'], lay['entryMin']))
check('UI 390px：無水平捲動', lay['overflow'] <= 0, lay['overflow'])
check('UI 390px：兩大入口在第一屏內', lay['entriesTop'] <= 844, lay['entriesTop'])
cdp('Emulation.clearDeviceMetricsOverride')

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'), (e['params']['exceptionDetails'].get('exception', {}) or {}).get('description', '')[:160])
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
