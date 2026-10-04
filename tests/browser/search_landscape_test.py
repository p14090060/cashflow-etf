import sys, json, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

# 矮視窗（橫向）：搜尋框取得焦點時進入 gs-kb 狀態，離開後回復
ev("(()=>{ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); return true; })()"); wait_ms(600)
check('L1 landscape focus enters gs-kb', ev("document.body.classList.contains('gs-kb')") is True, ev("window.innerHeight"))
check('L2 header becomes non-sticky', ev("getComputedStyle(document.querySelector('.app-hdr')).position") == 'static')
check('L3 bottom nav hidden', ev("getComputedStyle(document.querySelector('.bottom-nav')).display") == 'none')
ev("(()=>{ const i=document.getElementById('gsearch'); i.focus(); i.dispatchEvent(new Event('focus')); i.value='0050'; i.dispatchEvent(new Event('input')); return true; })()"); wait_ms(300)
check('L6 landscape results show keyboard hint row', ev("!!document.querySelector('#gsearchList .gs-kb-hint')") is True)
check('L6b hint row is first, results follow', ev("document.querySelector('#gsearchList .gs-row') !== null") is True)
ev("(()=>{ const i=document.getElementById('gsearch'); i.blur(); i.dispatchEvent(new Event('blur')); return true; })()"); wait_ms(500)
check('L4 blur restores sticky header', ev("document.body.classList.contains('gs-kb')") is False)
check('L5 header sticky again', ev("getComputedStyle(document.querySelector('.app-hdr')).position") == 'sticky')

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
