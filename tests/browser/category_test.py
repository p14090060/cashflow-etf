import sys, json, collections
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

FX = json.load(open('tests/fixtures/etf_203.json', encoding='utf-8'))
def set_view(w, h, orient):
    cdp('Emulation.setDeviceMetricsOverride', {'width': w, 'height': h, 'deviceScaleFactor': 1, 'mobile': True,
        'screenOrientation': {'type': orient, 'angle': 90 if orient.startswith('landscape') else 0}})
    wait_ms(500)
def state_of_cat(): return ev("document.getElementById('page-cat').dataset.state")
def defer(name, detail):
    results.append((name, None, detail))
    print('DEFER ' + name + ' -- ' + str(detail))
def click(sel): ev("(function(){ const el=document.querySelector(%s); if(el) el.click(); return !!el; })()" % json.dumps(sel)); wait_ms(60)

# ── FX：固定 fixture（203 檔快照），與 Python 參照實作獨立比對 ──
fx_in = json.dumps([{'code': e['code'], 'name': e['name'], 'div_category': e['div_category']} for e in FX['etfs']], ensure_ascii=False)
got = json.loads(ev("JSON.stringify((%s).map(e=>catClassify(e)))" % fx_in))
exp = [e['category'] for e in FX['etfs']]
mism = [(FX['etfs'][i]['code'], got[i], exp[i]) for i in range(len(exp)) if got[i] != exp[i]]
check('FX-1 fixture has 203 rows, unique codes', len(FX['etfs']) == 203 and len({e['code'] for e in FX['etfs']}) == 203)
check('FX-4/5 JS rules match fixture expected for all 203', not mism, mism[:5])
dist = collections.Counter(exp)
order = ['mcap', 'div', 'active', 'tech', 'overseas', 'theme', 'bond', 'other']
check('FX-3 fixture distribution = approved (16/22/32/20/78/21/6/8)', [dist[k] for k in order] == [16, 22, 32, 20, 78, 21, 6, 8], [dist[k] for k in order])
check('FX-2 single membership: 8 categories sum to 203', sum(dist.values()) == 203)
for code, want in [('00920', 'theme'), ('00923', 'theme'), ('009809', 'theme'), ('00850', 'other'), ('00888', 'other'),
                   ('00928', 'other'), ('00692', 'other'), ('0057', 'other'), ('00682U', 'other'), ('00840B', 'bond'),
                   ('00402A', 'active'), ('00878', 'div'), ('00929', 'tech'), ('00702', 'overseas'), ('00771', 'overseas'),
                   ('00894', 'div'), ('0050', 'mcap'), ('00737', 'tech'), ('00965', 'tech'), ('0055', 'theme')]:
    row = next(e for e in FX['etfs'] if e['code'] == code)
    check('FX-4 %s -> %s' % (code, want), row['category'] == want, row['category'])

# ── LV：live 資料不變條件（不作數字 assertion）──
live = json.loads(ev("JSON.stringify(ETFS.map(e=>[e.code, catClassify(e)]))"))
codes = [c for c, _ in live]
check('LV-1 live: every ETF has exactly one category (sum = ETFS.length)', len(live) == len(set(codes)) == ev("ETFS.length"), len(live))
check('LV-1 live: all categories are among the 8 keys', all(k in order for _, k in live))

# ── UI：八份文件夾、左右各 4 ──
check('UI 8 bands in total', ev("document.querySelectorAll('.cat-band').length") == 8)
check('UI left stack has 4 bands', ev("document.querySelectorAll('#catStackL .cat-band').length") == 4)
check('UI right stack has 4 bands', ev("document.querySelectorAll('#catStackR .cat-band').length") == 4)
want_counts = ','.join('%d 檔' % dist[k] for k in ['mcap', 'div', 'active', 'tech', 'overseas', 'theme', 'bond', 'other'])
check('UI band counts match fixture distribution (DOM order L then R)', ev("[...document.querySelectorAll('.cb-n')].map(x=>x.textContent).join(',')") == want_counts,
      ev("[...document.querySelectorAll('.cb-n')].map(x=>x.textContent).join(',')"))

