from __future__ import annotations

import datetime
import json
import os
from dataclasses import asdict
from typing import TYPE_CHECKING

from app.scripts.misc import (
    get_available_skills,
    get_every_skills,
    get_skill_details,
    set_var_to_ClassVar,
)

if TYPE_CHECKING:
    from .shared_data import SharedData


data_version = 3

local_appdata: str = os.environ.get("LOCALAPPDATA", default="")

data_path_legacy = "C:\\PDFiles"
file_dir_legacy = "C:\\PDFiles\\PDSkillMacro.json"

if local_appdata:
    data_path: str = os.path.join(local_appdata, "ProDays")
    file_dir: str = os.path.join(data_path, "SkillMacro.json")

else:
    # 이전에 사용하던 경로 "C:\\PDFiles\\PDSkillMacro.json"
    data_path: str = data_path_legacy
    file_dir: str = file_dir_legacy


def load_data(shared_data: SharedData, num: int = -1) -> None:
    """
    실행, 탭 변경 시 데이터 로드

    :param shared_data: SharedData 인스턴스
    :param num: 탭 번호, -1이면 최근 탭
    """

    try:
        # 파일이 존재하지 않으면 데이터 생성
        if not os.path.isfile(file_dir):
            create_default_data(shared_data=shared_data)

        # 데이터 로드
        with open(file_dir, "r", encoding="UTF8") as f:
            json_object: dict = json.load(f)

        # num이 -1이면 최근 탭, 아니면 해당 탭 번호
        if num == -1:
            shared_data.recent_preset = json_object["recentPreset"]
        else:
            shared_data.recent_preset = num

        # 데이터를 불러올 탭의 데이터
        data: dict = json_object["preset"][shared_data.recent_preset]

        # 탭 이름 설정
        set_var_to_ClassVar(
            shared_data.tab_names, [preset["name"] for preset in json_object["preset"]]
        )

        # 장착된 스킬들 불러오기
        set_var_to_ClassVar(shared_data.equipped_skills, data["skills"]["activeSkills"])
        # 스킬 키 설정
        set_var_to_ClassVar(shared_data.skill_keys, data["skills"]["skillKeys"])

        # 서버 ID와 직업 ID 설정
        shared_data.server_ID = data["settings"]["serverID"]
        shared_data.job_ID = data["settings"]["jobID"]

        # 딜레이 설정
        shared_data.delay_type = data["settings"]["delay"][0]
        shared_data.delay_input = data["settings"]["delay"][1]

        # 딜레이 설정 타입에 따라 딜레이 값 설정
        if shared_data.delay_type == 0:
            shared_data.delay = shared_data.DEFAULT_DELAY
        else:
            shared_data.delay = shared_data.delay_input

        # 쿨타임 감소 스탯 설정
        shared_data.cooltime_reduction_type = data["settings"]["cooltime"][0]
        shared_data.cooltime_reduction_input = data["settings"]["cooltime"][1]

        # 쿨타임 감소 스탯 타입에 따라 쿨타임 감소 값 설정
        if shared_data.cooltime_reduction_type == 0:
            shared_data.cooltime_reduction = shared_data.DEFAULT_COOLTIME_REDUCTION
        else:
            shared_data.cooltime_reduction = shared_data.cooltime_reduction_input

        # 시작 키
        shared_data.start_key_type = data["settings"]["startKey"][0]
        shared_data.start_key_input = data["settings"]["startKey"][1]

        # 시작 키 타입에 따라 시작 키 값 설정
        if shared_data.start_key_type == 0:
            shared_data.start_key = shared_data.DEFAULT_START_KEY
        else:
            shared_data.start_key = shared_data.start_key_input

        # 마우스 클릭 설정
        shared_data.mouse_click_type = data["settings"]["mouseClickType"]

        # 스킬 사용설정
        # 사용 여부
        set_var_to_ClassVar(
            shared_data.is_use_skill,
            {
                skill: setting["is_use_skill"]
                for skill, setting in data["usageSettings"].items()
            },
        )
        # 단독 사용
        set_var_to_ClassVar(
            shared_data.is_use_sole,
            {
                skill: setting["is_use_sole"]
                for skill, setting in data["usageSettings"].items()
            },
        )
        # 콤보 횟수
        set_var_to_ClassVar(
            shared_data.combo_count,
            {
                skill: setting["combo_count"]
                for skill, setting in data["usageSettings"].items()
            },
        )
        # 스킬 우선순위
        set_var_to_ClassVar(
            shared_data.skill_priority,
            {
                skill: setting["skill_priority"]
                for skill, setting in data["usageSettings"].items()
            },
        )

        # 링크 스킬 불러오기
        set_var_to_ClassVar(shared_data.link_skills, data["linkSettings"])

        # 시뮬레이션 데이터 불러오기
        # 스탯 정보
        stats: dict[str, int] = data["info"]["stats"]
        for stat, value in stats.items():
            shared_data.info_stats.set_stat_from_name(stat=stat, value=value)

        # 스킬 레벨 정보
        set_var_to_ClassVar(shared_data.info_skill_levels, data["info"]["skill_levels"])
        # 시뮬레이션 상세 정보
        set_var_to_ClassVar(shared_data.info_sim_details, data["info"]["sim_details"])

    except Exception:
        # 오류 발생 시 백업 데이터로 복원
        backup_data()

        # 기본 데이터 생성
        create_default_data(shared_data=shared_data)

        # 데이터 다시 로드
        load_data(shared_data=shared_data)


