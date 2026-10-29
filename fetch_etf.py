import json, math, datetime, os, ssl, re, requests, sys
import urllib.request as _ur
from pathlib import Path
import yfinance as yf
sys.path.append(str(Path(__file__).resolve().parent / "scripts"))
from json_safe import (atomic_write_json, nullify_nonfinite, validate_base, validate_base_policy, validate_dividend_info,   # noqa: E402
                       validate_pool_cache, validate_excluded_products)
import product_policy as _policy   # noqa: E402
import official_frequency as _official   # noqa: E402  D-068：官方政策證據／待公告解除的單一驗證規則

# Windows 本機主控台常是 cp950，print() 遇到 ✓/⚠ 等符號會 UnicodeEncodeError 整支腳本崩潰
# （GitHub Actions 的 Ubuntu 預設 UTF-8 不受影響，但本機手動執行會中招，2026-07-08 發現）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OUT_BASE  = Path(__file__).parent / "data" / "_base.json"
OUT_MARKET = Path(__file__).parent / "data" / "market.json"   # 初始化核對用（唯讀）
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
            and _official.known_policy(code, meta) is not None            # D-068／D-071：附了任一種證據就必須有效
        }
    except Exception:
        return {}

_CONFIRMED_FREQ = _load_confirmed_freq()


def _load_div_meta():
    """D-068：dividend_info.json 逐檔原始紀錄（唯讀）：官方政策證據與待公告解除紀錄由 official_frequency 驗證後才採用。"""
    try:
        with open(OUT_DIV, encoding="utf-8") as f:
            etfs = json.load(f).get("etfs", {})
        return etfs if isinstance(etfs, dict) else {}
    except Exception:
        return {}


_DIV_META = _load_div_meta()
# 已驗證官方政策證據（含 _todo:true；政策已核實不代表金額已核實）
_EVIDENCE_FREQ = {code: meta["frequency"] for code, meta in _DIV_META.items()
                  if isinstance(meta, dict) and "frequency_evidence" in meta and _official.policy_evidence_problem(code, meta) is None
                  and _official.known_policy(code, meta) is not None}   # D-071：同檔若另附失效 policy_source 也不採用

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
def _yld_pending_for(code):
    """D-068：「待公告」＝在 _YLD_PENDING 且該段待公告沒有有效的官方公告解除紀錄（daily_check 查證後寫入 dividend_info）。
    解除紀錄綁定同一段 pending_since，人工改了查證日期就要重新查證；靜態清單不會把已解除的蓋回去。"""
    if code not in _YLD_PENDING:
        return False
    return _official.pending_resolution_problem(code, _DIV_META.get(code), _YLD_PENDING[code]) is not None


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

_OFFICIAL_FREQ_RECOVERIES = {}


def fetch_div_freq_twse(code):
    """Resolve explicit, fund-identified TWSE policy; never scan a generic page."""
    from scripts.official_frequency import resolve_frequency
    result = resolve_frequency(code)
    if result.get("status") == "verified":
        _OFFICIAL_FREQ_RECOVERIES[code] = result
        return result["frequency"]
    print("[FREQ] %s official policy unresolved: %s" % (code, result.get("reason")))
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
    # 0b. D-068：dividend_info 已驗證的官方政策證據（例：發行人文件明確不分配收益）
    evidenced = _EVIDENCE_FREQ.get(code)
    if evidenced:
        return evidenced
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
            # D-062：沒有配息歷史不等於「不配息」（可能尚未首次配息、資料源缺漏）。
            # 前面的已核靜態／人工表／名稱／官方政策都沒有結果時一律回「不明」，
            # 不論交易天數多長；確認不配息只能來自上述可信來源。
            return "不明"
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
    '正2', '反1', '正二', '反一', '公債', '公司債', '高收益', '不動產',
    'REITs', '基礎建設', '優先股', '可轉換', '黃金', '原油',
    '石油', '天然氣', '白銀', '農產',
    'R1', 'R2',   # 受益憑證（01xxxT），非 ETF
]

# 代號字尾 L＝槓桿、R＝反向、U＝期貨／商品。2026-10-05 實測 ISIN ETF 區段 382 檔，
# 字尾與名稱完全一致（0 例外）。名稱關鍵字擋不住簡稱（02001L 富邦蘋果正二N、
# 00682U／00693U／00763U），所以用代號擋。A／B／D／K／C 等字尾不受影響。
EXCLUDE_SUFFIX = ('L', 'R', 'U')

# 商品收錄政策（PO 2026-10-10 永久規則）：不收錄代號尾碼 K 的商品、不收錄任何 ETN。
# 稽核清單 data/excluded_products.json 讀不到或格式錯 → 直接丟例外結束（fail-closed，不當成沒有排除商品）。
EXCLUDED_CODES = _policy.listed_codes()

# ISIN 頁的區段名 → 該區段 CFI 應有的前綴。**只收 ETF 區段且 CFI 為 CE… 的列**；
# ETN 區段（CFI CM…）只用來交叉排除與提醒補登稽核清單，不收錄（PO 2026-10-10）。
ISIN_SECTIONS = {'ETF': 'CE'}
ISIN_ETN_SECTION = ('ETN', 'CM')
POOL_STATUS = {'markets_ok': 0}   # 本輪 ISIN 成功的市場別數（2＝上市＋上櫃都成功），build_pool 用來驗 CURATED
_SECTION_RE = re.compile(r'<tr><td[^>]*colspan=7[^>]*>\s*<B>\s*(.*?)\s*<B>', re.I)
_TD_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.I | re.S)


def pool_excluded(code, name):
    """資料池篩選鏈②③④：回傳排除原因字串，通過則回傳 None。
    ISIN 即時抓取、etf_pool_cache.json fallback、CURATED 都走這一支。"""
    if not code or not name:
        return 'empty'
    if not code.startswith('0'):        # ② 排除 TDR（9xxx）等
        return 'not-0'
    if code.endswith('T'):              # ② 排除受益憑證（01004T 等）
        return 'suffix-T'
    if code.endswith(EXCLUDE_SUFFIX):   # ③ 槓桿／反向／期貨
        return 'suffix-' + code[-1]
    pol = _policy.exclusion_reason(code, EXCLUDED_CODES)   # ⑤ K 尾碼／ETN 稽核清單（PO 2026-10-10）
    if pol:
        return pol
    if any(kw in name for kw in EXCLUDE_KW):  # ④ 名稱關鍵字
        return 'keyword'
    return None


# etf_pool_cache.json 新格式每列是 {code, name, is_otc, section, cfi}，保存 ISIN 區段與 CFI，fallback 時照它驗類型。
# 舊格式 [code, name, is_otc] 沒有類型資訊 → 保守規則：只認 00 開頭代號（2026-10-05 實測 ISIN 上市＋上櫃
# ETF 區段 360 檔代號全為 00 開頭；02 開頭全在 ETN 區段，一律不收；其他區段沒有 00 開頭代號）。
# 舊程式讀到頁尾時誤收的 01111S～01114S（受益證券-資產基礎證券）也靠這條擋。
_CACHE_PRODUCT_RE = re.compile(r'00[0-9]{2,4}[A-Z]?')


def cache_product_ok(code):
    """舊格式 cache fallback 的產品類型防線：只認 ETF（00…）代號格式；ETN（02…）與類型不明一律不收。"""
    return bool(_CACHE_PRODUCT_RE.fullmatch(code or ''))


def cache_row_ok(r):
    """cache 一列 → (code, name, is_otc) 或 None。新格式要 section＝ETF、CFI 為 CE…；舊格式走 cache_product_ok。"""
    if isinstance(r, dict):
        code, name = r.get('code'), r.get('name')
        if (r.get('section') != 'ETF' or not str(r.get('cfi') or '').startswith(ISIN_SECTIONS['ETF'])
                or not isinstance(code, str) or not code or not isinstance(name, str) or not name):
            return None
        return code, name, bool(r.get('is_otc'))
    if isinstance(r, (list, tuple)) and len(r) >= 2 and r[0] and r[1] and cache_product_ok(r[0]):
        return r[0], r[1], bool(r[2]) if len(r) > 2 else False
    return None


