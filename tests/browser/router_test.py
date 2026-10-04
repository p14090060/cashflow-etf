import sys, json
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0
# 手動計時：timeout／3 秒處理中只由 hook 觸發，避免測試期間自動計時器亂入
ev("window.__routerManualTimers = true; window.__routerDeferTraversal = false; true")

def st(): return ev("JSON.stringify(Router.state())")
def stack_types(): return ev("Router.state().stack.map(l=>l.t).join(',')")
def tcount(): return ev("__routerTraversalCount")
def comp(): return ev("__routerCompletions")
def pruns(): return ev("__routerParkedRuns")
def hlen(): return ev("history.length")
def hstate(): return ev("JSON.stringify(history.state)")
def pop_back(): ev("history.back(); true"); wait_ms(260)
def pop_fwd(): ev("history.forward(); true"); wait_ms(260)
def key_esc(): ev("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); true"); wait_ms(260)

# 起點：基底首頁，stack 為空
ev("switchPage('today'); true"); wait_ms(200)
check('START base home stack empty', ev("Router.state().base") == 'home' and ev("Router.state().stack.length") == 0)

# ── RT-1／RT-2／RT-9：總覽 → 資料夾 → Detail → Back → 資料夾 → Back → 總覽；Forward 還原；user Back 不呼叫 back ──
ev("Router.toBase({base:'cat'}); true"); wait_ms(120)
ev("Router.openFolder('mcap'); true"); wait_ms(300)
ev("openDetail('0050'); true"); wait_ms(300)
check('RT-1 setup: folder mcap + detail 0050', stack_types() == 'folder,detail', stack_types())
t0 = tcount()
pop_back()
check('RT-1 Back closes Detail, folder stays', stack_types() == 'folder' and ev("!document.getElementById('gsPanel').hidden") is False)
check('RT-9 user Back issues no programmatic traversal', tcount() == t0, (tcount(), t0))
pop_back()
check('RT-1 Back again returns to overview (base cat, empty)', ev("Router.state().base") == 'cat' and ev("Router.state().stack.length") == 0)
check('RT-1 overview: folder closed', ev("document.getElementById('page-cat').dataset.state") == 'overview')
pop_fwd()
check('RT-2 Forward restores folder mcap', stack_types() == 'folder' and ev("Router.state().stack[0].key") == 'mcap')
pop_fwd()
check('RT-2 Forward again restores Detail 0050', stack_types() == 'folder,detail' and ev("Router.state().stack[1].code") == '0050')

# ── RT-3：Detail reload 還原資料夾＋Detail；不產生空白 entry ──
L = hlen()
cdp('Page.reload'); time.sleep(2.2); wait_ms(600)
ev("window.__routerManualTimers = true; window.__routerDeferTraversal = false; true")
check('RT-3 reload restores folder+detail', stack_types() == 'folder,detail', stack_types())
check('RT-3 reload: Detail visible, folder rows rendered', ev("!document.getElementById('gsPanel').hidden") is True and ev("document.querySelectorAll('#catList .cat-row').length") > 0)
check('RT-8 reload does not add entries', hlen() == L, (hlen(), L))

# ── RT-11：Detail 開著切換另一檔 → replace，不增加 entry；一次 Back 直接離開 Detail ──
L = hlen()
ev("openDetail('0056'); true"); wait_ms(200)
check('RT-11 switch ETF replaces (no new entry)', hlen() == L, (hlen(), L))
check('RT-11 switch ETF: code 0056 in state', ev("Router.state().stack[1].code") == '0056')
pop_back()
check('RT-11 one Back leaves Detail (not previous ETF)', stack_types() == 'folder' and ev("document.getElementById('gsPanel').hidden") is True)

# ── RT-5：Esc 只退一層 ──
ev("openDetail('0050'); true"); wait_ms(200)
key_esc()
check('RT-5 ESC 1 closes Detail only', stack_types() == 'folder')
key_esc()
check('RT-5 ESC 2 closes folder', ev("Router.state().stack.length") == 0)

# ── RT-6／RT-7：返回資料夾後排序、已展開數、捲動位置保留 ──
ev("Router.openFolder('active'); true"); wait_ms(320)
ev("Router.updateUi({sort:'name', shown:20}); true")
ev("(function(){ const l=document.getElementById('catList'); l.style.maxHeight='120px'; l.scrollTop=60; return true; })()"); wait_ms(60)
ev("Category.snapshot(); true")
ev("openDetail('00402A'); true"); wait_ms(250)
pop_back()
check('RT-6 sort kept after Detail back', ev("Router.state().stack[0].ui.sort") == 'name')
check('RT-6 shown kept after Detail back (20)', ev("Router.state().stack[0].ui.shown") == 20)
check('RT-6 rendered 20 rows', ev("document.querySelectorAll('#catList .cat-row').length") == 20)
check('RT-7 scroll position kept (~60px)', abs((ev("document.getElementById('catList').scrollTop") or 0) - 60) <= 4, ev("document.getElementById('catList').scrollTop"))
ev("Router.closeFolder(); true"); wait_ms(320)

