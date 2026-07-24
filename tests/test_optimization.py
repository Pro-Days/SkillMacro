from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor

import pytest

from app.scripts.calculator_engine import (
    Contribution,
    EvaluationContext,
    OptimizationFailure,
    OptimizationFailureReason,
    OptimizationResult,
    CandidateGroupSelectionResult,
    build_base_state,
    build_calculator_context,
    build_danjeon_contribution,
    build_distribution_contribution,
    build_internal_base_stats,
    evaluate_single_metric,
    optimize_current_selection,
    select_candidate_groups,
)
from app.scripts.calculator_models import (
    BaseStats,
    CalculatorPresetInput,
    DanjeonState,
    DistributionState,
    FinalStats,
    OptimizationCandidateGroup,
    OptimizationCandidateOption,
    OptimizationCandidateStat,
    PowerMetric,
    RealmTier,
    StatKey,
    TargetDanjeonState,
    TargetDistributionState,
)
from app.scripts.macro_models import MacroPreset
from app.scripts.registry.server_registry import ServerSpec
from tests.conftest import (
    build_full_equipped_preset,
    build_synthetic_server,
    make_calculator_input,
    make_realistic_base_stats,
)

# 최적화 테스트 공통 딜레이 입력값
DELAY_MS: int = 300


@pytest.fixture
def small_server() -> ServerSpec:
    """최적화 계산량 축소용 2비급 4스킬 합성 서버"""

    return build_synthetic_server(scroll_count=2)


@pytest.fixture
def small_preset(small_server: ServerSpec) -> MacroPreset:
    """소형 합성 서버 기준 풀 장착 프리셋"""

    return build_full_equipped_preset(small_server)


