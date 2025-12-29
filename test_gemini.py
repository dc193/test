"""测试 Gemini 集成

使用方法：
1. 设置环境变量: export GEMINI_API_KEY="你的key"
2. 运行: python test_gemini.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


async def test_gemini_basic():
    """基础 Gemini 测试"""
    print("\n" + "=" * 50)
    print("  基础 Gemini 测试")
    print("=" * 50)

    from src.core.llm import create_llm_provider, get_api_key

    # 检查 API Key
    api_key = get_api_key("gemini")
    if not api_key:
        print("[ERROR] 请设置 GEMINI_API_KEY 或 GOOGLE_API_KEY 环境变量")
        return False

    print(f"[OK] API Key 已配置 (前8位: {api_key[:8]}...)")

    # 创建 Provider
    try:
        llm = create_llm_provider(provider_name="gemini")
        print(f"[OK] Gemini Provider 创建成功")
    except Exception as e:
        print(f"[ERROR] 创建 Provider 失败: {e}")
        return False

    # 简单对话测试
    print("\n[测试] 简单对话:")
    try:
        response = await llm.chat([
            {"role": "user", "content": "用一句话介绍你自己"}
        ])
        print(f"    回复: {response}")
    except Exception as e:
        print(f"    [ERROR] 对话失败: {e}")
        return False

    return True


async def test_advisory_with_gemini():
    """使用 Gemini 测试顾问系统"""
    print("\n" + "=" * 50)
    print("  顾问系统测试 (Gemini)")
    print("=" * 50)

    from src.core.llm import create_llm_provider, get_api_key
    from src.agents import AdvisorySystem, Perspective

    api_key = get_api_key("gemini")
    if not api_key:
        print("[SKIP] 需要 GEMINI_API_KEY")
        return True

    llm = create_llm_provider(provider_name="gemini")
    advisory = AdvisorySystem(llm_provider=llm)

    # 获取战略视角建议
    print("\n[测试] 获取战略视角建议:")
    context = "我们的 SaaS 产品月活用户 5000，但付费转化率只有 2%"

    try:
        opinion = await advisory.get_perspective(
            Perspective.STRATEGIC,
            context=context
        )
        print(f"    视角: {opinion.perspective.value}")
        print(f"    观点: {opinion.opinion[:200]}...")
        print(f"    要点: {opinion.key_points[:3]}")
    except Exception as e:
        print(f"    [ERROR] 获取建议失败: {e}")
        return False

    return True


async def test_ceo_with_gemini():
    """使用 Gemini 测试 CEO Agent"""
    print("\n" + "=" * 50)
    print("  CEO Agent 测试 (Gemini)")
    print("=" * 50)

    from src.core.llm import create_llm_provider, get_api_key
    from src.agents import CEOAgent, AdvisorySystem, GodLayer

    api_key = get_api_key("gemini")
    if not api_key:
        print("[SKIP] 需要 GEMINI_API_KEY")
        return True

    llm = create_llm_provider(provider_name="gemini")
    advisory = AdvisorySystem(llm_provider=llm)
    god = GodLayer(llm_provider=llm, data_dir="data/test_gemini")

    ceo = CEOAgent(
        llm_provider=llm,
        advisory_system=advisory,
        god_layer=god
    )

    # 快速任务
    print("\n[测试] CEO 快速任务:")
    try:
        result = await ceo.quick_task("列出 3 个提升用户留存的策略")
        print(f"    结果: {result[:300]}...")
    except Exception as e:
        print(f"    [ERROR] 任务失败: {e}")
        return False

    return True


async def test_full_workflow_gemini():
    """完整工作流测试"""
    print("\n" + "=" * 50)
    print("  完整工作流测试 (Gemini)")
    print("=" * 50)

    from src.core.llm import create_llm_provider, get_api_key
    from src.agents import (
        CEOAgent, AdvisorySystem, GodLayer,
        COO, CHRO, AgentPool, HookManager,
        Task, Perspective
    )

    api_key = get_api_key("gemini")
    if not api_key:
        print("[SKIP] 需要 GEMINI_API_KEY")
        return True

    # 创建完整系统
    print("\n[1] 初始化系统组件:")
    llm = create_llm_provider(provider_name="gemini")
    print("    - LLM (Gemini): OK")

    hook_manager = HookManager()
    print("    - HookManager: OK")

    agent_pool = AgentPool(max_agents=5, llm_provider=llm)
    print("    - AgentPool: OK")

    chro = CHRO(agent_pool=agent_pool, llm_provider=llm, data_dir="data/test_gemini")
    print("    - CHRO: OK")

    coo = COO(chro=chro, agent_pool=agent_pool, llm_provider=llm, hook_manager=hook_manager)
    print("    - COO: OK")

    advisory = AdvisorySystem(llm_provider=llm)
    print("    - Advisory: OK")

    god = GodLayer(llm_provider=llm, data_dir="data/test_gemini")
    print("    - GodLayer: OK")

    ceo = CEOAgent(llm_provider=llm, advisory_system=advisory, god_layer=god)
    print("    - CEO: OK")

    # 执行任务
    print("\n[2] 执行任务: '分析竞品并给出差异化建议'")
    try:
        task = Task.create("分析竞品并给出差异化建议")
        result = await ceo.handle_task(task)

        print(f"\n[3] 任务结果:")
        print(f"    状态: {result.status}")
        print(f"    咨询视角: {result.perspectives_consulted}")
        print(f"\n    输出摘要:")
        print(f"    {result.output[:500]}...")

    except Exception as e:
        print(f"    [ERROR] 任务执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """主测试"""
    print("=" * 60)
    print("  Gemini 集成测试")
    print("=" * 60)

    # 检查环境变量
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        print("\n[提示] 请先设置 Gemini API Key:")
        print("  export GEMINI_API_KEY='你的key'")
        print("  或在 .env 文件中添加: GEMINI_API_KEY=你的key")
        print("\n然后重新运行此脚本")
        return

    tests = [
        ("基础 Gemini 测试", test_gemini_basic),
        ("顾问系统测试", test_advisory_with_gemini),
        ("CEO Agent 测试", test_ceo_with_gemini),
        ("完整工作流", test_full_workflow_gemini),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\n[ERROR] {name} 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, "ERROR"))

    # 总结
    print("\n" + "=" * 60)
    print("  测试结果")
    print("=" * 60)
    for name, result in results:
        icon = "OK" if result == "PASS" else "X"
        print(f"    [{icon}] {name}: {result}")


if __name__ == "__main__":
    asyncio.run(main())
