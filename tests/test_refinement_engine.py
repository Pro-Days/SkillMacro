from __future__ import annotations

import numpy as np
import pytest

from app.scripts.calculator_models import (
    RefinementEquipment,
    RefinementInput,
    RefinementStrategy,
    RefinementStrategyMode,
    StatKey,
)
from app.scripts.refinement_data import (
    DOWNGRADE_RATE_ON_FAILURE,
    MAX_REFINE_STEP,
    REFINE_ATTEMPT_STEP_COUNT,
    REFINE_BASE_COSTS,
    REFINE_BASE_SUCCESS_RATES,
    refine_cost_multiplier,
    refinement_stat_delta,
)
from app.scripts.refinement_engine import (
    PREPARATION_PROBABILITIES,
    ExpectedTotals,
    RefinementDistribution,
    RefinementInputError,
    RefinementPlan,
    RefinementStrategyChoice,
    assist_points_from_thresholds,
    build_plan,
    choose_auto_strategy,
    compute_distributions,
    compute_expected_totals,
    expected_weight_total,
    point_price_from_bundle,
    resolve_strategy_choice,
    validate_refinement_input,
    validate_strategy_thresholds,
)

# 보조 없는 단계별 소모 포인트
NO_ASSIST_POINTS: tuple[int, ...] = (0,) * REFINE_ATTEMPT_STEP_COUNT


def solve_expected_total(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
    start_step: int,
    target_step: int,
) -> float:
    """상태 전이 연립방정식을 직접 풀어 기대 소모량 계산

    엔진의 첫 통과 재귀와 독립적인 검증 기준으로 사용한다.
    """

    # 목표 단계를 흡수 상태로 두고 0 ~ 목표-1 상태의 연립방정식 구성
    size: int = target_step
    coefficients: np.ndarray = np.zeros((size, size), dtype=np.float64)
    constants: np.ndarray = np.zeros(size, dtype=np.float64)

    for step in range(size):
        success_rate: float = success_rates[step]
        failure_rate: float = 1.0 - success_rate

        coefficients[step, step] += 1.0
        constants[step] = weights[step]

        # 성공 시 다음 단계로 이동 (목표 단계는 흡수)
        if step + 1 < target_step:
            coefficients[step, step + 1] -= success_rate

        # 실패 후 유지
        coefficients[step, step] -= failure_rate * (1.0 - DOWNGRADE_RATE_ON_FAILURE)

        # 실패 후 하락 (0강은 하락해도 0강 유지)
        lower_step: int = max(step - 1, 0)
        coefficients[step, lower_step] -= failure_rate * DOWNGRADE_RATE_ON_FAILURE

    solution: np.ndarray = np.linalg.solve(coefficients, constants)
    return float(solution[start_step])


@pytest.mark.parametrize(
    ("level_cap", "start_step", "target_step"),
    [
        (0, 0, 1),
        (50, 0, 10),
        (180, 3, 12),
        (110, 12, 20),
    ],
)
def test_expected_cost_matches_state_equation_solution(
    level_cap: int,
    start_step: int,
    target_step: int,
) -> None:
    """기대 재련비가 상태 전이 연립방정식 해와 일치하는지 검증"""

    plan: RefinementPlan = build_plan(level_cap, False, False, NO_ASSIST_POINTS)
    expected: float = expected_weight_total(
        plan.success_rates,
        plan.costs,
        start_step,
        target_step,
    )
    reference: float = solve_expected_total(
        plan.success_rates,
        plan.costs,
        start_step,
        target_step,
    )

    assert expected == pytest.approx(reference, rel=1e-9)


def test_expected_points_matches_state_equation_solution_with_assist() -> None:
    """보조 전략 적용 시 기대 강화포인트가 연립방정식 해와 일치하는지 검증"""

    plan: RefinementPlan = build_plan(
        110,
        True,
        True,
        assist_points_from_thresholds(4, 12),
    )
    point_weights: tuple[float, ...] = tuple(
        float(points) for points in plan.assist_points
    )

    expected: float = expected_weight_total(plan.success_rates, point_weights, 3, 18)
    reference: float = solve_expected_total(plan.success_rates, point_weights, 3, 18)

    assert expected == pytest.approx(reference, rel=1e-9)


def test_assist_raises_success_rate_and_consumes_points() -> None:
    """보조 적용 단계의 성공확률 증가와 포인트 소모 검증"""

    plan: RefinementPlan = build_plan(
        180,
        False,
        False,
        assist_points_from_thresholds(4, 12),
    )

    # 보조 없는 구간은 기본 성공확률 유지
    assert plan.assist_points[3] == 0
    assert plan.success_rates[3] == pytest.approx(REFINE_BASE_SUCCESS_RATES[3])

    # 3pt 구간은 +3%p, 7pt 구간은 +5%p
    assert plan.assist_points[4] == 3
    assert plan.success_rates[4] == pytest.approx(REFINE_BASE_SUCCESS_RATES[4] + 0.03)
    assert plan.assist_points[12] == 7
    assert plan.success_rates[12] == pytest.approx(REFINE_BASE_SUCCESS_RATES[12] + 0.05)


