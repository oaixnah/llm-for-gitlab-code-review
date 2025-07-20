import logging
import time
from typing import Dict, List, Optional

from openai import OpenAI as OpenAIClient
from openai.types.chat import ChatCompletion

from config import settings
from utils import parse_response

# 配置日志
logger = logging.getLogger(__name__)


class Service:
    """LLM服务类，提供与大语言模型的交互功能"""

    def __init__(
            self,
            model: str = settings.llm_model,
            api_url: str = settings.llm_api_url,
            api_key: Optional[str] = settings.llm_api_key,
            max_retries: int = 3,
            timeout: float = 30.0,
    ):
        """初始化LLM服务
        
        Args:
            model: 模型名称
            api_url: API地址
            api_key: API密钥
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

        try:
            self.client = OpenAIClient(
                api_key=api_key,
                base_url=api_url,
                timeout=timeout
            )
            logger.info(f"LLM服务初始化成功，模型: {model}")
        except Exception as e:
            logger.error(f"LLM服务初始化失败: {e}")
            raise

    def check(self) -> bool:
        """检查服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        try:
            self.client.models.retrieve(self.model)
            logger.info(f"LLM服务检查通过，模型: {self.model}")
            return True
        except Exception as e:
            logger.error(f"LLM服务检查失败: {e}")
            return False

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict:
        """与LLM进行对话
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 其他参数，如 temperature, max_tokens 等
            
        Returns:
            Dict: 解析后的响应结果，包含duration字段
            
        Raises:
            ValueError: 当响应解析失败时
            Exception: 当API调用失败时
        """
        if not messages:
            raise ValueError("消息列表不能为空")

        # 设置默认参数
        chat_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        chat_params.update(kwargs)

        start_time = time.time()
        last_exception = None

        # 重试机制
        for attempt in range(self.max_retries):
            try:
                logger.info(f"发起LLM请求，尝试次数: {attempt + 1}/{self.max_retries}")

                resp: ChatCompletion = self.client.chat.completions.create(**chat_params)

                if not resp.choices or not resp.choices[0].message.content:
                    raise ValueError("LLM返回空响应")

                duration = time.time() - start_time

                # 记录成功日志
                logger.info(
                    f"LLM请求成功，耗时: {duration:.2f}s, "
                    f"tokens: {resp.usage.total_tokens if resp.usage else 'unknown'}"
                )

                return parse_response(resp.choices[0].message.content, duration)

            except Exception as e:
                last_exception = e
                logger.warning(f"LLM请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")

                # 如果不是最后一次尝试，等待一段时间再重试
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(f"等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)

        # 所有重试都失败了
        duration = time.time() - start_time
        logger.error(f"LLM请求最终失败，总耗时: {duration:.2f}s")
        raise Exception(f"LLM请求失败，已重试{self.max_retries}次: {last_exception}")