@pytest.fixture
def serial_search(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """최적화 탐색의 단일 프로세스 직렬 실행 강제"""

    # 워커 수 1 기준 서브 범위 축소로 프로세스 풀 생성 회피
    import os

    monkeypatch.setattr(os, "cpu_count", lambda: 1)

    yield


def _build_context(
    server_spec: ServerSpec,
    preset: MacroPreset,
    base_stats: BaseStats,
) -> EvaluationContext:
    """보스 데미지 공식 기준 평가 컨텍스트 구성"""

    return build_calculator_context(
        server_spec=server_spec,
        preset=preset,
        skills_info=preset.usage_settings,
        delay_ms=DELAY_MS,
        base_stats=base_stats,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
        custom_formulas=(),
    )


def _brute_force_delta(
    context: EvaluationContext,
    base_stats: BaseStats,
    calculator_input: CalculatorPresetInput,
    distribution: DistributionState,
    danjeon: DanjeonState,
) -> float:
    """단일 분배/단전 후보의 전투력 변화 직접 계산"""

    # 현재 선택 기여를 제거한 기준 베이스에 후보 기여 적용
    base_state = build_base_state(base_stats, calculator_input)
    contribution: Contribution = Contribution().merge(
        build_distribution_contribution(distribution),
        build_danjeon_contribution(danjeon),
    )
    candidate_base: BaseStats = contribution.apply_to(base_state.base_stats)

    # 분배/단전은 스킬속도에 영향이 없어 기준 타임라인 재사용
    target_value: float = evaluate_single_metric(
        artifacts=context.timeline_artifacts,
        resolved_stats=candidate_base.resolve(),
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
        compiled_custom_formula=None,
    )
    return target_value - context.baseline_power


def _run_optimize(
    server_spec: ServerSpec,
    preset: MacroPreset,
    base_stats: BaseStats,
    calculator_input: CalculatorPresetInput,
) -> OptimizationResult | OptimizationFailure:
    """공통 인자 기준 최적화 실행"""

    context: EvaluationContext = _build_context(server_spec, preset, base_stats)
    return optimize_current_selection(
        server_spec=server_spec,
        preset=preset,
        skills_info=preset.usage_settings,
        delay_ms=DELAY_MS,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
        cancel_checker=lambda: None,
    )


def test_distribution_contribution_matches_hand_values() -> None:
    """스탯 분배 기여의 손계산 수치 고정 검증

    분배 1포인트 = 해당 기본 스탯 +1.
    전수조사 비교 테스트가 이 헬퍼를 기준값 계산에 재사용하므로,
    기여 수치 자체는 여기서 리터럴로 고정해야 회귀가 검출된다.
    """

    contribution: Contribution = build_distribution_contribution(
        DistributionState(strength=3, dexterity=2, vitality=1, luck=4)
    )

    assert contribution.values == {
        StatKey.STR: 3.0,
        StatKey.DEXTERITY: 2.0,
        StatKey.VITALITY: 1.0,
        StatKey.LUCK: 4.0,
    }


def test_danjeon_contribution_matches_hand_values() -> None:
    """단전 기여의 손계산 수치 고정 검증

    상단전 1포인트: 체력% +3, 저항% +1
    중단전 1포인트: 공격력% +1
    하단전 1포인트: 드랍률% +1.5, 경험치% +0.5
    """

    contribution: Contribution = build_danjeon_contribution(
        DanjeonState(upper=2, middle=3, lower=4)
    )

    assert contribution.values == {
        StatKey.HP_PERCENT: 6.0,
        StatKey.RESIST_PERCENT: 2.0,
        StatKey.ATTACK_PERCENT: 3.0,
        StatKey.DROP_RATE_PERCENT: 6.0,
        StatKey.EXP_PERCENT: 2.0,
    }


def test_danjeon_optimization_matches_brute_force(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    serial_search: None,
) -> None:
    """단전 단독 최적화의 전수조사 일치 검증"""

    # 분배 잠금 + 단전 초기화 탐색 구성 (일류 5포인트)
    base_stats: BaseStats = make_realistic_base_stats()
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=100,
        realm_tier=RealmTier.FIRST_RATE,
        distribution=DistributionState(
            strength=100, dexterity=50, vitality=30, luck=20, is_locked=True
        ),
        danjeon=DanjeonState(upper=1, middle=1, lower=1, use_reset=True),
        base_stats=base_stats,
    )

    result: OptimizationResult | OptimizationFailure = _run_optimize(
        small_server, small_preset, base_stats, calculator_input
    )

    assert isinstance(result, OptimizationResult)

    # 잠금 분배 유지 확인
    assert result.candidate.distribution.strength == 100
    assert result.candidate.distribution.dexterity == 50
    assert result.candidate.distribution.vitality == 30
    assert result.candidate.distribution.luck == 20

    # 전수조사 기준 최적 delta 계산 (5포인트 전체 조합)
    context: EvaluationContext = _build_context(small_server, small_preset, base_stats)
    total_points: int = 5
    best_delta: float | None = None
    for upper in range(total_points + 1):
        for middle in range(total_points - upper + 1):
            lower: int = total_points - upper - middle
            delta: float = _brute_force_delta(
                context,
                base_stats,
                calculator_input,
                calculator_input.distribution,
                DanjeonState(upper=upper, middle=middle, lower=lower),
            )
            if best_delta is None or delta > best_delta:
                best_delta = delta

    assert best_delta is not None
    assert result.delta == pytest.approx(best_delta, rel=1e-9)

    # 보스 데미지 기준 중단전(공격력%) 집중 최적해 확인
    assert result.candidate.danjeon.middle == total_points
    assert result.candidate.danjeon.upper == 0
    assert result.candidate.danjeon.lower == 0


