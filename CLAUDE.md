# ETF 存股健診

靜態 PWA，每日從 TWSE + yfinance + FinMind 抓資料，GitHub Action 自動更新，GitHub Pages 自動部署。

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
| `.github/workflows/update-data.yml` | 盤中每 10 分鐘更新 market.json |

## 兩階段 Action 架構

1. `fetch.yml` → 跑 `fetch_etf.py` → 產出 `data/_base.json`
2. `update-data.yml` → 跑 `mis_fetcher.py` → 合併 _base.json → 產出 `data/market.json` → 跑 `intraday_notify.py`

**前端只讀 `data/market.json`**，改完 fetch_etf.py 要先觸發 fetch.yml，再觸發 update-data.yml 才會反映。

## 文案規範

- **禁用**「買進/賣出/觀望/建議」等動作指令
- **改用**「合理價區/熱門排行/留意風險」等狀態描述
- 品牌調性：多用「資金/水/流向」意象

## 頁面區塊代號（溝通用，不顯示在 APP）

### 今日頁（Tab 1）
| 代號 | 說明 |
|---|---|
| A-1 | 大盤現況（mood-card：大盤漲跌 + 情緒） |
| A-2 | 值得留意 ETF（便宜全顯示 + LAZY_WATCHLIST 合理最多5支，可能為 0 支） |
| A-3 | 今日熱門 TOP 10 區（熱度排行，非推薦清單） |
| A-4 | 查詢其他 ETF（自訂代碼即時查詢） |

### 配息頁（Tab 2）
| 代號 | 說明 |
|---|---|
| B-1 | 配息計算機 |
| B-2 | 配息行事曆 |

### 頻道頁（Tab 3）
| 代號 | 說明 |
|---|---|
| C-1 | 頻道介紹卡（Logo + 訂閱按鈕） |
| C-2 | 最新影片連結 |
| C-3 | 今日股市笑話 |

### 健診頁（Tab 4）
| 代號 | 說明 |
|---|---|
| D-1 | ETF 持倉健檢（輸入代碼 + 張數 + 成本價 → 損益 / 訊號 / 配息預估） |
| D-2 | 財務試算（資金 + 定期定額 + 報酬率 → 複利試算 + ETF 建議） |

### 排行頁（Tab 5）
| 代號 | 說明 |
|---|---|
| E-1 | 依成交量排行 TOP 100，每列顯示：配息頻率 / 1年內報酬 / 年殖利率 / 近3月績效柱狀圖 |

## 訊號顏色規範（四態）

| 訊號 | 標籤 | 顏色 |
|---|---|---|
| `cheap` | 便宜 | 綠色 #00e5a0 |
| `fair` | 合理✓ | 金黃 #F0B840 |
| `hot` | 過熱 | 紅色 #ef4444 |
| `dear` | 偏貴 | 橘色 #fb923c |

禁止在「過熱」加閃電符號 ⚡。

## 篩選邏輯（四態訊號）

| 訊號 | 條件 |
|---|---|
| `cheap` 便宜 | 52週低位 < 30% 且 低於 60MA > 3% |
| `fair` 合理價 | 溢價 <1% + price ≤ ma20×1.02 + 5日漲幅 <5% + 量達標（高股息額外：殖利率 >5%） |
| `hot` 過熱 | 5日漲幅 ≥5% 或溢價 ≥2% |
| `dear` 偏貴 | 其他（52週高位 >78% 或遠高於60MA） |

## 殖利率資料來源優先順序

1. **FinMind** `TaiwanStockDividend` / `CashEarningsDistribution`（過去 365 天加總）
2. yfinance `hist['Dividends']` 加總
3. yfinance `info.dividend_yield`
4. yfinance `tk.dividends`（UTC 時區修正）
5. `_YLD_OVERRIDE` 手動覆寫 dict

## 配息頻率覆寫清單注意事項

- `fetch_etf.py` 內有手動覆寫 dict（`_CONFIRMED_FREQ`）
- 已確認實質不配息但被 API 誤標者需加入：`"0057":"不配息", "00660":"不配息"`
- 新增覆寫後需重跑 `fetch.yml` 才生效

## 排行頁殖利率顯示規則

| 狀況 | 顯示 |
|---|---|
| 有殖利率數字 | 金黃粗體 % |
| 不配息 ETF | 不適用（灰色） |
| 新上市且 yld=0 | 未滿1歲（灰色） |
| 其他查無 | --（灰色） |

## 持倉健檢配息顯示規則

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

## 資料來源

- 即時行情 / 歷史資料：yfinance（`.TW` 後綴）
- ETF 淨值：TWSE 公開資訊觀測站 API（失敗 fallback 前一日收盤）
- 殖利率：FinMind API（主要）+ yfinance（fallback）
- 配息行事曆：TWSE 官方

## 法遵

- 所有訊號附「非投資建議」警語（頂部 disclaimer）
- 0 支合理價時顯示「為什麼今天沒有」說明
- 介面不出現具體買賣指令

## 部署

- GitHub Pages：p14090060.github.io/cashflow-etf（主要）
- GitHub：github.com/p14090060/cashflow-etf
- Action 手動觸發：GitHub → Actions → 選擇 workflow → Run workflow
