"""Phase 5 CP4：Tools 三張功能卡＋source-aware Flow layer＋Active Flow 橫向 ETF 選擇器。

PHASE5_PLAN §3、§3.4、§8.3；測試 TC-1～8、RT-T1～T3、RF-1～9、FS-1～6。
Codex 補充前提：RF-2 用真的有 Flow 資料、且 Detail 入口按鈕實際可見的 ETF；
RF-8 用合法 ETF 走 Router（不竄改 treemap 資料），並驗紅綠方塊仍在。
執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
"""
import sys, json
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0

ev("clearInterval(_pollTimer); window.__routerManualTimers = true; window.__routerDeferTraversal = false; true")
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if(_flowData||Date.now()-t>20000){clearInterval(i);r(true)}},100)})", True)

def st(): return json.loads(ev("JSON.stringify(Router.state())"))
def types(): return ev("Router.state().stack.map(l=>l.t).join()")
def hlen(): return ev("history.length")
def tc(): return ev("__routerTraversalCount")
def back(ms=400): ev("history.back(); true"); wait_ms(ms)
def fwd(ms=400): ev("history.forward(); true"); wait_ms(ms)
def flow_on(): return ev("flowLayerVisible() && !document.getElementById('flowLayer').hidden") is True
def page_on(pid): return ev("document.getElementById('%s').classList.contains('active')" % pid) is True
def esc(): ev("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); true"); wait_ms(350)
def cells(): return ev("document.querySelectorAll('#treemap .tm-cell').length") or 0
def home():
    ev("Router.toBase({base:'home'}); true"); wait_ms(300)

# 有 flow 金額資料、且在 ETFS 內（Detail 持股分頁會出現「查看完整持股異動」）的主動式 ETF
FC = ev("Object.keys(_flowData.etfs).filter(k=>(_flowData.etfs[k].flow||[]).length>0 && ETFS.some(e=>e.code===k))")
check('setup: active ETFs with flow rows exist', isinstance(FC, list) and len(FC) >= 2, FC)
A, B = FC[0], FC[1]
ALL = ev("Object.keys(_flowData.etfs).sort()")
LAST = ALL[-1]


# CP6b FIX-2：push 防線。forward entry 會被截斷，history.length 不能當證據 → 改計 history.pushState 呼叫次數，
# 並比對 push 後的 history.state 與 Router.state()（同一個 top layer）。
HSPY = """(()=>{ window.__hc = {push:0, rep:0};
  if (!window.__hspy) { window.__hspy = 1;
    const P = history.pushState, Rp = history.replaceState;
    history.pushState = function () { window.__hc.push++; return P.apply(history, arguments); };
    history.replaceState = function () { window.__hc.rep++; return Rp.apply(history, arguments); }; }
  return true; })()"""
def push_ok(t, extra=None):
    """恰好一次 pushState；history.state 與 Router.state() 一致且頂層型別為 t。"""
    r = ev("""(()=>{const hs=history.state, rs=Router.state(); const top=hs&&hs.stack&&hs.stack[hs.stack.length-1];
      const sk = x => JSON.stringify({b:x.base, s:x.stack.map(l=>[l.t, l.id, l.code||null, l.key||null])});
      // 比對結構（base、各層型別／id／代碼）；ui 不比——Flow 層的預設選取只 setUi 進記憶體、刻意不寫 history（§3.4.3）
      return {push:window.__hc.push, same: !!hs && sk(hs)===sk(rs), topT: top&&top.t, topId: top&&(top.id_||top.id), topCode: top&&top.code, n: hs&&hs.stack.length}})()""")
    return r if isinstance(r, dict) else {'push': -1, 'same': False, 'topT': None, 'topId': None, 'topCode': None, 'n': -1, 'err': r}   # history.state 異常時判 FAIL、不中斷


def click_at(sel):
    """在 sel 元素的可見中心以 elementFromPoint 取得實際命中元素並 click；回傳命中元素描述。"""
    return ev("""(()=>{const el=document.querySelector(%s); if(!el) return null; el.scrollIntoView({block:'center'}); const r=el.getBoundingClientRect();
      const sb=(document.querySelector('.rank-sticky')||{getBoundingClientRect:()=>({bottom:0})}).getBoundingClientRect().bottom;
      const y=(Math.max(r.top, sb)+r.bottom)/2; const hit=document.elementFromPoint(r.left+r.width/2, y); if(!hit) return null; hit.click();
      return hit.className||hit.tagName})()""" % json.dumps(sel))

# ════════ TC：三張功能卡 ════════
home()
h0 = hlen()
ev("switchPage('tools'); true"); wait_ms(250)
cards = ev("""[...document.querySelectorAll('#page-tools .tool-card')].map(b=>({tag:b.tagName, h:b.getBoundingClientRect().height,
  t:b.querySelector('b').textContent, d:b.querySelector('.tc-text > span').textContent, ic:!!b.querySelector('.tc-ic'), ar:(b.querySelector('.tc-arrow')||{}).textContent}))""")
