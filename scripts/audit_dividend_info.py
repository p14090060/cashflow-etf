# -*- coding: utf-8 -*-
"""
audit_dividend_info.py
比對 dividend_info.json 與 TWSE ETFortune ajaxDividendData 的差異報告。

資料來源：TWSE ETFortune  POST /zh/ETFortune/ajaxDividendData
  - 每支 ETF 一次 POST，回傳最近最多 ~4 筆配息紀錄（含除息日與實際金額）

用法: python scripts/audit_dividend_info.py
"""

import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

# ── 確保 UTF-8 輸出 ──────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 設定 ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_FILE = REPO_ROOT / "data" / "dividend_info.json"

FREQ_MAP = {"月配": 12, "季配": 4, "半年配": 2, "年配": 1, "不配息": 0}

TODAY = date.today()

# ── ROC 日期轉換 ─────────────────────────────────────────
ROC_PAT = re.compile(r"(\d{2,3})年(\d{1,2})月(\d{1,2})日")


def parse_roc_date(text: str):
    """民國日期 → date；失敗回 None"""
    m = ROC_PAT.search(text)
    if not m:
        return None
    try:
        return date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# ── TWSE 請求 ────────────────────────────────────────────
AJAX_URL = "https://www.twse.com.tw/zh/ETFortune/ajaxDividendData"

# 跳過 SSL 驗證（TWSE 憑證鏈在部分 Windows 環境有問題）
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.twse.com.tw/rwd/zh/ETFortune/dividendCalendar",
}


def fetch_dividend_data(code: str) -> list:
    """
    POST ajaxDividendData，回傳 list of (ex_date, amount)，按除息日升序排列。
    失敗回 []。
    """
    params = urllib.parse.urlencode(
        {"lang": "zh", "response": "json", "stkNo": code, "top": "top"}
    )
    body = params.encode("utf-8")

    for attempt in range(2):
        try:
            req = urllib.request.Request(
                AJAX_URL, data=body, headers=HEADERS, method="POST"
            )
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            break
        except Exception as e:
            if attempt == 0:
                print(f"  [警告] {code} 第1次失敗: {e}，重試…")
                time.sleep(1.5)
            else:
                print(f"  [錯誤] {code} 無法取得資料: {e}")
                return []

    records = []
    for row in payload.get("data", []):
        if len(row) < 6:
            continue
        ex_date = parse_roc_date(row[2])
        if ex_date is None:
            continue
        # 過濾：只取過去 12 個月 + 未來 2 個月的紀錄
        months_diff = (TODAY.year - ex_date.year) * 12 + (TODAY.month - ex_date.month)
        if months_diff > 12 or months_diff < -2:
            continue
        amt_str = str(row[5]).replace(",", "").strip()
        if not amt_str:
            continue
        try:
            amount = float(amt_str)
        except ValueError:
            continue
        records.append((ex_date, amount))

    records.sort()
    return records


# ── 頻率判斷 ─────────────────────────────────────────────
def infer_frequency(dates: list) -> str:
    """由除息日清單推算配息頻率（dates 為已排序的 date 清單）"""
    if len(dates) < 2:
        return "無法判斷(僅1筆)" if dates else "無法判斷(0筆)"
    gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    avg_gap = sum(gaps) / len(gaps)
    if avg_gap < 45:
        return "月配"
    elif avg_gap <= 100:
        return "季配"
    elif avg_gap <= 200:
        return "半年配"
    else:
        return "年配"


