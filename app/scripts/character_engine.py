from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

from app.scripts.calculator_engine import evaluate_official_power
from app.scripts.calculator_models import (
    REALM_TIER_SPECS,
    TALISMAN_SPECS,
    BaseStats,
    DanjeonState,
    DistributionState,
    EquippedState,
    FinalStats,
    OwnedTalisman,
    OwnedTitle,
    RealmTier,
    StatKey,
    TalismanSpec,
)
from app.scripts.character_data import (
    ADDITIONAL_OPTION_SPECS,
    ARMOR_EQUIPMENT_SLOTS,
    ARMOR_SLOT_STAT_KEYS,
    DISPLAY_STAND_COLUMN_STAT_KEYS,
    ELIXIR_SPECS,
    EQUIPMENT_ITEM_SPECS,
    EQUIPMENT_REFORGE_STAT_KEYS,
    EQUIPMENT_SCROLL_EFFECTS,
    EQUIPMENT_SCROLL_LIMITS,
    NECKLACE_REFORGE_STAT_KEYS,
    PILL_SPECS,
    POTENTIAL_EQUIPMENT_SLOTS,
    POTENTIAL_OPTION_SPECS,
    EquipmentItemSpec,
    OptionSpec,
)
from app.scripts.character_models import (
    CHARACTER_DATA_VERSION,
    EQUIPMENT_KIND_SLOTS,
    EQUIPMENT_OPTION_SLOT_COUNT,
    MAX_ELIXIR_COUNT,
    MAX_EQUIPPED_TALISMAN_COUNT,
    MAX_REFORGE_STEP,
    MAX_TALISMAN_LEVEL,
    AdditionalLine,
    CharacterProfile,
    CharacterStore,
    CharacterTalisman,
    CharacterTitle,
    DanjeonDistribution,
    EquipmentGrade,
    EquipmentKind,
    EquipmentSlot,
    OwnedEquipment,
    PotentialLine,
    ScrollTier,
    StatDistribution,
)

CHARACTER_BASE_HP: float = 50.0
CHARACTER_HP_PER_LEVEL: float = 5.0


@dataclass(frozen=True, slots=True)
class LiveStatView:
    """캐릭터 실시간 스탯 계산 결과"""

    base: BaseStats
    final: FinalStats
    official_power: float


@dataclass(frozen=True, slots=True)
class CalculatorInputFill:
    """계산기 입력 페이지 반영값"""

    overall_stats: dict[StatKey, float]
    level: int
    realm_tier: RealmTier
    distribution: DistributionState
    danjeon: DanjeonState
    owned_titles: list[OwnedTitle]
    owned_talismans: list[OwnedTalisman]
    equipped_state: EquippedState


def _character_base_stat_map(profile: CharacterProfile) -> dict[StatKey, float]:
    """캐릭터 기본 원시 스탯 맵 구성"""

    base_values: dict[StatKey, float] = BaseStats.create_default().to_stat_map()
    base_values[StatKey.HP] = CHARACTER_BASE_HP + (
        profile.level * CHARACTER_HP_PER_LEVEL
    )
    return base_values


def _add_stat(
    target: dict[StatKey, float],
    stat_key: StatKey,
    value: float,
) -> None:
    """단일 스탯 누적"""

    target[stat_key] = target[stat_key] + value


def _merge_stats(
    target: dict[StatKey, float],
    source: dict[StatKey, float],
    multiplier: float = 1.0,
) -> None:
    """스탯 맵 누적"""

    for stat_key, value in source.items():
        _add_stat(target, stat_key, value * multiplier)


def _validate_non_negative_int(value: int, field_name: str) -> None:
    """음수 정수 입력 차단"""

    if value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to 0")


def _validate_positive_int(value: int, field_name: str) -> None:
    """양수 정수 입력 검증"""

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than 0")


def _validate_non_negative_float(value: float, field_name: str) -> None:
    """음수 실수 입력 차단"""

    if value < 0.0:
        raise ValueError(f"{field_name} must be greater than or equal to 0")


def _validate_option_value(option_spec: OptionSpec, value: float) -> None:
    """옵션 수치 범위 검증"""

    if (
        value < option_spec.value_range.minimum
        or value > option_spec.value_range.maximum
    ):
        raise ValueError(
            f"option value must be between {option_spec.value_range.minimum} and "
            f"{option_spec.value_range.maximum}"
        )


def _talisman_spec_map() -> dict[str, TalismanSpec]:
    """부적 이름 기준 스펙 맵 구성"""

    return {spec.name: spec for spec in TALISMAN_SPECS}


def _new_id() -> str:
    """새 저장 식별자 생성"""

    return str(uuid4())