check('TC-1 恰好 3 張卡、順序與 PO 文案', [c['t'] for c in cards] == ['成交量排行', '配息日曆', '主動式 ETF 持股異動']
      and [c['d'] for c in cards] == ['查看 ETF 成交量排行', '查看近期 ETF 除息與配息日期', '看基金最近加碼、減碼哪些持股']
      and not any('看今天' in c['d'] for c in cards), cards)   # D5／D6：舊文案「看今天哪些 ETF 成交最活躍」復活即 FAIL
check('TC-1 整張卡是 button、icon＋›、高度 ≥ 72px', all(c['tag'] == 'BUTTON' and c['ic'] and c['ar'] == '›' and c['h'] >= 72 for c in cards), cards)
check('TC-1 無 YouTube／計算機／更多', ev("""(()=>{const t=document.getElementById('page-tools').innerText; return !/YouTube|計算機|更多/.test(t) && document.querySelectorAll('#page-tools button').length===3})()""") is True)
check('TC-1 底部導覽進工具：history.length 不變、stack []', hlen() == h0 and st()['base'] == 'tools' and st()['stack'] == [])

for cid, page, tool in (('toolRank', 'page-rank', 'rank'), ('toolDiv', 'page-div', 'div')):
    ev("switchPage('tools'); true"); wait_ms(200)
    L = hlen()
    ev(HSPY)
    ev("(function(){ const b=document.getElementById('%s'); b.querySelector('.tc-text > span').click(); return true; })()" % cid); wait_ms(300)
    n = 'TC-2' if tool == 'rank' else 'TC-3'
    pk = push_ok('tool')
    check('%s 點卡片說明文字也能進入 %s、stack [tool %s]' % (n, page, tool), page_on(page) and types() == 'tool' and st()['stack'][0]['id'] == tool and hlen() <= L + 1, (types(), hlen(), L))
    check('%s push 防線：history.pushState 恰好 1 次、history.state 與 Router.state() 結構一致、頂層為 tool %s' % (n, tool),
          pk['push'] == 1 and pk['same'] and pk['topT'] == 'tool' and pk['n'] == 1 and ev("(history.state && history.state.stack[0] || {}).id") == tool, pk)
    if tool == 'div':
        check('TC-3 配息日曆有內容、無 B-1 元素', ev("document.getElementById('calList').children.length>0 && !document.getElementById('sharesIn')") is True)
    back()
    check('%s Back → 三張卡、stack []' % n, page_on('page-tools') and st()['stack'] == [])
    fwd()
    check('%s Forward → 再進 %s' % (n, page), page_on(page) and types() == 'tool')
    back()

# TC-4 持股異動卡
ev("switchPage('tools'); true"); wait_ms(200)
L = hlen(); t0 = tc()
ev(HSPY)
ev("document.getElementById('toolFlow').click(); true"); wait_ms(400)
pk = push_ok('flow')
check('TC-4 持股異動卡：base 仍 tools、stack [flow]、traversal 0', st()['base'] == 'tools' and types() == 'flow' and tc() == t0 and hlen() <= L + 1, (st(), hlen(), L))
check('TC-4 push 防線：history.pushState 恰好 1 次、history.state 與 Router.state() 結構一致、頂層為 flow', pk['push'] == 1 and pk['same'] and pk['topT'] == 'flow' and pk['n'] == 1, pk)
check('TC-4 Flow 層可見、紅綠方塊有內容、底部導覽亮「工具」', flow_on() and cells() > 0 and ev("document.getElementById('nav-tools').classList.contains('active')") is True, cells())
back()
check('TC-4 Back → 三張卡、stack []、Flow 層隱藏', page_on('page-tools') and st()['stack'] == [] and not flow_on() and ev("document.getElementById('catFlowHost').contains(document.getElementById('page-check'))") is True)

# TC-5 底部導覽不累積
ev("switchPage('tools'); true"); wait_ms(200)
href = ev("location.href")
L = hlen(); t0 = tc()
ev("switchPage('today'); true"); wait_ms(300)
check('TC-5 卡片列表 → 底部導覽：traversal 0、history.length 不變', tc() == t0 and hlen() == L and page_on('page-today'))
ev("switchPage('tools'); true"); wait_ms(200)
ev("document.getElementById('toolRank').click(); true"); wait_ms(300)
L = hlen(); t0 = tc()
ev("switchPage('today'); true"); wait_ms(400)
check('TC-5 子頁 → 底部導覽：traversal 1、history.length 不變、未離站', tc() == t0 + 1 and hlen() == L and ev("location.href") == href and st()['stack'] == [] and page_on('page-today'), (tc() - t0, hlen(), L))
ev("switchPage('tools'); true"); wait_ms(200)
for i in range(3):
    ev("document.getElementById('toolRank').click(); true"); wait_ms(250)
    back(300)
check('TC-5 「卡片 → 子頁 → Back」×3 後仍在卡片列表、stack []（Back 深度不增加）', page_on('page-tools') and st()['stack'] == [])

