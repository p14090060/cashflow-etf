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


# ══════════════════════════════════════════════════════════════
# TWSE 官方收盤價（全市場，含個股）
# 與 fetch_etf.py 的 fetch_twse_official_closes() 同一支 API；
# 那邊是 module import 時就執行，直接 import 會多打一次網路，故另寫一份。
# ══════════════════════════════════════════════════════════════
def fetch_twse_closes(max_lookback=6):
    """回傳 (date_str, {股票代碼: 收盤價})。找不到回 (None, {})。"""
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    for delta in range(max_lookback):
        d = now_tw.date() - datetime.timedelta(days=delta)
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

        st = [a for a in (d.get("asset") or []) if a.get("AssetCode") == "ST"]
        details = (st[0].get("Details") or []) if st else []
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
            out[ticker] = {"name": name, "issuer": "統一", "holdings": holdings}
            tag = f"（{_roc(date_obj)} 歷史）" if specific else ""
            print(f"[統一] {ticker} {name}：{len(holdings)} 檔{tag}")
        time.sleep(1)
    return out


# ══════════════════════════════════════════════════════════════
# Adapter：永豐投信（sitc.sinopac.com）
#   PCF 頁面是靜態 HTML，預設就帶出 00410A 的完整持股表
# ══════════════════════════════════════════════════════════════
SINOPAC_FUNDS = {"00410A": "主動永豐科技趨勢"}


def fetch_sinopac(date_obj, specific=False):
    if specific:
        return {}          # 永豐頁面只給當期，沒有歷史查詢，回補時略過
    url = "https://sitc.sinopac.com/SinopacEtfs/Etfs/Pcf"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
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
    name = SINOPAC_FUNDS["00410A"]
    print(f"[永豐] 00410A {name}：{len(holdings)} 檔")
    return {"00410A": {"name": name, "issuer": "永豐", "holdings": holdings}}


ADAPTERS = [fetch_tsit, fetch_sinopac]


# ══════════════════════════════════════════════════════════════
def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def build_flow(prev, cur, closes):
    """比對兩份快照，逐檔 ETF 算出它自己的加減碼明細。

    回傳 {etf代碼: {"buy","sell","changed","flow":[{code,name,delta_shares,amount}]}}
    不做跨 ETF 彙總——涵蓋率不足時彙總數字會誤導（看起來像全市場結論，其實漏一大半）。
    """
    prev_etfs = prev.get("etfs", {})
    out = {}

    for etf, info in cur.get("etfs", {}).items():
        before = (prev_etfs.get(etf) or {}).get("holdings", {})
        after  = info.get("holdings", {})
        if not before:
            continue                          # 沒有前一份可比就跳過這檔
        rows = []
        for code in set(before) | set(after):
            b = (before.get(code) or {}).get("shares", 0)
            a = (after.get(code) or {}).get("shares", 0)
            d = a - b
            if not d:
                continue
            price = closes.get(code)
            if not price:
                continue                      # 查不到收盤價就不硬算金額
            rows.append({
                "code": code,
                "name": (after.get(code) or before.get(code) or {}).get("name", ""),
                "delta_shares": d,
                "amount": round(d * price, 0),
            })
        rows.sort(key=lambda x: -abs(x["amount"]))
        out[etf] = {
            "buy":     round(sum(r["amount"] for r in rows if r["amount"] > 0), 0),
            "sell":    round(sum(r["amount"] for r in rows if r["amount"] < 0), 0),
            "changed": len(rows),
            "flow":    rows,
        }
    return out


def main():
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    today  = now_tw.date()

    etfs = {}
    for fn in ADAPTERS:
        try:
            etfs.update(fn(today))
        except Exception as e:
            print(f"[WARN] {fn.__name__} 整支失敗: {e}")

    if not etfs:
        print("[ABORT] 所有 adapter 都沒抓到資料，保留既有檔案不覆蓋")
        return 1

    price_date, closes = fetch_twse_closes()
    snapshot = {
        "snapshot_date": today.strftime("%Y-%m-%d"),
        "price_date": price_date,
        "etfs": etfs,
    }

    prev = load_json(SNAPSHOT)

    # 沒有前次快照時，向支援歷史查詢的投信回補前一交易日，
    # 這樣第一次執行就算得出買賣超，不用空等一天。
    if not prev:
        d = today - datetime.timedelta(days=1)
        while d.weekday() >= 5:
            d -= datetime.timedelta(days=1)
        print(f"[BOOTSTRAP] 無前次快照，回補 {d} 的 PCF")
        back = {}
        for fn in ADAPTERS:
            try:
                back.update(fn(d, specific=True))
            except Exception as e:
                print(f"[WARN] {fn.__name__} 回補失敗: {e}")
        if back:
            prev = {"snapshot_date": d.strftime("%Y-%m-%d"), "etfs": back}
        else:
            print("[BOOTSTRAP] 沒有投信支援歷史查詢，只能等下一個交易日")

    flows, basis = {}, None
    if prev and prev.get("snapshot_date") != snapshot["snapshot_date"]:
        flows = build_flow(prev, snapshot, closes)
        basis = prev.get("snapshot_date")
    elif prev:
        print(f"[SKIP] 快照日期與上次相同（{prev.get('snapshot_date')}），沿用既有結果")
        old = load_json(OUT) or {}
        basis = old.get("basis_date")
        flows = {k: {kk: v[kk] for kk in ("buy", "sell", "changed", "flow")}
                 for k, v in (old.get("etfs") or {}).items() if "flow" in v}
    else:
        print("[INIT] 第一次執行，只存快照；要等下一個交易日才算得出加減碼")

    out_etfs = {}
    for code, info in etfs.items():
        row = {"name": info["name"], "issuer": info["issuer"],
               "holdings": len(info["holdings"]),
               # comparable=False：這檔還沒有前一份快照可比（例如永豐沒有歷史查詢，
               # 要等下一個交易日）。前端要跟「今天真的沒調整」分開顯示。
               "comparable": code in flows}
        row.update(flows.get(code, {"buy": 0, "sell": 0, "changed": 0, "flow": []}))
        out_etfs[code] = row

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "updated":    now_tw.strftime("%Y-%m-%d %H:%M"),
            "data_date":  snapshot["snapshot_date"],
            "basis_date": basis,
            "price_date": price_date,
            "note":       "加減碼以兩份公開 PCF 快照相減推估，不等同基金實際成交",
            "etfs":       out_etfs,
        }, f, ensure_ascii=False, indent=2)

    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print("")
    for code, r in sorted(out_etfs.items()):
        print(f"[OK] {code} {r['name']}：持股 {r['holdings']} 檔、異動 {r['changed']} 檔"
              f"、加碼 {r['buy']/1e8:.1f} 億／減碼 {r['sell']/1e8:.1f} 億")
    return 0


if __name__ == "__main__":
    sys.exit(main())
