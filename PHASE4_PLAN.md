# PHASE 4 PLAN — 自選／我的 ETF（Rev.2.1，Codex PASS；D1～D6 已由 Gate 決議）

> 狀態：**Plan only，尚未 coding。** 產品需求已由 PO／GPT Gate 確認（2026-10-05），本 Plan 只描述實作方式、與現有架構的衝突點、測試。
>
> **Rev.1 → Rev.2（回應 Codex Plan Review NEED FIX 四項）**
> 1. 既有測試與 Detail 收藏整合：§3.1 委派順序與鍵盤；§3.2 `_dtSyncFav()` 獨立於 `detailPatch()` 的 early return；✕ 加 `id="dtClose"`；§10.3 列出**完整**測試遷移清單；新增 DF-* Detail 收藏測試；§8.1 script 載入與初始化順序。
> 2. 跨分頁／拖曳／復原交界：§2.5 通知型別與 storage 同步規則（不回寫、寫入失敗後不被舊資料覆蓋、提示文字更正）；§2.6 `restore` 冪等與 index 規則；§7.4 收藏清單變動時取消拖曳、放下時以 code 規劃位置；新增 ST-5～ST-8、UN-4～UN-6、DR-7。
> 3. 拖曳自動捲動與終止：§7.1 座標系與每幀重算；§7.5 所有終止路徑的收尾；鍵盤防捲頁與焦點；新增 DR-8～DR-13，真機條件照實 DEFER。
> 4. Active Flow：§8.2 列為不可刪除／弱化的既有功能；新增 FL-1～FL-7（computed 色彩與文字、Back／Forward、狀態語意、FD-1～6 保留、收藏不重設 Flow）。
> **Rev.2 → Rev.2.1（Codex 複審 NEED FIX 兩項，只改測試規格）**：FL-4 改為封版 Router 語意（Back 回分類總覽、不回 Detail；涵蓋首頁／工具／分類／自選來源）；UN-5 拆成 UN-5a～c，與「只復原最近一次」一致。§8.2 對應描述同步。
>
> 另：D5 依 Codex 意見，Plan 預設改為「點 ⠿ 開啟移動選單」作為不需拖曳的替代（§7.2），仍待 Gate 確認。
> 前置：Phase 3 VERIFIED / CLOSED，baseline `82ce3ee9`。
> 原則沿用：靜態 PWA、傳統 `<script>`、無 build、無框架、**不新增第三方套件、不新增資料來源**。

---

## 0. 需求摘要（Gate 已定，不在此重議）

| # | 需求 | 本 Plan 對應 |
|---|---|---|
| R1 | 分類列右側殖利率 → ♡；♡／♥ 切換；Detail 同步 ♡／♥；三處共用一份收藏狀態 | §2、§3、§4 |
| R2 | 自選頁正式化；一張 ETF 一張簡易大卡；卡片內容固定（見 §5.2）；點卡片進既有 Detail | §5 |
| R3 | 「近半年走勢」6 柱，沿用 `ret_months` 與 mini-bar 語言；資料不足顯示「歷史資料不足」 | §5.3 |
| R4 | **台股色彩硬規格**：漲紅、跌綠、0 中性、缺值灰；今日漲跌與 6 柱一致 | §6 |
| R5 | 拖曳排序：專用把手 ⠿、不干擾頁面捲動、明文提示、保存順序；不引入大型套件 | §7 |
| R6 | 取消收藏不跳 Dialog；Toast「已從自選移除　復原」，復原回到原位置 | §8 |
| R7 | 引導式空狀態＋［前往分類］ | §5.5 |
| R8 | localStorage only；低調提示「自選 ETF 僅儲存在此裝置與瀏覽器中。」；不做匯出入 | §2 |
| R9 | 預設依加入順序；拖曳後以使用者順序為準；不自動重排 | §2.3 |
| R10 | 不把卡片做成迷你 Detail；典型 3～5 檔；不需學習隱藏操作 | 全篇 |

---

## 1. 現況盤點與衝突點（需 Codex／Gate 注意）

| # | 現況 | 與需求的關係 | Plan 處理 |
|---|---|---|---|
| C1 | 分類清單每列是 `<button class="cat-row">`（`js/category.js` `rowHtml`），整列點擊開 Detail | ♡ 必須是獨立可點的控制；**`<button>` 內不能再放 `<button>`**（HTML 不合法，iOS／螢幕閱讀器行為不可靠） | 列結構改為 `<div class="cat-row" data-code>` 容器，內含「主區按鈕」（代碼＋名稱，開 Detail）與「♡ 按鈕」兩個並列 `<button>`。保留 `.cat-row` class 與 `data-code`，Phase 3 測試與 D4／renderList 的選擇器不變；點擊委派先判斷 `.fav-btn`。§3.1 |
| C2 | `miniBars()`（`js/format.js`）**0 會畫成紅色**（`val >= 0`），顏色寫死 `#ff6b6b／#00e5a0`，不是 `--up／--dn` token | 違反 R4「0＝中性」與「沿用既有 token」 | 新增選項參數 `miniBars(months, { zeroNeutral: true, token: true })`，自選卡使用；**排行頁與 Detail 預設行為不變**（避免 Phase 2／3 回歸）。是否全站統一改為 0 中性，列為 **D1**（§11）。 |
| C3 | 站上**只有深色主題**（`css/base.css` `:root` 無 light mode、無 `prefers-color-scheme`） | R4 寫「Light／Dark 都維持語意」 | 本 Phase 不新增淺色主題（屬範圍外）。自選卡所有漲跌色一律走 `--up／--dn／--dim` token，未來加淺色主題時只需覆寫 token，語意自動延續。列為 **D2** 確認。 |
| C4 | 今日漲跌：`search.js` `gs-chg` 也是 `p >= 0` 視為上漲（0 變紅） | 自選卡需 0 中性 | 自選卡自己的格式函式處理 0／null；不改 search.js（Phase 1 不回歸）。 |
| C5 | Detail 標題列 `.gs-panel-hd`（代碼＋名稱＋✕）在 `body.dt-collapsed`（往下捲）時整列隱藏 | Detail 的 ♡ 若放標題列，捲動收合時會一起暫時消失 | 採標題列（✕ 左側）——與 ✕ 同層級、位置固定好找；收合時與 ✕ 一樣回頂部即出現（Phase 2 已接受的取捨）。替代方案（放在價格列 `.dt-headrow`）列為 **D3**。 |
| C6 | `Router` 已有 `watch` base（`BASE_PAGE.watch = 'page-watch'`），自選頁目前是靜態占位 | 無衝突 | 自選頁不新增 Router 層；Detail 從自選開啟走既有 `openDetail(code)`（push detail 層於 base `watch`）。§5.4 |
| C7 | 市場資料 30 秒輪詢後 `renderAll()` → `Router.onMarketUpdate()` | 自選卡需要跟著更新現價／漲跌 | 在 `renderAll` 尾端呼叫 `Watch.refresh()`（只更新內容，不重建順序、不動捲動、拖曳中不重繪）。§5.6 |
| C8 | 分類列移除殖利率 | 高股息資料夾使用者失去「一眼看殖利率」 | 依 Gate 決定移除；殖利率仍在 Detail 總覽與配息分頁。僅記錄，不改需求。 |

