"""
scripts/daily_check.py
每日收盤後驗證 market.json 資料品質，有異常發 Telegram 通知。
自動修正：TWSE 官方新配息金額 vs 儲存 avg 差 >15% → 更新 dividend_info.json
"""
import json, os, sys, urllib.request, urllib.parse
from pathlib import Path

ROOT        = Path(__file__).parent.parent
MARKET      = ROOT / "data" / "market.json"
DIV_INFO    = ROOT / "data" / "dividend_info.json"
DIV_CAL     = ROOT / "data" / "dividend_calendar.json"
KNOWN_CODES = ROOT / "data" / "known_codes.json"

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

TG_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def notify(msg: str):
    """發 Telegram 訊息，沒有 token 就印到 stdout。"""
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


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def check_new_in_top100(etfs: list) -> list:
    """比對本次 TOP 100 與上次紀錄，回傳新進的 ETF 物件清單。"""
    top100 = sorted(
        [e for e in etfs if (e.get("cur_vol") or 0) > 0 and e.get("price", 0) > 0],
        key=lambda e: e.get("heat", 0),
        reverse=True,
    )[:100]
    current_codes = {e["code"] for e in top100}

    # 讀上次紀錄
    try:
        with open(KNOWN_CODES, encoding="utf-8") as f:
            known = set(json.load(f))
    except Exception:
        known = None  # 第一次執行，沒有基準

    # 更新紀錄
    with open(KNOWN_CODES, "w", encoding="utf-8") as f:
        json.dump(sorted(current_codes), f, ensure_ascii=False)

    if known is None:
        print("[INFO] known_codes.json 初始化完成，下次執行才開始偵測新進")
        return []

    new_codes = current_codes - known
    code_map  = {e["code"]: e for e in top100}
    return [code_map[c] for c in new_codes if c in code_map]


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

    # ── TOP 100 新進偵測 ──
    new_entries = check_new_in_top100(etfs)

    # ── 發通知 ──
    lines = []
    if issues:
        lines.append("🚨 ETF健診 資料異常")
        lines.extend(issues)
    if updated:
        lines.append("✅ ETF健診 avg 自動更新")
        lines.extend(updated)
    if new_entries:
        lines.append("🆕 新進成交量 TOP 100")
        for e in new_entries:
            sig  = {"cheap":"便宜","fair":"合理","hot":"過熱","dear":"偏貴"}.get(e.get("signal",""), "?")
            yld  = e.get("yld", 0)
            ystr = f"殖利率 {yld}%" if yld else "無殖利率紀錄"
            lines.append(f"• {e['code']} {e.get('name','')} · {sig} · {ystr}")

    if lines:
        notify("\n".join(lines))
    else:
        print("[OK] 所有 LAZY_WATCHLIST ETF 資料正常，TOP 100 無新進")


if __name__ == "__main__":
    main()
