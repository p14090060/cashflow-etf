"""scripts/market_bootstrap.py
一次性人工工具：把正式遠端的舊格式 market.json（沒有逐檔 quote_date／quote_src）初始化成新格式。
**不放進任何排程**。排程中的 update-data／wrapper 一律走 market_guard.py；舊格式遠端在那裡會 ABORT。

只在「可證明本機不會比遠端舊」時放行（fail-closed，任何一項不成立 → exit 1）：
  1. 遠端確實是舊格式（沒有 market_state）；已經是新格式 → exit 2（不需要初始化）。
  2. 遠端每一檔都沒有逐檔日期／來源欄位（若有任何新格式證據，改走 market_guard 比較，不在這裡處理）。
  3. 本機通過 validate_market，market_state＝closed，close_confirmed：etfs＝total＝ETF 數（每一檔都有
     交易日 D 的官方收盤或官方確認無成交）；有成交的每一檔 quote_date＝D、來源為官方。
  4. 執行時間在 D 當天 15:00（台北）以後：此時市場已收盤，遠端舊檔的任何 MIS 成交都不可能晚於 D 的官方收盤。
  5. 遠端 updated 的日期 ≤ D，且遠端每一檔 mis_time（若有）≤ 13:30。
  6. 遠端的 ETF 代號都在本機（不會無聲消失）。
  7. 官方 no_trade 只代表「當日無成交」，不是價格較新的證據。這類 ETF 沿用的參考價必須：
     有來源（quote_src）與日期（quote_date），而且與遠端現值相同（只容許浮點表示誤差，見 same_value；
     等於沒有改動，不可能倒退）；遠端沒有這檔則可。價格大小不代表先後，任何一檔不成立 → 整批 NOT SAFE，
     並列出代號與原因。
  8. （F-2）候選的大盤（market 區塊）也必須有可比較證據：以 market_guard.stamp 判斷，必須是 MIS 成交證據
     （quote_date＋mis_time），quote_date＝D、is_live＝false；遠端 updated 也是 D 時，候選 mis_time 不得早於遠端
     大盤 mis_time。缺日期、只有日期沒有來源、未來／過去日期、無法解析 → NOT SAFE。
     不用 updated 或 ETF 日期補大盤日期：否則初始化後每次 update-data 的 Guard 都會對 __market__ ABORT。
發布與回復請用 scripts/market_init.py（publish／rollback），不要手動組合指令。

用法：python scripts/market_bootstrap.py [本機檔 data/market.json] [遠端 ref origin/main] [--now "YYYY-MM-DD HH:MM"]
"""
import datetime, math, subprocess, sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from json_safe import load_strict, strict_loads, validate_market, validate_market_policy   # noqa: E402
import product_policy   # noqa: E402
import market_guard     # noqa: E402

OFFICIAL = ("TWSE_MI_INDEX", "TPEX_OTC")
TZ = datetime.timezone(datetime.timedelta(hours=8))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class NotSafe(Exception):
    pass


def same_value(a, b):
    """只容許浮點表示誤差的等值（相對 1e-12），不是價格跳動容差：8.33 vs 8.32 不同、8.33 vs 8.330000000000002 相同。"""
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=0.0)


