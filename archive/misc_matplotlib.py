from __future__ import annotations

import os
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from PyQt6.QtGui import QFontDatabase, QFontMetrics, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton

from .custom_classes import CustomFont

if TYPE_CHECKING:
    from .shared_data import SharedData


def convert_skill_name_to_slot(skill_name: str) -> int:
    """
    스킬 이름을 슬롯 번호로 변환
    """

    return (
        app_state.macro.equipped_skills.index(skill_name)
        if skill_name in app_state.macro.equipped_skills
        else -1
    )


def is_key_used(key: str) -> bool:
    """
    키가 사용중인지 확인
    """

    # "\n"이 포함되어 있으면 "_"로 대체
    key = key.replace("\n", "_")

    # 사용중인 키 목록
    used_keys: list[str] = []

    # 시작 키
    if shared_data.start_key_type == 1:
        used_keys.append(shared_data.start_key_input)
    else:
        used_keys.append("F9")

    # 스킬 사용 키
    used_keys.extend(app_state.macro.skill_keys)

    # 연계 스킬 키
    used_keys.extend(
        [
            link_skill["key"]
            for link_skill in shared_data.link_skills
            if link_skill["keyType"] == 1
        ]
    )

    # if self.settingType == 3:
    #     usingKey.append(self.ButtonLinkKey1.text())

    # print(usingKey, key)

    return key in used_keys


def convert_resource_path(relative_path: str) -> str:
    """
    리소스 경로 변경
    """

    base_path: str = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(base_path)

    return os.path.join(base_path, relative_path)


def set_default_fonts() -> None:
    """
    기본 폰트 설정
    """

    # "나눔스퀘어라운드 ExtraBold"
    QFontDatabase.addApplicationFont(
        convert_resource_path("resources\\font\\NSR_B.ttf")
    )
    QFontDatabase.addApplicationFont(
        convert_resource_path("resources\\font\\NSR_EB.ttf")
    )
    QFontDatabase.addApplicationFont(
        convert_resource_path("resources\\font\\NotoSansKR-Regular.ttf")
    )

    font_path = convert_resource_path("resources\\font\\NotoSansKR-Regular.ttf")
    fm.fontManager.addfont(font_path)
    prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = prop.get_name()

    # print(QFontDatabase.families())


def get_skill_pixmap(skill_name: str, state: int = -1) -> QPixmap:
    """
    스킬 아이콘 반환

    skill == ""이면 빈 스킬 아이콘 반환
    state == -1이면 해당 스킬의 최대 카운트 반환, -2이면 비활성화 아이콘 반환
    """

    if not skill_name:
        return QPixmap(convert_resource_path(f"resources\\image\\emptySkill.png"))

    # count가 -1이면 shared_data에서 해당 스킬의 최대 카운트 가져오기
    if state == -1:
        state = get_skill_details(skill_name)["max_combo_count"]

    skill_id: int = get_available_skills(shared_data).index(skill_name)

    # state가 -2이면 비활성화 아이콘 반환
    return QPixmap(
        convert_resource_path(
            f"resources\\image\\skills\\{app_state.macro.server.id}\\{shared_data.job_ID}\\{skill_id}\\{state if state != -2 else 'off'}.png"
        )
    )


## 위젯 크기에 맞는 폰트로 변경
def adjust_font_size(
    widget: QPushButton | QLabel,
    text: str,
    maxSize: int,
    font_name="나눔스퀘어라운드 ExtraBold",
) -> None:
    # 텍스트 설정
    widget.setText(text)

    # "\n"이 포함되어 있으면 첫 줄만 사용
    if "\n" in text:
        text = text.split("\n")[0]

    # 위젯 크기가 0이거나 텍스트가 비어있으면 폰트 조정하지 않음
    if widget.width() == 0 or widget.height() == 0 or not text:
        return

    # 폰트 설정
    font_size = 1
    font = CustomFont(font_size)
    metrics = QFontMetrics(font)

    # 폰트 크기를 증가시키면서 위젯 크기에 맞는지 확인
    while font_size < maxSize:
        text_width: int = metrics.horizontalAdvance(text)
        text_height: int = metrics.height()

        # QPushButton이면 여백을 추가
        if isinstance(widget, QPushButton):
            text_width += 4
            text_height += 4

        # 위젯 크기를 초과하면 중지
        if text_width > widget.width() or text_height > widget.height():
            break

        font_size += 1
        font.setPointSize(font_size)
        metrics = QFontMetrics(font)

    # 폰트 크기 설정
    font.setPointSize(font_size - 1)
    widget.setFont(font)


def adjust_text_length(
    text: str, widget: QPushButton | QLabel, margin: int = 40
) -> str:
    """
    위젯 크기에 맞게 텍스트를 자름
    """

    font_metrics: QFontMetrics = widget.fontMetrics()
    max_width: int = widget.width() - margin

    for i in range(len(text), 0, -1):
        if font_metrics.boundingRect(text[:i]).width() < max_width:
            return text[:i]

    return ""


def set_var_to_ClassVar(var: list | dict, value: list | dict) -> None:
    """
    SharedData 클래스의 변수에 값을 설정
    """

    if isinstance(var, list) and isinstance(value, list):
        var.clear()
        for v in value:
            var.append(v)

    elif isinstance(var, dict) and isinstance(value, dict):
        var.clear()
        for key, v in value.items():
            var[key] = v

    else:
        raise TypeError("var와 value는 모두 list 또는 dict여야 합니다.")


def get_available_skills() -> list[str]:
    """
    서버, 직업에 따라 사용 가능한 스킬 목록 반환
    """

    return shared_data.skill_data[app_state.macro.server.id]["jobs"][
        shared_data.job_ID
    ]["skills"]


def get_every_skills() -> list[str]:
    """
    서버의 모든 스킬 목록 반환
    """

    skills: list[str] = sum(
        [
            skills["skills"]
            for job, skills in shared_data.skill_data[app_state.macro.server.id][
                "jobs"
            ].items()
        ],
        [],
    )

    return skills


def get_skill_details(skill_name: str) -> dict:
    """
    서버, 직업에 따른 스킬 상세 정보 반환
    """

    return shared_data.skill_data[app_state.macro.server.id]["skill_details"][
        skill_name
    ]
