"""scripts/json_safe.py
資料檔的安全寫入與資料契約驗證（fetch_etf.py、mis_fetcher.py、daily_check.py、validate_data.py、
publish_gate.py 共用）。

寫入（atomic_write_json）：先驗證 → 完整嚴格序列化（不允許 NaN／Infinity）→ 寫同目錄暫存檔、
flush、fsync → os.replace。保證範圍是「單一檔案」：任一步失敗都丟例外、清掉暫存檔，該檔位元組不變
（不會先清空或截斷）。多個檔案之間沒有交易一致性，由呼叫端與 publish_gate.py 處理。

契約（validate_*）：必要欄位缺值或型別不符就 DataInvalid；可選欄位可以缺省或 null，
但存在且非 null 時必須符合型別（數值須有限）。不把錯誤字串轉成數值、不把未知值補 0。
"""
import json, math, os, re, tempfile
from pathlib import Path


class DataInvalid(ValueError):
    """資料不符合契約。"""


def strict_dumps(obj):
    """標準 JSON（allow_nan=False）：遇到 NaN／Infinity 直接 ValueError。"""
    return json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)


def strict_loads(text):
    """解析 JSON；出現 NaN／Infinity／-Infinity 這類非標準常數就 DataInvalid。"""
    def _reject(c):
        raise DataInvalid(f"非標準 JSON 數值 {c}")
    return json.loads(text, parse_constant=_reject)


def load_strict(path):
    with open(path, encoding="utf-8") as f:
        return strict_loads(f.read())


def atomic_write_json(path, obj, validate=None):
    """驗證 → 序列化 → 暫存檔 → 原子替換。失敗時該檔不變、暫存檔清除，例外往上丟。"""
    path = Path(path)
    if validate:
        validate(obj)
    text = strict_dumps(obj)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
    f = None
    try:
        f = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
    except BaseException:
        os.close(fd)                     # fdopen 失敗：描述符還沒交給檔案物件，自己關
        _unlink(tmp)
        raise
    try:
        with f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        _unlink(tmp)
        raise


def _unlink(p):
    try:
        os.unlink(p)
    except OSError:
        pass


# ── 型別小工具 ───────────────────────────────────────────
_DATE_RE  = re.compile(r"\d{4}-\d{2}-\d{2}")
_HM_RE    = re.compile(r"\d{2}:\d{2}")
_STAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?")


