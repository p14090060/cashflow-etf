"""scripts/publish_gate.py
fetch.yml 的提交／推送關卡。PO 決策：本次要發布的任何 JSON 不合格 → 整批不 commit、不 push。

驗證對象＝實際會被發布的內容，不只是傳入清單：
  0. 起始狀態：index 必須與 HEAD 相同（不得有事先 stage 的東西）。
  1. 允許清單內每一份工作目錄檔案：嚴格 JSON＋json_safe.VALIDATORS 契約。任何一份不合格 → 整批阻擋。
  2. git add 允許清單 → 實際 staged 檔案必須 ⊆ 允許清單，且每一份 index blob 再驗一次。
  3. commit（沒有變更就不 commit，但仍檢查 outgoing）。
  4. git pull --rebase 後，先把 origin/main 與 HEAD 固定成兩個完整 SHA（base、tip），檢查
     「全部 outgoing commits」（base..tip）：不得有 merge commit；每個 commit 改到的檔案都必須在允許清單內、
     不得刪除；每個 commit 中被改到的 JSON 都要驗證；tip 快照中的允許清單檔案也要驗證。
  5. push 前再確認 HEAD 仍是 tip；變了（並行 writer）→ fail-closed 整次中止。
     推送 git push origin <tip SHA>:refs/heads/main——推的是驗證過的固定 SHA，不重新解析 HEAD；
     不使用 force，被拒絕就失敗，不重試、不強推。

D-014 同一版本資格依據：_base.json／market.json 的商品政策、MG-1 移除與 market／_base 一致性檢查，
  使用的 etf_pool_cache.json（ETF 類型證據）與 excluded_products.json（排除／PO_REMOVED 依據）一律取「被驗資料
  的同一個版本」：工作目錄驗工作目錄、index 驗 index、每個 outgoing commit 驗該 commit、tip 驗 tip。
  後面的 commit 新增的核准不能掩蓋前面 commit 的未核准縮水；工作目錄偽造的證據影響不到 index／歷史／tip。
  證據或排除清單有變動時，即使 _base.json／market.json 本身沒變，也以新依據重驗允許清單內的這兩份。

D-022 配息日曆成對（O2 BLOCKER-1）：允許清單同時含 _base.json 與 dividend_info.json 時，工作目錄、index、
  每個 outgoing commit、tip 四層各自的快照中，兩份 calendar 都必須存在且完全相同；只改一份也要比。
  只列其中一份的發布路徑不檢查（未涵蓋，見工作單 10 交接）。

任何一步不通過或出例外 → exit 1，GITHUB_OUTPUT 寫 degraded=true／blocked=<原因>；
在 push 之前就決定，不會「先推再報錯」。通過 → degraded=false。
GITHUB_OUTPUT 另寫 pushed=<實際推送的完整 SHA>；沒有推送（無變更、--no-push、失敗）→ pushed= 空值。
exit 0 不等於一定有推送，呼叫端要看 pushed。

--base SHA（update-data 用）：固定基線。開始時 HEAD 必須就是這個 SHA；不做 pull --rebase，
  所有「上一版」比較都對這個 SHA；只推 base 的直接後代。遠端已前進 → 非 force push 被拒 → exit 1，
  由呼叫端從新基線重新產生、重新驗證（不把舊候選 rebase 到新遠端上）。
--expect 檔案=sha256（可重複）：Guard 判定前記下的候選位元組 SHA256。Gate 只讀一次工作目錄檔、核對 SHA256，
  驗證的就是這份位元組；stage 後 index 內容必須就是這份位元組（只容許 git 本身的 CRLF→LF 轉換），
  要推送的 tip 中該檔必須是 stage 時那個 blob，否則中止（候選中途被換掉）。

用法：python scripts/publish_gate.py [--no-push] [--message MSG] [--base SHA] [--expect 檔案=sha256]... 檔案...
"""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from json_safe import validate_text   # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class GateAbort(Exception):
    pass


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True)
    if check and r.returncode != 0:
        raise GateAbort(f"git {' '.join(args)} 失敗：{r.stderr.decode('utf-8', 'replace').strip()}")
    return r


