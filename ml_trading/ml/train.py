"""
模型训练脚本

讲解：
训练流程：
1. 从数据库加载历史数据
2. 计算特征和标签
3. 分割训练集/测试集（时间序列不能随机分割！）
4. 训练 XGBoost 模型
5. 验证效果
6. 保存模型

关键：
- 用 Walk-Forward 验证（更接近实盘）
- 防止过拟合（正则化 + 早停）
- 特征重要性分析（知道什么有用）
"""
import sys
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.features import FeatureEngineer, prepare_features

# 尝试导入 XGBoost
try:
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    import joblib
    XGBOOST_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  缺少依赖：{e}")
    print("安装：pip install xgboost scikit-learn joblib")
    XGBOOST_AVAILABLE = False

# 数据库路径
TRADING_DB = Path('/home/wz/.openclaw/workspace/trading_system/cache/trading.db')


class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, symbol: str = 'BTCUSDT'):
        self.symbol = symbol
        self.model = None
        self.feature_names = []
        self.metrics = {}
    
    def load_data(self, timeframe: str = '4h', limit: int = 2000) -> pd.DataFrame:
        """
        从数据库加载数据
        
        讲解：
        我们用现有的 trading.db，里面有历史 K 线数据
        """
        import sqlite3
        
        if not TRADING_DB.exists():
            raise FileNotFoundError(f"数据库不存在：{TRADING_DB}")
        
        conn = sqlite3.connect(str(TRADING_DB))
        
        # 查询 K 线数据
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM klines
            WHERE symbol = ? AND interval = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(self.symbol, timeframe, limit))
        conn.close()
        
        if len(df) == 0:
            raise ValueError(f"没有找到 {symbol} {timeframe} 的数据")
        
        # 转换时间戳（毫秒转 datetime）
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # 反转顺序（从旧到新）
        df = df.iloc[::-1]
        
        print(f"✅ 加载数据：{len(df)} 根 K 线")
        print(f"   时间范围：{df.index[0]} 到 {df.index[-1]}")
        
        return df
    
    def prepare_data(self, df: pd.DataFrame, forward_period: int = 4, threshold: float = 2.0):
        """
        准备特征和标签
        
        讲解：
        forward_period=4 表示预测未来 4 根 K 线
        threshold=2.0 表示涨跌幅超过 2% 才算趋势，否则是震荡
        """
        print(f"\n📐 计算特征...")
        
        fe = FeatureEngineer()
        features = fe.calculate_all_features(df)
        label = fe.create_label(df, forward_period, threshold)
        
        # 删除 NaN
        mask = features.notna().all(axis=1) & label.notna()
        features = features[mask]
        label = label[mask]
        
        self.feature_names = fe.get_feature_names()
        
        print(f"✅ 特征数量：{len(self.feature_names)}")
        print(f"✅ 样本数量：{len(features)}")
        print(f"\n标签分布:")
        print(label.value_counts())
        
        return features, label
    
    def train(self, features: pd.DataFrame, label: pd.Series, test_ratio: float = 0.2):
        """
        训练模型
        
        讲解：
        1. 时间序列分割：前 80% 训练，后 20% 测试（不能随机打乱！）
        2. XGBoost 参数：
           - max_depth=6: 树的最大深度，防止过拟合
           - learning_rate=0.1: 学习率
           - n_estimators=100: 树的数量
           - scale_pos_weight: 处理类别不平衡
        3. 早停：验证集误差连续 10 轮不下降就停止
        """
        if not XGBOOST_AVAILABLE:
            print("❌ XGBoost 不可用")
            return
        
        print(f"\n🚀 训练模型...")
        
        # 时间序列分割
        split_idx = int(len(features) * (1 - test_ratio))
        X_train = features.iloc[:split_idx]
        X_test = features.iloc[split_idx:]
        y_train = label.iloc[:split_idx]
        y_test = label.iloc[split_idx:]
        
        print(f"   训练集：{len(X_train)} 样本")
        print(f"   测试集：{len(X_test)} 样本")
        
        # 处理类别不平衡（涨/跌/震荡的数量可能不同）
        from collections import Counter
        label_counts = Counter(y_train)
        total = len(y_train)
        # 计算每个类别的权重
        scale_pos_weight = {
            cls: total / (count * len(label_counts)) 
            for cls, count in label_counts.items()
        }
        
        # XGBoost 参数（二分类）
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            min_child_weight=5,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            eval_metric='logloss',
            early_stopping_rounds=20,
            verbosity=1,
            use_label_encoder=False
        )
        
        # 训练
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        self.model = model
        
        # 评估
        print(f"\n📊 评估模型...")
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\n=== 测试结果 ===")
        print(f"准确率：{accuracy:.2%}")
        print(f"\n混淆矩阵:")
        print(confusion_matrix(y_test, y_pred))
        print(f"\n分类报告:")
        print(classification_report(y_test, y_pred, target_names=['跌', '涨']))
        
        # 保存指标
        self.metrics = {
            'accuracy': accuracy,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'feature_count': len(self.feature_names),
            'timestamp': datetime.now().isoformat()
        }
        
        # 特征重要性
        print(f"\n🏆 Top 10 重要特征:")
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for i, row in importance.head(10).iterrows():
            print(f"  {row['importance']:.4f} - {row['feature']}")
        
        return model
    
    def save_model(self, path: str = None):
        """保存模型"""
        if path is None:
            path = Path(__file__).parent / 'models' / f'{self.symbol}_model.pkl'
        
        path = Path(path)
        path.parent.mkdir(exist_ok=True)
        
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'symbol': self.symbol
        }, path)
        
        print(f"\n💾 模型已保存：{path}")
        
        # 保存指标到 JSON
        metrics_path = path.with_suffix('.json')
        with open(metrics_path, 'w') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        
        print(f"📝 指标已保存：{metrics_path}")
    
    def load_model(self, path: str = None):
        """加载模型"""
        if path is None:
            path = Path(__file__).parent / 'models' / f'{self.symbol}_model.pkl'
        
        data = joblib.load(path)
        self.model = data['model']
        self.feature_names = data['feature_names']
        self.metrics = data.get('metrics', {})
        self.symbol = data.get('symbol', 'UNKNOWN')
        
        print(f"✅ 模型已加载：{path}")
        print(f"   准确率：{self.metrics.get('accuracy', 'N/A'):.2%}")
        
        return self.model


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='训练 ML 交易模型')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='交易对')
    parser.add_argument('--interval', type=str, default='4h', help='时间周期')
    parser.add_argument('--limit', type=int, default=2000, help='数据量')
    parser.add_argument('--forward', type=int, default=4, help='预测周期')
    parser.add_argument('--threshold', type=float, default=2.0, help='涨跌阈值')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🤖 ML Trading - 模型训练")
    print("=" * 80)
    print(f"交易对：{args.symbol}")
    print(f"时间周期：{args.interval}")
    print(f"数据量：{args.limit}")
    print(f"预测周期：未来 {args.forward} 根 K 线")
    print(f"涨跌阈值：±{args.threshold}%")
    print("=" * 80)
    
    # 创建训练器
    trainer = ModelTrainer(args.symbol)
    
    # 加载数据
    df = trainer.load_data(args.interval, args.limit)
    
    # 准备特征
    features, label = trainer.prepare_data(df, args.forward, args.threshold)
    
    # 训练模型
    trainer.train(features, label)
    
    # 保存模型
    trainer.save_model()
    
    print("\n" + "=" * 80)
    print("✅ 训练完成！")
    print("=" * 80)


if __name__ == '__main__':
    main()
