from .data_manager import convertResourcePath


import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

from PyQt6.QtGui import QFontDatabase


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
