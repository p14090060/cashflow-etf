# ETF 存股雷達

靜態 PWA，每日從 TWSE + yfinance + FinMind 抓資料，GitHub Action 自動更新，GitHub Pages 自動部署。

## 🚨 靜態資料填寫鐵則（Claude 必須遵守）

> 適用範圍：`dividend_info.json`、`_YLD_OVERRIDE`、任何人工維護的靜態欄位

1. **單源查無 → 必須 WebSearch 查證**：程式抓不到資料，不代表資料不存在。上網（goodinfo / moneydj / cmoney / 投信官網）查得到就填查到的，查不到才說查不到。
2. **WebSearch 也查無 → TG 通知 Gavin，顯示 `--`**：不可用模型記憶、不可憑感覺估填、不可隨意寫預設值佔位。
3. **填之前必須說明來源**：告訴 Gavin「從哪個網站查到什麼數字」，不能只說「已填入」。
4. **查到資料才能設 `_todo: false`**：沒有實際查證就設 false 等於造假。

## 核心檔案

| 檔案 | 用途 |
|---|---|
| `index.html` | 前端 PWA（純 HTML/JS，無框架） |
| `fetch_etf.py` | 每日基礎資料抓取（yfinance + TWSE + FinMind） |
| `scripts/mis_fetcher.py` | 盤中即時行情更新 |
| `scripts/daily_check.py` | 每日資料核對 + Telegram 通知（6 項異常檢查） |
| `scripts/intraday_notify.py` | 盤中固定時間點推播 LAZY_WATCHLIST 便宜訊號 |
| `scripts/fetch_dividend_calendar.py` | 配息行事曆抓取 |
| `data/_base.json` | fetch_etf.py 產出（不手動編輯） |
| `data/market.json` | mis_fetcher.py 產出，**前端讀這個** |
| `data/dividend_calendar.json` | 配息行事曆資料 |
| `.github/workflows/fetch.yml` | 每日 08:30 + 15:00 自動排程 |
| `.github/workflows/update-data.yml` | 盤中每 10 分鐘更新 market.json（由 cron-job.org 觸發） |

## 兩階段 Action 架構

1. `fetch.yml` → 跑 `fetch_etf.py` → 產出 `data/_base.json`
2. `update-data.yml` → 跑 `mis_fetcher.py` → 合併 _base.json → 產出 `data/market.json` → 跑 `intraday_notify.py`

**前端只讀 `data/market.json`**，改完 fetch_etf.py 要先觸發 fetch.yml，再觸發 update-data.yml 才會反映。

## cron-job.org 觸發設定（2026-05-25）

GitHub Actions 內建 cron 有 5～30 分鐘隨機延遲，改用 cron-job.org 精確觸發：

- **帳號**：p14090060（GitHub 帳號登入）
- **Job**：ETF update-data 每10分
- **排程**：`*/10 9-13 * * 1-5`（Asia/Taipei，台北 09:00～13:59，週一至週五）
- **觸發方式**：POST `https://api.github.com/repos/p14090060/cashflow-etf/actions/workflows/update-data.yml/dispatches`
- **is_trading_hour 邊界**：`scripts/mis_fetcher.py` 上限改為 13:35（`<= 815`），讓 13:35 那次能抓到收盤現價與大盤漲幅

## 文案規範

- **禁用**「買進/賣出/觀望/建議」等動作指令
- **改用**「合理價區/熱門排行/留意風險」等狀態描述
- 品牌調性：多用「資金/水/流向」意象

## 頁面區塊代號（溝通用，不顯示在 APP）

> Phase 5（2026-10，CP8 文件 closeout）後的實際結構：底部導覽 **首頁／分類／自選／工具** 四個分頁，
> 加上全站共用的 Header（標題＋資料狀態、YouTube 品牌 Logo、☀／🌙 主題鈕、↻）、Header 全站搜尋與 ETF Detail 面板。
> 代號沿用舊編號（舊 Tab 編號已不對應畫面位置），退役者保留刪除線備查。

### 首頁（底部導覽「首頁」，`page-today`）
| 代號 | 說明 |
|---|---|
| A-1 | 大盤現況（mood-card：大盤漲跌＋情緒；加權漲跌幅紅漲綠跌） |
| A-E | 兩大入口：「我想看看 ETF」→ 分類、「我已經有 ETF」→ 我的 ETF（Phase 5；藍＝探索、綠＝已持有） |
| A-2 | 價格合理區（成交量前 100 中 cheap／fair 且配息型；cheap 先、同狀態依成交量；>10 檔可展開；0 檔不補位、顯示「目前沒有 ETF 符合價格條件」；不用 LAZY_WATCHLIST） |
| A-3 | 今日成交量 TOP 10（`cur_vol` 排序，非推薦清單；整列開 Detail） |
| ~~A-4~~ | ~~查詢其他 ETF~~（Phase 5 退役，改用 Header 全站搜尋） |

### 分類（底部導覽「分類」，`page-cat`）
| 代號 | 說明 |
|---|---|
| — | 分類總覽（8 份文件夾）→ 進入分類清單（排序、查看更多、整列開 Detail、♡ 收藏）；主動式分類另有「持股異動」分段（D-1 原生入口） |

### 自選（底部導覽「自選」，`page-watch`）
| 代號 | 說明 |
|---|---|
| — | 我的 ETF：♡ 收藏的自選大卡（近半年 6 柱、台股漲紅跌綠）、⠿ 拖曳／移動選單排序、取消後可復原；空狀態引導去分類；只存 localStorage |

### 工具（底部導覽「工具」，`page-tools`）：三張功能卡，各開一個子頁
| 代號 | 說明 |
|---|---|
| E-1 | 成交量排行（`page-rank`，見下方「排行頁」） |
| B-2 | 配息日曆（`page-div`） |
| D-1 | 主動式 ETF 持股異動（Flow 層；見下方「主動頁」） |
| ~~B-1~~ | ~~配息計算機~~（Phase 5 退役；張數試算在 ETF Detail 配息分頁） |
| ~~C-1~~ | ~~頻道介紹卡~~（Phase 5 退役：`page-yt` 移除，改為 Header 右上 YouTube 品牌 Logo 直接開外部頻道） |
| ~~C-2~~ | ~~最新影片連結~~（同上） |
| ~~C-3~~ | ~~今日股市笑話~~（隨頻道頁移除，前端已無此區塊） |

