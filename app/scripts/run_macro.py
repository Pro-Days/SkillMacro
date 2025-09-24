from __future__ import annotations

import copy
import time
from pynput import keyboard, mouse
from threading import Thread
from typing import TYPE_CHECKING, NoReturn

from PyQt6.QtCore import QThread, pyqtSignal

from .misc import convert_skill_name_to_slot, get_skill_details, set_var_to_ClassVar


if TYPE_CHECKING:
    from .shared_data import SharedData


print_info = False  # 디버깅용


"""
pynput을 사용한 키보드 감지
"""

# 전역 변수로 키 상태 추적
pressed_keys = set()
any_key_pressed = False


def on_press(key):
    global pressed_keys, any_key_pressed
    try:
        # 일반 키의 경우
        if hasattr(key, "char") and key.char:
            pressed_keys.add(key.char.lower())
        else:
            # 특수 키의 경우
            pressed_keys.add(str(key).replace("Key.", ""))
        any_key_pressed = True
    except AttributeError:
        # 알 수 없는 키의 경우
        pressed_keys.add(str(key))
        any_key_pressed = True


def on_release(key):
    global pressed_keys, any_key_pressed
    try:
        # 일반 키의 경우
        if hasattr(key, "char") and key.char:
            pressed_keys.discard(key.char.lower())
        else:
            # 특수 키의 경우
            pressed_keys.discard(str(key).replace("Key.", ""))
    except AttributeError:
        # 알 수 없는 키의 경우
        pressed_keys.discard(str(key))


def is_key_pressed(key_name: str) -> bool:
    """특정 키가 눌려있는지 확인"""
    global pressed_keys
    # 키 이름을 소문자로 변환하여 확인
    key_lower = key_name.lower()

    # 특수 키 매핑
    special_keys = {
        "space": "space",
        "enter": "enter",
        "shift": "shift",
        "ctrl": "ctrl",
        "alt": "alt",
        "tab": "tab",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "page_up": "page_up",
        "page_down": "page_down",
    }

    if key_lower in special_keys:
        return special_keys[key_lower] in pressed_keys
    else:
        return key_lower in pressed_keys


