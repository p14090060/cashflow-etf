"""殖利率排行比較資料：真來源原件解析／計算、嚴格驗證、來源額度、真 writer 鏈（fetch→Gate→MIS→Guard→Gate）。

全程離線：socket／DNS／curl_cffi 原生封鎖；git 只用本機假 bare。
原件在 etf/evidence/yield-ranking-sample/2026-11-03（可用 YIELD_SAMPLE_DIR 指定），不修改。
用法：python tests/test_yield_comparison.py [輸出目錄]；輸出目錄會留下候選資料給 tests/browser/yield_rank_test.py。
"""
import copy, datetime as dt, hashlib, io, json, math, os, shutil, socket, subprocess, sys, tarfile, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
NET = []
def _blocked(*a, **k):
    NET.append(repr(a)[:120])
    raise OSError("network blocked")
socket.socket.connect = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
import yield_comparison as Y
from json_safe import DataInvalid, check_yield_basis, validate_market

SAMPLE = Path(os.environ.get("YIELD_SAMPLE_DIR") or ROOT.parents[1] / "evidence/yield-ranking-sample/2026-11-03")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="yield_out_"))
OUT.mkdir(parents=True, exist_ok=True)
AS_OF = dt.date(2026, 11, 3)
fails = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (("  -- " + str(detail)) if detail != "" and not cond else ""))
    if not cond:
        fails.append(name)

def ev(ex, amount="0.5", pay=None, future=None):
    return {"ex_date": ex, "pay_date": pay or ex, "amount": amount, "source": Y.YIELD_SOURCE_TWSE, "source_name": "x",
            "future": dt.date.fromisoformat(ex) > AS_OF if future is None else future}
def row(code="T1", ex="115年06月01日", pay="115年06月10日", amount="0.5", name="測試"):
    return {"code": code, "name": name, "ex": ex, "pay": pay, "amount": amount, "source": Y.YIELD_SOURCE_TWSE}
CODES = {"T1": "測試"}
START = Y.window_start(AS_OF)

# ── 真來源原件 ──
twse_raw, tpex_raw = (SAMPLE / "TWSE_bulk.html").read_bytes(), (SAMPLE / "TPEX_bulk.json").read_bytes()
twse, tpex = Y.parse_twse_html(twse_raw), Y.parse_tpex_json(tpex_raw)
col = json.loads((SAMPLE / "COLLECTION.json").read_bytes())
check("S-0 原件 hash 與採樣紀錄相符（未改寫）", hashlib.sha256(twse_raw).hexdigest() == col["requests"][0]["sha256"]
      and hashlib.sha256(tpex_raw).hexdigest() == col["requests"][1]["sha256"])
check("S-1 TWSE 846 列（847 含表頭）、TPEx 672 列", len(twse) == 846 and len(tpex) == 672, (len(twse), len(tpex)))
M = json.loads((SAMPLE / "market.json").read_bytes())
I = json.loads((SAMPLE / "dividend_info.json").read_bytes())["etfs"]
RK = json.loads((SAMPLE / "ranking.json").read_bytes())
res = [{"code": e["code"], "name": e["name"], "price": e["price"], "new_listing": e.get("new_listing"), "otc": e.get("otc")} for e in M["etfs"]]
conf = {c: m["frequency"] for c, m in I.items() if m.get("frequency")}
SRC = {"twse": twse, "tpex": tpex, "twse_sha256": hashlib.sha256(twse_raw).hexdigest(), "tpex_sha256": hashlib.sha256(tpex_raw).hexdigest()}
# 明示合成：樣本沒有存 ISIN 原件，上市日依樣本 new_listing 給固定值（只決定方法，順序與比率仍對照官方原件算出的樣本）
LD = {e["code"]: "2026-06-01" if e.get("new_listing") else "2020-01-01" for e in M["etfs"]}
summary = Y.attach(res, SRC, {}, conf, {}, {e["code"]: [] for e in res}, LD, AS_OF)
by = {e["code"]: e for e in res}
b406, b992 = by["00406A"]["yield_basis"], by["00992A"]["yield_basis"]
check("S-2 00406A 四期 20.3759…、年化估算", len(b406["events"]) == 4 and str(b406["rate"]).startswith("20.3759") and b406["method"] == "annualized_estimate", b406["rate"])
check("S-3 00992A 兩期 17.8983…、年化估算", len(b992["events"]) == 2 and str(b992["rate"]).startswith("17.8983"), b992["rate"])
check("S-4 00927 滿一年＝近12月", by["00927"]["yield_basis"]["method"] == "trailing_12m")
rows = sorted([e for e in res if e.get("yield_basis")], key=lambda e: (-e["yield_basis"]["rate"], e["code"]))
check("S-5 前 100 名順序與每檔比率＝固定樣本", [e["code"] for e in rows[:100]] == [r["code"] for r in RK["rows"]]
      and all(abs(e["yield_basis"]["rate"] - r["annual_rate"]) < 1e-9 for e, r in zip(rows, RK["rows"])))
