import json, math, datetime, ssl, re, requests, sys
import urllib.request as _ur
from pathlib import Path
import yfinance as yf

# Windows 本機主控台常是 cp950，print() 遇到 ✓/⚠ 等符號會 UnicodeEncodeError 整支腳本崩潰
# （GitHub Actions 的 Ubuntu 預設 UTF-8 不受影響，但本機手動執行會中招，2026-07-08 發現）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OUT_BASE  = Path(__file__).parent / "data" / "_base.json"
OUT_DIV   = Path(__file__).parent / "data" / "dividend_info.json"
POOL_CACHE = Path(__file__).parent / "data" / "etf_pool_cache.json"

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

def _load_confirmed_months():
    """dividend_info.json 裡 _todo:false（人工核實過）的除息月份清單。"""
    try:
        with open(OUT_DIV, encoding="utf-8") as f:
            info = json.load(f)
        return {
            code: meta["months"]
            for code, meta in info.get("etfs", {}).items()
            if not meta.get("_todo", True) and meta.get("months")
        }
    except Exception:
        return {}

_CONFIRMED_MONTHS = _load_confirmed_months()

# ⚠ 不要拿 dividend_info.json 的 avg_dividend_per_share 去推殖利率。
#   那個欄位是給「下次除息金額預估」用的，不少是舊值或峰值。
#   2026-09-27 實測：用「avg × 年配次數 ÷ 市價」跟實際殖利率比對 98 檔，
#   中位數相對誤差 14.2%、只有 55/98 落在 20% 以內，離譜的如
#   00896 推算 14.5% vs 實際 2.7%、00930 推算 20.5% vs 實際 7.5%。
#   FinMind 拿不到的（上櫃 ETF、額度爆掉）請乖乖進 _YLD_OVERRIDE。

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
_YLD_PENDING = {
    # 上市後尚未配息、殖利率顯示「待公告」的 ETF。**手動維護，不會自動清除。**
    # 值 = 最後一次查證「仍未配息」的日期；daily_check.py 會在超過 90 天沒複查時發 TG 提醒。
    # 改成 dict 是為了讓查證日期變成結構化資料；`code in _YLD_PENDING` 對 dict 是查 key，行為不變。
    "00411A": "2026-09-27",  # 統一前沿科技，年配(4月)，2026-08-26 上櫃；首配 2027-04
    "00949": "2026-09-23",   # 復華日本龍頭，年配(10月)，2024-07-01 上市
    "00954": "2026-09-23",   # 中信日本半導體，年配，2024-08-20 上市
    "00965": "2026-09-23",   # 元大航太防衛，年配，2025 上市
    "009800": "2026-09-23",   # 中信NASDAQ，年配(11月)，2025-02-11 上市，經理人得決定不配
    "00983A": "2026-09-23",   # 主動中信ARK創新，年配，2025-06-18 上市
    "009824": "2026-09-23",   # 群益美國科技巨頭，季配，2026-06-25 上市，成立滿45日後才配息（最早9月）
    "009825": "2026-09-30",   # 聯邦美國金融創新，年配，2026-07-17 上櫃；收益評價日=每年 12 月最後一個日曆日，首次評價 2026-12-31、首配預估 2027-01
    "00989A": "2026-10-01",   # 主動摩根美國科技，季配（評價日 3/6/9/12 月底倒數第 3 營業日，除息月 1/4/7/10），2025-10-22 上市、成立後 120 日才分配；MoneyDJ 查無配息資料——2026-04 與 2026-07 兩個除息月都評價了卻沒配，最快 2026-10
    "009823": "2026-10-01",   # 群益標普500，季配（評價月 1/4/7/10，除息月 2/5/8/11），2026-06-25 上市、成立滿 45 日才配；MoneyDJ 查無配息資料。S&P500 本身殖利率就只有 1.3% 左右，首配金額預期很小
    "009815": "2026-10-01",   # 大華美國MAG7+，半年配（評價日 3 月與 9 月的最後一個日曆日，評價後 45 營業日內發放），2026-01-26 掛牌；MoneyDJ 查無配息資料——2026-03 與 2026-09 兩次評價都沒配。公開說明書寫明「經理公司得依基金收益之情況決定每次之分配金額或不分配」，成分股是美股成長型科技股，本來就不靠股利
    "00408A": "2026-07-21",   # 主動第一金優股息，季配(1/4/7/10)，2026-07-15 上市，成立滿60日才配息，首配預估2026-10
    "00985A": "2026-09-23",   # 主動野村台灣50，半年配，2025-07-21 上市，評價日月份未公開；MoneyDJ/Win投資查無配息紀錄
    "009811": "2026-09-23",   # 統一美國50，半年配(評價日3月底/9月底，配息月4/10)，2025-07-29 上市，首次評價2026-03底但至今未配
    "009810": "2026-09-23",   # 玉山全球藍籌100，年配(12月)，2025-07-16 上市，首次評價日為成立後180日，首次除息預計2026-12
    "00986A": "2026-09-23",   # 主動台新龍頭成長，年配(評價日10/31，除息11月，發放12月)，2025-08-27 上市，首配預計2026-11
    "00409A": "2026-09-05",   # 主動復華全球50，年配（收益評價日 10 月底），2026-08-20 成立、2026-09-02 上市，尚未配息
    "00403A": "2026-09-05",   # 統一台股升級50（MoneyDJ 主動統一升級50），季配，MoneyDJ basic0005「查無配息資料」上市後從未配息
    "00410A": "2026-09-05",   # 主動永豐科技趨勢，半年配，2026-07-23 成立、08-03 上市，MoneyDJ basic0005「查無配息資料」
    "009829": "2026-09-05",   # 大華韓國KOSPI50，半年配，2026-08-12 成立、08-21 上市，MoneyDJ basic0005「查無配息資料」
    "009827": "2026-09-11",   # 玉山未來全球算力，季配（3/6/9/12月底評價、評價後45個營業日內發放），2026-08-24 成立、09-02 上市，尚未配息
}


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
    # 原本填 0.8 是把「單月」配息率當年殖利率（0.085/10.1≈0.84%）——
    # 這正是「年化 ÷ 單次」反推驗算要擋的那種錯。月配 0.085 × 12 = 1.02/年，
    # 除以市價約 10 元 → 10.1%。鉅亨 2026-06「年殖利率10.09%」、
    # 工商 2026-09「年配息率逾10%」雙源一致（2026-09-27 更正）
    "00984D": 10.1,
    # ── 上櫃 ETF，FinMind 抓不到（額度爆掉時還會整批退回 yfinance 殘缺值）──
    # 數字＝dividend_info 已雙源查證的每次配息 × 年配次數 ÷ 當時市價
    "00985D": 7.6,   # 0.061 × 12 ÷ 9.65；貝萊德官網月配 + 鉅亨年化7.14%（2026-09-27）
    "00998A": 10.0,  # 0.414 × 4 ÷ 16.63；復華官網季配 + Yahoo年化10.08%（2026-09-27）
    "00840B": 5.3,   # 0.125 × 12 ÷ 28.27；Yahoo 除息2026/02~09月配 + CMoney（2026-09-27）
    "00980D": 6.7,   # 0.114 × 12 ÷ 20.5；經濟日報年化6.57% + ETF資訊網近12月6.25%（2026-09-27）
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
# CURATED 裡的上櫃碼先寫死當保底；其餘由 build_pool() 從 ISIN strMode=4 自動補進來，
# 不要再手動維護——2026-09-27 以前這裡寫死兩支，導致上櫃 ETF 整批進不了池子，
# 連成交量排第 32 名的 00411A 都不在排行榜上。
CURATED_OTC = {"00928", "006201"}
TWO_CODES   = set(CURATED_OTC)

