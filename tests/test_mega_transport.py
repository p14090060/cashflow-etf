import io
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mega_transport import MegaOpener

URL = 'https://www.megafunds.com.tw/MEGA/etf/trade_pcf.aspx'


class Primary:
    addheaders = [('User-Agent', 'old-agent'), ('Cookie', 'old-cookie')]

    def __init__(self, code=403):
        self.code = code
        self.calls = []

    def open(self, target, timeout):
        self.calls.append(target)
        if self.code:
            raise urllib.error.HTTPError(URL, self.code, 'blocked', {}, io.BytesIO(b'blocked'))
        return io.BytesIO(b'primary')


class Browser:
    def __init__(self, status=200, body=b'official'):
        self.status, self.body = status, body
        self.calls = []

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(status_code=self.status, content=self.body)

    def close(self):
        pass


class TransportTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.socket.connect', side_effect=AssertionError('offline test attempted network'))
        guard.start()
        self.addCleanup(guard.stop)

    def test_primary_unchanged(self):
        with patch('curl_cffi.requests.Session') as factory:
            self.assertEqual(MegaOpener(Primary(0), {'23'}).open(URL).read(), b'primary')
            factory.assert_not_called()

    def test_get_then_post_same_bounded_session(self):
        browser = Browser()
        primary = Primary()
        with patch('curl_cffi.requests.Session', return_value=browser) as factory:
            op = MegaOpener(primary, {'23'})
            self.assertEqual(op.open(URL).read(), b'official')
            req = urllib.request.Request(URL, data=b'fund_id=23', headers={'Referer': URL})
            self.assertEqual(op.open(req).read(), b'official')
            with self.assertRaises(RuntimeError):
                op.open(URL)
            factory.assert_called_once_with(impersonate='chrome', trust_env=False)
            self.assertEqual(len(primary.calls), 1)
            self.assertEqual(len(browser.calls), 2)
            self.assertEqual(browser.calls[1][0], ('POST', URL))
            self.assertEqual(browser.calls[1][1]['data'], b'fund_id=23')
            for _, options in browser.calls:
                self.assertFalse(options['allow_redirects'])
                self.assertTrue(options['verify'])
                self.assertEqual(options['timeout'], 12)
                self.assertFalse({'cookie', 'user-agent'} & {k.lower() for k in options['headers']})

    def test_other_failures_not_retried(self):
        with patch('curl_cffi.requests.Session') as factory:
            for code, target in [(404, URL), (403, urllib.request.Request(URL, data=b'x=1'))]:
                with self.subTest(code=code, target=target):
                    with self.assertRaises(urllib.error.HTTPError):
                        MegaOpener(Primary(code), {'23'}).open(target)
            factory.assert_not_called()

    def test_browser_failure_never_returns_success(self):
        for status in [301, 302, 307, 403, 500]:
            with self.subTest(status=status), patch('curl_cffi.requests.Session', return_value=Browser(status)):
                with self.assertRaises(urllib.error.HTTPError):
                    MegaOpener(Primary(), {'23'}).open(URL)
        browser = Browser()
        browser.request = lambda *a, **k: (_ for _ in ()).throw(TimeoutError())
        with patch('curl_cffi.requests.Session', return_value=browser):
            with self.assertRaises(TimeoutError):
                MegaOpener(Primary(), {'23'}).open(URL)

    def test_reject_unregistered_routes_before_transport(self):
        urls = [URL.replace('https:', 'http:'), URL.replace('www.', 'fake.'), URL + '#x',
                URL + '?x=1', URL.replace('trade_pcf', 'other'),
                URL.replace('www.megafunds.com.tw', 'user@www.megafunds.com.tw'),
                URL.replace('.tw/', '.tw:443/'),
                'https://www.megafunds.com.tw/MEGA/etf/etf_product.aspx?id=99',
                'https://www.megafunds.com.tw/MEGA/etf/etf_product.aspx?id=23&id=23']
        primary = Primary()
        with patch('curl_cffi.requests.Session') as factory:
            for url in urls:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    MegaOpener(primary, {'23'}).open(url)
            for method in ['PUT', 'DELETE']:
                with self.assertRaises(ValueError):
                    MegaOpener(primary, {'23'}).open(urllib.request.Request(URL, method=method))
            self.assertEqual(primary.calls, [])
            factory.assert_not_called()

    def test_credentials_rejected(self):
        primary = Primary()
        for key in ['Authorization', 'Proxy-Authorization']:
            with self.assertRaises(ValueError):
                MegaOpener(primary, {'23'}).open(urllib.request.Request(URL, headers={key: 'secret'}))
        self.assertEqual(primary.calls, [])

    def test_large_body_rejected(self):
        with patch('curl_cffi.requests.Session', return_value=Browser(body=b'x' * 2000001)):
            with self.assertRaises(ValueError):
                MegaOpener(Primary(), {'23'}).open(URL)

    def test_saved_official_body_identical(self):
        raw = (Path(__file__).parent / 'fixtures' / 'mega_pcf_00996A_20261007.html').read_bytes()
        primary = Primary(0)
        primary.open = lambda *a, **k: io.BytesIO(raw)
        expected = MegaOpener(primary, {'23'}).open(URL).read()
        with patch('curl_cffi.requests.Session', return_value=Browser(body=raw)):
            actual = MegaOpener(Primary(), {'23'}).open(URL).read()
        self.assertEqual(actual, expected)

    def test_real_adapter_saved_pcf_recovery(self):
        import datetime
        import fetch_active_etf as active
        raw = (Path(__file__).parent / 'fixtures' / 'mega_pcf_00996A_20261007.html').read_bytes()
        def run(blocked):
            primary = Primary(403 if blocked else 0)
            if not blocked:
                primary.open = lambda *a, **k: io.BytesIO(raw)
            browser = Browser(body=raw)
            with patch.object(active, '_opener', return_value=primary), \
                    patch.object(active.time, 'sleep'), \
                    patch.object(active.mega_feed, 'next_trading_day', return_value=datetime.date(2026, 10, 8)), \
                    patch.object(active.mega_feed, 'latest_valid', return_value=(None, None)), \
                    patch('curl_cffi.requests.Session', return_value=browser):
                result = active.fetch_mega(datetime.date(2026, 10, 7), specific=True)
            return result, active.MEGA_LAST_SOURCE.copy(), browser
        expected, source, unused = run(False)
        actual, recovered_source, browser = run(True)
        self.assertTrue(expected['00996A']['holdings'])
        self.assertEqual(expected['00996A']['data_date'], '2026-10-07')
        self.assertEqual(actual, expected)
        self.assertEqual(source, recovered_source)
        self.assertEqual(source['00996A'], 'mega_trade_pcf')
        self.assertEqual(len(browser.calls), 2)


if __name__ == '__main__':
    unittest.main()
