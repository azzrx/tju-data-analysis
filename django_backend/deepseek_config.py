"""
DeepSeek API 配置文件
用于存储 DeepSeek API 密钥和相关配置
"""
import os
from pathlib import Path

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # 从环境变量读取，默认为空
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")  # API 基础地址

# DeepSeek 模型配置
DEEPSEEK_MODELS = {
    "chat": "deepseek-chat",  # 通用对话模型
    "coder": "deepseek-coder",  # 代码专用模型
}

# 默认使用的模型
DEFAULT_DEEPSEEK_MODEL = DEEPSEEK_MODELS["chat"]

# API 调用参数
DEEPSEEK_API_PARAMS = {
    "temperature": 0.1,  # 较低的温度确保稳定输出
    "max_tokens": 4096,  # 最大输出长度
    "top_p": 0.95,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
}

# 超时设置
DEEPSEEK_TIMEOUT = 60  # API 调用超时时间（秒）

def get_api_key() -> str:
    """
    获取 DeepSeek API Key
    优先级：
    1. 环境变量 DEEPSEEK_API_KEY
    2. .env 文件
    3. 配置文件中的硬编码值（不推荐）
    """
    # 尝试从环境变量获取
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    if api_key:
        return api_key
    
    # 尝试从 .env 文件读取
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEEPSEEK_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        return api_key
        except Exception as e:
            print(f"⚠️  读取 .env 文件失败: {e}")
    
    # 如果都没有找到，返回空字符串
    if not api_key:
        print("⚠️  未找到 DeepSeek API Key！")
        print("请通过以下方式之一设置 API Key：")
        print("1. 设置环境变量: export DEEPSEEK_API_KEY='your-api-key'")
        print("2. 在 django_backend 目录创建 .env 文件，添加: DEEPSEEK_API_KEY=your-api-key")
    
    return api_key

def validate_api_key() -> bool:
    """验证 API Key 是否已配置"""
    api_key = get_api_key()
    return bool(api_key and len(api_key) > 10)