check("S-6 名稱不同但代號相同的事件仍採用，原始名稱保留", any(x["source_name"] != e["name"] for e in rows for x in e["yield_basis"]["events"]))
check("S-7 名稱差異有記錄、未因此拒收", any(d["code"] == "00904" for d in summary["name_differences"]))
(OUT / "SAMPLE_NOT_COMPARABLE.json").write_text(json.dumps(summary["not_comparable"], ensure_ascii=False, indent=1), encoding="utf-8")
print("   樣本 eligible：本實作 %d／樣本 %d；差異 %s" % (len(rows), RK["eligible"], summary["not_comparable"].get("009829")))

# ── 解析／事件規則（合成例）──
e_, u_, _ = Y.collect_events([row(amount="")], CODES, START, AS_OF)
check("R-1 已除息空金額 → 分子不完整、不可比較", "T1" in u_)
e_, u_, _ = Y.collect_events([row(ex="115年12月01日", pay="115年12月10日", amount="")], CODES, START, AS_OF)
check("R-2 未來空金額 → 不採用、不算壞", not u_ and not e_.get("T1"))
e_, u_, _ = Y.collect_events([row(ex="115年12月01日", pay="115年12月10日", amount="0.4")], CODES, START, AS_OF)
check("R-3 未來正額 → 標 future", list(e_["T1"].values())[0]["future"] is True)
e_, u_, _ = Y.collect_events([row(code="T2")], CODES, START, AS_OF)
check("R-4 錯代號不採用", not e_ and not u_)
_, u_, _ = Y.collect_events([row(ex="115/06/01")], CODES, START, AS_OF)
check("R-5 壞日期 → 不可比較", "T1" in u_)
for bad in ("NaN", "Infinity", True, -1, "abc", None, "1e3"):
    _, u_, _ = Y.collect_events([row(amount=bad)], CODES, START, AS_OF)
    check("R-6 壞金額 %r → 不可比較" % (bad,), "T1" in u_)
e_, u_, _ = Y.collect_events([row(), row()], CODES, START, AS_OF)
check("R-7 完全相同的重複只算一次", len(e_["T1"]) == 1 and not u_)
_, u_, _ = Y.collect_events([row(), row(amount="0.6")], CODES, START, AS_OF)
check("R-8 同日金額衝突 → 不可比較", "衝突" in u_.get("T1", ""))
e_, u_, _ = Y.collect_events([row(ex="114年11月03日", pay="114年11月20日"), row(ex="114年11月04日", pay="114年11月20日")], CODES, START, AS_OF)
check("R-9 窗口邊界：11/03 排除、11/04 納入", list(e_["T1"]) == ["2025-11-04"])
e_, u_, _ = Y.collect_events([row(amount="0")], CODES, START, AS_OF)
check("R-10 官方明列 0 不算配息也不算缺值", not e_.get("T1") and not u_)
try:
    Y.parse_twse_html("<table><tr><th>別的欄</th></tr></table>".encode()); ok = False
except Y.SourceInvalid:
    ok = True
check("R-11 TWSE 表頭改版 → 來源失敗", ok)

