import time
import threading
from typing import Dict, Any, Optional
from django.core.cache import cache
import hashlib
from .models import APIKey, RateLimit, ConversationSession
from django.conf import settings

# 全局配置
# API_KEY_LENGTH = 32
# TOKEN_EXPIRY_SECONDS = 3600
# RATE_LIMIT_MAX = 5  # 每分钟最大请求数
# RATE_LIMIT_INTERVAL = 60

# 线程锁用于速率限制
rate_lock = threading.Lock()

# 全局单例：TopKLogSystem 实例（懒加载）
_log_system_instance = None
_log_system_lock = threading.Lock()


def reset_log_system():
    """在模型配置切换后重置 TopKLogSystem 实例。"""
    global _log_system_instance

    with _log_system_lock:
        if _log_system_instance is not None:
            import logging

            logger = logging.getLogger(__name__)
            logger.info("重置 TopKLogSystem 实例以应用新的模型配置")
            _log_system_instance = None

def get_log_system():
    """
    获取 TopKLogSystem 单例实例（懒加载 + 线程安全）
    只在第一次调用时初始化，后续直接返回已有实例
    """
    global _log_system_instance
    
    if _log_system_instance is None:
        with _log_system_lock:
            # 双重检查锁定模式（避免多线程重复初始化）
            if _log_system_instance is None:
                from topklogsystem import TopKLogSystem
                from model_config import CURRENT_CONFIG
                import logging
                logger = logging.getLogger(__name__)
                
                logger.info("初始化 TopKLogSystem 单例实例...")
                logger.info(f"使用模型: LLM={CURRENT_CONFIG['llm']}, Embedding={CURRENT_CONFIG['embedding_model']}")
                
                # 检查是否使用 API
                use_api = CURRENT_CONFIG.get('use_api', False)
                if use_api:
                    logger.info("🌐 配置为使用 DeepSeek API")
                else:
                    logger.info("🖥️  配置为使用本地 Ollama")
                
                _log_system_instance = TopKLogSystem(
                    log_path="./data/log",
                    llm=CURRENT_CONFIG['llm'],
                    embedding_model=CURRENT_CONFIG['embedding_model'],
                    use_api=use_api  # 传递 API 使用标志
                )
                logger.info("TopKLogSystem 初始化完成！")
    
    return _log_system_instance

