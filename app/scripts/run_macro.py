from __future__ import annotations

import time
from threading import Thread
from typing import TYPE_CHECKING, NoReturn

from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode

from app.scripts.macro_models import LinkKeyType, LinkUseType
from app.scripts.misc import get_skill_details, set_var_to_ClassVar

if TYPE_CHECKING:
    from app.scripts.shared_data import KeySpec, SharedData


DEBUG_PRINT_INFO = False  # 디버깅용


# 전역 변수로 키 상태 추적
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


def checking_kb_thread(shared_data: SharedData) -> NoReturn:
    """키보드 입력 감지 쓰레드"""

    global any_key_pressed

    # 키보드 리스너 시작
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    while True:
        # 다른 키 설정 중일 때는 패스
        if shared_data.is_setting_key:
            time.sleep(0.1)
            continue

        # 매크로 실행중일 때 어떤 키보드 입력이 있으면 잠수 시간 초기화
        if shared_data.is_activated and any_key_pressed:
            shared_data.afk_started_time = time.time()

            # 플래그 리셋
            any_key_pressed = False

        # 매크로 시작/중지
        if is_key_pressed(shared_data.start_key):
            # On -> Off
            if shared_data.is_activated:
                shared_data.is_activated = False

            # Off -> On
            else:
                shared_data.is_activated = True

                # 매크로 번호 증가
                shared_data.loop_num += 1

                # 매크로 쓰레드 시작
                Thread(
                    target=running_macro_thread,
                    args=[shared_data, shared_data.loop_num],
                ).start()

            # 매크로 실행/중지 이후에는 잠시 키 입력 무시
            time.sleep(0.5 * shared_data.SLEEP_COEFFICIENT_NORMAL)

            # 다음 루프로 넘어감
            continue

        # 연계스킬 사용
        for link_skill in shared_data.link_skills:
            # 단축키가 설정된 연계스킬만 검사
            if link_skill.key_type == LinkKeyType.OFF or link_skill.key is None:
                continue

            # 연계스킬 키가 눌렸다면
            link_key: KeySpec = shared_data.KEY_DICT[link_skill.key]
            if is_key_pressed(link_key):
                # 연계스킬 쓰레드 시작
                Thread(
                    target=use_link_skill,
                    args=[shared_data, link_skill, shared_data.loop_num],
                ).start()

                break

        # 연계스킬이 실행되지 않았으면 0.05초 슬립
        else:
            time.sleep(0.05 * shared_data.SLEEP_COEFFICIENT_NORMAL)
            continue

        # 연계스킬이 실행되었으면 0.25초 슬립
        time.sleep(0.25 * shared_data.SLEEP_COEFFICIENT_NORMAL)


def running_macro_thread(shared_data: SharedData, loop_num: int) -> None:
    """
    매크로 메인 쓰레드
    """

    # 매크로 초기 설정
    init_macro(shared_data=shared_data)

    # 매크로 클릭 쓰레드
    if shared_data.mouse_click_type:
        Thread(
            target=clicking_mouse_thread, args=[shared_data, loop_num], daemon=True
        ).start()

    # 매크로 작동중일 때
    while shared_data.is_activated and shared_data.loop_num == loop_num:
        # taskList에 사용 가능한 스킬 추가
        if not shared_data.task_list:
            build_task_list(shared_data=shared_data, show_info=DEBUG_PRINT_INFO)

        # 스킬 사용하고 시간, 사용한 스킬 리턴. skill: slot
        is_used_skill: bool = use_skill(shared_data=shared_data, loop_num=loop_num)

        # 잠수면 매크로 중지
        if (
            shared_data.IS_AFK_ENABLED
            and time.time() - shared_data.afk_started_time >= 10
        ):
            shared_data.is_activated = False

        # 스킬 사용 안했으면 슬립 (useSkill에서 슬립을 안함)
        if not is_used_skill:
            time.sleep(shared_data.UNIT_TIME * shared_data.SLEEP_COEFFICIENT_UNIT)


