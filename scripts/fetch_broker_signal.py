#!/usr/bin/env python3
"""
fetch_broker_signal.py — 分點均價篩選器

取 ETF 成分股 → 抓 TWSE 各券商分點 120 日買賣資料
→ 計算加權平均成本 → 找現價低於分點均價的個股
→ 輸出 data/broker_signal.json

快取機制：已抓到的 (股票代碼, 日期) 不再重抓，每日只追加最新一天。
初次執行需時較長（120 日 × N 檔），之後每日 < 1 分鐘。

用法：
    python scripts/fetch_broker_signal.py          # 一般執行（增量）
    python scripts/fetch_broker_signal.py --full   # 強制重抓全部（初始化時用）
"""

import json
import sys
import time
import os
from datetime import date, timedelta
from pathlib import Path

import requests
import yfinance as yf

# ── 設定 ──────────────────────────────────────────────────
TARGET_ETFS = ["0050", "006208", "0056", "00878", "00919", "00929"]
LOOKBACK    = 120           # 分析天數（交易日）
DELAY       = 0.6           # TWSE 每次請求間隔（秒），避免被擋
MAX_STOCKS  = 150           # 最多處理幾檔（防 Action 超時）
MIN_DISCOUNT = 0.0          # 只輸出折扣 > 0% 的個股（低於均價才算）

ROOT   = Path(__file__).parent.parent
CACHE  = ROOT / "data" / "_broker_cache.json"
OUTPUT = ROOT / "data" / "broker_signal.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":    "https://www.twse.com.tw/",
}

# ── 取得 ETF 成分股 ─────────────────────────────────────────
def get_etf_components():
    """從 TWSE 取多檔 ETF 成分股，回傳不重複的 (代碼, 名稱) dict。"""
    stocks = {}
    for etf in TARGET_ETFS:
        try:
            url  = (f"https://www.twse.com.tw/rwd/zh/ETF/getETFComponentStocks"
                    f"?stockNo={etf}&response=json")
            resp = requests.get(url, headers=HEADERS, timeout=10)
            data = resp.json()
            for row in data.get("data", []):
                code = str(row[0]).strip()
                name = str(row[1]).strip() if len(row) > 1 else code
                if code and code.isdigit() and len(code) in (4, 5, 6):
                    stocks[code] = name
            print(f"  [{etf}] {len(data.get('data', []))} 檔成分股", flush=True)
            time.sleep(0.5)
        except Exception as e:
            print(f"  [{etf}] 抓取失敗: {e}", flush=True)
    return stocks

# ── 取得過去 N 個交易日日期 ──────────────────────────────────
def get_trading_dates(n=LOOKBACK + 20):
    """用大盤指數取最近 N 個有成交的日期，格式 YYYYMMDD。"""
    try:
        hist  = yf.download("^TWII", period="9mo", interval="1d",
                            progress=False, auto_adjust=True)
        dates = hist.index.strftime("%Y%m%d").tolist()
        return dates[-(n):]
    except Exception as e:
        print(f"  [日期] 取得失敗: {e}", flush=True)
        return []

# ── 抓單一股票單日的分點資料 ─────────────────────────────────
def fetch_broker_day(code, date_str):
    """
    回傳 (buy_shares, sell_shares) 或 None（抓不到）。
    TWSE TWT44U：個股各券商分點買賣彙總，股數單位。
    """
    url = (f"https://www.twse.com.tw/rwd/zh/fund/TWT44U"
           f"?reportType=day&stockNo={code}&date={date_str}&response=json")
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                return None
            body = resp.json()
            if body.get("stat") != "OK":
                return None
            total_buy  = 0
            total_sell = 0
            for row in body.get("data", []):
                # fields: 券商代號, 券商名稱, 買進股數, 賣出股數, 買賣差股數
                try:
                    b = int(str(row[2]).replace(",", "") or 0)
                    s = int(str(row[3]).replace(",", "") or 0)
                    total_buy  += b
                    total_sell += s
                except (ValueError, IndexError):
                    pass
            return (total_buy, total_sell)
        except Exception:
            time.sleep(1)
    return None

# ── 載入快取 ────────────────────────────────────────────────
def load_cache():
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_cache(cache):
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

