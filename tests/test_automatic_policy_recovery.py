"""D-071：配息政策缺值自動查證、同輪採用、發布與門檻通知 — 限定離線驗收。

全部離線：本程序 socket／DNS／curl_cffi 原生封鎖；git 只用本機 file 傳輸（暫存 bare 當假遠端）。
官方來源：SITCA 2026-09 ETF 基本資料月報原件（tests/fixtures/automatic_policy_recovery，sha256 對 MANIFEST）；
TWSE 公告以替身回應（查無／失敗／明確公告），不連網。TG 以替身接收（成功／失敗可控）。時鐘以 daily_check._now 固定。
真路徑：daily_check.cli()（--defer-notifications／--send-prepared）、fetch.yml 既有「Commit and push」同一組 git 指令、
mis_fetcher.main()（休市時鐘，不連 MIS）。
用法：python tests/test_automatic_policy_recovery.py [--out 證據目錄]
"""
import contextlib, copy, datetime, hashlib, importlib.util, io, json, os, shutil, socket, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "automatic_policy_recovery"
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path(tempfile.mkdtemp(prefix="d071_out_"))
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp(prefix="d071_"))
results, NET = [], []


def _blocked(*a, **k):
    NET.append(repr(a[:2])); raise OSError("D-071 offline: network blocked")


socket.socket.connect = lambda self, *a, **k: _blocked(*a)
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
try:
    import curl_cffi as _cc
    _cc.Curl.perform = _blocked
    _cc.AsyncCurl.add_handle = _blocked
except (ImportError, AttributeError):
    pass
for k in list(os.environ):
    if k.startswith(("TELEGRAM", "TG_", "FINMIND", "HEALTHCHECK", "GITHUB")):
        os.environ.pop(k)
os.environ["GIT_ALLOW_PROTOCOL"] = "file"