def _fin(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _is_date(s):
    if not isinstance(s, str) or not _DATE_RE.fullmatch(s):
        return False
    try:
        import datetime
        datetime.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def _req_num(where, d, k, min_=None):
    v = d.get(k) if isinstance(d, dict) else None
    if not _fin(v) or (min_ is not None and v < min_):
        raise DataInvalid(f"{where} 必要欄位 {k} 無效：{v!r}")


def _opt_num(where, d, k, min_=None):
    v = d.get(k)
    if v is None:
        return
    if not _fin(v) or (min_ is not None and v < min_):
        raise DataInvalid(f"{where} 欄位 {k} 無效：{v!r}")


def _opt_str(where, d, k, pattern=None, choices=None, date=False):
    v = d.get(k)
    if v is None:
        return
    ok = isinstance(v, str) and (pattern is None or pattern.fullmatch(v)) and \
        (choices is None or v in choices) and (not date or _is_date(v))
    if not ok:
        raise DataInvalid(f"{where} 欄位 {k} 無效：{v!r}")


def _opt_bool(where, d, k):
    v = d.get(k)
    if v is not None and not isinstance(v, bool):
        raise DataInvalid(f"{where} 欄位 {k} 不是布林：{v!r}")


def _opt_num_list(where, d, k):
    v = d.get(k)
    if v is None:
        return
    if not isinstance(v, list) or not all(x is None or _fin(x) for x in v):
        raise DataInvalid(f"{where} 欄位 {k} 無效：{v!r}")


def nullify_nonfinite(etfs, keys=("ret1y", "ret_months")):
    """產生階段用：既有語意允許 null 的非關鍵欄位，NaN／Infinity → None，list 逐項處理。不補 0。"""
    for e in etfs:
        for k in keys:
            v = e.get(k)
            if isinstance(v, list):
                e[k] = [x if not isinstance(x, float) or math.isfinite(x) else None for x in v]
            elif isinstance(v, float) and not math.isfinite(v):
                e[k] = None


# ── ETF 欄位契約（前端 js/*.js 與 mis_fetcher 會直接拿來算術或 toFixed 的欄位）──
# 可選數值：缺省或 null 可（前端以 == null／|| 0 處理），存在就必須有限
_ETF_NUM_OPT = ("change_pt", "change_pct", "cur_vol", "vol_ratio", "heat", "ret1y", "ret5d", "ret1m",
                "yld", "ma60", "ma20", "maD", "low52", "high52", "est", "days", "aum", "avg_vol", "rsi",
                "score_cont", "div_avg_per_share", "price_prev")
_ETF_BOOL_OPT = ("curated", "otc", "new_listing", "yld_verified", "yld_pending", "close_confirmed")
_QUOTE_SRCS   = ("MIS", "TWSE_MI_INDEX", "TPEX_OTC", "yfinance")
_OFFICIAL_SRCS = ("TWSE_MI_INDEX", "TPEX_OTC")


def _check_etf_common(e):
    code = e.get("code") if isinstance(e, dict) else None
    if not isinstance(code, str) or not code:
        raise DataInvalid(f"ETF 代號無效：{code!r}")
    if not isinstance(e.get("name"), str):
        raise DataInvalid(f"{code} name 無效")
    _req_num(code, e, "price", 0)
    for k in _ETF_NUM_OPT:
        _opt_num(code, e, k)
    for k in _ETF_BOOL_OPT:
        _opt_bool(code, e, k)
    _opt_num_list(code, e, "ret_months")
    _opt_str(code, e, "signal")
    _opt_str(code, e, "div_next", date=True)
    return code


def _check_official(code, off):
    if off is None:
        return
    if not isinstance(off, dict) or off.get("src") not in _OFFICIAL_SRCS or not _is_date(off.get("date")):
        raise DataInvalid(f"{code} official_close 格式不符（src／date）：{off!r}")
    st, vs = off.get("status"), off.get("vol_shares")
    vs_ok = vs is None or (isinstance(vs, int) and not isinstance(vs, bool) and vs >= 0)
    if st == "traded":
        if not (_fin(off.get("price")) and off["price"] > 0) or not vs_ok:
            raise DataInvalid(f"{code} official_close traded 價格／股數無效")
        _opt_num(code + ".official_close", off, "change_pt")
        _opt_num(code + ".official_close", off, "prev_close", 0)
    elif st == "no_trade":
        if off.get("price") is not None or vs != 0 or isinstance(vs, bool):
            raise DataInvalid(f"{code} official_close no_trade 與價格／股數矛盾")
    else:
        raise DataInvalid(f"{code} official_close.status 無效")


def _check_index_close(where, m):
    """大盤官方收盤證據只認同一列、同一日期與官方漲跌，不能掛在MIS或舊價上。"""
    from decimal import Decimal, ROUND_HALF_UP
    import datetime
    c = m.get("index_close")
    keys = {"source", "date", "price", "prev_close", "change_pt", "change_pct"}
    if not isinstance(c, dict) or set(c) != keys or c.get("source") != "TWSE_MI_INDEX":
        raise DataInvalid(f"{where} 大盤收盤來源／欄位無效")
    if not _is_date(c.get("date")) or c["date"] > datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat():
        raise DataInvalid(f"{where} 大盤收盤日期無效")
    for key in ("price", "prev_close", "change_pt", "change_pct"):
        _req_num(where + ".index_close", c, key)
    if c["price"] <= 0 or c["prev_close"] <= 0:
        raise DataInvalid(f"{where} 大盤收盤／昨收必須正值")
    q = Decimal("0.01")
    price, prev, change, pct = (Decimal(str(c[k])) for k in ("price", "prev_close", "change_pt", "change_pct"))
    try:
        coherent = price - prev == change and (change / prev * 100).quantize(q, rounding=ROUND_HALF_UP) == pct
    except ArithmeticError:
        coherent = False
    if not coherent:
        raise DataInvalid(f"{where} 大盤官方數值關係不一致")
    if m.get("quote_date") != c["date"] or m.get("quote_src") != c["source"] or m.get("is_live") is not False or m.get("close_confirmed") is not True:
        raise DataInvalid(f"{where} 大盤收盤證據與行情狀態不一致")
    if any(not _fin(m.get(k)) or m[k] != c[k] for k in ("price", "change_pt", "change_pct")):
        raise DataInvalid(f"{where} 大盤收盤證據與顯示數值不同")


def confirmed_market_close(m):
    if not isinstance(m, dict) or m.get("index_close") is None:
        return False
    try:
        _check_index_close("market", m)
        return True
    except (DataInvalid, ArithmeticError, TypeError, ValueError):
        return False


def _check_market_block(where, m):
    if not isinstance(m, dict):
        raise DataInvalid(f"{where} market 不是物件")
    for k in ("price", "change_pt", "change_pct"):       # render.js renderMood 直接 toFixed
        _req_num(where + ".market", m, k)
    if m.get("index_close") is not None:
        _check_index_close(where + ".market", m)
    elif m.get("close_confirmed") is True:
        raise DataInvalid(f"{where} 大盤缺官方收盤證據卻標為已確認")


def _check_calendar(where, cal):
    if cal is None:
        return
    if not isinstance(cal, list):
        raise DataInvalid(f"{where} calendar 不是陣列")
    for c in cal:
        # 配息日曆列（render.js 配息日曆直接顯示 code、name）：code／name 必要；
        # iso_date 舊資料有缺省（只有 mon／day），存在就須是合法日期
        if not isinstance(c, dict):
            raise DataInvalid(f"{where} calendar 項目不是物件")
        w = where + ".calendar"
        if not (isinstance(c.get("code"), str) and c["code"] and isinstance(c.get("name"), str)):
            raise DataInvalid(f"{w} 缺 code／name：{c!r}")
        _opt_str(w, c, "iso_date", date=True)
        _opt_num(w, c, "amt")
        _opt_num(w, c, "days_until")
        _opt_bool(w, c, "soon")
        for k in ("mon", "day", "source"):
            _opt_str(w, c, k)


_BASE_NUM_REQUIRED = ("ma60", "ma20", "low52", "high52", "avg_vol", "cur_vol")


def _check_no_excluded(where, obj, ctx=None):
    """商品收錄政策（PO 2026-10-10）：核心池不得含 K 尾碼或稽核清單（excluded_products.json）商品。
    清單讀不到／格式錯 → PolicyError（fail-closed：無法確認就不讓資料通過）。
    只用在「這次要寫出／發布的新資料」（*_policy 版、publish_gate、market_guard／bootstrap 的本機候選）；
    validate_base／validate_market 本身仍接受政策前的歷史版本（PG-5 不誤拒舊資料），讀遠端舊檔也不受影響。
    E-1 Phase 2：另外要求每一檔都有合格 ETF 類型證據（ISIN ETF 區段＋CFI CE…，見 product_policy.load_etf_evidence）；
    證據缺失／舊格式／損壞／日期晚於本份資料 → DataInvalid（不發布、既有正式資料保留）。
    ctx（D-014）：{"evidence": 證據文字, "excluded": 排除清單文字}——Publish Gate 傳入與被驗資料「同一版本」的內容
    （工作目錄／index／每個 outgoing commit／tip 各自的 blob），不讀工作目錄檔；版本中缺檔 → 無法確認 → DataInvalid。
    ctx 為 None：讀工作目錄檔（寫出端 fetch_etf／mis_fetcher 的既有行為）。"""
    import datetime
    import product_policy
    try:
        as_of = datetime.date.fromisoformat(str(obj.get("updated") or "")[:10])
    except ValueError:
        raise DataInvalid(f"{where} updated 無效，無法核對 ETF 類型證據日期：{obj.get('updated')!r}")
    try:
        if ctx is None:
            listed = product_policy.listed_codes()
            evidence = product_policy.load_etf_evidence(as_of=as_of, listed=listed)
        else:
            if ctx.get("excluded") is None or ctx.get("evidence") is None:
                raise product_policy.PolicyError("同一版本缺 excluded_products.json 或 etf_pool_cache.json")
            listed = product_policy.listed_codes(text=ctx["excluded"])
            evidence = product_policy.load_etf_evidence(as_of=as_of, listed=listed, text=ctx["evidence"])
    except product_policy.PolicyError as e:
        raise DataInvalid(f"{where} 無法確認商品類型：{e}")
    bad = [(e.get("code"), r) for e in obj["etfs"] for r in [product_policy.type_reason(e.get("code"), listed, evidence)] if r]
    if bad:
        raise DataInvalid(f"{where} 含不收錄或無合格 ETF 類型證據的商品：{bad[:6]}")


# D-044：已上市但歷史不足的 ETF（fetch_etf.history_fallback）。只有這個明確狀態、且官方收盤證據完整時，
# 歷史指標才允許是 null——而且必須是 null（不可填 0 或部分歷史冒完整期間）；其他 ETF 照舊要求有限數值。
INSUFFICIENT_HISTORY = "insufficient_history"
_INSUFFICIENT_NULL = ("ma60", "ma20", "low52", "high52", "avg_vol", "rsi", "maD", "vol_ratio", "heat",
                      "ret5d", "ret1m", "ret1y", "score_cont", "signal")


def _check_insufficient_nulls(code, e):
    """R1：每個已定不足欄位都必須「存在且為 null」（缺鍵不算 null）；ret_months 必須恰好是 6 個 null 的 list。"""
    missing = [k for k in _INSUFFICIENT_NULL if k not in e]
    bad = [k for k in _INSUFFICIENT_NULL if k in e and e[k] is not None]
    rm = e.get("ret_months", "<缺>")
    if missing or bad or not (isinstance(rm, list) and len(rm) == 6 and all(x is None for x in rm)):
        raise DataInvalid(f"{code} 歷史不足但指標／訊號不是如實 null：缺鍵 {missing}、非 null {bad}、ret_months {rm!r}")


def _check_insufficient_history(code, e):
    if e.get("indicator_status") != INSUFFICIENT_HISTORY:
        raise DataInvalid(f"{code} indicator_status 無效：{e.get('indicator_status')!r}")
    if not _is_date(e.get("listing_date")):
        raise DataInvalid(f"{code} 歷史不足但 listing_date 無效：{e.get('listing_date')!r}")
    off = e.get("official_close")
    if not isinstance(off, dict) or off.get("status") != "traded":
        raise DataInvalid(f"{code} 歷史不足但沒有有成交的官方收盤證據")
    if e.get("price_date") != off.get("date") or e.get("price") != off.get("price"):
        raise DataInvalid(f"{code} 歷史不足：price／price_date 必須等於官方收盤證據")
    if e["listing_date"] > off["date"]:
        raise DataInvalid(f"{code} 上市日 {e['listing_date']} 晚於官方收盤日 {off['date']}")
    _req_num(code, e, "cur_vol", 0)
    _check_insufficient_nulls(code, e)


def validate_base(obj):
    """_base.json：etfs 非空；每檔必要數值有限；新欄位（price_date／price_prev／official_close）可缺省，
    存在就須合法；market 三個數值有限。"""
    if not isinstance(obj, dict):
        raise DataInvalid("_base.json 不是物件")
    etfs = obj.get("etfs")
    if not isinstance(etfs, list) or not etfs:
        raise DataInvalid("_base.json etfs 為空")
    for e in etfs:
        code = _check_etf_common(e)
        if e.get("indicator_status") is None:
            for k in _BASE_NUM_REQUIRED:
                _req_num(code, e, k, 0)
        _opt_str(code, e, "price_date", date=True)
        _check_official(code, e.get("official_close"))
        if e.get("indicator_status") is not None:
            _check_insufficient_history(code, e)
    _check_market_block("_base.json", obj.get("market"))
    _check_calendar("_base.json", obj.get("calendar"))
    v = obj.get("twse_price_check_date")
    if v is not None and not (isinstance(v, str) and re.fullmatch(r"\d{8}", v)):
        raise DataInvalid(f"twse_price_check_date 無效：{v!r}")


def validate_base_policy(obj, ctx=None):
    """寫出／發布用：validate_base＋商品收錄政策。"""
    validate_base(obj)
    _check_no_excluded("_base.json", obj, ctx)


_STATES = ("live", "closed", "stale", "holiday")


def validate_market(obj):
    """market.json：etfs 非空；每檔 price 有限 ≥ 0、可選數值有限或 null；新 metadata（quote_date／
    quote_time／quote_src／close_status／market_state／close_confirmed）可缺省（舊格式），存在就須合法；
    market 三個數值有限。"""
    if not isinstance(obj, dict):
        raise DataInvalid("market.json 不是物件")
    etfs = obj.get("etfs")
    if not isinstance(etfs, list) or not etfs:
        raise DataInvalid("market.json etfs 為空")
    for e in etfs:
        code = _check_etf_common(e)
        _opt_str(code, e, "quote_date", date=True)
        _opt_str(code, e, "mis_time", pattern=_HM_RE)
        _opt_str(code, e, "quote_src", choices=_QUOTE_SRCS)
        _opt_str(code, e, "close_status", choices=("traded", "no_trade"))
        if e.get("indicator_status") is not None:
            # D-044：歷史不足的 ETF 不得帶買賣訊號或歷史指標（不足期間的數值一律 null）
            if e["indicator_status"] != INSUFFICIENT_HISTORY or not _is_date(e.get("listing_date")):
                raise DataInvalid(f"{code} indicator_status／listing_date 無效")
            _check_insufficient_nulls(code, e)
    if not isinstance(obj.get("updated"), str):
        raise DataInvalid("updated 無效")
    _opt_str("market.json", obj, "quote_date", date=True)
    _opt_str("market.json", obj, "quote_time", pattern=_STAMP_RE)
    if obj.get("quote_time") and not _is_date(obj["quote_time"][:10]):
        raise DataInvalid("quote_time 日期無效")
    _opt_str("market.json", obj, "market_state", choices=_STATES)
    _opt_str("market.json", obj, "last_trading_time", pattern=_HM_RE)
    for k in ("is_closed", "is_holiday"):
        _opt_bool("market.json", obj, k)
    cc = obj.get("close_confirmed")
    if cc is not None:
        if not isinstance(cc, dict) or cc.get("total") != len(etfs) or not all(
                isinstance(cc.get(k), int) and not isinstance(cc.get(k), bool) and cc[k] >= 0
                for k in ("etfs", "traded", "no_trade", "total")) or cc["etfs"] != cc["traded"] + cc["no_trade"]:
            raise DataInvalid(f"close_confirmed 無效：{cc!r}")
    m = obj.get("market")
    _check_market_block("market.json", m)
    _opt_str("market.json.market", m, "quote_date", date=True)
    _opt_str("market.json.market", m, "mis_time", pattern=_HM_RE)
    _opt_bool("market.json.market", m, "is_live")
    _opt_bool("market.json.market", m, "close_confirmed")
    _check_calendar("market.json", obj.get("calendar"))


def validate_market_policy(obj, ctx=None):
    """寫出／發布用：validate_market＋商品收錄政策。"""
    validate_market(obj)
    _check_no_excluded("market.json", obj, ctx)


POLICY_VALIDATORS = {"_base.json": validate_base_policy, "market.json": validate_market_policy}


# ── fetch.yml 其他提交檔的結構契約（下游 Python／前端讀取所需的最小形狀）──
def _dict_of_dicts(where, d):
    if not isinstance(d, dict) or not all(isinstance(k, str) and isinstance(v, dict) for k, v in d.items()):
        raise DataInvalid(f"{where} 不是 {{代號: 物件}}")


def validate_dividend_info(obj):
    if not isinstance(obj, dict):
        raise DataInvalid("dividend_info.json 不是物件")
    _dict_of_dicts("dividend_info.etfs", obj.get("etfs"))
    for code, d in obj["etfs"].items():
        _opt_num("dividend_info." + code, d, "avg_dividend_per_share")
        _opt_str("dividend_info." + code, d, "frequency")
        # D-068：官方政策證據／待公告解除紀錄存在就必須完整有效（同一套規則：official_frequency）
        if "frequency_evidence" in d or "pending_resolution" in d:
            import official_frequency
            if "frequency_evidence" in d:
                why = official_frequency.policy_evidence_problem(code, d)
                if why:
                    raise DataInvalid(f"dividend_info.{code}.frequency_evidence 無效：{why}")
            if "pending_resolution" in d:
                why = official_frequency.pending_resolution_problem(code, d)
                if why:
                    raise DataInvalid(f"dividend_info.{code}.pending_resolution 無效：{why}")
        # D-071（安全版整合）：SITCA 等新來源採用紀錄存在就必須有效；不靠「舊驗證器忽略未知欄位」過關
        if "policy_source" in d:
            import official_frequency
            why = official_frequency.policy_source_problem(code, d)
            if why:
                raise DataInvalid(f"dividend_info.{code}.policy_source 無效：{why}")
    _check_calendar("dividend_info.json", obj.get("calendar"))


def validate_dividend_calendar(obj):
    """dividend_calendar.json → etfs → {代號: {name, ex_dividend_date, amount, …}}。
    mis_fetcher.build_calendar() 直接讀 d["name"]（缺了會 KeyError），所以每檔 name 必要且為字串；
    ex_dividend_date 存在須為合法日期（缺省時 build_calendar 會跳過該檔）；amount 有限或 null。"""
    if not isinstance(obj, dict):
        raise DataInvalid("dividend_calendar.json 不是物件")
    _dict_of_dicts("dividend_calendar.etfs", obj.get("etfs"))
    for code, d in obj["etfs"].items():
        w = "dividend_calendar." + code
        if not isinstance(d.get("name"), str):
            raise DataInvalid(f"{w} 缺 name（build_calendar 必要欄位）：{d!r}")
        _opt_num(w, d, "amount")
        _opt_str(w, d, "ex_dividend_date", date=True)
        _opt_str(w, d, "code")
        _opt_str(w, d, "amount_source")


def validate_known_codes(obj):
    if not isinstance(obj, list) or not all(isinstance(c, str) and c for c in obj):
        raise DataInvalid("known_codes.json 不是代號字串陣列")


def validate_daily_state(obj):
    """daily_state.json：{狀態名: {代號: 數值}}（yld_prev、zero_vol_streak）；數值須有限或 null。"""
    if not isinstance(obj, dict):
        raise DataInvalid("daily_state.json 不是物件")
    for k, v in obj.items():
        if not isinstance(v, dict) or not all(isinstance(c, str) and (x is None or _fin(x)) for c, x in v.items()):
            raise DataInvalid(f"daily_state.{k} 不是 {{代號: 數值}}：{str(v)[:80]}")


def _pool_row_ok(r):
    if isinstance(r, list):                       # 舊格式 [代號, 名稱, is_otc]（讀取時走保守規則，不是類型證據）
        return len(r) >= 2 and all(isinstance(x, str) for x in r[:2])
    return (isinstance(r, dict) and all(isinstance(r.get(k), str) and r[k] for k in ("code", "name", "cfi", "seen"))
            and r.get("section") == "ETF" and isinstance(r.get("is_otc"), bool) and _is_date(r["seen"])
            and ("absent_since" not in r or _is_date(r["absent_since"]))                     # D-014 選填
            and ("notified" not in r or (isinstance(r["notified"], str) and ":" in r["notified"]
                                         and _is_date(r["notified"].split(":", 1)[1]))))


def validate_pool_cache(obj):
    """新格式 [{code, name, is_otc, section: "ETF", cfi, seen}]（ISIN 區段＋CFI＋確認日，即 ETF 類型證據）；
    舊格式 [[代號, 名稱, …]] 仍可讀（但不算類型證據）。
    D-056：正式版 D-055 v2 完整性記錄 {format: "etf-pool-cache/v2", complete, markets, rows: [[代號, 名稱, is_otc]]}
    同樣可讀（過渡／歷史格式），但不是類型證據（product_policy 不採用，需完整查核初始化）。"""
    if isinstance(obj, dict) and obj.get("format") == "etf-pool-cache/v2":
        rows = obj.get("rows")
        if (obj.get("complete") is not True or not isinstance(obj.get("markets"), dict) or not isinstance(rows, list) or not rows
                or not all(isinstance(r, list) and len(r) == 3 and _pool_row_ok(r) and isinstance(r[2], bool) for r in rows)):
            raise DataInvalid("etf_pool_cache.json v2 記錄結構不合法")
        return
    if not isinstance(obj, list) or not obj or not all(_pool_row_ok(r) for r in obj):
        raise DataInvalid("etf_pool_cache.json 不是 [{code, name, is_otc, section: ETF, cfi}] 或 [[代號, 名稱, …]] 陣列")
    if any(isinstance(r, dict) for r in obj):
        if not all(isinstance(r, dict) for r in obj):
            raise DataInvalid("etf_pool_cache.json 新舊格式混雜")
        import product_policy
        try:
            product_policy.validate_evidence_rows(obj)          # 代號格式、CFI CE…、日期存在、代號不重複
        except product_policy.PolicyError as e:
            raise DataInvalid(str(e))


def validate_excluded_products(obj):
    import product_policy
    try:
        product_policy.validate_policy(obj)
    except product_policy.PolicyError as e:
        raise DataInvalid(str(e))


def validate_active_flow(obj):
    """active_flow.json（flow.js treemap 以 amount 算面積、buy／sell 顯示合計）：
    每檔 name 字串；buy／sell／scale_pct 有限或 null；holdings／changed 為整數或 null；
    flow 為 [{code, delta_shares, amount}]，數值有限。"""
    if not isinstance(obj, dict) or not isinstance(obj.get("updated"), str):
        raise DataInvalid("active_flow.json 缺 updated")
    _dict_of_dicts("active_flow.etfs", obj.get("etfs"))
    for code, e in obj["etfs"].items():
        w = "active_flow." + code
        _opt_str(w, e, "name")
        for k in ("buy", "sell", "scale_pct"):
            _opt_num(w, e, k)
        for k in ("holdings", "changed"):
            v = e.get(k)
            if v is not None and not (isinstance(v, int) and not isinstance(v, bool)):
                raise DataInvalid(f"{w}.{k} 不是整數：{v!r}")
        fl = e.get("flow")
        if fl is None:
            continue
        if not isinstance(fl, list):
            raise DataInvalid(f"{w}.flow 不是陣列")
        for r in fl:
            if not isinstance(r, dict) or not isinstance(r.get("code"), str):
                raise DataInvalid(f"{w}.flow 項目無效：{r!r}")
            _req_num(w + ".flow." + r["code"], r, "amount")
            _req_num(w + ".flow." + r["code"], r, "delta_shares")


def validate_active_snapshot(obj):
    """_active_snapshot.json（fetch_active_etf 下次比對用）：每檔 holdings 為 {股票代號: {shares}}，
    shares 為有限且 ≥ 0 的數值；data_date 為日期或 null。"""
    if not isinstance(obj, dict):
        raise DataInvalid("_active_snapshot.json 不是物件")
    _dict_of_dicts("_active_snapshot.etfs", obj.get("etfs"))
    for code, e in obj["etfs"].items():
        w = "_active_snapshot." + code
        _opt_str(w, e, "data_date", date=True)
        h = e.get("holdings")
        if not isinstance(h, dict):
            raise DataInvalid(f"{w}.holdings 不是物件：{type(h).__name__}")
        for sc, x in h.items():
            if not isinstance(x, dict):
                raise DataInvalid(f"{w}.holdings.{sc} 不是物件")
            _req_num(f"{w}.holdings.{sc}", x, "shares", 0)


# 檔名 → 契約（publish_gate.py／validate_data.py 依實際要提交的檔名查表；查不到的 JSON 只做嚴格解析）
VALIDATORS = {
    "_base.json":             validate_base,
    "market.json":            validate_market,
    "dividend_info.json":     validate_dividend_info,
    "dividend_calendar.json": validate_dividend_calendar,
    "known_codes.json":       validate_known_codes,
    "daily_state.json":       validate_daily_state,
    "etf_pool_cache.json":    validate_pool_cache,
    "excluded_products.json": validate_excluded_products,
    "active_flow.json":       validate_active_flow,
    "_active_snapshot.json":  validate_active_snapshot,
}


def validate_text(name, text, policy=False, ctx=None):
    """以檔名查契約，驗證 JSON 文字（嚴格解析＋契約）。失敗丟 DataInvalid／ValueError。
    policy=True（要發布的新資料）：_base.json／market.json 另外套用商品收錄政策；
    ctx：同一版本的證據／排除清單文字（見 _check_no_excluded）。"""
    obj = strict_loads(text)
    pv = POLICY_VALIDATORS.get(Path(name).name) if policy else None
    if pv:
        pv(obj, ctx)
    else:
        v = VALIDATORS.get(Path(name).name)
        if v:
            v(obj)
    return obj
