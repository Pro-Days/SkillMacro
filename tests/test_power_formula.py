from __future__ import annotations

import math
from typing import Any

import pytest

from app.scripts.calculator_engine import (
    EvaluationContext,
    build_calculator_context,
    build_calculator_timeline,
    compile_custom_formula,
    evaluate_single_metric,
)
from app.scripts.calculator_models import (
    BaseStats,
    CustomPowerFormula,
    OVERALL_STAT_ORDER,
    PowerMetric,
    StatKey,
)
from app.scripts.macro_models import MacroPreset
from app.scripts.registry.server_registry import ServerSpec

from tests.conftest import (
    make_realistic_base_stats,
    build_synthetic_server,
    build_full_equipped_preset,
)


def _build_context(
    server_spec: ServerSpec,
    preset: MacroPreset,
    base_stats: BaseStats,
    target_formula_id: str = PowerMetric.BOSS_DAMAGE.value,
    custom_formulas: tuple[CustomPowerFormula, ...] = (),
) -> EvaluationContext:
    """테스트용 EvaluationContext 빌드"""

    return build_calculator_context(
        server_spec=server_spec,
        preset=preset,
        skills_info=preset.usage_settings,
        delay_ms=300,
        base_stats=base_stats,
        target_formula_id=target_formula_id,
        custom_formulas=custom_formulas,
    )


def test_boss_damage_and_normal_damage_are_positive(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """현실적인 스탯에서 보스/일반 데미지는 양수다"""

    context_boss: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    context_normal: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats,
        target_formula_id=PowerMetric.NORMAL_DAMAGE.value,
    )

    assert context_boss.baseline_power > 0
    assert context_normal.baseline_power > 0


def test_boss_damage_is_greater_than_normal_damage(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """동일 스탯에서 보스 데미지가 일반 데미지보다 크다 (보스 공격력% > 0)"""

    context_boss: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats,
        target_formula_id=PowerMetric.BOSS_DAMAGE.value,
    )
    context_normal: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats,
        target_formula_id=PowerMetric.NORMAL_DAMAGE.value,
    )

    assert context_boss.baseline_power > context_normal.baseline_power


def test_official_formula_is_deterministic(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """공식 전투력은 두 번 호출해도 같은 정수 값을 반환한다"""

    context1: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats,
        target_formula_id=PowerMetric.OFFICIAL.value,
    )
    context2: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats,
        target_formula_id=PowerMetric.OFFICIAL.value,
    )

    assert context1.baseline_power == context2.baseline_power


