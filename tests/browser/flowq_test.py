"""Phase 5 CP6d（PO Change #3）：Active Flow ETF 快速搜尋（PHASE5_PLAN §8.4；FQ-1～FQ-9）。

FQ-10＝FS-1～6（tools_test.py）與完整 regression。執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
"""
import sys, json
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

ev("clearInterval(_pollTimer); window.__routerManualTimers = true; true")
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowData||Date.now()-t>20000){clearInterval(i);r(true)}},100)})", True)

def st(): return json.loads(ev("JSON.stringify(Router.state())"))
def types(): return ev("Router.state().stack.map(l=>l.t+(l.view?':'+l.view:'')).join()")
def back(ms=400): ev("history.back(); true"); wait_ms(ms)
def fwd(ms=400): ev("history.forward(); true"); wait_ms(ms)
def flow_vis(): return ev("flowLayerVisible() || Category.isFlowVisible()") is True
HSPY = """(()=>{ window.__hc = {push:0, rep:0};
  if (!window.__hspy) { window.__hspy = 1; const P = history.pushState, Rp = history.replaceState;
    history.pushState = function () { window.__hc.push++; return P.apply(history, arguments); };
    history.replaceState = function () { window.__hc.rep++; return Rp.apply(history, arguments); }; }
  return true; })()"""
QS = """(()=>{const b=document.getElementById('flowQBtn'), box=document.getElementById('flowQBox'), i=document.getElementById('flowQ'); const r=b.getBoundingClientRect();
  return {open:b.getAttribute('aria-expanded'), ctl:b.getAttribute('aria-controls'), name:b.getAttribute('aria-label'), tag:b.tagName, dis:b.disabled, w:r.width, h:r.height,
          boxHidden:box.hidden, boxDisp:getComputedStyle(box).display, q:i.value, focus:document.activeElement===i, btnFocus:document.activeElement===b,
          items:[...document.querySelectorAll('#flowQList .flow-q-item')].map(x=>x.dataset.code), empty:(document.querySelector('#flowQList .flow-q-empty')||{}).textContent||null,
          vis: !!b.offsetParent}})()"""
def qs(): return ev(QS)
def typeq(q):
    ev("{const i=document.getElementById('flowQ'); i.value=%s; i.dispatchEvent(new Event('input'));} true" % json.dumps(q)); wait_ms(150)
def key(k, code, vk):
    cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': k, 'code': code, 'windowsVirtualKeyCode': vk, **({'text': '\r'} if k == 'Enter' else {})})
    cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': k, 'code': code, 'windowsVirtualKeyCode': vk}); wait_ms(300)
def click_btn():
    ev("""(()=>{const b=document.getElementById('flowQBtn'); const r=b.getBoundingClientRect(); document.elementFromPoint(r.left+r.width/2, r.top+r.height/2).click(); return true})()"""); wait_ms(200)

FL = ev("Object.keys(_flowData.etfs).sort()")
NAMES = ev("Object.fromEntries(Object.keys(_flowData.etfs).map(k=>[k,_flowData.etfs[k].name]))")
NOFLOW = ev("(ETFS.find(e=>!_flowData.etfs[e.code] && /^00/.test(e.code))||{}).code")
check('setup: flow data ok、至少 10 檔、有一檔非 Flow ETF', ev("_flowStatus") == 'ok' and len(FL) >= 10 and bool(NOFLOW), (len(FL), NOFLOW))
A = FL[len(FL) // 2]; B = FL[-1]

cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})