def check(name, ok, detail=""):
    results.append({"name": name, "ok": bool(ok), "detail": detail if isinstance(detail, (dict, list)) else str(detail)[:1500]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  -> " + str(detail)[:800]), flush=True)
    return bool(ok)


sha = lambda b: hashlib.sha256(b).hexdigest()
TZ = datetime.timezone(datetime.timedelta(hours=8))
T0 = datetime.datetime(2026, 10, 23, 9, 0, tzinfo=TZ).timestamp()
H = 3600
MAN = {m["file"]: m for m in json.loads((FIX / "MANIFEST.json").read_text(encoding="utf-8"))}
SITCA = (FIX / "sitca_202609.html").read_bytes()
check("IN-0 SITCA 2026-09 月報原件 sha256＝MANIFEST（0bf78c00…）", sha(SITCA) == MAN["sitca_202609.html"]["sha256"])
BATCH24 = {"006205": "不配息", "006207": "不配息", "00636": "不配息", "00645": "不配息", "00657": "不配息", "00661": "年配",
           "00668": "不配息", "00678": "不配息", "00700": "不配息", "00703": "不配息", "00709": "不配息", "00737": "不配息",
           "00762": "不配息", "00861": "不配息", "00875": "不配息", "00876": "不配息", "00895": "不配息", "00897": "不配息",
           "00898": "不配息", "00899": "不配息", "00903": "季配", "00886": "不配息", "009806": "年配", "009807": "年配"}
SITCA_URL9 = "https://www.sitca.org.tw/ROC/SITCA_ETF/etf_statement2.aspx?txtR1=0&txtYM=202609"
SITCA_URL8 = "https://www.sitca.org.tw/ROC/SITCA_ETF/etf_statement2.aspx?txtR1=0&txtYM=202608"


def git(cwd, *a, check=True):
    r = subprocess.run(["git", "-c", "core.autocrlf=false", *a], cwd=cwd, capture_output=True)
    if check and r.returncode:
        raise RuntimeError("git %s: %s" % (a, r.stderr.decode("utf-8", "replace")))
    return r.stdout.decode("utf-8", "replace").strip()


def make_repo(tag, market_mut=None, info_mut=None):
    """暫存假遠端：本工作樹 HEAD 樹＋未 commit 的 D-071 產品檔，commit 進 bare；回傳 clone 路徑。"""
    src = TMP / (tag + "_src")
    src.mkdir()
    arc = subprocess.run(["git", "-c", "safe.directory=" + str(ROOT).replace("\\", "/"), "archive", "HEAD"], cwd=ROOT, capture_output=True, check=True).stdout
    import tarfile
    tarfile.open(fileobj=io.BytesIO(arc)).extractall(src)
    for f in ("scripts/official_frequency.py", "scripts/daily_check.py", "scripts/mis_fetcher.py", "fetch_etf.py"):
        shutil.copyfile(ROOT / f, src / f)
    m = json.loads((src / "data" / "market.json").read_text(encoding="utf-8"))
    m["updated"] = datetime.datetime.fromtimestamp(T0, TZ).strftime("%Y-%m-%d %H:%M")
    if market_mut:
        market_mut(m)
    (src / "data" / "market.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    if info_mut:
        i = json.loads((src / "data" / "dividend_info.json").read_text(encoding="utf-8"))
        info_mut(i)
        (src / "data" / "dividend_info.json").write_text(json.dumps(i, ensure_ascii=False, indent=2), encoding="utf-8")
    bare = TMP / (tag + ".git")
    git(TMP, "init", "-q", "--bare", "-b", "main", str(bare))
    git(src, "init", "-q", "-b", "main")
    for k, v in (("user.name", "d071"), ("user.email", "d071@test.invalid"), ("commit.gpgsign", "false")):
        git(src, "config", k, v)
    git(src, "add", "-A"); git(src, "commit", "-q", "-m", "base"); git(src, "remote", "add", "origin", str(bare))
    git(src, "push", "-q", "origin", "main")
    r = TMP / tag
    git(TMP, "clone", "-q", str(bare), str(r))
    for k, v in (("user.name", "github-actions[bot]"), ("user.email", "bot@test.invalid"), ("commit.gpgsign", "false")):
        git(r, "config", k, v)
    return r, bare


def sitca_ok(url):
    if url == SITCA_URL9:
        return SITCA
    raise OSError("not captured")


def twse_none(code, get=None):
    return {"status": "unresolved", "reason": "official policy unavailable or conflicting", "attempts": [{"status": "received"}]}


def load_daily(r, tag):
    for m in ("daily_check", "official_frequency"):
        sys.modules.pop(m, None)
    sys.path.insert(0, str(r / "scripts"))
    sp = importlib.util.spec_from_file_location("d071_daily_" + tag, r / "scripts" / "daily_check.py")
    d = importlib.util.module_from_spec(sp); sp.loader.exec_module(d)
    import official_frequency as of
    sys.path.remove(str(r / "scripts"))
    return d, of


def daily(r, tag, now, sitca=sitca_ok, twse=twse_none, tg_ok=True, mode="defer"):
    """真 daily_check：defer 模式準備訊息；回傳 (rc, prepared, log, sent, twse_calls)。"""
    d, of = load_daily(r, tag)
    sent, calls = [], []
    d.notify = lambda m: (sent.append(m), tg_ok)[1]
    d._now = lambda: now
    tw = lambda code, get=None: (calls.append(code), twse(code))[1]
    prep = TMP / ("prep_%s.json" % tag)
    with patch.object(of, "_get_sitca", sitca), patch.object(of, "resolve_frequency", tw), \
            contextlib.redirect_stdout(io.StringIO()) as buf, contextlib.redirect_stderr(buf):
        if mode == "defer":
            with patch.object(sys, "argv", ["daily", "--defer-notifications", str(prep)]):
                rc = d.cli()
        else:
            d.main(); rc = 0
    pj = json.loads(prep.read_text(encoding="utf-8")) if mode == "defer" else None
    (OUT / ("daily_%s.log" % tag)).write_text(buf.getvalue(), encoding="utf-8")
    return rc, pj, buf.getvalue(), sent, calls


PUBLISH = ["data/_base.json", "data/dividend_info.json", "data/dividend_calendar.json", "data/known_codes.json", "data/daily_state.json",
           "data/etf_pool_cache.json", "data/active_flow.json", "data/_active_snapshot.json"]


def publish(r, msg):
    """fetch.yml 既有「Commit and push」同一組指令（不修改 workflow，逐條照跑）。"""
    present = [f for f in PUBLISH if (r / f).exists()]
    git(r, "add", *present)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=r).returncode:
        git(r, "commit", "-q", "-m", msg)
    git(r, "pull", "-q", "--rebase", "origin", "main")
    git(r, "push", "-q")


def send(r, tag, prep_doc, tg_ok=True, publish_ok="true", before=None, now=None):
    d, _ = load_daily(r, tag)
    if now is not None:
        d._now = lambda: now
    sent = []
    d.notify = lambda m: (sent.append(m), tg_ok)[1]
    prep = TMP / ("send_%s.json" % tag)
    prep.write_text(json.dumps(prep_doc, ensure_ascii=False), encoding="utf-8")
    if before:
        before()
    with patch.object(sys, "argv", ["daily", "--send-prepared", str(prep)]), patch.dict(os.environ, {"ETF_PUBLISH_OK": publish_ok}), \
            contextlib.redirect_stdout(io.StringIO()) as buf, contextlib.redirect_stderr(buf):
        rc = d.cli()
    (OUT / ("send_%s.log" % tag)).write_text(buf.getvalue(), encoding="utf-8")
    return rc, sent, buf.getvalue()


def run_mis(r, tag, now=datetime.datetime(2026, 10, 24, 10, 0, tzinfo=TZ)):
    for m in ("mis_fetcher",):
        sys.modules.pop(m, None)
    sys.path.insert(0, str(r / "scripts"))
    try:
        sp = importlib.util.spec_from_file_location("d071_mis_" + tag, r / "scripts" / "mis_fetcher.py")
        mf = importlib.util.module_from_spec(sp); sp.loader.exec_module(mf)
        mf.tw_now = lambda: now
        mf._fetch_url = lambda url: (_ for _ in ()).throw(OSError("offline"))
        mf.time.sleep = lambda s: None
        with contextlib.redirect_stdout(io.StringIO()) as buf, contextlib.redirect_stderr(buf):
            try:
                mf.main(); st = "ok"
            except SystemExit as e:
                st = "exit %s" % e.code
    finally:
        sys.path.remove(str(r / "scripts"))
    return st, json.loads((r / "data" / "market.json").read_text(encoding="utf-8"))


rj = lambda r, f: json.loads((r / f).read_text(encoding="utf-8"))
origin = lambda bare, f: json.loads(subprocess.run(["git", "--git-dir", str(bare), "show", "main:" + f], capture_output=True).stdout.decode("utf-8"))
lines_of = lambda msgs: [l for m in msgs for l in m.splitlines()]

# ══ 1. 主路徑：發現缺值 → SITCA 查證 → 同輪候選 → 既有發布步驟 → 下輪讀回保持 ══
r, bare = make_repo("main")
info0 = rj(r, "data/dividend_info.json")
st0, mk0 = run_mis(r, "before")                       # 同時鐘、同資料的「修前」writer 輸出（對照用）
git(r, "checkout", "-q", "--", ".")                   # 修前輸出只作對照，不留在工作目錄
rc, pj, log, sent, calls = daily(r, "main1", T0)
info1 = rj(r, "data/dividend_info.json")
adopted = {c: info1["etfs"][c]["frequency"] for c in BATCH24 if c in info1["etfs"]}
check("A-1 真 daily_check：剩餘 24 檔全部由 SITCA 2026-09 月報（代號＋簡稱身分＋明確分類）同輪採用，頻率逐檔＝整批清單；"
      "不需逐檔 TWSE 查詢；K 類 4 檔不納入",
      adopted == BATCH24 and not any(c.endswith("K") for c in calls) and not [c for c in calls if c in BATCH24], {"diff": {c: (adopted.get(c), f) for c, f in BATCH24.items() if adopted.get(c) != f}, "calls": calls})
src_ok = all(info1["etfs"][c]["policy_source"]["sha256"] == sha(SITCA) and info1["etfs"][c]["policy_source"]["report_month"] == "202609"
             and info1["etfs"][c]["policy_source"]["url"] == SITCA_URL9 for c in BATCH24)
check("A-2 採用紀錄保存來源／月報月份／更新日／原件 hash／身分／分類；不填金額、月份、殖利率，_todo 仍 true；其他 148 筆逐筆不變",
      src_ok and all(info1["etfs"][c]["months"] == [] and info1["etfs"][c]["avg_dividend_per_share"] is None and info1["etfs"][c]["_todo"] is True
                     for c in BATCH24)
      and all(info1["etfs"][c] == v for c, v in info0["etfs"].items()) and set(info1["etfs"]) - set(info0["etfs"]) == set(BATCH24),
      [c for c, v in info0["etfs"].items() if info1["etfs"].get(c) != v])
known_conf = {c: s for c, s in rj(r, "data/daily_state.json")["policy_status"].items() if c not in BATCH24}
check("A-3 已知政策與最新 SITCA 分類不同（00735／00646／009808／00984A／009818）→ 不覆蓋，進衝突追蹤並排入 TWSE 替代來源查證（R1：狀態 4 衝突／1 排隊）",
      all(info1["etfs"][c]["frequency"] == info0["etfs"][c]["frequency"] for c in known_conf) and set(known_conf) == {"00735", "00646", "009808", "00984A", "009818"}
      and set(known_conf.values()) <= {1, 2, 4}, known_conf)
check("A-4 第一次就有衝突／缺值也不發求助：待發訊息不含求助標題、無 ack", not any("自動查證仍無解" in m for m in pj["messages"]) and "ack" not in pj, pj["messages"])
publish(r, "chore: update ETF base data (test round 1)")
rc_s, sent_s, log_s = send(r, "main1s", pj)
oi = origin(bare, "data/dividend_info.json")
check("A-5 既有發布步驟推到假遠端後，--send-prepared 核驗已發布 blob 通過（exit 0）；遠端 dividend_info 已含 24 檔採用值",
      rc_s == 0 and all(oi["etfs"][c]["frequency"] == f for c, f in BATCH24.items()), log_s[-400:])
st1, mk1 = run_mis(r, "after")
check("A-6 真 mis writer：24 檔 div_frequency＝採用值（writer 自行疊上，不手改 market）",
      st1 == "ok" and all({e["code"]: e for e in mk1["etfs"]}[c]["div_frequency"] == f for c, f in BATCH24.items()),
      {c: {e["code"]: e for e in mk1["etfs"]}[c].get("div_frequency") for c in BATCH24})
e0, e1 = {e["code"]: e for e in mk0["etfs"]}, {e["code"]: e for e in mk1["etfs"]}
allowed = {"div_frequency", "div_months", "div_avg_per_share", "div_category", "div_todo", "div_freq"}
fd = {c: sorted(k for k in set(e0[c]) | set(e1[c]) if e0[c].get(k) != e1[c].get(k)) for c in e0 if e0[c] != e1.get(c)}
check("A-7 其他商品不退化：200 檔集合／順序相同；差異只在 24 檔配息靜態欄位；價格、殖利率、熱度、訊號等數值全同；非未知 ETF 完全相同",
      [e["code"] for e in mk0["etfs"]] == [e["code"] for e in mk1["etfs"]] and set(fd) <= set(BATCH24)
      and all(set(v) <= allowed for v in fd.values()) and {k: v for k, v in mk0.items() if k != "etfs"} == {k: v for k, v in mk1.items() if k != "etfs"},
      fd)
git(r, "add", "data/market.json"); git(r, "commit", "-q", "-m", "market"); git(r, "push", "-q")
rc, pj2, log2, _, calls2 = daily(r, "main2", T0 + 6 * H)
info2 = rj(r, "data/dividend_info.json")
check("A-8 下一輪 daily 讀回：24 檔維持採用值（不被覆蓋回不明）、不再列為待查；不重複 SITCA 以外的查詢",
      all(info2["etfs"][c]["frequency"] == f for c, f in BATCH24.items())
      and not set(BATCH24) & set(rj(r, "data/daily_state.json")["policy_status"]) and not set(calls2) & set(BATCH24))

# ══ 2. 87176ee6 安全候選相容 ══
GIT87 = ["git", "-c", "safe.directory=C:/專案/etf/releases/d055/.git", "--git-dir", r"C:\專案\etf\releases\d055\.git"]
vd = TMP / "v87"; vd.mkdir()
ok87 = True
for f in ("json_safe.py", "official_frequency.py", "product_policy.py"):
    b = subprocess.run(GIT87 + ["show", "87176ee6b2cd1e6deebc535192f7a10086c70a4a:scripts/" + f], capture_output=True)
    ok87 &= b.returncode == 0
    (vd / f).write_bytes(b.stdout)
for m in ("json_safe", "official_frequency", "product_policy"):
    sys.modules.pop(m, None)
sys.path.insert(0, str(vd))
import json_safe as JS87, official_frequency as OF87   # noqa: E402
sys.path.remove(str(vd))
res87 = {}
for f in ("data/dividend_info.json", "data/daily_state.json"):
    try:
        JS87.validate_text(f, (r / f).read_text(encoding="utf-8")); res87[f] = "accepted"
    except Exception as e:
        res87[f] = "rejected: %r" % e
check("C-1 87176ee6 原版 json_safe 接受新 dividend_info 與 daily_state（全數值狀態）；其 effective_frequency 採用 24 檔（policy_source 不影響）",
      ok87 and set(res87.values()) == {"accepted"} and all(OF87.effective_frequency(c, info2["etfs"][c]) == f for c, f in BATCH24.items()), res87)

# ══ 3. 求助門檻：一次查無／排隊／暫時錯誤不通知；3 輪＋跨 24h 才通知；送達才記錄 ══
NOSRC = ["00903", "00886", "00899", "00898", "00897", "00895"]   # 從 SITCA 拿掉 → 只能靠 TWSE（替身查無）


def drop_rows(body, codes):
    t = body.decode("utf-8-sig")
    import re
    keep = lambda m: "" if any(re.search(r"<td[^>]*>\s*(?:<b>)?\s*%s\s*(?:</b>)?\s*</td>" % c, m.group(0)) for c in codes) else m.group(0)
    out = re.sub(r"<tr\b[^>]*>.*?</tr>", keep, t, flags=re.S | re.I)
    assert all(">%s<" % c not in out for c in codes)
    return out.encode("utf-8")


SITCA_MINUS = drop_rows(SITCA, NOSRC)
sitca_minus = lambda url: SITCA_MINUS if url == SITCA_URL9 else (_ for _ in ()).throw(OSError("not captured"))
r, bare = make_repo("help")
CONF5 = {"00735", "00646", "009808", "00984A", "009818"}
rounds = []
for i, t in enumerate((T0, T0 + 8 * H, T0 + 16 * H, T0 + 20 * H)):
    rc, pj, log, _, calls = daily(r, "help%d" % i, t, sitca=sitca_minus)
    publish(r, "round %d" % i)
    rounds.append((pj, calls, rj(r, "data/daily_state.json")))
helped = lambda pj: [l for l in lines_of(pj["messages"]) if l.startswith("• ") and "完成判讀" in l]
helped_codes = lambda pj: {l.split()[1] for l in helped(pj)}
check("H-1 輪替＋上限：6 檔缺值＋5 檔已知衝突都要查 TWSE 替代來源，每輪最多 4 檔、最久沒查優先，前 3 輪全部輪到；排隊者狀態＝1（不算查無）",
      all(len(c) <= 4 for _, c, _ in rounds) and set().union(*[set(c) for _, c, _ in rounds[:3]]) >= set(NOSRC) | CONF5
      and all(rounds[0][2]["policy_status"][c] == 1 for c in (set(NOSRC) | CONF5) - set(rounds[0][1])),
      [c for _, c, _ in rounds])
check("H-2 未達門檻（輪數不足或未滿 24 小時）→ 不發缺值求助（4 輪都沒有求助行）",
      not any(helped(pj) for pj, _, _ in rounds), [helped(pj) for pj, _, _ in rounds])


def until_help(tag, t0, n=12, **kw):
    """往後每小時跑一輪（照常發布），直到出現求助；回傳 (pj, 該輪 calls, state, 時間)。"""
    for k in range(n):
        rc, pj, log, _, calls = daily(r, "%s%d" % (tag, k), t0 + k * H, sitca=sitca_minus, **kw)
        publish(r, "%s %d" % (tag, k))
        if helped(pj):
            return pj, calls, rj(r, "data/daily_state.json"), t0 + k * H
    return None, None, rj(r, "data/daily_state.json"), None


pj5, calls5, st5, t5 = until_help("help_due", T0 + 49 * H)
due_ok = pj5 is not None and all(
    c in calls5 and st5["policy_rounds"][c] >= 3 and t5 - st5["policy_first"][c] >= 24 * H and st5["policy_status"][c] in (4, 5)
    for c in helped_codes(pj5))
check("H-3 達門檻才彙整求助：只列本輪實際完成查證（本輪有查 TWSE）且完成 ≥3 輪、首末跨 24h 者；每檔寫明本輪實際已查 SITCA 月報＋TWSE 公告；"
      "標題聲明只支援這兩個自動來源、其他發行人未支援",
      due_ok and all("本輪已查 SITCA 202609 月報＋TWSE 公告" in l for l in helped(pj5))
      and any("支援的自動來源只有" in l and "不代表所有官方皆查無" in l for l in lines_of(pj5["messages"])) and pj5.get("ack"),
      {"lines": helped(pj5) if pj5 else None, "calls": calls5})
rc_f, sent_f, log_f = send(r, "help_tgfail", pj5, tg_ok=False)
st_f = origin(bare, "data/daily_state.json")
failed_codes = helped_codes(pj5)
again = set()
for k in range(6):
    rc, pjx, _, _, _ = daily(r, "help_again%d" % k, t5 + (k + 1) * H, sitca=sitca_minus)
    publish(r, "again %d" % k)
    again |= helped_codes(pjx) & failed_codes
    if again == failed_codes:
        break
check("H-4 求助 TG 失敗 → 不寫回執（log 註明下輪重送）、遠端無 policy_notified；之後輪到該檔完成查證時照列（不被去重壓掉）",
      "下輪仍會重送" in log_f and not st_f.get("policy_notified") and again == failed_codes, {"log": log_f[-300:], "again": sorted(again)})
pj6 = pjx
head_before = git(r, "rev-parse", "HEAD")
rc_o, sent_o, log_o = send(r, "help_tgok", pj6, tg_ok=True, now=t5 + 9 * H)
st_o = origin(bare, "data/daily_state.json")
git(r, "fetch", "-q", "origin")
files = git(r, "show", "--name-only", "--format=", "origin/main")
ack_parent = git(r, "rev-parse", "origin/main^")
git(r, "reset", "-q", "--hard", "origin/main")       # 模擬下一輪 Actions 全新 checkout（回執 commit 只在遠端，不動本機）
acked = set(pj6["ack"]["codes"]["policy_notified"])
relisted = set()
for k in range(6):
    rc, pj7, _, _, _ = daily(r, "help_after%d" % k, t5 + 10 * H + k * H, sitca=sitca_minus)
    publish(r, "after %d" % k)
    relisted |= helped_codes(pj7) & acked
check("H-5 求助送達 → 回執 commit 為發布版直接後代、只改 daily_state、遠端有 policy_notified；已送達代號之後 6 輪（14 天內）都不再列",
      rc_o == 0 and st_o.get("policy_notified") and ack_parent == head_before
      and files.splitlines() == ["data/daily_state.json"] and not relisted,
      {"rc": rc_o, "notified": st_o.get("policy_notified"), "parent": ack_parent, "head": head_before,
       "log": log_o[-400:], "files": files, "relisted": sorted(relisted)})
rc_p, sent_p, _ = send(r, "help_pubfail", pj6, publish_ok="false")
check("H-6 發布失敗（ETF_PUBLISH_OK=false）→ 只送未宣告恢復、不送求助、exit 1", rc_p == 1 and all("尚未宣告恢復" in m for m in sent_p), sent_p)

# ══ R1（D071_R1_INSTRUCTIONS）══
# ── F1 已知衝突查替代來源；本輪暫時失敗／排隊不借舊狀態求助 ──
TW_FIX = {"00646": "不配息", "00735": "半年配"}            # 00646：TWSE＝現有（衝突解除）；00735：TWSE 也和現有不同（仍矛盾）


def twse_conf(code, get=None):
    if code in TW_FIX:
        return {"status": "verified", "code": code, "frequency": TW_FIX[code], "checked_at": "2026-10-23T09:00:00+08:00",
                "sources": [{"code": code, "frequency": TW_FIX[code], "url": "https://www.twse.com.tw/zh/ETFortune/newsDetail/ab%s" % code[-2:],
                             "sha256": "3" * 64}], "attempts": [{"status": "received"}]}
    return {"status": "unresolved", "reason": "official policy unavailable or conflicting", "attempts": [{"status": "failed"}]}


r, bare = make_repo("r1conf")
calls_all, states = [], []
for k in range(3):
    _, pjc, _, _, calls = daily(r, "r1conf%d" % k, T0 + k * 13 * H, twse=twse_conf)
    publish(r, "r1conf %d" % k)
    calls_all.append(calls)
    states.append(rj(r, "data/daily_state.json"))
infoc = rj(r, "data/dividend_info.json")["etfs"]
stc = states[-1]
check("R1-F1a 真 daily：5 檔已知衝突都實際查了 TWSE 替代來源（輪替、每輪 ≤4）；00646 TWSE＝現有政策 → 衝突解除（不再追蹤、資料不改）；"
      "00735 TWSE 仍與現有不同 → 保留原政策、記衝突且算完成；其餘 TWSE 讀取失敗 → 暫時失敗、完成輪數 0",
      set().union(*map(set, calls_all)) >= CONF5 and all(len(c) <= 4 for c in calls_all)
      and "00646" not in stc["policy_status"] and infoc["00646"]["frequency"] == info0["etfs"]["00646"]["frequency"]
      and stc["policy_status"].get("00735") == 4 and infoc["00735"]["frequency"] == info0["etfs"]["00735"]["frequency"]
      and stc["policy_rounds"].get("00735", 0) >= 1
      and all(stc["policy_status"][c] in (1, 2) and not stc["policy_rounds"].get(c) for c in ("009808", "009818", "00984A")),
      {"calls": calls_all, "status": stc["policy_status"], "rounds": stc.get("policy_rounds")})
# 舊版行為對照：衝突不查 TWSE（X 探針 twse_calls=[]）——此處以同輸入確認新版確實有查
check("R1-F1b 修前對照：X 探針中 5 檔衝突 TWSE 呼叫 0 次；修後同輸入第一輪就對其中 4 檔發出 TWSE 查詢",
      len(set(calls_all[0]) & CONF5) == 4, calls_all[0])
sys.path.insert(0, str(ROOT / "scripts"))
for m in ("daily_check", "official_frequency"):
    sys.modules.pop(m, None)
import daily_check as DC   # noqa: E402
import official_frequency as OFm   # noqa: E402
sys.path.remove(str(ROOT / "scripts"))
hist = {"policy_status": {"X": 5}, "policy_first": {"X": T0}, "policy_rounds": {"X": 3}, "policy_notified": {}, "frequency_recovery": {"X": T0}}
for label, s in (("TEMP_FAIL", OFm.TEMP_FAIL), ("QUEUED", OFm.QUEUED)):
    stx = copy.deepcopy(hist)
    due = DC.update_policy_state(stx, {"status": {"X": s}, "completed": [], "twse_tried": [], "detail": {}, "checked": {}}, T0 + 48 * H)
    check("R1-F1c 歷史已 3 輪無解、跨 48h；本輪 %s → due 為空（不借用舊無解冒稱本輪查完）、歷史輪數保留 3、狀態照實記為 %d" % (label, s),
          due == [] and stx["policy_rounds"]["X"] == 3 and stx["policy_status"]["X"] == s, {"due": due, "state": stx})
stx = copy.deepcopy(hist)
due = DC.update_policy_state(stx, {"status": {"X": OFm.NO_RESULT}, "completed": ["X"], "twse_tried": ["X"], "detail": {}, "checked": {}}, T0 + 48 * H)
check("R1-F1d 同歷史、本輪實際完成查證仍無解 → 才列入 due（輪數 4）", due == ["X"] and stx["policy_rounds"]["X"] == 4, stx)
# 真 daily：先累積到門檻，再讓本輪 SITCA 暫時失敗 → 不發求助
r, bare = make_repo("r1temp")
for k in range(9):
    daily(r, "r1temp%d" % k, T0 + k * 6 * H, sitca=sitca_minus)
    publish(r, "r1temp %d" % k)
stt = rj(r, "data/daily_state.json")
ripe = [c for c in NOSRC if stt["policy_rounds"].get(c, 0) >= 3]
_, pjt, _, _, _ = daily(r, "r1temp_fail", T0 + 60 * H, sitca=lambda u: (_ for _ in ()).throw(OSError("HTTP Error 403")),
                       twse=lambda c: {"status": "unresolved", "reason": "x", "attempts": [{"status": "failed"}]})
check("R1-F1e 真 daily：%d 檔已累積 ≥3 輪無解後，本輪 SITCA 403＋TWSE 失敗 → 不列任何求助（暫時失敗不算本輪查完）" % len(ripe),
      ripe and not helped(pjt), {"ripe": ripe, "helped": helped(pjt)})

# ── F2 壞 policy_source：daily／fetch／mis 一致拒用 ──
BAD661 = None


def bad661(i):
    global BAD661
    BAD661 = dict(info2["etfs"]["00661"], frequency="季配", policy_source=dict(info2["etfs"]["00661"]["policy_source"],
                                                                               url="https://evil.example/fake", frequency="季配"))
    i["etfs"]["00661"] = BAD661


r, bare = make_repo("r1bad", info_mut=bad661)
fail_sitca = lambda u: (_ for _ in ()).throw(OSError("HTTP Error 403"))
fail_twse = lambda c: {"status": "unresolved", "reason": "x", "attempts": [{"status": "failed"}]}
daily(r, "r1bad", T0, sitca=fail_sitca, twse=fail_twse)
base_b = {e["code"]: e for e in rj(r, "data/_base.json")["etfs"]}
stb = rj(r, "data/daily_state.json")
git(r, "checkout", "-q", "--", "data/market.json") if subprocess.run(["git", "diff", "--quiet", "--", "data/market.json"], cwd=r).returncode else None
stm, mkb = run_mis(r, "r1bad")
eb = {e["code"]: e for e in mkb["etfs"]}
# 對照：同一 repo、同時鐘，把 00661 換成有效紀錄跑 mis
r2, _ = make_repo("r1good", info_mut=lambda i: i["etfs"].__setitem__("00661", info2["etfs"]["00661"]))
stg, mkg = run_mis(r2, "r1good")
eg = {e["code"]: e for e in mkg["etfs"]}
diffc = sorted(c for c in eg if eg[c] != eb.get(c))
check("R1-F2a 壞新來源（假網址、頻率季配）＋SITCA／TWSE 都不可用：真 daily 不把季配疊回 _base（00661 為暫時失敗待查）；"
      "真 mis writer 輸出 00661 div_frequency＝不明（X 探針修前為季配）",
      base_b["00661"].get("div_freq") != "季配" and base_b["00661"].get("div_frequency") != "季配" and stb["policy_status"].get("00661") == 2
      and stm == "ok" and eb["00661"]["div_frequency"] == "不明",
      {"base": {k: base_b["00661"].get(k) for k in ("div_freq", "div_frequency")}, "mis": eb["00661"].get("div_frequency")})
check("R1-F2b 同時鐘對照：有效證據版本 mis 輸出 00661＝年配；兩版 200 檔中只有 00661 不同（其他商品數值不變、既有靜態政策照常）",
      stg == "ok" and eg["00661"]["div_frequency"] == "年配" and diffc == ["00661"], diffc)
fsrc = (ROOT / "fetch_etf.py").read_text(encoding="utf-8")
import ast  # noqa: E402
fn = next(n for n in ast.parse(fsrc).body if isinstance(n, ast.FunctionDef) and n.name == "_load_confirmed_freq")
tmpdi = TMP / "fetch_di.json"
tmpdi.write_text(json.dumps({"etfs": {"00661": dict(BAD661, _todo=False), "00999": {"frequency": "年配", "_todo": False},
                                      "00998": dict(info2["etfs"]["00661"], _todo=False)}}, ensure_ascii=False), encoding="utf-8")
ns = {"OUT_DIV": tmpdi, "json": json, "_policy_source_problem": OFm.policy_source_problem}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "fetch_load_confirmed", "exec"), ns)
conf = ns["_load_confirmed_freq"]()
check("R1-F2c fetch_etf._load_confirmed_freq（實際函式）：壞新來源（即使 _todo:false）不當已確認；無新來源欄位的既有已核靜態政策照常採用",
      "00661" not in conf and conf.get("00999") == "年配", conf)

