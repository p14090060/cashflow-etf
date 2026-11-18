"""Current-run active ETF coverage, using existing ISIN responses, no network.

The runtime inventory is monitoring evidence, never an eligibility/data source.
Unimplemented sources stay visible in a work queue; they are not 'official no data'.
"""
import ast,datetime,hashlib,json,os,re,tempfile,time
from pathlib import Path
from html import unescape

FORMAT='active-holdings-universe/v1'

def is_active_bond(code):
    # Security-code suffix identifies active bonds; scope only, never eligibility.
    return isinstance(code,str) and re.fullmatch(r'\d{5}D',code) is not None

STATE_KEYS=('active_gap_rounds','active_gap_first','active_gap_last','active_gap_run','active_gap_notified')
# R1 F1：完整性監控本身失效（名單縮水、單市場、舊輸出…）的受控追蹤。單一鍵 'monitor'，沿 daily_state {鍵: 數值} 契約。
INTEGRITY_KEYS=('active_integrity_rounds','active_integrity_first','active_integrity_last','active_integrity_run','active_integrity_reason','active_integrity_notified')
INTEGRITY_REASONS={r:i for i,r in enumerate(('本輪官方完整名單未取得／識別不符','上市／上櫃名單未同輪完成','官方名單逾期／格式不符','官方商品列身分不符','官方上市日無效','官方兩市場代號衝突','官方主動名單為空或少了已追蹤代號，不認完整','持股輸出未取得','持股輸出不是本輪新結果'),1)}
# R1 F2：已安全採用的動態安聯成員（代號 → 最後一次本輪核身＋持股有效＋正式輸出的時間）。只是路由提示，不是身分或資格證據。
DYNAMIC_KEY='active_dynamic_allianz'
STATUS_CODES={name:i for i,name in enumerate(('covered','not_listed','missing_adapter','missing_output','fetch_failed','source_conflict','non_equity','baseline','chart','quantity_list','unchanged','missing_display_rows'),1)}

def run_key():
    if os.environ.get('GITHUB_RUN_ID'):
        return os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
    return os.environ.get('ETF_RUN_ID') or None

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,allow_nan=False)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def capture_market(path,key,mode,section,now=None):
    """Capture active CE ETF rows before trading-pool filtering, both markets."""
    now=time.time() if now is None else now
    if not key or mode not in (2,4) or not isinstance(section,str) or not section:
        raise ValueError('coverage source/run unavailable')
    rows={};etf_count=0
    for raw in re.split(r'<tr\b[^>]*>',section,flags=re.I):
        cells=re.findall(r'<td\b[^>]*>(.*?)</td>',raw,re.I|re.S)
        cells=[unescape(re.sub('<[^>]+>','',c)).strip() for c in cells]
        if len(cells)<6:continue
        pair=re.fullmatch(r'(\d{4,6}[A-Z]?)\s+(.+)',cells[0])
        if not pair or not re.fullmatch(r'CE[A-Z]{4}',cells[5]):continue
        etf_count+=1;code,name=pair.groups()
        if not name.startswith('主動'):continue
        day=datetime.date.fromisoformat(cells[2].replace('/','-')).isoformat()
        item={'code':code,'name':name,'listing_date':day,'cfi':cells[5]}
        if code in rows:raise ValueError('duplicate active ETF source row')
        rows[code]=item
    if not etf_count:raise ValueError('ETF source rows unavailable')
    try:doc=json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):doc={}
    if doc.get('format')!=FORMAT or doc.get('run')!=key:
        doc={'format':FORMAT,'run':key,'started_at':now,'markets':{}}
    doc['markets'][str(mode)]={'checked_at':now,'source_sha256':hashlib.sha256(section.encode()).hexdigest(),'etf_count':etf_count,'rows':rows}
    atomic(path,doc);return doc

def registrations(source):
    """Read literal source registries without importing/executing the writer."""
    found={}
    for node in ast.parse(source).body:
        if not isinstance(node,ast.Assign) or len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name):continue
        name=node.targets[0].id
        if not name.endswith('_FUNDS'):continue
        try:value=ast.literal_eval(node.value)
        except (ValueError,TypeError):continue
        if isinstance(value,dict):
            for code in value:
                if isinstance(code,str) and re.fullmatch(r'\d{4,6}[A-Z]?',code):found[code]=name
    return found

