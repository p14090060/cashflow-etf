"""00996A 交接檔（feed/mega）——handoff contract、雲端驗證、交易日工具。

背景（AI_HANDOFF「00996A Incident」）：兆豐投信官網在 GitHub Actions 上 PCF 頁與商品頁皆 HTTP 403，
本機可正常取得。架構：本機 collector 只產出交接檔 → feed/mega 分支 → Actions 驗證後才採用；
Actions 仍是 data/active_flow.json 唯一寫入者。本模組不寫任何正式資料。

交接檔 mega_<code>_<data_date>.json（schema_version 1）：
{
  "schema_version": 1,
  "etf_code": "00996A",
  "etf_name": "主動兆豐台灣豐收",
  "issuer": "兆豐",
  "official_data_date": "YYYY-MM-DD",   # 官方頁面標示的資料日（不是抓取日、不是查詢日）
  "query_date": "YYYY-MM-DD" | null,    # trade_pcf 的 qdt（公告日＝資料日的下一交易日）；最新一份為 null
  "fetched_at": "YYYY-MM-DDTHH:MM:SS+08:00",
  "source": {"id": "mega_trade_pcf" | "mega_product", "url": "..."},
  "holdings": [{"code": "2330", "name": "台積電", "shares": 147000, "raw": {...原始欄位}}],
  "row_count": 53,
  "sha256": "<holdings 正規化 JSON 的 sha256>"   # 只做傳輸完整性，不代表資料真實
}
"""
import datetime, hashlib, json, os, re

SCHEMA_VERSION = 1
SOURCES = {"mega_trade_pcf", "mega_product"}
CODE_RE = re.compile(r"\d{4,6}[A-Z]?")
MIN_ROWS = 20           # 00996A 歷來 52～53 檔；過少多半是頁面不完整
MAX_ROWS = 300
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _canon(holdings):
    return json.dumps([[h["code"], h["name"], h["shares"]] for h in holdings],
                      ensure_ascii=False, separators=(",", ":"))


def holdings_sha256(holdings):
    return hashlib.sha256(_canon(holdings).encode("utf-8")).hexdigest()


def build_record(code, name, issuer, data_date, holdings, source_id, url,
                 query_date=None, fetched_at=None):
    """holdings：{code: {"name", "shares", ...}}（adapter 的格式）→ 交接檔 dict。"""
    rows = [{"code": c, "name": v.get("name", ""), "shares": v.get("shares"),
             "raw": {k: x for k, x in v.items() if k not in ("name", "shares")}}
            for c, v in sorted(holdings.items())]
    fa = fetched_at or datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds")
    return {"schema_version": SCHEMA_VERSION, "etf_code": code, "etf_name": name,
            "issuer": issuer, "official_data_date": data_date,
            "query_date": query_date, "fetched_at": fa,
            "source": {"id": source_id, "url": url},
            "holdings": rows, "row_count": len(rows),
            "sha256": holdings_sha256(rows)}


def validate_record(rec, expected_code, current_date=None):
    """雲端驗證。回傳 (ok, reason)。current_date：目前正式資料的資料日（新資料必須更新）。"""
    if not isinstance(rec, dict):
        return False, "not_object"
    if rec.get("schema_version") != SCHEMA_VERSION:
        return False, f"schema_version {rec.get('schema_version')!r}"
    if rec.get("etf_code") != expected_code:
        return False, f"wrong_etf {rec.get('etf_code')!r}"
    d = rec.get("official_data_date")
    if not (isinstance(d, str) and DATE_RE.fullmatch(d)):
        return False, f"bad_date {d!r}"
    try:
        dd = datetime.date.fromisoformat(d)
    except ValueError:
        return False, f"bad_date {d!r}"
    if dd.weekday() >= 5:
        return False, f"weekend_date {d}"
    if current_date and d <= current_date:
        return False, f"not_newer {d} <= {current_date}"
    src = rec.get("source") or {}
    if src.get("id") not in SOURCES or not str(src.get("url", "")).startswith("https://www.megafunds.com.tw/"):
        return False, "bad_source"
    rows = rec.get("holdings")
    if not isinstance(rows, list) or not rows:
        return False, "empty_holdings"
    if not (MIN_ROWS <= len(rows) <= MAX_ROWS):
        return False, f"row_count {len(rows)}"
    if rec.get("row_count") != len(rows):
        return False, "row_count_mismatch"
    seen = set()
    for r in rows:
        c = r.get("code") if isinstance(r, dict) else None
        if not (isinstance(c, str) and CODE_RE.fullmatch(c)):
            return False, f"bad_code {c!r}"
        if c in seen:
            return False, f"duplicate {c}"
        seen.add(c)
        s = r.get("shares")
        if not (isinstance(s, int) and not isinstance(s, bool) and s > 0):
            return False, f"bad_shares {c}={s!r}"
        if not (isinstance(r.get("name"), str) and r["name"].strip()):
            return False, f"bad_name {c}"
    if rec.get("sha256") != holdings_sha256(rows):
        return False, "sha256_mismatch"
    return True, "ok"


def record_to_adapter(rec):
    """交接檔 → fetch_mega 的輸出格式（_Holdings 由呼叫端包）。"""
    return {"name": rec.get("etf_name") or rec["etf_code"], "issuer": rec.get("issuer") or "兆豐",
            "data_date": rec["official_data_date"],
            "holdings": {r["code"]: {"name": r["name"], "shares": r["shares"]} for r in rec["holdings"]}}


