"""LLM通用接口 - 支持多种Provider"""
import os
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
import yaml


class LLMProvider(ABC):
    """LLM提供者基类"""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """普通对话"""
        pass

    @abstractmethod
    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """流式对话"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI兼容接口（支持OpenAI、Azure、本地Ollama等）"""

    def __init__(self, api_key: str, base_url: str, model: str):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content

    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            **kwargs
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class ClaudeProvider(LLMProvider):
    """Claude接口"""

    def __init__(self, api_key: str, model: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # 转换消息格式（OpenAI格式 -> Claude格式）
        system = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system or "",
            messages=claude_messages,
            **kwargs
        )
        return response.content[0].text

    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        system = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            system=system or "",
            messages=claude_messages,
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text


class GeminiProvider(LLMProvider):
    """Google Gemini接口"""

    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name = model

    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """转换消息格式（OpenAI格式 -> Gemini格式）"""
        system = None
        gemini_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({
                    "role": "user",
                    "parts": [msg["content"]]
                })
            elif msg["role"] == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [msg["content"]]
                })

        return system, gemini_messages

    async def chat(self, messages: list[dict], **kwargs) -> str:
        import google.generativeai as genai

        system, gemini_messages = self._convert_messages(messages)

        # 如果有system prompt，创建带system instruction的模型
        if system:
            model = genai.GenerativeModel(self.model_name, system_instruction=system)
        else:
            model = self.model

        response = await model.generate_content_async(
            gemini_messages,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=4096,
            )
        )
        return response.text

    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        import google.generativeai as genai

        system, gemini_messages = self._convert_messages(messages)

        if system:
            model = genai.GenerativeModel(self.model_name, system_instruction=system)
        else:
            model = self.model

        response = await model.generate_content_async(
            gemini_messages,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=4096,
            ),
            stream=True
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text


def load_config(config_path: str = "config/llm.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def create_llm_provider(provider_name: Optional[str] = None, config_path: str = "config/llm.yaml") -> LLMProvider:
    """创建LLM Provider"""
    config = load_config(config_path)
    provider_name = provider_name or config.get("default_provider", "openai")
    provider_config = config["providers"].get(provider_name, {})

    if provider_name == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("请设置 ANTHROPIC_API_KEY 环境变量")
        return ClaudeProvider(
            api_key=api_key,
            model=provider_config.get("model", "claude-3-opus-20240229")
        )
    elif provider_name == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("请设置 GEMINI_API_KEY 或 GOOGLE_API_KEY 环境变量")
        return GeminiProvider(
            api_key=api_key,
            model=provider_config.get("model", "gemini-1.5-pro")
        )
    else:
        # OpenAI或兼容接口
        api_key = os.getenv("OPENAI_API_KEY", "not-needed")  # 本地模型可能不需要
        return OpenAIProvider(
            api_key=api_key,
            base_url=provider_config.get("base_url", "https://api.openai.com/v1"),
            model=provider_config.get("model", "gpt-4")
        )