# ── F3 回執私有 index：不碰他人 stage／HEAD／工作檔 ──


def snapshot(rp):
    return {"index": subprocess.run(["git", "ls-files", "-s"], cwd=rp, capture_output=True).stdout,
            "cached": subprocess.run(["git", "diff", "--cached"], cwd=rp, capture_output=True).stdout,
            "head": git(rp, "rev-parse", "HEAD"),
            "work": (rp / "data" / "daily_state.json").read_bytes(), "other": (rp / "data" / "known_codes.json").read_bytes()}


def ack_case(tag, mutate, reject=False):
    rp, bp = make_repo(tag)
    pjx = None
    for k in range(14):
        _, pjk, _, _, _ = daily(rp, "%s%d" % (tag, k), T0 + k * 6 * H, sitca=sitca_minus)
        publish(rp, "%s %d" % (tag, k))
        if pjk.get("ack"):
            pjx = pjk
            break
    head = git(rp, "rev-parse", "HEAD")
    mutate(rp)
    if reject:
        (bp / "hooks" / "pre-receive").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    before = snapshot(rp)
    rc, _, log = send(rp, tag + "_send", pjx, tg_ok=True)
    after = snapshot(rp)
    tip = subprocess.run(["git", "--git-dir", str(bp), "rev-parse", "main"], capture_output=True).stdout.decode().strip()
    files = subprocess.run(["git", "--git-dir", str(bp), "diff-tree", "--no-commit-id", "--name-only", "-r", "main"], capture_output=True).stdout.decode().split()
    parent = subprocess.run(["git", "--git-dir", str(bp), "rev-parse", "main^"], capture_output=True).stdout.decode().strip()
    return {"ok_ack": "回執已保存" in log, "preserved": before == after, "tip_is_ack": tip != head and parent == head and files == ["data/daily_state.json"],
            "remote_unchanged": tip == head, "log": log[-300:], "had_ack": bool(pjx)}


