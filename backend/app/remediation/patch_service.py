"""Safely apply or roll back a remediation patch.

apply_patch safety guarantees:
* only a patch in PROPOSED state can be applied (explicit user action);
* the target must resolve inside the pipeline repository, never .git;
* only Python source files may be modified;
* the file must be byte-for-byte what the patch was generated against;
* the stored proposed content must match its recorded hash;
* the change is committed, so it is auditable and revertible.

rollback_patch safety guarantees:
* only a patch in APPLIED state can be rolled back (explicit operator action);
* restores the file from the .orig backup written during apply;
* verifies the restore content matches the recorded base_sha256;
* commits the rollback with a distinct message for auditability;
* prevents double rollback.
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


def rollback_patch(settings: Settings, patch: PatchProposal, incident_type: str) -> PatchProposal:
    """Explicitly restore the pre-fix source and commit a revert.

    Only an APPLIED patch may be rolled back.  The original file content is
    taken from the .orig backup written during apply_patch, and its hash is
    verified against base_sha256 to ensure the backup was not tampered with.
    """
    if patch.status != "APPLIED":
        raise ConflictError(
            f"Patch {patch.patch_id} is {patch.status}; only APPLIED patches can be rolled back."
        )

    orig_path = settings.patches_dir / f"{patch.patch_id}.orig"
    if not orig_path.is_file():
        raise ConflictError(
            f"Original backup for patch {patch.patch_id} not found; cannot roll back safely."
        )

    original = orig_path.read_text(encoding="utf-8")
    if sha256_text(original) != patch.base_sha256:
        raise UnsafeOperationError(
            "Backup content does not match the recorded base hash; refusing rollback."
        )

    target = resolve_in_repo(settings.pipeline_repo, patch.file)
    if not target.is_file():
        raise ConflictError(f"{patch.file} does not exist in the pipeline repository.")

    git = workspace_git(settings)
    if not git.is_clean():
        raise ConflictError(
            "Pipeline repository has uncommitted changes; cannot roll back the patch."
        )

    applied_short = patch.applied_commit[:7] if patch.applied_commit else "unknown"
    current = target.read_text(encoding="utf-8")
    try:
        write_text_atomic(target, original)
        git.stage_file(patch.file)
        sha = git.commit_staged(
            f"revert: roll back failed fix {patch.patch_id} ({incident_type}) "
            f"[was {applied_short}] [DataSentinel {patch.incident_id}]",
            *BOT_AUTHOR,
        )
    except Exception:
        # Restore whatever was on disk before our rollback attempt.
        write_text_atomic(target, current)
        git.stage_file(patch.file)
        raise

    log.info(
        "Rolled back patch %s on %s as commit %s (reverting %s)",
        patch.patch_id, patch.file, sha[:7], applied_short,
    )
    return patch.model_copy(
        update={"status": "ROLLED_BACK", "rolled_back_at": utcnow(), "rollback_commit": sha}
    )