def check(local, remote, now):
    """回傳 'OK'／'NOT_NEEDED'；不安全丟 NotSafe。now：台北時間 datetime。"""
    if remote is None:
        raise NotSafe("讀不到遠端 market.json")
    if "market_state" in remote:
        return "NOT_NEEDED"
    for e in remote.get("etfs", []):
        if any(k in e for k in ("quote_date", "quote_src", "close_status")):
            raise NotSafe(f"遠端 {e.get('code')} 已有逐檔證據欄位，請改用 market_guard 比較")
    validate_market_policy(local)   # 候選不得含 K／ETN（商品收錄政策）
    etfs = local["etfs"]
    cc = local.get("close_confirmed") or {}
    if local.get("market_state") != "closed" or cc.get("etfs") != cc.get("total") or cc.get("total") != len(etfs):
        raise NotSafe(f"本機不是全部官方確認收盤（market_state={local.get('market_state')}, close_confirmed={cc}）")
    d = datetime.date.fromisoformat(local.get("quote_date") or "")
    for e in etfs:
        if e.get("close_status") == "traded" and (e.get("quote_date") != d.isoformat() or e.get("quote_src") not in OFFICIAL):
            raise NotSafe(f"本機 {e['code']} 不是 {d} 的官方收盤")
        if e.get("close_status") not in ("traded", "no_trade"):
            raise NotSafe(f"本機 {e['code']} 沒有官方收盤狀態")
    if now.date() != d or (now.hour, now.minute) < (15, 0):
        raise NotSafe(f"只能在交易日 {d} 15:00 以後執行（現在 {now:%Y-%m-%d %H:%M}）")
    try:
        ru = datetime.datetime.strptime(remote.get("updated") or "", "%Y-%m-%d %H:%M")
    except ValueError:
        raise NotSafe(f"遠端 updated 無法解析：{remote.get('updated')!r}")
    if ru.date() > d:
        raise NotSafe(f"遠端 updated {ru:%Y-%m-%d %H:%M} 晚於 {d}")
    close = datetime.time(13, 30)
    for e in remote.get("etfs", []):
        if e.get("mis_time"):
            try:
                t = datetime.datetime.strptime(e["mis_time"], "%H:%M").time()
            except ValueError:
                raise NotSafe(f"遠端 {e.get('code')} mis_time 無法解析：{e['mis_time']!r}")
            if t > close:
                raise NotSafe(f"遠端 {e.get('code')} mis_time {e['mis_time']} 晚於 13:30")
    missing = {e.get("code") for e in remote.get("etfs", [])} - {e["code"] for e in etfs}
    # 商品收錄政策（PO 2026-10-10）：只有 K 尾碼與 excluded_products.json 已核實的商品可以消失；
    # 清單讀不到 → 例外 → NOT SAFE（fail-closed）
    listed = product_policy.listed_codes()
    missing = {c for c in missing if not product_policy.exclusion_reason(c, listed)}
    if missing:
        raise NotSafe(f"遠端有本機沒有的 ETF：{sorted(missing)[:5]}")
    rmap = {e.get("code"): e for e in remote.get("etfs", [])}
    blocked = []
    for e in etfs:
        if e.get("close_status") != "no_trade":
            continue
        r = rmap.get(e["code"])
        if r is None:
            continue                                   # 遠端沒有這檔：不會覆蓋任何既有價格
        if not e.get("quote_src") or not e.get("quote_date"):
            blocked.append(f"{e['code']}：無成交參考價來源／日期不明（{e.get('quote_src')}／{e.get('quote_date')}）")
            continue
        rp, lp = r.get("price"), e.get("price")
        if not isinstance(rp, (int, float)) or not isinstance(lp, (int, float)) or not same_value(rp, lp):
            blocked.append(f"{e['code']}：無成交，參考價 {lp}（{e['quote_src']} {e['quote_date']}）與遠端 {rp} 不同，"
                           f"無法證明不是倒退")
    if blocked:
        raise NotSafe("無成交 ETF 參考價無法確認，整批不初始化：" + "；".join(blocked))
    _check_market_block(local, remote, d, ru)
    return "OK"


def _check_market_block(local, remote, d, ru):
    """F-2：候選大盤必須是 Guard 能比較的 D 日 MIS 證據；不補造日期。"""
    m = local.get("market") or {}
    try:
        st = market_guard.stamp(m)
    except market_guard.Unknown as e:
        raise NotSafe(f"候選大盤無法比較：{e}")
    if st is None:
        raise NotSafe(f"候選大盤沒有行情日期（不以 updated／ETF 日期補）：{m}")
    if st[1] != 1:
        raise NotSafe(f"候選大盤只有日期、沒有可比較的成交時間／來源：{m}")
    if st[0] != d:
        raise NotSafe(f"候選大盤日期 {st[0]} 不是交易日 {d}")
    if m.get("is_live") is not False:
        raise NotSafe(f"候選大盤 is_live 不是 false：{m.get('is_live')!r}")
    rm = remote.get("market")
    if rm is None:
        rm = {}
    if not isinstance(rm, dict):
        raise NotSafe(f"遠端大盤不是物件：{type(rm).__name__}")
    if rm.get("quote_date") is not None or rm.get("quote_src") is not None:
        raise NotSafe("遠端大盤已有日期／來源欄位，請改用 market_guard 比較")
    rmt = rm.get("mis_time")                            # 鍵不存在或 null＝缺省；其他非字串／空字串／格式錯＝非法
    if rmt is not None:
        if not isinstance(rmt, str):
            raise NotSafe(f"遠端大盤 mis_time 型別不合法：{rmt!r}")
        try:
            rt = datetime.datetime.strptime(rmt, "%H:%M").time()
        except ValueError:
            raise NotSafe(f"遠端大盤 mis_time 無法解析：{rmt!r}")
        if ru.date() == d and st[2] < rt:
            raise NotSafe(f"候選大盤 {st[2]:%H:%M} 早於遠端同日大盤 {rmt}（倒退）")


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    now = datetime.datetime.now(TZ).replace(tzinfo=None)
    if "--now" in argv:
        now = datetime.datetime.strptime(argv[argv.index("--now") + 1], "%Y-%m-%d %H:%M")
        args = [a for a in args if a != argv[argv.index("--now") + 1]]
    local_path = args[0] if args else "data/market.json"
    ref = args[1] if len(args) > 1 else "origin/main"
    try:
        local = load_strict(local_path)
        r = subprocess.run(["git", "show", f"{ref}:data/market.json"], capture_output=True)
        remote = strict_loads(r.stdout.decode("utf-8")) if r.returncode == 0 else None
        verdict = check(local, remote, now)
    except Exception as e:
        print(f"::error::[BOOTSTRAP] NOT SAFE: {type(e).__name__}: {e}")
        return 1
    if verdict == "NOT_NEEDED":
        print("[BOOTSTRAP] 遠端已是新格式，不需要初始化")
        return 2
    print("[BOOTSTRAP] OK：可用 publish_gate.py 手動發布一次")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
