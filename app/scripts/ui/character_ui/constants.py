from __future__ import annotations

from dataclasses import dataclass

from app.scripts.calculator_models import StatKey
from app.scripts.character_models import (
    DisplayStandColumn,
    EquipmentKind,
    EquipmentSlot,
)


@dataclass(frozen=True, slots=True)
class CharacterTabSpec:
    """캐릭터 입력 탭 표시 정의"""

    key: str
    label: str
    color: str


CHARACTER_TABS: tuple[CharacterTabSpec, ...] = (
    CharacterTabSpec("title", "기본정보", "#e6e0f5"),
    CharacterTabSpec("equip", "장비", "#dcecfa"),
    CharacterTabSpec("dist", "스탯·단전 분배", "#d9f3e1"),
    CharacterTabSpec("shelf", "진열대", "#f8f5e8"),
    CharacterTabSpec("talisman", "부적", "#fde0ec"),
    CharacterTabSpec("yeongdan", "영단", "#e6e0f5"),
    CharacterTabSpec("hwan", "환", "#fef7d6"),
)

STAT_DISTRIBUTION_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("strength", "힘", "공격력 +1 · 치명타 공격력% +0.1"),
    ("dexterity", "민첩", "공격력% +0.3 · 치명타 확률% +0.05"),
    ("vitality", "생명력", "체력 +5 · 회피% +0.03 · 물약 회복량% +0.5"),
    ("luck", "행운", "경험치 획득량% +0.2 · 드랍률% +0.2"),
)

DANJEON_DISTRIBUTION_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("upper", "상단전", "체력% +3 · 저항% +1"),
    ("middle", "중단전", "공격력% +1"),
    ("lower", "하단전", "드랍률% +1.5 · 경험치 획득량% +0.5"),
)

DISPLAY_STAND_COLUMNS: tuple[tuple[DisplayStandColumn, str, str], ...] = (
    (DisplayStandColumn.HELMET, "투구", "경험치%"),
    (DisplayStandColumn.ARMOR, "갑옷", "공격력"),
    (DisplayStandColumn.BELT, "허리띠", "드랍률%"),
    (DisplayStandColumn.SHOES, "신발", "공격력%"),
    (DisplayStandColumn.SET, "세트효과", "힘·민·생·행%"),
)

DISPLAY_STAND_SUMMARY_LABELS: dict[DisplayStandColumn, str] = {
    DisplayStandColumn.HELMET: "경험치 획득량%",
    DisplayStandColumn.ARMOR: "공격력",
    DisplayStandColumn.BELT: "드랍률%",
    DisplayStandColumn.SHOES: "공격력%",
    DisplayStandColumn.SET: "세트효과(힘·민·생·행%)",
}

STAT_DISTRIBUTION_KEYS: dict[str, StatKey] = {
    "strength": StatKey.STR,
    "dexterity": StatKey.DEXTERITY,
    "vitality": StatKey.VITALITY,
    "luck": StatKey.LUCK,
}

GRADE_COLORS: dict[str, str] = {
    "일반": "#9b9690",
    "고급": "#2a9d99",
    "희귀": "#0075de",
    "영웅": "#dd5b00",
    "전설": "#7b3ff2",
}

EQUIPMENT_SLOT_LABELS: dict[EquipmentSlot, str] = {
    EquipmentSlot.WEAPON: "무기",
    EquipmentSlot.HELMET: "투구",
    EquipmentSlot.ARMOR: "갑옷",
    EquipmentSlot.BELT: "허리띠",
    EquipmentSlot.SHOES: "신발",
    EquipmentSlot.RING1: "반지",
    EquipmentSlot.RING2: "반지",
    EquipmentSlot.NECKLACE: "목걸이",
    EquipmentSlot.EARRING: "귀걸이",
}

EQUIPMENT_KIND_LABELS: dict[EquipmentKind, str] = {
    EquipmentKind.WEAPON: "무기",
    EquipmentKind.HELMET: "투구",
    EquipmentKind.ARMOR: "갑옷",
    EquipmentKind.BELT: "허리띠",
    EquipmentKind.SHOES: "신발",
    EquipmentKind.RING: "반지",
    EquipmentKind.NECKLACE: "목걸이",
    EquipmentKind.EARRING: "귀걸이",
}

EQUIPMENT_COL_LEFT: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.WEAPON,
    EquipmentSlot.HELMET,
    EquipmentSlot.ARMOR,
    EquipmentSlot.BELT,
    EquipmentSlot.SHOES,
)

EQUIPMENT_COL_RIGHT: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.RING1,
    EquipmentSlot.RING2,
    EquipmentSlot.NECKLACE,
    EquipmentSlot.EARRING,
)