def test_distribution_optimization_matches_brute_force(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    serial_search: None,
) -> None:
    """스탯 분배 최적화의 전수조사 일치 검증"""

    # 분배 초기화 탐색 + 단전 잠금 구성 (레벨 1, 5포인트)
    base_stats: BaseStats = make_realistic_base_stats()
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=1,
        realm_tier=RealmTier.THIRD_RATE,
        distribution=DistributionState(use_reset=True),
        danjeon=DanjeonState(is_locked=True),
        base_stats=base_stats,
    )

    result: OptimizationResult | OptimizationFailure = _run_optimize(
        small_server, small_preset, base_stats, calculator_input
    )

    assert isinstance(result, OptimizationResult)

    # 전수조사 기준 최적 delta 계산 (5포인트 전체 조합)
    context: EvaluationContext = _build_context(small_server, small_preset, base_stats)
    total_points: int = 5
    best_delta: float | None = None
    for strength in range(total_points + 1):
        for dexterity in range(total_points - strength + 1):
            for vitality in range(total_points - strength - dexterity + 1):
                luck: int = total_points - strength - dexterity - vitality
                delta: float = _brute_force_delta(
                    context,
                    base_stats,
                    calculator_input,
                    DistributionState(
                        strength=strength,
                        dexterity=dexterity,
                        vitality=vitality,
                        luck=luck,
                    ),
                    calculator_input.danjeon,
                )
                if best_delta is None or delta > best_delta:
                    best_delta = delta

    assert best_delta is not None
    assert result.delta == pytest.approx(best_delta, rel=1e-9)

    # 반환 후보의 delta 자체 일관성 확인
    reported_delta: float = _brute_force_delta(
        context,
        base_stats,
        calculator_input,
        result.candidate.distribution,
        result.candidate.danjeon,
    )
    assert reported_delta == pytest.approx(result.delta, rel=1e-9)


def _assert_final_stats_match(
    final_stats: FinalStats,
    expected_final_stats: dict[StatKey, float],
) -> None:
    """최종 스탯 전 항목의 손계산 리터럴 일치 확인"""

    assert set(final_stats.values.keys()) == set(expected_final_stats.keys())
    for stat_key, expected_value in expected_final_stats.items():
        assert final_stats.values[stat_key] == pytest.approx(
            expected_value, abs=0.011
        ), f"{stat_key.value} 최종 스탯이 손계산 값과 다릅니다."


def test_user_stats_boss_damage_check_optimization_matches_expected_result(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    serial_search: None,
) -> None:
    """실제 전체 스탯 입력의 보스 데미지 기댓값 최적화 결과 검증"""

    displayed_stats: BaseStats = BaseStats.from_stat_map(
        {
            StatKey.ATTACK: 1891.19,
            StatKey.ATTACK_PERCENT: 162.86,
            StatKey.HP: 3220.29,
            StatKey.HP_PERCENT: 59.31,
            StatKey.STR: 225.48,
            StatKey.STR_PERCENT: 61.83,
            StatKey.DEXTERITY: 228.19,
            StatKey.DEXTERITY_PERCENT: 73.67,
            StatKey.VITALITY: 119.68,
            StatKey.VITALITY_PERCENT: 49.6,
            StatKey.LUCK: 1412.22,
            StatKey.LUCK_PERCENT: 49.6,
            StatKey.SKILL_DAMAGE_PERCENT: 34.9,
            StatKey.FINAL_ATTACK_PERCENT: 12.4,
            StatKey.CRIT_RATE_PERCENT: 14.96,
            StatKey.CRIT_DAMAGE_PERCENT: 149.54,
            StatKey.EXP_PERCENT: 355.84,
            StatKey.BOSS_ATTACK_PERCENT: 41.68,
            StatKey.DROP_RATE_PERCENT: 334.36,
            StatKey.DODGE_PERCENT: 3.59,
            StatKey.POTION_HEAL_PERCENT: 89.84,
            StatKey.RESIST_PERCENT: 5.0,
            StatKey.SKILL_SPEED_PERCENT: 20.03,
        }
    )
    base_stats: BaseStats = build_internal_base_stats(displayed_stats)
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=162,
        distribution=DistributionState(luck=810, use_reset=True),
        danjeon=DanjeonState(is_locked=True),
        selected_formula_id=PowerMetric.BOSS_DAMAGE_CHECK.value,
        base_stats=base_stats,
    )
    small_preset.info.calculator = calculator_input
    context: EvaluationContext = build_calculator_context(
        server_spec=small_server,
        preset=small_preset,
        skills_info=small_preset.usage_settings,
        delay_ms=DELAY_MS,
        base_stats=base_stats,
        target_formula_id=PowerMetric.BOSS_DAMAGE_CHECK.value,
        custom_formulas=(),
    )

    result: OptimizationResult | OptimizationFailure = optimize_current_selection(
        server_spec=small_server,
        preset=small_preset,
        skills_info=small_preset.usage_settings,
        delay_ms=DELAY_MS,
        context=context,
        base_stats=base_stats,
        calculator_input=calculator_input,
        target_formula_id=PowerMetric.BOSS_DAMAGE_CHECK.value,
        cancel_checker=lambda: None,
    )

    assert isinstance(result, OptimizationResult)
    assert result.candidate.distribution == DistributionState(
        strength=398,
        dexterity=412,
        vitality=0,
        luck=0,
        use_reset=True,
    )
    _assert_final_stats_match(
        result.base_stats.resolve(),
        {
            StatKey.ATTACK: 6511.16,
            StatKey.ATTACK_PERCENT: 377.51,
            StatKey.HP: 3220.29,
            StatKey.HP_PERCENT: 59.31,
            StatKey.STR: 869.56,
            StatKey.STR_PERCENT: 61.83,
            StatKey.DEXTERITY: 943.71,
            StatKey.DEXTERITY_PERCENT: 73.67,
            StatKey.VITALITY: 119.68,
            StatKey.VITALITY_PERCENT: 49.6,
            StatKey.LUCK: 200.46,
            StatKey.LUCK_PERCENT: 49.6,
            StatKey.SKILL_DAMAGE_PERCENT: 34.9,
            StatKey.FINAL_ATTACK_PERCENT: 12.4,
            StatKey.CRIT_RATE_PERCENT: 50.74,
            StatKey.CRIT_DAMAGE_PERCENT: 213.95,
            StatKey.EXP_PERCENT: 113.49,
            StatKey.BOSS_ATTACK_PERCENT: 41.68,
            StatKey.DROP_RATE_PERCENT: 92.01,
            StatKey.DODGE_PERCENT: 3.59,
            StatKey.POTION_HEAL_PERCENT: 89.84,
            StatKey.RESIST_PERCENT: 5.0,
            StatKey.SKILL_SPEED_PERCENT: 20.03,
        },
    )