---

## 2. 收藏狀態（單一來源）

### 2.1 模組

新增 `js/watch-store.js`（純資料，無 DOM），於 `category.js`、`detail.js` 之前載入：

```
WatchStore.list()                 → ['0056', '00878', …]（使用者順序，回傳複本）
WatchStore.has(code)              → boolean
WatchStore.add(code)              → 已存在則不動；否則加到最後（R9）
WatchStore.remove(code)           → 回傳 { code, index } 或 null（不存在）
WatchStore.restore(code, index)   → 冪等，規則見 §2.6
WatchStore.moveCode(code, beforeCode)  → 拖曳／移動選單用；以 code 規劃，不用舊索引（§7.4）
WatchStore.subscribe(fn)          → fn({ type, code })，型別見 §2.5
WatchStore.persistOk()            → 最近一次寫入是否成功（供提示）
```

- 三處（分類、Detail、自選）**只讀寫 WatchStore**，不各自保存狀態。
- 通知型別 `add`／`remove`／`restore` 帶 code，分類列與 Detail 只更新該 code 的 ♡；`move`、`sync`（整份重讀）不帶 code，**所有訂閱者都要重新同步**（自選頁依新順序重排、分類列與 Detail 重新對照 ♡）。分類清單的捲動與 D4「已展開數」不受影響（只改 ♡ 節點，不重建列）。

### 2.2 儲存格式

- key：`etfRadar.watch.v1`；值：`{"v":1,"codes":["0056","00878"]}`。
- 所有讀寫包 `try/catch`，不假裝已保存：
  - **讀取失敗**（localStorage 不可用）：以空清單、記憶體模式啟動，提示「目前瀏覽器無法保存自選，重新整理後會遺失。」
  - **寫入失敗**（例如儲存空間滿）：保留本次記憶體狀態（畫面照使用者操作呈現），`persistOk()` 為 false，提示「這次的變更無法保存，重新整理後可能回到先前保存的內容。」——**不**宣稱「全部清空」，因為舊的持久化資料可能仍在。
  - 下一次寫入成功後提示消失。
- 讀取時驗證：非陣列、非字串、重複代碼 → 清洗（去重、保留第一次出現的順序）。
- `storage` 事件規則見 §2.5。
- **不做**匯出／匯入、雲端、帳號（R8），也不做跨分頁原子交易。

### 2.3 排序規則

- 新加入 → 放最後（加入順序）。
- 拖曳 → `move()` 後立即寫入，之後一律以使用者順序為準。
- 不依漲跌、代碼、signal 自動重排；分類頁的排序按鈕（代碼／名稱）只影響分類清單，不影響自選順序。

### 2.4 收藏的代碼不在今日資料中

例如 ETF 下市或被排出資料池：**不自動刪除**。自選卡顯示代碼與「目前無法取得這檔的資料」，♥ 與 ⠿ 仍可用，使用者可自行移除。

### 2.5 通知與 `storage` 同步

| 情境 | 行為 |
|---|---|
| 本分頁 add／remove／restore／moveCode | 更新記憶體 → 寫入 localStorage → 通知（對應型別） |
| 其他分頁改了 key（`storage` 事件） | 重讀 → 清洗 → **只更新記憶體並發 `sync` 通知，不回寫**（避免兩分頁互相觸發形成循環） |
| 本分頁最近一次寫入失敗（`persistOk()` 為 false）時收到 `storage` 事件 | **不以舊資料覆蓋**本次記憶體狀態（使用者剛做的變更優先）；忽略該次重讀，直到本分頁下一次寫入成功 |
| `sync` 期間正在拖曳 | 依 §7.4 取消拖曳 |
| `sync` 期間 Toast 仍在 | Toast 保留；按「復原」時依 §2.6 冪等規則處理 |

### 2.6 `restore` 規則（冪等）

- `restore(code, index)`：
  - 若 `code` **已在清單中**（例如 5 秒內從分類、Detail 或另一分頁重新加入）→ **不做任何事**（不重複、不搬動既有位置），Toast 關閉。
  - 否則插入 `min(index, 目前長度)`。`index` 是移除當下的位置；期間清單若被重排、新增或刪除，仍以這個數字夾限，不嘗試推算「原本的鄰居」。（簡單、可預期；Codex 已確認夾限方案可保留。）
- 只保留最近一次移除的復原資訊；第二次移除會取代第一次（D4）。
- 復原成功發 `restore` 通知；自選頁把卡片插回該位置。

---

## 3. 收藏入口

### 3.1 分類清單列（取代殖利率）

```
[ 0056   元大高股息                    ♡ ]
  └──── 主區按鈕：開 Detail ────┘  └ ♡ 按鈕 ┘
```