# TC-6 排行定位（只定位不過濾）
ev("document.getElementById('toolRank').click(); true"); wait_ms(300)
n_rows = ev("document.querySelectorAll('#page-rank .rank-row').length")
check('TC-6 先展開 🔍（PO Change #2：預設收起），輸入框可見', ev("(()=>{ if(document.getElementById('rankFindBtn').getAttribute('aria-expanded')!=='true') document.getElementById('rankFindBtn').click(); const i=document.getElementById('rankFind'); return i.offsetParent!==null && i.getBoundingClientRect().height>0; })()") is True)
ev("{const f=document.getElementById('rankFind'); f.value='0050'; f.dispatchEvent(new Event('input'));} true"); wait_ms(250)
check('TC-6 rankFind 只定位不過濾、訊息含 0050', ev("document.querySelectorAll('#page-rank .rank-row').length") == n_rows and '0050' in (ev("document.getElementById('rankFindMsg').innerText") or ''), n_rows)

# TC-7 子頁 → Detail → 返回（排行：捲動、rankFind 保留）
ev("[...document.querySelectorAll('#page-rank .rank-row')][12].scrollIntoView({block:'center'}); true"); wait_ms(300)
y0 = ev("window.scrollY")
code_mid = ev("[...document.querySelectorAll('#page-rank .rank-row')][12].dataset.code")
# CP6c：改為真的點排行列（原本以程式呼叫 openDetail）。點列的左側（名次／代碼），避開「持股異動 ›」
ev(HSPY)
ev("""(()=>{const row=[...document.querySelectorAll('#page-rank .rank-row')][12]; const r=row.querySelector('.rank-code').getBoundingClientRect();
  document.elementFromPoint(r.left+r.width/2, r.top+r.height/2).click(); return true})()"""); wait_ms(350)
check('TC-7 真實點擊排行列 → Detail：stack [tool, detail]、該列 ETF、pushState 1 次', types() == 'tool,detail' and st()['stack'][-1]['code'] == code_mid and ev("window.__hc.push") == 1, (types(), code_mid))
back()
check('TC-7 Back → 仍在排行、捲動不變、rankFind 值與定位保留', types() == 'tool' and page_on('page-rank') and abs(ev("window.scrollY") - y0) <= 2
      and ev("document.getElementById('rankFind').value") == '0050' and ev("!!document.querySelector('#page-rank .rank-row.found')") is True, (ev("window.scrollY"), y0))
back()
check('TC-7 再 Back → 三張卡', page_on('page-tools') and st()['stack'] == [])
ev("document.getElementById('toolDiv').click(); true"); wait_ms(300)
dcode = ev("(document.querySelector('#calList .cal-item')||{dataset:{}}).dataset.code")
check('TC-7 前提：配息日曆有列', bool(dcode), dcode)
ev(HSPY)
click_at('#calList .cal-item'); wait_ms(350)
check('TC-7 真實點擊配息日曆列 → 該檔 Detail、pushState 1 次', types() == 'tool,detail' and st()['stack'][-1]['code'] == dcode and ev("window.__hc.push") == 1, (types(), dcode))
back()
check('TC-7 配息日曆 → Detail → Back：回配息日曆', types() == 'tool' and page_on('page-div'))
back()

# TC-8 相容入口
ev("switchPage('tools'); true"); wait_ms(200)
ev("switchPage('div'); true"); wait_ms(250)
check('TC-8 switchPage(div) 與卡片相同', page_on('page-div') and types() == 'tool')
back()
ev("switchPage('check'); true"); wait_ms(350)
check('TC-8 switchPage(check) 與持股異動卡相同（Flow 層、base tools）', st()['base'] == 'tools' and types() == 'flow' and flow_on())
back()

# ════════ RT-T ════════
check('RT-T1 Router 公開 API 未新增', sorted(ev("Object.keys(Router)")) == sorted(['init', 'normalize', 'state', 'navigate', 'openDetail', 'closeDetail', 'closeFolder', 'openFolder', 'setFolderView', 'toBase', 'openFlow', 'updateUi', 'setUi', 'onMarketUpdate', 'onDataError']), ev("Object.keys(Router)"))
check('RT-T1 Tools 卡片頁＝page-tools', page_on('page-tools') and st()['base'] == 'tools')

