"""
scripts/daily_check.py
每日收盤後驗證 market.json 資料品質，有異常發 Telegram 通知。
自動修正：TWSE 官方新配息金額 vs 儲存 avg 差 >15% → 更新 dividend_info.json
"""
import json, os, sys, time, urllib.request
from pathlib import Path

ROOT        = Path(__file__).parent.parent
MARKET      = ROOT / "data" / "market.json"
DIV_INFO    = ROOT / "data" / "dividend_info.json"
DIV_CAL     = ROOT / "data" / "dividend_calendar.json"
KNOWN_CODES = ROOT / "data" / "known_codes.json"
DAILY_STATE = ROOT / "data" / "daily_state.json"

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


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def check_new_in_top100(etfs: list) -> list:
    top100 = sorted(
        [e for e in etfs if (e.get("cur_vol") or 0) > 0 and e.get("price", 0) > 0],
        key=lambda e: e.get("heat", 0),
        reverse=True,
    )[:100]
    current_codes = {e["code"] for e in top100}

    try:
        with open(KNOWN_CODES, encoding="utf-8") as f:
            known = set(json.load(f))
    except Exception:
        known = None

    save_json(KNOWN_CODES, sorted(current_codes))

    if known is None:
        print("[INFO] known_codes.json 初始化完成，下次執行才開始偵測新進")
        return []

    new_codes = current_codes - known
    code_map  = {e["code"]: e for e in top100}
    return [code_map[c] for c in new_codes if c in code_map]


