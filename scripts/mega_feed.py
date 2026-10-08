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
import datetime, hashlib, json, os, re, urllib.request

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


def latest_valid(feed_dir, expected_code, current_date=None, log=print):
    """在 feed_dir 找最新、驗證通過、且比 current_date 新的交接檔。回傳 record 或 None。"""
    if not feed_dir or not os.path.isdir(feed_dir):
        log(f"[FEED] 沒有 feed 目錄（{feed_dir}）")
        return None
    pat = re.compile(rf"mega_{re.escape(expected_code)}_(\d{{4}}-\d{{2}}-\d{{2}})\.json")
    names = sorted((n for n in os.listdir(feed_dir) if pat.fullmatch(n)), reverse=True)
    if not names:
        log("[FEED] feed 目錄內沒有交接檔")
    for n in names:
        try:
            with open(os.path.join(feed_dir, n), encoding="utf-8") as f:
                rec = json.load(f)
        except Exception as e:
            log(f"[FEED] {n} 讀取失敗：{type(e).__name__}")
            continue
        ok, why = validate_record(rec, expected_code, current_date)
        if ok and pat.fullmatch(n).group(1) != rec["official_data_date"]:
            ok, why = False, "filename_date_mismatch"
        if ok:
            return rec
        log(f"[FEED] {n} 不採用：{why}")
        if why.startswith("not_newer"):
            break          # 依檔名新到舊，後面只會更舊
    return None


# ── 交易日（證交所 FMTQIK 每月成交資訊：有列出的日期才是交易日）──
_TD_CACHE = {}


def _fmtqik_days(year, month):
    key = (year, month)
    if key not in _TD_CACHE:
        url = ("https://www.twse.com.tw/exchangeReport/FMTQIK?response=json"
               f"&date={year}{month:02d}01")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode("utf-8"))
        days = set()
        for row in j.get("data") or []:
            y, m, d = row[0].split("/")
            days.add(datetime.date(int(y) + 1911, int(m), int(d)))
        _TD_CACHE[key] = days
    return _TD_CACHE[key]


def next_trading_day(d, is_trading=None, max_days=15):
    """d 之後的下一個交易日（不含 d）。is_trading 可注入（測試用）。

    未來日期 FMTQIK 尚無資料時，退回「下一個非週末日」——只用於查詢參數，
    不會被當成官方資料日（官方資料日一律以頁面標示為準）。
    """
    if is_trading is None:
        def is_trading(x):
            if x > datetime.date.today():
                return x.weekday() < 5
            return x in _fmtqik_days(x.year, x.month)
    x = d
    for _ in range(max_days):
        x += datetime.timedelta(days=1)
        if is_trading(x):
            return x
    raise ValueError(f"{d} 之後 {max_days} 天內找不到交易日")
