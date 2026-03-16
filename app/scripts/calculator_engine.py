from __future__ import annotations

import random
from collections.abc import Iterator
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
from app.scripts.macro_models import EquippedSkillRef, LinkUseType
from app.scripts.registry.skill_registry import (
    BuffEffect,
    DamageEffect,
    LevelEffect,
    get_builtin_skill_id,
)
from app.scripts.run_macro import get_prepared_link_skill_indices

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
class CalculatorTimelineEvaluationArtifacts:
    """타임라인 평가용 사전 계산 결과"""

    timeline: CalculatorTimeline
    active_buffs_by_hit: tuple[tuple[CalculatorBuffWindow, ...], ...]


@dataclass(frozen=True, slots=True)
class CalculatorSkillUse:
    """계산기용 스킬 사용 이벤트"""

    skill_id: str
    time: float


@dataclass(frozen=True, slots=True)
class CalculatorScheduledBuff:
    """계산기용 버프 이벤트"""

    skill_id: str
    stat_key: StatKey
    start_time: float
    end_time: float
    value: float


@dataclass(frozen=True, slots=True)
class CalculatorDamageEvent:
    """계산기용 최종 피해 이벤트"""

    skill_id: str
    time: float
    damage: float


@dataclass(frozen=True, slots=True)
class CalculatorGraphAttack:
    """그래프 출력용 단일 피해 이벤트"""

    # 그래프 범례와 스킬 기여도 계산에 사용할 스킬 식별자
    skill_id: str
    # 그래프 x축 배치에 사용할 타격 시점
    time: float
    # 그래프 y축 배치에 사용할 최종 피해량
    damage: float


@dataclass(frozen=True, slots=True)
class CalculatorGraphAnalysis:
    """그래프 분석 카드 1행 데이터"""

    # 분석 카드 제목
    title: str
    # 기준값 표기 문자열
    value: str
    # 최소값 표기 문자열
    min: str
    # 최대값 표기 문자열
    max: str
    # 표준편차 표기 문자열
    std: str
    # 25퍼센타일 표기 문자열
    p25: str
    # 50퍼센타일 표기 문자열
    p50: str
    # 75퍼센타일 표기 문자열
    p75: str

    def get_data_from_str(self, data_name: str) -> str:
        """분석 카드 세부 항목 문자열 반환"""

        if not hasattr(self, data_name):
            raise AttributeError(f"{data_name} 항목이 존재하지 않습니다.")

        return str(getattr(self, data_name))


@dataclass(frozen=True, slots=True)
class CalculatorGraphReport:
    """그래프/요약 화면 공용 리포트"""

    # 5종 전투력 원본 수치 맵
    metrics: dict[PowerMetric, float]
    # 그래프 상단 분석 카드 데이터
    analysis: tuple[CalculatorGraphAnalysis, ...] = ()
    # 보스 기준 결정론 타격 이벤트 목록
    deterministic_boss_attacks: tuple[CalculatorGraphAttack, ...] = ()
    # 보스 기준 확률론 타격 이벤트 목록
    random_boss_attacks: tuple[tuple[CalculatorGraphAttack, ...], ...] = ()


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

    timeline_artifacts: CalculatorTimelineEvaluationArtifacts
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
    resolved_base: CalculatorResolvedStats
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
    equipped_talisman_ids: tuple[str, ...]


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
    equipped_title_id: str | None,
    owned_title_map: dict[str, OwnedTitle],
) -> CalculatorContribution:
    """현재 장착 칭호 기여 계산"""

    if equipped_title_id is None:
        return CalculatorContribution()

    # 사전 계산된 칭호 조회 맵 기반 즉시 조회
    equipped_title: OwnedTitle = owned_title_map[equipped_title_id]

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


def _build_owned_title_map(owned_titles: list[OwnedTitle]) -> dict[str, OwnedTitle]:
    """보유 칭호 ID 기준 조회 맵 구성"""

    owned_title_map: dict[str, OwnedTitle] = {
        owned_title.title_id: owned_title for owned_title in owned_titles
    }
    return owned_title_map


