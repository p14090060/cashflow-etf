# 第一階段補充｜分類排序、Bottom Nav 方案、拆檔計畫

> 回應三個未決項目：(2) 分類顯示順序、(9) 4 格 vs 5 格 Bottom Nav、(10) 拆檔方案。
> 所有數字為 2026-10-03 直接讀 `index.html` 原始碼與 `data/market.json` 實測。
> **本階段不寫任何程式碼。**

---

## 題 2　分類顯示順序

### 先更正：我上一份說「照檔數排」，那是錯的

查了實際數據後要收回這個建議。三種排序法會給出三種完全不同的結果：

| 分類 | 檔數 | 20 日均量佔比 | 在你的 13 檔精選中 |
|---|---:|---:|---:|
| 主動式 | 32 | **54.4%** | 2 |
| 高股息 | 61 | 23.9% | **6** |
| 市值型 | **8** | 8.5% | 3 |
| 海外／區域 | **62** | 8.3% | **0** |
| 科技半導體 | 10 | 2.7% | 0 |
| 主題型 | 23 | 1.1% | 2 |
| 債券 | 6 | 1.1% | 0 |

兩個關鍵矛盾：

1. **海外／區域檔數最多（62），但成交量只佔 8.3%，而且你自己挑的 13 檔精選裡一檔都沒有。**
   那是長尾，不是重點。
2. **市值型檔數最少（8），卻裝著 0050、006208、006201。**
   台灣人最先認識的 ETF 全在這一疊。

照檔數排的話，**0050 會被排到第 6 疊**。對新手來說這是最糟的排法。

### 建議順序：認知難度由淺到深，熱門度當同層的排序依據

| # | 分類 | 檔數 | 為什麼排這裡 |
|---|---|---:|---|
| 1 | 市值型 | 8 | 「買下整個台股」。0050 是多數人聽過的第一檔 ETF，概念一句話說得完 |
| 2 | 高股息 | 61 | 「領股息」。台灣存股族的入門概念，0056 知名度僅次於 0050 |
| 3 | 主動式 | 32 | 成交量 54%，現在最熱。但「有經理人在選股」比前兩個難一階 |
| 4 | 科技半導體 | 10 | 具體、看得懂的產業主題 |
| 5 | 海外／區域 | 62 | 需要先有「分散市場」的概念才有意義 |
| 6 | 主題型 | 23 | 最窄、最需要自己判斷 |
| 7 | 債券 | 6 | 不同資產類別，通常是比較後面才接觸 |

### 比排序更有效的一件事：每疊加一句白話副標

分類名稱本身對新手幫助有限。建議每張卡片標題下加一行說明：

| 分類 | 副標 |
|---|---|
| 市值型 | 一次買下台股最大的那幾十家 |
| 高股息 | 以領配息為主要目的 |
| 主動式 | 由經理人選股，不追蹤指數 |
| 科技半導體 | 押注台灣最強的那個產業 |
| 海外／區域 | 把錢分到台灣以外的市場 |
| 主題型 | 鎖定單一趨勢，波動通常較大 |
| 債券 | 波動較小，常用來平衡股票部位 |

這比排序本身更能降低認知負擔。

---

## 題 9　Bottom Navigation：4 格 vs 5 格

### 先排除一個站不住的論點

**觸控面積不是問題。** 查過現有 CSS：`.bottom-nav` 是 `max-width:430px`、每格 `flex:1`。

- 5 格 → 每格 86px（430px 時）／78px（390px 手機）
- 4 格 → 每格 107px／97px

兩者都遠超過 44px 的最小觸控目標建議值。**所以不要拿「5 格太擠」當理由**，那不是真的差別。

真正的差別是**語意**。

### 方案 A：4 格（首頁／分類／自選／工具）

**優點**

- 四格全部是「在網站裡移動」，心智模型一致
- 少一個選擇，符合「不用看說明也知道按哪裡」
- 之後要加功能還有餘裕

**缺點**

- 頻道從「隨時看得到」變成「要找一下」
- 如果把頻道收進「工具」，工具頁就變成混裝：網站功能 ＋ 外部連結

### 方案 B：5 格含頻道（首頁／分類／自選／工具／頻道）

**優點**

- 頻道永遠在視線內，轉換入口最大化
- 符合這個網站的實際目的（免費工具導流到 YouTube）

**缺點**