### 主動頁（D-1；入口：工具卡、排行「持股異動」、Detail、分類主動式）
| 代號 | 說明 |
|---|---|
| D-1 | **單檔**主動式 ETF 的當日持股異動 treemap（面積＝金額、**紅加碼綠減碼**＝台股慣例、格內顯示張數） |

資料由 `scripts/fetch_active_etf.py` 產生 `data/active_flow.json`：
抓各投信官網公告的 **PCF 申購買回清單**（法規要求主動式 ETF 每日開盤前揭露全部持股），
加減碼 =（本次股數 − 前一份快照股數）× **該資料日**的 TWSE／TPEx 官方收盤價。

**刻意不做跨 ETF 彙總。** 彙總數字會在畫面上長得像「全市場主動圈結論」，
只要還有投信接不到就等於騙人（同 2026-05 砍掉「月月都有錢領」的毛病）。
單檔版在任何涵蓋率下都誠實：接得到就顯示，接不到就不出現在 chips 裡。

- 排行頁只有**有 Active Flow 資料的那幾檔**出現「持股異動」按鈕（`.rank-row.has-flow` + `.rank-flow`；整列其他位置開 Detail）
- `advanced:false` 代表這檔 PCF 這次沒出新的，和「有出新的但持股沒動」是兩種狀態，
  前端必須分開顯示，不要混為一談
- **這是兩份公開快照相減的推估值，不等於基金實際成交**，前端已標註，不要拿掉那段警語
- 抓不到的 ETF **保留上一次的換檔結果**（`fetched:false` + `last_change_date`），
  絕不讓它從畫面消失——使用者看到的會是「我買的那檔不見了」

#### 已接的投信（2026-10-02：32 檔 / 16 家，**全市場覆蓋**）
統一 4、中信 3、群益 3、野村 3、安聯 3、台新 2、復華 3、第一金 2、摩根 2、
永豐 1、凱基 1、富邦 1、兆豐 1、元大 1、國泰 1、聯博 1

排行榜認定的主動式 ETF 共 30 檔**全部接完**，另加不在那份名單內的 00411A。
復華 00998A 主動復華金融股息（53 檔全海外）2026-10-02 補進來——它一直抓得到，
是被 adapter 的「非台股就丟掉」那行濾掉的，見下面〈海外持股可能在 adapter
就被丟掉〉。只有 00986D 主動復華金融債息仍不輸出（債券 ISIN，不是股票）。

新增一家投信＝新增一個 `fetch_xxx(date_obj, specific=False)` adapter，回傳
`{ticker: {name, issuer, data_date, holdings: {code: {name, shares}}}}`，再掛進 `ADAPTERS`。
`specific=True` 用於回補前一份（快照裡沒有的 ETF 會自動觸發，所以新接投信當天就有數字）。

**踩過的坑，加新 adapter 前先看：**
- ⚠ **「公告日 ≠ 資料日」已經踩 6 次**（凱基 `DataDate`、中信 公告日、群益 `pcf.date1`、
  安聯 `PCFDate`、兆豐、第一金 `pStrDate`）。API 給的常是**未來的交割公告日**，
  真正的資料日要看 NAV 日／`date2`／淨值日期／回傳的 `sdate`。**一律以回傳值為準，
  不要相信自己送出去的日期。**
- ⚠ **「PCF 頁沒有成分股」≠「這家沒公開持股」**。富邦在 `Fund/Assets.aspx`、
  復華只在 Excel 下載連結裡、第一金只在 `WebAPI.aspx/Get_hd`（頁面那張表只有比重沒股數）。
- ⚠ 回應編碼會飄（第一金 UTF-8／Big5 都出現過），先試 utf-8 再退 cp950。
- ⚠ 兆豐的 `category_id` 下拉選單是陷阱：先送它篩「主動式ETF」反而會把 `fund_id`
  的 `<option>` 清空，初始頁本來就列齊了，直接送 `fund_id` 就好。
- 國泰 `cwapi.cathaysite.com.tw/api/ETF/GetETFDetailStockList`，
  參數 `FundCode=EA` + **`SearchDate`**（不是 `date`），股數欄位叫 **`volumn`**；
  資料日預設取 `GetETFAssets` 的 `preDate`，非交易日回空陣列不會給錯日期。
- 聯博 `webapi.alliancebernstein.com/v2/funds/tw/zh-tw/investor/<ISIN>/holdings?date=`，
  取 `domesticHoldings` 裡 `holdings-section-equity` 那段；
  ⚠ 同基金的 `/basket` 端點 `date` 是**公告日**，別拿它的日期當資料日。
- 摩根走 `FundsMarketingHandler/product-data`，**`role` 只有 `twetf` 會過**
  （per/ins/adv/retail 都回 "Country/Role combination is not supported by FMA"）；
  `cusip` 就是 ISIN。難得沒有公告日陷阱，`effectiveDate` 直接是資料日。
- 元大是 Nuxt SPA，但持股 SSR 在 `window.__NUXT__` 的 `StockWeights` 裡，
  欄位值常是 minified 變數（`_nuxt_vars` 負責還原）；資料日用 DOM 上那個「交易日期」。
- ⚠ 海外持股查無台股報價會被靜默略過 → 一定要進 `no_price` 並印 `[WARN]`。
- ⚠ **輸出的判斷是 `advanced and (changed or no_price)`，不能只看 `changed`。**
  `changed` 只計「查得到台股收盤價」的異動，所以**台股持股 0 檔**的 ETF
  （00983A 中信ARK、00989A 摩根美國科技、00402A 安聯美國科技）永遠是 0；
  而 `no_price` 以前寫在同一個 `if` 裡，會跟著落空 → 整筆換股不留痕跡。
  2026-09-30 用 git 歷史比對原始快照才抓到：**00989A 09/23→09/24 換了 37 檔**，
  畫面上卻完全空白。查「有沒有漏」的方法就是拿舊 commit 的
  `_active_snapshot.json` 逐版比對股數，不要只看 `active_flow.json` 的結論。
- 認證花招：統一 session cookie、中信 bootstrap token `"www.ctbcinvestments.com"`
  → `home/AuthToken`、安聯 `X-XSRF-TOKEN`（來自 `AntiForgery/GetAntiForgeryToken`）。

