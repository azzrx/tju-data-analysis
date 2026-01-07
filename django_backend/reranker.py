"""
重排序模块
对检索结果进行二次排序，提升最相关结果的排名
支持基于规则和基于模型的重排序
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    """重排序结果"""
    content: str
    original_score: float
    rerank_score: float
    final_score: float
    rank: int
    features: Dict[str, float]  # 特征分数


class BaseReranker:
    """基础重排序器"""
    
    def __init__(self):
        logger.info("基础重排序器初始化完成")
    
    def rerank(
        self,
        query: str,
        results: List[Any],
        top_k: Optional[int] = None
    ) -> List[Any]:
        """
        重排序结果
        
        Args:
            query: 查询文本
            results: 检索结果列表
            top_k: 返回前 k 个结果
            
        Returns:
            重排序后的结果列表
        """
        raise NotImplementedError


class RuleBasedReranker(BaseReranker):
    """
    基于规则的重排序器
    使用多种启发式规则对结果进行重排序
    """
    
    def __init__(
        self,
        feature_weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化重排序器
        
        Args:
            feature_weights: 特征权重字典
        """
        super().__init__()
        
        # 默认特征权重
        self.feature_weights = feature_weights or {
            'query_term_coverage': 0.3,      # 查询词覆盖率
            'exact_match': 0.2,               # 精确匹配
            'keyword_density': 0.15,          # 关键词密度
            'severity_score': 0.15,           # 严重性分数
            'length_penalty': 0.1,            # 长度惩罚
            'position_bias': 0.1              # 位置偏差
        }
        
        logger.info(f"基于规则的重排序器初始化完成，特征权重: {self.feature_weights}")
    
    def rerank(
        self,
        query: str,
        results: List[Any],
        top_k: Optional[int] = None
    ) -> List[Any]:
        """重排序结果"""
        if not results:
            return results
        
        logger.info(f"二重排序 {len(results)} 条结果")
        
        # 计算每个结果的特征分数
        scored_results = []
        for idx, result in enumerate(results):
            features = self._extract_features(query, result, idx, len(results))
            rerank_score = self._calculate_score(features)
            
            # 组合原始分数和重排序分数
            original_score = getattr(result, 'score', 0.5)
            final_score = 0.6 * original_score + 0.4 * rerank_score
            
            scored_results.append({
                'result': result,
                'original_score': original_score,
                'rerank_score': rerank_score,
                'final_score': final_score,
                'features': features
            })
        
        # 按最终分数排序
        scored_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 返回排序后的结果
        if top_k:
            scored_results = scored_results[:top_k]
        
        # 更新结果的分数
        reranked = []
        for item in scored_results:
            result = item['result']
            result.score = item['final_score']
            reranked.append(result)
        
        logger.info(f"重排序完成，返回 {len(reranked)} 条结果")
        return reranked
    
    def _extract_features(
        self,
        query: str,
        result: Any,
        position: int,
        total: int
    ) -> Dict[str, float]:
        """提取特征"""
        content = getattr(result, 'content', '')
        
        features = {}
        
        # 1. 查询词覆盖率
        features['query_term_coverage'] = self._calculate_term_coverage(query, content)
        
        # 2. 精确匹配
        features['exact_match'] = self._calculate_exact_match(query, content)
        
        # 3. 关键词密度
        features['keyword_density'] = self._calculate_keyword_density(query, content)
        
        # 4. 严重性分数
        if hasattr(result, 'metadata') and hasattr(result.metadata, 'severity_score'):
            features['severity_score'] = result.metadata.severity_score
        else:
            features['severity_score'] = 0.5
        
        # 5. 长度惩罚（避免过长或过短的结果）
        features['length_penalty'] = self._calculate_length_penalty(content)
        
        # 6. 位置偏差（轻微惩罚靠后的结果）
        features['position_bias'] = 1.0 - (position / total) * 0.2
        
        return features
    
    def _calculate_term_coverage(self, query: str, content: str) -> float:
        """计算查询词覆盖率"""
        query_terms = set(self._tokenize(query))
        content_terms = set(self._tokenize(content))
        
        if not query_terms:
            return 0.0
        
        matched = query_terms & content_terms
        coverage = len(matched) / len(query_terms)
        
        return coverage
    
    def _calculate_exact_match(self, query: str, content: str) -> float:
        """计算精确匹配分数"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        if query_lower in content_lower:
            return 1.0
        
        # 检查部分精确匹配
        query_words = query_lower.split()
        if len(query_words) > 1:
            # 检查 2-gram 匹配
            for i in range(len(query_words) - 1):
                bigram = ' '.join(query_words[i:i+2])
                if bigram in content_lower:
                    return 0.5
        
        return 0.0
    
    def _calculate_keyword_density(self, query: str, content: str) -> float:
        """计算关键词密度"""
        query_terms = self._tokenize(query)
        content_terms = self._tokenize(content)
        
        if not content_terms:
            return 0.0
        
        # 统计查询词在内容中的出现次数
        content_counter = Counter(content_terms)
        total_matches = sum(content_counter[term] for term in query_terms)
        
        # 归一化
        density = total_matches / len(content_terms)
        
        # 限制在 0-1 范围
        return min(density * 10, 1.0)
    
    def _calculate_length_penalty(self, content: str) -> float:
        """计算长度惩罚"""
        length = len(content)
        
        # 理想长度范围：50-500 字符
        if 50 <= length <= 500:
            return 1.0
        elif length < 50:
            return length / 50
        else:  # length > 500
            return max(1.0 - (length - 500) / 1000, 0.5)
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        # 提取中英文词语
        tokens = []
        
        # 中文字符
        chinese = re.findall(r'[\u4e00-\u9fff]+', text)
        tokens.extend(chinese)
        
        # 英文单词（转小写）
        english = re.findall(r'[a-zA-Z]+', text.lower())
        tokens.extend(english)
        
        # 数字
        numbers = re.findall(r'\d+', text)
        tokens.extend(numbers)
        
        return tokens
    
    def _calculate_score(self, features: Dict[str, float]) -> float:
        """根据特征计算最终分数"""
        score = 0.0
        
        for feature_name, feature_value in features.items():
            weight = self.feature_weights.get(feature_name, 0.0)
            score += weight * feature_value
        
        return score


class CrossEncoderReranker(BaseReranker):
    """
    基于交叉编码器的重排序器
    使用预训练模型对 query-document 对进行打分
    
    注：这里提供接口，实际使用需要安装 sentence-transformers
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        super().__init__()
        self.model_name = model_name
        self.model = None
        
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            logger.info(f"交叉编码器重排序器初始化完成: {model_name}")
        except ImportError:
            logger.warning("未安装 sentence-transformers，无法使用交叉编码器重排序")
            logger.info("安装方法: pip install sentence-transformers")
        except Exception as e:
            logger.error(f"加载交叉编码器失败: {e}")
    
    def rerank(
        self,
        query: str,
        results: List[Any],
        top_k: Optional[int] = None
    ) -> List[Any]:
        """使用交叉编码器重排序"""
        if not self.model:
            logger.warning("交叉编码器未初始化，跳过重排序")
            return results
        
        if not results:
            return results
        
        logger.info(f"使用交叉编码器重排序 {len(results)} 条结果")
        
        try:
            # 准备 query-document 对
            pairs = []
            for result in results:
                content = getattr(result, 'content', '')
                pairs.append([query, content])
            
            # 批量打分
            scores = self.model.predict(pairs)
            
            # 组合原始分数和重排序分数
            scored_results = []
            for i, result in enumerate(results):
                original_score = getattr(result, 'score', 0.5)
                rerank_score = float(scores[i])
                final_score = 0.5 * original_score + 0.5 * rerank_score
                
                result.score = final_score
                scored_results.append(result)
            
            # 排序
            scored_results.sort(key=lambda x: x.score, reverse=True)
            
            if top_k:
                scored_results = scored_results[:top_k]
            
            logger.info(f"交叉编码器重排序完成，返回 {len(scored_results)} 条结果")
            return scored_results
            
        except Exception as e:
            logger.error(f"交叉编码器重排序失败: {e}")
            return results


