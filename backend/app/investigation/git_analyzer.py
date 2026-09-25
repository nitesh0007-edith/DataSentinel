"""Safe, read-mostly Git inspection.

Only a fixed allowlist of git subcommands can run, always as an argument list
(never through a shell), with a timeout, against a single repository path.
Revision arguments are validated so user-supplied text never reaches git as an
option or arbitrary expression.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from app.core.errors import DataSentinelError, UnsafeOperationError
from app.core.logging import get_logger
from app.core.models import CommitEvidence, CommitInfo, DiffHunk, DiffLine

log = get_logger("git")

READ_COMMANDS = {"log", "diff", "show", "rev-parse", "status", "cat-file"}
WRITE_COMMANDS = {"init", "add", "commit"}
_REF_RE = re.compile(r"^(?:[0-9a-fA-F]{4,40}|HEAD(?:~\d{1,3})?)$")
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"

# Hooks and signing from the host's global git config must not affect the demo repo.
_SAFE_CONFIG = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "commit.gpgsign=false",
    "-c", "core.quotepath=false",
    "-c", "color.ui=false",
]


class GitError(DataSentinelError):
    status_code = 500


def validate_ref(ref: str) -> str:
    if not _REF_RE.match(ref):
        raise UnsafeOperationError(f"Rejected git revision '{ref}'")
    return ref


def validate_repo_path(path: str) -> str:
    """Repo-relative path: no absolute paths, no traversal, no option injection."""
    p = Path(path)
    if p.is_absolute() or ".." in p.parts or path.startswith("-") or not path:
        raise UnsafeOperationError(f"Rejected repository path '{path}'")
    return p.as_posix()


class GitRepository:
    def __init__(self, repo_path: Path, timeout: int = 20) -> None:
        self.repo_path = repo_path
        self.timeout = timeout
        self.git_bin = shutil.which("git")
        if not self.git_bin:
            raise GitError("git executable not found on PATH")

    # ------------------------------------------------------------ plumbing
    def _run(self, args: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> str:
        if not args or args[0] not in READ_COMMANDS | WRITE_COMMANDS:
            raise UnsafeOperationError(f"git subcommand not allowed: {args[:1]}")
        cmd = [self.git_bin, "-C", str(self.repo_path), *_SAFE_CONFIG, *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=False,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitError(f"git {args[0]} timed out") from exc
        if check and proc.returncode != 0:
            raise GitError(f"git {args[0]} failed: {proc.stderr.strip()[:500]}")
        return proc.stdout

    def is_repo(self) -> bool:
        if not (self.repo_path / ".git").exists():
            return False
        try:
            self._run(["rev-parse", "--is-inside-work-tree"])
            return True
        except DataSentinelError:
            return False

    # ------------------------------------------------------------ writes (internal use only)
    def init(self) -> None:
        self.repo_path.mkdir(parents=True, exist_ok=True)
        self._run(["init", "-q", "-b", "main"])

    def commit_all(self, message: str, author_name: str, author_email: str) -> str:
        import os

        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
        }
        self._run(["add", "-A"], env=env)
        self._run(["commit", "-q", "-m", message], env=env)
        return self.head()

    def stage_file(self, path: str) -> None:
        self._run(["add", "--", validate_repo_path(path)])

    def commit_staged(self, message: str, author_name: str, author_email: str) -> str:
        import os

        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
        }
        self._run(["commit", "-q", "-m", message], env=env)
        return self.head()

    # ------------------------------------------------------------ reads
    def head(self, short: bool = False) -> str:
        args = ["rev-parse", "--short", "HEAD"] if short else ["rev-parse", "HEAD"]
        return self._run(args).strip()

    def is_clean(self) -> bool:
        return self._run(["status", "--porcelain"]).strip() == ""

    def recent_commits(self, limit: int = 10) -> list[CommitInfo]:
        limit = max(1, min(int(limit), 50))
        fmt = _FIELD_SEP.join(["%H", "%h", "%an <%ae>", "%aI", "%s"]) + _RECORD_SEP
        out = self._run(["log", f"-{limit}", f"--pretty=format:{fmt}"])
        return _parse_commits(out)

    def commits_between(self, base: str, head: str = "HEAD") -> list[CommitInfo]:
        validate_ref(base)
        validate_ref(head)
        fmt = _FIELD_SEP.join(["%H", "%h", "%an <%ae>", "%aI", "%s"]) + _RECORD_SEP
        out = self._run(["log", f"--pretty=format:{fmt}", f"{base}..{head}"])
        return _parse_commits(out)

    def commit_info(self, ref: str) -> CommitInfo:
        validate_ref(ref)
        fmt = _FIELD_SEP.join(["%H", "%h", "%an <%ae>", "%aI", "%s"]) + _RECORD_SEP
        out = self._run(["log", "-1", f"--pretty=format:{fmt}", ref])
        commits = _parse_commits(out)
        if not commits:
            raise GitError(f"commit {ref} not found")
        return commits[0]

    def changed_files(self, ref: str) -> list[str]:
        validate_ref(ref)
        out = self._run(["show", "--pretty=format:", "--name-only", ref])
        return [line.strip() for line in out.splitlines() if line.strip()]

    def show_diff(self, ref: str) -> str:
        """Unified diff introduced by a single commit."""
        validate_ref(ref)
        return self._run(["show", "--pretty=format:", "--unified=3", "--no-ext-diff", ref])

    def diff(self, base: str, head: str = "HEAD") -> str:
        validate_ref(base)
        validate_ref(head)
        return self._run(["diff", "--unified=3", "--no-ext-diff", base, head])

    def file_at(self, ref: str, path: str) -> str:
        validate_ref(ref)
        rel = validate_repo_path(path)
        return self._run(["show", f"{ref}:{rel}"])

    def commit_evidence(self, ref: str) -> CommitEvidence:
        info = self.commit_info(ref)
        diff = self.show_diff(info.sha)
        return CommitEvidence(
            commit=info,
            changed_files=self.changed_files(info.sha),
            diff=diff,
            hunks=parse_unified_diff(diff),
        )


def _parse_commits(out: str) -> list[CommitInfo]:
    commits: list[CommitInfo] = []
    for record in out.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(_FIELD_SEP)
        if len(parts) != 5:
            continue
        sha, short, author, date, message = parts
        commits.append(CommitInfo(sha=sha, short_sha=short, author=author, date=date, message=message))
    return commits


def parse_unified_diff(diff: str) -> list[DiffHunk]:
    """Parse unified diff text into hunks with old/new line numbers."""
    hunks: list[DiffHunk] = []
    current_file: str | None = None
    hunk: DiffHunk | None = None
    old_no = new_no = 0
    for raw in diff.splitlines():
        if raw.startswith("diff --git"):
            hunk = None
            continue
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            current_file = None if target == "/dev/null" else target.removeprefix("b/")
            continue
        if raw.startswith("--- "):
            continue
        m = _HUNK_RE.match(raw)
        if m and current_file:
            old_start, old_count = int(m.group(1)), int(m.group(2) or 1)
            new_start, new_count = int(m.group(3)), int(m.group(4) or 1)
            hunk = DiffHunk(
                file=current_file,
                header=raw,
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                lines=[],
            )
            hunks.append(hunk)
            old_no, new_no = old_start, new_start
            continue
        if hunk is None or not raw or raw.startswith("\\"):
            continue
        kind, content = raw[0], raw[1:]
        if kind == "+":
            hunk.lines.append(DiffLine(kind="+", content=content, new_lineno=new_no))
            new_no += 1
        elif kind == "-":
            hunk.lines.append(DiffLine(kind="-", content=content, old_lineno=old_no))
            old_no += 1
        elif kind == " ":
            hunk.lines.append(DiffLine(kind=" ", content=content, old_lineno=old_no, new_lineno=new_no))
            old_no += 1
            new_no += 1
    return hunks
