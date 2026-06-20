#!/bin/bash
set -e
cd "$(dirname "$0")"
source venv/bin/activate
echo "▶ 手動執行爬蟲…"
cd backend
python scraper.py
echo "✓ 完成"