def create_default_data(shared_data: SharedData) -> None:
    """
    오류 발생 또는 최초 실행 시 데이터 생성
    """

    jsonObject: dict = {
        "version": data_version,
        "recentPreset": 0,
        "preset": [
            get_default_preset(shared_data=shared_data),
        ],
    }

    # 폴더가 없으면 생성
    os.makedirs(data_path, exist_ok=True)

    # 저장
    with open(file_dir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False, indent=4)


def save_data(shared_data: SharedData) -> None:
    """
    데이터 저장
    """

    with open(file_dir, "r", encoding="UTF8") as f:
        jsonObject: dict = json.load(f)

    jsonObject["recentPreset"] = shared_data.recent_preset
    data: dict = jsonObject["preset"][shared_data.recent_preset]

    data["name"] = shared_data.tab_names[shared_data.recent_preset]

    data["skills"]["activeSkills"] = shared_data.equipped_skills
    data["skills"]["skillKeys"] = shared_data.skill_keys

    data["settings"]["serverID"] = shared_data.server_ID
    data["settings"]["jobID"] = shared_data.job_ID
    data["settings"]["delay"][0] = shared_data.delay_type
    data["settings"]["delay"][1] = shared_data.delay_input
    data["settings"]["cooltime"][0] = shared_data.cooltime_reduction_type
    data["settings"]["cooltime"][1] = shared_data.cooltime_reduction_input
    data["settings"]["startKey"][0] = shared_data.start_key_type
    data["settings"]["startKey"][1] = shared_data.start_key_input
    data["settings"]["mouseClickType"] = shared_data.mouse_click_type

    # 스킬 사용 설정 저장
    for job in shared_data.skill_data[shared_data.server_ID]["jobs"].keys():
        for skill in shared_data.skill_data[shared_data.server_ID]["jobs"][job][
            "skills"
        ]:
            data["usageSettings"][skill] = {
                "is_use_skill": shared_data.is_use_skill[skill],
                "is_use_sole": shared_data.is_use_sole[skill],
                "combo_count": shared_data.combo_count[skill],
                "skill_priority": shared_data.skill_priority[skill],
            }

    data["linkSettings"] = shared_data.link_skills

    data["info"]["stats"] = asdict(shared_data.info_stats)
    data["info"]["skill_levels"] = shared_data.info_skill_levels
    data["info"]["sim_details"] = shared_data.info_sim_details

    # 저장
    with open(file_dir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False, indent=4)

    print("Data saved successfully.")


def remove_preset(num: int) -> None:
    """
    탭 제거시 데이터 삭제
    """

    with open(file_dir, "r", encoding="UTF8") as f:
        jsonObject: dict = json.load(f)

    jsonObject["preset"].pop(num)

    with open(file_dir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False, indent=4)


def add_preset(shared_data: SharedData) -> None:
    """
    탭 추가시 데이터 생성
    """

    with open(file_dir, "r", encoding="UTF8") as f:
        jsonObject: dict = json.load(f)

    jsonObject["preset"].append(get_default_preset(shared_data=shared_data))

    with open(file_dir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False, indent=4)


def get_default_preset(shared_data: SharedData) -> dict:
    """
    기본 프리셋 데이터 생성
    """

    return {
        "name": "스킬 매크로",
        "skills": {
            "activeSkills": [""]
            * shared_data.USABLE_SKILL_COUNT[shared_data.DEFAULT_SERVER_ID],
            "skillKeys": [
                str(2 + i)
                for i in range(
                    shared_data.USABLE_SKILL_COUNT[shared_data.DEFAULT_SERVER_ID],
                )
            ],
        },
        "settings": {
            "serverID": shared_data.DEFAULT_SERVER_ID,
            "jobID": shared_data.DEFAULT_JOB_ID,
            "delay": [0, shared_data.DEFAULT_DELAY],
            "cooltime": [0, shared_data.DEFAULT_COOLTIME_REDUCTION],
            "startKey": [0, shared_data.DEFAULT_START_KEY],
            "mouseClickType": 0,
        },
        "usageSettings": {
            skill: {
                "is_use_skill": True,
                "is_use_sole": False,
                "combo_count": get_skill_details(
                    shared_data=shared_data, skill_name=skill
                )["max_combo_count"],
                "skill_priority": 0,
            }
            for skill in get_every_skills(shared_data=shared_data)
        },
        "linkSettings": [],
        "info": {
            "stats": {stat: 0 for stat in shared_data.STATS.keys()},
            "skill_levels": {
                skill: 1 for skill in get_every_skills(shared_data=shared_data)
            },
            "sim_details": {info: 0 for info in shared_data.SIM_DETAILS.keys()},
        },
    }