# ── build_basis（合成例）──
SHA = "a" * 64
NEW, OLD = "2026-06-01", "2020-01-01"
B = lambda evs, price=10.0, nl=False, f="季配", ver=(), rec=(), ob=(): Y.build_basis("T1", evs, price, NEW if nl is True else OLD if nl is False else nl, f, AS_OF, SHA, ver, rec, list(ob) if ob is not None else None)
b, why = B([ev("2026-01-05"), ev("2026-04-05"), ev("2026-12-05")])
check("B-1 成熟不含未來事件", b["annual_cash"] == "1.0" and len(b["events"]) == 2 and abs(b["rate"] - 10) < 1e-9, b)
b, why = B([ev("2026-12-05")])
check("B-2 成熟只有未來公告 → 不可比較", b is None)
b, why = B([ev("2026-10-05", "0.2"), ev("2026-12-05", "0.4")], nl=True)
check("B-3 新上市含未來正額 → 估算", b["method"] == "annualized_estimate" and Y.Decimal(b["annual_cash"]) == Y.Decimal("1.2") and b["events"][-1]["future"] is True)
b, why = B([ev("2026-%02d-05" % m, "0.1") for m in range(1, 8)], nl=True)
check("B-4 新上市最多取一年次數", len(b["events"]) == 4)
b, why = B([ev("2026-10-05")], nl=True, f=None)
check("B-5 新上市頻率未知 → 不硬算", b is None and "頻率" in why)
b, why = B([ev("2026-10-05")], f="不配息")
check("B-6 政策不配息 → 不進榜", b is None)
for bad in (float("nan"), float("inf"), 0, -1, True, None, "10"):
    b, why = B([ev("2026-10-05")], price=bad)
    check("B-7 壞價格 %r" % (bad,), b is None)
b, why = B([ev("2026-10-05")], nl=None)
check("B-8 沒有可信上市日 → 不硬算", b is None and "上市日" in why)
b, why = B([])
check("B-9 無事件（含本期不分配）不填 0", b is None and why == "沒有可採正額")
VER = [{"date": "2026-03-01", "ratio": "7", "source": "合成官方依據"}]
b, why = B([ev("2026-01-05", "0.7"), ev("2026-08-05", "0.1")], ver=VER, ob=[dt.date(2026, 3, 1)])
check("B-10 已核實生效日：拆前金額依比例換算且保留原額與依據", abs(b["rate"] - 2.0) < 1e-9 and b["events"][0]["raw_amount"] == "0.7" and b["unit_changes"] == VER, b)
b, why = B([ev("2026-01-05", "0.7")], rec=[("2026-03-01", 7)], ob=[])
check("B-10b 只有約略紀錄、歷史也沒回報（X probe）→ 不造數", b is None and "單位" in why)
b, why = B([ev("2026-01-05", "0.7")], rec=[("2026-03-01", 7)], ob=[dt.date(2026, 3, 5)])
check("B-10c 約略紀錄＋Yahoo 日期相近仍不換算", b is None)
b, why = B([ev("2026-01-05", "0.7")], ver=VER, ob=[dt.date(2026, 3, 5)])
check("B-10d 觀測日與核實生效日不同 → 不可比較（不再容許 31 天）", b is None)
b, why = B([ev("2026-01-05")], rec=[("2025-10-20", 7)], ob=[])
check("B-10e 約略日期在窗口外但差距內 → 仍視為無法確認", b is None)
b, why = B([ev("2026-01-05")], ob=[dt.date(2026, 3, 1)])
check("B-11 窗口內拆分但無可信比例 → 不可比較", b is None and "單位" in why)
b, why = B([ev("2026-01-05")], ob=None)
check("B-12 沒有歷史可核對 → 不可比較", b is None and "單位" in why)
b, why = B([ev("2026-01-05")], ob=[dt.date(2025, 3, 1)])
check("B-13 窗口外拆分不影響", b is not None)
b2 = Y.refresh_basis("T1", b, 8.0, AS_OF)
check("B-14 MIS 同分子配新價", abs(b2["rate"] - 0.5 / 8 * 100) < 1e-9 and b2["annual_cash"] == b["annual_cash"] and b2["price"] == 8.0)
check("B-15 超過 14 天 → 不再稱近12月", Y.refresh_basis("T1", b, 8.0, AS_OF + dt.timedelta(days=15)) is None)
b16 = B([ev("2026-10-05")], nl="2025-11-10")[0]
check("B-16 新上市轉滿一年，舊估算不再沿用", b16["method"] == "annualized_estimate" and Y.refresh_basis("T1", b16, 10.0, dt.date(2026, 11, 12)) is None)
b17 = B([ev("2026-01-05")], nl=True)[0]
check("B-17 方法只看上市日：歷史長短推得的 new_listing 不影響", b17["method"] == "annualized_estimate" and B([ev("2026-01-05")], nl="2025-11-03")[0]["method"] == "trailing_12m")
check("B-18 上市滿一年當日算滿一年、前一天算新上市", B([ev("2026-10-05")], nl="2025-11-04")[0]["method"] == "annualized_estimate" and B([ev("2026-10-05")], nl="2025-11-03")[0]["method"] == "trailing_12m")
check("B-19 上市日晚於資料日 → 不可比較", B([ev("2026-10-05")], nl="2026-12-01")[0] is None)
base_ok = B([ev("2026-01-05")])[0]
for label, mut in (("rate=999", lambda x: x.update(rate=999)), ("price 字串", lambda x: x.update(price="10")), ("分子壞", lambda x: x.update(annual_cash="9")),
                   ("窗口冒充", lambda x: x.update(window_start="2020-01-01")), ("hash 壞", lambda x: x.update(source_sha256="x"))):
    bad_b = copy.deepcopy(base_ok); mut(bad_b)
    check("B-20 損壞前值（%s）不被新價洗成有效（X probe）" % label, Y.refresh_basis("T1", bad_b, 8.0, AS_OF) is None)

