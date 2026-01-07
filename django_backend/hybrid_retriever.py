"""
高级混合检索器
实现 BM25 + 向量检索的混合检索策略
支持日志元数据过滤和时间序列分析
"""

import os
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# numpy 用于处理 BM25 返回的数组
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# BM25 算法 - 可选依赖
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    logger.warning("rank-bm25 未安装，BM25 检索功能将不可用")
    logger.info("安装方法: pip install rank-bm25")
    BM25_AVAILABLE = False
    BM25Okapi = None

# llama-index - 必需依赖
try:
    from llama_index.core import VectorStoreIndex
    from llama_index.core.schema import NodeWithScore, TextNode
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    logger.error("llama-index 未安装，混合检索器无法使用")
    LLAMA_INDEX_AVAILABLE = False
    VectorStoreIndex = None
    NodeWithScore = None
    TextNode = None


@dataclass
class LogMetadata:
    """日志元数据"""
    service: Optional[str] = None
    level: Optional[str] = None  # ERROR, WARN, FATAL, INFO
    error_type: Optional[str] = None
    component: Optional[str] = None
    timestamp: Optional[datetime] = None
    severity_score: float = 0.0  # 严重程度评分


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    score: float
    metadata: LogMetadata
    source: str  # 'vector', 'bm25', 'hybrid'
    node_id: Optional[str] = None


