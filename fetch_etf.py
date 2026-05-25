import json, math, datetime, ssl, re, requests
import urllib.request as _ur
from pathlib import Path
import yfinance as yf

OUT_BASE = Path(__file__).parent / "data" / "_base.json"
OUT_DIV  = Path(__file__).parent / "data" / "dividend_info.json"

# 啟動時載入 dividend_info.json，_todo:false 的條目作為最高優先來源
def _load_confirmed_freq():
    try:
        with open(OUT_DIV, encoding="utf-8") as f:
            info = json.load(f)
        return {
            code: meta["frequency"]
            for code, meta in info.get("etfs", {}).items()
            if not meta.get("_todo", True) and meta.get("frequency")
        }
    except Exception:
        return {}

_CONFIRMED_FREQ = _load_confirmed_freq()

# ETF 拆分紀錄（備查，供未來防呆與進榜時核對）
# 格式：代碼 → [(拆分日, 拆分比例)]，比例 = 拆後張數 / 拆前張數
SPLIT_RECORDS = {
    "0050":   [("2025-06-01", 4)],   # 1拆4
    "0052":   [("2025-11-17", 7)],   # 1拆7（yfinance 跳變在 2025-11-17，pre_mask 邊界要在此）
    "00631L": [("2026-03-01", 22)],  # 1拆22
    "00663L": [("2026-01-01", 7)],   # 1拆7（首例槓桿型）
    "00685L": [("2026-01-01", 24)],  # 1拆24（擬進行，待確認日期）
}

# 手動覆蓋 ret1y：yfinance 歷史資料異常的 ETF，填真實年化報酬率
_RET1Y_OVERRIDE = {
    # 改用 Adj Close 後拆分問題已自動修正，不再需要手動覆蓋
}

# 上市後至今尚未配息，殖利率欄位顯示「待公告」
_YLD_PENDING = {"00949", "00954", "00965", "009800", "009805"}  # 009805 季配但尚未配，2025/5 上市

# 手動覆蓋 yld：yfinance 12 個月加總失真的 ETF，填真實年化殖利率
_YLD_OVERRIDE = {
    "00928": 1.8,    # 上櫃ETF FinMind抓不到，trailing 12M 核實 0.66/37=1.8%（2026-05-25）
    "006201": 1.6,   # 上櫃ETF FinMind抓不到，trailing 12M 核實 0.77/49=1.6%（2026-05-25）
    "00940": 4.67,   # yfinance 抓到上市初期大配息，真實年化 4.67%（2026-05-20 確認）
    "006208": 2.0,   # FinMind × TWSE ETFortune 雙源核實，更新 3.06%→2.0%（2026-05-23）
    "00881": 9.9,    # TWSE ETFortune 核實，最新配息 2026-01-20 NT$2.65（2026-05-23 確認）
    "00912": 6.2,    # TWSE ETFortune 核實，FinMind 算法算出 15.2% 過高（2026-05-23 確認）
    "00701": 7.8,    # TWSE ETFortune 核實，半年配取近 2 筆平均（2026-05-23 確認）
    # ── 以下 16 支 FinMind×TWSE 雙源核實（2026-05-23）──
    "00702": 2.7,
    "00717": 3.8,
    "00771": 1.3,
    "00882": 2.8,
    "00907": 4.3,
    "00770": 6.5,
    "00911": 1.8,
    "00913": 3.7,
    "00923": 4.5,
    "00830": 10.8,
    "00904": 6.7,
    "00714": 2.3,
    "00733": 0.8,
    "00728": 0.9,
    "00690": 5.7,
    "00984D": 0.8,
    "00731": 3.7,    # FinMind×TWSE 核實（2026-05-23）
    "00896": 2.7,    # FinMind×TWSE 核實（2026-05-23）
    "00917": 16.2,   # FinMind×TWSE 核實（2026-05-23）
}

def calc_rsi(close_series, period=14):
    """Wilder RSI，回傳 0-100；資料不足時回傳 50"""
    c = close_series.dropna()
    if len(c) < period + 1:
        return 50.0
    delta  = c.diff().dropna()
    gains  = delta.clip(lower=0).tail(period * 3)
    losses = (-delta).clip(lower=0).tail(period * 3)
    avg_g  = gains.ewm(com=period - 1, adjust=False).mean().iloc[-1]
    avg_l  = losses.ewm(com=period - 1, adjust=False).mean().iloc[-1]
    if avg_l == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_g / avg_l)), 1)

