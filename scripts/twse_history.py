"""Bounded official daily-history fallback for listed, mature ETFs without split records.

Price/volume come from STOCK_DAY. Cash adjustments use the ETF's official dividend
history; never label unadjusted Close as Adj Close. Any unsupported action or incomplete
source rejects the fallback. This module does not publish data or send notifications.
"""
import datetime as dt
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import hashlib
import json
import math
import re
import ssl
import time
import http.client
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://www.twse.com.tw"
MONTH_FIELDS = ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數", "註記"]
SPLIT_FIELDS = ["停止買賣日期", "分割(反分割)", "恢復買賣日期", "分割(反分割)比率(註1)"]


class Unusable(ValueError):
    pass


class FetchFailed(Unusable):
    """官方歷史請求／驗證在某一階段失敗（仍是 Unusable：呼叫端照舊拒用）。diag 只含可安全寫進 log 的欄位：
    stage（商品頁／配息清單／月報YYYY-MM／驗證）、kind（network／http_status／response／budget／rejected）、
    url（本程式自己組的官方請求網址）、status（HTTP 狀態或 None）、location（僅 scheme://host/path）、
    location_host_official、reason。不跟轉址、不重試。"""
    def __init__(self, stage, kind, url=None, status=None, location=None, official=None, reason=""):
        self.diag = {"stage": stage, "kind": kind, "url": url, "status": status,
                     "location": location, "location_host_official": official, "reason": reason}
        bits = ["階段=%s" % stage, "類別=%s" % kind]
        if status is not None:
            bits.append("HTTP %s" % status)
        if kind == "http_status" and 300 <= (status or 0) < 400:
            bits.append("Location=%s" % (location or "（無）"))
            if location and not official:
                bits.append("非官方主機")
        if reason:
            bits.append(reason)
        if url:
            bits.append("URL=%s" % url)
        super().__init__("；".join(bits))


_SAFE_PATH = re.compile(r"[^A-Za-z0-9/._~%\-]")


def safe_location(value, base):
    """Location 只留 scheme://host[:port]/path：去帳密、query、fragment，非 http(s) 只標 scheme；
    path 只保留 URL 安全字元並截 120 字。回 (摘要, 是否為官方主機)；沒有 Location → (None, None)。"""
    if value is None:
        return None, None
    try:
        u = urllib.parse.urlsplit(urllib.parse.urljoin(base, str(value).strip()))
        host, port = (u.hostname or ""), u.port
    except ValueError:
        return "（無法解析）", False
    scheme = u.scheme.lower()
    if scheme not in ("http", "https"):
        return "（非 http(s)：%s）" % _SAFE_PATH.sub("?", scheme)[:12], False
    host = re.sub(r"[^a-z0-9.\-]", "?", host.lower())[:80]
    path = _SAFE_PATH.sub("?", u.path or "/")[:120]
    official = scheme == "https" and host == "www.twse.com.tw" and port in (None, 443)
    return "%s://%s%s%s" % (scheme, host, ":%d" % port if port else "", path), official


def _number(value, integer=False):
    if not isinstance(value, str) or not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value.strip()):
        raise Unusable("官方數值格式錯誤")
    n = Decimal(value.replace(",", "").strip())
    if not n.is_finite() or not math.isfinite(float(n)) or n < 0 or (integer and n != n.to_integral_value()):
        raise Unusable("官方數值無效")
    return int(n) if integer else float(n)


