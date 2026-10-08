# feed/mega — 00996A 交接資料（只放交接檔，不放網站正式輸出）

- 檔案：`mega_00996A_<official_data_date>.json`（schema v1，見 main 的 `scripts/mega_feed.py`）
- 來源：本機人工執行 `scripts/mega_collect.py` 取得的兆豐官方 PCF（trade_pcf；最新一份另與商品頁交叉比對）
- 讀取者：main 的 `.github/workflows/fetch.yml` → `scripts/fetch_active_etf.py`，只在兆豐 PCF 與商品頁都失敗時讀，並再驗證一次
- `data/active_flow.json`、`data/_active_snapshot.json` 只由 GitHub Actions 寫入；本分支永遠不放這兩個檔
