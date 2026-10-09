"""D4 配息日曆來源標籤＋Detail 金額來源文字。

執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
- 除息日來源（source）與金額來源（amount_source）分開：source=official 不等於金額官方
- 金額只有 amount_source 以 TWSE 開頭才標官方；MoneyDJ 等第三方、未知來源原樣顯示；manual 不宣稱核實
- Detail：第三方金額稱「參考金額」，不稱「公告金額」
"""
import sys, json, re
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0
ev("clearInterval(_pollTimer); true")

OFFICIAL_WORDS = ('官方公告', '核實', 'TWSE')
def expect(c):
    """獨立於前端的預期：回傳 (必含字串, 不得含字串)"""
    raw = c.get('amount_source') or ''
    keep = '（保留前值）' in raw
    a = raw.replace('（保留前值）', '')
    pre = '官方除息日｜' if c.get('source') == 'official' else ''
    must = []
    if a.startswith('TWSE'): must = [pre + '金額來源：' + a]
    elif a == 'FinMind（估算）': must = [pre + '金額：FinMind 估算']
    elif c.get('source') == 'manual' and a in ('', 'manual'): must = ['人工提供資料']
    elif c.get('source') == 'estimate' and not a: must = ['歷史平均估算']
    elif not a or a == c.get('source'): must = [pre + '金額來源未標示']
    else: must = [pre + '金額來源：' + a]
    if keep: must.append('（保留前值）')
    banned = [] if a.startswith('TWSE') else ['官方公告', '核實', '金額來源：TWSE']
    return must, banned

# ── 正式 calendar：逐筆比對 rendered 標籤
ev("Router.toBase({base:'home'}); true"); wait_ms(300)
cal = ev("CALENDAR.filter(c=>!c.iso_date || c.iso_date >= new Date().toLocaleDateString('sv-SE'))")
lbls = ev("[...document.querySelectorAll('#calList .cal-item')].map(x=>({code:x.dataset.code, lbl:(x.querySelector('.src-lbl')||{}).textContent||'', amt:(x.querySelector('.cal-amt')||{}).textContent||''}))")
check('正式日曆筆數與畫面一致（%d 筆）' % len(cal), len(cal) == len(lbls) and [c['code'] for c in cal] == [l['code'] for l in lbls], (len(cal), len(lbls)))
bad = []
for c, l in zip(cal, lbls):
    must, banned = expect(c)
    if c.get('amt') is None:
        if l['lbl']: bad.append((c['code'], 'amt null 卻有標籤', l['lbl']))
        continue
    if not l['lbl']: bad.append((c['code'], '留白')); continue
    if any(m not in l['lbl'] for m in must) or any(b in l['lbl'] for b in banned): bad.append((c['code'], l['lbl'], must, banned))
    if ('%.2f 元' % c['amt']) not in l['amt']: bad.append((c['code'], '金額被改', l['amt']))
check('正式日曆每筆都有正確來源標籤、金額未改', not bad, bad)
for code in ('00936', '00929', '0056'):
    row = [l for l in lbls if l['code'] == code]
    c = [x for x in cal if x['code'] == code]
    if not row or not c: print('   SKIP %s：正式日曆已無此筆' % code); continue
    print('   %s %s ｜ %s' % (code, row[0]['lbl'], row[0]['amt']))
    if c[0].get('amount_source') == 'MoneyDJ' and c[0].get('source') == 'official':
        check('%s：官方除息日｜金額來源：MoneyDJ，不稱官方金額' % code, '官方除息日｜金額來源：MoneyDJ' in row[0]['lbl'] and '官方公告' not in row[0]['lbl'], row[0])
est = [l for c, l in zip(cal, lbls) if c.get('source') == 'estimate']
check('估算 %d 筆全部「歷史平均估算」、無官方字樣' % len(est), all('歷史平均估算' in l['lbl'] and not any(w in l['lbl'] for w in OFFICIAL_WORDS) for l in est), est[:3])

