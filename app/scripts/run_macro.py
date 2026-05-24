from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock, Thread
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
    LinkUseType,
    SkillTask,
    SkillUsageSetting,
)
from app.scripts.registry.key_registry import KeyRegistry, KeySpec

DEBUG_PRINT_INFO = False
ATTACK_PAUSE_BUFFER_SECONDS = 0.05
ATTACK_PAUSE_POLL_SECONDS = 0.01
LINK_CANCEL_BEFORE_SKILL_SECONDS = 0.1
LINK_CANCEL_AFTER_SKILL_SECONDS = 0.1
LINK_CANCEL_SPAM_PRESS_SECONDS = 0.05
LINK_CANCEL_SPAM_RELEASE_SECONDS = 0.05
LINK_CANCEL_KEY_SPEC = KeySpec.from_key("Space", "link_cancel_space", Key.space)


# 전역 입력 상태 추적
pressed_keys: set[KeySpec] = set()
pressed_key_started_at: dict[str, float] = {}
handled_key_ids: set[str] = set()
has_user_activity = False

# 프로그램 주입 입력 추적 상태
injected_press_counts: dict[str, int] = {}
injected_release_counts: dict[str, int] = {}
injected_input_lock: Lock = Lock()

# 연계 캔슬 Space 연타 상태
link_cancel_spam_until: float = 0.0
link_cancel_spam_run_id: int | None = None
is_link_cancel_spam_running: bool = False
link_cancel_spam_lock: Lock = Lock()


@dataclass(slots=True)
class PreviewTaskState:
    """프리뷰 계산용 상태 묶음"""

    prepared_skills: set[EquippedSkillRef]
    task_list: list[SkillTask]
    skill_sequence: list[EquippedSkillRef]
    using_link_skills: list[list[SkillTask]]
    link_skills_requirements: list[list[EquippedSkillRef]]


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


def _consume_injected_key_event(
    key: Key | KeyCode,
    counters: dict[str, int],
) -> bool:
    """프로그램이 등록한 입력인지 확인 후 소모"""

    # 키 아이디 변환 불가 입력은 사용자 입력으로 처리
    if key == LINK_CANCEL_KEY_SPEC.value:
        key_id: str | None = LINK_CANCEL_KEY_SPEC.key_id
    else:
        key_spec: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(key)
        key_id = key_spec.key_id if key_spec is not None else None

    if key_id is None:
        return False

    # 등록된 주입 입력 카운트 차감
    with injected_input_lock:
        remaining_count: int = counters.get(key_id, 0)
        if remaining_count == 0:
            return False

        if remaining_count == 1:
            del counters[key_id]

        else:
            counters[key_id] = remaining_count - 1

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

    # 프로그램이 보낸 키 입력은 AFK 갱신 대상에서 제외
    if _consume_injected_key_event(key, injected_press_counts):
        return

    # 잠수 감지는 인식 불가 키도 사용자 입력으로 인정
    has_user_activity = True

    # 모디파이어 조합 등으로 변형된 키도 동일 KeySpec으로 정규화
    key_spec: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(key)
    if key_spec is not None:
        # 최초 입력 시점 기록 및 이전 처리 상태 초기화
        if key_spec not in pressed_keys:
            pressed_key_started_at[key_spec.key_id] = time.perf_counter()
            handled_key_ids.discard(key_spec.key_id)

        pressed_keys.add(key_spec)


def on_release(key: Key | KeyCode | None) -> None:
    """키가 떼어졌을 때 호출되는 함수"""

    global pressed_keys, pressed_key_started_at, handled_key_ids

    if key is None:
        return

    # 프로그램이 보낸 키 해제 입력은 눌림 상태 추적에서 제외
    if _consume_injected_key_event(key, injected_release_counts):
        return

    key_spec: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(key)
    if key_spec is not None:
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

    global pressed_keys, pressed_key_started_at, handled_key_ids

    # 지원하는 마우스 버튼 기준 KeySpec 정규화
    key_spec: KeySpec | None = KeyRegistry.pynput_mouse_to_keyspec(button)
    if key_spec is None:
        return

    # 마우스 버튼 press 상태 등록
    if pressed:
        if key_spec not in pressed_keys:
            pressed_key_started_at[key_spec.key_id] = time.perf_counter()
            handled_key_ids.discard(key_spec.key_id)

        pressed_keys.add(key_spec)
        return

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