# ── 開啟「主動式」：前 10 檔、查看更多每次 +10、排序 ──
ev("Router.toBase({base:'tools'}); true"); wait_ms(200)
ev("Router.toBase({base:'cat'}); true"); wait_ms(200)
click('.cat-band[data-k="active"]')
check('OPEN opening/open state after tap', state_of_cat() in ('opening', 'open'), state_of_cat())
wait_ms(400)
check('OPEN state is open after transition', state_of_cat() == 'open', state_of_cat())
check('OPEN shows first 10 rows of 32', ev("document.querySelectorAll('#catList .cat-row').length") == 10)
check('OPEN more button says 還有 22 檔', ev("document.getElementById('catMore').textContent") == '查看更多（還有 22 檔）')
click('#catMore'); check('MORE +10 -> 20 rows', ev("document.querySelectorAll('#catList .cat-row').length") == 20)
click('#catMore'); click('#catMore')
check('MORE caps at 32 rows', ev("document.querySelectorAll('#catList .cat-row').length") == 32)
check('MORE hidden when all shown', ev("document.getElementById('catMore').hidden") is True)
first_code = ev("document.querySelector('#catList .cat-row').dataset.code")
check('DEFAULT sort is numeric code (first 00400A)', first_code == '00400A', first_code)
click('#catSortBtn')
check('SORT name toggled (button shows 名稱)', ev("document.getElementById('catSortBtn').textContent") == '排序：名稱')
check('SORT by name: first 10 equal the first 10 of the full zh-Hant sort', ev("(function(){ const all=catGroup(ETFS).active.map(e=>e.name).sort(new Intl.Collator('zh-Hant',{numeric:true}).compare).slice(0,10); const shown=[...document.querySelectorAll('#catList .cat-row .cr-name')].map(x=>x.textContent); return JSON.stringify(all)===JSON.stringify(shown); })()") is True)
check('SORT toggle resets shown to 10', ev("document.querySelectorAll('#catList .cat-row').length") == 10)
click('#catSortBtn')

# ── 次要區切換：只 replace，不增加 history ──
L = ev("history.length")
ev("(function(){ const b=document.querySelector('#catStrip button[data-k=\"mcap\"]'); b.click(); return true; })()"); wait_ms(120)
check('STRIP switch folder to 市值 replaces (no new entry)', ev("history.length") == L, '%s vs %s' % (ev("history.length"), L))
check('STRIP switch: router folder key = mcap', ev("Router.state().stack[0].key") == 'mcap')
check('STRIP switch: title shows 市值型', ev("document.getElementById('catName').textContent") == '市值型')
check('STRIP switch: 市值型 shows first 10 (resets shown)', ev("document.querySelectorAll('#catList .cat-row').length") == 10)
check('STRIP switch: more says 還有 6 檔', ev("document.getElementById('catMore').textContent") == '查看更多（還有 6 檔）')
click('#catStrip button[data-k="active"]')

# ── 持股異動分段：可見、treemap 有畫、選檔後 ui 記住 ──
ev("(function(){ document.querySelector('#catSeg button[data-v=\"flow\"]').click(); return true; })()"); wait_ms(250)
check('FLOW segment shows flow view', ev("Category.isFlowVisible()") is True)
check('FLOW treemap drawn with non-zero children', (ev("document.getElementById('treemap').children.length") or 0) > 0)
fl_code = ev("Object.keys(_flowData.etfs)[1]")
ev("flowSelect('%s'); true" % fl_code); wait_ms(120)
check('FLOW select stored in folder ui', ev("Router.state().stack[0].ui.code") == fl_code, fl_code)
ev("(function(){ document.querySelector('#catSeg button[data-v=\"list\"]').click(); return true; })()"); wait_ms(120)
check('FLOW back to list segment', ev("Category.isFlowVisible()") is False)

# ── 從資料夾進入 Detail，返回後排序／已展開數／捲動保留 ──
click('#catSortBtn')
click('#catMore')
row_code = ev("document.querySelectorAll('#catList .cat-row')[3].dataset.code")
ev("(function(){ document.querySelectorAll('#catList .cat-row')[3].click(); return true; })()"); wait_ms(250)
check('DETAIL opened from folder row', ev("!document.getElementById('gsPanel').hidden") is True and ev("_curEtfCode") == row_code)
ev("(function(){ closeDetail(); return true; })()"); wait_ms(250)
check('AFTER DETAIL BACK sort kept (名稱)', ev("document.getElementById('catSortBtn').textContent") == '排序：名稱')
check('AFTER DETAIL BACK shown kept (20)', ev("document.querySelectorAll('#catList .cat-row').length") == 20)
check('AFTER DETAIL BACK folder still open', state_of_cat() == 'open')

