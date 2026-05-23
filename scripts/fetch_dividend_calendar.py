"""
scripts/fetch_dividend_calendar.py
多源除息行事曆抓取：TWSE ETFortune（主）→ FinMind（副）
- TWSE 金額為 0 時自動向 FinMind 補查
- 距除息日 ≤ 7 天且所有來源均查無金額 → TG 通知
- amount=null 代表真正查無，前端顯示「待公告」
輸出 data/dividend_calendar.json
"""
import json, sys, ssl, os, datetime, re, time, urllib.request, urllib.parse
from pathlib import Path

ROOT     = Path(__file__).parent.parent
OUT      = ROOT / "data" / "dividend_calendar.json"
BASE_URL = "https://www.twse.com.tw/rwd/zh/ETFortune/dividendList"
HEADERS  = {"User-Agent": "ETF-dividend-fetcher/1.0 (github.com/p14090060/cashflow-etf)"}

FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN", "")
TG_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
ALERT_DAYS    = 7   # 距除息日 ≤ N 天且查無金額 → 發 TG

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


def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx


def notify_tg(msg: str):
    print(f"[TG] {msg}")
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": msg}).encode()
        req  = urllib.request.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[TG ERROR] {e}", file=sys.stderr)


# ── Source 1: TWSE ETFortune bulk list ──────────────────────────────

def _parse_twse_html(html: str) -> list:
    results = []
    for tr_m in TR_RE.finditer(html):
        cells = [strip_tags(td_m.group(1)) for td_m in TD_RE.finditer(tr_m.group(1))]
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
        except (ValueError, IndexError):
            amount = 0.0
        results.append({"code": code, "name": cells[1], "ex_dividend_date": ex_date, "amount": amount})
    return results