def _equipment_slots(kind: EquipmentKind) -> tuple[EquipmentSlot, ...]:
    """장비 종류별 장착 가능 슬롯 조회"""

    return EQUIPMENT_KIND_SLOTS[kind]


def _equipment_primary_slot(equipment: OwnedEquipment) -> EquipmentSlot:
    """장비 종류 기준 검증 대표 슬롯 조회"""

    return _equipment_slots(equipment.kind)[0]


def equipment_item_spec(equipment: OwnedEquipment) -> EquipmentItemSpec | None:
    """장비 입력값 기준 정적 아이템 스펙 조회"""

    if equipment.kind in (EquipmentKind.RING, EquipmentKind.EARRING):
        return None

    for item_spec in EQUIPMENT_ITEM_SPECS:
        if equipment.kind == EquipmentKind.NECKLACE:
            if (
                item_spec.name == equipment.item_name
                and EquipmentSlot.NECKLACE in item_spec.slots
            ):
                return item_spec

            continue

        if (
            equipment.level == item_spec.level
            and equipment.tier == item_spec.tier
            and _equipment_primary_slot(equipment) in item_spec.slots
        ):
            return item_spec

    raise ValueError("equipment item spec does not exist")


def _validate_distribution(profile: CharacterProfile) -> None:
    """스탯 분배와 단전 분배 검증"""

    _validate_non_negative_int(profile.level, "level")

    distribution_total: int = (
        profile.distribution.strength
        + profile.distribution.dexterity
        + profile.distribution.vitality
        + profile.distribution.luck
    )
    for value in (
        profile.distribution.strength,
        profile.distribution.dexterity,
        profile.distribution.vitality,
        profile.distribution.luck,
    ):
        _validate_non_negative_int(value, "stat distribution")

    if distribution_total > profile.level * 5:
        raise ValueError("stat distribution exceeds level point cap")

    danjeon_total: int = (
        profile.danjeon.upper + profile.danjeon.middle + profile.danjeon.lower
    )
    for value in (
        profile.danjeon.upper,
        profile.danjeon.middle,
        profile.danjeon.lower,
    ):
        _validate_non_negative_int(value, "danjeon distribution")

    realm_cap: int = REALM_TIER_SPECS[profile.realm].danjeon_points
    if danjeon_total > realm_cap:
        raise ValueError("danjeon distribution exceeds realm point cap")


def _validate_equipped(profile: CharacterProfile) -> None:
    """장착 참조 무결성 검증"""

    title_ids: set[str] = {title.id for title in profile.titles}
    if (
        profile.equipped.title_id is not None
        and profile.equipped.title_id not in title_ids
    ):
        raise ValueError("equipped title id does not exist")

    talisman_ids: set[str] = {talisman.id for talisman in profile.talismans}
    talisman_key_by_id: dict[str, str] = {
        talisman.id: talisman.talisman_key for talisman in profile.talismans
    }
    if len(profile.equipped.talisman_ids) > MAX_EQUIPPED_TALISMAN_COUNT:
        raise ValueError("equipped talismans exceed slot count")

    if len(profile.equipped.talisman_ids) != len(set(profile.equipped.talisman_ids)):
        raise ValueError("equipped talisman ids must be unique")

    for talisman_id in profile.equipped.talisman_ids:
        if talisman_id not in talisman_ids:
            raise ValueError("equipped talisman id does not exist")

    equipped_talisman_keys: list[str] = [
        talisman_key_by_id[talisman_id] for talisman_id in profile.equipped.talisman_ids
    ]
    if len(equipped_talisman_keys) != len(set(equipped_talisman_keys)):
        raise ValueError("equipped talisman keys must be unique")


def _validate_titles(profile: CharacterProfile) -> None:
    """칭호 입력 검증"""

    title_ids: set[str] = set()
    for title in profile.titles:
        if title.id in title_ids:
            raise ValueError("title ids must be unique")

        title_ids.add(title.id)
        for slot in title.slots:
            if slot is None:
                continue

            _validate_non_negative_float(slot.value, "title stat value")


def _validate_talismans(profile: CharacterProfile) -> None:
    """부적 입력 검증"""

    talisman_ids: set[str] = set()
    talisman_keys: set[str] = set()
    talisman_specs: dict[str, TalismanSpec] = _talisman_spec_map()
    for talisman in profile.talismans:
        if talisman.id in talisman_ids:
            raise ValueError("talisman ids must be unique")

        talisman_ids.add(talisman.id)
        if talisman.talisman_key not in talisman_specs:
            raise ValueError("talisman key does not exist")

        if talisman.talisman_key in talisman_keys:
            raise ValueError("talisman keys must be unique")

        talisman_keys.add(talisman.talisman_key)
        if talisman.level < 0 or talisman.level > MAX_TALISMAN_LEVEL:
            raise ValueError("talisman level is out of range")


