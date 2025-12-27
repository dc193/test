"""GitHub Learner - 从 GitHub 仓库学习

功能：
- Clone 仓库
- 用 LLM 分析代码，提炼核心思路
- 存入知识库（存的是"智慧"，不是原始代码）
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

from .knowledge_base import KnowledgeBase, Knowledge, KnowledgeType

if TYPE_CHECKING:
    from ..core.llm import LLMProvider


@dataclass
class RepoInfo:
    """仓库信息"""
    url: str
    name: str
    local_path: Path
    language: Optional[str] = None
    description: str = ""


# LLM 分析提示词
ANALYSIS_PROMPT = """你是一个代码分析专家。请分析以下 GitHub 仓库的代码，提炼出核心知识。

## 仓库信息
- 名称: {repo_name}
- URL: {repo_url}

## README 内容
{readme_content}

## 核心代码文件
{code_files}

---

请用中文提炼以下内容（每个部分 2-5 句话，简洁有力）：

### 1. 项目概述
这个项目解决什么问题？目标用户是谁？

### 2. 核心架构
项目的整体架构是什么？主要模块如何划分？

### 3. 关键实现思路
最核心的技术实现是什么？有什么巧妙的设计？

### 4. 设计模式与最佳实践
使用了哪些设计模式？有什么值得学习的代码实践？

### 5. 可复用的经验
如果要做类似项目，可以复用哪些思路？有什么注意事项？

