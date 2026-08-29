"""재련 시뮬레이터 계산 엔진

상태 전이는 다음 규칙을 따른다.

- 시도 전에 현재 단계의 재련비와 보조 강화포인트를 소모한다.
- 성공하면 1단계 상승한다.
- 실패하면 남은 실패확률에 하락 60%, 유지 40%를 적용한다.
- 0강에서 하락하면 0강을 유지한다.

기대값은 단계별 첫 통과(현재 단계 → 다음 단계) 재귀로 정확히 계산하고,
분포와 분위수는 첫 통과 확률생성함수를 단위원 격자에서 평가한 뒤
역푸리에 변환으로 복원한다.

분포 격자는 다음 세 가지를 지킨다.

- 시도 1회 소모량이 격자 배수가 아니면 인접한 두 격자에 소수부 비율대로
  나눠 싣는다. 기대 소모량이 정확히 보존되므로 재련비와 강화포인트
  환산액을 함께 다루면서도 격자를 잘게 쪼갤 필요가 없다.
- 필요한 표현 범위는 저해상도 격자로 먼저 찾는다. 끝부분에 남는 질량은
  분해능이 아니라 표현 범위에 따라 정해지므로 실해상도 격자를 여러 번
  다시 만들지 않아도 된다.
- 표현 범위가 격자 크기 상한을 넘으면 크기 대신 단위를 넓힌다. 계산량과
  메모리 사용량이 소모량 규모와 무관하게 일정한 범위에 머문다.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
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
    REFINEMENT_STAT_KEYS,
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
_MAX_GRID_SIZE: int = 1 << 20

# 표현 범위 탐색 시작점으로 쓰는 기대값 배수와 꼬리 허용 질량
_GRID_MEAN_FACTOR: int = 8
_GRID_TAIL_TOLERANCE: float = 1e-7

# 평균 보존 분배로 생기는 흐림의 허용 상한 (평균 대비 표준편차 비율)
#
# 시도 1회 비용이 격자 배수가 아니면 인접한 두 격자에 평균이 보존되도록
# 나눠 싣는다. 이때 시도마다 최대 unit/2 의 표준편차가 더해지므로,
# 누적 흐림이 평균의 이 비율을 넘지 않는 범위에서만 격자를 넓힌다.
_MAX_SPLIT_BLUR_RATIO: float = 1e-3


class RefinementInputError(ValueError):
    """재련 계산 입력 오류"""


@dataclass(frozen=True, slots=True)
class RefinementPlan:
    """전략까지 확정된 단계별 재련 조건"""

    # 단계별 실제 재련비 (할인 반영)
    costs: tuple[float, ...]
    # 분포 계산에 쓰는 기본 격자 단위 1개당 재련비
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
            cumulative_probability: float = float(self.pmf.sum())
        else:
            cumulative_probability = float(self.pmf[: unit_count + 1].sum())

        # 푸리에 역변환의 미세한 수치 오차가 확률 범위를 벗어나지 않도록 제한
        return min(1.0, max(0.0, cumulative_probability))

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
    """유효한 최저 단계 기준 목표 단계 하나의 효율 계산 입력"""

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
    economic_cost_distribution: RefinementDistribution
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


def _split_shift(
    grid_points: np.ndarray,
    weight: float,
    unit_value: float,
) -> np.ndarray:
    """시도 1회 소모량의 생성함수 반환 (평균 보존 분배)

    소모량이 격자 배수가 아니면 인접한 두 격자에 나눠 싣는다. 배분 비율을
    소수부와 맞추므로 기대 소모량이 정확히 보존되고, 격자 배수로 반올림할
    때 생기는 계통 오차가 사라진다.
    """

    # 격자 개수와 소수부 분리
    scaled: float = weight / unit_value
    lower_count: int = int(np.floor(scaled + 1e-9))
    upper_ratio: float = scaled - float(lower_count)

    base: np.ndarray = grid_points**lower_count
    if upper_ratio <= 1e-12:
        return base

    # (1-f)·z^k + f·z^(k+1) 를 z^k 로 묶어 거듭제곱 1회로 계산
    return base * (1.0 - upper_ratio + upper_ratio * grid_points)


def _max_split_unit(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
    base_unit: float,
    start_step: int,
    target_step: int,
) -> float:
    """분배 흐림이 허용 범위를 넘지 않는 최대 격자 단위 반환"""

    expected_value: float = expected_weight_total(
        success_rates, weights, start_step, target_step
    )
    attempt_weights: tuple[float, ...] = (1.0,) * REFINE_ATTEMPT_STEP_COUNT
    expected_attempts: float = expected_weight_total(
        success_rates, attempt_weights, start_step, target_step
    )
    if expected_attempts <= 0.0 or expected_value <= 0.0:
        return base_unit

    # 시도당 분배 분산은 최대 unit²/4 이므로 누적 표준편차는 unit/2·√n
    blur_limited_unit: float = (
        2.0 * _MAX_SPLIT_BLUR_RATIO * expected_value / expected_attempts**0.5
    )
    return max(base_unit, blur_limited_unit)


def _iter_target_distributions(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
    unit_value: float,
    start_step: int,
    target_steps: tuple[int, ...],
    grid_size: int,
    progress_callback: Callable[[int], None] | None = None,
    cancel_checker: Callable[[], None] | None = None,
) -> "Iterator[tuple[int, RefinementDistribution]]":
    """목표 단계별 누적 소모량 분포를 낮은 단계부터 하나씩 복원

    누적곱을 목표 단계 수만큼 모아 두면 메모리 사용량이 격자 크기에
    비례해 커지므로, 목표 단계에 닿을 때마다 곧바로 역변환해 넘긴다.
    """

    # 단위원 위 격자점 구성 (실수 신호이므로 절반만 사용)
    half_size: int = grid_size // 2 + 1
    angles: np.ndarray = 2.0 * np.pi * np.arange(half_size) / float(grid_size)
    grid_points: np.ndarray = np.exp(1j * angles)

    max_target: int = max(target_steps)
    target_step_set: set[int] = set(target_steps)
    done_count: int = 0

    running_product: np.ndarray = np.ones(half_size, dtype=np.complex128)
    previous_pgf: np.ndarray = np.ones(half_size, dtype=np.complex128)
    for step in range(max_target):
        if cancel_checker is not None:
            cancel_checker()

        success_rate: float = success_rates[step]
        failure_rate: float = 1.0 - success_rate

        # 시도 1회 소모량에 해당하는 생성함수
        shift: np.ndarray = _split_shift(grid_points, weights[step], unit_value)

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
                pmf: np.ndarray = np.fft.irfft(
                    np.conj(running_product), n=grid_size
                )
                yield step + 1, RefinementDistribution(
                    pmf=pmf,
                    unit_value=unit_value,
                )

                done_count += 1
                if progress_callback is not None:
                    progress_callback(done_count * 100 // len(target_steps))

        previous_pgf = current_pgf


def _is_zero_weight_range(
    weights: tuple[float, ...],
    start_step: int,
    target_step: int,
) -> bool:
    """구간 내 소모량이 전부 0인지 여부 반환"""

    return all(weight == 0.0 for weight in weights[start_step:target_step])


def _zero_distribution(unit_value: float) -> "RefinementDistribution":
    """0에 확률이 몰린 분포 반환"""

    zero_pmf: np.ndarray = np.zeros(1, dtype=np.float64)
    zero_pmf[0] = 1.0
    return RefinementDistribution(pmf=zero_pmf, unit_value=unit_value)


# 표현 범위 탐색에 쓰는 저해상도 격자 크기
_PROBE_GRID_SIZE: int = 1 << 16

# 저해상도 탐색은 분해능 손실을 감안해 더 엄격한 기준을 적용
_PROBE_TOLERANCE_MARGIN: float = 0.01


def _tail_mass(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
    unit_value: float,
    start_step: int,
    target_step: int,
    grid_size: int,
    cancel_checker: Callable[[], None] | None = None,
) -> float:
    """지정 격자에서 끝부분에 남는 확률 질량 반환"""

    _, distribution = next(
        iter(
            _iter_target_distributions(
                success_rates,
                weights,
                unit_value,
                start_step,
                (target_step,),
                grid_size,
                cancel_checker=cancel_checker,
            )
        )
    )
    return float(distribution.pmf[grid_size * 3 // 4 :].sum())


def _probe_value_range(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
    start_step: int,
    target_step: int,
    cancel_checker: Callable[[], None] | None = None,
) -> float:
    """접힘 오차가 허용 범위에 드는 최소 표현 범위 탐색

    끝부분에 남는 질량은 분해능이 아니라 표현 범위에 따라 정해지므로,
    실제 계산보다 훨씬 작은 격자로 범위만 먼저 찾아 둔다. 이렇게 하면
    실해상도 격자를 여러 번 다시 만들지 않아도 된다.
    """

    expected_value: float = expected_weight_total(
        success_rates, weights, start_step, target_step
    )
    value_range: float = expected_value * float(_GRID_MEAN_FACTOR)
    tolerance: float = _GRID_TAIL_TOLERANCE * _PROBE_TOLERANCE_MARGIN

    # 표현 범위를 2배씩 넓히며 꼬리 질량이 기준 아래로 내려가는 지점 탐색
    while value_range < expected_value * float(1 << 20):
        tail_mass: float = _tail_mass(
            success_rates,
            weights,
            value_range / float(_PROBE_GRID_SIZE),
            start_step,
            target_step,
            _PROBE_GRID_SIZE,
            cancel_checker,
        )
        if tail_mass <= tolerance:
            return value_range

        value_range *= 2.0

    return value_range


def resolve_grid(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
    base_unit: float,
    start_step: int,
    target_step: int,
    cancel_checker: Callable[[], None] | None = None,
) -> tuple[float, int]:
    """접힘 오차가 허용 범위에 들도록 격자 단위와 크기 결정

    격자를 넓히는 방법은 두 가지다. 크기를 키우면 분해능을 유지한 채
    표현 범위가 늘지만 계산량도 함께 는다. 단위를 키우면 계산량 그대로
    표현 범위만 는 대신 분배 흐림이 커진다. 계산량이 상한에 닿기 전까지는
    크기를 키우고, 그 뒤에는 흐림 허용치까지 단위를 키운다.
    """

    value_range: float = _probe_value_range(
        success_rates,
        weights,
        start_step,
        target_step,
        cancel_checker,
    )
    max_unit: float = _max_split_unit(
        success_rates, weights, base_unit, start_step, target_step
    )

    # 필요한 표현 범위를 담을 수 있는 최소 격자 구성
    unit_value: float = base_unit
    while True:
        grid_size: int = _MIN_GRID_SIZE
        while (
            float(grid_size) * unit_value < value_range
            and grid_size < _MAX_GRID_SIZE
        ):
            grid_size <<= 1

        if float(grid_size) * unit_value >= value_range:
            return unit_value, grid_size

        # 계산량 상한에 닿았으면 흐림 허용치 안에서 단위를 넓힌다
        if unit_value * 2.0 > max_unit:
            return unit_value, grid_size

        unit_value *= 2.0


def compute_distributions(
    success_rates: tuple[float, ...],
    weight_units: tuple[float, ...],
    unit_value: float,
    start_step: int,
    target_steps: tuple[int, ...],
) -> dict[int, RefinementDistribution]:
    """목표 단계별 누적 소모량 분포 계산"""

    # 소모량이 없는 전략은 0에 확률이 몰린 분포로 즉시 반환
    max_target: int = max(target_steps)
    if _is_zero_weight_range(weight_units, start_step, max_target):
        return {
            target: _zero_distribution(unit_value) for target in target_steps
        }

    resolved_unit, grid_size = resolve_grid(
        success_rates,
        weight_units,
        unit_value,
        start_step,
        max_target,
    )
    return dict(
        _iter_target_distributions(
            success_rates,
            weight_units,
            resolved_unit,
            start_step,
            target_steps,
            grid_size,
        )
    )


@dataclass(frozen=True, slots=True)
class DistributionSummary:
    """분포에서 화면 표시에 필요한 값만 추린 결과

    목표 단계마다 전체 분포 배열을 들고 있으면 메모리 사용량이 크게 늘어
    그래프로 그리는 한 단계만 분포를 남기고 나머지는 이 요약만 보관한다.
    """

    # 기준값 이하로 끝날 확률 (기준값이 없으면 0)
    reach_probability: float
    # PREPARATION_PROBABILITIES 순서에 대응하는 분위수
    quantiles: tuple[float, ...]


def _summarize(
    distribution: "RefinementDistribution",
    reach_threshold: float | None,
) -> DistributionSummary:
    """분포에서 도달 확률과 분위수 추출"""

    return DistributionSummary(
        reach_probability=(
            0.0
            if reach_threshold is None
            else distribution.probability_at_most(reach_threshold)
        ),
        quantiles=tuple(
            distribution.quantile(probability)
            for probability in PREPARATION_PROBABILITIES
        ),
    )


def compute_distribution_series(
    success_rates: tuple[float, ...],
    weights: tuple[float, ...],
    base_unit: float,
    start_step: int,
    target_steps: tuple[int, ...],
    reach_threshold: float | None = None,
    detail_target: int | None = None,
    progress_callback: Callable[[int], None] | None = None,
    cancel_checker: Callable[[], None] | None = None,
) -> tuple[dict[int, DistributionSummary], RefinementDistribution | None]:
    """목표 단계별 분포 요약과 지정 단계의 전체 분포 계산

    목표 단계별 분포를 하나씩 복원해 요약만 남기고 즉시 버린다.
    """

    max_target: int = max(target_steps)

    # 소모량이 없는 전략은 0에 확률이 몰린 분포로 즉시 반환
    if _is_zero_weight_range(weights, start_step, max_target):
        zero: RefinementDistribution = _zero_distribution(base_unit)
        summary: DistributionSummary = _summarize(zero, reach_threshold)
        return (
            {target: summary for target in target_steps},
            None if detail_target is None else zero,
        )

    resolved_unit, grid_size = resolve_grid(
        success_rates,
        weights,
        base_unit,
        start_step,
        max_target,
        cancel_checker,
    )
    summaries: dict[int, DistributionSummary] = {}
    detail: RefinementDistribution | None = None
    for target, distribution in _iter_target_distributions(
        success_rates,
        weights,
        resolved_unit,
        start_step,
        target_steps,
        grid_size,
        progress_callback,
        cancel_checker,
    ):
        summaries[target] = _summarize(distribution, reach_threshold)

        # 그래프로 그리는 단계만 분포를 남기고 나머지는 곧바로 버린다
        if target == detail_target:
            detail = distribution

    return summaries, detail


def compute_economic_cost_distribution(
    plan: RefinementPlan,
    point_price: float,
    start_step: int,
    target_step: int,
) -> RefinementDistribution:
    """재련비와 강화포인트 환산액을 합친 총 비용 분포 계산"""

    return compute_distributions(
        plan.success_rates,
        economic_attempt_costs(plan, point_price),
        plan.cost_unit_value,
        start_step,
        (target_step,),
    )[target_step]


def economic_attempt_costs(
    plan: RefinementPlan,
    point_price: float,
) -> tuple[float, ...]:
    """시도 1회당 재련비와 강화포인트 환산액을 합친 소모량 반환"""

    return tuple(
        cost + points * point_price
        for cost, points in zip(plan.costs, plan.assist_points)
    )


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

    def report_stage(message: str, base: int, span: int) -> Callable[[int], None]:
        """분포 계산 진행률을 전체 진행률 구간으로 환산하는 콜백 구성"""

        def on_progress(ratio: int) -> None:
            if progress_callback is not None:
                progress_callback(message, base + span * ratio // 100)

        return on_progress

    if progress_callback is not None:
        progress_callback("재련비 분포 계산 중...", 0)

    if cancel_checker is not None:
        cancel_checker()

    # 재련비 분포 계산 (그래프에 쓰는 목표 단계만 전체 분포 유지)
    cost_summaries: dict[int, DistributionSummary]
    cost_distribution: RefinementDistribution | None
    cost_summaries, cost_distribution = compute_distribution_series(
        plan.success_rates,
        plan.costs,
        plan.cost_unit_value,
        start_step,
        target_steps,
        reach_threshold=refinement.budget,
        detail_target=refinement.target_step,
        progress_callback=report_stage("재련비 분포 계산 중...", 0, 45),
        cancel_checker=cancel_checker,
    )

    if progress_callback is not None:
        progress_callback("강화포인트 분포 계산 중...", 45)

    # 강화포인트 분포 계산 (표에 분위수만 쓰므로 요약만 유지)
    point_summaries: dict[int, DistributionSummary]
    point_summaries, _ = compute_distribution_series(
        plan.success_rates,
        tuple(float(points) for points in plan.assist_points),
        1.0,
        start_step,
        target_steps,
        progress_callback=report_stage("강화포인트 분포 계산 중...", 45, 45),
        cancel_checker=cancel_checker,
    )

    if progress_callback is not None:
        progress_callback("총 비용 분포 계산 중...", 90)

    # 총 비용 분포 계산 (그래프에 쓰는 선택 목표 단계만 필요)
    economic_distribution: RefinementDistribution | None
    _, economic_distribution = compute_distribution_series(
        plan.success_rates,
        economic_attempt_costs(plan, point_price),
        plan.cost_unit_value,
        start_step,
        (refinement.target_step,),
        detail_target=refinement.target_step,
        progress_callback=report_stage("총 비용 분포 계산 중...", 90, 9),
        cancel_checker=cancel_checker,
    )

    if cost_distribution is None or economic_distribution is None:
        raise RefinementInputError("비용 분포를 계산하지 못했습니다.")

    if progress_callback is not None:
        progress_callback("전투력 변화 계산 중...", 99)

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

    # 역산한 베이스 스탯이 음수가 아닌 최저 재련 단계 결정
    efficiency_baseline_step: int | None = None
    if context is not None:
        refinement_stat_keys: tuple[StatKey, StatKey, StatKey] = REFINEMENT_STAT_KEYS[
            refinement.equipment
        ]
        for candidate_step in range(MAX_REFINE_STEP + 1):
            candidate_base_stats: BaseStats = context.baseline_base_stats.with_changes(
                refinement_stat_delta(
                    refinement.equipment,
                    start_step,
                    candidate_step,
                )
            )
            if any(
                candidate_base_stats.values[stat_key.value] < 0.0
                for stat_key in refinement_stat_keys
            ):
                continue

            efficiency_baseline_step = candidate_step
            break

    # 현재 시작 단계 기준 전투력 변화량 공유 캐시 구성
    power_deltas_from_current: dict[int, float] = {}
    if context is not None:
        for target_step in range(1, MAX_REFINE_STEP + 1):
            if cancel_checker is not None:
                cancel_checker()

            power_deltas_from_current[target_step] = evaluate_arbitrary_stat_delta(
                context,
                refinement_stat_delta(
                    refinement.equipment,
                    start_step,
                    target_step,
                ),
                refinement.selected_formula_id,
            )

    # 유효한 최저 단계부터의 누적 비용과 전투력 기준 효율 구성
    efficiency_rows: list[RefinementEfficiencyRow] = []
    if context is not None and efficiency_baseline_step is not None:
        baseline_power_delta: float = evaluate_arbitrary_stat_delta(
            context,
            refinement_stat_delta(
                refinement.equipment,
                start_step,
                efficiency_baseline_step,
            ),
            refinement.selected_formula_id,
        )
        for target_step in range(efficiency_baseline_step + 1, MAX_REFINE_STEP + 1):
            if cancel_checker is not None:
                cancel_checker()

            expected_from_baseline: ExpectedTotals = compute_expected_totals(
                plan,
                efficiency_baseline_step,
                target_step,
                point_price,
            )
            efficiency_rows.append(
                RefinementEfficiencyRow(
                    target_step=target_step,
                    expected_economic_cost=expected_from_baseline.economic_cost,
                    power_delta=(
                        power_deltas_from_current[target_step] - baseline_power_delta
                    ),
                )
            )
    elif context is None:
        for target_step in range(1, MAX_REFINE_STEP + 1):
            if cancel_checker is not None:
                cancel_checker()

            expected_from_zero: ExpectedTotals = compute_expected_totals(
                plan,
                0,
                target_step,
                point_price,
            )
            efficiency_rows.append(
                RefinementEfficiencyRow(
                    target_step=target_step,
                    expected_economic_cost=expected_from_zero.economic_cost,
                    power_delta=None,
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
        cost_summary: DistributionSummary = cost_summaries[target_step]
        point_summary: DistributionSummary = point_summaries[target_step]

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
                reach_probability=cost_summary.reach_probability,
                expected=expected,
                cost_quantiles=cost_summary.quantiles,
                point_quantiles=point_summary.quantiles,
                stat_delta=stat_delta,
                power_delta=power_delta,
                efficiency=efficiency,
            )
        )

    if progress_callback is not None:
        progress_callback("결과 정리 중...", 99)

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
        cost_distribution=cost_distribution,
        economic_cost_distribution=economic_distribution,
        baseline_power=baseline_power,
        power_error=power_error,
        formula_label=formula_label,
    )