def checking_kb_thread(shared_data: SharedData) -> NoReturn:
    global any_key_pressed

    # 키보드 리스너 시작
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    while True:
        # 매크로 실행중일 때 아무 키보드 입력이 있으면 잠수 시간 초기화
        if shared_data.is_activated and any_key_pressed:
            shared_data.afk_started_time = time.time()
            any_key_pressed = False  # 플래그 리셋

        # 매크로 시작/중지
        start_key = shared_data.KEY_DICT.get(
            shared_data.start_key, shared_data.start_key
        )
        if is_key_pressed(start_key):
            # On -> Off
            if shared_data.is_activated:
                shared_data.is_activated = False

            # Off -> On
            else:
                shared_data.is_activated = True

                # 매크로 번호 증가
                shared_data.loop_num += 1

                # 선택된 아이템 슬롯을 모르는 상태(-1)로 설정
                shared_data.selected_item_slot = -1

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
            # 연계스킬 키가 눌렸다면
            link_key = shared_data.KEY_DICT.get(link_skill["key"], link_skill["key"])
            if link_key and is_key_pressed(link_key):
                # 연계스킬에 사용되는 스킬 이름들
                skills: list[str] = [skill["name"] for skill in link_skill["skills"]]

                # 연계스킬에 필요한 스킬이 모두 장착되어 있는지 확인
                if all(skill in shared_data.equipped_skills for skill in skills):
                    # 연계스킬 쓰레드 시작
                    Thread(
                        target=useLinkSkill,
                        args=[shared_data, link_skill, shared_data.loop_num],
                    ).start()
                    break
        else:
            # 연계스킬도 실행되지 않았으면 0.05초 슬립
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

    # 스킬 쿨타임 타이머 : [사용된 시간] * 6
    set_var_to_ClassVar(
        shared_data.skill_cooltime_timers,
        [0.0] * shared_data.USABLE_SKILL_COUNT[shared_data.server_ID],
    )

    # 스킬 사용 가능 횟수 : [3, 2, 2, 1, 3, 3]
    set_var_to_ClassVar(
        shared_data.available_skill_counts,
        [
            (
                get_skill_details(
                    shared_data,
                    skill_name=shared_data.equipped_skills[i],
                )["max_combo_count"]
                # 스킬이 장착되어있지 않으면 0
                if shared_data.equipped_skills[i]
                else 0
            )
            for i in range(shared_data.USABLE_SKILL_COUNT[shared_data.server_ID])
        ],
    )

    # 스킬 쿨타임 업데이트 쓰레드
    Thread(
        target=updating_cooltimes_thread, args=[shared_data, loop_num], daemon=True
    ).start()

    # 매크로 클릭 쓰레드
    if shared_data.mouse_click_type:
        Thread(
            target=clicking_mouse_thread, args=[shared_data, loop_num], daemon=True
        ).start()

    # shared_data.startTime = time.time()
    # usedSkillList = []

    while (
        shared_data.is_activated and shared_data.loop_num == loop_num
    ):  # 매크로 작동중일 때
        # taskList에 사용 가능한 스킬 추가
        add_task_list(shared_data=shared_data)

        # 스킬 사용하고 시간, 사용한 스킬 리턴. skill: slot
        used_skill: int = use_skill(shared_data=shared_data, loop_num=loop_num)

        # 잠수면 매크로 중지
        if shared_data.IS_AFK_ENABLED:
            if time.time() - shared_data.afk_started_time >= 10:
                shared_data.is_activated = False

        # 스킬 사용 안했으면 슬립 (useSkill에서 슬립을 안함)
        if not used_skill:
            time.sleep(shared_data.UNIT_TIME * shared_data.SLEEP_COEFFICIENT_UNIT)

        # 디버깅용
        # if usedSkill != None:
        #     usedSkillList.append([usedSkill, int((time.time() - shared_data.startTime) * 1000)])
        #     print(f"{time.time() - shared_data.startTime:.3f} - {usedSkill}")
        # for i in range(6):
        #     print(
        #         f"{shared_data.availableSkillCount[i]} / {shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][shared_data.jobID][
        #         shared_data.equipped_skills[i]
        #     ]} : {shared_data.skillCoolTimers[i]} / {int(shared_data.SKILL_COOLTIME_LIST[shared_data.serverID][shared_data.jobID][shared_data.equipped_skills[i]] * (100 - shared_data.cooltimeReduce))}"
        #     )
        # print()

    # print(usedSkillList)


def clicking_mouse_thread(shared_data: SharedData, loop_num: int) -> None:
    # pynput 마우스 컨트롤러 생성
    mouse_controller = mouse.Controller()

    while shared_data.is_activated and shared_data.loop_num == loop_num:
        mouse_controller.click(mouse.Button.left)

        time.sleep(shared_data.delay * 0.001)


def updating_cooltimes_thread(shared_data: SharedData, loopNum: int) -> None:
    # 정확한 매크로 시작 시간
    started_time: float = time.perf_counter()

    # 병목이 생기지 않도록 미리 캐싱

    # 장착된 스킬 슬롯 번호들
    equipped_slots: list[int] = [
        slot
        for slot in range(shared_data.USABLE_SKILL_COUNT[shared_data.server_ID])
        if shared_data.equipped_skills[slot]
    ]
    # 장착된 스킬의 최대 연계 횟수
    max_combo_counts: dict[int, int] = {
        slot: get_skill_details(
            shared_data=shared_data,
            skill_name=shared_data.equipped_skills[slot],
        )["max_combo_count"]
        for slot in equipped_slots
    }
    # 장착된 스킬의 쿨감 스탯이 적용된 쿨타임
    cooltimes: dict[int, float] = {
        slot: get_skill_details(
            shared_data=shared_data,
            skill_name=shared_data.equipped_skills[slot],
        )["cooltime"]
        * (100 - shared_data.cooltime_reduction)
        / 100.0
        for slot in equipped_slots
    }

    i = 0
    # 매크로가 작동중일 때
    while shared_data.is_activated and shared_data.loop_num == loopNum:
        # time.time()
        now: float = time.time()

        # 각 장착된 스킬에 대해
        for slot in equipped_slots:
            # 스킬 쿨타임이 지났는지 확인
            if (
                # 스킬 사용해서 쿨타임 기다리는 중이고
                shared_data.available_skill_counts[slot] < max_combo_counts[slot]
                # 쿨타임이 지났다면
                and (now - shared_data.skill_cooltime_timers[slot]) >= cooltimes[slot]
            ):
                # 대기열에 추가
                shared_data.prepared_skills[2].append(slot)
                # 사용 가능 횟수 증가
                shared_data.available_skill_counts[slot] += 1

                # print(
                #     f"{time.time() - self.startTime:.3f} - {skill} {time.time() - self.skillCoolTimers[skill]}"
                # )

                # 쿨타임 초기화
                shared_data.skill_cooltime_timers[slot] = now

        i += 1

        # 매크로 작동 중 발생한 지연 시간을 고려하여 슬립
        now_precise: float = time.perf_counter()
        sleep_time: float = shared_data.UNIT_TIME * i - (now_precise - started_time)

        # 슬립 시간이 음수면 0으로 설정
        time.sleep(max(0.0, sleep_time))