**不可用來源**：`etfinfo.tw`（robots.txt `Disallow: /api/`、使用條款禁爬禁再利用）、
`nctuwanglin/active-etf`（無授權條款）。台灣**沒有**集中式的主動式 ETF 持股揭露，
TWSE `ETFortune/etfInfo` 與 TPEx `serial_active_etf` 都只有彙總頁。

#### ⚠ 2026-09-27 我把國泰誤判成「沒有股數」，Gavin 截圖打臉
官網持股權重頁明明就有股數欄。三個誤判環節，之後查任何一家都要避開：
1. 拿 `GetIndexStockWeights` 當持股 —— 那是**指數成分權重**不是基金持股，
   本來就沒股數，我卻拿它下結論。
2. `BuySale/GetStocksList` 回空陣列（00400A 是現金申購買回、PCF 沒股票籃），
   我把「這支 API 沒資料」讀成「官網沒揭露」。
3. 真正那支 `ETF/GetETFDetailStockList` 我試過，但參數傳成 `date`，
   正確是 **`SearchDate`**，於是回「查無資料」——**參數名錯 ≠ 資料不存在**。

**通則：SPA 要找 API，別在主 bundle 猜。** Angular 看 `runtime.js` 的 chunk 地圖、
Vue/Nuxt 看懶載入 chunk、webpack 看 `i.u=e=>...` 那串，把該 chunk 單獨抓下來
grep 呼叫端，參數名和欄位名會直接寫在那裡（國泰的股數欄位叫 `volumn`，拼錯的）。

#### 海外持股：算不出金額，但一定要列出名稱（2026-10-01）

金額＝`股數變化 × 收盤價`，而收盤價表只接 TWSE MI_INDEX（上市）+ 櫃買（上櫃），
**兩個都是台灣交易所**。持股代碼查不到就進 `no_price`，不硬算。
31 檔裡有 8 檔受影響：全海外 3 檔（00402A／00983A／00989A）、
混合 5 檔（00411A／00986A／00988A／00990A／00997A）。

**算不出的只有「金額」。** 「買賣了哪一支、幾股」PCF 本來就寫得清清楚楚，
所以 `no_price` 存 `{code, name, delta_shares}`，前端在 treemap 下方條列顯示。
代碼格式各家不同：統一給 Bloomberg 式 `TWLO US`／`285A JP`，摩根給純代號
`NVDA`，群益連名稱都給中文（`鎧俠控股公司`）。結尾兩個大寫字母才當市場別。

**⚠ 不要再想「比對名稱來判斷是不是台股」。** 2026-10-01 量過，1158 筆台股
持股有 **58 筆對不上**——投信寫全名、交易所寫簡稱：

| PCF | 交易所 |
|---|---|
| 台灣積體電路製造 | 台積電 |
| 聯華電子 | 聯電 |
| 中國信託金融控股 | 中信金 |
| 南亞電路板 | 南電 |
| 日月光投資控股 | 日月光投控 |

字串上毫無包含關係，而台積電是幾乎每檔台股主動 ETF 的最大持股，出現在 7 檔裡。
**+56 個假警報、+0 個真問題**（那 2 檔真日股靠「台股價格表沒這個碼」就抓到了）。
跟 `confirmed_yld` 同一個教訓：先量，再決定要不要做。

#### 代碼撞號：各市場號碼空間重疊（2026-10-01）

00986A 同時持有台積電 `2330` 與東京 `6981` 村田、`8306` 三菱UFJ，後兩者是
**裸四碼**，在台股代碼空間裡完全合法。今天實測台股 2356 碼沒有這兩碼，
所以沒撞到——但那是運氣。真撞到時 `closes.get("6981")` 會回傳台灣那檔的
收盤價，算出看起來正常、實際張冠李戴的金額，而且沒有任何警告。

更糟的是同檔 ETF 同時持有兩個市場的同一碼：`holdings[code] = {...}`
會讓後者**無聲蓋掉**前者，持股少一檔、名稱消失。
→ `_Holdings(dict)` 子類別在覆寫時記錄並印 `[DUP]`，經 `dup` 欄位併進
`anomaly`，由 daily_check 發 TG。**只偵測、不改行為**（撞號當下仍後者勝）。

#### ⚠ 同一家投信常有兩條路徑，交易頁不一定是比較好的那條（2026-10-02）

00996A 在 Actions 上連續 18 次排程回空、本機正常，卡了 5 個交易日。
後來發現兆豐同時有兩個頁面給同一份持股：

| | `trade_pcf.aspx`（原本用的） | `etf_product.aspx?id=<同一組 fund_id>` |
|---|---|---|
| 取得方式 | ASP.NET POST＋viewstate＋`__EVENTTARGET` postback | **單純 GET** |
| 股數 | 精確 | 精確（逐筆完全吻合） |
| 資料日 | `#div_prev_unit_total` 那行 | 頁面標「持股比重 資料來源：兆豐投信，YYYY/MM/DD」 |
| 歷史查詢 | ✅ `qdt`（bootstrap 回補要用） | ❌ 只有最新 |

**接 adapter 時別只看交易／下載頁。** 商品介紹頁常常是同一份資料的單純 GET 版，
在 CI 上穩得多。現在 trade_pcf 仍是主路徑（為了歷史查詢），拿不到才走商品頁。

> **驗日期標示時小心「今天」。** 商品頁標 2026/10/02，而當天剛好就是 10/02，
> 光看一檔分不出那是資料日還是今天。驗法是**同時看多檔**：實測 id=21/22 標
> 10/01、id=18/19/20/23 標 10/02，會隨基金不同 → 是真的資料日。

已排除的來源：`emega.com.tw`（兆豐證券）的 `api/holdingDetails` 持股對得上，
但**沒有資料日**，而且用「張」只到小數 2 位＝四捨五入到 10 股，
跟 PCF 混用會讓非整張持股天天冒出假異動。

#### ⚠ 「以下為…」必須跟實際畫出來的東西綁在一起（2026-10-02）

