"""收盤成交量前 100 名（與網站排行同一規則）— CLOSE_TOP100_RECOVERY（2026-11-12）。

權威是 js/rank.js 的 rankVolState()＋renderRank()：本檔逐行移植，不另立公式。
  - 就緒：updated 有效；新格式（quote_src）只認該交易日（ready 中最大的 quote_date）MIS 盤中 09:00–13:30
    或官方收盤（TWSE_MI_INDEX／TPEX_OTC）；舊格式只認 mis_time。cur_vol 須有限非負。
  - 排序：就緒且 cur_vol>0 且 price>0 的不足 100 → 改用就緒且 price>0（零量補位）；cur_vol 降冪、avg_vol 降冪；
    同值保持原陣列順序（JS Array.sort 穩定）；最多 100。不依 heat。
收盤確認（R1，無容忍值）：榜上每一檔都必須是同一交易日 T 的官方收盤（不是 MIS／yfinance／舊日），
且全體沒有任何未就緒（成交量未確認者可能屬於前 100，順位無法證明）。任一不成立 → 只是「暫定榜」：
可用於補查優先次序，但不是已確認收盤榜、不寫紀錄、不計完成輪。排名本身一律照網站規則，不排除商品湊 100。
兩個來源，結果必須與網站最終收盤榜相同：
  market：data/market.json 本身已是官方收盤（隔日 09:00 或更晚的 daily）。
  base  ：15:00 fetch 的 daily 在 MIS writer 之前執行；此時 _base.json 已有當日官方收盤，
          依 mis_fetcher 非盤中合併規則（①官方有成交 ①'官方無成交 ③上一份較新 ④基線）推出 writer 稍後會寫出的列。
          tests/test_close_top100_recovery.py 以真 mis_fetcher＋真 Chrome renderRank 逐代號／次序比對。
只讀檔、不連網、不寫檔。
"""
import hashlib
import json
import math
import re

OFFICIAL = ("TWSE_MI_INDEX", "TPEX_OTC")
_HM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _iso(s):
    import datetime
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return s if datetime.date.fromisoformat(s).isoformat() == s else None
    except ValueError:
        return None


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _js_num(v):
    """JS `(x || 0)` 於數值欄的效果：非數字／NaN／0 → 0。"""
    return v if _num(v) else 0


def rank_state(etfs, updated, is_holiday):
    """rank.js rankVolState 的移植。回傳 {valid, day, ready:set, pending}。"""
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", str(updated or ""))
    up_day = _iso(m.group(1)) if m else None
    up_hm = m.group(2) if (m and _HM.fullmatch(m.group(2))) else None
    valid = bool(up_day and up_hm)
    holiday = is_holiday is True
    sess = lambda t: isinstance(t, str) and bool(_HM.fullmatch(t)) and "09:00" <= t <= "13:30"
    rows = [e for e in (etfs if isinstance(etfs, list) else []) if isinstance(e, dict)]
    day, new_fmt = None, False
    for e in rows:
        if e.get("quote_src") is None:
            continue
        new_fmt = True
        qd = _iso(e.get("quote_date"))
        if valid and qd and qd <= up_day and (e["quote_src"] == "MIS" or e["quote_src"] in OFFICIAL) and (not day or qd > day):
            day = qd
    ready = set()
    if valid:
        for e in rows:
            cv = e.get("cur_vol")
            if not (_num(cv) and cv >= 0):
                continue
            ok = False
            if e.get("quote_src") is not None:
                qd = _iso(e.get("quote_date"))
                if qd and qd == day:
                    if e["quote_src"] == "MIS":
                        ok = sess(e.get("mis_time")) and (qd < up_day or e["mis_time"] <= up_hm)
                    else:
                        ok = e["quote_src"] in OFFICIAL
            elif not new_fmt and sess(e.get("mis_time")):
                ok = holiday or e["mis_time"] <= up_hm
            if ok:
                ready.add(e.get("code"))
    pending = sum(1 for e in rows if _num(e.get("price")) and e["price"] > 0 and e.get("code") not in ready)
    return {"valid": valid, "day": day, "ready": ready, "pending": pending}


