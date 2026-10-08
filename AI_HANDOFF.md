# AI_HANDOFF — Claude × Codex 交接本

## 0. 目前唯一有效狀態（Compact 後先讀這一節）

**Phase 3、Phase 4 已 VERIFIED / CLOSED（2026-10-05；baseline 分別為 `82ce3ee9`、`edb065d2`）。** Compact 後先讀本節；Phase 5 已完成 GPT Gate 決策（見「Phase 5 — GPT Gate 決策」），尚未寫 Plan、未 coding。§0.5 以下為 Phase 3 的過程紀錄。

### 0.1 專案與階段

- 專案：ETF 存股雷達（`c:\專案\etf`）。靜態 PWA，部署於 GitHub Pages。傳統 `<script>`，無 build，無框架。
- Phase 0–2：已完成（由 Product Owner 確認）。
- **Phase 2：VERIFIED / CLOSED。** Verified functional baseline：`1958cdc0`。封版文件：`74c61106`。已 push。
- **Phase 3 Plan：Rev.3.3，commit `8326f465`。** Codex 最終結論：**PASS FOR CODING AFTER PRODUCT DECISIONS**。
- **Phase 3 Resync blocker：RESOLVED**（Rev.3.3 已通過）。
- **Phase 3：VERIFIED / CLOSED（2026-10-05）**，見下方 `82ce3ee9` 一項。（歷史：Phase 3 曾為 APPROVED FOR CODING。）
- **Phase 3 Coding commit：`99ec4b14`。** Codex 複審結果：**NEED FIX**（三項必修）。
- **Phase 3 必修修正 commit：`8e3e59bb`。** 本機，尚未 push。Codex 複審 `99ec4b14..8e3e59bb`：Finding 2（flow visualViewport）與 Finding 3（LR-8）RESOLVED；唯一待修 Finding 1 已在後續 fix commit 修正（見下）。
- **Phase 3 Finding 1 fix commit：`c050c719`**（本機，未 push）。Detail scroll 被分類 snapshot 覆蓋；修正內容見 `PHASE3_CHANGELOG.md` 的「Codex 複審 Finding 1 修正」一節。
- **Phase 3 LR-4 responsive fallback commit：`7b750336`**（本機，未 push）。**Codex 唯讀確認：LR-4 PASS / CLOSED。不再修改。**
- **Phase 3 844×390 無鍵盤 blocker fix commit：`1f636d86`**（本機，未 push）。LR-3／§11.4：清單初始實際可見 ≥ 44px、不被導覽列遮住。內容見 `PHASE3_CHANGELOG.md` 的「Blocker：844×390 無鍵盤時分類清單初始可見高度為 0」一節。
- **Phase 3 直向 inside／doorway commit：`fdc1d139`**（本機，未 push）。PO 真機回饋後的 UX 調整（Gate 核准）：進入分類後其他分類立即收合，主 TAB 的 ▾／▴ 重新展開。內容見 `PHASE3_CHANGELOG.md` 的「直向 inside／doorway」一節。**Codex PASS。**
- **Phase 3 真機 Bug fix commit：`3be2d19c`**（本機，未 push）。visualViewport 縮短時的底部錨定。**Codex PASS。** 真機重測後，此修正保留，另有下一項（`1418695a`）。
- **Phase 3 renderList 重建保留位置 fix commit：`1418695a`**（本機，未 push）。真機重測 PASS（Detail × 關閉、停留跨輪詢、中段位置、查看更多 +10）。**Codex PASS。**
- **Phase 3 UX-1／UX-2 commit：`395c774e`**。UX-1：金色提醒與分類內容之間的空白（31px → 15px）。UX-2：「切換分類 ▼／▲」按鈕（說明列，99×44）。內容見 `PHASE3_CHANGELOG.md` 的「UX-1、UX-2 小修」一節。**Codex 複審 `1418695a..395c774e`：PASS**（UX-1、UX-2、長名稱／小螢幕、Accessibility、Regression 皆 PASS；category 186 PASS、0 FAIL、1 DEFER（LR-8））。
- **Push 狀態（2026-10-05 確認）**：`395c774e`（程式）與 `ca262607`（handoff）已在 `origin/main`。研判是後續本機自動行情排程推送 main 時一併帶上去。**PO 已接受，不需 rollback**；GitHub Pages 已是 Phase 3 版本。
- **Phase 3 B6 警示條輕量化 commit：`ec2eec09`**。**Codex 複審 `395c774e..ec2eec09`：PASS，checkpoint 關閉，不再修改或重審。**
- **Phase 3 文件夾說明／藏字 commit：`3bde9239`**。**Codex 唯讀複審：PASS，checkpoint 關閉。**
- **⚠ SHA 被自動排程改寫**：本機行情排程會先 `pull --rebase` 再推，所以尚未推上去的本機 commit 會換成新的 SHA（程式內容不變，只有 `data/` 不同）。已發生：`ec2eec09` → **`a9f99081`**（B6）、`3bde9239` → **`51677d06`**（文件夾）。之後請以 commit 訊息和 `git log` 為準，舊 SHA 雖然還查得到，但已不在 main 上。
- **Phase 3 ESG 分類＋inside 標題列 commit：`82ce3ee9`**（原 `88ad38cb`，被自動排程改寫；對應 handoff 原 `e66844a1` → `aeab5fa2`）。**Codex 唯讀複審：PASS。**
- **Phase 3：VERIFIED / CLOSED（2026-10-05）。** Verified baseline（功能程式）：**`82ce3ee9`**。已在 `origin/main`，GitHub Pages 已上線。
  - Codex：各 checkpoint 皆 PASS（UX-1／UX-2 `395c774e`、B6 `a9f99081`、文件夾 `51677d06`、ESG＋標題列 `82ce3ee9`）。
  - 真機驗收（iPhone + Google Chrome，PO 執行）：步驟 1～5 PASS（警示條、8 份文件夾的名稱／檔數／說明、堆疊與無藏字、科技／半導體）；步驟 6～16 PASS（overview → inside → doorway → 切換分類、▼／▲、inside 不重複說明、← 返回、D4 查看更多 → Detail → × 返回、橫向準備）；**LR-8 真機補驗 PASS**（橫向鍵盤開啟時搜尋框可見、收起後恢復）。自動測試中的 LR-8 DEFER 由這次真機結果取代。
  - **真機 Observation（不修正，屬瀏覽器環境差異）**：iPhone Chrome 橫向時，瀏覽器 UI 收合或展開會讓可用 viewport 高度明顯不同。UI 展開且鍵盤開啟時，可用高度會大幅縮小，此時 low-height fallback「收起鍵盤以查看 ETF 清單」運作正常；鍵盤收起後畫面正常恢復。PO 決定不再修改 CSS 或 Category 邏輯。
  - 仍有效的 Observation（不阻擋封版）：§0.7 的 Known Observation（清單剛好放得下時縮短，「查看更多」被裁約 16px；真機未造成問題）、0057 富邦摩台、低高度橫向的持股異動 treemap。
  - **Phase 4 尚未開始 coding。**
- **Phase 4 Plan：Rev.2.1，Codex PASS；PO／Gate D1～D6 已決議（commit `df5d5072`）。**
- **Phase 4 Coding commit：`b78134c1`**（本機，未手動 push；自動排程推送時 SHA 可能被改寫，commit 訊息開頭「feat(phase4): 我的 ETF（自選）」）。**Codex Code Review：NEED FIX。下一位：Claude｜修正下方三項實際 bug（見「Phase 4 Implementation — Codex Code Review」）。** Phase 4 尚未完成，修正複審後才交 PO 真機驗收。
- **Phase 4 Code Review 修正 commit：`6d2d9a3d`**（本機，未手動 push；推送後 SHA 可能被改寫，訊息開頭「fix(phase4): Codex Code Review 三項」）。Codex 複審：**NEED FIX，僅剩選單高度補償被誤算為拖曳門檻的問題**（見「Phase 4 6d2d9a3d — Codex 複審」）。下一位：Claude；尚未交真機驗收。
- **Phase 4 拖曳門檻修正 commit：`5df1cb50`**。**Codex 複審 PASS，Phase 4 Code Review 完成。** PO 真機驗收步驟 1～21 PASS，步驟 21 後因拖曳手感 UX 暫停（22～34 未測）。
- **Phase 4 拖曳手感修正 commit：`76252269`**（本機，未手動 push；訊息開頭「fix(phase4): 拖曳手感」）。Codex Code Review：**NEED FIX，兩項按住計時交界 bug**（見下方「76252269 — Codex Code Review」）。下一位：Claude；修正複審 PASS 後才由 PO 重測拖曳、接續後面的真機驗收。
- **Phase 4 按住計時交界修正 commit：`ba3070f3`**。**Codex 複審 PASS。**
- **PO iPhone Chrome 主驗收（2026-10-05）**：拖曳 UX 重測 R1～R11 全部 PASS；原 QA 1～24、26～33 PASS（28、29 Active Flow PASS）；25 N/A（績效內容高度不足，無法觸發標題列收合）；34 未測（選做 VoiceOver）。Samsung Chrome 抽測尚未執行。
- **Phase 5 待辦（PO 決定，Phase 4 不改）**：直向「持股異動」檢視仍使用展開的分類標籤列，而非「切換分類 ▼／▲」。經查為 Phase 3 既有設計（`ctlActive()` 限 `view === 'list'`，baseline `82ce3ee9` 起即如此，category_test 明文驗證），屬兩套 UI 尚未統一，移至 Phase 5 UX 統一。
- **Phase 4 收尾：拖曳底部邊界 commit：`edb065d2`**。Codex Code Review PASS；底部拖曳修正後真機重測 PASS。
- **Phase 4：VERIFIED / CLOSED（2026-10-05）。** 功能 baseline：**`edb065d2`**（之後若只有文件 commit，不重開 Phase 4）。iPhone Chrome 主要 QA、拖曳 R1～R11、Active Flow 真機測試完成；**Samsung Chrome S1～S8 全部 PASS**；25 N/A（內容高度不足以觸發收合）、34 選做未測。不需補測、不豁免、不再審查。
  - 產品需求已由 PO／GPT Gate 確認（自選／我的 ETF：♡ 收藏、自選大卡、近半年走勢 6 柱、台股漲紅跌綠、⠿ 拖曳排序、取消後可復原、引導式空狀態、localStorage only）。Plan 不重議需求。
  - 已標示的架構衝突（Plan §1）：C1 分類列是 `<button>`，無法內嵌 ♡ 按鈕 → 改為容器＋兩個並列按鈕；C2 `miniBars` 會把 0 畫成紅色且顏色寫死 → 新增選項參數，只有自選卡生效；C3 站上沒有淺色主題；C5 Detail 標題列捲動時會收合。
  - 待 PO／Gate 確認的做法（Plan §11 D1～D6）：miniBars 的 0 是否全站改中性、淺色主題、Detail ♡ 位置、Toast 規則、替代排序、頁面標題。
  - Codex 審查後若 NEED FIX，由 Claude 修改 Plan；PASS 並經 Gate 確認 D1～D6 後才開始 coding。

### Phase 4 Rev.1 — Codex Plan Review（2026-10-05）：NEED FIX

本輪只審 `PHASE4_PLAN.md` Rev.1 與目前程式／資料，未開始 coding。以下為必要的 Plan 補強；不要求重構 Router、Detail、Flow 或資料 pipeline。D1～D6 尚未替 PO 決定。下一位：Claude，修 Plan 後交 Codex 複審，再交 PO／GPT Gate。

1. **既有測試與 Detail 收藏整合（Plan §3、§10.3）**
   - C1「容器＋兩個並列 button」方向正確；現有 Category 委派先命中 `.cat-row`，實作必須改成先收藏、再主區，維持 Enter／Space 開 Detail 與獨立收藏。
   - 不只 `category_test.py` 要遷移：`detail_state_test.py` 也直接對 `.cat-row[data-code]` 呼叫 click；`detail_ui_test.py`、`detail_history_fix_test.py`、`detail_state_test.py`、`category_test.py` 都以 `#gsPanel .gs-panel-hd button` 的第一個 button 當作 X。依 Plan 把 ♡ 插在 X 前面後，這些測試會改點收藏。請列出完整遷移範圍，使用明確的關閉控制選擇器，不放寬原 history／scroll assertions。
   - 補測 Detail 點 ♡ 不關面板、不 push／replace、不改 tab／scroll／計算機輸入；換 ETF、Back／Forward、missing ETF 時收藏與 accessible name 都正確。`detailPatch()` 的 `!e` 分支有 early return，收藏更新應位於該 return 前或使用獨立同步函式。新增 Watch scripts 的順序需明確：store 在使用者之前，Watch UI／Toast 初始化在 bootstrap 與訂閱回呼需要它們之前。

2. **跨分頁／拖曳／復原的狀態交界（Plan §2、§4、§7）**
   - `storage` 同步可能在拖曳期間改變清單；只延後 `Watch.refresh()` 的行情更新不足以保護 `move(from,to)`。例：拖 B 時另一頁刪 A，索引位移後放手可能移到 C。請規定收藏增刪／storage 同步時取消拖曳或重新依 code 規劃，不以舊索引覆寫新順序，並補測。
   - `restore` 也必須去重／冪等：移除後五秒內，該 code 在另一入口或分頁重新加入，再按復原，不能重複或把已存在的收藏搬走。原位置 index 夾限的既定方案可保留；補測期間新增／刪除、清單縮短與連續移除，明確說明中途重新排序時採用的 index 規則。
   - `storage` 回呼只同步，不回寫形成通知循環；`move`、整份 storage 同步也必須通知 Watch 更新順序（通知不能只涵蓋某 code 的 ♡）。持久化失敗後保留本次記憶體狀態，勿被舊 localStorage 重讀覆蓋。寫入失敗不代表舊持久化收藏已清空；提示應說本次變更重新整理後可能遺失／回到先前保存內容，而不是保證全部清空。補讀失敗、寫失敗、失敗後同步與 reload 測試；不要求跨分頁原子交易系統。

3. **拖曳自動捲動與終止（Plan §7、DR 測試）**
   - 自動捲動會在 pointer 不動時改變卡片 rect；請明確使用同一座標系處理 pointer、visualViewport.offsetTop 與卡片位置，捲動每幀也重算目的位置／拖曳位移，避免只在 pointermove 更新。
   - pointerup／cancel／lostpointercapture、離開自選頁或開 Detail 時，清除 capture、transform 與自動捲動迴圈；cancel 不保存排序，延後行情更新也要收尾。鍵盤排序防止箭頭同時捲頁，重排後焦點保留在同一檔把手。
   - 補測 10 檔上下緣連續拖曳、頁面已有 scroll、低高度／offset viewport、cancel 後停止捲動、拖曳中導航、連續鍵盤排序。真機才能生成的 viewport 條件照實 DEFER，不以 stub 當真機 PASS。

4. **Active Flow 明確保留與驗收（Plan §8、§10）**
   - 「不改 flow.js」是正確邊界，但 §10 只有列舊 suite 總數，沒有保護持股異動紅／綠語意的明確 assertion。請列為不可刪除、弱化、重做或由一般成分清單替代的功能。
   - 加入分類 → 主動式 → 持股異動、Detail → 查看完整持股異動及 Back／Forward；保持 treemap 與海外無報價增減股數列表，正值紅加碼／負值綠減碼。依 `flow.js` `_renderNoPrice` 與 `renderFlow`，驗證實際 computed 色彩／文字（不是只檢查 class）。
   - 保留 fetched=false／舊資料／無異動／海外無報價語意，以及已存在 FD-1～FD-6 resize／visualViewport 重繪驗收。收藏或自選重繪不得重設 Flow 選取與顯示；不要求修改 Flow 實作。

**已確認可行**：`data/market.json` 203 檔都有 price、change_pt、change_pct、div_frequency、signal 與六段 ret_months；`fetch_etf.py` 由舊到新產生六段，Detail 已說明每段約 22 交易日。miniBars 新參數維持原預設，可局部實現紅漲綠跌、0 中性、null 缺值。Router 已有 watch base，Category／Detail／Watch 共用 Store、不另建 history 系統可行。

**D1～D6 技術意見（不代 PO 決定）**：D1 局部修 0 可接受；D2 不增加 light theme 可接受；D3 標題列可接受，需上述控制／收合回歸；D4 最近一次＋5 秒可接受，需上述冪等與中途排序規則；D5 Pointer＋鍵盤可實作，但只有鍵盤替代對手機 VoiceOver／無外接鍵盤使用者不充分，請 Gate 確認此可用性取捨或採可操作的無拖曳替代；D6「我的自選」可接受。這些選項本身不要求現在 coding。

### Phase 4 Rev.2 — 修訂內容（Claude，2026-10-05）：交 Codex 複審

只修 Plan，未 coding。對應 Rev.1 NEED FIX 四項（Plan 開頭有對照摘要）：

1. **既有測試與 Detail 收藏整合**：§3.1 委派順序改為 `.fav-btn` → `.cr-main` → 其餘既有分支，Enter／Space 各自觸發；§3.2 ✕ 加 `id="dtClose"`，新增 `_dtSyncFav()`，在 `detailPatch()` 的 `!e` early return **之前**呼叫，點 ♡ 不碰 Router／tab／scroll／計算機；§10.3 列出**完整**遷移表（category 125、133、464、552、466、554；detail_state 93、108；detail_ui 112、157、178、192；detail_history_fix 56；`.cat-row` 計數類不變），實作前重掃；§8.1 script 順序：`watch-store.js` 在 category／detail 之前，`watch.js`（含 Toast）在 detail 之後、router／boot 之前，載入即 init；新增 DF-1～DF-6。
2. **跨分頁／拖曳／復原**：§2.5 通知型別（`move`／`sync` 全體重同步）、storage 只同步不回寫、寫入失敗後不被舊資料覆蓋、提示改為「這次的變更無法保存，重新整理後可能回到先前保存的內容」；§2.6 `restore` 冪等（已存在則不動）＋ `min(index, 長度)` 夾限；§7.4 拖曳中任何清單通知即取消拖曳，放下以 `moveCode(code, beforeCode)` 規劃，不用舊索引；新增 ST-5～ST-9、UN-4～UN-6、DR-7。
3. **拖曳自動捲動與終止**：§7.1 統一 layout viewport client 座標、可視區用 `visualViewport.offsetTop..+height` 並扣頂欄／nav，位移含 scrollY 差，rAF 每幀重算；§7.5 `endDrag(commit)` 收尾表（up／cancel／lostpointercapture／清單變動／換頁／開 Detail／visibilitychange／pagehide）；鍵盤 ↑↓ `preventDefault`、焦點留在同一檔把手；新增 DR-8～DR-13；offsetTop>0、觸控手感、VoiceOver 照實 DEFER 真機。
4. **Active Flow**：§8.2 列為不可刪除／弱化／重做／替代的功能；新增 FL-1～FL-7（treemap 與無報價列表的 computed 紅加碼／綠減碼與正負號、Detail → 完整持股異動 Back／Forward、fetched=false／無異動／未更新語意、FD-1～6 保留、收藏不重設 `_flowSel`）。

**D5 調整**：依 Codex 意見，Plan 預設改為「點 ⠿（移動 < 8px）開移動選單：上移／下移／最上／最下」作為不需拖曳的替代，卡片不加常駐按鈕；新增 DR-14。仍待 Gate 確認。D1～D4、D6 不變。

**Codex 複審範圍**：只看 `PHASE4_PLAN.md` Rev.2 的修訂處是否解決四項 finding；不需重審已確認可行的部分（資料欄位、miniBars 參數方向、Router watch base）。PASS 後交 PO／GPT Gate 確認 D1～D6，才開始 coding。

### Phase 4 Rev.2 — Codex 複審（2026-10-05）：NEED FIX

只審 Rev.2 修訂與現有程式，未修改程式、未 commit／push。上一輪四項結果：

- Finding 1（DOM／測試遷移／Detail 收藏）：RESOLVED。§3.1、§3.2、§8.1、§10.3 與 DF-1～6 已補齊。
- Finding 2（跨分頁／拖曳／復原）：實作規則 RESOLVED，UN-5 測試情境仍需更正（下列第 2 項）。通知、冪等、失敗提示與 code-based 排序方向可接受。
- Finding 3（拖曳捲動／終止）：RESOLVED。§7.1、§7.4、§7.5 與 DR 測試已涵蓋；offsetTop、觸控／VoiceOver 如實留真機驗證，無需架構重構。
- Finding 4（Active Flow）：PARTIALLY RESOLVED。不可替代功能、紅加碼／綠減碼、海外無報價列表、狀態語意與 FD-1～6 都已保護；FL-4 的返回期望與封版 Router 相反，必須更正。

**必要修改（只修 Plan／測試規格，不改既有 runtime）：**

1. **FL-4 不得要求 Back 回 Detail。** `PHASE4_PLAN.md` §10.1 FL-4 現在寫「Back 回 Detail；Forward 再到 Flow」。實際 `detailGoFlow → openFlow → Router.intentBase({flow:true})` 會退到共同基底，再建立 `folder(active,flow)`；`PHASE3_PLAN.md` §8.3 明文寫 Back 回分類總覽、不回 Detail，§16.6 NV-A～NV-D 與現有 router_test RT-22 也沿用此語意。請改為：Detail → 完整持股異動選定同檔 → Back 分類總覽 → Forward 回同檔持股異動；覆蓋首頁、工具、分類與新增自選來源，最終不留下 Detail 層。不可以為了讓 FL-4 綠燈去修改 Router 或重建持股異動 history。FL-1～3、FL-5～7 的保護方向可接受；使用 fixture 保證需驗證的正／負值與狀態確實存在，保留 computed 色彩與文字 assertion。

