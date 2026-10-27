"""
scripts/mis_fetcher.py
每 10 分鐘由 GitHub Actions 執行。
讀 data/_base.json（每日基線）＋ data/dividend_info.json（配息靜態）
→ 視盤況決定是否疊上 MIS 即時資料
→ 輸出 data/market.json（前端讀這個）
"""

import json, math, os, sys, time, ssl, datetime
import urllib.request as _ur
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_check import no_distribution_note   # D-053：與 D-052 TG 告警同一套官方「本期不分配」判定
import official_frequency as _official_policy     # D-068：官方政策證據的單一驗證規則

sys.path.append(str(Path(__file__).resolve().parent))
from json_safe import atomic_write_json, validate_market, validate_market_policy, INSUFFICIENT_HISTORY   # noqa: E402

# Windows 本機主控台常是 cp950，print() 遇到 emoji/特殊符號會 UnicodeEncodeError 整支腳本崩潰
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── 路徑 ────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
BASE        = ROOT / "data" / "_base.json"
DIV         = ROOT / "data" / "dividend_info.json"
DIV_CAL     = ROOT / "data" / "dividend_calendar.json"    # TWSE 官方公告
MANUAL_CAL  = ROOT / "data" / "manual_calendar.json"      # 人工核實（不被 Action 覆蓋）
OUT         = ROOT / "data" / "market.json"

FREQ_MAP = {"月配": 12, "雙月配": 6, "季配": 4, "半年配": 2, "年配": 1, "不配息": 0}

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
    return 540 <= t <= 830          # 09:00 ~ 13:50（含收盤後緩衝）

# ── 休市日（TWSE 官方休市表）─────────────────────────────
# 表內除了休市日，也列「開始交易日」「最後交易日」這類有交易的日子，要依名稱排除。
HOLIDAY_URL      = "https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule"
_TRADING_DAY_KW  = ("開始交易", "最後交易")

def fetch_holiday_schedule():
    """回傳 {date: 名稱}（只含當年度表列日期）。
    抓不到、不是 list、或任何一列缺 Date／Name、日期不合法 → 整份不用，回 None（fail-safe：
    寧可當作「不知道」交給 MIS 日期檢查，也不能因欄位缺漏把交易日判成休市）。"""
    try:
        rows = _fetch_url(HOLIDAY_URL)
        if not isinstance(rows, list) or not rows:
            raise ValueError("not a non-empty list")
        out = {}
        for r in rows:
            roc  = str(r.get("Date") or "").strip()       # 民國年 YYYMMDD，例 1151009
            name = str(r.get("Name") or "").strip()
            if len(roc) != 7 or not roc.isdigit() or not name:
                raise ValueError(f"bad row {r!r}")
            out[datetime.date(int(roc[:3]) + 1911, int(roc[3:5]), int(roc[5:]))] = name
        return out
    except Exception as e:
        print(f"[HOLIDAY] 休市表不可用: {e}", file=sys.stderr)
        return None

def classify_day(day, schedule):
    """weekend／holiday／trading／unknown。
    unknown＝休市表抓不到或沒有今年的資料：不宣稱休市，交給 MIS 報價日期檢查把關。"""
    if day.weekday() >= 5:
        return "weekend"
    if not schedule or not any(d.year == day.year for d in schedule):
        return "unknown"
    name = schedule.get(day)
    if name is None or any(k in name for k in _TRADING_DAY_KW):
        return "trading"
    return "holiday"

def _ymd_iso(s):
    """'20261008' → '2026-10-08'；不合法回 ''。"""
    s = str(s or "")
    return f"{s[:4]}-{s[4:6]}-{s[6:]}" if len(s) == 8 and s.isdigit() else ""

# ── MIS 資料抓取 ──────────────────────────────────────────
def _fetch_url(url):
    req = _ur.Request(url, headers=HEADERS)
    with _ur.urlopen(req, timeout=12, context=SSL_CTX) as r:
        return json.loads(r.read().decode("utf-8"))

# ETF 報價分批：每批檔數與批次間等待秒數（工作單08／D-020）。預設 20 檔／3 秒＝原行為；
# 環境變數 MIS_BATCH（正整數）、MIS_PAUSE（有限非負秒數）可覆寫，無效值回到該欄預設並在 stderr 告警。
MIS_BATCH_DEFAULT, MIS_PAUSE_DEFAULT = 20, 3.0


