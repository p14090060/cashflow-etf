"""
scripts/auto_sync_etfs.py
每週自動同步 ETF 配息資訊（取代 validate_div_freq.py 的功能並大幅擴充）：

1. 從 TWSE ETFortune 抓近 15 個月 + 未來 2 個月配息公告
   → 涵蓋「歷史計算均值」和「首次配息公告偵測」
2. 偵測新 ETF（出現在公告但不在 dividend_info.json）→ 自動加入
3. 自動推算配息頻率、配息月份、平均每單位配息
4. 新 ETF 首次配息公告 → 自動填入 avg_dividend_per_share
5. 從 TWSE ETF_SEARCH 驗證頻率文字（雙重確認）
"""
import json, time, ssl, re, datetime, urllib.request
from collections import defaultdict
from pathlib import Path

try:
    import requests as _req
    def _get(url, **kw):
        r = _req.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"}, **kw)
        return r.text
except ImportError:
    def _get(url, **kw):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return r.read().decode("utf-8")

ROOT     = Path(__file__).parent.parent
DIV_JSON = ROOT / "data" / "dividend_info.json"
BASE_URL = "https://www.twse.com.tw/rwd/zh/ETFortune/dividendList"

ROC_DATE_RE = re.compile(r'(\d{3})年(\d{2})月(\d{2})日')
TR_RE       = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
TD_RE       = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.DOTALL | re.IGNORECASE)
TAG_RE      = re.compile(r'<[^>]+>')
CODE_RE     = re.compile(r'^[0-9]{4,6}[A-Z]?$')

FREQ_KEYWORDS = [
    (["每月", "月配", "按月"], "月配"),
    (["每季", "季配", "按季"], "季配"),
    (["每半年", "半年配", "半年度"], "半年配"),
    (["每年", "年配", "按年"], "年配"),
    (["不配", "不分配", "不收益分配"], "不配息"),
]

# 從唯一配息月份數量推算頻率（輔助判斷）
def _freq_from_unique_months(unique_month_count):
    if unique_month_count >= 10:
        return "月配"
    if unique_month_count >= 3:
        return "季配"
    if unique_month_count >= 2:
        return "半年配"
    if unique_month_count >= 1:
        return "年配"
    return None


def roc_to_iso(text):
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


def strip_tags(html):
    return TAG_RE.sub("", html).strip()