class HybridRetriever:
    """
    混合检索器
    结合 BM25 关键词检索和向量语义检索
    """
    
    def __init__(
        self,
        vector_index: VectorStoreIndex,
        documents: List[Dict[str, str]],
        alpha: float = 0.5
    ):
        """
        初始化混合检索器
        
        Args:
            vector_index: llama-index 的向量索引
            documents: 文档列表，每个文档是 {"text": "...", "metadata": {...}}
            alpha: 向量检索和 BM25 的权重，0.5 表示各占 50%
        
        Raises:
            ValueError: 参数验证失败
            RuntimeError: 依赖库未安装
        """
        # 参数验证
        if not LLAMA_INDEX_AVAILABLE:
            raise RuntimeError("llama-index 未安装，无法初始化混合检索器")
        
        if vector_index is None:
            raise ValueError("vector_index 不能为 None")
        
        if not isinstance(documents, list):
            raise ValueError(f"documents 必须是列表类型，当前类型: {type(documents)}")
        
        if not documents:
            raise ValueError("documents 不能为空列表")
        
        if not (0 <= alpha <= 1):
            raise ValueError(f"alpha 必须在 [0, 1] 范围内，当前值: {alpha}")
        
        self.vector_index = vector_index
        self.documents = documents
        self.alpha = float(alpha)  # 向量检索权重
        self.beta = 1.0 - self.alpha  # BM25 权重
        
        # 初始化 BM25 相关属性
        self.bm25 = None
        self.tokenized_docs = []
        self.bm25_enabled = BM25_AVAILABLE
        
        # 构建 BM25 索引
        if self.bm25_enabled:
            logger.info("正在构建 BM25 索引...")
            try:
                self._build_bm25_index()
            except Exception as e:
                logger.error(f"BM25 索引构建失败: {e}")
                self.bm25_enabled = False
                logger.warning("将仅使用向量检索")
        else:
            logger.warning("BM25 不可用，将仅使用向量检索")
        
        # 提取元数据
        self._extract_metadata()
        
        logger.info(f"混合检索器初始化完成：{len(documents)} 条文档，alpha={alpha}")
    
    def _build_bm25_index(self):
        """
        构建 BM25 索引
        
        Raises:
            RuntimeError: BM25 不可用或构建失败
        """
        if not BM25_AVAILABLE or BM25Okapi is None:
            raise RuntimeError("BM25 库未安装")
        
        # 分词（简单的空格分词，可以根据需要使用更复杂的分词器）
        tokenized_docs = []
        for i, doc in enumerate(self.documents):
            try:
                text = doc.get("text", "")
                if not isinstance(text, str):
                    logger.warning(f"文档 {i} 的 text 字段不是字符串类型，跳过")
                    tokenized_docs.append([])
                    continue
                
                # 简单分词：中文按字符分，英文按单词分
                tokens = self._tokenize(text)
                tokenized_docs.append(tokens)
            except Exception as e:
                logger.error(f"文档 {i} 分词失败: {e}")
                tokenized_docs.append([])
        
        if not tokenized_docs or all(not tokens for tokens in tokenized_docs):
            raise RuntimeError("所有文档分词后都为空，无法构建 BM25 索引")
        
        try:
            self.bm25 = BM25Okapi(tokenized_docs)
            self.tokenized_docs = tokenized_docs
            logger.info(f"BM25 索引构建完成：{len(tokenized_docs)} 条文档")
        except Exception as e:
            raise RuntimeError(f"BM25Okapi 初始化失败: {e}")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        分词函数
        中文按字符分，英文按单词分
        """
        tokens = []
        
        # 使用正则表达式分割中英文
        # 保留连续的英文单词和数字，中文按字符分
        pattern = r'[a-zA-Z0-9_]+|[\u4e00-\u9fff]'
        matches = re.findall(pattern, text.lower())
        
        return matches
    
    def _extract_metadata(self):
        """从文档中提取元数据（服务名、级别、时间等）"""
        self.doc_metadata = []
        
        for doc in self.documents:
            text = doc.get("text", "")
            metadata = self._parse_log_metadata(text)
            self.doc_metadata.append(metadata)
        
        logger.info(f"元数据提取完成：{len(self.doc_metadata)} 条记录")
    
    def _parse_log_metadata(self, text: str) -> LogMetadata:
        """
        解析日志元数据
        根据日志格式提取结构化信息
        """
        metadata = LogMetadata()
        
        # 解析 CSV 格式：服务,级别,错误,消息,组件,原因
        # 注意：text 可能是 "Pandas(Index=0, 服务='AuthService', 级别='ERROR', ...)" 格式
        try:
            # 尝试多种解析方式
            if ',' in text:
                # 方法1：直接按逗号分割（标准 CSV）
                parts = [p.strip() for p in text.split(',')]
                if len(parts) >= 6:
                    # 清理可能的引号
                    metadata.service = parts[0].strip("'\" ").strip() if parts[0].strip() else None
                    metadata.level = parts[1].strip("'\" ").strip() if parts[1].strip() else None
                    metadata.error_type = parts[2].strip("'\" ").strip() if parts[2].strip() else None
                    if len(parts) > 4:
                        metadata.component = parts[4].strip("'\" ").strip() if parts[4].strip() else None
                
                # 方法2：如果上面没解析到，尝试从 Pandas 格式提取
                if not metadata.level and '级别' in text:
                    import re
                    level_match = re.search(r"级别\s*[=:]\s*['\"]?(\w+)['\"]?", text)
                    if level_match:
                        metadata.level = level_match.group(1).upper()
                
                if not metadata.service and '服务' in text:
                    import re
                    service_match = re.search(r"服务\s*[=:]\s*['\"]?(\w+)['\"]?", text)
                    if service_match:
                        metadata.service = service_match.group(1)
                
                # 计算严重程度评分
                metadata.severity_score = self._calculate_severity(metadata.level)
        except Exception as e:
            logger.debug(f"解析日志元数据失败: {e}, 文本: {text[:50]}...")
        
        return metadata
    
    def _calculate_severity(self, level: Optional[str]) -> float:
        """计算日志严重程度评分"""
        severity_map = {
            'FATAL': 1.0,
            'ERROR': 0.8,
            'WARN': 0.5,
            'WARNING': 0.5,
            'INFO': 0.2,
            'DEBUG': 0.1
        }
        
        if level and level.upper() in severity_map:
            return severity_map[level.upper()]
        return 0.3  # 默认分数
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        boost_recent: bool = False,
        boost_severity: bool = True
    ) -> List[RetrievalResult]:
        """
        混合检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filters: 元数据过滤条件，如 {"level": "ERROR", "service": "AuthService"}
            boost_recent: 是否提升最近日志的权重
            boost_severity: 是否提升高严重性日志的权重
            
        Returns:
            检索结果列表
            
        Raises:
            ValueError: 参数验证失败
        """
        # 参数验证
        if not query or not isinstance(query, str):
            raise ValueError("query 必须是非空字符串")
        
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(f"top_k 必须是正整数，当前值: {top_k}")
        
        query = query.strip()
        if not query:
            logger.warning("查询为空字符串，返回空结果")
            return []
        
        logger.info(f"混合检索：query='{query[:50]}...', top_k={top_k}")
        
        # 1. 向量检索
        try:
            candidate_count = min(top_k * 2, 100)  # 限制候选数量
            vector_results = self._vector_retrieve(query, candidate_count)
            logger.info(f"向量检索返回 {len(vector_results)} 条结果")
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            vector_results = []
        
        # 2. BM25 检索
        bm25_results = []
        if self.bm25_enabled:
            try:
                bm25_results = self._bm25_retrieve(query, candidate_count)
                logger.info(f"BM25 检索返回 {len(bm25_results)} 条结果")
            except Exception as e:
                logger.error(f"BM25 检索失败: {e}")
                bm25_results = []
        else:
            logger.debug("BM25 检索未启用，跳过")
        
        # 如果两种检索都失败，返回空结果
        if not vector_results and not bm25_results:
            logger.warning("向量检索和 BM25 检索都没有返回结果")
            return []
        
        # 3. 合并结果
        try:
            merged_results = self._merge_results(vector_results, bm25_results)
            logger.info(f"合并后共 {len(merged_results)} 条结果")
        except Exception as e:
            logger.error(f"结果合并失败: {e}")
            # 回退：只使用向量检索结果
            merged_results = vector_results[:top_k]
            logger.warning("回退到仅使用向量检索结果")
        
        # 4. 应用元数据过滤
        if filters and isinstance(filters, dict):
            try:
                before_filter_count = len(merged_results)
                filtered_results = self._apply_filters(merged_results, filters)
                after_filter_count = len(filtered_results)
                logger.info(f"过滤前: {before_filter_count} 条，过滤后: {after_filter_count} 条")
                
                # 如果过滤后结果为空，但过滤前有结果，说明过滤条件太严格
                # 为了不丢失所有结果，我们返回未过滤的结果，但记录警告
                if after_filter_count == 0 and before_filter_count > 0:
                    logger.warning(f"⚠ 过滤条件 '{filters}' 过滤掉了所有 {before_filter_count} 条结果")
                    logger.warning("⚠ 返回未过滤的结果以避免空结果，但建议检查过滤条件是否合理")
                    # 保留未过滤的结果，但降低它们的分数（表示可能不完全匹配）
                    for result in merged_results:
                        result.score *= 0.9  # 轻微降低分数
                    merged_results = merged_results
                else:
                    merged_results = filtered_results
            except Exception as e:
                logger.error(f"过滤失败: {e}，跳过过滤")
        
        # 5. 应用权重提升
        if boost_severity:
            try:
                merged_results = self._boost_by_severity(merged_results)
            except Exception as e:
                logger.error(f"严重性权重提升失败: {e}，跳过")
        
        # 6. 排序并返回 top_k
        try:
            merged_results.sort(key=lambda x: x.score, reverse=True)
            results = merged_results[:top_k]
        except Exception as e:
            logger.error(f"排序失败: {e}")
            results = merged_results[:top_k]
        
        logger.info(f"最终返回 {len(results)} 条结果")
        return results
    
    def _vector_retrieve(self, query: str, top_k: int) -> List[RetrievalResult]:
        """向量检索"""
        try:
            retriever = self.vector_index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)
            
            results = []
            for i, node in enumerate(nodes):
                if i >= len(self.doc_metadata):
                    metadata = LogMetadata()
                else:
                    metadata = self.doc_metadata[i] if i < len(self.doc_metadata) else LogMetadata()
                
                result = RetrievalResult(
                    content=node.text,
                    score=node.score if node.score else 0.5,
                    metadata=metadata,
                    source='vector',
                    node_id=node.node_id if hasattr(node, 'node_id') else None
                )
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    def _bm25_retrieve(self, query: str, top_k: int) -> List[RetrievalResult]:
        """
        BM25 检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        if not self.bm25_enabled or self.bm25 is None:
            logger.debug("BM25 未启用")
            return []
        
        try:
            # 分词
            query_tokens = self._tokenize(query)
            if not query_tokens:
                logger.warning("查询分词后为空，BM25 检索返回空结果")
                return []
            
            # BM25 评分（返回 numpy 数组）
            scores = self.bm25.get_scores(query_tokens)
            
            # 转换为 Python 列表（避免 numpy 数组的真值判断问题）
            if NUMPY_AVAILABLE and isinstance(scores, np.ndarray):
                scores = scores.tolist()
            
            if len(scores) == 0:
                logger.warning("BM25 评分为空")
                return []
            
            # 验证分数数组长度
            if len(scores) != len(self.documents):
                logger.error(f"BM25 分数数量 ({len(scores)}) 与文档数量 ({len(self.documents)}) 不匹配")
                return []
            
            # 获取 top_k（过滤掉分数为 0 或负数的结果）
            # 确保分数是标量值进行比较
            valid_indices = [(i, float(scores[i])) for i in range(len(scores)) if float(scores[i]) > 0]
            if not valid_indices:
                logger.warning("所有 BM25 分数都为 0 或负数")
                return []
            
            # 按分数排序
            valid_indices.sort(key=lambda x: x[1], reverse=True)
            top_indices = [idx for idx, _ in valid_indices[:top_k]]
            
            results = []
            for idx in top_indices:
                if idx >= len(self.documents):
                    logger.warning(f"索引 {idx} 超出文档范围")
                    continue
                
                doc = self.documents[idx]
                metadata = self.doc_metadata[idx] if idx < len(self.doc_metadata) else LogMetadata()
                
                result = RetrievalResult(
                    content=doc.get("text", ""),
                    score=float(scores[idx]),
                    metadata=metadata,
                    source='bm25'
                )
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"BM25 检索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _merge_results(
        self,
        vector_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        合并向量检索和 BM25 检索结果
        使用加权平均的方式合并分数
        """
        # 归一化分数
        vector_results = self._normalize_scores(vector_results)
        bm25_results = self._normalize_scores(bm25_results)
        
        # 使用内容作为去重键
        result_map = {}
        
        # 添加向量检索结果
        for result in vector_results:
            key = result.content[:100]  # 使用前100个字符作为键
            result.score = result.score * self.alpha
            result.source = 'hybrid'
            result_map[key] = result
        
        # 合并 BM25 结果
        for result in bm25_results:
            key = result.content[:100]
            if key in result_map:
                # 已存在，合并分数
                result_map[key].score += result.score * self.beta
            else:
                # 新结果
                result.score = result.score * self.beta
                result.source = 'hybrid'
                result_map[key] = result
        
        return list(result_map.values())
    
    def _normalize_scores(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """归一化分数到 0-1 范围"""
        if not results:
            return results
        
        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score - min_score < 1e-6:
            # 所有分数相同
            for result in results:
                result.score = 1.0
        else:
            for result in results:
                result.score = (result.score - min_score) / (max_score - min_score)
        
        return results
    
    def _apply_filters(
        self,
        results: List[RetrievalResult],
        filters: Dict[str, Any]
    ) -> List[RetrievalResult]:
        """应用元数据过滤"""
        filtered = []
        
        for result in results:
            match = True
            
            # 检查每个过滤条件
            if 'level' in filters:
                if result.metadata.level != filters['level']:
                    match = False
            
            if 'service' in filters:
                if result.metadata.service != filters['service']:
                    match = False
            
            if 'component' in filters:
                if result.metadata.component != filters['component']:
                    match = False
            
            if 'min_severity' in filters:
                if result.metadata.severity_score < filters['min_severity']:
                    match = False
            
            if match:
                filtered.append(result)
        
        return filtered
    
    def _boost_by_severity(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """根据严重程度提升权重"""
        for result in results:
            # 严重性越高，权重提升越大
            severity_boost = 1.0 + result.metadata.severity_score * 0.5
            result.score *= severity_boost
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取检索器统计信息"""
        # 统计各类日志数量
        level_counts = defaultdict(int)
        service_counts = defaultdict(int)
        
        for metadata in self.doc_metadata:
            if metadata.level:
                level_counts[metadata.level] += 1
            if metadata.service:
                service_counts[metadata.service] += 1
        
        return {
            "total_documents": len(self.documents),
            "level_distribution": dict(level_counts),
            "service_distribution": dict(service_counts),
            "alpha": self.alpha,
            "beta": self.beta
        }


