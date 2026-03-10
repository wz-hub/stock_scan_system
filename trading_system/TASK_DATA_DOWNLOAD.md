# 数据下载任务清单

## 任务目标
下载 3-5 年历史 K 线数据，建设完整回测系统

## 下载配置
- **时间跨度:** 1095 天 (3 年)
- **时间周期:** 1h, 4h, 1d
- **交易对:** 主流币种 50 个
- **预计数据量:** 150 万 + 条 K 线

## 交易对列表
BTCUSDT,ETHUSDT,BCHUSDT,XRPUSDT,DOGEUSDT,ADAUSDT,SOLUSDT,DOTUSDT,MATICUSDT,LINKUSDT,AVAXUSDT,UNIUSDT,ATOMUSDT,LTCUSDT,ETCUSDT,FILUSDT,NEARUSDT,APTUSDT,ARBUSDT,OPUSDT,RUNEUSDT,INJUSDT,SUIUSDT,SEIUSDT,TIAUSDT,PEPEUSDT,SHIBUSDT,FLOKIUSDT,BONKUSDT,WIFUSDT

## 进度汇报
- **频率:** 每 30 分钟
- **内容:** 下载进度、数据量、错误统计
- **方式:** 更新本文件 + 发送消息

## 数据校验
下载完成后校验：
- [ ] 数据完整性（无缺失时间段）
- [ ] 数据正确性（价格无异常）
- [ ] 数据全面性（覆盖所有交易对和周期）

## 持久化配置
修改扫描脚本，确保：
- [ ] 每次扫描保存信号到数据库
- [ ] 每次扫描保存扫描日志
- [ ] 每天备份数据库
- [ ] 每周导出 CSV

## 状态
- [ ] 未开始
- [ ] 下载中
- [ ] 校验中
- [ ] 已完成
