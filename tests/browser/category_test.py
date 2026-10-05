import sys, json, collections, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0
# 停用快取後重新載入：避免瀏覽器拿到舊的 js/*.js（同一個 ?v= 版本號會命中快取）
cdp('Network.setCacheDisabled', {'cacheDisabled': True})
cdp('Page.reload'); time.sleep(2.2); wait_ms(600)

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
ev("(function(){ if (document.getElementById('catMain').classList.contains('cat-inside')) document.getElementById('catExpand').click(); return true; })()"); wait_ms(200)
ev("(function(){ const b=document.querySelector('#catStrip button[data-k=\"mcap\"]'); b.click(); return true; })()"); wait_ms(120)
check('STRIP switch folder to 市值 replaces (no new entry)', ev("history.length") == L, '%s vs %s' % (ev("history.length"), L))
check('STRIP switch: router folder key = mcap', ev("Router.state().stack[0].key") == 'mcap')
check('STRIP switch: title shows 市值型', ev("document.getElementById('catName').textContent") == '市值型')
check('STRIP switch: 市值型 shows first 10 (resets shown)', ev("document.querySelectorAll('#catList .cat-row').length") == 10)
check('STRIP switch: more says 還有 6 檔', ev("document.getElementById('catMore').textContent") == '查看更多（還有 6 檔）')
ev("(function(){ if (document.getElementById('catMain').classList.contains('cat-inside')) document.getElementById('catExpand').click(); return true; })()"); wait_ms(200)
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

# ── FD（PHASE3_PLAN §9.2 F-d）：持股異動可見時，視窗、方向、visualViewport 事件都重繪；清單可見時不重繪 ──
ev("(function(){ document.querySelector('#catSeg button[data-v=\"flow\"]').click(); return true; })()"); wait_ms(300)
ev("window.__rf = 0; window.__rfOrig = window.renderFlow; window.renderFlow = function(){ window.__rf++; return window.__rfOrig.apply(this, arguments); }; true")
ev("visualViewport.dispatchEvent(new Event('resize')); true")
check('FD-1 visualViewport resize redraws flow when visible', ev("window.__rf") == 1, ev("window.__rf"))
ev("visualViewport.dispatchEvent(new Event('scroll')); true")
check('FD-2 visualViewport scroll redraws flow when visible', ev("window.__rf") == 2, ev("window.__rf"))
ev("window.dispatchEvent(new Event('orientationchange')); true")
check('FD-3 orientationchange redraws flow when visible', ev("window.__rf") == 3, ev("window.__rf"))
ev("window.dispatchEvent(new Event('resize')); true")
check('FD-4 window resize redraws flow when visible', ev("window.__rf") == 4, ev("window.__rf"))
ev("(function(){ document.querySelector('#catSeg button[data-v=\"list\"]').click(); return true; })()"); wait_ms(150)
ev("window.__rf = 0; true")
ev("visualViewport.dispatchEvent(new Event('resize')); window.dispatchEvent(new Event('orientationchange')); true")
check('FD-5 list view visible: visualViewport/orientation do not redraw flow', ev("window.__rf") == 0, ev("window.__rf"))
ev("window.renderFlow = window.__rfOrig; true")
set_view(390, 844, 'portraitPrimary')
ev("(function(){ document.querySelector('#catSeg button[data-v=\"flow\"]').click(); return true; })()"); wait_ms(300)
w0 = ev("document.getElementById('treemap').clientWidth")
set_view(360, 780, 'portraitPrimary'); wait_ms(400)
w1 = ev("document.getElementById('treemap').clientWidth")
fit_ok = ev("(function(){ const b=document.getElementById('treemap'); const W=b.clientWidth; const cs=[...b.querySelectorAll('.tm-cell')]; return cs.length>0 && cs.every(c => parseFloat(c.style.left)+parseFloat(c.style.width) <= W+1); })()")
check('FD-6 resize 390→360: treemap follows container width and cells stay inside', w1 < w0 and fit_ok is True, (w0, w1, fit_ok))
set_view(390, 844, 'portraitPrimary')
ev("(function(){ document.querySelector('#catSeg button[data-v=\"list\"]').click(); return true; })()"); wait_ms(150)

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

# ── 低高度：Phase 1 gs-ckm 觸發時，次要區與說明讓位；清單不足一列時走 fallback ──
# LR-4（PO 決策方案 B，responsive fallback，已核准；不是 DEFER）：844×170 鍵盤開、可用高度 < 44px
#   → 不強制顯示清單、顯示「收起鍵盤以查看 ETF 清單」、免責保留、分類狀態不遺失；鍵盤收起後自動恢復（見 LR-9 之後的 LR-4 恢復檢查）。
ev("switchPage('cat'); true"); wait_ms(150)
click('.cat-band[data-k="active"]'); wait_ms(400)
set_view(844, 390, 'landscapePrimary'); wait_ms(200)
ev("document.getElementById('catMore').click(); true"); wait_ms(120)     # 20 檔，使清單可捲動
ev("document.getElementById('catList').scrollTop = 40; true"); wait_ms(300)
lr4_scroll = ev("document.getElementById('catList').scrollTop")
lr4_ui = ev("JSON.stringify(Router.state().stack[0].ui)")
check('LR-4 precondition: list scrollable and scrolled to ~40px before keyboard', lr4_scroll > 0 and ev("document.getElementById('catList').scrollHeight > document.getElementById('catList').clientHeight") is True, lr4_scroll)
ev("(function(){ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); return true; })()"); wait_ms(300)
set_view(844, 170, 'landscapePrimary'); wait_ms(400)
check('LR-4 ckm on at 844x170 (keyboard)', ev("document.body.classList.contains('gs-ckm')") is True)
check('LR-4 strip hidden in ckm (Phase 1 behavior)', ev("getComputedStyle(document.getElementById('catStrip')).display") == 'none')
check('LR-4 fallback: list not forced (collapsed, 0px, hidden)', ev("(function(){ const l=document.getElementById('catList'); return getComputedStyle(l).visibility==='hidden' && l.getBoundingClientRect().height===0; })()") is True,
      ev("document.getElementById('catList').getBoundingClientRect().height"))
check('LR-4 fallback: more button collapsed', ev("getComputedStyle(document.getElementById('catMore')).display") == 'none')
check('LR-4 fallback: hint shows "收起鍵盤以查看 ETF 清單"', ev("(function(){ const h=document.getElementById('catHint'); return !h.hidden && h.textContent==='收起鍵盤以查看 ETF 清單'; })()") is True)
hint_ok = ev("(function(){ const h=document.getElementById('catHint'); if(!h||h.hidden) return false; const r=h.getBoundingClientRect(); const vv=window.visualViewport; const top=vv?vv.offsetTop:0; const bot=vv?vv.offsetTop+vv.height:innerHeight; return r.bottom>top && r.top<bot; })()")
check('LR-4 fallback hint is inside the visible region', hint_ok is True)
check('LR-4 Phase 1 disclaimer kept (not hidden by fallback)', ev("getComputedStyle(document.querySelector('.disclaimer')).display") != 'none')
check('LR-4 fallback keeps folder state (sort/shown/scroll in Router layer)', ev("JSON.stringify(Router.state().stack[0].ui)") == lr4_ui, (ev("JSON.stringify(Router.state().stack[0].ui)"), lr4_ui))
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
# LR-4 恢復（PO 核准：鍵盤收起後分類清單必須自動恢復；狀態不得遺失）
check('LR-4 restore: fallback hint hidden after keyboard closes', ev("document.getElementById('catHint').hidden") is True)
check('LR-4 restore: list expanded again (>= 44px, visible)', ev("(function(){ const l=document.getElementById('catList'); return getComputedStyle(l).visibility!=='hidden' && l.getBoundingClientRect().height >= 44; })()") is True,
      ev("document.getElementById('catList').getBoundingClientRect().height"))
