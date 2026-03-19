from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.scripts.calculator_models import (
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
    is_skill: bool


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
class CalculatorEvaluationContext:
    """평가 기준이 되는 초기 상태 컨텍스트"""

    timeline_artifacts: TimelineEvaluationArtifacts
    baseline_base_stats: BaseStats
    baseline_final_stats: FinalStats
    baseline_summary: PowerSummary


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
    """스크롤 레벨 상승 효율 계산 결과"""

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
class CalculatorBaseState:
    """기준 베이스 스탯 분리 결과"""

    base_stats: BaseStats
    final_stats: FinalStats
    contribution: Contribution


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
    base_stats: BaseStats


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
    equipped_title_id: str | None,
    owned_title_map: dict[str, OwnedTitle],
) -> Contribution:
    """현재 장착 칭호 기여 계산"""

    if equipped_title_id is None:
        return Contribution()

    # 사전 계산된 칭호 조회 맵 기반 즉시 조회
    equipped_title: OwnedTitle = owned_title_map[equipped_title_id]

    contribution: Contribution = Contribution()
    for stat_key_text, value in equipped_title.stats.items():
        contribution = contribution.add(StatKey(stat_key_text), value)
    return contribution


def _find_talisman_template(
    owned_talisman: OwnedTalisman,
) -> tuple[StatKey, int] | None:
    """보유 부적의 스탯 대상과 등급 보정값 조회"""

    for spec in TALISMAN_SPECS:
        if spec.name != owned_talisman.name:
            continue

        return spec.stat_key, spec.level_stats

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
        stat_key, grade_offset = talisman_spec
        stat_value: float = float((grade_offset * 10) + owned_talisman.level)
        talisman_stat_map[owned_talisman.owned_id] = (stat_key, stat_value)

    return talisman_stat_map


def build_talisman_contribution(
    equipped_talisman_ids: list[str],
    talisman_stat_map: dict[str, tuple[StatKey, float]],
) -> Contribution:
    """현재 장착 부적 기여 계산"""

    contribution: Contribution = Contribution()
    for equipped_id in equipped_talisman_ids:
        stat_key: StatKey
        stat_value: float
        stat_key, stat_value = talisman_stat_map[equipped_id]
        contribution = contribution.add(stat_key, stat_value)

    return contribution


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
        calculator_input.equipped_state.equipped_title_id,
        owned_title_map,
    )
    talisman_contribution: Contribution = build_talisman_contribution(
        calculator_input.equipped_state.equipped_talisman_ids,
        talisman_stat_map,
    )
    return distribution_contribution.merge(
        danjeon_contribution,
        title_contribution,
        talisman_contribution,
    )


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
    basic_attack_interval_ms: int = int((100 - cooltime_reduction) * 10)
    hit_events: list[HitEvent] = []
    for current_time_ms in range(
        0,
        TIMELINE_MILLISECONDS,
        basic_attack_interval_ms,
    ):
        hit_events.append(
            HitEvent(
                skill_id=basic_attack_skill_id,
                time=round(current_time_ms * 0.001, 2),
                multiplier=1.0,
                is_skill=False,
            )
        )

    skill_uses: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
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
                    is_skill=True,
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
    hit_event: HitEvent
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

    # 타격별 활성 버프 스냅샷 재사용 기반 총데미지 누적
    total_boss_damage: float = 0.0
    total_normal_damage: float = 0.0

    hit_event: HitEvent
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

    # 세그먼트별 비타격 전투력 배수 시간가중 평균 누적
    weighted_boss_multiplier_sum: float = 0.0
    weighted_normal_multiplier_sum: float = 0.0
    timeline_segment: TimelineSegment
    for timeline_segment in artifacts.timeline_segments:
        segment_stats: dict[StatKey, float] = _apply_active_buffs(
            resolved_stats,
            timeline_segment.active_buffs,
        )

        # 보스 전투력용 생존 배수 계산
        hp_value: float = float(segment_stats[StatKey.HP])
        dodge_value: float = float(segment_stats[StatKey.DODGE_PERCENT])
        resist_value: float = float(segment_stats[StatKey.RESIST_PERCENT])
        potion_heal_value: float = float(segment_stats[StatKey.POTION_HEAL_PERCENT])
        dodge_denominator: float = max(1.0 - (dodge_value * 0.01), 0.01)

        boss_multiplier: float = hp_value
        boss_multiplier *= 1.0 / dodge_denominator
        boss_multiplier *= 1.0 + (resist_value * 0.01)
        boss_multiplier *= 1.0 + (potion_heal_value * 0.01)
        weighted_boss_multiplier_sum += boss_multiplier * timeline_segment.duration

        # 일반 전투력용 획득 배수 계산
        drop_rate_value: float = float(segment_stats[StatKey.DROP_RATE_PERCENT])
        exp_value: float = float(segment_stats[StatKey.EXP_PERCENT])

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
) -> CalculatorEvaluationContext:
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
        _build_timeline_evaluation_artifacts(timeline)
    )

    # 기준 타임라인 아티팩트와 기준 스탯으로 기준 전투력 계산
    baseline_summary: PowerSummary = evaluate_calculator_power(
        artifacts=timeline_artifacts,
        resolved_stats=baseline_final_stats,
    )

    return CalculatorEvaluationContext(
        timeline_artifacts=timeline_artifacts,
        baseline_base_stats=base_stats,
        baseline_final_stats=baseline_final_stats,
        baseline_summary=baseline_summary,
    )