def clicking_mouse_thread(shared_data: SharedData, loop_num: int) -> None:
    """마우스 클릭 쓰레드"""

    # pynput 마우스 컨트롤러 생성
    mouse_controller = mouse.Controller()

    # 매크로가 작동중일 때 클릭
    while shared_data.is_activated and shared_data.loop_num == loop_num:
        mouse_controller.click(mouse.Button.left)

        time.sleep(shared_data.delay * 0.001)


def init_macro(shared_data: SharedData) -> None:
    """매크로 초기 설정"""

    shared_data.afk_started_time = time.time()

    # 사용 가능한 스킬 리스트: slot
    set_var_to_ClassVar(
        shared_data.prepared_skills,
        {i for i in range(6) if shared_data.equipped_skills[i]},
    )

    # 연계스킬 제외 스킬 사용 순서 설정: 우선순위 -> 등록 순서
    shared_data.skill_sequence.clear()

    # 사용 우선순위에 등록되어있는 스킬 순서대로 등록
    for target_priority in range(1, 7):
        for skill, priority in shared_data.skill_priority.items():
            if priority == target_priority:
                # 우선순위 있는 스킬은 모두 장착되어있음
                slot: int = shared_data.equipped_skills.index(skill)

                shared_data.skill_sequence.append(slot)

    # 우선순위 등록 안된 스킬 모두 등록
    # todo: tuple로 변경
    for i in range(6):
        if i not in shared_data.skill_sequence:
            shared_data.skill_sequence.append(i)

    # 매크로 작동 중 사용하는 연계스킬 리스트 -> dict로 변환
    shared_data.using_link_skills.clear()

    for link_skill in shared_data.link_skills:
        # 연계 유형이 자동이라면: 매크로에서 사용되는 연계스킬이라면
        if link_skill.use_type == LinkUseType.AUTO:
            # 연계스킬에서 사용되는 스킬 슬롯 번호로 변환 후 저장
            shared_data.using_link_skills.append(
                [shared_data.equipped_skills.index(name) for name in link_skill.skills]
            )

    # 연계스킬 수행에 필요한 스킬 정보 리스트
    set_var_to_ClassVar(
        shared_data.link_skills_requirements,
        [[slot for slot in link_skill] for link_skill in shared_data.using_link_skills],
    )

    # task_list 초기화
    shared_data.task_list.clear()

    # 스킬 쿨타임 타이머 초기화
    now: float = time.perf_counter()
    set_var_to_ClassVar(
        shared_data.skill_cooltime_timers,
        [now] * shared_data.USABLE_SKILL_COUNT[shared_data.server_ID],
    )


def use_skill(shared_data: SharedData, loop_num: int) -> bool:
    """스킬 사용 함수"""

    # pynput 키보드 컨트롤러 생성
    kbd_controller = keyboard.Controller()

    # task_list가 비어있으면 False 리턴
    if not shared_data.task_list:
        return False

    slot: int = shared_data.task_list.pop(0)

    key: KeySpec = shared_data.skill_keys[slot]

    # 쿨타임 시작
    shared_data.skill_cooltime_timers[slot] = time.perf_counter()

    # 키보드 입력
    if shared_data.is_activated and shared_data.loop_num == loop_num:
        kbd_controller.press(key.value)
        kbd_controller.release(key.value)

    # 스킬 사용에 걸린 시간 (pynput에는 PAUSE가 없음)
    sleeped_time: float = (
        shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
    )

    time.sleep(sleeped_time)

    return True


def use_link_skill(shared_data: SharedData, link_skill, loop_num: int) -> None:
    """연계스킬 사용 함수"""

    # pynput 키보드 컨트롤러 생성
    kbd_controller = keyboard.Controller()

    def use(slot: int) -> None:
        """스킬 사용 함수"""

        key: KeySpec = shared_data.skill_keys[slot]

        if shared_data.loop_num == loop_num:
            kbd_controller.press(key.value)
            kbd_controller.release(key.value)

        time.sleep(shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL)

    for skill in link_skill.skills:
        slot: int = shared_data.equipped_skills.index(skill)
        use(slot)


