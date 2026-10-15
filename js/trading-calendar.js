// trading-calendar.js — 台北交易日分類（純靜態，不連網、不新增 API）
// 資料來源：TWSE OpenAPI holidaySchedule 官方休市表（115 年），與 D-037 工具同源的已保存 fixture
//   twse_holiday_schedule_115.json  SHA256 f72a44c4a309319de714208020afe3e3886cff57ebfbea96bc02ad8f9c672f17（2026-10-09 實際回應）
// 只涵蓋下列年度；年度不在表內 → 'unknown'（不從昨天的 is_holiday 猜今天）。
// 表內「開始交易／最後交易」為有交易日，其餘表列日為休市；未表列的平日為交易日；週六日為週末。
// ⚠ 一律用傳統 <script> 載入。
const TW_TRADING_CAL = {
  source: 'TWSE OpenAPI holidaySchedule（twse_holiday_schedule_115.json）',
  sha256: 'f72a44c4a309319de714208020afe3e3886cff57ebfbea96bc02ad8f9c672f17',
  years: [2026],
  days: {"2026-01-01": "中華民國開國紀念日","2026-01-02": "國曆新年開始交易日","2026-02-11": "農曆春節前最後交易日","2026-02-12": "市場無交易，僅辦理結算交割作業","2026-02-13": "市場無交易，僅辦理結算交割作業","2026-02-15": "農曆除夕及春節","2026-02-16": "農曆除夕及春節","2026-02-17": "農曆除夕及春節","2026-02-18": "農曆除夕及春節","2026-02-19": "農曆除夕及春節","2026-02-20": "農曆除夕及春節","2026-02-23": "農曆春節後開始交易日","2026-02-27": "和平紀念日","2026-02-28": "和平紀念日","2026-04-03": "兒童節及民族掃墓節","2026-04-04": "兒童節及民族掃墓節","2026-04-05": "兒童節及民族掃墓節","2026-04-06": "兒童節及民族掃墓節","2026-05-01": "勞動節","2026-06-19": "端午節","2026-09-25": "中秋節","2026-09-28": "孔子誕辰紀念日/ 教師節","2026-10-09": "國慶日","2026-10-10": "國慶日","2026-10-25": "臺灣光復暨金門古寧頭大捷紀念日","2026-10-26": "臺灣光復暨金門古寧頭大捷紀念日","2026-12-25": "行憲紀念日"}
};
// 台北現在（與瀏覽器時區無關）：回傳 { ymd:'YYYY-MM-DD', min:分鐘數, dow:0-6 }
function twNow(ms) {
  const t = new Date((ms == null ? Date.now() : ms) + 8 * 3600000);
  return { ymd: t.toISOString().slice(0, 10), min: t.getUTCHours() * 60 + t.getUTCMinutes(), dow: t.getUTCDay() };
}
// 'trading'｜'holiday'｜'weekend'｜'unknown'；日曆壞掉或年度不在表內 → 'unknown'
function twDayKind(ymd) {
  const cal = (typeof TW_TRADING_CAL !== 'undefined') ? TW_TRADING_CAL : null;
  // R1：必要結構不完整（years 非正整數陣列、days 非物件、日期鍵不在 years、名稱非字串、缺 sha256）→ unknown，不把缺資料猜成交易日
  if (!cal || !Array.isArray(cal.years) || !cal.years.length || !cal.years.every(y => Number.isInteger(y) && y > 1911)) return 'unknown';
  if (!cal.days || typeof cal.days !== 'object' || Array.isArray(cal.days) || typeof cal.sha256 !== 'string' || cal.sha256.length !== 64) return 'unknown';
  if (!Object.keys(cal.days).every(k => /^\d{4}-\d{2}-\d{2}$/.test(k) && cal.years.indexOf(+k.slice(0, 4)) >= 0 && typeof cal.days[k] === 'string')) return 'unknown';
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ymd || '');
  if (!m || cal.years.indexOf(+m[1]) < 0) return 'unknown';
  const dow = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])).getUTCDay();
  if (dow === 0 || dow === 6) return 'weekend';
  const name = cal.days[ymd];
  if (name == null) return 'trading';
  return /開始交易|最後交易/.test(String(name)) ? 'trading' : 'holiday';
}