请直接输出分析结果，不要有多余的开场白。
"""


class GitHubLearner:
    """GitHub 学习器 - 用 LLM 分析并提炼知识

    不是简单存储代码，而是让 AI 理解、分析、提炼
    """

    # 要分析的文件扩展名
    CODE_EXTENSIONS = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript React",
        ".jsx": "JavaScript React",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".kt": "Kotlin",
        ".swift": "Swift",
        ".rb": "Ruby",
        ".php": "PHP",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++ Header",
    }

    # 要跳过的目录
    SKIP_DIRS = {
        "node_modules", "__pycache__", ".git", ".venv", "venv",
        "dist", "build", ".next", ".nuxt", "vendor", "target",
        ".idea", ".vscode", "coverage", ".pytest_cache", "test", "tests"
    }

    # 重要文件（优先分析）
    IMPORTANT_FILES = {
        "README.md", "readme.md", "README.rst",
        "main.py", "app.py", "index.js", "index.ts", "main.go",
        "setup.py", "pyproject.toml", "package.json",
    }

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        llm_provider: Optional["LLMProvider"] = None,
        workspace_dir: str = "data/github_workspace"
    ):
        """初始化

        Args:
            knowledge_base: 知识库实例
            llm_provider: LLM 提供者（用于分析代码）
            workspace_dir: 临时工作目录
        """
        self.kb = knowledge_base
        self.llm = llm_provider
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(parents=True, exist_ok=True)

    async def learn_from_url(
        self,
        repo_url: str,
        max_code_files: int = 10,
        max_file_size: int = 30000,
        cleanup: bool = True
    ) -> dict:
        """从 GitHub URL 学习

        Args:
            repo_url: GitHub 仓库 URL
            max_code_files: 分析的核心代码文件数
            max_file_size: 最大文件大小
            cleanup: 学习后是否删除本地仓库

        Returns:
            学习结果统计
        """
        print(f"开始学习仓库: {repo_url}")

        # Clone 仓库
        repo_info = self._clone_repo(repo_url)
        if not repo_info:
            return {"error": "Clone 失败"}

        try:
            # 用 LLM 分析并提炼 (async)
            result = await self._analyze_with_llm(repo_info, max_code_files, max_file_size)
            return result
        finally:
            # 清理
            if cleanup:
                self._cleanup(repo_info)

    def _clone_repo(self, repo_url: str) -> Optional[RepoInfo]:
        """Clone 仓库"""
        # 从 URL 提取仓库名
        repo_name = repo_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        local_path = self.workspace / repo_name

        # 如果已存在，先删除
        if local_path.exists():
            shutil.rmtree(local_path)

        # Clone
        try:
            print(f"Cloning {repo_url}...")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(local_path)],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                print(f"Clone 失败: {result.stderr}")
                return None

            return RepoInfo(
                url=repo_url,
                name=repo_name,
                local_path=local_path
            )

        except subprocess.TimeoutExpired:
            print("Clone 超时")
            return None
        except Exception as e:
            print(f"Clone 错误: {e}")
            return None

    async def _analyze_with_llm(
        self,
        repo_info: RepoInfo,
        max_code_files: int,
        max_file_size: int
    ) -> dict:
        """用 LLM 分析仓库并提炼知识"""
        stats = {
            "repo": repo_info.name,
            "url": repo_info.url,
            "files_read": 0,
            "knowledge_added": 0,
            "analysis": None,
            "errors": []
        }

        # 1. 读取 README
        readme_content = self._read_readme(repo_info)
        if readme_content:
            stats["files_read"] += 1

        # 2. 读取核心代码文件
        code_files_content = self._read_core_files(repo_info, max_code_files, max_file_size)
        stats["files_read"] += len(code_files_content)

        # 3. 如果没有 LLM，回退到简单存储
        if self.llm is None:
            print("警告: 没有 LLM provider，使用简单存储模式")
            return self._simple_store(repo_info, readme_content, code_files_content, stats)

        # 4. 用 LLM 分析
        print("正在用 AI 分析代码...")
        try:
            # 构建代码文件内容
            code_text = ""
            for file_path, content in code_files_content.items():
                code_text += f"\n### {file_path}\n```\n{content[:5000]}\n```\n"

            # 构建 prompt
            prompt = ANALYSIS_PROMPT.format(
                repo_name=repo_info.name,
                repo_url=repo_info.url,
                readme_content=readme_content[:8000] if readme_content else "（无 README）",
                code_files=code_text[:20000] if code_text else "（无代码文件）"
            )

            # 调用 LLM (async) - 需要传入 messages 格式
            messages = [{"role": "user", "content": prompt}]
            analysis = await self.llm.chat(messages)

            stats["analysis"] = analysis

            # 5. 存入知识库
            self.kb.add(
                content=analysis,
                knowledge_type=KnowledgeType.GITHUB_EXAMPLE,
                title=f"[学习笔记] {repo_info.name}",
                source=repo_info.url,
                tags=["github", "学习笔记", repo_info.name],
                metadata={
                    "repo_name": repo_info.name,
                    "files_analyzed": stats["files_read"],
                    "analysis_type": "llm"
                }
            )
            stats["knowledge_added"] = 1

            print(f"学习完成: 分析了 {stats['files_read']} 个文件，提炼了 1 条知识")

        except Exception as e:
            stats["errors"].append(f"LLM 分析失败: {e}")
            print(f"LLM 分析失败: {e}")
            # 回退到简单存储
            return self._simple_store(repo_info, readme_content, code_files_content, stats)

        return stats

    def _read_readme(self, repo_info: RepoInfo) -> str:
        """读取 README"""
        for name in ["README.md", "readme.md", "README.rst", "README"]:
            readme_path = repo_info.local_path / name
            if readme_path.exists():
                try:
                    return readme_path.read_text(encoding="utf-8", errors="ignore")
                except:
                    pass
        return ""

    def _read_core_files(
        self,
        repo_info: RepoInfo,
        max_files: int,
        max_file_size: int
    ) -> dict[str, str]:
        """读取核心代码文件"""
        files_content = {}

        # 先找入口文件
        entry_files = ["main.py", "app.py", "index.js", "index.ts", "main.go", "src/main.py", "src/app.py"]
        for entry in entry_files:
            entry_path = repo_info.local_path / entry
            if entry_path.exists() and entry_path.stat().st_size < max_file_size:
                try:
                    content = entry_path.read_text(encoding="utf-8", errors="ignore")
                    files_content[entry] = content
                except:
                    pass

        # 再找其他核心文件
        code_files = []
        for ext in self.CODE_EXTENSIONS:
            for file_path in repo_info.local_path.rglob(f"*{ext}"):
                if any(skip in file_path.parts for skip in self.SKIP_DIRS):
                    continue
                if file_path.stat().st_size < max_file_size:
                    code_files.append(file_path)

        # 按重要性排序（小文件优先，src 目录优先）
        def importance(p):
            score = p.stat().st_size
            if "src" in p.parts:
                score -= 10000
            if p.name in self.IMPORTANT_FILES:
                score -= 20000
            return score

        code_files.sort(key=importance)

        # 读取内容
        for file_path in code_files:
            if len(files_content) >= max_files:
                break
            rel_path = str(file_path.relative_to(repo_info.local_path))
            if rel_path not in files_content:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    files_content[rel_path] = content
                except:
                    pass

        return files_content

    def _simple_store(
        self,
        repo_info: RepoInfo,
        readme_content: str,
        code_files: dict[str, str],
        stats: dict
    ) -> dict:
        """简单存储模式（无 LLM 时的回退）"""
        # 存 README
        if readme_content:
            self.kb.add(
                content=readme_content[:10000],
                knowledge_type=KnowledgeType.DOCUMENTATION,
                title=f"{repo_info.name} - README",
                source=repo_info.url,
                tags=["readme", repo_info.name]
            )
            stats["knowledge_added"] += 1

        # 存核心代码
        for file_path, content in list(code_files.items())[:5]:
            self.kb.add(
                content=f"# {file_path}\n\n```\n{content[:8000]}\n```",
                knowledge_type=KnowledgeType.CODE_PATTERN,
                title=f"{repo_info.name}/{file_path}",
                source=repo_info.url,
                tags=["code", repo_info.name]
            )
            stats["knowledge_added"] += 1

        return stats

    def _cleanup(self, repo_info: RepoInfo):
        """清理临时文件"""
        try:
            if repo_info.local_path.exists():
                shutil.rmtree(repo_info.local_path)
                print(f"已清理: {repo_info.local_path}")
        except Exception as e:
            print(f"清理失败: {e}")


def learn_from_github(
    repo_url: str,
    knowledge_base: Optional[KnowledgeBase] = None,
    llm_provider: Optional["LLMProvider"] = None,
    **kwargs
) -> dict:
    """便捷函数 - 从 GitHub 学习

    Args:
        repo_url: GitHub 仓库 URL
        knowledge_base: 知识库实例
        llm_provider: LLM 提供者（用于智能分析）
        **kwargs: 其他参数

    Returns:
        学习结果统计
    """
    from .knowledge_base import create_knowledge_base

    kb = knowledge_base or create_knowledge_base()
    learner = GitHubLearner(kb, llm_provider=llm_provider)
    return learner.learn_from_url(repo_url, **kwargs)