# (a) Tools → Flow
t0 = tc(); ev("document.getElementById('toolFlow').click(); true"); wait_ms(350)
ra = (tc() - t0, types(), st()['base']); back()
# (b) 排行 → Flow
ev("document.getElementById('toolRank').click(); true"); wait_ms(300)
t0 = tc(); ev("openFlow(%s); true" % json.dumps(A)); wait_ms(350)
rb = (tc() - t0, types(), st()['base']); back(); rb_back = (types(), page_on('page-rank'))
# (c) 排行 → Detail → 完整持股異動
ev("openDetail(%s); detailTab('holdings'); true" % json.dumps(A)); wait_ms(350)
t0 = tc(); ev("document.querySelector('.gs-flow-btn').click(); true"); wait_ms(350)
rc = (tc() - t0, types(), st()['base']); back(); rc_back = types(); back(); back()
check('RT-T2 (a) Tools [] → [flow]、traversal 0、base 不變', ra == (0, 'flow', 'tools'), ra)
check('RT-T2 (b) 排行 [tool] → [tool, flow]、traversal 0；Back 回排行', rb == (0, 'tool,flow', 'tools') and rb_back == ('tool', True), (rb, rb_back))
check('RT-T2 (c) Detail [tool, detail] → [tool, detail, flow]、traversal 0；Back 回 Detail', rc == (0, 'tool,detail,flow', 'tools') and rc_back == 'tool,detail', (rc, rc_back))
for base in ('home', 'watch', 'cat'):
    ev("Router.toBase({base:%s}); true" % json.dumps(base)); wait_ms(300)
    ev("openDetail(%s); true" % json.dumps(A)); wait_ms(300)
    t0 = tc(); ev("openFlow(%s); true" % json.dumps(A)); wait_ms(350)
    ok = (tc() == t0 and types() == 'detail,flow' and st()['base'] == base)
    back(); ok2 = types() == 'detail' and st()['base'] == base
    check('RT-T2 base %s：Detail → Flow push 一層、Back 回 Detail' % base, ok and ok2, types())
    back()
home()
ev("openFlow(%s); true" % json.dumps(A)); wait_ms(350)
L = hlen(); fid = st()['stack'][-1]['id']
ev("openFlow(%s); true" % json.dumps(A)); wait_ms(250)
check('RT-T2 頂層已是 flow：openFlow(同檔) 不動', hlen() == L and st()['stack'][-1]['id'] == fid and types() == 'flow')
ev("openFlow(%s); true" % json.dumps(B)); wait_ms(300)
check('RT-T2 頂層已是 flow：openFlow(他檔) replace、history.length 不變', hlen() == L and types() == 'flow' and st()['stack'][-1]['ui']['code'] == B and ev("_flowSel") == B)
back()
# RT-T3（R1～R8）：由 router_test.py 64 項覆蓋（RT-14～21 改以 openFolder 驅動 traversal）

# ════════ RF ════════
# RF-1 Tools 往返不累積
ev("switchPage('tools'); true"); wait_ms(250)
ok = True
for i in range(3):
    ev("document.getElementById('toolFlow').click(); true"); wait_ms(300)
    ok = ok and types() == 'flow' and flow_on()
    back(300)
    ok = ok and st()['stack'] == [] and page_on('page-tools') and not flow_on()
check('RF-1 Tools → Flow → Back ×3：每次回三張卡、stack []', ok)

# RF-2 Detail → Flow → Back 保留 ETF、分頁、捲動、輸入（A 有 flow 資料，入口按鈕可見）
home()
ev("openDetail(%s); true" % json.dumps(A)); wait_ms(350)
ev("detailTab('dividend'); true"); wait_ms(150)
ev("{const i=document.getElementById('dtSharesIn'); i.value='7'; i.dispatchEvent(new Event('input'));} true"); wait_ms(120)
ev("detailTab('holdings'); true"); wait_ms(200)
btn_vis = ev("(()=>{const b=document.querySelector('.gs-flow-btn'); if(!b) return false; const r=b.getBoundingClientRect(); return r.height>0 && r.width>0 && !b.closest('[hidden]')})()")
check('RF-2 前提：%s 的「查看完整持股異動」入口可見' % A, btn_vis is True)
ev("document.getElementById('gsPanel').scrollTop = 120; document.getElementById('gsPanel').dispatchEvent(new Event('scroll')); true"); wait_ms(300)
p0 = ev("document.getElementById('gsPanel').scrollTop")
calc0 = ev("document.getElementById('dtCalcOut').innerText")
ev("document.querySelector('.gs-flow-btn').click(); true"); wait_ms(400)
check('RF-2 Flow 層開在 Detail 上、選取＝%s' % A, types() == 'detail,flow' and flow_on() and ev("_flowSel") == A and ev("document.getElementById('flowSelName').textContent") == ev("_flowData.etfs[%s].name" % json.dumps(A)))
back()
rf2 = ev("({code:_curEtfCode, tab:_detailTab, top:document.getElementById('gsPanel').scrollTop, shares:document.getElementById('dtSharesIn').value, calc:document.getElementById('dtCalcOut').innerText, open:!document.getElementById('gsPanel').hidden})")
check('RF-2 Back → 原 Detail：同檔、持股分頁、捲動、輸入 7 張與試算保留', rf2['open'] and rf2['code'] == A and rf2['tab'] == 'holdings' and abs(rf2['top'] - p0) <= 2 and p0 > 0
      and rf2['shares'] == '7' and rf2['calc'] == calc0 and types() == 'detail', (rf2, p0, calc0))
back()