# ── 主流程 ──────────────────────────────────────────────────
def main():
    force_full = "--full" in sys.argv
    print("=== 分點均價篩選器 ===", flush=True)

    # 1. ETF 成分股
    print("[1/4] 取 ETF 成分股...", flush=True)
    stocks = get_etf_components()
    if not stocks:
        print("  ❌ 無成分股，中止", flush=True)
        sys.exit(1)
    codes = list(stocks.keys())[:MAX_STOCKS]
    print(f"  共 {len(codes)} 檔（最多 {MAX_STOCKS} 檔）", flush=True)

    # 2. 交易日清單
    print("[2/4] 取交易日期...", flush=True)
    all_dates    = get_trading_dates(LOOKBACK + 30)
    trade_dates  = all_dates[-LOOKBACK:]     # 最近 120 個交易日
    if len(trade_dates) < LOOKBACK:
        print(f"  ⚠ 只取到 {len(trade_dates)} 天，繼續執行", flush=True)
    print(f"  {trade_dates[0]} ~ {trade_dates[-1]}", flush=True)

    # 3. 增量抓分點資料
    print("[3/4] 抓分點資料（有快取的跳過）...", flush=True)
    cache = {} if force_full else load_cache()

    # 清除快取中超出 120 日範圍的舊資料
    cutoff = trade_dates[0]
    for c in list(cache.keys()):
        cache[c] = {d: v for d, v in cache[c].items() if d >= cutoff}

    fetched = 0
    for ci, code in enumerate(codes):
        need = [d for d in trade_dates if d not in cache.get(code, {})]
        if not need:
            continue
        if code not in cache:
            cache[code] = {}
        for d in need:
            result = fetch_broker_day(code, d)
            if result:
                cache[code][d] = {"b": result[0], "s": result[1]}
            fetched += 1
            time.sleep(DELAY)
        if ci % 10 == 0:
            save_cache(cache)      # 每 10 檔存一次，防止中途崩潰
            print(f"  進度 {ci+1}/{len(codes)}，已抓 {fetched} 筆", flush=True)

    save_cache(cache)
    print(f"  完成，共抓 {fetched} 筆新資料", flush=True)

    # 4. 取現價 + 計算 120 日分點均價
    print("[4/4] 取現價 + 計算均價...", flush=True)
    tickers_yf = [f"{c}.TW" for c in codes]
    try:
        hist_all = yf.download(tickers_yf, period="6mo", interval="1d",
                               progress=False, auto_adjust=True)
        close_all = hist_all["Close"] if "Close" in hist_all else hist_all.get("close", None)
    except Exception as e:
        print(f"  ⚠ yfinance 批次下載失敗: {e}", flush=True)
        close_all = None

    results = []
    for code in codes:
        name = stocks.get(code, code)
        cdata = cache.get(code, {})

        # 取最新現價
        cur_price = None
        try:
            col = f"{code}.TW"
            if close_all is not None and col in close_all.columns:
                series = close_all[col].dropna()
                if not series.empty:
                    cur_price = float(series.iloc[-1])
        except Exception:
            pass
        if not cur_price:
            try:
                tk = yf.Ticker(f"{code}.TW")
                cur_price = tk.fast_info.last_price
            except Exception:
                pass
        if not cur_price:
            continue

        # 計算 120 日分點加權均價
        # 公式：所有買方買進股數加權，以當日收盤價為代理成本
        total_buy_shares = 0
        total_buy_value  = 0.0
        for d in trade_dates:
            if d not in cdata:
                continue
            buy_s = cdata[d].get("b", 0)
            if buy_s <= 0:
                continue
            # 找對應日期的收盤價
            try:
                dt_str = f"{d[:4]}-{d[4:6]}-{d[6:]}"
                col = f"{code}.TW"
                if close_all is not None and col in close_all.columns:
                    if dt_str in close_all.index.strftime("%Y-%m-%d"):
                        idx = close_all.index.strftime("%Y-%m-%d").tolist().index(dt_str)
                        day_price = float(close_all[col].iloc[idx])
                        if day_price > 0:
                            total_buy_shares += buy_s
                            total_buy_value  += buy_s * day_price
            except Exception:
                pass

        if total_buy_shares < 1000:   # 資料太少跳過
            continue

        avg_cost = total_buy_value / total_buy_shares

        if cur_price >= avg_cost:     # 現價高於均價，不列入
            continue

        discount_pct = (avg_cost - cur_price) / avg_cost * 100

        if discount_pct < MIN_DISCOUNT:
            continue

        results.append({
            "code":     code,
            "name":     name,
            "price":    round(cur_price, 1),
            "avg":      round(avg_cost, 1),
            "discount": round(discount_pct, 1),
        })

    # 依折扣由大到小排序
    results.sort(key=lambda x: x["discount"], reverse=True)

    out = {
        "updated": date.today().strftime("%Y-%m-%d"),
        "lookback_days": LOOKBACK,
        "count": len(results),
        "data": results,
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 完成：{len(results)} 檔低於分點均價 → {OUTPUT}", flush=True)
    for r in results[:10]:
        print(f"  {r['name']:12s}  現:{r['price']:>8.1f}  均:{r['avg']:>8.1f}  -{r['discount']:.1f}%",
              flush=True)


if __name__ == "__main__":
    main()
