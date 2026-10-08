"""00996A incident Phase 2C：handoff contract、雲端驗證、下一交易日、feed 失敗矩陣（全離線）。

執行：python tests/test_mega_feed.py
"""
import contextlib, copy, datetime, io, json, os, sys, tempfile, unittest, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mega_feed as M            # noqa: E402
import fetch_active_etf as F     # noqa: E402

D = datetime.date
CODE = "00996A"
PCF_HTML = (ROOT / "tests" / "fixtures" / "mega_pcf_00996A_20261007.html").read_text(encoding="utf-8")
FORM_HTML = '<form><input type="hidden" name="__VIEWSTATE" value="x"/></form>'

# 2026-09/10 實際交易日（TWSE FMTQIK）：9/25 中秋、9/28 教師節休市
TRADING = {D(2026, 9, d) for d in (21, 22, 23, 24, 29, 30)} | \
          {D(2026, 10, d) for d in (1, 2, 5, 6, 7, 8, 9, 12, 13)}


M.set_calendar(lambda d: d in TRADING)     # 測試一律用固定交易日曆（離線）


def holdings(n=52, start=1101):
    return {str(start + i): {"name": f"股{i}", "shares": 1000 + i} for i in range(n)}


def rec(date="2026-10-08", n=52, **over):
    r = M.build_record(CODE, "主動兆豐台灣豐收", "兆豐", date, holdings(n), "mega_trade_pcf", F.MEGA_URL,
                       fetched_at="2026-10-08T20:00:00+08:00")
    r.update(over)
    return r


def resign(r):
    r["row_count"] = len(r["holdings"]); r["sha256"] = M.holdings_sha256(r["holdings"]); return r


class NextTradingDay(unittest.TestCase):
    def nt(self, d):
        return M.next_trading_day(d, is_trading=lambda x: x in TRADING)

    def test_consecutive(self):
        self.assertEqual(self.nt(D(2026, 10, 6)), D(2026, 10, 7))

    def test_friday_to_monday(self):
        self.assertEqual(self.nt(D(2026, 10, 9)), D(2026, 10, 12))

    def test_0924_to_0929_holidays(self):
        self.assertEqual(self.nt(D(2026, 9, 24)), D(2026, 9, 29))

    def test_1002_to_1005(self):
        self.assertEqual(self.nt(D(2026, 10, 2)), D(2026, 10, 5))

    def test_fetch_mega_sends_next_trading_day(self):
        sent = []
        with fake_net(pcf=True, capture=sent), quiet():
            F.fetch_mega(D(2026, 9, 24), specific=True)
        self.assertTrue(any(s.endswith("qdt=2026/09/29") for s in sent), sent)


class Validate(unittest.TestCase):
    def bad(self, r, want, cur=None):
        ok, why = M.validate_record(r, CODE, cur)
        self.assertFalse(ok); self.assertTrue(why.startswith(want), why)

    def test_ok(self):
        self.assertEqual(M.validate_record(rec(), CODE, "2026-10-07"), (True, "ok"))

    def test_schema(self):          self.bad(rec(schema_version=2), "schema_version")
    def test_wrong_etf(self):       self.bad(rec(etf_code="00981A"), "wrong_etf")
    def test_bad_date(self):        self.bad(rec(official_data_date="2026/10/08"), "bad_date")
    def test_weekend(self):         self.bad(rec(date="2026-10-10"), "weekend_date")
    def test_rollback(self):        self.bad(rec(date="2026-10-01"), "not_newer", "2026-10-07")
    def test_same_date(self):       self.bad(rec(date="2026-10-07"), "not_newer", "2026-10-07")
    def test_bad_source(self):      self.bad(rec(source={"id": "x", "url": "https://evil/"}), "bad_source")
    def test_empty(self):           self.bad(resign(rec(holdings=[])), "empty_holdings")
    def test_too_few_rows(self):    self.bad(rec(n=5), "row_count")
    def test_sha_mismatch(self):
        r = rec(); r["holdings"][0]["shares"] += 1; self.bad(r, "sha256_mismatch")

    def test_zero_shares(self):
        r = rec(); r["holdings"][3]["shares"] = 0; self.bad(resign(r), "bad_shares")

    def test_negative_or_string_shares(self):
        r = rec(); r["holdings"][3]["shares"] = -5; self.bad(resign(r), "bad_shares")
        r = rec(); r["holdings"][3]["shares"] = "1,000"; self.bad(resign(r), "bad_shares")

    def test_duplicate(self):
        r = rec(); r["holdings"][4]["code"] = r["holdings"][3]["code"]; self.bad(resign(r), "duplicate")

    def test_invalid_code(self):
        r = rec(); r["holdings"][2]["code"] = "現金"; self.bad(resign(r), "bad_code")

    def test_sha_alone_not_enough(self):
        # sha256 正確但內容違規（股數 0）仍必須拒絕：sha 只是傳輸完整性
        r = rec(); r["holdings"][0]["shares"] = 0; resign(r)
        self.assertEqual(r["sha256"], M.holdings_sha256(r["holdings"]))
        self.bad(r, "bad_shares")