def test_refine_pet_and_vip_discounts_apply_additively() -> None:
    """재련펫·VIP 할인이 합연산으로 적용되는지 검증"""

    assert refine_cost_multiplier(False, False) == pytest.approx(1.0)
    assert refine_cost_multiplier(True, False) == pytest.approx(0.95)
    assert refine_cost_multiplier(False, True) == pytest.approx(0.90)
    assert refine_cost_multiplier(True, True) == pytest.approx(0.85)

    plan: RefinementPlan = build_plan(180, True, True, NO_ASSIST_POINTS)
    assert plan.costs[0] == pytest.approx(REFINE_BASE_COSTS[180][0] * 0.85)


def test_expected_totals_keep_step_balance() -> None:
    """기대 성공 횟수와 하락 횟수의 차이가 상승 단계 수와 같은지 검증"""

    plan: RefinementPlan = build_plan(180, False, False, NO_ASSIST_POINTS)
    totals: ExpectedTotals = compute_expected_totals(plan, 2, 15, 20000.0)

    assert totals.successes - totals.downgrades == pytest.approx(15 - 2, rel=1e-9)
    assert totals.attempts == pytest.approx(totals.successes + totals.failures)
    assert totals.economic_cost == pytest.approx(
        totals.cost + totals.points * 20000.0
    )


def test_distribution_reproduces_expected_value_and_total_mass() -> None:
    """복원된 분포의 총질량과 평균이 기대값과 일치하는지 검증"""

    plan: RefinementPlan = build_plan(50, False, False, NO_ASSIST_POINTS)
    distributions: dict[int, RefinementDistribution] = compute_distributions(
        plan.success_rates,
        plan.cost_units,
        plan.cost_unit_value,
        0,
        (5, 10),
    )
    expected: ExpectedTotals = compute_expected_totals(plan, 0, 10, 0.0)

    distribution: RefinementDistribution = distributions[10]
    assert distribution.total_mass() == pytest.approx(1.0, abs=1e-9)
    assert distribution.mean() == pytest.approx(expected.cost, rel=1e-6)

    # 목표 단계가 높을수록 같은 확률 기준 준비량이 커야 함
    assert distributions[5].quantile(0.9) < distribution.quantile(0.9)


def test_distribution_quantiles_are_monotonic() -> None:
    """준비량 분위수가 확률 순서대로 증가하는지 검증"""

    plan: RefinementPlan = build_plan(80, False, False, NO_ASSIST_POINTS)
    distribution: RefinementDistribution = compute_distributions(
        plan.success_rates,
        plan.cost_units,
        plan.cost_unit_value,
        0,
        (8,),
    )[8]

    quantiles: list[float] = [
        distribution.quantile(probability)
        for probability in PREPARATION_PROBABILITIES
    ]
    assert quantiles == sorted(quantiles)

    # 분위수 지점의 누적 확률은 기준 확률 이상이어야 함
    for probability, value in zip(PREPARATION_PROBABILITIES, quantiles):
        assert distribution.probability_at_most(value) >= probability - 1e-9


def test_distribution_without_assist_points_is_zero_only() -> None:
    """보조를 쓰지 않으면 강화포인트 분포가 0에 몰리는지 검증"""

    plan: RefinementPlan = build_plan(50, False, False, NO_ASSIST_POINTS)
    distribution: RefinementDistribution = compute_distributions(
        plan.success_rates,
        plan.assist_points,
        1.0,
        0,
        (10,),
    )[10]

    assert distribution.probability_at_most(0.0) == pytest.approx(1.0)
    assert distribution.quantile(0.95) == pytest.approx(0.0)


