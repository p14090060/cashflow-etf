// watch-store.js — Phase 4 自選（我的 ETF）收藏狀態：唯一來源（PHASE4_PLAN §2）
// 分類、Detail、自選頁只透過 WatchStore 讀寫，不各自保存。純資料，不碰 DOM。
// 通知型別：add／remove／restore（帶 code，只需更新該檔的 ♡）；move／sync（不帶 code，所有訂閱者全部重新同步）。
// ⚠ 傳統 <script>，不要 type="module"。須在 category.js、detail.js、watch.js 之前載入。

const WatchStore = (function () {
  const KEY = 'etfRadar.watch.v1';
  let codes = [];
  let readOk = true;       // false：localStorage 讀不到（記憶體模式）
  let persistOk = true;    // false：最近一次寫入失敗（記憶體狀態優先，不被舊資料覆蓋）
  const subs = [];

  function clean(arr) {
    if (!Array.isArray(arr)) return [];
    const seen = {}, out = [];
    arr.forEach(c => {
      if (typeof c !== 'string') return;
      const k = c.trim().toUpperCase();
      if (!k || seen[k]) return;
      seen[k] = true; out.push(k);
    });
    return out;
  }
  function parse(raw) {
    if (!raw) return [];
    try { const o = JSON.parse(raw); return clean(o && o.codes); } catch (e) { return []; }
  }
  function load() {
    try { codes = parse(localStorage.getItem(KEY)); readOk = true; }
    catch (e) { codes = []; readOk = false; }
  }
  function save() {
    if (!readOk) { persistOk = false; return; }
    try { localStorage.setItem(KEY, JSON.stringify({ v: 1, codes: codes })); persistOk = true; }
    catch (e) { persistOk = false; }
  }
  function emit(type, code) {
    const ev = { type: type, code: code || null };
    subs.slice().forEach(fn => { try { fn(ev); } catch (e) { setTimeout(() => { throw e; }); } });
  }
  function norm(code) { return String(code || '').trim().toUpperCase(); }

  function add(code) {
    const c = norm(code);
    if (!c || codes.indexOf(c) >= 0) return false;
    codes.push(c); save(); emit('add', c);
    return true;
  }
  function remove(code) {
    const c = norm(code), i = codes.indexOf(c);
    if (i < 0) return null;
    codes.splice(i, 1); save(); emit('remove', c);
    return { code: c, index: i };
  }
  // 冪等：已在清單中就不動（不重複、不搬動）；否則插在 min(index, 長度)
  function restore(code, index) {
    const c = norm(code);
    if (!c || codes.indexOf(c) >= 0) return false;
    const i = Math.max(0, Math.min(index | 0, codes.length));
    codes.splice(i, 0, c); save(); emit('restore', c);
    return true;
  }
  // 以 code 規劃位置：把 code 移到 beforeCode 之前（beforeCode 為 null → 最後）。任一不存在就不動。
  function moveCode(code, beforeCode) {
    const c = norm(code), from = codes.indexOf(c);
    if (from < 0) return false;
    const b = beforeCode == null ? null : norm(beforeCode);
    if (b === c) return false;
    if (b != null && codes.indexOf(b) < 0) return false;
    const next = codes.slice(); next.splice(from, 1);
    const to = b == null ? next.length : next.indexOf(b);
    next.splice(to, 0, c);
    if (next.join() === codes.join()) return false;
    codes = next; save(); emit('move');
    return true;
  }
  function subscribe(fn) { subs.push(fn); return function () { const i = subs.indexOf(fn); if (i >= 0) subs.splice(i, 1); }; }

  // 其他分頁改了自選：只同步、不回寫。本分頁最近一次寫入失敗時，不以舊資料覆蓋使用者剛做的變更。
  window.addEventListener('storage', function (ev) {
    if (ev.key !== KEY && ev.key !== null) return;
    if (!persistOk) return;
    let next;
    try { next = parse(localStorage.getItem(KEY)); } catch (e) { return; }
    if (next.join() === codes.join()) return;
    codes = next; emit('sync');
  });

  load();

  return {
    KEY: KEY,
    list: function () { return codes.slice(); },
    has: function (code) { return codes.indexOf(norm(code)) >= 0; },
    add: add,
    remove: remove,
    restore: restore,
    moveCode: moveCode,
    subscribe: subscribe,
    persistOk: function () { return persistOk; },
    readOk: function () { return readOk; },
    _reload: load   // 測試用
  };
})();
