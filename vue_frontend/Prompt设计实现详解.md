# Prompt 设计实现详解

## 📋 概述

本系统实现了**科学、精准的 Prompt 设计**，通过多层次的 Prompt 模板和智能上下文构建，引导大模型进行高质量的数据分析。系统采用**模板化设计**、**上下文增强**、**Few-shot 学习**等策略，显著提升了数据分析的准确性和深度。

---

## 🏗️ 架构设计

### 核心组件

```
┌─────────────────────────────────────┐
│  前端层 (Frontend)                   │
│  - 用户选择查询类型                  │
│  - 发送 query_type 参数              │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  API 路由层 (api.py)                 │
│  - 接收 query_type                   │
│  - 构建上下文                        │
│  - 调用服务层                        │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Prompt 模板层 (prompt_templates.py) │
│  - 专业模板定义                      │
│  - 按类型选择模板                    │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Prompt 构建层 (topklogsystem.py)    │
│  - 整合日志上下文                    │
│  - 应用模板                          │
│  - 构建最终 Prompt                   │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  大模型调用层 (services.py)          │
│  - 发送增强后的 Prompt               │
│  - 获取分析结果                      │
└─────────────────────────────────────┘
```

---

## 📝 核心实现文件

### 1. Prompt 模板定义
**文件**: `django_backend/deepseek_api/prompt_templates.py`

### 2. Prompt 构建逻辑
**文件**: `django_backend/topklogsystem.py` (第 555-652 行)

### 3. 上下文构建
**文件**: `django_backend/deepseek_api/conversation_manager.py` (第 237-285 行)

### 4. 服务调用
**文件**: `django_backend/deepseek_api/services.py` (第 71-183 行)

### 5. API 路由
**文件**: `django_backend/deepseek_api/api.py` (第 144-419 行)

### 6. 前端交互
**文件**: `vue_frontend/src/components/ChatInput.vue` (第 1-30 行)
**文件**: `vue_frontend/src/api.js` (第 42-44 行)

---

## 🔍 详细实现解析

## 一、前端层：查询类型选择

### 1.1 用户界面 (`ChatInput.vue`)

```vue
<template>
  <select
    v-model="selectedQueryType"
    class="query-type-select"
    :disabled="loading"
    @change="handleQueryTypeChange"
  >
    <option value="analysis">日志分析</option>
    <option value="general_chat">日常聊天</option>
  </select>
</template>

<script setup>
const selectedQueryType = ref("analysis"); // 默认查询类型
</script>
```

**功能**：
- 用户可以选择查询类型：`analysis`（日志分析）或 `general_chat`（日常聊天）
- 默认选择 `analysis` 模式

### 1.2 API 调用 (`api.js`)

```javascript
// 发送聊天消息
chat(sessionId, userInput, queryType = "analysis") {
  return api.post('/chat', { 
    session_id: sessionId, 
    user_input: userInput, 
    query_type: queryType  // 传递查询类型
  });
}
```

**关键点**：
- `queryType` 参数决定后端使用哪种 Prompt 模板
- 默认值为 `"analysis"`

---

## 二、后端层：Prompt 模板系统

### 2.1 Prompt 模板定义 (`prompt_templates.py`)

#### 2.1.1 系统角色定义

```python
SYSTEM_ROLE = """你是一个专业的日志分析专家，擅长从海量日志中发现问题、定位根因、提供解决方案。

你的分析应该：
1. 结构化：使用清晰的段落和标题
2. 数据驱动：引用具体的日志证据
3. 深入：从现象到根因，再到解决方案
4. 可操作：提供具体的修复建议

输出格式要求：
- 使用 Markdown 格式
- 包含：问题摘要、根因分析、影响范围、解决方案
"""
```

**设计要点**：
- ✅ **角色定位**：明确 AI 的身份和专业领域
- ✅ **分析原则**：结构化、数据驱动、深入、可操作
- ✅ **格式要求**：明确输出格式，便于前端渲染

#### 2.1.2 日志分析模板