沿用舊紀錄的那幾條提示會無條件宣告「以下為最近一次調整」，但沿用的紀錄**可能
本身就是空的**：00983A 中信ARK 從 2026-09-23 開始追蹤起一次換股都沒記錄到
（`flow` 空、`no_price` 空、`last_change_date` 是 `null`），畫面於是變成
「⏳ 以下為最近一次調整」緊接著「目前沒有可顯示的調整紀錄」，自己打自己臉。
→ `hasPrev = flow.length || np` 為真才接「，以下為…」。
同理「面積＝金額」的說明框在沒有 treemap 時要隱藏，全海外那幾檔要換成股數版，
否則是在解釋一張不存在的圖。改完模擬 31 檔，矛盾 0 件。

**查到的事實順便記著**：00983A 的 PCF 是真的沒變。中信每個交易日都公告新檔，
但 09-23／09-24／09-29／09-30 四個公告日內容一字不差（43 檔、股數總和 392,749、
TSLA 7392）。它以前會變（08-18 總和 516,919 → 09-18 405,335），
是 09-23 起凍結，而我們剛好 09-23 開始追蹤。**「畫面沒東西」不一定是程式壞了。**

#### ⚠ 海外持股可能在 adapter 就被丟掉，不是「沒有」（2026-10-02）

上面那條假設 PCF 抓進來的持股是完整的。**`fetch_fuhwa` 不是。** 它解析時
對「非台股代號」無條件 `continue`，00409A 主動復華全球50 的 41 檔海外持股
整批蒸發，畫面只剩 10 檔台股——**一檔「全球50」只顯示 20% 的持股，
而且 `holdings` 有數字、`no_price` 是空的，所有監控都正常。**

> 判斷「這檔有沒有海外持股」不能看 `no_price` 是不是空的，
> 那只代表**解析後**沒有。要看 PCF 原始檔。

同一行還讓 00998A 主動復華金融股息（53 檔全海外）因為「無台股持股」
被整檔略過，從來沒進過追蹤清單。修正後 31 檔 → 32 檔。

保留規則用彭博格式 `^[A-Z0-9][A-Z0-9/.-]{0,7} [A-Z]{2}$`，排除債券 ISIN
（`US89117F8Z56`，12 碼無空格）和表頭。實測 4 檔復華基金 123 種非台股代碼：
收下 93 種全是股票，排除 30 種全是 00986D 金融債的 ISIN 與表頭，**零誤判**。

**其他 adapter 已經掃過了，只有復華有這個問題。** 永豐／凱基／富邦／第一金／
兆豐／國泰 的解析也有同樣的 `continue`，但 2026-10-02 用 shim 攔 `re.fullmatch`
實測（含台新、統一共 8 支）：**被丟掉而長得像海外股票的列＝0 筆**。
它們丟掉的是現金、期貨那類非個股列，那是對的。不用再掃一遍。

**改解析器會讓新舊快照不可比。** `build_flow` 用 `set(before) | set(after)`，
舊快照 11 檔對新的 51 檔會生出 41 筆假加碼。做法是把該檔從
`_active_snapshot.json` 移除，走既有的 BOOTSTRAP 路徑用新解析器重算前一份，
不要另外寫特例。

#### 彭博市場別代碼 ≠ ISO 國碼（2026-10-02）

`_NP_MKT` 原本照 ISO 寫，**`CH` 那條是錯的**：`300757 CH` 是深圳創業板的
中國 A 股（彭博 CH＝China），舊表標成「瑞（士）」。瑞士在彭博是 `SW`。
`KR/GB/DE/FR/NL/CA/AU/SG/TW` 九個 ISO 碼實測一次都沒出現過，是死條目。

實際出現 14 種，每種都用成分股本身的身分核對過：

| 碼 | 市場 | 佐證成分股 |
|---|---|---|
| `US` `JP` `HK` | 美／日／港 | — |
| `CH` | 中國 A 股 | `300757 CH` 深圳創業板 |
| `KS` `KP` | 韓 | `009150 KS`＝`009150 KP` 三星電機，兩家投信寫法不同 |
| `LN` | 英 | `SDLF LN` 標準人壽 |
| `GY` `FP` `IM` `NA` `SM` | 德法義荷西 | `IFX GY` 英飛凌、`AMUN FP` 東方匯理、`UCG IM` 裕信、`ABN NA` 荷蘭銀行、`CABK SM` 凱克薩 |
| `GA` `BB` | 希／比 | `BOCHGR GA` 賽普勒斯銀行（掛雅典）、`KBC BB` 比利時聯合金融 |

認不得的會原樣顯示代碼（`_NP_MKT[mkt] || mkt`），不會壞。**要新增先找佐證，
不要照國名猜。**

> **Tab 4 原本是「健診頁」**（持倉健檢 + 財務試算），2026-09-23 下架改放此頁。
> HTML 存在 `<template id="archived-check">`、JS 在 `/* 健診頁邏輯 */` 註解區塊裡，
> 兩邊都原樣保留，要恢復把 template 標籤拿掉並解開註解即可。

### 排行頁（E-1，工具 → 成交量排行）
| 代號 | 說明 |
|---|---|
| E-1 | 依成交量排行 TOP 100，每列顯示：配息頻率 / 1年內報酬 / 年殖利率 / 近3月績效柱狀圖 |

排序鍵是前端的 `cur_vol`（絕對成交量，單位**張**），不是 `heat`。
`heat`（量比＋漲跌幅＋連續性）只有 `daily_check.py` 偵測 TOP 100 新進時用。

#### ⚠ ETF 池子一定要含上櫃（2026-09-27 修）
`fetch_twse_etf_pool()` 從 ISIN 抓 **strMode=2 上市 + strMode=4 上櫃**兩邊。
在這之前只讀上市，上櫃 ETF 整批進不了池子，只有寫死在 `CURATED` 的
00928／006201 例外。造成的實際後果：

| 代號 | 名稱 | 張數 | 應有名次 |
|---|---|---|---|
| 00411A | 主動統一前沿科技 | 8,290 | 32 |
| 00998A | 主動復華金融股息 | 8,083 | 33 |
| 00888 | 永豐台灣ESG | 3,975 | 49 |
| 00887 | 永豐中國科技50大 | 2,766 | 55 |
| 00955 | 中信日本商社 | 1,576 | 74 |
| 00877 | 復華中國5G | 1,465 | 77 |

（TOP 100 門檻當時是 601 張。）00411A 更尷尬：我們早就在抓它的持股異動，
主動頁有格子，排行頁卻永遠找不到它。

