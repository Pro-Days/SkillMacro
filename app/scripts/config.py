from __future__ import annotations

import os
from dataclasses import dataclass
from typing import ClassVar

from app.scripts.registry.key_registry import KeyRegistry, KeySpec


def _env_flag(name: str) -> bool:
    value: str | None = os.getenv(name)

    if value is None:
        return False

    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


@dataclass(frozen=True)
class UiConfig:
    DEFAULT_WINDOW_WIDTH: ClassVar[int] = 960
    DEFAULT_WINDOW_HEIGHT: ClassVar[int] = 540

    analysis_card_colors: ClassVar[tuple[str, ...]] = (
        "255, 130, 130",  # #FF8282
        "255, 230, 140",  # #FFE68C
        "170, 230, 255",  # #AAE6FF
        "150, 225, 210",  # #96E1D2
    )

    debug_colors: ClassVar[bool] = _env_flag("SKILLMACRO_DEBUG_COLORS")


@dataclass(frozen=True)
class MacroConfig:
    # AFK 모드 활성화 여부: 정식 버전에서는 True로 변경
    is_afk_enabled: ClassVar[bool] = True

    # 버전 확인 모드 활성화 여부: 정식 버전에서는 True로 변경
    is_version_check_enabled: ClassVar[bool] = True

    # 이 계수를 조정하여 time.sleep과 실제 시간 간의 괴리를 조정
    # todo: 다른 방식으로 조정하도록 변경
    SLEEP_COEFFICIENT_NORMAL: ClassVar[float] = 1.0
    SLEEP_COEFFICIENT_UNIT: ClassVar[float] = 1.0
    # SLEEP_COEFFICIENT_NORMAL: ClassVar[float] = 0.975
    # SLEEP_COEFFICIENT_UNIT: ClassVar[float] = 0.97


@dataclass(frozen=True)
class SettingSpec:
    """설정 항목 하나에 대한 기준을 담는 클래스"""

    label: str
    default: int
    min: int
    max: int


@dataclass(frozen=True)
class MacroSpecs:
    """모든 매크로 설정의 기준들을 모아둔 클래스"""

    # 기타 설정
    DELAY: ClassVar[SettingSpec] = SettingSpec(
        label="딜레이", default=300, min=50, max=1000
    )
    COOLTIME_REDUCTION: ClassVar[SettingSpec] = SettingSpec(
        label="스킬속도(%)", default=0, min=0, max=90
    )

    DEFAULT_START_KEY: ClassVar[KeySpec] = KeyRegistry.get("f9")
    DEFAULT_SWAP_KEY: ClassVar[KeySpec] = KeyRegistry.get("h")

    DEFAULT_SERVER_ID: ClassVar[str] = "한월 RPG"


@dataclass(frozen=True)
class AppConfig:
    version: ClassVar[str] = "v1.0.0"
    app_name: ClassVar[str] = "PD SkillMacro"

    ui: ClassVar[UiConfig] = UiConfig()
    macro: ClassVar[MacroConfig] = MacroConfig()
    specs: ClassVar[MacroSpecs] = MacroSpecs()


config = AppConfig()