2. **UN-5 與「最近一次移除」規則衝突。** §2.6／§4 規定第二次移除會取代第一次 Toast，但 UN-5 寫「移除第 3 張 → 再移除另一張 → 復原插回 index 2」，一般 UI 情境下復原應針對第二次移除。請分開驗收：(a) 連續 UI 移除：只復原最後一檔與其 index；(b) 原 Toast 存續時，由 storage 同步或明確的非 Toast 測試安排使清單縮短，再復原原檔，驗證 min(index,length)；(c) 移除後拖曳重排，再復原，依明定原數字 index 夾限。不要為了 UN-5 而擴成多筆復原或忽略第二次移除。

**D1～D6：** 全部仍交 PO／GPT Gate。D1 局部 0 中性、D2 不增加 light theme、D3 標題列收藏、D4 最近一次＋5 秒、D6「我的自選」在技術上可接受。D5 新增點把手移動選單＋鍵盤替代，方向可接受，比僅靠拖曳／外接鍵盤更完整；是否採用由 Gate 決定，VoiceOver 點擊與選單焦點／關閉行為需實作及真機驗證。

下一位：Claude。只修上述兩項 Plan 驗收期望後交 Codex；已關閉的前三項不需重新擴張。PASS 後才交 PO／GPT Gate 決定 D1～D6，未授權 coding。

### Phase 4 Coding — 交 Codex Code Review（Claude，2026-10-05）

依 `PHASE4_PLAN.md` Rev.2.1 與 §11.1 D1～D6 實作。不可回歸：① 台股漲紅跌綠；② Active Flow 不得刪除、弱化、替代。

- **新檔**：`js/watch-store.js`（收藏唯一來源）、`js/watch.js`（我的 ETF 頁、卡片、Toast、拖曳、移動選單、鍵盤；全域 `watchToggle(code)` 供分類／Detail／自選共用）、`css/watch.css`、`tests/browser/watch_test.py`。
- **修改**：`js/category.js`（`rowHtml` 改容器＋`.cr-main`＋`.fav-btn`，委派先 ♡ 再主區，訂閱 Store 只更新 ♡）、`css/category.css`（`.cat-row`／`.cr-main`，移除 `.cr-yld`）、`js/detail.js`（`_dtSyncFav()` 在 `detailPatch()` 的 `!e` return 之前；`#dtFav` 點擊只呼叫 `watchToggle`）、`index.html`（`#page-watch` 正式化、標題「我的 ETF」、`#dtFav`／`#dtClose`、Toast、§8.1 script 順序、版本 `20261005s`）、`js/format.js`（`miniBars(months, {token})`、`favBtnHtml／favBtnSync`）、`js/render.js`（`renderAll` 尾端 `Watch.refresh()`）。
- **D1 全站 0 中性**：`miniBars` 的 0 改為中性短柱（`--dim`，壓在中線），缺值維持灰色；排行頁「近一年」`retClr`／`fmtRet` 的 0 改中性、不加「+」；搜尋結果 `_gsFmtChg` 的 0 顯示中性「0.00%」。排行／Detail 的紅綠色值沿用原本 `#ff6b6b`／`#00e5a0`（只修 0），自選卡用 `--up`／`--dn` token。
- **未改**：`router.js`、`flow.js`、B6、Phase 3 文件夾與標題列、資料 pipeline。
- **與 Plan 的小差異（請 Codex 判斷）**：① 拖曳提示文字為「按住 ⠿ 可拖曳調整順序，點一下 ⠿ 可選擇移動位置」（因 D5 保留兩種方式）；② 把手按 Enter／Space 也開移動選單（Plan 只寫 ↑↓）；③ Plan §4 提到的卡片移除 150ms 淡出未做（直接消失，`prefers-reduced-motion` 本來就不做）；④ 收藏清單任何變動時自選頁整個重畫（行情更新才只換內容）。
- **既有測試只遷移選擇器**（§10.3）：category 125、133、464、552 → `.cr-main`；466、554、detail_state 93、detail_ui 112／157／178／192、detail_history_fix 56 → `#dtClose`；detail_state 108 → `.cr-main`。另 category「NAV watch」改驗「我的 ETF」＋引導式空狀態（原本驗 Phase 3 占位文字）。AB／RL 清單幾何未變（列高仍 44px），視窗不需再調。
- **測試結果**：watch_test **98 PASS、0 FAIL、4 DEFER**；category 250 PASS／1 DEFER（LR-8，已真機 PASS）；router 64/64；search_compact 38/38；detail_ui 42/42；detail_history_fix 14/14；regression 14/14；detail_collapse 25/25；detail_state 42/42。負向對照：把今日漲跌改成美股色、把 0 改回紅色 → watch_test 8 項 FAIL（BR-1、CL-1／CL-2、D1）。
- **watch_test 涵蓋**：ST-1～8（含寫入／讀取失敗、storage 不回寫、失敗後不被覆蓋、reload）、SY-1～3、CD-1～3、UN-1／3／4／5a／5b／5c／6、BR-1～3、CL-1～2、D1、ES-1～2、DR-1～3／5～9／11～14、DF-1～5、LV-1（844×390、390×300）、A11Y、FL-1～5／7、FL-4 四個來源（首頁／工具／分類／自選）。FL-6＝category_test 的 FD-1～6。
- **DEFER（真機）**：DR-R1 `visualViewport.offsetTop > 0` 時的拖曳與自動捲動；DR-R2 觸控手感、iOS 長按選字、Samsung 左緣返回手勢；DR-R3 VoiceOver 點兩下 ⠿ 開選單；DF-6 Detail 收合時 ♡ 與 ✕ 同步隱藏（headless 內容不夠長，未觸發收合）。
- **Codex 審查重點**：WatchStore 的通知／storage／失敗狀態；分類列結構與委派對 D4／renderList／LR-4／tight3 的影響；`_dtSyncFav` 與 Detail 狀態；拖曳的座標、rAF、所有終止路徑；D1 改動範圍；FL 保護是否確實；新測試是否真的驗證行為。

### Phase 4 Code Review 修正 — 交 Codex 複審（Claude，2026-10-05）

只修 Codex 三項，未改產品需求、未擴大重構；`router.js`／`flow.js` 仍無 diff。

1. **把手標準 click**（`js/watch.js` `bind()`）：移動選單改由 `click` 開／關（涵蓋滑鼠、觸控 tap、原生 Enter／Space、VoiceOver／TalkBack 合成 click）。`pointerup` 不再開選單；拖曳放開時設 `suppressClick` 吃掉瀏覽器補發的 click（400ms 後自動解除）。按下把手時若關掉的是同一檔的選單（`pressClosedMenu`），隨後的 click 只把焦點還給把手、不重開（＝點同一把手關閉）。移除原本 keydown 的 Enter／Space 分支，避免與原生 activation 雙觸發；↑／↓ 與 focusCode 保留。
2. **開選單時拖曳的幾何**（`startPress()`／`activate()`）：在 `startPress` 量測前先 `closeMenu`，記下這張卡關閉前後的 top 差 `shift`，`y0 = clientY − shift`，所以拖曳位移包含版面上移量，卡片維持在手指下；`activate()` 的快照一律在選單關閉後才量。選單在卡片下方時 shift＝0。
3. **漲跌額／幅各自判色**（`chgHtml()` → `chgPart()`）：兩欄各自以四捨五入到 2 位後的值決定 up／dn／flat（`--up`／`--dn`／`--dim`）與 ▲▼／+−；null 一律灰「--」；`+0.004`／`−0.004` 顯示中性 0.00，不出現 −0.00。CSS 新增 `.wc-chgs` 容器。

- **新增 regression（watch_test）**：CL-1 改為兩欄分別驗文字＋computed color；CL-3 ×6（−0.01／0、0／+0.01、null／+1.2、+0.3／null、±0.004、正負不同號）；DR-15 click-only 開／再 click 關且焦點回把手；DR-16 Enter、Space 各開一次且不捲頁；DR-17 真實 tap 只觸發一次；DR-18 拖曳放開不開選單；DR-19 以真實 tap 開 A 選單 → 拖 A 跟手（≤ 3px）＋最終順序；DR-20 開 A 選單 → 拖下方 B 10px 跟手（≤ 3px）＋依關閉選單後的新版面計算放下位置，驗最終順序。
- **測試結果**：watch_test **114 PASS、0 FAIL、4 DEFER**（真機項目不變）；category 250／1 DEFER；router 64；search_compact 38；detail_ui 42；detail_history_fix 14；regression 14；detail_collapse 25；detail_state 42，全部 PASS。
- **負向對照**：以 `b78134c1` 的舊 `watch.js` 跑同一份測試 → 15 FAIL（CL-1／CL-3、DR-15、DR-19、DR-20；DR-20 實測手指 551.59 vs 把手 433.59，與 Codex 重現一致）。
- 資源版本 `20261005t`。DF-6 收合驗收依 Codex 意見非 blocker，未新增。

### Phase 4 76252269 — 拖曳手感修正（Claude，2026-10-05）：交 Codex Code Review

PO 真機回報：按住 ⠿ 沒有「已抓住」回饋、要慢按、要快拖才換位、節奏不對就整頁捲動。Claude 分析後 PO／GPT Gate 決策：按住 200ms 抓起；已亮起但沒拖就放開＝只放下、不開選單；不加震動；換位改「前緣越過中線」；把手觸控範圍只擴大到 ⠿ 那一欄；處理 iOS 捲動競爭與自動捲動緩衝；亮起只綁 drag active；提示文字定案。只改 `js/watch.js`、`css/watch.css`、`index.html`（提示文字、版本 `20261005v`）、`tests/browser/watch_test.py`。

- **抓起條件**（`startPress`／`activate`）：pointerdown 後啟動 200ms 計時（`HOLD_MS`）；計時到仍未移動 8px → `activate()`。200ms 前已移動 ≥ 8px（仍以 `yRaw` 判斷）→ 立即 `activate()` 並清計時。200ms 內放開且 < 8px → 不 activate，標準 click 開選單（Codex 已驗規則不變）。已 activate 但沒換位就放開 → `endDrag(true)`（target＝from 不寫入）＋ `suppressClick` → 不開選單。計時器在 `activate` 與 `endDrag` 都清除，所有終止路徑（換頁、開 Detail、清單改變、visibilitychange、pagehide、cancel）都不會延遲抓起。
- **亮起**：只在 `activate()` 加 `.lifting`（金色 2px 框、底色變亮、陰影加深、`scale(1.02)`；reduced-motion 不放大）；pointerdown 不亮。色彩美化留 Phase 5。
- **換位門檻**（`frame()`）：往下拖時，拖曳卡片底緣越過下方卡片中線即換位；往上拖時，頂緣越過上方卡片中線即換位（約半張卡，原本中心對中心約一張卡）。讓位動畫與以 code 寫入不變。
- **把手欄**（CSS）：`.drag-handle` `align-self: stretch`，上下吃掉卡片 padding，與卡片同高；⠿ 仍在上方；寬 44px，不與 `.wc-main`（代碼、名稱、價格、標籤）重疊，♥ 在另一側。
- **iOS 捲動競爭**：`#watchList` 加 `touchmove`（`passive: false`）監聽，只有在拖曳狀態存在且觸控從 `.drag-handle` 開始時才 `preventDefault`；**不擋 touchstart**（保留輕點 click）。卡片主區的 touchmove 不處理，照常滑頁。
- **自動捲動緩衝**：`EDGE` 48 → 36px；手指相對起點朝該邊緣移動 ≥ 24px（`AUTO_MIN`）才開始捲動。
- **提示文字**：「按住 ⠿ 卡片亮起後拖曳調整順序；點一下 ⠿ 可選擇移動位置」。

- **既有測試調整**：DR-1、DR-9、DR-18、DR-19 的拖曳距離依新門檻由 1.6 張卡改為 1.0 張卡（1.6 張在新門檻下會越過兩張，期望順序仍是「越過一張」，未放寬檢查）；DR-7 同步改為 1.0。DR-20 依新版面計算（C 中線再下 10px），新門檻下仍只越過 C，未改。DR-21（3px／7px 觸控、1px 滑鼠，皆在 200ms 內放開）不變且 PASS。
- **新增測試**：HT-0 提示文字；HO-1 pointerdown 與 100ms 時未亮、約 200ms 後亮起進入拖曳、沒拖就放開不開選單且狀態清除；HO-2 200ms 內放開開選單且從未亮起；HO-4 200ms 前移動 12px 立即抓起、cancel 完整清除；TH-1 拖 0.6 張卡即換位且不開選單；TH-2 0.3 張不換位；TH-3 往上 0.6 張換位；HA-1 把手欄與卡片同高、不與主區重疊、按在下半部也能抓起；HA-2 代碼／名稱位置屬卡片主區；AS-1 抓起靠上緣的卡片後移動 10px 不捲動、移動 ≥ 24px 才捲動；HC-1／HC-2 計時中換頁或清單改變不會延遲抓起；PV-1 從把手移動 5px 不捲頁且仍是點擊。
- **測試結果**：watch_test **136 PASS、0 FAIL、4 DEFER**；category 250／1 DEFER；router 64；search_compact 38；detail_ui 42；detail_history_fix 14；regression 14；detail_collapse 25；detail_state 42，全部 PASS。
- **負向對照**：以 `5df1cb50` 的 `watch.js`／`watch.css` 跑同一份測試 → 11 FAIL（HO-1、TH-1、TH-3、HA-1、AS-1，以及依新門檻校正的 DR-1／9／18／19）。
- **仍需真機**：手感是否改善（不再需要慢按、正常速度可換位）、iOS 是否仍搶捲動，只能由 PO 真機確認。

### Phase 4 edb065d2 — 拖曳邊界（Claude，2026-10-05）：交 Codex Code Review

PO 真機 Observation：往下拖曳卡片時可以越過清單底部，穿過「自選 ETF 僅儲存在此裝置與瀏覽器中」提示區，拖進下方空白（放手後排序仍正確）。

- **原因**：`frame()` 的卡片位移（`translateY(off)`）沒有上下限；自動捲動只看手指是否靠近可視區邊緣，清單底已經完整可見仍會繼續捲，而被拖曳卡片的 transform 又讓文件可捲高度持續變大（舊程式實測 scrollY 被帶到 3216）。
- **修正（只改 `js/watch.js` `frame()`）**：以 activate 時的卡片快照取清單邊界（第一張頂～最後一張底，文件座標）；跟手位移 `off` 與排序位移 `intent`（`raw − comp`）都夾在「頂端對齊第一張、底端對齊最後一張」之間；自動捲動往下只在清單底尚未進入可視區（`listBot − scrollY > band.bottom`）時繼續，往上同理。拖到最後一列、底部自動捲動、跟手、前緣換位、`comp` 分離、排序寫入與持久化都不變。未改其他 UI；版本 `20261005x`。
- **新增測試**：BD-1 拖到底時卡片底緣不超過清單底、不進提示區（4 檔、10 檔）；BD-2 清單底可見後自動捲動停止；BD-3 放開成為最後一張並寫入；BD-4 拖曳卡片在底部導覽列上方；BD-5 往上拖超過清單頂時卡片頂緣不超出第一張、放開成為第一張。
- **既有測試調整**：DR-8 反向原本驗 `scrollY < 50`；新邊界下自動捲動在清單頂可見時就停（清單上方還有標題與提示），改驗「放下成為第 1，且第一張卡頂端在頂欄下方可見」。其餘不變。
- **測試結果**：watch_test **149 PASS、0 FAIL、4 DEFER**；category 250／1 DEFER；router 64；search_compact 38；detail_ui 42；detail_history_fix 14；regression 14；detail_collapse 25；detail_state 42，全部 PASS。
- **負向對照**：以 `ba3070f3` 的 `watch.js` 跑同一份測試 → BD 7 項 FAIL（卡片底緣進入提示區與導覽列、scrollY 持續增加到 3216、往上拖卡片頂緣到 −68）。

### Phase 4 ba3070f3 — 按住計時交界修正（Claude，2026-10-05）：交 Codex 複審

只修 Codex 兩項，`js/watch.js` 以外只改測試與版本號（`20261005w`）：

1. **選單補償不算排序意圖**：`activate()` 關閉上方選單時的高度差存為 `drag.comp`，仍加到 `y0` 讓卡片跟手；`frame()` 的換位改用 `intent = off − comp`（手指實際位移＋頁面捲動）計算前緣越過中線。開 A 選單 → 按住下方 B 不動 → 放開時 intent＝0、target＝from，不寫入。
2. **失去 capture 一律取消**：`lostpointercapture` 只要是同一 pointer（`drag.pid`）就 `endDrag(false)`，按住計時中與拖曳中都會清計時器、capture、亮起與 transform，不保存排序。正常放開時 `pointerup` 已先 `endDrag` 把 `drag` 清掉，之後的 lostpointercapture 不會重複收尾。

- **新增測試**：HO-5 開 A 選單 → 按住下方 B 300ms 不移動（會亮起）→ 放開：畫面、Store、localStorage 順序都不變，不開選單、亮起清除；LC-1 pointerdown(pid 99) → lostpointercapture → 300ms 後不抓起、無亮起；LC-2 拖曳中 lostpointercapture → 拖曳取消、亮起與 transform 清除、不保存排序；LC-3 之後重新輕點可開選單、按住拖曳 1.0 張卡可換位。
- **DR-20 調整**：放下位置改為「手指從按下處往下移 1.0 張卡」（排序意圖只看手指實際位移），期望仍是 B 移到 C 之後；10px 時的跟手檢查（≤ 3px）不變。DR-19、TH-1～3 不變且 PASS。
- **測試結果**：watch_test **140 PASS、0 FAIL、4 DEFER**；category 250／1 DEFER；router 64；search_compact 38；detail_ui 42；detail_history_fix 14；regression 14；detail_collapse 25；detail_state 42，全部 PASS。
- **負向對照**：以 `76252269` 的 `watch.js` 跑同一份測試 → HO-5、LC-1、DR-20 FAIL（HO-5 重現 Codex 的 `[0050,00878,0056,00919]` 類型重排；LC-1 300ms 後仍抓起）。LC-2 在舊程式也 PASS（舊程式已處理拖曳中的 capture 遺失），作為保護性 regression。
- **體驗上的取捨（請 Codex 判斷）**：選單開著時從下方卡片開始拖，卡片會停在手指下（跟手），但換位依手指實際位移計算，所以在這個少見情境下，換位時機相對畫面會差一個選單高。一般情況（沒開選單）comp＝0，完全不受影響。

### 76252269 — Codex Code Review（2026-10-05）：NEED FIX

只審 `76252269` 的 PO 核准拖曳手感修正與相關 regression；不重開已通過的產品需求。重跑 watch_test：136 PASS／0 FAIL／4 DEFER。以下兩項以獨立瀏覽器補測重現，未修改程式或測試檔：

1. **選單開著時，只按住下方卡片、沒有移動，放開仍會改排序。** `js/watch.js` `activate()` 關閉上方選單後，把高度差補到 `y0`；新 HOLD_MS 會在手指完全沒動時 activate，`frame()` 又用這個含版面補償的 off 計算前緣換位，`endDrag(true)` 寫入。因此布局補償被當成使用者排序意圖。390×844，收藏 `[0050,0056,00878,00919]`：輕點 0050 把手開 A 選單 → 按住下方 0056 把手 300ms、不送任何 touchMove → 原地放開 → 順序變 `[0050,00878,0056,00919]`。違反核准「已亮起但沒拖就放開＝只放下、不改排序、不開選單」。請分開處理真實 pointer 排序位移與保持跟手的布局補償，不能只依經補償的 target 決定提交。補「開 A 選單 → hold 下方 B 不移動 → release」驗收，Store／localStorage 都應保持原順序，保留 DR-19／20 跟手與 TH 前緣換位。

2. **抓起前失去 capture，不會取消 hold 計時器。** `bind()` 的 `lostpointercapture` 仍要求 `drag.active` 才呼叫 `endDrag(false)`；pending press 在 200ms 前收到此終止事件會被忽略。補測 pointerdown(pid=99) → lostpointercapture(pid=99) → 等 300ms，`Watch._state().dragging === true` 且 `.lifting` 有一張；沒有新的 press，卡片仍延遲抓起。請讓同 pointer 的 pending／active 狀態都能取消、清 timer／capture／樣式，不保存排序；正常 pointerup 的 release 事件仍需避免重複收尾。補 capture 在 hold 計時中遺失、active 時遺失、接著重新按下可正常操作三種測試。

**測試有效性：** 新 HO／TH／HA／AS／HC／PV 實際檢查亮起時機、觸控命中、前緣換位、scrollY、退出清理；DR 拖曳距離 1.6→1.0 是新門檻的合理前提調整，排序 assertion 沒有放寬。HO-1 沒有先開選單，HC 沒有 capture 遺失，所以尚未涵蓋上述兩項，136 PASS 不代表它們已解決。四個真機 DEFER 與這兩項可自動重現的問題無關。

**範圍與下一步：** 200ms／8px 決策、整欄把手、提示、無震動、紅綠語意等不重議，不要求 refactor。Claude 只修兩項與補 regression 後交 Codex；PO 現在不用操作。未改程式、未 commit／push。

### Phase 4 5df1cb50 — 拖曳門檻修正（Claude，2026-10-05）：交 Codex 複審

只修 Codex 指出的「真實手指移動與選單關閉版面補償混用」，`js/watch.js` 以外的程式未動：

