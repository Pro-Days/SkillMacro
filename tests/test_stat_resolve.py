from __future__ import annotations

import pytest

from app.scripts.calculator_models import (
    OVERALL_STAT_ORDER,
    BaseStats,
    FinalStats,
    StatKey,
)


def _make_base_stats(values: dict[StatKey, float]) -> BaseStats:
    """지정 스탯만 채운 베이스 스탯 구성"""

    # 전체 스탯 0 초기화 후 지정 값 반영
    base_values: dict[str, float] = {
        stat_key.value: 0.0 for stat_key in OVERALL_STAT_ORDER
    }
    for stat_key, value in values.items():
        base_values[stat_key.value] = value

    return BaseStats(values=base_values)


def test_zero_stats_resolve_to_zero() -> None:
    """전부 0인 스탯의 최종 변환 결과 0 유지 검증"""

    resolved: FinalStats = _make_base_stats({}).resolve()

    for stat_key in OVERALL_STAT_ORDER:
        assert resolved.values[stat_key] == 0.0


def test_attack_and_strength_resolve_hand_computed() -> None:
    """공격력/힘 결합 공식의 손계산 값 일치 검증

    최종 힘 = 힘 * (1 + 힘% * 0.01)
    공격력 = (공격력 + 최종 힘) * (1 + 공격력% * 0.01)
    치명타 공격력% = 치명타 공격력% + 최종 힘 * 0.1
    """

    resolved: FinalStats = _make_base_stats(
        {
            StatKey.ATTACK: 100.0,
            StatKey.ATTACK_PERCENT: 10.0,
            StatKey.STR: 100.0,
            StatKey.STR_PERCENT: 10.0,
        }
    ).resolve()

    # 최종 힘 = 100 * 1.1 = 110
    assert resolved.values[StatKey.STR] == pytest.approx(110.0)

    # 공격력 = (100 + 110) * 1.1 = 231
    assert resolved.values[StatKey.ATTACK] == pytest.approx(231.0)

    # 치명타 공격력% = 0 + 110 * 0.1 = 11
    assert resolved.values[StatKey.CRIT_DAMAGE_PERCENT] == pytest.approx(11.0)


def test_secondary_stat_bonuses_hand_computed() -> None:
    """민첩/생명력/행운 파생 보너스의 손계산 값 일치 검증

    민첩: 공격력% +0.3/1, 치명타 확률% +0.05/1
    생명력: 체력 +5/1, 회피% +0.03/1, 물약 회복량% +0.5/1
    행운: 드랍률% +0.2/1, 경험치% +0.2/1
    """

    resolved: FinalStats = _make_base_stats(
        {
            StatKey.DEXTERITY: 100.0,
            StatKey.VITALITY: 100.0,
            StatKey.LUCK: 50.0,
        }
    ).resolve()

    # 민첩 파생 보너스 확인
    assert resolved.values[StatKey.ATTACK_PERCENT] == pytest.approx(30.0)
    assert resolved.values[StatKey.CRIT_RATE_PERCENT] == pytest.approx(5.0)

    # 생명력 파생 보너스 확인
    assert resolved.values[StatKey.HP] == pytest.approx(500.0)
    assert resolved.values[StatKey.DODGE_PERCENT] == pytest.approx(3.0)
    assert resolved.values[StatKey.POTION_HEAL_PERCENT] == pytest.approx(50.0)

    # 행운 파생 보너스 확인
    assert resolved.values[StatKey.DROP_RATE_PERCENT] == pytest.approx(10.0)
    assert resolved.values[StatKey.EXP_PERCENT] == pytest.approx(10.0)


def test_hp_resolve_includes_vitality_and_percent() -> None:
    """체력 공식의 생명력 합산 후 체력% 적용 순서 검증

    체력 = (체력 + 최종 생명력 * 5) * (1 + 체력% * 0.01)
    """

    resolved: FinalStats = _make_base_stats(
        {
            StatKey.HP: 1000.0,
            StatKey.HP_PERCENT: 20.0,
            StatKey.VITALITY: 100.0,
            StatKey.VITALITY_PERCENT: 10.0,
        }
    ).resolve()

    # 최종 생명력 = 110, 체력 = (1000 + 550) * 1.2 = 1860
    assert resolved.values[StatKey.VITALITY] == pytest.approx(110.0)
    assert resolved.values[StatKey.HP] == pytest.approx(1860.0)


def test_with_changes_add_then_subtract_restores_original() -> None:
    """스탯 변화 적용 후 동일 변화 제거 시 원상 복구 검증"""

    base: BaseStats = _make_base_stats({StatKey.ATTACK: 500.0})
    changes: dict[StatKey, float] = {
        StatKey.ATTACK: 100.0,
        StatKey.CRIT_RATE_PERCENT: 5.0,
    }

    changed: BaseStats = base.with_changes(changes)
    restored: BaseStats = changed.with_changes(changes, is_add=False)

    assert restored.to_dict() == base.to_dict()


def test_resolve_with_changes_matches_pre_applied_changes() -> None:
    """resolve(stat_changes)와 선적용 후 resolve의 동일성 검증"""

    base: BaseStats = _make_base_stats(
        {StatKey.ATTACK: 500.0, StatKey.STR: 100.0, StatKey.DEXTERITY: 50.0}
    )
    changes: dict[StatKey, float] = {StatKey.STR: 25.0, StatKey.ATTACK_PERCENT: 10.0}

    resolved_inline: FinalStats = base.resolve(stat_changes=changes)
    resolved_pre_applied: FinalStats = base.with_changes(changes).resolve()

    assert resolved_inline.values == resolved_pre_applied.values