```python
LOG_ANALYSIS_TEMPLATE = """## 相关历史日志
{log_context}

## 分析任务
{query}

## 分析要求
请按照以下步骤进行分析：

### 第一步：问题识别
从日志中提取关键错误信息、异常模式、性能指标

### 第二步：根因分析
结合日志时间线、错误堆栈、系统状态，推断问题根本原因

### 第三步：影响评估
评估问题的严重程度、影响范围、业务影响

### 第四步：解决方案
提供分层解决方案：
- 紧急修复（立即可执行）
- 短期优化（一周内）
- 长期改进（架构层面）

### 第五步：预防措施
建议监控指标、告警规则、代码规范

## 输出格式要求
请使用 Markdown 格式，包含以下部分：
- **问题摘要**：简明概述问题
- **根因分析**：详细分析问题原因
- **影响范围**：评估影响范围和严重程度
- **解决方案**：分层次提供解决建议
- **预防措施**：防止类似问题再次发生的建议

## Few-shot 示例
<example>
问题：数据库连接池耗尽
日志：HikariPool-1 - Connection is not available, request timed out after 30000ms

分析：
**问题摘要**
系统出现数据库连接池耗尽，导致新请求无法获取连接

**根因分析**
1. 连接泄漏：部分代码未正确关闭连接
2. 慢查询：某些查询执行时间过长，占用连接
3. 并发量激增：流量突增超过连接池容量

**解决方案**
- 紧急：重启服务释放连接，临时扩大连接池
- 短期：代码审查，添加连接自动回收机制
- 长期：引入读写分离，优化慢查询
</example>

请开始你的分析：
"""
```

**设计亮点**：

1. **五步分析法**：
   - 问题识别 → 根因分析 → 影响评估 → 解决方案 → 预防措施
   - 引导大模型进行系统化分析

2. **分层解决方案**：
   - 紧急修复（立即）
   - 短期优化（一周内）
   - 长期改进（架构层面）
   - 提供不同时间维度的解决方案

3. **Few-shot 学习**：
   - 提供具体示例，展示期望的输出格式
   - 帮助大模型理解分析深度和结构

4. **模板变量**：
   - `{log_context}`: 检索到的日志上下文
   - `{query}`: 用户查询

#### 2.1.3 多轮对话模板

```python
MULTI_TURN_TEMPLATE = """## 历史对话
{conversation_history}

## 最新问题
{current_query}

## 上下文理解
基于历史对话，当前问题的意图是：{intent}

请继续分析：
"""
```

**功能**：
- 支持多轮对话的上下文理解
- 明确当前问题的意图

#### 2.1.4 日常聊天模板

```python
elif query_type == "general_chat":
    return f"""你是一个友好的技术助手。请回答用户的问题，提供准确、有用的信息。

用户问题：{kwargs.get('query', '')}

请回答："""
```

**特点**：
- 简洁的对话模板
- 适合日常聊天场景，不需要复杂的分析步骤

#### 2.1.5 模板选择方法

```python
def get_template_by_type(self, query_type: str, **kwargs) -> str:
    """根据查询类型获取对应的模板"""
    if query_type == "analysis":
        return self.SYSTEM_ROLE + "\n\n" + self.LOG_ANALYSIS_TEMPLATE.format(**kwargs)
    elif query_type == "multi_turn":
        return self.SYSTEM_ROLE + "\n\n" + self.MULTI_TURN_TEMPLATE.format(**kwargs)
    elif query_type == "query_rewrite":
        return self.QUERY_REWRITE_TEMPLATE.format(**kwargs)
    elif query_type == "general_chat":
        # 日常聊天模式，使用简单的对话模板
        return f"""你是一个友好的技术助手。请回答用户的问题，提供准确、有用的信息。

用户问题：{kwargs.get('query', '')}

请回答："""
    else:
        # 默认返回基础分析模板
        return self.SYSTEM_ROLE + "\n\n" + self.LOG_ANALYSIS_TEMPLATE.format(**kwargs)
```

**设计模式**：
- ✅ **策略模式**：根据 `query_type` 选择不同的模板
- ✅ **组合模式**：`SYSTEM_ROLE` + 具体模板
- ✅ **默认回退**：未知类型使用默认模板

---

## 三、Prompt 构建流程

### 3.1 Prompt 构建方法 (`topklogsystem.py`)

