"""
scripts/daily_check.py
每日收盤後驗證 market.json 資料品質，有異常發 LINE Notify。
自動修正：TWSE 官方新配息金額 vs 儲存 avg 差 >15% → 更新 dividend_info.json
"""
import json, os, sys, urllib.request, urllib.parse
from pathlib import Path

ROOT        = Path(__file__).parent.parent
MARKET      = ROOT / "data" / "market.json"
DIV_INFO    = ROOT / "data" / "dividend_info.json"
DIV_CAL     = ROOT / "data" / "dividend_calendar.json"

LAZY_WATCHLIST = {
    '0050','0056','006208',
    '00878','00919','00929','00940','00939',
    '00936','00930','00932',
    '00713','00701','00850','00757',
    '00646','00662',
    '00679B','00687B','00772B',
    '00403A',
}

FREQ_MULT = {"月配":12,"雙月配":6,"季配":4,"半年配":2,"年配":1,"不配息":0}

LINE_TOKEN = os.environ.get("LINE_NOTIFY_TOKEN","")


def notify(msg: str):
    """發 LINE Notify，沒有 token 就印到 stdout。"""
    print(f"[NOTIFY] {msg}")
    if not LINE_TOKEN:
        return
    try:
        data = urllib.parse.urlencode({"message": f"\n{msg}"}).encode()
        req  = urllib.request.Request(
            "https://notify-api.line.me/api/notify",
            data=data,
            headers={"Authorization": f"Bearer {LINE_TOKEN}"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[NOTIFY ERROR] {e}", file=sys.stderr)


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main():
    market   = load(MARKET)
    div_info = load(DIV_INFO)
    div_cal  = load(DIV_CAL)

    if not market or not div_info:
        notify("⚠ ETF健診：market.json 或 dividend_info.json 讀取失敗")
        return

    etfs     = market.get("etfs", [])
    info_map = div_info.get("etfs", {})
    cal_map  = (div_cal or {}).get("etfs", {})

    issues   = []
    updated  = []  # avg 自動更新的紀錄

    for e in etfs:
        code = e.get("code","")
        if code not in LAZY_WATCHLIST:
            continue

        name  = e.get("name", code)
        price = e.get("price", 0)
        yld   = e.get("yld",   0)

        # ── 1. 價格異常 ──
        if price <= 0:
            issues.append(f"• {code} {name}：現價為 0，資料抓取失敗")
            continue

        # ── 2. 殖利率 >15%（防呆已攔截多數，這是最後防線）──
        if yld > 15:
            issues.append(f"• {code} {name}：殖利率 {yld}% 異常（>15%）")

        # ── 3. TWSE 官方最新配息 vs 儲存 avg，差 >15% → 自動更新 ──
        cal = cal_map.get(code)
        info = info_map.get(code, {})
        stored_avg = info.get("avg_dividend_per_share")

        if cal and stored_avg and stored_avg > 0:
            official_amt = cal.get("amount", 0)
            if official_amt > 0:
                diff = abs(official_amt - stored_avg) / stored_avg
                if diff > 0.15:
                    # 自動更新
                    info_map[code]["avg_dividend_per_share"] = official_amt
                    updated.append(
                        f"• {code} {name}：avg {stored_avg}→{official_amt}"
                        f"（TWSE官方公告，差{diff*100:.0f}%）"
                    )

    # ── 儲存自動更新 ──
    if updated:
        div_info["etfs"] = info_map
        with open(DIV_INFO, "w", encoding="utf-8") as f:
            json.dump(div_info, f, ensure_ascii=False, indent=2)
        print(f"[AUTO-FIX] 更新 {len(updated)} 支 avg")

    # ── 發通知 ──
    lines = []
    if issues:
        lines.append("🚨 ETF健診 資料異常")
        lines.extend(issues)
    if updated:
        lines.append("✅ ETF健診 avg 自動更新")
        lines.extend(updated)

    if lines:
        notify("\n".join(lines))
    else:
        print("[OK] 所有 LAZY_WATCHLIST ETF 資料正常")


if __name__ == "__main__":
    main()
