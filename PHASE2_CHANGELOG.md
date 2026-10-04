# Phase 2 CHANGELOG — ETF 詳細頁

依據：`PHASE2_PLAN.md` Rev. 3（GPT 最終 Gate：APPROVE FOR CODING）。
基準：`89e6641a`（Phase 1 Verified baseline）。

## 新增

- `js/detail.js`：ETF 詳細頁。總覽／配息／績效／成分四個 tab。
  - 配息判定（`_dvView`）：官方有效 → 官方過期 → 不配息 → 待公告 → 推算有效 → 推算過期 → 資料不足，依序命中。
  - 單次試算只在官方金額，或 `est` 與日期可確認同源時啟用；計算機使用獨立 DOM id（`#dtSharesIn` / `#dtCalcOut`）。
  - History：`openDetail` / `closeDetail`（idempotent，每次開啟最多一次 `history.back()`）、popstate 不呼叫 back、`event.state === null` 安全處理、重整後還原 Detail。
  - 刷新採 slot patching：市場資料與 flow 完成時只更新內容，不重建骨架與股數輸入框。

## 修改

- `js/calc.js`：新增 `CALENDAR` 全域。
- `js/render.js`：`renderAll()` 寫入 `CALENDAR`，尾端呼叫 `detailOnMarketUpdate()`。
- `js/flow.js`：新增 `_flowStatus`（loading / ok / failed），`fetchFlow()` 完成時通知 Detail。
- `js/boot.js`：↻ 改 `location.replace`（不再每次新增 history entry）；讀取重整前的 history 標記；資料失敗時觸發還原。
- `js/nav.js`：`switchPage()` 開頭關閉 Detail。
- `js/search.js`：選取改為 `openDetail`；打字不再關閉 Detail（D2）；Esc 改接 `closeDetail`；移除 `gsClosePanel` / `gsGoFlow`。
- `index.html`：✕ 按鈕改接 `closeDetail()`；載入 `detail.js`；版本號 bump 為 `20261004c`。
- `css/components.css`：`.dt-*` 詳細頁樣式。
- `css/base.css`、`js/search.js`：過時註解更新。

## 刻意與計畫不同之處

無。所有實作依 Rev. 3。

## 驗證（開發環境，無頭 Chrome + DevTools 協定）

- 靜態：殘留 `gsClosePanel` / `gsGoFlow` 引用 0 筆；全域頂層名稱無重複宣告。
- 互動測試 42 項全數通過（配息判定、History 單次返回、Esc／✕／導覽／成分跳轉的重複 close、重整還原、計算機股數保留、0.0% 顯示、官方過期與推算過期的記憶體內假日期）。
- 迴歸 15 項全數通過（五個分頁切換、配息頁晶片計算機、排行頁搜尋、主動頁 treemap、搜尋下拉）。
- 兩組測試執行期間 Console 無未捕捉例外。

## 未在開發環境驗證

- Android 真機：手機鍵盤與 `visualViewport`、手勢返回、重整還原的實際畫面（G1–G3）。
- iOS Safari：未實測，列為 Known Limitation。

## Review 修正（Codex review of `6033ecb8`）

- **Finding 1（Blocker）**：pending restore 可能在使用者已離開 Detail entry 後仍被延遲的 market／error callback 還原，造成 History 配對錯誤。
  - `_tryRestoreDetail()` 先清除 `_restoreCode`，只有在 `history.state` 仍是同代碼的 `etfDetail` entry 時才還原。
  - popstate 開頭一律取消 pending restore。
  - 補測：pending restore 遇基底 entry 不開啟；popstate 取消 pending restore；真實 reload 後立即 Back 不留下 Detail。
  - 註：Chrome 中 reload 後的 Back 會跨文件返回，舊文件的 pending 狀態隨之消失，本次未能以該路徑重現錯配。修正為 state 不變條件的防禦性守衛。
- **Finding 2（Risk）**：Back 關閉 Detail 時搜尋下拉未收起。
  - popstate 關閉 Detail 的分支同步隱藏 `#gsearchList`（Rev.3 §6.6）。
  - 補測：Back 同時收起 Detail 與下拉，且只產生一次 popstate。
- 瀏覽器測試腳本收入 `tests/browser/`，可由專案根目錄重跑（見 AI_HANDOFF.md）。

## 已知限制（依 Rev. 3）

- `est` 與日期的同源判斷由 calendar 欄位推定，market.json 沒有 provenance 欄位。
- 重整後從還原的 Detail 按 ✕，會因跨文件返回而整頁載入一次，不產生幽靈 entry。
- `fetch_etf.py:882-884` 在歷史不足時寫入 `0.0`，前端無法與真實 0% 區分。本 Phase 不改 pipeline。
- 今日頁 A-4 與卡片的 `divPill` 仍會對 `009818` 顯示 90 天 / 0.30（D7，獨立 issue）。
