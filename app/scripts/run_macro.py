from __future__ import annotations

import copy
import time
import keyboard as kb
import pyautogui as pag
from threading import Thread
from typing import TYPE_CHECKING

from .misc import convert7to5


if TYPE_CHECKING:
    from .shared_data import SharedData


print_info = False  # 디버깅용


def check_kb_pressed(shared_data: SharedData):
    while True:
        key = kb.read_key()
        convertedKey = shared_data.KEY_DICT[key] if key in shared_data.KEY_DICT else key

        # 링크스킬에 사용되는 키 리스트
        linkKeys = []
        for i in shared_data.link_skills:
            if i["keyType"] == 1:
                linkKeys.append(i["key"])

        if shared_data.is_activated:
            shared_data.afkTime0 = time.time()

        # 매크로 시작/중지
        if convertedKey == shared_data.startKey:
            if shared_data.is_activated:  # On -> Off
                shared_data.is_activated = False

                # self.setWindowIcon(self.icon)  # 윈도우 아이콘 변경 (자주 변경하면 중지됨)

            else:  # Off -> On
                shared_data.is_activated = True

                # self.setWindowIcon(self.icon_on)  # 윈도우 아이콘 변경 (자주 변경하면 중지됨)

                shared_data.loop_num += 1
                shared_data.selected_item_slot = -1
                Thread(
                    target=runMacro, args=[shared_data, shared_data.loop_num]
                ).start()

            time.sleep(0.5 * shared_data.SLEEP_COEFFICIENT_NORMAL)

        # 연계스킬 사용
        elif convertedKey in linkKeys and not shared_data.is_activated:
            for i in range(len(linkKeys)):
                if convertedKey == linkKeys[i]:
                    skills = [
                        shared_data.link_skills[i]["skills"][num][0]
                        for num in range(len(shared_data.link_skills[i]["skills"]))
                    ]

                    canStart = True
                    for skill in skills:
                        if not skill in shared_data.equipped_skills:
                            canStart = False
                            break

                    if canStart:
                        Thread(
                            target=useLinkSkill,
                            args=[shared_data, i, shared_data.loop_num],
                        ).start()

            time.sleep(0.25 * shared_data.SLEEP_COEFFICIENT_NORMAL)


def runMacro(shared_data: SharedData, loop_num):
    """
    매크로 메인 쓰레드
    """

    initMacro(shared_data, print_info=print_info)

    # 스킬 쿨타임 타이머 : [time] * 6  # 사용한 시간
    shared_data.skillCoolTimers = [None] * shared_data.USABLE_SKILL_COUNT[
        shared_data.serverID
    ]

    # 스킬 사용 가능 횟수 : [3, 2, 2, 1, 3, 3]
    shared_data.availableSkillCount = [
        shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][shared_data.jobID][
            shared_data.equipped_skills[i]
        ]
        for i in range(shared_data.USABLE_SKILL_COUNT[shared_data.serverID])
    ]

    # 스킬 쿨타임 쓰레드
    Thread(
        target=updateSkillCooltime, args=[shared_data, loop_num], daemon=True
    ).start()

    # 매크로 클릭 쓰레드
    if shared_data.activeMouseClickSlot:
        Thread(target=macroClick, args=[shared_data, loop_num], daemon=True).start()

    # shared_data.startTime = time.time()
    # usedSkillList = []

    while (
        shared_data.is_activated and shared_data.loop_num == loop_num
    ):  # 매크로 작동중일 때
        addTaskList(shared_data)  # taskList에 사용 가능한 스킬 추가
        usedSkill = useSkill(
            shared_data, loop_num
        )  # 스킬 사용하고 시간, 사용한 스킬 리턴. skill: slot

        # 잠수면 매크로 중지
        if shared_data.IS_AFK_ENABLED:
            if time.time() - shared_data.afkTime0 >= 10:
                shared_data.is_activated = False

        # 스킬 사용 안했으면 슬립 (useSkill에서 슬립을 안함)
        if usedSkill == None:
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


def macroClick(shared_data: SharedData, loopNum):
    while shared_data.is_activated and shared_data.loop_num == loopNum:
        pag.click()

        time.sleep(shared_data.delay * 0.001)