def isin_sections(html):
    """切出 ISIN 頁的區段 {區段名: 區段 HTML}，每段只到下一個區段標題列為止。"""
    marks = [(m.group(1).strip(), m.start(), m.end()) for m in _SECTION_RE.finditer(html)]
    out = {}
    for k, (title, _, end) in enumerate(marks):
        stop = marks[k + 1][1] if k + 1 < len(marks) else len(html)
        out.setdefault(title, html[end:stop])
    return out


# D-044：本輪 ISIN 原文解析到的上市日 {code: "YYYY-MM-DD"}。ISIN 本輪失敗（走 cache fallback）就是空的
# → 歷史不足的已上市 ETF 沒有可追溯上市日，不走 history_fallback（寧可不收也不猜上市日）。
ISIN_LISTING_DATE = {}


def parse_isin_rows(section, cfi_prefix, label=''):
    """解析一個區段的資料列 → [(code, name, cfi)]；CFI 不符預期前綴的列印警告後略過。"""
    out = []
    for row in re.split(r'<tr>', section, flags=re.I):
        tds = _TD_RE.findall(row)
        if len(tds) < 6 or '　' not in tds[0]:
            continue
        code, name = (x.strip() for x in tds[0].split('　', 1))
        cfi = tds[5].strip()
        if not cfi.startswith(cfi_prefix):
            print("[POOL] %s %s %s CFI=%s 不是 %s…，略過" % (label, code, name, cfi, cfi_prefix))
            continue
        out.append((code, name, cfi))
        # D-044：同一 ISIN 原文的「公開發行／上市日」（第 3 欄 YYYY/MM/DD）只另存備查，不改回傳契約與證據檔格式
        _ld = re.fullmatch(r'(\d{4})/(\d{2})/(\d{2})', tds[2].strip())
        if _ld:
            # 既有測試會把本函式單獨抽出執行（沒有模組層級的 ISIN_LISTING_DATE），所以經 globals() 取用
            globals().setdefault("ISIN_LISTING_DATE", {})[code] = "%s-%s-%s" % _ld.groups()
    return out


def parse_isin_pool_typed(html, label=''):
    """從一個市場別的 ISIN 頁取出資料池候選 [(code, name, cfi)]（篩選鏈①～⑤）。
    只收「ETF」區段且 CFI 為 CE… 的列；找不到 ETF 區段 → 丟例外（視為該市場別抓取失敗，不退回整頁解析）。
    ETN 區段不收錄：它的代號若也出現在 ETF 區段 → 一併排除（fail-closed）；不在稽核清單 → 印警告請補登。
    找不到 ETN 區段 → 印警告；收錄仍只看 ETF 區段＋CFI，不會因此放進任何 ETN。"""
    secs = isin_sections(html)
    if 'ETF' not in secs:
        raise ValueError("找不到 ETF 區段（%s）" % label)
    etn_title, etn_prefix = ISIN_ETN_SECTION
    etn = set()
    POOL_STATUS['last_etn'] = {}            # 本頁 ETN 區段 {代號: CFI}（CM…），供既有 ETF 改列 ETN 的可信判斷
    if etn_title in secs:
        for code, name, cfi in parse_isin_rows(secs[etn_title], etn_prefix, label):
            etn.add(code)
            POOL_STATUS['last_etn'][code] = cfi
            if code not in EXCLUDED_CODES and not code.endswith(EXCLUDE_SUFFIX):
                print("[POOL] %s ETN %s %s 不在 excluded_products.json，已排除；請補登稽核清單" % (label, code, name))
    else:
        print("[POOL] %s 找不到 ETN 區段（收錄仍只認 ETF 區段＋CFI）" % label)
    out, seen = [], set()
    for title, prefix in ISIN_SECTIONS.items():
        for code, name, cfi in parse_isin_rows(secs[title], prefix, label):
            if code in seen or code in etn or pool_excluded(code, name):
                continue
            seen.add(code)
            out.append((code, name, cfi))
    return out


def parse_isin_pool(html, label=''):
    """parse_isin_pool_typed 的 (code, name) 版。"""
    return [(c, n) for c, n, _ in parse_isin_pool_typed(html, label)]