def deepseek_r1_api_call(prompt: str, query_type: str = "analysis") -> str:
    """
    调用 DeepSeek API
    
    Args:
        prompt: 用户输入的问题
        query_type: 查询类型（analysis: 日志分析, general_chat: 日常聊天）
    
    Returns:
        LLM 的响应文本
    """
    print(f"\n🤖 [大模型调用] 开始调用 DeepSeek API")
    print(f"🤖 [调用参数] query_type: '{query_type}'")
    print(f"🤖 [Prompt长度] {len(prompt)} 字符")
    
    # 先进行意图分类，检查是否为工具类意图
    from .intent_classifier import get_intent_classifier, TOOL_INTENTS
    classifier = get_intent_classifier()
    intent_result = classifier.classify_intent(prompt)
    
    print(f"🔍 [意图分类] 意图: {intent_result.intent.value}, 置信度: {intent_result.confidence:.3f}")
    
    # 如果是工具类意图，执行工具并将结果传递给LLM
    tool_result = None
    if intent_result.intent in TOOL_INTENTS:
        print(f"🔧 [工具调用] 检测到工具类意图: {intent_result.intent.value}")
        tool_func = classifier.tools.get(intent_result.intent)
        if tool_func:
            tool_result = tool_func(prompt)
            print(f"✅ [工具执行] 工具执行完成，结果长度: {len(tool_result)} 字符")
            print(f"🔧 [工具结果] 将工具结果传递给LLM进行分析和回答")
        else:
            print(f"⚠️ [工具调用] 未找到对应的工具函数: {intent_result.intent.value}")
    
    from model_config import CURRENT_CONFIG
    use_api = CURRENT_CONFIG.get('use_api', False)
    
    if use_api:
        # 使用 DeepSeek API
        from deepseek_llm import DeepSeekLLM
        from llama_index.core.llms import ChatMessage
        
        # 如果执行了工具，将工具结果作为上下文传递给LLM
        if tool_result:
            # 构建包含工具结果的prompt
            enhanced_prompt = f"""用户问题：{prompt}

工具执行结果：
{tool_result}

请基于以上工具执行结果，对用户的问题进行详细分析和回答。要求：
1. 对工具结果进行总结和分析
2. 指出关键问题和异常
3. 提供具体的建议和解决方案
4. 用清晰、专业的方式组织回答"""
            
            print(f"🤖 [工具增强Prompt] 构建完成，长度: {len(enhanced_prompt)} 字符")
            llm = DeepSeekLLM(model=CURRENT_CONFIG['llm'], timeout=60)
            messages = [ChatMessage(role="user", content=enhanced_prompt)]
            
            print(f"🤖 [API请求] 发送工具增强的请求到大模型...")
            response = llm.chat(messages)
            
            result_text = response.message.content
            print(f"🤖 [API响应] 收到回复，长度: {len(result_text)} 字符")
            print(f"🤖 [回复内容] {result_text[:100]}{'...' if len(result_text) > 100 else ''}")
            
            return result_text
        
        # 根据 query_type 决定是否使用 RAG
        if query_type == "analysis":
            # 日志分析模式：使用 RAG
            print(f"🤖 [RAG模式] 日志分析，使用 RAG 检索")
            system = get_log_system()
            
            print(f"🤖 [API请求] 发送请求到大模型...")
            result = system.query(prompt, query_type=query_type)
            time.sleep(0.5)
            
            response = result["response"]
            print(f"🤖 [API响应] 收到回复，长度: {len(response)} 字符")
            print(f"🤖 [回复内容] {response[:100]}{'...' if len(response) > 100 else ''}")
            
            return response
        else:
            # 日常聊天模式：直接调用 API，不使用 RAG
            print(f"🤖 [纯对话模式] 日常聊天，直接调用 DeepSeek API，不使用 RAG 检索")
            
            llm = DeepSeekLLM(model=CURRENT_CONFIG['llm'], timeout=60)
            messages = [ChatMessage(role="user", content=prompt)]
            
            print(f"🤖 [API请求] 发送请求到大模型...")
            response = llm.chat(messages)
            
            result_text = response.message.content
            print(f"🤖 [API响应] 收到回复，长度: {len(result_text)} 字符")
            print(f"🤖 [回复内容] {result_text[:100]}{'...' if len(result_text) > 100 else ''}")
            
            return result_text
    else:
        # 使用本地 Ollama + RAG 系统
        print(f"🤖 [RAG模式] 使用本地 Ollama + RAG 检索")
        system = get_log_system()
        
        print(f"🤖 [API请求] 发送请求到大模型...")
        result = system.query(prompt, query_type=query_type)
        time.sleep(0.5)
        
        response = result["response"]
        print(f"🤖 [API响应] 收到回复，长度: {len(response)} 字符")
        print(f"🤖 [回复内容] {response[:100]}{'...' if len(response) > 100 else ''}")
        
        return response

