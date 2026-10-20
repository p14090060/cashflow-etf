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
