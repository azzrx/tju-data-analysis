"""
查询优化器
实现查询重写、扩展、改进等功能
提升检索准确率和召回率
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OptimizedQuery:
    """优化后的查询"""
    original: str
    rewritten: List[str]  # 重写后的查询列表
    expanded_terms: List[str]  # 扩展的术语
    intent: str  # 查询意图
    

class QueryOptimizer:
    """
    查询优化器
    负责查询改写、扩展、术语标准化等
    """
    
    def __init__(self):
        # 日志领域的同义词词典
        self.synonym_dict = {
            "错误": ["error", "异常", "exception", "失败", "failure", "bug", "问题"],
            "error": ["错误", "异常", "exception", "失败", "failure"],
            "连接": ["connection", "链接", "connect"],
            "超时": ["timeout", "time out", "超过时间"],
            "数据库": ["database", "db", "mysql", "postgresql", "mongo"],
            "性能": ["performance", "速度", "慢", "slow", "延迟", "latency"],
            "内存": ["memory", "mem", "ram", "oom"],
            "CPU": ["cpu", "处理器", "processor"],
            "网络": ["network", "net", "网关", "gateway"],
            "服务": ["service", "服务器", "server"],
            "崩溃": ["crash", "宕机", "down", "故障", "failure"],
            "日志": ["log", "logs", "logging"],
            "配置": ["config", "configuration", "settings", "设置"],
            "认证": ["auth", "authentication", "授权", "authorization"],
            "token": ["令牌", "凭证", "credential"],
            "请求": ["request", "req"],
            "响应": ["response", "resp"],
            "并发": ["concurrent", "并行", "parallel"],
        }
        
        # 错误类型映射
        self.error_patterns = {
            "连接错误": ["connection refused", "connection timeout", "connection lost", "无法连接"],
            "认证错误": ["authentication failed", "unauthorized", "invalid token", "认证失败", "token校验失败"],
            "数据库错误": ["database error", "sql error", "db connection", "连接池耗尽"],
            "超时错误": ["timeout", "time out", "响应超时", "请求超时"],
            "内存错误": ["out of memory", "memory overflow", "oom", "内存溢出"],
            "网络错误": ["network error", "dns error", "网络异常"],
            "权限错误": ["permission denied", "access denied", "forbidden", "权限不足"],
        }
        
        # 日志级别关键词
        self.level_keywords = {
            "严重": ["fatal", "critical", "严重"],
            "错误": ["error", "错误"],
            "警告": ["warn", "warning", "警告"],
            "信息": ["info", "information", "信息"],
        }
        
        logger.info("查询优化器初始化完成")
    
    def optimize(self, query: str) -> OptimizedQuery:
        """
        优化查询
        
        Args:
            query: 原始查询
            
        Returns:
            优化后的查询对象
            
        Raises:
            ValueError: 参数验证失败
        """
        # 参数验证
        if not query or not isinstance(query, str):
            raise ValueError("query 必须是非空字符串")
        
        query = query.strip()
        if not query:
            logger.warning("查询为空字符串")
            return OptimizedQuery(
                original=query,
                rewritten=[query],
                expanded_terms=[],
                intent="unknown"
            )
        
        logger.info(f"优化查询: '{query}'")
        
        # 1. 清理查询
        cleaned_query = self._clean_query(query)
        
        # 2. 识别查询意图
        intent = self._detect_intent(cleaned_query)
        logger.info(f"查询意图: {intent}")
        
        # 3. 查询重写
        rewritten_queries = self._rewrite_query(cleaned_query, intent)
        logger.info(f"重写查询: {rewritten_queries}")
        
        # 4. 术语扩展
        expanded_terms = self._expand_terms(cleaned_query)
        logger.info(f"扩展术语: {expanded_terms}")
        
        result = OptimizedQuery(
            original=query,
            rewritten=rewritten_queries,
            expanded_terms=expanded_terms,
            intent=intent
        )
        
        return result
    
    def _clean_query(self, query: str) -> str:
        """清理查询文本"""
        # 去除多余空格
        query = re.sub(r'\s+', ' ', query)
        query = query.strip()
        
        # 去除特殊字符（保留中文、英文、数字、基本标点）
        query = re.sub(r'[^\w\s\u4e00-\u9fff\?\!\.\,\:\;，。？！：；]', '', query)
        
        return query
    
    def _detect_intent(self, query: str) -> str:
        """
        检测查询意图（用于优化日志检索）
        
        注意：这是内部检索优化意图，不是前端的查询类型。
        前端只有两种查询类型：analysis（日志分析）和 general_chat（日常聊天）。
        
        内部检索意图（用于优化 RAG 检索）：
        - error_diagnosis: 错误诊断（查找错误相关日志）
        - solution_seeking: 寻求解决方案（查找问题和解决方法）
        - log_search: 通用日志搜索（默认）
        """
        query_lower = query.lower()
        
        # 错误相关查询
        if any(word in query_lower for word in ['错误', 'error', '异常', 'exception', '失败', 'failure', 'bug']):
            # 如果是寻求解决方案
            if any(word in query_lower for word in ['怎么', 'how', '解决', 'solve', 'fix', '修复', '如何']):
                return 'solution_seeking'
            else:
                # 错误诊断
                return 'error_diagnosis'
        
        # 默认为日志搜索
        return 'log_search'
    
    def _rewrite_query(self, query: str, intent: str) -> List[str]:
        """
        查询重写
        根据意图生成多个查询变体（用于提升检索召回率）
        """
        rewritten = [query]  # 始终包含原始查询
        
        # 根据意图添加特定的重写规则
        if intent == 'error_diagnosis':
            # 添加错误相关的变体
            rewritten.append(f"{query} 错误信息")
            rewritten.append(f"{query} 异常堆栈")
            
        elif intent == 'solution_seeking':
            # 添加解决方案相关的变体
            rewritten.append(f"{query} 解决方法")
            rewritten.append(f"{query} 修复方案")
            rewritten.append(f"{query} 解决方案")
        
        # 去重
        rewritten = list(dict.fromkeys(rewritten))
        
        return rewritten
    
    def _expand_terms(self, query: str) -> List[str]:
        """
        术语扩展
        使用同义词词典扩展查询术语
        """
        expanded = set()
        
        # 提取查询中的关键词
        keywords = self._extract_keywords(query)
        
        for keyword in keywords:
            # 查找同义词
            for base_term, synonyms in self.synonym_dict.items():
                if keyword.lower() == base_term.lower() or keyword.lower() in [s.lower() for s in synonyms]:
                    # 添加同义词
                    expanded.add(base_term)
                    expanded.update(synonyms)
        
        return list(expanded)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取查询中的关键词"""
        # 简单的关键词提取（按空格分词）
        # 可以使用更复杂的 NLP 方法
        keywords = []
        
        # 中文词语提取
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', query)
        keywords.extend(chinese_words)
        
        # 英文单词提取
        english_words = re.findall(r'[a-zA-Z]+', query)
        keywords.extend(english_words)
        
        return keywords
    
    def suggest_filters(self, query: str) -> Dict[str, Any]:
        """
        根据查询建议元数据过滤器
        
        Returns:
            建议的过滤条件
        """
        filters = {}
        query_lower = query.lower()
        
        # 检测日志级别
        for level, keywords in self.level_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                if level == "严重":
                    filters['level'] = 'FATAL'
                elif level == "错误":
                    filters['level'] = 'ERROR'
                elif level == "警告":
                    filters['level'] = 'WARN'
                break
        
        # 检测严重性阈值
        if any(word in query_lower for word in ['严重', 'critical', 'fatal', '紧急']):
            filters['min_severity'] = 0.7
        
        return filters
    
    def enhance_query_for_retrieval(self, query: str) -> str:
        """
        为检索增强查询
        生成一个最优的检索查询
        """
        optimized = self.optimize(query)
        
        # 组合原始查询和扩展术语
        enhanced_parts = [optimized.original]
        
        # 添加最相关的扩展术语（限制数量避免噪声）
        if optimized.expanded_terms:
            enhanced_parts.extend(optimized.expanded_terms[:5])
        
        enhanced_query = ' '.join(enhanced_parts)
        
        logger.info(f"增强后的检索查询: '{enhanced_query}'")
        return enhanced_query
    
    def extract_error_type(self, query: str) -> Optional[str]:
        """从查询中提取错误类型"""
        query_lower = query.lower()
        
        for error_type, patterns in self.error_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return error_type
        
        return None