check('LR-4 restore: list scroll position kept (~40px)', abs((ev("document.getElementById('catList').scrollTop") or 0) - (lr4_scroll or 0)) <= 2, (ev("document.getElementById('catList').scrollTop"), lr4_scroll))
check('LR-4 restore: sort/shown/scroll kept in Router layer', ev("JSON.stringify(Router.state().stack[0].ui)") == lr4_ui, (ev("JSON.stringify(Router.state().stack[0].ui)"), lr4_ui))
MORE_EL = "(document.querySelector('.cat-more-in') || document.getElementById('catMore'))"
check('LR-4 restore: more button back (12 remaining; inside list when cat-tight3)', ev("getComputedStyle(%s).display" % MORE_EL) != 'none' and ev("%s.textContent" % MORE_EL) == '查看更多（還有 12 檔）', ev("%s.textContent" % MORE_EL))

# ── BL（Codex blocker）：844×390、無鍵盤：清單實際可見 ≥ 44px、不被導覽列遮住、可捲動／操作、無水平 overflow；回到一般高度版面正常 ──
BL_JS = """(function(){
  const list = document.getElementById('catList'), nav = document.querySelector('.bottom-nav');
  const r = list.getBoundingClientRect(), navR = nav.getBoundingClientRect();
  const vv = window.visualViewport;
  const visTop = vv ? vv.offsetTop : 0;
  const visBottom = Math.min(vv ? vv.offsetTop + vv.height : innerHeight, navR.top);
  const top = Math.max(r.top, visTop), bottom = Math.min(r.bottom, visBottom);
  const visH = Math.max(0, bottom - top);
  const cx = (Math.max(r.left, 0) + Math.min(r.right, innerWidth)) / 2;
  const e = visH > 0 ? document.elementFromPoint(cx, top + visH / 2) : null;
  return { visH: visH, listTop: r.top, listBottom: r.bottom, navTop: navR.top, navDisplay: getComputedStyle(nav).display,
           hitInList: !!e && list.contains(e), hitNav: !!e && nav.contains(e),
           scrollable: list.scrollHeight > list.clientHeight, hScroll: document.documentElement.scrollWidth > innerWidth,
           pageHScroll: document.getElementById('page-cat').scrollWidth > document.getElementById('page-cat').clientWidth + 1,
           tight3: document.getElementById('catMain').classList.contains('cat-tight3'),
           innerMore: document.querySelectorAll('#catList .cat-more-in').length };
})()"""
ev("(function(){ if (document.getElementById('page-cat').dataset.state !== 'open') { switchPage('cat'); } return true; })()"); wait_ms(200)
bl_state = ev("document.getElementById('page-cat').dataset.state")
check('BL precondition: 844x390 keyboard off, folder open (active), nav visible', bl_state == 'open' and ev("document.body.classList.contains('gs-ckm')") is False and ev("Router.state().stack[0].key") == 'active' and ev("getComputedStyle(document.querySelector('.bottom-nav')).display") != 'none', (bl_state, ev("Router.state().stack.map(l=>l.key)")))
bl = ev(BL_JS)
check('BL-1 list actual visible intersection with viewport and above nav >= 44px', bl['visH'] >= 44, bl)
check('BL-2 bottom nav does not overlap the list (list bottom <= nav top)', bl['listBottom'] <= bl['navTop'] + 0.5, bl)
check('BL-3 elementFromPoint at visible list center hits the list, not the bottom nav', bl['hitInList'] is True and bl['hitNav'] is False, bl)
check('BL-4 no horizontal overflow (document and category page)', bl['hScroll'] is False and bl['pageHScroll'] is False, bl)
check('BL-5 layout is the no-keyboard low-height layer (cat-tight3)', bl['tight3'] is True, bl)
bl_sort = ev("Router.state().stack[0].ui.sort")
bl_shown_before = ev("Router.state().stack[0].ui.shown")
check('BL-6 list is scrollable (folder has more rows than fit)', bl['scrollable'] is True, bl)
ev("document.getElementById('catList').scrollTop = 60; true"); wait_ms(300)
check('BL-6 list scrolls (scrollTop moves to ~60px)', abs((ev("document.getElementById('catList').scrollTop") or 0) - 60) <= 2, ev("document.getElementById('catList').scrollTop"))
# 真實滑鼠點擊：點可視區內、完整落在清單裡的第一列，應開啟對應的 Detail
row_pt = ev("""(function(){ const l=document.getElementById('catList'); const lr=l.getBoundingClientRect(); const vv=window.visualViewport; const vb=Math.min(vv?vv.offsetTop+vv.height:innerHeight, document.querySelector('.bottom-nav').getBoundingClientRect().top);
  const top=Math.max(lr.top, 0), bot=Math.min(lr.bottom, vb);
  let best=null;
  for (const x of l.querySelectorAll('.cat-row')) { const r=x.getBoundingClientRect(); const vis=Math.min(r.bottom,bot)-Math.max(r.top,top); if (vis>=22 && (!best || vis>best.vis)) best={row:x, r:r, vis:vis}; }
  if(!best) return null;
  const y=(Math.max(best.r.top,top)+Math.min(best.r.bottom,bot))/2, x=(best.r.left+best.r.right)/2;
  const hit=document.elementFromPoint(x,y);
  return {x: Math.round(x), y: Math.round(y), code: best.row.dataset.code, vis: Math.round(best.vis), hitInList: !!hit && l.contains(hit), hitRow: !!hit && best.row.contains(hit)}; })()""")
check('BL-7 a list row with >= 22px inside the visible list region exists, and elementFromPoint hits that row', isinstance(row_pt, dict) and row_pt['hitRow'] is True, row_pt)
if isinstance(row_pt, dict):
    cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': row_pt['x'], 'y': row_pt['y'], 'button': 'left', 'clickCount': 1})
    cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': row_pt['x'], 'y': row_pt['y'], 'button': 'left', 'clickCount': 1})
    wait_ms(320)
    top_code_now = ev("(function(){ const st=Router.state(); const t=st.stack[st.stack.length-1]; return t && t.t==='detail' ? t.code : null; })()")
    check('BL-7 real tap on a visible row opens its Detail', ev("!document.getElementById('gsPanel').hidden") is True and top_code_now == row_pt['code'], (top_code_now, row_pt))
    ev("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); true"); wait_ms(320)
    types_now = ev("Router.state().stack.map(l=>l.t).join(',')")
    check('BL-7 Esc closes that Detail; folder still open with its list scroll', types_now == 'folder' and abs((ev("document.getElementById('catList').scrollTop") or 0) - 60) <= 2, (types_now, ev("document.getElementById('catList').scrollTop")))
