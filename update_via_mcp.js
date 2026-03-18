#!/usr/bin/env node
/**
 * 使用 MCP 方式调用 feishu_update_doc 工具
 */

const fs = require('fs');
const https = require('https');

// 配置
const APP_ID = 'cli_a9eddbc73ab85bcd';
const APP_SECRET = 'pSul1MqDerYxg6dI69OktfKaxpVAa7qI';
const DOC_ID = 'Kekcdlaypo4wwrxQjuccRFk6nyh';
const MCP_ENDPOINT = 'https://open.feishu.cn/mcp';

// 读取文档内容
const docContent = fs.readFileSync('/home/wz/.openclaw/workspace/ml_trading/DOC_CONTENT.md', 'utf8');

// 获取 user_access_token（通过 OAuth 或其他方式）
// 这里我们使用 tenant_access_token 作为替代
function getTenantAccessToken() {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      app_id: APP_ID,
      app_secret: APP_SECRET
    });

    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: '/open-apis/auth/v3/tenant_access_token/internal',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': data.length
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      res.on('data', (chunk) => responseData += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(responseData);
          if (result.code === 0) {
            resolve(result.tenant_access_token);
          } else {
            reject(new Error(`获取 token 失败：${JSON.stringify(result)}`));
          }
        } catch (e) {
          reject(new Error(`解析失败：${responseData}`));
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

// 调用 MCP 工具
function callMcpTool(toolName, args, uat) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      jsonrpc: '2.0',
      id: 'update-doc-call',
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: args
      }
    });

    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: '/mcp',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': Buffer.byteLength(body),
        'X-Lark-MCP-UAT': uat,
        'X-Lark-MCP-Allowed-Tools': toolName,
        'User-Agent': 'OpenClaw/2026.3.13'
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      res.on('data', (chunk) => responseData += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(responseData);
          resolve({ statusCode: res.statusCode, data: result });
        } catch (e) {
          resolve({ statusCode: res.statusCode, rawData: responseData });
        }
      });
    });

    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  try {
    console.log('📝 开始使用 MCP 更新飞书文档...');
    console.log('文档 ID:', DOC_ID);
    console.log('内容大小:', docContent.length, '字符');
    
    // 获取 token
    console.log('\n🔑 正在获取 tenant_access_token...');
    const token = await getTenantAccessToken();
    console.log('✅ Token 获取成功');
    
    // 调用 MCP 工具
    console.log('\n🔧 正在调用 feishu_update_doc 工具...');
    const result = await callMcpTool('update-doc', {
      doc_id: DOC_ID,
      mode: 'overwrite',
      markdown: docContent
    }, token);
    
    console.log('\n📊 响应状态:', result.statusCode);
    console.log('📄 响应数据:', JSON.stringify(result.data, null, 2));
    
    if (result.statusCode === 200 && result.data?.result) {
      console.log('\n✅ 文档更新成功!');
      console.log('doc_id:', DOC_ID);
      console.log('doc_url:', `https://feishu.cn/docx/${DOC_ID}`);
    } else {
      console.log('\n❌ 文档更新失败');
      if (result.data?.error) {
        console.log('错误:', JSON.stringify(result.data.error, null, 2));
      }
    }
    
  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();
