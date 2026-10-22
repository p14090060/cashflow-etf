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
        if meta.get("frequency") not in UNKNOWN:
            # Previously verified/static data was not yet propagated to market.
            entry.pop("div_freq", None)
            entry["div_frequency"] = meta["frequency"]
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


# ── D-071：全體未知配息政策的自動查證（TWSE 公告＋投信投顧公會 SITCA ETF 基本資料表）──
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


def policy_source_problem(code, meta):
    """D-071 policy_source（SITCA 採用紀錄）讀回核對；None＝有效、'absent'＝沒有該欄位。壞型別不崩潰。"""
    try:
        if not isinstance(meta, dict):
            return "invalid static record"
        ps = meta.get("policy_source")
        if ps is None:
            return "absent"
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
    """已知政策或 None。policy_source 存在但無效 → 視為未知、重新查證（不沿用壞證據）。"""
    if not isinstance(meta, dict) or meta.get("frequency") in UNKNOWN:
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
    if source is not None:
        meta["policy_source"] = source
    info_map[code] = meta
    return meta


def recover_policies(etfs, info_map, last_try, today, now_iso, twse_resolver=None, sitca_get=None, limit=4):
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
    kinds = {c: (k, known, sf) for c, k, known, sf in pending}
    for i, code in enumerate(sorted(kinds, key=lambda c: (last_try.get(c, 0), c))):
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
        else:
            status[code] = CONFLICT if kind == "identity_conflict" else NO_RESULT
            detail[code] = "%s；TWSE 公告無明確政策（%s）" % (detail.get(code) or "SITCA 無明確分類", r.get("reason", ""))
            completed.append(code)
    return {"status": status, "detail": detail, "checked": checked, "adopted": adopted, "completed": completed,
            "twse_tried": twse_tried, "conflicts_known": conflicts_known,
            "sitca": {"ok": st is not None, "report_month": st and st["report_month"], "updated": st and st["updated"],
                      "sha256": st and st["sha256"], "attempts": sitca_attempts}}
