from __future__ import annotations

import copy
from dataclasses import dataclass

from app.scripts.macro_models import LinkSkill, MacroPreset
from app.scripts.registry.server_registry import ServerSpec
from app.scripts.registry.skill_registry import (
    ScrollDef,
    is_builtin_skill_id,
    is_custom_skill_id,
)


class SkillMigrationError(ValueError):
    """스킬 마이그레이션 입력 오류"""


def get_custom_scroll_defs(server_spec: ServerSpec) -> list[ScrollDef]:
    """서버의 커스텀 무공비급 목록 반환 (이름순 정렬)"""

    custom_scrolls: list[ScrollDef] = [
        scroll_def
        for scroll_def in server_spec.skill_registry.get_all_scroll_defs()
        if is_custom_skill_id(scroll_def.id)
    ]
    return sorted(custom_scrolls, key=lambda scroll_def: scroll_def.name)


def get_builtin_scroll_defs(server_spec: ServerSpec) -> list[ScrollDef]:
    """서버의 기본 무공비급 목록 반환 (이름순 정렬)"""

    builtin_scrolls: list[ScrollDef] = [
        scroll_def
        for scroll_def in server_spec.skill_registry.get_all_scroll_defs()
        if is_builtin_skill_id(scroll_def.id)
    ]
    return sorted(builtin_scrolls, key=lambda scroll_def: scroll_def.name)


def has_custom_scrolls(server_spec: ServerSpec) -> bool:
    """서버에 커스텀 무공비급 존재 여부"""

    return any(
        is_custom_skill_id(scroll_def.id)
        for scroll_def in server_spec.skill_registry.get_all_scroll_defs()
    )


@dataclass(frozen=True, slots=True)
class MigrationPair:
    """커스텀 -> 기본 무공비급 교체 pair"""

    custom_scroll_id: str
    builtin_scroll_id: str
    # 커스텀 스킬 ID -> 기본 스킬 ID (무공비급 내 위치 순서 기준)
    skill_map: dict[str, str]

    @classmethod
    def create(
        cls,
        server_spec: ServerSpec,
        custom_scroll_id: str,
        builtin_scroll_id: str,
    ) -> "MigrationPair":
        """레지스트리 기준 교체 쌍 생성"""

        # 교체 방향 검증
        if not is_custom_skill_id(custom_scroll_id):
            raise SkillMigrationError("교체 대상은 커스텀 무공비급이어야 합니다.")

        if not is_builtin_skill_id(builtin_scroll_id):
            raise SkillMigrationError("교체될 무공비급은 기본 무공비급이어야 합니다.")

        custom_scroll: ScrollDef = server_spec.skill_registry.get_scroll(
            custom_scroll_id
        )
        builtin_scroll: ScrollDef = server_spec.skill_registry.get_scroll(
            builtin_scroll_id
        )

        # 두 무공비급 모두 정확히 2개 스킬을 가지므로 위치 순서로 매핑
        skill_map: dict[str, str] = {
            custom_skill_id: builtin_skill_id
            for custom_skill_id, builtin_skill_id in zip(
                custom_scroll.skills, builtin_scroll.skills
            )
        }

        return cls(
            custom_scroll_id=custom_scroll_id,
            builtin_scroll_id=builtin_scroll_id,
            skill_map=skill_map,
        )


def _migrate_preset(
    preset: MacroPreset,
    scroll_map: dict[str, str],
    skill_map: dict[str, str],
) -> None:
    """단일 프리셋의 무공비급/스킬 참조 교체"""

    # 장착 중인 무공비급 교체
    for index, scroll_id in enumerate(preset.skills.equipped_scrolls):
        if scroll_id in scroll_map:
            preset.skills.equipped_scrolls[index] = scroll_map[scroll_id]

    # 하단 배치 스킬 교체
    for index, skill_id in enumerate(preset.skills.placed_skills):
        if skill_id in skill_map:
            preset.skills.placed_skills[index] = skill_map[skill_id]

    # 무공비급 레벨 복사 (기본이 커스텀 값을 물려받음, 커스텀 항목은 보존)
    for custom_scroll_id, builtin_scroll_id in scroll_map.items():
        if custom_scroll_id in preset.info.scroll_levels:
            preset.info.scroll_levels[builtin_scroll_id] = preset.info.scroll_levels[
                custom_scroll_id
            ]

    # 일반 스킬 사용 설정 복사 (객체 공유 방지, 커스텀 항목은 보존)
    for custom_skill_id, builtin_skill_id in skill_map.items():
        if custom_skill_id in preset.usage_settings:
            preset.usage_settings[builtin_skill_id] = copy.copy(
                preset.usage_settings[custom_skill_id]
            )

    # 연계스킬에 등록된 스킬만 교체하고 자동/수동·키·기억 상태는 유지
    link_skill: LinkSkill
    for link_skill in preset.link_skills:
        link_skill.skills = [
            skill_map.get(skill_id, skill_id) for skill_id in link_skill.skills
        ]


def apply_skill_migration(
    presets: list[MacroPreset],
    server_id: str,
    pairs: list[MigrationPair],
) -> None:
    """선택한 교체 쌍을 해당 서버의 모든 프리셋에 적용"""

    if not pairs:
        return

    # 통합 무공비급/스킬 매핑 구성
    scroll_map: dict[str, str] = {}
    skill_map: dict[str, str] = {}
    pair: MigrationPair
    for pair in pairs:
        scroll_map[pair.custom_scroll_id] = pair.builtin_scroll_id
        skill_map.update(pair.skill_map)

    # 같은 서버를 사용하는 모든 프리셋 교체
    preset: MacroPreset
    for preset in presets:
        if preset.settings.server_id != server_id:
            continue

        _migrate_preset(preset, scroll_map, skill_map)
