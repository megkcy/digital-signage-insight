#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "▶ Insight — Competitor Tracker"
echo "================================"

# 建立虛擬環境（若不存在）
if [ ! -d "venv" ]; then
  echo "建立虛擬環境…"
  python3 -m venv venv
fi

source venv/bin/activate

echo "安裝依賴套件…"
pip install -q -r requirements.txt

echo "初始化資料庫…"
python backend/database.py

echo ""
echo "✓ 啟動 API server: http://localhost:8000"
echo "✓ Dashboard:        http://localhost:8000"
echo "  (按 Ctrl+C 停止)"
echo ""

cd backend
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