def test_boss_damage_optimization_matches_hand_computed_final_stats(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    serial_search: None,
) -> None:
    """힘/민첩이 실제 트레이드오프로 갈리는 보스 데미지 최적화의 손계산 검증

    레벨 4 (분배 20포인트) + 일류 (단전 5포인트) 초기화 탐색.
    베이스는 현실 스탯에서 공격력% 50 -> 800, 치명타 확률 30 -> 69.28로 바꾼 값.

    보스 데미지는 모든 타격에 공통 배율이 곱해지므로 포인트별 한계 이득은
    '공격력 x 기대 치명타 배율'의 상대 증가율로 손계산할 수 있다.
    기준 상태: 공격력 = (5000+1310) x (1+9.9) 계열, CF = 1 + min(치확,100)/100 x 2.1

    - 민첩 1포인트 (치확 100% 도달 전): 공격력% +0.36 (상대 +3.3e-4)
      + 치확 +0.06 (상대 +4.1e-4) = 합계 약 7.4e-4
    - 힘 1포인트: 공격력 +1.3 (상대 +2.1e-4) + 치공 +0.13 (상대 +4.2e-4)
      = 합계 약 6.3e-4
    - 민첩 1포인트 (상한 도달 후): 공격력% 기여만 남아 약 3.3e-4

    최종 치확 = 69.28 + 0.05 x 최종민첩 = 99.28 + 0.06/포인트이므로
    민첩 12포인트에서 정확히 100%에 도달한다. 따라서 우선순위는
    민첩(상한 전) > 힘 > 민첩(상한 후) -> 민첩 12, 힘 8.
    (20포인트 구간에서 최종 힘/공격력%의 2차 변동은 0.5% 미만이라 순서 불변)
    단전은 보스 데미지에 기여하는 중단전(공격력%)만 유효 -> 중단전 5.

    기대 최종 스탯 손계산:
        최종 힘 = 1008 x 1.3 = 1310.4, 최종 민첩 = 512 x 1.2 = 614.4
        공격력% = (800+5) + 614.4 x 0.3 = 989.32
        공격력 = (5000+1310.4) x 10.8932 = 68740.45
        치확 = 69.28 + 614.4 x 0.05 = 100.0, 치공 = 180 + 131.04 = 311.04
    """

    base_stats: BaseStats = make_realistic_base_stats().with_changes(
        {
            StatKey.ATTACK_PERCENT: 750.0,
            StatKey.CRIT_RATE_PERCENT: 39.28,
        }
    )
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=4,
        realm_tier=RealmTier.FIRST_RATE,
        distribution=DistributionState(use_reset=True),
        danjeon=DanjeonState(use_reset=True),
        base_stats=base_stats,
    )

    result: OptimizationResult | OptimizationFailure = _run_optimize(
        small_server, small_preset, base_stats, calculator_input
    )

    assert isinstance(result, OptimizationResult)

    # 손계산 최적 배분 확인 (치확 상한까지 민첩, 이후 힘 + 중단전 전량)
    assert result.candidate.distribution.strength == 8
    assert result.candidate.distribution.dexterity == 12
    assert result.candidate.distribution.vitality == 0
    assert result.candidate.distribution.luck == 0
    assert result.candidate.danjeon.upper == 0
    assert result.candidate.danjeon.middle == 5
    assert result.candidate.danjeon.lower == 0

    # 최적 배분 적용 후 최종 스탯 전 항목의 손계산 리터럴 비교
    _assert_final_stats_match(
        result.base_stats.resolve(),
        {
            StatKey.ATTACK: 68740.45,
            StatKey.ATTACK_PERCENT: 989.32,
            StatKey.HP: 17280.0,
            StatKey.HP_PERCENT: 20.0,
            StatKey.STR: 1310.4,
            StatKey.STR_PERCENT: 30.0,
            StatKey.DEXTERITY: 614.4,
            StatKey.DEXTERITY_PERCENT: 20.0,
            StatKey.VITALITY: 880.0,
            StatKey.VITALITY_PERCENT: 10.0,
            StatKey.LUCK: 315.0,
            StatKey.LUCK_PERCENT: 5.0,
            StatKey.SKILL_DAMAGE_PERCENT: 40.0,
            StatKey.FINAL_ATTACK_PERCENT: 25.0,
            StatKey.CRIT_RATE_PERCENT: 100.0,
            StatKey.CRIT_DAMAGE_PERCENT: 311.04,
            StatKey.BOSS_ATTACK_PERCENT: 40.0,
            StatKey.DROP_RATE_PERCENT: 73.0,
            StatKey.EXP_PERCENT: 73.0,
            StatKey.DODGE_PERCENT: 31.4,
            StatKey.POTION_HEAL_PERCENT: 455.0,
            StatKey.RESIST_PERCENT: 5.0,
            StatKey.SKILL_SPEED_PERCENT: 0.0,
        },
    )


