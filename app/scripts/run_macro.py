from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock, Thread
from typing import NoReturn

from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode

from app.scripts.app_state import app_state
from app.scripts.config import config
from app.scripts.macro_models import (
    EquippedSkillRef,
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    SkillUsageSetting,
)
from app.scripts.registry.key_registry import KeyRegistry, KeySpec

DEBUG_PRINT_INFO = False
ATTACK_PAUSE_BUFFER_SECONDS = 0.05
ATTACK_PAUSE_POLL_SECONDS = 0.01


# 전역 입력 상태 추적
pressed_keys: set[Key | KeyCode] = set()
any_key_pressed = False

# 프로그램 주입 입력 추적 상태
injected_press_counts: dict[str, int] = {}
injected_release_counts: dict[str, int] = {}
injected_input_lock: Lock = Lock()


@dataclass(slots=True)
class PreviewTaskState:
    """프리뷰 계산용 상태 묶음"""

    prepared_skills: set[EquippedSkillRef]
    task_list: list[EquippedSkillRef]
    preview_line_index: int
    skill_sequence: list[EquippedSkillRef]
    using_link_skills: list[list[EquippedSkillRef]]
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
    key_spec: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(key)
    if key_spec is None:
        return False

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

    global pressed_keys, any_key_pressed

    if key is None:
        return

    # 프로그램이 보낸 키 입력은 AFK 갱신 대상에서 제외
    if _consume_injected_key_event(key, injected_press_counts):
        return

    pressed_keys.add(key)
    any_key_pressed = True


def on_release(key: Key | KeyCode | None) -> None:
    """키가 떼어졌을 때 호출되는 함수"""

    global pressed_keys

    if key is None:
        return

    # 프로그램이 보낸 키 해제 입력은 눌림 상태 추적에서 제외
    if _consume_injected_key_event(key, injected_release_counts):
        return

    pressed_keys.discard(key)


def is_key_pressed(key: KeySpec) -> bool:
    """특정 키가 눌려있는지 확인"""

    global pressed_keys

    return key.value in pressed_keys


def checking_kb_thread() -> NoReturn:
    """키보드 입력 감지 쓰레드"""

    global any_key_pressed

    # 키보드 리스너 시작
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    while True:
        # 다른 키 설정 중일 때는 패스
        if app_state.ui.is_setting_key:
            time.sleep(0.1)
            continue

        # 매크로 실행중일 때 어떤 키보드 입력이 있으면 잠수 시간 초기화
        if app_state.macro.is_running and any_key_pressed:
            app_state.macro.afk_started_time = time.time()

            # 플래그 리셋
            any_key_pressed = False

        # 매크로 시작/중지
        if is_key_pressed(app_state.macro.current_start_key):
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
            if is_key_pressed(link_key):
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
            app_state.macro.is_running = False

        if not is_used_skill:
            time.sleep(wait_seconds * config.macro.SLEEP_COEFFICIENT_UNIT)

    # 현재 실행 주기 종료 시 1줄 종료 상태 복구
    if app_state.macro.run_id == run_id:
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
    _register_injected_key_event(swap_key)
    kbd_controller.press(swap_key.value)
    kbd_controller.release(swap_key.value)
    app_state.macro.current_line_index = 0


def _press_skill_keys(
    kbd_controller: keyboard.Controller,
    skill_ref: EquippedSkillRef,
    run_id: int,
    require_running: bool,
) -> None:
    """줄 상태에 맞는 입력 수행"""

    if app_state.macro.run_id != run_id:
        return

    if require_running and not app_state.macro.is_running:
        return

    # 목표 줄과 현재 줄이 다르면 스왑 입력 수행
    if skill_ref.line_index != app_state.macro.current_line_index:
        swap_key: KeySpec = app_state.macro.current_swap_key

        # 프로그램 주입 스왑 입력 등록
        _register_injected_key_event(swap_key)
        kbd_controller.press(swap_key.value)
        kbd_controller.release(swap_key.value)

        app_state.macro.current_line_index = skill_ref.line_index

    # 현재 세로줄 공용키 기준 스킬 입력 키 조회
    skill_key: KeySpec = KeyRegistry.get(
        app_state.macro.current_preset.skills.skill_keys[skill_ref.scroll_index]
    )

    # 프로그램 주입 스킬 입력 등록
    _register_injected_key_event(skill_key)
    kbd_controller.press(skill_key.value)
    kbd_controller.release(skill_key.value)


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
    app_state.macro.current_line_index = 0
    app_state.macro.prepared_skills = set(placed_refs)
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

        app_state.macro.using_link_skills.append(
            [skill_ref_map[skill_id] for skill_id in link_skill.skills]
        )

    app_state.macro.link_skills_requirements = [
        [skill_ref for skill_ref in link_skill]
        for link_skill in app_state.macro.using_link_skills
    ]
    app_state.macro.task_list.clear()

    now: float = time.perf_counter()
    app_state.macro.skill_cooltime_timers = {
        skill_ref: now for skill_ref in placed_refs
    }


