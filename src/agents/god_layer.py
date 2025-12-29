"""上帝层 (God Layer) - 元认知与自我进化

职责：
- 观察系统运行模式
- 发现知识缺口
- 触发学习和进化
- 生成进化报告

触发机制：
- 定时：每周一次
- 事件：每 N 个任务后

权限边界：
- 可以：观察、分析、有限学习
- 不能：删除知识、修改核心配置
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from enum import Enum


class TriggerType(str, Enum):
    """触发类型"""
    SCHEDULED = "scheduled"  # 定时触发
    EVENT = "event"          # 事件触发
    MANUAL = "manual"        # 手动触发


@dataclass
class TaskRecord:
    """任务记录"""
    task_id: str
    description: str
    status: str  # "success", "failed", "partial"
    started_at: str
    completed_at: Optional[str] = None
    perspectives_consulted: list[str] = field(default_factory=list)
    knowledge_used: list[str] = field(default_factory=list)
    user_feedback: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "perspectives_consulted": self.perspectives_consulted,
            "knowledge_used": self.knowledge_used,
            "user_feedback": self.user_feedback,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskRecord":
        return cls(**data)


@dataclass
class KnowledgeGap:
    """知识缺口"""
    id: str
    topic: str
    description: str
    discovered_at: str
    frequency: int = 1  # 出现频率
    related_tasks: list[str] = field(default_factory=list)
    status: str = "open"  # "open", "learning", "resolved"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "description": self.description,
            "discovered_at": self.discovered_at,
            "frequency": self.frequency,
            "related_tasks": self.related_tasks,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGap":
        return cls(**data)


@dataclass
class EvolutionLog:
    """进化日志"""
    id: str
    trigger_type: TriggerType
    triggered_at: str
    observations: list[str] = field(default_factory=list)
    gaps_found: list[str] = field(default_factory=list)
    knowledge_learned: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trigger_type": self.trigger_type.value,
            "triggered_at": self.triggered_at,
            "observations": self.observations,
            "gaps_found": self.gaps_found,
            "knowledge_learned": self.knowledge_learned,
            "summary": self.summary
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvolutionLog":
        data["trigger_type"] = TriggerType(data["trigger_type"])
        return cls(**data)


@dataclass
class EvolutionReport:
    """进化周报"""
    period_start: str
    period_end: str
    total_tasks: int
    success_rate: float
    knowledge_gaps: list[KnowledgeGap]
    new_knowledge_count: int
    top_consulted_perspectives: list[tuple[str, int]]
    recommendations: list[str]


class GodLayer:
    """上帝层 - 元认知与自我进化"""

    def __init__(
        self,
        knowledge_base=None,
        llm_provider=None,
        data_dir: str = "data/god_layer",
        # 触发配置
        task_trigger_count: int = 20,
        # 限制配置
        max_weekly_learning: int = 10,
        learning_cooldown_hours: int = 1
    ):
        self.knowledge_base = knowledge_base
        self.llm = llm_provider
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 配置
        self.task_trigger_count = task_trigger_count
        self.max_weekly_learning = max_weekly_learning
        self.learning_cooldown_hours = learning_cooldown_hours

        # 数据文件
        self.tasks_file = self.data_dir / "task_records.json"
        self.gaps_file = self.data_dir / "knowledge_gaps.json"
        self.evolution_log_file = self.data_dir / "evolution_log.json"
        self.state_file = self.data_dir / "god_state.json"

        # 内存数据
        self._task_records: list[TaskRecord] = []
        self._knowledge_gaps: dict[str, KnowledgeGap] = {}
        self._evolution_logs: list[EvolutionLog] = []
        self._state: dict = {}

        # 加载数据
        self._load_all()

    def _load_all(self):
        """加载所有数据"""
        # 任务记录
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._task_records = [TaskRecord.from_dict(d) for d in data]
            except Exception as e:
                print(f"加载任务记录失败: {e}")

        # 知识缺口
        if self.gaps_file.exists():
            try:
                with open(self.gaps_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._knowledge_gaps = {
                        k: KnowledgeGap.from_dict(v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"加载知识缺口失败: {e}")

        # 进化日志
        if self.evolution_log_file.exists():
            try:
                with open(self.evolution_log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._evolution_logs = [EvolutionLog.from_dict(d) for d in data]
            except Exception as e:
                print(f"加载进化日志失败: {e}")

        # 状态
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
            except Exception as e:
                print(f"加载状态失败: {e}")

    def _save_tasks(self):
        """保存任务记录"""
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self._task_records], f, ensure_ascii=False, indent=2)

    def _save_gaps(self):
        """保存知识缺口"""
        with open(self.gaps_file, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in self._knowledge_gaps.items()}, f, ensure_ascii=False, indent=2)

    def _save_evolution_log(self):
        """保存进化日志"""
        with open(self.evolution_log_file, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._evolution_logs], f, ensure_ascii=False, indent=2)

    def _save_state(self):
        """保存状态"""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    # ==================== 观察能力 ====================

    def record_task(self, task: TaskRecord):
        """记录任务（由 CEO 层调用）"""
        self._task_records.append(task)
        self._save_tasks()

        # 检查是否触发事件驱动的进化
        tasks_since_last = self._state.get("tasks_since_last_evolution", 0) + 1
        self._state["tasks_since_last_evolution"] = tasks_since_last
        self._save_state()

        if tasks_since_last >= self.task_trigger_count:
            return self._should_trigger_evolution()
        return False

    def _should_trigger_evolution(self) -> bool:
        """检查是否应该触发进化"""
        last_evolution = self._state.get("last_evolution_at")
        if last_evolution:
            last_time = datetime.fromisoformat(last_evolution)
            cooldown = timedelta(hours=self.learning_cooldown_hours)
            if datetime.now() - last_time < cooldown:
                return False
        return True

    def observe_task_patterns(self) -> dict:
        """观察任务模式"""
        if not self._task_records:
            return {"message": "暂无任务记录"}

        # 最近的任务（最多100条）
        recent_tasks = self._task_records[-100:]

        # 统计
        total = len(recent_tasks)
        success = len([t for t in recent_tasks if t.status == "success"])
        failed = len([t for t in recent_tasks if t.status == "failed"])

        # 咨询视角统计
        perspective_counts = {}
        for task in recent_tasks:
            for p in task.perspectives_consulted:
                perspective_counts[p] = perspective_counts.get(p, 0) + 1

        # 知识使用统计
        knowledge_counts = {}
        for task in recent_tasks:
            for k in task.knowledge_used:
                knowledge_counts[k] = knowledge_counts.get(k, 0) + 1

        return {
            "total_tasks": total,
            "success_count": success,
            "failed_count": failed,
            "success_rate": success / total if total > 0 else 0,
            "top_perspectives": sorted(perspective_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_knowledge": sorted(knowledge_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "recent_failures": [
                {"task_id": t.task_id, "description": t.description, "notes": t.notes}
                for t in recent_tasks if t.status == "failed"
            ][-5:]
        }

    async def identify_knowledge_gaps(self) -> list[KnowledgeGap]:
        """识别知识缺口"""
        if not self.llm:
            return list(self._knowledge_gaps.values())

        # 获取最近失败的任务
        recent_failures = [
            t for t in self._task_records[-50:]
            if t.status in ("failed", "partial")
        ]

        if not recent_failures:
            return list(self._knowledge_gaps.values())

        # 用 LLM 分析知识缺口
        failure_descriptions = "\n".join([
            f"- 任务: {t.description}\n  问题: {t.notes}"
            for t in recent_failures[:10]
        ])

        prompt = f"""分析以下任务失败/部分完成的情况，识别可能的知识缺口。

