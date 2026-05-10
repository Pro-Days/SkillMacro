from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BUILTIN_SKILL_PREFIX = "builtin"
CUSTOM_SKILL_PREFIX = "custom"


def get_builtin_skill_id(server_id: str, skill_name: str) -> str:
    """builtin 스킬 ID 생성"""

    return f"{BUILTIN_SKILL_PREFIX}:{server_id}:{skill_name}"


def parse_skill_id(skill_id: str) -> tuple[str, str]:
    """스킬 ID를 (server_id, skill_name) 튜플로 파싱"""

    if not skill_id:
        raise ValueError("skill_id must be a non-empty string")

    splited: list[str] = skill_id.split(":", 2)

    if len(splited) != 3:
        raise ValueError("skill_id must be in the format 'prefix:server_id:skill_name'")

    prefix, server_id, skill_name = splited

    return server_id, skill_name


@dataclass(frozen=True, slots=True)
class SkillDef:
    """스킬 데이터"""

    id: str
    server_id: str
    name: str
    cooltime: float
    target_count: int
    levels: dict[int, float]

    @staticmethod
    def from_detail_dict(
        skill_id: str, server_id: str, detail: dict[str, Any]
    ) -> "SkillDef":
        """detail dict에서 SkillDef 생성"""

        levels: dict[int, float] = {
            int(level_str): float(level_detail)
            for level_str, level_detail in detail["levels"].items()
        }

        return SkillDef(
            id=skill_id,
            server_id=server_id,
            name=detail["name"],
            cooltime=float(detail["cooltime"]),
            target_count=int(detail["target_count"]),
            levels=levels,
        )


@dataclass(frozen=True, slots=True)
class ScrollDef:
    """무공비급 데이터"""

    id: str
    server_id: str
    name: str
    skills: tuple[str, str]

    @classmethod
    def from_dict(cls, server_id: str, detail: dict[str, Any]) -> "ScrollDef":
        """detail dict에서 ScrollDef 생성"""

        skills: list[str] = list(detail["skills"])
        if len(skills) != 2:
            raise ValueError("scroll skills must contain exactly 2 skill ids")

        return cls(
            id=detail["scroll_id"],
            server_id=server_id,
            name=detail["name"],
            skills=(skills[0], skills[1]),
        )


@dataclass
class SkillRegistry:
    """스킬 레지스트리"""

    _skills: dict[str, SkillDef]
    _scrolls: dict[str, ScrollDef]
    _skill_to_scroll: dict[str, str]

    def add_skill_def(self, skill_def: SkillDef) -> None:
        self._skills[skill_def.id] = skill_def

    def add_scroll_def(self, scroll_def: ScrollDef) -> None:
        self._scrolls[scroll_def.id] = scroll_def
        for skill_id in scroll_def.skills:
            self._skill_to_scroll[skill_id] = scroll_def.id

    def remove_skill_def(self, skill_id: str) -> None:
        self._skills.pop(skill_id, None)
        self._skill_to_scroll.pop(skill_id, None)

    def remove_scroll_def(self, scroll_id: str) -> None:
        scroll_def = self._scrolls.pop(scroll_id, None)
        if scroll_def:
            for skill_id in scroll_def.skills:
                self._skill_to_scroll.pop(skill_id, None)

    def get_all_skill_ids(self) -> list[str]:
        return list(self._skills.keys())

    def get_all_skill_defs(self) -> list[SkillDef]:
        return list(self._skills.values())

    def get(self, skill_id: str) -> SkillDef:
        return self._skills[skill_id]

    def get_all_scroll_ids(self) -> list[str]:
        return list(self._scrolls.keys())

    def get_all_scroll_defs(self) -> list[ScrollDef]:
        return list(self._scrolls.values())

    def get_scroll(self, scroll_id: str) -> ScrollDef:
        return self._scrolls[scroll_id]

    def get_scroll_id_by_skill_id(self, skill_id: str) -> str:
        return self._skill_to_scroll[skill_id]

    @classmethod
    def from_skill_data(
        cls, skill_data: dict[str, Any], server_id: str
    ) -> SkillRegistry:
        """skill_data에서 SkillRegistry 생성"""

        server_data: dict[str, Any] = skill_data[server_id]

        skill_ids: list[str] = server_data["skills"]
        details: dict[str, dict[str, Any]] = server_data["skill_details"]
        scroll_details: list[dict[str, Any]] = server_data["scrolls"]

        skills: dict[str, SkillDef] = {}
        for skill_id in skill_ids:
            detail: dict[str, Any] = details[skill_id]

            skill_def: SkillDef = SkillDef.from_detail_dict(
                skill_id=skill_id, server_id=server_id, detail=detail
            )
            skills[skill_id] = skill_def

        scrolls: dict[str, ScrollDef] = {}
        skill_to_scroll: dict[str, str] = {}
        for detail in scroll_details:
            scroll_def: ScrollDef = ScrollDef.from_dict(
                server_id=server_id,
                detail=detail,
            )
            scrolls[scroll_def.id] = scroll_def

            for skill_id in scroll_def.skills:
                skill_to_scroll[skill_id] = scroll_def.id

        return cls(
            _skills=skills,
            _scrolls=scrolls,
            _skill_to_scroll=skill_to_scroll,
        )
