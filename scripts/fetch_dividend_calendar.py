"""
scripts/fetch_dividend_calendar.py
從 TWSE OpenAPI TWT48U_ALL 抓取官方除權息預告
輸出 data/dividend_calendar.json

授權：政府開放資料 data.gov.tw/license
"""
import json, sys, ssl, datetime, urllib.request
from pathlib import Path

ROOT    = Path(__file__).parent.parent
OUT     = ROOT / "data" / "dividend_calendar.json"
API_URL = "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL"
HEADERS = {"User-Agent": "ETF-dividend-fetcher/1.0 (github.com/p14090060/cashflow-etf)"}

# 與 index.html LAZY_WATCHLIST 同步維護
LAZY_WATCHLIST = {
    '0050', '0056', '006208', '00878', '00919', '00929', '00940', '00939',
    '00936', '00930', '00932', '00713', '00701', '00850', '00757',
    '00646', '00662', '00679B', '00687B', '00772B',
}

FREQ_MAP = {
    "月配": 12, "季配": 4, "半年配": 2, "年配": 1, "不配息": 0,
}


def roc_to_iso(date_str: str) -> str:
    """
    民國日期 → ISO 8601
    "1150519" → "2026-05-19"
    前 3 碼民國年 + 1911 = 西元年；後 4 碼 MMDD
    """
    s = str(date_str).strip()
    if len(s) != 7:
        return ""
    try:
        year  = int(s[:3]) + 1911
        month = int(s[3:5])
        day   = int(s[5:7])
        datetime.date(year, month, day)   # 驗證日期合法
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        return ""


def fetch_api() -> list:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    req = urllib.request.Request(API_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    today = datetime.date.today()
    today_str = today.isoformat()

    print(f"[DIV] 抓取 TWSE TWT48U_ALL … ({today_str})")

    try:
        rows = fetch_api()
        print(f"[DIV] 取得 {len(rows)} 筆原始資料")
    except Exception as e:
        print(f"[DIV] ⚠ API 失敗：{e}", file=sys.stderr)
        if OUT.exists():
            print("[DIV] 保留現有 dividend_calendar.json，本次不覆寫")
            sys.exit(0)
        else:
            print("[DIV] 無舊資料可保留，退出", file=sys.stderr)
            sys.exit(1)

    # code → 最近一筆未來公告
    # 同一 ETF 可能有多筆（月配 ETF 每月一筆），取 ex_dividend_date 最近者
    candidates: dict[str, dict] = {}

    for row in rows:
        code = str(row.get("Code", "")).strip()
        if code not in LAZY_WATCHLIST:
            continue

        # 只取有現金配息的行（ETF 幾乎都是現金，這層過濾也排除純配股）
        try:
            amount = float(str(row.get("CashDividend", "0")).strip())
        except ValueError:
            continue
        if amount <= 0:
            continue

        iso_date = roc_to_iso(str(row.get("Date", "")))
        if not iso_date or iso_date < today_str:
            continue   # 已過去的公告略過

        name = str(row.get("Name", "")).strip()

        # 同代號取日期最近（最小）的未來公告
        if code not in candidates or iso_date < candidates[code]["ex_dividend_date"]:
            candidates[code] = {
                "name":            name,
                "ex_dividend_date": iso_date,
                "amount":          amount,
            }

    print(f"[DIV] LAZY_WATCHLIST 中有官方公告：{len(candidates)} 支")
    for code, d in sorted(candidates.items()):
        print(f"      {code:8s}  {d['name']:<22s}  {d['ex_dividend_date']}  {d['amount']:.4f} 元/單位")

    output = {
        "_meta": {
            "last_updated": today_str,
            "source":       "TWSE OpenAPI (TWT48U_ALL)",
            "source_url":   API_URL,
            "license":      "政府開放資料 (data.gov.tw/license)",
            "note":         "僅收錄 LAZY_WATCHLIST 中的 ETF；同代號多筆時取最近未來公告"
        },
        "etfs": candidates,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[DIV] OK 已輸出 {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
