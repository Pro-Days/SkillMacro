from __future__ import annotations

import pytest

from app.scripts.calculator_models import REALM_TIER_SPECS, RealmTier, StatKey
from app.scripts.character_engine import (
    CHARACTER_BASE_HP,
    CHARACTER_HP_PER_LEVEL,
    CalculatorInputFill,
    LiveStatView,
    build_calculator_input_fill,
    clamp_profile_allocations,
    clone_character_profile,
    compute_live_view,
    create_equipment,
    deserialize_character_profile,
    duplicate_equipment,
    equip_equipment,
    optimize_danjeon,
    optimize_stat_distribution,
    remove_equipment,
    rename_equipment,
    serialize_character_profile,
    unequip_equipment,
    validate_character_profile,
    validate_character_store,
)
from app.scripts.character_models import (
    AdditionalStatGroup,
    AdditionalStatLine,
    CharacterProfile,
    CharacterStore,
    CharacterTalisman,
    CharacterTitle,
    DanjeonDistribution,
    EquipmentFreeStatLine,
    EquipmentKind,
    EquipmentSlot,
    OwnedEquipment,
    StatDistribution,
    TitleStatSlot,
    TALISMAN_SPECS,
)


@pytest.fixture
def basic_profile() -> CharacterProfile:
    """검증 통과 기준 기본 캐릭터 프로필"""

    return CharacterProfile(
        name="테스트 캐릭터",
        level=10,
        realm=RealmTier.SECOND_RATE,
        distribution=StatDistribution(strength=10, dexterity=5, vitality=3, luck=2),
        danjeon=DanjeonDistribution(upper=1, middle=1, lower=0),
    )


def test_default_store_passes_validation() -> None:
    """기본 캐릭터 저장소의 검증 통과 확인"""

    validate_character_store(CharacterStore.create_default())


def test_basic_profile_passes_validation(basic_profile: CharacterProfile) -> None:
    """기본 입력 프로필의 검증 통과 확인"""

    validate_character_profile(basic_profile)


def test_distribution_over_level_cap_is_rejected(
    basic_profile: CharacterProfile,
) -> None:
    """레벨 한도 초과 스탯 분배의 명시적 거부 검증"""

    # 레벨 10 한도(50포인트) 초과 분배 구성
    basic_profile.distribution.strength = 51

    with pytest.raises(ValueError):
        validate_character_profile(basic_profile)


def test_negative_distribution_is_rejected(basic_profile: CharacterProfile) -> None:
    """음수 스탯 분배의 명시적 거부 검증"""

    basic_profile.distribution.luck = -1

    with pytest.raises(ValueError):
        validate_character_profile(basic_profile)


def test_danjeon_over_realm_cap_is_rejected(basic_profile: CharacterProfile) -> None:
    """경지 한도 초과 단전 분배의 명시적 거부 검증"""

    # 이류 한도(2포인트) 초과 단전 구성
    basic_profile.danjeon.middle = 3

    with pytest.raises(ValueError):
        validate_character_profile(basic_profile)


def test_unknown_equipped_title_is_rejected(basic_profile: CharacterProfile) -> None:
    """미보유 칭호 장착 참조의 명시적 거부 검증"""

    basic_profile.equipped.title_id = "missing-title-id"

    with pytest.raises(ValueError):
        validate_character_profile(basic_profile)


def test_unknown_talisman_key_is_rejected(basic_profile: CharacterProfile) -> None:
    """존재하지 않는 부적 종류의 명시적 거부 검증"""

    basic_profile.talismans.append(CharacterTalisman(talisman_key="없는부적", level=1))

    with pytest.raises(ValueError):
        validate_character_profile(basic_profile)


def test_unknown_equipped_talisman_is_rejected(
    basic_profile: CharacterProfile,
) -> None:
    """미보유 부적 장착 참조의 명시적 거부 검증"""

    basic_profile.equipped.talisman_ids.append("missing-talisman-id")

    with pytest.raises(ValueError):
        validate_character_profile(basic_profile)