def lines(*args):
    return [l for l in git(*args).stdout.decode("utf-8", "replace").splitlines() if l.strip()]


EVID, EXCL = "data/etf_pool_cache.json", "data/excluded_products.json"


def _ctx(read):
    """同一版本的資格依據：read(路徑) → 文字或 None。"""
    return {"evidence": read(EVID), "excluded": read(EXCL)}


def _ctx_differs(a, b):
    """兩個版本的資格依據內容是否不同（以 JSON 內容比，不受換行符號影響；解析不了就比文字）。"""
    for k in ("evidence", "excluded"):
        x, y = a.get(k), b.get(k)
        try:
            if json.loads(x) != json.loads(y):
                return True
        except Exception:
            if x != y:
                return True
    return False


def _listed(ctx):
    import product_policy
    if ctx is None or ctx.get("excluded") is None:
        raise ValueError("同一版本缺 excluded_products.json，無法確認排除依據")
    return product_policy.listed_codes(text=ctx["excluded"])


def _valid(name, text, policy=True, ctx=None):
    """policy：這份內容是本次要發布的新資料（與上游不同）→ _base.json／market.json 另套商品收錄政策
    （K／ETN 不得寫入）。未變動、與上游相同的舊檔只驗原契約，不因政策前的歷史內容整批阻擋。
    ctx：被驗版本的證據／排除清單（_ctx）。"""
    try:
        validate_text(name, text, policy=policy, ctx=ctx)
        return None
    except Exception as e:                     # DataInvalid／ValueError（含 JSONDecodeError）／其他
        return f"{type(e).__name__}: {e}"


_SET_FILES = ("market.json", "_base.json")


def _removals(name, text, prev, ctx):
    """MG-1：要發布的 market.json／_base.json 不得比上一版（上游／outgoing 前一版／推送基準）少任何一般 ETF；
    只有 K 尾碼與 excluded_products.json 可以消失。上一版不存在（首次建立）→ 不比。回傳錯誤字串或 None。"""
    if Path(name).name not in _SET_FILES or prev is None or text is None or text == prev:
        return None
    try:
        import product_policy
        from json_safe import strict_loads
        gone = product_policy.unapproved_removals(strict_loads(prev).get("etfs"), strict_loads(text).get("etfs"),
                                                  listed=_listed(ctx))
    except Exception as e:
        return f"無法核對商品集合（{type(e).__name__}: {e}）"
    return f"比上一版少了 {len(gone)} 檔一般 ETF（未經核准的移除）：{gone[:10]}" if gone else None


def _sync(read, ctx):
    """MG-1：同一個快照裡要發布的 market.json 必須與 _base.json 商品集合一致（market＝base 扣掉 K／ETN 清單），
    不能用一份縮水的資料搭配另一份合格資料。read(檔名) → 文字或 None；任一份不存在 → 不比。"""
    m, b = read("data/market.json"), read("data/_base.json")
    if m is None or b is None:
        return None
    try:
        import product_policy
        from json_safe import strict_loads
        miss, extra = product_policy.market_base_mismatch(strict_loads(m).get("etfs"), strict_loads(b).get("etfs"),
                                                          listed=_listed(ctx))
    except Exception as e:
        return f"無法核對 market.json／_base.json 商品集合（{type(e).__name__}: {e}）"
    if miss or extra:
        return f"market.json 與 _base.json 商品集合不一致：market 缺 {miss[:10]}、多出 {extra[:10]}"
    return None


CAL_PAIR = ("data/_base.json", "data/dividend_info.json")