配套三件事，缺一不可：
- `TWO_CODES` 不再寫死，由 `build_pool()` 從上櫃清單自動補；yfinance 要 `.TWO` 後綴
- `_base.json` 每筆多存 `"otc"`，`mis_fetcher.py` 靠它決定 MIS 用 `otc_` 還是 `tse_`
  前綴（用 `tse_` 查上櫃會回一筆 `c=""` 的空殼，等於查不到，就會退回昨天的量排名）
- `etf_pool_cache.json` 從兩元組改三元組 `[code, name, is_otc]`，讀取時相容舊格式

## 訊號顏色規範（四態 + 債券）

| 訊號 | 標籤 | 顏色（token） |
|---|---|---|
| `cheap` | 便宜 | `--sig-cheap`：dark #00e5a0／light #059669 |
| `fair` | 合理 | `--sig-fair` #F0B840 |
| `hot` | 過熱 | `--sig-hot` #ef4444 |
| `dear` | 偏貴 | `--sig-dear` #fb923c |
| `bond` | 債券型 | `--sig-bond` #58a6ff |

全站（首頁、排行、Detail、我的 ETF）同一組標籤與色：文字＋框線＝上表色、底色透明（CP7 PO-Locked）。
標籤一律「合理」（V3／CP8 起不再有「合理✓」；只剩已下架健診頁的封存程式 `archived-check.js` 保留原樣）。
Light／Dark 的透明底對比低於 4.5 是 PO 已接受的設計取捨（theme_test TH-6 Known Blocker），不要為了測試改色。

禁止在「過熱」加閃電符號 ⚡。

### `bond`：債券 ETF 不套股價訊號（2026-09-27）

`is_bond_etf(code)`＝代號 **B／D 結尾**。ISIN 全部 1294 檔裡 111 檔 B/D 結尾，
名稱**全部**是債券型、零例外；反查「名稱含債但代號非 B/D」只有槓反類
（00680L/00681R/00688L/00689R/00687C），那些 `EXCLUDE_KW` 已擋。
**不能用名稱關鍵字判**——簡稱常把「債」省掉：主動富邦動態入息（投資級債）、
主動貝萊德優投等（投資等級債）、凱基IG精選15+（IG 債）三個都躲過「債」字。

為什麼不給訊號：債券 ETF 跟著利率走，`cheap` 的條件（52 週位置 < 40% 且
低於 60MA > 2%）會被利率緩跌機械性踩中。實測榜上 3 檔債券型 **3/3 全是 cheap**，
但全池只有 8%（15/185）是 cheap。那不是划算，是模型量錯東西。

債券色刻意**不借用四態任何一色**，免得被讀成買賣判斷，它只是在說「這是債券型」。
（最初是中性灰；CP7 Visual Gate 起改為 PO 鎖定的 #58a6ff 藍，仍是「分類」語意，不是買賣判斷。）

⚠ 改訊號邏輯時 `calc_signal` 有**兩份**要同步：`fetch_etf.py`（回
`(signal, maD)` 兩元組）和 `scripts/mis_fetcher.py`（只回字串）。
mis_fetcher 還有**三處**會重算並覆蓋 signal（含寫檔後的自驗），
少改一處債券就會被蓋回 `cheap`。四個呼叫點都要把 `code` 傳進去。

副作用（都是想要的）：`daily_check.py` 與 `intraday_notify.py` 只推
`signal == "cheap"`，債券改成 `bond` 之後就不會再推「00984D 便宜」了。

## 主題（Dark／Light）與 visual tokens（Phase 5 CP7）

- **切換**：Header ☀／🌙 鈕；`<html data-theme="dark|light">`。初值：localStorage `etfRadar.theme` → 沒有就跟 `prefers-color-scheme`；
  手動選過以選擇為準。`<head>` 行內 script 在 CSS 前決定主題（不閃錯色）；meta theme-color 同步（dark #0F141B／light #FEF8E2）。
- **token 都在 `css/base.css`**：`:root` 是 dark，`:root[data-theme="light"]` 覆寫。**換主題只換 token**，元件不得寫死色值。
  - 環境：`--bg`（light 為奶油底 #FEF8E2）、`--card`、`--card2`、`--border`、`--dim`、`--bright`、`--link／--brand`。
  - 狀態五色：`--sig-cheap／fair／dear／hot／bond`＋`--sig-backing`（transparent）。
  - 漲跌：`--up／--dn`（一般漲跌字）；`--vivid-up／--vivid-dn`＋`--vivid-*-fill`＋`--rgb-vivid-*`（排行報酬率／漲跌柱、Active Flow 加減碼與 treemap 共用的鮮明紅綠）。
  - 其他：`--num-accent`（配息頻率、殖利率、配息金額：dark 鮮黃／light 橘）、`--rank1／2／3-bg／fg`（首頁 TOP10 light 與排行前三名的金銀銅）、
    `--etf-code-*`／`--etf-name-*`（全站 ETF 代碼／名稱字型）、`--mono`（數字字型＝微軟正黑體，名稱沿用）。
- **Active Flow treemap** 不用 token 透明度：`flow.js` `_flowFill` 依主題以「同色相、明度分層」算實色，並保證黑／白字對比；
  換主題由 `flowRecolor()`（`etf:themechange`）就地重算，不重建 DOM。
- 主題相關回歸：`tests/browser/theme_test.py`（TH-1～TH-10）。

## 篩選邏輯（四態訊號 + 債券短路）

以 `fetch_etf.py` 與 `scripts/mis_fetcher.py` 的 `calc_signal()` 為準（兩份必須同步），
**依序判斷、命中即停**。pos52＝(現價−52週低)/(52週高−52週低)；maD60＝(現價−60MA)/60MA×100%。

| 順序 | 訊號 | 條件 |
|---|---|---|
| 0 | `bond` 債券 | **代號 B/D 結尾直接短路**，不進下面任何一條（見訊號顏色規範那節） |
| 1 | `hot` 過熱 | 5 日漲幅 ≥ 5% **或** RSI ≥ 75 |
| 2 | `dear` 偏貴 | pos52 > 78% **或** 現價 > 60MA × 1.06 |
| 3 | `cheap` 便宜 | pos52 < 40% **且** maD60 < −2（低於 60MA 超過 2%） |
| 4 | `fair` 合理 | 現價 ≤ 60MA × 1.03、5 日漲幅 < 5%、量比 ≤ 3.0、RSI < 75 全部成立；高股息型（名稱含高股息／高息等，或殖利率 > 5%）另需殖利率 > 5% |
| 5 | `dear` 偏貴 | 以上皆不符（預設） |