def mis_batch_params():
    """回傳 (每批檔數, 批次間等待秒數)。每次呼叫重新讀環境變數。"""
    batch, pause = MIS_BATCH_DEFAULT, MIS_PAUSE_DEFAULT
    raw = os.environ.get("MIS_BATCH")
    if raw is not None:
        s = raw.strip()
        try:
            # 超長數字會超過 Python 整數字串轉換上限（ValueError）：視同無效，不放寬該安全限制
            v = int(s) if s.isdigit() and s.isascii() else 0
        except ValueError:
            v = 0
        if v > 0:
            batch = v
        else:
            print(f"::warning::[MIS] MIS_BATCH={raw[:40]!r}{'…' if len(raw) > 40 else ''} 無效（須為正整數），"
                  f"改用預設 {MIS_BATCH_DEFAULT}", file=sys.stderr)
    raw = os.environ.get("MIS_PAUSE")
    if raw is not None:
        try:
            v = float(raw.strip())
            if not math.isfinite(v) or v < 0:
                raise ValueError
            pause = v
        except ValueError:
            print(f"::warning::[MIS] MIS_PAUSE={raw!r} 無效（須為有限非負秒數），改用預設 {MIS_PAUSE_DEFAULT:g}", file=sys.stderr)
    return batch, pause


