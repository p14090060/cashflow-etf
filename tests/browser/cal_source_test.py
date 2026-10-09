"""D4 配息日曆來源標籤＋Detail 金額來源文字。

執行方式同其他 browser 測試（http 8765、Chrome remote debugging 9223）。
- 除息日來源（source）與金額來源（amount_source）分開：source=official 不等於金額官方
- 現有欄位證明不了「本次官方公告金額」（TWSE 逐檔查詢不綁除息日、保留前值、FinMind 只比數值），
  所以任何來源都不得標成「公告金額」或「核實」；來源資訊（差異比例、保留前值）照實保留
- manual 只標「人工提供資料」；未知來源原樣顯示且經跳脫
- Detail：一律「參考金額（來源…；未能確認為本次官方公告金額）」「依參考金額試算」
"""
import sys, json, re
src = open('tests/browser/detail_ui_test.py', encoding='utf-8').read()
exec(src.split("# ── T2 開啟 0050")[0])   # 載入頁面、helper、T0
ev("clearInterval(_pollTimer); true")

# 標籤裡不得出現的官方／核實字樣（負向）
BANNED = ('公告金額', '核實', '官方公告', '🏛', '官方金額')
def amt_text(c):
    """獨立於前端的金額來源描述（與 calAmtSrcText 規則相同、各自實作）"""
    raw = c.get('amount_source') or ''
    kept = '（保留前值）' in raw
    a = raw.replace('（保留前值）', '')
    if not a or a == c.get('source'): t = '金額來源未標示'
    elif a == 'TWSE × FinMind 核實': t = '金額來源：TWSE，與 FinMind 最近一筆相差 ≤ 5%'
    elif a == 'FinMind（估算）': t = '金額：FinMind 估算'
    else: t = '金額來源：' + a
    return t + ('（保留前值，可能是前次金額）' if kept else '')
def is_estimate(c):
    a = c.get('amount_source') or ''
    return (c.get('source') == 'estimate' and not a) or a.replace('（保留前值）', '') == 'FinMind（估算）'
def expect(c):
    """日曆標籤預期：估算照講估算；其餘一律明示「參考金額」（Detail 用 amt_text，外層另有「參考金額（…）」）"""
    a = c.get('amount_source') or ''
    if c.get('source') == 'manual' and a in ('', 'manual'): return '人工提供資料（參考金額）'
    if c.get('source') == 'estimate' and not a: return '歷史平均估算'
    t = amt_text(c)
    if not is_estimate(c):
        t = re.sub(r'^金額來源未標示', '參考金額，來源未標示', t); t = re.sub(r'^金額來源：', '參考金額來源：', t)
    return ('官方除息日｜' if c.get('source') == 'official' else '') + t
def label_ok(lbl, c):
    # 負向：非估算的標籤少了「參考金額」、或出現公告金額／核實／官方公告 → FAIL
    return expect(c) in lbl and not any(b in lbl for b in BANNED) and (is_estimate(c) or '參考金額' in lbl)

# ── 正式 calendar：逐筆比對 rendered 標籤
ev("Router.toBase({base:'home'}); true"); wait_ms(300)
cal = ev("CALENDAR.filter(c=>!c.iso_date || c.iso_date >= new Date().toLocaleDateString('sv-SE'))")
lbls = ev("[...document.querySelectorAll('#calList .cal-item')].map(x=>({code:x.dataset.code, lbl:(x.querySelector('.src-lbl')||{}).textContent||'', cls:(x.querySelector('.src-lbl')||{}).className||'', amt:(x.querySelector('.cal-amt')||{}).textContent||''}))")
check('正式日曆筆數與畫面一致（%d 筆）' % len(cal), len(cal) == len(lbls) and [c['code'] for c in cal] == [l['code'] for l in lbls], (len(cal), len(lbls)))
bad = []
for c, l in zip(cal, lbls):
    if c.get('amt') is None:
        if l['lbl']: bad.append((c['code'], 'amt null 卻有標籤', l['lbl']))
        continue
    if not l['lbl']: bad.append((c['code'], '留白')); continue
    if not label_ok(l['lbl'], c) or 'src-official' in l['cls']: bad.append((c['code'], l['lbl'], expect(c)))
    if ('%.2f 元' % c['amt']) not in l['amt']: bad.append((c['code'], '金額被改', l['amt']))
