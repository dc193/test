"""
Obsidian Vault 读写模块
负责灵感和思维模型的存储与检索
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


class ObsidianVault:
    """Obsidian Vault 管理器"""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.ideas_dir = self.vault_path / "💡 灵感"
        self.models_dir = self.vault_path / "🧠 思维模型"
        self.summaries_dir = self.vault_path / "📊 总结"

    def init_vault(self, templates_dir: str = "vault_templates"):
        """初始化 vault 目录结构，复制思维模型模板"""
        # 创建目录
        self.ideas_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

        # 复制思维模型模板
        templates_path = Path(templates_dir) / "思维模型"
        if templates_path.exists() and not any(self.models_dir.iterdir()):
            for template_file in templates_path.glob("*.md"):
                dest_file = self.models_dir / template_file.name
                if not dest_file.exists():
                    content = template_file.read_text(encoding="utf-8")
                    # 替换日期占位符
                    content = content.replace("{{date}}", datetime.now().strftime("%Y-%m-%d"))
                    dest_file.write_text(content, encoding="utf-8")
            print(f"✅ 已初始化 {len(list(self.models_dir.glob('*.md')))} 个思维模型")

    def save_idea(
        self,
        content: str,
        models: list[str] = None,
        tags: list[str] = None,
        trigger: str = None,
        ai_analysis: str = None,
    ) -> str:
        """
        保存一条灵感到 vault

        Args:
            content: 灵感内容
            models: 关联的思维模型列表
            tags: 标签列表
            trigger: 触发这个想法的场景
            ai_analysis: AI 的分析

        Returns:
            保存的文件路径
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H%M%S")

        # 生成简短标题（取前20个字符）
        title = re.sub(r"[\\/:*?\"<>|]", "", content[:30]).strip()
        if len(content) > 30:
            title += "..."

        filename = f"{date_str}-{time_str}-{title}.md"
        filepath = self.ideas_dir / filename

        # 构建 frontmatter
        frontmatter_lines = [
            "---",
            f"date: {now.strftime('%Y-%m-%d %H:%M')}",
        ]

        if tags:
            frontmatter_lines.append(f"tags: [{', '.join(tags)}]")

        if models:
            model_links = [f"[[{m}]]" for m in models]
            frontmatter_lines.append(f"models: {', '.join(model_links)}")

        if trigger:
            frontmatter_lines.append(f"trigger: \"{trigger}\"")

        frontmatter_lines.append("---")

        # 构建正文
        body_lines = [
            "",
            f"# {title}",
            "",
            content,
        ]

        if ai_analysis:
            body_lines.extend([
                "",
                "## AI 分析",
                "",
                ai_analysis,
            ])

        body_lines.extend([
            "",
            "## 相关灵感",
            "",
        ])

        # 写入文件
        full_content = "\n".join(frontmatter_lines + body_lines)
        filepath.write_text(full_content, encoding="utf-8")

        return str(filepath)

    def get_all_models(self) -> list[dict]:
        """获取所有思维模型"""
        models = []
        for model_file in self.models_dir.glob("*.md"):
            content = model_file.read_text(encoding="utf-8")
            name = model_file.stem

            # 提取定义（## 定义 后的内容）
            definition = ""
            match = re.search(r"## 定义\n+(.+?)(?=\n##|\n---|\Z)", content, re.DOTALL)
            if match:
                definition = match.group(1).strip()

            # 提取别名
            aliases = []
            match = re.search(r"aliases:\s*\[([^\]]+)\]", content)
            if match:
                aliases = [a.strip() for a in match.group(1).split(",")]

            models.append({
                "name": name,
                "definition": definition,
                "aliases": aliases,
                "file_path": str(model_file),
            })

        return models

    def get_model_names(self) -> list[str]:
        """获取所有思维模型的名称"""
        return [m.stem for m in self.models_dir.glob("*.md")]

    def get_recent_ideas(self, limit: int = 10) -> list[dict]:
        """获取最近的灵感"""
        ideas = []
        files = sorted(self.ideas_dir.glob("*.md"), key=os.path.getmtime, reverse=True)

        for idea_file in files[:limit]:
            content = idea_file.read_text(encoding="utf-8")
            name = idea_file.stem

            # 提取日期
            date = ""
            match = re.search(r"date:\s*(.+)", content)
            if match:
                date = match.group(1).strip()

            # 提取正文（跳过 frontmatter 和标题）
            body = ""
            lines = content.split("\n")
            in_frontmatter = False
            for line in lines:
                if line.strip() == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if not in_frontmatter and not line.startswith("#") and line.strip():
                    body = line.strip()
                    break

            ideas.append({
                "name": name,
                "date": date,
                "preview": body[:100] + "..." if len(body) > 100 else body,
                "file_path": str(idea_file),
            })

        return ideas

    def search_ideas(self, keyword: str) -> list[dict]:
        """搜索灵感"""
        results = []
        keyword_lower = keyword.lower()

        for idea_file in self.ideas_dir.glob("*.md"):
            content = idea_file.read_text(encoding="utf-8")
            if keyword_lower in content.lower():
                name = idea_file.stem
                # 找到包含关键词的行
                for line in content.split("\n"):
                    if keyword_lower in line.lower():
                        results.append({
                            "name": name,
                            "match": line.strip()[:100],
                            "file_path": str(idea_file),
                        })
                        break

        return results

    def get_random_idea(self) -> Optional[dict]:
        """随机获取一条灵感"""
        import random

        files = list(self.ideas_dir.glob("*.md"))
        if not files:
            return None

        idea_file = random.choice(files)
        content = idea_file.read_text(encoding="utf-8")

        # 提取正文
        body = ""
        lines = content.split("\n")
        in_frontmatter = False
        capture = False
        body_lines = []

        for line in lines:
            if line.strip() == "---":
                in_frontmatter = not in_frontmatter
                continue
            if not in_frontmatter:
                if line.startswith("# "):
                    capture = True
                    continue
                if line.startswith("## "):
                    break
                if capture:
                    body_lines.append(line)

        body = "\n".join(body_lines).strip()

        return {
            "name": idea_file.stem,
            "content": body,
            "file_path": str(idea_file),
        }

    def get_ideas_count(self) -> int:
        """获取灵感总数"""
        return len(list(self.ideas_dir.glob("*.md")))

    def get_models_count(self) -> int:
        """获取思维模型总数"""
        return len(list(self.models_dir.glob("*.md")))

    def save_model(
        self,
        name: str,
        definition: str,
        key_points: list[str] = None,
        applications: list[str] = None,
        representatives: str = None,
    ) -> str:
        """
        保存一个新的思维模型

        Args:
            name: 模型名称
            definition: 定义
            key_points: 核心要点列表
            applications: 应用场景列表
            representatives: 代表人物

        Returns:
            保存的文件路径
        """
        filename = f"{name}.md"
        filepath = self.models_dir / filename

        # 如果已存在则返回 None 表示未创建
        if filepath.exists():
            return None

        # 构建内容
        lines = [
            "---",
            f"tags: [思维模型]",
            f"created: {datetime.now().strftime('%Y-%m-%d')}",
            "---",
            "",
            f"# {name}",
            "",
            "## 定义",
            "",
            definition,
            "",
        ]

        if key_points:
            lines.extend([
                "## 核心要点",
                "",
            ])
            for point in key_points:
                lines.append(f"- {point}")
            lines.append("")

        if applications:
            lines.extend([
                "## 典型应用",
                "",
            ])
            for app in applications:
                lines.append(f"- {app}")
            lines.append("")

        if representatives:
            lines.extend([
                "## 代表人物",
                "",
                representatives,
                "",
            ])

        lines.extend([
            "## 相关灵感",
            "",
        ])

        content = "\n".join(lines)
        filepath.write_text(content, encoding="utf-8")

        return str(filepath)

    def delete_model(self, name: str) -> bool:
        """
        删除一个思维模型

        Args:
            name: 模型名称

        Returns:
            是否删除成功
        """
        filepath = self.models_dir / f"{name}.md"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def get_model_detail(self, name: str) -> Optional[dict]:
        """
        获取思维模型详情

        Args:
            name: 模型名称

        Returns:
            模型详情
        """
        filepath = self.models_dir / f"{name}.md"
        if not filepath.exists():
            return None

        content = filepath.read_text(encoding="utf-8")

        # 提取定义
        definition = ""
        match = re.search(r"## 定义\n+(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if match:
            definition = match.group(1).strip()

        return {
            "name": name,
            "definition": definition,
            "content": content,
            "file_path": str(filepath),
        }

    def get_two_random_ideas(self) -> tuple[Optional[dict], Optional[dict]]:
        """获取两条随机灵感用于关联分析"""
        import random

        files = list(self.ideas_dir.glob("*.md"))
        if len(files) < 2:
            return None, None

        selected = random.sample(files, 2)
        ideas = []

        for idea_file in selected:
            content = idea_file.read_text(encoding="utf-8")

            # 提取正文
            lines = content.split("\n")
            in_frontmatter = False
            capture = False
            body_lines = []

            for line in lines:
                if line.strip() == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if not in_frontmatter:
                    if line.startswith("# "):
                        capture = True
                        continue
                    if line.startswith("## "):
                        break
                    if capture:
                        body_lines.append(line)

            body = "\n".join(body_lines).strip()
            ideas.append({
                "name": idea_file.stem,
                "content": body,
            })

        return ideas[0], ideas[1]

    def save_summary(self, content: str, title: str = None) -> str:
        """
        保存周报/总结

        Args:
            content: 总结内容
            title: 标题（可选）

        Returns:
            保存的文件路径
        """
        now = datetime.now()
        if not title:
            # 默认使用周报格式
            week_num = now.isocalendar()[1]
            title = f"{now.year}-W{week_num:02d} 周报"

        filename = f"{title}.md"
        filepath = self.summaries_dir / filename

        lines = [
            "---",
            f"date: {now.strftime('%Y-%m-%d %H:%M')}",
            "tags: [总结]",
            "---",
            "",
            f"# {title}",
            "",
            content,
        ]

        full_content = "\n".join(lines)
        filepath.write_text(full_content, encoding="utf-8")

        return str(filepath)
