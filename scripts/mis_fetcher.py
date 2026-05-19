"""
scripts/mis_fetcher.py
每 10 分鐘由 GitHub Actions 執行。
讀 data/_base.json（每日基線）＋ data/dividend_info.json（配息靜態）
→ 視盤況決定是否疊上 MIS 即時資料
→ 輸出 data/market.json（前端讀這個）
"""

import json, sys, time, ssl, datetime
import urllib.request as _ur
from pathlib import Path

# ── 路徑 ────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
BASE        = ROOT / "data" / "_base.json"
DIV         = ROOT / "data" / "dividend_info.json"
DIV_CAL     = ROOT / "data" / "dividend_calendar.json"    # TWSE 官方公告
MANUAL_CAL  = ROOT / "data" / "manual_calendar.json"      # 人工核實（不被 Action 覆蓋）
OUT         = ROOT / "data" / "market.json"

FREQ_MAP = {"月配": 12, "季配": 4, "半年配": 2, "年配": 1, "不配息": 0}

# ── MIS API ──────────────────────────────────────────────
MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ETF-fetcher/1.0)"}
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode    = ssl.CERT_NONE

# ── 時間判斷 ──────────────────────────────────────────────
def tw_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

def is_weekday(now=None):
    return (now or tw_now()).weekday() < 5   # 0=Mon … 4=Fri

def is_trading_hour(now=None):
    n = now or tw_now()
    if n.weekday() >= 5:
        return False
    t = n.hour * 60 + n.minute
    return 540 <= t <= 810          # 09:00 ~ 13:30

# ── MIS 資料抓取 ──────────────────────────────────────────
def _fetch_url(url):
    req = _ur.Request(url, headers=HEADERS)
    with _ur.urlopen(req, timeout=12, context=SSL_CTX) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_mis_etfs(codes):
    """
    codes: list of str（ETF 代碼，台股 ETF 幾乎全為上市 tse）
    回傳 {code: {price, vol, change_pt, change_pct, mis_time}}
    每批 20 支，批次間等 3 秒
    """
    results, batch_size = {}, 20
    batches = [codes[i:i+batch_size] for i in range(0, len(codes), batch_size)]
    for idx, batch in enumerate(batches):
        if idx > 0:
            time.sleep(3)
        ex_ch = "|".join(f"tse_{c}.tw" for c in batch)
        try:
            d = _fetch_url(f"{MIS_URL}?json=1&delay=0&ex_ch={ex_ch}")
            for item in d.get("msgArray", []):
                code = str(item.get("c", "")).strip()
                z    = item.get("z", "-")
                y    = item.get("y", "-")
                v    = item.get("v", "-")
                t    = item.get("t", "")
                if not code or not z or z == "-":
                    continue
                try:
                    price = float(z)
                    prev  = float(y) if y and y != "-" else price
                    vol   = float(str(v).replace(",", "")) if v and v != "-" else 0
                    results[code] = {
                        "price":      price,
                        "vol":        vol,
                        "change_pt":  round(price - prev, 2),
                        "change_pct": round((price - prev) / prev * 100, 2) if prev > 0 else 0,
                        "mis_time":   t[:5] if t else "",
                    }
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            print(f"[MIS] batch {idx} 失敗: {e}", file=sys.stderr)
    return results

def fetch_mis_market():
    """抓加權指數（tse_t00.tw）"""
    try:
        d    = _fetch_url(f"{MIS_URL}?json=1&delay=0&ex_ch=tse_t00.tw")
        item = d.get("msgArray", [{}])[0]
        z, y, t = item.get("z","-"), item.get("y","-"), item.get("t","")
        if z and z != "-":
            cur, prev = float(z), (float(y) if y and y != "-" else float(z))
            return {
                "price":      round(cur, 2),
                "change_pt":  round(cur - prev, 2),
                "change_pct": round((cur - prev) / prev * 100, 2) if prev > 0 else 0,
                "mis_time":   t[:5] if t else "",
            }
    except Exception as e:
        print(f"[MIS] 大盤失敗: {e}", file=sys.stderr)
    return None

# ── 訊號計算（與 fetch_etf.py 統一：ma60 + RSI，不靠 NAV）──
_HIGH_DIV_KW = ["高股息", "高息", "精選高息", "永續高息", "價值高息"]

def calc_signal(price, ma20, ma60, low52, high52, ret5d, vol_ratio, rsi, yld, name):
    if price <= 0 or ma60 <= 0:
        return "dear"
    pos52 = (price - low52) / (high52 - low52) if high52 > low52 else 0.5
    maD60 = round((price - ma60) / ma60 * 100, 1) if ma60 > 0 else 0

    if ret5d >= 5 or rsi >= 75:
        return "hot"
    if pos52 > 0.78 or price > ma60 * 1.06:
        return "dear"

    is_high_div = any(k in name for k in _HIGH_DIV_KW) or yld > 5
    conds = [price <= ma60 * 1.03, ret5d < 5, 0.5 <= vol_ratio <= 3.0, rsi < 75]
    if is_high_div:
        conds.append(yld > 5)
    if all(conds):
        return "fair"

    if pos52 < 0.40 and maD60 < -2:
        return "cheap"
    return "dear"