失败任务：
{failure_descriptions}

请识别 1-3 个知识缺口，返回 JSON 格式：
[
  {{"topic": "缺口主题", "description": "缺什么知识，为什么需要"}}
]

只返回 JSON，不要其他内容。"""

        try:
            response = await self.llm.chat([{"role": "user", "content": prompt}])
            gaps_data = json.loads(response)

            new_gaps = []
            for gap_data in gaps_data:
                gap_id = f"gap_{len(self._knowledge_gaps) + 1}"
                gap = KnowledgeGap(
                    id=gap_id,
                    topic=gap_data["topic"],
                    description=gap_data["description"],
                    discovered_at=datetime.now().isoformat(),
                    related_tasks=[t.task_id for t in recent_failures[:5]]
                )
                self._knowledge_gaps[gap_id] = gap
                new_gaps.append(gap)

            self._save_gaps()
            return new_gaps

        except Exception as e:
            print(f"识别知识缺口失败: {e}")
            return []

    # ==================== 进化能力 ====================

    def get_learning_quota(self) -> dict:
        """获取学习配额状态"""
        week_start = self._get_week_start()
        weekly_count = self._state.get(f"learning_count_{week_start}", 0)

        return {
            "week_start": week_start,
            "used": weekly_count,
            "remaining": max(0, self.max_weekly_learning - weekly_count),
            "max": self.max_weekly_learning
        }

    def _get_week_start(self) -> str:
        """获取本周开始日期"""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        return week_start.isoformat()

    def _can_learn(self) -> tuple[bool, str]:
        """检查是否可以学习"""
        # 检查冷却
        last_learn = self._state.get("last_learn_at")
        if last_learn:
            last_time = datetime.fromisoformat(last_learn)
            cooldown = timedelta(hours=self.learning_cooldown_hours)
            if datetime.now() - last_time < cooldown:
                remaining = cooldown - (datetime.now() - last_time)
                return False, f"冷却中，剩余 {remaining.seconds // 60} 分钟"

        # 检查周配额
        quota = self.get_learning_quota()
        if quota["remaining"] <= 0:
            return False, f"本周配额已用完 ({quota['used']}/{quota['max']})"

        return True, "可以学习"

    async def auto_learn(self, max_items: int = None) -> list[dict]:
        """自动学习（有限度）"""
        can_learn, reason = self._can_learn()
        if not can_learn:
            return [{"status": "blocked", "reason": reason}]

        if max_items is None:
            max_items = min(3, self.get_learning_quota()["remaining"])

        # 获取待解决的知识缺口
        open_gaps = [g for g in self._knowledge_gaps.values() if g.status == "open"]
        if not open_gaps:
            return [{"status": "no_gaps", "message": "没有待解决的知识缺口"}]

        # 按频率排序，优先学习高频缺口
        open_gaps.sort(key=lambda x: x.frequency, reverse=True)

        learned = []
        for gap in open_gaps[:max_items]:
            result = await self._learn_for_gap(gap)
            learned.append(result)

            if result.get("status") == "success":
                gap.status = "resolved"
                self._save_gaps()

        # 更新学习记录
        week_start = self._get_week_start()
        count_key = f"learning_count_{week_start}"
        self._state[count_key] = self._state.get(count_key, 0) + len([l for l in learned if l.get("status") == "success"])
        self._state["last_learn_at"] = datetime.now().isoformat()
        self._save_state()

        return learned

    async def _learn_for_gap(self, gap: KnowledgeGap) -> dict:
        """为特定知识缺口学习"""
        if not self.llm or not self.knowledge_base:
            return {"status": "error", "gap_id": gap.id, "message": "缺少 LLM 或知识库"}

        # 生成学习内容
        prompt = f"""为以下知识缺口生成一条高质量的知识条目。

