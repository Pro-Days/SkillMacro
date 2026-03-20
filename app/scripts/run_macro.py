from __future__ import annotations

import time
from threading import Thread
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


# 전역 입력 상태 추적
pressed_keys: set[Key | KeyCode] = set()
any_key_pressed = False


def on_press(key: Key | KeyCode | None) -> None:
    """키가 눌렸을 때 호출되는 함수"""

    global pressed_keys, any_key_pressed

    if key is None:
        return

    pressed_keys.add(key)
    any_key_pressed = True


def on_release(key: Key | KeyCode | None) -> None:
    """키가 떼어졌을 때 호출되는 함수"""

    global pressed_keys

    if key is None:
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
            app_state.macro.is_running = not app_state.macro.is_running

            # 매크로 시작
            if app_state.macro.is_running:
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
        Thread(
            target=clicking_mouse_thread,
            args=[app_state.macro.run_id],
            daemon=True,
        ).start()

    while app_state.macro.is_running and app_state.macro.run_id == run_id:
        # taskList에 사용 가능한 스킬 추가
        if not app_state.macro.task_list:
            build_task_list(show_info=DEBUG_PRINT_INFO)

        # 스킬 사용하고 사용 여부 리턴
        is_used_skill: bool = use_skill(run_id=app_state.macro.run_id)

        # 잠수면 매크로 중지
        if (
            config.macro.is_afk_enabled
            and time.time() - app_state.macro.afk_started_time >= 10
        ):
            app_state.macro.is_running = False

        if not is_used_skill:
            time.sleep(1 * config.macro.SLEEP_COEFFICIENT_UNIT)


def clicking_mouse_thread(run_id: int) -> None:
    """마우스 클릭 쓰레드"""

    mouse_controller = mouse.Controller()

    while app_state.macro.is_running and app_state.macro.run_id == run_id:
        mouse_controller.click(mouse.Button.left)
        time.sleep(app_state.macro.current_delay * 0.001)


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

    if skill_ref.line_index != app_state.macro.current_line_index:
        swap_key: KeySpec = app_state.macro.current_swap_key

        kbd_controller.press(swap_key.value)
        kbd_controller.release(swap_key.value)

        app_state.macro.current_line_index = skill_ref.line_index

    skill_key: KeySpec = KeyRegistry.get(
        app_state.macro.current_preset.skills.skill_keys[skill_ref.scroll_index]
    )

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

    app_state.macro.afk_started_time = time.time()
    app_state.macro.current_line_index = 0
    app_state.macro.prepared_skills = set(placed_refs)
    app_state.macro.skill_sequence = _collect_priority_skill_sequence()
    app_state.macro.using_link_skills.clear()

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

    kbd_controller = keyboard.Controller()
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

    kbd_controller = keyboard.Controller()

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
) -> EquippedSkillRef | None:
    """현재 줄 상태를 반영한 다음 일반 스킬 선택"""

    # 자동 연계에 속한 스킬 참조 집합 구성
    linked_skill_refs: set[EquippedSkillRef] = {
        skill_ref
        for requirements in app_state.macro.link_skills_requirements
        for skill_ref in requirements
    }
    first_usable_skill_ref: EquippedSkillRef | None = None
    first_usable_allows_solo_swap: bool = False
    first_current_line_skill_ref: EquippedSkillRef | None = None

    # 우선순위 순서대로 사용 가능한 일반 스킬 후보 탐색
    for skill_ref in app_state.macro.skill_sequence:
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


def build_task_list(show_info: bool = False) -> None:
    """task_list에 사용할 스킬 추가"""

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
        )
        if next_regular_skill_ref is not None:
            app_state.macro.task_list.append(next_regular_skill_ref)

    if DEBUG_PRINT_INFO and show_info:
        print_macro_info(brief=False)


def build_preview_task_list() -> tuple[EquippedSkillRef, ...]:
    """프리뷰용 task_list 계산"""

    if not app_state.macro.is_running:
        init_macro()

    # 현재 실행 상태를 훼손하지 않도록 프리뷰 전용 복사본 구성
    prepared_skills: set[EquippedSkillRef] = app_state.macro.prepared_skills.copy()
    task_list: list[EquippedSkillRef] = app_state.macro.task_list.copy()
    preview_line_index: int = app_state.macro.current_line_index

    prepared_link_skill_indices: list[int] = get_prepared_link_skill_indices(
        prepared_skills=prepared_skills,
        link_skills_requirements=app_state.macro.link_skills_requirements,
    )

    # 자동 연계가 준비된 경우 실제 실행 순서와 동일하게 먼저 추가
    for prepared_link_skill_index in prepared_link_skill_indices:
        for skill_ref in app_state.macro.using_link_skills[prepared_link_skill_index]:
            prepared_skills.discard(skill_ref)
            task_list.append(skill_ref)
            preview_line_index = skill_ref.line_index

    # 남은 일반 스킬은 단독 스왑 규칙을 반영하며 순서대로 추가
    while True:
        next_regular_skill_ref: EquippedSkillRef | None = _pop_next_regular_task(
            prepared_skills=prepared_skills,
            current_line_index=preview_line_index,
        )
        if next_regular_skill_ref is None:
            break

        task_list.append(next_regular_skill_ref)
        preview_line_index = next_regular_skill_ref.line_index

    return tuple(task_list)


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