def parse_month(raw, code, name, month, pad_title=False):
    try:
        d = json.loads(raw)
    except (ValueError, UnicodeError, TypeError) as ex:
        raise Unusable("月報不是JSON") from ex
    title = f"{month.year - 1911}年{month.month:02d}月 {code} {name} 各日成交資訊"
    got = d.get("title") if isinstance(d, dict) else None
    if pad_title and isinstance(got, str):
        # 已核拆分重建路徑專用：官方名稱欄以半形空白補寬（「富邦NASDAQ       各日」）。只把連續半形空白
        # 收成一格後逐字比對，代號／名稱／年月仍須完全相同；不做模糊包含。一般路徑行為不變。
        got = re.sub(r" +", " ", got)
    if not isinstance(d, dict) or d.get("stat") != "OK" or d.get("date") != month.strftime("%Y%m01") or got != title or d.get("fields") != MONTH_FIELDS:
        raise Unusable("月報身分／日期／表頭不符")
    if not isinstance(d.get("data"), list) or not d["data"]:
        raise Unusable("月報沒有資料列")
    rows, seen, skipped = [], set(), []
    previous = None
    for r in d["data"]:
        if not isinstance(r, list) or len(r) != len(MONTH_FIELDS):
            raise Unusable("月報資料列長度錯誤")
        try:
            year, mm, day = map(int, r[0].split("/"))
            date = dt.date(year + 1911, mm, day)
        except (ValueError, TypeError, AttributeError) as ex:
            raise Unusable("月報交易日錯誤") from ex
        if (date.year, date.month) != (month.year, month.month) or date in seen or (previous and date <= previous):
            raise Unusable("月報交易日重複／倒序／跨月")
        seen.add(date); previous = date
        volume = _number(r[1], True)
        if r[6] == "--":
            skipped.append({"date": date.isoformat(), "volume": volume})
            continue
        close = _number(r[6])
        if close <= 0:
            raise Unusable("官方收盤必須正值")
        rows.append((date, close, volume))
    return rows, skipped


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.table is not None:
                raise Unusable("巢狀表格不支援")
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("th", "td") and self.row is not None:
            self.cell = []

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None:
            self.row.append(re.sub(r"\s+", "", "".join(self.cell))); self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row); self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table); self.table = None


def _profile_tables(raw, code, name):
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    except UnicodeError as ex:
        raise Unusable("官方商品頁編碼錯誤") from ex
    identity = re.findall(r'<b\s+id=["\']stkNo["\']\s*>\s*([0-9A-Z]+)\s*</b>', text)
    info = re.search(r'<div class="etf-info">(.*?)<div class="etf-result">', text, re.S)
    if identity != [code] or not info or name not in re.sub(r"<[^>]*>", "", info[1]):
        raise Unusable("官方商品頁身分不符")
    p = _Tables(); p.feed(text)
    tables = [t for t in p.tables if t and t[0] == SPLIT_FIELDS]
    if len(tables) != 1:
        raise Unusable("分割紀錄存在或分割表未確認；不冒算調整後歷史")
    payments = [t for t in p.tables if t and t[0] == ["收益分配發放日", "配息（每1受益權益單位）"]]
    if len(payments) != 1:
        raise Unusable("商品頁配息摘要不能確認")
    return tables[0][1:], payments[0][1:]


def verify_no_splits(raw, code, name):
    splits, payments = _profile_tables(raw, code, name)
    if splits != [["查無資料"]]:
        raise Unusable("分割紀錄存在或分割表未確認；不冒算調整後歷史")
    return payments


