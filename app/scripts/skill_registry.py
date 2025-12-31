from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

BUILTIN_SKILL_PREFIX = "builtin"


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
    levels: dict[str, list[dict[str, Any]]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_detail(
        skill_id: str, server_id: str, detail: dict[str, Any]
    ) -> "SkillDef":
        """detail dict에서 SkillDef 생성"""

        return SkillDef(
            id=skill_id,
            server_id=server_id,
            name=detail["name"],
            cooltime=detail["cooltime"],
            levels=detail["levels"],
        )


class SkillRegistry:
    """스킬 레지스트리"""

    # todo: dict -> class

    def __init__(self, skills: dict[str, SkillDef]) -> None:
        self._skills: dict[str, SkillDef] = skills.copy()

    def all_skill_ids(self) -> list[str]:
        return list(self._skills.keys())

    def get(self, skill_id: str) -> SkillDef:
        return self._skills[skill_id]

    def name(self, skill_id: str) -> str:
        return self.get(skill_id).name

    def details(self, skill_id: str) -> dict[str, Any]:
        return self.get(skill_id).as_dict()

    @classmethod
    def from_skill_data(
        cls, skill_data: dict[str, Any], server_id: str
    ) -> "SkillRegistry":
        """skill_data에서 SkillRegistry 생성"""

        server_data: dict[str, Any] = skill_data[server_id]

        skill_ids: list[str] = server_data["skills"]
        details: dict[str, dict[str, Any]] = server_data["skill_details"]

        skills: dict[str, SkillDef] = {}
        for skill_id in skill_ids:
            detail: dict[str, Any] = details[skill_id]

            skill_def: SkillDef = SkillDef.from_detail(
                skill_id=skill_id, server_id=server_id, detail=detail
            )
            skills[skill_id] = skill_def

        return cls(skills)
