"""재련 시뮬레이터 계산 엔진

상태 전이는 다음 규칙을 따른다.

- 시도 전에 현재 단계의 재련비와 보조 강화포인트를 소모한다.
- 성공하면 1단계 상승한다.
- 실패하면 남은 실패확률에 하락 60%, 유지 40%를 적용한다.
- 0강에서 하락하면 0강을 유지한다.

기대값은 단계별 첫 통과(현재 단계 → 다음 단계) 재귀로 정확히 계산하고,
분포와 분위수는 첫 통과 확률생성함수를 단위원 격자에서 평가한 뒤
역푸리에 변환으로 복원한다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from app.scripts.calculator_engine import (
    build_calculator_context,
    evaluate_arbitrary_stat_delta,
)
from app.scripts.calculator_models import (
    BaseStats,
    CustomPowerFormula,
    RefinementAssist,
    RefinementEquipment,
    RefinementInput,
    RefinementStrategy,
    RefinementStrategyMode,
    StatKey,
)
from app.scripts.refinement_data import (
    DOWNGRADE_RATE_ON_FAILURE,
    MAX_REFINE_STEP,
    POINT_BUNDLE_SIZE,
    REFINE_ATTEMPT_STEP_COUNT,
    REFINE_BASE_COSTS,
    REFINE_BASE_SUCCESS_RATES,
    REFINE_COST_UNIT,
    REFINEMENT_ASSIST_SPECS,
    refine_cost_multiplier,
    refinement_stat_delta,
)

if TYPE_CHECKING:
    from app.scripts.calculator_engine import EvaluationContext
    from app.scripts.macro_models import MacroPreset, SkillUsageSetting
    from app.scripts.registry.server_registry import ServerSpec


# 준비량 표시 기준 확률
PREPARATION_PROBABILITIES: tuple[float, ...] = (0.25, 0.5, 0.75, 0.9)

# 분포 격자 최소/최대 크기
_MIN_GRID_SIZE: int = 1 << 10
_MAX_GRID_SIZE: int = 1 << 22

# 격자 크기 결정에 사용하는 기대값 배수와 꼬리 허용 질량
_GRID_MEAN_FACTOR: int = 8
_GRID_TAIL_TOLERANCE: float = 1e-9


class RefinementInputError(ValueError):
    """재련 계산 입력 오류"""


@dataclass(frozen=True, slots=True)
class RefinementPlan:
    """전략까지 확정된 단계별 재련 조건"""

    # 단계별 실제 재련비 (할인 반영)
    costs: tuple[float, ...]
    # 단계별 재련비의 격자 단위 개수
    cost_units: tuple[int, ...]
    # 격자 단위 1개당 실제 재련비
    cost_unit_value: float
    # 단계별 성공확률 (보조 반영)
    success_rates: tuple[float, ...]
    # 단계별 소모 강화포인트
    assist_points: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class RefinementStrategyChoice:
    """계산에 사용된 전략 정보"""

    mode: RefinementStrategyMode
    assist_points: tuple[int, ...]
    strategy_name: str
    assist3_step: int | None
    assist7_step: int | None


@dataclass(frozen=True, slots=True)
class ExpectedTotals:
    """목표 단계까지의 기대 소모량"""

    cost: float
    points: float
    attempts: float
    successes: float
    failures: float
    downgrades: float
    economic_cost: float


@dataclass(frozen=True, slots=True)
class RefinementDistribution:
    """격자 단위 기준 누적 소모량 분포"""

    pmf: np.ndarray
    unit_value: float

    def probability_at_most(self, value: float) -> float:
        """지정 값 이하로 끝날 확률 반환"""

        # 격자 단위 개수로 환산 후 누적 확률 계산
        unit_count: int = int(np.floor(value / self.unit_value + 1e-9))
        if unit_count < 0:
            return 0.0

        if unit_count >= self.pmf.size:
            return float(self.pmf.sum())

        return float(self.pmf[: unit_count + 1].sum())

    def quantile(self, probability: float) -> float:
        """누적 확률을 처음 넘는 지점의 값 반환"""

        # 누적합에서 목표 확률 이상이 되는 첫 격자 조회
        cumulative: np.ndarray = np.cumsum(self.pmf)
        index: int = int(np.searchsorted(cumulative, probability, side="left"))
        if index >= self.pmf.size:
            index = self.pmf.size - 1

        return float(index) * self.unit_value

    def mean(self) -> float:
        """분포 기준 평균값 반환"""

        indices: np.ndarray = np.arange(self.pmf.size, dtype=np.float64)
        return float((self.pmf * indices).sum()) * self.unit_value

    def total_mass(self) -> float:
        """복원된 분포의 총 확률 질량 반환"""

        return float(self.pmf.sum())


@dataclass(frozen=True, slots=True)
class RefinementTargetRow:
    """목표 단계 하나에 대한 계산 결과"""

    target_step: int
    reach_probability: float
    expected: ExpectedTotals
    cost_quantiles: tuple[float, ...]
    point_quantiles: tuple[float, ...]
    stat_delta: dict[StatKey, float]
    power_delta: float | None
    efficiency: float | None


@dataclass(frozen=True, slots=True)
class RefinementEfficiencyRow:
    """0강 기준 목표 단계 하나의 효율 계산 입력"""

    target_step: int
    expected_economic_cost: float
    power_delta: float | None


@dataclass(frozen=True, slots=True)
class RefinementReport:
    """재련 시뮬레이터 계산 결과 전체"""

    equipment: RefinementEquipment
    level_cap: int
    start_step: int
    target_step: int
    budget: float
    point_price: float
    plan: RefinementPlan
    strategy: RefinementStrategyChoice
    rows: tuple[RefinementTargetRow, ...]
    efficiency_rows: tuple[RefinementEfficiencyRow, ...]
    reachable_steps: tuple[tuple[float, int], ...]
    cost_distribution: RefinementDistribution
    baseline_power: float | None
    power_error: str | None
    formula_label: str

    @property
    def target_row(self) -> RefinementTargetRow:
        """선택한 목표 단계의 결과 행 반환"""

        for row in self.rows:
            if row.target_step == self.target_step:
                return row

        raise RefinementInputError("목표 단계 결과가 없습니다.")


def point_price_from_bundle(bundle_price: float) -> float:
    """강화주머니 가격을 1pt 단가로 환산"""

    # 주머니 1개가 제공하는 포인트 수로 나눠 단가 계산
    return bundle_price / float(POINT_BUNDLE_SIZE)


def assist_points_from_thresholds(
    assist3_step: int,
    assist7_step: int,
) -> tuple[int, ...]:
    """`x단계 이상 3pt`, `y단계 이상 7pt` 규칙의 단계별 소모 포인트 구성"""

    # 단계별로 적용되는 보조를 결정
    points: list[int] = []
    for step in range(REFINE_ATTEMPT_STEP_COUNT):
        if step >= assist7_step:
            assist: RefinementAssist = RefinementAssist.POINT7

        elif step >= assist3_step:
            assist = RefinementAssist.POINT3

        else:
            assist = RefinementAssist.NONE

        points.append(REFINEMENT_ASSIST_SPECS[assist].points)

    return tuple(points)


def validate_strategy_thresholds(assist3_step: int, assist7_step: int) -> str | None:
    """사용자 전략 입력 조건 검증 후 오류 메시지 반환"""

    # 계획된 전략 형식은 0 ≤ x < y ≤ 19 만 허용
    last_attempt_step: int = REFINE_ATTEMPT_STEP_COUNT - 1
    if assist3_step < 0 or assist7_step > last_attempt_step:
        return f"보조 시작 단계는 0 ~ {last_attempt_step} 사이여야 합니다."

    if assist3_step >= assist7_step:
        return "3pt 시작 단계는 7pt 시작 단계보다 낮아야 합니다."

    return None


def build_plan(
    level_cap: int,
    use_refine_pet: bool,
    use_vip: bool,
    assist_points: tuple[int, ...],
) -> RefinementPlan:
    """단계별 재련비와 성공확률이 확정된 계산 조건 구성"""

    # 할인 배율과 기본 재련비로 단계별 비용 구성
    multiplier: float = refine_cost_multiplier(use_refine_pet, use_vip)
    base_costs: tuple[float, ...] = REFINE_BASE_COSTS[level_cap]
    costs: tuple[float, ...] = tuple(
        base_cost * multiplier for base_cost in base_costs
    )
    cost_units: tuple[int, ...] = tuple(
        int(round(base_cost / REFINE_COST_UNIT)) for base_cost in base_costs
    )

    # 보조 성공확률 증가량 반영
    point_bonus: dict[int, float] = {
        spec.points: spec.success_bonus for spec in REFINEMENT_ASSIST_SPECS.values()
    }
    success_rates: tuple[float, ...] = tuple(
        min(1.0, REFINE_BASE_SUCCESS_RATES[step] + point_bonus[assist_points[step]])
        for step in range(REFINE_ATTEMPT_STEP_COUNT)
    )

    return RefinementPlan(
        costs=costs,
        cost_units=cost_units,
        cost_unit_value=REFINE_COST_UNIT * multiplier,
        success_rates=success_rates,
        assist_points=assist_points,
    )


def _first_passage_weights(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
) -> list[float]:
    """단계별 첫 통과(s → s+1) 기대 소모량 계산"""

    # f_s = (w_s + 하락확률 × f_{s-1}) / p_s
    passage_weights: list[float] = []
    previous: float = 0.0
    for step in range(REFINE_ATTEMPT_STEP_COUNT):
        success_rate: float = success_rates[step]
        downgrade_rate: float = (1.0 - success_rate) * DOWNGRADE_RATE_ON_FAILURE
        current: float = (weights[step] + downgrade_rate * previous) / success_rate
        passage_weights.append(current)
        previous = current

    return passage_weights


def expected_weight_total(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
    start_step: int,
    target_step: int,
) -> float:
    """시작 단계에서 목표 단계까지의 기대 소모량 계산"""

    # 하락 후 복구까지 포함되도록 0강부터 재귀를 구성
    passage_weights: list[float] = _first_passage_weights(success_rates, weights)
    return float(sum(passage_weights[start_step:target_step]))


def compute_expected_totals(
    plan: RefinementPlan,
    start_step: int,
    target_step: int,
    point_price: float,
) -> ExpectedTotals:
    """목표 단계까지의 기대 소모량 묶음 계산"""

    success_rates: tuple[float, ...] = plan.success_rates

    # 시도당 소모량별 가중치 구성
    attempt_weights: tuple[float, ...] = (1.0,) * REFINE_ATTEMPT_STEP_COUNT
    success_weights: tuple[float, ...] = success_rates
    downgrade_weights: tuple[float, ...] = tuple(
        0.0
        if step == 0
        else (1.0 - success_rates[step]) * DOWNGRADE_RATE_ON_FAILURE
        for step in range(REFINE_ATTEMPT_STEP_COUNT)
    )
    point_weights: tuple[float, ...] = tuple(
        float(points) for points in plan.assist_points
    )

    cost: float = expected_weight_total(
        success_rates, plan.costs, start_step, target_step
    )
    points: float = expected_weight_total(
        success_rates, point_weights, start_step, target_step
    )
    attempts: float = expected_weight_total(
        success_rates, attempt_weights, start_step, target_step
    )
    successes: float = expected_weight_total(
        success_rates, success_weights, start_step, target_step
    )
    downgrades: float = expected_weight_total(
        success_rates, downgrade_weights, start_step, target_step
    )

    return ExpectedTotals(
        cost=cost,
        points=points,
        attempts=attempts,
        successes=successes,
        failures=attempts - successes,
        downgrades=downgrades,
        economic_cost=cost + points * point_price,
    )


def _select_grid_size(expected_units: float) -> int:
    """기대 소모량 기준 초기 격자 크기 결정"""

    # 기대값의 일정 배수를 덮는 2의 거듭제곱 격자 사용
    required: float = expected_units * float(_GRID_MEAN_FACTOR)
    grid_size: int = _MIN_GRID_SIZE
    while grid_size < required and grid_size < _MAX_GRID_SIZE:
        grid_size <<= 1

    return grid_size


def _build_pmfs(
    success_rates: tuple[float, ...],
    weight_units: tuple[int, ...],
    start_step: int,
    target_steps: tuple[int, ...],
    grid_size: int,
) -> dict[int, np.ndarray]:
    """확률생성함수를 격자에서 평가해 목표 단계별 분포 복원"""

    # 단위원 위 격자점 구성 (실수 신호이므로 절반만 사용)
    half_size: int = grid_size // 2 + 1
    angles: np.ndarray = 2.0 * np.pi * np.arange(half_size) / float(grid_size)
    grid_points: np.ndarray = np.exp(1j * angles)

    # 목표 단계별 누적곱과 복원 결과 저장
    max_target: int = max(target_steps)
    running_product: np.ndarray = np.ones(half_size, dtype=np.complex128)
    previous_pgf: np.ndarray = np.ones(half_size, dtype=np.complex128)
    pmfs: dict[int, np.ndarray] = {}

    target_step_set: set[int] = set(target_steps)
    for step in range(max_target):
        success_rate: float = success_rates[step]
        failure_rate: float = 1.0 - success_rate

        # 시도 1회 소모량에 해당하는 위상 이동
        shift: np.ndarray = grid_points ** weight_units[step]

        # 하락 시 아래 단계를 다시 통과해야 하므로 직전 단계 함수를 사용
        denominator: np.ndarray = 1.0 - failure_rate * shift * (
            (1.0 - DOWNGRADE_RATE_ON_FAILURE)
            + DOWNGRADE_RATE_ON_FAILURE * previous_pgf
        )
        current_pgf: np.ndarray = success_rate * shift / denominator

        # 시작 단계부터의 통과만 누적곱에 포함
        if step >= start_step:
            running_product = running_product * current_pgf

            if (step + 1) in target_step_set:
                pmfs[step + 1] = np.fft.irfft(np.conj(running_product), n=grid_size)

        previous_pgf = current_pgf

    return pmfs


def compute_distributions(
    success_rates: tuple[float, ...],
    weight_units: tuple[int, ...],
    unit_value: float,
    start_step: int,
    target_steps: tuple[int, ...],
) -> dict[int, RefinementDistribution]:
    """목표 단계별 누적 소모량 분포 계산"""

    # 소모량이 없는 전략은 0에 확률이 몰린 분포로 즉시 반환
    max_target: int = max(target_steps)
    if all(unit == 0 for unit in weight_units[start_step:max_target]):
        zero_pmf: np.ndarray = np.zeros(1, dtype=np.float64)
        zero_pmf[0] = 1.0
        return {
            target: RefinementDistribution(pmf=zero_pmf, unit_value=unit_value)
            for target in target_steps
        }

    # 최대 목표 단계 기대값 기준으로 격자 크기 결정
    float_weights: tuple[float, ...] = tuple(float(unit) for unit in weight_units)
    expected_units: float = expected_weight_total(
        success_rates,
        float_weights,
        start_step,
        max_target,
    )

    grid_size: int = _select_grid_size(expected_units)
    while True:
        pmfs: dict[int, np.ndarray] = _build_pmfs(
            success_rates,
            weight_units,
            start_step,
            target_steps,
            grid_size,
        )

        # 격자 끝부분에 남은 질량이 크면 접힘 오차가 커지므로 확장
        tail_mass: float = float(pmfs[max_target][grid_size * 3 // 4 :].sum())
        if tail_mass <= _GRID_TAIL_TOLERANCE or grid_size >= _MAX_GRID_SIZE:
            break

        grid_size <<= 1

    return {
        target: RefinementDistribution(pmf=pmf, unit_value=unit_value)
        for target, pmf in pmfs.items()
    }


def choose_auto_strategy(
    level_cap: int,
    use_refine_pet: bool,
    use_vip: bool,
    start_step: int,
    target_step: int,
    point_price: float,
) -> tuple[int, int] | None:
    """기대 경제적 총비용이 가장 낮은 전략 탐색

    무보조가 가장 좋으면 None을 반환한다.
    """

    # 무보조 기준값 계산
    best_thresholds: tuple[int, int] | None = None
    no_assist_points: tuple[int, ...] = (0,) * REFINE_ATTEMPT_STEP_COUNT
    no_assist_plan: RefinementPlan = build_plan(
        level_cap,
        use_refine_pet,
        use_vip,
        no_assist_points,
    )
    best_totals: ExpectedTotals = compute_expected_totals(
        no_assist_plan,
        start_step,
        target_step,
        point_price,
    )
    best_economic: float = best_totals.economic_cost
    best_cost: float = best_totals.cost

    # 유효한 모든 (x, y) 조합 전수 비교
    last_attempt_step: int = REFINE_ATTEMPT_STEP_COUNT - 1
    for assist3_step in range(0, last_attempt_step):
        for assist7_step in range(assist3_step + 1, last_attempt_step + 1):
            plan: RefinementPlan = build_plan(
                level_cap,
                use_refine_pet,
                use_vip,
                assist_points_from_thresholds(assist3_step, assist7_step),
            )
            totals: ExpectedTotals = compute_expected_totals(
                plan,
                start_step,
                target_step,
                point_price,
            )

            # 경제적 총비용이 같으면 기대 재련비가 적은 전략을 선택
            is_better: bool = totals.economic_cost < best_economic or (
                totals.economic_cost == best_economic and totals.cost < best_cost
            )
            if not is_better:
                continue

            best_economic = totals.economic_cost
            best_cost = totals.cost
            best_thresholds = (assist3_step, assist7_step)

    return best_thresholds


def resolve_strategy_choice(
    refinement: RefinementInput,
    strategies: tuple[RefinementStrategy, ...],
) -> RefinementStrategyChoice:
    """입력 상태 기준 실제 적용 전략 확정"""

    point_price: float = point_price_from_bundle(refinement.point_bundle_price)

    # 무보조 전략
    if refinement.strategy_mode == RefinementStrategyMode.NONE:
        return RefinementStrategyChoice(
            mode=RefinementStrategyMode.NONE,
            assist_points=(0,) * REFINE_ATTEMPT_STEP_COUNT,
            strategy_name="무보조",
            assist3_step=None,
            assist7_step=None,
        )

    # 자동 최적 전략
    if refinement.strategy_mode == RefinementStrategyMode.AUTO:
        thresholds: tuple[int, int] | None = choose_auto_strategy(
            refinement.level_cap,
            refinement.use_refine_pet,
            refinement.use_vip,
            refinement.start_step,
            refinement.target_step,
            point_price,
        )
        if thresholds is None:
            return RefinementStrategyChoice(
                mode=RefinementStrategyMode.AUTO,
                assist_points=(0,) * REFINE_ATTEMPT_STEP_COUNT,
                strategy_name="자동 최적",
                assist3_step=None,
                assist7_step=None,
            )

        return RefinementStrategyChoice(
            mode=RefinementStrategyMode.AUTO,
            assist_points=assist_points_from_thresholds(*thresholds),
            strategy_name="자동 최적",
            assist3_step=thresholds[0],
            assist7_step=thresholds[1],
        )

    # 저장한 사용자 전략
    for strategy in strategies:
        if strategy.id != refinement.selected_strategy_id:
            continue

        return RefinementStrategyChoice(
            mode=RefinementStrategyMode.USER,
            assist_points=assist_points_from_thresholds(
                strategy.assist3_step,
                strategy.assist7_step,
            ),
            strategy_name=strategy.name,
            assist3_step=strategy.assist3_step,
            assist7_step=strategy.assist7_step,
        )

    raise RefinementInputError("선택한 사용자 전략을 찾을 수 없습니다.")


def validate_refinement_input(
    refinement: RefinementInput,
    strategies: tuple[RefinementStrategy, ...],
) -> str | None:
    """재련 계산 입력 검증 후 오류 메시지 반환"""

    # 레벨제와 단계 범위 검증
    if refinement.level_cap not in REFINE_BASE_COSTS:
        return "레벨제를 선택해 주세요."

    if not 0 <= refinement.start_step < MAX_REFINE_STEP:
        return f"시작 단계는 0 ~ {MAX_REFINE_STEP - 1} 사이여야 합니다."

    if not refinement.start_step < refinement.target_step <= MAX_REFINE_STEP:
        return "목표 단계는 시작 단계보다 높고 20 이하여야 합니다."

    # 재화 입력 검증
    if refinement.budget < 0.0:
        return "보유 재화는 0 이상이어야 합니다."

    if refinement.point_bundle_price < 0.0:
        return "강화주머니 가격은 0 이상이어야 합니다."

    # 사용자 전략 선택 검증
    if refinement.strategy_mode == RefinementStrategyMode.USER:
        selected: RefinementStrategy | None = next(
            (
                strategy
                for strategy in strategies
                if strategy.id == refinement.selected_strategy_id
            ),
            None,
        )
        if selected is None:
            return "사용할 전략을 선택해 주세요."

        threshold_error: str | None = validate_strategy_thresholds(
            selected.assist3_step,
            selected.assist7_step,
        )
        if threshold_error is not None:
            return threshold_error

    return None


def _build_reachable_steps(
    rows: tuple[RefinementTargetRow, ...],
    start_step: int,
) -> tuple[tuple[float, int], ...]:
    """확률 기준별 현재 재화로 도달 가능한 최고 단계 계산"""

    reachable: list[tuple[float, int]] = []
    for probability in PREPARATION_PROBABILITIES:
        # 추가 재련 가능 여부와 관계없이 현재 단계까지는 이미 도달한 상태
        highest_step: int = start_step
        for row in rows:
            if row.reach_probability < probability:
                continue

            highest_step = row.target_step

        reachable.append((probability, highest_step))

    return tuple(reachable)


def build_refinement_report(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, "SkillUsageSetting"],
    delay_ms: int,
    base_stats: BaseStats,
    custom_formulas: tuple[CustomPowerFormula, ...],
    refinement: RefinementInput,
    strategies: tuple[RefinementStrategy, ...],
    formula_label: str,
    progress_callback: Callable[[str, int], None] | None = None,
    cancel_checker: Callable[[], None] | None = None,
) -> RefinementReport:
    """재련 시뮬레이터 전체 결과 구성"""

    # 입력 검증 후 적용 전략 확정
    input_error: str | None = validate_refinement_input(refinement, strategies)
    if input_error is not None:
        raise RefinementInputError(input_error)

    strategy: RefinementStrategyChoice = resolve_strategy_choice(
        refinement,
        strategies,
    )
    plan: RefinementPlan = build_plan(
        refinement.level_cap,
        refinement.use_refine_pet,
        refinement.use_vip,
        strategy.assist_points,
    )
    point_price: float = point_price_from_bundle(refinement.point_bundle_price)

    start_step: int = refinement.start_step
    target_steps: tuple[int, ...] = tuple(
        range(start_step + 1, MAX_REFINE_STEP + 1)
    )

    if progress_callback is not None:
        progress_callback("재련비 분포 계산 중...", 10)

    if cancel_checker is not None:
        cancel_checker()

    # 재련비 분포 계산
    cost_distributions: dict[int, RefinementDistribution] = compute_distributions(
        plan.success_rates,
        plan.cost_units,
        plan.cost_unit_value,
        start_step,
        target_steps,
    )

    if progress_callback is not None:
        progress_callback("강화포인트 분포 계산 중...", 45)

    if cancel_checker is not None:
        cancel_checker()

    # 강화포인트 분포 계산
    point_distributions: dict[int, RefinementDistribution] = compute_distributions(
        plan.success_rates,
        plan.assist_points,
        1.0,
        start_step,
        target_steps,
    )

    if progress_callback is not None:
        progress_callback("전투력 변화 계산 중...", 75)

    if cancel_checker is not None:
        cancel_checker()

    # 선택 공식 기준 평가 컨텍스트 구성 (실패 시 비용 분석만 제공)
    context: "EvaluationContext | None" = None
    baseline_power: float | None = None
    power_error: str | None = None
    try:
        context = build_calculator_context(
            server_spec=server_spec,
            preset=preset,
            skills_info=skills_info,
            delay_ms=delay_ms,
            base_stats=base_stats,
            target_formula_id=refinement.selected_formula_id,
            custom_formulas=custom_formulas,
        )
        baseline_power = context.baseline_power

    except (ValueError, KeyError, ZeroDivisionError) as error:
        power_error = str(error) or "전투력을 계산할 수 없습니다."

    # 0강 기준 단계별 효율 계산 입력 구성
    zero_step_power: float | None = None
    if context is not None:
        zero_step_power = context.baseline_power + evaluate_arbitrary_stat_delta(
            context,
            refinement_stat_delta(refinement.equipment, start_step, 0),
            refinement.selected_formula_id,
        )

    power_deltas_from_current: dict[int, float] = {}
    efficiency_rows: list[RefinementEfficiencyRow] = []
    for target_step in range(1, MAX_REFINE_STEP + 1):
        if cancel_checker is not None:
            cancel_checker()

        expected_from_zero: ExpectedTotals = compute_expected_totals(
            plan,
            0,
            target_step,
            point_price,
        )
        power_delta_from_zero: float | None = None
        if context is not None and zero_step_power is not None:
            power_delta_from_current: float = evaluate_arbitrary_stat_delta(
                context,
                refinement_stat_delta(
                    refinement.equipment,
                    start_step,
                    target_step,
                ),
                refinement.selected_formula_id,
            )
            power_deltas_from_current[target_step] = power_delta_from_current
            power_delta_from_zero = (
                context.baseline_power + power_delta_from_current - zero_step_power
            )

        efficiency_rows.append(
            RefinementEfficiencyRow(
                target_step=target_step,
                expected_economic_cost=expected_from_zero.economic_cost,
                power_delta=power_delta_from_zero,
            )
        )

    # 현재 시작 단계 기준 목표 단계별 결과 행 구성
    rows: list[RefinementTargetRow] = []
    for target_step in target_steps:
        if cancel_checker is not None:
            cancel_checker()

        expected: ExpectedTotals = compute_expected_totals(
            plan,
            start_step,
            target_step,
            point_price,
        )
        cost_distribution: RefinementDistribution = cost_distributions[target_step]
        point_distribution: RefinementDistribution = point_distributions[target_step]

        stat_delta: dict[StatKey, float] = refinement_stat_delta(
            refinement.equipment,
            start_step,
            target_step,
        )

        # 전투력 상승량과 비용 대비 효율 계산
        power_delta: float | None = None
        efficiency: float | None = None
        if context is not None:
            power_delta = power_deltas_from_current[target_step]
            if expected.economic_cost > 0.0:
                efficiency = power_delta / expected.economic_cost

        rows.append(
            RefinementTargetRow(
                target_step=target_step,
                reach_probability=cost_distribution.probability_at_most(
                    refinement.budget
                ),
                expected=expected,
                cost_quantiles=tuple(
                    cost_distribution.quantile(probability)
                    for probability in PREPARATION_PROBABILITIES
                ),
                point_quantiles=tuple(
                    point_distribution.quantile(probability)
                    for probability in PREPARATION_PROBABILITIES
                ),
                stat_delta=stat_delta,
                power_delta=power_delta,
                efficiency=efficiency,
            )
        )

    if progress_callback is not None:
        progress_callback("결과 정리 중...", 95)

    return RefinementReport(
        equipment=refinement.equipment,
        level_cap=refinement.level_cap,
        start_step=start_step,
        target_step=refinement.target_step,
        budget=refinement.budget,
        point_price=point_price,
        plan=plan,
        strategy=strategy,
        rows=tuple(rows),
        efficiency_rows=tuple(efficiency_rows),
        reachable_steps=_build_reachable_steps(tuple(rows), start_step),
        cost_distribution=cost_distributions[refinement.target_step],
        baseline_power=baseline_power,
        power_error=power_error,
        formula_label=formula_label,
    )