# 查看更多在清單底部：捲到底後可見、可點，點了確實多列出 10 檔
ev("(function(){ const l=document.getElementById('catList'); l.scrollTop = l.scrollHeight; return true; })()"); wait_ms(250)
inner_ok = ev("""(function(){ const b=document.querySelector('#catList .cat-more-in'); if(!b) return 'none'; const l=document.getElementById('catList').getBoundingClientRect(); const r=b.getBoundingClientRect(); const vv=window.visualViewport; const vb=Math.min(vv?vv.offsetTop+vv.height:innerHeight, document.querySelector('.bottom-nav').getBoundingClientRect().top); return (r.top>=l.top-0.5 && r.bottom<=l.bottom+0.5 && r.bottom<=vb) ? 'visible' : 'hidden:'+JSON.stringify([r.top,r.bottom,l.top,l.bottom,vb]); })()""")
check('BL-8 查看更多 is inside the list at its bottom, visible and above the nav', inner_ok == 'visible', inner_ok)
ev("document.querySelector('#catList .cat-more-in').click(); true"); wait_ms(150)
check('BL-8 查看更多 (inside list) lists 10 more rows', ev("Router.state().stack[0].ui.shown") == bl_shown_before + 10 and ev("document.querySelectorAll('#catList .cat-row').length") == bl_shown_before + 10, (ev("Router.state().stack[0].ui.shown"), bl_shown_before))
bl_shown_after = ev("Router.state().stack[0].ui.shown")
# 回到一般高度（直向 390×844）：版面恢復，清單不再是 cat-tight3，「查看更多」回到清單外、狀態保留
set_view(390, 844, 'portraitPrimary'); wait_ms(400)
check('BACK-TO-NORMAL layer removed (no cat-tight3 on page or main)', ev("document.getElementById('catMain').classList.contains('cat-tight3') || document.getElementById('page-cat').classList.contains('cat-tight3')") is False)
check('BACK-TO-NORMAL list height >= 110px and visible', ev("(function(){ const l=document.getElementById('catList'); return !l.hidden && l.getBoundingClientRect().height >= 110; })()") is True, ev("document.getElementById('catList').getBoundingClientRect().height"))
check('BACK-TO-NORMAL 查看更多 inside list (D4, portrait list); external hidden', ev("document.querySelectorAll('#catList .cat-more-in').length") == 1 and ev("getComputedStyle(document.getElementById('catMore')).display") == 'none')
check('BACK-TO-NORMAL folder state kept (sort, shown)', ev("Router.state().stack[0].ui.sort") == bl_sort and ev("Router.state().stack[0].ui.shown") == bl_shown_after, (ev("Router.state().stack[0].ui.sort"), ev("Router.state().stack[0].ui.shown")))
check('BACK-TO-NORMAL no horizontal overflow', ev("document.documentElement.scrollWidth <= innerWidth") is True)

# ── LR-8（PHASE3_PLAN §11.6 B、C）：鍵盤開、可視區下移（visualViewport.offsetTop > 0）──
# headless 目前產生不了 offsetTop > 0。已試過：setPageScaleFactor + 捲動手勢、pinch（touch 模擬）、
# Emulation.setDeviceMetricsOverride 的 positionY／viewport；visualViewport 都沒有改變，
# 且 index.html 的 user-scalable=no 本來就不允許縮放。所以真實 LR-8 只能 DEFER，需 iPhone Chrome 真機
# （iOS 鍵盤開啟時會實際平移可視區）。
# 下方 LR8_CHECK 是檢查邏輯，只能在 offsetTop > 0 時當成真實結果；目前另以 stub 自我檢查（SELF-TEST），
# 那只證明檢查邏輯的正反兩面正確，不是 LR-8 的結果。
LR8_CHECK = """(function(){
  const vv = window.visualViewport;
  const top = vv ? vv.offsetTop : 0;
  const bot = vv ? vv.offsetTop + vv.height : innerHeight;
  function part(el) {
    if (!el || el.hidden || getComputedStyle(el).display === 'none') return null;
    const r = el.getBoundingClientRect();
    const t = Math.max(r.top, top), b = Math.min(r.bottom, bot);
    return { h: Math.max(0, b - t), cx: (Math.max(r.left, 0) + Math.min(r.right, innerWidth)) / 2, cy: (t + b) / 2 };
  }
  // true＝可視區內中心點命中該元素；false＝被別的元素蓋住；null＝不在可視區內
  function hit(el, p) {
    if (!p || p.h <= 0) return null;
    const e = document.elementFromPoint(p.cx, p.cy);
    return !!e && (el === e || el.contains(e));
  }
  const s = document.getElementById('gsearch');
  const ps = part(s);
  const occluded = [];
  ['.app-hdr', '.bottom-nav'].forEach(sel => {
    const el = document.querySelector(sel);
    const p = part(el);
    if (p && p.h >= 12 && hit(el, p) === false) occluded.push(sel);
  });
  return {
    offsetTop: top, visBottom: bot,
    searchVisible: ps ? ps.h : 0,
    searchNeed: Math.min(s.getBoundingClientRect().height, 12),
    searchHit: hit(s, ps) === true,
    occluded: occluded,
    hScroll: document.documentElement.scrollWidth > innerWidth
  };
})()"""
set_view(844, 170, 'landscapePrimary'); wait_ms(200)
ev("(function(){ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); return true; })()"); wait_ms(300)
check('LR-8 setup: keyboard state (gs-ckm on) at 844x170', ev("document.body.classList.contains('gs-ckm')") is True)
lr8_scroll_before = ev("document.getElementById('catList').scrollTop")
cdp('Emulation.setPageScaleFactor', {'pageScaleFactor': 2}); wait_ms(250)
cdp('Input.synthesizeScrollGesture', {'x': 200, 'y': 120, 'yDistance': -120, 'gestureSourceType': 'touch', 'speed': 800}); wait_ms(400)
off = ev("visualViewport ? visualViewport.offsetTop : 0")
if isinstance(off, (int, float)) and off > 0:
    r = ev(LR8_CHECK)
    check('LR-8 B: search has ≥12px inside visible region [offsetTop, offsetTop+height]', r['searchVisible'] >= r['searchNeed'], r)
    check('LR-8 B: elementFromPoint at visible search center hits the search input', r['searchHit'] is True, r)
    check('LR-8 B: visible header/nav are not occluded', r['occluded'] == [], r['occluded'])
    check('LR-8 B: no horizontal scroll', r['hScroll'] is False)
    cdp('Emulation.setPageScaleFactor', {'pageScaleFactor': 1}); wait_ms(300)
    ev("window.scrollTo(0,0); true"); wait_ms(200)
    check('LR-8 C: visible region returns to offsetTop 0 after recovery', ev("visualViewport.offsetTop") == 0)
    ev("(function(){ const i=document.getElementById('gsearch'); i.blur(); i.dispatchEvent(new Event('blur')); return true; })()"); wait_ms(400)
    check('LR-8 C: gs-ckm removed after keyboard closes', ev("document.body.classList.contains('gs-ckm')") is False)
    check('LR-8 C: strip, list and bottom nav visible again', ev("getComputedStyle(document.getElementById('catStrip')).display") != 'none' and ev("!document.getElementById('catList').hidden && document.getElementById('catList').getBoundingClientRect().height > 0") is True and ev("getComputedStyle(document.querySelector('.bottom-nav')).display") != 'none')
    check('LR-8 C: list scroll position kept across the keyboard cycle', abs((ev("document.getElementById('catList').scrollTop") or 0) - (lr8_scroll_before or 0)) <= 2, (lr8_scroll_before, ev("document.getElementById('catList').scrollTop")))