def dynamic_members(root):
    """讀回已持久的動態成員代號（只作排程提示）；壞資料 → 空集合（fail closed：不更新，不當身分）。"""
    try:d=json.loads((Path(root)/'data/daily_state.json').read_text(encoding='utf-8')).get(DYNAMIC_KEY)
    except (OSError,ValueError,AttributeError):return set()
    if not isinstance(d,dict):return set()
    return {c for c,v in d.items() if isinstance(c,str) and re.fullmatch(r'\d{4,6}[A-Z]?',c) and isinstance(v,(int,float)) and not isinstance(v,bool)}

def current_rows(root,prefix,*,now=None):
    """本輪、兩市場、2 小時內官方名單中（已上市、CE、名稱前綴相符）的列；名單不可信 → None。"""
    now=time.time() if now is None else now
    try:doc=json.loads((Path(root)/'logs/active_universe.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return None
    if not run_key() or not isinstance(doc,dict) or doc.get('format')!=FORMAT or doc.get('run')!=run_key() or not isinstance(doc.get('markets'),dict) or set(doc['markets'])!={'2','4'}:return None
    today=datetime.datetime.fromtimestamp(now,datetime.timezone(datetime.timedelta(hours=8))).date()
    rows={}
    for market in doc['markets'].values():
        if not isinstance(market,dict) or not isinstance(market.get('rows'),dict) or not isinstance(market.get('checked_at'),(int,float)) or not 0<=now-market['checked_at']<=7200:return None
        for code,r in market['rows'].items():
            if code in rows:return None
            rows[code]=r
    out={}
    for code,r in sorted(rows.items()):
        if not isinstance(r,dict) or r.get('code')!=code or not re.fullmatch(r'\d{4,6}[A-Z]?',code) or not str(r.get('name','')).startswith(prefix):continue
        try:listing=datetime.date.fromisoformat(r['listing_date'])
        except (ValueError,TypeError,KeyError):continue
        if listing<=today and re.fullmatch(r'CE[A-Z]{4}',str(r.get('cfi',''))):out[code]=r
    return out

def discovery_candidates(root,prefix,known,*,now=None):
    """Only current, two-market official inventory may drive a known adapter."""
    rows=current_rows(root,prefix,now=now)
    if rows is None:return []
    out=[r for code,r in rows.items() if code not in known and not is_active_bond(code)]
    try:last=json.loads((Path(root)/'data/daily_state.json').read_text(encoding='utf-8')).get('active_discovery_last',{})
    except (OSError,ValueError,AttributeError):last={}
    return sorted(out,key=lambda r:(last.get(r['code'],0),r['code']))

def evaluate(inventory,flow,writer_source,state,*,key,now,today):
    """逐檔缺口＋R1 F1 完整性監控失效追蹤（不放行縮水名單、不刪代號、不猜退市）。"""
    result=_evaluate(inventory,flow,writer_source,state,key=key,now=now,today=today)
    result['integrity_due']=False
    if result['complete']:
        for sk in INTEGRITY_KEYS:state.pop(sk,None)          # 恢復完整：清除整段故障狀態（含冷卻）
        return result
    if not key:return result                                   # 無本輪識別：無法跨 run 去重，不計輪
    for sk in INTEGRITY_KEYS:
        if not isinstance(state.get(sk),dict):state[sk]={}
    rid=int.from_bytes(hashlib.sha256(key.encode()).digest()[:6],'big')
    s={sk:state[sk] for sk in INTEGRITY_KEYS}
    if s['active_integrity_run'].get('monitor')!=rid:
        s['active_integrity_rounds']['monitor']=s['active_integrity_rounds'].get('monitor',0)+1
        s['active_integrity_first'].setdefault('monitor',now)
        s['active_integrity_last']['monitor']=now;s['active_integrity_run']['monitor']=rid
    s['active_integrity_reason']['monitor']=INTEGRITY_REASONS.get(result['reason'],0)
    if s['active_integrity_rounds']['monitor']>=3 and now-s['active_integrity_first']['monitor']>=86400 and now-s['active_integrity_notified'].get('monitor',0)>=14*86400:
        result['integrity_due']=True
    for sk in INTEGRITY_KEYS:
        if not state[sk]:state.pop(sk)
    return result

def _evaluate(inventory,flow,writer_source,state,*,key,now,today):
    """No extra lookups, no first-miss TG; current-run gap dedup + delivered ACK."""
    result={'complete':False,'reason':None,'rows':{},'due':[],'counts':{}}
    if not key or not isinstance(inventory,dict) or inventory.get('format')!=FORMAT or inventory.get('run')!=key:
        result['reason']='本輪官方完整名單未取得／識別不符';return result
    markets=inventory.get('markets')
    if not isinstance(markets,dict) or set(markets)!={'2','4'}:
        result['reason']='上市／上櫃名單未同輪完成';return result
    entries={}
    for market in markets.values():
        if not isinstance(market,dict) or not isinstance(market.get('checked_at'),(int,float)) or isinstance(market['checked_at'],bool) or not 0<=now-market['checked_at']<=7200 or not isinstance(market.get('rows'),dict):
            result['reason']='官方名單逾期／格式不符';return result
        for code,row in market['rows'].items():
            if not isinstance(row,dict) or row.get('code')!=code or not isinstance(row.get('name'),str) or not row['name'].startswith('主動') or not re.fullmatch(r'CE[A-Z]{4}',str(row.get('cfi',''))):
                result['reason']='官方商品列身分不符';return result
            try:datetime.date.fromisoformat(row['listing_date'])
            except (ValueError,TypeError,KeyError):result['reason']='官方上市日無效';return result
            if code in entries:result['reason']='官方兩市場代號衝突';return result
            entries[code]=row
    if not entries or {c for c in (state.get('active_coverage_status') or {}) if not is_active_bond(c)}-set(entries):
        result['reason']='官方主動名單為空或少了已追蹤代號，不認完整';return result
    if not isinstance(flow,dict) or not isinstance(flow.get('etfs'),dict):
        result['reason']='持股輸出未取得';return result
    try:
        stamp=datetime.datetime.strptime(flow['updated'],'%Y-%m-%d %H:%M').replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp()
        start=float(inventory['started_at'])
        if not 0<=now-stamp<=7200 or stamp<start-60:raise ValueError()
    except (KeyError,TypeError,ValueError):
        result['reason']='持股輸出不是本輪新結果';return result
    # PO 2026-11-19: active bonds stay in the universe, outside holdings-change scope.
    # Migrate only after complete, fresh inventory/output checks pass.
    entries={c:r for c,r in entries.items() if not is_active_bond(c)}
    for sk in STATE_KEYS+('active_coverage_status','active_coverage_listing','active_coverage_checked'):
        values=state.get(sk)
        if isinstance(values,dict):
            for c in list(values):
                if is_active_bond(c):values.pop(c)
    registered=registrations(writer_source)
    dyn=state.get(DYNAMIC_KEY)
    if isinstance(dyn,dict):registered.update({c:DYNAMIC_KEY for c in dyn if isinstance(c,str)})
    rid=int.from_bytes(hashlib.sha256(key.encode()).digest()[:6],'big')
    for sk in STATE_KEYS:state.setdefault(sk,{})
    for code,row in entries.items():
        e=flow['etfs'].get(code);status='covered'
        if row['listing_date']>today.isoformat():status='not_listed'
        elif not isinstance(e,dict):status='missing_output' if code in registered else 'missing_adapter'
        elif e.get('fetched') is not True:status='fetch_failed'
        elif e.get('anomaly'):status='source_conflict'
        elif e.get('non_equity_changes') or e.get('non_equity_status'):status='non_equity'
        elif e.get('reason')=='no_basis':status='baseline'
        elif e.get('flow'):status='chart'
        elif e.get('no_price'):status='quantity_list'
        elif not e.get('changed'):status='unchanged'
        else:status='missing_display_rows'
        item=dict(row,status=status,registry=registered.get(code));result['rows'][code]=item
        gap=status in ('missing_adapter','missing_output','missing_display_rows')
        if not gap:
            if status in ('covered','non_equity','baseline','chart','quantity_list','unchanged'):
                for sk in STATE_KEYS:state[sk].pop(code,None)
            continue
        if state['active_gap_run'].get(code)!=rid:
            state['active_gap_rounds'][code]=state['active_gap_rounds'].get(code,0)+1
            state['active_gap_first'].setdefault(code,now)
            state['active_gap_last'][code]=now;state['active_gap_run'][code]=rid
        if state['active_gap_rounds'][code]>=3 and now-state['active_gap_first'][code]>=86400 and now-state['active_gap_notified'].get(code,0)>=14*86400:
            result['due'].append(code)
    result['complete']=True
    result['counts']={s:sum(r['status']==s for r in result['rows'].values()) for s in sorted({r['status'] for r in result['rows'].values()})}
    state['active_coverage_status']={code:STATUS_CODES[row['status']] for code,row in result['rows'].items()}
    state['active_coverage_listing']={code:int(row['listing_date'].replace('-','')) for code,row in result['rows'].items()}
    state['active_coverage_checked']={code:now for code in result['rows']}
    return result

def check(root,state,now=None,today=None):
    root=Path(root);now=time.time() if now is None else now;today=today or datetime.datetime.fromtimestamp(now,datetime.timezone(datetime.timedelta(hours=8))).date()
    def load(p):
        try:return json.loads(p.read_text(encoding='utf-8'))
        except (OSError,ValueError):return None
    discovery=load(root/'logs/active_discovery_allianz.json')
    if isinstance(discovery,dict) and discovery.get('run')==run_key() and isinstance(discovery.get('checked_at'),(int,float)) and 0<=now-discovery['checked_at']<=7200:
        last=state.setdefault('active_discovery_last',{})
        for code in discovery.get('attempted') or []:
            if isinstance(code,str) and re.fullmatch(r'\d{4,6}[A-Z]?',code):last[code]=discovery['checked_at']
    flow=load(root/'data/active_flow.json')
    result=evaluate(load(root/'logs/active_universe.json'),flow,(root/'scripts/fetch_active_etf.py').read_text(encoding='utf-8'),state,key=run_key(),now=now,today=today)
    # R1 F2：只在本輪完整、探索報告同輪新鮮、官方名單含該碼、且正式輸出本輪 fetched:true 時，記住動態成員
    if result['complete'] and isinstance(discovery,dict) and discovery.get('run')==run_key() and isinstance(discovery.get('checked_at'),(int,float)) and 0<=now-discovery['checked_at']<=7200:
        ok=[c for k in ("adopted","updated") if isinstance(discovery.get(k),list) for c in discovery[k]]
        members=state.get(DYNAMIC_KEY) if isinstance(state.get(DYNAMIC_KEY),dict) else {}
        for code in ok:
            row=result['rows'].get(code) if isinstance(code,str) else None
            e=(flow or {}).get('etfs',{}).get(code) if isinstance(code,str) else None
            if row and str(row.get('name','')).startswith('主動安聯') and isinstance(e,dict) and e.get('fetched') is True:
                members[code]=discovery['checked_at']
        if members:state[DYNAMIC_KEY]=members
    atomic(root/'logs/active_coverage.json',result)
    print('[ACTIVE-COVERAGE] '+json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False))
    queue=[r for r in result['rows'].values() if r['status'] in ('missing_adapter','missing_output','missing_display_rows','fetch_failed','source_conflict','not_listed')]
    if queue:print('[ACTIVE-COVERAGE-QUEUE] '+json.dumps(queue,ensure_ascii=False))
    lines=[]
    if result.get('integrity_due'):
        lines+=['🔧 主動ETF完整性監控名單不完整（已連續至少3輪、跨24小時；不是官方查無、不是宣告下市，逐檔缺口檢查暫停中，工程端需查明）',
                '• 原因：%s' % (result['reason'] or '未知')]
    if result['due']:
        lines=['🔧 主動ETF自動接線缺口（已核官方名單及來源設定，非官方查無；工程端仍需補接）']
        lines+=['• %s %s：%s' % (c,result['rows'][c]['name'],{'missing_adapter':'官方已上市，持股來源尚未接入','missing_output':'來源已登錄但本輪沒有持股輸出','missing_display_rows':'有異動數量但沒有可顯示明細'}[result['rows'][c]['status']]) for c in result['due'][:15]]
    return result,lines