SUFFIX = ".TW"
HIGH_DIV_KEYWORDS = ["高股息", "高息", "精選高息", "永續高息", "價值高息"]

# ── 配息頻率靜態對照表（ETF 配息頻率幾乎不變，寫死最可靠）──────────
DIV_FREQ = {
    # ── 年配 ──
    "0050":"半年配","0051":"年配",  "0052":"年配",   "0053":"年配",
    "0055":"年配",  "006201":"年配", "00646":"不配息",
    "00402A":"年配",
    "00909":"年配", "00951":"年配",  "00971":"年配",
    "009804":"半年配","009811":"半年配","00984D":"月配", "00980A":"季配",
    # ── 2026-09-27 補上櫃後新進池子的，全部雙源查證（自動推論都推錯）──
    "00985D":"月配",   # 貝萊德官網「每月配息，每月最後一個日曆日為收益評價日」；
                       # 鉅亨「每次 0.061、年化 7.14%」反推 0.061/10.25≈0.595%×12 吻合。
                       # 自動推論成季配 → 殖利率被算成 1/3（2.5%）
    "00998A":"季配",   # 復華官網：評價 2/5/8/11 月底，已配 2026-06-17 0.404、
                       # 2026-09-17 0.424；Yahoo「年化約 10.08%」反推 0.404×4/16.03 吻合。
                       # 自動推論成半年配 → 殖利率被算成一半（5.0%）
    "00411A":"年配",   # 統一前沿科技，2026-08-26 上櫃掛牌，每年 3 月底評價、4 月除息，
                       # 首次配息 2027-04（元大 IPO 頁 + StockFeel 雙源）。目前尚未配過
    "00888":"季配",    # MoneyDJ 實際除息日 1/4/7/10 月，鎖定避免日後誤判。
                       # ⚠ 新聞寫「2026 改雙月配」與實際紀錄不符，不要採信
    "00840B":"月配",   # 凱基IG精選15+，Yahoo 除息 2026/02~09 每月一次（0.115~0.127）
                       # ＋CMoney 1/31、2/28、3/31 月配；自動推論成雙月配 → 殖利率少算一半
    "00980D":"月配",   # 主動聯博投等入息，經濟日報「每月配息、每單位 0.114、年化 6.57%」
                       # ＋ETF資訊網近12月配息率 6.25%；自動推論本來就對，鎖定避免日後飄掉
    "00982A":"季配", "00983A":"年配", "00986A":"年配", "009810":"年配",
    "009805":"季配",   # 台新美國電力基建（原新光，已更名），首次配息2026-07-15除息0.1元確認（2026-07-21）
    # ── 季配 ──
    "0056":"季配",
    "00713":"季配", "006208":"半年配","00850":"季配",
    "00881":"半年配", "00882":"季配", "00892":"季配",
    "00901":"年配",  "00908":"季配", "00913":"季配",
    "00916":"季配", "00921":"季配", "00922":"季配",
    "00923":"季配", "00926":"半年配","00932":"季配",
    "00947":"季配", "00692":"季配", "00701":"半年配",
    "00733":"季配", "00735":"年配", "00690":"半年配",
    "009816":"不配息","009819":"年配","009820":"年配","009813":"不配息","009824":"季配",
    "009825":"年配",   # 聯邦美國金融創新，公開說明書：「年配。於收益評價日(即每年十二月之最後一個日曆日)之本基金淨資產價值進行收益分配之評價」
    "009823":"季配",   # 群益標普500，收益評價月 1/4/7/10、除息月 2/5/8/11
    "009815":"半年配",   # 大華美國MAG7+，評價日 3 月／9 月最後一個日曆日
    "009827":"季配",   # 玉山未來全球算力，評價日 3/6/9/12 月底
    "009829":"半年配",   # 大華韓國KOSPI50，評價日 6 月／12 月最後一日曆日
    "009822":"不配息",   # 華南永昌未來金融，累積型。注意：是「設計上就不配」，不是「還沒配」，所以不進 _YLD_PENDING，畫面要顯示「不配息」而非「待公告」
    "00409A":"年配",   # 主動復華全球50，評價日 10 月底。2026-09-05 查證時只寫進 _YLD_PENDING 的註解，漏了同步到這張表，顯示成「不明」
    "00410A":"半年配",   # 主動永豐科技趨勢，同上，2026-09-05 查證過但漏填
    "00985A":"年配","00987A":"年配","00988A":"年配","00989A":"季配",
    "00990A":"不配息","00991A":"半年配","00992A":"季配","00993A":"年配",
    "00994A":"季配","00995A":"季配","00997A":"季配",
    # ── 月配 ──
    "00919":"季配", "00981A":"季配","00403A":"季配","00405A":"季配","00404A":"季配","00878":"季配",
    "00940":"月配", "00929":"月配",
    "00891":"季配", "00894":"季配", "00896":"月配", "00900":"月配",
    "00904":"月配", "00905":"月配", "00907":"月配", "00915":"季配",
    "00918":"季配", "00927":"季配", "00930":"雙月配", "00934":"月配",
    "00936":"月配", "00939":"月配", "00944":"月配", "00946":"月配",
    "00948":"月配", "00952":"月配", "00961":"月配", "00964":"月配",
    "00400A":"月配","00401A":"月配","00999A":"季配","00996A":"季配",
    "00408A":"季配",   # 主動第一金優股息，1/4/7/10月，2026-07-15上市（2026-07-21確認）
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
    "0057":"不配息", "00660":"不配息", "00407A":"不配息",
    "00763U":"不配息",  # 期貨型銅 ETF，結構上不配息（2026-05-25 確認）
    "0061":  "不配息",  # 元大寶滬深，CSI300 不分配（多源查無配息紀錄，2026-05-25）
    "006206":"不配息",  # 元大上證50，無配息政策（2026-05-25）
    "00783": "不配息",  # 富邦中証500，查無配息紀錄（2026-05-25）
    "020032":"不配息",  # 元大綠能N，ETN連結「特選台灣綠能報酬指數」，結構上不配息（WebSearch核實，2026-07-24）
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
        recent = divs[divs.index > cutoff]
        n = len(recent)
        if n >= 1:
            # 2026-09-05 修正：原本純看 3 年內配息「筆數」（n>=3 → 半年配、
            # n>=5 → 季配），但年配 ETF 只要有 3 年歷史就必然有 3 筆，
            # 必被誤判（實例 00917 中信特選金融，三年都在 1 月配息卻被判半年配，
            # 導致前端出現不存在的「9/21 除息」）。
            # 改用「一年配幾次」判斷：實際涵蓋年數算平均次數，再用「配息落在
            # 幾個不同月份」交叉驗證，兩個訊號取較保守（次數少）的那個。
            span_days = (recent.index[-1] - recent.index[0]).days
            per_year  = n / max(span_days / 365.0, 1.0)
            months    = len({d.month for d in recent.index})
            est       = min(per_year, months)
            if est >= 10:  return "月配"
            if est >= 5:   return "雙月配"
            if est >= 3:   return "季配"
            if est >= 1.5: return "半年配"
            return "年配"
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
    "006208":2.10, "00981A":0.63, "00878":0.38, "00940":0.32,
    "00929":0.42, "00850":0.80, "00403A":0.30,
    "00918":1.26, "00916":1.92,
}

