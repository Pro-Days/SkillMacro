from .utils.data_manager import *
from .utils.version_checker import *
from .shared_data import SharedData
from .utils.set_font import *
from .utils.run_macro import *
from .utils.graph import *
from .utils.get_character_data import *
from .utils.misc import *
from .utils.simulate_macro import *

import os
import sys
import copy
import random
import requests

from threading import Thread
from webbrowser import open_new
from functools import partial

import matplotlib.pyplot as plt

from PyQt6.QtCore import QSize, Qt, QThread, QTimer, pyqtSlot
from PyQt6.QtGui import (
    QPen,
    QFont,
    QIcon,
    QColor,
    QPixmap,
    QPainter,
    QPalette,
    QTransform,
    QFontMetrics,
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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        set_default_fonts()
        self.shared_data = SharedData()
        self.setWindowIcon(QIcon(QPixmap(convertResourcePath("resources\\image\\icon.ico"))))

        dataUpdate()
        dataLoad(self.shared_data)

        self.initUI()

        self.checkVersion()
        self.activateThread()

    ## 서브 쓰레드 실행
    def activateThread(self):
        Thread(target=check_kb_pressed, args=[self.shared_data], daemon=True).start()

        self.previewTimer = QTimer(self)
        self.previewTimer.singleShot(16, self.tick)

    def changeLayout(self, num):
        self.windowLayout.setCurrentIndex(num)
        self.shared_data.layout_type = num

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
        pixmap = QPixmap(convertResourcePath("resources\\image\\x.png"))
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
        if self.shared_data.sim_type == 3:
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
        self.shared_data.sim_type = 0
        plt.close("all")

    def makeSimulType4(self):
        if not (self.sim_stat_inputCheck and self.sim_skill_inputCheck and self.sim_simInfo_inputCheck):
            self.makeNoticePopup("SimInputError")
            return

        self.removeSimulWidgets()
        self.sim_updateNavButton(3)

        self.shared_data.sim_type = 4

        self.sim_card_updated = False

        self.sim_powers = simulateMacro(
            self.shared_data,
            tuple(self.shared_data.info_stats),
            tuple(self.shared_data.info_skills),
            tuple(self.shared_data.info_simInfo),
            1,
        )
        # self.sim_powers = [str(int(i)) for i in self.sim_powers]

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
        if not (self.sim_stat_inputCheck and self.sim_skill_inputCheck and self.sim_simInfo_inputCheck):
            self.makeNoticePopup("SimInputError")
            return

        self.removeSimulWidgets()
        self.sim_updateNavButton(2)

        self.shared_data.sim_type = 3

        # print(self.shared_data.info_simInfo)
        self.sim_powers = simulateMacro(
            self.shared_data,
            tuple(self.shared_data.info_stats),
            tuple(self.shared_data.info_skills),
            tuple(self.shared_data.info_simInfo),
            1,
        )
        # self.sim_powers = [str(int(i)) for i in self.sim_powers]

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
                image: url({convertResourcePath("resources\\image\\down_arrow.png").replace("\\", "/")});
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
        self.sim_efficiency_statL.addItems(self.shared_data.STAT_LIST)
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
        pixmap = QPixmap(convertResourcePath("resources\\image\\lineArrow.png"))
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
        self.sim_efficiency_statR.addItems(self.shared_data.STAT_LIST)
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

            self.sim_skill_inputs[i].setText(str(self.shared_data.info_skills[i]))

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
        self.sim_potential_stat0.addItems(self.shared_data.POTENTIAL_STAT_LIST.keys())
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
        self.sim_potential_stat1.addItems(self.shared_data.POTENTIAL_STAT_LIST.keys())
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
        self.sim_potential_stat2.addItems(self.shared_data.POTENTIAL_STAT_LIST.keys())
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
        for key, (num, value) in self.shared_data.POTENTIAL_STAT_LIST.items():
            stats = self.shared_data.info_stats.copy()
            stats[num] += value

            powers = simulateMacro(
                self.shared_data,
                tuple(stats),
                tuple(self.shared_data.info_skills),
                tuple(self.shared_data.info_simInfo),
                1,
            )
            diff_powers = [round(powers[i] - self.sim_powers[i], 5) for i in range(4)]

            for i in range(4):
                texts[i].append([key, diff_powers[i]])

        [texts[i].sort(key=lambda x: x[1], reverse=True) for i in range(4)]
        for i in range(4):
            for j in range(len(self.shared_data.POTENTIAL_STAT_LIST)):
                if texts[i][j][1] == 0:
                    texts[i][j] = ["", "", ""]
                else:
                    texts[i][j][1] = f"+{round(texts[i][j][1])}"
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

        self.shared_data.sim_type = 2

        self.sim_powers, analysis, resultDet, results = simulateMacro(
            self.shared_data,
            tuple(self.shared_data.info_stats),
            tuple(self.shared_data.info_skills),
            tuple(self.shared_data.info_simInfo),
            random.random(),
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
                names.append(
                    self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][
                        self.shared_data.selectedSkillList[i]
                    ]
                )
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
                names.append(
                    self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][
                        self.shared_data.selectedSkillList[i]
                    ]
                )
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

        self.shared_data.sim_type = 1

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

            self.sim_stat_inputs[i].setText(str(self.shared_data.info_stats[i]))

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

            self.sim_skill_inputs[i].setText(str(self.shared_data.info_skills[i]))

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

            self.sim_simInfo_inputs[i].setText(str(self.shared_data.info_simInfo[i]))

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
            data = get_character_info(self.sim4_info_nicknameInput.text())
        except:
            self.makeNoticePopup("SimCharLoadError")
            return

        for i, j in enumerate(data):
            job, level = j["job"], j["level"]
            if job == self.shared_data.jobID:
                self.sim4_info_charButtonList[i].setText(
                    f"{self.shared_data.JOB_LIST[self.shared_data.serverID][job]} | Lv.{level}"
                )
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
                self.sim4_info_charButtonList[i].setText(
                    f"{self.shared_data.JOB_LIST[self.shared_data.serverID][job]} | Lv.{level}"
                )
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
            name, url = get_character_card_data(name)
        except:
            self.makeNoticePopup("SimCardError")
            return

        pixmap = QPixmap(convertResourcePath("resources\\image\\card_bg.png"))
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
        self.sim4_card_job.setText(
            self.shared_data.JOB_LIST[self.shared_data.serverID][self.shared_data.jobID]
        )
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
                self.sim4_card_powers[i][2].setText(f"{int(self.sim_powers[i])}")

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

        stats = self.shared_data.info_stats.copy()
        for i in range(3):
            num, value = self.shared_data.POTENTIAL_STAT_LIST[indexList[i]]
            stats[num] += value

        powers = simulateMacro(
            self.shared_data,
            tuple(stats),
            tuple(self.shared_data.info_skills),
            tuple(self.shared_data.info_simInfo),
            1,
        )

        diff_powers = [round(powers[i] - self.sim_powers[i]) for i in range(4)]

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

        stats = self.shared_data.info_stats.copy()
        stats[self.sim_efficiency_statL.currentIndex()] += int(self.sim_efficiency_statInput.text())
        powers = simulateMacro(
            self.shared_data,
            tuple(stats),
            tuple(self.shared_data.info_skills),
            tuple(self.shared_data.info_simInfo),
            1,
        )
        reqStats = getRequiredStat(self.shared_data, powers, self.sim_efficiency_statR.currentIndex())

        [self.sim_efficiency_power_list[i][2].setText(reqStats[i]) for i in range(4)]

    def sim_efficiency_Changed(self):
        text = self.sim_efficiency_statInput.text()
        index = self.sim_efficiency_statL.currentIndex()
        if not text.isdigit():
            [self.sim_efficiency_power_list[i][2].setText("오류") for i in range(4)]
            return

        stat = self.shared_data.info_stats[self.sim_efficiency_statL.currentIndex()] + int(text)

        if self.shared_data.STAT_RANGE_LIST[index][0] <= stat:
            if self.shared_data.STAT_RANGE_LIST[index][1] == None:
                self.sim_update_efficiency()
                return
            else:
                if stat <= self.shared_data.STAT_RANGE_LIST[index][1]:
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

            self.shared_data.info_simInfo = [int(i.text()) for i in self.sim_simInfo_inputs]
            dataSave(self.shared_data)
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
        texts = self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID]

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

            if self.shared_data.sim_type == 1:
                self.shared_data.info_skills = [int(i.text()) for i in self.sim_skill_inputs]
                dataSave(self.shared_data)
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

        if self.shared_data.sim_type == 3:
            self.update_additional_power_list()

    def update_additional_power_list(self):
        if self.sim_skill_inputCheck and self.sim_stat_inputCheck:
            stats = self.shared_data.info_stats.copy()
            stats = [stats[i] + int(self.sim_stat_inputs[i].text()) for i in range(len(stats))]
            skills = self.shared_data.info_skills.copy()
            skills = [skills[i] + int(self.sim_skill_inputs[i].text()) for i in range(len(skills))]

            powers = simulateMacro(
                self.shared_data, tuple(stats), tuple(skills), tuple(self.shared_data.info_simInfo), 1
            )

            diff_powers = [powers[i] - self.sim_powers[i] for i in range(4)]

            [
                self.sim_additional_power_list[i][2].setText(
                    f"{int(powers[i]):}\n({round(diff_powers[i]):+}, {round(diff_powers[i] / self.sim_powers[i] * 100, 2):+.1f}%)"
                )
                for i in range(4)
            ]
        else:
            [self.sim_additional_power_list[i][2].setText("오류") for i in range(4)]

    def sim_makeStatInput(self, mainframe):
        self.sim_stat_frames = []
        self.sim_stat_labels = []
        self.sim_stat_inputs = []
        for i in range(len(self.shared_data.STAT_LIST)):
            frame = QFrame(mainframe)
            frame.setStyleSheet("QFrame { background-color: transparent; border: 0px solid; }")
            self.sim_stat_frames.append(frame)

            label = QLabel(self.shared_data.STAT_LIST[i], frame)
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
            if self.shared_data.sim_type == 1:
                if not text.isdigit():
                    return False

                if self.shared_data.STAT_RANGE_LIST[num][0] <= int(text):
                    if self.shared_data.STAT_RANGE_LIST[num][1] == None:
                        return True
                    else:
                        if int(text) <= self.shared_data.STAT_RANGE_LIST[num][1]:
                            return True
                        return False
                return False
            else:  # self.simType == 3
                try:
                    value = int(text)
                except ValueError:
                    return False

                stat = self.shared_data.info_stats[num] + value
                if self.shared_data.STAT_RANGE_LIST[num][0] <= stat:
                    if self.shared_data.STAT_RANGE_LIST[num][1] == None:
                        return True
                    else:
                        if stat <= self.shared_data.STAT_RANGE_LIST[num][1]:
                            return True
                        return False
                return False

        if not False in [checkInput(i, j.text()) for i, j in enumerate(self.sim_stat_inputs)]:  # 모두 digit
            for i in self.sim_stat_inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            if self.shared_data.sim_type == 1:
                self.shared_data.info_stats = [int(i.text()) for i in self.sim_stat_inputs]
                dataSave(self.shared_data)
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

        if self.shared_data.sim_type == 3:
            self.update_additional_power_list()

    def keyPressEvent(self, e):  # 키가 눌러졌을 때 실행됨

        # ESC
        if e.key() == Qt.Key.Key_Escape:
            if self.shared_data.is_tab_remove_popup_activated:
                self.onTabRemovePopupClick(0, False)
            elif self.shared_data.active_error_popup_count >= 1:
                self.removeNoticePopup()
            elif self.shared_data.active_popup != "":
                self.disablePopup()

        # Ctrl
        elif e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if e.key() == Qt.Key.Key_W and not self.shared_data.is_tab_remove_popup_activated:
                self.onTabRemoveClick(self.shared_data.recentPreset)

        # Enter
        elif e.key() == Qt.Key.Key_Return:
            if self.shared_data.is_tab_remove_popup_activated:
                self.onTabRemovePopupClick(self.shared_data.recentPreset)
            elif self.shared_data.active_popup == "settingDelay":
                self.onInputPopupClick("delay")
            elif self.shared_data.active_popup == "settingCooltime":
                self.onInputPopupClick("cooltime")
            elif self.shared_data.active_popup == "changeTabName":
                self.onInputPopupClick(("tabName", self.shared_data.recentPreset))

        # # Temp
        # elif e.key() == Qt.Key.Key_L:
        #     print(self.getSimulatedSKillList())

    def checkVersion(self):
        """
        버전 확인
        """

        self.worker = VersionChecker()

        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.start()
        self.worker.versionChecked.connect(self.onVersionChecked)

        self.delayTimer = QTimer()
        self.delayTimer.setSingleShot(True)
        self.delayTimer.timeout.connect(self.worker.checkVersion)
        self.delayTimer.start(1000)

    @pyqtSlot(str)
    def onVersionChecked(self, recentVersion):
        """
        버전이 확인 되었을 때 실행
        """

        if recentVersion == "FailedUpdateCheck":
            self.makeNoticePopup("FailedUpdateCheck")
        elif recentVersion != self.shared_data.VERSION:
            self.recentVersion = recentVersion
            self.update_url = self.worker.updateUrl
            self.makeNoticePopup("RequireUpdate")

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

    ## 프로그램 초기 UI 설정
    def initUI(self):
        self.setWindowTitle("데이즈 스킬매크로 " + self.shared_data.VERSION)
        self.setMinimumSize(self.shared_data.DEFAULT_WINDOW_WIDTH, self.shared_data.DEFAULT_WINDOW_HEIGHT)
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
        for tabNum in range(len(self.shared_data.tabNames)):
            tabBackground = QLabel("", self.page1)
            if tabNum == self.shared_data.recentPreset:
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
            tabButton.setText(self.limitText(f" {self.shared_data.tabNames[tabNum]}", tabButton))
            tabButton.clicked.connect(partial(lambda x: self.onTabClick(x), tabNum))
            if tabNum == self.shared_data.recentPreset:
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
            if tabNum == self.shared_data.recentPreset:
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
            pixmap = QPixmap(convertResourcePath("resources\\image\\x.png"))
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
        pixmap = QPixmap(convertResourcePath("resources\\image\\plus.png"))
        self.tabAddButton.setIcon(QIcon(pixmap))
        self.tabAddButton.setFixedSize(40, 40)
        self.tabAddButton.move(370 + 250 * len(self.shared_data.tabNames), 25)

        self.shared_data.layout_type = 0

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

            label = QLabel(
                self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][i], j
            )
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
            if self.shared_data.selectedSkillList[i] != -1:
                pixmap = QPixmap(self.getSkillImage(self.shared_data.selectedSkillList[i]))
            else:
                pixmap = QPixmap(convertResourcePath("resources\\image\\emptySkill.png"))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(64, 64))
            button.show()
            self.selectedSkillImageButton.append(button)

            button = QPushButton(self.shared_data.skillKeys[i], j)
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
        self.shared_data.is_skill_selecting = -1
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
        # print(self.shared_data.selectedSkillList[num])
        if self.shared_data.setting_type == 3:
            self.cancelSkillSelection()
            self.makeNoticePopup("editingLinkSkill")
            return
        if self.shared_data.is_activated:
            self.cancelSkillSelection()
            self.makeNoticePopup("MacroIsRunning")
            return
        if self.shared_data.is_skill_selecting == num:
            pixmap = QPixmap(convertResourcePath("resources\\image\\emptySkill.png"))
            self.selectedSkillImageButton[num].setIcon(QIcon(pixmap))

            for i, j in enumerate(self.shared_data.linkSkillList):
                for k in j["skills"]:
                    if k[0] == self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting]:
                        self.shared_data.linkSkillList[i]["useType"] = 1

            if self.shared_data.setting_type == 2:
                self.removeSetting2()
                self.shared_data.setting_type = -1
                self.changeSettingTo2()

            self.shared_data.skillPriority[self.shared_data.selectedSkillList[num]] = None
            for i in range(1, 7):
                if not (i in self.shared_data.skillPriority):
                    for j, k in enumerate(self.shared_data.skillPriority):
                        if not (k == None):
                            if k > i:
                                self.shared_data.skillPriority[j] -= 1
                                if self.shared_data.setting_type == 1:
                                    self.settingSkillSequences[j].setText(str(k - 1))
            if self.shared_data.setting_type == 1 and self.shared_data.selectedSkillList[num] != -1:
                pixmap = QPixmap(self.getSkillImage(self.shared_data.selectedSkillList[num], "off"))
                self.settingSkillImages[self.shared_data.selectedSkillList[num]].setIcon(QIcon(pixmap))
                self.settingSkillSequences[self.shared_data.selectedSkillList[num]].setText("-")
                # print(self.shared_data.selectedSkillList)

            self.shared_data.selectedSkillList[num] = -1
            self.cancelSkillSelection()
            dataSave(self.shared_data)
            return

        self.shared_data.is_skill_selecting = num

        for i in range(6):
            self.selectedSkillImageButton[i].setStyleSheet(
                f"QPushButton {{ background-color: {self.selectedSkillColors[i]}; border-radius :10px; }}"
            )

        self.selectedSkillImageButton[num].setStyleSheet(
            f"QPushButton {{ background-color: {self.selectedSkillColors[num]}; border-radius :10px; border: 4px solid red; }}"
        )
        for i in range(8):
            if not (i in self.shared_data.selectedSkillList):
                self.selectableSkillImageButton[i].setStyleSheet(
                    "QPushButton { background-color: #bbbbbb; border-radius :10px; border: 4px solid #00b000; }"
                )

    ## 상단 스킬 아이콘 클릭 (8개)
    def onSelectableSkillClick(self, num):
        if self.shared_data.setting_type == 3:
            self.cancelSkillSelection()
            return
        self.selectedSkillImageButton[self.shared_data.is_skill_selecting].setStyleSheet(
            f"QPushButton {{ background-color: {self.selectedSkillColors[self.shared_data.is_skill_selecting]}; border-radius :10px; }}"
        )
        for i in range(8):
            self.selectableSkillImageButton[i].setStyleSheet(
                "QPushButton { background-color: #bbbbbb; border-radius :10px; }"
            )
        if self.shared_data.is_skill_selecting == -1:  # 스킬 선택중이 아닐 때
            return
        elif num in self.shared_data.selectedSkillList:  # 이미 선택된 스킬을 선택했을 때
            self.shared_data.is_skill_selecting = -1
            return

        if self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting] != -1:
            if self.shared_data.setting_type == 1:
                pixmap = QPixmap(
                    self.getSkillImage(
                        self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting], "off"
                    )
                )
                self.settingSkillImages[
                    self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting]
                ].setIcon(QIcon(pixmap))
                self.settingSkillSequences[
                    self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting]
                ].setText("-")

            for i, j in enumerate(self.shared_data.linkSkillList):
                for k in j["skills"]:
                    if k[0] == self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting]:
                        self.shared_data.linkSkillList[i]["useType"] = 1

        self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting] = num

        self.shared_data.skillPriority[
            self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting]
        ] = None
        for i in range(1, 7):
            if not (i in self.shared_data.skillPriority):
                for j, k in enumerate(self.shared_data.skillPriority):
                    if not (k == None):
                        if k > i:
                            self.shared_data.skillPriority[j] -= 1
                            if self.shared_data.setting_type == 1:
                                self.settingSkillSequences[j].setText(str(k - 1))

        self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting] = num
        pixmap = QPixmap(self.getSkillImage(num))
        self.selectedSkillImageButton[self.shared_data.is_skill_selecting].setIcon(QIcon(pixmap))

        if self.shared_data.setting_type == 1:
            pixmap = QPixmap(self.getSkillImage(num))
            self.settingSkillImages[num].setIcon(QIcon(pixmap))

        self.shared_data.is_skill_selecting = -1
        dataSave(self.shared_data)

    def tick(self):
        self.previewTimer.singleShot(100, self.tick)
        self.showSkillPreview()

    ## 스킬 미리보기 프레임에 스킬 아이콘 설정
    def showSkillPreview(self):
        if not self.shared_data.is_activated:
            initMacro(self.shared_data)
            addTaskList(self.shared_data)
            # self.printMacroInfo(True)
            # print(self.shared_data.taskList)

        for i in self.shared_data.skill_preview_list:
            i.deleteLater()
        self.shared_data.skill_preview_list = []

        fwidth = self.skillPreviewFrame.width()
        width = round(self.skillPreviewFrame.width() * 0.166667)
        height = self.skillPreviewFrame.height()

        count = min(len(self.shared_data.taskList), 6)
        for i in range(count):
            skill = QPushButton("", self.skillPreviewFrame)
            # self.tabAddButton.clicked.connect(self.onTabAddClick)
            skill.setStyleSheet("background-color: transparent;")
            if not self.shared_data.is_activated:
                pixmap = QPixmap(
                    self.getSkillImage(
                        self.shared_data.selectedSkillList[self.shared_data.taskList[i][0]], "off"
                    )
                )
            else:
                pixmap = QPixmap(
                    self.getSkillImage(self.shared_data.selectedSkillList[self.shared_data.taskList[i][0]], 1)
                )
            skill.setIcon(QIcon(pixmap))
            skill.setIconSize(QSize(min(width, height), min(width, height)))
            skill.setFixedSize(width, height)
            skill.move(round((fwidth - width * count) * 0.5) + width * i, 0)
            skill.show()

            self.shared_data.skill_preview_list.append(skill)

    ## 사이드바 설정 종류 아이콘 버튼 생성
    def getSidebarButton(self, num):
        button = QPushButton("", self.sidebarOptionFrame)
        match num:
            case 0:
                button.clicked.connect(self.changeSettingTo0)
                pixmap = QPixmap(convertResourcePath("resources\\image\\setting.png"))
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
                pixmap = QPixmap(convertResourcePath("resources\\image\\usageSetting.png"))
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
                pixmap = QPixmap(convertResourcePath("resources\\image\\linkSetting.png"))
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
                pixmap = QPixmap(convertResourcePath("resources\\image\\simulationSidebar.png"))
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
        self.ButtonLinkKey0.deleteLater()
        self.ButtonLinkKey1.deleteLater()
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

        match self.shared_data.setting_type:
            case 0:
                return
            case 1:
                self.removeSetting1()
            case 2:
                self.removeSetting2()
            case 3:
                self.removeSetting3()

        self.shared_data.setting_type = 0

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
            self.shared_data.SERVER_LIST[self.shared_data.serverID], 40, 200, self.onServerClick
        )
        self.buttonJobList = self.getSettingButton(
            self.shared_data.JOB_LIST[self.shared_data.serverID][self.shared_data.jobID],
            160,
            200,
            self.onJobClick,
        )

        # 딜레이
        self.labelDelay = self.getSettingName("딜레이", 60, 150 + 130)
        self.labelDelay.setToolTip(
            "스킬을 사용하기 위한 키보드 입력, 마우스 클릭과 같은 동작 사이의 간격을 설정합니다.\n단위는 밀리초(millisecond, 0.001초)를 사용합니다.\n입력 가능한 딜레이의 범위는 50~1000입니다.\n딜레이를 계속해서 조절하며 1분간 매크로를 실행했을 때 놓치는 스킬이 없도록 설정해주세요."
        )
        if self.shared_data.activeDelaySlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultDelay = self.getSettingCheck(
            "기본: 150",
            40,
            200 + 130,
            self.onDefaultDelayClick,
            disable=temp[0],
        )
        self.buttonInputDelay = self.getSettingCheck(
            str(self.shared_data.inputDelay),
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
        if self.shared_data.activeCooltimeSlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultCooltime = self.getSettingCheck(
            "기본: 0", 40, 200 + 130 * 2, self.onDefaultCooltimeClick, disable=temp[0]
        )
        self.buttonInputCooltime = self.getSettingCheck(
            str(self.shared_data.inputCooltime),
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
        if self.shared_data.activeStartKeySlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultStartKey = self.getSettingCheck(
            "기본: F9", 40, 200 + 130 * 3, self.onDefaultStartKeyClick, disable=temp[0]
        )
        self.buttonInputStartKey = self.getSettingCheck(
            str(self.shared_data.inputStartKey),
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
        if self.shared_data.activeMouseClickSlot == 0:
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

        match self.shared_data.setting_type:
            case 0:
                self.removeSetting0()
            case 1:
                return
            case 2:
                self.removeSetting2()
            case 3:
                self.removeSetting3()

        self.shared_data.setting_type = 1

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
            if i in self.shared_data.selectedSkillList:
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
            if self.shared_data.ifUseSkill[i]:
                pixmap = QPixmap(convertResourcePath("resources\\image\\checkTrue.png"))
            else:
                pixmap = QPixmap(convertResourcePath("resources\\image\\checkFalse.png"))
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
            if self.shared_data.ifUseSole[i]:
                pixmap = QPixmap(convertResourcePath("resources\\image\\checkTrue.png"))
            else:
                pixmap = QPixmap(convertResourcePath("resources\\image\\checkFalse.png"))
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
                f"{self.shared_data.comboCount[i]} / {self.shared_data.SKILL_COMBO_COUNT_LIST[self.shared_data.serverID][self.shared_data.jobID][i]}",
                self.sidebarFrame,
            )
            button.clicked.connect(partial(lambda x: self.onSkillComboCountsClick(x), i))
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.setFixedSize(46, 32)
            button.move(177, 210 + 51 * i)
            button.show()
            self.settingSkillComboCounts.append(button)

            txt = "-" if self.shared_data.skillPriority[i] == None else str(self.shared_data.skillPriority[i])
            button = QPushButton(txt, self.sidebarFrame)
            button.clicked.connect(partial(lambda x: self.onSkillSequencesClick(x), i))
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.setFixedSize(46, 32)
            button.move(227, 210 + 51 * i)
            button.show()
            self.settingSkillSequences.append(button)

    ## 사이드바 타입 -> 연계설정 스킬 목록으로 변경
    def changeSettingTo2(self):
        self.disablePopup()

        match self.shared_data.setting_type:
            case 0:
                self.removeSetting0()
            case 1:
                self.removeSetting1()
            case 2:
                return
            case 3:
                self.removeSetting3()

        self.shared_data.setting_type = 2

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
        self.sidebarFrame.setFixedSize(300, 220 + 51 * len(self.shared_data.linkSkillList))

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
        for i, j in enumerate(self.shared_data.linkSkillList):
            line = QFrame(self.sidebarFrame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(264, 1)
            line.move(18, 251 + 51 * i)
            line.show()
            self.settingLines.append(line)

            am_dp = QFrame(self.sidebarFrame)  # auto, manual 표시 프레임
            if j["useType"]:
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

            imageCount = min(len(j["skills"]), 12)
            if imageCount <= 3:
                for k in range(len(j["skills"])):
                    button = QPushButton("", self.sidebarFrame)
                    pixmap = QPixmap(self.getSkillImage(j["skills"][k][0], j["skills"][k][1]))
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(48, 48))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(50, 50)
                    button.move(18 + 50 * k, 201 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)
            elif imageCount <= 6:
                for k in range(len(j["skills"])):
                    button = QPushButton("", self.sidebarFrame)
                    pixmap = QPixmap(self.getSkillImage(j["skills"][k][0], j["skills"][k][1]))
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
                    pixmap = QPixmap(self.getSkillImage(j["skills"][k][0], j["skills"][k][1]))
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(24, 24))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(25, 25)
                    button.move(18 + 25 * k, 201 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)
                for k in range(line2):
                    button = QPushButton("", self.sidebarFrame)
                    pixmap = QPixmap(self.getSkillImage(j["skills"][k + line1][0], j["skills"][k + line1][1]))
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(24, 24))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(25, 25)
                    button.move(18 + 25 * k, 226 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)

            if j["keyType"] == 0:
                text = ""
            else:
                text = j["key"]
            button = QPushButton(text, self.sidebarFrame)
            button.setStyleSheet("QPushButton { background-color: transparent; border: 0px; }")
            button.setFixedSize(50, 50)
            button.move(182, 201 + 51 * i)
            button.show()
            self.adjustFontSize(button, text, 20)
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
            pixmap = QPixmap(convertResourcePath("resources\\image\\x.png"))
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

        match self.shared_data.setting_type:
            case 0:
                self.removeSetting0()
            case 1:
                self.removeSetting1()
            case 2:
                self.removeSetting2()
            case 3:
                return

        self.shared_data.setting_type = 3
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

        self.sidebarFrame.setFixedSize(300, 390 + 51 * len(data["skills"]))

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
        if data["useType"]:
            self.ButtonLinkType0.setStyleSheet("color: #999999;")
        else:
            self.ButtonLinkType0.setStyleSheet("color: #000000;")
        self.ButtonLinkType0.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.ButtonLinkType0.setFixedSize(50, 30)
        self.ButtonLinkType0.move(155, 200)
        self.ButtonLinkType0.show()

        self.ButtonLinkType1 = QPushButton("수동", self.sidebarFrame)
        self.ButtonLinkType1.clicked.connect(lambda: self.setLinkSkillToManual(data))
        if data["useType"]:
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

        self.ButtonLinkKey0 = QPushButton("설정안함", self.sidebarFrame)
        self.ButtonLinkKey0.clicked.connect(lambda: self.setLinkSkillKey(data, 0))
        self.ButtonLinkKey0.setFixedSize(50, 30)
        self.ButtonLinkKey0.setFont(QFont("나눔스퀘어라운드 ExtraBold", 8))
        if data["keyType"] == 0:
            self.ButtonLinkKey0.setStyleSheet("color: #000000;")
        else:
            self.ButtonLinkKey0.setStyleSheet("color: #999999;")
        self.ButtonLinkKey0.move(155, 235)
        self.ButtonLinkKey0.show()

        self.ButtonLinkKey1 = QPushButton(data["key"], self.sidebarFrame)
        self.ButtonLinkKey1.clicked.connect(lambda: self.setLinkSkillKey(data, 1))
        self.ButtonLinkKey1.setFixedSize(50, 30)
        self.adjustFontSize(self.ButtonLinkKey1, data["key"], 30)
        if data["keyType"] == 0:
            self.ButtonLinkKey1.setStyleSheet("color: #999999;")
        else:
            self.ButtonLinkKey1.setStyleSheet("color: #000000;")
        self.ButtonLinkKey1.move(210, 235)
        self.ButtonLinkKey1.show()

        self.linkSkillLineA = QFrame(self.sidebarFrame)
        self.linkSkillLineA.setStyleSheet("QFrame { background-color: #b4b4b4;}")
        self.linkSkillLineA.setFixedSize(280, 1)
        self.linkSkillLineA.move(10, 274)
        self.linkSkillLineA.show()

        self.linkSkillImageList = []
        self.linkSkillCount = []
        self.linkSkillLineB = []
        self.linkSkillRemove = []
        for i, j in enumerate(data["skills"]):
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
                f"{j[1]} / {self.shared_data.SKILL_COMBO_COUNT_LIST[self.shared_data.serverID][self.shared_data.jobID][j[0]]}",
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
            pixmap = QPixmap(convertResourcePath("resources\\image\\xAlpha.png"))
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
        pixmap = QPixmap(convertResourcePath("resources\\image\\plus.png"))
        self.linkSkillPlus.setIcon(QIcon(pixmap))
        self.linkSkillPlus.setIconSize(QSize(24, 24))
        self.linkSkillPlus.setFixedSize(36, 36)
        self.linkSkillPlus.move(132, 289 + 51 * len(data["skills"]))
        self.linkSkillPlus.show()

        self.linkSkillCancelButton = QPushButton("취소", self.sidebarFrame)
        self.linkSkillCancelButton.clicked.connect(self.cancelEditingLinkSkill)
        self.linkSkillCancelButton.setFixedSize(120, 32)
        self.linkSkillCancelButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.linkSkillCancelButton.move(15, 350 + 51 * len(data["skills"]))
        self.linkSkillCancelButton.show()

        self.linkSkillSaveButton = QPushButton("저장", self.sidebarFrame)
        self.linkSkillSaveButton.clicked.connect(lambda: self.saveEditingLinkSkill(data))
        self.linkSkillSaveButton.setFixedSize(120, 32)
        self.linkSkillSaveButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.linkSkillSaveButton.move(165, 350 + 51 * len(data["skills"]))
        self.linkSkillSaveButton.show()

    ## 사이드바 타입3 새로고침
    def reloadSetting3(self, data):
        self.removeSetting3()
        self.shared_data.setting_type = -1
        self.changeSettingTo3(data)

    ## 링크스킬 종류 변경
    def editLinkSkillType(self, var):
        data, num = var

        if self.shared_data.active_popup == "editLinkSkillType":
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
                self.getSkillImage(i)
                if i in self.shared_data.selectedSkillList
                else self.getSkillImage(i, "off")
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

        if data["skills"][num][0] == i:
            return
        data["skills"][num][0] = i
        data["skills"][num][1] = 1
        data["useType"] = 1
        self.reloadSetting3(data)

    ## 링크스킬 목록에서 하나 삭제
    def removeOneLinkSkill(self, var):
        self.disablePopup()
        data, num = var

        if len(data["skills"]) == 1:
            return
        del data["skills"][num]
        data["useType"] = 1
        self.reloadSetting3(data)

    ## 링크스킬 저장
    def saveEditingLinkSkill(self, data):
        self.disablePopup()

        num = data["num"]
        data.pop("num")
        if num == -1:
            self.shared_data.linkSkillList.append(data)
        else:
            self.shared_data.linkSkillList[num] = data

        dataSave(self.shared_data)
        self.removeSetting3()
        self.shared_data.setting_type = -1
        self.changeSettingTo2()

    ## 링크스킬 취소
    def cancelEditingLinkSkill(self):
        self.disablePopup()

        self.removeSetting3()
        self.shared_data.setting_type = -1
        self.changeSettingTo2()

    ## 링크스킬 추가
    def addLinkSkill(self, data):
        def checkRemain():
            skillID = 0
            maxSkill = self.shared_data.SKILL_COMBO_COUNT_LIST[self.shared_data.serverID][
                self.shared_data.jobID
            ][skillID]
            for i in data["skills"]:
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
        data["skills"].append([0, 1])
        data["useType"] = 1
        self.reloadSetting3(data)

    ## 링크스킬 사용 횟수 설정
    def editLinkSkillCount(self, var):
        data, num = var

        if self.shared_data.active_popup == "editLinkSkillCount":
            self.disablePopup()
            return
        self.activatePopup("editLinkSkillCount")

        count = self.shared_data.SKILL_COMBO_COUNT_LIST[self.shared_data.serverID][self.shared_data.jobID][
            data["skills"][num][0]
        ]

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
            skillID = data["skills"][num][0]
            maxSkill = self.shared_data.SKILL_COMBO_COUNT_LIST[self.shared_data.serverID][
                self.shared_data.jobID
            ][skillID]
            for i in data["skills"]:
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

        data["skills"][num][1] = i
        if checkRemain() == -1:
            self.makeNoticePopup("exceedMaxLinkSkill")
        data["useType"] = 1
        self.reloadSetting3(data)

    ## 링크스킬 키 설정
    def setLinkSkillKey(self, data, num):
        if num == 0:
            data["keyType"] = 0
            self.reloadSetting3(data)
        else:
            self.activatePopup("settingLinkSkillKey")
            self.makeKeyboardPopup(("LinkSkill", data))

    ## 링크스킬 자동으로 설정
    def setLinkSkillToAuto(self, data):
        self.disablePopup()
        if data["useType"] == 0:
            return

        num = data["num"]

        for i in data["skills"]:
            if not (i[0] in self.shared_data.selectedSkillList):
                self.makeNoticePopup("skillNotSelected")
                return

        # 사용여부는 연계스킬에 적용되지 않음
        # for i in data[2]:
        #     if not self.useSkill[i[0]]:
        #         self.makeNoticePopup("skillNotUsing")
        #         return
        if len(self.shared_data.linkSkillList) != 0:
            prevData = copy.deepcopy(self.shared_data.linkSkillList[num])
            self.shared_data.linkSkillList[num] = copy.deepcopy(data)
            self.shared_data.linkSkillList[num].pop("num")
            autoSkillList = []
            for i in self.shared_data.linkSkillList:
                if i["useType"] == 0:
                    for j in range(len(i["skills"])):
                        autoSkillList.append(i["skills"][j][0])
            self.shared_data.linkSkillList[num] = prevData

            for i in range(len(data["skills"])):
                if data["skills"][i][0] in autoSkillList:
                    self.makeNoticePopup("autoAlreadyExist")
                    return

        data["useType"] = 0
        self.reloadSetting3(data)

    ## 링크스킬 수동으로 설정
    def setLinkSkillToManual(self, data):
        self.disablePopup()
        if data["useType"] == 1:
            return

        data["useType"] = 1
        self.reloadSetting3(data)

    ## 링크스킬 미리보기 생성
    def makeLinkSkillPreview(self, data):
        for i in self.linkSkillPreviewList:
            i.deleteLater()

        count = len(data["skills"])
        if count <= 6:
            x1 = round((288 - 48 * count) * 0.5)
            for i, j in enumerate(data["skills"]):
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
            for i, j in enumerate(data["skills"]):
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
        del self.shared_data.linkSkillList[num]
        self.removeSetting2()
        self.shared_data.setting_type = -1
        self.changeSettingTo2()
        dataSave(self.shared_data)

    ## 연계스킬 설정
    def editLinkSkill(self, num):
        self.disablePopup()
        self.cancelSkillSelection()

        data = copy.deepcopy(self.shared_data.linkSkillList[num])
        data["num"] = num
        self.removeSetting2()
        self.shared_data.setting_type = -1
        self.changeSettingTo3(data)

    ## 새 연계스킬 생성
    def makeNewLinkSkill(self):
        def findKey():
            for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if not isKeyUsing(self.shared_data, char):
                    return char
            return None

        self.disablePopup()
        self.cancelSkillSelection()

        data = {
            "useType": 1,
            "keyType": 0,
            "key": findKey(),
            "skills": [
                [0, 1],
            ],
            "num": -1,
        }
        self.removeSetting2()
        self.shared_data.setting_type = -1
        self.changeSettingTo3(data)

    ## 스킬 사용설정 -> 사용 여부 클릭
    def onSkillUsagesClick(self, num):
        self.disablePopup()
        if self.shared_data.ifUseSkill[num]:
            pixmap = QPixmap(convertResourcePath("resources\\image\\checkFalse.png"))
            self.settingSkillUsages[num].setIcon(QIcon(pixmap))
            self.shared_data.ifUseSkill[num] = False

            # for i, j in enumerate(self.shared_data.linkSkillList):
            #     for k in j[2]:
            #         if k[0] == num:
            #             self.shared_data.linkSkillList[i][0] = 1
        else:
            pixmap = QPixmap(convertResourcePath("resources\\image\\checkTrue.png"))
            self.settingSkillUsages[num].setIcon(QIcon(pixmap))
            self.shared_data.ifUseSkill[num] = True
        dataSave(self.shared_data)

    ## 스킬 사용설정 -> 콤보 여부 클릭
    def onSkillCombosClick(self, num):
        self.disablePopup()
        if self.shared_data.ifUseSole[num]:
            pixmap = QPixmap(convertResourcePath("resources\\image\\checkFalse.png"))
            self.settingSkillSingle[num].setIcon(QIcon(pixmap))
            self.shared_data.ifUseSole[num] = False
        else:
            pixmap = QPixmap(convertResourcePath("resources\\image\\checkTrue.png"))
            self.settingSkillSingle[num].setIcon(QIcon(pixmap))
            self.shared_data.ifUseSole[num] = True
        dataSave(self.shared_data)

    ## 스킬 사용설정 -> 콤보 횟수 클릭
    def onSkillComboCountsClick(self, num):
        combo = self.shared_data.SKILL_COMBO_COUNT_LIST[self.shared_data.serverID][self.shared_data.jobID][
            num
        ]
        if self.shared_data.active_popup == "SkillComboCounts":
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

        self.shared_data.comboCount[num] = count
        self.settingSkillComboCounts[num].setText(
            f"{count} / {self.shared_data.SKILL_COMBO_COUNT_LIST[self.shared_data.serverID][self.shared_data.jobID][num]}"
        )

        dataSave(self.shared_data)
        self.disablePopup()

    ## 스킬 사용설정 -> 사용 순서 클릭
    def onSkillSequencesClick(self, num):
        self.disablePopup()

        def returnMin():
            for i in range(1, 7):
                if not (i in self.shared_data.skillPriority):
                    return i

        if not (num in self.shared_data.selectedSkillList):
            return

        if self.shared_data.skillPriority[num] == None:
            minValue = returnMin()
            self.shared_data.skillPriority[num] = minValue
            self.settingSkillSequences[num].setText(str(minValue))
        else:
            self.shared_data.skillPriority[num] = None
            self.settingSkillSequences[num].setText("-")

            for i in range(1, 7):
                if not (i in self.shared_data.skillPriority):
                    for j, k in enumerate(self.shared_data.skillPriority):
                        if not (k == None):
                            if k > i:
                                self.shared_data.skillPriority[j] -= 1
                                self.settingSkillSequences[j].setText(str(k - 1))

        dataSave(self.shared_data)

    ## 스킬 이미지 디렉토리 리턴
    def getSkillImage(self, num, count=-1):
        # return convertResourcePath("resources\\emptySkill.png")
        if count == -1:
            return convertResourcePath(
                f"resources\\image\\skill\\{self.shared_data.serverID}\\{self.shared_data.jobID}\\{num}\\{self.shared_data.SKILL_COMBO_COUNT_LIST[self.shared_data.serverID][self.shared_data.jobID][num]}.png"
            )
        else:
            return convertResourcePath(
                f"resources\\image\\skill\\{self.shared_data.serverID}\\{self.shared_data.jobID}\\{num}\\{count}.png"
            )

    ## 탭 변경
    def changeTab(self, num):
        dataLoad(self.shared_data, num)

        if self.shared_data.setting_type != 0:
            self.changeSettingTo0()

        for tabNum in range(len(self.shared_data.tabNames)):
            if tabNum == self.shared_data.recentPreset:
                self.tabList[tabNum].setStyleSheet(
                    """background-color: #eeeeff; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )
            else:
                self.tabList[tabNum].setStyleSheet(
                    """background-color: #dddddd; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )

            if tabNum == self.shared_data.recentPreset:
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
            if tabNum == self.shared_data.recentPreset:
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
            self.selectableSkillImageName[i].setText(
                self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][i]
            )
        for i in range(6):
            if self.shared_data.selectedSkillList[i] != -1:
                pixmap = QPixmap(self.getSkillImage(self.shared_data.selectedSkillList[i]))
            else:
                pixmap = QPixmap(convertResourcePath("resources\\image\\emptySkill.png"))
            self.selectedSkillImageButton[i].setIcon(QIcon(pixmap))

        self.buttonServerList.setText(self.shared_data.SERVER_LIST[self.shared_data.serverID])
        self.buttonJobList.setText(
            self.shared_data.JOB_LIST[self.shared_data.serverID][self.shared_data.jobID]
        )

        self.buttonInputDelay.setText(str(self.shared_data.inputDelay))
        rgb = 153 if self.shared_data.activeDelaySlot == 1 else 0
        self.buttonDefaultDelay.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        rgb = 153 if self.shared_data.activeDelaySlot == 0 else 0
        self.buttonInputDelay.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")

        self.buttonInputCooltime.setText(str(self.shared_data.inputCooltime))
        rgb = 153 if self.shared_data.activeCooltimeSlot == 1 else 0
        self.buttonDefaultCooltime.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        rgb = 153 if self.shared_data.activeCooltimeSlot == 0 else 0
        self.buttonInputCooltime.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")

        self.buttonInputStartKey.setText(str(self.shared_data.inputStartKey))
        rgb = 153 if self.shared_data.activeStartKeySlot == 1 else 0
        self.buttonDefaultStartKey.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        rgb = 153 if self.shared_data.activeStartKeySlot == 0 else 0
        self.buttonInputStartKey.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")

        rgb = 153 if self.shared_data.activeMouseClickSlot == 1 else 0
        self.button1stMouseType.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        rgb = 153 if self.shared_data.activeMouseClickSlot == 0 else 0
        self.button2ndMouseType.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")

        self.update()
        self.updatePosition()
        dataSave(self.shared_data)

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

        if self.shared_data.is_tab_remove_popup_activated:
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
                text = f"딜레이는 {self.shared_data.MIN_DELAY}~{self.shared_data.MAX_DELAY}까지의 수를 입력해야 합니다."
                icon = "error"
            case "cooltimeInputError":
                text = f"쿨타임은 {self.shared_data.MIN_COOLTIME}~{self.shared_data.MAX_COOLTIME}까지의 수를 입력해야 합니다."
                icon = "error"
            case "StartKeyChangeError":
                text = "해당 키는 이미 사용중입니다."
                icon = "error"
            case "RequireUpdate":
                text = f"프로그램이 최신버전이 아닙니다.\n현재 버전: {self.shared_data.VERSION}, 최신버전: {self.recentVersion}"
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
            self.height() - frameHeight - 15 - self.shared_data.active_error_popup_count * 10,
        )
        noticePopup.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
        noticePopup.show()

        noticePopupIcon = QPushButton(noticePopup)
        noticePopupIcon.setStyleSheet("background-color: transparent;")
        noticePopupIcon.setFixedSize(24, 24)
        noticePopupIcon.move(13, 15)
        pixmap = QPixmap(convertResourcePath(f"resources\\image\\{icon}.png"))
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
            partial(lambda x: self.removeNoticePopup(x), self.shared_data.active_error_popup_count)
        )
        pixmap = QPixmap(convertResourcePath("resources\\image\\x.png"))
        noticePopupRemove.setIcon(QIcon(pixmap))
        noticePopupRemove.setIconSize(QSize(24, 24))
        noticePopupRemove.show()

        self.shared_data.active_error_popup.append(
            [noticePopup, frameHeight, self.shared_data.active_error_popup_count]
        )
        self.shared_data.active_error_popup_count += 1

    ## 알림 창 제거
    def removeNoticePopup(self, num=-1):
        if num != -1:
            for i, j in enumerate(self.shared_data.active_error_popup):
                if num == j[2]:
                    j[0].deleteLater()
                    self.shared_data.active_error_popup.pop(i)
        else:
            self.shared_data.active_error_popup[-1][0].deleteLater()
            self.shared_data.active_error_popup.pop()
        # self.activeErrorPopup[num][0].deleteLater()
        # self.activeErrorPopup.pop(0)
        self.shared_data.active_error_popup_count -= 1
        self.updatePosition()

    ## 모든 팝업창 제거
    def disablePopup(self):
        if self.shared_data.active_popup == "":
            return
        else:
            self.settingPopupFrame.deleteLater()
        self.shared_data.active_popup = ""

    ## 팝업창 할당
    def activatePopup(self, text):
        self.disablePopup()
        self.shared_data.active_popup = text

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
                x = 360 + 200 * self.shared_data.recentPreset
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
                default = str(self.shared_data.inputDelay)
            case "cooltime":
                default = str(self.shared_data.inputCooltime)
            case ("tabName", _):
                default = self.shared_data.tabNames[self.shared_data.recentPreset]
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
                if not (self.shared_data.MIN_DELAY <= text <= self.shared_data.MAX_DELAY):
                    self.disablePopup()
                    self.makeNoticePopup("delayInputError")
                    return
                self.buttonInputDelay.setText(str(text))
                self.shared_data.inputDelay = text
                self.shared_data.delay = text
            case "cooltime":
                if not (self.shared_data.MIN_COOLTIME <= text <= self.shared_data.MAX_COOLTIME):
                    self.disablePopup()
                    self.makeNoticePopup("cooltimeInputError")
                    return
                self.buttonInputCooltime.setText(str(text))
                self.shared_data.inputCooltime = text
                self.shared_data.cooltimeReduce = text
            case ("tabName", _):
                self.tabButtonList[input_type[1]].setText(" " + text)
                self.shared_data.tabNames[input_type[1]] = text

        dataSave(self.shared_data)
        self.disablePopup()

        self.update()
        self.updatePosition()

    ## 사이드바 설정 - 서버 클릭
    def onServerClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingServer":
            self.disablePopup()
        else:
            self.activatePopup("settingServer")

            self.settingPopupFrame = QFrame(self.sidebarFrame)
            self.settingPopupFrame.setStyleSheet("background-color: white; border-radius: 10px;")
            self.settingPopupFrame.setFixedSize(130, 5 + 35 * len(self.shared_data.SERVER_LIST))
            self.settingPopupFrame.move(25, 240)
            self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
            self.settingPopupFrame.show()

            for i in range(len(self.shared_data.SERVER_LIST)):
                self.settingServerButton = QPushButton(
                    self.shared_data.SERVER_LIST[i], self.settingPopupFrame
                )
                self.settingServerButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
                self.settingServerButton.clicked.connect(partial(lambda x: self.onServerPopupClick(x), i))
                self.settingServerButton.setStyleSheet(
                    f"""
                                QPushButton {{
                                    background-color: {"white" if i != self.shared_data.serverID else "#dddddd"}; border-radius: 10px;
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
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

    ## 사이드바 설정 - 직업 클릭
    def onJobClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingJob":
            self.disablePopup()
        else:
            self.activatePopup("settingJob")

            self.settingPopupFrame = QFrame(self.sidebarFrame)
            self.settingPopupFrame.setStyleSheet("background-color: white; border-radius: 10px;")
            self.settingPopupFrame.setFixedSize(
                130, 5 + 35 * len(self.shared_data.JOB_LIST[self.shared_data.serverID])
            )
            self.settingPopupFrame.move(145, 240)
            self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
            self.settingPopupFrame.show()

            for i in range(len(self.shared_data.JOB_LIST[self.shared_data.serverID])):
                self.settingJobButton = QPushButton(
                    self.shared_data.JOB_LIST[self.shared_data.serverID][i], self.settingPopupFrame
                )
                self.settingJobButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
                self.settingJobButton.clicked.connect(partial(lambda x: self.onJobPopupClick(x), i))
                self.settingJobButton.setStyleSheet(
                    f"""
                                QPushButton {{
                                    background-color: {"white" if i != self.shared_data.jobID else "#dddddd"}; border-radius: 10px;
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
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.shared_data.jobID != num:
            self.shared_data.jobID = num
            self.shared_data.selectedSkillList = [-1, -1, -1, -1, -1, -1]
            self.shared_data.linkSkillList = []

            self.buttonJobList.setText(self.shared_data.JOB_LIST[self.shared_data.serverID][num])

            for i in range(8):
                self.shared_data.comboCount[i] = self.shared_data.SKILL_COMBO_COUNT_LIST[
                    self.shared_data.serverID
                ][self.shared_data.jobID][i]

            for i in range(8):
                pixmap = QPixmap(self.getSkillImage(i))
                self.selectableSkillImageButton[i].setIcon(QIcon(pixmap))
                self.selectableSkillImageName[i].setText(
                    self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][i]
                )

            for i in range(6):
                if self.shared_data.selectedSkillList[i] != -1:
                    pixmap = QPixmap(self.getSkillImage(self.shared_data.selectedSkillList[i]))
                else:
                    pixmap = QPixmap(convertResourcePath("resources\\image\\emptySkill.png"))
                self.selectedSkillImageButton[i].setIcon(QIcon(pixmap))

            self.updatePosition()

            dataSave(self.shared_data)
        self.disablePopup()

    ## 사이드바 설정 - 기본 딜레이 클릭
    def onDefaultDelayClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.shared_data.activeDelaySlot == 0:
            return

        self.shared_data.activeDelaySlot = 0
        self.shared_data.delay = 150

        self.buttonDefaultDelay.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputDelay.setStyleSheet("QPushButton { color: #999999; }")

        dataSave(self.shared_data)

    ## 사이드바 설정 -  유저 딜레이 클릭
    def onInputDelayClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingDelay":
            self.disablePopup()
            return
        self.disablePopup()

        if self.shared_data.activeDelaySlot == 1:
            self.activatePopup("settingDelay")

            self.makePopupInput("delay")
        else:
            self.shared_data.activeDelaySlot = 1
            self.shared_data.delay = self.shared_data.inputDelay

            self.buttonDefaultDelay.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputDelay.setStyleSheet("QPushButton { color: #000000; }")

            dataSave(self.shared_data)

    ## 사이드바 설정 - 기본 쿨타임 감소 클릭
    def onDefaultCooltimeClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.shared_data.activeCooltimeSlot == 0:
            return

        self.shared_data.activeCooltimeSlot = 0
        self.shared_data.cooltimeReduce = 0

        self.buttonDefaultCooltime.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputCooltime.setStyleSheet("QPushButton { color: #999999; }")

        dataSave(self.shared_data)

    ## 사이드바 설정 - 유저 쿨타임 감소 클릭
    def onInputCooltimeClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingCooltime":
            self.disablePopup()
            return
        self.disablePopup()

        if self.shared_data.activeCooltimeSlot == 1:
            self.activatePopup("settingCooltime")

            self.makePopupInput("cooltime")
        else:
            self.shared_data.activeCooltimeSlot = 1
            self.shared_data.cooltimeReduce = self.shared_data.inputCooltime

            self.buttonDefaultCooltime.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputCooltime.setStyleSheet("QPushButton { color: #000000; }")

            dataSave(self.shared_data)

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
                    isKeyUsing(self.shared_data, key),
                )

        row = 0
        column = 1
        for key in k1:
            makePresetKey(key, row, column, isKeyUsing(self.shared_data, key))
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
            isKeyUsing(self.shared_data, "Tab"),
        )
        row = 0
        column += 1
        for key in k2:
            makePresetKey(key, row, column, isKeyUsing(self.shared_data, key))
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
            makePresetKey(key, row, column, isKeyUsing(self.shared_data, key))
            row += 1
        makeKey(
            "Enter",
            445,
            110,
            55,
            30,
            isKeyUsing(self.shared_data, "Enter"),
        )

        makeKey(
            "Shift",
            5,
            145,
            70,
            30,
            isKeyUsing(self.shared_data, "Shift"),
        )
        row = 0
        column += 1
        for key in k4:
            makePresetKey(key, row, column, isKeyUsing(self.shared_data, key))
            row += 1
        makeKey(
            "Shift",
            430,
            145,
            70,
            30,
            isKeyUsing(self.shared_data, "Shift"),
        )

        makeKey(
            "Ctrl",
            5,
            180,
            45,
            30,
            isKeyUsing(self.shared_data, "Ctrl"),
        )
        makeImageKey(
            "Window",
            55,
            180,
            45,
            30,
            convertResourcePath("resources\\image\\window.png"),
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
            isKeyUsing(self.shared_data, "Alt"),
        )
        makeKey(
            "Space",
            155,
            180,
            145,
            30,
            isKeyUsing(self.shared_data, "Space"),
        )
        makeKey(
            "Alt",
            305,
            180,
            45,
            30,
            isKeyUsing(self.shared_data, "Alt"),
        )
        makeImageKey(
            "Window",
            355,
            180,
            45,
            30,
            convertResourcePath("resources\\image\\window.png"),
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
            isKeyUsing(self.shared_data, "Ctrl"),
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
                    isKeyUsing(self.shared_data, j2),
                )

        makeImageKey(
            "Up",
            565,
            145,
            30,
            30,
            convertResourcePath("resources\\image\\arrow.png"),
            16,
            0,
            isKeyUsing(self.shared_data, "Up"),
        )
        makeImageKey(
            "Left",
            530,
            180,
            30,
            30,
            convertResourcePath("resources\\image\\arrow.png"),
            16,
            270,
            isKeyUsing(self.shared_data, "Left"),
        )
        makeImageKey(
            "Down",
            565,
            180,
            30,
            30,
            convertResourcePath("resources\\image\\arrow.png"),
            16,
            180,
            isKeyUsing(self.shared_data, "Down"),
        )
        makeImageKey(
            "Right",
            600,
            180,
            30,
            30,
            convertResourcePath("resources\\image\\arrow.png"),
            16,
            90,
            isKeyUsing(self.shared_data, "Right"),
        )

    ## 시작키 설정용 가상키보드 키 클릭시 실행
    def onStartKeyPopupKeyboardClick(self, key, disabled):
        if self.shared_data.is_activated:
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
        self.shared_data.inputStartKey = key
        self.shared_data.startKey = key

        dataSave(self.shared_data)
        self.disablePopup()

    ## 사이드바 설정 - 기본 시작키 클릭
    def onDefaultStartKeyClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.shared_data.activeStartKeySlot == 0:
            return

        if self.shared_data.inputStartKey != "F9" and isKeyUsing(self.shared_data, "F9"):
            self.makeNoticePopup("StartKeyChangeError")
            return

        self.shared_data.activeStartKeySlot = 0
        self.shared_data.startKey = "F9"

        self.buttonDefaultStartKey.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputStartKey.setStyleSheet("QPushButton { color: #999999; }")

        dataSave(self.shared_data)

    ## 사이드바 설정 - 유저 시작키 클릭
    def onInputStartKeyClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingStartKey":
            self.disablePopup()
            return
        self.disablePopup()

        if self.shared_data.activeStartKeySlot == 1:
            self.activatePopup("settingStartKey")

            self.makeKeyboardPopup("StartKey")
        else:
            if isKeyUsing(self.shared_data, self.shared_data.inputStartKey) and not (
                self.shared_data.inputStartKey == "F9"
            ):
                self.makeNoticePopup("StartKeyChangeError")
                return
            self.shared_data.activeStartKeySlot = 1
            self.shared_data.startKey = self.shared_data.inputStartKey

            self.buttonDefaultStartKey.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputStartKey.setStyleSheet("QPushButton { color: #000000; }")

            dataSave(self.shared_data)

    ## 사이드바 설정 - 마우스설정1 클릭
    def on1stMouseTypeClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.shared_data.activeMouseClickSlot == 0:
            return

        self.shared_data.activeMouseClickSlot = 0

        self.button1stMouseType.setStyleSheet("QPushButton { color: #000000; }")
        self.button2ndMouseType.setStyleSheet("QPushButton { color: #999999; }")

        dataSave(self.shared_data)

    ## 사이드바 설정 - 마우스설정2 클릭
    def on2ndMouseTypeClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        if self.shared_data.activeMouseClickSlot == 1:
            return

        self.shared_data.activeMouseClickSlot = 1

        self.button1stMouseType.setStyleSheet("QPushButton { color: #999999; }")
        self.button2ndMouseType.setStyleSheet("QPushButton { color: #000000; }")

        dataSave(self.shared_data)

    ## 탭 클릭
    def onTabClick(self, num):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.shared_data.recentPreset == num:
            if self.shared_data.active_popup == "changeTabName":
                self.disablePopup()
            else:
                self.activatePopup("changeTabName")
                self.makePopupInput(("tabName", num))
            return
        self.disablePopup()

        self.changeTab(num)

    ## 탭 추가버튼 클릭
    def onTabAddClick(self):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()

        dataAdd()

        tabNum = len(self.shared_data.tabNames)
        dataLoad(self.shared_data, tabNum)

        tabBackground = QLabel("", self.page1)
        tabBackground.setStyleSheet(
            """background-color: #eeeef5; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
        )
        tabBackground.setFixedSize(250, 50)
        tabBackground.move(340 + 250 * tabNum, 20)
        tabBackground.setGraphicsEffect(self.getShadow(5, -2))
        tabBackground.show()

        tabButton = QPushButton(f" {self.shared_data.tabNames[tabNum]}", self.page1)
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
        pixmap = QPixmap(convertResourcePath("resources\\image\\x.png"))
        tabRemoveButton.setIcon(QIcon(pixmap))
        tabRemoveButton.setFixedSize(40, 40)
        tabRemoveButton.move(545 + 250 * tabNum, 25)
        tabRemoveButton.show()

        self.tabButtonList.append(tabButton)
        self.tabList.append(tabBackground)
        self.tabRemoveList.append(tabRemoveButton)

        self.tabAddButton.move(350 + 250 * len(self.shared_data.tabNames), 25)

        self.changeTab(tabNum)

    ## 탭 제거버튼 클릭
    def onTabRemoveClick(self, num):
        self.shared_data.is_tab_remove_popup_activated = True
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
            self.limitText(f'정말 "{self.shared_data.tabNames[num]}', self.tabRemoveNameLabel, margin=5) + '"'
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
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        self.disablePopup()
        self.tabRemoveBackground.deleteLater()
        self.shared_data.is_tab_remove_popup_activated = False

        if not remove:
            return

        tabCount = len(self.shared_data.tabNames)

        if tabCount != 1:
            if self.shared_data.recentPreset == num:
                if (tabCount - 1) > num:
                    self.shared_data.tabNames.pop(num)
                    dataRemove(num)
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
                    self.tabAddButton.move(350 + 250 * len(self.shared_data.tabNames), 25)

                    self.changeTab(num)
                else:
                    self.shared_data.tabNames.pop(num)
                    dataRemove(num)
                    self.tabButtonList[num].deleteLater()
                    self.tabButtonList.pop(num)
                    self.tabList[num].deleteLater()
                    self.tabList.pop(num)
                    self.tabRemoveList[num].deleteLater()
                    self.tabRemoveList.pop(num)

                    self.tabAddButton.move(350 + 250 * len(self.shared_data.tabNames), 25)

                    self.changeTab(num - 1)
                    self.shared_data.recentPreset = num - 1
            elif self.shared_data.recentPreset > num:
                self.shared_data.tabNames.pop(num)
                dataRemove(num)
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
                self.tabAddButton.move(350 + 250 * len(self.shared_data.tabNames), 25)

                self.changeTab(self.shared_data.recentPreset - 1)
            elif self.shared_data.recentPreset < num:
                # print(self.shared_data.tabNames)
                # print(num)
                self.shared_data.tabNames.pop(num)
                dataRemove(num)
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
                self.tabAddButton.move(350 + 250 * len(self.shared_data.tabNames), 25)
        else:
            dataRemove(0)
            dataLoad(self.shared_data, 0)
            self.changeTab(0)
            self.tabButtonList[0].setText(" " + self.shared_data.tabNames[0])

        self.update()
        self.updatePosition()
        dataSave(self.shared_data)

    ## 링크스킬 단축키용 가상키보드 키 클릭시 실행
    def onLinkSkillKeyPopupKeyboardClick(self, key, disabled, data):
        if self.shared_data.is_activated:
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

        data["key"] = key
        data["keyType"] = 1
        self.reloadSetting3(data)

    ## 스킬 단축키용 가상키보드 키 클릭시 실행
    def onSkillKeyPopupKeyboardClick(self, key, disabled, num):
        if self.shared_data.is_activated:
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
        self.shared_data.skillKeys[num] = key

        dataSave(self.shared_data)
        self.disablePopup()

    ## 스킬 단축키 설정 버튼 클릭
    def onSkillKeyClick(self, num):
        if self.shared_data.is_activated:
            self.disablePopup()
            self.makeNoticePopup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "skillKey":
            self.disablePopup()
            return
        self.disablePopup()

        self.activatePopup("skillKey")
        self.makeKeyboardPopup(["skillKey", num])

    ## 마우스 클릭하면 실행
    def mousePressEvent(self, event):
        self.disablePopup()
        if self.shared_data.layout_type == 0:
            self.cancelSkillSelection()

    ## 사이드바 구분선 생성
    def paintEvent(self, event):
        if self.shared_data.layout_type == 0:
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
        if self.shared_data.layout_type == 0:
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
            for i, j in enumerate(self.shared_data.skill_preview_list):
                j.setFixedSize(round((288 * (xMultSize + 1) / 6)), round(48 * (yMultSize + 1)))
                j.move(
                    round(
                        (
                            self.skillPreviewFrame.width()
                            - j.width() * len(self.shared_data.skill_preview_list)
                        )
                        * 0.5
                    )
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
                j.setText(
                    self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][i]
                )
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
                self.adjustFontSize(j, self.shared_data.skillKeys[i], 20)

            if 460 + 200 * len(self.shared_data.tabNames) <= self.width():
                for tabNum in range(len(self.shared_data.tabNames)):
                    self.tabList[tabNum].move(360 + 200 * tabNum, 20)
                    self.tabList[tabNum].setFixedSize(200, 50)
                    self.tabButtonList[tabNum].move(365 + 200 * tabNum, 25)
                    self.tabButtonList[tabNum].setFixedSize(190, 40)
                    self.tabButtonList[tabNum].setText(
                        self.limitText(f" {self.shared_data.tabNames[tabNum]}", self.tabButtonList[tabNum])
                    )
                    self.tabRemoveList[tabNum].move(515 + 200 * tabNum, 25)
                    self.tabAddButton.move(370 + 200 * len(self.shared_data.tabNames), 25)

                    if self.shared_data.active_popup == "changeTabName":
                        self.settingPopupFrame.move(360 + 200 * self.shared_data.recentPreset, 80)
            else:
                width = round((self.width() - 460) / len(self.shared_data.tabNames))
                for tabNum in range(len(self.shared_data.tabNames)):
                    self.tabList[tabNum].move(360 + width * tabNum, 20)
                    self.tabList[tabNum].setFixedSize(width, 50)
                    self.tabButtonList[tabNum].move(365 + width * tabNum, 25)
                    self.tabButtonList[tabNum].setFixedSize(width - 10, 40)
                    self.tabButtonList[tabNum].setText(
                        self.limitText(f" {self.shared_data.tabNames[tabNum]}", self.tabButtonList[tabNum])
                    )
                    self.tabRemoveList[tabNum].move(315 + width * (tabNum + 1), 25)
                    self.tabAddButton.move(self.width() - 80, 25)
                    # self.tabAddButton.move(350 + width * len(self.shared_data.tabNames), 25)
                if self.shared_data.active_popup == "changeTabName":
                    self.settingPopupFrame.move(360 + width * self.shared_data.recentPreset, 80)

            if self.shared_data.is_tab_remove_popup_activated:
                self.tabRemoveBackground.setFixedSize(self.width(), self.height())
                self.tabRemoveFrame.move(round(self.width() * 0.5 - 170), round(self.height() * 0.5 - 60))
                self.tabRemoveBackground.raise_()

        else:  # 레이아웃 1 (계산기)
            deltaWidth = self.width() - self.shared_data.DEFAULT_WINDOW_WIDTH

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

            if self.shared_data.sim_type == 1:  # 정보 입력
                self.sim1_frame1.move(deltaWidth // 2, 0)
                self.sim1_frame2.move(
                    deltaWidth // 2,
                    self.sim1_frame1.y() + self.sim1_frame1.height() + self.sim_main_D,
                )
                self.sim1_frame3.move(
                    deltaWidth // 2,
                    self.sim1_frame2.y() + self.sim1_frame2.height() + self.sim_main_D,
                )

            elif self.shared_data.sim_type == 2:  # 시뮬레이터
                self.sim2_frame1.move(deltaWidth // 2, 0)
                self.sim2_frame2.move(
                    deltaWidth // 2,
                    self.sim2_frame1.y() + self.sim2_frame1.height() + self.sim_main_D,
                )

            elif self.shared_data.sim_type == 3:  # 스탯 계산기
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

            elif self.shared_data.sim_type == 4:  # 캐릭터 카드
                self.sim4_frame.move(deltaWidth // 2, 0)

        # 항상 업데이트
        self.labelCreator.move(2, self.height() - 25)
        for i, j in enumerate(self.shared_data.active_error_popup):
            j[0].move(
                self.width() - 420,
                self.height() - j[1] - 15 - i * 10,
            )
        for i in self.shared_data.active_error_popup:
            i[0].raise_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