- **導覽列裡混進一個「出口」。** 其他四格都是切換站內畫面，頻道是離站。
  使用者對 bottom nav 的預期是「換頁」，不是「離開網站」。
- 新手可能誤讀。「頻道」兩個字在 ETF 網站的語境下，有機會被當成某種分類
  （例如以為是某種 ETF 類型），點進去發現是 YouTube 會有落差感。
- 佔掉最後一格，之後要再加功能就得重新洗牌。

### 建議：方案 A，但頻道要有補償性曝光

重點不是把頻道降級，是**換到更會被點的位置**：

1. **右上角固定 YouTube icon**（與 Light/Dark 切換並排）— 全站都在，一直看得到
2. **首頁最下方一張卡**：「看影片解析 → 金流黑盒子」
3. **工具頁最下方**再放一條

理由：bottom nav 的點擊多半發生在「我要去別的地方做事」的當下，那個心態不會想看影片。
反而是**使用者看完內容、滑到頁面底部**的那一刻轉換意願最高。
放在那裡的實際點擊，有機會比塞進導覽列更多。

> **但這是推論，不是實測。** 我沒有這個網站的流量數據。
> 如果你有 GA 或任何頻道頁的點擊統計，拿出來看會比任何 UX 論證都準。
> 如果現在頻道頁點擊量本來就很低，那保留第 5 格的價值也就不高；
> 如果很高，就該認真考慮方案 B。

---

## 題 10　拆檔方案

### 現況盤點

`index.html` 共 1,863 行，結構其實很乾淨：

```
行 1 –   11    HTML head
行 12 –  516   <style>        505 行（27%）
行 517 – 800   HTML body      284 行（16%）
行 801 –1858   <script>     1,058 行（57%）
行 1859–1863   收尾
```

**零外部資源** — 沒有任何 CDN、網路字型或第三方函式庫。整站自包。

**部署方式：**

- `.github/workflows/` 裡**沒有 Pages 部署 workflow**
  → 是 Settings → Pages 的「Deploy from branch」模式
- 也就是說 **main 分支根目錄的內容就是線上網站**，沒有任何建置步驟
- 資料不從 Pages 讀，是直接抓
  `raw.githubusercontent.com/p14090060/cashflow-etf/main/data/market.json?t=`
  （用時間戳記繞過快取）

### ⚠ 最大的地雷：25 個行內 onclick

HTML 裡有 **25 個 `onclick="..."`**，呼叫 16 個全域函式：

```
switchPage ×5, setRate ×3, setDCA ×2, updateRate, selChip,
runHoldingCheck, runCalc, reloadData, openFlow, lookupToday,
lookupCustom, flowTap, flowSelect, findInRank, clearRankFind
```

**如果拆成 ES module（`<script type="module" src="app.js">`），這 25 個全部會失效。**
因為 module 有自己的作用域，`onclick="switchPage('today')"` 找的是 `window.switchPage`，
而 module 裡宣告的函式不會掛到 window 上。

而且**壞法很隱蔽**：頁面照常顯示、版面完全正常、沒有任何錯誤提示，
只有點下去沒反應，加上 console 一行 `switchPage is not defined`。
如果沒有逐一點過每個按鈕，很容易上線了才發現。

**兩種解法：**

| 作法 | 說明 | 風險 |
|---|---|---|
| (a) 傳統 `<script src="...">` | 不加 `type="module"`，函式自動成為全域，25 個 onclick 全部照常運作 | **低** |
| (b) 改用 module ＋ addEventListener | 要同時改 HTML 與 JS，移除全部行內事件 | 高 |

**建議走 (a)。** 這次是 UI 重構，不是 JS 現代化；兩件事混在一起會讓問題難以歸因。

### 建議的檔案結構

```
index.html              ~300 行，只留 HTML 結構
├─ css/
│   ├─ base.css         設計 token、排版、Light/Dark 主題
│   ├─ components.css   卡片、導覽列、表格、按鈕
│   └─ pages.css        各頁專屬樣式
└─ js/
    ├─ data.js          抓 market.json / active_flow.json、快取、fallback
    ├─ format.js        數字、日期、漲跌顏色等工具函式
    ├─ nav.js           switchPage、路由、底部導覽
    ├─ page-home.js
    ├─ page-category.js
    ├─ page-detail.js   ETF 詳細頁（新增）
    ├─ page-tools.js
    └─ flow.js          主動式 ETF treemap（目前最複雜的一塊）
```

載入方式（**關鍵，不要寫成 module**）：