check('正式日曆每筆都有正確來源標籤、無官方金額／核實字樣、金額未改', not bad, bad)
for code in ('00936', '00929', '0056'):
    row = [l for l in lbls if l['code'] == code]; c = [x for x in cal if x['code'] == code]
    if not row or not c: print('   SKIP %s：正式日曆已無此筆' % code); continue
    print('   %s %s ｜ %s' % (code, row[0]['lbl'], row[0]['amt']))
    if c[0].get('amount_source') == 'MoneyDJ' and c[0].get('source') == 'official':
        check('%s：官方除息日｜參考金額來源：MoneyDJ' % code, '官方除息日｜參考金額來源：MoneyDJ' in row[0]['lbl'] and not any(b in row[0]['lbl'] for b in BANNED), row[0])
est = [l for c, l in zip(cal, lbls) if c.get('source') == 'estimate']
check('估算 %d 筆全部「歷史平均估算」、無官方字樣' % len(est), all('歷史平均估算' in l['lbl'] and not any(b in l['lbl'] for b in BANNED) for l in est), est[:3])

# ── 合成：各種來源走 calSrcLabel；負向＝證據不足的來源不得出現公告金額／核實
CASES = [
    ('TWSE 正常值', {'source': 'official', 'amount_source': 'TWSE'}),
    ('TWSE（保留前值）', {'source': 'official', 'amount_source': 'TWSE（保留前值）'}),
    ('TWSE_UNKNOWN', {'source': 'official', 'amount_source': 'TWSE_UNKNOWN'}),
    ('TWSE × FinMind 核實', {'source': 'official', 'amount_source': 'TWSE × FinMind 核實'}),
    ('TWSE（FinMind 差異 12%）', {'source': 'official', 'amount_source': 'TWSE（FinMind 差異 12%）'}),
    ('TWSE × FinMind 核實（保留前值）', {'source': 'official', 'amount_source': 'TWSE × FinMind 核實（保留前值）'}),
    ('MoneyDJ', {'source': 'official', 'amount_source': 'MoneyDJ'}),
    ('MoneyDJ（保留前值）', {'source': 'official', 'amount_source': 'MoneyDJ（保留前值）'}),
    ('FinMind（估算）', {'source': 'official', 'amount_source': 'FinMind（估算）'}),
    ('official 回填', {'source': 'official', 'amount_source': 'official'}),
    ('官方日期、金額來源缺值', {'source': 'official', 'amount_source': None}),
    ('Gavin 人工確認', {'source': 'official', 'amount_source': 'Gavin 人工確認'}),
    ('manual', {'source': 'manual', 'amount_source': 'manual'}),
    ('estimate', {'source': 'estimate', 'amount_source': None}),
    ('未知來源（含 HTML）', {'source': 'official', 'amount_source': '某新來源<b>x</b>'}),
]
for name, cs in CASES:
    c = dict(cs, code='ZZ1', amt=1.23)
    got = ev("calSrcLabel(%s)" % json.dumps(c, ensure_ascii=False))
    check('合成 %s → %s' % (name, got and got['text']), got and label_ok(got['text'], c) and got['cls'] != 'src-official', (got, expect(c)))
check('差異比例照實保留：「TWSE（FinMind 差異 12%）」', '差異 12%' in ev("calSrcLabel({source:'official', amount_source:'TWSE（FinMind 差異 12%）', amt:1}).text"))

# 舊金額沿用到新除息日：實際畫進日曆，標籤要講明保留前值、不得稱公告或核實
ev("window.__cal0 = CALENDAR.slice(); CALENDAR.unshift({code:'0050', name:'x', iso_date:'2099-01-02', day:'2', mon:'1月', amt:1.0, source:'official', amount_source:'TWSE × FinMind 核實（保留前值）'}); true")
ev("renderAll(ETFS, CALENDAR, '2026-10-09 22:20', {price:1,change_pt:0,change_pct:0}, true, false); true"); wait_ms(150)
h = ev("(()=>{const x=[...document.querySelectorAll('#calList .cal-item')].find(i=>i.dataset.code==='0050'); const l=x&&x.querySelector('.src-lbl'); return l?l.textContent:null})()")
check('舊金額沿用到新除息日：參考金額＋「保留前值，可能是前次金額」、無核實／公告金額', h and '參考金額來源：TWSE，與 FinMind 最近一筆相差 ≤ 5%' in h
      and '保留前值，可能是前次金額' in h and not any(b in h for b in BANNED), h)