def init_macro(shared_data: SharedData) -> None:
    shared_data.selected_item_slot = -1
    shared_data.afk_started_time = time.time()

    # 사용 가능한 스킬 리스트: slot
    # [사용X 설정, 사용O 설정, 쿨타임 지나서 대기중]
    set_var_to_ClassVar(
        shared_data.prepared_skills,
        [
            [
                i
                for i in range(6)
                if shared_data.equipped_skills[i]
                and not shared_data.is_use_skill[shared_data.equipped_skills[i]]
            ],
            [
                i
                for i in range(6)
                if shared_data.equipped_skills[i]
                and shared_data.is_use_skill[shared_data.equipped_skills[i]]
            ],
            [],  # append 대기
        ],
    )

    # 사용 가능한 스킬 개수 리스트: slot
    # [사용X 설정, 사용O 설정, 쿨타임 지나서 대기중]
    set_var_to_ClassVar(
        shared_data.prepared_skill_counts,
        [
            [
                get_skill_details(
                    shared_data=shared_data, skill_name=shared_data.equipped_skills[i]
                )["max_combo_count"]
                for i in range(6)
                if shared_data.equipped_skills[i]
                and not shared_data.is_use_skill[shared_data.equipped_skills[i]]
            ],
            [
                get_skill_details(
                    shared_data=shared_data, skill_name=shared_data.equipped_skills[i]
                )["max_combo_count"]
                for i in range(6)
                if shared_data.equipped_skills[i]
                and shared_data.is_use_skill[shared_data.equipped_skills[i]]
            ],
        ],
    )

    set_var_to_ClassVar(
        shared_data.prepared_skill_combos,
        [
            (
                shared_data.combo_count[shared_data.equipped_skills[i]]
                if shared_data.equipped_skills[i]
                else 0
            )
            for i in range(6)
        ],
    )  # 0~5

    # 연계스킬 제외 스킬 사용 순서: 우선순위 -> 등록: slot
    shared_data.skill_sequence.clear()  # 0~5 in self.equipped_skills

    # for i in self.link_skills:  # 연계스킬 메인1
    #     if not i[0]:
    #         self.skillSequences.append(self.convert7to5(i[2][0][0]))
    # for j, k in enumerate(self.equipped_skills):
    #     if k == i[2][0][0]:
    #         self.skillSequences.append(j)
    # print(self.skillSequences)

    # 사용 우선순위에 등록되어있는 스킬 순서대로 등록
    for target_priority in range(1, 7):
        for skill, priority in shared_data.skill_priority.items():
            if priority == target_priority:
                # slot is not -1: 우선순위 있는 스킬은 모두 장착되어있음.
                slot: int = convert_skill_name_to_slot(shared_data, skill)

                shared_data.skill_sequence.append(slot)

                # print(f"i: {i}, j: {j}, k: {k}")
                # for x, y in enumerate(self.equipped_skills):  # x: 0~5, y: 0~7
                #     if y == j and not (x in self.skillSequences):
                #         self.skillSequences.append(x)
                # print(f"j: {j}, x: {x}, y: {y}")
                # self.skillSequences.append(self.equipped_skills[j])

                # 타겟 우선순위에 맞는 스킬 발견하면 다음 우선순위로 넘어감
                break

        # 타겟 우선순위에 해당하는 스킬이 없으면 -> 이후 우선순위도 모두 없음.
        else:
            break

    # print(self.skillSequences)

    # 우선순위 등록 안된 스킬 모두 등록
    for i in range(6):
        if i not in shared_data.skill_sequence:
            shared_data.skill_sequence.append(i)

    # 매크로 작동 중 사용하는 연계스킬 리스트 -> dict로 변환
    shared_data.using_link_skills.clear()
    shared_data.using_link_skill_combos.clear()

    for link_skill in shared_data.link_skills:
        # 연계 유형이 자동이라면 = 매크로에서 사용되는 연계스킬이라면
        if link_skill["useType"] == "auto":
            # 연계스킬에서 사용되는 스킬 슬롯 번호로 변환 후 저장
            shared_data.using_link_skills.append(
                [
                    convert_skill_name_to_slot(shared_data, skill["name"])
                    for skill in link_skill["skills"]
                ]
            )
            shared_data.using_link_skill_combos.append(
                [skill["count"] for skill in link_skill["skills"]]
            )

    # 연계스킬 수행에 필요한 스킬 정보 리스트
    shared_data.link_skills_requirements.clear()
    shared_data.link_skills_combo_requirements.clear()

    for i, link_skill in enumerate(shared_data.using_link_skills):
        shared_data.link_skills_requirements.append([])
        shared_data.link_skills_combo_requirements.append([])

        for j, slot in enumerate(link_skill):  # y: slot
            # req에 없는 스킬이면 추가
            if slot not in shared_data.link_skills_requirements[-1]:  # set으로 변경
                shared_data.link_skills_requirements[-1].append(slot)
                shared_data.link_skills_combo_requirements[-1].append(
                    shared_data.using_link_skill_combos[i][j]
                )

            # req에 있는 스킬이면 콤보 개수 추가
            else:
                k: int = shared_data.link_skills_requirements[-1].index(slot)

                shared_data.link_skills_combo_requirements[-1][
                    k
                ] += shared_data.using_link_skill_combos[i][j]

    # 준비된 연계스킬 번호들: 0 ~ len
    set_var_to_ClassVar(
        shared_data.prepared_link_skill_indices,
        list(range(len(shared_data.using_link_skills))),
    )

    # task_list 초기화
    shared_data.task_list.clear()

    if print_info:
        print_macro_info(shared_data, brief=False)