def _build_owned_talisman_stat_map(
    owned_talismans: list[OwnedTalisman],
) -> dict[str, tuple[StatKey, float]]:
    """보유 부적 ID 기준 최종 스탯값 조회 맵 구성"""

    talisman_stat_map: dict[str, tuple[StatKey, float]] = {}
    for owned_talisman in owned_talismans:
        talisman_spec: tuple[StatKey, int] | None = _find_talisman_template(
            owned_talisman
        )
        if talisman_spec is None:
            continue

        # 장착 시 즉시 더할 수 있는 최종 스탯값 형태로 고정 저장
        stat_key: StatKey
        grade_offset: int
        stat_key, grade_offset = talisman_spec
        stat_value: float = float((grade_offset * 10) + owned_talisman.level)
        talisman_stat_map[owned_talisman.owned_id] = (stat_key, stat_value)

    return talisman_stat_map


def build_talisman_contribution(
    equipped_talisman_ids: list[str],
    talisman_stat_map: dict[str, tuple[StatKey, float]],
) -> CalculatorContribution:
    """현재 장착 부적 기여 계산"""

    contribution: CalculatorContribution = CalculatorContribution()
    for equipped_id in equipped_talisman_ids:
        stat_key: StatKey
        stat_value: float
        stat_key, stat_value = talisman_stat_map[equipped_id]
        contribution = _add_stat_contribution(contribution, stat_key, stat_value)

    return contribution


def _merge_selection_contributions(
    distribution_contribution: CalculatorContribution,
    danjeon_contribution: CalculatorContribution,
    title_contribution: CalculatorContribution,
    talisman_contribution: CalculatorContribution,
) -> CalculatorContribution:
    """고정 4축 선택 기여 병합"""

    # 스탯 합산 맵 구성
    direct_values: dict[StatKey, float] = {}
    contribution: CalculatorContribution
    for contribution in (
        distribution_contribution,
        danjeon_contribution,
        title_contribution,
        talisman_contribution,
    ):
        stat_key: StatKey
        value: float
        for stat_key, value in contribution.direct_values.items():
            current_value: float = direct_values.get(stat_key, 0.0)
            direct_values[stat_key] = current_value + value

    # 원시/베이스 수치 필드 직접 합산 기반 단일 결과 객체 구성
    merged_contribution: CalculatorContribution = CalculatorContribution(
        raw_strength=distribution_contribution.raw_strength
        + danjeon_contribution.raw_strength
        + title_contribution.raw_strength
        + talisman_contribution.raw_strength,
        raw_dexterity=distribution_contribution.raw_dexterity
        + danjeon_contribution.raw_dexterity
        + title_contribution.raw_dexterity
        + talisman_contribution.raw_dexterity,
        raw_vitality=distribution_contribution.raw_vitality
        + danjeon_contribution.raw_vitality
        + title_contribution.raw_vitality
        + talisman_contribution.raw_vitality,
        raw_luck=distribution_contribution.raw_luck
        + danjeon_contribution.raw_luck
        + title_contribution.raw_luck
        + talisman_contribution.raw_luck,
        base_attack_source=distribution_contribution.base_attack_source
        + danjeon_contribution.base_attack_source
        + title_contribution.base_attack_source
        + talisman_contribution.base_attack_source,
        base_hp_source=distribution_contribution.base_hp_source
        + danjeon_contribution.base_hp_source
        + title_contribution.base_hp_source
        + talisman_contribution.base_hp_source,
        base_attack_percent_source=distribution_contribution.base_attack_percent_source
        + danjeon_contribution.base_attack_percent_source
        + title_contribution.base_attack_percent_source
        + talisman_contribution.base_attack_percent_source,
        base_crit_rate_source=distribution_contribution.base_crit_rate_source
        + danjeon_contribution.base_crit_rate_source
        + title_contribution.base_crit_rate_source
        + talisman_contribution.base_crit_rate_source,
        base_crit_damage_source=distribution_contribution.base_crit_damage_source
        + danjeon_contribution.base_crit_damage_source
        + title_contribution.base_crit_damage_source
        + talisman_contribution.base_crit_damage_source,
        base_drop_rate_source=distribution_contribution.base_drop_rate_source
        + danjeon_contribution.base_drop_rate_source
        + title_contribution.base_drop_rate_source
        + talisman_contribution.base_drop_rate_source,
        base_exp_source=distribution_contribution.base_exp_source
        + danjeon_contribution.base_exp_source
        + title_contribution.base_exp_source
        + talisman_contribution.base_exp_source,
        base_dodge_source=distribution_contribution.base_dodge_source
        + danjeon_contribution.base_dodge_source
        + title_contribution.base_dodge_source
        + talisman_contribution.base_dodge_source,
        base_potion_heal_source=distribution_contribution.base_potion_heal_source
        + danjeon_contribution.base_potion_heal_source
        + title_contribution.base_potion_heal_source
        + talisman_contribution.base_potion_heal_source,
        direct_values=direct_values,
    )
    return merged_contribution


