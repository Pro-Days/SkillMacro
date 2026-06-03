from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from app.scripts.calculator_models import RealmTier, StatKey


CHARACTER_DATA_VERSION: int = 1
TITLE_STAT_SLOT_COUNT: int = 3
EQUIPMENT_OPTION_SLOT_COUNT: int = 3
MAX_EQUIPPED_TALISMAN_COUNT: int = 3
MAX_TALISMAN_LEVEL: int = 14
MAX_ELIXIR_COUNT: int = 10


class EquipmentSlot(str, Enum):
    """캐릭터 장비 슬롯"""

    HELMET = "helmet"
    ARMOR = "armor"
    BELT = "belt"
    SHOES = "shoes"
    WEAPON = "weapon"
    RING1 = "ring1"
    RING2 = "ring2"
    NECKLACE = "necklace"
    EARRING = "earring"


class EquipmentKind(str, Enum):
    """캐릭터 보유 장비 종류"""

    HELMET = "helmet"
    ARMOR = "armor"
    BELT = "belt"
    SHOES = "shoes"
    WEAPON = "weapon"
    RING = "ring"
    NECKLACE = "necklace"
    EARRING = "earring"


class EquipmentGrade(str, Enum):
    """장비 등급"""

    BASIC = "basic"
    RADIANT = "radiant"


class ScrollTier(str, Enum):
    """주문서 성공률 단계"""

    TEN = "10"
    TWENTY = "20"
    FORTY = "40"
    FIFTY = "50"
    SIXTY = "60"
    HUNDRED = "100"


class PotentialOption(str, Enum):
    """잠재능력 옵션"""

    STR_PERCENT = "str_percent"
    DEXTERITY_PERCENT = "dexterity_percent"
    VITALITY_PERCENT = "vitality_percent"
    LUCK_PERCENT = "luck_percent"
    SKILL_SPEED_PERCENT = "skill_speed_percent"
    RESIST_PERCENT = "resist_percent"
    CRIT_DAMAGE_PERCENT = "crit_damage_percent"
    HP_PERCENT = "hp_percent"
    BOSS_ATTACK_PERCENT = "boss_attack_percent"


class AdditionalOption(str, Enum):
    """추가능력 옵션"""

    STR = "str"
    DEXTERITY = "dexterity"
    VITALITY = "vitality"
    LUCK = "luck"
    HP = "hp"
    CRIT_RATE_PERCENT = "crit_rate_percent"
    DROP_RATE_PERCENT = "drop_rate_percent"
    POTION_HEAL_PERCENT = "potion_heal_percent"


class DisplayStand(str, Enum):
    """진열대 식별자"""

    CRUEL_LEATHER = "cruel_leather"
    CRUEL_ARTISAN = "cruel_artisan"
    CRUEL_GLOW = "cruel_glow"
    CRUEL_SNOW = "cruel_snow"
    CRUEL_FALCON = "cruel_falcon"
    CRUEL_FIGHTING_SPIRIT = "cruel_fighting_spirit"
    CRUEL_WHITE_RAIN = "cruel_white_rain"
    CRUEL_TIGER = "cruel_tiger"
    CALM_CLEAR_STREAM = "calm_clear_stream"
    CALM_INK_FLOWER = "calm_ink_flower"
    CALM_MOONLIGHT = "calm_moonlight"
    CALM_RED_FLAME = "calm_red_flame"
    CALM_WIND_WAVE = "calm_wind_wave"
    CALM_CLOUD_MIST = "calm_cloud_mist"
    CALM_THUNDER = "calm_thunder"
    CALM_ICE_WHITE = "calm_ice_white"
    FLYING_DRAGON_PEERLESS = "flying_dragon_peerless"
    FLYING_DRAGON_BREAKING_SKY = "flying_dragon_breaking_sky"
    FLYING_DRAGON_FATAL = "flying_dragon_fatal"
    FLYING_DRAGON_FRENZY = "flying_dragon_frenzy"
    MYTH_DAWN = "myth_dawn"
    MYTH_DUSK = "myth_dusk"
    MYTH_STARRY_NET = "myth_starry_net"
    MYTH_ABYSS = "myth_abyss"
    LEGEND_DRAGON_SCALE = "legend_dragon_scale"
    LEGEND_PHOENIX = "legend_phoenix"
    LEGEND_KIRIN = "legend_kirin"


