from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import NoReturn, cast

from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

from app.scripts.app_state import app_state
from app.scripts.config import config
from app.scripts.macro_models import (
    EquippedSkillRef,
    LinkKeyType,
    LinkSkill,
)
from app.scripts.macro_scheduler import (
    BASIC_ATTACK_INTERVAL_MILLISECONDS,
    build_auto_link_skill_groups,
    build_priority_skill_sequence,
    build_skill_cooltimes_ms,
    can_use_basic_attack,
    take_next_task,
)
from app.scripts.registry.key_registry import KeyRegistry, KeySpec

DEBUG_PRINT_INFO = False
ATTACK_PAUSE_POLL_SECONDS = 0.01
MACRO_SLEEP_POLL_SECONDS = 0.05
SKILL_RECHECK_BUFFER_MILLISECONDS = 50


# 전역 입력 상태 추적
pressed_keys: set[KeySpec] = set()
pressed_key_started_at: dict[str, float] = {}
handled_key_ids: set[str] = set()
has_user_activity = False

# 프로그램 주입 입력 추적 상태
injected_press_counts: dict[str, int] = {}
injected_release_counts: dict[str, int] = {}
injected_input_lock: Lock = Lock()

# 매크로와 수동 연계스킬의 동시 실행 방지 상태
is_input_sequence_running = False


def is_input_sequence_active() -> bool:
    """메인 매크로 또는 수동 연계 입력 실행 여부 반환"""

    return app_state.macro.is_running or is_input_sequence_running


@dataclass(slots=True)
class ManualLinkSession:
    """수동 연계 입력 한 번의 실행 상태"""

    link_skill: LinkSkill
    trigger_key: KeySpec
    trigger_pressed_at: float
    delay_seconds: float
    hold_transition_at: float
    stop_pressed_at: float | None = None
    stop_event: Event = field(default_factory=Event)
    is_hold: bool = False


@dataclass(slots=True)
class MacroStartSession:
    """메인 매크로 시작키 한 번의 입력 상태"""

    trigger_key: KeySpec
    trigger_pressed_at: float
    hold_transition_at: float
    run_id: int
    stop_pressed_at: float | None = None


# 현재 실행 중인 수동 연계 입력 상태
active_manual_link_session: ManualLinkSession | None = None
manual_link_session_lock: Lock = Lock()

# 현재 실행 중인 메인 매크로 시작 입력 상태
active_macro_start_session: MacroStartSession | None = None
macro_start_session_lock: Lock = Lock()


@dataclass(slots=True)
class PreviewTaskState:
    """프리뷰 계산용 상태 묶음"""

    prepared_skills: set[EquippedSkillRef]
    task_list: list[EquippedSkillRef]
    skill_sequence: list[EquippedSkillRef]
    using_link_skills: list[list[EquippedSkillRef]]


def _reserve_stop_intent(key_spec: KeySpec, pressed_at: float) -> None:
    """실행 중인 입력과 같은 키의 재입력을 중지 의도로 고정"""

    # 메인 매크로 재입력의 대상 실행을 물리적 press 시점에 고정
    with macro_start_session_lock:
        macro_session: MacroStartSession | None = active_macro_start_session
        if (
            macro_session is not None
            and macro_session.trigger_key.key_id == key_spec.key_id
            and macro_session.trigger_pressed_at != pressed_at
            and app_state.macro.is_running
            and app_state.macro.run_id == macro_session.run_id
        ):
            macro_session.stop_pressed_at = pressed_at
            handled_key_ids.add(key_spec.key_id)
            return

    # 수동 연계 재입력의 대상 실행을 물리적 press 시점에 고정
    with manual_link_session_lock:
        link_session: ManualLinkSession | None = active_manual_link_session
        if (
            link_session is not None
            and link_session.trigger_key.key_id == key_spec.key_id
            and link_session.trigger_pressed_at != pressed_at
        ):
            link_session.stop_pressed_at = pressed_at
            handled_key_ids.add(key_spec.key_id)


def _apply_pending_macro_stop(key_hold_seconds: float) -> None:
    """유지 시간을 충족한 메인 매크로 중지 의도 확정"""

    with macro_start_session_lock:
        session: MacroStartSession | None = active_macro_start_session
        if session is None or session.stop_pressed_at is None:
            return

        if (
            pressed_key_started_at.get(session.trigger_key.key_id)
            != session.stop_pressed_at
        ):
            session.stop_pressed_at = None
            return

        if (
            is_key_held(session.trigger_key, key_hold_seconds)
            and app_state.macro.is_running
            and app_state.macro.run_id == session.run_id
        ):
            app_state.macro.is_running = False


def _apply_pending_manual_link_stop(key_hold_seconds: float) -> None:
    """유지 시간을 충족한 수동 연계 중지 의도 확정"""

    with manual_link_session_lock:
        session: ManualLinkSession | None = active_manual_link_session
        if session is None or session.stop_pressed_at is None:
            return

        if (
            pressed_key_started_at.get(session.trigger_key.key_id)
            != session.stop_pressed_at
        ):
            session.stop_pressed_at = None
            return

        if is_key_held(session.trigger_key, key_hold_seconds):
            session.stop_event.set()


def _stop_manual_link_on_hold_release(key_spec: KeySpec) -> None:
    """홀드 전환된 수동 연계의 단축키 해제를 중지 요청으로 처리"""

    with manual_link_session_lock:
        session: ManualLinkSession | None = active_manual_link_session
        if session is None or session.trigger_key.key_id != key_spec.key_id:
            return

        if (
            pressed_key_started_at.get(key_spec.key_id)
            != session.trigger_pressed_at
        ):
            return

        now: float = time.perf_counter()
        if not session.is_hold and now < session.hold_transition_at:
            return

        session.is_hold = True
        session.stop_event.set()


