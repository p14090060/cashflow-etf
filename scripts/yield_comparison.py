"""scripts/yield_comparison.py
殖利率排行的比較資料（工具頁排行與 Detail 共用同一份 yield_basis）。

成熟基金：觀察日往前 12 個月、已到除息日且有確定正額的配息合計 ÷ 最新合法價格。
新上市：已公告金額平均 × 年配次數 ÷ 價格，最多取一年次數；可含未來正式公告，一律標估算。
這不是 yld／訊號的來源：不改 yld、yld_verified、signal。

來源只用既有官方兩支整批清單，一個 fetch 輪次合計最多 2 個請求（含失敗，不重試）；
MIS 與前端不查來源，只用已保存的分子配最新價格重算。
"""
import datetime as dt
import hashlib
import json
import math
import re
import ssl
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

import official_frequency
from json_safe import DataInvalid, YIELD_SOURCE_TPEX, YIELD_SOURCE_TWSE, check_yield_basis, yield_is_new, yield_window_start

FREQ_PER_YEAR = {"月配": 12, "雙月配": 6, "季配": 4, "半年配": 2, "年配": 1}
MAX_BASIS_AGE_DAYS = 14                # 來源連續失敗時沿用的上限：超過就不能再稱「近12月」
RECORD_DATE_MARGIN_DAYS = 31           # SPLIT_RECORDS 部分日期是月初約略值：只用來判定「窗口附近可能有變更」，不拿來換算
# 已核實的單位變更；只使用官方生效日，未核實的其他拆分仍不可比較。
# 0052：TWSE 2025/10/09時程與11/25結果公告；原文／SHA256保存在yield-0052-split/2026-11-08。
VERIFIED_UNIT_CHANGES = {"0052": [{
    "date": "2025-11-26", "ratio": "7",
    "source": "https://www.twse.com.tw/zh/ETFortune/announcement?company=A00010&date=20251009&fund=0052&seq=1&type=other"
              "#sha256=be8332864915d2ec9e6fba68efc3c7e8aff7e52448bc1b5082cacb9ec14d6e86",
}]}
TWSE_URL = "https://www.twse.com.tw/rwd/zh/ETFortune/dividendList"
TPEX_URL = "https://info.tpex.org.tw/api/etfExDiv"
_TWSE_HEADER = ["證券代號", "證券簡稱", "除息交易日", "收益分配基準日", "收益分配發放日", "收益分配金額(每1受益權益單位)"]
_ROC_RE = re.compile(r"(\d{2,3})年(\d{1,2})月(\d{1,2})日")
_AMOUNT_RE = re.compile(r"\d+(?:\.\d+)?")


class SourceInvalid(ValueError):
    """來源回應不是預期格式（改版、錯誤頁）。視同該來源本輪失敗。"""


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._row, self._cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.tables[-1].append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_twse_html(raw):
    parser = _TableParser()
    parser.feed(raw.decode("utf-8"))
    if len(parser.tables) != 1 or not parser.tables[0]:
        raise SourceInvalid("TWSE 配息清單表格數不符")
    table = parser.tables[0]
    if ["".join(c.split()) for c in table[0][:6]] != _TWSE_HEADER:
        raise SourceInvalid("TWSE 配息清單欄位不符")
    return [{"code": r[0], "name": r[1], "ex": r[2], "pay": r[4], "amount": r[5], "source": YIELD_SOURCE_TWSE}
            for r in table[1:] if len(r) >= 6]