def stage_same(rp):
    (rp / "data" / "daily_state.json").write_text('{"other_writer_stage": {"0050": 123}}', encoding="utf-8")
    git(rp, "add", "data/daily_state.json")


def stage_other(rp):
    (rp / "data" / "known_codes.json").write_text('["OTHER"]', encoding="utf-8")
    git(rp, "add", "data/known_codes.json")


def work_edit(rp):
    (rp / "data" / "daily_state.json").write_text('{"unstaged_other": {"0050": 1}}', encoding="utf-8")


cases = {"stage_same_file": ack_case("r1a1", stage_same), "stage_other_file": ack_case("r1a2", stage_other),
         "worktree_edit": ack_case("r1a3", work_edit), "own_plain": ack_case("r1a4", lambda rp: None),
         "reject_with_other_stage": ack_case("r1a5", stage_same, reject=True)}
check("R1-F3a 他人同檔 stage／他檔 stage／工作檔修改：回執照常以私有 index 推送（父＝發布版、只改 daily_state），本機 index／HEAD／工作檔逐位元不變",
      all(cases[k]["had_ack"] and cases[k]["ok_ack"] and cases[k]["tip_is_ack"] and cases[k]["preserved"]
          for k in ("stage_same_file", "stage_other_file", "worktree_edit", "own_plain")), cases)
