from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.scripts.calculator_models import (
    BUILTIN_TALISMAN_TEMPLATES,
    REALM_TIER_SPECS,
    TALISMAN_GRADE_OFFSETS,
    CalculatorPresetInput,
    DanjeonState,
    DistributionState,
    EquippedOptimizationState,
    OwnedTalisman,
    OwnedTitle,
    PowerMetric,
    RealmTier,
    RealmTierSpec,
    StatKey,
)
from app.scripts.custom_classes import SimAttack, SimBuff
from app.scripts.registry.skill_registry import BuffEffect, DamageEffect, LevelEffect

if TYPE_CHECKING:
    from app.scripts.macro_models import MacroPreset, SkillUsageSetting
    from app.scripts.registry.server_registry import ServerSpec


# 스탯 표시 순서 고정
DISPLAY_STAT_KEYS: tuple[StatKey, ...] = (
    StatKey.ATTACK,
    StatKey.ATTACK_PERCENT,
    StatKey.HP,
    StatKey.HP_PERCENT,
    StatKey.STR,
    StatKey.STR_PERCENT,
    StatKey.DEXTERITY,
    StatKey.DEXTERITY_PERCENT,
    StatKey.VITALITY,
    StatKey.VITALITY_PERCENT,
    StatKey.LUCK,
    StatKey.LUCK_PERCENT,
    StatKey.SKILL_DAMAGE_PERCENT,
    StatKey.FINAL_ATTACK_PERCENT,
    StatKey.CRIT_RATE_PERCENT,
    StatKey.CRIT_DAMAGE_PERCENT,
    StatKey.EXP_PERCENT,
    StatKey.BOSS_ATTACK_PERCENT,
    StatKey.DROP_RATE_PERCENT,
    StatKey.DODGE_PERCENT,
    StatKey.POTION_HEAL_PERCENT,
    StatKey.RESIST_PERCENT,
    StatKey.SKILL_SPEED_PERCENT,
)


# 절댓값 표시 스탯 집합 고정
DISPLAY_ABSOLUTE_STAT_KEYS: tuple[StatKey, ...] = (
    StatKey.ATTACK,
    StatKey.HP,
    StatKey.STR,
    StatKey.DEXTERITY,
    StatKey.VITALITY,
    StatKey.LUCK,
)


# 퍼센트 표시 스탯 집합 고정
DISPLAY_PERCENT_STAT_KEYS: tuple[StatKey, ...] = (
    StatKey.ATTACK_PERCENT,
    StatKey.HP_PERCENT,
    StatKey.STR_PERCENT,
    StatKey.DEXTERITY_PERCENT,
    StatKey.VITALITY_PERCENT,
    StatKey.LUCK_PERCENT,
    StatKey.FINAL_ATTACK_PERCENT,
    StatKey.CRIT_DAMAGE_PERCENT,
    StatKey.BOSS_ATTACK_PERCENT,
    StatKey.DODGE_PERCENT,
    StatKey.RESIST_PERCENT,
    StatKey.SKILL_SPEED_PERCENT,
    StatKey.SKILL_DAMAGE_PERCENT,
    StatKey.CRIT_RATE_PERCENT,
    StatKey.EXP_PERCENT,
    StatKey.DROP_RATE_PERCENT,
    StatKey.POTION_HEAL_PERCENT,
)


# 전투력 표시 순서 고정
DISPLAY_POWER_METRICS: tuple[PowerMetric, ...] = (
    PowerMetric.BOSS_DAMAGE,
    PowerMetric.NORMAL_DAMAGE,
    PowerMetric.BOSS,
    PowerMetric.NORMAL,
    PowerMetric.OFFICIAL,
)


# 전투력 한글 라벨 고정
POWER_METRIC_LABELS: dict[PowerMetric, str] = {
    PowerMetric.BOSS_DAMAGE: "보스 데미지",
    PowerMetric.NORMAL_DAMAGE: "일반 데미지",
    PowerMetric.BOSS: "보스 전투력",
    PowerMetric.NORMAL: "일반 전투력",
    PowerMetric.OFFICIAL: "공식 전투력",
}


@dataclass(frozen=True, slots=True)
class CalculatorBuffWindow:
    """계산기용 버프 활성 구간"""

    stat_key: StatKey
    start_time: float
    end_time: float
    value: float


@dataclass(frozen=True, slots=True)
class CalculatorHitEvent:
    """계산기용 단일 타격 이벤트"""

    skill_id: str
    time: float
    multiplier: float
    is_skill: bool


@dataclass(frozen=True, slots=True)
class CalculatorTimeline:
    """계산기용 60초 타임라인"""

    hit_events: tuple[CalculatorHitEvent, ...]
    buff_windows: tuple[CalculatorBuffWindow, ...]


@dataclass(frozen=True, slots=True)
class CalculatorResolvedStats:
    """
    계산기 공식 계산에 사용할 최종 스탯
    전체 스탯과 변화량을 기반으로 2차 효과 제거한 원시 베이스와 최종 표시값이 모두 포함된 스탯 맵
    """

    values: dict[StatKey, float]
    base_attack_source: float
    base_hp_source: float
    base_attack_percent_source: float
    base_crit_rate_source: float
    base_crit_damage_source: float
    base_drop_rate_source: float
    base_exp_source: float
    base_dodge_source: float
    base_potion_heal_source: float
    raw_strength: float
    raw_dexterity: float
    raw_vitality: float
    raw_luck: float


@dataclass(frozen=True, slots=True)
class CalculatorPowerSummary:
    """계산기 전투력 요약"""

    metrics: dict[PowerMetric, float]


@dataclass(frozen=True, slots=True)
class CalculatorEvaluationContext:
    """효율 계산 기준 컨텍스트"""

    timeline: CalculatorTimeline
    baseline_stats: CalculatorResolvedStats
    baseline_summary: CalculatorPowerSummary


@dataclass(frozen=True, slots=True)
class LevelUpEvaluation:
    """
    레벨업 효율 계산 결과
    단일 레벨업으로 얻는 체력 +10과 스탯 포인트 5개를 최적으로 분배했을 때의 스탯 분배와 전투력 변화량
    """

    stat_distribution: dict[StatKey, int]
    deltas: dict[PowerMetric, float]


@dataclass(frozen=True, slots=True)
class RealmAdvanceEvaluation:
    """
    다음 경지 효율 계산 결과
    다음 경지로 진급할 때의 경지 포인트 분배와 전투력 변화량
    """

    target_realm: RealmTier
    danjeon_distribution: tuple[int, int, int]
    deltas: dict[PowerMetric, float]


@dataclass(frozen=True, slots=True)
class ScrollUpgradeEvaluation:
    """스크롤 레벨 상승 효율 계산 결과"""

    scroll_id: str
    scroll_name: str
    next_level: int
    deltas: dict[PowerMetric, float]


