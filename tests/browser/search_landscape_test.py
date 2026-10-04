import sys, json, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0
MODE = sys.argv[1] if len(sys.argv) > 1 else 'landscape'
if MODE == 'portrait':
    cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True,
        'screenOrientation': {'type': 'portraitPrimary', 'angle': 0}})
else:
    cdp('Emulation.setDeviceMetricsOverride', {'width': 844, 'height': 390, 'deviceScaleFactor': 1, 'mobile': True,
        'screenOrientation': {'type': 'landscapePrimary', 'angle': 90}})
load_page()
print('mode', MODE, 'screen.orientation', ev("screen.orientation && screen.orientation.type"))

# 矮視窗（橫向）：搜尋框取得焦點時進入 gs-kb 狀態，離開後回復
ev("(()=>{ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); return true; })()"); wait_ms(600)
land = ev("_gsIsLandscape()")
check('L1 gs-kb matches device orientation (landscape=%s)' % land, ev("document.body.classList.contains('gs-kb')") == land, ev("window.innerHeight"))
check('L2 header becomes non-sticky when landscape', ev("getComputedStyle(document.querySelector('.app-hdr')).position") == ('static' if land else 'sticky'))
check('L3 bottom nav hidden when landscape', ev("getComputedStyle(document.querySelector('.bottom-nav')).display") == ('none' if land else 'flex'))
ev("(()=>{ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); i.value='0050'; i.dispatchEvent(new Event('input')); return true; })()"); wait_ms(300)
check('L6 hint row only when landscape', ev("!!document.querySelector('#gsearchList .gs-kb-hint')") == land)
check('L6b results follow', ev("document.querySelector('#gsearchList .gs-row') !== null") is True)
ev("(()=>{ const i=document.getElementById('gsearch'); i.blur(); i.dispatchEvent(new Event('blur')); return true; })()"); wait_ms(500)
check('L4 blur restores sticky header', ev("document.body.classList.contains('gs-kb')") is False)
check('L5 header sticky again', ev("getComputedStyle(document.querySelector('.app-hdr')).position") == 'sticky')

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
