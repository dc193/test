"""LLM通用接口 - 支持多种Provider"""
import os
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from pathlib import Path
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


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI兼容接口（支持OpenAI、Grok、Qwen、本地Ollama等）"""

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
        """转换消息格式"""
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


# Provider配置映射
PROVIDER_CONFIGS = {
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4",
        "type": "openai_compatible"
    },
    "claude": {
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-3-opus-20240229",
        "type": "claude"
    },
    "gemini": {
        "env_key": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "default_model": "gemini-1.5-pro",
        "type": "gemini"
    },
    "grok": {
        "env_key": "XAI_API_KEY",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-beta",
        "type": "openai_compatible"
    },
    "qwen": {
        "env_key": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "type": "openai_compatible"
    },
    "local": {
        "env_key": None,  # 本地不需要key
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama2",
        "type": "openai_compatible"
    },
    "ollama": {
        "env_key": None,
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama2",
        "type": "openai_compatible"
    }
}


def load_config(config_path: str = "config/llm.yaml") -> dict:
    """加载配置文件"""
    # 尝试多个可能的路径
    paths_to_try = [
        config_path,
        Path(__file__).parent.parent.parent / "config" / "llm.yaml",
        "config/llm.yaml"
    ]

    for path in paths_to_try:
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            continue

    # 返回默认配置
    return {"default_provider": "openai", "providers": {}}


def get_api_key(provider_name: str) -> Optional[str]:
    """获取API Key"""
    config = PROVIDER_CONFIGS.get(provider_name, {})
    env_keys = config.get("env_key")

    if env_keys is None:
        return "not-needed"  # 本地模型不需要key

    if isinstance(env_keys, list):
        for key in env_keys:
            value = os.getenv(key)
            if value:
                return value
        return None

    return os.getenv(env_keys)


def get_available_providers() -> list[dict]:
    """获取所有可用的Provider（已配置API Key的）"""
    available = []
    for name, config in PROVIDER_CONFIGS.items():
        api_key = get_api_key(name)
        available.append({
            "name": name,
            "has_key": api_key is not None,
            "default_model": config.get("default_model"),
            "type": config.get("type")
        })
    return available


def create_llm_provider(provider_name: Optional[str] = None, config_path: str = "config/llm.yaml") -> LLMProvider:
    """创建LLM Provider

    Args:
        provider_name: 指定provider名称，如果为None则使用配置文件中的默认值
        config_path: 配置文件路径

    Returns:
        LLMProvider实例

    Raises:
        ValueError: 如果缺少API Key
    """
    config = load_config(config_path)
    provider_name = provider_name or config.get("default_provider", "openai")
    provider_config = config.get("providers", {}).get(provider_name, {})

    # 获取provider的默认配置
    default_config = PROVIDER_CONFIGS.get(provider_name, PROVIDER_CONFIGS["openai"])

    # 获取API Key
    api_key = get_api_key(provider_name)
    if api_key is None:
        env_key = default_config.get("env_key")
        if isinstance(env_key, list):
            env_key = " 或 ".join(env_key)
        raise ValueError(f"请设置 {env_key} 环境变量")

    # 获取配置参数
    base_url = provider_config.get("base_url", default_config.get("base_url"))
    model = provider_config.get("model", default_config.get("default_model"))

    # 根据类型创建Provider
    provider_type = default_config.get("type", "openai_compatible")

    if provider_type == "claude":
        return ClaudeProvider(api_key=api_key, model=model)
    elif provider_type == "gemini":
        return GeminiProvider(api_key=api_key, model=model)
    else:
        # OpenAI兼容接口
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url,
            model=model
        )
