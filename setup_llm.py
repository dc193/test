#!/usr/bin/env python3
"""LLM 配置向导

功能：
1. 检测已配置的 API Key
2. 获取各 Provider 可用模型列表
3. 让用户选择或自动推荐
4. 保存配置到 config/llm.yaml
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


def check_api_keys():
    """检查已配置的 API Key"""
    keys = {
        "gemini": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        "claude": os.getenv("ANTHROPIC_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY"),
        "grok": os.getenv("XAI_API_KEY"),
        "qwen": os.getenv("DASHSCOPE_API_KEY"),
    }

    available = {k: v for k, v in keys.items() if v}
    return available


def fetch_gemini_models(api_key: str) -> list[dict]:
    """获取 Gemini 可用模型"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        models = []
        for m in client.models.list():
            model_id = m.name.replace('models/', '')
            # 只保留 gemini 模型，排除 embedding 等
            if 'gemini' in model_id.lower() and 'embedding' not in model_id.lower():
                models.append({
                    "id": model_id,
                    "name": getattr(m, 'display_name', model_id),
                    "description": getattr(m, 'description', '')[:80] if hasattr(m, 'description') else ''
                })

        # 按版本排序，新版本在前
        models.sort(key=lambda x: x['id'], reverse=True)
        return models
    except Exception as e:
        print(f"  获取模型失败: {e}")
        return []


def fetch_claude_models(api_key: str) -> list[dict]:
    """获取 Claude 可用模型"""
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
                models.append({
                    "id": m.get("id", ""),
                    "name": m.get("display_name", m.get("id", "")),
                    "description": ""
                })
            models.sort(key=lambda x: x['id'], reverse=True)
            return models
    except Exception as e:
        print(f"  获取模型失败: {e}")
    return []