def safe(v, default=0):
    try:
        return default if (v is None or math.isnan(float(v)) or math.isinf(float(v))) else v
    except Exception:
        return default

# ── 精選池：固定追蹤，B-1 計算機 / D-1 建議用此清單 ──────────────────
CURATED = [
    ("0056",   "元大高股息"),
    ("00713",  "台灣高息低波"),
    ("0050",   "元大台灣50"),
    ("00919",  "群益台灣精選高息"),
    ("006208", "富邦台50"),
    ("00981A", "統一台股增長"),
    ("00403A", "統一台股升級50"),
    ("00878",  "國泰永續高息"),
    ("00940",  "元大台灣價值高息"),
    ("00929",  "復華台灣科技優息"),
    ("00850",  "元大ESG永續"),
    ("00928",  "中信上櫃ESG 30"),
    ("006201", "元大富櫃50"),
]
CURATED_CODES = {code for code, _ in CURATED}

# 上櫃 ETF 用 .TWO 後綴（TPEx），其餘用 .TW（TWSE）
TWO_CODES = {"00928", "006201"}

SUFFIX = ".TW"
HIGH_DIV_KEYWORDS = ["高股息", "高息", "精選高息", "永續高息", "價值高息"]

# ── 配息頻率靜態對照表（ETF 配息頻率幾乎不變，寫死最可靠）──────────
DIV_FREQ = {
    # ── 年配 ──
    "0050":"半年配","0051":"年配",  "0052":"年配",   "0053":"年配",
    "0055":"年配",  "006201":"年配", "00646":"不配息",
    "00909":"年配", "00951":"年配",  "00971":"年配",
    "009804":"半年配","009811":"半年配","00984D":"月配", "00980A":"季配",
    "00982A":"季配", "00983A":"年配", "00986A":"年配", "009810":"年配",
    # ── 季配 ──
    "0056":"季配",
    "00713":"季配", "006208":"半年配","00850":"季配",
    "00881":"半年配", "00882":"季配", "00892":"季配",
    "00901":"年配",  "00908":"季配", "00913":"季配",
    "00916":"季配", "00921":"季配", "00922":"季配",
    "00923":"季配", "00926":"半年配","00932":"季配",
    "00947":"季配", "00692":"季配", "00701":"半年配",
    "00733":"季配", "00735":"年配", "00690":"半年配",
    "009816":"不配息","009819":"年配","009820":"年配","009813":"不配息",
    "00985A":"年配","00987A":"年配","00988A":"年配","00989A":"季配",
    "00990A":"不配息","00991A":"半年配","00992A":"季配","00993A":"年配",
    "00994A":"季配","00995A":"季配","00997A":"季配",
    # ── 月配 ──
    "00919":"季配", "00981A":"季配","00403A":"季配","00878":"季配",
    "00940":"月配", "00929":"月配",
    "00891":"季配", "00894":"季配", "00896":"月配", "00900":"月配",
    "00904":"月配", "00905":"月配", "00907":"月配", "00915":"季配",
    "00918":"季配", "00927":"季配", "00930":"雙月配", "00934":"月配",
    "00936":"月配", "00939":"月配", "00944":"月配", "00946":"月配",
    "00948":"月配", "00952":"月配", "00961":"月配", "00964":"月配",
    "00400A":"月配","00401A":"月配","00999A":"季配","00996A":"季配",
    # ── 半年配 ──
    "00830":"半年配","00935":"半年配","00984A":"季配",
    "009802":"季配","009803":"季配","00981T":"月配",
    "00982T":"半年配","00983D":"月配",
    # ── 不配（外國指數/商品/無配息型）──
    "00641":"不配息", "00643":"不配息", "00652":"不配息",
    "00662":"不配息", "00757":"不配息", "00885":"不配息",
    "00902":"不配息", "00910":"不配息", "00924":"不配息",
    "00941":"不配息", "00949":"年配",   "00954":"年配",
    "00965":"年配",   "009800":"年配",  "009812":"不配息",
    # 不定期/實質不配息（歷史幾乎無配）
    "0057":"不配息", "00660":"不配息",
    "00763U":"不配息",  # 期貨型銅 ETF，結構上不配息（2026-05-25 確認）
    "0061":  "不配息",  # 元大寶滬深，CSI300 不分配（多源查無配息紀錄，2026-05-25）
    "006206":"不配息",  # 元大上證50，無配息政策（2026-05-25）
    "00783": "不配息",  # 富邦中証500，查無配息紀錄（2026-05-25）
}

