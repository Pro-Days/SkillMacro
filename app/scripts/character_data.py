from __future__ import annotations

from dataclasses import dataclass

from app.scripts.calculator_models import StatKey
from app.scripts.character_models import (
    AdditionalOption,
    DisplayStand,
    DisplayStandColumn,
    Elixir,
    EquipmentGrade,
    EquipmentSlot,
    Pill,
    PotentialOption,
    ScrollTier,
)


@dataclass(frozen=True, slots=True)
class ValueRange:
    """수치 입력 허용 범위"""

    minimum: float
    maximum: float


@dataclass(frozen=True, slots=True)
class EquipmentItemSpec:
    """장비 아이템 기본 스펙"""

    name: str
    slots: tuple[EquipmentSlot, ...]
    level: int
    tier: int
    grade_stats: dict[EquipmentGrade | None, dict[StatKey, float]]
    armor_stat_values: dict[EquipmentGrade, float]


@dataclass(frozen=True, slots=True)
class OptionSpec:
    """장비 옵션 스펙"""

    stat_key: StatKey
    value_range: ValueRange


@dataclass(frozen=True, slots=True)
class DisplayStandSpec:
    """진열대 행 스펙"""

    stand: DisplayStand
    name: str


@dataclass(frozen=True, slots=True)
class ConsumableSpec:
    """영단/환 효과 스펙"""

    name: str
    effects: dict[StatKey, float]


ARMOR_EQUIPMENT_SLOTS: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.HELMET,
    EquipmentSlot.ARMOR,
    EquipmentSlot.BELT,
    EquipmentSlot.SHOES,
)
POTENTIAL_EQUIPMENT_SLOTS: tuple[EquipmentSlot, ...] = ARMOR_EQUIPMENT_SLOTS
FREE_BASE_STAT_EQUIPMENT_SLOTS: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.RING1,
    EquipmentSlot.RING2,
    EquipmentSlot.EARRING,
)
RING_EQUIPMENT_SLOTS: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.RING1,
    EquipmentSlot.RING2,
)


ARMOR_SLOT_STAT_KEYS: dict[EquipmentSlot, StatKey] = {
    EquipmentSlot.HELMET: StatKey.LUCK,
    EquipmentSlot.ARMOR: StatKey.STR,
    EquipmentSlot.BELT: StatKey.VITALITY,
    EquipmentSlot.SHOES: StatKey.DEXTERITY,
}


EQUIPMENT_REFORGE_STAT_KEYS: dict[EquipmentSlot, tuple[StatKey, ...]] = {
    EquipmentSlot.HELMET: (
        StatKey.LUCK,
        StatKey.LUCK_PERCENT,
        StatKey.EXP_PERCENT,
    ),
    EquipmentSlot.ARMOR: (
        StatKey.STR,
        StatKey.STR_PERCENT,
        StatKey.EXP_PERCENT,
    ),
    EquipmentSlot.BELT: (
        StatKey.VITALITY,
        StatKey.VITALITY_PERCENT,
        StatKey.EXP_PERCENT,
    ),
    EquipmentSlot.SHOES: (
        StatKey.DEXTERITY,
        StatKey.DEXTERITY_PERCENT,
        StatKey.EXP_PERCENT,
    ),
    EquipmentSlot.WEAPON: (
        StatKey.ATTACK,
        StatKey.ATTACK_PERCENT,
        StatKey.SKILL_DAMAGE_PERCENT,
    ),
    EquipmentSlot.RING1: (),
    EquipmentSlot.RING2: (),
    EquipmentSlot.NECKLACE: (),
    EquipmentSlot.EARRING: (),
}


NECKLACE_REFORGE_STAT_KEYS: dict[str, tuple[StatKey, ...]] = {
    "적옥목걸이": (
        StatKey.VITALITY,
        StatKey.VITALITY_PERCENT,
        StatKey.SKILL_DAMAGE_PERCENT,
        StatKey.FINAL_ATTACK_PERCENT,
    ),
    "청옥목걸이": (
        StatKey.STR,
        StatKey.STR_PERCENT,
        StatKey.SKILL_DAMAGE_PERCENT,
        StatKey.FINAL_ATTACK_PERCENT,
    ),
    "녹옥목걸이": (
        StatKey.LUCK,
        StatKey.LUCK_PERCENT,
        StatKey.SKILL_DAMAGE_PERCENT,
        StatKey.FINAL_ATTACK_PERCENT,
    ),
}


def _stats(*pairs: tuple[StatKey, float]) -> dict[StatKey, float]:
    """스탯 맵 리터럴 구성"""

    return {stat_key: value for stat_key, value in pairs}


def _make_weapon_spec(
    level: int,
    tier: int,
    name: str,
    basic_stats: dict[StatKey, float],
    radiant_stats: dict[StatKey, float],
) -> EquipmentItemSpec:
    """무기 아이템 스펙 구성"""

    return EquipmentItemSpec(
        name=name,
        slots=(EquipmentSlot.WEAPON,),
        level=level,
        tier=tier,
        grade_stats={
            EquipmentGrade.BASIC: basic_stats,
            EquipmentGrade.RADIANT: radiant_stats,
        },
        armor_stat_values={},
    )