def checking_kb_thread() -> NoReturn:
    """키보드 입력 감지 쓰레드"""

    global has_user_activity, handled_key_ids

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
        is_start_key_ready: bool = (
            is_key_held(start_key, key_hold_seconds)
            and start_key.key_id not in handled_key_ids
        )

        # 매크로 시작/중지
        if is_start_key_ready:
            handled_key_ids.add(start_key.key_id)

            # 현재 중이면 즉시 종료 상태 전환
            if app_state.macro.is_running:
                app_state.macro.is_running = False

                # 종료 입력 직후 1줄 종료 상태 즉시 복구
                _restore_first_line_state()

            # 현재 중이 아니면 새 실행 시작
            else:
                app_state.macro.is_running = True

                # 매크로 번호 증가
                app_state.macro.run_id += 1

                # 매크로 쓰레드 시작
                Thread(
                    target=running_macro_thread,
                    args=[app_state.macro.run_id],
                    daemon=True,
                ).start()

            # 매크로 실행/중지 이후에는 잠시 키 입력 무시
            time.sleep(0.5 * config.macro.SLEEP_COEFFICIENT_NORMAL)

            # 다음 루프로 넘어감
            continue

        # 연계스킬 사용
        for link_skill in app_state.macro.current_preset.link_skills:
            # 단축키가 설정된 연계스킬만 검사
            if link_skill.key_type == LinkKeyType.OFF or link_skill.key is None:
                continue

            # 연계스킬 키가 눌렸다면
            link_key: KeySpec = KeyRegistry.get(link_skill.key)
            if (
                is_key_held(link_key, key_hold_seconds)
                and link_key.key_id not in handled_key_ids
            ):
                handled_key_ids.add(link_key.key_id)

                # 연계스킬 쓰레드 시작
                Thread(
                    target=use_link_skill,
                    args=[link_skill, app_state.macro.run_id],
                    daemon=True,
                ).start()
                break

        # 연계스킬이 실행되지 않았으면 0.05초 슬립
        else:
            time.sleep(0.05 * config.macro.SLEEP_COEFFICIENT_NORMAL)
            continue

        # 연계스킬이 실행되었으면 0.25초 슬립
        time.sleep(0.25 * config.macro.SLEEP_COEFFICIENT_NORMAL)


def running_macro_thread(run_id: int) -> None:
    """
    매크로 메인 쓰레드
    시뮬레이션과 약간의 오차가 있지만 무시할만 함 (나중에 개선 예정)
    """

    init_macro()

    # 매크로 클릭 쓰레드
    if app_state.macro.current_use_default_attack:
        # 첫 스킬 입력 전에 평타가 먼저 나가지 않도록 시작 직후 보호 구간 선예약
        _pause_attack_for(_get_attack_hold_seconds())

        Thread(
            target=clicking_mouse_thread,
            args=[app_state.macro.run_id],
            daemon=True,
        ).start()

    while app_state.macro.is_running and app_state.macro.run_id == run_id:
        # taskList에 사용 가능한 스킬 추가
        wait_seconds: float = 0.0
        if not app_state.macro.task_list:
            wait_seconds = build_task_list(show_info=DEBUG_PRINT_INFO)

        # 다음 스킬이 아직 멀면 평타를 유지한 채 직전 보호 구간까지만 대기
        if not app_state.macro.task_list and wait_seconds > 0.0:
            attack_hold_seconds: float = _get_attack_hold_seconds()

            if wait_seconds > attack_hold_seconds:
                time.sleep(
                    (wait_seconds - attack_hold_seconds)
                    * config.macro.SLEEP_COEFFICIENT_UNIT
                )
                continue

            # 다음 스킬 임박 구간 동안 평타 중지 예약
            _pause_attack_for(wait_seconds + ATTACK_PAUSE_BUFFER_SECONDS)

        # 즉시 사용할 스킬이 있으면 평타 스레드 선차단
        if app_state.macro.task_list:
            _pause_attack_for(_get_attack_hold_seconds())

        # 스킬 사용하고 사용 여부 리턴
        is_used_skill: bool = use_skill(run_id=app_state.macro.run_id)

        # 잠수면 매크로 중지
        if (
            config.macro.is_afk_enabled
            and time.time() - app_state.macro.afk_started_time >= 10
        ):
            # UI 스레드 알림 표시용 잠수 종료 상태 기록
            app_state.macro.has_pending_afk_notice = True
            app_state.macro.is_running = False

        if not is_used_skill:
            time.sleep(wait_seconds * config.macro.SLEEP_COEFFICIENT_UNIT)

    # 현재 실행 주기 종료 시 1줄 종료 상태 복구
    if app_state.macro.run_id == run_id:
        _settle_cooltime_state_after_stop()
        _restore_first_line_state()