- `rowHtml` 改為容器 `<div class="cat-row" data-code>` ＋ `<button class="cr-main">`（`.cr-code`、`.cr-name`）＋ `<button class="fav-btn">`。
- ♡ 按鈕可點擊區 **44×44**；圖示 ♡（未收藏，`--dim`）／♥（已收藏，`--up` 紅）。
- `aria-pressed="true|false"`；`aria-label`：「加入自選：0056 元大高股息」／「從自選移除：0056 元大高股息」。
- 事件委派（`#page-cat` 現有的 click handler）**順序改為**：① `.fav-btn` → 切換收藏並 `return`；② `.cr-main` → 開 Detail（取代目前直接比對 `.cat-row`）；③ 其餘既有分支（切換分類、分段、排序、查看更多、返回）不變。
- 鍵盤：`.cr-main` 與 `.fav-btn` 都是原生 `<button>`，Enter／Space 各自觸發（前者開 Detail，後者切換收藏），Tab 依序經過兩者。
- 移除 `.cr-yld` 與 `fmtYld` 在分類列的呼叫（`fmtYld` 其他頁仍在用，函式保留）。
- 影響面：`.cat-row` 仍是每列的外層、`data-code` 不變（計數類檢查不變）；直接對 `.cat-row` 呼叫 `click()` 的測試需改點 `.cr-main`（完整清單見 §10.3）。D4 的 `.cat-more-in` 不變。

### 3.2 Detail（§1 C5）

- `.gs-panel-hd` 結構：`[標題] [♡ #dtFav] [✕ #dtClose]`。✕ **新增 `id="dtClose"`**（文字與 `onclick="closeDetail()"` 不變），測試一律改用 `#dtClose` 作為關閉控制，不再用「標題列第一個 button」（§10.3）。
- ♡ 44×44，同一套圖示與 aria（「加入自選：代碼 名稱」／「從自選移除：代碼 名稱」；這檔不在資料中時只帶代碼）。
- 新增獨立函式 `_dtSyncFav()`：依 `WatchStore.has(_curEtfCode)` 更新圖示、`aria-pressed`、`aria-label`。呼叫點：
  - `detailPatch()` **開頭**（在 `if (!e) … return` 這個 early return **之前**），因此 missing ETF 時也會更新；
  - WatchStore 通知（任何型別）且 Detail 開著時；
  - `detailShow()` 換到另一檔時（經由 `detailPatch()`）。
- 點 ♡ 只呼叫 WatchStore，**不**呼叫 Router、不關面板、不改 `_detailTab`、不動 `#gsPanel` 的 scrollTop、不重建 Detail 內容（不呼叫 `_dtBuild()`），計算機輸入框的值與焦點以外的狀態保持不變。DF-* 測試驗證（§10.1）。

### 3.3 其他頁面

首頁、搜尋結果、排行頁 **不加 ♡**（不在需求內）；從那些頁面開 Detail 後可在 Detail 收藏。

---

## 4. 取消收藏與復原（R6）

- 任何一處（分類、Detail、自選卡）把 ♥ 點回 ♡ → 立即移除，不跳 Dialog。
- 顯示全站共用 Toast（固定在 bottom nav 上方，`role="status"`、`aria-live="polite"`）：
  `已從自選移除　［復原］`，約 **5 秒**後自動消失。
- 復原：`WatchStore.restore(code, index)` 插回原位置（若期間清單變短，夾到最後）。
- 只保留「最近一次」移除；連續移除第二檔時，Toast 換成第二檔，第一檔不可再復原（簡單、可預期）。列為 **D4** 確認。
- 新增收藏 **不顯示** Toast（♥ 本身即回饋），避免干擾。列為 D4 一併確認。
- 自選頁上移除：卡片直接消失（`prefers-reduced-motion` 時無動畫，否則 150ms 淡出）。
- Toast 不遮住 bottom nav；低高度橫向時字級不變，「復原」按鈕永遠完整可見（≥ 44px 高），空間不足時讓說明文字換行，而不是截斷「復原」。

---

## 5. 自選頁

### 5.1 版面（由上而下）

```
我的自選                          （頁面標題，與其他頁一致）
按住 ⠿ 可拖曳調整順序              （≥ 2 檔時顯示；1 檔不顯示）
┌───────────────────────────────┐
│ ⠿  0056  元大高股息        ♥ │
│    57.78   ▲0.73  +1.27%       │
│    近半年走勢  ▁▃▅▂▆▃          │
│    [偏貴] · 高股息 · 季配       │
└───────────────────────────────┘
…（每檔一張）
自選 ETF 僅儲存在此裝置與瀏覽器中。 （低調小字，頁尾）
```

### 5.2 卡片內容（固定，不增不減）

| 列 | 內容 | 資料 |
|---|---|---|
| 1 | ⠿ 把手、代碼＋名稱、♥ | `code`、`name`、WatchStore |
| 2 | 現價、今日漲跌額、今日漲跌幅 | `price`、`change_pt`、`change_pct`（顏色 §6） |
| 3 | 「近半年走勢」＋ 6 柱 | `ret_months`（§5.3） |
| 4 | 價位訊號標籤 · Phase 3 分類 · 配息頻率 | `signal`（沿用 `_DT_SIG`／`sig-*` class）、`catDefOf(catClassify(e)).label`、`div_frequency` |

- **不放**：殖利率、52 週位置、RSI／MA／量、台股／海外標籤、績效數字。
- 卡片高度目標約 120～140px（390px 寬）；一列一張。
- 點卡片主體 → `openDetail(code)`；⠿ 與 ♥ 是卡片內獨立按鈕，點它們不開 Detail（同 §3.1 的結構：卡片為 `<div>`，內含主區 `<button>`、⠿、♥）。

### 5.3 近半年走勢（6 柱）

- 取 `ret_months` 全部 6 段（由舊到新，最右為最近）。
- 視覺沿用 mini-bar（寬 8px、高 26px、中線、正值向上、負值向下），以 `miniBars(months, { zeroNeutral: true, token: true })` 繪製（§1 C2）。
- 缺值段：灰色短柱（沿用既有缺值視覺）。
- **6 段全缺** → 不畫柱，顯示文字「歷史資料不足」（`--dim`）。目前 203 檔中 1 檔（009827）全缺。
- 只有部分缺值（目前 26 檔，多為上市未滿約半年）→ 照畫，缺值為灰柱，不另加文字。
- 卡片上**不寫**技術定義（22 個交易日、非日曆月）；這段說明保留在 Detail 績效分頁（已存在）。
- 標題文字固定為「近半年走勢」，不寫「近 6 個月報酬」。
- 每根柱的 `title`／`aria-label` 帶數值（例如「+4.0%」），柱群整體 `aria-label`：「近半年走勢：+8.6%、+18.8%、…」，缺值讀作「資料不足」。

