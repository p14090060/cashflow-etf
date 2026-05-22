"""
scripts/verify_yld.py
自動比對所有 ETF 的殖利率：FinMind vs TWSE ETFortune（主）
FinMind 超額時降級為 TWSE vs cur_yld 模式。
輸出差異報告，超過容許誤差的列為「需人工確認」

用法：python scripts/verify_yld.py
"""
import json, re, ssl, time, datetime, requests, urllib.request as _ur
from pathlib import Path

ROOT    = Path(__file__).parent.parent
MARKET  = ROOT / "data" / "market.json"
REPORT  = ROOT / "data" / "yld_verify_report.json"

TOLERANCE    = 2.0   # 殖利率差距容許值（%）
TWSE_DELAY   = 0.6   # TWSE 每次請求間隔（秒），避免被限速

# 已知有拆股的 ETF（ret1y 需特別關注）
SPLIT_CODES = {"0050", "0052", "00631L", "00663L", "00685L"}

_fm_limit_reached = False  # FinMind 超額旗標（全局，只警告一次）

def check_ret1y(e):
    """回傳 (status, note)：OK / 可疑"""
    code        = e['code']
    ret1y       = e.get('ret1y', 0)
    new_listing = e.get('new_listing', False)

    if new_listing:
        return "跳過", "新上市"
    if ret1y is None or ret1y == 0:
        return "可疑", "ret1y=0（非新上市，應有報酬率）"
    if ret1y > 300:
        return "可疑", f"ret1y={ret1y}% 過高，疑似拆股未修正（台股AI行情150-230%屬正常）"
    if ret1y < -60:
        return "可疑", f"ret1y={ret1y}% 過低"
    if code in SPLIT_CODES:
        return "注意", f"有拆股紀錄，ret1y={ret1y}%，請確認合理"
    return "OK", ""

_FREQ_N = {"月配": 12, "雙月配": 6, "季配": 4, "半年配": 2, "年配": 1}

ROC_RE = re.compile(r'(\d+)年(\d+)月(\d+)日')
TR_RE  = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
TD_RE  = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.DOTALL | re.IGNORECASE)
TAG_RE = re.compile(r'<[^>]+>')

def strip(h):
    return TAG_RE.sub('', h).strip()

def roc_to_iso(s):
    m = ROC_RE.search(str(s))
    if not m:
        return ""
    return f"{int(m.group(1))+1911}-{m.group(2)}-{m.group(3)}"

def _calc_annual(payments, div_freq):
    """依頻率計算年化配息額。payments 已降序排序。"""
    if not payments:
        return 0.0
    n = _FREQ_N.get(div_freq, 0)
    if n > 0:
        recent = payments[:n]
        return sum(a for _, a in recent) / len(recent) * n
    else:
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        return sum(a for d, a in payments if d >= cutoff)