class DisplayStandColumn(str, Enum):
    """진열대 입력 열"""

    HELMET = "helmet"
    ARMOR = "armor"
    BELT = "belt"
    SHOES = "shoes"
    SET = "set"


class Elixir(str, Enum):
    """영단 식별자"""

    HWANGHWANDAN = "hwanghwandan"
    NOKHWANDAN = "nokhwandan"
    JAHWANDAN = "jahwandan"
    CHEONGHWANDAN = "cheonghwandan"
    JEOKHWANDAN = "jeokhwandan"
    BAEKHWANDAN = "baekhwandan"
    HEUKHWANDAN = "heukhwandan"
    OKHWANDAN = "okhwandan"
    EUNHWANDAN = "eunhwandan"
    GEUMHWANDAN = "geumhwandan"
    MAEHWADAN = "maehwadan"
    YONGHYEOLDAN = "yonghyeoldan"
    MYEONGWOLDAN = "myeongwoldan"
    TAEGEUKDAN = "taegeukdan"
    CHEONGYEONGDAN = "cheongyeongdan"
    SIGONGDAN = "sigongdan"


class Pill(str, Enum):
    """환 식별자"""

    HWALSAENGHWAN = "hwalsaenghwan"
    HWANGTOHWAN = "hwangtohwan"
    HOESAENGHWAN = "hoesaenghwan"
    MYEONGMOKHWAN = "myeongmokhwan"
    CHEONMOKHWAN = "cheonmokhwan"
    SINMOKHWAN = "sinmokhwan"
    GANGGEUNHWAN = "ganggeunhwan"
    CHEONGSIMHWAN = "cheongsimhwan"
    DAERYEOKHWAN = "daeryeokhwan"
    YONGRYEOKHWAN = "yongryeokhwan"
    CHEONSEHWAN = "cheonsehwan"
    CHEONSIMHWAN = "cheonsimhwan"
    MANNYEONHWAN = "mannyeonhwan"


def _new_id() -> str:
    """새 저장 식별자 생성"""

    return str(uuid4())


def _read_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    """저장 루트의 하위 딕셔너리 조회"""

    value: Any = data[key]
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a dict")

    return value


def _read_list(data: dict[str, Any], key: str) -> list[Any]:
    """저장 루트의 하위 리스트 조회"""

    value: Any = data[key]
    if not isinstance(value, list):
        raise TypeError(f"{key} must be a list")

    return value


def _read_optional_stat_slots(
    raw_slots: list[Any],
) -> tuple["TitleStatSlot | None", ...]:
    """칭호 스탯 슬롯 복원"""

    if len(raw_slots) != TITLE_STAT_SLOT_COUNT:
        raise ValueError("title stat slots must have exactly 3 items")

    slots: list[TitleStatSlot | None] = []
    for raw_slot in raw_slots:
        if raw_slot is None:
            slots.append(None)
            continue

        if not isinstance(raw_slot, dict):
            raise TypeError("title stat slot must be a dict or null")

        slots.append(TitleStatSlot.from_dict(raw_slot))

    return tuple(slots)


def _read_optional_potential_lines(
    raw_lines: list[Any],
) -> tuple["PotentialLine | None", ...]:
    """잠재능력 슬롯 복원"""

    if len(raw_lines) != EQUIPMENT_OPTION_SLOT_COUNT:
        raise ValueError("potential lines must have exactly 3 items")

    lines: list[PotentialLine | None] = []
    for raw_line in raw_lines:
        if raw_line is None:
            lines.append(None)
            continue

        if not isinstance(raw_line, dict):
            raise TypeError("potential line must be a dict or null")

        lines.append(PotentialLine.from_dict(raw_line))

    return tuple(lines)