@dataclass(frozen=True, slots=True)
class CalculatorContribution:
    """현재 선택 기여 합산 결과"""

    raw_strength: float = 0.0
    raw_dexterity: float = 0.0
    raw_vitality: float = 0.0
    raw_luck: float = 0.0
    base_attack_source: float = 0.0
    base_hp_source: float = 0.0
    base_attack_percent_source: float = 0.0
    base_crit_rate_source: float = 0.0
    base_crit_damage_source: float = 0.0
    base_drop_rate_source: float = 0.0
    base_exp_source: float = 0.0
    base_dodge_source: float = 0.0
    base_potion_heal_source: float = 0.0
    direct_values: dict[StatKey, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CalculatorBaseState:
    """기준 베이스 스탯 분리 결과"""

    base_overall_stats: dict[str, float]
    contribution: CalculatorContribution


@dataclass(frozen=True, slots=True)
class CalculatorBaseValidation:
    """기준 베이스 스탯 검증 결과"""

    is_valid: bool
    message: str


@dataclass(frozen=True, slots=True)
class OptimizationCandidate:
    """최적화 후보 선택 상태"""

    distribution: DistributionState
    danjeon: DanjeonState
    equipped_title_id: str | None
    equipped_talisman_ids: list[str]


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """최적화 최종 결과"""

    candidate: OptimizationCandidate
    deltas: dict[PowerMetric, float]
    optimized_overall_stats: dict[str, float]


def _copy_stats(stats: dict[StatKey, float]) -> dict[StatKey, float]:
    """스탯 맵 얕은 복사"""

    copied: dict[StatKey, float] = {
        stat_key: float(value) for stat_key, value in stats.items()
    }
    return copied


def _inverse_percent_applied_value(final_value: float, percent_value: float) -> float:
    """퍼센트 적용 후 수치에서 적용 전 값 역산"""

    denominator: float = 1.0 + (percent_value * 0.01)
    if denominator <= 0.0:
        return 0.0

    raw_value: float = final_value / denominator

    return float(round(raw_value))


def _build_stat_map(overall_stats: dict[str, float]) -> dict[StatKey, float]:
    """문자열 키 기반 저장값을 enum 키 맵으로 변환"""

    mapped: dict[StatKey, float] = {}
    for stat_key in DISPLAY_STAT_KEYS:
        mapped[stat_key] = float(overall_stats[stat_key.value])

    return mapped


def _apply_changes(
    base_stats: dict[StatKey, float],
    stat_changes: dict[StatKey, float] | None,
) -> dict[StatKey, float]:
    """표시 스탯 변화량 반영"""

    resolved_stats: dict[StatKey, float] = _copy_stats(base_stats)
    if stat_changes is None:
        return resolved_stats

    for stat_key, value in stat_changes.items():
        current_value: float = float(resolved_stats[stat_key])
        resolved_stats[stat_key] = current_value + float(value)

    return resolved_stats


def resolve_calculator_stats(
    overall_stats: dict[str, float],
    stat_changes: dict[StatKey, float] | None = None,
) -> CalculatorResolvedStats:
    """전체 스탯과 변화량 기준 계산기 최종 스탯 계산"""

    # 입력된 전체 스탯을 enum 키 기반 스탯 맵으로 정규화
    normalized_stats: dict[StatKey, float] = _build_stat_map(overall_stats)
    changed_stats: dict[StatKey, float] = _apply_changes(normalized_stats, stat_changes)

    # 힘/민첩/생명력/행운 표시값 역산
    raw_strength: float = _inverse_percent_applied_value(
        float(changed_stats[StatKey.STR]),
        float(changed_stats[StatKey.STR_PERCENT]),
    )
    raw_dexterity: float = _inverse_percent_applied_value(
        float(changed_stats[StatKey.DEXTERITY]),
        float(changed_stats[StatKey.DEXTERITY_PERCENT]),
    )
    raw_vitality: float = _inverse_percent_applied_value(
        float(changed_stats[StatKey.VITALITY]),
        float(changed_stats[StatKey.VITALITY_PERCENT]),
    )
    raw_luck: float = _inverse_percent_applied_value(
        float(changed_stats[StatKey.LUCK]),
        float(changed_stats[StatKey.LUCK_PERCENT]),
    )

    # 표시 기준 최종 1차 스탯 계산
    final_strength: float = raw_strength * (
        1.0 + (float(changed_stats[StatKey.STR_PERCENT]) * 0.01)
    )
    final_dexterity: float = raw_dexterity * (
        1.0 + (float(changed_stats[StatKey.DEXTERITY_PERCENT]) * 0.01)
    )
    final_vitality: float = raw_vitality * (
        1.0 + (float(changed_stats[StatKey.VITALITY_PERCENT]) * 0.01)
    )
    final_luck: float = raw_luck * (
        1.0 + (float(changed_stats[StatKey.LUCK_PERCENT]) * 0.01)
    )

    # 2차 효과를 제거한 원시 공격/체력/기타 베이스 역산
    raw_attack_before_secondary: float = _inverse_percent_applied_value(
        float(changed_stats[StatKey.ATTACK]),
        float(changed_stats[StatKey.ATTACK_PERCENT]),
    )
    raw_hp_before_secondary: float = _inverse_percent_applied_value(
        float(changed_stats[StatKey.HP]),
        float(changed_stats[StatKey.HP_PERCENT]),
    )

    # 스탯% 적용 전 베이스 스탯 계산
    # 예: 힘1 -> 공+1 이므로 최종 힘 스탯량을 제거함
    base_attack_source: float = float(
        round(raw_attack_before_secondary - final_strength)
    )
    base_hp_source: float = float(
        round(raw_hp_before_secondary - (final_vitality * 5.0))
    )
    base_attack_percent_source: float = float(changed_stats[StatKey.ATTACK_PERCENT]) - (
        final_dexterity * 0.3
    )
    base_crit_rate_source: float = float(changed_stats[StatKey.CRIT_RATE_PERCENT]) - (
        final_dexterity * 0.05
    )
    base_crit_damage_source: float = float(
        changed_stats[StatKey.CRIT_DAMAGE_PERCENT]
    ) - (final_strength * 0.1)
    base_drop_rate_source: float = float(changed_stats[StatKey.DROP_RATE_PERCENT]) - (
        final_luck * 0.2
    )
    base_exp_source: float = float(changed_stats[StatKey.EXP_PERCENT]) - (
        final_luck * 0.2
    )
    base_dodge_source: float = float(changed_stats[StatKey.DODGE_PERCENT]) - (
        final_vitality * 0.03
    )
    base_potion_heal_source: float = float(
        changed_stats[StatKey.POTION_HEAL_PERCENT]
    ) - (final_vitality * 0.5)

    # 역산된 베이스와 2차 효과를 조합해 최종 스탯 재구성
    resolved_values: dict[StatKey, float] = _copy_stats(changed_stats)
    resolved_values[StatKey.STR] = final_strength
    resolved_values[StatKey.DEXTERITY] = final_dexterity
    resolved_values[StatKey.VITALITY] = final_vitality
    resolved_values[StatKey.LUCK] = final_luck
    resolved_values[StatKey.ATTACK] = (base_attack_source + final_strength) * (
        1.0 + (float(changed_stats[StatKey.ATTACK_PERCENT]) * 0.01)
    )
    resolved_values[StatKey.HP] = (base_hp_source + (final_vitality * 5.0)) * (
        1.0 + (float(changed_stats[StatKey.HP_PERCENT]) * 0.01)
    )
    resolved_values[StatKey.CRIT_RATE_PERCENT] = base_crit_rate_source + (
        final_dexterity * 0.05
    )
    resolved_values[StatKey.CRIT_DAMAGE_PERCENT] = base_crit_damage_source + (
        final_strength * 0.1
    )
    resolved_values[StatKey.DROP_RATE_PERCENT] = base_drop_rate_source + (
        final_luck * 0.2
    )
    resolved_values[StatKey.EXP_PERCENT] = base_exp_source + (final_luck * 0.2)
    resolved_values[StatKey.DODGE_PERCENT] = base_dodge_source + (final_vitality * 0.03)
    resolved_values[StatKey.POTION_HEAL_PERCENT] = base_potion_heal_source + (
        final_vitality * 0.5
    )
    resolved_values[StatKey.ATTACK_PERCENT] = base_attack_percent_source + (
        final_dexterity * 0.3
    )
    resolved_values[StatKey.SKILL_SPEED_PERCENT] = float(
        changed_stats[StatKey.SKILL_SPEED_PERCENT]
    )

    return CalculatorResolvedStats(
        values=resolved_values,
        base_attack_source=base_attack_source,
        base_hp_source=base_hp_source,
        base_attack_percent_source=base_attack_percent_source,
        base_crit_rate_source=base_crit_rate_source,
        base_crit_damage_source=base_crit_damage_source,
        base_drop_rate_source=base_drop_rate_source,
        base_exp_source=base_exp_source,
        base_dodge_source=base_dodge_source,
        base_potion_heal_source=base_potion_heal_source,
        raw_strength=raw_strength,
        raw_dexterity=raw_dexterity,
        raw_vitality=raw_vitality,
        raw_luck=raw_luck,
    )


def calculate_power_deltas(
    baseline_summary: CalculatorPowerSummary,
    target_summary: CalculatorPowerSummary,
) -> dict[PowerMetric, float]:
    """기준 대비 전투력 변화량 계산"""

    # 전투력 종류별 증감량 계산
    deltas: dict[PowerMetric, float] = {}
    for power_metric in DISPLAY_POWER_METRICS:
        deltas[power_metric] = (
            target_summary.metrics[power_metric]
            - baseline_summary.metrics[power_metric]
        )

    return deltas


def _add_direct_contribution(
    direct_values: dict[StatKey, float],
    stat_key: StatKey,
    value: float,
) -> None:
    """직접 반영 스탯 기여 누적"""

    # 직접 누적 가능한 표시 스탯 합산
    current_value: float = direct_values.get(stat_key, 0.0)
    direct_values[stat_key] = current_value + value


def _add_stat_contribution(
    contribution: CalculatorContribution,
    stat_key: StatKey,
    value: float,
) -> CalculatorContribution:
    """단일 스탯 기여를 기여 모델에 반영"""

    # 직접 누적 가능한 표시 스탯 사본 구성
    next_direct_values: dict[StatKey, float] = {
        key: float(current_value)
        for key, current_value in contribution.direct_values.items()
    }

    if stat_key == StatKey.STR:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength + value,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.DEXTERITY:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity + value,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.VITALITY:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality + value,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.LUCK:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck + value,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.ATTACK:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source + value,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.HP:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source + value,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.ATTACK_PERCENT:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source + value,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.CRIT_RATE_PERCENT:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source + value,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.CRIT_DAMAGE_PERCENT:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source + value,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.DROP_RATE_PERCENT:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source + value,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.EXP_PERCENT:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source + value,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.DODGE_PERCENT:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source + value,
            base_potion_heal_source=contribution.base_potion_heal_source,
            direct_values=next_direct_values,
        )

    if stat_key == StatKey.POTION_HEAL_PERCENT:
        return CalculatorContribution(
            raw_strength=contribution.raw_strength,
            raw_dexterity=contribution.raw_dexterity,
            raw_vitality=contribution.raw_vitality,
            raw_luck=contribution.raw_luck,
            base_attack_source=contribution.base_attack_source,
            base_hp_source=contribution.base_hp_source,
            base_attack_percent_source=contribution.base_attack_percent_source,
            base_crit_rate_source=contribution.base_crit_rate_source,
            base_crit_damage_source=contribution.base_crit_damage_source,
            base_drop_rate_source=contribution.base_drop_rate_source,
            base_exp_source=contribution.base_exp_source,
            base_dodge_source=contribution.base_dodge_source,
            base_potion_heal_source=contribution.base_potion_heal_source + value,
            direct_values=next_direct_values,
        )

    _add_direct_contribution(next_direct_values, stat_key, value)
    return CalculatorContribution(
        raw_strength=contribution.raw_strength,
        raw_dexterity=contribution.raw_dexterity,
        raw_vitality=contribution.raw_vitality,
        raw_luck=contribution.raw_luck,
        base_attack_source=contribution.base_attack_source,
        base_hp_source=contribution.base_hp_source,
        base_attack_percent_source=contribution.base_attack_percent_source,
        base_crit_rate_source=contribution.base_crit_rate_source,
        base_crit_damage_source=contribution.base_crit_damage_source,
        base_drop_rate_source=contribution.base_drop_rate_source,
        base_exp_source=contribution.base_exp_source,
        base_dodge_source=contribution.base_dodge_source,
        base_potion_heal_source=contribution.base_potion_heal_source,
        direct_values=next_direct_values,
    )