# RF-3 排行 → Flow → Back 保留來源狀態
ev("switchPage('rank'); true"); wait_ms(300)
check('RF-3 先展開 🔍，輸入框可見', ev("(()=>{ if(document.getElementById('rankFindBtn').getAttribute('aria-expanded')!=='true') document.getElementById('rankFindBtn').click(); const i=document.getElementById('rankFind'); return i.offsetParent!==null && i.getBoundingClientRect().height>0; })()") is True)
ev("{const f=document.getElementById('rankFind'); f.value='0056'; f.dispatchEvent(new Event('input'));} true"); wait_ms(250)
ev("window.scrollTo(0, 700); true"); wait_ms(300)
y0 = ev("window.scrollY")
rcode = ev("(document.querySelector('#page-rank .rank-row.has-flow')||{dataset:{}}).dataset.code")
ev("new Promise(r=>{let last=-1,same=0;const i=setInterval(()=>{const y=Math.round(scrollY); same=(y===last)?same+1:0; last=y; if(same>=3){clearInterval(i);r(y)}},120)})", True)   # 等 0056 定位的 smooth scroll 停下
ev("document.querySelector('#page-rank .rank-row.has-flow .rank-flow').scrollIntoView({block:'center', behavior:'instant'}); true"); wait_ms(300)
y0 = ev("window.scrollY")
ev(HSPY)
ev("""(()=>{const b=document.querySelector('#page-rank .rank-row.has-flow .rank-flow'); const r=b.getBoundingClientRect(); const h=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); if(h) h.click(); return true})()"""); wait_ms(400)
check('RF-3 排行「持股異動 ›」→ Flow 層、stack [tool, flow]、選取＝該列 ETF、未開 Detail、pushState 1 次（CP6c：row → Detail，按鈕 → Flow）',
      types() == 'tool,flow' and flow_on() and ev("_flowSel") == rcode and ev("document.getElementById('gsPanel').hidden") is True and ev("window.__hc.push") == 1, (types(), rcode, ev("window.__hc.push")))
check('RF-9 開 Flow 不捲動來源頁', abs(ev("window.scrollY") - y0) <= 2, (ev("window.scrollY"), y0))
back()
check('RF-3 Back → 原排行：捲動、rankFind 值、定位標示保留', page_on('page-rank') and types() == 'tool' and abs(ev("window.scrollY") - y0) <= 2
      and ev("document.getElementById('rankFind').value") == '0056' and ev("!!document.querySelector('#page-rank .rank-row.found')") is True, (ev("window.scrollY"), y0))
ev("{const f=document.getElementById('rankFind'); f.value=''; f.dispatchEvent(new Event('input'));} true")
back()

# RF-4 換 ETF 不寫 history、不污染 folder（分類 base 下開資料夾 → Detail → Flow）
ev("Router.toBase({base:'cat'}); true"); wait_ms(300)
ev("Router.openFolder('active'); true"); wait_ms(700)
fold0 = json.dumps(st()['stack'][0]['ui'], sort_keys=True)
ev("openDetail(%s); true" % json.dumps(A)); wait_ms(350)
ev("openFlow(%s); true" % json.dumps(A)); wait_ms(350)
L = hlen(); n0 = len(st()['stack'])
ev("window.scrollTo(0,0); window.__sy = 0; true")
ev("document.querySelector('#flowChips .flow-chip[data-code=%s]').click(); true" % json.dumps(B)); wait_ms(300)
s4 = st()
check('RF-4 換 ETF：history.length、stack 長度不變，flow.ui.code 更新', hlen() == L and len(s4['stack']) == n0 and s4['stack'][-1]['ui']['code'] == B and ev("_flowSel") == B, s4)
check('RF-4 folder.ui 完全不變（不污染）', json.dumps(s4['stack'][0]['ui'], sort_keys=True) == fold0, (s4['stack'][0]['ui'], fold0))

# RF-5 Back／Forward／refresh
back()
check('RF-5 Back → 原 Detail', types() == 'folder,detail' and not flow_on())
fwd()
check('RF-5 Forward → Flow 顯示換過的 ETF（%s）' % B, types() == 'folder,detail,flow' and flow_on() and ev("_flowSel") == B and ev("document.querySelector('#flowChips .flow-chip.active').dataset.code") == B)
cdp('Page.reload'); time.sleep(1.5)
ev("new Promise(r=>{const t=Date.now();const i=setInterval(()=>{if((ETFS.length>0&&_flowData&&flowLayerVisible())||Date.now()-t>20000){clearInterval(i);r(true)}},150)})", True); wait_ms(400)
ev("clearInterval(_pollTimer); true")
check('RF-5 refresh → Flow 層還原、選取＝%s、來源 Detail 也還原' % B, flow_on() and ev("_flowSel") == B and types() == 'folder,detail,flow'
      and ev("!document.getElementById('gsPanel').hidden && _curEtfCode") == A, (types(), ev("_flowSel")))
back()
check('RF-5 refresh 後 Back → Detail（Flow 關閉）', types() == 'folder,detail' and not flow_on())
back(); back()