def updateSkillCooltime(shared_data: SharedData, loopNum):
    startTime = time.perf_counter()

    i = 0
    while shared_data.is_activated and shared_data.loop_num == loopNum:
        i += 1

        for skill in range(shared_data.USABLE_SKILL_COUNT[shared_data.serverID]):  # 0~6
            if (
                shared_data.availableSkillCount[skill]
                < shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][
                    shared_data.jobID
                ][shared_data.equipped_skills[skill]]
            ) and (  # 스킬 사용해서 쿨타임 기다리는 중이면
                ((time.time() - shared_data.skillCoolTimers[skill]) * 100)
                >= int(
                    shared_data.SKILL_COOLTIME_LIST[shared_data.serverID][
                        shared_data.jobID
                    ][shared_data.equipped_skills[skill]]
                    * (100 - shared_data.cooltimeReduce)
                )
            ):  # 쿨타임이 지나면
                shared_data.preparedSkillList[2].append(skill)  # 대기열에 추가
                shared_data.availableSkillCount[skill] += 1  # 사용 가능 횟수 증가

                # print(
                #     f"{time.time() - self.startTime:.3f} - {skill} {time.time() - self.skillCoolTimers[skill]}"
                # )

                shared_data.skillCoolTimers[skill] = time.time()  # 쿨타임 초기화

        time.sleep(shared_data.UNIT_TIME * i - (time.perf_counter() - startTime))


def initMacro(shared_data: SharedData, print_info=False):
    shared_data.selected_item_slot = -1
    shared_data.afkTime0 = time.time()

    shared_data.preparedSkillList = [  # 0~5
        [
            i
            for i in range(6)
            if not shared_data.ifUseSkill[shared_data.equipped_skills[i]]
            and shared_data.equipped_skills[i] != -1
        ],
        [
            i
            for i in range(6)
            if shared_data.ifUseSkill[shared_data.equipped_skills[i]]
            and shared_data.equipped_skills[i] != -1
        ],
        [],  # append 대기
    ]
    shared_data.preparedSkillCountList = [  # 0~5
        [
            shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][shared_data.jobID][
                shared_data.equipped_skills[i]
            ]
            for i in range(6)
            if not shared_data.ifUseSkill[shared_data.equipped_skills[i]]
            and shared_data.equipped_skills[i] != -1
        ],
        [
            shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][shared_data.jobID][
                shared_data.equipped_skills[i]
            ]
            for i in range(6)
            if shared_data.ifUseSkill[shared_data.equipped_skills[i]]
            and shared_data.equipped_skills[i] != -1
        ],
    ]
    shared_data.preparedSkillComboList = [
        shared_data.comboCount[shared_data.equipped_skills[i]] for i in range(6)
    ]  # 0~5

    # 개별 우선순위 -> 등록 순서
    shared_data.skillSequences = []  # 0~5 in self.equipped_skills
    # for i in self.link_skills:  # 연계스킬 메인1
    #     if not i[0]:
    #         self.skillSequences.append(self.convert7to5(i[2][0][0]))
    # for j, k in enumerate(self.equipped_skills):
    #     if k == i[2][0][0]:
    #         self.skillSequences.append(j)
    # print(self.skillSequences)
    for i in range(1, 7):
        for j, k in enumerate(shared_data.skill_priority):  # 0~7, 0~5
            if k == i:
                x = convert7to5(shared_data, j)
                if (
                    not (x in shared_data.skillSequences)
                    # and x in self.preparedSkillList[1]
                ):
                    shared_data.skillSequences.append(x)
                # print(f"i: {i}, j: {j}, k: {k}")
                # for x, y in enumerate(self.equipped_skills):  # x: 0~5, y: 0~7
                #     if y == j and not (x in self.skillSequences):
                #         self.skillSequences.append(x)
                # print(f"j: {j}, x: {x}, y: {y}")
                # self.skillSequences.append(self.equipped_skills[j])
    # print(self.skillSequences)
    for i in range(6):
        if (
            not (i in shared_data.skillSequences)
            and i in shared_data.preparedSkillList[1]
        ):
            shared_data.skillSequences.append(i)

    shared_data.usinglink_skills = []
    shared_data.usingLinkSkillComboList = []
    for i in shared_data.link_skills:
        if i["useType"] == 0:
            shared_data.usinglink_skills.append([])
            shared_data.usingLinkSkillComboList.append([])
            for j in i["skills"]:
                x = convert7to5(shared_data, j[0])
                # if not (x in self.requirelink_skills[-1]):
                shared_data.usinglink_skills[-1].append(x)
                shared_data.usingLinkSkillComboList[-1].append(j[1])

    shared_data.linkSkillRequirementList = []
    shared_data.linkSkillComboRequirementList = []
    for i, j in enumerate(shared_data.usinglink_skills):
        shared_data.linkSkillRequirementList.append([])
        shared_data.linkSkillComboRequirementList.append([])
        for x, y in enumerate(j):
            if not y in shared_data.linkSkillRequirementList[-1]:
                shared_data.linkSkillRequirementList[-1].append(y)
                shared_data.linkSkillComboRequirementList[-1].append(
                    shared_data.usingLinkSkillComboList[i][x]
                )
            else:
                for k, l in enumerate(shared_data.linkSkillRequirementList[-1]):
                    if l == y:
                        shared_data.linkSkillComboRequirementList[-1][
                            k
                        ] += shared_data.usingLinkSkillComboList[i][x]

    shared_data.preparedlink_skills = list(range(len(shared_data.usinglink_skills)))

    shared_data.task_list = []

    if print_info:
        printMacroInfo(shared_data, brief=False)


