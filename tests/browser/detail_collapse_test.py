import sys, json, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

hdr_display = "getComputedStyle(document.querySelector('.app-hdr')).display"
panel_top = "getComputedStyle(document.getElementById('gsPanel')).top"

def add_spacer():
    ev("(()=>{ const sp=document.createElement('div'); sp.id='__spacer'; sp.style.height='2000px'; document.getElementById('gsPanelBody').appendChild(sp); })(); true")

# ── C1 往下捲：收起頂部區域
ev("gsPick('0050'); true"); wait_ms(300)
add_spacer(); wait_ms(100)
ev("document.getElementById('gsPanel').scrollTop = 300; true"); wait_ms(300)
check('C1 scroll down collapses header', ev("document.body.classList.contains('dt-collapsed')") is True)
check('C1 header hidden', ev(hdr_display) == 'none', ev(hdr_display))
check('C1 panel fills top', ev(panel_top) == '0px', ev(panel_top))

# ── C2 回到頂部：頂部區域重新出現，高度重新量測
ev("document.getElementById('gsPanel').scrollTop = 0; true"); wait_ms(300)
check('C2 back to top shows header', ev("document.body.classList.contains('dt-collapsed')") is False)
check('C2 header visible again', ev(hdr_display) != 'none', ev(hdr_display))
check('C2 header height re-measured', ev("parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--hdr-h'))") > 0)

# ── C3 滯後區間：捲到 2px 不收起、不閃動
ev("document.getElementById('gsPanel').scrollTop = 2; true"); wait_ms(250)
check('C3 small scroll (2px) does not collapse', ev("document.body.classList.contains('dt-collapsed')") is False)

# ── C4 關閉 Detail 時一定還原頂部區域
ev("document.getElementById('gsPanel').scrollTop = 300; true"); wait_ms(250)
check('C4 collapsed before close', ev("document.body.classList.contains('dt-collapsed')") is True)
ev("closeDetail(); true"); wait_ms(300)
check('C4 close restores header', ev("document.body.classList.contains('dt-collapsed')") is False and ev(hdr_display) != 'none')

# ── C5 沒有超出內容時不收起
ev("gsPick('0050'); true"); wait_ms(300)
check('C5 short content never collapses', ev("document.body.classList.contains('dt-collapsed')") is False)
ev("closeDetail(); true"); wait_ms(300)

# ── C6 計算機輸入框獲得焦點不產生例外
ev("gsPick('0050'); detailTab('dividend'); true"); wait_ms(300)
ev("document.getElementById('dtSharesIn').focus(); true"); wait_ms(500)
ev("closeDetail(); true"); wait_ms(300)


# ── C7 略有溢出（約 100px）：不得收合，也不得閃動
ev("gsPick('0050'); true"); wait_ms(300)
ev("(()=>{ const sp=document.createElement('div'); sp.id='__spacer'; document.getElementById('gsPanelBody').appendChild(sp); const p=document.getElementById('gsPanel'); sp.style.height='0px'; const ov=p.scrollHeight-p.clientHeight; sp.style.height=Math.max(0,100-ov)+'px'; return true; })()")
wait_ms(100)
ov7 = ev("(()=>{ const p=document.getElementById('gsPanel'); return p.scrollHeight - p.clientHeight; })()")
check('C7 precondition: overflow about 100px', isinstance(ov7, (int, float)) and 60 <= ov7 <= 160, ov7)
ev("document.getElementById('gsPanel').scrollTop = 100; true"); wait_ms(600)
check('C7 slight overflow does not collapse', ev("document.body.classList.contains('dt-collapsed')") is False)
check('C7 scroll position not forced to 0', (ev("document.getElementById('gsPanel').scrollTop") or 0) > 50, ev("document.getElementById('gsPanel').scrollTop"))
ev("closeDetail(); true"); wait_ms(300)

# ── C8 明顯溢出：收合後位置仍保留，不會被壓回 0
ev("gsPick('0050'); true"); wait_ms(300)
add_spacer(); wait_ms(100)
ev("document.getElementById('gsPanel').scrollTop = 300; true"); wait_ms(600)
check('C8 collapsed after clear overflow', ev("document.body.classList.contains('dt-collapsed')") is True)
check('C8 stays collapsed, no bounce to top', ev("document.body.classList.contains('dt-collapsed')") is True and (ev("document.getElementById('gsPanel').scrollTop") or 0) > 200, ev("document.getElementById('gsPanel').scrollTop"))
ev("closeDetail(); true"); wait_ms(300)

# ── C9 收合中切到短分頁：應自動展開一次並穩定，不來回閃動
ev("gsPick('0050'); detailTab('perf'); true"); wait_ms(300)
ev("(()=>{ const sp=document.createElement('div'); sp.id='__spacer'; sp.style.height='2000px'; document.querySelector('[data-pane=perf]').appendChild(sp); return true; })()")
wait_ms(100)
ev("document.getElementById('gsPanel').scrollTop = 300; true"); wait_ms(400)
check('C9 precondition: collapsed on long tab', ev("document.body.classList.contains('dt-collapsed')") is True)
ev("window.__cls = 0; window.__mo = new MutationObserver(() => { window.__cls++; }); window.__mo.observe(document.body, { attributes: true, attributeFilter: ['class'] }); true")
ev("detailTab('overview'); true"); wait_ms(1000)
toggles = ev("(()=>{ window.__mo.disconnect(); return window.__cls; })()")
check('C9 short tab restores header once', ev("document.body.classList.contains('dt-collapsed')") is False)
check('C9 no oscillation after tab switch', isinstance(toggles, int) and toggles <= 1, toggles)
ev("closeDetail(); true"); wait_ms(300)

# ── C10 長內容捲動中不閃動（收合後穩定）
ev("gsPick('0050'); true"); wait_ms(300)
add_spacer(); wait_ms(100)
ev("window.__cls = 0; window.__mo = new MutationObserver(() => { window.__cls++; }); window.__mo.observe(document.body, { attributes: true, attributeFilter: ['class'] }); true")
ev("document.getElementById('gsPanel').scrollTop = 300; true"); wait_ms(1000)
toggles10 = ev("(()=>{ window.__mo.disconnect(); return window.__cls; })()")
check('C10 collapse happens once, no flicker', isinstance(toggles10, int) and toggles10 <= 1, toggles10)
ev("closeDetail(); true"); wait_ms(300)

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