def deepseek_r1_api_call_stream(prompt: str, query_type: str = "analysis", history_context: str = ""):
    """
    流式调用 DeepSeek API（支持 RAG 和历史上下文）
    
    Args:
        prompt: 用户输入的问题
        query_type: 查询类型（analysis: 日志分析, general_chat: 日常聊天）
        history_context: 历史对话上下文字符串
    
    Yields:
        流式响应的生成器
    """
    print(f"\n🤖 [流式调用] 开始流式调用 DeepSeek API")
    print(f"🤖 [调用参数] query_type: '{query_type}'")
    print(f"🤖 [Prompt长度] {len(prompt)} 字符")
    print(f"🤖 [历史上下文长度] {len(history_context)} 字符")
    
    # 先进行意图分类，检查是否为工具类意图
    from .intent_classifier import get_intent_classifier, TOOL_INTENTS
    classifier = get_intent_classifier()
    intent_result = classifier.classify_intent(prompt)
    
    print(f"🔍 [意图分类] 意图: {intent_result.intent.value}, 置信度: {intent_result.confidence:.3f}")
    
    # 如果是工具类意图，执行工具并将结果传递给LLM
    tool_result = None
    if intent_result.intent in TOOL_INTENTS:
        print(f"🔧 [工具调用] 检测到工具类意图: {intent_result.intent.value}")
        tool_func = classifier.tools.get(intent_result.intent)
        if tool_func:
            tool_result = tool_func(prompt)
            print(f"✅ [工具执行] 工具执行完成，结果长度: {len(tool_result)} 字符")
            print(f"🔧 [工具结果] 将工具结果传递给LLM进行分析和流式回答")
        else:
            print(f"⚠️ [工具调用] 未找到对应的工具函数: {intent_result.intent.value}")
    
    from model_config import CURRENT_CONFIG
    use_api = CURRENT_CONFIG.get('use_api', False)
    
    if not use_api:
        print("🤖 [流式模式] 当前配置使用本地 Ollama，直接启用原生流式输出")
        system = get_log_system()
        stream = system.stream_query(
            query=prompt,
            query_type=query_type,
            tool_result=tool_result,
            history_context=history_context
        )
        for chunk in stream:
            yield chunk
        return
    
    from deepseek_llm import DeepSeekLLM
    from llama_index.core.llms import ChatMessage
    
    # 解析历史上下文，构建消息列表
    messages = []
    if history_context:
        print(f"🤖 [历史解析] 解析历史对话...")
        from .conversation_manager import ConversationManager
        conversation_manager = ConversationManager(max_context_length=4000, max_turns=10)
        
        # 解析并压缩历史
        historical_turns = conversation_manager.parse_conversation_history(history_context)
        compressed_turns = conversation_manager.compress_context(historical_turns)
        
        print(f"🤖 [历史压缩] 原始轮次: {len(historical_turns)}, 压缩后: {len(compressed_turns)}")
        
        # 将历史转换为消息列表
        for turn in compressed_turns:
            messages.append(ChatMessage(role="user", content=turn.user_input))
            messages.append(ChatMessage(role="assistant", content=turn.assistant_reply))
    
    # 如果执行了工具，将工具结果作为上下文传递给LLM进行流式回答
    if tool_result:
        # 构建包含工具结果的prompt
        enhanced_prompt = f"""用户问题：{prompt}

工具执行结果：
{tool_result}

请基于以上工具执行结果，对用户的问题进行详细分析和回答。要求：
1. 对工具结果进行总结和分析
2. 指出关键问题和异常
3. 提供具体的建议和解决方案
4. 用清晰、专业的方式组织回答"""
        
        print(f"🤖 [工具增强Prompt] 构建完成，长度: {len(enhanced_prompt)} 字符")
        messages.append(ChatMessage(role="user", content=enhanced_prompt))
        
        # 流式调用 LLM
        llm = DeepSeekLLM(model=CURRENT_CONFIG['llm'], timeout=120)
        print(f"🤖 [流式生成] 开始基于工具结果流式生成回复...")
        return llm.stream_chat(messages)
    
    # 根据 query_type 决定是否使用 RAG
    if query_type == "analysis":
        # 日志分析模式：使用 RAG 检索，然后流式生成
        print(f"🤖 [RAG模式] 日志分析，先进行 RAG 检索...")
        system = get_log_system()
        
        # 1. RAG 检索相关日志
        log_results = system.retrieve_logs(prompt)
        print(f"🤖 [RAG检索] 检索到 {len(log_results)} 条相关日志")
        
        # 2. 构建包含检索结果的 prompt
        rag_prompt = system._build_prompt_string(prompt, log_results, query_type)
        print(f"🤖 [RAG Prompt] 构建完成，长度: {len(rag_prompt)} 字符")
        
        # 3. 添加当前用户输入（使用RAG增强的prompt）
        messages.append(ChatMessage(role="user", content=rag_prompt))
        
        print(f"🤖 [消息列表] 总消息数: {len(messages)} (包含历史)")
    else:
        # 日常聊天模式：直接添加用户输入
        print(f"🤖 [纯对话模式] 日常聊天，直接流式调用...")
        messages.append(ChatMessage(role="user", content=prompt))
        
        print(f"🤖 [消息列表] 总消息数: {len(messages)} (包含历史)")
    
    # 流式调用 LLM
    llm = DeepSeekLLM(model=CURRENT_CONFIG['llm'], timeout=120)
    print(f"🤖 [流式生成] 开始流式生成回复...")
    return llm.stream_chat(messages)

def create_api_key(user: str) -> str:
    """创建 API Key 并保存到数据库"""
    key = APIKey.generate_key()
    expiry = time.time() + settings.TOKEN_EXPIRY_SECONDS
    
    api_key = APIKey.objects.create(
        key=key,
        user=user,
        expiry_time=expiry
    )
    
    # 创建对应的速率限制记录
    RateLimit.objects.create(
        api_key=api_key,
        reset_time=time.time() + settings.RATE_LIMIT_INTERVAL
    )
    
    return key

def validate_api_key(key_str: str) -> bool:
    """验证 API Key 是否存在且未过期"""
    try:
        api_key = APIKey.objects.get(key=key_str)
        if api_key.is_valid():
            return True
        else:
            api_key.delete()  # 删除过期key
            return False
    except APIKey.DoesNotExist:
        return False