def _stop_macro_on_hold_release(key_spec: KeySpec) -> None:
    """홀드 전환된 메인 매크로의 시작키 해제를 중지 요청으로 처리"""

    with macro_start_session_lock:
        session: MacroStartSession | None = active_macro_start_session
        if session is None or session.trigger_key.key_id != key_spec.key_id:
            return

        if (
            pressed_key_started_at.get(key_spec.key_id)
            != session.trigger_pressed_at
        ):
            return

        if (
            not app_state.macro.is_running
            or app_state.macro.run_id != session.run_id
            or time.perf_counter() < session.hold_transition_at
        ):
            return

        app_state.macro.is_running = False


def _register_injected_key_event(key_spec: KeySpec) -> None:
    """프로그램이 직접 주입하는 키 이벤트 등록"""

    # 리스너 무시 대상 press/release 카운트 등록
    with injected_input_lock:
        injected_press_counts[key_spec.key_id] = (
            injected_press_counts.get(key_spec.key_id, 0) + 1
        )
        injected_release_counts[key_spec.key_id] = (
            injected_release_counts.get(key_spec.key_id, 0) + 1
        )


def _consume_injected_input_event(
    key_spec: KeySpec,
    counters: dict[str, int],
) -> bool:
    """프로그램이 등록한 입력인지 확인 후 소모"""

    # 등록된 주입 입력 카운트 차감
    with injected_input_lock:
        remaining_count: int = counters.get(key_spec.key_id, 0)
        if remaining_count == 0:
            return False

        if remaining_count == 1:
            del counters[key_spec.key_id]

        else:
            counters[key_spec.key_id] = remaining_count - 1

    return True


def _clear_injected_key_events() -> None:
    """누적된 프로그램 주입 입력 추적 상태 초기화"""

    # 이전 실행 주기의 잔여 주입 입력 상태 정리
    with injected_input_lock:
        injected_press_counts.clear()
        injected_release_counts.clear()


def on_press(key: Key | KeyCode | None) -> None:
    """키가 눌렸을 때 호출되는 함수"""

    global pressed_keys, pressed_key_started_at, handled_key_ids, has_user_activity

    if key is None:
        return

    key_spec: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(key)

    # 프로그램이 보낸 키 입력은 AFK 갱신 대상에서 제외
    if key_spec is not None and _consume_injected_input_event(
        key_spec,
        injected_press_counts,
    ):
        return

    # 잠수 감지는 인식 불가 키도 사용자 입력으로 인정
    has_user_activity = True

    # 모디파이어 조합 등으로 변형된 키도 동일 KeySpec으로 정규화
    if key_spec is not None:
        # 최초 입력 시점 기록 및 이전 처리 상태 초기화
        if key_spec not in pressed_keys:
            pressed_at: float = time.perf_counter()
            pressed_key_started_at[key_spec.key_id] = pressed_at
            handled_key_ids.discard(key_spec.key_id)
            _reserve_stop_intent(key_spec, pressed_at)

        pressed_keys.add(key_spec)


def on_release(key: Key | KeyCode | None) -> None:
    """키가 떼어졌을 때 호출되는 함수"""

    global pressed_keys, pressed_key_started_at, handled_key_ids

    if key is None:
        return

    key_spec: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(key)
    if key_spec is not None:
        # 프로그램이 보낸 키 해제 입력은 눌림 상태 추적에서 제외
        if _consume_injected_input_event(key_spec, injected_release_counts):
            return

        _stop_manual_link_on_hold_release(key_spec)
        _stop_macro_on_hold_release(key_spec)

        # 눌림 상태 및 1회 처리 상태 해제
        pressed_keys.discard(key_spec)
        pressed_key_started_at.pop(key_spec.key_id, None)
        handled_key_ids.discard(key_spec.key_id)


def on_click(
    x: int,
    y: int,
    button: Button,
    pressed: bool,
) -> None:
    """마우스 버튼 입력 시 호출되는 함수"""

    global pressed_keys, pressed_key_started_at, handled_key_ids, has_user_activity

    # 지원하는 마우스 버튼 기준 KeySpec 정규화
    key_spec: KeySpec | None = KeyRegistry.pynput_mouse_to_keyspec(button)
    if key_spec is None:
        return

    # 프로그램이 보낸 마우스 입력은 사용자 입력 상태에서 제외
    counters: dict[str, int] = (
        injected_press_counts if pressed else injected_release_counts
    )
    if _consume_injected_input_event(key_spec, counters):
        return

    # 사용자 마우스 사이드버튼 입력 기준 AFK 갱신
    has_user_activity = True

    # 마우스 버튼 press 상태 등록
    if pressed:
        if key_spec not in pressed_keys:
            pressed_at: float = time.perf_counter()
            pressed_key_started_at[key_spec.key_id] = pressed_at
            handled_key_ids.discard(key_spec.key_id)
            _reserve_stop_intent(key_spec, pressed_at)

        pressed_keys.add(key_spec)
        return

    _stop_manual_link_on_hold_release(key_spec)
    _stop_macro_on_hold_release(key_spec)

    # 마우스 버튼 release 상태 해제
    pressed_keys.discard(key_spec)
    pressed_key_started_at.pop(key_spec.key_id, None)
    handled_key_ids.discard(key_spec.key_id)