```html
<link rel="stylesheet" href="css/base.css?v=20261003">
<link rel="stylesheet" href="css/components.css?v=20261003">
<link rel="stylesheet" href="css/pages.css?v=20261003">
...
<script src="js/data.js?v=20261003"></script>
<script src="js/format.js?v=20261003"></script>
<script src="js/nav.js?v=20261003"></script>
<script src="js/page-home.js?v=20261003"></script>
...
```

### 相依關係

```
data.js      ← 無相依（最先載入）
format.js    ← 無相依
nav.js       ← 需要 data.js
page-*.js    ← 需要 data.js、format.js、nav.js
flow.js      ← 需要 data.js、format.js
```

依這個順序放 `<script>` 標籤即可，不需要任何打包工具。

### GitHub Pages 影響

- **沒有建置步驟，所以沒有任何部署流程需要修改。** 多檔靜態網站 Pages 原生支援。
- **路徑一律用相對路徑**（`css/base.css`），**不要用開頭的斜線**（`/css/base.css`）。
  因為站台在子路徑 `/cashflow-etf/` 之下，開頭斜線會指到網域根目錄而 404。
  這是這個部署模式最常見的錯誤。
- 新檔案第一次推上去後，Pages 大約 1～2 分鐘生效。
- **快取**：根目錄的 `_headers` 檔在 GitHub Pages **完全沒有作用**
  （那是 Netlify / Cloudflare Pages 的格式）。
  目前是靠資料網址後面的 `?t=` 時間戳記在繞快取。
  拆檔後 CSS/JS 也會有同樣問題，所以上面範例都加了 `?v=20261003`，
  改版時換掉這個數字即可強制更新。

### 回滾方式

因為 Pages 直接吃 main 根目錄，回滾就是純 git 操作：

```bash
# 方法 1：整包還原拆檔那次變更（最乾淨）
git revert <拆檔的 commit sha>
git push

# 方法 2：只把 index.html 拉回單檔版本
git checkout <拆檔前的 sha> -- index.html
git commit -m "revert: 回到單檔版本"
git push
```

**建議的保險做法：**

1. 拆檔前先打 tag：`git tag pre-split && git push origin pre-split`
   之後只要 `git checkout pre-split -- index.html` 就能一行還原。
2. **拆檔獨立成一個 commit，不要跟任何功能改動混在一起。** 這樣 revert 才乾淨。
3. 拆完先推一次、確認線上正常，再開始做 UI 改動。

### 確認拆檔不影響資料與計算

這是你要求先確認的部分。拆檔是**純文字搬移，不改任何一行邏輯**。驗證方式：

1. **字元級比對**：把拆後所有 JS 檔串接起來，與拆前的 `<script>` 內容比對，
   確認差異只有空白與檔案順序。
2. **四個資料入口完全不動**：
   - `raw.githubusercontent.com/.../data/market.json?t=`
   - `raw.githubusercontent.com/.../data/active_flow.json?t=`
   - `data/active_flow.json?t=`（相對路徑那條）
   - `data.json`（fallback）
3. **Python 端完全不碰**。已確認 `fetch_etf.py`、`scripts/*.py` 與四個 workflow
   （fetch / update-data / dividend-update / validate-freq）
   **沒有任何一個讀寫 `index.html`**，所以拆檔不可能影響資料產生或計算。

### 順帶發現：一個該一起處理的東西

根目錄的 `data.json` **最後更新是 2026-05-13，已經 5 個月沒動**，
但 `index.html` 第 802 行還留著它當 fallback（註解寫「data.json 抓失敗時使用」）。

如果主資料來源真的掛掉而 fallback 生效，使用者會看到 5 月的舊價格，
**而且畫面上沒有任何提示**。

這不在 UI 重構範圍內，但拆檔時一定會碰到那段程式碼，建議順手決定：

- 要嘛讓排程一起更新 `data.json`
- 要嘛移除 fallback，改成顯示「資料暫時無法取得」

---

## 本階段待拍板

1. 分類順序採「認知難度」排法（市值型 → 高股息 → 主動式 → 科技半導體 → 海外／區域 → 主題型 → 債券）？
2. Bottom Nav 採 4 格 ＋ 頻道補償曝光，還是 5 格含頻道？（如有流量數據請提供）
3. 拆檔是否執行？若執行，確認採傳統 `<script>` 而非 ES module。
4. `data.json` fallback 要更新還是移除？