def fetch_div_freq_twse(code):
    """從 TWSE ETF_SEARCH 回傳資料中找配息頻率關鍵字"""
    try:
        clean = ''.join(c for c in code if c.isalnum())
        r = requests.get(
            f"https://www.twse.com.tw/fund/ETF_SEARCH?response=json&etfNo={clean}",
            timeout=6, headers={"User-Agent": "Mozilla/5.0"}
        )
        text = r.text
        if '每月' in text or '月配' in text: return "月配"
        if '每季' in text or '季配' in text: return "季配"
        if '每半年' in text or '半年' in text: return "半年配"
        if '每年' in text or '年配' in text: return "年配"
    except Exception:
        pass
    return None

# 名稱關鍵字對應配息頻率
_NAME_FREQ = [
    (["月月配", "月配"], "月配"),
    (["季配"],           "季配"),
    (["半年配"],         "半年配"),
    (["年配"],           "年配"),
]

def detect_div_freq(tk, code, name="", hist_days=0):
    """優先查 dividend_info.json（已確認）→ 手動表 → 名稱關鍵字 → TWSE API → yfinance 推算"""
    # 0. dividend_info.json 已確認（_todo:false）優先
    confirmed = _CONFIRMED_FREQ.get(code)
    if confirmed:
        return confirmed
    # 1. 手動維護表
    manual = DIV_FREQ.get(code)
    if manual:
        return manual
    # 2. 名稱關鍵字（直接含月配/季配等字樣）
    for keywords, freq in _NAME_FREQ:
        if any(kw in name for kw in keywords):
            return freq
    # 3. TWSE ETF_SEARCH 頁面文字
    twse = fetch_div_freq_twse(code)
    if twse:
        return twse
    # 4. yfinance 股利歷史（拉長到 3 年）
    try:
        import pandas as _pd
        divs = tk.dividends
        if len(divs) == 0:
            # 有 1 年以上交易紀錄卻從未配息 → 確認不配
            return "不配息" if hist_days >= 200 else "不明"
        cutoff = _pd.Timestamp.now(tz='UTC') - _pd.Timedelta(days=1095)
        n = len(divs[divs.index > cutoff])
        if n >= 10: return "月配"
        if n >= 5:  return "季配"
        if n >= 3:  return "半年配"
        if n >= 1:  return "年配"
    except Exception:
        pass
    return "不明"

# 配息資料 fallback（yfinance 抓不到時才用）
DIV_DAYS = {
    "0056":47, "00713":88, "0050":145, "00919":32,
    "006208":158, "00981A":55, "00878":65, "00940":28,
    "00929":19, "00850":112, "00403A":90,
}
DIV_EST = {
    "0056":1.10, "00713":1.05, "0050":3.50, "00919":0.45,
    "006208":2.10, "00981A":0.40, "00878":0.38, "00940":0.32,
    "00929":0.42, "00850":0.80, "00403A":0.30,
}

# 每種配息頻率對應的預設間隔天數
_FREQ_DAYS = {"月配": 30, "雙月配": 60, "季配": 91, "半年配": 182, "年配": 365}

# 每種配息頻率一年應配幾次（用於殖利率年化計算）
_FREQ_N = {"月配": 12, "雙月配": 6, "季配": 4, "半年配": 2, "年配": 1}

def calc_div_forecast(divs, code, div_freq):
    """從 yfinance 股利歷史推算下次配息日與預估金額。
    回傳 (days_left, est_amt, next_date_str or None)
    """
    fallback_days = DIV_DAYS.get(code, 90)
    fallback_est  = DIV_EST.get(code, 0.30)
    try:
        if divs is None or divs.empty:
            return fallback_days, fallback_est, None

        freq_days = _FREQ_DAYS.get(div_freq, 90)

        # 用最近幾次配息算實際平均間隔（比寫死更準）
        n = {"月配": 4, "雙月配": 4, "季配": 4, "半年配": 3, "年配": 2}.get(div_freq, 3)
        if len(divs) >= n + 1:
            recent = divs.index[-(n + 1):]
            gaps = [(recent[i + 1] - recent[i]).days for i in range(len(recent) - 1)]
            freq_days = int(sum(gaps) / len(gaps))

        last_date = divs.index[-1].to_pydatetime().replace(tzinfo=None)
        last_amt  = round(float(divs.iloc[-1]), 2)

        today = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ).replace(tzinfo=None)

        # 往後推直到未來日期
        next_date = last_date + datetime.timedelta(days=freq_days)
        while next_date <= today:
            next_date += datetime.timedelta(days=freq_days)

        days_left = (next_date - today).days
        return days_left, last_amt, next_date.strftime("%Y-%m-%d")
    except Exception:
        return fallback_days, fallback_est, None

