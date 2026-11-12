"""Bounded recovery of missing distribution policy from identified TWSE notices.

No dividend-history inference, quote requests, Telegram, or publication here.
"""
import datetime
import hashlib
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BASE = "https://www.twse.com.tw"
UNKNOWN = (None, "", "?", "不明")


class Rows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(re.sub(r"\s+", "", "".join(self.cell)))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def parse_policy(body, code):
    """Only an identified fund's explicitly labelled policy cell is evidence."""
    text = body.decode("utf-8", errors="strict")
    parser = Rows()
    parser.feed(text)
    identities = [r[1] for r in parser.rows if len(r) == 2 and
                  r[0] in ("證券代號", "股票代號", "ETF代號", "證券編號", "上市代號")]
    if not identities or any(x != code for x in identities):
        raise ValueError("official notice fund identity missing or mismatched")
    cells = [r[1] for r in parser.rows if len(r) == 2 and
             r[0] in ("ETF配息頻率/次數", "配息頻率/次數", "配息頻率", "收益分配頻率")]
    mapping = {"收益不分配": "不配息", "不分配收益": "不配息", "不配息": "不配息",
               "月配": "月配", "月配息": "月配", "每月": "月配",
               "季配": "季配", "季配息": "季配", "每季": "季配",
               "半年配": "半年配", "半年配息": "半年配", "每半年": "半年配",
               "年配": "年配", "年配息": "年配", "每年": "年配",
               "雙月配": "雙月配", "雙月配息": "雙月配"}
    values = [mapping.get(x) for x in cells]
    if not values or None in values or len(set(values)) != 1:
        raise ValueError("explicit distribution policy missing, ambiguous or conflicting")
    return values[0]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ETF-policy-recovery/1.0"})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=6) as response:
        final = urllib.parse.urlsplit(response.url)
        if response.status != 200 or final.scheme != "https" or final.hostname != "www.twse.com.tw":
            raise ValueError("official source returned an unexpected status or destination")
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("official response exceeds evidence size limit")
        return body


def resolve_frequency(code, get=None):
    """At most one search + three identified notices. Failures remain explicit."""
    if not isinstance(code, str) or not re.fullmatch(r"[0-9A-Z]{4,8}", code):
        return {"status": "unresolved", "reason": "invalid fund code", "attempts": []}
    get = get or _get
    attempts, evidence = [], []
    url = BASE + "/zh/ETFortune/newsList?" + urllib.parse.urlencode({"keyword": code})

    def read(source):
        try:
            body = get(source)
            attempts.append({"url": source, "sha256": hashlib.sha256(body).hexdigest(),
                             "bytes": len(body), "status": "received"})
            return body
        except Exception as ex:
            attempts.append({"url": source, "status": "failed", "reason": type(ex).__name__})
            return None

    body = read(url)
    if body is not None:
        text = body.decode("utf-8", errors="replace")
        paths = []
        for row in re.findall(r"<tr\b[^>]*>.*?</tr>", text, re.S | re.I):
            title = re.sub(r"<[^>]*>", " ", row)
            if not re.search(r"(?<![A-Za-z0-9])" + code + r"(?![A-Za-z0-9])", title):
                continue
            match = re.search(r"/zh/ETFortune/newsDetail/[a-fA-F0-9]+", row)
            if match and match[0] not in paths:
                paths.append(match[0])
        if len(paths) > 3:
            return {"status": "unresolved", "reason": "too many policy candidates; not fully checked",
                    "attempts": attempts}
        for path in paths:
            source = BASE + path
            raw = read(source)
            if raw is None:
                continue
            try:
                frequency = parse_policy(raw, code)
                evidence.append({"code": code, "frequency": frequency, "url": source,
                                 "sha256": hashlib.sha256(raw).hexdigest()})
            except (ValueError, UnicodeError) as ex:
                attempts[-1]["policy_error"] = str(ex)
    values = {e["frequency"] for e in evidence}
    if len(values) != 1 or any(a["status"] == "failed" for a in attempts):
        return {"status": "unresolved", "reason": "official policy unavailable or conflicting",
                "attempts": attempts}
    return {"status": "verified", "code": code, "frequency": values.pop(), "sources": evidence,
            "checked_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
            "attempts": attempts}


def recover_missing(etfs, info_map, resolver=None, limit=4):
    """Repair missing policy only; never infer dates, money, or known policies.

    Caller owns persistence/publication. Deferred work is not labelled 'not found'.
    """
    resolver = resolver or resolve_frequency
    attempts, recovered = [], []
    for entry in etfs:
        code = entry.get("code")
        if (entry.get("div_freq") or entry.get("div_frequency")) not in UNKNOWN:
            continue
        meta = info_map.get(code, {})
        if not isinstance(meta, dict):
            attempts.append({"code": code, "status": "unresolved", "reason": "invalid static record"})
            continue
        known = effective_frequency(code, meta)          # D-068：有證據就須通過驗證；壞證據＝未知，照常補查／警報
        if known is not None:
            # Previously verified/static data was not yet propagated to market.
            entry.pop("div_freq", None)
            entry["div_frequency"] = known
            continue
        if len([a for a in attempts if a.get("status") != "deferred"]) >= limit:
            attempts.append({"code": code, "status": "deferred", "reason": "bounded lookup budget; retry next run"})
            continue
        try:
            result = resolver(code)
        except Exception as ex:
            result = {"status": "unresolved", "reason": type(ex).__name__}
        attempts.append({"code": code, **result})
        if result.get("status") != "verified":
            continue
        frequency = result.get("frequency")
        if frequency not in ("不配息", "月配", "季配", "半年配", "年配", "雙月配"):
            continue
        updated = dict(meta)
        updated.setdefault("name", entry.get("name", code))
        updated.setdefault("months", [])
        updated.setdefault("avg_dividend_per_share", None)
        updated.setdefault("_todo", True)  # Policy verification does not verify every dividend field.
        updated["frequency"] = frequency
        updated["frequency_evidence"] = result
        info_map[code] = updated
        entry.pop("div_freq", None)
        entry["div_frequency"] = frequency
        recovered.append(code)
    return {"attempts": attempts, "recovered": recovered}


# ── D-068：官方政策證據與待公告查證（只服務配息通知修復；不是通用爬蟲）──
# 採用的發行人／交易所文件只限下列 https 來源（精確主機＋路徑前綴）；每份文件須另有 TWSE 同代號身分頁核對。
EVIDENCE_SOURCES = (
    ("www.twse.com.tw", "/"),
    ("www.cathaysite.com.tw", "/"),
    ("cwapi.cathaysite.com.tw", "/"),
    ("www.fubon.com", "/asset-management/"),
    ("www.fsitc.com.tw", "/"),
)
POLICIES = ("不配息", "月配", "季配", "半年配", "年配", "雙月配")
_HEX64 = re.compile(r"[0-9a-f]{64}")
# 「收益不分配」類政策只認明確語句；單獨一個「無」字不算（例如表格欄位「收益分配 無」必須另有完整句）。
_NO_DIST_PHRASES = ("本基金收益不分配", "收益不分配", "不配息，基金之收益全部併入基金資產")


def _https_url_ok(url):
    try:
        sp = urllib.parse.urlsplit(str(url))
    except ValueError:
        return False
    return sp.scheme == "https" and bool(sp.hostname) and not sp.username and not sp.password


def evidence_url_ok(url):
    try:
        sp = urllib.parse.urlsplit(str(url))
    except ValueError:
        return False
    if sp.scheme != "https" or sp.username or sp.password or sp.port or sp.fragment:
        return False
    return any(sp.hostname == h and sp.path.startswith(p) for h, p in EVIDENCE_SOURCES)


# D-068 R1（F1）：持久化證據讀回時一樣要核「來源＋種類＋身分鏈」，不因「已存進去」就可信。
# 只接受下列三種實際 producer 寫出的形狀（不以代號豁免）：
#   twse_notice  ：resolve_frequency（TWSE ETFortune 公告）——sources 無 kind、url＝www.twse.com.tw/zh/ETFortune/newsDetail/<hex>，無 identity
#   issuer_doc   ：verify_issuer_no_distribution——sources 一筆、kind 為已審兩種之一、url 符合該種類，必有 TWSE 精確身分鏈
#   legacy_tsit  ：D-063 後已審發布的台新產品頁格式（00851）——url 精確 www.tsit.com.tw/ETF/Home/ETFSeriesDetail/<同代號>，無 kind／identity
_TWSE_NOTICE = re.compile(r"/zh/ETFortune/newsDetail/[a-fA-F0-9]+")
_ISSUER_KINDS = {
    "fubon_fund_page": lambda sp: sp.hostname == "www.fubon.com" and sp.path == "/asset-management/fund/info/fund"
                                  and re.fullmatch(r"Fd=\d+", sp.query or "") is not None,
    "cathay_prospectus_pdf": lambda sp: sp.hostname == "cwapi.cathaysite.com.tw" and sp.path.startswith("/uploads/")
                                        and sp.path.lower().endswith(".pdf") and not sp.query,
}


def _split_exact(url):
    """https、無帳密／port／fragment 才回 SplitResult，否則 None（壞型別不崩潰）。"""
    if not isinstance(url, str):
        return None
    try:
        sp = urllib.parse.urlsplit(url)
        if sp.scheme != "https" or sp.username or sp.password or sp.port or sp.fragment or not sp.hostname:
            return None
    except ValueError:
        return None
    return sp


def _source_shape(code, s):
    sp = _split_exact(s.get("url"))
    if sp is None:
        return None
    kind = s.get("kind")
    if kind is None:
        if sp.hostname == "www.twse.com.tw" and _TWSE_NOTICE.fullmatch(sp.path) and not sp.query:
            return "twse_notice"
        if sp.hostname == "www.tsit.com.tw" and sp.path == "/ETF/Home/ETFSeriesDetail/" + code and not sp.query:
            return "legacy_tsit"
        return None
    if isinstance(kind, str) and kind in _ISSUER_KINDS and _ISSUER_KINDS[kind](sp):
        return "issuer_doc"
    return None


def policy_evidence_problem(code, meta):
    """dividend_info 單檔的官方政策證據是否可採；None＝可採，否則回原因。沒有證據欄位回 'absent'。"""
    try:
        return _policy_evidence_problem(code, meta)
    except Exception as ex:                      # 壞型別一律當無效證據，不崩潰
        return "evidence malformed（%s）" % type(ex).__name__