check("R1-F3b 推送被拒（不 force／不重試）且他人已 stage 同檔 → 不保存、遠端不變、他人 index 內容完整保留（X 探針修前被 reset）",
      cases["reject_with_other_stage"]["had_ack"] and not cases["reject_with_other_stage"]["ok_ack"]
      and cases["reject_with_other_stage"]["remote_unchanged"] and cases["reject_with_other_stage"]["preserved"], cases["reject_with_other_stage"])

# 暫時錯誤：SITCA 403／逾時、TWSE 讀取失敗 → 一律暫時失敗，不累積輪數、不求助
r, bare = make_repo("temp")
sitca_fail = lambda url: (_ for _ in ()).throw(OSError("HTTP Error 403"))
twse_fail = lambda code: {"status": "unresolved", "reason": "official policy unavailable or conflicting", "attempts": [{"status": "failed"}]}
tp = []
for i in range(5):
    rc, pj, log, _, _ = daily(r, "temp%d" % i, T0 + i * 12 * H, sitca=sitca_fail, twse=twse_fail)
    publish(r, "temp %d" % i)
    tp.append(pj)
stt = rj(r, "data/daily_state.json")
check("T-1 SITCA 403／TWSE 失敗連續 5 輪、跨 48 小時 → 全部狀態暫時失敗（2）或排隊（1），完成輪數 0，不發缺值求助；資料不變",
      not any(helped(p) for p in tp) and not stt.get("policy_rounds") and set(stt["policy_status"].values()) <= {1, 2}
      and rj(r, "data/dividend_info.json") == info0, stt.get("policy_status"))
