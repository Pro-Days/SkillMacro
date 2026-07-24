from __future__ import annotations

from collections.abc import Iterator

import pytest
from pynput.keyboard import KeyCode

import app.scripts.run_macro as run_macro
from app.scripts.app_state import app_state
from app.scripts.calculator_engine import SkillUseEvent, build_skill_use_sequence
from app.scripts.macro_models import (
    EquippedSkillRef,
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    MacroPreset,
    SkillUsageSetting,
)
from app.scripts.macro_scheduler import build_priority_skill_sequence
from app.scripts.registry.key_registry import KeyRegistry, KeySpec
from app.scripts.registry.server_registry import ServerSpec, server_registry
from app.scripts.run_macro import (
    _restore_or_reset_cooltime_state,
    _settle_cooltime_state_after_stop,
    build_preview_task_list,
    build_task_list,
    init_macro,
)


@pytest.fixture
def macro_state_with_preset(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> Iterator[MacroPreset]:
    """합성 서버 등록과 전역 매크로 상태 구성"""

    # current_server 조회가 가능하도록 합성 서버를 레지스트리에 임시 등록
    server_registry._SERVERS[synthetic_server.id] = synthetic_server

    # 현재 프리셋으로 풀 장착 프리셋 반영
    app_state.macro.presets = [full_preset]
    app_state.macro.current_preset_index = 0

    yield full_preset

    # 합성 서버 등록 해제
    server_registry._SERVERS.pop(synthetic_server.id, None)


def test_preview_contains_all_placed_skills(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
) -> None:
    """프리뷰의 전체 배치 스킬 1회씩 포함 검증"""

    preview: tuple[EquippedSkillRef, ...] = build_preview_task_list()

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )

    assert sorted(preview, key=lambda ref: ref.flat_index) == sorted(
        placed_refs, key=lambda ref: ref.flat_index
    )
    assert len(preview) == len(placed_refs)


def test_preview_orders_priority_skill_first(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
) -> None:
    """우선순위 1 지정 스킬의 프리뷰 최우선 배치 검증"""

    # 배치 순서상 뒤쪽 스킬에 우선순위 1 지정
    target_skill_id: str = macro_state_with_preset.skills.placed_skills[6]
    macro_state_with_preset.usage_settings[target_skill_id] = SkillUsageSetting(
        priority=1
    )

    preview: tuple[EquippedSkillRef, ...] = build_preview_task_list()

    first_skill_id: str = macro_state_with_preset.skills.get_placed_skill_id(preview[0])
    assert first_skill_id == target_skill_id


def test_preview_places_auto_link_group_first(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
) -> None:
    """자동 연계 묶음의 프리뷰 선두 연속 배치 검증"""

    first_link_skill_id: str = macro_state_with_preset.skills.placed_skills[2]
    second_link_skill_id: str = macro_state_with_preset.skills.placed_skills[8]
    macro_state_with_preset.link_skills.append(
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.OFF,
            key=None,
            skills=[first_link_skill_id, second_link_skill_id],
        )
    )

    preview: tuple[EquippedSkillRef, ...] = build_preview_task_list()

    preview_skill_ids: list[str] = [
        macro_state_with_preset.skills.get_placed_skill_id(skill_ref)
        for skill_ref in preview
    ]
    assert preview_skill_ids[0] == first_link_skill_id
    assert preview_skill_ids[1] == second_link_skill_id


def test_build_task_list_selects_priority_skill(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
) -> None:
    """실행용 작업 목록의 우선순위 스킬 선택 검증"""

    # 우선순위 1 스킬 지정 및 매크로 런타임 상태 수동 구성
    target_skill_id: str = macro_state_with_preset.skills.placed_skills[6]
    macro_state_with_preset.usage_settings[target_skill_id] = SkillUsageSetting(
        priority=1
    )

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    app_state.macro.skill_sequence = list(
        build_priority_skill_sequence(
            server_spec=synthetic_server,
            preset=macro_state_with_preset,
            skills_info=macro_state_with_preset.usage_settings,
        )
    )
    app_state.macro.prepared_skills = set(placed_refs)
    app_state.macro.using_link_skills = []
    app_state.macro.task_list = []

    wait_seconds: float = build_task_list()

    # 준비 스킬 존재 시 대기 없이 우선순위 스킬 1개 선택 확인
    assert wait_seconds == 0.0
    assert len(app_state.macro.task_list) == 1

    selected_skill_id: str = macro_state_with_preset.skills.get_placed_skill_id(
        app_state.macro.task_list[0]
    )
    assert selected_skill_id == target_skill_id