def on_move(x: int, y: int) -> None:
    """마우스가 움직였을 때 호출되는 함수"""

    global has_user_activity

    # 잠수 감지용 사용자 마우스 이동 기록
    has_user_activity = True


def is_key_held(key: KeySpec, hold_seconds: float) -> bool:
    """특정 키가 설정 시간 이상 눌려있는지 확인"""

    global pressed_keys, pressed_key_started_at

    # 현재 눌리지 않은 키 제외
    if key not in pressed_keys:
        return False

    # 키 입력 시작 이후 경과 시간 확인
    started_at: float | None = pressed_key_started_at.get(key.key_id)
    if started_at is None:
        pressed_keys.discard(key)
        return False

    return time.perf_counter() - started_at >= hold_seconds


def _press_key_spec(
    kbd_controller: keyboard.Controller,
    mouse_controller: mouse.Controller,
    key_spec: KeySpec,
) -> None:
    """KeySpec 기준 키보드 또는 마우스 입력 실행"""

    # 프로그램 주입 입력 등록
    _register_injected_key_event(key_spec)

    # 마우스 버튼 입력 실행
    if key_spec.type == "mouse":
        mouse_button: Button = cast(Button, key_spec.value)
        mouse_controller.press(mouse_button)
        mouse_controller.release(mouse_button)
        return

    # 키보드 키 입력 실행
    keyboard_key: Key | KeyCode = cast(Key | KeyCode, key_spec.value)
    kbd_controller.press(keyboard_key)
    kbd_controller.release(keyboard_key)


def checking_kb_thread() -> NoReturn:
    """키보드 입력 감지 쓰레드"""

    global active_macro_start_session
    global active_manual_link_session
    global has_user_activity, handled_key_ids, is_input_sequence_running

    # 키보드 리스너 시작
    keyboard_listener: keyboard.Listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release,
    )
    keyboard_listener.start()

    # 마우스 버튼 및 이동 리스너 시작
    mouse_listener: mouse.Listener = mouse.Listener(on_click=on_click, on_move=on_move)
    mouse_listener.start()

    while True:
        # 다른 키 설정 중일 때는 패스
        if app_state.ui.is_setting_key:
            time.sleep(0.1)
            continue

        # 매크로 실행중일 때 사용자 활동이 있으면 잠수 시간 초기화
        if app_state.macro.is_running and has_user_activity:
            app_state.macro.afk_started_time = time.time()

            # 플래그 리셋
            has_user_activity = False

        # 시작키 유지 시간 기준 충족 여부 확인
        key_hold_seconds: float = app_state.macro.current_key_hold_seconds
        start_key: KeySpec = app_state.macro.current_start_key
        start_pressed_at: float | None = pressed_key_started_at.get(start_key.key_id)

        # press 시점에 고정한 메인 매크로 중지 의도 판정
        _apply_pending_macro_stop(key_hold_seconds)

        # 매크로 시작/중지
        if (
            start_pressed_at is not None
            and is_key_held(start_key, key_hold_seconds)
            and start_key.key_id not in handled_key_ids
        ):
            handled_key_ids.add(start_key.key_id)

            # 실행 중이면 즉시 종료 상태 전환
            if app_state.macro.is_running:
                app_state.macro.is_running = False

            # 실행 중이 아니면 새 실행 시작
            else:
                if is_input_sequence_running:
                    continue

                is_input_sequence_running = True
                app_state.macro.is_running = True

                # 매크로 번호 증가
                app_state.macro.run_id += 1
                run_id: int = app_state.macro.run_id

                delay_seconds: float = (
                    app_state.macro.current_delay
                    * 0.001
                    * config.macro.SLEEP_COEFFICIENT_NORMAL
                )
                session = MacroStartSession(
                    trigger_key=start_key,
                    trigger_pressed_at=start_pressed_at,
                    hold_transition_at=time.perf_counter() + delay_seconds,
                    run_id=run_id,
                )
                with macro_start_session_lock:
                    active_macro_start_session = session

                # 매크로 쓰레드 시작
                Thread(
                    target=running_macro_thread,
                    args=[run_id],
                    daemon=True,
                ).start()

            continue

        if is_input_sequence_running:
            # press 시점에 고정한 수동 연계 중지 의도 판정
            _apply_pending_manual_link_stop(key_hold_seconds)

            with manual_link_session_lock:
                active_link_session: ManualLinkSession | None = (
                    active_manual_link_session
                )

            # 연계스킬
            for link_skill in app_state.macro.current_preset.link_skills:
                if link_skill.key_type == LinkKeyType.OFF or link_skill.key is None:
                    continue

                link_key: KeySpec = KeyRegistry.get(link_skill.key)
                if link_key in pressed_keys:
                    if (
                        active_link_session is not None
                        and link_key.key_id
                        == active_link_session.trigger_key.key_id
                    ):
                        continue

                    handled_key_ids.add(link_key.key_id)

            time.sleep(0.05 * config.macro.SLEEP_COEFFICIENT_NORMAL)
            continue

        # 연계스킬 사용
        for link_skill in app_state.macro.current_preset.link_skills:
            # 단축키가 설정된 연계스킬만 검사
            if link_skill.key_type == LinkKeyType.OFF or link_skill.key is None:
                continue

            # 연계스킬 키가 눌렸다면
            link_key: KeySpec = KeyRegistry.get(link_skill.key)
            trigger_pressed_at: float | None = pressed_key_started_at.get(
                link_key.key_id
            )
            if (
                trigger_pressed_at is not None
                and is_key_held(link_key, key_hold_seconds)
                and link_key.key_id not in handled_key_ids
            ):
                delay_seconds: float = (
                    app_state.macro.current_delay
                    * 0.001
                    * config.macro.SLEEP_COEFFICIENT_NORMAL
                )
                activated_at: float = time.perf_counter()
                session = ManualLinkSession(
                    link_skill=link_skill,
                    trigger_key=link_key,
                    trigger_pressed_at=trigger_pressed_at,
                    delay_seconds=delay_seconds,
                    hold_transition_at=activated_at + delay_seconds,
                )

                handled_key_ids.add(link_key.key_id)
                with manual_link_session_lock:
                    active_manual_link_session = session
                    is_input_sequence_running = True

                Thread(
                    target=use_link_skill,
                    args=[session],
                    daemon=True,
                ).start()
                break

        # 연계스킬이 실행되지 않았으면 0.05초 슬립
        else:
            time.sleep(0.05 * config.macro.SLEEP_COEFFICIENT_NORMAL)
            continue

        # 연계 실행 직후부터 실행 중 입력 감지 주기로 복귀
        continue


