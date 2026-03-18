"""
特征工程模块

讲解：
特征工程是机器学习交易系统的核心。
好的特征 = 模型能学到有效规律
差的特征 = 模型只能记住噪音

我们构建 50+ 个特征，分为 5 大类：
1. 技术指标 - 经典但有效
2. 价量特征 - 最直接的信息
3. 波动率特征 - 衡量风险
4. 市场结构 - 位置感
5. 时间特征 - 周期性模式
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class FeatureEngineer:
    """特征工程器"""
    
    def __init__(self):
        # 特征名称列表（用于保存顺序）
        self.feature_names = []
    
    def calculate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有特征
        
        Args:
            df: K 线数据，必须包含列：open, high, low, close, volume
        
        Returns:
            特征 DataFrame
        """
        features = pd.DataFrame(index=df.index)
        
        # === 1. 价量特征（最基础）===
        features = self._add_price_volume_features(features, df)
        
        # === 2. 技术指标 ===
        features = self._add_technical_indicators(features, df)
        
        # === 3. 波动率特征 ===
        features = self._add_volatility_features(features, df)
        
        # === 4. 市场结构特征 ===
        features = self._add_market_structure_features(features, df)
        
        # === 5. 时间特征 ===
        features = self._add_time_features(features, df)
        
        # 保存特征名称
        self.feature_names = features.columns.tolist()
        
        return features
    
    def _add_price_volume_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        价量特征
        
        逻辑：价格和成交量是最原始的信息，其他指标都是从这里衍生出来的
        """
        close = df['close']
        volume = df['volume']
        
        # --- 收益率特征 ---
        # 过去 1/4/12/24 根 K 线的收益率
        for period in [1, 4, 12, 24]:
            features[f'return_{period}'] = close.pct_change(period) * 100
        
        # 当前收益率（相对于开盘）
        features['return_current'] = (close - df['open']) / df['open'] * 100
        
        # --- 成交量特征 ---
        # 成交量比率：当前成交量 / 过去 20 根平均成交量
        features['volume_ratio'] = volume / volume.rolling(20).mean()
        
        # 成交量变化率
        features['volume_change'] = volume.pct_change(1) * 100
        features['volume_change_4'] = volume.pct_change(4) * 100
        
        # 量价关系：价格上涨 + 放量 = 强势
        features['price_volume_corr'] = close.rolling(20).corr(volume)
        
        return features
    
    def _add_technical_indicators(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        技术指标
        
        逻辑：经典指标经过几十年验证，虽然简单但有信息量
        """
        close = df['close']
        high = df['high']
        low = df['low']
        
        # --- RSI (相对强弱指标) ---
        # 逻辑：衡量超买超卖，0-100，>70 超买，<30 超卖
        for period in [7, 14, 21]:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = -delta.where(delta < 0, 0).rolling(period).mean()
            rs = gain / loss
            features[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # --- MACD (移动平均收敛发散) ---
        # 逻辑：快慢线交叉，判断趋势
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        features['macd'] = ema12 - ema26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_hist'] = features['macd'] - features['macd_signal']
        
        # --- 布林带 ---
        # 逻辑：价格通道，衡量超买超卖 + 波动率
        for period in [20]:
            sma = close.rolling(period).mean()
            std = close.rolling(period).std()
            features[f'bb_upper_{period}'] = (close - (sma + 2 * std)) / close * 100
            features[f'bb_lower_{period}'] = (close - (sma - 2 * std)) / close * 100
            features[f'bb_width_{period}'] = (2 * std) / sma * 100  # 带宽
            features[f'bb_position'] = (close - sma) / (2 * std)  # 价格在布林带中的位置 (-1 到 1)
        
        # --- CCI (商品通道指标) ---
        # 逻辑：衡量价格偏离统计平均值的程度
        tp = (high + low + close) / 3
        tp_mean = tp.rolling(20).mean()
        tp_std = tp.rolling(20).std()
        features['cci_20'] = (tp - tp_mean) / (0.015 * tp_std)
        
        # --- 随机指标 (KDJ) ---
        # 逻辑：衡量收盘价在高低点中的位置
        for period in [9, 14]:
            lowest_low = low.rolling(period).min()
            highest_high = high.rolling(period).max()
            features[f'kdj_k_{period}'] = (close - lowest_low) / (highest_high - lowest_low) * 100
        
        return features
    
    def _add_volatility_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        波动率特征
        
        逻辑：波动率衡量风险和机会，高波动 = 高风险高收益
        """
        close = df['close']
        high = df['high']
        low = df['low']
        
        # --- ATR (平均真实波幅) ---
        # 逻辑：衡量波动性的绝对值
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        for period in [7, 14]:
            features[f'atr_{period}'] = tr.rolling(period).mean() / close * 100
        
        # --- 波动率比率 ---
        # 当前波动率 / 过去平均波动率
        returns = close.pct_change()
        current_vol = returns.rolling(7).std()
        avg_vol = returns.rolling(30).std()
        features['volatility_ratio'] = current_vol / avg_vol
        
        # --- 高低点幅度 ---
        features['high_low_range'] = (high - low) / close * 100
        features['high_low_range_ma'] = features['high_low_range'].rolling(10).mean()
        
        return features
    
    def _add_market_structure_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        市场结构特征
        
        逻辑：价格在历史中的位置很重要，突破前高/前低往往是重要信号
        """
        close = df['close']
        high = df['high']
        low = df['low']
        
        # --- 距离高低点的百分比 ---
        for period in [24, 48, 168]:  # 24H, 48H, 1 周
            highest = high.rolling(period).max()
            lowest = low.rolling(period).min()
            features[f'dist_from_high_{period}'] = (highest - close) / highest * 100
            features[f'dist_from_low_{period}'] = (close - lowest) / lowest * 100
            features[f'price_position_{period}'] = (close - lowest) / (highest - lowest)  # 0-1
        
        # --- 突破信号 ---
        # 是否突破过去 N 根 K 线的高点/低点
        for period in [20, 50]:
            features[f'breakout_high_{period}'] = (close > high.rolling(period).max().shift(1)).astype(int)
            features[f'breakout_low_{period}'] = (close < low.rolling(period).min().shift(1)).astype(int)
        
        # --- 均线系统 ---
        for period in [20, 50, 200]:
            ma = close.rolling(period).mean()
            features[f'ma_{period}'] = ma
            features[f'ma_dist_{period}'] = (close - ma) / ma * 100  # 价格偏离均线 %
        
        # 均线排列
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        features['ma_alignment'] = ((ma20 > ma50).astype(int))  # 多头排列=1, 空头=0
        
        return features
    
    def _add_time_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        时间特征
        
        逻辑：加密市场有周期性模式（如周末效应、亚洲/欧美时段）
        """
        # 确保索引是 datetime
        if not isinstance(features.index, pd.DatetimeIndex):
            features.index = pd.to_datetime(features.index)
        
        # 小时 (0-23)
        features['hour'] = features.index.hour
        
        # 星期几 (0=周一，6=周日)
        features['day_of_week'] = features.index.dayofweek
        
        # 月份
        features['month'] = features.index.month
        
        # 是否周末
        features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
        
        # 时段（亚洲/欧洲/美洲）
        hour = features['hour']
        features['session_asia'] = ((hour >= 0) & (hour < 8)).astype(int)
        features['session_europe'] = ((hour >= 8) & (hour < 16)).astype(int)
        features['session_us'] = ((hour >= 16) & (hour < 24)).astype(int)
        
        return features
    
    def create_label(self, df: pd.DataFrame, forward_period: int = 4, threshold: float = 2.0) -> pd.Series:
        """
        创建标签（要预测的目标）
        
        逻辑：预测未来 N 根 K 线的涨跌幅是否超过阈值
        
        Args:
            df: K 线数据
            forward_period: 向前看多少根 K 线
            threshold: 涨跌幅阈值 (%)
        
        Returns:
            标签 Series (1=涨超阈值，0=跌超阈值，-1=震荡)
        """
        close = df['close']
        
        # 未来收益率
        future_return = close.shift(-forward_period) / close * 100 - 100
        
        # 二分类：涨 (1)/跌 (0)
        label = (future_return > threshold).astype(int)
        
        return label
    
    def get_feature_names(self) -> List[str]:
        """获取特征名称列表"""
        return self.feature_names


# 便捷函数
def prepare_features(df: pd.DataFrame, forward_period: int = 4, threshold: float = 2.0) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    准备特征和标签
    
    Returns:
        (features, label, feature_names)
    """
    fe = FeatureEngineer()
    features = fe.calculate_all_features(df)
    label = fe.create_label(df, forward_period, threshold)
    
    # 删除 NaN
    mask = features.notna().all(axis=1) & label.notna()
    features = features[mask]
    label = label[mask]
    
    return features, label, fe.get_feature_names()


# 测试
if __name__ == '__main__':
    print("测试特征工程模块...")
    
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=500, freq='1H')
    np.random.seed(42)
    test_df = pd.DataFrame({
        'open': np.random.randn(500).cumsum() + 100,
        'high': np.random.randn(500).cumsum() + 101,
        'low': np.random.randn(500).cumsum() + 99,
        'close': np.random.randn(500).cumsum() + 100,
        'volume': np.abs(np.random.randn(500)) * 1000
    }, index=dates)
    
    # 计算特征
    features, label, names = prepare_features(test_df)
    
    print(f"\n✅ 特征数量：{len(names)}")
    print(f"\n前 20 个特征:")
    for i, name in enumerate(names[:20]):
        print(f"  {i+1}. {name}")
    
    print(f"\n标签分布:")
    print(label.value_counts())
    
    print(f"\n特征统计:")
    print(features.describe().round(2))
