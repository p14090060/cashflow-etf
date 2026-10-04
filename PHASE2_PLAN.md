# Phase 2 Implementation Plan — ETF 詳細頁（Rev. 3）

> 狀態：Rev. 3。**最後一次 Plan 修訂，仍未開始 coding。**
> 本版只修三項：① 配息判斷順序與 est 來源 ② History 的 onclick、重整、重複 close ③ 0% 不再視為缺資料。
> 驗收基準：`89e6641a`。數字為 2026-10-04 實測。Python／data pipeline 不修改。

---

## 0. 範圍與不變條件

- **範圍**：全域搜尋 → 選 ETF → Detail（總覽／配息／績效／成分），配息計算機繼承目前 ETF。
- **不做**：分類頁、自選、工具頁、底部導覽改版、`lookup.js`、`fetch_etf.py`／`mis_fetcher.py`、workflow。
- 傳統 `<script>`，不加 `type="module"`。
- Detail 只接受 `ETFS` 中存在的真實 ETF。
- 不污染 `selETF`；Detail 計算機用獨立 DOM id；不複製 treemap。
- **不製造數字**：缺資料只依可確認的資料訊號判定（null、路徑缺失），不依數值推論。

---

## 1. 資料現況（實測摘要）

| 項目 | 實測 | 說明 |
|---|---|---|
| 配息欄位 | 122 檔有 `div_months` 等四欄；81 檔全缺；18 檔 `div_avg_per_share` 為 null | 不可假設 203 檔同 schema |
| 配息 fallback 路徑 | `div_next == null` 共 92 檔，皆 `days=90`、`est=0.3` | `calc_div_forecast()` 成功時必回傳日期；fallback 路徑必回傳 `None`（fetch_etf.py:374-378, 412-413）。**判斷依據是「日期為 null」這個路徑訊號，不是 90 或 0.3 這兩個數值** |
| `est` 來源 | 預設為 yfinance 歷史最後一筆配息（`fetch_etf.py:390`），但 `mis_fetcher.py:546-548` 若該檔 calendar 有官方金額（amount>0）會**覆寫**為官方金額 | 來源不統一，不得一律標為「上一次配息」 |
| 日期來源分裂 | `div_next`（yfinance 推算）與 calendar `iso_date`（官方，5 檔）不一致，如 00939：11-01 vs 10-05。`mis_fetcher.py:544-550` 只覆寫 `days`／`est`，不覆寫 `div_next` | 日期與倒數來源不同 |
| calendar | 12 筆：5 筆 `source:"official"` 且有 `iso_date`；7 筆 `source:"estimate"`、`iso_date:null` | |
| 報酬 0.0 | `fetch_etf.py:882-884` 在歷史不足時寫入 `0.0`，與真實 0% **在 market.json 中無法區分** | 已知 pipeline 限制，本 Phase 不改 |
| 新上市 `ret1y` | `new_listing` 42 檔，為相對面額 NT$10 的報酬 | fetch_etf.py:900-901；mis_fetcher.py:574-576 |
| `ret_months` | 6 段、最舊→最新、每段約 22 交易日、無月份標籤；26 檔含 null | fetch_etf.py:886-890 |
| 成分 | `active_flow.json` 32 檔（主動式），每檔只有增減 `flow`，無完整持股權重 | |

---

## 2. Dividend Data Priority / Confidence Rule

### 2.1 基本定義

- `today`：台北時間今日（`YYYY-MM-DD`，與 render.js 相同算法）。
- `c`：該代碼在 `CALENDAR` 的那一筆（可能為 null）。
- **`estPaired`**：`est` 與 `div_next` 可視為同源，當且僅當
  `div_next != null` **且** `!(c && c.amount_source && c.amt > 0)`。
  - 第一條：`div_next` 有值代表來自 `calc_div_forecast` 成功路徑，與 `est` 同一次呼叫產生。
  - 第二條：沒有被官方金額覆寫。
  - **已知限制**：此判斷是由 calendar 欄位與 mis_fetcher 覆寫行為**推定**，market.json 沒有 provenance 欄位。若 pipeline 日後提供來源欄位，改用該欄位。

