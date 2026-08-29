from __future__ import annotations

from dataclasses import dataclass
from math import fsum, isfinite
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.scripts.custom_skill_models import CustomSkillDefinition

BUILTIN_SKILL_PREFIX = "builtin"
CUSTOM_SKILL_PREFIX = "custom"


def get_builtin_skill_id(server_id: str, skill_name: str) -> str:
    """builtin 스킬 ID 생성"""

    return f"{BUILTIN_SKILL_PREFIX}:{server_id}:{skill_name}"


def is_builtin_skill_id(skill_id: str) -> bool:
    """기본 스킬/무공비급 ID 여부"""

    # 기본 스킬 네임스페이스 접두사 확인
    return skill_id.startswith(f"{BUILTIN_SKILL_PREFIX}:")


def is_custom_skill_id(skill_id: str) -> bool:
    """커스텀 스킬/무공비급 ID 여부"""

    # 커스텀 스킬 네임스페이스 접두사 확인
    return skill_id.startswith(f"{CUSTOM_SKILL_PREFIX}:")


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
class SkillHitDef:
    """스킬 단일 타격 데이터"""

    offset_ms: int
    multiplier: float


@dataclass(frozen=True, slots=True)
class SkillDef:
    """스킬 데이터"""

    id: str
    server_id: str
    name: str
    cooltime: float
    target_count: int
    hits_by_level: dict[int, tuple[SkillHitDef, ...]]

    @property
    def levels(self) -> dict[int, float]:
        """호버와 계산식용 레벨별 총 데미지 계수 반환"""

        return {
            level: fsum(hit.multiplier for hit in hits)
            for level, hits in self.hits_by_level.items()
        }

    @classmethod
    def from_immediate_levels(
        cls,
        skill_id: str,
        server_id: str,
        name: str,
        cooltime: float,
        target_count: int,
        levels: dict[int, float],
    ) -> "SkillDef":
        """레벨별 총 계수를 사용 즉시 발생하는 단일 타격으로 변환"""

        hits_by_level: dict[int, tuple[SkillHitDef, ...]] = {
            level: (SkillHitDef(offset_ms=0, multiplier=damage),)
            for level, damage in levels.items()
        }
        return cls(
            id=skill_id,
            server_id=server_id,
            name=name,
            cooltime=cooltime,
            target_count=target_count,
            hits_by_level=hits_by_level,
        )

    @classmethod
    def from_custom_definition(
        cls,
        server_id: str,
        definition: "CustomSkillDefinition",
    ) -> "SkillDef":
        """검증된 커스텀 스킬 정의를 단일 타격 SkillDef로 변환"""

        return cls.from_immediate_levels(
            skill_id=definition.skill_id,
            server_id=server_id,
            name=definition.name,
            cooltime=definition.cooltime,
            target_count=definition.target_count,
            levels=definition.levels,
        )

    @classmethod
    def from_builtin_detail_dict(
        cls, skill_id: str, server_id: str, detail: dict[str, Any]
    ) -> "SkillDef":
        """빌트인 스킬 타격 데이터를 SkillDef로 변환"""

        raw_damage_events: Any = detail["damage_events"]
        if not isinstance(raw_damage_events, list):
            raise TypeError("skill damage_events must be a list")

        if not raw_damage_events:
            raise ValueError("skill damage_events must contain at least one event")

        mutable_hits_by_level: dict[int, list[SkillHitDef]] = {}
        previous_offset_ms: int = -1
        for raw_damage_event in raw_damage_events:
            if not isinstance(raw_damage_event, dict):
                raise TypeError("skill damage event must be a dict")

            offset_ms: Any = raw_damage_event["offset_ms"]
            if type(offset_ms) is not int:
                raise TypeError("skill hit offset_ms must be an integer")

            if offset_ms < 0:
                raise ValueError(
                    "skill hit offset_ms must be greater than or equal to 0"
                )

            if offset_ms < previous_offset_ms:
                raise ValueError("skill damage_events must be ordered by offset_ms")

            previous_offset_ms = offset_ms
            raw_event_levels: Any = raw_damage_event["levels"]
            if not isinstance(raw_event_levels, dict):
                raise TypeError("skill damage event levels must be a dict")

            if not raw_event_levels:
                raise ValueError("skill damage event levels must not be empty")

            for level_str, multiplier_value in raw_event_levels.items():
                level: int = int(level_str)
                multiplier: float = float(multiplier_value)
                if not isfinite(multiplier) or multiplier <= 0.0:
                    raise ValueError(
                        "skill damage event multiplier must be a positive finite number"
                    )

                hit: SkillHitDef = SkillHitDef(
                    offset_ms=offset_ms,
                    multiplier=multiplier,
                )
                mutable_hits_by_level.setdefault(level, []).append(hit)

        hits_by_level: dict[int, tuple[SkillHitDef, ...]] = {
            level: tuple(hits) for level, hits in mutable_hits_by_level.items()
        }

        return cls(
            id=skill_id,
            server_id=server_id,
            name=detail["name"],
            cooltime=float(detail["cooltime"]),
            target_count=int(detail["target_count"]),
            hits_by_level=hits_by_level,
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

            skill_def: SkillDef = SkillDef.from_builtin_detail_dict(
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
