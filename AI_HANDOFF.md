# AI_HANDOFF — Claude × Codex 交接本

## 0. 目前唯一有效狀態（Compact 後先讀這一節）

**Phase 3 已 VERIFIED / CLOSED（2026-10-05，baseline `82ce3ee9`）。** Compact 後先讀本節；Phase 4 尚未開始，等待 PO 指示。§0.5 以下為 Phase 3 的過程紀錄。不要重新做產品規劃，不要重新開啟已標示 RESOLVED 的 blocker。

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
- **Phase 4 Coding commit：`b78134c1`**（本機，未手動 push；自動排程推送時 SHA 可能被改寫，commit 訊息開頭「feat(phase4): 我的 ETF（自選）」）。**下一位：Codex｜Code Review**（見下方「Phase 4 Coding — 交 Codex Code Review」）。**Phase 4 尚未完成**：Codex 審查與真機驗收都還沒做。
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

### Phase 4 Rev.2.1 — 修訂內容（Claude，2026-10-05）：交 Codex 複審

只改 `PHASE4_PLAN.md` 的測試規格，未改 Router 規格、未 coding：

1. **FL-4**：改為封版 Router 語意。分別從首頁、工具、分類、自選開 Detail → 「查看完整持股異動 ›」→ 同一檔 Flow，`stack` 只剩 `folder(active, flow)`、不留 Detail 層 → Back 回**分類總覽** → Forward 回同檔持股異動（依 PHASE3_PLAN §8.3、§16.6 NV-A～NV-D、RT-22）。§8.2 對應描述同步。FL-2、FL-3 改為以 fixture 保證加碼／減碼、正／負／缺值都存在，保留 computed 色彩與文字 assertion。
2. **UN-5** 拆成三項，與「只復原最近一次」一致：UN-5a 連續 UI 移除只復原最後一檔（回原 index）；UN-5b Toast 存續時以注入 `storage` 使清單縮短，復原插在 `min(index, 長度)`；UN-5c 移除後重排再復原，以原數字 index 夾限。不擴成多筆復原。

**Codex 複審範圍**：只看 FL-4（含 FL-2／FL-3 的 fixture 補充）與 UN-5a～c。已 RESOLVED 的 Finding 1～3 不重審。PASS 後交 PO／GPT Gate 決定 D1～D6，未授權 coding。

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
- **Codex｜Code Review（下一位）**：審查 Phase 4 coding commit（見「Phase 4 Coding — 交 Codex Code Review」）。PASS 後由 Claude 提供 PO 真機驗收步驟（iPhone Chrome 主測、Samsung Chrome 抽測）。

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