### 2.2 判定順序（依序檢查，命中即停止）

| 順序 | 代號 | 條件 | 日期 | 金額 | 單次計算機 |
|---|---|---|---|---|---|
| 1 | **O1 官方有效** | `c.source==="official"` 且 `c.iso_date >= today` | `c.iso_date`（標「官方公告」） | `c.amt > 0` → 公告金額，標 `c.amount_source`；否則「金額待公告」 | 啟用 iff `c.amt > 0` |
| 2 | **O2 官方已過期** | `c.source==="official"` 且 `c.iso_date < today` | 顯示為「公告日 X（已過）」，**不顯示倒數** | 不顯示 | 停用 |
| 3 | **N 不配息** | `div_frequency === "不配息"` | — | — | 停用 |
| 4 | **P 待公告** | `yld_pending === true`，或 `new_listing && div_next == null` | — | — | 停用 |
| 5 | **E1 推算有效** | `div_next != null` 且 `div_next >= today` | `div_next`（標「依歷史推算」） | `estPaired && est > 0` → 「歷史配息金額 X 元（yfinance，未經官方核實）」；否則「金額不可用（無法確認與日期同源）」 | 啟用 iff `estPaired && est > 0` |
| 6 | **E2 推算已過期** | `div_next != null` 且 `div_next < today` | 「推算日已過，資料待更新」，**不顯示倒數** | 不顯示 | 停用 |
| 7 | **U 資料不足** | 以上皆非（實際上即 `div_next == null` 且無官方日期） | — | — | 停用 |

**順序理由**：
- 官方（1、2）優先於 yld_pending／new_listing（4）：官方公告是具體除息日，yld_pending 是人工維護的粗略狀態。
- 待公告（4）優先於推算（5、6）：yld_pending 為真時，即使有推算日也不採用。
- 過期（2、6）位於對應有效狀態之後，但因條件互斥（以 `today` 區分），**過期狀態一定可達**。

### 2.3 同源規則的落實

- 日期與金額必須來自同一列：O1 → 日期與金額都取 calendar；E1 → 日期取 `div_next`，金額僅在 `estPaired` 成立時取 `est`。
- **禁止**：O1 的日期搭配 `est`；E1 的日期搭配官方 `amt`；`estPaired` 不成立時把 `est` 組進單次試算。
- **禁止**：以 `days` 欄位做倒數。倒數一律由採用的日期現算。

### 2.4 計算機與年化

| 項目 | 規則 |
|---|---|
| 單次試算 | 只在 O1（`amt>0`）或 E1（`estPaired && est>0`）啟用。公式：`每股金額 × 張數 × 1000`。O1 標「依公告金額」；E1 標「依歷史配息金額試算，不代表下次實際配息」 |
| 年化 | 只在 `yld_verified === true` 時顯示；否則「年化待核實」 |
| 停用狀態 | O2、N、P、E2、U 停用，顯示停用原因；**輸入框保留**，不清空不報錯 |

### 2.5 四種情況的呈現

| 情況 | 判定 | 呈現 |
|---|---|---|
| 欄位不存在 | `!('div_months' in e)`（81 檔） | 配息月份／歷史平均／分類三列整列省略；底部小字「此檔未建立配息分類資料」。不顯示 `--`（會被讀成查無） |
| 欄位存在但 null | `div_avg_per_share === null`（18 檔） | 該列顯示「資料不足（尚無足夠配息紀錄）」 |
| 不配息 | N | 「此檔不配息」 |
| 待公告 | P | 「待公告」 |
| 有依據 | O1／E1 | 依 2.2 標籤顯示 |

**全域禁止**：不得寫「近一次實際配發」；不得出現任何 fallback 數值（不論其數字是多少）。