# RF-6 底部導覽清理 Flow 層
cases = []
for label, setup in (('[flow]', "switchPage('tools')|switchPage('check')"),
                     ('[tool rank, flow]', "switchPage('rank')|openFlow(%s)" % json.dumps(A)),
                     ('[detail, flow]', "Router.toBase({base:'watch'})|openDetail(%s)|openFlow(%s)" % (json.dumps(A), json.dumps(A)))):
    for stepjs in setup.split('|'):
        ev(stepjs + "; true"); wait_ms(350)
    pre = types()
    L = hlen(); t0 = tc(); href = ev("location.href")
    ev("switchPage('today'); true"); wait_ms(500)
    ok = (tc() == t0 + 1 and hlen() == L and ev("location.href") == href and not flow_on()
          and ev("document.getElementById('gsPanel').hidden") is True and st()['stack'] == [] and st()['base'] == 'home' and page_on('page-today'))
    check('RF-6 %s（實際 %s）→ 底部導覽首頁：traversal 1、history.length 不變、未離站、Flow 與 Detail 都清掉' % (label, pre), ok, (pre, tc() - t0, hlen(), L, types()))

# RF-7 分類原生 flow 不變
ev("Router.toBase({base:'cat'}); true"); wait_ms(300)
ev("Router.openFolder('active'); true"); wait_ms(700)
L = hlen()
ev("Router.setFolderView('flow'); true"); wait_ms(400)
check('RF-7 原生：[folder(active, flow)]、在 #catFlowHost 顯示、Flow 層不開', types() == 'folder' and st()['stack'][0]['view'] == 'flow' and ev("Category.isFlowVisible()") is True
      and not flow_on() and ev("document.getElementById('catFlowHost').contains(document.getElementById('page-check')) && !document.getElementById('catFlowHost').hidden") is True and hlen() == L)
ev("document.querySelector('#flowChips .flow-chip[data-code=%s]').click(); true" % json.dumps(A)); wait_ms(300)
check('RF-7 原生換 ETF 仍寫 folder.ui.code、不新增 history', st()['stack'][0]['ui'].get('code') == A and hlen() == L and cells() > 0)
ev("Router.setFolderView('list'); true"); wait_ms(300)
back(); home()

# RF-8 疊放與 Esc（Flow 上開合法 ETF 的 Detail；不竄改 treemap 資料）
ev("switchPage('tools'); true"); wait_ms(250)
ev("document.getElementById('toolFlow').click(); true"); wait_ms(400)
c0 = cells()
ev("gsPick('0050'); true"); wait_ms(400)
z = ev("({f:+getComputedStyle(document.getElementById('flowLayer')).zIndex, d:+getComputedStyle(document.getElementById('gsPanel')).zIndex})")
check('RF-8 Flow 上開 Detail（0050）：stack [flow, detail]、Detail 疊在 Flow 之上', types() == 'flow,detail' and z['d'] > z['f'] and flow_on(), (types(), z))
esc()
check('RF-8 Esc 只關 Detail → 回 Flow；紅綠方塊仍在', types() == 'flow' and flow_on() and ev("document.getElementById('gsPanel').hidden") is True and cells() == c0 and c0 > 0, (types(), cells(), c0))
esc()
check('RF-8 再 Esc 關 Flow → 回三張卡', st()['stack'] == [] and not flow_on() and page_on('page-tools'))
ev("gsClear(); true")

# RF-9 Flow 開／關／換 ETF 不呼叫 window.scrollTo
ev("switchPage('rank'); true"); wait_ms(300)
ev("window.scrollTo(0, 500); window.__st = 0; window.__origST = window.scrollTo; window.scrollTo = function(){ window.__st++; return window.__origST.apply(window, arguments); }; true"); wait_ms(200)
y0 = ev("window.scrollY")
ev("openFlow(%s); true" % json.dumps(A)); wait_ms(350)
ev("document.querySelector('#flowChips .flow-chip[data-code=%s]').click(); true" % json.dumps(B)); wait_ms(300)
back()
check('RF-9 Flow 開／換 ETF／關：window.scrollTo 呼叫 0 次、來源頁 scrollY 不變', ev("window.__st") == 0 and abs(ev("window.scrollY") - y0) <= 2, (ev("window.__st"), ev("window.scrollY"), y0))
ev("window.scrollTo = window.__origST; true")
back()

# ════════ RF-10／RF-11（CP4 fix）：Detail → Flow → 第二個 Detail → Back → Back，第二個 Detail 不得污染第一個 ════════
def dstate():
    return ev("({code:_curEtfCode, tab:_detailTab, top:document.getElementById('gsPanel').scrollTop, shares:document.getElementById('dtSharesIn').value, open:!document.getElementById('gsPanel').hidden})")