# 部分來源失敗不阻擋：SITCA 正常、TWSE 全失敗 → 24 檔照常採用
r, bare = make_repo("partial")
daily(r, "partial", T0, twse=twse_fail)
check("T-2 TWSE 全部失敗不影響 SITCA 已核政策：24 檔照常同輪採用", all(rj(r, "data/dividend_info.json")["etfs"][c]["frequency"] == f for c, f in BATCH24.items()))

# ══ 4. 錯誤證據拒用 ══
import re  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts"))
for m in ("official_frequency",):
    sys.modules.pop(m, None)
import official_frequency as OF   # noqa: E402
sys.path.remove(str(ROOT / "scripts"))
TODAY = datetime.date(2026, 10, 23)
text = SITCA.decode("utf-8-sig")
bad_bodies = {
    "pdf_body": b"%PDF-1.4 fake",
    "html_not_statement": b"<html><body>SITCA maintenance</body></html>",
    "wrong_month_page": text.replace("txtYM=202609", "txtYM=202608").encode("utf-8"),
    "future_update_date": text.replace(">2026.10.15<", ">2026.11.30<").encode("utf-8"),
    "update_before_month_end": text.replace(">2026.10.15<", ">2026.09.20<").encode("utf-8"),
    "header_changed": text.replace(">證券代號<", ">代碼<", 1).encode("utf-8"),
    "truncated_table": text[: text.find("<tr", text.find("table2")) + 2000].encode("utf-8"),
}
rej = {}
for k, b in bad_bodies.items():
    try:
        OF.parse_sitca(b, "202609", TODAY); rej[k] = "accepted"
    except (ValueError, UnicodeError) as e:
        rej[k] = "rejected"