def _policy_evidence_problem(code, meta):
    if not isinstance(meta, dict):
        return "invalid static record"
    ev = meta.get("frequency_evidence")
    if ev is None:
        return "absent"
    if not isinstance(ev, dict) or ev.get("status") != "verified" or ev.get("code") != code:
        return "evidence status／code mismatch"
    if meta.get("frequency") not in POLICIES or ev.get("frequency") != meta.get("frequency"):
        return "evidence frequency mismatch"
    srcs = ev.get("sources")
    if not isinstance(srcs, list) or not srcs:
        return "evidence has no sources"
    shapes = set()
    for s in srcs:
        if not isinstance(s, dict) or not isinstance(s.get("sha256"), str) or not _HEX64.fullmatch(s["sha256"]):
            return "evidence source sha256 invalid"
        if s.get("code") != code or s.get("frequency") != meta.get("frequency"):
            return "evidence source code／frequency mismatch"
        shape = _source_shape(code, s)
        if shape is None:
            return "evidence source not an accepted official source／kind"
        shapes.add(shape)
    if len(shapes) != 1 or (shapes & {"issuer_doc", "legacy_tsit"} and len(srcs) != 1):
        return "evidence mixes source kinds"
    shape = shapes.pop()
    try:
        datetime.datetime.fromisoformat(str(ev.get("checked_at")))
    except ValueError:
        return "evidence checked_at invalid"
    ident = ev.get("identity")
    if shape != "issuer_doc":
        return None if ident is None else "identity chain not expected for this source kind"
    # 發行人文件：必須有 TWSE 同代號身分鏈，身分頁 URL 精確等於 www.twse.com.tw/zh/ETFortune/etfInfo/<代號>
    if not isinstance(ident, dict) or ident.get("code") != code:
        return "identity chain missing／code mismatch"
    if not all(isinstance(ident.get(k), str) and ident[k] for k in ("full_name", "issuer", "short_name")):
        return "identity chain fields missing"
    if ident.get("twse_url") != "https://www.twse.com.tw/zh/ETFortune/etfInfo/" + code:
        return "identity TWSE url not exact"
    if not isinstance(ident.get("twse_sha256"), str) or not _HEX64.fullmatch(ident["twse_sha256"]):
        return "identity TWSE sha256 invalid"
    kind = srcs[0]["kind"]
    if (kind == "fubon_fund_page" and "富邦" not in ident["issuer"]) or (kind == "cathay_prospectus_pdf" and "國泰" not in ident["issuer"]):
        return "identity issuer does not match document kind"
    if ev.get("frequency") != "不配息" or ev.get("policy_statement") not in _NO_DIST_PHRASES + ("收益分配不配息，基金之收益全部併入基金資產",):
        return "issuer evidence statement／policy invalid"
    return None


def effective_frequency(code, meta):
    """靜態頻率的單一採用規則（fetch／mis／daily 共用）：有證據就必須通過驗證，否則視為未知；
    沒有證據欄位的既有靜態資料照舊沿用（不追溯推翻人工核實資料）。"""
    if not isinstance(meta, dict) or meta.get("frequency") in UNKNOWN:
        return None
    p = policy_evidence_problem(code, meta)
    if p not in (None, "absent"):
        return None
    return meta["frequency"]


def _plain(html_bytes):
    text = html_bytes.decode("utf-8", errors="strict")
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", text, flags=re.S | re.I)
    return re.sub(r"\s+", "", __import__("html").unescape(re.sub(r"<[^>]+>", " ", text)))


def twse_identity(code, html_bytes):
    """TWSE ETFortune etfInfo 頁：取完整基金名稱與發行公司，且證券代號必須是 code。"""
    t = _plain(html_bytes)
    m = re.search(r"ETF商品(?P<name>[^\s]{6,120}?)證券代號(?P<code>[0-9A-Z]{4,8})證券簡稱(?P<short>.{1,30}?)證券類別.{1,20}?發行公司(?P<issuer>.{2,40}?股份有限公司)", t)
    if not m or m.group("code") != code:
        raise ValueError("TWSE identity page code missing or mismatched")
    return {"code": code, "full_name": m.group("name"), "short_name": m.group("short"), "issuer": m.group("issuer")}


def _norm_name(s):
    return re.sub(r"[\s（）()]|加掛美元受益憑證", "", s)


def verify_issuer_no_distribution(code, twse_url, twse_bytes, doc_url, doc_bytes, doc_text, kind, checked_at):
    """以已保存原文核實「發行人文件明確不分配收益」並建立可持久化證據；任何一項不符 → ValueError。
    kind: 'fubon_fund_page'（HTML，頁內 stkId 必須等於代號）或 'cathay_prospectus_pdf'（PDF 由呼叫端轉出文字 doc_text，
    PDF 本身沒有代號 → 須以文件內完整基金名稱＝TWSE 身分頁完整名稱、發行公司相符建立身分鏈）。"""
    if not evidence_url_ok(twse_url) or urllib.parse.urlsplit(twse_url).path != "/zh/ETFortune/etfInfo/" + code:
        raise ValueError("TWSE identity url not exact")
    if not evidence_url_ok(doc_url) or urllib.parse.urlsplit(doc_url).hostname == "www.twse.com.tw":
        raise ValueError("issuer document url not allowed")
    ident = twse_identity(code, twse_bytes)
    if kind == "fubon_fund_page":
        if not doc_url.startswith("https://www.fubon.com/asset-management/fund/info/fund?Fd="):
            raise ValueError("fubon fund page url not exact")
        raw = doc_bytes.decode("utf-8", errors="strict")
        stk = re.findall(r'var\s+stkId\s*=\s*"([0-9A-Z]{4,8})"', raw)
        if stk != [code] or "富邦" not in ident["issuer"]:
            raise ValueError("fubon page stkId／issuer does not match TWSE identity")
        t = _plain(doc_bytes)
        stmt = "收益分配不配息，基金之收益全部併入基金資產"          # 基金檔案欄位「收益分配」的完整值，不是單字判斷
        if t.count(stmt) != 1:
            raise ValueError("fubon page has no single explicit no-distribution policy field")
    elif kind == "cathay_prospectus_pdf":
        if not doc_url.startswith("https://cwapi.cathaysite.com.tw/uploads/") or not doc_bytes.startswith(b"%PDF-"):
            raise ValueError("cathay prospectus url／format not exact")
        t = re.sub(r"\s+", "", doc_text or "")
        if "國泰" not in ident["issuer"] or _norm_name(ident["full_name"]) not in t:
            raise ValueError("prospectus does not name the TWSE-identified fund／issuer")
        if not re.search(r"\(無，本基金收益不分配\)|本基金收益不分配", t):
            raise ValueError("prospectus has no explicit no-distribution statement")
        stmt = "本基金收益不分配"
    else:
        raise ValueError("unknown issuer document kind")
    return {"status": "verified", "code": code, "frequency": "不配息", "policy_statement": stmt,
            "sources": [{"code": code, "frequency": "不配息", "url": doc_url, "sha256": hashlib.sha256(doc_bytes).hexdigest(),
                         "kind": kind}],
            "identity": dict(ident, twse_url=twse_url, twse_sha256=hashlib.sha256(twse_bytes).hexdigest()),
            "checked_at": checked_at}


# ── 待公告逾期查證：只用既有可信 TWSE 配息日曆（dividend_calendar.json），不另外爬投信網站 ──
# D-068 R1（F2）：只認 fetch_dividend_calendar.py 實際寫出的 TWSE 官方金額來源字串（精確比對，不以字首代表官方）。
# 「（保留前值）」「FinMind（估算）」「MoneyDJ」「Gavin 人工確認」等一律非官方 → partial。
_TWSE_AMOUNT_SOURCES = re.compile(r"TWSE|TWSE × FinMind 核實|TWSE（FinMind 差異 \d{1,3}%）")


def _official_amount(src):
    return isinstance(src, str) and _TWSE_AMOUNT_SOURCES.fullmatch(src) is not None


def pending_announcement(code, since, cal_entry):
    """回傳 (status, detail)。status：announced（有效同檔官方公告：除息日在 since 之後、金額為 TWSE 官方且 > 0）／
    partial（有日期但金額非官方或 0，維持待公告）／none／invalid（資料壞掉）。不試算、不改殖利率。"""
    if not isinstance(cal_entry, dict):
        return "none", "TWSE 配息日曆沒有這檔"
    if cal_entry.get("code") != code:             # producer 一定寫 code；缺漏或不符都不能關聯到這檔
        return "invalid", "日曆項目代號 %r 與 %s 不符" % (cal_entry.get("code"), code)
    try:
        ex = datetime.date.fromisoformat(str(cal_entry.get("ex_dividend_date")))
    except ValueError:
        return "invalid", "除息日不合法：%r" % cal_entry.get("ex_dividend_date")
    if ex <= since:
        return "none", "日曆最近除息日 %s 不在上次查證 %s 之後" % (ex, since)
    amt = cal_entry.get("amount")
    if isinstance(amt, bool) or not isinstance(amt, (int, float)) or amt != amt or amt in (float("inf"), float("-inf")):
        return "invalid", "金額不合法：%r" % amt
    if amt <= 0 or not _official_amount(cal_entry.get("amount_source")):
        return "partial", "已有除息日 %s，但金額 %r（來源 %r）非 TWSE 官方，維持待公告" % (ex, amt, cal_entry.get("amount_source"))
    return "announced", {"ex_dividend_date": ex.isoformat(), "amount": float(amt), "amount_source": cal_entry.get("amount_source")}


def pending_resolution_problem(code, meta, since=None):
    """dividend_info 單檔的待公告解除紀錄是否有效；None＝有效。since 給了就須是同一段待公告（pending_since 相同）。"""
    try:
        return _pending_resolution_problem(code, meta, since)
    except Exception as ex:
        return "resolution malformed（%s）" % type(ex).__name__


