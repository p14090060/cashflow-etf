"""scripts/validate_data.py
發布前驗證資料檔（fetch.yml 在 commit 前呼叫）。「腳本 exit 0」不等於「資料有效」，這裡獨立再驗一次。

用法：python scripts/validate_data.py base [data/_base.json]
      python scripts/validate_data.py market [data/market.json]
驗證通過 exit 0；失敗印出 ::error::（GitHub Actions 註記）、有設 TELEGRAM_BOT_TOKEN／TELEGRAM_CHAT_ID
就發 Telegram（與 daily_check.py 同一組 secrets），exit 1。
"""
import json, os, sys, urllib.request
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from json_safe import DataInvalid, load_strict, validate_base, validate_market   # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
KINDS = {
    "base":   (ROOT / "data" / "_base.json", validate_base),
    "market": (ROOT / "data" / "market.json", validate_market),
}


def notify(msg):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        return
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": msg}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[NOTIFY ERROR] {e}", file=sys.stderr)


def check(kind, path=None):
    """回傳 None（有效）或錯誤訊息字串。"""
    default, validate = KINDS[kind]
    path = Path(path) if path else default
    try:
        validate(load_strict(path))
        return None
    except (OSError, ValueError, DataInvalid) as e:      # json.JSONDecodeError 是 ValueError
        return f"{path.name} 驗證失敗：{e}"


def main(argv):
    if len(argv) < 2 or argv[1] not in KINDS:
        print(__doc__)
        return 2
    err = check(argv[1], argv[2] if len(argv) > 2 else None)
    if err:
        print(f"::error::{err}")
        notify(f"🚨 ETF存股雷達：{err}，本次不提交該檔（保留上一版）")
        return 1
    print(f"[VALIDATE] {argv[1]} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