def clicking_mouse_thread(run_id: int) -> None:
    """마우스 클릭 쓰레드"""

    mouse_controller: mouse.Controller = mouse.Controller()

    while app_state.macro.is_running and app_state.macro.run_id == run_id:
        # 스킬 입력 보호 구간에는 평타 클릭 보류
        remaining_pause_seconds: float = (
            app_state.macro.attack_pause_until - time.perf_counter()
        )
        if remaining_pause_seconds > 0.0:
            time.sleep(min(remaining_pause_seconds, ATTACK_PAUSE_POLL_SECONDS))
            continue

        mouse_controller.click(mouse.Button.left)
        time.sleep(0.1)


def _get_attack_hold_seconds() -> float:
    """다음 스킬 직전에 평타를 멈출 보호 구간 반환"""

    # 평타 1회 주기와 추가 버퍼를 합친 스킬 선점 구간 계산
    attack_hold_seconds: float = (
        app_state.macro.current_delay * 0.001
    ) + ATTACK_PAUSE_BUFFER_SECONDS
    return attack_hold_seconds


def _pause_attack_for(duration_seconds: float) -> None:
    """지정 시간 동안 평타를 중지하도록 예약"""

    if duration_seconds <= 0.0:
        return

    # 이미 더 긴 중지 예약이 있으면 기존 종료 시각 유지
    pause_until: float = time.perf_counter() + duration_seconds
    app_state.macro.attack_pause_until = max(
        app_state.macro.attack_pause_until,
        pause_until,
    )


def _restore_first_line_state() -> None:
    """현재 줄 상태를 1줄 종료 상태로 복구"""

    # 이미 1줄이면 추가 입력 없이 종료
    if app_state.macro.current_line_index == 0:
        return

    swap_key: KeySpec = app_state.macro.current_swap_key

    # 종료 복귀용 스왑 입력 등록
    kbd_controller: keyboard.Controller = keyboard.Controller()
    _press_keyboard_key(kbd_controller, swap_key)
    app_state.macro.current_line_index = 0


def _press_keyboard_key(
    kbd_controller: keyboard.Controller,
    key_spec: KeySpec,
) -> None:
    """키보드 키를 한 번 입력"""

    _register_injected_key_event(key_spec)
    keyboard_key: Key | KeyCode = cast(Key | KeyCode, key_spec.value)
    kbd_controller.press(keyboard_key)
    kbd_controller.release(keyboard_key)


# 단발 캔슬 입력 경로는 필요할 때 다시 연결할 수 있도록 유지
def _hold_link_cancel_key(
    kbd_controller: keyboard.Controller,
    hold_seconds: float,
) -> None:
    """연계 캔슬 키를 지정 시간 동안 입력"""

    _register_injected_key_event(LINK_CANCEL_KEY_SPEC)
    keyboard_key: Key = cast(Key, LINK_CANCEL_KEY_SPEC.value)
    kbd_controller.press(keyboard_key)
    time.sleep(hold_seconds)
    kbd_controller.release(keyboard_key)


