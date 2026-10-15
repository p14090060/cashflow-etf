"""00996A 本機 collector（00996A incident Phase 2C）——只產出交接檔，不寫正式資料。

⚠ 不寫 main、不寫 data/active_flow.json、不寫 data/_active_snapshot.json；只寫到 --out 指定的目錄。
⚠ 本階段**不建立自動排程**；正式啟用前由 Gavin 確認兆豐 PCF 自動存取條件。

用法：
  python scripts/mega_collect.py --out <dir> --latest
  python scripts/mega_collect.py --out <dir> --date 2026-09-24 --date 2026-09-29 ...
"""
import argparse, datetime, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.pop("MEGA_FEED_DIR", None)          # collector 自己絕不讀 feed（避免自我循環）
import fetch_active_etf as F                    # noqa: E402
import mega_feed                                # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CODE = "00996A"
FUND_ID, NAME = F.MEGA_FUNDS[CODE]


def _refuse_data_dir(out):
    p = Path(out).resolve()
    if p == (ROOT / "data").resolve() or (ROOT / "data").resolve() in p.parents:
        sys.exit(f"[collect] 拒絕寫入 {p}：collector 不得寫正式資料目錄")


def collect_history(d, fetched_at=None):
    """官方 trade_pcf 歷史查詢：qdt＝d 的下一交易日；資料日以頁面為準，必須等於 d。
    fetched_at：只供離線重播帶入原始抓取時間；正式執行留空＝現在。"""
    out = F.fetch_mega(d, specific=True).get(CODE)
    if not out:
        return None, "官方歷史查詢回空"
    if F.MEGA_LAST_SOURCE.get(CODE) != "mega_trade_pcf":
        return None, f"來源不是官方 PCF（{F.MEGA_LAST_SOURCE.get(CODE)}），不產出"
    if out["data_date"] != d.isoformat():
        return None, f"官方資料日 {out['data_date']} ≠ 要求 {d}"
    q = mega_feed.next_trading_day(d).isoformat()
    return mega_feed.build_record(CODE, NAME, "兆豐", out["data_date"], out["holdings"],
                                  "mega_trade_pcf", F.MEGA_URL, query_date=q, fetched_at=fetched_at), "ok"


def collect_latest(fetched_at=None):
    """最新一份：官方 PCF 成功，且與另外獨立取得的商品頁「同資料日、同股數」才產出（交叉驗證）。
    D-046：fetch_mega 走商品頁備援（PCF 失敗）時不得標成 mega_trade_pcf，也不得拿商品頁跟自己比——
    沒有獨立第二來源，安全拒絕並寫明原因。"""
    out = F.fetch_mega(datetime.date.today(), specific=False).get(CODE)
    src = F.MEGA_LAST_SOURCE.get(CODE)
    pd_date, pd_hold = F._mega_product(FUND_ID)
    if not out:
        return None, "PCF 與商品頁皆未取得"
    if src != "mega_trade_pcf":
        return None, (f"官方 PCF 未成功（實際來源 {src}），商品頁沒有獨立來源可交叉驗證，不產出"
                      f"（商品頁 {pd_date or '未取得'}）")
    if not pd_hold or pd_date != out["data_date"] or \
       {k: v["shares"] for k, v in pd_hold.items()} != {k: v["shares"] for k, v in out["holdings"].items()}:
        return None, f"PCF 與商品頁不一致（PCF {out['data_date']}／商品頁 {pd_date}），不產出"
    return mega_feed.build_record(CODE, NAME, "兆豐", out["data_date"], out["holdings"],
                                  "mega_trade_pcf", F.MEGA_URL, fetched_at=fetched_at), "ok"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--date", action="append", default=[])
    a = ap.parse_args(argv)
    _refuse_data_dir(a.out)
    os.makedirs(a.out, exist_ok=True)
    jobs = [("latest", None)] if a.latest else []
    jobs += [("date", datetime.date.fromisoformat(x)) for x in a.date]
    rc = 0
    for kind, d in jobs:
        rec, why = collect_latest() if kind == "latest" else collect_history(d)
        if rec:
            ok, v = mega_feed.validate_record(rec, CODE)
            if not ok:
                rec, why = None, f"本機驗證失敗：{v}"
        if not rec:
            print(f"[collect] {d or '最新'}：不產出（{why}）"); rc = 1; continue
        path = Path(a.out) / f"mega_{CODE}_{rec['official_data_date']}.json"
        mega_feed.write_atomic(path, rec)
        print(f"[collect] {path.name}：{rec['row_count']} 檔，sha256 {rec['sha256'][:12]}…")
    return rc


if __name__ == "__main__":
    sys.exit(main())
