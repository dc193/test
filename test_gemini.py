#!/usr/bin/env python3
"""
测试 Gemini API 连通性
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# 加载 .env 文件
load_dotenv()

# 获取 API Key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("错误：未找到 GOOGLE_API_KEY 环境变量")
    exit(1)

print(f"API Key: {api_key[:10]}...{api_key[-4:]}")

# 配置 API
genai.configure(api_key=api_key)

# 测试不同的模型名称
model_names = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash",
]

for model_name in model_names:
    print(f"\n--- 测试模型: {model_name} ---")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("你好，测试一下连通性，回复'OK'即可")
        print(f"成功！响应: {response.text[:100]}")
        break  # 成功就跳出
    except Exception as e:
        print(f"失败: {e}")