def use_skill(shared_data: SharedData, loop_num: int) -> int:
    # pynput 키보드 컨트롤러 생성
    kbd_controller = keyboard.Controller()

    def press(key: str) -> None:
        if shared_data.is_activated and shared_data.loop_num == loop_num:
            # 키 문자열을 pynput Key 객체로 변환
            try:
                if len(key) == 1:
                    # 일반 문자
                    kbd_controller.press(key)
                    kbd_controller.release(key)
                else:
                    # 특수 키
                    special_key = getattr(keyboard.Key, key.lower(), None)
                    if special_key:
                        kbd_controller.press(special_key)
                        kbd_controller.release(special_key)
                    else:
                        # 알 수 없는 키는 문자로 처리
                        kbd_controller.press(key)
                        kbd_controller.release(key)
            except Exception as e:
                print(f"키 입력 오류: {key}, {e}")

    def click() -> None:
        if shared_data.is_activated and shared_data.loop_num == loop_num:
            # pynput 마우스 컨트롤러 사용
            mouse_controller = mouse.Controller()
            mouse_controller.click(mouse.Button.left)

    def use(skill: int) -> None:
        # 스킬 스택이 모두 찬 상태일 때 쿨타임 시작
        # 스택이 모두 차지 않았을 때는 이미 쿨타임이 시작되어있음.
        if (
            shared_data.available_skill_counts[skill]
            == get_skill_details(
                shared_data=shared_data, skill_name=shared_data.equipped_skills[skill]
            )["max_combo_count"]
        ):
            shared_data.skill_cooltime_timers[skill] = time.time()

        shared_data.available_skill_counts[skill] -= 1

    if not shared_data.task_list:
        return -1  # task_list가 비어있으면 -1 리턴

    slot: int = shared_data.task_list.pop(0)

    # 클릭 여부
    is_click: bool = get_skill_details(
        shared_data=shared_data, skill_name=shared_data.equipped_skills[slot]
    )["is_casting"]

    key: str = shared_data.skill_keys[slot]
    if key in shared_data.KEY_DICT:
        key = shared_data.KEY_DICT[key]

    # 인게임 선택된 슬롯이 사용하려는 스킬 슬롯과 다르다면
    if shared_data.selected_item_slot != slot:
        if is_click:  # press -> delay -> click
            press(key=key)

            time.sleep(shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL)

            use(skill=slot)
            click()

            shared_data.selected_item_slot = slot

        else:  # press
            use(skill=slot)
            press(key=key)

            shared_data.selected_item_slot = slot

    else:
        if is_click:  # click
            use(skill=slot)
            click()

        else:  # press
            use(skill=slot)
            press(key=key)

    # print(
    #     f"{time.time() - self.startTime - 0.1 if doClick else time.time() - self.startTime:.3f} - {skill}"
    # )

    # 스킬 사용에 걸린 시간 (pynput에는 PAUSE가 없음)
    sleeped_time: float = (
        shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
    )

    time.sleep(sleeped_time)

    return slot


