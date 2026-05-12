from __future__ import annotations

import pytest

from app.scripts.calculator_engine import (
    EvaluationContext,
    LevelUpEvaluation,
    ScrollUpgradeEvaluation,
    build_calculator_context,
    evaluate_arbitrary_stat_delta,
    evaluate_level_up_delta,
    evaluate_scroll_upgrade_deltas,
    evaluate_single_stat_delta,
)
from app.scripts.calculator_models import (
    BaseStats,
    FinalStats,
    PowerMetric,
    StatKey,
)
from app.scripts.macro_models import MacroPreset
from app.scripts.registry.server_registry import ServerSpec


@pytest.fixture
def base_context(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> EvaluationContext:
    """효율 계산 검증용 공통 평가 컨텍스트"""

    return build_calculator_context(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        base_stats=realistic_base_stats,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
        custom_formulas=(),
    )


def test_decomposed_changes_yield_same_final_stats(
    realistic_base_stats: BaseStats,
) -> None:
    """힘 +1을 두 번 적용한 최종 스탯은 힘 +2를 한 번 적용한 결과와 동일"""

    decomposed: FinalStats = (
        realistic_base_stats.with_changes({StatKey.STR: 1.0})
        .with_changes({StatKey.STR: 1.0})
        .resolve()
    )
    direct: FinalStats = realistic_base_stats.with_changes({StatKey.STR: 2.0}).resolve()
    assert decomposed.values == direct.values


def test_decomposed_changes_yield_same_final_stats_multi_stat(
    realistic_base_stats: BaseStats,
) -> None:
    """여러 스탯을 부분 적용한 최종 스탯도 한 번에 적용한 결과와 동일"""

    decomposed: FinalStats = (
        realistic_base_stats.with_changes({StatKey.STR: 5.0})
        .with_changes({StatKey.DEXTERITY: 3.0, StatKey.VITALITY: 2.0})
        .resolve()
    )
    direct: FinalStats = realistic_base_stats.with_changes(
        {StatKey.STR: 5.0, StatKey.DEXTERITY: 3.0, StatKey.VITALITY: 2.0}
    ).resolve()
    assert decomposed.values == direct.values


def test_single_delta_for_non_damage_stat_is_zero(
    base_context: EvaluationContext,
) -> None:
    """행운은 데미지에 영향을 주지 않으므로 보스 데미지 delta가 0"""

    # 보스 데미지 공식에는 행운이 직접 들어가지 않음
    delta: float = evaluate_single_stat_delta(
        context=base_context,
        stat_key=StatKey.LUCK,
        amount=10.0,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    assert delta == 0.0


def test_single_delta_for_damage_stat_is_positive(
    base_context: EvaluationContext,
) -> None:
    """힘은 데미지에 양의 영향을 미치므로 delta > 0"""

    delta: float = evaluate_single_stat_delta(
        context=base_context,
        stat_key=StatKey.STR,
        amount=100.0,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    assert delta > 0.0


def test_arbitrary_delta_consistent_with_single_for_non_interacting_stat(
    base_context: EvaluationContext,
) -> None:
    """공격력 절대값은 attack에 1차로만 들어가므로 단일/누적 delta가 일치한다

    공격력은 final_attack = (ATTACK + final_strength) * (1 + attack_percent * 0.01) 식에서
    attack_percent가 STR과 무관할 때 attack에 대해 선형이다.
    """

    arbitrary_delta: float = evaluate_arbitrary_stat_delta(
        context=base_context,
        stat_changes={StatKey.ATTACK: 2.0},
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    single_a: float = evaluate_single_stat_delta(
        context=base_context,
        stat_key=StatKey.ATTACK,
        amount=1.0,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    single_b: float = evaluate_single_stat_delta(
        context=base_context,
        stat_key=StatKey.ATTACK,
        amount=1.0,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    assert single_a + single_b == pytest.approx(arbitrary_delta, rel=1e-9)


def test_level_up_delta_returns_valid_distribution(
    base_context: EvaluationContext,
) -> None:
    """레벨업 효율 결과는 분배 합 5, delta는 유한 실수"""

    evaluation: LevelUpEvaluation = evaluate_level_up_delta(
        context=base_context,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    distribution_sum: int = (
        evaluation.stat_distribution[StatKey.STR]
        + evaluation.stat_distribution[StatKey.DEXTERITY]
        + evaluation.stat_distribution[StatKey.VITALITY]
        + evaluation.stat_distribution[StatKey.LUCK]
    )
    assert distribution_sum == 5
    assert isinstance(evaluation.delta, float)


def test_level_up_delta_is_non_negative_for_boss_damage(
    base_context: EvaluationContext,
) -> None:
    """보스 데미지 기준 레벨업 delta는 음수가 아니다 (스탯 증가만 가능)"""

    evaluation: LevelUpEvaluation = evaluate_level_up_delta(
        context=base_context,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    assert evaluation.delta >= 0.0


def test_scroll_upgrade_deltas_returns_one_per_equipped_scroll(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    base_context: EvaluationContext,
) -> None:
    """장착된 무공비급 수만큼 효율 결과가 반환된다"""

    evaluations: list[ScrollUpgradeEvaluation] = evaluate_scroll_upgrade_deltas(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        baseline_context=base_context,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    # 무공비급 7개 모두 장착, 모두 1레벨이라 모두 업그레이드 가능
    assert len(evaluations) == synthetic_server.scroll_slot_count


def test_scroll_upgrade_deltas_are_positive(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    base_context: EvaluationContext,
) -> None:
    """무공비급 1레벨 상승은 보스 데미지를 증가시킨다 (스킬 계수 증가)"""

    evaluations: list[ScrollUpgradeEvaluation] = evaluate_scroll_upgrade_deltas(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        baseline_context=base_context,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    for evaluation in evaluations:
        assert evaluation.delta > 0.0, f"{evaluation.scroll_id} delta should be positive"


def test_scroll_upgrade_preserves_original_levels(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    base_context: EvaluationContext,
) -> None:
    """무공비급 업그레이드 평가는 평가 후 원래 레벨로 되돌려놓는다"""

    original_levels: dict[str, int] = dict(full_preset.info.scroll_levels)

    evaluate_scroll_upgrade_deltas(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        baseline_context=base_context,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert full_preset.info.scroll_levels == original_levels


def test_arbitrary_delta_zero_input_returns_zero(
    base_context: EvaluationContext,
) -> None:
    """빈 변화 입력은 0 delta를 반환한다"""

    delta: float = evaluate_arbitrary_stat_delta(
        context=base_context,
        stat_changes={},
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    assert delta == 0.0
