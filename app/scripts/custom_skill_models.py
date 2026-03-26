from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CustomSkillImportError(ValueError):
    """커스텀 스킬 입력 검증 오류"""


def _require_text(data: dict[str, Any], key: str) -> str:
    """필수 문자열 필드 검증"""

    # 문자열 존재 여부 및 공백 입력 차단
    value: Any = data[key]
    text: str = str(value).strip()
    if not text:
        raise CustomSkillImportError(f"{key} must be a non-empty string")

    return text


def _require_float(data: dict[str, Any], key: str) -> float:
    """필수 숫자 필드 검증"""

    # 숫자 변환 실패를 입력 오류로 통일
    raw_value: Any = data[key]
    try:
        value: float = float(raw_value)

    except (TypeError, ValueError) as exc:
        raise CustomSkillImportError(f"{key} must be a number") from exc

    return value


class SkillEffectType(str, Enum):
    """스킬 효과 타입"""

    DAMAGE = "damage"
    HEAL = "heal"
    BUFF = "buff"


@dataclass(frozen=True, slots=True)
class DamageEffectPayload:
    """데미지 효과 입력 데이터"""

    time: float
    damage: float
    type: SkillEffectType = SkillEffectType.DAMAGE

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DamageEffectPayload":
        # 데미지 효과 필수 필드 검증
        time: float = _require_float(data, "time")
        damage: float = _require_float(data, "damage")

        return cls(time=time, damage=damage)

    def to_dict(self) -> dict[str, Any]:
        # 저장용 표준 딕셔너리 직렬화
        payload: dict[str, Any] = {
            "time": self.time,
            "type": self.type.value,
            "damage": self.damage,
        }
        return payload


@dataclass(frozen=True, slots=True)
class HealEffectPayload:
    """회복 효과 입력 데이터"""

    time: float
    heal: float
    type: SkillEffectType = SkillEffectType.HEAL

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealEffectPayload":
        # 회복 효과 필수 필드 검증
        time: float = _require_float(data, "time")
        heal: float = _require_float(data, "heal")

        return cls(time=time, heal=heal)

    def to_dict(self) -> dict[str, Any]:
        # 저장용 표준 딕셔너리 직렬화
        payload: dict[str, Any] = {
            "time": self.time,
            "type": self.type.value,
            "heal": self.heal,
        }
        return payload


@dataclass(frozen=True, slots=True)
class BuffEffectPayload:
    """버프 효과 입력 데이터"""

    time: float
    stat: str
    value: float
    duration: float
    type: SkillEffectType = SkillEffectType.BUFF

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuffEffectPayload":
        # 버프 효과 필수 필드 검증
        time: float = _require_float(data, "time")
        stat: str = _require_text(data, "stat")
        value: float = _require_float(data, "value")
        duration: float = _require_float(data, "duration")

        return cls(
            time=time,
            stat=stat,
            value=value,
            duration=duration,
        )

    def to_dict(self) -> dict[str, Any]:
        # 저장용 표준 딕셔너리 직렬화
        payload: dict[str, Any] = {
            "time": self.time,
            "type": self.type.value,
            "stat": self.stat,
            "value": self.value,
            "duration": self.duration,
        }
        return payload


SkillEffectPayload = DamageEffectPayload | HealEffectPayload | BuffEffectPayload


