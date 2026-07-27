from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.scripts.calculator_engine import (
    DamageEvent,
    EvaluationContext,
    GraphReport,
    HitEvent,
    SkillUseEvent,
    build_calculator_context,
    build_calculator_timeline,
    build_damage_events,
    build_skill_use_sequence,
)
from app.scripts.calculator_models import BaseStats, FinalStats, PowerMetric, StatKey
from app.scripts.macro_models import (
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    MacroPreset,
    SkillUsageSetting,
)
from app.scripts.registry.server_registry import ServerSpec
from app.scripts.simulate_macro import simulate_random_from_calculator

# 시퀀스 공통 딜레이 입력값
DELAY_MS: int = 300
GOLDEN_PATH: Path = (
    Path(__file__).resolve().parent / "data" / "golden" / "timeline_damage_cases.json"
)


def _build_sequence(
    server_spec: ServerSpec,
    preset: MacroPreset,
    cooltime_reduction: float = 0.0,
) -> tuple[SkillUseEvent, ...]:
    """테스트용 60초 스킬 사용 순서 구성"""

    return build_skill_use_sequence(
        server_spec=server_spec,
        preset=preset,
        skills_info=preset.usage_settings,
        delay_ms=DELAY_MS,
        cooltime_reduction=cooltime_reduction,
    )


