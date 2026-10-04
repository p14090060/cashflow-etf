# Phase 3 CHANGELOG — 分類瀏覽與導覽重組

依據：`PHASE3_PLAN.md` Rev.3.3（Codex 最終 Review：PASS FOR CODING AFTER PRODUCT DECISIONS）。
前置：Phase 2 VERIFIED / CLOSED（baseline `1958cdc0`；封版文件 `74c61106`）。
狀態：Coding commit 完成，**待 Codex Code Review**。未 push。真機驗收待 Codex 審查後另行安排。

## 產品決策（Product Owner，2026-10-05）

- **D-ESG**：00920 富邦ESG綠色電力、00923 群益台ESG低碳50、009809 富邦淨零ESG50 → **主題型**。
  依主要產品特色（ESG／綠能／低碳／淨零主題）的一般瀏覽直覺歸類；不建立僅為 00920 的名稱覆寫。
- **D14**：「自選」只建立可進入的空狀態頁「我的自選／自選 ETF 功能即將開放」。收藏、localStorage、排序等留到 Phase 4。
- 其他 D11–D13、D15–D17 依 Plan 預設。

## 新增

- `js/category-rules.js`：分類規則（純函式、無 DOM）。優先順序與 Plan §3.1 一致。
  - 規則表只在此檔；UI 不含任何 ETF 代碼。
  - 代碼數字感知排序、名稱排序（zh-Hant collator，不支援時退回字串比較）。
- `js/router.js`：history 協調（Plan §7，Rev.3.3）。唯一呼叫 `pushState`／`replaceState`／`history.back`／`history.go` 的地方。
  - 單一 popstate listener；popstate 只根據 `history.state` 渲染；完成只以 popstate 為準。
  - 導航以 intent 表示，規劃只用已確認位置（confirmed）。同時最多一個 traversal；在途時 active 忽略、orphan park（last wins）。
  - timeout（500ms）只取消 continuation；3 秒只顯示「處理中」；orphan continuation 永不復活。
  - Phase 2 語意保留：未開啟 Detail → push；已開啟切換另一檔 → replace；一次 Back 離開。
  - Phase 2 格式（`{etfDetail, code}`）與 `null` state 正規化為 v2，只修正當前 entry，不新增 entry。
- `js/category.js`：分類分頁 UI。
  - 八份文件夾（左右各 4）、頁籤不重疊、些微錯位（不旋轉文字）。
  - 開啟過場：被點頁籤微抬起，主區淡入；收合過場；reduced-motion 時立即切換。
  - 清單前 10 檔、查看更多每次 +10、代碼／名稱排序、次要 7 個短標籤、持股異動分段（主動式）。
  - 低高度讓位：`gs-ckm` 時隱藏次要標籤與說明；量測實際可用高度；提示列位於標題列內。
- `css/category.css`：文件夾、過場（transform／opacity）、reduced-motion、低高度讓位、工具頁與自選樣式。
- `tests/fixtures/etf_203.json`：203 檔快照（code、name、div_category）＋期望分類（Python 參照實作產生）。
- `tests/browser/category_test.py`（84 項）、`tests/browser/router_test.py`（64 項）。

## 修改

- `index.html`：導覽改為 首頁／分類／自選／工具 四格；新增 `#page-cat`、`#page-watch`、`#page-tools`；持股異動頁（`#page-check`）移入分類頁的 `#catFlowHost`；首頁加入頻道入口卡；資源版本號 bump 為 `20261005g`。
- `js/nav.js`：`switchPage` 改為 Router 的基底切換；舊名稱保留為相容入口。
- `js/detail.js`：history 相關程式（`_pendingPop`、`_queuedOpen`、`_detailPushed`、`_restoreCode`、popstate／keydown listener）移除，改委派給 Router。Detail 畫面與內容不改。`detailTab`、`detailGoFlow`、`detailOnMarketUpdate` 保留。
- `js/boot.js`：啟動時 `Router.init()`；首次載入失敗改為 `Router.onDataError()`；`openFlow` 改為 `Router.openFlow`。
- `js/render.js`：`renderAll` 尾端呼叫 `Router.onMarketUpdate()`。
- `js/flow.js`：`page-check.active` 的判斷改為 `Category.isFlowVisible()`；資料到位時若持股異動可見則重繪；`flowSelect` 記住代碼。

## 實作中發現並修正的問題

