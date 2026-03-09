# 免费 AI 编程工具完整清单

## 🆓 完全免费（软件+大模型都免费）

### 1. VS Code + Continue + Ollama

**组合方案：**
- **VS Code** - 免费编辑器
- **Continue** - 免费 AI 插件（开源）
- **Ollama** - 本地运行大模型（免费）

**官网：**
- https://code.visualstudio.com/
- https://continue.dev/
- https://ollama.com/

**特点：**
- ✅ 完全免费，无需联网
- ✅ 隐私好，代码不上传
- ✅ 支持多种开源模型（Llama、Qwen、DeepSeek）
- ✅ 代码补全、聊天、修改都能用

**配置方法：**
```bash
# 1. 安装 Ollama
brew install ollama  # Mac
# 或 https://ollama.com/download

# 2. 下载模型
ollama run qwen2.5-coder:7b  # 编程模型

# 3. VS Code 安装 Continue 插件
# 4. 配置 continue/config.json
{
  "models": [{
    "title": "Ollama",
    "provider": "ollama",
    "model": "qwen2.5-coder:7b"
  }]
}
```

**适合：** 想要完全免费、注重隐私的开发者

---

### 2. Cursor（免费版）

**官网：** https://cursor.com

**价格：**
- 免费版：每月 50 次 AI 补全 + 2 小时无限使用
- 学生免费升级 Pro

**特点：**
- ✅ 基于 VS Code，上手快
- ✅ AI 深度集成
- ✅ 免费版够日常使用
- ✅ 可以用自己的 API key

**限制：**
- 免费版有使用次数限制
- 高级功能需要付费

**适合：** 日常编程、学生

---

### 3. Codeium（免费插件）

**官网：** https://codeium.com

**价格：**
- 个人版：完全免费
- 企业版：收费

**支持平台：**
- VS Code、JetBrains、Vim 等

**特点：**
- ✅ 个人完全免费
- ✅ 代码补全准确率高
- ✅ 支持 70+ 语言
- ✅ 有聊天功能

**限制：**
- 不能执行命令
- 上下文理解一般

**适合：** 需要免费代码补全的开发者

---

### 4. OpenClaw（你正在用）

**官网：** https://openclaw.ai

**价格：**
- 软件：开源免费
- 大模型：用自己的 API key（可选免费模型）

**特点：**
- ✅ 开源免费
- ✅ 可以集成到微信/飞书/Telegram
- ✅ 支持定时任务
- ✅ 可以执行命令、操作文件
- ✅ 可以用免费/廉价模型（DeepSeek、Qwen）

**配置免费模型：**
```json
{
  "model": "deepseek-chat",
  "api_key": "sk-xxx",  // DeepSeek 免费额度
  "api_url": "https://api.deepseek.com/v1/chat/completions"
}
```

**适合：** 自动化任务、定时扫描、多渠道集成

---

### 5. LocalAI + 任意编辑器

**官网：** https://localai.io

**价格：** 完全免费

**特点：**
- ✅ 本地运行，完全免费
- ✅ 兼容 OpenAI API
- ✅ 可以用任何编辑器调用
- ✅ 支持多种开源模型

**配置：**
```bash
# 安装 LocalAI
docker-compose up -d

# 下载模型
wget https://huggingface.co/TheBloke/CodeLlama-7B-GGUF

# 任何支持 OpenAI 的插件都能用
```

**适合：** 技术高手、想要完全控制

---

## 💰 软件免费，大模型收费（但有免费额度）

### 6. VS Code + Cline/Roo Cline

**官网：**
- https://cline.bot/
- https://github.com/RooVetGit/Roo-Cline

**价格：**
- 插件：免费开源
- 大模型：用自己的 API key

**特点：**
- ✅ 类似 Claude Code 的功能
- ✅ 可以执行命令、修改文件
- ✅ 支持多种模型（Claude、GPT、DeepSeek）
- ✅ 可以用廉价模型（DeepSeek $0.14/1M tokens）

**适合：** 想要 Claude Code 功能但不想付 $20/月

---

### 7. Windsurf（免费版）

**官网：** https://windsurf.ai

**价格：**
- 免费版：有限使用
- Pro 版：$15/月

**特点：**
- ✅ 类似 Cursor
- ✅ AI 原生编辑器
- ✅ 免费版可以体验

**适合：** 想尝试 AI 编辑器

---

### 8. Tabnine（免费版）

**官网：** https://tabnine.com

**价格：**
- 基础版：免费（本地模型）
- Pro 版：$12/月