def test_empty_placement_returns_empty_sequence(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """배치 스킬이 없는 상태의 빈 시퀀스 반환 검증"""

    full_preset.skills.placed_skills = [""] * len(full_preset.skills.placed_skills)

    assert _build_sequence(synthetic_server, full_preset) == ()


def test_sequence_is_deterministic(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """동일 입력의 시퀀스 결정론 검증"""

    first: tuple[SkillUseEvent, ...] = _build_sequence(synthetic_server, full_preset)
    second: tuple[SkillUseEvent, ...] = _build_sequence(synthetic_server, full_preset)

    assert first == second
    assert len(first) > 0


def test_cooldown_is_respected_per_skill(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """스킬별 재사용 간격의 쿨타임과 추가 대기 이상 유지 검증"""

    events: tuple[SkillUseEvent, ...] = _build_sequence(synthetic_server, full_preset)
    extra_wait_seconds: float = (
        full_preset.settings.effective_cooltime_extra_wait * 0.001
    )

    # 스킬별 사용 시각 목록 수집
    use_times: dict[str, list[float]] = {}
    for event in events:
        use_times.setdefault(event.skill_id, []).append(event.time)

    # 각 스킬의 연속 사용 간격 확인 (시각 반올림 오차 허용)
    for skill_id, times in use_times.items():
        cooltime: float = synthetic_server.skill_registry.get(skill_id).cooltime
        for previous_time, next_time in zip(times, times[1:]):
            assert (
                next_time - previous_time
                >= cooltime + extra_wait_seconds - 0.011
            )


def test_cooltime_reduction_increases_usage_count(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """쿨타임 감소 적용 시 60초 사용 횟수 증가 검증"""

    baseline_count: int = len(_build_sequence(synthetic_server, full_preset))
    reduced_count: int = len(
        _build_sequence(synthetic_server, full_preset, cooltime_reduction=50.0)
    )

    assert reduced_count > baseline_count


def test_priority_skill_is_used_first(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """우선순위 1 지정 스킬의 최우선 사용 검증"""

    # 배치 순서상 뒤쪽 스킬에 우선순위 1 지정
    target_skill_id: str = full_preset.skills.placed_skills[6]
    full_preset.usage_settings[target_skill_id] = SkillUsageSetting(priority=1)

    events: tuple[SkillUseEvent, ...] = _build_sequence(synthetic_server, full_preset)

    assert events[0].skill_id == target_skill_id


def test_disabled_skill_is_never_used(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """사용 여부 OFF 스킬의 시퀀스 제외 검증"""

    disabled_skill_id: str = full_preset.skills.placed_skills[0]
    full_preset.usage_settings[disabled_skill_id] = SkillUsageSetting(use_skill=False)

    events: tuple[SkillUseEvent, ...] = _build_sequence(synthetic_server, full_preset)

    assert events
    assert disabled_skill_id not in {event.skill_id for event in events}


def test_auto_link_skills_are_used_as_group(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """자동 연계스킬 묶음의 연속 실행 검증"""

    # 서로 다른 무공비급의 두 스킬로 자동 연계 구성
    first_link_skill_id: str = full_preset.skills.placed_skills[0]
    second_link_skill_id: str = full_preset.skills.placed_skills[4]
    full_preset.link_skills.append(
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.OFF,
            key=None,
            skills=[first_link_skill_id, second_link_skill_id],
        )
    )

    events: tuple[SkillUseEvent, ...] = _build_sequence(synthetic_server, full_preset)

    # 전체 준비 상태인 시작 시점의 연계 우선 실행 확인
    assert events[0].skill_id == first_link_skill_id
    assert events[1].skill_id == second_link_skill_id

    # 단독 사용 OFF 연계 스킬의 모든 사용이 묶음 순서를 유지하는지 확인
    for index, event in enumerate(events):
        if event.skill_id != first_link_skill_id:
            continue

        assert events[index + 1].skill_id == second_link_skill_id


def test_use_alone_allows_link_member_solo_use(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    """단독 사용 ON 연계 스킬의 개별 사용 허용 검증"""

    # 쿨타임이 크게 다른 두 스킬로 연계 구성 (첫 스킬 4.0초, 둘째 스킬 7.0초)
    fast_skill_id: str = full_preset.skills.placed_skills[0]
    slow_skill_id: str = full_preset.skills.placed_skills[13]
    full_preset.link_skills.append(
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.OFF,
            key=None,
            skills=[fast_skill_id, slow_skill_id],
        )
    )
    full_preset.usage_settings[fast_skill_id] = SkillUsageSetting(use_alone=True)

    events: tuple[SkillUseEvent, ...] = _build_sequence(synthetic_server, full_preset)

    # 단독 사용 허용 스킬의 사용 횟수가 연계 상대보다 많은지 확인
    fast_count: int = sum(1 for event in events if event.skill_id == fast_skill_id)
    slow_count: int = sum(1 for event in events if event.skill_id == slow_skill_id)

    assert fast_count > slow_count


@pytest.fixture
def timeline(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> tuple[HitEvent, ...]:
    return build_calculator_timeline(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=DELAY_MS,
        cooltime_reduction=0.0,
    )


def test_deterministic_damage_is_positive_and_reproducible(
    timeline: tuple[HitEvent, ...],
    realistic_base_stats: BaseStats,
) -> None:
    resolved: FinalStats = realistic_base_stats.resolve()
    first: list[DamageEvent] = build_damage_events(
        hit_events=timeline,
        resolved_stats=resolved,
        is_boss=True,
        deterministic=True,
    )
    second: list[DamageEvent] = build_damage_events(
        hit_events=timeline,
        resolved_stats=resolved,
        is_boss=True,
        deterministic=True,
    )

    assert len(first) == len(timeline)
    assert all(event.damage > 0.0 for event in first)
    assert first == second


def test_seed_controls_random_damage(
    timeline: tuple[HitEvent, ...],
    realistic_base_stats: BaseStats,
) -> None:
    resolved: FinalStats = realistic_base_stats.resolve()

    def build_with_seed(seed: float) -> list[DamageEvent]:
        return build_damage_events(
            hit_events=timeline,
            resolved_stats=resolved,
            is_boss=True,
            deterministic=False,
            random_seed=seed,
        )

    first: list[DamageEvent] = build_with_seed(1234.0)
    assert build_with_seed(1234.0) == first
    assert build_with_seed(5678.0) != first


def test_boss_flag_increases_total_damage(
    timeline: tuple[HitEvent, ...],
    realistic_base_stats: BaseStats,
) -> None:
    resolved: FinalStats = realistic_base_stats.resolve()

    def total_damage(is_boss: bool) -> float:
        return sum(
            event.damage
            for event in build_damage_events(
                hit_events=timeline,
                resolved_stats=resolved,
                is_boss=is_boss,
                deterministic=True,
            )
        )

    assert total_damage(is_boss=True) > total_damage(is_boss=False)


@pytest.mark.parametrize(
    ("crit_rate_change", "is_over_cap"),
    [
        # 상한 이내 기대 치명타 (최종 60%)
        (0.0, False),
        # 상한 초과 입력의 100% 상한 적용 (최종 130%)
        (70.0, True),
    ],
)
def test_single_hit_damage_matches_hand_formula(
    realistic_base_stats: BaseStats,
    crit_rate_change: float,
    is_over_cap: bool,
) -> None:
    """단일 타격 데미지의 손계산 일치와 치명타 확률 100% 상한 검증"""

    resolved: FinalStats = realistic_base_stats.with_changes(
        {StatKey.CRIT_RATE_PERCENT: crit_rate_change}
    ).resolve()

    # 케이스가 의도한 상한 초과 여부 전제 확인
    assert (resolved.values[StatKey.CRIT_RATE_PERCENT] > 100.0) is is_over_cap

    multiplier: float = 2.0
    events: list[DamageEvent] = build_damage_events(
        hit_events=(HitEvent(skill_id="test", time=0.0, multiplier=multiplier),),
        resolved_stats=resolved,
        is_boss=True,
        deterministic=True,
    )

    values: dict[StatKey, float] = resolved.values
    expected: float = values[StatKey.ATTACK]
    expected *= 1.0 + values[StatKey.FINAL_ATTACK_PERCENT] * 0.01
    expected *= 1.0 + values[StatKey.BOSS_ATTACK_PERCENT] * 0.01
    expected *= multiplier
    expected *= 1.0 + (
        min(values[StatKey.CRIT_RATE_PERCENT], 100.0)
        * 0.01
        * (values[StatKey.CRIT_DAMAGE_PERCENT] - 100.0)
        * 0.01
    )
    expected *= 1.0 + values[StatKey.SKILL_DAMAGE_PERCENT] * 0.01

    assert events[0].damage == pytest.approx(expected)


def test_timeline_damage_matches_snapshot(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
) -> None:
    with open(GOLDEN_PATH, "r", encoding="utf-8") as file:
        payload: dict[str, Any] = json.load(file)
    case: dict[str, Any] = payload["cases"][0]
    if case["expected"] is None:
        pytest.fail("타임라인 스냅샷 기대값이 비어 있습니다.")

    expected: dict[str, Any] = case["expected"]
    contexts: dict[PowerMetric, EvaluationContext] = {
        metric: build_calculator_context(
            server_spec=synthetic_server,
            preset=full_preset,
            skills_info=full_preset.usage_settings,
            delay_ms=int(case["delay_ms"]),
            base_stats=realistic_base_stats,
            target_formula_id=metric.value,
            custom_formulas=(),
        )
        for metric in (PowerMetric.BOSS_DAMAGE, PowerMetric.NORMAL_DAMAGE)
    }
    boss_context: EvaluationContext = contexts[PowerMetric.BOSS_DAMAGE]

    assert len(boss_context.timeline_artifacts.hit_events) == int(
        expected["hit_event_count"]
    )
    assert boss_context.baseline_power == pytest.approx(
        expected["boss_damage_power"], abs=0.011
    )
    assert contexts[PowerMetric.NORMAL_DAMAGE].baseline_power == pytest.approx(
        expected["normal_damage_power"], abs=0.011
    )
    boss_events: list[DamageEvent] = build_damage_events(
        hit_events=boss_context.timeline_artifacts.hit_events,
        resolved_stats=boss_context.baseline_final_stats,
        is_boss=True,
        deterministic=True,
    )
    assert sum(event.damage for event in boss_events) == pytest.approx(
        boss_context.baseline_power, rel=1e-9
    )


def test_graph_simulation_builds_complete_report(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    realistic_base_stats: BaseStats,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.scripts.simulate_macro.random.random", lambda: 0.5)

    report: GraphReport = simulate_random_from_calculator(
        server_spec=synthetic_server,
        preset=full_preset,
        skills_info=full_preset.usage_settings,
        delay_ms=DELAY_MS,
        base_stats=realistic_base_stats,
    )

    assert [entry.title for entry in report.analysis] == [
        "초당 보스피해량",
        "총 보스피해량",
        "초당 피해량",
        "총 피해량",
    ]
    assert len(report.deterministic_boss_attacks) > 0
    assert len(report.random_boss_attacks) == 1000
    assert all(report.random_boss_attacks)
