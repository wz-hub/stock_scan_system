#!/usr/bin/env python3
"""
信号表现统计模块
统计策略和 AI 的准确率
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import json

DB_FILE = Path('cache/trading.db')


class SignalStats:
    """信号表现统计"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_FILE)
    
    def get_closed_signals(self, days: int = 30) -> List[Dict]:
        """获取已平仓信号"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''
                SELECT 
                    symbol, strategy_name, direction,
                    entry_price, exit_price, stop_loss_price, take_profit_price,
                    exit_reason, pnl_pct,
                    confidence,
                    ai_score, ai_direction, ai_reason,
                    created_at, exit_time
                FROM signals
                WHERE status IN ('STOP_LOSS', 'TAKE_PROFIT', 'CLOSED')
                AND created_at >= datetime('now', ?)
                ORDER BY created_at DESC
            '''
            
            df = pd.read_sql_query(query, conn, params=[f'-{days} days'])
            conn.close()
            
            return df.to_dict('records')
        except Exception as e:
            print(f"获取已平仓信号失败：{e}")
            return []
    
    def calculate_strategy_stats(self, days: int = 30) -> Dict:
        """
        计算策略统计
        
        Returns:
            {
                '策略名': {
                    'total': 总数量,
                    'win': 盈利数量,
                    'loss': 亏损数量,
                    'win_rate': 胜率,
                    'avg_pnl': 平均盈亏,
                    'total_pnl': 总盈亏
                }
            }
        """
        signals = self.get_closed_signals(days)
        
        if not signals:
            return {}
        
        # 按策略分组
        strategy_groups = {}
        for sig in signals:
            strategy = sig.get('strategy_name', 'Unknown')
            if strategy not in strategy_groups:
                strategy_groups[strategy] = []
            strategy_groups[strategy].append(sig)
        
        # 计算每个策略的统计
        stats = {}
        for strategy, sigs in strategy_groups.items():
            total = len(sigs)
            wins = [s for s in sigs if s.get('pnl_pct', 0) > 0]
            losses = [s for s in sigs if s.get('pnl_pct', 0) <= 0]
            
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = (win_count / total * 100) if total > 0 else 0
            
            avg_pnl = sum(s.get('pnl_pct', 0) for s in sigs) / total if total > 0 else 0
            total_pnl = sum(s.get('pnl_pct', 0) for s in sigs)
            
            stats[strategy] = {
                'total': total,
                'win': win_count,
                'loss': loss_count,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl
            }
        
        return stats
    
    def calculate_ai_stats(self, days: int = 30) -> Dict:
        """
        计算 AI 统计
        
        Returns:
            {
                'overall': {  # 总体统计
                    'total': 总数量,
                    'correct': 正确数量,
                    'accuracy': 准确率,
                    'avg_confidence': 平均置信度
                },
                'by_direction': {  # 按方向统计
                    'LONG': {...},
                    'SHORT': {...},
                    'WAIT': {...}
                }
            }
        """
        signals = self.get_closed_signals(days)
        
        # 只统计有 AI 评分的信号
        ai_signals = [s for s in signals if s.get('ai_score') is not None and s.get('ai_direction')]
        
        if not ai_signals:
            return {}
        
        # 判断 AI 是否正确
        for sig in ai_signals:
            ai_dir = sig.get('ai_direction')
            pnl = sig.get('pnl_pct', 0)
            
            # AI 判断正确的条件
            if ai_dir == 'LONG':
                sig['ai_correct'] = (pnl > 0)  # 做多赚钱=正确
            elif ai_dir == 'SHORT':
                sig['ai_correct'] = (pnl > 0)  # 做空赚钱=正确
            elif ai_dir == 'WAIT':
                # 观望：如果信号亏损，说明观望正确
                sig['ai_correct'] = (pnl <= 0)
            else:
                sig['ai_correct'] = False
        
        # 总体统计
        total = len(ai_signals)
        correct = len([s for s in ai_signals if s.get('ai_correct')])
        accuracy = (correct / total * 100) if total > 0 else 0
        avg_confidence = sum(s.get('ai_score', 0) for s in ai_signals) / total if total > 0 else 0
        
        stats = {
            'overall': {
                'total': total,
                'correct': correct,
                'wrong': total - correct,
                'accuracy': accuracy,
                'avg_confidence': avg_confidence
            },
            'by_direction': {}
        }
        
        # 按方向统计
        for direction in ['LONG', 'SHORT', 'WAIT']:
            dir_signals = [s for s in ai_signals if s.get('ai_direction') == direction]
            if not dir_signals:
                continue
            
            dir_total = len(dir_signals)
            dir_correct = len([s for s in dir_signals if s.get('ai_correct')])
            dir_accuracy = (dir_correct / dir_total * 100) if dir_total > 0 else 0
            dir_avg_conf = sum(s.get('ai_score', 0) for s in dir_signals) / dir_total if dir_total > 0 else 0
            
            stats['by_direction'][direction] = {
                'total': dir_total,
                'correct': dir_correct,
                'wrong': dir_total - dir_correct,
                'accuracy': dir_accuracy,
                'avg_confidence': dir_avg_conf
            }
        
        return stats
    
    def get_comparison_stats(self, days: int = 30) -> Dict:
        """
        获取策略 vs AI 对比统计
        
        Returns:
            {
                'strategy': {...},  # 策略统计
                'ai': {...},        # AI 统计
                'agreement': {      # 一致性统计
                    'total': 总数量,
                    'agree': 一致数量,
                    'disagree': 分歧数量,
                    'agree_win_rate': 一致时胜率,
                    'disagree_win_rate': 分歧时胜率
                }
            }
        """
        signals = self.get_closed_signals(days)
        
        # 只统计既有策略置信度又有 AI 评分的信号
        valid_signals = [
            s for s in signals 
            if s.get('confidence') and s.get('ai_score') and s.get('ai_direction')
        ]
        
        if not valid_signals:
            return {}
        
        # 一致性统计
        agree_signals = []
        disagree_signals = []
        
        for sig in valid_signals:
            strategy_dir = sig.get('direction')
            ai_dir = sig.get('ai_direction')
            
            if ai_dir == strategy_dir:
                agree_signals.append(sig)
            elif ai_dir != 'WAIT':  # AI 不是观望且方向不同
                disagree_signals.append(sig)
        
        # 计算胜率
        agree_wins = len([s for s in agree_signals if s.get('pnl_pct', 0) > 0])
        disagree_wins = len([s for s in disagree_signals if s.get('pnl_pct', 0) > 0])
        
        agree_win_rate = (agree_wins / len(agree_signals) * 100) if agree_signals else 0
        disagree_win_rate = (disagree_wins / len(disagree_signals) * 100) if disagree_signals else 0
        
        return {
            'strategy': self.calculate_strategy_stats(days),
            'ai': self.calculate_ai_stats(days),
            'agreement': {
                'total': len(valid_signals),
                'agree': len(agree_signals),
                'disagree': len(disagree_signals),
                'agree_win_rate': agree_win_rate,
                'disagree_win_rate': disagree_win_rate
            }
        }
    
    def print_report(self, days: int = 30):
        """打印统计报告"""
        print("=" * 80)
        print(f"📊 信号表现统计报告 (最近 {days} 天)")
        print("=" * 80)
        
        # 策略统计
        print("\n📈 策略统计:")
        print("-" * 80)
        strategy_stats = self.calculate_strategy_stats(days)
        
        if strategy_stats:
            print(f"{'策略名':<30} {'总数':<8} {'胜率':<10} {'平均盈亏':<10} {'总盈亏':<10}")
            print("-" * 80)
            for strategy, stats in sorted(strategy_stats.items(), key=lambda x: x[1]['win_rate'], reverse=True):
                print(f"{strategy:<30} {stats['total']:<8} {stats['win_rate']:.1f}%      {stats['avg_pnl']:+.2f}%     {stats['total_pnl']:+.2f}%")
        else:
            print("暂无已平仓信号数据")
        
        # AI 统计
        print("\n🤖 AI 统计:")
        print("-" * 80)
        ai_stats = self.calculate_ai_stats(days)
        
        if ai_stats and 'overall' in ai_stats:
            overall = ai_stats['overall']
            print(f"总体: {overall['total']} 次判断，正确 {overall['correct']} 次，准确率 {overall['accuracy']:.1f}%")
            print(f"平均置信度：{overall['avg_confidence']:.1f}%")
            
            if 'by_direction' in ai_stats:
                print("\n按方向:")
                for direction, stats in ai_stats['by_direction'].items():
                    print(f"  {direction}: {stats['total']} 次，准确率 {stats['accuracy']:.1f}%, 平均置信度 {stats['avg_confidence']:.1f}%")
        else:
            print("暂无 AI 评分数据")
        
        # 策略 vs AI 对比
        print("\n⚖️ 策略 vs AI 对比:")
        print("-" * 80)
        comp_stats = self.get_comparison_stats(days)
        
        if comp_stats and 'agreement' in comp_stats:
            agree = comp_stats['agreement']
            print(f"总信号数：{agree['total']}")
            print(f"策略&AI 一致：{agree['agree']} 个，胜率 {agree['agree_win_rate']:.1f}%")
            print(f"策略&AI 分歧：{agree['disagree']} 个，胜率 {agree['disagree_win_rate']:.1f}%")
        else:
            print("暂无对比数据")
        
        print("\n" + "=" * 80)


def main():
    """主函数"""
    stats = SignalStats()
    stats.print_report(30)


if __name__ == '__main__':
    main()
