# 拆檔執行報告

> 執行日期：2026-10-03
> 範圍：純結構拆檔 ＋ 移除過期備援資料。**沒有任何 UI 變更，沒有任何計算邏輯變更。**
> Commit：`88b481d0`（拆檔）、`fb1666a7`（移除備援）
> 還原點：`git tag pre-split` → `7b83383f`

---

## 執行前的重要更正

你的決策 3 提到「25 個 onclick」。實測後這個數字要修正：

| | 數量 | 說明 |
|---|---:|---|
| **實際會執行的 onclick** | **14** | 需要全域函式，拆檔時必須保證不失聯 |
| 封存、不會執行的 | 11 | 在 `<template id="archived-check">` 裡，對應 JS 也被 `/* */` 整塊註解 |
| 合計（原本的計數） | 25 | |

那 11 個是 2026-09-23 下架的「持倉健檢／財務試算」，HTML 存在 `<template>` 裡不會渲染，
JS 在 `/* ── 健診頁邏輯 ── */` 註解區塊內不會執行。兩邊都原樣保留，這次沒有動。

另外一個發現改變了做法：**`LAZY_WATCHLIST` 寫在「Fallback static data」註解區塊裡，
但它不是備援資料**——`renderAll()` 用它挑便宜訊號（render.js 三處引用）。
如果照字面把那個區塊整個刪掉，首頁的「值得留意 ETF」會直接壞掉。已保留。

---

## 1. 實際檔案結構

```
index.html              315 行   14,890 bytes   只剩 HTML 結構
├─ css/
│   ├─ base.css          97 行    4,941 bytes   設計 token、頂欄、頁面容器、底部導覽
│   ├─ components.css   218 行   11,309 bytes   卡片、情緒、訊號、配息頁、計算機、行事曆
│   └─ pages.css        201 行   15,265 bytes   頻道頁、主動頁、排行頁、treemap
└─ js/                                          （載入順序＝原始行序，不可調動）
    ├─ config.js         20 行      946 bytes   LAZY_WATCHLIST
    ├─ nav.js            17 行      992 bytes   switchPage
    ├─ flow.js          287 行   16,107 bytes   主動式 ETF 持股異動 treemap
    ├─ archived-check.js 200 行  10,540 bytes   健診頁邏輯（整塊註解，原樣保留）
    ├─ format.js         36 行    1,942 bytes   miniBars、fmtYld、yldBadge
    ├─ calc.js           63 行    4,160 bytes   ETFS 全域、配息 chips、計算機、訊號卡
    ├─ lookup.js         88 行    3,916 bytes   單檔查詢
    ├─ render.js        193 行    9,823 bytes   renderMood、renderAll
    ├─ rank.js          155 行    8,136 bytes   排行頁與站內搜尋
    └─ boot.js           60 行    2,922 bytes   開場抓資料、30 秒輪詢、錯誤處理
```

**拆前**：`index.html` 單檔 1,863 行 / 99,539 bytes
**拆後**：14 個檔 / 105,889 bytes（+6,350 來自每個檔的來源註解與新增的錯誤處理）

### 載入方式

```html
<link rel="stylesheet" href="css/base.css?v=20261003">
<link rel="stylesheet" href="css/components.css?v=20261003">
<link rel="stylesheet" href="css/pages.css?v=20261003">
...
<!-- 順序即相依順序，不可調動；一律傳統 script，不要 type="module" -->
<script src="js/config.js?v=20261003"></script>
<script src="js/nav.js?v=20261003"></script>
<script src="js/flow.js?v=20261003"></script>
<script src="js/archived-check.js?v=20261003"></script>
<script src="js/format.js?v=20261003"></script>
<script src="js/calc.js?v=20261003"></script>
<script src="js/lookup.js?v=20261003"></script>
<script src="js/render.js?v=20261003"></script>
<script src="js/rank.js?v=20261003"></script>
<script src="js/boot.js?v=20261003"></script>
```

**全部是傳統 `<script>`，沒有 `type="module"`**，依決策 3 執行。

### 為什麼切點不能重排

原始碼有 6 處頂層立即執行的語句，順序一動就會壞：