def test_auto_strategy_matches_exhaustive_minimum() -> None:
    """자동 최적 전략이 전수 탐색 최솟값과 같은 결과인지 검증"""

    level_cap: int = 180
    start_step: int = 0
    target_step: int = 20
    point_price: float = point_price_from_bundle(100000.0)

    chosen: tuple[int, int] | None = choose_auto_strategy(
        level_cap,
        False,
        False,
        start_step,
        target_step,
        point_price,
    )

    # 무보조를 포함한 모든 전략의 기대 경제적 총비용 재계산
    def economic_cost(assist_points: tuple[int, ...]) -> float:
        plan: RefinementPlan = build_plan(level_cap, False, False, assist_points)
        return compute_expected_totals(
            plan,
            start_step,
            target_step,
            point_price,
        ).economic_cost

    best_cost: float = economic_cost(NO_ASSIST_POINTS)
    last_attempt_step: int = REFINE_ATTEMPT_STEP_COUNT - 1
    for assist3_step in range(0, last_attempt_step):
        for assist7_step in range(assist3_step + 1, last_attempt_step + 1):
            candidate_cost: float = economic_cost(
                assist_points_from_thresholds(assist3_step, assist7_step)
            )
            best_cost = min(best_cost, candidate_cost)

    chosen_points: tuple[int, ...] = (
        NO_ASSIST_POINTS if chosen is None else assist_points_from_thresholds(*chosen)
    )
    assert economic_cost(chosen_points) == pytest.approx(best_cost, rel=1e-12)


def test_auto_strategy_follows_point_price() -> None:
    """1pt 가격에 따라 자동 최적 전략이 달라지는지 검증"""

    # 포인트가 공짜면 가능한 최대 보조를 사용
    assert choose_auto_strategy(180, False, False, 0, 20, 0.0) == (0, 1)

    # 포인트가 매우 비싸면 무보조를 선택
    assert choose_auto_strategy(180, False, False, 0, 20, 1e9) is None


def test_strategy_threshold_validation() -> None:
    """사용자 전략 입력 조건 검증"""

    assert validate_strategy_thresholds(0, 19) is None
    assert validate_strategy_thresholds(5, 5) is not None
    assert validate_strategy_thresholds(-1, 5) is not None
    assert validate_strategy_thresholds(5, 20) is not None


def test_resolve_strategy_choice_uses_saved_user_strategy() -> None:
    """저장한 사용자 전략이 그대로 적용되는지 검증"""

    strategy: RefinementStrategy = RefinementStrategy(
        id="strategy-1",
        name="안전 재련",
        assist3_step=4,
        assist7_step=12,
    )
    refinement: RefinementInput = RefinementInput(
        strategy_mode=RefinementStrategyMode.USER,
        selected_strategy_id="strategy-1",
    )

    choice: RefinementStrategyChoice = resolve_strategy_choice(
        refinement,
        (strategy,),
    )
    assert choice.assist3_step == 4
    assert choice.assist7_step == 12
    assert choice.assist_points == assist_points_from_thresholds(4, 12)

    # 없는 전략을 선택하면 계산을 진행할 수 없음
    refinement.selected_strategy_id = "missing"
    with pytest.raises(RefinementInputError):
        resolve_strategy_choice(refinement, (strategy,))


def test_validate_refinement_input_rejects_invalid_steps() -> None:
    """단계 범위와 전략 선택 입력 검증"""

    valid: RefinementInput = RefinementInput(start_step=0, target_step=20)
    assert validate_refinement_input(valid, ()) is None

    same_step: RefinementInput = RefinementInput(start_step=5, target_step=5)
    assert validate_refinement_input(same_step, ()) is not None

    over_max: RefinementInput = RefinementInput(
        start_step=0,
        target_step=MAX_REFINE_STEP + 1,
    )
    assert validate_refinement_input(over_max, ()) is not None

    missing_strategy: RefinementInput = RefinementInput(
        strategy_mode=RefinementStrategyMode.USER,
        selected_strategy_id="",
    )
    assert validate_refinement_input(missing_strategy, ()) is not None


def test_weapon_and_armor_stat_delta_follows_cumulative_table() -> None:
    """장비 종류별 단계 상승 스탯이 누적표를 따르는지 검증"""

    weapon_delta: dict[StatKey, float] = refinement_stat_delta(
        RefinementEquipment.WEAPON,
        0,
        MAX_REFINE_STEP,
    )
    assert weapon_delta == {
        StatKey.ATTACK: 60.0,
        StatKey.ATTACK_PERCENT: 4.0,
        StatKey.SKILL_DAMAGE_PERCENT: 7.0,
    }

    # 방어구는 부위 주스탯과 경험치 획득량으로 상승
    helmet_delta: dict[StatKey, float] = refinement_stat_delta(
        RefinementEquipment.HELMET,
        10,
        MAX_REFINE_STEP,
    )
    assert helmet_delta == {
        StatKey.LUCK: 55.0,
        StatKey.LUCK_PERCENT: 4.0,
        StatKey.EXP_PERCENT: 1.0,
    }

    belt_delta: dict[StatKey, float] = refinement_stat_delta(
        RefinementEquipment.BELT,
        0,
        3,
    )
    assert belt_delta == {StatKey.VITALITY: 3.0, StatKey.VITALITY_PERCENT: 1.0}

    # 같은 단계면 변화가 없어야 함
    assert refinement_stat_delta(RefinementEquipment.SHOES, 7, 7) == {}