class HybridReranker(BaseReranker):
    """
    混合重排序器
    结合规则和模型两种方法
    """
    
    def __init__(
        self,
        use_cross_encoder: bool = False,
        rule_weight: float = 0.5
    ):
        """
        初始化混合重排序器
        
        Args:
            use_cross_encoder: 是否使用交叉编码器
            rule_weight: 规则分数权重，剩余权重分配给模型分数
        """
        super().__init__()
        
        self.rule_reranker = RuleBasedReranker()
        self.model_reranker = None
        self.rule_weight = rule_weight
        self.model_weight = 1 - rule_weight
        
        if use_cross_encoder:
            self.model_reranker = CrossEncoderReranker()
        
        logger.info(f"混合重排序器初始化完成，rule_weight={rule_weight}")
    
    def rerank(
        self,
        query: str,
        results: List[Any],
        top_k: Optional[int] = None
    ) -> List[Any]:
        """混合重排序"""
        if not results:
            return results
        
        logger.info(f"混合重排序 {len(results)} 条结果")
        
        # 保存原始分数
        original_scores = {id(r): getattr(r, 'score', 0.5) for r in results}
        
        # 1. 规则重排序
        rule_results = self.rule_reranker.rerank(query, results, top_k=None)
        rule_scores = {id(r): r.score for r in rule_results}
        
        # 2. 模型重排序（如果可用）
        if self.model_reranker and self.model_reranker.model:
            model_results = self.model_reranker.rerank(query, results, top_k=None)
            model_scores = {id(r): r.score for r in model_results}
        else:
            model_scores = original_scores
        
        # 3. 组合分数
        for result in results:
            result_id = id(result)
            rule_score = rule_scores.get(result_id, 0.5)
            model_score = model_scores.get(result_id, 0.5)
            
            final_score = (
                self.rule_weight * rule_score +
                self.model_weight * model_score
            )
            result.score = final_score
        
        # 4. 排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        if top_k:
            results = results[:top_k]
        
        logger.info(f"混合重排序完成，返回 {len(results)} 条结果")
        return results