def _cal_pair(read):
    """O2 BLOCKER-1（D-022）：允許清單同時含 _base.json 與 dividend_info.json 時，同一個快照中兩份的 calendar
    必須存在、是陣列且內容完全相同（含順序）。不論本次改了幾份都比——一新一舊（寫入中斷／回寫失敗）時
    兩份各自合法，只有這裡擋得住。read(檔名) → 文字或 None；任一份不存在／無法解析／缺 calendar → 不合格。"""
    try:
        from json_safe import strict_loads
        cals = []
        for f in CAL_PAIR:
            text = read(f)
            if text is None:
                return f"同一快照缺 {f}，無法核對兩份 calendar"
            obj = strict_loads(text)
            if not isinstance(obj, dict) or not isinstance(obj.get("calendar"), list):
                return f"{f} 缺 calendar 陣列，無法核對兩份 calendar"
            cals.append(obj["calendar"])
    except Exception as e:
        return f"無法核對 _base.json／dividend_info.json calendar（{type(e).__name__}: {e}）"
    if cals[0] != cals[1]:
        return f"_base.json 與 dividend_info.json 的 calendar 不一致（{len(cals[0])} 筆 vs {len(cals[1])} 筆）"
    return None


def _pair_listed(allowed):
    return all(f in allowed for f in CAL_PAIR)


def blob(ref_path):
    r = git("show", ref_path, check=False)
    return None if r.returncode != 0 else r.stdout.decode("utf-8")


def output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def check_outgoing(allowed, base, tip):
    """outgoing commits（base..tip，兩端都是固定 SHA）全部檢查：無 merge、只改允許清單、不刪檔、
    改到的 JSON 每個版本都合格；再驗 tip 快照中的允許清單檔。"""
    if lines("rev-list", "--merges", f"{base}..{tip}"):
        raise GateAbort("outgoing 含 merge commit")
    for c in lines("rev-list", "--reverse", f"{base}..{tip}"):
        cx = _ctx(lambda p, c=c: blob(f"{c}:{p}"))          # 這個 commit 自己的資格依據
        changed = []
        for row in lines("diff-tree", "--no-commit-id", "-r", "--name-status", "--no-renames", c):
            st, path = row.split("\t", 1)
            if path not in allowed:
                raise GateAbort(f"outgoing commit {c[:8]} 改到未核准的檔案：{path}")
            if st == "D":
                raise GateAbort(f"outgoing commit {c[:8]} 刪除了 {path}")
            changed.append(path)
            text = blob(f"{c}:{path}")
            err = None if text is not None else "讀不到"
            err = err or _valid(path, text, ctx=cx) or _removals(path, text, blob(f"{c}^:{path}"), cx)
            if err:
                raise GateAbort(f"outgoing commit {c[:8]} 的 {path} 不合格：{err}")
        if EVID in changed or EXCL in changed:                # 依據變了：以新依據重驗允許清單內的 _base／market
            for f in allowed:
                if Path(f).name in _SET_FILES and f not in changed:
                    text = blob(f"{c}:{f}")
                    err = text is not None and _valid(f, text, ctx=cx)
                    if err:
                        raise GateAbort(f"outgoing commit {c[:8]} 更新資格依據後 {f} 不合格：{err}")
        if "data/market.json" in allowed:
            err = _sync(lambda p, c=c: blob(f"{c}:{p}"), cx)
            if err:
                raise GateAbort(f"outgoing commit {c[:8]}：{err}")
        if _pair_listed(allowed):                             # 每個 outgoing commit 自己的快照
            err = _cal_pair(lambda p, c=c: blob(f"{c}:{p}"))
            if err:
                raise GateAbort(f"outgoing commit {c[:8]}：{err}")
    tx = _ctx(lambda p: blob(f"{tip}:{p}"))
    ctx_changed = _ctx_differs(tx, _ctx(lambda p: blob(f"{base}:{p}")))
    for f in allowed:
        text = blob(f"{tip}:{f}")
        prev = blob(f"{base}:{f}")
        if text is not None and (_valid(f, text, policy=text != prev or ctx_changed, ctx=tx)
                                 or _removals(f, text, prev, tx)) is not None:
            raise GateAbort(f"要推送的 {tip[:8]} 中 {f} 不合格")
    if "data/market.json" in allowed:
        err = _sync(lambda p: blob(f"{tip}:{p}"), tx)
        if err:
            raise GateAbort(f"要推送的 {tip[:8]}：{err}")
    if _pair_listed(allowed):
        err = _cal_pair(lambda p: blob(f"{tip}:{p}"))
        if err:
            raise GateAbort(f"要推送的 {tip[:8]}：{err}")


