from __future__ import annotations

import math

import pytest

from app.scripts.calculator_models import (
    BaseStats,
    FinalStats,
    OVERALL_STAT_ORDER,
    StatKey,
)


def _round2(value: float) -> float:
    """FinalStats가 소수 둘째자리까지 라운드한다는 사실에 맞춰 비교"""

    return round(value, 2)


def test_create_default_only_sets_crit_damage() -> None:
    """기본 베이스 스탯은 치명피해 110만 값으로 가진다"""

    base: BaseStats = BaseStats.create_default()

    # 치명피해 외 모든 키는 0
    for stat_key in OVERALL_STAT_ORDER:
        if stat_key == StatKey.CRIT_DAMAGE_PERCENT:
            assert base.values[stat_key.value] == 110.0
            continue

        assert base.values[stat_key.value] == 0.0


def test_resolve_default_keeps_only_crit_damage() -> None:
    """기본 베이스는 모든 2차 효과가 0이라 최종에서도 치명피해 110만 살아남는다"""

    base: BaseStats = BaseStats.create_default()
    final: FinalStats = base.resolve()

    assert final.values[StatKey.CRIT_DAMAGE_PERCENT] == 110.0
    assert final.values[StatKey.ATTACK] == 0.0
    assert final.values[StatKey.HP] == 0.0
    assert final.values[StatKey.STR] == 0.0
    assert final.values[StatKey.DEXTERITY] == 0.0


def test_resolve_str_with_percent_propagates_to_attack_and_crit() -> None:
    """힘 + 힘% 는 공격력과 치명피해에 곱연산으로 반영된다"""

    values: dict[str, float] = {key.value: 0.0 for key in OVERALL_STAT_ORDER}
    values[StatKey.STR.value] = 1000.0
    values[StatKey.STR_PERCENT.value] = 50.0
    values[StatKey.CRIT_DAMAGE_PERCENT.value] = 110.0
    base: BaseStats = BaseStats(values=values)

    final: FinalStats = base.resolve()

    # 힘 1500 = 1000 * 1.5
    assert final.values[StatKey.STR] == _round2(1500.0)

    # 공격력 = (0 + 1500) * (1 + 0%) = 1500
    assert final.values[StatKey.ATTACK] == _round2(1500.0)

    # 치명피해 = 110 + 1500 * 0.1 = 260
    assert final.values[StatKey.CRIT_DAMAGE_PERCENT] == _round2(260.0)


def test_resolve_dex_secondary_effects() -> None:
    """민첩은 공격력%와 치명타율에 부수 효과를 준다"""

    values: dict[str, float] = {key.value: 0.0 for key in OVERALL_STAT_ORDER}
    values[StatKey.ATTACK.value] = 1000.0
    values[StatKey.DEXTERITY.value] = 1000.0
    base: BaseStats = BaseStats(values=values)

    final: FinalStats = base.resolve()

    # 민첩 1000 → 공격력% +300, 치명타율 +50
    assert final.values[StatKey.ATTACK_PERCENT] == _round2(300.0)
    assert final.values[StatKey.CRIT_RATE_PERCENT] == _round2(50.0)

    # 공격력 = (1000 + 0) * (1 + 300%) = 4000
    assert final.values[StatKey.ATTACK] == _round2(4000.0)


def test_resolve_vitality_chain() -> None:
    """생명력은 HP, 회피, 물약 회복에 부수 효과를 준다"""

    values: dict[str, float] = {key.value: 0.0 for key in OVERALL_STAT_ORDER}
    values[StatKey.HP.value] = 5000.0
    values[StatKey.HP_PERCENT.value] = 20.0
    values[StatKey.VITALITY.value] = 1000.0
    values[StatKey.VITALITY_PERCENT.value] = 50.0
    base: BaseStats = BaseStats(values=values)

    final: FinalStats = base.resolve()

    # 생명력 1500 = 1000 * 1.5
    assert final.values[StatKey.VITALITY] == _round2(1500.0)

    # HP = (5000 + 1500 * 5) * (1 + 20%) = 12500 * 1.2 = 15000
    assert final.values[StatKey.HP] == _round2(15000.0)

    # 회피 +45 = 1500 * 0.03
    assert final.values[StatKey.DODGE_PERCENT] == _round2(45.0)

    # 물약 회복 +750 = 1500 * 0.5
    assert final.values[StatKey.POTION_HEAL_PERCENT] == _round2(750.0)