def build_distribution_contribution(
    distribution: DistributionState,
) -> CalculatorContribution:
    """현재 스탯 분배 기여 계산"""

    contribution: CalculatorContribution = CalculatorContribution()
    contribution = _add_stat_contribution(
        contribution,
        StatKey.STR,
        float(distribution.strength),
    )
    contribution = _add_stat_contribution(
        contribution,
        StatKey.DEXTERITY,
        float(distribution.dexterity),
    )
    contribution = _add_stat_contribution(
        contribution,
        StatKey.VITALITY,
        float(distribution.vitality),
    )
    contribution = _add_stat_contribution(
        contribution,
        StatKey.LUCK,
        float(distribution.luck),
    )
    return contribution


def build_danjeon_contribution(danjeon: DanjeonState) -> CalculatorContribution:
    """현재 단전 기여 계산"""

    contribution: CalculatorContribution = CalculatorContribution()
    contribution = _add_stat_contribution(
        contribution,
        StatKey.HP_PERCENT,
        float(danjeon.upper * 3),
    )
    contribution = _add_stat_contribution(
        contribution,
        StatKey.RESIST_PERCENT,
        float(danjeon.upper),
    )
    contribution = _add_stat_contribution(
        contribution,
        StatKey.ATTACK_PERCENT,
        float(danjeon.middle),
    )
    contribution = _add_stat_contribution(
        contribution,
        StatKey.DROP_RATE_PERCENT,
        float(danjeon.lower * 1.5),
    )
    contribution = _add_stat_contribution(
        contribution,
        StatKey.EXP_PERCENT,
        float(danjeon.lower * 0.5),
    )
    return contribution


def build_title_contribution(
    owned_titles: list[OwnedTitle],
    equipped_title_id: str | None,
) -> CalculatorContribution:
    """현재 장착 칭호 기여 계산"""

    if equipped_title_id is None:
        return CalculatorContribution()

    equipped_title: OwnedTitle | None = None
    for owned_title in owned_titles:
        if owned_title.title_id == equipped_title_id:
            equipped_title = owned_title
            break

    if equipped_title is None:
        return CalculatorContribution()

    contribution: CalculatorContribution = CalculatorContribution()
    for stat_key_text, value in equipped_title.stats.items():
        contribution = _add_stat_contribution(
            contribution,
            StatKey(stat_key_text),
            float(value),
        )
    return contribution


def _find_talisman_template(
    owned_talisman: OwnedTalisman,
) -> tuple[StatKey, int] | None:
    """보유 부적의 스탯 대상과 등급 보정값 조회"""

    for template in BUILTIN_TALISMAN_TEMPLATES:
        if template.template_id != owned_talisman.template_id:
            continue

        grade_offset: int = TALISMAN_GRADE_OFFSETS[template.grade]
        return template.stat_key, grade_offset

    return None


def build_talisman_contribution(
    owned_talismans: list[OwnedTalisman],
    equipped_state: EquippedOptimizationState,
) -> CalculatorContribution:
    """현재 장착 부적 기여 계산"""

    contribution: CalculatorContribution = CalculatorContribution()
    owned_map: dict[str, OwnedTalisman] = {
        owned_talisman.owned_id: owned_talisman for owned_talisman in owned_talismans
    }
    for equipped_id in equipped_state.equipped_talisman_ids:
        if equipped_id not in owned_map:
            continue

        owned_talisman: OwnedTalisman = owned_map[equipped_id]
        talisman_spec = _find_talisman_template(owned_talisman)
        if talisman_spec is None:
            continue

        stat_key: StatKey
        grade_offset: int
        stat_key, grade_offset = talisman_spec
        stat_value: float = float((grade_offset * 10) + owned_talisman.level)
        contribution = _add_stat_contribution(contribution, stat_key, stat_value)

    return contribution


def merge_contributions(
    contributions: tuple[CalculatorContribution, ...],
) -> CalculatorContribution:
    """복수 기여 모델 병합"""

    merged: CalculatorContribution = CalculatorContribution()
    for contribution in contributions:
        for stat_key, value in contribution.direct_values.items():
            merged = _add_stat_contribution(merged, stat_key, value)

        merged = CalculatorContribution(
            raw_strength=merged.raw_strength + contribution.raw_strength,
            raw_dexterity=merged.raw_dexterity + contribution.raw_dexterity,
            raw_vitality=merged.raw_vitality + contribution.raw_vitality,
            raw_luck=merged.raw_luck + contribution.raw_luck,
            base_attack_source=merged.base_attack_source
            + contribution.base_attack_source,
            base_hp_source=merged.base_hp_source + contribution.base_hp_source,
            base_attack_percent_source=(
                merged.base_attack_percent_source
                + contribution.base_attack_percent_source
            ),
            base_crit_rate_source=(
                merged.base_crit_rate_source + contribution.base_crit_rate_source
            ),
            base_crit_damage_source=(
                merged.base_crit_damage_source + contribution.base_crit_damage_source
            ),
            base_drop_rate_source=(
                merged.base_drop_rate_source + contribution.base_drop_rate_source
            ),
            base_exp_source=merged.base_exp_source + contribution.base_exp_source,
            base_dodge_source=merged.base_dodge_source + contribution.base_dodge_source,
            base_potion_heal_source=(
                merged.base_potion_heal_source + contribution.base_potion_heal_source
            ),
            direct_values=merged.direct_values,
        )

    return merged


def build_current_selected_contribution(
    calculator_input: CalculatorPresetInput,
) -> CalculatorContribution:
    """현재 선택 상태 전체 기여 계산"""

    # 현재 스탯 분배/단전/칭호/부적 기여를 하나의 모델로 병합
    distribution_contribution: CalculatorContribution = build_distribution_contribution(
        calculator_input.distribution
    )
    danjeon_contribution: CalculatorContribution = build_danjeon_contribution(
        calculator_input.danjeon
    )
    title_contribution: CalculatorContribution = build_title_contribution(
        calculator_input.owned_titles,
        calculator_input.equipped.equipped_title_id,
    )
    talisman_contribution: CalculatorContribution = build_talisman_contribution(
        calculator_input.owned_talismans,
        calculator_input.equipped,
    )
    return merge_contributions(
        (
            distribution_contribution,
            danjeon_contribution,
            title_contribution,
            talisman_contribution,
        )
    )