class DiversityReranker(BaseReranker):
    """
    多样性重排序器
    在保证相关性的同时增加结果多样性
    避免返回过多相似的结果
    """
    
    def __init__(
        self,
        base_reranker: Optional[BaseReranker] = None,
        diversity_weight: float = 0.3,
        similarity_threshold: float = 0.8
    ):
        """
        初始化多样性重排序器
        
        Args:
            base_reranker: 基础重排序器
            diversity_weight: 多样性权重
            similarity_threshold: 相似度阈值，超过此值认为结果重复
        """
        super().__init__()
        self.base_reranker = base_reranker or RuleBasedReranker()
        self.diversity_weight = diversity_weight
        self.similarity_threshold = similarity_threshold
        
        logger.info(f"多样性重排序器初始化完成，diversity_weight={diversity_weight}")
    
    def rerank(
        self,
        query: str,
        results: List[Any],
        top_k: Optional[int] = None
    ) -> List[Any]:
        """多样性重排序"""
        if not results:
            return results
        
        # 首先使用基础重排序器
        results = self.base_reranker.rerank(query, results, top_k=None)
        
        # 实现 MMR (Maximal Marginal Relevance) 算法
        selected = []
        remaining = results.copy()
        
        # 选择第一个（最相关的）
        if remaining:
            selected.append(remaining.pop(0))
        
        # 迭代选择后续结果
        target_count = top_k if top_k else len(results)
        while remaining and len(selected) < target_count:
            best_score = -float('inf')
            best_idx = 0
            
            for idx, candidate in enumerate(remaining):
                # 相关性分数
                relevance = candidate.score
                
                # 与已选结果的最大相似度
                max_similarity = max(
                    self._calculate_similarity(candidate, selected_result)
                    for selected_result in selected
                )
                
                # MMR 分数
                mmr_score = (
                    (1 - self.diversity_weight) * relevance -
                    self.diversity_weight * max_similarity
                )
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            selected.append(remaining.pop(best_idx))
        
        logger.info(f"多样性重排序完成，返回 {len(selected)} 条结果")
        return selected
    
    def _calculate_similarity(self, result1: Any, result2: Any) -> float:
        """计算两个结果的相似度"""
        content1 = getattr(result1, 'content', '')
        content2 = getattr(result2, 'content', '')
        
        # 使用 Jaccard 相似度
        tokens1 = set(self._tokenize(content1))
        tokens2 = set(self._tokenize(content2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        return re.findall(r'[\w\u4e00-\u9fff]+', text.lower())


def create_reranker(
    reranker_type: str = "rule",
    **kwargs
) -> BaseReranker:
    """
    工厂函数：创建重排序器
    
    Args:
        reranker_type: 重排序器类型
            - "rule": 基于规则
            - "cross_encoder": 交叉编码器
            - "hybrid": 混合
            - "diversity": 多样性
        **kwargs: 其他参数
    
    Returns:
        重排序器实例
    """
    if reranker_type == "rule":
        return RuleBasedReranker(**kwargs)
    elif reranker_type == "cross_encoder":
        return CrossEncoderReranker(**kwargs)
    elif reranker_type == "hybrid":
        return HybridReranker(**kwargs)
    elif reranker_type == "diversity":
        return DiversityReranker(**kwargs)
    else:
        logger.warning(f"未知的重排序器类型: {reranker_type}，使用默认的规则重排序器")
        return RuleBasedReranker()


if __name__ == "__main__":
    print("=== 重排序器测试 ===")
    
    # 创建测试数据
    from dataclasses import dataclass
    
    @dataclass
    class MockResult:
        content: str
        score: float
    
    query = "数据库连接错误"
    results = [
        MockResult("数据库连接池耗尽，无法获取连接", 0.9),
        MockResult("系统启动正常", 0.3),
        MockResult("MySQL连接超时", 0.85),
        MockResult("认证服务异常", 0.5),
        MockResult("数据库连接失败，错误代码：1045", 0.88),
    ]
    
    # 测试规则重排序
    print("\n1. 规则重排序:")
    reranker = RuleBasedReranker()
    reranked = reranker.rerank(query, results)
    for i, r in enumerate(reranked):
        print(f"  #{i+1}: {r.content[:40]}, score={r.score:.3f}")
    
    # 测试多样性重排序
    print("\n2. 多样性重排序:")
    div_reranker = DiversityReranker()
    diverse_results = div_reranker.rerank(query, results.copy())
    for i, r in enumerate(diverse_results):
        print(f"  #{i+1}: {r.content[:40]}, score={r.score:.3f}")

