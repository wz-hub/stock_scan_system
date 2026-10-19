"""
测试阿里云提供的 API 配置
"""
import os
import requests
import json

# Boss 提供的配置
API_URL = "https://coding.dashscope.aliyuncs.com/v1"
# 密钥不再硬编码：本仓库是公开仓库，导出环境变量后再运行
#   export DASHSCOPE_API_KEY=sk-xxxx
API_KEY = os.getenv("DASHSCOPE_API_KEY", "").strip()
MODEL = "qwen3.5-plus"

if not API_KEY:
    raise SystemExit("未设置 DASHSCOPE_API_KEY 环境变量，无法测试。")

print("🧪 测试阿里云 API 配置")
print("="*60)
print(f"API 地址：{API_URL}")
print(f"模型：{MODEL}")
print(f"API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
print("="*60)

# 测试请求
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# 尝试不同的端点
endpoints = [
    "/chat/completions",
    "/v1/chat/completions",
    "/api/v1/services/aigc/text-generation/generation"
]

test_payload = {
    "model": MODEL,
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "max_tokens": 10
}

for endpoint in endpoints:
    full_url = API_URL.rstrip('/') + endpoint
    print(f"\n📍 测试端点：{full_url}")
    
    try:
        response = requests.post(full_url, headers=headers, json=test_payload, timeout=10)
        print(f"  状态码：{response.status_code}")
        
        if response.status_code == 200:
            print(f"  ✅ 成功！")
            result = response.json()
            print(f"  回复：{result['choices'][0]['message']['content'][:50]}...")
            break
        else:
            try:
                error = response.json()
                print(f"  ❌ 错误：{error.get('error', {}).get('message', 'Unknown')}")
            except:
                print(f"  ❌ 错误：{response.text[:100]}")
    
    except Exception as e:
        print(f"  ❌ 异常：{e}")

print("\n" + "="*60)

# 单独测试 Boss 提供的地址
print("\n🔍 单独测试提供的地址...")
full_url = API_URL
response = requests.post(full_url, headers=headers, json=test_payload, timeout=10)
print(f"直接访问 {full_url} 的状态码：{response.status_code}")
print(f"响应：{response.text[:300]}")