def _validate_equipment_item_identity(
    equipment: OwnedEquipment,
    item_spec: EquipmentItemSpec | None,
) -> None:
    """보유 장비 종류와 정적 스펙 검증"""

    if not equipment.name.strip():
        raise ValueError("equipment name is required")

    if equipment.kind in (EquipmentKind.RING, EquipmentKind.EARRING):
        if equipment.item_name is not None:
            raise ValueError("free base stat equipment cannot reference item catalog")

        if equipment.level != 0:
            raise ValueError("free base stat equipment level must be 0")

        if equipment.tier != 1:
            raise ValueError("free base stat equipment tier must be 1")

        if equipment.grade is not None:
            raise ValueError("free base stat equipment cannot have grade")

        return

    if item_spec is None:
        raise ValueError("equipment item spec is required")

    if equipment.kind == EquipmentKind.NECKLACE:
        if equipment.item_name != item_spec.name:
            raise ValueError("necklace item name does not match item spec")

    else:
        if equipment.item_name is not None:
            raise ValueError("non-necklace catalog equipment cannot store item name")

    if equipment.kind in (
        EquipmentKind.HELMET,
        EquipmentKind.ARMOR,
        EquipmentKind.BELT,
        EquipmentKind.SHOES,
        EquipmentKind.WEAPON,
    ):
        if equipment.grade not in item_spec.grade_stats:
            raise ValueError("equipment grade is required")

        return

    if equipment.grade is not None:
        raise ValueError("equipment grade must be empty")


def _validate_equipment_options(slot: EquipmentSlot, equipment: OwnedEquipment) -> None:
    """장비 잠재능력과 추가능력 검증"""

    if len(equipment.potentials) != EQUIPMENT_OPTION_SLOT_COUNT:
        raise ValueError("potential lines must have exactly 3 items")

    if len(equipment.additionals) != EQUIPMENT_OPTION_SLOT_COUNT:
        raise ValueError("additional lines must have exactly 3 items")

    if slot not in POTENTIAL_EQUIPMENT_SLOTS:
        if any(line is not None for line in equipment.potentials):
            raise ValueError("potential lines are allowed only for armor slots")

        if any(line is not None for line in equipment.additionals):
            raise ValueError("additional lines are allowed only for armor slots")

        return

    potential_line: PotentialLine | None
    for potential_line in equipment.potentials:
        if potential_line is None:
            continue

        _validate_option_value(
            POTENTIAL_OPTION_SPECS[potential_line.option],
            potential_line.value,
        )

    additional_line: AdditionalLine | None
    for additional_line in equipment.additionals:
        if additional_line is None:
            continue

        _validate_option_value(
            ADDITIONAL_OPTION_SPECS[additional_line.option],
            additional_line.value,
        )


def _allowed_reforge_stat_keys(
    slot: EquipmentSlot,
    equipment: OwnedEquipment,
) -> tuple[StatKey, ...]:
    """장비 재련 입력 가능 스탯 조회"""

    if slot == EquipmentSlot.NECKLACE:
        if equipment.item_name is None:
            raise ValueError("necklace item name is required")

        return NECKLACE_REFORGE_STAT_KEYS[equipment.item_name]

    return EQUIPMENT_REFORGE_STAT_KEYS[slot]


def _validate_equipment_reforge(slot: EquipmentSlot, equipment: OwnedEquipment) -> None:
    """장비 재련 입력값 검증"""

    _validate_non_negative_int(equipment.reforge_step, "reforge step")
    if equipment.reforge_step > MAX_REFORGE_STEP:
        raise ValueError("reforge step exceeds maximum")

    allowed_stat_keys: tuple[StatKey, ...] = _allowed_reforge_stat_keys(slot, equipment)
    for stat_key, value in equipment.reforge_stats.items():
        if stat_key not in allowed_stat_keys:
            raise ValueError("reforge stat is not allowed for this equipment")

        _validate_non_negative_float(value, "reforge stat value")