def _merge_buff_windows(
    buff_windows: list[CalculatorBuffWindow],
) -> tuple[CalculatorBuffWindow, ...]:
    """동일 스탯/값 버프 구간 병합"""

    # 동일 스탯/값 버프 구간끼리 그룹화
    grouped: dict[tuple[StatKey, float], list[CalculatorBuffWindow]] = {}
    for buff_window in buff_windows:
        group_key: tuple[StatKey, float] = (buff_window.stat_key, buff_window.value)

        if group_key not in grouped:
            grouped[group_key] = []

        grouped[group_key].append(buff_window)

    # 그룹별로 구간 병합 후 전체 구간 리스트에 추가
    merged_windows: list[CalculatorBuffWindow] = []
    for group_key, group_windows in grouped.items():
        sorted_windows: list[CalculatorBuffWindow] = sorted(
            group_windows,
            key=lambda item: item.start_time,
        )
        current_window: CalculatorBuffWindow = sorted_windows[0]

        for target_window in sorted_windows[1:]:
            # 현재 구간과 겹치는 구간은 병합
            if target_window.start_time <= current_window.end_time:
                current_window = CalculatorBuffWindow(
                    stat_key=current_window.stat_key,
                    start_time=current_window.start_time,
                    end_time=max(current_window.end_time, target_window.end_time),
                    value=current_window.value,
                )
                continue

            # 겹치지 않는 구간은 현재 구간을 결과에 추가하고 다음 구간으로 이동
            merged_windows.append(current_window)
            current_window = target_window

        merged_windows.append(current_window)

    ordered_windows: tuple[CalculatorBuffWindow, ...] = tuple(
        sorted(merged_windows, key=lambda item: item.start_time)
    )
    return ordered_windows


def build_calculator_timeline(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    cooltime_reduction: float,
) -> CalculatorTimeline:
    """메인 화면 스킬 상태 기준 계산기용 60초 타임라인 생성"""

    # 기존 시뮬레이터의 스킬 사용 순서를 그대로 재사용
    from app.scripts.simulate_macro import get_simulated_skills

    # 구형 시뮬레이터가 반환하는 공격/버프 이벤트를 재사용
    skills_info_tuple: tuple[tuple[str, tuple[bool, bool, int]], ...] = tuple(
        sorted(
            (skill_id, setting.to_tuple()) for skill_id, setting in skills_info.items()
        )
    )
    attack_details: list[SimAttack]
    buff_details: list[SimBuff]
    attack_details, buff_details = get_simulated_skills(
        cooltimeReduce=cooltime_reduction,
        skills_info_tuple=skills_info_tuple,
    )

    # 평타 여부와 데미지 배율만 남기는 계산기용 공격 이벤트 구성
    hit_events: list[CalculatorHitEvent] = []
    for attack_detail in attack_details:
        is_skill: bool = not attack_detail.skill_id.endswith(":평타")
        hit_events.append(
            CalculatorHitEvent(
                skill_id=attack_detail.skill_id,
                time=attack_detail.time,
                multiplier=attack_detail.damage,
                is_skill=is_skill,
            )
        )

    # 계산기 스탯 키로 직접 저장된 버프만 계산기 구간으로 변환
    converted_buff_windows: list[CalculatorBuffWindow] = []
    for buff_detail in buff_details:
        stat_key: StatKey = StatKey(str(buff_detail.stat))

        converted_buff_windows.append(
            CalculatorBuffWindow(
                stat_key=stat_key,
                start_time=float(buff_detail.start_time),
                end_time=float(buff_detail.end_time),
                value=float(buff_detail.value),
            )
        )

    merged_buff_windows: tuple[CalculatorBuffWindow, ...] = _merge_buff_windows(
        converted_buff_windows
    )
    timeline: CalculatorTimeline = CalculatorTimeline(
        hit_events=tuple(hit_events),
        buff_windows=merged_buff_windows,
    )
    return timeline


def _apply_active_buffs(
    resolved_stats: CalculatorResolvedStats,
    active_buffs: tuple[CalculatorBuffWindow, ...],
) -> dict[StatKey, float]:
    """현재 시점 활성 버프 반영 스탯 구성"""

    buffed_values: dict[StatKey, float] = _copy_stats(resolved_stats.values)
    for active_buff in active_buffs:
        current_value: float = float(buffed_values[active_buff.stat_key])
        buffed_values[active_buff.stat_key] = current_value + active_buff.value

    return buffed_values


def _collect_active_buffs(
    buff_windows: tuple[CalculatorBuffWindow, ...],
    target_time: float,
) -> tuple[CalculatorBuffWindow, ...]:
    """특정 시점 활성 버프 목록 수집"""

    active_buffs: tuple[CalculatorBuffWindow, ...] = tuple(
        buff_window
        for buff_window in buff_windows
        if buff_window.start_time <= target_time <= buff_window.end_time
    )
    return active_buffs


def _calculate_hit_damage(
    resolved_stats: dict[StatKey, float],
    hit_event: CalculatorHitEvent,
    is_boss: bool,
) -> float:
    """단일 타격 데미지 계산"""

    # 공격력 표시값에 최종 공격력과 보스 공격력을 차례대로 반영
    attack_power: float = float(resolved_stats[StatKey.ATTACK])
    attack_power *= 1.0 + (float(resolved_stats[StatKey.FINAL_ATTACK_PERCENT]) * 0.01)
    if is_boss:
        attack_power *= 1.0 + (
            float(resolved_stats[StatKey.BOSS_ATTACK_PERCENT]) * 0.01
        )

    # 기대 치명타를 반영한 기본 타격 데미지 계산
    crit_rate: float = min(float(resolved_stats[StatKey.CRIT_RATE_PERCENT]), 100.0)
    crit_damage: float = float(resolved_stats[StatKey.CRIT_DAMAGE_PERCENT])
    damage: float = attack_power * hit_event.multiplier
    damage *= 1.0 + (crit_rate * crit_damage * 0.0001)

    # 평타가 아닌 스킬 타격에만 스킬 피해량 보정 적용
    if hit_event.is_skill:
        damage *= 1.0 + (float(resolved_stats[StatKey.SKILL_DAMAGE_PERCENT]) * 0.01)

    return damage


def evaluate_calculator_power(
    timeline: CalculatorTimeline,
    resolved_stats: CalculatorResolvedStats,
) -> CalculatorPowerSummary:
    """계산기 타임라인과 최종 스탯 기준 5종 전투력 계산"""

    # 보스/일반 총데미지 누적
    total_boss_damage: float = 0.0
    total_normal_damage: float = 0.0

    for hit_event in timeline.hit_events:
        active_buffs: tuple[CalculatorBuffWindow, ...] = _collect_active_buffs(
            timeline.buff_windows,
            hit_event.time,
        )
        buffed_stats: dict[StatKey, float] = _apply_active_buffs(
            resolved_stats, active_buffs
        )
        total_boss_damage += _calculate_hit_damage(
            resolved_stats=buffed_stats,
            hit_event=hit_event,
            is_boss=True,
        )
        total_normal_damage += _calculate_hit_damage(
            resolved_stats=buffed_stats,
            hit_event=hit_event,
            is_boss=False,
        )

    # 5종 전투력 계산
    hp_value: float = float(resolved_stats.values[StatKey.HP])
    dodge_value: float = float(resolved_stats.values[StatKey.DODGE_PERCENT])
    resist_value: float = float(resolved_stats.values[StatKey.RESIST_PERCENT])
    potion_heal_value: float = float(resolved_stats.values[StatKey.POTION_HEAL_PERCENT])
    drop_rate_value: float = float(resolved_stats.values[StatKey.DROP_RATE_PERCENT])
    exp_value: float = float(resolved_stats.values[StatKey.EXP_PERCENT])

    dodge_denominator: float = max(1.0 - (dodge_value * 0.01), 0.01)

    boss_power: float = total_boss_damage
    boss_power *= hp_value
    boss_power *= 1.0 / dodge_denominator
    boss_power *= 1.0 + (resist_value * 0.01)
    boss_power *= 1.0 + (potion_heal_value * 0.01)

    normal_power: float = total_normal_damage
    normal_power *= 1.0 + (drop_rate_value * 0.01)
    normal_power *= 1.0 + (exp_value * 0.01)

    # 임시 공식 전투력
    official_power: float = (total_boss_damage + total_normal_damage) * 0.5

    metrics: dict[PowerMetric, float] = {
        PowerMetric.BOSS_DAMAGE: total_boss_damage,
        PowerMetric.NORMAL_DAMAGE: total_normal_damage,
        PowerMetric.BOSS: boss_power,
        PowerMetric.NORMAL: normal_power,
        PowerMetric.OFFICIAL: official_power,
    }

    return CalculatorPowerSummary(metrics=metrics)


