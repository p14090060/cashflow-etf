"""Phase 5 P1：資料池篩選鏈（EX-1～EX-11）。

fetch_etf.py 是頂層直接執行的腳本（import 就會開始抓資料），所以這裡用 ast
只取出篩選相關的常數與函式來測，不 import 整支。
fixture：tests/fixtures/isin_strmode{2,4}.html（2026-10-05 ISIN 實際頁面，
ETF／ETN 區段保留全部資料列，其他區段各留 3 列）。

執行：python tests/test_pool.py
"""
import ast, io, json, re, ssl, sys, tempfile, contextlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / 'tests' / 'fixtures'

WANT = {'EXCLUDE_KW', 'EXCLUDE_SUFFIX', 'ISIN_SECTIONS', '_SECTION_RE', '_TD_RE',
        'CURATED', 'CURATED_CODES', 'pool_excluded', 'isin_sections',
        'parse_isin_rows', 'parse_isin_pool', '_isin_etf_pool',
        'fetch_twse_etf_pool', 'build_pool'}


def load():
    tree = ast.parse((ROOT / 'fetch_etf.py').read_text(encoding='utf-8'))
    body = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in WANT:
            body.append(n)
        elif isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in WANT for t in n.targets):
            body.append(n)
    ns = {'re': re, 'ssl': ssl, 'json': json, 'Path': Path, 'TWO_CODES': set()}
    exec(compile(ast.Module(body=body, type_ignores=[]), 'fetch_etf.py', 'exec'), ns)
    return ns


F = load()
results = []


def check(name, cond, info=''):
    results.append(bool(cond))
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(info)))


def page(m):
    return (FIX / ('isin_strmode%d.html' % m)).read_text(encoding='utf-8')


