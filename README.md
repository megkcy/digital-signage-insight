# Digital Signage Insight — 競爭對手追蹤 Dashboard

數位看板產業競爭對手追蹤 Dashboard，追蹤 50+ 個競爭對手的 SEO、Tech Stack 與社群媒體數據，每週自動更新。

## 功能

- **SEO 追蹤**：網站頁數、Tech Stack 分析
- **社群媒體**：LinkedIn 追蹤者數
- **Google Trends**：關鍵字趨勢追蹤
- **歷史趨勢圖**：每週歷史記錄可視化（Chart.js）
- **新增 / 編輯 / 刪除**競爭對手（即時同步 Firestore）
- **自動排程**：每週透過 GitHub Actions 自動爬取並寫入 Firestore

## 技術架構

| 層 | 技術 |
|----|------|
| 前端 | 純 HTML / CSS / JS + Chart.js |
| 資料庫 | Firebase Firestore |
| 爬蟲排程 | GitHub Actions（每週一 06:00 UTC） |
| 部署 | Railway（FastAPI 靜態檔案伺服器）或直接開啟 `docs/index.html` |

## 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動本地伺服器（http://localhost:8000）
./start.sh
```

## 手動觸發爬取

在 Dashboard 右上角點「▶ 立即爬取」，需要先在「設定」填入 GitHub Personal Access Token（需 `repo` + `workflow` 權限）。

或直接在 GitHub Actions 頁面手動觸發 `weekly_scrape.yml`。

## Railway 部署

1. 前往 [railway.app](https://railway.app) 並以 GitHub 登入
2. **New Project → Deploy from GitHub repo** → 選 `megkcy/digital-signage-insight`
3. Railway 自動偵測 `railway.toml` 並部署
4. **Settings → Networking → Generate Domain** 取得公開連結

## Firebase 設定

資料存放於 Firebase Firestore，collection: `insight`，document: `data`。  
如需替換為自己的 Firebase 專案，修改 `docs/app.js` 中的 `firebaseConfig`。

## 追蹤的競爭對手

涵蓋 51 個數位看板相關競爭對手，包括：  
Yodeck、Broadsign、ScreenCloud、OptiSigns、NoviSign、RISE Vision、OnSign TV、Poppulo、Samsung VXT、Scala、BrightSign、Signagelive 等。
