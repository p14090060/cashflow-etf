"""Use recorded official quotes to prove recovery without another live round."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CURRENT = load(ROOT / "scripts/mis_fetcher.py", "mis_recovery_current")
ITEMS = json.loads((ROOT / "tests/fixtures/mis_one_sided_quotes_20261020.json").read_bytes())["msgArray"]


def parse(items, module=CURRENT):
    calls, sleeps = [], []
    def fetch(url):
        calls.append(url)
        return {"msgArray": items}
    with patch.object(module, "_fetch_url", fetch), patch.object(module.time, "sleep", sleeps.append):
        result = module.fetch_mis_etfs([item["c"] for item in items])
    return result, calls, sleeps


class MisPriceRecovery(unittest.TestCase):
    def setUp(self):
        guard = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def test_actual_bid_only_quotes_are_recovered(self):
        result, _, _ = parse(ITEMS)
        self.assertEqual(result["006204"]["price"], 214.95)
        self.assertEqual(result["00668"]["price"], 61.8)
        for item in ITEMS:
            self.assertEqual(result[item["c"]]["mis_time"], item["t"][:5])

    def test_fixed_formal_version_reproduces_dropped_records(self):
        body = subprocess.check_output(["git", "-c", "safe.directory=" + str(ROOT), "-C", str(ROOT),
                                        "show", "21d2512ba935830ca6f7fbb50701a312073b8efe:scripts/mis_fetcher.py"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "before.py"
            path.write_bytes(body)
            before = load(path, "mis_recovery_before")
            self.assertEqual(parse(ITEMS, before)[0], {})
            regular = [dict(ITEMS[0], z="220.5", a="-", b="-")]
            self.assertEqual(parse(regular)[0], parse(regular, before)[0])
            self.assertEqual(parse(regular)[1:], parse(regular, before)[1:])

    def test_one_bad_side_does_not_discard_other_side(self):
        for invalid in ["-", "", None, "NaN", "Infinity", "bad", True, -1, "0"]:
            for side in ("a", "b"):
                item = dict(ITEMS[0], z="-", a="210_", b="210_")
                item[side] = invalid
                with self.subTest(side=side, value=invalid):
                    self.assertEqual(parse([item])[0][item["c"]]["price"], 210)

    def test_regular_midpoint_and_previous_close_order(self):
        for data, expected in [({"z": "220", "a": "210_", "b": "200_"}, 220),
                               ({"z": "-", "a": "210_", "b": "200_"}, 205),
                               ({"z": "-", "a": "-", "b": "-", "y": "199"}, 199)]:
            item = dict(ITEMS[0], **data)
            self.assertEqual(parse([item])[0][item["c"]]["price"], expected)

    def test_invalid_all_prices_never_create_a_zero_or_nonfinite_price(self):
        for invalid in ["-", None, "NaN", "Infinity", "-Infinity", "0", "-1", True, False]:
            item = dict(ITEMS[0], z=invalid, a=invalid, b=invalid, y=invalid)
            with self.subTest(value=invalid):
                self.assertEqual(parse([item])[0], {})

    def test_invalid_trade_price_uses_available_quote(self):
        for invalid in ["NaN", "Infinity", "-Infinity", True, "0"]:
            item = dict(ITEMS[0], z=invalid, a="-", b="210_")
            self.assertEqual(parse([item])[0][item["c"]]["price"], 210)

    def test_original_batch_size_pause_and_otc_prefix_are_preserved(self):
        codes = [str(10000 + i) for i in range(41)]
        calls, sleeps = [], []
        with patch.object(CURRENT, "_fetch_url", lambda url: calls.append(url) or {"msgArray": []}), \
                patch.object(CURRENT.time, "sleep", sleeps.append):
            CURRENT.fetch_mis_etfs(codes, otc_codes={codes[20]})
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [3, 3])
        self.assertIn("otc_" + codes[20] + ".tw", calls[1])
        self.assertNotIn("tse_" + codes[20] + ".tw", calls[1])

    def test_without_valid_previous_close_change_does_not_become_infinite(self):
        for invalid in [None, "0", "NaN", "Infinity", True]:
            item = dict(ITEMS[0], z="210", y=invalid)
            result = parse([item])[0][item["c"]]
            self.assertEqual(result["change_pct"], 0)
            self.assertTrue(math.isfinite(result["change_pt"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
