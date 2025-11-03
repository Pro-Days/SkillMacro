from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


# @dataclass(frozen=True)
# class BuildConfig:
#     version: str = "3.1.0-beta.2"


@dataclass(frozen=True)
class UiConfig:
    # test_mode: bool = _env_flag("SKILLMACRO_TEST_MODE")
    debug_colors: bool = _env_flag("SKILLMACRO_DEBUG_COLORS")
    # default_width: int = 928
    # default_height: int = 720


# @dataclass(frozen=True)
# class TimingConfig:
#     unit_time: float = 0.05
#     min_delay: int = 50
#     max_delay: int = 1000
#     default_delay: int = 150
#     sleep_coeff_normal: float = 0.975
#     sleep_coeff_unit: float = 0.97


# @dataclass(frozen=True)
# class PathsConfig:
#     data_dir: str = "resources/data"
#     image_dir: str = "resources/image"
#     backup_file: str = "resources/data/skill_data.json.backup"


@dataclass(frozen=True)
class AppConfig:
    # build: BuildConfig = BuildConfig()
    ui: UiConfig = UiConfig()
    # timing: TimingConfig = TimingConfig()
    # paths: PathsConfig = PathsConfig()

    # ENV_PREFIX: ClassVar[str] = "SKILLMACRO_"


config = AppConfig()