def quiet(fn, *a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            r = fn(*a)
        except Exception as e:
            r = e
    return r, buf.getvalue()


ex = F['pool_excluded']

# EX-1 字尾規則
for c, n in [('00631L', '元大台灣50正2'), ('00632R', '元大台灣50反1'), ('00682U', '元大美元指數'),
             ('00693U', '街口S&P黃豆'), ('00763U', '街口道瓊銅'), ('02001L', '富邦蘋果正二N')]:
    check('EX-1 %s 被③排除' % c, ex(c, 'X') == 'suffix-' + c[-1], ex(c, 'X'))
for c in ['0050', '00981A', '00980D', '00625K', '00687C']:
    check('EX-1 %s 不被③排除' % c, not str(ex(c, 'X')).startswith('suffix'), ex(c, 'X'))

# EX-2 A／B／D／K 不誤殺
for c, n in [('00981A', '主動統一台股增長'), ('00840B', '凱基IG精選15+'),
             ('00980D', '主動聯博投等入息'), ('00625K', '富邦上証+R')]:
    check('EX-2 %s 通過③④' % c, ex(c, n) is None, ex(c, n))

# EX-3 關鍵字第二道防線
check('EX-3 正二（字尾非 L）被④排除', ex('009999', '某某正二') == 'keyword')
check('EX-3 反一（字尾非 R）被④排除', ex('009998', '某某反一') == 'keyword')

# 解析兩頁
p2, log2 = quiet(F['parse_isin_pool'], page(2), 'strMode=2')
p4, log4 = quiet(F['parse_isin_pool'], page(4), 'strMode=4')
codes = {c for c, _ in p2} | {c for c, _ in p4}
check('fixture 解析成功', isinstance(p2, list) and isinstance(p4, list), (p2, p4))
check('fixture 收到一般 ETF（0050、006201、00411A）', {'0050', '006201', '00411A'} <= codes)

# EX-4 完整篩選鏈（①～⑤）
check('EX-4 00687C 不在結果（④「債」）', '00687C' not in codes)
check('EX-4 00981D 主動中信非投等債 不在結果（④「債」）', '00981D' not in codes)
for c in ['00840B', '00980D', '00982D', '00983D', '00984D', '00985D']:
    check('EX-4 債券 %s 在結果' % c, c in codes)
check('EX-4 結果無 L／R／U／T 字尾', not [c for c in codes if c[-1] in 'LRUT'],
      [c for c in codes if c[-1] in 'LRUT'])

# EX-9 ETN positive
check('EX-9 020032 元大綠能N 在結果', '020032' in codes)
check('EX-9 02001L 富邦蘋果正二N 被排除', '02001L' not in codes)
etn2 = F['isin_sections'](page(2))['ETN']
check('EX-9 020032 CFI 為 CMXXXU', re.search(r'020032　.*?CMXXXU', etn2, re.S))

# EX-10／EX-5 區段邊界
secs2 = F['isin_sections'](page(2))
check('EX-10 ETF 區段只到 ETN 標題為止', 'ETN <B>' not in secs2['ETF'] and '020032' not in secs2['ETF'])
check('EX-10 ETN 區段只到下一標題（不含 TDR）', 'TDR' not in secs2['ETN'])
other = []
for t, sec in list(secs2.items()) + list(F['isin_sections'](page(4)).items()):
    if t not in ('ETF', 'ETN'):
        other += [m for m in re.findall(r'<td[^>]*>([0-9A-Z]{4,6})　', sec)]
check('EX-10 其他區段樣本確實存在', len(other) >= 6, other)
check('EX-10／EX-5 其他區段資料列不被收入', not (set(other) & codes), set(other) & codes)
wr = [m for m in re.findall(r'<td[^>]*>([0-9A-Z]{4,6})　[^<]*</td>(?:<td[^>]*>[^<]*</td>){4}<td[^>]*>RW', page(2) + page(4))]
check('EX-5 權證樣本（CFI RW…）存在且不被收入', wr and not (set(wr) & codes), wr)
bad_cfi = page(2).replace('<B> ETF <B> </td></tr>',
    '<B> ETF <B> </td></tr><tr><td>009990　假權證</td><td>X</td><td>X</td><td>X</td><td></td><td>RWSCCA</td><td></td></tr>', 1)
r, log = quiet(F['parse_isin_pool'], bad_cfi, 't')
check('EX-5 ETF 區段內 CFI 不符的列被略過並警告', '009990' not in {c for c, _ in r} and 'CFI=RWSCCA' in log)

# EX-11 缺 ETN 區段
no_etn = re.sub(r'<tr><td[^>]*colspan=7[^>]*><B> ETN <B>.*?(?=<tr><td[^>]*colspan=7)', '', page(2), flags=re.S)
r, log = quiet(F['parse_isin_pool'], no_etn, 'strMode=2')
rc = {c for c, _ in r} if isinstance(r, list) else set()
check('EX-11 無 ETN 區段：ETF 照收', '0050' in rc and len(rc) > 100, len(rc))
check('EX-11 無 ETN 區段：ETN 為空、不退回整頁', '020032' not in rc and not any(c.isdigit() and c[0] != '0' for c in rc))
check('EX-11 印警告', '找不到 ETN 區段' in log, log)

# EX-6 找不到 ETF 區段（即使有 ETN 也視為失敗，不退回整頁）
no_etf = page(2).replace('<B> ETF <B>', '<B> XXX <B>')
r, _ = quiet(F['parse_isin_pool'], no_etf, 'strMode=2')
check('EX-6 parse 丟例外（不退回整頁）', isinstance(r, Exception), r)
pages = {2: no_etf, 4: page(4)}
F['_isin_etf_pool'] = lambda m: F['parse_isin_pool'](pages[m], 'strMode=%s' % m)
tmp = Path(tempfile.mkdtemp())
F['POOL_CACHE'] = tmp / 'cache.json'
r, log = quiet(F['fetch_twse_etf_pool'])
check('EX-6 該市場別回傳空並印警告、另一市場照收',
      '[POOL] ISIN strMode=2' in log and r and all(otc for _, _, otc in r), log)
pages[4] = page(4).replace('<B> ETF <B>', '<B> XXX <B>')
r, log = quiet(F['fetch_twse_etf_pool'])
check('EX-6 兩市場都失敗 → 回傳空（交給 cache fallback）', r == [], r)

# EX-7 cache fallback
json.dump([['0050', '元大台灣50', False], ['00631L', '元大台灣50正2', False],
           ['00682U', '元大美元指數', False], ['009997', '某某正二', False],
           ['00687C', '國泰20年美債+櫃U', True], ['00411A', '主動統一前沿科技', True]],
          open(F['POOL_CACHE'], 'w', encoding='utf-8'))
F['TWO_CODES'].clear()
pool, log = quiet(F['build_pool'])
pc = {c for c, _ in pool}
check('EX-7 cache 的 L／U／關鍵字項目被排除', not ({'00631L', '00682U', '009997', '00687C'} & pc), pc)
check('EX-7 cache 的正常項目保留（含上櫃 TWO_CODES）', {'0050', '00411A'} <= pc and '00411A' in F['TWO_CODES'])

# EX-8 CURATED 防禦性
F['CURATED'] = F['CURATED'] + [('00631L', '元大台灣50正2')]
F['CURATED_CODES'] = {c for c, _ in F['CURATED']}
pool, _ = quiet(F['build_pool'])
check('EX-8 CURATED 出現 L 字尾也被排除', '00631L' not in {c for c, _ in pool})
check('EX-8 CURATED 正常項目保留', {'0056', '0050', '00928'} <= {c for c, _ in pool})

print('\n%d/%d PASS' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