def test_minimum_bound_optimization_matches_hand_computed_final_stats(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    serial_search: None,
) -> None:
    """전체 스탯/단전이 일부씩 찍힌 최소분배 최적화의 손계산 검증

    레벨 4 (분배 20포인트) + 일류 (단전 5포인트) 초기화 탐색에
    최소분배 힘3/민첩3/생명2/행운2, 상단전1/중단전1/하단전1을 걸어
    일곱 축 전부가 0이 아닌 배분을 받게 한다. 현실 스탯 기준
    자유 포인트의 한계 이득은 민첩(약 1.65e-3)이 힘(약 5.5e-4)의 3배이고
    생명/행운과 상/하단전은 보스 데미지에 기여하지 않으므로,
    자유 분배 10포인트는 민첩, 자유 단전 2포인트는 중단전으로 간다.
    -> 분배 (3, 13, 2, 2), 단전 (1, 3, 1)

    기대 최종 스탯 손계산:
        최종 힘 = 1003 x 1.3 = 1303.9, 최종 민첩 = 513 x 1.2 = 615.6
        최종 생명 = 802 x 1.1 = 882.2, 최종 행운 = 302 x 1.05 = 317.1
        공격력% = (50+3) + 615.6 x 0.3 = 237.68
        공격력 = (5000+1303.9) x 3.3768 = 21287.01
        체력% = 20+3 = 23, 체력 = (10000 + 882.2x5) x 1.23 = 17725.53
        치확 = 30 + 30.78 = 60.78, 치공 = 180 + 130.39 = 310.39
        드랍률 = (10+1.5) + 63.42 = 74.92, 경험치 = (10+0.5) + 63.42 = 73.92
        회피 = 5 + 26.466 = 31.466, 물약 회복 = 15 + 441.1 = 456.1
        저항 = 5+1 = 6
    """

    base_stats: BaseStats = make_realistic_base_stats()
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=4,
        realm_tier=RealmTier.FIRST_RATE,
        distribution=DistributionState(use_reset=True),
        danjeon=DanjeonState(use_reset=True),
        base_stats=base_stats,
    )
    calculator_input.target_distribution = TargetDistributionState(
        strength=3,
        dexterity=3,
        vitality=2,
        luck=2,
        is_minimum=True,
    )
    calculator_input.target_danjeon = TargetDanjeonState(
        upper=1,
        middle=1,
        lower=1,
        is_minimum=True,
    )

    result: OptimizationResult | OptimizationFailure = _run_optimize(
        small_server, small_preset, base_stats, calculator_input
    )

    assert isinstance(result, OptimizationResult)

    # 손계산 최적 배분 확인 (최소분배 하한 + 자유 포인트는 민첩/중단전)
    assert result.candidate.distribution.strength == 3
    assert result.candidate.distribution.dexterity == 13
    assert result.candidate.distribution.vitality == 2
    assert result.candidate.distribution.luck == 2
    assert result.candidate.danjeon.upper == 1
    assert result.candidate.danjeon.middle == 3
    assert result.candidate.danjeon.lower == 1

    # 최적 배분 적용 후 최종 스탯 전 항목의 손계산 리터럴 비교
    _assert_final_stats_match(
        result.base_stats.resolve(),
        {
            StatKey.ATTACK: 21287.01,
            StatKey.ATTACK_PERCENT: 237.68,
            StatKey.HP: 17725.53,
            StatKey.HP_PERCENT: 23.0,
            StatKey.STR: 1303.9,
            StatKey.STR_PERCENT: 30.0,
            StatKey.DEXTERITY: 615.6,
            StatKey.DEXTERITY_PERCENT: 20.0,
            StatKey.VITALITY: 882.2,
            StatKey.VITALITY_PERCENT: 10.0,
            StatKey.LUCK: 317.1,
            StatKey.LUCK_PERCENT: 5.0,
            StatKey.SKILL_DAMAGE_PERCENT: 40.0,
            StatKey.FINAL_ATTACK_PERCENT: 25.0,
            StatKey.CRIT_RATE_PERCENT: 60.78,
            StatKey.CRIT_DAMAGE_PERCENT: 310.39,
            StatKey.BOSS_ATTACK_PERCENT: 40.0,
            StatKey.DROP_RATE_PERCENT: 74.92,
            StatKey.EXP_PERCENT: 73.92,
            StatKey.DODGE_PERCENT: 31.466,
            StatKey.POTION_HEAL_PERCENT: 456.1,
            StatKey.RESIST_PERCENT: 6.0,
            StatKey.SKILL_SPEED_PERCENT: 0.0,
        },
    )


