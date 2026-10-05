# PHASE 5 PLAN — 首頁入口大廳、Tools 同層切換、特殊 ETF 排除修補、Dark／Light 與全站收尾（Rev.4，待 Codex Plan Re-review／GPT Gate）

> 狀態：**Plan only，尚未 coding。**
> 依據：`AI_HANDOFF.md`「Phase 5 — GPT Gate 決策」1～13、GPT Gate／PO 對 Rev.1 D1～D6 的決定、Codex Rev.1 Plan Review（NEED FIX）、`CLAUDE.md`「產品決策與原因（長期保存）」、`IA_PROPOSAL.md`／`IA_PHASE1B.md` 的入口大廳與 Header 構想。
> 前置：Phase 2～4 VERIFIED / CLOSED（Phase 4 baseline `edb065d2`）。Phase 5 的回歸測試是**保護**，不重開舊 Phase。
> 原則：靜態 PWA、傳統 `<script>`、無 build、無框架；不新增第三方套件、不新增資料來源；文件配合程式，**不改 `calc_signal` 公式**。

## Rev.3 → Rev.4 修訂摘要（Codex Rev.3：只剩 Router finding）

- **Tools 分頁狀態與 Router history 分離**：撤回 Rev.3 的 `Router.setTool`（把 `tool div／rank` 寫進 E0 stack 會讓 Router 依 `stack.length` 多算一層返回）。Rev.4 中「成交量排行｜配息日曆」只是 Tools 頁面內的 UI 狀態，存在 Tools 模組記憶體與 `sessionStorage`，**不寫入 Router state、不新增 stack layer、不呼叫任何 history API**。Tools 仍只有一個真正的 base entry（base `tools`、stack `[]`）。§3.2～3.4、§3.6、§9、TL 測試、G2 依此改寫；新增 RT-T1～T5。
- ETF／ETN 解析與 Detail 試算遷移已由 Codex 判定 CLOSED，本輪未修改。

## Rev.2 → Rev.3 修訂摘要（Codex Rev.2 NEED FIX 三項）

1. **history 預期改以已封版 Router 實際行為為準**：底部導覽／首頁入口切換 base 時，Router 是 **replace 目前 entry（E0）**，不新增 entry，所以 Back 不會回首頁。§2.3、§3.2～3.4、HM-2、TL-1～5 依此改寫；`Router.setTool` 只改 Tools 自己的 entry，不改 base-page history。新增 §3.6 history 對照表。
2. **ETN 保留來源明確化**：證交所 ISIN 頁的 ETF 與 ETN 是兩個不同區段；現行解析是從「ETF」一路讀到頁尾才順帶收進 ETN。Rev.3 明確解析「ETF」「ETN」兩個區段（各到下一個區段標題為止），L／R／U 規則兩者都適用；新增 ETN positive fixture（020032）。
3. **Detail 配息試算遷移測試更正**：`#dtCalcOut` 改驗「單次可領」「N 張市值約」等金額隨張數連動；倒數（「N 天後」）改在配息資訊區驗證。不改 Phase 2 顯示文字。

## Rev.1 → Rev.2 修訂摘要

1. 補回完整 Phase 5 範圍（首頁整體重整、首頁兩大入口、Tools 同層切換、Header YouTube、舊 YouTube 入口移除、Dark／Light、visual tokens、UX closeout、跨裝置最終 QA）。
2. 已定規格寫入：首頁「查詢其他 ETF」（`lookupToday()`）直接淘汰；價格合理區標籤用「合理」；TOP 10 維持 `cur_vol`；前端 LAZY_WATCHLIST 實作後確認無引用即刪除，Python 三份不動；Light Mode 與色彩美化納入本 Phase；債券資料池維持現況。
3. Tools 改寫為正式 UX 規格（預設、切換、history、Detail 返回、排行定位保留）。
4. 特殊 ETF 排除：區分「未被 L／R／U 排除」與「最終進入資料池」；處理 `_isin_etf_pool()` 區段與 fallback 邊界；修正 00687C 期待；新增完整篩選鏈測試。
5. 舊功能退休改為 dependency migration（`ETFS`／`CALENDAR` 全域、`calc.js:36`、`lookup.js:86–87`、既有測試遷移）。
6. Active Flow 明列為保護功能；Phase 5 只統一直向分類導航。
7. 最終 QA 全覆蓋（Homepage、搜尋、分類、Detail、我的 ETF、Tools、Active Flow、Dark／Light、history、iPhone、Samsung）。

---

## 0. 範圍

| # | 項目 | 章節 |
|---|---|---|
| H1 | 首頁整體重整：入口大廳（不再是功能牆） | §2.1 |
| H2 | 首頁全站 ETF 搜尋（沿用 Header 全站搜尋為首頁主搜尋） | §2.2 |
| H3 | 「我想看看 ETF」→ 分類；「我已經有 ETF」→ 我的 ETF | §2.3 |
| H4 | 價格合理區 | §2.4 |
| H5 | 今日成交量 TOP 10 | §2.5 |
| H6 | 舊首頁單一 ETF 查詢（A-4 `lookupToday()`）淘汰 | §2.6、§6 |
| T1 | Tools：成交量排行｜配息日曆 同層切換 | §3 |
| T2 | 舊獨立配息計算機（B-1、`lookupCustom()`）淘汰 | §3.5、§6 |
| Y1 | Header 固定低調 YouTube 入口；首頁底部與 Tools 舊 YouTube 入口移除 | §4 |
| P1 | 資料池排除槓桿／反向／商品期貨（修補漏網），債券資料池維持現況 | §5 |
| V1 | Dark／Light Mode（切換與保存） | §7.1 |
| V2 | 全站 visual tokens／色彩美化 | §7.2 |
| V3 | 全站 UX closeout | §7.3 |
| F1 | 直向「主動式 ETF 持股異動」分類導航統一為「切換分類 ▼／▲」 | §8 |
| Q1 | 最終 iPhone Chrome／Samsung Chrome 跨裝置 QA | §10 |