@dataclass(frozen=True, slots=True)
class CustomSkillDefinition:
    """커스텀 스킬 입력 데이터"""

    skill_id: str
    name: str
    cooltime: float
    levels: dict[int, tuple[SkillEffectPayload, ...]]

    @classmethod
    def from_dict(
        cls,
        skill_id: str,
        data: dict[str, Any],
    ) -> "CustomSkillDefinition":
        # 스킬 기본 필수 필드 검증
        name: str = _require_text(data, "name")
        cooltime: float = _require_float(data, "cooltime")

        # 레벨 효과 선택 필드 정규화
        raw_levels: Any = data["levels"] if "levels" in data else {}
        if raw_levels in ("", None):
            raw_levels = {}

        if not isinstance(raw_levels, dict):
            raise CustomSkillImportError("levels must be a dictionary when provided")

        levels: dict[int, tuple[SkillEffectPayload, ...]] = {}

        # 레벨별 효과 목록 정규화
        for raw_level, raw_effects in raw_levels.items():
            level: int = int(raw_level)

            if raw_effects in ("", None):
                raw_effects = []

            if not isinstance(raw_effects, list):
                raise CustomSkillImportError(
                    "level effects must be a list when provided"
                )

            effects: list[SkillEffectPayload] = []
            for raw_effect in raw_effects:
                if not isinstance(raw_effect, dict):
                    raise CustomSkillImportError("skill effect must be a dictionary")

                # 효과 타입 문자열 검증 및 enum 변환
                effect_type_text: str = _require_text(raw_effect, "type")
                try:
                    effect_type: SkillEffectType = SkillEffectType(effect_type_text)

                except ValueError as exc:
                    raise CustomSkillImportError(
                        f"unsupported skill effect type: {effect_type_text}"
                    ) from exc

                effect: SkillEffectPayload

                # 효과 타입별 세부 페이로드 파싱
                if effect_type == SkillEffectType.DAMAGE:
                    effect = DamageEffectPayload.from_dict(raw_effect)
                elif effect_type == SkillEffectType.HEAL:
                    effect = HealEffectPayload.from_dict(raw_effect)
                else:
                    effect = BuffEffectPayload.from_dict(raw_effect)

                effects.append(effect)

            levels[level] = tuple(effects)

        return cls(
            skill_id=skill_id,
            name=name,
            cooltime=cooltime,
            levels=levels,
        )

    def to_dict(self) -> dict[str, Any]:
        # 저장용 스킬 상세 데이터 직렬화
        level_payload: dict[str, list[dict[str, Any]]] = {}

        # 레벨 번호를 문자열 키로 변환하여 저장 형식 유지
        for level, effects in sorted(self.levels.items()):
            serialized_effects: list[dict[str, Any]] = []
            for effect in effects:
                serialized_effects.append(effect.to_dict())

            level_payload[str(level)] = serialized_effects

        payload: dict[str, Any] = {
            "name": self.name,
            "cooltime": self.cooltime,
            "levels": level_payload,
        }
        return payload