def _pending_resolution_problem(code, meta, since):
    if not isinstance(meta, dict) or not isinstance(meta.get("pending_resolution"), dict):
        return "absent"
    r = meta["pending_resolution"]
    if r.get("source") == "TPEx ETF InfoHub 配息清單（etfExDiv）":
        return _tpex_resolution_problem(code, meta, since)
    if r.get("status") != "announced" or r.get("code") != code or not _official_amount(r.get("amount_source")) \
            or r.get("source") not in ("TWSE 配息日曆（dividend_calendar.json）", HISTORY_SOURCE):
        return "resolution status／code／source invalid"
    try:
        ps = datetime.date.fromisoformat(str(r.get("pending_since")))
        ex = datetime.date.fromisoformat(str(r.get("ex_dividend_date")))
        datetime.datetime.fromisoformat(str(r.get("checked_at")))
    except ValueError:
        return "resolution dates invalid"
    a = r.get("amount")
    if isinstance(a, bool) or not isinstance(a, (int, float)) or not (a > 0) or a != a or a == float("inf"):
        return "resolution amount invalid"
    if ex <= ps:
        return "resolution ex-date not after pending_since"
    if since is not None and str(since) != ps.isoformat():
        return "resolution belongs to a different pending period"
    # R1（F1）：歷史清單來源嚴格核實際寫出的格式；日曆來源不得混帶歷史專有欄位（保留已發布日曆格式相容）
    hist_keys = {"url", "sha256", "pay_date"}
    if r.get("source") == HISTORY_SOURCE:
        if not history_url_ok(code, r.get("url"), ps):
            return "history resolution url invalid"
        if not isinstance(r.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", r["sha256"]):
            return "history resolution sha256 invalid"
        if r.get("pay_date") is not None:
            try:
                datetime.date.fromisoformat(r["pay_date"])
            except (TypeError, ValueError):
                return "history resolution pay_date invalid"
    elif hist_keys & set(r):
        return "calendar resolution carries history-only fields"
    return None


def _tpex_resolution_problem(code, meta, since):
    """同基金 TPEx 正額公告；嚴格獨立格式，不混用 TWSE 資格或來源。"""
    r = meta["pending_resolution"]
    keys = {"status", "code", "pending_since", "ex_dividend_date", "amount", "amount_source", "source",
            "checked_at", "pay_date", "url", "sha256", "request_params", "identity"}
    if set(r) != keys or r.get("status") != "announced" or r.get("code") != code or r.get("amount_source") != "TPEx":
        return "TPEx resolution format／code／amount source invalid"
    if not isinstance(code, str) or not re.fullmatch(r"[0-9A-Z]{4,8}", code):
        return "TPEx resolution code invalid"
    ps = datetime.date.fromisoformat(r["pending_since"])
    ex = datetime.date.fromisoformat(r["ex_dividend_date"])
    checked = datetime.datetime.fromisoformat(r["checked_at"])
    if checked.tzinfo is None or checked.date() > datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date():
        return "TPEx resolution checked date invalid"
    if ex <= ps or checked.date() < ps or (since is not None and str(since) != ps.isoformat()):
        return "TPEx resolution pending period invalid"
    amount = r["amount"]
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not (0 < amount < float("inf")):
        return "TPEx resolution amount invalid"
    if r["pay_date"] is not None and datetime.date.fromisoformat(r["pay_date"]) < ex:
        return "TPEx resolution payment before ex-date"
    ident = r["identity"]
    ikeys = {"code", "name", "full_name", "issuer", "listing_date", "url", "sha256"}
    if not isinstance(ident, dict) or set(ident) != ikeys or ident.get("code") != code:
        return "TPEx resolution identity invalid"
    if not isinstance(ident["name"], str) or not ident["name"].strip() or _norm(ident["name"]) != _norm(meta.get("name")):
        return "TPEx resolution identity name mismatch"
    if not isinstance(ident["full_name"], str) or "基金" not in ident["full_name"] or not isinstance(ident["issuer"], str) or not ident["issuer"].strip():
        return "TPEx resolution full identity missing"
    listed = datetime.date.fromisoformat(ident["listing_date"])
    if listed > ps or listed > checked.date():
        return "TPEx resolution listing date invalid"
    if ident["url"] != "https://info.tpex.org.tw/api/etfProduct?lang=zh-tw&query=" + code or r["url"] != "https://info.tpex.org.tw/api/etfExDiv":
        return "TPEx resolution URL invalid"
    for value in (ident["sha256"], r["sha256"]):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            return "TPEx resolution hash invalid"
    if r["request_params"] != {"stkNo": code, "startDate": listed.strftime("%Y%m%d"), "endDate": checked.strftime("%Y%m%d"), "lang": "zh-tw"}:
        return "TPEx resolution request parameters invalid"
    return None


# ── D-071：全體未知配息政策的自動查證（TWSE 公告＋投信投顧公會 SITCA ETF 基本資料表）──
def tpex_calendar_problem(code, entry):
    """A new TPEx calendar row must carry the same exact identity/hash proof.

    Reuse the reviewed TPEx evidence validator with listing as the lower bound;
    the temporary wrapper is never persisted as a fake pending period.
    """
    try:
        if (not isinstance(entry, dict) or entry.get('code') != code or
                entry.get('amount_source') != 'TPEx' or not isinstance(entry.get('name'), str)):
            return 'TPEx calendar identity invalid'
        proof = entry['tpex_evidence']
        if not isinstance(proof, dict) or set(proof) != {'identity', 'url', 'sha256', 'request_params', 'checked_at', 'pay_date'}:
            return 'TPEx calendar proof format invalid'
        checked = datetime.datetime.fromisoformat(proof['checked_at'])
        if datetime.date.fromisoformat(entry['ex_dividend_date']) > checked.date() + datetime.timedelta(days=366):
            return 'TPEx calendar announcement too far in the future'
        record = dict(proof, status='announced', code=code,
                      pending_since=proof['identity']['listing_date'],
                      ex_dividend_date=entry['ex_dividend_date'], amount=entry['amount'],
                      amount_source='TPEx', source='TPEx ETF InfoHub 配息清單（etfExDiv）')
        return _tpex_resolution_problem(code, {'name': entry['name'], 'pending_resolution': record}, None)
    except (KeyError, TypeError, ValueError, AttributeError):
        return 'TPEx calendar proof invalid'


def tpex_pending_resolution(code, entry, since):
    """Bind an already verified calendar candidate to the real pending period."""
    if tpex_calendar_problem(code, entry) is not None:
        return None
    record = dict(entry['tpex_evidence'], status='announced', code=code,
                  pending_since=str(since), ex_dividend_date=entry['ex_dividend_date'],
                  amount=entry['amount'], amount_source='TPEx',
                  source='TPEx ETF InfoHub 配息清單（etfExDiv）')
    meta = {'name': entry['name'], 'pending_resolution': record}
    return record if pending_resolution_problem(code, meta, str(since)) is None else None


def stored_tpex_calendar(code, meta):
    """Recover a verified row after the existing daily calendar writer resets it."""
    import copy
    try:
        if not isinstance(meta, dict):
            return None
        if 'tpex_calendar' in meta:
            entry = meta['tpex_calendar']
            if (tpex_calendar_problem(code, entry) is not None or
                    _norm(meta.get('name')) != _norm(entry['name'])):
                return None
            return copy.deepcopy(entry)
        r = meta.get('pending_resolution', {})
        if r.get('source') != 'TPEx ETF InfoHub 配息清單（etfExDiv）' or pending_resolution_problem(code, meta) is not None:
            return None
        entry = {'code': code, 'name': meta['name'], 'ex_dividend_date': r['ex_dividend_date'],
                 'amount': r['amount'], 'amount_source': 'TPEx',
                 'tpex_evidence': {k: r[k] for k in ('identity', 'url', 'sha256', 'request_params', 'checked_at', 'pay_date')}}
        return entry if tpex_calendar_problem(code, entry) is None else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


# 支援來源（只有這些，不宣稱查遍所有發行人官網）：
#   1. SITCA「ETF基本資料」月報 www.sitca.org.tw/ROC/SITCA_ETF/etf_statement2.aspx?txtR1=0&txtYM=YYYYMM
#      整張表一次讀取（每輪最多 SITCA_MONTHS 個月份請求），涵蓋全部商品，不佔逐檔查詢額度。
#   2. TWSE ETFortune 政策公告（resolve_frequency，既有；逐檔、每輪上限 limit）。
SITCA_HOST = "www.sitca.org.tw"
SITCA_URL = "https://www.sitca.org.tw/ROC/SITCA_ETF/etf_statement2.aspx?txtR1=0&txtYM={ym}"
SITCA_MONTHS = 2                       # 最新可用月報：上月，取不到再往前一個月
SITCA_MAX_AGE_MONTHS = 3               # 報表月份距今超過就不採用（過期來源不採用、不覆蓋）
SITCA_HEADER = ["序號", "類型代號", "證券代號", "證券簡稱", "基金統編", "基金名稱", "類型"]
SITCA_POLICY = {"不分級別/不分配": "不配息", "不分級別/分配(月配)": "月配", "不分級別/分配(季配)": "季配",
                "不分級別/分配(半年配)": "半年配", "不分級別/分配(年配)": "年配", "不分級別/分配(雙月配)": "雙月配"}
POLICY_VALUES = ("不配息", "月配", "季配", "半年配", "年配", "雙月配")
# 狀態碼（daily_state 只能存數值）
QUEUED, TEMP_FAIL, ADOPTED, CONFLICT, NO_RESULT = 1, 2, 3, 4, 5
STATUS_TEXT = {QUEUED: "排隊待查", TEMP_FAIL: "暫時失敗（下輪重試）", ADOPTED: "已採用", CONFLICT: "來源衝突／身分不符",
               NO_RESULT: "支援來源已完成查證仍無明確政策"}
EXCLUDED_SUFFIX = ("K",)               # K 類依既有資格政策處理，不納入政策補查


def _norm(s):
    import unicodedata
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s or "")))