# ── json_safe 反向證明 ──
good = B([ev("2026-01-05"), ev("2026-04-05")])[0]
def rejects(mut, price=10.0):
    x = copy.deepcopy(good); mut(x)
    try:
        check_yield_basis("T1", x, price); return False
    except (DataInvalid, KeyError, TypeError):
        return True
for name, mut in {
    "未知欄位": lambda x: x.update(extra=1), "缺欄位": lambda x: x.pop("rate"), "比率不符": lambda x: x.update(rate=11.0),
    "比率 NaN": lambda x: x.update(rate=float("nan")), "比率 bool": lambda x: x.update(rate=True),
    "分子不符": lambda x: x.update(annual_cash="9"), "價格不符": lambda x: x.update(price=11.0), "方法亂寫": lambda x: x.update(method="x"),
    "事件空": lambda x: x.update(events=[]), "事件重複": lambda x: x["events"].append(dict(x["events"][0])),
    "未來標記錯": lambda x: x["events"][0].update(future=True), "未知來源": lambda x: x["events"][0].update(source="goodinfo"),
    "事件超窗": lambda x: x["events"][0].update(ex_date="2020-01-01", pay_date="2020-01-02"),
    "金額 bool": lambda x: x["events"][0].update(amount=True), "發放早於除息": lambda x: x["events"][0].update(pay_date="2025-12-01"),
    "頻率次數不符": lambda x: x.update(periods_per_year=12),
}.items():
    check("V-驗證拒絕 " + name, rejects(mut))
check("V-估算不能掛在滿一年基金", rejects(lambda x: x.update(method="annualized_estimate")))
check("V-近12月不能掛在新上市", rejects(lambda x: x.update(listing_date="2026-06-01")))
def old_as_trailing(x):
    x.update(window_start="2020-01-01", annual_cash="1", rate=10.0, events=[dict(x["events"][0], ex_date="2020-02-01", pay_date="2020-03-01", amount="1")])
check("V-舊年度冒充近12月（X probe）", rejects(old_as_trailing))
check("V-未來資料日（X probe）", rejects(lambda x: x.update(as_of="2099-01-01", window_start="2098-01-02")))
check("V-窗口不是一年", rejects(lambda x: x.update(window_start="2025-01-01")))
check("V-上市日晚於資料日", rejects(lambda x: x.update(listing_date="2099-01-01")))
check("V-換算金額對不上原公告", rejects(lambda x: x.update(unit_changes=[{"date": "2026-03-01", "ratio": "7", "source": "s"}])))
check("V-缺來源 hash", rejects(lambda x: x.pop("source_sha256")))

