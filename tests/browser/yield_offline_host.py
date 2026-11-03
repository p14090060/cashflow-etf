"""離線瀏覽器環境：本機 http 8765 提供站台、Chrome remote debugging 9223；market.json 等遠端請求由 CDP 改答本機候選，
其他外連一律中止並記錄。在環境存活期間依序執行 tests/browser 的測試腳本。

用法：python tests/browser/yield_offline_host.py <站台目錄> <候選 market.json> <輸出目錄> 測試1.py [測試2.py ...]
"""
import base64, functools, http.server, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.parse, urllib.request
from pathlib import Path
import websocket

site, market, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
tests = sys.argv[4:]
out.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CHROME = next(p for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p))

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), functools.partial(Quiet, directory=str(site)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = tempfile.mkdtemp(prefix="yield_chrome_")
chrome = subprocess.Popen([CHROME, "--headless=new", "--remote-debugging-port=9223", "--user-data-dir=" + prof, "--no-first-run", "--disable-gpu",
                           "--disable-background-networking", "--disable-component-update", "--window-size=460,850", "about:blank"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
external, local_answers = [], []
stop = threading.Event()
try:
    for _ in range(100):
        try:
            page = [t for t in json.load(urllib.request.urlopen("http://127.0.0.1:9223/json")) if t["type"] == "page"][0]
            break
        except Exception:
            time.sleep(.1)
    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=2)
    def intercept():
        ws.send(json.dumps({"id": 1, "method": "Fetch.enable", "params": {"patterns": [{"urlPattern": "*"}]}}))
        n = 10
        while not stop.is_set():
            try:
                msg = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                return
            if msg.get("method") != "Fetch.requestPaused":
                continue
            rid, url = msg["params"]["requestId"], msg["params"]["request"]["url"]
            n += 1
            host = urllib.parse.urlsplit(url).hostname
            m = re.match(r"https://raw\.githubusercontent\.com/p14090060/cashflow-etf/main/data/([^?]+)", url)
            if host == "127.0.0.1" or url.startswith("data:"):
                ws.send(json.dumps({"id": n, "method": "Fetch.continueRequest", "params": {"requestId": rid}}))
            elif m:
                local_answers.append(m[1])
                body = market.read_bytes() if m[1] == "market.json" else (site / "data" / m[1]).read_bytes()
                ws.send(json.dumps({"id": n, "method": "Fetch.fulfillRequest", "params": {"requestId": rid, "responseCode": 200,
                    "responseHeaders": [{"name": "Content-Type", "value": "application/json"}, {"name": "Access-Control-Allow-Origin", "value": "*"}],
                    "body": base64.b64encode(body).decode()}}))
            else:
                external.append(url[:160])
                ws.send(json.dumps({"id": n, "method": "Fetch.failRequest", "params": {"requestId": rid, "errorReason": "BlockedByClient"}}))
    threading.Thread(target=intercept, daemon=True).start()
    time.sleep(.5)
    summary = {}
    for t in tests:
        name = Path(t).stem
        try:
            r = subprocess.run([sys.executable, t], cwd=site, capture_output=True, timeout=420,
                               env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", YIELD_OUT=str(out), YIELD_MARKET=str(market)))
            text, rc = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace"), r.returncode
        except subprocess.TimeoutExpired as ex:
            text, rc = (ex.stdout or b"").decode("utf-8", "replace") + "\nTIMEOUT", -1
        (out / (name + ".log")).write_text(text, encoding="utf-8")
        fails = [l[:200] for l in text.splitlines() if l.startswith("FAIL")]
        summary[name] = {"rc": rc, "pass": sum(l.startswith("PASS") for l in text.splitlines()), "fail": fails}
        print(name, rc, summary[name]["pass"], "FAIL", len(fails))
    summary["_external_blocked"] = sorted(set(external))
    summary["_answered_locally"] = sorted(set(local_answers))
    (out / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("external blocked:", summary["_external_blocked"])
finally:
    stop.set()
    chrome.terminate()
    try:
        chrome.wait(10)
    except Exception:
        chrome.kill()
    shutil.rmtree(prof, ignore_errors=True)
    srv.shutdown()