### 5.4 卡片 → Detail → 返回

- 開啟：`openDetail(code)`，Router 在 base `watch` 上 push detail 層（與分類開 Detail 同一路徑，**不建立第二套 Detail**）。
- 返回（✕、Back、Esc）：Detail 關閉，回到自選頁。Detail 是覆蓋在頁面上的面板，自選頁本身沒有切換，**window 捲動位置自然保留**（`applyBasePage` 只在換頁時 `scrollTo(0,0)`）。
- 在 Detail 取消收藏後返回：該卡已不在清單（Toast 可復原）；若復原，卡片回到原位置。
- 自選頁不寫入新的 Router 層、不記 `ui`（無資料夾式的內部狀態）。重新整理後回到自選頁頂端。列為測試確認，不另做捲動還原。

### 5.5 空狀態（R7）

```
還沒有收藏 ETF
到「分類」逛逛，看到有興趣的 ETF，按下 ♡ 就能加入這裡。
［前往分類］
```

- ［前往分類］→ `switchPage('cat')`（分類總覽）。按鈕 ≥ 44px。
- 空狀態下也顯示頁尾儲存提示。
- 最後一檔被移除時立即切成空狀態；此時按「復原」回到 1 張卡。

### 5.6 資料更新

- `renderAll()` 尾端呼叫 `Watch.refresh()`：只更新每張卡的數值、顏色、柱、標籤；**不重排、不重建 DOM 順序、不動捲動**。
- 拖曳進行中收到更新 → 延後到放開後再補畫（避免拖曳中卡片跳動）。
- 資料尚未載入（首次開啟、離線）：卡片顯示代碼與「資料載入中…」；資料失敗時沿用全站 `data-error` 橫幅，不另做錯誤頁。

---

## 6. 台股色彩（R4，硬規格）

| 值 | 今日漲跌額／幅 | 6 柱 | Token |
|---|---|---|---|
| > 0 | 紅，前綴 ▲／+ | 紅柱向上 | `--up`（#ff3f5e） |
| < 0 | 綠，前綴 ▼／− | 綠柱向下 | `--dn`（#00c87a） |
| = 0 | 中性，無箭頭，「0.00」「0.00%」 | 中線上一條中性短柱 | `--dim` |
| null／缺 | 灰，「--」 | 灰色短柱（既有缺值樣式） | `rgba(255,255,255,.15)`（沿用 miniBars 缺值色） |

- 0 與缺值**必須可區分**：0 是「有資料、沒漲跌」，缺值是「沒有資料」（文字 0.00% vs --；柱：中性短柱 vs 灰色短柱，透明度不同）。
- 不依賴顏色作為唯一資訊：漲跌額另有 ▲／▼ 與正負號（色弱可辨）。
- **禁止**美股漲綠跌紅；測試以實際 computed color 比對 token（§10）。
- 價位訊號標籤沿用既有 `sig-*` 顏色（便宜綠、合理金、過熱紅、偏貴橘、債券藍）——這是**訊號語意**，不是漲跌語意；兩者在卡片上分列，不混用。

---

## 7. 拖曳排序（R5）

### 7.1 方式：原生 Pointer Events（不引入套件）

- 每張卡左側 `<button class="drag-handle" aria-label="調整順序：0056 元大高股息">⠿</button>`，可點擊區 **44×44**。
- **只有把手** `touch-action: none`；卡片其他區域維持預設，頁面上下滑動不受影響。
- `pointerdown`（把手）→ 移動 ≥ 8px 才進入拖曳（§7.2）→ `setPointerCapture` → 卡片「抬起」（陰影、`transform: translateY()` 跟手）→ 依各卡中線判斷插入位置，其他卡以 `transform` 讓位 → `pointerup` 放下 → `WatchStore.moveCode()`（§7.4）寫入 → 以新順序重排 DOM。
- 拖到可視區上／下緣 48px 內時自動捲動，讓 10 檔左右也能拖到頭尾。

**座標系（統一用 layout viewport 的 client 座標）**
- pointer 的 `clientY` 與卡片的 `getBoundingClientRect()` 都是 layout viewport 的 client 座標，直接比較。
- 可視區邊界（判斷是否靠近上／下緣）：`visualViewport.offsetTop` 到 `offsetTop + visualViewport.height`（同樣是 client 座標）；不支援 visualViewport 時用 `0..innerHeight`。上緣再扣掉頂欄、下緣扣掉 bottom nav 的實際 rect，避免把被遮住的區域當成可視。
- 拖曳位移 = `(pointerY − 起始 pointerY) + (scrollY − 起始 scrollY)`：頁面捲動時，即使手指不動，卡片仍跟著手指位置。

**每幀重算**
- 拖曳期間以 `requestAnimationFrame` 迴圈處理：每幀依最後一次 pointerY 判斷是否自動捲動（速度依距邊緣遠近，上限約 12px／幀）→ `window.scrollBy` → **重新讀取各卡 rect、重算拖曳位移與插入位置**。不只在 pointermove 時更新，所以手指停在邊緣時插入位置仍會隨捲動前進。
- pointermove 只更新「最後的 pointerY」，實際排版計算都在 rAF 內。
- iOS：把手加 `-webkit-user-select: none; -webkit-touch-callout: none;`，避免長按跳出選字／放大鏡。
- 按下把手後直接進入拖曳（不需長按）——提示文字寫「按住 ⠿ 可拖曳」，使用者照做即可；不需學習隱藏手勢。
- `prefers-reduced-motion`：讓位不做過渡動畫，直接換位。

### 7.2 無障礙與不需拖曳的替代操作（D5，Plan 預設已依 Codex 意見調整）