def test_compute_live_view_validates_first(basic_profile: CharacterProfile) -> None:
    """실시간 스탯 계산 진입 시 프로필 검증 선행 확인"""

    basic_profile.distribution.strength = 9999

    with pytest.raises(ValueError):
        compute_live_view(basic_profile)


def test_live_view_aggregates_inputs_hand_computed(
    basic_profile: CharacterProfile,
) -> None:
    """캐릭터 입력 합산 결과의 손계산 값 일치 검증

    기본 체력 = 50 + 레벨 * 5
    단전: 상단전 체력% +3/저항% +1, 중단전 공격력% +1
    칭호: 슬롯 스탯 그대로 합산, 추가 스탯: 같은 그룹의 중복 스탯도 합산
    VIP: 드랍률% +3
    """

    # 공격력 +100, 보스 공격력% +5 칭호 장착 구성
    title: CharacterTitle = CharacterTitle(
        name="테스트 칭호",
        slots=(
            TitleStatSlot(stat_key=StatKey.ATTACK, value=100.0),
            TitleStatSlot(stat_key=StatKey.BOSS_ATTACK_PERCENT, value=5.0),
            None,
        ),
    )
    basic_profile.titles.append(title)
    basic_profile.equipped.title_id = title.id
    basic_profile.additional_stat_groups.append(
        AdditionalStatGroup(
            name="기타",
            stats=[
                AdditionalStatLine(stat_key=StatKey.ATTACK, value=20.0),
                AdditionalStatLine(stat_key=StatKey.ATTACK, value=30.0),
            ],
        )
    )
    basic_profile.vip = True

    live: LiveStatView = compute_live_view(basic_profile)
    base_values: dict[str, float] = live.base.values

    # 레벨 기반 기본 체력 확인
    assert base_values[StatKey.HP.value] == pytest.approx(
        CHARACTER_BASE_HP + basic_profile.level * CHARACTER_HP_PER_LEVEL
    )

    # 스탯 분배 반영 확인
    assert base_values[StatKey.STR.value] == pytest.approx(10.0)
    assert base_values[StatKey.DEXTERITY.value] == pytest.approx(5.0)
    assert base_values[StatKey.VITALITY.value] == pytest.approx(3.0)
    assert base_values[StatKey.LUCK.value] == pytest.approx(2.0)

    # 단전 반영 확인 (상단전 1, 중단전 1)
    assert base_values[StatKey.HP_PERCENT.value] == pytest.approx(3.0)
    assert base_values[StatKey.RESIST_PERCENT.value] == pytest.approx(1.0)
    assert base_values[StatKey.ATTACK_PERCENT.value] == pytest.approx(1.0)

    # 칭호와 같은 그룹 내 중복 추가 스탯, VIP 반영 확인
    assert base_values[StatKey.ATTACK.value] == pytest.approx(150.0)
    assert base_values[StatKey.BOSS_ATTACK_PERCENT.value] == pytest.approx(5.0)
    assert base_values[StatKey.DROP_RATE_PERCENT.value] == pytest.approx(3.0)

    # 최종 스탯의 resolve 일관성과 공식 전투력 양수 확인
    assert live.final.values == live.base.resolve().values
    assert live.official_power > 0.0


def test_calculator_input_fill_matches_profile(
    basic_profile: CharacterProfile,
) -> None:
    """계산기 반영값의 프로필 상태 일치 검증"""

    fill: CalculatorInputFill = build_calculator_input_fill(basic_profile)

    assert fill.level == basic_profile.level
    assert fill.realm_tier == basic_profile.realm
    assert fill.distribution.strength == basic_profile.distribution.strength
    assert fill.distribution.dexterity == basic_profile.distribution.dexterity
    assert fill.danjeon.upper == basic_profile.danjeon.upper
    assert fill.danjeon.middle == basic_profile.danjeon.middle

    # 반영 전체 스탯의 실시간 최종 스탯 일치 확인
    live: LiveStatView = compute_live_view(basic_profile)
    assert fill.overall_stats == live.final.values


