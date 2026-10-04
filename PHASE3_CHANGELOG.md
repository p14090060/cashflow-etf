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