def rank_board(etfs, updated, is_holiday):
    """rank.js renderRank 的 sorted（最多 100）。回傳 ([列], state)。"""
    st = rank_state(etfs, updated, is_holiday)
    rows = [e for e in (etfs if isinstance(etfs, list) else []) if isinstance(e, dict)]
    pos = lambda e: _num(e.get("price")) and e["price"] > 0
    with_vol = [e for e in rows if e.get("code") in st["ready"] and _num(e.get("cur_vol")) and e["cur_vol"] > 0 and pos(e)]
    pool = with_vol if len(with_vol) >= 100 else [e for e in rows if e.get("code") in st["ready"] and pos(e)]
    ordered = sorted(pool, key=lambda e: (-_js_num(e.get("cur_vol")), -_js_num(e.get("avg_vol"))))   # sorted 穩定＝JS sort
    return ordered[:100], st


def _closing(etfs, updated, is_holiday, origin, digest, provisional=False):
    board, st = rank_board(etfs, updated, is_holiday)
    total = sum(1 for e in etfs if isinstance(e, dict))
    if not st["valid"] or not st["day"]:
        return None, "資料時間無法確認"
    if not board:
        return None, "沒有可排名的已確認成交量"
    day = st["day"]
    not_close = [e["code"] for e in board if not (e.get("quote_src") in OFFICIAL and e.get("quote_date") == day)]
    waiting = sorted(e.get("code") for e in etfs if isinstance(e, dict) and _num(e.get("price")) and e["price"] > 0
                     and e.get("code") not in st["ready"])
    why = None
    if not_close:
        why = "%s 榜上 %d 檔不是官方收盤（例：%s），尚未收盤或收盤未確認" % (day, len(not_close), ",".join(not_close[:5]))
    elif waiting:
        why = "%s 尚有 %d 檔成交量未確認（%s），最終順位無法證明，收盤資料不完整" % (day, len(waiting), ",".join(waiting[:5]))
    out = {"trade_day": day, "origin": origin, "source_sha256": digest, "codes": [e["code"] for e in board],
           "rows": {e["code"]: e for e in board}, "waiting": waiting, "not_official": not_close, "size": len(board),
           "confirmed": why is None}
    if why and not provisional:
        return None, why
    return out, why


def _sha(path):
    try:
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    except OSError:
        return None


def board_from_market(market, digest=None, provisional=False):
    if not isinstance(market, dict) or not isinstance(market.get("etfs"), list):
        return None, "market.json 讀取失敗"
    return _closing(market["etfs"], market.get("updated"), market.get("is_holiday"), "market", digest, provisional)


def _official(b):
    """mis_fetcher._official 同一規則（再驗一次型別），格式不符回 None。"""
    off = b.get("official_close")
    if not isinstance(off, dict) or not off.get("date") or off.get("src") not in OFFICIAL:
        return None
    vs = off.get("vol_shares")
    vs_ok = vs is None or (isinstance(vs, int) and not isinstance(vs, bool) and vs >= 0)
    if off.get("status") == "traded" and _num(off.get("price")) and off["price"] > 0 and vs_ok:
        return off
    if off.get("status") == "no_trade" and off.get("price") is None and vs == 0 and not isinstance(vs, bool):
        return off
    return None


def _prev_src(p):
    if not p:
        return None
    if p.get("quote_src"):
        return p["quote_src"]
    return "MIS" if p.get("mis_time") else None


def _keep_prev(p, b_qd, b_src):
    src = _prev_src(p)
    if src != "MIS" and src not in OFFICIAL:
        return False
    qd = p.get("quote_date")
    if not qd:
        return not b_qd
    if not b_qd or qd > b_qd:
        return True
    if qd < b_qd:
        return False
    return src in OFFICIAL or b_src not in OFFICIAL