def parse_tpex_json(raw):
    data = json.loads(raw)
    if not isinstance(data, list):
        raise SourceInvalid("TPEx 配息清單不是陣列")
    rows = []
    for r in data:
        if not isinstance(r, dict) or not {"stockNo", "stockName", "divDate", "inDate", "amount"} <= set(r):
            raise SourceInvalid("TPEx 配息清單欄位不符")
        rows.append({"code": r["stockNo"], "name": r["stockName"], "ex": r["divDate"], "pay": r["inDate"],
                     "amount": r["amount"], "source": YIELD_SOURCE_TPEX})
    return rows


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _default_read(req):
    import certifi
    opener = urllib.request.build_opener(
        _NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
    with opener.open(req, timeout=30) as r:
        return r.read()


window_start = yield_window_start


def fetch_sources(as_of, read=None):
    """兩個來源各一次（失敗不重試）。回傳 ({"twse": rows|None, "tpex": rows|None, 成功者另有 "<key>_sha256"}, 請求數)。"""
    read = read or _default_read
    start, end = window_start(as_of).strftime("%Y%m%d"), as_of.strftime("%Y%m%d")
    headers = {"User-Agent": "ETF-fetcher/1.0"}
    plans = (
        ("twse", urllib.request.Request(TWSE_URL + "?startDate=%s&endDate=%s" % (start, end), headers=headers),
         parse_twse_html),
        ("tpex", urllib.request.Request(
            TPEX_URL, data=urllib.parse.urlencode({"startDate": start, "endDate": end, "lang": "zh-tw", "stkNo": ""}).encode(),
            headers=dict(headers, **{"Content-Type": "application/x-www-form-urlencoded"})), parse_tpex_json),
    )
    out, count = {}, 0
    for key, req, parse in plans:
        count += 1
        try:
            raw = read(req)
            out[key] = parse(raw)
            out[key + "_sha256"] = hashlib.sha256(raw).hexdigest()   # 原文 hash 跟著每筆 basis 走，原文本身不進 market
        except Exception as ex:        # 任何失敗都不等於查無：呼叫端沿用該市場前值
            out[key] = None
            print("[YIELD] %s 配息清單本輪失敗（%s），沿用前值" % (key, type(ex).__name__))
    return out, count


def _roc(value):
    m = _ROC_RE.fullmatch(value) if isinstance(value, str) else None
    if not m:
        raise ValueError("日期格式不符")
    return dt.date(int(m[1]) + 1911, int(m[2]), int(m[3]))


def collect_events(rows, codes, start, as_of):
    """回傳 (events, unusable, name_diffs)。

    events＝{code: {ex_iso: event}}。unusable＝{code: 原因}：衝突或已到除息日卻無法確認金額，
    分子不完整就不能比較。未來除息尚無金額是正常狀態，只是不採用。
    """
    events, unusable, name_diffs = {}, {}, []
    for r in rows:
        code = r.get("code")
        if not isinstance(code, str) or code not in codes:
            continue
        if r.get("name") is not None and "".join(str(r["name"]).split()) != "".join(str(codes[code]).split()):
            name_diffs.append({"code": code, "source_name": r["name"], "display_name": codes[code], "source": r["source"]})
        try:
            ex = _roc(r.get("ex"))
        except ValueError:
            unusable[code] = "除息日無法解析"
            continue
        if ex < start:
            continue
        future = ex > as_of
        raw_amount = r.get("amount")
        try:
            if isinstance(raw_amount, bool) or not _AMOUNT_RE.fullmatch(str(raw_amount)):
                raise ValueError("金額未確定")
            amount = Decimal(str(raw_amount))
            if amount == 0:            # 官方明列 0＝該次沒有分配，不是缺值
                continue
            pay = _roc(r.get("pay"))
            if pay < ex:
                raise ValueError("發放日早於除息日")
        except (ValueError, InvalidOperation) as err:
            if not future:
                unusable[code] = "%s 已除息但%s" % (ex.isoformat(), err)
            continue
        item = {"ex_date": ex.isoformat(), "pay_date": pay.isoformat(), "amount": str(amount),
                "source": r["source"], "source_name": str(r.get("name") or ""), "future": future}
        held = events.setdefault(code, {})
        prior = held.get(item["ex_date"])
        if prior and (Decimal(prior["amount"]) != amount or prior["pay_date"] != item["pay_date"]):
            unusable[code] = "%s 同日配息資料衝突" % item["ex_date"]
        elif not prior:
            held[item["ex_date"]] = item
    return events, unusable, name_diffs


def _apply_unit_changes(events, verified, records, observed, start, as_of):
    """回傳 (調整後事件, 採用的變更)；窗口內有未核實的單位變更 → (None, None)。observed None＝沒有歷史可核對。
    只有 verified 的生效日可換算：records（SPLIT_RECORDS）多為約略或待確認日期，Yahoo 日期也不是金額單位的證明，只用來發現「有變更」。"""
    if observed is None:
        return None, None
    inside = [c for c in verified if start <= dt.date.fromisoformat(c["date"]) <= as_of]
    days = {c["date"] for c in inside}
    if any(start <= day <= as_of and day.isoformat() not in days for day in observed):
        return None, None
    margin = dt.timedelta(days=RECORD_DATE_MARGIN_DAYS)
    for d, _ in records:
        day = dt.date.fromisoformat(d)
        if start - margin <= day <= as_of + margin and not any(
                abs((dt.date.fromisoformat(c) - day).days) <= RECORD_DATE_MARGIN_DAYS for c in days):
            return None, None
    out = []
    for ev in events:
        amount, item = Decimal(ev["amount"]), dict(ev)
        for c in inside:
            if ev["ex_date"] < c["date"]:
                amount /= Decimal(c["ratio"])
        if amount != Decimal(ev["amount"]):
            item["raw_amount"], item["amount"] = ev["amount"], format(amount, "f")
        out.append(item)
    return out, inside


def rate_of(annual_cash, price):
    return float(Decimal(annual_cash) / Decimal(str(price)) * 100)


def build_basis(code, events, price, listing_date, frequency, as_of, source_sha256, verified=(), records=(), observed=None):
    """回傳 (basis, None) 或 (None, 不可比較原因)。events 為該檔已通過 collect_events 的事件。"""
    if frequency == "不配息":
        return None, "政策不配息"
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
        return None, "沒有有效價格"
    try:
        listed = dt.date.fromisoformat(listing_date)
    except (TypeError, ValueError):
        return None, "沒有可信上市日，無法確認是否滿一年"
    if listed > as_of:
        return None, "上市日晚於資料日"
    start = window_start(as_of)
    ordered = sorted(events, key=lambda ev: ev["ex_date"])
    if not ordered:
        return None, "沒有可採正額"
    ordered, applied = _apply_unit_changes(ordered, verified, records, observed, start, as_of)
    if ordered is None:
        return None, "窗口內單位變更無法確認"
    per_year = FREQ_PER_YEAR.get(frequency)
    if yield_is_new(listed, as_of):
        if not per_year:
            return None, "新上市配息頻率未經可信政策確認"
        selected = ordered[-per_year:]
        annual = sum(Decimal(ev["amount"]) for ev in selected) / len(selected) * per_year
        method = "annualized_estimate"
    else:
        selected = [ev for ev in ordered if not ev["future"]]
        if not selected:
            return None, "滿一年基金只有未來公告"
        annual = sum(Decimal(ev["amount"]) for ev in selected)
        method = "trailing_12m"
    basis = {"method": method, "as_of": as_of.isoformat(), "window_start": start.isoformat(), "listing_date": listing_date,
             "source_sha256": source_sha256, "frequency": frequency if per_year else None, "periods_per_year": per_year,
             "annual_cash": format(annual, "f"), "events": selected, "price": price,
             "rate": rate_of(format(annual, "f"), price)}
    if applied:
        basis["unit_changes"] = applied
    check_yield_basis(code, basis, price)
    return basis, None


def refresh_basis(code, basis, price, today):
    """同一分子配最新價格重算。先完整驗原紀錄，重算不得把壞掉的 rate／price 洗成有效。
    壞掉、過期或已滿一年仍是估算 → None（該檔不進榜，頁面照常）。"""
    if basis is None:
        return None
    try:
        check_yield_basis(code, basis, basis.get("price") if isinstance(basis, dict) else None)
        age = (today - dt.date.fromisoformat(basis["as_of"])).days
        if age < 0 or age > MAX_BASIS_AGE_DAYS:
            return None
        if (basis["method"] == "annualized_estimate") is not yield_is_new(dt.date.fromisoformat(basis["listing_date"]), today):
            return None
        fresh = dict(basis, price=price, rate=rate_of(basis["annual_cash"], price))
        check_yield_basis(code, fresh, price)
        return fresh
    except (DataInvalid, KeyError, TypeError, ValueError, ArithmeticError) as ex:
        print("[YIELD] %s 比較資料無法使用（%s），本輪不進榜" % (code, type(ex).__name__))
        return None


def refresh_market_entry(e, today):
    """mis_fetcher：只重算比率，不查來源。"""
    if "yield_basis" not in e:
        return
    fresh = refresh_basis(e.get("code"), e["yield_basis"], e.get("price"), today)
    if fresh is None:
        e.pop("yield_basis")
    else:
        e["yield_basis"] = fresh


def trusted_frequencies(div_meta):
    """沿用既有政策判定：known_policy 有效，且 _todo:false 或附有效官方證據（_todo 可能只代表金額／月份待核）。
    壞證據即使 _todo:false 也拒用；沒有證據的 _todo:true 不靠文字欄位放行。"""
    out = {}
    for code, meta in div_meta.items():
        if not isinstance(meta, dict) or not meta.get("frequency") or official_frequency.known_policy(code, meta) is None:
            continue
        if not meta.get("_todo", True) or "frequency_evidence" in meta or "policy_source" in meta:
            out[code] = meta["frequency"]
    return out


def attach(results, sources, previous, confirmed_freq, split_records, observed_splits, listing_dates, as_of, verified_units=None):
    """fetch_etf 寫 _base 前呼叫：同一次來源結果套給全部 ETF，某市場來源失敗時該市場沿用前值。
    上市日只收本輪 ISIN 原文；ISIN 本輪失敗就沿用前值紀錄裡當初由 ISIN 取得的上市日。"""
    verified_units = VERIFIED_UNIT_CHANGES if verified_units is None else verified_units
    codes = {e["code"]: e["name"] for e in results}
    start = window_start(as_of)
    rows = (sources.get("twse") or []) + (sources.get("tpex") or [])
    events, unusable, name_diffs = collect_events(rows, codes, start, as_of)
    summary = {"fresh": 0, "kept": 0, "not_comparable": {}, "name_differences": name_diffs,
               "source_sha256": {k: sources.get(k + "_sha256") for k in ("twse", "tpex")}}
    for e in results:
        code = e["code"]
        e.pop("yield_basis", None)
        market = "tpex" if e.get("otc") else "twse"
        prior = previous.get(code)
        if sources.get(market) is None:
            kept = refresh_basis(code, prior, e.get("price"), as_of)
            if kept and kept["frequency"] not in (None, confirmed_freq.get(code)):
                kept = None            # 政策已失效或改變：舊估算不沿用
            if kept:
                e["yield_basis"] = kept
                summary["kept"] += 1
            else:
                summary["not_comparable"][code] = "來源本輪失敗且無可沿用前值"
            continue
        if code in unusable:
            summary["not_comparable"][code] = unusable[code]
            continue
        listing = listing_dates.get(code) or (prior.get("listing_date") if isinstance(prior, dict) else None)
        basis, why = build_basis(code, list(events.get(code, {}).values()), e.get("price"), listing, confirmed_freq.get(code), as_of,
                                 sources.get(market + "_sha256"), verified_units.get(code, ()), split_records.get(code, ()), observed_splits.get(code))
        if basis:
            e["yield_basis"] = basis
            summary["fresh"] += 1
        else:
            summary["not_comparable"][code] = why
    return summary