def test_optimize_danjeon_puts_all_points_in_middle(
    basic_profile: CharacterProfile,
) -> None:
    """단전 자동 설정의 중단전 집중 배분 검증"""

    optimized: DanjeonDistribution = optimize_danjeon(basic_profile)

    realm_cap: int = REALM_TIER_SPECS[basic_profile.realm].danjeon_points
    assert optimized.upper == 0
    assert optimized.middle == realm_cap
    assert optimized.lower == 0


def test_clamp_allocations_trims_over_cap_values() -> None:
    """한도 초과 분배값의 순서 기반 정리 검증"""

    profile: CharacterProfile = CharacterProfile(
        name="한도 초과",
        level=1,
        realm=RealmTier.SECOND_RATE,
        distribution=StatDistribution(strength=10, dexterity=10, vitality=1, luck=1),
        danjeon=DanjeonDistribution(upper=5, middle=1, lower=1),
    )

    clamp_profile_allocations(profile)

    # 레벨 1 한도(5포인트)의 힘 우선 정리 확인
    assert profile.distribution.strength == 5
    assert profile.distribution.dexterity == 0
    assert profile.distribution.vitality == 0
    assert profile.distribution.luck == 0

    # 이류 한도(2포인트)의 상단전 우선 정리 확인
    assert profile.danjeon.upper == 2
    assert profile.danjeon.middle == 0
    assert profile.danjeon.lower == 0

    # 정리 결과의 검증 통과 확인
    validate_character_profile(profile)


def test_equipment_lifecycle_updates_all_equipped_references(
    basic_profile: CharacterProfile,
) -> None:
    """장비 생성·장착·이름 변경·복제·삭제의 참조 일관성 검증"""

    original: OwnedEquipment = create_equipment(
        basic_profile,
        OwnedEquipment(name="원본 반지", kind=EquipmentKind.RING),
    )
    equip_equipment(basic_profile, EquipmentSlot.RING1, original.name)

    rename_equipment(basic_profile, "원본 반지", "이름 변경 반지")
    assert original.name == "이름 변경 반지"
    assert basic_profile.equipment.equipped[EquipmentSlot.RING1] == original.name

    duplicated: OwnedEquipment = duplicate_equipment(
        basic_profile,
        original.name,
        "복제 반지",
    )
    duplicated.base_stat_lines.append(
        EquipmentFreeStatLine(stat_key=StatKey.ATTACK, value=10.0)
    )
    assert original.base_stat_lines == []
    equip_equipment(basic_profile, EquipmentSlot.RING2, duplicated.name)

    remove_equipment(basic_profile, original.name)
    assert basic_profile.equipment.equipped[EquipmentSlot.RING1] is None
    assert basic_profile.equipment.equipped[EquipmentSlot.RING2] == duplicated.name

    unequip_equipment(basic_profile, EquipmentSlot.RING2)
    assert basic_profile.equipment.equipped[EquipmentSlot.RING2] is None
    validate_character_profile(basic_profile)


def test_equipment_lifecycle_rejects_invalid_operations(
    basic_profile: CharacterProfile,
) -> None:
    """장비 이름·슬롯·삭제 대상 invariant 위반의 명시적 거부 검증"""

    create_equipment(
        basic_profile,
        OwnedEquipment(name="반지", kind=EquipmentKind.RING),
    )

    with pytest.raises(ValueError):
        create_equipment(
            basic_profile,
            OwnedEquipment(name="반지", kind=EquipmentKind.RING),
        )

    with pytest.raises(ValueError):
        equip_equipment(basic_profile, EquipmentSlot.WEAPON, "반지")

    with pytest.raises(ValueError):
        rename_equipment(basic_profile, "반지", "   ")

    with pytest.raises(ValueError):
        duplicate_equipment(basic_profile, "반지", "반지")

    with pytest.raises(ValueError):
        remove_equipment(basic_profile, "없는 장비")