# ── F1 政策接線（走真 known_policy）──
import official_frequency as OF
vp = json.loads((SAMPLE.parents[1] / "yield-ranking-tool/2026-11-04/x-review/VALID_POLICY_INFO.json").read_text(encoding="utf-8"))
vp = vp.get("etfs", vp)
good_996 = vp.get("00996A") or next(iter(vp.values()))
FM = {"00996A": good_996,
      "G2": {"frequency": "季配", "_todo": True, "_source": "官網寫季配"}, "G3": {"frequency": "年配", "_todo": False},
      "G4": dict(good_996, _todo=False, policy_source=dict(good_996.get("policy_source") or {}, sha256="xyz")),
      "G6": {"frequency": "季配"}}
TF = Y.trusted_frequencies(FM)
check("F1-1 X 以 SITCA 原件產生的 00996A 有效證據＋_todo:true → 接得上（修前 confirmed 為空）", TF.get("00996A") == "季配", TF)
check("F1-2 無證據＋_todo:true，文字 _source 不放行", "G2" not in TF and "G6" not in TF, TF)
check("F1-3 既有已核靜態政策照舊", TF.get("G3") == "年配", TF)
check("F1-4 壞證據即使 _todo:false 也拒用", "G4" not in TF, TF)
RI = Y.trusted_frequencies(I)
print("   真資料：", {c: {"_todo": I[c].get("_todo"), "evidence": "policy_source" in I[c] or "frequency_evidence" in I[c], "trusted": c in RI} for c in ("00996A", "00995A", "00408A")})
check("F1-5 00996A／00995A／00408A 現存紀錄都沒有結構化證據 → 依規則不進榜，不靠文字硬放", not {"00996A", "00995A", "00408A"} & set(RI))
check("V-正例通過", not rejects(lambda x: None))

# ── 來源額度：一輪最多 2 個請求，失敗不重試 ──
calls = []
def fail_read(req):
    calls.append(req.full_url); raise OSError("down")
srcs, n = Y.fetch_sources(AS_OF, read=fail_read)
check("Q-1 全失敗仍只 2 請求、不重試", n == 2 and len(calls) == 2 and srcs == {"twse": None, "tpex": None}, calls)
calls.clear()
srcs, n = Y.fetch_sources(AS_OF, read=lambda req: (calls.append(req.full_url), twse_raw if "twse" in req.full_url else tpex_raw)[1])
check("Q-2 成功也只 2 請求，原文 hash 留下", len(calls) == 2 and len(srcs["twse"]) == 846 and "startDate=20251104" in calls[0] and srcs["twse_sha256"] == SRC["twse_sha256"])
check("Q-2b 每筆 basis 帶所屬市場的原文 hash", by["00927"]["yield_basis"]["source_sha256"] in (SRC["twse_sha256"], SRC["tpex_sha256"]))
prev = {"00927": by["00927"]["yield_basis"]}
r2 = [dict(by["00927"], price=30.0), dict(by["00406A"])]
for x in r2: x.pop("yield_basis")
s2 = Y.attach(r2, {"twse": None, "tpex": tpex, "tpex_sha256": SRC["tpex_sha256"]}, prev, conf, {}, {"00927": [], "00406A": []}, LD, AS_OF + dt.timedelta(days=1))
check("Q-3 來源失敗：沿用前值、as_of 不冒新鮮、分子不變、比率用新價", r2[0]["yield_basis"]["as_of"] == "2026-11-03"
      and r2[0]["yield_basis"]["annual_cash"] == prev["00927"]["annual_cash"] and r2[0]["yield_basis"]["price"] == 30.0 and s2["kept"] == 1)
check("Q-4 無前值 → 不進榜、不造數", "yield_basis" not in r2[1] and "00406A" in s2["not_comparable"])

