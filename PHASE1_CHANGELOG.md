# Phase 1 Changelog — 全站搜尋

**日期**：2026-10-04
**Baseline**：`2ec0cb17`（pre-UI verified）
**本階段 commit**：`e674f8e2`（功能）、`9c5622b6`（桌面實測後修正）、`89e6641a`（真機實測後修正）
**最終 SHA**：`89e6641a`

---

## 修改檔案

| 檔案 | 變更 |
|---|---|
| `js/search.js` | **新增**（~150 行）。搜尋、下拉、結果面板、表頭高度同步 |
| `index.html` | 表頭改為 `<header class="app-hdr">` 包住標題列＋新增的搜尋列；新增結果面板 DOM；新增 `<script src="js/search.js">`；版本號 `20261003b` → `20261004a` |
| `css/base.css` | 新增 `.app-hdr` / `.gsearch-*` / `.gs-*`；sticky 與背景從 `.topbar` 移到 `.app-hdr`；新增 `[hidden]{display:none!important}` |
| `css/pages.css` | `.rank-sticky` 的 `top:0` 改為 `top:var(--hdr-h, 104px)` |

---

## 新增功能

**頂部固定搜尋列**，全站五個分頁皆可見。

- 輸入代碼或名稱 → 即時下拉最多 8 筆（代碼、名稱、現價、漲跌）
- 超過 8 筆時標示「共 N 檔符合，先顯示前 8 筆」
- 鍵盤：`Enter` 選第一筆、`↑↓` 移動、`Esc` 全部收起
- `✕` 清空輸入；點搜尋列以外的地方收起下拉
- 選取後開啟**結果面板**（覆蓋層），沿用既有 `renderSignalCard()`
- 該檔有 PCF 持股資料時，面板多一顆「看這檔的持股異動 ›」→ 呼叫既有 `openFlow()`

### 比對規則

`_gsMatch()`：`4` 代碼完全相同 ／ `3` 代碼開頭 ／ `2` 代碼或名稱包含 ／ `1` 只有分類包含。
同分以成交量排序。

多比對 `div_category` 是實測決定的——台灣 ETF 名稱混用「高股息」與「高息」：

| 查詢 | 只比名稱 | 加上分類 |
|---|---:|---:|
| 高股息 | 8 | **76** |
| 債券 | 0 | **3** |
| 海外 | 0 | **10** |
| 科技 | 18 | 21 |
| 0050 | 1 | 1 |
| 00981A | 1 | 1 |

代碼搜尋完全不受影響。

---

## 修正（實測後）

1. **結果面板蓋住下拉**（本階段造成）
   `.app-hdr` 是 `position:sticky` ＋ `z-index:50`，**會建立堆疊脈絡**，
   因此下拉寫 `z-index:60` 對外仍等同 50，而面板（兄弟節點）是 55 → 面板勝出。
   症狀：搜「高股息」時下拉被前次留著的面板遮住，看起來像「只找到一檔」。
   → 面板降為 `z-index:40`；開始新查詢時自動收掉舊面板；`Esc` 一次收乾淨。

2. **表頭變高導致排行頁 sticky 區塊被遮**（本階段造成）
   `.rank-sticky` 原為 `top:0`、`z-index:10`，低於表頭的 50。
   → `_syncHdrH()` 於 load 與 resize 時量出表頭實際高度寫入 `--hdr-h`，
     `.rank-sticky` 改用該值。高度會隨狀態列字數變動，故用量測而非寫死。

---

## 真機測試後的修正（`89e6641a`）

Android 實機測試（直向／橫向）發現兩項 FAIL，皆由 Phase 1 引入，已於本階段內修正。

### FAIL 1 — 虛擬鍵盤彈出後，下拉只看得到前 3 筆

**原因**（兩個疊加）

1. `.gsearch-list` 的 `max-height:46vh` —— `vh` 不會因虛擬鍵盤而縮減，
   下拉以為自己有半個螢幕可用。
2. 底部導覽列是 `position:fixed`、`z-index:100`，直接壓在下拉上面，再被切一刀。

**修正**

新增 `_gsSyncListMax()`，用 `window.visualViewport` 取得鍵盤彈出後的實際可視高度，
再取「可視視窗底部」與「底部導覽列上緣」兩者較小值當地板：

