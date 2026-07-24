from __future__ import annotations

import pytest

from app.scripts.character_data import (
    ADDITIONAL_OPTION_SPECS,
    ELIXIR_SPECS,
    EQUIPMENT_ITEM_SPECS,
    PILL_SPECS,
    POTENTIAL_OPTION_SPECS,
    OptionSpec,
)
from app.scripts.character_models import MAX_TALISMAN_LEVEL, TALISMAN_SPECS
from app.scripts.registry.server_registry import ServerSpec, server_registry


@pytest.fixture(scope="module")
def hanwol_server() -> ServerSpec:
    """실제 skill_data.json 기반 한월 RPG 서버 스펙"""

    return server_registry.get("한월 RPG")


def test_hanwol_server_loads_with_expected_shape(hanwol_server: ServerSpec) -> None:
    """한월 RPG 서버 데이터의 기본 구성 검증"""

    assert hanwol_server.scroll_slot_count == 7
    assert hanwol_server.skill_line_count == 2
    assert hanwol_server.skills_per_scroll == 2
    assert hanwol_server.max_skill_level == 15

    # 무공비급과 스킬 데이터 존재 확인
    assert len(hanwol_server.skill_registry.get_all_scroll_ids()) > 0
    assert len(hanwol_server.skill_registry.get_all_skill_ids()) > 0


def test_every_scroll_references_existing_skills(hanwol_server: ServerSpec) -> None:
    """모든 무공비급의 스킬 참조 무결성 검증"""

    skill_ids: set[str] = set(hanwol_server.skill_registry.get_all_skill_ids())

    for scroll_def in hanwol_server.skill_registry.get_all_scroll_defs():
        # 무공비급당 스킬 2개 구성 확인
        assert len(scroll_def.skills) == 2, f"{scroll_def.id} 스킬 수 오류"

        # 참조 스킬 존재와 소속 역참조 일치 확인
        for skill_id in scroll_def.skills:
            assert skill_id in skill_ids, f"{scroll_def.id}의 {skill_id} 참조 끊김"
            assert (
                hanwol_server.skill_registry.get_scroll_id_by_skill_id(skill_id)
                == scroll_def.id
            ), f"{skill_id} 소속 무공비급 역참조 불일치"


def test_every_scroll_skill_has_complete_level_table(
    hanwol_server: ServerSpec,
) -> None:
    """무공비급 스킬의 레벨 1~15 데미지 계수 완결성 검증"""

    for scroll_def in hanwol_server.skill_registry.get_all_scroll_defs():
        for skill_id in scroll_def.skills:
            skill_def = hanwol_server.skill_registry.get(skill_id)

            # 쿨타임/타겟 수 유효 범위 확인
            assert skill_def.cooltime > 0.0, f"{skill_id} 쿨타임 오류"
            assert skill_def.target_count >= 1, f"{skill_id} 타겟 수 오류"

            # 전체 레벨 구간 데미지 계수 존재와 양수 확인
            for level in range(1, hanwol_server.max_skill_level + 1):
                assert level in skill_def.levels, f"{skill_id} 레벨 {level} 누락"
                assert skill_def.levels[level] > 0.0, f"{skill_id} 레벨 {level} 계수 오류"


def test_talisman_specs_cover_all_levels() -> None:
    """부적 데이터의 전체 레벨 구간 수치 완결성 검증"""

    assert len(TALISMAN_SPECS) > 0

    seen_names: set[str] = set()
    for spec in TALISMAN_SPECS:
        # 부적 이름 중복 차단 확인 (이름이 저장 참조 키로 사용됨)
        assert spec.name not in seen_names, f"부적 이름 중복: {spec.name}"
        seen_names.add(spec.name)

        # 레벨 0~14 전체 수치 존재 확인
        for level in range(0, MAX_TALISMAN_LEVEL + 1):
            assert level in spec.level_stats, f"{spec.name} 레벨 {level} 누락"


def test_equipment_and_consumable_specs_are_valid() -> None:
    """장비/소모품 정적 데이터의 기본 무결성 검증"""

    assert len(EQUIPMENT_ITEM_SPECS) > 0
    assert len(ELIXIR_SPECS) > 0
    assert len(PILL_SPECS) > 0

    # 잠재/추가 옵션 수치 범위 유효성 확인
    option_spec: OptionSpec
    for option_spec in (*POTENTIAL_OPTION_SPECS.values(), *ADDITIONAL_OPTION_SPECS.values()):
        assert option_spec.value_range.minimum <= option_spec.value_range.maximum
