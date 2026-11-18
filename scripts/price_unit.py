"""價格／歷史「單位一致性」保護（2026-11-17，00662 1拆5 復牌 incident；11-18 R1 收窄為已核官方事件）。

背景：Yahoo 對 00662 的一年日線同時混有拆分前（~118）與拆分後（~23）量級，生效日之前就已出現拆後量級、
停牌日是 0 量平盤列、沒有 splits 事件、Adj Close 也沒正規化。用這種序列算 ma60／52 週／報酬，
會得到「現價 23、60MA 121、跌 81%、便宜」這種假訊號。

範圍（R1 F3）：只處理 EVENTS 內「有官方事故證據」的代號與期間。不是全池數值政策——非事件代號即使同單位
連續大漲、價格／MA ≥ 1.8，也完全不介入（不清空指標）。通用分割偵測若要做須另案。

原則（不猜、不補）：
- 不依日期把舊價一律除以比例（會把已調整的列再除一次），也不逐列猜哪一筆是哪個單位。
- 事件代號在事件期間內，只「偵測」單位不一致：相鄰正收盤價比值 ≥ UNIT_JUMP（任一方向），或最終價格與
  歷史最後一筆／60MA／基線價格相差 ≥ UNIT_JUMP 倍。停牌 0 量列的沿用價也參與。
- 偵測到就把依歷史計算的指標與訊號如實設為 null，並標 price_unit_status＝"unverified"（待確認）。
  價格本身（官方收盤／MIS）與殖利率公式都不動。
- 沒有偵測到（來源已整段調整成同一單位）→ 完全不介入，照原公式計算（標記自然移除＝恢復）。
- 資料契約（狀態值、斷點日期、必要 null）由 json_safe 共用檢查，原 Gate 會拒絕壞狀態。
"""
import datetime
import math

from json_safe import PRICE_UNIT_UNVERIFIED as UNVERIFIED, PRICE_UNIT_BASE_NULL, PRICE_UNIT_MARKET_NULL

UNIT_JUMP = 1.8

# 已核官方事件（唯一適用範圍）。window：停牌起日～復牌後 400 天（一年日線視窗＋緩衝）；期間外不介入。
EVENTS = {
    "00662": {
        "kind": "split", "ratio": 5, "halt_from": "2026-11-11", "resume": "2026-11-17",
        "sources": [
            # 證據：etf/evidence/operational-followup/2026-11-16/00662-official/
            {"url": "https://www.twse.com.tw/zh/ETFortune/announcement?company=A00010&date=20261112&fund=00662&seq=1&type=value",
             "sha256": "73b34801dcc159131486856fe7c8a90c125ad684be0b3779e244c6125ffae219"},
            {"url": "https://www.fubon.com/financialholdings/news/news_1261106_958650.htm",
             "sha256": "3f8c2ae2760b34e1be8d6329cb7fa3954b1efca157cc63ed53678932800b5c34"},
        ],
    },
}
_WINDOW_DAYS = 400

# 相容舊名（測試／呼叫端）
BASE_NULL = tuple(k for k in PRICE_UNIT_BASE_NULL)
MARKET_NULL = tuple(k for k in PRICE_UNIT_MARKET_NULL)


def _iso(d):
    if d is None:
        return None
    if isinstance(d, datetime.datetime):
        d = d.date()
    return d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]


def event_active(code, as_of=None):
    """代號是否有已核官方事件，且 as_of（日期或 ISO）在事件期間內；as_of=None 只看代號。"""
    ev = EVENTS.get(code)
    if ev is None:
        return False
    if as_of is None:
        return True
    a = _iso(as_of)
    end = (datetime.date.fromisoformat(ev["resume"]) + datetime.timedelta(days=_WINDOW_DAYS)).isoformat()
    return ev["halt_from"] <= a <= end


def _pos(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def jump(a, b):
    """兩個正價格是否相差 ≥ UNIT_JUMP 倍（任一方向）。非正／非有限 → False（無從判斷，不當證據）。"""
    if not (_pos(a) and _pos(b)):
        return False
    r = a / b
    return r >= UNIT_JUMP or r <= 1 / UNIT_JUMP


def history_unit_break(rows):
    """rows：依日期排序的 (日期, 收盤, 成交量)。回傳最後一個單位斷點的日期，沒有則 None。"""
    last, brk = None, None
    for d, close, vol in rows:
        if not _pos(close):
            continue
        if last is not None and jump(close, last):
            brk = d
        last = close
    return brk


def base_problem(code, rows, price, ma60, as_of=None):
    """fetch_etf 用：回傳 (是否單位待確認, 斷點日期或 None)。非事件代號／事件期間外 → (False, None)。"""
    if not event_active(code, as_of):
        return False, None
    brk = history_unit_break(rows)
    if brk is not None:
        return True, brk
    traded = [c for _, c, _v in rows if _pos(c)]
    if traded and jump(price, traded[-1]):
        return True, None                 # 官方現價與歷史最後一筆成交價單位不同（來源尚未反映拆分）
    if jump(price, ma60):
        return True, None
    return False, None


def apply_base(row, problem, brk):
    """把 fetch_etf 的一列標成單位待確認（就地）。"""
    if not problem:
        return row
    for k in PRICE_UNIT_BASE_NULL:
        row[k] = None
    row["ret_months"] = [None] * 6
    row["price_unit_status"] = UNVERIFIED
    row["price_unit_break"] = _iso(brk)
    return row


def market_problem(e, b, as_of=None):
    """mis_fetcher 用：基線已標待確認 → True；否則只有事件代號（期間內）才比較最終價格與基線 60MA／價格。"""
    if b.get("price_unit_status") == UNVERIFIED:
        return True
    if not event_active(e.get("code") or b.get("code"), as_of):
        return False
    p = e.get("price")
    return jump(p, b.get("ma60")) or jump(p, b.get("price"))


def apply_market(e):
    for k in PRICE_UNIT_MARKET_NULL:
        e[k] = None
    e["ret_months"] = [None] * 6
    e["price_unit_status"] = UNVERIFIED
    return e