- `window.Category`／`window.Router` 判斷失效：頂層 `const` 不會掛在 `window` 上，改為 `typeof X !== 'undefined'`。
- `onMarketUpdate` 在還原前的首次資料到位時跳過分類重算，導致計數與清單永遠空白；改為每次資料到位都先重算。
- 清單 `fit()` 先清空 `max-height` 再量測，展開時沒有捲動範圍，`scrollTop` 被夾成 0；改為直接量測。
- Phase 2 的 popstate 行為（`cancelPendingSearch`、Back 關 Detail 時收起搜尋下拉）在 router 改寫時遺失，已補回（X7、F2）。
- 改寫 `detail.js` 時誤刪 `detailTab`，已補回（T17、T18、C9 因此失敗，補回後通過）。
- 低高度：分段切換列過高，已在 `gs-ckm` 下改為緊湊尺寸。

## 驗證結果（headless Chrome，CDP）

| 測試 | 結果 |
|---|---|
| `detail_ui_test.py` | 42 / 42 PASS |
| `detail_history_fix_test.py` | 14 / 14 PASS |
| `regression_test.py` | 14 / 14 PASS |
| `detail_collapse_test.py` | 25 / 25 PASS |
| `search_compact_test.py` | 38 / 38 PASS |
| `router_test.py` | 64 / 64 PASS |
| `category_test.py` | 82 PASS，0 FAIL，**2 DEFER**（見下） |
| 靜態：頂層名稱重複 | 無（127 個頂層名稱） |
| 靜態：history API 只在 `router.js` | 是 |
| 靜態：UI 程式含 ETF 代碼 | 無（代碼只在規則表與 fixture） |
| 靜態：`type="module"` | 無 |

### 分類分布（fixture，依 PO 決策）

市值型 16、高股息 22、主動式 32、科技／半導體 20、海外／區域 78、主題型 21、債券 6、其他 8（合計 203）。
與 Rev.2 的 18／19 相比，差異來自 00923、009809 改為主題型。

## 測試政策執行（Plan §16.1）

行為斷言全部保留。只有「內部 history／實作狀態」斷言依 router 改寫更新為 v2 等價斷言：

| 測試 | 原斷言（內部） | 更新為（行為等價） |
|---|---|---|
| detail_ui T8、T19 | `_pendingPop == 0` | `__routerInflightState() is None` |
| detail_ui T12 | `history.state.code == '0056'` | `Router.state().stack[-1].code == '0056'` |
| detail_ui T13 | `page-check.classList.contains('active')` | `page-cat` active 且 `Category.isFlowVisible()` |
| detail_history_fix F1（兩項） | `_restoreCode is None` | `Router.state().stack.length == 0`；移除對 `_restoreCode` 的設定，保留行為情境 |
| regression R（check） | `page-check.active` | `page-cat` active 且 `Category.isFlowVisible()` |

`detail_collapse_test.py` 與 `search_compact_test.py` 未修改。

## 已知限制與 DEFER（需決策或真機）

1. **LR-4（844×170，鍵盤開）：清單無法達到 44px。** 全站免責 `.disclaimer`（85px，Phase 1 既有、法遵要求）不在分類頁內，不改 Phase 1 行為則無法騰出空間。目前 fallback：提示「收起鍵盤可看完整清單」位於標題列內（可視區內）。**需要決策**：是否在鍵盤模式隱藏全站免責（會改變 Phase 1 已驗證行為）。
2. **LR-8（offsetTop > 0）：headless 無法產生可視區平移。** 需 iPhone Chrome 真機補測。依指示，本次不要求真機測試。
3. **R-N3：traversal 若永不抵達**，系統停在「處理中」，復原靠重新整理（從實際 `history.state` 還原）。需真機確認是否會發生。
4. **base 切換以 replaceState 進行（E0）**：關閉 Detail 後留下的 forward entry 仍存在，Forward 可回到舊 Detail，行為與 Phase 2 相同（RT-20 記錄）。
5. **↻ 重新整理仍用 `location.replace`**（Phase 2 既有已知限制：跨文件返回）。
6. **排行列直接進入持股異動**：Back 回分類總覽（與 Plan §8 的來源一致；排行列未列入 §8 的四種來源，此處依同一規則處理）。
7. **動畫為簡化版**：開啟時被點頁籤微抬起、主區淡入（220–240ms）；未做完整幾何 FLIP。reduced-motion 下狀態立即切換。
8. **工具頁與自選占位為靜態 HTML**：Plan §15 預計的 `js/tools.js` 未建立（無狀態，不需要）。
9. **00850、00888、00928、00692** 仍歸其他（PO 決策只涵蓋 00920、00923、009809）。

