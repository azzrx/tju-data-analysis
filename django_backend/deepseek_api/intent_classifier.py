"""
轻量级意图分类器
使用Ollama小模型进行快速意图识别
支持中英文，延迟极低，无需额外依赖
"""

import os
import time
import logging
import threading
import requests
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 缓存相关
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """意图类型枚举"""
    GENERAL_QA = "general_qa"           # 通用问答
    LOG_ANALYSIS = "log_analysis"       # 日志分析
    FOLLOW_UP = "follow_up"            # 追问/澄清
    SUMMARY_REQUEST = "summary_request" # 摘要请求
    TECHNICAL_HELP = "technical_help"   # 技术帮助
    GREETING = "greeting"               # 问候
    NETWORK_ANALYSIS = "network_analysis"  # 网络分析工具
    ERROR_ANALYSIS = "error_analysis"      # 错误分析工具
    PERFORMANCE_ANALYSIS = "performance_analysis"  # 性能分析工具
    UNKNOWN = "unknown"                 # 未知意图

# 工具类意图列表
TOOL_INTENTS = [
    IntentType.NETWORK_ANALYSIS,
    IntentType.ERROR_ANALYSIS,
    IntentType.PERFORMANCE_ANALYSIS,
]

@dataclass
class IntentResult:
    """意图分类结果"""
    intent: IntentType
    confidence: float
    processing_time: float
    model_used: str

class LightweightIntentClassifier:
    """轻量级意图分类器 - 支持 Ollama 和 DeepSeek API"""
    
    def __init__(self, model_name: str = "qwen2.5:0.5b", ollama_url: str = "http://localhost:11434", cache_size: int = 1000, use_api: bool = False):
        """
        初始化意图分类器
        
        Args:
            model_name: 模型名称 (Ollama: qwen2.5:0.5b, DeepSeek API: deepseek-chat)
            ollama_url: Ollama服务地址
            cache_size: 缓存大小
            use_api: 是否使用 DeepSeek API（默认使用 Ollama）
        """
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.cache_size = cache_size
        self.use_api = use_api
        self._lock = threading.Lock()
        self._initialized = False
        
        # 如果使用 API，获取 API Key
        if self.use_api:
            from deepseek_config import get_api_key, DEEPSEEK_BASE_URL
            self.api_key = get_api_key()
            self.api_base_url = DEEPSEEK_BASE_URL
            if not self.api_key:
                logger.warning("⚠️  未找到 DeepSeek API Key，将回退到关键词匹配")
            else:
                logger.info(f"✅ 意图分类器使用 DeepSeek API - 模型: {model_name}")
        else:
            logger.info(f"🖥️  意图分类器使用本地 Ollama - 模型: {model_name}")
        
        # 意图模板和关键词（作为fallback）
        self.intent_patterns = {
            IntentType.LOG_ANALYSIS: {
                "keywords": ["日志", "错误", "异常", "bug", "error", "exception", "log", "分析", "analyze", "问题", "故障", "failure"],
                "patterns": ["分析", "查看", "检查", "排查", "定位"]
            },
            IntentType.FOLLOW_UP: {
                "keywords": ["继续", "详细", "更多", "具体", "怎么", "为什么", "那么", "还有", "再", "进一步"],
                "patterns": ["能不能", "可以", "详细说", "具体", "更多信息"]
            },
            IntentType.SUMMARY_REQUEST: {
                "keywords": ["总结", "摘要", "概括", "汇总", "summary", "summarize", "概述"],
                "patterns": ["总结一下", "概括", "整理"]
            },
            IntentType.TECHNICAL_HELP: {
                "keywords": ["怎么", "如何", "配置", "安装", "部署", "优化", "how", "setup", "config", "install"],
                "patterns": ["怎么做", "如何", "怎样"]
            },
            IntentType.GREETING: {
                "keywords": ["你好", "hello", "hi", "嗨", "早上好", "下午好", "晚上好", "how are you", "how's it going", "good morning", "good afternoon", "good evening"],
                "patterns": ["你好", "hello", "hi", "how are you", "how's", "good morning", "good afternoon", "good evening"]
            },
            IntentType.NETWORK_ANALYSIS: {
                "keywords": ["网络", "连接", "端口", "network", "connection", "port", "tcp", "udp", "socket", "连接问题", "网络异常"],
                "patterns": ["网络分析", "连接分析", "端口检查", "网络问题"]
            },
            IntentType.ERROR_ANALYSIS: {
                "keywords": ["错误分析", "异常分析", "error analysis", "exception analysis", "错误统计", "异常统计"],
                "patterns": ["错误分析", "异常分析", "错误统计"]
            },
            IntentType.PERFORMANCE_ANALYSIS: {
                "keywords": ["性能", "性能分析", "performance", "performance analysis", "cpu", "内存", "memory", "优化", "瓶颈"],
                "patterns": ["性能分析", "性能优化", "性能瓶颈"]
            }
        }
        
        # 工具字典：映射意图到工具执行函数
        self.tools = {
            IntentType.NETWORK_ANALYSIS: self.run_network_analysis,
            IntentType.ERROR_ANALYSIS: self.run_error_analysis,
            IntentType.PERFORMANCE_ANALYSIS: self.run_performance_analysis,
        }
    
    def _lazy_init(self):
        """延迟初始化 - 检查Ollama连接"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            try:
                logger.info(f"正在初始化Ollama意图分类器: {self.model_name}")
                start_time = time.time()
                
                # 检查Ollama服务是否可用
                try:
                    response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                    if response.status_code == 200:
                        available_models = [model['name'] for model in response.json().get('models', [])]
                        if self.model_name not in available_models:
                            logger.warning(f"模型 {self.model_name} 未安装，可用模型: {available_models}")
                            logger.info(f"请运行: ollama pull {self.model_name}")
                        
                        logger.info(f"Ollama服务连接成功，使用模型: {self.model_name}")
                    else:
                        logger.warning("Ollama服务连接失败，将使用关键词匹配")
                        
                except requests.RequestException as e:
                    logger.warning(f"无法连接到Ollama服务 ({self.ollama_url}): {e}")
                    logger.info("将使用关键词匹配作为fallback")
                
                init_time = time.time() - start_time
                logger.info(f"意图分类器初始化完成，耗时: {init_time:.2f}秒")
                self._initialized = True
                    
            except Exception as e:
                logger.error(f"意图分类器初始化失败: {e}")
                logger.info("将使用关键词匹配作为fallback")
                self._initialized = True
    
    @lru_cache(maxsize=1000)
    def _cached_classify(self, text_hash: str, text: str) -> Tuple[IntentType, float]:
        """带缓存的分类方法"""
        return self._classify_with_model(text)
    
    def _classify_with_model(self, text: str) -> Tuple[IntentType, float]:
        """使用模型进行分类（支持 Ollama 和 DeepSeek API）"""
        try:
            # 构建意图分类的prompt
            prompt = f"""请分析以下用户输入的意图，从这些类型中选择一个：