def split_event(code):
    """只接受 price_unit.EVENTS 內已核官方拆分（目前僅 00662 1拆5）；其他代號／種類 → None。"""
    import price_unit
    ev = price_unit.EVENTS.get(code)
    if not isinstance(ev, dict) or ev.get("kind") != "split":
        return None
    ratio = ev.get("ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, int) or ratio < 2:
        raise Unusable("已核事件比率無效")
    halt, resume = dt.date.fromisoformat(ev["halt_from"]), dt.date.fromisoformat(ev["resume"])
    if not halt < resume:
        raise Unusable("已核事件停牌／復牌日期衝突")
    return {"code": code, "ratio": ratio, "halt_from": halt, "resume": resume}


def pinned_event(event, code):
    """R1：呼叫者傳入的拆分事件必須與 price_unit.EVENTS 內嵌已核事件逐欄完全一致（代號／比率／停牌／復牌、型別）。
    不靠 1.8 倍斷點閾值認比率（1:4、1:3 會落在閾值內）；不一致一律拒用。"""
    try:
        pinned = split_event(code)
    except (KeyError, TypeError, ValueError) as ex:
        raise Unusable("已核事件內容無效") from ex
    if pinned is None:
        raise Unusable("代號沒有已核拆分事件")
    if (not isinstance(event, dict) or set(event) != set(pinned)
            or type(event.get("ratio")) is not int or type(event.get("code")) is not str
            or type(event.get("halt_from")) is not dt.date or type(event.get("resume")) is not dt.date
            or event != pinned):
        raise Unusable("拆分事件與內嵌已核事件不一致（代號／比率／日期）")
    return pinned


def verify_split_profile(raw, code, name, event):
    """商品頁身分／配息摘要照原檢查。分割表「查無資料」不能當「沒有分割」的證明，也不否定已核公告；
    表內若有任何列，本程式不認得其格式 → 拒用（不猜是不是同一事件）。"""
    if not isinstance(event, dict) or event.get("code") != code:
        raise Unusable("已核事件與代號不符")
    pinned_event(event, code)
    splits, payments = _profile_tables(raw, code, name)
    if splits != [["查無資料"]]:
        raise Unusable("商品頁分割表有內容，無法與已核事件比對；不重建")
    return payments


def split_normalize(win, skipped, event, official_day):
    """win：(日期, 官方原始收盤, 原始成交股數)，已排序。拆分前收盤 ÷ 已核比率；成交量保持官方原始股數。
    必須：停牌期間沒有任何列、復牌日有有效收盤、原始序列唯一一個 1.8 倍斷點恰在復牌日、調整後無斷點。"""
    import price_unit
    event = pinned_event(event, event.get("code") if isinstance(event, dict) else None)
    halt, resume, ratio = event["halt_from"], event["resume"], event["ratio"]
    dates = [d for d, _, _ in win]
    if not dates or not dates[0] < halt or official_day < resume:
        raise Unusable("已核拆分不在一年視窗內")
    if any(halt <= d < resume for d in dates) or any(halt <= dt.date.fromisoformat(x["date"]) < resume for x in skipped):
        raise Unusable("停牌期間出現交易列，與已核停牌不符")
    if resume not in dates:
        raise Unusable("復牌日沒有有效官方收盤")
    jumps = [b[0] for a, b in zip(win, win[1:]) if price_unit.jump(a[1], b[1])]
    if jumps != [resume]:
        raise Unusable("原始官方序列單位斷點%s與已核復牌日%s不符（混尺度／重複調整／日期錯）"
                       % ([d.isoformat() for d in jumps], resume.isoformat()))
    out = [(d, float(Decimal(str(c)) / ratio) if d < resume else c, v) for d, c, v in win]
    if any(price_unit.jump(a[1], b[1]) for a, b in zip(out, out[1:])):
        raise Unusable("依已核比率調整後仍有單位斷點；比率不符")
    return out


def cash_adjust(rows, events):
    """Construct separate Adj Close using backward cash factors; Close stays untouched.

    The caller must first verify the official no-split table. Unsupported splits
    are rejected rather than guessed. Cash factors match normal Yahoo semantics.
    """
    dates = [r[0] for r in rows]
    adj = [Decimal(str(c)) for _, c, _ in rows]
    used = []
    if len({x["ex_dividend_date"] for x in events}) != len(events):
        raise Unusable("配息事件重複／衝突")
    for event in sorted(events, key=lambda x: x["ex_dividend_date"]):
        ex = event["ex_dividend_date"]
        if ex not in dates:
            raise Unusable("除息日沒有有效官方收盤")
        before = [i for i, d in enumerate(dates) if d < ex]
        if not before:
            raise Unusable("沒有除息前價")
        i = before[-1]
        if (ex - dates[i]).days > 15:
            raise Unusable("除息前價日期缺口過長")
        value = event.get("amount")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise Unusable("現金分配金額無效")
        cash = Decimal(str(value)); previous = Decimal(str(rows[i][1]))
        if cash <= 0 or cash >= previous:
            raise Unusable("現金分配金額與除息前價不符")
        factor = (previous - cash) / previous
        for j in before:
            adj[j] *= factor
        used.append({"date": ex.isoformat(), "cash": float(cash), "prior_date": dates[i].isoformat(), "prior_close": float(previous), "factor": str(factor)})
    return [float(x) for x in adj], used


def build_history(months, profile, dividends, code, name, today, official_day, official_price, split=None):
    import pandas as pd
    import official_frequency as policy
    if not re.fullmatch(r"\d{4,6}[A-Z]?", code) or not isinstance(name, str) or not name:
        raise Unusable("ETF身分無效")
    if split is not None:
        split = pinned_event(split, code)
    if not isinstance(today, dt.date) or not isinstance(official_day, dt.date) or not 0 <= (today - official_day).days <= 15:
        raise Unusable("官方末日錯誤／過期")
    payments = verify_split_profile(profile, code, name, split) if split else verify_no_splits(profile, code, name)
    start = today - dt.timedelta(days=365)
    expected = month_starts(start, official_day)
    if set(months) != set(expected):
        raise Unusable("一年月報不完整")
    rows, skipped = [], []
    for month in expected:
        try:
            rr, ss = parse_month(months[month], code, name, month, pad_title=bool(split))
        except Unusable as ex:
            raise Unusable("月報%s：%s" % (month.strftime("%Y-%m"), ex)) from ex
        rows.extend(rr); skipped.extend(ss)
    if any(d > today for d, _, _ in rows) or any(dt.date.fromisoformat(x["date"]) > today for x in skipped):
        raise Unusable("官方月報含未來交易日")
    win = [(d, c, v) for d, c, v in rows if start <= d <= official_day]
    dates = [r[0] for r in win]
    if len(win) < 5 or dates != sorted(set(dates)) or dates[0] > start + dt.timedelta(days=15) or dates[-1] != official_day:
        raise Unusable("一年日線涵蓋不足／未到官方末日")
    if any((b - a).days > 15 for a, b in zip(dates, dates[1:])):
        raise Unusable("一年日線中間缺口超過15天")
    raw_win = win
    if split:
        win = split_normalize(win, skipped, split, official_day)
    if isinstance(official_price, bool) or not isinstance(official_price, (int, float)) or not math.isfinite(official_price) or official_price <= 0 or win[-1][1] != official_price:
        raise Unusable("歷史末價不等於本輪已驗官方收盤")
    try:
        events, bad = policy.parse_dividend_list(dividends, code)
    except (ValueError, UnicodeError) as ex:
        raise Unusable("官方配息歷史不能確認") from ex
    if bad:
        raise Unusable("官方配息歷史含無效列")
    # STOCK_DAY marks an ex-adjustment with X. It also uses X when the preceding
    # trading report has no close (e.g. 2026-08-31, 7 odd-lot shares); that is not
    # a dividend. Require all other X dates to be accounted for by cash events.
    reported, marked = {}, set()
    for month in expected:
        for row in json.loads(months[month])["data"]:
            y, mm, dd = map(int, row[0].split("/")); date = dt.date(y + 1911, mm, dd)
            reported[date] = row[6]
            if str(row[7]).strip().startswith("X"):
                marked.add(date)
    event_dates = {x["ex_dividend_date"] for x in events if dates[0] < x["ex_dividend_date"] <= official_day}
    for date in marked:
        if not dates[0] < date <= official_day:
            continue
        prior = max((d for d in reported if d < date), default=None)
        if prior is not None and reported[prior] != "--" and date not in event_dates:
            raise Unusable("月報調整日沒有對應的官方分配事件")
    if not event_dates <= marked:
        raise Unusable("官方分配事件與月報調整日不一致")
    for row in payments:
        if row == ["查無資料"]:
            continue
        if split and row == ["尚無配息資料"] and len(payments) == 1 and not events:
            continue                    # 拆分重建路徑：商品頁「尚無配息資料」且官方配息清單也是空的才放行（一致）
        try:
            if len(row) != 2:
                raise ValueError("payment columns")
            pay = dt.datetime.strptime(row[0], "%Y/%m/%d").date()
            cash = _number(row[1])
        except (ValueError, TypeError) as ex:
            raise Unusable("商品頁配息摘要格式無效") from ex
        if start <= pay <= today and not any(x["pay_date"] == pay and x["amount"] == cash for x in events):
            raise Unusable("官方配息歷史與商品頁摘要不一致")
    in_window_events = [x for x in events if dates[0] <= x["ex_dividend_date"] <= official_day]
    events = sorted((x for x in in_window_events if dates[0] < x["ex_dividend_date"]), key=lambda x: x["ex_dividend_date"])
    if split and any(x["ex_dividend_date"] < split["resume"] for x in in_window_events):
        raise Unusable("拆分前現金分配的單位換算未支援；不重建")
    adj, used_events = cash_adjust(win, events)
    dividends_by_day = {x["ex_dividend_date"]: x["amount"] for x in in_window_events}
    index = pd.DatetimeIndex(dates).tz_localize("Asia/Taipei")
    hist = pd.DataFrame({"Close": [r[1] for r in win], "Volume": [r[2] for r in win], "Adj Close": adj,
                         "Dividends": [dividends_by_day.get(day, 0.) for day in dates]}, index=index)
    if split:
        # R2（PO 核准）：歷史量「比較基準」換成拆後等值股數（拆前原始股數×已核比率）；Volume 仍是官方原始股數。
        raw_vol = {d: v for d, _, v in raw_win}
        hist["Volume Equiv"] = [raw_vol[d] * split["ratio"] if d < split["resume"] else raw_vol[d] for d in dates]
    hist.attrs["twse_history"] = {"source": "TWSE_STOCK_DAY+ETFortune", "code": code, "first": dates[0].isoformat(), "last": dates[-1].isoformat(), "rows": len(win), "cash_events": used_events, "missing_close_rows": skipped}
    if split:
        pre = [(d, c) for d, c, _ in raw_win if d < split["resume"]]
        hist.attrs["twse_history"]["split"] = {
            "ratio": split["ratio"], "halt_from": split["halt_from"].isoformat(), "resume": split["resume"].isoformat(),
            "price": "拆分前官方收盤÷已核比率（同單位）", "volume": "官方原始成交股數，未依拆分調整",
            "volume_equiv": "比較基準：拆前原始股數×已核比率＝拆後等值股數；只用於均量／量比／熱度",
            "adjusted_rows": len(pre), "last_pre_raw": [pre[-1][0].isoformat(), pre[-1][1]] if pre else None}
    return hist


def month_starts(start, end):
    out = []; d = start.replace(day=1)
    while d <= end:
        out.append(d)
        d = dt.date(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1, 1)
    return out


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def fetch_history(code, name, today, official_day, official_price, get=None, split=None):
    """At most 15 existing official GETs, one pass; any failure stops this fallback."""
    if type(today) is not dt.date or type(official_day) is not dt.date or not 0 <= (today - official_day).days <= 15:
        raise Unusable("官方末日錯誤／過期")
    if isinstance(official_price, bool) or not isinstance(official_price, (int, float)) or not math.isfinite(official_price) or official_price <= 0:
        raise Unusable("本輪官方末價無效")
    calls, bodies = [], {}
    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    def request(stage, path, params=None):
        url = HOST + path + (("?" + urllib.parse.urlencode(params)) if params else "")
        if len(calls) >= 15:
            raise FetchFailed(stage, "budget", url, reason="官方歷史查證額度已滿")
        calls.append(url)
        try:
            if get is None:
                with opener.open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=12) as r:
                    raw = r.read(2_000_001)
            else:
                raw = get(url)
        except urllib.error.HTTPError as ex:      # NoRedirect：3xx 在此以 HTTPError 結束，不跟轉址
            loc, official = safe_location(ex.headers.get("Location") if ex.headers is not None else None, url)
            raise FetchFailed(stage, "http_status", url, ex.code, loc, official) from ex
        except (urllib.error.URLError, http.client.HTTPException, OSError) as ex:   # 逾時／DNS／TLS／連線中斷
            inner = getattr(ex, "reason", None)
            why = type(inner).__name__ if isinstance(inner, BaseException) else type(ex).__name__
            raise FetchFailed(stage, "network", url, reason=why) from ex
        if not isinstance(raw, bytes) or not raw or len(raw) > 2_000_000:
            raise FetchFailed(stage, "response", url, reason="官方回應空白或過大")
        bodies[url] = hashlib.sha256(raw).hexdigest()
        if get is None:
            time.sleep(.4)
        return raw
    if not re.fullmatch(r"\d{4,6}[A-Z]?", code):
        raise Unusable("代號無效")
    if split is not None:
        split = pinned_event(split, code)          # 錯事件在發出任何請求前就拒用
    start = today - dt.timedelta(days=365)
    profile_url = HOST + "/zh/ETFortune/etfInfo/" + code
    profile = request("商品頁", "/zh/ETFortune/etfInfo/" + code)
    try:
        if split:
            verify_split_profile(profile, code, name, split)
        else:
            verify_no_splits(profile, code, name)
    except FetchFailed:
        raise
    except Unusable as ex:
        raise FetchFailed("商品頁", "rejected", profile_url, reason=str(ex)) from ex
    dividends = request("配息清單", "/rwd/zh/ETFortune/dividendList", {"stkNo": code, "startDate": start.strftime("%Y%m%d")})
    months = {m: request("月報" + m.strftime("%Y-%m"), "/exchangeReport/STOCK_DAY", {"response": "json", "date": m.strftime("%Y%m01"), "stockNo": code})
              for m in month_starts(start, official_day)}
    try:
        hist = build_history(months, profile, dividends, code, name, today, official_day, official_price, split=split)
    except FetchFailed:
        raise
    except Unusable as ex:
        raise FetchFailed("驗證", "rejected", reason=str(ex)) from ex
    hist.attrs["twse_history"].update(requests=len(calls), bodies=bodies)
    return hist
