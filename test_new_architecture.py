"""测试新的三层架构

测试内容：
1. 上帝层 (GodLayer) - 元认知与进化
2. CEO层 (CEOAgent) - 决策与执行
3. 顾问团 (AdvisorySystem) - 多元视角
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


async def test_advisory_system():
    """测试顾问团"""
    print("\n" + "=" * 50)
    print("  测试顾问团 (Advisory System)")
    print("=" * 50)

    from src.agents.advisory import AdvisorySystem, Perspective, PERSPECTIVE_PROFILES
    from src.core.llm import create_llm_provider

    # 创建 LLM
    try:
        llm = create_llm_provider()
        print(f"[OK] LLM Provider 创建成功")
    except Exception as e:
        print(f"[WARN] LLM 不可用: {e}")
        llm = None

    # 创建顾问系统
    advisory = AdvisorySystem(llm_provider=llm)

    # 1. 查看所有视角
    print("\n[1] 可用视角:")
    for p in Perspective:
        profile = PERSPECTIVE_PROFILES[p]
        print(f"    - {p.value}: {profile.name} - {profile.description}")

    # 2. 获取单个视角建议
    print("\n[2] 测试单视角咨询:")
    context = "我们的产品用户增长放缓，需要找到新的增长点"

    opinion = await advisory.get_perspective(
        Perspective.STRATEGIC,
        context=context
    )
    print(f"    视角: {opinion.perspective.value}")
    print(f"    观点: {opinion.opinion}")
    print(f"    要点: {opinion.key_points}")
    print(f"    建议: {opinion.suggestions}")

    # 3. 多视角咨询
    print("\n[3] 测试多视角咨询:")
    opinions = await advisory.consult(
        context=context,
        perspectives=[Perspective.PRODUCT, Perspective.USER, Perspective.BUSINESS]
    )
    for op in opinions:
        profile = PERSPECTIVE_PROFILES[op.perspective]
        print(f"\n    【{profile.name}】")
        print(f"    {op.opinion}")

    # 4. 综合意见
    if llm:
        print("\n[4] 综合意见:")
        synthesis = await advisory.synthesize_opinions(opinions, context)
        print(f"    {synthesis}")

    return True


async def test_god_layer():
    """测试上帝层"""
    print("\n" + "=" * 50)
    print("  测试上帝层 (God Layer)")
    print("=" * 50)

    from src.agents.god_layer import GodLayer, TaskRecord, TriggerType
    from src.core.llm import create_llm_provider

    # 创建 LLM
    try:
        llm = create_llm_provider()
    except:
        llm = None

    # 创建上帝层（使用测试目录）
    god = GodLayer(
        llm_provider=llm,
        data_dir="data/test_god_layer",
        task_trigger_count=5,  # 测试用，设置小一点
        max_weekly_learning=3
    )

    # 1. 查看状态
    print("\n[1] 上帝层状态:")
    status = god.get_status()
    for k, v in status.items():
        print(f"    {k}: {v}")

    # 2. 模拟记录几个任务
    print("\n[2] 模拟任务记录:")
    test_tasks = [
        ("task_001", "分析竞品策略", "success"),
        ("task_002", "设计用户增长方案", "success"),
        ("task_003", "优化技术架构", "partial"),
        ("task_004", "制定营销计划", "failed"),
        ("task_005", "财务预测分析", "failed"),
    ]

    for task_id, desc, status in test_tasks:
        record = TaskRecord(
            task_id=task_id,
            description=desc,
            status=status,
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T10:30:00",
            perspectives_consulted=["strategic", "product"],
            notes="测试任务" if status != "success" else ""
        )
        should_evolve = god.record_task(record)
        print(f"    记录: {desc} ({status}) -> 触发进化: {should_evolve}")

    # 3. 观察任务模式
    print("\n[3] 任务模式分析:")
    patterns = god.observe_task_patterns()
    print(f"    总任务: {patterns.get('total_tasks', 0)}")
    print(f"    成功率: {patterns.get('success_rate', 0):.1%}")
    print(f"    最近失败: {len(patterns.get('recent_failures', []))} 个")

    # 4. 学习配额
    print("\n[4] 学习配额:")
    quota = god.get_learning_quota()
    print(f"    本周已用: {quota['used']}/{quota['max']}")
    print(f"    剩余: {quota['remaining']}")

    # 5. 运行进化（如果有 LLM）
    if llm:
        print("\n[5] 运行进化:")
        log = await god.run_evolution(TriggerType.MANUAL)
        print(f"    触发类型: {log.trigger_type.value}")
        print(f"    观察: {log.observations}")
        print(f"    总结: {log.summary}")

    return True


async def test_ceo_agent():
    """测试 CEO 层"""
    print("\n" + "=" * 50)
    print("  测试 CEO 层 (CEO Agent)")
    print("=" * 50)

    from src.agents.ceo_agent import CEOAgent, Task
    from src.agents.advisory import AdvisorySystem, Perspective
    from src.agents.god_layer import GodLayer
    from src.core.llm import create_llm_provider

    # 创建组件
    try:
        llm = create_llm_provider()
        print("[OK] LLM Provider 创建成功")
    except Exception as e:
        print(f"[WARN] LLM 不可用: {e}")
        llm = None

    advisory = AdvisorySystem(llm_provider=llm)
    god = GodLayer(llm_provider=llm, data_dir="data/test_god_layer")

    # 创建 CEO
    ceo = CEOAgent(
        llm_provider=llm,
        advisory_system=advisory,
        god_layer=god
    )

    # 1. 查看状态
    print("\n[1] CEO 状态:")
    status = ceo.get_status()
    for k, v in status.items():
        print(f"    {k}: {v}")

    # 2. 快速任务
    print("\n[2] 快速任务测试:")
    if llm:
        result = await ceo.quick_task("简要分析 SaaS 产品的核心增长指标")
        print(f"    结果: {result[:200]}...")
    else:
        print("    [跳过] 需要 LLM")

    # 3. 问答模式
    print("\n[3] 问答模式:")
    if llm:
        answer = await ceo.ask(
            "什么是产品市场契合度(PMF)?",
            perspectives=[Perspective.PRODUCT, Perspective.BUSINESS]
        )
        print(f"    回答: {answer[:200]}...")
    else:
        print("    [跳过] 需要 LLM")

    # 4. 分析模式
    print("\n[4] 分析模式:")
    if llm:
        analysis = await ceo.analyze(
            topic="用户流失原因",
            context="B2B SaaS 产品，月活用户 1000，月流失率 5%"
        )
        print(f"    主题: {analysis['topic']}")
        print(f"    咨询视角: {analysis['perspectives']}")
        print(f"    分析: {analysis['analysis'][:200]}...")
    else:
        print("    [跳过] 需要 LLM")

    # 5. 决策模式
    print("\n[5] 决策模式:")
    if llm:
        decision = await ceo.decide(
            question="是否应该扩展到海外市场？",
            options=[
                "立即扩展，抢占先机",
                "先做市场调研，6个月后决定",
                "专注国内市场，暂不考虑"
            ]
        )
        print(f"    决策: {decision[:200]}...")
    else:
        print("    [跳过] 需要 LLM")

    return True


async def test_full_workflow():
    """测试完整工作流"""
    print("\n" + "=" * 50)
    print("  测试完整工作流")
    print("=" * 50)

    from src.agents import GodLayer, CEOAgent, AdvisorySystem
    from src.core.llm import create_llm_provider
    from src.memory.knowledge_base import create_knowledge_base, KnowledgeType

    # 创建所有组件
    try:
        llm = create_llm_provider()
    except:
        print("[WARN] LLM 不可用，跳过完整工作流测试")
        return True

    # 创建知识库
    kb = create_knowledge_base(data_dir="data/test_knowledge")

    # 添加一些测试知识
    kb.add(
        content="AARRR 模型是增长漏斗的核心框架：获取(Acquisition)、激活(Activation)、留存(Retention)、推荐(Referral)、收入(Revenue)。每个环节都需要关键指标来衡量。",
        knowledge_type=KnowledgeType.METHODOLOGY,
        title="AARRR 增长模型",
        tags=["增长", "产品", "指标"]
    )

    # 创建三层架构
    god = GodLayer(llm_provider=llm, knowledge_base=kb, data_dir="data/test_god_layer")
    advisory = AdvisorySystem(llm_provider=llm, knowledge_base=kb)
    ceo = CEOAgent(
        llm_provider=llm,
        knowledge_base=kb,
        advisory_system=advisory,
        god_layer=god
    )

    # 执行任务
    print("\n[工作流] 用户提出任务:")
    task_desc = "帮我制定一个提升用户留存率的方案"
    print(f"    '{task_desc}'")

    print("\n[工作流] CEO 处理中...")
    from src.agents.ceo_agent import Task
    task = Task.create(task_desc)
    result = await ceo.handle_task(task)

    print(f"\n[工作流] 任务结果:")
    print(f"    状态: {result.status}")
    print(f"    咨询视角: {result.perspectives_consulted}")
    print(f"    使用知识: {result.knowledge_used}")
    print(f"\n    输出:")
    print(f"    {result.output}")

    # 检查上帝层
    print("\n[工作流] 上帝层状态:")
    god_status = god.get_status()
    print(f"    已记录任务: {god_status['total_tasks_recorded']}")
    print(f"    距下次进化: {god_status['trigger_threshold'] - god_status['tasks_since_last_evolution']} 个任务")

    return True


async def main():
    """主测试函数"""
    print("=" * 60)
    print("  AI 公司三层架构测试")
    print("=" * 60)

    tests = [
        ("顾问团测试", test_advisory_system),
        ("上帝层测试", test_god_layer),
        ("CEO层测试", test_ceo_agent),
        ("完整工作流", test_full_workflow),
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
        status_icon = "✓" if result == "PASS" else "✗"
        print(f"    {status_icon} {name}: {result}")


if __name__ == "__main__":
    asyncio.run(main())