| 原始行 | 內容 | 落在 |
|---:|---|---|
| 1125 | `window.addEventListener('resize', …)` | flow.js |
| 1379 | `getElementById('sharesIn').addEventListener('input', calcUpdate)` | calc.js |
| 1495 | `getElementById('customCode').addEventListener('keydown', …)` | lookup.js |
| 1496 | `getElementById('todayCode').addEventListener('keydown', …)` | lookup.js |
| 1845 | `fetchFlow().then(d => { if (d) renderRank(); })` | boot.js |
| 1858 | `fetchData()` | boot.js |

切點嚴格照原始行序，`<script>` 順序＝原始順序。
這是「執行結果不變」的證明基礎：原本解析得到的識別字，拆後仍在同一個相對順序上被定義。

---

## 2. 是否所有原功能正常

**狀態：靜態檢查全部通過；執行期行為未驗證。**

這台機器上沒有任何 JavaScript 引擎（node / deno / bun / qjs 都沒有，
也沒有 quickjs、py_mini_racer 之類的 Python 綁定），所以**我無法實際執行這些程式碼**。
以下是能做到的靜態驗證：

| 檢查項目 | 方法 | 結果 |
|---|---|---|
| 內容完全沒變 | 把拆出的檔案串回來，與拆前逐字元比對 | ✅ CSS 28,586 字元、JS 48,471 字元，完全相同 |
| 每個檔自己是完整的 | 去除字串與註解後計算 `{} () []` 收支 | ✅ 13 個檔全部收斂為 0 |
| 沒有跨檔重複宣告 | 掃描所有頂層 `function` / `const` / `let` / `var` | ✅ 0 個重複 |
| 頂層 DOM 操作的 id 存在 | 比對 `getElementById(...).addEventListener` 與 HTML 的 id | ✅ sharesIn、customCode、todayCode 都在 |

> **為什麼「沒有跨檔重複宣告」特別重要**：傳統 `<script>` 之間共用同一個全域詞法作用域。
> 兩個檔各宣告一次 `let ETFS` 會直接 `SyntaxError: Identifier 'ETFS' has already been declared`，
> 而且後面所有 script 都不會執行。這是多檔化最容易炸、也最難從畫面看出原因的錯誤。

**還需要人工確認的部分見本報告最後的「待你點一遍的清單」。**

---

## 3. 14 個生效 onclick 是否全部正常

**靜態檢查：全部對得上定義檔。**

| 函式 | 次數 | 寫在哪 | 定義在哪 |
|---|---:|---|---|
| `switchPage` | 5 | index.html | js/nav.js |
| `reloadData` | 1 | index.html | js/boot.js |
| `lookupToday` | 1 | index.html | js/lookup.js |
| `lookupCustom` | 1 | index.html | js/lookup.js |
| `findInRank` | 1 | index.html | js/rank.js |
| `clearRankFind` | 1 | index.html | js/rank.js |
| `flowSelect` | 1 | js/flow.js（動態產生的 HTML 字串） | js/flow.js |
| `flowTap` | 1 | js/flow.js（同上） | js/flow.js |
| `selChip` | 1 | js/calc.js（同上） | js/calc.js |
| `openFlow` | 1 | js/rank.js（同上） | js/boot.js |

注意最後一列：`openFlow` 在 **rank.js** 產生的 HTML 裡被引用，但定義在 **boot.js**。
因為兩者都是全域函式、而且點擊發生在載入完成之後，所以沒問題——
**但如果改成 ES module 就會壞**，這也是維持傳統 `<script>` 的理由之一。

封存未執行的 11 個（`setRate` ×3、`setDCA` ×2、`runHoldingCheck`、`updateRate`、`runCalc`、
以及 3 個行內 `if`）維持原狀，沒有動。

---

## 4. 資料載入是否正常

程式讀的四個入口，**拆檔完全沒有更動**：

| 入口 | 狀態 |
|---|---|
| `raw.githubusercontent.com/.../data/market.json?t=` | ✅ HTTP 200，JSON 可解析，`updated=2026-10-02 21:45`，**203 檔**，含 calendar |
| `raw.githubusercontent.com/.../data/active_flow.json?t=` | ✅ HTTP 200，JSON 可解析，`updated=2026-10-02 21:42`，**32 檔** |
| `data/active_flow.json?t=`（相對路徑那條） | 未更動 |
| `data.json`（舊 fallback） | **已不再使用**，見第 6 節 |