### 2.6 既有 UI（本 Phase 不修）

`renderSignalCard()`（calc.js:51-53）與 `renderBuyCard()`（render.js:98-100）只看 `yld>0`，仍會對 009818 顯示 90 天／0.30。Detail 不使用這兩段 divPill。今日頁與 A-4 查詢的修正列為獨立 issue（D7）。

---

## 3. 不可製造的資料

| 項目 | 處置 |
|---|---|
| 逐日價格走勢 | 不做 |
| 官方實際配發歷史、配息歷史清單 | 不做 |
| 持股權重 % | 不做，成分只顯示異動摘要 |
| 報酬 0.0 | **0.0 就是 0.0%**，顯示 `0.0%`，不改成 `--`。只有 null 才顯示 `--` |
| `ret_months` 月份名稱 | 不寫月份，標「每段約 22 個交易日，最右為最近一段」 |
| 海外持股金額 | 不算，只列增減股數（既有行為） |

---

## 4. 既有程式：重用與不重用

| 項目 | 處置 |
|---|---|
| `#gsPanel` / `#gsPanelBody` / `.gs-panel` | 沿用為容器 |
| `renderSignalCard()` | Detail 不用，不改 |
| `calcUpdate()` / `selETF` / `#sharesIn` / `#calcOut` | 不用、不改 |
| Detail 計算機 | 新寫 `detailCalc()`，獨立 id `#dtSharesIn` / `#dtCalcOut` |
| `miniBars()` | 沿用。null 畫灰色短柱；0 畫成最小高度 2px 的柱（格式函式本身不動，且 0 不代表缺資料） |
| `_flowData` / `openFlow()` / `_npList()` | 沿用資料與跳轉 |
| `lookup.js` | 不動，Detail 不呼叫 |
| `gsGoFlow()` | 由 `detailGoFlow(code)` 取代（見第 6 節與第 9 節） |

---

## 5. 狀態與刷新

### 5.1 狀態變數（detail.js）

| 變數 | 用途 |
|---|---|
| `_curEtfCode` | 目前代碼（獨立，不用 `selETF`） |
| `_detailOpen` | Detail 是否開啟（= `#gsPanel` 可見） |
| `_detailTab` | `overview` / `dividend` / `perf` / `holdings` |
| `_detailPushed` | 目前這次開啟對應的是否為我們推的 history entry |
| `_pendingPop` | 我們呼叫 `history.back()` 後尚未收到 popstate 的次數 |
| `_queuedOpen` | 等待 `_pendingPop` 歸零後才執行的開啟請求 |
| `_restoreCode` | 重整後從 history state 讀到的代碼，待資料載入後還原（見 6.2） |

**calendar**：`calc.js` 新增 `let CALENDAR = [];`；`render.js` 的 `renderAll()` 內 `CALENDAR = cal;`。Detail 以 `CALENDAR.find(...)` 讀取，不塞進 ETF 物件。

**flow 狀態（實作注意，最小改動）**：`flow.js` 新增 `_flowStatus`，值為 `loading`／`ok`／`failed`。
- 成分 Tab 只在 `ok` 且該代碼有 coverage 時顯示。
- `loading` 與 `failed` 都不顯示，`failed` 不另報錯（主動頁自己會顯示）。
- `ok` 但無 coverage 與 `failed` 的區別在於是否真的載入成功。

### 5.2 刷新：slot patching

- 骨架（標題、tab 列、四個 pane、`#dtSharesIn`、`#dtCalcOut`）在 `openDetail()` 或切換 ETF 時建立一次。
- 每次資料更新只對 `data-slot` 節點寫 `textContent`／`innerHTML`，**不得改寫 input 的 value**。
- 呼叫點：
  - `renderAll()` 尾端 → `detailOnMarketUpdate()`
  - `flow.js` 的 `fetchFlow()` 完成（成功或失敗）→ `detailOnFlowUpdate()`
