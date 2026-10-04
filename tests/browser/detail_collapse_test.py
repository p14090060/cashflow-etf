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

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