**不在範圍**：`calc_signal` 公式（cheap 40%／2% 等維持）；`daily_check.py`／`intraday_notify.py`／`fetch_dividend_calendar.py` 的 LAZY_WATCHLIST；把既有規則排除的債券大量加回資料池；0057 歸類；Phase 2～4 已封版功能的行為（只做回歸保護與必要的入口遷移）；新增資料來源。

---

## 1. 現況（以程式為準）

| 項目 | 現況 | 位置 |
|---|---|---|
| Header | 標題、狀態徽章（`#statusBadge`）、↻（`reloadData()`）、全站搜尋（sticky） | `index.html` 21～40 |
| 首頁 | A-1 大盤 mood 卡 → A-2「值得留意 ETF」（大型 buy-card、LAZY 限制、fallback）→ A-3「今日熱門 ETF TOP 10」（不可點）→ A-4「查詢其他 ETF」（`lookupToday()`，查無時產生**假估算**）→ YouTube 入口卡 | `index.html` 60～97、`js/render.js`、`js/lookup.js` |
| 工具 | 兩張入口卡（配息工具、排行）＋ YouTube 連結；子頁 `page-div`（B-1 計算機＋B-2 日曆）、`page-rank`、`page-yt` 由 Router `tool` 層開啟（push） | `index.html` 252～330、`js/router.js` 19、152 |
| 計算機 | `js/calc.js`：**宣告全站 `ETFS`／`CALENDAR`**、`selETF`、`renderChips`／`selChip`／`calcUpdate`、`calc.js:36` 綁 `#sharesIn`、`renderSignalCard`（只供 `lookup.js` 使用） | `js/calc.js` |
| 查詢 | `js/lookup.js`：`lookupCustom()`、`lookupToday()`；`lookup.js:86–87` 在載入時綁 `#customCode`／`#todayCode` 的 keydown | `js/lookup.js` |
| 主題 | 只有深色；`:root` token 不完整，CSS／JS 中約 120 處寫死色值（含 `miniBars` 的 `#ff6b6b`／`#00e5a0`、`flow.js` treemap 的 `rgba(255,63,94,…)`／`rgba(0,200,122,…)`、排行頁標籤色） | `css/*.css`、`js/*.js` |
| 資料池 | `EXCLUDE_KW` 名稱關鍵字；`_isin_etf_pool()` 以 `html.find('ETF <B>')` 切段，**找不到時退回整頁**；漏網 02001L（正二）、00682U／00693U／00763U（「期」開頭） | `fetch_etf.py` 438～475 |
| 持股異動直向 | `ctlActive()` 限 `view === 'list'`，flow 時展開分類標籤列 | `js/category.js` 131 |

---

## 2. 首頁（入口大廳）

### 2.1 版面（H1）

由上而下（390px 直向）：

```
Header：ETF 存股雷達 [狀態]          [▶ YouTube] [☀/🌙] [↻]
        🔍 全站搜尋（sticky，既有）
─────────────────────────────────
A-1 今天大盤（既有 mood 卡，內容不改）
─────────────────────────────────
[ 我想看看 ETF        → ]   不知道從哪開始？從分類逛起
[ 我已經有 ETF        → ]   看我的 ETF、查配息
─────────────────────────────────
價格合理區（精簡列表，最多先 10 列）
─────────────────────────────────
今日成交量 TOP 10（精簡列表）
─────────────────────────────────
（頁尾警語，既有）
```

- 定位是「入口大廳」：首頁只放市場摘要、兩個入口、兩個精簡列表。**不放**單檔查詢、計算機、YouTube 卡、大型 ETF 卡片。
- 免責聲明（B6 警示條）與頁尾警語維持既有。

### 2.2 首頁全站 ETF 搜尋（H2）

- 首頁的主要搜尋就是 Header 既有的全站搜尋（Phase 1 已 VERIFIED，所有頁面共用、sticky），**不在首頁另外放第二個搜尋框**。
- 舊 A-4「查詢其他 ETF」移除後，首頁查詢一律走全站搜尋：查無就說查無（Phase 1 行為），不產生估算值。

### 2.3 兩大入口（H3）

- 「我想看看 ETF」→ `switchPage('cat')`：分類總覽（8 份文件夾，`data-state="overview"`）。
- 「我已經有 ETF」→ `switchPage('watch')`：我的 ETF。
- 兩個都是整塊 `<button>`（≥ 44px，建議 64px 以上），呼叫與底部導覽**完全相同**的 `switchPage()`／`Router.toBase()`。history 依現行封版 Router（§3.6）：首頁沒有開啟中的層時，切換 base 是 **replace 目前 entry**，不新增 entry；因此在分類／我的 ETF 按 Back **不會回到首頁**，而是離開到進站前的 entry（與目前底部導覽切頁一致）。不為入口按鈕另訂 history 規則。

### 2.4 價格合理區（H4，PO 決策固定）

```
TOP100 = ETFS 中 cur_vol > 0 且 price > 0，依 cur_vol 由高到低取前 100   ← 沿用現行
候選   = TOP100 中 signal ∈ {cheap, fair} 且 div_frequency !== '不配息'
排序   = cheap 在前、fair 在後；同狀態內 cur_vol 由高到低
```

- 標題「價格合理區」；說明「目前共有 X 檔 ETF 符合價格條件」，X＝全部符合檔數。
- 每列：代碼、名稱（過長省略號）、標籤「**便宜**」或「**合理**」（沿用 `sig-cheap`／`sig-fair` 配色；**不是**「合理✓」）。整列 `<button>`（≥ 44px），點擊 `openDetail(code)`。
- X ≤ 10 全部顯示；X > 10 預設前 10（依上述排序），「查看全部 X 檔」展開，展開後「收起」。展開狀態只存在記憶體；30 秒輪詢重繪時保留。
- 0 檔：只顯示「目前沒有 ETF 符合價格條件」；**不提供** fallback，不放入未符合 cheap／fair 的 ETF。
- **不使用 LAZY_WATCHLIST**；債券（`signal === 'bond'`）、hot、dear 自然不納入。
- 原說明行更正為現行公式的白話：「便宜：52 週位置偏低且低於 60MA 2% 以上｜合理：不超過 60MA 3%、未追熱｜僅含配息型、成交量前 100」。
- 移除 `renderBuyCard`、range 條、配息 pill、「為什麼今天沒有」長段說明。

