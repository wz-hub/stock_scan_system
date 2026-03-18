"""
模型验证脚本 - 用 Walk-Forward 交叉验证

讲解：
时间序列不能随机分割，要用 Walk-Forward 验证：
- 第 1 轮：1-70% 训练，70-85% 测试
- 第 2 轮：1-85% 训练，85-100% 测试
- 平均准确率才是真实水平
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from features import FeatureEngineer
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score
import sqlite3

# 数据库路径
DB_PATH = '/home/wz/.openclaw/workspace/trading_system/cache/trading.db'


def load_data(symbol='BTCUSDT', interval='4h', limit=2000):
    """加载数据"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('''
        SELECT timestamp, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND interval = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', conn, params=(symbol, interval, limit))
    conn.close()
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.iloc[::-1]
    
    return df


def walk_forward_validation(df, n_splits=5):
    """
    Walk-Forward 交叉验证
    """
    print(f"\n🔄 Walk-Forward 交叉验证 ({n_splits} 轮)...")
    print("=" * 70)
    
    fe = FeatureEngineer()
    features = fe.calculate_all_features(df)
    label = fe.create_label(df, forward_period=4, threshold=0.0)
    
    # 删除 NaN
    mask = features.notna().all(axis=1) & label.notna()
    features = features[mask]
    label = label[mask]
    
    print(f"总样本：{len(features)}")
    
    # 时间序列分割
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    accuracies = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(features), 1):
        X_train, X_test = features.iloc[train_idx], features.iloc[test_idx]
        y_train, y_test = label.iloc[train_idx], label.iloc[test_idx]
        
        # 训练
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective='binary:logistic',
            eval_metric='logloss',
            verbosity=0
        )
        model.fit(X_train, y_train)
        
        # 测试
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        accuracies.append(acc)
        
        # 标签分布
        train_dist = y_train.value_counts().to_dict()
        test_dist = y_test.value_counts().to_dict()
        
        print(f"\n第 {fold} 轮:")
        print(f"  训练集：{len(X_train)} 样本 (涨:{train_dist.get(1, 0)}, 跌:{train_dist.get(0, 0)})")
        print(f"  测试集：{len(X_test)} 样本 (涨:{test_dist.get(1, 0)}, 跌:{test_dist.get(0, 0)})")
        print(f"  准确率：{acc:.2%}")
    
    print("\n" + "=" * 70)
    print(f"📊 平均准确率：{np.mean(accuracies):.2%} ± {np.std(accuracies):.2%}")
    print(f"最低：{np.min(accuracies):.2%}, 最高：{np.max(accuracies):.2%}")
    
    return accuracies


if __name__ == '__main__':
    print("=" * 70)
    print("🤖 ML Trading - Walk-Forward 交叉验证")
    print("=" * 70)
    
    # 加载数据
    df = load_data('BTCUSDT', '4h', 2000)
    print(f"数据：{len(df)} 根 K 线")
    print(f"时间：{df.index[0]} 到 {df.index[-1]}")
    
    # 交叉验证
    accuracies = walk_forward_validation(df, n_splits=5)
    
    print("\n✅ 验证完成！")