# 每種配息頻率對應的預設間隔天數
_FREQ_DAYS = {"月配": 30, "雙月配": 60, "季配": 91, "半年配": 182, "年配": 365}

# 每種配息頻率一年應配幾次（用於殖利率年化計算）
_FREQ_N = {"月配": 12, "雙月配": 6, "季配": 4, "半年配": 2, "年配": 1}

def _next_ex_date_from_months(months, last_date, today):
    """依已核實的除息月份，推「今天之後、且不是上次那個月」的最近一次除息日。
    日期沿用上次除息的日號（月底不足則退到 28 號）。找不到回 None。"""
    day = min(last_date.day, 28)
    y, m = today.year, today.month
    for _ in range(26):
        if m in months:
            cand = datetime.datetime(y, m, day)
            if cand > today and (cand.year, cand.month) != (last_date.year, last_date.month):
                return cand
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return None

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

        # 2026-09-05：已人工核實除息月份的，改用月份清單推下一次，不用平均間隔。
        # 間隔法只要歷史有缺漏（停配一期、評價日改期）就會整個偏掉——實測
        # 00692 實際 [7,11] 卻推成 2027-02、00911 實際 [1,7] 卻推成 2026-11。
        months = _CONFIRMED_MONTHS.get(code)
        if months:
            by_month = _next_ex_date_from_months(months, last_date, today)
            if by_month:
                next_date = by_month

        days_left = (next_date - today).days
        return days_left, last_amt, next_date.strftime("%Y-%m-%d")
    except Exception:
        return fallback_days, fallback_est, None

