"""Generate a remediation patch from the RCA finding.

Strategy (deterministic and conservative): reverse the diff hunks that the
suspect commit introduced in the implicated file, restoring the last known-good
code. The patch is only *proposed* here; nothing on disk changes.
"""

from __future__ import annotations

import difflib
import hashlib

from app.core.config import Settings
from app.core.errors import ConflictError
from app.core.models import DiffHunk, EvidencePackage, PatchProposal, RootCauseAnalysis
from app.core.state import write_text_atomic
from app.pipeline.workspace import resolve_in_repo


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _find_block(lines: list[str], block: list[str], hint: int) -> int:
    """Index where ``block`` occurs in ``lines``, preferring the position closest to ``hint``."""
    n = len(block)
    matches = [i for i in range(len(lines) - n + 1) if lines[i : i + n] == block]
    if not matches:
        return -1
    return min(matches, key=lambda i: abs(i - hint))


def reverse_hunks(content: str, hunks: list[DiffHunk]) -> str:
    lines = content.splitlines()
    # Apply bottom-up so earlier positions stay valid.
    for hunk in sorted(hunks, key=lambda h: h.new_start, reverse=True):
        new_side = [line.content for line in hunk.lines if line.kind in (" ", "+")]
        old_side = [line.content for line in hunk.lines if line.kind in (" ", "-")]
        idx = _find_block(lines, new_side, hunk.new_start - 1)
        if idx < 0:
            raise ConflictError(
                f"Cannot build patch: code introduced by the suspect commit is no longer present in {hunk.file}."
            )
        lines[idx : idx + len(new_side)] = old_side
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def generate_patch(
    settings: Settings, incident_id: str, patch_id: str, rca: RootCauseAnalysis, evidence: EvidencePackage
) -> PatchProposal:
    if rca.insufficient_evidence or not rca.file or not rca.commit:
        raise ConflictError("Root cause is not specific enough (no file/commit) to propose a safe code fix.")

    commit_ev = next((ce for ce in evidence.commits_since_baseline if ce.commit.sha == rca.commit), None)
    if commit_ev is None:
        raise ConflictError(f"Commit {rca.commit[:7]} is not part of the collected evidence.")
    hunks = [h for h in commit_ev.hunks if h.file == rca.file]
    if not hunks:
        raise ConflictError(f"Commit {rca.commit[:7]} did not change {rca.file}.")

    path = resolve_in_repo(settings.pipeline_repo, rca.file)
    current = path.read_text(encoding="utf-8")
    proposed = reverse_hunks(current, hunks)
    if proposed == current:
        raise ConflictError("Proposed patch would not change the file.")

    diff = "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"a/{rca.file}",
            tofile=f"b/{rca.file}",
            n=3,
        )
    )
    diff_path = settings.patches_dir / f"{patch_id}.diff"
    write_text_atomic(diff_path, diff)
    write_text_atomic(settings.patches_dir / f"{patch_id}.proposed", proposed)

    return PatchProposal(
        patch_id=patch_id,
        incident_id=incident_id,
        file=rca.file,
        commit_reverted=rca.commit,
        description=(
            f"Revert the {len(hunks)} change(s) commit {rca.commit[:7]} made to {rca.file}, "
            f"restoring the last known-good code. {rca.recommended_fix}"
        ),
        diff=diff,
        base_sha256=sha256_text(current),
        proposed_sha256=sha256_text(proposed),
        diff_path=str(diff_path),
    )