def useSkill(shared_data: SharedData, loopNum):

    def press(key):
        if shared_data.is_activated and shared_data.loop_num == loopNum:
            kb.press(key)

    def click():
        if shared_data.is_activated and shared_data.loop_num == loopNum:
            pag.click()

    def use(skill):
        if (
            shared_data.availableSkillCount[skill]
            == shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][
                shared_data.jobID
            ][shared_data.equipped_skills[skill]]
        ):
            shared_data.skillCoolTimers[skill] = (
                time.time()
            )  # 스킬 스택이 모두 찬 상태일 때

        shared_data.availableSkillCount[skill] -= 1

    if len(shared_data.task_list) != 0:
        skill = shared_data.task_list[0][0]  # skill = slot
        doClick = shared_data.task_list[0][1]  # T, F
        key = shared_data.skillKeys[skill]
        key = shared_data.KEY_DICT[key] if key in shared_data.KEY_DICT else key

        if shared_data.selected_item_slot != skill:
            if doClick:  # press -> delay -> click => use
                press(key)
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )
                use(skill)
                click()
                shared_data.selected_item_slot = skill
            else:  # press => use
                use(skill)
                press(key)
                shared_data.selected_item_slot = skill
        else:
            if doClick:  # click => use
                use(skill)
                click()
            else:  # press => use
                use(skill)
                press(key)

        shared_data.task_list.pop(0)

        # print(
        #     f"{time.time() - self.startTime - pag.PAUSE if doClick else time.time() - self.startTime:.3f} - {skill}"
        # )

        sleepTime = (
            shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL - pag.PAUSE
            if doClick
            else shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
        )
        time.sleep(sleepTime)
        return skill
    else:
        return None


def useLinkSkill(shared_data: SharedData, num, loopNum):
    def press(key):
        if shared_data.loop_num == loopNum:
            kb.press(key)

    def click():
        if shared_data.loop_num == loopNum:
            pag.click()

    def useSkill(slot):
        skill = taskList[0][0]  # skill = slot
        clickTF = taskList[0][1]  # T, F
        key = shared_data.skillKeys[skill]
        key = shared_data.KEY_DICT[key] if key in shared_data.KEY_DICT else key

        if slot != skill:
            if clickTF:
                press(key)
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )
                click()
                slot = skill
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )
            else:
                press(key)
                slot = skill
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )
        else:
            if clickTF:
                click()
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )
            else:
                press(key)
                time.sleep(
                    shared_data.delay * 0.001 * shared_data.SLEEP_COEFFICIENT_NORMAL
                )

        taskList.pop(0)

        return slot

    slot = -1
    taskList = []
    for i in shared_data.link_skills[num]["skills"]:
        for _ in range(i[1]):
            taskList.append(
                [
                    convert7to5(shared_data, i[0]),
                    shared_data.IS_SKILL_CASTING[shared_data.serverID][
                        shared_data.jobID
                    ][i[0]],
                ]
            )
    for i in range(len(taskList)):
        slot = useSkill(slot)


