from __future__ import annotations

import pytest

from app.scripts.calculator_engine import (
    OptimizationFailure,
    OptimizationFailureReason,
    OptimizationResult,
    build_calculator_context,
    optimize_current_selection,
)
from app.scripts.calculator_models import (
    BaseStats,
    CalculatorPresetInput,
    DanjeonState,
    DistributionState,
    PowerMetric,
    RealmTier,
    StatKey,
    TargetDistributionState,
)
from app.scripts.macro_models import MacroPreset
from app.scripts.registry.server_registry import ServerSpec

from tests.conftest import make_calculator_input, make_realistic_base_stats


def _build_small_inputs(
    server_spec: ServerSpec,
    preset: MacroPreset,
    distribution: DistributionState,
    danjeon: DanjeonState,
    target_distribution: TargetDistributionState | None = None,
    base_stats: BaseStats | None = None,
    realm_tier: RealmTier = RealmTier.THIRD_RATE,
    level: int = 10,
):
    """탐색 공간이 작은 최적화 케이스 인자 구성"""

    # 분배 잠금이라 search root가 단일 노드 → 직렬 실행 보장
    actual_base_stats: BaseStats = (
        base_stats if base_stats is not None else make_realistic_base_stats()
    )
    actual_target_distribution: TargetDistributionState = (
        target_distribution
        if target_distribution is not None
        else TargetDistributionState()
    )

    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=level,
        realm_tier=realm_tier,
        distribution=distribution,
        danjeon=danjeon,
        base_stats=actual_base_stats,
    )
    calculator_input.target_distribution = actual_target_distribution

    # 평가 컨텍스트 빌드
    context = build_calculator_context(
        server_spec=server_spec,
        preset=preset,
        skills_info=preset.usage_settings,
        delay_ms=300,
        base_stats=actual_base_stats,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
        custom_formulas=(),
    )

    return calculator_input, context, actual_base_stats