else:
    cdp('Emulation.setPageScaleFactor', {'pageScaleFactor': 1}); wait_ms(200)
    defer('LR-8 B/C keyboard offsetTop > 0 (headless cannot produce visualViewport offset; needs iPhone Chrome real device)', 'offsetTop=%s after pageScale 2 + scroll gesture; visualViewport unchanged' % off)

# LR-8 SELF-TEST（stub，不是 LR-8 結果）：用 stub 的 visualViewport 驗證檢查邏輯的正反兩面
def lr8_stub(off, h):
    ev("(function(){ window.__vvSaved = Object.getOwnPropertyDescriptor(window, 'visualViewport'); Object.defineProperty(window, 'visualViewport', {configurable: true, get: function(){ return {offsetTop: %d, height: %d, width: innerWidth, scale: 1, offsetLeft: 0, pageTop: 0, pageLeft: 0}; }}); return true; })()" % (off, h))
    r = ev(LR8_CHECK)
    ev("(function(){ if (window.__vvSaved) Object.defineProperty(window, 'visualViewport', window.__vvSaved); else delete window.visualViewport; return true; })()")
    return r
ss = ev("(function(){ const s=document.getElementById('gsearch').getBoundingClientRect(); return {top: s.top, bottom: s.bottom}; })()")
pos = lr8_stub(max(0, int(ss['top'])), 20)
check('LR-8 SELF-TEST (stub): region starting at the search top → checker reports search visible and hit', pos['offsetTop'] == max(0, int(ss['top'])) and pos['searchVisible'] >= pos['searchNeed'] and pos['searchHit'] is True, pos)
neg = lr8_stub(int(ss['bottom']) + 60, 20)
check('LR-8 SELF-TEST (stub): region below the search → checker reports search NOT visible', neg['offsetTop'] == int(ss['bottom']) + 60 and neg['searchVisible'] < neg['searchNeed'], neg)
ev("(function(){ const i=document.getElementById('gsearch'); i.blur(); i.dispatchEvent(new Event('blur')); return true; })()"); wait_ms(300)

set_view(390, 844, 'portraitPrimary')
# ── PT（PHASE3 Gate：直向 inside／doorway）：主 TAB ▾／▴、其他分類收合、清單取得空間、導覽列不遮擋、footer 可正常捲到 ──
PT_JS = """(function(){
  const q = id => document.getElementById(id);
  const r = el => el ? el.getBoundingClientRect() : null;
  const list = q('catList'), nav = document.querySelector('.bottom-nav'), inner = document.querySelector('#catList .cat-more-in');
  const lr = r(list), nr = r(nav);
  return { ctl: q('catMain').classList.contains('cat-ctl'), inside: q('catMain').classList.contains('cat-inside'),
           expText: q('catExpand').textContent, expAria: q('catExpand').getAttribute('aria-expanded'),
           expDisp: getComputedStyle(q('catExpand')).display, stripDisp: getComputedStyle(q('catStrip')).display,
           listTop: Math.round(lr.top), listH: Math.round(lr.height), listBottom: Math.round(lr.bottom), navTop: Math.round(nr.top),
           listScroll: list.scrollTop, footDisp: getComputedStyle(q('catFoot')).display,
           extMoreDisp: getComputedStyle(q('catMore')).display, innerCount: document.querySelectorAll('#catList .cat-more-in').length,
           scrollY: Math.round(scrollY), docH: document.documentElement.scrollHeight, title: q('catName').textContent,
           portrait: matchMedia('(orientation: portrait)').matches };
})()"""
PT_CLICK = lambda sel: ev("(function(){ const el=document.querySelector(%s); if(el) el.click(); return !!el; })()" % json.dumps(sel))
PT_EMPTY = {'ctl': False, 'inside': False, 'expText': None, 'expAria': None, 'expDisp': None, 'stripDisp': None, 'listTop': 0, 'listH': 0, 'listBottom': 0, 'navTop': 0, 'listScroll': 0, 'footDisp': None, 'extMoreDisp': None, 'innerCount': 0, 'scrollY': 0, 'docH': 0, 'title': None, 'portrait': False}
def pt():
    r = ev(PT_JS)   # 缺少元素（例如舊版）時 JS 會出錯：回傳空值，讓各檢查判為 FAIL，而不是中斷測試
    return r if isinstance(r, dict) else PT_EMPTY
