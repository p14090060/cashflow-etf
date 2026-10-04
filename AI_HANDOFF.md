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
  - 需要真機驗收（主要環境：iPhone + Google Chrome；Samsung + Chrome、iPhone + Safari 為相容性抽測）
- Codex 給怡恩的完成回覆一律使用下方白話格式；取代原先固定的「等待 Codex Review」結尾，避免誤報下一位。
- 不 push、不進下一個 Phase，除非怡恩明確要求。

### Codex 固定溝通規則

- Review 技術內容可以維持專業，但最後給怡恩的回覆必須使用一般使用者看得懂的繁體中文。
- 怡恩不是負責閱讀程式碼的工程師，不得只寫 commit、函式名稱、測試編號或「第 1、6 項」就要求她操作。
- 技術細節放在前面，最後一定翻成白話。回覆保持精簡，但不能省略「我要怎麼做」。

每次工作完成後，固定依序使用以下格式結尾：

**【檢查結果】**

- PASS / NEED FIX。
- 用 1～3 句白話說明發生什麼事。

**【現在需要我做事嗎？】**

- 不需要時明確寫：「不用，你現在不用做任何事。」
- 需要時明確寫：「需要，請你做以下操作。」

**【如果需要我操作】**

需要怡恩操作時，逐步寫清楚：

1. 我要開什麼。
2. 我要點哪裡。
3. 我要輸入什麼（若需要）。
4. 我要觀察什麼。
5. 什麼結果算 PASS。
6. 什麼結果算 FAIL。

不得只寫「測 G1–G3」、「測第 1、6 項」或測試代號，除非同時附上白話操作步驟。不需要操作時可省略此區。

**【下一步】**

- 下一位：Claude / Codex / 怡恩 / GPT。
- 要做什麼：用白話說明。

額外規則：

- 不要把本檔裡的「下一位：Codex」原封不動當成給怡恩的回覆；應依實際完成狀態更新下一步。
- checkpoint 已 PASS 時，不重複 Review 同一個 commit range，除非有新 commit 或怡恩明確要求。
- 下一位是 Claude，且 finding 已寫入本檔時，只告訴怡恩：「請叫 Claude 讀 AI_HANDOFF.md」，不要要求她人工轉述技術內容。
- 下一位是怡恩時，必須提供完整操作步驟；缺少可操作的網址或必要資訊時，先明確說明缺少什麼，不把她留在無法操作的狀態。

## 目前 Checkpoint

| 項目 | 內容 |
|---|---|
| Phase / Task | **Phase 3 ETF 分類瀏覽：Plan Rev.1，待 Codex Review。尚未開始 Coding** |
| Phase 3 Plan | `PHASE3_PLAN.md`（Rev.2）。待 Codex 複審；怡恩決定 D-ESG、D14–D17 |
| 前一階段 | Phase 2 ETF 詳細頁：VERIFIED / CLOSED。Verified baseline（功能程式）`1958cdc0`；封版文件 `74c61106`；已 push |
| 搜尋 Blocker 修正 commit | `1958cdc0`（程式與測試）— Codex 已確認解決 |
| 收合測試條件修正 commit | `82dc1dde`（僅 `detail_collapse_test.py`，產品收合邏輯未改） |
| 本輪 Review 範圍 | `369f3616..82dc1dde`（程式 `1958cdc0`、測試條件 `82dc1dde`；文件 `37ac3784` 僅更新文件）。Codex 上一輪 `d88da242..369f3616` 已完成，結果 NEED FIX |
| 上一個修正 commit | `1ca7cf08` |
| Phase 2 實作 commit | `6033ecb8fd94cf973e97d27c205494c30f26d909` |
| Round 1 修正 commit | `bb9d59e68be8da4e3f7fc18bfbd936a0776e1a42`（Review 範圍 `6033ecb8..bb9d59e6`） |
| Plan 依據 | `PHASE2_PLAN.md` Rev. 3（GPT Final Gate 核准） |
| Changelog | `PHASE2_CHANGELOG.md` |

## 本輪 Blocker：延遲搜尋未在離開 Detail 時取消

**問題**：按搜尋後有 300ms 延遲。若期間按 ✕、按 Back、或點搜尋列以外的地方，舊的延遲請求仍會開啟 Detail，或把下拉重新叫出來。`1ca7cf08` 只補了清除、改查、直接選取、切換分頁四種情況。

**修正**（commit `1958cdc0`，只改下列三處，沒有重構）：
- `closeDetail()` 開頭呼叫 `cancelPendingSearch()`（✕ 與 Esc 都走這裡）。
- popstate（Back）開頭呼叫 `cancelPendingSearch()`。
- 點搜尋列外側的 click 處理呼叫 `cancelPendingSearch()`。
- `index.html` 資源版本號 bump 為 `20261004o`。

