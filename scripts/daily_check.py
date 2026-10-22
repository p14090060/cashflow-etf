"""
scripts/daily_check.py
每日收盤後驗證 market.json 資料品質，有異常發 Telegram 通知。
自動修正：TWSE 官方新配息金額 vs 儲存 avg 差 >15% → 更新 dividend_info.json
"""
import ast, datetime, json, math, os, re, sys, time, urllib.parse, urllib.request
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


def notify(msg: str) -> bool:
    """送 Telegram；API 回 ok=true 才回 True（D-071：送達確認後才記錄回執）。錯誤訊息不含 token。"""
    print(f"[NOTIFY] {msg}")
    if not TG_TOKEN or not TG_CHAT_ID:
        print("[NOTIFY FAILED] 未設定 TELEGRAM_BOT_TOKEN／TELEGRAM_CHAT_ID，訊息未發送", file=sys.stderr)
        return False
    try:
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": msg}).encode()
        req  = urllib.request.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("ok") is not True:
            raise RuntimeError("Telegram 回應失敗：%s" % body.get("error_code"))
    except Exception as e:
        print(f"[NOTIFY ERROR] {type(e).__name__}: {str(e).replace(TG_TOKEN, '***') if TG_TOKEN else e}", file=sys.stderr)
        return False
    return True


def _now():
    return time.time()


# ── D-071：配息政策缺值自動查證的跨輪狀態與求助門檻 ──
# daily_state 只放 {欄位: {代號: 數值}}（與 87176ee6 json_safe.validate_daily_state 相容）：
#   frequency_recovery 上次 TWSE 逐檔查詢 epoch；policy_status 狀態碼（official_frequency.QUEUED…NO_RESULT）；
#   policy_first 第一次「完成判讀仍無解」epoch；policy_rounds 完成判讀仍無解的輪數；policy_notified 求助確認送達 epoch。
POLICY_HELP_ROUNDS  = 3
POLICY_HELP_SECONDS = 24 * 3600
POLICY_REMIND_DAYS  = 14
POLICY_HELP_MAX     = 15
POLICY_KEYS = ("frequency_recovery", "policy_status", "policy_first", "policy_rounds", "policy_notified")
ACK = {}                 # 本輪求助訊息要求的送達回執 {"policy_notified": [代號]}
ACK_MESSAGE = [None]


def _num_map(v):
    return {c: x for c, x in (v or {}).items() if isinstance(c, str) and isinstance(x, (int, float))
            and not isinstance(x, bool) and math.isfinite(x)} if isinstance(v, dict) else {}


def update_policy_state(state, result, now):
    """依本輪查證結果更新跨輪狀態；回傳達求助門檻的代號（未在 POLICY_REMIND_DAYS 內確認送達過）。"""
    import official_frequency as of
    st = {k: _num_map(state.get(k)) for k in POLICY_KEYS}
    for c in result["twse_tried"]:
        st["frequency_recovery"][c] = now
    tracked = set(result["status"])
    for k in ("policy_status", "policy_first", "policy_rounds", "policy_notified"):
        st[k] = {c: v for c, v in st[k].items() if c in tracked}        # 已不再未知／衝突者清除
    for c, s in result["status"].items():
        if s == of.ADOPTED:
            for k in ("policy_status", "policy_first", "policy_rounds", "policy_notified"):
                st[k].pop(c, None)
            continue
        st["policy_status"][c] = s                   # R1：照實記錄本輪狀態（排隊／暫時失敗不沿用舊的無解）
        if c in result["completed"]:                 # 只有支援來源都完成判讀才算一輪；排隊／暫時失敗不算
            st["policy_first"].setdefault(c, now)
            st["policy_rounds"][c] = st["policy_rounds"].get(c, 0) + 1
    state.update(st)
    # R1：只有本輪所有適用來源都實際讀完（completed）仍無解／矛盾才可能求助；歷史輪數保留但不冒充本輪已查完
    due = [c for c, s in st["policy_status"].items()
           if c in result["completed"] and s in (of.CONFLICT, of.NO_RESULT) and st["policy_rounds"].get(c, 0) >= POLICY_HELP_ROUNDS
           and now - st["policy_first"].get(c, now) >= POLICY_HELP_SECONDS
           and now - st["policy_notified"].get(c, 0) >= POLICY_REMIND_DAYS * 86400]
    return sorted(due, key=lambda c: (st["policy_first"][c], c))


