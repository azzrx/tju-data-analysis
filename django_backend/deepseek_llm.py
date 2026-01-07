"""
DeepSeek LLM 包装类
兼容 llama-index 的 LLM 接口，使用 DeepSeek API
"""
import logging
import requests
from typing import Any, Dict, Optional, Sequence
from llama_index.core.llms import (
    LLM,
    ChatMessage,
    ChatResponse,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
)
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
from deepseek_config import get_api_key, DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL, DEEPSEEK_API_PARAMS, DEEPSEEK_TIMEOUT

logger = logging.getLogger(__name__)


class DeepSeekLLM(LLM):
    """
    DeepSeek LLM 包装类，兼容 llama-index 接口
    """
    
    def __init__(
        self,
        model: str = DEFAULT_DEEPSEEK_MODEL,
        api_key: Optional[str] = None,
        base_url: str = DEEPSEEK_BASE_URL,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: int = DEEPSEEK_TIMEOUT,
        **kwargs: Any,
    ) -> None:
        """
        初始化 DeepSeek LLM
        
        Args:
            model: 模型名称
            api_key: API 密钥（如果不提供，从配置文件读取）
            base_url: API 基础地址
            temperature: 温度参数
            max_tokens: 最大输出长度
            timeout: 超时时间
        """
        super().__init__()
        self._model = model
        self._api_key = api_key or get_api_key()
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        
        if not self._api_key:
            raise ValueError(
                "未找到 DeepSeek API Key！请通过以下方式之一设置：\n"
                "1. 设置环境变量: export DEEPSEEK_API_KEY='your-api-key'\n"
                "2. 创建 .env 文件，添加: DEEPSEEK_API_KEY=your-api-key\n"
                "3. 在初始化时传入: DeepSeekLLM(api_key='your-api-key')"
            )
        
        logger.info(f"✅ DeepSeek LLM 初始化成功 - 模型: {self._model}")
    
    @property
    def metadata(self) -> LLMMetadata:
        """返回 LLM 元数据"""
        return LLMMetadata(
            context_window=32768,  # DeepSeek 上下文窗口
            num_output=self._max_tokens,
            model_name=self._model,
        )
    
    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        """
        同步聊天接口
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            ChatResponse 对象
        """
        # 转换消息格式
        api_messages = []
        for msg in messages:
            api_messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        
        # 调用 DeepSeek API
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self._model,
            "messages": api_messages,
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "stream": False,
        }
        
        try:
            logger.info(f"🚀 调用 DeepSeek API - 模型: {self._model}")
            response = requests.post(
                f"{self._base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            logger.info(f"✅ DeepSeek API 响应成功 - 长度: {len(content)} 字符")
            
            return ChatResponse(
                message=ChatMessage(role="assistant", content=content),
                raw=result,
            )
        
        except requests.exceptions.Timeout:
            logger.error(f"❌ DeepSeek API 超时 - 超时时间: {self._timeout}秒")
            raise Exception(f"DeepSeek API 调用超时（{self._timeout}秒）")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ DeepSeek API 请求失败: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"错误详情: {e.response.text}")
            raise Exception(f"DeepSeek API 调用失败: {e}")
    
    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """
        同步补全接口（通过 chat 实现）
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            CompletionResponse 对象
        """
        messages = [ChatMessage(role="user", content=prompt)]
        chat_response = self.chat(messages, **kwargs)
        
        return CompletionResponse(
            text=chat_response.message.content,
            raw=chat_response.raw,
        )
    
    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        """流式聊天"""
        # 转换消息格式
        api_messages = []
        for msg in messages:
            api_messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        
        # 调用 DeepSeek API (流式)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self._model,
            "messages": api_messages,
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "stream": True,  # 开启流式
        }
        
        try:
            logger.info(f"🚀 调用 DeepSeek API (流式) - 模型: {self._model}")
            response = requests.post(
                f"{self._base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self._timeout,
                stream=True,  # 流式响应
            )
            response.raise_for_status()
            
            # 生成器：逐块返回
            def gen():
                full_text = ""
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            data_text = line_text[6:]  # 去掉 'data: '
                            if data_text == '[DONE]':
                                break
                            try:
                                import json
                                data = json.loads(data_text)
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    full_text += content
                                    yield ChatResponse(
                                        message=ChatMessage(role="assistant", content=full_text),
                                        delta=content,
                                        raw=data,
                                    )
                            except:
                                continue
            
            return gen()
        
        except requests.exceptions.Timeout:
            logger.error(f"❌ DeepSeek API 超时 - 超时时间: {self._timeout}秒")
            raise Exception(f"DeepSeek API 调用超时（{self._timeout}秒）")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ DeepSeek API 请求失败: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"错误详情: {e.response.text}")
            raise Exception(f"DeepSeek API 调用失败: {e}")
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        """流式补全（暂不支持）"""
        raise NotImplementedError("DeepSeek 流式补全暂未实现")
    
    async def achat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponse:
        """异步聊天（暂不支持，调用同步版本）"""
        return self.chat(messages, **kwargs)
    
    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """异步补全（暂不支持，调用同步版本）"""
        return self.complete(prompt, **kwargs)
    
    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        """异步流式聊天（暂不支持）"""
        raise NotImplementedError("DeepSeek 异步流式聊天暂未实现")
    
    async def astream_complete(
        self, prompt: str, **kwargs: Any
    ) -> CompletionResponseGen:
        """异步流式补全（暂不支持）"""
        raise NotImplementedError("DeepSeek 异步流式补全暂未实现")


def create_deepseek_embedding(model_name: str = "nomic-embed-text", **kwargs):
    """
    创建 Embedding 模型
    注意：DeepSeek 目前不提供 Embedding API，这里使用本地 Ollama
    
    返回 OllamaEmbedding 实例（兼容 llama-index）
    """
    from llama_index.embeddings.ollama import OllamaEmbedding
    
    logger.warning(
        "⚠️  DeepSeek 暂不提供 Embedding API，Embedding 功能仍使用 Ollama\n"
        f"   使用模型: {model_name}\n"
        "   请确保 Ollama 服务正在运行: ollama serve"
    )
    
    return OllamaEmbedding(
        model_name=model_name,
        request_timeout=300.0
    )