- 新增 `drag.yRaw`（原始 pointerdown 位置），`pointermove` 以 `|y − yRaw| ≥ 8` 判斷是否進入拖曳；`y0` 只作跟手錨點。
- **選單改在確定拖曳（`activate()`）時才關閉**，不在 pointerdown 關閉：若按下時就關閉，選單上方的卡片會在手指下方上移約一個選單高，觸控輕點產生的 click 會落到別的元素上（實測 3px／7px 觸控輕點時 B 選單未開）。`activate()` 先 `closeMenu`、量這張卡關閉前後的 top 差，再 `y0 −= shift`，接著才做卡片快照 → DR-19／20 的跟手錨定不變（DR-20 手指 551.59＝把手 551.59）。
- 移除 `pressClosedMenu`：點同一把手關閉選單由標準 click 的 toggle（`menu.code === code` → `closeMenu(true)`）處理；拖曳放開後的 `suppressClick` 保留。
- **新增 DR-21 ×3**：開 A 選單 → 在下方 B 把手輕點（觸控 3px、觸控 7px、滑鼠 1px，皆 < 8px）→ 放開前 `dragging === false`、放開後只開 B 選單、只有一個選單、順序與 Store 不變。
- **測試結果**：watch_test **117 PASS、0 FAIL、4 DEFER**（DR-15～20 仍 PASS：click-only／Enter／Space／tap 不雙觸發、拖曳後 click 不誤開、≥ 8px 跟手與最終排序）；category 250／1 DEFER；router 64；search_compact 38；detail_ui 42；detail_history_fix 14；regression 14；detail_collapse 25；detail_state 42，全部 PASS。
- **負向對照**：以 `6d2d9a3d` 的 `watch.js` 跑同一份測試 → DR-21 三項 FAIL（按下後立即 `dragging === true`、B 選單未開），與 Codex 重現一致。
- 資源版本 `20261005u`。

### Phase 4 6d2d9a3d — Codex 複審（2026-10-05）：NEED FIX

本輪只驗上一輪三項與 CL-3、DR-15～20；未改程式／測試、未 commit／push。重跑 watch_test：114 PASS／0 FAIL／4 DEFER。判色（第 3 項）RESOLVED；標準 click／Enter／Space／tap 與拖曳跟手的原問題已修，但第 1／2 項交界有一個新引入、可重現的 blocking bug：

**選單在卡片上方時，輕點被誤判為拖曳。** `js/watch.js` `startPress()` 設 `y0 = ev.clientY - shift`（shift 是關閉選單造成的版面位移），但 `pointermove` 又用 `Math.abs(drag.y - drag.y0) >= 8` 判斷真實手指是否拖動。即使只移動 1～3px，只要 shift 約 118px，也會立即進入 dragging；pointerup 隨後設定 suppressClick，原本應開啟 B 選單的 click 被吃掉。

獨立 CDP 滑鼠與觸控都重現（390×844，收藏 0050／0056／00878／00919）：
1. 點第一檔 A（0050）把手，確認 A 選單已開。
2. 在 A 選單下方的 B（0056）把手 pointerdown，輕移滑鼠 1px 或觸控 3px（皆小於 8px）。
3. 放開前 `Watch._state().dragging === true`；放開後 menu 為 null，B 選單未開。正常 click-only 控制測試仍可開 B，確認是新門檻問題。

**必要修正：** 使用未經版面補償的原始 pointer 起點判斷 DRAG_PX；跟手位移保留選單高度補償，勿移除原本已正確的 DR-19／20 錨定。補測「開 A 選單 → 輕點下方 B，移動 <8px → 只開 B 選單、不開始拖曳、不重排」，並維持 ≥8px 的跟手與最終排序、click-only／Enter／Space／tap 不雙觸發、拖曳後 click 不誤開。

**新增測試有效性：** CL-3 以每欄完整文字及 computed color 驗混合值與四捨五入，未放寬驗收，通過；DR-15～18 有實際 activation／release；DR-19～20 驗 ≤3px 跟手誤差與最終順序，能抓舊 bug，但每次先移動 10px，沒有覆蓋上述 <8px 輕點門檻，114 PASS 不代表此交界已通過。四個 DEFER 繼續留真機 QA，與本 blocker 無關。

下一位：Claude。只修這個門檻交界並補測，再交 Codex。PO 現在不用操作；不要擴大修正範圍或重審已關閉項目。

### Phase 4 Implementation — Codex Code Review（2026-10-05）：NEED FIX

實際審查 `b78134c1`，基準 Plan／Gate `df5d5072`。只修改本 handoff；沒有修改程式、測試、Plan，沒有 commit／push。產品決策不重議。必要修正共三項：

1. **標準 click 無法開把手選單（`js/watch.js` `bind()`，約 261–305 行）。** 移動選單只從 pointerup 與把手 keydown 開啟，click handler 沒有 `.drag-handle` 分支。補測 `document.querySelector('.drag-handle').click()` 後 `Watch._state().menu` 仍為 null；相同把手透過 pointerdown/up 則正常。VoiceOver／TalkBack 的合成 click 路徑缺少實作，不可只列 DR-R3 真機 DEFER。請加入標準 button activation 路徑並避免 pointerup＋隨後 click 雙觸發；拖曳放開不得誤開選單。補 click-only、Enter／Space、真實 tap 各一次及拖曳 release 的測試。

2. **已有移動選單時，開始拖曳會使用過期幾何（`js/watch.js` `startPress()`／`activate()`，約 199–222 行）。** `activate()` 先量卡片 document top，再 `closeMenu(false)`；選單實際插在卡片之後、占版面高度，移除後其下方卡片立刻上移，但已保存的 y0／rect 仍含選單高度。補測四檔：開第一檔選單，拖第二檔向下 10px；手指期望位置 551.59，實際把手中心 433.59，偏離約 118px（scrollY=0）。請在開始量測前關閉選單，並維持 pointer／card 的起始錨點一致，不能只在快照完成後移除；若開始按下的卡片位於選單下方，也需處理移除造成的起始位置變動。補「開 A 選單 → 拖 A／下方 B」的跟手位置與最終順序驗收，勿只驗 Store 最後可 move。

3. **今日漲跌額／幅共用一個判色與箭頭，0／缺值會被染成另一欄的狀態（`js/watch.js` `chgHtml()`，約 36–47 行）。** 用 pct 優先決定整個 span 的 k，再對 pt 取 Math.abs。補測：pt=-0.01、pct=0 → 顯示中性「0.01　0.00%」，跌幅符號與綠色消失；pt=0、pct=0.01 → 「▲0.00」變紅；pt=null、pct=1.2 → 缺值「--」也變紅。這些是數字各自四捨五入／部分缺欄時的有效邊界，違反 §6／Gate 的漲紅跌綠、0 中性、缺值灰。請每欄依自身值顯示顏色及正負語意，保留 pt 的下跌方向，不將 null 當另一欄的正值。補混合 0／正負／null fixture；原 CL 測試只涵蓋兩欄同號，無法抓此問題。

**四項 Plan deviation 判定：** ① 提示同時說明拖曳與點選：可接受；② Enter／Space 開選單：可接受且有益，但須修第 1 項 click-only 路徑；③ 無 150ms 移除淡出：可接受，功能不受影響；④ 收藏清單變更整份重畫、行情只 patch：目前核心同步與順序測試通過，實作形式本身不阻擋。鍵盤排序已有 focusCode 還原，修正時保留。

**Active Flow：** `router.js`／`flow.js` 無 diff；watch_test 重跑 FL 項目通過。computed treemap 紅加碼／綠減碼、海外正負／缺值列表、fetched=false／無異動／未更新文字、四種來源 Detail → Flow → Back 總覽 → Forward 同檔均被驗證，收藏重繪未重設 Flow。不得為修 Phase 4 而改這些封版語意。

**驗證：** watch_test 重跑 98 PASS／0 FAIL／4 DEFER；另重跑 category_test 與 detail_state_test（Detail 42 PASS／0 FAIL），Category 的低高度實際點擊、D4 與 inside／doorway 等回歸已核對。另以獨立瀏覽器補測重現上述三項（未建立測試檔）。既有選擇器遷移 diff 沒有放寬 assertion，但新的把手測試只使用 pointer 事件，沒有驗 click-only；拖曳測試沒有先開選單；漲跌測試沒有混合欄位狀態，故 98 PASS 不代表這三項已涵蓋。

**四個 DEFER：** offsetTop>0、真實觸控／系統手勢、VoiceOver 操作、Detail 收合目視可留真機 QA，不直接判 FAIL；但已可重現的 click-only 缺失需先修，不可用 VoiceOver DEFER 掩蓋。DF-6 可補自動收合驗收，現有 CSS 同列隱藏方向無明確 regression，不因此新增 blocker。

下一位：Claude。只修三項並補對應 regression，交 Codex 複審；PO 現在無需操作，不開始下一 Phase。

### Phase 4 Rev.2.1 — 修訂內容（Claude，2026-10-05）：交 Codex 複審

只改 `PHASE4_PLAN.md` 的測試規格，未改 Router 規格、未 coding：

1. **FL-4**：改為封版 Router 語意。分別從首頁、工具、分類、自選開 Detail → 「查看完整持股異動 ›」→ 同一檔 Flow，`stack` 只剩 `folder(active, flow)`、不留 Detail 層 → Back 回**分類總覽** → Forward 回同檔持股異動（依 PHASE3_PLAN §8.3、§16.6 NV-A～NV-D、RT-22）。§8.2 對應描述同步。FL-2、FL-3 改為以 fixture 保證加碼／減碼、正／負／缺值都存在，保留 computed 色彩與文字 assertion。
2. **UN-5** 拆成三項，與「只復原最近一次」一致：UN-5a 連續 UI 移除只復原最後一檔（回原 index）；UN-5b Toast 存續時以注入 `storage` 使清單縮短，復原插在 `min(index, 長度)`；UN-5c 移除後重排再復原，以原數字 index 夾限。不擴成多筆復原。

**Codex 複審範圍**：只看 FL-4（含 FL-2／FL-3 的 fixture 補充）與 UN-5a～c。已 RESOLVED 的 Finding 1～3 不重審。PASS 後交 PO／GPT Gate 決定 D1～D6，未授權 coding。

### Phase 5 — GPT Gate 決策（PO 確認，2026-10-05）：尚未開始實作

本節為 Phase 5 已確認的產品決策與 Git 考古結論。**只記錄，尚未 coding**；不新增範圍，不重開 Phase 2～4。

1. **新手 ETF 展示原則（資料池層級產品規則）**：ETF 存股雷達主要面向 ETF 新手（PO 曾遇新手詢問「槓桿 ETF 能不能買」），刻意不主動提供需要額外理解產品機制的特殊 ETF。**槓桿：排除；反向：排除；商品期貨：排除（PO 本次決定）；一般債券：保留。** 規則放在資料池（`fetch_etf.py` 建池），前台不需額外大量說明。
2. **修補特殊 ETF 排除漏洞（待實作）**：現行 `EXCLUDE_KW`（`e15e9af3` 起）有漏網——`02001L 富邦蘋果正二N`（「正二」非「正2」，已在 `etf_pool_cache.json`，目前因量低／抓不到才沒出現，非規則保證）；商品期貨 ETF 名稱以「期」開頭而非「期貨」（00682U 期元大美元指數、00693U 期街口S&P黃豆、00763U 期街口道瓊銅目前在資料池，歸「其他」）。**不可單純加入過寬的「期」字關鍵字**，正式實作前須提出較可靠的產品辨識方式（例：代號字尾／證交所商品類別等，需先查證再提案）。 **具體辨識方式由 Claude 在 Phase 5 Plan 提出，PO 不需選技術實作。**
3. **「價格合理區」母體**：成交量前 100 檔（`cur_vol` 排序）→ 再判斷價格條件；不從全部 ETF 直接挑。
4. **LAZY_WATCHLIST**：Git 考古確認**不是**槓桿／反向的新手安全機制。最初 `99c8b9b7`（2026-05-14）以 20 檔人工白名單限制舊首頁「合理價」只收熱門 ETF、避免冷門／極新 ETF；`8e8e1566`（2026-05-20）起 cheap 不再受限、同時加入 00403A（21 檔）；之後未再維護（3 檔債券 00679B／00687B／00772B 不在資料池、3 檔 00757／00646／00662 不配息；`intraday_notify.py`、`fetch_dividend_calendar.py` 的副本少 00403A）。**Phase 5 決定：新「價格合理區」不再用 LAZY_WATCHLIST 限制 fair**（成交量前 100 已取代其目的）。⚠ 名單仍被 `daily_check.py`（TG 通知）、`intraday_notify.py`（盤中推播）、`fetch_dividend_calendar.py`（配息行事曆）使用，**不可全域刪除**；其他用途需另行確認後才清理。 **TG／盤中推播／配息行事曆這三處本輪不修改、不刪除，列為既有技術／歷史項目，不是 Phase 5 的 PO blocker。**
5. **不配息 ETF**：「價格合理區」繼續排除 `div_frequency === '不配息'`（舊首頁自 `99c8b9b7` 起即排除，`8e8e1566` 改用頻率判斷、`098b5fed` 連 fallback 也排除）。不配息 ETF 仍正常存在於分類、全站搜尋、ETF Detail、我的 ETF 等功能，只是不主動進入首頁價格合理區。
6. **cheap 門檻正式確認：52 週位置 < 40%，且低於 60MA > 2%（`pos52 < 0.40 and maD60 < -2`），維持不變，不改回舊版 30%／3%。**
   - **PO 歷史原因（請勿再依舊文件誤改）**：舊版 30%／3% 條件太嚴格，曾連續很多天幾乎沒有 ETF 符合，首頁「值得留意」長期沒有內容可呈現，因此刻意放寬為 40%／2%。
   - **Git 證據**：初版 `9f6db875`（2026-05-11）與 `e55e77df`（2026-05-12，同時建立 CLAUDE.md）為 `pos52 < 0.30 and maD60 < -3`；`4ea6db41`（2026-05-19）commit 訊息明寫「cheap 條件放寬：pos52<0.40、maD60<-2」，`fetch_etf.py` 與 `mis_fetcher.py` 同步修改。CLAUDE.md 之後未更新，才出現文件與程式不一致。
7. **更新過期文件（以程式為準）**：CLAUDE.md 訊號表格自 `4ea6db41` 後未更新，須依現行程式更正 **cheap、fair、hot 與債券相關說明**（現行：hot＝5 日漲幅 ≥ 5% 或 RSI ≥ 75；dear＝52 週位置 > 78% 或現價 > 60MA×1.06，及其餘預設；cheap 如上；fair＝現價 ≤ 60MA×1.03、5 日 < 5%、量比 ≤ 3.0（`4c00a1fe` 移除下限 0.5）、RSI < 75，高股息型另需殖利率 > 5%；bond＝代號 B／D 結尾短路）。**原則：文件配合程式，不因文件過期反改公式。**
8. **價格合理區顯示方式**：符合 ≤ 10 檔全部顯示；超過 10 檔預設顯示前 10 檔＋「查看全部 X 檔」，展開後可「收起」；每列整列可點擊進 ETF Detail；精簡列表（例：`00998A　主動復華金融股息　[便宜]`），不做大型卡片，不壓過後面的熱門前 10。區塊名稱「價格合理區」、說明「目前共有 X 檔 ETF 符合價格條件」；納入狀態為便宜＋合理。
9. **舊功能處理**：舊版獨立配息計算機已決定淘汰；`js/lookup.js` `lookupCustom()` 對不存在代碼產生估算價格／殖利率／配息天數的舊路徑，不為 Phase 5 修復或保留。ETF Detail 內正式的配息＋持有張數計算保留。
10. **其他記錄**：直向「持股異動」仍用展開分類標籤（Phase 3 既有設計）→ 列入 Phase 5 UX 統一。
11. **首頁成交量排行（PO 決策）**：演算法維持 `cur_vol` 成交量排序，**不改成 `heat`**（`heat` 只用於 `daily_check.py` 偵測新進前 100）；標題正式改為「**今日成交量 TOP 10**」；每列整列可點擊進入 ETF Detail。
12. **價格合理區 0 檔（PO 決策：方案 A）**：只顯示「目前沒有 ETF 符合價格條件」。**不再提供**舊版「最接近門檻 3 檔」fallback，也不放入未真正符合 cheap／fair 的 ETF 填版面。
13. **價格合理區排序（PO 決策）**：第一排序 cheap 在前、fair 在後；第二排序同一狀態內依 `cur_vol` 由高到低。超過 10 檔時預設前 10 也依此順序，其餘以「查看全部 X 檔」展開。

**Phase 5 價格合理區的 PO Gate 已全部完成。**

**Phase 5 Plan：Rev.4 APPROVED（`PHASE5_PLAN.md`，docs commit `d348cdf6`＝implementation 起點）。Codex：Router finding CLOSED、Plan PASS；GPT Gate 核准。不再出 Rev.5。**

**PO Change #1（2026-10-05，Plan 已更新，待 GPT Gate／Codex Plan delta review；CP2 尚未開始、未改前端與資料 pipeline）**
- Tools 改為三張大型功能卡：成交量排行／配息日曆／主動式 ETF 持股異動（PHASE5_PLAN §3 全改）。Active Flow 代碼列改單列橫向捲動選擇器＋完整名稱一行（新 F2，§8.3），紅綠方塊／treemap／加碼減碼／海外清單／資料與計算邏輯全保留。
- **Router 最小修改＝零新 API**：排行／配息日曆卡用既有 `tool` 層（push 一層，Back 回卡片；RT-12 與 Phase 3 已上線行為），持股異動卡用既有 `openFlow`（`switchPage('check')`）。`BASE_PAGE.tools` 維持 `page-tools`、`page-div` 保留為配息日曆子頁（只移除 B-1）。Router 程式仍只刪 `TOOL_PAGE.yt`（G1）。
- **被 PO Change #1 取代**：Rev.4 的同頁分段切換、`page-rank` 外殼、`page-div` 退役、`js/tools.js`／`sessionStorage etfRadar.toolsTab`／`Tools.setTab`、TL-1～5、TL-7、舊 RT-T1～T5、G2（已在 Plan 標記並移除，不並存）。
- 測試異動：新增 TC-1～8（TL-6 改名 TC-6）、RT-T1～T3（新內容）、FS-1～6（橫向選擇器）；§6.1 的 R switch page div、R rank find、T11、category TOOLS card、X2 改回「行為不變」（只改選擇器）；RT-12 完全不變。
- **G3 Codex Plan Delta Review NEED FIX → Gate 否決方案 A，改 source-aware Flow layer（Plan §3.4 已改寫，待 Codex Plan Delta Re-review）**：從哪裡進入就回哪裡——Tools `[]`→`[flow]` Back 回三張卡；Detail `[…,detail]`→`[…,detail,flow]` Back 回原 Detail（ETF／分頁／捲動／輸入）；排行 `[tool rank]`→`[tool rank,flow]` Back 回原排行（搜尋／定位／捲動）；分類原生分段（`setFolderView('flow')`）不變。
  - Router 最小修改（不新增公開 API）：新層 `{t:'flow', ui:{code}}`；`openFlow` intent 改為同 base push 一層（頂層已是 flow：同檔 null、他檔 replace），移除 `intentBase` 的 flow 分支；`sameLayer` 把 flow 視為同層（ETF 在 ui）；`apply()` 依最上層 flow／detail 的順序呼叫 `flowLayerShow／Hide` 並決定疊放。R1～R8、execute／popstate、RT-12 不動。
  - 畫面：新 `#flowLayer` 覆蓋面板，來源 page 與 Detail 不卸載只被覆蓋（狀態自然保留、不 `scrollTo`）；flow 內容節點只有一份，在 `#flowLayer` 與 `#catFlowHost` 間移動，共用 `renderFlow`。
  - 目前 ETF：Flow 層寫 `updateUi({code},'flow')`（replace，不新增 history、不碰 folder.ui）；分類原生仍寫 folder.ui.code。Back／Forward 靠 entry 的 ui＋uiCache，refresh 靠 init 還原＋資料到達後 apply。底部導覽用真正 stack 深度 traverse，無虛擬層。
  - 測試：改寫 TC-4、RT-T2、FS-5；RT-22、FL-4 期望改為回來源（行為改變，非放寬）；新增 RF-1～9（Tools 往返不累積、Detail 保留、排行保留、換 ETF 不寫 history／不污染 folder、Back／Forward／refresh、底部導覽清理、分類原生不變、疊放與 Esc、不捲來源頁）；FS-1～4、6 保留。

**Phase 5 implementation 進度（每個 checkpoint：Claude 實作＋測試 → commit → handoff → Codex Review，PASS 才進下一個）**

