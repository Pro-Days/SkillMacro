from __future__ import annotations

import pytest

from app.scripts.macro_models import (
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    MacroPreset,
    SkillUsageSetting,
)
from app.scripts.registry.server_registry import ServerSpec
from app.scripts.registry.skill_registry import ScrollDef, SkillDef
from app.scripts.skill_migration import (
    MigrationPair,
    SkillMigrationError,
    apply_skill_migration,
    get_builtin_scroll_defs,
    get_custom_scroll_defs,
    has_custom_scrolls,
)
from tests.conftest import SYNTHETIC_SERVER_ID, build_full_equipped_preset

# 테스트 커스텀 무공비급/스킬 ID 상수
CUSTOM_SCROLL_ID: str = f"custom:{SYNTHETIC_SERVER_ID}:커스텀비급"
CUSTOM_SKILL_A_ID: str = f"custom:{SYNTHETIC_SERVER_ID}:커스텀A"
CUSTOM_SKILL_B_ID: str = f"custom:{SYNTHETIC_SERVER_ID}:커스텀B"


def _inject_custom_scroll(server_spec: ServerSpec) -> None:
    """합성 서버 레지스트리에 커스텀 무공비급 주입"""

    # 커스텀 스킬 2개 등록
    for skill_id, name in (
        (CUSTOM_SKILL_A_ID, "커스텀A"),
        (CUSTOM_SKILL_B_ID, "커스텀B"),
    ):
        server_spec.skill_registry.add_skill_def(
            SkillDef(
                id=skill_id,
                server_id=SYNTHETIC_SERVER_ID,
                name=name,
                cooltime=5.0,
                target_count=1,
                levels={level: 1.0 for level in range(1, 16)},
            )
        )

    # 커스텀 무공비급 등록
    server_spec.skill_registry.add_scroll_def(
        ScrollDef(
            id=CUSTOM_SCROLL_ID,
            server_id=SYNTHETIC_SERVER_ID,
            name="커스텀비급",
            skills=(CUSTOM_SKILL_A_ID, CUSTOM_SKILL_B_ID),
        )
    )


@pytest.fixture
def server_with_custom_scroll(synthetic_server: ServerSpec) -> ServerSpec:
    """커스텀 무공비급 1개가 주입된 합성 서버"""

    _inject_custom_scroll(synthetic_server)
    return synthetic_server


@pytest.fixture
def migration_env(synthetic_server: ServerSpec) -> tuple[ServerSpec, MacroPreset]:
    """커스텀 무공비급 사용 프리셋과 주입 완료 서버 구성"""

    # 커스텀 주입 전 기본 풀 장착 프리셋 생성
    preset: MacroPreset = build_full_equipped_preset(synthetic_server)
    _inject_custom_scroll(synthetic_server)

    # 슬롯 0 장착/배치를 커스텀 무공비급으로 교체
    preset.skills.equipped_scrolls[0] = CUSTOM_SCROLL_ID
    preset.skills.placed_skills[0] = CUSTOM_SKILL_A_ID
    preset.skills.placed_skills[1] = CUSTOM_SKILL_B_ID

    # 커스텀 무공비급의 레벨/사용설정/연계 참조 구성
    preset.info.scroll_levels[CUSTOM_SCROLL_ID] = 7
    preset.usage_settings[CUSTOM_SKILL_A_ID] = SkillUsageSetting(
        use_alone=True, priority=2
    )
    preset.usage_settings[CUSTOM_SKILL_B_ID] = SkillUsageSetting(
        use_skill=False,
        use_alone=True,
        priority=4,
    )
    preset.link_skills.append(
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.ON,
            key="q",
            skills=[
                CUSTOM_SKILL_A_ID,
                CUSTOM_SKILL_B_ID,
                preset.skills.placed_skills[4],
            ],
        )
    )

    return synthetic_server, preset


def test_custom_scroll_listing(server_with_custom_scroll: ServerSpec) -> None:
    """커스텀/기본 무공비급 분류 조회 검증"""

    assert has_custom_scrolls(server_with_custom_scroll) is True

    custom_ids: list[str] = [
        scroll_def.id for scroll_def in get_custom_scroll_defs(server_with_custom_scroll)
    ]
    assert custom_ids == [CUSTOM_SCROLL_ID]

    builtin_ids: list[str] = [
        scroll_def.id
        for scroll_def in get_builtin_scroll_defs(server_with_custom_scroll)
    ]
    assert CUSTOM_SCROLL_ID not in builtin_ids
    assert len(builtin_ids) == server_with_custom_scroll.scroll_slot_count


