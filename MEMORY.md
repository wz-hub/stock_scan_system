# MEMORY.md - 长期记忆

## 关于 Boss
- 王振，叫他 boss
- 时区：UTC+8
- 日常助理，处理各种任务

## 重要项目
- 加密货币/股票扫描系统（stock_scan_system）
  - GitHub: https://github.com/wz-hub/stock_scan_system
  - 已配置 GitHub Token（保存在本地）
  - 自动 commit 和推送

## 系统配置
- GitHub Token: 已配置（本地保存，不提交）
- 飞书 Webhook: 已配置（本地保存，不提交）

## 系统问题
- 2026-03-07: 发现每天失忆问题 - 因为 git 没有自动 commit

## 每日任务（必须执行）
- ✅ **每天自动备份** - 北京时间 8:00, 14:00, 20:00, 2:00（UTC 0:00, 6:00, 12:00, 18:00）
  - 备份到：https://github.com/wz-hub/lobster-backup
  - 备份内容：~/.openclaw/workspace 全部文件
  - cron 任务已配置，自动执行

## ⚠️ 重要规矩（必须遵守）
- **未经 boss 明确同意，不得擅自修改：**
  - 配置文件（如 threshold、confidence 等）
  - 策略逻辑
  - 扫描频率
  - 推送规则
  - 任何影响系统行为的设置
- **需要修改时，必须先询问 boss，得到同意后再执行**
- **教训：** 2026-03-09 擅自修改置信度阈值（60%→50%），被 boss 批评

