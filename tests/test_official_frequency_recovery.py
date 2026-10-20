"""Offline policy recovery and actual daily-check/publication notification tests."""
import contextlib
import ast
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import official_frequency as policy

FIX = ROOT / "tests" / "fixtures" / "official_frequency"
RAW = (FIX / "policy_00412A.html").read_bytes()
SEARCH = (FIX / "search_00412A.html").read_bytes()


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.guard = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def test_real_official_policy(self):
        self.assertEqual(policy.parse_policy(RAW, "00412A"), "不配息")

    def test_identity_and_policy_boundaries(self):
        for body, code in [(RAW, "00412AX"), (RAW, "0050"),
                           ((FIX / "no_history_00412A.html").read_bytes(), "00412A"),
                           (RAW.replace("收益不分配".encode(), "本期不分配".encode()), "00412A")]:
            with self.subTest(code=code, body_size=len(body)), self.assertRaises(ValueError):
                policy.parse_policy(body, code)

    def test_generic_fund_and_all_supported_policies(self):
        for value, expected in [("季配", "季配"), ("每月", "月配"), ("每半年", "半年配"),
                                ("年配息", "年配"), ("雙月配息", "雙月配")]:
            body = RAW.replace(b"00412A", b"0050").replace("收益不分配".encode(), value.encode())
            with self.subTest(policy=value):
                self.assertEqual(policy.parse_policy(body, "0050"), expected)

    def test_search_and_identified_notice_are_both_required(self):
        calls = []
        def get(url):
            calls.append(url)
            return SEARCH if "newsList?" in url else RAW
        result = policy.resolve_frequency("00412A", get)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["frequency"], "不配息")
        self.assertEqual(len(result["sources"][0]["sha256"]), 64)

    def test_wrong_code_and_errors_do_not_become_verified(self):
        for get in [lambda u: b"not found", lambda u: SEARCH.replace(b"00412A", b"00412AX"),
                    lambda u: (_ for _ in ()).throw(TimeoutError())]:
            self.assertEqual(policy.resolve_frequency("00412A", get)["status"], "unresolved")
        self.assertEqual(policy.resolve_frequency("../00412A", lambda u: self.fail("must not request"))["status"], "unresolved")

    def test_conflicting_policy_is_not_silently_chosen(self):
        other = "/zh/ETFortune/newsDetail/" + "a" * 32
        search = SEARCH + ('<tr onclick="document.location=\'' + other + '\'"><td>00412A</td></tr>').encode()
        def get(url):
            if "newsList?" in url:
                return search
            return RAW.replace("收益不分配".encode(), "季配".encode()) if url.endswith("a" * 32) else RAW
        self.assertEqual(policy.resolve_frequency("00412A", get)["status"], "unresolved")

    def test_recovery_is_bounded_and_preserves_other_fields(self):
        rows = [{"code": "00412A", "price": 9.03, "div_frequency": "不明"},
                {"code": "0050", "price": 20, "div_frequency": "不明"},
                {"code": "0056", "price": 30, "div_frequency": "季配"}]
        old = copy.deepcopy(rows)
        info = {}
        result = policy.recover_missing(rows, info, lambda c: policy.resolve_frequency(c, lambda u: SEARCH if "newsList?" in u else RAW), limit=1)
        self.assertEqual(result["recovered"], ["00412A"])
        self.assertEqual(result["attempts"][1]["status"], "deferred")
        self.assertEqual(rows[1:], old[1:])
        self.assertEqual(rows[0]["price"], old[0]["price"])
        self.assertIsNone(info["00412A"]["avg_dividend_per_share"])
        self.assertTrue(info["00412A"]["_todo"])

    def test_known_policy_is_propagated_without_network(self):
        rows = [{"code": "00412A", "div_frequency": "不明"}]
        policy.recover_missing(rows, {"00412A": {"frequency": "不配息"}}, lambda c: self.fail("no lookup"))
        self.assertEqual(rows[0]["div_frequency"], "不配息")

    def test_fetch_entrypoint_uses_new_resolver_without_running_full_fetch(self):
        source = ast.parse((ROOT / "fetch_etf.py").read_text(encoding="utf-8"))
        function = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "fetch_div_freq_twse")
        namespace = {"_OFFICIAL_FREQ_RECOVERIES": {}}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "fetch-frequency-only", "exec"), namespace)
        # The real function imports the namespace package, just as fetch_etf.py does.
        sys.path.insert(0, str(ROOT))
        import scripts.official_frequency as fetch_policy
        expected = policy.resolve_frequency("00412A", lambda u: SEARCH if "newsList?" in u else RAW)
        with patch.object(fetch_policy, "resolve_frequency", return_value=expected):
            self.assertEqual(namespace["fetch_div_freq_twse"]("00412A"), "不配息")
        self.assertEqual(namespace["_OFFICIAL_FREQ_RECOVERIES"]["00412A"], expected)

    def test_weekly_no_data_is_not_reported_as_all_consistent(self):
        spec = importlib.util.spec_from_file_location("weekly_policy_test", ROOT / "scripts/validate_div_freq.py")
        weekly = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(weekly)
        output = io.StringIO()
        with patch.object(weekly, "fetch_freq_twse", return_value=None), \
                patch.object(weekly.time, "sleep"), contextlib.redirect_stdout(output):
            weekly.main()
        self.assertNotIn("全部 ETF 配息頻率與 TWSE 一致", output.getvalue())
        self.assertIn("查無資料", output.getvalue())

    def test_actual_daily_main_repairs_before_alerting(self):
        with tempfile.TemporaryDirectory(prefix="etf_recovery_test_") as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "data", root / "data")
            shutil.copyfile(ROOT / "fetch_etf.py", root / "fetch_etf.py")
            spec = importlib.util.spec_from_file_location("daily_recovery_test", ROOT / "scripts/daily_check.py")
            daily = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(daily)
            for name in ("MARKET", "DIV_INFO", "DIV_CAL", "KNOWN_CODES", "DAILY_STATE", "ACTIVE_FLOW", "FETCH_ETF"):
                old = getattr(daily, name)
                setattr(daily, name, root / old.relative_to(ROOT))
            daily.ROOT = root
            market = json.loads(daily.MARKET.read_bytes())
            target = next(e for e in market["etfs"] if e["code"] == "00412A")
            target["div_frequency"] = "不明"
            daily.MARKET.write_text(json.dumps(market), encoding="utf-8")
            static = json.loads(daily.DIV_INFO.read_bytes())
            static["etfs"].pop("00412A", None)
            daily.DIV_INFO.write_text(json.dumps(static), encoding="utf-8")
            base = json.loads((root / "data/_base.json").read_bytes())
            next(e for e in base["etfs"] if e["code"] == "00412A")["div_freq"] = "不明"
            (root / "data/_base.json").write_text(json.dumps(base), encoding="utf-8")
            original_market = daily.MARKET.read_bytes()
            daily.KNOWN_CODES.write_text("[]", encoding="utf-8")
            saved = {p: p.read_bytes() for p in (root / "data").iterdir() if p.is_file()}
            before = types.ModuleType("daily_before_recovery")
            before.__file__ = str(ROOT / "scripts/daily_check.py")
            baseline = subprocess.check_output(["git", "-c", "safe.directory=" + str(ROOT),
                                                "-C", str(ROOT), "show",
                                                "5628fb794de891dc4e79323fc64add77390a20a7:scripts/daily_check.py"])
            exec(compile(baseline, before.__file__, "exec"), before.__dict__)
            for name in ("MARKET", "DIV_INFO", "DIV_CAL", "KNOWN_CODES", "DAILY_STATE", "ACTIVE_FLOW", "FETCH_ETF"):
                setattr(before, name, getattr(daily, name))
            before.ROOT = root
            old_messages = []
            before.notify = old_messages.append
            with contextlib.redirect_stdout(io.StringIO()):
                before.main()
            self.assertTrue(any("00412A" in line and "配息方式不明" in line
                                for msg in old_messages for line in msg.splitlines()))
            for path, body in saved.items():
                path.write_bytes(body)
            messages = []
            daily.notify = messages.append
            original_resolve = policy.resolve_frequency
            def resolver(code):
                return original_resolve(code, lambda u: SEARCH if "newsList?" in u else RAW) if code == "00412A" else {"status": "unresolved", "reason": "fixture unavailable"}
            with patch.object(policy, "resolve_frequency", resolver), contextlib.redirect_stdout(io.StringIO()):
                daily.main()
            self.assertEqual(json.loads(daily.DIV_INFO.read_bytes())["etfs"]["00412A"]["frequency"], "不配息")
            for message in messages:
                for line in message.splitlines():
                    if "00412A" in line:
                        self.assertNotIn("配息方式不明", line)
                        self.assertNotIn("殖利率查無", line)
            self.assertEqual(daily.MARKET.read_bytes(), original_market)
            after = json.loads((root / "data/_base.json").read_bytes())
            expected = copy.deepcopy(base)
            for e in after["etfs"]:
                before = next(x for x in base["etfs"] if x["code"] == e["code"])
                self.assertEqual(e["price"], before["price"])
            self.assertEqual(len(after["etfs"]), len(expected["etfs"]))

    def test_workflow_defers_notifications_until_after_push(self):
        text = (ROOT / ".github/workflows/fetch.yml").read_text(encoding="utf-8")
        self.assertLess(text.index("--defer-notifications"), text.index("git push"))
        self.assertLess(text.index("git push"), text.index("--send-prepared"))
        self.assertIn("steps.publish.outcome == 'success'", text)

    def test_real_cli_requires_committed_remote_data_before_notifications(self):
        with tempfile.TemporaryDirectory(prefix="etf_notify_test_") as tmp:
            root = Path(tmp) / "repo"
            bare = Path(tmp) / "remote.git"
            root.mkdir()
            (root / "data").mkdir()
            (root / "data/dividend_info.json").write_text('{"etfs":{}}', encoding="utf-8")
            def git(*args):
                return subprocess.check_output(["git", "-c", "safe.directory=" + str(root),
                                                "-c", "user.name=Offline test", "-c", "user.email=test@localhost",
                                                "-C", str(root), *args], stderr=subprocess.DEVNULL)
            git("init", "-b", "main")
            subprocess.check_call(["git", "init", "--bare", str(bare)], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            git("add", "data")
            git("commit", "-m", "fixture")
            git("remote", "add", "origin", str(bare))
            git("push", "origin", "main")
            spec = importlib.util.spec_from_file_location("daily_notify_test", ROOT / "scripts/daily_check.py")
            daily = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(daily)
            daily.ROOT = root
            messages = []
            daily.notify = messages.append
            daily.main = lambda: daily.notify("remaining genuine issue")
            report = Path(tmp) / "prepared.json"
            with patch.object(sys, "argv", ["daily", "--defer-notifications", str(report)]):
                self.assertEqual(daily.cli(), 0)
            self.assertEqual(messages, [])
            self.assertEqual(json.loads(report.read_text())["messages"], ["remaining genuine issue"])
            with patch.object(sys, "argv", ["daily", "--send-prepared", str(report)]), \
                    patch.dict(os.environ, {"ETF_PUBLISH_OK": "false"}):
                self.assertEqual(daily.cli(), 1)
            self.assertNotIn("remaining genuine issue", messages)
            messages.clear()
            with patch.object(sys, "argv", ["daily", "--send-prepared", str(report)]), \
                    patch.dict(os.environ, {"ETF_PUBLISH_OK": "true"}):
                self.assertEqual(daily.cli(), 0)
            self.assertEqual(messages, ["remaining genuine issue"])
            messages.clear()
            data = json.loads(report.read_text())
            data["data_sha256"]["dividend_info.json"] = "0" * 64
            report.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(sys, "argv", ["daily", "--send-prepared", str(report)]), \
                    patch.dict(os.environ, {"ETF_PUBLISH_OK": "true"}):
                self.assertEqual(daily.cli(), 1)
            self.assertNotIn("remaining genuine issue", messages)
            messages.clear()
            (root / "data/new.json").write_text("{}", encoding="utf-8")
            git("add", "data")
            git("commit", "-m", "not published")
            with patch.object(sys, "argv", ["daily", "--send-prepared", str(report)]), \
                    patch.dict(os.environ, {"ETF_PUBLISH_OK": "true"}):
                self.assertEqual(daily.cli(), 1)
            self.assertNotIn("remaining genuine issue", messages)


if __name__ == "__main__":
    unittest.main(verbosity=2)