def calc_heat_score(cur_vol, avg_vol, aum, today_chg, recent_vols, curated=False):
    """複合熱度指數：量比(0-40) + 漲跌幅(0-30) + 連續性(0-30)，規模 <500億歸零"""
    if not curated and aum > 0 and aum < 50_000_000_000:
        return 0
    vol_ratio   = cur_vol / avg_vol if avg_vol > 0 else 0
    score_vol   = min(vol_ratio * 20, 40)
    score_chg   = min(abs(today_chg) * 10, 30)
    days_above  = sum(1 for v in recent_vols if avg_vol > 0 and v > avg_vol)
    score_cont  = days_above * 6
    return round(score_vol + score_chg + score_cont, 2)

# ── 自動發現：排除非股票型 ETF 的關鍵字 ────────────────────────────
EXCLUDE_KW = [
    '債', '期貨', '槓桿', '反向', '貨幣市場', '貨幣',
    '正2', '反1', '公債', '公司債', '高收益', '不動產',
    'REITs', '基礎建設', '優先股', '可轉換', '黃金', '原油',
    '石油', '天然氣', '白銀', '農產',
]

def fetch_twse_etf_pool():
    """從 TWSE ISIN strMode=2 的 ETF 區段抓股票型 ETF 清單，回傳 [(code, name)]"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = _ur.Request(
            'https://isin.twse.com.tw/isin/C_public.jsp?strMode=2',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with _ur.urlopen(req, timeout=20, context=ctx) as r:
            html = r.read().decode('ms950', errors='ignore')
        # 只取 ETF 區段（從 "ETF <B>" 開始）
        etf_start = html.find('ETF <B>')
        section = html[etf_start:] if etf_start >= 0 else html
        pairs = re.findall(r'([0-9]{4,6}[A-Z]?)　([^\t<\r\n]{2,30})', section)
        results, seen = [], set()
        for code, name in pairs:
            code, name = code.strip(), name.strip()
            if not code or not name or code in seen:
                continue
            if not code.startswith('0'):   # 排除台灣存託憑證（9xxx）
                continue
            if any(kw in name for kw in EXCLUDE_KW):
                continue
            seen.add(code)
            results.append((code, name))
        print(f"[POOL] TWSE 股票型 ETF: {len(results)} 支")
        return results
    except Exception as e:
        print(f"[POOL] TWSE 抓取失敗，僅用精選清單: {e}")
        return []

def build_pool():
    """精選池 + TWSE 自動發現池合併，精選碼不重複"""
    auto = fetch_twse_etf_pool()
    pool = list(CURATED)
    added = 0
    for code, name in auto:
        if code not in CURATED_CODES:
            pool.append((code, name))
            added += 1
    print(f"[POOL] 合計: 精選 {len(CURATED)} + 自動發現 {added} = {len(pool)} 支")
    return pool

# ── 訊號計算 ──────────────────────────────────────────────────────────
def is_high_div(name, yld):
    return any(k in name for k in HIGH_DIV_KEYWORDS) or yld > 5

def calc_signal(price, ma20, ma60, low52, high52, ret5d, vol_ratio, rsi, yld, name):
    pos52 = (price - low52) / (high52 - low52) if high52 > low52 else 0.5
    maD60 = round((price - ma60) / ma60 * 100, 1) if ma60 > 0 else 0

    if ret5d >= 5 or rsi >= 75:
        return "hot", maD60
    if pos52 > 0.78 or price > ma60 * 1.06:
        return "dear", maD60

    conds = [price <= ma60 * 1.03, ret5d < 5, 0.5 <= vol_ratio <= 3.0, rsi < 75]
    if is_high_div(name, yld):
        conds.append(yld > 5)
    if all(conds):
        return "fair", maD60

    if pos52 < 0.40 and maD60 < -2:
        return "cheap", maD60
    return "dear", maD60

def fetch_finmind_yld(code, price, div_freq="不明"):
    """從 FinMind 抓配息紀錄，依頻率取最近 N 次加總算年化殖利率。
    拉 730 天確保各頻率都能抓到足夠筆數；不配息直接回 0。
    """
    if div_freq == "不配息":
        return 0.0
    try:
        from datetime import datetime, timedelta
        start = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        r = requests.get(
            f'https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockDividend&data_id={code}&start_date={start}',
            timeout=8, headers={"User-Agent": "Mozilla/5.0"}
        )
        data = r.json().get('data', [])
        if not data:
            return 0.0

        # 只保留現金配息 > 0，依日期降序（最新在前）
        payments = sorted(
            [(x.get('date', ''), float(x.get('CashEarningsDistribution', 0) or 0))
             for x in data
             if float(x.get('CashEarningsDistribution', 0) or 0) > 0],
            key=lambda x: x[0], reverse=True
        )
        if not payments:
            return 0.0

        n = _FREQ_N.get(div_freq, 0)
        if n > 0:
            # 取最近 n 次；不足 n 次（新 ETF）按已有次數等比推算
            recent = payments[:n]
            total  = sum(amt for _, amt in recent)
            annual = total / len(recent) * n
        else:
            # 頻率不明：退回 365 天加總
            one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            annual = sum(amt for date, amt in payments if date >= one_year_ago)

        if annual > 0 and price > 0:
            return round(annual / price * 100, 1)
    except Exception:
        pass
    return 0.0

def _parse_roc_date(s):
    """民國日期 '115年01月22日' → '2026-01-22'"""
    try:
        m = re.match(r'(\d+)年(\d+)月(\d+)日', str(s))
        if m:
            return f"{int(m.group(1))+1911}-{m.group(2)}-{m.group(3)}"
    except Exception:
        pass
    return ""

def fetch_twse_etfortune_yld(code, price, div_freq):
    """從 TWSE ETFortune 官方網頁解析歷史配息，依頻率取最近 N 次加總算年化殖利率。
    解析 HTML 表格（與 fetch_dividend_calendar.py 同一套做法），無需 JSON API。
    """
    if div_freq == "不配息" or price <= 0:
        return 0.0
    try:
        from datetime import datetime, timedelta
        import ssl, urllib.request as _ur2
        start = (datetime.now() - timedelta(days=730)).strftime('%Y%m%d')
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        url = (f"https://www.twse.com.tw/rwd/zh/ETFortune/dividendList"
               f"?stkNo={code}&startDate={start}")
        req = _ur2.Request(url, headers={"User-Agent": "ETF-fetcher/1.0"})
        with _ur2.urlopen(req, timeout=10, context=ctx) as r:
            html = r.read().decode("utf-8")

        # 解析 HTML 表格（與 fetch_dividend_calendar.py 同套 regex）
        tr_re = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
        td_re = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.DOTALL | re.IGNORECASE)
        tag_re = re.compile(r'<[^>]+>')
        def strip(h): return tag_re.sub('', h).strip()

        payments = []
        for tr in tr_re.finditer(html):
            cells = [strip(td.group(1)) for td in td_re.finditer(tr.group(1))]
            if len(cells) < 6:
                continue
            # 欄位：代碼 名稱 除息日 基準日 發放日 金額
            row_code = cells[0].strip()
            if row_code != code:
                continue
            date_str = _parse_roc_date(cells[2])
            if not date_str:
                continue
            try:
                amt = float(str(cells[5]).replace(',', ''))
            except Exception:
                amt = 0.0
            if amt > 0:
                payments.append((date_str, amt))

        if not payments:
            return 0.0
        payments.sort(key=lambda x: x[0], reverse=True)

        n = _FREQ_N.get(div_freq, 0)
        if n > 0:
            recent = payments[:n]
            total  = sum(amt for _, amt in recent)
            annual = total / len(recent) * n
        else:
            one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            annual = sum(amt for date, amt in payments if date >= one_year_ago)

        if annual > 0:
            return round(annual / price * 100, 1)
    except Exception:
        pass
    return 0.0

def cross_verify_yld(yld_a, yld_b, tolerance=2.0):
    """雙源核對殖利率。回傳 (final_yld, verified)。
    兩源都有且差距在容許範圍內 → verified=True。
    只有單源或差距過大 → verified=False（顯示為 '--'）。
    """
    if yld_a > 0 and yld_b > 0:
        if abs(yld_a - yld_b) <= tolerance:
            return yld_a, True
        else:
            return yld_a, False
    elif yld_a > 0:
        return yld_a, False
    elif yld_b > 0:
        return yld_b, False
    return 0.0, False

def fetch_nav_twse(code):
    try:
        clean = ''.join(c for c in code if c.isdigit())
        r = requests.get(
            f"https://www.twse.com.tw/fund/ETF_SEARCH?response=json&etfNo={clean}",
            timeout=6, headers={"User-Agent": "Mozilla/5.0"}
        )
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
    except Exception:
        pass
    return None

# ── 主流程 ──────────────────────────────────────────────────────────
ALL_ETFS  = build_pool()

results = []
for code, name in ALL_ETFS:
    curated = code in CURATED_CODES
    ticker_code = code + (".TWO" if code in TWO_CODES else SUFFIX)
    try:
        tk = yf.Ticker(ticker_code)
        hist = tk.history(period="1y", auto_adjust=False)
        if hist.empty or len(hist) < 5:
            raise ValueError("insufficient data")

        # 開盤前 Action 跑時，yfinance 最後一筆可能是 Close=NaN 的不完整當日資料
        c = hist["Close"].dropna()
        v = hist["Volume"].dropna()
        if len(c) < 5:
            raise ValueError("insufficient clean data")

        # Adj Close：拆分回溯調整，用於報酬率計算；Close 用於現價/均線/訊號
        adj = hist["Adj Close"].dropna() if "Adj Close" in hist.columns else c

        # yfinance 未套用已知拆股時，手動補正 adj close 中的拆股前價格
        if code in SPLIT_RECORDS:
            import pandas as _pd
            adj = adj.copy()
            for split_date_str, split_ratio in SPLIT_RECORDS[code]:
                split_ts = _pd.Timestamp(split_date_str)
                split_ts = split_ts.tz_localize(adj.index.tz) if adj.index.tz else split_ts
                pre_mask = adj.index < split_ts
                # 若拆股前的 adj close 均值明顯高於拆股後（超過比例的 50%），表示未調整
                if pre_mask.any() and (~pre_mask).any():
                    pre_mean  = float(adj[pre_mask].mean())
                    post_mean = float(adj[~pre_mask].mean())
                    if post_mean > 0 and pre_mean > post_mean * (split_ratio * 0.5):
                        adj[pre_mask] = adj[pre_mask] / split_ratio

        price    = round(float(c.iloc[-1]), 2)
        low52    = round(float(c.min()), 2)
        high52   = round(float(c.max()), 2)
        ma60     = round(float(c.tail(60).mean()), 2)
        ma20     = round(float(c.tail(20).mean()), 2)
        rsi      = calc_rsi(c)
        ret5d    = round(float((adj.iloc[-1] / adj.iloc[-6]  - 1) * 100), 2) if len(adj) >= 6  else 0.0
        ret1m    = round(float((adj.iloc[-1] / adj.iloc[-22] - 1) * 100), 1) if len(adj) >= 22 else 0.0
        ret1y    = round(float((adj.iloc[-1] / adj.iloc[0]   - 1) * 100), 1) if len(adj) >= 2  else 0.0
        # 每月個別報酬（最近 6 個月，oldest→newest），k=6 最舊、k=1 最新
        def _mr(k):
            n = len(adj); e = n-(k-1)*22; s = n-k*22
            if s < 0 or e <= s: return None
            return round(float((adj.iloc[e-1]/adj.iloc[s]-1)*100), 1)
        ret_months  = [_mr(k) for k in range(6, 0, -1)]
        new_listing = len(hist) < 240   # 上市未滿約1年（交易日 < 240）
        # 新上市 ETF 以面額 NT$10 為基準計算報酬，反映申購成本
        if new_listing and len(adj) >= 2:
            ret1y = round((price - 10.0) / 10.0 * 100, 1)
        # yfinance 歷史資料異常防呆：adj close 高低比 > 4 代表拆分調整失效，ret1y 不可信
        # 用 adj（已做拆分調整）而非原始 Close，避免正常拆股的 ETF 被誤判為 0
        _adj_max = float(adj.max()) if len(adj) > 0 else 0
        _adj_min = float(adj.min()) if len(adj) > 0 else 0
        if _adj_max > 0 and _adj_min > 0 and (_adj_max / _adj_min) > 4:
            ret1y = None
        # 手動覆蓋優先（已知 yfinance 資料有問題的 ETF）
        if code in _RET1Y_OVERRIDE:
            ret1y = _RET1Y_OVERRIDE[code]
        avg_vol     = float(v.tail(20).mean())
        cur_vol     = float(v.iloc[-1])
        vol_ratio   = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0
        today_chg   = round(float((c.iloc[-1] / c.iloc[-2] - 1) * 100), 2) if len(c) >= 2 else 0.0
        recent_vols = v.tail(5).values.tolist()

        # 自動發現的 ETF：成交量太低（冷門）就跳過
        if not curated and avg_vol < 100:
            print(f"[SKIP] {code} {name}  avg_vol={avg_vol:.0f} 太低，略過")
            continue

        nav = fetch_nav_twse(code) or round(float(hist["Close"].iloc[-2]), 2)
        premium = round((price - nav) / nav * 100, 2) if nav > 0 else 0.0

        aum = 0.0
        yld = 0.0
        try:
            info = tk.fast_info
            aum = safe(getattr(info, "market_cap", 0) or 0)
        except Exception:
            pass
        import pandas as _pd
        divs = tk.dividends  # 一次抓，配息預測共用

        # 先偵測配息頻率，殖利率年化計算需要用到
        div_freq = detect_div_freq(tk, code, name, hist_days=len(hist))

        # 殖利率雙源核對：FinMind（A）× TWSE ETFortune（B），兩源一致才 verified
        fm_yld   = fetch_finmind_yld(code, price, div_freq)
        twse_yld = fetch_twse_etfortune_yld(code, price, div_freq)
        yld, yld_verified = cross_verify_yld(fm_yld, twse_yld)

        # fallback：兩源都是 0 才啟用，一律標記 unverified
        if yld == 0.0 and price > 0 and 'Dividends' in hist.columns:
            try:
                annual = float(hist['Dividends'].sum())
                if annual > 0:
                    yld = round(annual / price * 100, 1)
                    yld_verified = False
            except Exception:
                pass
        if yld == 0.0 and price > 0:
            try:
                _dy = getattr(info, "dividend_yield", None)
                if _dy:
                    yld = round(float(_dy) * 100, 1)
                    yld_verified = False
            except Exception:
                pass
        if yld == 0.0 and price > 0:
            try:
                cutoff = _pd.Timestamp.now(tz='UTC') - _pd.Timedelta(days=365)
                idx = divs.index.tz_convert('UTC') if divs.index.tz else divs.index.tz_localize('UTC')
                annual = float(divs[idx > cutoff].sum())
                if annual > 0:
                    yld = round(annual / price * 100, 1)
                    yld_verified = False
            except Exception:
                pass
        # 手動覆寫：人工查證過的直接視為 verified
        if code in _YLD_OVERRIDE:
            yld = _YLD_OVERRIDE[code]
            yld_verified = True

        yld_pending = code in _YLD_PENDING

        signal, maD = calc_signal(price, ma20, ma60, low52, high52,
                                   ret5d, vol_ratio, rsi, yld, name)
        heat     = calc_heat_score(cur_vol, avg_vol, aum, today_chg, recent_vols, curated)
        div_days, div_est, div_next = calc_div_forecast(divs, code, div_freq)

        results.append({
            "code": code, "name": name, "curated": curated,
            "price": safe(price), "ma60": safe(ma60), "ma20": safe(ma20),
            "low52": safe(low52), "high52": safe(high52),
            "rsi": safe(rsi),
            "yld": safe(yld), "yld_verified": yld_verified, "yld_pending": yld_pending, "days": div_days,
            "est": div_est, "div_next": div_next,
            "signal": signal, "maD": safe(maD),
            "ret5d": safe(ret5d), "ret1m": safe(ret1m),
            "ret1y": safe(ret1y), "ret_months": ret_months, "new_listing": new_listing,
            "avg_vol": safe(avg_vol), "cur_vol": safe(cur_vol),
            "vol_ratio": safe(vol_ratio), "heat": safe(heat),
            "aum": safe(aum), "div_freq": div_freq,
        })
        tag = "精選" if curated else "自動"
        print(f"[{tag}] {code} {name}  {price}  sig={signal}  vol={avg_vol:.0f}")

    except Exception as e:
        if curated:
            # 精選池即使失敗也要輸出（保持計算機可用）
            results.append({
                "code": code, "name": name, "curated": True,
                "price": 0, "ma60": 0, "ma20": 0, "low52": 0, "high52": 0,
                "rsi": 50,
                "yld": 0, "yld_verified": False, "days": DIV_DAYS.get(code, 90), "est": DIV_EST.get(code, 0.30),
                "div_next": None, "signal": "dear", "maD": 0,
                "ret5d": 0, "ret1m": 0, "ret1y": 0, "ret_months": [0,0,0,0,0,0], "new_listing": False,
                "avg_vol": 0, "cur_vol": 0, "vol_ratio": 0, "heat": 0,
                "aum": 0, "div_freq": DIV_FREQ.get(code, "不明"),
            })
            print(f"[WARN] {code} {name} 失敗（保留精選）: {e}")
        else:
            print(f"[SKIP] {code} {name} 失敗，略過: {e}")

# ── 大盤加權指數：TWSE 官方 MI_INDEX（fallback yfinance）────────────
market = {"change_pct": 0.0, "change_pt": 0.0, "price": 0.0}
def _fetch_twse_market():
    """TWSE MI_5MINS_INDEX 抓今日加權收盤，yfinance 提供前一日基準計算漲跌"""
    import urllib.request as _ur, ssl as _ssl, json as _json
    ctx = _ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=_ssl.CERT_NONE
    url = "https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_INDEX?response=json"
    req = _ur.Request(url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.twse.com.tw/"})
    with _ur.urlopen(req, timeout=10, context=ctx) as r:
        d = _json.loads(r.read().decode("utf-8"))
    rows = d.get("data", [])
    if not rows:
        return None
    # 最後一筆（13:30:00）= 收盤，欄位 index 1 = 加權指數
    last = rows[-1]
    cur = float(str(last[1]).replace(",", ""))
    if cur <= 0:
        return None
    # 前一日收盤用 yfinance iloc[-2]（歷史資料穩定）
    twii = yf.Ticker("^TWII")
    h = twii.history(period="5d")
    if len(h) < 2:
        return None
    prev = float(h["Close"].iloc[-2])
    chg_pt = round(cur - prev, 2)
    chg_pc = round(chg_pt / prev * 100, 2) if prev else 0
    return {"price": round(cur, 2), "change_pt": chg_pt, "change_pct": chg_pc}

try:
    m = _fetch_twse_market()
    if m:
        market = m
        print(f"[OK] 大盤(TWSE) {m['price']}  {m['change_pt']:+.2f} ({m['change_pct']:+.2f}%)")
    else:
        raise ValueError("MI_INDEX 無法解析")
except Exception as e:
    print(f"[WARN] TWSE 大盤失敗({e})，改用 yfinance")
    try:
        twii = yf.Ticker("^TWII")
        h = twii.history(period="5d")
        if len(h) >= 2:
            prev  = float(h["Close"].iloc[-2])
            cur   = float(h["Close"].iloc[-1])
            chg   = round(cur - prev, 2)
            chg_p = round((cur - prev) / prev * 100, 2)
            market = {"change_pct": chg_p, "change_pt": chg, "price": round(cur, 2)}
            print(f"[OK] 大盤(yfinance) {cur}  {chg:+.2f} ({chg_p:+.2f}%)")
    except Exception as e2:
        print(f"[WARN] 大盤抓取失敗: {e2}")

curated_n = sum(1 for r in results if r.get("curated"))
auto_n    = len(results) - curated_n

# ── 配息日曆：從精選池中取 div_next 在 90 天內的，依日期排序 ──
today_str = datetime.datetime.now(
    datetime.timezone(datetime.timedelta(hours=8))
).strftime("%Y-%m-%d")
calendar = []
for r in results:
    if not r.get("curated") or not r.get("div_next"):
        continue
    if r["div_next"] > today_str and r["days"] <= 90:
        d = datetime.datetime.strptime(r["div_next"], "%Y-%m-%d")
        calendar.append({
            "iso_date": r["div_next"],
            "mon":    f"{d.month}月",
            "day":    str(d.day),
            "code":   r["code"],
            "name":   r["name"],
            "amt":    r["est"],
            "soon":   r["days"] <= 14,
            "source": "yfinance",
        })
calendar.sort(key=lambda x: x["iso_date"])

output = {
    "updated": datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%Y-%m-%d %H:%M"),
    "market": market,
    "etfs": results,
    "calendar": calendar,
}

OUT_BASE.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_BASE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# 同步更新 dividend_info.json 的 calendar（mis_fetcher.py 讀這個當估算來源）
if calendar and OUT_DIV.exists():
    try:
        with open(OUT_DIV, encoding="utf-8") as f:
            div_info = json.load(f)
        div_info["calendar"] = calendar
        with open(OUT_DIV, "w", encoding="utf-8") as f:
            json.dump(div_info, f, ensure_ascii=False, indent=2)
        print(f"✓ dividend_info.json calendar 更新：{len(calendar)} 筆")
    except Exception as e:
        print(f"[WARN] dividend_info.json 更新失敗: {e}")

print(f"\n✓ data/_base.json 完成：精選 {curated_n} + 自動發現 {auto_n} = {len(results)} 支 ETF")