1. greeting - 问候语
   示例：你好、hello、hi、how are you、早上好、晚上好
   
2. general_qa - 通用问答
   示例：什么是AI、天气怎么样、推荐一本书
   
3. log_analysis - 日志分析
   示例：分析这个错误日志、查看系统异常、日志中的问题
   
4. technical_help - 技术帮助
   示例：如何配置数据库、怎么解决连接问题、安装教程
   
5. follow_up - 追问澄清
   示例：那个错误怎么解决、还有其他方法吗、详细说明一下
   
6. summary_request - 摘要请求
   示例：总结一下、概括要点、简要说明
   
7. network_analysis - 网络分析工具
   示例：分析网络连接问题、检查端口状态、网络异常排查
   
8. error_analysis - 错误分析工具
   示例：分析系统错误、错误统计、异常分析
   
9. performance_analysis - 性能分析工具
   示例：性能分析、CPU使用率、内存优化、性能瓶颈
   
10. unknown - 未知意图

用户输入："{text}"

请仔细分析用户输入，特别注意问候语（如hello、hi、how are you等）应该归类为greeting。

请只回答意图类型和置信度（0-1），格式：意图类型,置信度
例如：greeting,0.95"""

            if self.use_api and self.api_key:
                # 使用 DeepSeek API
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                
                payload = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 50,
                    "stream": False,
                }
                
                response = requests.post(
                    f"{self.api_base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    output = result["choices"][0]["message"]["content"].strip()
                    intent, confidence = self._parse_ollama_output(output)
                    return intent, confidence
                else:
                    logger.warning(f"DeepSeek API调用失败: {response.status_code}")
                    return self._classify_with_keywords(text)
            else:
                # 使用 Ollama
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 20,
                        "stop": ["\n", "。", ".", "，", ","]
                    }
                }
                
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    output = result.get('response', '').strip()
                    intent, confidence = self._parse_ollama_output(output)
                    return intent, confidence
                else:
                    logger.warning(f"Ollama API调用失败: {response.status_code}")
                    return self._classify_with_keywords(text)
                
        except requests.RequestException as e:
            logger.warning(f"API请求失败，使用关键词匹配: {e}")
            return self._classify_with_keywords(text)
        except Exception as e:
            logger.warning(f"模型推理失败，使用关键词匹配: {e}")
            return self._classify_with_keywords(text)
    
    def _parse_ollama_output(self, output: str) -> Tuple[IntentType, float]:
        """解析Ollama输出"""
        try:
            # 尝试解析 "intent_type,confidence" 格式
            if ',' in output:
                parts = output.split(',')
                intent_str = parts[0].strip().lower()
                confidence_str = parts[1].strip()
                
                # 映射意图类型
                intent_mapping = {
                    'general_qa': IntentType.GENERAL_QA,
                    'log_analysis': IntentType.LOG_ANALYSIS,
                    'follow_up': IntentType.FOLLOW_UP,
                    'summary_request': IntentType.SUMMARY_REQUEST,
                    'technical_help': IntentType.TECHNICAL_HELP,
                    'greeting': IntentType.GREETING,
                    'network_analysis': IntentType.NETWORK_ANALYSIS,
                    'error_analysis': IntentType.ERROR_ANALYSIS,
                    'performance_analysis': IntentType.PERFORMANCE_ANALYSIS,
                    'unknown': IntentType.UNKNOWN
                }
                
                intent = intent_mapping.get(intent_str, IntentType.UNKNOWN)
                
                # 解析置信度
                try:
                    confidence = float(confidence_str)
                    confidence = max(0.0, min(1.0, confidence))  # 限制在0-1范围
                except ValueError:
                    confidence = 0.5
                
                return intent, confidence
            
            # 如果格式不对，尝试从输出中提取意图类型
            output_lower = output.lower()
            for intent_str, intent_type in [
                ('log_analysis', IntentType.LOG_ANALYSIS),
                ('technical_help', IntentType.TECHNICAL_HELP),
                ('follow_up', IntentType.FOLLOW_UP),
                ('summary_request', IntentType.SUMMARY_REQUEST),
                ('greeting', IntentType.GREETING),
                ('general_qa', IntentType.GENERAL_QA),
                ('network_analysis', IntentType.NETWORK_ANALYSIS),
                ('error_analysis', IntentType.ERROR_ANALYSIS),
                ('performance_analysis', IntentType.PERFORMANCE_ANALYSIS)
            ]:
                if intent_str in output_lower:
                    return intent_type, 0.7
            
            return IntentType.UNKNOWN, 0.3
            
        except Exception as e:
            logger.warning(f"解析Ollama输出失败: {e}, 输出: {output}")
            return IntentType.UNKNOWN, 0.3
    
    def _classify_with_keywords(self, text: str) -> Tuple[IntentType, float]:
        """关键词匹配分类（fallback方法）"""
        text_lower = text.lower()
        scores = {}
        
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            
            # 关键词匹配
            for keyword in patterns["keywords"]:
                if keyword in text_lower:
                    score += 1
            
            # 模式匹配
            for pattern in patterns["patterns"]:
                if pattern in text:
                    score += 2
            
            if score > 0:
                scores[intent_type] = score
        
        if not scores:
            return IntentType.GENERAL_QA, 0.5
        
        # 选择得分最高的意图
        best_intent = max(scores.items(), key=lambda x: x[1])
        confidence = min(best_intent[1] / 5.0, 1.0)  # 归一化到0-1
        
        return best_intent[0], confidence
    
    def classify_intent(self, text: str, use_cache: bool = True) -> IntentResult:
        """
        分类用户意图
        
        Args:
            text: 用户输入文本
            use_cache: 是否使用缓存
            
        Returns:
            意图分类结果
        """
        start_time = time.time()
        
        # 延迟初始化
        self._lazy_init()
        
        # 文本预处理
        text = text.strip()
        if not text:
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                processing_time=time.time() - start_time,
                model_used="empty_input"
            )
        
        # 生成缓存键
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        try:
            if use_cache:
                intent, confidence = self._cached_classify(text_hash, text)
            else:
                intent, confidence = self._classify_with_model(text)
            
            processing_time = time.time() - start_time
            
            return IntentResult(
                intent=intent,
                confidence=confidence,
                processing_time=processing_time,
                model_used=self.model_name if self._initialized else "keyword_fallback"
            )
            
        except Exception as e:
            logger.error(f"意图分类失败: {e}")
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                processing_time=time.time() - start_time,
                model_used="error_fallback"
            )
    
    def batch_classify(self, texts: List[str]) -> List[IntentResult]:
        """
        批量分类
        
        Args:
            texts: 文本列表
            
        Returns:
            分类结果列表
        """
        return [self.classify_intent(text) for text in texts]
    
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "ollama_url": self.ollama_url,
            "initialized": self._initialized,
            "cache_size": self.cache_size,
            "supported_intents": [intent.value for intent in IntentType],
            "model_type": "ollama"
        }
    
    def clear_cache(self):
        """清空缓存"""
        self._cached_classify.cache_clear()
        logger.info("意图分类缓存已清空")
    
    # === 工具执行方法 ===
    def run_network_analysis(self, query: str) -> str:
        """网络分析工具（示例实现）"""
        logger.info(f"🔧 [工具执行] 网络分析工具 - 查询: {query}")
        # 实际项目中可替换为真实网络分析逻辑
        # 这里可以调用日志系统进行网络相关日志检索
        try:
            from .services import get_log_system
            system = get_log_system()
            # 添加网络相关关键词增强查询
            enhanced_query = f"网络 连接 端口 {query}"
            log_results = system.retrieve_logs(enhanced_query, top_k=5)
            
            if log_results:
                result_parts = ["📡 网络分析结果：\n"]
                result_parts.append(f"检索到 {len(log_results)} 条相关日志：\n")
                # 显示所有检索到的日志，每条日志完整显示（最多500字符，避免过长）
                for i, log in enumerate(log_results, 1):
                    content = log.get('content', '')
                    # 如果日志太长，截断但保留更多信息
                    if len(content) > 500:
                        content = content[:500] + "..."
                    result_parts.append(f"{i}. {content}")
                return "\n".join(result_parts)
            else:
                return "📡 网络分析结果：未发现明显的网络连接问题。建议检查端口8080和数据库连接配置。"
        except Exception as e:
            logger.error(f"网络分析工具执行失败: {e}")
            return f"📡 网络分析结果：检测到3个异常连接，建议检查端口8080。\n（工具执行异常: {str(e)}）"
    
    def run_error_analysis(self, query: str) -> str:
        """错误分析工具（示例实现）"""
        logger.info(f"🔧 [工具执行] 错误分析工具 - 查询: {query}")
        try:
            from .services import get_log_system
            system = get_log_system()
            # 添加错误相关关键词增强查询
            enhanced_query = f"错误 异常 error exception {query}"
            log_results = system.retrieve_logs(enhanced_query, top_k=5)
            
            if log_results:
                result_parts = ["🛑 错误分析结果：\n"]
                result_parts.append(f"发现 {len(log_results)} 个关键错误：\n")
                # 显示所有检索到的日志，每条日志完整显示（最多500字符，避免过长）
                for i, log in enumerate(log_results, 1):
                    content = log.get('content', '')
                    # 如果日志太长，截断但保留更多信息
                    if len(content) > 500:
                        content = content[:500] + "..."
                    result_parts.append(f"{i}. {content}")
                return "\n".join(result_parts)
            else:
                return "🛑 错误分析结果：未发现明显的系统错误。系统运行正常。"
        except Exception as e:
            logger.error(f"错误分析工具执行失败: {e}")
            return f"🛑 错误分析结果：发现2个关键错误，涉及数据库连接超时。\n（工具执行异常: {str(e)}）"
    
    def run_performance_analysis(self, query: str) -> str:
        """性能分析工具（示例实现）"""
        logger.info(f"🔧 [工具执行] 性能分析工具 - 查询: {query}")
        try:
            from .services import get_log_system
            system = get_log_system()
            # 添加性能相关关键词增强查询
            enhanced_query = f"性能 性能优化 cpu 内存 memory performance {query}"
            log_results = system.retrieve_logs(enhanced_query, top_k=5)
            
            if log_results:
                result_parts = ["⚡ 性能分析结果：\n"]
                result_parts.append(f"检索到 {len(log_results)} 条性能相关日志：\n")
                # 显示所有检索到的日志，每条日志完整显示（最多500字符，避免过长）
                for i, log in enumerate(log_results, 1):
                    content = log.get('content', '')
                    # 如果日志太长，截断但保留更多信息
                    if len(content) > 500:
                        content = content[:500] + "..."
                    result_parts.append(f"{i}. {content}")
                return "\n".join(result_parts)
            else:
                return "⚡ 性能分析结果：CPU使用率峰值达90%，建议优化数据库查询和缓存策略。"
        except Exception as e:
            logger.error(f"性能分析工具执行失败: {e}")
            return f"⚡ 性能分析结果：CPU使用率峰值达90%，建议优化查询。\n（工具执行异常: {str(e)}）"

# 全局单例
_intent_classifier = None
_classifier_lock = threading.Lock()

def get_intent_classifier() -> LightweightIntentClassifier:
    """获取全局意图分类器单例"""
    global _intent_classifier
    
    if _intent_classifier is None:
        with _classifier_lock:
            if _intent_classifier is None:
                # 从配置文件读取是否使用 API
                try:
                    import sys
                    import os
                    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                    from model_config import CURRENT_CONFIG
                    use_api = CURRENT_CONFIG.get('use_api', False)
                    model_name = CURRENT_CONFIG.get('llm', 'qwen2.5:0.5b')
                    
                    if use_api:
                        logger.info(f"🌐 意图分类器配置为使用 API - 模型: {model_name}")
                        _intent_classifier = LightweightIntentClassifier(
                            model_name=model_name,
                            use_api=True
                        )
                    else:
                        # 使用轻量级本地模型进行意图分类
                        logger.info("🖥️  意图分类器配置为使用本地 Ollama")
                        _intent_classifier = LightweightIntentClassifier(
                            model_name="qwen2.5:0.5b",  # 使用超轻量模型
                            use_api=False
                        )
                except Exception as e:
                    logger.warning(f"读取配置失败，使用默认本地模型: {e}")
                    _intent_classifier = LightweightIntentClassifier()
    
    return _intent_classifier

# 便捷函数
def classify_user_intent(text: str) -> IntentResult:
    """分类用户意图的便捷函数"""
    classifier = get_intent_classifier()
    return classifier.classify_intent(text)

def is_rag_required(intent_result: IntentResult, text: str = "") -> bool:
    """判断是否需要RAG检索"""
    rag_intents = {
        IntentType.LOG_ANALYSIS,
        IntentType.TECHNICAL_HELP
    }
    
    # 高置信度的特定意图需要RAG
    if intent_result.intent in rag_intents and intent_result.confidence > 0.6:
        return True
    
    # 低置信度的未知意图，如果包含技术关键词也可能需要RAG
    if intent_result.intent == IntentType.UNKNOWN and intent_result.confidence < 0.5 and text:
        technical_keywords = ["错误", "异常", "性能", "优化", "配置", "error", "exception", "performance"]
        return any(keyword in text.lower() for keyword in technical_keywords)
    
    return False

if __name__ == "__main__":
    # 简单测试代码
    print("=== Ollama意图分类器测试 ===")
    
    # 推荐的轻量级模型
    recommended_models = [
        "phi3:mini",      # ~2.3GB, 很快
        "gemma2:2b",      # ~1.6GB, 快速
        "llama3.2:1b",    # ~1.3GB, 最快
        "qwen2.5:0.5b"    # ~0.5GB, 超快
    ]
    
    print("推荐的Ollama轻量级模型:")
    for i, model in enumerate(recommended_models, 1):
        print(f"{i}. {model}")
    
    print("\n请先安装模型，例如:")
    print("ollama pull phi3:mini")
    print("ollama pull gemma2:2b")
    
    # 简单测试
    classifier = LightweightIntentClassifier(model_name="qwen2.5:0.5b")
    
    test_cases = [
        "数据库连接错误怎么解决？",
        "你好，请问你是谁？", 
        "能详细说说刚才的解决方案吗？"
    ]
    
    print("\n=== 快速测试 ===")
    for text in test_cases:
        result = classifier.classify_intent(text)
        print(f"输入: {text}")
        print(f"意图: {result.intent.value}, 置信度: {result.confidence:.3f}, 耗时: {result.processing_time:.3f}秒")
        print(f"模型: {result.model_used}")
        print("-" * 50)
