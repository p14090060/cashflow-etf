import sys, json, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0
# 停用快取後重新載入：避免瀏覽器拿到舊的 js/*.js（同一個 ?v= 版本號會命中快取）
cdp('Network.setCacheDisabled', {'cacheDisabled': True})
cdp('Page.reload'); time.sleep(2.2); wait_ms(600)
# DS：Detail 的分頁與捲動位置（PHASE3_PLAN §16.5 RT-2）。Back → Forward 必須還原同一層的 UI。

def stack_types(): return ev("Router.state().stack.map(l=>l.t).join(',')")
def detail_open(): return ev("!document.getElementById('gsPanel').hidden") is True
def panel_top(): return ev("document.getElementById('gsPanel').scrollTop")
def pane_tab():
    return ev("(function(){ const p=[...document.querySelectorAll('#gsPanelBody .dt-pane')].find(x=>!x.hidden); return p?p.getAttribute('data-pane'):null; })()")
def top_ui(): return ev("(function(){ const st=Router.state(); const t=st.stack[st.stack.length-1]; return JSON.stringify(t?(t.ui||{}):null); })()")
def top_code(): return ev("(function(){ const st=Router.state(); const t=st.stack[st.stack.length-1]; return t?t.code:null; })()")
def set_scroll(v, settle=260):
    ev("document.getElementById('gsPanel').scrollTop = %d; true" % v); wait_ms(settle)
def pop_back(): ev("history.back(); true"); wait_ms(320)
def pop_fwd(): ev("history.forward(); true"); wait_ms(320)
def close_all():
    ev("Router.toBase({base:'home'}); true"); wait_ms(250)

# ── DS-1～DS-3：0050／配息／捲動 120px → Back → Forward 還原同一 UI（Codex 指定情境）──
close_all()
ev("openDetail('0050'); true"); wait_ms(280)
check('DS setup: Detail 0050 open over home (one detail layer)', detail_open() and stack_types() == 'detail' and top_code() == '0050', stack_types())
ev("detailTab('dividend'); true"); wait_ms(120)
check('DS-1 tab change is recorded in the Detail layer (tab=dividend)', '"tab":"dividend"' in top_ui(), top_ui())
set_scroll(120)
pre_scroll = panel_top()
check('DS-1 precondition: panel scrolled to ~120px before Back', pre_scroll > 0 and abs(pre_scroll - 120) <= 6, pre_scroll)
pop_back()
check('DS-2 Back closes Detail (home)', not detail_open() and stack_types() == '', stack_types())
pop_fwd()
check('DS-2 Forward reopens the same Detail 0050', detail_open() and top_code() == '0050', top_code())
check('DS-2 Forward restores tab 配息 (not overview)', pane_tab() == 'dividend', pane_tab())
check('DS-2 Forward restores scroll position (same px, not 0)', abs(panel_top() - pre_scroll) <= 2, (panel_top(), pre_scroll))

# ── DS-3：Back 前的最後一次捲動還沒寫進 history（合併延後），Back → Forward 仍要拿到最新值（快取路徑）──
ev("document.getElementById('gsPanel').scrollTop = 200; true"); wait_ms(60)
pending_not_flushed = ev("(function(){ const s=history.state; const t=s&&s.stack&&s.stack[s.stack.length-1]; return !(t && t.ui && t.ui.scrollTop === 200); })()")
check('DS-3 precondition: history entry not yet flushed when Back is pressed', pending_not_flushed is True)
pop_back()
pop_fwd()
check('DS-3 Back right after scroll then Forward restores latest scroll (200px)', abs(panel_top() - 200) <= 2, panel_top())
check('DS-3 still on the same Detail after Forward', detail_open() and top_code() == '0050')

# ── DS-4：重新整理後，已寫入 history 的分頁與捲動要還原（DS-3 的 flush 已完成）──
wait_ms(300)
cdp('Page.reload'); time.sleep(2.2); wait_ms(700)
check('DS-4 reload restores Detail 0050', detail_open() and top_code() == '0050', top_code())
check('DS-4 reload restores tab 配息', pane_tab() == 'dividend', pane_tab())
check('DS-4 reload restores scroll (200px)', abs(panel_top() - 200) <= 2, panel_top())

# ── DS-5：切換另一檔（replace）沿用分頁、捲動歸零；Back／Forward 還原新檔的 UI ──
L = ev("history.length")
ev("openDetail('0056'); true"); wait_ms(280)
check('DS-5 switch ETF: no new entry (replace)', ev("history.length") == L, (ev("history.length"), L))
check('DS-5 switch ETF: code 0056, tab kept (Phase 2 semantics), scroll reset', top_code() == '0056' and pane_tab() == 'dividend' and panel_top() <= 2, (top_code(), pane_tab(), panel_top()))
pop_back()
check('DS-5 one Back leaves Detail', not detail_open())
pop_fwd()
check('DS-5 Forward restores 0056 with its own UI (tab dividend, scroll 0)', detail_open() and top_code() == '0056' and pane_tab() == 'dividend' and panel_top() <= 2, (top_code(), pane_tab(), panel_top()))

# ── DS-6：分頁在 Detail 內切換（perf）→ Back → Forward 還原 perf，不回到總覽 ──
ev("detailTab('perf'); true"); wait_ms(120)
pop_back()
pop_fwd()
check('DS-6 Forward restores tab 績效 after a second tab change', pane_tab() == 'perf', pane_tab())

# ── DS-7：Detail 開在資料夾之上：Back 只關 Detail，資料夾保留；Forward 還原 Detail 的 UI，資料夾不受影響 ──
close_all()
ev("Router.openFolder('mcap'); true"); wait_ms(350)
ev("openDetail('0050'); true"); wait_ms(280)
check('DS-7 setup: folder mcap + Detail 0050', stack_types() == 'folder,detail', stack_types())
ev("detailTab('perf'); true"); wait_ms(120)
set_scroll(60)
pre7 = panel_top()
pop_back()
check('DS-7 Back closes only the Detail (folder stays)', stack_types() == 'folder' and not detail_open(), stack_types())
pop_fwd()
check('DS-7 Forward: folder + Detail restored', stack_types() == 'folder,detail' and ev("Router.state().stack[0].key") == 'mcap', stack_types())
check('DS-7 Forward restores Detail tab 績效 and scroll', pane_tab() == 'perf' and abs(panel_top() - pre7) <= 2, (pane_tab(), panel_top(), pre7))

# ── DS-8：Detail 的 tab／捲動只寫進 Detail 層，不寫進資料夾層 ──
folder_ui = ev("JSON.stringify(Router.state().stack[0].ui)")
check('DS-8 folder layer ui holds no Detail tab key', '"tab"' not in folder_ui, folder_ui)
check('DS-8 folder layer ui not polluted by Detail scroll (folder list scroll unchanged)', ev("Router.state().stack[0].ui.scrollTop") in (0, None), folder_ui)

check('no uncaught exceptions', len([e for e in events if e.get('method') == 'Runtime.exceptionThrown']) == 0)
fails = [r for r in results if r[1] is False]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
