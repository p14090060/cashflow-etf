// state.js — 全站共用資料（Phase 5 從 calc.js 搬出；calc.js／lookup.js 已退役）
// ⚠ 一律用傳統 <script> 載入，不要加 type="module"，且必須排在所有讀 ETFS／CALENDAR 的檔案之前。
// renderAll（render.js）在每次資料到達時重新指派這兩個陣列；
// 初始為空陣列：抓不到資料時寧可畫面空著並明說，也不要拿假資料充數（2026-10-03）。
let ETFS = [];
let CALENDAR = [];