# ── FQ-1 四種入口都有 🔍、預設收起、尺寸與 a11y、標題單行
def enter(which):
    ev("Router.toBase({base:'home'}); true"); wait_ms(300)
    if which == 'tools':
        ev("switchPage('tools'); true"); wait_ms(250); ev("document.getElementById('toolFlow').click(); true")
    elif which == 'rank':
        ev("switchPage('rank'); true"); wait_ms(300); ev("openFlow(%s); true" % json.dumps(A))
    elif which == 'detail':
        ev("openDetail(%s); true" % json.dumps(A)); wait_ms(350); ev("detailTab('holdings'); true"); wait_ms(200); ev("document.querySelector('.gs-flow-btn').click(); true")
    else:
        ev("Router.toBase({base:'cat'}); true"); wait_ms(250); ev("Router.openFolder('active'); true"); wait_ms(600); ev("Router.setFolderView('flow'); true")
    wait_ms(500)
for which in ('tools', 'rank', 'detail', 'cat'):
    enter(which)
    q = qs()
    title1 = ev("(()=>{const t=document.querySelector('#flowHead .flow-title'), b=document.getElementById('flowQBtn'); const tr=t.getBoundingClientRect(), br=b.getBoundingClientRect(); return tr.height<=30 && Math.abs((tr.top+tr.bottom)/2-(br.top+br.bottom)/2)<12})()")
    check('FQ-1 [%s] 有 🔍、預設收起、button ≥44px、aria-expanded／controls／name、標題單行與 🔍 同列' % which,
          flow_vis() and q['vis'] and q['tag'] == 'BUTTON' and not q['dis'] and q['open'] == 'false' and q['ctl'] == 'flowQBox' and q['name'] == '在主動式 ETF 中搜尋'
          and q['w'] >= 44 and q['h'] >= 44 and q['boxHidden'] and q['boxDisp'] == 'none' and title1 is True, (q, title1))
cdp('Emulation.setDeviceMetricsOverride', {'width': 360, 'height': 740, 'deviceScaleFactor': 2, 'mobile': True}); wait_ms(300)
t360 = ev("(()=>{const t=document.querySelector('#flowHead .flow-title').getBoundingClientRect(); const b=document.getElementById('flowQBtn').getBoundingClientRect(); return {h:t.height, sameRow:Math.abs((t.top+t.bottom)/2-(b.top+b.bottom)/2)<12, ov:document.documentElement.scrollWidth-document.documentElement.clientWidth}})()")
check('FQ-1 360px：標題單行、與 🔍 同列、無水平溢出', t360['h'] <= 30 and t360['sameRow'] and t360['ov'] <= 0, t360)
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}); wait_ms(300)

# ── FQ-2 展開／收起（從 Tools 入口）
enter('tools')
y0 = ev("Math.round(scrollY)"); ly0 = ev("document.getElementById('flowLayer').scrollTop")
click_btn()
q = qs()
check('FQ-2 點 🔍 展開：輸入框可見並取得焦點、window 不捲動', q['open'] == 'true' and not q['boxHidden'] and q['focus'] and ev("Math.round(scrollY)") == y0, (q, y0))
click_btn()
q = qs()
check('FQ-2 再點 🔍 收起、焦點回 🔍', q['open'] == 'false' and q['boxHidden'] and q['btnFocus'], q)

# ── FQ-3 搜尋
click_btn()
typeq(A)
q = qs()
check('FQ-3 代碼完全相同 %s → 第一筆' % A, q['items'][:1] == [A], q['items'])
pre = A[:4]
typeq(pre)
q = qs()
exp = [c for c in FL if c.startswith(pre)][:8]
check('FQ-3 代碼開頭「%s」→ 只出現 Flow ETF、依代碼排序、≤ 8 筆' % pre, q['items'] == exp and len(q['items']) <= 8 and all(c in FL for c in q['items']), (q['items'], exp))
nm = (NAMES.get(B) or '')
kw = nm.replace('主動', '')[:2] if nm.startswith('主動') else nm[:2]
typeq(kw)
q = qs()
check('FQ-3 名稱關鍵字「%s」找得到 %s（%s）' % (kw, B, nm), B in q['items'] and all(c in FL for c in q['items']), q['items'])
typeq('0050' if '0050' not in FL else NOFLOW)
typeq(NOFLOW)
q = qs()
check('FQ-3 非 Flow ETF（%s）查無、顯示說明' % NOFLOW, q['items'] == [] and bool(q['empty']) and '找不到' in q['empty'], q)
# 排序：完全相同 > 開頭 > 包含（以 A 的末三碼當「包含」查詢）
mix = A[-3:]
typeq(mix)
q = qs()
sc = ev("%s.map(c=>_matchEtf({code:c,name:_flowData.etfs[c].name||''}, %s))" % (json.dumps(q['items']), json.dumps(mix.upper())))
check('FQ-3 排序依 _matchEtf 分數由高到低（%s）' % mix, sc == sorted(sc, reverse=True) and len(sc) >= 1, (q['items'], sc))