def _validate_equipment_scrolls(
    slot: EquipmentSlot,
    equipment: OwnedEquipment,
    item_spec: EquipmentItemSpec | None,
) -> None:
    """장비 주문서 입력값 검증"""

    total_count: int = 0
    seen_scrolls: set[tuple[StatKey, ScrollTier]] = set()
    allowed_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = (
        EQUIPMENT_SCROLL_EFFECTS[slot]
    )
    for scroll in equipment.scrolls:
        if scroll.stat_key not in allowed_effects:
            raise ValueError("scroll stat is not allowed for this equipment")

        if scroll.tier not in allowed_effects[scroll.stat_key]:
            raise ValueError("scroll tier is not allowed for this equipment stat")

        scroll_key: tuple[StatKey, ScrollTier] = (scroll.stat_key, scroll.tier)
        if scroll_key in seen_scrolls:
            raise ValueError("scroll line must be unique")

        seen_scrolls.add(scroll_key)
        _validate_positive_int(scroll.count, "scroll count")
        total_count += scroll.count

    limit_map: dict[int, int] | None = EQUIPMENT_SCROLL_LIMITS[slot]
    if limit_map is None:
        return

    if total_count == 0:
        return

    if item_spec is None:
        raise ValueError("scroll-limited equipment requires item spec")

    if item_spec.level not in limit_map:
        raise ValueError("scroll limit does not exist for equipment level")

    if total_count > limit_map[item_spec.level]:
        raise ValueError("scroll count exceeds equipment limit")


def _validate_equipment(equipment: OwnedEquipment) -> None:
    """장비 입력 상태 검증"""

    slot: EquipmentSlot = _equipment_primary_slot(equipment)
    item_spec: EquipmentItemSpec | None = equipment_item_spec(equipment)
    _validate_equipment_item_identity(equipment, item_spec)

    if (
        equipment.kind not in (EquipmentKind.RING, EquipmentKind.EARRING)
        and equipment.base_stat_lines
    ):
        raise ValueError("base stat lines are allowed only for ring or earring")

    for line in equipment.base_stat_lines:
        _validate_non_negative_float(line.value, "equipment base stat value")

    _validate_equipment_options(slot, equipment)
    _validate_equipment_reforge(slot, equipment)
    _validate_equipment_scrolls(slot, equipment, item_spec)


def _validate_equipment_state(profile: CharacterProfile) -> None:
    """캐릭터 장비 전체 검증"""

    equipment_by_name: dict[str, OwnedEquipment] = {}
    for equipment in profile.equipment.owned:
        if equipment.name in equipment_by_name:
            raise ValueError("equipment names must be unique")

        equipment_by_name[equipment.name] = equipment
        _validate_equipment(equipment)

    equipped_names: list[str] = []
    for slot in EquipmentSlot:
        equipment_name: str | None = profile.equipment.equipped[slot]
        if equipment_name is None:
            continue

        if equipment_name not in equipment_by_name:
            raise ValueError("equipped equipment name does not exist")

        if equipment_name in equipped_names:
            raise ValueError("same equipment cannot be equipped twice")

        equipped_names.append(equipment_name)
        equipment: OwnedEquipment = equipment_by_name[equipment_name]
        if slot not in _equipment_slots(equipment.kind):
            raise ValueError("equipment cannot be equipped in this slot")


def _validate_display_stand(profile: CharacterProfile) -> None:
    """진열대 입력값 검증"""

    for entry in profile.display_stand.entries.values():
        for column, value in entry.items():
            if column not in DISPLAY_STAND_COLUMN_STAT_KEYS:
                raise ValueError("display stand column is not supported")

            _validate_non_negative_float(value, "display stand value")


def _validate_consumables(profile: CharacterProfile) -> None:
    """영단과 환 입력값 검증"""

    for elixir, count in profile.elixir.counts.items():
        if elixir not in ELIXIR_SPECS:
            raise ValueError("elixir is not supported")

        if count < 0 or count > MAX_ELIXIR_COUNT:
            raise ValueError("elixir count is out of range")

    for pill in profile.pill.active:
        if pill not in PILL_SPECS:
            raise ValueError("pill is not supported")


def validate_character_profile(profile: CharacterProfile) -> None:
    """캐릭터 프로필 전체 검증"""

    _validate_distribution(profile)
    _validate_titles(profile)
    _validate_talismans(profile)
    _validate_equipped(profile)
    _validate_equipment_state(profile)
    _validate_display_stand(profile)
    _validate_consumables(profile)


def validate_character_store(store: CharacterStore) -> None:
    """캐릭터 저장 루트 검증"""

    if store.version > CHARACTER_DATA_VERSION:
        raise ValueError("character data version is newer than supported")

    if not store.characters:
        if store.selected_index != -1:
            raise ValueError("empty character store must select -1")

        return

    if not (0 <= store.selected_index < len(store.characters)):
        raise ValueError("selected character index is out of range")

    character_ids: set[str] = set()
    for character in store.characters:
        if character.id in character_ids:
            raise ValueError("character ids must be unique")

        character_ids.add(character.id)
        validate_character_profile(character)


def _ensure_unique_owned_names(profile: CharacterProfile) -> None:
    """보유 장비 이름 유일성 검증"""

    seen: set[str] = set()
    for equipment in profile.equipment.owned:
        if equipment.name in seen:
            raise ValueError("equipment names must be unique")

        seen.add(equipment.name)


