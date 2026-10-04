# PHASE3_PLAN.md — 分類瀏覽與導覽重組（Phase 3）

狀態：**Plan Rev.3.3，待 Codex 複審（只驗 resync blocker）。尚未開始 Coding。**
前置：Phase 2 VERIFIED / CLOSED（功能 baseline `1958cdc0`；封版文件 `74c61106`）。
Rev.3 只修正 Codex 對 Rev.2（`eebc1794`）的 findings，不擴張 scope。

---

## 0. Rev.3 修訂摘要

| Codex finding | Rev.3 處理 | 章節 |
|---|---|---|
| 1. Detail history 須保留 Phase 2 語意（未開啟→push；已開啟切換→replace；一次 Back 離開） | 明列 Phase 2 現行語意；router 只委派 history 操作，語意不變 | §6、§7.5 |
| 2. 退層規則 Rev.2 §7.3 與 §7.6 矛盾 | 選定單一方案（§7.1）；移除 Rev.2 的 back 迴圈 | §7 |
| 3. 「查看持股異動」導航順序錯誤 | 改為先退到共同層級，再 push 目標層；四種來源都驗證 | §8 |
| 4. 首次載入失敗的 Detail 行為被誤寫成「延後還原」 | 依 `showDataError()` 實際行為修正；history 與畫面一致 | §7.10、§12 |
| 5. 170px 低高度不可能同時容納所有 UI | 定義讓位優先序，沿用 Phase 1 `gs-ckm` 觸發條件；以可視區量測驗證；20px fallback 驗證恢復 | §11 |
| 6. flow.js 仍綁 `page-check.active` | 列出所有顯示、resize、redraw 觸發點與回歸測試 | §9 |
| 7. 細部分布錯誤 | 依 Codex 核對：市值型 9、其他 1；總分布維持 18／22／32／20／78／19／6／8 | §2.2 |
| 8. D-ESG 與 D14 維持 pending | D-ESG 補上三檔的標的指數證據（§3.4），不以「50」判定；D14 保留 PO 決策 | §3.4、§18 |

**已採預設、不再詢問 Product Owner**：D11（桌機第一版維持 430 欄）、D12（重整還原資料夾與 Detail）、D13（排序與已展開數不跨開啟記憶）、D15（↻ 維持 Phase 2 行為）、D16（首頁標籤改為「首頁」）、D17（持股異動入口在 分類 → 主動式）。

**仍 pending**：D-ESG（三檔歸類）、D14（自選分頁內容）。

**Rev.3.1 只修兩項**（不改其他章節）：(1) §7.8 的 timeout 與晚到事件規則，及對應測試 RT-14～RT-18；(2) §11.1–11.2 的 visualViewport 座標系，及對應低高度與鍵盤測試 LR-7～LR-9、§11.6。另修正 §18.2 的一句錯誤敘述。

**Rev.3.3 只修 3 秒 resync**（§7.8、§7.8.1、RT-19、§19 的 R-N3，以及 §7.1 R7 與 confirmed 定義中的 resync 字樣）：3 秒只進入「處理中」，不清除 inflight、不執行 parked、不發第二個 traversal、不以 `history.state` 宣告完成。

**Rev.3.2 只修 router 的 timeout 後新操作**（§7.1、§7.5–§7.8、RT-14～RT-21、§19 的 R-N3）：timeout 只取消 continuation，不代表 traversal 完成；區分「已確認位置」與「請求目標」；在途期間新導航一律 park。visualViewport（§11）未變動。

---

## 1. 導覽與既有功能遷移

### 1.1 底部導覽

| 位置 | 名稱 | 內容 | 狀態 |
|---|---|---|---|
| 1 | 首頁 | 原「今日」頁（A-1～A-4），內容不變 | 既有（標籤改名，D16） |
| 2 | 分類 | 八大資料夾（§4）；主動式資料夾內含持股異動 | 新增 |
| 3 | 自選 | 內容待 PO 決策（D14） | 待決策 |
| 4 | 工具 | 工具列表：配息工具、排行、YouTube 頻道 | 新增（承接既有） |

既有 5 個分頁（今日、配息、頻道、主動、排行）收斂為 4 個主導覽。既有頁面全部保留，只改入口與容器。

### 1.2 既有功能遷移（Phase 3 不刪除任何既有功能）

| 既有位置 | 既有內容 | Phase 3 新位置 | 進入方式 | 備註 |
|---|---|---|---|---|
| 今日（`page-today`） | A-1～A-4 | 首頁 | 導覽 1 | 內容不變 |
| 配息（`page-div`） | B-1 計算機、B-2 行事曆 | 工具 → 配息工具 | 工具卡片 | 子頁；Back 回工具列表 |
| 排行（`page-rank`） | E-1 成交量排行 | 工具 → 排行 | 工具卡片 | 子頁；Back 回工具列表 |
| 頻道（`page-yt`） | C-1～C-3 | 工具底部連結；首頁保留小入口卡 | 工具卡片、首頁入口 | 子頁 |
| 主動（`page-check`） | 持股異動：chips、treemap、加減碼總計 | 分類 → 主動式 → 持股異動分段 | 分類內切換分段 | DOM 與功能保留，只換容器（§9） |
| Detail「查看完整持股異動 ›」 | `detailGoFlow` → `openFlow` | 分類 → 主動式 → 持股異動，並選定代碼 | Detail 按鈕 | 導航順序見 §8 |
| 健診（`archived-check`） | 已下架 | 不變 | — | 不在導覽 |

### 1.3 呼叫點

既有程式中 `switchPage('check' | 'div' | 'rank' | 'yt')`、`openFlow(code)`、`detailGoFlow(code)` 都會改為 router 的導航入口。實作前須列出全部呼叫點（PHASE3_CHANGELOG 記錄），並保留舊函式名作為相容入口。

---

## 2. 資料現況與分布

來源：`data/market.json`（203 檔；bot 於 2026-10-04 14:25 更新）、`data/active_flow.json`（32 檔）、`data/dividend_info.json`（人工維護）。

### 2.1 欄位可用性

| 欄位／線索 | 實測 | 能否作為分類依據 |
|---|---|---|
| `div_category`（人工配息標籤） | 高股息 76、指數型 8、主動型 12、海外 10、科技 6、ESG 4、債券 3、主題型 2、產業型 1、無 81 | 只作備援（§4.1 第 10 順位） |
| 代號末碼 `B`／`D` | 6 檔：00840B、00980D、00982D、00983D、00984D、00985D | 可用（與 `is_bond_etf` 一致） |
| 代號末碼 `A` | 32 檔，與 `active_flow.json` 完全一致（已逐一核對） | 可用；執行期不讀 `active_flow.json` |
| 名稱關鍵字 | 市場資料的 `name` 為簡稱 | 可用，但有名稱來源限制（§3.5） |

### 2.2 人工標籤「高股息」的細部分布（Codex 核對）

人工標籤為「高股息」的 76 檔中，只有 22 檔在高股息資料夾（名稱命中 19 ＋ 備援 3）。其餘 54 檔：

- **移至市值型：9 檔**（含 00923 群益台ESG低碳50，見 §3.4，此項 pending）
- **移至其他：1 檔**（00888 永豐台灣ESG）
- 其餘 44 檔：海外 14、主動式 12、科技 11、主題型 4、債券 3

### 2.3 八大分類總分布（Rev.2 驗證值，Rev.3 維持）

| 分類 | 檔數 |
|---|---|
| 市值型 | 18 |
| 高股息 | 22 |
| 主動式 | 32 |
| 科技／半導體 | 20 |
| 海外／區域 | 78 |
| 主題型 | 19 |
| 債券 | 6 |
| 其他 | 8 |
| **合計** | **203** |

這組數字只是目前資料的驗證結果，不是永久 assertion（§16.2）。其中 00920、00923、009809 的歸類待 D-ESG 決定，替代數字見 §3.4 與附錄 B。

---

## 3. 分類規則

### 3.1 單一歸屬與優先順序

依序判斷，命中即停止。

| 順序 | 類別 | 規則 | 說明 |
|---|---|---|---|
| 1 | 債券 | 代號末碼 `B` 或 `D` | 代號規則 |
| 2 | 主動式 | 代號末碼 `A`，或名稱含「主動」 | 主動產品的身分優先於行業 |
| 3 | 其他 | 名稱以「期」開頭 | 期貨型，非股票籃 |
| 4 | 海外／區域 | 名稱含地區、國家、國際指數關鍵字（附錄 A） | 海外＋高息 → 海外（怡恩確認） |
| 5 | 科技／半導體 | 名稱含科技、半導體、電子、晶圓、IC設計、AI、PCB、資安、5G、通訊 | 科技＋高息 → 科技（怡恩確認）；AI 機器人、航太防衛 → 科技（怡恩確認） |
| 6 | 高股息 | 名稱含高股息、高息、股利、優息、高填息 | |
| 7 | 市值型 | 名稱含 50、100、中型、中小、加權、藍籌、領袖、龍頭、MSCI台灣、台灣50、臺灣50 | 見 §3.4：「50」單獨不足以判定市值型 |
| 8 | 主題型 | 名稱含太空、稀土、元宇宙、機器人、生技、基因、綠能、電動車、智能車、未來車、車、潔淨、能源、電池、儲能、電力、數據、算力、航運、航太、防衛、數位、金融、工業 | 金融、工業、數位支付 → 主題（怡恩確認） |
| 9 | 其他 | 名稱含 ESG、公司治理、淨零（策略型） | 策略型原則歸其他（怡恩規則）；見 §3.4 |
| 10 | 高股息（人工備援） | 以上皆未命中，且 `div_category` 為「高股息」 | 只作最後備援 |
| 11 | 其他 | 以上皆未命中 | 包含 0057（待查證，§3.6） |