# ── FQ-4／FQ-5 選取＝點 chip；不寫 history
def snap():
    return ev("""({sel:_flowSel, active:(document.querySelector('#flowChips .flow-chip.active')||{}).dataset.code, name:document.getElementById('flowSelName').textContent,
      buy:document.getElementById('flowBuy').textContent, sell:document.getElementById('flowSell').textContent, cells:document.querySelectorAll('#treemap .tm-cell').length,
      tip:document.getElementById('flowTip').textContent, chipVis:(()=>{const b=document.getElementById('flowChips'), a=b.querySelector('.flow-chip.active'); if(!a) return false; const br=b.getBoundingClientRect(), ar=a.getBoundingClientRect(); return ar.left>=br.left-1 && ar.right<=br.right+1})()})""")
# 對照組：點 chip 選 B
ev("document.querySelector('#flowChips .flow-chip[data-code=\"%s\"]').click(); true" % B); wait_ms(300)
ref = snap()
ev("document.querySelector('#flowChips .flow-chip[data-code=\"%s\"]').click(); true" % FL[0]); wait_ms(300)
L = ev("history.length"); n0 = len(st()['stack'])
ev(HSPY)
typeq(B)
ev("document.querySelector('#flowQList .flow-q-item[data-code=\"%s\"]').click(); true" % B); wait_ms(350)
got = snap(); q = qs()
check('FQ-4 搜尋選取 %s 與點 chip 結果相同（active chip／名稱／加碼減碼／treemap／提示）' % B, got == ref, (got, ref))
check('FQ-4 選取 chip 在可視範圍、搜尋收起、焦點回 🔍', got['chipVis'] and q['boxHidden'] and q['btnFocus'], (got['chipVis'], q))
check('FQ-5 pushState 0、history.length 與 stack 長度不變（Tools 入口：寫 flow.ui.code）',
      ev("window.__hc.push") == 0 and ev("history.length") == L and len(st()['stack']) == n0 and st()['stack'][-1]['ui'].get('code') == B, (ev("window.__hc"), st()))

# ── FQ-6 返回／前進
back()
check('FQ-6 Tools 入口：Back → 三張卡', ev("document.getElementById('page-tools').classList.contains('active')") is True and st()['stack'] == [] and not flow_vis())
fwd()
check('FQ-6 Forward → Flow 顯示剛選的 %s' % B, ev("_flowSel") == B and ev("flowLayerVisible()") is True)
check('FQ-8 Flow 關閉後重新進入：預設收起、query 清空', qs()['boxHidden'] and qs()['q'] == '' and qs()['open'] == 'false', qs())
back()
for which, back_ok in (('rank', "Router.state().stack.map(l=>l.t).join()==='tool' && document.getElementById('page-rank').classList.contains('active')"),
                       ('detail', "Router.state().stack.map(l=>l.t).join()==='detail' && !document.getElementById('gsPanel').hidden")):
    enter(which)
    ev(HSPY); n0 = len(st()['stack'])
    click_btn(); typeq(B)
    key('Enter', 'Enter', 13)
    check('FQ-8／FQ-5 [%s] Enter 選第一筆 → %s、pushState 0、stack 不變' % (which, B), ev("_flowSel") == B and ev("window.__hc.push") == 0 and len(st()['stack']) == n0 and qs()['boxHidden'], (ev("_flowSel"), ev("window.__hc")))
    back()
    check('FQ-6 [%s] Back → 原入口' % which, ev(back_ok) is True, types())