class AdvancedLogRetriever(HybridRetriever):
    """
    高级日志检索器
    在混合检索基础上增加时间序列分析和上下文感知
    """
    
    def __init__(
        self,
        vector_index: VectorStoreIndex,
        documents: List[Dict[str, str]],
        alpha: float = 0.5,
        enable_context_expansion: bool = True
    ):
        super().__init__(vector_index, documents, alpha)
        self.enable_context_expansion = enable_context_expansion
        
        # 构建时间索引
        self._build_temporal_index()
    
    def _build_temporal_index(self):
        """构建时间索引（如果日志包含时间信息）"""
        # 这里可以根据实际日志格式提取时间戳
        # 当前示例数据没有时间戳，所以使用文档顺序作为时间代理
        self.temporal_index = list(range(len(self.documents)))
        logger.info("时间索引构建完成")
    
    def retrieve_with_context(
        self,
        query: str,
        top_k: int = 10,
        context_window: int = 2,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        带上下文的检索
        对于检索到的每条日志，同时返回前后的相关日志
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            context_window: 上下文窗口大小（前后各多少条）
            **kwargs: 其他检索参数
        """
        # 首先进行标准检索
        results = self.retrieve(query, top_k, **kwargs)
        
        if not self.enable_context_expansion:
            return results
        
        # 扩展上下文
        expanded_results = []
        seen_contents = set()
        
        for result in results:
            # 添加主结果
            if result.content not in seen_contents:
                expanded_results.append(result)
                seen_contents.add(result.content)
            
            # TODO: 添加上下文日志（需要文档ID映射）
            # 这里需要从原始文档列表中找到相邻的日志
        
        return expanded_results
    
    def analyze_error_patterns(self, top_k: int = 50) -> Dict[str, Any]:
        """
        分析错误模式
        统计最常见的错误类型、服务、组件等
        """
        # 检索所有错误日志
        error_results = self.retrieve(
            query="错误 异常 失败 error exception failure",
            top_k=top_k,
            filters={"level": "ERROR"}
        )
        
        # 统计模式
        error_types = defaultdict(int)
        services = defaultdict(int)
        components = defaultdict(int)
        
        for result in error_results:
            if result.metadata.error_type:
                error_types[result.metadata.error_type] += 1
            if result.metadata.service:
                services[result.metadata.service] += 1
            if result.metadata.component:
                components[result.metadata.component] += 1
        
        return {
            "total_errors": len(error_results),
            "error_types": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)),
            "affected_services": dict(sorted(services.items(), key=lambda x: x[1], reverse=True)),
            "affected_components": dict(sorted(components.items(), key=lambda x: x[1], reverse=True))
        }


if __name__ == "__main__":
    print("混合检索器模块")
    print("需要配合 TopKLogSystem 使用")

