"""
主回测运行脚本
运行所有策略并生成报告
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from backtest.engine import BacktestEngine, Trade
from backtest.data_loader import DataLoader, load_data
from strategies import (
    TrendFollowingStrategy,
    Reversal123Strategy,
    SupportResistanceStrategy,
    PatternTradingStrategy,
    MACrossStrategy,
    VolatilityBreakoutStrategy,
    PairsTradingStrategy,
    BollingerBandsStrategy,
    RSIStrategy,
    BreakoutStrategy
)


def run_backtest(strategy, df: pd.DataFrame, initial_capital: float = 100000.0) -> dict:
    """运行单个策略回测"""
    engine = BacktestEngine(initial_capital=initial_capital)
    engine.reset()
    
    # 生成信号
    signals_df = strategy.generate_signals(df)
    
    # 模拟交易 - 基于 position 列
    current_position = 0  # 0: 空仓，1: 多仓，-1: 空仓
    
    for i in range(len(signals_df)):
        idx = signals_df.index[i]
        row = signals_df.iloc[i]
        
        # 跳过无效数据
        if pd.isna(row.get('close', np.nan)):
            current_position = int(row.get('position', 0)) if not pd.isna(row.get('position', 0)) else 0
            engine.update_equity(row['close'])
            continue
        
        target_position = int(row.get('position', 0)) if not pd.isna(row.get('position', 0)) else 0
        
        # 位置变化时执行交易
        if target_position != current_position:
            # 平仓
            if current_position == 1 and target_position != 1:
                engine.sell(row['close'], str(idx.date()))
            elif current_position == -1 and target_position != -1:
                engine.buy(row['close'], str(idx.date()), reason='close_short')
            
            # 开仓
            if target_position == 1 and current_position != 1:
                engine.buy(row['close'], str(idx.date()))
            elif target_position == -1 and current_position != -1:
                engine.sell(row['close'], str(idx.date()))
        
        current_position = target_position
        engine.update_equity(row['close'])
    
    # 平仓
    if engine.position.direction != '':
        engine.close_all(df.iloc[-1]['close'], str(df.index[-1].date()))
    
    # 获取指标
    metrics = engine.get_metrics()
    metrics['strategy_name'] = strategy.name
    
    return metrics, engine


def run_all_strategies(df: pd.DataFrame, initial_capital: float = 100000.0) -> pd.DataFrame:
    """运行所有策略回测"""
    strategies = [
        TrendFollowingStrategy(),
        Reversal123Strategy(),
        SupportResistanceStrategy(),
        PatternTradingStrategy(),
        MACrossStrategy(),
        VolatilityBreakoutStrategy(),
        BollingerBandsStrategy(),
        RSIStrategy(),
        BreakoutStrategy(),
    ]
    
    results = []
    
    print(f"\n{'='*60}")
    print(f"开始回测 - 数据范围：{df.index[0].date()} 至 {df.index[-1].date()}")
    print(f"初始资金：${initial_capital:,.2f}")
    print(f"{'='*60}\n")
    
    for strategy in strategies:
        print(f"回测策略：{strategy.name}...")
        try:
            metrics, engine = run_backtest(strategy, df, initial_capital)
            results.append(metrics)
            
            # 打印简要结果
            print(f"  总收益：{metrics.get('total_return', 0)*100:.2f}%")
            print(f"  胜率：{metrics.get('win_rate', 0)*100:.1f}%")
            print(f"  最大回撤：{metrics.get('max_drawdown', 0)*100:.2f}%")
            print(f"  夏普比率：{metrics.get('sharpe_ratio', 0):.2f}")
            print()
        except Exception as e:
            print(f"  ❌ 错误：{e}")
            results.append({
                'strategy_name': strategy.name,
                'error': str(e)
            })
    
    return pd.DataFrame(results)


def generate_report(results_df: pd.DataFrame, output_dir: str = 'results'):
    """生成回测报告"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存详细结果
    results_file = output_path / f"backtest_results_{timestamp}.csv"
    results_df.to_csv(results_file, index=False)
    print(f"\n详细结果已保存至：{results_file}")
    
    # 生成 Markdown 报告
    report_file = output_path / f"backtest_report_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 交易策略回测报告\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 排序（按总收益）
        if 'total_return' in results_df.columns:
            sorted_df = results_df.sort_values('total_return', ascending=False)
        else:
            sorted_df = results_df
        
        # 摘要表格
        f.write("## 📊 策略表现排名\n\n")
        f.write("| 排名 | 策略 | 总收益 | 胜率 | 最大回撤 | 夏普比率 | 交易次数 |\n")
        f.write("|------|------|--------|------|----------|----------|----------|\n")
        
        for idx, row in sorted_df.iterrows():
            rank = idx + 1
            name = row.get('strategy_name', 'Unknown')
            total_return = f"{row.get('total_return', 0)*100:.2f}%"
            win_rate = f"{row.get('win_rate', 0)*100:.1f}%"
            max_dd = f"{row.get('max_drawdown', 0)*100:.2f}%"
            sharpe = f"{row.get('sharpe_ratio', 0):.2f}"
            trades = row.get('total_trades', 0)
            
            f.write(f"| {rank} | {name} | {total_return} | {win_rate} | {max_dd} | {sharpe} | {trades} |\n")
        
        f.write("\n\n")
        
        # 详细指标
        f.write("## 📈 详细指标\n\n")
        
        for idx, row in sorted_df.iterrows():
            f.write(f"### {row.get('strategy_name', 'Unknown')}\n\n")
            f.write(f"- 总收益：{row.get('total_return', 0)*100:.2f}%\n")
            f.write(f"- 总盈亏：${row.get('total_pnl', 0):,.2f}\n")
            f.write(f"- 最终权益：${row.get('final_equity', 0):,.2f}\n")
            f.write(f"- 交易次数：{row.get('total_trades', 0)}\n")
            f.write(f"- 胜率：{row.get('win_rate', 0)*100:.1f}%\n")
            f.write(f"- 盈利交易：{row.get('winning_trades', 0)}\n")
            f.write(f"- 亏损交易：{row.get('losing_trades', 0)}\n")
            f.write(f"- 平均盈利：${row.get('avg_win', 0):,.2f}\n")
            f.write(f"- 平均亏损：${row.get('avg_loss', 0):,.2f}\n")
            f.write(f"- 盈亏比：{row.get('profit_factor', 0):.2f}\n")
            f.write(f"- 最大回撤：{row.get('max_drawdown', 0)*100:.2f}%\n")
            f.write(f"- 夏普比率：{row.get('sharpe_ratio', 0):.2f}\n")
            f.write("\n---\n\n")
        
        # 建议
        f.write("## 💡 建议\n\n")
        
        if len(sorted_df) > 0:
            best = sorted_df.iloc[0]
            f.write(f"**最佳策略**: {best.get('strategy_name', 'Unknown')}\n\n")
            
            # 筛选稳健策略
            stable_strategies = sorted_df[
                (sorted_df['max_drawdown'] > -0.2) & 
                (sorted_df['sharpe_ratio'] > 0.5) &
                (sorted_df['win_rate'] > 0.4)
            ]
            
            if len(stable_strategies) > 0:
                f.write("**稳健策略推荐**:\n")
                for idx, row in stable_strategies.head(3).iterrows():
                    f.write(f"- {row.get('strategy_name', 'Unknown')}: 收益 {row.get('total_return', 0)*100:.1f}%, "
                           f"回撤 {row.get('max_drawdown', 0)*100:.1f}%\n")
    
    print(f"报告已保存至：{report_file}")
    return report_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='交易策略回测系统')
    parser.add_argument('--symbol', type=str, default=None, help='交易标的 (如 BTC-USD, AAPL)')
    parser.add_argument('--start', type=str, default='2020-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2024-12-31', help='结束日期')
    parser.add_argument('--capital', type=float, default=100000.0, help='初始资金')
    parser.add_argument('--synthetic', action='store_true', help='使用模拟数据')
    parser.add_argument('--data', type=str, default=None, help='本地 CSV 数据文件路径')
    
    args = parser.parse_args()
    
    # 加载数据
    if args.data:
        loader = DataLoader()
        df = loader.load_csv(args.data)
    else:
        df = load_data(
            symbol=args.symbol,
            start_date=args.start,
            end_date=args.end,
            use_synthetic=args.synthetic
        )
    
    print(f"\n数据加载完成:")
    print(f"  记录数：{len(df)}")
    print(f"  日期范围：{df.index[0].date()} 至 {df.index[-1].date()}")
    print(f"  价格范围：${df['low'].min():.2f} - ${df['high'].max():.2f}")
    
    # 运行回测
    results_df = run_all_strategies(df, args.capital)
    
    # 生成报告
    generate_report(results_df)
    
    print("\n✅ 回测完成!")
    
    return results_df


if __name__ == '__main__':
    main()
