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
import urllib.parse
import urllib.request

HOST = "https://www.twse.com.tw"
MONTH_FIELDS = ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數", "註記"]
SPLIT_FIELDS = ["停止買賣日期", "分割(反分割)", "恢復買賣日期", "分割(反分割)比率(註1)"]


class Unusable(ValueError):
    pass


def _number(value, integer=False):
    if not isinstance(value, str) or not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value.strip()):
        raise Unusable("官方數值格式錯誤")
    n = Decimal(value.replace(",", "").strip())
    if not n.is_finite() or not math.isfinite(float(n)) or n < 0 or (integer and n != n.to_integral_value()):
        raise Unusable("官方數值無效")
    return int(n) if integer else float(n)


def parse_month(raw, code, name, month):
    try:
        d = json.loads(raw)
    except (ValueError, UnicodeError, TypeError) as ex:
        raise Unusable("月報不是JSON") from ex
    title = f"{month.year - 1911}年{month.month:02d}月 {code} {name} 各日成交資訊"
    if not isinstance(d, dict) or d.get("stat") != "OK" or d.get("date") != month.strftime("%Y%m01") or d.get("title") != title or d.get("fields") != MONTH_FIELDS:
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


def verify_no_splits(raw, code, name):
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
    if len(tables) != 1 or tables[0][1:] != [["查無資料"]]:
        raise Unusable("分割紀錄存在或分割表未確認；不冒算調整後歷史")
    payments = [t for t in p.tables if t and t[0] == ["收益分配發放日", "配息（每1受益權益單位）"]]
    if len(payments) != 1:
        raise Unusable("商品頁配息摘要不能確認")
    return payments[0][1:]


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


def build_history(months, profile, dividends, code, name, today, official_day, official_price):
    import pandas as pd
    import official_frequency as policy
    if not re.fullmatch(r"\d{4,6}[A-Z]?", code) or not isinstance(name, str) or not name:
        raise Unusable("ETF身分無效")
    if not isinstance(today, dt.date) or not isinstance(official_day, dt.date) or not 0 <= (today - official_day).days <= 15:
        raise Unusable("官方末日錯誤／過期")
    payments = verify_no_splits(profile, code, name)
    start = today - dt.timedelta(days=365)
    expected = month_starts(start, official_day)
    if set(months) != set(expected):
        raise Unusable("一年月報不完整")
    rows, skipped = [], []
    for month in expected:
        rr, ss = parse_month(months[month], code, name, month); rows.extend(rr); skipped.extend(ss)
    if any(d > today for d, _, _ in rows) or any(dt.date.fromisoformat(x["date"]) > today for x in skipped):
        raise Unusable("官方月報含未來交易日")
    win = [(d, c, v) for d, c, v in rows if start <= d <= official_day]
    dates = [r[0] for r in win]
    if len(win) < 5 or dates != sorted(set(dates)) or dates[0] > start + dt.timedelta(days=15) or dates[-1] != official_day:
        raise Unusable("一年日線涵蓋不足／未到官方末日")
    if any((b - a).days > 15 for a, b in zip(dates, dates[1:])):
        raise Unusable("一年日線中間缺口超過15天")
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
    adj, used_events = cash_adjust(win, events)
    dividends_by_day = {x["ex_dividend_date"]: x["amount"] for x in in_window_events}
    index = pd.DatetimeIndex(dates).tz_localize("Asia/Taipei")
    hist = pd.DataFrame({"Close": [r[1] for r in win], "Volume": [r[2] for r in win], "Adj Close": adj,
                         "Dividends": [dividends_by_day.get(day, 0.) for day in dates]}, index=index)
    hist.attrs["twse_history"] = {"source": "TWSE_STOCK_DAY+ETFortune", "code": code, "first": dates[0].isoformat(), "last": dates[-1].isoformat(), "rows": len(win), "cash_events": used_events, "missing_close_rows": skipped}
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


def fetch_history(code, name, today, official_day, official_price, get=None):
    """At most 15 existing official GETs, one pass; any failure stops this fallback."""
    if type(today) is not dt.date or type(official_day) is not dt.date or not 0 <= (today - official_day).days <= 15:
        raise Unusable("官方末日錯誤／過期")
    if isinstance(official_price, bool) or not isinstance(official_price, (int, float)) or not math.isfinite(official_price) or official_price <= 0:
        raise Unusable("本輪官方末價無效")
    calls, bodies = [], {}
    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    def request(path, params=None):
        url = HOST + path + (("?" + urllib.parse.urlencode(params)) if params else "")
        if len(calls) >= 15:
            raise Unusable("官方歷史查證額度已滿")
        calls.append(url)
        if get is None:
            with opener.open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=12) as r:
                raw = r.read(2_000_001)
        else:
            raw = get(url)
        if not isinstance(raw, bytes) or not raw or len(raw) > 2_000_000:
            raise Unusable("官方回應空白或過大")
        bodies[url] = hashlib.sha256(raw).hexdigest()
        if get is None:
            time.sleep(.4)
        return raw
    if not re.fullmatch(r"\d{4,6}[A-Z]?", code):
        raise Unusable("代號無效")
    start = today - dt.timedelta(days=365)
    profile = request("/zh/ETFortune/etfInfo/" + code)
    verify_no_splits(profile, code, name)
    dividends = request("/rwd/zh/ETFortune/dividendList", {"stkNo": code, "startDate": start.strftime("%Y%m%d")})
    months = {m: request("/exchangeReport/STOCK_DAY", {"response": "json", "date": m.strftime("%Y%m01"), "stockNo": code}) for m in month_starts(start, official_day)}
    hist = build_history(months, profile, dividends, code, name, today, official_day, official_price)
    hist.attrs["twse_history"].update(requests=len(calls), bodies=bodies)
    return hist
