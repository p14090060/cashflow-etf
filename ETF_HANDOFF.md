# ETF 存股雷達 — 交接本

> 新 session 上線先讀這份。詳細技術規則在 `CLAUDE.md`，UI 重構的四份文件見下方。

**最後更新**：2026-10-04

---

## 專案基本

| 項目 | 值 |
|---|---|
| 本機路徑 | `c:\專案\etf` |
| Repo | `github.com/p14090060/cashflow-etf`（private） |
| 線上網址 | https://p14090060.github.io/cashflow-etf/ |
| 部署方式 | GitHub Pages「Deploy from branch」，main 的根目錄就是網站，**沒有 build step** |
| 資料更新 | GitHub Action 產生 `market.json` / `active_flow.json` 等，由 Action 自己 commit |

---

## 現在停在哪裡

**UI/UX 重構 Phase 1(全站搜尋)已完成並通過真機實測,等 GPT 確認後才開始 Phase 2。**

```
2360ead2  docs: PHASE1_CHANGELOG 補上真機測試的兩項 FAIL 與修正結果   ← HEAD
89e6641a  fix(phase1): 修 Mobile 真機測出的兩項 FAIL                 ← Phase 1 最終程式碼 SHA
d3a4aa2c  docs: 收進 UI 重構的四份文件
9c5622b6  fix(phase1): 結果面板蓋住下拉；搜尋改為同時比對分類
e674f8e2  feat(phase1): 全站搜尋
```

- 回退點：`2ec0cb17`（pre-UI verified）、tag `pre-split` → `7b83383f`
- 整個 Phase 1 回退：`git revert 89e6641a 9c5622b6 e674f8e2`

### 待辦（有先後順序，不可跳）

1. **等使用者轉達 GPT 的確認**，把 `89e6641a` 定為 Phase 1 Verified baseline。
2. 之後才開始 **Phase 2：ETF 詳細頁**（總覽｜走勢｜配息｜績效｜成分 五個 tab）。
3. GPT 明確要求延後、**現在不要動**的項目：
   - 「搜尋『高股息』會找到大量結果」→ 留到分類頁完成後統一審查
   - 4 個搜尋入口尚未整併 → Phase 2 處理
   - `rank.js` 的 `_matchEtf()` 還沒加分類比對（`search.js` 的 `_gsMatch()` 有）

---

## UI 重構的四份文件

| 檔案 | 內容 |
|---|---|
| `IA_PROPOSAL.md` | 資訊架構提案（7 大分類、4 格 Bottom Nav、分類排序的理由） |
| `IA_PHASE1B.md` | 分類與導覽的細部規劃 |
| `SPLIT_REPORT.md` | 1,863 行 `index.html` 拆成 14 檔的驗證報告（已 review 過） |
| `PHASE1_CHANGELOG.md` | Phase 1 全站搜尋的完整變更 + 真機實測結果（最新一份，交給 GPT review 的就是這個） |

**工作流程**：使用者把規劃／報告貼給 ChatGPT 做第二次 review，GPT 回覆再由使用者轉達。所以每個階段結束要產出 `.md`，不要只在對話裡講。

---

## 這台機器的限制（會影響驗證方式）

- **沒有任何 JavaScript 引擎**（node / deno / bun / qjs、Python 的 JS binding 全都沒有）
- **沒有瀏覽器、沒有 `gh` CLI**
- ⇒ 所有 runtime 行為（畫面、點擊、Console 有沒有紅字）**只能請使用者實測回報**。
  靜態面可以自己驗：AST 解析、括號平衡、跨檔重複宣告掃描、onclick 對應函式是否存在。
- 使用者不熟開發者工具。**不要叫他開 F12／Network 分頁**；要驗快取就給 `?fresh=時間戳` 的網址，
  要他回報就請他截圖，步驟要寫成「點哪裡 → 應該看到什麼」。

---

## 容易踩的坑（細節在 `CLAUDE.md`）

- 改了 `js/*.js` 或 `css/*.css` **一定要同步 bump `index.html` 裡的 `?v=`**，否則瀏覽器讀快取。
- 所有 JS 都是傳統 `<script>`，**不可加 `type="module"`**——HTML 和動態字串裡有行內 `onclick`。
- 傳統 script 之間共用同一個全域 lexical scope，跨檔重複 `let`/`const` 會 SyntaxError 整頁掛掉。
- 彭博市場別代碼 ≠ ISO 國碼（`CH`=中國不是瑞士）。
- 台灣 ETF 代碼 `A`=主動式、`B`=債券，分類正則要用 `00\d{3}A`。
- 禁止閃爍動畫。
