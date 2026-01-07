#!/usr/bin/env python3
"""
高级 RAG 系统快速测试脚本
用于验证系统是否正常工作
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from topklogsystem import TopKLogSystem
from model_config import CURRENT_CONFIG


def test_basic_rag():
    """测试基础 RAG（不启用高级功能）"""
    print("\n" + "="*60)
    print("测试 1: 基础 RAG（原始模式）")
    print("="*60)
    
    try:
        system = TopKLogSystem(
            log_path="./data/log",
            llm=CURRENT_CONFIG['llm'],
            embedding_model=CURRENT_CONFIG['embedding_model'],
            use_advanced_rag=False  # 禁用高级 RAG
        )
        
        query = "数据库连接错误"
        print(f"\n查询: {query}")
        
        result = system.query(query, query_type="analysis")
        
        print(f"\n✓ 基础 RAG 测试成功")
        print(f"检索到 {result['retrieval_stats']} 条日志")
        print(f"\n回答预览: {result['response'][:200]}...")
        return True
    except Exception as e:
        print(f"\n✗ 基础 RAG 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_advanced_rag():
    """测试高级 RAG"""
    print("\n" + "="*60)
    print("测试 2: 高级 RAG（混合检索 + 重排序 + 查询优化）")
    print("="*60)
    
    try:
        system = TopKLogSystem(
            log_path="./data/log",
            llm=CURRENT_CONFIG['llm'],
            embedding_model=CURRENT_CONFIG['embedding_model'],
            use_advanced_rag=True,
            retrieval_mode="hybrid",
            enable_reranking=True,
            enable_query_optimization=True
        )
        
        if not system.use_advanced_rag:
            print("\n⚠ 高级 RAG 未启用，可能是依赖未安装")
            print("请运行: pip install rank-bm25")
            return False
        
        query = "数据库连接错误怎么解决？"
        print(f"\n查询: {query}")
        
        result = system.query(query, query_type="analysis")
        
        print(f"\n✓ 高级 RAG 测试成功")
        print(f"检索到 {result['retrieval_stats']} 条日志")
        print(f"\n回答预览: {result['response'][:200]}...")
        return True
    except Exception as e:
        print(f"\n✗ 高级 RAG 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retrieval_with_filters():
    """测试带过滤条件的检索"""
    print("\n" + "="*60)
    print("测试 3: 带过滤条件的检索")
    print("="*60)
    
    try:
        system = TopKLogSystem(
            log_path="./data/log",
            llm=CURRENT_CONFIG['llm'],
            embedding_model=CURRENT_CONFIG['embedding_model'],
            use_advanced_rag=True
        )
        
        if not system.use_advanced_rag:
            print("\n⚠ 跳过此测试（高级 RAG 未启用）")
            return False
        
        query = "认证错误"
        filters = {"level": "ERROR"}
        
        print(f"\n查询: {query}")
        print(f"过滤条件: {filters}")
        
        logs = system.retrieve_logs(query, top_k=5, filters=filters)
        
        print(f"\n✓ 检索测试成功")
        print(f"找到 {len(logs)} 条结果")
        
        for i, log in enumerate(logs, 1):
            print(f"\n结果 {i}:")
            print(f"  服务: {log['metadata'].get('service', 'N/A')}")
            print(f"  级别: {log['metadata'].get('level', 'N/A')}")
            print(f"  分数: {log['score']:.3f}")
            print(f"  内容: {log['content'][:80]}...")
        
        return True
    except Exception as e:
        print(f"\n✗ 检索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_optimizer():
    """测试查询优化器"""
    print("\n" + "="*60)
    print("测试 4: 查询优化器")
    print("="*60)
    
    try:
        from query_optimizer import QueryOptimizer
        
        optimizer = QueryOptimizer()
        
        test_queries = [
            "数据库连接错误怎么解决？",
            "系统性能很慢",
            "查看认证失败的日志"
        ]
        
        for query in test_queries:
            print(f"\n原始查询: {query}")
            optimized = optimizer.optimize(query)
            
            print(f"  意图: {optimized.intent}")
            print(f"  扩展术语: {optimized.expanded_terms[:3]}")
            print(f"  建议过滤器: {optimizer.suggest_filters(query)}")
        
        print("\n✓ 查询优化器测试成功")
        return True
    except Exception as e:
        print(f"\n✗ 查询优化器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_pattern_analysis():
    """测试错误模式分析"""
    print("\n" + "="*60)
    print("测试 5: 错误模式分析")
    print("="*60)
    
    try:
        system = TopKLogSystem(
            log_path="./data/log",
            llm=CURRENT_CONFIG['llm'],
            embedding_model=CURRENT_CONFIG['embedding_model'],
            use_advanced_rag=True
        )
        
        if not system.hybrid_retriever:
            print("\n⚠ 跳过此测试（混合检索器未初始化）")
            return False
        
        print("\n分析错误模式...")
        patterns = system.hybrid_retriever.analyze_error_patterns(top_k=50)
        
        print(f"\n✓ 错误模式分析成功")
        print(f"\n总错误数: {patterns['total_errors']}")
        
        print(f"\n错误类型分布（前 5 名）:")
        for error_type, count in list(patterns['error_types'].items())[:5]:
            print(f"  {error_type}: {count}")
        
        print(f"\n受影响的服务（前 5 名）:")
        for service, count in list(patterns['affected_services'].items())[:5]:
            print(f"  {service}: {count}")
        
        return True
    except Exception as e:
        print(f"\n✗ 错误模式分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("高级 RAG 系统测试套件")
    print("="*60)
    
    tests = [
        ("基础 RAG", test_basic_rag),
        ("高级 RAG", test_advanced_rag),
        ("带过滤的检索", test_retrieval_with_filters),
        ("查询优化器", test_query_optimizer),
        ("错误模式分析", test_error_pattern_analysis),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n测试 '{test_name}' 发生异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠ {total - passed} 个测试失败")
        print("请检查错误信息并修复问题")


if __name__ == "__main__":
    main()