def _get_sitca(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ETF-policy-recovery/1.0"})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
        final = urllib.parse.urlsplit(response.url)
        if response.status != 200 or final.scheme != "https" or final.hostname != SITCA_HOST:
            raise ValueError("SITCA returned an unexpected status or destination")
        body = response.read(3_000_001)
        if len(body) > 3_000_000:
            raise ValueError("SITCA response exceeds evidence size limit")
        return body


def _clean_cell(x):
    import html as _html
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def parse_sitca(body, ym, today):
    """SITCA ETF 基本資料月報 → {代號: [(簡稱, 完整名稱, 類型), …]}。
    格式不符（不是 HTML 表、PDF／其他內容、表頭不同、表單月份不是 ym、更新日期不在該月之後或在未來、列數太少）→ ValueError。"""
    if not isinstance(body, bytes) or body[:5] == b"%PDF-":
        raise ValueError("SITCA body is not the HTML statement")
    text = body.decode("utf-8-sig", errors="strict")
    if 'action="./etf_statement2.aspx?txtR1=0&amp;txtYM=%s"' % ym not in text or "ETF基本資料" not in text:
        raise ValueError("SITCA page is not the requested monthly statement")
    m = re.search(r'id="ctl00_ContentPlaceHolder1_lblMRdate">(\d{4})\.(\d{2})\.(\d{2})<', text)
    if not m:
        raise ValueError("SITCA statement update date missing")
    updated = datetime.date(int(m[1]), int(m[2]), int(m[3]))
    first_next = (datetime.date(int(ym[:4]), int(ym[4:]), 28) + datetime.timedelta(days=4)).replace(day=1)
    if not (first_next <= updated <= today):
        raise ValueError("SITCA statement update date %s not after %s or in the future" % (updated, ym))
    rows, header_ok = {}, False
    for tr in re.findall(r"<tr\b[^>]*>.*?</tr>", text, re.S | re.I):
        cells = [_clean_cell(c) for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
        if cells[:7] == SITCA_HEADER:
            header_ok = True
            continue
        if header_ok and len(cells) >= 7 and re.fullmatch(r"[0-9A-Z]{4,8}", cells[2]):
            rows.setdefault(cells[2], []).append((cells[3], cells[5], cells[6]))
    if not header_ok or len(rows) < 100:
        raise ValueError("SITCA statement table missing or incomplete")
    return {"report_month": ym, "updated": updated.isoformat(), "rows": rows}


def _months_back(today, n):
    y, m, out = today.year, today.month, []
    for _ in range(n):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append("%04d%02d" % (y, m))
    return out


def load_sitca(today, get=None):
    """讀最新可用月報（上月→前一月）。回傳 (statement 或 None, attempts)。只讀，不推論。"""
    get = get or _get_sitca
    attempts = []
    for ym in _months_back(today, SITCA_MONTHS):
        url = SITCA_URL.format(ym=ym)
        try:
            body = get(url)
        except Exception as ex:
            attempts.append({"url": url, "status": "failed", "reason": type(ex).__name__})
            continue
        try:
            st = parse_sitca(body, ym, today)
        except (ValueError, UnicodeError) as ex:
            attempts.append({"url": url, "status": "rejected", "reason": str(ex)[:120], "sha256": hashlib.sha256(body).hexdigest()})
            continue
        st.update(url=url, sha256=hashlib.sha256(body).hexdigest())
        attempts.append({"url": url, "status": "received", "sha256": st["sha256"]})
        return st, attempts
    return None, attempts


def sitca_policy(code, name, st, today):
    """單檔判讀 → (status, frequency, detail)。status：verified／absent（表內沒有或不是明確頻率、月報過期）／
    conflict（簡稱身分不符或同代號多列分類矛盾）。"""
    rows = st["rows"].get(code)
    if not rows:
        return "absent", None, "SITCA %s 月報沒有 %s" % (st["report_month"], code)
    y, m = int(st["report_month"][:4]), int(st["report_month"][4:])
    if (today.year - y) * 12 + today.month - m > SITCA_MAX_AGE_MONTHS:
        return "absent", None, "SITCA 月報 %s 已過期" % st["report_month"]
    if any(_norm(r[0]) != _norm(name) for r in rows):
        return "conflict", None, "SITCA 簡稱 %r 與商品名稱 %r 不符" % (rows[0][0], name)
    values = {SITCA_POLICY.get(r[2]) for r in rows}
    if len(values) != 1:
        return "conflict", None, "SITCA 同代號多列分類不一致：%s" % sorted({r[2] for r in rows})
    freq = values.pop()
    if freq is None:
        return "absent", None, "SITCA 分類 %r 不是明確頻率" % rows[0][2]
    return "verified", freq, {"kind": "sitca_etf_statement", "code": code, "frequency": freq, "report_month": st["report_month"],
                              "report_updated": st["updated"], "url": st["url"], "sha256": st["sha256"],
                              "short_name": rows[0][0], "full_name": rows[0][1], "classification": rows[0][2]}


# ── CLOSE_TOP100_RECOVERY（2026-11-12）：兩個已驗明的發行人政策入口（只此兩種，不泛化到其他網站）──
#   fuhwa_etf_page   ：復華 ETF 商品頁 https://www.fhtrust.com.tw/ETF/etf_detail/ETFnn（代號→頁碼只認下表，表外＝未支援）。
#                      身分＝頁首 <span class="text-en-9-bold">代號</span><span class="pl-2 text-9-medium">簡稱</span> 恰好一組、
#                      簡稱＝商品名稱、h1 完整名稱；政策＝「基本資料」表格「收益分配」那一格，只認「否」→ 不配息
#                      （「是」沒有頻率 → 無明確政策）。導覽選單／下拉清單／標題／基金特色文案都不當證據。
#   esun_sprospectus ：玉山 ETF 專頁 https://www.esunam.com/act/etf_<代號>/ 連出的 assets/pdf/<代號>_sProspectus.pdf。
#                      身分＝專頁 <title> 含代號與名稱 N、該專頁恰有一個同代號簡式公開說明書連結；PDF「基金名稱」＝玉山＋N＋證券投資信託基金；
#                      政策＝簡式公開說明書基本資料表「存續期間」欄之後、「計價幣別」欄之前那一格的完整值（季配息等）。
#                      PDF 文字以標準庫 zlib 解析（FlateDecode／ObjStm／Identity-H＋ToUnicode），不依賴外部工具或套件。
#   兩者都保存原件 sha256、來源日期（復華：頁面淨值日期；玉山：刊印日期）、完整政策欄原文與身分；金額／月份不從這裡推。
ISSUER_KIND = "issuer_policy_page"
# R1（F3）：精確身分表。首次解析與讀回都對同一張表核對：同代號的入口、頁碼、完整基金名稱、簡稱（＝商品名稱）、
# 玉山專頁標題名稱。表外代號＝未支援（覆蓋不足）。新增一檔須先以官方原件核實這幾項再加表，不以任意字串拼接通過。
ISSUER_FUNDS = {
    "00418A": {"issuer": "fuhwa", "page": "ETF27", "full_name": "復華台灣新星主動式ETF基金", "short_name": "主動復華台灣新星"},
    "00413A": {"issuer": "esun", "title_name": "臺灣關鍵科技主動式ETF",
               "full_name": "玉山臺灣關鍵科技主動式ETF證券投資信託基金", "short_name": "主動玉山關鍵科技"},
}
FUHWA_ETF_PAGES = {c: f["page"] for c, f in ISSUER_FUNDS.items() if f["issuer"] == "fuhwa"}
FUHWA_HOST, ESUN_HOST = "www.fhtrust.com.tw", "www.esunam.com"
ESUN_CELL = {"月配息": "月配", "雙月配息": "雙月配", "季配息": "季配", "半年配息": "半年配", "年配息": "年配", "不配息": "不配息"}
_ISSUER_KEYS = {"kind", "issuer", "code", "frequency", "url", "sha256", "source_date", "checked_at", "full_name", "short_name", "statement"}


def fuhwa_url(code):
    page = FUHWA_ETF_PAGES.get(code)
    return "https://%s/ETF/etf_detail/%s" % (FUHWA_HOST, page) if page else None


def esun_urls(code):
    return "https://%s/act/etf_%s/" % (ESUN_HOST, code), "https://%s/act/etf_%s/assets/pdf/%s_sProspectus.pdf" % (ESUN_HOST, code, code)


def issuer_entry(code, name):
    """此代號是否有已支援的發行人入口：('fuhwa'|'esun', url) 或 None（未支援＝覆蓋不足，不是查無）。"""
    if not isinstance(code, str) or not re.fullmatch(r"[0-9]{4,6}[A-Z]?", code):
        return None
    f = ISSUER_FUNDS.get(code)
    if f is None:
        return None                                   # 表外代號＝未支援（覆蓋不足）；名稱不符由解析／讀回核對拒用
    return (f["issuer"], fuhwa_url(code)) if f["issuer"] == "fuhwa" else (f["issuer"], esun_urls(code)[0])


def _issuer_get(url, host):
    request = urllib.request.Request(url, headers={"User-Agent": "ETF-policy-recovery/1.0"})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
        final = urllib.parse.urlsplit(response.url)
        if response.status != 200 or final.scheme != "https" or final.hostname != host:
            raise ValueError("issuer source returned an unexpected status or destination")
        body = response.read(3_000_001)
        if len(body) > 3_000_000:
            raise ValueError("issuer response exceeds evidence size limit")
        return body


def _tag_text(html_text, pattern):
    import html as _html
    return [re.sub(r"\s+", "", _html.unescape(re.sub(r"<!--.*?-->|<[^>]+>", "", m))) for m in re.findall(pattern, html_text, re.S)]


def parse_fuhwa_page(code, short_name, url, body):
    """→ (frequency 或 None, 欄位原文, 完整名稱, 來源日期)；身分或格式不符 → ValueError。"""
    if url != fuhwa_url(code) or not isinstance(body, bytes) or body[:5] == b"%PDF-":
        raise ValueError("fuhwa page url／format not exact")
    t = body.decode("utf-8", errors="strict")
    heads = re.findall(r'<span class="text-en-9-bold">\s*([0-9A-Z]{4,8})\s*</span>\s*<span class="pl-2 text-9-medium">\s*([^<]{1,40}?)\s*</span>', t)
    if len(heads) != 1 or heads[0][0] != code or _norm(heads[0][1]) != _norm(short_name) \
            or _norm(heads[0][1]) != _norm(ISSUER_FUNDS.get(code, {}).get("short_name")):
        raise ValueError("fuhwa page identity (code／short name) missing or mismatched")
    full = _tag_text(t, r'<h1 class="fundState-name heading-1">(.*?)</h1>')
    if len(full) != 1 or full[0] != ISSUER_FUNDS.get(code, {}).get("full_name"):
        raise ValueError("fuhwa page full fund name missing")
    dates = re.findall(r'<div class="fundState-date[^"]*">\s*(\d{4})/(\d{2})/(\d{2})\s*</div>', t)
    if len(set(dates)) != 1:
        raise ValueError("fuhwa page source date missing or ambiguous")
    src_date = datetime.date(*map(int, dates[0])).isoformat()
    cells = re.findall(r'<th class="fundInformationTable-head">\s*收益分配(?:<!--v-if-->)?\s*</th>\s*'
                       r'<td class="fundInformationTable-content[^"]*">(.*?)</td>', t, re.S)
    vals = [re.sub(r"\s+", "", re.sub(r"<!--.*?-->|<[^>]+>", "", c, flags=re.S)) for c in cells]
    if len(vals) != 1:
        raise ValueError("fuhwa page 收益分配 field missing or duplicated")
    return ("不配息" if vals[0] == "否" else None), "收益分配：" + vals[0], full[0], src_date


def parse_esun_landing(code, url, body):
    """→ (pdf_url, 名稱 N)。"""
    landing, pdf = esun_urls(code)
    if url != landing or not isinstance(body, bytes) or body[:5] == b"%PDF-":
        raise ValueError("esun landing url／format not exact")
    t = body.decode("utf-8", errors="strict")
    titles = _tag_text(t, r"<title>(.*?)</title>")
    m = re.fullmatch(r"玉山投信%s(.+?ETF)(?:｜.*)?" % re.escape(code), titles[0]) if len(titles) == 1 else None
    if not m:
        raise ValueError("esun landing title identity missing or mismatched")
    links = set(re.findall(r'href="([^"]*_sProspectus\.pdf)"', t))
    if links != {"assets/pdf/%s_sProspectus.pdf" % code}:
        raise ValueError("esun landing simplified prospectus link missing or ambiguous")
    if m.group(1) != ISSUER_FUNDS.get(code, {}).get("title_name"):
        raise ValueError("esun landing title name is not the registered fund")
    return pdf, m.group(1)


def pdf_text(blob):
    """最小 PDF 文字抽取（標準庫）：只支援本入口實際格式；不支援／損壞的結構一律在此邊界轉成 ValueError（R1 F4），不猜。"""
    import zlib
    try:
        return _pdf_text(blob)
    except ValueError:
        raise
    except (zlib.error, KeyError, AttributeError, IndexError, TypeError, UnicodeError, OverflowError) as ex:
        raise ValueError("PDF structure unsupported or corrupt（%s）" % type(ex).__name__)


def _pdf_text(blob):
    import zlib
    if not isinstance(blob, bytes) or not blob.startswith(b"%PDF-") or b"/Encrypt" in blob:
        raise ValueError("not an unencrypted PDF")
    objs = {int(m.group(1)): m.group(2) for m in re.finditer(rb"(\d+) 0 obj(.*?)endobj", blob, re.S)}

    def stream(body):
        i = body.find(b"stream")
        if i < 0:
            raise ValueError("PDF object has no stream")
        s = body[i + 6:]
        s = s[2:] if s[:2] == b"\r\n" else s[1:]
        raw = s[:s.rfind(b"endstream")]
        filt = re.findall(rb"/Filter\s*/(\w+)", body[:i])
        if filt == [b"FlateDecode"]:
            return zlib.decompress(raw)
        if not filt:
            return raw
        raise ValueError("unsupported PDF filter")
    for body in list(objs.values()):
        if b"/ObjStm" in body[:300]:
            d, first = stream(body), int(re.search(rb"/First (\d+)", body).group(1))
            hdr = list(map(int, d[:first].split()))
            for k in range(0, len(hdr), 2):
                end = hdr[k + 3] if k + 3 < len(hdr) else len(d) - first
                objs.setdefault(hdr[k], d[first + hdr[k + 1]:first + end])

    def cmap(n):
        d, m = stream(objs[n]).decode("latin1"), {}
        for blk in re.findall(r"beginbfchar(.*?)endbfchar", d, re.S):
            for a, u in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                m[int(a, 16)] = bytes.fromhex(u).decode("utf-16-be")
        for blk in re.findall(r"beginbfrange(.*?)endbfrange", d, re.S):
            for a, z, u, arr in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:<([0-9A-Fa-f]+)>|\[([^\]]*)\])", blk):
                lo, hi = int(a, 16), int(z, 16)
                if u:
                    for k in range(lo, hi + 1):
                        m[k] = chr(int(u, 16) + k - lo)
                else:
                    for k, x in zip(range(lo, hi + 1), re.findall(r"<([0-9A-Fa-f]+)>", arr)):
                        m[k] = bytes.fromhex(x).decode("utf-16-be")
        return m
    pages_obj = [n for n, b in sorted(objs.items()) if re.search(rb"/Type\s*/Pages\b", b)]
    if len(pages_obj) != 1:
        raise ValueError("PDF page tree not supported")
    kids = [int(x) for x in re.findall(rb"(\d+) 0 R", re.search(rb"/Kids\s*\[(.*?)\]", objs[pages_obj[0]], re.S).group(1))]
    out = []
    tok = re.compile(r"/(F\d+)\s+[\d.]+\s+Tf|\[(.*?)\]\s*TJ|\(((?:\\.|[^\\)])*)\)\s*Tj|<([0-9A-Fa-f]*)>\s*Tj|(T\*|Td|TD|Tm|ET)\b", re.S)
    for p in kids:
        page = objs[p]
        fonts = {k.decode(): int(v) for k, v in re.findall(rb"/(F\d+) (\d+) 0 R", page)}
        maps = {}
        for k, v in fonts.items():
            tu = re.search(rb"/ToUnicode (\d+) 0 R", objs[v])
            if re.search(rb"/Subtype\s*/Type0", objs[v]) and not tu:
                raise ValueError("composite font without ToUnicode")
            maps[k] = cmap(int(tu.group(1))) if tu else None
        cur, text = None, []
        for t in tok.finditer(stream(objs[int(re.search(rb"/Contents (\d+) 0 R", page).group(1))]).decode("latin1")):
            if t.group(1):
                cur = t.group(1)
                continue
            if t.group(5):
                text.append("\n")
                continue
            if t.group(2) is not None:
                parts = re.findall(r"<([0-9A-Fa-f]*)>|\(((?:\\.|[^\\)])*)\)", t.group(2))
            elif t.group(3) is not None:
                parts = [("", t.group(3))]
            else:
                parts = [(t.group(4), "")]
            m = maps.get(cur)
            for hx, lit in parts:
                raw = bytes.fromhex(hx) if hx else re.sub(r"\\(.)", r"\1", lit).encode("latin1")
                if m is None:
                    text.append(raw.decode("cp1252", errors="replace"))
                else:
                    text.append("".join(m.get(raw[i] * 256 + raw[i + 1], "�") for i in range(0, len(raw) - 1, 2)))
        out.append("".join(text))
    return "\n".join(out)


