"""
每週自動驗證 ETF 配息頻率。
對照 TWSE ETF_SEARCH，若與 dividend_info.json 不符則自動修正並輸出變動報告。
"""
import json, time, requests
from pathlib import Path

DIV_JSON = Path(__file__).parent.parent / "data" / "dividend_info.json"

FREQ_KEYWORDS = [
    (["每月", "月配", "按月"], "月配"),
    (["每季", "季配", "按季"], "季配"),
    (["每半年", "半年配", "半年度"], "半年配"),
    (["每年", "年配", "按年"], "年配"),
    (["不配", "不分配", "不收益分配"], "不配息"),
]

def fetch_freq_twse(code):
    try:
        clean = ''.join(c for c in code if c.isalnum())
        r = requests.get(
            f"https://www.twse.com.tw/fund/ETF_SEARCH?response=json&etfNo={clean}",
            timeout=8, headers={"User-Agent": "Mozilla/5.0"}
        )
        text = r.text
        for keywords, freq in FREQ_KEYWORDS:
            if any(kw in text for kw in keywords):
                return freq
    except Exception:
        pass
    return None


def main():
    with open(DIV_JSON, encoding="utf-8") as f:
        data = json.load(f)

    etfs = data["etfs"]
    changes = []
    skipped = []

    for code, meta in etfs.items():
        current = meta.get("frequency", "不明")
        twse = fetch_freq_twse(code)
        time.sleep(0.4)

        if twse is None:
            skipped.append(f"{code} {meta['name']} (TWSE 無資料)")
            continue

        if twse != current:
            note = ""
            # 已確認過的條目頻率改了，months 也需要重新核實
            if not meta.get("_todo", True):
                meta["_todo"] = True
                meta["months"] = []
                note = " ⚠️ 已重設 _todo=true，請核實 months"
            meta["frequency"] = twse
            changes.append(f"  {code} {meta['name']}: {current} → {twse}{note}")

    if changes:
        with open(DIV_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ 修正 {len(changes)} 支 ETF 配息頻率：")
        for c in changes:
            print(c)
    else:
        print("✓ 全部 ETF 配息頻率與 TWSE 一致，無需修正")

    if skipped:
        print(f"\n⚠ TWSE 查無資料（共 {len(skipped)} 支，略過）：")
        for s in skipped:
            print(f"  {s}")


if __name__ == "__main__":
    main()