**新增回歸測試**：`tests/browser/search_compact_test.py` 的 X5–X8（桌面模擬，以程式直接呼叫送出流程）。

| 編號 | 情境 | 修正前 | 修正後 |
|---|---|---|---|
| X5 | 開著詳細頁，送出 0050，期間呼叫 closeDetail | FAIL | PASS |
| X6 | 開著詳細頁，送出「高股息」，期間呼叫 closeDetail，下拉不得重現 | FAIL | PASS |
| X7 | 送出 0050 期間按 Back，不得開出 0050 詳細頁 | FAIL | PASS |
| X8 | 送出「高股息」期間點搜尋列外側，下拉不得重現 | FAIL | PASS |

**收合測試**：C7、C9 的前置條件修正見下方「測試結果」（commit `82dc1dde`）。

## Round 1 修正（`bb9d59e6`）

- **Finding 1（Blocker）**：pending restore 可能在使用者已離開 Detail entry 後被延遲 callback 還原。
  - `_tryRestoreDetail()` 先清除 `_restoreCode`，且只在 `history.state` 仍是同代碼的 `etfDetail` entry 時還原。
  - popstate 開頭一律取消 pending restore。
  - 註：在 Chrome 中，reload 後的 Back 會跨文件返回，本次未能以該路徑重現 Codex 所述的錯配。修正是依 Rev.3 的 history 不變條件補上的防禦性守衛。若 Codex 有可重現步驟，請附在 Review 結果中。
- **Finding 2（Risk）**：Back 關閉 Detail 時同步隱藏 `#gsearchList`（Rev.3 §6.6）。Phase 1 其他搜尋行為未改。
- 瀏覽器回歸測試收入 `tests/browser/`，並補上上述兩項的測試。

## 測試結果

| 測試 | 結果 |
|---|---|
| `tests/browser/search_compact_test.py` | 38 / 38 PASS（含本輪 X5–X8；修正前 X5–X8 為 FAIL） |
| `tests/browser/detail_ui_test.py` | 42 / 42 PASS |
| `tests/browser/detail_history_fix_test.py` | 14 / 14 PASS |
| `tests/browser/regression_test.py` | 14 / 14 PASS |
| `tests/browser/detail_collapse_test.py` | 25 / 25 PASS（固定 390×844，連跑兩次結果相同） |

**收合測試 C7、C9：已修正測試條件（產品收合邏輯未改）**
- **原因一（視窗）**：測試未固定視窗尺寸。headless 預設約 764×485，此時 0050 總覽超出視窗 217px，C7「略微溢出 100px」的前置條件不成立。
- **原因二（spacer 算式）**：測試用 `scrollHeight − clientHeight` 計算溢出，但內容比視窗矮時這個值會被夾成 0，spacer 只加了 100px，溢出仍是 0。改為量內容實際高度（497px）再計算 spacer；校正一次後溢出為 100px。
- **更正我先前的說法**：我前一輪推測是即時 `market.json` 變動所致。該推測錯誤，已撤回。
- **C9**：切換前先量總覽內容是否放得進展開（659px ≤ 659px）與收合（659px ≤ 781px）後的視窗，前置條件不成立時直接 FAIL。
- **量測證據（390×844 直向）**：總覽 scrollHeight 659 = clientHeight 659（無溢出）；持股配息 scrollHeight 821、clientHeight 659（溢出 162px）；C7 校正後溢出 100px；C9 切到總覽後未收合、scrollTop 0。
- **未重跑其他四組**：本輪只改收合測試檔，產品程式沒有變動。
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
| 延遲搜尋：✕／Back／點搜尋列外側未取消（Codex 上一輪 NEED FIX） | Blocker | 已解決（`1958cdc0`），Codex 已確認 |
| 收合測試 C7、C9 前置條件未成立（未固定視窗、spacer 算式錯誤） | QA | 已修正測試條件（`82dc1dde`），待 Codex 複審 |

**Ready for Codex re-review**（範圍 `369f3616..82dc1dde`）。

## 真機環境更正（怡恩 2026-10-04）

- 今天實際真機測試的環境是 **iPhone + iOS + Google Chrome**，不是 Samsung／Android。
- 文件中原本標為 Android、Samsung 的真機紀錄是誤歸類，已改寫為 iPhone + Chrome 的紀錄。若某一輪實際不是這台手機，請怡恩指出，再更正。
- 今天量到的 `innerHeight` 20 → 276，以及「0050 → 按鍵盤搜尋 → 鍵盤收起 → Detail 開啟 PASS」，都是 iPhone + Chrome 真機結果。
- 先前依 Samsung 瀏覽器推論的「標題列與工具列佔掉大部分高度」，尚未在 iPhone 上驗證，視為待確認，不是已證實的原因。
- 今後 QA 矩陣：
  1. **iPhone + Chrome**：主要驗收環境。
  2. **iPhone + Safari**：相容性抽測，只測首頁、搜尋與鍵盤、直橫向、Detail、返回。
  3. **Samsung + Chrome**：相容性抽測，同樣只測關鍵流程。