知识缺口：
- 主题：{gap.topic}
- 描述：{gap.description}

请生成一条实用的知识，包含：
1. 核心概念或方法
2. 具体应用场景
3. 注意事项

返回格式：
{{
  "title": "知识标题",
  "content": "知识内容（200-500字）",
  "tags": ["标签1", "标签2"]
}}

只返回 JSON。"""

        try:
            response = await self.llm.chat([{"role": "user", "content": prompt}])
            knowledge_data = json.loads(response)

            # 添加到知识库
            from ..memory.knowledge_base import KnowledgeType
            knowledge = self.knowledge_base.add(
                content=knowledge_data["content"],
                knowledge_type=KnowledgeType.METHODOLOGY,
                title=knowledge_data["title"],
                source="god_layer_auto_learn",
                tags=knowledge_data.get("tags", [])
            )

            return {
                "status": "success",
                "gap_id": gap.id,
                "knowledge_id": knowledge.id,
                "title": knowledge_data["title"]
            }

        except Exception as e:
            return {"status": "error", "gap_id": gap.id, "message": str(e)}

    # ==================== 报告能力 ====================

    async def run_evolution(self, trigger_type: TriggerType = TriggerType.MANUAL) -> EvolutionLog:
        """运行一次进化"""
        log_id = f"evo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log = EvolutionLog(
            id=log_id,
            trigger_type=trigger_type,
            triggered_at=datetime.now().isoformat()
        )

        # 1. 观察任务模式
        patterns = self.observe_task_patterns()
        log.observations.append(f"任务成功率: {patterns.get('success_rate', 0):.1%}")
        if patterns.get("recent_failures"):
            log.observations.append(f"最近失败任务: {len(patterns['recent_failures'])} 个")

        # 2. 识别知识缺口
        new_gaps = await self.identify_knowledge_gaps()
        log.gaps_found = [g.id for g in new_gaps]
        if new_gaps:
            log.observations.append(f"发现新知识缺口: {len(new_gaps)} 个")

        # 3. 自动学习
        learned = await self.auto_learn()
        log.knowledge_learned = [
            l.get("knowledge_id") for l in learned
            if l.get("status") == "success" and l.get("knowledge_id")
        ]
        if log.knowledge_learned:
            log.observations.append(f"自动学习: {len(log.knowledge_learned)} 条新知识")

        # 4. 生成总结
        log.summary = await self._generate_summary(patterns, new_gaps, learned)

        # 保存
        self._evolution_logs.append(log)
        self._save_evolution_log()

        # 重置计数器
        self._state["tasks_since_last_evolution"] = 0
        self._state["last_evolution_at"] = datetime.now().isoformat()
        self._save_state()

        return log

    async def _generate_summary(self, patterns: dict, gaps: list, learned: list) -> str:
        """生成进化总结"""
        if not self.llm:
            parts = []
            if patterns.get("success_rate"):
                parts.append(f"任务成功率 {patterns['success_rate']:.1%}")
            if gaps:
                parts.append(f"发现 {len(gaps)} 个知识缺口")
            if learned:
                success_count = len([l for l in learned if l.get("status") == "success"])
                parts.append(f"学习了 {success_count} 条新知识")
            return "；".join(parts) if parts else "本次进化无重大发现"

        prompt = f"""根据以下信息生成一句简洁的进化总结（不超过50字）：