def running_macro_thread(run_id: int) -> None:
    """매크로 메인 쓰레드"""

    global active_macro_start_session
    global is_input_sequence_running

    current_line_index: int = 0

    try:
        init_macro()

        # 평타 사용 여부와 무관한 첫 스킬 입력 예정 시각 초기화
        app_state.macro.next_skill_input_at = time.perf_counter()

        # 매크로 클릭 쓰레드
        if app_state.macro.current_use_default_attack:
            Thread(
                target=clicking_mouse_thread,
                args=[run_id],
                daemon=True,
            ).start()

        while app_state.macro.is_running and app_state.macro.run_id == run_id:
            # taskList에 사용 가능한 스킬 추가
            wait_seconds: float = 0.0
            if not app_state.macro.task_list:
                wait_seconds = build_task_list(show_info=DEBUG_PRINT_INFO)

                # 대기 중에도 평타 보호 구간이 실제 다음 스킬 시각을 따르도록 갱신
                app_state.macro.next_skill_input_at = _get_next_runnable_skill_at(
                    time.perf_counter()
                )

            # 스킬 준비 시점 직전의 재평가 구간 확보
            if not app_state.macro.task_list and wait_seconds > 0.0:
                wait_milliseconds: int = round(wait_seconds * 1000)
                recheck_lead_milliseconds: int = (
                    app_state.macro.current_delay + SKILL_RECHECK_BUFFER_MILLISECONDS
                )

                if wait_milliseconds > recheck_lead_milliseconds:
                    _wait_until_while_macro_running(
                        time.perf_counter()
                        + (wait_milliseconds - recheck_lead_milliseconds)
                        * 0.001
                        * config.macro.SLEEP_COEFFICIENT_UNIT
                    )
                    continue

            # 스킬 사용하고 사용 여부 리턴
            is_used_skill, current_line_index = use_skill(
                current_line_index=current_line_index,
            )

            # 잠수면 매크로 중지
            if (
                config.macro.is_afk_enabled
                and time.time() - app_state.macro.afk_started_time
                >= config.macro.AFK_TIMEOUT_SECONDS
            ):
                # UI 스레드 알림 표시용 잠수 종료 상태 기록
                app_state.macro.has_pending_afk_notice = True
                app_state.macro.is_running = False

            if not is_used_skill:
                wait_duration_seconds: float = (
                    wait_seconds * config.macro.SLEEP_COEFFICIENT_UNIT
                    if wait_seconds > 0.0
                    else MACRO_SLEEP_POLL_SECONDS
                )
                _wait_until_while_macro_running(
                    time.perf_counter() + wait_duration_seconds
                )
    finally:
        if app_state.macro.run_id == run_id:
            try:
                # 현재 실행 주기 종료 시 1줄 종료 상태 복구
                _settle_cooltime_state_after_stop()
                kbd_controller: keyboard.Controller = keyboard.Controller()
                mouse_controller: mouse.Controller = mouse.Controller()
                _restore_first_line_state(
                    kbd_controller,
                    mouse_controller,
                    current_line_index,
                )
            finally:
                with macro_start_session_lock:
                    session: MacroStartSession | None = active_macro_start_session
                    if session is not None and session.run_id == run_id:
                        active_macro_start_session = None

                # 매크로 종료 후 입력 점유 상태 해제
                is_input_sequence_running = False


def clicking_mouse_thread(run_id: int) -> None:
    """마우스 클릭 쓰레드"""

    mouse_controller: mouse.Controller = mouse.Controller()

    while app_state.macro.is_running and app_state.macro.run_id == run_id:
        # 직전·다음 스킬 보호 구간에는 평타 클릭 보류
        if not can_use_basic_attack(
            current_time=time.perf_counter(),
            last_skill_input_at=app_state.macro.last_skill_input_at,
            next_skill_input_at=app_state.macro.next_skill_input_at,
        ):
            time.sleep(ATTACK_PAUSE_POLL_SECONDS)
            continue

        mouse_controller.click(mouse.Button.left)
        time.sleep(BASIC_ATTACK_INTERVAL_MILLISECONDS * 0.001)