- **CP1｜P1 資料池（§5、§9 順序 1）— `be71744e`＋fix `c808dcdc`：Codex Re-review PASS／CLOSED（test_pool 54/54）。**
  - `fetch_etf.py`：篩選鏈②③④集中為 `pool_excluded(code, name)`；新增 `EXCLUDE_SUFFIX = L/R/U`；`EXCLUDE_KW` 補「正二」「反一」（其餘不動，債券池維持現況）。
  - ISIN 解析：`isin_sections()` 以 `colspan=7` 區段標題切段，只讀「ETF」「ETN」各到下一標題；`parse_isin_rows()` 檢查 CFI（ETF `CE…`、ETN `CM…`，不符印警告略過）；`parse_isin_pool()` 找不到 ETF 區段丟例外（該市場別失敗、不退回整頁），找不到 ETN 區段印警告、ETF 照收。
  - `etf_pool_cache.json` fallback 與 `CURATED` 也過 `pool_excluded`（防禦性）。
  - 測試：`tests/test_pool.py`（用 ast 只抽出篩選函式，不 import 整支腳本）EX-1～EX-11 共 47 項 PASS；fixture `tests/fixtures/isin_strmode{2,4}.html` 是 2026-10-05 ISIN 實頁節錄（ETF／ETN 全列、其他區段各 3 列）。負向對照：把 `EXCLUDE_SUFFIX` 改空 → 8 項 FAIL。
  - 實頁新舊比對（上市 199→195、上櫃 30→26）：移除 00682U、00693U、00763U、02001L（預期）；另移除上櫃「受益證券-資產基礎證券」區段的 01111S～01114S（中租賃，舊程式讀到頁尾才誤收；不在 market.json）。沒有新增任何代碼。
  - **未重跑 fetch／未改 market.json**：生效需跑 `fetch.yml` → `update-data.yml`，時機由 PO 決定（§5.3）；跑完後 00682U／00693U／00763U 會從「其他」消失、`daily_check` 可能觸發一次 TOP 100 通知（預期）。`category_test` band count 改比 live 計數的遷移放在 CP2 測試遷移一起做。
  - ~~實作備註：§6.1 殘字~~ → CP1 fix 已把 §6.1 `category_test` 遷移列的「stack＝`[tool div]`」改為「stack 仍為 `[]`」（只改文字，Router finding 不重開）。
  - **CP1 fix（Codex：ISIN 失敗走舊 `etf_pool_cache.json` fallback 時，01111S～01114S 資產基礎證券會回到候選池）**：cache 只有 `[code, name, is_otc]`、沒有 CFI，所以 fallback 加產品類型防線 `cache_product_ok(code)`＝代號須符合 `0[02]\d{2,4}[A-Z]?`。依據：2026-10-05 ISIN 實頁上市＋上櫃 ETF 區段 360 檔全為 00 開頭、ETN 21 檔全為 02 開頭，其他區段（股票、權證、特別股、TDR、受益證券）沒有任何 00／02 開頭代號。只套在 cache fallback（即時抓取已有區段＋CFI 防線）；`pool_excluded`、L/R/U、關鍵字、債券現況、020032 全部不變。
    - 新增 EX-7b 7 項：模擬 ISIN 兩市場都失敗 → fallback 舊快取；01111S～01114S 不進池、不補進 TWO_CODES；0050／00981A／00980D／00625K／020032／006201 恢復；00687C、02001L 仍排除；fixture 全部 ETF／ETN 代號 0 誤殺；現行 cache 229 筆只擋掉那 4 檔。`tests/test_pool.py` **54/54 PASS**。負向對照：防線放寬成 `0\d…` → 01111S 相關 2 項 FAIL。資料檔無變更。
- **Rev.4 修正（Router）**：撤回 Rev.3 的 `Router.setTool`。Tools「成交量排行｜配息日曆」改為 Tools 模組 UI state（`js/tools.js` 模組變數＋`sessionStorage` `etfRadar.toolsTab`），不寫 Router state、不新增 stack layer、不呼叫任何 history API；Tools 只有一個 base entry（base `tools`、stack `[]`，開 Detail 時 `[detail]`），所以 Router 的 `k = stack.length − p` 與 Phase 4 相同，切過分頁後離開 Tools 不多退、不離站。`page-rank` 改為 Tools 外殼（含兩個 pane），`page-div` 的 B-2 搬入後退役；`BASE_PAGE.tools → page-rank`、`TOOL_PAGE` 只留給既有帶 tool intent（RT-12）。新增 RT-T1～T5，TL-1～5、TL-7、G2 同步改寫。
- **Rev.3 修正**：① history 依現行封版 Router：底部導覽／首頁入口切 base＝replace E0（不新增 entry，Back 不回首頁）；`Router.setTool` 只 replace Tools 目前 entry 的 stack，不 push／traverse；排行 → Detail＝push detail、Back 關閉回同分頁；新增 §3.6 對照表；RT-12 Router 行為不變、只把 Back 後頁面期望改為預設分頁 `page-rank`。② ETN：ISIN 頁 ETF 與 ETN 是不同區段（現行從 ETF 讀到頁尾才順帶收 ETN），Rev.3 明確解析兩區段、各到下一個標題；L／R／U 兩者都適用；EX-9～11（020032 positive、區段邊界、缺 ETN 區段）。③ Detail 試算遷移：`#dtCalcOut` 驗「單次可領」「N 張市值約」隨張數連動，不要求「天後」；倒數在配息資訊區驗；不改 Phase 2 文字。
- **GPT Gate／PO 對 Rev.1 D1～D6 的決定（已寫入 Rev.2，不再詢問）**：債券資料池維持現況（不大量加回既有規則排除的債券）；首頁「查詢其他 ETF」`lookupToday()` 直接淘汰、假估算不修不留；前端 `LAZY_WATCHLIST` 實作後確認無 JS 引用即刪除，Python 三份不動；價格合理區標籤用「合理」（非「合理✓」）；Dark／Light 與全站色彩美化納入 Phase 5；B-1 計算機與 `lookupCustom()` 淘汰。
- **Rev.2 範圍**：首頁入口大廳（A-1 → 我想看看 ETF／我已經有 ETF → 價格合理區 → 今日成交量 TOP 10）、首頁沿用 Header 全站搜尋、Tools 同層切換（成交量排行｜配息日曆；預設排行；切換以附加 `Router.setTool` replace 不新增 entry；排行 → Detail → 返回保留捲動與 `rankFind`）、Header 低調 YouTube（外部連結）並移除首頁底部／Tools 舊入口、`page-yt` 退役（待 Gate G1）、資料池篩選鏈 ①～⑦（新增字尾 L／R／U、區段解析不再退回整頁、00687C 由「債」關鍵字排除＝維持現況）、舊功能 dependency migration（`ETFS`／`CALENDAR` 移到新 `js/state.js`、`calc.js`／`lookup.js` 退役、七項既有測試遷移到正式入口）、Dark／Light（Header 切換、localStorage `etfRadar.theme`、跟隨系統）、全站 token 化（含 Active Flow treemap 色值，紅＝加碼綠＝減碼不變）、UX closeout（「合理✓」全站改「合理」等）、直向持股異動 `cat-sw` 切換分類（橫向維持直接標籤）、最終 iPhone／Samsung Dark＋Light QA。
- **待 GPT Gate 確認（非 PO 產品決策）**：G1 `page-yt` 退役、Header 圖示直接開外部頻道；G2 Tools 分頁以附加 `Router.setTool`（replaceTop）實作。

### 0.2 Product Owner 最終決策（不要重新詢問）

- **00920 富邦ESG綠色電力、00923 群益台ESG低碳50、009809 富邦淨零ESG50 → 主題型。** 依一般使用者瀏覽時的直覺歸類。不建立僅為 00920 的名稱覆寫。
- **自選：Phase 3 僅做空狀態頁**「我的自選／自選 ETF 功能即將開放」。收藏、取消收藏、localStorage、排序等完整功能留到 Phase 4。
- D11–D13、D15–D17：採 Plan 預設，不需再詢問。
- **LR-4：已決定（PO 2026-10-05，方案 B），Codex 已確認 PASS／CLOSED。** 鍵盤開啟且可用清單高度不足 44px 時，不強制顯示清單，改顯示「收起鍵盤以查看 ETF 清單」。免責聲明保留、不隱藏。鍵盤收起後清單自動恢復，排序、已展開數、捲動不遺失。

### 0.3 Phase 3 核心產品原則

- 「**分類是拿來逛的，搜尋是拿來找的。**」分類服務不知道要找哪一檔的新手；搜尋服務已知代碼或名稱，或不知道歸類的人。不要為了讓分類解決所有交叉屬性而把規則做得過度複雜。
- **8 個 TAB 資料夾分類**：桌面式堆疊，左右各 4 份，有堆疊感，8 個 TAB 都必須能辨識。點選後：選定資料夾抽出 → 放大打開 → 顯示 ETF 清單；其他資料夾退至次要位置。動畫約 200–300ms，支援 prefers-reduced-motion。
- **Bottom Navigation 固定：首頁｜分類｜自選｜工具。** 不新增第 5、第 6 個主導覽。
  - 配息、排行 → 工具（子頁）。
  - 主動式 ETF → 分類 → 主動式（持股異動為分段）。
  - YouTube 頻道 → 工具底部連結，並保留首頁適當入口。
- 八個資料夾維持單一歸屬。高股息資料夾 22 檔與搜尋「高股息」約 76 檔可以共存，不要求一致。資料夾說明用「主要以高股息策略為特色的 ETF」。
- 不新增高股息標籤篩選器。不 hard-code 示意 ETF。分類內容由實際 `market.json` 產生。

### 0.4 工作流程

- **Claude = implementation**：寫程式、測試、文件、commit。
- **Codex = code review / QA**：審查 commit，指出 blocker，驗證測試。
- **Product Owner（怡恩）= 產品決策與真機測試。**
- **Coding 完成後先交 Codex**，不直接要求 Product Owner 測試。Codex 通過後，才由 Claude 提供 Product Owner 真機測試步驟（逐步操作，附 PASS／FAIL 判準）。
- 不 push，除非 Product Owner 明確要求。
- **PO／GPT Gate 已決定（不要重新詢問）**：
  - inside／doorway 狀態模型：APPROVE。進入分類 → inside（其他分類立即收合）；主 TAB 的 ▾／▴ 或標題區 → doorway；doorway 選另一分類 → 新 inside。
  - 不做「回頂自動展開」gesture。
  - D2（說明行）：暫緩，本輪不隱藏。D3（持股異動分段）：維持原樣。D4（查看更多入清單底部）：APPROVE。D5（直向列表隱藏重複的 `#catFoot`）：APPROVE，`.site-footer` 不隱藏。
  - D6（鎖定頁面）：**不採用**。不用 `body.cat-lock`，不做 scrollY 記錄與恢復，手機頁面維持正常捲動。
  - 不採側邊 TAB A／B。
- 不擴張 scope。不因測試方便而降低或刪除既有行為驗證。

### 0.5 Phase 3 Coding 狀態（目前）

- **實作鏈**：`99ec4b14` → Codex NEED FIX → `8e3e59bb` → `c050c719` → `7b750336`（LR-4，Codex PASS）→ `1f636d86`（844×390 blocker）→ `fdc1d139`（inside／doorway，Codex PASS）→ `3be2d19c`（visualViewport 底部錨定，Codex PASS）→ `1418695a`（renderList 重建保留位置，Codex PASS；真機重測 PASS）→ **`395c774e`（UX-1、UX-2，Codex PASS）**。**Codex 已全部 PASS，目前等待 PO iPhone + Chrome 最終真機驗收。不要重新 review `1418695a..395c774e`。**
- **UX-1（空白）**：來源為 44px ▾ 按鈕撐高標題列（46 → 54px）＋頁面頂端 14px padding，文字距金色提醒 31px。調整（僅直向 `cat-ctl`）：頁面頂端 14 → 8px、標題列 padding 歸零、高度 36px。結果：間距 15px。
- **UX-2（切換分類）**：按鈕移到分類說明列（`.cat-subrow`，與說明同列），文字「切換分類 ▼」（inside）／「切換分類 ▲」（doorway），99×44px 整個可點擊。標題列保留全寬（「科技／半導體」不截斷；標題放不下按鈕與長名稱，故改放說明列）。`aria-expanded` 保留，`aria-label` 含「切換分類」。主分類標題仍可切換（Gate 核准），按鈕與標題各只切換一次。
- **自動測試（`395c774e`）**：
  - router_test 64/64；search_compact_test 38/38；detail_ui_test 42/42；detail_history_fix_test 14/14；regression_test 14/14；detail_collapse_test 25/25；detail_state_test 42/42。
  - category_test 186 PASS、0 FAIL、**1 DEFER**（LR-8 真機）。UX 區塊：間距 10–20px、按鈕文字與尺寸、位於說明列、點擊一次、標題與按鈕不衝突、長名稱不截斷、橫向不顯示。
  - 負向對照：`1418695a` 下 UX 相關 14 項 FAIL（間距 31、標題列 54、按鈕仍為 ▾）。
- **Codex 本輪範圍（只看 `1418695a..395c774e`）**：
  - `index.html`：`.cat-subrow` 結構與按鈕位置、版本號 `20261005o`。
  - `js/category.js`：`syncMode` 的按鈕文字與 aria、`#page-cat` 的 `cat-ctl` 同步。
  - `css/category.css`：`.cat-subrow`、`#page-cat.cat-ctl` 頂端 padding、標題列 padding、tight3 grid 的 `sub` 區域（空時零高度）。
  - `tests/browser/category_test.py`：UX 區塊、PT 的文字期望更新。
  - 確認 renderList／D4、visualViewport 錨定、LR-4、cat-tight3、844×390、橫向未 regression。
- **不要重審**：renderList（已真機 PASS）、visualViewport 錨定、LR-4、Finding 1–3、844×390 blocker、inside／doorway 既有結論、Router、Detail、Flow。
- **DEFER（不算 PASS）**：LR-8 B／C（headless 無法產生 offsetTop > 0，留給 iPhone 真機）。
- **最終真機驗收（iPhone + Chrome，Codex 已 PASS，待 PO 執行）**：
  1. 直向 inside：金色提醒與分類標題之間間距正常（不貼齊、不過大）。
  2. 按「切換分類 ▼」：進入其他分類顯示，按鈕變「切換分類 ▲」；再按回到 inside。
  3. 點主分類標題：同樣切換一次。
  4. 「科技／半導體」完整顯示，不被截斷。
  5. 高股息滑到底、Detail 關閉：「查看更多」仍可見（回歸）。
  6. LR-8 B／C（headless DEFER，僅能真機確認）。

- **B6 警示條輕量化（`ec2eec09`）**：
  - 目標（PO）：390px 直向一般字級時，警示文字從 3 行變 2 行；警示存在、可讀，但不是主角。文字一字不刪。UX-1 的 15px 間距不動。
  - `index.html`：`.disclaimer` 移除純排版用的 `<br>`（前後兩句各以「。」結尾，無語意／a11y 需要）；資源版本 `20261005o` → `20261005p`。
  - `css/base.css` `.disclaimer`：16px／1.5／`6px 16px`／`.02em` → **14px／1.45／`4px 12px`／0**。全站唯一頂端警示條，所有分頁一致變更（預期）。不用固定高度、nowrap、overflow hidden、transform。
  - 實測（headless，Microsoft JhengHei）：320／360／375 → 3 行 70px（原 85，320 原 4 行 109）；**390 → 2 行 50px**；414／430 → 2 行 50px。各寬度無溢出、無裁切。14px 時全文約 698px，390 兩行可用 732px，餘約 34px（iPhone 蘋方與 emoji 寬度差的緩衝）。
  - `tests/browser/category_test.py`：AB 段與 RL 段視窗 390×844／800 → **809／765**（＝B6 前 844／800 的同一清單幾何），維持「清單需要捲動」前提；未刪減或放寬任何 check，並附註解。
  - 測試（`ec2eec09`）：category 186 PASS、0 FAIL、1 DEFER（LR-8）；router 64/64；search_compact 38/38；detail_ui 42/42；detail_history_fix 14/14；regression 14/14；detail_collapse 25/25；detail_state 42/42。UX-1（15px）、UX-2、LR-4、844×390、橫向、D4／renderList 皆 PASS。
  - 調整測試前，`category_test` 在 390×844 有 3 FAIL（AB-1 ×2、RL-1）。原因見 §0.7 Known Observation（既存行為，非 B6 regression）。
  - Codex 範圍：只看 `395c774e..ec2eec09`（不含資料 commit）。不修改 Category／Router／Detail／Flow。

- **文件夾說明／藏字（`3bde9239`）**：
  - PO 決策：分類說明從 inside 移到總覽 8 份文件夾的紙張上（頁籤＝名稱＋檔數）。目的是讓人在進入前就知道分類代表什麼，不是以省 inside 高度為 KPI。維持「桌上堆疊 8 份有 TAB 的資料夾」，不改成獨立卡片。UX-2 不動。
  - **藏字根因**：`#catNote`（「分類是主要方向…」）是一般排版的 `<p>`，而 `.cat-stack` 與 `.cat-band` 是 absolute，提醒文字因此落在整疊文件夾底下，從 8px 縱向縫與 12px 欄縫露出半截字，而且從來沒有被完整看到過。修正：改為 grid 第 5 列，位於整疊下方。
  - `css/category.css`：`.cat-stage` 改為 grid（2 欄，`repeat(4, 1fr) auto` 列）；`.cat-stack` 改 `display: contents`；文件夾 `position: relative`，`margin-bottom: -6px` 只疊前一份底部留白（padding-bottom 10px），保留 `--dx` 左右錯位、向上陰影與 z-index。1fr 讓 8 份同高（＝內容最高那份），不會只有單一份變高。`.cb-tab`（34px）＋`.cb-sub`（13px／1.45）。`.cb-name` 不再 nowrap／ellipsis（320px「科技／半導體」原本就被截成「科技／…」，現在改為自然換行）。`.cat-sub:empty` 零 padding。
  - `js/category.js`：`build()` 輸出 `.cb-tab`＋`.cb-sub`，移除 inline `top`；`refreshAll()` 的 `catSub` 改為留空（inside 不重複）。Router／Detail／Flow／D4 未動。
  - `js/category-rules.js` 文案（PO 核准）：市值型「追蹤大型、中型或特定市值指數的 ETF」、主題型「聚焦金融、工業、數位支付等特定主題的 ETF」、其他「ESG 篩選、期貨型等不屬前述分類的 ETF」。其餘 5 個不變。`PHASE3_PLAN.md` §分類表仍是舊文案（文件債，是否更正由 PO 決定）。
  - `index.html`：版本 `20261005q`。
  - 實測（headless）：320px 文件夾 102px（主題型、其他為 3 行，統一高度）；360／375／390／414／430px 文件夾 83px、步距約 77px、重疊 6px。390px 總覽 stage 220 → 371px（含提醒文字，現在可見）。各寬度無 overflow、無截斷、無遮蓋。
  - 測試（`3bde9239`）：category 212 PASS、0 FAIL、1 DEFER（LR-8；新增 FO 區塊 26 項：6 種寬度 × 同高、重疊僅底部留白、名稱與說明完整未被遮、提醒在整疊下方且無水平溢出；inside 不重複說明且按鈕位置不變；橫向空說明列零高度）。負向對照：舊程式下 FO 20 FAIL。router 64/64、search_compact 38/38、detail_ui 42/42、detail_history_fix 14/14、regression 14/14、detail_collapse 25/25、detail_state 42/42。UX-1（15px）、UX-2、LR-4、844×390、橫向、D4／renderList 皆 PASS。

- **ESG 分類＋inside 標題列（`88ad38cb`）**：
  - **A｜ESG → 主題型（做法乙）**：`js/category-rules.js` 第 9 順位策略型（ESG、公司治理）由 `'other'` 改為 `'theme'`。其他順位與關鍵字不變，因此較明確的定位仍然優先（00878、00930、00932、00936、00961 這類 ESG／永續＋高息仍歸高股息）。實際移動 00850、00888、00928、00692（含公司治理，PO 核准）。分布 16／22／32／20／78／**25**／6／**4**。0057 富邦摩台不處理，維持 Observation。
  - 文案：主題型「聚焦 ESG、金融、數位支付等特定主題的 ETF」（原有「工業」，為了 360px 維持 2 行而省略；另一候選「聚焦 ESG、金融、工業等特定主題的 ETF」也是 2 行）；其他「期貨型或未歸入前述分類的 ETF」。兩段在 320px 為 3 行，其餘寬度 ≤ 2 行，文件夾仍同高（FO 測試）。
  - `tests/fixtures/etf_203.json`：只人工改 4 筆期望值、分布與 `_note`（fixture 原本由 repo 外的 Python 參照實作產生，這次沒有重跑，而是依 PO 決策逐筆更新）。
  - `PHASE3_PLAN.md`：新增 §3.0「現行正式決策」，並同步 §2.2、§2.3、§3.1 順序表（程式實際是主題型第 7、市值型第 8，舊表寫反）、§3.3、§3.4 標題、§4.1 文案、FX-4／FX-6、D-ESG-1、關鍵字表、附錄 D。
  - **B｜inside 標題列（方案 1）**：`index.html` 標題列為 `[catClose ←] [名稱] [catSortBtn 代碼 ⇅] [catExpand 切換分類 ▼]`，`catExpand` 從說明列移入標題列；`#catCount` 移除。`catClose` 的 aria-label 改為「返回分類」，用 CSS `order: -1` 排在最左；點擊仍呼叫 `Router.closeFolder()`（Router 未動）。排序按鈕文字改為「代碼 ⇅／名稱 ⇅」，aria-label 為「排序：代碼，點擊改為依名稱排序」等完整語意。
  - `css/category.css`（只作用於 `cat-ctl`，也就是直向、列表、非鍵盤）：標題列 `flex-wrap: wrap`、`column-gap` 與 `row-gap` 6px；標題 `flex: 1 0 auto`（不縮、不截斷）；← 為 44×44；切換分類 `margin-left: auto`（換行時靠右）；頁面頂端 padding 8 → 4px，讓 UX-1 間距維持 15px。全域只改了 `.cat-back { order: -1 }`：橫向和 tight3 的返回鍵同樣在左側，文字由 ✕ 改為 ←，尺寸仍沿用 `.cat-btn`／tight3 的既有規則。說明列為空時零高度。
  - 實測（headless）：360／375／390／414／430px 標題列單列 44px；320px 為兩列（第二列是切換分類，靠右）。「科技／半導體」各寬度都不截斷，UX-1 間距各寬度都是 15px。390px 清單頂端 260 → **220px**（−40px）。360px 單列只剩約 5px 餘裕；iPhone 蘋方字寬如果稍寬，會自動變成兩列（不會截斷）。
  - 測試：category **250 PASS、0 FAIL、1 DEFER（LR-8）**。新增 HD 區塊：6 種寬度 × 返回鍵、名稱、排序、切換分類與單列／兩列，加上排序切換、doorway、← 回到總覽；另新增 FX ESG 抽樣（ESG＋高息 4 檔仍歸高股息、00763U 仍歸其他）。UX-1／UX-2 與 FO 的期望值改成新結構（按鈕在標題列）。router 64/64、search_compact 38/38、detail_ui 42/42、detail_history_fix 14/14、regression 14/14、detail_collapse 25/25、detail_state 42/42。負向對照：舊程式下 36 FAIL。
  - **AB／RL 視窗 809／765 → 769／725**：標題列少一列後，清單多出約 40px，在 809 又碰到 §0.7 的 Known Observation（清單剛好全部放得下）。改用 769／725 後，清單幾何與原本 844／800 完全相同（h 479、max 7），沒有放寬任何檢查。