def test_resolve_luck_drop_and_exp() -> None:
    """행운은 드랍률과 경험치에 부수 효과를 준다"""

    values: dict[str, float] = {key.value: 0.0 for key in OVERALL_STAT_ORDER}
    values[StatKey.LUCK.value] = 500.0
    values[StatKey.LUCK_PERCENT.value] = 20.0
    base: BaseStats = BaseStats(values=values)

    final: FinalStats = base.resolve()

    # 행운 600 = 500 * 1.2
    assert final.values[StatKey.LUCK] == _round2(600.0)

    # 드랍률 = 0 + 600 * 0.2 = 120
    assert final.values[StatKey.DROP_RATE_PERCENT] == _round2(120.0)

    # 경험치% = 0 + 600 * 0.2 = 120
    assert final.values[StatKey.EXP_PERCENT] == _round2(120.0)


def test_resolve_with_changes_equals_with_changes_then_resolve() -> None:
    """resolve(stat_changes)와 with_changes()+resolve()는 동일 결과를 낸다"""

    base: BaseStats = BaseStats.create_default()
    values: dict[str, float] = base.values.copy()
    values[StatKey.STR.value] = 200.0
    base = BaseStats(values=values)

    stat_changes: dict[StatKey, float] = {
        StatKey.STR: 100.0,
        StatKey.DEXTERITY: 50.0,
    }

    inline_final: FinalStats = base.resolve(stat_changes)
    composed_final: FinalStats = base.with_changes(stat_changes).resolve()

    assert inline_final.values == composed_final.values


def test_with_changes_composes_associatively() -> None:
    """with_changes를 두 번 부분 적용한 결과는 한 번 합쳐 적용한 결과와 동일

    이 invariant가 깨지면 효율 계산의 분해 가정이 무너진다.
    """

    base: BaseStats = BaseStats.create_default()
    values: dict[str, float] = base.values.copy()
    values[StatKey.STR.value] = 100.0
    base = BaseStats(values=values)

    # 분해 적용
    decomposed: BaseStats = base.with_changes({StatKey.STR: 1.0}).with_changes(
        {StatKey.STR: 1.0}
    )

    # 한 번에 적용
    direct: BaseStats = base.with_changes({StatKey.STR: 2.0})

    # 원시 베이스 스탯 차원에서 동일
    assert decomposed.values == direct.values

    # resolve 후 최종 스탯도 동일
    assert decomposed.resolve().values == direct.resolve().values


def test_with_changes_none_returns_same_object() -> None:
    """변화 인자가 None이면 동일 인스턴스 반환"""

    base: BaseStats = BaseStats.create_default()
    assert base.with_changes(None) is base


def test_with_changes_subtract_mode_negates_input() -> None:
    """is_add=False 모드는 입력 값을 차감한다"""

    base: BaseStats = BaseStats.create_default()
    values: dict[str, float] = base.values.copy()
    values[StatKey.STR.value] = 100.0
    base = BaseStats(values=values)

    result: BaseStats = base.with_changes({StatKey.STR: 30.0}, is_add=False)
    assert result.values[StatKey.STR.value] == 70.0


def test_realistic_base_stats_resolve_is_deterministic(
    realistic_base_stats: BaseStats,
) -> None:
    """현실적인 베이스 스탯의 resolve 결과는 호출마다 동일 (멱등성)"""

    first: FinalStats = realistic_base_stats.resolve()
    second: FinalStats = realistic_base_stats.resolve()
    assert first.values == second.values


def test_realistic_base_stats_attack_value_golden(
    realistic_base_stats: BaseStats,
) -> None:
    """현실적인 베이스의 최종 공격력을 손계산 값으로 검증"""

    # final_strength = 1000 * (1 + 30%) = 1300
    # final_dexterity = 500 * (1 + 20%) = 600
    # attack_percent = 50 + 600 * 0.3 = 230
    # attack = (5000 + 1300) * (1 + 230%) = 6300 * 3.3 = 20790
    final: FinalStats = realistic_base_stats.resolve()
    assert final.values[StatKey.ATTACK] == _round2(20790.0)


def test_realistic_base_stats_crit_damage_golden(
    realistic_base_stats: BaseStats,
) -> None:
    """현실적인 베이스의 최종 치명피해를 손계산 값으로 검증"""

    # final_strength = 1300
    # crit_damage = 180 + 1300 * 0.1 = 310
    final: FinalStats = realistic_base_stats.resolve()
    assert final.values[StatKey.CRIT_DAMAGE_PERCENT] == _round2(310.0)


def test_realistic_base_stats_hp_golden(
    realistic_base_stats: BaseStats,
) -> None:
    """현실적인 베이스의 최종 HP를 손계산 값으로 검증"""

    # final_vitality = 800 * (1 + 10%) = 880
    # hp = (10000 + 880 * 5) * (1 + 20%) = 14400 * 1.2 = 17280
    final: FinalStats = realistic_base_stats.resolve()
    assert final.values[StatKey.HP] == _round2(17280.0)
