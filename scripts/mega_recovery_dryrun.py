"""00996A 歷史回補 dry-run（00996A incident Phase 2C）——只預覽，不寫正式資料。

依交易日順序重放：每一天只和「前一個有效交易日」的快照比較（build_flow），
絕不把 09-24 → 10-08 的累積差額當成單日 Flow。

現有資料模型（見 fetch_active_etf.main）：
  data/_active_snapshot.json  每檔只存「最新一份」持股（作為下一次比對基準）
  data/active_flow.json       每檔只存「最近一次」flow（flow_from → flow_to）＋ last_change_date
  → 沒有逐日歷史欄位；逐日紀錄只存在 git 歷史。回補的正式結果因此是：
    快照＝最後一天持股、flow＝最後兩個交易日之間的單日異動；中間各日 flow 僅在 dry-run 報告中呈現。

用法：python scripts/mega_recovery_dryrun.py --feed <dir> --report <file.json>
"""
import argparse, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.pop("MEGA_FEED_DIR", None)
import fetch_active_etf as F     # noqa: E402
import mega_feed                 # noqa: E402

CODE = "00996A"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args(argv)
    if Path(a.report).resolve().parent == (F.ROOT / "data").resolve():
        sys.exit("[dryrun] 報告不得寫進 data/")

    snap = (F.load_json(F.SNAPSHOT) or {}).get("etfs", {}).get(CODE)
    if not snap:
        sys.exit("[dryrun] 快照內沒有 00996A，無比對基準")
    base = {"name": snap.get("name"), "issuer": snap.get("issuer"), "data_date": snap["data_date"],
            "holdings": snap["holdings"]}
    print(f"[dryrun] 起點＝現有快照 {base['data_date']}（{len(base['holdings'])} 檔）")

    recs = []
    for n in sorted(os.listdir(a.feed)):
        if n.startswith(f"mega_{CODE}_") and n.endswith(".json"):
            recs.append(json.load(open(os.path.join(a.feed, n), encoding="utf-8")))
    recs.sort(key=lambda r: r.get("official_data_date", ""))

    steps, prev = [], base
    for rec in recs:
        ok, why = mega_feed.validate_record(rec, CODE, prev["data_date"])
        d = rec.get("official_data_date")
        if not ok:
            # 與基準同日：確認內容一致即可略過；其他驗證失敗＝資料缺口，停止往後重放
            if why.startswith("not_newer") and d == prev["data_date"]:
                same = {r["code"]: r["shares"] for r in rec["holdings"]} == F._shares(prev["holdings"])
                print(f"[dryrun] {d}：與基準同日，內容{'一致' if same else '不一致！'}，略過")
                if not same:
                    steps.append({"date": d, "error": "same_date_mismatch"}); break
                continue
            print(f"[dryrun] {d}：驗證失敗（{why}）→ 標記資料缺口，停止")
            steps.append({"date": d, "gap": why}); break
        cur = mega_feed.record_to_adapter(rec)
        f = F.build_flow({"etfs": {CODE: prev}}, {"etfs": {CODE: cur}})[CODE]
        step = {"from": prev["data_date"], "to": d, "rows": rec["row_count"],
                "advanced": f.get("advanced"), "reason": f.get("reason"),
                "changed": f.get("changed"), "buy": f.get("buy"), "sell": f.get("sell"),
                "no_price": len(f.get("no_price") or []), "price_date": f.get("price_date"),
                "anomaly": f.get("anomaly")}
        steps.append(step)
        print(f"[dryrun] {step['from']} → {d}：{rec['row_count']} 檔、異動 {step['changed']}、"
              f"加碼 {(step['buy'] or 0)/1e8:.2f} 億／減碼 {(step['sell'] or 0)/1e8:.2f} 億、"
              f"價格日 {step['price_date']}")
        prev = cur

    final = {"snapshot_data_date": prev["data_date"], "snapshot_rows": len(prev["holdings"]),
             "active_flow_flow_from": steps[-1].get("from") if steps else None,
             "active_flow_flow_to": steps[-1].get("to") if steps else None}
    json.dump({"etf": CODE, "start": base["data_date"], "steps": steps, "final_preview": final},
              open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[dryrun] 最終預覽：{final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
