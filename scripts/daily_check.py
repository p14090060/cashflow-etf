"""
scripts/daily_check.py
每日收盤後驗證 market.json 資料品質，有異常發 Telegram 通知。
自動修正：TWSE 官方新配息金額 vs 儲存 avg 差 >15% → 更新 dividend_info.json
"""
import ast, datetime, json, os, re, sys, time, urllib.request
from pathlib import Path

# Windows 本機主控台常是 cp950，print() 遇到 emoji/特殊符號會 UnicodeEncodeError 整支腳本崩潰
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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


FETCH_ETF          = ROOT / "fetch_etf.py"
STALE_PENDING_DAYS = 90

ACTIVE_FLOW      = ROOT / "data" / "active_flow.json"
ACTIVE_MIN_ETFS  = 26    # 目前接 31 檔；本次實抓掉到 26 以下 = 約兩家投信的 adapter 壞了
                         # （少 3 檔以內由下面的 kept 檢查負責，這條是整批掛掉的後盾）
ACTIVE_STALE_ALL = 4     # 全部 ETF 的最新資料日都超過這天數 → 整條抓取停擺
ACTIVE_STALE_ONE = 7     # 單一 ETF 資料日落後這麼多天 → 那家投信可能改版或擋我們
# 「本次抓不到（fetched=False）」而且資料已經舊了，性質跟「投信公告慢」完全不同：
# 前者是我們這邊回空，門檻要嚴很多。base 取的是最後一個交易日而不是今天，
# 放假不會把 lag 撐大，所以不必為了連假留寬容。
# 2026-10-02 用 git 回放 34 個 active_flow.json 版本校準：門檻 2/3/4 結果一模一樣
# （00996A 13 次、00997A 1 次），全是真的斷線，零誤報，取最寬的 4。
ACTIVE_DEAD_ONE  = 4
ACTIVE_NO_CHANGE = 21    # 資料日持續前進、卻這麼多天沒記錄到任何換股 → 值得看一眼。
                         # 主動式 ETF 三週不動有可能（富邦 00405A 就真的沒動），
                         # 所以這條是提醒不是錯誤；真正的 bug 由 anomaly 那條精準抓。