def _read_optional_additional_lines(
    raw_lines: list[Any],
) -> tuple["AdditionalLine | None", ...]:
    """추가능력 슬롯 복원"""

    if len(raw_lines) != EQUIPMENT_OPTION_SLOT_COUNT:
        raise ValueError("additional lines must have exactly 3 items")

    lines: list[AdditionalLine | None] = []
    for raw_line in raw_lines:
        if raw_line is None:
            lines.append(None)
            continue

        if not isinstance(raw_line, dict):
            raise TypeError("additional line must be a dict or null")

        lines.append(AdditionalLine.from_dict(raw_line))

    return tuple(lines)


def _stat_float_map_from_dict(data: dict[str, Any]) -> dict[StatKey, float]:
    """StatKey 문자열 맵 복원"""

    values: dict[StatKey, float] = {}
    for key, value in data.items():
        values[StatKey(str(key))] = float(value)

    return values


def _stat_float_map_to_dict(data: dict[StatKey, float]) -> dict[str, float]:
    """StatKey 맵 저장 구조 구성"""

    return {stat_key.value: float(value) for stat_key, value in data.items()}


@dataclass(slots=True)
class StatDistribution:
    """캐릭터 스탯 분배"""

    strength: int = 0
    dexterity: int = 0
    vitality: int = 0
    luck: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StatDistribution":
        """저장 데이터로부터 스탯 분배 복원"""

        return cls(
            strength=int(data["strength"]),
            dexterity=int(data["dexterity"]),
            vitality=int(data["vitality"]),
            luck=int(data["luck"]),
        )

    def to_dict(self) -> dict[str, int]:
        """스탯 분배 직렬화"""

        return {
            "strength": self.strength,
            "dexterity": self.dexterity,
            "vitality": self.vitality,
            "luck": self.luck,
        }


@dataclass(slots=True)
class DanjeonDistribution:
    """캐릭터 단전 분배"""

    upper: int = 0
    middle: int = 0
    lower: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DanjeonDistribution":
        """저장 데이터로부터 단전 분배 복원"""

        return cls(
            upper=int(data["upper"]),
            middle=int(data["middle"]),
            lower=int(data["lower"]),
        )

    def to_dict(self) -> dict[str, int]:
        """단전 분배 직렬화"""

        return {
            "upper": self.upper,
            "middle": self.middle,
            "lower": self.lower,
        }


@dataclass(slots=True)
class TitleStatSlot:
    """칭호 스탯 슬롯"""

    stat_key: StatKey
    value: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TitleStatSlot":
        """저장 데이터로부터 칭호 스탯 슬롯 복원"""

        return cls(
            stat_key=StatKey(str(data["stat_key"])),
            value=float(data["value"]),
        )

    def to_dict(self) -> dict[str, str | float]:
        """칭호 스탯 슬롯 직렬화"""

        return {
            "stat_key": self.stat_key.value,
            "value": float(self.value),
        }


@dataclass(slots=True)
class CharacterTitle:
    """캐릭터 보유 칭호"""

    id: str = field(default_factory=_new_id)
    name: str = ""
    slots: tuple[TitleStatSlot | None, ...] = field(
        default_factory=lambda: (None, None, None)
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterTitle":
        """저장 데이터로부터 보유 칭호 복원"""

        raw_slots: list[Any] = _read_list(data, "slots")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            slots=_read_optional_stat_slots(raw_slots),
        )

    def to_dict(self) -> dict[str, Any]:
        """보유 칭호 직렬화"""

        return {
            "id": self.id,
            "name": self.name,
            "slots": [
                slot.to_dict() if slot is not None else None for slot in self.slots
            ],
        }


@dataclass(slots=True)
class CharacterTalisman:
    """캐릭터 보유 부적"""

    id: str = field(default_factory=_new_id)
    talisman_key: str = ""
    level: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterTalisman":
        """저장 데이터로부터 보유 부적 복원"""

        return cls(
            id=str(data["id"]),
            talisman_key=str(data["talisman_key"]),
            level=int(data["level"]),
        )

    def to_dict(self) -> dict[str, str | int]:
        """보유 부적 직렬화"""

        return {
            "id": self.id,
            "talisman_key": self.talisman_key,
            "level": self.level,
        }