- QA 紀錄不得從截圖或上下文推測裝置、OS 或瀏覽器。只有怡恩明確確認的環境，才能標記為真機 PASS。

## 真機驗收（第一輪，測試版本 bb9d59e6）

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

## 真機驗收第二輪（修正 commit `0c679655`）

| 項目 | 狀態 |
|---|---|
| Q1：詳細頁往下捲時收起頂部區域，回到頂部再出現 | 已實作，待怡恩回測 |
| Q2：↻ 維持關閉詳細頁 | 維持現狀，不需修改 |
| 第 1 項（配息輸入框 + 鍵盤） | 已修正，待怡恩回測 |
| 第 6 項（橫向 + 捲動） | 已修正，待怡恩回測 |
| 第 5 項（重整後還原） | 不變（PASS），↻ 行為依 Q2 維持 |

**驗證**：桌面瀏覽器測試共 82 項全數通過（收合 12、互動 42、history 14、迴歸 14）。鍵盤與橫向只能由真機確認。

**已知取捨**：收起期間 ✕ 按鈕也暫時看不到，返回手勢仍可關閉詳細頁。

**Ready for Codex re-review**（範圍 `7a7831c8..0c679655`）。

## Codex 複審結果（收合修正）與 Claude 修正（commit `9ece2c6d`）

| 項目 | 狀態 |
|---|---|
| Blocker：收合後 scrollTop 被壓回 0，立即展開造成閃動 | 已修正。收合前檢查收合後仍在範圍內；展開只看真的回到頂部 |
| Blocker 測試缺口（略溢出、切短分頁） | 已補 C7–C10，並以舊版邏輯重現（舊版：未收合、scrollTop=0） |
| Risk：鍵盤與橫向需真機回測 | 仍待怡恩回測第 1、6 項 |

**驗證**：桌面瀏覽器測試共 91 項全數通過（收合 21、互動 42、history 14、迴歸 14）。

**Ready for Codex re-review**（範圍 `6bf51c54..9ece2c6d`）。

## iPhone + Google Chrome 真機回測（怡恩，測試版本 `b5af04c3`）

環境：怡恩確認為 **iPhone + iOS + Google Chrome**（iOS／Chrome 版本號未提供，未記錄）。測試網址為 `http://192.168.68.52:8080/index.html?r=b5af04c3`（HEAD `b5af04c3` 匯出，區網服務）。

| # | 項目 | 結果 |
|---|---|---|
| 1 | 直向搜尋 0050 → 點結果開 Detail → ✕ 關閉 | **PASS** |
| 2 | Detail 開著按返回 → 關閉，搜尋下拉不殘留 | **PASS** |
| 3 | 橫向＋鍵盤輸入 0050 → 按「搜尋」→ 鍵盤收起 → Detail 開啟 | **PASS** |
| 4 | 橫向＋鍵盤輸入「高股息」→ 按「搜尋」→ 鍵盤收起 → 列表顯示、不開 Detail | **PASS** |
| 5 | 直向 Detail 配息頁 → 點股數輸入框 → 輸入框在鍵盤上方可見、結果可讀（原第 1 項） | **PASS** |
| 6 | 橫向 Detail 捲動 → 收起／回頂部恢復，無閃動（原第 6 項） | **PASS** |

- 延遲取消（✕／返回／點外側）的 300ms 競態無法手動精準重現，由桌面自動測試 X5–X8 涵蓋；真機只確認主流程。
- 本次回測屬於 iPhone + Chrome。**不代表** Samsung + Chrome 或 iPhone + Safari 的結果。

## 最終相容性驗收（GPT Gate 彙整，2026-10-04）

| 環境 | 結果 | 說明 |
|---|---|---|
| iPhone + iOS + Google Chrome | **6/6 PASS** | 上表 1–6 項 |
| iPhone + Safari | **3/3 PASS** | 相容性抽測，關鍵流程 |
| Samsung + Google Chrome | **3/3 PASS** | 相容性抽測，關鍵流程；橫向＋鍵盤搜尋正常，0050 搜尋送出與 Detail 流程 PASS |

**Observation（不列 Blocker，未修改程式）**：iPhone + Safari 首次開啟時曾觀察到約 3 秒捲動延遲。重新進入 Detail 後，「立即滑動」與「等待 5 秒後滑動」皆無法重現。

## Phase 3 Plan（Rev.2，待 Codex 複審）

- 需求來源：怡恩 2026-10-04 Phase 3 需求；Codex Rev.1 Review（NEED FIX）；怡恩 Rev.2 產品決策。本階段只修 Plan 與交接本，**未修改程式、未開始 Coding、未 push**。
- 文件：`PHASE3_PLAN.md`（Rev.2）。

