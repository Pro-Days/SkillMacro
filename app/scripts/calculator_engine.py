"""
# 계산기 스탯 시스템 구조

## 전체 스탯 입력 → 원시 스탯 역산

사용자가 "전체 스탯"에 입력하는 값은 **게임에서 보이는 최종 스탯** (% 보정, 파생 효과 적용됨)이다.
이 값은 저장 시 `build_internal_base_stats()` (`calculator_engine.py`)를 거쳐 **원시 스탯으로 역산**되어 `calculator_input.base_stats`에 저장된다.

- 입력 경로: `simul_ui.py` → `_read_stats()` → `build_internal_base_stats(resolved_input)` (simul_ui.py:3534-3535)
- 역산 로직: `build_internal_base_stats()` (calculator_engine.py:665) — % 제거, 파생 스탯(공격력, HP, 크리티컬 등) 역산

## 모든 스탯 기여는 동일한 레벨에서 동작

아래 항목들은 **전부 원시 스탯(`base_stats`)에 단순 가산** → `resolve()`로 최종 스탯 산출하는 동일한 경로를 탄다:

| 입력 항목 | 적용 함수 | 적용 대상 |
|---|---|---|
| 분배 | `build_distribution_contribution()` | STR, DEX, VIT, LUCK |
| 단전 | `build_danjeon_contribution()` | HP%, 저항%, 공격력%, 드랍률%, 경험치% |
| 칭호 | `build_title_contribution()` | 칭호별 임의 스탯 |
| 부적 | `build_talisman_contribution()` | 부적별 임의 스탯 |
| 변화량 | `with_changes()` 직접 호출 | 사용자 지정 임의 스탯 |

공통 경로: `with_changes()` (원시 스탯에 가산) → `resolve()` (% 보정 + 파생 효과 적용) → `FinalStats`

따라서 **변화량에 분배 차이값을 입력하면 분배 변경 시뮬레이션이 정확하게 동작**한다.
예: 분배를 힘 -10, 민첩 +10으로 바꾸고 싶으면 변화량에 `힘 -10, 민첩 +10`을 입력하면 된다.
"""

from __future__ import annotations

import heapq
import os
import random
from collections.abc import Callable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeVar

from app.scripts.calculator_models import (
    OVERALL_STAT_ORDER,
    REALM_TIER_SPECS,
    TALISMAN_SPECS,
    BaseStats,
    CalculatorPresetInput,
    DanjeonState,
    DistributionState,
    FinalStats,
    OwnedTalisman,
    OwnedTitle,
    PowerMetric,
    RealmSpec,
    RealmTier,
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
    from app.scripts.registry.skill_registry import ScrollDef


# 전투력 표시 순서 고정
DISPLAY_POWER_METRICS: tuple[PowerMetric, ...] = (
    PowerMetric.BOSS_DAMAGE,
    PowerMetric.NORMAL_DAMAGE,
    PowerMetric.BOSS,
    PowerMetric.NORMAL,
    PowerMetric.OFFICIAL,
)


# 전투력 한글 라벨
POWER_METRIC_LABELS: dict[PowerMetric, str] = {
    PowerMetric.BOSS_DAMAGE: "보스 데미지",
    PowerMetric.NORMAL_DAMAGE: "일반 데미지",
    PowerMetric.BOSS: "보스 전투력",
    PowerMetric.NORMAL: "일반 전투력",
    PowerMetric.OFFICIAL: "공식 전투력",
}


# 타임라인 길이 상수
TIMELINE_SECONDS: float = 60.0
TIMELINE_MILLISECONDS: int = 60000


# 역산 시 음수 허용 범위
INVERSE_NEGATIVE_TOLERANCE: float = 0.01

# _fast_resolve 용 enum 키 모듈 수준 캐시 (매 호출마다 enum descriptor 접근 제거)
_FK_STR: StatKey = StatKey.STR
_FK_STR_PERCENT: StatKey = StatKey.STR_PERCENT
_FK_DEXTERITY: StatKey = StatKey.DEXTERITY
_FK_DEXTERITY_PERCENT: StatKey = StatKey.DEXTERITY_PERCENT
_FK_VITALITY: StatKey = StatKey.VITALITY
_FK_VITALITY_PERCENT: StatKey = StatKey.VITALITY_PERCENT
_FK_LUCK: StatKey = StatKey.LUCK
_FK_LUCK_PERCENT: StatKey = StatKey.LUCK_PERCENT
_FK_ATTACK: StatKey = StatKey.ATTACK
_FK_ATTACK_PERCENT: StatKey = StatKey.ATTACK_PERCENT
_FK_HP: StatKey = StatKey.HP
_FK_HP_PERCENT: StatKey = StatKey.HP_PERCENT
_FK_CRIT_RATE_PERCENT: StatKey = StatKey.CRIT_RATE_PERCENT
_FK_CRIT_DAMAGE_PERCENT: StatKey = StatKey.CRIT_DAMAGE_PERCENT
_FK_DROP_RATE_PERCENT: StatKey = StatKey.DROP_RATE_PERCENT
_FK_EXP_PERCENT: StatKey = StatKey.EXP_PERCENT
_FK_DODGE_PERCENT: StatKey = StatKey.DODGE_PERCENT
_FK_POTION_HEAL_PERCENT: StatKey = StatKey.POTION_HEAL_PERCENT
_FK_SKILL_SPEED_PERCENT: StatKey = StatKey.SKILL_SPEED_PERCENT

# _evaluate_distribution_selection 용 사전 계산 상수
_STAT_ORDER_KEYS: tuple[StatKey, ...] = OVERALL_STAT_ORDER
_STAT_ORDER_VALUES: tuple[str, ...] = tuple(sk.value for sk in OVERALL_STAT_ORDER)

# 기울기 기반 필터링 상수
_GRADIENT_TOP_K: int = 15
_GRADIENT_EXACT_THRESHOLD: int = 500

# 보스 전투력 생존 계수 튜닝 상수
_BOSS_HP_FACTOR_DIVISOR: float = 200.0
_BOSS_HP_FACTOR_EXPONENT: float = 0.4
_BOSS_POTION_FACTOR_DIVISOR: float = 25.0
_BOSS_POTION_FACTOR_EXPONENT: float = 0.5
_BOSS_DODGE_FACTOR_EXPONENT: float = 1.0
_BOSS_RESIST_FACTOR_EXPONENT: float = 0.6


def _get_boss_potion_base_heal(level: int) -> float:
    """레벨 구간별 5초 포션 기본 회복량 반환"""

    # 레벨 구간별 포션 기본 회복량 결정 블록
    if level >= 150:
        return 180.0

    if level >= 100:
        return 120.0

    if level >= 50:
        return 70.0

    return 20.0


def _compute_power_gradient(
    timeline_artifacts: TimelineEvaluationArtifacts,
    base_changed_stats: dict[StatKey, float],
    target_metric: PowerMetric,
    relevant_stat_keys: frozenset[StatKey],
) -> dict[StatKey, float]:
    """기준점에서의 전투력 기울기 (∂power/∂stat) 계산"""

    base_resolved: FinalStats = _fast_resolve(base_changed_stats)
    base_power: PowerSummary = evaluate_calculator_power(
        timeline_artifacts, base_resolved
    )
    base_value: float = base_power.metrics[target_metric]

    gradient: dict[StatKey, float] = {}
    for stat_key in relevant_stat_keys:
        perturbed: dict[StatKey, float] = base_changed_stats.copy()
        perturbed[stat_key] = perturbed.get(stat_key, 0.0) + 1.0
        perturbed_resolved: FinalStats = _fast_resolve(perturbed)
        perturbed_power: PowerSummary = evaluate_calculator_power(
            timeline_artifacts, perturbed_resolved
        )
        gradient[stat_key] = perturbed_power.metrics[target_metric] - base_value

    return gradient


def _score_contribution_by_gradient(
    gradient: dict[StatKey, float],
    contribution: Contribution,
) -> float:
    """기울기 기반 기여 점수 계산 (선형 근사)"""

    score: float = 0.0
    for stat_key, value in contribution.values.items():
        grad_value: float | None = gradient.get(stat_key)
        if grad_value is not None:
            score += grad_value * value
    return score


def _fast_resolve(changed_stats: dict[StatKey, float]) -> FinalStats:
    """enum 접근 최소화된 고속 resolve (사전 구성된 StatKey dict 전용)"""

    final_strength: float = changed_stats[_FK_STR] * (
        1.0 + (changed_stats[_FK_STR_PERCENT] * 0.01)
    )
    final_dexterity: float = changed_stats[_FK_DEXTERITY] * (
        1.0 + (changed_stats[_FK_DEXTERITY_PERCENT] * 0.01)
    )
    final_vitality: float = changed_stats[_FK_VITALITY] * (
        1.0 + (changed_stats[_FK_VITALITY_PERCENT] * 0.01)
    )
    final_luck: float = changed_stats[_FK_LUCK] * (
        1.0 + (changed_stats[_FK_LUCK_PERCENT] * 0.01)
    )

    resolved_values: dict[StatKey, float] = changed_stats.copy()

    resolved_values[_FK_STR] = final_strength
    resolved_values[_FK_DEXTERITY] = final_dexterity
    resolved_values[_FK_VITALITY] = final_vitality
    resolved_values[_FK_LUCK] = final_luck

    attack_percent: float = changed_stats[_FK_ATTACK_PERCENT] + (final_dexterity * 0.3)
    resolved_values[_FK_ATTACK_PERCENT] = attack_percent

    resolved_values[_FK_ATTACK] = (changed_stats[_FK_ATTACK] + final_strength) * (
        1.0 + (attack_percent * 0.01)
    )

    resolved_values[_FK_HP] = (changed_stats[_FK_HP] + (final_vitality * 5.0)) * (
        1.0 + (changed_stats[_FK_HP_PERCENT] * 0.01)
    )

    resolved_values[_FK_CRIT_RATE_PERCENT] = changed_stats[_FK_CRIT_RATE_PERCENT] + (
        final_dexterity * 0.05
    )

    resolved_values[_FK_CRIT_DAMAGE_PERCENT] = changed_stats[
        _FK_CRIT_DAMAGE_PERCENT
    ] + (final_strength * 0.1)

    resolved_values[_FK_DROP_RATE_PERCENT] = changed_stats[_FK_DROP_RATE_PERCENT] + (
        final_luck * 0.2
    )

    resolved_values[_FK_EXP_PERCENT] = changed_stats[_FK_EXP_PERCENT] + (
        final_luck * 0.2
    )

    resolved_values[_FK_DODGE_PERCENT] = changed_stats[_FK_DODGE_PERCENT] + (
        final_vitality * 0.03
    )

    resolved_values[_FK_POTION_HEAL_PERCENT] = changed_stats[
        _FK_POTION_HEAL_PERCENT
    ] + (final_vitality * 0.5)

    return FinalStats(values=resolved_values)


INVERSE_ROUND_DIGITS: int = 6


@dataclass(frozen=True, slots=True)
class BuffWindow:
    """버프 활성 구간"""

    stat_key: StatKey
    start_time: float
    end_time: float
    value: float


@dataclass(frozen=True, slots=True)
class HitEvent:
    """단일 타격 이벤트"""

    skill_id: str
    time: float
    multiplier: float


@dataclass(frozen=True, slots=True)
class Timeline:
    """타임라인: 타격 이벤트, 버프 활성 구간 정보"""

    hit_events: tuple[HitEvent, ...]
    buff_windows: tuple[BuffWindow, ...]


@dataclass(frozen=True, slots=True)
class TimelineSegment:
    """전투력 평가를 위한 타임라인 세그먼트: 활성 버프 구간"""

    start_time: float
    end_time: float
    duration: float
    active_buffs: tuple[BuffWindow, ...]


@dataclass(frozen=True, slots=True)
class TimelineEvaluationArtifacts:
    """타임라인 사전 계산 결과"""

    timeline: Timeline

    # 각 HitEvent 마다 활성화된 버프 구간들의 튜플 목록
    # 동일한 HitEvent 를 구분하기 위해 dict를 사용하지 않음.
    active_buffs_by_hit: tuple[tuple[BuffWindow, ...], ...]

    timeline_segments: tuple[TimelineSegment, ...]
    level: int = 0


@dataclass(frozen=True, slots=True)
class SkillUseEvent:
    """스킬 사용 이벤트"""

    skill_id: str
    time: float


@dataclass(frozen=True, slots=True)
class BuffEvent:
    """버프 이벤트"""

    skill_id: str
    stat_key: StatKey
    start_time: float
    end_time: float
    value: float


@dataclass(frozen=True, slots=True)
class DamageEvent:
    """최종 데미지 이벤트"""

    skill_id: str
    time: float
    damage: float


@dataclass(frozen=True, slots=True)
class GraphDamageEvent:
    """그래프 출력용 단일 피해 이벤트"""

    # 그래프 범례와 스킬 기여도 계산에 사용할 스킬 식별자
    skill_id: str
    # 그래프 x축 배치에 사용할 타격 시점
    time: float
    # 그래프 y축 배치에 사용할 최종 피해량
    damage: float


@dataclass(frozen=True, slots=True)
class GraphAnalysis:
    """그래프 분석 카드 행 데이터"""

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
class GraphReport:
    """그래프/요약 화면 공용 리포트"""

    # 5종 전투력 수치
    metrics: dict[PowerMetric, float]
    # 그래프 분석 카드 데이터
    analysis: tuple[GraphAnalysis, ...] = ()

    # 보스 기준 결정론 타격 이벤트 목록
    deterministic_boss_attacks: tuple[GraphDamageEvent, ...] = ()

    # 보스 기준 확률론 타격 이벤트 목록
    random_boss_attacks: tuple[tuple[GraphDamageEvent, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class PowerSummary:
    """계산기 전투력 요약"""

    metrics: dict[PowerMetric, float]


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """평가 기준이 되는 초기 상태 컨텍스트"""

    timeline_artifacts: TimelineEvaluationArtifacts
    baseline_base_stats: BaseStats
    baseline_final_stats: FinalStats
    baseline_summary: PowerSummary
    server_spec: "ServerSpec"
    preset: "MacroPreset"
    skills_info: dict[str, "SkillUsageSetting"]
    delay_ms: int


@dataclass(frozen=True, slots=True)
class LevelUpEvaluation:
    """
    레벨업 효율 계산 결과
    1 레벨업으로 얻는 `체력 +5과 스탯 포인트 5개`를 최적으로 분배했을 때의 스탯 분배와 전투력 변화량
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
    """무공비급 레벨 상승 효율 계산 결과"""

    scroll_id: str
    scroll_name: str
    next_level: int
    deltas: dict[PowerMetric, float]


@dataclass(frozen=True, slots=True)
class Contribution:
    """현재 선택 기여 합산 결과"""

    values: dict[StatKey, float] = field(default_factory=dict)

    def add(self, stat_key: StatKey, value: float) -> "Contribution":
        """스탯 변화가 반영된 (frozen=True이므로) 새 기여 반환"""

        next_values: dict[StatKey, float] = self.values.copy()
        next_values[stat_key] = next_values.get(stat_key, 0.0) + value

        return type(self)(values=next_values)

    def merge(self, *others: "Contribution") -> "Contribution":
        """여러 기여를 합산한 새 기여 반환"""

        merged_values: dict[StatKey, float] = self.values.copy()

        for target in others:
            for stat_key, value in target.values.items():
                merged_values[stat_key] = merged_values.get(stat_key, 0.0) + value

        return type(self)(values=merged_values)

    def apply_to(self, base_stats: BaseStats, is_add: bool = True) -> BaseStats:
        """베이스 스탯에 현재 기여를 적용"""

        return base_stats.with_changes(self.values, is_add=is_add)


@dataclass(frozen=True, slots=True)
class BaseState:
    """기준 베이스 스탯 분리 결과"""

    base_stats: BaseStats
    final_stats: FinalStats
    contribution: Contribution


@dataclass(frozen=True, slots=True)
class BaseValidation:
    """기준 베이스 스탯 검증 결과"""

    is_valid: bool
    message: str


@dataclass(frozen=True, slots=True)
class OptimizationCandidate:
    """최적화 후보 선택 상태"""

    distribution: DistributionState
    danjeon: DanjeonState
    equipped_title_name: str | None
    equipped_talisman_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """최적화 최종 결과"""

    candidate: OptimizationCandidate
    deltas: dict[PowerMetric, float]
    base_stats: BaseStats


@dataclass(frozen=True, slots=True)
class DistributionSearchRange:
    """스탯 분배 범위 노드"""

    strength_min: int
    strength_max: int
    dexterity_min: int
    dexterity_max: int
    vitality_min: int
    vitality_max: int
    luck_min: int
    target_points: int
    is_locked: bool
    use_reset: bool


EntryPayload = TypeVar("EntryPayload")


def calculate_power_deltas(
    baseline_summary: PowerSummary,
    target_summary: PowerSummary,
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


def build_distribution_contribution(
    distribution: DistributionState,
) -> Contribution:
    """현재 스탯 분배 기여 계산"""

    return (
        Contribution()
        .add(StatKey.STR, distribution.strength)
        .add(StatKey.DEXTERITY, distribution.dexterity)
        .add(StatKey.VITALITY, distribution.vitality)
        .add(StatKey.LUCK, distribution.luck)
    )


def build_danjeon_contribution(danjeon: DanjeonState) -> Contribution:
    """현재 단전 기여 계산"""

    return (
        Contribution()
        .add(StatKey.HP_PERCENT, danjeon.upper * 3)
        .add(StatKey.RESIST_PERCENT, danjeon.upper)
        .add(StatKey.ATTACK_PERCENT, danjeon.middle)
        .add(StatKey.DROP_RATE_PERCENT, danjeon.lower * 1.5)
        .add(StatKey.EXP_PERCENT, danjeon.lower * 0.5)
    )


def build_title_contribution(
    equipped_title_name: str | None,
    owned_title_map: dict[str, OwnedTitle],
) -> Contribution:
    """현재 장착 칭호 기여 계산"""

    if equipped_title_name is None:
        return Contribution()

    equipped_title: OwnedTitle = owned_title_map[equipped_title_name]

    contribution: Contribution = Contribution()
    for title_stat in equipped_title.stats:
        if title_stat is None:
            continue

        contribution = contribution.add(title_stat.stat_key, title_stat.value)

    return contribution


def build_talisman_contribution(
    equipped_talisman_names: list[str],
    talisman_stat_map: dict[str, tuple[StatKey, float]],
) -> Contribution:
    """현재 장착 부적 기여 계산"""

    contribution: Contribution = Contribution()
    for equipped_name in equipped_talisman_names:
        # 빈 슬롯 문자열 및 비어 있는 장착명 제외
        if not equipped_name:
            continue

        stat_key: StatKey
        stat_value: float
        stat_key, stat_value = talisman_stat_map[equipped_name]
        contribution = contribution.add(stat_key, stat_value)

    return contribution


def _build_owned_title_map(owned_titles: list[OwnedTitle]) -> dict[str, OwnedTitle]:
    """보유 칭호 ID 기준 조회 맵 구성"""

    owned_title_map: dict[str, OwnedTitle] = {
        owned_title.name: owned_title for owned_title in owned_titles
    }
    return owned_title_map


def _build_owned_talisman_stat_map(
    owned_talismans: list[OwnedTalisman],
) -> dict[str, tuple[StatKey, float]]:
    """보유 부적 ID 기준 최종 스탯값 조회 맵 구성"""

    talisman_stat_map: dict[str, tuple[StatKey, float]] = {}

    for owned_talisman in owned_talismans:
        # 부적 정의 조회 블록
        talisman_spec: tuple[StatKey, dict[int, float]] | None = None

        for spec in TALISMAN_SPECS:
            if spec.name == owned_talisman.name:
                talisman_spec = spec.stat_key, spec.level_stats
                break

        if talisman_spec is None:
            continue

        # 동일 이름 최고 레벨 유지 블록
        stat_key, level_stats = talisman_spec
        stat_value: float = level_stats[owned_talisman.level]
        current_entry: tuple[StatKey, float] | None = talisman_stat_map.get(
            owned_talisman.name
        )
        if current_entry is not None and current_entry[1] >= stat_value:
            continue

        talisman_stat_map[owned_talisman.name] = (
            stat_key,
            stat_value,
        )

    return talisman_stat_map


def build_current_selected_contribution(
    calculator_input: CalculatorPresetInput,
    owned_title_map: dict[str, OwnedTitle],
    talisman_stat_map: dict[str, tuple[StatKey, float]],
) -> Contribution:
    """현재 선택 상태 전체 기여 계산"""

    # 현재 스탯 분배/단전/칭호/부적 기여를 하나의 모델로 병합
    distribution_contribution: Contribution = build_distribution_contribution(
        calculator_input.distribution
    )
    danjeon_contribution: Contribution = build_danjeon_contribution(
        calculator_input.danjeon
    )
    title_contribution: Contribution = build_title_contribution(
        calculator_input.equipped_state.equipped_title_name,
        owned_title_map,
    )
    talisman_contribution: Contribution = build_talisman_contribution(
        calculator_input.equipped_state.equipped_talisman_names,
        talisman_stat_map,
    )
    return distribution_contribution.merge(
        danjeon_contribution,
        title_contribution,
        talisman_contribution,
    )


def build_internal_base_stats(base_stats: BaseStats) -> BaseStats:
    """전체 스탯 입력값을 내부 계산용 원시 스탯으로 역산"""

    # 최종 합산 입력값 기준 스탯 맵 복원 블록
    resolved_values: dict[StatKey, float] = base_stats.to_stat_map()

    # 주스탯 역산 비율 계산 블록
    strength_ratio: float = 1.0 + (resolved_values[StatKey.STR_PERCENT] * 0.01)
    dexterity_ratio: float = 1.0 + (resolved_values[StatKey.DEXTERITY_PERCENT] * 0.01)
    vitality_ratio: float = 1.0 + (resolved_values[StatKey.VITALITY_PERCENT] * 0.01)
    luck_ratio: float = 1.0 + (resolved_values[StatKey.LUCK_PERCENT] * 0.01)

    # 최종 주스탯 기준 원시 주스탯 복원 블록
    final_strength: float = resolved_values[StatKey.STR]
    final_dexterity: float = resolved_values[StatKey.DEXTERITY]
    final_vitality: float = resolved_values[StatKey.VITALITY]
    final_luck: float = resolved_values[StatKey.LUCK]
    raw_strength: float = final_strength / strength_ratio
    raw_dexterity: float = final_dexterity / dexterity_ratio
    raw_vitality: float = final_vitality / vitality_ratio
    raw_luck: float = final_luck / luck_ratio

    # 주스탯 파생 항목 역산 블록
    raw_attack_percent: float = resolved_values[StatKey.ATTACK_PERCENT] - (
        final_dexterity * 0.3
    )
    attack_ratio: float = 1.0 + (resolved_values[StatKey.ATTACK_PERCENT] * 0.01)
    hp_ratio: float = 1.0 + (resolved_values[StatKey.HP_PERCENT] * 0.01)
    raw_attack: float = (resolved_values[StatKey.ATTACK] / attack_ratio) - (
        final_strength
    )
    raw_hp: float = (resolved_values[StatKey.HP] / hp_ratio) - (final_vitality * 5.0)
    raw_crit_rate: float = resolved_values[StatKey.CRIT_RATE_PERCENT] - (
        final_dexterity * 0.05
    )
    raw_crit_damage: float = resolved_values[StatKey.CRIT_DAMAGE_PERCENT] - (
        final_strength * 0.1
    )
    raw_drop_rate: float = resolved_values[StatKey.DROP_RATE_PERCENT] - (
        final_luck * 0.2
    )
    raw_exp: float = resolved_values[StatKey.EXP_PERCENT] - (final_luck * 0.2)
    raw_dodge: float = resolved_values[StatKey.DODGE_PERCENT] - (final_vitality * 0.03)
    raw_potion_heal: float = resolved_values[StatKey.POTION_HEAL_PERCENT] - (
        final_vitality * 0.5
    )

    # 내부 계산용 원시 스탯 맵 재구성 블록
    raw_values: dict[StatKey, float] = resolved_values.copy()
    raw_values[StatKey.STR] = raw_strength
    raw_values[StatKey.DEXTERITY] = raw_dexterity
    raw_values[StatKey.VITALITY] = raw_vitality
    raw_values[StatKey.LUCK] = raw_luck
    raw_values[StatKey.ATTACK_PERCENT] = raw_attack_percent
    raw_values[StatKey.ATTACK] = raw_attack
    raw_values[StatKey.HP] = raw_hp
    raw_values[StatKey.CRIT_RATE_PERCENT] = raw_crit_rate
    raw_values[StatKey.CRIT_DAMAGE_PERCENT] = raw_crit_damage
    raw_values[StatKey.DROP_RATE_PERCENT] = raw_drop_rate
    raw_values[StatKey.EXP_PERCENT] = raw_exp
    raw_values[StatKey.DODGE_PERCENT] = raw_dodge
    raw_values[StatKey.POTION_HEAL_PERCENT] = raw_potion_heal

    return BaseStats.from_stat_map(_normalize_inverse_stat_map(raw_values))


def _normalize_inverse_stat_map(
    stat_values: dict[StatKey, float],
) -> dict[StatKey, float]:
    """역산 및 제거 결과 스탯값 정규화"""

    # 역산 잔차 정규화 블록
    normalized_values: dict[StatKey, float] = {}
    stat_key: StatKey
    stat_value: float
    for stat_key, stat_value in stat_values.items():
        rounded_value: float = round(stat_value, INVERSE_ROUND_DIGITS)
        if -INVERSE_NEGATIVE_TOLERANCE <= rounded_value < 0.0:
            normalized_values[stat_key] = 0.0
            continue

        normalized_values[stat_key] = rounded_value

    return normalized_values


def _merge_buff_windows(
    buff_windows: list[BuffWindow],
) -> tuple[BuffWindow, ...]:
    """동일 스탯/값 버프 구간 병합"""

    # 동일 스탯/값 버프 구간끼리 그룹화
    grouped: dict[tuple[StatKey, float], list[BuffWindow]] = {}
    for buff_window in buff_windows:
        group_key: tuple[StatKey, float] = (buff_window.stat_key, buff_window.value)

        if group_key not in grouped:
            grouped[group_key] = []

        grouped[group_key].append(buff_window)

    # 그룹별로 구간 병합 후 전체 구간 리스트에 추가
    merged_windows: list[BuffWindow] = []
    for group_key, group_windows in grouped.items():
        sorted_windows: list[BuffWindow] = sorted(
            group_windows,
            key=lambda item: item.start_time,
        )
        current_window: BuffWindow = sorted_windows[0]

        for target_window in sorted_windows[1:]:
            # 현재 구간과 겹치는 구간은 병합
            if target_window.start_time <= current_window.end_time:
                current_window = BuffWindow(
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

    ordered_windows: tuple[BuffWindow, ...] = tuple(
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
    current_line_index: int,
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

    # 자동 연계에 속한 스킬 참조 집합 구성
    linked_skill_refs: set[EquippedSkillRef] = {
        skill_ref
        for requirement_group in link_skill_requirements
        for skill_ref in requirement_group
    }
    first_usable_skill_ref: EquippedSkillRef | None = None
    first_usable_allows_solo_swap: bool = False
    first_current_line_skill_ref: EquippedSkillRef | None = None

    # 우선순위 순서대로 사용 가능한 일반 스킬 후보 탐색
    for skill_ref in skill_sequence:
        if skill_ref not in prepared_skills:
            continue

        skill_id: str = preset.skills.get_placed_skill_id(skill_ref)
        setting: "SkillUsageSetting" = skills_info[skill_id]
        can_use_linked_skill_alone: bool = (
            skill_ref in linked_skill_refs and setting.use_alone
        )
        can_use_regular_skill: bool = (
            skill_ref not in linked_skill_refs and setting.use_skill
        )

        # 일반 스킬 선택 조건을 만족하는 후보만 유지
        if not can_use_linked_skill_alone and not can_use_regular_skill:
            continue

        # 전체 최상위 후보와 현재 줄 후보를 각각 기록
        if first_usable_skill_ref is None:
            first_usable_skill_ref = skill_ref
            first_usable_allows_solo_swap = setting.use_solo_swap

        if (
            skill_ref.line_index == current_line_index
            and first_current_line_skill_ref is None
        ):
            first_current_line_skill_ref = skill_ref

    # 일반 스킬 후보가 없으면 빈 목록 반환
    if first_usable_skill_ref is None:
        return []

    # 현재 줄 스킬은 즉시 선택
    if first_usable_skill_ref.line_index == current_line_index:
        prepared_skills.discard(first_usable_skill_ref)
        return [first_usable_skill_ref]

    # 단독 스왑 허용 스킬은 우선순위대로 즉시 선택
    if first_usable_allows_solo_swap:
        prepared_skills.discard(first_usable_skill_ref)
        return [first_usable_skill_ref]

    # 현재 줄 스킬이 있으면 스왑을 미루고 먼저 선택
    if first_current_line_skill_ref is not None:
        prepared_skills.discard(first_current_line_skill_ref)
        return [first_current_line_skill_ref]

    # 현재 줄에 남은 스킬이 없으면 다른 줄 최상위 스킬 선택
    prepared_skills.discard(first_usable_skill_ref)
    return [first_usable_skill_ref]


def build_skill_use_sequence(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    cooltime_reduction: float,
) -> tuple[SkillUseEvent, ...]:
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
    used_skills: list[SkillUseEvent] = []
    elapsed_time_ms: int = 0
    current_line_index: int = 0
    while elapsed_time_ms < TIMELINE_MILLISECONDS:
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
                current_line_index=current_line_index,
            )

        if task_list:
            skill_ref: EquippedSkillRef = task_list.pop(0)
            skill_id: str = preset.skills.get_placed_skill_id(skill_ref)
            used_skills.append(
                SkillUseEvent(
                    skill_id=skill_id,
                    time=round(elapsed_time_ms * 0.001, 2),
                )
            )
            # 사용한 스킬 줄 상태를 다음 선택 조건에 반영
            current_line_index = skill_ref.line_index
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
) -> tuple[tuple[HitEvent, ...], tuple[BuffEvent, ...]]:
    """공유 스케줄러 기준 공격/버프 이벤트 구성"""

    # 평타 간격과 배치 스킬 사용 기록을 각각 이벤트로 확장
    basic_attack_skill_id: str = get_builtin_skill_id(server_spec.id, "평타")
    hit_events: list[HitEvent] = []
    for current_time_ms in range(
        0,
        TIMELINE_MILLISECONDS,
        700,
    ):
        hit_events.append(
            HitEvent(
                skill_id=basic_attack_skill_id,
                time=round(current_time_ms * 0.001, 2),
                multiplier=1.0,
            )
        )

    skill_uses: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        cooltime_reduction=cooltime_reduction,
    )

    # 현재 무공비급 레벨 기준 데미지/버프 효과 테이블 조회
    placed_skill_ids: list[str] = preset.skills.get_placed_skill_ids()
    damage_effects_map: dict[str, list[DamageEffect]]
    buff_effects_map: dict[str, list[BuffEffect]]
    damage_effects_map, buff_effects_map = build_skill_effect_maps(
        server_spec=server_spec,
        preset=preset,
        placed_skill_ids=placed_skill_ids,
    )

    # 사용 시점과 효과 테이블을 조합해 최종 이벤트 생성
    buff_events: list[BuffEvent] = []
    for skill_use in skill_uses:
        damage_effects: list[DamageEffect] = damage_effects_map[skill_use.skill_id]
        buff_effects: list[BuffEffect] = buff_effects_map[skill_use.skill_id]
        for damage_effect in damage_effects:
            hit_events.append(
                HitEvent(
                    skill_id=skill_use.skill_id,
                    time=round(skill_use.time + damage_effect.time, 2),
                    multiplier=damage_effect.damage,
                )
            )

        for buff_effect in buff_effects:
            buff_events.append(
                BuffEvent(
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
    ordered_hit_events: tuple[HitEvent, ...] = tuple(
        sorted(hit_events, key=lambda item: item.time)
    )
    ordered_buff_events: tuple[BuffEvent, ...] = tuple(
        sorted(buff_events, key=lambda item: item.start_time)
    )
    return ordered_hit_events, ordered_buff_events


def build_calculator_timeline(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    cooltime_reduction: float,
) -> Timeline:
    """메인 화면 스킬 상태 기준 계산기용 60초 타임라인 생성"""

    # 공유 스케줄러가 생성한 이벤트를 계산기 타임라인으로 정규화
    hit_events: tuple[HitEvent, ...]
    buff_events: tuple[BuffEvent, ...]
    hit_events, buff_events = build_simulation_events(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        cooltime_reduction=cooltime_reduction,
    )
    converted_buff_windows: list[BuffWindow] = []
    for buff_event in buff_events:
        converted_buff_windows.append(
            BuffWindow(
                stat_key=buff_event.stat_key,
                start_time=buff_event.start_time,
                end_time=buff_event.end_time,
                value=buff_event.value,
            )
        )

    merged_buff_windows: tuple[BuffWindow, ...] = _merge_buff_windows(
        converted_buff_windows
    )
    timeline: Timeline = Timeline(
        hit_events=hit_events,
        buff_windows=merged_buff_windows,
    )
    return timeline


def _apply_active_buffs(
    resolved_stats: FinalStats,
    active_buffs: tuple[BuffWindow, ...],
) -> dict[StatKey, float]:
    """현재 시점 활성 버프 반영 스탯 구성"""

    buffed_values: dict[StatKey, float] = resolved_stats.values.copy()
    for active_buff in active_buffs:
        current_value: float = float(buffed_values[active_buff.stat_key])
        buffed_values[active_buff.stat_key] = current_value + active_buff.value

    return buffed_values


def _collect_active_buffs(
    buff_windows: tuple[BuffWindow, ...],
    target_time: float,
) -> tuple[BuffWindow, ...]:
    """특정 시점 활성 버프 목록 수집"""

    active_buffs: tuple[BuffWindow, ...] = tuple(
        buff_window
        for buff_window in buff_windows
        if buff_window.start_time <= target_time <= buff_window.end_time
    )
    return active_buffs


def _build_timeline_evaluation_artifacts(
    timeline: Timeline,
    level: int = 0,
) -> TimelineEvaluationArtifacts:
    """타임라인 평가 반복용 활성 버프 스냅샷 구성"""

    # 타격 이벤트 순서 기준 활성 버프 튜플 1회 계산
    active_buffs_by_hit: list[tuple[BuffWindow, ...]] = []
    hit_event: HitEvent
    for hit_event in timeline.hit_events:
        active_buffs: tuple[BuffWindow, ...] = _collect_active_buffs(
            timeline.buff_windows,
            hit_event.time,
        )
        active_buffs_by_hit.append(active_buffs)

    # 데미지가 아닌 전투력 평가용 시간 경계와 활성 버프 구간 계산
    boundary_values: set[float] = {0.0, TIMELINE_SECONDS}
    buff_window: BuffWindow
    for buff_window in timeline.buff_windows:
        clamped_start_time: float = max(
            0.0,
            min(buff_window.start_time, TIMELINE_SECONDS),
        )
        clamped_end_time: float = max(
            0.0,
            min(buff_window.end_time, TIMELINE_SECONDS),
        )
        boundary_values.add(clamped_start_time)
        boundary_values.add(clamped_end_time)

    # 반열린 구간 기준 비타격 전투력 평가 세그먼트 구성
    ordered_boundaries: tuple[float, ...] = tuple(sorted(boundary_values))
    timeline_segments: list[TimelineSegment] = []
    boundary_index: int
    for boundary_index in range(len(ordered_boundaries) - 1):
        start_time: float = ordered_boundaries[boundary_index]
        end_time: float = ordered_boundaries[boundary_index + 1]

        # 세그먼트 시작 시점 활성 버프 수집
        segment_active_buffs: tuple[BuffWindow, ...] = tuple(
            current_buff_window
            for current_buff_window in timeline.buff_windows
            if (
                current_buff_window.start_time
                <= start_time
                < current_buff_window.end_time
            )
        )
        timeline_segments.append(
            TimelineSegment(
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                active_buffs=segment_active_buffs,
            )
        )

    # 동일 타임라인 재평가 시 재사용할 불변 구조로 고정
    artifacts: TimelineEvaluationArtifacts = TimelineEvaluationArtifacts(
        timeline=timeline,
        active_buffs_by_hit=tuple(active_buffs_by_hit),
        timeline_segments=tuple(timeline_segments),
        level=level,
    )
    return artifacts


def _calculate_hit_damage(
    resolved_stats: dict[StatKey, float],
    hit_event: HitEvent,
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

    # 기대 치명타 배율 계산
    crit_rate: float = min(float(resolved_stats[StatKey.CRIT_RATE_PERCENT]), 100.0)
    crit_damage: float = float(resolved_stats[StatKey.CRIT_DAMAGE_PERCENT])
    crit_bonus_ratio: float = (crit_damage - 100.0) * 0.01
    damage: float = attack_power * hit_event.multiplier
    damage *= 1.0 + ((crit_rate * 0.01) * crit_bonus_ratio)

    damage *= 1.0 + (float(resolved_stats[StatKey.SKILL_DAMAGE_PERCENT]) * 0.01)

    return damage


def _calculate_random_hit_damage(
    resolved_stats: dict[StatKey, float],
    hit_event: HitEvent,
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
    damage *= rng.uniform(0.95, 1.05)

    # 치명타 추가 배율 계산
    crit_rate: float = min(float(resolved_stats[StatKey.CRIT_RATE_PERCENT]), 100.0)
    crit_damage: float = float(resolved_stats[StatKey.CRIT_DAMAGE_PERCENT])
    crit_bonus_ratio: float = (crit_damage - 100.0) * 0.01
    if rng.random() < (crit_rate * 0.01):
        damage *= 1.0 + crit_bonus_ratio

    damage *= 1.0 + (float(resolved_stats[StatKey.SKILL_DAMAGE_PERCENT]) * 0.01)

    return damage


def build_damage_events(
    timeline: Timeline,
    resolved_stats: FinalStats,
    is_boss: bool,
    deterministic: bool,
    random_seed: float | None = None,
) -> list[DamageEvent]:
    """타임라인과 스탯 기준 최종 피해 이벤트 목록 구성"""

    artifacts: TimelineEvaluationArtifacts = _build_timeline_evaluation_artifacts(
        timeline
    )
    damage_events: list[DamageEvent] = []

    # 결정론 기준 타격 이벤트 순회 및 피해량 누적
    if deterministic:
        hit_event: HitEvent
        buffed_stats: dict[StatKey, float]
        for hit_event, buffed_stats in _iterate_buffed_hit_events(
            artifacts,
            resolved_stats,
        ):
            # 기대 치명타 기반 단일 타격 피해량 계산
            damage: float = _calculate_hit_damage(
                resolved_stats=buffed_stats,
                hit_event=hit_event,
                is_boss=is_boss,
            )

            # 계산된 타격 이벤트 결과 누적
            damage_events.append(
                DamageEvent(
                    skill_id=hit_event.skill_id,
                    time=hit_event.time,
                    damage=damage,
                )
            )

        return damage_events

    # 확률론 기준 시뮬레이션 전체에서 재사용할 난수 생성기 구성
    rng: random.Random = random.Random(random_seed)

    # 확률론 기준 타격 이벤트 순회 및 피해량 누적
    hit_event: HitEvent
    buffed_stats: dict[StatKey, float]
    for hit_event, buffed_stats in _iterate_buffed_hit_events(
        artifacts,
        resolved_stats,
    ):
        # 동일 시뮬레이션의 연속 난수 상태를 반영한 단일 타격 피해량 계산
        damage: float = _calculate_random_hit_damage(
            resolved_stats=buffed_stats,
            hit_event=hit_event,
            is_boss=is_boss,
            rng=rng,
        )

        # 계산된 타격 이벤트 결과 누적
        damage_events.append(
            DamageEvent(
                skill_id=hit_event.skill_id,
                time=hit_event.time,
                damage=damage,
            )
        )

    return damage_events


def _iterate_buffed_hit_events(
    artifacts: TimelineEvaluationArtifacts,
    resolved_stats: FinalStats,
) -> Iterator[tuple[HitEvent, dict[StatKey, float]]]:
    """타임라인 아티팩트 기준 버프 반영 타격 순회"""

    hit_index: int
    hit_event: HitEvent
    for hit_index, hit_event in enumerate(artifacts.timeline.hit_events):
        active_buffs: tuple[BuffWindow, ...] = artifacts.active_buffs_by_hit[hit_index]
        buffed_stats: dict[StatKey, float] = _apply_active_buffs(
            resolved_stats, active_buffs
        )
        yield hit_event, buffed_stats


def evaluate_calculator_power(
    artifacts: TimelineEvaluationArtifacts,
    resolved_stats: FinalStats,
) -> PowerSummary:
    """사전 계산 타임라인 아티팩트 기준 5종 전투력 계산"""

    # enum 키 상수를 로컬 변수로 캐시하여 반복 descriptor 접근 제거
    _ATTACK: StatKey = StatKey.ATTACK
    _FINAL_ATTACK_PERCENT: StatKey = StatKey.FINAL_ATTACK_PERCENT
    _BOSS_ATTACK_PERCENT: StatKey = StatKey.BOSS_ATTACK_PERCENT
    _CRIT_RATE_PERCENT: StatKey = StatKey.CRIT_RATE_PERCENT
    _CRIT_DAMAGE_PERCENT: StatKey = StatKey.CRIT_DAMAGE_PERCENT
    _SKILL_DAMAGE_PERCENT: StatKey = StatKey.SKILL_DAMAGE_PERCENT
    _HP: StatKey = StatKey.HP
    _DODGE_PERCENT: StatKey = StatKey.DODGE_PERCENT
    _RESIST_PERCENT: StatKey = StatKey.RESIST_PERCENT
    _POTION_HEAL_PERCENT: StatKey = StatKey.POTION_HEAL_PERCENT
    _DROP_RATE_PERCENT: StatKey = StatKey.DROP_RATE_PERCENT
    _EXP_PERCENT: StatKey = StatKey.EXP_PERCENT
    potion_base_heal: float = _get_boss_potion_base_heal(artifacts.level)

    base_values: dict[StatKey, float] = resolved_stats.values
    hit_events: tuple[HitEvent, ...] = artifacts.timeline.hit_events
    all_active_buffs: tuple[tuple[BuffWindow, ...], ...] = artifacts.active_buffs_by_hit

    # 동일 버프 조합에 대한 스탯 캐시 (dict.copy 횟수 대폭 감소)
    buff_stats_cache: dict[int, dict[StatKey, float]] = {}

    # 타격별 활성 버프 스냅샷 재사용 기반 총데미지 누적
    total_boss_damage: float = 0.0
    total_normal_damage: float = 0.0

    # 연속 동일 버프 참조 빠른 건너뛰기 (id() + dict.get 호출 제거)
    prev_active_buffs: tuple[BuffWindow, ...] | None = None
    cached_buffed_stats: dict[StatKey, float] = base_values

    hit_index: int
    hit_event: HitEvent
    for hit_index, hit_event in enumerate(hit_events):
        active_buffs: tuple[BuffWindow, ...] = all_active_buffs[hit_index]
        if active_buffs is not prev_active_buffs:
            prev_active_buffs = active_buffs
            buff_id: int = id(active_buffs)
            buffed_stats: dict[StatKey, float] | None = buff_stats_cache.get(buff_id)
            if buffed_stats is None:
                buffed_stats = base_values.copy()
                for active_buff in active_buffs:
                    buffed_stats[active_buff.stat_key] = (
                        buffed_stats[active_buff.stat_key] + active_buff.value
                    )
                buff_stats_cache[buff_id] = buffed_stats
            cached_buffed_stats = buffed_stats
        buffed_stats = cached_buffed_stats

        # 인라인된 데미지 계산 (함수 호출 오버헤드 제거)
        multiplier: float = hit_event.multiplier
        attack_power: float = buffed_stats[_ATTACK]
        attack_power *= 1.0 + (buffed_stats[_FINAL_ATTACK_PERCENT] * 0.01)

        # 치명타 기대 배율 계산
        crit_rate: float = buffed_stats[_CRIT_RATE_PERCENT]
        if crit_rate > 100.0:
            crit_rate = 100.0

        crit_damage: float = buffed_stats[_CRIT_DAMAGE_PERCENT]
        crit_bonus_ratio: float = (crit_damage - 100.0) * 0.01
        skill_damage_mult: float = 1.0 + (buffed_stats[_SKILL_DAMAGE_PERCENT] * 0.01)
        crit_mult: float = 1.0 + ((crit_rate * 0.01) * crit_bonus_ratio)
        base_damage: float = attack_power * multiplier * crit_mult * skill_damage_mult

        # 보스 데미지: 보스 공격력% 추가 반영
        boss_attack_mult: float = 1.0 + (buffed_stats[_BOSS_ATTACK_PERCENT] * 0.01)
        total_boss_damage += base_damage * boss_attack_mult
        total_normal_damage += base_damage

    # 세그먼트별 비타격 전투력 배수 시간가중 평균 누적
    weighted_boss_multiplier_sum: float = 0.0
    weighted_normal_multiplier_sum: float = 0.0
    timeline_segment: TimelineSegment
    for timeline_segment in artifacts.timeline_segments:
        seg_buffs: tuple[BuffWindow, ...] = timeline_segment.active_buffs
        seg_buff_id: int = id(seg_buffs)
        segment_stats: dict[StatKey, float] | None = buff_stats_cache.get(seg_buff_id)
        if segment_stats is None:
            segment_stats = base_values.copy()
            for active_buff in seg_buffs:
                segment_stats[active_buff.stat_key] = (
                    segment_stats[active_buff.stat_key] + active_buff.value
                )
            buff_stats_cache[seg_buff_id] = segment_stats

        # 보스 전투력용 생존 배수 계산
        hp_value: float = segment_stats[_HP]
        dodge_value: float = segment_stats[_DODGE_PERCENT]
        resist_value: float = segment_stats[_RESIST_PERCENT]
        potion_heal_percent_value: float = segment_stats[_POTION_HEAL_PERCENT]
        dodge_denominator: float = 1.0 - (dodge_value * 0.01)
        if dodge_denominator < 0.01:
            dodge_denominator = 0.01

        # 음수 입력 방지
        resist_multiplier: float = 1.0 + (resist_value * 0.01)
        if resist_multiplier < 0.01:
            resist_multiplier = 0.01

        hp_factor_input: float = 1.0 + (max(hp_value, 0.0) / _BOSS_HP_FACTOR_DIVISOR)
        potion_heal_value: float = potion_base_heal * (
            1.0 + (potion_heal_percent_value * 0.01)
        )
        potion_factor_input: float = 1.0 + (
            max(potion_heal_value, 0.0) / _BOSS_POTION_FACTOR_DIVISOR
        )

        # 체력과 포션의 역할을 분리한 보스 생존 배수 계산 블록
        boss_multiplier: float = hp_factor_input**_BOSS_HP_FACTOR_EXPONENT
        boss_multiplier *= potion_factor_input**_BOSS_POTION_FACTOR_EXPONENT
        boss_multiplier *= (1.0 / dodge_denominator) ** _BOSS_DODGE_FACTOR_EXPONENT
        boss_multiplier *= resist_multiplier**_BOSS_RESIST_FACTOR_EXPONENT
        weighted_boss_multiplier_sum += boss_multiplier * timeline_segment.duration

        # 일반 전투력용 획득 배수 계산
        drop_rate_value: float = segment_stats[_DROP_RATE_PERCENT]
        exp_value: float = segment_stats[_EXP_PERCENT]

        normal_multiplier: float = 1.0 + (drop_rate_value * 0.01)
        normal_multiplier *= 1.0 + (exp_value * 0.01)
        weighted_normal_multiplier_sum += normal_multiplier * timeline_segment.duration

    # 60초 기준 평균 배수로 최종 전투력 계산
    averaged_boss_multiplier: float = weighted_boss_multiplier_sum / TIMELINE_SECONDS
    averaged_normal_multiplier: float = (
        weighted_normal_multiplier_sum / TIMELINE_SECONDS
    )
    boss_power: float = total_boss_damage * averaged_boss_multiplier
    normal_power: float = total_normal_damage * averaged_normal_multiplier

    official_power: float = (total_boss_damage + total_normal_damage) * 0.5

    metrics: dict[PowerMetric, float] = {
        PowerMetric.BOSS_DAMAGE: total_boss_damage,
        PowerMetric.NORMAL_DAMAGE: total_normal_damage,
        PowerMetric.BOSS: boss_power,
        PowerMetric.NORMAL: normal_power,
        PowerMetric.OFFICIAL: official_power,
    }

    return PowerSummary(metrics=metrics)


def build_calculator_context(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    base_stats: BaseStats,
) -> EvaluationContext:
    """현재 계산기 입력 기준 평가 컨텍스트 구성"""

    baseline_final_stats: FinalStats = base_stats.resolve()

    # 현재 스킬속도 기준 타임라인 구성
    timeline: Timeline = build_calculator_timeline(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        cooltime_reduction=baseline_final_stats.values[StatKey.SKILL_SPEED_PERCENT],
    )
    timeline_artifacts: TimelineEvaluationArtifacts = (
        _build_timeline_evaluation_artifacts(
            timeline,
            level=preset.info.calculator.level,
        )
    )

    # 기준 타임라인 아티팩트와 기준 스탯으로 기준 전투력 계산
    baseline_summary: PowerSummary = evaluate_calculator_power(
        artifacts=timeline_artifacts,
        resolved_stats=baseline_final_stats,
    )

    return EvaluationContext(
        timeline_artifacts=timeline_artifacts,
        baseline_base_stats=base_stats,
        baseline_final_stats=baseline_final_stats,
        baseline_summary=baseline_summary,
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
    )


def evaluate_stat_changes(
    context: EvaluationContext,
    stat_changes: dict[StatKey, float],
) -> PowerSummary:
    """베이스 스탯 변화량 반영 후 전투력 계산"""

    # 기준 입력의 내부 원시 스탯 기준 변화량 적용 블록
    resolved_stats: FinalStats = context.baseline_base_stats.resolve(stat_changes)

    # 스킬속도 변화 여부 기준 타임라인 재사용 분기 블록
    timeline_artifacts: TimelineEvaluationArtifacts = context.timeline_artifacts
    baseline_skill_speed: float = float(
        context.baseline_final_stats.values[StatKey.SKILL_SPEED_PERCENT]
    )
    resolved_skill_speed: float = float(
        resolved_stats.values[StatKey.SKILL_SPEED_PERCENT]
    )
    if resolved_skill_speed != baseline_skill_speed:

        # 변경된 스킬속도 기준 타임라인 재구성 블록
        updated_timeline: Timeline = build_calculator_timeline(
            server_spec=context.server_spec,
            preset=context.preset,
            skills_info=context.skills_info,
            delay_ms=context.delay_ms,
            cooltime_reduction=resolved_skill_speed,
        )
        timeline_artifacts = _build_timeline_evaluation_artifacts(
            updated_timeline,
            level=context.timeline_artifacts.level,
        )

    # 기준 타임라인 아티팩트 재사용 기반 전투력 재평가
    summary: PowerSummary = evaluate_calculator_power(
        artifacts=timeline_artifacts,
        resolved_stats=resolved_stats,
    )

    return summary


def evaluate_single_stat_delta(
    context: EvaluationContext,
    stat_key: StatKey,
    amount: float,
) -> dict[PowerMetric, float]:
    """단일 스탯 변화량 기준 전투력 차이 계산"""

    # 단일 스탯 변화량 맵 구성
    stat_changes: dict[StatKey, float] = {stat_key: amount}
    target_summary: PowerSummary = evaluate_stat_changes(
        context=context,
        stat_changes=stat_changes,
    )

    return calculate_power_deltas(context.baseline_summary, target_summary)


def evaluate_arbitrary_stat_delta(
    context: EvaluationContext,
    stat_changes: dict[StatKey, float],
) -> dict[PowerMetric, float]:
    """여러 스탯 변화량 기준 전투력 차이 계산"""

    # 다중 스탯 변화량 전투력 계산
    target_summary: PowerSummary = evaluate_stat_changes(
        context=context,
        stat_changes=stat_changes,
    )

    return calculate_power_deltas(context.baseline_summary, target_summary)


def extract_skill_level_effects(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skill_id: str,
) -> list[LevelEffect]:
    """현재 무공비급 레벨 기준 스킬 효과 목록 조회"""

    # 무공비급 레벨과 실제 효과 테이블 연결
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

    # 무공비급 레벨 반영 효과를 데미지/버프별로 미리 분리
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
    context: EvaluationContext,
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
                    StatKey.HP: 5.0,
                    StatKey.STR: float(strength),
                    StatKey.DEXTERITY: float(dexterity),
                    StatKey.VITALITY: float(vitality),
                    StatKey.LUCK: float(luck),
                }
                deltas: dict[PowerMetric, float] = evaluate_arbitrary_stat_delta(
                    context=context,
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
    context: EvaluationContext,
    current_realm: RealmTier,
    level: int,
    target_metric: PowerMetric,
) -> RealmAdvanceEvaluation | None:
    """현재 레벨 기준 다음 경지 상승 효율 계산"""

    # 다음 경지와 요구 레벨 조건 확인
    next_realm: RealmTier | None = _get_next_realm(current_realm)
    if next_realm is None:
        return None

    next_realm_spec: RealmSpec = REALM_TIER_SPECS[next_realm]
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
    base_stats: BaseStats,
) -> list[ScrollUpgradeEvaluation]:
    """각 무공비급 1레벨 상승 시 전투력 차이 계산"""

    # 현재 레벨 기준 기준 전투력 컨텍스트 구성
    baseline_context: EvaluationContext = build_calculator_context(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        base_stats=base_stats,
    )

    # 현재 프리셋 장착 순서 기준 계산 대상 무공비급 목록 구성
    equipped_scroll_ids: list[str] = []
    seen_scroll_ids: set[str] = set()
    scroll_id: str
    for scroll_id in preset.skills.equipped_scrolls:
        # 빈 슬롯과 중복 저장 무공비급 제외
        if not scroll_id or scroll_id in seen_scroll_ids:
            continue

        equipped_scroll_ids.append(scroll_id)
        seen_scroll_ids.add(scroll_id)

    # 무공비급별 1레벨 상승 효과 계산
    evaluations: list[ScrollUpgradeEvaluation] = []
    scroll_def: "ScrollDef"
    for scroll_id in equipped_scroll_ids:
        # 현재 장착 무공비급 정의 조회
        scroll_def = server_spec.skill_registry.get_scroll(scroll_id)
        current_level: int = preset.info.get_scroll_level(scroll_def.id)
        if current_level >= server_spec.max_skill_level:
            continue

        # 현재 프리셋 레벨을 일시적으로 올려 상승 후 전투력 계산
        preset.info.set_scroll_level(scroll_def.id, current_level + 1)
        try:
            upgraded_context: EvaluationContext = build_calculator_context(
                server_spec=server_spec,
                preset=preset,
                skills_info=skills_info,
                delay_ms=delay_ms,
                base_stats=base_stats,
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


def build_base_state(
    base_stats: BaseStats,
    calculator_input: CalculatorPresetInput,
) -> BaseState:
    """현재 선택 기여를 제거한 기준 베이스 스탯 계산"""

    owned_title_map: dict[str, OwnedTitle] = _build_owned_title_map(
        calculator_input.owned_titles
    )
    talisman_stat_map: dict[str, tuple[StatKey, float]] = (
        _build_owned_talisman_stat_map(calculator_input.owned_talismans)
    )

    contribution: Contribution = build_current_selected_contribution(
        calculator_input,
        owned_title_map,
        talisman_stat_map,
    )
    base_without_selection_raw: BaseStats = contribution.apply_to(
        base_stats,
        is_add=False,
    )

    # 현재 선택 제거 후 미세 음수 정규화 블록
    normalized_base_without_selection: dict[StatKey, float] = (
        _normalize_inverse_stat_map(base_without_selection_raw.to_stat_map())
    )
    base_without_selection: BaseStats = BaseStats.from_stat_map(
        normalized_base_without_selection
    )

    return BaseState(
        base_stats=base_without_selection,
        final_stats=base_without_selection.resolve(),
        contribution=contribution,
    )


def validate_base_state(
    base_stats: BaseStats,
    calculator_input: CalculatorPresetInput,
) -> BaseValidation:
    """현재 선택 기여 제거 가능 여부 검증"""

    # 포인트 제한 검증
    distribution_sum: int = (
        calculator_input.distribution.strength
        + calculator_input.distribution.dexterity
        + calculator_input.distribution.vitality
        + calculator_input.distribution.luck
    )
    if distribution_sum > calculator_input.level * 5:
        return BaseValidation(
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
        return BaseValidation(
            is_valid=False,
            message="단전 포인트가 현재 경지 최대치를 초과합니다.",
        )

    base_state: BaseState = build_base_state(base_stats, calculator_input)
    if any(
        value < -INVERSE_NEGATIVE_TOLERANCE
        for value in base_state.base_stats.values.values()
    ):
        return BaseValidation(
            is_valid=False,
            message="현재 선택 기여를 제거하면 음수 베이스 스탯이 발생합니다.",
        )

    return BaseValidation(is_valid=True, message="정상")


def _build_base_stats_from_base_and_contribution(
    base_state: BaseState,
    contribution: Contribution,
) -> BaseStats:
    """기준 베이스와 후보 기여로 최종 베이스 스탯 재구성"""

    return contribution.apply_to(base_state.base_stats)


def _build_distribution_search_root(
    calculator_input: CalculatorPresetInput,
) -> DistributionSearchRange:
    """스탯 분배 탐색 루트 범위 구성"""

    current_state: DistributionState = calculator_input.distribution
    if current_state.is_locked:
        # 잠금 상태 단일 노드 구성 블록
        used_points: int = (
            current_state.strength
            + current_state.dexterity
            + current_state.vitality
            + current_state.luck
        )
        return DistributionSearchRange(
            strength_min=current_state.strength,
            strength_max=current_state.strength,
            dexterity_min=current_state.dexterity,
            dexterity_max=current_state.dexterity,
            vitality_min=current_state.vitality,
            vitality_max=current_state.vitality,
            luck_min=current_state.luck,
            target_points=used_points,
            is_locked=current_state.is_locked,
            use_reset=current_state.use_reset,
        )

    # 리셋 여부 기반 탐색 경계 구성 블록
    max_points: int = calculator_input.level * 5
    strength_min: int = 0 if current_state.use_reset else current_state.strength
    dexterity_min: int = 0 if current_state.use_reset else current_state.dexterity
    vitality_min: int = 0 if current_state.use_reset else current_state.vitality
    luck_min: int = 0 if current_state.use_reset else current_state.luck
    return DistributionSearchRange(
        strength_min=strength_min,
        strength_max=max_points,
        dexterity_min=dexterity_min,
        dexterity_max=max_points,
        vitality_min=vitality_min,
        vitality_max=max_points,
        luck_min=luck_min,
        target_points=max_points,
        is_locked=current_state.is_locked,
        use_reset=current_state.use_reset,
    )


def _is_distribution_search_range_feasible(
    distribution_range: DistributionSearchRange,
) -> bool:
    """스탯 분배 범위 실현 가능 여부 확인"""

    # 최소 포인트 합 검증 블록
    minimum_allocated_points: int = (
        distribution_range.strength_min
        + distribution_range.dexterity_min
        + distribution_range.vitality_min
    )
    return (
        minimum_allocated_points + distribution_range.luck_min
        <= distribution_range.target_points
    )


def _is_leaf_distribution_search_range(
    distribution_range: DistributionSearchRange,
) -> bool:
    """스탯 분배 범위 리프 여부 확인"""

    # 각 축 단일값 여부 확인 블록
    return (
        distribution_range.strength_min == distribution_range.strength_max
        and distribution_range.dexterity_min == distribution_range.dexterity_max
        and distribution_range.vitality_min == distribution_range.vitality_max
    )


def _build_leaf_distribution_state(
    distribution_range: DistributionSearchRange,
) -> DistributionState:
    """리프 범위의 실제 스탯 분배 상태 구성"""

    # 남은 포인트 기반 행운 계산 블록
    luck: int = distribution_range.target_points - (
        distribution_range.strength_min
        + distribution_range.dexterity_min
        + distribution_range.vitality_min
    )
    return DistributionState(
        strength=distribution_range.strength_min,
        dexterity=distribution_range.dexterity_min,
        vitality=distribution_range.vitality_min,
        luck=luck,
        is_locked=distribution_range.is_locked,
        use_reset=distribution_range.use_reset,
    )


def _build_optimistic_distribution_state(
    distribution_range: DistributionSearchRange,
) -> DistributionState:
    """범위 노드 상계 계산용 낙관 스탯 분배 구성"""

    # 각 축 개별 최대치 계산 블록
    max_strength: int = min(
        distribution_range.strength_max,
        distribution_range.target_points
        - distribution_range.luck_min
        - distribution_range.dexterity_min
        - distribution_range.vitality_min,
    )
    max_dexterity: int = min(
        distribution_range.dexterity_max,
        distribution_range.target_points
        - distribution_range.luck_min
        - distribution_range.strength_min
        - distribution_range.vitality_min,
    )
    max_vitality: int = min(
        distribution_range.vitality_max,
        distribution_range.target_points
        - distribution_range.luck_min
        - distribution_range.strength_min
        - distribution_range.dexterity_min,
    )
    max_luck: int = distribution_range.target_points - (
        distribution_range.strength_min
        + distribution_range.dexterity_min
        + distribution_range.vitality_min
    )
    return DistributionState(
        strength=max_strength,
        dexterity=max_dexterity,
        vitality=max_vitality,
        luck=max_luck,
        is_locked=distribution_range.is_locked,
        use_reset=distribution_range.use_reset,
    )


def _split_distribution_search_range(
    distribution_range: DistributionSearchRange,
) -> tuple[DistributionSearchRange, DistributionSearchRange]:
    """최대 폭 축 기준 스탯 분배 범위 분할"""

    # 축별 폭 계산 블록
    strength_span: int = (
        distribution_range.strength_max - distribution_range.strength_min
    )
    dexterity_span: int = (
        distribution_range.dexterity_max - distribution_range.dexterity_min
    )
    vitality_span: int = (
        distribution_range.vitality_max - distribution_range.vitality_min
    )

    # 힘 축 우선 분할 블록
    if strength_span >= dexterity_span and strength_span >= vitality_span:
        midpoint: int = (
            distribution_range.strength_min + distribution_range.strength_max
        ) // 2
        return (
            DistributionSearchRange(
                strength_min=distribution_range.strength_min,
                strength_max=midpoint,
                dexterity_min=distribution_range.dexterity_min,
                dexterity_max=distribution_range.dexterity_max,
                vitality_min=distribution_range.vitality_min,
                vitality_max=distribution_range.vitality_max,
                luck_min=distribution_range.luck_min,
                target_points=distribution_range.target_points,
                is_locked=distribution_range.is_locked,
                use_reset=distribution_range.use_reset,
            ),
            DistributionSearchRange(
                strength_min=midpoint + 1,
                strength_max=distribution_range.strength_max,
                dexterity_min=distribution_range.dexterity_min,
                dexterity_max=distribution_range.dexterity_max,
                vitality_min=distribution_range.vitality_min,
                vitality_max=distribution_range.vitality_max,
                luck_min=distribution_range.luck_min,
                target_points=distribution_range.target_points,
                is_locked=distribution_range.is_locked,
                use_reset=distribution_range.use_reset,
            ),
        )

    # 민첩 축 우선 분할 블록
    if dexterity_span >= vitality_span:
        midpoint: int = (
            distribution_range.dexterity_min + distribution_range.dexterity_max
        ) // 2
        return (
            DistributionSearchRange(
                strength_min=distribution_range.strength_min,
                strength_max=distribution_range.strength_max,
                dexterity_min=distribution_range.dexterity_min,
                dexterity_max=midpoint,
                vitality_min=distribution_range.vitality_min,
                vitality_max=distribution_range.vitality_max,
                luck_min=distribution_range.luck_min,
                target_points=distribution_range.target_points,
                is_locked=distribution_range.is_locked,
                use_reset=distribution_range.use_reset,
            ),
            DistributionSearchRange(
                strength_min=distribution_range.strength_min,
                strength_max=distribution_range.strength_max,
                dexterity_min=midpoint + 1,
                dexterity_max=distribution_range.dexterity_max,
                vitality_min=distribution_range.vitality_min,
                vitality_max=distribution_range.vitality_max,
                luck_min=distribution_range.luck_min,
                target_points=distribution_range.target_points,
                is_locked=distribution_range.is_locked,
                use_reset=distribution_range.use_reset,
            ),
        )

    # 생명력 축 우선 분할 블록
    midpoint: int = (
        distribution_range.vitality_min + distribution_range.vitality_max
    ) // 2
    return (
        DistributionSearchRange(
            strength_min=distribution_range.strength_min,
            strength_max=distribution_range.strength_max,
            dexterity_min=distribution_range.dexterity_min,
            dexterity_max=distribution_range.dexterity_max,
            vitality_min=distribution_range.vitality_min,
            vitality_max=midpoint,
            luck_min=distribution_range.luck_min,
            target_points=distribution_range.target_points,
            is_locked=distribution_range.is_locked,
            use_reset=distribution_range.use_reset,
        ),
        DistributionSearchRange(
            strength_min=distribution_range.strength_min,
            strength_max=distribution_range.strength_max,
            dexterity_min=distribution_range.dexterity_min,
            dexterity_max=distribution_range.dexterity_max,
            vitality_min=midpoint + 1,
            vitality_max=distribution_range.vitality_max,
            luck_min=distribution_range.luck_min,
            target_points=distribution_range.target_points,
            is_locked=distribution_range.is_locked,
            use_reset=distribution_range.use_reset,
        ),
    )


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

    title_names: list[str | None] = []
    for owned_title in calculator_input.owned_titles:
        title_names.append(owned_title.name)

    return title_names


def _build_talisman_candidates(
    calculator_input: CalculatorPresetInput,
) -> list[list[str]]:
    """부적 조합 후보 목록 생성"""

    owned_talismans: list[OwnedTalisman] = calculator_input.owned_talismans
    if not owned_talismans:
        return [[]]

    # 동일 이름 제거 기반 후보 이름 구성 블록
    seen_names: set[str] = set()
    owned_names: list[str] = []
    owned_talisman: OwnedTalisman
    for owned_talisman in owned_talismans:
        if owned_talisman.name in seen_names:
            continue

        seen_names.add(owned_talisman.name)
        owned_names.append(owned_talisman.name)

    target_size: int = 3

    candidates: list[list[str]] = []

    def build_combinations(start_index: int, selected_names: list[str]) -> None:
        """현재 보유 부적 조합 구성"""

        if len(selected_names) == target_size:
            candidates.append(selected_names.copy())
            return

        for current_index in range(start_index, len(owned_names)):
            owned_name: str = owned_names[current_index]
            if owned_name in selected_names:
                continue

            selected_names.append(owned_name)
            build_combinations(current_index + 1, selected_names)
            selected_names.pop()

    build_combinations(0, [])
    if not candidates:
        return [[]]

    return candidates


def _build_contribution_signature(
    contribution: Contribution,
) -> tuple[tuple[str, float], ...]:
    """기여 정규화 시그니처 구성"""

    # 0이 아닌 기여만 고정 순서로 직렬화 블록
    ordered_items: list[tuple[str, float]] = sorted(
        (
            stat_key.value,
            float(value),
        )
        for stat_key, value in contribution.values.items()
        if value != 0.0
    )
    return tuple(ordered_items)


def _contribution_dominates(
    left_contribution: Contribution,
    right_contribution: Contribution,
) -> bool:
    """좌측 기여의 우월 관계 확인"""

    # 비교 대상 스탯 키 집합 구성 블록
    target_stat_keys: set[StatKey] = set(left_contribution.values.keys()) | set(
        right_contribution.values.keys()
    )
    has_strict_advantage: bool = False
    stat_key: StatKey
    for stat_key in target_stat_keys:
        left_value: float = float(left_contribution.values.get(stat_key, 0.0))
        right_value: float = float(right_contribution.values.get(stat_key, 0.0))
        if left_value < right_value:
            return False

        if left_value > right_value:
            has_strict_advantage = True

    return has_strict_advantage


def _prune_contribution_entries(
    entries: list[tuple[EntryPayload, Contribution]],
) -> list[tuple[EntryPayload, Contribution]]:
    """중복 및 지배 후보 제거"""

    # 완전 동일 기여 제거 블록
    signature_to_entry: dict[
        tuple[tuple[str, float], ...], tuple[EntryPayload, Contribution]
    ] = {}
    payload: EntryPayload
    contribution: Contribution
    for payload, contribution in entries:
        signature: tuple[tuple[str, float], ...] = _build_contribution_signature(
            contribution
        )
        if signature in signature_to_entry:
            continue

        signature_to_entry[signature] = (payload, contribution)

    # 지배 후보 제거 블록
    unique_entries: list[tuple[EntryPayload, Contribution]] = list(
        signature_to_entry.values()
    )
    pruned_entries: list[tuple[EntryPayload, Contribution]] = []
    target_index: int
    for target_index, (payload, contribution) in enumerate(unique_entries):
        is_dominated: bool = False
        compare_index: int
        other_payload: EntryPayload
        other_contribution: Contribution
        for compare_index, (other_payload, other_contribution) in enumerate(
            unique_entries
        ):
            if compare_index == target_index:
                continue

            if not _contribution_dominates(other_contribution, contribution):
                continue

            is_dominated = True
            break

        if is_dominated:
            continue

        pruned_entries.append((payload, contribution))

    return pruned_entries


def _build_distribution_cache_key(
    distribution_state: DistributionState,
) -> tuple[int, int, int, int]:
    """스탯 분배 평가 캐시 키 구성"""

    # 4종 분배값 튜플화 블록
    return (
        distribution_state.strength,
        distribution_state.dexterity,
        distribution_state.vitality,
        distribution_state.luck,
    )


def _evaluate_distribution_selection(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    context: EvaluationContext,
    base_state: BaseState,
    distribution_state: DistributionState,
    danjeon_entries: list[tuple[DanjeonState, Contribution]],
    title_entries: list[tuple[str | None, Contribution]],
    talisman_entries: list[tuple[tuple[str, ...], Contribution]],
    timeline_cache: dict[float, TimelineEvaluationArtifacts],
    target_metric: PowerMetric,
) -> OptimizationResult | None:
    """고정 스탯 분배 기준 내부 선택지 최적화"""

    # 분배 기여 사전 계산 블록
    distribution_contribution: Contribution = build_distribution_contribution(
        distribution_state
    )

    # 기준 베이스의 str 키 → 값 맵을 사전 캐시하여 반복 변환 제거
    base_raw_values: dict[str, float] = base_state.base_stats.values

    # 분배 기여만 적용한 기준 스탯 구성 (기울기 계산용)
    dist_base_stats: dict[StatKey, float] = {}
    for _idx, _sk in enumerate(_STAT_ORDER_KEYS):
        _base_val: float = base_raw_values.get(_STAT_ORDER_VALUES[_idx], 0.0)
        dist_base_stats[_sk] = _base_val + distribution_contribution.values.get(
            _sk, 0.0
        )

    # 기준 타임라인 조회 (기울기 계산용)
    dist_resolved: FinalStats = _fast_resolve(dist_base_stats)
    dist_skill_speed: float = float(dist_resolved.values[_FK_SKILL_SPEED_PERCENT])
    dist_speed_key: float = round(dist_skill_speed, 2)
    dist_timeline: TimelineEvaluationArtifacts | None = timeline_cache.get(
        dist_speed_key
    )
    if dist_timeline is None:
        dist_timeline = _build_timeline_evaluation_artifacts(
            build_calculator_timeline(
                server_spec=server_spec,
                preset=preset,
                skills_info=skills_info,
                delay_ms=delay_ms,
                cooltime_reduction=dist_skill_speed,
            ),
            level=preset.info.calculator.level,
        )
        timeline_cache[dist_speed_key] = dist_timeline

    # 조합 수 기반 기울기 필터링 적용 여부 결정
    total_combos: int = (
        len(danjeon_entries) * len(title_entries) * len(talisman_entries)
    )
    if total_combos > _GRADIENT_EXACT_THRESHOLD:
        # 기여에 사용되는 스탯 키 수집
        relevant_stats: set[StatKey] = set()
        for _, _contrib in danjeon_entries:
            relevant_stats.update(k for k, v in _contrib.values.items() if v != 0.0)
        for _, _contrib in title_entries:
            relevant_stats.update(k for k, v in _contrib.values.items() if v != 0.0)
        for _, _contrib in talisman_entries:
            relevant_stats.update(k for k, v in _contrib.values.items() if v != 0.0)

        # 기준점 기울기 계산
        gradient: dict[StatKey, float] = _compute_power_gradient(
            dist_timeline,
            dist_base_stats,
            target_metric,
            frozenset(relevant_stats),
        )

        # 각 차원 독립 점수 매기기 → 상위 K개 필터링
        effective_danjeon: list[tuple[DanjeonState, Contribution]] = sorted(
            danjeon_entries,
            key=lambda e: _score_contribution_by_gradient(gradient, e[1]),
            reverse=True,
        )[:_GRADIENT_TOP_K]
        effective_title: list[tuple[str | None, Contribution]] = sorted(
            title_entries,
            key=lambda e: _score_contribution_by_gradient(gradient, e[1]),
            reverse=True,
        )[:_GRADIENT_TOP_K]
        effective_talisman: list[tuple[tuple[str, ...], Contribution]] = sorted(
            talisman_entries,
            key=lambda e: _score_contribution_by_gradient(gradient, e[1]),
            reverse=True,
        )[:_GRADIENT_TOP_K]
    else:
        effective_danjeon = danjeon_entries
        effective_title = title_entries
        effective_talisman = talisman_entries

    # 필터링된 후보에 대한 정확 평가 루프
    best_result: OptimizationResult | None = None
    best_metric_delta: float | None = None
    danjeon_state: DanjeonState
    danjeon_contribution: Contribution
    for danjeon_state, danjeon_contribution in effective_danjeon:
        equipped_title_name: str | None
        title_contribution: Contribution
        for equipped_title_name, title_contribution in effective_title:
            equipped_talisman_names: tuple[str, ...]
            talisman_contribution: Contribution
            for equipped_talisman_names, talisman_contribution in effective_talisman:
                # 선택지 기여 병합 블록 (인라인)
                merged_values: dict[StatKey, float] = (
                    distribution_contribution.values.copy()
                )
                for _contrib in (
                    danjeon_contribution,
                    title_contribution,
                    talisman_contribution,
                ):
                    for _sk, _v in _contrib.values.items():
                        merged_values[_sk] = merged_values.get(_sk, 0.0) + _v

                # 기여 적용 + resolve 통합
                changed_stats: dict[StatKey, float] = {}
                for _idx, _sk in enumerate(_STAT_ORDER_KEYS):
                    _base_val = base_raw_values.get(_STAT_ORDER_VALUES[_idx], 0.0)
                    changed_stats[_sk] = _base_val + merged_values.get(_sk, 0.0)

                optimized_resolved_stats: FinalStats = _fast_resolve(changed_stats)

                candidate_skill_speed: float = float(
                    optimized_resolved_stats.values[_FK_SKILL_SPEED_PERCENT]
                )
                speed_cache_key: float = round(candidate_skill_speed, 2)
                cached_timeline_artifacts: TimelineEvaluationArtifacts | None = (
                    timeline_cache.get(speed_cache_key)
                )
                if cached_timeline_artifacts is None:
                    cached_timeline: Timeline = build_calculator_timeline(
                        server_spec=server_spec,
                        preset=preset,
                        skills_info=skills_info,
                        delay_ms=delay_ms,
                        cooltime_reduction=candidate_skill_speed,
                    )
                    cached_timeline_artifacts = _build_timeline_evaluation_artifacts(
                        cached_timeline,
                        level=preset.info.calculator.level,
                    )
                    timeline_cache[speed_cache_key] = cached_timeline_artifacts

                optimized_summary: PowerSummary = evaluate_calculator_power(
                    artifacts=cached_timeline_artifacts,
                    resolved_stats=optimized_resolved_stats,
                )
                deltas: dict[PowerMetric, float] = calculate_power_deltas(
                    context.baseline_summary,
                    optimized_summary,
                )
                metric_delta: float = deltas[target_metric]
                if best_metric_delta is not None and metric_delta <= best_metric_delta:
                    continue

                best_metric_delta = metric_delta
                optimized_base_stats: BaseStats = BaseStats.from_stat_map(changed_stats)
                best_result = OptimizationResult(
                    candidate=OptimizationCandidate(
                        distribution=distribution_state,
                        danjeon=danjeon_state,
                        equipped_title_name=equipped_title_name,
                        equipped_talisman_names=equipped_talisman_names,
                    ),
                    deltas=deltas,
                    base_stats=optimized_base_stats,
                )

    return best_result


def _search_subtree(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    context: EvaluationContext,
    base_state: BaseState,
    danjeon_entries: list[tuple[DanjeonState, Contribution]],
    title_entries: list[tuple[str | None, Contribution]],
    talisman_entries: list[tuple[tuple[str, ...], Contribution]],
    target_metric: PowerMetric,
    sub_range: DistributionSearchRange,
    baseline_timeline_entry: tuple[float, TimelineEvaluationArtifacts],
) -> OptimizationResult | None:
    """단일 서브트리에 대한 Branch-and-Bound 탐색 (프로세스 워커 호환)"""

    timeline_cache: dict[float, TimelineEvaluationArtifacts] = {
        baseline_timeline_entry[0]: baseline_timeline_entry[1]
    }
    distribution_result_cache: dict[tuple[int, int, int, int], OptimizationResult] = {}

    # 서브트리 루트 상계 계산
    root_distribution_state: DistributionState = _build_optimistic_distribution_state(
        sub_range
    )
    root_cache_key: tuple[int, int, int, int] = _build_distribution_cache_key(
        root_distribution_state
    )
    root_result: OptimizationResult | None = _evaluate_distribution_selection(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        context=context,
        base_state=base_state,
        distribution_state=root_distribution_state,
        danjeon_entries=danjeon_entries,
        title_entries=title_entries,
        talisman_entries=talisman_entries,
        timeline_cache=timeline_cache,
        target_metric=target_metric,
    )
    if root_result is None:
        return None

    distribution_result_cache[root_cache_key] = root_result

    # 상계 우선 탐색 큐 초기화
    search_queue: list[tuple[float, int, DistributionSearchRange]] = []
    root_upper_bound: float = root_result.deltas[target_metric]
    heapq.heappush(search_queue, (-root_upper_bound, 0, sub_range))

    best_result: OptimizationResult | None = None
    best_metric_delta: float | None = None
    node_sequence: int = 1

    while search_queue:
        priority_item: tuple[float, int, DistributionSearchRange] = heapq.heappop(
            search_queue
        )
        node_upper_bound: float = -priority_item[0]
        distribution_range: DistributionSearchRange = priority_item[2]
        if best_metric_delta is not None and node_upper_bound <= best_metric_delta:
            continue

        if _is_leaf_distribution_search_range(distribution_range):
            leaf_distribution_state: DistributionState = _build_leaf_distribution_state(
                distribution_range
            )
            leaf_cache_key: tuple[int, int, int, int] = _build_distribution_cache_key(
                leaf_distribution_state
            )
            leaf_result: OptimizationResult | None = distribution_result_cache.get(
                leaf_cache_key
            )
            if leaf_result is None:
                leaf_result = _evaluate_distribution_selection(
                    server_spec=server_spec,
                    preset=preset,
                    skills_info=skills_info,
                    delay_ms=delay_ms,
                    context=context,
                    base_state=base_state,
                    distribution_state=leaf_distribution_state,
                    danjeon_entries=danjeon_entries,
                    title_entries=title_entries,
                    talisman_entries=talisman_entries,
                    timeline_cache=timeline_cache,
                    target_metric=target_metric,
                )
                if leaf_result is None:
                    continue
                distribution_result_cache[leaf_cache_key] = leaf_result

            leaf_metric_delta: float = leaf_result.deltas[target_metric]
            if best_metric_delta is not None and leaf_metric_delta <= best_metric_delta:
                continue

            best_metric_delta = leaf_metric_delta
            best_result = leaf_result
            continue

        child_ranges: tuple[DistributionSearchRange, DistributionSearchRange] = (
            _split_distribution_search_range(distribution_range)
        )
        child_range: DistributionSearchRange
        for child_range in child_ranges:
            if not _is_distribution_search_range_feasible(child_range):
                continue

            optimistic_distribution_state: DistributionState = (
                _build_optimistic_distribution_state(child_range)
            )
            optimistic_cache_key: tuple[int, int, int, int] = (
                _build_distribution_cache_key(optimistic_distribution_state)
            )
            optimistic_result: OptimizationResult | None = (
                distribution_result_cache.get(optimistic_cache_key)
            )
            if optimistic_result is None:
                optimistic_result = _evaluate_distribution_selection(
                    server_spec=server_spec,
                    preset=preset,
                    skills_info=skills_info,
                    delay_ms=delay_ms,
                    context=context,
                    base_state=base_state,
                    distribution_state=optimistic_distribution_state,
                    danjeon_entries=danjeon_entries,
                    title_entries=title_entries,
                    talisman_entries=talisman_entries,
                    timeline_cache=timeline_cache,
                    target_metric=target_metric,
                )
                if optimistic_result is None:
                    continue
                distribution_result_cache[optimistic_cache_key] = optimistic_result

            child_upper_bound: float = optimistic_result.deltas[target_metric]
            if best_metric_delta is not None and child_upper_bound <= best_metric_delta:
                continue

            heapq.heappush(
                search_queue,
                (-child_upper_bound, node_sequence, child_range),
            )
            node_sequence += 1

    return best_result


def _generate_sub_ranges(
    root_range: DistributionSearchRange,
    target_count: int,
) -> list[DistributionSearchRange]:
    """탐색 루트를 target_count 개 이상의 서브 범위로 분할"""

    ranges: list[DistributionSearchRange] = [root_range]
    while len(ranges) < target_count:
        # 가장 넓은 축 폭을 가진 범위를 선택하여 분할
        best_idx: int = 0
        best_span: int = 0
        for idx, search_range in enumerate(ranges):
            span: int = max(
                search_range.strength_max - search_range.strength_min,
                search_range.dexterity_max - search_range.dexterity_min,
                search_range.vitality_max - search_range.vitality_min,
            )
            if span > best_span:
                best_span = span
                best_idx = idx

        if best_span == 0:
            break

        target_range: DistributionSearchRange = ranges.pop(best_idx)
        child_a: DistributionSearchRange
        child_b: DistributionSearchRange
        child_a, child_b = _split_distribution_search_range(target_range)
        if _is_distribution_search_range_feasible(child_a):
            ranges.append(child_a)
        if _is_distribution_search_range_feasible(child_b):
            ranges.append(child_b)

    return ranges


def optimize_current_selection(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    context: EvaluationContext,
    base_stats: BaseStats,
    calculator_input: CalculatorPresetInput,
    target_metric: PowerMetric,
    progress_callback: Callable[[str, int], None] | None = None,
    cancel_checker: Callable[[], None] | None = None,
) -> OptimizationResult | None:
    """현재 선택 조합 최적화"""

    # 최적화 진입 직전 취소와 진행 상태 확인 블록
    if cancel_checker is not None:
        cancel_checker()

    if progress_callback is not None:
        progress_callback("최적화 후보 준비 중...", 0)

    # 기준 베이스 분리 검증 실패 시 최적화 중단
    validation: BaseValidation = validate_base_state(
        base_stats=base_stats,
        calculator_input=calculator_input,
    )
    if not validation.is_valid:
        return None

    base_state: BaseState = build_base_state(
        base_stats=base_stats,
        calculator_input=calculator_input,
    )

    # 스탯 분배 탐색 루트 구성 블록
    distribution_root: DistributionSearchRange = _build_distribution_search_root(
        calculator_input
    )
    if not _is_distribution_search_range_feasible(distribution_root):
        return None

    # 각 내부 선택지 후보 목록 구성 블록
    danjeon_candidates: list[DanjeonState] = _build_danjeon_candidates(calculator_input)
    title_candidates: list[str | None] = _build_title_candidates(calculator_input)
    talisman_candidates: list[list[str]] = _build_talisman_candidates(calculator_input)

    # 보유 칭호/부적 사전 계산 블록
    owned_title_map: dict[str, OwnedTitle] = _build_owned_title_map(
        calculator_input.owned_titles
    )
    talisman_stat_map: dict[str, tuple[StatKey, float]] = (
        _build_owned_talisman_stat_map(calculator_input.owned_talismans)
    )

    # 내부 선택지 기여 사전 계산 및 정리 블록
    danjeon_entries: list[tuple[DanjeonState, Contribution]] = (
        _prune_contribution_entries(
            [
                (danjeon_state, build_danjeon_contribution(danjeon_state))
                for danjeon_state in danjeon_candidates
            ]
        )
    )
    title_entries: list[tuple[str | None, Contribution]] = _prune_contribution_entries(
        [
            (
                equipped_title_name,
                build_title_contribution(equipped_title_name, owned_title_map),
            )
            for equipped_title_name in title_candidates
        ]
    )
    talisman_entries: list[tuple[tuple[str, ...], Contribution]] = (
        _prune_contribution_entries(
            [
                (
                    tuple(equipped_talisman_names),
                    build_talisman_contribution(
                        equipped_talisman_names,
                        talisman_stat_map,
                    ),
                )
                for equipped_talisman_names in talisman_candidates
            ]
        )
    )

    # 스킬속도 기준 타임라인 캐시 시드
    baseline_speed_cache_key: float = round(
        context.baseline_final_stats.values[StatKey.SKILL_SPEED_PERCENT], 2
    )
    baseline_timeline_entry: tuple[float, TimelineEvaluationArtifacts] = (
        baseline_speed_cache_key,
        context.timeline_artifacts,
    )

    # 탐색 공간 분할 및 병렬 실행
    worker_count: int = os.cpu_count() or 4
    sub_ranges: list[DistributionSearchRange] = _generate_sub_ranges(
        distribution_root, worker_count * 2
    )

    shared_args: tuple[object, ...] = (
        server_spec,
        preset,
        skills_info,
        delay_ms,
        context,
        base_state,
        danjeon_entries,
        title_entries,
        talisman_entries,
        target_metric,
    )

    # 서브 범위가 적으면 직렬 실행, 충분하면 병렬 실행
    best_result: OptimizationResult | None = None
    best_metric_delta: float | None = None
    total_sub_ranges: int = max(1, len(sub_ranges))
    completed_sub_ranges: int = 0

    # 서브 범위 준비 완료 진행 상태 반영 블록
    if progress_callback is not None:
        progress_callback("최적화 계산 중...", 5)

    if len(sub_ranges) <= 2:
        # 탐색 공간이 작으면 직렬 실행
        for sub_range in sub_ranges:
            if cancel_checker is not None:
                cancel_checker()

            result: OptimizationResult | None = _search_subtree(
                *shared_args,
                sub_range=sub_range,
                baseline_timeline_entry=baseline_timeline_entry,
            )
            completed_sub_ranges += 1

            if result is not None:
                delta: float = result.deltas[target_metric]
                if best_metric_delta is None or delta > best_metric_delta:
                    best_metric_delta = delta
                    best_result = result

            # 직렬 탐색 진행률 반영 블록
            if progress_callback is not None:
                progress_value: int = 5 + int(
                    (completed_sub_ranges / total_sub_ranges) * 90
                )
                progress_callback("최적화 계산 중...", progress_value)
    else:
        # 병렬 탐색 중 취소 응답성 확보 블록
        pool: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=worker_count)
        pending_futures: set[Future[OptimizationResult | None]] = set()
        should_wait_for_pool: bool = True

        try:
            pending_futures = {
                pool.submit(
                    _search_subtree,
                    *shared_args,
                    sub_range=sub_range,
                    baseline_timeline_entry=baseline_timeline_entry,
                )
                for sub_range in sub_ranges
            }
            while pending_futures:
                if cancel_checker is not None:
                    cancel_checker()

                done_futures: set[Future[OptimizationResult | None]]
                done_futures, pending_futures = wait(
                    pending_futures,
                    timeout=0.1,
                    return_when=FIRST_COMPLETED,
                )
                if not done_futures:
                    continue

                future: Future[OptimizationResult | None]
                for future in done_futures:
                    result: OptimizationResult | None = future.result()
                    completed_sub_ranges += 1
                    if result is not None:
                        delta: float = result.deltas[target_metric]
                        if best_metric_delta is None or delta > best_metric_delta:
                            best_metric_delta = delta
                            best_result = result

                    # 병렬 탐색 진행률 반영 블록
                    if progress_callback is not None:
                        progress_value: int = 5 + int(
                            (completed_sub_ranges / total_sub_ranges) * 90
                        )
                        progress_callback("최적화 계산 중...", progress_value)
        except Exception:
            should_wait_for_pool = False
            raise
        finally:
            pool.shutdown(
                wait=should_wait_for_pool,
                cancel_futures=not should_wait_for_pool,
            )

    return best_result