def fetch_openai_models(api_key: str) -> list[dict]:
    """获取 OpenAI 可用模型"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        models = []
        for m in client.models.list():
            if any(x in m.id for x in ['gpt-4', 'gpt-3.5']) and 'instruct' not in m.id:
                models.append({
                    "id": m.id,
                    "name": m.id,
                    "description": ""
                })

        models.sort(key=lambda x: x['id'], reverse=True)
        return models
    except Exception as e:
        print(f"  获取模型失败: {e}")
    return []


def recommend_model(models: list[dict], provider: str) -> str:
    """智能推荐模型"""
    if not models:
        return None

    # 推荐策略
    preferences = {
        "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0", "gemini-1.5-pro"],
        "claude": ["claude-sonnet-4", "claude-3-5-sonnet", "claude-3-sonnet", "claude-3-haiku"],
        "openai": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    }

    prefs = preferences.get(provider, [])

    for pref in prefs:
        for m in models:
            if pref in m['id'].lower():
                return m['id']

    # 没有匹配，返回第一个
    return models[0]['id']


def save_config(provider: str, model: str):
    """保存配置"""
    import yaml

    config_path = Path("config/llm.yaml")

    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {"default_provider": provider, "providers": {}}

    config["default_provider"] = provider
    if "providers" not in config:
        config["providers"] = {}
    if provider not in config["providers"]:
        config["providers"][provider] = {}
    config["providers"][provider]["model"] = model

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print(f"\n配置已保存到 {config_path}")


def interactive_setup():
    """交互式配置"""
    print("=" * 60)
    print("  LLM 配置向导")
    print("=" * 60)

    # 1. 检查 API Keys
    print("\n[1] 检测 API Key...")
    available_keys = check_api_keys()

    if not available_keys:
        print("\n未检测到任何 API Key。请设置以下环境变量之一：")
        print("  - GEMINI_API_KEY 或 GOOGLE_API_KEY")
        print("  - ANTHROPIC_API_KEY")
        print("  - OPENAI_API_KEY")
        print("\n示例: export GEMINI_API_KEY='your-key'")
        return

    print(f"  检测到 {len(available_keys)} 个可用 Provider:")
    for provider in available_keys:
        key_preview = available_keys[provider][:12] + "..."
        print(f"    - {provider} ({key_preview})")

    # 2. 选择 Provider
    providers = list(available_keys.keys())
    if len(providers) == 1:
        selected_provider = providers[0]
        print(f"\n自动选择: {selected_provider}")
    else:
        print(f"\n[2] 选择 Provider:")
        for i, p in enumerate(providers, 1):
            print(f"    {i}. {p}")

        while True:
            choice = input(f"\n请选择 (1-{len(providers)}, 默认 1): ").strip() or "1"
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(providers):
                    selected_provider = providers[idx]
                    break
            except ValueError:
                pass
            print("  无效选择，请重试")

    # 3. 获取可用模型
    print(f"\n[3] 获取 {selected_provider} 可用模型...")
    api_key = available_keys[selected_provider]

    if selected_provider == "gemini":
        models = fetch_gemini_models(api_key)
    elif selected_provider == "claude":
        models = fetch_claude_models(api_key)
    elif selected_provider == "openai":
        models = fetch_openai_models(api_key)
    else:
        models = []

    if not models:
        print("  无法获取模型列表，请检查 API Key 是否有效")
        return

    print(f"  找到 {len(models)} 个可用模型")

    # 4. 推荐或选择模型
    recommended = recommend_model(models, selected_provider)

    print(f"\n[4] 选择模型:")
    print(f"  推荐: {recommended}")
    print(f"\n  可用模型列表:")

    # 只显示前 10 个
    display_models = models[:10]
    for i, m in enumerate(display_models, 1):
        marker = " *" if m['id'] == recommended else ""
        print(f"    {i}. {m['id']}{marker}")

    if len(models) > 10:
        print(f"    ... 还有 {len(models) - 10} 个模型")

    choice = input(f"\n请选择 (1-{len(display_models)}, 回车使用推荐): ").strip()

    if choice:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(display_models):
                selected_model = display_models[idx]['id']
            else:
                selected_model = recommended
        except ValueError:
            selected_model = recommended
    else:
        selected_model = recommended

    # 5. 保存配置
    print(f"\n[5] 配置确认:")
    print(f"  Provider: {selected_provider}")
    print(f"  Model: {selected_model}")

    confirm = input("\n确认保存? (Y/n): ").strip().lower()
    if confirm != 'n':
        save_config(selected_provider, selected_model)
        print("\n配置完成！现在可以运行测试:")
        print(f"  python test_gemini.py")
    else:
        print("\n已取消")


def auto_setup():
    """自动配置（非交互式）"""
    print("自动检测并配置 LLM...")

    available_keys = check_api_keys()
    if not available_keys:
        print("未检测到 API Key")
        return None, None

    # 优先级: gemini > claude > openai
    priority = ["gemini", "claude", "openai", "grok", "qwen"]

    for provider in priority:
        if provider in available_keys:
            api_key = available_keys[provider]

            if provider == "gemini":
                models = fetch_gemini_models(api_key)
            elif provider == "claude":
                models = fetch_claude_models(api_key)
            elif provider == "openai":
                models = fetch_openai_models(api_key)
            else:
                models = []

            if models:
                model = recommend_model(models, provider)
                print(f"自动选择: {provider} / {model}")
                save_config(provider, model)
                return provider, model

    return None, None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM 配置向导")
    parser.add_argument("--auto", action="store_true", help="自动配置（非交互式）")
    parser.add_argument("--list", action="store_true", help="列出所有可用模型")
    args = parser.parse_args()

    if args.auto:
        auto_setup()
    elif args.list:
        available_keys = check_api_keys()
        for provider, key in available_keys.items():
            print(f"\n{provider.upper()} 可用模型:")
            if provider == "gemini":
                models = fetch_gemini_models(key)
            elif provider == "claude":
                models = fetch_claude_models(key)
            elif provider == "openai":
                models = fetch_openai_models(key)
            else:
                models = []

            for m in models[:15]:
                print(f"  - {m['id']}")
    else:
        interactive_setup()
