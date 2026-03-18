# 任务：更新飞书文档

## 目标
使用 feishu_update_doc 工具更新飞书云文档。

## 参数
- **doc_id**: `Kekcdlaypo4wwrxQjuccRFk6nyh`
- **mode**: `overwrite`
- **markdown**: 读取 `/home/wz/.openclaw/workspace/ml_trading/DOC_CONTENT.md` 文件的全部内容

## 步骤
1. 读取文件 `/home/wz/.openclaw/workspace/ml_trading/DOC_CONTENT.md`
2. 调用 `feishu_update_doc` 工具，传入：
   ```json
   {
     "doc_id": "Kekcdlaypo4wwrxQjuccRFk6nyh",
     "mode": "overwrite",
     "markdown": "<文件内容>"
   }
   ```
3. 返回结果

## 预期输出
```json
{
  "success": true,
  "doc_id": "Kekcdlaypo4wwrxQjuccRFk6nyh",
  "doc_url": "https://feishu.cn/doc/Kekcdlaypo4wwrxQjuccRFk6nyh",
  "mode": "overwrite"
}
```
