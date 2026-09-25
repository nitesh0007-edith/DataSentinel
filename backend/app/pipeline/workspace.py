"""The monitored pipeline repository ("workspace").

DataSentinel monitors a small, real git repository holding the pipeline's
transformation code. It is rebuilt from ``template_repo`` on every demo reset so
the demo is deterministic, and incidents/fixes are real git commits inside it,
never in the DataSentinel project's own history.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import TEMPLATE_REPO_DIR, Settings
from app.core.errors import UnsafeOperationError
from app.core.logging import get_logger
from app.investigation.git_analyzer import GitRepository

log = get_logger("workspace")

PLATFORM_AUTHOR = ("Data Platform", "platform@datasentinel.example")


def resolve_in_repo(repo: Path, rel_path: str) -> Path:
    """Resolve a repo-relative path, refusing anything outside the repo or inside .git."""
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts or not rel_path:
        raise UnsafeOperationError(f"Path '{rel_path}' is not a repository-relative path")
    root = repo.resolve()
    target = (root / rel).resolve()
    if not target.is_relative_to(root):
        raise UnsafeOperationError(f"Path '{rel_path}' escapes the pipeline repository")
    if ".git" in target.relative_to(root).parts:
        raise UnsafeOperationError("Writes into .git are not allowed")
    return target


def reset_workspace(settings: Settings) -> GitRepository:
    repo_dir = settings.pipeline_repo
    if repo_dir.exists():
        # Only ever delete the dedicated workspace directory we created.
        if repo_dir.name != "pipeline_repo":
            raise UnsafeOperationError(f"Refusing to delete unexpected directory {repo_dir}")
        shutil.rmtree(repo_dir)
    repo_dir.mkdir(parents=True)

    git = GitRepository(repo_dir, timeout=settings.git_timeout_seconds)
    git.init()

    # Commit 1: pipeline code
    shutil.copytree(TEMPLATE_REPO_DIR / "pipelines", repo_dir / "pipelines", ignore=_ignore_cache)
    shutil.copy(TEMPLATE_REPO_DIR / "README.md", repo_dir / "README.md")
    shutil.copy(TEMPLATE_REPO_DIR / "gitignore.template", repo_dir / ".gitignore")
    git.commit_all("feat: customer revenue pipeline (bronze/silver/gold)", *PLATFORM_AUTHOR)

    # Commit 2: regression tests
    shutil.copytree(TEMPLATE_REPO_DIR / "tests", repo_dir / "tests", ignore=_ignore_cache)
    git.commit_all("test: add transformation regression tests", *PLATFORM_AUTHOR)

    log.info("Pipeline workspace reset at %s (HEAD %s)", repo_dir, git.head(short=True))
    return git


def _ignore_cache(_dir: str, names: list[str]) -> list[str]:
    return [n for n in names if n in {"__pycache__", ".pytest_cache"} or n.endswith(".pyc")]


def workspace_git(settings: Settings) -> GitRepository:
    return GitRepository(settings.pipeline_repo, timeout=settings.git_timeout_seconds)