- 若 ETF 已不在 `ETFS`：顯示「這檔目前不在清單中」，停用計算機，保留骨架與股數。
- 保留：目前 tab、股數與焦點、scroll 位置。

### 5.3 切換另一檔（D1 預設）

股數保留；tab 保留（若新 ETF 無該 tab 則退回總覽）；scroll 回頂部。

---

## 6. History / Back / Close

### 6.1 不變條件

| 編號 | 條件 |
|---|---|
| I1 | `_detailOpen` ⇔ `#gsPanel` 可見 |
| I2 | `_detailOpen ⇒ _detailPushed`，或處於「還原中」狀態（見 6.2） |
| I3 | **每次 Detail 開啟（lifecycle）最多呼叫一次 `history.back()`**。由 `_detailPushed` 把關：呼叫 back 前先把 `_detailOpen` 與 `_detailPushed` 同步設為 false，後續呼叫直接返回 |
| I4 | popstate 處理函式**永不呼叫** `history.back()` |
| I5 | `_pendingPop > 0` 時收到的 popstate 只消耗一次並忽略 |
| I6 | `event.state` 可能為 `null`（回到基底畫面）。判斷一律寫 `ev.state && ev.state.etfDetail`，null 視為基底 |

### 6.2 重整（reload）後的 history entry

- **不清除標記**。若在 boot 直接 `replaceState(null)`，會留下與基底重複的 entry，即幽靈 entry。
- boot 讀到 `history.state.etfDetail` → 設 `_restoreCode = state.code`。
- **還原時機**：第一次 `detailOnMarketUpdate()` 或第一次 `showDataError()`，以先到者為準。
  - 代碼在 `ETFS` 中 → `openDetail(code, {fromHistory:true})`（不 push，`_detailPushed=true`）。
  - 代碼不在 `ETFS` → 仍開啟骨架，顯示「這檔目前不在清單中」。
  - 資料載入失敗 → 仍開啟骨架，顯示資料錯誤。
  - 還原後 tab 回到總覽。
- **已知限制**：還原後若按 ✕ 或返回，瀏覽器會跨文件返回到重整前的那筆 entry（同一 URL），造成一次整頁載入，結果等同回到基底畫面。**不產生幽靈 entry**，但會有一次畫面閃動。列入 F12 驗收。

### 6.3 `closeDetail()`（唯一的關閉入口，idempotent）

```
function closeDetail() {
  if (!_detailOpen) { _queuedOpen = null; return; }
  hideDetail();                       // 先隱藏，畫面不等 history
  if (_detailPushed) {
    _detailPushed = false;
    _pendingPop++;
    history.back();
  }
}
```

所有關閉來源都呼叫它：✕（`index.html:44`）、Esc、底部導覽（`switchPage()` 開頭）、`detailGoFlow()`。重複呼叫不會再次 back。

### 6.4 popstate 處理（順序固定）

1. `_pendingPop > 0`：`_pendingPop--`；若歸零且 `_queuedOpen` 存在，執行並清空；**return**。
2. `ev.state && ev.state.etfDetail`：`openDetail(ev.state.code, {fromHistory:true})`；**return**。
3. 否則若 `_detailOpen`：`hideDetail()`；`_detailPushed = false`。

此處理器沒有任何 `history.back()` 呼叫（I4）。

**已知 race**：back 落地前連按兩次返回，第二次會被當成使用者返回，可能離開站內。可接受，列入 F10。

### 6.5 轉換表

