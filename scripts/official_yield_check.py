"""Identify OTC fund and read TPEx cash history before classifying missing yield.

No yield calculation, static-data update, Telegram or publication here. The public
API uses POST for read-only queries, exactly as the official ETF InfoHub page.
"""
import datetime as dt
import hashlib
import json
import math
import re
import ssl
import urllib.parse
import urllib.request

HOST = 'https://info.tpex.org.tw'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _date(value):
    if isinstance(value, str):
        roc = re.fullmatch(r'(\d{2,3})年(\d{1,2})月(\d{1,2})日', value)
        if roc:
            return dt.date(int(roc[1])+1911,int(roc[2]),int(roc[3]))
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}[./-]\d{2}[./-]\d{2}', value):
        raise ValueError('official date invalid')
    return dt.date.fromisoformat(value.replace('/', '-').replace('.', '-'))


def diagnose(code, name, today, request=None):
    """Two bounded read-only queries; errors never mean official no payments."""
    attempts = []
    def read(path, params):
        url = HOST + path
        try:
            if request is None:
                op = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
                req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), headers={'User-Agent':'ETF-yield-check/1.0', 'Content-Type':'application/x-www-form-urlencoded'}, method='POST')
                with op.open(req, timeout=6) as response:
                    if response.status != 200 or response.url != url:
                        raise ValueError('unexpected official response destination')
                    raw = response.read(2_000_001)
            else:
                raw = request(url, params)
            if not isinstance(raw, bytes) or not raw or len(raw) > 2_000_000:
                raise ValueError('official response size invalid')
            attempts.append({'url':url, 'params':params, 'sha256':hashlib.sha256(raw).hexdigest(), 'status':'received'})
            return json.loads(raw)
        except Exception:
            if not attempts or attempts[-1].get('url') != url:
                attempts.append({'url':url, 'params':params, 'status':'failed'})
            raise
    try:
        if not isinstance(code, str) or not re.fullmatch(r'\d{4,6}[A-Z]?', code) or not isinstance(name,str) or not name.strip() or type(today) is not dt.date:
            raise ValueError('fund identity or query date invalid')
        p = read('/api/etfProduct?lang=zh-tw&query='+code, {})
        same_name = lambda value: isinstance(value,str) and re.sub(r'\s+','',value)==re.sub(r'\s+','',name)
        if not isinstance(p, dict) or p.get('stockNo') != code or not same_name(p.get('shortName')) or not isinstance(p.get('name'), str) or '基金' not in p['name'] or not isinstance(p.get('issuer'), str) or not p['issuer'].strip():
            raise ValueError('official fund identity missing or mismatched')
        start = _date(p.get('listingDate'))
        if start > today or not isinstance(p.get('dividend'), list):
            raise ValueError('listing date or dividend summary invalid')
        rows = read('/api/etfExDiv', {'stkNo':code, 'startDate':start.strftime('%Y%m%d'), 'endDate':today.strftime('%Y%m%d'), 'lang':'zh-tw'})
        if not isinstance(rows, list):
            raise ValueError('official history is not a list')
        if not rows:
            if p['dividend']:
                raise ValueError('official summary and historical list conflict')
            return {'status':'no_record', 'detail':'櫃買同基金身分已核，自上市起官方配息清單與商品摘要均無紀錄；不等於永久不配息或已確認0%', 'attempts':attempts}
        positive, future, pending_amount, seen = [], [], [], set()
        for row in rows:
            if not isinstance(row, dict) or row.get('stockNo') != code or not same_name(row.get('stockName')):
                raise ValueError('historical dividend identity mismatch')
            date = _date(row.get('divDate'))
            amount = row.get('amount')
            if date < start or date in seen:
                raise ValueError('official dividend date invalid or duplicate')
            seen.add(date)
            # The official list can announce an ex-date before publishing its
            # cash amount. This is neither a failed query nor a zero payment.
            # Validate identity/date first; only the exact official empty string
            # gets this status. Missing, null and malformed values still fail.
            if amount == '' and isinstance(amount, str):
                pay_date = _date(row.get('inDate'))
                if pay_date < date or date > today + dt.timedelta(days=366):
                    raise ValueError('official pending payment date invalid')
                pending_amount.append({'date': date.isoformat(), 'pay_date': pay_date.isoformat()})
                continue
            if isinstance(amount,str) and re.fullmatch(r'\d+(?:\.\d+)?', amount):
                amount=float(amount)
            if isinstance(amount,bool) or not isinstance(amount,(int,float)) or not math.isfinite(amount) or amount < 0:
                raise ValueError('official dividend amount/date invalid or duplicate')
            if amount > 0:
                (future if date > today else positive).append({'date':date.isoformat(),'amount':amount})
        if positive:
            return {'status':'positive', 'detail':'櫃買已核到同基金正額配息，但目前殖利率未讀入，需查資料計算路徑', 'payments':positive, 'attempts':attempts}
        if future:
            return {'status':'future', 'detail':'櫃買已核到正額配息公告，除息日尚未到；不冒算已領配息殖利率', 'payments':future, 'attempts':attempts}
        if pending_amount:
            return {'status':'amount_pending', 'detail':'櫃買同基金已公告除息及發放日期，金額欄仍空白；保留未知、不填0、不當成來源故障，下輪續查',
                    'pending_announcements': pending_amount, 'attempts': attempts}
        return {'status':'zero_record', 'detail':'櫃買同基金官方歷史金額均為0；不據此填入已確認0%殖利率', 'attempts':attempts}
    except Exception as ex:
        return {'status':'error', 'detail':'櫃買查證未完成（'+type(ex).__name__+'），不是官方查無；保留資料，下輪續查', 'attempts':attempts}