def _project(b, prev, today):
    """mis_fetcher 非盤中（無 MIS）時對單檔決定的 price／cur_vol／quote_*／mis_time（只取排行需要的欄位）。"""
    e = {"code": b.get("code"), "price": b.get("price"), "cur_vol": b.get("cur_vol"), "avg_vol": b.get("avg_vol")}
    off = _official(b)
    off_today = off if off and off["date"] == today else None

    def apply_official(o):
        e["price"] = o["price"]
        if o.get("vol_shares") is not None:
            e["cur_vol"] = round(o["vol_shares"] / 1000, 1)
        else:
            e.pop("cur_vol", None)
        e.pop("mis_time", None)
        e["quote_date"], e["quote_src"] = o["date"], o["src"]

    def reference(o):
        b_qd, b_src = ((o["date"], o["src"]) if o and o["status"] == "traded"
                       else ((b["price_date"], "yfinance") if b.get("price_date") else (None, None)))
        if _keep_prev(prev, b_qd, b_src):
            for k in ("price", "cur_vol"):
                if k in prev:
                    e[k] = prev[k]
                else:
                    e.pop(k, None)
            if prev.get("mis_time"):
                e["mis_time"] = prev["mis_time"]
            else:
                e.pop("mis_time", None)
            e["quote_date"], e["quote_src"] = prev.get("quote_date"), _prev_src(prev)
        elif b_src in OFFICIAL:
            apply_official(o)
        else:
            cv = e.get("cur_vol") or 0
            if cv > 0:
                e["cur_vol"] = round(cv / 1000, 1)
            e.pop("mis_time", None)
            e["quote_date"], e["quote_src"] = b_qd, b_src

    if off_today and off_today["status"] == "traded":
        apply_official(off_today)
    elif off_today:
        reference(None)
        e.pop("mis_time", None)
        e["cur_vol"] = 0.0
    else:
        reference(off)
    return e


def board_from_base(base, prev_market, digest=None, provisional=False):
    """15:00：_base 官方收盤日 T 的全體都有官方證據時，推出 writer 稍後寫出的收盤榜。"""
    if not isinstance(base, dict) or not isinstance(base.get("etfs"), list) or not base["etfs"]:
        return None, "_base.json 讀取失敗"
    days = {(_official(b) or {}).get("date") for b in base["etfs"] if isinstance(b, dict)}
    days.discard(None)
    if not days:
        return None, "_base.json 沒有官方收盤證據"
    today = max(d for d in days if _iso(d))
    prev = {e.get("code"): e for e in ((prev_market or {}).get("etfs") or []) if isinstance(e, dict)}
    rows = [_project(b, prev.get(b.get("code")), today) for b in base["etfs"] if isinstance(b, dict)]
    return _closing(rows, today + " 23:59", False, "base", digest, provisional)


def closing_board(root):
    """回傳 (已確認收盤榜 或 None, 說明, 暫定榜 或 None)。
    已確認：兩來源中交易日較新者；同日時兩者都須確認且代號次序相同（以 market 為準）。
    暫定榜：資料不齊時網站同規則的榜（只供補查優先次序與輪數去重的交易日識別，不寫紀錄、不計完成）。"""
    from pathlib import Path
    root = Path(root)
    mk_path, base_path = root / "data" / "market.json", root / "data" / "_base.json"
    try:
        market = json.loads(mk_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        market = None
    try:
        base = json.loads(base_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        base = None
    bm, why_m = board_from_market(market, _sha(mk_path), provisional=True)
    bb, why_b = board_from_base(base, market, _sha(base_path), provisional=True)
    cands = [b for b in (bm, bb) if b]
    if not cands:
        return None, "market：%s；base：%s" % (why_m, why_b), None
    day = max(b["trade_day"] for b in cands)
    same = [b for b in cands if b["trade_day"] == day]
    prov = same[0]                                   # market 優先（網站實際檔）
    conf = [b for b in same if b["confirmed"]]
    if len(conf) == 2 and conf[0]["codes"] != conf[1]["codes"]:
        return None, "%s 兩來源推得的收盤榜不同（market %d 檔、base %d 檔），不採用" % (day, conf[0]["size"], conf[1]["size"]), prov
    if conf:
        # 15:00：同日 market 仍是盤中 MIS（未確認）、base 已由官方收盤確認 → 採 base；兩者皆確認且相同 → market
        return conf[0], conf[0]["origin"], conf[0]
    reasons = "；".join("%s：%s" % (b["origin"], w) for b, w in ((bm, why_m), (bb, why_b)) if b and b["trade_day"] == day and w)
    return None, reasons or "收盤未確認", prov


def digest_ints(hexdigest):
    """daily_state 只存數值：64 位十六進位切成 5 段（13,13,13,13,12 位），每段 < 2^52，JSON 浮點可精確保存。"""
    return {str(i): int(hexdigest[i * 13:(i + 1) * 13], 16) for i in range(5)}