def _link_cancel_spam_thread(run_id: int) -> None:
    """예약된 시각까지 연계 캔슬 키를 반복 입력"""

    global is_link_cancel_spam_running
    global link_cancel_spam_run_id

    kbd_controller: keyboard.Controller = keyboard.Controller()
    keyboard_key: Key = cast(Key, LINK_CANCEL_KEY_SPEC.value)

    while True:
        now: float = time.perf_counter()
        with link_cancel_spam_lock:
            should_stop: bool = (
                app_state.macro.run_id != run_id
                or link_cancel_spam_run_id != run_id
                or now >= link_cancel_spam_until
            )

            if should_stop:
                if link_cancel_spam_run_id == run_id:
                    is_link_cancel_spam_running = False
                    link_cancel_spam_run_id = None
                return

        _register_injected_key_event(LINK_CANCEL_KEY_SPEC)
        kbd_controller.press(keyboard_key)
        time.sleep(LINK_CANCEL_SPAM_PRESS_SECONDS)
        kbd_controller.release(keyboard_key)
        time.sleep(LINK_CANCEL_SPAM_RELEASE_SECONDS)


def _schedule_link_cancel_spam_until(run_id: int, end_at: float) -> None:
    """연계 캔슬 키 연타 종료 시각 예약"""

    global is_link_cancel_spam_running
    global link_cancel_spam_run_id
    global link_cancel_spam_until

    should_start_thread: bool = False
    with link_cancel_spam_lock:
        if is_link_cancel_spam_running and link_cancel_spam_run_id == run_id:
            link_cancel_spam_until = max(link_cancel_spam_until, end_at)
            return

        link_cancel_spam_run_id = run_id
        link_cancel_spam_until = end_at
        is_link_cancel_spam_running = True
        should_start_thread = True

    if should_start_thread:
        Thread(
            target=_link_cancel_spam_thread,
            args=[run_id],
            daemon=True,
        ).start()


def _schedule_link_cancel_spam_for_skill(
    last_skill_input_at: float | None,
    run_id: int,
) -> None:
    """캔슬 스킬 직전 딜레이부터 직후 딜레이 끝까지 연타 예약"""

    now: float = time.perf_counter()
    skill_delay_seconds: float = _get_skill_delay_seconds()
    if last_skill_input_at is None:
        expected_skill_input_at: float = now
    else:
        expected_skill_input_at = max(now, last_skill_input_at + skill_delay_seconds)

    _schedule_link_cancel_spam_until(
        run_id,
        expected_skill_input_at + skill_delay_seconds,
    )


def _press_skill_keys(
    kbd_controller: keyboard.Controller,
    skill_ref: EquippedSkillRef,
    run_id: int,
    require_running: bool,
) -> bool:
    """줄 상태에 맞는 입력 수행"""

    if app_state.macro.run_id != run_id:
        return False

    if require_running and not app_state.macro.is_running:
        return False

    # 목표 줄과 현재 줄이 다르면 스왑 입력 수행
    if skill_ref.line_index != app_state.macro.current_line_index:
        swap_key: KeySpec = app_state.macro.current_swap_key

        # 프로그램 주입 스왑 입력 등록
        _press_keyboard_key(kbd_controller, swap_key)

        app_state.macro.current_line_index = skill_ref.line_index

    # 현재 세로줄 공용키 기준 스킬 입력 키 조회
    skill_key: KeySpec = KeyRegistry.get(
        app_state.macro.current_preset.skills.skill_keys[skill_ref.scroll_index]
    )

    # 프로그램 주입 스킬 입력 등록
    _press_keyboard_key(kbd_controller, skill_key)
    return True


def _get_skill_delay_seconds() -> float:
    """스킬 입력 간격을 초 단위로 반환"""

    return app_state.macro.current_delay * 0.001 * config.macro.SLEEP_COEFFICIENT_NORMAL


def _wait_before_skill_input(
    use_cancel: bool,
    run_id: int,
    require_running: bool,
) -> bool:
    """다음 스킬 입력 전 필요한 대기와 캔슬 선입력을 수행"""

    last_skill_input_at: float | None = app_state.macro.last_skill_input_at
    if use_cancel:
        _schedule_link_cancel_spam_for_skill(last_skill_input_at, run_id)

    if last_skill_input_at is not None:
        elapsed_seconds: float = time.perf_counter() - last_skill_input_at
        wait_seconds: float = max(
            0.0,
            _get_skill_delay_seconds() - elapsed_seconds,
        )
        if wait_seconds > 0.0:
            time.sleep(wait_seconds)

    if app_state.macro.run_id != run_id:
        return False

    if require_running and not app_state.macro.is_running:
        return False

    return True


