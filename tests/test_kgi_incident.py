"""00407A incident（2026-10-08）：凱基資料日語意、同資料日 anomaly、逐日回補（全離線，原始頁取自
docs/incidents/00407A/raw，為凱基官方 RedemptionVC 2026-10-08 實際回應）。

執行：python tests/test_kgi_incident.py
"""
import contextlib, datetime, io, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_active_etf as F          # noqa: E402
import mega_feed as M                 # noqa: E402
import recover_kgi_history as R       # noqa: E402
import daily_check as DC              # noqa: E402

F.time.sleep = lambda s: None          # fetch_kgi 每檔睡 1 秒（對投信禮貌），離線測試不需要
RAW = ROOT / "docs" / "incidents" / "00407A" / "raw"
D = datetime.date
TRADING = {D(2026, 9, d) for d in (22, 23, 24, 29, 30)} | {D(2026, 10, d) for d in (1, 2, 5, 6, 7, 8)}


@contextlib.contextmanager
def quiet():
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def kgi_from(name):
    page = (RAW / f"kgi_J024_{name}.html").read_text(encoding="utf-8")
    saved = F.urllib.request.urlopen
    F.urllib.request.urlopen = lambda *a, **k: io.BytesIO(page.encode("utf-8"))
    try:
        with quiet():
            return F.fetch_kgi(D(2026, 10, 8)).get("00407A")
    finally:
        F.urllib.request.urlopen = saved


def H(n, bump=0):
    return {str(1101 + i): {"name": f"股{i}", "shares": 1000 + i + (bump if i < 3 else 0)} for i in range(n)}


class KgiDataDate(unittest.TestCase):
    def test_latest_announce_future_but_data_is_1008(self):
        page = (RAW / "kgi_J024_latest.html").read_text(encoding="utf-8")
        self.assertIn('value="2026/10/12"', page)                 # DataDate＝公告日（未來）
        self.assertEqual(kgi_from("latest")["data_date"], "2026-10-08")

    def test_query_day_returns_previous_trading_day(self):
        expect = {"q20260929": "2026-09-24", "q20260930": "2026-09-29", "q20261001": "2026-09-30",
                  "q20261002": "2026-10-01", "q20261005": "2026-10-02", "q20261006": "2026-10-05",
                  "q20261007": "2026-10-06", "q20261008": "2026-10-07"}
        for name, want in expect.items():
            with self.subTest(name=name):
                got = kgi_from(name)
                self.assertEqual(got["data_date"], want)
                self.assertEqual(len(got["holdings"]), 50)

    def test_ambiguous_dates_fail_closed(self):
        page = (RAW / "kgi_J024_latest.html").read_text(encoding="utf-8").replace("(2026/10/08)", "(2026/10/07)", 1)
        saved = F.urllib.request.urlopen
        F.urllib.request.urlopen = lambda *a, **k: io.BytesIO(page.encode("utf-8"))
        try:
            with quiet():
                self.assertEqual(F.fetch_kgi(D(2026, 10, 8)), {})     # fail closed：整檔不交出
        finally:
            F.urllib.request.urlopen = saved


class BuildFlowGuard(unittest.TestCase):
    def setUp(self):
        self.saved = F.closes_on
        F.closes_on = lambda d, max_lookback=6: (d.strftime("%Y%m%d"), {str(1101 + i): 10.0 for i in range(60)})

    def tearDown(self):
        F.closes_on = self.saved

    def flow(self, d_old, h_old, d_new, h_new, code="00407A"):
        with quiet():
            return F.build_flow({"etfs": {code: {"data_date": d_old, "holdings": h_old}}},
                                {"etfs": {code: {"data_date": d_new, "holdings": h_new}}})[code]

    def test_same_date_same_holdings_idempotent(self):
        f = self.flow("2026-10-08", H(50), "2026-10-08", H(50))
        self.assertEqual((f["advanced"], f["reason"], f["flow"]), (False, "not_updated", []))
        self.assertIsNone(f.get("anomaly"))

    def test_same_date_different_holdings_anomaly_no_flow(self):
        f = self.flow("2026-10-07", H(50), "2026-10-07", H(50, bump=500))
        self.assertEqual((f["advanced"], f["changed"], f["flow"]), (False, 0, []))
        self.assertIn("同一資料日 2026-10-07 持股內容不同（3 檔）", f["anomaly"])

    def test_adjacent_days_normal_flow(self):
        f = self.flow("2026-10-06", H(50), "2026-10-07", H(50, bump=500))
        self.assertEqual((f["advanced"], f["changed"], f["basis_date"], f["data_date"]), (True, 3, "2026-10-06", "2026-10-07"))
        self.assertIsNone(f.get("anomaly"))

    def test_non_kgi_flow_unchanged(self):
        f = self.flow("2026-10-07", H(40), "2026-10-08", H(40, bump=-200), code="00981A")
        self.assertEqual((f["advanced"], f["changed"], f["sell"], f["buy"]), (True, 3, -6000.0, 0))
        self.assertEqual(sorted(r["delta_shares"] for r in f["flow"]), [-200, -200, -200])


