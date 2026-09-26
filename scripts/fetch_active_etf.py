# -*- coding: utf-8 -*-
"""
fetch_active_etf.py
抓主動式 ETF 每日持股（PCF 申購買回清單），算出個股的買賣超金額。

資料源：各投信官網公告的 PCF，一手官方資料。
       法規要求主動式 ETF 每日開盤前揭露全部持股，所以持股是每日更新的。

買賣超 =（本次股數 − 前一份快照股數）× 當日 TWSE 官方收盤價

⚠ 這是「兩份公開快照相減」的推估值，不等於基金實際成交。
  除權息、股票分割、成分股調整都可能造成假訊號，前端必須標註清楚。

輸出：
  data/_active_snapshot.json   內部用：最近一份持股快照（下次執行拿來相減）
  data/active_flow.json        前端讀：個股買賣超金額 + 主買/主賣的 ETF

用法: python scripts/fetch_active_etf.py
"""

import datetime
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Windows cp950 主控台印 emoji 會 UnicodeEncodeError，比照其他腳本加防呆
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT     = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "_active_snapshot.json"
OUT      = ROOT / "data" / "active_flow.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode    = ssl.CERT_NONE


def _opener():
    """帶 cookie 的 opener——統一投信要先拿到 session cookie 才肯回 PCF。"""
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=_SSL),
    )
    op.addheaders = [("User-Agent", UA)]
    return op


def _roc(d):
    """date -> 民國日期字串 115/09/23"""
    return f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"


def _ms_date(v):
    """PCF 回傳的日期 -> "2026-09-22"；解析不出來回 None。

    同一支 API 會混用兩種格式（實測 00403A 回 /Date(...)/、00981A 回 ISO），
    兩種都要認，只認一種會讓另一半的資料日變成 None。
    """
    s = str(v or "")
    m = re.search(r"/Date\((-?\d+)\)/", s)
    if m:
        return datetime.datetime.fromtimestamp(
            int(m.group(1)) / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


# ══════════════════════════════════════════════════════════════
# TWSE 官方收盤價（全市場，含個股）
# 與 fetch_etf.py 的 fetch_twse_official_closes() 同一支 API；
# 那邊是 module import 時就執行，直接 import 會多打一次網路，故另寫一份。
# ══════════════════════════════════════════════════════════════
_CLOSES_CACHE = {}


def closes_on(day, max_lookback=6):
    """取 day（datetime.date）當日或之前最近交易日的全市場收盤價。

    PCF 的資料日比行情落後 1~2 天且各投信不同，所以金額要用「該 ETF 資料日」
    的收盤價換算，不能一律用最新收盤——用錯日期會讓金額系統性偏掉。
    回傳 (實際使用的日期字串, {代碼: 收盤價})。
    """
    if day in _CLOSES_CACHE:
        return _CLOSES_CACHE[day]
    date_str, closes = fetch_twse_closes(max_lookback=max_lookback, end=day)
    # TWSE MI_INDEX 只有上市股票。ETF 常持有上櫃股（00410A 30 檔裡就有 6 檔
    # ——力旺/昇達科/聯亞/旺矽/金居/新應材），少了櫃買這半，那些持股的異動
    # 會因為查不到價而被靜靜跳過。
    if date_str:
        closes = dict(closes)
        closes.update(fetch_tpex_closes(date_str))
    _CLOSES_CACHE[day] = (date_str, closes)
    return _CLOSES_CACHE[day]


def fetch_tpex_closes(date_str):
    """櫃買中心當日收盤行情。date_str 為 YYYYMMDD，回傳 {代碼: 收盤價}。"""
    try:
        d = datetime.datetime.strptime(date_str, "%Y%m%d").date()
        url = ("https://www.tpex.org.tw/www/zh-tw/afterTrading/otc"
               f"?date={d.strftime('%Y/%m/%d')}&type=EW&response=json")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20, context=_SSL) as r:
            resp = json.loads(r.read().decode("utf-8"))
        rows = (resp.get("tables") or [{}])[0].get("data") or []
        out = {}
        for row in rows:                       # [代號, 名稱, 收盤, ...]
            try:
                out[row[0].strip()] = float(str(row[2]).replace(",", ""))
            except (ValueError, IndexError):
                pass
        print(f"[TPEx] 上櫃收盤 {date_str}（{len(out)} 檔）")
        return out
    except Exception as e:
        print(f"[TPEx] {date_str} 抓取失敗: {e}")
        return {}