@dataclass(slots=True)
class Equipped:
    """캐릭터 장착 상태"""

    title_id: str | None = None
    talisman_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Equipped":
        """저장 데이터로부터 장착 상태 복원"""

        raw_title_id: Any = data["title_id"]
        title_id: str | None = None if raw_title_id is None else str(raw_title_id)
        return cls(
            title_id=title_id,
            talisman_ids=[str(item) for item in _read_list(data, "talisman_ids")],
        )

    def to_dict(self) -> dict[str, Any]:
        """장착 상태 직렬화"""

        return {
            "title_id": self.title_id,
            "talisman_ids": self.talisman_ids.copy(),
        }


@dataclass(slots=True)
class PotentialLine:
    """잠재능력 입력 라인"""

    option: PotentialOption
    value: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PotentialLine":
        """저장 데이터로부터 잠재능력 라인 복원"""

        return cls(
            option=PotentialOption(str(data["option"])),
            value=float(data["value"]),
        )

    def to_dict(self) -> dict[str, str | float]:
        """잠재능력 라인 직렬화"""

        return {
            "option": self.option.value,
            "value": float(self.value),
        }


@dataclass(slots=True)
class AdditionalLine:
    """추가능력 입력 라인"""

    option: AdditionalOption
    value: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdditionalLine":
        """저장 데이터로부터 추가능력 라인 복원"""

        return cls(
            option=AdditionalOption(str(data["option"])),
            value=float(data["value"]),
        )

    def to_dict(self) -> dict[str, str | float]:
        """추가능력 라인 직렬화"""

        return {
            "option": self.option.value,
            "value": float(self.value),
        }


@dataclass(slots=True)
class EquipmentFreeStatLine:
    """장비 자유 기본 스탯 라인"""

    stat_key: StatKey
    value: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EquipmentFreeStatLine":
        """저장 데이터로부터 자유 기본 스탯 라인 복원"""

        return cls(
            stat_key=StatKey(str(data["stat_key"])),
            value=float(data["value"]),
        )

    def to_dict(self) -> dict[str, str | float]:
        """자유 기본 스탯 라인 직렬화"""

        return {
            "stat_key": self.stat_key.value,
            "value": float(self.value),
        }


