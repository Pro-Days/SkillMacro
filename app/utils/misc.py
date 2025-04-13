from .data_manager import convertResourcePath

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtGui import QIcon, QPixmap, QFont, QFontMetrics
from PyQt6.QtWidgets import QPushButton


def convert7to5(shared_data, num):
    for x, y in enumerate(shared_data.selectedSkillList):  # x: 0~5, y: 0~7
        if y == num:
            return x


def isKeyUsing(shared_data, key):
    """
    가상 키보드 생성 중 키가 사용중인지 확인
    """

    key = key.replace("\n", "_")
    usingKey = []

    if shared_data.activeStartKeySlot == 1:
        usingKey.append(shared_data.inputStartKey)
    else:
        usingKey.append("F9")

    for i in shared_data.skillKeys:
        usingKey.append(i)

    for i in shared_data.linkSkillList:
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


## 스킬 이미지 디렉토리 리턴
def getSkillImage(shared_data, skill, count=-1):
    if skill == -1:
        return QIcon(QPixmap(convertResourcePath(f"resources\\image\\emptySkill.png")))

    count = (
        count
        if count != -1
        else shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][shared_data.jobID][skill]
    )

    return QIcon(
        QPixmap(
            convertResourcePath(
                f"resources\\image\\skill\\{shared_data.serverID}\\{shared_data.jobID}\\{skill}\\{count}.png"
            )
        )
    )


## 위젯 크기에 맞는 폰트로 변경
def adjustFontSize(widget, text, maxSize, font_name="나눔스퀘어라운드 ExtraBold"):
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
