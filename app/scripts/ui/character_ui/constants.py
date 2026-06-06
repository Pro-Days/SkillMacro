from __future__ import annotations

from dataclasses import dataclass

from app.scripts.calculator_models import STAT_SPECS, StatKey
from app.scripts.character_models import DisplayStandColumn, EquipmentSlot


@dataclass(frozen=True, slots=True)
class CharacterTabSpec:
    """캐릭터 입력 탭 표시 정의"""

    key: str
    label: str


CHARACTER_TABS: tuple[CharacterTabSpec, ...] = (
    CharacterTabSpec("title", "기본정보"),
    CharacterTabSpec("equip", "장비"),
    CharacterTabSpec("dist", "스탯·단전 분배"),
    CharacterTabSpec("shelf", "진열대"),
    CharacterTabSpec("talisman", "부적"),
    CharacterTabSpec("yeongdan", "영단"),
    CharacterTabSpec("hwan", "환"),
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

DISPLAY_STAND_COLUMNS: tuple[tuple[DisplayStandColumn, str], ...] = (
    (DisplayStandColumn.HELMET, "투구"),
    (DisplayStandColumn.ARMOR, "갑옷"),
    (DisplayStandColumn.BELT, "허리띠"),
    (DisplayStandColumn.SHOES, "신발"),
    (DisplayStandColumn.SET, "세트효과"),
)

# 스탯 선택 라벨 역조회와 콤보 표시 목록 (칭호·자유 스탯 공용)
STAT_LABEL_TO_KEY: dict[str, StatKey] = {
    label: stat_key for stat_key, label in STAT_SPECS.items()
}

STAT_CHOICE_LABELS: tuple[str, ...] = ("미설정", *STAT_SPECS.values())

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
