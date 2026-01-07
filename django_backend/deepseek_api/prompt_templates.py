"""
Prompt Templates for Log Analysis System
Contains specialized prompt templates for different types of log analysis tasks
"""

class PromptTemplates:
    """专业的 Prompt 模板管理"""
    
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

    MULTI_TURN_TEMPLATE = """## 历史对话
{conversation_history}

## 最新问题
{current_query}

## 上下文理解
基于历史对话，当前问题的意图是：{intent}

请继续分析：
"""

    QUERY_REWRITE_TEMPLATE = """原始查询：{query}

请将查询改写为更适合检索的形式：
1. 提取关键技术术语
2. 添加同义词
3. 扩展相关概念

改写后的查询：
"""

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