def _isin_etf_pool(str_mode):
    """抓 ISIN 某一市場別的 ETF 候選（不含 ETN），回傳 [(code, name, cfi)]。strMode=2 上市、4 上櫃。"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = _ur.Request(
        'https://isin.twse.com.tw/isin/C_public.jsp?strMode=%s' % str_mode,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with _ur.urlopen(req, timeout=20, context=ctx) as r:
        html = r.read().decode('ms950', errors='ignore')
    return parse_isin_pool_typed(html, 'strMode=%s' % str_mode)


# D-055（D-056 對齊到 ETF 類型證據契約）：商品池完整性。2026-10-16 正式事故：上櫃 ISIN 抓取失敗
# （官方 log：Connection reset by peer），舊程式把上市部分清單寫進快取，上櫃一般 ETF 18 檔從 _base／market 消失（200→182）。
# 正式版 D-055 的 v2 快取（列數＋原始回應 sha256）在這裡不再寫出；etf_pool_cache.json 只有一種可信格式＝ETF 類型證據
# （每列 ISIN 區段＋CFI＋seen，product_policy）。等價規則：
#   - 任一市場失敗／空結果／缺 ETF 區段 → 不寫證據；有證據時兩市場既有資格全部保留（plan_pool），沒有證據 → PoolIncomplete。
#   - 兩市場都成功但少列既有代號 → 不推定下架：保留舊資格並記 absent_since（plan_pool），合併後證據不得縮水（evidence_shrink）。
#   - 最終候選（含單邊失敗時沿用證據的結果）寫任何檔之前，逐代號比對現有 _base.json ∪ market.json；
#     少了無法以排除清單（K／ETN／PO_REMOVED）或本輪可信 ETN 變更解釋的代號 → PoolIncomplete，不寫證據／排除清單／_base。
#   - D-055 v2 記錄與舊格式 list 都沒有 CFI：不升格成資格證據、不當補齊來源（read_prev_evidence）。
POOL_CACHE_V2_FORMAT = "etf-pool-cache/v2"


class PoolIncomplete(Exception):
    """商品池不完整（沒有可信證據可補、或最終候選少了既有一般 ETF）：不得以部分商品池繼續。"""


def read_prev_evidence():
    """上一版 ETF 類型證據；D-055 v2 完整性記錄（沒有 CFI）視同沒有證據（None），不升格、不拿來補齊。
    新格式證據損壞 → PolicyError（fail-closed）。"""
    try:
        obj = json.load(open(POOL_CACHE, encoding="utf-8"))
    except Exception:
        obj = None                                          # 不存在／讀不到：交給 read_evidence_file 判斷（存在但損壞 → PolicyError）
    if isinstance(obj, dict) and obj.get("format") == POOL_CACHE_V2_FORMAT:
        print("[POOL] etf_pool_cache.json 是 D-055 v2 完整性記錄（沒有 ISIN 區段／CFI），不當 ETF 類型證據；"
              "需一次上市＋上櫃都成功的完整查核初始化")
        return None
    return _policy.read_evidence_file(POOL_CACHE)


def pool_missing_codes(pool, etn_new):
    """最終候選與現有 _base.json ∪ market.json 逐代號比對：回傳無法以排除清單或本輪可信 ETN 變更解釋的缺少代號。
    檔案損壞 → PolicyError（fail-closed）；檔案不存在 → 該檔不計。"""
    have = {c for c, _, _ in pool}
    return sorted(c for c in _init_codes() if c not in have and not _policy.exclusion_reason(c, EXCLUDED_CODES)
                  and c not in etn_new)


def fetch_twse_etf_pool():
    """抓 ISIN 的股票型 ETF 清單（**上市 + 上櫃**），回傳 [(code, name, is_otc)]。
    資料池成員與 etf_pool_cache.json（ETF 類型證據）由 update_pool_evidence 決定（D-014）。

    ⚠ 一定要連上櫃一起抓。2026-09-27 以前只讀 strMode=2，上櫃 ETF 全部進不了池子，
      只有 CURATED 裡寫死的 00928/006201 例外——結果成交量排第 32 名的 00411A
      （主動統一前沿科技）、第 33 名的 00998A 都不在排行榜上，
      連我們自己有抓持股異動的 00411A 都連不回排行頁。
    """
    POOL_STATUS['markets_ok'] = 0
    POOL_STATUS['plan'] = None
    _clear_check_report()                   # 本輪開始：舊摘要作廢，daily_check 不會拿到上一輪（或早上）的結果
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()
    today_etf, today_etn, errors = {}, {}, {}
    for str_mode, is_otc, lab in ((2, False, "上市"), (4, True, "上櫃")):
        try:
            got = _isin_etf_pool(str_mode)
        except Exception as e:
            # 其中一邊掛掉不要拖垮另一邊，但一定要出聲——靜默縮水是這專案的老毛病
            print("[POOL] ISIN strMode=%s（%s）抓取失敗: %s" % (str_mode, lab, e))
            today_etf[is_otc] = None
            errors[lab] = "%s: %s" % (type(e).__name__, e)
            continue
        if not got:                                         # D-055：空結果視同該市場失敗，不當完整查核
            print("[POOL] ISIN strMode=%s（%s）結果為空，視為該市場失敗" % (str_mode, lab))
            today_etf[is_otc] = None
            errors[lab] = "空結果"
            continue
        POOL_STATUS['markets_ok'] += 1
        today_etf[is_otc] = [r if len(r) > 2 else (r[0], r[1], ISIN_SECTIONS['ETF']) for r in got]
        today_etn[is_otc] = dict(POOL_STATUS.get('last_etn') or {})
        errors[lab] = "ok"
        print("[POOL] %s股票型 ETF: %d 支" % (lab, len(got)))
    return update_pool_evidence(today_etf, today_etn, errors, today)


def _check_report_path():
    import os, tempfile
    return os.environ.get("ETF_POOL_CHECK_REPORT") or os.path.join(tempfile.gettempdir(), "etf_pool_check.json")


def _run_id():
    """本輪執行識別：Actions 同一 job 內各步驟相同（GITHUB_RUN_ID＋ATTEMPT）；本機可用 ETF_RUN_ID。都沒有 → None
    （daily_check 不會接受沒有執行識別的摘要）。"""
    import os
    if os.environ.get("GITHUB_RUN_ID"):
        return "%s-%s" % (os.environ["GITHUB_RUN_ID"], os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    return os.environ.get("ETF_RUN_ID") or None


def _clear_check_report():
    import os
    try:
        os.remove(_check_report_path())
    except FileNotFoundError:
        pass
    except Exception as e:
        print("[POOL] 舊查核摘要無法刪除：%s" % e)


def _sha256_file(path):
    import hashlib
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def _write_check_report(report):
    """本輪官方查核摘要（daily_check 用來附在通知裡）。暫存檔，不在 data/、不發布。
    綁定本輪執行（run）與寫出當下的證據／排除清單內容（SHA256），daily_check 只接受完全相符的摘要。"""
    report = dict(report, run=_run_id(), evidence_sha256=_sha256_file(POOL_CACHE),
                  excluded_sha256=_sha256_file(_policy.POLICY_FILE))
    try:
        with open(_check_report_path(), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False)
    except Exception as e:
        print("[POOL] 查核摘要寫入失敗：%s" % e)


def _init_codes():
    """初始化核對對象：現有 _base.json 與 market.json 的商品聯集。檔案不存在 → 該檔不計；
    存在但讀不到／不是 {etfs: [{code: 字串}]} → 例外（fail-closed，不當成空集合）。"""
    out = set()
    for p in (OUT_BASE, OUT_MARKET):
        if not Path(p).exists():
            continue
        try:
            doc = json.load(open(p, encoding="utf-8"))
            etfs = doc.get("etfs")
            if not isinstance(etfs, list) or not all(isinstance(e, dict) and isinstance(e.get("code"), str) for e in etfs):
                raise ValueError("etfs 不是 [{code: 字串}]")
        except Exception as e:
            raise _policy.PolicyError("初始化無法核對 %s：%s: %s" % (Path(p).name, type(e).__name__, e))
        out |= {e["code"] for e in etfs}
    return out


def update_pool_evidence(today_etf, today_etn, errors, today):
    """D-014：ISIN 上市＋上櫃都成功的那一次才改變資料池成員與證據檔；其他情況沿用最後有效證據。
    完整查核：合併（列出的 seen＝今天；缺席保留舊 seen 記 absent_since；新合格 ETF 加入；官方 ETN 區段＋CM 的
    既有代號登錄排除清單 ETN）。寫出前檢查：初始化須涵蓋現有 _base.json ∪ market.json 全部未排除代號、合併後不得縮水；
    不符 → 不寫任何檔、exit 1（保留最後有效資料）。不完整：證據檔不寫；兩市場既有未排除資格全部保留；
    當天新出現、證據沒有的代號暫緩到下一次完整查核。"""
    report = {"checked_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
              "source": "TWSE ISIN C_public.jsp strMode=2（上市）／4（上櫃）", "markets": errors,
              "full": False, "listed": [], "absent": [], "deferred": [], "etn_registered": [], "init_missing": []}
    prev = read_prev_evidence()                             # 新格式但損壞 → PolicyError → 整支結束（fail-closed）
    plan = _policy.plan_pool(prev, today_etf, today_etn, EXCLUDED_CODES, today)
    if plan is None:                                        # 沒有可用證據又不完整：不以部分結果繼續（D-055）
        _write_check_report(report)
        raise PoolIncomplete("ISIN 不完整（%s）且沒有新格式 ETF 類型證據可沿用——不寫證據／_base，既有資料保留"
                             % "；".join("%s=%s" % kv for kv in errors.items()))
    # D-055：寫任何檔之前，最終候選逐代號比對現有 _base.json ∪ market.json（含單邊失敗時沿用證據的結果）
    missing = pool_missing_codes(plan["pool"], plan["etn_new"])
    if missing:
        report["init_missing" if prev is None else "pool_missing"] = missing
        _write_check_report(report)
        if prev is None:                                    # 初始化沿用既審訊息與結束方式
            print("::error::[POOL] 首次 ETF 類型證據沒有涵蓋現有 _base.json／market.json 的 %d 檔一般 ETF，不寫入、不發布：%s"
                  % (len(missing), missing[:20]), file=sys.stderr)
            sys.exit(1)
        raise PoolIncomplete("本次候選商品池缺少現有 _base.json／market.json 的一般 ETF %d 檔（%s；%s），"
                             "無排除清單／可信 ETN 變更依據——不寫證據／_base，待核對"
                             % (len(missing), missing[:20], "完整查核" if plan["full"] else "單邊失敗沿用證據"))
    POOL_STATUS['plan'] = plan
    report.update(full=plan["full"], absent=plan["absent"], deferred=plan["deferred"],
                  listed=sorted(c for rows in today_etf.values() if rows for c, _, _ in rows))
    if not plan["full"]:
        print("[POOL] ISIN 只有 %d 個市場別成功：沿用最後有效證據 %d 檔，不覆寫 etf_pool_cache.json"
              % (POOL_STATUS['markets_ok'], len(plan["pool"])))
        if plan["deferred"]:
            print("[POOL] 單邊成功，新代號暫緩到下次完整查核：%s" % plan["deferred"])
        _write_check_report(report)
        return plan["pool"]
    new_rows = plan["evidence"]
    # 初始化涵蓋檢查（現有 _base.json ∪ market.json 全部未排除商品）已在上方對所有路徑執行
    shrink = _policy.evidence_shrink(prev, new_rows, EXCLUDED_CODES | set(plan["etn_new"]))
    if shrink:                                              # 先檢查、後寫檔：任何檢查失敗都不留下半套變更
        print("::error::[POOL] 合併後證據少了 %d 檔未排除代號，不寫入：%s" % (len(shrink), shrink[:20]), file=sys.stderr)
        _write_check_report(report)
        sys.exit(1)
    if plan["etn_new"]:                                     # 可信 ETF→ETN 變更：登錄排除清單（同一批由 Gate 發布）
        pol = _policy.load_policy()
        for c, (name, cfi, otc) in plan["etn_new"].items():
            pol["products"][c] = {"name": name, "type": "ETN", "reason": "ISIN 改列 ETN 區段（CFI %s）" % cfi,
                                  "source": "TWSE ISIN C_public.jsp strMode=%d ETN 區段" % (4 if otc else 2),
                                  "confirmed": today,
                                  "notify_pending": True}   # 待通知 PO；daily_check 送達後才清除，失敗下輪重送
        try:
            atomic_write_json(_policy.POLICY_FILE, pol, validate=validate_excluded_products)
        except Exception as e:
            print("::error::[POOL] 排除清單寫入失敗（不更新證據）：%s" % e, file=sys.stderr)
            _write_check_report(report)
            sys.exit(1)
        EXCLUDED_CODES.update(plan["etn_new"])
        report["etn_registered"] = sorted(plan["etn_new"])
        print("::warning::[POOL] 依 ISIN ETN 區段登錄排除：%s" % sorted(plan["etn_new"]))
    try:
        atomic_write_json(POOL_CACHE, new_rows, validate=validate_pool_cache)
    except Exception as e:
        print("::error::[POOL] etf_pool_cache.json 寫入失敗（原檔保留）：%s" % e, file=sys.stderr)
        _write_check_report(report)
        sys.exit(1)
    if plan["absent"]:
        print("[POOL] 完整查核未列出、保留舊資格：%s" % plan["absent"][:20])
    _write_check_report(report)
    return plan["pool"]

def build_pool():
    """精選池 + ISIN 自動發現池合併，精選碼不重複。
    ISIN 失敗時 fallback etf_pool_cache.json（上次成功的清單），避免縮水成 13 支精選。
    順便把自動發現的上櫃碼補進 TWO_CODES，yfinance 才會用 .TWO 後綴去抓。
    """
    auto = fetch_twse_etf_pool()          # D-055 完整性檢查在 update_pool_evidence（寫任何檔之前）

    if not auto:
        if POOL_CACHE.exists():
            try:
                cached = json.load(open(POOL_CACHE, encoding="utf-8"))
                # cache 可能是舊的兩元組 [(code, name)]（2026-09-27 之前只存上市），
                # 補不出市場別時一律當上市，至少不會整批壞掉
                # cache 是舊規則時代寫的也一樣要過篩選鏈（③槓反期貨可能還在裡面）
                # 新格式驗 section＋CFI；舊格式只認 00 開頭（cache_row_ok）；兩者都要再過篩選鏈（含 K／ETN）
                auto = [t for t in (cache_row_ok(r) for r in cached) if t and not pool_excluded(t[0], t[1])]
                print(f"[POOL] ISIN 失敗，從 etf_pool_cache.json fallback 取得 {len(auto)} 支")
            except Exception as fb_err:
                print(f"[POOL] fallback 讀取 cache 失敗: {fb_err}")

    # CURATED 也要過篩選鏈＋商品類型驗證：上市＋上櫃 ISIN 都成功時，必須出現在 ISIN「ETF」區段（CFI CE…）；
    # ISIN 不完整時退回 cache_product_ok（只認 00 開頭），任何情況都不能繞過 K／ETN 排除
    # D-014：有新格式證據時，只認本次資料池（＝證據）中的代號；不完整時不能用「00 開頭」繞過資格
    plan = POOL_STATUS.get('plan')
    verified = ({c for c, _, _ in auto} if (plan is not None or POOL_STATUS.get('markets_ok') == 2) else None)
    pool = []
    for c, n in CURATED:
        ok_type = (c in verified) if verified is not None else cache_product_ok(c)
        why = pool_excluded(c, n) or (None if ok_type else 'curated-unverified')
        if why:
            print(f"[POOL] CURATED {c} {n} 排除：{why}")
            continue
        pool.append((c, n))
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


_DEC_RE   = re.compile(r"[+-]?(?:[1-9]\d{0,2}(?:,\d{3})+|\d+)(?:\.\d+)?")
# ↑ 十進位數字（可帶號、千分位須每 3 位一組）；先驗格式再去逗號。拒 58,3／1,2,3／1,,000／Infinity／NaN／1e3
_SHARE_RE = re.compile(r"[1-9]\d{0,2}(?:,\d{3})+|\d+")   # 非負整數股數（千分位首組不得 0 開頭）
_PRICE_MAX = 1_000_000.0                               # 合理價格上限（防呆，非業務規則）
TWSE_NO_TRADE_CLOSE = "--"                             # MI_INDEX 收盤價欄的無成交標記
TPEX_NO_TRADE_CLOSE = "----"                           # TPEx 收盤欄的無成交標記
TPEX_NO_CHANGE      = "---"                            # TPEx 漲跌欄的不比較標記（無成交時）
TWSE_SIGNS          = {"+", "-", "", "X"}              # MI_INDEX 漲跌(+/-) 欄合法值；X＝不比價


def _dec(s):
    """嚴格十進位數字 → float；空白、"--"、"ERROR"、"Infinity"、"NaN"、"1e3" 等都回 None。"""
    t = str(s).strip()
    if not _DEC_RE.fullmatch(t):
        return None
    v = float(t.replace(",", ""))
    return v if math.isfinite(v) else None


def _shares(s):
    """嚴格非負整數股數 → int；負數、小數、空白、文字回 None（不截斷、不取整）。"""
    t = str(s).strip()
    return int(t.replace(",", "")) if _SHARE_RE.fullmatch(t) else None


def _price(s):
    """有效收盤價：有限、> 0、不超過合理上限；否則 None。"""
    v = _dec(s)
    return v if v is not None and 0 < v < _PRICE_MAX else None


def _roc_date(date_str):
    """'20261008' → ('115年10月08日', '115/10/08')：官方報表內的民國日期寫法。"""
    roc = int(date_str[:4]) - 1911
    return f"{roc}年{date_str[4:6]}月{date_str[6:]}日", f"{roc}/{date_str[4:6]}/{date_str[6:]}"


def _official_record(src, date_iso, close_raw, no_trade_mark, chg, shares_raw):
    """逐檔官方收盤證據。status：traded＝有成交收盤價；no_trade＝官方確認當日無成交（價格 None、成交 0 股）。
    無成交只認來源契約的標記且成交股數＝0；標記與成交股數矛盾、收盤或股數解析失敗 → None（拒絕，不當證據）。"""
    shares = _shares(shares_raw)
    if shares is None:
        return None
    close_txt = str(close_raw).strip()
    if close_txt == no_trade_mark:
        if shares != 0:
            return None
        return {"date": date_iso, "src": src, "status": "no_trade", "price": None,
                "change_pt": None, "prev_close": None, "vol_shares": 0}
    close = _price(close_txt)
    if close is None:
        return None
    prev = round(close - chg, 2) if chg is not None else None
    if prev is not None and not prev > 0:
        chg, prev = None, None                        # 前收盤不合理：漲跌缺值，不虛構
    return {"date": date_iso, "src": src, "status": "traded", "price": close,
            "change_pt": round(chg, 2) if chg is not None else None,
            "prev_close": prev, "vol_shares": shares}


def parse_mi_index_row(row, date_iso):
    """MI_INDEX 每日收盤行情一列 → 逐檔官方收盤證據（給 mis_fetcher 判斷收盤用）。
    欄位：[證券代號, 名稱, 成交股數, 成交筆數, 成交金額, 開, 高, 低, 收盤價, 漲跌(+/-), 漲跌價差, ...]
    收盤價 "--" 且成交股數 0 → 官方確認無成交。漲跌符號是 X（不比價）或不在合法值內、價差無法解析
    → change_pt=None（保留缺值，不否定整筆）。"""
    if len(row) < 11:
        return None
    sign = re.sub(r"<[^>]+>", "", str(row[9])).strip()
    diff = _dec(row[10])
    chg = None
    if sign in TWSE_SIGNS and diff is not None and diff >= 0:
        if sign == "-":
            chg = -diff
        elif sign == "+":
            chg = diff
        elif sign == "" and diff == 0:
            chg = 0.0
    return _official_record("TWSE_MI_INDEX", date_iso, row[8], TWSE_NO_TRADE_CLOSE, chg, row[2])


def parse_tpex_row(row, date_iso):
    """TPEx 上櫃每日收盤行情一列。欄位：[代號, 名稱, 收盤, 漲跌, 開, 高, 低, 成交股數, ...]
    （索引 11／13 是「最後買／賣量（張數）」，不是成交量）。收盤 "----" 且成交股數 0 → 官方確認無成交。
    漲跌是帶號數字（+0.06／-0.30／0.00）；"---" 或無法解析 → None（保留缺值）。"""
    if len(row) < 8:
        return None
    chg_txt = str(row[3]).strip()
    chg = None if chg_txt == TPEX_NO_CHANGE else _dec(chg_txt)
    return _official_record("TPEX_OTC", date_iso, row[2], TPEX_NO_TRADE_CLOSE, chg, row[7])


_MI_INDEX_FIELDS = {0: "證券代號", 2: "成交股數", 8: "收盤價", 9: "漲跌(+/-)", 10: "漲跌價差"}
_TPEX_FIELDS     = {0: "代號", 2: "收盤", 3: "漲跌", 7: "成交股數"}


def twse_rows_from_response(resp, date_str):
    """驗證 MI_INDEX 回應並取出逐檔資料：stat＝OK、回應 date＝要求日期、
    「每日收盤行情」表標題日期＝要求日期、欄位表頭符合預期。任一不符回 None（拒絕當日證據）。
    回傳 (mapping {code: close_or_None}（既有覆蓋用）, rows {code: 證據 or None})。"""
    if not isinstance(resp, dict) or resp.get("stat") != "OK" or str(resp.get("date", "")) != date_str:
        return None
    roc_title, _ = _roc_date(date_str)
    tbl = next((t for t in resp.get("tables", []) if "每日收盤行情" in str(t.get("title", ""))), None)
    if not tbl or roc_title not in str(tbl.get("title", "")) or not tbl.get("data"):
        return None
    fields = [str(f).strip() for f in tbl.get("fields", [])]
    if any(i >= len(fields) or fields[i] != name for i, name in _MI_INDEX_FIELDS.items()):
        return None
    date_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    mapping, rows = {}, {}
    for row in tbl["data"]:
        code = str(row[0]).strip()
        mapping[code] = _price(row[8]) if len(row) > 8 else None   # 既有價格覆蓋：只收有效收盤價
        rows[code] = parse_mi_index_row(row, date_iso)
    return mapping, rows


def tpex_rows_from_response(resp, date_str):
    """驗證 TPEx 上櫃收盤行情回應：stat＝ok、回應 date＝要求日期、表內 date（民國 115/10/08）＝要求日期、
    欄位表頭符合預期（成交股數在索引 7）。任一不符或無資料回 None。回傳 {code: 證據 or None}。"""
    if not isinstance(resp, dict) or str(resp.get("stat", "")).lower() != "ok" or str(resp.get("date", "")) != date_str:
        return None
    _, roc_slash = _roc_date(date_str)
    tbl = (resp.get("tables") or [{}])[0]
    if str(tbl.get("date", "")).strip() != roc_slash or not tbl.get("data"):
        return None
    fields = [re.sub(r"<[^>]+>", "", str(f)).strip() for f in tbl.get("fields", [])]
    if any(i >= len(fields) or fields[i] != name for i, name in _TPEX_FIELDS.items()):
        return None
    date_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return {str(row[0]).strip(): parse_tpex_row(row, date_iso) for row in tbl["data"]}


def _official_get(url):
    import urllib.request as _ur3, ssl as _ssl3
    ctx = _ssl3.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl3.CERT_NONE
    req = _ur3.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with _ur3.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


_TWSE_MARKET_CLOSE = None


def parse_twse_market_close(resp, date_str):
    """重用逐檔收盤同一份MI_INDEX的價格指數表；不額外發請求、不猜日期或昨收。"""
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
    if not isinstance(resp, dict) or resp.get("stat") != "OK" or resp.get("date") != date_str:
        return None
    try:
        day = datetime.datetime.strptime(date_str, "%Y%m%d").date()
        if day > datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date():
            return None
        title = f"{day.year - 1911}年{day.month:02d}月{day.day:02d}日 價格指數(臺灣證券交易所)"
        tables = [t for t in resp.get("tables", []) if isinstance(t, dict) and t.get("title") == title]
        fields = ["指數", "收盤指數", "漲跌(+/-)", "漲跌點數", "漲跌百分比(%)", "特殊處理註記"]
        if len(tables) != 1 or tables[0].get("fields") != fields:
            return None
        rows = [r for r in tables[0].get("data", []) if isinstance(r, list) and r and r[0] == "發行量加權股價指數"]
        if len(rows) != 1 or len(rows[0]) != 6 or str(rows[0][5]).strip():
            return None
        row = rows[0]
        def number(value):
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise ValueError("bad index number")
            text = str(value).strip()
            if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", text):
                raise ValueError("bad index number")
            return Decimal(text.replace(",", ""))
        price, amount, pct = number(row[1]), number(row[3]), number(row[4])
        sign = re.sub(r"<[^>]*>", "", str(row[2])).strip()
        if amount < 0 or sign not in ("+", "-", "") or (not sign and amount != 0):
            return None
        change = -amount if sign == "-" else amount
        prev = price - change
        if price <= 0 or prev <= 0 or (change / prev * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) != pct:
            return None
        if not all(math.isfinite(float(v)) for v in (price, prev, change, pct)):
            return None
        record = {"source": "TWSE_MI_INDEX", "date": day.isoformat(), "price": float(price),
                  "prev_close": float(prev), "change_pt": float(change), "change_pct": float(pct)}
        return {"price": float(price), "change_pt": float(change), "change_pct": float(pct),
                "quote_date": day.isoformat(), "quote_src": "TWSE_MI_INDEX", "is_live": False,
                "close_confirmed": True, "index_close": record}
    except (ValueError, TypeError, KeyError, ArithmeticError, InvalidOperation):
        return None


def fetch_twse_official_closes(max_lookback=6):
    """從今日往回找最近一個有完整收盤資料的交易日，回傳 (date_str, {code: close_or_None}, {code: 證據})。

    2026-07-08 發現：yfinance 對台股上市 ETF 偶發整批回傳最新交易日 Close=NaN，
    dropna() 會悄悄退回前一日舊價，且無任何警報（158/179 支 ETF 曾同時中招）。
    改用 TWSE 官方 MI_INDEX 全市場收盤行情一次性核對/覆蓋 price，徹底避免此類 yfinance 資料延遲問題。

    close_or_None: None 代表當日零成交量（TWSE 顯示 "--"），呼叫端應保留原價，不覆蓋。
    回應日期與要求日期不符（例：要求 10/12 回 10/08）視同該日沒有資料，繼續往回找。
    找不到任何資料（連假、TWSE 暫時性故障）時回傳 (None, {}, {})，呼叫端應 fallback 純用 yfinance。
    """
    global _TWSE_MARKET_CLOSE
    _TWSE_MARKET_CLOSE = None
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    for delta in range(max_lookback):
        d = now_tw.date() - datetime.timedelta(days=delta)
        if d.weekday() >= 5:   # 跳過週末
            continue
        date_str = d.strftime('%Y%m%d')
        try:
            response = _official_get(
                f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
                f"?date={date_str}&type=ALLBUT0999&response=json")
            got = twse_rows_from_response(response, date_str)
            if not got:
                continue
            mapping, rows = got
            _TWSE_MARKET_CLOSE = parse_twse_market_close(response, date_str)
            print(f"[TWSE] 官方收盤核對來源：{date_str}（{len(mapping)} 檔）")
            return date_str, mapping, rows
        except Exception as e:
            print(f"[TWSE] {date_str} 抓取失敗: {e}")
            continue
    print("[TWSE] 官方收盤核對來源抓取失敗，本次改用 yfinance 原始價格（無交叉核對）")
    return None, {}, {}


def fetch_tpex_official_rows(max_lookback=6):
    """TPEx 上櫃每日收盤行情（完整逐檔證據）。與 fetch_active_etf.fetch_tpex_closes 的 {code: price} 契約無關。
    回傳 (date_str, {code: 證據})；找不到回 (None, {})。"""
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    for delta in range(max_lookback):
        d = now_tw.date() - datetime.timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        date_str = d.strftime('%Y%m%d')
        try:
            rows = tpex_rows_from_response(_official_get(
                "https://www.tpex.org.tw/www/zh-tw/afterTrading/otc"
                f"?date={d.strftime('%Y/%m/%d')}&type=EW&response=json"), date_str)
            if not rows:
                continue
            print(f"[TPEx] 官方上櫃收盤：{date_str}（{len(rows)} 檔）")
            return date_str, rows
        except Exception as e:
            print(f"[TPEx] {date_str} 抓取失敗: {e}")
            continue
    print("[TPEx] 官方上櫃收盤抓取失敗，上櫃 ETF 本次沒有官方收盤證據")
    return None, {}

_TWSE_PRICE_DATE, _TWSE_OFFICIAL_CLOSES, _TWSE_OFFICIAL_ROWS = fetch_twse_official_closes()
_TPEX_DATE, _TPEX_OFFICIAL_ROWS = fetch_tpex_official_rows()
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


# ── D-044：已上市但歷史不足的 ETF ───────────────────────────────────
# yfinance 歷史 < 5 筆（例：00412A 10/13 剛上市、00972 Yahoo 只回 1 筆）原本整檔 SKIP，網站就少了這檔。
# 只有「本輪 ISIN 原文有上市日、上市日不晚於官方收盤日、官方收盤證據有成交且日期合法」才保留：
#   價格／成交量＝官方收盤證據；均線、RSI、52 週、平均量、量比、熱度、報酬、maD 一律 null（不填 0、不拿少量資料冒完整期間）；
#   signal＝null（不判便宜／合理／偏貴）；indicator_status＝"insufficient_history"；listing_date＝ISIN 上市日。
# 上市年齡由 ISIN 上市日判斷，不用 Yahoo 第一筆（00972 2025-01-09 上市，Yahoo 只有 1 筆也不是新上市）。
INSUFFICIENT = "insufficient_history"


def _div_freq_offline(code, name):
    """detect_div_freq 的前三步（已確認／手動表／名稱關鍵字），不發任何請求；查不到回「不明」。"""
    f = _CONFIRMED_FREQ.get(code) or DIV_FREQ.get(code)
    if f:
        return f
    for keywords, freq in _NAME_FREQ:
        if any(kw in name for kw in keywords):
            return freq
    return "不明"


def history_fallback(code, name, curated):
    """回傳 (entry, None) 或 (None, 拒絕原因)。"""
    otc = code in TWO_CODES
    rows, ds = (_TPEX_OFFICIAL_ROWS, _TPEX_DATE) if otc else (_TWSE_OFFICIAL_ROWS, _TWSE_PRICE_DATE)
    ld = ISIN_LISTING_DATE.get(code)
    if not ld:
        return None, "本輪 ISIN 沒有可追溯的上市日"
    if not ds or not re.fullmatch(r"\d{8}", str(ds)):
        return None, "沒有官方收盤報表日期"
    off_iso = "%s-%s-%s" % (ds[:4], ds[4:6], ds[6:])
    off = rows.get(code)
    if not off:
        return None, "官方收盤報表沒有這檔"
    if off.get("status") != "traded" or off.get("date") != off_iso:
        return None, "官方收盤證據不是當日有成交（%s／%s）" % (off.get("status"), off.get("date"))
    px = off.get("price")
    if not isinstance(px, (int, float)) or isinstance(px, bool) or not math.isfinite(px) or px <= 0:
        return None, "官方收盤價無效 %r" % (px,)
    vs = off.get("vol_shares")
    if not isinstance(vs, int) or isinstance(vs, bool) or vs < 0:
        return None, "官方成交股數無效 %r" % (vs,)
    try:
        d_list, d_off = datetime.date.fromisoformat(ld), datetime.date.fromisoformat(off_iso)
    except ValueError:
        return None, "上市日或官方日期不合法"
    if d_list > d_off:
        return None, "上市日 %s 晚於官方收盤日 %s（尚未上市）" % (ld, off_iso)
    entry = {
        "code": code, "name": name, "curated": curated, "otc": otc,
        "price": px, "ma60": None, "ma20": None, "low52": None, "high52": None, "rsi": None,
        "yld": 0.0, "yld_verified": False, "yld_pending": _yld_pending_for(code),
        "days": DIV_DAYS.get(code, 90), "est": DIV_EST.get(code, 0.30), "div_next": None,
        "signal": None, "maD": None,
        "ret5d": None, "ret1m": None, "ret1y": None, "ret_months": [None] * 6,
        "new_listing": (d_off - d_list).days < 365,
        "avg_vol": None, "cur_vol": float(vs), "vol_ratio": None, "heat": None, "score_cont": None,
        "aum": safe(float(EMEGA_AUM.get(code, 0) or 0)), "div_freq": _div_freq_offline(code, name),
        "price_date": off_iso, "price_prev": None, "official_close": off,
        "indicator_status": INSUFFICIENT, "listing_date": ld,
    }
    return entry, None


# ── 00972 歷史缺口（2026-10-27）：一年歷史不足時，同 Yahoo 來源的有界替代區間查證 ──
# 原請求 period=1y 不足 5 筆時，先用「主回應 validRanges 明示支援」的較長區間再取一次日線（每檔最多 1 個替代請求、
# 每輪最多 HIST_ALT_LIMIT 檔）；替代結果須核代號、日線粒度、回應區間、唯一且遞增的交易日、有限正價、實際涵蓋滿一年，
# 合格才截成與 period=1y 相同的一年視窗照原計算；近期才有資料≠一年歷史 → 不採用，照 D-044 保留官方價與 null 指標。
# 查證狀態寫到執行期檔 logs/history_check.json（不發布、不進 data）給同一 job 的 daily_check 判斷是否已完成判讀；
# 輪替依 daily_state.history_recheck（daily_check 記錄的上次實際查證時間）由舊到新優先。
# R1（2026-10-28）：只有可查證的舊 ETF（上市滿一年）參與保留額度；查證紀錄綁定本輪執行識別與 _base 實際內容 SHA256、原子寫出。
HIST_ALT_LIMIT  = 4
HIST_ALT_RANGES = ("2y", "5y", "10y", "max")          # 比 1y 長、由短到長；只取主回應 validRanges 有列的
HIST_CHECK_OUT  = Path(os.environ.get("ETF_HISTORY_CHECK") or (Path(__file__).parent / "logs" / "history_check.json"))
HIST_CHECK = {}                                       # {代號: {"status", "detail", "range"}}
HIST_TWSE_USED = False                                # 每輪最多一檔；13月＋商品頁／配息頁最多15個GET
HIST_TWSE_TARGET = None


def _hist_meta(tk):
    """yfinance 最近一次 history() 回應的 metadata（不另發請求；get_history_metadata 會補打 5d／1h，不用）。"""
    try:
        m = getattr(tk._lazy_load_price_history(), "_history_metadata", None)
        return m if isinstance(m, dict) else None
    except Exception:
        return None


def _hist_today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()


def _hist_ineligible(code, today):
    """不具替代查證資格 → (狀態, 說明)；可查證的舊 ETF → None。保留額度與 alt_history 用同一判斷。"""
    ld = ISIN_LISTING_DATE.get(code)
    try:
        d_list = datetime.date.fromisoformat(ld) if ld else None
    except ValueError:
        d_list = None
    if d_list is None:
        return "no_listing", "沒有可追溯的上市日，不做替代查證"
    if (today - d_list).days < 365:
        return "new_listing", "上市 %s 未滿一年，歷史不足屬正常" % ld
    return None


def _hist_alt_plan():
    """額度輪替：上一份 _base 已是歷史不足、且本輪官方上市日可查證滿一年的檔，依 daily_state.history_recheck 由舊到新保留額度；
    新上市／無上市日不占額度。其餘先到先用剩下的。"""
    try:
        prev = json.loads(OUT_BASE.read_text(encoding="utf-8")).get("etfs") or []
        insuff = sorted({e.get("code") for e in prev if isinstance(e, dict) and e.get("indicator_status") == INSUFFICIENT} - {None})
    except Exception:
        insuff = []
    try:
        rech = json.loads((Path(__file__).parent / "data" / "daily_state.json").read_text(encoding="utf-8")).get("history_recheck") or {}
    except Exception:
        rech = {}
    num = lambda v: v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else 0
    today = _hist_today()
    insuff = [c for c in insuff if _hist_ineligible(c, today) is None]
    return insuff and sorted(insuff, key=lambda c: (num(rech.get(c)), c))[:HIST_ALT_LIMIT] or []


HIST_ALT_RESERVED = None                              # 第一次需要額度時才規劃（此時本輪 ISIN 上市日已載入）
HIST_ALT_USED = {"reserved": set(), "other": 0}


def _hist_alt_slot(code):
    global HIST_ALT_RESERVED
    if HIST_ALT_RESERVED is None:
        HIST_ALT_RESERVED = set(_hist_alt_plan())
    if code in HIST_ALT_RESERVED:
        HIST_ALT_USED["reserved"].add(code)
        return True
    if HIST_ALT_USED["other"] < HIST_ALT_LIMIT - len(HIST_ALT_RESERVED):
        HIST_ALT_USED["other"] += 1
        return True
    return False


def verify_daily_history(hist, meta, ticker_code, want_range, today):
    """替代區間回應的嚴格核對。回傳 (一年視窗 DataFrame, None) 或 (None, 拒用原因)。"""
    if not isinstance(meta, dict):
        return None, "回應沒有 metadata"
    if meta.get("symbol") != ticker_code:
        return None, "代號不符（%r）" % (meta.get("symbol"),)
    if meta.get("dataGranularity") != "1d":
        return None, "粒度 %r 不是日線" % (meta.get("dataGranularity"),)
    # R2：yfinance 1.5.2 只把 period='max' 轉成 period1／period2 起訖請求（不送 range），Yahoo 正常回應 range 為空字串；
    # 只對 max 精確接受 ""，缺 range（None）、其他區間（2y／5y…）仍須完全相符
    if not (meta.get("range") == want_range or (want_range == "max" and meta.get("range") == "")):
        return None, "回應區間 %r 不是請求的 %s" % (meta.get("range"), want_range)
    if hist is None or hist.empty or "Close" not in hist.columns:
        return None, "沒有資料列"
    days = [ts.date() for ts in hist.index]
    if len(set(days)) != len(days):
        return None, "%d 筆只有 %d 個交易日（非日線）" % (len(days), len(set(days)))
    if any(b <= a for a, b in zip(days, days[1:])):
        return None, "交易日未遞增"
    if days[-1] > today:
        return None, "含未來交易日 %s" % days[-1]
    close = [float(x) for x in hist["Close"]]
    bad = [i for i, x in enumerate(close) if not (math.isfinite(x) and x > 0)]
    if bad and (bad != [len(close) - 1] or not math.isnan(close[-1])):      # 只容許最後一筆缺值（NaN）
        return None, "收盤價有缺值／非有限／非正數（%s）" % days[bad[0]]
    one_yr_ago = today - datetime.timedelta(days=365)
    keep = [d >= one_yr_ago for d in days]                     # 與 period=1y 相同的一年視窗
    win = hist[keep]
    ok = [d for d, x in zip(days, close) if d >= one_yr_ago and math.isfinite(x) and x > 0]
    if len(ok) < 5:
        return None, "一年視窗內不足 5 筆"
    # 覆蓋以截窗後的有效收盤判斷：舊年度資料被截掉後不能替一年視窗作證（避免舊 ETF 被原計算判成新上市）
    if ok[0] > one_yr_ago + datetime.timedelta(days=15):
        return None, "一年視窗有效日線只涵蓋 %s～%s（%d 個交易日），不足一年" % (ok[0], ok[-1], len(ok))
    gap = max(((b - a).days, a) for a, b in zip(ok, ok[1:])) if len(ok) > 1 else (0, None)
    if gap[0] > 15:
        return None, "一年視窗內 %s 起缺 %d 天日線，不足一年" % (gap[1], gap[0])
    if ok[-1] < today - datetime.timedelta(days=10):
        return None, "最後一筆 %s 過舊" % ok[-1]
    return win, None


def _twse_alt_history(code, name, today, previous):
    """Yahoo不足才核同代號官方歷史；不碰正常一年資料、不填假指標。"""
    global HIST_TWSE_USED, HIST_TWSE_TARGET
    if code in TWO_CODES:
        return None
    try:
        end = datetime.datetime.strptime(_TWSE_PRICE_DATE, "%Y%m%d").date()
        price = _TWSE_OFFICIAL_CLOSES.get(code)
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise ValueError("沒有本輪有效官方末價")
    except (ValueError, TypeError):
        HIST_CHECK[code] = {"status": "error", "detail": previous["detail"] + "；本輪官方末價不能確認，TWSE歷史未查完", "range": previous.get("range")}
        return None
    if HIST_TWSE_TARGET is None:
        eligible = [c for c in _hist_alt_plan() if c not in TWO_CODES
                    and isinstance(_TWSE_OFFICIAL_CLOSES.get(c), (int, float))
                    and not isinstance(_TWSE_OFFICIAL_CLOSES.get(c), bool)
                    and math.isfinite(_TWSE_OFFICIAL_CLOSES[c]) and _TWSE_OFFICIAL_CLOSES[c] > 0]
        HIST_TWSE_TARGET = eligible[0] if eligible else code
    if HIST_TWSE_USED or code != HIST_TWSE_TARGET:
        HIST_CHECK[code] = {"status": "queued", "detail": previous["detail"] + "；TWSE歷史額度已用，下輪優先查證，不算查完", "range": previous.get("range")}
        return None
    HIST_TWSE_USED = True
    try:
        import twse_history
        h = twse_history.fetch_history(code, name, today, end, price)
        proof = h.attrs["twse_history"]
        HIST_CHECK[code] = {"status": "recovered", "detail": "Yahoo一年／較長區間不足；TWSE官方一年日線%d筆、%d個現金分配事件及無分割證據已核對" % (len(h), len(proof["cash_events"])), "range": "TWSE一年", "official": proof}
        print("[HISTORY-TWSE] %s recovered %d rows (%s → %s)" % (code, len(h), proof["first"], proof["last"]))
        return h
    except Exception as ex:
        HIST_CHECK[code] = {"status": "error", "detail": previous["detail"] + "；TWSE官方歷史未能完成（%s：%s），下輪再查，不算查無" % (type(ex).__name__, str(ex)[:150]), "range": previous.get("range")}
        print("[HISTORY-TWSE] %s incomplete %s" % (code, type(ex).__name__))
        return None


def alt_history(tk, code, ticker_code, name=None):
    """period=1y 不足時的替代區間查證。合格回傳一年視窗日線，否則 None（狀態記在 HIST_CHECK）。"""
    today = _hist_today()

    def rec(status, detail, rng=None):
        HIST_CHECK[code] = {"status": status, "detail": detail, "range": rng}
        print("[HISTORY-ALT] %s %s %s%s" % (code, status, detail, " (%s)" % rng if rng else ""))
        if name and status in ("error", "no_range", "rejected"):
            return _twse_alt_history(code, name, today, dict(HIST_CHECK[code]))
        return None
    inel = _hist_ineligible(code, today)
    if inel:
        return rec(*inel)
    meta = _hist_meta(tk)
    valid = meta.get("validRanges") if isinstance(meta, dict) else None
    if not isinstance(valid, list):
        return rec("error", "一年請求沒有可判讀的 validRanges，無法確認支援區間（本輪不算查完）")
    rng = next((r for r in HIST_ALT_RANGES if r in valid), None)
    if rng is None:
        return rec("no_range", "來源支援區間 %s 沒有比一年長的區間" % ",".join(map(str, valid)))
    if not _hist_alt_slot(code):
        return rec("queued", "本輪替代查證額度已用完，排隊下輪", rng)
    try:
        h = tk.history(period=rng, interval="1d", auto_adjust=False)
    except Exception as e:
        return rec("error", "替代請求失敗：%s（本輪不算查完）" % type(e).__name__, rng)
    if h is None or h.empty:
        return rec("error", "替代請求沒有回資料（逾時或錯誤，本輪不算查完）", rng)
    win, why = verify_daily_history(h, _hist_meta(tk), ticker_code, rng, today)
    if win is None:
        return rec("rejected", why, rng)
    rec("recovered", "替代區間取得 %s 起一年日線 %d 筆" % (win.index[0].date(), len(win)), rng)
    return win

# ── 主流程 ──────────────────────────────────────────────────────────
try:
    ALL_ETFS  = build_pool()
except PoolIncomplete as _pi:
    # D-055：安全中止——不寫 _base／快取，既有正式資料原樣保留（workflow 該步 continue-on-error）
    print("::error::[POOL] 商品池不完整，本次不更新：%s" % _pi)
    sys.exit(1)
EMEGA_AUM = fetch_emega_aum()

results = []
for code, name in ALL_ETFS:
    curated = code in CURATED_CODES
    ticker_code = code + (".TWO" if code in TWO_CODES else SUFFIX)
    try:
        tk = yf.Ticker(ticker_code)
        hist = tk.history(period="1y", auto_adjust=False)
        if hist.empty or len(hist) < 5 or "Close" not in hist.columns or len(hist["Close"].dropna()) < 5:
            alt = alt_history(tk, code, ticker_code, name)  # Yahoo不足才按額度核官方一年日線及調整事件
            if alt is not None:
                hist = alt
        if hist.empty or len(hist) < 5:
            raise ValueError("insufficient data")

        # 開盤前 Action 跑時，yfinance 最後一筆可能是 Close=NaN 的不完整當日資料
        c = hist["Close"].dropna()
        v = hist["Volume"].dropna()
        if len(c) < 5:
            raise ValueError("insufficient clean data")
        price_date = c.index[-1].date().isoformat()     # yfinance 最後一筆的日期（第三方，非收盤證明）
        price_prev = round(float(c.iloc[-2]), 2)        # 同一序列的前一筆收盤（yfinance 價格算漲跌用）

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
        # 官方歷史已核過同一批分配事件，不再回頭要求壞掉的Yahoo事件來源。
        divs = hist.loc[hist["Dividends"] > 0, "Dividends"] if hist.attrs.get("twse_history") else tk.dividends

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

        yld_pending = _yld_pending_for(code)

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
            # 逐檔資料來源（mis_fetcher 判斷有效日期／收盤證據用）：
            # price_date／price_prev＝yfinance 最後一筆日期與前一筆收盤；official_close＝逐檔官方收盤證據
            # （上市取 TWSE MI_INDEX、上櫃取 TPEx，各自驗證報表日期；status traded／no_trade；表內沒有＝None）
            "price_date": price_date, "price_prev": safe(price_prev),
            "official_close": (_TPEX_OFFICIAL_ROWS if code in TWO_CODES else _TWSE_OFFICIAL_ROWS).get(code),
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
        elif str(e) in ("insufficient data", "insufficient clean data"):
            # D-044：歷史不足但已上市且有可信官方收盤 → 保留（指標不足）；條件不成立照原本略過
            fb, why = history_fallback(code, name, curated)
            if fb:
                results.append(fb)
                print(f"[INSUFFICIENT] {code} {name}  官方收盤 {fb['price']}（{fb['price_date']}），"
                      f"上市日 {fb['listing_date']}，歷史不足 → 保留、指標不足")
            else:
                print(f"[SKIP] {code} {name} 失敗，略過: {e}（歷史不足保留條件不成立：{why}）")
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
    m = _TWSE_MARKET_CLOSE or _fetch_twse_market()
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
# 非關鍵欄位（既有語意可為 null）的 NaN／Infinity 轉 null；必要欄位不合法 → 不寫檔、exit 1，原檔不動
nullify_nonfinite(results)
try:                                                  # R1：先移除舊查證紀錄，本輪寫不出時 daily 不會誤採上一份
    HIST_CHECK_OUT.unlink()
except FileNotFoundError:
    pass
except Exception as e:
    print(f"[HISTORY-ALT] 舊查證狀態無法移除：{e}", file=sys.stderr)
try:
    atomic_write_json(OUT_BASE, output, validate=validate_base_policy)   # 含商品收錄政策：K／ETN 不得寫入
except Exception as e:
    print(f"::error::_base.json 未更新（驗證或寫入失敗，原檔保留）：{e}", file=sys.stderr)
    sys.exit(1)

# 2026-10-27：替代歷史查證狀態（執行期檔，不發布）。R1：綁定本輪執行識別（_run_id）、寫出後 _base 的實際內容 SHA256
# 與查證時間；daily_check 只採用同一執行、同一份 _base 的紀錄。暫存檔＋os.replace 原子寫出。
try:
    import time as _time
    HIST_CHECK_OUT.parent.mkdir(parents=True, exist_ok=True)
    _tmp = HIST_CHECK_OUT.with_name(HIST_CHECK_OUT.name + ".tmp")
    _tmp.write_text(json.dumps({"run": _run_id(), "base_sha256": _sha256_file(OUT_BASE), "checked_at": _time.time(),
                                "base_updated": output["updated"], "limit": HIST_ALT_LIMIT, "checks": HIST_CHECK},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(_tmp, HIST_CHECK_OUT)
except Exception as e:
    print(f"[HISTORY-ALT] 查證狀態未能寫出（daily_check 視為未完成判讀）：{e}", file=sys.stderr)

# 同步更新 dividend_info.json 的 calendar（mis_fetcher.py 讀這個當估算來源）
# 原子寫入；失敗時 dividend_info.json 原檔保留，並以 exit 1 回報（_base.json 已是獨立的成功寫入）
# D-063：同一次原子寫入一併納入正式版官方頻率補查結果（只補原本未知的頻率，附官方證據）。
_div_failed = False
if (calendar or _OFFICIAL_FREQ_RECOVERIES) and OUT_DIV.exists():
    try:
        with open(OUT_DIV, encoding="utf-8") as f:
            div_info = json.load(f)
        for code, evidence in _OFFICIAL_FREQ_RECOVERIES.items():
            meta = div_info.setdefault("etfs", {}).get(code, {})
            if not isinstance(meta, dict) or meta.get("frequency") not in (None, "", "?", "不明"):
                continue
            meta.setdefault("name", next((e.get("name", code) for e in results if e["code"] == code), code))
            meta.setdefault("months", [])
            meta.setdefault("avg_dividend_per_share", None)
            meta.setdefault("_todo", True)
            meta["frequency"] = evidence["frequency"]
            meta["frequency_evidence"] = evidence
            div_info["etfs"][code] = meta
        if calendar:
            div_info["calendar"] = calendar
        atomic_write_json(OUT_DIV, div_info, validate=validate_dividend_info)
        print(f"✓ dividend_info.json calendar 更新：{len(calendar)} 筆")
    except Exception as e:
        print(f"::error::dividend_info.json 未更新（原檔保留）：{e}", file=sys.stderr)
        _div_failed = True

print(f"\n✓ data/_base.json 完成：精選 {curated_n} + 自動發現 {auto_n} = {len(results)} 支 ETF")
if _TWSE_PRICE_DATE:
    print(f"✓ TWSE 官方收盤核對（{_TWSE_PRICE_DATE}）：覆蓋 {_twse_override_count} 支價格")
else:
    print("⚠ 本次未能取得 TWSE 官方收盤核對來源，price 僅來自 yfinance")

if _div_failed:
    sys.exit(1)
