from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import cast

import pytest
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

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
from app.scripts.macro_scheduler import (
    build_priority_skill_sequence,
    can_use_basic_attack,
)
from app.scripts.registry.key_registry import KeyRegistry, KeySpec
from app.scripts.registry.server_registry import ServerSpec, server_registry
from app.scripts.run_macro import (
    _get_link_skill_readiness,
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


def test_runtime_yields_when_no_skills_can_be_scheduled(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """빈 스킬 구성의 메인 런타임 폴링 대기 검증"""

    macro_state_with_preset.skills.placed_skills = [
        ""
    ] * len(macro_state_with_preset.skills.placed_skills)
    macro_state_with_preset.settings.use_default_attack = False
    app_state.macro.is_running = True
    app_state.macro.run_id = 1

    wait_end_times: list[float] = []

    def stop_after_wait(end_at: float) -> None:
        wait_end_times.append(end_at)
        app_state.macro.is_running = False

    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: 100.0)
    monkeypatch.setattr(
        run_macro,
        "_wait_until_while_macro_running",
        stop_after_wait,
    )
    monkeypatch.setattr(run_macro.keyboard, "Controller", lambda: None)
    monkeypatch.setattr(run_macro.mouse, "Controller", lambda: None)

    run_macro.running_macro_thread(run_id=1)

    assert wait_end_times == [100.0 + run_macro.MACRO_SLEEP_POLL_SECONDS]


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


def test_build_task_list_includes_configured_cooldown_extra_wait(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """설정된 쿨타임 추가 대기를 포함한 잔여 시간 계산 검증"""

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    macro_state_with_preset.settings.custom_cooltime_extra_wait = 350
    macro_state_with_preset.settings.use_custom_cooltime_extra_wait = True
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
    assert wait_seconds == pytest.approx(shortest_cooltime - 1.0 + 0.35)


def test_each_skill_waits_its_own_cooldown_extra_wait(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """다른 스킬의 대기 구간 중 쿨타임이 끝난 스킬의 개별 추가 대기 보장"""

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    ready_ref: EquippedSkillRef = placed_refs[0]
    cooling_priority_ref: EquippedSkillRef = placed_refs[2]
    cooling_priority_id: str = (
        macro_state_with_preset.skills.get_placed_skill_id(cooling_priority_ref)
    )
    macro_state_with_preset.usage_settings[cooling_priority_id] = SkillUsageSetting(
        priority=1
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

    # 4.0초 스킬은 추가 대기까지 완료, 4.5초 우선순위 스킬은 쿨타임만 완료된 시점
    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: 104.55)

    wait_seconds: float = build_task_list()

    assert wait_seconds == 0.0
    assert app_state.macro.task_list == [ready_ref]


def test_manual_link_cooltime_state_includes_extra_wait(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """수동 연계 쿨타임 동기화의 추가 대기 적용 검증"""

    skill_id: str = macro_state_with_preset.skills.placed_skills[0]
    link_skill = LinkSkill(skills=[skill_id], remember_state=True)
    link_skill.skill_timers[skill_id] = 100.0
    current_time: list[float] = [104.199]
    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: current_time[0])

    assert _get_link_skill_readiness(link_skill, link_skill.skill_timers) == (
        [],
        0.001,
    )

    current_time[0] = 104.2
    assert _get_link_skill_readiness(link_skill, link_skill.skill_timers) == (
        [skill_id],
        0.0,
    )


class StopCheckingThread(Exception):
    """입력 감지 무한 루프의 작업 시작 직후 종료 신호"""


class FakeListener:
    """입력 리스너 시작 경계 대체"""

    def __init__(self, **_callbacks: Callable[..., None]) -> None:
        return

    def start(self) -> None:
        return


class FakeThread:
    """입력 작업 스레드 시작 경계 대체"""

    def start(self) -> None:
        return


CheckingThreadArgument = int | run_macro.ManualLinkSession
CheckingThreadStart = tuple[
    Callable[..., None],
    list[CheckingThreadArgument],
    bool,
]


def _run_checking_thread_until_first_sleep(
    monkeypatch: pytest.MonkeyPatch,
    sleep_seconds: list[float] | None = None,
) -> list[CheckingThreadStart]:
    """입력 감지 스레드의 첫 작업 시작 정보 기록"""

    started_threads: list[CheckingThreadStart] = []

    def record_thread(
        *,
        target: Callable[..., None],
        args: list[CheckingThreadArgument],
        daemon: bool,
    ) -> FakeThread:
        started_threads.append((target, args, daemon))
        return FakeThread()

    def stop_after_task_start(seconds: float) -> None:
        if sleep_seconds is not None:
            sleep_seconds.append(seconds)
        raise StopCheckingThread

    monkeypatch.setattr(run_macro.time, "sleep", stop_after_task_start)
    monkeypatch.setattr(run_macro.keyboard, "Listener", FakeListener)
    monkeypatch.setattr(run_macro.mouse, "Listener", FakeListener)
    monkeypatch.setattr(run_macro, "Thread", record_thread)

    with pytest.raises(StopCheckingThread):
        run_macro.checking_kb_thread()

    return started_threads


def _start_main_macro_from_checking_thread(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[KeySpec, list[float]]:
    """실제 입력 감지 경계에서 메인 매크로 시작 상태 구성"""

    macro_state_with_preset.settings.custom_delay = 300
    macro_state_with_preset.settings.use_custom_delay = True
    start_key: KeySpec = app_state.macro.current_start_key
    current_time: list[float] = [100.0]

    monkeypatch.setattr(
        run_macro.time,
        "perf_counter",
        lambda: current_time[0],
    )
    monkeypatch.setattr(run_macro, "pressed_keys", {start_key})
    monkeypatch.setattr(
        run_macro,
        "pressed_key_started_at",
        {start_key.key_id: 99.0},
    )
    monkeypatch.setattr(run_macro, "handled_key_ids", set())
    monkeypatch.setattr(run_macro, "injected_release_counts", {})
    monkeypatch.setattr(run_macro, "has_user_activity", False)
    monkeypatch.setattr(run_macro, "is_input_sequence_running", False)
    monkeypatch.setattr(run_macro, "active_manual_link_session", None)
    monkeypatch.setattr(
        run_macro,
        "active_macro_start_session",
        None,
        raising=False,
    )
    app_state.macro.is_running = False
    app_state.macro.run_id = 0

    sleep_seconds: list[float] = []
    started_threads = _run_checking_thread_until_first_sleep(
        monkeypatch,
        sleep_seconds,
    )

    assert started_threads == [
        (run_macro.running_macro_thread, [1], True),
    ]
    assert sleep_seconds == [0.05]
    assert app_state.macro.is_running is True
    assert app_state.macro.run_id == 1
    assert run_macro.is_input_sequence_running is True
    return start_key, current_time


def test_main_macro_short_release_preserves_existing_toggle_start(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """짧은 시작키 해제 후 기존 메인 매크로 실행 유지 검증"""

    start_key, current_time = _start_main_macro_from_checking_thread(
        macro_state_with_preset,
        monkeypatch,
    )
    current_time[0] = 100.1

    run_macro.on_release(cast(Key | KeyCode, start_key.value))

    assert app_state.macro.is_running is True


def test_main_macro_hold_release_stops_after_current_delay(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """현재 딜레이 이상 유지한 시작키 해제의 메인 매크로 중지 검증"""

    start_key, current_time = _start_main_macro_from_checking_thread(
        macro_state_with_preset,
        monkeypatch,
    )
    session: run_macro.MacroStartSession | None = (
        run_macro.active_macro_start_session
    )
    assert session is not None
    assert session.hold_transition_at == 100.3

    current_time[0] = 100.31
    run_macro.on_release(cast(Key | KeyCode, start_key.value))

    assert app_state.macro.is_running is False


@pytest.mark.parametrize("trigger_kind", ["main", "link"])
def test_checking_thread_preserves_press_time_when_release_races_with_activation(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
    trigger_kind: str,
) -> None:
    """유지 판정 직후 키 해제와 실행 활성화의 경합 검증"""

    macro_state_with_preset.settings.custom_delay = 300
    macro_state_with_preset.settings.use_custom_delay = True
    trigger_key: KeySpec = (
        app_state.macro.current_start_key
        if trigger_kind == "main"
        else KeyRegistry.get("q")
    )
    link_skill = LinkSkill(
        key_type=LinkKeyType.ON,
        key=trigger_key.key_id,
        skills=[macro_state_with_preset.skills.placed_skills[0]],
    )
    macro_state_with_preset.link_skills = (
        [link_skill] if trigger_kind == "link" else []
    )

    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: 100.0)
    monkeypatch.setattr(run_macro, "pressed_keys", {trigger_key})
    monkeypatch.setattr(
        run_macro,
        "pressed_key_started_at",
        {trigger_key.key_id: 99.0},
    )
    monkeypatch.setattr(run_macro, "handled_key_ids", set())
    monkeypatch.setattr(run_macro, "injected_release_counts", {})
    monkeypatch.setattr(run_macro, "has_user_activity", False)
    monkeypatch.setattr(run_macro, "is_input_sequence_running", False)
    monkeypatch.setattr(run_macro, "active_manual_link_session", None)
    monkeypatch.setattr(run_macro, "active_macro_start_session", None)
    app_state.macro.is_running = False
    app_state.macro.run_id = 0

    def release_after_hold_check(
        key_spec: KeySpec,
        _hold_seconds: float,
    ) -> bool:
        if key_spec != trigger_key:
            return False

        run_macro.on_release(cast(Key | KeyCode, trigger_key.value))
        return True

    monkeypatch.setattr(run_macro, "is_key_held", release_after_hold_check)

    started_threads = _run_checking_thread_until_first_sleep(monkeypatch)

    assert len(started_threads) == 1
    target, args, daemon = started_threads[0]
    assert daemon is True
    if trigger_kind == "main":
        assert target is run_macro.running_macro_thread
        assert args == [1]
        session = cast(
            run_macro.MacroStartSession,
            run_macro.active_macro_start_session,
        )
    else:
        assert target is run_macro.use_link_skill
        session = cast(run_macro.ManualLinkSession, args[0])

    assert session.trigger_pressed_at == 99.0


def test_unavailable_manual_link_requests_notice_without_skill_input(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """미배치 스킬 연계 단축키의 입력 차단과 알림 요청 검증"""

    trigger_key: KeySpec = KeyRegistry.get("q")
    unplaced_skill_id: str = macro_state_with_preset.skills.placed_skills[0]
    macro_state_with_preset.skills.placed_skills[0] = ""
    link_skill = LinkSkill(
        key_type=LinkKeyType.ON,
        key=trigger_key.key_id,
        skills=[unplaced_skill_id],
    )
    session = run_macro.ManualLinkSession(
        link_skill=link_skill,
        trigger_key=trigger_key,
        trigger_pressed_at=99.0,
        delay_seconds=0.3,
        hold_transition_at=99.3,
    )

    monkeypatch.setattr(run_macro.keyboard, "Controller", lambda: None)
    monkeypatch.setattr(run_macro.mouse, "Controller", lambda: None)
    monkeypatch.setattr(
        run_macro,
        "_run_manual_link_cycle",
        lambda *_args, **_kwargs: pytest.fail("실행 불가 연계가 입력을 시도함"),
    )
    monkeypatch.setattr(run_macro, "is_input_sequence_running", True)
    monkeypatch.setattr(run_macro, "active_manual_link_session", session)
    monkeypatch.setattr(
        app_state.macro,
        "has_pending_link_skill_unavailable_notice",
        False,
    )

    run_macro.use_link_skill(session)

    assert run_macro.active_manual_link_session is None
    assert run_macro.is_input_sequence_running is False
    assert app_state.macro.has_pending_link_skill_unavailable_notice is True


def _record_manual_link_run(
    monkeypatch: pytest.MonkeyPatch,
    link_skill: LinkSkill,
    event_hook: Callable[[list[float], float], None],
    initial_time: float,
    trigger_pressed_at: float,
    delay_seconds: float,
) -> tuple[list[tuple[float, str]], run_macro.ManualLinkSession]:
    """가상 시계와 실제 입력 콜백을 사용한 수동 연계 입력 기록"""

    current_time: list[float] = [initial_time]
    recorded_inputs: list[tuple[float, str]] = []
    trigger_key: KeySpec = KeyRegistry.get("q")
    session = run_macro.ManualLinkSession(
        link_skill=link_skill,
        trigger_key=trigger_key,
        trigger_pressed_at=trigger_pressed_at,
        delay_seconds=delay_seconds,
        hold_transition_at=initial_time + delay_seconds,
    )

    def advance_clock(seconds: float) -> None:
        target_time: float = round(current_time[0] + seconds, 6)
        event_hook(current_time, target_time)
        current_time[0] = target_time

    def record_input(
        _kbd_controller: None,
        _mouse_controller: None,
        key_spec: KeySpec,
    ) -> None:
        recorded_inputs.append((current_time[0], key_spec.key_id))

    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: current_time[0])
    monkeypatch.setattr(run_macro.time, "sleep", advance_clock)
    monkeypatch.setattr(run_macro.keyboard, "Controller", lambda: None)
    monkeypatch.setattr(run_macro.mouse, "Controller", lambda: None)
    monkeypatch.setattr(run_macro, "_press_key_spec", record_input)
    monkeypatch.setattr(run_macro, "pressed_keys", {trigger_key})
    monkeypatch.setattr(
        run_macro,
        "pressed_key_started_at",
        {trigger_key.key_id: trigger_pressed_at},
    )
    monkeypatch.setattr(run_macro, "handled_key_ids", {trigger_key.key_id})
    monkeypatch.setattr(run_macro, "is_input_sequence_running", True)
    monkeypatch.setattr(run_macro, "active_manual_link_session", session)

    run_macro.use_link_skill(session)
    return recorded_inputs, session


@pytest.mark.parametrize("remember_state", [False, True])
@pytest.mark.parametrize("hold_for_one_cycle", [False, True])
def test_manual_link_single_use_preserves_input_timeline_and_state(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
    remember_state: bool,
    hold_for_one_cycle: bool,
) -> None:
    """수동 연계 1회 실행의 입력 시각·줄 복귀·쿨타임 상태 계약 검증"""

    macro_state_with_preset.settings.custom_delay = 300
    macro_state_with_preset.settings.use_custom_delay = True
    skill_ids: list[str] = [
        macro_state_with_preset.skills.placed_skills[index] for index in (0, 2, 1)
    ]
    link_skill = LinkSkill(skills=skill_ids, remember_state=remember_state)
    trigger_pressed_at: float = 9.9
    released: list[bool] = [False]

    def release_trigger(current_time: list[float], target_time: float) -> None:
        release_at: float = 10.7 if hold_for_one_cycle else 10.15
        if not released[0] and current_time[0] < release_at <= target_time:
            current_time[0] = release_at
            run_macro.on_release(KeyCode.from_char("q"))
            released[0] = True

    recorded_inputs, session = _record_manual_link_run(
        monkeypatch=monkeypatch,
        link_skill=link_skill,
        event_hook=release_trigger,
        initial_time=10.0,
        trigger_pressed_at=trigger_pressed_at,
        delay_seconds=0.3,
    )

    assert recorded_inputs == [
        (10.0, "2"),
        (10.3, "3"),
        (10.6, "h"),
        (10.6, "2"),
        (10.9, "h"),
    ]
    assert app_state.macro.last_skill_input_at == 10.6
    assert app_state.macro.next_skill_input_at is None
    assert run_macro.is_input_sequence_running is False
    assert session.is_hold is hold_for_one_cycle
    assert link_skill.skill_timers == (
        {
            skill_ids[0]: 10.0,
            skill_ids[1]: 10.3,
            skill_ids[2]: 10.6,
        }
        if remember_state
        else {}
    )


@pytest.mark.parametrize(
    ("stop_kind", "expected_skill_count", "expected_hold"),
    [
        ("repress", 2, False),
        ("hold_release", 2, True),
    ],
)
def test_manual_link_stops_before_next_skill_from_real_input_callbacks(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
    stop_kind: str,
    expected_skill_count: int,
    expected_hold: bool,
) -> None:
    """재입력과 홀드 해제의 다음 연계 스킬 차단 검증"""

    macro_state_with_preset.settings.custom_delay = 300
    macro_state_with_preset.settings.use_custom_delay = True
    macro_state_with_preset.settings.custom_key_hold_seconds = 0.2
    macro_state_with_preset.settings.use_custom_key_hold_seconds = True
    skill_ids: list[str] = [
        macro_state_with_preset.skills.placed_skills[index] for index in (0, 2, 4)
    ]
    link_skill = LinkSkill(skills=skill_ids)
    trigger_pressed_at: float = -0.1
    stop_input_sent: list[bool] = [False]

    def send_stop_input(current_time: list[float], target_time: float) -> None:
        if stop_kind == "repress" and not stop_input_sent[0]:
            current_time[0] = 0.15
            run_macro.on_release(KeyCode.from_char("q"))
            current_time[0] = 0.16
            run_macro.on_press(KeyCode.from_char("q"))
            stop_input_sent[0] = True

        if (
            stop_kind == "repress"
            and stop_input_sent[0]
            and current_time[0] < 0.361 <= target_time
        ):
            current_time[0] = 0.361
            run_macro._apply_pending_manual_link_stop(
                app_state.macro.current_key_hold_seconds,
            )

        if (
            stop_kind == "hold_release"
            and not stop_input_sent[0]
            and current_time[0] < 0.45 <= target_time
        ):
            current_time[0] = 0.45
            run_macro.on_release(KeyCode.from_char("q"))
            stop_input_sent[0] = True

    recorded_inputs, session = _record_manual_link_run(
        monkeypatch=monkeypatch,
        link_skill=link_skill,
        event_hook=send_stop_input,
        initial_time=0.0,
        trigger_pressed_at=trigger_pressed_at,
        delay_seconds=0.3,
    )
    input_times: list[float] = [
        input_time for input_time, key_id in recorded_inputs if key_id != "h"
    ]

    assert input_times == [index * 0.3 for index in range(expected_skill_count)]
    assert session.stop_event.is_set()
    assert session.is_hold is expected_hold
    assert app_state.macro.next_skill_input_at is None
    assert run_macro.is_input_sequence_running is False


@pytest.mark.parametrize("trigger_kind", ["main", "link"])
@pytest.mark.parametrize("session_ends_early", [False, True])
def test_repress_stop_intent_is_not_retargeted_after_hold_delay(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
    trigger_kind: str,
    session_ends_early: bool,
) -> None:
    """재입력 중지의 유지 시간 적용과 대상 실행 고정 검증"""

    macro_state_with_preset.settings.custom_key_hold_seconds = 0.5
    macro_state_with_preset.settings.use_custom_key_hold_seconds = True
    trigger_key: KeySpec = (
        app_state.macro.current_start_key
        if trigger_kind == "main"
        else KeyRegistry.get("q")
    )
    link_skill = LinkSkill(
        key_type=LinkKeyType.ON,
        key=trigger_key.key_id,
        skills=[macro_state_with_preset.skills.placed_skills[0]],
    )
    macro_state_with_preset.link_skills = (
        [link_skill] if trigger_kind == "link" else []
    )
    current_time: list[float] = [100.0]
    macro_session = run_macro.MacroStartSession(
        trigger_key=trigger_key,
        trigger_pressed_at=99.0,
        hold_transition_at=99.3,
        run_id=1,
    )
    link_session = run_macro.ManualLinkSession(
        link_skill=link_skill,
        trigger_key=trigger_key,
        trigger_pressed_at=99.0,
        delay_seconds=0.3,
        hold_transition_at=99.3,
    )

    monkeypatch.setattr(
        run_macro.time,
        "perf_counter",
        lambda: current_time[0],
    )
    monkeypatch.setattr(run_macro, "pressed_keys", set())
    monkeypatch.setattr(run_macro, "pressed_key_started_at", {})
    monkeypatch.setattr(run_macro, "handled_key_ids", set())
    monkeypatch.setattr(run_macro, "has_user_activity", False)
    monkeypatch.setattr(run_macro, "is_input_sequence_running", True)
    monkeypatch.setattr(
        run_macro,
        "active_macro_start_session",
        macro_session if trigger_kind == "main" else None,
    )
    monkeypatch.setattr(
        run_macro,
        "active_manual_link_session",
        link_session if trigger_kind == "link" else None,
    )
    app_state.macro.is_running = trigger_kind == "main"
    app_state.macro.run_id = 1

    run_macro.on_press(cast(Key | KeyCode, trigger_key.value))

    assert trigger_key.key_id in run_macro.handled_key_ids
    assert app_state.macro.is_running is (trigger_kind == "main")
    assert not link_session.stop_event.is_set()

    current_time[0] = 100.49
    assert _run_checking_thread_until_first_sleep(monkeypatch) == []
    assert app_state.macro.is_running is (trigger_kind == "main")
    assert not link_session.stop_event.is_set()

    if session_ends_early:
        app_state.macro.is_running = False
        run_macro.is_input_sequence_running = False
        run_macro.active_macro_start_session = None
        run_macro.active_manual_link_session = None

    current_time[0] = 100.501
    assert _run_checking_thread_until_first_sleep(monkeypatch) == []
    assert trigger_key.key_id in run_macro.handled_key_ids
    if trigger_kind == "main":
        assert app_state.macro.is_running is False
    else:
        assert link_session.stop_event.is_set() is not session_ends_early


@pytest.mark.parametrize("remember_state", [False, True])
def test_manual_link_hold_reuses_cooldown_and_resets_only_temporary_state(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
    remember_state: bool,
) -> None:
    """홀드 재사용과 동기화 OFF 임시 쿨타임 폐기 검증"""

    macro_state_with_preset.settings.custom_delay = 300
    macro_state_with_preset.settings.use_custom_delay = True
    skill_id: str = macro_state_with_preset.skills.placed_skills[0]
    link_skill = LinkSkill(skills=[skill_id], remember_state=remember_state)
    trigger_pressed_at: float = -0.1
    released: list[bool] = [False]

    def release_after_reuse(current_time: list[float], target_time: float) -> None:
        if not released[0] and current_time[0] < 4.3 <= target_time:
            current_time[0] = 4.3
            run_macro.on_release(KeyCode.from_char("q"))
            released[0] = True

    recorded_inputs, session = _record_manual_link_run(
        monkeypatch=monkeypatch,
        link_skill=link_skill,
        event_hook=release_after_reuse,
        initial_time=0.0,
        trigger_pressed_at=trigger_pressed_at,
        delay_seconds=0.3,
    )
    input_times: list[float] = [
        input_time for input_time, key_id in recorded_inputs if key_id != "h"
    ]

    assert input_times == [0.0, 4.2]
    assert session.is_hold is True
    assert link_skill.skill_timers == ({skill_id: 4.2} if remember_state else {})


def test_checking_thread_uses_current_delay_for_manual_link_hold_transition(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """실제 입력 감지 경계의 현재 딜레이 기반 홀드 전환 시각 검증"""

    macro_state_with_preset.settings.custom_delay = 450
    macro_state_with_preset.settings.use_custom_delay = True
    macro_state_with_preset.settings.custom_key_hold_seconds = 0.2
    macro_state_with_preset.settings.use_custom_key_hold_seconds = True
    trigger_key: KeySpec = KeyRegistry.get("q")
    trigger_pressed_at: float = 99.8
    current_time: list[float] = [100.0]
    link_skill = LinkSkill(
        key_type=LinkKeyType.ON,
        key=trigger_key.key_id,
        skills=[macro_state_with_preset.skills.placed_skills[0]],
    )
    macro_state_with_preset.link_skills = [link_skill]

    monkeypatch.setattr(
        run_macro.time,
        "perf_counter",
        lambda: current_time[0],
    )
    monkeypatch.setattr(run_macro, "pressed_keys", {trigger_key})
    monkeypatch.setattr(
        run_macro,
        "pressed_key_started_at",
        {trigger_key.key_id: trigger_pressed_at},
    )
    monkeypatch.setattr(run_macro, "handled_key_ids", set())
    monkeypatch.setattr(run_macro, "has_user_activity", False)
    monkeypatch.setattr(run_macro, "is_input_sequence_running", False)
    monkeypatch.setattr(run_macro, "active_manual_link_session", None)

    sleep_seconds: list[float] = []
    started_threads = _run_checking_thread_until_first_sleep(
        monkeypatch,
        sleep_seconds,
    )

    assert len(started_threads) == 1
    assert sleep_seconds == [0.05]
    target, args, daemon = started_threads[0]
    assert target is run_macro.use_link_skill
    assert daemon is True
    assert len(args) == 1
    session = cast(run_macro.ManualLinkSession, args[0])
    assert session.link_skill is link_skill
    assert session.trigger_key == trigger_key
    assert session.trigger_pressed_at == trigger_pressed_at
    assert session.delay_seconds == 0.45
    assert session.hold_transition_at == 100.45

    current_time[0] = 100.1
    run_macro.on_release(KeyCode.from_char("q"))
    current_time[0] = 100.11
    run_macro.on_press(KeyCode.from_char("q"))

    current_time[0] = 100.3
    assert _run_checking_thread_until_first_sleep(monkeypatch) == []
    assert not session.stop_event.is_set()

    current_time[0] = 100.311
    assert _run_checking_thread_until_first_sleep(monkeypatch) == []
    assert session.stop_event.is_set()


@pytest.mark.parametrize(
    ("current_time", "expected"),
    [
        (10.299, False),
        (10.3, True),
        (10.849, True),
        (10.85, False),
    ],
)
def test_basic_attack_uses_fixed_asymmetric_skill_guards(
    current_time: float,
    expected: bool,
) -> None:
    """설정 딜레이와 무관한 스킬 후 300ms·스킬 전 150ms 보호 검증"""

    assert (
        can_use_basic_attack(
            current_time=current_time,
            last_skill_input_at=10.0,
            next_skill_input_at=11.0,
        )
        is expected
    )


def test_clicking_mouse_thread_matches_basic_attack_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """실제 평타 스레드의 보호 구간 이후 600ms 입력 주기 검증"""

    skill_input_times: tuple[float, ...] = (0.0, 0.3, 0.6, 1.6)
    current_time: list[float] = [0.0]
    next_skill_index: list[int] = [0]
    click_times: list[float] = []

    class RecordingMouseController:
        """평타 입력 시각 기록용 마우스 컨트롤러"""

        def click(self, _button: Button) -> None:
            click_times.append(round(current_time[0], 3))

    def advance_clock(seconds: float) -> None:
        target_time: float = current_time[0] + seconds
        while (
            next_skill_index[0] < len(skill_input_times)
            and skill_input_times[next_skill_index[0]] <= target_time
        ):
            skill_input_at: float = skill_input_times[next_skill_index[0]]
            app_state.macro.last_skill_input_at = skill_input_at
            next_skill_index[0] += 1
            app_state.macro.next_skill_input_at = (
                skill_input_times[next_skill_index[0]]
                if next_skill_index[0] < len(skill_input_times)
                else None
            )

        current_time[0] = target_time
        if current_time[0] >= 3.0:
            app_state.macro.is_running = False

    monkeypatch.setattr(
        run_macro.time,
        "perf_counter",
        lambda: current_time[0],
    )
    monkeypatch.setattr(run_macro.time, "sleep", advance_clock)
    monkeypatch.setattr(
        run_macro.mouse,
        "Controller",
        RecordingMouseController,
    )

    app_state.macro.is_running = True
    app_state.macro.run_id = 1
    app_state.macro.last_skill_input_at = None
    app_state.macro.next_skill_input_at = skill_input_times[0]

    run_macro.clicking_mouse_thread(run_id=1)

    assert click_times == [0.9, 1.9, 2.5]


def test_runtime_exposes_attack_window_between_queued_skills(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """500ms 간격의 연속 스킬 사이 50ms 평타 허용 창 검증"""

    macro_state_with_preset.settings.custom_delay = 500
    macro_state_with_preset.settings.use_custom_delay = True
    init_macro()

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    app_state.macro.task_list = placed_refs[:2]
    monkeypatch.setattr(app_state.macro, "is_running", True)

    current_times: Iterator[float] = iter((100.0, 100.0))
    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: next(current_times))
    monkeypatch.setattr(run_macro.keyboard, "Controller", lambda: None)
    monkeypatch.setattr(run_macro.mouse, "Controller", lambda: None)
    monkeypatch.setattr(run_macro, "_press_key_spec", lambda *_args: None)
    monkeypatch.setattr(
        run_macro,
        "_wait_until_while_macro_running",
        lambda _end_at: None,
    )

    is_used_skill, _current_line_index = run_macro.use_skill(
        current_line_index=0,
    )

    assert is_used_skill is True
    assert app_state.macro.last_skill_input_at == 100.0
    assert app_state.macro.next_skill_input_at == 100.5
    assert can_use_basic_attack(
        current_time=100.31,
        last_skill_input_at=app_state.macro.last_skill_input_at,
        next_skill_input_at=app_state.macro.next_skill_input_at,
    )
    assert not can_use_basic_attack(
        current_time=100.35,
        last_skill_input_at=app_state.macro.last_skill_input_at,
        next_skill_input_at=app_state.macro.next_skill_input_at,
    )


def test_runtime_allows_basic_attack_while_every_skill_is_on_cooltime(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """전체 스킬 쿨타임 상태로 시작한 런타임의 평타 허용 검증"""

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    macro_state_with_preset.settings.remember_previous_state = True
    macro_state_with_preset.settings.use_default_attack = False

    # 전체 스킬을 방금 사용한 상태로 복원해 첫 반복에서 사용 가능한 스킬이 없게 구성
    app_state.macro.skill_cooltime_timers = {
        skill_ref: 100.0 for skill_ref in placed_refs
    }
    app_state.macro.prepared_skills = set()
    app_state.macro.is_running = True
    app_state.macro.run_id = 1

    def stop_after_wait(_end_at: float) -> None:
        app_state.macro.is_running = False

    monkeypatch.setattr(run_macro.time, "perf_counter", lambda: 100.0)
    monkeypatch.setattr(
        run_macro,
        "_wait_until_while_macro_running",
        stop_after_wait,
    )
    monkeypatch.setattr(run_macro.keyboard, "Controller", lambda: None)
    monkeypatch.setattr(run_macro.mouse, "Controller", lambda: None)

    run_macro.running_macro_thread(run_id=1)

    # 가장 빨리 준비되는 스킬의 쿨타임 4.0초와 추가 대기 0.2초 이후가 다음 입력 시각
    assert app_state.macro.next_skill_input_at == pytest.approx(104.2)
    assert can_use_basic_attack(
        current_time=101.0,
        last_skill_input_at=app_state.macro.last_skill_input_at,
        next_skill_input_at=app_state.macro.next_skill_input_at,
    )
    assert not can_use_basic_attack(
        current_time=104.1,
        last_skill_input_at=app_state.macro.last_skill_input_at,
        next_skill_input_at=app_state.macro.next_skill_input_at,
    )


def _record_runtime_skill_events(
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[SkillUseEvent, ...]:
    """실제 런타임 경로의 60초 스킬 입력 기록"""

    macro_state_with_preset.settings.use_default_attack = False
    current_time_seconds: list[float] = [0.0]
    end_time_seconds: float = 60.0
    current_line_index: list[int] = [0]
    recorded_events: list[SkillUseEvent] = []
    clock_advance_count: list[int] = [0]
    skill_key_index_by_value: dict[Key | KeyCode, int] = {
        cast(Key | KeyCode, KeyRegistry.get(key_id).value): scroll_index
        for scroll_index, key_id in enumerate(
            macro_state_with_preset.skills.skill_keys
        )
    }
    swap_key_value: Key | KeyCode = cast(
        Key | KeyCode,
        app_state.macro.current_swap_key.value,
    )

    class RecordingKeyboardController:
        """스킬 슬롯과 입력 시각 기록용 키보드 컨트롤러"""

        def press(self, key: Key | KeyCode) -> None:
            if key == swap_key_value:
                current_line_index[0] = 1 - current_line_index[0]
                return

            scroll_index: int | None = skill_key_index_by_value.get(key)
            if scroll_index is None:
                return

            skill_ref = EquippedSkillRef(
                scroll_index=scroll_index,
                line_index=current_line_index[0],
            )
            recorded_events.append(
                SkillUseEvent(
                    skill_id=(
                        macro_state_with_preset.skills.get_placed_skill_id(skill_ref)
                    ),
                    time=round(current_time_seconds[0], 3),
                )
            )

        def release(self, _key: Key | KeyCode) -> None:
            return

    keyboard_controller = RecordingKeyboardController()

    def advance_clock(seconds: float) -> None:
        clock_advance_count[0] += 1
        if clock_advance_count[0] > 10000:
            pytest.fail("60초 런타임 가상 시계가 제한 횟수 안에 완료되지 않았습니다.")

        clock_step_seconds: float = max(seconds, 0.000000001)
        current_time_seconds[0] = min(
            round(current_time_seconds[0] + clock_step_seconds, 9),
            end_time_seconds,
        )
        if current_time_seconds[0] >= end_time_seconds:
            app_state.macro.is_running = False

    with monkeypatch.context() as runtime_patches:
        runtime_patches.setattr(
            run_macro.time,
            "perf_counter",
            lambda: current_time_seconds[0],
        )
        runtime_patches.setattr(
            run_macro.time,
            "time",
            lambda: current_time_seconds[0],
        )
        runtime_patches.setattr(run_macro.time, "sleep", advance_clock)
        runtime_patches.setattr(
            run_macro.keyboard,
            "Controller",
            lambda: keyboard_controller,
        )
        runtime_patches.setattr(run_macro.mouse, "Controller", lambda: None)

        app_state.macro.is_running = True
        app_state.macro.run_id += 1
        run_macro.running_macro_thread(run_id=app_state.macro.run_id)

    return tuple(recorded_events)


@pytest.mark.parametrize("cooltime_reduction", [0.0, 20.0, 40.0])
def test_runtime_matches_60_second_simulation_sequence_for_14_skills(
    synthetic_server: ServerSpec,
    macro_state_with_preset: MacroPreset,
    monkeypatch: pytest.MonkeyPatch,
    cooltime_reduction: float,
) -> None:
    """스킬속도별 14스킬 런타임과 시뮬레이터의 60초 시퀀스 검증"""

    placed_refs: list[EquippedSkillRef] = (
        macro_state_with_preset.skills.get_placed_skill_refs(synthetic_server)
    )
    assert len(placed_refs) == 14

    first_link_skill_id: str = macro_state_with_preset.skills.placed_skills[1]
    second_link_skill_id: str = macro_state_with_preset.skills.placed_skills[6]
    macro_state_with_preset.link_skills.append(
        LinkSkill(
            use_type=LinkUseType.AUTO,
            skills=[first_link_skill_id, second_link_skill_id],
        )
    )
    delay_ms: int = 300
    macro_state_with_preset.settings.custom_delay = delay_ms
    macro_state_with_preset.settings.use_custom_delay = True
    macro_state_with_preset.settings.custom_cooltime_reduction = cooltime_reduction
    macro_state_with_preset.settings.use_custom_cooltime_reduction = True
    macro_state_with_preset.settings.custom_cooltime_extra_wait = 350
    macro_state_with_preset.settings.use_custom_cooltime_extra_wait = True
    expected_events: tuple[SkillUseEvent, ...] = build_skill_use_sequence(
        server_spec=synthetic_server,
        preset=macro_state_with_preset,
        skills_info=macro_state_with_preset.usage_settings,
        delay_ms=delay_ms,
        cooltime_reduction=cooltime_reduction,
    )

    actual_events: tuple[SkillUseEvent, ...] = _record_runtime_skill_events(
        macro_state_with_preset=macro_state_with_preset,
        monkeypatch=monkeypatch,
    )

    assert actual_events == expected_events


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