def use_skill(run_id: int) -> bool:
    """스킬 사용 함수"""

    if not app_state.macro.task_list:
        return False

    # 스킬 입력 직전과 후속 딜레이 동안 평타 끼어들기 차단
    _pause_attack_for(_get_attack_hold_seconds())

    kbd_controller: keyboard.Controller = keyboard.Controller()
    skill_ref: EquippedSkillRef = app_state.macro.task_list.pop(0)
    app_state.macro.skill_cooltime_timers[skill_ref] = time.perf_counter()

    _press_skill_keys(kbd_controller, skill_ref, run_id, require_running=True)

    time.sleep(
        app_state.macro.current_delay * 0.001 * config.macro.SLEEP_COEFFICIENT_NORMAL
    )

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

    # 연계 입력 전체 구간 동안 평타 클릭 차단
    link_skill_pause_seconds: float = (
        len(link_skill.skills) * app_state.macro.current_delay * 0.001
    ) + ATTACK_PAUSE_BUFFER_SECONDS
    _pause_attack_for(link_skill_pause_seconds)

    # 수동 연계 시작 기준 1줄 상태 초기화
    app_state.macro.current_line_index = 0

    kbd_controller: keyboard.Controller = keyboard.Controller()

    # 연계에 등록된 순서대로 스킬 입력 진행
    for skill_id in link_skill.skills:
        skill_ref: EquippedSkillRef = skill_ref_map[skill_id]

        _press_skill_keys(kbd_controller, skill_ref, run_id, require_running=False)
        time.sleep(
            app_state.macro.current_delay
            * 0.001
            * config.macro.SLEEP_COEFFICIENT_NORMAL
        )