def _mis_positive_price(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (ValueError, TypeError):
        return None


def fetch_mis_etfs(codes, otc_codes=(), today=None):
    """
    codes: list of str（ETF 代碼）
    otc_codes: 其中屬於**上櫃**的代碼集合，MIS 前綴要用 otc_ 不是 tse_
               （用 tse_ 查上櫃會回一筆空殼 c=""，等於查不到）
    回傳 {code: {price, vol, change_pt, change_pct, mis_time}}
    每批 MIS_BATCH 支（預設 20）、批次間等 MIS_PAUSE 秒（預設 3；見 mis_batch_params）
    today: "YYYYMMDD"；給了就只收 MIS 報價日期 d 等於今天的（休市日、開盤前 MIS 回的是前一交易日報價）
    """
    otc = set(otc_codes)
    batch_size, pause = mis_batch_params()
    results = {}
    batches = [codes[i:i+batch_size] for i in range(0, len(codes), batch_size)]
    for idx, batch in enumerate(batches):
        if idx > 0:
            time.sleep(pause)
        ex_ch = "|".join(("otc_" if c in otc else "tse_") + c + ".tw" for c in batch)
        try:
            d = _fetch_url(f"{MIS_URL}?json=1&delay=0&ex_ch={ex_ch}")
            for item in d.get("msgArray", []):
                code = str(item.get("c", "")).strip()
                z    = _mis_positive_price(item.get("z"))
                y    = _mis_positive_price(item.get("y"))
                v    = item.get("v", "-")
                t    = item.get("t", "")
                if not code:
                    continue
                if today and item.get("d") != today:
                    continue
                # 當 z="-" 時，依序 fallback：買賣報價中點 → MIS 昨收(y)
                if z is None:
                    a_str = item.get("a", "")  # ask: "29.40_29.41_..."
                    b_str = item.get("b", "")  # bid: "29.39_29.38_..."
                    # Parse each side independently: '-' on ask must not discard
                    # an available bid (and vice versa).
                    best_ask = _mis_positive_price(str(a_str or "").split("_")[0])
                    best_bid = _mis_positive_price(str(b_str or "").split("_")[0])
                    if best_ask is not None and best_bid is not None:
                        z = round(best_ask / 2 + best_bid / 2, 4)
                    elif best_ask is not None or best_bid is not None:
                        # D-060: no valid trade and only one side quoted — a lone
                        # resting order is not a price. Skip this record so the
                        # ETF keeps its baseline (existing missing-MIS path).
                        continue
                    elif y is not None:
                        z = y  # Existing final fallback remains explicit MIS previous close.
                    else:
                        continue
                try:
                    price = float(z)
                    prev  = float(y) if y and y != "-" else price
                    vol   = float(str(v).replace(",", "")) if v and v != "-" else None
                    if not all(math.isfinite(x) for x in (price, prev) + (() if vol is None else (vol,))) or price <= 0:
                        continue                       # MIS 回 NaN／Infinity 等非有限值：當作沒有報價
                    # 成交量未取得（v="-"／缺）或報價時間在 09:00 前（開盤前試撮）／缺時間：不是當日已確認成交量，
                    # 記成未知（None），不寫成 0 冒充「今天真的沒成交」；價格判定不變
                    if vol is not None and (not t or t[:5] < "09:00"):
                        vol = None
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

def fetch_twii_prev_close():
    """yfinance 抓 ^TWII 前一交易日收盤，作為漲跌基準（MIS API 的 y 欄位對指數不準確）"""
    try:
        import yfinance as yf
        tw_today = tw_now().date()
        hist = yf.Ticker("^TWII").history(period="5d")
        if hist.empty:
            return None
        dates = [idx.date() if hasattr(idx, "date") else idx for idx in hist.index]
        past = [float(hist["Close"].iloc[i]) for i, d in enumerate(dates) if d < tw_today]
        return past[-1] if past else None
    except Exception as e:
        print(f"[yf] ^TWII prev_close 失敗: {e}", file=sys.stderr)
    return None

def fetch_mis_market(today=None):
    """抓加權指數（tse_t00.tw），昨收優先用 MIS y 欄位（fallback: yfinance）"""
    try:
        d    = _fetch_url(f"{MIS_URL}?json=1&delay=0&ex_ch=tse_t00.tw")
        item = d.get("msgArray", [{}])[0]
        if today and item.get("d") != today:
            return None
        z, y, t = item.get("z", "-"), item.get("y", "-"), item.get("t", "")
        if z and z != "-":
            cur  = float(z)
            if not math.isfinite(cur) or cur <= 0:
                return None
            prev = None
            if y and y != "-":
                try:
                    prev = float(y)
                    if not math.isfinite(prev):
                        prev = None
                except (ValueError, TypeError):
                    pass
            if not prev:
                prev = fetch_twii_prev_close()
            if not prev:
                prev = cur
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
    if is_bond_etf(code):
        return "bond"
    if price <= 0 or ma60 <= 0:
        return "dear"
    pos52 = (price - low52) / (high52 - low52) if high52 > low52 else 0.5
    maD60 = round((price - ma60) / ma60 * 100, 1) if ma60 > 0 else 0

    if ret5d >= 5 or rsi >= 75:
        return "hot"
    if pos52 > 0.78 or price > ma60 * 1.06:
        return "dear"

    if pos52 < 0.40 and maD60 < -2:
        return "cheap"

    is_high_div = any(k in name for k in _HIGH_DIV_KW) or yld > 5
    conds = [price <= ma60 * 1.03, ret5d < 5, vol_ratio <= 3.0, rsi < 75]
    if is_high_div:
        conds.append(yld > 5)
    if all(conds):
        return "fair"

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
    if info.get("frequency") not in _official_policy.UNKNOWN and _official_policy.known_policy(code, info) is None:
        frequency = "不明"                   # D-071：失效證據的頻率不參與殖利率推算（與未知政策同處理）
    multiplier = FREQ_MAP.get(frequency, 4)

    if multiplier == 0:
        return 0.0, "none", "無配息紀錄"

    # 優先 1：TWSE 官方公告
    # 官方金額 None／缺鍵＝本次未取得官方金額（例 fetch_dividend_calendar「所有來源查無金額」），不代表官方尚未公告；
    # 也不是 0：不做官方推算，往下走歷史平均／無資料；不拿 manual 預估代替。
    cal = div_cal_etfs.get(code)
    if cal and cal.get("amount") is not None:
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

    def _append(code, name, ex_date, amt, source, amount_source=None):
        days_left = (ex_date - today).days
        if days_left < 0:
            return
        # amt=None 代表查無（待公告），不使用歷史 fallback
        # amt=0 代表舊格式空值，才走 fallback
        if amt is None:
            pass
        elif not amt:
            amt = amt_fallback.get(code, 0)
        result.append({
            "code":          code,
            "name":          name,
            "iso_date":      ex_date.isoformat(),
            "day":           str(ex_date.day),
            "mon":           f"{ex_date.month}月",
            "amt":           amt,
            "soon":          days_left <= 14,
            "days_until":    days_left,
            "source":        source,
            "amount_source": amount_source or source,
        })
        covered.add(code)

    # 1. TWSE 官方公告
    for code, d in div_cal_etfs.items():
        try:
            ex_date = datetime.date.fromisoformat(d["ex_dividend_date"])
        except (ValueError, KeyError):
            continue
        _append(code, d["name"], ex_date, d.get("amount"), "official",
                d.get("amount_source"))

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

# ── 監測：_base.json 過期警報（獨立於 fetch.yml，確保 fetch 掛掉時也能通知）──
def check_base_staleness():
    import os
    TG_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    if not BASE.exists():
        return
    age_hours = (time.time() - BASE.stat().st_mtime) / 3600
    if age_hours > 25:
        msg = (f"🚨 _base.json 已 {age_hours:.0f} 小時未更新\n"
               f"fetch.yml 可能持續失敗，ETF 基線資料（均線/RSI/殖利率）已過期\n"
               f"請至 GitHub Actions 確認 Fetch ETF Data 最近執行狀況")
        try:
            data = json.dumps({"chat_id": TG_CHAT_ID, "text": msg}).encode()
            req  = _ur.Request(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                data=data, headers={"Content-Type": "application/json"},
            )
            _ur.urlopen(req, timeout=10)
            print(f"[STALE ALERT] _base.json 已 {age_hours:.0f} 小時未更新，TG 已通知")
        except Exception as e:
            print(f"[STALE ALERT ERROR] {e}", file=sys.stderr)


# ── 自驗：寫完 market.json 後立刻核對並自動修正 signal ──────────────────
def verify_output(data=None):
    """自驗 signal。data 給了（main 寫檔前）：就地修正、不寫檔，main 只做一次原子寫入；
    data=None（單獨呼叫）：讀 market.json、修正後原子重寫。"""
    import os
    TG_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    in_memory = data is not None

    if not in_memory:
        if not OUT.exists():
            return
        try:
            data = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            return

    fixed      = []   # 已自動修正，只記 log
    unfixable  = []   # 無法自動修正，需 TG 通知

    for e in data.get("etfs", []):
        code       = e.get("code", "")
        price      = e.get("price", 0)
        stored_sig = e.get("signal", "")

        # 價格為 0 → 無法自動修正，通知
        if price <= 0:
            unfixable.append(f"❌ {code} 價格={price}（異常，請確認資料來源）")
            continue

        # D-044：歷史不足的 ETF 沒有訊號可驗（signal 必須是 null，由 validate_market 把關）
        if e.get("indicator_status") == INSUFFICIENT_HISTORY:
            continue

        # signal 不符 → 直接用正確值覆蓋（資料本身足夠重算，不需人工）
        expected = calc_signal(
            price,
            e.get("ma20", 0), e.get("ma60", 0),
            e.get("low52", 0), e.get("high52", 0),
            e.get("ret5d", 0), e.get("vol_ratio", 1),
            e.get("rsi", 50), e.get("yld", 0), e.get("name", ""), code,
        )
        if expected != stored_sig:
            e["signal"] = expected
            if e.get("ma60", 0) > 0:
                e["maD"] = round((price - e["ma60"]) / e["ma60"] * 100, 1)
            fixed.append(
                f"{code}({e.get('name','')}) {stored_sig}→{expected} "
                f"(price={price}, ma60={e.get('ma60',0)})"
            )

    # 有修正 → 重寫 market.json（in-memory 模式由 main 寫）
    if fixed and in_memory:
        print(f"[VERIFY] 自動修正 {len(fixed)} 支 signal：" + "、".join(fixed))
    elif fixed:
        try:
            atomic_write_json(OUT, data, validate=validate_market_policy)
        except Exception as ex:
            print(f"::error::market.json 自驗修正未寫入（原檔保留）：{ex}", file=sys.stderr)
            sys.exit(1)
        print(f"[VERIFY] 自動修正 {len(fixed)} 支 signal：" + "、".join(fixed))
    else:
        print(f"[VERIFY] market.json 自驗通過（{len(data.get('etfs', []))} 支）")

    # 無法自動修正的才發 TG
    if not unfixable or not TG_TOKEN or not TG_CHAT_ID:
        return
    report = "🚨 market.json 有無法自動修正的異常：\n" + "\n".join(unfixable)
    print(f"[VERIFY ERROR]\n{report}", file=sys.stderr)
    try:
        body = json.dumps({"chat_id": TG_CHAT_ID, "text": report}).encode()
        req  = _ur.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=body, headers={"Content-Type": "application/json"},
        )
        _ur.urlopen(req, timeout=10)
        print(f"[VERIFY] TG 通知已發（{len(unfixable)} 項無法自動修正）")
    except Exception as ex:
        print(f"[VERIFY TG ERROR] {ex}", file=sys.stderr)