def evaluate_stat_changes(
    context: CalculatorEvaluationContext,
    base_stats: BaseStats,
    stat_changes: dict[StatKey, float],
) -> PowerSummary:
    """베이스 스탯 변화량 반영 후 전투력 계산"""

    resolved_stats: FinalStats = base_stats.resolve(stat_changes)

    # 기준 타임라인 아티팩트 재사용 기반 전투력 재평가
    summary: PowerSummary = evaluate_calculator_power(
        artifacts=context.timeline_artifacts,
        resolved_stats=resolved_stats,
    )

    return summary


def evaluate_single_stat_delta(
    context: CalculatorEvaluationContext,
    base_stats: BaseStats,
    stat_key: StatKey,
    amount: float,
) -> dict[PowerMetric, float]:
    """단일 스탯 변화량 기준 전투력 차이 계산"""

    # 단일 스탯 변화량 맵 구성
    stat_changes: dict[StatKey, float] = {stat_key: amount}
    target_summary: PowerSummary = evaluate_stat_changes(
        context=context,
        base_stats=base_stats,
        stat_changes=stat_changes,
    )

    return calculate_power_deltas(context.baseline_summary, target_summary)


def evaluate_arbitrary_stat_delta(
    context: CalculatorEvaluationContext,
    base_stats: BaseStats,
    stat_changes: dict[StatKey, float],
) -> dict[PowerMetric, float]:
    """여러 스탯 변화량 기준 전투력 차이 계산"""

    # 다중 스탯 변화량 전투력 계산
    target_summary: PowerSummary = evaluate_stat_changes(
        context=context,
        base_stats=base_stats,
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
    base_stats: BaseStats,
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
                    base_stats=base_stats,
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
    base_stats: BaseStats,
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
                base_stats=base_stats,
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
    """각 스크롤 1레벨 상승 시 전투력 차이 계산"""

    # 현재 레벨 기준 기준 전투력 컨텍스트 구성
    baseline_context: CalculatorEvaluationContext = build_calculator_context(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        base_stats=base_stats,
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
) -> CalculatorBaseState:
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
    base_without_selection: BaseStats = contribution.apply_to(base_stats, is_add=False)

    return CalculatorBaseState(
        base_stats=base_without_selection,
        final_stats=base_without_selection.resolve(),
        contribution=contribution,
    )


def validate_base_state(
    base_stats: BaseStats,
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

    base_state: CalculatorBaseState = build_base_state(base_stats, calculator_input)
    if any(value < 0.0 for value in base_state.base_stats.values.values()):
        return CalculatorBaseValidation(
            is_valid=False,
            message="현재 선택 기여를 제거하면 음수 베이스 스탯이 발생합니다.",
        )

    return CalculatorBaseValidation(is_valid=True, message="정상")


def _build_base_stats_from_base_and_contribution(
    base_state: CalculatorBaseState,
    contribution: Contribution,
) -> BaseStats:
    """기준 베이스와 후보 기여로 최종 베이스 스탯 재구성"""

    return contribution.apply_to(base_state.base_stats)


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
        title_ids.append(owned_title.name)

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
    base_stats: BaseStats,
    calculator_input: CalculatorPresetInput,
    target_metric: PowerMetric,
) -> OptimizationResult | None:
    """현재 선택 조합 최적화"""

    # 기준 베이스 분리 검증 실패 시 최적화 중단
    validation: CalculatorBaseValidation = validate_base_state(
        base_stats=base_stats,
        calculator_input=calculator_input,
    )
    if not validation.is_valid:
        return None

    base_state: CalculatorBaseState = build_base_state(
        base_stats=base_stats,
        calculator_input=calculator_input,
    )

    # 각 선택지 후보 목록 구성
    distribution_candidates: list[DistributionState] = _build_distribution_candidates(
        calculator_input
    )
    danjeon_candidates: list[DanjeonState] = _build_danjeon_candidates(calculator_input)
    title_candidates: list[str | None] = _build_title_candidates(calculator_input)
    talisman_candidates: list[list[str]] = _build_talisman_candidates(calculator_input)

    # 보유 칭호/부적 사전 계산
    owned_title_map: dict[str, OwnedTitle] = _build_owned_title_map(
        calculator_input.owned_titles
    )
    talisman_stat_map: dict[str, tuple[StatKey, float]] = (
        _build_owned_talisman_stat_map(calculator_input.owned_talismans)
    )

    # 합산 스탯 사전 계산
    distribution_entries: list[tuple[DistributionState, Contribution]] = [
        (distribution_state, build_distribution_contribution(distribution_state))
        for distribution_state in distribution_candidates
    ]
    danjeon_entries: list[tuple[DanjeonState, Contribution]] = [
        (danjeon_state, build_danjeon_contribution(danjeon_state))
        for danjeon_state in danjeon_candidates
    ]
    title_entries: list[tuple[str | None, Contribution]] = [
        (
            equipped_title_id,
            build_title_contribution(equipped_title_id, owned_title_map),
        )
        for equipped_title_id in title_candidates
    ]
    talisman_entries: list[tuple[list[str], Contribution]] = [
        (
            equipped_talisman_ids,
            build_talisman_contribution(equipped_talisman_ids, talisman_stat_map),
        )
        for equipped_talisman_ids in talisman_candidates
    ]

    # 스킬속도 기준 타임라인 캐시 구성
    baseline_speed_cache_key: float = round(
        context.baseline_final_stats.values[StatKey.SKILL_SPEED_PERCENT], 2
    )
    timeline_cache: dict[float, TimelineEvaluationArtifacts] = {
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
                    candidate_contribution: Contribution = (
                        distribution_contribution.merge(
                            danjeon_contribution,
                            title_contribution,
                            talisman_contribution,
                        )
                    )
                    optimized_base_stats: BaseStats = (
                        _build_base_stats_from_base_and_contribution(
                            base_state,
                            candidate_contribution,
                        )
                    )

                    # 후보 최종 스탯 및 스킬속도 기준 타임라인 캐시 키 정규화
                    optimized_resolved_stats: FinalStats = (
                        optimized_base_stats.resolve()
                    )
                    candidate_skill_speed: float = float(
                        optimized_resolved_stats.values[StatKey.SKILL_SPEED_PERCENT]
                    )
                    speed_cache_key: float = round(candidate_skill_speed, 2)

                    # 동일 스킬속도 구간 타임라인 재활용 및 최초 1회만 재계산
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
                        cached_timeline_artifacts = (
                            _build_timeline_evaluation_artifacts(cached_timeline)
                        )
                        timeline_cache[speed_cache_key] = cached_timeline_artifacts

                    # 캐시된 타임라인 활성 버프 스냅샷과 후보 스탯 기준 전투력 재평가
                    optimized_summary: PowerSummary = evaluate_calculator_power(
                        artifacts=cached_timeline_artifacts,
                        resolved_stats=optimized_resolved_stats,
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
                        base_stats=optimized_base_stats,
                    )

    return best_result