- **點一下 ⠿（沒有拖動）→ 開啟移動選單**：「上移一格／下移一格／移到最上面／移到最下面」，在第一檔或最後一檔時對應選項停用。卡片上**不增加**任何常駐按鈕；VoiceOver／TalkBack 使用者點兩下把手即可操作，不需要拖曳手勢。
  - 判斷「點一下」與「拖曳」：pointerdown 後移動 < 8px 且放開 → 視為點擊開選單；移動 ≥ 8px → 進入拖曳。
  - 選單為卡片下方的小浮層（`role="menu"`），點選後關閉；點外面、Esc、捲動頁面時關閉。
- 把手聚焦時，**↑／↓ 鍵**直接上移／下移一格（外接鍵盤），`preventDefault()` 防止同時捲動頁面；重排後**焦點留在同一檔的把手**；`aria-live` 播報「0056 移到第 2 位，共 4 檔」。
- 把手 `aria-label`：「調整順序：0056 元大高股息，第 1 位，共 4 檔」。
- 若 Gate 認為移動選單仍不需要（只要拖曳＋鍵盤），可移除選單，其他不受影響（D5）。

### 7.3 風險評估

| 風險 | 評估 | 對策 |
|---|---|---|
| iOS Chrome（WebKit）Pointer Events | iOS 13+ 支援；`touch-action: none` 只在把手上，頁面捲動不受影響 | 真機 iPhone Chrome 必測 |
| 拖曳與頁面捲動互搶 | 把手 `touch-action: none` 使瀏覽器不在把手上啟動捲動；把手以外照常捲動 | 測試 §10.1 DR-* |
| Samsung Chrome 邊緣返回手勢 | 把手在卡片左側，可能靠近螢幕左緣 | 卡片左內距使把手距螢幕左緣 ≥ 16px；真機抽測 |
| 拖曳中資料輪詢 | 重繪會打斷拖曳 | §5.6 延後補畫 |
| 實作量 | 約 150～200 行原生 JS，無依賴 | 評估可控，**不需第三方套件** |

結論：**原生實作風險可接受**，不擴充依賴。

### 7.4 拖曳期間收藏清單改變

- 拖曳開始時記下 `dragCode` 與當時的清單快照。
- 拖曳期間若收到 WatchStore 的 `add`／`remove`／`restore`／`sync`／`move` 通知（例如另一分頁刪除了別檔、或 Toast 復原）→ **立即取消這次拖曳**（同 §7.5 cancel：不寫入，卡片回位），自選頁依最新清單重繪。不嘗試把舊的拖曳意圖套到新清單上。
- 放下時**以 code 規劃位置**：依畫面上插入點取得「放在哪一檔之前」的 `beforeCode`（最後則為 null），呼叫 `moveCode(dragCode, beforeCode)`。WatchStore 內部以目前清單重新找位置；若 `dragCode` 或 `beforeCode` 已不存在（理論上已被上一條取消，作為防禦）→ 不做任何事。**不使用拖曳開始時的舊索引覆寫新順序。**
- 移動選單（§7.2）與鍵盤排序同樣經由 `moveCode`。

### 7.5 拖曳的所有終止路徑（統一收尾 `endDrag(commit)`）

| 觸發 | commit | 收尾 |
|---|---|---|
| `pointerup`（且已進入拖曳） | 是 | 寫入順序 |
| `pointercancel`、`lostpointercapture`（非正常放開） | 否 | 回原順序 |
| 清單改變（§7.4） | 否 | 回原順序後依新清單重繪 |
| 離開自選頁（Router 換 base）、開啟 Detail、`visibilitychange` 變 hidden、`pagehide` | 否 | 回原順序 |

`endDrag` 一律：釋放 pointer capture、清除所有卡片的 `transform`／抬起樣式、停止 rAF 自動捲動迴圈、移除暫時事件監聽、補畫拖曳期間被延後的 `Watch.refresh()`（§5.6）。cancel 不寫入 localStorage。

---

## 8. 檔案變更規劃

| 檔案 | 變更 |
|---|---|
| `js/watch-store.js`（新） | §2 收藏狀態、localStorage、`storage` 事件、subscribe |
| `js/watch.js`（新） | 自選頁渲染、卡片、空狀態、Toast、拖曳、`Watch.refresh()` |
| `js/category.js` | `rowHtml` 改結構（§3.1）、點擊委派加 `.fav-btn`、訂閱 WatchStore 更新 ♡ |
| `js/detail.js` | 標題列 ♡（§3.2），`detailPatch` 同步 |
| `js/format.js` | `miniBars` 新增選項參數（預設行為不變） |
| `js/render.js` | `renderAll` 尾端呼叫 `Watch.refresh()` |
| `index.html` | `#page-watch` 改為正式容器；`.gs-panel-hd` 加 `#dtFav`、✕ 加 `id="dtClose"`；Toast 容器；依 §8.1 順序載入新 script；資源版本號 |
| `css/watch.css`（新）或併入 `css/category.css` | 卡片、把手、Toast、♡ 按鈕、空狀態 |
| `tests/browser/watch_test.py`（新） | §10 自動測試 |
| `tests/browser/category_test.py`、`detail_state_test.py`、`detail_ui_test.py`、`detail_history_fix_test.py` | 選擇器遷移（§10.3 完整清單）；category 另加 ♡ 與 FL-* 檢查 |

**不改**：`router.js`（沿用 `watch` base 與既有 detail 層）、`flow.js`、`search.js`、B6 警示條、Phase 3 文件夾與標題列、資料 pipeline。

### 8.1 Script 載入與初始化順序

目前順序：`config → nav → flow → archived-check → format → calc → lookup → render → rank → search → category-rules → category → detail → router → boot`。Phase 4 插入：

```
… format → calc → lookup → render → rank → search
→ watch-store.js        ← 新：在所有使用者（category、detail、watch）之前；載入時讀 localStorage，不碰 DOM
→ category-rules → category → detail
→ watch.js              ← 新：自選頁＋Toast；在 router／boot 之前定義 Watch 並完成 init
→ router → boot
```

