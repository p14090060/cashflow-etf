"""scripts/market_init.py
market.json 新格式「一次性初始化」的受控發布與回復（人工執行，不放進任何排程）。
請在乾淨的隔離 worktree（不是主工作樹）執行；data/market.json 為 mis_fetcher 產生的候選檔。

publish：
  1. git fetch，固定 base＝origin/main 完整 SHA；記下遠端 market.json 的 blob（備份）。
  2. 候選檔只讀一次位元組：同一份位元組做 market_bootstrap.check 與計算預期 blob（hash-object --path）。
  3. 提交前比對工作目錄檔仍是那份位元組（被改 → 中止），再交 publish_gate.run(push=False) 建立 commit。
  4. 立刻固定 tip＝HEAD 完整 SHA，並自行再驗：tip 的父＝base、base..tip 只改 data/market.json、
     tip 中 market.json 的 blob＝候選 blob、publish_gate.check_outgoing(base, tip) 通過。
  5. 推送前 HEAD 必須仍是 tip（變動 → 中止，不推送）；git push origin <tip>:refs/heads/main（不 force；
     遠端已前進 → non-fast-forward 被拒 → 中止重新核對）。
  6. 寫出紀錄檔：backup_main、backup_market_blob、init_commit、init_market_blob。

rollback（依紀錄檔）：
  1. git fetch，固定 cur＝origin/main；cur 的 market.json blob 必須仍＝init_market_blob，
     否則（已有其他 writer 發布新行情）中止，不覆蓋。
  2. 本機隔離 worktree reset 到 cur（只動本機），把 backup_main 版 market.json 寫回，
     publish_gate.run(push=False) 建補償 commit；同樣固定 tip、再驗只改 market.json、父＝cur、
     blob＝備份 blob；HEAD 不得變動；推送 <tip>:refs/heads/main（不 force，不 reset 遠端）。
  其他 writer 已發布的非 market 檔案因為是在 cur 之上補償，全部保留。

用法：
  python scripts/market_init.py publish  --record init_record.json [--now "YYYY-MM-DD HH:MM"]
  python scripts/market_init.py rollback --record init_record.json
"""
import argparse, datetime, json, subprocess, sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import market_bootstrap as mb   # noqa: E402
import publish_gate as pg       # noqa: E402
from json_safe import strict_loads   # noqa: E402

MARKET = "data/market.json"
TZ = datetime.timezone(datetime.timedelta(hours=8))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class Abort(Exception):
    pass


def git(*a, check=True):
    r = subprocess.run(["git", *a], capture_output=True)
    if check and r.returncode != 0:
        raise Abort(f"git {' '.join(a)} 失敗：{r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8", "replace").strip()


def rev(ref):
    return git("rev-parse", "--verify", ref + "^{commit}")


def blob_of(ref):
    return git("rev-parse", "--verify", f"{ref}:{MARKET}")


def _commit_and_pin(base, expected_blob, message, before_push=None):
    """publish_gate --no-push 建 commit → 固定 tip 並再驗 → HEAD 未變 → 推送固定 SHA。回傳 tip。"""
    if pg.run([MARKET], message, push=False) != 0:
        raise Abort("publish_gate 驗證失敗")
    tip = rev("HEAD")
    if rev(tip + "^") != base:
        raise Abort(f"commit {tip[:8]} 的父不是固定的 base {base[:8]}")
    changed = git("diff", "--name-only", base, tip).splitlines()
    if changed != [MARKET]:
        raise Abort(f"base..tip 改到的檔案不是只有 {MARKET}：{changed}")
    if blob_of(tip) != expected_blob:
        raise Abort("commit 中的 market.json 不是驗證過的那一份")
    pg.check_outgoing({MARKET}, base, tip)
    if before_push:
        before_push()
    if rev("HEAD") != tip:
        raise Abort(f"驗證後 HEAD 變動（{tip[:8]} → {rev('HEAD')[:8]}），中止、不推送")
    r = subprocess.run(["git", "push", "origin", f"{tip}:refs/heads/main"], capture_output=True)
    if r.returncode != 0:
        raise Abort("推送被拒（遠端可能已前進），中止並重新核對：" + r.stderr.decode("utf-8", "replace").strip())
    return tip