| 動作 | 前置狀態 | 行為 | History |
|---|---|---|---|
| 搜尋選取 ETF | 關閉 | `openDetail(code)` → `pushState` | +1 |
| 搜尋選取另一檔 | 開啟 | 更新代碼與骨架，保留 tab | `replaceState`（D1） |
| 搜尋框只打字 | 開啟 | 無變化（D2） | 無 |
| ✕ | 開啟 | `closeDetail()` | 一次 back |
| Esc（input 的 gsKey 與 document 監聽都會觸發） | 開啟 | 第一次觸發關閉，第二次為 no-op | 一次 back |
| 底部導覽 | 開啟 | `switchPage()` → `closeDetail()` → 切頁 | 一次 back |
| 成分「查看完整持股異動」 | 開啟 | `detailGoFlow(code)`：`closeDetail()` → `gsClear()` → `openFlow(code)` | 一次 back |
| 手機返回鍵 | 開啟 | popstate step 3 | 無額外 |
| 瀏覽器 Forward | 關閉 | popstate step 2 → 開啟 | 不 push |
| back 未落地又要開 | `_pendingPop > 0` | `openDetail` 進 `_queuedOpen` | 落地後 push |
| ↻ | 任何 | `location.replace(...)`（見 6.6） | 不新增 |
| Tab 切換 | 開啟 | 只改 pane 顯示 | 無 |

### 6.6 其他

- **↻ 重新整理**：`boot.js` 的 `reloadData()` 目前用 `location.href`，每按一次新增 entry（既有問題）。改為 `location.replace(...)`。
- **onclick 全數改接**（見第 9 節清單）：`index.html:44` 必須改為 `closeDetail()`，不能留下 `gsClosePanel()`。
- 搜尋下拉不在 history 內；Detail 開著按返回時，下拉一併收起。

---

## 7. 成分 Tab

### 7.1 可見條件

`_flowStatus === "ok"` 且 `_flowData.etfs[code]` 存在（同 search.js:152-153 的既有判斷）。

### 7.2 內容（摘要，不重寫 treemap）

| 欄位 | 顯示 |
|---|---|
| 投信 | `issuer` |
| 資料日 | `data_date`；金額換算日 `price_date`（有值才顯示） |
| 加碼／減碼總額 | `buy`／`sell`；皆空或 0 → 「—」，不顯示 +0.0 億（沿用 flow.js:160-162） |
| 最近持股異動日 | `last_change_date`（null 則不顯示此列）。文字用中性的「最近持股異動日」，**不宣稱一定是換股** |
| 持股檔數 | `holdings` |

### 7.3 必須保留的資料語意

| 條件 | 顯示 |
|---|---|
| `fetched === false` | 「本次未能取得新資料（投信網站異常）」；若有先前結果，加「以下為先前結果」 |
| `flow_to` 存在且 ≠ `data_date` | 「最新 PCF（資料日）持股無異動，以下為最近一次有持股異動的紀錄」 |
| `reason === "not_updated"` 且 `advanced === false` | 「資料日之後尚未有新的 PCF」 |
| `scale_pct != null` | 「本期持股同步變動 ±N%，屬基金規模增減（申購／贖回），非經理人選股」 |
| 有任何金額 | 「金額為兩份 PCF 快照相減的推估值，不等同基金實際成交」 |
| `no_price` 非空 | 「另有 N 檔海外持股異動，無台股報價無法換算金額，完整清單見主動頁」 |

### 7.4 `flow = []` 的 empty state

| 條件 | 顯示 |
|---|---|
| `reason === "no_basis"` | 「尚無前一份持股可比對」 |
| `flow` 空、無 `no_price` | 「最新 PCF（資料日 X）持股與前一份相同」 |
| `flow` 空、有 `no_price` | 「本次異動皆為海外持股，無台股報價換算金額」 |
| `flow` 空、`last_change_date` 為 null | 不出現「以下為…」字樣（沿用 flow.js:175-176 的 hasPrev 判斷） |

### 7.5 操作

「查看完整持股異動 ›」→ `detailGoFlow(code)`。不新增第二份 treemap，不改 `renderFlow()` 介面。

---

## 8. 績效 Tab

