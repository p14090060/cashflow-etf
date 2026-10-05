# AI_HANDOFF — Claude × Codex 交接本

## 0. 目前唯一有效狀態（Compact 後先讀這一節）

Compact 後請先讀本檔與 `PHASE3_PLAN.md`，然後從「0.5 Phase 3 Coding 狀態」繼續。不要重新做產品規劃，不要重新開啟已標示 RESOLVED 的 blocker。

### 0.1 專案與階段

- 專案：ETF 存股雷達（`c:\專案\etf`）。靜態 PWA，部署於 GitHub Pages。傳統 `<script>`，無 build，無框架。
- Phase 0–2：已完成（由 Product Owner 確認）。
- **Phase 2：VERIFIED / CLOSED。** Verified functional baseline：`1958cdc0`。封版文件：`74c61106`。已 push。
- **Phase 3 Plan：Rev.3.3，commit `8326f465`。** Codex 最終結論：**PASS FOR CODING AFTER PRODUCT DECISIONS**。
- **Phase 3 Resync blocker：RESOLVED**（Rev.3.3 已通過）。
- **Phase 3：APPROVED FOR CODING。**
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
- **Phase 3：尚未 Verified。** 等待 iPhone + Chrome 最終真機驗收（§0.5 清單）。
- **Phase 3 B6 警示條輕量化 commit：`ec2eec09`**。**Codex 複審 `395c774e..ec2eec09`：PASS，checkpoint 關閉，不再修改或重審。**
- **Phase 3 文件夾說明／藏字 commit：`3bde9239`**（本機，未手動 push）。PO 真機後的 refinement，PO／GPT Gate 核准。**等待 Codex 唯讀複審（範圍 `ec2eec09..3bde9239`，不含資料 commit）。**

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

### 0.6 下一步

- **Codex：唯讀複審 `ec2eec09..3bde9239`**。重點：grid／`display: contents` 的堆疊與 z-index、`-6px` 疊層不遮文字、8 份同高、`#catNote` 位置、opening 動畫（`.is-pulled`）、`catSub` 留空對 inside／tight3／橫向的影響、FO 測試是否確實驗證。B6 與更早的範圍不重審。
- **Claude**：Codex PASS 後，提供 PO 真機步驟：§0.5 六項，加上 B6（390 直向警示 2 行），以及文件夾（說明完整、無藏字、堆疊感、inside 不重複說明）。
- **PO**：執行真機驗收；全數 PASS 後由 PO／Gate 宣告 Phase 3 Verified。若有 FAIL，Claude 依回饋修正並交 Codex。
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
