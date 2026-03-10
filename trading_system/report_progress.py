#!/usr/bin/env python3
"""
重构进度汇报脚本
每 20 分钟自动汇报一次进度
"""
import sys
import json
from pathlib import Path
from datetime import datetime

PROGRESS_FILE = Path('/home/wz/.openclaw/workspace/trading_system/REFACTOR_PROGRESS.json')

def load_progress():
    """加载进度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {
        'current_task': 1,
        'completed_tasks': 0,
        'total_tasks': 14,
        'phase': 1,
        'last_updated': datetime.now().isoformat()
    }

def report_progress():
    """汇报进度"""
    progress = load_progress()
    
    print("="*80)
    print("⏰ 重构进度定时汇报")
    print("="*80)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Phase: {progress['phase']}")
    print(f"进度：{progress['completed_tasks']}/{progress['total_tasks']} ({progress['completed_tasks']/progress['total_tasks']*100:.0f}%)")
    print(f"当前 Task: {progress['current_task']}")
    print(f"最后更新：{progress['last_updated']}")
    print("="*80)
    
    # 检查是否完成
    if progress['completed_tasks'] >= progress['total_tasks']:
        print("✅ Phase 1 全部完成！")
        print("🎯 准备验收")
    else:
        print(f"⏳ 继续执行 Task {progress['current_task']}")
    print("="*80)

if __name__ == '__main__':
    report_progress()
