"""One bounded browser-compatible transport fallback for public Mega PCF pages.

No proxy, credentials, alternate host, retry loop, parsing, or data publication.
"""
import io
import urllib.error
import urllib.parse
import urllib.request


class MegaOpener:
    def __init__(self, primary, fund_ids):
        self.primary = primary
        self.addheaders = list(primary.addheaders)
        self.fund_ids = set(fund_ids)
        self.browser = None
        self.browser_calls = 0

    def _validate(self, url, method):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "www.megafunds.com.tw" or
                parsed.fragment or method not in ("GET", "POST")):
            raise ValueError("Mega transport only accepts existing public official routes")
        if parsed.path == "/MEGA/etf/trade_pcf.aspx" and not parsed.query:
            return
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if (method == "GET" and parsed.path == "/MEGA/etf/etf_product.aspx" and
                set(query) == {"id"} and len(query["id"]) == 1 and query["id"][0] in self.fund_ids):
            return
        raise ValueError("Unexpected Mega route or fund identifier")

    def open(self, target, timeout=30):
        request = target if isinstance(target, urllib.request.Request) else urllib.request.Request(target)
        url, method = request.full_url, request.get_method()
        self._validate(url, method)
        headers = self.addheaders + list(request.header_items())
        if any(name.lower() in ("authorization", "proxy-authorization") for name, _ in headers):
            raise ValueError("Public Mega requests must not carry credentials")
        if self.browser is None:
            self.primary.addheaders = self.addheaders
            try:
                return self.primary.open(target, timeout=timeout)
            except urllib.error.HTTPError as error:
                # Only the observed initial GET/403 condition is retried. Do not
                # replay a POST with state from a different transport/session.
                if error.code != 403 or method != "GET":
                    raise
                try:
                    from curl_cffi import requests
                    self.browser = requests.Session(impersonate="chrome", trust_env=False)
                except (ImportError, TypeError):
                    raise error
                error.close()
                print("[Mega] initial GET HTTP403; trying same official source with browser-compatible transport")
        if self.browser_calls >= 2:
            raise RuntimeError("Mega fallback request budget exhausted")
        self.browser_calls += 1
        # The new session handles its own public cookies and browser headers.
        # Do not forward the old session's cookies, credentials or User-Agent.
        safe_headers = {name: value for name, value in headers
                        if name.lower() in ("referer", "content-type")}
        response = self.browser.request(method, url, data=request.data, headers=safe_headers,
                                        timeout=min(timeout, 12), allow_redirects=False, verify=True)
        body = response.content
        if response.status_code != 200:
            raise urllib.error.HTTPError(url, response.status_code, "Mega fallback unsuccessful", {}, io.BytesIO(body))
        if len(body) > 2_000_000:
            raise ValueError("Mega public response exceeds size limit")
        return io.BytesIO(body)

    def close(self):
        if self.browser is not None:
            self.browser.close()
            self.browser = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