set_view(390, 844, 'portraitPrimary'); wait_ms(300)
ev("Router.toBase({base:'home'}); true"); wait_ms(200)
ev("switchPage('cat'); true"); wait_ms(200)
ev("document.querySelector('.cat-band[data-k=\"mcap\"]').click(); true"); wait_ms(450)
p0 = pt()
check('PT-1 portrait open: 進入 inside（其他分類收合，▾ 可見）', p0['ctl'] and p0['inside'] and p0['stripDisp'] == 'none' and p0['expText'] == '切換分類 ▼' and p0['expAria'] == 'false' and p0['expDisp'] != 'none', p0)
check('PT-1 inside: 說明列與外部「查看更多」隱藏，清單內有「查看更多」（D4／D5）', p0['footDisp'] == 'none' and p0['extMoreDisp'] == 'none' and p0['innerCount'] == 1, p0)
check('PT-1 inside: 清單底部在導覽列上方（頁面未捲動）', p0['listBottom'] <= p0['navTop'] and p0['scrollY'] == 0, p0)
# 排序／已展開數／捲動在 inside ↔ doorway 切換前後保留（Router 資料夾層）
PT_click_sort = ev("(function(){ document.getElementById('catSortBtn').click(); return true; })()"); wait_ms(120)
ev("(function(){ const m=document.querySelector('#catList .cat-more-in'); if(m) m.click(); return true; })()"); wait_ms(150)
ev("document.getElementById('catList').scrollTop = 40; true"); wait_ms(300)
ui_before = ev("JSON.stringify(Router.state().stack[0].ui)")
ls_before = ev("document.getElementById('catList').scrollTop")
h_inside = pt()['listH']
PT_CLICK('#catExpand'); wait_ms(250)
p1 = pt()
check('PT-2 ▾ → doorway：其他分類顯示、▴、清單高度減少（約一列）', p1['inside'] is False and p1['stripDisp'] != 'none' and p1['expText'] == '切換分類 ▲' and p1['expAria'] == 'true' and p1['listH'] < h_inside, (p1['listH'], h_inside))
check('PT-2 inside→doorway：清單多出的空間為次要標籤列高度（±4px）', abs((h_inside - p1['listH']) - 48) <= 4, (h_inside, p1['listH']))
check('PT-2 doorway：排序、已展開數、捲動保留（Router 資料夾層不變）', ev("JSON.stringify(Router.state().stack[0].ui)") == ui_before, (ev("JSON.stringify(Router.state().stack[0].ui)"), ui_before))
check('PT-2 doorway：清單捲動位置不跳動', ev("document.getElementById('catList').scrollTop") == ls_before, (ev("document.getElementById('catList').scrollTop"), ls_before))
PT_CLICK('#catExpand'); wait_ms(250)
p2 = pt()
check('PT-3 ▴ → inside 再次（其他分類收合，清單高度回復）', p2['inside'] and p2['stripDisp'] == 'none' and p2['listH'] == h_inside, (p2['listH'], h_inside))
check('PT-3 inside again：捲動位置與 Router 狀態不變', ev("document.getElementById('catList').scrollTop") == ls_before and ev("JSON.stringify(Router.state().stack[0].ui)") == ui_before, (ev("document.getElementById('catList').scrollTop"), ls_before))
# 點主 TAB 標題區也能切換
ev("document.querySelector('#catMain .cat-title').click(); true"); wait_ms(200)
check('PT-4 點主 TAB 標題區：inside → doorway', pt()['inside'] is False)
ev("document.querySelector('#catMain .cat-title').click(); true"); wait_ms(200)
check('PT-4 點主 TAB 標題區：doorway → inside', pt()['inside'] is True)
# doorway 選另一分類 → 立即新的 inside
PT_CLICK('#catExpand'); wait_ms(250)
PT_CLICK('#catStrip button[data-k="div"]'); wait_ms(350)
p3 = pt()
check('PT-5 doorway 選「高股息」→ 新分類立即 inside（主 TAB 改名、其他分類收合）', p3['title'] == '高股息' and p3['inside'] and p3['stripDisp'] == 'none' and p3['expText'] == '切換分類 ▼', p3)
# 高股息清單：查看更多在清單底部、捲到底可見、可點、導覽列不遮擋
ev("document.getElementById('catList').scrollTop = 99999; true"); wait_ms(300)
ib = ev("(function(){ const b=document.querySelector('#catList .cat-more-in'); if(!b) return null; const r=b.getBoundingClientRect(); const l=document.getElementById('catList').getBoundingClientRect(); const n=document.querySelector('.bottom-nav').getBoundingClientRect(); return {top:r.top, bottom:r.bottom, lTop:l.top, lBottom:l.bottom, navTop:n.top}; })()")
check('PT-6 查看更多：捲到清單底部後可見、在清單內、在導覽列上方', isinstance(ib, dict) and ib['top'] >= ib['lTop'] - 0.5 and ib['bottom'] <= ib['lBottom'] + 0.5 and ib['bottom'] <= ib['navTop'], ib)
hit_more = ev("(function(){ const b=document.querySelector('#catList .cat-more-in'); const r=b.getBoundingClientRect(); const e=document.elementFromPoint(r.left+r.width/2, (r.top+r.bottom)/2); return !!e && (e===b || b.contains(e)); })()")
check('PT-6 查看更多：elementFromPoint 命中按鈕（未被導覽列或其他元素蓋住）', hit_more is True)
rows_before = ev("document.querySelectorAll('#catList .cat-row').length")
ev("document.querySelector('#catList .cat-more-in').click(); true"); wait_ms(200)
check('PT-6 查看更多：點擊後多列出 10 檔', ev("document.querySelectorAll('#catList .cat-row').length") == rows_before + 10, (rows_before, ev("document.querySelectorAll('#catList .cat-row').length")))
# 導覽列不遮擋：頁面捲動後，清單底部仍在導覽列上方（清單高度不隨捲動改變）
ev("window.scrollTo(0, 150); true"); wait_ms(300)
p4 = pt()
check('PT-7 頁面捲動 150px：清單底部仍在導覽列上方（不被遮住）', p4['listBottom'] <= p4['navTop'] + 0.5, p4)
ev("window.dispatchEvent(new Event('resize')); true"); wait_ms(250)
p4b = pt()
check('PT-7 頁面捲動後觸發 resize：清單高度不因捲動改變（以未捲動位置計算）', p4b['listH'] == p4['listH'] and p4b['listBottom'] <= p4b['navTop'] + 0.5, (p4['listH'], p4b['listH'], p4b['listBottom'], p4b['navTop']))
ev("window.scrollTo(0, 0); true"); wait_ms(300)
p5 = pt()
check('PT-7 頁面回到頂端：清單高度與位置與 inside 一致（未因捲動改變）', p5['listH'] == pt()['listH'] and p5['listBottom'] <= p5['navTop'], p5)
# footer 仍可透過正常頁面捲動看到（D6 未採用，不鎖定）
ev("window.scrollTo(0, 99999); true"); wait_ms(300)
foot = ev("(function(){ const f=document.querySelector('.site-footer').getBoundingClientRect(); const n=document.querySelector('.bottom-nav').getBoundingClientRect(); return {top:f.top, bottom:f.bottom, navTop:n.top, scrollY:scrollY, docH:document.documentElement.scrollHeight, innerH:innerHeight}; })()")
check('PT-8 footer：正常捲動可到達（scrollY > 0，footer 完整在導覽列上方）', foot['scrollY'] > 0 and foot['top'] >= 0 and foot['bottom'] <= foot['navTop'] + 1, foot)
ev("window.scrollTo(0, 0); true"); wait_ms(250)
# flow（持股異動）：不啟用 inside；次要標籤列顯示。回到清單：重新進入 inside
PT_CLICK('#catExpand'); wait_ms(250)
PT_CLICK('#catStrip button[data-k="active"]'); wait_ms(350)
ev("(function(){ document.querySelector('#catSeg button[data-v=\"flow\"]').click(); return true; })()"); wait_ms(300)
pf = pt()
check('PT-9 持股異動檢視：不啟用 inside，次要標籤列與 ▾ 不影響（展開控制隱藏）', pf['ctl'] is False and pf['expDisp'] == 'none' and pf['stripDisp'] != 'none', pf)
ev("(function(){ document.querySelector('#catSeg button[data-v=\"list\"]').click(); return true; })()"); wait_ms(300)
check('PT-9 回到清單：重新進入 inside（其他分類收合）', pt()['inside'] is True)
# Detail 開關不改變模式（doorway 保留）
PT_CLICK('#catExpand'); wait_ms(250)
ev("(function(){ document.querySelector('#catList .cat-row').click(); return true; })()"); wait_ms(300)
check('PT-10 doorway 中開 Detail', ev("!document.getElementById('gsPanel').hidden") is True)
ev("document.querySelector('#gsPanel .gs-panel-hd button').click(); true"); wait_ms(320)
check('PT-10 關閉 Detail 後仍為 doorway（模式不變）', pt()['inside'] is False and pt()['expText'] == '切換分類 ▲')
# 收合回到總覽：✕ → overview，展開控制與清單模式移除
ev("document.getElementById('catClose').click(); true"); wait_ms(320)
po = pt()
check('PT-11 ✕ 回到總覽：不再有 cat-ctl／cat-inside', po['ctl'] is False and po['inside'] is False)
# 橫向：路徑不變（無展開控制、次要標籤列顯示、清單可見）
set_view(844, 390, 'landscapePrimary'); wait_ms(300)
ev("document.querySelector('.cat-band[data-k=\"mcap\"]').click(); true"); wait_ms(450)
pl = pt()
check('PT-12 橫向：無 inside／▾，次要標籤列顯示（不 regression）', pl['ctl'] is False and pl['inside'] is False and pl['expDisp'] == 'none' and pl['stripDisp'] != 'none', pl)
set_view(390, 844, 'portraitPrimary'); wait_ms(300)
check('PT-12 回到直向：inside 重新啟用', pt()['inside'] is True and pt()['ctl'] is True)
ev("document.getElementById('catClose').click(); true"); wait_ms(320)

