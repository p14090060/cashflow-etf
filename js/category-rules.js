// category-rules.js — Phase 3 分類規則（純函式，無 DOM）
// 依 PHASE3_PLAN.md §3.1 的優先順序；規則只在這個檔案，UI 不寫死任何 ETF 代碼。
// 單一歸屬：依序判斷，命中即停止。
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"。

// 資料夾顯示順序（PHASE3_PLAN §4.1）
const CAT_DEF = [
  { key: 'mcap',     label: '市值型',       short: '市值', sub: '主要追蹤大型、中型或特定市值範圍指數的 ETF' },
  { key: 'div',      label: '高股息',       short: '高股息', sub: '主要以高股息策略為特色的 ETF' },
  { key: 'active',   label: '主動式',       short: '主動', sub: '由經理人主動操作持股的 ETF' },
  { key: 'tech',     label: '科技／半導體', short: '科技', sub: '主要投資科技與半導體產業的 ETF' },
  { key: 'overseas', label: '海外／區域',   short: '海外', sub: '主要投資海外市場或特定地區的 ETF' },
  { key: 'theme',    label: '主題型',       short: '主題', sub: '聚焦特定主題或產業（如金融、工業、數位支付）的 ETF' },
  { key: 'bond',     label: '債券',         short: '債券', sub: '主要投資債券的 ETF' },
  { key: 'other',    label: '其他',         short: '其他', sub: '不屬於前述分類，或以 ESG 等篩選策略為主、期貨型等的 ETF' }
];

// 關鍵字（名稱包含即命中；英文不分大小寫）
const CAT_KW = {
  overseas: ['美國', '日本', '日經', '日股', '東證', '印度', '歐洲', '中國', '越南', '恒生', '韓', '北美',
             '標普', 'S&P', 'NASDAQ', '納斯達克', '那斯達克', '道瓊', '費城', '上証', '上證', '滬深',
             '深証', '深100', '中証500', 'MSCI A股', '全球', '亞太', '海外', '新興', '世界', 'FANG', 'MAG7', 'US'],
  tech:     ['科技', '半導體', '電子', '晶圓', 'IC設計', 'AI', 'PCB', '資安', '5G', '通訊'],
  div:      ['高股息', '高息', '股利', '優息', '高填息'],
  // 主題：包含 ESG 以外的明確產品特色（低碳、淨零、綠能、綠色電力…）。ESG 本身不算主題。
  theme:    ['低碳', '淨零', '綠能', '綠色', '太空', '稀土', '元宇宙', '機器人', '生技', '基因', '電動車',
             '智能車', '未來車', '車', '潔淨', '能源', '電池', '儲能', '電力', '數據', '算力', '航運', '航太',
             '防衛', '數位', '金融', '工業'],
  mcap:     ['0050', '50', '100', '中型', '中小', '加權', '藍籌', '領袖', '龍頭', 'MSCI台灣', '台灣50', '臺灣50'],
  // 策略型（ESG、公司治理）：只有在沒有更明確定位時才歸其他
  strategy: ['ESG', '公司治理']
};

function _catHas(name, kws) {
  const N = String(name).toUpperCase();
  return kws.some(k => N.indexOf(k.toUpperCase()) >= 0);
}

// 回傳分類 key。優先順序與 PHASE3_PLAN §3.1 一致。
function catClassify(e) {
  const code = String(e.code || '').toUpperCase();
  const name = String(e.name || '');
  if (/[BD]$/.test(code)) return 'bond';                                  // 1 債券
  if (/A$/.test(code) || name.indexOf('主動') >= 0) return 'active';      // 2 主動式
  if (name.indexOf('期') === 0) return 'other';                            // 3 期貨型
  if (_catHas(name, CAT_KW.overseas)) return 'overseas';                  // 4 海外／區域
  if (_catHas(name, CAT_KW.tech)) return 'tech';                          // 5 科技／半導體
  if (_catHas(name, CAT_KW.div)) return 'div';                            // 6 高股息
  if (_catHas(name, CAT_KW.theme)) return 'theme';                        // 7 主題型
  if (_catHas(name, CAT_KW.mcap)) return 'mcap';                          // 8 市值型
  if (_catHas(name, CAT_KW.strategy)) return 'other';                     // 9 策略型 → 其他
  if (e.div_category === '高股息') return 'div';                          // 10 人工標籤備援（只在前面都未命中時）
  return 'other';                                                         // 11 未命中
}

// 依分類分組；每個分類都有陣列（即使空）
function catGroup(list) {
  const g = {};
  CAT_DEF.forEach(d => { g[d.key] = []; });
  (list || []).forEach(e => { g[catClassify(e)].push(e); });
  return g;
}

// 代碼數字感知排序：先比數字，再比字母後綴（0050 < 00400A < 006201 < 009800）
function _catNatKey(code) {
  const m = /^(\d+)([A-Z]*)$/.exec(String(code).toUpperCase());
  return m ? [parseInt(m[1], 10), m[2]] : [Infinity, String(code)];
}
function catCompareCode(a, b) {
  const x = _catNatKey(a.code), y = _catNatKey(b.code);
  if (x[0] !== y[0]) return x[0] - y[0];
  return x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0;
}

// 名稱排序：zh-Hant + numeric；不支援時退回字串比較
const _catCollator = (typeof Intl !== 'undefined' && Intl.Collator)
  ? new Intl.Collator('zh-Hant', { numeric: true }) : null;
function catCompareName(a, b) {
  const x = String(a.name || ''), y = String(b.name || '');
  if (_catCollator) return _catCollator.compare(x, y);
  return x < y ? -1 : x > y ? 1 : 0;
}

function catDefOf(key) {
  return CAT_DEF.find(d => d.key === key) || null;
}