def fetch_month_dividends(yyyymmdd, retries=2):
    """抓 TWSE ETFortune dividendList 單月資料（含重試）"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    url = f"{BASE_URL}?date={yyyymmdd}"
    req = urllib.request.Request(url, headers={"User-Agent": "ETF-auto-sync/1.0"})
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                html = r.read().decode("utf-8")
            break
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(2)
    else:
        raise last_err

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
        except ValueError:
            amount = 0.0
        results.append({"code": code, "name": cells[1],
                         "ex_dividend_date": ex_date, "amount": amount})
    return results


def fetch_freq_from_twse(code):
    """從 TWSE ETF_SEARCH 抓配息頻率描述文字"""
    try:
        clean = "".join(c for c in code if c.isalnum())
        text = _get(f"https://www.twse.com.tw/fund/ETF_SEARCH?response=json&etfNo={clean}")
        for keywords, freq in FREQ_KEYWORDS:
            if any(kw in text for kw in keywords):
                return freq
    except Exception:
        pass
    return None


def iter_months(start: datetime.date, count: int, forward=True):
    """從 start 往前或往後產生 count 個月的第一天"""
    d = start.replace(day=1)
    for _ in range(count):
        yield d
        if forward:
            # 往後一個月
            d = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        else:
            # 往前一個月
            if d.month == 1:
                d = d.replace(year=d.year - 1, month=12)
            else:
                d = d.replace(month=d.month - 1)


def main():
    today = datetime.date.today()
    print(f"[AUTO-SYNC] 開始同步 ETF 配息資訊 ({today})")

    # ── Phase 1: 抓配息公告（過去 15 個月 + 未來 2 個月）──
    fetch_targets = []
    # 往前 15 個月（含當月）
    for d in iter_months(today, 15, forward=False):
        fetch_targets.append(d.strftime("%Y%m%d"))
    # 往後 2 個月（不含當月，已包含在上面）
    nxt = today.replace(day=1)
    for _ in range(2):
        nxt = (nxt.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        fetch_targets.append(nxt.strftime("%Y%m%d"))

    # {code: [{date, amount, name}, ...]}
    history: dict[str, list] = defaultdict(list)
    print(f"[AUTO-SYNC] 抓取 {len(fetch_targets)} 個月資料...")
    for ds in fetch_targets:
        try:
            rows = fetch_month_dividends(ds)
            for row in rows:
                history[row["code"]].append({
                    "date":   row["ex_dividend_date"],
                    "amount": row["amount"],
                    "name":   row["name"],
                })
            time.sleep(0.35)
        except Exception as e:
            print(f"[AUTO-SYNC] !! {ds} 失敗：{e}")

    # 去重（同日期只保留一筆），再按日期排序
    for code in history:
        seen, deduped = set(), []
        for rec in history[code]:
            if rec["date"] not in seen:
                seen.add(rec["date"])
                deduped.append(rec)
        history[code] = sorted(deduped, key=lambda x: x["date"])

    print(f"[AUTO-SYNC] 蒐集到 {len(history)} 支 ETF 的配息紀錄")

    # ── Phase 2: 載入 dividend_info.json ──
    with open(DIV_JSON, encoding="utf-8") as f:
        data = json.load(f)
    etfs = data["etfs"]

    new_added, updated_avg, updated_months, updated_freq = [], [], [], []

    # ── Phase 3: 偵測新 ETF（有配息紀錄但不在 dividend_info.json）──
    for code, recs in history.items():
        if code in etfs:
            continue

        name = recs[-1]["name"] if recs else code
        print(f"[AUTO-SYNC] 發現新 ETF：{code} {name}，向 TWSE 確認頻率...")

        # 先從 TWSE ETF_SEARCH 取官方頻率
        freq = fetch_freq_from_twse(code)
        time.sleep(0.4)

        # fallback：從歷史配息月份數量推算
        if freq is None:
            paid_months = set(int(r["date"][5:7]) for r in recs if r["amount"] > 0)
            freq = _freq_from_unique_months(len(paid_months)) or "不明"

        # 配息月份（從歷史推算）
        paid_months_sorted = sorted(set(int(r["date"][5:7]) for r in recs if r["amount"] > 0))

        # 平均每單位配息（只算有金額的）
        amounts = [r["amount"] for r in recs if r["amount"] > 0]
        avg = round(sum(amounts) / len(amounts), 4) if amounts else None

        etfs[code] = {
            "name":                  name,
            "frequency":             freq,
            "months":                paid_months_sorted,
            "category":              "高股息",   # 預設，_todo=True 標記需人工核實
            "avg_dividend_per_share": avg,
            "_todo":                 True,
        }
        new_added.append(
            f"  {code} {name}  freq={freq}  months={paid_months_sorted}  avg={avg}"
        )

    # ── Phase 4: 更新現有 ETF ──
    for code, meta in etfs.items():
        recs   = history.get(code, [])
        paid   = [r for r in recs if r["amount"] > 0]
        amounts = [r["amount"] for r in paid]

        # 4a. avg_dividend_per_share 為 null，但現在有公告金額 → 自動填入
        if meta.get("avg_dividend_per_share") is None and amounts:
            avg = round(sum(amounts) / len(amounts), 4)
            meta["avg_dividend_per_share"] = avg
            updated_avg.append(
                f"  {code} {meta['name']}  avg={avg}（{len(amounts)} 筆）"
            )

        # 4b. months 為空 且 _todo=True → 從歷史推算並填入
        if not meta.get("months") and meta.get("_todo", True) and paid:
            months = sorted(set(int(r["date"][5:7]) for r in paid))
            meta["months"] = months
            updated_months.append(f"  {code} {meta['name']}  months={months}")

        # 4c. 向 TWSE 確認頻率（雙重核實，不覆蓋已確認的資料除非真的不同）
        if not recs:
            continue   # 沒有配息紀錄的 ETF 略過頻率驗證（避免誤判）
        twse_freq = fetch_freq_from_twse(code)
        time.sleep(0.4)
        if twse_freq and twse_freq != meta.get("frequency"):
            old_freq = meta.get("frequency")
            meta["frequency"] = twse_freq
            if not meta.get("_todo", True):
                meta["_todo"] = True
                meta["months"] = []
            updated_freq.append(
                f"  {code} {meta['name']}: {old_freq} → {twse_freq}"
            )

    # ── Phase 5: 寫回 ──
    changed = bool(new_added or updated_avg or updated_months or updated_freq)
    if changed:
        with open(DIV_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 報告 ──
    print(f"\n{'='*50}")
    print(f"[AUTO-SYNC] 新增 ETF：{len(new_added)} 支")
    for s in new_added:
        print(s)

    print(f"\n[AUTO-SYNC] 首次配息 → 自動填入 avg_dividend_per_share：{len(updated_avg)} 支")
    for s in updated_avg:
        print(s)

    print(f"\n[AUTO-SYNC] 自動填入 months：{len(updated_months)} 支")
    for s in updated_months:
        print(s)

    print(f"\n[AUTO-SYNC] 頻率修正：{len(updated_freq)} 支")
    for s in updated_freq:
        print(s)

    if not changed:
        print("\n[AUTO-SYNC] 全部資料已是最新，無需修正")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
