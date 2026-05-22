"""
scripts/intraday_notify.py
盤中固定時間點發送 LAZY_WATCHLIST 便宜訊號快照。
由 update-data.yml 每 10 分鐘呼叫，腳本自行判斷是否在通知時間點。

台北通知時間：09:10, 10:00, 11:00, 12:00, 13:00
對應 UTC：    01:10, 02:00, 03:00, 04:00, 05:00
"""
import json, os, sys, urllib.request, datetime
from pathlib import Path

ROOT   = Path(__file__).parent.parent
MARKET = ROOT / "data" / "market.json"

# (UTC hour, UTC minute, 台北時間標籤)
NOTIFY_SLOTS = [
    (1, 10, "09:10"),
    (2,  0, "10:00"),
    (3,  0, "11:00"),
    (4,  0, "12:00"),
    (5,  0, "13:00"),
]
WINDOW_MIN = 6  # ±6 分鐘容許誤差（配合每 10 分鐘排程）

LAZY_WATCHLIST = {
    '0050','0056','006208',
    '00878','00919','00929','00940','00939',
    '00936','00930','00932',
    '00713','00701','00850','00757',
    '00646','00662',
    '00679B','00687B','00772B',
    '00403A',
}

TG_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def notify(msg: str):
    print(f"[NOTIFY] {msg}")
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": msg}).encode()
        req  = urllib.request.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[NOTIFY ERROR] {e}", file=sys.stderr)


def current_slot():
    now = datetime.datetime.utcnow()
    for h, m, label in NOTIFY_SLOTS:
        target_min = h * 60 + m
        now_min    = now.hour * 60 + now.minute
        if abs(now_min - target_min) <= WINDOW_MIN:
            return label
    return None


def main():
    slot = current_slot()
    if not slot:
        print("[SKIP] 非通知時間點")
        return

    try:
        with open(MARKET, encoding="utf-8") as f:
            market = json.load(f)
    except Exception:
        print("[ERROR] 無法讀取 market.json")
        return

    etfs = market.get("etfs", [])

    SIG = {"cheap": "便宜", "fair": "合理✓", "hot": "過熱", "dear": "偏貴"}

    cheap = []
    for e in etfs:
        if e.get("code") not in LAZY_WATCHLIST:
            continue
        if e.get("signal") != "cheap":
            continue
        code  = e["code"]
        name  = e.get("name", code)
        price = e.get("price", 0)
        yld   = e.get("yld", 0)
        days  = e.get("days")
        ystr  = f"殖利率 {yld}%" if yld else "殖利率 --"
        dstr  = f"，{days} 天後配息" if days is not None and days <= 30 else ""
        cheap.append(f"• {code} {name}  現價 {price}  {ystr}{dstr}")

    if not cheap:
        print(f"[{slot}] 監控清單無便宜訊號，略過通知")
        return

    lines = [f"💚 [{slot}] 監控清單 便宜訊號"] + cheap
    lines.append("⚠ 訊號僅供參考，非買賣建議")
    notify("\n".join(lines))


if __name__ == "__main__":
    main()
