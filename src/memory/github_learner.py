"""GitHub Learner - 从 GitHub 仓库学习

功能：
- Clone 仓库
- 分析代码结构
- 提取重要代码片段
- 存入知识库
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .knowledge_base import KnowledgeBase, Knowledge, KnowledgeType


@dataclass
class RepoInfo:
    """仓库信息"""
    url: str
    name: str
    local_path: Path
    language: Optional[str] = None
    description: str = ""


class GitHubLearner:
    """GitHub 学习器

    从 GitHub 仓库中提取知识并存入知识库
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
        ".idea", ".vscode", "coverage", ".pytest_cache"
    }

    # 重要文件（优先分析）
    IMPORTANT_FILES = {
        "README.md", "readme.md", "README.rst",
        "setup.py", "pyproject.toml", "package.json",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        "Makefile", "Dockerfile", "docker-compose.yml",
        "main.py", "app.py", "index.js", "index.ts", "main.go"
    }

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        workspace_dir: str = "data/github_workspace"
    ):
        """初始化

        Args:
            knowledge_base: 知识库实例
            workspace_dir: 临时工作目录
        """
        self.kb = knowledge_base
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def learn_from_url(
        self,
        repo_url: str,
        max_files: int = 50,
        max_file_size: int = 50000,  # 50KB
        cleanup: bool = True
    ) -> dict:
        """从 GitHub URL 学习

        Args:
            repo_url: GitHub 仓库 URL
            max_files: 最大分析文件数
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
            # 分析仓库
            result = self._analyze_repo(repo_info, max_files, max_file_size)
            return result
        finally:
            # 清理
            if cleanup:
                self._cleanup(repo_info)

    def learn_from_local(
        self,
        local_path: str,
        repo_name: str = "",
        max_files: int = 50,
        max_file_size: int = 50000
    ) -> dict:
        """从本地目录学习

        Args:
            local_path: 本地目录路径
            repo_name: 仓库名称
            max_files: 最大分析文件数
            max_file_size: 最大文件大小

        Returns:
            学习结果统计
        """
        path = Path(local_path)
        if not path.exists():
            return {"error": f"路径不存在: {local_path}"}

        repo_info = RepoInfo(
            url=f"local://{local_path}",
            name=repo_name or path.name,
            local_path=path
        )

        return self._analyze_repo(repo_info, max_files, max_file_size)

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
                timeout=120  # 2分钟超时
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

    def _analyze_repo(
        self,
        repo_info: RepoInfo,
        max_files: int,
        max_file_size: int
    ) -> dict:
        """分析仓库"""
        stats = {
            "repo": repo_info.name,
            "url": repo_info.url,
            "files_analyzed": 0,
            "knowledge_added": 0,
            "languages": set(),
            "errors": []
        }

        # 1. 先处理 README
        self._process_readme(repo_info, stats)

        # 2. 分析重要文件
        important_files = self._find_important_files(repo_info.local_path)
        for file_path in important_files[:10]:  # 最多 10 个重要文件
            self._process_file(file_path, repo_info, stats, max_file_size)

        # 3. 分析代码文件
        code_files = self._find_code_files(repo_info.local_path)
        remaining = max_files - stats["files_analyzed"]

        for file_path in code_files[:remaining]:
            self._process_file(file_path, repo_info, stats, max_file_size)

        stats["languages"] = list(stats["languages"])
        print(f"学习完成: 分析 {stats['files_analyzed']} 个文件，添加 {stats['knowledge_added']} 条知识")
        return stats

    def _find_important_files(self, root_path: Path) -> list[Path]:
        """查找重要文件"""
        files = []
        for name in self.IMPORTANT_FILES:
            file_path = root_path / name
            if file_path.exists():
                files.append(file_path)
        return files

    def _find_code_files(self, root_path: Path) -> list[Path]:
        """查找代码文件"""
        files = []

        for ext in self.CODE_EXTENSIONS:
            for file_path in root_path.rglob(f"*{ext}"):
                # 跳过特定目录
                if any(skip in file_path.parts for skip in self.SKIP_DIRS):
                    continue
                files.append(file_path)

        # 按文件大小排序（小文件优先，可能更有代表性）
        files.sort(key=lambda p: p.stat().st_size)
        return files

    def _process_readme(self, repo_info: RepoInfo, stats: dict):
        """处理 README"""
        for name in ["README.md", "readme.md", "README.rst", "README"]:
            readme_path = repo_info.local_path / name
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding="utf-8", errors="ignore")
                    if content.strip():
                        # 添加为文档知识
                        self.kb.add(
                            content=content[:10000],  # 限制长度
                            knowledge_type=KnowledgeType.DOCUMENTATION,
                            title=f"{repo_info.name} - README",
                            source=repo_info.url,
                            tags=["readme", "documentation", repo_info.name]
                        )
                        stats["knowledge_added"] += 1
                        stats["files_analyzed"] += 1
                except Exception as e:
                    stats["errors"].append(f"README 处理失败: {e}")
                break

    def _process_file(
        self,
        file_path: Path,
        repo_info: RepoInfo,
        stats: dict,
        max_file_size: int
    ):
        """处理单个文件"""
        try:
            # 检查文件大小
            if file_path.stat().st_size > max_file_size:
                return

            # 读取内容
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                return

            # 获取相对路径
            rel_path = file_path.relative_to(repo_info.local_path)

            # 确定语言
            ext = file_path.suffix.lower()
            language = self.CODE_EXTENSIONS.get(ext, "Unknown")
            stats["languages"].add(language)

            # 确定知识类型
            knowledge_type = KnowledgeType.CODE_PATTERN
            if file_path.name in self.IMPORTANT_FILES:
                knowledge_type = KnowledgeType.BEST_PRACTICE

            # 构建知识内容
            knowledge_content = f"""# {rel_path}
Language: {language}
Repository: {repo_info.name}

```{ext[1:] if ext else ''}
{content[:8000]}
```
"""

            # 添加到知识库
            self.kb.add(
                content=knowledge_content,
                knowledge_type=knowledge_type,
                title=f"{repo_info.name}/{rel_path}",
                source=repo_info.url,
                tags=[language.lower(), repo_info.name, ext[1:] if ext else "unknown"],
                metadata={
                    "file_path": str(rel_path),
                    "language": language,
                    "size": len(content)
                }
            )

            stats["files_analyzed"] += 1
            stats["knowledge_added"] += 1

        except Exception as e:
            stats["errors"].append(f"{file_path}: {e}")

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
    **kwargs
) -> dict:
    """便捷函数 - 从 GitHub 学习

    Args:
        repo_url: GitHub 仓库 URL
        knowledge_base: 知识库实例（可选，会自动创建）
        **kwargs: 传递给 learn_from_url 的参数

    Returns:
        学习结果统计
    """
    from .knowledge_base import create_knowledge_base

    kb = knowledge_base or create_knowledge_base()
    learner = GitHubLearner(kb)
    return learner.learn_from_url(repo_url, **kwargs)
