from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, cast

from app.scripts.custom_classes import Stats


@dataclass(slots=True)
class MacroSkills:
    active_skills: list[str] = field(default_factory=list)
    skill_keys: list[str] = field(default_factory=list)  # "2", "f9", ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroSkills":
        return cls(
            active_skills=list(data.get("active_skills", [])),
            skill_keys=list(data.get("skill_keys", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_skills": list(self.active_skills),
            "skill_keys": list(self.skill_keys),
        }

    def resolve_skill_keys(self, key_dict: dict[str, Any]) -> list[Any]:
        """키를 KeySpec으로 변환"""
        return [key_dict[k] for k in self.skill_keys]


@dataclass(slots=True)
class MacroSettings:
    server_id: str = ""
    delay: tuple[int, int] = (0, 0)  # [type, input]
    cooltime: tuple[int, int] = (0, 0)  # [type, input]
    start_key: tuple[int, str] = (0, "")  # [type, key_id]
    mouse_click_type: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroSettings":
        return cls(
            server_id=data.get("server_id", ""),
            delay=(
                int(data.get("delay", [0, 0])[0]),
                int(data.get("delay", [0, 0])[1]),
            ),
            cooltime=(
                int(data.get("cooltime", [0, 0])[0]),
                int(data.get("cooltime", [0, 0])[1]),
            ),
            start_key=(
                int(data.get("start_key", [0, ""])[0]),
                str(data.get("start_key", [0, ""])[1]),
            ),
            mouse_click_type=int(data.get("mouse_click_type", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_id": self.server_id,
            "delay": [self.delay[0], self.delay[1]],
            "cooltime": [self.cooltime[0], self.cooltime[1]],
            "start_key": [self.start_key[0], self.start_key[1]],
            "mouse_click_type": self.mouse_click_type,
        }

    def resolve_start_key(self, key_dict: dict[str, Any]) -> Any:
        """키를 KeySpec으로 변환"""
        return key_dict[self.start_key[1]]


@dataclass(slots=True)
class SkillUsageSetting:
    is_use_skill: bool = True
    is_use_sole: bool = False
    skill_priority: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillUsageSetting":
        return cls(
            is_use_skill=bool(data.get("is_use_skill", True)),
            is_use_sole=bool(data.get("is_use_sole", False)),
            skill_priority=int(data.get("skill_priority", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_use_skill": bool(self.is_use_skill),
            "is_use_sole": bool(self.is_use_sole),
            "skill_priority": int(self.skill_priority),
        }


class LinkUseType(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class LinkKeyType(str, Enum):
    ON = "on"
    OFF = "off"


@dataclass(slots=True)
class LinkSkill:
    """연계스킬 데이터 모델"""

    use_type: LinkUseType = LinkUseType.MANUAL
    key_type: LinkKeyType = LinkKeyType.OFF
    key: str = ""
    skills: list[str] = field(default_factory=list)
    num: int = -1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LinkSkill":
        # todo: snake case로 변경
        use_type_raw: str = str(data["useType"])
        key_type_raw: str = str(data["keyType"])

        return cls(
            use_type=LinkUseType(use_type_raw),
            key_type=LinkKeyType(key_type_raw),
            key=str(data["key"]),
            skills=list(data["skills"]),
            num=int(data["num"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "useType": self.use_type.value,
            "keyType": self.key_type.value,
            "key": self.key,
            "skills": self.skills.copy(),
            "num": self.num,
        }

    def set_manual(self) -> None:
        self.use_type = LinkUseType.MANUAL

    def set_auto(self) -> None:
        self.use_type = LinkUseType.AUTO

    def clear_key(self) -> None:
        self.key_type = LinkKeyType.OFF
        self.key = ""

    def set_key(self, key_id: str) -> None:
        self.key_type = LinkKeyType.ON
        self.key = key_id


@dataclass(slots=True)
class PresetInfo:
    stats: dict[str, int | float] = field(default_factory=dict)
    skill_levels: dict[str, int] = field(default_factory=dict)
    sim_details: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PresetInfo":
        stats_raw: dict[str, Any] = data.get("stats", {})
        levels_raw: dict[str, Any] = data.get("skill_levels", {})
        sim_raw: dict[str, Any] = data.get("sim_details", {})

        return cls(
            stats=dict(stats_raw),
            skill_levels={k: int(v) for k, v in levels_raw.items()},
            sim_details={k: int(v) for k, v in sim_raw.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stats": dict(self.stats),
            "skill_levels": dict(self.skill_levels),
            "sim_details": dict(self.sim_details),
        }

    def to_stats(self) -> "Stats":
        """스탯 dict를 Stats로 변환"""

        kwargs = cast(dict[str, Any], dict(self.stats))
        if "NAEGONG" in kwargs:
            kwargs["NAEGONG"] = int(kwargs["NAEGONG"])
        return Stats(**kwargs)

    @classmethod
    def from_stats(
        cls,
        stats: "Stats",
        skill_levels: dict[str, int] | None = None,
        sim_details: dict[str, int] | None = None,
    ) -> "PresetInfo":
        """스탯 Stats로부터 PresetInfo 생성"""

        return cls(
            stats=dict(vars(stats)),
            skill_levels=dict(skill_levels or {}),
            sim_details=dict(sim_details or {}),
        )


@dataclass(slots=True)
class MacroPreset:
    name: str = ""
    skills: MacroSkills = field(default_factory=MacroSkills)
    settings: MacroSettings = field(default_factory=MacroSettings)
    usage_settings: dict[str, SkillUsageSetting] = field(default_factory=dict)
    link_settings: list[LinkSkill] = field(default_factory=list)
    info: PresetInfo = field(default_factory=PresetInfo)

    # 모델 기본값(프리셋 단위 데이터)
    DEFAULT_NAME: ClassVar[str] = "스킬 매크로"
    DEFAULT_STATS: ClassVar[dict[str, int]] = {
        "ATK": 100,
        "DEF": 100,
        "PWR": 100,
        "STR": 100,
        "INT": 100,
        "RES": 10,
        "CRIT_RATE": 50,
        "CRIT_DMG": 50,
        "BOSS_DMG": 20,
        "ACC": 10,
        "DODGE": 10,
        "STATUS_RES": 10,
        "NAEGONG": 10,
        "HP": 2000,
        "ATK_SPD": 15,
        "POT_HEAL": 10,
        "LUK": 10,
        "EXP": 10,
    }
    DEFAULT_SIM_DETAILS: ClassVar[dict[str, int]] = {
        "NORMAL_NAEGONG": 10,
        "BOSS_NAEGONG": 10,
        "POTION_HEAL": 300,
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroPreset":
        usage_raw: dict[str, Any] = data["usage_settings"]

        return cls(
            name=data["name"],
            skills=MacroSkills.from_dict(data["skills"]),
            settings=MacroSettings.from_dict(data["settings"]),
            usage_settings={
                k: SkillUsageSetting.from_dict(v) for k, v in usage_raw.items()
            },
            link_settings=[
                LinkSkill.from_dict(ls) for ls in list(data["link_settings"])
            ],
            info=PresetInfo.from_dict(data["info"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "skills": self.skills.to_dict(),
            "settings": self.settings.to_dict(),
            "usage_settings": {k: v.to_dict() for k, v in self.usage_settings.items()},
            "link_settings": [ls.to_dict() for ls in self.link_settings],
            "info": self.info.to_dict(),
        }

    @classmethod
    def create_default(
        cls,
        server_id: str,
        skill_count: int,
        skills_all: list[str],
        default_delay: int,
        default_cooltime_reduction: int,
        default_start_key_id: str,
        name: str | None = None,
    ) -> "MacroPreset":
        """기본 프리셋을 생성한다.

        이 함수는 '프리셋 단위 데이터(탭별 데이터)'의 기본 구성을 MacroPreset 모델에
        모으기 위한 용도다. (IO/경로/저장은 data_manager에서 담당)
        """

        preset_name: str = cls.DEFAULT_NAME if name is None else name

        return cls(
            name=preset_name,
            skills=MacroSkills(
                active_skills=[""] * int(skill_count),
                skill_keys=[str(2 + i) for i in range(int(skill_count))],
            ),
            settings=MacroSettings(
                server_id=str(server_id),
                delay=(0, int(default_delay)),
                cooltime=(0, int(default_cooltime_reduction)),
                start_key=(0, str(default_start_key_id)),
                mouse_click_type=0,
            ),
            usage_settings={
                skill: SkillUsageSetting(
                    is_use_skill=True,
                    is_use_sole=False,
                    skill_priority=0,
                )
                for skill in list(skills_all)
            },
            link_settings=[],
            info=PresetInfo(
                stats=dict(cls.DEFAULT_STATS),
                # todo: 설정을 변경 한 스킬만 저장하도록 수정
                skill_levels={skill: 1 for skill in list(skills_all)},
                sim_details=dict(cls.DEFAULT_SIM_DETAILS),
            ),
        )


@dataclass(slots=True)
class MacroPresetFile:
    """json 파일을 저장하는 최상위 객체"""

    version: int = 1
    recent_preset: int = 0
    preset: list[MacroPreset] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroPresetFile":
        presets_raw: list[dict[str, Any]] = data.get("preset", [])
        return cls(
            version=int(data.get("version", 1)),
            recent_preset=int(data.get("recent_preset", 0)),
            preset=[MacroPreset.from_dict(p) for p in presets_raw],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": int(self.version),
            "recent_preset": int(self.recent_preset),
            "preset": [p.to_dict() for p in self.preset],
        }


# __all__ 설정
# 이 파일에서 외부로 노출할 클래스 및 함수 목록
__all__: list[str] = [
    "MacroPreset",
    "MacroPresetFile",
    "MacroSkills",
    "MacroSettings",
    "SkillUsageSetting",
    "LinkUseType",
    "LinkKeyType",
    "LinkSkill",
    "PresetInfo",
    "MacroPresetRepository",
]


class MacroPresetRepository:
    """매크로 프리셋 파일을 로드하고 저장하는 클래스"""

    def __init__(self, file_path: str) -> None:
        self.file_path: str = file_path

    def load(self) -> MacroPresetFile:
        with open(self.file_path, "r", encoding="UTF8") as f:
            obj: dict[str, Any] = json.load(f)

        return MacroPresetFile.from_dict(obj)

    def save(self, preset_file: MacroPresetFile) -> None:
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        with open(self.file_path, "w", encoding="UTF8") as f:
            json.dump(preset_file.to_dict(), f, ensure_ascii=False, indent=4)
