"""Safely apply a previously proposed patch.

Safety guarantees:
* only a patch in PROPOSED state can be applied (explicit user action);
* the target must resolve inside the pipeline repository, never .git;
* only Python source files may be modified;
* the file must be byte-for-byte what the patch was generated against;
* the stored proposed content must match its recorded hash;
* the change is committed, so it is auditable and revertible.
"""

from __future__ import annotations

import shutil

from app.core.config import Settings
from app.core.errors import ConflictError, UnsafeOperationError
from app.core.logging import get_logger
from app.core.models import PatchProposal, utcnow
from app.core.state import write_text_atomic
from app.pipeline.workspace import resolve_in_repo, workspace_git
from app.remediation.patch_generator import sha256_text

log = get_logger("patch")

ALLOWED_SUFFIXES = {".py"}
BOT_AUTHOR = ("DataSentinel", "datasentinel-bot@datasentinel.example")


def apply_patch(settings: Settings, patch: PatchProposal, incident_type: str) -> PatchProposal:
    if patch.status != "PROPOSED":
        raise ConflictError(f"Patch {patch.patch_id} is {patch.status}; only PROPOSED patches can be applied.")

    target = resolve_in_repo(settings.pipeline_repo, patch.file)
    if target.suffix not in ALLOWED_SUFFIXES:
        raise UnsafeOperationError(f"Patching {target.suffix} files is not allowed")
    if not target.is_file():
        raise ConflictError(f"{patch.file} does not exist")

    current = target.read_text(encoding="utf-8")
    if sha256_text(current) != patch.base_sha256:
        raise ConflictError(f"{patch.file} changed since the patch was proposed. Regenerate the fix.")

    proposed_path = settings.patches_dir / f"{patch.patch_id}.proposed"
    proposed = proposed_path.read_text(encoding="utf-8")
    if sha256_text(proposed) != patch.proposed_sha256:
        raise UnsafeOperationError("Stored patch content does not match its recorded hash.")

    git = workspace_git(settings)
    if not git.is_clean():
        raise ConflictError("Pipeline repository has uncommitted changes; cannot apply the patch.")
    shutil.copyfile(target, settings.patches_dir / f"{patch.patch_id}.orig")
    reverted = patch.commit_reverted[:7] if patch.commit_reverted else "change"
    try:
        write_text_atomic(target, proposed)
        git.stage_file(patch.file)
        sha = git.commit_staged(
            f"fix: revert {reverted} ({incident_type}) [DataSentinel {patch.incident_id}]",
            *BOT_AUTHOR,
        )
    except Exception:
        write_text_atomic(target, current)
        git.stage_file(patch.file)
        raise
    log.info("Applied patch %s to %s as commit %s", patch.patch_id, patch.file, sha[:7])
    return patch.model_copy(update={"status": "APPLIED", "applied_at": utcnow(), "applied_commit": sha})