### 2.5 今日成交量 TOP 10（H5）

- 標題「**今日成交量 TOP 10**」；演算法維持 TOP100 前 10（`cur_vol`），**不用 `heat`**。
- 每列整列 `<button>` → `openDetail(code)`；列內容（名次、代碼、名稱、現價、年殖利率、價格狀態）沿用，價格狀態標籤與價格合理區一致改為「合理」。

### 2.6 舊首頁單一 ETF 查詢淘汰（H6）

- 移除 A-4 區塊（`#todayCode`、`#todayMsg`、`#todayResult`）與 `lookupToday()`；**假估算路徑不修、不保留**。相依處理見 §6。

---

## 3. Tools：成交量排行｜配息日曆（T1）

### 3.1 版面

```
工具
[ 成交量排行 | 配息日曆 ]     ← 同層分段切換（segmented，role="tablist"）
───────────────────────────
（目前分頁的完整內容：排行 or 配息日曆）
```

- 一頁兩個同層分頁，**一次只顯示一個**；不上下堆疊兩個完整工具，也不只留入口卡。
- 「成交量排行」＝既有 `page-rank` 內容（含 `rankFind`「找 ETF／排名定位」、只定位不過濾、柱狀圖、特殊標籤、持股異動入口）。
- 「配息日曆」＝既有 B-2 近期配息日曆（`#calList`）。B-1 計算機移除（§3.5）。
- 不再有 YouTube 連結（§4）。

### 3.2 頁面結構與 Router 映射

- Tools 是**一個** base page：`page-rank` 改為 Tools 外殼，內含分段切換列（「成交量排行｜配息日曆」，`role="tablist"`）與兩個 pane——排行 pane（既有 `page-rank` 內容）與配息日曆 pane（原 `page-div` 的 B-2 `#calList`，搬入後 `page-div` 元素退役）。
- Router 映射：`BASE_PAGE.tools` → `page-rank`（Codex 已確認）。`TOOL_PAGE` 只留給既有帶 tool 的 intent（RT-12 使用）：`rank`、`div` 都映射到 `page-rank`；`yt` 隨 `page-yt` 退役（G1）。這只是頁面映射常數，Router 導航規則不改。
- 舊的工具入口卡頁（`page-tools`）退役。

### 3.3 分頁狀態：Tools UI state，不是 Router history layer

- 狀態保存：`js/tools.js`（新）的模組變數 `tab`（`'rank'` | `'div'`），並寫一份到 `sessionStorage`（`etfRadar.toolsTab`，try/catch；失敗只影響重新整理後的預設值）。
- 切換分頁＝只切換兩個 pane 的 `hidden` 與 tab 的 `aria-selected`。**不呼叫 Router、不寫 `history.state`、不呼叫 `pushState／replaceState／back／go`、不改 stack**。
- 進入 Tools（底部導覽「工具」）：維持既有 `switchPage('tools')` → `Router.toBase({ base: 'tools' })`（replace E0、stack `[]`）。畫面顯示 `tab` 的值（同一 session 內為上次的分頁；第一次或 storage 不可用時為「成交量排行」）。
- 重新整理：Router 依 entry 還原 base `tools`；Tools 模組依 `sessionStorage` 還原分頁。
- 相容入口：`switchPage('div')`／`switchPage('rank')`（`nav.js`）改為「`Router.toBase({ base: 'tools' })` 之後 `Tools.setTab(id)`」。原本會 push tool 層的 `toBase({ base: 'tools', tool })` 不再由 UI 呼叫（intent 本身不改，RT-12 照驗）。
- **不新增任何 Router API**（撤回 Rev.3 的 `Router.setTool`）。

### 為何不影響 Router 的返回層數

Router 以 `confirmed.stack` 與 `commonPrefix` 計算 traversal 層數（`k = c.stack.length − p`）。Tools 分頁狀態從不進入 `confirmed`，所以：

- Tools 中 stack 永遠是 `[]`（開 Detail 時為 `[detail]`），與分頁無關 → `k` 的計算與 Phase 4 完全相同。
- 底部導覽離開 Tools：stack `[]` → `k = 0`，replace E0，不 traverse（與其他 base 一致）；Detail 開著時 `k = 1`，與其他 base 開 Detail 時相同。
- 不會因為切過分頁而多退一層或離站。

### 3.4 從排行開 ETF Detail 後返回

- 點排行列 → `openDetail(code)`：既有 `intentDetail`，在 Tools 目前的 entry 上 **push** 一個 detail 層。
- ✕／Back／Esc → 關閉 Detail（回到 push 前的 Tools entry，分頁不變）；Detail 是覆蓋面板，window 捲動位置自然保留；`rankFind` 值與定位結果保留；30 秒輪詢的 `renderRank` 仍套用定位。
- Forward → 再開同一檔 Detail。
- 從排行「持股異動 ›」→ Flow：封版語意不變（RT-22：Back 回分類總覽）。

### 3.6 history 對照（依現行封版 Router）

| 路徑 | 寫入 history | Router stack | Back | Forward |
|---|---|---|---|---|
| 首頁 → 分類／我的 ETF（入口按鈕或底部導覽；首頁無開啟中的層） | replace 目前 entry，`history.length` 不變 | `[]` | 離開到進站前的 entry（不回首頁） | 不適用 |
| 任意 base → 底部導覽「工具」 | replace E0 為 `tools`，`history.length` 不變 | `[]` | 同上 | 不適用 |
| Tools 分頁切換（排行 ⇄ 配息日曆） | **無**（不呼叫任何 history API） | 仍為 `[]` | 與未切換時相同 | 與未切換時相同 |
| 底部導覽離開 Tools（不論切過幾次分頁） | replace E0，`history.length` 不變、traversal 0 次 | `[]` | 離開到進站前的 entry（與其他 base 相同） | 不適用 |
| Tools（任一分頁）→ Detail → 返回 | push detail；關閉時 back 一層 | `[detail]` → `[]` | 關閉 Detail，回到原分頁；排行捲動、`rankFind` 值與定位保留 | 再開同一檔 Detail，分頁不變 |
| Tools 排行「持股異動 ›」→ Flow | 既有 `intentBase(flow)`：stack `[]` 時 replace E0 為 `cat` 再 push folder（traversal 0 次） | `[folder(active, flow)]` | 回分類總覽（RT-22） | 依既有規則 |
| Tools → Detail →「查看完整持股異動」→ Flow | 既有規則（與 FL-4 相同：traversal 1 次回 E0 後 replace＋push） | `[folder(active, flow)]` | 回分類總覽（FL-4） | 依既有規則 |