### 3.2 例外與理由

- **地區優先於策略**：「國泰標普低波高息」「元大US高息特別股」歸海外，與「富邦美國特別股」一致。
- **科技優先於高股息**：「復華台灣科技優息」「兆豐電子高息等權」歸科技。
- **地區規則排在科技之前**：009828 中信台日韓PCB 命中「韓」，歸海外（區域型），因為投資範圍是三國，不是單一產業。
- **主動優先於行業**：「主動安聯美國科技」歸主動式。

### 3.3 策略型與「不能只因 ESG 強制其他」

依怡恩規則：ESG、公司治理、淨零等策略型原則歸其他，但若有更明確的主要產品定位，應優先使用較明確的分類。

| 代碼 | 名稱 | 規則結果（Rev.2） | 理由 |
|---|---|---|---|
| 00930 | 永豐ESG低碳高息 | 高股息 | 「高息」是更明確的定位 |
| 00850 | 元大ESG永續 | 其他 | 無更明確定位 |
| 00888 | 永豐台灣ESG | 其他 | 無更明確定位 |
| 00928 | 中信上櫃ESG 30 | 其他 | 無更明確定位 |
| 00692 | 富邦公司治理 | 其他 | 策略型 |
| 00920 | 富邦ESG綠色電力 | 主題型（待 D-ESG） | 見 §3.4 |
| 00923 | 群益台ESG低碳50 | 市值型（待 D-ESG） | 見 §3.4 |
| 009809 | 富邦淨零ESG50 | 市值型（待 D-ESG） | 見 §3.4 |

### 3.4 D-ESG：三檔的分類依據（Rev.3 補證據，決定仍待怡恩）

**不以「50」判定市值型。** 以下依各檔的標的指數與選股方法，來源為公開網頁（次級來源與投信頁面）：

| 代碼 | 標的指數與選股方法 | 證據指向 | Rev.2 現行 | 證據支持的替代 |
|---|---|---|---|---|
| **00923 群益台ESG低碳50** | 追蹤「臺灣指數公司特選臺灣 ESG 低碳 50 指數」。先篩流動性，剔除博弈、菸草、色情、軍事等爭議業，保留 ESG 評等 BBB 以上，再依碳密度低選出 50 檔。成分約六成集中於半導體。 | ESG 低碳篩選策略。「50」是成分檔數，不是市值範圍定位。 | 市值型 | **其他（策略型）** |
| **009809 富邦淨零ESG50** | 追蹤「S&P TIP 臺灣淨零轉型 ESG 50 指數」。母體為 S&P 臺灣中大型股，排除爭議業、EPS<0、無碳排資料的公司，再以碳排強度與 ESG 分數做權重優化。 | 淨零／ESG 策略。母體是中大型股，但指數的定義來自 ESG 與碳排條件。 | 市值型 | **其他（策略型）**；若怡恩認為母體定位較明確，則維持市值型 |
| **00920 富邦ESG綠色電力**（官方全名：富邦全球ESG綠色電力） | 追蹤「NYSE FactSet 全球綠能 ESG 指數」。投資全球綠電產業（太陽能、風能、氫能、水力、地熱、生質能、儲能），涵蓋 25 國。 | 綠能主題，且範圍為全球。 | 主題型 | **海外（全球）**，與 00762 元大全球AI、00876 元大全球5G 一致；或維持主題型 |

**名稱來源限制（R-N1）**：規則比對的是市場資料中的簡稱。00920 的簡稱「富邦ESG綠色電力」不含「全球」，所以目前落在主題型；官方全名含「全球」，依同一規則應落在海外。這是名稱來源造成的不一致，需怡恩一併決定（見 D-ESG-2）。