def test_build_task_list_runs_prepared_auto_link_first(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
) -> None:
    """실행용 작업 목록의 준비된 자동 연계 우선 실행 검증"""

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    link_refs: list[EquippedSkillRef] = [placed_refs[3], placed_refs[7]]

    # 연계 요구/실행 목록을 런타임 상태에 직접 구성
    app_state.macro.skill_sequence = list(
        build_priority_skill_sequence(
            server_spec=synthetic_server,
            preset=macro_state_with_preset,
            skills_info=macro_state_with_preset.usage_settings,
        )
    )
    app_state.macro.prepared_skills = set(placed_refs)
    app_state.macro.using_link_skills = [list(link_refs)]
    app_state.macro.task_list = []

    wait_seconds: float = build_task_list()

    assert wait_seconds == 0.0
    assert app_state.macro.task_list == link_refs


def test_build_task_list_returns_exact_cooldown_wait_without_fixed_margin(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """쿨타임 대기의 임의 고정 지연 없는 밀리초 기준 계산 검증"""

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    app_state.macro.skill_sequence = list(
        build_priority_skill_sequence(
            server_spec=synthetic_server,
            preset=macro_state_with_preset,
            skills_info=macro_state_with_preset.usage_settings,
        )
    )
    app_state.macro.prepared_skills = set()
    app_state.macro.using_link_skills = []
    app_state.macro.task_list = []
    app_state.macro.skill_cooltime_timers = {
        skill_ref: 100.0 for skill_ref in placed_refs
    }
    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: 101.0)

    wait_seconds: float = build_task_list()

    shortest_cooltime: float = min(
        synthetic_server.skill_registry.get(
            macro_state_with_preset.skills.get_placed_skill_id(skill_ref)
        ).cooltime
        for skill_ref in placed_refs
    )
    assert wait_seconds == shortest_cooltime - 1.0


def test_runtime_scheduler_matches_60_second_simulation_sequence(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """가상 시계에서 런타임과 시뮬레이터의 전체 상태 일치 검증"""

    first_link_skill_id: str = macro_state_with_preset.skills.placed_skills[1]
    second_link_skill_id: str = macro_state_with_preset.skills.placed_skills[6]
    macro_state_with_preset.link_skills.append(
        LinkSkill(
            use_type=LinkUseType.AUTO,
            skills=[first_link_skill_id, second_link_skill_id],
        )
    )
    delay_ms: int = 300
    expected_events: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=macro_state_with_preset,
        skills_info=macro_state_with_preset.usage_settings,
        delay_ms=delay_ms,
        cooltime_reduction=0.0,
    )

    started_at: float = 100.0
    current_time_seconds: float = 0.0
    monkeypatch.setattr(
        run_macro.time,
        "perf_counter",
        lambda: started_at + current_time_seconds,
    )
    init_macro()

    actual_events: list[SkillUseEvent] = []
    while current_time_seconds < 60.0:
        wait_seconds: float = 0.0
        if not app_state.macro.task_list:
            wait_seconds = build_task_list()

        if app_state.macro.task_list:
            skill_ref: EquippedSkillRef = app_state.macro.task_list.pop(0)
            skill_id: str = macro_state_with_preset.skills.get_placed_skill_id(
                skill_ref
            )
            app_state.macro.skill_cooltime_timers[skill_ref] = (
                run_macro.time.perf_counter()
            )
            actual_events.append(
                SkillUseEvent(
                    skill_id=skill_id,
                    time=round(current_time_seconds, 3),
                )
            )
            current_time_seconds += delay_ms * 0.001
            continue

        assert wait_seconds > 0.0
        current_time_seconds += wait_seconds

    assert tuple(actual_events) == expected_events


def test_cooltime_state_resets_when_remembering_is_disabled(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """이전 상태 기억 OFF 재시작의 전체 스킬 준비 상태 초기화 검증"""

    import app.scripts.run_macro as run_macro

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    macro_state_with_preset.settings.remember_previous_state = False
    app_state.macro.prepared_skills = {placed_refs[0]}

    # 전체 스킬의 타이머를 채워 '타이머 불완전' 폴백이 아닌 기억 OFF만이 초기화 사유가 되게 구성
    # (99.0 기준 경과 1초는 모든 쿨타임 미만이라 복원 경로라면 준비 스킬이 비어야 함)
    app_state.macro.skill_cooltime_timers = {
        skill_ref: 99.0 for skill_ref in placed_refs
    }
    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: 100.0)

    _restore_or_reset_cooltime_state(placed_refs)

    assert app_state.macro.prepared_skills == set(placed_refs)
    assert app_state.macro.skill_cooltime_timers == {
        skill_ref: 100.0 for skill_ref in placed_refs
    }