@pytest.mark.parametrize(
    "calculator_input_kwargs, expected_reason",
    [
        # 레벨 1 대비 분배 포인트 초과
        (
            {
                "level": 1,
                "distribution": DistributionState(strength=10, is_locked=True),
            },
            OptimizationFailureReason.STAT_DISTRIBUTION_EXCEEDS_LEVEL_CAP,
        ),
        # 삼류 경지 대비 단전 포인트 초과
        (
            {
                "level": 100,
                "realm_tier": RealmTier.THIRD_RATE,
                "danjeon": DanjeonState(upper=2, is_locked=True),
            },
            OptimizationFailureReason.DANJEON_EXCEEDS_REALM_CAP,
        ),
    ],
)
def test_invalid_selection_input_returns_failure(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    serial_search: None,
    calculator_input_kwargs: dict,
    expected_reason: OptimizationFailureReason,
) -> None:
    """분배/단전 한도 초과 입력의 최적화 실패 사유 검증"""

    base_stats: BaseStats = make_realistic_base_stats()
    calculator_input: CalculatorPresetInput = make_calculator_input(
        base_stats=base_stats,
        **calculator_input_kwargs,
    )

    result: OptimizationResult | OptimizationFailure = _run_optimize(
        small_server, small_preset, base_stats, calculator_input
    )

    assert isinstance(result, OptimizationFailure)
    assert result.reason == expected_reason


