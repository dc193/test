#!/usr/bin/env python3
"""测试自进化系统"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from src.memory import create_knowledge_base, SelfEvolvingKnowledge
from src.core.llm import create_llm_provider


async def test_evolution():
    """测试自进化流程"""
    print("\n" + "=" * 50)
    print("  自进化系统测试")
    print("=" * 50)

    # 1. 初始化
    print("\n[1] 初始化知识库和自进化系统...")
    kb = create_knowledge_base()
    llm = create_llm_provider()

    evolution = SelfEvolvingKnowledge(
        knowledge_base=kb,
        llm_provider=llm,
        learning_cooldown_seconds=10,  # 测试用：10秒冷却
        daily_learning_quota=50        # 测试用：50次配额
    )

    # 2. 查看防护状态
    print("\n[2] 防护状态:")
    status = evolution.get_protection_status()
    print(f"    每日配额: {status['daily_quota']}")
    print(f"    今日剩余: {status['remaining_quota']}")
    print(f"    冷却时间: {status['cooldown_seconds']}秒")
    print(f"    可以学习: {status['can_learn']}")

    # 3. 专家召唤测试
    print("\n[3] 测试专家召唤...")
    print("    场景：需要制定一个产品增长策略")

    results = await evolution.summon_experts(
        task_description="制定一个 SaaS 产品的用户增长策略，目标是 3 个月内增长 50%",
        domain="product"
    )

    if results:
        print(f"    找到 {len(results)} 条相关知识:")
        for r in results[:3]:
            print(f"      - {r.knowledge.title[:40]}... (相关度: {r.score:.2f})")
    else:
        print("    知识库为空，先添加一些知识再测试")

    # 4. 任务追踪流程
    print("\n[4] 测试任务追踪流程...")

    # 开始任务
    task = evolution.start_task(
        task_id="test_task_001",
        description="为电商 App 设计一个会员积分系统",
        domain="product",
        required_personas=["product_manager", "growth_hacker"]
    )
    print(f"    任务已创建: {task.task_id}")

    # 模拟使用知识
    if results:
        for r in results[:2]:
            evolution.record_knowledge_usage(task.task_id, r.knowledge.id)
            print(f"    记录使用知识: {r.knowledge.id}")

    # 完成任务
    completed = evolution.complete_task(
        task_id="test_task_001",
        outcome="success",
        user_feedback="积分系统设计很实用，用户反馈良好"
    )
    print(f"    任务完成: {completed.outcome}")

    # 5. 从任务学习（会调用 LLM）
    print("\n[5] 测试从任务学习（调用 LLM）...")

    task_result = """
    设计了一个三层会员积分系统：
    - 基础积分：消费金额 1:1 积分
    - 任务积分：签到、评价、分享可获得额外积分
    - 等级倍数：高等级会员有积分加成

    用户参与度提升 30%，复购率提升 15%。
    关键成功因素是让积分获取路径清晰且即时可见。
    """

    knowledge, message = await evolution.learn_from_task(
        task_id="test_task_001",
        task_result=task_result
    )

    print(f"    学习结果: {message}")
    if knowledge:
        print(f"    新知识ID: {knowledge.id}")
        print(f"    标题: {knowledge.title}")

    # 6. 更新后的防护状态
    print("\n[6] 更新后的防护状态:")
    status = evolution.get_protection_status()
    print(f"    今日已用: {status['used_today']}")
    print(f"    今日剩余: {status['remaining_quota']}")
    print(f"    冷却剩余: {status['cooldown_remaining']}秒")

    # 7. 测试知识缺口发现
    print("\n[7] 测试知识缺口发现...")

    gap, gap_msg = await evolution.discover_knowledge_gap(
        task_description="需要做 A/B 测试来验证新功能",
        task_id="test_task_002",
        failure_reason="不确定如何设计统计显著性的样本量"
    )

    print(f"    结果: {gap_msg}")
    if gap:
        print(f"    缺口ID: {gap.id}")
        print(f"    建议来源: {gap.suggested_sources}")

    # 8. 查看统计
    print("\n[8] 进化统计:")
    stats = evolution.get_evolution_stats()
    for key, value in stats.items():
        print(f"    {key}: {value}")

    print("\n" + "=" * 50)
    print("  测试完成！")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(test_evolution())