def parse_esun_sprospectus(code, name_n, url, blob):
    """→ (frequency, 欄位原文, 完整名稱, 刊印日期)。"""
    if url != esun_urls(code)[1]:
        raise ValueError("esun prospectus url not exact")
    flat = re.sub(r"\s+", "", pdf_text(blob))
    full = "玉山" + _norm(name_n) + "證券投資信託基金"
    if full != ISSUER_FUNDS.get(code, {}).get("full_name"):
        raise ValueError("esun fund name is not the registered fund")
    if "基金名稱" + full not in flat or "簡式公開說明書" not in flat:
        raise ValueError("simplified prospectus does not name the landing-page fund")
    dm = re.findall(r"刊印日期：(\d{4})年(\d{1,2})月(\d{1,2})日", flat)
    if len(set(dm)) != 1:
        raise ValueError("simplified prospectus print date missing or ambiguous")
    head = flat.split("壹、基本資料", 1)
    if len(head) != 2 or "貳、" not in head[1]:
        raise ValueError("simplified prospectus basic-data section missing")
    sec = head[1].split("貳、", 1)[0]
    cells = re.findall(r"存續期間不定期限[^一-鿿]{0,12}(月配息|雙月配息|季配息|半年配息|年配息|不配息)計價幣別", sec)
    if len(cells) != 1 or sec.count("配息計價幣別") != 1:
        raise ValueError("simplified prospectus distribution cell missing or ambiguous")
    return ESUN_CELL[cells[0]], "基本資料：" + cells[0], full, datetime.date(*map(int, dm[0])).isoformat()


def resolve_issuer_policy(code, name, now_iso, get=None):
    """發行人入口一次查證。回傳 {status: verified／no_policy／failed／rejected／unsupported, frequency, source, detail, label}。
    failed（連線／403／逾時）與 rejected（格式或身分不符）都不算完成判讀。"""
    entry = issuer_entry(code, name)
    if entry is None:
        return {"status": "unsupported", "detail": "沒有已支援的發行人入口（覆蓋不足，不是查無）"}
    issuer, url = entry
    get = get or _issuer_get
    label = "復華商品頁" if issuer == "fuhwa" else "玉山簡式公開說明書"
    try:
        if issuer == "fuhwa":
            body = get(url, FUHWA_HOST)
        else:
            landing = get(url, ESUN_HOST)
    except Exception as ex:
        return {"status": "failed", "label": label, "detail": "%s讀取失敗（%s，下輪重試）" % (label, type(ex).__name__)}
    try:
        if issuer == "fuhwa":
            freq, stmt, full, sdate = parse_fuhwa_page(code, name, url, body)
            src = {"url": url, "sha256": hashlib.sha256(body).hexdigest()}
        else:
            pdf_url, n = parse_esun_landing(code, url, landing)
            try:
                blob = get(pdf_url, ESUN_HOST)
            except Exception as ex:
                return {"status": "failed", "label": label, "detail": "%s讀取失敗（%s，下輪重試）" % (label, type(ex).__name__)}
            freq, stmt, full, sdate = parse_esun_sprospectus(code, n, pdf_url, blob)
            src = {"url": pdf_url, "sha256": hashlib.sha256(blob).hexdigest(), "landing_url": url,
                   "landing_sha256": hashlib.sha256(landing).hexdigest()}
    except (ValueError, UnicodeError, KeyError, AttributeError, IndexError, TypeError) as ex:
        return {"status": "rejected", "label": label, "detail": "%s格式／身分不符（%s），未算完成" % (label, str(ex)[:80])}
    if freq is None:
        return {"status": "no_policy", "label": label, "detail": "%s「%s」不是明確頻率" % (label, stmt)}
    source = dict(src, kind=ISSUER_KIND, issuer=issuer, code=code, frequency=freq, source_date=sdate, checked_at=now_iso,
                  full_name=full, short_name=name, statement=stmt)
    if policy_source_problem(code, {"frequency": freq, "policy_source": dict(source)}) is not None:
        return {"status": "rejected", "label": label, "detail": "%s採用紀錄自我核對失敗" % label}
    return {"status": "verified", "label": label, "frequency": freq, "source": source, "detail": "%s：%s" % (label, stmt)}