def addTaskList(shared_data: SharedData, print_info=False):
    # append
    lCopy = copy.deepcopy(shared_data.preparedSkillList)
    for skill in lCopy[2]:
        if shared_data.ifUseSkill[shared_data.equipped_skills[skill]]:
            if skill in lCopy[1]:
                for i in range(len(lCopy[1])):
                    if skill == lCopy[1][i]:
                        shared_data.preparedSkillCountList[1][i] += 1
            else:
                shared_data.preparedSkillList[1].append(skill)
                shared_data.preparedSkillCountList[1].append(1)
        else:
            if skill in lCopy[0]:
                for i in range(len(lCopy[0])):
                    if skill == lCopy[0][i]:
                        shared_data.preparedSkillCountList[0][i] += 1
            else:
                shared_data.preparedSkillList[0].append(skill)
                shared_data.preparedSkillCountList[0].append(1)
    del shared_data.preparedSkillList[2][: len(lCopy[2])]

    # 준비된 연계스킬 리스트
    checkIsLinkReady(shared_data)
    # if print_info:
    #     print("준비된 연계스킬리스트:", shared_data.preparedlink_skills)

    # 연계스킬 사용
    while len(shared_data.preparedlink_skills) != 0:
        for j in range(
            len(shared_data.usinglink_skills[shared_data.preparedlink_skills[0]])
        ):
            skill = shared_data.usinglink_skills[shared_data.preparedlink_skills[0]][j]
            count = shared_data.usingLinkSkillComboList[
                shared_data.preparedlink_skills[0]
            ][j]

            for k in [0, 1]:
                # print(
                #     "i:",
                #     i,
                #     "skill:",
                #     skill,
                #     "self.preparedSkillList[k]:",
                #     self.preparedSkillList[k],
                # )
                if skill in shared_data.preparedSkillList[k]:
                    for idx in range(len(shared_data.preparedSkillList[k])):
                        if skill == shared_data.preparedSkillList[k][idx]:
                            for _ in range(count):
                                if shared_data.IS_SKILL_CASTING[shared_data.serverID][
                                    shared_data.jobID
                                ][shared_data.equipped_skills[skill]]:
                                    shared_data.task_list.append(
                                        [skill, True]
                                    )  # skill: k, click: True
                                else:
                                    shared_data.task_list.append(
                                        [skill, False]
                                    )  # skill: k, click: False
                                shared_data.preparedSkillCountList[k][idx] -= 1
                                # print(
                                #     "count: ",
                                #     count,
                                #     "1준비된 스킬 개수 리스트:",
                                #     self.preparedSkillCountList,
                                # )
        checkIsLinkReady(shared_data)
    shared_data.preparedlink_skills = []
    reloadPreparedSkillList(shared_data, print_info=print_info)

    # 준비된 스킬 정렬순서대로 사용
    for i in shared_data.skillSequences:
        tempL = []
        for x in range(len(shared_data.linkSkillRequirementList)):
            for y in shared_data.linkSkillRequirementList[x]:
                tempL.append(y)  # 연계스킬 사용중인 스킬 전부 모으기

        if (
            (
                i in shared_data.preparedSkillList[0]
                or i in shared_data.preparedSkillList[1]
            )
            and i in tempL
            and shared_data.ifUseSole[shared_data.equipped_skills[i]]
        ):
            for x in [0, 1]:
                for j, k in enumerate(shared_data.preparedSkillList[x]):
                    if i == k:
                        while shared_data.preparedSkillCountList[x][j] >= 1:
                            if shared_data.IS_SKILL_CASTING[shared_data.serverID][
                                shared_data.jobID
                            ][shared_data.equipped_skills[k]]:
                                shared_data.task_list.append(
                                    [k, True]
                                )  # skill: k, click: True
                            else:
                                shared_data.task_list.append(
                                    [k, False]
                                )  # skill: k, click: False
                            shared_data.preparedSkillCountList[x][j] -= 1
                            # print(
                            #     "2준비된 스킬 개수 리스트:",
                            #     self.preparedSkillCountList,
                            # )
        if (
            i in shared_data.preparedSkillList[1]
            and not (i in tempL)
            and shared_data.ifUseSkill[shared_data.equipped_skills[i]]
        ):
            for j, k in enumerate(shared_data.preparedSkillList[1]):
                if i == k:
                    while (
                        shared_data.preparedSkillCountList[1][j]
                        >= shared_data.preparedSkillComboList[i]
                    ):
                        for _ in range(shared_data.preparedSkillComboList[i]):
                            if shared_data.IS_SKILL_CASTING[shared_data.serverID][
                                shared_data.jobID
                            ][shared_data.equipped_skills[k]]:
                                shared_data.task_list.append(
                                    [k, True]
                                )  # skill: k, click: True
                            else:
                                shared_data.task_list.append(
                                    [k, False]
                                )  # skill: k, click: False
                            shared_data.preparedSkillCountList[1][j] -= 1
                            # print(
                            #     "2준비된 스킬 개수 리스트:",
                            #     self.preparedSkillCountList,
                            # )
    reloadPreparedSkillList(shared_data, print_info=print_info)