def fetch_twse_closes(max_lookback=6, end=None):
    """回傳 (date_str, {股票代碼: 收盤價})。找不到回 (None, {})。"""
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    base = end or now_tw.date()
    for delta in range(max_lookback):
        d = base - datetime.timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        ds = d.strftime("%Y%m%d")
        try:
            url = ("https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
                   f"?date={ds}&type=ALLBUT0999&response=json")
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20, context=_SSL) as r:
                resp = json.loads(r.read().decode("utf-8"))
            if resp.get("stat") != "OK":
                continue
            tables = resp.get("tables", [])
            if len(tables) < 9 or not tables[8].get("data"):
                continue
            out = {}
            for row in tables[8]["data"]:
                try:
                    out[row[0].strip()] = float(str(row[8]).replace(",", ""))
                except (ValueError, IndexError):
                    pass
            print(f"[TWSE] 收盤價來源 {ds}（{len(out)} 檔）")
            return ds, out
        except Exception as e:
            print(f"[TWSE] {ds} 失敗: {e}")
    print("[TWSE] 收盤價抓取失敗，本次無法換算金額")
    return None, {}


# ══════════════════════════════════════════════════════════════
# Adapter：統一投信（www.ezmoney.com.tw）
#   GET  /                        取 session cookie（少了會 302 迴圈）
#   POST /ETF/Transaction/GetPCF  {"fundCode","date","specificDate"}
#   持股在 asset[AssetCode=="ST"].Details
#   fundCode 是投信內部代碼（63YTW…），不是股票代號
# ══════════════════════════════════════════════════════════════
TSIT_FUNDS = {
    "00981A": ("49YTW", "主動統一台股增長"),
    "00403A": ("63YTW", "主動統一升級50"),
    "00988A": ("61YTW", "主動統一全球創新"),
    "00411A": ("64YTW", "主動統一前沿科技"),
}


def fetch_tsit(date_obj, specific=False):
    """specific=True 時抓指定日期的歷史 PCF（統一的 API 支援，用來回補前一交易日）。"""
    op = _opener()
    try:
        op.open("https://www.ezmoney.com.tw/", timeout=20).read()
    except Exception as e:
        print(f"[統一] 取 cookie 失敗: {e}")
        return {}

    out = {}
    for ticker, (fund_code, name) in TSIT_FUNDS.items():
        payload = json.dumps({
            "fundCode": fund_code,
            "date": _roc(date_obj),
            "specificDate": specific,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://www.ezmoney.com.tw/ETF/Transaction/GetPCF",
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.ezmoney.com.tw/ETF/Transaction/PCF",
            },
        )
        try:
            raw = op.open(req, timeout=25).read().decode("utf-8")
            if raw.lstrip().startswith("<"):
                print(f"[統一] {ticker} 回傳 HTML（非 JSON），略過")
                continue
            d = json.loads(raw)
        except Exception as e:
            print(f"[統一] {ticker} 失敗: {e}")
            continue

        # PCF 自己的資料日（TranDate）。統一的 PCF 比行情落後約 2 天，且傳進去的
        # date 參數不等於回傳的 TranDate，所以資料日一定要從回應裡取，
        # 不能拿執行當天的日期充當——那會讓「資料沒更新」被誤顯示成「今日無異動」。
        data_date = _ms_date((d.get("pcf") or [{}])[0].get("TranDate"))

        st = [a for a in (d.get("asset") or []) if a.get("AssetCode") == "ST"]
        details = (st[0].get("Details") or []) if st else []
        # 查歷史時 pcf 陣列可能是空的，但每一筆持股明細自己也帶 TranDate，拿來備援
        if not data_date and details:
            data_date = _ms_date(details[0].get("TranDate"))
        holdings = {}
        for x in details:
            code = str(x.get("DetailCode", "")).strip()
            try:
                share = int(x.get("Share") or 0)
            except (TypeError, ValueError):
                continue
            if code and share:
                holdings[code] = {
                    "name": str(x.get("DetailName", "")).strip(),
                    "shares": share,
                }
        if holdings:
            out[ticker] = {"name": name, "issuer": "統一",
                           "data_date": data_date, "holdings": holdings}
            print(f"[統一] {ticker} {name}：{len(holdings)} 檔，資料日 {data_date or '?'}")
        time.sleep(1)
    return out


# ══════════════════════════════════════════════════════════════
# Adapter：永豐投信（sitc.sinopac.com）
#   PCF 頁面是靜態 HTML，預設就帶出 00410A 的完整持股表
# ══════════════════════════════════════════════════════════════
SINOPAC_FUNDS = {"00410A": "主動永豐科技趨勢"}