- `ma20` 有傳入但不參與判斷；mis_fetcher 版另有「現價或 60MA ≤ 0 → dear」防護。
- 量比原本有下限 0.5，2026-05-29（`4c00a1fe`）移除：盤中累積量未達日均一半時會被誤判成 dear。
- **cheap 門檻 40%／2% 是刻意放寬的結果，不要改回 30%／3%**，原因見「產品決策與原因」。
- 本表曾長期停留在 2026-05-12 的舊版（30%／3%、溢價、MA20），2026-10-05 依程式更正。**文件配合程式，不因文件過期反改公式。**

## 產品決策與原因（長期保存）

> 只記未來維護需要知道的「決策＋原因」。進度、checkpoint、下一棒等短期狀態放 `AI_HANDOFF.md`。

### 網站面向 ETF 新手：資料池排除特殊機制型 ETF

- **決策**：資料池（`fetch_etf.py` 建池）排除**槓桿、反向、商品期貨**型 ETF；**一般債券 ETF 保留**。
  這是資料池層級的產品規則，前台不需要額外大量說明。
- **原因**：ETF 存股雷達主要面向 ETF 新手。PO 實際遇過新手詢問「槓桿 ETF 能不能買」；
  這類 ETF 需要額外理解產品機制，不適合主動提供給新手。
- **現況：篩選鏈（`fetch_etf.py`，Phase 5 P1 起；測試 `tests/test_pool.py` EX-1～EX-11）**
  1. **ISIN 區段**：上市 strMode=2＋上櫃 strMode=4，只取 `ETF`、`ETN` 兩個區段（`isin_sections`），
     列的 CFI 須符合區段前綴（ETF＝`CE…`、ETN＝`CM…`，`parse_isin_rows`），不再整頁解析。
  2. **代號型態**（`pool_excluded`）：必須 `0` 開頭（擋 TDR 9xxx 等）、不得 `T` 結尾（受益憑證）。
  3. **代號字尾** `EXCLUDE_SUFFIX = L／R／U`：槓桿／反向／期貨商品。名稱關鍵字擋不住簡稱
     （`02001L 富邦蘋果正二N`、`00682U／00693U／00763U`），所以用代號擋；2026-10-05 實測 ISIN ETF 區段字尾與名稱 0 例外。
  4. **名稱關鍵字** `EXCLUDE_KW`（債、期貨、槓桿、反向、貨幣、正2／反1、REITs、黃金、原油…）。
  5. **cache fallback 防線**：ISIN 抓不到改讀 `etf_pool_cache.json` 時，代號須符合 ETF（00…）／ETN（02…）格式（`cache_product_ok`），
     擋掉舊快取誤收的 01111S～01114S。`CURATED` 精選清單同樣走 `pool_excluded`。
  - ⚠ 文件與程式待對齊（CP8 盤點時發現，未改）：`EXCLUDE_KW` 含「債／公債／公司債」，名稱帶「債」的債券 ETF 會被濾掉，
    與上面「一般債券 ETF 保留」的決策字面不一致；目前榜上的債券 ETF 是名稱沒有「債」字者（見 `bond` 一節）。是否調整由 PO 決定。
  - 修補時**不要加過寬的「期」字**，以免誤排正常 ETF。

### cheap 門檻 40%／2% 是刻意放寬，不是誤改

- **決策**：cheap＝52 週位置 < 40% 且低於 60MA > 2%，維持不變。
- **原因**：初版 30%／3%（2026-05-11／12）太嚴格，曾連續多日幾乎沒有 ETF 符合，
  首頁「值得留意」長期沒有內容可呈現，PO 因此刻意放寬（2026-05-19 `4ea6db41`「cheap 條件放寬」）。
  舊文件曾殘留 30%／3%，看到不一致時以程式為準，不要改回去。

### LAZY_WATCHLIST 是舊首頁合理價白名單，不是新手安全機制

- **事實**：2026-05-14（`99c8b9b7`）建立的 20 檔人工白名單，用途是讓舊首頁「合理價」只收熱門 ETF、
  避免冷門／極新 ETF 混入；2026-05-20（`8e8e1566`）起 cheap 不再受限，並加入 00403A（21 檔）。
  它**與排除槓桿／反向無關**。之後未再維護，部分代碼已不在資料池或不配息。
- **決策**：首頁價格區改以「成交量前 100」為候選母體後，**首頁 fair 不再依賴 LAZY_WATCHLIST**
  （候選母體已達成原本「只收熱門」的目的）。
- **注意**：`daily_check.py`、`intraday_notify.py`、`fetch_dividend_calendar.py` 仍各有一份名單在使用
  （副本內容不完全一致），清理前要逐一確認用途，不可直接全域刪除。

### 首頁價格區與成交量排行的母體

- **價格區**（便宜＋合理）：候選母體＝**成交量前 100**（`cur_vol`），再判斷價格條件；不從全部 ETF 直接挑。
  排除 `div_frequency === '不配息'`（首頁價格區是存股取向；不配息 ETF 在分類、搜尋、Detail、自選照常可用）。
- **今日成交量 TOP 10**：依 `cur_vol` 成交量排序，**不用 `heat`**（`heat` 只給 `daily_check.py` 偵測新進前 100）。

## 殖利率資料來源優先順序

1. **FinMind** `TaiwanStockDividend` / `CashEarningsDistribution`（過去 365 天加總）
2. yfinance `hist['Dividends']` 加總
3. yfinance `info.dividend_yield`
4. yfinance `tk.dividends`（UTC 時區修正）
5. `_YLD_OVERRIDE` 手動覆寫 dict

### ⚠ 頻率錯 → 殖利率等比例錯（2026-09-27 一次抓到 3 檔）

`fetch_finmind_yld(code, price, div_freq)` 是**用頻率去年化**的
（`_FREQ_N`＝月配12／雙月配6／季配4／半年配2／年配1），所以
**`div_freq` 判錯，殖利率就照倍數錯**，而且畫面照樣標「已核實」。

