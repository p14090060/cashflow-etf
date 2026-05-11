import json, datetime
import yfinance as yf

ETFS = [
    ("0056",   "元大高股息"),
    ("00713",  "台灣高息低波"),
    ("0050",   "元大台灣50"),
    ("00919",  "群益台灣精選高息"),
    ("006208", "富邦台50"),
    ("00981A", "統一台股增長"),  # 若 yfinance 抓不到改用估值
    ("00878",  "國泰永續高息"),
    ("00940",  "元大台灣價值高息"),
    ("00929",  "復華台灣科技優息"),
    ("00850",  "元大ESG永續"),
]

# 台股 ETF 在 yfinance 加 .TW 後綴
SUFFIX = ".TW"

# 近期配息天數（手動維護，每季更新一次）
DIV_DAYS = {
    "0056":   47,  "00713": 88,  "0050":  145, "00919": 32,
    "006208": 158, "00981A": 55, "00878":  65, "00940":  28,
    "00929":  19,  "00850": 112,
}
# 預估配息（元/張，手動維護）
DIV_EST = {
    "0056":  1.10, "00713": 1.05, "0050":  3.50, "00919": 0.45,
    "006208":2.10, "00981A":0.40, "00878": 0.38, "00940": 0.32,
    "00929": 0.42, "00850": 0.80,
}

def calc_signal(price, ma60, low52, high52):
    pos52 = (price - low52) / (high52 - low52) if high52 > low52 else 0.5
    maD   = (price - ma60) / ma60 * 100 if ma60 > 0 else 0
    # 便宜：52週位置 < 35% 且 60MA 偏離 < -2%
    # 偏貴：52週位置 > 70% 且 60MA 偏離 > +4%
    if pos52 < 0.35 and maD < -2:
        signal = "cheap"
    elif pos52 > 0.70 and maD > 4:
        signal = "dear"
    else:
        signal = "fair"
    return signal, round(maD, 1)

results = []
for code, name in ETFS:
    ticker_code = code + SUFFIX
    try:
        tk = yf.Ticker(ticker_code)
        hist = tk.history(period="1y")
        if hist.empty:
            raise ValueError("no data")

        price  = round(float(hist["Close"].iloc[-1]), 2)
        low52  = round(float(hist["Low"].min()), 2)
        high52 = round(float(hist["High"].max()), 2)
        ma60   = round(float(hist["Close"].tail(60).mean()), 2)

        # 殖利率：用近一年配息總額 / 現價估算
        info = tk.fast_info
        yld = round(getattr(info, "dividend_yield", 0) * 100, 1) if hasattr(info, "dividend_yield") else 0.0

        signal, maD = calc_signal(price, ma60, low52, high52)

        results.append({
            "code":   code,
            "name":   name,
            "price":  price,
            "ma60":   ma60,
            "low52":  low52,
            "high52": high52,
            "yld":    yld,
            "days":   DIV_DAYS.get(code, 90),
            "est":    DIV_EST.get(code, 0.5),
            "signal": signal,
            "maD":    maD,
        })
        print(f"[OK] {code} {name}  price={price}  signal={signal}  maD={maD}%")

    except Exception as e:
        print(f"[WARN] {code} {name} 抓取失敗: {e}，使用預設值")
        results.append({
            "code": code, "name": name,
            "price": 0, "ma60": 0, "low52": 0, "high52": 0,
            "yld": 0, "days": DIV_DAYS.get(code, 90),
            "est": DIV_EST.get(code, 0.5),
            "signal": "fair", "maD": 0,
        })

output = {
    "updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
    "etfs": results,
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✓ data.json 寫入完成，共 {len(results)} 支 ETF")