**特点：**
- ✅ 免费版有基础补全
- ✅ 本地运行，隐私好
- ✅ 支持多种编辑器

**适合：** 基础代码补全

---

## 🎓 学生免费

### 9. GitHub Student Pack

**官网：** https://education.github.com/pack

**包含：**
- ✅ GitHub Copilot 免费
- ✅ Cursor Pro 免费
- ✅ 其他工具优惠

**条件：** 在校学生

---

## 🆓 免费大模型 API（可以自己配）

### 10. 免费/廉价 API 列表

| 提供商 | 模型 | 价格 | 免费额度 | 官网 |
|--------|------|------|----------|------|
| **DeepSeek** | deepseek-chat | ¥0.14/1M tokens | 注册送 ¥2 | https://platform.deepseek.com |
| **通义千问** | qwen-plus | ¥0.004/1K tokens | 每日免费额度 | https://dashscope.aliyun.com |
| **智谱 AI** | glm-4 | ¥0.005/1K tokens | 注册送 ¥20 | https://open.bigmodel.cn |
| **Moonshot** | moonshot-v1 | ¥0.012/1K tokens | 注册送 ¥10 | https://platform.moonshot.cn |
| **Ollama** | 本地模型 | 免费 | 无限 | https://ollama.com |
| **LM Studio** | 本地模型 | 免费 | 无限 | https://lmstudio.ai |

**推荐组合：**
```
VS Code + Continue + DeepSeek API
= 几乎免费（¥0.14/1M tokens，能用很久）
```

---

## 📋 完整对比表

| 工具 | 软件费用 | 大模型费用 | 总成本 | 推荐指数 |
|------|----------|------------|--------|----------|
| **VS Code + Continue + Ollama** | 免费 | 免费 | ¥0 | ⭐⭐⭐⭐⭐ |
| **Codeium** | 免费 | 免费 | ¥0 | ⭐⭐⭐⭐ |
| **Cursor（免费版）** | 免费 | 免费（有限） | ¥0 | ⭐⭐⭐⭐ |
| **OpenClaw + DeepSeek** | 免费 | 超便宜 | ¥0.14/1M | ⭐⭐⭐⭐⭐ |
| **Cline + DeepSeek** | 免费 | 超便宜 | ¥0.14/1M | ⭐⭐⭐⭐⭐ |
| **GitHub Copilot** | $10/月 | 包含 | $120/年 | ⭐⭐⭐ |
| **Cursor Pro** | $20/月 | 包含 | $240/年 | ⭐⭐⭐⭐ |
| **Claude Code** | $20/月 + API | $0.15/1M | ~$30/月 | ⭐⭐⭐ |

---

## 🎯 我的推荐

### 完全免费方案
```
VS Code + Continue 插件 + Ollama（本地模型）
= ¥0，隐私好，无限制
```

### 性价比最高
```
VS Code + Cline 插件 + DeepSeek API
= ¥0.14/1M tokens，功能强大
```

### 自动化任务
```
OpenClaw + DeepSeek/Qwen API
= 定时任务 + 多渠道推送
```

### 专业开发
```
Cursor Pro + GitHub Copilot
= $30/月，最强体验
```

---

## 🔧 快速开始（推荐方案）

### 方案 1：完全免费
```bash
# 1. 安装 VS Code
https://code.visualstudio.com/

# 2. 安装 Continue 插件
# VS Code 扩展搜索 "Continue"

# 3. 安装 Ollama
brew install ollama  # Mac
# 或 https://ollama.com/download

# 4. 下载编程模型
ollama run qwen2.5-coder:7b

# 5. 配置 Continue
# 选择 Ollama 作为模型

# ✅ 完成！开始免费使用
```

### 方案 2：性价比最高
```bash
# 1. 安装 VS Code

# 2. 安装 Cline 插件
# VS Code 扩展搜索 "Cline"

# 3. 注册 DeepSeek
https://platform.deepseek.com/

# 4. 获取 API key
# 注册送 ¥2，够写很多代码

# 5. 配置 Cline
# 填入 DeepSeek API key

# ✅ 完成！超便宜好用
```

### 方案 3：自动化（你现在的）
```bash
# OpenClaw 已经配置好了
# 配置 DeepSeek 或 Qwen API 即可

# config/model.json
{
  "model": "deepseek-chat",
  "api_key": "sk-xxx",
  "api_url": "https://api.deepseek.com/v1/chat/completions"
}

# ✅ 定时任务 + 飞书推送
```

---

_最后更新：2026-03-09_