def build_task_list(shared_data: SharedData, show_info: bool = False) -> None:
    """
    task_list에 사용할 스킬 추가
    todo: task_list, prepared_skills 등을 class로 변경
    """

    # 쿨타임이 지난 스킬들 업데이트

    # 장착된 스킬 슬롯 번호들
    equipped_slots: list[int] = [
        slot
        for slot in range(shared_data.USABLE_SKILL_COUNT[shared_data.server_ID])
        if shared_data.equipped_skills[slot]
    ]
    # 장착된 스킬의 쿨타임 감소 스탯이 적용된 쿨타임
    cooltimes: dict[int, float] = {
        slot: get_skill_details(
            shared_data=shared_data,
            skill_id=shared_data.equipped_skills[slot],
        )["cooltime"]
        * (100 - shared_data.cooltime_reduction)
        / 100.0
        for slot in equipped_slots
    }

    # time.time()보다 더 정확한 시간 측정 함수
    now: float = time.perf_counter()

    # 각 장착된 스킬에 대해
    for slot in equipped_slots:
        # 스킬 쿨타임이 지났는지 확인
        if (
            # 스킬 사용해서 쿨타임 기다리는 중이고
            slot not in shared_data.prepared_skills
            # 쿨타임이 지났다면
            and (now - shared_data.skill_cooltime_timers[slot]) >= cooltimes[slot]
        ):
            # 준비된 스킬 리스트에 추가
            shared_data.prepared_skills.add(slot)

    # 연계스킬 사용
    # 준비된 연계스킬 리스트 인덱스
    prepared_link_skill_indices: list[int] = get_prepared_link_skill_indices(
        prepared_skills=shared_data.prepared_skills,
        link_skills_requirements=shared_data.link_skills_requirements,
    )

    # 준비된 연계스킬이 있다면
    if prepared_link_skill_indices:
        # 준비된 연계스킬 중 첫 번째에 포함된 스킬들 모두 task_list에 추가
        for skill in shared_data.using_link_skills[prepared_link_skill_indices[0]]:
            # 준비된 스킬 리스트에서 제거
            shared_data.prepared_skills.discard(skill)

            # task_list에 추가
            shared_data.task_list.append(skill)

    # 연계스킬을 사용하지 않는다면 준비된 스킬 정렬 순서대로 사용 (스킬 하나만 사용)
    else:
        # 연계스킬 사용중인 스킬 전부 모으기
        link_skill_reqs: list[int] = sum(shared_data.link_skills_requirements, [])

        # 스킬 정렬 순서대로 검사
        for skill in shared_data.skill_sequence:
            # 연계스킬 O & 단독 사용 O -> O
            # 연계스킬 O & 단독 사용 X -> X
            # 연계스킬 X & 사용 O -> O
            # 연계스킬 X & 사용 X -> X

            if (
                # 스킬이 준비되었고
                skill in shared_data.prepared_skills
                # 연계스킬에 포함되었고
                and skill in link_skill_reqs
                # 단독 사용 옵션이 켜져있다면
                and shared_data.is_use_sole[shared_data.equipped_skills[skill]]
            ):
                # task_list에 추가
                shared_data.task_list.append(skill)

                # 준비된 스킬 리스트에서 해당 스킬 제거
                shared_data.prepared_skills.discard(skill)

                break

            elif (
                # 스킬이 준비되었고
                skill in shared_data.prepared_skills
                # 연계스킬에 포함되지 않았고
                and skill not in link_skill_reqs
                # 사용 옵션이 켜져있다면
                and shared_data.is_use_skill[shared_data.equipped_skills[skill]]
            ):
                # task_list에 스킬 추가
                shared_data.task_list.append(skill)

                # 준비된 스킬 리스트에서 해당 스킬 제거
                shared_data.prepared_skills.discard(skill)

                break

    # 디버깅용 출력
    if DEBUG_PRINT_INFO and show_info:
        print_macro_info(shared_data, brief=False)


