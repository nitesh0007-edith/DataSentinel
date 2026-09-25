"""Central configuration for DataSentinel.

Every threshold and path lives here so detection rules never carry magic numbers.
Values can be overridden with environment variables prefixed ``DATASENTINEL_``
(LLM settings use their conventional unprefixed names).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
TEMPLATE_REPO_DIR = BACKEND_ROOT / "app" / "pipeline" / "template_repo"


class DetectionThresholds(BaseModel):
    """Thresholds used by the deterministic anomaly rules."""

    # Row count: absolute fractional change vs baseline.
    row_count_info: float = 0.02
    row_count_warning: float = 0.10
    row_count_critical: float = 0.25

    # Null rate: absolute change in null fraction (0.05 == 5 percentage points).
    null_rate_warning: float = 0.05
    null_rate_critical: float = 0.20

    # Duplicate rate: absolute change in duplicate-row fraction.
    duplicate_warning: float = 0.01
    duplicate_critical: float = 0.05

    # Categorical columns: a value with at least this baseline share that
    # vanishes in the current run is a disappearance.
    category_min_baseline_share: float = 0.01
    categorical_max_unique: int = 50
    # Total variation distance between baseline and current category distributions.
    category_shift_warning: float = 0.10
    category_shift_critical: float = 0.25

    # Numeric columns: fractional change in mean / median.
    numeric_mean_warning: float = 0.10
    numeric_mean_critical: float = 0.50


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DATASENTINEL_",
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore",
    )

    # Root for runtime data, artifacts and the monitored workspace repo.
    home: Path = PROJECT_ROOT
    # Where the monitored pipeline git repository is created. Defaults to <home>/workspace.
    workspace_dir: Path | None = None

    default_rows: int = 110_000
    default_seed: int = 42

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    git_timeout_seconds: int = 20
    test_timeout_seconds: int = 120

    thresholds: DetectionThresholds = Field(default_factory=DetectionThresholds)

    # LLM configuration (unprefixed names, per .env.example)
    llm_provider: str = Field(
        default="heuristic", validation_alias=AliasChoices("LLM_PROVIDER", "DATASENTINEL_LLM_PROVIDER")
    )
    llm_model: str | None = Field(
        default=None, validation_alias=AliasChoices("LLM_MODEL", "DATASENTINEL_LLM_MODEL")
    )
    llm_timeout_seconds: int = Field(
        default=60, validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "DATASENTINEL_LLM_TIMEOUT_SECONDS")
    )
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", validation_alias="OPENAI_BASE_URL")

    # ---- derived paths -------------------------------------------------
    @property
    def data_dir(self) -> Path:
        return self.home / "data"

    @property
    def raw_data_path(self) -> Path:
        return self.data_dir / "generated" / "customers_raw.csv"

    @property
    def current_output_path(self) -> Path:
        return self.data_dir / "current" / "customers_gold.csv"

    @property
    def baseline_output_path(self) -> Path:
        return self.data_dir / "baseline" / "customers_gold.csv"

    @property
    def artifacts_dir(self) -> Path:
        return self.home / "artifacts"

    @property
    def profiles_dir(self) -> Path:
        return self.artifacts_dir / "profiles"

    @property
    def incidents_dir(self) -> Path:
        return self.artifacts_dir / "incidents"

    @property
    def patches_dir(self) -> Path:
        return self.artifacts_dir / "patches"

    @property
    def logs_dir(self) -> Path:
        return self.artifacts_dir / "logs"

    @property
    def state_path(self) -> Path:
        return self.artifacts_dir / "state.json"

    @property
    def pipeline_repo(self) -> Path:
        base = self.workspace_dir if self.workspace_dir else self.home / "workspace"
        return base / "pipeline_repo"

    @property
    def transform_module_path(self) -> str:
        """Repo-relative path of the transformation module the runner executes."""
        return "pipelines/customer_transform.py"

    def ensure_dirs(self) -> None:
        for d in (
            self.data_dir / "generated",
            self.data_dir / "current",
            self.data_dir / "baseline",
            self.profiles_dir,
            self.incidents_dir,
            self.patches_dir,
            self.logs_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
