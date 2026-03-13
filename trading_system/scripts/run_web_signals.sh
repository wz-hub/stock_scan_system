#!/bin/bash
# 启动信号中心 Web 界面

cd "$(dirname "$0")/.."

echo "🚀 启动信号中心 Web 界面..."
echo "📍 地址：http://localhost:8502"
echo "📡 页面：信号中心 - AI 评分"
echo ""

streamlit run web_signals.py --server.port 8502 --server.address localhost