def _press_skill_task(
    kbd_controller: keyboard.Controller,
    skill_task: SkillTask,
    run_id: int,
    require_running: bool,
) -> bool:
    """스킬 입력 정보에 맞춰 실제 키 입력 수행"""

    if not _wait_before_skill_input(
        skill_task.use_cancel,
        run_id,
        require_running,
    ):
        return False

    if not _press_skill_keys(
        kbd_controller,
        skill_task.skill_ref,
        run_id,
        require_running=require_running,
    ):
        return False

    app_state.macro.last_skill_input_at = time.perf_counter()

    return True


def _collect_priority_skill_sequence() -> list[EquippedSkillRef]:
    """우선순위 기준 스킬 순서 반환"""

    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )
    skill_sequence: list[EquippedSkillRef] = []

    # 현재 하단 슬롯에 실제 배치된 스킬만 우선순위 후보로 제한
    for target_priority in range(1, len(placed_refs) + 1):
        for skill_ref in placed_refs:
            skill_id: str = app_state.macro.current_preset.skills.get_placed_skill_id(
                skill_ref
            )
            setting: SkillUsageSetting = app_state.macro.current_preset.usage_settings[
                skill_id
            ]

            if setting.priority != target_priority:
                continue

            # 배치되지 않은 숨은 설정값은 무시하고 실제 슬롯 순서만 반영
            skill_sequence.append(skill_ref)

    for skill_ref in placed_refs:
        if skill_ref not in skill_sequence:
            skill_sequence.append(skill_ref)

    return skill_sequence


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
    cooltimes: dict[EquippedSkillRef, float] = {
        skill_ref: app_state.macro.current_server.skill_registry.get(
            app_state.macro.current_preset.skills.get_placed_skill_id(skill_ref)
        ).cooltime
        * (100 - app_state.macro.current_cooltime_reduction)
        / 100.0
        for skill_ref in placed_refs
    }

    # 쿨타임이 지난 스킬을 준비 완료 상태로 반영
    for skill_ref in placed_refs:
        if skill_ref in prepared_skills:
            continue

        started_at: float = app_state.macro.skill_cooltime_timers[skill_ref]
        if (now - started_at) >= cooltimes[skill_ref]:
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
        app_state.macro.prepared_skills
        | {skill_task.skill_ref for skill_task in app_state.macro.task_list}
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
    app_state.macro.current_line_index = 0
    app_state.macro.last_skill_input_at = None
    app_state.macro.skill_sequence = _collect_priority_skill_sequence()
    app_state.macro.using_link_skills.clear()
    app_state.macro.attack_pause_until = 0.0

    skill_ref_map: dict[str, EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_ref_map(
            app_state.macro.current_server
        )
    )

    # 자동 연계의 장착 참조 변환
    for link_skill in app_state.macro.current_preset.link_skills:
        if link_skill.use_type != LinkUseType.AUTO:
            continue

        if not all(skill_id in skill_ref_map for skill_id in link_skill.skills):
            continue

        link_skill.sync_skill_cancels()
        app_state.macro.using_link_skills.append(
            [
                SkillTask(skill_ref_map[skill_id], link_skill.skill_cancels[index])
                for index, skill_id in enumerate(link_skill.skills)
            ]
        )

    app_state.macro.link_skills_requirements = [
        [skill_task.skill_ref for skill_task in link_skill]
        for link_skill in app_state.macro.using_link_skills
    ]
    app_state.macro.task_list.clear()
    _restore_or_reset_cooltime_state(placed_refs)


