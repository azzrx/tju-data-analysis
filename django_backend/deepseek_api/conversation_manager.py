"""
多轮对话管理器
负责管理对话上下文、窗口限制、摘要压缩等功能
"""

import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from .intent_classifier import get_intent_classifier, IntentType, classify_user_intent, is_rag_required

logger = logging.getLogger(__name__)

class ConversationType(Enum):
    """对话类型枚举（保持向后兼容）"""
    GENERAL_QA = "general_qa"           # 通用问答
    LOG_ANALYSIS = "log_analysis"       # 日志分析
    FOLLOW_UP = "follow_up"            # 追问/澄清
    SUMMARY_REQUEST = "summary_request" # 摘要请求
    TECHNICAL_HELP = "technical_help"   # 技术帮助
    GREETING = "greeting"               # 问候
    UNKNOWN = "unknown"                 # 未知意图

@dataclass
class ConversationTurn:
    """单轮对话数据结构"""
    user_input: str
    assistant_reply: str
    conversation_type: ConversationType
    timestamp: str
    metadata: Dict = None  # 存储额外信息，如检索到的日志数量等

class ConversationManager:
    """多轮对话管理器"""
    
    def __init__(self, max_context_length: int = 4000, max_turns: int = 10):
        """
        初始化对话管理器
        
        Args:
            max_context_length: 最大上下文长度（字符数）
            max_turns: 最大保留轮次
        """
        self.max_context_length = max_context_length
        self.max_turns = max_turns
    
    def classify_conversation_type(self, user_input: str, has_history: bool) -> Tuple[ConversationType, Dict]:
        """
        使用轻量级模型分类对话类型
        
        Args:
            user_input: 用户输入
            has_history: 是否有历史对话
            
        Returns:
            对话类型和分类详情
        """
        # 使用轻量级意图分类器
        intent_result = classify_user_intent(user_input)
        
        # 映射IntentType到ConversationType
        intent_mapping = {
            IntentType.GENERAL_QA: ConversationType.GENERAL_QA,
            IntentType.LOG_ANALYSIS: ConversationType.LOG_ANALYSIS,
            IntentType.FOLLOW_UP: ConversationType.FOLLOW_UP,
            IntentType.SUMMARY_REQUEST: ConversationType.SUMMARY_REQUEST,
            IntentType.TECHNICAL_HELP: ConversationType.TECHNICAL_HELP,
            IntentType.GREETING: ConversationType.GENERAL_QA,  # 问候归类为通用问答
            IntentType.UNKNOWN: ConversationType.GENERAL_QA
        }
        
        conversation_type = intent_mapping.get(intent_result.intent, ConversationType.GENERAL_QA)
        
        # 如果有历史对话，进一步判断是否是追问
        if has_history and intent_result.intent == IntentType.FOLLOW_UP:
            conversation_type = ConversationType.FOLLOW_UP
        elif has_history and intent_result.confidence < 0.5:
            # 低置信度时，检查是否包含追问特征
            follow_up_indicators = ['继续', '详细', '更多', '具体', '再', '进一步']
            if any(indicator in user_input for indicator in follow_up_indicators):
                conversation_type = ConversationType.FOLLOW_UP
        
        # 返回分类结果和详细信息
        classification_details = {
            "intent_type": intent_result.intent.value,
            "confidence": intent_result.confidence,
            "processing_time": intent_result.processing_time,
            "model_used": intent_result.model_used,
            "has_history": has_history,
            "final_type": conversation_type.value
        }
        
        return conversation_type, classification_details
    
    def parse_conversation_history(self, context_string: str) -> List[ConversationTurn]:
        """
        解析对话历史字符串为结构化数据
        
        Args:
            context_string: 原始上下文字符串
            
        Returns:
            对话轮次列表
        """
        turns = []
        if not context_string.strip():
            return turns
        
        # 按照 "用户：...\\n回复：...\\n" 的格式解析
        parts = context_string.split('用户：')[1:]  # 跳过第一个空元素
        
        for part in parts:
            if '回复：' in part:
                user_part, reply_part = part.split('回复：', 1)
                user_input = user_part.strip()
                
                # 找到回复的结束位置（下一个"用户："或字符串结尾）
                reply_lines = reply_part.split('\n')
                assistant_reply = []
                
                for line in reply_lines:
                    if line.strip() == '':
                        continue
                    assistant_reply.append(line)
                
                if assistant_reply:
                    assistant_reply_text = '\n'.join(assistant_reply)
                    
                    # 推断对话类型（简化版）
                    conv_type = self.classify_conversation_type(user_input, len(turns) > 0)
                    
                    turn = ConversationTurn(
                        user_input=user_input,
                        assistant_reply=assistant_reply_text,
                        conversation_type=conv_type,
                        timestamp="",  # 历史数据没有时间戳
                        metadata={}
                    )
                    turns.append(turn)
        
        return turns
    
    def compress_context(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        """
        压缩上下文，保留关键信息
        
        Args:
            turns: 对话轮次列表
            
        Returns:
            压缩后的对话轮次列表
        """
        if len(turns) <= self.max_turns:
            return turns
        
        # 策略1：保留最近的对话
        recent_turns = turns[-self.max_turns:]
        
        # 策略2：如果还是太长，进行摘要压缩
        total_length = sum(len(turn.user_input) + len(turn.assistant_reply) for turn in recent_turns)
        
        if total_length > self.max_context_length:
            # 保留最近3轮，其余进行摘要
            if len(recent_turns) > 3:
                summary_turns = recent_turns[:-3]
                keep_turns = recent_turns[-3:]
                
                # 生成摘要
                summary_text = self._generate_summary(summary_turns)
                summary_turn = ConversationTurn(
                    user_input="[历史对话摘要]",
                    assistant_reply=summary_text,
                    conversation_type=ConversationType.SUMMARY_REQUEST,
                    timestamp="",
                    metadata={"is_summary": True, "original_turns": len(summary_turns)}
                )
                
                return [summary_turn] + keep_turns
        
        return recent_turns
    
    def _generate_summary(self, turns: List[ConversationTurn]) -> str:
        """
        生成对话摘要
        
        Args:
            turns: 需要摘要的对话轮次
            
        Returns:
            摘要文本
        """
        if not turns:
            return "无历史对话"
        
        # 简化版摘要：提取关键主题和结论
        topics = []
        conclusions = []
        
        for turn in turns:
            # 提取主题（用户问题的关键词）
            user_keywords = self._extract_keywords(turn.user_input)
            if user_keywords:
                topics.extend(user_keywords)
            
            # 提取结论（回复的关键信息）
            if len(turn.assistant_reply) > 100:
                # 取前100字符作为摘要
                conclusions.append(turn.assistant_reply[:100] + "...")
        
        summary = f"讨论主题：{', '.join(set(topics[:5]))}。"
        if conclusions:
            summary += f" 主要结论：{conclusions[-1]}"
        
        return summary
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        提取关键词（简化版）
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        # 简化的关键词提取
        keywords = []
        technical_terms = ['数据库', '索引', '连接', '性能', '错误', '日志', '服务', '系统']
        
        for term in technical_terms:
            if term in text:
                keywords.append(term)
        
        return keywords
    
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
    
    def should_use_rag(self, conversation_type: ConversationType, user_input: str, classification_details: Dict = None) -> Tuple[bool, Dict]:
        """
        使用意图分类结果判断是否需要RAG检索
        
        Args:
            conversation_type: 对话类型
            user_input: 用户输入
            classification_details: 分类详情
            
        Returns:
            是否使用RAG和决策详情
        """
        # 使用意图分类器的结果
        intent_result = classify_user_intent(user_input)
        use_rag = is_rag_required(intent_result, user_input)
        
        # 决策详情
        decision_details = {
            "intent_confidence": intent_result.confidence,
            "intent_type": intent_result.intent.value,
            "conversation_type": conversation_type.value,
            "use_rag": use_rag,
            "decision_reason": self._get_rag_decision_reason(intent_result, conversation_type)
        }
        
        # 特殊情况处理
        if conversation_type == ConversationType.FOLLOW_UP:
            # 追问通常不需要新的RAG检索，除非是技术追问
            if intent_result.intent in [IntentType.LOG_ANALYSIS, IntentType.TECHNICAL_HELP]:
                use_rag = True
                decision_details["decision_reason"] = "技术追问需要RAG检索"
            else:
                use_rag = False
                decision_details["decision_reason"] = "普通追问基于历史对话"
        
        elif conversation_type == ConversationType.SUMMARY_REQUEST:
            # 摘要请求不需要RAG
            use_rag = False
            decision_details["decision_reason"] = "摘要请求基于历史对话"
        
        return use_rag, decision_details
    
    def _get_rag_decision_reason(self, intent_result, conversation_type: ConversationType) -> str:
        """获取RAG决策原因"""
        if intent_result.intent == IntentType.LOG_ANALYSIS:
            return f"日志分析意图，置信度: {intent_result.confidence:.2f}"
        elif intent_result.intent == IntentType.TECHNICAL_HELP:
            return f"技术帮助意图，置信度: {intent_result.confidence:.2f}"
        elif intent_result.confidence < 0.5:
            return f"低置信度意图({intent_result.confidence:.2f})，可能需要RAG"
        else:
            return f"通用对话意图({intent_result.intent.value})，不需要RAG"
    
    def format_context_for_storage(self, turns: List[ConversationTurn]) -> str:
        """
        将结构化对话数据格式化为存储字符串
        
        Args:
            turns: 对话轮次列表
            
        Returns:
            格式化的存储字符串
        """
        context_parts = []
        for turn in turns:
            context_parts.append(f"用户：{turn.user_input}")
            context_parts.append(f"回复：{turn.assistant_reply}")
        
        return "\n".join(context_parts) + "\n"

    def add_new_turn(self, turns: List[ConversationTurn], user_input: str, 
                    assistant_reply: str, conversation_type: ConversationType,
                    timestamp: str, metadata: Dict = None) -> List[ConversationTurn]:
        """
        添加新的对话轮次
        
        Args:
            turns: 现有对话轮次
            user_input: 用户输入
            assistant_reply: 助手回复
            conversation_type: 对话类型
            timestamp: 时间戳
            metadata: 元数据
            
        Returns:
            更新后的对话轮次列表
        """
        new_turn = ConversationTurn(
            user_input=user_input,
            assistant_reply=assistant_reply,
            conversation_type=conversation_type,
            timestamp=timestamp,
            metadata=metadata or {}
        )
        
        updated_turns = turns + [new_turn]
        return self.compress_context(updated_turns)