# ── 真 writer 鏈 ──
FETCH_DRIVER = r'''
import datetime, json, math, os, runpy, socket, sys, time
from pathlib import Path
SAMPLE = Path(os.environ["YIELD_SAMPLE_DIR"])
net = []
def blocked(*a, **k):
    net.append(repr(a)[:100]); raise OSError("network blocked")
socket.socket.connect = blocked; socket.create_connection = blocked; socket.getaddrinfo = blocked
import curl_cffi.curl
curl_cffi.curl.Curl.perform = blocked
time.sleep = lambda s: None
import pandas as pd, yfinance as yf
class Frozen(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        t = datetime.datetime(2026, 11, 3, 16, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        return t.astimezone(tz) if tz else t.replace(tzinfo=None)
datetime.datetime = Frozen
M = {e["code"]: e for e in json.load(open("data/market.json", encoding="utf-8"))["etfs"]}
class T:
    def __init__(self, t, **k): self.code = t.split(".")[0]
    info = {}; dividends = pd.Series(dtype=float)
    def history(self, **k):
        e = M.get(self.code); px = float(e["price"]) if e else 20000.0
        days = 200 if e and e.get("new_listing") else 372
        idx = pd.bdate_range(end="2026-11-03", periods=int(days * 5 / 7), tz="Asia/Taipei")
        c = [round(px * (1 + 0.01 * math.sin(i)), 2) for i in range(len(idx) - 1)] + [px]
        return pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c, "Adj Close": c, "Volume": [1000000] * len(idx), "Dividends": 0.0, "Stock Splits": 0.0}, index=idx)
yf.Ticker = T
sys.path.insert(0, "scripts")
try:
    import yield_comparison as Y
except ImportError:
    Y = None
reads = []
if Y:
    def read(req):
        reads.append(req.full_url)
        if os.environ.get("YIELD_SOURCES_DOWN"): raise OSError("down")
        return (SAMPLE / ("TWSE_bulk.html" if "twse" in req.full_url else "TPEX_bulk.json")).read_bytes()
    Y._default_read = read
    # 假環境 ISIN 不通（本輪上市日是空的）；明示合成上市日只補空缺，真鏈不驗 ISIN 上市日原文
    _attach = Y.attach
    def attach(results, sources, previous, confirmed, records, observed, listing, as_of, verified_units=None):
        fixed = {c: "2026-06-01" if (M.get(c) or {}).get("new_listing") else "2020-01-01" for c in M}
        return _attach(results, sources, previous, confirmed, records, observed, dict(fixed, **listing), as_of, verified_units)
    Y.attach = attach
try:
    runpy.run_path("fetch_etf.py", run_name="__main__")
finally:
    Path(os.environ["YIELD_LOG"]).write_text(json.dumps({"yield_requests": reads, "blocked_attempts": len(net)}), encoding="utf-8")
'''
MIS_DRIVER = r'''
import datetime, importlib.util, json, re, socket, sys, time
def blocked(*a, **k): raise OSError("network blocked")
socket.socket.connect = blocked; socket.create_connection = blocked; socket.getaddrinfo = blocked
time.sleep = lambda s: None
sys.path.insert(0, "scripts")
sp = importlib.util.spec_from_file_location("mis_real", "scripts/mis_fetcher.py")
mf = importlib.util.module_from_spec(sp); sp.loader.exec_module(mf)
mf.tw_now = lambda: datetime.datetime(2026, 11, 4, 11, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
PX = {e["code"]: e["price"] for e in json.load(open("data/_base.json", encoding="utf-8"))["etfs"]}
def fake(url):
    if "getStockInfo" not in url: return []
    items = []
    for code in re.findall(r"(?:tse|otc)_([^.|]+)\.tw", url):
        px = 20000.0 if code == "t00" else round(PX.get(code, 10) * 1.02, 2)
        items.append({"c": code, "z": str(px), "y": str(px / 1.02), "v": "1000", "t": "11:00:00", "d": "20261104"})
    return {"msgArray": items}
mf._fetch_url = fake
mf.main()
'''