def rev(ref):
    return lines("rev-parse", "--verify", ref + "^{commit}")[0]


def _pin_expect(expect):
    """--expect：讀一次工作目錄檔、核對 SHA256；回傳 {檔案: 位元組}。之後驗證都用這份位元組。"""
    pinned = {}
    for f, h in (expect or {}).items():
        b = Path(f).read_bytes() if Path(f).exists() else None
        if b is None or hashlib.sha256(b).hexdigest() != h:
            raise GateAbort(f"工作目錄的 {f} 不是 Guard 判定過的候選（SHA256 不符）")
        pinned[f] = b
    return pinned


def _blob_id(ref_path):
    r = git("rev-parse", "--verify", "-q", ref_path, check=False)
    return r.stdout.decode().strip() if r.returncode == 0 else None


def _staged_blobs(pinned):
    """stage 後：index 內容必須就是 pinned 位元組（只容許 CRLF→LF 轉換）；回傳 {檔案: index blob SHA}。"""
    ids = {}
    for f, b in pinned.items():
        ids[f] = _blob_id(f":{f}")
        r = git("cat-file", "blob", ids[f], check=False) if ids[f] else None
        if r is None or r.returncode != 0 or r.stdout not in (b, b.replace(b"\r\n", b"\n")):
            raise GateAbort(f"index 中的 {f} 不是 Guard 判定過的候選")
    return ids


def _check_tip(ids, tip):
    for f, h in ids.items():
        if _blob_id(f"{tip}:{f}") != h:
            raise GateAbort(f"要推送的 {tip[:8]} 中的 {f} 不是 stage 時驗證的那一份")