class KgiFailClosedE2E(unittest.TestCase):
    """BLOCKER 1：凱基沒有唯一可信資料日 → production main() 不得動 00407A 的快照與 Flow、不得寫 null、不得 crash。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); t = Path(self.td.name)
        self.snap, self.out = t / "snap.json", t / "flow.json"
        self.snap_rec = {"name": "主動凱基台灣", "issuer": "凱基", "data_date": "2026-10-08", "holdings": H(50)}
        self.flow_rec = {"name": "主動凱基台灣", "issuer": "凱基", "holdings": 50, "data_date": "2026-10-08",
                         "advanced": True, "reason": "ok", "fetched": True, "first_seen": "2026-09-30", "anomaly": None,
                         "last_change_date": "2026-10-07", "flow_from": "2026-10-06", "flow_to": "2026-10-07",
                         "price_date": "20261007", "scale_pct": None, "buy": 0, "sell": -246400000.0, "changed": 3,
                         "flow": [{"code": "3529", "name": "力旺", "delta_shares": -30000, "amount": -1.0}], "no_price": []}
        json.dump({"fetched": "x", "etfs": {"00407A": self.snap_rec}}, open(self.snap, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"etfs": {"00407A": self.flow_rec}}, open(self.out, "w", encoding="utf-8"), ensure_ascii=False)
        self.saved = (F.SNAPSHOT, F.OUT, F.ADAPTERS, F.closes_on, F.urllib.request.urlopen)
        other = {"name": "其他", "issuer": "x", "data_date": "2026-10-08", "holdings": H(30)}
        # 第二個 adapter 讓 main() 不會因「全部沒抓到」提早 ABORT，確實走到寫檔與 KEEP 路徑
        F.SNAPSHOT, F.OUT, F.ADAPTERS = self.snap, self.out, [F.fetch_kgi, lambda d, specific=False: {} if specific else {"00981A": other}]
        F.closes_on = lambda d, max_lookback=6: (d.strftime("%Y%m%d"), {"9999": 1.0})

    def tearDown(self):
        F.SNAPSHOT, F.OUT, F.ADAPTERS, F.closes_on, F.urllib.request.urlopen = self.saved
        self.td.cleanup()

    def run_with(self, page):
        F.urllib.request.urlopen = lambda *a, **k: io.BytesIO(page.encode("utf-8"))
        with quiet():
            F.main()                                              # 不得 KeyError('reason') 或其他例外
        snap = json.load(open(self.snap, encoding="utf-8"))["etfs"]["00407A"]
        row = json.load(open(self.out, encoding="utf-8"))["etfs"]["00407A"]
        self.assertEqual(snap, self.snap_rec)                     # 快照逐欄保留
        for k in ("data_date", "advanced", "reason", "flow_from", "flow_to", "changed", "buy", "sell", "flow",
                  "last_change_date", "price_date", "holdings", "first_seen"):
            self.assertEqual(row.get(k), self.flow_rec[k], k)     # Flow 保留（只有 KEEP 標 fetched:false）
        self.assertFalse(row["fetched"])
        self.assertIsNotNone(row["data_date"])

    def test_paren_dates_missing(self):
        import re as _re
        page = _re.sub(r"\(\d{4}/\d{2}/\d{2}\)", "", (RAW / "kgi_J024_latest.html").read_text(encoding="utf-8"))
        self.assertNotRegex(page, r"\(\d{4}/\d{2}/\d{2}\)")
        self.run_with(page)

    def test_paren_dates_conflict(self):
        page = (RAW / "kgi_J024_latest.html").read_text(encoding="utf-8").replace("(2026/10/08)", "(2026/10/07)", 1)
        self.run_with(page)


class RecoveryReplay(unittest.TestCase):
    """離線重播（--raw 官方原始頁、不 apply）：逐日、只比相鄰交易日。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); t = Path(self.td.name)
        self.snap, self.out, self.evid = t / "snap.json", t / "flow.json", t / "evid"
        json.dump({"etfs": {"00407A": kgi_from("latest")}}, open(self.snap, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"etfs": {"00407A": OLD_ROW}}, open(self.out, "w", encoding="utf-8"), ensure_ascii=False)
        self.saved = (F.SNAPSHOT, F.OUT, F.closes_on, M._IS_TRADING)
        F.SNAPSHOT, F.OUT = self.snap, self.out
        F.closes_on = lambda d, max_lookback=6: (d.strftime("%Y%m%d"), {"2330": 1000.0, "2317": 200.0})
        M.set_calendar(lambda d: d in TRADING)

    def tearDown(self):
        F.SNAPSHOT, F.OUT, F.closes_on = self.saved[:3]
        M.set_calendar(self.saved[3]); self.td.cleanup()

    def run_r(self, raw):
        with quiet():
            return R.main(["--start", "2026-09-24", "--evidence", str(self.evid), "--raw", str(raw)])

    def test_replay_only_adjacent_days(self):
        before = self.snap.read_bytes(), self.out.read_bytes()
        self.run_r(RAW)
        self.assertEqual((self.snap.read_bytes(), self.out.read_bytes()), before)          # dry-run 不寫
        rep = json.load(open(self.evid / "report.json", encoding="utf-8"))
        changed = {s["data_date"]: s["flow_from"] + "→" + s["flow_to"] for s in rep["steps"] if s["flow_to"] == s["data_date"]}
        self.assertEqual(changed, {"2026-09-30": "2026-09-29→2026-09-30", "2026-10-01": "2026-09-30→2026-10-01",
                                   "2026-10-05": "2026-10-02→2026-10-05", "2026-10-07": "2026-10-06→2026-10-07"})
        self.assertEqual((rep["after"]["flow"]["flow_from"], rep["after"]["flow"]["flow_to"]), ("2026-10-06", "2026-10-07"))

    def test_missing_baseline_aborts(self):
        bad = Path(self.td.name) / "raw_bad"; bad.mkdir()
        for p in RAW.iterdir():
            (bad / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        (bad / "kgi_J024_q20261008.html").write_text((RAW / "kgi_J024_q20261007.html").read_text(encoding="utf-8"),
                                                       encoding="utf-8")       # 10/07 基準換成 10/06 的頁
        with self.assertRaises(SystemExit):
            self.run_r(bad)


OLD_ROW = {"name": "主動凱基台灣", "issuer": "凱基", "holdings": 50, "data_date": "2026-10-08", "fetched": True,
           "advanced": False, "reason": "not_updated", "flow_from": "2026-09-23", "flow_to": "2026-09-24", "changed": 49,
           "buy": 0, "sell": -1.0, "flow": [], "last_change_date": "2026-09-24", "first_seen": "2026-09-30",
           "price_date": "20260924", "scale_pct": None, "anomaly": None, "no_price": []}


def _g(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout


class RecoveryApplyGit(unittest.TestCase):
    """BLOCKER 2：apply 以遠端 main 為正式資料、基準 commit 為 parent 的非 force push（failure injection）。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); t = Path(self.td.name)
        self.origin, self.work, self.other = t / "origin.git", t / "work", t / "other"
        _g(t, "init", "-q", "--bare", "-b", "main", str(self.origin))
        _g(t, "clone", "-q", str(self.origin), str(self.work))
        for d in (self.work,):
            _g(d, "config", "user.name", "t"); _g(d, "config", "user.email", "t@t")
            _g(d, "checkout", "-q", "-b", "main")
        (self.work / "data").mkdir()
        self.final_snap = json.loads(json.dumps(kgi_from("latest"), ensure_ascii=False))
        self.write(self.work, snap=self.final_snap, row=OLD_ROW)
        _g(self.work, "add", "-A"); _g(self.work, "commit", "-q", "-m", "init"); _g(self.work, "push", "-q", "origin", "main")
        _g(t, "clone", "-q", str(self.origin), str(self.other))
        _g(self.other, "config", "user.name", "o"); _g(self.other, "config", "user.email", "o@o")
        self.saved = (F.closes_on, M._IS_TRADING, R._HOOK_BEFORE_WRITE, R._HOOK_BEFORE_PUSH, F.SNAPSHOT, F.OUT)
        F.closes_on = lambda d, max_lookback=6: (d.strftime("%Y%m%d"), {"2330": 1000.0, "2317": 200.0})
        M.set_calendar(lambda d: d in TRADING)

    def tearDown(self):
        F.closes_on, _, R._HOOK_BEFORE_WRITE, R._HOOK_BEFORE_PUSH, F.SNAPSHOT, F.OUT = self.saved
        M.set_calendar(self.saved[1])
        self.td.cleanup()

    @staticmethod
    def write(repo, snap=None, row=None, extra=None):
        if snap is not None:
            json.dump({"etfs": {"00407A": snap}}, open(repo / "data" / "_active_snapshot.json", "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
        if row is not None:
            doc = {"etfs": {"00407A": row}}
            if extra:
                doc["etfs"].update(extra)
            json.dump(doc, open(repo / "data" / "active_flow.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def origin_file(self, name):
        return json.loads(_g(self.work, "--git-dir", str(self.origin), "show", f"main:data/{name}"))

    def origin_head(self):
        return _g(self.work, "--git-dir", str(self.origin), "rev-parse", "main").strip()

    def apply(self):
        with quiet():
            return R.main(["--start", "2026-09-24", "--evidence", str(Path(self.td.name) / "evid"), "--raw", str(RAW),
                           "--apply", "--repo", str(self.work)])

    def other_pushes(self):
        _g(self.other, "pull", "-q", "origin", "main")
        doc = json.load(open(self.other / "data" / "active_flow.json", encoding="utf-8"))
        doc["etfs"]["00981A"] = {"data_date": "2026-10-09", "note": "其他 writer 的更新"}
        json.dump(doc, open(self.other / "data" / "active_flow.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        _g(self.other, "commit", "-qam", "other writer"); _g(self.other, "push", "-q", "origin", "main")

    def test_flow_only_success_snapshot_untouched(self):
        h0 = self.origin_head()
        self.apply()
        h1 = self.origin_head()
        self.assertNotEqual(h0, h1)
        self.assertEqual(_g(self.work, "--git-dir", str(self.origin), "rev-parse", "main^").strip(), h0)   # parent＝基準
        changed = _g(self.work, "--git-dir", str(self.origin), "diff", "--name-only", h0, h1).split()
        self.assertEqual(changed, ["data/active_flow.json"])                                            # 快照不寫
        row = self.origin_file("active_flow.json")["etfs"]["00407A"]
        self.assertEqual((row["flow_from"], row["flow_to"]), ("2026-10-06", "2026-10-07"))
        self.assertEqual(row["changed"] + len(row["no_price"]), 3)        # 測試價格表只有兩檔，其餘進 no_price

    def test_idempotent_second_apply_writes_nothing(self):
        self.apply(); h1 = self.origin_head()
        self.apply()
        self.assertEqual(self.origin_head(), h1)

    def test_snapshot_differs_refuses(self):
        snap = dict(self.final_snap, data_date="2026-10-07")
        self.write(self.work, snap=snap, row=OLD_ROW)
        _g(self.work, "commit", "-qam", "snap differs"); _g(self.work, "push", "-q", "origin", "main")
        h0 = self.origin_head()
        with self.assertRaises(SystemExit):
            self.apply()
        self.assertEqual(self.origin_head(), h0)

    def test_concurrent_writer_before_push_is_preserved(self):
        R._HOOK_BEFORE_PUSH = self.other_pushes
        with self.assertRaises(SystemExit):
            self.apply()
        doc = self.origin_file("active_flow.json")["etfs"]
        self.assertEqual(doc["00981A"]["note"], "其他 writer 的更新")         # 他人更新保留
        self.assertEqual(doc["00407A"], OLD_ROW)                                # 回補沒有覆蓋上去

    def test_concurrent_writer_between_check_and_write_is_preserved(self):
        R._HOOK_BEFORE_WRITE = self.other_pushes
        with self.assertRaises(SystemExit):
            self.apply()
        self.assertEqual(self.origin_file("active_flow.json")["etfs"]["00981A"]["note"], "其他 writer 的更新")

    def test_write_failure_leaves_no_partial_state(self):
        h0 = self.origin_head()
        real = os.replace

        def boom(src, dst):
            if str(dst).endswith("active_flow.json"):
                raise OSError("simulated disk failure")
            return real(src, dst)
        os.replace = boom
        try:
            with self.assertRaises(OSError):
                self.apply()
        finally:
            os.replace = real
        self.assertEqual(self.origin_head(), h0)                                 # 正式資料完全沒變
        self.assertEqual(self.origin_file("active_flow.json")["etfs"]["00407A"], OLD_ROW)
        self.assertEqual(_g(self.work, "worktree", "list").count("\n"), 1)       # 暫存 worktree 已清掉

    def test_push_failure_leaves_no_partial_state(self):
        h0 = self.origin_head()

        def break_remote():
            (self.origin / "hooks" / "pre-receive").write_text("#!/bin/sh\nexit 1\n")
            os.chmod(self.origin / "hooks" / "pre-receive", 0o755)
        R._HOOK_BEFORE_PUSH = break_remote
        with self.assertRaises(SystemExit):
            self.apply()
        self.assertEqual(self.origin_head(), h0)


class TelegramPath(unittest.TestCase):
    """build_flow 的 anomaly → main() 寫進 active_flow → daily_check 列入「主動式 ETF 持股資料異常」通知。"""

    def test_anomaly_reaches_daily_check(self):
        td = tempfile.TemporaryDirectory(); t = Path(td.name)
        snap, out, mkt = t / "snap.json", t / "flow.json", t / "market.json"
        json.dump({"etfs": {"00407A": {"name": "主動凱基台灣", "issuer": "凱基", "data_date": "2026-10-07", "holdings": H(50)}}},
                  open(snap, "w", encoding="utf-8"))
        json.dump({"etfs": {"00407A": {"name": "主動凱基台灣", "issuer": "凱基", "data_date": "2026-10-07", "fetched": True,
                                       "advanced": True, "changed": 1, "buy": 0, "sell": 0, "flow": [], "flow_from": "2026-10-06",
                                       "flow_to": "2026-10-07", "first_seen": "2026-09-30", "last_change_date": "2026-10-07"}}},
                  open(out, "w", encoding="utf-8"))
        json.dump({"twse_price_check_date": "20261007"}, open(mkt, "w"))
        saved = (F.SNAPSHOT, F.OUT, F.ADAPTERS, F.closes_on, DC.ACTIVE_FLOW, DC.MARKET, DC.ACTIVE_MIN_ETFS)
        try:
            F.SNAPSHOT, F.OUT = snap, out
            F.ADAPTERS = [lambda d, specific=False: {} if specific else
                          {"00407A": {"name": "主動凱基台灣", "issuer": "凱基", "data_date": "2026-10-07", "holdings": H(50, bump=9)}}]
            F.closes_on = lambda d, max_lookback=6: (d.strftime("%Y%m%d"), {"9999": 1.0})
            with quiet():
                F.main()
            row = json.load(open(out, encoding="utf-8"))["etfs"]["00407A"]
            self.assertIn("同一資料日", row["anomaly"])
            self.assertEqual((row["flow_from"], row["flow_to"]), ("2026-10-06", "2026-10-07"))   # 沒產生新 Flow
            DC.ACTIVE_FLOW, DC.MARKET, DC.ACTIVE_MIN_ETFS = out, mkt, 1
            issues = DC.check_active_flow()
            self.assertTrue(any(i.startswith("• 🐛 00407A") and "同一資料日" in i for i in issues), issues)
            src = (ROOT / "scripts" / "daily_check.py").read_text(encoding="utf-8")
            self.assertIn('lines.append("📉 主動式 ETF 持股資料異常")\n        lines.extend(active_issues)', src)
        finally:
            F.SNAPSHOT, F.OUT, F.ADAPTERS, F.closes_on, DC.ACTIVE_FLOW, DC.MARKET, DC.ACTIVE_MIN_ETFS = saved
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