def test_migration_replaces_all_references(
    migration_env: tuple[ServerSpec, MacroPreset],
) -> None:
    """커스텀 -> 기본 교체 시 프리셋 전체 참조 이관 검증"""

    server_spec, preset = migration_env

    # 첫 번째 기본 무공비급으로 교체 쌍 구성
    builtin_scroll_id: str = f"builtin:{SYNTHETIC_SERVER_ID}:scroll_0"
    builtin_scroll: ScrollDef = server_spec.skill_registry.get_scroll(builtin_scroll_id)
    pair: MigrationPair = MigrationPair.create(
        server_spec=server_spec,
        custom_scroll_id=CUSTOM_SCROLL_ID,
        builtin_scroll_id=builtin_scroll_id,
    )

    apply_skill_migration(
        presets=[preset],
        server_id=SYNTHETIC_SERVER_ID,
        pairs=[pair],
    )

    # 장착/배치 참조 교체 확인
    assert preset.skills.equipped_scrolls[0] == builtin_scroll_id
    assert preset.skills.placed_skills[0] == builtin_scroll.skills[0]
    assert preset.skills.placed_skills[1] == builtin_scroll.skills[1]

    # 무공비급 레벨 이관 확인 (커스텀 항목 보존)
    assert preset.info.scroll_levels[builtin_scroll_id] == 7
    assert preset.info.scroll_levels[CUSTOM_SCROLL_ID] == 7

    # 사용설정 복사 확인 (객체 공유 방지)
    migrated_setting_a: SkillUsageSetting = preset.usage_settings[
        builtin_scroll.skills[0]
    ]
    migrated_setting_b: SkillUsageSetting = preset.usage_settings[
        builtin_scroll.skills[1]
    ]
    assert migrated_setting_a.use_alone is True
    assert migrated_setting_a.priority == 2
    assert migrated_setting_a is not preset.usage_settings[CUSTOM_SKILL_A_ID]
    assert migrated_setting_b.use_skill is False
    assert migrated_setting_b.use_alone is True
    assert migrated_setting_b.priority == 4
    assert migrated_setting_b is not preset.usage_settings[CUSTOM_SKILL_B_ID]

    # 연계스킬 참조 교체와 키/자동 상태 유지 확인
    migrated_link: LinkSkill = preset.link_skills[-1]
    assert migrated_link.skills[:2] == list(builtin_scroll.skills)
    assert migrated_link.use_type == LinkUseType.AUTO
    assert migrated_link.key == "q"


def test_migration_skips_other_server_presets(
    migration_env: tuple[ServerSpec, MacroPreset],
) -> None:
    """다른 서버 프리셋의 마이그레이션 제외 검증"""

    server_spec, preset = migration_env
    preset.settings.server_id = "다른 서버"
    original_preset: dict[str, object] = preset.to_dict()

    pair: MigrationPair = MigrationPair.create(
        server_spec=server_spec,
        custom_scroll_id=CUSTOM_SCROLL_ID,
        builtin_scroll_id=f"builtin:{SYNTHETIC_SERVER_ID}:scroll_0",
    )

    apply_skill_migration(
        presets=[preset],
        server_id=SYNTHETIC_SERVER_ID,
        pairs=[pair],
    )

    # 서버 불일치 프리셋의 전체 상태 유지 확인
    assert preset.to_dict() == original_preset


def test_migration_pair_rejects_wrong_direction(
    server_with_custom_scroll: ServerSpec,
) -> None:
    """교체 방향 위반 입력의 명시적 거부 검증"""

    builtin_scroll_id: str = f"builtin:{SYNTHETIC_SERVER_ID}:scroll_0"

    # 기본 -> 기본 교체 시도 거부
    with pytest.raises(SkillMigrationError):
        MigrationPair.create(
            server_spec=server_with_custom_scroll,
            custom_scroll_id=builtin_scroll_id,
            builtin_scroll_id=builtin_scroll_id,
        )

    # 커스텀 -> 커스텀 교체 시도 거부
    with pytest.raises(SkillMigrationError):
        MigrationPair.create(
            server_spec=server_with_custom_scroll,
            custom_scroll_id=CUSTOM_SCROLL_ID,
            builtin_scroll_id=CUSTOM_SCROLL_ID,
        )