- `watch-store.js` 只定義資料與 `subscribe`，不依賴任何 DOM 或其他模組。
- `category.js`、`detail.js` 在各自既有的初始化處 `WatchStore.subscribe(...)`；回呼內只操作自己的 DOM，且先檢查節點存在（Detail 未開時不做事）。
- `watch.js` 載入時立即 `Watch.init()`：建立 Toast 容器、綁定自選頁事件、訂閱 WatchStore、以「資料載入中」畫出卡片骨架。因此 `boot.js` 第一次 `fetchData → renderAll → Watch.refresh()` 時 `Watch` 已存在。
- `render.js` 雖然在 `watch.js` 之前載入，但 `renderAll` 只在 boot 之後被呼叫；呼叫處仍加 `typeof Watch !== 'undefined'` 守衛（與現有 `typeof Category` 寫法一致）。
- Toast 屬於 `watch.js`，分類與 Detail 取消收藏時呼叫 `Watch.toastRemoved({code,index})`；`Watch` 一定先於任何使用者操作完成初始化。

### 8.2 Active Flow（持股異動）——不可刪除、弱化、重做或替代的既有功能

Phase 4 不修改 `flow.js`，且下列行為必須維持，並以 §10.1 FL-* 測試明確保護：

- 分類 → 主動式 → 「持股異動」分段：treemap 正常顯示；**加碼＝紅、減碼＝綠**（`renderFlow` 的 `rgba(255,63,94,…)`／`rgba(0,200,122,…)`）。
- 海外無報價的增減股數列表（`_renderNoPrice`）：正值 `var(--up)` 紅、負值 `var(--dn)` 綠、缺值 `var(--dim)`，文字帶正負號。
- Detail 持股分頁 → 「查看完整持股異動 ›」→ Flow（同一檔），沿用封版 Router 語意：不留 Detail 層，Back 回分類總覽、Forward 回同檔持股異動（Phase 4 不改 Router、不重建持股異動 history）。
- `fetched=false`（沿用舊資料）、最新 PCF 無異動、海外無報價、未更新等提示語意不變。
- 既有 FD-1～FD-6（visualViewport／orientation／resize 重繪、容器寬度追隨）保留。
- 收藏 ♡ 或自選頁重繪**不得**重設 Flow 的選取 ETF（`_flowSel`）與目前顯示的分段。
- 分類列結構改動（§3.1）不影響持股異動分段（Flow 檢視不使用 `.cat-row`）。

---

## 9. 實作順序（每步可獨立驗證）

1. WatchStore（含清洗、容錯、storage 事件）＋單元測試。
2. 分類列結構改造＋♡（先確保 Phase 3 全部回歸 PASS）。
3. Detail ♡。
4. 自選頁卡片（不含拖曳）＋空狀態＋儲存提示＋資料更新。
5. 取消收藏 Toast／復原。
6. 拖曳排序（含自動捲動、終止收尾、清單變動取消）＋移動選單＋鍵盤替代。
7. 全回歸 → 交 Codex → 真機。

---

## 10. 測試計畫

### 10.1 自動測試（headless Chrome，`tests/browser/watch_test.py`）

| 編號 | 項目 | 通過條件 |
|---|---|---|
| ST-1 | WatchStore 基本 | add／remove／restore／moveCode 結果正確；重複 add 不重複 |
| ST-2 | 容錯 | localStorage 丟例外 → 退回記憶體、頁面顯示「無法保存」提示、無未捕捉例外；壞 JSON → 清洗為空 |
| ST-3 | 重新整理保留 | 加入 3 檔、拖曳成新順序 → reload → 收藏與順序一致 |
| ST-4 | 跨分頁 | 觸發 `storage` 事件 → 本頁重讀 |
| SY-1 | 三處同步 | 分類點 ♡ → Detail 該檔顯示 ♥ → 自選頁出現卡片；自選取消 → 分類與 Detail 回到 ♡ |
| SY-2 | 分類列 | ♡ 44×44、`aria-pressed`、`aria-label` 正確；點 ♡ **不開 Detail**；點主區開 Detail；殖利率已不顯示 |
| SY-3 | 分類狀態不受影響 | 點 ♡ 後清單捲動位置、已展開數（D4）、排序不變 |
| CD-1 | 卡片內容 | 代碼、名稱、現價、漲跌額／幅、6 柱、signal、分類、配息頻率皆正確；**無**殖利率、52 週、RSI 等 |
| CD-2 | 卡片 → Detail → 返回 | 開的是同一個 `#gsPanel`；✕／Back 返回後仍在自選頁，window 捲動位置不變 |
| CD-3 | Detail 中取消再返回 | 卡片消失、Toast 出現；復原後回到原位置 |
| UN-1 | 取消 → 復原 | 移除第 2 張（共 4 張）→ 復原 → 回到第 2 位；5 秒後 Toast 消失 |
| UN-2 | 連續移除 | 只能復原最後一次 |
| UN-3 | 最後一檔 | 移除後顯示空狀態；復原回到 1 張 |
| BR-1 | 6 柱正／負／0／缺值 | 以 fixture 注入 `[2.1,-1.5,0,null,3.0,-0.4]`：柱方向、computed color 分別為 `--up`／`--dn`／`--dim`／缺值灰 |
| BR-2 | 全缺 | 6 段 null → 不畫柱，顯示「歷史資料不足」 |
| BR-3 | 新上市部分缺值 | 以實際資料（如 00402A）驗證灰柱數量正確、無例外 |
| CL-1 | 漲紅跌綠 | `change_pt` > 0 → computed color = `--up`（紅）、▲；< 0 → `--dn`（綠）、▼；0 → `--dim`、無箭頭；null → 「--」 |
| CL-2 | 反向守衛 | 明確斷言「上漲不是綠、下跌不是紅」（防止日後誤改） |
| DR-1 | 把手拖曳 | 以 CDP `Input.dispatchTouchEvent` 在把手上拖動 → 順序改變並寫入 |
| DR-2 | 卡片本體滑動 | 在卡片非把手區域垂直滑動 → 頁面捲動、順序**不變** |
| DR-3 | 把手 `touch-action` | 把手 computed `touch-action: none`；卡片其他區域不是 none |
| DR-4 | pointercancel | 拖曳中發 cancel → 回原順序、不寫入 |
| DR-5 | 鍵盤 | 把手聚焦按 ↓ → 下移一格並播報 |
| DR-6 | 拖曳中輪詢 | 拖曳中呼叫 `Watch.refresh()` → 不重排；放開後數值更新 |
| ES-1 | 空狀態 | 文案正確；［前往分類］→ 分類總覽（`data-state="overview"`） |
| ES-2 | 提示文字 | 儲存提示存在；拖曳提示 ≥ 2 檔才顯示 |
| LV-1 | 低高度／橫向 | 844×390、844×170（鍵盤）：卡片不水平溢出、Toast 不遮 nav、把手可用 |
| A11Y | 無障礙 | ♡／⠿／［前往分類］有 accessible name；Toast `role="status"` |