```python
def _build_prompt_string(self, query: str, context: Dict, query_type: str = "analysis") -> str:
    """
    构建提示词字符串
    
    Args:
        query: 用户查询
        context: 检索到的日志上下文
        query_type: 查询类型，可选值: analysis（日志分析）, general_chat（日常聊天）
        
    Returns:
        构建好的提示词
    """
    # 1. 构建日志上下文
    log_context = ""
    for i, log in enumerate(context, 1):
        log_context += f"日志 {i} : {log['content']}\n\n"
    
    # 2. 使用 prompt 模板
    if prompt_templates:
        # 使用专业模板库
        try:
            prompt = prompt_templates.get_template_by_type(
                query_type=query_type,
                log_context=log_context,
                query=query
            )
            return prompt
        except Exception as e:
            logger.error(f"使用模板失败: {e}，回退到内置模板")
    
    # 3. 内置的默认模板（作为备份）
    prompt = f"""
你是一个专业的日志分析专家...
## 相关历史日志参考:
{log_context}
## 当前需要分析的问题:
{query}
...
"""
    return prompt
```

**实现流程**：

1. **日志上下文构建**：
   ```python
   log_context = ""
   for i, log in enumerate(context, 1):
       log_context += f"日志 {i} : {log['content']}\n\n"
   ```
   - 将检索到的日志按顺序编号
   - 格式化输出，便于大模型理解

2. **模板应用**：
   ```python
   prompt = prompt_templates.get_template_by_type(
       query_type=query_type,
       log_context=log_context,
       query=query
   )
   ```
   - 根据 `query_type` 选择模板
   - 填充模板变量（`log_context`、`query`）

3. **容错机制**：
   - 如果模板库不可用，使用内置默认模板
   - 确保系统稳定性

---

## 四、上下文增强机制

### 4.1 对话上下文构建 (`conversation_manager.py`)

```python
def build_context_for_llm(self, turns: List[ConversationTurn], current_input: str, 
                         conversation_type: ConversationType) -> str:
    """
    为LLM构建上下文字符串
    
    Args:
        turns: 历史对话轮次
        current_input: 当前用户输入
        conversation_type: 当前对话类型
        
    Returns:
        格式化的上下文字符串
    """
    if not turns:
        return f"用户：{current_input}\n回复："
    
    # 根据对话类型选择不同的上下文构建策略
    if conversation_type == ConversationType.FOLLOW_UP:
        # 追问时，重点关注最近的对话
        context_parts = []
        for turn in turns[-2:]:  # 只保留最近2轮
            context_parts.append(f"用户：{turn.user_input}")
            context_parts.append(f"回复：{turn.assistant_reply}")
        
        context_parts.append(f"用户：{current_input}")
        context_parts.append("回复：")
        return "\n".join(context_parts)
    
    elif conversation_type == ConversationType.SUMMARY_REQUEST:
        # 摘要请求时，包含更多历史信息
        context_parts = []
        for turn in turns:
            context_parts.append(f"用户：{turn.user_input}")
            context_parts.append(f"回复：{turn.assistant_reply}")
        
        context_parts.append(f"用户：{current_input}")
        context_parts.append("回复：")
        return "\n".join(context_parts)
    
    else:
        # 默认策略：包含压缩后的历史
        context_parts = []
        for turn in turns:
            context_parts.append(f"用户：{turn.user_input}")
            context_parts.append(f"回复：{turn.assistant_reply}")
        
        context_parts.append(f"用户：{current_input}")
        context_parts.append("回复：")
        return "\n".join(context_parts)
```

**智能上下文策略**：

| 对话类型 | 上下文策略 | 说明 |
|---------|----------|------|
| **FOLLOW_UP** (追问) | 只保留最近2轮 | 重点关注当前对话，避免上下文过长 |
| **SUMMARY_REQUEST** (摘要请求) | 包含所有历史 | 需要完整历史信息进行摘要 |
| **默认** | 包含压缩后的历史 | 平衡上下文长度和信息完整性 |

**设计优势**：
- ✅ **自适应**：根据对话类型动态调整上下文
- ✅ **性能优化**：避免不必要的长上下文
- ✅ **精准聚焦**：追问时只关注相关历史

---

## 五、工具增强 Prompt

### 5.1 工具执行结果增强 (`services.py`)

```python
# 如果是工具类意图，执行工具并将结果传递给LLM
tool_result = None
if intent_result.intent in TOOL_INTENTS:
    tool_func = classifier.tools.get(intent_result.intent)
    if tool_func:
        tool_result = tool_func(prompt)
        
        # 构建包含工具结果的prompt
        enhanced_prompt = f"""用户问题：{prompt}

工具执行结果：
{tool_result}

请基于以上工具执行结果，对用户的问题进行详细分析和回答。要求：
1. 对工具结果进行总结和分析
2. 指出关键问题和异常
3. 提供具体的建议和解决方案
4. 用清晰、专业的方式组织回答"""
        
        messages = [ChatMessage(role="user", content=enhanced_prompt)]
        response = llm.chat(messages)
        return response.message.content
```

