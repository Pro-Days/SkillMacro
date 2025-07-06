from __future__ import annotations

from .data_manager import convertResourcePath

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

from typing import Optional, Union, TYPE_CHECKING

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtGui import QIcon, QPixmap, QFont, QFontMetrics
from PyQt6.QtWidgets import QPushButton, QWidget, QLabel


if TYPE_CHECKING:
    from .main_window import MainWindow
    from .shared_data import SharedData


def convert7to5(shared_data: SharedData, num: int) -> Optional[int]:
    for x, y in enumerate(shared_data.equipped_skills):  # x: 0~5, y: 0~7
        if y == num:
            return x


def isKeyUsing(shared_data: SharedData, key: str) -> bool:
    """
    키가 사용중인지 확인
    """

    key = key.replace("\n", "_")
    usingKey = []

    if shared_data.activeStartKeySlot == 1:
        usingKey.append(shared_data.inputStartKey)
    else:
        usingKey.append("F9")

    for i in shared_data.skillKeys:
        usingKey.append(i)

    for i in shared_data.link_skills:
        if i["keyType"] == 1:
            usingKey.append(i["key"])

    # if self.settingType == 3:
    #     usingKey.append(self.ButtonLinkKey1.text())

    # print(usingKey, key)

    return key in usingKey


def set_default_fonts():
    """
    기본 폰트 설정
    """

    # "나눔스퀘어라운드 ExtraBold"
    QFontDatabase.addApplicationFont(convertResourcePath("resources\\font\\NSR_B.ttf"))
    QFontDatabase.addApplicationFont(convertResourcePath("resources\\font\\NSR_EB.ttf"))

    font_path = convertResourcePath("resources\\font\\NSR_B.ttf")
    fm.fontManager.addfont(font_path)
    prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = prop.get_name()

    # print(QFontDatabase.families())


def get_skill_pixmap(
    shared_data: SharedData, skill: int, state: Union[str, int] = -1
) -> QPixmap:
    """
    스킬 아이콘 반환
    skill: -1이면 빈 스킬 아이콘 반환
    state: -1이면 해당 스킬의 최대 카운트 반환, "off"이면 비활성화 아이콘 반환
    """

    if skill == -1:
        return QPixmap(convertResourcePath(f"resources\\image\\emptySkill.png"))

    # count가 -1이면 shared_data에서 해당 스킬의 최대 카운트 가져오기
    if state == -1:
        state = shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][  # type: ignore
            shared_data.jobID
        ][
            skill
        ]

    return QPixmap(
        convertResourcePath(
            f"resources\\image\\skill\\{shared_data.serverID}\\{shared_data.jobID}\\{skill}\\{state}.png"
        )
    )


## 위젯 크기에 맞는 폰트로 변경
def adjustFontSize(
    widget: Union[QPushButton, QLabel],
    text: str,
    maxSize: int,
    font_name="나눔스퀘어라운드 ExtraBold",
):
    widget.setText(text)
    widget.setFont(QFont(font_name))

    if "\n" in text:
        text = text.split("\n")[0]

    if widget.width() == 0 or widget.height() == 0 or not text:
        return

    font = widget.font()
    font_size = 1
    font.setPointSize(font_size)
    metrics = QFontMetrics(font)

    while font_size < maxSize:
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        if isinstance(widget, QPushButton):
            text_width += 4
            text_height += 4

        if text_width > widget.width() or text_height > widget.height():
            break

        font_size += 1
        font.setPointSize(font_size)
        metrics = QFontMetrics(font)

    font.setPointSize(font_size - 1)
    widget.setFont(font)


def limit_text(text: str, widget: QWidget, margin: int = 40) -> str:
    """
    위젯 크기에 맞게 텍스트를 자름
    """

    font_metrics: QFontMetrics = widget.fontMetrics()
    max_width: int = widget.width() - margin

    for i in range(len(text), 0, -1):
        if font_metrics.boundingRect(text[:i]).width() < max_width:
            return text[:i]

    return ""


def clear_equipped_skill(master: MainWindow, shared_data: SharedData, skill: int):
    """
    장착된 스킬 초기화
    """

    # 연계스킬 수동 사용으로 변경
    for i, j in enumerate(shared_data.link_skills):
        for k in j["skills"]:
            if k[0] == skill:
                shared_data.link_skills[i][
                    "useType"
                ] = 1  # 나중에 useType -> use_auto: bool 변경

    # 스킬 사용 우선순위 리로드
    prev_priority: int = shared_data.skill_priority[skill]

    # 해제되는 스킬의 우선순위가 있다면
    if prev_priority:
        shared_data.skill_priority[skill] = 0

        # 해당 스킬보다 높은 우선순위의 스킬들 우선순위 -1
        for j, k in enumerate(shared_data.skill_priority):
            if k > prev_priority:
                shared_data.skill_priority[j] -= 1

                if shared_data.sidebar_type == 2:
                    master.get_sidebar().skill_sequence[j].setText(str(k - 1))

    # 스킬 연계설정이라면 -> 리로드
    if shared_data.sidebar_type == 3:
        master.get_sidebar().delete_sidebar_3()
        shared_data.sidebar_type = -1
        master.get_sidebar().change_sidebar_to_3()

    # 사이드바가 스킬 사용설정이라면
    if shared_data.sidebar_type == 2:
        master.get_sidebar().skill_icons[skill].setIcon(
            QIcon(
                get_skill_pixmap(
                    shared_data=shared_data,
                    skill=skill,
                    state="off",
                )
            )
        )

        master.get_sidebar().skill_sequence[skill].setText("-")
