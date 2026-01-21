from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import ClassVar

from app.scripts.registry.key_registry import KeyRegistry, KeySpec
from app.scripts.registry.server_registry import ServerSpec, server_registry


def _env_flag(name: str) -> bool:
    value: str | None = os.getenv(name)

    if value is None:
        return False

    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


@dataclass(frozen=True)
class UiConfig:
    DEFAULT_WINDOW_WIDTH: ClassVar[int] = 960
    DEFAULT_WINDOW_HEIGHT: ClassVar[int] = 540

    sim_colors4: ClassVar[tuple[str, ...]] = (
        "255, 130, 130",  # #FF8282
        "255, 230, 140",  # #FFE68C
        "170, 230, 255",  # #AAE6FF
        "150, 225, 210",  # #96E1D2
    )

    debug_colors: ClassVar[bool] = _env_flag("SKILLMACRO_DEBUG_COLORS")


@dataclass(frozen=True)
class SimulationConfig:
    # 전투력 계수
    coef_boss_dmg: ClassVar[float] = 1.0
    coef_normal_dmg: ClassVar[float] = 1.3
    coef_boss: ClassVar[float] = 0.0002
    coef_normal: ClassVar[float] = 0.7

    # 전투력 종류
    power_titles: ClassVar[tuple[str, ...]] = (
        "보스데미지",
        "일반데미지",
        "보스",
        "사냥",
    )
    # 전투력 세부정보 표시 항목
    power_details: ClassVar[tuple[str, ...]] = (
        "min",
        "max",
        "std",
        "p25",
        "p50",
        "p75",
    )

    stats_counts: ClassVar[int] = 18
    skill_levels_counts: ClassVar[int] = 8
    sim_details_counts: ClassVar[int] = 3


@dataclass(frozen=True)
class MacroConfig:
    # AFK 모드 활성화 여부: 정식 버전에서는 True로 변경
    is_afk_enabled: ClassVar[bool] = False

    # 버전 확인 모드 활성화 여부: 정식 버전에서는 True로 변경
    is_version_check_enabled: ClassVar[bool] = False

    # 이 계수를 조정하여 time.sleep과 실제 시간 간의 괴리를 조정
    # todo: 다른 방식으로 조정하도록 변경
    SLEEP_COEFFICIENT_NORMAL: ClassVar[float] = 0.975
    SLEEP_COEFFICIENT_UNIT: ClassVar[float] = 0.97


@dataclass(frozen=True)
class PotentialSpec:
    """잠재능력 수치 정보를 담는 클래스"""

    values: tuple[int, ...]


# 미리 정의된 잠재능력 수치들
POTENTIAL_123 = PotentialSpec(values=(1, 2, 3))
POTENTIAL_246 = PotentialSpec(values=(2, 4, 6))


@dataclass(frozen=True)
class SettingSpec:
    """설정 항목 하나에 대한 기준을 담는 클래스"""

    label: str
    default: int
    min: int
    max: int
    potential: PotentialSpec | None = None


@dataclass(frozen=True)
class ChoiceSpec:
    """선택지 항목에 대한 기준을 담는 클래스"""

    label: str
    choices: tuple[ServerSpec, ...]
    default: ServerSpec


@dataclass(frozen=True)
class MacroSpecs:
    """모든 매크로 설정의 기준들을 모아둔 클래스"""

    # 스탯 설정
    STATS: ClassVar[dict[str, SettingSpec]] = {
        "ATK": SettingSpec(label="공격력", default=1, min=1, max=10000),
        "DEF": SettingSpec(label="방어력", default=1, min=1, max=10000),
        "PWR": SettingSpec(label="파괴력", default=1, min=1, max=10000),
        "STR": SettingSpec(label="근력", default=1, min=1, max=10000),
        "INT": SettingSpec(label="지력", default=1, min=1, max=10000),
        "RES": SettingSpec(
            label="경도", default=1, min=1, max=10000, potential=POTENTIAL_123
        ),
        "CRIT_RATE": SettingSpec(
            label="치명타확률", default=0, min=0, max=10000, potential=POTENTIAL_123
        ),
        "CRIT_DMG": SettingSpec(
            label="치명타데미지", default=0, min=0, max=10000, potential=POTENTIAL_246
        ),
        "BOSS_DMG": SettingSpec(
            label="보스데미지", default=0, min=0, max=10000, potential=POTENTIAL_123
        ),
        "ACC": SettingSpec(label="명중률", default=0, min=0, max=10000),
        "DODGE": SettingSpec(label="회피율", default=0, min=0, max=10000),
        "STATUS_RES": SettingSpec(
            label="상태이상저항", default=0, min=0, max=10000, potential=POTENTIAL_246
        ),
        "NAEGONG": SettingSpec(
            label="내공", default=0, min=0, max=10000, potential=POTENTIAL_123
        ),
        "HP": SettingSpec(
            label="체력", default=1, min=1, max=10000, potential=POTENTIAL_246
        ),
        "ATK_SPD": SettingSpec(
            label="공격속도", default=0, min=0, max=50, potential=POTENTIAL_123
        ),
        "POT_HEAL": SettingSpec(
            label="포션회복력", default=0, min=0, max=10000, potential=POTENTIAL_246
        ),
        "LUK": SettingSpec(
            label="운", default=0, min=0, max=10000, potential=POTENTIAL_246
        ),
        "EXP": SettingSpec(label="경험치획득량", default=0, min=0, max=10000),
    }

    # 시뮬레이션 환경 설정
    SIM_DETAILS: ClassVar[dict[str, SettingSpec]] = {
        "NORMAL_NAEGONG": SettingSpec(label="몬스터 내공", default=0, min=0, max=100),
        "BOSS_NAEGONG": SettingSpec(label="보스 내공", default=0, min=0, max=100),
        "POTION_HEAL": SettingSpec(label="포션 회복량", default=100, min=0, max=1000),
    }

    # 기타 설정
    DELAY: ClassVar[SettingSpec] = SettingSpec(
        label="딜레이", default=150, min=50, max=1000
    )
    COOLTIME_REDUCTION: ClassVar[SettingSpec] = SettingSpec(
        label="쿨타임 감소", default=0, min=0, max=50
    )

    DEFAULT_START_KEY: ClassVar[KeySpec] = KeyRegistry.get("f9")

    DEFAULT_SERVER_ID: ClassVar[str] = "한월 RPG"


@dataclass(frozen=True)
class AppConfig:
    version: ClassVar[str] = "3.1.0-beta.2"
    app_name: ClassVar[str] = "PD SkillMacro"

    ui: ClassVar[UiConfig] = UiConfig()
    simulation: ClassVar[SimulationConfig] = SimulationConfig()
    macro: ClassVar[MacroConfig] = MacroConfig()
    specs: ClassVar[MacroSpecs] = MacroSpecs()


config = AppConfig()