def update_data(shared_data: SharedData) -> None:
    """
    데이터 업데이트
    """

    def update_1to2() -> None:
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

    def update_2to3() -> None:
        # 폴더가 없으면 생성
        os.makedirs(data_path, exist_ok=True)

        jsonObject["version"] = 3

        for i in range(len(jsonObject["preset"])):
            # activeSkills 업데이트
            skills: list[int] = jsonObject["preset"][i]["skills"]["activeSkills"]

            server_id: int = jsonObject["preset"][i]["settings"]["serverID"]
            job_id: int = jsonObject["preset"][i]["settings"]["jobID"]

            server_name: str = shared_data.SERVERS[server_id]
            job_name: str = shared_data.JOBS[server_name][job_id]

            jsonObject["preset"][i]["skills"]["activeSkills"] = [
                (
                    ""
                    if skill == -1
                    else shared_data.skill_data[server_name]["jobs"][job_name][
                        "skills"
                    ][skill]
                )
                for skill in skills
            ]

            # serverID, jobID 업데이트
            jsonObject["preset"][i]["settings"]["serverID"] = server_name
            jsonObject["preset"][i]["settings"]["jobID"] = shared_data.JOBS[
                server_name
            ][job_id]

            shared_data.server_ID = server_name
            shared_data.job_ID = jsonObject["preset"][i]["settings"]["jobID"]

            # linkSettings 업데이트
            for j, link in enumerate(jsonObject["preset"][i]["linkSettings"]):
                # useType은 "auto", "manual"로 변경
                link["useType"] = "auto" if link["useType"] == 0 else "manual"

                # keyType -> useKey로 변경, bool로 변경
                link["useKey"] = bool(link.pop("keyType"))

                for k, skill_info in enumerate(link["skills"]):
                    skill = skill_info[0]
                    count = skill_info[1]

                    jsonObject["preset"][i]["linkSettings"][j]["skills"][k] = {
                        "skill_name": shared_data.skill_data[server_name]["jobs"][
                            job_name
                        ]["skills"][skill],
                        "count": count,
                    }

            ## usageSettings 업데이트
            # usageSettings는 스킬 이름에 대한 딕셔너리로 변경
            settings: list[list] = jsonObject["preset"][i]["usageSettings"]
            jsonObject["preset"][i]["usageSettings"] = {}

            # 기존에 저장된 데이터 변환
            for j in range(8):
                skill: str = get_available_skills(shared_data=shared_data)[j]
                jsonObject["preset"][i]["usageSettings"][skill] = {
                    "is_use_skill": settings[j][0],
                    "is_use_sole": settings[j][1],
                    "combo_count": settings[j][2],
                    "skill_priority": settings[j][3],
                }

            # skill_data에서 지금 서버의 모든 스킬에 대해 데이터 추가
            for skill in get_every_skills(shared_data=shared_data)[8:]:
                if skill not in jsonObject["preset"][i]["usageSettings"]:
                    jsonObject["preset"][i]["usageSettings"][skill] = {
                        "is_use_skill": True,
                        "is_use_sole": False,
                        "combo_count": get_skill_details(
                            shared_data=shared_data, skill_name=skill
                        )["max_combo_count"],
                        "skill_priority": 0,
                    }

            ## info 업데이트
            info: dict = jsonObject["preset"][i]["info"]

            # stats 업데이트
            jsonObject["preset"][i]["info"]["stats"] = {
                stat: info["stats"][j]
                for j, stat in enumerate(shared_data.STATS.keys())
            }

            # skills -> skill_levels, dict로 업데이트
            jsonObject["preset"][i]["info"]["skill_levels"] = {
                skill: info["skills"][j]
                for j, skill in enumerate(get_available_skills(shared_data=shared_data))
            } | {
                # 다른 직업들의 스킬 레벨을 1로 설정
                skill: 1
                for skill in get_every_skills(shared_data=shared_data)[8:]
            }
            # skills 키 삭제
            del jsonObject["preset"][i]["info"]["skills"]

            # simInfo -> sim_details, dict로 업데이트
            jsonObject["preset"][i]["info"]["sim_details"] = {
                detail: info["simInfo"][j]
                for j, detail in enumerate(shared_data.SIM_DETAILS.keys())
            }
            # simInfo 키 삭제
            del jsonObject["preset"][i]["info"]["simInfo"]

        with open(file_dir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f, ensure_ascii=False, indent=4)

    try:
        # 데이터가 있으면 불러오기
        if os.path.isfile(file_dir):
            with open(file_dir, "r", encoding="UTF8") as f:
                jsonObject: dict = json.load(f)

        # 데이터가 없고, 이전 경로 파일이 있으면 불러오기
        elif os.path.isfile(file_dir_legacy):
            with open(file_dir_legacy, "r", encoding="UTF8") as f:
                jsonObject: dict = json.load(f)

            # 이전 경로에 있는 파일 삭제
            files: list[str] = os.listdir(data_path_legacy)

            for file_name in files:
                file_path: str = os.path.join(data_path_legacy, file_name)
                os.remove(file_path)

            os.rmdir(data_path_legacy)

        # 데이터가 없으면 새로 생성
        else:
            create_default_data(shared_data=shared_data)

            return

        if "version" not in jsonObject:
            update_1to2()

        if jsonObject["version"] == 2:
            update_2to3()

    except Exception as e:
        print(f"Error occurred: {e}")

        backup_data()

        create_default_data(shared_data=shared_data)