def _equipment_by_name(profile: CharacterProfile) -> dict[str, OwnedEquipment]:
    """장비 이름 기준 보유 장비 맵 구성"""

    _ensure_unique_owned_names(profile)
    return {equipment.name: equipment for equipment in profile.equipment.owned}


def list_equippable_equipment(
    profile: CharacterProfile,
    slot: EquipmentSlot,
) -> list[OwnedEquipment]:
    """슬롯에 장착 가능한 보유 장비 목록 반환"""

    _ensure_unique_owned_names(profile)
    return [
        equipment
        for equipment in profile.equipment.owned
        if slot in _equipment_slots(equipment.kind)
    ]


def create_equipment(
    profile: CharacterProfile,
    equipment: OwnedEquipment,
) -> OwnedEquipment:
    """보유 장비 추가"""

    equipment_by_name: dict[str, OwnedEquipment] = _equipment_by_name(profile)
    if equipment.name in equipment_by_name:
        raise ValueError("equipment names must be unique")

    _validate_equipment(equipment)
    profile.equipment.owned.append(equipment)
    return equipment


def equip_equipment(
    profile: CharacterProfile,
    slot: EquipmentSlot,
    equipment_name: str,
) -> None:
    """보유 장비를 슬롯에 장착"""

    equipment_by_name: dict[str, OwnedEquipment] = _equipment_by_name(profile)
    equipment: OwnedEquipment = equipment_by_name[equipment_name]
    if slot not in _equipment_slots(equipment.kind):
        raise ValueError("equipment cannot be equipped in this slot")

    profile.equipment.equipped[slot] = equipment_name


def unequip_equipment(profile: CharacterProfile, slot: EquipmentSlot) -> None:
    """슬롯 장비 장착 해제"""

    profile.equipment.equipped[slot] = None


def remove_equipment(profile: CharacterProfile, equipment_name: str) -> None:
    """보유 장비 삭제 및 장착 참조 정리"""

    if all(equipment.name != equipment_name for equipment in profile.equipment.owned):
        raise ValueError("equipment does not exist")

    profile.equipment.owned = [
        equipment
        for equipment in profile.equipment.owned
        if equipment.name != equipment_name
    ]
    for slot, equipped_name in profile.equipment.equipped.items():
        if equipped_name != equipment_name:
            continue

        profile.equipment.equipped[slot] = None


def rename_equipment(
    profile: CharacterProfile,
    old_name: str,
    new_name: str,
) -> None:
    """보유 장비 이름 변경 및 장착 참조 갱신"""

    if not new_name.strip():
        raise ValueError("equipment name is required")

    equipment_by_name: dict[str, OwnedEquipment] = _equipment_by_name(profile)
    equipment: OwnedEquipment = equipment_by_name[old_name]
    if new_name != old_name and new_name in equipment_by_name:
        raise ValueError("equipment names must be unique")

    equipment.name = new_name
    for slot, equipped_name in profile.equipment.equipped.items():
        if equipped_name != old_name:
            continue

        profile.equipment.equipped[slot] = new_name


def duplicate_equipment(
    profile: CharacterProfile,
    source_name: str,
    new_name: str,
) -> OwnedEquipment:
    """보유 장비 복제"""

    if not new_name.strip():
        raise ValueError("equipment name is required")

    equipment_by_name: dict[str, OwnedEquipment] = _equipment_by_name(profile)
    if new_name in equipment_by_name:
        raise ValueError("equipment names must be unique")

    source: OwnedEquipment = equipment_by_name[source_name]
    duplicated: OwnedEquipment = OwnedEquipment.from_dict(source.to_dict())
    duplicated.name = new_name
    profile.equipment.owned.append(duplicated)
    return duplicated


def _add_distribution(
    accumulated: dict[StatKey, float],
    distribution: StatDistribution,
) -> None:
    """스탯 분배 기여 누적"""

    _add_stat(accumulated, StatKey.STR, float(distribution.strength))
    _add_stat(accumulated, StatKey.DEXTERITY, float(distribution.dexterity))
    _add_stat(accumulated, StatKey.VITALITY, float(distribution.vitality))
    _add_stat(accumulated, StatKey.LUCK, float(distribution.luck))


def _add_danjeon(
    accumulated: dict[StatKey, float],
    danjeon: DanjeonDistribution,
) -> None:
    """단전 분배 기여 누적"""

    _add_stat(accumulated, StatKey.HP_PERCENT, float(danjeon.upper * 3))
    _add_stat(accumulated, StatKey.RESIST_PERCENT, float(danjeon.upper))
    _add_stat(accumulated, StatKey.ATTACK_PERCENT, float(danjeon.middle))
    _add_stat(accumulated, StatKey.DROP_RATE_PERCENT, float(danjeon.lower * 1.5))
    _add_stat(accumulated, StatKey.EXP_PERCENT, float(danjeon.lower * 0.5))


