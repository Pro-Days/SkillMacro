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
    from app.scripts.registry.server_registry import ServerSpec
    from app.scripts.registry.skill_registry import ScrollDef


@dataclass(frozen=True, slots=True)
class EquippedSkillRef:
    """장착 스킬 인덱스 참조 모델"""

    scroll_index: int
    line_index: int

    @property
    def flat_index(self) -> int:
        """14칸 평탄 인덱스"""

        return (self.scroll_index * 2) + self.line_index


@dataclass(slots=True)
class MacroSkills:
    """매크로 스킬 데이터 모델"""

    # 장착된 스크롤 ID 목록 (빈 슬롯은 "")
    equipped_scrolls: list[str] = field(default_factory=list)

    # 하단 슬롯 배치 스킬 ID 목록 (빈 슬롯은 "")
    placed_skills: list[str] = field(default_factory=list)

    # 스킬 단축키 목록
    skill_keys: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroSkills":
        """딕셔너리로부터 MacroSkills 생성"""

        return cls(
            equipped_scrolls=data["equipped_scrolls"].copy(),
            placed_skills=data["placed_skills"].copy(),
            skill_keys=data["skill_keys"].copy(),
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "equipped_scrolls": self.equipped_scrolls.copy(),
            "placed_skills": self.placed_skills.copy(),
            "skill_keys": self.skill_keys.copy(),
        }

    def get_available_skill_ids(
        self,
        server_spec: "ServerSpec",
    ) -> list[str]:
        """현재 장착 스크롤 기준 제공 스킬 ID 목록 반환"""

        # 장착된 스크롤 순서를 유지한 채 2개 스킬씩 평탄화 구성
        available_skill_ids: list[str] = []

        for scroll_id in self.equipped_scrolls:
            # 빈 스크롤 슬롯은 제공 스킬이 없으므로 건너뛰기
            if not scroll_id:
                continue

            scroll_def: "ScrollDef" = server_spec.skill_registry.get_scroll(scroll_id)
            available_skill_ids.extend(scroll_def.skills)

        return available_skill_ids

    def get_placed_skill_id(
        self,
        skill_ref: EquippedSkillRef,
    ) -> str:
        """(하단) 해당 위치에 배치된 스킬 ID 반환"""

        # 하단 14칸 수동 배치 상태 직접 조회
        skill_id: str = self.placed_skills[skill_ref.flat_index]
        return skill_id

    def get_placed_skill_ids(self) -> list[str]:
        """하단 슬롯에 배치된 스킬 ID 목록 반환"""

        # 빈 슬롯 제외 후 실제 배치된 스킬만 압축 반환
        return [skill_id for skill_id in self.placed_skills if skill_id]

    def get_placed_skill_refs(
        self,
        server_spec: "ServerSpec",
    ) -> list[EquippedSkillRef]:
        """하단 슬롯에 배치된 스킬 참조 목록 반환"""

        refs: list[EquippedSkillRef] = []

        # 서버가 허용하는 전체 슬롯 범위를 순회하며 배치 위치 수집
        for scroll_index in range(server_spec.scroll_slot_count):
            for line_index in range(server_spec.skill_line_count):

                skill_ref: EquippedSkillRef = EquippedSkillRef(
                    scroll_index=scroll_index,
                    line_index=line_index,
                )

                # 빈 슬롯이 아닌 경우만 실제 배치 슬롯으로 취급
                if self.get_placed_skill_id(skill_ref):
                    refs.append(skill_ref)

        return refs

    def get_placed_skill_ref_map(
        self,
        server_spec: "ServerSpec",
    ) -> dict[str, EquippedSkillRef]:
        """배치된 스킬 ID -> 참조 매핑 반환"""

        skill_ref_map: dict[str, EquippedSkillRef] = {}

        # 현재 배치 상태를 기준으로 역참조 맵 구성
        for skill_ref in self.get_placed_skill_refs(server_spec):
            skill_id: str = self.get_placed_skill_id(skill_ref)

            if skill_id:
                skill_ref_map[skill_id] = skill_ref

        return skill_ref_map

    def get_available_skill_id(
        self,
        server_spec: "ServerSpec",
        skill_ref: EquippedSkillRef,
    ) -> str:
        """(상단) 해당 위치의 스크롤로부터 스킬 ID 반환"""

        scroll_id: str = self.equipped_scrolls[skill_ref.scroll_index]

        # 위치에 스크롤이 장착되지 않은 경우
        if not scroll_id:
            return ""

        scroll_def: "ScrollDef" = server_spec.skill_registry.get_scroll(scroll_id)
        return scroll_def.skills[skill_ref.line_index]



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

    # 스왑키
    custom_swap_key: str = config.specs.DEFAULT_SWAP_KEY.key_id
    use_custom_swap_key: bool = False

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
            custom_swap_key=data["custom_swap_key"],
            use_custom_swap_key=data["use_custom_swap_key"],
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
            "custom_swap_key": self.custom_swap_key,
            "use_custom_swap_key": self.use_custom_swap_key,
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
    # 스크롤 레벨 (key: scroll_id, value: level)
    scroll_levels: dict[str, int] = field(default_factory=dict)
    # 시뮬레이션 세부 정보
    sim_details: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresetInfo:
        """딕셔너리로부터 PresetInfo 생성"""

        return cls(
            stats=data["stats"].copy(),
            scroll_levels=data["scroll_levels"].copy(),
            sim_details=data["sim_details"].copy(),
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""

        return {
            "stats": self.stats.copy(),
            "scroll_levels": self.scroll_levels.copy(),
            "sim_details": self.sim_details.copy(),
        }

    @classmethod
    def from_stats(
        cls,
        stats: "Stats",
        scroll_levels: dict[str, int],
        sim_details: dict[str, int],
    ) -> "PresetInfo":
        """스탯 Stats로부터 PresetInfo 생성"""

        return cls(
            # Stats를 dict로 변환
            # todo: Stats에 to_dict() 메서드 추가
            stats=stats.to_dict(),
            scroll_levels=scroll_levels.copy(),
            sim_details=sim_details.copy(),
        )

    def get_scroll_level(self, scroll_id: str) -> int:
        """스크롤 ID 기준 레벨 반환"""

        # 스크롤이 레벨 저장의 단일 기준이므로 ID로 직접 조회
        level: int = self.scroll_levels[scroll_id]
        return level

    def set_scroll_level(self, scroll_id: str, level: int) -> None:
        """스크롤 ID 기준 레벨 저장"""

        self.scroll_levels[scroll_id] = level

    def get_skill_level(
        self,
        server_spec: "ServerSpec",
        skill_id: str,
    ) -> int:
        """스킬 ID 기준 소속 스크롤 레벨 반환"""

        # 스킬이 속한 스크롤을 현재 서버 정의에서 역탐색
        scroll_def: ScrollDef
        for scroll_def in server_spec.skill_registry.get_all_scroll_defs():
            if skill_id not in scroll_def.skills:
                continue

            # 스킬별 저장 대신 소속 스크롤 레벨을 단일 기준으로 사용
            return self.get_scroll_level(scroll_def.id)

        # 스크롤에 속하지 않는 스킬은 현 구조에서 레벨 저장 대상이 아님
        raise KeyError(f"skill_id does not belong to any scroll: {skill_id}")


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
        scroll_slot_count: int,
        scroll_ids: list[str],
        skills_all: list[str],
        default_delay: int,
        default_cooltime_reduction: int,
        default_start_key_id: str,
        default_swap_key_id: str,
    ) -> "MacroPreset":
        """기본값으로 MacroPreset 생성"""

        return cls(
            name=cls.DEFAULT_NAME,
            skills=MacroSkills(
                equipped_scrolls=[""] * scroll_slot_count,
                placed_skills=[""] * (scroll_slot_count * 2),
                skill_keys=[str(2 + i) for i in range(scroll_slot_count)],
            ),
            settings=MacroSettings(
                server_id=server_id,
                custom_delay=default_delay,
                use_custom_delay=False,
                custom_cooltime_reduction=default_cooltime_reduction,
                use_custom_cooltime_reduction=False,
                custom_start_key=default_start_key_id,
                use_custom_start_key=False,
                custom_swap_key=default_swap_key_id,
                use_custom_swap_key=False,
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
                # 현재 서버의 모든 스크롤 레벨 기본값 구성
                scroll_levels={scroll_id: 1 for scroll_id in scroll_ids.copy()},
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