def check_active_flow() -> list:
    """主動式 ETF 持股資料的健康檢查。

    fetch.yml 裡這個步驟是 continue-on-error，抓取整個失敗也不會讓 workflow 紅燈；
    加上 PCF 本來就有 1~2 天公告延遲，「數字沒動」看起來很正常——沒有這個檢查，
    投信改版或擋 IP 會完全靜默，只能等人察覺。這是本專案反覆出現的失效模式。
    """
    issues = []
    data = load(ACTIVE_FLOW)
    if not data:
        return ["• active_flow.json 讀取失敗或不存在"]

    etfs = data.get("etfs") or {}
    # 只算「本次真的抓到」的。輸出會保留抓不到的 ETF（fetched:false）避免它從畫面
    # 消失，所以 len(etfs) 只增不減——拿總數當警戒線的話，全部投信掛掉也不會叫。
    live = [c for c, e in etfs.items() if e.get("fetched") is not False]
    if len(live) < ACTIVE_MIN_ETFS:
        issues.append(f"• 主動式 ETF 本次只抓到 {len(live)} 檔（低於 {ACTIVE_MIN_ETFS}，"
                      f"檔案共 {len(etfs)} 檔），可能有投信 adapter 壞了")

    # 本次沒抓到、沿用舊資料的（fetch_active_etf 會標 fetched:false）
    # 門檻 3 是「一次掉一批」的訊號，單檔偶爾回空很常見（連假、投信晚公告）。
    # ⚠ 但單檔**一直**回空就是壞了，這條完全看不到：2026-09-28~10-02 的 00996A
    #   連續 18 次排程沒抓到，kept 始終是 1，所有監控全綠，是使用者自己發現的。
    #   那個缺口現在由下面的 ACTIVE_DEAD_ONE 補，這裡維持只管「一次掉一批」。
    kept = [c for c, e in etfs.items() if e.get("fetched") is False]
    if len(kept) >= 3:
        issues.append(f"• 有 {len(kept)} 檔本次沒抓到，沿用舊資料：{'、'.join(sorted(kept))}")

    # **基準是最後一個交易日，不是日曆上的今天**。國定假日（如 2026-09-25 中秋）
    # 和週末不會有新的 PCF，用 today 比會在每個連假都誤報一次「資料停更」。
    # twse_price_check_date 由 fetch_etf.py 寫入，是 TWSE 實際有行情的那天。
    mkt = load(MARKET) or {}
    raw = str(mkt.get("twse_price_check_date") or "")
    try:
        base = datetime.datetime.strptime(raw, "%Y%m%d").date()
    except ValueError:
        base = datetime.date.today()      # 抓不到就退回今天，寧可誤報也不要漏報

    dates = {}
    for code, e in etfs.items():
        try:
            dates[code] = datetime.date.fromisoformat(str(e.get("data_date")))
        except (TypeError, ValueError):
            issues.append(f"• {code} {e.get('name','')}：沒有有效的資料日")

    if dates:
        newest = max(dates.values())
        gap = (base - newest).days
        if gap > ACTIVE_STALE_ALL:
            issues.append(f"• 主動式 ETF 全面停更：最新資料日 {newest}，"
                          f"距最後交易日 {base} 已 {gap} 天")
        else:
            # 只有個別投信落後才逐檔列，否則全面停更時會洗版
            for code, d in sorted(dates.items(), key=lambda x: x[1]):
                lag = (base - d).days
                e = etfs[code]
                dead = e.get("fetched") is False
                limit = ACTIVE_DEAD_ONE if dead else ACTIVE_STALE_ONE
                if lag > limit:
                    issues.append(
                        f"• {code} {e.get('name','')}："
                        + (f"連續抓不到，資料停在 {d}（落後最後交易日 {lag} 天）"
                           if dead else
                           f"資料日 {d} 落後最後交易日 {lag} 天")
                        + f"（{e.get('issuer','')}投信）")

    # ── A. 不變量自檢：fetch_active_etf 算出「股數有差卻沒產出異動」 ──
    # 這是精準訊號，代表異動在寫檔前被程式吃掉了，不是投信沒動。
    # 2026-09-30 抓到的 00989A（一次 37 檔全美股）就是這種，當時所有監控都顯示健康。
    for code, e in sorted(etfs.items()):
        if e.get("anomaly"):
            issues.append(f"• 🐛 {code} {e.get('name','')}：{e['anomaly']}")

    # ── B. 廣角網：資料日一直前進，卻很久沒記錄到任何換股 ──
    # 用 first_seen 扣掉「才剛開始追蹤」的，否則新接的投信會整批誤報。
    for code, e in sorted(etfs.items()):
        if e.get("fetched") is False or code not in dates:
            continue                      # 沒抓到的另有 kept 檢查負責
        if (base - dates[code]).days > ACTIVE_STALE_ONE:
            continue                      # 資料本來就停更，上面已經報過
        try:
            seen = datetime.date.fromisoformat(str(e.get("first_seen"))[:10])
        except (TypeError, ValueError):
            continue                      # 沒有追蹤起點就無從判斷，寧可不報
        last = e.get("last_change_date")
        try:
            since = datetime.date.fromisoformat(str(last)[:10]) if last else seen
        except ValueError:
            since = seen
        quiet = (base - since).days
        if quiet > ACTIVE_NO_CHANGE:
            what = f"最後換股 {last}" if last else f"自 {seen} 開始追蹤以來從未換股"
            issues.append(f"• {code} {e.get('name','')}：{what}，已 {quiet} 天"
                          f"（資料日 {dates[code]} 仍正常更新，請確認不是又被吃掉）")
    return issues


