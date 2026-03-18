const https = require('https');
const fs = require('fs');

// 飞书开放平台配置
const APP_ID = 'cli_a9eddbc73ab85bcd';
const APP_SECRET = 'pSul1MqDerYxg6dI69OktfKaxpVAa7qI';

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

// 获取文档信息（验证文档是否存在）
function getDocumentInfo(token, docId) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: `/open-apis/docx/v1/documents/${docId}`,
      method: 'GET',
      headers: {
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
    req.end();
  });
}

// 使用旧版 API 更新文档内容
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

// 使用新版 Docx API 获取文档块
function getDocumentBlocks(token, docId) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: `/open-apis/docx/v1/documents/${docId}/blocks/root`,
      method: 'GET',
      headers: {
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
    req.end();
  });
}

async function main() {
  try {
    console.log('📝 开始更新飞书文档...');
    console.log('文档 ID:', 'Kekcdlaypo4wwrxQjuccRFk6nyh');
    console.log('内容大小:', docContent.length, '字符');
    
    // 获取 token
    console.log('\n🔑 正在获取 tenant_access_token...');
    const token = await getTenantAccessToken();
    console.log('✅ Token 获取成功');
    
    // 先获取文档信息，验证文档是否存在
    console.log('\n🔍 正在获取文档信息...');
    const docInfo = await getDocumentInfo(token, 'Kekcdlaypo4wwrxQjuccRFk6nyh');
    console.log('📊 文档信息响应状态:', docInfo.statusCode);
    console.log('📄 文档信息:', JSON.stringify(docInfo.data || docInfo.rawData, null, 2));
    
    if (docInfo.statusCode !== 200 || docInfo.data?.code !== 0) {
      console.log('\n⚠️ 文档可能不存在或无权限访问');
      console.log('请检查文档 ID 是否正确，或是否有访问权限');
      return;
    }
    
    // 尝试获取文档块
    console.log('\n📦 正在获取文档块...');
    const blocks = await getDocumentBlocks(token, 'Kekcdlaypo4wwrxQjuccRFk6nyh');
    console.log('📊 文档块响应状态:', blocks.statusCode);
    if (blocks.data) {
      console.log('📄 文档块:', JSON.stringify(blocks.data, null, 2));
    }
    
    // 尝试使用旧版 API 更新
    console.log('\n📤 正在使用旧版 API 更新文档内容...');
    const result = await updateDocumentRaw(token, 'Kekcdlaypo4wwrxQjuccRFk6nyh', docContent);
    
    console.log('\n📊 响应状态:', result.statusCode);
    if (result.data) {
      console.log('📄 响应数据:', JSON.stringify(result.data, null, 2));
    } else {
      console.log('📄 原始响应:', result.rawData?.substring(0, 500));
    }
    
    if (result.statusCode === 200 && result.data?.code === 0) {
      console.log('\n✅ 文档更新成功!');
      console.log('doc_id: Kekcdlaypo4wwrxQjuccRFk6nyh');
      console.log('doc_url: https://feishu.cn/docx/Kekcdlaypo4wwrxQjuccRFk6nyh');
    } else {
      console.log('\n❌ 文档更新失败');
      if (result.data?.msg) {
        console.log('错误信息:', result.data.msg);
      }
    }
    
  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();
