"""
scripts/fetch_dividend_calendar.py
從 TWSE e添富 ETFortune/dividendList 抓取上市 ETF 除息公告
比舊 TWT48U_ALL 早公告 4-6 週，資料更完整
輸出 data/dividend_calendar.json
"""
import json, sys, ssl, datetime, re, urllib.request
from pathlib import Path

ROOT     = Path(__file__).parent.parent
OUT      = ROOT / "data" / "dividend_calendar.json"
BASE_URL = "https://www.twse.com.tw/rwd/zh/ETFortune/dividendList"
HEADERS  = {"User-Agent": "ETF-dividend-fetcher/1.0 (github.com/p14090060/cashflow-etf)"}

LAZY_WATCHLIST = {
    '0050', '0056', '006208', '00878', '00919', '00929', '00940', '00939',
    '00936', '00930', '00932', '00713', '00701', '00850', '00757',
    '00646', '00662', '00679B', '00687B', '00772B',
}

ROC_DATE_RE = re.compile(r'(\d{3})年(\d{2})月(\d{2})日')
TR_RE       = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
TD_RE       = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.DOTALL | re.IGNORECASE)
TAG_RE      = re.compile(r'<[^>]+>')
CODE_RE     = re.compile(r'^[0-9]{4,6}[A-Z]?$')


def roc_to_iso(text: str) -> str:
    m = ROC_DATE_RE.search(str(text).strip())
    if not m:
        return ""
    try:
        year  = int(m.group(1)) + 1911
        month = int(m.group(2))
        day   = int(m.group(3))
        datetime.date(year, month, day)
        return f"{year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        return ""


def strip_tags(html: str) -> str:
    return TAG_RE.sub("", html).strip()


def fetch_html(date_str: str) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    url = f"{BASE_URL}?date={date_str}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return r.read().decode("utf-8")


def parse_html(html: str) -> list:
    results = []
    for tr_m in TR_RE.finditer(html):
        cells = [strip_tags(td_m.group(1))
                 for td_m in TD_RE.finditer(tr_m.group(1))]
        if len(cells) < 6:
            continue
        code = cells[0]
        if not CODE_RE.match(code):
            continue
        ex_date = roc_to_iso(cells[2])
        if not ex_date:
            continue
        try:
            amount = float(cells[5].replace(",", ""))
        except ValueError:
            amount = 0.0
        results.append({
            "code":             code,
            "name":             cells[1],
            "ex_dividend_date": ex_date,
            "amount":           amount,
        })
    return results


def main():
    today     = datetime.date.today()
    today_str = today.isoformat()
    print(f"[ETFORTUNE] 除息行事曆抓取 ({today_str})")

    # 抓當月 + 未來兩個月
    fetch_dates = []
    d = today.replace(day=1)
    for _ in range(3):
        fetch_dates.append(d.strftime("%Y%m%d"))
        d = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    all_rows = []
    for ds in fetch_dates:
        try:
            print(f"[ETFORTUNE] 抓取 {ds} …")
            html = fetch_html(ds)
            rows = parse_html(html)
            print(f"[ETFORTUNE] 解析 {len(rows)} 筆")
            all_rows.extend(rows)
        except Exception as e:
            print(f"[ETFORTUNE] ⚠ {ds} 失敗：{e}", file=sys.stderr)

    if not all_rows:
        print("[ETFORTUNE] ⚠ 無任何資料，保留現有檔案", file=sys.stderr)
        sys.exit(0)

    # 篩選 LAZY_WATCHLIST + 未來日期；同代號取最近未來日期
    candidates: dict = {}
    for row in all_rows:
        code = row["code"]
        if code not in LAZY_WATCHLIST:
            continue
        iso = row["ex_dividend_date"]
        if iso < today_str:
            continue
        if code not in candidates or iso < candidates[code]["ex_dividend_date"]:
            candidates[code] = row

    print(f"\n[ETFORTUNE] LAZY_WATCHLIST 有公告：{len(candidates)} 支")
    for code, d in sorted(candidates.items(), key=lambda x: x[1]["ex_dividend_date"]):
        print(f"  {code:8s}  {d['name']:<22s}  {d['ex_dividend_date']}  {d['amount']:.4f} 元")

    output = {
        "_meta": {
            "last_updated": today_str,
            "source":       "TWSE e添富 (ETFortune/dividendList)",
            "source_url":   BASE_URL,
            "license":      "政府開放資料 (data.gov.tw/license)",
            "note":         "抓當月+未來兩個月，LAZY_WATCHLIST 中同代號取最近未來日期",
        },
        "etfs": candidates,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[ETFORTUNE] OK → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