def use_skill(run_id: int) -> bool:
    """스킬 사용 함수"""

    if not app_state.macro.task_list:
        return False

    # 스킬 입력 직전과 후속 딜레이 동안 평타 끼어들기 차단
    _pause_attack_for(_get_attack_hold_seconds())

    kbd_controller: keyboard.Controller = keyboard.Controller()
    skill_task: SkillTask = app_state.macro.task_list.pop(0)
    skill_ref: EquippedSkillRef = skill_task.skill_ref

    if not _press_skill_task(
        kbd_controller,
        skill_task,
        run_id,
        require_running=True,
    ):
        return False

    app_state.macro.skill_cooltime_timers[skill_ref] = (
        app_state.macro.last_skill_input_at or time.perf_counter()
    )

    # 옵션 활성화 시 스킬 사용 후 1번 줄로 복귀
    # 다음 스킬 입력 타이밍 계산이 남은 딜레이를 이어서 처리한다.
    if (
        app_state.macro.current_always_return_to_first_line
        and app_state.macro.current_line_index != 0
    ):
        time.sleep(_get_skill_delay_seconds() * 0.5)

        swap_key: KeySpec = app_state.macro.current_swap_key
        _press_keyboard_key(kbd_controller, swap_key)

        app_state.macro.current_line_index = 0
    return True


def _collect_ready_link_skill_indices(link_skill: LinkSkill) -> list[int]:
    """연계스킬 타이머 기준 사용 가능 스킬 인덱스 목록 반환"""

    # 연계스킬 자체 발동 이력 추적
    now: float = time.perf_counter()
    cooltime_reduction: float = app_state.macro.current_cooltime_reduction
    skill_registry = app_state.macro.current_server.skill_registry

    ready_skill_indices: list[int] = []
    for index, skill_id in enumerate(link_skill.skills):
        cooltime: float = (
            skill_registry.get(skill_id).cooltime * (100 - cooltime_reduction) / 100.0
        )
        started_at: float | None = link_skill.skill_timers.get(skill_id)

        # 미사용이거나 쿨타임 경과 시 사용 가능 후보로 포함
        if started_at is None or (now - started_at) >= cooltime:
            ready_skill_indices.append(index)

    return ready_skill_indices


def _wait_before_link_skill_input(
    last_skill_input_at: float | None,
    use_cancel: bool,
    run_id: int,
) -> bool:
    """수동 연계의 다음 스킬 입력 전 대기와 캔슬 선입력을 수행"""

    if use_cancel:
        _schedule_link_cancel_spam_for_skill(last_skill_input_at, run_id)

    if last_skill_input_at is not None:
        elapsed_seconds: float = time.perf_counter() - last_skill_input_at
        wait_seconds: float = max(
            0.0,
            _get_skill_delay_seconds() - elapsed_seconds,
        )
        if wait_seconds > 0.0:
            time.sleep(wait_seconds)

    if app_state.macro.run_id != run_id:
        return False

    return True


def use_link_skill(link_skill: LinkSkill, run_id: int) -> None:
    """연계스킬 사용 함수"""

    skill_ref_map: dict[str, EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_ref_map(
            app_state.macro.current_server
        )
    )

    if not all(skill_id in skill_ref_map for skill_id in link_skill.skills):
        return

    # 쿨타임 동기화 옵션 시 연계스킬 타이머 기준으로 필터링
    link_skill.sync_skill_cancels()

    if link_skill.remember_state:
        skill_indices_to_press: list[int] = _collect_ready_link_skill_indices(
            link_skill
        )
    else:
        skill_indices_to_press = list(range(len(link_skill.skills)))

    # 입력할 스킬이 없으면 상태를 건드리지 않고 종료
    if not skill_indices_to_press:
        return

    # 연계 입력 전체 구간 동안 평타 클릭 차단
    link_skill_pause_seconds: float = (
        len(skill_indices_to_press) * app_state.macro.current_delay * 0.001
    ) + ATTACK_PAUSE_BUFFER_SECONDS
    _pause_attack_for(link_skill_pause_seconds)

    # 수동 연계 시작 기준 1줄 상태 초기화
    app_state.macro.current_line_index = 0

    kbd_controller: keyboard.Controller = keyboard.Controller()
    last_skill_input_at: float | None = None

    # 연계에 등록된 순서대로 스킬 입력 진행
    for skill_index in skill_indices_to_press:
        skill_id: str = link_skill.skills[skill_index]
        skill_ref: EquippedSkillRef = skill_ref_map[skill_id]
        use_cancel: bool = link_skill.skill_cancels[skill_index]

        if not _wait_before_link_skill_input(
            last_skill_input_at,
            use_cancel,
            run_id,
        ):
            return

        # 쿨타임 동기화 옵션 시 입력 직전 연계 자체 타이머 갱신
        if link_skill.remember_state:
            link_skill.skill_timers[skill_id] = time.perf_counter()

        if not _press_skill_keys(
            kbd_controller,
            skill_ref,
            run_id,
            require_running=False,
        ):
            return

        last_skill_input_at = time.perf_counter()

    if last_skill_input_at is not None:
        remaining_delay_seconds: float = max(
            0.0,
            _get_skill_delay_seconds() - (time.perf_counter() - last_skill_input_at),
        )
        if remaining_delay_seconds > 0.0:
            time.sleep(remaining_delay_seconds)

    if app_state.macro.run_id == run_id:
        _restore_first_line_state()


