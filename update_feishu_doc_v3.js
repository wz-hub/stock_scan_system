const https = require('https');
const fs = require('fs');

// 飞书开放平台配置
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

// 获取文档根块
function getDocumentRoot(token, docId) {
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

// 删除文档内容（清空所有块）
function clearDocument(token, docId, rootBlockId) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: `/open-apis/docx/v1/documents/${docId}/blocks/${rootBlockId}/children`,
      method: 'DELETE',
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

// 创建文档块（添加内容）
function createDocumentBlocks(token, docId, parentBlockId, blocks) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      blocks: blocks
    });

    const options = {
      hostname: 'open.feishu.cn',
      port: 443,
      path: `/open-apis/docx/v1/documents/${docId}/blocks/${parentBlockId}/children`,
      method: 'POST',
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

// 将 Markdown 转换为飞书文档块（简化版）
function markdownToBlocks(markdown) {
  const lines = markdown.split('\n');
  const blocks = [];
  
  for (const line of lines) {
    if (line.startsWith('# ')) {
      // H1 标题
      blocks.push({
        block_type: 1,
        heading1: {
          elements: [{
            text_run: { content: line.substring(2) + '\n' }
          }]
        }
      });
    } else if (line.startsWith('## ')) {
      // H2 标题
      blocks.push({
        block_type: 2,
        heading2: {
          elements: [{
            text_run: { content: line.substring(3) + '\n' }
          }]
        }
      });
    } else if (line.startsWith('### ')) {
      // H3 标题
      blocks.push({
        block_type: 3,
        heading3: {
          elements: [{
            text_run: { content: line.substring(4) + '\n' }
          }]
        }
      });
    } else if (line.startsWith('```')) {
      // 代码块开始/结束
      if (line === '```') {
        blocks.push({
          block_type: 14,
          code: {
            elements: [{
              text_run: { content: '\n' }
            }]
          }
        });
      } else {
        const lang = line.substring(3);
        blocks.push({
          block_type: 14,
          code: {
            language: lang || 'plain_text',
            elements: [{
              text_run: { content: '\n' }
            }]
          }
        });
      }
    } else if (line.startsWith('- ')) {
      // 列表项
      blocks.push({
        block_type: 4,
        bullet: {
          elements: [{
            text_run: { content: line.substring(2) + '\n' }
          }]
        }
      });
    } else if (line.trim() === '') {
      // 空行
      blocks.push({
        block_type: 5,
        text: {
          elements: [{
            text_run: { content: '\n' }
          }]
        }
      });
    } else {
      // 普通文本
      blocks.push({
        block_type: 5,
        text: {
          elements: [{
            text_run: { content: line + '\n' }
          }]
        }
      });
    }
  }
  
  return blocks;
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
    
    // 获取文档根块
    console.log('\n📦 正在获取文档根块...');
    const rootResult = await getDocumentRoot(token, DOC_ID);
    console.log('📊 响应状态:', rootResult.statusCode);
    
    if (rootResult.statusCode !== 200 || rootResult.data?.code !== 0) {
      console.log('❌ 获取根块失败:', JSON.stringify(rootResult.data || rootResult.rawData, null, 2));
      return;
    }
    
    const rootBlockId = rootResult.data.data.block_id;
    console.log('✅ 根块 ID:', rootBlockId);
    
    // 清空现有内容
    console.log('\n🗑️  正在清空现有内容...');
    const clearResult = await clearDocument(token, DOC_ID, rootBlockId);
    console.log('📊 清空响应状态:', clearResult.statusCode);
    if (clearResult.data) {
      console.log('📄 清空结果:', JSON.stringify(clearResult.data, null, 2));
    }
    
    // 将 Markdown 转换为块
    console.log('\n🔄 正在转换 Markdown 为文档块...');
    const blocks = markdownToBlocks(docContent);
    console.log('✅ 转换完成，共', blocks.length, '个块');
    
    // 分批创建块（每次最多 50 个）
    console.log('\n📤 正在创建文档块...');
    const batchSize = 50;
    for (let i = 0; i < blocks.length; i += batchSize) {
      const batch = blocks.slice(i, i + batchSize);
      console.log(`  批次 ${Math.floor(i / batchSize) + 1}/${Math.ceil(blocks.length / batchSize)}: 创建 ${batch.length} 个块...`);
      
      const createResult = await createDocumentBlocks(token, DOC_ID, rootBlockId, batch);
      console.log(`  📊 响应状态:`, createResult.statusCode);
      
      if (createResult.statusCode !== 200 || createResult.data?.code !== 0) {
        console.log('  ❌ 创建失败:', JSON.stringify(createResult.data || createResult.rawData, null, 2));
        // 继续尝试下一批
      }
    }
    
    console.log('\n✅ 文档更新完成!');
    console.log('doc_id:', DOC_ID);
    console.log('doc_url:', `https://feishu.cn/docx/${DOC_ID}`);
    
  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();