@dataclass(slots=True)
class OwnedEquipment:
    """캐릭터 장비 입력 상태"""

    name: str = ""
    kind: EquipmentKind = EquipmentKind.WEAPON
    item_name: str | None = None
    level: int = 0
    tier: int = 1
    grade: EquipmentGrade | None = None
    base_stat_lines: list[EquipmentFreeStatLine] = field(default_factory=list)
    reforge_stats: dict[StatKey, float] = field(default_factory=dict)
    scrolls: dict[StatKey, dict[ScrollTier, int]] = field(default_factory=dict)
    potentials: tuple[PotentialLine | None, ...] = field(
        default_factory=lambda: (None, None, None)
    )
    additionals: tuple[AdditionalLine | None, ...] = field(
        default_factory=lambda: (None, None, None)
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OwnedEquipment":
        """저장 데이터로부터 장비 입력 상태 복원"""

        raw_item_name: Any = data["item_name"]
        item_name: str | None = None if raw_item_name is None else str(raw_item_name)

        raw_grade: Any = data["grade"]
        grade: EquipmentGrade | None = None
        if raw_grade is not None:
            grade = EquipmentGrade(str(raw_grade))

        raw_scrolls: dict[str, Any] = _read_dict(data, "scrolls")
        scrolls: dict[StatKey, dict[ScrollTier, int]] = {}
        for stat_key_value, raw_tiers in raw_scrolls.items():
            if not isinstance(raw_tiers, dict):
                raise TypeError("scroll tier map must be a dict")

            scrolls[StatKey(str(stat_key_value))] = {
                ScrollTier(str(tier)): int(count)
                for tier, count in raw_tiers.items()
            }

        return cls(
            name=str(data["name"]),
            kind=EquipmentKind(str(data["kind"])),
            item_name=item_name,
            level=int(data["level"]),
            tier=int(data["tier"]),
            grade=grade,
            base_stat_lines=[
                EquipmentFreeStatLine.from_dict(item)
                for item in _read_list(data, "base_stat_lines")
            ],
            reforge_stats=_stat_float_map_from_dict(_read_dict(data, "reforge_stats")),
            scrolls=scrolls,
            potentials=_read_optional_potential_lines(_read_list(data, "potentials")),
            additionals=_read_optional_additional_lines(
                _read_list(data, "additionals")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """장비 입력 상태 직렬화"""

        return {
            "name": self.name,
            "kind": self.kind.value,
            "item_name": self.item_name,
            "level": self.level,
            "tier": self.tier,
            "grade": self.grade.value if self.grade is not None else None,
            "base_stat_lines": [line.to_dict() for line in self.base_stat_lines],
            "reforge_stats": _stat_float_map_to_dict(self.reforge_stats),
            "scrolls": {
                stat_key.value: {
                    tier.value: int(count) for tier, count in tier_counts.items()
                }
                for stat_key, tier_counts in self.scrolls.items()
            },
            "potentials": [
                line.to_dict() if line is not None else None for line in self.potentials
            ],
            "additionals": [
                line.to_dict() if line is not None else None
                for line in self.additionals
            ],
        }


@dataclass(slots=True)
class EquipmentState:
    """캐릭터 보유 장비와 장착 상태"""

    owned: list[OwnedEquipment] = field(default_factory=list)
    equipped: dict[EquipmentSlot, str | None] = field(
        default_factory=lambda: {slot: None for slot in EquipmentSlot}
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EquipmentState":
        """저장 데이터로부터 보유 장비와 장착 상태 복원"""

        owned: list[OwnedEquipment] = [
            OwnedEquipment.from_dict(item) for item in _read_list(data, "owned")
        ]
        equipped: dict[EquipmentSlot, str | None] = {}
        for slot in EquipmentSlot:
            raw_name: Any = _read_dict(data, "equipped")[slot.value]
            if raw_name is None:
                equipped[slot] = None
                continue

            equipped[slot] = str(raw_name)

        return cls(owned=owned, equipped=equipped)

    def to_dict(self) -> dict[str, Any]:
        """보유 장비와 장착 상태 직렬화"""

        return {
            "owned": [equipment.to_dict() for equipment in self.owned],
            "equipped": {
                slot.value: equipment_name
                for slot, equipment_name in self.equipped.items()
            },
        }


@dataclass(slots=True)
class DisplayStandEntry:
    """진열대 한 행 입력값"""

    values: dict[DisplayStandColumn, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DisplayStandEntry":
        """저장 데이터로부터 진열대 행 복원"""

        return cls(
            values={
                DisplayStandColumn(str(key)): float(value)
                for key, value in data["values"].items()
            }
        )

    def to_dict(self) -> dict[str, dict[str, float]]:
        """진열대 행 직렬화"""

        return {
            "values": {
                column.value: float(value) for column, value in self.values.items()
            }
        }


@dataclass(slots=True)
class DisplayStandState:
    """진열대 입력 상태"""

    entries: dict[DisplayStand, DisplayStandEntry] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DisplayStandState":
        """저장 데이터로부터 진열대 상태 복원"""

        return cls(
            entries={
                DisplayStand(str(key)): DisplayStandEntry.from_dict(value)
                for key, value in data["entries"].items()
            }
        )

    def to_dict(self) -> dict[str, dict[str, dict[str, float]]]:
        """진열대 상태 직렬화"""

        return {
            "entries": {
                stand.value: entry.to_dict() for stand, entry in self.entries.items()
            }
        }


@dataclass(slots=True)
class ElixirState:
    """영단 사용 상태"""

    counts: dict[Elixir, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ElixirState":
        """저장 데이터로부터 영단 상태 복원"""

        return cls(
            counts={
                Elixir(str(key)): int(value) for key, value in data["counts"].items()
            }
        )

    def to_dict(self) -> dict[str, dict[str, int]]:
        """영단 상태 직렬화"""

        return {
            "counts": {
                elixir.value: int(count) for elixir, count in self.counts.items()
            }
        }


@dataclass(slots=True)
class PillState:
    """환 사용 상태"""

    active: set[Pill] = field(default_factory=set)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PillState":
        """저장 데이터로부터 환 상태 복원"""

        return cls(active={Pill(str(item)) for item in _read_list(data, "active")})

    def to_dict(self) -> dict[str, list[str]]:
        """환 상태 직렬화"""

        return {"active": [pill.value for pill in self.active]}


@dataclass(slots=True)
class CharacterProfile:
    """전역 캐릭터 프로필"""

    id: str = field(default_factory=_new_id)
    name: str = ""
    level: int = 0
    realm: RealmTier = RealmTier.THIRD_RATE
    distribution: StatDistribution = field(default_factory=StatDistribution)
    danjeon: DanjeonDistribution = field(default_factory=DanjeonDistribution)
    titles: list[CharacterTitle] = field(default_factory=list)
    talismans: list[CharacterTalisman] = field(default_factory=list)
    equipped: Equipped = field(default_factory=Equipped)
    equipment: EquipmentState = field(default_factory=EquipmentState)
    display_stand: DisplayStandState = field(default_factory=DisplayStandState)
    elixir: ElixirState = field(default_factory=ElixirState)
    pill: PillState = field(default_factory=PillState)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterProfile":
        """저장 데이터로부터 캐릭터 프로필 복원"""

        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            level=int(data["level"]),
            realm=RealmTier(str(data["realm"])),
            distribution=StatDistribution.from_dict(_read_dict(data, "distribution")),
            danjeon=DanjeonDistribution.from_dict(_read_dict(data, "danjeon")),
            titles=[
                CharacterTitle.from_dict(item) for item in _read_list(data, "titles")
            ],
            talismans=[
                CharacterTalisman.from_dict(item)
                for item in _read_list(data, "talismans")
            ],
            equipped=Equipped.from_dict(_read_dict(data, "equipped")),
            equipment=EquipmentState.from_dict(_read_dict(data, "equipment")),
            display_stand=DisplayStandState.from_dict(
                _read_dict(data, "display_stand")
            ),
            elixir=ElixirState.from_dict(_read_dict(data, "elixir")),
            pill=PillState.from_dict(_read_dict(data, "pill")),
        )

    def to_dict(self) -> dict[str, Any]:
        """캐릭터 프로필 직렬화"""

        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "realm": self.realm.value,
            "distribution": self.distribution.to_dict(),
            "danjeon": self.danjeon.to_dict(),
            "titles": [title.to_dict() for title in self.titles],
            "talismans": [talisman.to_dict() for talisman in self.talismans],
            "equipped": self.equipped.to_dict(),
            "equipment": self.equipment.to_dict(),
            "display_stand": self.display_stand.to_dict(),
            "elixir": self.elixir.to_dict(),
            "pill": self.pill.to_dict(),
        }


@dataclass(slots=True)
class CharacterStore:
    """전역 캐릭터 저장 루트"""

    version: int = CHARACTER_DATA_VERSION
    characters: list[CharacterProfile] = field(default_factory=list)
    selected_index: int = -1

    @classmethod
    def create_empty(cls) -> "CharacterStore":
        """빈 캐릭터 저장 루트 생성"""

        return cls(
            version=CHARACTER_DATA_VERSION,
            characters=[],
            selected_index=-1,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterStore":
        """저장 데이터로부터 캐릭터 저장 루트 복원"""

        return cls(
            version=int(data["version"]),
            characters=[
                CharacterProfile.from_dict(item)
                for item in _read_list(data, "characters")
            ],
            selected_index=int(data["selected_index"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """캐릭터 저장 루트 직렬화"""

        return {
            "version": self.version,
            "characters": [character.to_dict() for character in self.characters],
            "selected_index": self.selected_index,
        }