def _add_equipped_title(
    accumulated: dict[StatKey, float],
    profile: CharacterProfile,
) -> None:
    """장착 칭호 기여 누적"""

    if profile.equipped.title_id is None:
        return

    title_by_id: dict[str, CharacterTitle] = {
        title.id: title for title in profile.titles
    }
    equipped_title: CharacterTitle = title_by_id[profile.equipped.title_id]
    for slot in equipped_title.slots:
        if slot is None:
            continue

        _add_stat(accumulated, slot.stat_key, slot.value)


def _add_equipped_talismans(
    accumulated: dict[StatKey, float],
    profile: CharacterProfile,
) -> None:
    """장착 부적 기여 누적"""

    talisman_by_id: dict[str, CharacterTalisman] = {
        talisman.id: talisman for talisman in profile.talismans
    }
    talisman_spec_by_name: dict[str, TalismanSpec] = _talisman_spec_map()
    for talisman_id in profile.equipped.talisman_ids:
        talisman: CharacterTalisman = talisman_by_id[talisman_id]
        talisman_spec: TalismanSpec = talisman_spec_by_name[talisman.talisman_key]
        _add_stat(
            accumulated,
            talisman_spec.stat_key,
            talisman_spec.level_stats[talisman.level],
        )


def _add_equipment_base_stats(
    accumulated: dict[StatKey, float],
    slot: EquipmentSlot,
    equipment: OwnedEquipment,
) -> None:
    """장비 기본 스탯 기여 누적"""

    for line in equipment.base_stat_lines:
        _add_stat(accumulated, line.stat_key, line.value)

    item_spec: EquipmentItemSpec | None = equipment_item_spec(equipment)
    if item_spec is None:
        return

    grade_key: EquipmentGrade | None = equipment.grade
    _merge_stats(accumulated, item_spec.grade_stats[grade_key])

    if slot not in ARMOR_EQUIPMENT_SLOTS:
        return

    armor_stat_key: StatKey = ARMOR_SLOT_STAT_KEYS[slot]
    armor_stat_value: float = item_spec.armor_stat_values[equipment.grade]
    _add_stat(accumulated, armor_stat_key, armor_stat_value)


def _add_equipment_reforge(
    accumulated: dict[StatKey, float],
    equipment: OwnedEquipment,
) -> None:
    """장비 재련 스탯 기여 누적"""

    _merge_stats(accumulated, equipment.reforge_stats)


def _add_equipment_scrolls(
    accumulated: dict[StatKey, float],
    slot: EquipmentSlot,
    equipment: OwnedEquipment,
) -> None:
    """장비 주문서 기여 누적"""

    slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = (
        EQUIPMENT_SCROLL_EFFECTS[slot]
    )
    for scroll in equipment.scrolls:
        _merge_stats(
            accumulated,
            slot_effects[scroll.stat_key][scroll.tier],
            multiplier=float(scroll.count),
        )


def _add_equipment_options(
    accumulated: dict[StatKey, float],
    equipment: OwnedEquipment,
) -> None:
    """장비 잠재능력과 추가능력 기여 누적"""

    for potential in equipment.potentials:
        if potential is None:
            continue

        potential_spec: OptionSpec = POTENTIAL_OPTION_SPECS[potential.option]
        _add_stat(accumulated, potential_spec.stat_key, potential.value)

    for additional in equipment.additionals:
        if additional is None:
            continue

        additional_spec: OptionSpec = ADDITIONAL_OPTION_SPECS[additional.option]
        _add_stat(accumulated, additional_spec.stat_key, additional.value)


def _add_equipment(
    accumulated: dict[StatKey, float],
    profile: CharacterProfile,
) -> None:
    """장비 전체 기여 누적"""

    equipment_by_name: dict[str, OwnedEquipment] = _equipment_by_name(profile)
    for slot, equipment_name in profile.equipment.equipped.items():
        if equipment_name is None:
            continue

        equipment: OwnedEquipment = equipment_by_name[equipment_name]
        _add_equipment_base_stats(accumulated, slot, equipment)
        _add_equipment_reforge(accumulated, equipment)
        _add_equipment_scrolls(accumulated, slot, equipment)
        _add_equipment_options(accumulated, equipment)


def _add_display_stand(
    accumulated: dict[StatKey, float],
    profile: CharacterProfile,
) -> None:
    """진열대 기여 누적"""

    for entry in profile.display_stand.entries.values():
        for column, value in entry.items():
            for stat_key in DISPLAY_STAND_COLUMN_STAT_KEYS[column]:
                _add_stat(accumulated, stat_key, value)


