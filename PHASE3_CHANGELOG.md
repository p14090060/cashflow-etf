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

## LR-4 responsive fallback（PO 決策：方案 B）

PO 決定（2026-10-05）：LR-4 採方案 B。核准為 responsive fallback，不再視為 DEFER／FAIL。

### 規格（PO 原文要點）

- 極低高度／虛擬鍵盤開啟、剩餘空間不足 44px 可用清單時：保留既有免責聲明，不隱藏、不修改 Phase 1 法遵呈現。
- 不強制顯示不足 44px 的清單；顯示提示「收起鍵盤以查看 ETF 清單」。
- 鍵盤收起、viewport 恢復足夠高度後，分類清單自動恢復。
- 分類狀態（排序、已展開數、捲動）不因 fallback 遺失。

### 實作

- `js/category.js` `fit()`：
  - fallback 條件：`body.gs-ckm`（鍵盤開啟）且可用高度 < 44px（`LINE_H`）且清單可見。
  - fallback 時清單加上 `cat-off`（收合但仍留在版面中，不用 `display:none`，因此 scrollTop 不會被重置）；「查看更多」加上 `cat-gone`；提示文字改為「收起鍵盤以查看 ETF 清單」並顯示。
  - 非 fallback：清單 `max-height = max(44, 可用高度)`（PHASE3_PLAN §11.4 的「最小 44px 並可捲動」）。
  - `snapshot()` 與清單捲動處理在 `cat-off` 時不寫入，避免收合期間的值被寫進資料夾層。
  - 新增 `MutationObserver` 監看 `body` 的 class，`gs-ckm` 切換時重算，不依賴 visualViewport 事件先後順序。
- `css/category.css`：`.cat-list.cat-off`（max-height 0、無邊框、visibility hidden）、`.cat-gone`（display none）。另修正 `gs-ckm` 註解：免責本來就沒有被隱藏，註解原寫錯。
- `index.html` 資源版本號 `20261005i` → `20261005j`。

### 為什麼非鍵盤的低高度不走 fallback

第一版實作把所有「可用高度 < 44px」都當成 fallback，結果 844×390 橫向、沒有鍵盤時，清單也被收合，而提示卻寫「收起鍵盤」，文字不符合實際狀態。PO 的規格與提示文字都是針對鍵盤開啟的情況，因此 fallback 限定在 `gs-ckm`。沒有鍵盤時，依 PHASE3_PLAN §11.4 把清單保持在最小 44px 並可捲動。

### 測試（`tests/browser/category_test.py`）

- LR-4（844×170，鍵盤開，清單先捲到約 40px）：
  - 清單收合（visibility hidden、高度 0），不強制顯示。
  - 「查看更多」收合。
  - 提示文字正確，位於可視區內。
  - 免責 `.disclaimer` 未被隱藏。
  - 資料夾狀態（sort、shown、scrollTop）與進入 fallback 前完全相同。
  - 搜尋框仍在可視區內。
- LR-4 恢復（放在 LR-9 之後，因為 LR-7 會沿用 LR-4 的焦點狀態）：
  - 提示隱藏，清單恢復為可見且高度 ≥ 44px。
  - 清單捲動位置（約 40px）、sort／shown／scrollTop 保留。
  - 「查看更多」恢復（剩餘 12 檔）。
- 原本的 LR-4 DEFER 已移除。LR-8 維持 DEFER（真機）。

### 已知限制（記錄，未改）

- 844×390 橫向、沒有鍵盤時，分類清單的位置落在底部導覽列下方（清單頂端約 363px，導覽列頂端約 328px）。header 與分類頂部內容佔去大部分高度。清單雖有 44px 最小高度，但需要頁面捲動才看得到。這是 Plan LR-3（清單可用高度 ≥ 110px）尚未達成的版面問題，超出 LR-4 範圍，未修改。需要時再由 PO 決定是否處理。

### 測試結果（headless Chrome，LR-4 修正版）

| 測試 | 結果 |
|---|---|
| `router_test.py` | 64 / 64 PASS |
| `search_compact_test.py`（Phase 1） | 38 / 38 PASS |
| `detail_ui_test.py`（Phase 2） | 42 / 42 PASS |
| `detail_history_fix_test.py`（Phase 2） | 14 / 14 PASS |
| `regression_test.py`（Phase 2） | 14 / 14 PASS |
| `detail_collapse_test.py`（Phase 2） | 25 / 25 PASS |
| `detail_state_test.py` | 42 / 42 PASS |
| `category_test.py`（Phase 3） | 102 PASS，0 FAIL，**1 DEFER**（LR-8 真機） |

LR-4 不再是 DEFER。LR-8 的真機項目不變。

## Blocker：844×390 無鍵盤時分類清單初始可見高度為 0（LR-3 / PHASE3_PLAN §11.4）

Codex 實測：清單頂端約 363px、導覽列頂端約 328px，初始實際可見清單 0px。違反 §11.4「低高度依序讓位，保留至少 44px 實際可見且可捲動的清單」。LR-4 鍵盤 fallback 已 PASS，本次不修改。

### 量測（修正前，844×390，無鍵盤，主動式資料夾）