## Phase 3 不做（依 Plan）

- 不新增高股息標籤篩選器；不改全站搜尋比對規則；不改資料 pipeline；不做 Phase 4 的自選功能。
- 不修改 1px 等外觀細節。
- 不 push。

## Codex 複審修正（針對 `99ec4b14`，NEED FIX）

依 Codex 的三項必修，範圍不擴張；LR-4 未改；不隱藏免責聲明；Phase 1 行為未改。

### 1. Detail 分頁與捲動在 Back → Forward 後還原（RT-2）

- **問題**：分頁切換與捲動沒有記進 history，Forward 回到 Detail 時分頁變回總覽、捲動歸零（pre-fix 對照：Forward 後分頁為 overview）。
- **修正**：
  - `js/router.js`：每個層加上穩定 `id`；新增 `setUi`（只更新記憶體與層快取，不寫 history）；`updateUi` 改為 `setUi` + 寫入。popstate 時以層快取覆蓋 entry 內的舊 ui。捲動等高頻事件先進快取，因此「捲動後立刻 Back」也拿得到最新值。
  - `js/detail.js`：`detailShow(code, ui)` 依層自己的 ui 還原分頁與捲動（先渲染內容，再設定捲動）。分頁切換立即寫入 history；捲動先寫快取，history 寫入合併為 150ms；`pagehide` 時 flush。只有頂層是同一檔 Detail 時才寫入。
  - 切換另一檔（replace）沿用分頁、捲動歸零（Phase 2 語意不變）。
- **測試**：新增 `tests/browser/detail_state_test.py`（DS-1～DS-8，26 項）。涵蓋 Codex 指定情境（0050／配息／捲動 120px → Back → Forward）、Back 後立刻 Forward（快取路徑）、重新整理後還原、切換另一檔、資料夾之上的 Detail、資料夾層 ui 不被污染。
- **負向對照**：暫時還原 `99ec4b14` 的 router／detail，DS 共 8 項 FAIL（DS-1、DS-2、DS-4、DS-5、DS-6、DS-7 等），確認測試會抓到這個 bug。

### 2. Flow 的 visualViewport 重繪（§9.2 F-d）

- **問題**：`flow.js` 只聽 `window.resize`；鍵盤開合與可視區平移時，持股異動不會重繪。
- **修正**：`js/flow.js` 新增 `flowRedrawIfVisible`，掛在 `resize`、`orientationchange`、`visualViewport` 的 `resize` 與 `scroll`。只有持股異動可見時才重繪（`Category.isFlowVisible()`）。
- **測試**：`tests/browser/category_test.py` 新增 FD-1～FD-6：visualViewport resize／scroll、orientationchange、window resize 各重繪一次；清單可見時不重繪；390→360 真實縮放後 treemap 寬度跟隨容器、格子不溢出。
- **負向對照**：pre-fix 的 flow.js 下 FD-1～FD-4 FAIL，修正後 PASS。

### 3. LR-8 驗收測試（§11.6 B、C）

- **問題**：舊測試只檢查 `offsetTop > 0`，偏移存在就算數，沒有驗證可視交集、遮擋與恢復。
- **修正**：`tests/browser/category_test.py` 的 LR-8 區塊重寫。
  - 先在鍵盤狀態（gs-ckm）下產生偏移。
  - **若 `offsetTop > 0`**：檢查搜尋框在 `[offsetTop, offsetTop+height]` 內的可視高度 ≥ 12px；可視區中心點 `elementFromPoint` 命中搜尋框；可視的標題列與導覽列沒有被遮住；無水平捲動。恢復後檢查 `offsetTop` 回到 0、gs-ckm 解除、strip／清單／導覽恢復、清單捲動位置保留。
  - **若 `offsetTop == 0`（目前 headless 的狀況）**：標示 DEFER，detail 寫明已嘗試的方法與結果。
  - **SELF-TEST（stub）**：以 stub 覆寫 `window.visualViewport`，驗證檢查邏輯的正反兩面（區域涵蓋搜尋框 → 判定可見且命中；區域在搜尋框下方 → 判定不可見）。這只證明檢查程式正確，**不是 LR-8 結果**，DEFER 不因此撤銷。
