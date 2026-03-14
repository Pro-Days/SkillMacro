from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.scripts.calculator_models import PowerMetric, StatKey
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
    base_crit_rate_source: float
    base_crit_damage_source: float
    base_drop_rate_source: float
    base_exp_source: float
    base_dodge_source: float
    base_potion_heal_source: float


@dataclass(frozen=True, slots=True)
class CalculatorPowerSummary:
    """계산기 전투력 요약"""

    metrics: dict[PowerMetric, float]


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
    resolved_values[StatKey.ATTACK_PERCENT] = float(
        changed_stats[StatKey.ATTACK_PERCENT]
    ) + (final_dexterity * 0.3)
    resolved_values[StatKey.SKILL_SPEED_PERCENT] = float(
        changed_stats[StatKey.SKILL_SPEED_PERCENT]
    )

    return CalculatorResolvedStats(
        values=resolved_values,
        base_attack_source=base_attack_source,
        base_hp_source=base_hp_source,
        base_crit_rate_source=base_crit_rate_source,
        base_crit_damage_source=base_crit_damage_source,
        base_drop_rate_source=base_drop_rate_source,
        base_exp_source=base_exp_source,
        base_dodge_source=base_dodge_source,
        base_potion_heal_source=base_potion_heal_source,
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
    _ = server_spec
    _ = preset
    _ = delay_ms
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
