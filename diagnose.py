#!/usr/bin/env python3
"""
诊断 Gemini API - 找出可用的模型
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("错误：未找到 GOOGLE_API_KEY")
    exit(1)

print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
print(f"SDK 版本: {genai.__version__}")
print()

genai.configure(api_key=api_key)

# 1. 列出所有可用模型
print("=" * 50)
print("可用模型列表：")
print("=" * 50)

available_for_generate = []
for model in genai.list_models():
    name = model.name
    methods = model.supported_generation_methods
    if "generateContent" in methods:
        print(f"✓ {name}")
        available_for_generate.append(name)

print()
print("=" * 50)
print("尝试调用测试：")
print("=" * 50)

# 2. 按优先级尝试这些模型
test_models = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
    "gemini-1.0-pro",
]

# 也加入从 list_models 获取的模型（去掉 models/ 前缀）
for m in available_for_generate:
    short_name = m.replace("models/", "")
    if short_name not in test_models:
        test_models.append(short_name)

for model_name in test_models:
    print(f"\n测试: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("回复OK")
        print(f"  ✓ 成功! 响应: {response.text.strip()[:50]}")
        print(f"\n推荐使用这个模型: {model_name}")
        break
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower():
            print(f"  ✗ 配额限制")
        elif "404" in err:
            print(f"  ✗ 模型不存在")
        else:
            print(f"  ✗ {err[:80]}")