def policy_help_lines(due, result, state, names):
    """達門檻的彙整求助（工程摘要）：列已查來源／輪數／時間／缺口，不要求 PO 代查官網。列出者才要求送達回執。"""
    import official_frequency as of
    if not due:
        return []
    fmt = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone(datetime.timedelta(hours=8))).strftime("%m/%d %H:%M")
    shown = due[:POLICY_HELP_MAX]
    sitca = result["sitca"]
    out = ["🔎 配息政策自動查證仍無解（%d 檔；已跨 %d 輪、24 小時以上）" % (len(due), POLICY_HELP_ROUNDS),
           "支援的自動來源只有投信投顧公會 ETF 基本資料月報（本輪 %s，更新 %s）與 TWSE ETFortune 政策公告；"
           "其他發行人網站未自動支援，不代表所有官方皆查無。每檔列本輪實際讀過的來源" % (sitca.get("report_month") or "未取得", sitca.get("updated") or "—")]
    for c in shown:
        out.append("• %s %s：%s；本輪已查 %s；%s（完成判讀 %d 輪，首次 %s）" % (
            c, names.get(c, ""), of.STATUS_TEXT[state["policy_status"][c]], "＋".join(result["checked"].get(c) or []),
            result["detail"].get(c, ""), state["policy_rounds"][c], fmt(state["policy_first"][c])))
    if len(due) > len(shown):
        out.append("…其餘 %d 檔下輪接續列出" % (len(due) - len(shown)))
    ACK.setdefault("policy_notified", []).extend(shown)
    return out


def _apply_ack(state, ack, now=None):
    now = _now() if now is None else now
    for key, codes in ack.items():
        cur = state.get(key) if isinstance(state.get(key), dict) else {}
        cur.update({c: now for c in codes})
        state[key] = cur


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


NO_DIST = "no_distribution_this_period"