def build_calculator_context(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    overall_stats: dict[str, float],
) -> CalculatorEvaluationContext:
    """현재 계산기 입력 기준 평가 컨텍스트 구성"""

    # 현재 전체 스탯 기준 최종 계산 스탯 구성
    baseline_stats: CalculatorResolvedStats = resolve_calculator_stats(
        overall_stats=overall_stats
    )

    # 현재 스킬속도 기준 타임라인 구성
    timeline: CalculatorTimeline = build_calculator_timeline(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        cooltime_reduction=baseline_stats.values[StatKey.SKILL_SPEED_PERCENT],
    )

    # 기준 타임라인과 기준 스탯으로 기준 전투력 계산
    baseline_summary: CalculatorPowerSummary = evaluate_calculator_power(
        timeline=timeline,
        resolved_stats=baseline_stats,
    )

    return CalculatorEvaluationContext(
        timeline=timeline,
        baseline_stats=baseline_stats,
        baseline_summary=baseline_summary,
    )


def evaluate_stat_changes(
    context: CalculatorEvaluationContext,
    overall_stats: dict[str, float],
    stat_changes: dict[StatKey, float],
) -> CalculatorPowerSummary:
    """전체 스탯 변화량 반영 후 전투력 계산"""

    # 변화량을 반영한 최종 스탯 재계산
    resolved_stats: CalculatorResolvedStats = resolve_calculator_stats(
        overall_stats=overall_stats,
        stat_changes=stat_changes,
    )

    # 기준 타임라인 재사용 기반 전투력 재평가
    summary: CalculatorPowerSummary = evaluate_calculator_power(
        timeline=context.timeline,
        resolved_stats=resolved_stats,
    )

    return summary


def evaluate_single_stat_delta(
    context: CalculatorEvaluationContext,
    overall_stats: dict[str, float],
    stat_key: StatKey,
    amount: float,
) -> dict[PowerMetric, float]:
    """단일 스탯 변화량 기준 전투력 차이 계산"""

    # 단일 스탯 변화량 맵 구성
    stat_changes: dict[StatKey, float] = {stat_key: amount}
    target_summary: CalculatorPowerSummary = evaluate_stat_changes(
        context=context,
        overall_stats=overall_stats,
        stat_changes=stat_changes,
    )

    return calculate_power_deltas(context.baseline_summary, target_summary)


def evaluate_arbitrary_stat_delta(
    context: CalculatorEvaluationContext,
    overall_stats: dict[str, float],
    stat_changes: dict[StatKey, float],
) -> dict[PowerMetric, float]:
    """여러 스탯 변화량 기준 전투력 차이 계산"""

    # 다중 스탯 변화량 전투력 계산
    target_summary: CalculatorPowerSummary = evaluate_stat_changes(
        context=context,
        overall_stats=overall_stats,
        stat_changes=stat_changes,
    )

    return calculate_power_deltas(context.baseline_summary, target_summary)


def extract_skill_level_effects(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skill_id: str,
) -> list[LevelEffect]:
    """현재 스크롤 레벨 기준 스킬 효과 목록 조회"""

    # 스크롤 레벨과 실제 효과 테이블 연결
    skill_level: int = preset.info.get_skill_level(server_spec, skill_id)
    skill_effects: list[LevelEffect] = server_spec.skill_registry.get(skill_id).levels[
        skill_level
    ]

    return skill_effects


def build_skill_effect_maps(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    placed_skill_ids: list[str],
) -> tuple[dict[str, list[DamageEffect]], dict[str, list[BuffEffect]]]:
    """현재 배치 스킬의 레벨별 데미지/버프 효과 맵 구성"""

    # 스크롤 레벨 반영 효과를 데미지/버프별로 미리 분리
    damage_effects_map: dict[str, list[DamageEffect]] = {}
    buff_effects_map: dict[str, list[BuffEffect]] = {}

    for skill_id in placed_skill_ids:
        level_effects: list[LevelEffect] = extract_skill_level_effects(
            server_spec=server_spec,
            preset=preset,
            skill_id=skill_id,
        )
        damage_effects: list[DamageEffect] = []
        buff_effects: list[BuffEffect] = []

        for level_effect in level_effects:
            if isinstance(level_effect, DamageEffect):
                damage_effects.append(level_effect)

            elif isinstance(level_effect, BuffEffect):
                buff_effects.append(level_effect)

        damage_effects_map[skill_id] = damage_effects
        buff_effects_map[skill_id] = buff_effects

    return damage_effects_map, buff_effects_map


def evaluate_level_up_delta(
    context: CalculatorEvaluationContext,
    overall_stats: dict[str, float],
    target_metric: PowerMetric,
) -> LevelUpEvaluation:
    """레벨 1업 시 최적 스탯 분배 기준 전투력 차이 계산"""

    # 체력 +10과 스탯 포인트 5개 분배 조합 전체 탐색
    best_distribution: dict[StatKey, int] = {
        StatKey.STR: 0,
        StatKey.DEXTERITY: 0,
        StatKey.VITALITY: 0,
        StatKey.LUCK: 0,
    }
    best_deltas: dict[PowerMetric, float] = {
        power_metric: 0.0 for power_metric in DISPLAY_POWER_METRICS
    }
    best_metric_delta: float = 0.0
    # 0~5 -> 6
    for strength in range(6):
        for dexterity in range(6 - strength):
            for vitality in range(6 - strength - dexterity):
                luck: int = 5 - strength - dexterity - vitality
                stat_changes: dict[StatKey, float] = {
                    StatKey.HP: 10.0,
                    StatKey.STR: float(strength),
                    StatKey.DEXTERITY: float(dexterity),
                    StatKey.VITALITY: float(vitality),
                    StatKey.LUCK: float(luck),
                }
                deltas: dict[PowerMetric, float] = evaluate_arbitrary_stat_delta(
                    context=context,
                    overall_stats=overall_stats,
                    stat_changes=stat_changes,
                )
                metric_delta: float = deltas[target_metric]
                if metric_delta <= best_metric_delta:
                    continue

                best_metric_delta = metric_delta
                best_distribution = {
                    StatKey.STR: strength,
                    StatKey.DEXTERITY: dexterity,
                    StatKey.VITALITY: vitality,
                    StatKey.LUCK: luck,
                }
                best_deltas = deltas

    return LevelUpEvaluation(
        stat_distribution=best_distribution,
        deltas=best_deltas,
    )


def _get_next_realm(current_realm: RealmTier) -> RealmTier | None:
    """다음 경지 반환"""

    # 선언 순서 기준 다음 경지 탐색
    ordered_realms: list[RealmTier] = list(REALM_TIER_SPECS.keys())
    current_index: int = ordered_realms.index(current_realm)
    next_index: int = current_index + 1
    if next_index >= len(ordered_realms):
        return None

    return ordered_realms[next_index]


def evaluate_next_realm_delta(
    context: CalculatorEvaluationContext,
    overall_stats: dict[str, float],
    current_realm: RealmTier,
    level: int,
    target_metric: PowerMetric,
) -> RealmAdvanceEvaluation | None:
    """현재 레벨 기준 다음 경지 상승 효율 계산"""

    # 다음 경지와 요구 레벨 조건 확인
    next_realm: RealmTier | None = _get_next_realm(current_realm)
    if next_realm is None:
        return None

    next_realm_spec: RealmTierSpec = REALM_TIER_SPECS[next_realm]
    if level < next_realm_spec.min_level:
        return None

    # 다음 경지에서 증가하는 단전 포인트 수 계산
    current_points: int = REALM_TIER_SPECS[current_realm].danjeon_points
    extra_points: int = next_realm_spec.danjeon_points - current_points

    # 추가 단전 포인트 최적 분배 탐색
    best_distribution: tuple[int, int, int] = (0, 0, 0)
    best_deltas: dict[PowerMetric, float] = {
        power_metric: 0.0 for power_metric in DISPLAY_POWER_METRICS
    }
    best_metric_delta: float = 0.0
    for upper in range(extra_points + 1):
        for middle in range(extra_points - upper + 1):
            lower: int = extra_points - upper - middle
            stat_changes: dict[StatKey, float] = {
                StatKey.HP_PERCENT: float(upper * 3),
                StatKey.RESIST_PERCENT: float(upper),
                StatKey.ATTACK_PERCENT: float(middle),
                StatKey.DROP_RATE_PERCENT: float(lower * 1.5),
                StatKey.EXP_PERCENT: float(lower * 0.5),
            }
            deltas: dict[PowerMetric, float] = evaluate_arbitrary_stat_delta(
                context=context,
                overall_stats=overall_stats,
                stat_changes=stat_changes,
            )
            metric_delta: float = deltas[target_metric]
            if metric_delta <= best_metric_delta:
                continue

            best_metric_delta = metric_delta
            best_distribution = (upper, middle, lower)
            best_deltas = deltas

    return RealmAdvanceEvaluation(
        target_realm=next_realm,
        danjeon_distribution=best_distribution,
        deltas=best_deltas,
    )


