# DeepSeek API 配置说明

## 🎯 概述

本系统已完成从本地 Ollama 模型到 DeepSeek API 的迁移。现在您只需配置 API Key 即可使用！

## 📋 前提条件

1. 拥有 DeepSeek API Key（从 [platform.deepseek.com](https://platform.deepseek.com) 获取）
2. 服务器能访问 DeepSeek API（需要网络连接）

## ⚙️ 配置步骤

### 方法 1：使用环境变量（推荐）

在终端中设置环境变量：

```bash
# Linux/MacOS
export DEEPSEEK_API_KEY='your-api-key-here'

# Windows (PowerShell)
$env:DEEPSEEK_API_KEY='your-api-key-here'

# Windows (CMD)
set DEEPSEEK_API_KEY=your-api-key-here
```

**永久设置（推荐）：**

Linux/MacOS - 添加到 `~/.bashrc` 或 `~/.zshrc`:
```bash
echo 'export DEEPSEEK_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 方法 2：使用 .env 文件

在 `django_backend` 目录下创建 `.env` 文件：

```bash
cd /root/projects/Django-Data-Analysis/django_backend
nano .env
```

在 `.env` 文件中添加：

```
DEEPSEEK_API_KEY=your-api-key-here
```

保存并退出（Ctrl+O, Enter, Ctrl+X）

## 🚀 启动服务

配置完成后，直接启动 Django 服务：

```bash
cd /root/projects/Django-Data-Analysis/django_backend
python manage.py runserver 0.0.0.0:8000
```

系统会自动：
1. ✅ 读取 API Key
2. ✅ 使用 DeepSeek API 进行对话生成
3. ✅ 使用本地 Ollama 进行 Embedding（仍需 Ollama 运行）

## 📝 注意事项

### Embedding 说明

- **LLM（对话生成）**：使用 DeepSeek API ✅ 无需本地部署
- **Embedding（向量化）**：仍使用本地 Ollama ⚠️ 需要 Ollama 运行

因为 DeepSeek 暂不提供 Embedding API，向量检索功能仍需要本地 Ollama。

**启动 Ollama Embedding 服务：**

```bash
# 确保 Ollama 正在运行
ollama serve

# 在另一个终端拉取 embedding 模型
ollama pull nomic-embed-text
```

如果不需要 RAG 向量检索功能（纯对话模式），可以忽略 Ollama。

## 🔧 配置切换

如果需要切换回本地 Ollama 模型，编辑 `model_config.py`：

```python
# 当前配置（第 61 行）
CURRENT_CONFIG = DEEPSEEK_CONFIG  # 使用 DeepSeek API

# 切换回本地 Ollama
# CURRENT_CONFIG = FAST_CONFIG  # 取消注释这行
```

## 🧪 测试配置

### 1. 测试 API Key 配置

```bash
cd /root/projects/Django-Data-Analysis/django_backend
python -c "from deepseek_config import get_api_key, validate_api_key; print('API Key:', get_api_key()[:10] + '...'); print('Valid:', validate_api_key())"
```

预期输出：
```
API Key: sk-1234567...
Valid: True
```

### 2. 测试 DeepSeek LLM

```bash
python -c "from deepseek_llm import DeepSeekLLM; llm = DeepSeekLLM(); response = llm.complete('你好'); print(response.text)"
```

### 3. 测试完整系统

启动服务后，使用前端或 API 客户端测试对话功能。

## 🛠️ 故障排除

### 问题 1：找不到 API Key

**错误信息：**
```
⚠️  未找到 DeepSeek API Key！
ValueError: 未找到 DeepSeek API Key！
```

**解决方案：**
1. 检查环境变量是否设置：`echo $DEEPSEEK_API_KEY`
2. 检查 `.env` 文件是否存在且格式正确
3. 确认 API Key 格式正确（以 `sk-` 开头）

### 问题 2：API 调用失败

**错误信息：**
```
❌ DeepSeek API 请求失败: 401
```

**解决方案：**
1. 验证 API Key 是否有效
2. 检查 API 账户是否有余额
3. 确认网络能访问 `api.deepseek.com`

### 问题 3：Embedding 错误

**错误信息：**
```
⚠️  DeepSeek 暂不提供 Embedding API，Embedding 功能仍使用 Ollama
无法连接到 Ollama 服务
```

**解决方案：**
1. 启动 Ollama 服务：`ollama serve`
2. 拉取 embedding 模型：`ollama pull nomic-embed-text`
3. 如果不需要向量检索，可以在前端选择"日常聊天"模式

## 📊 配置对比

| 配置项 | 使用 API | 使用本地 Ollama |
|--------|----------|----------------|
| 需要本地部署 | ❌ 否 | ✅ 是 |
| 内存占用 | 极小 (~100MB) | 大 (4-8GB) |
| 响应速度 | 快 (取决于网络) | 中等 |
| 费用 | 按调用计费 | 免费 |
| 模型质量 | 高 | 中高 |
| Embedding | 需要本地 | 本地 |

## 📚 API 费用说明

DeepSeek API 费用（参考 2024 年价格）：
- DeepSeek Chat: ~¥0.001/1K tokens
- 日常对话约 100-500 tokens/次
- 日志分析约 1000-3000 tokens/次

**预估费用：**
- 100 次日常对话 ≈ ¥0.05
- 100 次日志分析 ≈ ¥0.20

详细价格请查看：https://platform.deepseek.com/api-docs/pricing

## 🔐 安全建议

1. **不要** 将 API Key 提交到 Git 仓库
2. **不要** 在代码中硬编码 API Key
3. **定期** 轮换 API Key
4. **使用** 环境变量或 `.env` 文件存储密钥
5. 在 `.gitignore` 中添加 `.env` 文件

## 📞 获取帮助

如果遇到问题：
1. 查看日志输出（Django 控制台）
2. 检查本文档的故障排除章节
3. 访问 DeepSeek 文档：https://platform.deepseek.com/api-docs

## ✅ 配置完成检查清单

- [ ] 已获取 DeepSeek API Key
- [ ] 已通过环境变量或 .env 文件配置 API Key
- [ ] 已启动 Ollama 服务（用于 Embedding）
- [ ] 已拉取 nomic-embed-text 模型
- [ ] 已测试 API Key 配置
- [ ] 已启动 Django 服务
- [ ] 已测试对话功能

配置完成后，您就可以开始使用了！🎉

