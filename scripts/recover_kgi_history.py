"""00407A（凱基）歷史回補——00407A incident（2026-10-08）。

背景：fetch_kgi 舊版把「公告日」誤當資料日，同一資料日標到兩份不同持股，build_flow 判 not_updated，
9/30、10/1、10/5、10/7 的換股被靜默吃掉。資料日修正後，用凱基官方歷史查詢逐日重放。

做法（不另寫比對邏輯，直接重用 production 的 main()）：
  1. 取得官方逐日持股：queryDate＝資料日的下一交易日（凱基回「該日公告、前一交易日持股」），最新一份不帶 queryDate；
     每份的資料日（括號日期）必須剛好等於預期日，否則整個中止。
  2. 在暫存副本上，從起點（--start，必須與目前快照的持股逐筆相同）開始，每個交易日呼叫一次 main()，
     adapter 只回這檔當天的官方資料 → Flow 只會在相鄰交易日之間產生，與正常每日運作的結果完全一樣。
  3. --apply：正式資料＝遠端 main。以 fetch 當下的遠端 commit 為基準；快照必須已等於回補結果（否則拒絕），
     只改 active_flow.json 的 00407A 一列，做成以基準為 parent 的單一 commit、非 force push——
     遠端在這期間被任何 writer（Actions、本機行情排程）推進過就會被拒絕，絕不覆蓋他人更新。
  ⚠ 只供 incident 人工執行，不得掛進排程／workflow。

證據：--evidence 目錄存每日官方原始 HTML 與逐步結果 report.json；--raw 可指定已存的原始頁離線重播（Codex 重播用）。

用法：
  python scripts/recover_kgi_history.py --start 2026-09-24 --evidence docs/incidents/00407A            # dry-run
  python scripts/recover_kgi_history.py --start 2026-09-24 --evidence docs/incidents/00407A --apply    # 寫正式檔
  python scripts/recover_kgi_history.py --start 2026-09-24 --evidence <dir> --raw docs/incidents/00407A/raw   # 離線重播
"""
import argparse, contextlib, datetime, io, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_active_etf as F     # noqa: E402
import mega_feed                 # noqa: E402  （交易日曆：重用 closes_on）

CODE = "00407A"
FUND_ID = F.KGI_FUNDS[CODE][0]


def _fetch_page(query, raw_dir, evid_raw):
    name = "latest" if query is None else "q" + query.strftime("%Y%m%d")
    if raw_dir:
        page = Path(raw_dir, f"kgi_{FUND_ID}_{name}.html").read_text(encoding="utf-8")
    else:
        body = F.urllib.parse.urlencode({"fundID": FUND_ID,
                                          "queryDate": query.strftime("%Y/%m/%d") if query else ""}).encode()
        req = F.urllib.request.Request("https://www.kgifund.com.tw/Fund/RedemptionVC", data=body, headers={
            "User-Agent": F.UA, "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.kgifund.com.tw/Fund/RedemptionList"})
        page = F.urllib.request.urlopen(req, timeout=25, context=F._SSL).read().decode("utf-8", "replace")
    if evid_raw:
        Path(evid_raw, f"kgi_{FUND_ID}_{name}.html").write_text(page, encoding="utf-8")
    return page


def _parse(page):
    """用 production 的 fetch_kgi 解析（把網路換成這份頁面），確保跟每日排程同一套邏輯。"""
    saved = F.urllib.request.urlopen
    F.urllib.request.urlopen = lambda *a, **k: io.BytesIO(page.encode("utf-8"))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return F.fetch_kgi(datetime.date.today()).get(CODE)
    finally:
        F.urllib.request.urlopen = saved


def collect(start, raw_dir, evid_raw):
    """start 起（含）到最新一份，每個交易日的官方持股。回傳 [(資料日, adapter dict)]。"""
    latest = _parse(_fetch_page(None, raw_dir, evid_raw))
    if not latest or not latest["data_date"]:
        sys.exit("[recover] 讀不到最新一份的資料日，中止")
    end = datetime.date.fromisoformat(latest["data_date"])
    days, d = [], start
    while d < end:
        q = mega_feed.next_trading_day(d)
        got = _parse(_fetch_page(q, raw_dir, evid_raw))
        if not got or got["data_date"] != d.isoformat():
            sys.exit(f"[recover] queryDate={q} 預期資料日 {d}，實得 {got and got['data_date']}，中止")
        days.append((d.isoformat(), got))
        d = q
    days.append((end.isoformat(), latest))
    return days