任务模式：
- 成功率：{patterns.get('success_rate', 0):.1%}
- 最近失败：{len(patterns.get('recent_failures', []))} 个

知识缺口：{len(gaps)} 个新发现

学习情况：{len([l for l in learned if l.get('status') == 'success'])} 条新知识

直接返回总结文字，不要其他内容。"""

        try:
            return await self.llm.chat([{"role": "user", "content": prompt}])
        except:
            return "进化完成"

    def generate_weekly_report(self) -> EvolutionReport:
        """生成进化周报"""
        week_start = self._get_week_start()
        week_end = datetime.now().isoformat()

        # 本周任务
        week_tasks = [
            t for t in self._task_records
            if t.started_at >= week_start
        ]

        total = len(week_tasks)
        success = len([t for t in week_tasks if t.status == "success"])

        # 视角统计
        perspective_counts = {}
        for task in week_tasks:
            for p in task.perspectives_consulted:
                perspective_counts[p] = perspective_counts.get(p, 0) + 1

        # 本周学习数
        new_knowledge = self._state.get(f"learning_count_{week_start}", 0)

        # 生成建议
        recommendations = []
        if total > 0 and success / total < 0.7:
            recommendations.append("任务成功率偏低，建议检查常见失败原因")

        open_gaps = [g for g in self._knowledge_gaps.values() if g.status == "open"]
        if len(open_gaps) > 5:
            recommendations.append(f"有 {len(open_gaps)} 个知识缺口待解决，建议增加学习")

        return EvolutionReport(
            period_start=week_start,
            period_end=week_end,
            total_tasks=total,
            success_rate=success / total if total > 0 else 0,
            knowledge_gaps=list(self._knowledge_gaps.values()),
            new_knowledge_count=new_knowledge,
            top_consulted_perspectives=sorted(perspective_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            recommendations=recommendations
        )

    # ==================== 状态查询 ====================

    def get_status(self) -> dict:
        """获取上帝层状态"""
        quota = self.get_learning_quota()
        return {
            "total_tasks_recorded": len(self._task_records),
            "tasks_since_last_evolution": self._state.get("tasks_since_last_evolution", 0),
            "trigger_threshold": self.task_trigger_count,
            "open_knowledge_gaps": len([g for g in self._knowledge_gaps.values() if g.status == "open"]),
            "learning_quota": quota,
            "last_evolution": self._state.get("last_evolution_at"),
            "total_evolutions": len(self._evolution_logs)
        }