### 0.6 下一步

- **Phase 3 已 VERIFIED / CLOSED**，沒有待審或待測項目。不要重新 review 或重測已封版的 checkpoint。
- **下一位：Codex｜Plan Re-review（Phase 5 Rev.3）→ GPT Gate**：審查 `PHASE5_PLAN.md` Rev.3。核准前不 coding、不要求 PO 真機。Phase 4 已 VERIFIED / CLOSED，不再審查。

- **觀察項（不是待辦，現在不改程式）**：低高度橫向下「持股異動」treemap 可能落在導覽列下方（見 §0.7）。真機驗收後由 PO 決定是否處理。

### 0.7 已知限制（記錄，不是待辦）

- LR-4：已決定為 responsive fallback（見 0.2）。
- 844×390 無鍵盤的清單可見性：已由 blocker `1f636d86` 修正（清單 277–324px）。
- 直向 doorway 模式不寫入 history：Back／Forward 回到同一分類時，模式依 Category 目前狀態。
- 直向頁面向下捲動後，標題列與 ▾ 會捲出畫面，需向上捲回才能展開（依 Gate，不做回頂自動展開）。
- 直向鍵盤開啟（gs-ckm）時，展開控制與次要標籤列隱藏，依既有 gs-ckm 路徑。
- 中段但距底部 ≤ 約 44px 時，工具列收合（視窗變大）會被瀏覽器夾到新底部（修正前亦然，未處理）。
- Plan §11.4 偏差：次要標籤保留一列 40px，未收合為「其他分類 ▾」（見變更紀錄）。
- 低高度下的「持股異動」檢視：`cat-tight3` 只作用於清單檢視，treemap 在 844×390 仍落在導覽列下方，需要頁面捲動。**標記為觀察項（PO 2026-10-05）**：現在不改程式，真機驗收後由 PO 決定是否處理。
- LR-8：需真機（見 0.5）。
- **Observation：0057 富邦摩台**追蹤 MSCI 台灣指數，性質接近市值型，但名稱「摩台」沒有命中任何關鍵字，所以歸其他。PO／Gate 2026-10-05：本輪不處理，不擴大分類規則。
- **Known Observation（PO／Gate 2026-10-05，B6 期間發現）**：當清單原本剛好完整放得下，而 viewport 隨後略微縮短時，查看更多可能被底部裁切約 16px；目前可透過輕微捲動看到。此為既存邊界行為，B6 只是讓原測試尺寸碰到此條件。本輪不修改 Category。
  - 佐證：B6 前在 390×879 → 835 同樣重現（max 0 → 16、scrollTop 0、查看更多不完整可見）；B6 後 390×844 → 800 結果相同。
  - 處置：Phase 3 最終 iPhone 真機驗收時再觀察；只有真機實際造成明顯 UX 問題才另開修正。
- R-N3：traversal 永不抵達的復原方式為重新整理（從實際 `history.state` 還原）。
- base 切換以 replaceState 進行，關閉 Detail 後留下的 forward entry 仍存在（與 Phase 2 相同）。
- ↻ 重新整理仍用 `location.replace`（Phase 2 既有限制：跨文件返回）。
- 分類開啟動畫為簡化版（頁籤微抬起、主區淡入），未做完整幾何 FLIP。
- 00850、00888、00928、00692 仍歸其他（PO 決策只涵蓋 00920、00923、009809）。
- 工具頁與自選占位為靜態 HTML，未建立 Plan 中預計的 `js/tools.js`。

### 0.8 測試環境（Compact 後需重建）

- HTTP：在專案根目錄執行 `python -m http.server 8765 --bind 127.0.0.1`。
- Chrome：`chrome --headless=new --remote-debugging-port=9223 --remote-allow-origins=* --user-data-dir=<獨立目錄>`。
- 執行：`python tests/browser/<name>.py`。Windows 主控台需設定 `PYTHONIOENCODING=utf-8`。
- 測試會讀取 `raw.githubusercontent.com` 的 `market.json`，需要網路。
- 同一個 Chrome 分頁跨執行會保留 history 狀態。若遇到首次還原或計數異常，請換新的 `--user-data-dir`。
- `detail_state_test.py` 與 `category_test.py` 開頭會停用快取並重新載入，避免瀏覽器拿到舊的 `js/*.js`（同一個 `?v=` 會命中快取）。其他測試若做負向對照，請先停用快取。
- Phase 3 的 fixture 為 `tests/fixtures/etf_203.json`（期望分類由 Python 參照實作產生）。

### 0.9 文件與 Git

- Push：截至 `395c774e`／`ca262607` 的 Phase 3 commit 皆已在 `origin/main`（自動行情排程帶入，PO 接受）。注意：本機行情排程會推 main，之後的本機 commit 也可能被自動帶上去。
- 文件債（需 PO 決定是否更正，不阻擋 Phase 3）：`PHASE1_CHANGELOG.md`、`PHASE2_PLAN.md` 仍有 Android 字樣（例如 PLAN 的 G1 測試代號）。
- 第 2 節的歷史紀錄全部已 RESOLVED，包括 Phase 2 blockers、Plan Rev.1～Rev.3.3 blockers、resync blocker、visualViewport、3 秒處理中、QA C7／C9 等。不要把它們當成目前待辦。


- **G3／PO Change #1：Codex Plan Delta Re-review PASS、G3 CLOSED、PO Change #1 正式核准**（Plan `e0f6aaaa`）。Codex 補充兩個測試前提，留到對應 checkpoint：RF-2 用真正有 Flow 資料且入口實際可見的 ETF／fixture；RF-8 Router 模擬用合法 ETF，且不得為測導航破壞紅綠方塊資訊顯示。
- **CP2｜§6 舊功能退役與 dependency migration（§9 順序 2）— `2ee3f64f`：Codex Code Review PASS／CLOSED（DS-10 確認為既有測試前置條件）。**
  - `js/state.js`（新，最先載入）承接 `ETFS`／`CALENDAR`；`calc.js`、`lookup.js` 整檔刪除，`index.html` 移除兩支 script。
  - 首頁 A-4 單檔查詢（`#todayCode`／`lookupToday`／`renderSignalCard`）移除；配息頁 B-1 計算機（`#chips`／`#customCode`／`#sharesIn`／`#calcOut`、`selChip`／`lookupCustom`）移除，`page-div` 只剩 B-2 日曆（保留為配息日曆子頁，§6 表）；`render.js` 刪 `selETF`／`renderChips()`／`calcUpdate()` 初始化。工具卡說明「配息計算機、近期配息日曆」→「近期配息日曆」（只改文字以免寫著不存在的功能；三張卡改版仍在 CP4）。
  - Detail 配息分頁試算（`#dtSharesIn`／`#dtCalcOut`、`.calc-*`／`.input-*`／`.num-input` CSS）不動。CSS 只刪 `.etf-chip(s)`、`.custom-*`、`.big-num`。`.buy-card`／`.range-*`／`.div-pill` 仍被首頁 A-2（render.js）使用，留待首頁 checkpoint。
  - `LAZY_WATCHLIST`：`render.js` A-2 與 fallback 仍引用 → **本 checkpoint 不刪**（Plan §6：首頁改版後 grep 無引用才刪；Python 三份不動）。MG-3 的 `LAZY_WATCHLIST` 斷言同樣延到首頁 checkpoint。
  - `archived-check.js` 全檔為註解，無 `selETF`／`renderSignalCard` 實際引用，不動。
  - 測試遷移（§6.1，非刪除）：regression「R page-div chip calc uses 0056」→「配息頁只剩日曆」＋Detail 0056 配息分頁 1→7 張：單次可領＝amount×張×1000、N 張市值約＝price×張×1000、年化領回連動、配息資訊倒數（N 天後／今日）；detail_ui T7「selETF untouched」→「Router 狀態不變」（shares kept、7 張市值保留）；新增 MG-1（`ETFS`／`CALENDAR` 由 state.js 提供、無 calc／lookup script）、MG-3（7 個退役全域皆 undefined）、首頁 A-4 已移除。R switch page div／yt、rank find、T11、category TOOLS card、X2 期望不變。
  - 結果（headless 800×600，port 8766／9224）：router 64、search_compact 38、detail_ui 42、detail_history_fix 14、**regression 26**（原 14：-1 遷移、+13）、detail_collapse 25、detail_state 42、category 250＋1 DEFER、watch 149＋4 DEFER，全 PASS。負向對照：試算改成不乘張數 → regression 2 FAIL。資料全擋（market／*.json blocked）＋切六頁＋`gs-ckm`：0 例外、`ETFS` 為空陣列。
  - 環境備註：detail_state DS-10 前置條件（績效分頁可捲動）在 390×844 視窗下因內容不夠高而 FAIL，改動前 baseline 亦同；以 800×600（過去跑法）全 PASS，非 regression。
- **CP3｜§2 首頁入口大廳（§9 順序 3）— `7a58425d`：Codex Code Review PASS／CLOSED（687 PASS／0 FAIL／5 DEFER）。**
  - 版面（390px 直向由上而下）：A-1 大盤（不改）→ 兩大入口（整塊 button，72px）→ 價格合理區 → 今日成交量 TOP 10。移除首頁 YouTube 入口卡、大型 buy-card／range／配息 pill、「為什麼今天沒有」說明；首頁無任何輸入框，查詢一律走 Header 全站搜尋（H2）。Header YouTube／主題鈕仍屬 CP5／CP7，未做。
  - 兩大入口：`switchPage('cat')`／`switchPage('watch')`，與底部導覽同一路徑（replace E0，`history.length` 不變，不期望 Back 回首頁）。
  - 價格合理區（render.js `_pzList`／`renderPriceZone()`／`homeTogglePz()`）：TOP100（`cur_vol`）中 cheap／fair 且 `div_frequency !== '不配息'`；cheap 先、同狀態 `cur_vol` 高到低；計數「目前共有 X 檔 ETF 符合價格條件」；>10 預設 10＋「查看全部 X 檔」／「收起」（`_pzExpanded` 只在記憶體，`renderAll` 輪詢重繪保留）；0 檔只顯示「目前沒有 ETF 符合價格條件」（無計數、無按鈕、無 fallback）；整列 button → `openDetail(code)`；標籤「便宜」`sig-cheap`／「合理」`sig-fair`。
  - 今日成交量 TOP 10：`cur_vol` 前 10（不用 heat），列改 button → `openDetail`，狀態文字「合理」（無 ✓）。排行頁等其他頁的「合理✓」屬 V3（CP8），本 checkpoint 不動。
  - `LAZY_WATCHLIST`：前端已無任何引用 → `js/config.js` 刪除、script 移除（§6）。Python 三份不動。
  - CSS：新增 `.home-entries／.home-entry／.home-row／.home-more／.home-empty／.home-sub／.home-note`（字級 ≥ 14px，入口副標 15px、說明 14px；整列 ≥ 48px）；刪 `.buy-*`、`.div-pill／.div-num`、`.empty-why`、`.entry-card`。`.range-*`（Detail 用）、`.empty-state`（共用）保留。
  - CLAUDE.md「頁面區塊代號」A-2／A-3／A-4／B-1 改為現況（全面文件更新仍在 CP8）。
  - 測試：新增 `tests/browser/home_test.py` 37 項（HM-1～3、PZ-1～13、TV-1～3、MG-3 `LAZY_WATCHLIST` undefined、390×844 下可見文字 ≥14px／按鈕 ≥44px／入口 ≥64px／無水平捲動／兩大入口在第一屏）。fixture＝實際 ETFS 深拷貝改寫 signal／cur_vol／div_frequency 後呼叫 `renderAll`（停掉 `_pollTimer`）。負向對照：排序改成 fair 先＋說明字改 12px → 6 FAIL（PZ-5／7／8／11、可讀性）。
  - 結果（800×600）：home 37、router 64、search_compact 38、detail_ui 42、detail_history_fix 14、regression 26、detail_collapse 25、detail_state 42、category 250＋1 DEFER、watch 149＋4 DEFER，全 PASS。390px 截圖目視：入口、列表、標籤無截斷或溢出。
- **CP4｜T1 三張功能卡＋G3 source-aware Flow layer＋F2 橫向 ETF 選擇器（§3、§3.4、§8.3）— `937abe70`＋fix `db4150dc`：Codex Re-review PASS（Detail 污染 CLOSED、無 regression）。**
  - Tools：`page-tools` 三張整卡 button（`#toolRank`／`#toolDiv`／`#toolFlow`，icon＋標題＋PO 文案＋›，84px）。排行／配息日曆沿用既有 `tool` 層（Back 回卡片）；持股異動卡＝`switchPage('check')`。YouTube 連結移除（Header 入口在 CP5）；`TOOL_PAGE.yt`／`page-yt` 仍在，CP5 退役。
  - Router（不新增公開 API，`Object.keys(Router)` 不變）：`intentFlow(code)`——頂層非 flow → 同 base push `{t:'flow', ui:{code}}`（k=0）；頂層是 flow → 同檔 null、他檔 replaceTop（新 id，避免 uiCache 用舊 code 覆蓋）。`sameLayer`：flow 對 flow 為同層。`apply()` 先算最上層 flow／detail 的 index → `flowLayerShow(ui, fi>di)`／`flowLayerHide()`，再 `applyFolder`。`intentBase` 的 flow 分支移除；`_NAV_SPEC.check` 改 `{flow:true}`。
  - 畫面：`#flowLayer`（與 `gsPanel` 同位置的 fixed 覆蓋層，‹ 返回＝`history.back()`；z 39，`.over-detail` 時 41；`dt-collapsed` 時 top:0；`gs-ckm` 時隱藏）。`#page-check` 節點只有一份，Flow 層開時移入 `#flowLayerBody`、關時移回 `#catFlowHost`；`Category.renderFlowFor` 在 Flow 層持有節點時不重繪。來源頁與 Detail 不卸載、不呼叫 `scrollTo`。
  - 目前 ETF：`flowSelect` 在 Flow 層 → `Router.updateUi({code},'flow')`；原生 → `Category.setFlowCode`（folder.ui.code，既有）。Flow 層以 null code 進入時沿用 `renderFlow` 預設，`setUi` 記到該層（不寫 history）。fetchFlow 完成時 Flow 層可見則重繪。
  - F2：`#flowChips` 單列 flex 橫向捲動（chip 改 button、≥44px、16px、選取＝中性藍 2px 框＋`aria-pressed`；刻意不用紅綠），`_flowChipIntoView()` 只調 `scrollLeft`；新增 `#flowSelName` 完整名稱，`flowMeta` 改為「持股 N 檔　期間」（名稱移到上一行）。紅綠方塊、treemap、海外清單、資料與計算不變。
  - 測試：新增 `tests/browser/tools_test.py` 70 項——TC-1～8、RT-T1～2（RT-T3＝router_test 64）、RF-1～9、FS-1～6。RF-2 用有 flow 資料且 Detail「查看完整持股異動」入口實際可見的 ETF（並先驗入口可見）；RF-8 以 `gsPick('0050')` 在 Flow 上開合法 ETF 的 Detail，驗疊放、Esc 逐層、紅綠方塊數量不變（未竄改 flow 資料）。FS-4 以同頁注入舊 4 欄 grid 樣式量測基準。
  - 既有測試期望更新（G3 行為改變，非放寬）：router RT-22（排行 → Flow → Back 回排行）、watch FL-4 ×4 base（Detail → Flow → Back 回原 Detail、同分頁；Forward 回同檔 Flow）、detail_ui T13（Detail 上開 Flow、無 popstate、Back 回 Detail；42→43）、regression「switch page check」（Flow 層蓋在來源頁上）、category「TOOLS card」改點 `#toolDiv`。router RT-14～21 的 traversal 驅動改用 `openFolder('mcap')`（openFlow 已不 traverse），R4～R8 斷言不變。
  - 負向對照：flowSelect 改寫 folder＋選擇器改 wrap → tools_test 7 FAIL（RF-4、RF-5、FS-1、FS-3、FS-4）。
  - 結果（800×600）：tools 70、home 37、router 64、search_compact 38、detail_ui 43、detail_history_fix 14、regression 26、detail_collapse 25、detail_state 42、category 250＋1 DEFER、watch 149＋4 DEFER，全 PASS（761 PASS／0 FAIL／5 DEFER）。390px 截圖目視：三張卡、Flow 層、選擇列與名稱、紅綠方塊正常。
  - **CP4 fix `db4150dc`（Codex NEED FIX：Detail → Flow → 第二個 Detail → Back 污染原 Detail）**：根因＝`[detail, flow, detail]` 共用一個 Detail 面板，`detailShow()` 只比代碼（同檔 A→Flow→A 直接沿用畫面），`_dtSaveUi()` 不存張數。修正：`apply()` 傳 detail 層 id；`detailShow(code, ui, layerId)` 以層 id 判斷同一層，不同層依該層 ui 還原分頁／捲動／張數（ui 無 `shares` 時保留輸入框現值＝Phase 2 語意）；`_dtSaveUi` 加 `shares`，張數輸入即寫入該層；`_dtIsMyLayer` 比對層 id；`detailGoFlow` 進 Flow 前先 `_dtSaveUi(true)`。Router 規則、公開 API、Flow／folder 寫入方式不變。
    - 新增 tools_test RF-10（00996A 7 張・持股・捲動 → Flow → 全站搜尋開 0056 改 2 張・績效 → Back → Back）、RF-11（同一檔 00996A → Flow → 00996A）各 8 項：兩個 detail 層 id 不同、第一層 ui 未被寫入、Back ① 回 Flow 且紅綠方塊數量不變、Back ② 回 A 的 ETF／7 張／持股分頁／捲動、Forward ×2 回第二個 Detail 自己的狀態。負向對照：detail.js 還原成 `937abe70` → RF-10／11 各 2 項 FAIL（重現 Codex 的 2 張與分頁污染）。
    - detail_ui T7：張數現在記進 Detail 層 ui → 改驗「輸入後該層 ui.shares＝7」＋「之後的資料更新不改 Router 狀態」（43→44）。
    - category「UI band counts」依 PHASE5_PLAN §5.3 改比 live `catClassify` 計數（CP1 預定的遷移，先前漏做；今天資料池依 P1 更新後「其他」4→1，live ≠ fixture 才浮現）。FX-*（fixture 驗分類規則）不變。
    - 結果（800×600）：tools 86、home 37、router 64、search_compact 38、detail_history_fix 14、regression 26、detail_collapse 25、detail_state 42、category 250＋1 DEFER、watch 149＋4 DEFER 全 PASS；**detail_ui 44 中 41 PASS／3 FAIL（T4、T17×2）**——依賴 live 行事曆中 00939 的 2026-10-05 官方公告，今日資料更新後該筆已從 calendar 移除；在未改動的 `937abe70` 上同樣 3 FAIL，屬資料老化，非本次修正造成，未改（Phase 2 測試，待 Codex 判斷是否改 fixture）。總計 772 PASS／3 FAIL／5 DEFER。

- **Test maintenance：detail_ui T4／T17 — `546f7e9e`：Codex 複審 PASS／CLOSED。→ CP4 正式 CLOSED（baseline 779 PASS／0 FAIL／5 DEFER）。** Codex 判定 3 個 FAIL 為測試維護：原本依賴 live 行事曆的 00939 2026-10-05 官方公告，資料更新後被移除。
  - 改法：`FX939` 定義 `window.__fx939(today)`，在同一個同步 evaluate 內注入 00939 官方公告（`iso_date` 2026-10-05、`amt` 0.12、`amount_source` TWSE、`source` official）與 `div_next` 2026-11-01，`Date.now` 固定在台北時間 today 01:00，讀 Detail 配息分頁與試算後在 `finally` 還原（Date.now、CALENDAR、div_next；00939 不在 ETFS 時以 0050 複本補上並移除）。頁面重新載入後（T17 前）再定義一次。
  - T4（today 2026-10-03）：原兩項斷言不變（官方公告＋2026-10-05、不取 div_next 11-01），另加受控日期、「（2 天後）＋單次可領＋依公告金額試算」、fixture 還原檢查。
  - T17（today 2026-10-06）：原兩項斷言不變（「已過」且無「天後」、「計算停用」），另加受控日期檢查。T18 不變。
  - 沒有 skip、沒有放寬 assertion、產品程式未改。負向對照：把 `_dvView` 的 `offIso >= today` 拿掉 → T17 兩項 FAIL。
  - 結果（800×600）：detail_ui 48（44→48）全 PASS；完整 regression：tools 86、home 37、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 26、detail_collapse 25、detail_state 42、category 250＋1 DEFER、watch 149＋4 DEFER＝779 PASS／0 FAIL／5 DEFER。