def run(files, message, push=True, after_stage=None, before_push=None, upstream="origin/main", base=None, expect=None):
    """回傳 exit code。after_stage／before_push：測試用掛勾（stage 後／驗證完成、push 前）。
    base：固定基線完整 SHA（見檔頭 --base）；expect：{檔案: SHA256}（見檔頭 --expect）。"""
    allowed = set(files)
    staged = []
    pushed = ""
    try:
        if base is not None:
            if len(base) != 40 or rev(base) != base:
                raise GateAbort(f"--base 必須是存在的完整 commit SHA：{base!r}")
            if rev("HEAD") != base:
                raise GateAbort(f"開始時 HEAD（{rev('HEAD')[:8]}）不是固定基線 {base[:8]}")
            upstream = base
        for f in (expect or {}):
            if f not in allowed:
                raise GateAbort(f"--expect 的 {f} 不在允許清單")
        pinned = _pin_expect(expect)
        # 0. 起始 index 必須乾淨
        pre = lines("diff", "--cached", "--name-only")
        if pre:
            raise GateAbort(f"開始前已有 staged 變更：{', '.join(pre)}")
        # 1. 工作目錄：任何一份不合格 → 整批阻擋
        present = [f for f in files if Path(f).exists()]
        bad = []
        # 工作目錄快照：--expect 固定過的檔一律用那份位元組（Guard 判定的候選），其餘讀檔；
        # 資格依據、商品政策、MG-1、market／_base 同步、calendar 成對全部用同一個 wread
        wread = lambda p: (pinned[p].decode("utf-8") if p in pinned else                       # noqa: E731
                           (Path(p).read_text(encoding="utf-8") if Path(p).exists() else None))
        wx = _ctx(wread)                                      # 工作目錄版本的資格依據
        ctx_changed = _ctx_differs(wx, _ctx(lambda p: blob(f"{upstream}:{p}")))
        for f in present:
            text = wread(f)
            up = blob(f"{upstream}:{f}")
            e = _valid(f, text, policy=text != up or ctx_changed, ctx=wx) or _removals(f, text, up, wx)
            if e:
                bad.append((f, e))
        if "data/market.json" in allowed:
            e = _sync(wread, wx)
            if e:
                bad.append(("data/market.json", e))
        if _pair_listed(allowed):
            e = _cal_pair(wread)
            if e:
                bad.append(("data/dividend_info.json", e))
        if bad:
            raise GateAbort("驗證失敗，整批不發布：" + "；".join(f"{f}（{e}）" for f, e in bad))
        # 2. stage＋檢查實際 staged 清單與 index 內容
        if present:
            git("add", "--", *present)
            staged = present
        if after_stage:
            after_stage()
        ids = _staged_blobs(pinned)
        actual = lines("diff", "--cached", "--name-only")
        extra = [f for f in actual if f not in allowed]
        if extra:
            raise GateAbort(f"staged 清單含未核准檔案：{', '.join(extra)}")
        ix = _ctx(lambda p: blob(f":{p}"))                 # index 版本的資格依據
        for f in actual:
            text = blob(f":{f}")
            err = "index 中讀不到（刪除？）" if text is None else (_valid(f, text, ctx=ix)
                                                              or _removals(f, text, blob(f"{upstream}:{f}"), ix))
            if err:
                raise GateAbort(f"{f} 在 index 中不合格：{err}")
        if _pair_listed(allowed):                             # index 快照（含未 stage 變動的那一份）
            err = _cal_pair(lambda p: blob(f":{p}"))
            if err:
                raise GateAbort(f"index 中{err}")
        # 3. commit
        if actual:
            git("commit", "-q", "-m", message)
        staged = []
        # 4. rebase 後固定兩端 SHA，檢查全部 outgoing（之後只認這兩個 SHA，不再解析 HEAD）
        fixed = base is not None
        if not fixed:
            if push:
                git("pull", "-q", "--rebase", "origin", "main")
            base = rev(upstream)
        tip = rev("HEAD")
        if fixed and tip != base and lines("rev-list", "--parents", "-n", "1", tip)[0].split()[1:] != [base]:
            raise GateAbort(f"要推送的 {tip[:8]} 不是固定基線 {base[:8]} 的直接後代")
        check_outgoing(allowed, base, tip)
        _check_tip(ids, tip)
        if not lines("rev-list", f"{base}..{tip}"):
            print("[GATE] 沒有要發布的 commit")
        elif push:
            if before_push:
                before_push()
            # 驗證後本地 HEAD 有變動 ＝ 有並行 writer：fail-closed，整次不推送
            if rev("HEAD") != tip:
                raise GateAbort(f"驗證後 HEAD 變動（{tip[:8]} → {rev('HEAD')[:8]}），疑似並行寫入，整次中止")
            # 5. 推送已驗證的固定 SHA（不 force）
            git("push", "-q", "origin", f"{tip}:refs/heads/main")
            print(f"[GATE] 已推送 {tip[:8]}：{', '.join(actual) or '(無新變更)'}")
            pushed = tip
    except Exception as e:
        if staged:
            git("reset", "-q", "--", *staged, check=False)
        print(f"::error::發布關卡阻擋，本次不提交也不推送：{e}")
        output(degraded="true", blocked=str(e).replace("\n", " ")[:200], pushed="")
        return 1
    output(degraded="false", blocked="", pushed=pushed)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--message", default="chore: update ETF base data")
    ap.add_argument("--base")
    ap.add_argument("--expect", action="append", default=[])
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    try:
        expect = dict(x.split("=", 1) for x in a.expect)
    except ValueError:
        print(f"::error::--expect 格式應為 檔案=blob：{a.expect}")
        output(degraded="true", blocked="--expect 格式錯誤", pushed="")
        return 1
    return run(a.files, a.message, push=not a.no_push, base=a.base, expect=expect or None)


if __name__ == "__main__":
    sys.exit(main())