| 欄位 | 標籤 | 規則 |
|---|---|---|
| `ret5d` | 近 5 個交易日 | null → `--`；數值（含 0）→ 原樣顯示 `x.x%` |
| `ret1m` | 近約 1 個月（22 個交易日） | 同上 |
| `ret1y` | 非新上市：「近一年」；`new_listing`：「上市以來（以面額 10 元計）」 | 同上。新上市不得標「近一年」 |
| `ret_months` | 近 6 段（每段約 22 個交易日，最右為最近一段） | 沿用 `miniBars()`；單段 null 為灰色短柱；全 null → 「資料不足」；不寫月份名 |

---

## 9. 檔案變更清單

| 檔案 | 動作 |
|---|---|
| `js/detail.js` | **新增**：`dividendView()`（第 2 節）、`detailCalc()`、總覽卡、成分摘要、績效標籤、`openDetail()` / `closeDetail()` / `hideDetail()`、`detailGoFlow()`、popstate 處理、`_restoreCode` 還原、`detailPatch()`、`detailOnMarketUpdate()`、`detailOnFlowUpdate()`、tab 切換、document keydown（Esc） |
| `js/calc.js` | 新增 `let CALENDAR = [];`。其餘不動 |
| `js/render.js` | `renderAll()` 加 `CALENDAR = cal;` 與尾端 `detailOnMarketUpdate();`。`selETF` 那行不動 |
| `js/flow.js` | 新增 `_flowStatus`；`fetchFlow()` 成功與失敗回呼都更新狀態並呼叫 `detailOnFlowUpdate()` |
| `js/boot.js` | `reloadData()` 改 `location.replace`；`showDataError()` 末尾加還原觸發；boot 讀取 `history.state` 設 `_restoreCode`（**不清除**） |
| `js/nav.js` | `switchPage()` 開頭呼叫 `closeDetail()` |
| `js/search.js` | 見下方 onclick 清單 |
| `index.html` | **明列 onclick 改接**（見下）；新增 `<script src="js/detail.js?v=...">` 於 `search.js` 之後、`boot.js` 之前；全部 `?v=` bump。不改 HTML 結構 |
| `css/components.css` | 新增 `.dt-tabs` `.dt-tab` `.dt-tab.on` `.dt-pane` `.dt-row` `.dt-note` 等 |

**onclick 與函式改接清單（實作後必須 grep 確認無殘留）**：

| 位置 | 現況 | Rev.3 處置 |
|---|---|---|
| `index.html:44` | `onclick="gsClosePanel()"` | **改為 `onclick="closeDetail()"`**（必改，否則 ReferenceError） |
| `search.js:82` | `gsSearch()` 內 `gsClosePanel()` | 刪除（D2） |
| `search.js:115` | `gsKey()` Esc 內 `gsClosePanel()` | 改為 `closeDetail()` |
| `search.js:157` | `gsPick()` 產生的 `onclick="gsGoFlow(...)"` | 隨 gsPick 改寫移除；改由 `detailGoFlow()` 產生 |
| `search.js:165-173` | `gsClosePanel()` / `gsGoFlow()` 定義 | 刪除，不留相容層 |
| 保留 | `index.html:34` `gsClear()`；`search.js:100` `gsPick(...)` 列表 onclick | 不動（`gsPick` 保留為 openDetail 的薄包裝） |

實作後的靜態檢查：`grep -n "gsClosePanel\|gsGoFlow" index.html js/*.js` 必須無結果。

**載入順序**：config → nav → flow → archived-check → format → calc → lookup → render → rank → search → **detail** → boot。`detail.js` 頂層只註冊 listener。

---

## 10. 驗收測試（點哪裡 → 應看到什麼）

**A. 基本流程**
- A1 搜尋 0050 → 選取 → Detail 開啟，總覽顯示現價、殖利率、60MA、52 週區間。
- A2 0050 無 flow → 只有三個 tab，無「成分」。