def issuer_source_problem(code, ps):
    """issuer_policy_page 採用紀錄讀回核對（不重抓原件）：入口、網址、身分、欄位原文與頻率的對應都要精確。"""
    issuer = ps.get("issuer")
    keys = _ISSUER_KEYS | ({"landing_url", "landing_sha256"} if issuer == "esun" else set())
    if set(ps) != keys:
        return "issuer policy_source fields invalid"
    if ps.get("code") != code or not all(isinstance(ps.get(k), str) and ps[k] for k in keys):
        return "issuer policy_source code／field types invalid"
    if not all(re.fullmatch(r"[0-9a-f]{64}", ps[k]) for k in ("sha256", "landing_sha256") if k in ps):
        return "issuer policy_source sha256 invalid"
    f = ISSUER_FUNDS.get(code)
    if f is None or f["issuer"] != issuer or ps["full_name"] != f["full_name"] or ps["short_name"] != f["short_name"]:
        return "issuer policy_source identity is not the registered fund for this code"
    if issuer == "fuhwa":
        if ps["url"] != fuhwa_url(code) or ps["statement"] != "收益分配：否" or ps["frequency"] != "不配息":
            return "fuhwa policy_source url／statement invalid"
    elif issuer == "esun":
        landing, pdf = esun_urls(code)
        cell = ps["statement"][len("基本資料："):] if ps["statement"].startswith("基本資料：") else None
        if ps["url"] != pdf or ps["landing_url"] != landing or ESUN_CELL.get(cell) != ps["frequency"]:
            return "esun policy_source url／statement invalid"
    else:
        return "issuer policy_source issuer unknown"
    sdate = datetime.date.fromisoformat(ps["source_date"])
    checked = datetime.datetime.fromisoformat(ps["checked_at"])
    if checked.tzinfo is None or sdate > checked.astimezone(datetime.timezone(datetime.timedelta(hours=8))).date():
        return "issuer policy_source source_date after checked_at (future source)"
    return None