# ── AB（真機 D4 消失 bug）：visualViewport／工具列伸縮改變清單高度時的底部錨定 ──
# AB-1 原本在底部 → 縮短 → 仍在底部、查看更多完整可見；AB-2 恢復後仍在底部；
# AB-3 原本在中段 → 不跳到底部；AB-4 D4 查看更多仍可點、+10 正常。
AB_JS = """(function(){
  const l = document.getElementById('catList'), b = document.querySelector('#catList .cat-more-in');
  const lr = l.getBoundingClientRect();
  const br = b ? b.getBoundingClientRect() : null;
  return { h: Math.round(lr.height), scrollTop: Math.round(l.scrollTop), max: l.scrollHeight - l.clientHeight,
           inner: !!b, innerVisible: !!br && br.top >= lr.top - 0.5 && br.bottom <= lr.bottom + 0.5,
           rows: document.querySelectorAll('#catList .cat-row').length, listVis: getComputedStyle(l).visibility,
           remainText: b ? b.textContent : null };
})()"""
def ab(): return ev(AB_JS)
# B6（警示條 85 → 50px）後，390×844 下高股息 10 檔＋查看更多剛好完整放得下（max=0），不符本段「清單需要捲動」的前提；改用 809／765（＝B6 前 844／800 的同一清單幾何）。max=0 後再縮短時查看更多被裁約 16px 為既存邊界行為（B6 前 879→835 同樣重現），記於 AI_HANDOFF Known Observation，本輪不修 Category。
# ── A 段：PO 真機情境（高股息、10 檔、剩餘 12 檔、inside，直向 390×844）──
set_view(390, 809, 'portraitPrimary'); wait_ms(300)
ev("Router.toBase({base:'home'}); true"); wait_ms(200)
ev("switchPage('cat'); true"); wait_ms(200)
ev("document.querySelector('.cat-band[data-k=\"div\"]').click(); true"); wait_ms(450)
ab0 = ab()
check('AB precondition A: 高股息 inside, 10 rows shown, 「查看更多（還有 12 檔）」在清單內', ab0['inner'] and ab0['rows'] == 10 and ab0['remainText'] == '查看更多（還有 12 檔）', ab0)
ev("document.getElementById('catList').scrollTop = 99999; true"); wait_ms(300)
bot = ab()
check('AB-1a precondition: list scrolled to bottom, 查看更多 visible', bot['scrollTop'] == bot['max'] and bot['innerVisible'], bot)
set_view(390, 765, 'portraitPrimary'); wait_ms(600)
s1 = ab()
check('AB-1 原本在底部 → viewport 縮短：清單高度確實改變（fit 生效）', s1['h'] < bot['h'], (s1['h'], bot['h']))
check('AB-1 原本在底部 → viewport 縮短：仍保持在底部（scrollTop = 新的最大值）', s1['scrollTop'] == s1['max'], s1)
check('AB-1 原本在底部 → viewport 縮短：「查看更多」完整在清單可視範圍內', s1['innerVisible'], s1)
hit_s1 = ev("(function(){ const b=document.querySelector('#catList .cat-more-in'); const r=b.getBoundingClientRect(); const e=document.elementFromPoint(r.left+r.width/2,(r.top+r.bottom)/2); return !!e && (e===b || b.contains(e)); })()")
check('AB-1 viewport 縮短：查看更多 elementFromPoint 命中（未被導覽列蓋住）', hit_s1 is True)
set_view(390, 809, 'portraitPrimary'); wait_ms(600)
s2 = ab()
check('AB-2 viewport 恢復：清單高度回到原本', s2['h'] == bot['h'], (s2['h'], bot['h']))
check('AB-2 viewport 恢復：仍保持在底部，查看更多可見', s2['scrollTop'] == s2['max'] and s2['innerVisible'], s2)
# ── B 段：主動式（32 檔）：中段閱讀位置與 D4 +10 ──
ev("document.getElementById('catExpand').click(); true"); wait_ms(250)
ev("document.querySelector('#catStrip button[data-k=\"active\"]').click(); true"); wait_ms(400)
ev("(function(){ if (document.getElementById('catMain').classList.contains('cat-inside')) document.getElementById('catExpand').click(); return true; })()"); wait_ms(250)
ev("(function(){ const m=document.querySelector('#catList .cat-more-in'); if(m) m.click(); return true; })()"); wait_ms(200)   # 20 檔
ev("document.getElementById('catList').scrollTop = 120; true"); wait_ms(300)
mid = ab()
check('AB-3 precondition: 主動式 20 檔，清單在中段（≈120px，非底部）', mid['rows'] == 20 and abs(mid['scrollTop'] - 120) <= 2 and mid['max'] - mid['scrollTop'] > 40, mid)
set_view(390, 765, 'portraitPrimary'); wait_ms(600)
m1 = ab()
check('AB-3 中段 → viewport 縮短：閱讀位置不變（未跳到底部）', abs(m1['scrollTop'] - 120) <= 2 and m1['scrollTop'] != m1['max'], m1)
set_view(390, 809, 'portraitPrimary'); wait_ms(600)
m2 = ab()
check('AB-3 中段 → viewport 恢復：閱讀位置不變（未跳到底部）', abs(m2['scrollTop'] - 120) <= 2 and m2['scrollTop'] != m2['max'], m2)
ev("document.getElementById('catList').scrollTop = 99999; true"); wait_ms(300)
rows0 = ab()['rows']
ev("document.querySelector('#catList .cat-more-in').click(); true"); wait_ms(250)
check('AB-4 查看更多（D4）：點擊後 +10 檔（20 → 30）', ab()['rows'] == rows0 + 10, (rows0, ab()['rows']))
ev("document.getElementById('catList').scrollTop = 99999; true"); wait_ms(300)
d4 = ab()
check('AB-4 查看更多（D4）：點擊後再捲到底仍可見、可再點', d4['inner'] and d4['innerVisible'], d4)
ev("document.querySelector('#catList .cat-more-in').click(); true"); wait_ms(250)
check('AB-4 查看更多（D4）：再次點擊 +10（30 → 32，主動式總數）', ab()['rows'] == 32, ab()['rows'])

