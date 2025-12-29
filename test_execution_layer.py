"""测试执行层组件

测试内容：
1. AgentPool - 并行执行池
2. HookManager - 钩子系统
3. ContextManager - 上下文管理
4. COO - 协调执行
5. CHRO - Agent 管理
6. 完整工作流集成
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


async def test_agent_pool():
    """测试 Agent 池"""
    print("\n" + "=" * 50)
    print("  测试 AgentPool (Agent 并行执行池)")
    print("=" * 50)

    from src.agents import AgentPool, PoolStats

    # 创建池
    pool = AgentPool(max_agents=5, max_agents_per_type=2)

    # 1. 获取 Agent
    print("\n[1] 获取 Agent:")
    agent1 = pool.get_agent("researcher")
    print(f"    获取 researcher: {'成功' if agent1 else '失败'}")

    agent2 = pool.get_agent("writer")
    print(f"    获取 writer: {'成功' if agent2 else '失败'}")

    # 2. 查看池状态
    print("\n[2] 池状态:")
    stats = pool.get_stats()
    print(f"    总 Agent: {stats.total_agents}")
    print(f"    空闲: {stats.idle_agents}")
    print(f"    繁忙: {stats.busy_agents}")

    # 3. 按类型统计
    print("\n[3] 类型分布:")
    types = pool.get_agent_types()
    for t, count in types.items():
        print(f"    {t}: {count}")

    # 4. 异步获取测试
    print("\n[4] 异步获取测试:")
    agent3 = await pool.acquire_agent("analyst", task_id="test_001")
    print(f"    获取 analyst: {'成功' if agent3 else '失败'}")

    # 释放
    pool.release_agent(agent3, success=True)
    print("    释放 analyst: 完成")

    # 5. 最终状态
    print("\n[5] 最终状态:")
    stats = pool.get_stats()
    print(f"    完成任务: {stats.completed_tasks}")
    print(f"    失败任务: {stats.failed_tasks}")

    return True


async def test_hook_manager():
    """测试钩子系统"""
    print("\n" + "=" * 50)
    print("  测试 HookManager (钩子系统)")
    print("=" * 50)

    from src.agents import HookManager, HookType, hook

    # 创建管理器
    manager = HookManager()

    # 1. 注册钩子
    print("\n[1] 注册钩子:")

    # 使用函数注册
    async def on_task_start(context):
        print(f"    [钩子触发] 任务开始: {context.get('task_id', 'unknown')}")
        return {"status": "logged"}

    hook_id1 = manager.register(
        HookType.PRE_TASK,
        on_task_start,
        name="任务开始日志",
        priority=10
    )
    print(f"    注册 PRE_TASK 钩子: {hook_id1}")

    # 注册第二个钩子
    async def on_task_end(context):
        print(f"    [钩子触发] 任务结束: {context.get('success', False)}")
        return {"status": "completed"}

    hook_id2 = manager.register(
        HookType.POST_TASK,
        on_task_end,
        name="任务结束日志"
    )
    print(f"    注册 POST_TASK 钩子: {hook_id2}")

    # 2. 触发钩子
    print("\n[2] 触发钩子:")
    results = await manager.trigger(HookType.PRE_TASK, {"task_id": "test_123"})
    print(f"    PRE_TASK 结果: {len(results)} 个钩子执行")
    for r in results:
        print(f"      - 成功: {r.success}, 耗时: {r.duration_ms:.2f}ms")

    # 3. 触发 POST_TASK
    results = await manager.trigger(HookType.POST_TASK, {"success": True})
    print(f"    POST_TASK 结果: {len(results)} 个钩子执行")

    # 4. 查看已注册钩子
    print("\n[3] 已注册钩子:")
    hooks = manager.get_hooks()
    for h in hooks:
        print(f"    - {h.name} ({h.hook_type.value})")

    # 5. 禁用钩子
    print("\n[4] 禁用/启用钩子:")
    manager.disable(hook_id1)
    print(f"    禁用 {hook_id1}")

    results = await manager.trigger(HookType.PRE_TASK, {"task_id": "test_456"})
    print(f"    触发 PRE_TASK: {len(results)} 个钩子执行（预期 0）")

    manager.enable(hook_id1)
    print(f"    启用 {hook_id1}")

    return True


async def test_context_manager():
    """测试上下文管理"""
    print("\n" + "=" * 50)
    print("  测试 ContextManager (上下文管理)")
    print("=" * 50)

    from src.agents import ContextManager, CompressionStrategy

    # 创建管理器
    ctx = ContextManager(
        model="claude-3-sonnet",
        max_tokens=10000,  # 测试用小窗口
        warning_threshold=0.7,
        compression_strategy=CompressionStrategy.HYBRID
    )

    # 1. 设置系统提示
    print("\n[1] 设置系统提示:")
    ctx.set_system_prompt("你是一个 AI 助手，擅长分析和解决问题。")
    print(f"    系统提示已设置")

    # 2. 添加消息
    print("\n[2] 添加消息:")
    for i in range(5):
        success = ctx.add_message("user", f"这是第 {i+1} 条测试消息，用于测试上下文管理功能。")
        print(f"    消息 {i+1}: {'成功' if success else '失败'}")

    # 3. 查看使用情况
    print("\n[3] Token 使用情况:")
    usage = ctx.get_usage()
    window = usage["window"]
    print(f"    已用: {window['used_tokens']}/{window['max_tokens']}")
    print(f"    使用率: {window['usage_ratio']}")
    print(f"    警告状态: {window['is_warning']}")

    # 4. 创建快照
    print("\n[4] 创建快照:")
    snapshot = ctx.create_snapshot("test_snap_001")
    print(f"    快照 ID: {snapshot.id}")
    print(f"    消息数: {len(snapshot.messages)}")
    print(f"    Token: {snapshot.token_count}")

    # 5. 清除并恢复
    print("\n[5] 快照恢复:")
    ctx.clear_messages()
    print(f"    清除后消息数: {len(ctx.get_messages(include_system=False))}")

    ctx.restore_snapshot("test_snap_001")
    print(f"    恢复后消息数: {len(ctx.get_messages(include_system=False))}")

    # 6. 模拟大量消息测试压缩
    print("\n[6] 压缩测试:")
    for i in range(20):
        ctx.add_message("user", f"压缩测试消息 {i+1}：" + "这是一段很长的测试内容。" * 10)

    usage = ctx.get_usage()
    print(f"    添加 20 条长消息后:")
    print(f"    消息数: {len(ctx.get_messages(include_system=False))}")
    print(f"    Token 使用: {usage['window']['used_tokens']}")

    return True


async def test_coo_coordination():
    """测试 COO 协调"""
    print("\n" + "=" * 50)
    print("  测试 COO (首席运营官)")
    print("=" * 50)

    from src.agents import COO, CHRO, HookManager, AgentPool

    # 创建依赖组件
    hook_manager = HookManager()
    chro = CHRO(data_dir="data/test_chro")
    pool = AgentPool(max_agents=5)

    # 注册进度钩子
    async def on_progress(context):
        progress = context.get("progress")
        if progress:
            print(f"    [进度] {progress.completed}/{progress.total_subtasks} 完成")

    hook_manager.register(
        hook_type=hook_manager.__class__.__bases__[0] if hasattr(hook_manager, '__class__') else None,
        handler=on_progress
    ) if False else None  # 简化测试

    # 创建 COO
    coo = COO(
        chro=chro,
        agent_pool=pool,
        hook_manager=hook_manager,
        max_parallel_agents=3
    )

    # 1. 规划执行
    print("\n[1] 规划执行:")
    decision = {
        "task_id": "test_task_001",
        "description": "分析竞品并撰写报告",
        "action_items": [
            {"description": "搜索竞品信息", "agent_type": "researcher"},
            {"description": "分析竞品数据", "agent_type": "analyst", "dependencies": []},
            {"description": "撰写分析报告", "agent_type": "writer", "dependencies": []}
        ]
    }

    plan = await coo.plan_execution(decision)
    print(f"    计划 ID: {plan.id}")
    print(f"    子任务数: {len(plan.subtasks)}")
    print(f"    并行组数: {len(plan.parallel_groups)}")

    # 2. 查看子任务
    print("\n[2] 子任务列表:")
    for st in plan.subtasks:
        print(f"    - [{st.agent_type}] {st.description}")

    # 3. 执行（模拟）
    print("\n[3] 执行任务:")
    result = await coo.coordinate_agents(plan)
    print(f"    执行成功: {result.success}")
    print(f"    耗时: {result.total_duration_seconds:.2f}s")
    print(f"    摘要: {result.summary}")

    # 4. 汇总结果
    print("\n[4] 汇总报告:")
    report = await coo.aggregate_results(result)
    print(f"    任务 ID: {report['task_id']}")
    print(f"    状态: {'成功' if report['success'] else '失败'}")

    return True


async def test_chro_management():
    """测试 CHRO Agent 管理"""
    print("\n" + "=" * 50)
    print("  测试 CHRO (首席人力资源官)")
    print("=" * 50)

    from src.agents import CHRO, AgentProfile, AgentCapability

    # 创建 CHRO
    chro = CHRO(data_dir="data/test_chro")

    # 1. 查看可用 Agent
    print("\n[1] 可用 Agent:")
    agents = chro.get_available_agents()
    for a in agents[:5]:  # 只显示前 5 个
        print(f"    - {a.agent_type}: {a.name} (成本级别: {a.cost_level})")

    # 2. 招聘 Agent
    print("\n[2] 招聘 Agent:")
    hired = await chro.hire_for_task(
        requirements=["研究调研", "数据分析", "文案撰写"],
        budget_level=2
    )
    print(f"    招聘数量: {len(hired)}")
    for agent in hired:
        print(f"    - {agent.agent_type}")

    # 3. 评估表现
    print("\n[3] 评估表现:")
    chro.evaluate_performance(
        agent_type="researcher",
        task_id="test_001",
        task_description="测试任务",
        success=True,
        duration_seconds=30.5,
        quality_score=0.85
    )
    print("    已记录 researcher 表现")

    # 4. 获取统计
    print("\n[4] 表现统计:")
    stats = chro.get_performance_stats()
    print(f"    总任务: {stats.get('total_tasks', 0)}")
    print(f"    成功率: {stats.get('success_rate', 0):.1%}")

    # 5. 推荐 Agent
    print("\n[5] Agent 推荐:")
    recommended = await chro.recommend_agent("帮我写一篇技术博客")
    print(f"    推荐: {recommended}")

    # 6. 注册自定义 Agent
    print("\n[6] 注册自定义 Agent:")
    custom = AgentProfile(
        agent_type="specialist",
        name="专家顾问",
        description="领域专家，提供专业建议",
        capabilities=[AgentCapability.ANALYSIS, AgentCapability.REVIEW],
        model="sonnet",
        cost_level=3
    )
    chro.register_agent(custom)

    return True


async def test_full_integration():
    """测试完整集成"""
    print("\n" + "=" * 50)
    print("  测试完整集成工作流")
    print("=" * 50)

    from src.agents import (
        GodLayer, CEOAgent, AdvisorySystem, Perspective,
        COO, CHRO, AgentPool, HookManager, ContextManager
    )
    from src.core.llm import create_llm_provider

    # 创建 LLM
    try:
        llm = create_llm_provider()
        print("[OK] LLM Provider 创建成功")
    except Exception as e:
        print(f"[WARN] LLM 不可用: {e}")
        llm = None

    # 创建所有组件
    print("\n[1] 创建组件:")

    hook_manager = HookManager()
    print("    - HookManager: OK")

    context_manager = ContextManager(model="claude-3-sonnet")
    print("    - ContextManager: OK")

    agent_pool = AgentPool(max_agents=10, llm_provider=llm)
    print("    - AgentPool: OK")

    chro = CHRO(agent_pool=agent_pool, llm_provider=llm, data_dir="data/test_integration")
    print("    - CHRO: OK")

    coo = COO(chro=chro, agent_pool=agent_pool, llm_provider=llm, hook_manager=hook_manager)
    print("    - COO: OK")

    advisory = AdvisorySystem(llm_provider=llm)
    print("    - AdvisorySystem: OK")

    god = GodLayer(llm_provider=llm, data_dir="data/test_integration")
    print("    - GodLayer: OK")

    ceo = CEOAgent(
        llm_provider=llm,
        advisory_system=advisory,
        god_layer=god
    )
    print("    - CEOAgent: OK")

    # 2. 注册钩子
    print("\n[2] 注册钩子:")

    async def log_start(ctx):
        print(f"    [Hook] 任务开始")
        return True

    async def log_end(ctx):
        print(f"    [Hook] 任务结束")
        return True

    from src.agents import HookType
    hook_manager.register(HookType.PRE_TASK, log_start, name="开始日志")
    hook_manager.register(HookType.POST_TASK, log_end, name="结束日志")
    print("    已注册 2 个钩子")

    # 3. 模拟工作流
    print("\n[3] 模拟工作流:")
    print("    用户请求: '帮我分析用户流失原因'")

    # CEO 接收任务
    if llm:
        from src.agents import Task
        task = Task.create("帮我分析用户流失原因")
        result = await ceo.handle_task(task)
        print(f"    CEO 处理结果: {result.status}")
        print(f"    咨询视角: {result.perspectives_consulted}")
    else:
        print("    [跳过] 需要 LLM")

    # 4. 查看系统状态
    print("\n[4] 系统状态:")

    # CEO 状态
    ceo_status = ceo.get_status()
    print(f"    CEO 任务数: {ceo_status['tasks_completed']}")

    # Pool 状态
    pool_stats = agent_pool.get_stats()
    print(f"    Agent 池: {pool_stats.total_agents} agents, {pool_stats.completed_tasks} 任务完成")

    # Context 使用
    ctx_usage = context_manager.get_usage()
    print(f"    上下文使用: {ctx_usage['window']['usage_ratio']}")

    # God Layer 状态
    god_status = god.get_status()
    print(f"    上帝层任务记录: {god_status['total_tasks_recorded']}")

    return True


async def main():
    """主测试函数"""
    print("=" * 60)
    print("  AI 公司执行层测试")
    print("=" * 60)

    tests = [
        ("AgentPool 测试", test_agent_pool),
        ("HookManager 测试", test_hook_manager),
        ("ContextManager 测试", test_context_manager),
        ("COO 协调测试", test_coo_coordination),
        ("CHRO 管理测试", test_chro_management),
        ("完整集成测试", test_full_integration),
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
    print("  测试结果总结")
    print("=" * 60)
    for name, result in results:
        status_icon = "OK" if result == "PASS" else "X"
        print(f"    [{status_icon}] {name}: {result}")

    passed = sum(1 for _, r in results if r == "PASS")
    print(f"\n    通过: {passed}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