def _add_consumables(
    accumulated: dict[StatKey, float],
    profile: CharacterProfile,
) -> None:
    """영단과 환 기여 누적"""

    for elixir, count in profile.elixir.counts.items():
        _merge_stats(accumulated, ELIXIR_SPECS[elixir].effects, multiplier=float(count))

    for pill in profile.pill.active:
        _merge_stats(accumulated, PILL_SPECS[pill].effects)


def _accumulate_base_stats(profile: CharacterProfile) -> dict[StatKey, float]:
    """검증 없이 캐릭터 입력 기여를 원시 스탯 맵으로 합산"""

    accumulated: dict[StatKey, float] = _character_base_stat_map(profile)
    _add_distribution(accumulated, profile.distribution)
    _add_danjeon(accumulated, profile.danjeon)
    _add_equipped_title(accumulated, profile)
    _add_equipped_talismans(accumulated, profile)
    _add_equipment(accumulated, profile)
    _add_display_stand(accumulated, profile)
    _add_consumables(accumulated, profile)
    return accumulated


def aggregate_base_stats(profile: CharacterProfile) -> BaseStats:
    """캐릭터 입력값으로부터 원시 스탯 합산"""

    validate_character_profile(profile)
    return BaseStats.from_stat_map(_accumulate_base_stats(profile))


def compute_live_view(profile: CharacterProfile) -> LiveStatView:
    """캐릭터 실시간 최종 스탯과 공식 전투력 계산"""

    base_stats: BaseStats = aggregate_base_stats(profile)
    final_stats: FinalStats = base_stats.resolve()
    official_power: float = evaluate_official_power(final_stats)
    return LiveStatView(
        base=base_stats,
        final=final_stats,
        official_power=official_power,
    )


def build_calculator_input_fill(
    profile: CharacterProfile,
) -> CalculatorInputFill:
    """캐릭터 상태 기반 계산기 입력 페이지 반영값 생성"""

    # 캐릭터 전체 합산 결과에서 최종 스탯 맵 추출
    overall_stats: dict[StatKey, float] = compute_live_view(profile).final.values.copy()

    # 계산기 스탯 분배 입력값 구성
    distribution: DistributionState = DistributionState(
        strength=profile.distribution.strength,
        dexterity=profile.distribution.dexterity,
        vitality=profile.distribution.vitality,
        luck=profile.distribution.luck,
        is_locked=False,
        use_reset=False,
    )

    # 계산기 단전 분배 입력값 구성
    danjeon: DanjeonState = DanjeonState(
        upper=profile.danjeon.upper,
        middle=profile.danjeon.middle,
        lower=profile.danjeon.lower,
        is_locked=False,
        use_reset=False,
    )

    # 계산기 칭호·부적 입력 초기값 구성
    owned_titles: list[OwnedTitle] = []
    owned_talismans: list[OwnedTalisman] = []
    equipped_state: EquippedState = EquippedState()
    return CalculatorInputFill(
        overall_stats=overall_stats,
        level=profile.level,
        realm_tier=profile.realm,
        distribution=distribution,
        danjeon=danjeon,
        owned_titles=owned_titles,
        owned_talismans=owned_talismans,
        equipped_state=equipped_state,
    )


def optimize_danjeon(profile: CharacterProfile) -> DanjeonDistribution:
    """단전 분배 자동 설정 (중단전 공격력% 집중 고정)"""

    total_points: int = REALM_TIER_SPECS[profile.realm].danjeon_points
    return DanjeonDistribution(
        upper=0,
        middle=total_points,
        lower=0,
    )


def clamp_profile_allocations(profile: CharacterProfile) -> None:
    """레벨·경지 한도 기준 분배 초과값 정리"""

    remaining_stat_points: int = profile.level * 5
    profile.distribution.strength = min(
        profile.distribution.strength,
        remaining_stat_points,
    )
    remaining_stat_points -= profile.distribution.strength
    profile.distribution.dexterity = min(
        profile.distribution.dexterity,
        remaining_stat_points,
    )
    remaining_stat_points -= profile.distribution.dexterity
    profile.distribution.vitality = min(
        profile.distribution.vitality,
        remaining_stat_points,
    )
    remaining_stat_points -= profile.distribution.vitality
    profile.distribution.luck = min(
        profile.distribution.luck,
        remaining_stat_points,
    )

    remaining_danjeon_points: int = REALM_TIER_SPECS[profile.realm].danjeon_points
    profile.danjeon.upper = min(profile.danjeon.upper, remaining_danjeon_points)
    remaining_danjeon_points -= profile.danjeon.upper
    profile.danjeon.middle = min(profile.danjeon.middle, remaining_danjeon_points)
    remaining_danjeon_points -= profile.danjeon.middle
    profile.danjeon.lower = min(profile.danjeon.lower, remaining_danjeon_points)


