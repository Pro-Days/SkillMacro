from __future__ import annotations

import enum
from dataclasses import asdict, dataclass
from typing import Any

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


class LevelEffectType(enum.Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    BUFF = "buff"


@dataclass(frozen=True, slots=True)
class LevelEffect:
    """스킬 레벨별 효과 데이터"""

    level: int
    time: float

    @classmethod
    def from_dict(cls, level: int, effect_dict: dict[str, Any]) -> LevelEffect:
        if effect_dict["type"] == LevelEffectType.DAMAGE.value:
            return DamageEffect(
                level=level,
                time=effect_dict["time"],
                damage=effect_dict["damage"],
            )

        elif effect_dict["type"] == LevelEffectType.HEAL.value:
            return HealEffect(
                level=level,
                time=effect_dict["time"],
                heal=effect_dict["heal"],
            )

        elif effect_dict["type"] == LevelEffectType.BUFF.value:
            return BuffEffect(
                level=level,
                time=effect_dict["time"],
                stat=effect_dict["stat"],
                value=effect_dict["value"],
                duration=effect_dict["duration"],
            )

        else:
            raise ValueError(f"Unknown LevelEffectType: {effect_dict['type']}")


@dataclass(frozen=True, slots=True)
class DamageEffect(LevelEffect):
    """데미지 효과 데이터"""

    damage: float
    type: LevelEffectType = LevelEffectType.DAMAGE


@dataclass(frozen=True, slots=True)
class HealEffect(LevelEffect):
    """힐 효과 데이터"""

    heal: float
    type: LevelEffectType = LevelEffectType.HEAL


@dataclass(frozen=True, slots=True)
class BuffEffect(LevelEffect):
    """버프 효과 데이터"""

    stat: str
    value: float
    duration: float
    type: LevelEffectType = LevelEffectType.BUFF


@dataclass(frozen=True, slots=True)
class SkillDef:
    """스킬 데이터"""

    id: str
    server_id: str
    name: str
    cooltime: float
    levels: dict[int, list[LevelEffect]]

    @staticmethod
    def from_detail_dict(
        skill_id: str, server_id: str, detail: dict[str, Any]
    ) -> "SkillDef":
        """detail dict에서 SkillDef 생성"""

        levels: dict[int, list[LevelEffect]] = {
            int(level_str): [
                LevelEffect.from_dict(int(level_str), effect_dict)
                for effect_dict in effects_list
            ]
            for level_str, effects_list in detail["levels"].items()
        }

        return SkillDef(
            id=skill_id,
            server_id=server_id,
            name=detail["name"],
            cooltime=detail["cooltime"],
            levels=levels,
        )


@dataclass(frozen=True)
class SkillRegistry:
    """스킬 레지스트리"""

    _skills: dict[str, SkillDef]

    def get_all_skill_ids(self) -> list[str]:
        return list(self._skills.keys())

    def get(self, skill_id: str) -> SkillDef:
        return self._skills[skill_id]

    @classmethod
    def from_skill_data(
        cls, skill_data: dict[str, Any], server_id: str
    ) -> SkillRegistry:
        """skill_data에서 SkillRegistry 생성"""

        server_data: dict[str, Any] = skill_data[server_id]

        skill_ids: list[str] = server_data["skills"]
        details: dict[str, dict[str, Any]] = server_data["skill_details"]

        skills: dict[str, SkillDef] = {}
        for skill_id in skill_ids:
            detail: dict[str, Any] = details[skill_id]

            skill_def: SkillDef = SkillDef.from_detail_dict(
                skill_id=skill_id, server_id=server_id, detail=detail
            )
            skills[skill_id] = skill_def

        return cls(_skills=skills)