def test_selection_exceeding_total_stats_returns_failure(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    serial_search: None,
) -> None:
    """전체 스탯보다 큰 현재 선택 입력의 최적화 실패 검증"""

    # 힘 0 상태에서 분배 힘 100 제거 시도 구성
    base_stats: BaseStats = make_realistic_base_stats().with_changes(
        {StatKey.STR: -1000.0}
    )
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=100,
        distribution=DistributionState(strength=100, is_locked=True),
        base_stats=base_stats,
    )

    result: OptimizationResult | OptimizationFailure = _run_optimize(
        small_server, small_preset, base_stats, calculator_input
    )

    assert isinstance(result, OptimizationFailure)
    assert result.reason == OptimizationFailureReason.SELECTED_INPUT_EXCEEDS_TOTAL_STATS


def test_infeasible_minimum_distribution_returns_failure(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    serial_search: None,
) -> None:
    """레벨 한도를 초과하는 최소분배 조건의 최적화 실패 검증"""

    base_stats: BaseStats = make_realistic_base_stats()
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=1,
        distribution=DistributionState(use_reset=True),
        base_stats=base_stats,
    )
    calculator_input.target_distribution = TargetDistributionState(
        strength=10, is_minimum=True
    )

    result: OptimizationResult | OptimizationFailure = _run_optimize(
        small_server, small_preset, base_stats, calculator_input
    )

    assert isinstance(result, OptimizationFailure)
    assert (
        result.reason == OptimizationFailureReason.MINIMUM_DISTRIBUTION_EXCEEDS_LEVEL_CAP
    )


def test_candidate_group_selection_matches_brute_force(
    small_server: ServerSpec,
    small_preset: MacroPreset,
) -> None:
    """후보 그룹 선택의 전수조사 일치 검증"""

    base_stats: BaseStats = make_realistic_base_stats()
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=100,
        base_stats=base_stats,
    )

    # 그룹별 1개 선택 후보 그룹 2개 구성 (2 x 2 = 4 조합)
    group_options: dict[str, dict[str, dict[StatKey, float]]] = {
        "그룹1": {
            "공격력 후보": {StatKey.ATTACK: 500.0},
            "치명타 후보": {StatKey.CRIT_DAMAGE_PERCENT: 10.0},
        },
        "그룹2": {
            "보스 후보": {StatKey.BOSS_ATTACK_PERCENT: 10.0},
            "스킬 후보": {StatKey.SKILL_DAMAGE_PERCENT: 5.0},
        },
    }
    calculator_input.candidate_groups = [
        OptimizationCandidateGroup(
            name=group_name,
            selection_count=1,
            candidates=[
                OptimizationCandidateOption(
                    name=option_name,
                    stats=[
                        OptimizationCandidateStat(stat_key=stat_key, value=value)
                        for stat_key, value in stats.items()
                    ],
                )
                for option_name, stats in options.items()
            ],
        )
        for group_name, options in group_options.items()
    ]

    context: EvaluationContext = _build_context(small_server, small_preset, base_stats)
    result: CandidateGroupSelectionResult | OptimizationFailure | None = (
        select_candidate_groups(
            server_spec=small_server,
            preset=small_preset,
            skills_info=small_preset.usage_settings,
            delay_ms=DELAY_MS,
            context=context,
            base_stats=base_stats,
            calculator_input=calculator_input,
            target_formula_id=PowerMetric.BOSS_DAMAGE.value,
            cancel_checker=lambda: None,
        )
    )

    assert isinstance(result, CandidateGroupSelectionResult)

    # 4개 조합 전수조사 기준 최적 조합 계산
    best_delta: float | None = None
    best_names: tuple[str, str] | None = None
    for first_name, first_stats in group_options["그룹1"].items():
        for second_name, second_stats in group_options["그룹2"].items():
            changes: dict[StatKey, float] = dict(first_stats)
            for stat_key, value in second_stats.items():
                changes[stat_key] = changes.get(stat_key, 0.0) + value

            candidate_base: BaseStats = base_stats.with_changes(changes)
            target_value: float = evaluate_single_metric(
                artifacts=context.timeline_artifacts,
                resolved_stats=candidate_base.resolve(),
                target_formula_id=PowerMetric.BOSS_DAMAGE.value,
                compiled_custom_formula=None,
            )
            delta: float = target_value - context.baseline_power
            if best_delta is None or delta > best_delta:
                best_delta = delta
                best_names = (first_name, second_name)

    assert best_delta is not None and best_names is not None
    assert result.delta == pytest.approx(best_delta, rel=1e-9)

    selected_names: tuple[str, ...] = tuple(
        selection.selected_candidate_names[0] for selection in result.group_selections
    )
    assert selected_names == best_names