# ── 殖利率反算（Plan C）─────────────────────────────────
def calc_yield_with_source(code: str, price: float,
                           div_etfs: dict, div_cal_etfs: dict) -> tuple:
    """
    回傳 (yld_pct, yld_source, yld_label)
    優先順序：TWSE 官方公告 → 歷史平均 → 無資料
    """
    if price <= 0:
        return 0.0, "none", "無配息紀錄"

    info       = div_etfs.get(code, {})
    frequency  = info.get("frequency", "季配")
    multiplier = FREQ_MAP.get(frequency, 4)

    if multiplier == 0:
        return 0.0, "none", "無配息紀錄"

    # 優先 1：TWSE 官方公告
    cal = div_cal_etfs.get(code)
    if cal:
        annual = cal["amount"] * multiplier
        yld    = round(annual / price * 100, 2)
        return yld, "official", "TWSE 官方公告推算"

    # 優先 2：歷史平均
    avg = info.get("avg_dividend_per_share") or 0
    if avg > 0:
        annual = avg * multiplier
        yld    = round(annual / price * 100, 2)
        return yld, "historical", "歷史平均估算"

    return 0.0, "none", "無配息紀錄"


# ── 行事曆合併（官方 > 人工核實 > yfinance 估算）────────────────────────────
def build_calendar(div_info_cal: list, div_cal_etfs: dict,
                   manual_etfs: dict, div_info_etfs: dict) -> list:
    """
    優先順序：TWSE 官方公告 > manual_calendar.json（人工核實）> yfinance 估算
    yfinance 估算多一道月份合法性過濾：預測月份不在 dividend_info.json 的 months 清單時剔除。
    """
    today = datetime.date.today()
    result = []
    covered = set()   # 已有正確日期的代號（官方 or 人工）

    # 金額備用：優先 manual > yfinance，官方金額為 0 時使用
    amt_fallback = {item["code"]: item["amt"]
                    for item in div_info_cal if item.get("amt")}
    for code, d in manual_etfs.items():
        if d.get("amount"):
            amt_fallback[code] = d["amount"]

    def _append(code, name, ex_date, amt, source):
        days_left = (ex_date - today).days
        if days_left < 0:
            return
        if not amt:
            amt = amt_fallback.get(code, 0)
        result.append({
            "code":       code,
            "name":       name,
            "day":        str(ex_date.day),
            "mon":        f"{ex_date.month}月",
            "amt":        amt,
            "soon":       days_left <= 14,
            "days_until": days_left,
            "source":     source,
        })
        covered.add(code)

    # 1. TWSE 官方公告
    for code, d in div_cal_etfs.items():
        try:
            ex_date = datetime.date.fromisoformat(d["ex_dividend_date"])
        except (ValueError, KeyError):
            continue
        _append(code, d["name"], ex_date, d["amount"], "official")

    # 2. 人工核實（覆蓋 yfinance，但不蓋掉官方）
    for code, d in manual_etfs.items():
        if code in covered:
            continue
        try:
            ex_date = datetime.date.fromisoformat(d["ex_dividend_date"])
        except (ValueError, KeyError):
            continue
        _append(code, d["name"], ex_date, d["amount"], "manual")

    # 3. yfinance 估算（官方/人工已涵蓋的略過；月份不符的剔除）
    for item in div_info_cal:
        code = item.get("code", "")
        if code in covered:
            continue
        iso = item.get("iso_date", "")
        if not iso:
            continue
        try:
            ex_date = datetime.date.fromisoformat(iso)
        except ValueError:
            continue
        # 月份合法性過濾：dividend_info.json 有設 months 時，月份必須吻合
        known_months = div_info_etfs.get(code, {}).get("months", [])
        if known_months and ex_date.month not in known_months:
            continue
        days_left = (ex_date - today).days
        if days_left < 0:
            continue
        result.append({
            "code":       code,
            "name":       item.get("name", ""),
            "day":        str(ex_date.day),
            "mon":        f"{ex_date.month}月",
            "amt":        item.get("amt", 0),
            "soon":       days_left <= 14,
            "days_until": days_left,
            "source":     "estimate",
        })

    return sorted(result, key=lambda x: x["days_until"])


# ── 工具 ─────────────────────────────────────────────────
def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[LOAD] {path} 失敗: {e}", file=sys.stderr)
        return None

