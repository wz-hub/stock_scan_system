"""
AI 配置诊断工具
帮助排查 404 错误
"""
import json
import requests
from pathlib import Path

print("🔍 AI 配置诊断工具")
print("="*60)

# 加载配置
config_file = Path('config/ai_config.json')
if config_file.exists():
    with open(config_file) as f:
        config = json.load(f)
    print(f"✅ 配置文件：{config_file}")
else:
    print(f"❌ 配置文件不存在：{config_file}")
    config = {}

api_url = config.get('api_url', '')
api_key = config.get('api_key', '')
model = config.get('model', '')
enabled = config.get('enabled', False)

print(f"\n📋 当前配置:")
print(f"  启用状态：{'✅' if enabled else '❌'}")
print(f"  API 地址：{api_url}")
print(f"  模型：{model}")
print(f"  API Key: {'已配置' if api_key else '❌ 未配置'}")

# 测试连接
if not api_key:
    print("\n❌ API Key 未配置，无法测试")
    exit(1)

print("\n🧪 测试 API 连接...")

# 测试请求
test_payload = {
    "model": model,
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "max_tokens": 10
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

try:
    response = requests.post(api_url, headers=headers, json=test_payload, timeout=10)
    
    print(f"\n📊 响应状态码：{response.status_code}")
    
    if response.status_code == 200:
        print("✅ API 连接成功！")
        result = response.json()
        print(f"回复：{result['choices'][0]['message']['content'][:50]}...")
    
    elif response.status_code == 404:
        print("❌ 404 错误 - API 地址不正确")
        print("\n💡 可能的原因:")
        print("  1. API 地址拼写错误")
        print("  2. 该 API 不支持此格式")
        print("  3. 需要更换 API 端点")
        
        # 提供正确的地址
        print("\n✅ 常用的正确 API 地址:")
        print("  通义千问 (DashScope):")
        print("    https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        print("  DeepSeek:")
        print("    https://api.deepseek.com/v1/chat/completions")
        print("  OpenAI:")
        print("    https://api.openai.com/v1/chat/completions")
        
        # 尝试自动修复
        if 'dashscope' in api_url or 'aliyun' in api_url:
            print("\n🔧 检测到是通义千问，尝试修复 API 地址...")
            fixed_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            print(f"  建议地址：{fixed_url}")
            
            # 测试修复后的地址
            print("  测试修复后的地址...")
            try:
                test_response = requests.post(fixed_url, headers=headers, json=test_payload, timeout=10)
                if test_response.status_code == 200:
                    print(f"  ✅ 修复后的地址可用！请在配置中更新为：{fixed_url}")
                else:
                    print(f"  ❌ 修复后的地址也失败：{test_response.status_code}")
            except Exception as e:
                print(f"  ❌ 测试失败：{e}")
    
    elif response.status_code == 401:
        print("❌ 401 错误 - API Key 无效或过期")
        print("💡 请检查 API Key 是否正确")
    
    elif response.status_code == 403:
        print("❌ 403 错误 - 权限不足")
        print("💡 可能原因:")
        print("  - API Key 没有访问该模型的权限")
        print("  - 账户余额不足")
        print("  - IP 地址被限制")
    
    else:
        print(f"❌ 其他错误：{response.status_code}")
        print(f"详情：{response.text[:200]}")
    
    # 显示完整响应
    print(f"\n📄 完整响应:")
    try:
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False)[:500])
    except:
        print(response.text[:500])

except requests.exceptions.Timeout:
    print("❌ 请求超时 - 请检查网络连接")
except requests.exceptions.ConnectionError:
    print("❌ 无法连接到服务器 - 请检查 API 地址或网络")
except Exception as e:
    print(f"❌ 未知错误：{e}")

print("\n" + "="*60)