def useLinkSkill(shared_data: SharedData, num, loop_num: int) -> None:
    # pynput 키보드 컨트롤러 생성
    kbd_controller = keyboard.Controller()

    def press(key: str) -> None:
        if shared_data.loop_num == loop_num:
            # 키 문자열을 pynput Key 객체로 변환
            try:
                if len(key) == 1:
                    # 일반 문자
                    kbd_controller.press(key)
                    kbd_controller.release(key)
                else:
                    # 특수 키
                    special_key = getattr(keyboard.Key, key.lower(), None)
                    if special_key:
                        kbd_controller.press(special_key)
                        kbd_controller.release(special_key)
                    else:
                        # 알 수 없는 키는 문자로 처리
                        kbd_controller.press(key)
                        kbd_controller.release(key)
            except Exception as e:
                print(f"키 입력 오류: {key}, {e}")

    def click() -> None:
        if shared_data.loop_num == loop_num:
            # pynput 마우스 컨트롤러 사용
            mouse_controller = mouse.Controller()
            mouse_controller.click(mouse.Button.left)

    def useSkill(slot: int) -> int:
        skill: int = task_list.pop(0)

        is_click: bool = get_skill_details(
            shared_data=shared_data, skill_name=shared_data.equipped_skills[skill]
        )["is_casting"]

        key: str = shared_data.skill_keys[skill]
        if key in shared_data.KEY_DICT:
            key = shared_data.KEY_DICT[key]

        # 인게임 선택된 슬롯이 사용하려는 스킬 슬롯과 다르다면
        if slot != skill:
            if is_click:
                press(key=key)
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )

                click()
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )

            else:
                press(key)
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )

        else:
            if is_click:
                click()
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )

            else:
                press(key=key)
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )

        return skill

    # 초기 설정
    slot = -1
    task_list: list[int] = []

    for i in shared_data.link_skills[num]["skills"]:
        task_list.extend(
            [convert_skill_name_to_slot(shared_data=shared_data, skill_name=i["skill"])]
            * i["count"]
        )

    for _ in range(len(task_list)):
        slot: int = useSkill(slot=slot)


