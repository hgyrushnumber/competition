"""
Ollama客户端
"""
import ollama
from typing import Optional, List, Dict, Any, AsyncIterator
import asyncio
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Ollama客户端"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:latest",
        timeout: int = 120
    ):
        """
        初始化Ollama客户端
        
        Args:
            base_url: Ollama服务地址
            model: 模型名称
            timeout: 超时时间（秒）
        """
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.client = ollama.Client(host=base_url, timeout=timeout)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        同步聊天调用
        
        Args:
            messages: 消息列表，格式：[{"role": "user", "content": "..."}]
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            响应内容
        """
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return response
            else:
                return response.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        异步聊天调用
        
        Args:
            messages: 消息列表
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            响应内容
        """
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.chat(messages, stream=stream, **kwargs)
            )
            return response
        except Exception as e:
            logger.error(f"Ollama async chat error: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        生成文本（简化接口）
        
        Args:
            prompt: 提示词
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, stream=stream, **kwargs)
    
    async def generate_async(
        self,
        prompt: str,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        异步生成文本
        
        Args:
            prompt: 提示词
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.chat_async(messages, stream=stream, **kwargs)
    
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式聊天（异步生成器）
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            文本片段
        """
        async def _stream():
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    **kwargs
                )
            )
            
            for chunk in response:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
        
        return _stream()
    
    def check_connection(self) -> bool:
        """
        检查Ollama连接
        
        Returns:
            是否连接成功
        """
        try:
            # 尝试列出模型
            models = self.client.list()
            logger.info(f"Ollama connected, available models: {len(models.get('models', []))}")
            return True
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """
        列出可用模型
        
        Returns:
            模型名称列表
        """
        try:
            models = self.client.list()
            return [model["name"] for model in models.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