def test_clone_character_regenerates_ids_and_preserves_equipped_references(
    basic_profile: CharacterProfile,
) -> None:
    """캐릭터 복제 시 내부 ID 재발급과 장착 참조 재연결 검증"""

    title: CharacterTitle = CharacterTitle(name="장착 칭호")
    talisman: CharacterTalisman = CharacterTalisman(
        talisman_key=TALISMAN_SPECS[0].name,
        level=3,
    )
    basic_profile.titles.append(title)
    basic_profile.talismans.append(talisman)
    basic_profile.equipped.title_id = title.id
    basic_profile.equipped.talisman_ids = [talisman.id]

    cloned: CharacterProfile = clone_character_profile(basic_profile)

    assert cloned.id != basic_profile.id
    assert cloned.titles[0].id != title.id
    assert cloned.talismans[0].id != talisman.id
    assert cloned.equipped.title_id == cloned.titles[0].id
    assert cloned.equipped.talisman_ids == [cloned.talismans[0].id]
    assert cloned.to_dict() != basic_profile.to_dict()

    cloned.titles[0].name = "복제본 칭호"
    assert title.name == "장착 칭호"
    validate_character_profile(cloned)


def test_character_clipboard_roundtrip_regenerates_internal_ids(
    basic_profile: CharacterProfile,
) -> None:
    """캐릭터 붙여넣기 복원 시 독립 ID와 의미 상태 보존 검증"""

    title: CharacterTitle = CharacterTitle(name="복사 칭호")
    talisman: CharacterTalisman = CharacterTalisman(
        talisman_key=TALISMAN_SPECS[0].name,
        level=5,
    )
    basic_profile.titles.append(title)
    basic_profile.talismans.append(talisman)
    basic_profile.equipped.title_id = title.id
    basic_profile.equipped.talisman_ids = [talisman.id]

    restored: CharacterProfile = deserialize_character_profile(
        serialize_character_profile(basic_profile)
    )

    assert restored.id != basic_profile.id
    assert restored.name == basic_profile.name
    assert restored.level == basic_profile.level
    assert restored.titles[0].name == title.name
    assert restored.equipped.title_id == restored.titles[0].id
    assert restored.equipped.talisman_ids == [restored.talismans[0].id]
    assert restored.titles[0].id != title.id
    assert restored.talismans[0].id != talisman.id


def test_optimize_stat_distribution_matches_exhaustive_damage_score(
    basic_profile: CharacterProfile,
) -> None:
    """캐릭터 자동 스탯 분배의 힘·민첩 전수조사 최적해 일치 검증"""

    optimized: StatDistribution = optimize_stat_distribution(basic_profile)
    total_points: int = basic_profile.level * 5

    def damage_score(distribution: StatDistribution) -> float:
        candidate: CharacterProfile = CharacterProfile.from_dict(
            basic_profile.to_dict()
        )
        candidate.distribution = distribution
        values: dict[StatKey, float] = compute_live_view(candidate).final.values
        crit_rate: float = min(values[StatKey.CRIT_RATE_PERCENT], 100.0)
        return values[StatKey.ATTACK] * (
            1.0 + crit_rate * (values[StatKey.CRIT_DAMAGE_PERCENT] - 100.0) / 10000.0
        )

    optimized_score: float = damage_score(optimized)
    exhaustive_best: float = max(
        damage_score(
            StatDistribution(
                strength=strength,
                dexterity=total_points - strength,
            )
        )
        for strength in range(total_points + 1)
    )

    assert optimized.strength + optimized.dexterity == total_points
    assert optimized.vitality == 0
    assert optimized.luck == 0
    assert optimized_score == pytest.approx(exhaustive_best)
