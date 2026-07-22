import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from app.paths import BASE_DIR, CONFIG_PATH, FRONTEND_DIST

# Backwards-compatible alias: writable root for db/data resolution.
PROJECT_ROOT = BASE_DIR


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///./data/omr.db"


class DropzoneConfig(BaseModel):
    path: str = "C:\\OMR_Dropzone\\"
    lock_suffix: str = ".omr_lock"
    accepted_extensions: list[str] = Field(
        default_factory=lambda: [".jpg", ".jpeg", ".tiff", ".tif", ".pdf"]
    )


class ProcessingConfig(BaseModel):
    max_workers: int = 4
    target_seconds_per_page: float = 1.5
    auto_resume_batches: bool = False
    auto_resume_ingestion: bool = False
    stale_processing_seconds: int = 120
    worker_cap_by_ram: bool = False


class OmrContourConfig(BaseModel):
    min_grid_confidence: float = 0.70
    min_sheet_detection_ratio: float = 0.75
    min_mark_pixels: float = 40.0
    max_match_distance_px: float = 14.0


class OmrArbitrationConfig(BaseModel):
    min_consensus_margin: float = 0.15


class OmrPerfConfig(BaseModel):
    shared_otsu: bool = True
    roi_contours_only: bool = True
    skip_contour_on_low_grid: bool = True


class OmrConfig(BaseModel):
    strict_review: bool = False
    fill_threshold: float = 40.0
    dynamic_threshold: bool = True
    blank_threshold: float = 18.0
    multi_mark_threshold: float = 10.0
    comfort_margin: float = 28.0
    comfort_ratio: float = 1.35
    alignment_review_below: float = 0.72
    read_mode: str = "hybrid"
    contour: OmrContourConfig = Field(default_factory=OmrContourConfig)
    arbitration: OmrArbitrationConfig = Field(default_factory=OmrArbitrationConfig)
    perf: OmrPerfConfig = Field(default_factory=OmrPerfConfig)


class ExportConfig(BaseModel):
    default_mode: str = "literal"


class AppConfig(BaseSettings):
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    dropzone: DropzoneConfig = Field(default_factory=DropzoneConfig)
    omr: OmrConfig = Field(default_factory=OmrConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)

    @property
    def database_path(self) -> Path:
        url = self.database.url
        if url.startswith("sqlite:///"):
            rel = url.replace("sqlite:///", "")
            path = Path(rel)
            if not path.is_absolute():
                path = BASE_DIR / path
            return path
        return BASE_DIR / "data" / "omr.db"

    @property
    def frontend_dist(self) -> Path:
        return FRONTEND_DIST


def _load_yaml_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _apply_test_overrides(cfg: AppConfig) -> AppConfig:
    if os.environ.get("OMR_TEST_MODE") != "1":
        return cfg
    if db_url := os.environ.get("OMR_DATABASE_URL"):
        cfg.database.url = db_url
    if dropzone := os.environ.get("OMR_DROPZONE_PATH"):
        cfg.dropzone.path = dropzone
    return cfg


@lru_cache
def get_config() -> AppConfig:
    return _apply_test_overrides(AppConfig(**_load_yaml_config()))


def reload_config() -> AppConfig:
    get_config.cache_clear()
    return get_config()