def build_current_selected_contribution(
    calculator_input: CalculatorPresetInput,
    owned_title_map: dict[str, OwnedTitle],
    talisman_stat_map: dict[str, tuple[StatKey, float]],
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
        calculator_input.equipped.equipped_title_id,
        owned_title_map,
    )
    talisman_contribution: CalculatorContribution = build_talisman_contribution(
        calculator_input.equipped.equipped_talisman_ids,
        talisman_stat_map,
    )
    return _merge_selection_contributions(
        distribution_contribution,
        danjeon_contribution,
        title_contribution,
        talisman_contribution,
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


def _build_skill_sequence(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
) -> tuple[EquippedSkillRef, ...]:
    """우선순위 기준 스킬 순서 구성"""

    # 현재 배치된 스킬만 우선순위 후보로 제한
    placed_refs: list[EquippedSkillRef] = preset.skills.get_placed_skill_refs(
        server_spec
    )
    skill_sequence: list[EquippedSkillRef] = []

    # 우선순위 숫자 기준 1차 정렬 구성
    for target_priority in range(1, len(placed_refs) + 1):
        for skill_ref in placed_refs:
            skill_id: str = preset.skills.get_placed_skill_id(skill_ref)
            setting: "SkillUsageSetting" = skills_info[skill_id]
            if setting.priority != target_priority:
                continue

            skill_sequence.append(skill_ref)

    # 우선순위 미지정 스킬은 기존 배치 순서 유지
    for skill_ref in placed_refs:
        if skill_ref in skill_sequence:
            continue

        skill_sequence.append(skill_ref)

    return tuple(skill_sequence)


def _update_prepared_skills(
    placed_refs: list[EquippedSkillRef],
    skill_cooltime_timers_ms: dict[EquippedSkillRef, int],
    skill_cooltimes_ms: dict[EquippedSkillRef, int],
    elapsed_time_ms: int,
    prepared_skills: set[EquippedSkillRef],
) -> None:
    """쿨타임 종료 스킬 준비 상태 반영"""

    # 현재 시점까지 쿨타임이 끝난 스킬만 준비 상태로 복귀
    for skill_ref in placed_refs:
        if skill_ref in prepared_skills:
            continue

        elapsed_from_last_use: int = (
            elapsed_time_ms - skill_cooltime_timers_ms[skill_ref]
        )
        if elapsed_from_last_use < skill_cooltimes_ms[skill_ref]:
            continue

        prepared_skills.add(skill_ref)


def _build_next_task_list(
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    prepared_skills: set[EquippedSkillRef],
    link_skill_requirements: list[list[EquippedSkillRef]],
    auto_link_skills: list[list[EquippedSkillRef]],
    skill_sequence: tuple[EquippedSkillRef, ...],
) -> list[EquippedSkillRef]:
    """현재 시점 기준 실행 가능한 다음 작업 목록 구성"""

    # 자동 연계 완성 여부를 먼저 확인
    prepared_link_indices: list[int] = get_prepared_link_skill_indices(
        prepared_skills=prepared_skills,
        link_skills_requirements=link_skill_requirements,
    )
    if prepared_link_indices:
        target_link_skills: list[EquippedSkillRef] = auto_link_skills[
            prepared_link_indices[0]
        ]
        task_list: list[EquippedSkillRef] = []
        for skill_ref in target_link_skills:
            prepared_skills.discard(skill_ref)
            task_list.append(skill_ref)

        return task_list

    # 연계에 속한 스킬인지 빠르게 판단할 수 있도록 평탄화
    linked_skill_refs: set[EquippedSkillRef] = {
        skill_ref
        for requirement_group in link_skill_requirements
        for skill_ref in requirement_group
    }

    # 우선순위 순회하며 단독 사용 스킬 또는 일반 스킬 하나 선택
    for skill_ref in skill_sequence:
        if skill_ref not in prepared_skills:
            continue

        skill_id: str = preset.skills.get_placed_skill_id(skill_ref)
        setting: "SkillUsageSetting" = skills_info[skill_id]
        if skill_ref in linked_skill_refs and setting.use_alone:
            prepared_skills.discard(skill_ref)
            return [skill_ref]

        if skill_ref not in linked_skill_refs and setting.use_skill:
            prepared_skills.discard(skill_ref)
            return [skill_ref]

    return []


def build_skill_use_sequence(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    cooltime_reduction: float,
) -> tuple[CalculatorSkillUse, ...]:
    """입력 상태 기준 60초 스킬 사용 순서 구성"""

    # 실제 배치된 스킬이 없으면 빈 사용 기록 반환
    placed_refs: list[EquippedSkillRef] = preset.skills.get_placed_skill_refs(
        server_spec
    )
    if not placed_refs:
        return ()

    # 자동 연계 계산에 필요한 배치/설정 맵 구성
    prepared_skills: set[EquippedSkillRef] = set(placed_refs)
    skill_ref_map: dict[str, EquippedSkillRef] = preset.skills.get_placed_skill_ref_map(
        server_spec
    )
    auto_link_skills: list[list[EquippedSkillRef]] = [
        [skill_ref_map[skill_id] for skill_id in link_skill.skills]
        for link_skill in preset.link_skills
        if link_skill.use_type == LinkUseType.AUTO
        and all(skill_id in skill_ref_map for skill_id in link_skill.skills)
    ]
    link_skill_requirements: list[list[EquippedSkillRef]] = [
        [skill_ref for skill_ref in link_skill_group]
        for link_skill_group in auto_link_skills
    ]
    skill_sequence: tuple[EquippedSkillRef, ...] = _build_skill_sequence(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
    )

    # 쿨타임 감소를 반영한 스킬별 재사용 대기시간 계산
    skill_cooltime_timers_ms: dict[EquippedSkillRef, int] = {
        skill_ref: 0 for skill_ref in placed_refs
    }
    skill_cooltimes_ms: dict[EquippedSkillRef, int] = {
        skill_ref: int(
            server_spec.skill_registry.get(
                preset.skills.get_placed_skill_id(skill_ref)
            ).cooltime
            * (100 - cooltime_reduction)
            * 10
        )
        for skill_ref in placed_refs
    }

    # 60초 범위 내 실제 스킬 사용 시점 기록
    task_list: list[EquippedSkillRef] = []
    used_skills: list[CalculatorSkillUse] = []
    elapsed_time_ms: int = 0
    while elapsed_time_ms < 60000:
        if not task_list:
            _update_prepared_skills(
                placed_refs=placed_refs,
                skill_cooltime_timers_ms=skill_cooltime_timers_ms,
                skill_cooltimes_ms=skill_cooltimes_ms,
                elapsed_time_ms=elapsed_time_ms,
                prepared_skills=prepared_skills,
            )
            task_list = _build_next_task_list(
                preset=preset,
                skills_info=skills_info,
                prepared_skills=prepared_skills,
                link_skill_requirements=link_skill_requirements,
                auto_link_skills=auto_link_skills,
                skill_sequence=skill_sequence,
            )

        if task_list:
            skill_ref: EquippedSkillRef = task_list.pop(0)
            skill_id: str = preset.skills.get_placed_skill_id(skill_ref)
            used_skills.append(
                CalculatorSkillUse(
                    skill_id=skill_id,
                    time=round(elapsed_time_ms * 0.001, 2),
                )
            )
            skill_cooltime_timers_ms[skill_ref] = elapsed_time_ms
            elapsed_time_ms += int(delay_ms)
            continue

        # 모든 준비 스킬이 없으면 가장 빨리 돌아오는 스킬까지 점프
        waiting_refs: list[EquippedSkillRef] = [
            skill_ref for skill_ref in placed_refs if skill_ref not in prepared_skills
        ]
        if not waiting_refs:
            break

        next_cooltime_ms: int = min(
            skill_cooltimes_ms[skill_ref]
            - (elapsed_time_ms - skill_cooltime_timers_ms[skill_ref])
            for skill_ref in waiting_refs
        )
        elapsed_time_ms += next_cooltime_ms

    return tuple(used_skills)


def build_simulation_events(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    cooltime_reduction: float,
) -> tuple[tuple[CalculatorHitEvent, ...], tuple[CalculatorScheduledBuff, ...]]:
    """공유 스케줄러 기준 공격/버프 이벤트 구성"""

    # 평타 간격과 배치 스킬 사용 기록을 각각 이벤트로 확장
    basic_attack_skill_id: str = get_builtin_skill_id(server_spec.id, "평타")
    basic_attack_interval_ms: int = int((100 - cooltime_reduction) * 10)
    hit_events: list[CalculatorHitEvent] = []
    for current_time_ms in range(0, 60000, basic_attack_interval_ms):
        hit_events.append(
            CalculatorHitEvent(
                skill_id=basic_attack_skill_id,
                time=round(current_time_ms * 0.001, 2),
                multiplier=1.0,
                is_skill=False,
            )
        )

    skill_uses: tuple[CalculatorSkillUse, ...] = build_skill_use_sequence(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        cooltime_reduction=cooltime_reduction,
    )

    # 현재 스크롤 레벨 기준 데미지/버프 효과 테이블 조회
    placed_skill_ids: list[str] = preset.skills.get_placed_skill_ids()
    damage_effects_map: dict[str, list[DamageEffect]]
    buff_effects_map: dict[str, list[BuffEffect]]
    damage_effects_map, buff_effects_map = build_skill_effect_maps(
        server_spec=server_spec,
        preset=preset,
        placed_skill_ids=placed_skill_ids,
    )

    # 사용 시점과 효과 테이블을 조합해 최종 이벤트 생성
    buff_events: list[CalculatorScheduledBuff] = []
    for skill_use in skill_uses:
        damage_effects: list[DamageEffect] = damage_effects_map[skill_use.skill_id]
        buff_effects: list[BuffEffect] = buff_effects_map[skill_use.skill_id]
        for damage_effect in damage_effects:
            hit_events.append(
                CalculatorHitEvent(
                    skill_id=skill_use.skill_id,
                    time=round(skill_use.time + damage_effect.time, 2),
                    multiplier=damage_effect.damage,
                    is_skill=True,
                )
            )

        for buff_effect in buff_effects:
            buff_events.append(
                CalculatorScheduledBuff(
                    skill_id=skill_use.skill_id,
                    stat_key=StatKey(str(buff_effect.stat)),
                    start_time=round(skill_use.time + buff_effect.time, 2),
                    end_time=round(
                        skill_use.time + buff_effect.time + buff_effect.duration,
                        2,
                    ),
                    value=float(buff_effect.value),
                )
            )

    # 시각화/평가 일관성을 위한 시간순 정렬
    ordered_hit_events: tuple[CalculatorHitEvent, ...] = tuple(
        sorted(hit_events, key=lambda item: item.time)
    )
    ordered_buff_events: tuple[CalculatorScheduledBuff, ...] = tuple(
        sorted(buff_events, key=lambda item: item.start_time)
    )
    return ordered_hit_events, ordered_buff_events


def build_calculator_timeline(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    cooltime_reduction: float,
) -> CalculatorTimeline:
    """메인 화면 스킬 상태 기준 계산기용 60초 타임라인 생성"""

    # 공유 스케줄러가 생성한 이벤트를 계산기 타임라인으로 정규화
    hit_events: tuple[CalculatorHitEvent, ...]
    buff_events: tuple[CalculatorScheduledBuff, ...]
    hit_events, buff_events = build_simulation_events(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        cooltime_reduction=cooltime_reduction,
    )
    converted_buff_windows: list[CalculatorBuffWindow] = []
    for buff_event in buff_events:
        converted_buff_windows.append(
            CalculatorBuffWindow(
                stat_key=buff_event.stat_key,
                start_time=buff_event.start_time,
                end_time=buff_event.end_time,
                value=buff_event.value,
            )
        )

    merged_buff_windows: tuple[CalculatorBuffWindow, ...] = _merge_buff_windows(
        converted_buff_windows
    )
    timeline: CalculatorTimeline = CalculatorTimeline(
        hit_events=hit_events,
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


def _build_timeline_evaluation_artifacts(
    timeline: CalculatorTimeline,
) -> CalculatorTimelineEvaluationArtifacts:
    """타임라인 평가 반복용 활성 버프 스냅샷 구성"""

    # 타격 이벤트 순서 기준 활성 버프 튜플 1회 계산
    active_buffs_by_hit: list[tuple[CalculatorBuffWindow, ...]] = []
    hit_event: CalculatorHitEvent
    for hit_event in timeline.hit_events:
        active_buffs: tuple[CalculatorBuffWindow, ...] = _collect_active_buffs(
            timeline.buff_windows,
            hit_event.time,
        )
        active_buffs_by_hit.append(active_buffs)

    # 동일 타임라인 재평가 시 재사용할 불변 구조로 고정
    artifacts: CalculatorTimelineEvaluationArtifacts = (
        CalculatorTimelineEvaluationArtifacts(
            timeline=timeline,
            active_buffs_by_hit=tuple(active_buffs_by_hit),
        )
    )
    return artifacts


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


def _calculate_random_hit_damage(
    resolved_stats: dict[StatKey, float],
    hit_event: CalculatorHitEvent,
    is_boss: bool,
    rng: random.Random,
) -> float:
    """단일 타격 랜덤 피해량 계산"""

    # 공격력 표시값에 최종 공격력과 보스 공격력을 차례대로 반영
    attack_power: float = float(resolved_stats[StatKey.ATTACK])
    attack_power *= 1.0 + (float(resolved_stats[StatKey.FINAL_ATTACK_PERCENT]) * 0.01)
    if is_boss:
        attack_power *= 1.0 + (
            float(resolved_stats[StatKey.BOSS_ATTACK_PERCENT]) * 0.01
        )

    # 스킬 계수와 랜덤 최소/최대 데미지 폭 반영
    damage: float = attack_power * hit_event.multiplier
    damage *= rng.uniform(1.0, 1.2)

    # 치명타 확률과 치명타 피해량 기반 랜덤 치명타 반영
    crit_rate: float = min(float(resolved_stats[StatKey.CRIT_RATE_PERCENT]), 100.0)
    crit_damage: float = float(resolved_stats[StatKey.CRIT_DAMAGE_PERCENT])
    if rng.random() < (crit_rate * 0.01):
        damage *= 1.0 + (crit_damage * 0.01)

    # 평타가 아닌 스킬 타격에만 스킬 피해량 보정 적용
    if hit_event.is_skill:
        damage *= 1.0 + (float(resolved_stats[StatKey.SKILL_DAMAGE_PERCENT]) * 0.01)

    return damage


def build_damage_events(
    timeline: CalculatorTimeline,
    resolved_stats: CalculatorResolvedStats,
    is_boss: bool,
    deterministic: bool,
    random_seed: float | None = None,
) -> list[CalculatorDamageEvent]:
    """타임라인과 스탯 기준 최종 피해 이벤트 목록 구성"""

    artifacts: CalculatorTimelineEvaluationArtifacts = (
        _build_timeline_evaluation_artifacts(timeline)
    )
    damage_events: list[CalculatorDamageEvent] = []
    hit_event: CalculatorHitEvent
    buffed_stats: dict[StatKey, float]
    for hit_event, buffed_stats in _iterate_buffed_hit_events(
        artifacts,
        resolved_stats,
    ):
        # 결정론/확률론 모드에 따라 최종 타격 피해량 계산
        damage: float
        if deterministic:
            damage = _calculate_hit_damage(
                resolved_stats=buffed_stats,
                hit_event=hit_event,
                is_boss=is_boss,
            )

        else:
            damage = _calculate_random_hit_damage(
                resolved_stats=buffed_stats,
                hit_event=hit_event,
                is_boss=is_boss,
                rng=random.Random(random_seed),
            )

        damage_events.append(
            CalculatorDamageEvent(
                skill_id=hit_event.skill_id,
                time=hit_event.time,
                damage=damage,
            )
        )

    return damage_events


def _iterate_buffed_hit_events(
    artifacts: CalculatorTimelineEvaluationArtifacts,
    resolved_stats: CalculatorResolvedStats,
) -> Iterator[tuple[CalculatorHitEvent, dict[StatKey, float]]]:
    """타임라인 아티팩트 기준 버프 반영 타격 순회"""

    hit_index: int
    hit_event: CalculatorHitEvent
    for hit_index, hit_event in enumerate(artifacts.timeline.hit_events):
        active_buffs: tuple[CalculatorBuffWindow, ...] = artifacts.active_buffs_by_hit[
            hit_index
        ]
        buffed_stats: dict[StatKey, float] = _apply_active_buffs(
            resolved_stats, active_buffs
        )
        yield hit_event, buffed_stats


def evaluate_calculator_power(
    artifacts: CalculatorTimelineEvaluationArtifacts,
    resolved_stats: CalculatorResolvedStats,
) -> CalculatorPowerSummary:
    """사전 계산 타임라인 아티팩트 기준 5종 전투력 계산"""

    # 타격별 활성 버프 스냅샷 재사용 기반 총데미지 누적
    total_boss_damage: float = 0.0
    total_normal_damage: float = 0.0

    hit_event: CalculatorHitEvent
    buffed_stats: dict[StatKey, float]
    for hit_event, buffed_stats in _iterate_buffed_hit_events(
        artifacts,
        resolved_stats,
    ):
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

    # 전투력 계산
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
    timeline_artifacts: CalculatorTimelineEvaluationArtifacts = (
        _build_timeline_evaluation_artifacts(timeline)
    )

    # 기준 타임라인 아티팩트와 기준 스탯으로 기준 전투력 계산
    baseline_summary: CalculatorPowerSummary = evaluate_calculator_power(
        artifacts=timeline_artifacts,
        resolved_stats=baseline_stats,
    )

    return CalculatorEvaluationContext(
        timeline_artifacts=timeline_artifacts,
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

    # 기준 타임라인 아티팩트 재사용 기반 전투력 재평가
    summary: CalculatorPowerSummary = evaluate_calculator_power(
        artifacts=context.timeline_artifacts,
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
    owned_title_map: dict[str, OwnedTitle] = _build_owned_title_map(
        calculator_input.owned_titles
    )
    talisman_stat_map: dict[str, tuple[StatKey, float]] = (
        _build_owned_talisman_stat_map(calculator_input.owned_talismans)
    )
    contribution: CalculatorContribution = build_current_selected_contribution(
        calculator_input,
        owned_title_map,
        talisman_stat_map,
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
        resolved_base=resolve_calculator_stats(base_overall_stats),
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
    resolved_base: CalculatorResolvedStats = base_state.resolved_base

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
    resolved_base: CalculatorResolvedStats = base_state.resolved_base

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

    # 최적화 1회 동안 불변인 보유 칭호/부적 조회 구조 사전 계산
    owned_title_map: dict[str, OwnedTitle] = _build_owned_title_map(
        calculator_input.owned_titles
    )
    talisman_stat_map: dict[str, tuple[StatKey, float]] = (
        _build_owned_talisman_stat_map(calculator_input.owned_talismans)
    )

    # 기여 모델 사전 계산
    distribution_entries: list[tuple[DistributionState, CalculatorContribution]] = []
    for distribution_state in distribution_candidates:
        distribution_contribution: CalculatorContribution = (
            build_distribution_contribution(distribution_state)
        )
        distribution_entries.append((distribution_state, distribution_contribution))

    danjeon_entries: list[tuple[DanjeonState, CalculatorContribution]] = []
    for danjeon_state in danjeon_candidates:
        danjeon_contribution: CalculatorContribution = build_danjeon_contribution(
            danjeon_state
        )
        danjeon_entries.append((danjeon_state, danjeon_contribution))

    title_entries: list[tuple[str | None, CalculatorContribution]] = []
    for equipped_title_id in title_candidates:
        title_contribution: CalculatorContribution = build_title_contribution(
            equipped_title_id,
            owned_title_map,
        )
        title_entries.append((equipped_title_id, title_contribution))

    talisman_entries: list[tuple[list[str], CalculatorContribution]] = []
    for equipped_talisman_ids in talisman_candidates:
        talisman_contribution: CalculatorContribution = build_talisman_contribution(
            equipped_talisman_ids,
            talisman_stat_map,
        )
        talisman_entries.append((equipped_talisman_ids, talisman_contribution))

    # 기준 스킬속도 타임라인 재사용용 캐시 초기 상태 구성
    baseline_skill_speed: float = float(
        context.baseline_stats.values[StatKey.SKILL_SPEED_PERCENT]
    )
    baseline_speed_cache_key: float = round(baseline_skill_speed, 2)
    timeline_cache: dict[float, CalculatorTimelineEvaluationArtifacts] = {
        baseline_speed_cache_key: context.timeline_artifacts
    }

    # 선택 전투력 기준 최고 후보 탐색
    best_result: OptimizationResult | None = None
    best_metric_delta: float | None = None
    for distribution_state, distribution_contribution in distribution_entries:
        for danjeon_state, danjeon_contribution in danjeon_entries:
            for equipped_title_id, title_contribution in title_entries:
                for equipped_talisman_ids, talisman_contribution in talisman_entries:
                    # 후보 파트별 기여 직접 병합 기반 최종 스탯 구성
                    candidate_contribution: CalculatorContribution = (
                        _merge_selection_contributions(
                            distribution_contribution,
                            danjeon_contribution,
                            title_contribution,
                            talisman_contribution,
                        )
                    )
                    optimized_overall_stats: dict[str, float] = (
                        _build_overall_stats_from_base_and_contribution(
                            base_state,
                            candidate_contribution,
                        )
                    )

                    # 후보 최종 스탯 및 스킬속도 기준 타임라인 캐시 키 정규화
                    optimized_resolved_stats: CalculatorResolvedStats = (
                        resolve_calculator_stats(overall_stats=optimized_overall_stats)
                    )
                    candidate_skill_speed: float = float(
                        optimized_resolved_stats.values[StatKey.SKILL_SPEED_PERCENT]
                    )
                    speed_cache_key: float = round(candidate_skill_speed, 2)

                    # 동일 스킬속도 구간 타임라인 재활용 및 최초 1회만 재계산
                    cached_timeline_artifacts: (
                        CalculatorTimelineEvaluationArtifacts | None
                    ) = timeline_cache.get(speed_cache_key)
                    if cached_timeline_artifacts is None:
                        cached_timeline: CalculatorTimeline = build_calculator_timeline(
                            server_spec=server_spec,
                            preset=preset,
                            skills_info=skills_info,
                            delay_ms=delay_ms,
                            cooltime_reduction=candidate_skill_speed,
                        )
                        cached_timeline_artifacts = (
                            _build_timeline_evaluation_artifacts(cached_timeline)
                        )
                        timeline_cache[speed_cache_key] = cached_timeline_artifacts

                    # 캐시된 타임라인 활성 버프 스냅샷과 후보 스탯 기준 전투력 재평가
                    optimized_summary: CalculatorPowerSummary = (
                        evaluate_calculator_power(
                            artifacts=cached_timeline_artifacts,
                            resolved_stats=optimized_resolved_stats,
                        )
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
                            equipped_talisman_ids=tuple(equipped_talisman_ids),
                        ),
                        deltas=deltas,
                        optimized_overall_stats=optimized_overall_stats,
                    )

    return best_result
