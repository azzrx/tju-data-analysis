================================================================================
🚀 [数据流追踪] 开始处理 Chat 请求
================================================================================
✅ [认证成功] 用户: ckx, API Key: AfMAbwPJ...
📝 [请求参数] session_id: '3', query_type: 'analysis'
📝 [用户输入] how are you

🔍 [会话查询] 正在获取会话 session_id='3', user='ckx'
🔍 [数据库查询] 查找会话: session_id='3', user='ckx'
📂 [数据库操作] 加载现有会话 - ID: 21, session_id: '3'
📂 [现有会话详情] 用户: ckx, 上下文长度: 1541 字符
📂 [会话创建时间] 2025-10-23 17:47:58.416088+00:00
📂 [会话更新时间] 2025-10-26 13:23:12.699637+00:00
📂 [历史上下文预览] 用户：hello
回复：您好，请问有什么可以帮助您的吗？您可以告诉我您需要了解的技术领域或问题细节，我会尽力为您提供帮助。
用户：who are u
回复：我是Qwen，由阿里云开发的AI助手，旨在提供各种技术问题的答案和帮助。有什么我可以帮您的吗？
用户：how to solve database...
📊 [会话状态] 会话ID: 3
📊 [会话用户] ckx
📊 [历史长度] 1541 字符
📊 [历史内容预览] 用户：hello
回复：您好，请问有什么可以帮助您的吗？您可以告诉我您需要了解的技术领域或问题细节，我会尽力为您提供帮助。
用户：who are u
回复：我是Qwen，由阿里云开发的AI助手，旨在提供各种技术问题的答案和帮助。有什么我可以帮您的吗？
用户：how to solve database error
回复：## 分析要求
请按照以下步骤进行分析：

### 第一步：问题识别
从日志中提...

🧠 [智能对话管理] 开始分析对话类型和上下文...
意图分类失败: 'LightweightIntentClassifier' object has no attribute 'model'
意图分类失败: 'LightweightIntentClassifier' object has no attribute 'model'
意图分类失败: 'LightweightIntentClassifier' object has no attribute 'model'
🧠 [历史解析] 解析出 3 轮历史对话
意图分类失败: 'LightweightIntentClassifier' object has no attribute 'model'
🧠 [智能分类] 对话类型: general_qa
🧠 [分类详情] 意图: unknown, 置信度: 0.000
🧠 [模型信息] 使用模型: error_fallback, 耗时: 0.443秒
🧠 [上下文压缩] 压缩后保留 3 轮对话
意图分类失败: 'LightweightIntentClassifier' object has no attribute 'model'
name 'text' is not defined
Traceback (most recent call last):
  File "/home/victor/miniconda3/envs/chenkaixuan_DA/lib/python3.13/site-packages/ninja/operation.py", line 133, in run
    result = self.view_func(request, **values)
  File "/home/victor/DataAnalysis/django_backend/deepseek_api/api.py", line 134, in chat
    use_rag, rag_decision = conversation_manager.should_use_rag(conversation_type, user_input, classification_details)
                            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/victor/DataAnalysis/django_backend/deepseek_api/conversation_manager.py", line 301, in should_use_rag
    use_rag = is_rag_required(intent_result)
  File "/home/victor/DataAnalysis/django_backend/deepseek_api/intent_classifier.py", line 377, in is_rag_required
    return any(keyword in text.lower() for keyword in technical_keywords)
  File "/home/victor/DataAnalysis/django_backend/deepseek_api/intent_classifier.py", line 377, in <genexpr>
    return any(keyword in text.lower() for keyword in technical_keywords)
                          ^^^^
NameError: name 'text' is not defined. Did you mean: 'next'?
Internal Server Error: /api/chat
[26/Oct/2025 14:02:42] "POST /api/chat HTTP/1.1" 500 1151

