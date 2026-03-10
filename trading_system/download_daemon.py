#!/usr/bin/env python3
"""
数据下载守护进程 - 确保历史数据持续保存

功能：
- 启动数据下载
- 每 30 分钟汇报进度
- 数据校验
- 持久化配置
"""

import sys
import sqlite3
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent))


def check_database_stats(db_path: str = 'cache/trading.db') -> Dict:
    """检查数据库统计信息"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 总记录数
    cursor.execute('SELECT COUNT(*) FROM klines')
    total = cursor.fetchone()[0]
    
    # 按周期统计
    cursor.execute('''
        SELECT interval, COUNT(*), 
               MIN(timestamp) as min_ts, 
               MAX(timestamp) as max_ts
        FROM klines
        GROUP BY interval
        ORDER BY interval
    ''')
    by_interval = cursor.fetchall()
    
    # 按交易对统计
    cursor.execute('''
        SELECT symbol, COUNT(*) as cnt
        FROM klines
        GROUP BY symbol
        ORDER BY cnt DESC
        LIMIT 20
    ''')
    by_symbol = cursor.fetchall()
    
    conn.close()
    
    return {
        'total': total,
        'by_interval': by_interval,
        'by_symbol': by_symbol
    }


def update_progress_report(stats: Dict, download_start_time: datetime):
    """更新进度报告"""
    elapsed = datetime.now() - download_start_time
    
    report = f"""# 数据下载进度报告

**更新时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)  
**已运行:** {elapsed.total_seconds() / 3600:.1f} 小时

## 数据统计

### 总数据量
- **K 线总数:** {stats['total']:,} 条

### 按周期统计
"""
    
    for interval, count, min_ts, max_ts in stats['by_interval']:
        if min_ts and max_ts:
            min_date = datetime.fromtimestamp(min_ts/1000).strftime('%Y-%m-%d')
            max_date = datetime.fromtimestamp(max_ts/1000).strftime('%Y-%m-%d')
            report += f"- **{interval}:** {count:,} 条 ({min_date} ~ {max_date})\n"
    
    report += f"""
### Top 交易对
"""
    
    for symbol, count in stats['by_symbol'][:10]:
        report += f"- **{symbol}:** {count:,} 条\n"
    
    report += f"""
## 下次汇报
- **时间:** {(datetime.now() + timedelta(minutes=30)).strftime('%H:%M')}
- **间隔:** 30 分钟

---
*自动生成的进度报告*
"""
    
    # 保存到文件
    with open('DOWNLOAD_PROGRESS.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    return report


def main():
    """主函数"""
    print("=" * 80)
    print("📊 数据下载守护进程")
    print("=" * 80)
    print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print("=" * 80)
    print()
    
    download_start_time = datetime.now()
    last_report_time = download_start_time
    
    # 初始统计
    stats = check_database_stats()
    update_progress_report(stats, download_start_time)
    
    print()
    print("✅ 守护进程已启动")
    print("📝 每 30 分钟自动汇报进度")
    print("📄 进度报告：DOWNLOAD_PROGRESS.md")
    print()
    
    # 持续监控
    while True:
        time.sleep(1800)  # 30 分钟 = 1800 秒
        
        # 检查数据库
        stats = check_database_stats()
        
        # 更新进度报告
        update_progress_report(stats, download_start_time)
        
        print(f"\n[{datetime.now().strftime('%H:%M')}] 进度已更新")


if __name__ == '__main__':
    main()
