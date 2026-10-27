"""scripts/market_guard.py
market.json 發布前的新舊判斷（update-data.yml 與本機 wrapper 共用）：逐檔比較本機新產生的
market.json 與要覆蓋的遠端版本，不只看整份 JSON 的 updated／quote_time。

每檔（含大盤，代號 __market__）的有效行情戳記，沿用 Holiday Fix 的欄位：
  - 官方收盤（quote_src 為 TWSE_MI_INDEX／TPEX_OTC）：(quote_date, 官方)          → 當日最後
  - MIS 成交（quote_src=MIS 或舊檔有 mis_time）：  (quote_date, MIS, mis_time)    → 依成交時間
  - 其他（yfinance 等，只有日期）：               (quote_date, 只有日期)
日期與時間都先解析成 date／time 再比較，不用字串長短。

判斷：
  - 有的較新、有的較舊（部分倒退）→ ABORT（exit 1），整批不發布。
  - 只有較舊或相同（遠端整體較新）→ SKIP（exit 10），不發布、不算錯。
  - 任何一檔無法可靠比較（同日但一邊只有日期、本機日期不明而遠端有、格式不合）→ ABORT。
  - 都不舊、至少一檔較新 → PUBLISH（exit 0）。
  - 全部相同：本機 updated 較新（狀態更新，例如收盤／休市標記）→ PUBLISH；否則 SKIP（exit 10）。
  - 不因缺 market_state 或 updated 較新而放行：遠端任何一檔只要沒有可比較的證據
    （沒有 quote_date，或有 mis_time 卻沒有日期的舊格式）→ 無法判斷 → ABORT。
    舊格式遠端的首次升級由 scripts/market_bootstrap.py 一次性人工處理，不在排程內。
本機檔不符 json_safe.validate_market → ABORT。

用法：python scripts/market_guard.py [本機檔 data/market.json] [遠端 ref origin/main]
"""
import datetime, subprocess, sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from json_safe import load_strict, strict_loads, validate_market, validate_market_policy   # noqa: E402
import product_policy   # noqa: E402

PUBLISH, SKIP, ABORT = 0, 10, 1
OFFICIAL = ("TWSE_MI_INDEX", "TPEX_OTC")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class Unknown(Exception):
    pass


def _date(s):
    try:
        return datetime.date.fromisoformat(s) if s else None
    except (TypeError, ValueError):
        raise Unknown(f"日期格式不合：{s!r}")


def _time(s):
    try:
        return datetime.datetime.strptime(s, "%H:%M").time()
    except (TypeError, ValueError):
        raise Unknown(f"時間格式不合：{s!r}")


def _updated(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        raise Unknown(f"updated 格式不合：{s!r}")


def stamp(x):
    """(date, kind, time)；kind：2＝官方收盤、1＝MIS 成交、0＝只有日期。日期不明 → None。"""
    d = _date(x.get("quote_date"))
    if d is None:
        if x.get("mis_time") or x.get("quote_src"):
            raise Unknown("有成交時間／來源但沒有行情日期（舊格式）")
        return None
    src = x.get("quote_src")
    if src in OFFICIAL:
        return (d, 2, None)
    if x.get("mis_time"):
        return (d, 1, _time(x["mis_time"]))
    return (d, 0, None)


def compare(a, b):
    """a 相對 b：1 較新、0 相同、-1 較舊；無法可靠比較 → Unknown。"""
    if a is None and b is None:
        raise Unknown("兩邊都沒有行情日期")
    if a is None:
        raise Unknown("本機日期不明、遠端有日期")
    if b is None:
        raise Unknown("遠端沒有可比較的行情證據")
    if a[0] != b[0]:
        return 1 if a[0] > b[0] else -1
    if a[1] != b[1]:
        if 0 in (a[1], b[1]):
            raise Unknown("同一天但一邊只有日期（無法排序）")
        return 1 if a[1] > b[1] else -1
    if a[1] == 1:
        return (a[2] > b[2]) - (a[2] < b[2])
    return 0


def decide(local, remote):
    """回傳 (結果, 說明)。local 必須通過 validate_market＋商品收錄政策（含 K／ETN → 例外 → ABORT）。"""
    validate_market_policy(local)
    if remote is None:
        return PUBLISH, "遠端沒有 market.json"
    # MG-1：一般 ETF 不得無聲消失。遠端有、候選沒有的代號，只有 K 尾碼與 excluded_products.json（ETN 等）可放行；
    # 其他一檔都不行（合法下市流程尚未實作）→ ABORT，保留正式資料
    gone = product_policy.unapproved_removals(remote.get("etfs"), local.get("etfs"))
    if gone:
        return ABORT, f"候選比遠端少了 {len(gone)} 檔一般 ETF（未經核准的移除），不發布：{gone[:10]}"
    lu, ru = local.get("updated"), remote.get("updated")
    try:
        l_newer = _updated(lu) > _updated(ru)
    except Unknown as ex:
        return ABORT, f"無法比較 updated：{ex}"
    rmap = {e["code"]: e for e in remote.get("etfs", [])}
    items = [(e["code"], e, rmap[e["code"]]) for e in local["etfs"] if e["code"] in rmap]
    items.append(("__market__", local.get("market") or {}, remote.get("market") or {}))
    newer, older, unknown = [], [], []
    for code, a, b in items:
        try:
            sa, sb = stamp(a), stamp(b)
            if code == "__market__" and sa is None and sb is None:
                continue        # 大盤兩邊都沒有日期（基線大盤本來就無日期）：不作為判斷依據；個股仍嚴格
            c = compare(sa, sb)
        except Unknown as ex:
            unknown.append(f"{code}（{ex}）")
            continue
        if c > 0:
            newer.append(code)
        elif c < 0:
            older.append(f"{code} {a.get('quote_date')} {a.get('mis_time') or a.get('quote_src')} < "
                         f"{b.get('quote_date')} {b.get('mis_time') or b.get('quote_src')}")
    if unknown:
        return ABORT, "無法可靠判斷新舊，不發布：" + "；".join(unknown[:5])
    if older and newer:
        return ABORT, "部分行情倒退，整批不發布：" + "；".join(older[:5])
    if older:
        return SKIP, f"遠端較新（{len(older)} 檔本機較舊、沒有較新的），不發布：" + "；".join(older[:3])
    if newer:
        return PUBLISH, f"{len(newer)} 檔較新、無倒退"
    if l_newer:
        return PUBLISH, f"行情相同、狀態更新（updated {lu} > {ru}）"
    return SKIP, f"行情相同且 updated {lu} 不比 {ru} 新"


def main(argv):
    local_path = argv[1] if len(argv) > 1 else "data/market.json"
    ref = argv[2] if len(argv) > 2 else "origin/main"
    try:
        local = load_strict(local_path)
        r = subprocess.run(["git", "show", f"{ref}:data/market.json"], capture_output=True)
        remote = strict_loads(r.stdout.decode("utf-8")) if r.returncode == 0 else None
        code, why = decide(local, remote)
    except Exception as e:
        code, why = ABORT, f"{type(e).__name__}: {e}"
    tag = {PUBLISH: "PUBLISH", SKIP: "SKIP", ABORT: "ABORT"}[code]
    print(("::error::" if code == ABORT else "") + f"[GUARD] {tag}: {why}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