## 4. Header YouTube 與舊入口移除（Y1）

- Header 右側新增低調固定 YouTube 入口：小圖示按鈕（▶ 或 YouTube 圖示，≥ 44×44，`aria-label="金流黑盒子 YouTube 頻道"`），與主題切換、↻ 並排；**不做大型宣傳 Banner**。
- 點擊：以新分頁開啟頻道 `https://www.youtube.com/@CashFlowDataRecorder`（`target="_blank" rel="noopener"`），不經 Router。
- 不影響 `#statusBadge` 與 `reloadData()`（版面改為 flex 右側按鈕群，狀態徽章位置不變）；低高度／鍵盤（`gs-ckm`）時 Header 行為沿用。
- 移除：首頁底部 YouTube 入口卡（`index.html` 96）、工具頁 YouTube 連結（258）。
- `page-yt`（頻道介紹頁）移除後已無任何入口 → 一併退役（含 `TOOL_PAGE.yt`、`switchPage('yt')` 相容入口改為開啟同一外部連結）。見 §11 G1。

---

## 5. 資料池排除槓桿／反向／商品期貨（P1）

### 5.1 規則

**最終資料池＝下列篩選鏈依序通過者**（任一步排除即不進池）：

```
① ISIN 解析「ETF」與「ETN」兩個區段（strMode=2 上市、4 上櫃；各自到下一個區段標題為止）
② 代號必須以 0 開頭；排除 T 結尾（受益憑證）               ← 既有
③ 【新】代號字尾 L（槓桿）／R（反向）／U（期貨・商品）→ 排除
④ EXCLUDE_KW 名稱關鍵字 → 排除（既有，補「正二」「反一」）
⑤ build_pool：合併 CURATED、上櫃碼補 TWO_CODES               ← 既有
⑥ fetch 迴圈：yfinance 資料不足（< 5 筆）→ 一般 ETF 略過       ← 既有
⑦ fetch 迴圈：非精選且 avg_vol < 100 → 略過                    ← 既有
```

- **「沒有被③排除」≠「一定進入最終資料池」**：之後仍可能被④⑥⑦排除。例：`00687C 國泰20年美債+櫃U` 不被③排除，但名稱含「債」，被④排除 → **不在最終池**（維持現況）。
- ③ 依 2026-10-05 實測 ISIN ETF 區段 382 個代碼：字尾 L／R／U 與「名稱為槓桿／反向／期貨」完全一致（兩邊各 0 例外）。字尾 `A`（主動）、`B`／`D`（債券）、`K`（外幣級別，如 00625K 富邦上証+R 的「+R」是人民幣）、`C`、無字尾者**不受③影響**。
- **債券資料池維持現況**：④中的「債、公債、公司債、高收益」不動；本 Phase 不大量加回既有規則排除的債券。
- **ETN 的保留來源**：ISIN 頁的區段標題（2026-10-05 實測）——上市：股票／上市認購(售)權證／特別股／創新板／**ETF**／**ETN**／臺灣存託憑證(TDR)／受益證券-不動產投資信託；上櫃：上櫃認購(售)權證／**ETF**／**ETN**／股票／特別股／受益證券-資產基礎證券。0050、00631L、00679B、00687C、00980D 在「ETF」區段；020032 元大綠能N、02001L 富邦蘋果正二N 在「ETN」區段。**現行程式是從「ETF」一路讀到頁尾，才順帶收進 ETN**（其後的 TDR 被「0 開頭」、受益證券被「T 結尾」濾掉；上櫃 ETN 之後的股票代碼不以 0 開頭）。Rev.3 改為明確解析 ETF 與 ETN 兩個區段，ETN 的保留不再依賴這個副作用。
- ③④對 ETN 一樣適用：02001L（字尾 L）被排除；020032 等非槓反 ETN（字尾為數字）不受③影響，通過④⑥⑦後照常進池。目前 market.json 中的 ETN 只有 020032；其餘 ETN 因 avg_vol < 100 等既有條件不在最終池，維持現況。
- 同一套③④套用於：ISIN 即時抓取、`etf_pool_cache.json` fallback 讀取、`CURATED`（防禦性；目前精選池無 L／R／U）。

### 5.2 `_isin_etf_pool()` 區段與 fallback 邊界

- 現況 `html.find('ETF <B>')` 找不到時退回**整頁**解析——整頁含權證等商品，配合「代號以 0 開頭」可能誤收；找得到時則從 ETF 讀到頁尾（因此順帶收進 ETN 及其後區段）。
- 改為：
  - 以區段標題列（`<td … colspan=7 ><B> 名稱 <B>`）切出 **「ETF」** 與 **「ETN」** 兩段，各自只取到下一個區段標題列為止；其他區段（權證、股票、TDR、受益證券等）一律不讀。
  - **找不到「ETF」區段 → 該市場別視為抓取失敗**（印 `[POOL]` 警告），不退回整頁；兩個市場別都失敗才走既有 `etf_pool_cache.json` fallback。
  - **找不到「ETN」區段 → 該市場別沒有 ETN**（印警告），ETF 照常收取；不退回整頁。
  - 每列讀 CFI 欄位做健全性檢查：ETF 區段應為 `CE…`（實測 `CEOG*`／`CEOI*`／`CEOJ*`），ETN 區段應為 `CM…`（實測 `CMXXXU`）；不符者印警告並略過。

### 5.3 生效與連帶影響