st_ok = OF.parse_sitca(SITCA, "202609", TODAY)
st_ok.update(url=SITCA_URL9, sha256=sha(SITCA))
row_mut = copy.deepcopy(st_ok)
row_mut["rows"]["00661"] = row_mut["rows"]["00661"] + [("元大日經225", "元大日經225基金", "不分級別/分配(季配)")]
pol = {
    "name_mismatch": OF.sitca_policy("00661", "元大日經", st_ok, TODAY)[0],
    "multi_row_conflict": OF.sitca_policy("00661", "元大日經225", row_mut, TODAY)[0],
    "not_explicit(一年兩次)": OF.sitca_policy(next(c for c, rs in st_ok["rows"].items() if rs[0][2] == "不分級別/分配(一年兩次配息)"),
                                          st_ok["rows"][next(c for c, rs in st_ok["rows"].items() if rs[0][2] == "不分級別/分配(一年兩次配息)")][0][0], st_ok, TODAY)[0],
    "stale_report": OF.sitca_policy("00661", "元大日經225", st_ok, datetime.date(2027, 3, 1))[0],
    "absent_code": OF.sitca_policy("00000X", "x", st_ok, TODAY)[0],
}
check("E-1 SITCA 月報拒用：HTML 冒 PDF／非報表頁／表單月份不符／更新日在未來或早於月底／表頭變動／表格截斷 → 全部拒用",
      all(v == "rejected" for v in rej.values()), rej)
