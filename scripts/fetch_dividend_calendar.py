"""
scripts/fetch_dividend_calendar.py
多源除息行事曆抓取：TWSE ETFortune（主）→ FinMind（副）→ MoneyDJ（三源）
- TWSE 金額為 0 時自動向 FinMind 補查
- TWSE + FinMind 都查無時，再試 MoneyDJ HTML 解析
- 三源全無且距除息日 ≤ 7 天 → TG 通知
- amount=null 代表真正查無，前端顯示「待公告」
輸出 data/dividend_calendar.json

收錄母體（2026-11-17 漏收修補）：本輪有效 data/_base.json 的 ETF 全池（與 mis_fetcher 同一套商品政策：
K 尾碼／ETN／無合格 ETF 類型證據一律不收），主動／被動同規則；不再用固定 20 檔白名單。
- 新覆蓋商品只採 TWSE bulk 官方公告：日期照列，官方正額才採，空白／無法判讀 → null（不填 0、不用別期補）。
- 逐檔補查（TWSE per-ETF／FinMind／MoneyDJ）與 TG 告警只限 SUPPLEMENT_CODES（原 20 檔），不因擴池放大。
- 同代號同除息日官方金額矛盾 → null 並告警，不挑其中一筆；保留前值只限同一除息日（不跨期沿用）。
- _base／商品政策讀不到 → 保留現有檔案不寫；bulk 部分月份失敗 → 本輪沒抓到的既有未過期公告保留。
"""
import json, sys, ssl, os, datetime, re, time, urllib.request, urllib.parse
from pathlib import Path

ROOT     = Path(__file__).parent.parent
OUT      = ROOT / "data" / "dividend_calendar.json"
BASE     = ROOT / "data" / "_base.json"
BASE_URL = "https://www.twse.com.tw/rwd/zh/ETFortune/dividendList"
HEADERS  = {"User-Agent": "ETF-dividend-fetcher/1.0 (github.com/p14090060/cashflow-etf)"}

FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN", "")
TG_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
ALERT_DAYS    = 7   # 距除息日 ≤ N 天且查無金額 → 發 TG

# 逐檔補查名單（原 LAZY_WATCHLIST）：只決定誰可以多打 per-ETF／FinMind／MoneyDJ 與 TG 告警，不是收錄白名單
SUPPLEMENT_CODES = LAZY_WATCHLIST = {
    '0050', '0056', '006208', '00878', '00919', '00929', '00940', '00939',
    '00936', '00930', '00932', '00713', '00701', '00850', '00757',
    '00646', '00662', '00679B', '00687B', '00772B',
}