# ── 主程式 ───────────────────────────────────────────────
def main():
    # 1. 載入 dividend_info.json
    with open(DATA_FILE, encoding="utf-8") as f:
        div_info = json.load(f)
    etfs = div_info.get("etfs", {})
    print(f"已載入 dividend_info.json，共 {len(etfs)} 支 ETF")
    print(f"今日日期：{TODAY.isoformat()}")
    print(f"資料來源：TWSE ETFortune ajaxDividendData（每支 ETF 一次 POST）")
    print(f"篩選範圍：過去 12 個月 ~ 未來 2 個月的除息紀錄\n")
    print(f"開始抓取，共 {len(etfs)} 次請求，每次間隔 0.5s …\n")

    # 2. 逐支 ETF 抓取
    twse_data: dict[str, list] = {}  # code → list of (ex_date, amount)
    for i, code in enumerate(etfs.keys(), 1):
        records = fetch_dividend_data(code)
        twse_data[code] = records
        status = f"{len(records)}筆" if records else "無紀錄"
        print(f"  [{i:3d}/{len(etfs)}] {code:<8} {status}")
        time.sleep(0.5)

    print(f"\n抓取完成。")

    # 3. 比對
    freq_errors = []
    avg_errors = []
    no_twse_but_has_avg = []
    ok_list = []
    corrections = []

    for code, info in etfs.items():
        stored_freq = info.get("frequency", "")
        stored_avg = info.get("avg_dividend_per_share")
        name = info.get("name", code)
        records = twse_data.get(code, [])

        # 無 TWSE 紀錄
        if not records:
            if stored_avg not in (None, 0):
                no_twse_but_has_avg.append(
                    {
                        "code": code,
                        "name": name,
                        "stored_freq": stored_freq,
                        "stored_avg": stored_avg,
                    }
                )
            continue

        # 推算頻率
        dates_only = [r[0] for r in records]
        actual_freq = infer_frequency(dates_only)

        # 計算實際平均（最近 6 筆，但 API 最多回 4 筆，取全部）
        recent = records[-6:]
        actual_avg = round(sum(r[1] for r in recent) / len(recent), 4)

        # 比較頻率
        freq_mismatch = (
            actual_freq not in ("無法判斷(僅1筆)", "無法判斷(0筆)")
            and stored_freq not in ("不配息",)
            and actual_freq != stored_freq
        )

        # 比較平均配息
        avg_mismatch = False
        avg_pct = None
        if stored_avg not in (None, 0):
            diff_pct = abs(actual_avg - stored_avg) / stored_avg
            avg_pct = diff_pct * 100
            if diff_pct > 0.20:
                avg_mismatch = True

        correction = {
            "code": code,
            "name": name,
            "stored_freq": stored_freq,
            "actual_freq": actual_freq,
            "stored_avg": stored_avg,
            "actual_avg": actual_avg,
            "avg_diff_pct": round(avg_pct, 1) if avg_pct is not None else None,
            "twse_count": len(records),
            "twse_records": [(str(d), a) for d, a in records],
            "issues": [],
        }

        if freq_mismatch:
            correction["issues"].append("頻率錯誤")
            freq_errors.append(correction)
        if avg_mismatch:
            correction["issues"].append("平均配息差異>20%")
            avg_errors.append(correction)
        if not freq_mismatch and not avg_mismatch:
            ok_list.append(correction)

        if freq_mismatch or avg_mismatch:
            corrections.append(correction)

    # ── 5. 輸出報告 ──────────────────────────────────────
    SEP = "=" * 72

    print()
    print(SEP)
    print("  TWSE ETFortune 配息資料稽核報告")
    print(f"  產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)

    # Section A：頻率錯誤
    print(f"\n【A】頻率錯誤  ({len(freq_errors)} 支)")
    print("-" * 72)
    if freq_errors:
        for c in freq_errors:
            dates_str = ", ".join(r[0] for r in c["twse_records"])
            print(
                f"  {c['code']:<8} {c['name']:<20}"
                f"  檔案:{c['stored_freq']:<6} → TWSE:{c['actual_freq']:<8}"
                f"  (筆數:{c['twse_count']})"
            )
            print(f"           除息日: {dates_str}")
    else:
        print("  (無)")

    # Section B：平均配息差異 >20%
    print(f"\n【B】平均配息差異 >20%  ({len(avg_errors)} 支)")
    print("-" * 72)
    if avg_errors:
        for c in avg_errors:
            amts_str = ", ".join(str(r[1]) for r in c["twse_records"])
            print(
                f"  {c['code']:<8} {c['name']:<20}"
                f"  檔案avg:{str(c['stored_avg']):<8} → TWSE均:{c['actual_avg']:<8}"
                f"  差異:{c['avg_diff_pct']:.1f}%"
            )
            print(f"           TWSE各筆金額: {amts_str}")
    else:
        print("  (無)")

    # Section C：無 TWSE 紀錄但有 avg 填值
    print(f"\n【C】無 TWSE 紀錄但有 avg 填值  ({len(no_twse_but_has_avg)} 支)")
    print("  (可能：新 ETF 尚未配息、搜尋範圍內無配息、代號特殊)")
    print("-" * 72)
    if no_twse_but_has_avg:
        for c in no_twse_but_has_avg:
            print(
                f"  {c['code']:<8} {c['name']:<20}"
                f"  頻率:{c['stored_freq']:<6}"
                f"  avg:{c['stored_avg']}"
            )
    else:
        print("  (無)")

    # Section D：正常
    print(f"\n【D】正常  ({len(ok_list)} 支有 TWSE 紀錄且無重大差異)")
    print("-" * 72)
    for c in ok_list:
        freq_note = ""
        if c["actual_freq"] in ("無法判斷(僅1筆)", "無法判斷(0筆)"):
            freq_note = f"  ← {c['actual_freq']}"
        avg_note = ""
        if c["avg_diff_pct"] is not None:
            avg_note = f"  差:{c['avg_diff_pct']:.1f}%"
        stored_avg_str = str(c["stored_avg"]) if c["stored_avg"] is not None else "null"
        print(
            f"  {c['code']:<8} {c['name']:<20}"
            f"  {c['stored_freq']:<6}"
            f"  avg:{stored_avg_str:<8} TWSE均:{c['actual_avg']:<8}{avg_note}{freq_note}"
        )

    # ── 修正建議 ─────────────────────────────────────────
    print(f"\n{SEP}")
    print("  修正建議（有問題的 ETF 應改為以下值）")
    print(SEP)
    if corrections:
        for c in corrections:
            issues_str = ", ".join(c["issues"])
            print(f"\n  [{c['code']}] {c['name']}  問題：{issues_str}")
            print(f"    TWSE 最近紀錄：")
            for d, a in c["twse_records"]:
                print(f"      {d}  →  {a} 元")
            if "頻率錯誤" in c["issues"]:
                print(
                    f"    ✗ frequency: \"{c['stored_freq']}\"  →  建議改為 \"{c['actual_freq']}\""
                )
            if "平均配息差異>20%" in c["issues"]:
                print(
                    f"    ✗ avg_dividend_per_share: {c['stored_avg']}"
                    f"  →  建議改為 {c['actual_avg']}"
                    f"  (差異 {c['avg_diff_pct']:.1f}%)"
                )
    else:
        print("  (無需修正)")

    # ── 高殖利率警告 ─────────────────────────────────────
    print(f"\n{SEP}")
    print("  高殖利率警告  (avg × 年化頻率 > 15 元/股)")
    print("  ※ 若年化配息 > 15 元表示 avg 或 frequency 可能偏高，請確認")
    print("-" * 72)
    warned = []
    for code, info in etfs.items():
        stored_avg = info.get("avg_dividend_per_share")
        stored_freq = info.get("frequency", "")
        freq_mult = FREQ_MAP.get(stored_freq, 0)
        if stored_avg and freq_mult > 0:
            annualized = stored_avg * freq_mult
            if annualized > 15:
                warned.append(
                    (
                        code,
                        info.get("name", code),
                        stored_freq,
                        stored_avg,
                        annualized,
                    )
                )
    if warned:
        for code, name, freq, avg, ann in warned:
            print(
                f"  {code:<8} {name:<20}  {freq}  avg={avg}"
                f"  年化~{ann:.2f}元  ← 確認是否合理"
            )
    else:
        print("  (無 avg × 頻率 > 15 的項目)")

    # ── 摘要 ─────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  摘要")
    print(SEP)
    has_twse = sum(1 for code in etfs if twse_data.get(code))
    print(f"  dividend_info.json ETF 數量  : {len(etfs)}")
    print(f"  TWSE 12個月內有配息紀錄者    : {has_twse}")
    print(f"  無 TWSE 紀錄（新/無配/範圍外）: {len(etfs) - has_twse}")
    print(f"  Section A 頻率錯誤            : {len(freq_errors)}")
    print(f"  Section B 平均配息差異>20%    : {len(avg_errors)}")
    print(f"  Section C 無資料但有avg填值   : {len(no_twse_but_has_avg)}")
    print(f"  Section D 正常                : {len(ok_list)}")
    print(SEP)


if __name__ == "__main__":
    main()
