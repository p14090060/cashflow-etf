"""00407A incident（2026-10-08）：凱基資料日語意、同資料日 anomaly、逐日回補（全離線，原始頁取自
docs/incidents/00407A/raw，為凱基官方 RedemptionVC 2026-10-08 實際回應）。

執行：python tests/test_kgi_incident.py
"""
import contextlib, datetime, io, json, os, sys, tempfile, unittest
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

    def test_ambiguous_dates_give_none(self):
        page = (RAW / "kgi_J024_latest.html").read_text(encoding="utf-8").replace("(2026/10/08)", "(2026/10/07)", 1)
        saved = F.urllib.request.urlopen
        F.urllib.request.urlopen = lambda *a, **k: io.BytesIO(page.encode("utf-8"))
        try:
            with quiet():
                self.assertIsNone(F.fetch_kgi(D(2026, 10, 8))["00407A"]["data_date"])
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


class Recovery(unittest.TestCase):
    """離線重播（--raw 官方原始頁）：逐日、只比相鄰交易日。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); t = Path(self.td.name)
        self.snap, self.out, self.evid = t / "snap.json", t / "flow.json", t / "evid"
        start = kgi_from("q20260929")
        json.dump({"etfs": {"00407A": dict(start, data_date="2026-10-08"),         # 舊版標錯日期的快照
                            "00981A": {"data_date": "2026-10-07", "holdings": H(5)}}}, open(self.snap, "w", encoding="utf-8"))
        json.dump({"etfs": {"00407A": {"name": "主動凱基台灣", "issuer": "凱基", "data_date": "2026-10-08", "fetched": True,
                                       "advanced": False, "reason": "not_updated", "flow_from": "2026-09-23",
                                       "flow_to": "2026-09-24", "changed": 49, "buy": 0, "sell": -1.0, "flow": [],
                                       "last_change_date": "2026-09-24", "first_seen": "2026-09-30"},
                            "00981A": {"data_date": "2026-10-07", "fetched": True, "flow": [], "advanced": False, "changed": 0}}},
                  open(self.out, "w", encoding="utf-8"))
        self.saved = (F.SNAPSHOT, F.OUT, F.closes_on, M._IS_TRADING)
        F.SNAPSHOT, F.OUT = self.snap, self.out
        F.closes_on = lambda d, max_lookback=6: (d.strftime("%Y%m%d"), {"2330": 1000.0, "2317": 200.0})
        M.set_calendar(lambda d: d in TRADING)

    def tearDown(self):
        F.SNAPSHOT, F.OUT, F.closes_on = self.saved[:3]
        M.set_calendar(self.saved[3])
        self.td.cleanup()

    def run_r(self, raw, apply=False):
        with quiet():
            return R.main(["--start", "2026-09-24", "--evidence", str(self.evid), "--raw", str(raw)] + (["--apply"] if apply else []))

    def test_replay_only_adjacent_days_and_apply(self):
        self.run_r(RAW, apply=True)
        rep = json.load(open(self.evid / "report.json", encoding="utf-8"))
        self.assertEqual(rep["official_days"], ["2026-09-24", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02",
                                                "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08"])
        changed = {s["data_date"]: s["flow_from"] + "→" + s["flow_to"] for s in rep["steps"] if s["flow_to"] == s["data_date"]}
        self.assertEqual(changed, {"2026-09-30": "2026-09-29→2026-09-30", "2026-10-01": "2026-09-30→2026-10-01",
                                   "2026-10-05": "2026-10-02→2026-10-05", "2026-10-07": "2026-10-06→2026-10-07"})
        snap = json.load(open(self.snap, encoding="utf-8"))["etfs"]
        row = json.load(open(self.out, encoding="utf-8"))["etfs"]["00407A"]
        self.assertEqual(snap["00407A"]["data_date"], "2026-10-08")
        self.assertEqual((row["flow_from"], row["flow_to"], row["last_change_date"]), ("2026-10-06", "2026-10-07", "2026-10-07"))
        self.assertNotEqual(row["flow_from"], "2026-09-24")
        self.assertEqual(snap["00981A"]["data_date"], "2026-10-07")                # 其他 ETF 不動

    def test_missing_baseline_aborts_without_writing(self):
        bad = Path(self.td.name) / "raw_bad"; bad.mkdir()
        for p in RAW.iterdir():
            (bad / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        (bad / "kgi_J024_q20261008.html").write_text((RAW / "kgi_J024_q20261007.html").read_text(encoding="utf-8"),
                                                       encoding="utf-8")       # 10/07 基準換成 10/06 的頁
        before = self.snap.read_bytes(), self.out.read_bytes()
        with self.assertRaises(SystemExit):
            self.run_r(bad, apply=True)
        self.assertEqual((self.snap.read_bytes(), self.out.read_bytes()), before)


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
