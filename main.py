import copy
import json
import os
import sys
import time
import random
import requests
from functools import lru_cache
from pprint import pprint
from functools import partial
from threading import Thread
from webbrowser import open_new
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import matplotlib.ticker as mtick
import keyboard as kb
import pyautogui as pag
from PyQt6.QtCore import QObject, QSize, Qt, QThread, QTimer, pyqtSignal, QPoint, pyqtSlot
from PyQt6.QtGui import (
    QPen,
    QFont,
    QIcon,
    QColor,
    QRegion,
    QPixmap,
    QPainter,
    QPalette,
    QTransform,
    QFontMetrics,
    QFontDatabase,
)
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QWidget,
    QLineEdit,
    QComboBox,
    QPushButton,
    QFileDialog,
    QScrollArea,
    QApplication,
    QStackedLayout,
    QGraphicsDropShadowEffect,
)


## 리소스 경로 변경
def convertResourcePath(relative_path) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


## 최신버전 확인용 클래스
class VersionChecker(QObject):
    versionChecked = pyqtSignal(str)

    @pyqtSlot()
    def checkVersion(self):
        try:
            response = requests.get("https://api.github.com/repos/pro-days/skillmacro/releases/latest")
            if response.status_code == 200:
                recentVersion = response.json()["name"]
                self.updateUrl = response.json()["html_url"]
                self.versionChecked.emit(recentVersion)
            else:
                self.versionChecked.emit("FailedUpdateCheck")
        except:
            self.versionChecked.emit("FailedUpdateCheck")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setDefaultFont()
        self.defineVar()
        self.setWindowIcon(self.icon)

        self.dataUpdate()
        self.dataLoad()
        self.initUI()

        # self.checkVersion()
        self.activateThread()

    ## 서브 쓰레드 실행
    def activateThread(self):
        Thread(target=self.checkKeyboardPressed, daemon=True).start()
        self.previewTimer = QTimer(self)
        self.previewTimer.singleShot(16, self.tick)

    def checkKeyboardPressed(self):
        while True:
            key = kb.read_key()
            convertedKey = self.key_dict[key] if key in self.key_dict else key

            # 링크스킬에 사용되는 키 리스트
            linkKeys = []
            for i in self.linkSkillList:
                linkKeys.append(i[1])

            if self.isActivated:
                self.afkTime0 = time.time()

            if convertedKey == self.startKey:
                if self.isActivated:  # On -> Off
                    self.isActivated = False

                    # self.setWindowIcon(self.icon)  # 윈도우 아이콘 변경 (자주 변경하면 중지됨)

                else:  # Off -> On
                    self.isActivated = True

                    # self.setWindowIcon(self.icon_on)  # 윈도우 아이콘 변경 (자주 변경하면 중지됨)

                    self.loopNum += 1
                    self.selectedItemSlot = -1
                    Thread(target=self.runMacro, args=[self.loopNum]).start()

                time.sleep(0.5 * self.sleepCoefficient_normal)

            elif convertedKey in linkKeys and not self.isActivated:
                for i in range(len(linkKeys)):
                    if convertedKey == linkKeys[i]:
                        Thread(target=self.useLinkSkill, args=[i, self.loopNum]).start()

                time.sleep(0.25 * self.sleepCoefficient_normal)
            else:
                pass

    def changeLayout(self, num):
        self.windowLayout.setCurrentIndex(num)
        self.layoutType = num

        if num == 0:
            self.removeSimulWidgets()
            [i.deleteLater() for i in self.page2.findChildren(QWidget)]
            self.updatePosition()
        elif num == 1:
            self.makePage2()

    def makePage2(self):
        self.sim_colors4 = [
            "255, 130, 130",  # #FF8282
            "255, 230, 140",  # #FFE68C
            "170, 230, 255",  # #AAE6FF
            "150, 225, 210",  # #96E1D2
        ]
        self.sim_input_colors = ["#f0f0f0", "#D9D9D9"]  # [background, border]
        self.sim_input_colorsRed = "#FF6060"
        self.sim_labelFrame_color = "#bbbbbb"
        self.scrollBarWidth = 12
        self.sim_margin = 10
        self.sim_mainFrameMargin = 20

        self.sim_navHeight = 50
        self.sim_navBWidth = 200

        self.sim_title_H = 50

        self.sim_main1_D = 5
        self.sim_main_D = 40
        self.sim_widget_D = 20

        self.sim_label_H = 50
        self.sim_label_x = 50

        self.sim_stat_margin = 50
        self.sim_stat_frame_H = 60
        self.sim_stat_label_H = 20
        self.sim_stat_input_H = 40
        self.sim_stat_width = 120

        self.sim_skill_margin = 100
        self.sim_skill_image_Size = 56
        self.sim_skill_right_W = 76
        self.sim_skill_width = 132
        self.sim_skill_frame_H = 86
        self.sim_skill_name_H = 30
        self.sim_skill_level_H = 24
        self.sim_skill_input_H = 24

        self.sim_simInfo_margin = 224
        self.sim_simInfo_frame_H = self.sim_stat_frame_H
        self.sim_simInfo_label_H = self.sim_stat_label_H
        self.sim_simInfo_input_H = self.sim_stat_input_H
        self.sim_simInfo_width = self.sim_stat_width

        self.sim_powerL_margin = 25
        self.sim_powerL_D = 20
        self.sim_powerL_width = 205
        self.sim_powerL_frame_H = 140
        self.sim_powerL_title_H = 50
        self.sim_powerL_number_H = 90

        self.sim_analysis_margin = self.sim_powerL_margin
        self.sim_analysis_D = self.sim_powerL_D
        self.sim_analysis_width = self.sim_powerL_width
        self.sim_analysis_color_W = 4
        self.sim_analysis_widthXC = self.sim_analysis_width - self.sim_analysis_color_W
        self.sim_analysis_frame_H = 140
        self.sim_analysis_title_H = 40
        self.sim_analysis_number_H = 55
        self.sim_analysis_number_marginH = 5
        self.sim_analysis_details_H = 20
        self.sim_analysis_details_W = 63
        self.sim_analysis_detailsT_W = 22
        self.sim_analysis_detailsN_W = 41
        self.sim_analysis_details_margin = 3

        self.sim_dps_margin = 25
        self.sim_dps_width = 430
        self.sim_dps_height = 300

        self.sim_skillDps_margin = 20
        self.sim_skillDps_width = self.sim_dps_width
        self.sim_skillDps_height = self.sim_dps_height

        self.sim_dmg_margin = 25
        self.sim_dmg_width = 880
        self.sim_dmg_height = 400

        self.sim_powerS_margin = 375
        self.sim_powerS_D = 15
        self.sim_powerS_width = 120
        self.sim_powerS_frame_H = 100
        self.sim_powerS_title_H = 40
        self.sim_powerS_number_H = 60

        self.sim_efficiency_frame_H = 100
        self.sim_potential_frame_H = 100

        self.sim_efficiency_statL_W = 110
        self.sim_efficiency_statL_H = 24
        self.sim_efficiency_statL_y = 15
        self.sim_efficiency_statL_margin = 33

        self.sim_efficiency_statInput_margin = 28
        self.sim_efficiency_statInput_W = 120
        self.sim_efficiency_statInput_H = 40
        self.sim_efficiency_statInput_y = self.sim_efficiency_statL_y + self.sim_efficiency_statL_H + 6

        self.sim_efficiency_arrow_margin = 28 + self.sim_efficiency_statInput_W
        self.sim_efficiency_arrow_W = 60
        self.sim_efficiency_arrow_H = 60
        self.sim_efficiency_arrow_y = 20

        self.sim_efficiency_statR_margin = self.sim_efficiency_arrow_margin + self.sim_efficiency_arrow_W
        self.sim_efficiency_statR_W = 120
        self.sim_efficiency_statR_H = 30
        self.sim_efficiency_statR_y = 35

        self.sim_potential_stat_margin = 50
        self.sim_potential_stat_W = 125
        self.sim_potential_stat_H = 30
        self.sim_potential_stat_D = 5

        self.sim_powerM_margin = 225
        self.sim_powerM_D = 20
        self.sim_powerM_width = 148
        self.sim_powerM_frame_H = 100
        self.sim_powerM_title_H = 40
        self.sim_powerM_number_H = 60

        self.sim_potentialRank_margin = 25
        self.sim_potentialRank_D = 20
        self.sim_potentialRank_width = 205
        self.sim_potentialRank_title_H = 50
        self.sim_potentialRank_rank_H = 25
        self.sim_potentialRank_ranks_H = self.sim_potentialRank_rank_H * 16
        self.sim_potentialRank_frame_H = self.sim_potentialRank_title_H + self.sim_potentialRank_rank_H * 16
        self.sim_potentialRank_rank_ranking_W = 30
        self.sim_potentialRank_rank_potential_W = 115
        self.sim_potentialRank_rank_power_W = 60

        # 캐릭터 카드
        self.sim_char_frame_H = 420
        self.sim_char_margin = 50
        self.sim_char_margin_y = 20

        self.sim_charInfo_marginX = 20
        self.sim_charInfo_marginY = 25
        self.sim_charInfo_label_y = 2
        self.sim_charInfo_label_H = 33
        self.sim_charInfo_W = int((928 - self.sim_char_margin * 4) * 0.5)  # 364
        self.sim_charInfo_H = self.sim_char_frame_H - self.sim_char_margin_y  # 400
        self.sim_charInfo_frame_W = self.sim_charInfo_W - self.sim_charInfo_marginX * 2  # 324

        self.sim_charInfo_nickname_H = 80
        self.sim_charInfo_nickname_input_margin = 20
        self.sim_charInfo_nickname_input_W = 200
        self.sim_charInfo_nickname_input_H = 35
        self.sim_charInfo_nickname_load_margin = (
            self.sim_charInfo_nickname_input_margin * 2 + self.sim_charInfo_nickname_input_W
        )  # 200
        self.sim_charInfo_nickname_load_W = 64
        self.sim_charInfo_nickname_load_H = 31
        self.sim_charInfo_nickname_load_y = self.sim_charInfo_label_y + self.sim_charInfo_label_H + 2  # 37

        self.sim_charInfo_char_H = 75
        self.sim_charInfo_char_button_margin = 12
        self.sim_charInfo_char_button_W = 92
        self.sim_charInfo_char_button_H = 30
        self.sim_charInfo_char_button_y = self.sim_charInfo_label_y + self.sim_charInfo_label_H  # 35

        self.sim_charInfo_power_H = 75
        self.sim_charInfo_power_button_margin = 12
        self.sim_charInfo_power_button_W = 66
        self.sim_charInfo_power_button_H = 30
        self.sim_charInfo_power_button_y = self.sim_charInfo_label_y + self.sim_charInfo_label_H  # 35

        self.sim_charInfo_complete_y = 30
        self.sim_charInfo_complete_margin = 50
        self.sim_charInfo_complete_W = 120
        self.sim_charInfo_complete_H = 40

        self.sim_charInfo_save_y = self.sim_charInfo_complete_y
        self.sim_charInfo_save_margin = self.sim_charInfo_complete_margin + self.sim_charInfo_complete_W + 24
        self.sim_charInfo_save_W = 120
        self.sim_charInfo_save_H = 40

        self.sim_charCard_W = int((928 - self.sim_char_margin * 4) * 0.5)  # 364
        self.sim_charCard_H = self.sim_char_frame_H - self.sim_char_margin_y  # 400
        self.sim_charCard_title_H = 50

        self.sim_charCard_image_margin = 19
        self.sim_charCard_image_W = 156
        self.sim_charCard_image_H = 312

        self.sim_charCard_name_margin = self.sim_charCard_image_margin + self.sim_charCard_image_W + 10
        self.sim_charCard_name_y = self.sim_charCard_title_H + 50
        self.sim_charCard_name_W = 166
        self.sim_charCard_name_H = 35

        self.sim_charCard_job_margin = self.sim_charCard_image_margin + self.sim_charCard_image_W + 30
        self.sim_charCard_job_y = self.sim_charCard_name_y + self.sim_charCard_name_H
        self.sim_charCard_job_W = 50  # 50 + 79 = 126
        self.sim_charCard_job_H = 40
        self.sim_charCard_level_margin = self.sim_charCard_job_margin + self.sim_charCard_job_W
        self.sim_charCard_level_y = self.sim_charCard_job_y
        self.sim_charCard_level_W = 76  # 50 + 76 = 126
        self.sim_charCard_level_H = self.sim_charCard_job_H

        self.sim_charCard_name_line_W = 146
        self.sim_charCard_info_line_H = 16

        self.sim_charCard_powerFrame_margin = self.sim_charCard_image_margin + self.sim_charCard_image_W + 10
        self.sim_charCard_powerFrame_y = self.sim_charCard_job_y + self.sim_charCard_job_H + 15
        self.sim_charCard_powerFrame_W = 166
        self.sim_charCard_powerFrame_H = 40
        self.sim_charCard_power_title_W = 80
        self.sim_charCard_power_number_W = 86

        # 상단바
        self.sim_navFrame = QFrame(self.page2)
        self.sim_navFrame.setGeometry(
            self.sim_margin,
            self.sim_margin,
            self.width() - self.sim_margin * 2,
            self.sim_navHeight,
        )
        self.sim_navFrame.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); }")

        self.sim_navButtons = []
        texts = ["정보 입력", "시뮬레이터", "스탯 계산기", "캐릭터 카드"]
        for i in [0, 1, 2, 3]:
            button = QPushButton(texts[i], self.sim_navFrame)
            button.setGeometry(self.sim_navBWidth * i, 0, self.sim_navBWidth, self.sim_navHeight)
            button.setStyleSheet(
                f"""
                QPushButton {{ background-color: rgb(255, 255, 255); border: none; border-bottom: {"2" if i == 0 else "0"}px solid #9180F7; }}
                QPushButton:hover {{ background-color: rgb(234, 234, 234); }}
                """
            )
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            self.sim_navButtons.append(button)
        button = QPushButton(self.sim_navFrame)  # 닫기 버튼
        button.setGeometry(
            890,
            0,
            self.sim_navHeight,
            self.sim_navHeight,
        )
        button.setStyleSheet(
            """
            QPushButton { background-color: rgb(255, 255, 255); border: none; border-radius: 10px; }
            QPushButton:hover { background-color: rgb(234, 234, 234); }
            """
        )
        pixmap = QPixmap(convertResourcePath("resource\\image\\x.png"))
        button.setIcon(QIcon(pixmap))
        button.setIconSize(QSize(15, 15))
        self.sim_navButtons.append(button)

        self.sim_navButtons[0].clicked.connect(self.makeSimulType1)
        self.sim_navButtons[1].clicked.connect(self.makeSimulType2)
        self.sim_navButtons[2].clicked.connect(self.makeSimulType3)
        self.sim_navButtons[3].clicked.connect(self.makeSimulType4)
        self.sim_navButtons[4].clicked.connect(lambda: self.changeLayout(0))

        # 메인 프레임
        self.sim_mainFrame = QFrame(self.page2)
        self.sim_mainFrame.setGeometry(
            self.sim_margin,
            self.sim_margin + self.sim_navHeight + self.sim_main1_D,
            self.width() - self.scrollBarWidth - self.sim_margin * 2,
            self.height()
            - self.labelCreator.height()
            - self.sim_navHeight
            - self.sim_margin * 2
            - self.sim_main1_D,
        )
        self.sim_mainFrame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.sim_mainScrollArea = QScrollArea(self.page2)
        self.sim_mainScrollArea.setWidget(self.sim_mainFrame)
        self.sim_mainScrollArea.setGeometry(
            self.sim_margin,
            self.sim_margin + self.sim_navHeight + self.sim_main1_D,
            self.width() - self.sim_margin,
            self.height()
            - self.labelCreator.height()
            - self.sim_navHeight
            - self.sim_margin * 2
            - self.sim_main1_D,
        )
        self.sim_mainScrollArea.setStyleSheet(
            "QScrollArea { background-color: #FFFFFF; border: 0px solid black; border-radius: 10px; }"
        )
        self.sim_mainScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.sim_mainScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.sim_mainScrollArea.setPalette(self.backPalette)
        self.sim_mainScrollArea.show()

        self.makeSimulType1()

    def removeSimulWidgets(self):
        if self.simType == 3:
            comboboxList = [
                self.sim_efficiency_statL,
                self.sim_efficiency_statR,
                self.sim_potential_stat0,
                self.sim_potential_stat1,
                self.sim_potential_stat2,
            ]
            for i in comboboxList:
                i.showPopup()
                i.hidePopup()
        [i.deleteLater() for i in self.sim_mainFrame.findChildren(QWidget)]
        self.simType = 0
        plt.close("all")

    def makeSimulType4(self):
        self.removeSimulWidgets()
        self.sim_updateNavButton(3)

        self.simType = 4

        self.sim_card_updated = False

        self.sim_powers = self.simulateMacro(
            tuple(self.info_stats), tuple(self.info_skills), tuple(self.info_simInfo), 1
        )
        self.sim_powers = [str(int(i)) for i in self.sim_powers]

        # 스펙업 효율 계산기
        self.sim4_frame = QFrame(self.sim_mainFrame)
        self.sim4_frame.setGeometry(
            0,
            0,
            928,
            self.sim_char_frame_H,
        )
        self.sim4_frame.setStyleSheet(
            """QFrame {
            background-color: rgb(255, 255, 255);
            border: 0px solid;
        }"""
        )

        ## 캐릭터 정보 입력
        self.sim4_frame_info = QFrame(self.sim4_frame)
        self.sim4_frame_info.setGeometry(
            self.sim_char_margin,
            self.sim_char_margin_y,
            self.sim_charInfo_W,
            self.sim_charInfo_H,
        )
        self.sim4_frame_info.setStyleSheet(
            """QFrame {
            background-color: #F8F8F8;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
        }"""
        )

        # 닉네임 입력
        self.sim4_info_nicknameFrame = QFrame(self.sim4_frame_info)
        self.sim4_info_nicknameFrame.setGeometry(
            self.sim_charInfo_marginX,
            self.sim_charInfo_marginY,
            self.sim_charInfo_frame_W,
            self.sim_charInfo_nickname_H,
        )
        self.sim4_info_nicknameFrame.setStyleSheet(
            """QFrame {
            background-color: #FFFFFF;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
        }"""
        )

        self.sim4_info_nicknameLabel = QLabel("닉네임", self.sim4_info_nicknameFrame)
        self.sim4_info_nicknameLabel.setGeometry(
            self.sim_charInfo_nickname_input_margin,
            self.sim_charInfo_label_y,
            self.sim_charInfo_nickname_input_W,
            self.sim_charInfo_label_H,
        )
        self.sim4_info_nicknameLabel.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.sim4_info_nicknameLabel.setFont(QFont("나눔스퀘어라운드 Bold", 14))
        self.sim4_info_nicknameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sim4_info_nicknameInput = QLineEdit("", self.sim4_info_nicknameFrame)
        self.sim4_info_nicknameInput.setGeometry(
            self.sim_charInfo_nickname_input_margin,
            self.sim_charInfo_label_y + self.sim_charInfo_label_H,
            self.sim_charInfo_nickname_input_W,
            self.sim_charInfo_nickname_input_H,
        )
        self.sim4_info_nicknameInput.setStyleSheet(
            f"""QLineEdit {{
                background-color: {self.sim_input_colors[0]};
                border: 1px solid {self.sim_input_colors[1]};
                border-radius: 4px;
            }}"""
        )
        self.sim4_info_nicknameInput.setFont(QFont("나눔스퀘어라운드 Bold", 12))
        self.sim4_info_nicknameInput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sim4_info_nicknameInput.setFocus()

        self.sim4_info_nicknameButton = QPushButton("불러오기", self.sim4_info_nicknameFrame)
        self.sim4_info_nicknameButton.setGeometry(
            self.sim_charInfo_nickname_load_margin,
            self.sim_charInfo_nickname_load_y,
            self.sim_charInfo_nickname_load_W,
            self.sim_charInfo_nickname_load_H,
        )
        self.sim4_info_nicknameButton.setStyleSheet(
            f"""QPushButton {{
            background-color: #70BB70;
            border: 1px solid {self.sim_input_colors[1]};
            border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #60A060;
            }}"""
        )
        self.sim4_info_nicknameButton.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.sim4_info_nicknameButton.clicked.connect(self.sim_loadCharacterInfo)

        # 캐릭터 선택
        # 캐릭터 불러오면 시뮬레이션 진행한 직업과 같은 것만 선택 가능하도록
        self.sim_info_charData = None

        self.sim4_info_charFrame = QFrame(self.sim4_frame_info)
        self.sim4_info_charFrame.setGeometry(
            self.sim_charInfo_marginX,
            self.sim_charInfo_marginY * 2 + self.sim_charInfo_nickname_H,
            self.sim_charInfo_frame_W,
            self.sim_charInfo_char_H,
        )
        self.sim4_info_charFrame.setStyleSheet(
            """QFrame {
            background-color: #FFFFFF;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
        }"""
        )

        self.sim4_info_charLabel = QLabel("캐릭터 선택", self.sim4_info_charFrame)
        self.sim4_info_charLabel.setGeometry(
            0,
            self.sim_charInfo_label_y,
            self.sim_charInfo_frame_W,
            self.sim_charInfo_label_H,
        )
        self.sim4_info_charLabel.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.sim4_info_charLabel.setFont(QFont("나눔스퀘어라운드 Bold", 14))
        self.sim4_info_charLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sim4_info_charButtonList = []
        for i in range(3):
            button = QPushButton("", self.sim4_info_charFrame)
            button.setGeometry(
                self.sim_charInfo_char_button_margin
                + (self.sim_charInfo_char_button_W + self.sim_charInfo_char_button_margin) * i,
                self.sim_charInfo_char_button_y,
                self.sim_charInfo_char_button_W,
                self.sim_charInfo_char_button_H,
            )
            button.setStyleSheet(
                f"""QPushButton {{
                background-color: {self.sim_input_colors[0]};
                border: 1px solid {self.sim_input_colors[1]};
                border-radius: 8px;
                }}"""
            )
            button.setFont(QFont("나눔스퀘어라운드 Bold", 10))
            self.sim4_info_charButtonList.append(button)

        # 전투력 표시
        self.sim_info_powerActive = [True, True, True, True]

        self.sim4_info_powerFrame = QFrame(self.sim4_frame_info)
        self.sim4_info_powerFrame.setGeometry(
            self.sim_charInfo_marginX,
            self.sim_charInfo_marginY * 3 + self.sim_charInfo_nickname_H + self.sim_charInfo_char_H,
            self.sim_charInfo_frame_W,
            self.sim_charInfo_char_H,
        )
        self.sim4_info_powerFrame.setStyleSheet(
            """QFrame {
            background-color: #FFFFFF;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
        }"""
        )

        self.sim4_info_powerLabel = QLabel("전투력 표시", self.sim4_info_powerFrame)
        self.sim4_info_powerLabel.setGeometry(
            0,
            self.sim_charInfo_label_y,
            self.sim_charInfo_frame_W,
            self.sim_charInfo_label_H,
        )
        self.sim4_info_powerLabel.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.sim4_info_powerLabel.setFont(QFont("나눔스퀘어라운드 Bold", 14))
        self.sim4_info_powerLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        texts = ["보스데미지", "일반데미지", "보스", "사냥"]
        self.sim4_info_powerButtons = []
        for i in range(4):
            button = QPushButton(texts[i], self.sim4_info_powerFrame)
            button.setGeometry(
                self.sim_charInfo_power_button_margin
                + (self.sim_charInfo_power_button_W + self.sim_charInfo_power_button_margin) * i,
                self.sim_charInfo_power_button_y,
                self.sim_charInfo_power_button_W,
                self.sim_charInfo_power_button_H,
            )
            button.setStyleSheet(
                f"""QPushButton {{
                background-color: #FFFFFF;
                border: 1px solid {self.sim_input_colors[1]};
                border-radius: 5px;
                }}
                QPushButton:hover {{
                    background-color: #F0F0F0;
                }}"""
            )
            button.setFont(QFont("나눔스퀘어라운드 Bold", 10))
            button.clicked.connect(partial(lambda x: self.sim_info_powersClicked(x), i))
            self.sim4_info_powerButtons.append(button)

        # 입력 완료, 저장
        self.sim4_info_completeButton = QPushButton("입력 완료", self.sim4_frame_info)
        self.sim4_info_completeButton.setGeometry(
            self.sim_charInfo_complete_margin,
            self.sim_charInfo_marginY * 3
            + self.sim_charInfo_nickname_H
            + self.sim_charInfo_char_H
            + self.sim_charInfo_power_H
            + self.sim_charInfo_complete_y,
            self.sim_charInfo_complete_W,
            self.sim_charInfo_complete_H,
        )
        self.sim4_info_completeButton.setStyleSheet(
            f"""QPushButton {{
            background-color: #70BB70;
            border: 1px solid {self.sim_input_colors[1]};
            border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #60A060;
            }}"""
        )
        self.sim4_info_completeButton.setFont(QFont("나눔스퀘어라운드 Bold", 14))
        self.sim4_info_completeButton.clicked.connect(self.sim_card_update)

        self.sim4_info_saveButton = QPushButton("저장", self.sim4_frame_info)
        self.sim4_info_saveButton.setGeometry(
            self.sim_charInfo_save_margin,
            self.sim_charInfo_marginY * 3
            + self.sim_charInfo_nickname_H
            + self.sim_charInfo_char_H
            + self.sim_charInfo_power_H
            + self.sim_charInfo_save_y,
            self.sim_charInfo_save_W,
            self.sim_charInfo_save_H,
        )
        self.sim4_info_saveButton.setStyleSheet(
            f"""QPushButton {{
            background-color: #FF8282;
            border: 1px solid {self.sim_input_colors[1]};
            border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #FF6060;
            }}"""
        )
        self.sim4_info_saveButton.setFont(QFont("나눔스퀘어라운드 Bold", 14))
        self.sim4_info_saveButton.clicked.connect(self.sim_card_save)

        ## 캐릭터 카드
        self.sim4_frame_card = QFrame(self.sim4_frame)
        self.sim4_frame_card.setGeometry(
            self.sim_char_margin * 3 + self.sim_charInfo_W,
            self.sim_char_margin_y,
            self.sim_charCard_W,
            self.sim_charCard_H,
        )
        self.sim4_frame_card.setStyleSheet(
            """QFrame {
            background-color: #FFFFFF;
            border: 3px solid #CCCCCC;
            border-radius: 0px;
        }"""
        )

        # 타이틀
        self.sim4_card_title = QLabel("한월 캐릭터 카드", self.sim4_frame_card)
        self.sim4_card_title.setGeometry(
            0,
            0,
            self.sim_charCard_W,
            self.sim_charCard_title_H,
        )
        self.sim4_card_title.setStyleSheet(
            """QLabel {
            background-color: #CADEFC;
            border: 3px solid #CCCCCC;
            border-bottom: 0px solid;
            border-radius: 0px;
        }"""
        )
        self.sim4_card_title.setFont(QFont("나눔스퀘어라운드 ExtraBold", 18))
        self.sim4_card_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 이미지
        self.sim4_card_image_bg = QLabel("", self.sim4_frame_card)
        self.sim4_card_image_bg.setGeometry(
            self.sim_charCard_image_margin,
            self.sim_charCard_image_margin + self.sim_charCard_title_H,
            self.sim_charCard_image_W,
            self.sim_charCard_image_H,
        )
        self.sim4_card_image_bg.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 5px solid #AAAAAA;
            border-radius: 5px;
        }"""
        )
        self.sim4_card_image_bg.setScaledContents(True)

        self.sim4_card_image = QLabel("", self.sim4_frame_card)
        self.sim4_card_image.setGeometry(
            self.sim_charCard_image_margin + 15,
            self.sim_charCard_image_margin + self.sim_charCard_title_H + 15,
            self.sim_charCard_image_W - 30,  # 126
            self.sim_charCard_image_H - 30,  # 282
        )
        self.sim4_card_image.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.sim4_card_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sim4_card_image.setScaledContents(True)

        # 캐릭터 정보
        self.sim4_card_name = QLabel("", self.sim4_frame_card)
        self.sim4_card_name.setGeometry(
            self.sim_charCard_name_margin,
            self.sim_charCard_name_y,
            self.sim_charCard_name_W,
            self.sim_charCard_name_H,
        )
        self.sim4_card_name.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.sim4_card_name.setFont(QFont("나눔스퀘어라운드 ExtraBold", 18))
        self.sim4_card_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sim4_card_job = QLabel("", self.sim4_frame_card)
        self.sim4_card_job.setGeometry(
            self.sim_charCard_job_margin,
            self.sim_charCard_job_y,
            self.sim_charCard_job_W,
            self.sim_charCard_job_H,
        )
        self.sim4_card_job.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.sim4_card_job.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.sim4_card_job.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sim4_card_level = QLabel("", self.sim4_frame_card)
        self.sim4_card_level.setGeometry(
            self.sim_charCard_level_margin,
            self.sim_charCard_level_y,
            self.sim_charCard_level_W,
            self.sim_charCard_level_H,
        )
        self.sim4_card_level.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.sim4_card_level.setFont(QFont("나눔스퀘어라운드 Bold", 12))
        self.sim4_card_level.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sim4_card_name_line = QFrame(self.sim4_frame_card)
        self.sim4_card_name_line.setGeometry(
            self.sim_charCard_name_margin + 10,
            self.sim_charCard_name_y + self.sim_charCard_name_H,
            self.sim_charCard_name_line_W,
            1,
        )
        self.sim4_card_name_line.setStyleSheet(
            """QFrame {
            background-color: #CCCCCC;
            border: 0px solid;
        }"""
        )

        self.sim4_card_info_line = QFrame(self.sim4_frame_card)
        self.sim4_card_info_line.setGeometry(
            self.sim_charCard_level_margin + 1,
            self.sim_charCard_level_y + 12,
            1,
            self.sim_charCard_info_line_H,
        )
        self.sim4_card_info_line.setStyleSheet(
            """QFrame {
            background-color: #CCCCCC;
            border: 0px solid;
        }"""
        )

        # 전투력
        titles = ["보스데미지", "일반데미지", "보스", "사냥"]
        self.sim4_card_powers = [[], [], [], []]
        for i in range(4):
            frame = QFrame(self.sim4_frame_card)
            frame.setGeometry(
                self.sim_charCard_powerFrame_margin,
                self.sim_charCard_powerFrame_y + self.sim_charCard_powerFrame_H * i,
                self.sim_charCard_powerFrame_W,
                self.sim_charCard_powerFrame_H,
            )
            frame.setStyleSheet(
                """QFrame {
                background-color: transparent;
                border: 0px solid;
            }"""
            )
            self.sim4_card_powers[i].append(frame)

            title = QLabel(titles[i], frame)
            title.setStyleSheet(
                f"""QLabel {{
                    background-color: rgb({self.sim_colors4[i]});
                    border: 1px solid rgb({self.sim_colors4[i]});
                    border-top-left-radius: 4px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 4px;
                    border-bottom-right-radius: 0px;
                }}"""
            )
            title.setGeometry(0, 0, self.sim_charCard_power_title_W, self.sim_charCard_powerFrame_H)
            title.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim4_card_powers[i].append(title)

            number = QLabel("", frame)
            number.setStyleSheet(
                f"""QLabel {{
                    background-color: rgba({self.sim_colors4[i]}, 120);
                    border: 1px solid rgb({self.sim_colors4[i]});
                    border-left: 0px solid;
                    border-top-left-radius: 0px;
                    border-top-right-radius: 4px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 4px
                }}"""
            )
            number.setGeometry(
                self.sim_charCard_power_title_W,
                0,
                self.sim_charCard_power_number_W,
                self.sim_charCard_powerFrame_H,
            )
            number.setFont(QFont("나눔스퀘어라운드 ExtraBold", 14))
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim4_card_powers[i].append(number)

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim4_frame.y() + self.sim4_frame.height() + self.sim_mainFrameMargin,
        )
        [i.show() for i in self.page2.findChildren(QWidget)]
        self.updatePosition()

    def makeSimulType3(self):
        self.removeSimulWidgets()
        self.sim_updateNavButton(2)

        self.simType = 3
        # print(self.info_simInfo)
        self.sim_powers = self.simulateMacro(
            tuple(self.info_stats), tuple(self.info_skills), tuple(self.info_simInfo), 1
        )
        self.sim_powers = [str(int(i)) for i in self.sim_powers]

        self.widgetList = []
        self.sim_skill_inputCheck = False
        self.sim_stat_inputCheck = False
        comboboxStyle = f"""QComboBox {{ 
                background-color: {self.sim_input_colors[0]};
                border: 1px solid {self.sim_input_colors[1]};
                border-radius: 4px;
            }}
            QComboBox::drop-down {{
                width: 20px;
                border-left-width: 1px;
                border-left-color: darkgray;
                border-left-style: solid;
            }}
            QComboBox::down-arrow {{
                image: url({convertResourcePath("resource\\image\\down_arrow.png").replace("\\", "/")});
                width: 16px;
                height: 16px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {self.sim_input_colors[1]};
            }}"""

        # 스펙업 효율 계산기
        self.sim3_frame1 = QFrame(self.sim_mainFrame)
        self.sim3_frame1.setGeometry(
            0,
            0,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_efficiency_frame_H),
        )
        self.sim3_frame1.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")
        self.widgetList.append(self.sim3_frame1)

        self.sim3_frame1_labelFrame, self.sim3_frame1_label = self.sim_returnTitleFrame(
            self.sim3_frame1, "스펙업 효율 계산기"
        )
        self.widgetList.append(self.sim3_frame1_labelFrame)
        self.widgetList.append(self.sim3_frame1_label)

        self.sim_efficiency_statL = QComboBox(self.sim3_frame1)
        self.sim_efficiency_statL.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.sim_efficiency_statL.addItems(self.statList)
        self.sim_efficiency_statL.setStyleSheet(comboboxStyle)
        self.sim_efficiency_statL.setGeometry(
            self.sim_efficiency_statL_margin,
            self.sim_label_H + self.sim_widget_D + self.sim_efficiency_statL_y,
            self.sim_efficiency_statL_W,
            self.sim_efficiency_statL_H,
        )
        self.widgetList.append(self.sim_efficiency_statL)
        self.sim_efficiency_statL.currentIndexChanged.connect(self.sim_efficiency_Changed)

        self.sim_efficiency_statInput = QLineEdit("10", self.sim3_frame1)
        self.sim_efficiency_statInput.setFont(QFont("나눔스퀘어라운드 Bold", 14))
        self.sim_efficiency_statInput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sim_efficiency_statInput.setStyleSheet(
            f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
        )
        self.sim_efficiency_statInput.setGeometry(
            self.sim_efficiency_statInput_margin,
            self.sim_label_H + self.sim_widget_D + self.sim_efficiency_statInput_y,
            self.sim_efficiency_statInput_W,
            self.sim_efficiency_statInput_H,
        )
        self.sim_efficiency_statInput.setFocus()
        self.widgetList.append(self.sim_efficiency_statInput)
        # 데이터 입력시 실행할 함수 연결
        self.sim_efficiency_statInput.textChanged.connect(self.sim_efficiency_Changed)

        self.sim_efficiency_arrow = QLabel("", self.sim3_frame1)
        self.sim_efficiency_arrow.setStyleSheet(
            f"QLabel {{ background-color: transparent; border: 0px solid; }}"
        )
        pixmap = QPixmap(convertResourcePath("resource\\image\\lineArrow.png"))
        pixmap = pixmap.scaled(self.sim_efficiency_arrow_W, self.sim_efficiency_arrow_H)
        self.sim_efficiency_arrow.setPixmap(pixmap)
        self.sim_efficiency_arrow.setGeometry(
            self.sim_efficiency_arrow_margin,
            self.sim_label_H + self.sim_widget_D + self.sim_efficiency_arrow_y,
            self.sim_efficiency_arrow_W,
            self.sim_efficiency_arrow_H,
        )
        self.widgetList.append(self.sim_efficiency_arrow)

        self.sim_efficiency_statR = QComboBox(self.sim3_frame1)
        self.sim_efficiency_statR.setFont(QFont("나눔스퀘어라운드 Bold", 12))
        self.sim_efficiency_statR.addItems(self.statList)
        self.sim_efficiency_statR.setStyleSheet(comboboxStyle)
        self.sim_efficiency_statR.setGeometry(
            self.sim_efficiency_statR_margin,
            self.sim_label_H + self.sim_widget_D + self.sim_efficiency_statR_y,
            self.sim_efficiency_statR_W,
            self.sim_efficiency_statR_H,
        )
        self.widgetList.append(self.sim_efficiency_statR)
        self.sim_efficiency_statR.currentIndexChanged.connect(self.sim_efficiency_Changed)

        self.sim_efficiency_power_list = self.sim_makePowerLabels(
            self.sim3_frame1, ["0"] * 4
        )  # [[f, t, n], [f, t, n], [f, t, n], [f, t, n]]

        for i, (f, t, n) in enumerate(self.sim_efficiency_power_list):
            f.setGeometry(
                self.sim_powerS_margin + (self.sim_powerS_width + self.sim_powerS_D) * i,
                self.sim_label_H + self.sim_widget_D,
                self.sim_powerS_width,
                self.sim_powerS_frame_H,
            )
            self.widgetList.append(f)
            t.setGeometry(
                0,
                0,
                self.sim_powerS_width,
                self.sim_powerS_title_H,
            )
            self.widgetList.append(t)
            n.setGeometry(
                0,
                self.sim_powerS_title_H,
                self.sim_powerS_width,
                self.sim_powerS_number_H,
            )
            self.widgetList.append(n)

        self.sim_update_efficiency()

        # 추가 스펙업 계산기
        self.sim3_frame2 = QFrame(self.sim_mainFrame)
        self.sim3_frame2.setGeometry(
            0,
            self.sim3_frame1.y() + self.sim3_frame1.height() + self.sim_main_D,
            928,
            self.sim_title_H
            + (self.sim_widget_D + self.sim_stat_frame_H) * 3
            + self.sim_main_D
            + (self.sim_widget_D + self.sim_skill_frame_H) * 2
            + self.sim_main_D
            + (self.sim_widget_D + self.sim_powerL_frame_H),
        )
        self.sim3_frame2.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")
        self.widgetList.append(self.sim3_frame2)

        self.sim3_frame2_labelFrame, self.sim3_frame2_label = self.sim_returnTitleFrame(
            self.sim3_frame2, "추가 스펙업 계산기"
        )
        self.widgetList.append(self.sim3_frame2_labelFrame)
        self.widgetList.append(self.sim3_frame2_label)

        self.sim_additional_power_list = self.sim_makePowerLabels(
            self.sim3_frame2, ["0"] * 4, font_size=16
        )  # [[f, t, n], [f, t, n], [f, t, n], [f, t, n]]

        for i, (f, t, n) in enumerate(self.sim_additional_power_list):
            f.setGeometry(
                self.sim_powerL_margin + (self.sim_powerL_width + self.sim_powerL_D) * i,
                self.sim_label_H
                + self.sim_widget_D
                + (self.sim_widget_D + self.sim_stat_frame_H) * 3
                + self.sim_main_D
                + (self.sim_widget_D + self.sim_skill_frame_H) * 2
                + self.sim_main_D,
                self.sim_powerL_width,
                self.sim_powerL_frame_H,
            )
            self.widgetList.append(f)
            t.setGeometry(
                0,
                0,
                self.sim_powerL_width,
                self.sim_powerL_title_H,
            )
            self.widgetList.append(t)
            n.setGeometry(
                0,
                self.sim_powerL_title_H,
                self.sim_powerL_width,
                self.sim_powerL_number_H,
            )
            self.widgetList.append(n)

        self.sim_makeStatInput(self.sim3_frame2)

        margin, count = 21, 6
        for i in range(18):
            self.sim_stat_frames[i].move(
                self.sim_stat_margin + self.sim_stat_width * (i % count) + margin * (i % count),
                self.sim3_frame2_labelFrame.height()
                + self.sim_widget_D * ((i // count) + 1)
                + self.sim_stat_frame_H * (i // count),
            )
            self.widgetList.append(self.sim_stat_frames[i])
            self.sim_stat_labels[i].setGeometry(
                0,
                0,
                self.sim_stat_width,
                self.sim_stat_label_H,
            )
            self.widgetList.append(self.sim_stat_labels[i])
            self.sim_stat_inputs[i].setGeometry(
                0, self.sim_stat_label_H, self.sim_stat_width, self.sim_stat_input_H
            )
            self.widgetList.append(self.sim_stat_inputs[i])

            self.sim_stat_inputs[i].setText("0")

        self.sim_makeSkillInput(self.sim3_frame2)

        margin, count = 66, 4
        for i in range(8):
            self.sim_skill_frames[i].move(
                self.sim_skill_margin + self.sim_skill_width * (i % count) + margin * (i % count),
                self.sim3_frame2_labelFrame.height()
                + self.sim_widget_D * ((i // count) + 1)
                + self.sim_skill_frame_H * (i // count)
                + (self.sim_widget_D + self.sim_stat_frame_H) * 3
                + self.sim_main_D,
            )
            self.widgetList.append(self.sim_skill_frames[i])
            self.sim_skill_names[i].setGeometry(
                0,
                0,
                self.sim_skill_width,
                self.sim_skill_name_H,
            )
            self.widgetList.append(self.sim_skill_names[i])
            self.sim_skill_levels[i].setGeometry(
                self.sim_skill_image_Size,
                self.sim_skill_name_H,
                self.sim_skill_right_W,
                self.sim_skill_level_H,
            )
            self.widgetList.append(self.sim_skill_levels[i])
            self.sim_skill_inputs[i].setGeometry(
                self.sim_skill_image_Size,
                self.sim_skill_name_H + self.sim_skill_level_H,
                self.sim_skill_right_W,
                self.sim_skill_input_H,
            )
            self.widgetList.append(self.sim_skill_inputs[i])

            self.sim_skill_inputs[i].setText(str(self.info_skills[i]))

        # 잠재능력 계산기
        self.sim3_frame3 = QFrame(self.sim_mainFrame)
        self.sim3_frame3.setGeometry(
            0,
            self.sim3_frame2.y() + self.sim3_frame2.height() + self.sim_main_D,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_potential_frame_H),
        )
        self.sim3_frame3.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")
        self.widgetList.append(self.sim3_frame3)

        self.sim3_frame3_labelFrame, self.sim3_frame3_label = self.sim_returnTitleFrame(
            self.sim3_frame3, "잠재능력 계산기"
        )
        self.widgetList.append(self.sim3_frame3_labelFrame)
        self.widgetList.append(self.sim3_frame3_label)

        self.sim_potential_stat0 = QComboBox(self.sim3_frame3)
        self.sim_potential_stat0.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.sim_potential_stat0.addItems(self.potentialStatList.keys())
        self.sim_potential_stat0.setStyleSheet(comboboxStyle)
        self.sim_potential_stat0.setGeometry(
            self.sim_potential_stat_margin,
            self.sim_label_H + self.sim_widget_D,
            self.sim_potential_stat_W,
            self.sim_potential_stat_H,
        )
        self.sim_potential_stat0.currentIndexChanged.connect(self.sim_potential_update)
        self.widgetList.append(self.sim_potential_stat0)

        self.sim_potential_stat1 = QComboBox(self.sim3_frame3)
        self.sim_potential_stat1.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.sim_potential_stat1.addItems(self.potentialStatList.keys())
        self.sim_potential_stat1.setStyleSheet(comboboxStyle)
        self.sim_potential_stat1.setGeometry(
            self.sim_potential_stat_margin,
            self.sim_label_H + self.sim_widget_D + (self.sim_potential_stat_H + self.sim_potential_stat_D),
            self.sim_potential_stat_W,
            self.sim_potential_stat_H,
        )
        self.sim_potential_stat1.currentIndexChanged.connect(self.sim_potential_update)
        self.widgetList.append(self.sim_potential_stat1)

        self.sim_potential_stat2 = QComboBox(self.sim3_frame3)
        self.sim_potential_stat2.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.sim_potential_stat2.addItems(self.potentialStatList.keys())
        self.sim_potential_stat2.setStyleSheet(comboboxStyle)
        self.sim_potential_stat2.setGeometry(
            self.sim_potential_stat_margin,
            self.sim_label_H
            + self.sim_widget_D
            + (self.sim_potential_stat_H + self.sim_potential_stat_D) * 2,
            self.sim_potential_stat_W,
            self.sim_potential_stat_H,
        )
        self.sim_potential_stat2.currentIndexChanged.connect(self.sim_potential_update)
        self.widgetList.append(self.sim_potential_stat2)

        self.sim_potential_power_list = self.sim_makePowerLabels(
            self.sim3_frame3, ["0"] * 4
        )  # [[f, t, n], [f, t, n], [f, t, n], [f, t, n]]

        for i, (f, t, n) in enumerate(self.sim_potential_power_list):
            f.setGeometry(
                self.sim_powerM_margin + (self.sim_powerM_width + self.sim_powerM_D) * i,
                self.sim_label_H + self.sim_widget_D,
                self.sim_powerM_width,
                self.sim_powerM_frame_H,
            )
            self.widgetList.append(f)
            t.setGeometry(
                0,
                0,
                self.sim_powerM_width,
                self.sim_powerM_title_H,
            )
            self.widgetList.append(t)
            n.setGeometry(
                0,
                self.sim_powerM_title_H,
                self.sim_powerM_width,
                self.sim_powerM_number_H,
            )
            self.widgetList.append(n)

        self.sim_potential_update()

        # 잠재능력 옵션 순위표
        self.sim3_frame4 = QFrame(self.sim_mainFrame)
        self.sim3_frame4.setGeometry(
            0,
            self.sim3_frame3.y() + self.sim3_frame3.height() + self.sim_main_D,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_potentialRank_frame_H),
        )
        self.sim3_frame4.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")
        self.widgetList.append(self.sim3_frame4)

        self.sim3_frame4_labelFrame, self.sim3_frame4_label = self.sim_returnTitleFrame(
            self.sim3_frame4, "잠재능력 옵션 순위표"
        )
        self.widgetList.append(self.sim3_frame4_labelFrame)
        self.widgetList.append(self.sim3_frame4_label)

        titles = ["보스데미지", "일반데미지", "보스", "사냥"]
        texts = [[], [], [], []]
        for key, (num, value) in self.potentialStatList.items():
            stats = self.info_stats.copy()
            stats[num] += value

            powers = self.simulateMacro(tuple(stats), tuple(self.info_skills), tuple(self.info_simInfo), 1)
            diff_powers = [int(powers[i]) - int(self.sim_powers[i]) for i in range(4)]

            for i in range(4):
                texts[i].append([key, diff_powers[i]])

        [texts[i].sort(key=lambda x: x[1], reverse=True) for i in range(4)]
        for i in range(4):
            for j in range(len(self.potentialStatList)):
                if texts[i][j][1] == 0:
                    texts[i][j] = ["", "", ""]
                else:
                    texts[i][j][1] = f"+{texts[i][j][1]}"
                    texts[i][j].insert(0, str(j + 1))
        [texts[i].insert(0, ["순위", "잠재능력", "전투력"]) for i in range(4)]

        colors = ["255, 163, 134", "255, 152, 0", "33, 150, 243", "165, 214, 167"]
        transparencies = ["140", "89", "77", "179"]
        self.sim_potentialRank_potentialList = [[], [], [], []]
        self.sim_potentialRank_powerList = [[], [], [], []]
        for i in range(4):
            frame = QFrame(self.sim3_frame4)
            frame.setGeometry(
                self.sim_potentialRank_margin + (self.sim_potentialRank_width + self.sim_potentialRank_D) * i,
                self.sim_label_H + self.sim_widget_D,
                self.sim_potentialRank_width,
                self.sim_potentialRank_frame_H,
            )
            self.widgetList.append(frame)

            title = QLabel(titles[i], frame)
            title.setStyleSheet(
                f"""QLabel {{
                    background-color: rgb({self.sim_colors4[i]});
                    border: 1px solid rgb({self.sim_colors4[i]});
                    border-bottom: 0px solid;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                }}"""
            )
            title.setFont(QFont("나눔스퀘어라운드 ExtraBold", 14))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setGeometry(
                0,
                0,
                self.sim_potentialRank_width,
                self.sim_potentialRank_title_H + 1,
            )
            self.widgetList.append(title)

            table_frame = QFrame(frame)
            table_frame.setStyleSheet(
                f"""QFrame {{
                    background-color: rgba({self.sim_colors4[i]}, 120);
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 4px;
                    border-bottom-right-radius: 4px
                }}"""
            )
            table_frame.setGeometry(
                0,
                self.sim_potentialRank_title_H,
                self.sim_potentialRank_width,
                self.sim_potentialRank_ranks_H,
            )
            self.widgetList.append(table_frame)

            for j in range(16):
                rank = QLabel(texts[i][j][0], table_frame)
                if j == 0:
                    rank.setStyleSheet(
                        f"""QLabel {{
                            background-color: rgba({colors[i]}, {transparencies[i]});
                            border: 1px solid rgb({self.sim_colors4[i]});
                            border-top: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-bottom-right-radius: 0px;
                        }}"""
                    )
                elif j == 15:
                    rank.setStyleSheet(
                        f"""QLabel {{
                            background-color: transparent;
                            border: 1px solid rgb({self.sim_colors4[i]});
                            border-top: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 4px;
                            border-bottom-right-radius: 0px;
                        }}"""
                    )
                else:
                    rank.setStyleSheet(
                        f"""QLabel {{
                            background-color: transparent;
                            border: 1px solid rgb({self.sim_colors4[i]});
                            border-top: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-bottom-right-radius: 0px;
                        }}"""
                    )
                rank.setFont(QFont("나눔스퀘어라운드 Bold", 10))
                rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
                rank.setGeometry(
                    0,
                    self.sim_potentialRank_rank_H * j,
                    self.sim_potentialRank_rank_ranking_W,
                    self.sim_potentialRank_rank_H,
                )
                self.widgetList.append(rank)

                potential = QLabel(texts[i][j][1], table_frame)
                if j == 0:
                    potential.setStyleSheet(
                        f"""QLabel {{
                            background-color: rgba({colors[i]}, {transparencies[i]});
                            border: 1px solid rgb({self.sim_colors4[i]});
                            border-top: 0px solid;
                            border-left: 0px solid;
                            border-right: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-bottom-right-radius: 0px;
                        }}"""
                    )
                    potential.setAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    potential.setStyleSheet(
                        f"""QLabel {{
                            background-color: transparent;
                            border: 1px solid rgb({self.sim_colors4[i]});
                            border-top: 0px solid;
                            border-left: 0px solid;
                            border-right: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-bottom-right-radius: 0px;
                        }}"""
                    )
                    potential.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                potential.setFont(QFont("나눔스퀘어라운드 Bold", 10))
                potential.setGeometry(
                    self.sim_potentialRank_rank_ranking_W,
                    self.sim_potentialRank_rank_H * j,
                    self.sim_potentialRank_rank_potential_W,
                    self.sim_potentialRank_rank_H,
                )
                self.widgetList.append(potential)
                self.sim_potentialRank_potentialList[i].append(potential)

                power = QLabel(texts[i][j][2], table_frame)
                if j == 0:
                    power.setStyleSheet(
                        f"""QLabel {{
                            background-color: rgba({colors[i]}, {transparencies[i]});
                            border: 1px solid rgb({self.sim_colors4[i]});
                            border-top: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-bottom-right-radius: 0px;
                        }}"""
                    )
                elif j == 15:
                    power.setStyleSheet(
                        f"""QLabel {{
                            background-color: transparent;
                            border: 1px solid rgb({self.sim_colors4[i]});
                            border-top: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-bottom-right-radius: 4px;
                        }}"""
                    )
                else:
                    power.setStyleSheet(
                        f"""QLabel {{
                            background-color: transparent;
                            border: 1px solid rgb({self.sim_colors4[i]});
                            border-top: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-bottom-right-radius: 0px;
                        }}"""
                    )
                power.setFont(QFont("나눔스퀘어라운드 Bold", 10))
                power.setAlignment(Qt.AlignmentFlag.AlignCenter)
                power.setGeometry(
                    self.sim_potentialRank_rank_ranking_W + self.sim_potentialRank_rank_potential_W,
                    self.sim_potentialRank_rank_H * j,
                    self.sim_potentialRank_rank_power_W,
                    self.sim_potentialRank_rank_H,
                )
                self.widgetList.append(power)
                self.sim_potentialRank_powerList[i].append(power)

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim3_frame4.y() + self.sim3_frame4.height() + self.sim_mainFrameMargin,
        )
        [i.show() for i in self.widgetList]
        self.updatePosition()

    def makeSimulType2(self):
        if not (self.sim_stat_inputCheck and self.sim_skill_inputCheck and self.sim_simInfo_inputCheck):
            self.makeNoticePopup("SimInputError")
            return

        self.removeSimulWidgets()
        self.sim_updateNavButton(1)

        self.simType = 2

        self.sim_powers, analysis, resultDet, results = self.simulateMacro(
            tuple(self.info_stats), tuple(self.info_skills), tuple(self.info_simInfo), random.random()
        )

        # 전투력
        self.sim2_frame1 = QFrame(self.sim_mainFrame)
        self.sim2_frame1.setGeometry(
            0,
            0,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_powerL_frame_H),
        )
        self.sim2_frame1.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")

        self.sim2_frame1_labelFrame, self.sim2_frame1_label = self.sim_returnTitleFrame(
            self.sim2_frame1, "전투력"
        )
        self.sim_power_list = self.sim_makePowerLabels(
            self.sim2_frame1, self.sim_powers
        )  # [[f, t, n], [f, t, n], [f, t, n], [f, t, n]]

        for i, (f, t, n) in enumerate(self.sim_power_list):
            f.setGeometry(
                self.sim_powerL_margin + (self.sim_powerL_width + self.sim_powerL_D) * i,
                self.sim_label_H + self.sim_widget_D,
                self.sim_powerL_width,
                self.sim_powerL_frame_H,
            )
            t.setGeometry(
                0,
                0,
                self.sim_powerL_width,
                self.sim_powerL_title_H,
            )
            n.setGeometry(
                0,
                self.sim_powerL_title_H,
                self.sim_powerL_width,
                self.sim_powerL_number_H,
            )

        # 분석
        self.sim2_frame2 = QFrame(self.sim_mainFrame)
        self.sim2_frame2.setGeometry(
            0,
            self.sim2_frame1.y() + self.sim2_frame1.height() + self.sim_main_D,
            928,
            self.sim_title_H
            + (
                self.sim_widget_D * 5
                + self.sim_analysis_frame_H
                + self.sim_dps_height
                + self.sim_dmg_height * 3
            ),
        )
        self.sim2_frame2.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")

        self.sim2_frame2_labelFrame, self.sim2_frame2_label = self.sim_returnTitleFrame(
            self.sim2_frame2, "분석"
        )

        details = ["min", "max", "std", "p25", "p50", "p75"]

        self.sim_analysis_list = [
            [],
            [],
            [],
            [],
        ]  # [[f, c, t, n, [[f, t, n] * 6]], [f, c, t, n, [[f, t, n] * 6]], [f, c, t, n, [[f, t, n] * 6]], [f, c, t, n, [[f, t, n] * 6]]]
        for i in range(4):
            frame = QFrame(self.sim2_frame2)
            frame.setGeometry(
                self.sim_analysis_margin + (self.sim_analysis_width + self.sim_analysis_D) * i,
                self.sim_label_H + self.sim_widget_D,
                self.sim_analysis_width,
                self.sim_analysis_frame_H,
            )
            frame.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-top-left-radius: 0px; border-top-right-radius: 6px; border-bottom-left-radius: 0px; border-bottom-right-radius: 6px; }"
            )
            self.sim_analysis_list[i].append(frame)

            color = QFrame(frame)
            color.setGeometry(
                0,
                0,
                self.sim_analysis_color_W,
                self.sim_analysis_frame_H,
            )
            color.setStyleSheet(
                f"QFrame {{ background-color: rgb({self.sim_colors4[i]}); border: 0px solid; border-radius: 0px; border-bottom: 1px solid #CCCCCC; border-left: 1px solid #CCCCCC; border-top: 1px solid #CCCCCC; }}"
            )
            self.sim_analysis_list[i].append(color)

            title = QLabel(analysis[i]["title"], frame)
            title.setGeometry(
                self.sim_analysis_color_W,
                0,
                self.sim_analysis_widthXC,
                self.sim_analysis_title_H,
            )
            title.setStyleSheet("QLabel { background-color: transparent; border: 0px solid; }")
            title.setFont(QFont("나눔스퀘어라운드 Bold", 14))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim_analysis_list[i].append(title)

            number = QLabel(analysis[i]["number"], frame)
            number.setGeometry(
                self.sim_analysis_color_W,
                self.sim_analysis_title_H,
                self.sim_analysis_widthXC,
                self.sim_analysis_number_H,
            )
            number.setStyleSheet("QLabel { background-color: transparent; border: 0px solid; }")
            number.setFont(QFont("나눔스퀘어라운드 ExtraBold", 18))
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim_analysis_list[i].append(number)

            self.sim_analysis_list[i].append([])
            for j in range(6):
                self.sim_analysis_list[i][4].append([])
                detail_frame = QFrame(frame)
                detail_frame.setGeometry(
                    self.sim_analysis_color_W
                    + self.sim_analysis_details_margin
                    + (self.sim_analysis_details_W + self.sim_analysis_details_margin) * (j % 3)
                    - 1,
                    self.sim_analysis_title_H
                    + self.sim_analysis_number_H
                    + self.sim_analysis_number_marginH
                    + self.sim_analysis_details_H * (j // 3),
                    self.sim_analysis_details_W,
                    self.sim_analysis_details_H,
                )
                detail_frame.setStyleSheet("QFrame { background-color: transparent; border: 0px solid; }")
                self.sim_analysis_list[i][4][j].append(detail_frame)

                detail_title = QLabel(details[j], detail_frame)
                detail_title.setGeometry(
                    0,
                    0,
                    self.sim_analysis_detailsT_W,
                    self.sim_analysis_details_H,
                )
                detail_title.setStyleSheet(
                    "QLabel { background-color: transparent; border: 0px solid; color: #A0A0A0 }"
                )
                detail_title.setFont(QFont("나눔스퀘어라운드 ExtraBold", 8))
                detail_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.sim_analysis_list[i][4][j].append(detail_title)

                detail_number = QLabel(analysis[i][details[j]], detail_frame)
                detail_number.setGeometry(
                    self.sim_analysis_detailsT_W,
                    0,
                    self.sim_analysis_detailsN_W,
                    self.sim_analysis_details_H,
                )
                detail_number.setStyleSheet("QLabel { background-color: transparent; border: 0px solid; }")
                detail_number.setFont(QFont("나눔스퀘어라운드 ExtraBold", 8))
                detail_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.sim_analysis_list[i][4][j].append(detail_number)

        ## DPS 분포
        self.sim_dpsGraph_frame = QFrame(self.sim2_frame2)
        self.sim_dpsGraph_frame.setGeometry(
            self.sim_dps_margin,
            self.sim_label_H + self.sim_analysis_frame_H + self.sim_widget_D * 2,
            self.sim_dps_width,
            self.sim_dps_height,
        )
        self.sim_dpsGraph_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )
        data = [sum([i[2] for i in j]) for j in results]
        self.sim_dpsGraph = DpsDistributionCanvas(self.sim_dpsGraph_frame, data)  # 시뮬레이션 결과
        self.sim_dpsGraph.move(5, 5)
        self.sim_dpsGraph.resize(self.sim_dps_width - 10, self.sim_dps_height - 10)

        ## 스킬 DPS
        self.sim_skillDpsGraph_frame = QFrame(self.sim2_frame2)
        self.sim_skillDpsGraph_frame.setGeometry(
            self.sim_dps_margin + self.sim_dps_width + self.sim_skillDps_margin,
            self.sim_label_H + self.sim_analysis_frame_H + self.sim_widget_D * 2,
            self.sim_skillDps_width,
            self.sim_skillDps_height,
        )
        self.sim_skillDpsGraph_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )
        data = [sum([i[2] for i in resultDet if i[0] == num]) for num in list(range(6)) + [-1]]
        # data = [round(total_dmgs[i] / sum(total_dmgs) * 100, 1) for i in range(7)]
        names = []
        for i in range(6):
            if i != -1:
                names.append(self.skillNameList[self.serverID][self.jobID][self.selectedSkillList[i]])
            else:
                names.append(None)
        self.sim_skillDpsGraph = SkillDpsDistributionCanvas(self.sim_skillDpsGraph_frame, data, names)
        self.sim_skillDpsGraph.move(10, 10)
        self.sim_skillDpsGraph.resize(self.sim_skillDps_width - 20, self.sim_skillDps_height - 20)

        ## 시간 경과에 따른 피해량
        self.sim_dmgTime_frame = QFrame(self.sim2_frame2)
        self.sim_dmgTime_frame.setGeometry(
            self.sim_dps_margin,
            self.sim_label_H + self.sim_analysis_frame_H + self.sim_dps_height + self.sim_widget_D * 3,
            self.sim_dmg_width,
            self.sim_dmg_height,
        )
        self.sim_dmgTime_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )

        timeStep, timeStepCount = 1, 61  # 61이라면 61초까지 시뮬레이션 돌려야함
        times = [i * timeStep for i in range(timeStepCount)]

        dps_list = []
        for result in results:
            dps_list.append([])
            for i in range(timeStepCount):
                dps_list[-1].append(sum([j[2] for j in result if i * timeStep <= j[1] < (i + 1) * timeStep]))

        mean_list = [sum([j[i] for j in dps_list]) / len(dps_list) for i in range(timeStepCount)]
        max_list = [max([j[i] for j in dps_list]) for i in range(timeStepCount)]
        min_list = [min([j[i] for j in dps_list]) for i in range(timeStepCount)]
        data = {
            "time": times,
            "max": max_list,
            "mean": mean_list,
            "min": min_list,
        }
        self.sim_dmgTime = DMGCanvas(self.sim_dmgTime_frame, data, "time")  # 시뮬레이션 결과
        self.sim_dmgTime.move(5, 5)
        self.sim_dmgTime.resize(self.sim_dmg_width - 10, self.sim_dmg_height - 10)

        ## 누적 피해량
        self.sim_totalDmg_frame = QFrame(self.sim2_frame2)
        self.sim_totalDmg_frame.setGeometry(
            self.sim_dps_margin,
            self.sim_label_H
            + self.sim_analysis_frame_H
            + self.sim_dps_height
            + self.sim_dmg_height
            + self.sim_widget_D * 4,
            self.sim_dmg_width,
            self.sim_dmg_height,
        )
        self.sim_totalDmg_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )

        sums = [sum([i[2] for i in j]) for j in results]
        max_idx = sums.index(max(sums))
        min_idx = sums.index(min(sums))

        total_list = []
        for dps in dps_list:
            total_list.append([])
            for i in range(timeStepCount):
                total = sum([j for j in dps[: i + 1]])
                total_list[-1].append(total)

        means = [sum([j[i] for j in total_list]) / len(total_list) for i in range(timeStepCount)]
        data = {
            "time": times,
            "max": total_list[max_idx],
            "mean": means,
            "min": total_list[min_idx],
        }
        self.sim_totalDmg = DMGCanvas(self.sim_totalDmg_frame, data, "cumulative")  # 시뮬레이션 결과
        self.sim_totalDmg.move(5, 5)
        self.sim_totalDmg.resize(self.sim_dmg_width - 10, self.sim_dmg_height - 10)

        ## 스킬별 누적 기여도
        self.sim_skillContribute_frame = QFrame(self.sim2_frame2)
        self.sim_skillContribute_frame.setGeometry(
            self.sim_dps_margin,
            self.sim_label_H
            + self.sim_analysis_frame_H
            + self.sim_dps_height
            + self.sim_dmg_height * 2
            + self.sim_widget_D * 5,
            self.sim_dmg_width,
            self.sim_dmg_height,
        )
        self.sim_skillContribute_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )

        skillsData = []
        for num in list(range(6)) + [-1]:
            skillsData.append([])
            for i in range(timeStepCount):
                skillsData[-1].append(
                    sum([j[2] for j in resultDet if j[0] == num and j[1] < (i + 1) * timeStep])
                )

        totalData = []
        for i in range(timeStepCount):
            totalData.append(sum([j[2] for j in resultDet if j[1] < (i + 1) * timeStep]))

        data_normalized = []
        for i in range(7):
            data_normalized.append([skillsData[i][j] / totalData[j] for j in range(timeStepCount)])

        data_cumsum = [[0.0 for _ in row] for row in data_normalized]
        for i in range(len(data_normalized)):
            for j in range(len(data_normalized[0])):
                data_cumsum[i][j] = sum(row[j] for row in data_normalized[: i + 1])

        names = []
        for i in range(6):
            if i != -1:
                names.append(self.skillNameList[self.serverID][self.jobID][self.selectedSkillList[i]])
            else:
                names.append(None)

        data = {
            "time": times,
            "skills_normalized": data_normalized,
            "skills_sum": data_cumsum,
        }
        self.sim_skillContribute = SkillContributionCanvas(
            self.sim_skillContribute_frame, data, names
        )  # 시뮬레이션 결과
        self.sim_skillContribute.move(5, 5)
        self.sim_skillContribute.resize(
            self.sim_dmg_width - 10,
            self.sim_dmg_height - 10,
        )

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim2_frame2.y() + self.sim2_frame2.height() + self.sim_mainFrameMargin,
        )
        [i.show() for i in self.page2.findChildren(QWidget)]
        self.updatePosition()

    def makeSimulType1(self):
        self.removeSimulWidgets()
        self.sim_updateNavButton(0)

        self.simType = 1

        # 캐릭터 스탯
        self.sim1_frame1 = QFrame(self.sim_mainFrame)
        self.sim1_frame1.setGeometry(
            0,
            0,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_stat_frame_H) * 3,
        )
        self.sim1_frame1.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")

        self.sim1_frame1_labelFrame, self.sim1_frame1_label = self.sim_returnTitleFrame(
            self.sim1_frame1, "캐릭터 스탯"
        )
        self.sim_makeStatInput(self.sim1_frame1)
        self.sim_stat_inputs[0].setFocus()

        margin, count = 21, 6
        for i in range(18):
            self.sim_stat_frames[i].move(
                self.sim_stat_margin + self.sim_stat_width * (i % count) + margin * (i % count),
                self.sim1_frame1_labelFrame.height()
                + self.sim_widget_D * ((i // count) + 1)
                + self.sim_stat_frame_H * (i // count),
            )
            self.sim_stat_labels[i].setGeometry(
                0,
                0,
                self.sim_stat_width,
                self.sim_stat_label_H,
            )
            self.sim_stat_inputs[i].setGeometry(
                0, self.sim_stat_label_H, self.sim_stat_width, self.sim_stat_input_H
            )

            self.sim_stat_inputs[i].setText(str(self.info_stats[i]))

        # 스킬 레벨
        self.sim1_frame2 = QFrame(self.sim_mainFrame)
        self.sim1_frame2.setGeometry(
            0,
            self.sim1_frame1.y() + self.sim1_frame1.height() + self.sim_main_D,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_skill_frame_H) * 2,
        )
        self.sim1_frame2.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")

        self.sim1_frame2_labelFrame, self.sim1_frame2_label = self.sim_returnTitleFrame(
            self.sim1_frame2, "스킬 레벨"
        )
        self.sim_makeSkillInput(self.sim1_frame2)

        margin, count = 66, 4
        for i in range(8):
            self.sim_skill_frames[i].move(
                self.sim_skill_margin + self.sim_skill_width * (i % count) + margin * (i % count),
                self.sim1_frame2_labelFrame.height()
                + self.sim_widget_D * ((i // count) + 1)
                + self.sim_skill_frame_H * (i // count),
            )
            self.sim_skill_names[i].setGeometry(
                0,
                0,
                self.sim_skill_width,
                self.sim_skill_name_H,
            )
            self.sim_skill_levels[i].setGeometry(
                self.sim_skill_image_Size,
                self.sim_skill_name_H,
                self.sim_skill_right_W,
                self.sim_skill_level_H,
            )
            self.sim_skill_inputs[i].setGeometry(
                self.sim_skill_image_Size,
                self.sim_skill_name_H + self.sim_skill_level_H,
                self.sim_skill_right_W,
                self.sim_skill_input_H,
            )

            self.sim_skill_inputs[i].setText(str(self.info_skills[i]))

        # 추가 정보 입력
        self.sim1_frame3 = QFrame(self.sim_mainFrame)
        self.sim1_frame3.setGeometry(
            0,
            self.sim1_frame2.y() + self.sim1_frame2.height() + self.sim_main_D,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_simInfo_frame_H) * 1,
        )
        self.sim1_frame3.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }")

        self.sim1_frame3_labelFrame, self.sim1_frame3_label = self.sim_returnTitleFrame(
            self.sim1_frame3, "추가 정보 입력"
        )
        self.sim_makeSimInfoInput(self.sim1_frame3)

        margin = 60
        for i in range(3):
            self.sim_simInfo_frames[i].move(
                self.sim_simInfo_margin + (self.sim_simInfo_width + margin) * i,
                self.sim1_frame3_labelFrame.height() + self.sim_widget_D,
            )
            self.sim_simInfo_labels[i].setGeometry(
                0,
                0,
                self.sim_simInfo_width,
                self.sim_simInfo_label_H,
            )
            self.sim_simInfo_inputs[i].setGeometry(
                0, self.sim_simInfo_label_H, self.sim_simInfo_width, self.sim_simInfo_input_H
            )

            self.sim_simInfo_inputs[i].setText(str(self.info_simInfo[i]))

        # Tab Order 설정
        tabOrders = self.sim_stat_inputs + self.sim_skill_inputs + self.sim_simInfo_inputs
        for i in range(len(tabOrders) - 1):
            QWidget.setTabOrder(tabOrders[i], tabOrders[i + 1])

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim1_frame3.y() + self.sim1_frame3.height() + self.sim_mainFrameMargin,
        )
        [i.show() for i in self.page2.findChildren(QWidget)]
        self.updatePosition()

    def sim_loadCharacterInfo(self):
        self.sim_info_charData = None

        try:
            data = [
                {"job": 0, "level": 200},
                {"job": 2, "level": 190},
                {"job": 0, "level": 180},
            ]
        except:
            self.makeNoticePopup("SimCharLoadError")
            return

        for i, j in enumerate(data):
            job, level = j["job"], j["level"]
            if job == self.jobID:
                self.sim4_info_charButtonList[i].setText(f"{self.jobList[self.serverID][job]} | Lv.{level}")
                self.sim4_info_charButtonList[i].setStyleSheet(
                    f"""QPushButton {{
                    background-color: #FFFFFF;
                    border: 1px solid {self.sim_input_colors[1]};
                    border-radius: 8px;
                    color: #000000;
                    }}
                    QPushButton:hover {{
                        background-color: #F0F0F0;
                    }}"""
                )

                self.sim4_info_charButtonList[i].clicked.connect(
                    partial(lambda x, y: self.sim_selectCharacter(x, y), i, j)
                )
            else:
                self.sim4_info_charButtonList[i].setText(f"{self.jobList[self.serverID][job]} | Lv.{level}")
                self.sim4_info_charButtonList[i].setStyleSheet(
                    f"""QPushButton {{
                    background-color: #FFFFFF;
                    border: 1px solid {self.sim_input_colors[1]};
                    border-radius: 8px;
                    color: rgb(153, 153, 153);
                    }}"""
                )

                try:
                    self.sim4_info_charButtonList[i].clicked.disconnect()
                except:
                    pass

    def sim_selectCharacter(self, index, data):
        self.sim_loadCharacterInfo()

        self.sim_info_charData = data

        self.sim4_info_charButtonList[index].setStyleSheet(
            f"""QPushButton {{
            background-color: #CCCCCC;
            border: 1px solid {self.sim_input_colors[1]};
            border-radius: 8px;
            color: #000000;
            }}"""
        )

    def sim_info_powersClicked(self, num):
        self.sim_info_powerActive[num] = not self.sim_info_powerActive[num]

        for i in range(4):
            self.sim4_info_powerButtons[i].setStyleSheet(
                f"""QPushButton {{
                background-color: #FFFFFF;
                border: 1px solid {self.sim_input_colors[1]};
                border-radius: 5px;
                color: {"#000000" if self.sim_info_powerActive[i] else "rgb(153, 153, 153)"};
                }}
                QPushButton:hover {{
                    background-color: #F0F0F0;
                }}"""
            )

    def sim_card_save(self):
        if not self.sim_card_updated:
            self.makeNoticePopup("SimCardNotUpdated")
            return

        scale_factor = 3
        original_size = self.sim4_frame_card.size()
        scaled_size = original_size * scale_factor

        pixmap = QPixmap(scaled_size)
        pixmap.fill()

        painter = QPainter(pixmap)
        painter.scale(scale_factor, scale_factor)
        self.sim4_frame_card.render(painter)
        painter.end()

        # Open a file dialog to save the image
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilters(["Images (*.png *.jpg *.bmp)"])
        file_dialog.setDefaultSuffix("png")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            pixmap.save(file_path)
            os.startfile(file_path)

    def sim_card_update(self):
        if self.sim_info_charData is None:
            self.makeNoticePopup("SimCardError")
            return

        if not any(self.sim_info_powerActive):
            self.makeNoticePopup("SimCardPowerError")
            return

        name = self.sim4_info_nicknameInput.text()
        try:
            response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}")
            name = response.json()["name"]
            url = f"https://starlightskins.lunareclipse.studio/render/default/{name}/full?renderScale=3.2"
        except:
            self.makeNoticePopup("SimCardError")
            return

        pixmap = QPixmap(convertResourcePath("resource\\image\\card_bg.png"))
        self.sim4_card_image_bg.setPixmap(pixmap)
        image = requests.get(url).content
        pixmap = QPixmap()
        pixmap.loadFromData(image)

        h_ratio = 282 / pixmap.height()
        width = round(pixmap.width() * h_ratio)
        dWidth = width - (self.sim_charCard_image_W - 30)

        self.sim4_card_image.setGeometry(
            self.sim_charCard_image_margin + 15 - dWidth // 2,
            self.sim_charCard_image_margin + self.sim_charCard_title_H + 15,
            round(pixmap.width() * h_ratio),
            self.sim_charCard_image_H - 30,
        )
        self.sim4_card_image.setPixmap(pixmap)

        self.adjustFontSize(self.sim4_card_name, name, 18)
        self.sim4_card_job.setText(self.jobList[self.serverID][self.jobID])
        self.sim4_card_level.setText(f"Lv.{self.sim_info_charData["level"]}")

        countF = self.sim_info_powerActive.count(False)
        count = 0
        for i in range(4):
            if self.sim_info_powerActive[i]:
                self.sim4_card_powers[i][0].setGeometry(
                    self.sim_charCard_powerFrame_margin,
                    self.sim_charCard_powerFrame_y + self.sim_charCard_powerFrame_H * count + 20 * countF,
                    self.sim_charCard_powerFrame_W,
                    self.sim_charCard_powerFrame_H,
                )
                self.sim4_card_powers[i][2].setText(f"{self.sim_powers[i]}")

                self.sim4_card_powers[i][0].show()
                count += 1
            else:
                self.sim4_card_powers[i][0].hide()

        self.sim_card_updated = True

    def sim_returnTitleFrame(self, mainFrame, title):
        labelFrame = QFrame(mainFrame)
        labelFrame.setGeometry(0, 0, 928, self.sim_label_H)
        labelFrame.setStyleSheet(
            f"QFrame {{ background-color: rgb(255, 255, 255); border: none; border-bottom: 1px solid {self.sim_labelFrame_color}; }}"
        )
        label = QLabel(title, labelFrame)
        label.setGeometry(
            self.sim_label_x,
            0,
            928 - self.sim_label_x,
            self.sim_label_H,
        )
        label.setFont(QFont("나눔스퀘어라운드 Bold", 16))

        return labelFrame, label

    def sim_updateNavButton(self, num):
        for i in [0, 1, 2, 3]:
            self.sim_navButtons[i].setStyleSheet(
                f"""
                QPushButton {{ background-color: rgb(255, 255, 255); border: none; border-bottom: {"2" if i == num else "0"}px solid #9180F7; }}
                QPushButton:hover {{ background-color: rgb(234, 234, 234); }}
                """
            )

    def sim_makePowerLabels(self, mainframe, texts, font_size=18):
        titles = ["보스데미지", "일반데미지", "보스", "사냥"]
        power_list = [[], [], [], []]
        for i in range(4):
            frame = QFrame(mainframe)
            power_list[i].append(frame)

            title = QLabel(titles[i], frame)
            title.setStyleSheet(
                f"QLabel {{ background-color: rgb({self.sim_colors4[i]}); border: 1px solid rgb({self.sim_colors4[i]}); border-bottom: 0px solid; border-top-left-radius: 4px; border-top-right-radius: 4px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; }}"
            )
            title.setFont(QFont("나눔스퀘어라운드 ExtraBold", 14))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            power_list[i].append(title)

            number = QLabel(texts[i], frame)
            number.setStyleSheet(
                f"QLabel {{ background-color: rgba({self.sim_colors4[i]}, 120); border: 1px solid rgb({self.sim_colors4[i]}); border-top: 0px solid; border-top-left-radius: 0px; border-top-right-radius: 0px; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px }}"
            )
            number.setFont(QFont("나눔스퀘어라운드 ExtraBold", font_size))
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            power_list[i].append(number)

        return power_list

    def sim_makeSimInfoInput(self, mainframe):
        statList = [
            "몬스터 내공",
            "보스 내공",
            "포션 회복량",
        ]

        self.sim_simInfo_frames = []
        self.sim_simInfo_labels = []
        self.sim_simInfo_inputs = []
        for i in range(len(statList)):
            frame = QFrame(mainframe)
            frame.setStyleSheet("QFrame { background-color: transparent; border: 0px solid; }")
            self.sim_simInfo_frames.append(frame)

            label = QLabel(statList[i], frame)
            label.setStyleSheet("QLabel { background-color: transparent; border: 0px solid; }")
            label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
            self.sim_simInfo_labels.append(label)

            lineEdit = QLineEdit("", frame)
            lineEdit.setFont(QFont("나눔스퀘어라운드 Bold", 14))
            lineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lineEdit.setStyleSheet(
                f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
            )

            # 데이터 입력시 실행할 함수 연결
            lineEdit.textChanged.connect(self.sim_simInfo_inputChanged)
            self.sim_simInfo_inputs.append(lineEdit)

    def sim_potential_update(self):
        indexList = [
            self.sim_potential_stat0.currentText(),
            self.sim_potential_stat1.currentText(),
            self.sim_potential_stat2.currentText(),
        ]

        stats = self.info_stats.copy()
        for i in range(3):
            num, value = self.potentialStatList[indexList[i]]
            stats[num] += value

        powers = self.simulateMacro(tuple(stats), tuple(self.info_skills), tuple(self.info_simInfo), 1)

        diff_powers = [int(powers[i]) - int(self.sim_powers[i]) for i in range(4)]

        [self.sim_potential_power_list[i][2].setText(f"{diff_powers[i]:+}") for i in range(4)]

    def sim_update_efficiency(self):
        if self.sim_efficiency_statL.currentIndex() == self.sim_efficiency_statR.currentIndex():
            [
                self.sim_efficiency_power_list[i][2].setText(
                    f"{int(self.sim_efficiency_statInput.text()):.2f}"
                )
                for i in range(4)
            ]
            return

        stats = self.info_stats.copy()
        stats[self.sim_efficiency_statL.currentIndex()] += int(self.sim_efficiency_statInput.text())
        powers = self.simulateMacro(tuple(stats), tuple(self.info_skills), tuple(self.info_simInfo), 1)
        reqStats = self.getRequiredStat(powers, self.sim_efficiency_statR.currentIndex())

        [self.sim_efficiency_power_list[i][2].setText(reqStats[i]) for i in range(4)]

    def sim_efficiency_Changed(self):
        text = self.sim_efficiency_statInput.text()
        index = self.sim_efficiency_statL.currentIndex()
        if not text.isdigit():
            [self.sim_efficiency_power_list[i][2].setText("오류") for i in range(4)]
            return

        stat = self.info_stats[self.sim_efficiency_statL.currentIndex()] + int(text)

        if self.statRangeList[index][0] <= stat:
            if self.statRangeList[index][1] == None:
                self.sim_update_efficiency()
                return
            else:
                if stat <= self.statRangeList[index][1]:
                    self.sim_update_efficiency()
                    return
                [self.sim_efficiency_power_list[i][2].setText("오류") for i in range(4)]
                return
        [self.sim_efficiency_power_list[i][2].setText("오류") for i in range(4)]
        return

    def sim_simInfo_inputChanged(self):
        # 스탯이 정상적으로 입력되었는지 확인
        def checkInput(num, text) -> bool:
            if not text.isdigit():
                return False

            match num:
                case 0 | 1:
                    if int(text) == 0:
                        return False
                    return True
                case _:
                    return True

            return True

        if not False in [checkInput(i, j.text()) for i, j in enumerate(self.sim_simInfo_inputs)]:  # 모두 통과
            for i in self.sim_simInfo_inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            self.info_simInfo = [int(i.text()) for i in self.sim_simInfo_inputs]
            self.dataSave()
            self.sim_simInfo_inputCheck = True

        else:  # 하나라도 통과X
            for i, j in enumerate(self.sim_simInfo_inputs):
                if not checkInput(i, j.text()):  # 통과X면 빨간색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 2px solid {self.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
                    )
            self.sim_simInfo_inputCheck = False

    def sim_makeSkillInput(self, mainframe):
        texts = self.skillNameList[self.serverID][self.jobID]

        self.sim_skill_frames = []
        self.sim_skill_names = []
        self.sim_skill_images = []
        self.sim_skill_levels = []
        self.sim_skill_inputs = []
        for i in range(8):
            frame = QFrame(mainframe)
            frame.setStyleSheet("QFrame { background-color: transparent; border: 0px solid black; }")
            self.sim_skill_frames.append(frame)

            name = QLabel(texts[i], frame)
            name.setStyleSheet(
                f"QLabel {{ border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
            )
            name.setFont(QFont("나눔스퀘어라운드 Bold", 14))
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim_skill_names.append(name)

            label = QLabel("레벨", frame)
            label.setStyleSheet("QLabel { background-color: transparent; border: 0px solid; }")
            label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim_skill_levels.append(label)

            lineEdit = QLineEdit("", frame)
            lineEdit.setFont(QFont("나눔스퀘어라운드 Bold", 12))
            lineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lineEdit.setStyleSheet(
                f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
            )

            # 데이터 입력시 실행할 함수 연결
            lineEdit.textChanged.connect(self.sim_skill_inputChanged)
            self.sim_skill_inputs.append(lineEdit)

        for i in range(8):
            image = QPushButton(self.sim_skill_frames[i])
            image.setGeometry(
                0,
                self.sim_skill_name_H,
                self.sim_skill_image_Size,
                self.sim_skill_image_Size,
            )
            image.setStyleSheet("QPushButton { background-color: transparent; border: 0px solid; }")
            pixmap = QPixmap(self.getSkillImage(i))
            image.setIcon(QIcon(pixmap))
            image.setIconSize(QSize(self.sim_skill_image_Size, self.sim_skill_image_Size))
            self.sim_skill_images.append(image)

    def sim_skill_inputChanged(self):
        # 스킬이 정상적으로 입력되었는지 확인
        def checkInput(text: str) -> bool:
            if not text.isdigit():
                return False

            if int(text) == 0 or int(text) > 30:
                return False

            return True

        if not False in [checkInput(i.text()) for i in self.sim_skill_inputs]:  # 모두 통과
            for i in self.sim_skill_inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            if self.simType == 1:
                self.info_skills = [int(i.text()) for i in self.sim_skill_inputs]
                self.dataSave()
            self.sim_skill_inputCheck = True

        else:  # 하나라도 통과X
            for i in self.sim_skill_inputs:
                if not checkInput(i.text()):  # 통과X면 빨간색
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 2px solid {self.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
                    )
            self.sim_skill_inputCheck = False

        if self.simType == 3:
            self.update_additional_power_list()

    def update_additional_power_list(self):
        if self.sim_skill_inputCheck and self.sim_stat_inputCheck:
            stats = self.info_stats.copy()
            stats = [stats[i] + int(self.sim_stat_inputs[i].text()) for i in range(len(stats))]
            skills = self.info_skills.copy()
            skills = [skills[i] + int(self.sim_skill_inputs[i].text()) for i in range(len(skills))]
            powers = self.simulateMacro(tuple(stats), tuple(skills), tuple(self.info_simInfo), 1)

            diff_powers = [int(powers[i]) - int(self.sim_powers[i]) for i in range(4)]

            [
                self.sim_additional_power_list[i][2].setText(
                    f"{int(powers[i]):}\n({diff_powers[i]:+}, {diff_powers[i] / int(self.sim_powers[i]) * 100:+.1f}%)"
                )
                for i in range(4)
            ]
        else:
            [self.sim_additional_power_list[i][2].setText("오류") for i in range(4)]

    def sim_makeStatInput(self, mainframe):
        self.sim_stat_frames = []
        self.sim_stat_labels = []
        self.sim_stat_inputs = []
        for i in range(len(self.statList)):
            frame = QFrame(mainframe)
            frame.setStyleSheet("QFrame { background-color: transparent; border: 0px solid; }")
            self.sim_stat_frames.append(frame)

            label = QLabel(self.statList[i], frame)
            label.setStyleSheet("QLabel { background-color: transparent; border: 0px solid; }")
            label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
            self.sim_stat_labels.append(label)

            lineEdit = QLineEdit("", frame)
            lineEdit.setFont(QFont("나눔스퀘어라운드 Bold", 14))
            lineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lineEdit.setStyleSheet(
                f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
            )

            # 데이터 입력시 실행할 함수 연결
            lineEdit.textChanged.connect(self.sim_stat_inputChanged)
            self.sim_stat_inputs.append(lineEdit)

    def sim_stat_inputChanged(self):
        # 스탯이 정상적으로 입력되었는지 확인
        def checkInput(num, text) -> bool:
            # 기본데미지 = 공격력 * (근력 + 지력) * (1 + 파괴력 * 0.01) * 내공계수
            # 0공, 1방, 2파괴력, 3근력, 4지력, 5경도, 6치확, 7치뎀, 8보뎀, 9명중, 10회피, 11상태이상저항, 12내공, 13체력, 14공속, 15포션회복, 16운, 17경험치
            if self.simType == 1:
                if not text.isdigit():
                    return False

                if self.statRangeList[num][0] <= int(text):
                    if self.statRangeList[num][1] == None:
                        return True
                    else:
                        if int(text) <= self.statRangeList[num][1]:
                            return True
                        return False
                return False
            else:  # self.simType == 3
                try:
                    value = int(text)
                except ValueError:
                    return False

                stat = self.info_stats[num] + value
                if self.statRangeList[num][0] <= stat:
                    if self.statRangeList[num][1] == None:
                        return True
                    else:
                        if stat <= self.statRangeList[num][1]:
                            return True
                        return False
                return False

        if not False in [checkInput(i, j.text()) for i, j in enumerate(self.sim_stat_inputs)]:  # 모두 digit
            for i in self.sim_stat_inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            if self.simType == 1:
                self.info_stats = [int(i.text()) for i in self.sim_stat_inputs]
                self.dataSave()
            self.sim_stat_inputCheck = True

        else:  # 하나라도 통과X
            for i, j in enumerate(self.sim_stat_inputs):
                if not checkInput(i, j.text()):  # 통과X면 빨간색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 2px solid {self.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:  # 통과O면 원래색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
                    )
            self.sim_stat_inputCheck = False

        if self.simType == 3:
            self.update_additional_power_list()

    def getRequiredStat(self, powers, stat_num):
        reqStats = []
        reqStats.append(self.calculateRequiredStat(powers[0], stat_num, 0))
        reqStats.append(self.calculateRequiredStat(powers[1], stat_num, 1))
        reqStats.append(self.calculateRequiredStat(powers[2], stat_num, 2))
        reqStats.append(self.calculateRequiredStat(powers[3], stat_num, 3))

        return reqStats

    def calculateRequiredStat(self, power, stat_num, power_num):
        def checkInput(stat) -> bool:
            num = self.sim_efficiency_statR.currentIndex()
            if self.statRangeList[num][0] <= stat:
                if self.statRangeList[num][1] == None:
                    return True
                else:
                    if stat <= self.statRangeList[num][1]:
                        return True
                    return False
            return False

        stats = self.info_stats.copy()
        baseStat = self.info_stats[stat_num]
        current_power = self.simulateMacro(
            tuple(stats), tuple(self.info_skills), tuple(self.info_simInfo), 1
        )[power_num]

        # 1씩 증가시키며 범위 알아내기
        low, high = 0, 1
        step = 1
        num = 0
        while current_power < power and num < 10:
            if not checkInput(baseStat + low):
                return "0"
            stats[stat_num] = baseStat + high
            if stat_num == 12:
                stats[stat_num] = int(stats[stat_num])

            current_power = self.simulateMacro(
                tuple(stats), tuple(self.info_skills), tuple(self.info_simInfo), 1
            )[power_num]

            if current_power >= power:
                break

            # print(f"{low=}, {high=}, {step=}")

            low = high
            high += step
            step *= 2
            num += 1

        if num == 10:
            return "0"

        # 범위 내에서 이분탐색
        epsilon = 0.005
        num = 0
        while high - low > epsilon and num < 15:
            if not checkInput(baseStat + low):
                return "0"
            mid = (low + high) * 0.5
            stats[stat_num] = baseStat + mid
            if stat_num == 12:
                stats[stat_num] = int(stats[stat_num])
            # print(tuple(stats), tuple(self.info_skills), tuple(self.info_simInfo))
            current_power = self.simulateMacro(
                tuple(stats), tuple(self.info_skills), tuple(self.info_simInfo), 1
            )[power_num]

            # print(f"{low=}, {high=}, {mid=}")

            if current_power < power:
                low = mid
            else:
                high = mid

            num += 1

        # print("\n")
        return f"{(low + high) * 0.5:.2f}"

    @lru_cache
    def simulateMacro(self, stats: tuple, skillLevels: tuple, simInfo: tuple, randomSeed):
        def runSimul(attackDetails, buffDetails, stats, boss, simInfo, naegongDiff, deterministic=False):
            def getStatus(stats, nowTime, buff_list):
                status = list(stats).copy()
                for buff in buff_list:
                    if buff[0] <= nowTime <= buff[1]:
                        status[buff[2]] += buff[3]
                return status

            def getNaegongDiff(stats, naegong, naegongDiff):
                diff = naegong - stats[12]
                for (low, high), multiplier in naegongDiff.items():
                    if low <= diff <= high:
                        return multiplier

            def getDMG(stats, boss, naegong, naegongDiff, deterministic):
                # print(stats[0])
                dmg = (
                    stats[0]  # 공격력
                    * (stats[3] + stats[4])  # 근력 + 지력
                    * (1 + stats[2] * 0.01)  # 파괴력
                    * getNaegongDiff(stats, naegong, naegongDiff)
                    * ((1 + stats[8] * 0.01) if boss else 1)
                    * 0.01  # 보정계수
                )

                if deterministic:
                    crit_prob = stats[6] if stats[6] <= 100 else 100
                    dmg *= 1 + crit_prob * stats[7] * 0.0001
                    dmg *= 1.1  # 최소, 최대데미지 중간
                    return dmg

                dmg *= random.uniform(1, 1.2)  # 최소, 최대데미지
                return dmg * (1 + stats[7] * 0.01) if random.random() < stats[6] * 0.01 else dmg

            def merge_buff(data):
                # 지속 시간이 끝나는 시간 추가
                intervals = [
                    [start, round(start + duration, 2), buff_type, value]
                    for start, buff_type, value, duration in data
                ]

                # 종류와 값을 기준으로 그룹화
                grouped = {}
                for start, end, buff_type, value in intervals:
                    key = (buff_type, value)
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append([start, end])

                # 각 그룹의 겹치는 구간 병합
                merged_intervals = []
                for (buff_type, value), times in grouped.items():
                    times.sort()  # 시작 시간을 기준으로 정렬
                    merged = [times[0]]
                    for current in times[1:]:
                        prev = merged[-1]
                        if current[0] <= prev[1]:  # 겹침 확인
                            prev[1] = max(prev[1], current[1])  # 병합
                        else:
                            merged.append(current)
                    for start, end in merged:
                        merged_intervals.append((start, end, buff_type, value))

                # 시작 시간 기준으로 정렬
                merged_intervals.sort()
                return tuple(merged_intervals)

            buffInfo = merge_buff(buffDetails)  # [[start, type, value, duration], ...]
            attacks = []  # [type, time, damage]
            naegong = simInfo[1] if boss else simInfo[0]
            ## 시뮬레이션 시작
            for attack in attackDetails:
                status = getStatus(stats, attack[1], buffInfo)
                dmg = round(getDMG(status, boss, naegong, naegongDiff, deterministic) * attack[2], 5)
                attacks.append([attack[0], attack[1], dmg])

            # if deterministic:
            #     pprint(attacks)
            return attacks

        def calculate_percentile(data, percentile):
            data_sorted = sorted(data)
            rank = (percentile * 0.01) * (len(data) - 1) + 1
            lower_index = int(rank) - 1
            fraction = rank - int(rank)
            if lower_index + 1 < len(data):
                result = data_sorted[lower_index] + fraction * (
                    data_sorted[lower_index + 1] - data_sorted[lower_index]
                )
            else:
                result = data_sorted[lower_index]
            return result

        def calculate_std(data):
            # Step 1: 평균 계산
            mean = sum(data) / len(data)

            # Step 2: 각 데이터에서 평균을 뺀 제곱의 합 계산
            squared_differences = [(x - mean) ** 2 for x in data]

            # Step 3: 분산 계산
            variance = sum(squared_differences) / len(data)

            # Step 4: 표준편차 계산
            std_dev = variance**0.5

            return std_dev

        if randomSeed != 1:
            random.seed(randomSeed)
        simulatedSkills = self.getSimulatedSKillList(stats[14])

        # 1초 이내에 같은 스킬 사용 => 콤보
        for num, skill in enumerate(simulatedSkills):
            i = 1
            while (num >= i) and (skill[1] - simulatedSkills[num - i][1] <= 1000):

                if (simulatedSkills[num - i][0] == skill[0]) and (
                    simulatedSkills[num - i][2]
                    < self.skillComboCountList[self.serverID][self.jobID][self.selectedSkillList[skill[0]]]
                ):
                    simulatedSkills[num].append(simulatedSkills[num - i][2] + 1)
                    break

                i += 1

            # 콤보가 아닌 경우 0번콤보
            if len(simulatedSkills[num]) == 2:
                simulatedSkills[num].append(0)

        # 평타 추가
        num, delay = 0, 1
        while (t := num * (100 - stats[14]) * 10 * delay) <= 61000:
            simulatedSkills.append([-1, t])
            num += 1

        # 시간 단위를 1초로 변경
        for i in range(len(simulatedSkills)):
            simulatedSkills[i][1] = round(simulatedSkills[i][1] * 0.001, 2)

        # 스킬 세부사항 모으기
        attackDetails = []  # [스킬 번호, 시간, 데미지]
        buffDetails = []  #
        for attack in simulatedSkills:
            # 평타
            if attack[0] == -1:
                attackDetails.append(tuple(attack + [1.0]))
                continue

            # 스킬
            skillLevels = [0] * 8  # temp: self.info_skills -> info_skills = 0 * 8

            # [[0.0, [0, 0.5]], [0.1, [0, 0.5]], [0.2, [0, 0.5]], [0.3, [0, 0.5]], [0.4, [0, 0.5]]]
            skills = self.skillAttackData[self.serverID][self.jobID][self.selectedSkillList[attack[0]]][
                skillLevels[self.selectedSkillList[attack[0]]]
            ][attack[2]]

            for skill in skills:
                # [time, [type(0: damage, 1: buff), [buff_type, buff_value, buff_duration] or damage_value]]
                if skill[1][0] == 0:  # 공격
                    attackDetails.append(
                        (
                            attack[0],  # 스킬 번호
                            round(attack[1] + skill[0], 2),  # 시간
                            skill[1][1],  # 데미지
                        )
                    )
                else:  # 버프
                    buffDetails.append(
                        (
                            round(attack[1] + skill[0], 2),  # 시간
                            skill[1][1][0],  # 버프 종류
                            skill[1][1][1],  # 버프 값
                            skill[1][1][2],  # 버프 지속시간
                        )
                    )

        # 시간순으로 정렬
        attackDetails.sort(key=lambda x: x[1])
        buffDetails.sort(key=lambda x: x[0])
        buffDetails = tuple(buffDetails)
        naegongDiff = self.naegongDiff

        # print(attackDetails)
        # print(buffDetails)

        ## 전투력
        # 기본데미지 = 공격력 * (근력 + 지력) * (1 + 파괴력 * 0.01) * 내공계수
        # 0공, 1방, 2파괴력, 3근력, 4지력, 5경도, 6치확, 7치뎀, 8보뎀, 9명중, 10회피, 11상태이상저항, 12내공, 13체력, 14공속, 15포션회복, 16운, 17경험치
        boss_attacks = runSimul(
            attackDetails, buffDetails, stats, True, simInfo, naegongDiff, deterministic=True
        )
        normal_attacks = runSimul(
            attackDetails, buffDetails, stats, False, simInfo, naegongDiff, deterministic=True
        )
        sum_BossDMG = sum([i[2] for i in boss_attacks])
        sum_NormalDMG = sum([i[2] for i in normal_attacks])

        # 데미지감소 = 방어력 * 0.5 + 체력 * 경도 * 0.001
        dmgReduction = stats[1] * 0.5 + stats[13] * stats[5] * 0.001
        # dmgReduction = stats[1] * 0.8 + stats[13] * stats[5] * 0.0004
        # 초당 회복량 = 체력 * 자연회복 * 0.2 + 포션회복 * 0.5
        recovery = stats[13] * 0.1 * 0.2 + simInfo[2] * (1 + stats[15] * 0.01) * 0.5

        powers = [
            sum_BossDMG * self.coef_bossDMG,  # 보스데미지
            sum_NormalDMG * self.coef_normalDMG,  # 일반데미지
            sum_BossDMG
            # * self.coef_bossDMG  # 보스데미지
            # * (stats[13] ** 0.5)  # 체력 ** 0.5
            # * (dmgReduction + recovery)  # 뎀감 + 초당회복량 = 초당 버틸 수 있는 체력
            * (
                stats[13] + dmgReduction * 5 + recovery * 5
            )  # 5초마다 한 번씩 피해를 입는다는 가정에서의 버틸 수 있는 체력
            / (1 - stats[10] * 0.01)
            * self.coef_boss,  # 회피
            sum_NormalDMG
            * self.coef_normalDMG  # 일반데미지
            * (1 + stats[16] * 0.01)  # 운
            * (1 + stats[11] * 0.001)  # 상태이상저항
            * (1 + stats[17] * 0.01)  # 경험치
            * self.coef_normal,
        ]
        if randomSeed == 1:
            return powers

        powers = [str(int(i)) for i in powers]

        simuls_boss = []
        simuls_normal = []
        for i in range(100):  # 멀티프로세싱으로 수정 후 1000회로 변경
            simuls_boss.append(runSimul(attackDetails, buffDetails, stats, True, simInfo, naegongDiff))
            simuls_normal.append(runSimul(attackDetails, buffDetails, stats, False, simInfo, naegongDiff))

        sums_simulBossDMG = [sum([i[2] for i in j]) for j in simuls_boss]
        sums_simulNormalDMG = [sum([i[2] for i in j]) for j in simuls_normal]

        min_bossDMG = min(sums_simulBossDMG)
        max_bossDMG = max(sums_simulBossDMG)
        std_bossDMG = calculate_std(sums_simulBossDMG)
        p25_bossDMG = calculate_percentile(sums_simulBossDMG, 25)
        p50_bossDMG = calculate_percentile(sums_simulBossDMG, 50)
        p75_bossDMG = calculate_percentile(sums_simulBossDMG, 75)
        min_normalDMG = min(sums_simulNormalDMG)
        max_normalDMG = max(sums_simulNormalDMG)
        std_normalDMG = calculate_std(sums_simulNormalDMG)
        p25_normalDMG = calculate_percentile(sums_simulNormalDMG, 25)
        p50_normalDMG = calculate_percentile(sums_simulNormalDMG, 50)
        p75_normalDMG = calculate_percentile(sums_simulNormalDMG, 75)

        analysis = [
            {
                "title": "초당 보스피해량",
                "number": f"{int(sum_BossDMG / 60)}",
                "min": f"{int(min_bossDMG / 60)}",
                "max": f"{int(max_bossDMG / 60)}",
                "std": f"{std_bossDMG / 60:.1f}",
                "p25": f"{int(p25_bossDMG / 60)}",
                "p50": f"{int(p50_bossDMG / 60)}",
                "p75": f"{int(p75_bossDMG / 60)}",
            },
            {
                "title": "총 보스피해량",
                "number": f"{int(sum_BossDMG)}",
                "min": f"{int(min_bossDMG)}",
                "max": f"{int(max_bossDMG)}",
                "std": f"{std_bossDMG:.1f}",
                "p25": f"{int(p25_bossDMG)}",
                "p50": f"{int(p50_bossDMG)}",
                "p75": f"{int(p75_bossDMG)}",
            },
            {
                "title": "초당 피해량",
                "number": f"{int(sum_NormalDMG / 60)}",
                "min": f"{int(min_normalDMG / 60)}",
                "max": f"{int(max_normalDMG / 60)}",
                "std": f"{std_normalDMG / 60:.1f}",
                "p25": f"{int(p25_normalDMG / 60)}",
                "p50": f"{int(p50_normalDMG / 60)}",
                "p75": f"{int(p75_normalDMG / 60)}",
            },
            {
                "title": "총 피해량",
                "number": f"{int(sum_NormalDMG)}",
                "min": f"{int(min_normalDMG)}",
                "max": f"{int(max_normalDMG)}",
                "std": f"{std_normalDMG:.1f}",
                "p25": f"{int(p25_normalDMG)}",
                "p50": f"{int(p50_normalDMG)}",
                "p75": f"{int(p75_normalDMG)}",
            },
        ]

        return powers, analysis, boss_attacks, simuls_boss

    # 매크로 시뮬레이션 => 스킬 리스트
    def getSimulatedSKillList(self, cooltimeReduce):
        # 실제와 다른 경우가 있어서 시뮬레이션 진행할 때 옵션 추가해야함
        def use(skill, additionalTime=0):
            self.usedSkillList.append([skill, (self.elapsedTime + additionalTime)])

            self.minusSkillCount = [skill, additionalTime]
            # self.availableSkillCount[skill] -= 1

            # print(f"{(self.elapsedTime + additionalTime) * 0.001:.3f} - {skill}")

        self.initMacro()
        self.elapsedTime = 0  # 1000배
        self.simWaitTime = 0  # 다음 테스크 실행까지 대기 시간 (1000배)
        self.minusSkillCount = [
            None,
            None,
        ]  # availableSkillCount -= 1까지 남은 시간: [skill, time] (doClick을 할때 delay가 있기 때문)
        self.usedSkillList = []

        # 스킬 남은 쿨타임 : [0, 0, 0, 0, 0, 0]  # 초 1000배
        self.skillCoolTimers = [0] * self.usableSkillCount[
            self.serverID
        ]  # isUsed이면 self.unitTime(x1000)씩 증가, 쿨타임이 지나면 0으로 초기화

        # 스킬 사용 가능 횟수 : [3, 2, 2, 1, 3, 3]
        self.availableSkillCount = [
            self.skillComboCountList[self.serverID][self.jobID][self.selectedSkillList[i]]
            for i in range(self.usableSkillCount[self.serverID])
        ]

        while self.elapsedTime <= 62000:  # 65000
            self.addTaskList()

            # 스킬 사용
            if len(self.taskList) != 0 and self.simWaitTime == 0:
                skill = self.taskList[0][0]  # skill = slot
                doClick = self.taskList[0][1]  # T, F

                if self.selectedItemSlot != skill:
                    if doClick:  # press -> delay -> click => use
                        use(skill, self.delay)
                        self.selectedItemSlot = skill

                        self.simWaitTime = self.delay * 2
                    else:  # press => use
                        use(skill)
                        self.selectedItemSlot = skill

                        self.simWaitTime = self.delay
                else:
                    if doClick:  # click => use
                        use(skill)

                        self.simWaitTime = self.delay
                    else:  # press => use
                        use(skill)

                        self.simWaitTime = self.delay

                self.taskList.pop(0)

            for skill in range(self.usableSkillCount[self.serverID]):  # 0~6
                if (
                    self.availableSkillCount[skill]
                    < self.skillComboCountList[self.serverID][self.jobID][self.selectedSkillList[skill]]
                ):  # 스킬 사용해서 쿨타임 기다리는 중이면
                    self.skillCoolTimers[skill] += int(self.unitTime * 100)

                    if self.skillCoolTimers[skill] >= int(
                        self.skillCooltimeList[self.serverID][self.jobID][self.selectedSkillList[skill]]
                        * (100 - cooltimeReduce)
                    ):  # 쿨타임이 지나면
                        self.preparedSkillList[2].append(skill)  # 대기열에 추가
                        self.availableSkillCount[skill] += 1  # 사용 가능 횟수 증가

                        self.skillCoolTimers[skill] = 0  # 쿨타임 초기화
                        # print(f"{(self.elapsedTime) * 0.001:.3f} - {skill} 쿨타임")

            if self.minusSkillCount[1] == 0:
                self.availableSkillCount[self.minusSkillCount[0]] -= 1
                self.minusSkillCount = [None, None]

            if self.minusSkillCount[1] != None:
                self.minusSkillCount[1] = max(0, self.minusSkillCount[1] - int(self.unitTime * 1000))
            self.simWaitTime = max(0, self.simWaitTime - int(self.unitTime * 1000))
            self.elapsedTime += int(self.unitTime * 1000)

        self.usedSkillList = [i for i in self.usedSkillList if i[1] <= 61000]
        # 1초마다 평타도 추가시켜야함 => 데미지 계산 할 때 추가시키기
        return self.usedSkillList

    ## 매크로 메인 쓰레드
    def runMacro(self, loopNum):
        self.initMacro()

        # 스킬 쿨타임 타이머 : [time] * 6  # 사용한 시간
        self.skillCoolTimers = [None] * self.usableSkillCount[self.serverID]

        # 스킬 사용 가능 횟수 : [3, 2, 2, 1, 3, 3]
        self.availableSkillCount = [
            self.skillComboCountList[self.serverID][self.jobID][self.selectedSkillList[i]]
            for i in range(self.usableSkillCount[self.serverID])
        ]

        # 스킬 쿨타임 쓰레드
        Thread(target=self.updateSkillCooltime, args=[loopNum], daemon=True).start()
        # 매크로 클릭 쓰레드
        if self.activeMouseClickSlot:
            Thread(target=self.macroClick, args=[loopNum], daemon=True).start()
        self.startTime = time.time()

        while self.isActivated and self.loopNum == loopNum:  # 매크로 작동중일 때
            self.addTaskList()  # taskList에 사용 가능한 스킬 추가
            usedSkill = self.useSkill(loopNum)  # 스킬 사용하고 시간, 사용한 스킬 리턴. skill: slot

            # 잠수면 매크로 중지
            if self.isAFKEnabled:
                if time.time() - self.afkTime0 >= 10:
                    self.isActivated = False

            # 스킬 사용 안했으면 슬립 (useSkill에서 슬립을 안함)
            if usedSkill == None:
                time.sleep(self.unitTime * self.sleepCoefficient_unit)

            # 디버깅용
            # if usedSkill != None:
            #     print(f"{time.time() - self.startTime:.3f} - {usedSkill} 사용")
            # for i in range(6):
            #     print(
            #         f"{self.availableSkillCount[i]} / {self.skillComboCountList[self.serverID][self.jobID][
            #         self.selectedSkillList[i]
            #     ]} : {self.skillCoolTimers[i]} / {int(self.skillCooltimeList[self.serverID][self.jobID][self.selectedSkillList[i]] * (100 - self.cooltimeReduce))}"
            #     )
            # print()

    def macroClick(self, loopNum):
        while self.isActivated and self.loopNum == loopNum:
            pag.click()

            time.sleep(self.delay * 0.001)

    def updateSkillCooltime(self, loopNum):
        startTime = time.perf_counter()

        i = 0
        while self.isActivated and self.loopNum == loopNum:
            i += 1

            for skill in range(self.usableSkillCount[self.serverID]):  # 0~6
                if (
                    self.availableSkillCount[skill]
                    < self.skillComboCountList[self.serverID][self.jobID][self.selectedSkillList[skill]]
                ) and (  # 스킬 사용해서 쿨타임 기다리는 중이면
                    ((time.time() - self.skillCoolTimers[skill]) * 100)
                    >= int(
                        self.skillCooltimeList[self.serverID][self.jobID][self.selectedSkillList[skill]]
                        * (100 - self.cooltimeReduce)
                    )
                ):  # 쿨타임이 지나면
                    self.preparedSkillList[2].append(skill)  # 대기열에 추가
                    self.availableSkillCount[skill] += 1  # 사용 가능 횟수 증가

                    # print(
                    #     f"{time.time() - self.startTime:.3f} - {skill} {time.time() - self.skillCoolTimers[skill]}"
                    # )

                    self.skillCoolTimers[skill] = time.time()  # 쿨타임 초기화

            time.sleep(self.unitTime * i - (time.perf_counter() - startTime))

    def initMacro(self):
        self.selectedItemSlot = -1
        self.afkTime0 = time.time()

        self.preparedSkillList = [  # 0~5
            [
                i
                for i in range(6)
                if not self.ifUseSkill[self.selectedSkillList[i]] and self.selectedSkillList[i] != -1
            ],
            [
                i
                for i in range(6)
                if self.ifUseSkill[self.selectedSkillList[i]] and self.selectedSkillList[i] != -1
            ],
            [],  # append 대기
        ]
        self.preparedSkillCountList = [  # 0~5
            [
                self.skillComboCountList[self.serverID][self.jobID][self.selectedSkillList[i]]
                for i in range(6)
                if not self.ifUseSkill[self.selectedSkillList[i]] and self.selectedSkillList[i] != -1
            ],
            [
                self.skillComboCountList[self.serverID][self.jobID][self.selectedSkillList[i]]
                for i in range(6)
                if self.ifUseSkill[self.selectedSkillList[i]] and self.selectedSkillList[i] != -1
            ],
        ]
        self.preparedSkillComboList = [self.comboCount[self.selectedSkillList[i]] for i in range(6)]  # 0~5

        # 개별 우선순위 -> 등록 순서
        self.skillSequences = []  # 0~5 in self.selectedSkillList
        # for i in self.linkSkillList:  # 연계스킬 메인1
        #     if not i[0]:
        #         self.skillSequences.append(self.convert7to5(i[2][0][0]))
        # for j, k in enumerate(self.selectedSkillList):
        #     if k == i[2][0][0]:
        #         self.skillSequences.append(j)
        # print(self.skillSequences)
        for i in range(1, 7):
            for j, k in enumerate(self.skillPriority):  # 0~7, 0~5
                if k == i:
                    x = self.convert7to5(j)
                    if (
                        not (x in self.skillSequences)
                        # and x in self.preparedSkillList[1]
                    ):
                        self.skillSequences.append(x)
                    # print(f"i: {i}, j: {j}, k: {k}")
                    # for x, y in enumerate(self.selectedSkillList):  # x: 0~5, y: 0~7
                    #     if y == j and not (x in self.skillSequences):
                    #         self.skillSequences.append(x)
                    # print(f"j: {j}, x: {x}, y: {y}")
                    # self.skillSequences.append(self.selectedSkillList[j])
        # print(self.skillSequences)
        for i in range(6):
            if not (i in self.skillSequences) and i in self.preparedSkillList[1]:
                self.skillSequences.append(i)

        self.usingLinkSkillList = []
        self.usingLinkSkillComboList = []
        for i in self.linkSkillList:
            if i[0] == 0:
                self.usingLinkSkillList.append([])
                self.usingLinkSkillComboList.append([])
                for j in i[2]:
                    x = self.convert7to5(j[0])
                    # if not (x in self.requireLinkSkillList[-1]):
                    self.usingLinkSkillList[-1].append(x)
                    self.usingLinkSkillComboList[-1].append(j[1])

        self.linkSkillRequirementList = []
        self.linkSkillComboRequirementList = []
        for i, j in enumerate(self.usingLinkSkillList):
            self.linkSkillRequirementList.append([])
            self.linkSkillComboRequirementList.append([])
            for x, y in enumerate(j):
                if not y in self.linkSkillRequirementList[-1]:
                    self.linkSkillRequirementList[-1].append(y)
                    self.linkSkillComboRequirementList[-1].append(self.usingLinkSkillComboList[i][x])
                else:
                    for k, l in enumerate(self.linkSkillRequirementList[-1]):
                        if l == y:
                            self.linkSkillComboRequirementList[-1][k] += self.usingLinkSkillComboList[i][x]

        self.preparedLinkSkillList = list(range(len(self.usingLinkSkillList)))

        self.taskList = []
        # self.printMacroInfo(brief=False)

    def useSkill(self, loopNum):

        def press(key):
            if self.isActivated and self.loopNum == loopNum:
                kb.press(key)

        def click():
            if self.isActivated and self.loopNum == loopNum:
                pag.click()

        def use(skill):
            if (
                self.availableSkillCount[skill]
                == self.skillComboCountList[self.serverID][self.jobID][self.selectedSkillList[skill]]
            ):
                self.skillCoolTimers[skill] = time.time()  # 스킬 스택이 모두 찬 상태일 때

            self.availableSkillCount[skill] -= 1

        if len(self.taskList) != 0:
            skill = self.taskList[0][0]  # skill = slot
            doClick = self.taskList[0][1]  # T, F
            key = self.skillKeys[skill]
            key = self.key_dict[key] if key in self.key_dict else key

            if self.selectedItemSlot != skill:
                if doClick:  # press -> delay -> click => use
                    press(key)
                    time.sleep(self.delay * 0.001 * self.sleepCoefficient_normal)
                    use(skill)
                    click()
                    self.selectedItemSlot = skill
                else:  # press => use
                    use(skill)
                    press(key)
                    self.selectedItemSlot = skill
            else:
                if doClick:  # click => use
                    use(skill)
                    click()
                else:  # press => use
                    use(skill)
                    press(key)

            self.taskList.pop(0)

            # print(
            #     f"{time.time() - self.startTime - pag.PAUSE if doClick else time.time() - self.startTime:.3f} - {skill}"
            # )

            sleepTime = (
                self.delay * 0.001 * self.sleepCoefficient_normal - pag.PAUSE
                if doClick
                else self.delay * 0.001 * self.sleepCoefficient_normal
            )
            time.sleep(sleepTime)
            return skill
        else:
            return None

    def useLinkSkill(self, num, loopNum):
        def press(key):
            if self.loopNum == loopNum:
                kb.press(key)

        def click():
            if self.loopNum == loopNum:
                pag.click()

        def useSkill(slot):
            skill = taskList[0][0]  # skill = slot
            clickTF = taskList[0][1]  # T, F
            key = self.skillKeys[skill]
            key = self.key_dict[key] if key in self.key_dict else key

            if slot != skill:
                if clickTF:
                    press(key)
                    time.sleep(self.delay * 0.001 * self.sleepCoefficient_normal)
                    click()
                    slot = skill
                    # time.sleep(self.delay * 0.001)
                else:
                    press(key)
                    slot = skill
                    # time.sleep(self.delay * 0.001)
            else:
                if clickTF:
                    click()
                    # time.sleep(self.delay * 0.001)
                else:
                    press(key)
                    # time.sleep(self.delay * 0.001)

            taskList.pop(0)

            return slot

        slot = -1
        taskList = []
        for i in self.linkSkillList[num][2]:
            for _ in range(i[1]):
                taskList.append(
                    [
                        self.convert7to5(i[0]),
                        self.isSkillCasting[self.serverID][self.jobID][i[0]],
                    ]
                )
        for i in range(len(taskList)):
            slot = useSkill(slot)

    def addTaskList(self):
        # append
        lCopy = copy.deepcopy(self.preparedSkillList)
        for skill in lCopy[2]:
            if self.ifUseSkill[self.selectedSkillList[skill]]:
                if skill in lCopy[1]:
                    for i in range(len(lCopy[1])):
                        if skill == lCopy[1][i]:
                            self.preparedSkillCountList[1][i] += 1
                else:
                    self.preparedSkillList[1].append(skill)
                    self.preparedSkillCountList[1].append(1)
            else:
                if skill in lCopy[0]:
                    for i in range(len(lCopy[0])):
                        if skill == lCopy[0][i]:
                            self.preparedSkillCountList[0][i] += 1
                else:
                    self.preparedSkillList[0].append(skill)
                    self.preparedSkillCountList[0].append(1)
        del self.preparedSkillList[2][: len(lCopy[2])]

        # 준비된 연계스킬 리스트
        self.checkIsLinkReady()
        # print("준비된 연계스킬리스트:", self.preparedLinkSkillList)

        # 연계스킬 사용
        while len(self.preparedLinkSkillList) != 0:
            for j in range(len(self.usingLinkSkillList[self.preparedLinkSkillList[0]])):
                skill = self.usingLinkSkillList[self.preparedLinkSkillList[0]][j]
                count = self.usingLinkSkillComboList[self.preparedLinkSkillList[0]][j]

                for k in [0, 1]:
                    # print(
                    #     "i:",
                    #     i,
                    #     "skill:",
                    #     skill,
                    #     "self.preparedSkillList[k]:",
                    #     self.preparedSkillList[k],
                    # )
                    if skill in self.preparedSkillList[k]:
                        for idx in range(len(self.preparedSkillList[k])):
                            if skill == self.preparedSkillList[k][idx]:
                                for _ in range(count):
                                    if self.isSkillCasting[self.serverID][self.jobID][
                                        self.selectedSkillList[skill]
                                    ]:
                                        self.taskList.append([skill, True])  # skill: k, click: True
                                    else:
                                        self.taskList.append([skill, False])  # skill: k, click: False
                                    self.preparedSkillCountList[k][idx] -= 1
                                    # print(
                                    #     "count: ",
                                    #     count,
                                    #     "1준비된 스킬 개수 리스트:",
                                    #     self.preparedSkillCountList,
                                    # )
            self.checkIsLinkReady()
        self.preparedLinkSkillList = []
        self.reloadPreparedSkillList()

        # 준비된 스킬 정렬순서대로 사용
        for i in self.skillSequences:
            tempL = []
            for x in range(len(self.linkSkillRequirementList)):
                for y in self.linkSkillRequirementList[x]:
                    tempL.append(y)  # 연계스킬 사용중인 스킬 전부 모으기

            if (
                (i in self.preparedSkillList[0] or i in self.preparedSkillList[1])
                and i in tempL
                and self.ifUseSole[self.selectedSkillList[i]]
            ):
                for x in [0, 1]:
                    for j, k in enumerate(self.preparedSkillList[x]):
                        if i == k:
                            while self.preparedSkillCountList[x][j] >= 1:
                                if self.isSkillCasting[self.serverID][self.jobID][self.selectedSkillList[k]]:
                                    self.taskList.append([k, True])  # skill: k, click: True
                                else:
                                    self.taskList.append([k, False])  # skill: k, click: False
                                self.preparedSkillCountList[x][j] -= 1
                                # print(
                                #     "2준비된 스킬 개수 리스트:",
                                #     self.preparedSkillCountList,
                                # )
            if (
                i in self.preparedSkillList[1]
                and not (i in tempL)
                and self.ifUseSkill[self.selectedSkillList[i]]
            ):
                for j, k in enumerate(self.preparedSkillList[1]):
                    if i == k:
                        while self.preparedSkillCountList[1][j] >= self.preparedSkillComboList[i]:
                            for _ in range(self.preparedSkillComboList[i]):
                                if self.isSkillCasting[self.serverID][self.jobID][self.selectedSkillList[k]]:
                                    self.taskList.append([k, True])  # skill: k, click: True
                                else:
                                    self.taskList.append([k, False])  # skill: k, click: False
                                self.preparedSkillCountList[1][j] -= 1
                                # print(
                                #     "2준비된 스킬 개수 리스트:",
                                #     self.preparedSkillCountList,
                                # )
        self.reloadPreparedSkillList()

    def checkIsLinkReady(self):
        self.preparedLinkSkillList = []
        for x in range(len(self.linkSkillRequirementList)):
            ready = [False] * len(self.linkSkillRequirementList[x])

            for y in range(len(self.linkSkillRequirementList[x])):
                skill = self.linkSkillRequirementList[x][y]
                count = self.linkSkillComboRequirementList[x][y]
                for i in [0, 1]:
                    if skill in self.preparedSkillList[i]:
                        for j in range(len(self.preparedSkillList[i])):
                            if skill == self.preparedSkillList[i][j]:
                                if count <= self.preparedSkillCountList[i][j]:
                                    ready[y] = True

            if not False in ready:
                self.preparedLinkSkillList.append(x)

    def reloadPreparedSkillList(self):
        # self.printMacroInfo()
        # print("\n")

        for num in [0, 1]:
            for i in range(len(self.preparedSkillList[num]) - 1, -1, -1):
                if self.preparedSkillCountList[num][i] == 0:
                    self.preparedSkillList[num].pop(i)
                    self.preparedSkillCountList[num].pop(i)
                    # print("reload")

    def printMacroInfo(self, brief=False):
        if brief:
            print("테스크 리스트:", self.taskList)  # 사용여부 x, 사용여부 o
            print("준비된 스킬 리스트:", self.preparedSkillList)  # 사용여부 x, 사용여부 o
            print("준비된 스킬 개수 리스트:", self.preparedSkillCountList)  # 사용여부 x, 사용여부 o
            print("준비된 연계스킬리스트:", self.preparedLinkSkillList)
        else:
            print("준비된 스킬 리스트:", self.preparedSkillList)  # 사용여부 x, 사용여부 o
            print("준비된 스킬 개수 리스트:", self.preparedSkillCountList)  # 사용여부 x, 사용여부 o
            print("스킬 콤보 리스트:", self.preparedSkillComboList)  # 사용여부 o
            print("스킬 정렬 순서:", self.skillSequences)
            print("연계스킬 스킬 리스트:", self.usingLinkSkillList)
            print("연계스킬 스킬 콤보 리스트:", self.usingLinkSkillComboList)
            print("연계스킬에 필요한 스킬 리스트:", self.linkSkillRequirementList)
            print(
                "연계스킬에 필요한 스킬 콤보 리스트:",
                self.linkSkillComboRequirementList,
            )
            print("준비된 연계스킬리스트:", self.preparedLinkSkillList)

    def convert7to5(self, num):
        for x, y in enumerate(self.selectedSkillList):  # x: 0~5, y: 0~7
            if y == num:
                return x

    def keyPressEvent(self, e):  # 키가 눌러졌을 때 실행됨

        # ESC
        if e.key() == Qt.Key.Key_Escape:
            if self.isTabRemovePopupActivated:
                self.onTabRemovePopupClick(0, False)
            elif self.activeErrorPopupCount >= 1:
                self.removeNoticePopup()
            elif self.activePopup != "":
                self.disablePopup()

        # Ctrl
        elif e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if e.key() == Qt.Key.Key_W and not self.isTabRemovePopupActivated:
                self.onTabRemoveClick(self.recentPreset)

        # Enter
        elif e.key() == Qt.Key.Key_Return:
            if self.isTabRemovePopupActivated:
                self.onTabRemovePopupClick(self.recentPreset)
            elif self.activePopup == "settingDelay":
                self.onInputPopupClick("delay")
            elif self.activePopup == "settingCooltime":
                self.onInputPopupClick("cooltime")
            elif self.activePopup == "changeTabName":
                self.onInputPopupClick(("tabName", self.recentPreset))

        # # Temp
        # elif e.key() == Qt.Key.Key_L:
        #     print(self.getSimulatedSKillList())

        else:
            pass

    ## 버전 확인을 위한 함수
    def checkVersion(self):
        self.worker = VersionChecker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.start()
        self.worker.versionChecked.connect(self.onVersionChecked)
        self.delayTimer = QTimer()
        self.delayTimer.setSingleShot(True)
        self.delayTimer.timeout.connect(self.worker.checkVersion)
        self.delayTimer.start(1000)

    ## 버전이 확인 되었을 때 실행
    @pyqtSlot(str)
    def onVersionChecked(self, recentVersion):
        if recentVersion == "FailedUpdateCheck":
            self.makeNoticePopup("FailedUpdateCheck")
        elif recentVersion != version:
            self.recentVersion = recentVersion
            self.update_url = self.worker.updateUrl
            self.makeNoticePopup("RequireUpdate")
        else:
            pass

    ## 초기 변수 설정
    def defineVar(self):
        self.defaultWindowWidth = 960
        self.defaultWindowHeight = 540

        self.icon = QIcon(QPixmap(convertResourcePath("resource\\image\\icon\\icon.ico")))
        self.icon_on = QIcon(QPixmap(convertResourcePath("resource\\image\\icon\\icon_on.ico")))

        # pag.PAUSE = 0.01  # pag click delay 설정

        # 이 계수를 조정하여 time.sleep과 실제 시간 간의 괴리를 조정
        self.sleepCoefficient_normal = 0.975
        self.sleepCoefficient_unit = 0.97

        self.coef_bossDMG = 1.0
        self.coef_normalDMG = 1.3
        self.coef_boss = 0.0002
        self.coef_normal = 0.7

        self.simType = 0
        self.unitTime = 0.05  # 1tick
        self.isAFKEnabled = False  # AFK 모드 활성화 여부
        self.activeErrorPopupNumber = 0
        self.isTabRemovePopupActivated = False
        self.isActivated = False
        self.loopNum = 0
        self.defaultDelay = 150
        self.minDelay = 50
        self.maxDelay = 1000
        self.minCooltime = 0
        self.maxCooltime = 50
        self.selectedItemSlot = -1
        self.isSkillSelecting = -1
        self.settingType = -1
        self.layoutType = 0  # 0: 스킬, 1: 시뮬레이터
        self.activePopup = ""
        self.activeErrorPopup = []
        self.activeErrorPopupCount = 0
        self.skillPreviewList = []

        # 내공 차이에 의한 데미지 배수 (몹-나)
        self.naegongDiff = {
            (6, 1000): 0,
            (5, 5): 0.3,
            (4, 4): 0.5,
            (3, 3): 0.7,
            (2, 2): 0.85,
            (1, 1): 0.95,
            (0, 0): 1.0,
            (-1, -1): 1.025,
            (-2, -2): 1.05,
            (-4, -3): 1.075,
            (-6, -5): 1.1,
            (-9, -7): 1.15,
            (-13, -10): 1.2,
            (-18, -14): 1.3,
            (-25, -19): 1.4,
            (-1000, -26): 1.5,
        }

        self.statList = [
            "공격력",
            "방어력",
            "파괴력",
            "근력",
            "지력",
            "경도",
            "치명타확률",
            "치명타데미지",
            "보스데미지",
            "명중률",
            "회피율",
            "상태이상저항",
            "내공",
            "체력",
            "공격속도",
            "포션회복량",
            "운",
            "경험치획득량",
        ]
        self.statRangeList = [
            [1, None],
            [1, None],
            [0, None],
            [1, None],
            [1, None],
            [1, None],
            [0, None],
            [0, None],
            [0, None],
            [0, None],
            [0, None],
            [0, None],
            [0, None],
            [1, None],
            [0, self.maxCooltime],
            [0, None],
            [0, None],
            [0, None],
        ]
        self.potentialStatList = {
            "내공 +3": [12, 3],
            "내공 +2": [12, 2],
            "내공 +1": [12, 1],
            "경도 +3": [5, 3],
            "경도 +2": [5, 2],
            "경도 +1": [5, 1],
            "치명타확률 +3": [6, 3],
            "치명타확률 +2": [6, 2],
            "치명타확률 +1": [6, 1],
            "치명타데미지 +4": [7, 4],
            "치명타데미지 +3": [7, 3],
            "치명타데미지 +2": [7, 2],
            "보스데미지 +3": [8, 3],
            "보스데미지 +2": [8, 2],
            "보스데미지 +1": [8, 1],
            "상태이상저항 +6": [11, 6],
            "상태이상저항 +4": [11, 4],
            "상태이상저항 +2": [11, 2],
            "체력 +6": [13, 6],
            "체력 +4": [13, 4],
            "체력 +2": [13, 2],
            "공격속도 +3": [14, 3],
            "공격속도 +2": [14, 2],
            "공격속도 +1": [14, 1],
            "포션회복량 +6": [15, 6],
            "포션회복량 +4": [15, 4],
            "포션회복량 +2": [15, 2],
            "운 +6": [16, 6],
            "운 +4": [16, 4],
            "운 +2": [16, 2],
        }
        self.key_dict = {
            "f1": "F1",
            "f2": "F2",
            "f3": "F3",
            "f4": "F4",
            "f5": "F5",
            "f6": "F6",
            "f7": "F7",
            "f8": "F8",
            "f9": "F9",
            "f10": "F10",
            "f11": "F11",
            "f12": "F12",
            "a": "A",
            "b": "B",
            "c": "C",
            "d": "D",
            "e": "E",
            "f": "F",
            "g": "G",
            "h": "H",
            "i": "I",
            "j": "J",
            "k": "K",
            "l": "L",
            "m": "M",
            "n": "N",
            "o": "O",
            "p": "P",
            "q": "Q",
            "r": "R",
            "s": "S",
            "t": "T",
            "u": "U",
            "v": "V",
            "w": "W",
            "x": "X",
            "y": "Y",
            "z": "Z",
            "tab": "Tab",
            "space": "Space",
            "enter": "Enter",
            "shift": "Shift",
            "right shift": "Shift",
            "ctrl": "Ctrl",
            "right ctrl": "Ctrl",
            "alt": "Alt",
            "right alt": "Alt",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
            "print screen": "PrtSc",
            "scroll lock": "ScrLk",
            "pause": "Pause",
            "insert": "Insert",
            "home": "Home",
            "page up": "Page_Up",
            "page down": "Page_Down",
            "delete": "Delete",
            "end": "End",
        }
        self.serverList = [
            "한월 RPG",
        ]
        self.jobList = [
            ["검호", "매화", "살수", "도제", "술사", "도사", "빙궁", "귀궁"],
        ]
        self.usableSkillCount = [6]  # 장착 가능한 스킬 개수

        with open(convertResourcePath("resource\\data\\skill_data.json"), "r", encoding="utf-8") as f:

            skillData = json.load(f)
        # self.skillNameList[serverID][jobID][skill]
        self.skillNameList = skillData["Names"]

        # self.skillAttackData[serverID][jobID][skill][level:임시로 하나만][combo][attackNum]:
        # [time, [type(0: damage, 1: buff), [buff_type, buff_value, buff_duration] or damage_value]]
        self.skillAttackData = skillData["AttackData"]

        # self.skillCooltimeList[serverID][jobID][skill]
        self.skillCooltimeList = skillData["CooltimeList"]

        # self.skillComboCountList[serverID][jobID][skill]
        self.skillComboCountList = skillData["ComboCounts"]

        # self.skillComboList[serverID][jobID][skill]
        self.isSkillCasting = skillData["IsSkillCasting"]

    ## 기본 폰트 설정
    def setDefaultFont(self):
        # "나눔스퀘어라운드 Light"
        QFontDatabase.addApplicationFont(convertResourcePath("resource\\font\\NSR_L.ttf"))
        # "나눔스퀘어라운드 Regular"
        QFontDatabase.addApplicationFont(convertResourcePath("resource\\font\\NSR_R.ttf"))
        # "나눔스퀘어라운드 Bold"
        QFontDatabase.addApplicationFont(convertResourcePath("resource\\font\\NSR_B.ttf"))
        # "나눔스퀘어라운드 ExtraBold"
        QFontDatabase.addApplicationFont(convertResourcePath("resource\\font\\NSR_RB.ttf"))

        font_path = convertResourcePath("resource\\font\\NSR_B.ttf")
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        plt.rcParams["font.family"] = prop.get_name()

    ## 위젯 크기에 맞는 폰트로 변경
    def adjustFontSize(self, widget, text, maxSize, font_name="나눔스퀘어라운드 ExtraBold"):
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

    ## 위젯 크기에 맞게 텍스트 자름
    def limitText(self, text, widget, margin=40) -> str:
        font_metrics = widget.fontMetrics()
        max_width = widget.width() - margin

        for i in range(len(text), 0, -1):
            if font_metrics.boundingRect(text[:i]).width() < max_width:
                return text[:i]

        return ""

    ## 가상 키보드 생성 중 키가 사용중인지 확인
    def isKeyUsing(self, key) -> bool:
        key = key.replace("\n", "_")
        usingKey = []
        if self.activeStartKeySlot == 1:
            usingKey.append(self.inputStartKey)
        else:
            usingKey.append("F9")
        if self.settingType == 3:
            usingKey.append(self.ButtonLinkKey.text())
        for i in self.skillKeys:
            usingKey.append(i)
        for i in self.linkSkillList:
            usingKey.append(i[1])

        # print(usingKey, key)

        return True if key in usingKey else False

    ## 프로그램 초기 UI 설정
    def initUI(self):
        self.setWindowTitle("데이즈 스킬매크로 " + version)
        self.setMinimumSize(self.defaultWindowWidth, self.defaultWindowHeight)
        # self.setGeometry(0, 0, 960, 540)
        self.setStyleSheet("*:focus { outline: none; }")
        self.backPalette = self.palette()
        self.backPalette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        self.setPalette(self.backPalette)
        self.page1 = QFrame(self)
        self.page2 = QFrame(self)

        self.labelCreator = QPushButton("제작자: 프로데이즈  |  디스코드: prodays", self)
        self.labelCreator.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.labelCreator.setStyleSheet("background-color: transparent; text-align: left; border: 0px;")
        # self.labelCreator.clicked.connect(
        #     lambda: open_new("https://github.com/Pro-Days")
        # )
        self.labelCreator.setFixedSize(320, 24)
        self.labelCreator.move(2, self.height() - 25)

        # 메인 프레임 생성
        self.skillBackground = QFrame(self.page1)
        self.skillBackground.setStyleSheet(
            """QFrame { background-color: #eeeeff; border-top-left-radius :0px; border-top-right-radius : 30px; border-bottom-left-radius : 30px; border-bottom-right-radius : 30px }"""
        )
        self.skillBackground.setFixedSize(560, 450)
        self.skillBackground.move(360, 69)
        self.skillBackground.setGraphicsEffect(self.getShadow(0, 5, 20, 100))

        self.tabButtonList = []
        self.tabList = []
        self.tabRemoveList = []
        for tabNum in range(len(self.tabNames)):
            tabBackground = QLabel("", self.page1)
            if tabNum == self.recentPreset:
                tabBackground.setStyleSheet(
                    """background-color: #eeeeff; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )
            else:
                tabBackground.setStyleSheet(
                    """background-color: #dddddd; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )
            tabBackground.setFixedSize(250, 50)
            tabBackground.move(360 + 250 * tabNum, 20)
            tabBackground.setGraphicsEffect(self.getShadow(5, -2))

            tabButton = QPushButton("", self.page1)
            tabButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            tabButton.setFixedSize(240, 40)
            tabButton.setText(self.limitText(f" {self.tabNames[tabNum]}", tabButton))
            tabButton.clicked.connect(partial(lambda x: self.onTabClick(x), tabNum))
            if tabNum == self.recentPreset:
                tabButton.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #eeeeff; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #fafaff;
                    }
                """
                )
            else:
                tabButton.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #dddddd; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #eeeeee;
                    }
                """
                )
            tabButton.move(365 + 250 * tabNum, 25)

            tabRemoveButton = QPushButton("", self.page1)
            tabRemoveButton.clicked.connect(partial(lambda x: self.onTabRemoveClick(x), tabNum))
            tabRemoveButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 16))
            if tabNum == self.recentPreset:
                tabRemoveButton.setStyleSheet(
                    """
                    QPushButton {
                        background-color: transparent; border-radius: 20px;
                    }
                    QPushButton:hover {
                        background-color: #fafaff;
                    }
                """
                )
            else:
                tabRemoveButton.setStyleSheet(
                    """
                    QPushButton {
                        background-color: transparent; border-radius: 20px;
                    }
                    QPushButton:hover {
                        background-color: #eeeeee;
                    }
                """
                )
            pixmap = QPixmap(convertResourcePath("resource\\image\\x.png"))
            tabRemoveButton.setIcon(QIcon(pixmap))
            tabRemoveButton.setFixedSize(40, 40)
            tabRemoveButton.move(565 + 250 * tabNum, 25)

            self.tabButtonList.append(tabButton)
            self.tabList.append(tabBackground)
            self.tabRemoveList.append(tabRemoveButton)

        self.tabAddButton = QPushButton("", self.page1)
        self.tabAddButton.clicked.connect(self.onTabAddClick)
        self.tabAddButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 16))
        self.tabAddButton.setStyleSheet(
            """
            QPushButton {
                background-color: transparent; border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        """
        )
        pixmap = QPixmap(convertResourcePath("resource\\image\\plus.png"))
        self.tabAddButton.setIcon(QIcon(pixmap))
        self.tabAddButton.setFixedSize(40, 40)
        self.tabAddButton.move(370 + 250 * len(self.tabNames), 25)

        self.layoutType = 0

        self.skillPreviewFrame = QFrame(self.skillBackground)
        self.skillPreviewFrame.setStyleSheet(
            "QFrame { background-color: #ffffff; border-radius :5px; border: 1px solid black; }"
        )
        self.skillPreviewFrame.setFixedSize(288, 48)
        self.skillPreviewFrame.move(136, 10)
        self.skillPreviewFrame.show()
        # self.showSkillPreview()

        self.selectableSkillFrame = []
        for i in range(8):
            frame = QFrame(self.skillBackground)
            frame.setStyleSheet("QFrame { background-color: transparent; border-radius :0px; }")
            frame.setFixedSize(64, 88)
            frame.move(50 + 132 * (i % 4), 80 + 120 * (i // 4))
            frame.show()
            self.selectableSkillFrame.append(frame)
        self.selectableSkillImageButton = []
        self.selectableSkillImageName = []
        for i, j in enumerate(self.selectableSkillFrame):
            button = QPushButton(j)
            button.setStyleSheet("QPushButton { background-color: #bbbbbb; border-radius :10px; }")
            button.clicked.connect(partial(lambda x: self.onSelectableSkillClick(x), i))
            button.setFixedSize(64, 64)
            pixmap = QPixmap(self.getSkillImage(i))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(64, 64))
            button.show()
            self.selectableSkillImageButton.append(button)

            label = QLabel(self.skillNameList[self.serverID][self.jobID][i], j)
            label.setStyleSheet("QLabel { background-color: transparent; border-radius :0px; }")
            label.setFixedSize(64, 24)
            label.move(0, 64)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.show()
            self.selectableSkillImageName.append(label)

        self.selectionSkillLine = QFrame(self.skillBackground)
        self.selectionSkillLine.setStyleSheet("QFrame { background-color: #b4b4b4;}")
        self.selectionSkillLine.setFixedSize(520, 1)
        self.selectionSkillLine.move(20, 309)
        self.selectionSkillLine.show()

        self.selectedSkillFrame = []
        for i in range(6):
            frame = QFrame(self.skillBackground)
            frame.setStyleSheet("QFrame { background-color: transparent; border-radius :0px; }")
            frame.setFixedSize(64, 96)
            frame.move(38 + 84 * i, 330)
            frame.show()
            self.selectedSkillFrame.append(frame)
        self.selectedSkillImageButton = []
        self.selectedSkillKey = []
        for i, j in enumerate(self.selectedSkillFrame):
            button = QPushButton(j)
            # self.selectedSkillColors = [
            #     "#8BC28C",
            #     "#FF626C",
            #     "#96C0FF",
            #     "#FFA049",
            #     "#F18AAD",
            #     "#8E8FE0",
            # ]
            self.selectedSkillColors = [
                "#BBBBBB",
                "#BBBBBB",
                "#BBBBBB",
                "#BBBBBB",
                "#BBBBBB",
                "#BBBBBB",
            ]
            button.setStyleSheet(
                f"QPushButton {{ background-color: {self.selectedSkillColors[i]}; border-radius :10px; }}"
            )
            button.clicked.connect(partial(lambda x: self.onSelectedSkillClick(x), i))
            button.setFixedSize(64, 64)
            if self.selectedSkillList[i] != -1:
                pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[i]))
            else:
                pixmap = QPixmap(convertResourcePath("resource\\image\\emptySkill.png"))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(64, 64))
            button.show()
            self.selectedSkillImageButton.append(button)

            button = QPushButton(self.skillKeys[i], j)
            button.clicked.connect(partial(lambda x: self.onSkillKeyClick(x), i))
            button.setFixedSize(64, 24)
            button.move(0, 72)
            button.show()
            self.selectedSkillKey.append(button)

        ## 사이트바
        # 설정 레이블
        self.sidebarFrame = QFrame(self.page1)
        self.sidebarFrame.setFixedSize(300, 790)
        self.sidebarFrame.setStyleSheet("QFrame { background-color: #FFFFFF; }")
        # self.sidebarFrame.setPalette(self.backPalette)
        self.sidebarScrollArea = QScrollArea(self.page1)
        self.sidebarScrollArea.setWidget(self.sidebarFrame)
        self.sidebarScrollArea.setFixedSize(319, self.height() - 24)
        self.sidebarScrollArea.setStyleSheet(
            "QScrollArea { background-color: #FFFFFF; border: 0px solid black; border-radius: 10px; }"
        )
        self.sidebarScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        # self.sidebarScrollArea.setPalette(self.backPalette)
        self.sidebarScrollArea.show()

        ## 사이드바 옵션 아이콘
        self.sidebarOptionFrame = QFrame(self.page1)
        self.sidebarOptionFrame.setFixedSize(34, 136)
        self.sidebarOptionFrame.move(320, 20)

        self.sidebarButton0 = self.getSidebarButton(0)
        self.sidebarButton1 = self.getSidebarButton(1)
        self.sidebarButton2 = self.getSidebarButton(2)
        self.sidebarButton3 = self.getSidebarButton(3)

        self.labelSettings = QLabel("", self.sidebarFrame)
        self.labelSettings.setFont(QFont("나눔스퀘어라운드 ExtraBold", 20))
        self.labelSettings.setStyleSheet(
            "border: 0px solid black; border-radius: 10px; background-color: #CADEFC;"
        )
        self.labelSettings.setFixedSize(200, 100)
        self.labelSettings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labelSettings.move(50, 20)
        self.labelSettings.setGraphicsEffect(self.getShadow())
        self.changeSettingTo0()

        self.windowLayout = QStackedLayout()
        self.windowLayout.addWidget(self.page1)
        self.windowLayout.addWidget(self.page2)
        self.setLayout(self.windowLayout)
        self.windowLayout.setCurrentIndex(0)

        self.show()

    ## 스킬 장착 취소, 다른 곳 클릭시 실행
    def cancelSkillSelection(self):
        self.isSkillSelecting = -1
        for i in range(6):
            self.selectedSkillImageButton[i].setStyleSheet(
                f"QPushButton {{ background-color: {self.selectedSkillColors[i]}; border-radius :10px; }}"
            )
        for i in range(8):
            self.selectableSkillImageButton[i].setStyleSheet(
                "QPushButton { background-color: #bbbbbb; border-radius :10px; }"
            )

    ## 하단 스킬 아이콘 클릭 (6개)
    def onSelectedSkillClick(self, num):
        # print(self.selectedSkillList[num])
        if self.settingType == 3:
            self.cancelSkillSelection()
            self.makeNoticePopup("editingLinkSkill")
            return
        if self.isActivated:
            self.cancelSkillSelection()
            self.makeNoticePopup("MacroIsRunning")
            return
        if self.isSkillSelecting == num:
            pixmap = QPixmap(convertResourcePath("resource\\image\\emptySkill.png"))
            self.selectedSkillImageButton[num].setIcon(QIcon(pixmap))

            for i, j in enumerate(self.linkSkillList):
                for k in j[2]:
                    if k[0] == self.selectedSkillList[self.isSkillSelecting]:
                        self.linkSkillList[i][0] = 1

            if self.settingType == 2:
                self.removeSetting2()
                self.settingType = -1
                self.changeSettingTo2()

            self.skillPriority[self.selectedSkillList[num]] = None
            for i in range(1, 7):
                if not (i in self.skillPriority):
                    for j, k in enumerate(self.skillPriority):
                        if not (k == None):
                            if k > i:
                                self.skillPriority[j] -= 1
                                if self.settingType == 1:
                                    self.settingSkillSequences[j].setText(str(k - 1))
            if self.settingType == 1 and self.selectedSkillList[num] != -1:
                pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[num], "off"))
                self.settingSkillImages[self.selectedSkillList[num]].setIcon(QIcon(pixmap))
                self.settingSkillSequences[self.selectedSkillList[num]].setText("-")
                # print(self.selectedSkillList)

            self.selectedSkillList[num] = -1
            self.cancelSkillSelection()
            self.dataSave()
            return

        self.isSkillSelecting = num

        for i in range(6):
            self.selectedSkillImageButton[i].setStyleSheet(
                f"QPushButton {{ background-color: {self.selectedSkillColors[i]}; border-radius :10px; }}"
            )

        self.selectedSkillImageButton[num].setStyleSheet(
            f"QPushButton {{ background-color: {self.selectedSkillColors[num]}; border-radius :10px; border: 4px solid red; }}"
        )
        for i in range(8):
            if not (i in self.selectedSkillList):
                self.selectableSkillImageButton[i].setStyleSheet(
                    "QPushButton { background-color: #bbbbbb; border-radius :10px; border: 4px solid #00b000; }"
                )

    ## 상단 스킬 아이콘 클릭 (8개)
    def onSelectableSkillClick(self, num):
        if self.settingType == 3:
            self.cancelSkillSelection()
            return
        self.selectedSkillImageButton[self.isSkillSelecting].setStyleSheet(
            f"QPushButton {{ background-color: {self.selectedSkillColors[self.isSkillSelecting]}; border-radius :10px; }}"
        )
        for i in range(8):
            self.selectableSkillImageButton[i].setStyleSheet(
                "QPushButton { background-color: #bbbbbb; border-radius :10px; }"
            )
        if self.isSkillSelecting == -1:  # 스킬 선택중이 아닐 때
            return
        elif num in self.selectedSkillList:  # 이미 선택된 스킬을 선택했을 때
            self.isSkillSelecting = -1
            return

        if self.selectedSkillList[self.isSkillSelecting] != -1:
            if self.settingType == 1:
                pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[self.isSkillSelecting], "off"))
                self.settingSkillImages[self.selectedSkillList[self.isSkillSelecting]].setIcon(QIcon(pixmap))
                self.settingSkillSequences[self.selectedSkillList[self.isSkillSelecting]].setText("-")

            for i, j in enumerate(self.linkSkillList):
                for k in j[2]:
                    if k[0] == self.selectedSkillList[self.isSkillSelecting]:
                        self.linkSkillList[i][0] = 1

        self.selectedSkillList[self.isSkillSelecting] = num

        self.skillPriority[self.selectedSkillList[self.isSkillSelecting]] = None
        for i in range(1, 7):
            if not (i in self.skillPriority):
                for j, k in enumerate(self.skillPriority):
                    if not (k == None):
                        if k > i:
                            self.skillPriority[j] -= 1
                            if self.settingType == 1:
                                self.settingSkillSequences[j].setText(str(k - 1))

        self.selectedSkillList[self.isSkillSelecting] = num
        pixmap = QPixmap(self.getSkillImage(num))
        self.selectedSkillImageButton[self.isSkillSelecting].setIcon(QIcon(pixmap))

        if self.settingType == 1:
            pixmap = QPixmap(self.getSkillImage(num))
            self.settingSkillImages[num].setIcon(QIcon(pixmap))

        self.isSkillSelecting = -1
        self.dataSave()

    def tick(self):
        self.previewTimer.singleShot(100, self.tick)
        self.showSkillPreview()

    ## 스킬 미리보기 프레임에 스킬 아이콘 설정
    def showSkillPreview(self):
        if not self.isActivated:
            self.initMacro()
            self.addTaskList()
            # self.printMacroInfo(True)
            # print(self.taskList)

        for i in self.skillPreviewList:
            i.deleteLater()
        self.skillPreviewList = []

        fwidth = self.skillPreviewFrame.width()
        width = round(self.skillPreviewFrame.width() * 0.166667)
        height = self.skillPreviewFrame.height()

        count = min(len(self.taskList), 6)
        for i in range(count):
            skill = QPushButton("", self.skillPreviewFrame)
            # self.tabAddButton.clicked.connect(self.onTabAddClick)
            skill.setStyleSheet("background-color: transparent;")
            if not self.isActivated:
                pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[self.taskList[i][0]], "off"))
            else:
                pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[self.taskList[i][0]], 1))
            skill.setIcon(QIcon(pixmap))
            skill.setIconSize(QSize(min(width, height), min(width, height)))
            skill.setFixedSize(width, height)
            skill.move(round((fwidth - width * count) * 0.5) + width * i, 0)
            skill.show()

            self.skillPreviewList.append(skill)

    ## 사이드바 설정 종류 아이콘 버튼 생성
    def getSidebarButton(self, num):
        button = QPushButton("", self.sidebarOptionFrame)
        match num:
            case 0:
                button.clicked.connect(self.changeSettingTo0)
                pixmap = QPixmap(convertResourcePath("resource\\image\\setting.png"))
                button.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 8px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
                    }
                    QPushButton:hover {
                        background-color: #dddddd;
                    }
                """
                )
                button.move(0, 0)
            case 1:
                button.clicked.connect(self.changeSettingTo1)
                pixmap = QPixmap(convertResourcePath("resource\\image\\usageSetting.png"))
                button.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
                    }
                    QPushButton:hover {
                        background-color: #dddddd;
                    }
                """
                )
                button.move(0, 34)
            case 2:
                button.clicked.connect(self.changeSettingTo2)
                pixmap = QPixmap(convertResourcePath("resource\\image\\linkSetting.png"))
                button.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
                    }
                    QPushButton:hover {
                        background-color: #dddddd;
                    }
                """
                )
                button.move(0, 68)
            case 3:
                button.clicked.connect(lambda: self.changeLayout(1))
                # button.clicked.connect(self.changeLayout)
                pixmap = QPixmap(convertResourcePath("resource\\image\\simulationSidebar.png"))
                button.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
                    }
                    QPushButton:hover {
                        background-color: #dddddd;
                    }
                """
                )
                button.move(0, 102)

        button.setIcon(QIcon(pixmap))
        button.setIconSize(QSize(32, 32))
        button.setFixedSize(34, 34)

        return button

    ## 사이드바 타입 - 설정 제거
    def removeSetting0(self):
        self.labelServerJob.deleteLater()
        self.buttonServerList.deleteLater()
        self.buttonJobList.deleteLater()
        self.labelDelay.deleteLater()
        self.buttonDefaultDelay.deleteLater()
        self.buttonInputDelay.deleteLater()
        self.labelCooltime.deleteLater()
        self.buttonDefaultCooltime.deleteLater()
        self.buttonInputCooltime.deleteLater()
        self.labelStartKey.deleteLater()
        self.buttonDefaultStartKey.deleteLater()
        self.buttonInputStartKey.deleteLater()
        self.labelMouse.deleteLater()
        self.button1stMouseType.deleteLater()
        self.button2ndMouseType.deleteLater()
        for i in self.settingLines:
            i.deleteLater()

        self.sidebarButton0.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 8px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

    ## 사이드바 타입 - 사용설정 제거
    def removeSetting1(self):
        for i in self.skillSettingTexts:
            i.deleteLater()
        for i in range(8):
            self.settingLines[i].deleteLater()
            self.settingSkillImages[i].deleteLater()
            self.settingSkillUsages[i].deleteLater()
            self.settingSkillSingle[i].deleteLater()
            self.settingSkillComboCounts[i].deleteLater()
            self.settingSkillSequences[i].deleteLater()

        self.sidebarButton1.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

    ## 사이드바 타입 - 연계설정 제거
    def removeSetting2(self):
        self.newLinkSkill.deleteLater()
        for i in self.settingLines:
            i.deleteLater()
        for i in self.settingSkillPreview:
            i.deleteLater()
        for i in self.settingSkillBackground:
            i.deleteLater()
        for i in self.settingSkillKey:
            i.deleteLater()
        for i in self.settingSkillRemove:
            i.deleteLater()
        for i in self.settingAMDP:
            i.deleteLater()

        self.sidebarButton2.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

    ## 사이드바 타입 - 연계설정 제거
    def removeSetting3(self):
        self.linkSkillPreviewFrame.deleteLater()
        self.labelLinkType.deleteLater()
        self.ButtonLinkType0.deleteLater()
        self.ButtonLinkType1.deleteLater()
        self.labelLinkKey.deleteLater()
        self.ButtonLinkKey.deleteLater()
        self.linkSkillLineA.deleteLater()
        self.linkSkillPlus.deleteLater()
        self.linkSkillCancelButton.deleteLater()
        self.linkSkillSaveButton.deleteLater()
        for i in self.linkSkillPreviewList:
            i.deleteLater()
        for i in self.linkSkillImageList:
            i.deleteLater()
        for i in self.linkSkillCount:
            i.deleteLater()
        for i in self.linkSkillLineB:
            i.deleteLater()
        for i in self.linkSkillRemove:
            i.deleteLater()

        self.sidebarButton2.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

    ## 사이드바 타입 -> 설정으로 변경
    def changeSettingTo0(self):
        self.disablePopup()

        match self.settingType:
            case 0:
                return
            case 1:
                self.removeSetting1()
            case 2:
                self.removeSetting2()
            case 3:
                self.removeSetting3()

        self.settingType = 0

        self.sidebarButton0.setStyleSheet(
            """
            QPushButton {
                background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 8px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

        self.labelSettings.setText("설정")
        self.sidebarFrame.setFixedSize(300, 770)
        self.settingLines = []
        for i in range(4):
            line = QFrame(self.sidebarFrame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(260, 1)
            line.move(20, 260 + 130 * i)
            line.show()
            self.settingLines.append(line)

        # 서버 - 직업
        self.labelServerJob = self.getSettingName("서버 - 직업", 60, 150)
        self.labelServerJob.setToolTip(
            "투다이스 서버의 서버와 직업을 선택합니다.\n새로운 서버가 오픈될 경우 새 항목이 추가될 수 있습니다."
        )
        self.buttonServerList = self.getSettingButton(
            self.serverList[self.serverID], 40, 200, self.onServerClick
        )
        self.buttonJobList = self.getSettingButton(
            self.jobList[self.serverID][self.jobID], 160, 200, self.onJobClick
        )

        # 딜레이
        self.labelDelay = self.getSettingName("딜레이", 60, 150 + 130)
        self.labelDelay.setToolTip(
            "스킬을 사용하기 위한 키보드 입력, 마우스 클릭과 같은 동작 사이의 간격을 설정합니다.\n단위는 밀리초(millisecond, 0.001초)를 사용합니다.\n입력 가능한 딜레이의 범위는 50~1000입니다.\n딜레이를 계속해서 조절하며 1분간 매크로를 실행했을 때 놓치는 스킬이 없도록 설정해주세요."
        )
        if self.activeDelaySlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultDelay = self.getSettingCheck(
            f"기본: {self.defaultDelay}",
            40,
            200 + 130,
            self.onDefaultDelayClick,
            disable=temp[0],
        )
        self.buttonInputDelay = self.getSettingCheck(
            str(self.inputDelay),
            160,
            200 + 130,
            self.onInputDelayClick,
            disable=temp[1],
        )

        # 쿨타임 감소
        self.labelCooltime = self.getSettingName("쿨타임 감소", 60, 150 + 130 * 2)
        self.labelCooltime.setToolTip(
            "캐릭터의 쿨타임 감소 스탯입니다.\n입력 가능한 쿨타임 감소 스탯의 범위는 0~50입니다."
        )
        if self.activeCooltimeSlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultCooltime = self.getSettingCheck(
            "기본: 0", 40, 200 + 130 * 2, self.onDefaultCooltimeClick, disable=temp[0]
        )
        self.buttonInputCooltime = self.getSettingCheck(
            str(self.inputCooltime),
            160,
            200 + 130 * 2,
            self.onInputCooltimeClick,
            disable=temp[1],
        )

        # 시작키 설정
        self.labelStartKey = self.getSettingName("시작키 설정", 60, 150 + 130 * 3)
        self.labelStartKey.setToolTip(
            "매크로를 시작하기 위한 키입니다.\n쓰지 않는 키로 설정한 후, 로지텍 G 허브와 같은 프로그램으로 마우스의 버튼에 매핑하는 것을 추천합니다."
        )
        if self.activeStartKeySlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultStartKey = self.getSettingCheck(
            "기본: F9", 40, 200 + 130 * 3, self.onDefaultStartKeyClick, disable=temp[0]
        )
        self.buttonInputStartKey = self.getSettingCheck(
            str(self.inputStartKey),
            160,
            200 + 130 * 3,
            self.onInputStartKeyClick,
            disable=temp[1],
        )

        # 마우스 클릭
        self.labelMouse = self.getSettingName("마우스 클릭", 60, 150 + 130 * 4)
        self.labelMouse.setToolTip(
            "스킬 사용시: 스킬을 사용하기 위해 마우스를 클릭합니다. 평타를 사용하기 위한 클릭은 하지 않습니다.\n평타 포함: 스킬과 평타를 사용하기 위해 마우스를 클릭합니다."
        )
        if self.activeMouseClickSlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.button1stMouseType = self.getSettingCheck(
            "스킬 사용시", 40, 200 + 130 * 4, self.on1stMouseTypeClick, disable=temp[0]
        )
        self.button2ndMouseType = self.getSettingCheck(
            "평타 포함",
            160,
            200 + 130 * 4,
            self.on2ndMouseTypeClick,
            disable=temp[1],
        )

    ## 사이드바 타입 -> 사용설정으로 변경
    def changeSettingTo1(self):
        self.disablePopup()

        match self.settingType:
            case 0:
                self.removeSetting0()
            case 1:
                return
            case 2:
                self.removeSetting2()
            case 3:
                self.removeSetting3()

        self.settingType = 1

        self.sidebarButton1.setStyleSheet(
            """
            QPushButton {
                background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

        self.labelSettings.setText("스킬 사용설정")
        self.sidebarFrame.setFixedSize(300, 620)

        self.skillSettingTexts = []
        texts = ["사용\n여부", "단독\n사용", "콤보\n횟수", "우선\n순위"]
        tooltips = [
            "매크로가 작동 중일 때 자동으로 스킬을 사용할지 결정합니다.\n이동기같이 자신이 직접 사용해야 하는 스킬만 사용을 해제하시는 것을 추천드립니다.\n연계스킬에는 적용되지 않습니다.",
            "연계스킬을 대기할 때 다른 스킬들이 준비되는 것을 기다리지 않고 우선적으로 사용할 지 결정합니다.\n연계스킬 내에서 다른 스킬보다 너무 빠르게 준비되는 스킬은 사용을 해제하시는 것을 추천드립니다.\n사용여부가 활성화되지 않았다면 단독으로 사용되지 않습니다.",
            "매크로가 작동 중일 때 한 번에 스킬을 몇 번 사용할 지를 결정합니다.\n콤보가 존재하는 스킬에 사용하는 것을 추천합니다.\n연계스킬에는 적용되지 않습니다.",
            "매크로가 작동 중일 때 여러 스킬이 준비되었더라도 우선순위가 더 높은(숫자가 낮은) 스킬을 먼저 사용합니다.\n우선순위를 설정하지 않은 스킬들은 준비된 시간 순서대로 사용합니다.\n버프스킬의 우선순위를 높이는 것을 추천합니다.\n연계스킬은 우선순위가 적용되지 않습니다.",
        ]
        for i in range(4):
            label = QLabel(texts[i], self.sidebarFrame)
            label.setToolTip(tooltips[i])
            label.setStyleSheet("QLabel { border: 0px; border-radius: 0px; }")
            label.setFixedSize(50, 50)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.move(75 + 50 * i, 150)
            label.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            label.show()
            self.skillSettingTexts.append(label)

        self.settingLines = []
        self.settingSkillImages = []
        self.settingSkillUsages = []
        self.settingSkillSingle = []
        self.settingSkillComboCounts = []
        self.settingSkillSequences = []
        for i in range(8):
            line = QFrame(self.sidebarFrame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(260, 1)
            line.move(20, 200 + 51 * i)
            line.show()
            self.settingLines.append(line)

            skill = QPushButton("", self.sidebarFrame)
            if i in self.selectedSkillList:
                pixmap = QPixmap(self.getSkillImage(i))
            else:
                pixmap = QPixmap(self.getSkillImage(i, "off"))

            skill.setIcon(QIcon(pixmap))
            skill.setIconSize(QSize(50, 50))
            skill.setStyleSheet("QPushButton { background-color: transparent;}")
            skill.setFixedSize(50, 50)
            skill.move(20, 201 + 51 * i)
            skill.show()
            self.settingSkillImages.append(skill)

            button = QPushButton("", self.sidebarFrame)
            if self.ifUseSkill[i]:
                pixmap = QPixmap(convertResourcePath("resource\\image\\checkTrue.png"))
            else:
                pixmap = QPixmap(convertResourcePath("resource\\image\\checkFalse.png"))
            button.clicked.connect(partial(lambda x: self.onSkillUsagesClick(x), i))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(32, 32))
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent; border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: #dddddd;
                }
            """
            )
            button.setFixedSize(40, 40)
            button.move(80, 206 + 51 * i)
            button.show()
            self.settingSkillUsages.append(button)

            button = QPushButton("", self.sidebarFrame)
            if self.ifUseSole[i]:
                pixmap = QPixmap(convertResourcePath("resource\\image\\checkTrue.png"))
            else:
                pixmap = QPixmap(convertResourcePath("resource\\image\\checkFalse.png"))
            button.clicked.connect(partial(lambda x: self.onSkillCombosClick(x), i))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(32, 32))
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent; border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: #dddddd;
                }
            """
            )
            button.setFixedSize(40, 40)
            button.move(130, 206 + 51 * i)
            button.show()
            self.settingSkillSingle.append(button)

            button = QPushButton(
                f"{self.comboCount[i]} / {self.skillComboCountList[self.serverID][self.jobID][i]}",
                self.sidebarFrame,
            )
            button.clicked.connect(partial(lambda x: self.onSkillComboCountsClick(x), i))
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.setFixedSize(46, 32)
            button.move(177, 210 + 51 * i)
            button.show()
            self.settingSkillComboCounts.append(button)

            txt = "-" if self.skillPriority[i] == None else str(self.skillPriority[i])
            button = QPushButton(txt, self.sidebarFrame)
            button.clicked.connect(partial(lambda x: self.onSkillSequencesClick(x), i))
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.setFixedSize(46, 32)
            button.move(227, 210 + 51 * i)
            button.show()
            self.settingSkillSequences.append(button)

    ## 사이드바 타입 -> 연계설정으로 변경
    def changeSettingTo2(self):
        self.disablePopup()

        match self.settingType:
            case 0:
                self.removeSetting0()
            case 1:
                self.removeSetting1()
            case 2:
                return
            case 3:
                self.removeSetting3()

        self.settingType = 2

        self.sidebarButton2.setStyleSheet(
            """
            QPushButton {
                background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

        self.labelSettings.setText("스킬 연계설정")
        self.sidebarFrame.setFixedSize(300, 220 + 51 * len(self.linkSkillList))

        self.newLinkSkill = QPushButton("새 연계스킬 만들기", self.sidebarFrame)
        self.newLinkSkill.clicked.connect(self.makeNewLinkSkill)
        self.newLinkSkill.setFixedSize(240, 40)
        self.newLinkSkill.setFont(QFont("나눔스퀘어라운드 ExtraBold", 16))
        self.newLinkSkill.move(30, 150)
        self.newLinkSkill.show()

        self.settingLines = []
        self.settingSkillPreview = []
        self.settingSkillBackground = []
        self.settingSkillKey = []
        self.settingSkillRemove = []
        self.settingAMDP = []
        for i, j in enumerate(self.linkSkillList):
            line = QFrame(self.sidebarFrame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(264, 1)
            line.move(18, 251 + 51 * i)
            line.show()
            self.settingLines.append(line)

            am_dp = QFrame(self.sidebarFrame)  # auto, manual 표시 프레임
            if j[0]:
                am_dp.setStyleSheet(
                    "QFrame { background-color: #0000ff; border: 0px solid black; border-radius: 2px; }"
                )
            else:
                am_dp.setStyleSheet(
                    "QFrame { background-color: #ff0000; border: 0px solid black; border-radius: 2px; }"
                )
            am_dp.setFixedSize(4, 4)
            am_dp.move(280, 224 + 51 * i)
            am_dp.show()
            self.settingAMDP.append(am_dp)

            imageCount = min(len(j[2]), 12)
            if imageCount <= 3:
                for k in range(len(j[2])):
                    button = QPushButton("", self.sidebarFrame)
                    pixmap = QPixmap(self.getSkillImage(j[2][k][0], j[2][k][1]))
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(48, 48))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(50, 50)
                    button.move(18 + 50 * k, 201 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)
            elif imageCount <= 6:
                for k in range(len(j[2])):
                    button = QPushButton("", self.sidebarFrame)
                    pixmap = QPixmap(self.getSkillImage(j[2][k][0], j[2][k][1]))
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(24, 24))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(25, 25)
                    button.move(18 + 25 * k, 213 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)
            else:
                line2 = imageCount // 2
                line1 = imageCount - line2

                for k in range(line1):
                    button = QPushButton("", self.sidebarFrame)
                    pixmap = QPixmap(self.getSkillImage(j[2][k][0], j[2][k][1]))
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(24, 24))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(25, 25)
                    button.move(18 + 25 * k, 201 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)
                for k in range(line2):
                    button = QPushButton("", self.sidebarFrame)
                    pixmap = QPixmap(self.getSkillImage(j[2][k + line1][0], j[2][k + line1][1]))
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(24, 24))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(25, 25)
                    button.move(18 + 25 * k, 226 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)

            button = QPushButton(j[1], self.sidebarFrame)
            button.setStyleSheet("QPushButton { background-color: transparent; border: 0px; }")
            button.setFixedSize(50, 50)
            button.move(182, 201 + 51 * i)
            button.show()
            self.adjustFontSize(button, j[1], 20)
            self.settingSkillKey.append(button)

            button = QPushButton("", self.sidebarFrame)
            button.clicked.connect(partial(lambda x: self.editLinkSkill(x), i))
            button.setStyleSheet(
                """QPushButton { background-color: transparent; border: 0px; }
                QPushButton:hover { background-color: rgba(0, 0, 0, 32); border: 0px solid black; border-radius: 8px; }"""
            )
            button.setFixedSize(264, 50)
            button.move(18, 201 + 51 * i)
            button.show()
            self.settingSkillBackground.append(button)

            button = QPushButton("", self.sidebarFrame)
            button.clicked.connect(partial(lambda x: self.removeLinkSkill(x), i))
            pixmap = QPixmap(convertResourcePath("resource\\image\\x.png"))
            button.setIcon(QIcon(pixmap))
            button.setStyleSheet(
                """QPushButton { background-color: transparent; border: 0px; }
                QPushButton:hover { background-color: #dddddd; border: 0px solid black; border-radius: 18px; }"""
            )
            button.setIconSize(QSize(32, 32))
            button.setFixedSize(36, 36)
            button.move(239, 208 + 51 * i)
            button.show()
            self.settingSkillRemove.append(button)

    ## 사이드바 타입 -> 연계설정으로 변경
    def changeSettingTo3(self, data):
        self.disablePopup()

        match self.settingType:
            case 0:
                self.removeSetting0()
            case 1:
                self.removeSetting1()
            case 2:
                self.removeSetting2()
            case 3:
                return

        self.settingType = 3
        self.sidebarButton2.setStyleSheet(
            """
            QPushButton {
                background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

        self.sidebarFrame.setFixedSize(300, 390 + 51 * len(data[2]))

        self.linkSkillPreviewFrame = QFrame(self.sidebarFrame)
        self.linkSkillPreviewFrame.setStyleSheet(
            "QFrame { background-color: #ffffff; border-radius :5px; border: 1px solid black; }"
        )
        self.linkSkillPreviewFrame.setFixedSize(288, 48)
        self.linkSkillPreviewFrame.move(6, 140)
        self.linkSkillPreviewFrame.show()

        self.linkSkillPreviewList = []
        self.makeLinkSkillPreview(data)

        self.labelLinkType = QLabel("연계 유형", self.sidebarFrame)
        self.labelLinkType.setToolTip(
            "자동: 매크로가 실행 중일 때 자동으로 연계 스킬을 사용합니다. 자동 연계스킬에 사용되는 스킬은 다른 자동 연계스킬에 사용될 수 없습니다.\n연계스킬은 매크로 작동 여부와 관계 없이 단축키를 입력해서 작동시킬 수 있습니다."
        )
        self.labelLinkType.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.labelLinkType.setFixedSize(80, 30)
        self.labelLinkType.move(40, 200)
        self.labelLinkType.show()

        self.ButtonLinkType0 = QPushButton("자동", self.sidebarFrame)
        self.ButtonLinkType0.clicked.connect(lambda: self.setLinkSkillToAuto(data))
        if data[0]:
            self.ButtonLinkType0.setStyleSheet("color: #999999;")
        else:
            self.ButtonLinkType0.setStyleSheet("color: #000000;")
        self.ButtonLinkType0.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.ButtonLinkType0.setFixedSize(50, 30)
        self.ButtonLinkType0.move(155, 200)
        self.ButtonLinkType0.show()

        self.ButtonLinkType1 = QPushButton("수동", self.sidebarFrame)
        self.ButtonLinkType1.clicked.connect(lambda: self.setLinkSkillToManual(data))
        if data[0]:
            self.ButtonLinkType1.setStyleSheet("color: #000000;")
        else:
            self.ButtonLinkType1.setStyleSheet("color: #999999;")
        self.ButtonLinkType1.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.ButtonLinkType1.setFixedSize(50, 30)
        self.ButtonLinkType1.move(210, 200)
        self.ButtonLinkType1.show()

        self.labelLinkKey = QLabel("단축키", self.sidebarFrame)
        self.labelLinkKey.setToolTip("매크로가 실행 중이지 않을 때 해당 연계스킬을 작동시킬 단축키입니다.")
        self.labelLinkKey.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.labelLinkKey.setFixedSize(80, 30)
        self.labelLinkKey.move(40, 235)
        self.labelLinkKey.show()

        self.ButtonLinkKey = QPushButton(data[1], self.sidebarFrame)
        self.ButtonLinkKey.clicked.connect(lambda: self.setLinkSkillKey(data))
        self.ButtonLinkKey.setFixedSize(50, 30)
        self.adjustFontSize(self.ButtonLinkKey, data[1], 30)
        self.ButtonLinkKey.move(210, 235)
        self.ButtonLinkKey.show()

        self.linkSkillLineA = QFrame(self.sidebarFrame)
        self.linkSkillLineA.setStyleSheet("QFrame { background-color: #b4b4b4;}")
        self.linkSkillLineA.setFixedSize(280, 1)
        self.linkSkillLineA.move(10, 274)
        self.linkSkillLineA.show()

        self.linkSkillImageList = []
        self.linkSkillCount = []
        self.linkSkillLineB = []
        self.linkSkillRemove = []
        for i, j in enumerate(data[2]):
            skill = QPushButton("", self.sidebarFrame)
            skill.clicked.connect(partial(lambda x: self.editLinkSkillType(x), (data, i)))
            # skill.setStyleSheet("background-color: transparent;")
            pixmap = QPixmap(self.getSkillImage(j[0], j[1]))
            skill.setIcon(QIcon(pixmap))
            skill.setIconSize(QSize(50, 50))
            skill.setFixedSize(50, 50)
            skill.move(40, 281 + 51 * i)
            skill.setToolTip(
                "연계스킬을 구성하는 스킬의 목록과 사용 횟수를 설정할 수 있습니다.\n하나의 스킬이 너무 많이 사용되면 연계가 정상적으로 작동하지 않을 수 있습니다."
            )
            skill.show()
            self.linkSkillImageList.append(skill)

            button = QPushButton(
                f"{j[1]} / {self.skillComboCountList[self.serverID][self.jobID][j[0]]}",
                self.sidebarFrame,
            )
            button.clicked.connect(partial(lambda x: self.editLinkSkillCount(x), (data, i)))
            button.setFixedSize(50, 30)
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.move(210, 290 + 51 * i)
            button.show()
            self.linkSkillCount.append(button)

            remove = QPushButton("", self.sidebarFrame)
            remove.clicked.connect(partial(lambda x: self.removeOneLinkSkill(x), (data, i)))
            remove.setStyleSheet(
                """QPushButton {
                    background-color: transparent; border-radius: 16px;
                }
                QPushButton:hover {
                    background-color: #eeeeee;
                }"""
            )
            pixmap = QPixmap(convertResourcePath("resource\\image\\xAlpha.png"))
            remove.setIcon(QIcon(pixmap))
            remove.setIconSize(QSize(16, 16))
            remove.setFixedSize(32, 32)
            remove.move(266, 289 + 51 * i)
            remove.show()
            self.linkSkillRemove.append(remove)

            line = QFrame(self.sidebarFrame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(220, 1)
            line.move(40, 331 + 51 * i)
            line.show()
            self.linkSkillLineB.append(line)

        self.linkSkillPlus = QPushButton("", self.sidebarFrame)
        self.linkSkillPlus.clicked.connect(lambda: self.addLinkSkill(data))
        self.linkSkillPlus.setStyleSheet(
            """QPushButton {
                    background-color: transparent; border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }"""
        )
        pixmap = QPixmap(convertResourcePath("resource\\image\\plus.png"))
        self.linkSkillPlus.setIcon(QIcon(pixmap))
        self.linkSkillPlus.setIconSize(QSize(24, 24))
        self.linkSkillPlus.setFixedSize(36, 36)
        self.linkSkillPlus.move(132, 289 + 51 * len(data[2]))
        self.linkSkillPlus.show()

        self.linkSkillCancelButton = QPushButton("취소", self.sidebarFrame)
        self.linkSkillCancelButton.clicked.connect(self.cancelEditingLinkSkill)
        self.linkSkillCancelButton.setFixedSize(120, 32)
        self.linkSkillCancelButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.linkSkillCancelButton.move(15, 350 + 51 * len(data[2]))
        self.linkSkillCancelButton.show()

        self.linkSkillSaveButton = QPushButton("저장", self.sidebarFrame)
        self.linkSkillSaveButton.clicked.connect(lambda: self.saveEditingLinkSkill(data))
        self.linkSkillSaveButton.setFixedSize(120, 32)
        self.linkSkillSaveButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.linkSkillSaveButton.move(165, 350 + 51 * len(data[2]))
        self.linkSkillSaveButton.show()

    ## 사이드바 타입3 새로고침
    def reloadSetting3(self, data):
        self.removeSetting3()
        self.settingType = -1
        self.changeSettingTo3(data)

    ## 링크스킬 종류 변경
    def editLinkSkillType(self, var):
        data, num = var

        if self.activePopup == "editLinkSkillType":
            self.disablePopup()
            return
        self.activatePopup("editLinkSkillType")

        self.settingPopupFrame = QFrame(self.sidebarFrame)
        self.settingPopupFrame.setStyleSheet("QFrame { background-color: white; border-radius: 10px; }")
        self.settingPopupFrame.setFixedSize(185, 95)
        self.settingPopupFrame.move(100, 285 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
        self.settingPopupFrame.show()

        for i in range(8):
            button = QPushButton("", self.settingPopupFrame)
            pixmap = QPixmap(
                self.getSkillImage(i) if i in self.selectedSkillList else self.getSkillImage(i, "off")
            )
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(40, 40))
            button.clicked.connect(partial(lambda x: self.oneLinkSkillTypePopupClick(x), (data, num, i)))
            button.setFixedSize(40, 40)
            # button.setStyleSheet("background-color: transparent;")
            button.move(45 * (i % 4) + 5, 5 + (i // 4) * 45)

            button.show()

    ## 링크스킬 사용 횟수 팝업창 클릭시 실행
    def oneLinkSkillTypePopupClick(self, var):
        self.disablePopup()
        data, num, i = var

        if data[2][num][0] == i:
            return
        data[2][num][0] = i
        data[2][num][1] = 1
        data[0] = 1
        self.reloadSetting3(data)

    ## 링크스킬 목록에서 하나 삭제
    def removeOneLinkSkill(self, var):
        self.disablePopup()
        data, num = var

        if len(data[2]) == 1:
            return
        del data[2][num]
        data[0] = 1
        self.reloadSetting3(data)

    ## 링크스킬 저장
    def saveEditingLinkSkill(self, data):
        self.disablePopup()

        if data[3] == -1:
            self.linkSkillList.append(data[:3])
        else:
            self.linkSkillList[data[3]] = data[:3]

        self.dataSave()
        self.removeSetting3()
        self.settingType = -1
        self.changeSettingTo2()

    ## 링크스킬 취소
    def cancelEditingLinkSkill(self):
        self.disablePopup()

        self.removeSetting3()
        self.settingType = -1
        self.changeSettingTo2()

    ## 링크스킬 추가
    def addLinkSkill(self, data):
        def checkRemain():
            skillID = 0
            maxSkill = self.skillComboCountList[self.serverID][self.jobID][skillID]
            for i in data[2]:
                skill = i[0]
                count = i[1]
                if skill == skillID:
                    maxSkill -= count
            if maxSkill > 0:
                return 0
            else:
                return -1

        self.disablePopup()

        remainSkill = checkRemain()
        if remainSkill == -1:
            self.makeNoticePopup("exceedMaxLinkSkill")
        data[2].append([0, 1])
        data[0] = 1
        self.reloadSetting3(data)

    ## 링크스킬 사용 횟수 설정
    def editLinkSkillCount(self, var):
        data, num = var

        if self.activePopup == "editLinkSkillCount":
            self.disablePopup()
            return
        self.activatePopup("editLinkSkillCount")

        count = self.skillComboCountList[self.serverID][self.jobID][data[2][num][0]]

        self.settingPopupFrame = QFrame(self.sidebarFrame)
        self.settingPopupFrame.setStyleSheet("QFrame { background-color: white; border-radius: 10px; }")
        self.settingPopupFrame.setFixedSize(5 + 35 * count, 40)
        self.settingPopupFrame.move(200 - 35 * count, 285 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
        self.settingPopupFrame.show()

        for i in range(1, count + 1):
            button = QPushButton(str(i), self.settingPopupFrame)
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.clicked.connect(partial(lambda x: self.onLinkSkillCountPopupClick(x), (data, num, i)))
            button.setFixedSize(30, 30)
            button.move(35 * i - 30, 5)

            button.show()

    ## 링크스킬 사용 횟수 팝업창 클릭시 실행
    def onLinkSkillCountPopupClick(self, var):
        def checkRemain():
            skillID = data[2][num][0]
            maxSkill = self.skillComboCountList[self.serverID][self.jobID][skillID]
            for i in data[2]:
                skill = i[0]
                count = i[1]
                if skill == skillID:
                    maxSkill -= count
            if maxSkill >= 0:
                return 0
            else:
                return -1

        self.disablePopup()
        data, num, i = var

        data[2][num][1] = i
        if checkRemain() == -1:
            self.makeNoticePopup("exceedMaxLinkSkill")
        data[0] = 1
        self.reloadSetting3(data)

    ## 링크스킬 키 설정
    def setLinkSkillKey(self, data):
        self.activatePopup("settingLinkSkillKey")
        self.makeKeyboardPopup(("LinkSkill", data))

    ## 링크스킬 자동으로 설정
    def setLinkSkillToAuto(self, data):
        self.disablePopup()
        if data[0] == 0:
            return

        for i in data[2]:
            if not (i[0] in self.selectedSkillList):
                self.makeNoticePopup("skillNotSelected")
                return

        # 사용여부는 연계스킬에 적용되지 않음
        # for i in data[2]:
        #     if not self.useSkill[i[0]]:
        #         self.makeNoticePopup("skillNotUsing")
        #         return
        if len(self.linkSkillList) != 0:
            prevData = copy.deepcopy(self.linkSkillList[data[3]])
            self.linkSkillList[data[3]] = data[:3]
            autoSkillList = []
            for i in self.linkSkillList:
                if i[0] == 0:
                    for j in range(len(i[2])):
                        autoSkillList.append(i[2][j][0])
            self.linkSkillList[data[3]] = prevData

            for i in range(len(data[2])):
                if data[2][i][0] in autoSkillList:
                    self.makeNoticePopup("autoAlreadyExist")
                    return

        data[0] = 0
        self.reloadSetting3(data)

    ## 링크스킬 수동으로 설정
    def setLinkSkillToManual(self, data):
        self.disablePopup()
        if data[0] == 1:
            return

        data[0] = 1
        self.reloadSetting3(data)

    ## 링크스킬 미리보기 생성
    def makeLinkSkillPreview(self, data):
        for i in self.linkSkillPreviewList:
            i.deleteLater()

        count = len(data[2])
        if count <= 6:
            x1 = round((288 - 48 * count) * 0.5)
            for i, j in enumerate(data[2]):
                skill = QPushButton("", self.linkSkillPreviewFrame)
                skill.setStyleSheet("background-color: transparent;")
                pixmap = QPixmap(self.getSkillImage(j[0], j[1]))
                skill.setIcon(QIcon(pixmap))
                skill.setIconSize(QSize(48, 48))
                skill.setFixedSize(48, 48)
                skill.move(x1 + 48 * i, 0)
                skill.show()

                self.linkSkillPreviewList.append(skill)
        else:
            size = round(288 / count)
            for i, j in enumerate(data[2]):
                skill = QPushButton("", self.linkSkillPreviewFrame)
                skill.setStyleSheet("background-color: transparent;")
                pixmap = QPixmap(self.getSkillImage(j[0], j[1]))
                skill.setIcon(QIcon(pixmap))
                skill.setIconSize(QSize(size, size))
                skill.setFixedSize(size, size)
                skill.move(size * i, round((48 - size) * 0.5))
                skill.show()

                self.linkSkillPreviewList.append(skill)

    ## 연계스킬 제거
    def removeLinkSkill(self, num):
        self.disablePopup()
        del self.linkSkillList[num]
        self.removeSetting2()
        self.settingType = -1
        self.changeSettingTo2()
        self.dataSave()

    ## 연계스킬 설정
    def editLinkSkill(self, num):
        self.disablePopup()
        self.cancelSkillSelection()

        data = copy.deepcopy(self.linkSkillList[num])
        data.append(num)
        self.removeSetting2()
        self.settingType = -1
        self.changeSettingTo3(data)

    ## 새 연계스킬 생성
    def makeNewLinkSkill(self):
        def findKey():
            for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if not self.isKeyUsing(char):
                    return char
            return None

        self.disablePopup()
        self.cancelSkillSelection()

        data = [1, findKey(), [[0, 1]], -1]
        self.removeSetting2()
        self.settingType = -1
        self.changeSettingTo3(data)

    ## 스킬 사용설정 -> 사용 여부 클릭
    def onSkillUsagesClick(self, num):
        self.disablePopup()
        if self.ifUseSkill[num]:
            pixmap = QPixmap(convertResourcePath("resource\\image\\checkFalse.png"))
            self.settingSkillUsages[num].setIcon(QIcon(pixmap))
            self.ifUseSkill[num] = False

            # for i, j in enumerate(self.linkSkillList):
            #     for k in j[2]:
            #         if k[0] == num:
            #             self.linkSkillList[i][0] = 1
        else:
            pixmap = QPixmap(convertResourcePath("resource\\image\\checkTrue.png"))
            self.settingSkillUsages[num].setIcon(QIcon(pixmap))
            self.ifUseSkill[num] = True
        self.dataSave()

    ## 스킬 사용설정 -> 콤보 여부 클릭
    def onSkillCombosClick(self, num):
        self.disablePopup()
        if self.ifUseSole[num]:
            pixmap = QPixmap(convertResourcePath("resource\\image\\checkFalse.png"))
            self.settingSkillSingle[num].setIcon(QIcon(pixmap))
            self.ifUseSole[num] = False
        else:
            pixmap = QPixmap(convertResourcePath("resource\\image\\checkTrue.png"))
            self.settingSkillSingle[num].setIcon(QIcon(pixmap))
            self.ifUseSole[num] = True
        self.dataSave()

    ## 스킬 사용설정 -> 콤보 횟수 클릭
    def onSkillComboCountsClick(self, num):
        combo = self.skillComboCountList[self.serverID][self.jobID][num]
        if self.activePopup == "SkillComboCounts":
            self.disablePopup()
            return
        self.disablePopup()
        self.activatePopup("SkillComboCounts")

        self.settingPopupFrame = QFrame(self.sidebarFrame)
        self.settingPopupFrame.setStyleSheet("QFrame { background-color: white; border-radius: 5px; }")
        width = 4 + 36 * combo
        self.settingPopupFrame.setFixedSize(width, 40)
        self.settingPopupFrame.move(170 - width, 206 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 0, 30, 150))
        self.settingPopupFrame.show()

        for i in range(1, combo + 1):
            button = QPushButton(str(i), self.settingPopupFrame)
            button.clicked.connect(partial(lambda x: self.onSkillComboCountsPopupClick(x), (num, i)))
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.setFixedSize(32, 32)
            button.move(36 * i - 32, 4)
            button.show()

    ## 콤보 횟수 팝업 버튼 클릭
    def onSkillComboCountsPopupClick(self, var):
        num, count = var

        self.comboCount[num] = count
        self.settingSkillComboCounts[num].setText(
            f"{count} / {self.skillComboCountList[self.serverID][self.jobID][num]}"
        )

        self.dataSave()
        self.disablePopup()

    ## 스킬 사용설정 -> 사용 순서 클릭
    def onSkillSequencesClick(self, num):
        self.disablePopup()

        def returnMin():
            for i in range(1, 7):
                if not (i in self.skillPriority):
                    return i

        if not (num in self.selectedSkillList):
            return

        if self.skillPriority[num] == None:
            minValue = returnMin()
            self.skillPriority[num] = minValue
            self.settingSkillSequences[num].setText(str(minValue))
        else:
            self.skillPriority[num] = None
            self.settingSkillSequences[num].setText("-")

            for i in range(1, 7):
                if not (i in self.skillPriority):
                    for j, k in enumerate(self.skillPriority):
                        if not (k == None):
                            if k > i:
                                self.skillPriority[j] -= 1
                                self.settingSkillSequences[j].setText(str(k - 1))

        self.dataSave()

    ## 스킬 이미지 디렉토리 리턴
    def getSkillImage(self, num, count=-1):
        # return convertResourcePath("resource\\emptySkill.png")
        if count == -1:
            return convertResourcePath(
                f"resource\\image\\skill\\{self.serverID}\\{self.jobID}\\{num}\\{self.skillComboCountList[self.serverID][self.jobID][num]}.png"
            )
        else:
            return convertResourcePath(
                f"resource\\image\\skill\\{self.serverID}\\{self.jobID}\\{num}\\{count}.png"
            )

    ## 탭 변경
    def changeTab(self, num):
        self.dataLoad(num)

        if self.settingType != 0:
            self.changeSettingTo0()

        for tabNum in range(len(self.tabNames)):
            if tabNum == self.recentPreset:
                self.tabList[tabNum].setStyleSheet(
                    """background-color: #eeeeff; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )
            else:
                self.tabList[tabNum].setStyleSheet(
                    """background-color: #dddddd; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )

            if tabNum == self.recentPreset:
                self.tabButtonList[tabNum].setStyleSheet(
                    """
                    QPushButton {
                        background-color: #eeeeff; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #fafaff;
                    }
                """
                )
            else:
                self.tabButtonList[tabNum].setStyleSheet(
                    """
                    QPushButton {
                        background-color: #dddddd; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #eeeeee;
                    }
                """
                )
            if tabNum == self.recentPreset:
                self.tabRemoveList[tabNum].setStyleSheet(
                    """
                    QPushButton {
                        background-color: transparent; border-radius: 20px;
                    }
                    QPushButton:hover {
                        background-color: #fafaff;
                    }
                """
                )
            else:
                self.tabRemoveList[tabNum].setStyleSheet(
                    """
                    QPushButton {
                        background-color: transparent; border-radius: 20px;
                    }
                    QPushButton:hover {
                        background-color: #eeeeee;
                    }
                """
                )

        self.cancelSkillSelection()
        for i in range(8):
            pixmap = QPixmap(self.getSkillImage(i))
            self.selectableSkillImageButton[i].setIcon(QIcon(pixmap))
            self.selectableSkillImageName[i].setText(self.skillNameList[self.serverID][self.jobID][i])
        for i in range(6):
            if self.selectedSkillList[i] != -1:
                pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[i]))
            else:
                pixmap = QPixmap(convertResourcePath("resource\\image\\emptySkill.png"))
            self.selectedSkillImageButton[i].setIcon(QIcon(pixmap))

        self.buttonServerList.setText(self.serverList[self.serverID])
        self.buttonJobList.setText(self.jobList[self.serverID][self.jobID])

        self.buttonInputDelay.setText(str(self.inputDelay))
        rgb = 153 if self.activeDelaySlot == 1 else 0
        self.buttonDefaultDelay.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        rgb = 153 if self.activeDelaySlot == 0 else 0
        self.buttonInputDelay.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")

        self.buttonInputCooltime.setText(str(self.inputCooltime))
        rgb = 153 if self.activeCooltimeSlot == 1 else 0
        self.buttonDefaultCooltime.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        rgb = 153 if self.activeCooltimeSlot == 0 else 0
        self.buttonInputCooltime.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")

        self.buttonInputStartKey.setText(str(self.inputStartKey))
        rgb = 153 if self.activeStartKeySlot == 1 else 0
        self.buttonDefaultStartKey.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        rgb = 153 if self.activeStartKeySlot == 0 else 0
        self.buttonInputStartKey.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")

        rgb = 153 if self.activeMouseClickSlot == 1 else 0
        self.button1stMouseType.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        rgb = 153 if self.activeMouseClickSlot == 0 else 0
        self.button2ndMouseType.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")

        self.update()
        self.updatePosition()
        self.dataSave()

    ## 사이드바에 사용되는 버튼 리턴
    def getSettingButton(self, text, x, y, cmd) -> QPushButton:
        button = QPushButton(text, self.sidebarFrame)
        button.clicked.connect(cmd)
        button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        button.setFixedSize(100, 30)
        button.move(x, y)
        button.show()
        return button

    ## 사이드바에 사용되는 체크버튼 리턴
    def getSettingCheck(self, text, x, y, cmd, disable=False) -> QPushButton:
        button = QPushButton(text, self.sidebarFrame)
        button.clicked.connect(cmd)
        button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        rgb = 153 if disable else 0
        button.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        button.setFixedSize(100, 30)
        button.move(x, y)
        button.show()
        return button

    ## 사이드바에 사용되는 라벨 리턴
    def getSettingName(self, text, x, y) -> QLabel:
        label = QLabel(text, self.sidebarFrame)
        label.setFont(QFont("나눔스퀘어라운드 ExtraBold", 16))
        label.setStyleSheet("QLabel { border: 0px solid black; border-radius: 10px; }")
        label.setFixedSize(180, 40)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.move(x, y)
        label.show()
        return label

    ## 그림자 리턴
    def getShadow(self, first=5, second=5, radius=10, transparent=100) -> QGraphicsDropShadowEffect:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(radius)
        shadow.setColor(QColor(0, 0, 0, transparent))
        shadow.setOffset(first, second)
        return shadow

    ## 알림 창 생성
    def makeNoticePopup(self, e):
        """
        MacroIsRunning: 매크로 작동중
        editingLinkSkill: 연계스킬 수정중
        skillNotSelected: 연계스킬에 장착중이지 않은 스킬이 포함되어있음
        autoAlreadyExist: 이미 자동으로 사용중인 스킬이 포함되어있음
        exceedMaxLinkSkill: 연계스킬이 너무 많이 사용되어 연계가 정상적으로 작동하지 않을 수 있음
        delayInputError: 딜레이 입력 오류
        cooltimeInputError: 쿨타임 입력 오류
        StartKeyChangeError: 시작키 변경 오류
        RequireUpdate: 업데이트 필요
        FailedUpdateCheck: 업데이트 확인 실패
        SimInputError: 시뮬레이션 정보 입력 오류
        SimCharLoadError: 캐릭터 데이터 불러오기 실패
        SimCardError: 카드 생성 오류
        SimCardPowerError: 카드 전투력 선택 안함
        SimCardNotUpdated: 카드 정보 업데이트 필요
        """
        noticePopup = QFrame(self)

        if self.isTabRemovePopupActivated:
            self.tabRemoveBackground.raise_()

        frameHeight = 78
        match e:
            case "MacroIsRunning":
                text = "매크로가 작동중이기 때문에 수정할 수 없습니다."
                icon = "error"
            case "editingLinkSkill":
                text = "연계스킬을 수정중이기 때문에 장착스킬을 변경할 수 없습니다."
                icon = "error"
            case "skillNotSelected":
                text = "해당 연계스킬에 장착중이지 않은 스킬이 포함되어있습니다."
                icon = "error"
            case "autoAlreadyExist":
                text = "해당 연계스킬에 이미 자동으로 사용중인 스킬이 포함되어있습니다."
                icon = "error"
            case "exceedMaxLinkSkill":
                text = "해당 스킬이 너무 많이 사용되어 연계가 정상적으로 작동하지 않을 수 있습니다."
                icon = "warning"
            case "delayInputError":
                text = f"딜레이는 {self.minDelay}~{self.maxDelay}까지의 수를 입력해야 합니다."
                icon = "error"
            case "cooltimeInputError":
                text = f"쿨타임은 {self.minCooltime}~{self.maxCooltime}까지의 수를 입력해야 합니다."
                icon = "error"
            case "StartKeyChangeError":
                text = "해당 키는 이미 사용중입니다."
                icon = "error"
            case "RequireUpdate":
                text = (
                    f"프로그램이 최신버전이 아닙니다.\n현재 버전: {version}, 최신버전: {self.recentVersion}"
                )
                icon = "warning"

                button = QPushButton("다운로드 링크", noticePopup)
                button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
                button.setStyleSheet(
                    """
                                QPushButton {
                                    background-color: #86A7FC; border-radius: 4px;
                                }
                                QPushButton:hover {
                                    background-color: #6498f0;
                                }
                            """
                )
                button.setFixedSize(150, 32)
                button.move(48, 86)
                button.clicked.connect(lambda: open_new(self.update_url))
                button.show()

                frameHeight = 134
            case "FailedUpdateCheck":
                text = f"프로그램 업데이트 확인에 실패하였습니다."
                icon = "warning"
            case "SimInputError":
                text = f"시뮬레이션 정보가 올바르게 입력되지 않았습니다."
                icon = "error"
            case "SimCharLoadError":
                text = f"캐릭터를 불러올 수 없습니다. 닉네임을 확인해주세요."
                icon = "error"
            case "SimCardError":
                text = f"카드를 생성할 수 없습니다. 닉네임과 캐릭터를 확인해주세요."
                icon = "error"
            case "SimCardPowerError":
                text = f"표시할 전투력 종류를 선택해주세요."
                icon = "error"
            case "SimCardNotUpdated":
                text = f"캐릭터 정보를 입력하고 '입력완료' 버튼을 눌러주세요."
                icon = "error"

        noticePopup.setStyleSheet("background-color: white; border-radius: 10px;")
        noticePopup.setFixedSize(400, frameHeight)
        noticePopup.move(
            self.width() - 420,
            self.height() - frameHeight - 15 - self.activeErrorPopupCount * 10,
        )
        noticePopup.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
        noticePopup.show()

        noticePopupIcon = QPushButton(noticePopup)
        noticePopupIcon.setStyleSheet("background-color: transparent;")
        noticePopupIcon.setFixedSize(24, 24)
        noticePopupIcon.move(13, 15)
        pixmap = QPixmap(convertResourcePath(f"resource\\image\\{icon}.png"))
        noticePopupIcon.setIcon(QIcon(pixmap))
        noticePopupIcon.setIconSize(QSize(24, 24))
        noticePopupIcon.show()

        noticePopupLabel = QLabel(text, noticePopup)
        noticePopupLabel.setWordWrap(True)
        noticePopupLabel.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        noticePopupLabel.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        noticePopupLabel.setStyleSheet("background-color: white; border-radius: 10px;")
        noticePopupLabel.setFixedSize(304, frameHeight - 24)
        noticePopupLabel.move(48, 12)
        noticePopupLabel.show()
        if e == "RequireUpdate":
            button.raise_()

        noticePopupRemove = QPushButton(noticePopup)
        noticePopupRemove.setStyleSheet(
            """
                        QPushButton {
                            background-color: white; border-radius: 16px;
                        }
                        QPushButton:hover {
                            background-color: #dddddd;
                        }
                    """
        )
        noticePopupRemove.setFixedSize(32, 32)
        noticePopupRemove.move(355, 12)
        noticePopupRemove.clicked.connect(
            partial(lambda x: self.removeNoticePopup(x), self.activeErrorPopupNumber)
        )
        pixmap = QPixmap(convertResourcePath("resource\\image\\x.png"))
        noticePopupRemove.setIcon(QIcon(pixmap))
        noticePopupRemove.setIconSize(QSize(24, 24))
        noticePopupRemove.show()

        self.activeErrorPopup.append([noticePopup, frameHeight, self.activeErrorPopupNumber])
        self.activeErrorPopupCount += 1
        self.activeErrorPopupNumber += 1

    ## 알림 창 제거
    def removeNoticePopup(self, num=-1):
        if num != -1:
            for i, j in enumerate(self.activeErrorPopup):
                if num == j[2]:
                    j[0].deleteLater()
                    self.activeErrorPopup.pop(i)
        else:
            self.activeErrorPopup[-1][0].deleteLater()
            self.activeErrorPopup.pop()
        # self.activeErrorPopup[num][0].deleteLater()
        # self.activeErrorPopup.pop(0)
        self.activeErrorPopupCount -= 1
        self.updatePosition()

    ## 모든 팝업창 제거
    def disablePopup(self):
        if self.activePopup == "":
            return
        else:
            self.settingPopupFrame.deleteLater()
        self.activePopup = ""

    ## 팝업창 할당
    def activatePopup(self, text):
        self.disablePopup()
        self.activePopup = text

    ## 인풋 팝업 생성
    def makePopupInput(self, popup_type):
        match popup_type:
            case "delay":
                x = 140
                y = 370
                width = 140

                frame = self.sidebarFrame
            case "cooltime":
                x = 140
                y = 500
                width = 140

                frame = self.sidebarFrame
            case ("tabName", _):
                x = 360 + 200 * self.recentPreset
                y = 80
                width = 200

                frame = self
        self.settingPopupFrame = QFrame(frame)
        self.settingPopupFrame.setStyleSheet("background-color: white; border-radius: 10px;")
        self.settingPopupFrame.setFixedSize(width, 40)
        self.settingPopupFrame.move(x, y)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 0, 30, 150))
        self.settingPopupFrame.show()

        match popup_type:
            case "delay":
                default = str(self.inputDelay)
            case "cooltime":
                default = str(self.inputCooltime)
            case ("tabName", _):
                default = self.tabNames[self.recentPreset]
        self.settingPopupInput = QLineEdit(default, self.settingPopupFrame)
        self.settingPopupInput.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.settingPopupInput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.settingPopupInput.setStyleSheet("border: 1px solid black; border-radius: 10px;")
        self.settingPopupInput.setFixedSize(width - 70, 30)
        self.settingPopupInput.move(5, 5)
        self.settingPopupInput.setFocus()

        self.settingPopupButton = QPushButton("적용", self.settingPopupFrame)
        self.settingPopupButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.settingPopupButton.clicked.connect(lambda: self.onInputPopupClick(popup_type))
        self.settingPopupButton.setStyleSheet(
            """
                            QPushButton {
                                background-color: "white"; border-radius: 10px; border: 1px solid black;
                            }
                            QPushButton:hover {
                                background-color: #cccccc;
                            }
                        """
        )
        self.settingPopupButton.setFixedSize(50, 30)
        self.settingPopupButton.move(width - 60, 5)
        # self.settingServerFrame.setGraphicsEffect(self.getShadow(0, 5))

        self.settingPopupButton.show()
        self.settingPopupInput.show()

        self.update()
        self.updatePosition()

    ## 인풋 팝업 확인 클릭시 실행
    def onInputPopupClick(self, input_type):
        text = self.settingPopupInput.text()

        if input_type == "delay" or input_type == "cooltime":
            try:
                text = int(text)
            except:
                self.disablePopup()
                self.makeNoticePopup("delayInputError" if input_type == "delay" else "cooltimeInputError")
                return

        match input_type:
            case "delay":
                if not (self.minDelay <= text <= self.maxDelay):
                    self.disablePopup()
                    self.makeNoticePopup("delayInputError")
                    return
                self.buttonInputDelay.setText(str(text))
                self.inputDelay = text
                self.delay = text
            case "cooltime":
                if not (self.minCooltime <= text <= self.maxCooltime):
                    self.disablePopup()
                    self.makeNoticePopup("cooltimeInputError")
                    return
                self.buttonInputCooltime.setText(str(text))
                self.inputCooltime = text
                self.cooltimeReduce = text
            case ("tabName", _):
                self.tabButtonList[input_type[1]].setText(" " + text)
                self.tabNames[input_type[1]] = text

        self.dataSave()
        self.disablePopup()

        self.update()
        self.updatePosition()

    ## 사이드바 설정 - 서버 클릭
    def onServerClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.activePopup == "settingServer":
            self.disablePopup()
        else:
            self.activatePopup("settingServer")

            self.settingPopupFrame = QFrame(self.sidebarFrame)
            self.settingPopupFrame.setStyleSheet("background-color: white; border-radius: 10px;")
            self.settingPopupFrame.setFixedSize(130, 5 + 35 * len(self.serverList))
            self.settingPopupFrame.move(25, 240)
            self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
            self.settingPopupFrame.show()

            for i in range(len(self.serverList)):
                self.settingServerButton = QPushButton(self.serverList[i], self.settingPopupFrame)
                self.settingServerButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
                self.settingServerButton.clicked.connect(partial(lambda x: self.onServerPopupClick(x), i))
                self.settingServerButton.setStyleSheet(
                    f"""
                                QPushButton {{
                                    background-color: {"white" if i != self.serverID else "#dddddd"}; border-radius: 10px;
                                }}
                                QPushButton:hover {{
                                    background-color: #cccccc;
                                }}
                            """
                )
                self.settingServerButton.setFixedSize(120, 30)
                self.settingServerButton.move(5, 5 + 35 * i)
                # self.settingServerFrame.setGraphicsEffect(self.getShadow(0, 5))

                self.settingServerButton.show()

    ## 사이트바 서버 목록 팝업창 클릭시 실행
    def onServerPopupClick(self, num):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

    ## 사이드바 설정 - 직업 클릭
    def onJobClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.activePopup == "settingJob":
            self.disablePopup()
        else:
            self.activatePopup("settingJob")

            self.settingPopupFrame = QFrame(self.sidebarFrame)
            self.settingPopupFrame.setStyleSheet("background-color: white; border-radius: 10px;")
            self.settingPopupFrame.setFixedSize(130, 5 + 35 * len(self.jobList[self.serverID]))
            self.settingPopupFrame.move(145, 240)
            self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
            self.settingPopupFrame.show()

            for i in range(len(self.jobList[self.serverID])):
                self.settingJobButton = QPushButton(self.jobList[self.serverID][i], self.settingPopupFrame)
                self.settingJobButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
                self.settingJobButton.clicked.connect(partial(lambda x: self.onJobPopupClick(x), i))
                self.settingJobButton.setStyleSheet(
                    f"""
                                QPushButton {{
                                    background-color: {"white" if i != self.jobID else "#dddddd"}; border-radius: 10px;
                                }}
                                QPushButton:hover {{
                                    background-color: #cccccc;
                                }}
                            """
                )
                self.settingJobButton.setFixedSize(120, 30)
                self.settingJobButton.move(5, 5 + 35 * i)
                # self.settingServerFrame.setGraphicsEffect(self.getShadow(0, 5))

                self.settingJobButton.show()

    ## 사이트바 직업 목록 팝업창 클릭시 실행
    def onJobPopupClick(self, num):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.jobID != num:
            self.jobID = num
            self.selectedSkillList = [-1, -1, -1, -1, -1, -1]
            self.linkSkillList = []

            self.buttonJobList.setText(self.jobList[self.serverID][num])

            for i in range(8):
                self.comboCount[i] = self.skillComboCountList[self.serverID][self.jobID][i]

            for i in range(8):
                pixmap = QPixmap(self.getSkillImage(i))
                self.selectableSkillImageButton[i].setIcon(QIcon(pixmap))
                self.selectableSkillImageName[i].setText(self.skillNameList[self.serverID][self.jobID][i])

            for i in range(6):
                if self.selectedSkillList[i] != -1:
                    pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[i]))
                else:
                    pixmap = QPixmap(convertResourcePath("resource\\image\\emptySkill.png"))
                self.selectedSkillImageButton[i].setIcon(QIcon(pixmap))

            self.updatePosition()

            self.dataSave()
        self.disablePopup()

    ## 사이드바 설정 - 기본 딜레이 클릭
    def onDefaultDelayClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.activeDelaySlot == 0:
            return

        self.activeDelaySlot = 0
        self.delay = self.defaultDelay

        self.buttonDefaultDelay.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputDelay.setStyleSheet("QPushButton { color: #999999; }")

        self.dataSave()

    ## 사이드바 설정 -  유저 딜레이 클릭
    def onInputDelayClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.activePopup == "settingDelay":
            self.disablePopup()
            return
        self.disablePopup()

        if self.activeDelaySlot == 1:
            self.activatePopup("settingDelay")

            self.makePopupInput("delay")
        else:
            self.activeDelaySlot = 1
            self.delay = self.inputDelay

            self.buttonDefaultDelay.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputDelay.setStyleSheet("QPushButton { color: #000000; }")

            self.dataSave()

    ## 사이드바 설정 - 기본 쿨타임 감소 클릭
    def onDefaultCooltimeClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.activeCooltimeSlot == 0:
            return

        self.activeCooltimeSlot = 0
        self.cooltimeReduce = 0

        self.buttonDefaultCooltime.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputCooltime.setStyleSheet("QPushButton { color: #999999; }")

        self.dataSave()

    ## 사이드바 설정 - 유저 쿨타임 감소 클릭
    def onInputCooltimeClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.activePopup == "settingCooltime":
            self.disablePopup()
            return
        self.disablePopup()

        if self.activeCooltimeSlot == 1:
            self.activatePopup("settingCooltime")

            self.makePopupInput("cooltime")
        else:
            self.activeCooltimeSlot = 1
            self.cooltimeReduce = self.inputCooltime

            self.buttonDefaultCooltime.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputCooltime.setStyleSheet("QPushButton { color: #000000; }")

            self.dataSave()

    ## 가상키보드 생성
    def makeKeyboardPopup(self, kb_type):
        def makePresetKey(key, row, column, disabled=False):
            button = QPushButton(key, self.settingPopupFrame)
            match kb_type:
                case "StartKey":
                    button.clicked.connect(lambda: self.onStartKeyPopupKeyboardClick(key, disabled))
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(key, disabled, kb_type[1])
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(key, disabled, kb_type[1])
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 5px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(30, 30)
            match column:
                case 0:
                    defaultX = 115
                case 1:
                    defaultX = 5
                case 2:
                    defaultX = 50
                case 3:
                    defaultX = 60
                case 4:
                    defaultX = 80
            defaultY = 5

            self.adjustFontSize(button, key, 20)
            button.move(
                defaultX + row * 35,
                defaultY + column * 35,
            )
            button.show()

        def makeKey(key, x, y, width, height, disabled=False):
            button = QPushButton(key, self.settingPopupFrame)
            match kb_type:
                case "StartKey":
                    button.clicked.connect(lambda: self.onStartKeyPopupKeyboardClick(key, disabled))
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(key, disabled, kb_type[1])
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(key, disabled, kb_type[1])
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 5px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(width, height)
            self.adjustFontSize(button, key, 20)
            button.move(x, y)
            button.show()

        def makeImageKey(key, x, y, width, height, image, size, rot, disabled=False):
            button = QPushButton(self.settingPopupFrame)
            pixmap = QPixmap(image)
            pixmap = pixmap.transformed(QTransform().rotate(rot))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(size, size))
            match kb_type:
                case "StartKey":
                    button.clicked.connect(lambda: self.onStartKeyPopupKeyboardClick(key, disabled))
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(key, disabled, kb_type[1])
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(key, disabled, kb_type[1])
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 5px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(width, height)
            button.move(x, y)
            button.show()

        self.settingPopupFrame = QFrame(self)
        self.settingPopupFrame.setStyleSheet("background-color: white; border-radius: 10px;")
        self.settingPopupFrame.setFixedSize(635, 215)
        self.settingPopupFrame.move(30, 30)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 0, 30, 150))
        self.settingPopupFrame.show()

        k0 = [
            "Esc",
            "F1",
            "F2",
            "F3",
            "F4",
            "F5",
            "F6",
            "F7",
            "F8",
            "F9",
            "F10",
            "F11",
            "F12",
        ]
        k1 = ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]
        k2 = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"]
        k3 = ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'"]
        k4 = ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"]

        for i, key in enumerate(k0):
            x = 5 + 35 * i
            if i >= 1:
                x += 15
            if i >= 5:
                x += 15
            if i >= 9:
                x += 15

            if key == "Esc":
                makeKey(
                    key,
                    x,
                    5,
                    30,
                    30,
                    True,
                )
            else:
                makeKey(
                    key,
                    x,
                    5,
                    30,
                    30,
                    self.isKeyUsing(key),
                )

        row = 0
        column = 1
        for key in k1:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey(
            "Back",
            460,
            40,
            40,
            30,
            True,
        )

        makeKey(
            "Tab",
            5,
            75,
            40,
            30,
            self.isKeyUsing("Tab"),
        )
        row = 0
        column += 1
        for key in k2:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1

        makeKey(
            "Caps Lock",
            5,
            110,
            50,
            30,
            True,
        )
        row = 0
        column += 1
        for key in k3:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey(
            "Enter",
            445,
            110,
            55,
            30,
            self.isKeyUsing("Enter"),
        )

        makeKey(
            "Shift",
            5,
            145,
            70,
            30,
            self.isKeyUsing("Shift"),
        )
        row = 0
        column += 1
        for key in k4:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey(
            "Shift",
            430,
            145,
            70,
            30,
            self.isKeyUsing("Shift"),
        )

        makeKey(
            "Ctrl",
            5,
            180,
            45,
            30,
            self.isKeyUsing("Ctrl"),
        )
        makeImageKey(
            "Window",
            55,
            180,
            45,
            30,
            convertResourcePath("resource\\image\\window.png"),
            32,
            0,
            True,
        )
        makeKey(
            "Alt",
            105,
            180,
            45,
            30,
            self.isKeyUsing("Alt"),
        )
        makeKey(
            "Space",
            155,
            180,
            145,
            30,
            self.isKeyUsing("Space"),
        )
        makeKey(
            "Alt",
            305,
            180,
            45,
            30,
            self.isKeyUsing("Alt"),
        )
        makeImageKey(
            "Window",
            355,
            180,
            45,
            30,
            convertResourcePath("resource\\image\\window.png"),
            32,
            0,
            True,
        )
        makeKey(
            "Fn",
            405,
            180,
            45,
            30,
            True,
        )
        makeKey(
            "Ctrl",
            455,
            180,
            45,
            30,
            self.isKeyUsing("Ctrl"),
        )

        k5 = [
            ["PrtSc", "ScrLk", "Pause"],
            ["Insert", "Home", """Page\nUp"""],
            ["Delete", "End", "Page\nDown"],
        ]
        for i1, i2 in enumerate(k5):
            for j1, j2 in enumerate(i2):
                makeKey(
                    j2,
                    530 + j1 * 35,
                    5 + 35 * i1,
                    30,
                    30,
                    self.isKeyUsing(j2),
                )

        makeImageKey(
            "Up",
            565,
            145,
            30,
            30,
            convertResourcePath("resource\\image\\arrow.png"),
            16,
            0,
            self.isKeyUsing("Up"),
        )
        makeImageKey(
            "Left",
            530,
            180,
            30,
            30,
            convertResourcePath("resource\\image\\arrow.png"),
            16,
            270,
            self.isKeyUsing("Left"),
        )
        makeImageKey(
            "Down",
            565,
            180,
            30,
            30,
            convertResourcePath("resource\\image\\arrow.png"),
            16,
            180,
            self.isKeyUsing("Down"),
        )
        makeImageKey(
            "Right",
            600,
            180,
            30,
            30,
            convertResourcePath("resource\\image\\arrow.png"),
            16,
            90,
            self.isKeyUsing("Right"),
        )

    ## 시작키 설정용 가상키보드 키 클릭시 실행
    def onStartKeyPopupKeyboardClick(self, key, disabled):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        match key:
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        self.buttonInputStartKey.setText(key)
        self.inputStartKey = key
        self.startKey = key

        self.dataSave()
        self.disablePopup()

    ## 사이드바 설정 - 기본 시작키 클릭
    def onDefaultStartKeyClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.activeStartKeySlot == 0:
            return

        if self.inputStartKey != "F9" and self.isKeyUsing("F9"):
            self.makeNoticePopup("StartKeyChangeError")
            return

        self.activeStartKeySlot = 0
        self.startKey = "F9"

        self.buttonDefaultStartKey.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputStartKey.setStyleSheet("QPushButton { color: #999999; }")

        self.dataSave()

    ## 사이드바 설정 - 유저 시작키 클릭
    def onInputStartKeyClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.activePopup == "settingStartKey":
            self.disablePopup()
            return
        self.disablePopup()

        if self.activeStartKeySlot == 1:
            self.activatePopup("settingStartKey")

            self.makeKeyboardPopup("StartKey")
        else:
            if self.isKeyUsing(self.inputStartKey) and not (self.inputStartKey == "F9"):
                self.makeNoticePopup("StartKeyChangeError")
                return
            self.activeStartKeySlot = 1
            self.startKey = self.inputStartKey

            self.buttonDefaultStartKey.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputStartKey.setStyleSheet("QPushButton { color: #000000; }")

            self.dataSave()

    ## 사이드바 설정 - 마우스설정1 클릭
    def on1stMouseTypeClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.activeMouseClickSlot == 0:
            return

        self.activeMouseClickSlot = 0

        self.button1stMouseType.setStyleSheet("QPushButton { color: #000000; }")
        self.button2ndMouseType.setStyleSheet("QPushButton { color: #999999; }")

        self.dataSave()

    ## 사이드바 설정 - 마우스설정2 클릭
    def on2ndMouseTypeClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.activeMouseClickSlot == 1:
            return

        self.activeMouseClickSlot = 1

        self.button1stMouseType.setStyleSheet("QPushButton { color: #999999; }")
        self.button2ndMouseType.setStyleSheet("QPushButton { color: #000000; }")

        self.dataSave()

    ## 탭 클릭
    def onTabClick(self, num):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.recentPreset == num:
            if self.activePopup == "changeTabName":
                self.disablePopup()
            else:
                self.activatePopup("changeTabName")
                self.makePopupInput(("tabName", num))
            return
        self.disablePopup()

        self.changeTab(num)

    ## 탭 추가버튼 클릭
    def onTabAddClick(self):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        self.dataAdd()

        tabNum = len(self.tabNames)
        self.dataLoad(tabNum)

        tabBackground = QLabel("", self.page1)
        tabBackground.setStyleSheet(
            """background-color: #eeeef5; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
        )
        tabBackground.setFixedSize(250, 50)
        tabBackground.move(340 + 250 * tabNum, 20)
        tabBackground.setGraphicsEffect(self.getShadow(5, -2))
        tabBackground.show()

        tabButton = QPushButton(f" {self.tabNames[tabNum]}", self.page1)
        tabButton.clicked.connect(lambda: self.onTabClick(tabNum))
        tabButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        tabButton.setStyleSheet(
            """
            QPushButton {
                background-color: #eeeef5; border-radius: 15px; text-align: left;
            }
            QPushButton:hover {
                background-color: #fafaff;
            }
        """
        )
        tabButton.setFixedSize(240, 40)
        tabButton.move(345 + 250 * tabNum, 25)
        tabButton.show()

        tabRemoveButton = QPushButton("", self.page1)
        tabRemoveButton.clicked.connect(lambda: self.onTabRemoveClick(tabNum))
        tabRemoveButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 16))
        tabRemoveButton.setStyleSheet(
            """
            QPushButton {
                background-color: transparent; border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )
        pixmap = QPixmap(convertResourcePath("resource\\image\\x.png"))
        tabRemoveButton.setIcon(QIcon(pixmap))
        tabRemoveButton.setFixedSize(40, 40)
        tabRemoveButton.move(545 + 250 * tabNum, 25)
        tabRemoveButton.show()

        self.tabButtonList.append(tabButton)
        self.tabList.append(tabBackground)
        self.tabRemoveList.append(tabRemoveButton)

        self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

        self.changeTab(tabNum)

    ## 탭 제거버튼 클릭
    def onTabRemoveClick(self, num):
        self.isTabRemovePopupActivated = True
        self.tabRemoveBackground = QFrame(self.page1)
        self.tabRemoveBackground.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        self.tabRemoveBackground.setFixedSize(self.width(), self.height())
        self.tabRemoveBackground.show()

        self.tabRemoveFrame = QFrame(self.tabRemoveBackground)
        self.tabRemoveFrame.setStyleSheet("QFrame { background-color: white; border-radius: 20px; }")
        self.tabRemoveFrame.setFixedSize(340, 140)
        self.tabRemoveFrame.move(round(self.width() * 0.5 - 170), round(self.height() * 0.5 - 60))
        self.tabRemoveFrame.setGraphicsEffect(self.getShadow(2, 2, 20))
        self.tabRemoveFrame.show()

        self.tabRemoveNameLabel = QLabel("", self.tabRemoveFrame)
        self.tabRemoveNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabRemoveNameLabel.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.tabRemoveNameLabel.setFixedSize(330, 30)
        self.tabRemoveNameLabel.setText(
            self.limitText(f'정말 "{self.tabNames[num]}', self.tabRemoveNameLabel, margin=5) + '"'
        )
        self.tabRemoveNameLabel.move(5, 10)
        self.tabRemoveNameLabel.show()

        self.tabRemoveLabel = QLabel("탭을 삭제하시겠습니까?", self.tabRemoveFrame)
        self.tabRemoveLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabRemoveLabel.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.tabRemoveLabel.setFixedSize(330, 30)
        self.tabRemoveLabel.move(5, 40)
        self.tabRemoveLabel.show()

        self.settingJobButton = QPushButton("예", self.tabRemoveFrame)
        self.settingJobButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.settingJobButton.clicked.connect(lambda: self.onTabRemovePopupClick(num))
        self.settingJobButton.setStyleSheet(
            """
                        QPushButton {
                            background-color: #86A7FC; border-radius: 10px;
                        }
                        QPushButton:hover {
                            background-color: #6498f0;
                        }
                    """
        )
        self.settingJobButton.setFixedSize(100, 40)
        self.settingJobButton.move(50, 80)
        self.settingJobButton.setGraphicsEffect(self.getShadow(2, 2, 20))
        self.settingJobButton.show()

        self.settingJobButton = QPushButton("아니오", self.tabRemoveFrame)
        self.settingJobButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.settingJobButton.clicked.connect(lambda: self.onTabRemovePopupClick(num, False))
        self.settingJobButton.setStyleSheet(
            """
                        QPushButton {
                            background-color: #ffffff; border-radius: 10px;
                        }
                        QPushButton:hover {
                            background-color: #eeeeee;
                        }
                    """
        )
        self.settingJobButton.setFixedSize(100, 40)
        self.settingJobButton.move(170, 80)
        self.settingJobButton.setGraphicsEffect(self.getShadow(2, 2, 20))
        self.settingJobButton.show()

    def onTabRemovePopupClick(self, num=0, remove=True):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()
        self.tabRemoveBackground.deleteLater()
        self.isTabRemovePopupActivated = False

        if not remove:
            return

        tabCount = len(self.tabNames)

        if tabCount != 1:
            if self.recentPreset == num:
                if (tabCount - 1) > num:
                    self.tabNames.pop(num)
                    self.dataRemove(num)
                    self.tabButtonList[num].deleteLater()
                    self.tabButtonList.pop(num)
                    self.tabList[num].deleteLater()
                    self.tabList.pop(num)
                    self.tabRemoveList[num].deleteLater()
                    self.tabRemoveList.pop(num)

                    # print(self.tabButtonList)

                    for i, j in enumerate(self.tabButtonList):
                        j.clicked.disconnect()
                        j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                        self.tabRemoveList[i].clicked.disconnect()
                        self.tabRemoveList[i].clicked.connect(partial(lambda x: self.onTabRemoveClick(x), i))

                        self.tabList[i].move(340 + 250 * i, 20)
                        self.tabButtonList[i].move(345 + 250 * i, 25)
                        self.tabRemoveList[i].move(545 + 250 * i, 25)
                    self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

                    self.changeTab(num)
                else:
                    self.tabNames.pop(num)
                    self.dataRemove(num)
                    self.tabButtonList[num].deleteLater()
                    self.tabButtonList.pop(num)
                    self.tabList[num].deleteLater()
                    self.tabList.pop(num)
                    self.tabRemoveList[num].deleteLater()
                    self.tabRemoveList.pop(num)

                    self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

                    self.changeTab(num - 1)
                    self.recentPreset = num - 1
            elif self.recentPreset > num:
                self.tabNames.pop(num)
                self.dataRemove(num)
                self.tabButtonList[num].deleteLater()
                self.tabButtonList.pop(num)
                self.tabList[num].deleteLater()
                self.tabList.pop(num)
                self.tabRemoveList[num].deleteLater()
                self.tabRemoveList.pop(num)

                for i, j in enumerate(self.tabButtonList):
                    j.clicked.disconnect()
                    j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                    self.tabRemoveList[i].clicked.disconnect()
                    self.tabRemoveList[i].clicked.connect(partial(lambda x: self.onTabRemoveClick(x), i))

                    self.tabList[i].move(340 + 250 * i, 20)
                    self.tabButtonList[i].move(345 + 250 * i, 25)
                    self.tabRemoveList[i].move(545 + 250 * i, 25)
                self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

                self.changeTab(self.recentPreset - 1)
            elif self.recentPreset < num:
                # print(self.tabNames)
                # print(num)
                self.tabNames.pop(num)
                self.dataRemove(num)
                self.tabButtonList[num].deleteLater()
                self.tabButtonList.pop(num)
                self.tabList[num].deleteLater()
                self.tabList.pop(num)
                self.tabRemoveList[num].deleteLater()
                self.tabRemoveList.pop(num)

                for i, j in enumerate(self.tabButtonList):
                    j.clicked.disconnect()
                    j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                    self.tabRemoveList[i].clicked.disconnect()
                    self.tabRemoveList[i].clicked.connect(partial(lambda x: self.onTabRemoveClick(x), i))

                    self.tabList[i].move(340 + 250 * i, 20)
                    self.tabButtonList[i].move(345 + 250 * i, 25)
                    self.tabRemoveList[i].move(545 + 250 * i, 25)
                self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)
        else:
            self.dataRemove(0)
            self.dataLoad(0)
            self.changeTab(0)
            self.tabButtonList[0].setText(" " + self.tabNames[0])

        self.update()
        self.updatePosition()
        self.dataSave()

    ## 링크스킬 단축키용 가상키보드 키 클릭시 실행
    def onLinkSkillKeyPopupKeyboardClick(self, key, disabled, data):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        match key:
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        self.disablePopup()

        data[1] = key
        self.reloadSetting3(data)

    ## 스킬 단축키용 가상키보드 키 클릭시 실행
    def onSkillKeyPopupKeyboardClick(self, key, disabled, num):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        match key:
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        self.selectedSkillKey[num].setText(key)
        self.adjustFontSize(self.selectedSkillKey[num], key, 24)
        self.skillKeys[num] = key

        self.dataSave()
        self.disablePopup()

    ## 스킬 단축키 설정 버튼 클릭
    def onSkillKeyClick(self, num):
        if self.isActivated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.activePopup == "skillKey":
            self.disablePopup()
            return
        self.disablePopup()

        self.activatePopup("skillKey")
        self.makeKeyboardPopup(["skillKey", num])

    ## 마우스 클릭하면 실행
    def mousePressEvent(self, event):
        self.disablePopup()
        if self.layoutType == 0:
            self.cancelSkillSelection()

    ## 사이드바 구분선 생성
    def paintEvent(self, event):
        if self.layoutType == 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setPen(QPen(QColor(180, 180, 180), 1, Qt.PenStyle.SolidLine))
            painter.drawLine(320, 0, 320, self.height())

    ## 창 크기 조절시 실행
    def resizeEvent(self, event):
        self.update()
        self.updatePosition()

    ## 창 크기 조절시 위젯 위치, 크기 조절
    def updatePosition(self):
        if self.layoutType == 0:
            self.sidebarScrollArea.setFixedSize(319, self.height() - 24)
            xAddedSize = self.width() - 960
            xMultSize = ((self.width() - 400) / 560 - 1) * 0.5
            yAddedSize = self.height() - 540
            yMultSize = ((self.height() - 90) / 450 - 1) * 0.5
            self.skillBackground.setFixedSize(self.width() - 400, self.height() - 90)

            self.skillPreviewFrame.move(
                round(136 + xAddedSize * 0.5 - 288 * xMultSize * 0.5),
                round(10 + yAddedSize * 0.1 - 48 * yMultSize * 0.5),
            )
            self.skillPreviewFrame.setFixedSize(round(288 * (xMultSize + 1)), round(48 * (yMultSize + 1)))
            for i, j in enumerate(self.skillPreviewList):
                j.setFixedSize(round((288 * (xMultSize + 1) / 6)), round(48 * (yMultSize + 1)))
                j.move(
                    round((self.skillPreviewFrame.width() - j.width() * len(self.skillPreviewList)) * 0.5)
                    + j.width() * i,
                    0,
                )
                j.setIconSize(QSize(min(j.width(), j.height()), min(j.width(), j.height())))

            for i, j in enumerate(self.selectableSkillFrame):
                j.move(
                    round(
                        (50 + xAddedSize * 0.2)
                        + (64 + (68 + xAddedSize * 0.2)) * (i % 4)
                        - 64 * xMultSize * 0.5
                    ),
                    round(
                        (80 + yAddedSize * 0.3 + (120 + yAddedSize * 0.2) * (i // 4)) - 88 * yMultSize * 0.5
                    ),
                )
                j.setFixedSize(round(64 * (xMultSize + 1)), round(88 * (yMultSize + 1)))

            for i in self.selectableSkillImageButton:
                i.setFixedSize(round(64 * (xMultSize + 1)), round(64 * (yMultSize + 1)))
                i.setIconSize(QSize(min(i.width(), i.height()), min(i.width(), i.height())))

            for i, j in enumerate(self.selectableSkillImageName):
                j.move(0, round(64 * (yMultSize + 1)))
                j.setFixedSize(round(64 * (xMultSize + 1)), round(24 * (yMultSize + 1)))
                j.setText(self.skillNameList[self.serverID][self.jobID][i])
                j.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))

            self.selectionSkillLine.move(20, round(309 + yAddedSize * 0.7))
            self.selectionSkillLine.setFixedSize(520 + xAddedSize, 1)
            for i, j in enumerate(self.selectedSkillFrame):
                j.move(
                    round(
                        (38 + xAddedSize * 0.1) + (64 + (20 + xAddedSize * 0.16)) * i - 64 * xMultSize * 0.5
                    ),
                    round(330 + yAddedSize * 0.9 - 96 * yMultSize * 0.5),
                )
                j.setFixedSize(round(64 * (xMultSize + 1)), round(96 * (yMultSize + 1)))
            for i in self.selectedSkillImageButton:
                i.setFixedSize(round(64 * (xMultSize + 1)), round(64 * (yMultSize + 1)))
                i.setIconSize(QSize(min(i.width(), i.height()), min(i.width(), i.height())))
            for i, j in enumerate(self.selectedSkillKey):
                j.move(0, round(72 * (yMultSize + 1)))
                j.setFixedSize(round(64 * (xMultSize + 1)), round(24 * (yMultSize + 1)))
                self.adjustFontSize(j, self.skillKeys[i], 20)

            if 460 + 200 * len(self.tabNames) <= self.width():
                for tabNum in range(len(self.tabNames)):
                    self.tabList[tabNum].move(360 + 200 * tabNum, 20)
                    self.tabList[tabNum].setFixedSize(200, 50)
                    self.tabButtonList[tabNum].move(365 + 200 * tabNum, 25)
                    self.tabButtonList[tabNum].setFixedSize(190, 40)
                    self.tabButtonList[tabNum].setText(
                        self.limitText(f" {self.tabNames[tabNum]}", self.tabButtonList[tabNum])
                    )
                    self.tabRemoveList[tabNum].move(515 + 200 * tabNum, 25)
                    self.tabAddButton.move(370 + 200 * len(self.tabNames), 25)

                    if self.activePopup == "changeTabName":
                        self.settingPopupFrame.move(360 + 200 * self.recentPreset, 80)
            else:
                width = round((self.width() - 460) / len(self.tabNames))
                for tabNum in range(len(self.tabNames)):
                    self.tabList[tabNum].move(360 + width * tabNum, 20)
                    self.tabList[tabNum].setFixedSize(width, 50)
                    self.tabButtonList[tabNum].move(365 + width * tabNum, 25)
                    self.tabButtonList[tabNum].setFixedSize(width - 10, 40)
                    self.tabButtonList[tabNum].setText(
                        self.limitText(f" {self.tabNames[tabNum]}", self.tabButtonList[tabNum])
                    )
                    self.tabRemoveList[tabNum].move(315 + width * (tabNum + 1), 25)
                    self.tabAddButton.move(self.width() - 80, 25)
                    # self.tabAddButton.move(350 + width * len(self.tabNames), 25)
                if self.activePopup == "changeTabName":
                    self.settingPopupFrame.move(360 + width * self.recentPreset, 80)

            if self.isTabRemovePopupActivated:
                self.tabRemoveBackground.setFixedSize(self.width(), self.height())
                self.tabRemoveFrame.move(round(self.width() * 0.5 - 170), round(self.height() * 0.5 - 60))
                self.tabRemoveBackground.raise_()

        else:  # 레이아웃 1 (계산기)
            deltaWidth = self.width() - self.defaultWindowWidth

            self.sim_navFrame.move(self.sim_margin + deltaWidth // 2, self.sim_margin)
            self.sim_mainFrame.setFixedWidth(self.width() - self.scrollBarWidth - self.sim_margin * 2)
            self.sim_mainScrollArea.setFixedSize(
                self.width() - self.sim_margin,
                self.height()
                - self.labelCreator.height()
                - self.sim_navHeight
                - self.sim_margin * 2
                - self.sim_main1_D,
            )

            if self.simType == 1:  # 정보 입력
                self.sim1_frame1.move(deltaWidth // 2, 0)
                self.sim1_frame2.move(
                    deltaWidth // 2,
                    self.sim1_frame1.y() + self.sim1_frame1.height() + self.sim_main_D,
                )
                self.sim1_frame3.move(
                    deltaWidth // 2,
                    self.sim1_frame2.y() + self.sim1_frame2.height() + self.sim_main_D,
                )

            elif self.simType == 2:  # 시뮬레이터
                self.sim2_frame1.move(deltaWidth // 2, 0)
                self.sim2_frame2.move(
                    deltaWidth // 2,
                    self.sim2_frame1.y() + self.sim2_frame1.height() + self.sim_main_D,
                )

            elif self.simType == 3:  # 스탯 계산기
                self.sim3_frame1.move(deltaWidth // 2, 0)
                self.sim3_frame2.move(
                    deltaWidth // 2,
                    self.sim3_frame1.y() + self.sim3_frame1.height() + self.sim_main_D,
                )
                self.sim3_frame3.move(
                    deltaWidth // 2,
                    self.sim3_frame2.y() + self.sim3_frame2.height() + self.sim_main_D,
                )
                self.sim3_frame4.move(
                    deltaWidth // 2,
                    self.sim3_frame3.y() + self.sim3_frame3.height() + self.sim_main_D,
                )

            elif self.simType == 4:  # 캐릭터 카드
                self.sim4_frame.move(deltaWidth // 2, 0)

        # 항상 업데이트
        self.labelCreator.move(2, self.height() - 25)
        for i, j in enumerate(self.activeErrorPopup):
            j[0].move(
                self.width() - 420,
                self.height() - j[1] - 15 - i * 10,
            )
        for i in self.activeErrorPopup:
            i[0].raise_()

    ## 실행, 탭 변경 시 데이터 로드
    def dataLoad(self, num=-1):
        try:
            if os.path.isfile(fileDir):
                with open(fileDir, "r", encoding="UTF8") as f:
                    jsonObject = json.load(f)
                    if num == -1:
                        self.recentPreset = jsonObject["recentPreset"]
                    else:
                        self.recentPreset = num
                    data = jsonObject["preset"][self.recentPreset]

                    ## name
                    self.tabNames = [
                        jsonObject["preset"][i]["name"] for i in range(len(jsonObject["preset"]))
                    ]

                    ## skills
                    self.selectedSkillList = data["skills"]["activeSkills"]
                    self.skillKeys = data["skills"]["skillKeys"]

                    ## settings
                    self.serverID = data["settings"]["serverID"]
                    self.jobID = data["settings"]["jobID"]

                    self.activeDelaySlot = data["settings"]["delay"][0]
                    self.inputDelay = data["settings"]["delay"][1]
                    if self.activeDelaySlot == 0:
                        self.delay = self.defaultDelay
                    else:
                        self.delay = self.inputDelay

                    self.activeCooltimeSlot = data["settings"]["cooltime"][0]
                    self.inputCooltime = data["settings"]["cooltime"][1]
                    if self.activeCooltimeSlot == 0:
                        self.cooltimeReduce = 0
                    else:
                        self.cooltimeReduce = self.inputCooltime

                    self.activeStartKeySlot = data["settings"]["startKey"][0]
                    self.inputStartKey = data["settings"]["startKey"][1]
                    if self.activeStartKeySlot == 0:
                        self.startKey = "F9"
                    else:
                        self.startKey = self.inputStartKey

                    self.activeMouseClickSlot = data["settings"]["mouseClickType"]

                    ## usageSettings
                    self.ifUseSkill = [data["usageSettings"][i][0] for i in range(8)]
                    self.ifUseSole = [data["usageSettings"][i][1] for i in range(8)]
                    self.comboCount = [data["usageSettings"][i][2] for i in range(8)]
                    self.skillPriority = [data["usageSettings"][i][3] for i in range(8)]

                    ## linkSettings
                    self.linkSkillList = [[] for _ in range(len(data["linkSettings"]))]
                    for i, j in enumerate(self.linkSkillList):
                        j.append(data["linkSettings"][i]["type"])
                        j.append(data["linkSettings"][i]["key"])
                        j.append(data["linkSettings"][i]["skills"])

                    ## info
                    self.info_stats = data["info"]["stats"]
                    self.info_skills = data["info"]["skills"]
                    self.info_simInfo = data["info"]["simInfo"]
            else:
                self.dataMake()
                self.dataLoad()
        except:
            self.dataMake()
            self.dataLoad()

    ## 오류발생, 최초실행 시 데이터 생성
    def dataMake(self):
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
                        "delay": [0, self.defaultDelay],
                        "cooltime": [0, 0],
                        "startKey": [0, "F9"],
                        "mouseClickType": 0,
                    },
                    "usageSettings": [
                        [True, True, 3, None],
                        [True, True, 2, None],
                        [True, True, 2, None],
                        [True, True, 1, None],
                        [True, True, 3, None],
                        [True, True, 1, None],
                        [True, True, 1, None],
                        [True, True, 3, None],
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

        if not os.path.isdir("C:\\PDFiles"):
            os.mkdir("C:\\PDFiles")
        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f)

    ## 데이터 저장
    def dataSave(self):
        with open(fileDir, "r", encoding="UTF8") as f:
            jsonObject = json.load(f)

        jsonObject["recentPreset"] = self.recentPreset
        data = jsonObject["preset"][self.recentPreset]

        data["name"] = self.tabNames[self.recentPreset]

        data["skills"]["activeSkills"] = self.selectedSkillList
        data["skills"]["skillKeys"] = self.skillKeys

        data["settings"]["serverID"] = self.serverID
        data["settings"]["jobID"] = self.jobID
        data["settings"]["delay"][0] = self.activeDelaySlot
        data["settings"]["delay"][1] = self.inputDelay
        data["settings"]["cooltime"][0] = self.activeCooltimeSlot
        data["settings"]["cooltime"][1] = self.inputCooltime
        data["settings"]["startKey"][0] = self.activeStartKeySlot
        data["settings"]["startKey"][1] = self.inputStartKey
        data["settings"]["mouseClickType"] = self.activeMouseClickSlot

        for i in range(8):
            data["usageSettings"][i][0] = self.ifUseSkill[i]
            data["usageSettings"][i][1] = self.ifUseSole[i]
            data["usageSettings"][i][2] = self.comboCount[i]
            data["usageSettings"][i][3] = self.skillPriority[i]

        data["linkSettings"] = []
        for i in range(len(self.linkSkillList)):
            data["linkSettings"].append({})
            data["linkSettings"][i]["type"] = self.linkSkillList[i][0]
            data["linkSettings"][i]["key"] = self.linkSkillList[i][1]
            data["linkSettings"][i]["skills"] = self.linkSkillList[i][2]

        data["info"]["stats"] = self.info_stats
        data["info"]["skills"] = self.info_skills
        data["info"]["simInfo"] = self.info_simInfo

        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f)

    ## 탭 제거시 데이터 삭제
    def dataRemove(self, num):
        with open(fileDir, "r", encoding="UTF8") as f:
            jsonObject = json.load(f)

        jsonObject["preset"].pop(num)

        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f)

    ## 탭 추가시 데이터 생성
    def dataAdd(self):
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
                    "delay": [0, self.defaultDelay],
                    "cooltime": [0, 0],
                    "startKey": [0, "F9"],
                    "mouseClickType": 0,
                },
                "usageSettings": [
                    [True, True, 3, None],
                    [True, True, 2, None],
                    [True, True, 2, None],
                    [True, True, 1, None],
                    [True, True, 3, None],
                    [True, True, 1, None],
                    [True, True, 1, None],
                    [True, True, 3, None],
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
            json.dump(jsonObject, f)

    ## 데이터 업데이트
    def dataUpdate(self):
        def update_1to2():
            jsonObject["version"] = 2

            for i in range(len(jsonObject["preset"])):
                jsonObject["preset"][i]["info"] = {}
                jsonObject["preset"][i]["info"]["stats"] = [0] * 18
                jsonObject["preset"][i]["info"]["skills"] = [1] * 8
                jsonObject["preset"][i]["info"]["simInfo"] = [1, 1, 100]

        with open(fileDir, "r", encoding="UTF8") as f:
            jsonObject = json.load(f)

        if not "version" in jsonObject:
            update_1to2()
        # if jsonObject["version"] == 2:
        #     update_2to3()

        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f)


class DpsDistributionCanvas(FigureCanvas):

    def __init__(self, parent, data):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)
        self.data = data
        self.plot()

    def plot(self):
        self.colors = {
            "median": "#4070FF",
            "center5": "#75A2FC",
            "cursor": "#BAD0FD",
            "normal": "#F38181",
        }

        n_bins = 15
        counts, bins = self.custom_histogram(self.data, n_bins)
        bin_width = 0.9 * (bins[1] - bins[0])
        bars = self.ax.bar(bins[:-1], counts, width=bin_width, align="edge", bottom=0)

        # Customizing the plot similar to the image
        self.ax.set_title("DPS 분포")
        self.ax.yaxis.set_major_locator(mtick.MaxNLocator(integer=True))
        # self.ax.set_xlabel("DPS")
        # self.ax.set_ylabel("반복 횟수")

        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)

        self.ax.set_facecolor("#F8F8F8")
        self.fig.set_facecolor("#F8F8F8")

        # Change colors of the bars
        for bar in bars:
            bar.set_facecolor(self.colors["normal"])

        # Center 5 bars
        center_start = len(bars) // 2 - 2
        for i in range(center_start, center_start + 5):
            bars[i].set_facecolor(self.colors["center5"])

        # Highest bar
        median_idx = self.find_median_index(self.data, bins)
        bars[median_idx].set_facecolor(self.colors["median"])

        # Create the annotation
        annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(-24, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1),
            # arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        )
        annotation.set_visible(False)

        def on_hover(event):
            # Check if the cursor is in the plot area
            if event.inaxes == self.ax:
                for bar in bars:
                    bar.set_facecolor(self.colors["normal"])
                for i in range(center_start, center_start + 5):
                    bars[i].set_facecolor(self.colors["center5"])
                bars[median_idx].set_facecolor(self.colors["median"])

                # Find the bar under the cursor
                for i, bar in enumerate(bars):
                    if bar.contains(event)[0]:
                        bar.set_facecolor(self.colors["cursor"])
                        bin_val = bins[i]
                        count_val = counts[i]
                        annotation.xy = (event.xdata, event.ydata)
                        annotation.set_text(
                            f"상한 {bin_val + (bins[1]-bins[0]):.1f}\n하한 {bin_val:.1f}\n횟수 {int(count_val)}"
                        )
                        if not annotation._visible:
                            annotation.set_visible(True)
                        self.draw()
                        break
                else:
                    if annotation._visible:
                        annotation.set_visible(False)
                        for bar in bars:
                            bar.set_facecolor(self.colors["normal"])
                        for i in range(center_start, center_start + 5):
                            bars[i].set_facecolor(self.colors["center5"])
                        bars[median_idx].set_facecolor(self.colors["median"])
                        self.draw()
            else:
                if annotation._visible:
                    annotation.set_visible(False)
                    for bar in bars:
                        bar.set_facecolor(self.colors["normal"])
                    for i in range(center_start, center_start + 5):
                        bars[i].set_facecolor(self.colors["center5"])
                    bars[median_idx].set_facecolor(self.colors["median"])
                    self.draw()

        self.mpl_connect("motion_notify_event", on_hover)
        self.draw()

    def calculate_median(self, data):
        """
        Calculate the median of a list of numbers without using numpy.
        """
        sorted_data = sorted(data)
        n = len(sorted_data)

        if n % 2 == 1:  # Odd number of elements
            return sorted_data[n // 2]
        else:  # Even number of elements
            mid1, mid2 = sorted_data[n // 2 - 1], sorted_data[n // 2]
            return (mid1 + mid2) / 2

    def custom_digitize(self, value, bins):
        """
        Find the index of the bin into which the value falls.
        Equivalent to numpy.digitize.
        """
        for idx, b in enumerate(bins):
            if value <= b:
                return idx
        return len(bins)

    def find_median_index(self, data, bins):
        """
        Find the index of the bin where the median of data falls.
        """
        median_val = self.calculate_median(data)
        median_idx = self.custom_digitize(median_val, bins) - 1
        return median_idx

    def custom_histogram(self, data, n_bins):
        """
        Create a histogram with specified number of bins without using numpy.
        """
        min_val, max_val = min(data), max(data)
        bin_width = (max_val - min_val) / n_bins
        bins = [min_val + i * bin_width for i in range(n_bins + 1)]
        counts = [0] * n_bins

        for value in data:
            for i in range(n_bins):
                if bins[i] <= value < bins[i + 1]:
                    counts[i] += 1
                    break
            if value == max_val:  # Include the rightmost edge
                counts[-1] += 1

        return counts, bins


class SkillDpsDistributionCanvas(FigureCanvas):

    def __init__(self, parent, data, skill_name):
        fig, self.ax = plt.subplots()
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)
        self.data = data
        self.skill_name = skill_name
        self.plot()

    def plot(self):
        # Data for the pie chart
        data = [i for i in self.data if i != 0]
        labels = [f"{self.skill_name[i]}" for i, j in enumerate(self.data) if j != 0 and i != 6]
        labels.append(f"평타")
        colors = ["#EF9A9A", "#90CAF9", "#A5D6A7", "#FFEB3B", "#CE93D8", "#F0B070", "#2196F3"]

        # Plotting the pie chart
        wedges, texts, autotexts = self.ax.pie(
            data,
            labels=labels,
            colors=colors[: len(labels)],
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={"width": 0.7, "edgecolor": "#F8F8F8", "linewidth": 2},
            # textprops={"verticalalignment": "center"},
            pctdistance=0.65,
        )

        # Customizing the plot
        self.ax.set_title("스킬 DPS", fontsize=14)

        # Adjust text size
        for text in texts:
            text.set_fontsize(10)

        self.draw()


class DMGCanvas(FigureCanvas):

    def __init__(self, parent, data, canvas_type):
        fig, self.ax = plt.subplots()
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)
        self.data = data
        self.canvas_type = canvas_type
        self.plot()

    def plot(self):
        (self.line1,) = self.ax.plot(
            self.data["time"],
            self.data["max"],
            label="최대",
            color="#F38181",
            linewidth=1,
        )
        (self.line2,) = self.ax.plot(
            self.data["time"],
            self.data["mean"],
            label="평균",
            color="#70AAF9",
            linewidth=1,
        )
        (self.line3,) = self.ax.plot(
            self.data["time"],
            self.data["min"],
            label="최소",
            color="#80C080",
            linewidth=1,
        )

        if self.canvas_type == "time":
            self.ax.set_title("시간 경과에 따른 피해량")
            # self.ax.set_ylabel("피해량", rotation=0, labelpad=20)
        else:
            self.ax.set_title("누적 피해량")
            # self.ax.set_ylabel("피해량", rotation=0, labelpad=20)

        self.ax.set_xlabel("시간 (초)")
        self.ax.grid(True, linestyle="--")  # 격자를 점선으로 변경
        self.ax.set_ylim(bottom=0)  # y축 범위를 0부터 시작하도록 설정
        self.ax.set_xlim(left=0, right=60)  # x축 범위를 0부터 시작하도록 설정
        self.ax.legend()

        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)

        self.ax.set_facecolor("#F8F8F8")

        # Interactive annotations
        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(-24, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1),
        )
        self.annotation.set_visible(False)

        # Connect the hover event
        self.mpl_connect("motion_notify_event", self.on_hover)

    def on_hover(self, event):
        if event.inaxes == self.ax:
            x, y = event.xdata, event.ydata
            index = abs(self.data["time"] - x).argmin()
            closest_x = self.data["time"][index]
            max_val = self.data["max"][index]
            mean_val = self.data["mean"][index]
            min_val = self.data["min"][index]

            self.annotation.xy = (x, y)
            self.annotation.set_text(
                f"시간: {closest_x:.1f}\n최대: {max_val:.1f}\n평균: {mean_val:.1f}\n최소: {min_val:.1f}"
            )
            self.annotation.set_visible(True)
            self.draw_idle()
        else:
            self.annotation.set_visible(False)
            self.draw_idle()


class SkillContributionCanvas(FigureCanvas):

    def __init__(self, parent, data, names):
        fig, self.ax = plt.subplots(figsize=(8, 6))  # 명시적 크기 설정
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)

        # 캔버스 크기 설정
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        self.data = data
        self.skill_names = names

        self.plot()

    def plot(self):
        colors = ["#EF9A9A", "#90CAF9", "#A5D6A7", "#FFEB3B", "#CE93D8", "#F0B070", "#2196F3"]

        data_normLast = [i[-1] for i in self.data["skills_normalized"]]
        data_0idx = [i for i, j in enumerate(data_normLast) if j == 0]
        data_0idx.sort(reverse=True)

        for i in data_0idx:
            self.data["skills_normalized"].pop(i)
            self.data["skills_sum"].pop(i)
            self.skill_names.pop(i)
        self.skill_names.append("평타")

        self.skillCount = len(self.data["skills_normalized"])
        self.lines = []
        for i in reversed(range(self.skillCount)):
            (line,) = self.ax.plot(
                self.data["time"],
                self.data["skills_sum"][i],
                label=self.skill_names[i],
                color=colors[i],
                linewidth=2,
            )
            self.lines.append(line)

        # 영역 채우기
        for i in range(1, self.skillCount):
            self.ax.fill_between(
                self.data["time"],
                self.data["skills_sum"][i - 1],
                self.data["skills_sum"][i],
                color=colors[i],
            )  # 바로 위 선의 색상 사용

        # 맨 아래 영역 채우기
        self.ax.fill_between(self.data["time"], 0, self.data["skills_sum"][0], color=colors[0])

        self.ax.set_title("스킬별 기여도")
        self.ax.set_xlabel("시간 (초)")
        self.ax.grid(True, linestyle="--")
        self.ax.set_ylim(0, 1)  # y축 범위를 0부터 1로 설정
        self.ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        self.ax.set_xlim(left=0, right=60)  # x축 범위를 0부터 60으로 설정
        self.ax.legend()

        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)

        self.ax.set_facecolor("#F8F8F8")

        # Interactive annotations
        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(-24, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1),
        )
        self.annotation.set_visible(False)

        # Connect the hover event
        self.mpl_connect("motion_notify_event", self.on_hover)

    def on_hover(self, event):
        if event.inaxes == self.ax:
            x, y = event.xdata, event.ydata
            index = abs(self.data["time"] - x).argmin()
            closest_x = self.data["time"][index]

            values = []
            for i in reversed(range(self.skillCount)):
                values.append(f"{self.skill_names[i]}: {self.data["skills_normalized"][i][index] * 100:.1f}%")

            self.annotation.xy = (x, y)
            self.annotation.set_text(f"시간: {closest_x:.1f}\n\n" + "\n".join(values))
            self.annotation.set_visible(True)
            self.draw_idle()
        else:
            self.annotation.set_visible(False)
            self.draw_idle()


if __name__ == "__main__":
    version = "v3.1.0-alpha"
    dataVersion = 2
    fileDir = "C:\\PDFiles\\PDSkillMacro.json"
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
