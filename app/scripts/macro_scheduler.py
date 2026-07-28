from __future__ import annotations

from typing import TYPE_CHECKING

from app.scripts.macro_models import EquippedSkillRef, LinkUseType, SkillUsageSetting

if TYPE_CHECKING:
    from app.scripts.macro_models import MacroPreset
    from app.scripts.registry.server_registry import ServerSpec


BASIC_ATTACK_AFTER_SKILL_MILLISECONDS: int = 300
BASIC_ATTACK_BEFORE_SKILL_MILLISECONDS: int = 150
BASIC_ATTACK_INTERVAL_MILLISECONDS: int = 600


def can_use_basic_attack(
    current_time: float,
    last_skill_input_at: float | None,
    next_skill_input_at: float | None,
) -> bool:
    """직전·다음 스킬 시각 기준 평타 입력 허용 여부 반환"""

    after_skill_seconds: float = (
        BASIC_ATTACK_AFTER_SKILL_MILLISECONDS * 0.001
    )
    if (
        last_skill_input_at is not None
        and current_time < last_skill_input_at + after_skill_seconds
    ):
        return False

    before_skill_seconds: float = (
        BASIC_ATTACK_BEFORE_SKILL_MILLISECONDS * 0.001
    )
    return (
        next_skill_input_at is None
        or current_time < next_skill_input_at - before_skill_seconds
    )


def build_priority_skill_sequence(
    server_spec: ServerSpec,
    preset: MacroPreset,
    skills_info: dict[str, SkillUsageSetting],
) -> tuple[EquippedSkillRef, ...]:
    """우선순위와 배치 순서 기준 스킬 시퀀스 구성"""

    placed_refs: list[EquippedSkillRef] = preset.skills.get_placed_skill_refs(
        server_spec
    )
    skill_sequence: list[EquippedSkillRef] = []
    for target_priority in range(1, len(placed_refs) + 1):
        for skill_ref in placed_refs:
            skill_id: str = preset.skills.get_placed_skill_id(skill_ref)
            if skills_info[skill_id].priority == target_priority:
                skill_sequence.append(skill_ref)

    for skill_ref in placed_refs:
        if skill_ref not in skill_sequence:
            skill_sequence.append(skill_ref)

    return tuple(skill_sequence)


def build_auto_link_skill_groups(
    server_spec: ServerSpec,
    preset: MacroPreset,
) -> tuple[tuple[EquippedSkillRef, ...], ...]:
    """현재 배치로 완결되는 자동 연계 그룹 구성"""

    skill_ref_map: dict[str, EquippedSkillRef] = (
        preset.skills.get_placed_skill_ref_map(server_spec)
    )
    return tuple(
        tuple(skill_ref_map[skill_id] for skill_id in link_skill.skills)
        for link_skill in preset.link_skills
        if link_skill.use_type == LinkUseType.AUTO
        and all(skill_id in skill_ref_map for skill_id in link_skill.skills)
    )


def take_next_task(
    preset: MacroPreset,
    skills_info: dict[str, SkillUsageSetting],
    prepared_skills: set[EquippedSkillRef],
    auto_link_skill_groups: tuple[tuple[EquippedSkillRef, ...], ...],
    skill_sequence: tuple[EquippedSkillRef, ...],
) -> tuple[EquippedSkillRef, ...]:
    """준비 상태에서 다음 자동 연계 또는 일반 스킬을 꺼냄"""

    for link_skill_group in auto_link_skill_groups:
        if not all(skill_ref in prepared_skills for skill_ref in link_skill_group):
            continue

        for skill_ref in link_skill_group:
            prepared_skills.discard(skill_ref)
        return link_skill_group

    linked_skill_refs: set[EquippedSkillRef] = {
        skill_ref
        for link_skill_group in auto_link_skill_groups
        for skill_ref in link_skill_group
    }
    for skill_ref in skill_sequence:
        if skill_ref not in prepared_skills:
            continue

        skill_id: str = preset.skills.get_placed_skill_id(skill_ref)
        setting: SkillUsageSetting = skills_info[skill_id]
        in_link_skill: bool = skill_ref in linked_skill_refs
        can_use: bool = (in_link_skill and setting.use_alone) or (
            not in_link_skill and setting.use_skill
        )
        if not can_use:
            continue

        prepared_skills.discard(skill_ref)
        return (skill_ref,)

    return ()


def build_skill_cooltimes_ms(
    server_spec: ServerSpec,
    preset: MacroPreset,
    cooltime_reduction: float,
) -> dict[EquippedSkillRef, int]:
    """쿨타임 감소가 반영된 스킬별 밀리초 쿨타임 구성"""

    return {
        skill_ref: round(
            server_spec.skill_registry.get(
                preset.skills.get_placed_skill_id(skill_ref)
            ).cooltime
            * (100 - cooltime_reduction)
            * 10
        )
        for skill_ref in preset.skills.get_placed_skill_refs(server_spec)
    }