def policy_source_problem(code, meta):
    """D-071 policy_source（SITCA 採用紀錄）讀回核對；None＝有效、'absent'＝沒有該欄位。壞型別不崩潰。"""
    try:
        if not isinstance(meta, dict):
            return "invalid static record"
        ps = meta.get("policy_source")
        if ps is None:
            return "absent"
        if isinstance(ps, dict) and ps.get("kind") == ISSUER_KIND:
            return issuer_source_problem(code, ps) if ps.get("frequency") == meta.get("frequency") \
                else "policy_source frequency mismatch"
        if not isinstance(ps, dict) or ps.get("kind") != "sitca_etf_statement" or ps.get("code") != code:
            return "policy_source kind／code invalid"
        if ps.get("frequency") not in POLICY_VALUES or ps.get("frequency") != meta.get("frequency"):
            return "policy_source frequency mismatch"
        if ps.get("classification") not in SITCA_POLICY or SITCA_POLICY[ps["classification"]] != ps["frequency"]:
            return "policy_source classification invalid"
        ym = ps.get("report_month")
        if not isinstance(ym, str) or not re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])", ym) or ps.get("url") != SITCA_URL.format(ym=ym):
            return "policy_source url／month invalid"
        if not isinstance(ps.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", ps["sha256"]):
            return "policy_source sha256 invalid"
        datetime.date.fromisoformat(ps.get("report_updated"))
        datetime.datetime.fromisoformat(ps.get("checked_at"))
        if not (isinstance(ps.get("short_name"), str) and ps["short_name"] and isinstance(ps.get("full_name"), str) and ps["full_name"]):
            return "policy_source identity missing"
    except (TypeError, ValueError) as ex:
        return "policy_source malformed（%s）" % type(ex).__name__
    return None


def known_policy(code, meta):
    """已知政策或 None（安全版整合：D-068 frequency_evidence 與 D-071 policy_source 兩種證據都必須有效）。
    任一證據欄位存在但無效 → 視為未知、重新查證；兩者都沒有的既有已核靜態政策照舊沿用。"""
    if effective_frequency(code, meta) is None:
        return None
    if policy_source_problem(code, meta) not in (None, "absent"):
        return None
    return meta["frequency"]


def _adopt(info_map, code, name, frequency, source):
    meta = dict(info_map.get(code) or {})
    meta.setdefault("name", name or code)
    meta.setdefault("months", [])
    meta.setdefault("avg_dividend_per_share", None)
    meta.setdefault("_todo", True)              # 政策查證不等於金額／月份查證
    meta["frequency"] = frequency
    meta.pop("policy_source", None)
    meta.pop("frequency_evidence", None)       # 安全版整合：舊（可能失效）的 D-068 證據不得殘留在新採用紀錄上
    if source is not None:
        meta["policy_source"] = source
    info_map[code] = meta
    return meta


def prioritized(codes, last_try, priority, limit):
    """CLOSE_TOP100：收盤榜內優先，但只要榜外也有待查，每輪至少留一格給最久沒查的榜外（不讓既有輪替永久餓死）。
    回傳完整次序；前 limit 個是本輪要查的。"""
    base = sorted(codes, key=lambda c: (last_try.get(c, 0), c))
    priority = set(priority or ())
    top, rest = [c for c in base if c in priority], [c for c in base if c not in priority]
    if not top or not rest or limit < 2:
        return top + rest
    head = top[:limit - 1] + rest[:1]
    return head + [c for c in base if c not in head]


def recover_policies(etfs, info_map, last_try, today, now_iso, twse_resolver=None, sitca_get=None, limit=4,
                     priority=None, issuer_resolver=None):
    """每輪盤點全部未知政策（不限 TOP100）。SITCA 月報一次讀全表；SITCA 未解決的（缺值、身分不符、與已知政策衝突）
    依「最久沒查」輪替 TWSE 公告當替代來源，每輪最多 limit 檔（其餘排隊）。只寫 info_map 中原本未知（或證據失效）的條目；
    已知政策不覆蓋。completed＝本輪所有適用來源都實際讀完（未查／失敗不算）。checked＝本輪實際讀過的來源。
    D-071 R1：已知政策衝突也要查替代來源——TWSE 明確公告與現有政策相同 → 衝突解除；仍矛盾（含 SITCA 與 TWSE 都和現有不同）
    → 保留原政策、記衝突；TWSE 讀取失敗 → 暫時失敗；排隊 → 排隊。後兩者不算完成。"""
    resolver = twse_resolver or resolve_frequency
    st, sitca_attempts = load_sitca(today, sitca_get)
    sitca_label = "SITCA %s 月報" % st["report_month"] if st else None
    status, detail, checked, adopted, completed, twse_tried, conflicts_known, unknown = {}, {}, {}, [], [], [], [], []
    names = {e.get("code"): e.get("name", "") for e in etfs}
    pending = []                                  # 需要 TWSE 替代來源：(code, 種類)
    for e in etfs:
        code = e.get("code")
        if not isinstance(code, str) or code.endswith(EXCLUDED_SUFFIX):
            continue
        meta = info_map.get(code)
        known = known_policy(code, meta)
        if known is not None:
            if st is not None:
                s, f, _ = sitca_policy(code, names[code], st, today)
                if s == "verified" and f != known:
                    detail[code] = "現有政策 %s，%s為 %s" % (known, sitca_label, f)
                    checked[code] = [sitca_label]
                    conflicts_known.append(code)
                    pending.append((code, "known_conflict", known, f))
            if (e.get("div_freq") or e.get("div_frequency")) in UNKNOWN:
                e.pop("div_freq", None)
                e["div_frequency"] = known
            continue
        if (e.get("div_freq") or e.get("div_frequency")) not in UNKNOWN and meta is None:
            continue                              # 行情端已有頻率且靜態檔無條目：維持既有流程
        unknown.append(code)
    for code in unknown:
        if st is None:
            status[code], detail[code], checked[code] = TEMP_FAIL, "SITCA 月報暫時無法取得", []
            pending.append((code, "unknown", None, None))
            continue
        checked[code] = [sitca_label]
        s, f, d = sitca_policy(code, names[code], st, today)
        if s == "verified":
            _adopt(info_map, code, names[code], f, dict(d, checked_at=now_iso))
            status[code], detail[code] = ADOPTED, "%s：%s" % (sitca_label, d["classification"])
            adopted.append(code)
            continue
        detail[code] = d
        pending.append((code, "identity_conflict" if s == "conflict" else "unknown", None, None))
    # CLOSE_TOP100：已驗明的發行人入口（復華商品頁／玉山簡式公開說明書）。只對政策未知、且有入口的代號；
    # 與 TWSE 同額度上限（另計），榜內優先。失敗／格式不符 → 不算完成（incomplete），仍續查 TWSE 但不累積求助輪數。
    issuer_resolver = issuer_resolver or resolve_issuer_policy
    incomplete = set()
    cand = [c for c, k, _, _ in pending if k == "unknown" and issuer_entry(c, names.get(c)) is not None]
    order = prioritized(cand, last_try, priority, limit)
    for i, code in enumerate(order):
        if i >= limit:
            incomplete.add(code)
            detail[code] = (detail.get(code) or "") + "；發行人入口排隊（本輪額度已用完）"
            continue
        r = issuer_resolver(code, names.get(code), now_iso)
        if r.get("status") == "verified":
            _adopt(info_map, code, names[code], r["frequency"], r["source"])
            status[code], detail[code] = ADOPTED, r["detail"]
            checked.setdefault(code, []).append(r["label"])
            adopted.append(code)
            pending = [x for x in pending if x[0] != code]
            continue
        if r.get("status") == "no_policy":
            checked.setdefault(code, []).append(r["label"])
        else:
            incomplete.add(code)
        detail[code] = (detail.get(code) or "") + "；" + r.get("detail", "")
    kinds = {c: (k, known, sf) for c, k, known, sf in pending}
    for i, code in enumerate(prioritized(list(kinds), last_try, priority, limit)):
        kind, known, sitca_freq = kinds[code]
        if i >= limit:
            if status.get(code) != TEMP_FAIL:
                status[code] = QUEUED
            detail[code] = "排隊待查 TWSE 公告（本輪額度已用完）；" + detail.get(code, "")
            continue
        try:
            r = resolver(code)
        except Exception as ex:
            r = {"status": "unresolved", "reason": type(ex).__name__, "attempts": [{"status": "failed"}]}
        twse_tried.append(code)
        failed = any(a.get("status") == "failed" for a in r.get("attempts") or [])
        verified = r.get("status") == "verified" and r.get("frequency") in POLICY_VALUES
        if failed and not verified:
            status[code] = TEMP_FAIL
            detail[code] = (detail.get(code) or "") + "；TWSE 公告讀取失敗（下輪重試）"
            continue
        checked.setdefault(code, []).append("TWSE 公告")
        if kind == "known_conflict":
            if verified and r["frequency"] == known:
                status[code] = ADOPTED            # 替代來源確認現有政策：衝突解除，不改資料
                detail[code] = detail[code] + "；TWSE 公告確認現有 %s，衝突解除" % known
            else:
                status[code] = CONFLICT
                detail[code] += ("；TWSE 公告為 %s（仍與現有不同，保留原政策）" % r["frequency"]) if verified \
                    else "；TWSE 公告無明確政策（保留原政策）"
                completed.append(code)
            continue
        if verified:                              # TWSE 公告本身已核代號身分與明確頻率
            meta = _adopt(info_map, code, names[code], r["frequency"], None)
            meta["frequency_evidence"] = {k: v for k, v in r.items() if k != "attempts"}
            status[code], detail[code] = ADOPTED, "TWSE 公告：%s" % r["frequency"]
            adopted.append(code)
        elif status.get(code) == TEMP_FAIL:
            detail[code] = (detail.get(code) or "") + "；TWSE 公告無明確政策（SITCA 未取得，未算完成）"
        elif code in incomplete:
            status[code] = TEMP_FAIL
            detail[code] = "%s；TWSE 公告無明確政策（發行人入口未完成判讀，未算完成）" % (detail.get(code) or "")
        else:
            status[code] = CONFLICT if kind == "identity_conflict" else NO_RESULT
            detail[code] = "%s；TWSE 公告無明確政策（%s）" % (detail.get(code) or "SITCA 無明確分類", r.get("reason", ""))
            completed.append(code)
    return {"statement": st, "status": status, "detail": detail, "checked": checked, "adopted": adopted, "completed": completed,
            "twse_tried": twse_tried, "conflicts_known": conflicts_known,
            "sitca": {"ok": st is not None, "report_month": st and st["report_month"], "updated": st and st["updated"],
                      "sha256": st and st["sha256"], "attempts": sitca_attempts}}


def distribution_url_parts(url, code=None, *, legacy=False):
    """Exact existing TWSE distribution notice route; reject ambiguous query keys."""
    try:
        p = urllib.parse.urlsplit(url)
        q = urllib.parse.parse_qsl(p.query, keep_blank_values=True, strict_parsing=True)
        d = dict(q)
        if (p.scheme != "https" or p.netloc != "www.twse.com.tw" or p.fragment or
                p.path != "/zh/ETFortune/announcement" or len(q) != 5 or
                set(d) != {"company", "date", "seq", "fund", "type"} or d["type"] not in (("distribution", "all") if legacy else ("distribution",)) or
                not re.fullmatch(r"A[0-9]{5}", d["company"]) or not re.fullmatch(r"[0-9]{4,6}[A-Z]?", d["fund"]) or
                not re.fullmatch(r"[1-9][0-9]{0,5}", d["seq"]) or not re.fullmatch(r"[0-9]{8}", d["date"]) or
                (code is not None and d["fund"] != code)):
            return None
        datetime.datetime.strptime(d["date"], "%Y%m%d")
        return d
    except (TypeError, ValueError, KeyError):
        return None


def distribution_status_problem(code, st):
    """Persisted current-period decision format, including pre-existing records."""
    try:
        if not isinstance(st, dict) or st.get("status") != "no_distribution_this_period" or st.get("code") != code:
            return "decision identity"
        if any(not isinstance(st.get(k), str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", st[k]) for k in ("valuation_date", "announced_date", "valid_until")):
            return "decision dates"
        val, ann, until = (datetime.date.fromisoformat(st[k]) for k in ("valuation_date", "announced_date", "valid_until"))
        if not val <= ann <= val + datetime.timedelta(days=31) or not ann <= until < datetime.date(val.year + 1, 9, 30):
            return "decision period"
        src = st["source"]
        p = distribution_url_parts(src.get("url"), code, legacy=True)
        if not isinstance(src.get("name"), str) or not src["name"].strip() or p is None or p["date"] != ann.strftime("%Y%m%d"):
            return "decision source"
        if "sha256" in src and (not isinstance(src["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", src["sha256"])):
            return "decision hash"
    except (KeyError, ValueError, TypeError, AttributeError):
        return "malformed decision"
    return None


class DecisionNotApplicable(ValueError):
    """An identified, readable announcement contains no applicable no-pay decision."""


def parse_distribution_decision(body, code, full_name, frequency, url, today):
    """Only actual subject/section 1 decisions, never generic contract section 8."""
    p = distribution_url_parts(url, code)
    if p is None or not isinstance(full_name, str) or not full_name:
        raise ValueError("notice identity unavailable")
    articles = re.findall(r"<article\b[^>]*>(.*?)</article>", body.decode("utf-8", errors="strict"), re.S | re.I)
    if len(articles) != 1:
        raise ValueError("notice article missing or ambiguous")
    rows = Rows(); rows.feed(articles[0])
    subjects = [r[1] for r in rows.rows if len(r) == 2 and r[0] == "主旨"]
    if len(subjects) != 1:
        raise ValueError("notice subject missing")
    subject = subjects[0]
    identity = lambda x: _norm(x).replace("證券投資信託", "")
    if identity(full_name) not in identity(subject):
        raise ValueError("notice full fund name mismatched")
    facts = [r[i + 1] for r in rows.rows for i, c in enumerate(r[:-1]) if c == "事實發生日"]
    ann = datetime.datetime.strptime(p["date"], "%Y%m%d").date()
    if len(facts) != 1 or facts[0] != "%d/%02d/%02d" % (ann.year - 1911, ann.month, ann.day):
        raise ValueError("notice fact date mismatch")
    descriptions = [r[1] for r in rows.rows if len(r) == 2 and r[0] == "說明"]
    if len(descriptions) != 1:
        raise ValueError("notice description missing")
    first = re.search(r"^1[.．](.*?)2[.．]現金收益公布日期", descriptions[0])
    if first is None:
        raise ValueError("notice section 1 missing")
    decision = subject + first[1]
    if not re.search(r"評價結果(?:決定(?:本基金)?(?:本次將|當次收益)?(?:不予分配(?:收益)?|收益不予分配)|不進行收益分配之發放)", decision):
        raise DecisionNotApplicable("no explicit current-period decision")
    dates = set()
    for y, m, d in re.findall(r"(?<![0-9])([0-9]{3})年([0-9]{1,2})月([0-9]{1,2})日", decision):
        dates.add(datetime.date(int(y) + 1911, int(m), int(d)))
    for y, m, d in re.findall(r"(?<![0-9])([0-9]{3})/([0-9]{2})/([0-9]{2})(?![0-9])", decision):
        dates.add(datetime.date(int(y) + 1911, int(m), int(d)))
    if len(dates) != 1:
        raise ValueError("valuation date missing or ambiguous")
    val = dates.pop()
    months = {"月配": 1, "雙月配": 2, "季配": 3, "半年配": 6, "年配": 12}.get(frequency)
    if months is None or not val <= ann <= today or ann > val + datetime.timedelta(days=31):
        raise ValueError("decision dates/frequency invalid")
    import calendar
    month_index = val.year * 12 + val.month - 1 + months
    year, month = divmod(month_index, 12); month += 1
    next_val = datetime.date(year, month, min(val.day, calendar.monthrange(year, month)[1]))
    until = min(next_val - datetime.timedelta(days=1), datetime.date(val.year + 1, 9, 29))
    record = {"status": "no_distribution_this_period", "code": code, "valuation_date": val.isoformat(),
              "announced_date": ann.isoformat(), "valid_until": until.isoformat(),
              "source": {"name": "TWSE ETFortune 官方收益分配決議", "url": url, "sha256": hashlib.sha256(body).hexdigest()}}
    if distribution_status_problem(code, record):
        raise ValueError("decision invalid")
    if today > until:
        raise DecisionNotApplicable("decision expired")
    return record


def recover_distribution_decisions(etfs, info_map, state, statement, today, now_ts, get=None):
    """Two index pages + at most four queued documents, six requests/run, no retry.
    Cursor advances by actual page length (the source ignores requested max/fund).
    All persistent state remains numeric maps under the existing daily contract.
    """
    import html, math
    get = get or _get
    names = {e["code"]: e.get("name", "") for e in etfs if isinstance(e.get("code"), str) and not e["code"].endswith(EXCLUDED_SUFFIX)}
    fields = ("distribution_scan", "distribution_queue_date", "distribution_queue_company", "distribution_queue_seq",
              "distribution_checked", "distribution_checked_date", "distribution_checked_seq")
    maps = {}
    for field in fields:
        raw = state.get(field)
        clean = {}
        for key, value in (raw.items() if isinstance(raw, dict) else []):
            if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                continue
            cap = 2**48 - 1 if field == "distribution_scan" and key == "head" else 99999999
            if field != "distribution_checked" and (value != int(value) or value > cap):
                continue
            if field.endswith("_date"):
                try: datetime.datetime.strptime(str(int(value)), "%Y%m%d")
                except ValueError: continue
            clean[key] = value
        maps[field] = clean
        state[field] = maps[field]
    cursor = maps["distribution_scan"].get("offset", 0)
    cursor = int(cursor) if isinstance(cursor, (int, float)) and not isinstance(cursor, bool) and 0 <= cursor <= 100000 else 0
    attempts, adopted = [], []
    def read(url):
        try:
            body = get(url)
            if not isinstance(body, bytes) or len(body) > 2_000_000:
                raise ValueError("invalid response body")
            attempts.append({"url": url, "status": "received", "sha256": hashlib.sha256(body).hexdigest()})
            return body
        except Exception as ex:
            attempts.append({"url": url, "status": "failed", "reason": type(ex).__name__})
            return None
    head_count = 0
    for page in range(2):
        offset = 0 if page == 0 else max(head_count, cursor)
        url = BASE + "/zh/ETFortune/announcementList?" + urllib.parse.urlencode({"offset": offset, "type": "distribution"})
        body = read(url)
        if body is None: break
        links = []
        try:
            text = body.decode("utf-8", errors="strict")
        except UnicodeError:
            attempts[-1].update(status="failed", reason="UnicodeError")
            break
        for href in re.findall(r'href=[\"\']([^\"\']+)[\"\']', text, re.I):
            target = urllib.parse.urljoin(BASE, html.unescape(href))
            p = distribution_url_parts(target)
            if p and target not in links: links.append(target)
        if not links:
            cursor = head_count
            break
        if page == 0:
            head_count = len(links)
            # A new head restarts the backlog immediately behind it, so a burst
            # of >one page of new notices cannot fall between head and old cursor.
            fingerprint = int(hashlib.sha256("\n".join(links).encode()).hexdigest()[:12], 16)
            if maps["distribution_scan"].get("head") != fingerprint:
                cursor = head_count
            maps["distribution_scan"]["head"] = fingerprint
        for target in links:
            p = distribution_url_parts(target); code = p["fund"]
            if code not in names or p["date"] > today.strftime("%Y%m%d"): continue
            date, seq = int(p["date"]), int(p["seq"])
            if (maps["distribution_queue_date"].get(code, 0), maps["distribution_queue_seq"].get(code, 0)) <= (date, seq):
                maps["distribution_queue_date"][code] = date
                maps["distribution_queue_seq"][code] = seq
                maps["distribution_queue_company"][code] = int(p["company"][1:])
        if page == 1:
            cursor = offset + len(links)
    maps["distribution_scan"]["offset"] = cursor
    due = [c for c in maps["distribution_queue_date"] if c in names and
           1 <= maps["distribution_queue_seq"].get(c, 0) <= 999999 and
           1 <= maps["distribution_queue_company"].get(c, 0) <= 99999 and
           (maps["distribution_checked_date"].get(c), maps["distribution_checked_seq"].get(c)) !=
           (maps["distribution_queue_date"][c], maps["distribution_queue_seq"].get(c))]
    for code in sorted(due, key=lambda c: (maps["distribution_checked"].get(c, 0), c))[:4]:
        try:
            date = str(int(maps["distribution_queue_date"][code])); seq = str(int(maps["distribution_queue_seq"][code]))
            company = "A%05d" % maps["distribution_queue_company"][code]
        except (ValueError, TypeError, KeyError): continue
        url = BASE + "/zh/ETFortune/announcement?" + urllib.parse.urlencode({"company": company, "date": date, "seq": seq, "fund": code, "type": "distribution"})
        if distribution_url_parts(url, code) is None: continue
        maps["distribution_checked"][code] = now_ts
        body = read(url)
        if body is None: continue                 # retry in a later fair rotation, no immediate help request
        try:
            meta = info_map.get(code) or {}
            full_name, frequency = None, known_policy(code, meta)
            if statement:
                s, _, detail = sitca_policy(code, names[code], statement, today)
                if s == "verified": full_name = detail["full_name"]
            if full_name is None and policy_source_problem(code, meta) is None:
                full_name = meta["policy_source"]["full_name"]
            if not full_name or frequency is None:
                continue                         # identity not obtained; leave queued for a later round
            record = parse_distribution_decision(body, code, full_name, frequency, url, today)
        except DecisionNotApplicable:
            record = None
        except (ValueError, TypeError, KeyError, UnicodeError):
            continue                             # malformed/temporary source is not a completed judgement
        maps["distribution_checked_date"][code] = int(date)
        maps["distribution_checked_seq"][code] = int(seq)
        if record is not None:
            old = meta.get("distribution_status")
            if distribution_status_problem(code, old) is None and old["valuation_date"] > record["valuation_date"]:
                continue
            meta = dict(meta); meta["distribution_status"] = record; info_map[code] = meta
            adopted.append(code)
    return {"adopted": adopted, "attempts": attempts, "offset": cursor, "queued": len(due)}


# ── 10/26 補修：逾期待公告的 TWSE 歷史配息清單查證（日曆只含未來除息，已除息的公告會漏掉）──
# 既有 TWSE per-ETF 端點（fetch_dividend_calendar.fetch_twse_per_etf 同一路徑），只查 pending_since 之後；主機限定 www.twse.com.tw、不跟轉址。
TWSE_DIV_LIST = BASE + "/rwd/zh/ETFortune/dividendList"
HISTORY_SOURCE = "TWSE ETFortune 配息清單（dividendList，逐檔歷史）"
_HIST_HEADER = ["證券代號", "證券簡稱", "除息交易日", "收益分配基準日", "收益分配發放日"]
_HIST_HEADER_FULL = _HIST_HEADER + ["收益分配金額(每1受益權益單位)"]     # R1：第六欄＝金額＋官方單位文字（去空白後精確比對）


def history_url_ok(code, url, pending_since):
    """R1（F1）：系統實際寫出的歷史清單網址格式——https、精確 www.twse.com.tw、無帳密／port／fragment、精確 dividendList 路徑、
    查詢鍵恰為 stkNo＝同代號與 startDate＝pending_since 次日（各一次，無其他鍵）。"""
    try:
        sp = urllib.parse.urlsplit(url) if isinstance(url, str) else None
        if sp is None or sp.scheme != "https" or sp.hostname != "www.twse.com.tw" or sp.netloc != "www.twse.com.tw" \
                or sp.username or sp.password or sp.port or sp.fragment or sp.path != "/rwd/zh/ETFortune/dividendList":
            return False
        q = urllib.parse.parse_qsl(sp.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return False
    want = {"stkNo": code, "startDate": (pending_since + datetime.timedelta(days=1)).strftime("%Y%m%d")}
    return len(q) == 2 and dict(q) == want


def _roc(text):
    m = re.fullmatch(r"(\d{3})年(\d{2})月(\d{2})日", str(text).strip())
    if not m:
        raise ValueError("ROC date invalid: %r" % text)
    return datetime.date(int(m[1]) + 1911, int(m[2]), int(m[3]))


def parse_dividend_list(body, code):
    """TWSE dividendList 頁 → 同代號列 [(除息日, 金額, 發放日)]。表頭必須是配息清單；其他基金的列忽略；
    除息日或金額不能解析、金額非正數的同代號列 → 記為壞列（不採用）。回傳 (good_rows, bad_rows)。"""
    import html as _html
    text = body.decode("utf-8", errors="strict")
    cells_of = lambda tr: [re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                           for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
    # R1（F2）：表頭與資料列必須在同一個 table；前六欄的語意與位置（含第六欄金額與官方單位文字）逐一核對，只做空白正規化。
    norm = lambda s: re.sub(r"\s+", "", s)
    tables, stray = [], 0
    for tb in re.findall(r"<table\b[^>]*>.*?</table>", text, re.S | re.I):
        rows = [cells_of(tr) for tr in re.findall(r"<tr\b[^>]*>.*?</tr>", tb, re.S | re.I)]
        heads = [i for i, r in enumerate(rows) if [norm(c) for c in r[:6]] == _HIST_HEADER_FULL]
        if heads:
            tables.append(rows[heads[0] + 1:])
        else:
            stray += sum(1 for r in rows if r and r[0] == code)       # 同代號資料列落在未確認表頭的 table
    if len(tables) != 1 or stray:
        raise ValueError("TWSE dividendList table header not confirmed (tables=%d, stray rows=%d)" % (len(tables), stray))
    rows = tables[0]
    good, bad = [], []
    for r in rows:
        if len(r) < 6 or r[0] != code:
            continue
        try:
            ex = _roc(r[2]); pay = _roc(r[4]) if r[4] else None
            amt = float(r[5].replace(",", ""))
            if not (amt > 0) or amt != amt or amt == float("inf"):
                raise ValueError("amount not positive")
        except ValueError as e:
            bad.append({"row": r[:6], "why": str(e)})
            continue
        good.append({"ex_dividend_date": ex, "amount": amt, "pay_date": pay})
    return good, bad


def twse_history_announcement(code, since, get=None):
    """逐檔歷史查證。回傳 (status, detail)：announced（同代號、除息日在 since 之後、正額）／none（已讀到清單但無可採列）／
    error（讀取失敗、403、逾時、轉址、不是配息清單頁 → 暫時失敗，下輪重試，不算查無）。不推估、不改金額／殖利率。"""
    if not isinstance(code, str) or not re.fullmatch(r"[0-9A-Z]{4,8}", code):
        return "none", "代號不合法"
    get = get or _get
    url = TWSE_DIV_LIST + "?" + urllib.parse.urlencode({"stkNo": code, "startDate": (since + datetime.timedelta(days=1)).strftime("%Y%m%d")})
    try:
        body = get(url)
    except Exception as ex:
        return "error", "TWSE 歷史配息清單讀取失敗（%s），下輪重試" % type(ex).__name__
    try:
        good, bad = parse_dividend_list(body, code)
    except (ValueError, UnicodeError) as ex:
        return "error", "TWSE 歷史配息清單內容不可用（%s），下輪重試" % str(ex)[:60]
    after = sorted((g for g in good if g["ex_dividend_date"] > since), key=lambda g: g["ex_dividend_date"])
    if not after:
        why = "；另有 %d 列無效（%s）" % (len(bad), bad[0]["why"]) if bad else ""
        return "none", "TWSE 歷史配息清單 %s 之後沒有同檔已公告正額%s" % (since, why)
    g = after[0]
    return "announced", {"ex_dividend_date": g["ex_dividend_date"].isoformat(), "amount": g["amount"], "amount_source": "TWSE",
                         "pay_date": g["pay_date"].isoformat() if g["pay_date"] else None, "url": url,
                         "sha256": hashlib.sha256(body).hexdigest()}
