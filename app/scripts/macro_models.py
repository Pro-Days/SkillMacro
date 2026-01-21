from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, cast

from app.scripts.config import config
from app.scripts.custom_classes import Stats

if TYPE_CHECKING:
    from app.scripts.registry.key_registry import KeySpec


@dataclass(slots=True)
class MacroSkills:
    """매크로 스킬 데이터 모델"""

    # 장착된 스킬 ID 목록 (빈 슬롯은 "")
    equipped_skills: list[str] = field(default_factory=list)

    # 스킬 단축키 목록
    skill_keys: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroSkills":
        """딕셔너리로부터 MacroSkills 생성"""

        return cls(
            equipped_skills=data["equipped_skills"].copy(),
            skill_keys=data["skill_keys"].copy(),
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "equipped_skills": self.equipped_skills.copy(),
            "skill_keys": self.skill_keys.copy(),
        }


@dataclass(slots=True)
class MacroSettings:
    """매크로 설정 데이터 모델"""

    # 서버 ID
    server_id: str = ""

    # 딜레이
    custom_delay: int = config.specs.DELAY.default
    use_custom_delay: bool = False

    # 쿨타임 감소
    custom_cooltime_reduction: int = config.specs.COOLTIME_REDUCTION.default
    use_custom_cooltime_reduction: bool = False

    # 시작키
    custom_start_key: str = config.specs.DEFAULT_START_KEY.key_id
    use_custom_start_key: bool = False

    # 마우스 클릭 타입
    use_default_attack: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroSettings":
        """딕셔너리로부터 MacroSettings 생성"""

        return cls(
            server_id=data["server_id"],
            custom_delay=data["custom_delay"],
            use_custom_delay=data["use_custom_delay"],
            custom_cooltime_reduction=data["custom_cooltime_reduction"],
            use_custom_cooltime_reduction=data["use_custom_cooltime_reduction"],
            custom_start_key=data["custom_start_key"],
            use_custom_start_key=data["use_custom_start_key"],
            use_default_attack=data["use_default_attack"],
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "server_id": self.server_id,
            "custom_delay": self.custom_delay,
            "use_custom_delay": self.use_custom_delay,
            "custom_cooltime_reduction": self.custom_cooltime_reduction,
            "use_custom_cooltime_reduction": self.use_custom_cooltime_reduction,
            "custom_start_key": self.custom_start_key,
            "use_custom_start_key": self.use_custom_start_key,
            "use_default_attack": self.use_default_attack,
        }


@dataclass(slots=True)
class SkillUsageSetting:
    """스킬 사용 설정 데이터 모델"""

    use_skill: bool = True
    use_alone: bool = False
    priority: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillUsageSetting:
        """딕셔너리로부터 SkillUsageSetting 생성"""

        return cls(
            use_skill=data["use_skill"],
            use_alone=data["use_alone"],
            priority=data["priority"],
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "use_skill": self.use_skill,
            "use_alone": self.use_alone,
            "priority": self.priority,
        }

    def to_tuple(self) -> tuple[bool, bool, int]:
        """튜플로 변환"""

        return (self.use_skill, self.use_alone, self.priority)


class LinkUseType(str, Enum):
    """연계스킬 사용 타입"""

    AUTO = "auto"
    MANUAL = "manual"


class LinkKeyType(str, Enum):
    """연계스킬 키 설정 여부"""

    ON = "on"
    OFF = "off"


@dataclass(slots=True)
class LinkSkill:
    """연계스킬 데이터 모델"""

    # 연계스킬 사용 타입
    use_type: LinkUseType = LinkUseType.MANUAL
    # 연계스킬 키 설정 여부
    key_type: LinkKeyType = LinkKeyType.OFF
    # 연계스킬 키
    key: str | None = None
    # 연계스킬 스킬 ID 목록
    skills: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LinkSkill:
        """딕셔너리로부터 LinkSkill 생성"""

        # todo: snake case로 변경
        return cls(
            use_type=LinkUseType(data["useType"]),
            key_type=LinkKeyType(data["keyType"]),
            key=data["key"] if data["key"] is not None else None,
            skills=data["skills"].copy(),
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "useType": self.use_type.value,
            "keyType": self.key_type.value,
            "key": self.key,
            "skills": self.skills.copy(),
        }

    def set_manual(self) -> None:
        """연계스킬 수동 사용 설정"""

        self.use_type = LinkUseType.MANUAL

    def set_auto(self) -> None:
        """연계스킬 자동 사용 설정"""

        self.use_type = LinkUseType.AUTO

    def clear_key(self) -> None:
        """연계스킬 키 해제"""

        self.key_type = LinkKeyType.OFF
        self.key = None

    def set_key(self, key_id: str) -> None:
        """연계스킬 키 설정"""

        self.key_type = LinkKeyType.ON
        self.key = key_id