**Rev.2 新增**

| 編號 | 項目 | 通過條件 |
|---|---|---|
| ST-5 | storage 不回寫 | 注入 `storage` 事件 → 記憶體與畫面同步、`localStorage.setItem` 未被呼叫（spy） |
| ST-6 | 寫入失敗後的 storage | 讓 `setItem` 丟例外後再加入一檔 → 畫面保留這檔、出現「這次的變更無法保存…」提示；接著注入舊內容的 `storage` 事件 → **不被覆蓋** |
| ST-7 | 寫入失敗後 reload | 同上情境 reload → 回到先前成功保存的內容（不是全部清空）；提示文字不宣稱已清空 |
| ST-8 | 讀取失敗 | `getItem` 丟例外 → 空清單＋「無法保存自選」提示，可正常收藏（記憶體），無未捕捉例外 |
| ST-9 | move／sync 通知 | `moveCode` 與 `storage` 同步後，自選頁卡片順序、分類列 ♡、Detail ♡ 全部與 Store 一致 |
| UN-4 | 復原冪等 | 移除 A → 5 秒內從分類重新加入 A → 按「復原」→ A 只出現一次且位置不變 |
| UN-5a | 連續 UI 移除 | 共 5 張，移除第 3 張（A）→ Toast 尚在時再移除另一張（B，第 1 張）→ Toast 換成 B；按「復原」→ **只復原 B**，回到 index 0；A 不可復原、不重新出現 |
| UN-5b | 原 Toast 存續時清單縮短 | 共 5 張，移除第 5 張（A，index 4）→ Toast 尚在時以注入 `storage` 事件（非 Toast 操作）使清單剩 2 張 → 按「復原」→ A 插在 `min(4, 2)` = 2（最後） |
| UN-5c | 移除後拖曳重排再復原 | 共 5 張，移除第 2 張（A，index 1）→ Toast 尚在時以拖曳／移動選單重排其餘 4 張 → 按「復原」→ A 插在 index 1（原數字夾限，不推算原鄰居） |
| UN-6 | 跨分頁重新加入 | 移除 A → 注入 `storage` 使 A 重新出現 → 復原不重複 |
| DF-1 | Detail ♡ 不影響面板 | 點 `#dtFav`：面板仍開、`history.length` 與 `Router.state()` 不變、`_detailTab` 不變、`#gsPanel.scrollTop` 不變、配息計算機輸入值不變 |
| DF-2 | Detail 換 ETF | 開 A（已收藏）→ 在 Detail 內切到 B（未收藏）→ ♡ 狀態與 `aria-label` 隨之更新 |
| DF-3 | Back／Forward | Detail 收藏後 Back 關閉 → Forward 再開 → ♥ 仍正確 |
| DF-4 | missing ETF | 開一個不在資料中的代碼 → ♡ 仍可切換，`aria-label` 帶代碼 |
| DF-5 | 關閉控制 | `#dtClose` 存在且為原本的 ✕；點 ♡ 不會被當作關閉 |
| DF-6 | 收合 | Detail 往下捲（`dt-collapsed`）時 ♡ 與 ✕ 同步隱藏、回頂部同步出現 |
| DR-7 | 拖曳中清單改變 | 拖 B 時注入 `storage`（刪除 A）→ 拖曳取消、不寫入、畫面順序＝Store 順序；放手不會把 B 移到錯誤位置 |
| DR-8 | 10 檔上下緣連續拖曳 | 10 張卡，從第 1 張拖到畫面下緣停住 → 自動捲動直到最後，放下成為第 10；反向亦然 |
| DR-9 | 頁面已捲動 | 先捲到中段再拖曳 → 位移與插入位置正確（座標系一致） |
| DR-10 | 低高度 | 844×390、390×300 下拖曳與自動捲動正常，卡片不被導覽列遮住時才判定可視 |
| DR-11 | cancel 停止捲動 | 自動捲動中發 `pointercancel` → 之後 500ms `scrollY` 不再變化、所有卡片 transform 清除 |
| DR-12 | 拖曳中導航 | 拖曳中 `switchPage('cat')`／開 Detail → 拖曳結束、無殘留 capture／transform／rAF、順序未寫入 |
| DR-13 | 連續鍵盤排序 | 把手聚焦連按 ↓ 三次 → 移動三格、`scrollY` 未因箭頭改變、焦點仍在同一檔把手 |
| DR-14 | 點 ⠿ 開移動選單 | 點一下（移動 < 8px）→ 選單出現；「移到最上面」生效；第一檔時「上移」停用；Esc 關閉 |
| FL-1 | 持股異動顯示 | 分類 → 主動式 → 持股異動：treemap 有格子 |
| FL-2 | treemap 顏色 | 以 fixture 注入同時含加碼與減碼的 flow（不依賴當日真實資料），加碼格 computed background 為紅系（`rgb(255, 63, 94)` 帶透明度）、減碼格為綠系（`rgb(0, 200, 122)`）；斷言不是反過來 |
| FL-3 | 海外無報價列表 | 以 fixture 注入同時含正值、負值、缺值的 `no_price`：正值 computed color＝`--up`、負值＝`--dn`、缺值＝`--dim`，文字帶 +／− |
| FL-4 | Detail → 完整持股異動（**沿用封版 Router 語意，不改 Router**） | 分別從**首頁、工具、分類、自選**開啟某主動式 ETF 的 Detail → 持股分頁按「查看完整持股異動 ›」→ Flow 顯示**同一檔**；`Router.state().stack` 只有 `folder(active, flow)`、**不留 Detail 層**；Back → **分類總覽**（不回 Detail，依 PHASE3_PLAN §8.3、§16.6 NV-A～NV-D、router_test RT-22）；Forward → 回到同一檔的持股異動 |
| FL-5 | 狀態語意 | 以 fixture 注入 `fetched=false`、無異動、未更新三種狀態 → 對應提示文字存在 |
| FL-6 | FD-1～FD-6 | 既有檢查全數保留並 PASS |
| FL-7 | 收藏不重設 Flow | Flow 顯示中切換某檔 ♡（經 Detail）／自選頁重繪 → `_flowSel` 與目前分段不變 |

