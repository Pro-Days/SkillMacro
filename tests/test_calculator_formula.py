from __future__ import annotations

import math

import pytest

from app.scripts.calculator_engine import (
    TIMELINE_DAMAGE_INPUT_ERROR_MESSAGE,
    CompiledPowerFormula,
    EvaluationContext,
    LevelUpEvaluation,
    PowerFormulaInputValidation,
    RealmAdvanceEvaluation,
    ScrollUpgradeEvaluation,
    build_calculator_context,
    compile_custom_formula,
    evaluate_arbitrary_stat_delta,
    evaluate_level_up_delta,
    evaluate_next_realm_delta,
    evaluate_scroll_upgrade_deltas,
    evaluate_single_stat_delta,
    validate_custom_formula,
    validate_power_formula_input_requirements,
)
from app.scripts.calculator_models import (
    REALM_TIER_SPECS,
    BaseStats,
    CustomPowerFormula,
    FinalStats,
    PowerMetric,
    RealmTier,
    StatKey,
)
from app.scripts.macro_models import MacroPreset
from app.scripts.registry.server_registry import ServerSpec
from tests.conftest import build_full_equipped_preset, make_realistic_base_stats

# 계산기 공통 딜레이 입력값
DELAY_MS: int = 300


def _build_context(
    server_spec: ServerSpec,
    preset: MacroPreset,
    base_stats: BaseStats,
    target_formula_id: str = PowerMetric.BOSS_DAMAGE.value,
    custom_formulas: tuple[CustomPowerFormula, ...] = (),
) -> EvaluationContext:
    """테스트용 EvaluationContext 구성"""

    return build_calculator_context(
        server_spec=server_spec,
        preset=preset,
        skills_info=preset.usage_settings,
        delay_ms=DELAY_MS,
        base_stats=base_stats,
        target_formula_id=target_formula_id,
        custom_formulas=custom_formulas,
    )