# 人工確認的配息金額（僅在自動源查無時補入，自動源有資料則以官方為準）
_MANUAL_OVERRIDE: dict = {
    "00939": {"amount": 0.072, "amount_source": "Gavin 人工確認"},
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
            amount = None                      # 空白／無法判讀＝金額未定，不是 0
        if amount is not None and not (amount > 0 and amount == amount and amount != float("inf")):
            amount = None                      # 只有官方正額才採用
        results.append({"code": code, "name": cells[1], "ex_dividend_date": ex_date, "amount": amount})
    return results


# bulk 月份「成功」＝確認是本程式支援的官方配息清單（R1 F2）：HTTP 200 的維護頁／登入頁／改版或損壞頁面
# 不是「完整的空清單」，必須計為該月份失敗（沿既有 partial 保留）。合法空結果＝官方表頭完整、tbody 沒有任何資料列。
_REPORT_TABLE_RE = re.compile(r'<table[^>]*\bid="myTable"[^>]*>(.*?)</table>', re.DOTALL | re.IGNORECASE)
_THEAD_RE = re.compile(r'<thead[^>]*>(.*?)</thead>', re.DOTALL | re.IGNORECASE)
_TBODY_RE = re.compile(r'<tbody[^>]*>(.*?)</tbody>', re.DOTALL | re.IGNORECASE)
_REPORT_HEAD = ("證券代號", "證券簡稱", "除息交易日", "收益分配基準日", "收益分配發放日", "收益分配金額")


def _parse_twse_report(html: str):
    """回傳 (rows, None)＝確認為官方清單（rows 可為空＝合法空結果）；(None, 原因)＝不是可用的官方報表。"""
    tables = _REPORT_TABLE_RE.findall(html)
    if len(tables) != 1:
        return None, f"找不到唯一的官方配息表（myTable×{len(tables)}）"
    head, body = _THEAD_RE.search(tables[0]), _TBODY_RE.search(tables[0])
    if not head or not body:
        return None, "官方配息表缺 thead／tbody"
    cols = [strip_tags(m.group(1)) for m in TD_RE.finditer(head.group(1))]
    if len(cols) < 6 or any(not c.startswith(want) for c, want in zip(cols, _REPORT_HEAD)):
        return None, f"官方配息表欄位不符：{cols[:6]}"
    trs = TR_RE.findall(body.group(1))
    rows = _parse_twse_html(body.group(1))
    if len(rows) != len(trs):
        return None, f"官方配息表有 {len(trs) - len(rows)} 列無法判讀（共 {len(trs)} 列）"
    return rows, None


def fetch_twse_bulk(status=None) -> list:
    """status（dict，選填）：寫入 {"failed": 失敗月份數}，供 main 判斷本輪清單是否完整。"""
    today = datetime.date.today()
    all_rows = []
    failed = 0
    d = today.replace(day=1)
    for _ in range(3):
        ds = d.strftime("%Y%m%d")
        try:
            print(f"[TWSE] 抓取 {ds} …")
            req = urllib.request.Request(f"{BASE_URL}?date={ds}", headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
                html = r.read().decode("utf-8")
            rows, why = _parse_twse_report(html)
            if rows is None:
                raise ValueError(f"回應不是可用的官方配息清單（{why}）")
            print(f"[TWSE] 解析 {len(rows)} 筆")
            all_rows.extend(rows)
        except Exception as e:
            print(f"[TWSE] ⚠ {ds} 失敗：{e}", file=sys.stderr)
            failed += 1
        d = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    if status is not None:
        status["failed"] = failed
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
        future = [r for r in rows if r["ex_dividend_date"] >= today_str and (r["amount"] or 0) > 0]
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



# ── Source 4: MoneyDJ ETF 頁面 HTML 解析 ───────────────────────────

_MDJ_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Referer":         "https://www.moneydj.com/",
}
# MoneyDJ ETF 配息表格：col01=除息基準日，col07=每單位配息
_MDJ_DATE_COL_RE = re.compile(r'<td[^>]*class="col01"[^>]*>(\d{4}/\d{1,2}/\d{1,2})</td>')
_MDJ_AMT_COL_RE  = re.compile(r'<td[^>]*class="col07"[^>]*>([\d.]+)</td>')


def fetch_moneydj_dividend(code: str, ex_date_str: str) -> float:
    """
    從 MoneyDJ ETF 基本資料頁解析配息金額。
    以 CSS class col01（除息日）配對 col07（配息金額），不依賴中文關鍵字。
    ex_date_str: 預期除息日 (YYYY-MM-DD)，用來選最接近的紀錄。
    回傳 > 0 表示找到；0.0 表示無資料或解析失敗。
    """
    url = f"https://www.moneydj.com/etf/x/basic/basic0005.xdjhtm?etfid={code}.tw"
    try:
        req = urllib.request.Request(url, headers=_MDJ_HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
            raw = r.read()
        # 頁面是 Big5，但日期/數字是 ASCII，用 replace 不影響定位
        html = raw.decode("utf-8", errors="replace")

        # 收集所有 col01 日期（位置, 日期）
        dates = [
            (m.start(), datetime.date(*map(int, m.group(1).split("/"))))
            for m in _MDJ_DATE_COL_RE.finditer(html)
        ]
        # 收集所有 col07 金額（位置, 金額）—— 只取 ETF 配息合理範圍 0.005~9.99
        amts = []
        for m in _MDJ_AMT_COL_RE.finditer(html):
            try:
                a = float(m.group(1))
                if 0.005 < a < 10.0:
                    amts.append((m.start(), a))
            except ValueError:
                pass

        if not dates or not amts:
            print(f"  [MoneyDJ] {code} col01/col07 未找到資料", file=sys.stderr)
            return 0.0

        # 每個 col01 日期，配對其後最近的 col07 金額（同一 row）
        pairs = []
        for d_pos, d_date in dates:
            after = [(p, a) for p, a in amts if p > d_pos]
            if not after:
                continue
            nearest_pos, nearest_amt = min(after, key=lambda x: x[0] - d_pos)
            # 確保是同一 <tr>：金額在日期後 1500 bytes 內（一個 row 通常 < 500 bytes，留 buffer）
            if nearest_pos - d_pos < 1500:
                pairs.append((d_date, nearest_amt))

        if not pairs:
            print(f"  [MoneyDJ] {code} 日期金額配對失敗", file=sys.stderr)
            return 0.0

        # 優先找與預期除息日 ±45 天內的紀錄
        try:
            ex_dt = datetime.date.fromisoformat(ex_date_str)
            close = [(d, a) for d, a in pairs if abs((d - ex_dt).days) <= 45]
            if close:
                return min(close, key=lambda x: abs((x[0] - ex_dt).days))[1]
        except ValueError:
            pass

        # fallback：最新一筆（清單通常從新到舊排）
        return max(pairs, key=lambda x: x[0])[1]

    except Exception as e:
        print(f"  [MoneyDJ] {code} 失敗：{e}", file=sys.stderr)
    return 0.0


# ── 收錄母體：本輪有效 _base.json 全池 ─────────────────────────────

def load_pool(today):
    """回傳 (合格代號集合, 被政策拿掉的 [(代號, 原因)])；_base 無效、商品政策讀不到、有未核實的拿掉原因
    或母體為空 → (None, 原因)。與 mis_fetcher 同一套政策與安全語意：只有 K 尾碼／排除清單可逐檔拿掉。"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from json_safe import load_strict, validate_base
        import product_policy
        base = load_strict(BASE)
        validate_base(base)
        listed = product_policy.listed_codes()
        evidence = product_policy.load_etf_evidence(as_of=today, listed=listed)
        keep, dropped = product_policy.split_etfs(base["etfs"], listed, evidence)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    # R1 F1：與 MIS 相同的安全語意——只有已核實的不收錄商品（K 尾碼、排除清單）可以拿掉；
    # 缺證據／證據日期異常等未核實原因或空母體 → 本輪不能更新（不縮池發布、不刪既有公告、不推定退市）
    unverified = [(c, r) for c, r in dropped if r not in ("suffix-K", "excluded-list")]
    if unverified or not keep:
        return None, f"{len(unverified)} 檔沒有有效的 ETF 類型證據 {unverified[:10]}" if unverified else "合格母體為空"
    return {e["code"] for e in keep}, dropped


# ── Main ────────────────────────────────────────────────────────────

def main():
    today     = datetime.date.today()
    today_str = today.isoformat()
    print(f"[DIV-CAL] 除息行事曆抓取 ({today_str})")

    # Step 0: 收錄母體＝本輪有效 _base.json 全池（不再用固定 20 檔）
    pool, dropped = load_pool(today)
    if pool is None:
        print(f"::warning::[DIV-CAL] 無法確認收錄母體（_base.json／商品政策／類型證據：{dropped}），保留現有檔案、本輪不請求不寫", file=sys.stderr)
        sys.exit(0)
    print(f"[DIV-CAL] 收錄母體：_base.json 合格 ETF {len(pool)} 檔（政策拿掉 {len(dropped)} 檔）")

    # Step 1: TWSE bulk
    bulk_status: dict = {}
    all_rows = fetch_twse_bulk(bulk_status)
    if not all_rows:
        print("[DIV-CAL] ⚠ 無任何資料，保留現有檔案", file=sys.stderr)
        sys.exit(0)

    # 篩選全池 + 未來日期；同代號取最近未來日期
    max_future = (today + datetime.timedelta(days=730)).isoformat()
    by_date: dict = {}
    for row in all_rows:
        code = row["code"]
        if code not in pool:
            continue
        iso = row["ex_dividend_date"]
        if iso < today_str:
            continue
        if iso > max_future:
            print(f"[SKIP] {code} 除息日 {iso} 疑似 ROC 日期解析錯誤（超過2年），略過")
            continue
        by_date.setdefault(code, {}).setdefault(iso, []).append(row)

    candidates: dict = {}
    conflicts: set = set()      # 同代號同除息日官方金額矛盾：不挑、不補查、不保留前值
    for code, dates in by_date.items():
        iso  = min(dates)
        rows = dates[iso]
        amounts = sorted({r["amount"] for r in rows if r["amount"] is not None})
        if len(amounts) > 1:
            conflicts.add(code)
            print(f"::warning::[CONFLICT] {code} 除息日 {iso} 官方金額矛盾 {amounts}，不挑其中一筆，金額 null")
            amount = None
        else:
            amount = amounts[0] if amounts else None
        candidates[code] = {
            **rows[0],
            "amount":        amount,
            "amount_source": "TWSE" if amount is not None else None,
        }

    # Step 2: 距除息日 ≤ 14 天 → 強制雙源查詢（TWSE × FinMind）
    # 只限補查名單（原 20 檔）：擴池不增加逐檔請求與 TG 告警；新覆蓋商品等 bulk 自然更新
    DUAL_DAYS = 14
    dual_targets = [
        c for c, d in candidates.items()
        if c in SUPPLEMENT_CODES and c not in conflicts
        and (datetime.date.fromisoformat(d["ex_dividend_date"]) - today).days <= DUAL_DAYS
    ]

    alerts = []
    if dual_targets:
        print(f"\n[DIV-CAL] {len(dual_targets)} 支進入 {DUAL_DAYS} 天雙源核查視窗…")

        for code in dual_targets:
            entry     = candidates[code]
            ex_date   = entry["ex_dividend_date"]
            days_left = (datetime.date.fromisoformat(ex_date) - today).days
            twse_amt  = entry.get("amount") or 0.0

            # 若 TWSE bulk 無金額，先試 TWSE per-ETF
            if twse_amt == 0:
                time.sleep(0.5)
                twse_amt = fetch_twse_per_etf(code, today_str)
                if twse_amt > 0:
                    print(f"  [TWSE-ETF] {code} 補到 {twse_amt:.4f} 元")

            # 一律查 FinMind（雙源核對）
            time.sleep(0.3)
            fm_amt = fetch_finmind_dividend(code)

            # 比對並設定來源
            if twse_amt > 0 and fm_amt > 0:
                diff = abs(twse_amt - fm_amt) / twse_amt
                if diff <= 0.05:
                    entry["amount"]        = twse_amt
                    entry["amount_source"] = "TWSE × FinMind 核實"
                    print(f"  [OK]  {code} TWSE={twse_amt} FM={fm_amt} 雙源吻合")
                else:
                    entry["amount"]        = twse_amt  # 以 TWSE 為準
                    entry["amount_source"] = f"TWSE（FinMind 差異 {diff*100:.0f}%）"
                    print(f"  [DIFF] {code} TWSE={twse_amt} vs FM={fm_amt} 差 {diff*100:.0f}%")
            elif twse_amt > 0:
                entry["amount"]        = twse_amt
                entry["amount_source"] = "TWSE"
                print(f"  [TWSE] {code} {twse_amt:.4f} 元（FinMind 無資料）")
            elif fm_amt > 0:
                entry["amount"]        = fm_amt
                entry["amount_source"] = "FinMind（估算）"
                print(f"  [FM]   {code} {fm_amt:.4f} 元（TWSE 無資料）")
            else:
                # 先查人工確認值，有的話直接套用，不發 TG
                if code in _MANUAL_OVERRIDE:
                    entry.update(_MANUAL_OVERRIDE[code])
                    print(f"  [MANUAL] {code} 自動源查無，套用人工確認值 {_MANUAL_OVERRIDE[code]['amount']}")
                else:
                    # Source 4: MoneyDJ HTML 解析
                    time.sleep(0.5)
                    mj_amt = fetch_moneydj_dividend(code, ex_date)
                    if mj_amt > 0:
                        entry["amount"]        = mj_amt
                        entry["amount_source"] = "MoneyDJ"
                        print(f"  [MoneyDJ] {code} {mj_amt:.4f} 元")
                    else:
                        entry["amount"]        = None
                        entry["amount_source"] = None
                        print(f"  [NO DATA] {code} 除息日 {ex_date}，距今 {days_left} 天，所有來源查無金額")
                        if days_left <= ALERT_DAYS:
                            alerts.append((code, entry.get("name", code), ex_date, days_left))

    if alerts:
        lines = ["⚠️ 配息金額查無通知"]
        for code, name, ex_date, days_left in alerts:
            lines.append(f"• {code} {name}\n  除息日 {ex_date}（距今 {days_left} 天）")
        lines.append("TWSE ETFortune 及 FinMind 均查無配息金額，請人工確認")
        notify_tg("\n".join(lines))

    # 套用人工確認值（僅在自動源查無時補入）
    for code, override in _MANUAL_OVERRIDE.items():
        if code in candidates and code not in conflicts and candidates[code].get("amount") is None:
            candidates[code].update(override)
            print(f"  [MANUAL] {code} 自動源查無，套用人工確認值 {override['amount']}")

    # 保留前值：若本次查無（null）但舊檔「同一除息日」已有有效金額，不倒退覆蓋
    # 避免第二次執行因 TWSE 回傳空值而把已知正確金額洗掉；不同除息日＝另一期，不跨期沿用舊金額
    if OUT.exists():
        try:
            old_data = json.load(open(OUT, encoding="utf-8"))
            old_etfs = old_data.get("etfs", {})
            for code, entry in candidates.items():
                if entry.get("amount") is None and code not in conflicts:
                    old = old_etfs.get(code, {})
                    old_amt = old.get("amount")
                    valid = isinstance(old_amt, (int, float)) and not isinstance(old_amt, bool) and old_amt > 0
                    if old.get("ex_dividend_date") != entry["ex_dividend_date"]:
                        if valid:
                            print(f"  [NO-CARRY] {code} 舊金額 {old_amt} 屬 {old.get('ex_dividend_date')}，"
                                  f"不帶到新除息日 {entry['ex_dividend_date']}")
                        continue
                    if valid:
                        entry["amount"]        = old_amt
                        entry["amount_source"] = (old.get("amount_source") or "") + "（保留前值）"
                        print(f"  [KEEP] {code} 本次查無，保留前值 {old_amt}")
            # bulk 有月份抓取失敗：本輪清單可能不完整 → 既有未過期公告（仍在母體內）不被新清單洗掉
            if bulk_status.get("failed"):
                for code, old in old_etfs.items():
                    if code not in pool or not isinstance(old, dict):
                        continue
                    old_iso = old.get("ex_dividend_date")
                    if not isinstance(old_iso, str) or not (today_str <= old_iso <= max_future):
                        continue
                    new = candidates.get(code)
                    if new is None or old_iso < new["ex_dividend_date"]:
                        candidates[code] = old
                        print(f"  [KEEP-PARTIAL] {code} bulk 有 {bulk_status['failed']} 個月份失敗，保留既有公告 {old_iso}")
        except Exception as e:
            print(f"  [KEEP] 讀取舊檔失敗: {e}", file=sys.stderr)

    # 印出結果
    print(f"\n[DIV-CAL] 全池有公告：{len(candidates)} 支")
    for code, d in sorted(candidates.items(), key=lambda x: x[1]["ex_dividend_date"]):
        amt = d.get("amount")
        amt_str = f"{amt:.4f} 元" if amt is not None else "待公告"
        src_str = d.get("amount_source") or "--"
        print(f"  {code:8s}  {d['name']:<22s}  {d['ex_dividend_date']}  {amt_str}  [{src_str}]")

    output = {
        "_meta": {
            "last_updated": today_str,
            "sources":      "TWSE ETFortune → TWSE per-ETF → FinMind → MoneyDJ",
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