**真機才能驗證、headless 照實 DEFER（不以 stub 當 PASS）**
- `visualViewport.offsetTop > 0`（鍵盤或瀏覽器 UI 造成可視區位移）時的拖曳與自動捲動。
- 實際觸控拖曳手感、iOS 長按選字是否被抑制、Samsung 左緣返回手勢衝突。
- VoiceOver 點兩下 ⠿ 開移動選單。

### 10.2 回歸（全部既有測試必須 PASS）

router 64、search_compact 38、detail_ui 42、detail_history_fix 14、regression 14、detail_collapse 25、detail_state 42、category（現行 250 PASS／1 DEFER，含 FD-1～FD-6）。另加 §10.1 FL-1～FL-7 保護持股異動（§8.2）。

### 10.3 既有測試的必要調整（完整清單；只換選擇器，不放寬任何 history／scroll／狀態檢查）

| 檔案 | 位置（目前行號） | 現在 | 改為 |
|---|---|---|---|
| `category_test.py` | 125、133、464 | `#catList .cat-row` 直接 `click()` | 點該列的 `.cr-main` |
| `category_test.py` | 552（`rl_open_detail`） | `.cat-row[data-code=…]` `click()` | `.cat-row[data-code=…] .cr-main` |
| `category_test.py` | 466、554（`rl_close_x`） | `#gsPanel .gs-panel-hd button`（第一個 button） | `#dtClose` |
| `detail_state_test.py` | 93 | `#gsPanel .gs-panel-hd button` | `#dtClose` |
| `detail_state_test.py` | 108 | `.cat-row[data-code="0050"]` `click()` | `.cat-row[data-code="0050"] .cr-main` |
| `detail_ui_test.py` | 112、157、178、192 | `#gsPanel .gs-panel-hd button` | `#dtClose` |
| `detail_history_fix_test.py` | 56 | `#gsPanel .gs-panel-hd button` | `#dtClose` |
| `category_test.py`、`router_test.py` | 59、61、63、70、80、129、267、436、438、490、547；router 71 等 | `.cat-row` **計數**與 rect 量測 | **不變**（外層 class 保留） |

- 實作前再以 `grep -n "gs-panel-hd button\|\.cat-row" tests/browser/*.py` 重掃一次，行號以當時為準；不得遺漏任何一處。
- 若列高度因 ♡ 改變而影響 AB／RL 的清單幾何，依 Phase 3 的方式調整視窗並在 AI_HANDOFF 說明（附量測），不刪、不放寬檢查。

### 10.4 真機驗收（Codex PASS 後由 PO 執行）

| 環境 | 範圍 |
|---|---|
| **iPhone + Chrome**（主要） | 全部：收藏同步、自選卡、6 柱與顏色、拖曳 vs 捲動、取消／復原、空狀態、重新整理保留、橫向與低高度 |
| **Samsung + Chrome**（相容性抽測） | 收藏同步、拖曳 vs 捲動（含左緣返回手勢）、取消／復原、重新整理保留 |
| iPhone + Safari | 不列必測（需求未要求）；若 PO 方便可抽測 localStorage 與拖曳 |

真機步驟於 Codex PASS 後另行提供（逐步、每步一件事、附 PASS／FAIL）。

---

## 11. 待 PO／Gate 確認的實作細節（不改需求，只確認做法）

| # | 問題 | Plan 預設 |
|---|---|---|
| D1 | `miniBars` 的「0＝紅」是否全站修正為中性（排行頁、Detail 一起） | 只在自選卡生效；全站修正另議 |
| D2 | 站上沒有淺色主題，R4 的 Light mode 要求如何處理 | 本 Phase 不加淺色主題；色彩全走 token，未來加主題時語意自動延續 |
| D3 | Detail 的 ♡ 位置 | 標題列 ✕ 左側（捲動收合時與 ✕ 同步隱藏，回頂部出現） |
| D4 | Toast 規則 | 只對「移除」顯示、5 秒、只能復原最近一次；新增收藏不顯示 Toast |
| D5 | 拖曳之外的替代排序 | **點 ⠿ 開移動選單**（上移／下移／最上／最下）＋鍵盤 ↑／↓；卡片不加常駐按鈕（Rev.2 依 Codex 意見調整，待 Gate 確認） |
| D6 | 自選頁標題 | 「我的自選」（沿用 Phase 3 占位標題） |

---

### 11.1 PO／GPT Gate 最終決議（2026-10-05，Codex PASS Rev.2.1 後）

| # | 決議 |
|---|---|
| D1 | **全站**修正 6 柱／相關報酬視覺的 0% 為中性色；漲紅、跌綠、0 中性、缺值灰。不得使用美股漲綠跌紅 |
| D2 | Phase 4 不新增 Light Mode；維持 token 化，Light Mode 留 Phase 5 |
| D3 | Detail ♡／♥ 放右上標題列，位於 ✕ 左側 |
| D4 | 新增收藏不顯示 Toast；移除才顯示約 5 秒「已從自選移除　復原」，只復原最近一次 |
| D5 | 兩種排序都保留：按住 ⠿ 拖曳；點一下 ⠿ 開上移／下移／移到最上／移到最下選單 |
| D6 | 自選頁標題「**我的 ETF**」 |

不可回歸：① 台股視覺語意漲紅跌綠；② Active Flow（主動式 ETF 持股異動）不得刪除、弱化或替代。

## 12. 不在 Phase 4 範圍

匯出／匯入、帳號與雲端同步、價格提醒／推播、自選分組、首頁／搜尋／排行的 ♡ 入口、淺色主題、修改分類規則或資料 pipeline。
