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
    """Google Gemini接口 - 使用新版 google.genai SDK"""

    def __init__(self, api_key: str, model: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_name = model

    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """转换消息格式"""
        system = None
        gemini_contents = []

        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "user":
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                gemini_contents.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })

        return system, gemini_contents

    async def chat(self, messages: list[dict], **kwargs) -> str:
        system, contents = self._convert_messages(messages)

        config = {"max_output_tokens": 4096}
        if system:
            config["system_instruction"] = system

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )
        return response.text

    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        system, contents = self._convert_messages(messages)

        config = {"max_output_tokens": 4096}
        if system:
            config["system_instruction"] = system

        async for chunk in self.client.aio.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=config
        ):
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
        "default_model": "gemini-2.0-flash",
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


def list_models_for_provider(provider_name: str) -> list[dict]:
    """获取指定Provider的可用模型列表

    Returns:
        list of {"id": "model-id", "name": "显示名称", "description": "描述"}
    """
    api_key = get_api_key(provider_name)
    if api_key is None:
        return []

    try:
        if provider_name == "openai":
            return _list_openai_models(api_key)
        elif provider_name == "claude":
            return _list_claude_models()
        elif provider_name == "gemini":
            return _list_gemini_models(api_key)
        elif provider_name in ("local", "ollama"):
            return _list_ollama_models()
        elif provider_name == "grok":
            return _list_grok_models()
        elif provider_name == "qwen":
            return _list_qwen_models()
        else:
            return []
    except Exception as e:
        print(f"获取 {provider_name} 模型列表失败: {e}")
        return []


def _list_openai_models(api_key: str) -> list[dict]:
    """获取OpenAI可用模型"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        models = client.models.list()

        # 过滤出聊天模型
        chat_models = []
        for m in models.data:
            model_id = m.id
            # 只保留GPT系列聊天模型
            if any(x in model_id for x in ['gpt-4', 'gpt-3.5']):
                if 'instruct' not in model_id:  # 排除instruct模型
                    chat_models.append({
                        "id": model_id,
                        "name": model_id,
                        "description": _get_openai_model_desc(model_id)
                    })

        # 按名称排序，把最新的放前面
        chat_models.sort(key=lambda x: x["id"], reverse=True)
        return chat_models
    except Exception as e:
        print(f"获取OpenAI模型列表失败: {e}")
        # 返回默认列表
        return [
            {"id": "gpt-4o", "name": "GPT-4o", "description": "最新最强"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "快速版GPT-4"},
            {"id": "gpt-4", "name": "GPT-4", "description": "标准版"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "快速便宜"},
        ]


def _get_openai_model_desc(model_id: str) -> str:
    """获取OpenAI模型描述"""
    if "gpt-4o" in model_id:
        return "最新多模态模型"
    elif "gpt-4-turbo" in model_id:
        return "快速版GPT-4"
    elif "gpt-4" in model_id:
        return "强大推理能力"
    elif "gpt-3.5" in model_id:
        return "快速便宜"
    return ""


def _list_claude_models() -> list[dict]:
    """获取Claude可用模型 - 从Anthropic API动态获取"""
    api_key = get_api_key("claude")
    if not api_key:
        return []

    try:
        import requests
        resp = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            },
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            models = []
            for m in data.get("data", []):
                model_id = m.get("id", "")
                display_name = m.get("display_name", model_id)
                # 根据模型名生成描述
                desc = _get_claude_model_desc(model_id)
                models.append({
                    "id": model_id,
                    "name": display_name,
                    "description": desc
                })
            # 按模型ID排序，新版本在前
            models.sort(key=lambda x: x["id"], reverse=True)
            return models

    except Exception as e:
        print(f"获取Claude模型列表失败: {e}")

    # API失败时返回默认列表
    return [
        {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "description": "最新最强"},
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "description": "最新平衡"},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "description": "推荐"},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "description": "快速"},
    ]


def _get_claude_model_desc(model_id: str) -> str:
    """根据模型ID生成描述"""
    if "opus-4" in model_id:
        return "最新最强 - 复杂推理"
    elif "sonnet-4" in model_id:
        return "最新 - 平衡性能"
    elif "3-5-sonnet" in model_id:
        return "推荐 - 性价比高"
    elif "3-5-haiku" in model_id:
        return "快速便宜"
    elif "opus" in model_id:
        return "强大推理"
    elif "sonnet" in model_id:
        return "平衡性能"
    elif "haiku" in model_id:
        return "快速便宜"
    return ""


def _list_gemini_models(api_key: str) -> list[dict]:
    """获取Gemini可用模型"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        models = []
        for m in client.models.list():
            model_id = m.name.replace('models/', '')
            # 只保留 gemini 模型
            if 'gemini' in model_id.lower():
                models.append({
                    "id": model_id,
                    "name": m.display_name if hasattr(m, 'display_name') else model_id,
                    "description": m.description[:50] + "..." if hasattr(m, 'description') and m.description and len(m.description) > 50 else (m.description if hasattr(m, 'description') else "")
                })

        return models
    except Exception as e:
        print(f"获取Gemini模型列表失败: {e}")
        # 返回默认列表
        return [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "description": "最新快速版本"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "description": "强大版本"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "description": "快速版本"},
        ]