# ── RL（真機測試 A FAIL 已確認）：Detail 關閉／Back／Forward／資料輪詢重建清單時，底部與中段位置保持正確；ui.scrollTop 不寫入錯誤的 0 ──
RL_JS = """(function(){
  const l = document.getElementById('catList'), b = document.querySelector('#catList .cat-more-in');
  const lr = l.getBoundingClientRect(), br = b ? b.getBoundingClientRect() : null;
  const st = Router.state().stack[0];
  return { st: Math.round(l.scrollTop), max: l.scrollHeight - l.clientHeight, inner: !!b,
           vis: !!br && br.top >= lr.top - 0.5 && br.bottom <= lr.bottom + 0.5,
           ui: st && st.ui ? Math.round(st.ui.scrollTop) : null, rows: document.querySelectorAll('#catList .cat-row').length,
           detailOpen: !document.getElementById('gsPanel').hidden };
})()"""
def rl(): return ev(RL_JS)
def rl_open_detail(code):
    ev("(function(){ const r=document.querySelector('#catList .cat-row[data-code=\"%s\"]'); if(r) r.click(); return !!r; })()" % code); wait_ms(320)
def rl_close_x():
    ev("document.querySelector('#gsPanel .gs-panel-hd button').click(); true"); wait_ms(350)
set_view(390, 809, 'portraitPrimary'); wait_ms(300)
ev("Router.toBase({base:'home'}); true"); wait_ms(200)
ev("switchPage('cat'); true"); wait_ms(200)
ev("document.querySelector('.cat-band[data-k=\"div\"]').click(); true"); wait_ms(450)
# RL-1：底部 → 開 Detail（00907）→ × 關閉：清單仍在底部、查看更多可見、ui 與畫面一致（不得被寫成 0）
ev("document.getElementById('catList').scrollTop = 99999; true"); wait_ms(300)
r1a = rl()
check('RL-1 precondition: 高股息 at bottom, 查看更多 visible, 10 rows', r1a['st'] == r1a['max'] and r1a['vis'] and r1a['rows'] == 10, r1a)
rl_open_detail('00907')
check('RL-1 Detail 00907 opened from the list', rl()['detailOpen'] is True)
rl_close_x()
r1 = rl()
check('RL-1 Detail × 關閉後：清單仍在底部（st = 合法最大值）', r1['st'] == r1['max'] and r1['max'] > 0, r1)
check('RL-1 Detail × 關閉後：「查看更多」完整可見（真機測試 A）', r1['inner'] and r1['vis'], r1)
ev("true"); wait_ms(400)   # 讓 150ms 防抖也跑完，確認之後不會被寫成錯誤的值
r1b = rl()
check('RL-1 防抖結束後 ui.scrollTop 仍與畫面一致（沒有被寫回 0）', r1b['ui'] == r1b['st'] and r1b['vis'], r1b)
# RL-2：資料輪詢（Category.refresh，與 30 秒輪詢走同一條 renderList 路徑）：底部與中段
ev("document.getElementById('catList').scrollTop = 99999; true"); wait_ms(300)
Category_refresh = ev("(function(){ Category.refresh(); return true; })()"); wait_ms(300)
r2 = rl()
check('RL-2 資料輪詢重建（底部）：仍在底部，查看更多可見', r2['st'] == r2['max'] and r2['vis'] and r2['ui'] == r2['st'], r2)
# 把清單放到中段（先 +10 讓捲動範圍足夠）
ev("(function(){ const m=document.querySelector('#catList .cat-more-in'); if(m) m.click(); return true; })()"); wait_ms(200)   # 20 檔
ev("document.getElementById('catList').scrollTop = 120; true"); wait_ms(300)
mid0 = rl()
check('RL-3 precondition: 中段（120px，非底部）', abs(mid0['st'] - 120) <= 2 and mid0['max'] - mid0['st'] > 40, mid0)
ev("(function(){ Category.refresh(); return true; })()"); wait_ms(300)
r3 = rl()
check('RL-3 資料輪詢重建（中段）：閱讀位置不變，未被送到底部', abs(r3['st'] - mid0['st']) <= 2 and r3['st'] != r3['max'], (mid0['st'], r3['st'], r3['max']))
check('RL-3 資料輪詢重建（中段）：查看更多仍在清單內（D4）', r3['inner'], r3)
rl_open_detail('00907')
rl_close_x()
r3b = rl()
check('RL-3 Detail 關閉（中段）：閱讀位置不變，未被送到底部', abs(r3b['st'] - mid0['st']) <= 2 and r3b['st'] != r3b['max'], (mid0['st'], r3b['st'], r3b['max']))
# RL-4：底部 → Detail → Back（關閉）→ Forward（再開）→ Back：每一步都在底部、查看更多可見
ev("document.getElementById('catList').scrollTop = 99999; true"); wait_ms(300)
bot4 = rl()
rl_open_detail('00907')
ev("history.back(); true"); wait_ms(350)
b1 = rl()
check('RL-4 Back（Detail 關閉）：仍在底部，查看更多可見', b1['st'] == b1['max'] and b1['vis'] and not b1['detailOpen'], (bot4, b1))
ev("history.forward(); true"); wait_ms(350)
f1 = rl()
check('RL-4 Forward（Detail 再開）：Detail 開啟，清單仍在底部', f1['detailOpen'] and f1['st'] == f1['max'], f1)
ev("history.back(); true"); wait_ms(350)
b2 = rl()
check('RL-4 再次 Back：仍在底部，查看更多可見', b2['st'] == b2['max'] and b2['vis'] and not b2['detailOpen'], b2)

