"""
意图分类器配置文件
"""

# Ollama轻量级模型配置
INTENT_MODELS = {
    # 超轻量级模型（推荐）
    "qwen2.5:0.5b": {
        "model_name": "qwen2.5:0.5b",
        "size_mb": 500,  # ~0.5GB
        "languages": ["zh", "en", "多语言"],
        "description": "Qwen2.5超轻量级版本，延迟极低，支持中英文",
        "latency": "< 50ms",
        "recommended": True
    },
    
    "llama3.2:1b": {
        "model_name": "llama3.2:1b", 
        "size_mb": 1300,  # ~1.3GB
        "languages": ["zh", "en", "多语言"],
        "description": "Llama3.2轻量级版本，快速且准确"
    },
    
    "gemma2:2b": {
        "model_name": "gemma2:2b",
        "size_mb": 1600,  # ~1.6GB
        "languages": ["zh", "en", "多语言"],
        "description": "Gemma2轻量级版本，平衡性能和速度"
    },
    
    "phi3:mini": {
        "model_name": "phi3:mini",
        "size_mb": 2300,  # ~2.3GB
        "languages": ["zh", "en", "多语言"],
        "description": "Phi3 Mini版本，性能较好"
    }
}

# 默认配置 - 使用Ollama超轻量级模型
DEFAULT_MODEL = "qwen2.5:0.5b"  # 超轻量级，延迟极低

# 意图分类阈值配置
CONFIDENCE_THRESHOLDS = {
    "high_confidence": 0.8,    # 高置信度阈值
    "medium_confidence": 0.6,  # 中等置信度阈值
    "low_confidence": 0.4      # 低置信度阈值
}

# RAG决策配置
RAG_DECISION_CONFIG = {
    "always_rag_intents": ["log_analysis", "technical_help"],
    "never_rag_intents": ["greeting", "summary_request"],
    "conditional_rag_intents": ["general_qa", "follow_up"],
    "min_confidence_for_rag": 0.6
}

# 缓存配置
CACHE_CONFIG = {
    "max_cache_size": 1000,
    "cache_ttl_seconds": 3600,  # 1小时
    "enable_persistent_cache": False
}

# 性能配置
PERFORMANCE_CONFIG = {
    "max_sequence_length": 128,  # 最大输入长度
    "batch_size": 1,            # 批处理大小
    "use_gpu": True,            # 是否使用GPU
    "num_threads": 4            # CPU线程数
}

# 模型量化配置（进一步压缩模型）
QUANTIZATION_CONFIG = {
    "enable_quantization": True,
    "quantization_type": "dynamic",  # dynamic, static, qat
    "target_size_mb": 100           # 目标模型大小
}

def get_model_config(model_key: str = None) -> dict:
    """获取模型配置"""
    if model_key is None:
        model_key = DEFAULT_MODEL
    
    if model_key not in INTENT_MODELS:
        raise ValueError(f"未知的模型配置: {model_key}")
    
    return INTENT_MODELS[model_key]

def get_recommended_model() -> str:
    """获取推荐的模型"""
    return DEFAULT_MODEL

def list_available_models() -> dict:
    """列出所有可用模型"""
    return INTENT_MODELS