def check_stale_pending() -> list:
    """_YLD_PENDING 是人工維護、不會自動清除的清單，放著沒人複查就會一直顯示
    「待公告」——2026-09-23 就發現有 8 支滿 1 歲、最久 2.2 年沒人回頭查。
    這裡挑出超過 STALE_PENDING_DAYS 天沒複查的，提醒去查是不是已經開始配息。

    _YLD_PENDING 是 {代碼: "最後查證日"} 的 dict 字面值，直接從原始碼取出後用
    ast.literal_eval 解析（不 import fetch_etf，那支在 import 時就會打 TWSE API）。
    解析失敗就安靜跳過，寧可不提醒也不要誤報。
    """
    try:
        src = FETCH_ETF.read_text(encoding="utf-8")
        m = re.search(r"_YLD_PENDING\s*=\s*(\{.*?\n\})", src, re.S)
        if not m:
            return []
        pending = ast.literal_eval(m.group(1))
        if not isinstance(pending, dict):
            return []                      # 還是舊的 set 格式，沒有日期可判
    except Exception as e:
        print(f"[WARN] _YLD_PENDING 解析失敗，跳過逾期檢查: {e}")
        return []

    today, out = datetime.date.today(), []
    for code, checked in pending.items():
        try:
            d = datetime.date.fromisoformat(str(checked))
        except ValueError:
            continue
        days = (today - d).days
        if days > STALE_PENDING_DAYS:
            out.append((days, f"• {code}：已 {days} 天未複查（上次 {checked}）"))
    out.sort(reverse=True)
    return [t for _, t in out]


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
    # ⚠ 以前這裡看檔案 mtime，在 GitHub Actions 上**永遠不會觸發**：
    #   git 不保存 mtime，每次 actions/checkout 拿到的都是「剛剛」。
    #   這條是專門要抓「整條 pipeline 掛掉」的守門員，結果它自己在 CI 是瞎的。
    #   改看 market.json 裡的 updated 欄位（mis_fetcher 寫入，台北時間）。
    #   2026-09-30 實測：mtime 09-30 01:03，updated 09-29 21:52，差 3 小時。
    if not MARKET.exists():
        notify("🚨 market.json 不存在，請確認 Action 是否正常執行")
        return
    stamp = str((load(MARKET) or {}).get("updated") or "")
    age_hours = None
    try:
        # updated 是台北時間，CI 跑在 UTC，比較前要對齊時區
        wrote = datetime.datetime.strptime(stamp[:16], "%Y-%m-%d %H:%M")
        now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        age_hours = (now_tw.replace(tzinfo=None) - wrote).total_seconds() / 3600
    except ValueError:
        # 讀不到就退回 mtime，本機仍然準；CI 上等於不檢查，但至少不會誤報
        age_hours = (time.time() - MARKET.stat().st_mtime) / 3600
        print(f"[WARN] market.json 沒有可解析的 updated（{stamp!r}），退回用 mtime")
    if age_hours > 30:
        notify(f"🚨 market.json 資料過期（updated={stamp}，已 {age_hours:.0f} 小時未更新），"
               f"Action 可能執行失敗")
        return

    market   = load(MARKET)
    div_info = load(DIV_INFO)
    div_cal  = load(DIV_CAL)

    if not market or not div_info:
        notify("⚠ ETF存股雷達：market.json 或 dividend_info.json 讀取失敗")
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
        notify("⚠ ETF存股雷達：本次 fetch_etf.py 未能取得 TWSE 官方收盤核對來源，\n"
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
        # 00403A 長期處於 cheap 訊號每天狂發通知，2026-07-21 Gavin 要求靜音（其他檢查仍照常）
        if e.get("signal") == "cheap" and code != "00403A":
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

    # ── _YLD_PENDING 逾期未複查 ──
    stale = check_stale_pending()

    # ── 主動式 ETF 持股資料健康檢查 ──
    active_issues = check_active_flow()

    # ── 發通知 ──
    lines = []
    if issues:
        lines.append("🚨 ETF存股雷達 資料異常")
        lines.extend(issues)
    if updated:
        lines.append("✅ ETF存股雷達 avg 自動更新")
        lines.extend(updated)
    if cheap_alerts:
        lines.append("💚 監控清單 便宜訊號")
        lines.extend(cheap_alerts)
    if active_issues:
        lines.append("📉 主動式 ETF 持股資料異常")
        lines.extend(active_issues)
    if stale:
        lines.append(f"⏰ 待公告 ETF 逾 {STALE_PENDING_DAYS} 天未複查（查到已配息就從 _YLD_PENDING 移除）")
        lines.extend(stale)
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