def main():
    # ── 0. market.json 過期檢查（30 小時）──
    if MARKET.exists():
        age_hours = (time.time() - MARKET.stat().st_mtime) / 3600
        if age_hours > 30:
            notify(f"🚨 market.json 資料過期（已 {age_hours:.0f} 小時未更新），Action 可能執行失敗")
            return
    else:
        notify("🚨 market.json 不存在，請確認 Action 是否正常執行")
        return

    market   = load(MARKET)
    div_info = load(DIV_INFO)
    div_cal  = load(DIV_CAL)

    if not market or not div_info:
        notify("⚠ ETF健診：market.json 或 dividend_info.json 讀取失敗")
        return

    etfs     = market.get("etfs", [])
    info_map = div_info.get("etfs", {})
    cal_map  = (div_cal or {}).get("etfs", {})

    # ── 0b. ETF 筆數異常（TWSE ISIN 抓取失敗時縮水到精選清單 13 支）──
    if len(etfs) < 50:
        notify(f"🚨 ETF清單異常：market.json 只有 {len(etfs)} 支（正常應 >100），\n"
               f"TWSE ISIN 頁面可能抓取失敗，_base.json 已 fallback，請確認")

    # ── 0c. TWSE 官方收盤核對來源抓取失敗（price 僅靠 yfinance，可能有整批 NaN 延遲風險）──
    if not market.get("twse_price_check_date"):
        notify("⚠ ETF健診：本次 fetch_etf.py 未能取得 TWSE 官方收盤核對來源，\n"
               "price 僅來自 yfinance，若當天 yfinance 剛好整批延遲/NaN 將無法自動修正，請人工確認現價")

    # ── 載入跨日狀態 ──
    state      = load(DAILY_STATE) or {}
    yld_prev   = state.get("yld_prev", {})
    vol_streak = state.get("zero_vol_streak", {})

    issues        = []
    updated       = []
    cheap_alerts  = []
    div_alerts    = []

    # ── 1. 報酬率異常（台股 AI 行情 100-230% 屬正常，門檻設 300%）──
    for e in etfs:
        ret1y = e.get("ret1y")
        new_listing = e.get("new_listing", False)
        if ret1y is not None and abs(ret1y) > 300:
            issues.append(
                f"• {e['code']} {e.get('name','')}：近1年報酬 {ret1y:+.1f}%，"
                f"數值異常（>300%），疑似拆分未修正，請人工確認"
            )
        elif ret1y is None and not new_listing:
            issues.append(
                f"• {e['code']} {e.get('name','')}：近1年報酬無法計算（非新上市），"
                f"疑似資料抓取失敗或拆分問題，請確認"
            )

    # ── 2-6. LAZY_WATCHLIST 各項檢查 ──
    for e in etfs:
        code    = e.get("code", "")
        name    = e.get("name", code)
        price   = e.get("price", 0)
        yld     = e.get("yld", 0)
        cur_vol = e.get("cur_vol") or 0

        # ── 3. 成交量消失連追（LAZY_WATCHLIST）──
        if code in LAZY_WATCHLIST:
            if cur_vol == 0:
                vol_streak[code] = vol_streak.get(code, 0) + 1
                if vol_streak[code] >= 3:
                    issues.append(
                        f"• {code} {name}：連續 {vol_streak[code]} 天無成交量，"
                        f"可能下市、暫停交易或資料抓取失敗"
                    )
            else:
                vol_streak[code] = 0

        if code not in LAZY_WATCHLIST:
            continue

        # ── 2. 價格異常 ──
        if price <= 0:
            issues.append(f"• {code} {name}：現價為 0，資料抓取失敗")
            continue

        # ── 殖利率 >20%（防呆，15% 以上有合法高息 ETF）──
        if yld > 20:
            issues.append(f"• {code} {name}：殖利率 {yld}% 異常（>20%）")

        # ── 2. 殖利率從有到 0 ──
        prev_yld = yld_prev.get(code, 0)
        if prev_yld > 0 and yld == 0:
            issues.append(
                f"• {code} {name}：殖利率歸零（上次 {prev_yld}%），"
                f"可能 FinMind 無資料或該檔已停止配息"
            )
        yld_prev[code] = yld

        # ── 4. 訊號變便宜 ──
        if e.get("signal") == "cheap":
            cheap_alerts.append(f"• {code} {name}：訊號轉為便宜，目前位置偏低")

        # ── 5. 配息 7 天內 ──
        days = e.get("days")
        est  = e.get("est")
        if days is not None and 0 <= days <= 7:
            est_str = f"，預估 {est:.2f} 元/張" if est else ""
            div_alerts.append(f"• {code} {name}：{days} 天後配息{est_str}")

        # ── TWSE 官方配息 vs avg 差 >15% → 自動更新 ──
        cal        = cal_map.get(code)
        info       = info_map.get(code, {})
        stored_avg = info.get("avg_dividend_per_share")
        if cal and stored_avg and stored_avg > 0:
            official_amt = cal.get("amount") or 0
            if official_amt > 0:
                diff = abs(official_amt - stored_avg) / stored_avg
                if diff > 0.15:
                    info_map[code]["avg_dividend_per_share"] = official_amt
                    updated.append(
                        f"• {code} {name}：avg {stored_avg}→{official_amt}"
                        f"（TWSE官方公告，差{diff*100:.0f}%）"
                    )

    # ── 儲存自動更新 ──
    if updated:
        div_info["etfs"] = info_map
        save_json(DIV_INFO, div_info)
        print(f"[AUTO-FIX] 更新 {len(updated)} 支 avg")

    # ── 儲存跨日狀態 ──
    state["yld_prev"]        = yld_prev
    state["zero_vol_streak"] = vol_streak
    save_json(DAILY_STATE, state)

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
    if cheap_alerts:
        lines.append("💚 監控清單 便宜訊號")
        lines.extend(cheap_alerts)
    # 新進榜只在有資料問題時通知
    problem_entries = []
    for e in new_entries:
        freq    = e.get("div_freq") or e.get("div_frequency") or ""
        no_div  = freq == "不配息"
        pending = e.get("yld_pending", False)
        is_new  = e.get("new_listing", False)
        yld     = e.get("yld", 0)
        ret1y   = e.get("ret1y", 0)
        warn = []
        if freq in ("不明", "?", ""):
            warn.append("配息方式不明")
        if not yld and not is_new and not no_div and not pending:
            warn.append("殖利率查無")
        if not ret1y and not is_new:
            warn.append("報酬率查無")
        if warn:
            problem_entries.append(
                f"• {e['code']} {e.get('name','')}：{'、'.join(warn)}"
            )
    if problem_entries:
        lines.append("🆕 新進 TOP 100 資料異常")
        lines.extend(problem_entries)

    if lines:
        notify("\n".join(lines))
    else:
        print("[OK] 所有監控 ETF 資料正常，TOP 100 無新進")


if __name__ == "__main__":
    main()
