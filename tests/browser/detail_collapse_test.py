import sys, json, time
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

# 固定視窗尺寸（390×844 直向）。未固定時 headless 預設約 764×485，總覽會溢出 217px，C7 前置條件就不成立。
def set_view(w, h, orient):
    cdp('Emulation.setDeviceMetricsOverride', {'width': w, 'height': h, 'deviceScaleFactor': 1, 'mobile': True,
        'screenOrientation': {'type': orient, 'angle': 90 if orient.startswith('landscape') else 0}})
    wait_ms(500)

set_view(390, 844, 'portraitPrimary')
check('V0 fixed viewport 390x844', ev("innerWidth") == 390 and ev("innerHeight") == 844, '%sx%s' % (ev("innerWidth"), ev("innerHeight")))

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
# 量內容實際高度（spacer 高度 0，spacer 頂端即內容底端）。scrollHeight 在內容較矮時會夾成 client，不能直接拿來算溢出。
# spacer 只能往下加，不能縮短原本內容，所以內容高必須 ≤ 視窗高＋100 才成立。
c7 = ev("(()=>{ const sp=document.createElement('div'); sp.id='__spacer'; sp.style.height='0px'; document.getElementById('gsPanelBody').appendChild(sp); const p=document.getElementById('gsPanel'); const content = sp.getBoundingClientRect().top - (p.getBoundingClientRect().top + p.clientTop) + p.scrollTop; return {content: content, client: p.clientHeight}; })()")
content7 = c7.get('content') if isinstance(c7, dict) else None
client7 = c7.get('client') if isinstance(c7, dict) else None
check('C7 precondition: natural content <= viewport + 100px', isinstance(content7, (int, float)) and content7 <= client7 + 100, 'content=%s client=%s' % (content7, client7))
ev("(()=>{ const sp=document.getElementById('__spacer'); const p=document.getElementById('gsPanel'); const c=sp.getBoundingClientRect().top-(p.getBoundingClientRect().top+p.clientTop)+p.scrollTop; sp.style.height=Math.max(0,p.clientHeight+100-c)+'px'; return true; })()")
wait_ms(100)
# 第一次估算會多出 body 底部 padding（約 20px），校正一次到約 100px
ev("(()=>{ const sp=document.getElementById('__spacer'); const p=document.getElementById('gsPanel'); const ov=p.scrollHeight-p.clientHeight; sp.style.height=Math.max(0,sp.offsetHeight-(ov-100))+'px'; return true; })()")
wait_ms(100)
ov7 = ev("(()=>{ const p=document.getElementById('gsPanel'); return p.scrollHeight - p.clientHeight; })()")
check('C7 overflow set to about 100px', isinstance(ov7, (int, float)) and 60 <= ov7 <= 160, 'overflow=%s' % ov7)
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
ev("gsPick('0050'); true"); wait_ms(300)
# 短分頁必須實際放得進畫面：量總覽的內容高度（展開狀態）
ov9 = ev("(()=>{ const p=document.getElementById('gsPanel'); return p.scrollHeight; })()")
ov9_c = ev("document.getElementById('gsPanel').clientHeight")
check('C9 precondition: overview content fits expanded panel', isinstance(ov9, (int, float)) and ov9 <= ov9_c, 'overview scroll=%s client=%s' % (ov9, ov9_c))
ev("detailTab('perf'); true"); wait_ms(300)
ev("(()=>{ const sp=document.createElement('div'); sp.id='__spacer'; sp.style.height='2000px'; document.querySelector('[data-pane=perf]').appendChild(sp); return true; })()")
wait_ms(100)
ev("document.getElementById('gsPanel').scrollTop = 300; true"); wait_ms(400)
cl9 = ev("document.getElementById('gsPanel').clientHeight")
check('C9 precondition: collapsed on long tab', ev("document.body.classList.contains('dt-collapsed')") is True)
check('C9 precondition: overview content fits collapsed panel', isinstance(ov9, (int, float)) and ov9 <= cl9, 'overview scroll=%s collapsed client=%s' % (ov9, cl9))
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
