#!/bin/bash
# 交易信号扫描脚本 - 带飞书推送
# 用法：./scan_signals.sh

cd /home/wz/.openclaw/workspace/trading_system

echo "=== 开始扫描信号 ==="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"

# 运行信号生成
python3 send_signals.py 2>&1

echo "=== 扫描完成 ==="
echo ""