def _pop_next_regular_task(
    prepared_skills: set[EquippedSkillRef],
    current_line_index: int,
    skill_sequence: list[EquippedSkillRef],
    link_skills_requirements: list[list[EquippedSkillRef]],
) -> EquippedSkillRef | None:
    """현재 줄 상태를 반영한 다음 일반 스킬 선택"""

    # 자동 연계에 속한 스킬 참조 집합 구성
    linked_skill_refs: set[EquippedSkillRef] = {
        skill_ref
        for requirements in link_skills_requirements
        for skill_ref in requirements
    }
    first_usable_skill_ref: EquippedSkillRef | None = None
    first_usable_allows_solo_swap: bool = False
    first_current_line_skill_ref: EquippedSkillRef | None = None

    # 우선순위 순서대로 사용 가능한 일반 스킬 후보 탐색
    for skill_ref in skill_sequence:
        skill_id: str = app_state.macro.current_preset.skills.get_placed_skill_id(
            skill_ref
        )
        setting: SkillUsageSetting = app_state.macro.current_preset.usage_settings[
            skill_id
        ]
        is_ready: bool = skill_ref in prepared_skills
        in_link_skill: bool = skill_ref in linked_skill_refs
        can_use_linked_skill_alone: bool = in_link_skill and setting.use_alone
        can_use_regular_skill: bool = (not in_link_skill) and setting.use_skill

        # 준비되지 않았거나 일반 스킬 조건을 만족하지 않으면 제외
        if not is_ready:
            continue

        if not can_use_linked_skill_alone and not can_use_regular_skill:
            continue

        # 전체 최상위 후보와 현재 줄 후보를 각각 기록
        if first_usable_skill_ref is None:
            first_usable_skill_ref = skill_ref
            first_usable_allows_solo_swap = setting.use_solo_swap

        if (
            skill_ref.line_index == current_line_index
            and first_current_line_skill_ref is None
        ):
            first_current_line_skill_ref = skill_ref

    # 일반 스킬 후보가 없으면 선택 종료
    if first_usable_skill_ref is None:
        return None

    # 현재 줄 스킬은 즉시 사용
    if first_usable_skill_ref.line_index == current_line_index:
        prepared_skills.discard(first_usable_skill_ref)
        return first_usable_skill_ref

    # 단독 스왑 허용 스킬은 우선순위대로 즉시 스왑 허용
    if first_usable_allows_solo_swap:
        prepared_skills.discard(first_usable_skill_ref)
        return first_usable_skill_ref

    # 현재 줄에 사용 가능한 스킬이 있으면 스왑을 미루고 먼저 소모
    if first_current_line_skill_ref is not None:
        prepared_skills.discard(first_current_line_skill_ref)
        return first_current_line_skill_ref

    # 현재 줄 스킬이 없으면 다른 줄 최상위 스킬 진행
    prepared_skills.discard(first_usable_skill_ref)
    return first_usable_skill_ref


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

    prepared_link_skill_indices: list[int] = get_prepared_link_skill_indices(
        prepared_skills=app_state.macro.prepared_skills,
        link_skills_requirements=app_state.macro.link_skills_requirements,
    )

    if prepared_link_skill_indices:
        for skill_ref in app_state.macro.using_link_skills[
            prepared_link_skill_indices[0]
        ]:
            app_state.macro.prepared_skills.discard(skill_ref)
            app_state.macro.task_list.append(skill_ref)

    else:
        # 현재 줄 상태와 단독 스왑 규칙을 반영한 일반 스킬 1개 선택
        next_regular_skill_ref: EquippedSkillRef | None = _pop_next_regular_task(
            prepared_skills=app_state.macro.prepared_skills,
            current_line_index=app_state.macro.current_line_index,
            skill_sequence=app_state.macro.skill_sequence,
            link_skills_requirements=app_state.macro.link_skills_requirements,
        )
        if next_regular_skill_ref is not None:
            app_state.macro.task_list.append(next_regular_skill_ref)

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

    prepared_link_skill_indices: list[int] = get_prepared_link_skill_indices(
        prepared_skills=preview_state.prepared_skills,
        link_skills_requirements=preview_state.link_skills_requirements,
    )

    # 자동 연계가 준비된 경우 실제 실행 순서와 동일하게 먼저 추가
    for prepared_link_skill_index in prepared_link_skill_indices:
        for skill_ref in preview_state.using_link_skills[prepared_link_skill_index]:
            preview_state.prepared_skills.discard(skill_ref)
            preview_state.task_list.append(skill_ref)
            preview_state.preview_line_index = skill_ref.line_index

    # 남은 일반 스킬은 단독 스왑 규칙을 반영하며 순서대로 추가
    while True:
        next_regular_skill_ref: EquippedSkillRef | None = _pop_next_regular_task(
            prepared_skills=preview_state.prepared_skills,
            current_line_index=preview_state.preview_line_index,
            skill_sequence=preview_state.skill_sequence,
            link_skills_requirements=preview_state.link_skills_requirements,
        )
        if next_regular_skill_ref is None:
            break

        preview_state.task_list.append(next_regular_skill_ref)
        preview_state.preview_line_index = next_regular_skill_ref.line_index

    return tuple(preview_state.task_list)


def _build_preview_task_state() -> PreviewTaskState:
    """프리뷰 계산용 상태 스냅샷 구성"""

    # 실행 중에는 실제 런타임 상태를 복사해 프리뷰에 반영
    if app_state.macro.is_running:
        return PreviewTaskState(
            prepared_skills=app_state.macro.prepared_skills.copy(),
            task_list=app_state.macro.task_list.copy(),
            preview_line_index=app_state.macro.current_line_index,
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
    using_link_skills: list[list[EquippedSkillRef]] = []

    # 현재 배치 기준으로 실행 가능한 자동 연계만 프리뷰 대상에 포함
    link_skill: LinkSkill
    for link_skill in app_state.macro.current_preset.link_skills:
        if link_skill.use_type != LinkUseType.AUTO:
            continue

        if not all(skill_id in skill_ref_map for skill_id in link_skill.skills):
            continue

        using_link_skills.append(
            [skill_ref_map[skill_id] for skill_id in link_skill.skills]
        )

    return PreviewTaskState(
        prepared_skills=set(placed_refs),
        task_list=[],
        preview_line_index=0,
        skill_sequence=_collect_priority_skill_sequence(),
        using_link_skills=using_link_skills,
        link_skills_requirements=[
            [skill_ref for skill_ref in link_skill] for link_skill in using_link_skills
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