**工具增强流程**：

1. **意图识别**：检测是否为工具类意图（网络分析、错误分析、性能分析等）

2. **工具执行**：调用相应的工具函数获取数据

3. **Prompt 增强**：
   ```
   用户问题：{原始问题}
   
   工具执行结果：
   {工具返回的数据}
   
   请基于以上工具执行结果，对用户的问题进行详细分析和回答。
   ```

4. **分析要求**：
   - 总结和分析工具结果
   - 指出关键问题和异常
   - 提供具体建议和解决方案
   - 清晰、专业地组织回答

**优势**：
- ✅ **数据驱动**：基于真实数据进行分析
- ✅ **精准分析**：工具提供结构化数据，分析更准确
- ✅ **自动化**：无需用户手动收集数据

---

## 六、完整实现流程

### 6.1 日志分析模式流程

```
┌─────────────────┐
│ 用户选择         │
│ query_type =    │
│ "analysis"      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 前端发送请求     │
│ POST /chat       │
│ query_type:     │
│ "analysis"      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ API 路由层       │
│ 1. 解析参数      │
│ 2. 获取会话      │
│ 3. 构建上下文    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ RAG 检索        │
│ 检索相关日志     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Prompt 构建      │
│ 1. 格式化日志    │
│ 2. 选择模板      │
│ 3. 填充变量      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 最终 Prompt      │
│ SYSTEM_ROLE +   │
│ LOG_ANALYSIS_   │
│ TEMPLATE        │
│ + 日志上下文     │
│ + 用户查询       │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 大模型调用       │
│ 返回分析结果     │
└─────────────────┘
```

### 6.2 日常聊天模式流程

```
┌─────────────────┐
│ 用户选择         │
│ query_type =    │
│ "general_chat"  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 前端发送请求     │
│ query_type:     │
│ "general_chat"  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ API 路由层       │
│ 快速路径处理     │
│ 跳过 RAG 检索   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Prompt 构建      │
│ 使用简单模板     │
│ 不包含日志上下文 │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 大模型调用       │
│ 返回对话回复     │
└─────────────────┘
```

---

## 七、核心代码详解

### 7.1 API 路由层 (`api.py`)

```python
@router.post("/chat", response={200: ChatOut, 401: ErrorResponse})
def chat(request, data: ChatIn):
    # 1. 解析参数
    session_id = data.session_id.strip() or "default_session"
    user_input = data.user_input.strip()
    query_type = data.query_type or "analysis"  # 获取查询类型
    
    # 2. 获取会话和历史上下文
    session = get_or_create_session(session_id, user)
    
    # 3. 构建上下文（根据 query_type 选择策略）
    if query_type == "general_chat":
        # 快速路径：日常聊天模式
        llm_context = conversation_manager.build_context_for_llm(
            compressed_turns, user_input, conversation_type
        )
    else:
        # 日志分析模式：完整处理流程
        # ... 意图分类、RAG 检索等
    
    # 4. 调用大模型
    if query_type == "analysis":
        # 使用 RAG 系统（包含 Prompt 构建）
        reply = deepseek_r1_api_call(user_input, query_type)
    else:
        # 直接调用 API
        reply = deepseek_r1_api_call(user_input, query_type)
    
    return {"reply": reply, "timestamp": ...}
```

**关键点**：
- `query_type` 决定使用哪种 Prompt 模板和处理流程
- 日志分析模式：使用 RAG + 专业 Prompt 模板
- 日常聊天模式：使用简单 Prompt，快速响应

### 7.2 服务层调用 (`services.py`)

```python
def deepseek_r1_api_call(prompt: str, query_type: str = "analysis") -> str:
    # 根据 query_type 决定是否使用 RAG
    if query_type == "analysis":
        # 日志分析模式：使用 RAG
        system = get_log_system()  # 获取 RAG 系统
        result = system.query(prompt, query_type=query_type)
        # system.query() 内部会调用 _build_prompt_string()
        # 使用专业 Prompt 模板
        return result["response"]
    else:
        # 日常聊天模式：直接调用 API
        llm = DeepSeekLLM(model=CURRENT_CONFIG['llm'], timeout=60)
        messages = [ChatMessage(role="user", content=prompt)]
        response = llm.chat(messages)
        return response.message.content
```