def fetch_sinopac(date_obj, specific=False):
    """POST 表單查詢：fundId + hDate。查詢日 D 取回的是「資料日期 D-1」的 PCF。"""
    url = "https://sitc.sinopac.com/SinopacEtfs/Etfs/Pcf"
    body = urllib.parse.urlencode({
        "fundId": "00410A",
        "hDate": date_obj.strftime("%Y-%m-%d"),
        "op": "",
    }).encode()
    try:
        req = urllib.request.Request(url, data=body, headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": url,
        })
        html = urllib.request.urlopen(req, timeout=25, context=_SSL).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"[永豐] 失敗: {e}")
        return {}

    # 表格列：<td>代碼</td><td>名稱</td>…<td>股數</td>
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    tag = re.compile(r"<[^>]+>")
    holdings = {}
    for tr in rows:
        cells = [tag.sub("", c).replace("&nbsp;", " ").strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
        if len(cells) < 3:
            continue
        code = cells[0]
        if not re.fullmatch(r"\d{4,6}[A-Z]?", code):
            continue
        for c in cells[2:]:
            n = c.replace(",", "")
            if n.isdigit() and int(n) > 0:
                holdings[code] = {"name": cells[1], "shares": int(n)}
                break

    if not holdings:
        print("[永豐] 解析不到持股，頁面結構可能改了")
        return {}
    # 頁面上有「資料日期：2026/09/23」，永豐落後 1 天（統一落後 2 天），各家不同
    m = re.search(r"資料日期[：:]\s*(\d{4})[/-](\d{2})[/-](\d{2})", html)
    data_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
    name = SINOPAC_FUNDS["00410A"]
    print(f"[永豐] 00410A {name}：{len(holdings)} 檔，資料日 {data_date or '?'}")
    return {"00410A": {"name": name, "issuer": "永豐",
                       "data_date": data_date, "holdings": holdings}}


# ══════════════════════════════════════════════════════════════
# Adapter：凱基投信（www.kgifund.com.tw）
#   POST /Fund/RedemptionVC  fundID=<內部代碼>&queryDate=<YYYY/MM/DD 或空>
#   回傳 HTML 片段，表格欄位 [代碼, 名稱, 股數, 權重]，名稱是 HTML 實體編碼
#   資料日在 <input id="DataDate" value="2026/09/24">，實測**沒有延遲**
#   fundID 同樣是投信內部代碼（00407A → J024），不是股票代號
# ══════════════════════════════════════════════════════════════
KGI_FUNDS = {"00407A": ("J024", "主動凱基台灣")}


def fetch_kgi(date_obj, specific=False):
    import html as _html
    url = "https://www.kgifund.com.tw/Fund/RedemptionVC"
    out = {}
    for ticker, (fund_id, name) in KGI_FUNDS.items():
        body = urllib.parse.urlencode({
            "fundID": fund_id,
            "queryDate": date_obj.strftime("%Y/%m/%d") if specific else "",
        }).encode()
        try:
            req = urllib.request.Request(url, data=body, headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.kgifund.com.tw/Fund/RedemptionList",
            })
            page = urllib.request.urlopen(req, timeout=25, context=_SSL).read().decode("utf-8", "replace")
        except Exception as e:
            print(f"[凱基] {ticker} 失敗: {e}")
            continue

        # 別用 <input id="DataDate">，那是「現金申購買回清單公告日」，是未來的
        # 交割生效日（實測 2026/09/24 的資料顯示 2026/09/29）。真正的資料日跟在
        # 淨值等數字後面，取頁面上所有「不超過今天」的日期中最新的那個。
        cands = sorted({f"{a}-{b}-{c}" for a, b, c in
                        re.findall(r"(\d{4})/(\d{2})/(\d{2})", page)})
        today_s = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
        past = [x for x in cands if x <= today_s]
        data_date = past[-1] if past else None

        tag = re.compile(r"<[^>]+>")
        holdings = {}
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
            cells = [_html.unescape(tag.sub("", c)).replace("\xa0", " ").strip()
                     for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
            if len(cells) < 3 or not re.fullmatch(r"\d{4,6}[A-Z]?", cells[0]):
                continue
            try:
                share = int(cells[2].replace(",", ""))
            except ValueError:
                continue
            if share:
                holdings[cells[0]] = {"name": cells[1], "shares": share}
        if holdings:
            out[ticker] = {"name": name, "issuer": "凱基",
                           "data_date": data_date, "holdings": holdings}
            print(f"[凱基] {ticker} {name}：{len(holdings)} 檔，資料日 {data_date or '?'}")
        time.sleep(1)
    return out


# ══════════════════════════════════════════════════════════════
# Adapter：台新投信（www.tsit.com.tw）
#   POST /ETF/Home/Pcf  ETF_ID=<股票代號>&DATA_DATE=<YYYY-MM-DD>
#   這家直接用股票代號，不用內部代碼；DATA_DATE 可查歷史，且當天就有資料
#   表格欄位 [代號, 名稱, 股數, 持股權重]，代號帶彭博後綴（"2330 TT"）
# ══════════════════════════════════════════════════════════════
TSIT_TAISHIN_FUNDS = {
    "00986A": "主動台新龍頭成長",
    "00987A": "主動台新優勢成長",
}


def fetch_taishin(date_obj, specific=False):
    import html as _html
    url = "https://www.tsit.com.tw/ETF/Home/Pcf"
    out = {}
    for ticker, name in TSIT_TAISHIN_FUNDS.items():
        body = urllib.parse.urlencode({
            "ETF_ID": ticker,
            "DATA_DATE": date_obj.strftime("%Y-%m-%d"),
            "FUND_TYPE": "ALL",
        }).encode()
        try:
            req = urllib.request.Request(url, data=body, headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": url,
            })
            page = urllib.request.urlopen(req, timeout=25, context=_SSL).read().decode("utf-8", "replace")
        except Exception as e:
            print(f"[台新] {ticker} 失敗: {e}")
            continue

        # DATA_DATE 只是把我們送進去的值原樣回傳，不是真的資料日；
        # 真正的最新資料日在 MAX_DATE。取兩者較早的那個才正確。
        def _pick(name):
            m = re.search(name + r'[^>]*value="(\d{4})-(\d{2})-(\d{2})"', page)
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
        echoed, newest = _pick("DATA_DATE"), _pick("MAX_DATE")
        data_date = min(x for x in (echoed, newest) if x) if (echoed or newest) else None

        tag = re.compile(r"<[^>]+>")
        holdings = {}
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
            cells = [_html.unescape(tag.sub("", c)).replace("\xa0", " ").strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
            if len(cells) < 3:
                continue
            # 代號帶彭博後綴，"2330 TT" / "MSFT US"，取空白前那段
            code = cells[0].split()[0] if cells[0] else ""
            if not re.fullmatch(r"[0-9A-Z]{3,6}", code):
                continue
            try:
                share = int(cells[2].replace(",", ""))
            except ValueError:
                continue
            if share:
                holdings[code] = {"name": cells[1], "shares": share}
        if holdings:
            out[ticker] = {"name": name, "issuer": "台新",
                           "data_date": data_date, "holdings": holdings}
            print(f"[台新] {ticker} {name}：{len(holdings)} 檔，資料日 {data_date or '?'}")
        time.sleep(1)
    return out


# ══════════════════════════════════════════════════════════════
# Adapter：中國信託投信（www.ctbcinvestments.com.tw）
#   Vue SPA，資料走 JSON API，但要先換 token：
#     1. POST /API/home/AuthToken  token=www.ctbcinvestments.com（寫死的初始值）
#        → 回 Data.token（真 token，約 115 字元）
#     2. POST /API/etf/Buyback?token=<真token>  body {FID, StartDate, token}
#        token 要同時放 query 與 body，缺一不可
#   持股在 Data.Detail[Code=="STOCK"].Data，欄位 code_/name_/qty_
#   資料日用「淨值日期」，不是「公告日」（公告日是次一營業日）
#   FID 是投信內部代碼，可由 /API/etf/ETFCNOList 取得
# ══════════════════════════════════════════════════════════════
CTBC_API   = "https://www.ctbcinvestments.com.tw/API/"
CTBC_FUNDS = {
    "00406A": ("E0038", "主動中信台灣收益"),
    "00983A": ("E0034", "主動中信ARK創新"),
    "00995A": ("E0036", "主動中信台灣卓越"),
}


def _ctbc_token():
    body = json.dumps({"token": "www.ctbcinvestments.com"}).encode()
    req = urllib.request.Request(
        CTBC_API + "home/AuthToken?token=www.ctbcinvestments.com", data=body,
        headers={"User-Agent": UA, "Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=20, context=_SSL) as r:
        return json.loads(r.read().decode("utf-8"))["Data"]["token"]


def fetch_ctbc(date_obj, specific=False):
    try:
        token = _ctbc_token()
    except Exception as e:
        print(f"[中信] 取 token 失敗: {e}")
        return {}

    out = {}
    for ticker, (fid, name) in CTBC_FUNDS.items():
        body = json.dumps({"FID": fid, "token": token,
                           "StartDate": date_obj.strftime("%Y/%m/%d")}).encode()
        url = CTBC_API + "etf/Buyback?token=" + urllib.parse.quote(token, safe="")
        try:
            req = urllib.request.Request(url, data=body, headers={
                "User-Agent": UA, "Content-Type": "application/json; charset=utf-8"})
            d = json.loads(urllib.request.urlopen(req, timeout=25, context=_SSL)
                           .read().decode("utf-8"))
        except Exception as e:
            print(f"[中信] {ticker} 失敗: {e}")
            continue
        if d.get("ResultCode") != 0 or not d.get("Data"):
            print(f"[中信] {ticker} 回應異常: {str(d.get('ResultMsg'))[:40]}")
            continue

        data = d["Data"]
        head = (data.get("Data") or [{}])[0]
        # 用淨值日期，不是公告日——公告日是次一營業日
        raw = str(head.get("淨值日期") or head.get("每受益權單位淨資產價值DATE") or "")
        m = re.search(r"(\d{4})[/-](\d{2})[/-](\d{2})", raw)
        data_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

        holdings = {}
        for grp in data.get("Detail") or []:
            if grp.get("Code") != "STOCK":
                continue                       # 期貨/選擇權/現金不算持股
            for x in grp.get("Data") or []:
                code = str(x.get("code_", "")).strip()
                try:
                    share = int(float(str(x.get("qty_", "0")).replace(",", "")))
                except ValueError:
                    continue
                if code and share:
                    holdings[code] = {"name": str(x.get("name_", "")).strip(),
                                      "shares": share}
        if holdings:
            out[ticker] = {"name": name, "issuer": "中信",
                           "data_date": data_date, "holdings": holdings}
            print(f"[中信] {ticker} {name}：{len(holdings)} 檔，資料日 {data_date or '?'}")
        time.sleep(1)
    return out


# ══════════════════════════════════════════════════════════════
# Adapter：群益投信（www.capitalfund.com.tw，Angular）
#   POST /CFWeb/api/etf/buyback   {"fundId":"<內部碼>","date":null|"YYYY-MM-DD"}
#   **要 /CFWeb 前綴**，裸 /api/... 是 404
#   fundId 由 POST /CFWeb/api/etf/items 取得（fundNo ↔ stockNo 對照）
#   持股在 data.stocks，欄位 stocNo/stocName/share
#   資料日用 pcf.date2（date1 是未來的公告生效日，同凱基/中信的陷阱）
# ══════════════════════════════════════════════════════════════
CAPITAL_API = "https://www.capitalfund.com.tw/CFWeb/api/etf/"


def _capital_post(path, payload):
    req = urllib.request.Request(
        CAPITAL_API + path,
        data=json.dumps(payload).encode() if payload is not None else b"null",
        headers={"User-Agent": UA, "Content-Type": "application/json",
                 "Referer": "https://www.capitalfund.com.tw/etf/transaction/buyback"})
    with urllib.request.urlopen(req, timeout=25, context=_SSL) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_capital(date_obj, specific=False):
    try:
        items = _capital_post("items", None).get("data") or []
    except Exception as e:
        print(f"[群益] 取基金清單失敗: {e}")
        return {}
    funds = {x["stockNo"]: (x["fundNo"], x.get("shortName", ""))
             for x in items if str(x.get("stockNo", "")).endswith("A")}

    out = {}
    for ticker, (fund_no, name) in funds.items():
        try:
            d = _capital_post("buyback", {
                "fundId": fund_no,
                "date": date_obj.strftime("%Y-%m-%d") if specific else None,
            }).get("data") or {}
        except Exception as e:
            print(f"[群益] {ticker} 失敗: {e}")
            continue

        pcf = d.get("pcf") or {}
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(pcf.get("date2") or ""))
        data_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

        holdings = {}
        for x in d.get("stocks") or []:
            code = str(x.get("stocNo", "")).strip()
            try:
                share = int(float(x.get("share") or 0))
            except (TypeError, ValueError):
                continue
            if code and share:
                holdings[code] = {"name": str(x.get("stocName", "")).strip(),
                                  "shares": share}
        if holdings:
            out[ticker] = {"name": name, "issuer": "群益",
                           "data_date": data_date, "holdings": holdings}
            print(f"[群益] {ticker} {name}：{len(holdings)} 檔，資料日 {data_date or '?'}")
        time.sleep(1)
    return out


# ══════════════════════════════════════════════════════════════
# Adapter：富邦投信（websys.fsit.com.tw）
#   GET /FubonETF/Fund/Assets.aspx?stkId=<代號>&lan=TW
#   ⚠ 持股**不在** PCF 頁（Pcf.aspx 只有基金淨值等層級數字，一度讓我誤判
#     「富邦沒公開成分股」）。完整持股在「基金資產」頁 Assets.aspx。
#   表格欄位 [代號, 名稱, 股數, 市值, 權重]，只吃 stkId，沒有日期參數
# ══════════════════════════════════════════════════════════════
FUBON_FUNDS = {"00405A": "主動富邦台灣龍耀"}


def fetch_fubon(date_obj, specific=False):
    if specific:
        return {}          # Assets.aspx 沒有日期參數，查不了歷史
    out = {}
    for ticker, name in FUBON_FUNDS.items():
        url = ("https://websys.fsit.com.tw/FubonETF/Fund/Assets.aspx"
               f"?stkId={ticker}&lan=TW")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            page = urllib.request.urlopen(req, timeout=25, context=_SSL).read().decode("utf-8", "replace")
        except Exception as e:
            print(f"[富邦] {ticker} 失敗: {e}")
            continue

        tag = re.compile(r"<[^>]+>")
        holdings = {}
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
            cells = [tag.sub("", c).replace("&nbsp;", " ").strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
            if len(cells) < 3:
                continue
            code = cells[0].split()[0] if cells[0].split() else ""
            if not re.fullmatch(r"\d{4,6}[A-Z]?", code):
                continue
            try:
                share = int(cells[2].replace(",", ""))
            except ValueError:
                continue
            if share:
                holdings[code] = {"name": cells[1], "shares": share}

        m = re.search(r"(\d{4})/(\d{2})/(\d{2})", page)
        data_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
        if holdings:
            out[ticker] = {"name": name, "issuer": "富邦",
                           "data_date": data_date, "holdings": holdings}
            print(f"[富邦] {ticker} {name}：{len(holdings)} 檔，資料日 {data_date or '?'}")
    return out


# ══════════════════════════════════════════════════════════════
# Adapter：野村投信（www.nomurafunds.com.tw，Angular）
#   POST /API/ETFAPI/api/Fund/GetFundAssets  {"FundID":"00999A","SearchDate":null}
#   ⚠ SearchDate 是 nullable DateTime，傳空字串會 400，要傳 null 或日期
#   持股同樣不在 PCF 頁，而在「基金資產」：Entries.Data.Table 裡
#   TableTitle=="股票" 那一張，Rows = [代號, 名稱, 股數, 權重]，
#   資料日在該表的 NavDate
# ══════════════════════════════════════════════════════════════
NOMURA_FUNDS = {
    "00999A": "主動野村臺灣高息",
    "00980A": "主動野村臺灣優選",
    "00985A": "主動野村台灣50",
}


def fetch_nomura(date_obj, specific=False):
    url = "https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets"
    out = {}
    for ticker, name in NOMURA_FUNDS.items():
        payload = {"FundID": ticker,
                   "SearchDate": date_obj.strftime("%Y-%m-%d") if specific else None}
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                headers={"User-Agent": UA, "Content-Type": "application/json",
                         "Referer": "https://www.nomurafunds.com.tw/ETFWEB/pcf"})
            d = json.loads(urllib.request.urlopen(req, timeout=25, context=_SSL)
                           .read().decode("utf-8"))
        except Exception as e:
            print(f"[野村] {ticker} 失敗: {e}")
            continue

        tables = (((d.get("Entries") or {}).get("Data") or {}).get("Table")) or []
        stock_tbl = next((t for t in tables if "股票" in str(t.get("TableTitle", ""))), None)
        if not stock_tbl:
            print(f"[野村] {ticker} 找不到股票表")
            continue
        m = re.search(r"(\d{4})/(\d{2})/(\d{2})", str(stock_tbl.get("NavDate") or ""))
        data_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

        holdings = {}
        for row in stock_tbl.get("Rows") or []:
            if len(row) < 3:
                continue
            code = str(row[0]).strip()
            try:
                share = int(float(str(row[2]).replace(",", "")))
            except ValueError:
                continue
            if code and share:
                holdings[code] = {"name": str(row[1]).strip(), "shares": share}
        if holdings:
            out[ticker] = {"name": name, "issuer": "野村",
                           "data_date": data_date, "holdings": holdings}
            print(f"[野村] {ticker} {name}：{len(holdings)} 檔，資料日 {data_date or '?'}")
        time.sleep(1)
    return out


ADAPTERS = [fetch_tsit, fetch_sinopac, fetch_kgi, fetch_taishin, fetch_ctbc,
            fetch_capital, fetch_fubon, fetch_nomura]


# ══════════════════════════════════════════════════════════════
def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _shares(h):
    return {k: v.get("shares") for k, v in (h or {}).items()}


def build_flow(prev, cur):
    """逐檔 ETF 比對前後兩份 PCF，算出它自己的加減碼明細。

    不做跨 ETF 彙總——涵蓋率不足時彙總數字會誤導（看起來像全市場結論，其實漏一大半）。

    advanced=False 代表**這檔的 PCF 還沒出新的**（資料日沒變，或持股一模一樣），
    必須和「經理人今天沒動作」分開顯示。2026-09-24 就踩過這個坑：PCF 落後行情
    兩天沒更新，畫面卻顯示 5 檔全部「異動 0」，看起來像市場靜止，其實是沒新資料。
    """
    prev_etfs = prev.get("etfs", {})
    out = {}

    for etf, info in cur.get("etfs", {}).items():
        before_e = prev_etfs.get(etf) or {}
        before   = before_e.get("holdings") or {}
        after    = info.get("holdings") or {}
        d_new    = info.get("data_date")
        d_old    = before_e.get("data_date")

        if not before:
            out[etf] = {"advanced": False, "reason": "no_basis",
                        "data_date": d_new, "basis_date": None,
                        "buy": 0, "sell": 0, "changed": 0, "flow": []}
            continue

        # 只有「資料日沒前進」才算沒更新。資料日有前進但持股一模一樣，
        # 那是經理人真的沒調整，兩者意義完全不同，不能混為一談。
        same_date = bool(d_new and d_old and d_new == d_old)
        if same_date or (not d_new and _shares(before) == _shares(after)):
            out[etf] = {"advanced": False, "reason": "not_updated",
                        "data_date": d_new, "basis_date": d_old,
                        "buy": 0, "sell": 0, "changed": 0, "flow": []}
            continue

        # 金額用「該 ETF 資料日」的收盤價換算，不是最新收盤——PCF 落後 1~2 天且各家不同
        price_date, closes = (None, {})
        if d_new:
            try:
                price_date, closes = closes_on(datetime.date.fromisoformat(d_new))
            except ValueError:
                pass
        if not closes:
            price_date, closes = fetch_twse_closes()

        rows, no_price = [], []
        for code in set(before) | set(after):
            b = (before.get(code) or {}).get("shares", 0)
            a = (after.get(code) or {}).get("shares", 0)
            d = a - b
            if not d:
                continue
            price = closes.get(code)
            if not price:
                # 查不到價就不硬算金額，但一定要記錄——這種「有異動卻算不出金額」
                # 的缺口若靜靜跳過，畫面會顯示成「沒有異動」。
                no_price.append(code)
                continue
            rows.append({
                "code": code,
                "name": (after.get(code) or before.get(code) or {}).get("name", ""),
                "delta_shares": d,
                "amount": round(d * price, 0),
            })
        rows.sort(key=lambda x: -abs(x["amount"]))

        # 整檔基金申購/贖回時，所有持股會同步等比例增減——那不是經理人換股。
        # 實測 00407A 2026-09-24：50 檔裡 49 檔同步 -3.65%，顯示成「減碼 8.3 億」
        # 會讓人以為經理人在賣股，其實只是規模縮水。同向且比例接近就標示出來。
        scale_pct = None
        ratios = []
        for code in set(before) & set(after):
            b = before[code].get("shares", 0)
            a = after[code].get("shares", 0)
            if b:
                ratios.append((a - b) / b)
        moved = [r for r in ratios if abs(r) > 0.0005]
        if len(moved) >= 5 and len(moved) >= 0.6 * len(after) and \
           (all(r > 0 for r in moved) or all(r < 0 for r in moved)):
            med = sorted(moved)[len(moved) // 2]
            # 六成以上持股同向，且變動幅度集中在中位數附近 → 判定為規模變動
            close = [r for r in moved if abs(r - med) <= abs(med) * 0.35]
            if len(close) >= 0.8 * len(moved):
                scale_pct = round(med * 100, 2)

        if no_price:
            print(f"[WARN] {etf} 有 {len(no_price)} 檔異動查不到收盤價，未計入金額：{no_price}")
        out[etf] = {
            "advanced":   True,
            "reason":     "ok",
            "no_price":   no_price,
            "scale_pct":  scale_pct,   # 非 None = 全池同步等比例增減（申贖造成的規模變動）
            "data_date":  d_new,
            "basis_date": d_old,
            "price_date": price_date,
            "buy":        round(sum(r["amount"] for r in rows if r["amount"] > 0), 0),
            "sell":       round(sum(r["amount"] for r in rows if r["amount"] < 0), 0),
            "changed":    len(rows),
            "flow":       rows,
        }
    return out


def main():
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    today  = now_tw.date()

    # 用「最後一個交易日」當查詢日，不要用今天。週末與國定假日（例如 2026-09-25
    # 中秋）傳今天進去，永豐與中信會直接回空、台新會把假日日期原樣 echo 回來，
    # 看起來就像 adapter 壞了。closes_on() 本來就會往回找到有行情的那天。
    trade_day_str, _ = closes_on(today)
    try:
        query_day = datetime.datetime.strptime(trade_day_str, "%Y%m%d").date()
    except (TypeError, ValueError):
        query_day = today
    if query_day != today:
        print(f"[DATE] 今天 {today} 非交易日，改以最後交易日 {query_day} 查詢")

    etfs = {}
    for fn in ADAPTERS:
        try:
            etfs.update(fn(query_day))
        except Exception as e:
            print(f"[WARN] {fn.__name__} 整支失敗: {e}")

    if not etfs:
        print("[ABORT] 所有 adapter 都沒抓到資料，保留既有檔案不覆蓋")
        return 1

    snapshot = {"fetched": now_tw.strftime("%Y-%m-%d %H:%M"), "etfs": etfs}

    prev = load_json(SNAPSHOT)

    # 沒有前次快照時，向支援歷史查詢的投信回補前一交易日，
    # 這樣第一次執行就算得出買賣超，不用空等一天。
    if not prev:
        # 回補「前一份」PCF。各投信、甚至同投信不同基金的公告延遲都不一樣
        # （實測 00403A 落後 2 天、00981A 落後 1 天），所以不能用固定天數，
        # 要逐日往前找到「資料日與當期不同」的那一份才停，否則回補區間會
        # 拉成一整週，算出來的不是單日調整。
        cur_dates = {c: v.get("data_date") for c, v in etfs.items()}
        back = {}
        print("[BOOTSTRAP] 無前次快照，逐日往前找每檔的前一份 PCF")
        for back_days in range(1, 8):
            todo = [c for c in etfs if c not in back]
            if not todo:
                break
            d = query_day - datetime.timedelta(days=back_days)
            if d.weekday() >= 5:
                continue
            got = {}
            for fn in ADAPTERS:
                try:
                    got.update(fn(d, specific=True))
                except Exception as e:
                    print(f"[WARN] {fn.__name__} 回補失敗: {e}")
            for c, v in got.items():
                dd = v.get("data_date")
                if c in etfs and c not in back and dd and dd != cur_dates.get(c):
                    back[c] = v
                    print(f"[BOOTSTRAP] {c} 前一份 = {dd}（當期 {cur_dates.get(c)}）")
        if back:
            prev = {"fetched": "(bootstrap)", "etfs": back}
        else:
            print("[BOOTSTRAP] 沒有投信支援歷史查詢，只能等下一個交易日")

    flows = build_flow(prev, snapshot) if prev else {}
    old_out = (load_json(OUT) or {}).get("etfs") or {}

    # 這次沒抓到的 ETF 一律保留上次的結果，不讓它從畫面上消失。
    # 2026-09-25 中秋連假那天，永豐/台新/中信因為被傳了假日日期而回空，
    # 輸出直接從 11 檔掉到 5 檔——使用者看到的是「我買的那檔不見了」。
    out_etfs = {}
    for code, old in old_out.items():
        if code not in etfs:
            out_etfs[code] = dict(old, fetched=False)
            print(f"[KEEP] {code} {old.get('name','')}：本次未抓到，沿用上次資料"
                  f"（資料日 {old.get('data_date')}）")

    for code, info in etfs.items():
        f = flows.get(code) or {"advanced": False, "reason": "no_basis"}
        prev_out = old_out.get(code) or {}
        row = {
            "name":      info["name"],
            "issuer":    info["issuer"],
            "holdings":  len(info["holdings"]),
            "data_date": info.get("data_date"),      # 這檔 PCF 自己的資料日
            "advanced":  bool(f.get("advanced")),    # 這次 PCF 有沒有出新的
            "reason":    f.get("reason", "no_basis"),
            "fetched":   True,
        }
        if f.get("advanced") and f.get("changed"):
            row.update({
                "flow_from":  f.get("basis_date"),
                "flow_to":    f.get("data_date"),
                "price_date": f.get("price_date"),
                "no_price": f.get("no_price") or [],   # 有異動但查無報價（海外持股）
                "scale_pct": f.get("scale_pct"),
                "buy": f["buy"], "sell": f["sell"],
                "changed": f["changed"], "flow": f["flow"],
                # 最近一次「真的有換檔」的日期，排行頁用它決定標籤要不要顯示
                "last_change_date": f.get("data_date"),
            })
        else:
            # 這次沒有新調整（PCF 未更新，或有更新但持股沒動）：
            # 沿用上一次「真的有換檔」的結果，不要顯示成空白或異動 0。
            o = prev_out
            row.update({
                "last_change_date": o.get("last_change_date"),
                "flow_from":  o.get("flow_from"),
                "flow_to":    o.get("flow_to"),
                "price_date": o.get("price_date"),
                "no_price": o.get("no_price") or [],
                "scale_pct": o.get("scale_pct"),
                "buy": o.get("buy", 0), "sell": o.get("sell", 0),
                "changed": o.get("changed", 0), "flow": o.get("flow", []),
            })
        out_etfs[code] = row

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "updated": now_tw.strftime("%Y-%m-%d %H:%M"),
            "note":    "加減碼以兩份公開 PCF 快照相減推估，不等同基金實際成交；"
                       "各投信 PCF 公告日不同（實測落後行情 1~2 天），資料日以每檔的 data_date 為準",
            "etfs":    out_etfs,
        }, f, ensure_ascii=False, indent=2)

    # 這次沒抓到的投信要保留舊快照，否則下次會沒有可比對的基準
    merged = dict((prev or {}).get("etfs") or {})
    merged.update(etfs)
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump({"fetched": snapshot["fetched"], "etfs": merged},
                  f, ensure_ascii=False, indent=2)

    print("")
    for code, r in sorted(out_etfs.items()):
        if r["advanced"]:
            print(f"[OK] {code} {r['name']}：{r['flow_from']} → {r['flow_to']}，"
                  f"異動 {r['changed']} 檔、加碼 {r['buy']/1e8:.1f} 億／減碼 {r['sell']/1e8:.1f} 億")
        else:
            why = {"not_updated": "PCF 尚未更新", "no_basis": "尚無前一份可比對"}.get(r["reason"], r["reason"])
            print(f"[--] {code} {r['name']}：{why}（資料日 {r['data_date'] or '?'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