- **CP5｜Y1 Header YouTube＋G1 page-yt 退役（§4、§9 順序 5）— `86500f11`：Codex Code Review PASS、GPT Gate CLOSED。**
  - Header `.topbar` 右側改為 `.hdr-actions` 按鈕群：`#hdrYt`（`<a>`，inline SVG YouTube 圖示、44×44、`href` 頻道、`target="_blank"`、`rel="noopener noreferrer"`、`aria-label="金流黑盒子 YouTube 頻道"`，不經 Router）＋既有 `#refreshBtn`（`reloadData()` 不變，尺寸統一為 44×44、補 aria-label）。標題與 `#statusBadge` 留在左側原位。主題切換鈕屬 CP7，未做。
  - `page-yt`（HTML）與 `.yt-*` CSS 移除；`TOOL_PAGE` 刪 `yt`（舊 history entry 若帶 `tool yt`，`applyBasePage` 落回 `BASE_PAGE.tools`＝工具卡片頁）。`_NAV_SPEC.yt` 改 `{external: 頻道}`，`switchPage('yt')` 以 `window.open(url,'_blank','noopener')` 開外部頻道、不寫 history。`logo.png` 已無引用但檔案保留（未刪資產）。
  - 首頁 YouTube 大卡（CP3）、Tools YouTube 卡（CP4）維持移除；全站只剩 Header 一個 youtube.com 連結。
  - CLAUDE.md 頁面區塊代號 C-1／C-2 標記退役。
  - 測試：regression_test 新增 9 項——YT-1（a 連結、在 Header、≥44×44、href／target／rel／aria、點擊不改 history 與 Router 狀態、不影響 statusBadge／↻、390px 下標題與徽章不截斷不重疊、搜尋列 ≥340px、無水平溢出）、YT-2（`switchPage('yt')` 以 noopener 開同一連結且不換頁不寫 history、`page-yt` 不存在、首頁／工具頁無 YouTube、只剩 1 個 youtube 連結、舊 entry `tool yt` 經 popstate 還原落回工具卡片頁）。switch page 迴圈去掉 yt（check 改為疊在配息日曆子頁上）。26→34。
  - 結果（800×600）：tools 86、home 37、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 34、detail_collapse 25、detail_state 42、category 250＋1 DEFER、watch 149＋4 DEFER＝787 PASS／0 FAIL／5 DEFER。360px 截圖目視：標題、徽章、兩顆按鈕、搜尋列不擁擠。

- **CP6｜F1 持股異動直向切換分類（§8.2、§9 順序 6）— `4053c4a4`：Codex PASS、GPT Gate CLOSED。**（Gate／PO 確認：CP6 只做 F1；F2 selector 已於 CP4 完成，本 checkpoint 不動）
  - `js/category.js`：`swActive()`＝已開資料夾＋直向＋非 `gs-ckm`；`ctlActive()`＝`swActive()`＋`view==='list'`。`syncMode()` 對 `#catMain`／`#page-cat` 切 `cat-sw`（兩種檢視）與 `cat-ctl`（只清單），`cat-inside`＝`cat-sw && !stripOpen`，按鈕文字／aria 依 `cat-sw`。`toggleStrip()` 以 `swActive()` 為條件，持股異動時展開／收起後 `flowRedrawIfVisible()`。`applyFolder` 的 `stripOpen=false` 條件由「flow→list」擴為「view 改變」（清單 doorway → 持股異動也預設收起）。
  - `css/category.css`：`.cat-expand` 顯示、標題列單列化（wrap／gap）、標題、← 44px、切換分類靠右、頁首 padding 由 `cat-ctl` 改掛 `cat-sw`；`> .cat-more`、`> .cat-foot` 隱藏仍只在 `cat-ctl`；`cat-inside > #catStrip` 不變。
  - 橫向、鍵盤不套 `cat-sw`；`stripOpen` 不寫 Router；`flow.js`、F2 selector、Flow 層、資料與計算未改。`index.html` 只改這兩檔的快取版本參數（範圍外但只是 `?v=`）。
  - 測試：category_test 舊 PT-9「持股異動檢視不啟用 inside、次要標籤列顯示」依核准規格改寫（直向收起、橫向顯示），新增 SW-1～6 共 20 項：直向持股異動預設 inside＋「切換分類 ▼」44px＋← 44px＋標題列單列（≤52px）；無清單專屬行為；▼／▲ 與點標題切換、不寫 history／Router；展開時 treemap 下移、收起回原位、重畫不溢出；doorway 選高股息 → 進高股息清單（replace，history 不增）；清單 doorway → 持股異動預設收起、持股異動 doorway → 清單回 inside；橫向不套 cat-sw、標籤直接顯示、treemap 依寬度重畫；轉回直向恢復；鍵盤不套 cat-sw；F2 selector 單列＋完整名稱仍在。250→270 PASS。負向對照：category.js／category.css 還原為 CP5 版 → 8 FAIL。
  - 結果（800×600）：tools 86、home 37、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 34、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝807 PASS／0 FAIL／5 DEFER。390px 截圖目視：← 主動式 … 代碼⇅ 切換分類 ▼ 單列，分段下方直接接 selector 與紅綠方塊。

- **PO Change #2（Plan `4222de54`）：成交量排行第一屏（CP6b，§3.8）**。排程 CP6 → CP6b → CP7 → CP8 → Final。排行搜尋維持**定位**（PO 選 A，不用「篩選」字眼）；RK-1 依 Gate 核准方案 1：sticky ≤120px、完整 ≥4 列＋第 5 列部分可見（≥5 列在保留 Header／全站警示／44px 標題列／109px 卡片下無法達成，不縮卡片）。
- **CP6b — `e3852d6a`；Codex NEED FIX 2 項 → fix `768844d2`（見本段末），Codex 限定複審 PASS → **CP6b CLOSED**。**
  - `index.html`：`.rank-sticky` 改為 `.rank-top`（「成交量排行」＋`#rankFindBtn` 🔍＋`#rankInfoBtn` ⓘ，各 44×44、`aria-expanded`／`aria-controls`）、`#rankFindBox`（既有 `#rankFind`，placeholder「在排行中找 ETF」、`#rankFindClear`、`#rankFindMsg`）、`#rankInfo`（原兩段文字逐字、`#rankTotal`），兩個區塊預設 `hidden`；欄位名稱 `.rank-hdr` 不變（只縮內距）。
  - `js/rank.js`：`_rankFindOpen`／`_rankInfoOpen`、`rankToggleFind()`（展開時 `focus({preventScroll})`）、`rankToggleInfo()`、`_rankSyncTop()`；輸入有內容即保持展開；`clearRankFind` 同步。定位邏輯（`applyRankFind`、捲動扣 sticky 高度、榜外提示）未改。
  - `css/pages.css`：`.rank-top／.rank-title／.rank-ic(.on)／.rank-info`，`[hidden]{display:none}`；`.rank-hdr` padding 9/10 → 6、margin 8 → 6。標題色沿用原 #FFD700（CP7 token 化）。
  - 實測（390×844）：sticky **114px**（原 210）、第一筆 **y=300**（原 395）、完整可見 **4 列**（原 3）、第 5 列 top 768 < 導覽列 782（露出 14px）；捲動後 sticky 114px 黏在 Header 下。
  - 測試：新增 `tests/browser/rank_test.py` 22 項（RK-1 第一屏數值／display:none、RK-2 🔍 展開＋焦點＋placeholder＋無「篩選」字樣＋有內容時 ⓘ／輪詢不收起、RK-3 ⓘ 原文逐字＋筆數、RK-5 不寫 history／Router、RK-6 Detail 與 Flow 往返保留展開／內容／定位／捲動、RK-7 橫向與 gs-ckm 無溢出、文字 ≥13px）。RK-4：tools_test TC-6、RF-3 與 regression「R rank find 0050」各加「先展開 🔍、輸入框可見」一步，原斷言不變（TC-7 沿用 TC-6 的展開）。
  - 另修測試偶發 FAIL：TC-2／TC-3／TC-4（tools_test）與 PZ-11（home_test）原斷言 history.length 恰好 +1／≥L，但 push 會清掉先前 Back 留下的「多筆」forward entry，長度可能不增反減 → 改為 ≤ L+1，「確實多一層」仍由 stack 檢查與下一步 Back 驗證。非產品問題。
  - 負向對照：index.html／pages.css／rank.js 還原為 CP6 版 → rank_test 多項 FAIL＋未捕捉例外。
  - 結果（800×600）：rank 22、tools 88、home 37、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝832 PASS／0 FAIL／5 DEFER。
  - **CP6b fix `768844d2`**
    - FIX-1（定位列被 sticky 遮住）：原公式只扣 `.rank-sticky` 高度，但 sticky 黏在 Header 下方（`top: var(--hdr-h)`）。新增 `_rankOccludedTop()`＝max(Header 若 `position:sticky` 則其 `offsetHeight`, 排行 sticky 若 `position:sticky` 則 `parseFloat(computed top)＋offsetHeight`)；gs-ckm（Header static）與矮螢幕（sticky static）自動不計。實測 390×844：00406A（第 1 名）修正前 y=204～313、sticky 底 314（Codex 重現值）；修正後 y=326～435；第 5／34／51／67 名 y=326、第 100 名 y=506（頁尾不能再捲），全部在 sticky 下方、導覽列（782）上方。
    - rank_test 新增 RK-4b 22 項：6 個名次（1、5、34、51、67、100）定位後整列可見、列中心 `elementFromPoint` 命中該列、仍 100 列；ⓘ 展開時亦然；第一／中間／最後一檔 tappable 列在可見中心點擊 → 開該檔持股異動。⚠ 排行列本身沒有「點擊開 Detail」——既有設計是 tappable（有 PCF）列 → Flow、其他列無點擊動作；Plan §3.5 寫「排行列 → openDetail」與實作不符（CP4 起即如此，TC-7 用程式呼叫 openDetail）。本輪不改產品行為，請 Gate 判斷是否需要另開項目。
    - FIX-2（push 防線）：TC-2／TC-3／TC-4、PZ-11 加 `history.pushState`／`replaceState` 計數 spy：斷言 pushState 恰好 1 次、push 後 `history.state` 與 `Router.state()` 結構一致（base＋各層 t／id／code／key；不比 ui——Flow 層預設選取依 §3.4.3 只 `setUi` 進記憶體）、頂層型別／代碼正確；`history.length` 只保留 ≤ L+1。Router 未改。
    - Mutation：(1) `pushEntry` 改 `replaceState` → TC-2、TC-3、PZ-11 push 防線 FAIL（push=0），之後 Back 直接離站使 tools_test 中斷（TC-4 未執行到，等同 FAIL）；結構比對在 mutation 下仍 same=True，證明 push 次數這條才是關鍵防線。(2) rank.js 還原舊 offset → RK-4b 12 項 FAIL（第 1 名 y=204～313 被遮）。
    - 結果（800×600）：rank 44、tools 91、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝858 PASS／0 FAIL／5 DEFER。
  - **B（只記錄，未執行）**：GPT Gate 提供的 Active Flow／PCF 線索（00407A 10/06 股數異動 0；00983A NVIDIA、RKLB 加碼，TSLA、WGS、XE 減碼，第三方 10/06／10/07 日期定義不一；00986A 10/05 逐筆可核；00996A 10/05 尖點、景碩、汎銓加碼，矽力-KY、致茂減碼，10/06 異動日待核）。僅為除錯線索，不寫入正式資料。正式調查若開啟，順序＝投信官方 PCF → 原始持股股數逐日比較 → 第三方交叉驗證；以股數變化判定、不以權重；第三方日期定義不得混用；官方有新 PCF 而專案停在舊日期時沿 Download → Parse → Compare → Write → Publish／Monitor 追中斷點；官方無新 PCF 不得自行製造異動。待 CP6b CLOSED 後由 GPT Gate／PO 決定何時啟動。本輪未改 pipeline、未改資料。

- **CP6c｜排行／日曆 Detail navigation 規格校正（Plan `86cb7b83`，§3.5）— `b9aeccf4`，Codex NEED FIX 1 項（柱狀圖 tooltip regression）→ fix `2703a7a5`：Codex 限定複審 PASS → **CP6c CLOSED**。**
  - 調查（記入 Plan）：§3.5「排行列／日曆列 → openDetail」自 Rev.4 寫入，「既有」指 Router intent，UI 從未接線；排行列自 `599a5ecc` 起只有 PCF 列可點且開 Flow，日曆列從無點擊；CP4／CP6b 測試以程式呼叫 openDetail 或只點 tappable 列，所以沒抓到。
  - `js/rank.js`：排行列移除 inline `onclick`；每列 `.rank-hit`（覆蓋整列的 button，aria-label「第 N 名 代碼 名稱，查看詳細資料」）＋兄弟 `.rank-flow` button（「持股異動 ›」，aria-label「查看 代碼 持股異動」）。`#rankRows` delegated click：`.rank-flow` → `openFlow` 並 return，否則 `.rank-hit` → `openDetail`。「持股異動 ›」顯示條件改為 `_flowData.etfs[code]` 存在（決策 B）；`.tappable` 改名 `.has-flow`。`_changedWithin()`（flow.js）因此已無呼叫端，留給 CP8 死碼清理。代碼／名稱經 `_rankEsc` 轉義。
  - `js/render.js`：日曆列加 `data-code` 與 `.cal-hit`；`#calList` delegated click → `openDetail`（不在 ETFS 的代碼由 Detail 既有「這檔目前不在清單中」處理）。
  - CSS：`.rank-row`／`.cal-item` `position:relative`，覆蓋按鈕 `inset:0`，列內容 `pointer-events:none`；`.rank-flow` `min-height:44px` 以 `margin:-14px` 抵銷不撐高卡片（RK-1 仍 PASS）；focus-visible 外框。
  - 測試：rank_test 新增 NV-1～5 共 28 項（一般列 A0 與有 Flow 列 F0 真實點擊——以 elementFromPoint 命中後 click——→ Detail、只多一層、pushState 1 次、history.state 結構一致、Back 保留搜尋／定位／捲動；有 Flow 資料者皆有按鈕（含 7 天無換股者）、button ≥44px、aria-label、無巢狀；按鈕 → Flow、pushState 1 次、不開 Detail；三層返回；renderAll／renderRank 後仍有效；Tab 焦點 Enter／Space → Detail、Esc 關閉；日曆首末列 → Detail、pushState 1 次、Back 捲動保留、重繪後仍可點）。RK-4b 點擊驗證改為「整列 → Detail（一般列首末＋有 Flow 列）」＋「按鈕 → Flow」；TC-7 改真實點擊排行列與日曆列（刪除原「略過」分支）；RF-3 改點「持股異動 ›」（加 pushState 1 次、未開 Detail）。
  - Mutation：M1 移除排行列與日曆列 navigation → RK-4b 整列點擊 FAIL，之後 Back 離站使 rank_test 中斷（NV 未執行，等同 FAIL）。M2 「持股異動 ›」不 return、往下也 openDetail（模擬冒泡雙 navigation）→ 15 FAIL（RK-4b 按鈕兩項、NV-2／3／4 等）。
  - 結果（800×600）：rank 72、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝888 PASS／0 FAIL／5 DEFER。
  - **CP6c fix `2703a7a5`（排行小柱狀圖 hover 報酬提示消失）**：原因＝CP6c 讓 `.rank-main／.rank-sub` `pointer-events:none`，指標穿透到 `.rank-hit`，`format.js` miniBars 每根柱子的 `title` 無法 hover。修法：`.rank-sub .mini-bars { position:relative; z-index:1; pointer-events:auto }` 疊在 `.rank-hit` 上；`#rankRows` handler 將 `.mini-bars` 視同整列 → `openDetail`（`.rank-flow` 仍先判斷並 return）。修正前柱子中心命中 `rank-hit`（title 無）；修正後命中 `mb-bar`，title＝`-7.2%`／`+8.8%`／`+9.0%`（009816）。
    - rank_test 新增 NV-6 8 項（桌面 1280×800）：三根柱子 elementFromPoint 命中柱子且 title＝`ret_months` 末 3 筆格式化值；CDP mouseMoved 後 `:hover` 在該柱；CDP 真實點擊柱子 → Detail、pushState 1 次、不開 Flow；有 Flow 的列「持股異動 ›」與柱子互不遮擋、按鈕仍只開 Flow；列按鈕焦點＋Enter → Detail。既有 NV-1～5（一般區域 → Detail、按鈕 → Flow、Enter／Space、無巢狀）照跑全 PASS。
    - Mutation：移除該 CSS → NV-6 4 項 FAIL（命中 rank-hit、title 為空、:hover 落在 rank-hit、有 Flow 列柱子被蓋）。
    - 結果（800×600）：rank 80、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝896 PASS／0 FAIL／5 DEFER。

- **PO Change #3（Plan `2b98ba32`，§8.4）：Active Flow ETF 快速搜尋（CP6d）**。排程 CP6c → CP6d → CP7 → CP8 → Final。WHY：selector＝附近瀏覽、🔍＝已知要找哪檔直接跳；選取走既有 `flowSelect`，不新增 navigation。
- **CP6d — `455f5769`：Codex PASS、GPT Gate CLOSED。**
  - `index.html`：`.flow-head#flowHead` 右側 `#flowQBtn`（🔍，預設 disabled 直到 flow 資料 ok）；其後 `#flowQBox`（`#flowQ` 輸入框、`#flowQList` 結果），在 `#flowChips` 之外。
  - `js/flow.js`：`_flowQOpen`、`_flowQSync()`（`_flowStatus !== 'ok'` 時停用並收起；renderFlow 每次呼叫）、`_flowQItems()`（`Object.keys(_flowData.etfs)`，名稱 flow → ETFS）、`flowQSearch()`（`_matchEtf` 分數排序、同分依代碼、最多 8 筆、查無說明）、`flowQOpen／flowQClose(focusBtn)／flowQToggle／flowQPick(code)`（→ `flowSelect(code)` → 收起、焦點回 🔍）、`flowSearchReset()`（清 query、收起；`flowLayerHide` 呼叫）。結果 `#flowQList` delegated click；輸入框 Enter 選第一筆；`#flowHead`／`#flowQBox` keydown 在搜尋開啟時攔 Esc 並 `stopPropagation` → Router 的 document Esc 收不到。
  - `js/category.js`（範圍外但必要的兩處 hook）：分類原生離開持股異動（`refreshAll` 進清單、`applyFolder(null)` 時原本是 flow）→ `flowSearchReset()`，Flow 層持有節點時不清。
  - `css/pages.css`：`.flow-head` 改 flex；`.flow-q-btn`（44px、展開時中性藍框）、`.flow-q`、`.flow-q-item`（44px）、`.flow-q-empty`。
  - 測試：新增 `tests/browser/flowq_test.py` 35 項——FQ-1 四種入口（Tools／排行／Detail／分類原生）都有 🔍、預設收起、button 44px、aria、標題與 🔍 同列單行；360px 單行無溢出。FQ-2 展開取得焦點、window 不捲、收起焦點回 🔍。FQ-3 代碼完全相同第一、代碼開頭只出現 Flow ETF 且依代碼、名稱關鍵字、非 Flow ETF（0056）查無、`_matchEtf` 分數遞減。FQ-4 搜尋選取與點同一 chip 的 active／名稱／加碼減碼／treemap 格數／提示完全相同、chip 可見、收起。FQ-5 pushState 0、history.length 與 stack 不變；Tools 入口寫 `flow.ui.code`、分類原生寫 `folder.ui.code`。FQ-6 Tools／排行／Detail 入口 Back 回原處、Forward 顯示剛選 ETF。FQ-7 焦點在輸入框或結果時 Esc 只關搜尋、Flow 仍開；未開啟時 Esc 關 Flow。FQ-8 Enter 選第一筆；renderFlow＋高度縮小 resize 保留 query；Flow 關閉後重進、分類原生切走再回都為預設收起。FQ-9 390×844、844×390、1280×800、gs-ckm 無水平溢出。
  - Mutation：(1) 選取改 `openFlow(code)`（navigation）→ 3 FAIL（FQ-4、分類原生 FQ-5 push、FQ-8）；(2) 不攔 Esc → FQ-7 兩項 FAIL（Flow 被關）；(3) 搜尋範圍改用 ETFS → FQ-3 三項 FAIL（出現非 Flow ETF、0056 不再查無）。
  - 結果（800×600）：flowq 35、rank 80、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝931 PASS／0 FAIL／5 DEFER。390px 截圖目視：標題＋🔍 同列，展開後輸入框與結果在 selector 上方。