def prep_first(code):
    """Detail A：張數 7、持股分頁、面板捲到中段，經可見的「查看完整持股異動」進 Flow。回傳 A 的狀態。"""
    home()
    ev("openDetail(%s); true" % json.dumps(code)); wait_ms(350)
    ev("detailTab('dividend'); true"); wait_ms(150)
    ev("{const i=document.getElementById('dtSharesIn'); i.value='7'; i.dispatchEvent(new Event('input'));} true"); wait_ms(120)
    ev("detailTab('holdings'); true"); wait_ms(200)
    ev("document.getElementById('gsPanel').scrollTop = 120; document.getElementById('gsPanel').dispatchEvent(new Event('scroll')); true"); wait_ms(300)
    a = dstate()
    vis = ev("(()=>{const b=document.querySelector('.gs-flow-btn'); if(!b) return false; const r=b.getBoundingClientRect(); return r.height>0 && r.width>0})()")
    ev("document.querySelector('.gs-flow-btn').click(); true"); wait_ms(400)
    return a, vis

def second_detail(code):
    """Flow 上以全站搜尋開第二個 Detail，改張數 2、切到績效分頁、捲回頂端。"""
    ev("gsPick(%s); true" % json.dumps(code)); wait_ms(400)
    ev("detailTab('dividend'); true"); wait_ms(150)
    ev("{const i=document.getElementById('dtSharesIn'); i.value='2'; i.dispatchEvent(new Event('input'));} true"); wait_ms(120)
    ev("detailTab('perf'); true"); wait_ms(150)
    ev("document.getElementById('gsPanel').scrollTop = 0; document.getElementById('gsPanel').dispatchEvent(new Event('scroll')); true"); wait_ms(300)
    return dstate()

for tag, second in (('RF-10 A→Flow→B（0056）', '0056'), ('RF-11 A→Flow→同一檔 A', A)):
    a, vis = prep_first(A)
    check('%s 前提：%s 入口可見、A 狀態（7 張、持股、捲動 >0）' % (tag, A), vis is True and a['shares'] == '7' and a['tab'] == 'holdings' and a['top'] > 0, a)
    fl = ev("Object.keys(_flowData.etfs).length"); c0 = cells()
    b = second_detail(second)
    check('%s 第二個 Detail：stack [detail, flow, detail]、B 為 %s、2 張、績效分頁' % (tag, second), types() == 'detail,flow,detail' and b['code'] == second and b['shares'] == '2' and b['tab'] == 'perf', (types(), b))
    ids = ev("Router.state().stack.filter(l=>l.t==='detail').map(l=>l.id)")
    check('%s 兩個 detail 層是不同層（id 不同）' % tag, isinstance(ids, list) and len(ids) == 2 and ids[0] != ids[1], ids)
    check('%s 第一個 detail 層的 ui 未被第二個寫入' % tag, ev("JSON.stringify(Router.state().stack[0].ui.shares)") == '"7"' and ev("Router.state().stack[0].ui.tab") == 'holdings', ev("JSON.stringify(Router.state().stack[0].ui)"))
    back()
    check('%s Back ①：回 Flow（[detail, flow]），紅綠方塊仍在' % tag, types() == 'detail,flow' and flow_on() and cells() == c0 and c0 > 0, (types(), cells(), c0))
    back()
    r = dstate()
    check('%s Back ②：回原 Detail A——ETF、7 張、持股分頁、捲動都是 A 的' % tag, r['open'] and r['code'] == A and r['shares'] == '7' and r['tab'] == 'holdings' and abs(r['top'] - a['top']) <= 2 and types() == 'detail', (r, a))
    fwd()
    check('%s Forward → Flow' % tag, types() == 'detail,flow' and flow_on())
    fwd()
    r2 = dstate()
    check('%s 再 Forward → 第二個 Detail 還原為它自己的狀態（%s、2 張、績效）' % (tag, second), types() == 'detail,flow,detail' and r2['code'] == second and r2['shares'] == '2' and r2['tab'] == 'perf', r2)
    back(); back(); back()
    ev("gsClear(); true")

# ════════ FS：橫向選擇器（390×844 直向） ════════
cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
ev("switchPage('tools'); true"); wait_ms(300)
ev("document.getElementById('toolFlow').click(); true"); wait_ms(500)
fs1 = ev("""(()=>{const b=document.getElementById('flowChips'); const cs=[...b.querySelectorAll('.flow-chip')];
  return {n:cs.length, rows:new Set(cs.map(c=>c.offsetTop)).size, sw:b.scrollWidth, cw:b.clientWidth, ox:getComputedStyle(b).overflowX,
          codes:cs.map(c=>c.dataset.code), minH:Math.min(...cs.map(c=>c.getBoundingClientRect().height)), fs:Math.min(...cs.map(c=>parseFloat(getComputedStyle(c).fontSize)))}})()""")
check('FS-1 單列、可橫向捲動、全部主動式 ETF 都在（未刪減）', fs1['rows'] == 1 and fs1['sw'] > fs1['cw'] and fs1['ox'] == 'auto' and fs1['codes'] == ALL, fs1)
check('FS-1 選擇器 touch target ≥ 44px、字級 ≥ 16px', fs1['minH'] >= 44 and fs1['fs'] >= 16, fs1)
L = hlen()
ev("document.querySelector('#flowChips .flow-chip[data-code=%s]').click(); true" % json.dumps(B)); wait_ms(350)
fs2 = ev("""(()=>{const a=[...document.querySelectorAll('#flowChips .flow-chip.active')]; return {n:a.length, code:a[0]&&a[0].dataset.code, pressed:a[0]&&a[0].getAttribute('aria-pressed'),
  name:document.getElementById('flowSelName').textContent, bw:getComputedStyle(a[0]).borderTopWidth}})()""")