def _pop_next_regular_task(
    prepared_skills: set[EquippedSkillRef],
    skill_sequence: list[EquippedSkillRef],
    link_skills_requirements: list[list[EquippedSkillRef]],
) -> EquippedSkillRef | None:
    """우선순위 기준 다음 일반 스킬 선택"""

    # 자동 연계에 속한 스킬 참조 집합 구성
    linked_skill_refs: set[EquippedSkillRef] = {
        skill_ref
        for requirements in link_skills_requirements
        for skill_ref in requirements
    }

    # 우선순위 순서대로 사용 가능한 첫 스킬 선택
    for skill_ref in skill_sequence:
        if skill_ref not in prepared_skills:
            continue

        skill_id: str = app_state.macro.current_preset.skills.get_placed_skill_id(
            skill_ref
        )
        setting: SkillUsageSetting = app_state.macro.current_preset.usage_settings[
            skill_id
        ]
        in_link_skill: bool = skill_ref in linked_skill_refs
        can_use: bool = (in_link_skill and setting.use_alone) or (
            not in_link_skill and setting.use_skill
        )
        if not can_use:
            continue

        prepared_skills.discard(skill_ref)
        return skill_ref

    return None


def build_task_list(show_info: bool = False) -> float:
    """task_list에 사용할 스킬 추가. task_list가 비어있으면 다음 스킬 준비까지 남은 시간(초)을 반환, 아니면 0.0 반환"""

    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )
    cooltimes: dict[EquippedSkillRef, float] = {
        skill_ref: app_state.macro.current_server.skill_registry.get(
            app_state.macro.current_preset.skills.get_placed_skill_id(skill_ref)
        ).cooltime
        * (100 - app_state.macro.current_cooltime_reduction)
        / 100.0
        for skill_ref in placed_refs
    }
    now: float = time.perf_counter()

    # 쿨타임 완료 스킬 재준비
    for skill_ref in placed_refs:
        if skill_ref in app_state.macro.prepared_skills:
            continue

        started_at: float = app_state.macro.skill_cooltime_timers[skill_ref]
        if (now - started_at) >= cooltimes[skill_ref]:
            app_state.macro.prepared_skills.add(skill_ref)

    # 우선순위 기준 일반 스킬 1개 선택
    next_regular_skill_ref: EquippedSkillRef | None = _pop_next_regular_task(
        prepared_skills=app_state.macro.prepared_skills,
        skill_sequence=app_state.macro.skill_sequence,
        link_skills_requirements=app_state.macro.link_skills_requirements,
    )
    if next_regular_skill_ref is not None:
        app_state.macro.task_list.append(SkillTask(next_regular_skill_ref))
    else:
        prepared_link_skill_indices: list[int] = get_prepared_link_skill_indices(
            prepared_skills=app_state.macro.prepared_skills,
            link_skills_requirements=app_state.macro.link_skills_requirements,
        )
        if prepared_link_skill_indices:
            for skill_task in app_state.macro.using_link_skills[
                prepared_link_skill_indices[0]
            ]:
                app_state.macro.prepared_skills.discard(skill_task.skill_ref)
                app_state.macro.task_list.append(skill_task)

    if DEBUG_PRINT_INFO and show_info:
        print_macro_info(brief=False)

    if app_state.macro.task_list:
        return 0.0

    # 모든 스킬이 쿨타임 중인 경우, 가장 빨리 준비되는 스킬까지 남은 시간 반환
    remaining_times: list[float] = [
        cooltimes[skill_ref] - (now - app_state.macro.skill_cooltime_timers[skill_ref])
        for skill_ref in placed_refs
        if skill_ref not in app_state.macro.prepared_skills
    ]

    # 약간의 여유 시간을 추가하여 실제 준비 시점과의 오차 완화 (추후 설정 가능하게 개선 예정)
    return max(0.0, min(remaining_times) + 0.2) if remaining_times else 0.0