def _get_next_runnable_skill_at(not_before: float) -> float | None:
    """현재 스케줄 상태에서 다음 실제 스킬 입력 가능 시각 반환"""

    if app_state.macro.task_list:
        return not_before

    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )
    ready_delays_ms: dict[EquippedSkillRef, int] = (
        _build_runtime_skill_ready_delays_ms()
    )
    ready_at_by_ref: dict[EquippedSkillRef, float] = {
        skill_ref: (
            app_state.macro.skill_cooltime_timers[skill_ref]
            + ready_delays_ms[skill_ref] * 0.001
        )
        for skill_ref in placed_refs
        if skill_ref not in app_state.macro.prepared_skills
    }
    candidate_times: set[float] = {not_before}
    candidate_times.update(
        max(not_before, ready_at) for ready_at in ready_at_by_ref.values()
    )

    for candidate_time in sorted(candidate_times):
        future_prepared_skills: set[EquippedSkillRef] = (
            app_state.macro.prepared_skills.copy()
        )
        future_prepared_skills.update(
            skill_ref
            for skill_ref, ready_at in ready_at_by_ref.items()
            if ready_at <= candidate_time
        )
        next_task: tuple[EquippedSkillRef, ...] = take_next_task(
            preset=app_state.macro.current_preset,
            skills_info=app_state.macro.current_preset.usage_settings,
            prepared_skills=future_prepared_skills,
            auto_link_skill_groups=tuple(
                tuple(link_skill) for link_skill in app_state.macro.using_link_skills
            ),
            skill_sequence=tuple(app_state.macro.skill_sequence),
        )
        if next_task:
            return candidate_time

    return None


def _wait_until_while_macro_running(end_at: float) -> None:
    """매크로 중지 상태를 확인하며 목표 시각까지 대기"""

    while app_state.macro.is_running:
        remaining_seconds: float = end_at - time.perf_counter()
        if remaining_seconds <= 0.0:
            return

        time.sleep(min(remaining_seconds, MACRO_SLEEP_POLL_SECONDS))


def _restore_first_line_state(
    kbd_controller: keyboard.Controller,
    mouse_controller: mouse.Controller,
    current_line_index: int,
) -> int:
    """현재 줄 상태를 1줄 종료 상태로 복구"""

    # 이미 1줄이면 추가 입력 없이 종료
    if current_line_index == 0:
        return current_line_index

    swap_key: KeySpec = app_state.macro.current_swap_key

    # 종료 복귀용 스왑 입력 등록
    _press_key_spec(kbd_controller, mouse_controller, swap_key)
    return 0


def _press_skill_keys(
    kbd_controller: keyboard.Controller,
    mouse_controller: mouse.Controller,
    skill_ref: EquippedSkillRef,
    current_line_index: int,
) -> tuple[int, float]:
    """줄 상태에 맞는 입력 수행"""

    # 현재 세로줄 공용키 기준 스킬 입력 키 조회
    skill_key: KeySpec = KeyRegistry.get(
        app_state.macro.current_preset.skills.skill_keys[skill_ref.scroll_index]
    )

    # 목표 줄과 현재 줄이 다르면 스왑 입력 수행
    if skill_ref.line_index != current_line_index:
        swap_key: KeySpec = app_state.macro.current_swap_key

        # 프로그램 주입 스왑 입력 등록
        _press_key_spec(kbd_controller, mouse_controller, swap_key)

        current_line_index = skill_ref.line_index

    # 프로그램 주입 스킬 입력 등록
    skill_input_at: float = time.perf_counter()
    _press_key_spec(kbd_controller, mouse_controller, skill_key)

    return current_line_index, skill_input_at


def _reset_cooltime_state(placed_refs: list[EquippedSkillRef]) -> None:
    """장착 스킬 기준 쿨타임 상태 초기화"""

    # 모든 장착 스킬을 즉시 사용 가능 상태로 등록
    now: float = time.perf_counter()
    app_state.macro.prepared_skills = set(placed_refs)
    app_state.macro.skill_cooltime_timers = {
        skill_ref: now for skill_ref in placed_refs
    }


def _has_cooltime_state(placed_refs: list[EquippedSkillRef]) -> bool:
    """장착 스킬 전체의 쿨타임 상태 존재 여부 반환"""

    # 장착 스킬별 타이머가 모두 남아 있어야 재시작 상태 유지
    placed_ref_set: set[EquippedSkillRef] = set(placed_refs)
    timer_ref_set: set[EquippedSkillRef] = set(
        app_state.macro.skill_cooltime_timers.keys()
    )
    return bool(placed_ref_set) and placed_ref_set.issubset(timer_ref_set)


def _build_runtime_skill_ready_delays_ms() -> dict[EquippedSkillRef, int]:
    """쿨타임과 추가 대기가 반영된 스킬별 재사용 가능 시간 구성"""

    cooltimes_ms: dict[EquippedSkillRef, int] = build_skill_cooltimes_ms(
        server_spec=app_state.macro.current_server,
        preset=app_state.macro.current_preset,
        cooltime_reduction=app_state.macro.current_cooltime_reduction,
    )
    extra_wait_ms: int = app_state.macro.current_cooltime_extra_wait
    return {
        skill_ref: cooltime_ms + extra_wait_ms
        for skill_ref, cooltime_ms in cooltimes_ms.items()
    }


def _collect_ready_cooltime_skills(
    placed_refs: list[EquippedSkillRef],
) -> set[EquippedSkillRef]:
    """현재 타이머 기준 사용 가능 스킬 목록 반환"""

    # 현재 장착 스킬만 준비 완료 후보로 유지
    placed_ref_set: set[EquippedSkillRef] = set(placed_refs)
    prepared_skills: set[EquippedSkillRef] = (
        app_state.macro.prepared_skills & placed_ref_set
    )
    now: float = time.perf_counter()
    ready_delays_ms: dict[EquippedSkillRef, int] = (
        _build_runtime_skill_ready_delays_ms()
    )

    # 쿨타임과 추가 대기가 모두 지난 스킬을 준비 완료 상태로 반영
    for skill_ref in placed_refs:
        if skill_ref in prepared_skills:
            continue

        started_at: float = app_state.macro.skill_cooltime_timers[skill_ref]
        elapsed_ms: int = round((now - started_at) * 1000)
        if elapsed_ms >= ready_delays_ms[skill_ref]:
            prepared_skills.add(skill_ref)

    return prepared_skills


