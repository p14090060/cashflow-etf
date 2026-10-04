# AI_HANDOFF — Claude × Codex 交接本

## 協作協定

- **Claude**：主要 Developer。
- **Codex**：Reviewer / QA。
- 技術交接透過 Git 與本檔進行，不經怡恩轉述。
- Claude 可直接修正 Codex 指出的 bug、regression、資料錯誤、與 Plan 明確不符之處，不需詢問。
- Codex 不得因 coding style 或個人偏好要求重構。
- 需要怡恩的情況（回覆時以 `【需要怡恩】` 標出，並說明需要她決定或操作什麼）：
  - 產品需求需要改變
  - UI/UX 有兩種以上合理方案
  - 新增或刪除功能
  - 修改金融公式、資料來源或 data pipeline
  - Claude 與 Codex 有無法自行解決的實質衝突
  - 需要 Android 真機或 iOS 驗收
- 不需要怡恩時，回覆最後寫 `【不需要怡恩處理｜等待 Codex Review】`。
- 不 push、不進下一個 Phase，除非怡恩明確要求。

## 目前 Checkpoint

| 項目 | 內容 |
|---|---|
| Phase / Task | Phase 2 ETF 詳細頁／Codex review 修正（Round 1） |
| Phase 2 實作 commit | `6033ecb8fd94cf973e97d27c205494c30f26d909` |
| 修正 commit | `bb9d59e68be8da4e3f7fc18bfbd936a0776e1a42` |
| Review 範圍 | `6033ecb8..bb9d59e6`（本檔所在 commit 僅更新本檔） |
| Plan 依據 | `PHASE2_PLAN.md` Rev. 3（GPT Final Gate 核准） |
| Changelog | `PHASE2_CHANGELOG.md` |

## Claude 做了什麼

- **Finding 1（Blocker）**：pending restore 可能在使用者已離開 Detail entry 後被延遲 callback 還原。
  - `_tryRestoreDetail()` 先清除 `_restoreCode`，且只在 `history.state` 仍是同代碼的 `etfDetail` entry 時還原。
  - popstate 開頭一律取消 pending restore。
  - 註：在 Chrome 中，reload 後的 Back 會跨文件返回，本次未能以該路徑重現 Codex 所述的錯配。修正是依 Rev.3 的 history 不變條件補上的防禦性守衛。若 Codex 有可重現步驟，請附在 Review 結果中。
- **Finding 2（Risk）**：Back 關閉 Detail 時同步隱藏 `#gsearchList`（Rev.3 §6.6）。Phase 1 其他搜尋行為未改。
- 瀏覽器回歸測試收入 `tests/browser/`，並補上上述兩項的測試。

## 測試結果

| 測試 | 結果 |
|---|---|
| `tests/browser/detail_ui_test.py` | 42 / 42 PASS |
| `tests/browser/detail_history_fix_test.py` | 14 / 14 PASS |
| `tests/browser/regression_test.py` | 14 / 14 PASS |
| 靜態：殘留 `gsClosePanel` / `gsGoFlow` | 0 筆 |
| 靜態：頂層全域名稱重複宣告 | 無 |
| 執行期未捕捉例外 | 無 |

**執行方式**（從專案根目錄）：
1. `python -m http.server 8765 --bind 127.0.0.1`
2. `chrome --headless=new --remote-debugging-port=9223 --remote-allow-origins=* --user-data-dir=<獨立目錄>`
3. `python tests/browser/detail_ui_test.py`，其餘兩支同理。

測試需要網路以讀取 `raw.githubusercontent.com` 的 market.json。

## Codex Findings / Review Status

| 編號 | 等級 | 狀態 |
|---|---|---|
| F1 pending restore 在基底 entry 被還原 | Blocker | 已修正，待 Codex 複查 |
| F2 Back 關閉 Detail 時下拉未收起 | Risk | 已修正，待 Codex 複查 |

**Ready for Codex re-review.**

## Android 真機驗收（第一輪，測試版本 bb9d59e6）

| # | 項目 | 結果 | 說明 |
|---|---|---|---|
| 1 | 配息頁輸入框 + 鍵盤 | **FAIL** | 鍵盤跳出後詳細頁只剩一小條，輸入框需要滑動才看得到。 |
| 2 | 搜尋下拉 + 鍵盤（詳細頁開著） | PASS | |
| 3 | 返回鍵關閉詳細頁 | PASS | |
| 4 | 返回鍵一次關閉（含分頁切換、下拉收起） | PASS | |
| 5 | 手機重新整理後還原 | PASS | 同一檔詳細頁自動回來。App 內 ↻ 會關閉詳細頁（D4 設計），怡恩尚未決定是否保留。 |
| 6 | 橫向 + 捲動 | **FAIL** | 橫向時詳細頁只剩一點點可視區。 |
| 7 | 四個分頁顯示 | PASS | |

**根因（Claude 判斷）**：頂部標題與搜尋框加上底部導覽列，佔去大部分高度。鍵盤或橫向時，詳細頁可用空間不足。這與 Phase 1 已接受的「橫向可視高度約 190px」已知限制是同一個根因，但詳細頁新增了計算機輸入框，因此變成需要修正的問題。

**待怡恩決定**（需要選擇方案，未修改程式）：
- Q1：詳細頁開著時，頂部區域怎麼處理？
- Q2：↻ 按鈕要保留詳細頁，還是維持目前的關閉行為？

## 尚待處理事項

- Android 真機驗收第二輪（待 Q1、Q2 決定後修正，再由怡恩回測第 1、5、6 項）。
- iOS Safari：未實測，列為 Known Limitation。
- 尚未 push。push 後 GitHub Pages 會直接上線。
- 已知限制（不在本 Phase 修正）：
  - `fetch_etf.py:882-884` 在歷史不足時寫入 `0.0`，前端無法與真實 0% 區分。
  - `est` 與日期的同源判斷由 calendar 欄位推定，market.json 沒有 provenance 欄位。
  - 今日頁 A-4 與卡片的 `divPill` 仍會對 009818 顯示 90 天／0.30（D7，獨立 issue）。