def run(args, cwd, env=None, check_rc=True):
    full = {k: v for k, v in os.environ.items() if k not in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GITHUB_OUTPUT", "HEALTHCHECK_URL")}
    full.update(env or {}, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    r = subprocess.run(args, cwd=cwd, capture_output=True, env=full)
    if check_rc and r.returncode:
        raise RuntimeError("%s rc=%s\n%s\n%s" % (args[:3], r.returncode, r.stdout.decode("utf-8", "replace")[-1500:], r.stderr.decode("utf-8", "replace")[-1500:]))
    return r

FIXED_BASE = "a61576ceee6055c451f741e421150a77ab82815c"   # 對照固定在施工前底版，功能 commit 後 HEAD 已含 yield_basis

def chain(tag, overlay, tmp):
    """HEAD 樹＋工作樹施工檔（overlay）或固定底版→ 假 bare → 真 fetch → 真 Gate → 真 MIS → 真 Guard → 真 Gate。"""
    src, bare, clone = tmp / (tag + "_src"), tmp / (tag + ".git"), tmp / (tag + "_clone")
    src.mkdir()
    sd = "safe.directory=" + str(ROOT).replace("\\", "/")
    arc = subprocess.run(["git", "-c", sd, "archive", "HEAD" if overlay else FIXED_BASE], cwd=ROOT, capture_output=True, check=True).stdout
    tarfile.open(fileobj=io.BytesIO(arc)).extractall(src, filter="data")
    if overlay:
        changed = subprocess.run(["git", "-c", sd, "status", "--porcelain", "--", "*.py", "*.js", "*.css", "*.html"], cwd=ROOT, capture_output=True).stdout.decode("utf-8")
        for line in changed.splitlines():
            rel = line[3:].strip().strip('"')
            if (ROOT / rel).is_file():
                (src / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, src / rel)
    G = ["git", "-c", "core.autocrlf=false", "-c", "user.name=t", "-c", "user.email=t@t"]
    run(G + ["init", "-q", "-b", "main"], src); run(G + ["add", "-A"], src); run(G + ["commit", "-qm", "base"], src)
    run(["git", "clone", "-q", "--bare", str(src), str(bare)], tmp)
    run(["git", "clone", "-q", str(bare), str(clone)], tmp)
    for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
        run(["git", "config", k, v], clone)
    log = tmp / (tag + "_fetch.json")
    r = run([sys.executable, "-c", FETCH_DRIVER], clone, {"YIELD_SAMPLE_DIR": str(SAMPLE), "YIELD_LOG": str(log)})
    (OUT / (tag + "_fetch.log")).write_bytes(r.stdout)
    # fetch 也會改其他資料檔；本鏈只驗 _base，其餘還原（配息日曆成對檢查由 fetch_dividend_calendar 那步負責，不在本單）
    for f in run(["git", "diff", "--name-only"], clone).stdout.decode().split():
        if f != "data/_base.json":
            run(["git", "checkout", "-q", "--", f], clone)
    r = run([sys.executable, "scripts/publish_gate.py", "--message", "base data", "data/_base.json"], clone)
    (OUT / (tag + "_gate_base.log")).write_bytes(r.stdout)
    r = run([sys.executable, "-c", MIS_DRIVER], clone)
    (OUT / (tag + "_mis.log")).write_bytes(r.stdout)
    run(["git", "fetch", "-q", "origin", "main"], clone)
    base = run(["git", "rev-parse", "origin/main"], clone).stdout.decode().strip()
    cand = hashlib.sha256((clone / "data/market.json").read_bytes()).hexdigest()
    g = run([sys.executable, "scripts/market_guard.py", "data/market.json", base], clone, check_rc=False)
    (OUT / (tag + "_guard.log")).write_bytes(g.stdout + g.stderr)
    p = run([sys.executable, "scripts/publish_gate.py", "--base", base, "--expect", "data/market.json=" + cand, "--message", "market", "data/market.json"], clone, check_rc=False)
    (OUT / (tag + "_gate_market.log")).write_bytes(p.stdout + p.stderr)
    show = lambda f: json.loads(subprocess.run(["git", "--git-dir", str(bare), "show", "main:" + f], capture_output=True, check=True).stdout)
    return {"clone": clone, "bare": bare, "guard_rc": g.returncode, "gate_rc": p.returncode, "base": show("data/_base.json"), "market": show("data/market.json"),
            "log": json.loads(log.read_text(encoding="utf-8"))}

tmp = Path(tempfile.mkdtemp(prefix="yield_chain_"))
try:
    new = chain("new", True, tmp)
    old = chain("old", False, tmp)
    check("W-1 fetch 本輪新增請求＝2（TWSE＋TPEx 各一）", len(new["log"]["yield_requests"]) == 2, new["log"])
    bb = {e["code"]: e for e in new["base"]["etfs"]}
    mm = {e["code"]: e for e in new["market"]["etfs"]}
    n_b = sum("yield_basis" in e for e in bb.values())
    check("W-2 _base 經原 Gate 進假 bare 且含 yield_basis", n_b > 90, n_b)
    check("W-3 Guard／Gate 放行 market", new["guard_rc"] == 0 and new["gate_rc"] == 0, (new["guard_rc"], new["gate_rc"]))
    validate_market(new["market"])
    with_b = [e for e in mm.values() if e.get("yield_basis")]
    check("W-4 真 MIS 用最新價重算、分子與 _base 相同", len(with_b) == n_b and all(
        e["yield_basis"]["price"] == e["price"] and e["yield_basis"]["annual_cash"] == bb[e["code"]]["yield_basis"]["annual_cash"]
        and e["yield_basis"]["events"] == bb[e["code"]]["yield_basis"]["events"]
        and abs(e["yield_basis"]["rate"] - float(Y.Decimal(e["yield_basis"]["annual_cash"]) / Y.Decimal(str(e["price"])) * 100)) < 1e-9 for e in with_b))
    check("W-5 MIS 價格確實變了（非沿用 _base）", mm["00406A"]["price"] != bb["00406A"]["price"], (mm["00406A"]["price"], bb["00406A"]["price"]))
    sub = {r["code"]: r for r in RK["rows"]}
    check("W-6 真 fetch 的 00406A／00992A 分子＝樣本", Y.Decimal(bb["00406A"]["yield_basis"]["annual_cash"]) == Y.Decimal(sub["00406A"]["annual_cash"])
          and Y.Decimal(bb["00992A"]["yield_basis"]["annual_cash"]) == Y.Decimal(sub["00992A"]["annual_cash"]))
    b0052 = bb.get("0052", {}).get("yield_basis")
    check("W-7 0052 窗口內 1 拆 7 沒有已核實生效日 → 不可比較", b0052 is None, b0052)
    strip = lambda d: {k: {f: v for f, v in e.items() if f != "yield_basis"} for k, e in ((x["code"], x) for x in d["etfs"])}
    check("W-8 _base：與固定底版只差 yield_basis（集合／價格／訊號／yld／歷史／新上市 null 全同）", strip(new["base"]) == strip(old["base"]))
    check("W-9 market：與固定底版只差 yield_basis", strip(new["market"]) == strip(old["market"]))
    check("W-10 底版確實沒有 yield_basis", not any("yield_basis" in e for e in old["market"]["etfs"]))
    shutil.copy2(new["clone"] / "data/market.json", OUT / "candidate_market.json")
    # 壞欄位／缺欄位相容：_base 帶壞資料，真 MIS 剔除該檔、其他照常
    clone = new["clone"]
    base_path = clone / "data/_base.json"
    doc = json.loads(base_path.read_text(encoding="utf-8"))
    for e in doc["etfs"]:
        if e["code"] == "00406A": e["yield_basis"]["rate"] = 99.0; e["yield_basis"]["annual_cash"] = "abc"
        if e["code"] == "00992A": e.pop("yield_basis")
    base_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    run([sys.executable, "-c", MIS_DRIVER], clone)
    m2 = {e["code"]: e for e in json.loads((clone / "data/market.json").read_text(encoding="utf-8"))["etfs"]}
    check("W-11 壞／缺欄位：該檔不帶欄位、其他不變、market 仍寫出", "yield_basis" not in m2["00406A"] and "yield_basis" not in m2["00992A"]
          and "yield_basis" in m2["00927"] and set(m2) == set(mm))
    # 來源全掛：沿用 _base 前值，as_of 不變
    run(["git", "checkout", "-q", "--", "data"], clone)
    r = run([sys.executable, "-c", FETCH_DRIVER], clone, {"YIELD_SAMPLE_DIR": str(SAMPLE), "YIELD_LOG": str(tmp / "down.json"), "YIELD_SOURCES_DOWN": "1"})
    b3 = {e["code"]: e for e in json.loads(base_path.read_text(encoding="utf-8"))["etfs"]}
    down = json.loads((tmp / "down.json").read_text(encoding="utf-8"))
    check("W-12 兩來源失敗：仍只 2 請求、_base 照常、比較資料沿用", len(down["yield_requests"]) == 2 and b3["00927"]["yield_basis"]["annual_cash"] == bb["00927"]["yield_basis"]["annual_cash"], down)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
check("NET 測試程序零連線", not NET, NET[:3])
print("\n%d 項失敗" % len(fails) if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