def fetch_twse_bulk() -> list:
    today = datetime.date.today()
    all_rows = []
    d = today.replace(day=1)
    for _ in range(3):
        ds = d.strftime("%Y%m%d")
        try:
            print(f"[TWSE] 抓取 {ds} …")
            req = urllib.request.Request(f"{BASE_URL}?date={ds}", headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
                html = r.read().decode("utf-8")
            rows = _parse_twse_html(html)
            print(f"[TWSE] 解析 {len(rows)} 筆")
            all_rows.extend(rows)
        except Exception as e:
            print(f"[TWSE] ⚠ {ds} 失敗：{e}", file=sys.stderr)
        d = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return all_rows


# ── Source 2: TWSE ETFortune per-ETF query ─────────────────────────

def fetch_twse_per_etf(code: str, today_str: str) -> float:
    """逐支查 TWSE ETFortune，可能比 bulk 早出現金額。"""
    start = datetime.date.today().strftime("%Y%m%d")
    url   = f"{BASE_URL}?stkNo={code}&startDate={start}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
            html = r.read().decode("utf-8")
        rows = _parse_twse_html(html)
        future = [r for r in rows if r["ex_dividend_date"] >= today_str and r["amount"] > 0]
        if future:
            future.sort(key=lambda x: x["ex_dividend_date"])
            return future[0]["amount"]
    except Exception as e:
        print(f"[TWSE-ETF] {code} 失敗：{e}", file=sys.stderr)
    return 0.0


# ── Source 3: FinMind TaiwanStockDividend ──────────────────────────

def fetch_finmind_dividend(code: str) -> float:
    """從 FinMind 取最近 90 天的最新一筆現金配息金額。"""
    if not FINMIND_TOKEN:
        print(f"[FinMind] 無 token，跳過 {code}")
        return 0.0
    start  = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    params = urllib.parse.urlencode({
        "dataset":    "TaiwanStockDividend",
        "data_id":    code,
        "start_date": start,
        "token":      FINMIND_TOKEN,
    })
    try:
        req = urllib.request.Request(
            f"https://api.finmindtrade.com/api/v4/data?{params}",
            headers={"User-Agent": HEADERS["User-Agent"]},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        if data.get("status") == 402:
            print(f"[FinMind] 配額用完，跳過 {code}")
            return 0.0
        records = data.get("data", [])
        if records:
            latest = sorted(records, key=lambda x: x.get("date", ""), reverse=True)[0]
            for field in ("cash_dividend", "CashEarningsDistribution"):
                try:
                    amt = float(latest.get(field) or 0)
                    if amt > 0:
                        return amt
                except (TypeError, ValueError):
                    pass
    except Exception as e:
        print(f"[FinMind] {code} 失敗：{e}", file=sys.stderr)
    return 0.0


# ── Main ────────────────────────────────────────────────────────────

def main():
    today     = datetime.date.today()
    today_str = today.isoformat()
    print(f"[DIV-CAL] 除息行事曆抓取 ({today_str})")

    # Step 1: TWSE bulk
    all_rows = fetch_twse_bulk()
    if not all_rows:
        print("[DIV-CAL] ⚠ 無任何資料，保留現有檔案", file=sys.stderr)
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
            candidates[code] = {
                **row,
                "amount_source": "TWSE" if row["amount"] > 0 else None,
            }

    # Step 2: 補查金額為 0 的 ETF
    no_amount = [c for c, d in candidates.items() if d.get("amount_source") is None]
    if no_amount:
        print(f"\n[DIV-CAL] {len(no_amount)} 支 TWSE 金額為 0，啟動補查…")
        alerts = []

        for code in no_amount:
            entry     = candidates[code]
            ex_date   = entry["ex_dividend_date"]
            days_left = (datetime.date.fromisoformat(ex_date) - today).days

            # 2a: TWSE per-ETF
            time.sleep(0.5)
            amt = fetch_twse_per_etf(code, today_str)
            if amt > 0:
                entry["amount"]        = amt
                entry["amount_source"] = "TWSE"
                print(f"  [TWSE-ETF] {code} 補到 {amt:.4f} 元")
                continue

            # 2b: FinMind
            time.sleep(0.3)
            amt = fetch_finmind_dividend(code)
            if amt > 0:
                entry["amount"]        = amt
                entry["amount_source"] = "FinMind（估算）"
                print(f"  [FinMind]  {code} 補到 {amt:.4f} 元（估算）")
                continue

            # 2c: 仍查無
            entry["amount"]        = None   # 前端顯示「待公告」
            entry["amount_source"] = None
            print(f"  [NO DATA]  {code} 除息日 {ex_date}，距今 {days_left} 天，所有來源查無金額")

            if days_left <= ALERT_DAYS:
                alerts.append((code, entry.get("name", code), ex_date, days_left))

        if alerts:
            lines = ["⚠️ 配息金額查無通知"]
            for code, name, ex_date, days_left in alerts:
                lines.append(f"• {code} {name}\n  除息日 {ex_date}（距今 {days_left} 天）")
            lines.append("TWSE ETFortune 及 FinMind 均查無配息金額，請人工確認")
            notify_tg("\n".join(lines))

    # 印出結果
    print(f"\n[DIV-CAL] LAZY_WATCHLIST 有公告：{len(candidates)} 支")
    for code, d in sorted(candidates.items(), key=lambda x: x[1]["ex_dividend_date"]):
        amt = d.get("amount")
        amt_str = f"{amt:.4f} 元" if amt is not None else "待公告"
        src_str = d.get("amount_source") or "--"
        print(f"  {code:8s}  {d['name']:<22s}  {d['ex_dividend_date']}  {amt_str}  [{src_str}]")

    output = {
        "_meta": {
            "last_updated": today_str,
            "sources":      "TWSE ETFortune → TWSE per-ETF → FinMind",
            "source_url":   BASE_URL,
            "license":      "政府開放資料 (data.gov.tw/license)",
        },
        "etfs": candidates,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[DIV-CAL] OK → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
