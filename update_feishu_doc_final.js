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

// 更新文档内容（使用正确的 API）
function updateDocumentContent(token, docId, content) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      content: content
    });

    // 使用正确的 API endpoint
    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: `/open-apis/docx/v1/documents/${docId}/content`,
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
    console.log('📝 开始更新飞书文档...');
    console.log('文档 ID:', DOC_ID);
    console.log('内容大小:', docContent.length, '字符');
    
    // 获取 token
    console.log('\n🔑 正在获取 tenant_access_token...');
    const token = await getTenantAccessToken();
    console.log('✅ Token 获取成功');
    
    // 更新文档内容
    console.log('\n📤 正在更新文档内容...');
    const result = await updateDocumentContent(token, DOC_ID, docContent);
    
    console.log('\n📊 响应状态:', result.statusCode);
    console.log('📄 响应数据:', JSON.stringify(result.data, null, 2));
    
    if (result.statusCode === 200 && result.data?.code === 0) {
      console.log('\n✅ 文档更新成功!');
      console.log('doc_id:', DOC_ID);
      console.log('doc_url:', `https://feishu.cn/docx/${DOC_ID}`);
    } else {
      console.log('\n❌ 文档更新失败');
      if (result.data?.msg) {
        console.log('错误信息:', result.data.msg);
      }
      if (result.data?.error?.troubleshooter) {
        console.log('排查建议:', result.data.error.troubleshooter);
      }
    }
    
  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();
