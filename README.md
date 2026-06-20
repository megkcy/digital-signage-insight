# Insight — 競爭對手 SEO & 社群追蹤

數位看板產業競爭對手追蹤 Dashboard，追蹤 50+ 個競爭對手的 SEO 和社群媒體數據，每週自動更新。

## 功能

- **SEO 追蹤**：Open PageRank 分數、網站頁數、Tech Stack 分析
- **社群媒體**：Facebook、Instagram、X (Twitter)、LinkedIn 追蹤者數
- **趨勢圖**：每週歷史記錄可視化
- **自動排程**：每週一 06:00 自動爬取

## 快速啟動

```bash
cd insight
./start.sh
```

打開瀏覽器：http://localhost:8000

## 手動爬取

```bash
./scrape_now.sh
```

## 每週排程（背景執行）

```bash
source venv/bin/activate
python backend/scheduler.py
```

## 技術架構

- **後端**：Python FastAPI + SQLite
- **前端**：純 HTML/CSS/JS + Chart.js
- **爬蟲**：requests + BeautifulSoup4
- **排程**：APScheduler

## 追蹤的競爭對手

涵蓋 51 個數位看板相關競爭對手，包括：Yodeck、Broadsign、ScreenCloud、OptiSigns、NoviSign、RISE Vision、OnSign TV、Poppulo、Samsung VXT、Scala 等。