**B. 配息（對照第 2 節）**
- B1 0056 → 「官方公告」，日期 2026-10-22，倒數依今天現算，金額 1.35 並標來源；單次計算機啟用。
- B2 00939 → 日期 10-05（官方），**不是** `div_next` 的 11-01；金額 0.125 標 TWSE。
- B3 0050 → 「依歷史推算」，日期 2027-01-21；金額標籤只用「歷史配息金額 X 元（yfinance，未經官方核實）」，不得寫「上一次」或「預估」；計算機啟用，並標「不代表下次實際配息」。
- B4 009818 → 「資料不足」；畫面不得出現「90 天」或「0.30」；計算機停用並說明原因。
- B5 00910 → 「此檔不配息」，計算機停用。
- B6 任一 `yld_pending` 的 ETF → 「待公告」，計算機停用。
- B7 0053（欄位不存在）→ 配息分類三列不見，底部出現「此檔未建立配息分類資料」。
- B8 O2 過期（**僅程式審查**）：資料目前無過期官方日期。驗證方式：在本機瀏覽器 console 暫時把 `CALENDAR` 某筆 `iso_date` 改為過去日期，確認顯示「公告日 X（已過）」、無倒數、計算機停用。**不寫入任何 data 檔**。
- B9 E2 過期（同上，以 `div_next` 過去日期模擬）→ 「推算日已過，資料待更新」。
- B10 計算機：輸入 10 張 → 金額正確重算。

**C. 成分**
- C1 00981A → 成分 Tab 出現；點「查看完整持股異動」→ 主動頁選中 00981A，搜尋框已清空。
- C2 `flow` 為空的主動 ETF（實測時挑選）→ 顯示 empty state，無「以下為…」字樣。
- C3 00989A → 顯示「本次異動皆為海外持股」與檔數，**無 +0.0 億**。
- C4 `_flowStatus` 為 failed（以程式審查或暫時斷網測試）→ 成分 Tab 不顯示，無錯誤彈出。
- C5 最近持股異動日的文字為「最近持股異動日」，不出現「換股日」。

**D. 績效**
- D1 00403A（新上市）→ 年報酬標「上市以來（以面額 10 元計）」。
- D2 任一 `ret_months` 含 null 的 ETF → 該段為灰色短柱；標題無月份名。
- D3 **00980D（`ret1y` = 0.0）→ 顯示 `0.0%`，不顯示 `--`**。0 與 null 必須分開處理。

**E. 刷新**
- E1 Detail 開著 0050 超過 30 秒 → 仍是 0050，價格可更新，tab 不跳回。
- E2 配息 Tab 輸入 10 張，等 30 秒 → 股數仍為 10，金額正確。
- E3 flow 慢載入：Detail 先開，flow 完成後 → 成分 Tab 自動出現，不需重整。
- E4 Android：輸入框聚焦中等待刷新 → 焦點與鍵盤不被收起。

**F. History**
- F1 開 Detail → ✕ → 關閉。再按一次返回 → 離開站內或回到進站前頁面，**不再出現 Detail**。
- F2 開 Detail → 返回鍵 → 關閉，停在原分頁，不離開站內。
- F3 開 Detail → 切配息 Tab → 返回鍵 → 直接關閉（不是只退一個 Tab）。
- F4 開 Detail → 搜尋另一檔並選取 → 返回鍵 → 直接關閉，不回到前一檔。
- F5 開 Detail → 底部導覽「配息」→ 關閉並切頁；再按返回 → 不回到 Detail。
- F6 開 Detail → 成分「查看完整持股異動」→ 主動頁；**只按一次返回**，應回到進入 Detail 前的狀態，不需要按兩次。
- F7 電腦 Esc → 關閉；**Esc 後接著 ✕（快速連點）→ 只消耗一筆 entry**：之後按一次返回即離開，不需第二次。
- F8 關閉後再搜尋開啟 → 一次返回即關閉，無殘留。
- F9 按 ↻ → 頁面重新載入；之後按返回不會出現舊的 Detail。
- F10 Detail 開啟後快速連按兩次返回 → 不當機、不白屏。
- F11 **Detail 開著時重整瀏覽器** → Detail 會重新開啟在同一代碼（資料載入後），tab 回總覽；Console 無錯誤。
- F12 承 F11：按 ✕ → 可能有一次整頁載入（已知限制），結束後畫面為基底，**再按返回不得出現 Detail**（驗證無幽靈 entry）。
- F13 基底畫面按返回（`ev.state === null`）→ 無 Console 錯誤，無 Detail 出現。