def _make_armor_spec(
    level: int,
    tier: int,
    name: str,
    basic_armor_stat: float,
    basic_stats: dict[StatKey, float],
    radiant_armor_stat: float,
    radiant_stats: dict[StatKey, float],
) -> EquipmentItemSpec:
    """방어구 공용 아이템 스펙 구성"""

    return EquipmentItemSpec(
        name=name,
        slots=ARMOR_EQUIPMENT_SLOTS,
        level=level,
        tier=tier,
        grade_stats={
            EquipmentGrade.BASIC: basic_stats,
            EquipmentGrade.RADIANT: radiant_stats,
        },
        armor_stat_values={
            EquipmentGrade.BASIC: basic_armor_stat,
            EquipmentGrade.RADIANT: radiant_armor_stat,
        },
    )


def _make_necklace_spec(name: str) -> EquipmentItemSpec:
    """목걸이 아이템 스펙 구성"""

    return EquipmentItemSpec(
        name=name,
        slots=(EquipmentSlot.NECKLACE,),
        level=100,
        tier=1,
        grade_stats={None: {}},
        armor_stat_values={},
    )


WEAPON_ITEM_SPECS: tuple[EquipmentItemSpec, ...] = (
    _make_weapon_spec(
        0,
        1,
        "참도",
        _stats((StatKey.ATTACK, 30.0)),
        _stats((StatKey.ATTACK, 33.0)),
    ),
    _make_weapon_spec(
        20,
        1,
        "곡태도",
        _stats((StatKey.ATTACK, 40.0)),
        _stats(
            (StatKey.ATTACK, 44.0),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.1),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        20,
        2,
        "자월검",
        _stats((StatKey.ATTACK, 35.0)),
        _stats(
            (StatKey.ATTACK, 38.0),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.0),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        50,
        1,
        "흑귀도",
        _stats((StatKey.ATTACK, 76.0), (StatKey.FINAL_ATTACK_PERCENT, 1.8)),
        _stats(
            (StatKey.ATTACK, 83.0),
            (StatKey.FINAL_ATTACK_PERCENT, 1.8),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.6),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        50,
        2,
        "사월검",
        _stats((StatKey.ATTACK, 72.0), (StatKey.FINAL_ATTACK_PERCENT, 1.6)),
        _stats(
            (StatKey.ATTACK, 79.0),
            (StatKey.FINAL_ATTACK_PERCENT, 1.6),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.5),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        50,
        3,
        "녹태도",
        _stats((StatKey.ATTACK, 68.0), (StatKey.FINAL_ATTACK_PERCENT, 1.4)),
        _stats(
            (StatKey.ATTACK, 74.0),
            (StatKey.FINAL_ATTACK_PERCENT, 1.4),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.4),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        50,
        4,
        "사보도",
        _stats((StatKey.ATTACK, 64.0), (StatKey.FINAL_ATTACK_PERCENT, 1.2)),
        _stats(
            (StatKey.ATTACK, 70.0),
            (StatKey.FINAL_ATTACK_PERCENT, 1.2),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.3),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        50,
        5,
        "연화도",
        _stats((StatKey.ATTACK, 60.0), (StatKey.FINAL_ATTACK_PERCENT, 1.0)),
        _stats(
            (StatKey.ATTACK, 66.0),
            (StatKey.FINAL_ATTACK_PERCENT, 1.0),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.2),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        80,
        1,
        "홍련검",
        _stats((StatKey.ATTACK, 116.0), (StatKey.FINAL_ATTACK_PERCENT, 2.8)),
        _stats(
            (StatKey.ATTACK, 127.0),
            (StatKey.FINAL_ATTACK_PERCENT, 2.8),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.1),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        80,
        2,
        "청월검",
        _stats((StatKey.ATTACK, 112.0), (StatKey.FINAL_ATTACK_PERCENT, 2.6)),
        _stats(
            (StatKey.ATTACK, 123.0),
            (StatKey.FINAL_ATTACK_PERCENT, 2.6),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.0),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        80,
        3,
        "흑월검",
        _stats((StatKey.ATTACK, 108.0), (StatKey.FINAL_ATTACK_PERCENT, 2.4)),
        _stats(
            (StatKey.ATTACK, 118.0),
            (StatKey.FINAL_ATTACK_PERCENT, 2.4),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.9),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        80,
        4,
        "화연도",
        _stats((StatKey.ATTACK, 104.0), (StatKey.FINAL_ATTACK_PERCENT, 2.2)),
        _stats(
            (StatKey.ATTACK, 114.0),
            (StatKey.FINAL_ATTACK_PERCENT, 2.2),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.8),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        80,
        5,
        "화염사검",
        _stats((StatKey.ATTACK, 100.0), (StatKey.FINAL_ATTACK_PERCENT, 2.0)),
        _stats(
            (StatKey.ATTACK, 110.0),
            (StatKey.FINAL_ATTACK_PERCENT, 2.0),
            (StatKey.SKILL_DAMAGE_PERCENT, 1.7),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        110,
        1,
        "황금도",
        _stats((StatKey.ATTACK, 146.0), (StatKey.FINAL_ATTACK_PERCENT, 3.8)),
        _stats(
            (StatKey.ATTACK, 160.0),
            (StatKey.FINAL_ATTACK_PERCENT, 3.8),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.6),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        110,
        2,
        "은룡사검",
        _stats((StatKey.ATTACK, 142.0), (StatKey.FINAL_ATTACK_PERCENT, 3.6)),
        _stats(
            (StatKey.ATTACK, 156.0),
            (StatKey.FINAL_ATTACK_PERCENT, 3.6),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.5),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        110,
        3,
        "무네치카",
        _stats((StatKey.ATTACK, 138.0), (StatKey.FINAL_ATTACK_PERCENT, 3.4)),
        _stats(
            (StatKey.ATTACK, 151.0),
            (StatKey.FINAL_ATTACK_PERCENT, 3.4),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.4),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        110,
        4,
        "무라마사",
        _stats((StatKey.ATTACK, 134.0), (StatKey.FINAL_ATTACK_PERCENT, 3.2)),
        _stats(
            (StatKey.ATTACK, 147.0),
            (StatKey.FINAL_ATTACK_PERCENT, 3.2),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.3),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        110,
        5,
        "백혈도",
        _stats((StatKey.ATTACK, 130.0), (StatKey.FINAL_ATTACK_PERCENT, 3.0)),
        _stats(
            (StatKey.ATTACK, 143.0),
            (StatKey.FINAL_ATTACK_PERCENT, 3.0),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.2),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        150,
        1,
        "이매귀도",
        _stats((StatKey.ATTACK, 176.0), (StatKey.FINAL_ATTACK_PERCENT, 4.8)),
        _stats(
            (StatKey.ATTACK, 193.0),
            (StatKey.FINAL_ATTACK_PERCENT, 4.8),
            (StatKey.SKILL_DAMAGE_PERCENT, 3.1),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        150,
        2,
        "빙각룡",
        _stats((StatKey.ATTACK, 172.0), (StatKey.FINAL_ATTACK_PERCENT, 4.6)),
        _stats(
            (StatKey.ATTACK, 189.0),
            (StatKey.FINAL_ATTACK_PERCENT, 4.6),
            (StatKey.SKILL_DAMAGE_PERCENT, 3.0),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        150,
        3,
        "백룡검",
        _stats((StatKey.ATTACK, 168.0), (StatKey.FINAL_ATTACK_PERCENT, 4.4)),
        _stats(
            (StatKey.ATTACK, 184.0),
            (StatKey.FINAL_ATTACK_PERCENT, 4.4),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.9),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        150,
        4,
        "창룡검",
        _stats((StatKey.ATTACK, 164.0), (StatKey.FINAL_ATTACK_PERCENT, 4.2)),
        _stats(
            (StatKey.ATTACK, 180.0),
            (StatKey.FINAL_ATTACK_PERCENT, 4.2),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.8),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        150,
        5,
        "귀매도",
        _stats((StatKey.ATTACK, 160.0), (StatKey.FINAL_ATTACK_PERCENT, 4.0)),
        _stats(
            (StatKey.ATTACK, 176.0),
            (StatKey.FINAL_ATTACK_PERCENT, 4.0),
            (StatKey.SKILL_DAMAGE_PERCENT, 2.7),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        180,
        1,
        "화염마검",
        _stats((StatKey.ATTACK, 222.0), (StatKey.FINAL_ATTACK_PERCENT, 5.8)),
        _stats(
            (StatKey.ATTACK, 244.0),
            (StatKey.FINAL_ATTACK_PERCENT, 5.8),
            (StatKey.SKILL_DAMAGE_PERCENT, 3.6),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        180,
        2,
        "청산소천도",
        _stats((StatKey.ATTACK, 218.0), (StatKey.FINAL_ATTACK_PERCENT, 5.6)),
        _stats(
            (StatKey.ATTACK, 239.0),
            (StatKey.FINAL_ATTACK_PERCENT, 5.6),
            (StatKey.SKILL_DAMAGE_PERCENT, 3.5),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        180,
        3,
        "흑왕대검",
        _stats((StatKey.ATTACK, 214.0), (StatKey.FINAL_ATTACK_PERCENT, 5.4)),
        _stats(
            (StatKey.ATTACK, 235.0),
            (StatKey.FINAL_ATTACK_PERCENT, 5.4),
            (StatKey.SKILL_DAMAGE_PERCENT, 3.4),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        180,
        4,
        "황룡대도",
        _stats((StatKey.ATTACK, 210.0), (StatKey.FINAL_ATTACK_PERCENT, 5.2)),
        _stats(
            (StatKey.ATTACK, 231.0),
            (StatKey.FINAL_ATTACK_PERCENT, 5.2),
            (StatKey.SKILL_DAMAGE_PERCENT, 3.3),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
    _make_weapon_spec(
        180,
        5,
        "절영귀도",
        _stats((StatKey.ATTACK, 180.0), (StatKey.FINAL_ATTACK_PERCENT, 5.0)),
        _stats(
            (StatKey.ATTACK, 198.0),
            (StatKey.FINAL_ATTACK_PERCENT, 5.0),
            (StatKey.SKILL_DAMAGE_PERCENT, 3.2),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
    ),
)


ARMOR_ITEM_SPECS: tuple[EquipmentItemSpec, ...] = (
    _make_armor_spec(
        0,
        1,
        "가죽",
        2.0,
        _stats((StatKey.HP, 5.0)),
        6.0,
        _stats(
            (StatKey.ATTACK, 1.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 15.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        20,
        1,
        "장인",
        4.0,
        _stats((StatKey.HP, 10.0)),
        8.0,
        _stats(
            (StatKey.ATTACK, 2.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 20.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        50,
        1,
        "광설",
        14.0,
        _stats((StatKey.ATTACK, 3.0), (StatKey.HP, 35.0)),
        18.0,
        _stats(
            (StatKey.ATTACK, 4.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 45.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        50,
        2,
        "백비",
        12.0,
        _stats((StatKey.ATTACK, 2.0), (StatKey.HP, 30.0)),
        16.0,
        _stats(
            (StatKey.ATTACK, 3.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 40.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        50,
        3,
        "광전",
        10.0,
        _stats((StatKey.ATTACK, 2.0), (StatKey.HP, 25.0)),
        14.0,
        _stats(
            (StatKey.ATTACK, 3.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 35.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        50,
        4,
        "투해",
        8.0,
        _stats((StatKey.ATTACK, 1.0), (StatKey.HP, 20.0)),
        12.0,
        _stats(
            (StatKey.ATTACK, 2.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 30.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        50,
        5,
        "동군",
        6.0,
        _stats((StatKey.ATTACK, 1.0), (StatKey.HP, 15.0)),
        10.0,
        _stats(
            (StatKey.ATTACK, 2.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 25.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        80,
        1,
        "금군",
        24.0,
        _stats((StatKey.ATTACK, 6.0), (StatKey.HP, 60.0)),
        28.0,
        _stats(
            (StatKey.ATTACK, 7.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 70.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        80,
        2,
        "장현",
        22.0,
        _stats((StatKey.ATTACK, 5.0), (StatKey.HP, 55.0)),
        26.0,
        _stats(
            (StatKey.ATTACK, 6.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 65.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        80,
        3,
        "청군",
        20.0,
        _stats((StatKey.ATTACK, 5.0), (StatKey.HP, 50.0)),
        24.0,
        _stats(
            (StatKey.ATTACK, 6.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 60.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        80,
        4,
        "백현",
        18.0,
        _stats((StatKey.ATTACK, 4.0), (StatKey.HP, 45.0)),
        22.0,
        _stats(
            (StatKey.ATTACK, 5.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 55.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        80,
        5,
        "호군",
        16.0,
        _stats((StatKey.ATTACK, 4.0), (StatKey.HP, 40.0)),
        20.0,
        _stats(
            (StatKey.ATTACK, 5.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 50.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        110,
        1,
        "염화",
        34.0,
        _stats((StatKey.ATTACK, 9.0), (StatKey.HP, 85.0)),
        38.0,
        _stats(
            (StatKey.ATTACK, 10.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 95.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        110,
        2,
        "금청",
        32.0,
        _stats((StatKey.ATTACK, 8.0), (StatKey.HP, 80.0)),
        36.0,
        _stats(
            (StatKey.ATTACK, 9.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 90.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        110,
        3,
        "금투",
        30.0,
        _stats((StatKey.ATTACK, 8.0), (StatKey.HP, 75.0)),
        34.0,
        _stats(
            (StatKey.ATTACK, 9.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 85.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        110,
        4,
        "녹귀",
        28.0,
        _stats((StatKey.ATTACK, 7.0), (StatKey.HP, 70.0)),
        32.0,
        _stats(
            (StatKey.ATTACK, 8.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 80.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        110,
        5,
        "진무",
        26.0,
        _stats((StatKey.ATTACK, 7.0), (StatKey.HP, 65.0)),
        30.0,
        _stats(
            (StatKey.ATTACK, 8.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 75.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        150,
        1,
        "산령",
        44.0,
        _stats((StatKey.ATTACK, 12.0), (StatKey.HP, 110.0)),
        48.0,
        _stats(
            (StatKey.ATTACK, 13.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 120.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        150,
        2,
        "진군",
        42.0,
        _stats((StatKey.ATTACK, 11.0), (StatKey.HP, 105.0)),
        46.0,
        _stats(
            (StatKey.ATTACK, 12.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 115.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        150,
        3,
        "투령",
        40.0,
        _stats((StatKey.ATTACK, 11.0), (StatKey.HP, 100.0)),
        44.0,
        _stats(
            (StatKey.ATTACK, 12.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 110.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        150,
        4,
        "적령",
        38.0,
        _stats((StatKey.ATTACK, 10.0), (StatKey.HP, 95.0)),
        42.0,
        _stats(
            (StatKey.ATTACK, 11.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 105.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        150,
        5,
        "괴록",
        36.0,
        _stats((StatKey.ATTACK, 10.0), (StatKey.HP, 90.0)),
        40.0,
        _stats(
            (StatKey.ATTACK, 11.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 100.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        180,
        1,
        "금성",
        54.0,
        _stats((StatKey.ATTACK, 15.0), (StatKey.HP, 135.0)),
        58.0,
        _stats(
            (StatKey.ATTACK, 16.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 145.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        180,
        2,
        "괴황",
        52.0,
        _stats((StatKey.ATTACK, 14.0), (StatKey.HP, 130.0)),
        56.0,
        _stats(
            (StatKey.ATTACK, 15.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 140.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        180,
        3,
        "청귀",
        50.0,
        _stats((StatKey.ATTACK, 14.0), (StatKey.HP, 125.0)),
        54.0,
        _stats(
            (StatKey.ATTACK, 15.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 135.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        180,
        4,
        "천군",
        48.0,
        _stats((StatKey.ATTACK, 13.0), (StatKey.HP, 120.0)),
        52.0,
        _stats(
            (StatKey.ATTACK, 14.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 130.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
    _make_armor_spec(
        180,
        5,
        "광룡",
        46.0,
        _stats((StatKey.ATTACK, 13.0), (StatKey.HP, 115.0)),
        50.0,
        _stats(
            (StatKey.ATTACK, 14.0),
            (StatKey.ATTACK_PERCENT, 1.0),
            (StatKey.HP, 125.0),
            (StatKey.HP_PERCENT, 2.0),
        ),
    ),
)


NECKLACE_ITEM_SPECS: tuple[EquipmentItemSpec, ...] = (
    _make_necklace_spec("적옥목걸이"),
    _make_necklace_spec("청옥목걸이"),
    _make_necklace_spec("녹옥목걸이"),
)


EQUIPMENT_ITEM_SPECS: tuple[EquipmentItemSpec, ...] = (
        *WEAPON_ITEM_SPECS,
        *ARMOR_ITEM_SPECS,
        *NECKLACE_ITEM_SPECS,
)


POTENTIAL_OPTION_SPECS: dict[PotentialOption, OptionSpec] = {
    PotentialOption.STR_PERCENT: OptionSpec(StatKey.STR_PERCENT, ValueRange(1.0, 4.0)),
    PotentialOption.DEXTERITY_PERCENT: OptionSpec(
        StatKey.DEXTERITY_PERCENT,
        ValueRange(1.0, 4.0),
    ),
    PotentialOption.VITALITY_PERCENT: OptionSpec(
        StatKey.VITALITY_PERCENT,
        ValueRange(1.0, 4.0),
    ),
    PotentialOption.LUCK_PERCENT: OptionSpec(
        StatKey.LUCK_PERCENT,
        ValueRange(1.0, 4.0),
    ),
    PotentialOption.SKILL_SPEED_PERCENT: OptionSpec(
        StatKey.SKILL_SPEED_PERCENT,
        ValueRange(1.0, 4.0),
    ),
    PotentialOption.RESIST_PERCENT: OptionSpec(
        StatKey.RESIST_PERCENT,
        ValueRange(1.0, 4.0),
    ),
    PotentialOption.CRIT_DAMAGE_PERCENT: OptionSpec(
        StatKey.CRIT_DAMAGE_PERCENT,
        ValueRange(1.0, 4.0),
    ),
    PotentialOption.HP_PERCENT: OptionSpec(StatKey.HP_PERCENT, ValueRange(1.0, 10.0)),
    PotentialOption.BOSS_ATTACK_PERCENT: OptionSpec(
        StatKey.BOSS_ATTACK_PERCENT,
        ValueRange(1.0, 5.0),
    ),
}


ADDITIONAL_OPTION_SPECS: dict[AdditionalOption, OptionSpec] = {
    AdditionalOption.STR: OptionSpec(StatKey.STR, ValueRange(1.0, 10.0)),
    AdditionalOption.DEXTERITY: OptionSpec(StatKey.DEXTERITY, ValueRange(1.0, 10.0)),
    AdditionalOption.VITALITY: OptionSpec(StatKey.VITALITY, ValueRange(1.0, 10.0)),
    AdditionalOption.LUCK: OptionSpec(StatKey.LUCK, ValueRange(1.0, 10.0)),
    AdditionalOption.HP: OptionSpec(StatKey.HP, ValueRange(10.0, 50.0)),
    AdditionalOption.CRIT_RATE_PERCENT: OptionSpec(
        StatKey.CRIT_RATE_PERCENT,
        ValueRange(0.1, 2.0),
    ),
    AdditionalOption.DROP_RATE_PERCENT: OptionSpec(
        StatKey.DROP_RATE_PERCENT,
        ValueRange(1.0, 5.0),
    ),
    AdditionalOption.POTION_HEAL_PERCENT: OptionSpec(
        StatKey.POTION_HEAL_PERCENT,
        ValueRange(1.0, 10.0),
    ),
}


ARMOR_SCROLL_BASE_EFFECTS: dict[ScrollTier, dict[StatKey, float]] = {
    ScrollTier.TEN: _stats((StatKey.HP_PERCENT, 2.0)),
    ScrollTier.TWENTY: _stats((StatKey.HP_PERCENT, 1.0)),
    ScrollTier.FIFTY: {},
    ScrollTier.SIXTY: {},
    ScrollTier.HUNDRED: {},
}
ARMOR_SCROLL_STAT_VALUES: dict[ScrollTier, float] = {
    ScrollTier.TEN: 5.0,
    ScrollTier.TWENTY: 4.0,
    ScrollTier.FIFTY: 3.0,
    ScrollTier.SIXTY: 2.0,
    ScrollTier.HUNDRED: 1.0,
}


def _build_armor_scroll_effects(
    slot: EquipmentSlot,
) -> dict[StatKey, dict[ScrollTier, dict[StatKey, float]]]:
    """방어구 주문서 효과 구성"""

    effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = {}
    for stat_key in (
        StatKey.STR,
        StatKey.DEXTERITY,
        StatKey.VITALITY,
        StatKey.LUCK,
    ):
        effects[stat_key] = {
            tier: _stats(
                (stat_key, ARMOR_SCROLL_STAT_VALUES[tier]),
                *ARMOR_SCROLL_BASE_EFFECTS[tier].items(),
            )
            for tier in ARMOR_SCROLL_STAT_VALUES
        }

    percent_stat_key: StatKey = {
        EquipmentSlot.HELMET: StatKey.LUCK_PERCENT,
        EquipmentSlot.ARMOR: StatKey.STR_PERCENT,
        EquipmentSlot.BELT: StatKey.VITALITY_PERCENT,
        EquipmentSlot.SHOES: StatKey.DEXTERITY_PERCENT,
    }[slot]
    effects[percent_stat_key] = {
        tier: _stats(
            (percent_stat_key, ARMOR_SCROLL_STAT_VALUES[tier]),
            *ARMOR_SCROLL_BASE_EFFECTS[tier].items(),
        )
        for tier in ARMOR_SCROLL_STAT_VALUES
    }
    return effects


WEAPON_SCROLL_EFFECTS: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = {
    StatKey.ATTACK: {
        ScrollTier.TEN: _stats((StatKey.DEXTERITY, 3.0), (StatKey.ATTACK, 9.0)),
        ScrollTier.TWENTY: _stats((StatKey.DEXTERITY, 1.0), (StatKey.ATTACK, 8.0)),
        ScrollTier.FIFTY: _stats((StatKey.ATTACK, 7.0)),
        ScrollTier.SIXTY: _stats((StatKey.ATTACK, 6.0)),
        ScrollTier.HUNDRED: _stats((StatKey.ATTACK, 3.0)),
    },
    StatKey.STR: {
        ScrollTier.TEN: _stats((StatKey.STR, 9.0), (StatKey.CRIT_RATE_PERCENT, 1.0)),
        ScrollTier.TWENTY: _stats(
            (StatKey.STR, 8.0),
            (StatKey.CRIT_RATE_PERCENT, 0.5),
        ),
        ScrollTier.FIFTY: _stats((StatKey.STR, 7.0)),
        ScrollTier.SIXTY: _stats((StatKey.STR, 6.0)),
        ScrollTier.HUNDRED: _stats((StatKey.STR, 3.0)),
    },
    StatKey.DEXTERITY: {
        ScrollTier.TEN: _stats(
            (StatKey.DEXTERITY, 9.0),
            (StatKey.CRIT_RATE_PERCENT, 1.0),
        ),
        ScrollTier.TWENTY: _stats(
            (StatKey.DEXTERITY, 8.0),
            (StatKey.CRIT_RATE_PERCENT, 0.5),
        ),
        ScrollTier.FIFTY: _stats((StatKey.DEXTERITY, 7.0)),
        ScrollTier.SIXTY: _stats((StatKey.DEXTERITY, 6.0)),
        ScrollTier.HUNDRED: _stats((StatKey.DEXTERITY, 3.0)),
    },
    StatKey.ATTACK_PERCENT: {
        ScrollTier.FORTY: _stats((StatKey.STR, 3.0), (StatKey.ATTACK_PERCENT, 3.0)),
    },
}


RING_SCROLL_EFFECTS: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = {
    stat_key: {
        tier: _stats(
            (stat_key, ARMOR_SCROLL_STAT_VALUES[tier]),
            *ARMOR_SCROLL_BASE_EFFECTS[tier].items(),
        )
        for tier in ARMOR_SCROLL_STAT_VALUES
    }
    for stat_key in (
        StatKey.STR,
        StatKey.DEXTERITY,
        StatKey.VITALITY,
        StatKey.LUCK,
    )
}


EQUIPMENT_SCROLL_EFFECTS: dict[
    EquipmentSlot,
    dict[StatKey, dict[ScrollTier, dict[StatKey, float]]],
] = {
    EquipmentSlot.HELMET: _build_armor_scroll_effects(EquipmentSlot.HELMET),
    EquipmentSlot.ARMOR: _build_armor_scroll_effects(EquipmentSlot.ARMOR),
    EquipmentSlot.BELT: _build_armor_scroll_effects(EquipmentSlot.BELT),
    EquipmentSlot.SHOES: _build_armor_scroll_effects(EquipmentSlot.SHOES),
    EquipmentSlot.WEAPON: WEAPON_SCROLL_EFFECTS,
    EquipmentSlot.RING1: RING_SCROLL_EFFECTS,
    EquipmentSlot.RING2: RING_SCROLL_EFFECTS,
    EquipmentSlot.NECKLACE: {},
    EquipmentSlot.EARRING: {},
}


EQUIPMENT_SCROLL_LIMITS: dict[EquipmentSlot, dict[int, int] | None] = {
    EquipmentSlot.HELMET: {0: 3, 20: 3, 50: 3, 80: 4, 110: 5, 150: 6, 180: 7},
    EquipmentSlot.ARMOR: {0: 3, 20: 3, 50: 3, 80: 4, 110: 5, 150: 6, 180: 7},
    EquipmentSlot.BELT: {0: 3, 20: 3, 50: 3, 80: 4, 110: 5, 150: 6, 180: 7},
    EquipmentSlot.SHOES: {0: 3, 20: 3, 50: 3, 80: 4, 110: 5, 150: 6, 180: 7},
    EquipmentSlot.WEAPON: {0: 3, 20: 3, 50: 4, 80: 5, 110: 6, 150: 7, 180: 8},
    EquipmentSlot.RING1: None,
    EquipmentSlot.RING2: None,
    EquipmentSlot.NECKLACE: {},
    EquipmentSlot.EARRING: {},
}


DISPLAY_STAND_SPECS: tuple[DisplayStandSpec, ...] = (
    DisplayStandSpec(DisplayStand.GAJUK, "찬란한 가죽"),
    DisplayStandSpec(DisplayStand.JANGIN, "찬란한 장인"),
    DisplayStandSpec(DisplayStand.DONGGUN, "찬란한 동군"),
    DisplayStandSpec(DisplayStand.TUHAE, "찬란한 투해"),
    DisplayStandSpec(DisplayStand.GWANGJEON, "찬란한 광전"),
    DisplayStandSpec(DisplayStand.BAEKBI, "찬란한 백비"),
    DisplayStandSpec(DisplayStand.GWANGSEOL, "찬란한 광설"),
    DisplayStandSpec(DisplayStand.HOGUN, "찬란한 호군"),
    DisplayStandSpec(DisplayStand.BAEKHYEON, "찬란한 백현"),
    DisplayStandSpec(DisplayStand.CHEONGGUN, "찬란한 청군"),
    DisplayStandSpec(DisplayStand.JANGHYEON, "찬란한 장현"),
    DisplayStandSpec(DisplayStand.GEUMGUN, "찬란한 금군"),
    DisplayStandSpec(DisplayStand.JINMU, "찬란한 진무"),
    DisplayStandSpec(DisplayStand.NOKGWI, "찬란한 녹귀"),
    DisplayStandSpec(DisplayStand.GEUMTU, "찬란한 금투"),
    DisplayStandSpec(DisplayStand.GEUMCHEONG, "찬란한 금청"),
    DisplayStandSpec(DisplayStand.YEOMHWA, "찬란한 염화"),
    DisplayStandSpec(DisplayStand.GOEROK, "찬란한 괴록"),
    DisplayStandSpec(DisplayStand.JEOKRYEONG, "찬란한 적령"),
    DisplayStandSpec(DisplayStand.TURYEONG, "찬란한 투령"),
    DisplayStandSpec(DisplayStand.JINGUN, "찬란한 진군"),
    DisplayStandSpec(DisplayStand.SANRYEONG, "찬란한 산령"),
    DisplayStandSpec(DisplayStand.GWANGRYONG, "찬란한 광룡"),
    DisplayStandSpec(DisplayStand.CHEONGUN, "찬란한 천군"),
    DisplayStandSpec(DisplayStand.CHEONGGWI, "찬란한 청귀"),
    DisplayStandSpec(DisplayStand.GOEHWANG, "찬란한 괴황"),
    DisplayStandSpec(DisplayStand.GEUMSEONG, "찬란한 금성"),
)


DISPLAY_STAND_COLUMN_STAT_KEYS: dict[DisplayStandColumn, tuple[StatKey, ...]] = {
    DisplayStandColumn.HELMET: (StatKey.EXP_PERCENT,),
    DisplayStandColumn.ARMOR: (StatKey.ATTACK,),
    DisplayStandColumn.BELT: (StatKey.DROP_RATE_PERCENT,),
    DisplayStandColumn.SHOES: (StatKey.ATTACK_PERCENT,),
    DisplayStandColumn.SET: (
        StatKey.STR_PERCENT,
        StatKey.DEXTERITY_PERCENT,
        StatKey.VITALITY_PERCENT,
        StatKey.LUCK_PERCENT,
    ),
}


ELIXIR_SPECS: dict[Elixir, ConsumableSpec] = {
    Elixir.HWANGHWANDAN: ConsumableSpec(
        "황환단",
        _stats(
            (StatKey.STR, 2.0),
            (StatKey.DEXTERITY, 2.0),
            (StatKey.VITALITY, 2.0),
            (StatKey.LUCK, 2.0),
        ),
    ),
    Elixir.NOKHWANDAN: ConsumableSpec(
        "녹환단",
        _stats((StatKey.VITALITY_PERCENT, 1.0), (StatKey.STR_PERCENT, 1.0)),
    ),
    Elixir.JAHWANDAN: ConsumableSpec(
        "자환단",
        _stats((StatKey.DEXTERITY_PERCENT, 1.0), (StatKey.LUCK_PERCENT, 1.0)),
    ),
    Elixir.CHEONGHWANDAN: ConsumableSpec(
        "청환단",
        _stats((StatKey.ATTACK, 3.0), (StatKey.BOSS_ATTACK_PERCENT, 1.0)),
    ),
    Elixir.JEOKHWANDAN: ConsumableSpec(
        "적환단",
        _stats((StatKey.HP_PERCENT, 1.0), (StatKey.HP, 15.0)),
    ),
    Elixir.BAEKHWANDAN: ConsumableSpec(
        "백환단",
        _stats((StatKey.EXP_PERCENT, 1.0), (StatKey.DROP_RATE_PERCENT, 1.0)),
    ),
    Elixir.HEUKHWANDAN: ConsumableSpec(
        "흑환단",
        _stats((StatKey.POTION_HEAL_PERCENT, 3.0), (StatKey.RESIST_PERCENT, 3.0)),
    ),
    Elixir.OKHWANDAN: ConsumableSpec(
        "옥환단",
        _stats((StatKey.ATTACK_PERCENT, 1.0)),
    ),
    Elixir.EUNHWANDAN: ConsumableSpec(
        "은환단",
        _stats((StatKey.FINAL_ATTACK_PERCENT, 1.0)),
    ),
    Elixir.GEUMHWANDAN: ConsumableSpec(
        "금환단",
        _stats((StatKey.SKILL_DAMAGE_PERCENT, 1.0)),
    ),
    Elixir.MAEHWADAN: ConsumableSpec(
        "매화단",
        _stats((StatKey.HP, 5.0), (StatKey.CRIT_DAMAGE_PERCENT, 3.0)),
    ),
    Elixir.YONGHYEOLDAN: ConsumableSpec(
        "용혈단",
        _stats((StatKey.HP_PERCENT, 3.0), (StatKey.VITALITY, 5.0)),
    ),
    Elixir.MYEONGWOLDAN: ConsumableSpec(
        "명월단",
        _stats((StatKey.LUCK, 3.0), (StatKey.BOSS_ATTACK_PERCENT, 1.0)),
    ),
    Elixir.TAEGEUKDAN: ConsumableSpec(
        "태극단",
        _stats((StatKey.STR, 3.0), (StatKey.BOSS_ATTACK_PERCENT, 1.0)),
    ),
    Elixir.CHEONGYEONGDAN: ConsumableSpec(
        "천경단",
        _stats((StatKey.LUCK_PERCENT, 1.0), (StatKey.ATTACK, 3.0)),
    ),
    Elixir.SIGONGDAN: ConsumableSpec(
        "시공단",
        _stats((StatKey.EXP_PERCENT, 1.0), (StatKey.POTION_HEAL_PERCENT, 3.0)),
    ),
    Elixir.CHEONGRYONGDAN: ConsumableSpec(
        "청룡단",
        _stats((StatKey.STR, 4.0), (StatKey.EXP_PERCENT, 1.0)),
    ),
    Elixir.BAEKHODAN: ConsumableSpec(
        "백호단",
        _stats((StatKey.DEXTERITY, 4.0), (StatKey.EXP_PERCENT, 1.0)),
    ),
    Elixir.JUJAKDAN: ConsumableSpec(
        "주작단",
        _stats((StatKey.VITALITY, 4.0), (StatKey.EXP_PERCENT, 1.0)),
    ),
    Elixir.HYEONMUDAN: ConsumableSpec(
        "현무단",
        _stats((StatKey.LUCK, 4.0), (StatKey.EXP_PERCENT, 1.0)),
    ),
}


PILL_SPECS: dict[Pill, ConsumableSpec] = {
    Pill.HWALSAENGHWAN: ConsumableSpec("활생환", _stats((StatKey.VITALITY, 5.0))),
    Pill.HWANGTOHWAN: ConsumableSpec(
        "황토환",
        _stats((StatKey.POTION_HEAL_PERCENT, 5.0)),
    ),
    Pill.HOESAENGHWAN: ConsumableSpec(
        "회생환",
        _stats((StatKey.STR_PERCENT, 3.0)),
    ),
    Pill.MYEONGMOKHWAN: ConsumableSpec(
        "명목환",
        _stats((StatKey.EXP_PERCENT, 4.0)),
    ),
    Pill.CHEONMOKHWAN: ConsumableSpec(
        "천목환",
        _stats((StatKey.EXP_PERCENT, 6.0)),
    ),
    Pill.SINMOKHWAN: ConsumableSpec(
        "신목환",
        _stats((StatKey.EXP_PERCENT, 8.0)),
    ),
    Pill.GANGGEUNHWAN: ConsumableSpec("강근환", _stats((StatKey.ATTACK, 10.0))),
    Pill.CHEONGSIMHWAN: ConsumableSpec(
        "청심환",
        _stats((StatKey.DEXTERITY, 5.0)),
    ),
    Pill.DAERYEOKHWAN: ConsumableSpec("대력환", _stats((StatKey.STR, 5.0))),
    Pill.YONGRYEOKHWAN: ConsumableSpec(
        "용력환",
        _stats((StatKey.SKILL_SPEED_PERCENT, 3.0)),
    ),
    Pill.CHEONSEHWAN: ConsumableSpec(
        "천세환",
        _stats((StatKey.ATTACK_PERCENT, 3.0)),
    ),
    Pill.CHEONSIMHWAN: ConsumableSpec(
        "천심환",
        _stats((StatKey.CRIT_RATE_PERCENT, 2.0)),
    ),
    Pill.MANNYEONHWAN: ConsumableSpec(
        "만년환",
        _stats((StatKey.DROP_RATE_PERCENT, 10.0)),
    ),
}