def evaluate_scroll_upgrade_deltas(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    overall_stats: dict[str, float],
) -> list[ScrollUpgradeEvaluation]:
    """각 스크롤 1레벨 상승 시 전투력 차이 계산"""

    # 현재 레벨 기준 기준 전투력 컨텍스트 구성
    baseline_context: CalculatorEvaluationContext = build_calculator_context(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        overall_stats=overall_stats,
    )

    # 스크롤별 1레벨 상승 효과 계산
    evaluations: list[ScrollUpgradeEvaluation] = []
    for scroll_def in server_spec.skill_registry.get_all_scroll_defs():
        current_level: int = preset.info.get_scroll_level(scroll_def.id)
        if current_level >= server_spec.max_skill_level:
            continue

        # 현재 프리셋 레벨을 일시적으로 올려 상승 후 전투력 계산
        preset.info.set_scroll_level(scroll_def.id, current_level + 1)
        try:
            upgraded_context: CalculatorEvaluationContext = build_calculator_context(
                server_spec=server_spec,
                preset=preset,
                skills_info=skills_info,
                delay_ms=delay_ms,
                overall_stats=overall_stats,
            )

        finally:
            preset.info.set_scroll_level(scroll_def.id, current_level)

        evaluations.append(
            ScrollUpgradeEvaluation(
                scroll_id=scroll_def.id,
                scroll_name=scroll_def.name,
                next_level=current_level + 1,
                deltas=calculate_power_deltas(
                    baseline_summary=baseline_context.baseline_summary,
                    target_summary=upgraded_context.baseline_summary,
                ),
            )
        )

    return evaluations


def _get_direct_contribution_value(
    contribution: CalculatorContribution,
    stat_key: StatKey,
) -> float:
    """직접 반영 스탯 기여 조회"""

    if stat_key not in contribution.direct_values:
        return 0.0

    return float(contribution.direct_values[stat_key])


def _build_base_overall_stats_from_components(
    raw_strength: float,
    raw_dexterity: float,
    raw_vitality: float,
    raw_luck: float,
    strength_percent: float,
    dexterity_percent: float,
    vitality_percent: float,
    luck_percent: float,
    base_attack_source: float,
    base_hp_source: float,
    base_attack_percent_source: float,
    base_crit_rate_source: float,
    base_crit_damage_source: float,
    base_drop_rate_source: float,
    base_exp_source: float,
    base_dodge_source: float,
    base_potion_heal_source: float,
    direct_values: dict[StatKey, float],
) -> dict[str, float]:
    """내부 원시 구성요소로 기준 전체 스탯 재구성"""

    # 원시값과 퍼센트값으로 1차 스탯 재구성
    final_strength: float = raw_strength * (1.0 + (strength_percent * 0.01))
    final_dexterity: float = raw_dexterity * (1.0 + (dexterity_percent * 0.01))
    final_vitality: float = raw_vitality * (1.0 + (vitality_percent * 0.01))
    final_luck: float = raw_luck * (1.0 + (luck_percent * 0.01))

    # 2차 효과 포함 최종 스탯 재구성
    attack_percent: float = base_attack_percent_source + (final_dexterity * 0.3)
    crit_rate: float = base_crit_rate_source + (final_dexterity * 0.05)
    crit_damage: float = base_crit_damage_source + (final_strength * 0.1)
    drop_rate: float = base_drop_rate_source + (final_luck * 0.2)
    exp_rate: float = base_exp_source + (final_luck * 0.2)
    dodge_rate: float = base_dodge_source + (final_vitality * 0.03)
    potion_heal: float = base_potion_heal_source + (final_vitality * 0.5)
    attack: float = (base_attack_source + final_strength) * (
        1.0 + (attack_percent * 0.01)
    )
    hp: float = (base_hp_source + (final_vitality * 5.0)) * (
        1.0 + (direct_values[StatKey.HP_PERCENT] * 0.01)
    )

    # 전체 스탯 맵 문자열 키로 재구성
    base_overall_stats: dict[str, float] = {
        StatKey.ATTACK.value: attack,
        StatKey.ATTACK_PERCENT.value: attack_percent,
        StatKey.HP.value: hp,
        StatKey.HP_PERCENT.value: direct_values[StatKey.HP_PERCENT],
        StatKey.STR.value: final_strength,
        StatKey.STR_PERCENT.value: strength_percent,
        StatKey.DEXTERITY.value: final_dexterity,
        StatKey.DEXTERITY_PERCENT.value: dexterity_percent,
        StatKey.VITALITY.value: final_vitality,
        StatKey.VITALITY_PERCENT.value: vitality_percent,
        StatKey.LUCK.value: final_luck,
        StatKey.LUCK_PERCENT.value: luck_percent,
        StatKey.SKILL_DAMAGE_PERCENT.value: direct_values[StatKey.SKILL_DAMAGE_PERCENT],
        StatKey.FINAL_ATTACK_PERCENT.value: direct_values[StatKey.FINAL_ATTACK_PERCENT],
        StatKey.CRIT_RATE_PERCENT.value: crit_rate,
        StatKey.CRIT_DAMAGE_PERCENT.value: crit_damage,
        StatKey.EXP_PERCENT.value: exp_rate,
        StatKey.BOSS_ATTACK_PERCENT.value: direct_values[StatKey.BOSS_ATTACK_PERCENT],
        StatKey.DROP_RATE_PERCENT.value: drop_rate,
        StatKey.DODGE_PERCENT.value: dodge_rate,
        StatKey.POTION_HEAL_PERCENT.value: potion_heal,
        StatKey.RESIST_PERCENT.value: direct_values[StatKey.RESIST_PERCENT],
        StatKey.SKILL_SPEED_PERCENT.value: direct_values[StatKey.SKILL_SPEED_PERCENT],
    }

    return base_overall_stats


def build_base_state(
    overall_stats: dict[str, float],
    calculator_input: CalculatorPresetInput,
) -> CalculatorBaseState:
    """현재 선택 기여를 제거한 기준 베이스 스탯 계산"""

    # 현재 전체 스탯을 내부 원시 구성요소로 해석
    resolved_stats: CalculatorResolvedStats = resolve_calculator_stats(overall_stats)
    contribution: CalculatorContribution = build_current_selected_contribution(
        calculator_input
    )

    # 직접 반영 퍼센트 스탯 기여 제거 후 직접값 맵 구성
    direct_values: dict[StatKey, float] = {
        StatKey.HP_PERCENT: float(resolved_stats.values[StatKey.HP_PERCENT])
        - _get_direct_contribution_value(contribution, StatKey.HP_PERCENT),
        StatKey.STR_PERCENT: float(resolved_stats.values[StatKey.STR_PERCENT])
        - _get_direct_contribution_value(contribution, StatKey.STR_PERCENT),
        StatKey.DEXTERITY_PERCENT: float(
            resolved_stats.values[StatKey.DEXTERITY_PERCENT]
        )
        - _get_direct_contribution_value(contribution, StatKey.DEXTERITY_PERCENT),
        StatKey.VITALITY_PERCENT: float(resolved_stats.values[StatKey.VITALITY_PERCENT])
        - _get_direct_contribution_value(contribution, StatKey.VITALITY_PERCENT),
        StatKey.LUCK_PERCENT: float(resolved_stats.values[StatKey.LUCK_PERCENT])
        - _get_direct_contribution_value(contribution, StatKey.LUCK_PERCENT),
        StatKey.SKILL_DAMAGE_PERCENT: float(
            resolved_stats.values[StatKey.SKILL_DAMAGE_PERCENT]
        )
        - _get_direct_contribution_value(contribution, StatKey.SKILL_DAMAGE_PERCENT),
        StatKey.FINAL_ATTACK_PERCENT: float(
            resolved_stats.values[StatKey.FINAL_ATTACK_PERCENT]
        )
        - _get_direct_contribution_value(contribution, StatKey.FINAL_ATTACK_PERCENT),
        StatKey.BOSS_ATTACK_PERCENT: float(
            resolved_stats.values[StatKey.BOSS_ATTACK_PERCENT]
        )
        - _get_direct_contribution_value(contribution, StatKey.BOSS_ATTACK_PERCENT),
        StatKey.RESIST_PERCENT: float(resolved_stats.values[StatKey.RESIST_PERCENT])
        - _get_direct_contribution_value(contribution, StatKey.RESIST_PERCENT),
        StatKey.SKILL_SPEED_PERCENT: float(
            resolved_stats.values[StatKey.SKILL_SPEED_PERCENT]
        )
        - _get_direct_contribution_value(contribution, StatKey.SKILL_SPEED_PERCENT),
    }

    # 원시 베이스 구성요소에 현재 선택 기여 제거
    raw_strength: float = resolved_stats.raw_strength - contribution.raw_strength
    raw_dexterity: float = resolved_stats.raw_dexterity - contribution.raw_dexterity
    raw_vitality: float = resolved_stats.raw_vitality - contribution.raw_vitality
    raw_luck: float = resolved_stats.raw_luck - contribution.raw_luck
    base_attack_source: float = (
        resolved_stats.base_attack_source - contribution.base_attack_source
    )
    base_hp_source: float = resolved_stats.base_hp_source - contribution.base_hp_source
    base_attack_percent_source: float = (
        resolved_stats.base_attack_percent_source
        - contribution.base_attack_percent_source
    )
    base_crit_rate_source: float = (
        resolved_stats.base_crit_rate_source - contribution.base_crit_rate_source
    )
    base_crit_damage_source: float = (
        resolved_stats.base_crit_damage_source - contribution.base_crit_damage_source
    )
    base_drop_rate_source: float = (
        resolved_stats.base_drop_rate_source - contribution.base_drop_rate_source
    )
    base_exp_source: float = (
        resolved_stats.base_exp_source - contribution.base_exp_source
    )
    base_dodge_source: float = (
        resolved_stats.base_dodge_source - contribution.base_dodge_source
    )
    base_potion_heal_source: float = (
        resolved_stats.base_potion_heal_source - contribution.base_potion_heal_source
    )

    base_overall_stats: dict[str, float] = _build_base_overall_stats_from_components(
        raw_strength=raw_strength,
        raw_dexterity=raw_dexterity,
        raw_vitality=raw_vitality,
        raw_luck=raw_luck,
        strength_percent=direct_values[StatKey.STR_PERCENT],
        dexterity_percent=direct_values[StatKey.DEXTERITY_PERCENT],
        vitality_percent=direct_values[StatKey.VITALITY_PERCENT],
        luck_percent=direct_values[StatKey.LUCK_PERCENT],
        base_attack_source=base_attack_source,
        base_hp_source=base_hp_source,
        base_attack_percent_source=base_attack_percent_source,
        base_crit_rate_source=base_crit_rate_source,
        base_crit_damage_source=base_crit_damage_source,
        base_drop_rate_source=base_drop_rate_source,
        base_exp_source=base_exp_source,
        base_dodge_source=base_dodge_source,
        base_potion_heal_source=base_potion_heal_source,
        direct_values=direct_values,
    )

    return CalculatorBaseState(
        base_overall_stats=base_overall_stats,
        contribution=contribution,
    )