新上市 ETF 最容易中：配息紀錄筆數不足，`detect_div_freq` 會**往少的猜**。
2026-09-27 補上櫃後新進池子的 9 檔裡就有 3 檔中招：

| 代號 | 自動推論 | 實際 | 顯示殖利率 | 正確 |
|---|---|---|---|---|
| 00985D | 季配 | **月配** | 2.5% | ~7.1%（1/3） |
| 00998A | 半年配 | **季配** | 5.0% | ~10.0%（1/2） |
| 00840B | 雙月配 | **月配** | 2.6% | ~5.2%（1/2） |

**先修 `DIV_FREQ`。** `detect_div_freq` 會先查它，頻率對了 FinMind 就會用正確
倍數年化——這是根因，不要一開始就塞 `_YLD_OVERRIDE` 遮症狀（00984D 那次就是
被硬塞成 0.8 才出事）。

**但上櫃 ETF 例外，頻率修完還是得補 `_YLD_OVERRIDE`。** FinMind 抓不到上櫃
（`00928`/`006201` 的舊註解早就寫了），而且**免費額度會爆**：HTTP 402
`Requests reach the upper limit`，2026-09-27 本機連跑 4 輪 200+ 檔就整批
退回 yfinance 殘缺值，00998A 從 10.0% 掉回 5.0%、00985D 從 7.6% 掉回 2.5%。
所以「跑一次對了」不代表穩定，上櫃的一律寫死。

⚠ **不要拿 `dividend_info.json` 的 `avg_dividend_per_share` 去推殖利率。**
我試過把它當 FinMind 掛掉時的保底，量測 98 檔後發現不行：
中位數相對誤差 14.2%、只有 55/98 落在 20% 內（00896 推算 14.5% vs 實際 2.7%、
00930 推算 20.5% vs 實際 7.5%）。那個欄位是給「下次除息金額預估」用的，
不少是舊值或峰值。程式裡留了一段註解擋這條路。

**驗算法（照 `feedback_data_verification_sources`）**：拿新聞的「年化配息率」
÷「單次配息率」＝ 一年幾次。00985D 7.14% ÷ 0.595% = 12 → 月配。
反過來也能抓錯：00888 有新聞說「2026 改雙月配」，但 MoneyDJ 實際除息日是
1/4/7/10 月 → **季配，新聞錯了**。**永遠以實際除息日為準，不要信新聞的頻率敘述。**

新 ETF 尚未配息的（如 00411A，2027-04 才首配）進 `_YLD_PENDING`，
畫面顯示「待公告」，不要留 0.0%。

## 配息頻率覆寫清單注意事項

- `fetch_etf.py` 內有手動覆寫 dict（`_CONFIRMED_FREQ`）
- 已確認實質不配息但被 API 誤標者需加入：`"0057":"不配息", "00660":"不配息"`
- 新增覆寫後需重跑 `fetch.yml` 才生效

## 排行頁殖利率顯示規則

| 狀況 | 顯示 |
|---|---|
| 有殖利率數字 | `--num-accent` 粗體 %（dark 鮮黃／light 橘） |
| 不配息 ETF | 不適用（灰色） |
| 新上市且 yld=0 | 未滿1歲（灰色） |
| 其他查無 | --（灰色） |

## 持倉健檢配息顯示規則（功能已於 2026-09-23 下架，規則保留備查）

| 狀況 | 顯示 |
|---|---|
| 不配息 ETF | 不配息 |
| 新上市且 yld=0 | 新上市待公告 |
| 有配息紀錄 | N 天後配息・預估 NT$X |
| 查無 | -- |

## 盤中通知排程（intraday_notify.py）

台北時間：09:10 / 10:00 / 11:00 / 12:00 / 13:00（±6 分鐘容許誤差）
- 只在 LAZY_WATCHLIST 有 `cheap` 訊號時發送
- 15:00 收盤通知由 `daily_check.py` 的 cheap_alerts 覆蓋

## daily_check.py TG 通知規則

### ⚠ 監控本身也會壞，而且壞掉時看起來跟「一切正常」一樣（2026-09-30）

目標是「壞掉時它來找你」，不是「你每天去確認它沒壞」。兩個實際存在過的破口：

1. **過期守門員在 CI 上是瞎的。** 原本用 `MARKET.stat().st_mtime` 判斷
   market.json 是否超過 30 小時沒更新——但 **git 不保存 mtime**，
   `actions/checkout` 拿到的檔案 mtime 永遠是「剛剛」，所以這條在
   GitHub Actions 上**永遠不會觸發**，偏偏那正是它要防的場景。
   （實測本機：mtime 09-30 01:03，實際 updated 09-29 21:52。）
   改看 `market.json` 的 `updated` 欄位，並注意那是**台北時間**、CI 跑在 UTC。
2. **`fetch_etf.py` 那步沒有 `continue-on-error`。** 它一掛整個 job 中止，
   後面的 `daily_check` 根本不會執行 → 使用者收到「完全沒通知」。
   **壞掉的時候更要讓警報跑得到**，所以抓資料的步驟一律 continue-on-error，
   只留 commit/push 會讓 job 紅燈。

**加任何監控前先問：這條在「它要防的那個故障」真的發生時，跑得到嗎？**

3. **監控跑得到，但門檻把它濾掉了（2026-10-02）。** 00996A 主動兆豐台灣豐收
   從 09-28 起連續 **5 個交易日、18 次排程** `fetched=false`，資料停在 09-24，
   `check_active_flow()` 從頭到尾回報 **0 項**，最後是 Gavin 自己看畫面發現的。
   兩道門檻各差一點，剛好夾出一個誰都看不到的縫：
   - `kept >= 3` 是「一次掉一批」的訊號，單檔一直回空永遠湊不到 3
   - `ACTIVE_STALE_ONE = 7`，而它落後剛好 7 天，`> 7` 差一天不觸發

   `fetched=false`（**我們這邊回空**）和「投信公告慢」是兩回事，不該共用門檻。
   新增 `ACTIVE_DEAD_ONE = 4` 只管前者。
   `base` 取**最後一個交易日**而不是今天，所以放假不會把 lag 撐大，
   不必為連假留寬容——這點是這個門檻能設這麼嚴的前提。
   門檻用 git 回放 34 個 `active_flow.json` 版本校準：2/3/4 結果一模一樣
   （00996A 13 次、00997A 1 次），兩者都是真的斷線，零誤報，取最寬的 4。