- **已嘗試、無法產生 `offsetTop > 0`**（headless）：`Emulation.setPageScaleFactor` 2 倍 + 捲動手勢、`Input.synthesizePinchGesture`（touch 模擬）、`Emulation.setDeviceMetricsOverride` 的 `positionY`、`viewport`。`visualViewport` 皆無變化。另外 `index.html` 的 `user-scalable=no` 本來就不允許縮放。因此 LR-8 真實項目仍需 iPhone Chrome 真機。

### 測試基礎設施

- `detail_state_test.py` 與 `category_test.py` 開頭停用快取並重新載入。原因：`?v=` 版本號相同時，瀏覽器會拿到舊的 JS，負向對照會得到錯誤結果（第一次對照即因此失真，已改正）。

### 測試結果（headless Chrome，fix 版）

| 測試 | 結果 |
|---|---|
| `router_test.py` | 64 / 64 PASS |
| `search_compact_test.py`（Phase 1 搜尋） | 38 / 38 PASS |
| `detail_ui_test.py`（Phase 2） | 42 / 42 PASS |
| `detail_history_fix_test.py`（Phase 2） | 14 / 14 PASS |
| `regression_test.py`（Phase 2） | 14 / 14 PASS |
| `detail_collapse_test.py`（Phase 2） | 25 / 25 PASS |
| `category_test.py`（Phase 3） | 91 PASS，0 FAIL，**2 DEFER**（LR-4、LR-8 真機） |
| `detail_state_test.py`（新增，DS） | 26 / 26 PASS |

### DEFER（更新）

- **LR-4**：不變。844×170 鍵盤開時清單實測 2px，全站免責 85px 不在分類頁內，等 PO 決策。
- **LR-8**：headless 無法產生 `offsetTop > 0`。B、C 完整檢查已寫好，等 iPhone Chrome 真機實際鍵盤開啟時執行。目前只有 stub 自我檢查，不計為 PASS。
- **R-N3**、**真機 §11.4 九項**：不變，待 Codex 複審通過後再交 PO。

### 版本

- `index.html` 資源版本號 `20261005g` → `20261005h`。

## Codex 複審 Finding 1 修正（Detail scroll 被分類 snapshot 覆蓋）

Codex 複審 `99ec4b14..8e3e59bb`：Finding 2（flow visualViewport）與 Finding 3（LR-8）RESOLVED；唯一待修為 Finding 1。

- **路徑**：分類 → 市值型 → 0050 → 配息 → 捲動 120px → X 或 Esc 關閉 Detail → Forward，Detail 捲動變成資料夾的值（pre-fix 對照：40px，Codex 測得 0px）。
- **原因**：`Category.snapshot()` 在導覽前呼叫 `Router.updateUi`，而 `updateUi` 一律寫入「目前頂層」。Detail 開著時頂層是 Detail 層，資料夾的捲動因此覆蓋 Detail 層的 ui 快取與 entry。
- **修正**：
  - `js/router.js`：`updateUi(patch, type)`、`setUi(patch, type)` 支援指定目標層型別；省略時仍為頂層（Detail 的寫入不變）。指定 `folder` 時寫入最上面那一個資料夾層。
  - `js/category.js`：全部 5 處寫入（snapshot、清單捲動、代碼、排序、查看更多）改為 `Router.updateUi(..., 'folder')`，不再依賴「目前頂層是誰」。
  - 前述 Browser Back → Forward 行為未改（DS-1～DS-8 全數通過）。
- **測試**：`tests/browser/detail_state_test.py` 新增
  - DS-9：X 關閉 → Forward → 原分頁（配息）與捲動（120px）還原；關閉時資料夾的排序、展開數、捲動保留。
  - DS-10：Esc 關閉 → Forward → 原分頁（績效）與捲動（前置條件 > 0）還原。
  - DS-11：分類 sort／expanded（shown）／scroll snapshot 在 Esc + Forward 之後仍正確；Detail 未開時的資料夾捲動仍寫入資料夾層。
- **負向對照**：暫時還原 `8e3e59bb` 的 router 與 category，DS-9、DS-10 的 Forward 捲動都變成 40px（資料夾的捲動值，取代了 Detail 的 120px 與 52px），修正版 PASS。
- **測試結果（修正版）**：Router 64/64、search_compact 38/38、detail_ui 42/42、detail_history_fix 14/14、regression 14/14、detail_collapse 25/25、category 91 PASS／0 FAIL／2 DEFER（LR-4、LR-8 真機，不變）、detail_state 42/42。
- **未處理**：LR-4（PO 決策）。
