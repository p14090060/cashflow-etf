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
ROOT    = Path(__file__).parent.parent
BASE    = ROOT / "data" / "_base.json"
DIV     = ROOT / "data" / "dividend_info.json"
OUT     = ROOT / "data" / "market.json"

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
                    prev  = float(y)
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
            cur, prev = float(z), float(y)
            return {
                "price":      round(cur, 2),
                "change_pt":  round(cur - prev, 2),
                "change_pct": round((cur - prev) / prev * 100, 2) if prev > 0 else 0,
                "mis_time":   t[:5] if t else "",
            }
    except Exception as e:
        print(f"[MIS] 大盤失敗: {e}", file=sys.stderr)
    return None

# ── 訊號計算（Task 5：不靠 NAV）────────────────────────────
def calc_signal(price, ma20, ret5d, rsi, vol_ratio):
    if price <= 0 or ma20 <= 0:
        return "dear"
    if ret5d >= 5 or rsi >= 70:
        return "hot"
    if (ret5d < 5
            and price <= ma20 * 1.02
            and 0.5 <= vol_ratio <= 3.0
            and rsi < 70):
        return "fair"
    if price < ma20 * 0.97 and rsi < 40:
        return "cheap"
    return "dear"

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
    calendar = div_info.get("calendar", [])

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

        # 重算訊號（Task 5，不靠 NAV）
        e["signal"] = calc_signal(
            e.get("price",     0),
            e.get("ma20",      0),
            e.get("ret5d",     0),
            e.get("rsi",      50),
            e.get("vol_ratio", 1),
        )
        e.pop("premium", None)   # 移除 NAV 相關欄位

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