class AdvancedQueryOptimizer(QueryOptimizer):
    """
    高级查询优化器
    使用 LLM 进行更智能的查询改写
    """
    
    def __init__(self, llm=None):
        super().__init__()
        self.llm = llm
        logger.info("高级查询优化器初始化完成")
    
    def optimize_with_llm(self, query: str) -> OptimizedQuery:
        """
        使用 LLM 优化查询
        
        Args:
            query: 原始查询
            
        Returns:
            优化后的查询对象
        """
        if not self.llm:
            logger.warning("未配置 LLM，回退到基础优化")
            return self.optimize(query)
        
        try:
            # 构建提示词
            prompt = f"""请帮我优化以下日志分析查询，提取关键信息和同义词。

原始查询：{query}

请以JSON格式返回：
{{
    "intent": "查询意图（error_diagnosis/solution_seeking/log_search）",
    "rewritten": ["重写后的查询1", "重写后的查询2"],
    "expanded_terms": ["扩展术语1", "扩展术语2"]
}}

只返回JSON，不要其他说明。"""
            
            # 调用 LLM
            response = self.llm.complete(prompt)
            
            # 解析响应
            import json
            result_dict = json.loads(response.text)
            
            return OptimizedQuery(
                original=query,
                rewritten=result_dict.get('rewritten', [query]),
                expanded_terms=result_dict.get('expanded_terms', []),
                intent=result_dict.get('intent', 'log_search')
            )
            
        except Exception as e:
            logger.error(f"LLM 查询优化失败: {e}，回退到基础优化")
            return self.optimize(query)


def optimize_query(query: str) -> OptimizedQuery:
    """便捷函数：优化查询"""
    optimizer = QueryOptimizer()
    return optimizer.optimize(query)


if __name__ == "__main__":
    # 测试
    print("=== 查询优化器测试 ===")
    
    optimizer = QueryOptimizer()
    
    test_queries = [
        "数据库连接错误怎么解决？",
        "系统性能很慢",
        "为什么会出现内存溢出？",
        "查看认证失败的日志",
    ]
    
    for query in test_queries:
        print(f"\n原始查询: {query}")
        result = optimizer.optimize(query)
        print(f"意图: {result.intent}")
        print(f"重写: {result.rewritten}")
        print(f"扩展: {result.expanded_terms}")
        print(f"建议过滤器: {optimizer.suggest_filters(query)}")
        print("-" * 60)