**G. 手機鍵盤與視窗（實作後真機驗收，不以 Phase 1 搜尋框修正代替）**
- G1 Android Chrome：配息 Tab 點股數輸入框 → 輸入框保持在鍵盤上方可見，計算結果可讀。
- G2 旋轉手機 → Detail 不跑版，tab 列不被切掉。
- G3 Detail 內容可捲動，底部導覽不遮住最後一列。
- G4 iOS Safari：未實測，列為 Known Limitation（與 Phase 1 相同）。

**H. 回歸**
- H1 今日頁 A-1 ～ A-4 行為與 Phase 1 一致。
- H2 配息頁舊計算機正常；開過 Detail 後 `selETF` 與數字不變。
- H3 排行頁搜尋、tappable 列、持股異動按鈕正常。
- H4 主動頁 treemap、海外清單、格子點擊提示正常。
- H5 搜尋框鍵盤操作與 Phase 1 一致，**除 D2（打字不再關閉 Detail）為刻意變更**。
- H6 靜態檢查：`grep gsClosePanel\|gsGoFlow` 無殘留。

---

## 11. 開放決策（開工前請 GPT 確認預設值）

| 編號 | 問題 | 預設（本版採用） |
|---|---|---|
| D1 | Detail 開著時選另一檔 | `replaceState`，一次返回即關閉 |
| D2 | Detail 開著時只打字 | 不關閉 Detail（變更 Phase 1 行為） |
| D3 | 切換 ETF 時股數 | 保留 |
| D4 | ↻ | `location.replace`，仍整頁重載 |
| D5 | 總覽 Tab 內容 | 訊號細節（RSI、量比、heat、60MA 偏離），不重複 52 週區間 |
| D6 | `lookup.js` | 本 Phase 不動 |
| D7 | 今日頁 A-4 與卡片的 divPill fallback | 獨立 issue，本 Phase 不修 |
| D8 | flow 是否輪詢 | 不輪詢，開站時載入一次，完成時通知 Detail |

---

## 12. 修訂紀錄

### Rev. 2 → Rev. 3（Codex Rev.2 三項必修）

| 項目 | 改了什麼 |
|---|---|
| ① 配息判斷順序 | 原順序 S3（`div_next != null`）先於 S5（過期），過期永遠不可達。改為 2.2 的 O1 → O2 → N → P → E1 → E2 → U，過期以 `today` 比較，與有效狀態互斥。est 不再標「上一次配息」，改為「歷史配息金額（yfinance，未經官方核實）」；單次計算只在 `estPaired` 成立時啟用（2.1）。fallback 判斷改為路徑訊號（`div_next == null`），不看 90／0.3 數值 |
| ② History | `index.html:44` 的 `gsClosePanel()` 明列改為 `closeDetail()`；重整後採「還原不清除」（6.2），避免幽靈 entry；`closeDetail()` idempotent（6.3），每次 lifecycle 最多一次 back（I3）；popstate 永不 back（I4）、`ev.state === null` 安全處理（I6） |
| ③ 0% | 刪除「精確 0.0 視為資料不足」。0 與 null 分開處理（第 3、8 節）。`fetch_etf.py:882-884` 的 0.0 寫法列為已知 pipeline 限制，本 Phase 不改 |

### 其他三項（Codex 建議，依 GPT 指示列為實作／驗收注意）

- flow 三態（loading／failed／ok+無 coverage）：5.1、7.1、C4
- 手機鍵盤與 visualViewport 實作後真機驗收：G1–G3
- `last_change_date` 改稱「最近持股異動日」：7.2、C5

---

**Rev. 3 完成。仍未 Coding。**
