import os
from pathlib import Path
from uuid import uuid4

from ninja import NinjaAPI, Router, File
# from ninja.security import BaseAuth
from django.http import HttpRequest, StreamingHttpResponse
from typing import Optional
from ninja.files import UploadedFile
from . import services
from django.conf import settings
from .schemas import (
    LoginIn,
    LoginOut,
    ChatIn,
    ChatOut,
    HistoryOut,
    ErrorResponse,
    ModelsOut,
    ModelSwitchIn,
    FileUploadOut,
)
from .models import APIKey
from .services import get_or_create_session, deepseek_r1_api_call, get_cached_reply, set_cached_reply
from .conversation_manager import ConversationManager, ConversationType
from datetime import datetime
import logging
import json
import re
from pathlib import Path as _Path
import zipfile
import xml.etree.ElementTree as ET
from model_config import (
    get_available_configs,
    get_current_config_name,
    set_current_config,
)
logger = logging.getLogger(__name__)

# 初始化对话管理器
conversation_manager = ConversationManager(max_context_length=4000, max_turns=10)

api = NinjaAPI(title="KAI API", version="0.0.1")

UPLOAD_ROOT = Path(settings.BASE_DIR) / "data" / "uploads"
MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 20 * 1024 * 1024)  # 默认 20MB

# class ApiKeyAuth(AuthBase):
    # def authenticate(self, request):
        # auth_header = request.headers.get("Authorization")
        # if not auth_header:
            # return None  # 未提供认证信息，返回None表示认证失败
        
        # try:
            # # 解析 Authorization 头（格式：Bearer <api_key>）
            # scheme, key = auth_header.split()
            # if scheme.lower() != "bearer":
                # return None  # 认证方案不是Bearer，失败
            
            # # 查询对应的APIKey对象（验证有效性）
            # api_key = APIKey.objects.get(key=key)
            # # 返回APIKey对象（而非字符串），后续可通过request.auth访问
            # return api_key  
        # except (ValueError, APIKey.DoesNotExist):
            # # 解析失败或APIKey不存在，返回None表示认证失败
            # return None

