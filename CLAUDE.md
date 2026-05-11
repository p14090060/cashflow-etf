# ETF 存股健診

靜態 PWA，每日從 TWSE + yfinance 抓資料，GitHub Action 自動更新 data.json，Netlify 自動部署。

## 核心檔案

| 檔案 | 用途 |
|---|---|
| `index.html` | 前端 PWA（純 HTML/JS，無框架） |
| `fetch_etf.py` | 每日資料抓取腳本（yfinance + TWSE） |
| `data.json` | Action 產出的 ETF 資料（不手動編輯） |
| `.github/workflows/fetch.yml` | 每日 08:30 自動排程 |

## 文案規範

- **禁用**「買進/賣出/觀望/建議」等動作指令
- **改用**「合理價區/熱門排行/留意風險」等狀態描述
- 品牌調性：多用「資金/水/流向」意象

## 訊號區塊定義

| 區塊 | 說明 |
|---|---|
| A 區「合理價 ETF」 | 折溢價 + 技術面篩選，可能為 0 支 |
| B 區「今日熱門 TOP 10」 | 熱度排行，非推薦清單 |

## 篩選邏輯（四態訊號）

| 訊號 | 條件 |
|---|---|
| `cheap` 便宜 | 52週低位 < 30% 且 低於 60MA > 3% |
| `fair` 合理價 | 溢價 <1% + price ≤ ma20×1.02 + 5日漲幅 <5% + 量達標（高股息額外：殖利率 >5%） |
| `hot` 過熱 | 5日漲幅 ≥5% 或溢價 ≥2% |
| `dear` 偏貴 | 其他（52週高位 >78% 或遠高於60MA） |

## 資料來源

- 即時行情 / 歷史資料：yfinance（`.TW` 後綴）
- ETF 淨值：TWSE 公開資訊觀測站 API（失敗 fallback 前一日收盤）
- 配息天數 / 預估金額：`DIV_DAYS` / `DIV_EST` dict（手動維護，每季更新）

## 法遵

- 所有訊號附「非投資建議」警語（頂部 disclaimer）
- 0 支合理價時顯示「為什麼今天沒有」說明
- 介面不出現具體買賣指令

## 部署

- Netlify：cashflow-etf.netlify.app
- GitHub：github.com/p14090060/cashflow-etf
- Action 手動觸發：GitHub → Actions → Fetch ETF Data → Run workflow