@dataclass(slots=True)
class PresetInfo:
    """프리셋 정보 데이터 모델"""

    # 스탯
    stats: dict[str, int | float] = field(default_factory=dict)
    # 스킬 레벨 (key: skill_id, value: level)
    skill_levels: dict[str, int] = field(default_factory=dict)
    # 시뮬레이션 세부 정보
    sim_details: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresetInfo:
        """딕셔너리로부터 PresetInfo 생성"""

        return cls(
            stats=data["stats"].copy(),
            skill_levels=data["skill_levels"].copy(),
            sim_details=data["sim_details"].copy(),
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "stats": self.stats.copy(),
            "skill_levels": self.skill_levels.copy(),
            "sim_details": self.sim_details.copy(),
        }

    @classmethod
    def from_stats(
        cls,
        stats: "Stats",
        skill_levels: dict[str, int],
        sim_details: dict[str, int],
    ) -> "PresetInfo":
        """스탯 Stats로부터 PresetInfo 생성"""

        return cls(
            # Stats를 dict로 변환
            # todo: Stats에 to_dict() 메서드 추가
            stats=stats.to_dict(),
            skill_levels=skill_levels.copy(),
            sim_details=sim_details.copy(),
        )


@dataclass(slots=True)
class MacroPreset:
    """매크로 프리셋 데이터 모델"""

    # 프리셋 이름
    name: str = ""
    # 스킬 목록
    skills: MacroSkills = field(default_factory=MacroSkills)
    # 매크로 설정
    settings: MacroSettings = field(default_factory=MacroSettings)
    # 스킬 사용 설정
    usage_settings: dict[str, SkillUsageSetting] = field(default_factory=dict)
    # 연계스킬 목록
    link_skills: list[LinkSkill] = field(default_factory=list)
    # 프리셋 정보
    info: PresetInfo = field(default_factory=PresetInfo)

    # 모델 기본값
    DEFAULT_NAME: ClassVar[str] = "스킬 매크로"
    DEFAULT_STATS: ClassVar[dict[str, int | float]] = {
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
    def from_dict(cls, data: dict[str, Any]) -> MacroPreset:
        """딕셔너리로부터 MacroPreset 생성"""

        preset: "MacroPreset" = cls(
            name=data["name"],
            skills=MacroSkills.from_dict(data["skills"]),
            settings=MacroSettings.from_dict(data["settings"]),
            usage_settings={
                k: SkillUsageSetting.from_dict(v)
                for k, v in data["usage_settings"].items()
            },
            link_skills=[LinkSkill.from_dict(ls) for ls in list(data["link_skills"])],
            info=PresetInfo.from_dict(data["info"]),
        )

        return preset

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "name": self.name,
            "skills": self.skills.to_dict(),
            "settings": self.settings.to_dict(),
            "usage_settings": {k: v.to_dict() for k, v in self.usage_settings.items()},
            "link_skills": [ls.to_dict() for ls in self.link_skills],
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
    ) -> "MacroPreset":
        """기본값으로 MacroPreset 생성"""

        return cls(
            name=cls.DEFAULT_NAME,
            skills=MacroSkills(
                equipped_skills=[""] * skill_count,
                skill_keys=[str(2 + i) for i in range(skill_count)],
            ),
            settings=MacroSettings(
                server_id=server_id,
                custom_delay=default_delay,
                use_custom_delay=False,
                custom_cooltime_reduction=default_cooltime_reduction,
                use_custom_cooltime_reduction=False,
                custom_start_key=default_start_key_id,
                use_custom_start_key=False,
                use_default_attack=False,
            ),
            usage_settings={
                skill_id: SkillUsageSetting(
                    use_skill=True,
                    use_alone=False,
                    priority=0,
                )
                for skill_id in skills_all.copy()
            },
            link_skills=[],
            info=PresetInfo(
                stats=cls.DEFAULT_STATS.copy(),
                # todo: 설정을 변경 한 스킬만 저장하도록 수정
                skill_levels={skill_id: 1 for skill_id in skills_all.copy()},
                sim_details=cls.DEFAULT_SIM_DETAILS.copy(),
            ),
        )


@dataclass(slots=True)
class MacroPresetFile:
    """json 파일을 저장하는 최상위 객체"""

    version: int = 1
    recent_preset: int = 0
    preset: list[MacroPreset] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MacroPresetFile:
        """딕셔너리로부터 MacroPresetFile 생성"""

        return cls(
            version=data["version"],
            recent_preset=data["recent_preset"],
            preset=[MacroPreset.from_dict(p) for p in data["preset"]],
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "version": self.version,
            "recent_preset": self.recent_preset,
            "preset": [p.to_dict() for p in self.preset],
        }


class MacroPresetRepository:
    """매크로 프리셋 파일을 로드하고 저장하는 클래스"""

    def __init__(self, file_path: str) -> None:
        self.file_path: str = file_path

    def load(self) -> MacroPresetFile:
        """매크로 프리셋 파일 로드"""

        with open(self.file_path, "r", encoding="UTF8") as f:
            obj: dict[str, Any] = json.load(f)

        return MacroPresetFile.from_dict(obj)

    def save(self, preset_file: MacroPresetFile) -> None:
        """매크로 프리셋 파일 저장"""

        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        with open(self.file_path, "w", encoding="UTF8") as f:
            json.dump(preset_file.to_dict(), f, ensure_ascii=False, indent=4)