# ── UX（UX-1 金色提醒與分類內容間距；UX-2「切換分類 ▼／▲」）：直向 inside／doorway ──
UX_JS = """(function(){
  const d = document.querySelector('.disclaimer').getBoundingClientRect();
  const name = document.getElementById('catName'), rr = document.createRange(); rr.selectNodeContents(name);
  const nt = rr.getBoundingClientRect(); const btn = document.getElementById('catExpand'), br = btn.getBoundingClientRect();
  const t = document.querySelector('#catMain .cat-title');
  return { gap: Math.round(nt.top - d.bottom), headH: Math.round(document.querySelector('#catMain .cat-head').getBoundingClientRect().height),
           btnText: btn.textContent, btnW: Math.round(br.width), btnH: Math.round(br.height), btnInSubrow: btn.parentElement.classList.contains('cat-subrow'),
           btnInHead: !!btn.closest('.cat-head'), ariaExpanded: btn.getAttribute('aria-expanded'), ariaLabel: btn.getAttribute('aria-label'),
           titleScroll: t.scrollWidth, titleClient: t.clientWidth, titleW: Math.round(t.getBoundingClientRect().width),
           nameText: name.textContent, countText: document.getElementById('catCount').textContent,
           inside: document.getElementById('catMain').classList.contains('cat-inside'), btnDisp: getComputedStyle(btn).display };
})()"""
def ux(): return ev(UX_JS)
set_view(390, 844, 'portraitPrimary'); wait_ms(300)
ev("Router.toBase({base:'home'}); true"); wait_ms(200)
ev("switchPage('cat'); true"); wait_ms(200)
ev("document.querySelector('.cat-band[data-k=\"tech\"]').click(); true"); wait_ms(450)
u0 = ux()
check('UX-1 金色提醒與分類內容之間保留正常間距（10–20px，不貼齊、不過大）', 10 <= u0['gap'] <= 20, u0)
check('UX-1 標題列高度回到正常（≤ 40px，不再因 44px 按鈕撐高）', u0['headH'] <= 40, u0)
check('UX-2 按鈕文字：inside 為「切換分類 ▼」', u0['btnText'] == '切換分類 ▼' and u0['inside'], u0)
check('UX-2 按鈕可點擊區 ≥ 44×44', u0['btnW'] >= 44 and u0['btnH'] >= 44, u0)
check('UX-2 按鈕位於說明列（不在標題列）', u0['btnInSubrow'] and not u0['btnInHead'], u0)
check('UX-2 無障礙：aria-expanded=false、aria-label 含「切換分類」', u0['ariaExpanded'] == 'false' and '切換分類' in (u0['ariaLabel'] or ''), u0)
check('長分類名稱保留完整空間：科技／半導體 不被截斷（標題無溢出）', u0['nameText'] == '科技／半導體' and u0['titleScroll'] <= u0['titleClient'] + 1 and u0['titleW'] >= 200, u0)
# 點按鈕一次：只切換一次（inside → doorway），再點一次回到 inside
ev("document.getElementById('catExpand').click(); true"); wait_ms(250)
u1 = ux()
check('UX-2 點「切換分類 ▼」一次：進入 doorway，按鈕變「▲」，aria-expanded=true', u1['btnText'] == '切換分類 ▲' and u1['ariaExpanded'] == 'true' and not u1['inside'], u1)
ev("document.getElementById('catExpand').click(); true"); wait_ms(250)
u2 = ux()
check('UX-2 再點一次：回到 inside（只切換一次，沒有重複觸發）', u2['btnText'] == '切換分類 ▼' and u2['inside'], u2)
# 主分類標題仍可切換（Gate 核准），與按鈕不衝突：各點一次都只切換一次
ev("document.querySelector('#catMain .cat-title').click(); true"); wait_ms(250)
check('UX-2 點主分類標題：inside → doorway（只切換一次）', ux()['btnText'] == '切換分類 ▲' and not ux()['inside'])
ev("document.getElementById('catExpand').click(); true"); wait_ms(250)
check('UX-2 標題切換後再點按鈕：doorway → inside（不衝突，只切換一次）', ux()['inside'] is True and ux()['btnText'] == '切換分類 ▼')
# 橫向：按鈕不顯示；版面與 PASS 路徑一致
set_view(844, 390, 'landscapePrimary'); wait_ms(300)
ul = ux()
check('UX 橫向：切換分類按鈕不顯示（landscape 路徑不變）', ul['btnDisp'] == 'none', ul)
set_view(390, 844, 'portraitPrimary'); wait_ms(300)
check('UX 回到直向：按鈕重新顯示（inside）', ux()['btnDisp'] != 'none' and ux()['inside'] is True)
ev("document.getElementById('catClose').click(); true"); wait_ms(320)

# ── FO（分類說明移入文件夾、藏字修正）：總覽 8 份文件夾同高、說明完整不被遮、提醒在整疊下方；inside 不重複說明 ──
FO_JS = """(function(){
  const st = document.getElementById('catStage').getBoundingClientRect();
  const bands = [...document.querySelectorAll('.cat-band')], issues = [];
  bands.forEach(b => {
    const s = b.querySelector('.cb-sub'), n = b.querySelector('.cb-name'), br = b.getBoundingClientRect();
    if (!s || !s.textContent.trim()) { issues.push(b.dataset.k + ':noSub'); return; }
    if (s.scrollHeight > s.clientHeight + 1 || s.scrollWidth > s.clientWidth + 1) issues.push(b.dataset.k + ':overflow');
    if (s.getBoundingClientRect().bottom > br.bottom + 0.5) issues.push(b.dataset.k + ':subOutside');
    if (n.scrollWidth > n.clientWidth + 1) issues.push(b.dataset.k + ':nameTrunc');
    [s, n].forEach(el => { const rg = document.createRange(); rg.selectNodeContents(el);
      [...rg.getClientRects()].forEach(r => [0.1, 0.5, 0.9].forEach(fx => {
        const e = document.elementFromPoint(r.left + r.width * fx, r.top + r.height / 2);
        if (!e || !b.contains(e)) issues.push(b.dataset.k + ':covered'); })); });
  });
  const note = document.getElementById('catNote'), nr = note.getBoundingClientRect(), rg = document.createRange(); rg.selectNodeContents(note);
  [...rg.getClientRects()].forEach(r => { const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); if (e !== note) issues.push('noteCovered'); });
  const L = [...document.querySelectorAll('#catStackL .cat-band')].map(b => b.getBoundingClientRect());
  const overlap = L.slice(1).map((r, i) => Math.round(L[i].bottom - r.top));
  return { heights: [...new Set(bands.map(b => Math.round(b.getBoundingClientRect().height)))], overlap: overlap,
           noteBelow: nr.top >= Math.max(...bands.map(b => b.getBoundingClientRect().bottom)) - 0.5,
           docOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, issues: issues };
})()"""
ev("Router.toBase({base:'home'}); true"); wait_ms(200)
ev("switchPage('cat'); true"); wait_ms(300)
for fw in (320, 360, 375, 390, 414, 430):
    set_view(fw, 844, 'portraitPrimary'); wait_ms(300)
    fd = ev(FO_JS)
    check('FO-%d 8 份文件夾同高' % fw, len(fd['heights']) == 1, fd)
    check('FO-%d 疊層只壓底部留白（每份重疊 1–10px，仍有堆疊感）' % fw, all(1 <= o <= 10 for o in fd['overlap']), fd)
    check('FO-%d 分類名稱與說明完整：無 overflow、無截斷、未被下一份遮住' % fw, not fd['issues'], fd)
    check('FO-%d 提醒文字在整疊下方、未被文件夾遮住（無藏字）；無水平溢出' % fw, fd['noteBelow'] and not fd['docOverflow'], fd)
set_view(390, 844, 'portraitPrimary'); wait_ms(300)
ev("document.querySelector('.cat-band[data-k=\"theme\"]').click(); true"); wait_ms(450)
fi = ev("(function(){ const s=document.getElementById('catSub'), b=document.getElementById('catExpand'), r=document.querySelector('#catMain .cat-subrow').getBoundingClientRect(), br=b.getBoundingClientRect();"
        " return { sub: s.textContent, inside: document.getElementById('catMain').classList.contains('cat-inside'), rowH: Math.round(r.height), btnRight: Math.round(r.right - br.right), btnH: Math.round(br.height) }; })()")
check('FO inside：不重複顯示分類說明；切換分類按鈕仍在說明列右側、44px', fi['inside'] and fi['sub'] == '' and fi['btnH'] >= 44 and fi['btnRight'] <= 1, fi)
set_view(844, 390, 'landscapePrimary'); wait_ms(300)
fl = ev("(function(){ const s=document.getElementById('catSub'); return { sub: s.textContent, h: Math.round(s.getBoundingClientRect().height) }; })()")
check('FO 橫向 open：說明列空白時零高度', fl['sub'] == '' and fl['h'] == 0, fl)
set_view(390, 844, 'portraitPrimary'); wait_ms(300)
ev("document.getElementById('catClose').click(); true"); wait_ms(320)

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if r[1] is False]
defers = [r for r in results if r[1] is None]
print('\nTOTAL %d  PASS %d  FAIL %d  DEFER %d' % (len(results), len(results) - len(fails) - len(defers), len(fails), len(defers)))
for r in defers: print('  DEFER: ' + r[0] + ' -- ' + str(r[2]))
ws.close()