- 修改 `fetch_etf.py` 後需重跑 `fetch.yml` → `update-data.yml`（CLAUDE.md 兩階段架構）。何時觸發由 PO 決定。
- 預期移除：00682U、00693U、00763U（目前在「其他」）。「其他」由 4 檔變 1 檔（0057）。
- 已收藏這些 ETF 的使用者：我的 ETF 依 Phase 4 §2.4 顯示「目前無法取得這檔的資料」（既有行為，不自動刪除）。
- `category_test.py`「UI band counts match fixture distribution」目前比對 **live vs fixture**，資料池變動後會失效 → 改比 `catGroup(ETFS)` 的 live 計數；FX-*（以 fixture 驗分類規則）不變。
- `daily_check.py` 新進 TOP 100 偵測可能因池子變動觸發一次通知：屬預期，記錄於 handoff。

---

## 6. 舊功能退休的 dependency migration（H6、T2）

| 相依 | 現況 | 處理 |
|---|---|---|
| 全站 `ETFS`／`CALENDAR` | 宣告在 `js/calc.js` 第 8～9 行；`render.js`、`category.js`、`detail.js`、`format.js`、`watch.js`、`rank.js` 等都讀它 | **先**移到新檔 `js/state.js`（只放 `let ETFS = []; let CALENDAR = [];`），載入位置與原 `calc.js` 相同（`format.js` 之前），之後才移除 `calc.js` |
| `selETF` | `calc.js:10`；`render.js` 的 `selETF = …`、`renderChips()`、`calcUpdate()` | 全部移除 |
| `calc.js:36` | 載入時 `document.getElementById('sharesIn').addEventListener(...)`；`#sharesIn` 移除後會丟 TypeError、中斷後續 script | 隨計算機移除；`calc.js` 整檔退役（`renderSignalCard` 只供 `lookup.js`，一併移除） |
| `lookup.js:86–87` | 載入時綁 `#customCode`／`#todayCode` keydown；輸入框移除後會丟 TypeError | `lookupCustom()`、`lookupToday()` 都淘汰 → `lookup.js` 整檔退役 |
| `index.html` script | `calc.js`、`lookup.js` 的 `<script>` | 移除；新增 `state.js` |
| `.buy-card`、`.etf-chip`、`.custom-*`、`.calc-*` CSS | 首頁 buy-card、計算機 | 確認 Detail 未使用者才移除（`#dtCalcOut` 使用的 `.calc-row` 等保留） |
| `archived-check.js` | 已下架的健診頁（template 封存） | 實作時確認是否引用 `selETF`／`renderSignalCard`；若有，維持封存不載入或改用 `state.js`，不得造成載入錯誤 |
| `js/config.js` LAZY_WATCHLIST | 只剩 `render.js` A-2 與 fallback 引用 | 首頁改版後 `grep` 確認無任何 JS 引用 → 刪除前端常數（`config.js` 若因此為空則退役）；Python 三份不動 |

**驗收**：頁面載入無任何未捕捉例外（含首次載入、資料失敗、`gs-ckm`）；`ETFS`／`CALENDAR` 在所有使用者之前已宣告。

### 6.1 既有測試的遷移（遷移到新的正式入口，不是刪除）

| 測試 | 現在驗的 | 遷移後驗的 |
|---|---|---|
| `regression_test.py`「R switch page div／yt」 | `switchPage('div')`／`('yt')` 開子頁 | `switchPage('div')` → 工具頁且分頁＝配息日曆、`#calList` 有內容；`yt` 改驗 Header YouTube 連結存在、`href` 正確、`target="_blank"` |
| `regression_test.py`「R page-div chip calc uses 0056」 | B-1 `selChip('0056')`、`#calcOut` 含「天後」 | 改驗 **Detail 0056 配息分頁**的張數試算（同一使用者需求的正式入口）：`#dtSharesIn` 依序設 1、7 → `#dtCalcOut` 的「單次可領」金額＝`amount × 張數 × 1000`、「N 張市值約」＝`price × 張數 × 1000`（期望值以當下 ETF 資料計算，並驗 1 → 7 兩者等比例變化）；`yld_verified` 且 `yld > 0` 時「預估年化領回」同樣連動。**不要求 `#dtCalcOut` 出現「天後」**（Phase 2 試算本來就不顯示倒數）。倒數另於配息資訊區驗：除息日在未來時，配息資訊的日期文字含「（N 天後）」或「（今日）」（`_dtDivHtml` 既有輸出）。不修改 Detail 顯示文字或 UX |
| `regression_test.py`「R rank find 0050」 | 排行定位 | 在工具「成交量排行」分頁執行，期望不變 |
| `detail_ui_test.py` T7「selETF untouched」 | Detail 計算不污染 B-1 的 `selETF` | `selETF` 已不存在 → 改驗 Detail 計算不影響其他狀態：`detailOnMarketUpdate()` 後 `#dtSharesIn` 保留、`Router.state()` 不變（T7 原有的「shares kept」「7 張市值」兩項保留不變） |
| `detail_ui_test.py` T11「nav opened page-div」 | Detail 開著時切到配息頁 | `switchPage('div')` → 工具頁配息日曆分頁；Detail 關閉、單一 popstate 的斷言保留 |
| `category_test.py`「TOOLS card opens 配息 subpage／back returns to tools list」 | 入口卡 → 子頁（push tool 層）→ Back 回列表 | 入口卡已退役 → 改驗：底部導覽「工具」顯示排行、`history.length` 不變；切到配息日曆 `history.length` 仍不變、stack 仍為 `[]`（§3.3：分頁狀態不進 Router）；在配息日曆開 Detail → Back 關 Detail 後仍在配息日曆 |
| `search_compact_test.py` X2「stays on requested page」 | 延遲搜尋中 `switchPage('div')` | 期望改為工具頁配息日曆分頁；「不開 Detail」斷言保留 |

---

## 7. Dark／Light、visual tokens、UX closeout

### 7.1 切換方式與狀態保存（V1）

- Header 右側主題按鈕（☀／🌙，≥ 44×44，`aria-label` 依狀態「切換為淺色模式／深色模式」），與 YouTube、↻ 並排。
- 初始：localStorage `etfRadar.theme`（`'dark'`／`'light'`）有值則採用；沒有則依 `prefers-color-scheme`。
- 按下切換並寫入 localStorage（try/catch；讀寫失敗時只在本次頁面生效，不報錯）。
- 套用：`<html data-theme="dark|light">`。在 `<head>` 內以極短的行內 script 於 CSS 前設定，避免閃一下錯誤主題。
- 未手動選擇時，系統主題改變會跟著變；手動選擇後以選擇為準。