> **「門檻沒觸發」和「沒有問題」在畫面上一模一樣。** 改門檻一定要回放歷史資料，
> 不要憑感覺調——這個專案的監控已經在同一個地方失手三次了。

### 外部心跳監控（heartbeat monitoring）

上面兩條修完，仍有一個 `daily_check` 本質上補不了的洞：
**整條 Actions 根本沒跑**（服務中斷、workflow 被停用、repo 設定被改）。
監控住在被監控的東西裡面，它死了就一起死，使用者收到完全靜默。

解法是反過來——**不是「壞了就叫」，而是「沒心跳就叫」**：
`fetch.yml` 最後一步在成功時 ping 一個外部 URL（這就是「心跳」），外部
服務在超過寬限時間沒收到心跳時通知 Gavin。

分工：
| 誰 | 負責 |
|---|---|
| 外部心跳監控 | **有沒有跑** |
| `daily_check.py` | **跑出來的東西對不對** |

**現況：2026-09-30 已上線並實測成功**（check 名稱 `ETF fetch`、Cron
`0 1 * * 1-5` UTC、Grace 6 小時，GitHub secret `HEALTHCHECK_URL` 已設）。
通知管道走 Telegram（healthchecks.io → Integrations → Telegram）。
**注意：雲端版 healthchecks 用的是它自己的 bot，不是本專案 ETF 日報那支**，
所以會是另一個對話視窗，沒辦法合併。想合併只能用 Webhook 整合去打
`api.telegram.org/bot<TOKEN>/sendMessage`——但那等於把 TELEGRAM_BOT_TOKEN
存進第三方服務，違反「機敏資料集中管理」，不要這樣做。
分開其實更好讀：那支 bot 一出聲就代表整條 pipeline 沒跑。

當初的設定步驟（換 repo 或重建時照做）：
1. healthchecks.io 註冊 → Add Check，名稱 `ETF fetch`
2. Schedule 選 Cron，填 `0 1 * * 1-5`（UTC，對應台北 09:00 週一至五），
   Grace Time 給 6 小時（Actions 排程本身就有 5~30 分延遲，太短會誤報）
3. 複製該 check 的 Ping URL（`https://hc-ping.com/<uuid>`，
   後面**不要**接 `/start`、`/fail`、`/log`，也不要用 slug 版）
4. GitHub repo → Settings → Secrets and variables → Actions → New secret，
   名稱 **`HEALTHCHECK_URL`**，值貼上那個 URL

第 4 步沒設之前，那步會印「未設定，跳過 ping」後正常結束，不影響現有流程。

**⚠ 那步的 `if` 不要寫 `env.HEALTHCHECK_URL != ''`。**
HEALTHCHECK_URL 是同一個 step 的 `env`，而 step 自己的 env 在它自己的 `if`
裡算不算數，GitHub 沒有明確保證。萬一不算，secret 明明設好了 step 還是會
被永遠跳過 → ping 永遠不發 → healthchecks 每天誤報「掛了」，**把監控本身
變成雜訊來源，比沒有監控更糟**。空值判斷寫在 `run` 的 shell 裡才確定。

另外：job 卡死不動這種情況已經被這條蓋到了（沒 ping 就是沒 ping，過了
6 小時 grace 照樣叫），所以不需要為了「怕它 hang」去加 `timeout-minutes`。
真要加也只是省 Actions 分鐘數，不是補監控漏洞——別把兩件事搞混。

| 區塊 | 觸發條件 |
|---|---|
| 💚 監控清單便宜訊號 | LAZY_WATCHLIST 有 `cheap` 訊號 |
| 🆕 新進 TOP 100 資料異常 | 新進榜 ETF 有以下**任一**問題：配息方式不明 / 殖利率查無（非新上市、非不配息、非待公告）/ 報酬率查無（非新上市） |

- 配息 7 天通知：**已關閉**（2026-05-25 移除）
- 新進榜正常 ETF：**不通知**，只在資料異常時通知

## 配息行事曆雙源查詢邏輯（fetch_dividend_calendar.py）

排程：每個工作日 08:30（dividend-update.yml）

**距除息日 ≤ 14 天 → 強制雙源查詢（TWSE × FinMind）**

| 結果 | 來源標記 |
|---|---|
| TWSE 有、FinMind 有，差異 ≤5% | `TWSE × FinMind 核實` |
| TWSE 有、FinMind 無 | `TWSE` |
| TWSE 無、FinMind 有 | `FinMind（估算）` |
| 兩者皆無，且距除息 ≤ 7 天 | TG 通知 Gavin，前端顯示「待公告」 |

**關於第三來源：**
- Goodinfo 等網站的「未公告金額」是用歷史配息估算，非官方資料
- TWSE 和 FinMind 都查無 = 金額真的還沒公告，加第三官方源無效
- 若 FinMind 也無當筆，可考慮用 FinMind 最近一筆歷史配息作估算（待實作，需 Gavin 同意）

**`amount` 欄位語意：**
- `0.072`（數字）→ 有資料，前端顯示金額
- `null` → 查無，前端顯示「待公告」（不走歷史 fallback）

## 資料來源

- 即時行情 / 歷史資料：yfinance（上市 `.TW`、上櫃 `.TWO`，由 `TWO_CODES` 自動判斷）
- ETF 池子：TWSE ISIN `C_public.jsp` strMode=2（上市）+ strMode=4（上櫃），兩邊都要抓
- 盤中即時：TWSE MIS，上市 `tse_<code>.tw`、上櫃 `otc_<code>.tw`（v 欄位單位是**張**）
- ETF 淨值：TWSE 公開資訊觀測站 API（失敗 fallback 前一日收盤）
- 殖利率：FinMind API（主要）+ yfinance（fallback）
- 配息行事曆：TWSE ETFortune（主）+ FinMind TaiwanStockDividend（副）

## 法遵

- 所有訊號附「非投資建議」警語（頂部 disclaimer）
- 0 支合理價時顯示「為什麼今天沒有」說明
- 介面不出現具體買賣指令

## 部署

- GitHub Pages：p14090060.github.io/cashflow-etf（主要）
- GitHub：github.com/p14090060/cashflow-etf
- Action 手動觸發：GitHub → Actions → 選擇 workflow → Run workflow
