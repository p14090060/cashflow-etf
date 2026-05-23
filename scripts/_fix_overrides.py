"""把 _YLD_OVERRIDE 的值寫進 _base.json，yld_verified=True"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = ROOT / "data" / "_base.json"

OVERRIDES = {
    "006208": 2.0,
    "00702": 2.7,
    "00717": 3.8,
    "00771": 1.3,
    "00882": 2.8,
    "00907": 4.3,
    "00770": 6.5,
    "00911": 1.8,
    "00913": 3.7,
    "00923": 4.5,
    "00830": 10.8,
    "00904": 6.7,
    "00714": 2.3,
    "00733": 0.8,
    "00728": 0.9,
    "00690": 5.7,
    "00984D": 0.8,
}

data = json.loads(BASE.read_text(encoding='utf-8'))
updated = []
for e in data.get('etfs', []):
    code = e['code']
    if code in OVERRIDES:
        old = e.get('yld')
        e['yld'] = OVERRIDES[code]
        e['yld_verified'] = True
        updated.append(f"  {code}: {old} → {OVERRIDES[code]}")

BASE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"更新 {len(updated)} 支：")
for line in updated:
    print(line)
print("已存回 data/_base.json")
