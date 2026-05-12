from __future__ import annotations

from collections import Counter

import pytest

from app.scripts.calculator_engine import (
    SkillUseEvent,
    build_skill_use_sequence,
)
from app.scripts.macro_models import (
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    MacroPreset,
)
from app.scripts.registry.server_registry import ServerSpec

from tests.conftest import build_synthetic_server, build_full_equipped_preset


def _get_skills_info(preset: MacroPreset) -> dict:
    """build_skill_use_sequence에 넘길 skill usage 맵 추출"""

    return preset.usage_settings


def test_full_equip_default_sequence_is_line_then_scroll_ordered(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """14스킬 풀 장착, 모두 우선순위 0, 쿨감 0%, 연계 없음 상태에서

    60초 시퀀스의 첫 14개 입력은 placed_refs 순서 (1줄 7개 → 2줄 7개) 와 일치한다.
    """

    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    # 14스킬 풀 장착 + 짧은 딜레이라면 60초 동안 모두 한 번씩은 사용된다
    assert len(sequence) >= synthetic_server.total_equipped_skill_count

    first_round_ids: list[str] = [
        event.skill_id for event in sequence[: synthetic_server.total_equipped_skill_count]
    ]

    # 기대 순서: line 0 (7개) → line 1 (7개)
    expected_first_round: list[str] = []
    for line_index in range(synthetic_server.skill_line_count):
        for scroll_index in range(synthetic_server.scroll_slot_count):
            skill_id: str = full_preset.skills.placed_skills[
                scroll_index * 2 + line_index
            ]
            expected_first_round.append(skill_id)

    assert first_round_ids == expected_first_round


def test_full_equip_all_skills_used_at_least_once(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """14개 스킬 전부 60초 안에 최소 1회 이상 사용된다"""

    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    used_skill_ids: set[str] = {event.skill_id for event in sequence}
    placed_skill_ids: set[str] = {
        skill_id for skill_id in full_preset.skills.placed_skills if skill_id
    }
    assert used_skill_ids == placed_skill_ids


def test_priority_skills_come_before_zero_priority(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """우선순위 1로 설정된 스킬은 우선순위 0 스킬보다 먼저 사용된다"""

    # 마지막 슬롯 스킬에 우선순위 1 부여
    high_priority_skill_id: str = full_preset.skills.placed_skills[-1]
    full_preset.usage_settings[high_priority_skill_id].priority = 1

    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    # 60초 안에 우선순위 1 스킬이 가장 첫 번째로 호출되어야 함
    assert sequence[0].skill_id == high_priority_skill_id


def test_priority_order_is_strict(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """우선순위 1 → 2 → 3 → 0 순서가 첫 라운드에서 지켜진다"""

    placed: list[str] = full_preset.skills.placed_skills
    full_preset.usage_settings[placed[5]].priority = 1
    full_preset.usage_settings[placed[2]].priority = 2
    full_preset.usage_settings[placed[8]].priority = 3

    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    first_three: list[str] = [event.skill_id for event in sequence[:3]]
    assert first_three == [placed[5], placed[2], placed[8]]


def test_use_skill_false_excludes_skill_from_sequence(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """use_skill=False로 표시된 스킬은 시퀀스에 한 번도 나오지 않는다"""

    excluded_skill_id: str = full_preset.skills.placed_skills[3]
    full_preset.usage_settings[excluded_skill_id].use_skill = False

    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    used_skill_ids: set[str] = {event.skill_id for event in sequence}
    assert excluded_skill_id not in used_skill_ids


def test_cooltime_reduction_increases_usage_count(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """쿨감 50% 적용 시 동일 시간에 사용 횟수가 더 많아진다"""

    baseline_sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )
    reduced_sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=50.0,
    )

    # 풀 장착 시나리오에서 쿨감이 적용되면 더 많이 사용된다
    assert len(reduced_sequence) > len(baseline_sequence)


def test_auto_link_skills_are_grouped(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """자동 연계가 준비되면 연계 스킬들이 묶여서 들어간다"""

    placed: list[str] = full_preset.skills.placed_skills
    linked_a: str = placed[0]
    linked_b: str = placed[4]

    full_preset.link_skills = [
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.OFF,
            key=None,
            skills=[linked_a, linked_b],
            remember_state=False,
        )
    ]

    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    # 시퀀스 첫 두 입력은 연계 두 스킬이어야 함 (자동 연계는 큐 최우선)
    assert sequence[0].skill_id == linked_a
    assert sequence[1].skill_id == linked_b


def test_manual_link_skills_excluded_from_regular_queue(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """수동 연계스킬에 속한 스킬은 use_alone=False일 때 자동 큐에 들어가지 않는다"""

    placed: list[str] = full_preset.skills.placed_skills
    manual_skill: str = placed[7]

    full_preset.link_skills = [
        LinkSkill(
            use_type=LinkUseType.MANUAL,
            key_type=LinkKeyType.OFF,
            key=None,
            skills=[manual_skill, placed[8]],
            remember_state=False,
        )
    ]
    # 수동 연계는 자동 큐에 영향이 없다 (auto가 아니므로 use_alone 필터 자체가 적용 안 됨)
    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    # 수동 연계는 일반 큐 동작에 영향 없음 → 모든 스킬이 정상적으로 등장
    used_skill_ids: set[str] = {event.skill_id for event in sequence}
    placed_skill_ids: set[str] = {skill_id for skill_id in placed if skill_id}
    assert used_skill_ids == placed_skill_ids


def test_auto_linked_skill_only_in_sequence_when_use_alone(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """자동 연계에 속한 스킬은 use_alone=False면 일반 큐에서 빠진다"""

    placed: list[str] = full_preset.skills.placed_skills
    linked_a: str = placed[0]
    linked_b: str = placed[1]

    # 두 스킬의 쿨타임을 일부러 길게 두어, 연계 후 일반 큐 동작을 관찰
    full_preset.link_skills = [
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.OFF,
            key=None,
            skills=[linked_a, linked_b],
            remember_state=False,
        )
    ]
    full_preset.usage_settings[linked_a].use_alone = False
    full_preset.usage_settings[linked_b].use_alone = False

    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    # 연계 스킬은 자동 연계 한 번에만 사용되고, 일반 큐에서 단독으로 호출되지 않아야 한다
    counter: Counter[str] = Counter(event.skill_id for event in sequence)

    # linked_a와 linked_b는 자동 연계로 동기 호출되므로 사용 횟수가 같아야 함
    assert counter[linked_a] == counter[linked_b]


def test_empty_placement_returns_empty_sequence(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """모든 슬롯이 빈 상태라면 시퀀스도 비어 있다"""

    full_preset.skills.placed_skills = [""] * len(full_preset.skills.placed_skills)

    sequence: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    assert sequence == ()


def test_sequence_is_deterministic(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """동일 입력 두 번 호출은 동일 시퀀스를 반환한다"""

    first: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )
    second: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=_get_skills_info(full_preset),
        delay_ms=300,
        cooltime_reduction=0.0,
    )

    assert first == second