# ── RT-4：Detail 開著切換底部導覽 → 全部關閉、導覽正確、無殘留 ──
ev("Router.toBase({base:'cat'}); true"); wait_ms(120)
ev("Router.openFolder('theme'); true"); wait_ms(300)
ev("openDetail('0050'); true"); wait_ms(250)
t0 = tcount()
ev("switchPage('today'); true"); wait_ms(300)
check('RT-4 nav switch closes folder and Detail', ev("Router.state().base") == 'home' and ev("Router.state().stack.length") == 0)
check('RT-4 nav switch issues exactly one traversal', tcount() - t0 == 1, tcount() - t0)
check('RT-4 page-today active, Detail hidden', ev("document.getElementById('page-today').classList.contains('active')") is True and ev("document.getElementById('gsPanel').hidden") is True)

# ── RT-12：工具子頁 → Back 回工具列表 ──
ev("switchPage('tools'); true"); wait_ms(150)
ev("Router.toBase({tool:'rank', base:'tools'}); true"); wait_ms(250)
check('RT-12 tool rank page active', ev("document.getElementById('page-rank').classList.contains('active')") is True)
pop_back()
check('RT-12 Back returns to tools list', ev("document.getElementById('page-tools').classList.contains('active')") is True and ev("Router.state().stack.length") == 0)

# ── RT-13：Phase 2 格式的 state（etfDetail）在真實導覽中正規化，不新增 entry、不覆寫其他 entry ──
ev("switchPage('today'); true"); wait_ms(200)
L = hlen()
ev("history.pushState({etfDetail: 1, code: '0050'}, ''); true")   # 模擬 Phase 2 留下的 entry
pop_back()                                                        # 離開（回到 v2 基底）
check('RT-13 setup: back on v2 base before legacy forward', ev("Router.state().v") == 2 and ev("Router.state().stack.length") == 0)
Lfwd = hlen()
pop_fwd()                                                         # 真實 popstate 抵達 legacy entry
check('RT-13 legacy etfDetail normalized to v2 detail layer', stack_types() == 'detail' and ev("Router.state().v") == 2, st())
check('RT-13 legacy entry replaced in place (state is v2 now)', ev("history.state && history.state.v") == 2)
check('RT-13 normalization adds no entry (length unchanged by forward+normalize)', hlen() == Lfwd, (hlen(), Lfwd))
ev("switchPage('today'); true"); wait_ms(250)

# ════════════════════════════════════════════════════════════════════════
# RT-14～RT-19、RT-21：traversal 本身尚未完成（deferred），timeout、3 秒處理中、parked、release
# ════════════════════════════════════════════════════════════════════════
ev("Router.openDetail('0050'); true"); wait_ms(220)            # base home, stack [detail 0050]
L0 = hlen(); S0 = hstate()
ev("window.__routerDeferTraversal = true; true")
t_before = tcount()
ev("Router.openFlow('0050'); true"); wait_ms(60)               # k=1：traversal(-1) 排入佇列，尚未執行
check('RT-18 deferred: traversal queued, not executed', ev("__routerDeferredCount()") == 1 and ev("__routerInflightState()") == 'active', ev("__routerDeferredCount()"))
check('RT-18 deferred: history.state and length unchanged', hstate() == S0 and hlen() == L0)
check('RT-18 deferred: location still on the page (no navigation happened)', ev("location.href.indexOf('index.html') >= 0") is True)
check('RT-21 openFlow issued exactly one traversal', tcount() - t_before == 1, tcount() - t_before)

ev("__routerForceTimeout(); true"); wait_ms(60)               # 500ms：只取消 continuation，槽位仍佔用
check('RT-14 timeout marks inflight orphan (slot still occupied)', ev("__routerInflightState()") == 'orphan')
check('RT-14 timeout keeps screen unchanged (Detail still open, no flow)', ev("!document.getElementById('gsPanel').hidden") is True and ev("Category.isFlowVisible()") is False)
check('RT-14 timeout does not write history', hstate() == S0 and hlen() == L0)

ev("switchPage('tools'); true"); wait_ms(60)                  # 使用者立即導航：orphan 階段 → parked
ev("switchPage('watch'); true"); wait_ms(60)                  # 再一次：last wins
check('RT-16 parked: no new traversal issued while orphan', tcount() - t_before == 1, tcount() - t_before)
check('RT-16 parked: history.state still the Detail entry (not overwritten)', hstate() == S0)
check('RT-16 parked: history.length unchanged before release', hlen() == L0)
check('RT-16 parked: intent not executed yet (parked runs == 0)', pruns() == 0, pruns())

