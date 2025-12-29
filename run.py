#!/usr/bin/env python3
"""启动AI Company"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def main():
    """启动Web服务"""
    print("\n" + "=" * 50)
    print("  AI Company v0.1")
    print("=" * 50)
    print("\n启动中...\n")

    # 检查API Key
    has_key = (
        os.getenv("OPENAI_API_KEY") or
        os.getenv("ANTHROPIC_API_KEY") or
        os.getenv("GEMINI_API_KEY") or
        os.getenv("GOOGLE_API_KEY")
    )
    if not has_key:
        print("⚠️  警告: 未设置任何 API Key")
        print("   请设置以下环境变量之一:")
        print("   - GEMINI_API_KEY / GOOGLE_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("   - OPENAI_API_KEY\n")

    print("🚀 访问 http://localhost:8000 开始使用\n")
    print("=" * 50 + "\n")

    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