@dataclass(frozen=True, slots=True)
class CustomScrollDefinition:
    """커스텀 스크롤 입력 데이터"""

    scroll_id: str
    name: str
    skills: tuple[str, str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomScrollDefinition":
        # 스크롤 기본 필수 필드 검증
        scroll_id: str = _require_text(data, "scroll_id")
        name: str = _require_text(data, "name")
        raw_skills: Any = data["skills"]

        if not isinstance(raw_skills, list):
            raise CustomSkillImportError("scroll skills must be a list")

        if len(raw_skills) != 2:
            raise CustomSkillImportError("scroll skills must contain exactly 2 ids")

        # 연결 스킬 ID 공백 입력 차단
        first_skill_id: str = str(raw_skills[0]).strip()
        second_skill_id: str = str(raw_skills[1]).strip()
        if not first_skill_id or not second_skill_id:
            raise CustomSkillImportError("scroll skills must be non-empty strings")

        return cls(
            scroll_id=scroll_id,
            name=name,
            skills=(first_skill_id, second_skill_id),
        )

    def to_dict(self) -> dict[str, Any]:
        # 저장용 스크롤 데이터 직렬화
        payload: dict[str, Any] = {
            "scroll_id": self.scroll_id,
            "name": self.name,
            "skills": [self.skills[0], self.skills[1]],
        }
        return payload


@dataclass(frozen=True, slots=True)
class CustomSkillImport:
    """커스텀 스킬 묶음 입력 데이터"""

    skills: tuple[str, ...]
    scrolls: tuple[CustomScrollDefinition, ...]
    skill_details: dict[str, CustomSkillDefinition]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomSkillImport":
        # 최상위 필수 섹션 검증
        raw_skills: Any = data["skills"]
        raw_scrolls: Any = data["scrolls"]
        raw_skill_details: Any = data["skill_details"]

        if not isinstance(raw_skills, list):
            raise CustomSkillImportError("skills must be a list")

        if not isinstance(raw_scrolls, list):
            raise CustomSkillImportError("scrolls must be a list")

        if not isinstance(raw_skill_details, dict):
            raise CustomSkillImportError("skill_details must be a dictionary")

        skills: list[str] = []
        seen_skill_ids: set[str] = set()

        # 선언된 스킬 ID 목록 정규화 및 중복 차단
        for raw_skill_id in raw_skills:
            skill_id: str = str(raw_skill_id).strip()
            if not skill_id:
                raise CustomSkillImportError("skill id must be a non-empty string")

            if skill_id in seen_skill_ids:
                raise CustomSkillImportError(
                    f"duplicated skill id is not allowed: {skill_id}"
                )

            seen_skill_ids.add(skill_id)
            skills.append(skill_id)

        skill_details: dict[str, CustomSkillDefinition] = {}

        # 선언된 스킬 목록 기준 상세 데이터 정규화
        for skill_id in skills:
            if skill_id not in raw_skill_details:
                raise CustomSkillImportError(
                    f"skill_details entry is required for skill id: {skill_id}"
                )

            raw_detail: Any = raw_skill_details[skill_id]
            if not isinstance(raw_detail, dict):
                raise CustomSkillImportError("skill detail must be a dictionary")

            skill_detail: CustomSkillDefinition = CustomSkillDefinition.from_dict(
                skill_id=skill_id,
                data=raw_detail,
            )
            skill_details[skill_id] = skill_detail

        # 상세 데이터에 선언되지 않은 잉여 스킬 정의 차단
        for skill_id in raw_skill_details:
            if skill_id not in seen_skill_ids:
                raise CustomSkillImportError(
                    f"skill_details contains undefined skill id: {skill_id}"
                )

        scrolls: list[CustomScrollDefinition] = []
        seen_scroll_ids: set[str] = set()

        # 스크롤 정의 정규화 및 스킬 참조 무결성 검증
        for raw_scroll in raw_scrolls:
            if not isinstance(raw_scroll, dict):
                raise CustomSkillImportError("scroll must be a dictionary")

            scroll: CustomScrollDefinition = CustomScrollDefinition.from_dict(
                raw_scroll
            )
            if scroll.scroll_id in seen_scroll_ids:
                raise CustomSkillImportError(
                    f"duplicated scroll id is not allowed: {scroll.scroll_id}"
                )

            seen_scroll_ids.add(scroll.scroll_id)

            for skill_id in scroll.skills:
                if skill_id not in seen_skill_ids:
                    raise CustomSkillImportError(
                        f"scroll references undefined skill id: {skill_id}"
                    )

            scrolls.append(scroll)

        return cls(
            skills=tuple(skills),
            scrolls=tuple(scrolls),
            skill_details=skill_details,
        )

    def to_dict(self) -> dict[str, Any]:
        # 저장용 전체 입력 데이터 직렬화
        skill_details_payload: dict[str, dict[str, Any]] = {}

        # 선언 순서를 유지한 스킬 상세 딕셔너리 구성
        for skill_id in self.skills:
            skill_detail: CustomSkillDefinition = self.skill_details[skill_id]
            skill_details_payload[skill_id] = skill_detail.to_dict()

        payload: dict[str, Any] = {
            "skills": list(self.skills),
            "scrolls": [scroll.to_dict() for scroll in self.scrolls],
            "skill_details": skill_details_payload,
        }
        return payload