def fetch_finmind(code, price, div_freq):
    """回傳 (yld_float, limit_reached_bool)"""
    global _fm_limit_reached
    if _fm_limit_reached or div_freq == "不配息" or price <= 0:
        return 0.0, _fm_limit_reached
    try:
        start = (datetime.datetime.now() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
        r = requests.get(
            f'https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockDividend&data_id={code}&start_date={start}',
            timeout=8, headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code == 402:
            _fm_limit_reached = True
            return 0.0, True
        data = r.json().get('data', [])
        payments = sorted(
            [(x.get('date',''), float(x.get('CashEarningsDistribution', 0) or 0))
             for x in data if float(x.get('CashEarningsDistribution', 0) or 0) > 0],
            key=lambda x: x[0], reverse=True
        )
        annual = _calc_annual(payments, div_freq)
        return (round(annual / price * 100, 1) if annual > 0 else 0.0), False
    except Exception:
        return 0.0, False

def fetch_twse(code, price, div_freq):
    """回傳 yld_float。呼叫後外層應 sleep(TWSE_DELAY)。"""
    if div_freq == "不配息" or price <= 0:
        return 0.0
    try:
        start = (datetime.datetime.now() - datetime.timedelta(days=730)).strftime('%Y%m%d')
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        url = f"https://www.twse.com.tw/rwd/zh/ETFortune/dividendList?stkNo={code}&startDate={start}"
        req = _ur.Request(url, headers={"User-Agent": "ETF-verify/1.0"})
        with _ur.urlopen(req, timeout=12, context=ctx) as resp:
            html = resp.read().decode("utf-8")
        payments = []
        for tr in TR_RE.finditer(html):
            cells = [strip(td.group(1)) for td in TD_RE.finditer(tr.group(1))]
            if len(cells) < 6 or cells[0].strip() != code:
                continue
            date_str = roc_to_iso(cells[2])
            if not date_str:
                continue
            try:
                amt = float(str(cells[5]).replace(',', ''))
            except Exception:
                amt = 0.0
            if amt > 0:
                payments.append((date_str, amt))
        if not payments:
            return 0.0
        payments.sort(key=lambda x: x[0], reverse=True)
        annual = _calc_annual(payments, div_freq)
        return round(annual / price * 100, 1) if annual > 0 else 0.0
    except Exception:
        return 0.0

def main():
    global _fm_limit_reached

    data = json.loads(MARKET.read_text(encoding='utf-8'))
    etfs = data.get('etfs', [])
    print(f"[VERIFY] 共 {len(etfs)} 支 ETF，開始比對殖利率...")

    ok, warn, fail, skip = [], [], [], []
    fm_skipped_count = 0

    for i, e in enumerate(etfs):
        code     = e['code']
        price    = e.get('price', 0)
        freq     = e.get('div_frequency') or e.get('div_freq', '不明')
        cur_yld  = e.get('yld', 0) or 0.0

        if freq == "不配息":
            skip.append({"code": code, "reason": "不配息"})
            print(f"  [{i+1:3d}/{len(etfs)}] {code:<8} SKIP（不配息）")
            continue

        # --- FinMind ---
        fm_yld, fm_limited = fetch_finmind(code, price, freq)
        if fm_limited and fm_skipped_count == 0:
            print(f"  !! FinMind 今日額度已用盡，改用 TWSE vs cur_yld 模式")
        if fm_limited:
            fm_skipped_count += 1

        # --- TWSE ETFortune ---
        twse_yld = fetch_twse(code, price, freq)
        time.sleep(TWSE_DELAY)  # 避免 TWSE 限速

        ret_status, ret_note = check_ret1y(e)

        # --- 決定比對策略 ---
        if not fm_limited:
            # 雙源模式：FinMind vs TWSE
            if fm_yld > 0 and twse_yld > 0:
                diff = abs(fm_yld - twse_yld)
                mode = "FM×TW"
                ref_a, ref_b = fm_yld, twse_yld
            elif twse_yld > 0:
                diff = abs(twse_yld - cur_yld)
                mode = "TW×cur"
                ref_a, ref_b = twse_yld, cur_yld
            else:
                diff = None
                mode = "單源"
                ref_a, ref_b = fm_yld, twse_yld
        else:
            # 降級模式：TWSE vs cur_yld
            if twse_yld > 0:
                diff = abs(twse_yld - cur_yld)
                mode = "TW×cur"
                ref_a, ref_b = twse_yld, cur_yld
            else:
                diff = None
                mode = "單源"
                ref_a, ref_b = 0.0, 0.0

        rec = {
            "code": code, "freq": freq, "price": price,
            "cur": cur_yld, "finmind": fm_yld, "twse": twse_yld,
            "ret1y": e.get('ret1y'), "ret_status": ret_status, "ret_note": ret_note,
            "mode": mode,
        }

        if diff is None:
            yld_status = "單源"
            fail.append(rec)
        elif diff <= TOLERANCE:
            yld_status = "OK"
            rec["diff"] = round(diff, 1)
            ok.append(rec)
        else:
            yld_status = "差異"
            rec["diff"] = round(diff, 1)
            warn.append(rec)

        ret_flag = f" | ret1y={e.get('ret1y')}%[{ret_status}]" if ret_status not in ("OK", "跳過") else ""
        print(f"  [{i+1:3d}/{len(etfs)}] {code:<8} {freq:<5} FM={fm_yld:.1f}% TW={twse_yld:.1f}% cur={cur_yld:.1f}% [{mode}] → {yld_status}{ret_flag}")

    report = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fm_limit_reached": _fm_limit_reached,
        "summary": {
            "total": len(etfs),
            "ok": len(ok),
            "warn_diff": len(warn),
            "single_source": len(fail),
            "skip_no_div": len(skip),
        },
        "need_review": warn,
        "single_source": fail,
        "verified_ok": ok,
        "skipped": skip,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"\n{'='*50}")
    if _fm_limit_reached:
        print(f"[注意] FinMind 今日額度用完，{fm_skipped_count} 支改用 TWSE vs cur_yld 比對")
    print(f"結果：OK={len(ok)}  差異需確認={len(warn)}  單源={len(fail)}  不配息={len(skip)}")

    if warn:
        print(f"\n【需人工確認 {len(warn)} 筆】")
        for w in warn:
            a = w['finmind'] if w['mode'] == 'FM×TW' else w['twse']
            b = w['twse']    if w['mode'] == 'FM×TW' else w['cur']
            lbl_a = "FinMind" if w['mode'] == 'FM×TW' else "TWSE"
            lbl_b = "TWSE"    if w['mode'] == 'FM×TW' else "現在顯示"
            print(f"  {w['code']:<8} {w['freq']:<5} {lbl_a}={a:.1f}%  {lbl_b}={b:.1f}%  差={w['diff']:.1f}%  現在顯示={w['cur']:.1f}%")

    if [r for r in (ok + warn + fail) if r.get('ret_status') not in ("OK", "跳過")]:
        print(f"\n【ret1y 異常】")
        for r in ok + warn + fail:
            if r.get('ret_status') not in ("OK", "跳過"):
                print(f"  {r['code']:<8} ret1y={r['ret1y']}%  [{r['ret_status']}] {r['ret_note']}")

    print(f"\n報告已存至 data/yld_verify_report.json")

if __name__ == "__main__":
    main()