def _final_stats_with_distribution(
    fixed_stats: dict[StatKey, float],
    distribution: StatDistribution,
) -> FinalStats:
    """고정 기여값에 후보 분배를 적용한 최종 스탯 계산"""

    candidate_stats: dict[StatKey, float] = fixed_stats.copy()
    _add_distribution(candidate_stats, distribution)
    return BaseStats.from_stat_map(candidate_stats).resolve()


def _damage_score(final_stats: FinalStats) -> float:
    """스탯 분배 비교용 데미지 점수"""

    values: dict[StatKey, float] = final_stats.values
    return values[StatKey.ATTACK] * (
        1.0
        + values[StatKey.CRIT_RATE_PERCENT]
        * (values[StatKey.CRIT_DAMAGE_PERCENT] - 100.0)
        / 10000.0
    )


def optimize_stat_distribution(profile: CharacterProfile) -> StatDistribution:
    """자동 최적화 전용 데미지 기준 스탯 분배 최적화"""

    validate_character_profile(profile)

    # 후보마다 변하지 않는 캐릭터 기여값 사전 합산
    fixed_profile: CharacterProfile = replace(
        profile,
        distribution=StatDistribution(),
    )
    fixed_stats: dict[StatKey, float] = _accumulate_base_stats(fixed_profile)

    # 동점일 때 힘 우선 결과를 유지하기 위한 초기 후보 구성
    total_points: int = profile.level * 5
    best_distribution: StatDistribution = StatDistribution(
        strength=total_points,
        dexterity=0,
        vitality=0,
        luck=0,
    )
    best_damage_score: float = _damage_score(
        _final_stats_with_distribution(fixed_stats, best_distribution)
    )

    # 힘과 민첩의 전체 배분 조합별 최종 스탯 평가
    for strength in range(total_points - 1, -1, -1):
        candidate: StatDistribution = StatDistribution(
            strength=strength,
            dexterity=total_points - strength,
            vitality=0,
            luck=0,
        )
        damage_score: float = _damage_score(
            _final_stats_with_distribution(fixed_stats, candidate)
        )

        # 더 높은 데미지 후보 반영
        if damage_score > best_damage_score:
            best_distribution = candidate
            best_damage_score = damage_score

    return best_distribution


def clone_character_profile(profile: CharacterProfile) -> CharacterProfile:
    """캐릭터 복제본 생성"""

    return _regenerate_character_ids(profile)


def serialize_character_profile(profile: CharacterProfile) -> str:
    """캐릭터 클립보드용 JSON 문자열 생성"""

    validate_character_profile(profile)
    return json.dumps(profile.to_dict(), ensure_ascii=False, indent=4)


def deserialize_character_profile(payload: str) -> CharacterProfile:
    """클립보드 JSON 문자열로부터 새 캐릭터 복원"""

    raw_data: Any = json.loads(payload)
    if not isinstance(raw_data, dict):
        raise TypeError("character payload must be a dict")

    profile: CharacterProfile = CharacterProfile.from_dict(raw_data)
    regenerated_profile: CharacterProfile = _regenerate_character_ids(profile)
    validate_character_profile(regenerated_profile)
    return regenerated_profile


def _regenerate_character_ids(profile: CharacterProfile) -> CharacterProfile:
    """복제 캐릭터의 내부 식별자 재발급"""

    # 저장 구조 왕복을 통한 독립 복제본 구성
    cloned: CharacterProfile = CharacterProfile.from_dict(profile.to_dict())

    # 칭호 식별자 재발급 및 장착 참조 매핑 준비
    title_id_map: dict[str, str] = {}
    for title in cloned.titles:
        old_id: str = title.id
        title.id = _new_id()
        title_id_map[old_id] = title.id

    # 부적 식별자 재발급 및 장착 참조 매핑 준비
    talisman_id_map: dict[str, str] = {}
    for talisman in cloned.talismans:
        old_id: str = talisman.id
        talisman.id = _new_id()
        talisman_id_map[old_id] = talisman.id

    # 프로필 식별자 재발급
    cloned.id = _new_id()

    # 장착 칭호 참조를 재발급된 식별자로 교체
    if cloned.equipped.title_id is not None:
        cloned.equipped.title_id = title_id_map[cloned.equipped.title_id]

    # 장착 부적 참조를 재발급된 식별자로 교체
    cloned.equipped.talisman_ids = [
        talisman_id_map[talisman_id] for talisman_id in cloned.equipped.talisman_ids
    ]
    return cloned