```js
const viewH = (vv && vv.height) ? vv.height : window.innerHeight;   // fallback
const floor = nav ? Math.min(viewH, nav.getBoundingClientRect().top) : viewH;
```

不去猜鍵盤會不會把導覽列推上來——Android 各家瀏覽器行為不一致
（測試機會推上來，`resizes-visual` 模式的瀏覽器不會），取 `min()` 兩種情況都成立，
**未寫死任何裝置數值**。

- fallback：`visualViewport` 不支援時退回 `window.innerHeight`；
  CSS 的 `max-height:46vh` 保留為最後防線（JS 未執行時仍有上限）
- 下限 132px，確保至少露得出 3 筆；下拉本身 `overflow:auto`，可內部捲動
- 重算時機：`resize`、`orientationchange`（各算兩遍——當下一遍、
  下一個繪製影格再一遍，因旋轉時 `resize` 可能在版面定下來前就觸發）、
  `visualViewport` 的 `resize` 與 `scroll`（鍵盤開合只會動它，
  `window.resize` 不一定發）、以及每次顯示下拉之前

### FAIL 2 — 橫向模式下排行頁一列清單都看不到

**原因**

橫向視窗高約 350px，固定元素合計約 300px
（全站搜尋表頭 ~100 ＋ `.rank-sticky` ~140 ＋ 底部導覽 62），僅餘約 50px。

此問題由 Phase 1 引入：`.rank-sticky` 原本被表頭遮住而不可見，
`e674f8e2` 修正其 `top` 使其正常顯示後，矮螢幕上反而把內容擠光。

**修正**

```css
@media (max-height: 520px) { .rank-sticky { position:static; } }
```

寧可讓它捲走，也要讓排行內容看得到——未壓縮內容來保 sticky。
直向（高度 > 520px）行為完全不變。

### 一併處理

搜尋框 `font-size` 15px → **16px**。iOS Safari 對字級 < 16px 的輸入框，
聚焦時會自動放大頁面且不會縮回（`user-scalable=no` 自 iOS 10 起無效）。
站上其他輸入框本來就都是 16px，這裡對齊。
測試機為 Android 未重現，屬預防性修正。
修正後全站所有 `input` 字級皆為 16px。

### 複測結果（全部 PASS）

**Android 真機**

| # | 項目 | 結果 |
|---|---|---|
| 1 | 直向＋鍵盤開啟＋搜尋 `0050` | PASS — 下拉完整顯示，未被鍵盤或導覽列裁切 |
| 2 | 搜尋結果超過 3 筆（`高股息`，76 筆） | PASS — 下拉內部可捲動，8 筆皆可見 |
| 3 | Bottom Nav 不遮搜尋結果 | PASS |
| 4 | 關閉鍵盤後版面恢復 | PASS — 下拉高度跟著還原 |
| 5 | 橫向排行頁 | PASS — 清單可見且可捲動 |
| 6 | 轉回直向，排行頁 sticky | PASS — 恢復黏在搜尋列下方，行為未被破壞 |

**桌面（regression 檢查）**

| # | 項目 | 結果 |
|---|---|---|
| 7 | 搜尋、開面板、關面板、Esc | PASS |
| 8 | 排行頁捲動與 sticky | PASS |
| 9 | Console | PASS — 無新增 JavaScript error |

---

## 刻意未修改的範圍

- **今日頁、配息頁既有的查詢框保留**。Phase 1 維持純新增，回歸風險最低。
  IA 計畫的「四個搜尋入口收斂為一個」留待 Phase 2 詳細頁上線後一併處理。
- **未改 `rank.js` 的 `_matchEtf()`**，避免動到排行頁既有行為。
- **未沿用 `lookupToday()` 的估算路徑**（`estPrice = 20 + (code % 100) * 0.6`，
  用代碼數字推算價格）。全站搜尋只比對實際存在的 203 檔，查無就說查無。
- 未製作 ETF 詳細頁、未做分類頁、未改 Bottom Nav、未做 Light/Dark Mode。
- 未更動任何資料來源、計算邏輯、Python 端或 workflow。

---

## 實測項目與結果

環境：Windows / Chrome，網址帶 `?fresh=` 參數避開快取。