### 7.2 共用 visual tokens（V2）

- 在 `css/base.css` 建立完整 token，`:root`（＝dark）與 `[data-theme="light"]` 各一組：
  - 背景（`--bg`）、卡片（`--card`、`--card2`）、邊框（`--border`）、主文字（`--bright`）、次要文字（`--dim`）、品牌色（`--brand`）、提醒（`--fair`，B6 警示條）、價格狀態（`--cheap`、`--fair`、`--hot`、`--dear`、`--bond`）、漲跌（`--up`、`--dn`、0／缺值中性）、陰影、海外標示（`--sea`）。
- **台股漲紅跌綠語意不變**：兩種主題都是 `--up`＝紅、`--dn`＝綠、0＝中性、缺值＝灰。Light 用加深版維持可讀（起點參考 `IA_PROPOSAL.md`：約 `#D4494C`／`#1E8F6A`，實作時以對比量測定案）。
- **寫死色值盤點與替換**：CSS／JS 約 120 處逐一改用 token。包含：
  - `miniBars` 的 `#ff6b6b`／`#00e5a0` → `var(--up)`／`var(--dn)`（0 中性、缺值灰的 Phase 4 D1 規則不變）。
  - 排行頁 `retClr`、`getEtfTag` 標籤色、首頁與 Header 的 inline style 色值。
  - **Active Flow**：`flow.js` treemap 的 `rgba(255,63,94,…)`／`rgba(0,200,122,…)` 改為由 `--up`／`--dn` 換算（保留依面積調透明度），海外清單 `var(--up)`／`var(--dn)` 不變——**紅＝加碼、綠＝減碼的金融語意在兩種主題都不變**。
  - Phase 4 拖曳亮起（`.wc.lifting`）、我的 ETF 卡片、Toast、移動選單。
- **可讀性**：主文字、次要文字、價格狀態標籤、漲跌數字、B6 警示條在兩種主題對背景的對比度量測並記錄（目標：正文 ≥ 4.5:1，大字與圖形 ≥ 3:1）；不達標者調整 token，不改資訊層級。
- **不因換主題破壞資訊層級**：主內容 → 分類／導航 → 警示語的層級（Phase 3／B6 原則）在兩種主題維持；Phase 3 文件夾堆疊與陰影在 Light 下仍有層次。

### 7.3 全站 UX closeout（V3）

只做收尾一致性，不新增功能：

- 觸控目標 ≥ 44px（新增元件、Header 按鈕群、兩大入口、列表列）。
- 標籤文字統一：價格狀態全站「便宜／合理／過熱／偏貴／債券型」（「合理✓」全站改為「合理」，含 Detail、分類列、我的 ETF、成交量排行）。
- 空狀態文案一致（價格合理區、我的 ETF、搜尋查無）。
- 移除退役功能留下的死碼與 CSS（§6），`grep` 確認無殘留引用。
- `prefers-reduced-motion` 在新元件（分段切換、展開／收起）一樣生效。
- `CLAUDE.md`「頁面區塊代號」依新首頁與 Tools 更新；資料池排除規則改寫為篩選鏈；主題 token 說明。

---

## 8. 直向「主動式 ETF 持股異動」分類導航統一（F1）

### 8.1 保護範圍（不可弱化、刪除或替代）

持股異動本身、紅＝加碼／綠＝減碼視覺、treemap、海外無報價增減股數清單、ETF chips 選擇、`fetched=false`／無異動／未更新等狀態語意、Detail →「查看完整持股異動」→ Back 回分類總覽（RT-22）、FD-1～6 重繪、FL-1～7。**`flow.js` 不改邏輯**（只做 §7.2 的色值 token 化，語意不變）。

### 8.2 只改直向分類導航

- 把 `cat-ctl` 拆成兩層：
  - **切換分類 UI 層**（新 class `cat-sw`）：標題列 ←、「切換分類 ▼／▲」、inside 時收起 `#catStrip`、標題列單列化——直向＋非鍵盤時，**清單與持股異動都套用**。
  - **清單專屬層**（保留 `cat-ctl`）：查看更多移入清單底部、隱藏 `#catFoot`、清單 fit／tight3、LR-4 fallback——只在 `view === 'list'`。
- `stripOpen` 仍只存在 Category，不寫 Router。
- **橫向版維持既有直接分類標籤**（不套 `cat-sw`）；鍵盤（`gs-ckm`）路徑不變。
- 標籤列收起後 flow 可用高度變大，treemap 依容器重畫（由 FD-1～6 與新增測試驗證）。
- Phase 3 category_test 中「flow 時次要標籤列顯示」的斷言改為新規格（直向 inside 收起；橫向仍顯示）。

---

## 9. 檔案與實作順序

| 順序 | 內容 | 主要檔案 |
|---|---|---|
| 1 | P1 資料池排除與區段解析＋Python 測試 | `fetch_etf.py`、`tests/test_pool.py`（新） |
| 2 | §6 dependency migration（`state.js`、退役 `calc.js`／`lookup.js`、測試遷移） | `index.html`、`js/state.js`（新）、`js/render.js`、tests |
| 3 | H1～H6 首頁入口大廳、價格合理區、成交量 TOP 10 | `index.html`、`js/render.js`、`css/pages.css` |
| 4 | T1 Tools 同層切換（分頁狀態在 Tools 模組，不進 Router） | `index.html`、`js/tools.js`（新）、`js/nav.js`、`js/router.js`（僅 `BASE_PAGE`／`TOOL_PAGE` 映射常數）、`js/rank.js` |
| 5 | Y1 Header YouTube、舊入口與 `page-yt` 退役 | `index.html`、`css/base.css`、`js/router.js`（`TOOL_PAGE`） |
| 6 | F1 持股異動直向切換分類 | `js/category.js`、`css/category.css` |
| 7 | V1～V2 主題切換與 token 化（含 Active Flow 色值） | `index.html`、`css/*.css`、`js/format.js`、`js/rank.js`、`js/flow.js`（僅色值） |
| 8 | V3 UX closeout、文件 | 全站、`CLAUDE.md` |
| 9 | 全回歸 → Codex Code Review → 真機（§10.3） | |