def validate_base_state(
    overall_stats: dict[str, float],
    calculator_input: CalculatorPresetInput,
) -> CalculatorBaseValidation:
    """현재 선택 기여 제거 가능 여부 검증"""

    # 포인트 제한 검증
    distribution_sum: int = (
        calculator_input.distribution.strength
        + calculator_input.distribution.dexterity
        + calculator_input.distribution.vitality
        + calculator_input.distribution.luck
    )
    if distribution_sum > calculator_input.level * 5:
        return CalculatorBaseValidation(
            is_valid=False,
            message="스탯 분배 포인트가 레벨 기준 최대치를 초과합니다.",
        )

    danjeon_sum: int = (
        calculator_input.danjeon.upper
        + calculator_input.danjeon.middle
        + calculator_input.danjeon.lower
    )
    realm_cap: int = REALM_TIER_SPECS[calculator_input.realm_tier].danjeon_points
    if danjeon_sum > realm_cap:
        return CalculatorBaseValidation(
            is_valid=False,
            message="단전 포인트가 현재 경지 최대치를 초과합니다.",
        )

    # 기준 베이스 스탯 분리 후 음수 구성요소 검증
    base_state: CalculatorBaseState = build_base_state(overall_stats, calculator_input)
    resolved_base: CalculatorResolvedStats = resolve_calculator_stats(
        base_state.base_overall_stats
    )
    invalid_values: tuple[float, ...] = (
        resolved_base.raw_strength,
        resolved_base.raw_dexterity,
        resolved_base.raw_vitality,
        resolved_base.raw_luck,
        resolved_base.base_attack_source,
        resolved_base.base_hp_source,
        resolved_base.base_attack_percent_source,
        resolved_base.base_crit_rate_source,
        resolved_base.base_crit_damage_source,
        resolved_base.base_drop_rate_source,
        resolved_base.base_exp_source,
        resolved_base.base_dodge_source,
        resolved_base.base_potion_heal_source,
    )
    if any(value < 0.0 for value in invalid_values):
        return CalculatorBaseValidation(
            is_valid=False,
            message="현재 선택 기여를 제거하면 음수 원시 스탯이 발생합니다.",
        )

    return CalculatorBaseValidation(is_valid=True, message="정상")


def _build_overall_stats_from_base_and_contribution(
    base_state: CalculatorBaseState,
    contribution: CalculatorContribution,
) -> dict[str, float]:
    """기준 베이스와 후보 기여로 최종 전체 스탯 재구성"""

    # 기준 베이스 스탯을 내부 원시 구성요소로 재해석
    resolved_base: CalculatorResolvedStats = resolve_calculator_stats(
        base_state.base_overall_stats
    )

    # 직접 퍼센트 스탯과 원시 구성요소에 후보 기여 합산
    direct_values: dict[StatKey, float] = {
        StatKey.HP_PERCENT: float(resolved_base.values[StatKey.HP_PERCENT])
        + _get_direct_contribution_value(contribution, StatKey.HP_PERCENT),
        StatKey.STR_PERCENT: float(resolved_base.values[StatKey.STR_PERCENT])
        + _get_direct_contribution_value(contribution, StatKey.STR_PERCENT),
        StatKey.DEXTERITY_PERCENT: float(
            resolved_base.values[StatKey.DEXTERITY_PERCENT]
        )
        + _get_direct_contribution_value(contribution, StatKey.DEXTERITY_PERCENT),
        StatKey.VITALITY_PERCENT: float(resolved_base.values[StatKey.VITALITY_PERCENT])
        + _get_direct_contribution_value(contribution, StatKey.VITALITY_PERCENT),
        StatKey.LUCK_PERCENT: float(resolved_base.values[StatKey.LUCK_PERCENT])
        + _get_direct_contribution_value(contribution, StatKey.LUCK_PERCENT),
        StatKey.SKILL_DAMAGE_PERCENT: float(
            resolved_base.values[StatKey.SKILL_DAMAGE_PERCENT]
        )
        + _get_direct_contribution_value(contribution, StatKey.SKILL_DAMAGE_PERCENT),
        StatKey.FINAL_ATTACK_PERCENT: float(
            resolved_base.values[StatKey.FINAL_ATTACK_PERCENT]
        )
        + _get_direct_contribution_value(contribution, StatKey.FINAL_ATTACK_PERCENT),
        StatKey.BOSS_ATTACK_PERCENT: float(
            resolved_base.values[StatKey.BOSS_ATTACK_PERCENT]
        )
        + _get_direct_contribution_value(contribution, StatKey.BOSS_ATTACK_PERCENT),
        StatKey.RESIST_PERCENT: float(resolved_base.values[StatKey.RESIST_PERCENT])
        + _get_direct_contribution_value(contribution, StatKey.RESIST_PERCENT),
        StatKey.SKILL_SPEED_PERCENT: float(
            resolved_base.values[StatKey.SKILL_SPEED_PERCENT]
        )
        + _get_direct_contribution_value(contribution, StatKey.SKILL_SPEED_PERCENT),
    }

    return _build_base_overall_stats_from_components(
        raw_strength=resolved_base.raw_strength + contribution.raw_strength,
        raw_dexterity=resolved_base.raw_dexterity + contribution.raw_dexterity,
        raw_vitality=resolved_base.raw_vitality + contribution.raw_vitality,
        raw_luck=resolved_base.raw_luck + contribution.raw_luck,
        strength_percent=direct_values[StatKey.STR_PERCENT],
        dexterity_percent=direct_values[StatKey.DEXTERITY_PERCENT],
        vitality_percent=direct_values[StatKey.VITALITY_PERCENT],
        luck_percent=direct_values[StatKey.LUCK_PERCENT],
        base_attack_source=resolved_base.base_attack_source
        + contribution.base_attack_source,
        base_hp_source=resolved_base.base_hp_source + contribution.base_hp_source,
        base_attack_percent_source=resolved_base.base_attack_percent_source
        + contribution.base_attack_percent_source,
        base_crit_rate_source=resolved_base.base_crit_rate_source
        + contribution.base_crit_rate_source,
        base_crit_damage_source=resolved_base.base_crit_damage_source
        + contribution.base_crit_damage_source,
        base_drop_rate_source=resolved_base.base_drop_rate_source
        + contribution.base_drop_rate_source,
        base_exp_source=resolved_base.base_exp_source + contribution.base_exp_source,
        base_dodge_source=resolved_base.base_dodge_source
        + contribution.base_dodge_source,
        base_potion_heal_source=resolved_base.base_potion_heal_source
        + contribution.base_potion_heal_source,
        direct_values=direct_values,
    )