# 規模低於這個數（元）的非 curated ETF，熱度歸零。0 = 停用。
# ⚠ 這條規則從寫下來到 2026-10-02 為止**一次都沒生效過**：aum 來自 yfinance
#   的 fast_info.market_cap，對台股 ETF 永遠回 0，而條件要求 aum > 0。
#   2026-10-02 接上 emega 的真實規模後實測：原本的 500 億門檻會讓 189 檔
#   非 curated ETF 裡的 169 檔熱度歸零，熱度榜只剩 20 檔，幾乎所有主動式
#   ETF（00996A 40 億、00987A 25 億、00980A 201 億…）全部消失。
#   補資料不該順帶改掉排名，所以先停用。要啟用請先決定合理門檻再開。
AUM_HEAT_FLOOR = 0


def calc_heat_score(cur_vol, avg_vol, aum, today_chg, recent_vols, curated=False):
    """複合熱度指數：量比(0-40) + 漲跌幅(0-30) + 連續性(0-30)
    回傳 (heat, score_cont)，score_cont 供 mis_fetcher 即時重算 heat 時繼承。"""
    if AUM_HEAT_FLOOR and not curated and 0 < aum < AUM_HEAT_FLOOR:
        return 0, 0
    vol_ratio   = cur_vol / avg_vol if avg_vol > 0 else 0
    score_vol   = min(vol_ratio * 20, 40)
    score_chg   = min(abs(today_chg) * 10, 30)
    days_above  = sum(1 for v in recent_vols if avg_vol > 0 and v > avg_vol)
    score_cont  = days_above * 6
    return round(score_vol + score_chg + score_cont, 2), round(score_cont, 2)

# ── 自動發現：排除非股票型 ETF 的關鍵字 ────────────────────────────
EXCLUDE_KW = [
    '債', '期貨', '槓桿', '反向', '貨幣市場', '貨幣',
    '正2', '反1', '公債', '公司債', '高收益', '不動產',
    'REITs', '基礎建設', '優先股', '可轉換', '黃金', '原油',
    '石油', '天然氣', '白銀', '農產',
    'R1', 'R2',   # 受益憑證（01xxxT），非 ETF
]

