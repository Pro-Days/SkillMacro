from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class CustomSkillDefinition:
    """커스텀 스킬 입력 데이터"""

    skill_id: str
    name: str
    cooltime: float
    target_count: int
    levels: dict[int, float]

    @classmethod
    def from_dict(
        cls,
        skill_id: str,
        data: dict[str, Any],
    ) -> "CustomSkillDefinition":
        # 스킬 기본 필수 필드 검증
        name: str = _require_text(data, "name")
        cooltime: float = _require_float(data, "cooltime")
        target_count: int = data["target_count"]
        if type(target_count) is not int:
            raise CustomSkillImportError("target_count must be an integer")

        if target_count < 1:
            raise CustomSkillImportError("target_count must be greater than 0")

        # 레벨별 계수 선택 필드 정규화
        raw_levels: Any = data["levels"] if "levels" in data else {}
        if raw_levels in ("", None):
            raw_levels = {}

        if not isinstance(raw_levels, dict):
            raise CustomSkillImportError("levels must be a dictionary when provided")

        levels: dict[int, float] = {}

        # 레벨별 계수 숫자 정규화
        for raw_level, raw_level_detail in raw_levels.items():
            level: int = int(raw_level)
            try:
                levels[level] = float(raw_level_detail)

            except (TypeError, ValueError) as exc:
                raise CustomSkillImportError("level damage must be a number") from exc

        return cls(
            skill_id=skill_id,
            name=name,
            cooltime=cooltime,
            target_count=target_count,
            levels=levels,
        )

    def to_dict(self) -> dict[str, Any]:
        # 저장용 스킬 상세 데이터 직렬화
        level_payload: dict[str, float] = {}

        # 레벨 번호를 문자열 키로 변환하여 저장 형식 유지
        for level, damage in sorted(self.levels.items()):
            level_payload[str(level)] = damage

        payload: dict[str, Any] = {
            "name": self.name,
            "cooltime": self.cooltime,
            "target_count": self.target_count,
            "levels": level_payload,
        }
        return payload


@dataclass(frozen=True, slots=True)
class CustomScrollDefinition:
    """커스텀 무공비급 입력 데이터"""

    scroll_id: str
    name: str
    skills: tuple[str, str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomScrollDefinition":
        # 무공비급 기본 필수 필드 검증
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
        # 저장용 무공비급 데이터 직렬화
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

        # 무공비급 정의 정규화 및 스킬 참조 무결성 검증
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