| # | 項目 | 結果 |
|---|---|---|
| 1 | 搜尋 `0050` | PASS — 下拉首筆為 0050 元大台灣50，帶現價與漲跌 |
| 2 | 搜尋 `高股息` | PASS — 下拉 8 筆（0056、00900、00882、00934、00915、00964、00963、00956），底部標示「共 76 檔符合，先顯示前 8 筆」 |
| 3 | 搜尋 `債券` | PASS — 3 檔（00985D 9.44、00980D 19.44、00840B 27.54） |
| 4 | 點下拉開面板 | PASS — 顯示該檔價格訊號卡 |
| 5 | `0056` ＋ Enter（不用滑鼠） | PASS — 直接開啟 0056 面板 |
| 6 | 搜 `00981A` → 按「看這檔的持股異動 ›」 | PASS — 面板關閉，跳至主動頁並選取該檔，treemap 正常 |
| 7 | 面板開啟時直接改查別的 | PASS — 舊面板自動收掉，新下拉未被遮住 |
| 8 | `Esc` | PASS — 下拉、輸入、面板全部收起 |
| 9 | 排行頁捲動 | PASS — 「ETF 成交量排行」區塊正常停在搜尋列下方，未被遮蓋 |
| 10 | 五分頁切換 | PASS — 搜尋列在每一頁皆可見 |

### 靜態驗證

- 11 個 JS 檔括號全數收斂；跨檔重複頂層宣告 0 個
- 16 個生效 handler 全部對得到定義檔（新增 6 個 `gs*` 皆在 `search.js`）
- `search.js` 使用的 6 個 DOM id 全部存在
- 相依順序：`ETFS`／`renderSignalCard`（calc.js）、`_matchEtf`（rank.js）、
  `_flowData`（flow.js）皆先於 `search.js` 載入；
  `openFlow`（boot.js）在其後，但僅於點擊時呼叫，不受載入順序影響
- 線上 14 個資源實測 HTTP 200，零 404

---

## Console 狀態

**無新增 JavaScript error。**

僅餘 `/favicon.ico` 404 —— 經 git 比對確認 `pre-split`（`7b83383f`）已存在，
屬既有狀況，與本階段無關。

---

## 已知限制

1. **目前站上有 4 個搜尋入口**（全站搜尋、今日頁、配息頁、排行頁）。
   這是 Phase 1 刻意維持純新增的結果，預計 Phase 2 收斂。
2. **排行頁搜尋的比對規則與全站搜尋不同**（`_matchEtf` 無分類比對）。
   兩套會在排行頁搜尋併入全站搜尋時收斂。
3. **排行頁 sticky 區塊佔用較多垂直空間**。它原本就是 sticky，只是過去被表頭
   遮住看不見；修正 `top` 之後才正常顯示。待其搜尋框移除後可回收空間。
4. **結果面板目前只有價格訊號**，無配息、績效、成分。那些隨 Phase 2 的
   ETF 詳細頁提供，面板上已標示。
5. **只比對 `market.json` 收錄的 203 檔**。未收錄的代碼回報查無，不做估算。
6. `--hdr-h` 由 JS 於 load／resize 計算；若該段未執行，CSS fallback 為 104px。
7. **真機測試僅涵蓋 Android**（直向＋橫向，含虛擬鍵盤）。
   iOS 未實測；搜尋框字級已提升至 16px 以預防 Safari 聚焦自動放大，
   但 iOS 的 `position:fixed` 於網址列伸縮時的行為仍未驗證。
8. **橫向模式下可視內容仍然有限**。`.rank-sticky` 取消固定後可捲動，
   但全站搜尋表頭（~100px）與底部導覽列（62px）仍為固定元素，
   約 350px 高的橫向視窗剩約 190px 放內容。
   若後續要再改善，可考慮矮螢幕時一併收合搜尋列。

---

## Commit SHA

```
e674f8e2  feat(phase1): 全站搜尋
9c5622b6  fix(phase1): 結果面板蓋住下拉；搜尋改為同時比對分類
89e6641a  fix(phase1): 修 Mobile 真機測出的兩項 FAIL              ← 最終
```

回滾：`git revert 89e6641a 9c5622b6 e674f8e2`（回到 baseline `2ec0cb17`）