def write_atomic(path, rec):
    """先寫 .tmp、fsync，再 rename——中途中斷只會留下 .tmp，consumer 不讀 .tmp。"""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_valid_for_date(feed_dir, expected_code, date):
    """feed 裡指定資料日、驗證通過的交接檔；沒有回 None。"""
    if not feed_dir or not os.path.isdir(feed_dir):
        return None
    path = os.path.join(feed_dir, f"mega_{expected_code}_{date}.json")
    try:
        rec = _load(path)
    except Exception:
        return None
    ok, _ = validate_record(rec, expected_code)
    return rec if ok and rec.get("official_data_date") == date else None


def latest_valid(feed_dir, expected_code, current_date=None, log=print, is_trading=None):
    """選出要採用的 feed。回傳 (record, basis)：
      record：最新、驗證通過、比 current_date 新、且 official_data_date 確認為交易日的交接檔；沒有則 (None, None)。
      basis ：它的「上一交易日」比對基準——
              None  ＝ current_date 本身就是上一交易日（沿用正式快照）
              dict  ＝ feed 內上一交易日的合法交接檔（改用它當基準，避免跨多日的假單日 Flow）
              False ＝ 找不到上一交易日基準（呼叫端不得算 Flow，只能當 no_basis）
    交易日曆無法確認時 fail closed（不採用該檔）。"""
    if not feed_dir or not os.path.isdir(feed_dir):
        log(f"[FEED] 沒有 feed 目錄（{feed_dir}）")
        return None, None
    try:
        f = _cal(is_trading)
    except RuntimeError as e:
        log(f"[FEED] {e}，不採用 feed")
        return None, None
    pat = re.compile(rf"mega_{re.escape(expected_code)}_(\d{{4}}-\d{{2}}-\d{{2}})\.json")
    names = sorted((n for n in os.listdir(feed_dir) if pat.fullmatch(n)), reverse=True)
    if not names:
        log("[FEED] feed 目錄內沒有交接檔")
    by_date = {pat.fullmatch(n).group(1): n for n in names}
    for n in names:
        try:
            rec = _load(os.path.join(feed_dir, n))
        except Exception as e:
            log(f"[FEED] {n} 讀取失敗：{type(e).__name__}")
            continue
        ok, why = validate_record(rec, expected_code, current_date)
        if ok and pat.fullmatch(n).group(1) != rec["official_data_date"]:
            ok, why = False, "filename_date_mismatch"
        if ok:
            d = datetime.date.fromisoformat(rec["official_data_date"])
            t = f(d)
            if t is None:
                log(f"[FEED] {n} 無法確認 {d} 是否為交易日，fail closed 不採用")
                return None, None
            if not t:
                ok, why = False, f"not_trading_day {d}"
        if not ok:
            log(f"[FEED] {n} 不採用：{why}")
            if why.startswith("not_newer"):
                break          # 依檔名新到舊，後面只會更舊
            continue
        pd = prev_trading_day(d, f)
        if pd is None:
            log(f"[FEED] 無法確認 {d} 的上一交易日，fail closed 不採用")
            return None, None
        if current_date == pd.isoformat():
            return rec, None
        bn = by_date.get(pd.isoformat())
        basis = False
        if bn:
            try:
                b = _load(os.path.join(feed_dir, bn))
                bok, bwhy = validate_record(b, expected_code)
                if bok and b["official_data_date"] == pd.isoformat():
                    basis = b
                else:
                    log(f"[FEED] 基準 {bn} 不合法：{bwhy}")
            except Exception as e:
                log(f"[FEED] 基準 {bn} 讀取失敗：{type(e).__name__}")
        if basis is False:
            log(f"[FEED] {d} 缺上一交易日 {pd} 的基準 → 只更新持股、不算 Flow（no_basis）")
        return rec, basis
    return None, None


# ── 交易日：重用 fetch_active_etf 既有的行情日曆（closes_on：TWSE MI_INDEX 往回找有行情的那天）──
#   由 fetch_active_etf 在 import 時注入（set_calendar），不另建第二套日期規則。
#   is_trading(d) 回 True／False；無法確認（網路失敗等）回 None。
_IS_TRADING = None


def set_calendar(is_trading):
    global _IS_TRADING
    _IS_TRADING = is_trading


def _cal(is_trading):
    f = is_trading or _IS_TRADING
    if f is None:
        raise RuntimeError("交易日曆未設定")
    return f


def next_trading_day(d, is_trading=None, max_days=15):
    """d 之後的下一個交易日（不含 d）。今天以後的日期尚無行情，退回「非週末」——
    只用於查詢參數 qdt，不會被當成官方資料日。日曆無法確認時拋例外（呼叫端既有 try 會接住）。"""
    f = _cal(is_trading)
    today = datetime.date.today()
    x = d
    for _ in range(max_days):
        x += datetime.timedelta(days=1)
        ok = (x.weekday() < 5) if x >= today else f(x)
        if ok is None:
            raise RuntimeError(f"無法確認 {x} 是否為交易日")
        if ok:
            return x
    raise ValueError(f"{d} 之後 {max_days} 天內找不到交易日")


def prev_trading_day(d, is_trading=None, max_days=15):
    """d 之前的上一個交易日；無法確認回 None（fail closed）。"""
    f = _cal(is_trading)
    x = d
    for _ in range(max_days):
        x -= datetime.timedelta(days=1)
        ok = f(x)
        if ok is None:
            return None
        if ok:
            return x
    return None
