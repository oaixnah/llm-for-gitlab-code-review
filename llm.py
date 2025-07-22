import logging
import time
from typing import Dict, List, Optional

from openai import OpenAI as OpenAIClient
from openai.types.chat import ChatCompletion

from config import settings
from i18n import i18n
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
            logger.info(i18n.t("log.llm_service_init_success", model=model))
        except Exception as e:
            logger.error(i18n.t("log.llm_service_init_failed", error=e))
            raise

    def check(self) -> bool:
        """检查服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        try:
            self.client.models.retrieve(self.model)
            logger.info(i18n.t("log.llm_service_check_passed", model=self.model))
            return True
        except Exception as e:
            logger.error(i18n.t("log.llm_service_check_failed", error=e))
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
            raise ValueError(i18n.t("log.llm_empty_messages"))

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
                logger.info(i18n.t("log.llm_request_start", attempt=attempt + 1, max_retries=self.max_retries))

                resp: ChatCompletion = self.client.chat.completions.create(**chat_params)

                if not resp.choices or not resp.choices[0].message.content:
                    raise ValueError(i18n.t("log.llm_empty_response"))

                duration = time.time() - start_time

                # 记录成功日志
                tokens = resp.usage.total_tokens if resp.usage else 'unknown'
                logger.info(i18n.t("log.llm_request_success", duration=duration, tokens=tokens))

                return parse_response(resp.choices[0].message.content, duration)

            except Exception as e:
                last_exception = e
                logger.warning(i18n.t("log.llm_request_failed", attempt=attempt + 1, max_retries=self.max_retries, error=e))

                # 如果不是最后一次尝试，等待一段时间再重试
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(i18n.t("log.llm_request_retry_wait", wait_time=wait_time))
                    time.sleep(wait_time)

        # 所有重试都失败了
        duration = time.time() - start_time
        logger.error(i18n.t("log.llm_request_final_failed", duration=duration))
        raise Exception(f"LLM请求失败，已重试{self.max_retries}次: {last_exception}")