Python 端完全沒碰：`fetch_etf.py`、`scripts/*.py`、
四個 workflow（fetch / update-data / dividend-update / validate-freq）
**沒有任何一個讀寫 `index.html`**，所以拆檔不可能影響資料產生或計算。

---

## 5. GitHub Pages 線上版本是否正常

部署在推送後約 **40 秒**生效（Deploy from branch 模式，無建置步驟）。

全部 14 個資源實測：

```
index.html             200  14,575 bytes  text/html
css/base.css           200   4,844 bytes  text/css
css/components.css     200  11,091 bytes  text/css
css/pages.css          200  15,064 bytes  text/css
js/config.js           200     926 bytes  application/javascript
js/nav.js              200     975 bytes  application/javascript
js/flow.js             200  15,820 bytes  application/javascript
js/archived-check.js   200  10,340 bytes  application/javascript
js/format.js           200   1,906 bytes  application/javascript
js/calc.js             200   4,097 bytes  application/javascript
js/lookup.js           200   3,828 bytes  application/javascript
js/render.js           200   9,630 bytes  application/javascript
js/rank.js             200   7,981 bytes  application/javascript
js/boot.js             200   2,862 bytes  application/javascript
```

**零 404**，MIME type 全部正確。

### 內容一致性的額外佐證

每一個檔案都滿足：`線上 bytes ＝ 本機 bytes − 行數`
（例：base.css 4,941 − 97 行 ＝ 4,844）。
差值正好等於行數，代表只有 Windows 本機的 CRLF 與伺服器端 LF 的換行差異，
**內容逐字元相同**。14 個檔案全部符合。

### 相對路徑已驗證

站台在子路徑 `/cashflow-etf/` 下，所有資源都用相對路徑（`css/base.css`），
線上實測可正常取得。沒有使用會導致 404 的開頭斜線寫法。

---

## 6. 移除過期備援資料（決策 4）

### 原本的行為

`market.json` 抓失敗時會改畫寫死的 `STATIC_ETFS`：

```js
{ code:'0050', name:'元大台灣50', price:175.3, ma60:172.1, yld:4.2, signal:'fair', … }
{ code:'0056', name:'元大高股息', price:35.2,  ma60:33.8,  yld:6.3, signal:'cheap', … }
```

行事曆 `STATIC_CAL` 則停在 5 月。更新時間欄位雖然會寫「示範資料」，
但**價格、殖利率、訊號全是假的，畫面上跟真的一模一樣**。

### 補充更正

你的決策 4 寫「data.json 過期 fallback」。實際上機制不是 data.json ——
**根目錄的 `data.json` 從頭到尾沒有被程式讀過**，
只出現在一行過期註解裡（`// ── Fallback static data（data.json 抓失敗時使用）──`），
真正會被畫上畫面的是寫死在 JS 裡的 `STATIC_ETFS`。
那個 `data.json` 檔最後更新是 2026-05-13，是個孤兒檔。

### 改成什麼

| 情況 | 新行為 |
|---|---|
| 從沒載入成功過 | 畫面保持空白，不填任何數字。橫幅顯示「⚠ 資料暫時無法取得。可能是網路問題或資料來源暫時中斷，請稍後按右上角 ↻ 重新整理。」狀態列變成「資料載入失敗」 |
| 載入過之後才失敗（30 秒輪詢） | 保留已載入的內容，但橫幅明說「⚠ 目前無法更新，以下是 `<時間>` 的資料，不是現在的狀況。」 |

第二種情況是刻意的：已經載入的資料對使用者仍有用，直接清空反而更糟；
重點是**不讓它冒充成現在的狀況**，所以標明時間。

### 順帶修掉一個沉默的失敗

```js
// 改之前
.then(r => r.json())
// 改之後
.then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
```

`fetch()` 只有在網路層失敗時才 reject；**404 / 500 會正常進 `.then()`**，
然後在 `r.json()` 解析 HTML 錯誤頁時才爆掉，變成另一種看不懂的錯誤。