def test_cooltime_state_restores_elapsed_and_prepared_skills(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """이전 상태 기억 ON 재시작의 경과 쿨타임과 준비 상태 복원 검증"""

    import app.scripts.run_macro as run_macro

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    elapsed_ref: EquippedSkillRef = placed_refs[0]
    already_prepared_ref: EquippedSkillRef = placed_refs[1]
    waiting_ref: EquippedSkillRef = placed_refs[2]
    macro_state_with_preset.settings.remember_previous_state = True
    original_timers: dict[EquippedSkillRef, float] = {
        skill_ref: 99.0 for skill_ref in placed_refs
    }
    original_timers[elapsed_ref] = 90.0
    app_state.macro.skill_cooltime_timers = dict(original_timers)
    app_state.macro.prepared_skills = {already_prepared_ref}
    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: 100.0)

    _restore_or_reset_cooltime_state(placed_refs)

    assert elapsed_ref in app_state.macro.prepared_skills
    assert already_prepared_ref in app_state.macro.prepared_skills
    assert waiting_ref not in app_state.macro.prepared_skills
    assert app_state.macro.skill_cooltime_timers == original_timers


def test_incomplete_cooltime_state_forces_full_reset(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """배치 스킬 타이머 누락 상태의 안전한 전체 초기화 검증"""

    import app.scripts.run_macro as run_macro

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    macro_state_with_preset.settings.remember_previous_state = True
    app_state.macro.prepared_skills = set()
    app_state.macro.skill_cooltime_timers = {
        skill_ref: 1.0 for skill_ref in placed_refs[:-1]
    }
    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: 200.0)

    _restore_or_reset_cooltime_state(placed_refs)

    assert app_state.macro.prepared_skills == set(placed_refs)
    assert app_state.macro.skill_cooltime_timers == {
        skill_ref: 200.0 for skill_ref in placed_refs
    }


def test_settle_cooltime_state_returns_pending_tasks_to_prepared(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
) -> None:
    """매크로 중지 시 미실행 대기열의 준비 상태 복귀 검증"""

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    macro_state_with_preset.settings.remember_previous_state = True
    original_timers: dict[EquippedSkillRef, float] = {
        skill_ref: float(index) for index, skill_ref in enumerate(placed_refs)
    }
    app_state.macro.skill_cooltime_timers = dict(original_timers)
    app_state.macro.prepared_skills = {placed_refs[0]}
    app_state.macro.task_list = [placed_refs[1]]

    _settle_cooltime_state_after_stop()

    assert app_state.macro.task_list == []
    assert app_state.macro.prepared_skills == {placed_refs[0], placed_refs[1]}
    assert app_state.macro.skill_cooltime_timers == original_timers


def test_init_macro_uses_only_fully_placed_auto_links(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
) -> None:
    """매크로 시작 시 실제 배치가 완결된 자동 연계만 런타임 반영 검증"""

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    valid_skill_ids: list[str] = [
        macro_state_with_preset.skills.placed_skills[0],
        macro_state_with_preset.skills.placed_skills[4],
    ]
    macro_state_with_preset.link_skills = [
        LinkSkill(use_type=LinkUseType.AUTO, skills=valid_skill_ids),
        LinkSkill(
            use_type=LinkUseType.AUTO,
            skills=[valid_skill_ids[0], "custom:test_server:미배치스킬"],
        ),
    ]

    init_macro()

    skill_ref_map: dict[str, EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_ref_map(synthetic_server)
    )
    expected_link: list[EquippedSkillRef] = [
        skill_ref_map[skill_id] for skill_id in valid_skill_ids
    ]
    assert app_state.macro.using_link_skills == [expected_link]
    assert app_state.macro.prepared_skills == set(placed_refs)


def test_injected_input_is_ignored_but_user_input_updates_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_macro, "pressed_keys", set())
    monkeypatch.setattr(run_macro, "pressed_key_started_at", {})
    monkeypatch.setattr(run_macro, "handled_key_ids", set())
    monkeypatch.setattr(run_macro, "injected_press_counts", {})
    monkeypatch.setattr(run_macro, "injected_release_counts", {})
    monkeypatch.setattr(run_macro, "has_user_activity", False)
    key_spec: KeySpec = KeyRegistry.get("a")
    key_code: KeyCode = KeyCode.from_char("a")

    run_macro._register_injected_key_event(key_spec)
    run_macro.on_press(key_code)
    run_macro.on_release(key_code)

    assert run_macro.has_user_activity is False
    assert run_macro.pressed_keys == set()
    assert run_macro.injected_press_counts == {}
    assert run_macro.injected_release_counts == {}

    run_macro.on_press(key_code)
    assert run_macro.has_user_activity is True
    assert run_macro.pressed_keys == {key_spec}

    run_macro.on_release(key_code)
    assert run_macro.pressed_keys == set()