# ── 合成：各種來源直接走 calSrcLabel，並實際畫一次確認 DOM 一致
CASES = [
    {'source': 'official', 'amount_source': 'TWSE'},
    {'source': 'official', 'amount_source': 'TWSE × FinMind 核實'},
    {'source': 'official', 'amount_source': 'TWSE（FinMind 差異 12%）'},
    {'source': 'official', 'amount_source': 'TWSE（保留前值）'},
    {'source': 'official', 'amount_source': 'MoneyDJ'},
    {'source': 'official', 'amount_source': 'MoneyDJ（保留前值）'},
    {'source': 'official', 'amount_source': 'FinMind（估算）'},
    {'source': 'official', 'amount_source': 'official'},
    {'source': 'official', 'amount_source': None},
    {'source': 'official', 'amount_source': 'Gavin 人工確認'},
    {'source': 'manual', 'amount_source': 'manual'},
    {'source': 'estimate', 'amount_source': None},
    {'source': 'official', 'amount_source': '某新來源<b>x</b>'},
]
for cs in CASES:
    c = dict(cs, code='ZZ1', amt=1.23)
    got = ev("calSrcLabel(%s).text" % json.dumps(c, ensure_ascii=False))
    must, banned = expect(c)
    check('合成 %s／%s → %s' % (cs['source'], cs['amount_source'], got), isinstance(got, str) and got.strip() and all(m in got for m in must) and not any(b in got for b in banned), (got, must, banned))
# 未知來源要被跳脫，不得變成 HTML
ev("window.__cal0 = CALENDAR.slice(); CALENDAR.unshift({code:'0050', name:'x', iso_date:'2099-01-02', day:'2', mon:'1月', amt:1.0, source:'official', amount_source:'某新來源<b>x</b>'}); true")
ev("renderAll(ETFS, CALENDAR, '2026-10-09 22:20', {price:1,change_pt:0,change_pct:0}, true, false); true"); wait_ms(150)
h = ev("(()=>{const x=[...document.querySelectorAll('#calList .cal-item')].find(i=>i.dataset.code==='0050'); const l=x&&x.querySelector('.src-lbl'); return l?{t:l.textContent, b:l.querySelectorAll('b').length}:null})()")
check('未知來源原樣顯示且經跳脫（不渲染成 HTML）', h and '某新來源<b>x</b>' in h['t'] and h['b'] == 0, h)
ev("CALENDAR.length=0; __cal0.forEach(x=>CALENDAR.push(x)); renderAll(ETFS, CALENDAR, '2026-10-09 22:20', {price:1,change_pt:0,change_pct:0}, true, false); true"); wait_ms(150)

# ── Detail：第三方金額＝參考金額；TWSE 金額＝公告金額；其他 Detail 資訊不受影響
def dv(code):
    ev("openDetail(%s); detailTab('dividend'); true" % json.dumps(code)); wait_ms(250)
    t = ev("document.querySelector('[data-pane=dividend]').innerText") or ''
    ev("closeDetail(); true"); wait_ms(150)
    return t
for code in ('00936', '00929', '0056'):
    c = [x for x in cal if x['code'] == code]
    if not c or c[0].get('amount_source') != 'MoneyDJ': continue
    t = dv(code)
    check('Detail %s：參考金額（來源：MoneyDJ，非官方公告金額）、依參考金額試算、除息日仍標官方公告' % code,
          '參考金額（來源：MoneyDJ，非官方公告金額）' in t and '依參考金額試算' in t and '公告金額（來源' not in t and '官方公告' in t and c[0]['iso_date'] in t, t[:300].replace('\n', ' | '))
ev("""window.__cal1 = CALENDAR.slice(); const e=ETFS.find(x=>x.code==='0050');
  CALENDAR.push({code:'0050', name:e.name, iso_date:'2099-01-02', day:'2', mon:'1月', source:'official', amt:0.5, amount_source:'TWSE'}); true""")
t = dv('0050')
check('Detail TWSE 金額：仍為「公告金額（來源：TWSE）」與「依公告金額試算」', '公告金額（來源：TWSE）' in t and '依公告金額試算' in t, t[:300].replace('\n', ' | '))
ev("CALENDAR[CALENDAR.length-1].amount_source = null; true")
t = dv('0050')
check('Detail 官方除息日但金額來源缺值：參考金額（來源：未標示…），不稱公告金額', '參考金額（來源：未標示，非官方公告金額）' in t and '公告金額（來源' not in t, t[:300].replace('\n', ' | '))
ev("CALENDAR.length=0; __cal1.forEach(x=>CALENDAR.push(x)); true")

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'))
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