- **CP7｜V1 Dark／Light＋V2 visual tokens（§7.1、§7.2、§9 順序 7）— `033041ea`，Codex NEED FIX 3 項 → fix `028a31c2`；limited re-review：Issue ②③ CLOSED、Issue ① NEED FIX → fix `aab7b3ec`，待 Codex final limited re-review。**
  - V1：`index.html` `<head>` 在 CSS 前的行內 script：`localStorage.etfRadar.theme`（dark／light）優先，否則 `prefers-color-scheme`；未手動時 matchMedia `change` 跟著變，手動後不覆寫；讀寫失敗 try/catch（只在本次頁面生效）；`window.themeToggle()`、`themeApply()`；同步 `meta theme-color`（dark #0d1117／light #f6f8fa）。Header `.hdr-actions` 依序 YouTube（位置不動）→ `#themeBtn`（☀／🌙、44×44、aria-label「切換為淺色／深色模式」、aria-pressed）→ ↻。
  - V2：`css/base.css` `:root`＝dark，值與改版前實際色相同；新增語意 token（`--hot --warn --brand --link --silver --bronze --violet --mood-cta --src-official --err-text --err-soft --on-strong --fair-dim --hdr-bg --nav-bg --tm-border --shadow-pop/-menu/-lift/-band`）與 RGB 三元組（`--rgb-cheap/fair/up/dn/warn/hot/link/gold/violet/neutral/veil`，用法 `rgba(var(--rgb-x),α)`）；`:root[data-theme="light"]` 覆寫整組。CSS（base／components／pages／watch／category）與 JS（format miniBars、rank 標籤／SIG_COLOR／retClr／殖利率／配息方式、render 首頁 TOP 10、flow treemap）寫死色值全部改 token；剩下 pages.css 兩處 `#000` 為 mask 透明度，非顏色。archived-check.js（封存註解）未動。
  - 語意：兩主題 `--up` 紅、`--dn` 綠、0 中性、缺值灰；treemap `rgba(var(--rgb-up|dn), 0.30～0.85)`。light 下 treemap 格內文字隨 `--bright` 變深色。
  - dark 外觀刻意變更（依 Plan）：miniBars 從 #ff6b6b／#00e5a0 改 `--up`／`--dn`（Plan §7.2 明列）；排行狀態色（原 #4ade80／#fde047）、近一年報酬色、標籤色統一用全站 token；TH-6 對比調整 `--hot` #ef4444→#f25a5a（在 --card2 上原 4.3:1）、`--fair-dim` #8b7020→#a8913f（原 3.4～4.0:1）。
  - 測試：新增 `tests/browser/theme_test.py` 36 項——TH-1 系統 light／dark 初始、未手動時跟系統變、按鈕順序與 44px；TH-2 切換寫入、手動後系統不覆寫、重新整理維持、theme-color、切換不寫 history／Router；TH-3 Storage 全部丟例外時初始依系統、切換仍生效、無主題相關例外；TH-4（兩主題）miniBars、排行近一年報酬、我的 ETF 今日漲跌紅漲綠跌、0／缺值中性；TH-5（兩主題）treemap 只有紅系與綠系、加碼紅減碼綠、海外清單正紅負綠；TH-6（兩主題）28 組 token 對比全 ≥ 4.5（數值印在 log）、B6 警示條 ≥ 4.5；TH-7 文件夾陰影存在、B6 低調（字級 ≤ 主標、淡底 α<0.2）、無水平溢出。共用 header（detail_ui_test）加 `Emulation.setEmulatedMedia` 固定系統 dark（既有色值斷言以 dark 為基準）。依規格更新：watch D1（miniBars 改 --up／--dn）、tools FS-6（treemap 改讀 computed 色）。
  - Mutation：light 的 `--up` 改成綠 → theme_test 5 FAIL（TH-4 三項、TH-5 兩項）。
  - 結果（800×600）：theme 36、flowq 35、rank 80、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝967 PASS／0 FAIL／5 DEFER。390px light 截圖目視：首頁、排行、Active Flow、分類、我的 ETF 可讀，紅綠語意正確。
  - **CP7 fix `028a31c2`**
    - (1) rendered 對比：Codex 實測「過熱」dark 4.27／light 3.92、00981A treemap light 金額 3.76／張數 3.10（dark 更低）。修正：dark `--hot` #ff7070；light `--hot` #b31d28、`--warn`/`--brand` #9a3c00、`--cheap` #11643f、`--fair`/`--gold` #7a4f00、`--bond` #0858b9（三元組同步）。treemap 格色與面積透明度不變，`flow.js` 依「token 色×α 疊在 treemap 底」算出實際底色，字色取黑（#0d1117）或白對比較高者；移除 `.tm-amt`／`.tm-etf` opacity；中間調格（黑白皆 < 4.6）小字加淡底襯 `.tm-weak-l`（rgba(0,0,0,.28)）／`.tm-weak-d`（rgba(255,255,255,.4)）。紅漲綠跌、紅加碼綠減碼不變。
    - TH-6 改 rendered 掃描（SCAN_JS 內嵌於 theme_test）：每個有文字的可見元素，前景＝color×祖先 opacity，背景＝由 html 往下逐層混色；正文 ≥ 4.5、大字（≥24px 或 ≥18.66px 粗體）≥ 3；略過純符號。範圍：首頁、排行、工具、持股異動（00981A＋海外＋全部 32 檔 treemap 逐一切換）、分類總覽／清單／原生持股異動、我的 ETF、Detail 四分頁、Header、B6、導覽列，兩主題，全部 0 失敗。
    - (2) 主題鈕首次 paint：Header `.hdr-actions` 結束後緊接 `<script>themeApply(themeCurrent())</script>`（不在按鈕群內，TH-1 順序不變）。TH-8：`Network.setCacheDisabled`＋`Fetch.enable` 暫停 `js/state.js`，parser 停住（readyState=loading、ETFS 未定義）時驗 icon／aria-label／aria-pressed＝實際主題（light／dark 各一）。
    - (3) TH-5：逐格以 `_flowCells[i]` 回查原始 `flow` 的 amount 正負，>0 必須紅、<0 必須綠，聚合格須為紅或綠；另驗加碼／減碼金額色。
    - Mutation：M1a dark `--hot` 退回 #ef4444 → TH-6 dark FAIL；M1b treemap 不依底色設字色 → TH-6 dark＋light FAIL；M2 移除主題鈕即時同步 → TH-8 light FAIL（icon ☀、label「切換為淺色模式」）；M3 dark `--rgb-up`／`--rgb-dn` 互換 → TH-5 dark FAIL。
    - 結果（800×600）：theme 40、flowq 35、rank 80、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝971 PASS／0 FAIL／5 DEFER。
  - **CP7 Issue ① fix `aab7b3ec`（Flow 開著時直接切換主題，treemap 字色未重算；00981A Dark→Light 實測 2.38）**：原因＝字色與 `.tm-weak` 底襯是 renderFlow 當下依 token 算的 inline 值。`flow.js` 抽出 `_flowInkCtx(box)`（讀「當下」token 與 treemap 底色）、`_flowWeakCls()`；格子加 `data-side`／`data-a`；新增 `flowRecolor()` 就地重算每格 `color` 與底襯 class，**不重畫**。`index.html` 的 `themeApply()` 每次套用後 dispatch `etf:themechange`，flow.js 監聽後 `flowRecolor()`。面積→透明度、格子位置、ETF、選取、搜尋、捲動、Router 都不動。
    - theme_test 新增 TH-9 14 項：(a) dark 下開 Tools→Flow（00981A）、開搜尋 query「009」、selector 捲 120px、Flow 層捲 60px，直接按主題鈕 → light → dark：每次 treemap＋Flow 層 rendered 對比 0 失敗、格子仍紅／綠，且 ETF、query 與結果、active chip、selector／Flow 層／頁面捲動、格子位置與 data-a、computed 透明度、Router state、history.length 全部不變；(b) light 起點畫出 → 直接切 dark；(c) 分類原生持股異動 → light → dark。
    - Reverse validation：移除 `etf:themechange` 監聽 → TH-9 3 FAIL（dark→light 對比失敗，重現 2.38；light 起點→dark 失敗；分類原生→light 失敗）。
    - 結果（800×600）：theme 50、flowq 35、rank 80、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝981 PASS／0 FAIL／5 DEFER。

- **CP7 Visual Gate（GPT Gate／PO）**：Codex 技術 PASS 後，PO Visual Gate 判 NEED FIX（palette 不符核准方向；Light「像在聚光燈下、灰灰的、紅綠快分不清」）。PO 指定核准 palette 為 Visual Source of Truth（參考圖本輪 Claude 端未收到圖檔，依文字列出的核准色施工）。
  - **施工 `d09ac578`**（只改 token 與互動狀態色；DOM、流程、Router 不動）：
    - Light：`--bg #F7F9FC`、`--card #FFFFFF`、`--card2 #EEF2F8`（柔和藍灰）、`--border #DDE3EC`、`--bright #1F2937`、`--dim #64748B`、`--link/--brand/--mood-cta #2563EB`、`--up #DC2626`、`--rgb-dn 5,150,105`（#059669 填色）、`--rgb-fair/--rgb-gold 217,119,6`（#D97706）、`--violet/--tech #7C3AED`、`--active #B45309`（字）／`--rgb-active 245,158,11`。
    - Dark：`--bg #0F141B`、`--card #171E27`、`--card2 #202936`、`--border #2C3747`、`--bright #E8EDF3`、`--dim #98A4B3`、`--link/--brand/--bond #4C8DFF`、`--up/--dear #F06A6A`、`--dn/--cheap #4FC59A`、`--fair/--gold #D6A84B`、`--warn/--active #F59E0B`、`--violet #A78BFA`（字）／`--rgb-violet/--rgb-tech 139,92,246`（#8B5CF6）。新增 `--tech`、`--active`、`--rgb-tech`、`--rgb-active`。
    - 品牌藍＝操作／選取／焦點：`.nav-btn.active`、`.cat-seg button.on`、`.dt-tab.on` 底線、`.gsearch-bar input:focus`、`.num-input:focus`、`.rank-ic.on`、`.rank-find input:focus`、`.rank-hit／.rank-flow／.cal-hit:focus-visible`（原本綠或金）。
    - **元件層最小處理（核准色在該元件 rendered 對比 < 4.5，未改整體 palette）**：① light 文字型語意色用同色相加深版當字色、填色仍為核准色：`--cheap/--dn #065F46`（便宜、跌字；填色 #059669）、`--fair/--gold #A14A07`（合理、提醒字；填色 #D97706）、`--warn #9A3412`（偏貴）、`--hot/--dear #B91C1C`、`--bond #1D4ED8`、`--silver #536176`；② light 次要 surface 元件（cat-band、cat-strip、cat-more、cat-expand、mood-card、hot-item、home-row、home-empty、empty-state、flow-note、np-mkt、gs-more、wt-go、calc-out、num-input、router-proc）內 `--dim` 加深為 #536176（#64748B 在 #EEF2F8 上僅 4.24）；③ light `.rank-hdr` 紫色淡底 13%→8%（紫字 4.47→5.07）；④ dark `--hot #FB8A8A`（過熱標籤 12% 淡底上 #F87171 僅 4.47）。
    - 測試：既有色值常數依新 dark palette 更新（watch UP／DN／DIM＝rgb(240,106,106)／rgb(79,197,154)／rgb(152,164,179)、FL-2、tools FS-6），theme TH-1 light 底色 rgb(247,249,252)、TH-2 theme-color #F7F9FC。TH-6 rendered 掃描（兩主題、全部 32 檔 treemap）與 TH-9（Flow 開著時雙向直接切換主題的動態重算）皆 PASS。
    - 結果（800×600）：theme 50、flowq 35、rank 80、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝981 PASS／0 FAIL／5 DEFER。
  - 測試網址：手機（同 Wi-Fi）http://192.168.68.52:8090/index.html；本機 http://127.0.0.1:8090/index.html（8081 被其他程式佔用）。
  - 下一步：GPT Gate／PO 再次 Visual Gate；Visual PASS 後由 Codex 做本輪 visual-token 變更的技術 regression review。CP7 尚未 CLOSED、CP8 未開始。

- **CP7 Visual Gate NEED FIX（PO 狀態色規則）— `dc5ea5bb`**：PO 不接受 CP7 對五個估值／狀態色的改動（dark「過熱」#FB8A8A 偏粉紅）。依 Git history（CP7 改版前 commit `components.css` 的 `.sig-*` 與 `base.css` token）恢復原始色：過熱 #ef4444、偏貴 #fb923c、合理 #F0B840（`--fair`）、便宜 #00e5a0（`--cheap`）、債券 #58a6ff（`--bond`）。註：改版前排行頁 `rank.js` 的狀態字曾另用 #4ade80（便宜）／#fde047（合理）兩個淺色變體，本輪依「一組五色」以 `.sig-*` 標籤色為準統一。
  - 新增 `--sig-hot/--sig-dear/--sig-fair/--sig-cheap/--sig-bond`（只定義在 `:root`，light 不覆寫＝兩主題完全相同）與 `--sig-backing #0B0F14`。dark＝PO Hard Constraint；light 同色為 PO Visual Test，尚未正式鎖定。
  - 對比處理（不改五色）：`.sig-*` 背景由 12% 淡底改為 `--sig-backing` 深色底襯（文字與框線維持原色）；排行 `.rank-sig` 狀態字加同一底襯（`border-radius:6px; padding:0 6px`）。原色在底襯上：過熱 5.11、偏貴 8.49、合理 10.65、便宜 11.64、債券 7.61。原色直接放在 light 卡片上僅 1.7～3.8，故需要底襯。
  - theme_test 新增 TH-10 6 項（兩主題 `.sig-*` 文字／框線＝原始五色、對比 ≥ 4.5、排行狀態字同色）；反向：底襯改 transparent → TH-6 兩主題 FAIL。完整 regression：theme 56、flowq 35、rank 80、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、category 270＋1 DEFER、watch 149＋4 DEFER＝987 PASS／0 FAIL／5 DEFER。
  - 測試網址：手機 http://192.168.68.52:8090/index.html；本機 http://127.0.0.1:8090/index.html。下一步：GPT Gate／PO 再次 Visual Gate（CP7 未 CLOSED、未交 Codex、CP8 未開始）。

- **CP7 Visual Gate（Homepage polish＋Light status badge）— `d4ecc656`**：PO 確認五色與 dark 標籤 PASS。本輪：
  - (C) light 狀態標籤（`.sig-*`、`.rank-sig`）只把底色改 transparent，文字／框線維持 PO-Locked 五色、不降 opacity；dark 維持 `--sig-backing`。
  - (F) Header YouTube `.hdr-btn.hdr-yt { color:#FF0000 }`，兩主題品牌紅；CP5 行為（位置、44px、URL、新分頁、noopener noreferrer）不變，regression YT-1／YT-2 PASS。
  - (E) 首頁入口卡**未施工**：本輪訊息沒有附上 4 張參考圖（Claude 端只收到文字），依指示不猜配色。
  - (D) **light 透明底狀態標籤對比不足（依 PO 指示不改色、不加回底襯，待 GPT Gate／PO 決定）**。實測 390×844：首頁 home-row（#EEF2F8）合理 #F0B840 1.61；首頁 hot-item（#EEF2F8）偏貴 2.01、過熱 3.35；排行 rank-row（#FFFFFF）便宜 #00e5a0 1.65、合理 1.80、偏貴 2.26、債券 #58a6ff 2.53、過熱 3.76；Detail gs-panel（#F7F9FC）偏貴 2.15、過熱 3.57；我的 ETF wc（#FFFFFF）偏貴 2.26、過熱 3.76。理論值：五色對 #FFFFFF／#F7F9FC／#EEF2F8 → 過熱 3.76／3.57／3.35、偏貴 2.26／2.15／2.01、合理 1.80／1.71／1.61、便宜 1.65／1.57／1.47、債券 2.53／2.40／2.25，均低於 4.5（過熱在 #FFFFFF 也未達大字 3 以外的正文門檻）。
  - 測試：theme 58 中 57 PASS／1 FAIL（TH-6 [light]，失敗元素僅 `.rank-sig`、`.sig-fair`、`.sig-dear`、`.sig-hot` 等狀態標籤）；TH-10 新增 light 透明底與兩主題 YouTube 紅；其他 regression 照舊 PASS。
  - 測試網址：手機 http://192.168.68.52:8090/index.html；本機 http://127.0.0.1:8090/index.html。等待 GPT Gate／PO Visual Gate 與 D 節決定、入口卡參考圖。

- **【交接快照｜2026-10-07，context 打包，停止施工】**
  - 最新實作 commit：`4e6bd112`「style(phase5-CP7): light 狀態標籤底色改透明、Header YouTube 兩主題品牌紅（Visual Gate）」——即先前回報的 `d4ecc656`（本機自動排程推送市場資料時 `pull --rebase` 改寫了 SHA，內容相同；之後的 commit 只有 `data/market.json` 與本交接本）。
  - 狀態：Phase 5 CP1～CP6d CLOSED；**CP7 Engineering／Code Review PASS（Codex final limited re-review PASS）**；**CP7 Visual Gate 尚未 CLOSED**；**CP8 尚未開始**；**全部未 push**。
  - Global Status 五色（PO-Locked，兩主題相同，token `--sig-*`）：過熱 #ef4444、偏貴 #fb923c、合理 #F0B840、便宜 #00e5a0、債券 #58a6ff；一組五色全站一致（排行頁不用舊 #4ade80／#fde047）。
  - Dark 狀態標籤：維持 `--sig-backing #0B0F14` 底襯（PO Visual PASS）。Light 狀態標籤（`.sig-*`、`.rank-sig`）：background transparent，文字／框線維持五色、不降 opacity。
  - **Known Blocker（待 GPT Gate／PO 決定）**：Light 透明底狀態標籤對比 < 4.5，theme_test TH-6 [light] FAIL（其餘全部 PASS）。量測：首頁 home-row #EEF2F8 合理 1.61；首頁 hot-item #EEF2F8 偏貴 2.01、過熱 3.35；排行 rank-row #FFFFFF 便宜 1.65、合理 1.80、偏貴 2.26、債券 2.53、過熱 3.76；Detail #F7F9FC 偏貴 2.15、過熱 3.57；我的 ETF #FFFFFF 偏貴 2.26、過熱 3.76。PO 指示：不改五色、不加回底襯、不做 light 變體、不降 opacity。
  - Header YouTube：Light／Dark 固定品牌紅 #FF0000（`.hdr-btn.hdr-yt`），CP5 行為不變。
  - Homepage Entry Cards（「我想看看 ETF」藍／「我已經有 ETF」綠）：**尚未施工**——兩次指令都未實際收到 4 張參考圖，依指示未猜配色。
  - 其他 CP7 已完成內容見本段上方各 CP7 條目（V1／V2、rendered contrast、主題鈕首次 paint、TH-5、Flow 開著切主題 recolor、核准 palette）。`_changedWithin()` 仍留 CP8 cleanup。
  - 測試環境備註：瀏覽器測試以 scratchpad `run_tests.py`（http 8766、Chrome 9224、`WS=800,600`）執行；Visual Gate 測試站為 `python -m http.server 8090 --bind 0.0.0.0`（8081 被其他程式佔用）：本機 http://127.0.0.1:8090/index.html、手機 http://192.168.68.52:8090/index.html。

- **CP7 Visual Gate（Homepage Visual Polish）— `8f57809a`**（基準 `4e6bd112` 之上；本機，未手動 push，自動行情排程推送時 SHA 可能被改寫，訊息開頭「style(phase5-CP7): Visual Gate homepage polish」）：
  - (1) Status Badge Light＋Dark 全部透明底：`--sig-backing: transparent`（移除 light 專用覆寫）；text／border＝PO-Locked 五色，opacity 1。
  - (2) Light page 底 `--bg #FEF8E2`（PO 奶油 reference 取樣 #FEF8E2）、`--hdr-bg` 同色系、meta theme-color 同步；card 維持白。Dark page 底不動。連帶：light `--dim` #64748B 在奶油底只有 4.47 → 微調 #617187（4.68；白 card 4.98），避免新增非 Status 的 TH-6 FAIL。
  - (3) 首頁入口卡（`.he-explore`／`.he-owned`，只限這兩張）：依 PO 四張 reference 取樣——dark 藍 #0B1B2E／accent #3B82F6、dark 綠 #0A2724／#34C79A、light 藍 #E6F2FF／#2563EB、light 綠 #E2F7F0／#079A72；新增放大鏡／錢包 icon、左側 4px accent（inset shadow，不佔寬）、arrow 同 accent。尺寸、文案、onclick、Router 不變（卡高 79px 與前相同）。
  - (4) 加權漲跌幅：`pct>0` 紅（--up）、`<0` 綠（--dn）、`=0` neutral（--bright，無箭頭）；label「加權」維持次要字，數值 `.mi-val` 600、15px（同 TOP10 殖利率字級）。原 ±0.3% 才上色的門檻取消。
  - (5) Header YouTube：紅 Play Mark（#FF0000 SVG）＋「YouTube」wordmark（dark #FFFFFF／light #0F0F0F），透明底無框；≤380px 縮字。實測 360：YT 153–240、主題 248–292、↻ 300–344，scrollWidth 360、LIVE 徽章單行；390：162–270／278–322／330–374，scrollWidth 390；高 44。YT-1／YT-2 PASS。
  - 測試：theme 58 中 56 PASS／2 FAIL（TH-6 dark、TH-6 light，**失敗元素全部為 `.sig-*`／`.rank-sig`，無其他元素**）；TH-1／TH-2／TH-10 依 PO 新規格更新期望值（奶油底、theme-color、兩主題透明底、YouTube Logo）。regression 35、home 38、router 64、rank 80、tools 93、flowq 35、search_compact 38、detail_ui 48、detail_history_fix 14、detail_collapse 25、detail_state 42 全 PASS；category 270 PASS／1 DEFER（LR-8 既有）；watch 148 PASS／1 FAIL／4 DEFER——CD-1「卡片不含 52」在基準 `4e6bd112`（stash 後）同樣 FAIL，屬既有資料相依，非本輪 regression。
  - **Known Blocker（TH-6，待 GPT Gate／PO）**：rendered 實測——Dark：首頁 hot-item（--card2 #202936）過熱 3.90；排行 rank-row／我的 ETF（--card #171E27）過熱 4.46；其他四色在 dark 皆 ≥ 4.5。Light：首頁 hot-item（#EEF2F8）便宜 1.47、合理 1.61、偏貴 2.01、過熱 3.35；排行（#FFFFFF）便宜 1.65、合理 1.80、偏貴 2.26、債券 2.53、過熱 3.76；Detail（奶油 #FEF8E2）過熱 3.54；我的 ETF（#FFFFFF）過熱 3.76。依指示不改五色、不加底襯、不降標準。
  - 狀態：CP7 Visual Gate 未 CLOSED、未交 Codex、CP8 未開始、未手動 push。測試網址：本機 http://127.0.0.1:8090/index.html；手機 http://192.168.68.52:8090/index.html。