class FeedDir(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); self.dir = self.td.name

    def tearDown(self):
        self.td.cleanup()

    def put(self, r, name=None):
        M.write_atomic(os.path.join(self.dir, name or f"mega_{CODE}_{r['official_data_date']}.json"), r)

    def latest(self, cur="2026-10-07", **kw):
        with quiet():
            return M.latest_valid(self.dir, CODE, cur, **kw)[0]

    def pair(self, cur):
        with quiet():
            return M.latest_valid(self.dir, CODE, cur)

    def test_missing_dir(self):
        with quiet():
            self.assertEqual(M.latest_valid(os.path.join(self.dir, "nope"), CODE, "2026-10-07"), (None, None))

    def test_empty_dir(self):
        self.assertIsNone(self.latest())

    def test_normal(self):
        self.put(rec("2026-10-08")); self.assertEqual(self.latest()["official_data_date"], "2026-10-08")

    def test_stale(self):
        self.put(rec("2026-10-06")); self.assertIsNone(self.latest())

    def test_malformed_newer_falls_back_to_valid(self):
        self.put(rec("2026-10-08"))
        with open(os.path.join(self.dir, f"mega_{CODE}_2026-10-09.json"), "w") as f:
            f.write('{"schema_version": 1, "etf_code": "00996A", "holdings": [')   # 截斷
        self.assertEqual(self.latest()["official_data_date"], "2026-10-08")

    def test_partial_transfer_tmp_ignored(self):
        with open(os.path.join(self.dir, f"mega_{CODE}_2026-10-09.json.tmp"), "w") as f:
            f.write(json.dumps(rec("2026-10-09"))[:200])
        self.assertIsNone(self.latest())

    def test_filename_date_mismatch(self):
        self.put(rec("2026-10-08"), name=f"mega_{CODE}_2026-10-09.json")
        self.assertIsNone(self.latest())

    def test_wrong_etf_file(self):
        self.put(rec("2026-10-08", etf_code="00981A"), name=f"mega_{CODE}_2026-10-08.json")
        self.assertIsNone(self.latest())

    def test_weekday_holiday_rejected(self):
        self.put(rec("2026-09-25"))                       # 中秋，週五但休市
        self.assertIsNone(self.latest(cur="2026-09-24"))

    def test_calendar_unknown_fail_closed(self):
        self.put(rec("2026-10-08"))
        self.assertIsNone(self.latest(is_trading=lambda d: None))

    def test_basis_snapshot_is_prev_trading_day(self):
        self.put(rec("2026-10-08"))
        r, b = self.pair("2026-10-07")
        self.assertEqual((r["official_data_date"], b), ("2026-10-08", None))

    def test_basis_from_feed_when_gap(self):
        self.put(rec("2026-10-07", n=53)); self.put(rec("2026-10-08"))
        r, b = self.pair("2026-09-24")
        self.assertEqual((r["official_data_date"], b["official_data_date"]), ("2026-10-08", "2026-10-07"))

    def test_basis_across_holidays(self):
        self.put(rec("2026-09-24")); self.put(rec("2026-09-29"))
        r, b = self.pair("2026-09-23")
        self.assertEqual(b["official_data_date"], "2026-09-24")

    def test_no_basis_marked_false(self):
        self.put(rec("2026-10-08"))
        r, b = self.pair("2026-09-24")
        self.assertIs(b, False)

    def test_atomic_write_no_tmp_left(self):
        self.put(rec("2026-10-08"))
        self.assertEqual(os.listdir(self.dir), [f"mega_{CODE}_2026-10-08.json"])