def build_preview_task_list() -> tuple[EquippedSkillRef, ...]:
    """프리뷰용 task_list 계산"""

    # 프리뷰 전용 상태 스냅샷 구성
    preview_state: PreviewTaskState = _build_preview_task_state()

    # 일반 스킬을 우선순위대로 먼저 추가
    while True:
        next_regular_skill_ref: EquippedSkillRef | None = _pop_next_regular_task(
            prepared_skills=preview_state.prepared_skills,
            skill_sequence=preview_state.skill_sequence,
            link_skills_requirements=preview_state.link_skills_requirements,
        )
        if next_regular_skill_ref is None:
            break

        preview_state.task_list.append(SkillTask(next_regular_skill_ref))

    prepared_link_skill_indices: list[int] = get_prepared_link_skill_indices(
        prepared_skills=preview_state.prepared_skills,
        link_skills_requirements=preview_state.link_skills_requirements,
    )

    # 일반 스킬 후보가 없을 때 자동 연계를 추가
    for prepared_link_skill_index in prepared_link_skill_indices:
        for skill_task in preview_state.using_link_skills[prepared_link_skill_index]:
            preview_state.prepared_skills.discard(skill_task.skill_ref)
            preview_state.task_list.append(skill_task)

    return tuple(skill_task.skill_ref for skill_task in preview_state.task_list)


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
            link_skills_requirements=[
                requirements.copy()
                for requirements in app_state.macro.link_skills_requirements
            ],
        )

    # 미실행 중에는 프리뷰 전용 상태를 별도로 구성
    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )
    skill_ref_map: dict[str, EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_ref_map(
            app_state.macro.current_server
        )
    )
    using_link_skills: list[list[SkillTask]] = []

    # 현재 배치 기준으로 실행 가능한 자동 연계만 프리뷰 대상에 포함
    link_skill: LinkSkill
    for link_skill in app_state.macro.current_preset.link_skills:
        if link_skill.use_type != LinkUseType.AUTO:
            continue

        if not all(skill_id in skill_ref_map for skill_id in link_skill.skills):
            continue

        link_skill.sync_skill_cancels()
        using_link_skills.append(
            [
                SkillTask(skill_ref_map[skill_id], link_skill.skill_cancels[index])
                for index, skill_id in enumerate(link_skill.skills)
            ]
        )

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
        skill_sequence=_collect_priority_skill_sequence(),
        using_link_skills=using_link_skills,
        link_skills_requirements=[
            [skill_task.skill_ref for skill_task in link_skill]
            for link_skill in using_link_skills
        ],
    )


def get_prepared_link_skill_indices(
    prepared_skills: set[EquippedSkillRef],
    link_skills_requirements: list[list[EquippedSkillRef]],
) -> list[int]:
    """준비된 연계스킬 목록 반환"""

    prepared_indices: list[int] = []
    copied_prepared_skills: set[EquippedSkillRef] = prepared_skills.copy()

    for idx, requirements in enumerate(link_skills_requirements):
        if not all(skill_ref in copied_prepared_skills for skill_ref in requirements):
            continue

        for skill_ref in requirements:
            copied_prepared_skills.discard(skill_ref)

        prepared_indices.append(idx)

    return prepared_indices


def print_macro_info(brief: bool = False) -> None:
    """디버깅용 매크로 상태 출력"""

    print()
    print("테스크 리스트:", app_state.macro.task_list)
    print("준비된 스킬 리스트:", app_state.macro.prepared_skills)

    if brief:
        return

    print("스킬 정렬 순서:", app_state.macro.skill_sequence)
    print("연계스킬 스킬 리스트:", app_state.macro.using_link_skills)
    print("연계스킬에 필요한 스킬 리스트:", app_state.macro.link_skills_requirements)