- **CP7 Visual Gate（Typography Alignment）— `9defbd6c`**（本機，未手動 push）：
  - (1) 首頁「價格合理區」「今日成交量 TOP 10」標題 16 → 19px（`#pzTitle, #tvTitle`），位置／間距／row 不變。
  - (2) 全站 ETF 代碼／名稱：Source of Truth＝首頁條列 `.wait-code`／`.wait-name`。`base.css` token `--etf-code-*`／`--etf-name-*`＋共用規則：代碼 Microsoft JhengHei 16px 700 `--bright`；名稱 16px 400 `--link`（兩主題同邏輯，色走主題 token）。套用：Detail 標題（`.gs-panel-hd .t b`／新增 `.etf-name`）、分類清單 `.cr-code`／`.cr-name`（原 mono 14px／名稱 --dim）、100 排行 `.rank-code`／`.rank-name`（原 mono 20px／18px）。各頁原本的字型／字級／顏色宣告已移除，只留 layout 屬性。
  - 實測 360／390 × Light／Dark：首頁、分類、排行、Detail 的 code／name computed style 完全一致；代碼無截斷；首頁、分類、Detail 無水平 overflow。
  - 測試：home 38、detail_ui 48、detail_state 42、detail_history_fix 14、detail_collapse 25、router 64、regression 35、watch 149（4 DEFER）、search_compact 38、tools 93、flowq 35 全 PASS；category 270 PASS／1 DEFER（LR-8）；theme 56／2 FAIL（僅 TH-6 Status Known Blocker）；rank 79／1 FAIL——RK-1「捲動後 sticky 黏在 Header 下方」在前一個 commit（stash 後）同樣 FAIL（`--hdr-h` 138 vs Header 實際 122，盤後狀態相依；11:2x 盤中時 PASS），非本輪 regression。
  - **Observation（既有，本輪 scope lock 未修）**：360px 排行頁「持股異動 ›」（`.rank-flow`）右緣到 388px，頁面水平 overflow 28px；前一個 commit 同樣存在。另 RK-1 `--hdr-h` 未隨 Header 高度變化重新同步（見上）。兩項待 Gate 決定是否另開修正。

- **CP7 Visual Gate（Visual Polish Round，10 項）— `1e010a44`**（本機，未 push）：
  - 新增 token（base.css）：`--vivid-up/--vivid-dn`（字：dark #F25555／#22C55E，light #DC2626／#15803D）、`--vivid-*-fill`（dark #EF4444／#22C55E，light #EF4444／#16A34A）、`--rgb-vivid-*`、`--num-accent`（dark #FACC15 鮮黃／light #D97706 橘）、`--badge-gold`（dark #F0B840／light #D97706）。既有 `--up/--dn` 未動（自選、加權等不在本輪範圍）。
  - (1) Light 便宜：light 覆寫 `--sig-cheap #059669`（文字＋框、透明底）；dark 仍 #00e5a0。
  - (2) 數字字型：`--mono` → Microsoft JhengHei（token 名沿用；所有 font-size 未改）。副作用：自選卡數字行高變大 +4px → `.wc-px/.wc-chg line-height:1.17` 鎖回原高（否則 DR-17／DR-18／BD-5 觸控座標落到底部導覽列）。
  - (3) 首頁 TOP10 **LIGHT ONLY**（全部 `:root[data-theme="light"]` 選擇器）：1 金底 #D97706＋白、2 銀底 #E2E8F0＋藍 --link、3 銅底 --bronze #9A5B2E＋白；現價（字＋數字）#D97706；「年殖利率」字 --dim；「新上市」包 `.hr-new` 紫 --violet #7C3AED（無框無底）。Dark 截圖確認未變。
  - (4) Detail 中文：dt-lbl 15→16、dt-tab 15→16、dt-sec 15→16、dt-note／dt-sub 13→14、dt-tag／dt-foot 12→13；`.dt-val` 數值維持 15。中文字型本來就是 --sans（與首頁同）。
  - (5) 排行漲跌柱：`.rank-sub .mb[data-k]` 改 `--vivid-*-fill`（只限排行；長度／排序不變）。
  - (6) 「持股異動 ›」→「持股異動」；light 字 #D97706、dark 不變；觸控 44px／openFlow 不變。≤380px 第二行欄寬收窄（freq 56／num 70／yld 68 nowrap／flow 內距 1px）→ 360／390／1280 × 兩主題：首頁、排行、Flow、分類、Detail 水平 overflow 全為 0（原 360 排行 overflow 28px 已解）。
  - (7) 排行配息頻率、殖利率數字 → `--num-accent`（含未核實「~」值，原 --fair-dim 氧化色移除）；「未滿1歲」--dim；報酬率 retClr → `--vivid-up/--vivid-dn`。
  - (8) 排行 `合理✓` → `合理`（label 只改顯示）；light 便宜與首頁同 token。
  - (9) 「快配息囉」：透明底＋`--badge-gold` 文字與 1px 框；配息金額 `--num-accent`。
  - (10) Active Flow：treemap 填色與 `_flowInkCtx` 改讀 `--rgb-vivid-*`（透明度＝面積語意不變、不重建 DOM、flowRecolor／etf:themechange 保留）；flow-tot 與海外清單加減碼字 → `--vivid-*`；弱格底襯保留（對比保護），改 border-radius 8px＋同色 box-shadow 羽化，去除「小貼紙」硬邊。
  - 測試（800×600）：flowq 35、rank 80、tools 93、home 38、router 64、search_compact 38、detail_ui 48、detail_history_fix 14、regression 35、detail_collapse 25、detail_state 42、watch 149（4 DEFER）全 PASS；category 270／1 DEFER（LR-8）；theme 54／4 FAIL：TH-6 dark、TH-6 light（見下）、TH-5 dark／light——TH-5 為「今日 00981A 只有 3 格 < 需 ≥ 4 格」資料相依，stash 回前一版同樣 FAIL，顏色核對 bad=[]，非 regression。TH-9（Flow 開著雙向切主題）PASS。期望值依 PO 新色更新：tools FS-6、watch FL-2／FL-3（新增 FUP／FDN 常數，CL／BR 其他 --up/--dn 斷言不動）、theme TH-10（light 便宜 #059669）。
  - **TH-6 Known Blocker 重新量測**：
    - Dark（只剩過熱 #ef4444）：首頁 hot-item 3.90、排行／我的 ETF 4.46。其他無失敗。
    - Light 狀態標籤：首頁 便宜 3.35／合理 1.61／偏貴 2.01／過熱 3.35；排行 便宜 3.77／合理 1.80／偏貴 2.26／債券 2.53／過熱 3.76；Detail 過熱 3.54；我的 ETF 偏貴 2.26／過熱 3.76。
    - **本輪新增（PO 指定色本身 < 4.5，依指示不換色）**：light #D97706 —— 排行持股異動／配息頻率／殖利率數字 3.19（白卡）、首頁 TOP10 現價 2.84（#EEF2F8）、TOP10 第 1 名白字 on #D97706 3.19；第 2 名藍字 on 銀 #E2E8F0 4.19。
  - **無法從 repo 精準還原的 PO reference（本輪訊息未附 A／B／C 參考圖）**：Light 便宜綠（用核准 palette #059669）、方案 B 金／銀／銅底（用 #D97706／#E2E8F0／#9A5B2E）、方案 C 琥珀橘（用 PO 第 6 項指定的 #D97706）、方案 C 灰（用 --dim）、方案 A 紫（用 --violet #7C3AED）、方案 C 金黃 badge（用 dark #F0B840／light #D97706）、dark 鮮黃 #FACC15、鮮明紅綠全組。皆待 PO 實機確認或提供 HEX。

- **CP7 Visual Gate（PO 方案 A／B／C 參考圖補到）— `e1511f87`**：TOP10 與「快配息囉」改用參考圖像素取樣色，取代上一輪近似值。
  - TOP10（LIGHT ONLY）：1 金 #D49A06＋白（2.49）、2 銀 #CAD8EC＋藍 #0A42A4、3 銅 #D07540＋白（3.33）——方案 B（參考圖為漸層，取中段實色）；現價 #F05B02（方案 C 琥珀橘，on #EEF2F8 3.01）；「年殖利率」#54657F（方案 C 灰）；「新上市」字 #8B55EE（方案 A 紫，取 badge 色當文字色，4.04）。
  - 「快配息囉」：方案 C 金黃 badge，底＋框 #FCDF7A、字 #542B0A，兩主題相同（`--badge-gold` token 移除）。
  - 仍未由參考圖覆蓋（沿用上一輪）：Light 便宜 #059669、排行持股異動／配息頻率／殖利率／配息金額 light #D97706（PO 第 6 項指定）、dark 鮮黃 #FACC15、鮮明紅綠組。
  - 測試：theme 54／4（TH-6 兩主題＋TH-5 資料相依，同上一輪）、home 38、rank 80、tools 93、regression 35 PASS。

- **CP7 Visual Gate 實機複測補充（treemap 氧化／排行前三名）— `c2319bea`**（本機，未 push）：
  - A｜Active Flow treemap：原「rgba(token, 0.30～0.85) 疊在卡片底」在低透明度時混入灰／黑底 → 磚紅、灰綠。改 `_flowFill(side, a)`：同一色相、高飽和，只用明度分層——light 紅 H0 S84% L62→44%（#EF4D4D→#CE1212）、綠 H142 S72% L50→30%（#24DB67→#15843E）；dark 紅 H0 S74% L34→52%（#971717→#DF2A2A）、綠 H142 S70% L24→40%（#126832→#1FAD53）。`data-a`（面積層級 0.30～0.85）語意、geometry 不變；`_flowInkCtx` 改依實際填色算黑／白字；`flowRecolor()` 換主題時同時重算底色與字色（不重建 DOM）；弱格羽化底襯保留。實測 00981A（3 格）與 00993A（28 格）兩主題截圖：紅綠乾淨、無溢出；TH-6 全部 32 檔 treemap 文字對比兩主題皆 PASS；TH-9 雙向切換 PASS。
  - B｜排行 TOP100 名次 1～3：`.rank-no.gold/.silver/.bronze` 28px 底牌（margin 0 4px，欄寬仍 36），共用新 token `--rank1/2/3-bg/fg`（#D49A06＋白、#CAD8EC＋#0A42A4、#D07540＋白，兩主題相同）；首頁 TOP10 light 改讀同一組 token。4～100 不變。360／390／1280 × 兩主題水平 overflow 0。
  - 測試：flowq 35、rank 80、tools 93、home 38、router 64、search_compact 38、detail 四支、regression 35、watch 149、category 270／1 DEFER 全 PASS；theme 54／4：TH-6 兩主題（Known Blocker；本輪新增排行第 1／3 名白字 on 金 2.49、on 銅 3.33，兩主題）、TH-5 資料相依（同前）。期望值調整：tools FS-6、watch FL-2 改為色相家族判斷（底色已非固定 rgba）；TH-9 層級比對改讀 data-a（行為斷言不變）。

- **CP7 Visual Gate：treemap 文字 halo 移除 — `c5d4cfd8`**（本機，未 push）：
  - 來源：`css/pages.css` `.tm-weak-l/.tm-weak-d .tm-amt/.tm-etf` 的 `box-shadow:0 0 6px 3px rgba(...)`（`1e010a44` 為去「貼紙感」加的羽化），由 `_flowWeakCls` 在黑白字皆 < 4.6 的中間調格加上。
  - 處理：`_flowFill` 新增對比保護——若該格黑白字都 < 4.6，同色相、同飽和度往暗調明度（每步 1%）直到白字 ≥ 4.6；`_flowInkCtx` 用同一個填色選黑／白字。結果弱格數為 0：全部 32 檔、158 格，dark → light → dark 逐檔掃描 weak=0。box-shadow 移除；`.tm-weak` 底襯 CSS 保留為保險（無陰影、無羽化、圓角 4px）。
  - Contrast：TH-6 兩主題「全部 32 檔 treemap」無任何失敗元素；TH-9 雙向切換 PASS。TH-6 失敗仍只在狀態標籤／排行與首頁 PO 指定色（同上一輪清單）。
  - 測試：theme 54／4（TH-6×2 Known Blocker、TH-5×2 資料相依），其餘 13 支全 PASS（category 1 DEFER、watch 4 DEFER）。

- **【CP7 CLOSED｜2026-10-09】Engineering PASS（Codex final limited re-review）＋ PO 手機實機 Visual Gate PASS（Light／Dark）。** 最終實作 commit：`c5d4cfd8`（treemap halo 移除；行情排程推送時 SHA 可能被改寫，以 commit 訊息為準）。
  - 保留的已知測試狀態（未為 CLOSED 改色或弱化測試）：
    - theme_test TH-6 [dark]／[light] FAIL——Known Blocker，PO 接受為設計取捨：狀態標籤透明底五色（dark 過熱 3.90／4.46；light 便宜 3.35～3.77、合理 1.61～1.80、偏貴 2.01～2.26、債券 2.53、過熱 3.35～3.76）、PO 指定色（light #D97706 持股異動／配息頻率／殖利率 3.19；TOP10 現價 #F05B02 3.01；新上市 #8B55EE 4.04；第 1 名白字 on 金 #D49A06 2.49、第 3 名 on 銅 #D07540 3.33，排行兩主題同）。treemap 全部 32 檔兩主題 PASS。
    - theme_test TH-5 [dark]／[light] FAIL——資料相依：測試要求 00981A treemap ≥ 4 格，今日只有 3 格；顏色核對 bad=[]，前版同樣 FAIL。
    - category LR-8 DEFER（真機已補驗）、watch 4 DEFER（真機條件）——既有。
    - rank RK-1「捲動後 sticky 黏在 Header 下方」曾在盤後時段 FAIL（`--hdr-h` 未隨 Header 高度重新同步），盤中 PASS；列為 Observation 交 CP8 評估。
  - 下一步：CP8 尚未開始；先處理獨立 Data Pipeline Incident（00996A）。未 push。

- **【獨立 Data Pipeline Incident｜00996A 持股抓取失敗｜記錄，先不修】**（2026-10-07，PO 實機 Telegram 監控）
  - 現象：00996A 持續抓取失敗，資料停在 **2026-09-24**；15:10 該輪「未抓到清單」明確包含 00996A，15:28 仍未恢復。
  - 處理順序：**不併入 CP7**，CP7 Visual Gate 期間不改 pipeline／PCF adapter／data schema。Visual Gate 完成後另開單獨追查，依序判定 Download → Parse → Compare → Write 哪一段失敗，再提修正方案交 Gate。

- **【00996A Incident Phase 2A｜2026-10-08】結果：CASE 2 — `MEGA_REMOTE_SOURCE_BLOCKED`（Incident 未 CLOSED）**
  - Phase 1 診斷：FIRST DIVERGENCE＝Download（Actions 上 trade_pcf HTTP 403，CDN「Access Denied … Reference #18」）；次因＝fetch_mega 例外時 `continue`，商品頁備援從未執行。
  - 修正（program commit `cd9faa4c`，本機 main，未 push）：PCF 例外或解析不到 → 皆走既有 `_mega_product()`；兩者都失敗才回空 → 既有 KEEP＋監控。PCF 解析原樣搬入 `_mega_parse_pcf`；日期／驗證／Compare／Write／其他 adapter／specific=True 行為未改。
  - 本機 regression（模擬 403）：R1 PCF 正常 → 用 PCF（2026-10-08，53 檔）；R2 PCF 403 → 商品頁（2026-10-08，53 檔）；R3 兩者 403 → 回空（交 KEEP）；R4 specific=True＋PCF 403 → 不走商品頁、回空。
  - **Actions probe**（分支 `probe/mega-996a`，workflow `mega-probe.yml` 只在該分支 push 觸發、不 commit／不 push／不發 TG；run 37763570699、job 113265623286）：
    - PCF：HTTP 403 Forbidden（Access Denied）。
    - 修正後確實進入備援：`[兆豐] 商品頁失敗: HTTPError: HTTP Error 403: Forbidden`。
    - 結果：`[KEEP] 00996A …沿用上次資料（資料日 2026-09-24）`；reload from disk：data_date 2026-09-24、fetched False、52 檔。
    - 同一輪其他投信全部正常更新（多數 2026-10-08），不受影響。
  - 本機同時：PCF 200、商品頁 200，皆 2026-10-08、53 檔。
  - 依指示停止：未改 header／cookie／UA／retry／代理，未建本機排程。**下一步：PO／GPT 決定正式架構（官方替代來源 或 受控 local／self-hosted fetch）。** CP8 仍暫停。

## 1. 協作協定（團隊約定，原文保留）

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

## 2. 歷史紀錄（全部 RESOLVED，僅供追溯；不是待辦）

> 以下所有 blocker、Findings、「待 Codex 複查」「Ready for Codex re-review」等字樣均已過時，已解決（RESOLVED）。它們不代表目前的待辦。目前狀態只以第 0 節為準。

## 目前 Checkpoint（RESOLVED／歷史）

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

## 本輪 Blocker：延遲搜尋未在離開 Detail 時取消（RESOLVED／歷史）

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

## Round 1 修正（`bb9d59e6`）（RESOLVED／歷史）

- **Finding 1（Blocker）**：pending restore 可能在使用者已離開 Detail entry 後被延遲 callback 還原。
  - `_tryRestoreDetail()` 先清除 `_restoreCode`，且只在 `history.state` 仍是同代碼的 `etfDetail` entry 時還原。
  - popstate 開頭一律取消 pending restore。
  - 註：在 Chrome 中，reload 後的 Back 會跨文件返回，本次未能以該路徑重現 Codex 所述的錯配。修正是依 Rev.3 的 history 不變條件補上的防禦性守衛。若 Codex 有可重現步驟，請附在 Review 結果中。
- **Finding 2（Risk）**：Back 關閉 Detail 時同步隱藏 `#gsearchList`（Rev.3 §6.6）。Phase 1 其他搜尋行為未改。
- 瀏覽器回歸測試收入 `tests/browser/`，並補上上述兩項的測試。

## 測試結果（RESOLVED／歷史）

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

## Codex Findings / Review Status（RESOLVED／歷史）

| 編號 | 等級 | 狀態 |
|---|---|---|
| F1 pending restore 在基底 entry 被還原 | Blocker | 已修正，待 Codex 複查 |
| F2 Back 關閉 Detail 時下拉未收起 | Risk | 已修正，待 Codex 複查 |
| 延遲搜尋：✕／Back／點搜尋列外側未取消（Codex 上一輪 NEED FIX） | Blocker | 已解決（`1958cdc0`），Codex 已確認 |
| 收合測試 C7、C9 前置條件未成立（未固定視窗、spacer 算式錯誤） | QA | 已修正測試條件（`82dc1dde`），待 Codex 複審 |

**Ready for Codex re-review**（範圍 `369f3616..82dc1dde`）。

## 真機環境更正（怡恩 2026-10-04）（RESOLVED／歷史）

- 今天實際真機測試的環境是 **iPhone + iOS + Google Chrome**，不是 Samsung／Android。
- 文件中原本標為 Android、Samsung 的真機紀錄是誤歸類，已改寫為 iPhone + Chrome 的紀錄。若某一輪實際不是這台手機，請怡恩指出，再更正。
- 今天量到的 `innerHeight` 20 → 276，以及「0050 → 按鍵盤搜尋 → 鍵盤收起 → Detail 開啟 PASS」，都是 iPhone + Chrome 真機結果。
- 先前依 Samsung 瀏覽器推論的「標題列與工具列佔掉大部分高度」，尚未在 iPhone 上驗證，視為待確認，不是已證實的原因。
- 今後 QA 矩陣：
  1. **iPhone + Chrome**：主要驗收環境。
  2. **iPhone + Safari**：相容性抽測，只測首頁、搜尋與鍵盤、直橫向、Detail、返回。
  3. **Samsung + Chrome**：相容性抽測，同樣只測關鍵流程。
- QA 紀錄不得從截圖或上下文推測裝置、OS 或瀏覽器。只有怡恩明確確認的環境，才能標記為真機 PASS。

## 真機驗收（第一輪，測試版本 bb9d59e6）（RESOLVED／歷史）

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

## 真機驗收第二輪（修正 commit `0c679655`）（RESOLVED／歷史）

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

## Codex 複審結果（收合修正）與 Claude 修正（commit `9ece2c6d`）（RESOLVED／歷史）

| 項目 | 狀態 |
|---|---|
| Blocker：收合後 scrollTop 被壓回 0，立即展開造成閃動 | 已修正。收合前檢查收合後仍在範圍內；展開只看真的回到頂部 |
| Blocker 測試缺口（略溢出、切短分頁） | 已補 C7–C10，並以舊版邏輯重現（舊版：未收合、scrollTop=0） |
| Risk：鍵盤與橫向需真機回測 | 仍待怡恩回測第 1、6 項 |

**驗證**：桌面瀏覽器測試共 91 項全數通過（收合 21、互動 42、history 14、迴歸 14）。

**Ready for Codex re-review**（範圍 `6bf51c54..9ece2c6d`）。

## iPhone + Google Chrome 真機回測（怡恩，測試版本 `b5af04c3`）（RESOLVED／歷史）

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

## 最終相容性驗收（GPT Gate 彙整，2026-10-04）（RESOLVED／歷史）

| 環境 | 結果 | 說明 |
|---|---|---|
| iPhone + iOS + Google Chrome | **6/6 PASS** | 上表 1–6 項 |
| iPhone + Safari | **3/3 PASS** | 相容性抽測，關鍵流程 |
| Samsung + Google Chrome | **3/3 PASS** | 相容性抽測，關鍵流程；橫向＋鍵盤搜尋正常，0050 搜尋送出與 Detail 流程 PASS |

**Observation（不列 Blocker，未修改程式）**：iPhone + Safari 首次開啟時曾觀察到約 3 秒捲動延遲。重新進入 Detail 後，「立即滑動」與「等待 5 秒後滑動」皆無法重現。

## Phase 2 封版狀態（RESOLVED／歷史）

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