---

## 10. 測試計畫

### 10.1 新增自動測試

**Python（`tests/test_pool.py`，以存下的 ISIN HTML 片段為 fixture，不連網）**

| 編號 | 項目 | 通過條件 |
|---|---|---|
| EX-1 | 字尾規則 | 00631L、00632R、00682U、00693U、00763U、02001L 被③排除；0050、00981A、00980D、00625K、00687C **不被③排除**（00687C 之後由④排除，見 EX-4） |
| EX-2 | A／B／D／K 不誤殺 | 名稱不含關鍵字的 A／B／D／K 字尾 ETF 通過③④ |
| EX-3 | 關鍵字第二道防線 | 名稱含「正二」「反一」者被④排除（即使字尾不是 L／R） |
| EX-4 | 完整篩選鏈 | fixture 走 ①～⑤：00687C、名稱含「債」的 B 字尾 ETF 不在結果（維持現況）；6 檔現有債券（00840B、00980D、00982D～00985D）在結果 |
| EX-9 | ETN positive | fixture 的「ETN」區段 020032 元大綠能N（CFI `CMXXXU`）通過①～⑤並出現在結果；02001L 富邦蘋果正二N 被③排除 |
| EX-10 | 兩區段各自邊界 | ETN 區段之後的 TDR／受益證券／股票資料列不被收入；ETF 區段只到 ETN 標題為止 |
| EX-11 | 缺 ETN 區段 | 只有 ETF 區段時，ETF 照常收取、ETN 為空並印警告，不退回整頁 |
| EX-5 | 區段邊界 | ETF 區段之後的其他區段資料列不被收入；權證樣本（CFI `RW…`）不被收入 |
| EX-6 | 找不到 ETF 區段 | 該市場別回傳空並印警告，**不**退回整頁解析（即使頁面有 ETN 區段也一樣視為失敗） |
| EX-7 | cache fallback | `etf_pool_cache.json` 含 L／R／U 或關鍵字項目時，讀取後被排除 |
| EX-8 | CURATED | 精選池若出現 L／R／U 也被排除（防禦性） |

**Browser（`tests/browser/home_test.py`、`tools_test.py`、`theme_test.py`，fixture 注入 `ETFS` 後呼叫 `renderAll`）**

| 編號 | 項目 | 通過條件 |
|---|---|---|
| HM-1 | 首頁結構 | 依序為 A-1、兩大入口、價格合理區、今日成交量 TOP 10；無 A-4、無 YouTube 卡、無 `.buy-card` |
| HM-2 | 入口 | 「我想看看 ETF」→ 分類總覽、「我已經有 ETF」→ 我的 ETF；與底部導覽相同：`history.length` 不變、目前 entry 的 base 變為 `cat`／`watch`（replace E0）；**不期望** Back 回首頁 |
| HM-3 | 首頁搜尋 | Header 全站搜尋在首頁可用；首頁無第二個搜尋框；查無代碼顯示查無、不出現估算值 |
| PZ-1～13 | 價格合理區 | Rev.1 的 PZ-1～13 全數保留（母體、狀態、不配息、不用 LAZY、排序、計數、≤10、>10 展開／收起、輪詢保留、0 檔、整列點擊、精簡列、配色）；標籤文字為「便宜」「合理」 |
| TV-1～3 | 成交量 TOP 10 | 標題、`cur_vol` 演算法（heat 最高者不一定在內）、整列點擊開 Detail 並返回首頁 |
| TL-1 | Tools 預設 | 底部導覽「工具」→ 顯示成交量排行；`history.length` 不變；`Router.state()`＝base `tools`、stack `[]` |
| TL-2 | 切換不碰 history | 排行 → 配息日曆 → 排行：`history.length`、`history.state`（JSON 比對）、`Router.state()` 三者都不變；只有 pane 顯示與 `aria-selected` 改變 |
| TL-3 | 不寫 Router | 切換分頁期間 `history.pushState／replaceState／back／go` 呼叫次數為 0（spy）；`Router` 物件上沒有新增 API |
| TL-4 | 重新整理 | 配息日曆分頁重新整理後仍在配息日曆（`sessionStorage`）；`sessionStorage` 不可用時重新整理回到排行、無例外 |
| TL-5 | 排行 → Detail → 返回 | 定位 0050 並捲到中段 → 開 Detail（`history.length` +1、stack `[detail]`）→ ✕／Back 關閉（stack `[]`）→ 仍在排行分頁、捲動位置不變、`rankFind` 值與定位結果保留；Forward 再開同一檔 Detail |
| TL-6 | 排行定位功能 | `rankFind` 只定位不過濾（100 列都在）、訊息正確 |
| TL-7 | 相容入口 | `switchPage('div')`／`('rank')` 開對應分頁；`history.length` 不變、stack `[]`（不走帶 tool 的 push intent） |
| RT-T1 | 分頁切換不改 depth | Tools 預設排行 → 切配息日曆 → 切回排行：`Router.state().stack.length` 始終 0、`history.length` 不變、Router `stats.traversals` 不變 |
| RT-T2 | 切過分頁後以底部導覽離開 | 切到配息日曆（再切回、再切去，共 3 次）→ 底部導覽「首頁」與「分類」：traversal 0 次、`history.length` 不變、`location.href` 不變（未離站）、目標頁正確顯示 |
| RT-T3 | Detail 往返保留分頁 | 配息日曆分頁 → `openDetail('0056')` → Back：回到配息日曆分頁；排行分頁同樣測試並驗捲動與 `rankFind` 保留（同 TL-5） |
| RT-T4 | 切過分頁後走 Flow 路徑 | 切換分頁數次後：(a) 排行「持股異動 ›」→ traversal 0 次、stack＝`[folder(active, flow)]`、Back 回分類總覽（同 RT-22）；(b) 開 Detail →「查看完整持股異動」→ traversal 1 次（與未切換分頁時相同）、Back 回分類總覽（同 FL-4）。兩者的 traversal 次數與「未切過分頁」的對照組相同 |
| RT-T5 | R1～R8 | 切換分頁期間：popstate 處理不呼叫 back／go（R1）；切換分頁不受 inflight 影響且不寫 history（R5、R8）；Detail Back → Forward 再開同一檔且分頁不變；既有 router_test 64 項全數 PASS |
| TL-8 | 無 YouTube、無計算機 | 工具頁無 YouTube 連結、無 B-1 元素 |
| YT-1 | Header YouTube | 圖示存在、≥ 44×44、`href`＝頻道、`target="_blank"`、`rel` 含 `noopener`；不改變 `#statusBadge`／↻ 行為 |
| YT-2 | 舊入口移除 | 首頁、工具頁無 YouTube 連結；`page-yt` 不存在；`switchPage('yt')` 不丟例外 |
| MG-1 | 載入無例外 | 首次載入、資料失敗、`gs-ckm` 時無未捕捉例外；`ETFS`／`CALENDAR` 可用 |
| MG-2 | Detail 計算保留 | Detail 配息分頁張數試算可用；刷新後輸入保留（取代舊 selETF 測試） |
| MG-3 | 無殘留引用 | `selETF`、`renderChips`、`lookupToday`、`lookupCustom`、`LAZY_WATCHLIST` 在前端皆為 `undefined` |
| TH-1 | 初始主題 | 無儲存值時依 `prefers-color-scheme`（以 CDP `Emulation.setEmulatedMedia` 切換 dark／light 驗證） |
| TH-2 | 切換與保存 | 按主題鈕 → `data-theme` 改變、localStorage 寫入；重新整理後維持 |
| TH-3 | storage 失敗 | `localStorage` 丟例外時切換仍生效、無例外 |
| TH-4 | 漲紅跌綠（兩主題） | 兩種主題下：我的 ETF 今日漲跌、miniBars、排行近一年報酬的 computed color 屬紅系＝漲、綠系＝跌、0 中性、缺值灰；反向守衛（上漲不是綠） |
| TH-5 | Active Flow（兩主題） | treemap 加碼格紅系、減碼格綠系；海外清單正值紅、負值綠；兩主題都成立 |
| TH-6 | 可讀性 | 主文字、次要文字、價格狀態標籤、漲跌數字、B6 警示條在兩主題的對比度達標（記錄數值） |
| TH-7 | 資訊層級 | 兩主題下 Phase 3 文件夾堆疊陰影存在、B6 警示條為低調提示（字級與底色層級不變） |
| SW-1～6 | 持股異動直向切換分類 | 直向 inside 收起標籤列並顯示「切換分類 ▼」；doorway 展開；切到其他分類進清單；flow 無清單專屬行為；treemap 重畫不溢出；**橫向維持直接分類標籤** |