**Rev.2 主要修訂**
- 導覽固定為 **首頁／分類／自選／工具**（不新增第 5、第 6 個主導覽）。既有功能遷移：配息與排行 → 工具；主動持股異動 → 分類 → 主動式；YouTube 頻道 → 工具底部連結與首頁小入口。Phase 3 不刪除既有功能。
- 分類維持單一歸屬；高股息資料夾 22 檔與搜尋「高股息」76 檔可共存；資料夾說明用「主要以高股息策略為特色的 ETF」。
- 分類優先例外依怡恩決定：科技＋高息→科技、海外＋高息→海外、AI 機器人與航太防衛→科技、金融／工業／數位支付→主題型、0057 暫歸其他／待查證。
- ESG 規則依怡恩意見：不因名稱有 ESG 就強制歸其他。00920 → 主題型；00923、009809 → 市值型（**待怡恩確認**）。
- **history 改為單一 router**：所有 pushState／replaceState／back 集中在 `js/router.js`；popstate 只有一個 listener，只渲染、不呼叫 back；每層一個 entry；E0 唯一；busy 鎖。Phase 2 Detail 的 history 程式會搬到 router 下（Rev.1 的「只 hook」是錯的，已更正）。
- 測試涵蓋 Codex 指定情境：Browser Forward、Detail reload、Detail 開著切換導覽、Esc 只退一層、返回資料夾後的排序／已展開數／捲動位置、不產生重複基底 entry。
- Responsive 改依實際剩餘可用高度（扣除頁首、標題、次要區、導覽、安全區域）驗證，並列出 390×844、360×780、844×390、844×170、844×20 等情境。
- 補上：開啟期間資料更新、移類、消失、成功後更新、更新失敗保留 last-good、reduced-motion、空分類與錯誤狀態、203 檔固定 fixture 測試。數字只作為 fixture 的 assertion，不作永久 assertion。

**目前資料分布（Rev.2 推薦預設，203 檔）**
市值型 18、高股息 22、主動式 32、科技／半導體 20、海外／區域 78、主題型 19、債券 6、其他 8（合計 203）。

- 與 Gavin 引用的 16／22／32／20／78／18／6／11 不同，差異來自 ESG 規則（00920、00923、009809）。若要保留舊數字，見 D-ESG。

**需要怡恩決定（Plan 第 16.2 節）**
- D-ESG（三檔歸類）、D14（自選占位）、D15（↻ 行為）、D11（桌機版型）、D12（重整還原）、D13（排序是否記憶）、D16（首頁標籤）、D17（持股異動入口）。

**下一步**
- Codex 複審 `PHASE3_PLAN.md` Rev.2。重點：router 設計（第 7 節）、RT 測試清單（第 14.5 節）、responsive 公式（第 9 節）、遷移表（第 1.2 節）。
- 怡恩決定 D-ESG 與 D14–D17 後，才開始 Coding。

## Phase 2 封版狀態

- **Phase 2：VERIFIED / CLOSED**（GPT Gate 通過）。Verified baseline（功能程式）：`1958cdc0`。
- Codex 複審 `369f3616..b5af04c3`：PASS。
- 真機驗收：iPhone + Chrome 6/6、iPhone + Safari 3/3、Samsung + Chrome 3/3，皆 PASS。
- Observation（iPhone + Safari 首次捲動約 3 秒延遲，未重現）：不列 Bug，不修改程式。
- **Known UX limitation**：iPhone + Chrome 橫向鍵盤開啟時，可用 viewport 可能極小（實測約 20px）。搜尋送出、收鍵盤、進 Detail 均正常。同一支 iPhone 橫向鍵盤環境下，Safari 可用畫面明顯比 Chrome 充裕。此項不 hardcode 20px，Phase 2 功能不再修改。
- Samsung + Chrome 橫向鍵盤顯示正常，搜尋框與結果均可使用。
- 本次封版不修改功能程式、不重構、不處理 1px 等外觀細節。
- **Phase 3 尚未開始**，等待產品決策。
- 文件中仍有 Android 字樣的位置（PHASE1_CHANGELOG.md、PHASE2_PLAN.md 的測試代號）尚未更正，是否更正由怡恩決定。
- 尚未 push。push 後 GitHub Pages 會直接上線。
- 已知限制（不在本 Phase 修正）：
  - `fetch_etf.py:882-884` 在歷史不足時寫入 `0.0`，前端無法與真實 0% 區分。
  - `est` 與日期的同源判斷由 calendar 欄位推定，market.json 沒有 provenance 欄位。
  - 今日頁 A-4 與卡片的 `divPill` 仍會對 009818 顯示 90 天／0.30（D7，獨立 issue）。