# ── Esc 只退一層：Detail → 資料夾 ──
ev("(function(){ document.querySelectorAll('#catList .cat-row')[0].click(); return true; })()"); wait_ms(200)
ev("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); true"); wait_ms(250)
check('ESC 1: closes Detail only', ev("!document.getElementById('gsPanel').hidden") is False and state_of_cat() == 'open')
ev("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); true"); wait_ms(350)
check('ESC 2: closes folder', state_of_cat() == 'overview' and ev("Router.state().stack.length") == 0)

# ── ✕ 收合 + 連點只開一次 ──
ev("window.__pushes = 0; const _p = history.pushState.bind(history); history.pushState = function(){ window.__pushes++; return _p.apply(history, arguments); }; true")
ev("(function(){ const b=document.querySelector('.cat-band[data-k=\"tech\"]'); b.click(); b.click(); b.click(); return true; })()"); wait_ms(400)
check('DOUBLE TAP opens once (exactly one pushState)', ev("window.__pushes") == 1, ev("window.__pushes"))
ev("history.pushState = (function(){ const p = Object.getPrototypeOf(history).pushState; return p; })(); true")
click('#catClose'); wait_ms(320)
check('CLOSE ✕ returns to overview', state_of_cat() == 'overview')

# ── 減少動態效果：狀態立即切換，沒有過場 ──
cdp('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
click('.cat-band[data-k="div"]')
check('REDUCED MOTION opens immediately', state_of_cat() == 'open', state_of_cat())
check('REDUCED MOTION transition duration 0', ev("getComputedStyle(document.querySelector('#page-cat .cat-main')).transitionDuration") in ('0s', '0s, 0s'))
click('#catClose')
check('REDUCED MOTION closes immediately', state_of_cat() == 'overview', state_of_cat())
cdp('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})

# ── 空分類與錯誤狀態 ──
ev("window.__origETFS = ETFS; ETFS = ETFS.filter(e => catClassify(e) !== 'bond'); Category.refresh(); true")
click('.cat-band[data-k="bond"]'); wait_ms(300)
check('EMPTY category shows 目前沒有符合這個分類的 ETF', '目前沒有符合這個分類的 ETF' in (ev("document.getElementById('catList').innerText") or ''))
click('#catClose'); wait_ms(320)
ev("ETFS = window.__origETFS; Category.refresh(); true")
check('EMPTY restored: bond band 6 檔', ev("document.getElementById('cbN-bond').textContent") == '6 檔')
ev("window.__origETFS2 = ETFS; ETFS = []; Category.refresh(); true")
check('ERROR band counts show —', ev("document.getElementById('cbN-mcap').textContent") == '—')
click('.cat-band[data-k="mcap"]'); wait_ms(300)
check('ERROR open shows 資料暫時無法取得', '資料暫時無法取得' in (ev("document.getElementById('catList').innerText") or ''))
click('#catClose'); wait_ms(320)
ev("ETFS = window.__origETFS2; Category.refresh(); true")

# ── 導覽與工具頁、自選空狀態 ──
ev("switchPage('watch'); true"); wait_ms(120)
check('NAV watch shows 自選 empty state', ev("document.getElementById('page-watch').classList.contains('active')") is True and '自選 ETF 功能即將開放' in ev("document.getElementById('page-watch').innerText"))
check('NAV has four bottom buttons', ev("document.querySelectorAll('.bottom-nav .nav-btn').length") == 4)
ev("switchPage('tools'); true"); wait_ms(120)
ev("(function(){ document.querySelector('#page-tools .tool-card').click(); return true; })()"); wait_ms(120)
check('TOOLS card opens 配息 subpage', ev("document.getElementById('page-div').classList.contains('active')") is True)
ev("(function(){ history.back(); return true; })()"); wait_ms(250)
check('TOOLS back returns to tools list', ev("document.getElementById('page-tools').classList.contains('active')") is True)

# ── 低高度：Phase 1 gs-ckm 觸發時，次要區與說明讓位；清單仍可用 ──
ev("switchPage('cat'); true"); wait_ms(150)
click('.cat-band[data-k="active"]'); wait_ms(400)
set_view(844, 390, 'landscapePrimary'); wait_ms(200)
ev("(function(){ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); return true; })()"); wait_ms(300)
set_view(844, 170, 'landscapePrimary'); wait_ms(400)
check('LR-4 ckm on at 844x170 (keyboard)', ev("document.body.classList.contains('gs-ckm')") is True)
check('LR-4 strip hidden in ckm', ev("getComputedStyle(document.getElementById('catStrip')).display") == 'none')
list_h = ev("document.getElementById('catList').getBoundingClientRect().height") or 0
# 844×170 鍵盤開：全站免責 .disclaimer（85px，Phase 1 既有、法遵）不在分類頁內，無法在不改 Phase 1 行為的前提下騰出 44px。
# 這是需要決策的已知限制，不是 PASS：決策前記為 DEFER，並驗證使用者看得到的 fallback（提示列在標題列內、可視區內）。
defer('LR-4 list >= 44px at 844x170 keyboard (blocked by Phase 1 global disclaimer; needs decision)', 'list height=%s' % list_h)
hint_ok = ev("(function(){ const h=document.getElementById('catHint'); if(!h||h.hidden) return false; const r=h.getBoundingClientRect(); const vv=window.visualViewport; const top=vv?vv.offsetTop:0; const bot=vv?vv.offsetTop+vv.height:innerHeight; return r.bottom>top && r.top<bot && h.textContent==='收起鍵盤可看完整清單'; })()")
check('LR-4 fallback hint "收起鍵盤可看完整清單" is inside the visible region', hint_ok is True)
check('LR-4 search input is visible inside viewport', ev("(function(){const r=document.getElementById('gsearch').getBoundingClientRect(); return r.top>=0 && r.bottom<=innerHeight;})()") is True)

# LR-7：20px，offsetTop = 0（使用者看得到的搜尋框）
set_view(844, 20, 'landscapePrimary'); wait_ms(400)
rect = ev("(function(){const r=document.getElementById('gsearch').getBoundingClientRect(); return {top:r.top,bottom:r.bottom};})()")
vis_top = ev("visualViewport ? visualViewport.offsetTop : 0")
vis_h = ev("visualViewport ? visualViewport.height : innerHeight")
check('LR-7 20px: search input top within visible region (≤2px)', isinstance(rect, dict) and rect['top'] - vis_top <= 2, json.dumps(rect) + ' visTop=' + str(vis_top))
hit = ev("(function(){const r=document.getElementById('gsearch').getBoundingClientRect(); const x=r.left+r.width/2, y=Math.min(r.top+r.height/2, innerHeight-1); const e=document.elementFromPoint(x,y); return !!e && (e.id==='gsearch' || document.getElementById('gsearch').contains(e));})()")
check('LR-7 20px: elementFromPoint hits search input (not occluded)', hit is True)
check('LR-7 20px: no horizontal scroll', ev("document.documentElement.scrollWidth <= innerWidth") is True)

# LR-9：鍵盤關閉後恢復
set_view(844, 390, 'landscapePrimary'); wait_ms(300)
ev("(function(){ const i=document.getElementById('gsearch'); i.blur(); i.dispatchEvent(new Event('blur')); return true; })()"); wait_ms(400)
check('LR-9 restore: ckm off after keyboard closes', ev("document.body.classList.contains('gs-ckm')") is False)
check('LR-9 restore: strip visible again', ev("getComputedStyle(document.getElementById('catStrip')).display") != 'none')
check('LR-9 restore: category list visible', ev("!document.getElementById('catList').hidden && document.getElementById('catList').getBoundingClientRect().height > 0") is True)
check('LR-9 restore: bottom nav visible', ev("getComputedStyle(document.querySelector('.bottom-nav')).display") != 'none')

# LR-8：offsetTop > 0（前置條件：必須真的產生 offsetTop）
cdp('Emulation.setPageScaleFactor', {'pageScaleFactor': 2})
wait_ms(300)
cdp('Input.synthesizeScrollGesture', {'x': 200, 'y': 400, 'yDistance': -260, 'gestureSourceType': 'touch', 'speed': 800})
wait_ms(400)
off = ev("visualViewport ? visualViewport.offsetTop : 0")
if isinstance(off, (int, float)) and off > 0:
    check('LR-8 visualViewport.offsetTop > 0 (precondition met)', True, 'offsetTop=%s' % off)
else:
    defer('LR-8 offsetTop > 0 keyboard case (headless cannot pan visual viewport; needs iPhone Chrome real device)', 'offsetTop=%s' % off)
cdp('Emulation.setPageScaleFactor', {'pageScaleFactor': 1})

set_view(390, 844, 'portraitPrimary')
exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if r[1] is False]
defers = [r for r in results if r[1] is None]
print('\nTOTAL %d  PASS %d  FAIL %d  DEFER %d' % (len(results), len(results) - len(fails) - len(defers), len(fails), len(defers)))
for r in defers: print('  DEFER: ' + r[0] + ' -- ' + str(r[2]))
ws.close()