# ── 主流程 ────────────────────────────────────────────────
def main():
    now      = tw_now()
    today    = now.date()
    trading  = is_trading_hour(now)
    weekday  = is_weekday(now)
    holiday  = not weekday

    # 讀基線
    base = load_json(BASE)
    if base is None:
        print("[ERROR] data/_base.json 不存在，請先執行 fetch_etf.py", file=sys.stderr)
        sys.exit(1)

    # 讀配息靜態資料
    div_info = load_json(DIV) or {}
    div_etfs = div_info.get("etfs", {})

    # 讀官方公告（若尚未建立則 fallback 空 dict）
    div_cal      = load_json(DIV_CAL) or {}
    div_cal_etfs = div_cal.get("etfs", {})
    if div_cal_etfs:
        print(f"[DIV_CAL] 載入官方公告 {len(div_cal_etfs)} 支")

    # 讀人工核實日期
    manual_cal  = load_json(MANUAL_CAL) or {}
    manual_etfs = manual_cal.get("etfs", {})
    if manual_etfs:
        print(f"[MANUAL_CAL] 載入人工核實 {len(manual_etfs)} 支")

    # 合併行事曆：官方 > 人工核實 > yfinance 估算
    calendar = build_calendar(
        div_info.get("calendar", []), div_cal_etfs,
        manual_etfs, div_etfs,
    )

    base_etfs = {e["code"]: e for e in base.get("etfs", [])}

    # ── 情況 a) 盤中：抓 MIS ──
    mis_data   = {}
    mis_market = None
    mis_ok     = False

    if trading:
        codes      = [e["code"] for e in base.get("etfs", [])]
        mis_data   = fetch_mis_etfs(codes)
        mis_market = fetch_mis_market()
        mis_ok     = len(mis_data) > 0
        print(f"[MIS] 抓到 {len(mis_data)} 支即時資料，大盤={'OK' if mis_market else 'FAIL'}")

    # ── 合併 ETF ──
    etfs_out = []
    for code, b in base_etfs.items():
        e = dict(b)

        # 疊上 MIS 即時資料（盤中）
        if mis_ok and code in mis_data:
            m = mis_data[code]
            e["price"]      = m["price"]
            e["change_pt"]  = m["change_pt"]
            e["change_pct"] = m["change_pct"]
            e["cur_vol"]    = m["vol"]
            e["mis_time"]   = m["mis_time"]
            avg = e.get("avg_vol", 0)
            e["vol_ratio"]  = round(m["vol"] / avg, 2) if avg > 0 else 1.0

        # 疊上配息靜態資料
        d = div_etfs.get(code, {})
        if d:
            e["div_frequency"]     = d.get("frequency", e.get("div_freq", "不明"))
            e["div_months"]        = d.get("months", [])
            e["div_avg_per_share"] = d.get("avg_dividend_per_share")
            e["div_category"]      = d.get("category", "")
            e["div_todo"]          = d.get("_todo", True)
            e.pop("div_freq", None)

        # 官方公告金額/日期 → 覆蓋 yfinance 的 est 和 days
        if code in div_cal_etfs:
            official = div_cal_etfs[code]
            if official.get("amount", 0) > 0:
                e["est"] = official["amount"]
            try:
                ex_date = datetime.date.fromisoformat(official["ex_dividend_date"])
                days_left = (ex_date - today).days
                if days_left >= 0:
                    e["days"] = days_left
            except (ValueError, KeyError):
                pass

        # 重算訊號（不靠 NAV，與 fetch_etf.py 同一套邏輯）
        e["signal"] = calc_signal(
            e.get("price",     0),
            e.get("ma20",      0),
            e.get("ma60",      0),
            e.get("low52",     0),
            e.get("high52",    0),
            e.get("ret5d",     0),
            e.get("vol_ratio", 1),
            e.get("rsi",      50),
            e.get("yld",       0),
            e.get("name",     ""),
        )
        e.pop("premium", None)   # 移除 NAV 相關欄位

        # 殖利率反算（Plan C：官方公告 → 歷史平均 → 無資料）
        yld, yld_src, yld_lbl = calc_yield_with_source(
            code, e.get("price", 0), div_etfs, div_cal_etfs
        )
        if yld > 0:
            e["yld"] = yld          # 覆寫 _base.json 原始值
        e["yld_source"] = yld_src
        e["yld_label"]  = yld_lbl

        etfs_out.append(e)

    # ── 大盤 ──
    market_out = dict(base.get("market", {}))
    if mis_ok and mis_market:
        market_out.update(mis_market)

    # ── 狀態旗標 ──
    # 情況 a) 盤中 MIS 成功：is_closed=false
    # 情況 b) 平日盤後 MIS 空：is_closed=true, is_holiday=false
    # 情況 c) 假日：is_closed=true, is_holiday=true
    is_closed = not (trading and mis_ok)

    output = {
        "updated":           now.strftime("%Y-%m-%d %H:%M"),
        "is_closed":         is_closed,
        "is_holiday":        holiday,
        "last_trading_time": "13:30" if (is_closed and weekday) else None,
        "market":            market_out,
        "etfs":              etfs_out,
        "calendar":          calendar,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    status = "盤中 MIS" if mis_ok else ("收盤" if weekday else "假日")
    print(f"[OK] data/market.json 完成（{status}，ETF {len(etfs_out)} 支）")


if __name__ == "__main__":
    main()