# 未知來源要被跳脫，不得變成 HTML
ev("CALENDAR[0].amount_source = '某新來源<b>x</b><img src=x onerror=window.__xss=1>'; renderAll(ETFS, CALENDAR, '2026-10-09 22:20', {price:1,change_pt:0,change_pct:0}, true, false); true"); wait_ms(200)
h = ev("(()=>{const x=[...document.querySelectorAll('#calList .cal-item')].find(i=>i.dataset.code==='0050'); const l=x&&x.querySelector('.src-lbl'); return l?{t:l.textContent, el:l.querySelectorAll('b,img').length, xss:!!window.__xss}:null})()")
check('未知來源原樣顯示且經跳脫（不渲染 HTML、不執行）', h and '某新來源<b>x</b>' in h['t'] and h['el'] == 0 and not h['xss'], h)
ev("CALENDAR.length=0; __cal0.forEach(x=>CALENDAR.push(x)); renderAll(ETFS, CALENDAR, '2026-10-09 22:20', {price:1,change_pt:0,change_pct:0}, true, false); true"); wait_ms(150)

# ── Detail：一律參考金額＋來源；不稱公告金額、不說核實
def dv(code):
    ev("openDetail(%s); detailTab('dividend'); true" % json.dumps(code)); wait_ms(250)
    t = ev("document.querySelector('[data-pane=dividend]').innerText") or ''
    ev("closeDetail(); true"); wait_ms(150)
    return t
def detail_ok(t, c):
    return (('參考金額（' + amt_text(c) + '；未能確認為本次官方公告金額）') in t and '依參考金額試算' in t
            and '公告金額（來源' not in t and '依公告金額試算' not in t and 'FinMind 核實' not in t)
for code in ('00936', '00929', '0056'):
    c = [x for x in cal if x['code'] == code]
    if not c or c[0].get('source') != 'official': continue
    t = dv(code)
    check('Detail %s：參考金額（%s…）、除息日仍標官方公告' % (code, amt_text(c[0])), detail_ok(t, c[0]) and '官方公告' in t and c[0]['iso_date'] in t, t[:300].replace('\n', ' | '))
ev("window.__cal1 = CALENDAR.slice(); const e=ETFS.find(x=>x.code==='0050'); CALENDAR.push({code:'0050', name:e.name, iso_date:'2099-01-02', day:'2', mon:'1月', source:'official', amt:0.5, amount_source:'TWSE'}); true")
for name, a in [('TWSE 正常值', 'TWSE'), ('TWSE（保留前值）', 'TWSE（保留前值）'), ('TWSE_UNKNOWN', 'TWSE_UNKNOWN'), ('TWSE × FinMind 核實', 'TWSE × FinMind 核實'),
                ('TWSE（FinMind 差異 8%）', 'TWSE（FinMind 差異 8%）'), ('MoneyDJ', 'MoneyDJ'), ('金額來源缺值', None), ('未知來源', '某新來源')]:
    ev("CALENDAR[CALENDAR.length-1].amount_source = %s; true" % json.dumps(a, ensure_ascii=False))
    t = dv('0050')
    c = {'source': 'official', 'amount_source': a}
    check('Detail 合成 %s：參考金額＋來源、不稱公告金額／核實' % name, detail_ok(t, c), t[:260].replace('\n', ' | '))
ev("CALENDAR.length=0; __cal1.forEach(x=>CALENDAR.push(x)); true")

exc = [e for e in events if e.get('method') == 'Runtime.exceptionThrown']
for e in exc: print('   EXC:', e['params']['exceptionDetails'].get('text'))
check('no uncaught exceptions', len(exc) == 0, len(exc))
fails = [r for r in results if not r[1]]
print('\nTOTAL %d  PASS %d  FAIL %d' % (len(results), len(results) - len(fails), len(fails)))
ws.close()
