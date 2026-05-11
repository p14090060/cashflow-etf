import json, datetime, requests
import yfinance as yf

ETFS = [
    ("0056",   "元大高股息"),
    ("00713",  "台灣高息低波"),
    ("0050",   "元大台灣50"),
    ("00919",  "群益台灣精選高息"),
    ("006208", "富邦台50"),
    ("00981A", "統一台股增長"),
    ("00878",  "國泰永續高息"),
    ("00940",  "元大台灣價值高息"),
    ("00929",  "復華台灣科技優息"),
    ("00850",  "元大ESG永續"),
]

SUFFIX = ".TW"

HIGH_DIV_KEYWORDS = ["高股息", "高息", "精選高息", "永續高息", "價值高息"]

# 手動維護：近期配息天數 & 預估金額（每季更新）
DIV_DAYS = {
    "0056":47, "00713":88, "0050":145, "00919":32,
    "006208":158, "00981A":55, "00878":65, "00940":28,
    "00929":19, "00850":112,
}
DIV_EST = {
    "0056":1.10, "00713":1.05, "0050":3.50, "00919":0.45,
    "006208":2.10, "00981A":0.40, "00878":0.38, "00940":0.32,
    "00929":0.42, "00850":0.80,
}

def is_high_div(name, yld):
    return any(k in name for k in HIGH_DIV_KEYWORDS) or yld > 5

def fetch_nav_twse(code):
    """從 TWSE 公開資訊觀測站抓 ETF 前一日淨值，失敗回傳 None"""
    try:
        clean = ''.join(c for c in code if c.isdigit())
        url = f"https://www.twse.com.tw/fund/ETF_SEARCH?response=json&etfNo={clean}"
        r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        d = r.json()
        if d.get("stat") == "OK" and d.get("data"):
            for row in d["data"]:
                for cell in reversed(row):
                    try:
                        val = float(str(cell).replace(",", ""))
                        if 1 < val < 10000:
                            return val
                    except Exception:
                        pass
    except Exception as e:
        print(f"  [NAV] {code} TWSE 抓取失敗: {e}")
    return None

def calc_signal(price, ma20, ma60, low52, high52, premium, ret5d, vol_ratio, yld, name):
    pos52 = (price - low52) / (high52 - low52) if high52 > low52 else 0.5
    maD60 = round((price - ma60) / ma60 * 100, 1) if ma60 > 0 else 0

    # 過熱：近5日漲幅過大 或 溢價偏高
    if ret5d >= 5 or premium >= 2:
        return "hot", maD60

    # 偏貴：52週高位 或 遠高於60均線
    if pos52 > 0.78 or price > ma60 * 1.06:
        return "dear", maD60

    # 合理價：全部條件通過
    conds = [
        premium < 1,
        price <= ma20 * 1.02,
        ret5d < 5,
        vol_ratio > 0.5,
    ]
    if is_high_div(name, yld):
        conds.append(yld > 5)

    if all(conds):
        return "fair", maD60

    # 便宜：低位且明顯低於均線
    if pos52 < 0.30 and maD60 < -3:
        return "cheap", maD60

    return "dear", maD60

results = []
for code, name in ETFS:
    ticker_code = code + SUFFIX
    try:
        tk = yf.Ticker(ticker_code)
        hist = tk.history(period="1y")
        if hist.empty:
            raise ValueError("no data")

        price    = round(float(hist["Close"].iloc[-1]), 2)
        low52    = round(float(hist["Low"].min()), 2)
        high52   = round(float(hist["High"].max()), 2)
        ma60     = round(float(hist["Close"].tail(60).mean()), 2)
        ma20     = round(float(hist["Close"].tail(20).mean()), 2)
        ret5d    = round(float((hist["Close"].iloc[-1] / hist["Close"].iloc[-6] - 1) * 100), 2) if len(hist) >= 6 else 0.0
        avg_vol  = float(hist["Volume"].tail(20).mean())
        cur_vol  = float(hist["Volume"].iloc[-1])
        vol_ratio = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        # NAV：優先 TWSE，fallback 前一日收盤
        nav = fetch_nav_twse(code) or round(float(hist["Close"].iloc[-2]), 2)
        premium = round((price - nav) / nav * 100, 2) if nav > 0 else 0.0

        # 殖利率
        try:
            info = tk.fast_info
            yld = round(getattr(info, "dividend_yield", 0) * 100, 1)
        except Exception:
            yld = 0.0

        signal, maD = calc_signal(price, ma20, ma60, low52, high52,
                                   premium, ret5d, vol_ratio, yld, name)

        # 熱度分數：用於 TOP 10 排序
        heat = round(vol_ratio * max(1.0, 1 + ret5d * 0.1), 3)

        results.append({
            "code": code, "name": name,
            "price": price, "ma60": ma60, "ma20": ma20,
            "low52": low52, "high52": high52,
            "yld": yld, "days": DIV_DAYS.get(code, 90),
            "est": DIV_EST.get(code, 0.5),
            "signal": signal, "maD": maD,
            "premium": premium, "ret5d": ret5d,
            "vol_ratio": vol_ratio, "heat": heat,
        })
        print(f"[OK] {code} {name}  {price}  sig={signal}  maD={maD}%  ret5d={ret5d}%  premium={premium}%")

    except Exception as e:
        print(f"[WARN] {code} {name} 失敗: {e}")
        results.append({
            "code": code, "name": name,
            "price": 0, "ma60": 0, "ma20": 0,
            "low52": 0, "high52": 0,
            "yld": 0, "days": DIV_DAYS.get(code, 90),
            "est": DIV_EST.get(code, 0.5),
            "signal": "dear", "maD": 0,
            "premium": 0, "ret5d": 0, "vol_ratio": 0, "heat": 0,
        })

output = {
    "updated": datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%Y-%m-%d %H:%M"),
    "etfs": results,
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✓ data.json 完成，共 {len(results)} 支 ETF")
