import sys, json, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

def wait_event(name, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        msg = json.loads(ws.recv())
        if msg.get('method') == name:
            return True
    return False

# ── F2：Back 關閉 Detail 時同步收起搜尋下拉
ev("gsPick('0050'); true"); wait_ms(200)
ev("const i=document.getElementById('gsearch'); i.value='0056'; i.dispatchEvent(new Event('input')); true"); wait_ms(150)
check('F2 precondition: dropdown open', ev("!document.getElementById('gsearchList').hidden") is True)
ev("window.__pop=0; true")
ev("history.back(); true"); wait_ms(500)
check('F2 back closes detail', ev("document.getElementById('gsPanel').hidden") is True)
check('F2 back also hides dropdown', ev("document.getElementById('gsearchList').hidden") is True)
check('F2 single popstate', ev("window.__pop") == 1, ev("window.__pop"))
ev("gsClear(); true")

# ── F1-b：pending restore 遇到基底 entry，延遲 callback 不得開啟 Detail
ev("(()=>{ history.replaceState(null,''); detailOnMarketUpdate(); })(); true"); wait_ms(100)   # Phase 3：pending restore 由 router 管理，這裡只保留行為情境
check('F1 pending restore on base entry does not open detail', ev("document.getElementById('gsPanel').hidden") is True)
check('F1 pending restore cleared (v2: no detail layer on base)', ev("Router.state().stack.length") == 0)   # Phase 3：內部 _restoreCode → router 的 stack

# ── F1-c：popstate 離開 entry 時取消 pending restore
ev("(()=>{ history.replaceState(null,''); window.dispatchEvent(new PopStateEvent('popstate',{state:null})); })(); true"); wait_ms(100)   # Phase 3：同上
check('F1 popstate cancels pending restore (v2: stack empty)', ev("Router.state().stack.length") == 0)   # Phase 3：內部 _restoreCode → router 的 stack
check('F1 popstate on base keeps detail closed', ev("document.getElementById('gsPanel').hidden") is True)

# ── F1-a：真實流程：開 Detail → 重整 → 在資料回來前按 Back
ev("gsPick('0050'); true"); wait_ms(300)
cdp('Page.reload', {'ignoreCache': False})
wait_event('Page.domContentEventFired')
r = ev("(()=>{ try { history.back(); return 'ok'; } catch(e){ return 'err '+e; } })()")
time.sleep(2.5)
# 文件可能因跨文件返回而重新載入；只要求：沒有開啟的 Detail、沒有 detail 標記、無例外
ok_state = ev("(()=>{ const s=history.state; return !(s && s.etfDetail); })()")
panel_hidden = ev("document.getElementById('gsPanel') ? document.getElementById('gsPanel').hidden : true")
check('F1 real: reload then back leaves no detail open', panel_hidden is True and ok_state is True, 'panel_hidden=%s state_ok=%s' % (panel_hidden, ok_state))
time.sleep(2)
panel_later = ev("document.getElementById('gsPanel') ? document.getElementById('gsPanel').hidden : true")
check('F1 real: no late restore after data arrives', panel_later is True, panel_later)

# ── 回歸：一般重整還原仍有效
load_page()
ev("gsPick('0050'); true"); wait_ms(300)
cdp('Page.reload', {'ignoreCache': False})
wait_event('Page.domContentEventFired')
time.sleep(2.5)
ev("window.__pop=0; true")
check('R reload restores detail (normal path)', ev("!document.getElementById('gsPanel').hidden && document.getElementById('gsPanelTitle').textContent.includes('0050')") is True)
ev("document.querySelector('#dtClose').click(); true"); wait_ms(400)
check('R close after restore leaves no detail', ev("document.getElementById('gsPanel').hidden") is True)

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