def test_empty_candidate_groups_skip_selection(
    small_server: ServerSpec,
    small_preset: MacroPreset,
) -> None:
    """후보 그룹 부재 시 선택 계산 생략 검증"""

    base_stats: BaseStats = make_realistic_base_stats()
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=100, base_stats=base_stats
    )
    context: EvaluationContext = _build_context(small_server, small_preset, base_stats)

    result: CandidateGroupSelectionResult | OptimizationFailure | None = (
        select_candidate_groups(
            server_spec=small_server,
            preset=small_preset,
            skills_info=small_preset.usage_settings,
            delay_ms=DELAY_MS,
            context=context,
            base_stats=base_stats,
            calculator_input=calculator_input,
            target_formula_id=PowerMetric.BOSS_DAMAGE.value,
            cancel_checker=lambda: None,
        )
    )

    assert result is None


def test_parallel_optimization_matches_serial_result(
    small_server: ServerSpec,
    small_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """병렬 프로세스 탐색과 직렬 탐색의 결과 일치 검증"""

    # 레벨 4 (20포인트) + 이류 단전 (2포인트) 초기화 탐색 구성
    base_stats: BaseStats = make_realistic_base_stats()
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=4,
        realm_tier=RealmTier.SECOND_RATE,
        distribution=DistributionState(use_reset=True),
        danjeon=DanjeonState(use_reset=True),
        base_stats=base_stats,
    )

    import app.scripts.calculator_engine as calculator_engine

    # 단일 CPU 환경에서도 실제 프로세스 풀 분기로 진입하도록 워커 수 고정
    real_executor: type[ProcessPoolExecutor] = calculator_engine.ProcessPoolExecutor
    executor_created: bool = False

    def tracking_executor(max_workers: int | None = None) -> ProcessPoolExecutor:
        nonlocal executor_created
        executor_created = True
        return real_executor(max_workers=max_workers)

    monkeypatch.setattr(calculator_engine.os, "cpu_count", lambda: 2)
    monkeypatch.setattr(
        calculator_engine,
        "ProcessPoolExecutor",
        tracking_executor,
    )

    parallel_result: OptimizationResult | OptimizationFailure = _run_optimize(
        small_server, small_preset, base_stats, calculator_input
    )

    assert executor_created is True
    assert isinstance(parallel_result, OptimizationResult)

    # 전수조사 기준 최적 delta 계산 (분배 1771 x 단전 6 조합)
    context: EvaluationContext = _build_context(small_server, small_preset, base_stats)
    distribution_points: int = 20
    danjeon_points: int = 2
    best_delta: float | None = None
    for strength in range(distribution_points + 1):
        for dexterity in range(distribution_points - strength + 1):
            for vitality in range(distribution_points - strength - dexterity + 1):
                luck: int = distribution_points - strength - dexterity - vitality
                distribution: DistributionState = DistributionState(
                    strength=strength,
                    dexterity=dexterity,
                    vitality=vitality,
                    luck=luck,
                )
                for upper in range(danjeon_points + 1):
                    for middle in range(danjeon_points - upper + 1):
                        lower: int = danjeon_points - upper - middle
                        delta: float = _brute_force_delta(
                            context,
                            base_stats,
                            calculator_input,
                            distribution,
                            DanjeonState(upper=upper, middle=middle, lower=lower),
                        )
                        if best_delta is None or delta > best_delta:
                            best_delta = delta

    assert best_delta is not None
    assert parallel_result.delta == pytest.approx(best_delta, rel=1e-9)