### 10.2 既有測試（回歸保護）

- 全部回歸：router 64、search_compact 38、detail_ui 42、detail_history_fix 14、regression 14、detail_collapse 25、detail_state 42、category 250（＋1 DEFER）、watch 149（＋4 DEFER）。
- **Active Flow 保護不可刪除／弱化**：category FD-1～6、watch FL-1～7（兩主題下的色值斷言改為「紅系／綠系」判斷，仍以 computed color 驗證）。
- **RT-12**（`Router.toBase({ base: 'tools', tool: 'rank' })` push、Back 後 stack 長度 0）：Router 行為不變、繼續驗；唯一更新的是頁面期望——Back 後原本驗 `page-tools`（入口卡頁，已退役），改驗預設分頁 `page-rank` 顯示且 stack 長度 0。
- **因規格變更而更新的斷言**（不放寬，各附理由）：§6.1 七項遷移；category「UI band counts」改比 live（§5.3）；category「flow 時次要標籤列顯示」改為直向收起／橫向顯示（§8.2）；價格狀態文字「合理✓」→「合理」的相關斷言；watch BR／CL 色值在 Light 下的期望值。
- Phase 2～4 的行為只做回歸，不重新驗收。

### 10.3 最終真機驗收（Codex PASS 後由 PO 執行）

每項「操作 → 預期 → PASS／FAIL」的白話步驟於 Codex PASS 後另行提供。範圍：

| 區域 | 驗收重點 |
|---|---|
| Homepage | 入口大廳結構、兩大入口、價格合理區（0 檔／≤10／>10 展開收起／整列點擊）、今日成交量 TOP 10 點擊、無舊查詢與 YouTube 卡 |
| 搜尋 | 首頁與各頁 Header 搜尋、鍵盤、查無不出估算值 |
| 分類 | 文件夾、inside／doorway、切換分類、♡、D4 查看更多 |
| Detail | 開關、分頁、捲動、配息張數試算、♡ |
| 我的 ETF | 收藏同步、卡片、漲紅跌綠、拖曳與移動選單、取消／復原 |
| Tools | 預設排行、切換配息日曆、Back／Forward、排行 → Detail → 返回位置、排名定位 |
| Active Flow | 直向切換分類 ▼／▲、橫向直接標籤、treemap 紅加碼綠減碼、海外清單、Detail → 完整持股異動 → Back |
| Dark／Light | 切換、重新整理保留、跟隨系統、兩主題可讀性與漲紅跌綠、Active Flow 顏色 |
| history | 各頁 Back／Forward、重新整理還原 |
| 裝置 | **iPhone Chrome 主測（Dark＋Light）**、**Samsung Chrome 抽測（Dark＋Light）** |
| 資料池 | Actions 重跑後 00682U／00693U／00763U 不再出現；分類「其他」只剩 0057 |

---

## 11. 待 GPT Gate 確認的實作細節（非 PO 產品決策）

| # | 項目 | Plan 預設 |
|---|---|---|
| G1 | `page-yt` 頻道介紹頁在首頁與 Tools 入口移除後已無入口：退役，Header 圖示直接開外部頻道 | 退役；`switchPage('yt')` 相容入口改開外部連結 |
| G2 | Tools 分頁狀態放在 Tools 模組（記憶體＋`sessionStorage`），不進 Router state／stack，不新增 Router API（取代 Rev.3 的 `Router.setTool`；依 Codex Rev.3 finding） | 採用 |