# ── 主流程 ────────────────────────────────────────────────
def main():
    now      = tw_now()
    today    = now.date()
    weekday  = is_weekday(now)
    schedule = fetch_holiday_schedule() if weekday else None
    day_kind = classify_day(today, schedule)
    holiday  = day_kind in ("weekend", "holiday")
    trading  = is_trading_hour(now) and not holiday
    print(f"[DAY] {today} {day_kind}")

    # 每次執行都檢查 _base.json 是否過期
    check_base_staleness()

    # 讀基線
    base = load_json(BASE)
    if base is None:
        print("[ERROR] data/_base.json 不存在，請先執行 fetch_etf.py", file=sys.stderr)
        sys.exit(1)
    # 商品收錄政策（PO 2026-10-10）：K 尾碼與 ETN 一律不收。舊 _base.json（政策前產生）可能還帶著它們，
    # 在這裡先拿掉；稽核清單讀不到 → 結束（fail-closed），不在無法確認時照舊輸出
    # E-1 Phase 2：每一檔還必須有合格 ETF 類型證據（ISIN ETF 區段＋CFI CE…）；未登錄 ETN、CFI 非 ETF、類型未知都不輸出。
    # 證據缺失／舊格式／損壞／過期 → 結束（不輸出 market.json，既有正式資料保留），不改用舊快取或舊 _base.json 放行。
    try:
        import product_policy
        listed = product_policy.listed_codes()
        evidence = product_policy.load_etf_evidence(as_of=tw_now().date(), listed=listed)
        base["etfs"], dropped = product_policy.split_etfs(base.get("etfs", []), listed, evidence)
    except Exception as e:
        print(f"::error::[POLICY] 無法確認商品類型，本次不更新：{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    # E-1 Phase 3：只有已核實的不收錄商品（K 尾碼、excluded_products.json）可以拿掉；
    # 其他代號缺證據、證據過期或日期錯亂，一檔都不放行也不默默拿掉 → 整次不更新，正式資料保留
    unverified = [(c, r) for c, r in dropped if r not in ("suffix-K", "excluded-list")]
    if unverified or not base["etfs"]:
        print(f"::error::[POLICY] {len(unverified)} 檔沒有有效的 ETF 類型證據，本次不更新：{unverified[:10]}",
              file=sys.stderr)
        sys.exit(1)
    if dropped:
        print(f"::warning::[POLICY] _base.json 排除 {len(dropped)} 檔（不收錄或無合格 ETF 類型證據）：{dropped}")

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
        otc_codes  = {e["code"] for e in base.get("etfs", []) if e.get("otc")}
        ymd        = today.strftime("%Y%m%d")
        mis_data   = fetch_mis_etfs(codes, otc_codes, today=ymd)
        mis_market = fetch_mis_market(today=ymd)
        mis_ok     = len(mis_data) > 0
        print(f"[MIS] 抓到 {len(mis_data)} 支即時資料，大盤={'OK' if mis_market else 'FAIL'}")

    # ── 逐檔資料來源契約（quote_src／quote_date／close_status）──
    # 優先序：① 今天的逐檔官方收盤（上市 TWSE MI_INDEX、上櫃 TPEx，fetch_etf 已驗證報表日期）
    #         ①' 今天官方確認無成交：價格沿用參考價（標明其日期／來源），成交量＝官方 0
    #         ② 本次 MIS 當日報價  ③ 上一份 market.json 較新的有效資料  ④ _base.json
    # 新舊比較只用逐檔日期：official_close.date／price_date（yfinance 最後一筆）／上一份的 quote_date，
    # 不用全市場 twse_price_check_date，也不用 updated（檔案產生時間）。
    # 選用官方證據時（任何日期）價格、漲跌、成交股數、日期一併取用，量比／熱度依同一成交量重算。
    # close_status：traded＝今天官方有成交收盤價；no_trade＝今天官方確認無成交；None＝無資料／驗證失敗／未確認
    OFFICIAL_SRCS = ("TWSE_MI_INDEX", "TPEX_OTC")
    today_iso = today.isoformat()
    prev      = load_json(OUT) if OUT.exists() else None
    prev_map  = {e["code"]: e for e in (prev or {}).get("etfs", [])}

    def _fin(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

    def _official(b):
        """逐檔官方證據（fetch_etf 已驗證報表日期與數值）；這裡再檢查一次型別與數值，格式不符回 None。
        traded：price 有限且 > 0、vol_shares 為非負整數或缺值、change_pt／prev_close 有限或缺值；
        no_trade：price 缺值且 vol_shares＝0。其他（含 NaN／Infinity、負數或小數股數）一律不當證據。"""
        off = b.get("official_close")
        if not isinstance(off, dict) or not off.get("date") or off.get("src") not in OFFICIAL_SRCS:
            return None
        vs = off.get("vol_shares")
        vs_ok = vs is None or (isinstance(vs, int) and not isinstance(vs, bool) and vs >= 0)
        status = off.get("status")
        if status == "traded" and _fin(off.get("price")) and off["price"] > 0 and vs_ok:
            out = dict(off)
            if not (_fin(out.get("change_pt")) and _fin(out.get("prev_close")) and out["prev_close"] > 0):
                out["change_pt"], out["prev_close"] = None, None
            return out
        if status == "no_trade" and off.get("price") is None and vs == 0 and not isinstance(vs, bool):
            return dict(off)
        return None

    def _base_evidence(b, off):
        """基線這一檔可用價格的 (有效日期, 來源)：有成交的官方證據 → 官方；否則 yfinance 日期；都沒有 → 不明。"""
        if off and off["status"] == "traded":
            return off["date"], off["src"]
        if b.get("price_date"):
            return b["price_date"], "yfinance"
        return None, None

    def _prev_src(p):
        if not p:
            return None
        if p.get("quote_src"):
            return p["quote_src"]
        return "MIS" if p.get("mis_time") else None          # 舊版檔：有 mis_time 才是 MIS 價格

    def _keep_prev(p, b_qd, b_src):
        """上一份資料是否比基線新。舊版檔沒有 quote_date：基線日期也不明時才沿用（不從 updated 推）。
        同一天：官方證據優先；都不是官方時沿用上一份 MIS（基線盤後快照可能是盤中價）。"""
        src = _prev_src(p)
        if src != "MIS" and src not in OFFICIAL_SRCS:
            return False
        qd = p.get("quote_date")
        if not qd:
            return not b_qd
        if not b_qd or qd > b_qd:
            return True
        if qd < b_qd:
            return False
        return src in OFFICIAL_SRCS or b_src not in OFFICIAL_SRCS

    def _vol_heat(e, b, vol_lots, chg_pct):
        """量比、熱度：與 MIS 路徑同一套公式（vol_lots 單位「張」）。"""
        if e.get("indicator_status") == INSUFFICIENT_HISTORY:
            e["vol_ratio"], e["heat"] = None, None     # D-044：沒有平均量就沒有量比／熱度，不用 1.0 冒充
            return
        avg = e.get("avg_vol", 0)
        vr  = round(vol_lots * 1000 / avg, 2) if avg > 0 else 1.0
        e["vol_ratio"] = vr
        e["heat"] = round(min(vr * 20, 40) + min(abs(chg_pct or 0) * 10, 30) + (b.get("score_cont", 0) or 0), 2)

    def _apply_official(e, b, off):
        """官方有成交證據：價格、漲跌、成交量、日期同一來源；無可信前收盤 → 漲跌缺值；無成交量 → 量相關欄位缺值。"""
        e["price"] = off["price"]
        if off.get("change_pt") is not None and (off.get("prev_close") or 0) > 0:
            e["change_pt"]  = off["change_pt"]
            e["change_pct"] = round(off["change_pt"] / off["prev_close"] * 100, 2)
        else:
            e.pop("change_pt", None); e.pop("change_pct", None)
        if off.get("vol_shares") is not None:
            e["cur_vol"] = round(off["vol_shares"] / 1000, 1)          # 股 → 張
            _vol_heat(e, b, e["cur_vol"], e.get("change_pct"))
        else:
            for k in ("cur_vol", "vol_ratio", "heat"):
                e.pop(k, None)
        e.pop("mis_time", None)
        e["quote_date"], e["quote_src"] = off["date"], off["src"]

    def _reference(e, b, off):
        """沒有當日官方／MIS 時的參考價：上一份較新的有效資料，或基線（官方證據或 yfinance）。"""
        b_qd, b_src = _base_evidence(b, off)
        p = prev_map.get(e["code"])
        if _keep_prev(p, b_qd, b_src):
            # ③ 沿用上一份較新的有效資料（cur_vol 已是「張」）
            for k in ("price", "change_pt", "change_pct", "cur_vol", "vol_ratio", "heat"):
                if k in p:
                    e[k] = p[k]
                else:
                    e.pop(k, None)
            if p.get("mis_time"):
                e["mis_time"] = p["mis_time"]
            else:
                e.pop("mis_time", None)
            e["quote_date"], e["quote_src"] = p.get("quote_date"), _prev_src(p)
        elif b_src in OFFICIAL_SRCS:
            _apply_official(e, b, off)                               # ④ 基線的官方證據（較早日期）
        else:
            # ④ 基線 yfinance：cur_vol 是「股」換成「張」，不換算會以 1000 倍虛胖霸佔成交量排行（2026-09-05）。
            cv = e.get("cur_vol") or 0
            if cv > 0:
                e["cur_vol"] = round(cv / 1000, 1)
            e.pop("mis_time", None)
            # 漲跌只用同一序列的前一筆（公式同 MIS）；沒有就缺值
            e.pop("change_pt", None); e.pop("change_pct", None)
            if b_src == "yfinance" and (b.get("price_prev") or 0) > 0 and (e.get("price") or 0) > 0:
                pv = b["price_prev"]
                e["change_pt"]  = round(e["price"] - pv, 2)
                e["change_pct"] = round((e["price"] - pv) / pv * 100, 2)
            e["quote_date"], e["quote_src"] = b_qd, b_src

    # ── 合併 ETF ──
    # 先決定最終價格與來源，再算所有依賴價格的衍生欄位
    # （signal、maD、新上市 ret1y、Plan C 殖利率），避免價格與衍生欄位來自不同來源
    etfs_out = []
    for code, b in base_etfs.items():
        e = dict(b)
        e.pop("official_close", None)
        e.pop("price_date", None)
        e.pop("price_prev", None)
        off = _official(b)
        off_today = off if off and off["date"] == today_iso else None
        e["close_status"] = None

        if off_today and off_today["status"] == "traded":
            _apply_official(e, b, off_today)                        # ① 今天官方有成交收盤
            e["close_status"] = "traded"
        elif off_today:
            # ①' 今天官方確認無成交：不編造今日成交價；價格是參考價（quote_date／quote_src 標明出處），
            # 今日漲跌不存在，成交量為官方 0 股
            _reference(e, b, None)
            e.pop("change_pt", None); e.pop("change_pct", None); e.pop("mis_time", None)
            e["cur_vol"] = 0.0
            _vol_heat(e, b, 0.0, 0)
            e["close_status"] = "no_trade"
        elif mis_ok and code in mis_data:
            # ② 本次 MIS 當日報價
            m = mis_data[code]
            e["price"]      = m["price"]
            e["change_pt"]  = m["change_pt"]
            e["change_pct"] = m["change_pct"]
            e["cur_vol"]    = m["vol"]
            e["mis_time"]   = m["mis_time"]
            e["quote_date"], e["quote_src"] = today_iso, "MIS"
            if m["vol"] is None:
                # 成交量未知（開盤前／未取得）：量相關欄位缺值，同官方無成交量的處理，不用 0 或平均量代替
                for k in ("cur_vol", "vol_ratio", "heat"):
                    e.pop(k, None)
            else:
                # MIS v 單位是「張」，yfinance avg_vol 單位是「股」，1張=1000股
                _vol_heat(e, b, m["vol"], m.get("change_pct", 0))
        else:
            _reference(e, b, off)
        e["close_confirmed"] = e["close_status"] is not None

        # 疊上配息靜態資料
        d = div_etfs.get(code, {})
        if d:
            if d.get("frequency") not in _official_policy.UNKNOWN and _official_policy.known_policy(code, d) is None:
                e["div_frequency"] = "不明"          # D-068／D-071：附了證據（frequency_evidence／policy_source）卻無效 → 不採用，不帶回 _base 舊值
            else:
                e["div_frequency"] = d.get("frequency", e.get("div_freq", "不明"))
            e["div_months"]        = d.get("months", [])
            e["div_avg_per_share"] = d.get("avg_dividend_per_share")
            e["div_category"]      = d.get("category", "")
            e["div_todo"]          = d.get("_todo", True)
            e.pop("div_freq", None)
        else:
            # 不在 dividend_info.json，沿用 _base.json 的 div_freq
            if "div_freq" in e:
                e["div_frequency"] = e.pop("div_freq")

        # 官方公告金額/日期 → 覆蓋 yfinance 的 est 和 days
        if code in div_cal_etfs:
            official = div_cal_etfs[code]
            if (official.get("amount") or 0) > 0:
                e["est"] = official["amount"]
            try:
                ex_date = datetime.date.fromisoformat(official["ex_dividend_date"])
                days_left = (ex_date - today).days
                if 0 <= days_left <= 730:
                    e["days"] = days_left
            except (ValueError, KeyError):
                pass

        # 重算訊號（不靠 NAV，與 fetch_etf.py 同一套邏輯）
        _ma60 = e.get("ma60") or 0
        _price = e.get("price") or 0
        _insufficient = e.get("indicator_status") == INSUFFICIENT_HISTORY
        # D-044：歷史不足 → 不判便宜／合理／偏貴，maD／報酬維持 null（不拿面額或少量資料推）
        e["signal"] = None if _insufficient else calc_signal(
            _price,
            e.get("ma20",      0),
            _ma60,
            e.get("low52",     0),
            e.get("high52",    0),
            e.get("ret5d",     0),
            e.get("vol_ratio", 1),
            e.get("rsi",      50),
            e.get("yld",       0),
            e.get("name",     ""),
            e.get("code",     ""),
        )
        # maD 依最終價格重算（原本只在缺欄位時補寫，MIS 價格下會留著基線價格算的值）
        if _ma60 > 0 and not _insufficient:
            e["maD"] = round((_price - _ma60) / _ma60 * 100, 1)
        e.pop("premium", None)   # 移除 NAV 相關欄位

        # 新上市 ETF：用最終價格和 NT$10 面額重算 ret1y，確保與顯示價格一致
        if e.get("new_listing") and _price > 0 and not _insufficient:
            e["ret1y"] = round((_price - 10.0) / 10.0 * 100, 1)

        # 殖利率：_base.json 有合理值（fetch_etf.py 用 TWSE 多筆平均算的）→ 直接沿用
        # 不靠 mis_fetcher 的 "單筆×頻率" 反算，那樣對變動配息 ETF 會嚴重失真
        base_yld = b.get("yld") or 0
        if 0 < base_yld <= 20:
            # dividend_info.json 的 _todo:False 代表已人工核實，升格為 verified
            div_confirmed = not div_etfs.get(code, {}).get("_todo", True)
            is_verified   = b.get("yld_verified", False) or div_confirmed
            e["yld"]          = base_yld
            e["yld_verified"] = is_verified
            e["yld_source"]   = "verified" if is_verified else "base"
            e["yld_label"]    = ("雙源核對（FinMind × TWSE ETFortune）"
                                 if b.get("yld_verified") else
                                 "dividend_info 人工核實" if div_confirmed else
                                 "fetch_etf 計算")
        else:
            # Fallback：_base.json 沒有 yld 才用 Plan C（官方公告 → 歷史平均）
            yld, yld_src, yld_lbl = calc_yield_with_source(
                code, e.get("price", 0), div_etfs, div_cal_etfs
            )
            if 0 < yld <= 20:
                e["yld"] = yld
            elif yld > 20:
                yld_src = "error"
                yld_lbl = "資料異常（殖利率>20%）"
            e["yld_verified"] = False
            e["yld_source"]   = yld_src
            e["yld_label"]    = yld_lbl

        # D-053：官方確認「本期不分配」的可選證據欄位（給排行／個股頁顯示「本期無」）。
        # 只在 D-052 判定有效（來源／日期／有效期／後續配息）且沒有正殖利率時附上；不改任何數值欄位。
        # 判定失敗或資料壞掉 → 不附欄位（前端回「待確認」），不中止產出。
        e.pop("distribution_status", None)
        try:
            _dn, _ = no_distribution_note(code, div_etfs.get(code), div_cal_etfs.get(code), today)
        except Exception as _ex:
            _dn = None
            print(f"[DIST] {code} 本期不分配判定失敗，不附狀態：{type(_ex).__name__}")
        if _dn and not ((e.get("yld") or 0) > 0):
            _st = div_etfs[code]["distribution_status"]
            e["distribution_status"] = {
                "status":         _st["status"],
                "valuation_date": _st["valuation_date"],
                "announced_date": _st["announced_date"],
                "valid_until":    _st["valid_until"],
                "source_name":    _st["source"]["name"],
                "source_url":     _st["source"]["url"],
            }

        etfs_out.append(e)

    # ── 大盤（獨立判斷：個股有當日報價不代表大盤也是）──
    if mis_ok and mis_market:
        market_out = dict(base.get("market", {}))
        market_out.update(mis_market)
        market_out.update(quote_date=today.isoformat(), is_live=True)
    else:
        # 基線大盤（fetch_etf 的 yfinance ^TWII）沒有日期欄位 → 日期不明；上一份是 MIS 就沿用
        pm = (prev or {}).get("market") or {}
        if _keep_prev(pm, None, None):
            market_out = dict(pm)
            market_out["quote_date"] = pm.get("quote_date")
        else:
            market_out = dict(base.get("market", {}))
            market_out.pop("mis_time", None)
            market_out["quote_date"] = None
        market_out["is_live"] = False
    market_out["close_confirmed"] = False      # 目前沒有大盤的官方收盤來源，不宣稱大盤已收盤

    # ── 狀態 ──
    # holiday：已確認休市（週末或官方休市表）
    # closed ：ETF 池每一檔都有今天的官方收盤狀態（有成交 traded 或官方確認無成交 no_trade）；缺一檔就不是
    # live   ：盤中（09:00～13:30）且本次取得當日 MIS 報價
    # stale  ：其他（開盤前、開盤初期、盤中 MIS 失敗、只有部分 ETF 確認收盤、行情日期不明）
    #          部分確認時以 close_confirmed {etfs, total} 揭露數量，不把整頁當成已收盤
    def _stamp(x):
        if not x.get("quote_date"):
            return None
        return x["quote_date"] + (" " + x["mis_time"] if x.get("mis_time") else "")
    stamps     = [st for st in (_stamp(e) for e in etfs_out) if st]
    quote_time = max(stamps) if stamps else None          # 最新有效行情時間（顯示用）
    # 分母＝本次正式 ETF 池全部（_base.json 的 ETF），不因缺價縮小
    n_traded  = sum(1 for e in etfs_out if e["close_status"] == "traded")
    n_notrade = sum(1 for e in etfs_out if e["close_status"] == "no_trade")
    confirmed = n_traded + n_notrade
    if holiday:
        state = "holiday"
    elif etfs_out and confirmed == len(etfs_out):
        state = "closed"
    elif mis_ok and now.hour * 60 + now.minute < 810:
        state = "live"
    else:
        state = "stale"
    is_closed = state != "live"

    output = {
        "updated":           now.strftime("%Y-%m-%d %H:%M"),   # 檔案產生時間
        "quote_date":        quote_time[:10] if quote_time else None,   # 有效行情日期（不明＝None）
        "quote_time":        quote_time,                       # 有效行情時間 "YYYY-MM-DD[ HH:MM]"
        "market_state":      state,
        # 逐檔官方收盤確認數：etfs＝traded＋no_trade，total＝ETF 池全部
        "close_confirmed":   {"etfs": confirmed, "traded": n_traded, "no_trade": n_notrade, "total": len(etfs_out)},
        "is_closed":         is_closed,
        "is_holiday":        holiday,
        "last_trading_time": "13:30" if state == "closed" else None,
        "market":            market_out,
        "etfs":              etfs_out,
        "calendar":          calendar,
        "twse_price_check_date": base.get("twse_price_check_date"),
    }

    # 休市日內容不會變：只差 updated 就不重寫，免得每 10 分鐘推一個重複 commit
    # （第一次執行仍會寫入，把先前誤標的盤中狀態改正）
    # 寫檔前先自驗（就地修正 signal）：整個 main 只有這一次原子寫入，沒有「寫完又重寫」的中間狀態
    verify_output(output)

    def _body(d):
        return {k: v for k, v in d.items() if k != "updated"}
    if holiday and prev and _body(prev) == _body(output):
        print("[OK] 休市日資料未變，market.json 不重寫")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # 先驗證、嚴格序列化，再原子替換；任何一步失敗原檔不變、exit 1（wrapper／Actions 不會發布）
    try:
        atomic_write_json(OUT, output, validate=validate_market_policy)   # 含商品收錄政策
    except Exception as ex:
        print(f"::error::market.json 未更新（驗證或寫入失敗，原檔保留）：{ex}", file=sys.stderr)
        sys.exit(1)

    status = {"live": "盤中 MIS", "closed": "收盤", "holiday": "休市", "stale": "資料未確認"}[state]
    print(f"[OK] data/market.json 完成（{status}，ETF {len(etfs_out)} 支）")


if __name__ == "__main__":
    main()