def test_higher_str_yields_higher_boss_damage(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """힘이 더 높으면 보스 데미지도 더 높다 (단조성)"""

    low_stats: BaseStats = realistic_base_stats
    high_values: dict[str, float] = low_stats.values.copy()
    high_values[StatKey.STR.value] = low_stats.values[StatKey.STR.value] + 500.0
    high_stats: BaseStats = BaseStats(values=high_values)

    low_context: EvaluationContext = _build_context(
        synthetic_server, full_preset, low_stats,
    )
    high_context: EvaluationContext = _build_context(
        synthetic_server, full_preset, high_stats,
    )

    assert high_context.baseline_power > low_context.baseline_power


def test_skill_slot_variables_reflect_placed_skills(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """슬롯 변수는 실제 배치된 스킬의 데미지/쿨타임/타겟 수와 일치한다"""

    context: EvaluationContext = _build_context(
        synthetic_server, full_preset, realistic_base_stats,
    )
    skill_vars: dict[str, float | int] = context.timeline_artifacts.skill_slot_variables

    # 1번 슬롯 = placed_skills[0] 의 1레벨 데미지
    first_skill_id: str = full_preset.skills.placed_skills[0]
    first_skill_def = synthetic_server.skill_registry.get(first_skill_id)
    expected_damage: float = float(first_skill_def.levels[1])
    expected_cooltime: float = float(first_skill_def.cooltime)
    expected_target_count: int = int(first_skill_def.target_count)

    assert skill_vars["skill_1_damage"] == expected_damage
    assert skill_vars["skill_1_cooltime"] == expected_cooltime
    assert skill_vars["skill_1_target_count"] == expected_target_count


def test_skill_slot_variables_empty_slots_are_zero(
    synthetic_server: ServerSpec,
    realistic_base_stats: BaseStats,
) -> None:
    """장착하지 않은 슬롯은 데미지/쿨타임/타겟 수 모두 0"""

    # 한 무공비급만 장착하고 나머지는 비운 부분 장착 프리셋 구성
    preset: MacroPreset = build_full_equipped_preset(synthetic_server)
    for i in range(2, len(preset.skills.placed_skills)):
        preset.skills.placed_skills[i] = ""

    for i in range(1, len(preset.skills.equipped_scrolls)):
        preset.skills.equipped_scrolls[i] = ""

    context: EvaluationContext = _build_context(
        synthetic_server, preset, realistic_base_stats,
    )
    skill_vars: dict[str, float | int] = context.timeline_artifacts.skill_slot_variables

    # 1, 2번 슬롯은 채워져 있고 3~14번은 비어 있어야 함
    assert skill_vars["skill_1_damage"] > 0
    assert skill_vars["skill_2_damage"] > 0
    for slot in range(3, 15):
        assert skill_vars[f"skill_{slot}_damage"] == 0.0
        assert skill_vars[f"skill_{slot}_cooltime"] == 0.0
        assert skill_vars[f"skill_{slot}_target_count"] == 0


def test_custom_formula_simple_constant(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """가장 단순한 커스텀 공식 `result = 42` 가 그대로 평가된다"""

    formula: CustomPowerFormula = CustomPowerFormula(
        id="custom_const",
        name="상수",
        formula="result = 42",
    )
    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=formula.id,
        custom_formulas=(formula,),
    )

    assert context.baseline_power == 42.0


def test_custom_formula_referencing_stats(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """커스텀 공식이 최종 스탯 변수를 참조해 정확히 계산된다"""

    # final_attack = 20790 (test_stat_resolve의 골든값)
    formula: CustomPowerFormula = CustomPowerFormula(
        id="custom_attack",
        name="공격력",
        formula="result = attack",
    )
    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=formula.id,
        custom_formulas=(formula,),
    )

    assert context.baseline_power == 20790.0


def test_custom_formula_with_skill_slot_variables(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """커스텀 공식이 skill_N_damage 변수를 참조하면 슬롯 값으로 평가된다"""

    formula: CustomPowerFormula = CustomPowerFormula(
        id="skill_sum",
        name="스킬 합",
        formula="result = skill_1_damage + skill_14_damage",
    )
    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=formula.id,
        custom_formulas=(formula,),
    )

    # 합성 서버 기준: skill_1은 placed[0] (scroll 0 line 0), skill_14는 placed[13] (scroll 6 line 1)
    skill_1_def = synthetic_server.skill_registry.get(
        full_preset.skills.placed_skills[0]
    )
    skill_14_def = synthetic_server.skill_registry.get(
        full_preset.skills.placed_skills[13]
    )
    expected: float = (
        float(skill_1_def.levels[1]) + float(skill_14_def.levels[1])
    )

    assert context.baseline_power == pytest.approx(expected)


def test_custom_formula_with_branches(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """if/elif/else 분기와 누적 대입이 정상 평가된다"""

    formula: CustomPowerFormula = CustomPowerFormula(
        id="branch",
        name="분기",
        formula=(
            "power = 100\n"
            "if level < 50:\n"
            "    power = power * 1\n"
            "elif level < 100:\n"
            "    power = power * 2\n"
            "else:\n"
            "    power = power * 3\n"
            "result = power"
        ),
    )

    # level=100 → else 분기 → 300
    full_preset.info.calculator.level = 100
    context: EvaluationContext = _build_context(
        synthetic_server,
        full_preset,
        realistic_base_stats,
        target_formula_id=formula.id,
        custom_formulas=(formula,),
    )

    assert context.baseline_power == 300.0


def test_unknown_custom_formula_id_raises(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    """등록되지 않은 커스텀 공식 ID로 평가 요청하면 KeyError"""

    # custom_formulas로 등록되지 않은 ID를 전달
    with pytest.raises(KeyError):
        _build_context(
            synthetic_server,
            full_preset,
            realistic_base_stats,
            target_formula_id="non_existent_formula",
            custom_formulas=(),
        )


def test_higher_skill_damage_yields_higher_boss_damage(
    realistic_base_stats: BaseStats,
) -> None:
    """스킬 데미지 계수가 큰 서버가 보스 데미지도 더 크다"""

    weak_server: ServerSpec = build_synthetic_server(base_damage=1.0)
    strong_server: ServerSpec = build_synthetic_server(base_damage=5.0)
    weak_preset: MacroPreset = build_full_equipped_preset(weak_server)
    strong_preset: MacroPreset = build_full_equipped_preset(strong_server)

    weak_context: EvaluationContext = _build_context(
        weak_server, weak_preset, realistic_base_stats,
    )
    strong_context: EvaluationContext = _build_context(
        strong_server, strong_preset, realistic_base_stats,
    )

    assert strong_context.baseline_power > weak_context.baseline_power
