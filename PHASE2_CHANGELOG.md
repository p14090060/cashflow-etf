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

## Android 真機回報修正（第二輪）

依怡恩決定 Q1、Q2 修正：
- **Q1（鍵盤與橫向空間不足）**：詳細頁往下捲超過 4px 時，收起頂部標題、搜尋框與詳細頁標題列（含 ✕）；回到頂部才重新出現。收起期間返回手勢仍可關閉詳細頁。計算機輸入框獲得焦點時會捲到畫面中央。
- **Q2（↻ 重新整理）**：維持現狀，仍會關閉詳細頁。
- 資源版本號 bump 為 `20261004d`。
- 新增 `tests/browser/detail_collapse_test.py`（12 項）。

## Codex 複審 Blocker 修正（收合後歸零閃動）

- **問題**：收合會讓捲動視窗變高；若內容只略超出，收合後 `scrollTop` 被壓回 0，程式又立即展開，形成閃動。實測舊版在略溢出（約 100px）時結果為「未收合、scrollTop=0」。
- **修正**：只有在收合後的最大捲動量仍大於目前位置時才收合（由標題列與頂部高度換算）。展開只看使用者真的回到頂部（`scrollTop <= 0`）。
- 分頁切換與資料刷新後會重新判斷狀態。
- 新增 C7–C10 測試：略溢出不收合且不歸零、明顯溢出收合後位置保留、收合中切到短分頁只展開一次、長內容捲動不閃動。

## 橫向＋鍵盤精簡搜尋模式（compact keyboard mode，取代先前的橫向做法）

依怡恩 2026-10-04 規格（參考微軟遠端桌面的 UX：橫向鍵盤出現 → 優先保留輸入任務 → 非必要 UI 讓位）：
- **進入條件**（全部來自 viewport 狀態，不寫死機型）：裝置橫向（`screen.orientation`）＋搜尋框有焦點＋可視高度低於「搜尋框沒有焦點時」量到的高度的 75%（鍵盤已開）。
- **進入後**：隱藏頂部標題與 ↻、隱藏底部導覽、暫時收起詳細頁；搜尋框捲到最上方、維持全寬；下拉用搜尋列以下的全部可視高度（下限 40px）。
- **離開後**（鍵盤收起、或轉直向）：完整恢復原本版面（含詳細頁）。
- 直向完全不進入此模式，Phase 1 搜尋行為不變。
- 移除先前的 `gs-kb`（頂部 static＋提示列）與 `visualViewport` 平移做法。
- 測試 `tests/browser/search_compact_test.py`（17 項）：橫向無鍵盤不進入；鍵盤開進入、搜尋框寬、第一列在鍵盤上方可見、下拉可用高度；鍵盤收起恢復；直向鍵盤開也不進入。以 Chrome 裝置模擬代替鍵盤。
- 其餘四組測試照常通過（收合 21、互動 42、history 14、迴歸 14）。
- **限制**：Samsung 網際網路的瀏覽器標題列與工具列，加上鍵盤，會佔掉大部分高度。鍵盤開著時，網頁可用高度可能只剩約數十 px，下拉最多只能露出一列。這是瀏覽器本身的限制，網頁無法再縮小它。真機確認後才能定案。

## 真機第 6 項：橫向點搜尋框整頁上移（未解決）

- **問題**：橫向時點頂部搜尋框，鍵盤跳出後整頁往上跑，搜尋框被擋住。直向正常。
- **嘗試**：viewport meta 加上 `interactive-widget=resizes-content`。真機回測無效（畫面與嘗試前相同），已撤回。
- 目前裝置瀏覽器看起來是 Samsung 網際網路，行為與 Chrome 不同，桌面無法重現。
- **第二次嘗試（已撤回）**：以 `visualViewport.offsetTop` 反向平移頂部。真機回測無效，Samsung 網際網路沒有回報平移量。
- **第三次嘗試（待真機確認）**：矮螢幕（高度 < 600px）搜尋框取得焦點時，頂部改為一般捲動（不 sticky），搜尋框捲到畫面最上方；底部導覽暫時收起。原因：鍵盤出現時版面視窗變矮，sticky 頂部會釘住搜尋框使其露不出來。直向不進入此狀態。
- 真機回報：鍵盤開著時，網頁可見區只剩搜尋框一條，下拉結果看不到。
- **B（已採用）**：矮螢幕搜尋時，下拉第一列顯示提示「橫向時螢幕空間不足，收起鍵盤即可看到完整結果，或轉直向搜尋」。提示同樣需要鍵盤收起後才看得到。
- 桌面測試：橫向 9 項、收合 21 項、互動 42 項、history 14 項、迴歸 14 項，共 100 項全數通過。橫向效果需真機回測。
- **未決**：收起鍵盤後底部導覽是否要立即恢復（目前維持收起，直到點到搜尋框以外的地方）。
- **直向誤觸發（已修正）**：真機直向搜尋時出現橫向提示、底部導覽收起。原因：以 `window.innerHeight` 判斷橫向，鍵盤讓視窗變矮，直向也被誤判。改用裝置方向（`screen.orientation`），不受鍵盤影響。
- 測試：搜尋狀態測試以 Chrome 裝置模擬分別設為直向與橫向，確認只在橫向進入狀態；其餘四組測試照常通過。

## 已知限制（依 Rev. 3）

- `est` 與日期的同源判斷由 calendar 欄位推定，market.json 沒有 provenance 欄位。
- 重整後從還原的 Detail 按 ✕，會因跨文件返回而整頁載入一次，不產生幽靈 entry。
- `fetch_etf.py:882-884` 在歷史不足時寫入 `0.0`，前端無法與真實 0% 區分。本 Phase 不改 pipeline。
- 今日頁 A-4 與卡片的 `divPill` 仍會對 `009818` 顯示 90 天 / 0.30（D7，獨立 issue）。
