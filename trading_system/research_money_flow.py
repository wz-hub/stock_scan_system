"""
获取 Binance 资金流向数据
- 交易所流入流出
- 大户地址监控
- 链上数据
"""
import requests
import json
from datetime import datetime

print("💰  Binance 资金流向数据调研")
print("="*80)

# 方法 1: Binance API - 现货资金流向
print("\n📊 方法 1: Binance 现货资金流向")
print("-"*80)

# Binance 没有直接的资金流向 API
# 但可以通过以下数据推断：

# 1.1 大户持仓变化
print("1.1 大户持仓变化（通过持仓量推断）")
url = "https://fapi.binance.com/fapi/v1/openInterest"
params = {"symbol": "BTCUSDT"}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    print(f"  BTC 持仓量：{data['openInterest']} BTC")
    print(f"  时间：{datetime.fromtimestamp(data['time']/1000)}")
except Exception as e:
    print(f"  ❌ 获取失败：{e}")

# 1.2 合约持仓量
print("\n1.2 合约持仓量变化")
url = "https://fapi.binance.com/fapi/v1/openInterestHist"
params = {
    "symbol": "BTCUSDT",
    "period": "5m",
    "limit": 10
}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    if len(data) >= 2:
        current_oi = float(data[-1]['openInterest'])
        prev_oi = float(data[-2]['openInterest'])
        change = current_oi - prev_oi
        change_pct = (change / prev_oi) * 100
        
        print(f"  当前持仓：{current_oi:,.0f} BTC")
        print(f"  上期持仓：{prev_oi:,.0f} BTC")
        print(f"  变化：{change:+,.0f} BTC ({change_pct:+.2f}%)")
        print(f"  解读：{'资金流入 🟢' if change > 0 else '资金流出 🔴'}")
except Exception as e:
    print(f"  ❌ 获取失败：{e}")

# 1.3 大户账户多空比
print("\n1.3 大户账户多空比")
url = "https://fapi.binance.com/futures/data/topLongShortAccountRatio"
params = {
    "symbol": "BTCUSDT",
    "period": "5m",
    "limit": 5
}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    if data:
        latest = data[-1]
        print(f"  大户做多比：{latest['longAccount']}")
        print(f"  大户做空比：{latest['shortAccount']}")
        print(f"  多空比：{float(latest['longAccount'])/float(latest['shortAccount']):.2f}")
except Exception as e:
    print(f"  ❌ 获取失败：{e}")

# 1.4 合约持仓量多空比
print("\n1.4 合约持仓量多空比")
url = "https://fapi.binance.com/futures/data/topLongShortPositionRatio"
params = {
    "symbol": "BTCUSDT",
    "period": "5m",
    "limit": 5
}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    if data:
        latest = data[-1]
        print(f"  做多持仓比：{latest['longPos']}")
        print(f"  做空持仓比：{latest['shortPos']}")
        print(f"  多空比：{float(latest['longPos'])/float(latest['shortPos']):.2f}")
except Exception as e:
    print(f"  ❌ 获取失败：{e}")

# 方法 2: 链上数据（需要第三方 API）
print("\n💎 方法 2: 链上资金流向（需要第三方 API）")
print("-"*80)

third_party_apis = {
    "CryptoQuant": {
        "url": "https://api.cryptoquant.com",
        "data": ["交易所流入", "交易所流出", "鲸鱼地址", "矿工储备"],
        "free_tier": "有限制",
        "note": "需要注册获取 API Key"
    },
    "Glassnode": {
        "url": "https://api.glassnode.com",
        "data": ["链上转账", "交易所净流量", "大户持仓"],
        "free_tier": "免费数据有限",
        "note": "专业链上分析平台"
    },
    "Whale Alert": {
        "url": "https://api.whale-alert.io",
        "data": ["大额转账", "交易所转账"],
        "free_tier": "每月 1000 次",
        "note": "监控鲸鱼大额转账"
    },
    "Arkham": {
        "url": "https://api.arkhamintelligence.com",
        "data": ["地址标签", "资金流向", "机构持仓"],
        "free_tier": "免费额度",
        "note": "地址追踪和标签"
    }
}

for name, info in third_party_apis.items():
    print(f"\n{name}:")
    print(f"  数据类型：{', '.join(info['data'])}")
    print(f"  免费额度：{info['free_tier']}")
    print(f"  说明：{info['note']}")

# 方法 3: 通过交易量推断
print("\n📊 方法 3: 通过交易量推断资金流向")
print("-"*80)

# 获取多个币种的交易量
url = "https://api.binance.com/api/v3/ticker/24hr"
response = requests.get(url, timeout=10)
data = response.json()

# 筛选主流币种
main_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']

print("主流币种 24h 交易量（推断资金热度）:")
for item in data:
    if item['symbol'] in main_symbols:
        volume_usdt = float(item['quoteVolume']) / 1e6
        change = float(item['priceChangePercent'])
        print(f"  {item['symbol']}: {volume_usdt:,.0f}M USDT  ({change:+.1f}%)")

# 总结
print("\n" + "="*80)
print("📋 总结：可用的资金流向监控方案")
print("="*80)

print("""
✅ 立即可用（Binance API）:
  1. 合约持仓量变化 → 判断资金流入流出
  2. 大户多空比 → 判断大户方向
  3. 持仓量多空比 → 判断市场情绪
  4. 交易量变化 → 判断资金热度

⚠️ 需要第三方 API:
  1. CryptoQuant - 交易所资金流向
  2. Glassnode - 链上数据分析
  3. Whale Alert - 大额转账监控
  4. Arkham - 地址追踪

💡 建议方案:
  1. 先用 Binance API 数据（免费、实时）
  2. 有需要再接入 CryptoQuant（专业资金流向）
  3. 关注 Whale Alert 大额转账提醒
""")

# 保存调研结果
result = {
    "binance_apis": {
        "openInterest": "持仓量数据",
        "openInterestHist": "持仓量历史",
        "topLongShortAccountRatio": "大户账户多空比",
        "topLongShortPositionRatio": "持仓量多空比"
    },
    "third_party": list(third_party_apis.keys()),
    "recommended": [
        "持仓量变化",
        "大户多空比",
        "交易量变化"
    ]
}

output_file = '/home/wz/.openclaw/workspace/trading_system/data/money_flow_research.json'
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f"\n✅ 调研报告已保存：{output_file}")