def add_task_list(shared_data: SharedData, print_info: bool = False) -> None:
    """
    task_list에 사용할 스킬 추가
    """

    # append 대기중인 스킬 추가
    # skill: append 대기중인 스킬
    for skill in shared_data.prepared_skills[2]:
        # 대기중인 스킬이 사용 설정되어 있다면 -> index 1
        # 대기중인 스킬이 사용 설정되어 있지 않다면 -> index 0
        index: int = int(shared_data.is_use_skill[shared_data.equipped_skills[skill]])

        # 이미 준비된 같은 스킬이 있다면 그 개수 증가
        if skill in shared_data.prepared_skills[index]:
            # skill이 위치한 인덱스 찾기
            i: int = shared_data.prepared_skills[index].index(skill)

            shared_data.prepared_skill_counts[index][i] += 1

        # 준비된 같은 스킬이 없다면 새로 추가
        else:
            shared_data.prepared_skills[index].append(skill)
            shared_data.prepared_skill_counts[index].append(1)

    # append 후 모든 요소를 제거
    shared_data.prepared_skills[2].clear()

    # 준비된 연계스킬 리스트 업데이트
    # 사용되지 않은 task_list에 있는 스킬들 모두 포함해서 연계스킬 준비 여부 확인하도록 수정
    add_ready_link_skills(shared_data=shared_data)

    # if print_info:
    #     print("준비된 연계스킬리스트:", shared_data.preparedlink_skills)

    # -------------
    # 스킬 사용

    # 1. 연계스킬 사용
    # 준비된 연계스킬이 있는 동안
    while shared_data.prepared_link_skill_indices:
        # 준비된 연계스킬 인덱스 첫번째
        index: int = shared_data.prepared_link_skill_indices.pop(0)

        for skill, count in zip(
            shared_data.using_link_skills[index],
            shared_data.using_link_skill_combos[index],
        ):
            # i: prepared_skills의 [0]과 [1] 중 어느 것을 사용할지 결정
            i: int = int(skill not in shared_data.prepared_skills[0])

            # skill이 위치한 인덱스 찾기
            idx: int = shared_data.prepared_skills[i].index(skill)

            # 사용하는 횟수만큼 task_list에 추가 및 개수 감소
            for _ in range(count):
                # task_list에 스킬 추가
                shared_data.task_list.append(skill)

                # 스킬 사용 후 준비된 스킬 개수 감소
                shared_data.prepared_skill_counts[i][idx] -= 1

                # print(
                #     "count: ",
                #     count,
                #     "1준비된 스킬 개수 리스트:",
                #     self.preparedSkillCountList,
                # )

        # 이전 연계스킬에서 사용한 스킬이 다른 연계스킬에 포함되어있다면
        # 다음 연계스킬이 작동하지 않을 수 있으므로
        # 준비된 연계스킬 목록을 다시 업데이트
        add_ready_link_skills(shared_data=shared_data)

    # 연계스킬 사용 이후 준비된 스킬 목록 업데이트
    clear_used_skills(shared_data=shared_data, print_info=print_info)

    # 2. 준비된 스킬 정렬 순서대로 사용
    for skill in shared_data.skill_sequence:
        # 연계스킬 사용중인 스킬 전부 모으기
        using_skills: list[int] = sum(shared_data.link_skills_requirements, [])

        if (
            # 스킬이 준비되었고
            skill in shared_data.prepared_skills[1]
            # 연계스킬에 포함되었고
            and skill in using_skills
            # 단독 사용 옵션이 켜져있다면
            and shared_data.is_use_sole[shared_data.equipped_skills[skill]]
        ):
            # 준비된 스킬 개수 리스트에서 해당 스킬의 인덱스 찾기
            i: int = shared_data.prepared_skills[1].index(skill)

            # 해당 스킬의 개수만큼 task_list에 추가
            shared_data.task_list.extend(
                [skill] * shared_data.prepared_skill_counts[1][i]
            )
            shared_data.prepared_skill_counts[1][i] = 0

            # print(
            #     "2준비된 스킬 개수 리스트:",
            #     self.preparedSkillCountList,
            # )

        if (
            # 스킬이 준비되었고
            skill in shared_data.prepared_skills[1]
            # 연계스킬에 포함되지 않았고
            and skill not in using_skills
            # 사용 옵션이 켜져있다면
            and shared_data.is_use_skill[shared_data.equipped_skills[skill]]
        ):
            # 준비된 스킬 개수 리스트에서 해당 스킬의 인덱스 찾기
            i: int = shared_data.prepared_skills[1].index(skill)

            # 콤보 가능한 만큼 task_list에 추가
            while (
                shared_data.prepared_skill_counts[1][i]
                >= shared_data.prepared_skill_combos[skill]
            ):
                # task_list에 스킬 추가
                count: int = shared_data.prepared_skill_combos[skill]
                shared_data.task_list.extend([skill] * count)
                shared_data.prepared_skill_counts[1][i] -= count

                # print(
                #     "2준비된 스킬 개수 리스트:",
                #     self.preparedSkillCountList,
                # )

    # 사용 횟수가 0인 스킬 제거
    clear_used_skills(shared_data=shared_data, print_info=print_info)