def _twse_announcement_ok(url, code: str, announced: datetime.date) -> bool:
    """TWSE e添富公告網址精確驗證：https、www.twse.com.tw、/zh/ETFortune/announcement、無 fragment，
    query 的 fund 與 date 各只有一個值，fund＝代號、date＝公告日（YYYYMMDD）。"""
    if not isinstance(url, str) or not url:
        return False
    try:
        u = urllib.parse.urlsplit(url)
        q = urllib.parse.parse_qs(u.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return False
    return (u.scheme == "https" and u.netloc == "www.twse.com.tw" and u.path == "/zh/ETFortune/announcement"
            and not u.fragment and q.get("fund") == [code] and q.get("date") == [announced.strftime("%Y%m%d")])


def no_distribution_note(code: str, info: dict, cal: dict, today: datetime.date):
    """官方確認「本期收益不分配」紀錄（dividend_info.json 的 distribution_status）。
    回傳 (說明文字, None)＝有效；(None, 原因)＝有紀錄但不能採用（缺值警報照報並附原因）；(None, None)＝沒有紀錄。
    只認格式完整、代號一致、TWSE 公告來源、評價日≤公告日≤今天、在有效期內的紀錄；
    有效期不得跨過下一次收益評價日（每年 9 月最後日曆日，即 9/30），到期就回復原缺值診斷。
    之後若出現實際配息（配息日曆有除息日晚於評價日、金額 > 0），舊的不分配紀錄不再採用。"""
    st = (info or {}).get("distribution_status")
    if st is None:
        return None, None
    if not isinstance(st, dict) or st.get("status") != NO_DIST:
        return None, "不分配紀錄格式不符"
    if st.get("code") != code:
        return None, f"不分配紀錄代號 {st.get('code')!r} 與 {code} 不符"
    try:
        val, ann, until = (datetime.date.fromisoformat(st.get(k)) for k in ("valuation_date", "announced_date", "valid_until"))
    except (TypeError, ValueError):
        return None, "不分配紀錄日期不合法"
    src = st.get("source")
    if not (isinstance(src, dict) and isinstance(src.get("name"), str) and src["name"].strip()
            and _twse_announcement_ok(src.get("url"), code, ann)):
        return None, "不分配紀錄缺少官方來源"
    if not (val <= ann <= val + datetime.timedelta(days=31)):
        return None, "不分配紀錄公告日與評價日不合理"
    if not (ann <= until < datetime.date(val.year + 1, 9, 30)):
        return None, "不分配紀錄有效期跨過下一次收益評價"
    if today < ann:
        return None, "不分配紀錄尚未生效（公告日在未來）"
    if today > until:
        return None, f"不分配紀錄已於 {until} 到期"
    if cal is not None:
        if not isinstance(cal, dict):
            return None, "配息日曆格式不合法，不採用不分配紀錄"
        try:
            ex = datetime.date.fromisoformat(cal.get("ex_dividend_date"))
        except (TypeError, ValueError):
            return None, "配息日曆日期無法比較，不採用不分配紀錄"
        if ex > val:
            amt = cal.get("amount")
            # 只有有限、非負的真數字才判斷；null／缺欄位／字串／bool／NaN／Infinity／負數 → 未知，不當 0
            if isinstance(amt, bool) or not isinstance(amt, (int, float)) or not math.isfinite(amt) or amt < 0:
                return None, f"{ex} 配息金額無法確認（{amt!r}），不採用不分配紀錄"
            if amt > 0:
                return None, f"已有 {ex} 實際配息，不分配紀錄不再適用"
    return f"本期不分配（評價日 {val}）", None


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

    # D-071：全體未知政策（不限 TOP100／新進）先自動查證；合格就同輪寫入候選，經既有發布步驟採用。
    import official_frequency
    ACK.clear()
    ACK_MESSAGE[0] = None
    now_ts = _now()
    tz8 = datetime.timezone(datetime.timedelta(hours=8))
    policy_state = load(DAILY_STATE) or {}
    recovery = official_frequency.recover_policies(
        etfs, info_map, _num_map(policy_state.get("frequency_recovery")),
        datetime.datetime.fromtimestamp(now_ts, tz8).date(), datetime.datetime.fromtimestamp(now_ts, tz8).isoformat())
    for c, s in sorted(recovery["status"].items()):
        print("[POLICY] %s %s %s" % (c, official_frequency.STATUS_TEXT[s], recovery["detail"].get(c, "")))
    print("[POLICY] SITCA %s" % json.dumps(recovery["sitca"], ensure_ascii=False))
    if recovery["adopted"]:
        div_info["etfs"] = info_map
        save_json(DIV_INFO, div_info)
        print("[AUTO-RECOVERY] official policy adopted: " + ",".join(recovery["adopted"]))
    # Propagate verified static policy to this run's baseline, without changing
    # any quote, yield, date, signal or unrelated product field.
    base_path = ROOT / "data" / "_base.json"
    current_base = load(base_path)
    if isinstance(current_base, dict):
        changed = False
        for row in current_base.get("etfs", []):
            meta = info_map.get(row.get("code"), {})
            if (row.get("div_freq") or row.get("div_frequency")) in (None, "", "?", "不明"):
                frequency = official_frequency.known_policy(row.get("code"), meta)   # R1：壞 policy_source 不疊回
                if frequency not in (None, "", "?", "不明"):
                    key = "div_frequency" if "div_frequency" in row else "div_freq"
                    row[key] = frequency
                    changed = True
        if changed:
            save_json(base_path, current_base)

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
    policy_due = update_policy_state(state, recovery, now_ts)
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
    # A queued lookup is not an acknowledged/handled issue. Keep deferred
    # entrants eligible so a later exhausted lookup can still raise its alert.
    deferred_codes = {c for c, s in recovery["status"].items() if s != official_frequency.ADOPTED}
    if deferred_codes:
        known = load(KNOWN_CODES)
        if isinstance(known, list):
            save_json(KNOWN_CODES, [code for code in known if code not in deferred_codes])

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
    note_entries    = []
    today_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()
    for e in new_entries:
        freq    = e.get("div_freq") or e.get("div_frequency") or ""
        no_div  = freq == "不配息"
        pending = e.get("yld_pending", False)
        is_new  = e.get("new_listing", False)
        yld     = e.get("yld", 0)
        ret1y   = e.get("ret1y", 0)
        warn = []
        # D-071：政策未知不在這裡直接求助（一次查無／排隊／暫時失敗都不是 PO 工作），交給下方達門檻的彙整求助
        recovery_deferred = (e["code"] in recovery["status"] and e["code"] not in recovery["conflicts_known"]) or freq in ("不明", "?", "")
        if not yld and not is_new and not no_div and not pending and not recovery_deferred:
            note, why = no_distribution_note(e["code"], info_map.get(e["code"]), cal_map.get(e["code"]), today_tw)
            if note:
                note_entries.append(f"• {e['code']} {e.get('name','')}：{note}（官方公告，屬正常）")
            else:
                warn.append("殖利率查無" + (f"（{why}）" if why else ""))
        if not ret1y and not is_new:
            warn.append("報酬率查無")
        if warn:
            problem_entries.append(
                f"• {e['code']} {e.get('name','')}：{'、'.join(warn)}"
            )
    lines.extend(policy_help_lines(policy_due, recovery, state, {e.get("code"): e.get("name", "") for e in etfs}))
    if problem_entries:
        lines.append("🆕 新進 TOP 100 資料異常")
        lines.extend(problem_entries)
    if note_entries:
        lines.append("ℹ 新進 TOP 100 說明")
        lines.extend(note_entries)

    if lines:
        msg = "\n".join(lines)
        ok = notify(msg)
        if any(ACK.values()):
            ACK_MESSAGE[0] = msg
            if ok is True:                       # 直接模式：確認送達才寫回執；延後模式由 --send-prepared 處理
                _apply_ack(state, ACK)
                save_json(DAILY_STATE, state)
    else:
        print("[OK] 所有監控 ETF 資料正常，TOP 100 無新進")


def _git(*a):
    import subprocess
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True)


