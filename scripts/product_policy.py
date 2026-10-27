"""scripts/product_policy.py — 商品收錄政策（PO 2026-10-10 永久規則）：
金流黑盒子 ETF 存股雷達不收錄任何代號尾碼 K 的商品，也不收錄任何 ETN。

兩層判斷，任一成立即排除：
  1. 代號尾碼 K（外幣計價受益憑證等）：依代號本身，不需外部資料。
  2. data/excluded_products.json 的稽核清單：ETN 與已核實的 K 商品，每筆記錄名稱、類型、原因、來源、確認日期；
     以及 PO 明確批准移除的一般 ETF（type PO_REMOVED，必填 approved_by="PO" 與 PO 指令出處 source）。
     這份清單是 Guard／Gate／Bootstrap／mis_fetcher／fetch_etf 共用的唯一「可以消失」依據（D-013／D-014）。
ETN 的「收錄」判斷不靠這份清單：產品池只收 TWSE ISIN「ETF」區段且 CFI 為 CE… 的列（fetch_etf.py），
ETN 區段、CFI 不符、類型不明一律不收；這份清單是第二道防線，擋 CURATED、舊快取、舊 _base.json 與遠端舊資料。
清單檔不存在或格式錯誤 → 丟例外（fail-closed），呼叫端不得當成「沒有排除商品」。
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = ROOT / "data" / "excluded_products.json"
_TYPES = ("K", "ETN", "PO_REMOVED")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


class PolicyError(ValueError):
    pass


def is_k(code):
    return isinstance(code, str) and code.endswith("K")


def validate_policy(obj):
    """excluded_products.json：{"policy": 文字, "products": {代號: {name, type K|ETN, reason, source, confirmed}}}。"""
    if not isinstance(obj, dict) or not isinstance(obj.get("policy"), str) or not obj["policy"].strip():
        raise PolicyError("excluded_products.json 缺 policy 說明")
    prods = obj.get("products")
    if not isinstance(prods, dict) or not prods:
        raise PolicyError("excluded_products.json products 為空")
    for code, r in prods.items():
        if not isinstance(code, str) or not re.fullmatch(r"[0-9A-Z]{4,7}", code):
            raise PolicyError(f"排除清單代號無效：{code!r}")
        if not isinstance(r, dict) or r.get("type") not in _TYPES:
            raise PolicyError(f"{code} type 必須是 {_TYPES}")
        for k in ("name", "reason", "source"):
            if not isinstance(r.get(k), str) or not r[k].strip():
                raise PolicyError(f"{code} 缺 {k}")
        if not (isinstance(r.get("confirmed"), str) and _DATE_RE.fullmatch(r["confirmed"])):
            raise PolicyError(f"{code} confirmed 日期無效：{r.get('confirmed')!r}")
        if r["type"] == "K" and not is_k(code):
            raise PolicyError(f"{code} 標為 K 但代號不是 K 尾碼")
        if r["type"] == "PO_REMOVED" and r.get("approved_by") != "PO":
            raise PolicyError(f"{code} PO_REMOVED 必須有 approved_by: \"PO\"（只有 PO 明確批准才能移除一般 ETF）")
        if "notify_pending" in r and not isinstance(r["notify_pending"], bool):
            raise PolicyError(f"{code} notify_pending 必須是 true／false")   # 選填：自動登錄後待通知 PO（D-014）
    return obj


def load_policy(path=None, text=None):
    """text：直接給清單內容（Publish Gate 用同一版本的 blob 驗證），不讀檔。"""
    p = Path(path) if path else POLICY_FILE
    try:
        obj = json.loads(text if text is not None else p.read_text(encoding="utf-8"))
    except Exception as e:
        raise PolicyError(f"讀不到排除清單 {p if text is None else '(指定版本)'}：{type(e).__name__}: {e}")
    return validate_policy(obj)


def listed_codes(path=None, text=None):
    return set(load_policy(path, text)["products"])


def exclusion_reason(code, listed):
    """排除原因字串；可收錄回傳 None。listed 為稽核清單代號集合（必填，避免呼叫端忘了載入）。"""
    if is_k(code):
        return "suffix-K"
    if code in listed:
        return "excluded-list"
    return None


def unapproved_removals(remote_etfs, local_etfs, listed=None):
    """MG-1：遠端正式資料有、候選沒有的代號中，不屬於 PO 排除政策（K 尾碼、excluded_products.json）的那些（排序後）。
    一般 ETF 的合法下市流程尚未實作，任何其他代號消失都不放行；清單讀不到 → PolicyError（fail-closed）。"""
    if listed is None:
        listed = listed_codes()
    gone = {e.get("code") for e in (remote_etfs or [])} - {e.get("code") for e in (local_etfs or [])}
    return sorted(c for c in gone if not exclusion_reason(c, listed))


def market_base_mismatch(market_etfs, base_etfs, listed=None):
    """MG-1：同一快照的 market.json 與 _base.json 商品集合必須一致（market＝base 扣掉 K／稽核清單）。
    回傳 (base 有但 market 沒有的一般 ETF, market 有但 base 沒有的代號)，皆排序；清單讀不到 → PolicyError。"""
    if listed is None:
        listed = listed_codes()
    m = {e.get("code") for e in (market_etfs or [])}
    b = {e.get("code") for e in (base_etfs or [])}
    return (sorted(c for c in b - m if not exclusion_reason(c, listed)), sorted(m - b))


def split_etfs(etfs, listed, evidence=None):
    """把 [{code…}] 分成 (保留, [(代號, 原因)])，順序不變。evidence（合格 ETF 類型證據代號集合）給了就一併要求有證據。"""
    keep, dropped = [], []
    for e in etfs:
        r = type_reason(e.get("code"), listed, evidence) if evidence is not None else exclusion_reason(e.get("code"), listed)
        if r:
            dropped.append((e.get("code"), r))
        else:
            keep.append(e)
    return keep, dropped


# ── 合格 ETF 類型證據（E-1 Phase 2）──
# 排除清單只能擋「已知」的 K／ETN；未登錄的 ETN（例：X 重現的 029998，CFI CMXXXU）只要混在政策前的
# 舊 _base.json 裡就會回流。所以核心池改為「正面表列」：每一檔都必須在合格 ETF 類型證據裡。
# 證據＝fetch_etf 在 ISIN 上市＋上櫃都成功時寫出的 data/etf_pool_cache.json 新格式列：
#   {code, name, is_otc, section: "ETF", cfi: "CE…", seen: "YYYY-MM-DD"}（seen＝該次 ISIN 確認日）
# 證據缺失、舊格式（沒有區段／CFI）、任一列損壞、與排除政策矛盾、或過期 → PolicyError（fail-closed），
# 呼叫端不得改用舊快取或舊 _base.json 放行，也不得把整個池當成空的照發。
#
# D-014（工作單06）：資格與行情分離。已在證據裡的一般 ETF 不因 seen 老舊而被擋（取消 30 天 stale）；
# seen 只在 ISIN 上市＋上櫃都成功且確實列出時更新（真實查核日），60 天未成功確認只觸發工程查核與通知
# （eligibility_status），不影響行情。沒有證據列的新代號仍然擋（no-etf-evidence）；未來日期仍然擋。
# 選填欄位：absent_since（完整查核未列出的第一天）、notified（"<狀態>:<日期>"，已成功送出的通知）。
EVIDENCE_FILE = ROOT / "data" / "etf_pool_cache.json"
ELIGIBILITY_CHECK_DAYS = 60
_NOTIFIED_RE = re.compile(r"[a-z_]+:\d{4}-\d{2}-\d{2}")


class Evidence(dict):
    """{代號: seen 日期}；as_of＝要寫出／發布的資料日期（type_reason 據此逐檔驗證時效）。"""
    as_of = None


def validate_evidence_rows(rows):
    """新格式證據列逐列驗證（不看排除清單）；任何一列有問題 → PolicyError。回傳 rows。"""
    import datetime
    if not isinstance(rows, list) or not rows:
        raise PolicyError("ETF 類型證據為空")
    seen_codes = set()
    for r in rows:
        if not isinstance(r, dict):
            raise PolicyError(f"ETF 類型證據是舊格式（沒有 ISIN 區段／CFI），無法確認商品類型：{str(r)[:40]}")
        code = r.get("code")
        if (not isinstance(code, str) or not re.fullmatch(r"[0-9A-Z]{4,7}", code) or r.get("section") != "ETF"
                or not isinstance(r.get("cfi"), str) or not r["cfi"].startswith("CE") or not isinstance(r.get("is_otc"), bool)
                or not isinstance(r.get("name"), str) or not r["name"]
                or not (isinstance(r.get("seen"), str) and _DATE_RE.fullmatch(r["seen"]))
                or ("absent_since" in r and not (isinstance(r["absent_since"], str) and _DATE_RE.fullmatch(r["absent_since"])))
                or ("notified" in r and not (isinstance(r["notified"], str) and _NOTIFIED_RE.fullmatch(r["notified"])))):
            raise PolicyError(f"ETF 類型證據列無效：{r!r}"[:160])
        if code in seen_codes:
            raise PolicyError(f"ETF 類型證據代號重複：{code}")
        seen_codes.add(code)
        for k in ("seen", "absent_since"):
            if k in r:
                try:
                    datetime.date.fromisoformat(r[k])
                except ValueError:
                    raise PolicyError(f"ETF 類型證據 {code} {k} 日期無效：{r[k]!r}")
    return rows


def load_etf_evidence(path=None, as_of=None, listed=None, text=None):
    """回傳 Evidence {合格 ETF 代號: seen}。格式任何一列有問題 → 整份無效（PolicyError）。
    as_of（datetime.date）：要寫出／發布的資料日期；逐檔只檢查未來日期（future-etf-evidence）。
    已在排除清單的代號：該列視為排除、不放進 Evidence（不讓整份證據失效；排除仍由 exclusion_reason 生效）。
    text：直接給證據內容（Publish Gate 用同一版本的 blob 驗證），不讀檔。"""
    import datetime
    p = Path(path) if path else EVIDENCE_FILE
    try:
        rows = json.loads(text if text is not None else p.read_text(encoding="utf-8"))
    except Exception as e:
        raise PolicyError(f"讀不到 ETF 類型證據 {p.name if text is None else '(指定版本)'}：{type(e).__name__}: {e}")
    validate_evidence_rows(rows)
    if listed is None:
        listed = listed_codes()
    codes = Evidence()
    codes.as_of = as_of
    for r in rows:
        if exclusion_reason(r["code"], listed):
            continue
        codes[r["code"]] = datetime.date.fromisoformat(r["seen"])
    return codes


def type_reason(code, listed, evidence):
    """排除原因（K／稽核清單）；沒有證據 → 'no-etf-evidence'；
    該檔證據日期晚於資料日 1 天以上 → 'future-etf-evidence'；合格回傳 None。
    D-014：證據 seen 老舊不再阻擋（資格與行情分離；60 天查核見 eligibility_status）。"""
    r = exclusion_reason(code, listed)
    if r:
        return r
    if code not in evidence:
        return "no-etf-evidence"
    as_of = getattr(evidence, "as_of", None)
    seen = evidence[code] if isinstance(evidence, dict) else None
    if as_of is not None and seen is not None and (seen - as_of).days > 1:
        return "future-etf-evidence"
    return None


def eligibility_status(row, today):
    """'ok'＝距最後一次成功官方確認（seen）未滿 60 天；'overdue'＝已滿 60 天。只供查核／通知用，不影響行情。"""
    import datetime
    seen = datetime.date.fromisoformat(row["seen"])
    return "overdue" if (today - seen).days >= ELIGIBILITY_CHECK_DAYS else "ok"


# ── 資料池成員（D-014／PLAN_ETF_ELIGIBILITY Rev.2 §2.3、§2.4、§4）──
def read_evidence_file(path=None):
    """讀證據檔：不存在或舊格式（[代號, 名稱, …]）→ None（沒有可用的既有資格證據）；
    新格式但任一列無效 → PolicyError（fail-closed，不當成沒有證據而重新初始化）。"""
    p = Path(path) if path else EVIDENCE_FILE
    if not p.exists():
        return None
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise PolicyError(f"讀不到 ETF 類型證據 {p.name}：{type(e).__name__}: {e}")
    if isinstance(rows, list) and rows and all(isinstance(r, list) for r in rows):
        return None
    return validate_evidence_rows(rows)


def plan_pool(prev, today_etf, today_etn, listed, today):
    """決定本次資料池與新證據。
    prev：上一版證據列（read_evidence_file；None＝沒有可用證據）。
    today_etf：{is_otc(bool): [(code, name, cfi)] 或 None（該市場別 ISIN 失敗）}。
    today_etn：{is_otc: {code: cfi}}（ISIN ETN 區段，CFI CM…；失敗的市場別沒有）。
    listed：排除清單代號；today：'YYYY-MM-DD'。
    回傳 dict：full（兩市場都成功）、pool [(code, name, is_otc)]、evidence（要寫出的新證據列或 None＝不寫）、
    deferred（單邊成功時暫緩的新代號）、etn_new {code: (name, cfi, is_otc)}（完整查核發現改列 ETN 的既有代號）、
    absent（本次完整查核未列出、保留的代號）。"""
    full = today_etf.get(False) is not None and today_etf.get(True) is not None
    out = {"full": full, "pool": [], "evidence": None, "deferred": [], "etn_new": {}, "absent": []}
    keep_prev = [dict(r) for r in (prev or []) if not exclusion_reason(r["code"], listed)]
    if not full:
        if prev is None:
            return None                     # 沒有可用證據又不完整：交給呼叫端既有 fail-closed 路徑
        out["pool"] = [(r["code"], r["name"], r["is_otc"]) for r in keep_prev]
        known = {r["code"] for r in keep_prev}
        out["deferred"] = sorted({c for rows in today_etf.values() if rows for c, _, _ in rows
                                  if c not in known and not exclusion_reason(c, listed)})
        return out
    todays = {}
    for otc in (False, True):
        for code, name, cfi in today_etf[otc]:
            if code not in todays and not exclusion_reason(code, listed):
                todays[code] = {"code": code, "name": name, "is_otc": otc, "section": "ETF", "cfi": cfi, "seen": today}
    etn = {c: (otc, cfi) for otc in (False, True) for c, cfi in (today_etn.get(otc) or {}).items()}
    new_rows = []
    for r in keep_prev:
        c = r["code"]
        if c in todays:
            new_rows.append(todays.pop(c))              # 官方確實列出：seen＝今天；缺席／通知紀錄清除
        elif c in etn and str(etn[c][1]).startswith("CM"):
            out["etn_new"][c] = (r["name"], etn[c][1], etn[c][0])     # 官方 ETN 區段＋CM CFI：可信 ETN 變更
        else:
            r.setdefault("absent_since", today)         # 未知／不在任一區段：保留舊資格與 seen，不推定下市
            out["absent"].append(c)
            new_rows.append(r)
    new_rows.extend(todays.values())                    # 完整查核新出現的合格 ETF
    out["evidence"] = new_rows
    out["pool"] = [(r["code"], r["name"], r["is_otc"]) for r in new_rows]
    return out


def evidence_shrink(prev, new, listed):
    """新證據比上一版少了哪些未排除代號（只能增加，或因排除清單拿掉）。"""
    if not prev:
        return []
    have = {r["code"] for r in new}
    return sorted(r["code"] for r in prev if r["code"] not in have and not exclusion_reason(r["code"], listed))
