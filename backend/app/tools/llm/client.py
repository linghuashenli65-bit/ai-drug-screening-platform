"""
LLM 客户端

使用 requests 库直接调用 OpenAI 兼容 API，支持：
- 主模型 + 备用模型自动切换
- 指数退避重试
- Prompt 注入检测
- 请求/响应日志记录

注意：不使用 openai SDK，因为其 httpx 传输层在 uvicorn 事件循环中
存在 DNS/连接问题。直接使用 requests（urllib3）+ asyncio.to_thread 替代。
"""

import asyncio
from typing import Any, Optional

import requests as http_requests

from app.core.config import get_settings
from app.core.exceptions import (
    LLMModelError,
    LLMTimeoutError,
    PromptInjectionError,
)
from app.core.logger import get_logger
from app.core.security import sanitize_prompt
from app.tools.base import BaseTool, ToolResult

settings = get_settings()
logger = get_logger("tool.llm_client")


class LLMClient(BaseTool):
    """OpenAI 兼容 LLM 客户端

    使用 requests 库直接发送 HTTP 请求，支持多模型、自动回退、重试机制。
    """

    name = "llm_client"
    description = "调用 OpenAI/LLM API 进行文本生成和分析"

    def __init__(self):
        self.primary_model = settings.OPENAI_MODEL
        self.fallback_model = settings.LLM_FALLBACK_MODEL
        self.max_retries = settings.LLM_MAX_RETRIES
        self.timeout = settings.LLM_TIMEOUT
        self._base_url = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._api_key = settings.OPENAI_API_KEY

    def _call_api(
        self, model: str, messages: list[dict], temperature: float, max_tokens: int
    ) -> dict:
        """同步调用 LLM API（在 asyncio.to_thread 中运行）"""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = http_requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        use_fallback: bool = True,
    ) -> ToolResult:
        """调用 LLM Chat Completion

        Args:
            messages: 消息列表 [{role, content}, ...]
            model: 模型名称（默认使用配置值）
            temperature: 温度参数 (0-1)
            max_tokens: 最大输出 token 数
            use_fallback: 主模型失败时是否切换到备用模型

        Returns:
            ToolResult 包含 LLM 响应文本

        Raises:
            PromptInjectionError: 检测到 Prompt 注入
            LLMTimeoutError: 所有重试超时
            LLMModelError: 模型调用失败
        """
        model = model or self.primary_model

        # Prompt 注入检测
        for msg in messages:
            if msg.get("role") == "user":
                sanitize_prompt(msg.get("content", ""))

        if not self._api_key:
            logger.warning("OpenAI API Key 未配置，返回模拟响应")
            return ToolResult.success(
                data={
                    "content": self._mock_response(messages),
                    "model": model,
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "mock": True,
                }
            )

        models_to_try = [model]
        if use_fallback and model != self.fallback_model:
            models_to_try.append(self.fallback_model)

        last_error = None

        for attempt_model in models_to_try:
            for retry in range(self.max_retries):
                try:
                    logger.info(f"LLM 调用: model={attempt_model}, retry={retry}")

                    data = await asyncio.to_thread(
                        self._call_api, attempt_model, messages, temperature, max_tokens
                    )

                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})

                    logger.info(
                        f"LLM 调用成功: model={attempt_model}, "
                        f"tokens={usage.get('total_tokens', 0)}"
                    )

                    return ToolResult.success(
                        data={
                            "content": content,
                            "model": attempt_model,
                            "usage": {
                                "prompt_tokens": usage.get("prompt_tokens", 0),
                                "completion_tokens": usage.get("completion_tokens", 0),
                                "total_tokens": usage.get("total_tokens", 0),
                            },
                        }
                    )

                except http_requests.exceptions.Timeout as e:
                    last_error = e
                    if retry < self.max_retries - 1:
                        backoff = settings.TASK_RETRY_BACKOFF_BASE ** retry
                        logger.warning(f"LLM 超时，{backoff}s 后重试...")
                        await asyncio.sleep(backoff)
                    continue

                except http_requests.exceptions.ConnectionError as e:
                    last_error = e
                    if retry < self.max_retries - 1:
                        backoff = settings.TASK_RETRY_BACKOFF_BASE ** (retry + 1)
                        logger.warning(f"LLM 连接失败，{backoff}s 后重试...")
                        await asyncio.sleep(backoff)
                    continue

                except http_requests.exceptions.HTTPError as e:
                    last_error = e
                    status = e.response.status_code if e.response is not None else 0
                    if status == 429:
                        backoff = 2 ** (retry + 1)
                        logger.warning(f"LLM 速率限制，{backoff}s 后重试...")
                        await asyncio.sleep(backoff)
                        continue
                    logger.error(f"LLM API 错误 (HTTP {status}): {e}")
                    break  # 非重试型错误，切换到备用模型

                except Exception as e:
                    last_error = e
                    logger.error(f"LLM 调用异常: {e}")
                    break

            # 尝试备用模型
            if attempt_model == self.primary_model and use_fallback:
                logger.warning(f"主模型 {self.primary_model} 失败，切换到备用模型 {self.fallback_model}")
                continue

        # 所有重试都失败
        if isinstance(last_error, http_requests.exceptions.Timeout):
            raise LLMTimeoutError(message="LLM 调用超时，所有重试均失败")
        raise LLMModelError(message=f"LLM 调用失败: {last_error}")

    def _mock_response(self, messages: list[dict]) -> str:
        """无 API Key 时的模拟响应（仅用于开发环境）"""
        last_user_msg = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_user_msg = msg["content"]
                break

        return (
            "[开发模式] 这是 LLM 模拟响应。"
            f"收到 {len(messages)} 条消息，最后用户输入长度: {len(last_user_msg)} 字符。"
            "配置 OPENAI_API_KEY 以启用真实 LLM 调用。"
        )