**流程说明**：
1. `query_type == "analysis"`：调用 RAG 系统，内部使用 `_build_prompt_string()` 构建专业 Prompt
2. `query_type == "general_chat"`：直接使用用户输入作为 Prompt，不进行增强

---

## 八、Prompt 设计优势

### 8.1 科学的设计原则

| 原则 | 实现方式 | 效果 |
|------|---------|------|
| **结构化** | 五步分析法 | 系统化分析流程 |
| **数据驱动** | 日志上下文注入 | 基于真实数据 |
| **Few-shot 学习** | 提供示例 | 引导输出格式 |
| **分层解决** | 紧急/短期/长期 | 可操作的方案 |
| **上下文感知** | 历史对话整合 | 理解对话背景 |

### 8.2 精准的分析引导

1. **问题识别** → 提取关键错误、异常模式、性能指标
2. **根因分析** → 结合时间线、堆栈、系统状态
3. **影响评估** → 严重程度、影响范围、业务影响
4. **解决方案** → 分层提供（紧急/短期/长期）
5. **预防措施** → 监控指标、告警规则、代码规范

### 8.3 模板化优势

- ✅ **可维护性**：集中管理 Prompt 模板，易于修改和优化
- ✅ **可扩展性**：轻松添加新的模板类型
- ✅ **一致性**：确保所有分析遵循相同的标准
- ✅ **容错性**：内置默认模板，确保系统稳定性

---

## 九、实际应用示例

### 示例 1：日志分析 Prompt

**输入**：
- `query_type`: `"analysis"`
- `query`: `"分析数据库连接错误"`
- `log_context`: 检索到的相关日志

**构建的 Prompt**：
```
你是一个专业的日志分析专家，擅长从海量日志中发现问题、定位根因、提供解决方案。

你的分析应该：
1. 结构化：使用清晰的段落和标题
2. 数据驱动：引用具体的日志证据
3. 深入：从现象到根因，再到解决方案
4. 可操作：提供具体的修复建议

## 相关历史日志
日志 1 : 2024-01-15 10:30:25 ERROR [HikariPool-1] Connection is not available, request timed out after 30000ms
日志 2 : 2024-01-15 10:30:26 WARN [HikariPool-1] Pool stats (total=20, active=20, idle=0, waiting=5)

## 分析任务
分析数据库连接错误

## 分析要求
请按照以下步骤进行分析：
...
```

### 示例 2：日常聊天 Prompt

**输入**：
- `query_type`: `"general_chat"`
- `query`: `"什么是微服务架构？"`

**构建的 Prompt**：
```
你是一个友好的技术助手。请回答用户的问题，提供准确、有用的信息。

用户问题：什么是微服务架构？

请回答：
```

---

## 📊 总结

### 核心实现要点

1. **模板系统**：
   - 专业的 Prompt 模板库 (`prompt_templates.py`)
   - 根据 `query_type` 动态选择模板
   - 支持 Few-shot 学习和结构化输出

2. **上下文增强**：
   - RAG 检索日志上下文
   - 历史对话整合
   - 工具执行结果增强

3. **智能构建**：
   - 根据对话类型调整上下文策略
   - 自动格式化日志数据
   - 容错机制确保稳定性

4. **前后端协作**：
   - 前端选择查询类型
   - 后端根据类型构建相应 Prompt
   - 统一的参数传递机制

### 设计优势

- ✅ **科学性**：五步分析法，系统化引导
- ✅ **精准性**：基于真实数据和上下文
- ✅ **可操作性**：分层解决方案，具体可执行
- ✅ **可维护性**：模板化设计，易于优化
- ✅ **可扩展性**：支持新增模板类型

---

**核心文件位置**：
- Prompt 模板：`django_backend/deepseek_api/prompt_templates.py`
- Prompt 构建：`django_backend/topklogsystem.py` (第 555-652 行)
- 上下文构建：`django_backend/deepseek_api/conversation_manager.py` (第 237-285 行)
- 服务调用：`django_backend/deepseek_api/services.py` (第 71-183 行)
- 前端交互：`vue_frontend/src/components/ChatInput.vue`