# ── fetch_mega 整合（網路全部 mock）──
@contextlib.contextmanager
def quiet():
    with contextlib.redirect_stdout(io.StringIO()):
        yield


@contextlib.contextmanager
def fake_net(pcf=True, product=False, capture=None):
    class Resp:
        def __init__(self, t): self.t = t
        def read(self): return self.t.encode("utf-8")

    def opener():
        class Op:
            addheaders = []
            def open(self, req, timeout=None):
                url = req if isinstance(req, str) else req.full_url
                if capture is not None and not isinstance(req, str) and req.data:
                    capture.append(urllib.parse.unquote_plus(req.data.decode()))
                if "trade_pcf" in url:
                    if not pcf:
                        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"Access Denied"))
                    return Resp(PCF_HTML if not isinstance(req, str) else FORM_HTML)
                if "etf_product" in url:
                    raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"Access Denied"))
                raise AssertionError(url)
        return Op()
    import urllib.parse   # noqa: F401
    saved = (F._opener, F.time.sleep)
    F._opener, F.time.sleep = opener, (lambda s: None)
    try:
        yield
    finally:
        F._opener, F.time.sleep = saved


class FetchMegaFeed(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.feed = os.path.join(self.td.name, "feed"); os.makedirs(self.feed)
        self.snap = os.path.join(self.td.name, "snap.json")
        json.dump({"etfs": {CODE: {"data_date": "2026-09-24", "holdings": {}}}}, open(self.snap, "w"))
        self.saved = (F.SNAPSHOT, os.environ.get("MEGA_FEED_DIR"))
        F.SNAPSHOT = self.snap; os.environ["MEGA_FEED_DIR"] = self.feed
        F.MEGA_FEED_BASIS.clear()

    def tearDown(self):
        F.SNAPSHOT = self.saved[0]
        if self.saved[1] is None: os.environ.pop("MEGA_FEED_DIR", None)
        else: os.environ["MEGA_FEED_DIR"] = self.saved[1]
        self.td.cleanup()

    def run_mega(self, specific=False, **net):
        with fake_net(**net), quiet():
            return F.fetch_mega(D(2026, 10, 8), specific=specific)

    def put(self, r):
        M.write_atomic(os.path.join(self.feed, f"mega_{CODE}_{r['official_data_date']}.json"), r)

    def test_pcf_primary_wins_over_newer_feed(self):
        self.put(rec("2026-10-09"))
        out = self.run_mega(pcf=True)
        self.assertEqual(out[CODE]["data_date"], "2026-10-07")     # fixture 的官方資料日
        self.assertEqual(len(out[CODE]["holdings"]), 53)

    def test_pcf_403_uses_valid_feed(self):
        self.put(rec("2026-10-08"))
        out = self.run_mega(pcf=False)
        self.assertEqual(out[CODE]["data_date"], "2026-10-08")
        self.assertEqual(len(out[CODE]["holdings"]), 52)

    def test_pcf_403_no_feed_returns_empty_for_keep(self):
        self.assertEqual(self.run_mega(pcf=False), {})

    def test_pcf_403_stale_feed_returns_empty(self):
        self.put(rec("2026-09-24"))
        self.assertEqual(self.run_mega(pcf=False), {})

    def test_pcf_403_malformed_feed_returns_empty(self):
        r = rec("2026-10-08"); r["holdings"][0]["shares"] = 0
        self.put(r)
        self.assertEqual(self.run_mega(pcf=False), {})

    def test_specific_never_reads_feed(self):
        self.put(rec("2026-10-08"))
        self.assertEqual(self.run_mega(specific=True, pcf=False), {})

    def test_feed_code_scoped_to_mega_adapter(self):
        src = (ROOT / "scripts" / "fetch_active_etf.py").read_text(encoding="utf-8")
        uses = [i for i, l in enumerate(src.splitlines())
                if "mega_feed." in l and "next_trading_day" not in l and "set_calendar" not in l and not l.lstrip().startswith("#")]
        start = src.splitlines().index(next(l for l in src.splitlines() if l.startswith("def fetch_mega(")))
        end = src.splitlines().index(next(l for l in src.splitlines() if l.startswith("def _mega_parse_pcf(")))
        self.assertTrue(uses and all(start < i < end for i in uses), uses)


class MainRecovery(unittest.TestCase):
    """main() 端到端（網路全 mock）：快照停在 9/24、feed 有 10/07＋10/08 → Flow 只能是 10/07→10/08。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); t = self.td.name
        self.feed = os.path.join(t, "feed"); os.makedirs(self.feed)
        self.snap, self.out = os.path.join(t, "snap.json"), os.path.join(t, "flow.json")
        json.dump({"fetched": "x", "etfs": {
            CODE: {"name": "主動兆豐台灣豐收", "issuer": "兆豐", "data_date": "2026-09-24", "holdings": holdings(52)},
            "00981A": {"name": "統一", "issuer": "統一", "data_date": "2026-10-07", "holdings": holdings(30, 2001)}}},
            open(self.snap, "w", encoding="utf-8"))
        json.dump({"etfs": {
            CODE: {"name": "主動兆豐台灣豐收", "data_date": "2026-09-24", "fetched": False, "flow_from": "2026-09-23",
                   "flow_to": "2026-09-24", "flow": [], "first_seen": "2026-09-23",
                   "advanced": True, "changed": 4, "buy": 0, "sell": 0},
            "00981A": {"name": "統一", "data_date": "2026-10-07", "fetched": True, "flow": [],
                       "advanced": False, "changed": 0, "buy": 0, "sell": 0, "reason": "not_updated"}}},
            open(self.out, "w", encoding="utf-8"))
        r8 = rec("2026-10-08")
        for i in range(10):                                   # 10/08 相對 10/07 改 10 檔
            r8["holdings"][i]["shares"] += 1000
        resign(r8)
        for r in (rec("2026-09-29"), rec("2026-10-07"), r8):
            M.write_atomic(os.path.join(self.feed, f"mega_{CODE}_{r['official_data_date']}.json"), r)
        self.saved = (F.SNAPSHOT, F.OUT, F.ADAPTERS, F.closes_on, os.environ.get("MEGA_FEED_DIR"))
        F.SNAPSHOT, F.OUT = Path(self.snap), Path(self.out)
        F.closes_on = lambda d, max_lookback=6: ("20261008", {c: 10.0 for c in holdings(52)})
        os.environ["MEGA_FEED_DIR"] = self.feed
        F.MEGA_FEED_BASIS.clear()

    def tearDown(self):
        F.SNAPSHOT, F.OUT, F.ADAPTERS, F.closes_on, d = self.saved
        if d is None:
            os.environ.pop("MEGA_FEED_DIR", None)
        else:
            os.environ["MEGA_FEED_DIR"] = d
        F.MEGA_FEED_BASIS.clear(); self.td.cleanup()

    def run_main(self):
        F.ADAPTERS = [F.fetch_mega]
        with fake_net(pcf=False), quiet():
            return F.main()

    def load(self, p):
        return json.load(open(p, encoding="utf-8"))["etfs"]      # reload from disk

    def test_recovery_flow_is_single_day(self):
        self.assertEqual(self.run_main(), 0)
        flow, snap = self.load(self.out)[CODE], self.load(self.snap)[CODE]
        self.assertEqual((snap["data_date"], len(snap["holdings"])), ("2026-10-08", 52))
        self.assertEqual((flow["flow_from"], flow["flow_to"], flow["changed"]), ("2026-10-07", "2026-10-08", 10))
        self.assertTrue(flow["fetched"])

    def test_other_etf_untouched(self):
        self.run_main()
        o = self.load(self.out)["00981A"]
        self.assertEqual((o["data_date"], o["fetched"]), ("2026-10-07", False))   # 沒跑它的 adapter → 既有 KEEP
        self.assertEqual(self.load(self.snap)["00981A"]["data_date"], "2026-10-07")

    def test_no_basis_never_spans_days(self):
        os.remove(os.path.join(self.feed, f"mega_{CODE}_2026-10-07.json"))
        self.run_main()
        flow = self.load(self.out)[CODE]
        self.assertEqual(flow["data_date"], "2026-10-08")
        self.assertFalse(flow["advanced"])
        self.assertNotEqual(flow.get("flow_to"), "2026-10-08")

    def test_feed_broken_keeps_old(self):
        for n in os.listdir(self.feed):
            open(os.path.join(self.feed, n), "w").write("{broken")
        self.run_main()
        flow = self.load(self.out)[CODE]
        self.assertEqual((flow["data_date"], flow["fetched"]), ("2026-09-24", False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
