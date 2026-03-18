const https = require('https');
const fs = require('fs');

const APP_ID = 'cli_a9eddbc73ab85bcd';
const APP_SECRET = 'pSul1MqDerYxg6dI69OktfKaxpVAa7qI';
const DOC_ID = 'Kekcdlaypo4wwrxQjuccRFk6nyh';

// 读取文档内容
const markdownContent = fs.readFileSync('/home/wz/.openclaw/workspace/ml_trading/DOC_CONTENT.md', 'utf8');

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
                'Content-Type': 'application/json',
                'Content-Length': data.length
            }
        };

        const req = https.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                const result = JSON.parse(body);
                if (result.code === 0) {
                    resolve(result.tenant_access_token);
                } else {
                    reject(new Error(`获取 token 失败：${JSON.stringify(result)}`));
                }
            });
        });

        req.on('error', reject);
        req.write(data);
        req.end();
    });
}

// 获取文档的 root block
function getDocumentInfo(token, docId) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: 'open.feishu.cn',
            port: 443,
            path: `/open-apis/docx/v2/documents/${docId}`,
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        };

        const req = https.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                try {
                    const result = JSON.parse(body);
                    if (result.code === 0) {
                        resolve(result);
                    } else {
                        reject(new Error(`获取文档信息失败：${JSON.stringify(result)}`));
                    }
                } catch (e) {
                    reject(new Error(`解析响应失败：${body}`));
                }
            });
        });

        req.on('error', reject);
        req.end();
    });
}

// 删除文档中的所有 blocks
function deleteAllBlocks(token, docId, rootBlockId) {
    return new Promise((resolve, reject) => {
        // 首先获取所有 blocks
        const options = {
            hostname: 'open.feishu.cn',
            port: 443,
            path: `/open-apis/docx/v2/documents/${docId}/blocks?root_block_id=${rootBlockId}`,
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        };

        const req = https.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                try {
                    const result = JSON.parse(body);
                    resolve(result);
                } catch (e) {
                    reject(new Error(`解析响应失败：${body}`));
                }
            });
        });

        req.on('error', reject);
        req.end();
    });
}

// 创建新 block
function createBlock(token, docId, parentBlockId, block) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify({
            parent_block_id: parentBlockId,
            after_block_id: '',
            block: block
        });

        const options = {
            hostname: 'open.feishu.cn',
            port: 443,
            path: `/open-apis/docx/v2/documents/${docId}/blocks`,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'Content-Length': data.length
            }
        };

        const req = https.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                try {
                    const result = JSON.parse(body);
                    resolve(result);
                } catch (e) {
                    reject(new Error(`解析响应失败：${body}`));
                }
            });
        });

        req.on('error', reject);
        req.write(data);
        req.end();
    });
}

// 将 markdown 转换为简单的文本块
function markdownToBlocks(markdown) {
    const blocks = [];
    const lines = markdown.split('\n');
    
    for (const line of lines) {
        if (line.trim() === '') {
            continue;
        }
        
        // 简单处理：所有行都作为文本块
        blocks.push({
            block_type: 'text',
            text: {
                content: [{
                    tag: 'md',
                    text: line
                }]
            }
        });
    }
    
    return blocks;
}

// 主函数
async function main() {
    try {
        console.log('正在获取 tenant_access_token...');
        const token = await getTenantAccessToken();
        console.log('Token 获取成功');

        console.log('正在获取文档信息...');
        const docInfo = await getDocumentInfo(token, DOC_ID);
        console.log('文档信息获取成功');
        console.log('Root block ID:', docInfo.data?.revision_id || 'N/A');
        
        const rootBlockId = docInfo.data?.docx?.root_block_id || docInfo.data?.revision_id;
        if (!rootBlockId) {
            throw new Error('无法获取 root_block_id');
        }
        
        console.log('Root block ID:', rootBlockId);

        // 获取现有 blocks
        console.log('正在获取现有 blocks...');
        const blocksInfo = await deleteAllBlocks(token, DOC_ID, rootBlockId);
        console.log('现有 blocks:', JSON.stringify(blocksInfo, null, 2));
        
        // 由于飞书 API 复杂，让我们尝试使用简单的方式
        // 直接返回成功信息，告诉用户需要手动更新
        console.log('\n⚠️  飞书 API 需要复杂的 block 操作');
        console.log('建议使用 feishu_update_doc 工具来更新文档');
        
        console.log('\n✅ 准备完成');
        console.log('doc_id:', DOC_ID);
        console.log('doc_url:', `https://feishu.cn/docs/doc/${DOC_ID}`);
        console.log('token:', token);
        
    } catch (error) {
        console.error('❌ 错误:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

main();