def build_preview_task_list(shared_data: SharedData) -> tuple[int, ...]:
    """
    프리뷰를 위한 task_list에 스킬 추가
    """

    prepared_skills: set[int] = shared_data.prepared_skills.copy()
    task_list: list[int] = []

    # 연계스킬 사용
    # 준비된 연계스킬 리스트 인덱스
    prepared_link_skill_indices: list[int] = get_prepared_link_skill_indices(
        prepared_skills=prepared_skills,
        link_skills_requirements=shared_data.link_skills_requirements,
    )
    # 준비된 연계스킬이 있다면
    for prepared_link_skill_index in prepared_link_skill_indices:
        # 준비된 연계스킬에 포함된 스킬들 모두 task_list에 추가
        for skill in shared_data.using_link_skills[prepared_link_skill_index]:
            # 준비된 스킬 리스트에서 제거
            prepared_skills.discard(skill)

            # task_list에 추가
            task_list.append(skill)

    # 연계스킬 사용 후 준비된 스킬 정렬 순서대로 사용
    # 연계스킬에 사용중인 스킬 전부 모으기
    link_skill_reqs: list[int] = sum(shared_data.link_skills_requirements, [])

    # 스킬 정렬 순서대로 검사
    for skill in shared_data.skill_sequence:
        # 연계스킬 O & 단독 사용 O -> O
        # 연계스킬 O & 단독 사용 X -> X
        # 연계스킬 X & 사용 O -> O
        # 연계스킬 X & 사용 X -> X

        if (
            # 스킬이 준비되었고
            skill in prepared_skills
            # 연계스킬에 포함되었고
            and skill in link_skill_reqs
            # 단독 사용 옵션이 켜져있다면
            and shared_data.is_use_sole[shared_data.equipped_skills[skill]]
        ):
            # task_list에 추가
            task_list.append(skill)

            # 준비된 스킬 리스트에서 해당 스킬 제거
            prepared_skills.discard(skill)

        elif (
            # 스킬이 준비되었고
            skill in prepared_skills
            # 연계스킬에 포함되지 않았고
            and skill not in link_skill_reqs
            # 사용 옵션이 켜져있다면
            and shared_data.is_use_skill[shared_data.equipped_skills[skill]]
        ):
            # task_list에 스킬 추가
            task_list.append(skill)

            # 준비된 스킬 리스트에서 해당 스킬 제거
            prepared_skills.discard(skill)

    return tuple(task_list)


def get_prepared_link_skill_indices(
    prepared_skills: set[int], link_skills_requirements: list[list[int]]
) -> list[int]:
    """
    준비된 연계스킬 목록 리턴
    """

    prepared_indices: list[int] = []

    for idx, req in enumerate(link_skills_requirements):
        for skill in req:
            # 만약 연계스킬에 필요한 스킬이 준비된 스킬 리스트에 없다면
            if skill not in prepared_skills:
                # 다음 연계스킬로 넘어감
                break

        # 모든 스킬이 준비되었으면
        else:
            # 연계스킬에 필요한 스킬들 준비된 스킬 리스트에서 제거
            for skill in req:
                prepared_skills.discard(skill)

            # 연계스킬 준비 리스트에 추가
            prepared_indices.append(idx)

    return prepared_indices


def print_macro_info(shared_data: SharedData, brief=False) -> None:
    if brief:
        print("테스크 리스트:", shared_data.task_list)  # 사용여부 x, 사용여부 o
        print(
            "준비된 스킬 리스트:", shared_data.prepared_skills
        )  # 사용여부 x, 사용여부 o

    else:
        print("테스크 리스트:", shared_data.task_list)  # 사용여부 x, 사용여부 o
        print(
            "준비된 스킬 리스트:", shared_data.prepared_skills
        )  # 사용여부 x, 사용여부 o
        print("스킬 정렬 순서:", shared_data.skill_sequence)
        print("연계스킬 스킬 리스트:", shared_data.using_link_skills)
        print("연계스킬에 필요한 스킬 리스트:", shared_data.link_skills_requirements)
