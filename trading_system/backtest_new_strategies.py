"""
新策略回测脚本
回测 4 个新增策略：
1. Multi-Timeframe Resonance (多周期共振)
2. Volatility Squeeze Breakout (波动率收缩)
3. Money Flow Tracker (资金流追踪)
4. Liquidity Hunt (流动性猎杀)
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from backtest.engine import BacktestEngine
from backtest.data_loader import DataLoader, load_data
from strategies import (
    MultiTimeframeStrategy,
    VolatilitySqueezeStrategy,
    MoneyFlowStrategy,
    LiquidityHuntStrategy
)


def run_single_strategy_backtest(strategy, df: pd.DataFrame, 
                                  initial_capital: float = 100000.0,
                                  symbol: str = 'BTC-USD') -> dict:
    """
    运行单个策略回测
    
    Args:
        strategy: 策略实例
        df: K 线数据 (1D)
        initial_capital: 初始资金
        symbol: 交易标的
    
    Returns:
        回测结果字典
    """
    engine = BacktestEngine(initial_capital=initial_capital)
    engine.reset()
    
    trades = []
    current_action = 'WAIT'
    
    print(f"\n回测 {strategy.__class__.__name__}...")
    print(f"数据范围：{df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"数据长度：{len(df)} 根 K 线")
    
    # 遍历 K 线
    for i in range(len(df)):
        idx = df.index[i]
        row = df.iloc[i]
        
        if pd.isna(row.get('close', np.nan)):
            continue
        
        current_price = row['close']
        
        # 获取策略信号
        if hasattr(strategy, 'generate_signal'):
            # 新策略使用 generate_signal 方法
            if isinstance(strategy, MultiTimeframeStrategy):
                # 多周期策略需要多周期数据
                continue  # 跳过，单独处理
            else:
                signal = strategy.generate_signal(df.iloc[:i+1], symbol)
        else:
            continue
        
        if signal is None:
            engine.update_equity(current_price)
            continue
        
        action = signal.get('action', 'WAIT')
        
        # 执行交易
        if action == 'BUY' and current_action != 'BUY':
            # 平仓之前的空头
            if engine.position.direction == 'short':
                engine.buy(current_price, str(idx.date()), reason='close_short')
            
            # 开多
            if engine.position.direction == '':
                size = (engine.capital * 0.20) / current_price  # 20% 仓位
                engine.buy(current_price, str(idx.date()), size=size)
                trades.append({
                    'date': str(idx.date()),
                    'type': 'BUY',
                    'price': current_price,
                    'signal_confidence': signal.get('confidence', 0)
                })
        
        elif action == 'SELL' and current_action != 'SELL':
            # 平仓之前的多头
            if engine.position.direction == 'long':
                engine.sell(current_price, str(idx.date()))
                trades.append({
                    'date': str(idx.date()),
                    'type': 'SELL',
                    'price': current_price,
                    'signal_confidence': signal.get('confidence', 0)
                })
            
            # 开空（如果支持）
            # 暂时不做空，简化回测
        
        current_action = action
        engine.update_equity(current_price)
    
    # 平仓
    if engine.position.direction == 'long':
        engine.sell(df.iloc[-1]['close'], str(df.index[-1].date()), reason='end')
    
    # 获取指标
    metrics = engine.get_metrics()
    metrics['strategy_name'] = strategy.__class__.__name__
    metrics['total_trades'] = len(trades)
    metrics['trades'] = trades
    
    return metrics, engine


def run_multi_timeframe_backtest(df: pd.DataFrame, 
                                  initial_capital: float = 100000.0,
                                  symbol: str = 'BTC-USD') -> dict:
    """
    多周期共振策略回测（特殊处理）
    """
    from realtime_data import RealtimeData
    
    engine = BacktestEngine(initial_capital=initial_capital)
    engine.reset()
    
    rt = RealtimeData()
    trades = []
    
    print(f"\n回测 Multi-Timeframe Resonance (多周期共振)...")
    print(f"数据范围：{df.index[0].date()} 到 {df.index[-1].date()}")
    
    # 从第 100 天开始（确保有足够历史数据）
    start_idx = 100
    
    for i in range(start_idx, len(df)):
        idx = df.index[i]
        current_price = df.iloc[i]['close']
        
        # 获取多周期数据
        try:
            data_dict = {}
            for tf in ['1d', '4h', '1h']:
                klines = rt.get_binance_klines(symbol.replace('-USD', 'USDT'), interval=tf, limit=200)
                if klines.empty:
                    continue
                data_dict[tf.upper()] = klines
            
            if len(data_dict) < 3:
                engine.update_equity(current_price)
                continue
            
            # 生成信号
            mt_strategy = MultiTimeframeStrategy()
            signal = mt_strategy.generate_signal(data_dict, symbol)
            
            if signal is None or signal.get('action') == 'WAIT':
                engine.update_equity(current_price)
                continue
            
            action = signal.get('action')
            confidence = signal.get('confidence', 0)
            
            # 只交易高置信度信号
            if confidence < 70:
                engine.update_equity(current_price)
                continue
            
            # 执行交易
            if action == 'BUY' and engine.position.direction != 'long':
                size = (engine.capital * 0.20) / current_price
                engine.buy(current_price, str(idx.date()), size=size)
                trades.append({
                    'date': str(idx.date()),
                    'type': 'BUY',
                    'price': current_price,
                    'confidence': confidence
                })
            
            elif action == 'SELL' and engine.position.direction == 'long':
                engine.sell(current_price, str(idx.date()))
                trades.append({
                    'date': str(idx.date()),
                    'type': 'SELL',
                    'price': current_price,
                    'confidence': confidence
                })
            
            engine.update_equity(current_price)
            
            # 避免 API 限流
            import time
            time.sleep(0.3)
            
        except Exception as e:
            print(f"Error at {idx}: {e}")
            engine.update_equity(current_price)
            continue
    
    # 平仓
    if engine.position.direction == 'long':
        engine.sell(df.iloc[-1]['close'], str(df.index[-1].date()), reason='end')
    
    metrics = engine.get_metrics()
    metrics['strategy_name'] = 'Multi-Timeframe Resonance'
    metrics['total_trades'] = len(trades)
    metrics['trades'] = trades
    
    return metrics, engine


def print_metrics(metrics: dict, engine: BacktestEngine):
    """打印回测结果"""
    print("\n" + "="*80)
    print(f"策略：{metrics['strategy_name']}")
    print("="*80)
    
    print(f"\n📊 交易统计:")
    print(f"  总交易次数：{metrics.get('total_trades', 0)}")
    print(f"  盈利次数：{metrics.get('winning_trades', 0)}")
    print(f"  亏损次数：{metrics.get('losing_trades', 0)}")
    print(f"  胜率：{metrics.get('win_rate', 0)*100:.1f}%")
    
    print(f"\n💰 收益统计:")
    print(f"  总盈亏：${metrics.get('total_pnl', 0):,.2f}")
    print(f"  总收益率：{metrics.get('total_return', 0)*100:.2f}%")
    print(f"  最终资金：${metrics.get('final_equity', 0):,.2f}")
    
    print(f"\n📈 风险指标:")
    print(f"  夏普比率：{metrics.get('sharpe_ratio', 0):.2f}")
    print(f"  最大回撤：{metrics.get('max_drawdown', 0)*100:.2f}%")
    print(f"  盈亏比：{metrics.get('avg_win', 0)/metrics.get('avg_loss', 1) if metrics.get('avg_loss', 0) > 0 else 'N/A':.2f}")
    
    print("="*80)


def main():
    """主函数"""
    print("🧪 新策略回测")
    print("="*80)
    
    # 测试标的
    symbols = ['BTC-USD', 'ETH-USD']
    
    # 策略列表
    strategies = [
        ('Volatility Squeeze', VolatilitySqueezeStrategy()),
        ('Money Flow', MoneyFlowStrategy()),
        ('Liquidity Hunt', LiquidityHuntStrategy()),
    ]
    
    results = {}
    
    for symbol in symbols:
        print(f"\n\n{'='*80}")
        print(f"回测标的：{symbol}")
        print(f"{'='*80}")
        
        # 加载数据
        try:
            df = load_data(symbol, start_date='2023-01-01', end_date='2026-03-09')
        except Exception as e:
            print(f"⚠️ {symbol} 数据加载失败：{e}")
            print(f"   使用模拟数据...")
            df = DataLoader().generate_synthetic(days=500, start_price=50000 if 'BTC' in symbol else 3000)
        
        if df.empty:
            print(f"⚠️ {symbol} 无数据，跳过")
            continue
        
        # 回测每个策略
        for name, strategy in strategies:
            try:
                metrics, engine = run_single_strategy_backtest(
                    strategy, df, 
                    initial_capital=100000.0,
                    symbol=symbol
                )
                
                results[f"{symbol}_{name}"] = metrics
                print_metrics(metrics, engine)
                
            except Exception as e:
                print(f"❌ {name} 回测失败：{e}")
                import traceback
                traceback.print_exc()
        
        # 多周期策略（单独处理）
        try:
            metrics, engine = run_multi_timeframe_backtest(
                df,
                initial_capital=100000.0,
                symbol=symbol
            )
            results[f"{symbol}_Multi-Timeframe"] = metrics
            print_metrics(metrics, engine)
        except Exception as e:
            print(f"❌ Multi-Timeframe 回测失败：{e}")
    
    # 保存结果
    if results:
        results_dir = Path('backtest/results')
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = results_dir / f"new_strategies_backtest_{timestamp}.json"
        
        # 转换结果为可序列化格式
        serializable_results = {}
        for key, metrics in results.items():
            serializable_results[key] = {
                k: (v if not isinstance(v, list) else len(v)) 
                for k, v in metrics.items() 
                if k != 'trades'
            }
        
        import json
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 回测结果已保存：{results_file}")
    
    print("\n✅ 回测完成！")


if __name__ == '__main__':
    main()