def add_ready_link_skills(shared_data: SharedData) -> None:
    """
    준비된 연계스킬 목록 업데이트
    """

    # 준비된 연계 스킬 목록 초기화
    shared_data.prepared_link_skill_indices.clear()

    for link_skill_idx in range(len(shared_data.link_skills_requirements)):
        is_ready: list[bool] = [False] * len(
            shared_data.link_skills_requirements[link_skill_idx]
        )

        for skill_idx in range(
            len(shared_data.link_skills_requirements[link_skill_idx])
        ):
            skill: int = shared_data.link_skills_requirements[link_skill_idx][skill_idx]
            count: int = shared_data.link_skills_combo_requirements[link_skill_idx][
                skill_idx
            ]

            prepared_skills: list[int] = (
                shared_data.prepared_skills[0] + shared_data.prepared_skills[1]
            )
            prepared_skills_counts: list[int] = (
                shared_data.prepared_skill_counts[0]
                + shared_data.prepared_skill_counts[1]
            )

            # 만약 연계스킬에 필요한 스킬이 준비된 스킬 리스트에 있다면
            if skill in prepared_skills:
                for i in range(len(prepared_skills)):
                    # 연계스킬에 필요한 스킬이 준비된 스킬 리스트에 있고, 개수가 충분하다면
                    if (
                        skill == prepared_skills[i]
                        and count <= prepared_skills_counts[i]
                    ):
                        is_ready[skill_idx] = True

        if all(is_ready):
            shared_data.prepared_link_skill_indices.append(link_skill_idx)


def clear_used_skills(shared_data: SharedData, print_info=False) -> None:
    if print_info:
        print_macro_info(shared_data, brief=True)
        print("\n")

    for num in [0, 1]:
        # 사용된 스킬 개수 리스트에서 0인 스킬 제거
        filtered_skills: list[int] = []
        filtered_counts: list[int] = []

        for skill, count in zip(
            shared_data.prepared_skills[num], shared_data.prepared_skill_counts[num]
        ):
            # 스킬 개수가 0이 아니면 새 리스트에 추가
            if count:
                filtered_skills.append(skill)
                filtered_counts.append(count)

        # 필터링된 스킬 리스트로 업데이트
        shared_data.prepared_skills[num] = filtered_skills
        shared_data.prepared_skill_counts[num] = filtered_counts


def print_macro_info(shared_data: SharedData, brief=False) -> None:
    if brief:
        print("테스크 리스트:", shared_data.task_list)  # 사용여부 x, 사용여부 o
        print(
            "준비된 스킬 리스트:", shared_data.prepared_skills
        )  # 사용여부 x, 사용여부 o
        print(
            "준비된 스킬 개수 리스트:", shared_data.prepared_skill_counts
        )  # 사용여부 x, 사용여부 o
        print("준비된 연계스킬리스트:", shared_data.prepared_link_skill_indices)

    else:
        print(
            "준비된 스킬 리스트:", shared_data.prepared_skills
        )  # 사용여부 x, 사용여부 o
        print(
            "준비된 스킬 개수 리스트:", shared_data.prepared_skill_counts
        )  # 사용여부 x, 사용여부 o
        print("스킬 콤보 리스트:", shared_data.prepared_skill_combos)  # 사용여부 o
        print("스킬 정렬 순서:", shared_data.skill_sequence)
        print("연계스킬 스킬 리스트:", shared_data.using_link_skills)
        print("연계스킬 스킬 콤보 리스트:", shared_data.using_link_skill_combos)
        print("연계스킬에 필요한 스킬 리스트:", shared_data.link_skills_requirements)
        print(
            "연계스킬에 필요한 스킬 콤보 리스트:",
            shared_data.link_skills_combo_requirements,
        )
        print("준비된 연계스킬리스트:", shared_data.prepared_link_skill_indices)