**證據來源**：
- 00923：[StockFeel 股感](https://www.stockfeel.com.tw/00923-%E7%BE%A4%E7%9B%8A%E5%8F%B0%E7%81%A3esg%E4%BD%8E%E7%A2%B350-etf/)、[豐存股](https://aiinvest.sinotrade.com.tw/Stock/Content/TW/00923)、[財富101](https://rich101.tw/00923-constituents-and-dividend/)。三個來源對指數與選股條件描述一致；**群益投信官方頁尚未直接核對**（查證等級：次級來源）。
- 009809：[富邦投信 ETF 投資網](https://websys.fsit.com.tw/FubonETF/Fund/Profile.aspx?stkId=009809)（投信頁，含追蹤指數）、[StockFeel 股感](https://www.stockfeel.com.tw/009809-%E5%AF%8C%E9%82%A6%E5%8F%B0%E7%81%A3%E6%B7%A8%E9%9B%B6%E8%BD%89%E5%9E%8Besg50-etf/)。
- 00920：[TWSE ETF 資訊](https://www.twse.com.tw/zh/ETFortune/etfInfo/00920)（官方名稱與基本資料）、[StockFeel 股感](https://www.stockfeel.com.tw/00920-%E5%AF%8C%E9%82%A6%E5%85%A8%E7%90%83esg%E7%B6%A0%E8%89%B2%E9%9B%BB%E5%8A%9B-etf/)（指數與持股）。

**D-ESG 替代數字（僅供決定，本 Rev 不套用）**：

| 方案 | 市值型 | 高股息 | 主動式 | 科技 | 海外 | 主題 | 債券 | 其他 | 合計 |
|---|---|---|---|---|---|---|---|---|---|
| **Rev.3 現行（pending 預設，§2.3）** | 18 | 22 | 32 | 20 | 78 | 19 | 6 | 8 | 203 |
| E1：三檔依證據（00920→主題） | 16 | 22 | 32 | 20 | 78 | 19 | 6 | 10 | 203 |
| E2：三檔依證據（00920→海外） | 16 | 22 | 32 | 20 | 79 | 18 | 6 | 10 | 203 |

E1、E2 的市值型為 16，與 Gavin 最初引用的數字一致。

### 3.5 名稱來源（R-N1）

規則的輸入是市場資料的 `name`（簡稱）。若官方全名含有簡稱沒有的地區或策略字眼，分類可能不一致。Rev.3 不改 pipeline，也不新增欄位；這個限制列為 R-N1，由 D-ESG-2 決定是否建立人工覆寫清單（覆寫清單需附來源，並進 CHANGELOG）。

### 3.6 0057 富邦摩台：暫歸其他／待查證

名稱無法判定。依 CLAUDE.md 的靜態資料鐵則，不得憑記憶或名稱推測。查證前歸其他；查證後以附註記錄來源。

### 3.7 不做的事

- 不以 `div_category` 作為主依據。
- 不為單一 ETF 寫死代碼（0057 除外，它只是未命中的預設）。
- 不在執行期讀取 `active_flow.json` 判斷分類。
- 不新增第 9 類。

### 3.8 新 ETF 與未命中

- 新 ETF 自動套規則；未命中進其他，**不會消失**。
- 規則表的任何改動都要附受影響代碼清單，並記入 CHANGELOG。

---

## 4. 分類與資料夾 UI

### 4.1 八大分類

| 順序 | 分類 | 資料夾說明（UI 文案） |
|---|---|---|
| 1 | 市值型 | 主要追蹤大型、中型或特定市值範圍指數的 ETF |
| 2 | 高股息 | 主要以高股息策略為特色的 ETF |
| 3 | 主動式 | 由經理人主動操作持股的 ETF |
| 4 | 科技／半導體 | 主要投資科技與半導體產業的 ETF |
| 5 | 海外／區域 | 主要投資海外市場或特定地區的 ETF |
| 6 | 主題型 | 聚焦特定主題或產業（如金融、工業、數位支付）的 ETF |
| 7 | 債券 | 主要投資債券的 ETF |
| 8 | 其他 | 不屬於前述分類，或以 ESG 等篩選策略為主、期貨型等的 ETF |

資料夾底部固定一行：「分類是主要方向，不代表 ETF 的全部特徵。想找特定條件的 ETF，請用上方搜尋。」

### 4.2 總覽（OVERVIEW）

- 左右各一堆，每堆 4 份，合計 8 份。
- 每份只露出頁籤：高 44px，文字 15px，含分類名與檔數。
- 後面的頁籤在上，前面的在下；頁籤彼此不重疊。
- 同一堆內頁籤水平交錯 ±3px，**不旋轉**文字。

### 4.3 狀態機

| 狀態 | 畫面 | 進入 | 離開 |
|---|---|---|---|
| **OVERVIEW** | 8 份頁籤堆疊 | 進入分類導覽；router 回到此層 | 點頁籤 → OPENING |
| **OPENING** | 被點文件夾抽出到主區；其他 7 份退到次要區 | OVERVIEW 點頁籤 | 過場結束（reduced-motion 立即）→ OPEN |
| **OPEN** | 主區：分類名、說明、檔數、排序、清單（前 10 檔）、查看更多；次要區 7 個短標籤 | OPENING 結束；次要標籤切換完成 | ✕／Esc／Back → CLOSING；點次要標籤 → 切換；點 ETF → DETAIL；（主動式）切分段 → FLOW |
| **FLOW**（主動式的分段） | 持股異動畫面 | 主動式資料夾內切換分段；§8 的導航 | 切回清單分段；Back 離開資料夾 |
| **DETAIL** | Phase 2 Detail 疊在 OPEN 上方 | OPEN 點 ETF；搜尋選取 | ✕／Back／Esc → OPEN（資料夾保留） |
| **CLOSING** | 文件夾回到堆疊位置 | ✕／Esc／Back | OVERVIEW |

OPENING 與 CLOSING 期間忽略點擊（`pointer-events:none`）。過場結束以 `transitionend` 為主，另加 240ms 保險計時器。

### 4.4 主區（OPEN）

- 標題列：「海外／區域 · 78 檔」＋ 說明文案 ＋ 排序鈕（代碼／名稱）＋ ✕。
- 主動式資料夾多一個分段：「ETF 清單」｜「持股異動」。
- 清單列：代碼（等寬）、名稱（超出省略）、殖利率（沿用排行頁規則；查無顯示「--」）。
- 整列可點，點擊 → 開啟 Detail。列高 ≥ 44px。
- 底部「查看更多（還有 N 檔）」，全部顯示後隱藏。
- 文字不出現買賣字樣。

### 4.5 焦點與無障礙

- 開啟後焦點移到主區標題；收合後回到原頁籤。
- 頁籤為 `<button>`，帶 `aria-expanded`。
- Esc 只退一層（§7.9）。

---

## 5. 列表行為

| 項目 | 規則 |
|---|---|
| 預設排序 | 代碼由小到大，數字感知：先比數字部分，再比字母後綴。例：0050 → 0051 → 0056 → 0061 → 00400A → 00401A → 00625K → 00981A → 006201 → 009800 |
| 名稱排序 | `Intl.Collator('zh-Hant', {numeric:true})`；不支援時退回 `localeCompare`，再退回 `<` |
| 切換 | 排序鈕在代碼與名稱之間切換，皆由小到大 |
| 首次顯示 | 最多 10 檔 |
| 查看更多 | 每次 +10；全部顯示後隱藏 |
| 狀態保存 | 排序、已展開數、清單捲動位置，保存在 router 的 folder 層（§7.2） |
| 重設 | 從總覽重新開啟資料夾時重設（D13）。從 Detail 返回時**不重設** |

---

## 6. Detail 的語意與 Phase 2 相容（Rev.3 新增）

### 6.1 Phase 2 現行語意（需保留，已由既有測試驗證）

| 情境 | 行為 | history 操作 | 既有驗證 |
|---|---|---|---|
| 尚未開啟 Detail，開啟 ETF A | 顯示 A | **push 一層 Detail** | detail_ui T2 |
| Detail 已開啟 A，切換到另一檔 B | 顯示 B | **replace 當前 Detail state**（code 改為 B），不增加 entry | detail_ui T12（`history.length` 不變） |
| Detail 已開啟，再點同一檔 | 無變化 | 無 | — |
| 關閉 Detail（✕、Esc、Back） | 關閉 | 只做一次 back；一次 Back 直接離開 Detail，不因切過多檔而累積 | detail_ui T8、T9、T10、T19 |
| 關閉後再開啟 | 正常 | 再 push 一層 | — |

**重點**：切換 ETF 不得累積 history 層；一次 Back 必須直接離開 Detail。

### 6.2 Router 的 Detail 操作（委派，但語意不變）

- `router.openDetail(code)`：
  - 若 stack 頂層不是 detail → **push** `{t:'detail', code}`。
  - 若頂層已是 detail 且 code 不同 → **replaceTop** `{code}`（不增加 entry）。
  - 若 code 相同 → 無 history 操作。
- Rev.2 的「openDetail 一律 push」是錯的，Rev.3 撤回。
- `router.closeTop()` 在頂層為 detail 時只做一次 back（§7.5）。

### 6.3 不改寫的部分

Detail 的畫面、分頁、計算機、收合、刷新 slot patching、flow 區塊，都不改。只把 history 相關呼叫改成委派給 router。history 相關的內部變數（`_pendingPop`、`_queuedOpen`、`_detailPushed`、detail.js 內的 popstate listener）會移除，改由 router 管理，行為由 §10 的測試驗證。

---

## 7. 共用 Router：history 協調

### 7.1 退層與導航規則（Rev.3.2，唯一方案）

| 規則 | 內容 |
|---|---|
| **R1 popstate 只渲染** | popstate 只根據 `history.state`（normalize 後）渲染。popstate 本身不呼叫 `history.back()`、`go()`。 |
| **R2 單層關閉** | 使用者關閉頂層 → 一次 `traverse(-1)`。 |
| **R3 導航以 intent 表示** | 所有導航（開啟 Detail、關閉頂層、切換基底、查看持股異動）都先表示為 **intent**：在執行當下依**已確認位置**求值，回傳目標 `{base, stack}`。 |
| **R4 單一 traversal 槽** | 任一時間最多一個 traversal 在途（含 orphan）。每次導航最多呼叫一次 `traverse(-k)`，沒有 back 迴圈。 |
| **R5 在途時一律 park** | 槽位被佔用時，新導航不計算 k、不寫入 history，只把 intent 存為 `parked`（last wins）。 |
| **R6 continuation 驗證** | 在途 traversal 完成時，只有已確認位置的 `base` 與 `stack` 等於規劃時的前綴，才執行其 continuation（只 push／replace）；不符則丟棄 continuation，以已確認位置渲染。驗證以內容比對進行，不宣告 traversal 已完成。 |
| **R7 完成的唯一依據** | traversal 只有在 popstate 抵達時才算完成。**timeout 與「處理中」標記都不算完成。** |
| **R8 在途時不寫 history** | 有在途 traversal 時，任何 history 寫入（含 `replaceTop` 的 ui 快照）都不執行；ui 狀態只留在記憶體，待確認後再快照。 |

**位置的兩種身分（Rev.3.2 明確區分）**
- `confirmed`：瀏覽器已確認的目前 entry（只在 popstate 抵達時更新）。**所有規劃（k、前綴、intent 求值）只使用 `confirmed`。**
- `requested`：在途 traversal 的目標。只記在 `inflight` 裡，**不得用於規劃新導航**。

Rev.3.1 的 `expected` 與 nonce 已移除。

### 7.2 狀態模型

**層（layer）**：由下往上堆疊的覆蓋物。

| 類型 | 欄位 |
|---|---|
| `folder` | `key`、`view`（`list`／`flow`）、`ui`（`sort`、`shown`、`scrollTop`、`code`） |
| `detail` | `code`、`ui`（`tab`、`scrollTop`） |
| `tool` | `id`（`div`／`rank`／`yt`）、`ui` |

**基底（base）**：`home`／`cat`／`watch`／`tools`，不是層。

**history.state**（每個 entry 都是完整快照）：

```
{ v: 2, base: 'cat', stack: [ {t:'folder', key:'active', view:'list', ui:{...}}, {t:'detail', code:'00981A', ui:{...}} ] }
```

popstate 只需渲染 `state`，不需要推算。

### 7.3 Entry 不變條件

1. **E0 唯一**：stack 為空的 entry 即基底 entry。它只由 router 在啟動時 `replaceState` 寫入，之後不為基底變更建立新 entry。
2. **每層一個 entry**：push 一層 = 一次 `pushState`，entry 的 stack 長度 = 從 E0 往上的層數。
3. **同層更新只 replace**：切換 ETF（detail）、切換次要標籤、切換分段、排序、已展開數、捲動，全部只 `replaceState` 當前 entry，不新增 entry。
4. **基底切換只在 E0 發生**：切換底部導覽時，若 stack 非空，先由 R3 退回 E0，再 `replaceState` 基底。
5. **popstate 不呼叫 back**（R1）。

### 7.4 Migration 與防止重複基底（Rev.3 新增）

Phase 2 的 history 格式是 `{etfDetail:1, code}`，沒有 `v`，也沒有 base。Migration 規則：

| 啟動時 `history.state` | 處理 | 新增 entry？ |
|---|---|---|
| `v === 2` | 直接使用 | 否 |
| `etfDetail`（Phase 2 格式，例如部署前開著的分頁重新載入） | normalize 為 `{v:2, base:'home', stack:[{t:'detail', code}]}`，`replaceState` 當前 entry | **否** |
| `null` 或其他 | normalize 為 `{v:2, base:'home', stack:[]}`，`replaceState` 當前 entry | **否** |

**啟動時絕不 push。** 因此不會產生第二個基底 entry。

popstate 遇到 Phase 2 格式或 `null` 時，同樣只 normalize 當前 entry（`replaceState`），不新增 entry。

**已知限制（沿用 Phase 2）**：↻ 使用 `location.replace` 時，跨文件的 history 會留下舊 entry（見 §7.11）。

### 7.5 操作表（Rev.3.2，全部經 intent）

| 操作 | intent（執行當下依已確認位置求值） | 無在途 traversal | 有在途 traversal（R5） |
|---|---|---|---|
| `openDetail(code)` | §6.2：頂層為 detail 且 code 不同 → replace；頂層非 detail → push；相同不變 | 依 §7.7 執行 | park |
| `closeTop()` | 目標 = 已確認 stack 去掉頂層 | 一次 `traverse(-1)`（R2） | park |
| `navigate(base／folder／tool)` | 目標 = 指定的 base 與 stack | 依 §7.7 | park |
| `openFlow(code)` | 目標 = `{base:'cat', stack:[folder(active, flow, code)]}`（§8） | 依 §7.7 | park |
| `replaceTop(patch)` | 只更新 ui | 立即 `replaceState` | 不寫 history（R8） |

Phase 2 的 Detail 語意（§6.1）由 `openDetail` 的 intent 保留。

### 7.6 popstate（唯一入口，與 §7.8 統一）

1. `c = normalize(event.state)`（§7.4）。
2. **若無在途 traversal**：渲染 `c`；若有 `parked`，依 `c` 求值並執行（§7.7）。結束。
3. **若有在途 traversal `f`**：
   1. 清除 `inflight`。此 popstate 是 `f` 的完成事件（R7）。
   2. 若 `f` 為 active，且 `c` 符合 `f` 的規劃前綴（R6），執行 `f.continuation`，得到最終 state；否則丟棄 continuation。
   3. 若 `f` 為 **orphan**：**不執行任何 continuation。**
   4. 渲染：若存在 `parked`，**不渲染** `c`（畫面由 parked 的執行結果決定，避免閃回舊狀態）；否則渲染 `c` 或步驟 2 的最終 state。
   5. 若存在 `parked`：取出並清空，依**已確認位置**求值 intent 並執行（§7.7）。這是新導航自己的執行，不是 `f` 的 continuation。

### 7.7 navigate(intent) 協議（Rev.3.2）

1. 若 `inflight` 不為空 → `parked = intent`，返回（不計算 k，不寫 history）。
2. 依 `confirmed` 求值 `target = intent(confirmed)`。
3. 計算共同前綴 `p`：逐層比對 type、key、view、code；基底不同則 `p = 0`。`k = confirmed.stack.length − p`。
4. 若 `k = 0`：基底相同，直接 push 剩餘層。
5. 若 `k > 0`：
   - 建立 `inflight = {delta: −k, plannedPrefix: {base: confirmed.base, stack: confirmed.stack.slice(0, p)}, continuation: {base（若不同）, layers: target.stack.slice(p)}, state: 'active'}`；
   - 啟動 500ms timeout；
   - 呼叫 `traverse(−k)`，這是唯一的 history traversal 呼叫。

**規劃只使用 `confirmed`。** 這正是為了避免：在 traversal 尚未確認前，用假定的 expected 位置算出 k=0，並把 push／replace 寫進仍停留的舊 Detail entry。

### 7.8 timeout、orphan 與 3 秒處理中（Rev.3.3）

**timeout（500ms 內沒有 popstate）**
1. 清除 busy。使用者可以再操作，但新操作依 R5 被 park，不被忽略。
2. **取消 `inflight.continuation`**，之後永不執行。
3. `inflight.state = 'orphan'`。**槽位仍被佔用。** timeout 不代表 traversal 完成，瀏覽器可能尚未移動。
4. 畫面與 history 都不變（不渲染、不寫入）。

**orphan 完成**：下一個 popstate（R7）清除槽位，依 §7.6 步驟 3 處理：不執行 continuation；有 parked 時由 parked 決定畫面。

**3 秒「處理中」（只顯示，不改狀態）**
- 從發出 traversal 起算 3000ms 仍沒有 popstate → 畫面顯示「處理中」指示。
- **只做顯示。** 不清除 `inflight`，不執行 `parked`，不發出第二個 traversal，不寫入 history，不讀取 `history.state` 來宣告完成。
- `inflight`（含 orphan 狀態）與 `parked` 都保留。新操作仍依 R5 被 park，不會建立新的 traversal。
- 之後仍只等待真正的 popstate。

**真正的完成（popstate 抵達）**
1. 取得 `confirmed = normalize(event.state)`（R7 唯一的完成依據）。
2. 清除 `inflight` 與「處理中」指示。
3. orphan continuation 永遠不執行（§7.6 步驟 3）。
4. 依**新的 `confirmed`** 求值 `parked` intent，**只執行一次**（§7.7），清空 `parked`。

**不可能的完成方式**：以目前 `history.state` 宣告舊 traversal 已完成；以計時器清除槽位；以 3 秒到達後執行 parked。這些都被禁止。

**「處理中」無法自行結束時的復原**：若 traversal 理論上永不抵達（只在歷史入口不存在時發生），系統停在「處理中」，不會假定完成。復原方式是重新整理：重新整理從實際的 `history.state` 還原（§7.11、RT-3），這是使用者可以採取的明確動作，不是系統自動猜測。

**busy 的意義**：busy 只代表「active traversal 在途且未逾時」，此時使用者請求被忽略。timeout 後不再忽略，改為 park。

### 7.8.1 測試 hook（只在測試環境使用，行為忠實於瀏覽器）

| hook | 行為 |
|---|---|
| `window.__routerDeferTraversal = true` | `traverse()` 不呼叫 `history.go`，改排入佇列，模擬「traversal 尚未完成」。`window.__routerDeferredCount` 可讀。 |
| `window.__routerReleaseTraversal()` | 執行佇列中的真實 `history.go`，popstate 隨後抵達。 |
| `window.__routerForceTimeout()` | 立即執行 active → orphan 的 timeout 流程。 |
| `window.__routerForceProcessingMark()` | 立即執行「3 秒仍未完成」的標記：顯示處理中，不改變任何狀態。 |
| `window.__routerInflightState()` | 回傳目前在途 traversal 的狀態：`null`、`active` 或 `orphan`。 |
| `window.__routerCompletions` | 每次 popstate 完成在途 traversal 時 +1（RT-19 用來確認舊 traversal 只被完成一次）。 |
| `window.__routerParkedRuns` | 每次 parked intent 被執行時 +1（RT-19 用來確認只執行一次）。 |
| `window.__routerProcessing()` | 回傳「處理中」指示是否顯示。 |
| `window.__routerTraversalCount` | 每次 `traverse()` 呼叫計數（RT-21）。 |

### 7.9 Esc

- Esc 只呼叫 `closeTop()` 一次。
- 有在途 traversal 時，依 R5 park（以 `closeTop` 的 intent 求值，見 §7.5）；active 階段的 busy 期間忽略。
- 頂層是 Detail → 只關 Detail，資料夾保留。
- 頂層是資料夾 → 關資料夾。

### 7.10 首次載入失敗與 history 一致性（依 `showDataError()` 實際行為）

**Phase 2 現行行為（依程式碼）**：
- `boot.js` 的 `showDataError()` 在首次失敗時顯示「資料暫時無法取得，請稍後按右上角 ↻」，並**立即**呼叫 `_tryRestoreDetail()`。
- 因此，若重新整理前 Detail 開著，失敗時 Detail 會**立即**開啟，內容為「資料暫時無法取得」（`detailPatch()` 的空資料分支）。這不是「延後還原」。
- 資料之後載入成功時，Detail 由 `detailOnMarketUpdate()` 補上內容。

**Phase 3 規則**：
- 失敗時 router **不得移除任何層**，因為 history 與畫面必須一致。
- 資料夾層在失敗時顯示空狀態（§12）。
- Detail 層顯示與 Phase 2 相同的「資料暫時無法取得」。
- 資料後來成功時，層的內容自動補上，**history 不變**。

**測試**：HF-1 — 首次失敗時 `history.state` 的深度等於畫面上的層數；HF-2 — 失敗後成功，畫面補上內容且深度不變。

### 7.11 Reload（D15、D12）

- 啟動時 base 立即套用；stack 的層在**資料可用後**才渲染（資料夾與 Detail 都需要資料）。資料失敗時依 §7.10 立即渲染空狀態。
- 還原前必須再次驗證 `state` 與畫面一致，避免錯配（Phase 2 Blocker 的教訓）。
- ↻（D15）：維持 Phase 2 行為。Phase 2 以 `location.replace` 重新載入，**已知限制**：跨文件返回。Phase 3 不改此行為；若要改為就地更新，需另行決定。

### 7.12 不變條件摘要

- 只有 router 呼叫 `pushState`、`replaceState`、`history.back`、`history.go`。
- popstate 只有一個 listener。
- UI 元件不自行記錄 history 狀態。

---

## 8. 「查看完整持股異動」導航（Rev.3 修正）

### 8.1 目標

所有來源最終都應到達：**分類 → 主動式資料夾 → 持股異動內容**，且 history 中**不留下 Detail 層**。

### 8.2 演算法

Detail 的按鈕呼叫 `navigate(T)`，其中：

```
T = { base: 'cat', stack: [ {t:'folder', key:'active', view:'flow', code: <code>} ] }
```

- 共同前綴 = 0（T 的唯一層是 folder，當前 stack 的 folder 不會與 `view:'flow'` 且 code 完全相同，因為 Detail 不可能在持股異動畫面上開啟）。
- 因此 k = 當前 stack 長度（含 Detail）。
- 一次 `go(-k)` 回到 E0，再 `replaceState` 基底為 cat，再 push T 的 folder 層。
- **不先 push 主動式資料夾再關 Detail。**

### 8.3 四種來源

| 來源 | 當前 stack（Detail 開著） | k | 續行結果 | Back | Forward |
|---|---|---|---|---|---|
| A 首頁搜尋 → Detail | `[detail]`（基底 home） | 1 | 基底改 cat；push `folder(active, flow)` | 回分類總覽 | 回到持股異動 |
| B 工具子頁搜尋 → Detail | `[tool(div), detail]`（基底 tools） | 2 | 基底改 cat；push `folder(active, flow)` | 回分類總覽 | 回到持股異動 |
| C 其他分類資料夾 → Detail | `[folder(X,list), detail]`（基底 cat） | 2 | push `folder(active, flow)` | 回分類總覽（不回 X） | 回到持股異動 |
| D 原本在主動式 → Detail | `[folder(active,list), detail]`（基底 cat） | 2 | push `folder(active, flow)` | 回分類總覽（不回清單） | 回到持股異動 |

**Back 後不回到 Detail 或 X，是本 Rev 的明確行為**（需 Codex 確認）。

### 8.4 中間畫面

R4 的續行在 popstate 任務內完成，渲染只發生一次，因此不會畫出中間的總覽。仍需真機確認（R-N2）。

### 8.5 持股異動的資料

- `flow.js` 的資料與判斷不改（§9）。
- 32 檔都要能從清單進入（FL-1）。

---

## 9. Flow（持股異動）遷移：顯示、resize、redraw（Rev.3 新增）

### 9.1 現況（依程式碼）

| 位置 | 現行觸發 | 問題（遷移後） |
|---|---|---|
| `nav.js` `switchPage` | `if (id === 'check') renderFlow()` | 持股異動不再是頁面，要改為「主動式資料夾進入 FLOW」時觸發 |
| `flow.js` `window.resize` | `if (page-check.active) renderFlow()` | 改檢查「FLOW 可見」，不是 `page-check` |
| `flow.js` `renderFlow` | `if (_flowData) draw(); else fetchFlow().then(draw)` | 資料在持股異動開著時才回來，需要重繪 |
| `flow.js` `draw` | `box.clientWidth`、`clientHeight` | 資料夾 OPENING 中量到的寬高不是最終值；隱藏時寬為 0 |
| `boot.js` | `fetchFlow().then(renderRank)` | 只在啟動時抓一次；不影響分類頁 |

### 9.2 Rev.3 的觸發規則

| 編號 | 觸發 | 動作 |
|---|---|---|
| F-a | FLOW 進入（OPEN 結束，或 reduced-motion 立即） | `renderFlow()` |
| F-b | `flowSelect(code)` | `renderFlow()`（沿用） |
| F-c | `fetchFlow()` 完成，且 FLOW 可見 | `draw()` |
| F-d | `resize`、`orientationchange`、`visualViewport` resize／scroll，且 FLOW 可見 | `renderFlow()`（低高度時高度也會變） |
| F-e | 資料夾過場結束（OPENING／CLOSING） | 若 FLOW 可見，`draw()`（寬度此時才是最終值） |
| F-f | `box.clientWidth === 0`（容器隱藏） | 跳過繪製，等 F-a／F-e 再畫 |

**「FLOW 可見」的定義**：`router` 的頂層是 `folder(active)` 且 `view === 'flow'`，且資料夾處於 OPEN 狀態。不再使用 `page-check.active`。

### 9.3 DOM 與 CSS

- `#page-check` 內的元素搬到資料夾的 FLOW 容器（`#catFlowHost`）。
- 以下 id 必須保持唯一：`flowMeta`、`flowChips`、`flowBuy`、`flowSell`、`treemap`、`flowTip`、`flowForeign`。
- `css/pages.css` 中所有 `#page-check` 相關選擇器，實作前逐條 grep 並改寫；這是 Codex 指出的風險（R8）。

### 9.4 flow.js 的 onclick 字串

`flow.js` 內的 `onclick="flowSelect('…')"` 與 `flowTap(...)` 字串，搬移後要逐一核對。

### 9.5 FLOW 測試

| 編號 | 測試 |
|---|---|
| FL-1 | 32 檔主動式都能從清單進入持股異動，並選到該檔 |
| FL-2 | Detail「查看完整持股異動」進入正確代碼（§8 四種來源） |
| FL-3 | 視窗 resize 後 treemap 重繪，寬高與容器一致 |
| FL-4 | 切換到其他資料夾再回來，treemap 有非零寬高 |
| FL-5 | `fetchFlow` 在 FLOW 開著時完成，畫面更新 |
| FL-6 | reduced-motion 下進入 FLOW 立即繪製 |
| FL-7 | FLOW 隱藏時 resize 不繪製（F-f） |
| FL-8 | 加減碼總計與「未出新／抓不到」分開顯示與現況一致 |

---

## 10. 工具頁與自選（D14 pending）

### 10.1 工具頁

- 卡片：配息工具、排行、YouTube 頻道。
- 點卡片 → `open(tool)`，顯示既有子頁。Back 回工具列表。
- 工具底部的「YouTube 頻道」為連結卡，不佔導覽。

### 10.2 首頁小入口

首頁保留一張小卡「YouTube 頻道」，點擊 → `open(tool:yt)`。

### 10.3 自選（D14，pending）

- 自選分頁的內容**未決定**。
- Rev.3 不實作任何自選功能，也不實作占位內容。
- PO 決定前，導覽上的自選位置保留，內容以「待決策」處理（實作前需 PO 確認是否只顯示「尚未開放」）。

---

## 11. 響應式與低高度讓位（Rev.3 修正）

### 11.1 座標系（Rev.3.1）

所有量測使用**同一個座標系**：`getBoundingClientRect()` 的座標，相對於 layout viewport。

- **可視區（visible region）**：`visTop = visualViewport.offsetTop`，`visBottom = visualViewport.offsetTop + visualViewport.height`。不支援 visualViewport 時：`visTop = 0`，`visBottom = innerHeight`。
- **元素在可視區內**：`rect.bottom > visTop` 且 `rect.top < visBottom`，且 `display` 不為 `none`。
- **使用者實際看得到（未被遮住）**：
  - 可視區內的可見高度 ≥ `min(元素高度, 12px)`；
  - 且 `document.elementFromPoint(元素在可視區內的中心點)` 命中該元素或其後代（不是被其他固定元件蓋住）。
- **不重複扣 safe area**：`env(safe-area-inset-*)` 已由 `:root` 的 padding 處理；量測直接用 rect，不額外扣除。
- **offsetTop 不為 0 時**：所有比較一律用 `visTop`、`visBottom`，**不得**用 `0` 或 `innerHeight` 代替。

### 11.2 可用高度公式（Rev.3.1）

```
清單頂端     = 清單 rect.top
清單底界     = min(visBottom, 導覽 rect.top（若導覽可見）)
清單可用高度 = max(0, 清單底界 − 清單頂端)
```

清單的 `max-height` 依此公式設定，於 resize、orientationchange、visualViewport resize，以及 visualViewport scroll（offsetTop 變化）時重算（沿用 Phase 2 的 `_gsSyncAll` 模式）。

### 11.3 讓位優先序

| 優先 | UI | 低高度時 |
|---|---|---|
| P0 | 全域搜尋框 | 永遠保留 |
| P1 | 分類標題列（名稱、檔數、✕） | 保留 |
| P2 | 清單 | 保留，取剩餘高度 |
| P3 | 主動式的分段切換 | 與 P1 同列，縮為較小寬度 |
| P4 | 次要 7 個短標籤列 | 先隱藏（見 11.4） |
| P5 | 分類說明文案與底部免責 | 先隱藏 |
| P6 | 頁首標題與 ↻ | 隱藏（Phase 1/2 既有） |
| P7 | 底部導覽 | 隱藏（Phase 1/2 既有） |

### 11.4 讓位觸發（沿用 Phase 1）

**不另立門檻，沿用 Phase 1 的低高度搜尋觸發**：`_gsSyncCkm()` 的條件（搜尋框有焦點，且可視高度 < 「搜尋框未聚焦時量到的頁首高度」＋ `_GS_MIN_LIST_H`（110px））。進入此狀態時 `body.gs-ckm` 生效，Phase 1/2 已定義隱藏的 P6、P7 也隱藏。

Rev.3 在 `gs-ckm` 下額外讓位：

1. **先隱藏 P4、P5**（次要標籤列與說明文案）。
2. 清單取剩餘高度。
3. 若剩餘高度 < 1 列（44px），在清單區顯示一行「收起鍵盤可看完整清單」。

**非 ckm 的低高度**（例如橫向、鍵盤關閉、但高度仍不足）：若清單可用高度 < `_GS_MIN_LIST_H`（110px），依序隱藏 P5，再把 P4 收合為一個「其他分類 ▾」按鈕（40px 高），仍不足則清單保持最小 44px 並可捲動。

### 11.5 測試情境與通過條件

| 編號 | 視窗（寬×高） | 狀態 | 通過條件（以 rect 量測） |
|---|---|---|---|
| LR-1 | 390×844 直向 | 無鍵盤 | P1–P5 全部可見；清單可用高度 ≥ 110px；無水平捲動 |
| LR-2 | 360×780 直向 | 無鍵盤 | 次要 7 個標籤不溢出（需 ≥ 332px）；所有觸控目標 ≥ 44px |
| LR-3 | 844×390 橫向 | 無鍵盤 | 清單可用高度 ≥ 110px，否則依 11.4 讓位；導覽可見 |
| LR-4 | 844×170 | 鍵盤開（ckm） | P0、P1、P2 可見；P4、P5 隱藏；清單可用高度 ≥ 44px；P0 的 rect 與可視區有交集 |
| LR-5 | 844×20 | 鍵盤開（極端） | 見 11.6 |
| LR-6 | 1280×800 桌機 | 無鍵盤 | 同 430 欄置中（D11） |
| LR-7 | 844×20，offsetTop = 0 | 鍵盤開（極端） | 見 11.6 A |
| LR-8 | 844×20 與 844×170，offsetTop > 0 | 鍵盤開（可視區下移） | 見 11.6 B；可視區下界為 offsetTop；搜尋框仍在可視區內，且 elementFromPoint 命中搜尋框 |
| LR-9 | 鍵盤關閉後恢復 | — | 見 11.6 C |

### 11.6 20px 極端情境（使用者可見的 fallback）

**不得只驗證 DOM 中存在文字。** 必須以 rect、可視區與 `elementFromPoint` 驗證使用者實際看得見的內容。

**前置條件（同 C7、C9 的做法）**：測試 B 必須先確認 `visualViewport.offsetTop > 0`；若無法在 headless 產生，測試標記為「前置條件不成立」，不得判為 PASS。此情況需以 iPhone Chrome 真機補測（鍵盤開啟時會實際產生 offsetTop 的情境）。

**A. offsetTop = 0，鍵盤開（844×20）**
- 搜尋框 `rect.top ≤ 2px`，且與可視區 `[0, 20]` 的交集高度 ≥ 12px。
- `elementFromPoint` 於搜尋框在可視區內的中心點命中搜尋框。
- 清單與可視區沒有交集（已知限制，§11.7）。
- 不產生水平捲動；頁面不捲到空白區。

**B. offsetTop > 0，鍵盤開（可視區下移）**
- 可視區為 `[offsetTop, offsetTop + 20]`。
- 搜尋框與該可視區的交集高度 ≥ 12px（以 offsetTop 為下界量測，不是以 0 為下界）。
- `elementFromPoint` 於搜尋框在可視區內的中心點命中搜尋框。
- 不因此在可視區外顯示其他 UI 造成誤會（導覽與標題不應出現在可視區內但被遮住）。

**C. 鍵盤關閉（恢復）**
- `visualViewport.height ≥ 276`（以模擬的 Chrome 狀態為準），offsetTop 回到恢復後的值。
- `body.gs-ckm` 移除。
- P4、P5、P6、P7 的 rect 與可視區有交集，且 `elementFromPoint` 命中該元素。
- 清單與分類標題可見。
- 清單捲動位置與鍵盤開啟前相同；展開數與排序保留。

### 11.7 已知限制

在鍵盤開啟的極小可視區（約 20px）中，清單不可見。這是 Phase 2 已接受的 Known UX limitation，**不針對 20px 寫死任何數值，也不修改 Phase 2 功能**。

---

## 12. 資料更新與失敗

### 12.1 現況（依程式碼）

- `boot.js` 每 30 秒呼叫 `fetchData()`。
- 成功時呼叫 `renderAll()`；失敗時呼叫 `showDataError()`，**不清除既有畫面**。
- 失敗時的 banner 顯示上次更新時間（last-good 行為已存在）。

### 12.2 分類與更新規則

| 情境 | 行為 |
|---|---|
| 成功更新 | 重新計算分類（純函式）；清單與計數更新；排序、已展開數、捲動保留 |
| 資料夾開著時更新 | 清單依新資料重排；`shown = min(shown, total)` |
| ETF 移類 | 從舊資料夾消失、進新資料夾；Detail 不受影響 |
| ETF 消失 | 清單移除；Detail 若正在顯示它，顯示「這檔目前不在清單中」（Phase 2 既有文案），不自動關閉 |
| 新增 ETF | 依規則進入；未命中進其他 |
| 更新失敗 | 保留 last-good：分類與清單維持上次資料，banner 顯示時間 |
| 首次載入失敗 | 見 §7.10 |

### 12.3 不做的事

- 不因更新失敗而清空分類。
- 不因更新而自動跳出或關閉任何層。
- 不為了讓資料夾好看而補數字。

---

## 13. 空分類與錯誤狀態

| 狀況 | 畫面 |
|---|---|
| 首次載入失敗 | 頁籤名稱仍在，檔數「—」；開啟時清單區「資料暫時無法取得」 |
| 某分類 0 檔 | 頁籤「0 檔」可開；清單區「目前沒有符合這個分類的 ETF」 |
| 欄位缺（如 `yld` 為 null） | 殖利率「--」，不補數字 |
| 持股異動資料缺 | 沿用 `flow.js` 的「未出新／抓不到」分開顯示 |
| 新 ETF 未命中 | 進其他 |

---

## 14. 動畫與 reduced-motion

- 只動 `transform` 與 `opacity`；開啟 220ms、收合 200ms；曲線 `cubic-bezier(.2,.8,.2,1)`。
- `will-change` 只在過場期間設置。
- 不做循環動畫。
- `@media (prefers-reduced-motion: reduce)`：`transition: none !important`；狀態仍切換；OPENING／CLOSING 立即完成，不等 `transitionend`。
- 禁止閃爍、脈動、發光、閃框（專案既有決定）。
- 超過 300ms 的過場不允許。

---

## 15. 檔案變更清單

**新增**
- `js/category-rules.js`：分類規則與排序，純函式。
- `js/router.js`：history 協調（§7）。
- `js/category.js`：分類 UI、狀態機、資料夾層渲染。
- `js/tools.js`：工具頁。
- `css/category.css`：資料夾樣式與動畫。
- `tests/fixtures/etf_203.json`：203 檔快照（code、name、div_category）。
- `tests/browser/category_test.py`、`tests/browser/router_test.py`。
- `PHASE3_PLAN.md`、`PHASE3_CHANGELOG.md`。

**修改**
- `index.html`：導覽 4 個按鈕；`#page-cat`、`#page-watch`、`#page-tools`；載入新檔；版本號 bump。
- `js/nav.js`：`switchPage` 改為 `navigate`；舊入口保留。
- `js/detail.js`：history 相關程式委派給 router（§6.3）；畫面與內容不改。
- `js/boot.js`：`_restoreCode` 改為 router 的 pending restore；`openFlow` 改為 `navigate(T)`；`showDataError` 的 `_tryRestoreDetail()` 改為 router 的一致性規則（§7.10）。
- `js/render.js`：`renderAll` 尾端通知分類與 router。
- `js/flow.js`：依 §9 修改觸發與容器；判斷與資料不改。
- `css/pages.css`：`#page-check` 相關選擇器逐條改寫（§9.3）。

**不改**
- `fetch_etf.py`、`scripts/*`、`data/*` 的產生方式。
- `js/search.js` 的比對規則。
- `js/rank.js` 的排行內容。

---

## 16. 測試與回歸

### 16.1 Phase 2 回歸測試政策（Codex finding 4）

**原則**：
- 行為斷言（使用者看得見的結果）全部保留。
- 只有「內部 history 格式」斷言可以隨 router 改造更新。
- 不得為了讓舊測試通過而保留兩套 history 實作。
- 修改前，先逐條列出每個斷言的分類（行為／內部），並附在實作 PR 中。

**初步分類（依現有測試的斷言內容）**：

| 測試檔 | 行為斷言（保留） | 內部 state 斷言（更新為 v2 等價） |
|---|---|---|
| `detail_ui_test.py` | 一次 Back 只產生一次 popstate（T8、T9、T10、T11、T13、T19 的 popstate 計數）；切換 ETF 不增加 entry（T12 的 `history.length`）；Detail 的所有內容、分頁、計算機斷言 | `_pendingPop == 0`（T8、T19）；`history.state.etfDetail`／`history.state.code`（T10、T12、T16）；`history.state === null` 形式的基底判斷（T10、T16） |
| `detail_history_fix_test.py` | 單一 popstate（F2）；離開後不還原 Detail（以 DOM 判斷，F1 的行為面） | `_restoreCode` 內部變數（F1）；`history.state.etfDetail`（約第 41 行） |
| `regression_test.py` | 分頁切換與原五頁行為 | 分頁切換清單需更新為新導覽（IA 變動的必要更新，不是放寬） |
| `detail_collapse_test.py`、`search_compact_test.py` | 全部為行為斷言 | 無 |

實作時每一條內部斷言改寫為 v2 等價斷言（例如 `history.state.stack` 中的 detail code），不刪除。

### 16.2 固定 fixture（203 檔）

| 編號 | 測試 | 通過條件 |
|---|---|---|
| FX-1 | 完整性 | 203 檔、代碼不重複、每檔恰一類 |
| FX-2 | 單一歸屬 | 8 類加總 = 203，任一檔不命中兩類 |
| FX-3 | 分布 | 與 §2.3 一致（**只在 fixture 上作為 assertion**） |
| FX-4 | 規則抽樣 | 0050→市值；00981A、00402A→主動；00878→高股息；00929→科技；00702、00771→海外；00850、0057、00682U→其他；00840B→債券；00894→高股息（備援）；00888→其他 |
| FX-5 | 怡恩確認的例外 | 科技＋高息→科技（00929、00943、00946、00962）；海外＋高息→海外（00702、00771、00882、00956、00963、00964）；AI 機器人、航太防衛→科技（00737、00965）；金融／工業／數位支付→主題（0055、00728、00909、00917、009822） |
| FX-6 | D-ESG 未決 | 00920、00923、009809 的分類依 §2.3 的 pending 預設；D-ESG 決定後，此測試的期望值同步更新 |

### 16.3 即時資料不變條件

| 編號 | 測試 |
|---|---|
| LV-1 | 每檔恰一類；加總 = `ETFS.length`；無遺漏 |
| LV-2 | UI 程式不含 ETF 代碼字串（代碼只在規則表與 fixture） |

### 16.4 列表行為

| 編號 | 測試 |
|---|---|
| LS-1 | 預設代碼 natural 排序（市值第一檔 0050） |
| LS-2 | 名稱排序（zh-Hant collator） |
| LS-3 | 查看更多：主動式 32 檔 10 → 20 → 30 → 32，按鈕消失 |
| LS-4 | 從 Detail 返回：排序、已展開數、捲動位置保留 |
| LS-5 | 從總覽重新開啟：重設為代碼、10 檔 |

### 16.5 Router 與 history

| 編號 | 情境 | 通過條件 |
|---|---|---|
| RT-1 | 總覽 → 資料夾 → Detail → Back → 資料夾 → Back → 總覽 | 每步狀態正確 |
| RT-2 | Browser Forward | Back 後 Forward 還原同一層與 ui |
| RT-3 | Detail reload | 還原資料夾＋Detail（資料可用後）；Back 不產生空白 entry |
| RT-4 | Detail 開著切換底部導覽 | Detail 與資料夾都關閉；導覽正確；history 深度正確 |
| RT-5 | Esc 只退一層 | 第一次只關 Detail；第二次才關資料夾 |
| RT-6 | 返回資料夾後排序與已展開數 | 保留 |
| RT-7 | 返回資料夾後捲動位置 | 保留 |
| RT-8 | 不產生重複基底 entry | `history.length` 只在 push 時增加；replaceState 與 normalize 不增加 |
| RT-9 | popstate 不呼叫 back／go | 以 CDP 監看：Browser Back 之後沒有額外的 back 或 go |
| RT-10 | busy 鎖 | 快速連按 Esc 兩次只退一層；busy 期間的點擊被忽略 |
| RT-11 | 切換 ETF 不累積層（Phase 2 語意） | Detail 開著切換 A→B→C，`history.length` 不變，一次 Back 直接離開 Detail |
| RT-12 | 工具子頁 → Back | 回工具列表 |
| RT-13 | Phase 2 格式的 state（`etfDetail`）載入 | normalize 為 v2；`history.length` 不變；Back 到基底不產生額外 entry（MG-1） |
| RT-14 | timeout 只取消 continuation，不釋放槽位；畫面與 history 不變；busy 清除，新操作改為 park |
| RT-15 | **traversal 未完成**：從 Detail 發出 `traverse(−1)`（deferred）→ timeout → 使用者 navigate(tools)（parked）→ release。舊 continuation（push flow）不執行；parked 依已確認位置執行，最終基底 tools |
| RT-16 | **核心**：同 RT-15，release 前：parked 不寫入 history（`history.length`、`history.state` 不變，仍是 Detail entry）。證明新導航沒有寫進假定的 k=0 位置（Rev.3.1 會這樣做） |
| RT-17 | orphan 完成發生在 parked 之後：不渲染 orphan 的 flow 狀態（畫面不閃回）；最終只顯示 parked 的結果 |
| RT-18 | hook 忠實度：`__routerDeferTraversal` 期間 `history.state`、`location`、`history.length` 不變、`__routerDeferredCount` = 1；release 後才有 popstate |
| RT-19 | **3 秒處理中（必測）**：①舊 traversal deferred；②`__routerForceTimeout()` → orphan，continuation 取消，槽位仍佔用；③新 navigation → parked；④`__routerForceProcessingMark()`（3 秒）→ 顯示處理中，驗證：`__routerTraversalCount` 不變（沒有第二個 traversal）、`history.length` 與 `history.state` 不變（沒有提前 push／replace）、`__routerInflightState()` 仍為 `orphan`、`parked` 仍保留；⑤`__routerReleaseTraversal()` → 真實 popstate 抵達 → `__routerCompletions` = 1，處理中清除，依新的 confirmed 執行 parked 一次（`__routerParkedRuns` = 1）；⑥最終目標正確，`history.back()`／`history.forward()` 順序正確；⑦舊 continuation 始終未執行 |
| RT-20 | RT-15 完成後，`history.back()` 與 `history.forward()` 結果與 history 實際順序一致；Back 路徑上沒有舊 Detail；Forward 殘留的舊 entry 行為與 Phase 2 相同（已記錄） |
| RT-21 | 無 back loop：每次 navigate 最多一次 `traverse`；RT-15 流程的 `__routerTraversalCount` 符合規劃（orphan 1 次，加上 parked 規劃的次數） |

### 16.6 Detail 導航與持股異動

| 編號 | 情境 | 通過條件 |
|---|---|---|
| NV-A | 首頁搜尋 → Detail → 查看持股異動 | 最終 `[folder(active,flow)]`、基底 cat；Back → 總覽；Forward → 持股異動；無 Detail 層 |
| NV-B | 工具子頁搜尋 → Detail → 查看持股異動 | 同上；基底由 tools 變 cat |
| NV-C | 其他分類資料夾 → Detail → 查看持股異動 | 同上；Back 回總覽而非 X |
| NV-D | 原本在主動式 → Detail → 查看持股異動 | 同上；Back 回總覽而非清單 |
| NV-E | 持股異動中按 Forward／Back 往返 | 狀態一致 |

### 16.7 首次失敗與一致性

| 編號 | 測試 |
|---|---|
| HF-1 | 首次失敗時 `history` 深度 = 畫面層數；Detail 顯示「資料暫時無法取得」 |
| HF-2 | 失敗後成功，內容補上，深度不變 |

### 16.8 資料更新

| 編號 | 測試 |
|---|---|
| DU-1 | 資料夾開著時資料更新：清單重排，排序與已展開數保留 |
| DU-2 | ETF 移類：從舊資料夾消失、進新資料夾 |
| DU-3 | ETF 消失：Detail 顯示「這檔目前不在清單中」，不自動關閉 |
| DU-4 | 更新失敗：分類與清單保留上次資料；banner 顯示時間 |

### 16.9 Responsive 與低高度

| 編號 | 測試 |
|---|---|
| LR-1～LR-9 | 見 §11.5 |
| LR-7～LR-9 | 20px 與 offsetTop：rect、可視區與 elementFromPoint 驗證；鍵盤關閉恢復（§11.6） |
| UI-1 | 8 個頁籤 rect 不重疊、≥ 44px、名稱完整 |
| UI-2 | 開啟與收合狀態正確；連點只開一次 |
| UI-3 | reduced-motion：過場時間為 0 |
| UI-4 | 無水平捲動 |

### 16.10 Flow

見 §9.5（FL-1～FL-8）。

### 16.11 全域搜尋與既有回歸

| 編號 | 測試 |
|---|---|
| SR-1 | 分類頁開著時搜尋 0050 仍可開 Detail |
| SR-2 | 下拉仍在資料夾之上 |
| SR-3 | 搜尋選取後 Back 回資料夾 |
| 既有 | `search_compact_test.py` 38、`detail_ui_test.py` 42、`detail_history_fix_test.py` 14、`regression_test.py` 14、`detail_collapse_test.py` 25。內部 state 斷言依 §16.1 更新；行為斷言不得放寬 |

### 16.12 靜態檢查

- 頂層名稱不重複（新前綴 `ct`、`rt`、`tl`）。
- 無 `type="module"`。
- `history.pushState`、`replaceState`、`history.back`、`history.go` 只出現在 `js/router.js`。

### 16.13 真機（怡恩；iPhone Chrome 為主，Safari、Samsung 抽測）

Coding 完成後依協定提供逐步操作。預計項目：分類頁 8 個頁籤可辨識；頁籤抽出；查看更多；排序；ETF → Detail → 返回；主動式持股異動選一檔；橫向看頁籤與清單；鍵盤開啟的低高度；工具頁進入與返回；減少動態效果；Detail「查看完整持股異動」。

### 16.14 需求追溯

| 來源 | 驗證位置 |
|---|---|
| Codex 1（Detail 語意） | §6、RT-11 |
| Codex 2（退層規則）＋ Rev.3.1～3.3 timeout 與 resync | §7.1、§7.6–§7.8、RT-9～RT-21 |
| Codex 3（導航順序） | §8、NV-A～NV-E |
| Codex 4（首次失敗與測試政策） | §7.10、§16.1、HF-1、HF-2 |
| Codex 5（低高度） | §11、LR-1～LR-9 |
| Codex 6（flow） | §9、FL-1～FL-8 |
| Codex 7（細部分布） | §2.2 |
| Codex 8（D-ESG、D14） | §3.4、§10.3、§18 |

---

## 17. Rev.2 → Rev.3 修訂對照

見第 0 節。

---

## 18. 開放決策

### 18.1 已採預設（不再詢問）

D11、D12、D13、D15、D16、D17（見第 0 節）。

### 18.2 仍 pending

| 編號 | 問題 | 證據與選項 | 現行預設 |
|---|---|---|---|
| **D-ESG-1** | 00923、009809、00920 的歸類 | 見 §3.4：證據指向 00923、009809 為策略型（其他），00920 為綠能主題或全球（海外）。Rev.2 的市值型與主題型歸類**與證據不一致**。最終數量可依 Product Owner 的 ESG 分類決策改變；Rev.2 驗證值只是待決前的預設，不是固定數量 | Rev.2 分布（市值 18、主題 19、其他 8） |
| **D-ESG-2** | 名稱來源（R-N1）：是否建立人工覆寫清單，讓規則看見官方全名 | 00920 的官方全名含「全球」；覆寫清單需附來源 | 不建立覆寫清單 |
| **D14** | 自選分頁內容（是否只顯示「尚未開放」） | Product Owner 決策 | 待決策；不實作 |

---

## 19. 風險

| 編號 | 風險 | 緩解 |
|---|---|---|
| R1 | Phase 2 history 改寫，回歸風險高 | §6、§16.1；Phase 2 行為斷言不得放寬 |
| R2 | 搜尋 76 檔與分類 22 檔並存 | 已由怡恩確認；§4.4 說明 |
| R3 | 規則需隨新 ETF 維護 | 未命中進其他；規則集中一檔 |
| R4 | 代號規則依賴命名慣例 | 與 CLAUDE.md 一致 |
| R5 | 名稱關鍵字誤判 | fixture 與 §3.4 的逐檔證據 |
| R6 | 360px 寬與鍵盤縮小高度 | §11、LR-2、LR-4、LR-5 |
| R7 | iOS Safari 的 history 行為差異 | 真機抽測（§16.13） |
| R8 | 持股異動 DOM 搬入資料夾，既有 onclick 與 id 失效 | §9.3、§9.4、FL-1 |
| R9 | `regression_test.py` 分頁切換項目需改 | §16.1，先給 Codex 看差異 |
| R-N1 | 規則只看簡稱，官方全名可能含不同地區或策略字眼 | §3.5、D-ESG-2 |
| R-N2 | 持股異動與中間畫面的真機表現 | §8.4；真機確認 |
| R-N3 | traversal 若永不抵達（理論上只在歷史入口不存在時發生），系統停在「處理中」；復原靠重新整理（從實際 history.state 還原） | §7.8；真機確認是否會發生 |

---

## 20. 完成條件

- §16 全部測試通過（新增測試與既有五組，內部 state 斷言依 §16.1 更新）。
- Codex 的 8 項 findings 皆有對應章節與測試。
- iPhone + Chrome 真機主要項目 PASS，由怡恩確認環境。
- D-ESG-1、D-ESG-2、D14 由怡恩決定。
- PHASE3_CHANGELOG.md、AI_HANDOFF.md 更新。
- 不 push，除非怡恩明確要求。

---

## 附錄 A：分類關鍵字（Rev.3）

| 類別 | 關鍵字 |
|---|---|
| 海外／區域 | 美國、日本、日經、日股、東證、印度、歐洲、中國、越南、恒生、韓、北美、標普、S&P、NASDAQ、納斯達克、那斯達克、道瓊、費城、上証、上證、滬深、深証、深100、中証500、MSCI A股、全球、亞太、海外、新興、世界、FANG、MAG7、US |
| 科技／半導體 | 科技、半導體、電子、晶圓、IC設計、AI、PCB、資安、5G、通訊 |
| 高股息 | 高股息、高息、股利、優息、高填息 |
| 市值型 | 0050、50、100、中型、中小、加權、藍籌、領袖、龍頭、MSCI台灣、台灣50、臺灣50 |
| 主題型 | 太空、稀土、元宇宙、機器人、生技、基因、綠能、電動車、智能車、未來車、車、潔淨、能源、電池、儲能、電力、數據、算力、航運、航太、防衛、數位、金融、工業 |
| 其他（策略） | ESG、公司治理、淨零 |

比對：名稱字串包含即命中，依 §3.1 順序；英文關鍵字大小寫不敏感。

---

## 附錄 B：分布與 D-ESG 替代

見 §2.3 與 §3.4。試算方式：以 `data/market.json` 的 code、name、div_category 與代號末碼，依 §3.1 的順序判斷；試算腳本只在 scratchpad，未納入 repo。

---

## 附錄 C：修正紀錄

- Rev.1 → Rev.2：ESG 規則、導覽 4 項、單一 router 的初版。
- Rev.2 → Rev.3：見第 0 節。

---

## 附錄 D：各分類成員（Rev.2 驗證值，Rev.3 維持）

以下由試算產生，與 4.1 的規則一致。

**市值型（18）**
0050 元大台灣50、0051 元大中型100、00690 兆豐藍籌30、00733 富邦臺灣中小、00912 中信臺灣智慧50、00921 兆豐龍頭等權重、00922 國泰台灣領袖50、00923 群益台ESG低碳50、006201 元大富櫃50、006203 元大MSCI台灣、006204 永豐臺灣加權、006208 富邦台50、009802 富邦旗艦50、009803 玉山市值動能50、009804 聯邦台精彩50、009808 華南永昌優選50、009809 富邦淨零ESG50、009816 凱基台灣TOP50

**高股息（22）**
- 名稱命中：0056 元大高股息、00701 國泰股利精選30、00713 台灣高息低波、00730 富邦臺灣優質高息、00731 復華富時高息低波、00878 國泰永續高息、00900 富邦特選高股息30、00907 永豐優息存股、00915 凱基優選高股息30、00918 大華優利高填息30、00919 群益台灣精選高息、00930 永豐ESG低碳高息、00932 兆豐永續高息等權、00934 中信成長高股息、00936 台新永續高息中小、00939 統一台灣高息動能、00940 元大台灣價值高息、00944 野村趨勢動能高息、00961 FT臺灣永續高息
- 人工標籤備援：00894 中信小資高價30、00905 FT臺灣SMART、00938 凱基優選30

**主動式（32）**
00400A 主動國泰動能高息、00401A 主動摩根台灣鑫收、00402A 主動安聯美國科技、00403A 統一台股升級50、00404A 主動聯博動能50、00405A 主動富邦台灣龍耀、00406A 主動中信台灣收益、00407A 主動凱基台灣、00408A 主動第一金優股息、00409A 主動復華全球50、00410A 主動永豐科技趨勢、00411A 主動統一前沿科技、00980A 主動野村臺灣優選、00981A 統一台股增長、00982A 主動群益台灣強棒、00983A 主動中信ARK創新、00984A 主動安聯台灣高息、00985A 主動野村台灣50、00986A 主動台新龍頭成長、00987A 主動台新優勢成長、00988A 主動統一全球創新、00989A 主動摩根美國科技、00990A 主動元大AI新經濟、00991A 主動復華未來50、00992A 主動群益科技創新、00993A 主動安聯台灣、00994A 主動第一金台股優、00995A 主動中信台灣卓越、00996A 主動兆豐台灣豐收、00997A 主動群益美國增長、00998A 主動復華金融股息、00999A 主動野村臺灣高息

**科技／半導體（20）**
0052 富邦科技、0053 元大電子、00737 國泰AI機器人、00875 國泰網路資安、00881 國泰台灣科技龍頭、00891 中信關鍵半導體、00892 富邦台灣半導體、00904 台新臺灣半導體30、00911 兆豐洲際半導體、00913 兆豐台灣晶圓製造、00927 群益半導體收益、00929 復華台灣科技優息、00935 野村臺灣新科技50、00941 中信上游半導體、00943 兆豐電子高息等權、00946 群益科技高息成長、00947 台新臺灣IC設計、00952 凱基台灣AI50、00962 台新AI優息動能、00965 元大航太防衛科技

**海外／區域（78）**
0061 元大寶滬深、00625K 富邦上証+R、00636 國泰中國A50、00636K 國泰中國A50+U、00639 富邦深100、00643 群益深証中小、00643K 群益深証中小+R、00645 富邦日本、00646 元大S&P500、00652 富邦印度、00657 國泰日經225、00657K 國泰日經225+U、00660 元大歐洲50、00661 元大日經225、00662 富邦NASDAQ、00668 國泰美國道瓊、00668K 國泰美國道瓊+U、00678 群益那斯達克生技、00700 富邦恒生國企、00702 國泰標普低波高息、00703 台新MSCI中國、00709 富邦歐洲、00714 群益道瓊美國地產、00717 富邦美國特別股、00735 國泰臺韓科技、00736 國泰新興市場、00739 元大MSCI A股、00752 中信中國50、00757 統一FANG+、00762 元大全球AI、00770 國泰北美科技、00771 元大US高息特別股、00783 富邦中証500、00830 國泰費城半導體、00851 台新全球AI、00858 永豐美國500大、00861 元大全球未來通訊、00876 元大全球5G、00877 復華中國5G、00882 中信中國高股息、00885 富邦越南、00886 永豐美國科技、00887 永豐中國科技50大、00916 國泰全球品牌50、00924 復華S&P500成長、00926 凱基全球菁英55、00949 復華日本龍頭、00951 台新日本半導體、00954 中信日本半導體、00955 中信日本商社、00956 中信日經高股息、00960 野村全球航運龍頭、00963 中信全球高股息、00964 中信亞太高股息、00971 野村美國研發龍頭、006205 富邦上証、006206 元大上證50、006207 復華滬深、009800 中信NASDAQ、009801 中信美國創新科技、009805 台新美國電力基建、009806 台新標普500、009807 台新標普科技精選、009810 玉山全球藍籌100、009811 統一美國50、009812 野村日本東證、009813 貝萊德標普卓越50、009814 富邦標普500、009815 大華美國MAG7+、009818 華南永昌NASDAQxT、009820 元大納斯達克精選、009823 群益S&P500、009824 群益美國科技巨頭、009825 聯邦美國金融創新、009826 貝萊德世界股票、009827 玉山未來全球算力、009828 中信台日韓PCB、009829 大華韓國KOSPI50

**主題型（19）**
0055 元大MSCI金融、00728 第一金工業30、00893 國泰智能電動車、00895 富邦未來車、00896 中信綠能及電動車、00897 富邦基因免疫生技、00898 國泰基因免疫革命、00899 FT潔淨能源、00901 永豐智能車供應鏈、00902 中信電池及儲能、00903 富邦元宇宙、00909 國泰數位支付服務、00910 第一金太空衛星、00917 中信特選金融、00920 富邦ESG綠色電力、009819 中信數據及電力、009821 野村稀土關鍵資源、009822 華南永昌未來金融、020032 元大綠能N

**債券（6）**
00840B 凱基IG精選15+、00980D 主動聯博投等入息、00982D 主動富邦動態入息、00983D 主動富邦複合收益、00984D 主動聯博全球非投、00985D 主動貝萊德優投等

**其他（8）**
- 策略型：00692 富邦公司治理、00850 元大ESG永續、00888 永豐台灣ESG、00928 中信上櫃ESG 30
- 期貨型：00682U 期元大美元指數、00693U 期街口S&P黃豆、00763U 期街口道瓊銅
- 名稱無對應（待查證）：0057 富邦摩台