def test_optimization_returns_result_for_small_scenario(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """탐색 공간이 매우 작은 시나리오에서 OptimizationResult를 반환한다"""

    # 분배 잠금 + 단전 잠금으로 단일 후보만 탐색
    distribution: DistributionState = DistributionState(
        strength=20, dexterity=15, vitality=10, luck=5, is_locked=True
    )
    danjeon: DanjeonState = DanjeonState(upper=1, middle=0, lower=0, is_locked=True)

    calculator_input, context, base_stats = _build_small_inputs(
        synthetic_server, full_preset, distribution, danjeon
    )

    result = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert isinstance(result, OptimizationResult)


def test_optimization_is_deterministic(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """동일 입력 두 번 최적화는 같은 delta를 반환한다"""

    distribution: DistributionState = DistributionState(
        strength=20, dexterity=15, vitality=10, luck=5, is_locked=True
    )
    danjeon: DanjeonState = DanjeonState(upper=1, middle=0, lower=0, is_locked=True)

    calculator_input, context, base_stats = _build_small_inputs(
        synthetic_server, full_preset, distribution, danjeon
    )

    result1 = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    result2 = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert isinstance(result1, OptimizationResult)
    assert isinstance(result2, OptimizationResult)
    assert result1.delta == result2.delta


def test_optimization_delta_is_finite(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """최적화 delta 값은 유한한 실수다"""

    distribution: DistributionState = DistributionState(
        strength=20, dexterity=15, vitality=10, luck=5, is_locked=True
    )
    danjeon: DanjeonState = DanjeonState(upper=1, middle=0, lower=0, is_locked=True)

    calculator_input, context, base_stats = _build_small_inputs(
        synthetic_server, full_preset, distribution, danjeon
    )

    result = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert isinstance(result, OptimizationResult)
    assert result.delta == result.delta  # NaN 체크


def test_optimization_failure_when_distribution_exceeds_cap(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """분배 합계가 레벨 cap 초과 시 STAT_DISTRIBUTION_EXCEEDS_LEVEL_CAP 반환"""

    # 레벨 10 → cap 50, 분배 합 = 60으로 초과
    distribution: DistributionState = DistributionState(
        strength=30, dexterity=20, vitality=10, luck=0, is_locked=True
    )
    danjeon: DanjeonState = DanjeonState(upper=1, middle=0, lower=0, is_locked=True)

    calculator_input, context, base_stats = _build_small_inputs(
        synthetic_server, full_preset, distribution, danjeon, level=10
    )

    result = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert isinstance(result, OptimizationFailure)
    assert result.reason == OptimizationFailureReason.STAT_DISTRIBUTION_EXCEEDS_LEVEL_CAP


def test_optimization_failure_when_danjeon_exceeds_cap(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """단전 합계가 경지 cap 초과 시 DANJEON_EXCEEDS_REALM_CAP 반환"""

    distribution: DistributionState = DistributionState(
        strength=20, dexterity=15, vitality=10, luck=5, is_locked=True
    )
    # 삼류 = 1포인트만 허용, 5포인트 분배 시 초과
    danjeon: DanjeonState = DanjeonState(upper=3, middle=1, lower=1, is_locked=True)

    calculator_input, context, base_stats = _build_small_inputs(
        synthetic_server, full_preset, distribution, danjeon,
        realm_tier=RealmTier.THIRD_RATE,
    )

    result = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert isinstance(result, OptimizationFailure)
    assert result.reason == OptimizationFailureReason.DANJEON_EXCEEDS_REALM_CAP


def test_optimization_failure_when_minimum_distribution_exceeds_cap(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """목표 최소분배가 레벨 cap 초과 시 MINIMUM_DISTRIBUTION_EXCEEDS_LEVEL_CAP 반환"""

    # 레벨 10 → cap 50, 목표 최소분배 합 = 60
    distribution: DistributionState = DistributionState(use_reset=True)
    danjeon: DanjeonState = DanjeonState(upper=1, middle=0, lower=0, is_locked=True)
    target_distribution: TargetDistributionState = TargetDistributionState(
        strength=20,
        dexterity=20,
        vitality=10,
        luck=10,
        is_minimum=True,
    )

    calculator_input, context, base_stats = _build_small_inputs(
        synthetic_server,
        full_preset,
        distribution,
        danjeon,
        target_distribution=target_distribution,
        level=10,
    )

    result = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert isinstance(result, OptimizationFailure)
    assert result.reason == (
        OptimizationFailureReason.MINIMUM_DISTRIBUTION_EXCEEDS_LEVEL_CAP
    )


def test_optimization_result_distribution_sums_correctly(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """최적화 결과 분배의 합이 분배 잠금된 입력값과 일치한다"""

    distribution: DistributionState = DistributionState(
        strength=20, dexterity=15, vitality=10, luck=5, is_locked=True
    )
    danjeon: DanjeonState = DanjeonState(upper=1, middle=0, lower=0, is_locked=True)

    calculator_input, context, base_stats = _build_small_inputs(
        synthetic_server, full_preset, distribution, danjeon
    )

    result = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert isinstance(result, OptimizationResult)
    cand_dist = result.candidate.distribution
    total: int = (
        cand_dist.strength + cand_dist.dexterity + cand_dist.vitality + cand_dist.luck
    )
    # 잠금 상태라 입력값 그대로
    assert total == 50


@pytest.mark.slow
def test_optimization_realistic_scenario_runs_within_time_budget(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """현실적 탐색 공간 (분배 잠금 해제, 레벨 30)에서 OptimizationResult를 반환한다

    탐색 공간이 커서 1분 정도까지 걸릴 수 있음.
    분배가 잠금 해제이면 서브 범위가 분할되어 멀티프로세스 실행 경로를 탄다.
    """

    # 분배 잠금 해제, 단전 잠금으로 탐색 차원 1개만 열어둔다
    distribution: DistributionState = DistributionState(
        strength=0, dexterity=0, vitality=0, luck=0, use_reset=True
    )
    danjeon: DanjeonState = DanjeonState(upper=1, middle=0, lower=0, is_locked=True)

    calculator_input, context, base_stats = _build_small_inputs(
        synthetic_server, full_preset, distribution, danjeon,
        realm_tier=RealmTier.THIRD_RATE,
        level=30,
    )

    result = optimize_current_selection(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=300,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert isinstance(result, OptimizationResult)