def persist_ack(codes, head, published, prepared_digest):
    """求助確認送達後保存回執。R1：完全不碰共用 index、HEAD 與工作目錄——以「已發布版（＝本輪 HEAD）」的 daily_state
    為底套上回執，用私有暫存 index（GIT_INDEX_FILE）建只改 data/daily_state.json 的 commit（父＝head），
    push <commit>:refs/heads/main（不 force、被拒不重試）。任何不符／失敗 → 不推、不假稱已保存（下輪重送），
    也不需要清理（沒有改動任何共用狀態）。"""
    import hashlib, os, subprocess, tempfile
    if published != head:
        print("[ACK] 遠端 main 已被其他 writer 前進：回執不保存，下輪仍會重送")
        return False
    base = _git("show", head + ":data/daily_state.json")
    if base.returncode != 0 or hashlib.sha256(base.stdout.replace(b"\r\n", b"\n")).hexdigest() != prepared_digest:
        print("[ACK] 已發布的 daily_state 不是本輪核驗那份：回執不保存，下輪仍會重送")
        return False
    state = json.loads(base.stdout.decode("utf-8"))
    _apply_ack(state, codes)
    body = (json.dumps(state, ensure_ascii=False, indent=2)).encode("utf-8")
    fd, index = tempfile.mkstemp(prefix="ack_index_")
    os.close(fd)
    os.remove(index)
    env = dict(os.environ, GIT_INDEX_FILE=index)
    run = lambda *a, **k: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, env=env, **k)
    try:
        blob = run("hash-object", "-w", "--stdin", input=body).stdout.decode().strip()
        ok = (len(blob) == 40 and run("read-tree", head).returncode == 0
              and run("update-index", "--cacheinfo", "100644," + blob + ",data/daily_state.json").returncode == 0)
        tree = run("write-tree").stdout.decode().strip() if ok else ""
        commit = run("commit-tree", tree, "-p", head, "-m", "chore: record policy help receipt").stdout.decode().strip() if len(tree) == 40 else ""
        ok = (len(commit) == 40
              and _git("diff-tree", "--no-commit-id", "--name-only", "-r", head, commit).stdout.decode().split() == ["data/daily_state.json"]
              and _git("push", "-q", "origin", commit + ":refs/heads/main").returncode == 0)
    finally:
        if os.path.exists(index):
            os.remove(index)
    if ok:
        print("[ACK] 送達回執已保存（%s）：%s" % (commit[:8], "；".join(f"{k}={','.join(v)}" for k, v in codes.items())))
        return True
    print("[ACK] 回執未能保存（未改動共用 index／HEAD／工作目錄）：下輪仍會重送")
    return False