def check_rate_limit(key_str: str) -> bool:
    """检查 API Key 的请求频率是否超过限制"""
    with rate_lock:
        try:
            # api_key = APIKey.objects.get(key=key_str)
            # rate_limit = RateLimit.objects.get(api_key=api_key)
            rate_limit = RateLimit.objects.select_related('api_key').get(api_key__key=key_str)
            
            current_time = time.time()
            if current_time > rate_limit.reset_time:
                rate_limit.count = 1
                rate_limit.reset_time = current_time + settings.RATE_LIMIT_INTERVAL
                rate_limit.save()
                return True
            elif rate_limit.count < settings.RATE_LIMIT_MAX:
                rate_limit.count += 1
                rate_limit.save()
                return True
            else:
                return False
        except RateLimit.DoesNotExist:
            # 如果速率限制记录不存在，创建一个新的
            try:
                current_time = time.time()
                api_key = APIKey.objects.get(key=key_str)
                RateLimit.objects.create(
                    api_key=api_key,
                    count=1,
                    reset_time=current_time + settings.RATE_LIMIT_INTERVAL
                )
                return True
            except APIKey.DoesNotExist:
                return False

# def get_or_create_session(session_id: str, user: APIKey) -> ConversationSession:
    # """获取或创建会话，关联当前用户（通过API Key）"""
    # session, created = ConversationSession.objects.get_or_create(
        # session_id=session_id,
        # user=user,  # 绑定用户
        # defaults={'context': ''}
    # )
    # return session

def get_or_create_session(session_id: str, user: APIKey) -> ConversationSession:
    """
    获取或创建用户的专属会话：
    - 若用户+session_id已存在 → 加载旧会话（保留历史）
    - 若不存在 → 创建新会话（空历史）
    """
    print(f"🔍 [数据库查询] 查找会话: session_id='{session_id}', user='{user.user}'")
    
    session, created = ConversationSession.objects.get_or_create(
        session_id=session_id,  # 匹配会话ID
        user=user,              # 匹配当前用户（关键！避免跨用户会话冲突）
        defaults={'context': ''}
    )
    
    # 调试日志：确认是否创建新会话（created=True 表示新会话）
    import logging
    logger = logging.getLogger(__name__)
    
    if created:
        print(f"✨ [数据库操作] 创建新会话 - ID: {session.id}, session_id: '{session.session_id}'")
        print(f"✨ [新会话详情] 用户: {session.user.user}, 上下文: 空")
        logger.info(f"会话 {session_id}（用户：{user.user}）创建新会话")
    else:
        print(f"📂 [数据库操作] 加载现有会话 - ID: {session.id}, session_id: '{session.session_id}'")
        print(f"📂 [现有会话详情] 用户: {session.user.user}, 上下文长度: {len(session.context)} 字符")
        print(f"📂 [会话创建时间] {session.created_at}")
        print(f"📂 [会话更新时间] {session.updated_at}")
        if session.context:
            print(f"📂 [历史上下文预览] {session.context[:150]}{'...' if len(session.context) > 150 else ''}")
        logger.info(f"会话 {session_id}（用户：{user.user}）加载旧会话")
    
    return session

def get_cached_reply(prompt: str, session_id: str, user: APIKey) -> str | None:
    """缓存键包含 session_id 和 user，避免跨会话冲突"""
    cache_key = f"reply:{user.user}:{session_id}:{hash(prompt)}"
    print(f"🔍 [缓存查询] 缓存键: {cache_key}")
    
    cached_result = cache.get(cache_key)
    if cached_result:
        print(f"✅ [缓存命中] 找到缓存回复，长度: {len(cached_result)} 字符")
        print(f"💾 [缓存内容] {cached_result[:80]}{'...' if len(cached_result) > 80 else ''}")
    else:
        print(f"❌ [缓存未命中] 缓存中没有找到对应回复")
    
    return cached_result

def set_cached_reply(prompt: str, reply: str, session_id: str, user: APIKey, timeout=3600):
    cache_key = f"reply:{user.user}:{session_id}:{hash(prompt)}"
    print(f"💾 [缓存保存] 保存回复到缓存")
    print(f"💾 [缓存键] {cache_key}")
    print(f"💾 [缓存内容] 长度: {len(reply)} 字符, 过期时间: {timeout}秒")
    print(f"💾 [回复预览] {reply[:80]}{'...' if len(reply) > 80 else ''}")
    
    cache.set(cache_key, reply, timeout)
    print(f"✅ [缓存完成] 回复已成功保存到缓存")


def generate_cache_key(original_key: str) -> str:
    """
    生成安全的缓存键。
    对原始字符串进行哈希处理，确保键长度固定且仅包含安全字符。
    """
    # 使用SHA256哈希函数生成固定长度的键（64位十六进制字符串）
    hash_obj = hashlib.sha256(original_key.encode('utf-8'))
    return hash_obj.hexdigest()