def update_skill_data(shared_data: SharedData) -> None:
    # 파일 불러오기
    with open(file_dir, "r", encoding="UTF8") as f:
        jsonObject: dict = json.load(f)

    # skill_data에서 지금 서버의 모든 스킬에 대해 데이터 추가
    for i in range(len(jsonObject["preset"])):
        for skill in get_every_skills(shared_data=shared_data):
            # usageSettings
            # 현재 탭에 스킬이 없으면 추가
            if skill not in jsonObject["preset"][i]["usageSettings"]:
                # 기본값으로 설정
                jsonObject["preset"][i]["usageSettings"][skill] = {
                    "is_use_skill": True,
                    "is_use_sole": False,
                    "combo_count": get_skill_details(
                        shared_data=shared_data, skill_name=skill
                    )["max_combo_count"],
                    "skill_priority": 0,
                }

            # skill_levels
            if skill not in jsonObject["preset"][i]["info"]["skill_levels"]:
                jsonObject["preset"][i]["info"]["skill_levels"][skill] = 1

    # 저장
    with open(file_dir, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False, indent=4)


def backup_data() -> None:
    """
    데이터 백업
    """

    # 백업 폴더가 없으면 생성
    backup_path: str = os.path.join(data_path, "backup")
    os.makedirs(backup_path, exist_ok=True)

    # 백업 파일 경로 설정
    backup_file: str = os.path.join(
        backup_path,
        f"SkillMacro_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    # 파일이 존재하면 불러오기
    if os.path.isfile(file_dir):
        with open(file_dir, "r", encoding="UTF8") as f:
            jsonObject: dict = json.load(f)

    # 이전 경로에 있는 파일이 존재하면 불러오기
    elif os.path.isfile(file_dir_legacy):
        with open(file_dir_legacy, "r", encoding="UTF8") as f:
            jsonObject: dict = json.load(f)

    # 파일이 없으면 종료
    else:
        return

    # 백업 파일로 저장
    with open(backup_file, "w", encoding="UTF8") as f:
        json.dump(jsonObject, f, ensure_ascii=False, indent=4)


"""

data_version == 2:
- version 키 추가
- linkSettings의 type 키를 useType으로 변경
- linkSettings의 keyType 키를 추가하고 값은 1로 설정
- preset의 info 키 추가
- info의 stats, skills, simInfo 키 추가

data_version == 3:
- version 키를 3으로 변경

- 데이터 저장 경로 변경

- activeSkills을 스킬 번호에서 스킬 이름으로 변경

- serverID와 jobID를 번호에서 서버 이름과 직업 이름으로 변경

- linkSettings의 skills를 스킬 이름으로 변경
- linkSettings의 skills를 list[list]에서 list[dict]로 변경
- linkSettings의 useType을 int에서 str로 변경 ("auto", "manual")
- linkSettings의 keyType -> useKey로 변경, int에서 bool로 변경

- usageSettings을 list[list]에서 스킬 이름에 대한 딕셔너리로 변경

- info의 stats를 딕셔너리로 변경
- info의 skills(skill_levels)를 딕셔너리로 변경
- info의 simInfo(sim_details)를 딕셔너리로 변경
- info의 skills -> skill_levels로 변경, simInfo -> sim_details로 변경

"""