def _list_ollama_models() -> list[dict]:
    """获取本地Ollama可用模型"""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = []
            for m in data.get("models", []):
                models.append({
                    "id": m["name"],
                    "name": m["name"],
                    "description": f"本地模型 - {m.get('size', 'unknown')} bytes"
                })
            return models
    except Exception as e:
        print(f"获取Ollama模型列表失败: {e}")

    return [{"id": "llama2", "name": "Llama 2", "description": "需要先运行 ollama pull llama2"}]


def _list_grok_models() -> list[dict]:
    """获取Grok可用模型"""
    return [
        {"id": "grok-beta", "name": "Grok Beta", "description": "xAI最新模型"},
    ]


def _list_qwen_models() -> list[dict]:
    """获取通义千问可用模型"""
    return [
        {"id": "qwen-max", "name": "Qwen Max", "description": "最强版本"},
        {"id": "qwen-plus", "name": "Qwen Plus", "description": "增强版"},
        {"id": "qwen-turbo", "name": "Qwen Turbo", "description": "快速版"},
    ]


def get_all_available_models() -> list[dict]:
    """获取所有可用的模型（按Provider分组）

    Returns:
        list of {"provider": "provider_name", "provider_display": "显示名", "models": [...]}
    """
    provider_display_names = {
        "openai": "OpenAI",
        "claude": "Anthropic Claude",
        "gemini": "Google Gemini",
        "grok": "xAI Grok",
        "qwen": "阿里云通义千问",
        "local": "本地 Ollama",
        "ollama": "本地 Ollama"
    }

    result = []
    for provider_name, config in PROVIDER_CONFIGS.items():
        if provider_name == "ollama":  # 避免重复，local和ollama是同一个
            continue

        api_key = get_api_key(provider_name)
        if api_key is None:
            continue

        models = list_models_for_provider(provider_name)
        if models:
            result.append({
                "provider": provider_name,
                "provider_display": provider_display_names.get(provider_name, provider_name),
                "models": models
            })

    return result


def create_llm_provider(
    provider_name: Optional[str] = None,
    model_id: Optional[str] = None,
    config_path: str = "config/llm.yaml"
) -> LLMProvider:
    """创建LLM Provider

    Args:
        provider_name: 指定provider名称，如果为None则使用配置文件中的默认值
        model_id: 指定模型ID，如果为None则使用provider的默认模型
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

    # 模型优先级：参数传入 > 配置文件 > 默认值
    model = model_id or provider_config.get("model", default_config.get("default_model"))

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