class KeyboardMonitorThread(QThread):
    """
    QThread를 상속한 키보드 모니터링 클래스
    """

    # 시그널 정의
    key_pressed = pyqtSignal(str)  # 키가 눌렸을 때
    macro_toggle = pyqtSignal(bool)  # 매크로 상태 변경
    link_skill_triggered = pyqtSignal(dict)  # 연계스킬 트리거

    def __init__(self, shared_data: SharedData):
        super().__init__()
        self.shared_data: SharedData = shared_data
        self.running = True

        # 키 상태 추적 변수
        self.pressed_keys = set()
        self.any_key_pressed = False

        # 키보드 리스너
        self.listener = None

    def on_press(self, key):
        """키가 눌렸을 때 호출되는 콜백"""
        try:
            # 일반 키의 경우
            if hasattr(key, "char") and key.char:
                self.pressed_keys.add(key.char.lower())
                self.key_pressed.emit(key.char.lower())
            else:
                # 특수 키의 경우
                key_name = str(key).replace("Key.", "")
                self.pressed_keys.add(key_name)
                self.key_pressed.emit(key_name)
            self.any_key_pressed = True
        except AttributeError:
            # 알 수 없는 키의 경우
            key_name = str(key)
            self.pressed_keys.add(key_name)
            self.key_pressed.emit(key_name)
            self.any_key_pressed = True

    def on_release(self, key):
        """키가 떼어졌을 때 호출되는 콜백"""
        try:
            # 일반 키의 경우
            if hasattr(key, "char") and key.char:
                self.pressed_keys.discard(key.char.lower())
            else:
                # 특수 키의 경우
                self.pressed_keys.discard(str(key).replace("Key.", ""))
        except AttributeError:
            # 알 수 없는 키의 경우
            self.pressed_keys.discard(str(key))

    def is_key_pressed(self, key_name: str) -> bool:
        """특정 키가 눌려있는지 확인"""
        # 키 이름을 소문자로 변환하여 확인
        key_lower = key_name.lower()

        # 특수 키 매핑
        special_keys = {
            "space": "space",
            "enter": "enter",
            "shift": "shift",
            "ctrl": "ctrl",
            "alt": "alt",
            "tab": "tab",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "page_up": "page_up",
            "page_down": "page_down",
        }

        if key_lower in special_keys:
            return special_keys[key_lower] in self.pressed_keys
        else:
            return key_lower in self.pressed_keys

    def run(self):
        """QThread의 메인 실행 함수"""
        # 키보드 리스너 시작
        self.listener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release
        )
        self.listener.start()

        while self.running:
            # 매크로 실행중일 때 아무 키보드 입력이 있으면 잠수 시간 초기화
            if self.shared_data.is_activated and self.any_key_pressed:
                self.shared_data.afk_started_time = time.time()
                self.any_key_pressed = False  # 플래그 리셋

            # 매크로 시작/중지
            start_key = self.shared_data.KEY_DICT.get(
                self.shared_data.start_key, self.shared_data.start_key
            )
            if self.is_key_pressed(start_key):
                # 매크로 상태 토글
                new_state = not self.shared_data.is_activated
                self.shared_data.is_activated = new_state
                self.macro_toggle.emit(new_state)

                if new_state:
                    # 매크로 번호 증가
                    self.shared_data.loop_num += 1
                    # 선택된 아이템 슬롯을 모르는 상태(-1)로 설정
                    self.shared_data.selected_item_slot = -1
                    # 매크로 쓰레드 시작
                    Thread(
                        target=running_macro_thread,
                        args=[self.shared_data, self.shared_data.loop_num],
                    ).start()

                # 매크로 실행/중지 이후에는 잠시 키 입력 무시
                time.sleep(0.5 * self.shared_data.SLEEP_COEFFICIENT_NORMAL)
                continue

            # 연계스킬 사용
            for link_skill in self.shared_data.link_skills:
                # 연계스킬 키가 눌렸다면
                link_key = self.shared_data.KEY_DICT.get(
                    link_skill["key"], link_skill["key"]
                )
                if link_key and self.is_key_pressed(link_key):
                    # 연계스킬에 사용되는 스킬 이름들
                    skills: list[str] = [
                        skill["name"] for skill in link_skill["skills"]
                    ]

                    # 연계스킬에 필요한 스킬이 모두 장착되어 있는지 확인
                    if all(
                        skill in self.shared_data.equipped_skills for skill in skills
                    ):
                        # 연계스킬 트리거 시그널 발생
                        self.link_skill_triggered.emit(link_skill)
                        # 연계스킬 쓰레드 시작
                        Thread(
                            target=useLinkSkill,
                            args=[
                                self.shared_data,
                                link_skill,
                                self.shared_data.loop_num,
                            ],
                        ).start()
                        break
            else:
                # 연계스킬도 실행되지 않았으면 0.05초 슬립
                time.sleep(0.05 * self.shared_data.SLEEP_COEFFICIENT_NORMAL)
                continue

            # 연계스킬이 실행되었으면 0.25초 슬립
            time.sleep(0.25 * self.shared_data.SLEEP_COEFFICIENT_NORMAL)

    def stop(self):
        """쓰레드 종료"""
        self.running = False
        if self.listener:
            self.listener.stop()
        self.quit()
        self.wait()
