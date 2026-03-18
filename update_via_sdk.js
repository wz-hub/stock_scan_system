const { Client } = require('/home/wz/.openclaw/extensions/openclaw-lark/node_modules/@larksuiteoapi/node-sdk');
const fs = require('fs');

// 配置
const APP_ID = 'cli_a9eddbc73ab85bcd';
const APP_SECRET = 'pSul1MqDerYxg6dI69OktfKaxpVAa7qI';
const DOC_ID = 'Kekcdlaypo4wwrxQjuccRFk6nyh';

// 读取文档内容
const docContent = fs.readFileSync('/home/wz/.openclaw/workspace/ml_trading/DOC_CONTENT.md', 'utf8');

// 创建客户端
const client = new Client({
  appId: APP_ID,
  appSecret: APP_SECRET
});

async function main() {
  try {
    console.log('📝 开始使用飞书 SDK 更新文档...');
    console.log('文档 ID:', DOC_ID);
    console.log('内容大小:', docContent.length, '字符');
    
    // 使用 docs.doc.update 接口
    console.log('\n📤 正在更新文档内容...');
    const result = await client.docs.doc.update({
      params: {
        document_id: DOC_ID
      },
      data: {
        content: docContent
      }
    });
    
    console.log('\n📊 响应:', JSON.stringify(result, null, 2));
    
    if (result.code === 0) {
      console.log('\n✅ 文档更新成功!');
      console.log('doc_id:', DOC_ID);
      console.log('doc_url:', `https://feishu.cn/docx/${DOC_ID}`);
    } else {
      console.log('\n❌ 文档更新失败');
      console.log('错误码:', result.code);
      console.log('错误信息:', result.msg);
    }
    
  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();