def _blob_for(data):
    """這份位元組若以 data/market.json 提交時的 blob SHA（套用與 git add 相同的 path 過濾，例如 autocrlf）。"""
    r = subprocess.run(["git", "hash-object", "--stdin", "--path", MARKET], input=data, capture_output=True)
    if r.returncode != 0:
        raise Abort("git hash-object 失敗：" + r.stderr.decode("utf-8", "replace").strip())
    return r.stdout.decode().strip()


def publish(record, now, before_push=None, after_check=None):
    if git("diff", "--cached", "--name-only"):
        raise Abort("index 不乾淨")
    git("fetch", "-q", "origin", "main")
    base = rev("origin/main")
    backup_blob = blob_of(base)
    remote = strict_loads(git("show", f"{base}:{MARKET}"))
    # 候選內容只讀一次：同一份位元組同時用於 bootstrap 驗證與預期 blob，之後只拿它比對
    cand_bytes = Path(MARKET).read_bytes()
    cand_blob = _blob_for(cand_bytes)
    local = strict_loads(cand_bytes.decode("utf-8"))
    try:
        verdict = mb.check(local, remote, now)
    except mb.NotSafe as e:
        raise Abort(f"初始化檢查 NOT SAFE：{e}")
    if verdict != "OK":
        raise Abort(f"初始化檢查結果 {verdict}（遠端已是新格式？）")
    if rev("HEAD") != base:
        raise Abort("工作目錄 HEAD 不是最新的 origin/main，請先 reset 到 origin/main 再產生候選檔")
    if after_check:
        after_check()                                   # 測試掛勾：模擬驗證後有人改檔
    if Path(MARKET).read_bytes() != cand_bytes:
        raise Abort("候選 market.json 在驗證後被改動，中止、不發布")
    # Gate 會在此刻 git add 工作目錄檔；若其間又被改，_commit_and_pin 的 blob 比對（＝cand_blob）會中止
    tip = _commit_and_pin(base, cand_blob, "init market.json format (one-time)", before_push)
    rec = {"backup_main": base, "backup_market_blob": backup_blob, "init_commit": tip, "init_market_blob": cand_blob}
    Path(record).write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"[INIT] 已發布 {tip}；紀錄 {record}")
    return rec


def rollback(record, before_push=None):
    rec = json.loads(Path(record).read_text(encoding="utf-8"))
    if git("diff", "--cached", "--name-only"):
        raise Abort("index 不乾淨")
    git("fetch", "-q", "origin", "main")
    cur = rev("origin/main")
    if blob_of(cur) != rec["init_market_blob"]:
        raise Abort("遠端 market.json 已不是初始化版本（其他 writer 已發布新行情），中止回復、請重新核對")
    git("reset", "-q", "--hard", cur)                    # 只動本機隔離 worktree
    Path(MARKET).write_bytes(subprocess.run(["git", "show", f"{rec['backup_main']}:{MARKET}"],
                                            capture_output=True, check=True).stdout)
    if git("hash-object", MARKET) != rec["backup_market_blob"]:
        raise Abort("備份 market.json 內容與紀錄不符")
    tip = _commit_and_pin(cur, rec["backup_market_blob"], "revert market.json format init (compensating)", before_push)
    print(f"[ROLLBACK] 已發布補償 commit {tip}")
    return tip


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("publish", "rollback"))
    ap.add_argument("--record", required=True)
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    try:
        if a.action == "publish":
            now = (datetime.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now
                   else datetime.datetime.now(TZ).replace(tzinfo=None))
            publish(a.record, now)
        else:
            rollback(a.record)
    except Exception as e:
        print(f"::error::[INIT] 中止：{type(e).__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