# 分類原生：寫 folder.ui.code
enter('cat')
ev(HSPY); n0 = len(st()['stack']); L = ev("history.length")
click_btn(); typeq(A); key('Enter', 'Enter', 13)
s = st()
check('FQ-5 分類原生：選取寫 folder.ui.code、pushState 0、不新增層', s['stack'][0]['t'] == 'folder' and s['stack'][0]['ui'].get('code') == A and ev("window.__hc.push") == 0 and len(s['stack']) == n0 and ev("history.length") == L, (s, ev("window.__hc")))
ev("Router.setFolderView('list'); true"); wait_ms(300)
ev("Router.setFolderView('flow'); true"); wait_ms(400)
check('FQ-8 分類原生離開持股異動再回來：預設收起、query 清空', qs()['boxHidden'] and qs()['q'] == '', qs())

# ── FQ-7 Esc（Blocking）
enter('tools')
click_btn(); typeq(A)
key('Escape', 'Escape', 27)
q = qs()
check('FQ-7 搜尋開啟（焦點在輸入框）按 Esc：只關搜尋、Flow 仍開、stack 不變、焦點回 🔍', q['boxHidden'] and q['open'] == 'false' and ev("flowLayerVisible()") is True and types() == 'flow' and q['btnFocus'], (q, types()))
click_btn(); typeq(A)
ev("document.querySelector('#flowQList .flow-q-item').focus(); true")
key('Escape', 'Escape', 27)
check('FQ-7 焦點在結果按鈕時 Esc：同樣只關搜尋', qs()['boxHidden'] and ev("flowLayerVisible()") is True, qs())
ev("document.getElementById('flowQBtn').blur(); document.body.focus(); true")
key('Escape', 'Escape', 27)
check('FQ-7 搜尋未開啟時 Esc：維持既有行為，關閉 Flow → 三張卡', ev("flowLayerVisible()") is False and st()['stack'] == [], types())

# ── FQ-8 重繪／鍵盤 resize 保留 query
enter('tools')
click_btn(); typeq(pre)
items0 = qs()['items']
ev("renderFlow(); true"); wait_ms(250)
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 500, 'deviceScaleFactor': 2, 'mobile': True}); wait_ms(300)
ev("window.dispatchEvent(new Event('resize')); true"); wait_ms(300)
q = qs()
check('FQ-8 renderFlow 重繪＋鍵盤式高度縮小 resize：搜尋仍開、query 與結果保留', not q['boxHidden'] and q['q'] == pre and q['items'] == items0, q)
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}); wait_ms(300)

# ── FQ-9 版面
for w, h, mob in ((390, 844, True), (844, 390, True), (1280, 800, False)):
    cdp('Emulation.setDeviceMetricsOverride', {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': mob}); wait_ms(300)
    ov = ev("({doc:document.documentElement.scrollWidth-document.documentElement.clientWidth, layer:(()=>{const l=document.getElementById('flowLayer'); return l.scrollWidth-l.clientWidth})()})")
    check('FQ-9 %dx%d：搜尋開啟時無水平溢出' % (w, h), ov['doc'] <= 0 and ov['layer'] <= 0, ov)
ev("document.body.classList.add('gs-ckm'); true"); wait_ms(200)
check('FQ-9 鍵盤（gs-ckm）：無水平溢出', ev("document.documentElement.scrollWidth-document.documentElement.clientWidth") <= 0)
ev("document.body.classList.remove('gs-ckm'); true")
cdp('Emulation.clearDeviceMetricsOverride')
back()

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'), (e['params']['exceptionDetails'].get('exception', {}) or {}).get('description', '')[:200])
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