def api_key_auth(request):
    """验证请求头中的API Key"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None  # 未提供认证信息，返回None表示认证失败

    try:
        # 解析格式：Bearer <api_key>
        scheme, key = auth_header.split()
        if scheme.lower() != "bearer":
            return None  # 认证方案错误

        # 验证API Key是否存在
        api_key = APIKey.objects.get(key=key)
        return api_key  # 认证成功，返回APIKey对象
    except (ValueError, APIKey.DoesNotExist):
        return None  # 解析失败或Key不存在，认证失败

router = Router(auth=api_key_auth)

@api.post("/login", response={200: LoginOut, 400: ErrorResponse, 403: ErrorResponse})
def login(request, data: LoginIn):
    """
    登录接口：接收用户名和密码，验证后返回 API Key
    密码统一为"secret"，作为示例
    """
    username = data.username.strip()
    password = data.password.strip()
    
    if not username or not password:
        return 400, {"error": "用户名和密码不能为空"}
    
    if password != 'secret':
        return 403, {"error": "密码错误"}
    
    key = services.create_api_key(username)
    return {"api_key": key, "expiry": settings.TOKEN_EXPIRY_SECONDS}


@router.post("/files/upload", response={200: FileUploadOut, 400: ErrorResponse, 401: ErrorResponse})
def upload_file(request, file: UploadedFile = File(...)):
    if not request.auth:
        return 401, {"error": "请先登录获取API Key"}

    if not file:
        return 400, {"error": "请选择要上传的文件"}

    if file.size > MAX_UPLOAD_SIZE:
        max_size_mb = round(MAX_UPLOAD_SIZE / (1024 * 1024))
        return 400, {"error": f"文件过大，最大支持 {max_size_mb}MB"}

    original_filename = file.name
    extension = Path(original_filename).suffix
    stored_filename = f"{uuid4().hex}{extension}"

    try:
        UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        destination_path = UPLOAD_ROOT / stored_filename

        with destination_path.open("wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        relative_path = destination_path.relative_to(Path(settings.BASE_DIR))

        return {
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "size": file.size,
            "relative_path": str(relative_path),
        }
    except Exception as exc:
        logger.exception("文件上传失败")
        return 400, {"error": f"文件上传失败: {exc}"}


@router.post("/chat", response={200: ChatOut, 401: ErrorResponse})
def chat(request, data: ChatIn):
    print("=" * 80)
    print("🚀 [数据流追踪] 开始处理 Chat 请求")
    print("=" * 80)
    
    # 1. 认证验证（确保用户已登录）
    if not request.auth:
        print("❌ [认证失败] 未提供有效的API Key")
        return 401, {"error": "请先登录获取API Key"}
    
    print(f"✅ [认证成功] 用户: {request.auth.user}, API Key: {request.auth.key[:8]}...")
    
    # 2. 解析参数（确保 session_id 有效）
    session_id = data.session_id.strip() or "default_session"
    user_input = data.user_input.strip()
    query_type = data.query_type or "analysis"  # 获取查询类型，默认为 analysis
    
    print(f"📝 [请求参数] session_id: '{session_id}', query_type: '{query_type}'")
    print(f"📝 [用户输入] {user_input}")
    
    if not user_input:
        print("❌ [参数错误] 用户输入为空")
        return 400, {"error": "请输入消息内容"}

    # 如果用户在输入中包含已上传文件的路径（例如 data/uploads/...），尝试读取并附加文件内容到输入中
    try:
        file_paths = re.findall(r"data/uploads/[\w\-\.]+", user_input)
        attached_texts = []
        for rel in file_paths:
            abs_path = _Path(settings.BASE_DIR) / rel
            if abs_path.exists():
                try:
                    # 仅支持文本类文件和平常的文档格式（docx）
                    suffix = abs_path.suffix.lower()
                    text_content = None
                    if suffix in ['.txt', '.md', '.json', '.jsonl', '.csv']:
                        with abs_path.open('r', encoding='utf-8', errors='ignore') as f:
                            text_content = f.read()
                    elif suffix == '.docx':
                        # 解析 docx（无需外部依赖），直接读取 word/document.xml
                        try:
                            def _extract_docx_text(path: _Path) -> str:
                                with zipfile.ZipFile(str(path)) as zf:
                                    if 'word/document.xml' not in zf.namelist():
                                        return ''
                                    xml_content = zf.read('word/document.xml')
                                root = ET.fromstring(xml_content)
                                # WordprocessingML namespace
                                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                                paragraphs = []
                                for p in root.findall('.//w:p', ns):
                                    texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
                                    if texts:
                                        paragraphs.append(''.join(texts))
                                return '\n'.join(paragraphs)

                            text_content = _extract_docx_text(abs_path)
                        except Exception:
                            text_content = None
                    else:
                        # 不支持的二进制格式（例如 .doc、.pdf）
                        text_content = None

                    if text_content:
                        attached_texts.append((rel, text_content))
                        print(f"📎 [附加文件] 从 {rel} 读取内容，长度: {len(text_content)} 字符")
                    else:
                        print(f"⚠️ [附加文件] 无法解析文件内容: {rel} (suffix={suffix})")
                except Exception as e:
                    print(f"⚠️ [附加文件] 读取失败 {rel}: {e}")
            else:
                print(f"⚠️ [附加文件] 文件不存在: {rel}")

        # 如果读取到任何文件内容，将它们以标注形式追加到用户输入，便于后续 RAG/LLM 使用
        if attached_texts:
            additions = []
            for rel, txt in attached_texts:
                additions.append(f"\n\n[附件: {rel} 内容开始]\n{txt}\n[附件: {rel} 内容结束]\n")
            user_input = user_input + "\n" + "\n".join(additions)
    except Exception as _e:
        print(f"⚠️ [附加文件] 处理上传文件时出错: {_e}")
    
    # 3. 获取会话（加载旧会话或创建新会话）
    user = request.auth  # 从认证获取当前用户（APIKey对象）
    print(f"\n🔍 [会话查询] 正在获取会话 session_id='{session_id}', user='{user.user}'")
    session = get_or_create_session(session_id, user)
    
    print(f"📊 [会话状态] 会话ID: {session.session_id}")
    print(f"📊 [会话用户] {session.user.user}")
    print(f"📊 [历史长度] {len(session.context)} 字符")
    if session.context:
        print(f"📊 [历史内容预览] {session.context[:200]}{'...' if len(session.context) > 200 else ''}")
    else:
        print("📊 [历史内容] 空（新会话）")
    
    # 4. 初始化变量（确保在所有路径下都有定义）
    historical_turns = []
    compressed_turns = []
    conversation_type = None
    classification_details = {}
    rag_decision = {}
    use_rag = False
    
    # 快速路径：日常聊天模式优化
    if query_type == "general_chat":
        # 日常聊天模式：快速路径，跳过意图分类和复杂上下文处理
        print(f"\n💬 [日常聊天快速路径] 跳过意图分类，直接处理")
        use_rag = False
        
        # 简化上下文处理：只保留最近几轮对话
        historical_turns = conversation_manager.parse_conversation_history(session.context)
        # 只保留最近3轮，避免上下文过长
        recent_turns = historical_turns[-3:] if len(historical_turns) > 3 else historical_turns
        compressed_turns = recent_turns
        
        # 构建简单的对话上下文
        if compressed_turns:
            context_parts = []
            for turn in compressed_turns:
                context_parts.append(f"用户：{turn.user_input}")
                context_parts.append(f"回复：{turn.assistant_reply}")
            context_parts.append(f"用户：{user_input}")
            context_parts.append("回复：")
            llm_context = "\n".join(context_parts)
        else:
            llm_context = f"用户：{user_input}\n回复："
        
        # 简化分类信息（用于日志）
        conversation_type = ConversationType.GENERAL_QA
        classification_details = {
            'intent_type': 'general_qa',
            'confidence': 1.0,
            'processing_time': 0.0,
            'model_used': 'fast_path',
            'has_history': len(historical_turns) > 0,
            'final_type': 'general_qa'
        }
        rag_decision = {
            'intent_confidence': 1.0,
            'intent_type': 'general_qa',
            'conversation_type': 'general_qa',
            'use_rag': False,
            'decision_reason': '前端选择日常聊天模式，快速路径处理'
        }
        
        print(f"💬 [快速路径] 使用简化上下文，跳过意图分类")
    else:
        # 日志分析模式：完整处理流程
        print(f"\n🧠 [智能对话管理] 开始分析对话类型和上下文...")
        
        # 解析历史对话
        historical_turns = conversation_manager.parse_conversation_history(session.context)
        print(f"🧠 [历史解析] 解析出 {len(historical_turns)} 轮历史对话")
        
        # 使用轻量级模型分类当前对话类型
        conversation_type, classification_details = conversation_manager.classify_conversation_type(user_input, len(historical_turns) > 0)
        print(f"🧠 [智能分类] 对话类型: {conversation_type.value}")
        print(f"🧠 [分类详情] 意图: {classification_details['intent_type']}, 置信度: {classification_details['confidence']:.3f}")
        print(f"🧠 [模型信息] 使用模型: {classification_details['model_used']}, 耗时: {classification_details['processing_time']:.3f}秒")
        
        # 压缩历史上下文
        compressed_turns = conversation_manager.compress_context(historical_turns)
        print(f"🧠 [上下文压缩] 压缩后保留 {len(compressed_turns)} 轮对话")
        
        # 使用意图分类结果判断是否需要RAG检索
        use_rag, rag_decision = conversation_manager.should_use_rag(conversation_type, user_input, classification_details)
        
        # 日志分析模式，强制使用RAG
        if query_type == "analysis":
            use_rag = True
            rag_decision['decision_reason'] = "前端选择日志分析模式，使用RAG检索"
            print(f"🔍 [日志分析] 前端选择日志分析模式，使用RAG检索")
        
        print(f"🧠 [智能RAG决策] 使用RAG: {use_rag}")
        print(f"🧠 [决策原因] {rag_decision['decision_reason']}")
        print(f"🧠 [决策详情] 意图置信度: {rag_decision['intent_confidence']:.3f}, 意图类型: {rag_decision['intent_type']}")
        
        # 构建LLM上下文
        llm_context = conversation_manager.build_context_for_llm(compressed_turns, user_input, conversation_type)
    
    if query_type == "general_chat":
        print(f"\n💬 [快速路径上下文]")
        print(f"   保留轮次: {len(compressed_turns)}")
        print(f"   上下文长度: {len(llm_context)} 字符")
    else:
        print(f"\n🔧 [上下文构建]")
        print(f"   原始历史长度: {len(session.context)} 字符")
        print(f"   压缩后长度: {len(llm_context)} 字符")
        print(f"   对话类型: {conversation_type.value}")
        print(f"   使用RAG: {use_rag}")
        print(f"🔧 [LLM上下文] ↓↓↓")
        print("-" * 60)
        print(llm_context)
        print("-" * 60)
    
    # 根据对话类型选择不同的处理逻辑
    logger.info(f"传递给大模型的prompt：\n{llm_context}")  # 调试日志
    logger.info(f"查询类型：{query_type}")  # 记录查询类型
    
    # 5. 调用大模型（根据 query_type 选择策略）
    print(f"\n🔍 [缓存检查] 检查是否有缓存回复...")
    cached_reply = get_cached_reply(user_input, session_id, user)
    if cached_reply:
        reply = cached_reply
        print(f"✅ [缓存命中] 使用缓存回复，长度: {len(reply)} 字符")
        print(f"💾 [缓存回复] {reply[:100]}{'...' if len(reply) > 100 else ''}")
    else:
        print(f"❌ [缓存未命中] 调用大模型API...")
        
        if query_type == "analysis":
            # 日志分析模式：使用 RAG
            print(f"🔍 [RAG模式] 日志分析，使用 RAG 检索")
            print(f"🔍 [RAG查询] 原始查询: '{user_input}'")
            reply = deepseek_r1_api_call(user_input, query_type)
        else:
            # 日常聊天模式：直接调用 LLM，不使用 RAG
            print(f"💬 [对话模式] 日常聊天，不使用 RAG 检索")
            print(f"💬 [对话查询] 查询: '{user_input}'")
            reply = deepseek_r1_api_call(user_input, query_type)
        
        print(f"🤖 [大模型回复] 长度: {len(reply)} 字符")
        print(f"🤖 [回复内容] {reply[:100]}{'...' if len(reply) > 100 else ''}")
        
        # 设置缓存时传入session_id和user
        set_cached_reply(user_input, reply, session_id, user)
        print(f"💾 [缓存保存] 回复已缓存")
    
    # 6. 智能上下文保存 → 改进！
    print(f"\n💾 [智能上下文保存] 使用对话管理器更新历史...")
    
    # 添加新的对话轮次
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata = {
        "query_type": query_type,
        "conversation_type": conversation_type.value,
        "used_rag": use_rag,
        "original_turns": len(historical_turns),
        "compressed_turns": len(compressed_turns),
        # 新增：意图分类详情
        "intent_classification": classification_details,
        "rag_decision": rag_decision
    }
    
    updated_turns = conversation_manager.add_new_turn(
        compressed_turns, user_input, reply, conversation_type, timestamp, metadata
    )
    
    print(f"💾 [对话轮次] 添加新轮次，当前总轮次: {len(updated_turns)}")
    print(f"💾 [元数据] {metadata}")
    
    # 格式化为存储字符串
    new_context = conversation_manager.format_context_for_storage(updated_turns)
    old_context_length = len(session.context)
    new_context_length = len(new_context)
    
    print(f"💾 [上下文更新] 长度变化: {old_context_length} → {new_context_length} 字符")
    print(f"💾 [压缩效果] 压缩比: {new_context_length/max(old_context_length, 1):.2f}")
    
    # 更新会话
    session.context = new_context
    session.save()
    
    print(f"💾 [保存完成] 智能上下文已保存到数据库")
    print(f"💾 [最终状态] 会话ID: {session.session_id}, 轮次: {len(updated_turns)}, 长度: {len(session.context)} 字符")
    
    # session.update_context(user_input, reply)
    
    print(f"\n✅ [请求完成] 返回回复给前端")
    print("=" * 80)

    return {
        "reply": reply,
        # 前端需要的时间戳由前端生成，后端可返回当前时间供参考
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }

@router.post("/chat/stream")
def chat_stream(request, data: ChatIn):
    """流式聊天接口"""
    print("=" * 80)
    print("🚀 [流式对话] 开始处理 Stream Chat 请求")
    print("=" * 80)
    
    # 认证验证
    if not request.auth:
        return StreamingHttpResponse(
            iter([f"data: {json.dumps({'error': '请先登录'})}\n\n"]),
            content_type='text/event-stream'
        )
    
    session_id = data.session_id.strip() or "default_session"
    user_input = data.user_input.strip()
    query_type = data.query_type or "general_chat"
    
    print(f"📝 [流式请求] session_id: '{session_id}', query_type: '{query_type}'")
    print(f"📝 [用户输入] {user_input}")
    
    if not user_input:
        return StreamingHttpResponse(
            iter([f"data: {json.dumps({'error': '请输入消息内容'})}\n\n"]),
            content_type='text/event-stream'
        )
    # 同步处理上传文件引用（如 data/uploads/xxx）并把文件内容附加到 user_input
    try:
        file_paths = re.findall(r"data/uploads/[\w\-\.]+", user_input)
        for rel in file_paths:
            abs_path = _Path(settings.BASE_DIR) / rel
            if abs_path.exists():
                suffix = abs_path.suffix.lower()
                if suffix in ['.txt', '.md', '.json', '.jsonl', '.csv']:
                    with abs_path.open('r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    user_input += f"\n\n[附件: {rel} 内容开始]\n{content}\n[附件: {rel} 内容结束]\n"
                    print(f"📎 [流式附加文件] 附加 {rel} 到输入，长度: {len(content)}")
                elif suffix == '.docx':
                    try:
                        # 使用轻量级 docx 解析（无需 python-docx）：读取 word/document.xml
                        try:
                            with zipfile.ZipFile(str(abs_path)) as zf:
                                if 'word/document.xml' in zf.namelist():
                                    xml_content = zf.read('word/document.xml')
                                else:
                                    xml_content = b''
                            if xml_content:
                                root = ET.fromstring(xml_content)
                                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                                paragraphs = []
                                for p in root.findall('.//w:p', ns):
                                    texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
                                    if texts:
                                        paragraphs.append(''.join(texts))
                                content = '\n'.join(paragraphs)
                            else:
                                content = ''

                            if content:
                                user_input += f"\n\n[附件: {rel} 内容开始]\n{content}\n[附件: {rel} 内容结束]\n"
                                print(f"📎 [流式附加文件] 附加 {rel} 到输入，长度: {len(content)}")
                            else:
                                print(f"⚠️ [流式附加文件] 无法解析 docx 文件或内容为空: {rel}")
                        except Exception as _e:
                            print(f"⚠️ [流式附加文件] 解析 docx 失败: {rel}, error: {_e}")
                    except Exception:
                        print(f"⚠️ [流式附加文件] 无法解析 docx 文件: {rel}")
                else:
                    print(f"⚠️ [流式附加文件] 不支持的文件类型: {rel}")
            else:
                print(f"⚠️ [流式附加文件] 文件不存在: {rel}")
    except Exception as _e:
        print(f"⚠️ [流式附加文件] 处理上传文件时出错: {_e}")
    
    # 获取会话
    user = request.auth
    session = get_or_create_session(session_id, user)
    
    def stream_generator():
        """生成器函数：流式返回"""
        try:
            # 统一交由服务层处理是否为 API 或本地模式；
            # 本地模式在服务层会以“模拟流”的方式增量返回
            # 使用新的流式调用函数（支持 RAG 和历史上下文）
            from .services import deepseek_r1_api_call_stream
            
            print(f"🤖 [流式调用] 开始流式生成，query_type: {query_type}")
            print(f"🤖 [会话历史] 历史长度: {len(session.context)} 字符")
            
            # 调用流式函数，传递历史上下文
            stream_response = deepseek_r1_api_call_stream(
                user_input, 
                query_type, 
                history_context=session.context  # 传递历史上下文
            )
            
            full_reply = ""
            for response in stream_response:
                delta = response.delta if hasattr(response, 'delta') else ""
                if delta:
                    full_reply += delta
                    # 发送增量内容
                    yield f"data: {json.dumps({'delta': delta, 'content': full_reply})}\n\n"
            
            # 保存到会话历史
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metadata = {
                "query_type": query_type,
                "stream": True,
            }
            
            from .conversation_manager import ConversationType
            
            # 解析现有历史
            historical_turns = conversation_manager.parse_conversation_history(session.context)
            
            # 添加新的对话轮次
            updated_turns = conversation_manager.add_new_turn(
                historical_turns, user_input, full_reply, ConversationType.GENERAL_QA, timestamp, metadata
            )
            
            new_context = conversation_manager.format_context_for_storage(updated_turns)
            session.context = new_context
            session.save()
            
            # 发送完成信号
            yield f"data: {json.dumps({'done': True, 'content': full_reply})}\n\n"
            print(f"✅ [流式完成] 总长度: {len(full_reply)} 字符")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [流式错误] {error_msg}")
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
    
    response = StreamingHttpResponse(
        stream_generator(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

# 1. 修复 history 接口
@router.get("/history", response={200: HistoryOut})
def history(request, session_id: str = "default_session"):
    """查看对话历史接口：根据session_id返回对话历史"""
    print("=" * 80)
    print("📚 [历史查询] 开始处理 History 请求")
    print("=" * 80)
    
    # 直接使用 session_id 参数，无需通过 data
    processed_session_id = session_id.strip() or "default_session"
    user_api_key = request.auth.key
    
    print(f"📚 [查询参数] session_id: '{processed_session_id}'")
    print(f"📚 [用户信息] user: '{request.auth.user}', API Key: {user_api_key[:8]}...")
    
    session = services.get_or_create_session(processed_session_id, request.auth)
    
    print(f"📚 [历史内容] 长度: {len(session.context)} 字符")
    if session.context:
        print(f"📚 [内容预览] {session.context[:200]}{'...' if len(session.context) > 200 else ''}")
    else:
        print("📚 [内容预览] 空（无历史记录）")
    
    print(f"📚 [返回结果] 历史记录已准备完毕")
    print("=" * 80)
    
    return {"history": session.context}


# 2. 修复 clear_history 接口
@router.delete("/history", response={200: dict})
def clear_history(request, session_id: str = "default_session"):
    """清空对话历史接口"""
    print("=" * 80)
    print("🗑️ [历史清空] 开始处理 Clear History 请求")
    print("=" * 80)
    
    # 直接使用 session_id 参数，无需通过 data
    processed_session_id = session_id.strip() or "default_session"
    user_api_key = request.auth.key
    
    print(f"🗑️ [清空参数] session_id: '{processed_session_id}'")
    print(f"🗑️ [用户信息] user: '{request.auth.user}', API Key: {user_api_key[:8]}...")
    
    session = services.get_or_create_session(processed_session_id, request.auth)
    
    print(f"🗑️ [清空前状态] 历史长度: {len(session.context)} 字符")
    if session.context:
        print(f"🗑️ [清空前内容] {session.context[:100]}{'...' if len(session.context) > 100 else ''}")
    
    session.clear_context()
    
    print(f"🗑️ [清空完成] 历史记录已清空")
    print(f"🗑️ [清空后状态] 历史长度: {len(session.context)} 字符")
    print("=" * 80)
    
    return {"message": "历史记录已清空"}


@router.get("/models", response={200: ModelsOut})
def list_models(request):
    print("=" * 80)
    print("🧠 [模型列表] 查询可用模型配置")
    print("=" * 80)

    options = get_available_configs()
    current = get_current_config_name()

    print(f"🧠 [当前模型] {current}")
    print(f"🧠 [可选数量] {len(options)}")

    return {"current": current, "options": options}


@router.post("/models/switch", response={200: ModelsOut, 400: ErrorResponse})
def switch_model(request, data: ModelSwitchIn):
    print("=" * 80)
    print("🧠 [模型切换] 请求切换模型")
    print("=" * 80)
    try:
        set_current_config(data.model_key)
        services.reset_log_system()
        print(f"🧠 [模型切换成功] 当前模型: {get_current_config_name()}")
    except KeyError:
        print(f"❌ [模型切换失败] 无效的模型标识: {data.model_key}")
        return 400, {"error": "无效的模型标识"}

    options = get_available_configs()
    current = get_current_config_name()

    return {"current": current, "options": options}

# 将路由添加到API
api.add_router("", router)