@pytest.mark.parametrize("power_metric", list(PowerMetric))
def test_all_builtin_metrics_evaluate_positive_finite(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
    power_metric: PowerMetric,
) -> None:
    """전체 내장 공식의 현실 스탯 기준 유한 양수 평가 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=power_metric.value,
    )

    assert math.isfinite(context.baseline_power)
    assert context.baseline_power > 0.0


def test_boss_damage_exceeds_normal_damage(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """보스 공격력% 보유 시 보스 데미지 우위 검증"""

    context_boss: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    context_normal: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=PowerMetric.NORMAL_DAMAGE.value,
    )

    assert context_boss.baseline_power > context_normal.baseline_power


def test_attack_increase_raises_power(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """공격력 증가의 전투력 단조 증가 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats
    )

    delta: float = evaluate_single_stat_delta(
        context=context,
        stat_key=StatKey.ATTACK,
        amount=100.0,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert delta > 0.0


def test_zero_stat_change_produces_zero_delta(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """변화량 0 입력의 전투력 차이 0 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats
    )

    delta: float = evaluate_arbitrary_stat_delta(
        context=context,
        stat_changes={StatKey.ATTACK: 0.0},
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert delta == pytest.approx(0.0, abs=1e-9)


def test_skill_speed_over_limit_is_rejected(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """스킬속도 상한(70%) 초과 입력의 명시적 거부 검증"""

    over_limit_stats: BaseStats = realistic_base_stats.with_changes(
        {StatKey.SKILL_SPEED_PERCENT: 71.0}
    )

    with pytest.raises(ValueError):
        _build_context(synthetic_server, full_preset, over_limit_stats)


def test_empty_placement_requires_damage_input(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """배치 스킬과 평타가 모두 없는 상태의 60초 피해량 공식 거부 검증"""

    # 하단 배치 전체 해제 및 평타 미사용 상태 구성
    full_preset.skills.placed_skills = [""] * len(full_preset.skills.placed_skills)
    full_preset.settings.use_default_attack = False

    with pytest.raises(ValueError):
        _build_context(synthetic_server, full_preset, realistic_base_stats)


def test_level_up_delta_is_positive_and_spends_five_points(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """레벨업 효율 계산의 양수 delta와 5포인트 전량 분배 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats
    )

    evaluation: LevelUpEvaluation = evaluate_level_up_delta(
        context=context,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert evaluation.delta > 0.0
    assert sum(evaluation.stat_distribution.values()) == 5


def test_next_realm_delta_uses_all_extra_danjeon_points(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """다음 경지 효율 계산의 추가 단전 포인트 전량 분배 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats
    )

    evaluation: RealmAdvanceEvaluation | None = evaluate_next_realm_delta(
        context=context,
        current_realm=RealmTier.SECOND_RATE,
        level=999,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert evaluation is not None
    assert evaluation.target_realm == RealmTier.FIRST_RATE

    # 경지 승급으로 늘어나는 단전 포인트 수와 분배 합 일치 확인
    extra_points: int = (
        REALM_TIER_SPECS[RealmTier.FIRST_RATE].danjeon_points
        - REALM_TIER_SPECS[RealmTier.SECOND_RATE].danjeon_points
    )
    assert sum(evaluation.danjeon_distribution) == extra_points


def test_last_realm_has_no_next_realm_delta(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """최고 경지의 다음 경지 효율 계산 생략 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats
    )

    evaluation: RealmAdvanceEvaluation | None = evaluate_next_realm_delta(
        context=context,
        current_realm=RealmTier.LIFE_AND_DEATH,
        level=999,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert evaluation is None


def test_scroll_upgrade_deltas_cover_equipped_scrolls(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """무공비급 +1레벨 효율 계산의 대상/방향/상태 보존 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats
    )
    original_scroll_levels: dict[str, int] = dict(full_preset.info.scroll_levels)

    evaluations: list[ScrollUpgradeEvaluation] = evaluate_scroll_upgrade_deltas(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=DELAY_MS,
        baseline_context=context,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    # 장착 무공비급 전체가 계산 대상인지 확인
    assert len(evaluations) == synthetic_server.scroll_slot_count
    assert {evaluation.scroll_id for evaluation in evaluations} == set(
        full_preset.skills.equipped_scrolls
    )

    # 레벨 1 기준 다음 레벨 2와 계수 증가에 따른 양수 delta 확인
    for evaluation in evaluations:
        assert evaluation.next_level == 2
        assert evaluation.delta > 0.0

    # 계산용 임시 레벨 변경의 원상 복구 확인
    assert full_preset.info.scroll_levels == original_scroll_levels


def test_scroll_upgrade_skips_max_level_scrolls(
    synthetic_server: ServerSpec,
    realistic_base_stats: BaseStats,
) -> None:
    """최대 레벨 무공비급의 레벨업 효율 계산 제외 검증"""

    # 전체 무공비급을 최대 레벨(15)로 구성
    max_level_preset: MacroPreset = build_full_equipped_preset(
        synthetic_server,
        scroll_levels=synthetic_server.max_skill_level,
    )

    context: EvaluationContext = _build_context(
        synthetic_server, max_level_preset, realistic_base_stats
    )

    evaluations: list[ScrollUpgradeEvaluation] = evaluate_scroll_upgrade_deltas(
        server_spec=synthetic_server,
        preset=max_level_preset,
        skills_info=max_level_preset.usage_settings,
        delay_ms=DELAY_MS,
        baseline_context=context,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert evaluations == []


def test_insufficient_level_blocks_next_realm_delta(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """요구 레벨 미달 시 다음 경지 효율 계산 생략 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats
    )

    # 다음 경지 요구 레벨보다 1 낮은 레벨 입력
    required_level: int = REALM_TIER_SPECS[RealmTier.FIRST_RATE].min_level
    evaluation: RealmAdvanceEvaluation | None = evaluate_next_realm_delta(
        context=context,
        current_realm=RealmTier.SECOND_RATE,
        level=required_level - 1,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )

    assert evaluation is None


def test_timeline_formula_requires_positive_damage_input(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """60초 피해량 공식의 양수 데미지 입력 요구와 안내 문구 검증"""

    full_preset.skills.placed_skills = [""] * len(full_preset.skills.placed_skills)
    full_preset.settings.use_default_attack = False
    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=PowerMetric.OFFICIAL.value,
    )

    validation: PowerFormulaInputValidation = validate_power_formula_input_requirements(
        compile_custom_formula("boss_damage"),
        context.timeline_artifacts,
        context.baseline_final_stats,
    )

    assert validation.is_valid is False
    assert validation.message == TIMELINE_DAMAGE_INPUT_ERROR_MESSAGE


def test_stat_only_formula_allows_empty_skill_placement(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """일반 스탯 공식의 스킬 미배치 상태 허용 검증"""

    full_preset.skills.placed_skills = [""] * len(full_preset.skills.placed_skills)
    full_preset.settings.use_default_attack = False
    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=PowerMetric.OFFICIAL.value,
    )

    validation: PowerFormulaInputValidation = validate_power_formula_input_requirements(
        compile_custom_formula("attack + hp"),
        context.timeline_artifacts,
        context.baseline_final_stats,
    )

    assert validation.is_valid is True
    assert validation.message == "정상"


def test_referenced_skill_slots_require_at_least_one_damaging_skill(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """참조 슬롯 중 현재 레벨 데미지 입력이 하나 이상 필요한 계약 검증"""

    full_preset.skills.placed_skills = [""] * len(full_preset.skills.placed_skills)
    full_preset.skills.placed_skills[1] = synthetic_server.skill_registry.get_all_skill_ids()[
        1
    ]
    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=PowerMetric.OFFICIAL.value,
    )
    compiled_formula: CompiledPowerFormula = compile_custom_formula(
        "skill_1_damage + skill_2_damage"
    )

    valid: PowerFormulaInputValidation = validate_power_formula_input_requirements(
        compiled_formula,
        context.timeline_artifacts,
        context.baseline_final_stats,
    )
    assert valid.is_valid is True

    full_preset.skills.placed_skills[1] = ""
    empty_context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=PowerMetric.OFFICIAL.value,
    )
    invalid: PowerFormulaInputValidation = validate_power_formula_input_requirements(
        compiled_formula,
        empty_context.timeline_artifacts,
        empty_context.baseline_final_stats,
    )

    assert invalid.is_valid is False
    assert invalid.message == (
        "스킬 데미지가 입력되지 않았습니다.\n스킬 데미지 입력 후 다시 시도해주세요."
    )


def test_formula_skill_speed_limit_accepts_boundary_and_rejects_excess(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """계산기 스킬속도 70% 경계 허용과 초과 거부 문구 검증"""

    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=PowerMetric.OFFICIAL.value,
    )
    compiled_formula: CompiledPowerFormula = compile_custom_formula("attack")
    at_limit: FinalStats = realistic_base_stats.with_changes(
        {StatKey.SKILL_SPEED_PERCENT: 70.0}
    ).resolve()
    over_limit: FinalStats = realistic_base_stats.with_changes(
        {StatKey.SKILL_SPEED_PERCENT: 70.01}
    ).resolve()

    accepted: PowerFormulaInputValidation = validate_power_formula_input_requirements(
        compiled_formula,
        context.timeline_artifacts,
        at_limit,
    )
    rejected: PowerFormulaInputValidation = validate_power_formula_input_requirements(
        compiled_formula,
        context.timeline_artifacts,
        over_limit,
    )

    assert accepted.is_valid is True
    assert rejected.is_valid is False
    assert rejected.message == "스킬속도는 70% 이하여야 합니다."


@pytest.mark.parametrize(
    "formula_source",
    [
        "attack * (1 + skill_damage_percent * 0.01)",
        "dmg = attack\ndmg *= 1 + boss_attack_percent * 0.01\nresult = dmg",
        "result = floor(max(attack, hp)) if crit_rate_percent >= 50 else round(attack, 2)",
        "boss_damage + normal_damage",
        "attack * skill_1_damage + skill_2_target_count",
    ],
)
def test_valid_custom_formula_passes_validation(formula_source: str) -> None:
    assert validate_custom_formula(formula_source) is None


@pytest.mark.parametrize(
    "formula_source",
    [
        "__import__('os').system('dir')",
        "attack.__class__",
        "open('macros.json')",
        "mystery_stat + 1",
        "attack // 2",
        "[attack, hp]",
        "attack[0]",
        "round(attack, attack)",
        "min()",
        "import os\nresult = attack",
        "",
    ],
)
def test_forbidden_custom_formula_is_rejected(formula_source: str) -> None:
    assert validate_custom_formula(formula_source) is not None
    with pytest.raises(ValueError):
        compile_custom_formula(formula_source)


def test_custom_formula_evaluates_consistently_with_builtin(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    builtin_context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    custom_formula: CustomPowerFormula = CustomPowerFormula(
        name="보스 데미지 2배",
        formula="boss_damage * 2",
    )
    custom_context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=custom_formula.id,
        custom_formulas=(custom_formula,),
    )

    assert custom_context.baseline_power == pytest.approx(
        builtin_context.baseline_power * 2.0
    )


def test_unknown_custom_formula_id_is_rejected(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    with pytest.raises(KeyError):
        _build_context(
            synthetic_server,
            full_preset,
            realistic_base_stats,
            target_formula_id="missing-formula-id",
        )