| 區塊 | 位置（頂端、高度） |
|---|---|
| 頂部 header（標題列＋搜尋） | 0 / 122 |
| 全站免責 `.disclaimer`（Phase 1 法遵） | 122 / 85 |
| 分類頁 `#page-cat`（含 `.page` 頂端間距 14px） | 207 |
| 標題列 | 221 / 46 |
| 持股異動分段 | 267 / 40 |
| 次要標籤列 | 315 / 40 |
| 清單 | 363 / 44（可見 0px） |
| 導覽列 | 328 / 62 |

清單要完整落在導覽列上方（清單底部 ≤ 328），頂端需 ≤ 284。原本需省下約 80px。

### 做法（只在「無鍵盤」且仍不足一列時啟用，第三層讓位）

- **不隱藏免責**：`.disclaimer` 是 Phase 1 法遵呈現，PO 已明確要求保留。
- **頁面頂端間距歸零**（`#page-cat.cat-tight3 { padding-top: 0 }`），省 14px。
- **標題列與持股異動分段併成同一列**（CSS grid：`"head seg" / "strip strip" / "body body"`，DOM 不搬動），分段按鈕 28px。
- **次要標籤列保留一列、40px**（可橫向捲動，觸控高度 40px，與 Plan 的 P4 收合尺寸一致）。
- **「查看更多」移入清單底部**（`.cat-more-in`）。清單外的按鈕會被導覽列蓋住，移入清單後，捲到底即可看到與點擊。`syncInnerMore()` 在 `renderList` 與 `fit` 後同步。外部 `#catMore` 在 `cat-tight3` 下隱藏。
- **清單高度以實際 rect 量測**：`avail(pad)` 以導覽列頂端為下界，`cat-tight3` 時 pad = 4px（其他層仍為 8px）。

結果：清單 277–324px（47px 高），導覽列 328px，不重疊，`elementFromPoint` 命中清單。

### 與 Plan 的偏差（需知道）

- Plan §11.4 建議把次要標籤收合成「其他分類 ▾」按鈕（40px）。本次改為保留 7 個短標籤、一列 40px、可橫向捲動。理由：收合為下拉需要新的互動流程，且在這個高度下收合不會省下高度（標籤列本來就只有一列）。若 PO／Codex 認為需要「其他分類 ▾」，再另行處理。
- 不影響 LR-4 鍵盤 fallback（`kbd` 時不啟用 `cat-tight3`，程式路徑與 LR-4 完全相同）。

### 自動驗收（`category_test.py` BL 區塊，844×390 無鍵盤，以實際 rect 判斷）

| 編號 | 檢查 |
|---|---|
| BL precondition | 無鍵盤、資料夾開啟（主動式）、導覽列可見 |
| BL-1 | 清單與可視區、導覽列以上的交集 ≥ 44px（實測 47px） |
| BL-2 | 清單底部 ≤ 導覽列頂端（不重疊） |
| BL-3 | 可視區中心點 `elementFromPoint` 命中清單、不命中導覽列 |
| BL-4 | 無水平 overflow（document 與分類頁） |
| BL-5 | 進入 `cat-tight3` 版面 |
| BL-6 | 清單可捲動，scrollTop 可移到 ~60px |
| BL-7 | 找到一列在清單可視範圍內 ≥ 22px 的列，`elementFromPoint` 命中該列；**真實滑鼠點擊**開啟對應 Detail；Esc 關閉後資料夾仍開啟，清單捲動保留 |
| BL-8 | 「查看更多」在清單底部，可見、在導覽列上方；點擊後多列出 10 檔 |
| BACK-TO-NORMAL | 直向 390×844 後：`cat-tight3` 移除；清單高度 ≥ 110px；清單內無「查看更多」，外部按鈕回來；sort、shown 保留；無水平 overflow |

LR-4 恢復檢查中的「查看更多」改為同時接受清單內按鈕（`.cat-more-in` 或 `#catMore`）。

### 負向對照

還原 `7b750336` 的 `category.js` 與 `category.css`：BL-1、BL-2、BL-3、BL-5、BL-7、BL-8 FAIL，實測清單 `visH` 0、頂端 363、導覽列 328，與 Codex 的量測一致。修正版全部 PASS。

### 測試結果（headless Chrome）

| 測試 | 結果 |
|---|---|
| `router_test.py` | 64 / 64 PASS |
| `search_compact_test.py`（Phase 1） | 38 / 38 PASS |
| `detail_ui_test.py`（Phase 2） | 42 / 42 PASS |
| `detail_history_fix_test.py`（Phase 2） | 14 / 14 PASS |
| `regression_test.py`（Phase 2） | 14 / 14 PASS |
| `detail_collapse_test.py`（Phase 2） | 25 / 25 PASS |
| `detail_state_test.py` | 42 / 42 PASS |
| `category_test.py` | 120 PASS，0 FAIL，**1 DEFER**（LR-8 真機） |

### 未處理（記錄，非本 blocker）

- **分類「持股異動」檢視在低高度時**：`cat-tight3` 只作用於清單檢視（清單隱藏時不啟用），所以持股異動 treemap 在 844×390 仍落在導覽列下方，需要頁面捲動。本 blocker 只針對清單。
- LR-8：仍待 iPhone Chrome 真機（不變）。

### 版本

- `index.html` 資源版本號 `20261005k`。
