from __future__ import annotations

import os
import json
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .shared_data import SharedData


dataVersion = 3

local_appdata = os.environ.get("LOCALAPPDATA", "")

if not local_appdata:
    raise EnvironmentError("LOCALAPPDATA environment variable is not set.")

data_path = os.path.join(local_appdata, "ProDays")
fileDir = os.path.join(data_path, "SkillMacro.json")

# 이전에 사용하던 경로 "C:\\PDFiles\\PDSkillMacro.json"
data_path_old = "C:\\PDFiles"
fileDir_old = "C:\\PDFiles\\PDSkillMacro.json"


def convertResourcePath(relative_path):
    """
    리소스 경로 변경
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(base_path)
    return os.path.join(base_path, relative_path)


def data_load(shared_data: SharedData, num=-1):
    """
    실행, 탭 변경 시 데이터 로드
    """

    try:
        if os.path.isfile(fileDir):
            with open(fileDir, "r", encoding="UTF8") as f:
                jsonObject = json.load(f)

                if num == -1:
                    shared_data.recentPreset = jsonObject["recentPreset"]
                else:
                    shared_data.recentPreset = num
                data = jsonObject["preset"][shared_data.recentPreset]

                ## name
                shared_data.tabNames = [
                    jsonObject["preset"][i]["name"]
                    for i in range(len(jsonObject["preset"]))
                ]

                ## skills
                shared_data.equipped_skills = data["skills"]["activeSkills"]
                shared_data.skillKeys = data["skills"]["skillKeys"]

                ## settings
                shared_data.serverID = data["settings"]["serverID"]
                shared_data.jobID = data["settings"]["jobID"]

                shared_data.activeDelaySlot = data["settings"]["delay"][0]
                shared_data.inputDelay = data["settings"]["delay"][1]
                if shared_data.activeDelaySlot == 0:
                    shared_data.delay = 150  # default delay
                else:
                    shared_data.delay = shared_data.inputDelay

                shared_data.activeCooltimeSlot = data["settings"]["cooltime"][0]
                shared_data.inputCooltime = data["settings"]["cooltime"][1]
                if shared_data.activeCooltimeSlot == 0:
                    shared_data.cooltimeReduce = 0
                else:
                    shared_data.cooltimeReduce = shared_data.inputCooltime

                shared_data.activeStartKeySlot = data["settings"]["startKey"][0]
                shared_data.inputStartKey = data["settings"]["startKey"][1]
                if shared_data.activeStartKeySlot == 0:
                    shared_data.startKey = "F9"
                else:
                    shared_data.startKey = shared_data.inputStartKey

                shared_data.activeMouseClickSlot = data["settings"]["mouseClickType"]

                ## usageSettings
                shared_data.ifUseSkill = [data["usageSettings"][i][0] for i in range(8)]
                shared_data.ifUseSole = [data["usageSettings"][i][1] for i in range(8)]
                shared_data.comboCount = [data["usageSettings"][i][2] for i in range(8)]
                shared_data.skill_priority = [
                    data["usageSettings"][i][3] for i in range(8)
                ]

                shared_data.link_skills = data["linkSettings"]

                ## info
                shared_data.info_stats = data["info"]["stats"]
                shared_data.info_skills = data["info"]["skills"]
                shared_data.info_simInfo = data["info"]["simInfo"]
        else:
            dataMake()
            data_load(shared_data)
    except:
        dataMake()
        data_load(shared_data)


def dataMake():
    """
    오류발생 또는 최초실행 시 데이터 생성
    """

    jsonObject = {
        "version": dataVersion,
        "recentPreset": 0,
        "preset": [
            {
                "name": "스킬 매크로",
                "skills": {
                    "activeSkills": [-1] * 6,
                    "skillKeys": ["2", "3", "4", "5", "6", "7"],
                },
                "settings": {
                    "serverID": 0,
                    "jobID": 0,
                    "delay": [0, 150],
                    "cooltime": [0, 0],
                    "startKey": [0, "F9"],
                    "mouseClickType": 0,
                },
                "usageSettings": [
                    [True, True, 3, 0],
                    [True, True, 2, 0],
                    [True, True, 2, 0],
                    [True, True, 1, 0],
                    [True, True, 3, 0],
                    [True, True, 1, 0],
                    [True, True, 1, 0],
                    [True, True, 3, 0],
                ],
                "linkSettings": [],
                "info": {
                    "stats": [0] * 18,
                    "skills": [1] * 8,
                    "simInfo": [1, 1, 100],
                },
            }
        ],
    }

    os.makedirs(data_path, exist_ok=True)  # 폴더가 없으면 생성

    with open(fileDir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False)


def dataSave(shared_data: SharedData):
    """
    데이터 저장
    """

    with open(fileDir, "r", encoding="UTF8") as f:
        jsonObject = json.load(f)

    jsonObject["recentPreset"] = shared_data.recentPreset
    data = jsonObject["preset"][shared_data.recentPreset]

    data["name"] = shared_data.tabNames[shared_data.recentPreset]

    data["skills"]["activeSkills"] = shared_data.equipped_skills
    data["skills"]["skillKeys"] = shared_data.skillKeys

    data["settings"]["serverID"] = shared_data.serverID
    data["settings"]["jobID"] = shared_data.jobID
    data["settings"]["delay"][0] = shared_data.activeDelaySlot
    data["settings"]["delay"][1] = shared_data.inputDelay
    data["settings"]["cooltime"][0] = shared_data.activeCooltimeSlot
    data["settings"]["cooltime"][1] = shared_data.inputCooltime
    data["settings"]["startKey"][0] = shared_data.activeStartKeySlot
    data["settings"]["startKey"][1] = shared_data.inputStartKey
    data["settings"]["mouseClickType"] = shared_data.activeMouseClickSlot

    for i in range(8):
        data["usageSettings"][i][0] = shared_data.ifUseSkill[i]
        data["usageSettings"][i][1] = shared_data.ifUseSole[i]
        data["usageSettings"][i][2] = shared_data.comboCount[i]
        data["usageSettings"][i][3] = shared_data.skill_priority[i]

    data["linkSettings"] = shared_data.link_skills

    data["info"]["stats"] = shared_data.info_stats
    data["info"]["skills"] = shared_data.info_skills
    data["info"]["simInfo"] = shared_data.info_simInfo

    with open(fileDir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False)


def dataRemove(num):
    """
    탭 제거시 데이터 삭제
    """

    with open(fileDir, "r", encoding="UTF8") as f:
        jsonObject = json.load(f)

    jsonObject["preset"].pop(num)

    with open(fileDir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False)


def dataAdd():
    """
    탭 추가시 데이터 생성
    """

    with open(fileDir, "r", encoding="UTF8") as f:
        jsonObject = json.load(f)

    jsonObject["preset"].append(
        {
            "name": "스킬 매크로",
            "skills": {
                "activeSkills": [-1] * 6,
                "skillKeys": ["2", "3", "4", "5", "6", "7"],
            },
            "settings": {
                "serverID": 0,
                "jobID": 0,
                "delay": [0, 150],
                "cooltime": [0, 0],
                "startKey": [0, "F9"],
                "mouseClickType": 0,
            },
            "usageSettings": [
                [True, True, 3, 0],
                [True, True, 2, 0],
                [True, True, 2, 0],
                [True, True, 1, 0],
                [True, True, 3, 0],
                [True, True, 1, 0],
                [True, True, 1, 0],
                [True, True, 3, 0],
            ],
            "linkSettings": [],
            "info": {
                "stats": [0] * 18,
                "skills": [1] * 8,
                "simInfo": [1, 1, 100],
            },
        }
    )

    with open(fileDir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False)


def data_update():
    """
    데이터 업데이트
    """

    def update_1to2():
        jsonObject["version"] = 2

        for i in range(len(jsonObject["preset"])):
            for j in range(len(jsonObject["preset"][i]["linkSettings"])):
                jsonObject["preset"][i]["linkSettings"][j]["useType"] = jsonObject[
                    "preset"
                ][i]["linkSettings"][j].pop("type")
                jsonObject["preset"][i]["linkSettings"][j]["keyType"] = 1

        for i in range(len(jsonObject["preset"])):
            jsonObject["preset"][i]["info"] = {}
            jsonObject["preset"][i]["info"]["stats"] = [0] * 18
            jsonObject["preset"][i]["info"]["skills"] = [1] * 8
            jsonObject["preset"][i]["info"]["simInfo"] = [1, 1, 100]

    def update_2to3():
        os.makedirs(data_path, exist_ok=True)  # 폴더가 없으면 생성

        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f, ensure_ascii=False)

    try:
        with open(fileDir, "r", encoding="UTF8") as f:
            jsonObject = json.load(f)

        # if jsonObject["version"] == 1:
        #     update_1to2()

        # with open(fileDir, "w", encoding="UTF8") as f:
        #     json.dump(jsonObject, f)

    except:
        with open(fileDir_old, "r", encoding="UTF8") as f:
            jsonObject = json.load(f)

        if not "version" in jsonObject:
            update_1to2()

        if jsonObject["version"] == 2:
            update_2to3()

        # 이전 경로에 있는 파일 삭제
        filelist = os.listdir(data_path_old)
        for filename in filelist:
            file_path = os.path.join(data_path_old, filename)
            os.remove(file_path)
        os.rmdir(data_path_old)