def _restore_or_reset_cooltime_state(placed_refs: list[EquippedSkillRef]) -> None:
    """설정에 맞춘 쿨타임 상태 복원 또는 초기화"""

    # 상태 기억 비활성화 또는 보관 상태 없음이면 전체 쿨타임 초기화
    if (
        not app_state.macro.current_preset.settings.remember_previous_state
        or not _has_cooltime_state(placed_refs)
    ):
        _reset_cooltime_state(placed_refs)
        return

    app_state.macro.prepared_skills = _collect_ready_cooltime_skills(placed_refs)


def _settle_cooltime_state_after_stop() -> None:
    """매크로 중지 후 재시작용 쿨타임 상태 정리"""

    # 상태 기억 비활성화 시 다음 시작에서 전체 쿨타임 초기화
    if not app_state.macro.current_preset.settings.remember_previous_state:
        app_state.macro.clear_cooltime_state()
        return

    # 장착 스킬 기준 대기열과 타이머 상태 보존
    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )
    placed_ref_set: set[EquippedSkillRef] = set(placed_refs)
    prepared_skills: set[EquippedSkillRef] = (
        app_state.macro.prepared_skills | set(app_state.macro.task_list)
    ) & placed_ref_set

    # 미사용 대기열만 준비 상태로 되돌리고 기존 타이머는 그대로 유지
    app_state.macro.task_list.clear()
    app_state.macro.prepared_skills = prepared_skills


def init_macro() -> None:
    """매크로 초기 설정"""

    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )

    # 새 실행 사이클에 맞춘 런타임 상태 초기화
    _clear_injected_key_events()
    app_state.macro.afk_started_time = time.time()
    app_state.macro.has_pending_afk_notice = False
    app_state.macro.skill_sequence = list(
        build_priority_skill_sequence(
            server_spec=app_state.macro.current_server,
            preset=app_state.macro.current_preset,
            skills_info=app_state.macro.current_preset.usage_settings,
        )
    )
    app_state.macro.using_link_skills = [
        list(link_skill_group)
        for link_skill_group in build_auto_link_skill_groups(
            server_spec=app_state.macro.current_server,
            preset=app_state.macro.current_preset,
        )
    ]
    app_state.macro.last_skill_input_at = None
    app_state.macro.next_skill_input_at = None

    app_state.macro.task_list.clear()
    _restore_or_reset_cooltime_state(placed_refs)


def use_skill(current_line_index: int) -> tuple[bool, int]:
    """스킬 사용 함수"""

    if not app_state.macro.task_list:
        return False, current_line_index

    kbd_controller: keyboard.Controller = keyboard.Controller()
    mouse_controller: mouse.Controller = mouse.Controller()
    skill_ref: EquippedSkillRef = app_state.macro.task_list.pop(0)

    current_line_index, skill_input_at = _press_skill_keys(
        kbd_controller,
        mouse_controller,
        skill_ref,
        current_line_index=current_line_index,
    )
    skill_used_at: float = time.perf_counter()
    app_state.macro.skill_cooltime_timers[skill_ref] = skill_used_at
    app_state.macro.last_skill_input_at = skill_input_at

    delay_seconds: float = (
        app_state.macro.current_delay * 0.001 * config.macro.SLEEP_COEFFICIENT_NORMAL
    )
    delay_end_at: float = skill_used_at + delay_seconds
    app_state.macro.next_skill_input_at = _get_next_runnable_skill_at(delay_end_at)

    # 옵션 활성화 시 스킬 사용 후 1번 줄로 복귀
    if app_state.macro.current_always_return_to_first_line and current_line_index != 0:
        half_delay_seconds: float = delay_seconds * 0.5
        _wait_until_while_macro_running(skill_used_at + half_delay_seconds)
        current_line_index = _restore_first_line_state(
            kbd_controller,
            mouse_controller,
            current_line_index,
        )

        if app_state.macro.is_running:
            _wait_until_while_macro_running(delay_end_at)

        return True, current_line_index

    _wait_until_while_macro_running(delay_end_at)
    return True, current_line_index


def _get_link_skill_readiness(
    link_skill: LinkSkill,
    skill_timers: dict[str, float],
) -> tuple[list[str], float]:
    """연계스킬 타이머 기준 사용 가능 목록과 다음 준비 대기 반환"""

    # 연계스킬 자체 발동 이력 추적
    now: float = time.perf_counter()
    cooltime_reduction: float = app_state.macro.current_cooltime_reduction
    extra_wait_ms: int = app_state.macro.current_cooltime_extra_wait
    skill_registry = app_state.macro.current_server.skill_registry

    ready_skill_ids: list[str] = []
    minimum_wait_ms: int | None = None
    for skill_id in link_skill.skills:
        ready_delay_ms: int = (
            round(
                skill_registry.get(skill_id).cooltime * (100 - cooltime_reduction) * 10
            )
            + extra_wait_ms
        )
        started_at: float | None = skill_timers.get(skill_id)

        # 미사용이거나 쿨타임과 추가 대기 경과 시 사용 가능 후보로 포함
        if started_at is None:
            ready_skill_ids.append(skill_id)
            continue

        elapsed_ms: int = round((now - started_at) * 1000)
        remaining_ms: int = ready_delay_ms - elapsed_ms
        if remaining_ms <= 0:
            ready_skill_ids.append(skill_id)
            continue

        if minimum_wait_ms is None or remaining_ms < minimum_wait_ms:
            minimum_wait_ms = remaining_ms

    if ready_skill_ids:
        return ready_skill_ids, 0.0

    wait_seconds: float = (
        minimum_wait_ms * 0.001 if minimum_wait_ms is not None else 0.0
    )
    return ready_skill_ids, wait_seconds


