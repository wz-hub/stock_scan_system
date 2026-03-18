const https = require('https');
const fs = require('fs');

// 配置
const APP_ID = 'cli_a9eddbc73ab85bcd';
const APP_SECRET = 'pSul1MqDerYxg6dI69OktfKaxpVAa7qI';
const DOC_ID = 'Kekcdlaypo4wwrxQjuccRFk6nyh';

// 读取文档内容
const docContent = fs.readFileSync('/home/wz/.openclaw/workspace/ml_trading/DOC_CONTENT.md', 'utf8');

// 获取 tenant_access_token
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

// 使用旧版 API 更新文档
function updateDocumentRaw(token, docId, content) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      content: content
    });

    // 尝试旧版 API
    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: `/open-apis/doc/v1/${docId}/raw_content`,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': Buffer.byteLength(data),
        'Authorization': `Bearer ${token}`
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
    req.write(data);
    req.end();
  });
}

// 使用旧版 API 更新文档（另一种方式）
function updateDocument(token, docId, content) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      content: content
    });

    // 尝试另一种旧版 API
    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: `/open-apis/doc/v1/${docId}`,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': Buffer.byteLength(data),
        'Authorization': `Bearer ${token}`
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
    req.write(data);
    req.end();
  });
}

async function main() {
  try {
    console.log('📝 开始更新飞书文档（尝试旧版 API）...');
    console.log('文档 ID:', DOC_ID);
    console.log('内容大小:', docContent.length, '字符');
    
    // 获取 token
    console.log('\n🔑 正在获取 tenant_access_token...');
    const token = await getTenantAccessToken();
    console.log('✅ Token 获取成功');
    
    // 尝试旧版 API #1
    console.log('\n📤 尝试旧版 API #1: /open-apis/doc/v1/{docId}/raw_content...');
    let result = await updateDocumentRaw(token, DOC_ID, docContent);
    console.log('📊 响应状态:', result.statusCode);
    if (result.data) {
      console.log('📄 响应数据:', JSON.stringify(result.data, null, 2));
    }
    
    if (result.statusCode === 200 && result.data?.code === 0) {
      console.log('\n✅ 文档更新成功!');
      console.log('doc_id:', DOC_ID);
      console.log('doc_url:', `https://feishu.cn/docx/${DOC_ID}`);
      return;
    }
    
    // 尝试旧版 API #2
    console.log('\n📤 尝试旧版 API #2: /open-apis/doc/v1/{docId}...');
    result = await updateDocument(token, DOC_ID, docContent);
    console.log('📊 响应状态:', result.statusCode);
    if (result.data) {
      console.log('📄 响应数据:', JSON.stringify(result.data, null, 2));
    }
    
    if (result.statusCode === 200 && result.data?.code === 0) {
      console.log('\n✅ 文档更新成功!');
      console.log('doc_id:', DOC_ID);
      console.log('doc_url:', `https://feishu.cn/docx/${DOC_ID}`);
    } else {
      console.log('\n❌ 所有 API 尝试失败');
      console.log('💡 建议：可能需要使用飞书 MCP 工具或手动更新文档');
    }
    
  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();