def _git(repo, *args):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)} 失敗：{(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


# 測試用注入點：在「確認基準版本」之後、push 之前呼叫（模擬並行 writer、寫入失敗）
_HOOK_BEFORE_WRITE = None
_HOOK_BEFORE_PUSH = None


def apply_via_git(repo, remote, branch, base, final_snap, final_row):
    """把回補結果以「基準版本為 parent 的單一 commit、非 force push」寫進正式資料。

    - 快照：基準版本的 00407A 快照必須與回補結果逐欄相同 → 不寫；不同 → 拒絕（不自行覆蓋）。
    - Flow：只改 active_flow.json 的 00407A 一列；已相同 → 不需寫入。
    - 並行保護：push 不是 fast-forward（遠端已被別的 writer 推進）→ 被拒絕 → 中止，遠端保持他人的版本。
    - 原子性：正式資料只在 push 成功那一刻改變（單一 commit）；本機檔案在暫存 worktree 內修改，
      任何一步失敗都不會留下部分寫入的正式狀態。"""
    wt = Path(tempfile.mkdtemp(prefix="kgi_apply_"))
    _git(repo, "worktree", "add", "-q", "--detach", str(wt), base)
    try:
        snap = json.load(open(wt / "data" / "_active_snapshot.json", encoding="utf-8"))
        flow = json.load(open(wt / "data" / "active_flow.json", encoding="utf-8"))
        if snap["etfs"].get(CODE) != final_snap:
            sys.exit(f"[recover] 正式快照（{base[:8]}）的 {CODE} 與回補結果不同 → 拒絕 apply，不覆蓋快照")
        if flow["etfs"].get(CODE) == final_row:
            print(f"[recover] 正式資料（{base[:8]}）已等於回補結果，不需寫入")
            return None
        if _HOOK_BEFORE_WRITE:
            _HOOK_BEFORE_WRITE()
        flow["etfs"][CODE] = final_row
        path = wt / "data" / "active_flow.json"
        tmpf = str(path) + ".tmp"
        with open(tmpf, "w", encoding="utf-8") as f:
            json.dump(flow, f, ensure_ascii=False, indent=2)
        os.replace(tmpf, path)
        _git(str(wt), "add", "data/active_flow.json")
        _git(str(wt), "commit", "-q", "-m", f"data(active-flow): {CODE} 逐日回補（recover_kgi_history，base {base[:8]}）")
        if _HOOK_BEFORE_PUSH:
            _HOOK_BEFORE_PUSH()
        try:
            _git(str(wt), "push", "-q", remote, f"HEAD:refs/heads/{branch}")      # 非 force：不是 fast-forward 就拒絕
        except RuntimeError as e:
            sys.exit(f"[recover] push 被拒絕（遠端在回補期間已被更新），中止、未覆蓋：{e}")
        new = _git(str(wt), "rev-parse", "HEAD").strip()
        _git(repo, "fetch", "-q", remote, branch)
        got = json.loads(_git(repo, "show", f"{remote}/{branch}:data/active_flow.json"))["etfs"].get(CODE)
        if _git(repo, "rev-parse", f"{remote}/{branch}").strip() != new or got != final_row:
            sys.exit("[recover] 遠端驗證不一致")
        print(f"[recover] 已寫入正式資料 {new[:8]}（parent {base[:8]}），遠端讀回一致")
        return new
    finally:
        _git(repo, "worktree", "remove", "--force", str(wt))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--raw")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=str(F.ROOT))
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--branch", default="main")
    a = ap.parse_args(argv)
    evid = Path(a.evidence); evid.mkdir(parents=True, exist_ok=True)
    evid_raw = None if a.raw else evid / "raw"
    if evid_raw:
        evid_raw.mkdir(exist_ok=True)

    # 正式資料＝遠端 main 上的檔案（Actions 寫入後 push），不是本機工作目錄。
    # 以 fetch 當下的遠端 commit 為「基準版本」，全程只讀這個版本；寫回時以它為 parent、非 force push，
    # 遠端在這期間被任何 writer 推進過，push 就會被拒絕（git 的 compare-and-swap，所有 writer 都遵守）。
    base = None
    if a.apply:
        _git(a.repo, "fetch", "-q", a.remote, a.branch)
        base = _git(a.repo, "rev-parse", f"{a.remote}/{a.branch}").strip()
        prod_snap = json.loads(_git(a.repo, "show", f"{base}:data/_active_snapshot.json"))
        prod_out = json.loads(_git(a.repo, "show", f"{base}:data/active_flow.json"))
    else:
        prod_snap, prod_out = F.load_json(F.SNAPSHOT), F.load_json(F.OUT)
    before = {"snapshot": prod_snap["etfs"].get(CODE), "active_flow": prod_out["etfs"].get(CODE)}
    days = collect(datetime.date.fromisoformat(a.start), a.raw, evid_raw)
    start_d, start_h = days[0]
    if start_d != a.start:
        sys.exit("[recover] 起點不符")

    # 起點必須和正式快照的歷史起點吻合：用起點的官方持股當暫存快照的種子，
    # active_flow 列沿用正式檔（first_seen 等欄位），之後每一步都走 production main()。
    tmp = Path(tempfile.mkdtemp(prefix="kgi_recover_"))
    snap_p, out_p = tmp / "snap.json", tmp / "flow.json"
    json.dump({"fetched": "(recover seed)", "etfs": {CODE: start_h}}, open(snap_p, "w", encoding="utf-8"),
              ensure_ascii=False)
    seed_row = dict(prod_out["etfs"][CODE])
    json.dump({"etfs": {CODE: seed_row}}, open(out_p, "w", encoding="utf-8"), ensure_ascii=False)

    saved = (F.SNAPSHOT, F.OUT, F.ADAPTERS)
    steps = []
    try:
        F.SNAPSHOT, F.OUT = snap_p, out_p
        for d, h in days[1:]:
            F.ADAPTERS = [lambda date_obj, specific=False, _h=h: {} if specific else {CODE: _h}]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                F.main()
            row = json.load(open(out_p, encoding="utf-8"))["etfs"][CODE]
            steps.append({"data_date": d, "holdings": len(h["holdings"]),
                          "total_shares": sum(v["shares"] for v in h["holdings"].values()),
                          **{k: row.get(k) for k in ("advanced", "reason", "flow_from", "flow_to", "changed",
                                                      "buy", "sell", "last_change_date", "anomaly")},
                          "log": [l for l in buf.getvalue().splitlines() if CODE in l]})
            print(f"[recover] {d}：{steps[-1]['log'][-1] if steps[-1]['log'] else ''}")
        final_snap = json.load(open(snap_p, encoding="utf-8"))["etfs"][CODE]
        final_row = json.load(open(out_p, encoding="utf-8"))["etfs"][CODE]
    finally:
        F.SNAPSHOT, F.OUT, F.ADAPTERS = saved
        shutil.rmtree(tmp, ignore_errors=True)

    report = {"etf": CODE, "start": a.start, "official_days": [d for d, _ in days],
              "before": {"snapshot_date": (before["snapshot"] or {}).get("data_date"),
                         "flow": {k: (before["active_flow"] or {}).get(k) for k in
                                  ("flow_from", "flow_to", "changed", "last_change_date", "data_date")}},
              "steps": steps,
              "after": {"snapshot_date": final_snap["data_date"], "holdings": len(final_snap["holdings"]),
                        "flow": {k: final_row.get(k) for k in ("data_date", "advanced", "reason", "flow_from",
                                                              "flow_to", "changed", "buy", "sell", "last_change_date")}},
              "applied": bool(a.apply)}
    json.dump(report, open(evid / "report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[recover] 最終：快照 {final_snap['data_date']}，Flow {final_row.get('flow_from')} → {final_row.get('flow_to')}"
          f"（{final_row.get('changed')} 檔，最後換股 {final_row.get('last_change_date')}）")

    if a.apply:
        apply_via_git(a.repo, a.remote, a.branch, base, final_snap, final_row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