def checkIsLinkReady(shared_data: SharedData):
    shared_data.preparedlink_skills = []
    for x in range(len(shared_data.linkSkillRequirementList)):
        ready = [False] * len(shared_data.linkSkillRequirementList[x])

        for y in range(len(shared_data.linkSkillRequirementList[x])):
            skill = shared_data.linkSkillRequirementList[x][y]
            count = shared_data.linkSkillComboRequirementList[x][y]
            for i in [0, 1]:
                if skill in shared_data.preparedSkillList[i]:
                    for j in range(len(shared_data.preparedSkillList[i])):
                        if skill == shared_data.preparedSkillList[i][j]:
                            if count <= shared_data.preparedSkillCountList[i][j]:
                                ready[y] = True

        if not False in ready:
            shared_data.preparedlink_skills.append(x)


def reloadPreparedSkillList(shared_data: SharedData, print_info=False):
    if print_info:
        printMacroInfo(shared_data, brief=True)
        print("\n")

    for num in [0, 1]:
        for i in range(len(shared_data.preparedSkillList[num]) - 1, -1, -1):
            if shared_data.preparedSkillCountList[num][i] == 0:
                shared_data.preparedSkillList[num].pop(i)
                shared_data.preparedSkillCountList[num].pop(i)
                # print("reload")


def printMacroInfo(shared_data: SharedData, brief=False):
    if brief:
        print("테스크 리스트:", shared_data.task_list)  # 사용여부 x, 사용여부 o
        print(
            "준비된 스킬 리스트:", shared_data.preparedSkillList
        )  # 사용여부 x, 사용여부 o
        print(
            "준비된 스킬 개수 리스트:", shared_data.preparedSkillCountList
        )  # 사용여부 x, 사용여부 o
        print("준비된 연계스킬리스트:", shared_data.preparedlink_skills)
    else:
        print(
            "준비된 스킬 리스트:", shared_data.preparedSkillList
        )  # 사용여부 x, 사용여부 o
        print(
            "준비된 스킬 개수 리스트:", shared_data.preparedSkillCountList
        )  # 사용여부 x, 사용여부 o
        print("스킬 콤보 리스트:", shared_data.preparedSkillComboList)  # 사용여부 o
        print("스킬 정렬 순서:", shared_data.skillSequences)
        print("연계스킬 스킬 리스트:", shared_data.usinglink_skills)
        print("연계스킬 스킬 콤보 리스트:", shared_data.usingLinkSkillComboList)
        print("연계스킬에 필요한 스킬 리스트:", shared_data.linkSkillRequirementList)
        print(
            "연계스킬에 필요한 스킬 콤보 리스트:",
            shared_data.linkSkillComboRequirementList,
        )
        print("준비된 연계스킬리스트:", shared_data.preparedlink_skills)