def _build_distribution_candidates(
    calculator_input: CalculatorPresetInput,
) -> list[DistributionState]:
    """스탯 분배 후보 목록 생성"""

    current_state: DistributionState = calculator_input.distribution
    if current_state.is_locked:
        return [current_state]

    max_points: int = calculator_input.level * 5
    used_points: int = (
        current_state.strength
        + current_state.dexterity
        + current_state.vitality
        + current_state.luck
    )
    target_points: int = max_points if current_state.use_reset else used_points
    free_points: int = (
        max_points if current_state.use_reset else max_points - used_points
    )

    candidates: list[DistributionState] = []
    if current_state.use_reset:
        for strength in range(target_points + 1):
            for dexterity in range(target_points - strength + 1):
                for vitality in range(target_points - strength - dexterity + 1):
                    luck: int = target_points - strength - dexterity - vitality
                    candidates.append(
                        DistributionState(
                            strength=strength,
                            dexterity=dexterity,
                            vitality=vitality,
                            luck=luck,
                            is_locked=current_state.is_locked,
                            use_reset=current_state.use_reset,
                        )
                    )
        return candidates

    for add_strength in range(free_points + 1):
        for add_dexterity in range(free_points - add_strength + 1):
            for add_vitality in range(free_points - add_strength - add_dexterity + 1):
                add_luck: int = (
                    free_points - add_strength - add_dexterity - add_vitality
                )
                candidates.append(
                    DistributionState(
                        strength=current_state.strength + add_strength,
                        dexterity=current_state.dexterity + add_dexterity,
                        vitality=current_state.vitality + add_vitality,
                        luck=current_state.luck + add_luck,
                        is_locked=current_state.is_locked,
                        use_reset=current_state.use_reset,
                    )
                )

    return candidates


def _build_danjeon_candidates(
    calculator_input: CalculatorPresetInput,
) -> list[DanjeonState]:
    """단전 후보 목록 생성"""

    current_state: DanjeonState = calculator_input.danjeon
    if current_state.is_locked:
        return [current_state]

    max_points: int = REALM_TIER_SPECS[calculator_input.realm_tier].danjeon_points
    used_points: int = current_state.upper + current_state.middle + current_state.lower
    target_points: int = max_points if current_state.use_reset else used_points
    free_points: int = (
        max_points if current_state.use_reset else max_points - used_points
    )

    candidates: list[DanjeonState] = []
    if current_state.use_reset:
        for upper in range(target_points + 1):
            for middle in range(target_points - upper + 1):
                lower: int = target_points - upper - middle
                candidates.append(
                    DanjeonState(
                        upper=upper,
                        middle=middle,
                        lower=lower,
                        is_locked=current_state.is_locked,
                        use_reset=current_state.use_reset,
                    )
                )
        return candidates

    for add_upper in range(free_points + 1):
        for add_middle in range(free_points - add_upper + 1):
            add_lower: int = free_points - add_upper - add_middle
            candidates.append(
                DanjeonState(
                    upper=current_state.upper + add_upper,
                    middle=current_state.middle + add_middle,
                    lower=current_state.lower + add_lower,
                    is_locked=current_state.is_locked,
                    use_reset=current_state.use_reset,
                )
            )

    return candidates


def _build_title_candidates(
    calculator_input: CalculatorPresetInput,
) -> list[str | None]:
    """칭호 후보 목록 생성"""

    if not calculator_input.owned_titles:
        return [None]

    title_ids: list[str | None] = [None]
    for owned_title in calculator_input.owned_titles:
        title_ids.append(owned_title.title_id)

    return title_ids


def _build_talisman_candidates(
    calculator_input: CalculatorPresetInput,
) -> list[list[str]]:
    """부적 조합 후보 목록 생성"""

    owned_talismans: list[OwnedTalisman] = calculator_input.owned_talismans
    if not owned_talismans:
        return [[]]

    owned_template_map: dict[str, str] = {
        owned_talisman.owned_id: owned_talisman.template_id
        for owned_talisman in owned_talismans
    }
    owned_ids: list[str] = [
        owned_talisman.owned_id for owned_talisman in owned_talismans
    ]
    target_size: int = min(3, len(owned_ids))
    candidates: list[list[str]] = []

    def build_combinations(start_index: int, selected_ids: list[str]) -> None:
        """현재 보유 부적 조합 구성"""

        if len(selected_ids) == target_size:
            candidates.append(selected_ids.copy())
            return

        for current_index in range(start_index, len(owned_ids)):
            owned_id: str = owned_ids[current_index]
            template_id: str = owned_template_map[owned_id]
            if any(
                owned_template_map[selected_id] == template_id
                for selected_id in selected_ids
            ):
                continue

            selected_ids.append(owned_id)
            build_combinations(current_index + 1, selected_ids)
            selected_ids.pop()

    build_combinations(0, [])
    if not candidates:
        return [[]]

    return candidates


def optimize_current_selection(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    context: CalculatorEvaluationContext,
    overall_stats: dict[str, float],
    calculator_input: CalculatorPresetInput,
    target_metric: PowerMetric,
) -> OptimizationResult | None:
    """현재 선택 조합 최적화"""

    # 기준 베이스 분리 검증 실패 시 최적화 중단
    validation: CalculatorBaseValidation = validate_base_state(
        overall_stats=overall_stats,
        calculator_input=calculator_input,
    )
    if not validation.is_valid:
        return None

    base_state: CalculatorBaseState = build_base_state(
        overall_stats=overall_stats,
        calculator_input=calculator_input,
    )

    # 각 선택지 후보 목록 구성
    distribution_candidates: list[DistributionState] = _build_distribution_candidates(
        calculator_input
    )
    danjeon_candidates: list[DanjeonState] = _build_danjeon_candidates(calculator_input)
    title_candidates: list[str | None] = _build_title_candidates(calculator_input)
    talisman_candidates: list[list[str]] = _build_talisman_candidates(calculator_input)

    # 선택 전투력 기준 최고 후보 탐색
    best_result: OptimizationResult | None = None
    best_metric_delta: float | None = None
    for distribution_state in distribution_candidates:
        for danjeon_state in danjeon_candidates:
            for equipped_title_id in title_candidates:
                for equipped_talisman_ids in talisman_candidates:
                    candidate_input: CalculatorPresetInput = CalculatorPresetInput(
                        overall_stats=calculator_input.overall_stats,
                        level=calculator_input.level,
                        realm_tier=calculator_input.realm_tier,
                        distribution=distribution_state,
                        danjeon=danjeon_state,
                        owned_titles=calculator_input.owned_titles,
                        owned_talismans=calculator_input.owned_talismans,
                        equipped=EquippedOptimizationState(
                            equipped_title_id=equipped_title_id,
                            equipped_talisman_ids=equipped_talisman_ids.copy(),
                        ),
                    )
                    candidate_contribution: CalculatorContribution = (
                        build_current_selected_contribution(candidate_input)
                    )
                    optimized_overall_stats: dict[str, float] = (
                        _build_overall_stats_from_base_and_contribution(
                            base_state,
                            candidate_contribution,
                        )
                    )
                    candidate_context: CalculatorEvaluationContext = (
                        build_calculator_context(
                            server_spec=server_spec,
                            preset=preset,
                            skills_info=skills_info,
                            delay_ms=delay_ms,
                            overall_stats=optimized_overall_stats,
                        )
                    )
                    optimized_summary: CalculatorPowerSummary = (
                        candidate_context.baseline_summary
                    )
                    deltas: dict[PowerMetric, float] = calculate_power_deltas(
                        context.baseline_summary,
                        optimized_summary,
                    )
                    metric_delta: float = deltas[target_metric]
                    if (
                        best_metric_delta is not None
                        and metric_delta <= best_metric_delta
                    ):
                        continue

                    best_metric_delta = metric_delta
                    best_result = OptimizationResult(
                        candidate=OptimizationCandidate(
                            distribution=distribution_state,
                            danjeon=danjeon_state,
                            equipped_title_id=equipped_title_id,
                            equipped_talisman_ids=equipped_talisman_ids.copy(),
                        ),
                        deltas=deltas,
                        optimized_overall_stats=optimized_overall_stats,
                    )

    return best_result