ev("__routerForceProcessingMark(); true"); wait_ms(60)        # 3 秒：只顯示處理中
check('RT-19 3s processing shown', ev("__routerProcessing()") is True and ev("!document.getElementById('routerProc').hidden") is True)
check('RT-19 3s: no second traversal', tcount() - t_before == 1, tcount() - t_before)
check('RT-19 3s: inflight still orphan (not cleared by timer)', ev("__routerInflightState()") == 'orphan')
check('RT-19 3s: history not written early', hstate() == S0 and hlen() == L0)
check('RT-19 3s: parked not executed by timer (parked runs == 0)', pruns() == 0, pruns())

c0 = comp()
ev("__routerReleaseTraversal(); true"); wait_ms(320)          # 舊 traversal 真正完成（真實 popstate）
check('RT-15 old traversal completes exactly once', comp() - c0 == 1, comp() - c0)
check('RT-15 old continuation never executed (no flow entry, no Category flow)', ev("Category.isFlowVisible()") is False and stack_types() == '')
check('RT-15/17 parked executed exactly once after confirmation', pruns() == 1, pruns())
check('RT-17 final: parked (watch) applied on confirmed state', ev("Router.state().base") == 'watch' and ev("document.getElementById('page-watch').classList.contains('active')") is True)
check('RT-21 release adds no traversal', tcount() - t_before == 1, tcount() - t_before)
check('RT-19 processing hidden after completion', ev("__routerProcessing()") is False and ev("document.getElementById('routerProc').hidden") is True)
check('RT-17 history length unchanged after parked base change (replace only)', hlen() == L0, (hlen(), L0))
ev("window.__routerDeferTraversal = false; true")

# ── RT-20：完成後 Back／Forward 順序正確 ──
ev("Router.openFolder('mcap'); true"); wait_ms(200)
ev("openDetail('0050'); true"); wait_ms(200)
pop_back()
check('RT-20 Back from Detail returns to folder mcap', stack_types() == 'folder' and ev("Router.state().stack[0].key") == 'mcap')
pop_back()
check('RT-20 Back from folder returns to base (E0 replaced by cat when folder pushed)', ev("Router.state().base") == 'cat' and ev("Router.state().stack.length") == 0, ev("Router.state().base"))
pop_fwd()
check('RT-20 Forward goes to folder mcap', stack_types() == 'folder' and ev("Router.state().stack[0].key") == 'mcap')
pop_fwd()
check('RT-20 Forward goes to Detail 0050', stack_types() == 'folder,detail' and ev("Router.state().stack[1].code") == '0050')

# ── RT-10：busy 鎖——同一次同步呼叫內連按兩次 Esc，只退一層 ──
ev("(function(){ document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); return true; })()"); wait_ms(300)
check('RT-10 double Esc in one tick closes only one layer', stack_types() == 'folder', stack_types())
ev("switchPage('today'); true"); wait_ms(250)

# ── RT-22：排行頁的列進入持股異動（工具子頁 → openFlow）→ Back 回工具子頁 ──
ev("switchPage('rank'); true"); wait_ms(200)
check('RT-22 setup: rank tool page is active', ev("document.getElementById('page-rank').classList.contains('active')") is True)
ev("Router.openFlow('0050'); true"); wait_ms(320)
check('RT-22 openFlow from tool goes to 分類 → 主動式 持股異動 (single layer, no tool layer left)', ev("Router.state().base") == 'cat' and stack_types() == 'folder' and ev("Router.state().stack[0].view") == 'flow' and ev("Category.isFlowVisible()") is True, st())
pop_back()
check('RT-22 Back from flow returns to 分類總覽 (same as §8 sources; base E0 replaced to cat)', ev("Router.state().base") == 'cat' and ev("Router.state().stack.length") == 0 and ev("document.getElementById('page-cat').dataset.state") == 'overview', st())
ev("switchPage('today'); true"); wait_ms(200)

# ── SR-1：分類頁開著時，全域搜尋仍可開 Detail；關閉後資料夾保留 ──
ev("switchPage('cat'); true"); wait_ms(150)
ev("Router.openFolder('active'); true"); wait_ms(300)
ev("gsPick('0050'); true"); wait_ms(250)
check('SR-1 search pick opens Detail over the open folder', stack_types() == 'folder,detail' and ev("!document.getElementById('gsPanel').hidden") is True, st())
ev("closeDetail(); true"); wait_ms(260)
check('SR-1 closing Detail keeps the folder open', stack_types() == 'folder' and ev("Category.isFlowVisible()") is False and ev("document.getElementById('page-cat').dataset.state") == 'open')
ev("Router.closeFolder(); true"); wait_ms(320)
ev("switchPage('today'); true"); wait_ms(200)

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if r[1] is False]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
