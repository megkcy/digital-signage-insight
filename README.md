# Digital Signage Insight — 競爭對手追蹤 Dashboard

**🔗 https://megkcy.github.io/digital-signage-insight**

數位看板產業競爭對手追蹤 Dashboard，追蹤 50+ 個競爭對手的 SEO、Tech Stack、Facebook / LinkedIn 社群與關鍵字排名，每週自動更新。

## 功能

- **SEO 追蹤**：網站頁數、Tech Stack 分析
- **Facebook 追蹤者**：透過 SerpApi Facebook Profile API 取得粉絲數
- **LinkedIn 追蹤者**：透過 Bright Data 批量 API 取得追蹤數
- **關鍵字排名**：追蹤 `digital signage`、`menu board`、`cloud-based digital signage` 三組關鍵字，標示自家網站排名
- **Google Search Console**：cayintech.com & gocayin.com 的熱門關鍵字及流量來源國家
- **Semrush 連結**：每個競爭對手一鍵查看流量分析
- **歷史趨勢圖**：每週歷史記錄可視化（Chart.js）
- **新增 / 編輯 / 刪除**競爭對手（即時同步 Firestore，不會被爬取覆蓋）
- **自動排程**：每週透過 GitHub Actions 自動爬取並寫入 Firestore

## 技術架構

| 層 | 技術 |
|----|------|
| 前端 | 純 HTML / CSS / JS + Chart.js，部署於 GitHub Pages |
| 資料庫 | Firebase Firestore（collection: `insight`，document: `data`） |
| 爬蟲排程 | GitHub Actions（每週一 06:00 台灣時間） |
| 關鍵字 / Facebook | SerpApi（`engine=google`、`engine=facebook_profile`） |
| LinkedIn | Bright Data Datasets API（`gd_l1vikfnt1wgvvqz95w`） |
| GSC | Google Search Console API（Service Account） |

## 資料流程

```
GitHub Actions（每週自動 / 手動觸發）
    └─→ backend/scraper_static.py
         ├─→ SerpApi         → 關鍵字排名 + Facebook 追蹤者
         ├─→ Bright Data     → LinkedIn 追蹤者
         ├─→ Google GSC API  → 搜尋關鍵字 + 國家流量
         └─→ Firebase Firestore  ←─── 前端直接讀取
              └─→ docs/data.json（備份，Firestore 失敗時 fallback）
```

## GitHub Actions Secrets

| Secret | 說明 |
|--------|------|
| `FIREBASE_SERVICE_ACCOUNT` | Firebase Service Account JSON |
| `SERPAPI_KEY` | SerpApi API Key |
| `BRIGHTDATA_KEY` | Bright Data API Token |
| `GSC_SERVICE_ACCOUNT` | Google Search Console Service Account JSON |

## Firebase 設定

資料存放於 Firebase Firestore：
- **Collection**：`insight`
- **Document**：`data`

如需替換為自己的 Firebase 專案，修改 `docs/app.js` 中的 `firebaseConfig`。

## 追蹤的競爭對手

涵蓋 51 個數位看板相關競爭對手，包括：  
Yodeck、Broadsign、ScreenCloud、OptiSigns、NoviSign、RISE Vision、OnSign TV、Poppulo、Samsung VXT、Scala、BrightSign、Signagelive 等。

自家網站（cayintech.com、gocayin.com）在關鍵字排名中以藍色標示。