check("E-2 單檔判讀：簡稱身分不符、同代號多列矛盾 → 衝突；非明確頻率（一年兩次配息）、過期月報、表內沒有 → 不採用",
      pol == {"name_mismatch": "conflict", "multi_row_conflict": "conflict", "not_explicit(一年兩次)": "absent",
              "stale_report": "absent", "absent_code": "absent"}, pol)
ps_ok = info2["etfs"]["00661"]
bad_ps = {
    "code": dict(ps_ok, policy_source=dict(ps_ok["policy_source"], code="00662")),
    "freq": dict(ps_ok, policy_source=dict(ps_ok["policy_source"], frequency="季配")),
    "class": dict(ps_ok, policy_source=dict(ps_ok["policy_source"], classification="不分級別/不分配")),
    "url": dict(ps_ok, policy_source=dict(ps_ok["policy_source"], url="https://evil.example/x")),
    "sha": dict(ps_ok, policy_source=dict(ps_ok["policy_source"], sha256="xyz")),
    "type": dict(ps_ok, policy_source=["sitca"]),
    "kind": dict(ps_ok, policy_source=dict(ps_ok["policy_source"], kind="other")),
}
check("E-3 讀回壞 policy_source（代號／頻率／分類／網址／hash／型別／種類）→ 視為未知重新查證、不沿用；正常紀錄有效；壞型別不崩潰",
      OF.policy_source_problem("00661", ps_ok) is None and all(OF.known_policy("00661", m) is None for m in bad_ps.values()),
      {k: OF.policy_source_problem("00661", m) for k, m in bad_ps.items()})
# 壞 policy_source 在真 daily 下：重新查證並以有效來源覆寫（同一月報），不沿用壞值
r, bare = make_repo("badsrc", info_mut=lambda i: i["etfs"].__setitem__("00661", dict(bad_ps["freq"], frequency="季配")))
daily(r, "badsrc", T0)
check("E-4 真 daily：持久化壞證據（頻率被改成季配）→ 重新查證，改回官方月報的年配並寫入有效來源",
      rj(r, "data/dividend_info.json")["etfs"]["00661"]["frequency"] == "年配"
      and OF.policy_source_problem("00661", rj(r, "data/dividend_info.json")["etfs"]["00661"]) is None)
# 無歷史不推不配息：SITCA／TWSE 都沒有 → 不採用、不填
r, bare = make_repo("nohist")
daily(r, "nohist", T0, sitca=sitca_minus)
ni = rj(r, "data/dividend_info.json")["etfs"]
check("E-5 無官方來源（不在 SITCA、TWSE 查無）→ 不寫 dividend_info（不以無配息歷史推不配息）",
      not any(c in ni for c in NOSRC), [c for c in NOSRC if c in ni])

check("NET 全程零連線（socket／DNS／curl_cffi 原生）", not NET, NET[:5])
(OUT / "RESULTS.json").write_text(json.dumps({"results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
fails = [x for x in results if not x["ok"]]
print("\nTOTAL %d  PASS %d  FAIL %d  out=%s" % (len(results), len(results) - len(fails), len(fails), OUT))
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fails else 0)
