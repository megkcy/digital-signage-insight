# Digital Signage Insight — 競爭對手追蹤 Dashboard

**🔗 https://megkcy.github.io/digital-signage-insight**

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
| 前端 | 純 HTML / CSS / JS + Chart.js，部署於 GitHub Pages |
| 資料庫 | Firebase Firestore（collection: `insight`，document: `data`） |
| 爬蟲排程 | GitHub Actions（每週一 06:00 台灣時間） |

## 資料流程

```
GitHub Actions (每週自動 / 手動觸發)
    └─→ backend/scraper_static.py
         └─→ Firebase Firestore  ←─── 前端直接讀取
              └─→ docs/data.json（備份，Firestore 失敗時 fallback）
```

## 手動觸發爬取

在 GitHub Actions 頁面手動觸發 `weekly_scrape.yml`，需要在 repo Secrets 設定 `FIREBASE_SERVICE_ACCOUNT`（Firebase service account JSON）。

## Firebase 設定

資料存放於 Firebase Firestore：
- **Collection**：`insight`
- **Document**：`data`

如需替換為自己的 Firebase 專案，修改 `docs/app.js` 中的 `firebaseConfig`。

## 追蹤的競爭對手

涵蓋 51 個數位看板相關競爭對手，包括：  
Yodeck、Broadsign、ScreenCloud、OptiSigns、NoviSign、RISE Vision、OnSign TV、Poppulo、Samsung VXT、Scala、BrightSign、Signagelive 等。
