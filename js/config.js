// config.js — 靜態備援資料與 LAZY_WATCHLIST
// 從 index.html 行 802–832 原樣搬出（2026-10-03 拆檔，未改內容）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"：
//   HTML 裡有 15 個行內 onclick 需要這些函式掛在 window 上。
// ── Fallback static data（data.json 抓失敗時使用）──
const STATIC_ETFS = [
  { code:'0056',   name:'元大高股息',      price:35.2,  ma60:33.8,  low52:31.8, high52:38.5,  yld:6.3, days:47,  est:1.10, signal:'cheap', maD:-4.1, premium:0, ret5d:0, vol_ratio:1 },
  { code:'00713',  name:'台灣高息低波',     price:58.3,  ma60:60.1,  low52:51.2, high52:63.5,  yld:5.9, days:88,  est:1.05, signal:'cheap', maD:-3.0, premium:0, ret5d:0, vol_ratio:1 },
  { code:'0050',   name:'元大台灣50',       price:175.3, ma60:172.1, low52:142.5,high52:183.8, yld:4.2, days:145, est:3.50, signal:'fair',  maD:+1.9, premium:0, ret5d:0, vol_ratio:1 },
  { code:'00919',  name:'群益台灣精選高息', price:22.8,  ma60:22.1,  low52:19.5, high52:25.2,  yld:7.1, days:32,  est:0.45, signal:'fair',  maD:+3.2, premium:0, ret5d:0, vol_ratio:1 },
  { code:'006208', name:'富邦台50',         price:103.2, ma60:100.1, low52:84.6, high52:108.5, yld:3.8, days:158, est:2.10, signal:'fair',  maD:+3.1, premium:0, ret5d:0, vol_ratio:1 },
  { code:'00981A', name:'統一台股增長',     price:16.8,  ma60:16.2,  low52:13.5, high52:17.9,  yld:7.5, days:55,  est:0.40, signal:'fair',  maD:+3.7, premium:0, ret5d:0, vol_ratio:1 },
  { code:'00878',  name:'國泰永續高息',     price:21.5,  ma60:20.2,  low52:18.2, high52:23.1,  yld:6.8, days:65,  est:0.38, signal:'dear',  maD:+6.4, premium:0, ret5d:0, vol_ratio:1 },
  { code:'00940',  name:'元大台灣價值高息', price:14.8,  ma60:13.9,  low52:12.1, high52:16.2,  yld:7.8, days:28,  est:0.32, signal:'dear',  maD:+6.5, premium:0, ret5d:0, vol_ratio:1 },
  { code:'00929',  name:'復華台灣科技優息', price:19.2,  ma60:17.8,  low52:15.8, high52:20.1,  yld:8.2, days:19,  est:0.42, signal:'dear',  maD:+7.9, premium:0, ret5d:0, vol_ratio:1 },
  { code:'00850',  name:'元大ESG永續',      price:32.1,  ma60:30.5,  low52:27.8, high52:34.2,  yld:4.1, days:112, est:0.80, signal:'dear',  maD:+5.2, premium:0, ret5d:0, vol_ratio:1 },
];
const LAZY_WATCHLIST = new Set([
  '0050','0056','006208',
  '00878','00919','00929','00940','00939',
  '00936','00930','00932',
  '00713','00701','00850','00757',
  '00646','00662',
  '00679B','00687B','00772B',
  '00403A',
]);

const STATIC_CAL = [
  { mon:'5月', day:'19', code:'00929', name:'復華台灣科技優息', amt:0.42, soon:true  },
  { mon:'5月', day:'28', code:'00940', name:'元大台灣價值高息', amt:0.32, soon:false },
  { mon:'6月', day:'05', code:'00919', name:'群益台灣精選高息', amt:0.45, soon:false },
  { mon:'6月', day:'10', code:'0056',  name:'元大高股息',       amt:1.10, soon:false },
  { mon:'6月', day:'27', code:'00878', name:'國泰永續高息',     amt:0.38, soon:false },
];