def _is_manual_link_trigger_pressed(session: ManualLinkSession) -> bool:
    """수동 연계를 시작한 최초 단축키 입력의 유지 여부 반환"""

    return (
        session.trigger_key in pressed_keys
        and pressed_key_started_at.get(session.trigger_key.key_id)
        == session.trigger_pressed_at
    )


def _wait_for_manual_link_hold(session: ManualLinkSession) -> bool:
    """최초 입력이 딜레이 동안 유지되면 홀드 상태로 전환"""

    while not session.stop_event.is_set():
        if not _is_manual_link_trigger_pressed(session):
            return False

        remaining_seconds: float = session.hold_transition_at - time.perf_counter()
        if remaining_seconds <= 0.0:
            session.is_hold = True
            return True

        time.sleep(min(remaining_seconds, MACRO_SLEEP_POLL_SECONDS))

    return False


def _wait_for_manual_link_cooldown(
    session: ManualLinkSession,
    wait_seconds: float,
) -> None:
    """홀드 중지 상태를 확인하며 다음 스킬 준비까지 대기"""

    end_at: float = time.perf_counter() + wait_seconds
    while not session.stop_event.is_set():
        if not _is_manual_link_trigger_pressed(session):
            session.stop_event.set()
            return

        remaining_seconds: float = end_at - time.perf_counter()
        if remaining_seconds <= 0.0:
            return

        time.sleep(min(remaining_seconds, MACRO_SLEEP_POLL_SECONDS))


def _run_manual_link_cycle(
    session: ManualLinkSession,
    skills_to_press: list[str],
    skill_ref_map: dict[str, EquippedSkillRef],
    skill_timers: dict[str, float],
    kbd_controller: keyboard.Controller,
    mouse_controller: mouse.Controller,
) -> bool:
    """현재 연계 입력 방식 그대로 한 사이클 실행"""

    current_line_index: int = 0

    try:
        if not skills_to_press:
            return True

        app_state.macro.next_skill_input_at = time.perf_counter()

        # 연계에 등록된 순서대로 스킬 입력 진행
        for index, skill_id in enumerate(skills_to_press):
            if session.stop_event.is_set():
                return False

            skill_ref: EquippedSkillRef = skill_ref_map[skill_id]

            # 쿨타임 동기화 옵션 시 입력 직전 연계 자체 타이머 갱신
            if session.link_skill.remember_state:
                skill_timers[skill_id] = time.perf_counter()

            current_line_index, skill_input_at = _press_skill_keys(
                kbd_controller,
                mouse_controller,
                skill_ref,
                current_line_index=current_line_index,
            )
            skill_used_at: float = time.perf_counter()

            # 동기화 OFF 홀드의 현재 실행 주기 전용 쿨타임 기록
            if not session.link_skill.remember_state:
                skill_timers[skill_id] = skill_used_at

            app_state.macro.last_skill_input_at = skill_input_at
            app_state.macro.next_skill_input_at = (
                skill_used_at + session.delay_seconds
                if index + 1 < len(skills_to_press)
                else None
            )

            time.sleep(session.delay_seconds)

        return True
    finally:
        # 매 사이클 종료 후 기존 수동 연계와 동일한 1줄 상태 복구
        _restore_first_line_state(
            kbd_controller,
            mouse_controller,
            current_line_index,
        )


def use_link_skill(session: ManualLinkSession) -> None:
    """연계스킬 사용 함수"""

    global active_manual_link_session, is_input_sequence_running

    kbd_controller: keyboard.Controller = keyboard.Controller()
    mouse_controller: mouse.Controller = mouse.Controller()
    link_skill: LinkSkill = session.link_skill

    try:
        skill_ref_map: dict[str, EquippedSkillRef] = (
            app_state.macro.current_preset.skills.get_placed_skill_ref_map(
                app_state.macro.current_server
            )
        )

        if not all(skill_id in skill_ref_map for skill_id in link_skill.skills):
            app_state.macro.has_pending_link_skill_unavailable_notice = True
            return

        # 쿨타임 동기화 옵션 시 연계스킬 타이머 기준으로 필터링
        if link_skill.remember_state:
            skill_timers: dict[str, float] = link_skill.skill_timers
            skills_to_press, _wait_seconds = _get_link_skill_readiness(
                link_skill,
                skill_timers,
            )
        else:
            skill_timers = {}
            skills_to_press = list(link_skill.skills)

        # 최초 한 사이클은 기존 수동 연계와 동일한 목록과 순서로 실행
        if not _run_manual_link_cycle(
            session,
            skills_to_press,
            skill_ref_map,
            skill_timers,
            kbd_controller,
            mouse_controller,
        ):
            return

        if not _wait_for_manual_link_hold(session):
            return

        # 홀드 중에는 준비된 연계 스킬만 현재 연계 순서대로 반복 실행
        while not session.stop_event.is_set():
            skills_to_press, wait_seconds = _get_link_skill_readiness(
                link_skill,
                skill_timers,
            )
            if skills_to_press:
                if not _run_manual_link_cycle(
                    session,
                    skills_to_press,
                    skill_ref_map,
                    skill_timers,
                    kbd_controller,
                    mouse_controller,
                ):
                    return
                continue

            if wait_seconds <= 0.0:
                return

            _wait_for_manual_link_cooldown(
                session,
                wait_seconds,
            )
    finally:
        if session.stop_event.is_set():
            app_state.macro.next_skill_input_at = None

        with manual_link_session_lock:
            if active_manual_link_session is session:
                active_manual_link_session = None

            # 연계 입력 종료 후 입력 점유 상태 해제
            is_input_sequence_running = False