### 動到的檔案

| 檔案 | 變更 |
|---|---|
| `js/config.js` | 刪除 `STATIC_ETFS`、`STATIC_CAL`（36 → 21 行）。**保留 `LAZY_WATCHLIST`** |
| `js/calc.js` | `let ETFS = STATIC_ETFS` → `let ETFS = []` |
| `js/boot.js` | 新增 `showDataError()` / `hideDataError()`，改寫 `fetchData()` |
| `css/base.css` | 新增 `.status-error`、`.data-error`（**刻意不加任何 animation**） |
| `index.html` | 新增 `<div class="data-error" id="dataError" hidden></div>` |

已驗證 `ETFS` 改成空陣列不會讓開場的 `renderRank()` 出錯
（`[...[]].filter(…)` 只會得到 0 筆，不會丟例外）。

---

## 沒有做的事

- ❌ 沒有任何 UI 變更（版面、顏色、文案、分頁結構全部維持原狀）
- ❌ 沒有改任何計算邏輯
- ❌ 沒有做 ES module 化
- ❌ 沒有刪除 `data.json`（它確實沒用到，但刪檔不在這次授權範圍）
- ❌ 沒有動 `<template id="archived-check">` 與對應的註解區塊

---

## 待你點一遍的清單

這台沒有瀏覽器也沒有 JS 引擎，**「功能實際運作」與「console 有無錯誤」只能由你確認**。
用手機或電腦開 <https://p14090060.github.io/cashflow-etf/>，照下面點一遍，約 2 分鐘：

**第一件事：開 console**（電腦版 F12 → Console 分頁）。
如果有 `SyntaxError` 或 `xxx is not defined`，請把整行貼給我。

| # | 動作 | 應該看到 |
|---|---|---|
| 1 | 進站 | 市場情緒卡有數字、「值得留意 ETF」有卡片、「今日熱門 TOP 10」有列表 |
| 2 | 底部切換五個分頁 | 今日／配息／頻道／主動／排行 都能切，內容都有東西 |
| 3 | 今日頁輸入 `00692` 按查詢 | 出現該檔的訊號卡 |
| 4 | 配息頁點任一個 ETF chip | 下方配息計算更新 |
| 5 | 配息頁改「我有 ? 張」 | 數字即時跟著變（這條驗 `sharesIn` 的 input 監聽） |
| 6 | 配息頁輸入 `00878` 按查詢 | 出現配息資訊 |
| 7 | 主動頁點不同 ETF 代碼 | treemap 重畫 |
| 8 | 主動頁點 treemap 任一方塊 | 跳出該檔明細 |
| 9 | 排行頁搜尋框打 `0056` | 該列被標出來 |
| 10 | 排行頁按清除 | 標記消失 |
| 11 | 排行頁點有 PCF 的 ETF（如 00981A） | 跳到主動頁並顯示該檔 |
| 12 | 右上角 ↻ | 整頁重載 |
| 13 | 轉橫向／縮放視窗 | treemap 跟著重畫 |

第 5、11、13 項是拆檔最容易壞的三條
（分別是頂層 addEventListener、跨檔全域函式、resize 監聽），請務必測到。

---

## 如果有問題，怎麼回滾

```bash
# 整包還原（最乾淨）
git revert fb1666a7 88b481d0
git push

# 或直接回到單檔版本
git checkout pre-split -- index.html
git rm -r --cached css js && rm -rf css js
git commit -m "revert: 回到單檔版本"
git push
```

`pre-split` tag 已推到遠端，隨時可用。

---

## 確認通過後的下一步

上面 13 項都正常、console 乾淨之後，才進 UI 重構。
依先前拍板的內容，第一階段會是：

1. 全站頂部固定搜尋（取代現在四個各自獨立的代碼輸入框）
2. ETF 詳細頁（「目前這一檔」的唯一容器）
3. 分類頁（7 疊，順序：市值型 → 高股息 → 主動式 → 科技半導體 → 海外／區域 → 主題型 → 債券）
4. Bottom Nav 改 4 格 ＋ 頻道補償曝光
5. Light / Dark Mode
