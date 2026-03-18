const fs = require('fs');
const { execSync } = require('child_process');

const markdown = fs.readFileSync('ml_trading/DOC_CONTENT.md', 'utf8');

const payload = {
  title: 'ML Trading - 机器学习加密货币交易系统完整教程',
  markdown: markdown
};

// Write payload to temp file
fs.writeFileSync('/tmp/doc_payload.json', JSON.stringify(payload));

console.log('Payload written, size:', markdown.length, 'chars');
console.log('Calling MCP...');