def _isin_etf_pool(str_mode):
    """抓 ISIN 某一市場別的股票型 ETF，回傳 [(code, name)]。strMode=2 上市、4 上櫃。"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = _ur.Request(
        'https://isin.twse.com.tw/isin/C_public.jsp?strMode=%s' % str_mode,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with _ur.urlopen(req, timeout=20, context=ctx) as r:
        html = r.read().decode('ms950', errors='ignore')
    # 只取 ETF 區段（從 "ETF <B>" 開始）
    etf_start = html.find('ETF <B>')
    section = html[etf_start:] if etf_start >= 0 else html
    pairs = re.findall(r'([0-9]{4,6}[A-Z]?)　([^\t<\r\n]{2,30})', section)
    out, seen = [], set()
    for code, name in pairs:
        code, name = code.strip(), name.strip()
        if not code or not name or code in seen:
            continue
        if not code.startswith('0'):   # 排除台灣存託憑證（9xxx）
            continue
        if code.endswith('T'):         # 排除受益憑證（01004T, 01007T 等）
            continue
        if any(kw in name for kw in EXCLUDE_KW):
            continue
        seen.add(code)
        out.append((code, name))
    return out


def fetch_twse_etf_pool():
    """抓 ISIN 的股票型 ETF 清單（**上市 + 上櫃**），回傳 [(code, name, is_otc)]。
    成功時同步更新 etf_pool_cache.json 作為 fallback 備份。

    ⚠ 一定要連上櫃一起抓。2026-09-27 以前只讀 strMode=2，上櫃 ETF 全部進不了池子，
      只有 CURATED 裡寫死的 00928/006201 例外——結果成交量排第 32 名的 00411A
      （主動統一前沿科技）、第 33 名的 00998A 都不在排行榜上，
      連我們自己有抓持股異動的 00411A 都連不回排行頁。
    """
    results, seen = [], set()
    for str_mode, is_otc, lab in ((2, False, "上市"), (4, True, "上櫃")):
        try:
            got = _isin_etf_pool(str_mode)
        except Exception as e:
            # 其中一邊掛掉不要拖垮另一邊，但一定要出聲——靜默縮水是這專案的老毛病
            print("[POOL] ISIN strMode=%s（%s）抓取失敗: %s" % (str_mode, lab, e))
            continue
        added = 0
        for code, name in got:
            if code in seen:
                continue
            seen.add(code)
            results.append((code, name, is_otc))
            added += 1
        print("[POOL] %s股票型 ETF: %d 支" % (lab, added))

    if not results:                     # 兩邊都掛才算失敗，交給 build_pool() fallback
        print("[POOL] ISIN 兩個市場別都抓不到")
        return []
    try:
        with open(POOL_CACHE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return results

def build_pool():
    """精選池 + ISIN 自動發現池合併，精選碼不重複。
    ISIN 失敗時 fallback etf_pool_cache.json（上次成功的清單），避免縮水成 13 支精選。
    順便把自動發現的上櫃碼補進 TWO_CODES，yfinance 才會用 .TWO 後綴去抓。
    """
    auto = fetch_twse_etf_pool()

    if not auto:
        if POOL_CACHE.exists():
            try:
                cached = json.load(open(POOL_CACHE, encoding="utf-8"))
                # cache 可能是舊的兩元組 [(code, name)]（2026-09-27 之前只存上市），
                # 補不出市場別時一律當上市，至少不會整批壞掉
                auto = [(r[0], r[1], bool(r[2]) if len(r) > 2 else False)
                        for r in cached if len(r) >= 2 and r[0] and r[1]]
                print(f"[POOL] ISIN 失敗，從 etf_pool_cache.json fallback 取得 {len(auto)} 支")
            except Exception as fb_err:
                print(f"[POOL] fallback 讀取 cache 失敗: {fb_err}")

    pool = list(CURATED)
    added = otc_added = 0
    for code, name, is_otc in auto:
        if is_otc:
            TWO_CODES.add(code)          # yfinance 要 .TWO，MIS 要 otc_ 前綴
        if code not in CURATED_CODES:
            pool.append((code, name))
            added += 1
            if is_otc:
                otc_added += 1
    print(f"[POOL] 合計: 精選 {len(CURATED)} + 自動發現 {added} = {len(pool)} 支"
          f"（其中上櫃 {otc_added} 支，TWO_CODES 共 {len(TWO_CODES)} 碼）")
    return pool


# ── 訊號計算 ──────────────────────────────────────────────────────────
def is_high_div(name, yld):
    return any(k in name for k in HIGH_DIV_KEYWORDS) or yld > 5

def is_bond_etf(code):
    """代號 B/D 結尾＝債券型 ETF。

    實測 ISIN 全部 1294 檔裡 111 檔 B/D 結尾，名稱**全部**都是債券型，零例外；
    反向查「名稱含債但代號非 B/D」只抓到槓反類（00680L/00681R/00688L/00689R
    /00687C），那些本來就被 EXCLUDE_KW 擋掉。
    名稱關鍵字擋不住簡稱省略「債」字的（主動富邦動態入息＝投資級債、
    主動貝萊德優投等＝投資等級債、凱基IG精選15+＝IG 債），所以用代號判。
    """
    return bool(code) and code[-1] in ("B", "D")


def calc_signal(price, ma20, ma60, low52, high52, ret5d, vol_ratio, rsi, yld, name,
                code=""):
    # 債券 ETF 跟著利率走，不是動能標的。套股票的 MA/RSI 規則會機械性地一直
    # 判成「便宜」——實測 3 檔債券型 3/3 都是 cheap，但全池只有 8% 是 cheap。
    # 那不是划算，是模型量錯東西。寧可不給訊號，也不要給看起來像買點的假訊號。
    # ⚠ 這支回傳的是 (signal, maD) 兩元組，跟 mis_fetcher 那支只回字串不同，
    #   守衛也要回兩元組，否則呼叫端 `signal, maD = ...` 會把 "bond" 拆成 4 個字元
    maD60 = round((price - ma60) / ma60 * 100, 1) if ma60 > 0 else 0
    if is_bond_etf(code):
        return "bond", maD60
    pos52 = (price - low52) / (high52 - low52) if high52 > low52 else 0.5

    if ret5d >= 5 or rsi >= 75:
        return "hot", maD60
    if pos52 > 0.78 or price > ma60 * 1.06:
        return "dear", maD60

    if pos52 < 0.40 and maD60 < -2:
        return "cheap", maD60

    conds = [price <= ma60 * 1.03, ret5d < 5, vol_ratio <= 3.0, rsi < 75]
    if is_high_div(name, yld):
        conds.append(yld > 5)
    if all(conds):
        return "fair", maD60

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


def fetch_twse_official_closes(max_lookback=6):
    """從今日往回找最近一個有完整收盤資料的交易日，回傳 (date_str, {code: close_or_None})。

    2026-07-08 發現：yfinance 對台股上市 ETF 偶發整批回傳最新交易日 Close=NaN，
    dropna() 會悄悄退回前一日舊價，且無任何警報（158/179 支 ETF 曾同時中招）。
    改用 TWSE 官方 MI_INDEX 全市場收盤行情一次性核對/覆蓋 price，徹底避免此類 yfinance 資料延遲問題。

    close_or_None: None 代表當日零成交量（TWSE 顯示 "--"），呼叫端應保留原價，不覆蓋。
    找不到任何資料（連假、TWSE 暫時性故障）時回傳 (None, {})，呼叫端應 fallback 純用 yfinance。
    """
    import urllib.request as _ur3, ssl as _ssl3
    ctx = _ssl3.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl3.CERT_NONE
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    for delta in range(max_lookback):
        d = now_tw.date() - datetime.timedelta(days=delta)
        if d.weekday() >= 5:   # 跳過週末
            continue
        date_str = d.strftime('%Y%m%d')
        try:
            url = (f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
                   f"?date={date_str}&type=ALLBUT0999&response=json")
            req = _ur3.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with _ur3.urlopen(req, timeout=15, context=ctx) as r:
                resp = json.loads(r.read().decode("utf-8"))
            if resp.get("stat") != "OK":
                continue
            tables = resp.get("tables", [])
            if len(tables) < 9 or not tables[8].get("data"):
                continue
            mapping = {}
            for row in tables[8]["data"]:
                code = row[0].strip()
                try:
                    mapping[code] = float(str(row[8]).replace(",", ""))
                except (ValueError, IndexError):
                    mapping[code] = None
            print(f"[TWSE] 官方收盤核對來源：{date_str}（{len(mapping)} 檔）")
            return date_str, mapping
        except Exception as e:
            print(f"[TWSE] {date_str} 抓取失敗: {e}")
            continue
    print("[TWSE] 官方收盤核對來源抓取失敗，本次改用 yfinance 原始價格（無交叉核對）")
    return None, {}

_TWSE_PRICE_DATE, _TWSE_OFFICIAL_CLOSES = fetch_twse_official_closes()
_twse_override_count = 0

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

# ══════════════════════════════════════════════════════════════
# 資產規模：兆豐證券 ETF 專區（www.emega.com.tw）
#   yfinance 的 fast_info.market_cap 對台股 ETF 永遠回 0，所以 aum 長年是 0
#   （203 檔全部 0）。emega 的 api/etf 一次給 358 檔的「資產規模億」，
#   2026-10-02 實測可補 202/203。
#   流程：先 GET 頁面拿 cookie 與 <meta name="_csrf">，再 POST 回 api/etf。
#   ⚠ POST 一定要帶 body（即使是空字串）。少了 Content-Length 會被站前面的
#     Akamai 擋成 411 Bad Request，而且錯誤頁長得不像 API 回應，很難查。
#   ⚠ 只取規模。同一支 API 的「配息頻率」**不能用**——那是公開說明書的
#     「收益分配**評價**頻率」，不是實際有沒有配息。2026-10-02 實測 148 檔
#     有 14 檔對不上，全是我們標「不配息」它標「年配／季配」。抽查 00646
#     元大S&P500，MoneyDJ 明確「查無配息資料」，是我們對。拿它覆蓋會把
#     009822 那類累積型、以及 00989A 那種「過了評價月但決定不配」全部寫壞。
# ══════════════════════════════════════════════════════════════
EMEGA_BASE = "https://www.emega.com.tw/etfmaster"


def fetch_emega_aum():
    """回傳 {代號: 資產規模(元)}。失敗回空 dict，呼叫端沿用原本的 0。"""
    try:
        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0"
        page = s.get(f"{EMEGA_BASE}/analyze/index2.do", timeout=20).text
        m = re.search(r'name="_csrf"\s+content="([^"]+)"', page)
        if not m:
            print("[emega] 找不到 CSRF token，略過資產規模")
            return {}
        r = s.post(f"{EMEGA_BASE}/api/etf", data="",
                   headers={"X-XSRF-TOKEN": m.group(1),
                            "Referer": f"{EMEGA_BASE}/analyze/index2.do"},
                   timeout=30)
        rows = (r.json() or {}).get("data") or {}
    except Exception as e:
        print(f"[emega] 資產規模抓取失敗（沿用原值）: {e}")
        return {}
    out = {}
    for c, v in rows.items():
        try:
            yi = float(str((v or {}).get("資產規模億", "")).strip())
        except (TypeError, ValueError):
            continue
        if yi > 0:
            out[c] = round(yi * 1e8)        # 億 → 元
    print(f"[emega] 資產規模 {len(out)} 檔")
    return out


# ── 主流程 ──────────────────────────────────────────────────────────
ALL_ETFS  = build_pool()
EMEGA_AUM = fetch_emega_aum()

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

        # TWSE 官方收盤價覆蓋（上市 ETF 適用；上櫃 .TWO 無此 yfinance NaN 問題，略過）
        # 徹底避免 yfinance 整批延遲/NaN 導致 price 悄悄停留在前一交易日
        if code not in TWO_CODES and code in _TWSE_OFFICIAL_CLOSES:
            official_price = _TWSE_OFFICIAL_CLOSES[code]
            if official_price is not None and official_price > 0 and abs(official_price - price) > 0.011:
                print(f"[TWSE-OVERRIDE] {code} yfinance={price} → TWSE官方({_TWSE_PRICE_DATE})={official_price}")
                price  = official_price
                low52  = round(min(low52, price), 2)
                high52 = round(max(high52, price), 2)
                _twse_override_count += 1

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
        # 上市未滿約1年：改用「1年視窗最早一筆日期」而非交易日筆數判斷。
        # 2026-07-21 發現：冷門/低成交量 ETF（如 020032）即使上市超過2年，
        # 因為不是每天都有成交，period="1y" 抓回的筆數仍可能 <240，被誤判為新上市。
        # 只要最早一筆日期夠接近「1年前」（留15天緩衝防假日/停牌），代表資料涵蓋滿1年，就不是新上市。
        _one_yr_ago = (datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ) - datetime.timedelta(days=365)).date()
        new_listing = hist.index[0].date() > _one_yr_ago + datetime.timedelta(days=15)
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

        # 規模優先用 emega（yfinance 對台股 ETF 的 market_cap 永遠是 0）
        aum = float(EMEGA_AUM.get(code, 0) or 0)
        yld = 0.0
        if not aum:
            try:
                info = tk.fast_info
                aum = safe(getattr(info, "market_cap", 0) or 0)
            except Exception:
                pass
        import pandas as _pd
        divs = tk.dividends  # 一次抓，配息預測共用

        # 先偵測配息頻率，殖利率年化計算需要用到
        div_freq = detect_div_freq(tk, code, name, hist_days=len(hist))

        # 殖利率單源串接：ETFortune（官方）→ FinMind → yfinance trailing 12M
        yld, yld_verified = 0.0, False
        twse_yld = fetch_twse_etfortune_yld(code, price, div_freq)
        if twse_yld > 0:
            yld, yld_verified = twse_yld, True
        else:
            fm_yld = fetch_finmind_yld(code, price, div_freq)
            if fm_yld > 0:
                yld, yld_verified = fm_yld, True
            elif price > 0:
                # yfinance 保底：取過去365天實際配息加總
                try:
                    cutoff = _pd.Timestamp.now(tz='UTC') - _pd.Timedelta(days=365)
                    idx = divs.index.tz_convert('UTC') if divs.index.tz else divs.index.tz_localize('UTC')
                    annual = float(divs[idx > cutoff].sum())
                    if annual > 0:
                        yld = round(annual / price * 100, 1)
                except Exception:
                    pass

        # 手動覆寫：人工查證過的直接視為 verified
        if code in _YLD_OVERRIDE:
            yld = _YLD_OVERRIDE[code]
            yld_verified = True

        yld_pending = code in _YLD_PENDING

        signal, maD = calc_signal(price, ma20, ma60, low52, high52,
                                   ret5d, vol_ratio, rsi, yld, name, code)
        heat, score_cont = calc_heat_score(cur_vol, avg_vol, aum, today_chg, recent_vols, curated)
        div_days, div_est, div_next = calc_div_forecast(divs, code, div_freq)

        results.append({
            "code": code, "name": name, "curated": curated,
            # 上櫃註記：mis_fetcher 要靠它決定 MIS 用 otc_ 還是 tse_ 前綴
            "otc": code in TWO_CODES,
            "price": safe(price), "ma60": safe(ma60), "ma20": safe(ma20),
            "low52": safe(low52), "high52": safe(high52),
            "rsi": safe(rsi),
            "yld": safe(yld), "yld_verified": yld_verified, "yld_pending": yld_pending, "days": div_days,
            "est": div_est, "div_next": div_next,
            "signal": signal, "maD": safe(maD),
            "ret5d": safe(ret5d), "ret1m": safe(ret1m),
            "ret1y": safe(ret1y, default=None), "ret_months": ret_months, "new_listing": new_listing,
            "avg_vol": safe(avg_vol), "cur_vol": safe(cur_vol),
            "vol_ratio": safe(vol_ratio), "heat": safe(heat), "score_cont": safe(score_cont),
            "aum": safe(aum), "div_freq": div_freq,
        })
        tag = "精選" if curated else "自動"
        print(f"[{tag}] {code} {name}  {price}  sig={signal}  vol={avg_vol:.0f}")

    except Exception as e:
        if curated:
            # 精選池即使失敗也要輸出（保持計算機可用）
            results.append({
                "code": code, "name": name, "curated": True,
                "otc": code in TWO_CODES,
                "price": 0, "ma60": 0, "ma20": 0, "low52": 0, "high52": 0,
                "rsi": 50,
                "yld": 0, "yld_verified": False, "days": DIV_DAYS.get(code, 90), "est": DIV_EST.get(code, 0.30),
                "div_next": None, "signal": "dear", "maD": 0,
                "ret5d": 0, "ret1m": 0, "ret1y": None, "ret_months": [0,0,0,0,0,0], "new_listing": False,
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
        resp = _json.loads(r.read().decode("utf-8"))
    rows = resp.get("data", [])
    if not rows:
        return None
    # 最後一筆（13:30:00）= 收盤，欄位 index 1 = 加權指數
    last = rows[-1]
    cur = float(str(last[1]).replace(",", ""))
    if cur <= 0:
        return None
    # 從 API date 欄位取得資料日期，再找「該日之前」最後一個交易日的 yfinance 收盤
    # 避免盤前執行時 yfinance 尚未更新昨日資料導致 iloc[-2] 跳到錯誤的日期
    date_str = resp.get("date", "")
    try:
        data_date = datetime.date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError, IndexError):
        now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        data_date = (now_tw.date() - datetime.timedelta(days=1) if now_tw.hour < 9
                     else now_tw.date())
    twii = yf.Ticker("^TWII")
    h = twii.history(period="5d")
    if h.empty:
        return None
    dates = [idx.date() if hasattr(idx, "date") else idx for idx in h.index]
    past = [float(h["Close"].iloc[i]) for i, d in enumerate(dates) if d < data_date]
    if not past:
        return None
    prev = past[-1]
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
    "twse_price_check_date": _TWSE_PRICE_DATE,   # None 代表本次 TWSE 官方核對來源抓取失敗
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
if _TWSE_PRICE_DATE:
    print(f"✓ TWSE 官方收盤核對（{_TWSE_PRICE_DATE}）：覆蓋 {_twse_override_count} 支價格")
else:
    print("⚠ 本次未能取得 TWSE 官方收盤核對來源，price 僅來自 yfinance")