check('FS-2 點選即切換：只有一顆 active、aria-pressed、完整名稱、history.length 不變', fs2['n'] == 1 and fs2['code'] == B and fs2['pressed'] == 'true'
      and fs2['name'] == ev("_flowData.etfs[%s].name" % json.dumps(B)) and hlen() == L, fs2)
check('FS-2 選取高亮明顯（粗框 2px）', fs2['bw'] == '2px', fs2['bw'])
check('FS-2 加碼／減碼與 treemap 重畫為該 ETF', ev("document.getElementById('flowBuy').textContent") != '–' and cells() > 0)
back()
home()
ev("openFlow(%s); true" % json.dumps(LAST)); wait_ms(450)
y0 = ev("window.scrollY")
fs3 = ev("""(()=>{const b=document.getElementById('flowChips'); const a=b.querySelector('.flow-chip.active'); const br=b.getBoundingClientRect(), ar=a.getBoundingClientRect();
  return {code:a.dataset.code, left:ar.left-br.left, right:br.right-ar.right, sl:b.scrollLeft}})()""")
check('FS-3 帶入清單最後一檔（%s）：選取項完整落在選擇列可見範圍、選擇列已捲動' % LAST, fs3['code'] == LAST and fs3['left'] >= 0 and fs3['right'] >= 0 and fs3['sl'] > 0, fs3)
check('FS-3 不捲動整頁', ev("window.scrollY") == y0 and ev("document.getElementById('flowLayer').scrollTop") == 0)
tm_new = ev("document.getElementById('treemap').getBoundingClientRect().top")
ev("document.getElementById('flowChips').style.cssText='display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:0 14px 8px;overflow:visible;-webkit-mask-image:none;mask-image:none'; true"); wait_ms(100)
tm_old = ev("document.getElementById('treemap').getBoundingClientRect().top")
ev("document.getElementById('flowChips').style.cssText=''; true"); wait_ms(100)
check('FS-4 第一屏：treemap 頂端比舊多列 chips 更高，且在 844px 第一屏內', tm_new < tm_old and tm_new < 844, (tm_new, tm_old))
back()
# FS-5 同一份 Flow DOM
node_id = ev("(window.__fnode = document.getElementById('page-check'), true)")
ev("switchPage('tools'); true"); wait_ms(250)
ev("document.getElementById('toolFlow').click(); true"); wait_ms(400)
in_layer = ev("document.getElementById('flowLayer').contains(window.__fnode) && document.querySelectorAll('#page-check').length === 1")
back()
in_host = ev("document.getElementById('catFlowHost').contains(window.__fnode) && document.querySelectorAll('#flowChips').length === 1")
check('FS-5 Tools／排行／Detail／原生共用同一個 flow 節點（Flow 層時在 #flowLayer，關閉後回 #catFlowHost）', in_layer is True and in_host is True, (in_layer, in_host))
# FS-6 保護功能：紅＝加碼、綠＝減碼；海外清單
ev("openFlow(%s); true" % json.dumps(A)); wait_ms(400)
col = ev("""(()=>{const c=[...document.querySelectorAll('#treemap .tm-cell')].map(x=>getComputedStyle(x).backgroundColor); return {buy:c.filter(b=>{const v=b.match(/\d+/g).map(Number); return v[0]>v[1]+80 && v[0]>v[2]+80}).length, sell:c.filter(b=>{const v=b.match(/\d+/g).map(Number); return v[1]>v[0]+80 && v[1]>v[2]+40}).length,
  bt:getComputedStyle(document.getElementById('flowBuy')).color, stc:getComputedStyle(document.getElementById('flowSell')).color}})()""")
check('FS-6 treemap 紅＝加碼、綠＝減碼；加碼金額紅、減碼金額綠', col['buy'] + col['sell'] > 0 and col['bt'] == 'rgb(244, 97, 97)' and col['stc'] == 'rgb(34, 197, 94)', col)
npc = ev("Object.keys(_flowData.etfs).find(k=>(_flowData.etfs[k].no_price||[]).length>0)")
if npc:
    ev("document.querySelector('#flowChips .flow-chip[data-code=%s]').click(); true" % json.dumps(npc)); wait_ms(300)
    check('FS-6 海外持股清單仍顯示（%s）' % npc, (ev("document.querySelectorAll('#flowForeign .np-row').length") or 0) > 0)
else:
    check('FS-6 海外持股清單（目前資料無海外異動，略過）', True)
back()
cdp('Emulation.clearDeviceMetricsOverride')

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'), (e['params']['exceptionDetails'].get('exception', {}) or {}).get('description', '')[:200])
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