def build_task_list(show_info: bool = False) -> float:
    """task_list에 사용할 스킬 추가. task_list가 비어있으면 다음 스킬 준비까지 남은 시간(초)을 반환, 아니면 0.0 반환"""

    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )
    ready_delays_ms: dict[EquippedSkillRef, int] = (
        _build_runtime_skill_ready_delays_ms()
    )
    now: float = time.perf_counter()

    # 쿨타임과 추가 대기 완료 스킬 재준비
    for skill_ref in placed_refs:
        if skill_ref in app_state.macro.prepared_skills:
            continue

        started_at: float = app_state.macro.skill_cooltime_timers[skill_ref]
        elapsed_ms: int = round((now - started_at) * 1000)
        if elapsed_ms >= ready_delays_ms[skill_ref]:
            app_state.macro.prepared_skills.add(skill_ref)

    next_task: tuple[EquippedSkillRef, ...] = take_next_task(
        preset=app_state.macro.current_preset,
        skills_info=app_state.macro.current_preset.usage_settings,
        prepared_skills=app_state.macro.prepared_skills,
        auto_link_skill_groups=tuple(
            tuple(link_skill) for link_skill in app_state.macro.using_link_skills
        ),
        skill_sequence=tuple(app_state.macro.skill_sequence),
    )
    app_state.macro.task_list.extend(next_task)

    if DEBUG_PRINT_INFO and show_info:
        print_macro_info(brief=False)

    if app_state.macro.task_list:
        return 0.0

    # 모든 스킬이 쿨타임 중인 경우, 가장 빨리 준비되는 스킬까지 남은 시간 반환
    remaining_times_ms: list[int] = [
        ready_delays_ms[skill_ref]
        - round((now - app_state.macro.skill_cooltime_timers[skill_ref]) * 1000)
        for skill_ref in placed_refs
        if skill_ref not in app_state.macro.prepared_skills
    ]

    return max(0, min(remaining_times_ms)) * 0.001 if remaining_times_ms else 0.0


def build_preview_task_list() -> tuple[EquippedSkillRef, ...]:
    """프리뷰용 task_list 계산"""

    # 프리뷰 전용 상태 스냅샷 구성
    preview_state: PreviewTaskState = _build_preview_task_state()
    while True:
        next_task: tuple[EquippedSkillRef, ...] = take_next_task(
            preset=app_state.macro.current_preset,
            skills_info=app_state.macro.current_preset.usage_settings,
            prepared_skills=preview_state.prepared_skills,
            auto_link_skill_groups=tuple(
                tuple(link_skill) for link_skill in preview_state.using_link_skills
            ),
            skill_sequence=tuple(preview_state.skill_sequence),
        )
        if not next_task:
            break

        preview_state.task_list.extend(next_task)

    return tuple(preview_state.task_list)


def _build_preview_task_state() -> PreviewTaskState:
    """프리뷰 계산용 상태 스냅샷 구성"""

    # 실행 중에는 실제 런타임 상태를 복사해 프리뷰에 반영
    if app_state.macro.is_running:
        return PreviewTaskState(
            prepared_skills=app_state.macro.prepared_skills.copy(),
            task_list=app_state.macro.task_list.copy(),
            skill_sequence=app_state.macro.skill_sequence.copy(),
            using_link_skills=[
                link_skill.copy() for link_skill in app_state.macro.using_link_skills
            ],
        )

    # 미실행 중에는 프리뷰 전용 상태를 별도로 구성
    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )
    using_link_skills: list[list[EquippedSkillRef]] = [
        list(link_skill_group)
        for link_skill_group in build_auto_link_skill_groups(
            server_spec=app_state.macro.current_server,
            preset=app_state.macro.current_preset,
        )
    ]

    prepared_skills: set[EquippedSkillRef]
    if (
        app_state.macro.current_preset.settings.remember_previous_state
        and _has_cooltime_state(placed_refs)
    ):
        prepared_skills = _collect_ready_cooltime_skills(placed_refs)
        if prepared_skills == set(placed_refs):
            app_state.macro.clear_cooltime_state()

    else:
        prepared_skills = set(placed_refs)

    return PreviewTaskState(
        prepared_skills=prepared_skills,
        task_list=[],
        skill_sequence=list(
            build_priority_skill_sequence(
                server_spec=app_state.macro.current_server,
                preset=app_state.macro.current_preset,
                skills_info=app_state.macro.current_preset.usage_settings,
            )
        ),
        using_link_skills=using_link_skills,
    )


def print_macro_info(brief: bool = False) -> None:
    """디버깅용 매크로 상태 출력"""

    print()
    print("테스크 리스트:", app_state.macro.task_list)
    print("준비된 스킬 리스트:", app_state.macro.prepared_skills)

    if brief:
        return

    print("스킬 정렬 순서:", app_state.macro.skill_sequence)
    print("연계스킬 스킬 리스트:", app_state.macro.using_link_skills)