def cli():
    import argparse
    import hashlib
    import subprocess
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--defer-notifications")
    modes.add_argument("--send-prepared")
    args = parser.parse_args()
    if args.send_prepared:
        path = Path(args.send_prepared)
        if os.environ.get("ETF_PUBLISH_OK") != "true" or not path.is_file():
            notify("🚨 自動修復流程或資料發布未完成；系統將於下輪再試，尚未宣告恢復")
            return 1
        prepared = json.loads(path.read_text(encoding="utf-8"))
        # The notification must describe data that actually reached origin/main,
        # not an uncommitted local repair. No force, reset, or publication here.
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
        remote = subprocess.check_output(["git", "ls-remote", "origin", "refs/heads/main"], cwd=ROOT).decode().split()
        published = remote[0] if remote else None
        if published and published != head:
            # Another writer may legitimately have advanced main after our push.
            subprocess.check_call(["git", "fetch", "--no-tags", "--depth=20", "origin", published], cwd=ROOT)
            if subprocess.run(["git", "merge-base", "--is-ancestor", head, published], cwd=ROOT).returncode:
                published = None
        if not published:
            notify("🚨 自動修復發布結果無法確認；系統保留原警報待下輪重新核對")
            return 1
        for name, digest in prepared["data_sha256"].items():
            blob = subprocess.check_output(["git", "show", published + ":data/" + name], cwd=ROOT)
            if hashlib.sha256(blob.replace(b"\r\n", b"\n")).hexdigest() != digest:
                notify("🚨 自動修復候選與已發布資料不一致；系統下輪重新核對")
                return 1
        ack = prepared.get("ack") or {}
        ok_all = True
        for i, message in enumerate(prepared["messages"]):
            delivered = notify(message)
            ok_all = ok_all and delivered is True
            if ack and i == ack.get("message_index"):
                if delivered is True:
                    ok_all = persist_ack(ack["codes"], head, published, prepared["data_sha256"].get("daily_state.json")) and ok_all
                else:
                    print("[ACK] 求助訊息未送達：不寫回執，下輪仍會重送")
        if not ok_all:
            print("[NOTIFY] 有訊息未送達或回執未保存；下輪重送（結束碼沿用現役：通知步驟不擋後續流程）")
        return 0
    if not args.defer_notifications:
        main()
        return 0
    messages = []
    original = globals()["notify"]
    globals()["notify"] = messages.append
    try:
        main()
        data_hashes = {}
        for name in ("dividend_info.json", "_base.json", "daily_state.json", "known_codes.json"):
            path = ROOT / "data" / name
            if path.is_file():
                data_hashes[name] = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        path = Path(args.defer_notifications)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"messages": messages, "data_sha256": data_hashes}
        if any(ACK.values()) and ACK_MESSAGE[0] in messages:
            doc["ack"] = {"message_index": messages.index(ACK_MESSAGE[0]), "codes": {k: v for k, v in ACK.items() if v}}
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        print("[NOTIFY] Prepared; no Telegram sent before publication")
    finally:
        globals()["notify"] = original
    return 0


if __name__ == "__main__":
    sys.exit(cli())
