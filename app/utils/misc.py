from .data_manager import convertResourcePath

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from PyQt6.QtGui import QFontDatabase


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
