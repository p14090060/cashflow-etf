import sys, json, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

def set_view(w, h, orient):
    cdp('Emulation.setDeviceMetricsOverride', {'width': w, 'height': h, 'deviceScaleFactor': 1, 'mobile': True,
        'screenOrientation': {'type': orient, 'angle': 90 if orient.startswith('landscape') else 0}})
    wait_ms(500)

def ckm(): return ev("document.body.classList.contains('gs-ckm')")
def disp(sel): return ev("getComputedStyle(document.querySelector('%s')).display" % sel)

# 橫向、鍵盤未開：不進入精簡模式
set_view(844, 390, 'landscapePrimary')
ev("(()=>{ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); return true; })()"); wait_ms(400)
check('C1 landscape no keyboard: not compact', ckm() is False)
check('C1 topbar visible', disp('.topbar') != 'none')

# 鍵盤開（視窗高度縮小）：進入精簡模式
set_view(844, 170, 'landscapePrimary')
check('C2 landscape + keyboard: compact on', ckm() is True, ev("window.innerHeight"))
check('C2 topbar hidden', disp('.topbar') == 'none')
check('C2 bottom nav hidden', disp('.bottom-nav') == 'none')
check('C2 header not sticky (scrolls, search reachable)', ev("getComputedStyle(document.querySelector('.app-hdr')).position") == 'static')

# 搜尋 0050：輸入框寬、結果在鍵盤上方可見
ev("(()=>{ const i=document.getElementById('gsearch'); i.value='0050'; i.dispatchEvent(new Event('input')); return true; })()"); wait_ms(300)
iw = ev("document.getElementById('gsearch').getBoundingClientRect().width")
check('C3 search input keeps wide width', isinstance(iw, (int, float)) and iw >= 300, iw)
row = ev("(()=>{ const r=document.querySelector('#gsearchList .gs-row'); if(!r) return null; const b=r.getBoundingClientRect(); return {top:b.top, bottom:b.bottom}; })()")
vh = ev("window.innerHeight")
check('C3 first result row visible above keyboard', isinstance(row, dict) and row['bottom'] <= vh and row['top'] >= 0, json.dumps(row) + ' vh=' + str(vh))
check('C3 dropdown has usable height', ev("parseFloat(document.getElementById('gsearchList').style.maxHeight) >= 40") is True, ev("document.getElementById('gsearchList').style.maxHeight"))

# 鍵盤收起：恢復原本橫向版面
set_view(844, 390, 'landscapePrimary')
check('C4 keyboard closed: compact off', ckm() is False)
check('C4 topbar restored', disp('.topbar') != 'none')
check('C4 bottom nav restored', disp('.bottom-nav') != 'none')

# 直向：完全不進入精簡模式（鍵盤開著也一樣）
set_view(390, 844, 'portraitPrimary')
ev("(()=>{ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); return true; })()"); wait_ms(400)
check('C5 portrait no keyboard: not compact', ckm() is False)
set_view(390, 480, 'portraitPrimary')
check('C5 portrait + keyboard: still not compact', ckm() is False)
check('C5 portrait bottom nav kept', disp('.bottom-nav') != 'none')
set_view(390, 844, 'portraitPrimary')

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
