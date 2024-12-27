import copy
import json
import os
import sys
import time
from functools import partial
import matplotlib.patches as patches
from threading import Thread
from webbrowser import open_new
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import numpy as np
import keyboard as kb
import pyautogui as pag
from PyQt6.QtCore import QObject, QSize, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import (
    QPen,
    QFont,
    QIcon,
    QColor,
    QPixmap,
    QPainter,
    QPalette,
    QTransform,
    QFontDatabase,
)
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QWidget,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QApplication,
    QStackedLayout,
    QGraphicsDropShadowEffect,
)
from requests import get


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
            response = get(
                "https://api.github.com/repos/pro-days/skillmacro/releases/latest"
            )
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
        self.resetVar()
        self.setWindowIcon(self.icon)
        self.dataLoad()
        self.initUI()

        self.checkVersion()
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

                time.sleep(0.5 * self.sleepCoefficient)

            elif convertedKey in linkKeys and not self.isActivated:
                for i in range(len(linkKeys)):
                    if convertedKey == linkKeys[i]:
                        Thread(target=self.useLinkSkill, args=[i, self.loopNum]).start()

                time.sleep(0.25 * self.sleepCoefficient)
            else:
                pass

    def changeLayout(self, num):
        self.windowLayout.setCurrentIndex(num)
        self.layoutType = num

        if num == 0:
            [i.deleteLater() for i in self.page2.findChildren(QWidget)]
            self.updatePosition()
        elif num == 1:
            self.makePage2()

    def makePage2(self):
        self.sim_colors4 = [
            "255, 130, 130",
            "255, 230, 140",
            "170, 230, 255",
            "150, 225, 210",
        ]
        self.sim_input_colors = ["#f0f0f0", "#D9D9D9"]  # [background, border]
        self.sim_labelFrame_color = "#bbbbbb"
        self.scrollBarWidth = 12
        self.sim_margin = 10

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

        self.sim_powerL_margin = 25
        self.sim_powerL_D = 20
        self.sim_powerL_width = 205
        self.sim_powerL_frame_H = 140
        self.sim_powerL_title_H = 50
        self.sim_powerL_number_H = 90

        self.sim_analysis_margin = self.sim_powerL_margin
        self.sim_analysis_D = self.sim_powerL_D
        self.sim_analysis_width = self.sim_powerL_width
        self.sim_analysis_color_W = 5
        self.sim_analysis_widthXC = self.sim_analysis_width - self.sim_analysis_color_W
        self.sim_analysis_frame_H = 140
        self.sim_analysis_title_H = 40
        self.sim_analysis_number_H = 55
        self.sim_analysis_number_marginH = 5
        self.sim_analysis_details_H = 20
        self.sim_analysis_details_W = 60
        self.sim_analysis_detailsT_W = 23
        self.sim_analysis_detailsN_W = 37
        self.sim_analysis_details_margin = 5

        self.sim_dps_margin = 25
        self.sim_dps_width = 430
        self.sim_dps_height = 300

        self.sim_skillDps_margin = 20
        self.sim_skillDps_width = self.sim_dps_width
        self.sim_skillDps_height = self.sim_dps_height

        self.sim_dmg_margin = 25
        self.sim_dmg_width = 880
        self.sim_dmg_height = 400

        # 상단바
        self.sim_navFrame = QFrame(self.page2)
        self.sim_navFrame.setGeometry(
            self.sim_margin,
            self.sim_margin,
            self.width() - self.sim_margin * 2,
            self.sim_navHeight,
        )
        self.sim_navFrame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); }"
        )

        self.sim_navButtons = []
        texts = ["캐릭터 정보", "시뮬레이터", "스탯 계산기", "캐릭터 카드"]
        for i in [0, 1, 2, 3]:
            button = QPushButton(texts[i], self.sim_navFrame)
            button.setGeometry(
                self.sim_navBWidth * i, 0, self.sim_navBWidth, self.sim_navHeight
            )
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
        pixmap = QPixmap(convertResourcePath("resource\\x.png"))
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
            "QScrollArea { border: 0px solid black; border-radius: 10px; }"
        )
        self.sim_mainScrollArea.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.sim_mainScrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.sim_mainScrollArea.setPalette(self.backPalette)

        self.makeSimulType1()

    def removeSimulWidgets(self):
        [i.deleteLater() for i in self.sim_mainFrame.findChildren(QWidget)]
        self.simType = 0
        plt.close("all")

    def makeSimulType4(self):
        pass

    def makeSimulType3(self):
        pass

    def makeSimulType2(self):
        self.removeSimulWidgets()
        self.sim_updateNavButton(1)

        self.simType = 2

        # 전투력
        self.sim2_frame1 = QFrame(self.sim_mainFrame)
        self.sim2_frame1.setGeometry(
            0,
            0,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_powerL_frame_H),
        )
        self.sim2_frame1.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.sim2_frame1_labelFrame, self.sim2_frame1_label = self.sim_makeTitleFrame(
            self.sim2_frame1, "전투력"
        )
        text = ["12345", "12345", "12345", "12345"]
        self.sim_power_list = self.sim_make_PowerLabels(
            self.sim2_frame1, text
        )  # [[f, t, n], [f, t, n], [f, t, n], [f, t, n]]

        for i, (f, t, n) in enumerate(self.sim_power_list):
            f.setGeometry(
                self.sim_powerL_margin
                + (self.sim_powerL_width + self.sim_powerL_D) * i,
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
        self.sim2_frame2.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.sim2_frame2_labelFrame, self.sim2_frame2_label = self.sim_makeTitleFrame(
            self.sim2_frame2, "분석"
        )

        text = [
            {
                "title": "초당 피해량",
                "number": "12345",
                "min": "12345",
                "max": "12345",
                "std": "12345",
                "p25": "12345",
                "p50": "12345",
                "p75": "12345",
            },
            {
                "title": "총 피해량",
                "number": "12345",
                "min": "12345",
                "max": "12345",
                "std": "12345",
                "p25": "12345",
                "p50": "12345",
                "p75": "12345",
            },
            {
                "title": "초당 회복량",
                "number": "12345",
                "min": "12345",
                "max": "12345",
                "std": "12345",
                "p25": "12345",
                "p50": "12345",
                "p75": "12345",
            },
            {
                "title": "총 회복량",
                "number": "12345",
                "min": "12345",
                "max": "12345",
                "std": "12345",
                "p25": "12345",
                "p50": "12345",
                "p75": "12345",
            },
        ]
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
                self.sim_analysis_margin
                + (self.sim_analysis_width + self.sim_analysis_D) * i,
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

            title = QLabel(text[i]["title"], frame)
            title.setGeometry(
                self.sim_analysis_color_W,
                0,
                self.sim_analysis_widthXC,
                self.sim_analysis_title_H,
            )
            title.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            title.setFont(QFont("나눔스퀘어라운드 Bold", 14))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim_analysis_list[i].append(title)

            number = QLabel(text[i]["number"], frame)
            number.setGeometry(
                self.sim_analysis_color_W,
                self.sim_analysis_title_H,
                self.sim_analysis_widthXC,
                self.sim_analysis_number_H,
            )
            number.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
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
                    + (self.sim_analysis_details_W + self.sim_analysis_details_margin)
                    * (j % 3)
                    - 1,
                    self.sim_analysis_title_H
                    + self.sim_analysis_number_H
                    + self.sim_analysis_number_marginH
                    + self.sim_analysis_details_H * (j // 3),
                    self.sim_analysis_details_W,
                    self.sim_analysis_details_H,
                )
                detail_frame.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px solid; }"
                )
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

                detail_number = QLabel(text[i][details[j]], detail_frame)
                detail_number.setGeometry(
                    self.sim_analysis_detailsT_W,
                    0,
                    self.sim_analysis_detailsN_W,
                    self.sim_analysis_details_H,
                )
                detail_number.setStyleSheet(
                    "QLabel { background-color: transparent; border: 0px solid; }"
                )
                detail_number.setFont(QFont("나눔스퀘어라운드 ExtraBold", 9))
                detail_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.sim_analysis_list[i][4][j].append(detail_number)

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
        self.sim_dpsGraph = DpsDistributionCanvas(
            self.sim_dpsGraph_frame, np.random.normal(12000, 1000, 1000)
        )  # 시뮬레이션 결과
        self.sim_dpsGraph.move(5, 5)
        self.sim_dpsGraph.resize(self.sim_dps_width - 10, self.sim_dps_height - 10)

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
        self.sim_skillDpsGraph = SkillDpsDistributionCanvas(
            self.sim_skillDpsGraph_frame, [30.0, 20.0, 15.0, 12.5, 12.5, 10.0]
        )
        self.sim_skillDpsGraph.move(10, 10)
        self.sim_skillDpsGraph.resize(
            self.sim_skillDps_width - 20, self.sim_skillDps_height - 20
        )

        ## 시간 경과에 따른 피해량
        self.sim_dmgTime_frame = QFrame(self.sim2_frame2)
        self.sim_dmgTime_frame.setGeometry(
            self.sim_dps_margin,
            self.sim_label_H
            + self.sim_analysis_frame_H
            + self.sim_dps_height
            + self.sim_widget_D * 3,
            self.sim_dmg_width,
            self.sim_dmg_height,
        )
        self.sim_dmgTime_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )
        time = np.linspace(0, 60, 121)
        data = {
            "time": time,
            "max": 400 + 400 * np.sin(2 * np.pi * time / 20),
            "mean": 300 + 300 * np.sin(2 * np.pi * time / 20),
            "min": 200 + 200 * np.sin(2 * np.pi * time / 20),
        }
        self.sim_dmgTime = DMGCanvas(
            self.sim_dmgTime_frame, data, "time"
        )  # 시뮬레이션 결과
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
        time = np.linspace(0, 60, 121)
        data = {
            "time": time,
            "max": 400 + 400 * time - 400 * np.cos(2 * np.pi * time / 20),
            "mean": 300 + 300 * time - 300 * np.cos(2 * np.pi * time / 20),
            "min": 200 + 200 * time - 200 * np.cos(2 * np.pi * time / 20),
        }
        self.sim_totalDmg = DMGCanvas(
            self.sim_totalDmg_frame, data, "cumulative"
        )  # 시뮬레이션 결과
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

        # 5개의 스킬에 대한 데이터 생성
        time = np.linspace(0, 60, 121)
        num_skills = 6
        data_raw = np.random.rand(num_skills, 121)  # 5x100 랜덤 데이터

        def moving_average(data, window_size):
            window = np.ones(window_size) / window_size
            return np.convolve(data, window, mode="same")

        # 이동 평균을 사용하여 데이터 스무딩
        window_size = 11  # 윈도우 크기 (홀수를 사용하는 것이 좋음)
        smoothed_data = np.array([moving_average(row, window_size) for row in data_raw])

        # 각 시점에서 합이 1이 되도록 정규화
        data_normalized = smoothed_data / smoothed_data.sum(axis=0)
        # 누적 합 계산
        data_cumsum = np.cumsum(data_normalized, axis=0)

        # 데이터 딕셔너리 생성
        data = {
            "time": time,
            "skill1": data_normalized[0],
            "skill2": data_normalized[1],
            "skill3": data_normalized[2],
            "skill4": data_normalized[3],
            "skill5": data_normalized[4],
            "skill6": data_normalized[5],
            "skill1_sum": data_normalized[0],
            "skill2_sum": data_cumsum[0],
            "skill3_sum": data_cumsum[1],
            "skill4_sum": data_cumsum[2],
            "skill5_sum": data_cumsum[3],
            "skill6_sum": data_cumsum[4],
        }
        self.sim_skillContribute = SkillContributionCanvas(
            self.sim_skillContribute_frame, data
        )  # 시뮬레이션 결과
        self.sim_skillContribute.move(5, 5)
        self.sim_skillContribute.resize(
            self.sim_dmg_width - 10,
            self.sim_dmg_height - 10,
        )

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim2_frame2.y() + self.sim2_frame2.height(),
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
        self.sim1_frame1.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.sim1_frame1_labelFrame, self.sim1_frame1_label = self.sim_makeTitleFrame(
            self.sim1_frame1, "캐릭터 스탯"
        )
        self.sim_make_StatInput(self.sim1_frame1)
        self.sim_stat_inputs[0].setFocus()

        margin, count = 21, 6
        for i in range(18):
            self.sim_stat_frames[i].move(
                self.sim_stat_margin
                + self.sim_stat_width * (i % count)
                + margin * (i % count),
                self.sim1_frame1_labelFrame.height()
                + self.sim_widget_D * ((i // count) + 1)
                + self.sim_stat_frame_H * (i // count),
            )

        # 스킬 레벨
        self.sim1_frame2 = QFrame(self.sim_mainFrame)
        self.sim1_frame2.setGeometry(
            0,
            self.sim1_frame1.y() + self.sim1_frame1.height() + self.sim_main_D,
            928,
            self.sim_title_H + (self.sim_widget_D + self.sim_skill_frame_H) * 2,
        )
        self.sim1_frame2.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.sim1_frame2_labelFrame, self.sim1_frame2_label = self.sim_makeTitleFrame(
            self.sim1_frame2, "스킬 레벨"
        )
        self.sim_make_SkillInput(self.sim1_frame2)

        margin, count = 66, 4
        for i in range(8):
            self.sim_skill_frames[i].move(
                self.sim_skill_margin
                + self.sim_skill_width * (i % count)
                + margin * (i % count),
                self.sim1_frame2_labelFrame.height()
                + self.sim_widget_D * ((i // count) + 1)
                + self.sim_skill_frame_H * (i // count),
            )

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim1_frame2.y() + self.sim1_frame2.height(),
        )
        [i.show() for i in self.page2.findChildren(QWidget)]
        self.updatePosition()

    def sim_makeTitleFrame(self, mainFrame, title):
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

    def sim_make_PowerLabels(self, mainframe, texts):
        titles = ["보스", "데미지", "PVE", "PVP"]
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
            number.setFont(QFont("나눔스퀘어라운드 ExtraBold", 18))
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            power_list[i].append(number)

        return power_list

    def sim_make_SkillInput(self, mainframe):
        texts = self.skillNameList[self.serverID][self.jobID]

        self.sim_skill_frames = []
        self.sim_skill_names = []
        self.sim_skill_images = []
        self.sim_skill_levels = []
        self.sim1_skill_inputs = []
        for i in range(8):
            frame = QFrame(mainframe)
            frame.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px solid black; }"
            )
            self.sim_skill_frames.append(frame)

            name = QLabel(texts[i], frame)
            name.setGeometry(
                0,
                0,
                self.sim_skill_width,
                self.sim_skill_name_H,
            )
            name.setStyleSheet(
                f"QLabel {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
            )
            name.setFont(QFont("나눔스퀘어라운드 Bold", 14))
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim_skill_names.append(name)

            label = QLabel("레벨", frame)
            label.setGeometry(
                self.sim_skill_image_Size,
                self.sim_skill_name_H,
                self.sim_skill_right_W,
                self.sim_skill_level_H,
            )
            label.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sim_skill_levels.append(label)

            lineEdit = QLineEdit("", frame)
            lineEdit.setFont(QFont("나눔스퀘어라운드 Bold", 12))
            lineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lineEdit.setStyleSheet(
                f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
            )
            lineEdit.setGeometry(
                self.sim_skill_image_Size,
                self.sim_skill_name_H + self.sim_skill_level_H,
                self.sim_skill_right_W,
                self.sim_skill_input_H,
            )
            self.sim1_skill_inputs.append(lineEdit)

        for i in range(8):
            image = QPushButton(self.sim_skill_frames[i])
            image.setGeometry(
                0,
                self.sim_skill_name_H,
                self.sim_skill_image_Size,
                self.sim_skill_image_Size,
            )
            image.setStyleSheet(
                "QPushButton { background-color: transparent; border: 0px solid; }"
            )
            pixmap = QPixmap(self.getSkillImage(i))
            image.setIcon(QIcon(pixmap))
            image.setIconSize(
                QSize(self.sim_skill_image_Size, self.sim_skill_image_Size)
            )
            self.sim_skill_images.append(image)

    def sim_make_StatInput(self, mainframe):
        texts = [
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
            "신속",
            "체력",
            "공격속도",
            "포션회복량",
            "운",
            "경험치획득량",
        ]

        self.sim_stat_frames = []
        self.sim_stat_labels = []
        self.sim_stat_inputs = []
        for i in range(18):
            frame = QFrame(mainframe)
            frame.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px solid; }"
            )
            self.sim_stat_frames.append(frame)

            label = QLabel(texts[i], frame)
            label.setGeometry(
                0,
                0,
                self.sim_stat_width,
                self.sim_stat_label_H,
            )
            label.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
            self.sim_stat_labels.append(label)

            lineEdit = QLineEdit("", frame)
            lineEdit.setFont(QFont("나눔스퀘어라운드 Bold", 16))
            lineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lineEdit.setStyleSheet(
                f"QLineEdit {{ background-color: {self.sim_input_colors[0]}; border: 1px solid {self.sim_input_colors[1]}; border-radius: 4px; }}"
            )
            lineEdit.setGeometry(
                0, self.sim_stat_label_H, self.sim_stat_width, self.sim_stat_input_H
            )
            self.sim_stat_inputs.append(lineEdit)

    def getSimulatedSKillList(self):
        self.initMacro()
        self.elapsedTime = 0.0
        self.usedSkillList = []
        self.skillCoolTimers = [  # size: 사용 가능 스킬 개수 * 콤보개수
            [self.delay * 0.001]
            * self.skillComboCountList[self.serverID][self.jobID][
                self.selectedSkillList[i]
            ]
            for i in range(self.usableSkillCount[self.serverID])
        ]  # isUsed이면 self.unitTime씩 증가, 쿨타임이 지나면 0으로 초기화

        self.availableSkillCount = [
            [False]
            * self.skillComboCountList[self.serverID][self.jobID][
                self.selectedSkillList[i]
            ]
            for i in range(self.usableSkillCount[self.serverID])
        ]  # 스킬을 사용해서 쿨타임을 기다림

        while self.elapsedTime <= 65.0:
            self.addTaskList()
            passedTime, usedSkill = self.useSkill(self.loopNum, True)  # skill: slot
            self.elapsedTime += passedTime

            if usedSkill != None:
                # self.usedSkillList.append(
                #     [usedSkill, round(self.elapsedTime - self.delay * 0.001, 2)]
                # )
                pass
            else:
                self.elapsedTime += self.unitTime

            for skill in range(self.usableSkillCount[self.serverID]):
                for count in range(
                    self.skillComboCountList[self.serverID][self.jobID][
                        self.selectedSkillList[skill]
                    ]
                ):
                    if self.availableSkillCount[skill][count]:
                        if usedSkill == None:
                            self.skillCoolTimers[skill][count] += self.unitTime
                        self.skillCoolTimers[skill][count] += passedTime

                        if self.skillCoolTimers[skill][count] >= self.skillCooltimeList[
                            self.serverID
                        ][self.jobID][self.selectedSkillList[skill]] * (
                            1 - self.cooltimeReduce * 0.01
                        ):
                            self.preparedSkillList[2].append(skill)
                            self.availableSkillCount[skill][count] = False
                            self.skillCoolTimers[skill][count] = 0.0

        self.usedSkillList = [i for i in self.usedSkillList if i[1] <= 60.0]
        return self.usedSkillList

    ## 매크로 메인 쓰레드
    def runMacro(self, loopNum):
        self.initMacro()

        # 스킬 남은 쿨타임 : [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.skillCoolTimers = [0.0] * self.usableSkillCount[
            self.serverID
        ]  # isUsed이면 self.unitTime씩 증가, 쿨타임이 지나면 0으로 초기화

        # 스킬 사용 가능 횟수 : [3, 2, 2, 1, 3, 3]
        self.availableSkillCount = [
            self.skillComboCountList[self.serverID][self.jobID][
                self.selectedSkillList[i]
            ]
            for i in range(self.usableSkillCount[self.serverID])
        ]

        while self.isActivated and self.loopNum == loopNum:  # 매크로 작동중일 때
            self.addTaskList()  # taskList에 사용 가능한 스킬 추가
            passedTime, usedSkill = self.useSkill(
                loopNum
            )  # 스킬 사용하고 시간, 사용한 스킬 리턴. skill: slot

            # 잠수면 매크로 중지
            if self.isAFKEnabled:
                if time.time() - self.afkTime0 >= 10:
                    self.isActivated = False

            # 스킬 사용 안했으면 슬립
            if usedSkill == None:
                time.sleep(self.unitTime * self.sleepCoefficient)

            for skill in range(self.usableSkillCount[self.serverID]):  # 0~6
                if (
                    self.availableSkillCount[skill]
                    < self.skillComboCountList[self.serverID][self.jobID][
                        self.selectedSkillList[skill]
                    ]
                ):  # 스킬 사용해서 쿨타임 기다리는 중이면
                    if usedSkill == None:
                        self.skillCoolTimers[skill] += self.unitTime
                    self.skillCoolTimers[skill] += passedTime

                    if round(self.skillCoolTimers[skill], 3) >= self.skillCooltimeList[
                        self.serverID
                    ][self.jobID][self.selectedSkillList[skill]] * (
                        1 - self.cooltimeReduce * 0.01
                    ):  # 쿨타임이 지나면
                        self.preparedSkillList[2].append(skill)
                        self.availableSkillCount[skill] += 1
                        self.skillCoolTimers[skill] = 0.0

            # print(f"{usedSkill} 사용")
            # for i in range(6):
            #     print(
            #         f"{self.availableSkillCount[i]} / {self.skillComboCountList[self.serverID][self.jobID][
            #         self.selectedSkillList[i]
            #     ]} : {self.skillCoolTimers[i]} / {self.skillCooltimeList[self.serverID][self.jobID][self.selectedSkillList[i]] * (1 - self.cooltimeReduce * 0.01)}"
            #     )
            # print()

    def initMacro(self):
        self.selectedItemSlot = -1
        self.afkTime0 = time.time()

        self.preparedSkillList = [  # 0~5
            [
                i
                for i in range(6)
                if not self.ifUseSkill[self.selectedSkillList[i]]
                and self.selectedSkillList[i] != -1
            ],
            [
                i
                for i in range(6)
                if self.ifUseSkill[self.selectedSkillList[i]]
                and self.selectedSkillList[i] != -1
            ],
            [],  # append 대기
        ]
        self.preparedSkillCountList = [  # 0~5
            [
                self.skillComboCountList[self.serverID][self.jobID][
                    self.selectedSkillList[i]
                ]
                for i in range(6)
                if not self.ifUseSkill[self.selectedSkillList[i]]
                and self.selectedSkillList[i] != -1
            ],
            [
                self.skillComboCountList[self.serverID][self.jobID][
                    self.selectedSkillList[i]
                ]
                for i in range(6)
                if self.ifUseSkill[self.selectedSkillList[i]]
                and self.selectedSkillList[i] != -1
            ],
        ]
        self.preparedSkillComboList = [  # 0~5
            self.comboCount[self.selectedSkillList[i]] for i in range(6)
        ]

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
                    self.linkSkillComboRequirementList[-1].append(
                        self.usingLinkSkillComboList[i][x]
                    )
                else:
                    for k, l in enumerate(self.linkSkillRequirementList[-1]):
                        if l == y:
                            self.linkSkillComboRequirementList[-1][
                                k
                            ] += self.usingLinkSkillComboList[i][x]

        self.preparedLinkSkillList = list(range(len(self.usingLinkSkillList)))

        self.taskList = []
        # self.printMacroInfo(brief=False)

    def useSkill(self, loopNum, returnSkillOrder=False):
        """taskList에 있는 스킬 사용"""

        def press(key):
            if self.isActivated and self.loopNum == loopNum and not returnSkillOrder:
                kb.press(key)

        def click(b=True):
            if b:
                # self.usedSkillList.append(
                #     [-1, round(self.elapsedTime + self.passedTime, 2)]
                # )

                self.passedTime += pag.PAUSE
                if (
                    self.isActivated
                    and self.loopNum == loopNum
                    and not returnSkillOrder
                ):
                    pag.click()

        def use():
            # self.usedSkillList.append(
            #     [skill, round(self.elapsedTime + self.passedTime, 2)]
            # )

            self.availableSkillCount[skill] -= 1

        self.passedTime = 0.0

        if len(self.taskList) != 0:
            skill = self.taskList[0][0]  # skill = slot
            doClick = self.taskList[0][1]  # T, F
            key = self.skillKeys[skill]
            key = self.key_dict[key] if key in self.key_dict else key

            if self.selectedItemSlot != skill:
                if doClick:
                    press(key)
                    click(self.activeMouseClickSlot)
                    if not returnSkillOrder:
                        time.sleep(self.delay * 0.001 * self.sleepCoefficient)
                    self.passedTime += self.delay * 0.001
                    click()
                    use()
                    self.selectedItemSlot = skill
                else:
                    press(key)
                    click(self.activeMouseClickSlot)
                    use()
                    self.selectedItemSlot = skill
            else:
                if doClick:
                    click()
                    use()
                else:
                    press(key)
                    click(self.activeMouseClickSlot)
                    use()

            self.taskList.pop(0)
            if not returnSkillOrder:
                time.sleep(self.delay * 0.001 * self.sleepCoefficient)
            self.passedTime += self.delay * 0.001
            return self.passedTime, skill
        else:
            click(self.activeMouseClickSlot)
            return self.passedTime, None

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
                    time.sleep(self.delay * 0.001 * self.sleepCoefficient)
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
                                        self.taskList.append(
                                            [skill, True]
                                        )  # skill: k, click: True
                                    else:
                                        self.taskList.append(
                                            [skill, False]
                                        )  # skill: k, click: False
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
                                if self.isSkillCasting[self.serverID][self.jobID][
                                    self.selectedSkillList[k]
                                ]:
                                    self.taskList.append(
                                        [k, True]
                                    )  # skill: k, click: True
                                else:
                                    self.taskList.append(
                                        [k, False]
                                    )  # skill: k, click: False
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
                        while (
                            self.preparedSkillCountList[1][j]
                            >= self.preparedSkillComboList[i]
                        ):
                            for _ in range(self.preparedSkillComboList[i]):
                                if self.isSkillCasting[self.serverID][self.jobID][
                                    self.selectedSkillList[k]
                                ]:
                                    self.taskList.append(
                                        [k, True]
                                    )  # skill: k, click: True
                                else:
                                    self.taskList.append(
                                        [k, False]
                                    )  # skill: k, click: False
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
            print(
                "준비된 스킬 리스트:", self.preparedSkillList
            )  # 사용여부 x, 사용여부 o
            print(
                "준비된 스킬 개수 리스트:", self.preparedSkillCountList
            )  # 사용여부 x, 사용여부 o
            print("준비된 연계스킬리스트:", self.preparedLinkSkillList)
        else:
            print(
                "준비된 스킬 리스트:", self.preparedSkillList
            )  # 사용여부 x, 사용여부 o
            print(
                "준비된 스킬 개수 리스트:", self.preparedSkillCountList
            )  # 사용여부 x, 사용여부 o
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
        if e.key() == Qt.Key.Key_Escape:
            if self.isTabRemovePopupActivated:
                self.onTabRemovePopupClick(0, False)
            elif self.activeErrorPopupCount >= 1:
                self.removeNoticePopup()
            elif self.activePopup != "":
                self.disablePopup()
        elif e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if e.key() == Qt.Key.Key_W and not self.isTabRemovePopupActivated:
                self.onTabRemoveClick(self.recentPreset)
        elif e.key() == Qt.Key.Key_Return:
            if self.isTabRemovePopupActivated:
                self.onTabRemovePopupClick(self.recentPreset)
            elif self.activePopup == "settingDelay":
                self.onInputPopupClick("delay")
            elif self.activePopup == "settingCooltime":
                self.onInputPopupClick("cooltime")
            elif self.activePopup == "changeTabName":
                self.onInputPopupClick(("tabName", self.recentPreset))
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
    def resetVar(self):
        self.defaultWindowWidth = 960
        self.defaultWindowHeight = 540

        self.icon = QIcon(QPixmap(convertResourcePath("resource\\icon.ico")))
        self.icon_on = QIcon(QPixmap(convertResourcePath("resource\\icon_on.ico")))

        # pag.PAUSE = 0.01  # pag click delay 설정
        self.sleepCoefficient = (
            0.97  # 이 계수를 조정하여 time.sleep과 실제 시간 간의 괴리를 조정
        )
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
        self.skillNameList = [
            [
                [
                    "월성검법",
                    "수류검법",
                    "섬광베기",
                    "월성경공",
                    "월광검법",
                    "기합",
                    "청무흑검",
                    "섬극난무",
                ],
                [
                    "매화노방",
                    "매개이도",
                    "매화낙섬",
                    "매화낙락",
                    "매화분분",
                    "매인설한",
                    "운기",
                    "매화만리향",
                ],
                [
                    "급마살",
                    "겁속살투",
                    "극독무격",
                    "암행술",
                    "회극살투",
                    "혈마검법",
                    "삼천극",
                    "적월혈무",
                ],
                [
                    "흑무참",
                    "암자영참",
                    "비연참",
                    "음영천유",
                    "천강격류",
                    "천지극참",
                    "유성격참",
                    "검우무진",
                ],
                [
                    "열화주",
                    "낙뢰",
                    "회복진",
                    "이형환위",
                    "격뢰성진",
                    "삼매진화",
                    "열화지옥",
                    "협성마공",
                ],
                [
                    "파광부적",
                    "환공홍매",
                    "영기회생",
                    "천상제",
                    "부폭지술",
                    "무혼절기",
                    "연공지폭",
                    "선무회생",
                ],
                [
                    "빙정관사",
                    "삼로빙사",
                    "빙화연사",
                    "발궁순행",
                    "빙옥수렴",
                    "빙설극각",
                    "순행빙결",
                    "혹한비조",
                ],
                [
                    "이중연섬",
                    "풍력격퇴",
                    "명환진궁",
                    "일보퇴격",
                    "둔속사화",
                    "유선속발",
                    "연공신촉",
                    "극력일사",
                ],
            ]
        ]
        self.skillCooltimeList = [[[8] * 8] * 8]
        # self.skillCooltimeList = [
        #     [
        #         [3.0, 5.0, 6.0, 4.0, 4.0, 3.0, 5.0, 7.0],
        #         [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        #         [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        #         [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        #         [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        #         [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        #         [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        #         [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        #     ]
        # ]
        self.skillComboCountList = [
            [
                [3, 2, 2, 1, 3, 1, 1, 3],
                [2, 3, 2, 1, 1, 2, 1, 1],
                [2, 2, 1, 1, 2, 3, 3, 1],
                [1, 3, 1, 1, 1, 3, 1, 1],
                [3, 2, 2, 1, 1, 3, 1, 1],
                [3, 1, 1, 1, 2, 1, 1, 1],
                [2, 2, 1, 1, 1, 1, 1, 1],
                [2, 2, 1, 1, 2, 2, 1, 1],
            ]
        ]
        self.isSkillCasting = [
            [
                [True, True, False, False, True, False, False, True],
                [True, True, True, False, False, True, False, True],
                [True, True, False, False, True, True, True, True],
                [True, True, False, False, True, True, False, True],
                [True, True, False, False, True, False, True, False],
                [False, True, False, False, True, True, False, True],
                [True, True, False, False, True, True, False, True],
                [True, True, False, False, True, True, True, True],
            ]
        ]

    ## 기본 폰트 설정
    def setDefaultFont(self):
        QFontDatabase.addApplicationFont(convertResourcePath("font\\NSR_L.ttf"))
        QFontDatabase.addApplicationFont(convertResourcePath("font\\NSR_R.ttf"))
        QFontDatabase.addApplicationFont(convertResourcePath("font\\NSR_B.ttf"))
        QFontDatabase.addApplicationFont(convertResourcePath("font\\NSR_RB.ttf"))
        # "나눔스퀘어라운드 Light"
        # "나눔스퀘어라운드 Regular"
        # "나눔스퀘어라운드 Bold"
        # "나눔스퀘어라운드 ExtraBold"
        font_path = convertResourcePath("font\\NSR_B.ttf")
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        plt.rcParams["font.family"] = prop.get_name()

    ## 위젯 크기에 맞는 폰트로 변경
    def adjustFontSize(self, label, text, maxSize):
        label.setText(text)

        width = label.width()
        height = label.height()

        size = 1

        font = QFont("나눔스퀘어라운드 ExtraBold")
        font.setBold(True)
        font.setPointSize(size)
        label.setFont(font)

        while (
            label.fontMetrics().boundingRect(text).width() < width
            and (
                label.fontMetrics().boundingRect(text).height() * 2.6
                if "\n" in text
                else label.fontMetrics().boundingRect(text).height()
            )
            < height
            and size <= maxSize
        ):
            font.setPointSize(size)
            label.setFont(font)
            size += 1
            # print(label.fontMetrics().boundingRect(text).width(), width)

        size -= 6 if (text.isdigit() or text.isupper()) else 3
        size = size + 3 if "\n" in text else size
        font.setPointSize(size)
        label.setFont(font)

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
        self.backPalette = self.palette()
        self.backPalette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        self.setPalette(self.backPalette)
        self.page1 = QFrame(self)
        self.page2 = QFrame(self)

        self.labelCreator = QPushButton(
            "제작자: 프로데이즈  |  디스코드: prodays", self
        )
        self.labelCreator.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.labelCreator.setStyleSheet(
            "background-color: transparent; text-align: left; border: 0px;"
        )
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
            tabRemoveButton.clicked.connect(
                partial(lambda x: self.onTabRemoveClick(x), tabNum)
            )
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
            pixmap = QPixmap(convertResourcePath("resource\\x.png"))
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
        pixmap = QPixmap(convertResourcePath("resource\\plus.png"))
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
            frame.setStyleSheet(
                "QFrame { background-color: transparent; border-radius :0px; }"
            )
            frame.setFixedSize(64, 88)
            frame.move(50 + 132 * (i % 4), 80 + 120 * (i // 4))
            frame.show()
            self.selectableSkillFrame.append(frame)
        self.selectableSkillImageButton = []
        self.selectableSkillImageName = []
        for i, j in enumerate(self.selectableSkillFrame):
            button = QPushButton(j)
            button.setStyleSheet(
                "QPushButton { background-color: #bbbbbb; border-radius :10px; }"
            )
            button.clicked.connect(partial(lambda x: self.onSelectableSkillClick(x), i))
            button.setFixedSize(64, 64)
            pixmap = QPixmap(self.getSkillImage(i))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(64, 64))
            button.show()
            self.selectableSkillImageButton.append(button)

            label = QLabel(self.skillNameList[self.serverID][self.jobID][i], j)
            label.setStyleSheet(
                "QLabel { background-color: transparent; border-radius :0px; }"
            )
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
            frame.setStyleSheet(
                "QFrame { background-color: transparent; border-radius :0px; }"
            )
            frame.setFixedSize(64, 96)
            frame.move(38 + 84 * i, 330)
            frame.show()
            self.selectedSkillFrame.append(frame)
        self.selectedSkillImageButton = []
        self.selectedSkillKey = []
        for i, j in enumerate(self.selectedSkillFrame):
            button = QPushButton(j)
            self.selectedSkillColors = [
                "#8BC28C",
                "#FF626C",
                "#96C0FF",
                "#FFA049",
                "#F18AAD",
                "#8E8FE0",
            ]
            button.setStyleSheet(
                f"QPushButton {{ background-color: {self.selectedSkillColors[i]}; border-radius :10px; }}"
            )
            button.clicked.connect(partial(lambda x: self.onSelectedSkillClick(x), i))
            button.setFixedSize(64, 64)
            if self.selectedSkillList[i] != -1:
                pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[i]))
            else:
                pixmap = QPixmap(convertResourcePath("resource\\emptySkill.png"))
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
        self.sidebarFrame.setPalette(self.backPalette)
        self.sidebarScrollArea = QScrollArea(self.page1)
        self.sidebarScrollArea.setWidget(self.sidebarFrame)
        self.sidebarScrollArea.setFixedSize(319, self.height() - 24)
        self.sidebarScrollArea.setStyleSheet(
            "QScrollArea { border: 0px solid black; border-radius: 10px; }"
        )
        self.sidebarScrollArea.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.sidebarScrollArea.setPalette(self.backPalette)
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
            pixmap = QPixmap(convertResourcePath("resource\\emptySkill.png"))
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
                self.settingSkillImages[self.selectedSkillList[num]].setIcon(
                    QIcon(pixmap)
                )
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
                pixmap = QPixmap(
                    self.getSkillImage(
                        self.selectedSkillList[self.isSkillSelecting], "off"
                    )
                )
                self.settingSkillImages[
                    self.selectedSkillList[self.isSkillSelecting]
                ].setIcon(QIcon(pixmap))
                self.settingSkillSequences[
                    self.selectedSkillList[self.isSkillSelecting]
                ].setText("-")

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
                pixmap = QPixmap(
                    self.getSkillImage(
                        self.selectedSkillList[self.taskList[i][0]], "off"
                    )
                )
            else:
                pixmap = QPixmap(
                    self.getSkillImage(self.selectedSkillList[self.taskList[i][0]], 1)
                )
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
                pixmap = QPixmap(convertResourcePath("resource\\setting.png"))
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
                pixmap = QPixmap(convertResourcePath("resource\\usageSetting.png"))
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
                pixmap = QPixmap(convertResourcePath("resource\\linkSetting.png"))
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
                pixmap = QPixmap(convertResourcePath("resource\\simulationSidebar.png"))
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
            self.adjustFontSize(label, texts[i], 20)
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
                pixmap = QPixmap(convertResourcePath("resource\\checkTrue.png"))
            else:
                pixmap = QPixmap(convertResourcePath("resource\\checkFalse.png"))
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
                pixmap = QPixmap(convertResourcePath("resource\\checkTrue.png"))
            else:
                pixmap = QPixmap(convertResourcePath("resource\\checkFalse.png"))
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
            button.clicked.connect(
                partial(lambda x: self.onSkillComboCountsClick(x), i)
            )
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
                    button.setStyleSheet(
                        "QPushButton { background-color: transparent;}"
                    )
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
                    button.setStyleSheet(
                        "QPushButton { background-color: transparent;}"
                    )
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
                    button.setStyleSheet(
                        "QPushButton { background-color: transparent;}"
                    )
                    button.setFixedSize(25, 25)
                    button.move(18 + 25 * k, 201 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)
                for k in range(line2):
                    button = QPushButton("", self.sidebarFrame)
                    pixmap = QPixmap(
                        self.getSkillImage(j[2][k + line1][0], j[2][k + line1][1])
                    )
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(24, 24))
                    button.setStyleSheet(
                        "QPushButton { background-color: transparent;}"
                    )
                    button.setFixedSize(25, 25)
                    button.move(18 + 25 * k, 226 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)

            button = QPushButton(j[1], self.sidebarFrame)
            button.setStyleSheet(
                "QPushButton { background-color: transparent; border: 0px; }"
            )
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
            pixmap = QPixmap(convertResourcePath("resource\\x.png"))
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
        self.labelLinkKey.setToolTip(
            "매크로가 실행 중이지 않을 때 해당 연계스킬을 작동시킬 단축키입니다."
        )
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
            skill.clicked.connect(
                partial(lambda x: self.editLinkSkillType(x), (data, i))
            )
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
            button.clicked.connect(
                partial(lambda x: self.editLinkSkillCount(x), (data, i))
            )
            button.setFixedSize(50, 30)
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.move(210, 290 + 51 * i)
            button.show()
            self.linkSkillCount.append(button)

            remove = QPushButton("", self.sidebarFrame)
            remove.clicked.connect(
                partial(lambda x: self.removeOneLinkSkill(x), (data, i))
            )
            remove.setStyleSheet(
                """QPushButton {
                    background-color: transparent; border-radius: 16px;
                }
                QPushButton:hover {
                    background-color: #eeeeee;
                }"""
            )
            pixmap = QPixmap(convertResourcePath("resource\\xAlpha.png"))
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
        pixmap = QPixmap(convertResourcePath("resource\\plus.png"))
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
        self.linkSkillSaveButton.clicked.connect(
            lambda: self.saveEditingLinkSkill(data)
        )
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
        self.settingPopupFrame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 10px; }"
        )
        self.settingPopupFrame.setFixedSize(185, 95)
        self.settingPopupFrame.move(100, 285 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
        self.settingPopupFrame.show()

        for i in range(8):
            button = QPushButton("", self.settingPopupFrame)
            pixmap = QPixmap(
                self.getSkillImage(i)
                if i in self.selectedSkillList
                else self.getSkillImage(i, "off")
            )
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(40, 40))
            button.clicked.connect(
                partial(lambda x: self.oneLinkSkillTypePopupClick(x), (data, num, i))
            )
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
        self.settingPopupFrame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 10px; }"
        )
        self.settingPopupFrame.setFixedSize(5 + 35 * count, 40)
        self.settingPopupFrame.move(200 - 35 * count, 285 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
        self.settingPopupFrame.show()

        for i in range(1, count + 1):
            button = QPushButton(str(i), self.settingPopupFrame)
            button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            button.clicked.connect(
                partial(lambda x: self.onLinkSkillCountPopupClick(x), (data, num, i))
            )
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
            pixmap = QPixmap(convertResourcePath("resource\\checkFalse.png"))
            self.settingSkillUsages[num].setIcon(QIcon(pixmap))
            self.ifUseSkill[num] = False

            # for i, j in enumerate(self.linkSkillList):
            #     for k in j[2]:
            #         if k[0] == num:
            #             self.linkSkillList[i][0] = 1
        else:
            pixmap = QPixmap(convertResourcePath("resource\\checkTrue.png"))
            self.settingSkillUsages[num].setIcon(QIcon(pixmap))
            self.ifUseSkill[num] = True
        self.dataSave()

    ## 스킬 사용설정 -> 콤보 여부 클릭
    def onSkillCombosClick(self, num):
        self.disablePopup()
        if self.ifUseSole[num]:
            pixmap = QPixmap(convertResourcePath("resource\\checkFalse.png"))
            self.settingSkillSingle[num].setIcon(QIcon(pixmap))
            self.ifUseSole[num] = False
        else:
            pixmap = QPixmap(convertResourcePath("resource\\checkTrue.png"))
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
        self.settingPopupFrame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 5px; }"
        )
        width = 4 + 36 * combo
        self.settingPopupFrame.setFixedSize(width, 40)
        self.settingPopupFrame.move(170 - width, 206 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 0, 30, 150))
        self.settingPopupFrame.show()

        for i in range(1, combo + 1):
            button = QPushButton(str(i), self.settingPopupFrame)
            button.clicked.connect(
                partial(lambda x: self.onSkillComboCountsPopupClick(x), (num, i))
            )
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
                f"resource\\skill\\{self.serverID}\\{self.jobID}\\{num}\\{self.skillComboCountList[self.serverID][self.jobID][num]}.png"
            )
        else:
            return convertResourcePath(
                f"resource\\skill\\{self.serverID}\\{self.jobID}\\{num}\\{count}.png"
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
            self.selectableSkillImageName[i].setText(
                self.skillNameList[self.serverID][self.jobID][i]
            )
        for i in range(6):
            if self.selectedSkillList[i] != -1:
                pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[i]))
            else:
                pixmap = QPixmap(convertResourcePath("resource\\emptySkill.png"))
            self.selectedSkillImageButton[i].setIcon(QIcon(pixmap))

        self.buttonServerList.setText(self.serverList[self.serverID])
        self.buttonJobList.setText(self.jobList[self.serverID][self.jobID])

        self.buttonInputDelay.setText(str(self.inputDelay))
        rgb = 153 if self.activeDelaySlot == 1 else 0
        self.buttonDefaultDelay.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )
        rgb = 153 if self.activeDelaySlot == 0 else 0
        self.buttonInputDelay.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )

        self.buttonInputCooltime.setText(str(self.inputCooltime))
        rgb = 153 if self.activeCooltimeSlot == 1 else 0
        self.buttonDefaultCooltime.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )
        rgb = 153 if self.activeCooltimeSlot == 0 else 0
        self.buttonInputCooltime.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )

        self.buttonInputStartKey.setText(str(self.inputStartKey))
        rgb = 153 if self.activeStartKeySlot == 1 else 0
        self.buttonDefaultStartKey.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )
        rgb = 153 if self.activeStartKeySlot == 0 else 0
        self.buttonInputStartKey.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )

        rgb = 153 if self.activeMouseClickSlot == 1 else 0
        self.button1stMouseType.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )
        rgb = 153 if self.activeMouseClickSlot == 0 else 0
        self.button2ndMouseType.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )

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
    def getShadow(
        self, first=5, second=5, radius=10, transparent=100
    ) -> QGraphicsDropShadowEffect:
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
                text = f"프로그램이 최신버전이 아닙니다.\n현재 버전: {version}, 최신버전: {self.recentVersion}"
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
        pixmap = QPixmap(convertResourcePath(f"resource\\{icon}.png"))
        noticePopupIcon.setIcon(QIcon(pixmap))
        noticePopupIcon.setIconSize(QSize(24, 24))
        noticePopupIcon.show()

        noticePopupLabel = QLabel(text, noticePopup)
        noticePopupLabel.setWordWrap(True)
        noticePopupLabel.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
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
        pixmap = QPixmap(convertResourcePath("resource\\x.png"))
        noticePopupRemove.setIcon(QIcon(pixmap))
        noticePopupRemove.setIconSize(QSize(24, 24))
        noticePopupRemove.show()

        self.activeErrorPopup.append(
            [noticePopup, frameHeight, self.activeErrorPopupNumber]
        )
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
    def makePopupInput(self, type):
        match type:
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
        self.settingPopupFrame.setStyleSheet(
            "background-color: white; border-radius: 10px;"
        )
        self.settingPopupFrame.setFixedSize(width, 40)
        self.settingPopupFrame.move(x, y)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 0, 30, 150))
        self.settingPopupFrame.show()

        match type:
            case "delay":
                default = str(self.inputDelay)
            case "cooltime":
                default = str(self.inputCooltime)
            case ("tabName", _):
                default = self.tabNames[self.recentPreset]
        self.settingPopupInput = QLineEdit(default, self.settingPopupFrame)
        self.settingPopupInput.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.settingPopupInput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.settingPopupInput.setStyleSheet(
            "border: 1px solid black; border-radius: 10px;"
        )
        self.settingPopupInput.setFixedSize(width - 70, 30)
        self.settingPopupInput.move(5, 5)
        self.settingPopupInput.setFocus()

        self.settingPopupButton = QPushButton("적용", self.settingPopupFrame)
        self.settingPopupButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.settingPopupButton.clicked.connect(lambda: self.onInputPopupClick(type))
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
    def onInputPopupClick(self, type):
        text = self.settingPopupInput.text()

        if type == "delay" or type == "cooltime":
            try:
                text = int(text)
            except:
                self.disablePopup()
                self.makeNoticePopup(
                    "delayInputError" if type == "delay" else "cooltimeInputError"
                )
                return

        match type:
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
                self.tabButtonList[type[1]].setText(" " + text)
                self.tabNames[type[1]] = text

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
            self.settingPopupFrame.setStyleSheet(
                "background-color: white; border-radius: 10px;"
            )
            self.settingPopupFrame.setFixedSize(130, 5 + 35 * len(self.serverList))
            self.settingPopupFrame.move(25, 240)
            self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
            self.settingPopupFrame.show()

            for i in range(len(self.serverList)):
                self.settingServerButton = QPushButton(
                    self.serverList[i], self.settingPopupFrame
                )
                self.settingServerButton.setFont(
                    QFont("나눔스퀘어라운드 ExtraBold", 12)
                )
                self.settingServerButton.clicked.connect(
                    partial(lambda x: self.onServerPopupClick(x), i)
                )
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
            self.settingPopupFrame.setStyleSheet(
                "background-color: white; border-radius: 10px;"
            )
            self.settingPopupFrame.setFixedSize(
                130, 5 + 35 * len(self.jobList[self.serverID])
            )
            self.settingPopupFrame.move(145, 240)
            self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
            self.settingPopupFrame.show()

            for i in range(len(self.jobList[self.serverID])):
                self.settingJobButton = QPushButton(
                    self.jobList[self.serverID][i], self.settingPopupFrame
                )
                self.settingJobButton.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
                self.settingJobButton.clicked.connect(
                    partial(lambda x: self.onJobPopupClick(x), i)
                )
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
                self.comboCount[i] = self.skillComboCountList[self.serverID][
                    self.jobID
                ][i]

            for i in range(8):
                pixmap = QPixmap(self.getSkillImage(i))
                self.selectableSkillImageButton[i].setIcon(QIcon(pixmap))
                self.selectableSkillImageName[i].setText(
                    self.skillNameList[self.serverID][self.jobID][i]
                )

            for i in range(6):
                if self.selectedSkillList[i] != -1:
                    pixmap = QPixmap(self.getSkillImage(self.selectedSkillList[i]))
                else:
                    pixmap = QPixmap(convertResourcePath("resource\\emptySkill.png"))
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
    def makeKeyboardPopup(self, type):
        def makePresetKey(key, row, column, disabled=False):
            button = QPushButton(key, self.settingPopupFrame)
            match type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
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
            button.setFixedSize(round(30 * xSizeMultiple), round(30 * ySizeMultiple))
            match column:
                case 0:
                    defaultX = round(115 * xSizeMultiple)
                case 1:
                    defaultX = round(5 * xSizeMultiple)
                case 2:
                    defaultX = round(50 * xSizeMultiple)
                case 3:
                    defaultX = round(60 * xSizeMultiple)
                case 4:
                    defaultX = round(80 * xSizeMultiple)
            defaultY = round(5 * ySizeMultiple)

            self.adjustFontSize(button, key, 20)
            button.move(
                defaultX + row * round(35 * xSizeMultiple),
                defaultY + column * round(35 * ySizeMultiple),
            )
            button.show()

        def makeKey(key, x, y, width, height, disabled=False):
            button = QPushButton(key, self.settingPopupFrame)
            match type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
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
            match type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
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

        xSizeMultiple = self.width() / 960
        ySizeMultiple = self.height() / 540

        self.settingPopupFrame = QFrame(self)
        self.settingPopupFrame.setStyleSheet(
            "background-color: white; border-radius: 10px;"
        )
        self.settingPopupFrame.setFixedSize(
            round(635 * xSizeMultiple), round(215 * ySizeMultiple)
        )
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
            x = round((5 + 35 * i) * xSizeMultiple)
            if i >= 1:
                x += round(15 * xSizeMultiple)
            if i >= 5:
                x += round(15 * xSizeMultiple)
            if i >= 9:
                x += round(15 * xSizeMultiple)

            if key == "Esc":
                makeKey(
                    key,
                    x,
                    round(5 * ySizeMultiple),
                    round(30 * xSizeMultiple),
                    round(30 * ySizeMultiple),
                    True,
                )
            else:
                makeKey(
                    key,
                    x,
                    round(5 * ySizeMultiple),
                    round(30 * xSizeMultiple),
                    round(30 * ySizeMultiple),
                    self.isKeyUsing(key),
                )

        row = 0
        column = 1
        for key in k1:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey(
            "Back",
            round(460 * xSizeMultiple),
            round(40 * ySizeMultiple),
            round(40 * xSizeMultiple),
            round(30 * ySizeMultiple),
            True,
        )

        makeKey(
            "Tab",
            round(5 * xSizeMultiple),
            round(75 * ySizeMultiple),
            round(40 * xSizeMultiple),
            round(30 * ySizeMultiple),
            self.isKeyUsing("Tab"),
        )
        row = 0
        column += 1
        for key in k2:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1

        makeKey(
            "Caps Lock",
            round(5 * xSizeMultiple),
            round(110 * ySizeMultiple),
            round(50 * xSizeMultiple),
            round(30 * ySizeMultiple),
            True,
        )
        row = 0
        column += 1
        for key in k3:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey(
            "Enter",
            round(445 * xSizeMultiple),
            round(110 * ySizeMultiple),
            round(55 * xSizeMultiple),
            round(30 * ySizeMultiple),
            self.isKeyUsing("Enter"),
        )

        makeKey(
            "Shift",
            round(5 * xSizeMultiple),
            round(145 * ySizeMultiple),
            round(70 * xSizeMultiple),
            round(30 * ySizeMultiple),
            self.isKeyUsing("Shift"),
        )
        row = 0
        column += 1
        for key in k4:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey(
            "Shift",
            round(430 * xSizeMultiple),
            round(145 * ySizeMultiple),
            round(70 * xSizeMultiple),
            round(30 * ySizeMultiple),
            self.isKeyUsing("Shift"),
        )

        makeKey(
            "Ctrl",
            round(5 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(45 * xSizeMultiple),
            round(30 * ySizeMultiple),
            self.isKeyUsing("Ctrl"),
        )
        makeImageKey(
            "Window",
            round(55 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(45 * xSizeMultiple),
            round(30 * ySizeMultiple),
            convertResourcePath("resource\\window"),
            round(32 * ySizeMultiple),
            0,
            True,
        )
        makeKey(
            "Alt",
            round(105 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(45 * xSizeMultiple),
            round(30 * ySizeMultiple),
            self.isKeyUsing("Alt"),
        )
        makeKey(
            "Space",
            round(155 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(145 * xSizeMultiple),
            round(30 * ySizeMultiple),
            self.isKeyUsing("Space"),
        )
        makeKey(
            "Alt",
            round(305 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(45 * xSizeMultiple),
            round(30 * ySizeMultiple),
            self.isKeyUsing("Alt"),
        )
        makeImageKey(
            "Window",
            round(355 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(45 * xSizeMultiple),
            round(30 * ySizeMultiple),
            convertResourcePath("resource\\window"),
            round(32 * ySizeMultiple),
            0,
            True,
        )
        makeKey(
            "Fn",
            round(405 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(45 * xSizeMultiple),
            round(30 * ySizeMultiple),
            True,
        )
        makeKey(
            "Ctrl",
            round(455 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(45 * xSizeMultiple),
            round(30 * ySizeMultiple),
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
                    round((530 + j1 * 35) * xSizeMultiple),
                    round((5 + 35 * i1) * ySizeMultiple),
                    round(30 * xSizeMultiple),
                    round(30 * ySizeMultiple),
                    self.isKeyUsing(j2),
                )

        makeImageKey(
            "Up",
            round(565 * xSizeMultiple),
            round(145 * ySizeMultiple),
            round(30 * xSizeMultiple),
            round(30 * ySizeMultiple),
            convertResourcePath("resource\\arrow"),
            round(16 * xSizeMultiple),
            0,
            self.isKeyUsing("Up"),
        )
        makeImageKey(
            "Left",
            round(530 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(30 * xSizeMultiple),
            round(30 * ySizeMultiple),
            convertResourcePath("resource\\arrow"),
            round(16 * xSizeMultiple),
            270,
            self.isKeyUsing("Left"),
        )
        makeImageKey(
            "Down",
            round(565 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(30 * xSizeMultiple),
            round(30 * ySizeMultiple),
            convertResourcePath("resource\\arrow"),
            round(16 * xSizeMultiple),
            180,
            self.isKeyUsing("Down"),
        )
        makeImageKey(
            "Right",
            round(600 * xSizeMultiple),
            round(180 * ySizeMultiple),
            round(30 * xSizeMultiple),
            round(30 * ySizeMultiple),
            convertResourcePath("resource\\arrow"),
            round(16 * xSizeMultiple),
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
        pixmap = QPixmap(convertResourcePath("resource\\x.png"))
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
        self.tabRemoveFrame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 20px; }"
        )
        self.tabRemoveFrame.setFixedSize(340, 140)
        self.tabRemoveFrame.move(
            round(self.width() * 0.5 - 170), round(self.height() * 0.5 - 60)
        )
        self.tabRemoveFrame.setGraphicsEffect(self.getShadow(2, 2, 20))
        self.tabRemoveFrame.show()

        self.tabRemoveNameLabel = QLabel("", self.tabRemoveFrame)
        self.tabRemoveNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabRemoveNameLabel.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
        self.tabRemoveNameLabel.setFixedSize(330, 30)
        self.tabRemoveNameLabel.setText(
            self.limitText(
                f'정말 "{self.tabNames[num]}', self.tabRemoveNameLabel, margin=5
            )
            + '"'
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
        self.settingJobButton.clicked.connect(
            lambda: self.onTabRemovePopupClick(num, False)
        )
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
                        self.tabRemoveList[i].clicked.connect(
                            partial(lambda x: self.onTabRemoveClick(x), i)
                        )

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
                    self.tabRemoveList[i].clicked.connect(
                        partial(lambda x: self.onTabRemoveClick(x), i)
                    )

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
                    self.tabRemoveList[i].clicked.connect(
                        partial(lambda x: self.onTabRemoveClick(x), i)
                    )

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
            self.skillPreviewFrame.setFixedSize(
                round(288 * (xMultSize + 1)), round(48 * (yMultSize + 1))
            )
            for i, j in enumerate(self.skillPreviewList):
                j.setFixedSize(
                    round((288 * (xMultSize + 1) / 6)), round(48 * (yMultSize + 1))
                )
                j.move(
                    round(
                        (
                            self.skillPreviewFrame.width()
                            - j.width() * len(self.skillPreviewList)
                        )
                        * 0.5
                    )
                    + j.width() * i,
                    0,
                )
                j.setIconSize(
                    QSize(min(j.width(), j.height()), min(j.width(), j.height()))
                )

            for i, j in enumerate(self.selectableSkillFrame):
                j.move(
                    round(
                        (50 + xAddedSize * 0.2)
                        + (64 + (68 + xAddedSize * 0.2)) * (i % 4)
                        - 64 * xMultSize * 0.5
                    ),
                    round(
                        (80 + yAddedSize * 0.3 + (120 + yAddedSize * 0.2) * (i // 4))
                        - 88 * yMultSize * 0.5
                    ),
                )
                j.setFixedSize(round(64 * (xMultSize + 1)), round(88 * (yMultSize + 1)))

            for i in self.selectableSkillImageButton:
                i.setFixedSize(round(64 * (xMultSize + 1)), round(64 * (yMultSize + 1)))
                i.setIconSize(
                    QSize(min(i.width(), i.height()), min(i.width(), i.height()))
                )
            for i, j in enumerate(self.selectableSkillImageName):
                j.move(0, round(64 * (yMultSize + 1)))
                j.setFixedSize(round(64 * (xMultSize + 1)), round(24 * (yMultSize + 1)))
                self.adjustFontSize(
                    j, self.skillNameList[self.serverID][self.jobID][i], 20
                )
            self.selectionSkillLine.move(20, round(309 + yAddedSize * 0.7))
            self.selectionSkillLine.setFixedSize(520 + xAddedSize, 1)
            for i, j in enumerate(self.selectedSkillFrame):
                j.move(
                    round(
                        (38 + xAddedSize * 0.1)
                        + (64 + (20 + xAddedSize * 0.16)) * i
                        - 64 * xMultSize * 0.5
                    ),
                    round(330 + yAddedSize * 0.9 - 96 * yMultSize * 0.5),
                )
                j.setFixedSize(round(64 * (xMultSize + 1)), round(96 * (yMultSize + 1)))
            for i in self.selectedSkillImageButton:
                i.setFixedSize(round(64 * (xMultSize + 1)), round(64 * (yMultSize + 1)))
                i.setIconSize(
                    QSize(min(i.width(), i.height()), min(i.width(), i.height()))
                )
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
                        self.limitText(
                            f" {self.tabNames[tabNum]}", self.tabButtonList[tabNum]
                        )
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
                        self.limitText(
                            f" {self.tabNames[tabNum]}", self.tabButtonList[tabNum]
                        )
                    )
                    self.tabRemoveList[tabNum].move(315 + width * (tabNum + 1), 25)
                    self.tabAddButton.move(self.width() - 80, 25)
                    # self.tabAddButton.move(350 + width * len(self.tabNames), 25)
                if self.activePopup == "changeTabName":
                    self.settingPopupFrame.move(360 + width * self.recentPreset, 80)

            if self.isTabRemovePopupActivated:
                self.tabRemoveBackground.setFixedSize(self.width(), self.height())
                self.tabRemoveFrame.move(
                    round(self.width() * 0.5 - 170), round(self.height() * 0.5 - 60)
                )
                self.tabRemoveBackground.raise_()

        else:  # 레이아웃 1 (계산기)
            deltaWidth = self.width() - self.defaultWindowWidth

            self.sim_navFrame.move(self.sim_margin + deltaWidth // 2, self.sim_margin)
            # self.sim_navFrame.setFixedWidth(self.width() - self.sim_margin * 2)
            # self.sim_navButtons[4].move(
            #     self.sim_navFrame.width() - self.sim_navHeight, 0
            # )
            self.sim_mainFrame.setFixedWidth(
                self.width() - self.scrollBarWidth - self.sim_margin * 2
            )
            self.sim_mainScrollArea.setFixedSize(
                self.width() - self.sim_margin,
                self.height()
                - self.labelCreator.height()
                - self.sim_navHeight
                - self.sim_margin * 2
                - self.sim_main1_D,
            )

            if self.simType == 1:  # 캐릭터 정보
                self.sim1_frame1.move(deltaWidth // 2, 0)
                self.sim1_frame2.move(
                    deltaWidth // 2,
                    self.sim1_frame1.y() + self.sim1_frame1.height() + self.sim_main_D,
                )
                # self.sim1_frame1.setFixedWidth(
                #     self.width() - self.scrollBarWidth - self.sim_margin * 2
                # )
                # self.sim1_frame1_labelFrame.setFixedWidth(self.sim1_frame1.width())
                # self.sim1_frame1_label.setFixedWidth(
                #     self.sim1_frame1.width() - self.sim_label_x,
                # )

                # margin, count = 21, 6
                # if count == 6:
                #     self.sim1_frame1.setFixedHeight(
                #         self.sim_title_H
                #         + (self.sim_widget_D + self.sim_stat_frame_H) * 3
                #     )
                # else:
                #     self.sim1_frame1.setFixedHeight(
                #         self.sim_title_H
                #         + (self.sim_widget_D + self.sim_stat_frame_H) * 2
                #     )
                # for i in range(18):
                #     self.sim_stat_frames[i].move(
                #         self.sim_stat_margin
                #         + self.sim_stat_width * (i % count)
                #         + margin * (i % count),
                #         self.sim1_frame1_labelFrame.height()
                #         + self.sim_widget_D * ((i // count) + 1)
                #         + self.sim_stat_frame_H * (i // count),
                #     )

                # self.sim1_frame2.move(
                #     0,
                #     self.sim1_frame1.y() + self.sim1_frame1.height() + self.sim_main_D,
                # )
                # self.sim1_frame2_labelFrame.setFixedWidth(self.sim_mainFrame.width())
                # self.sim1_frame2_label.setFixedWidth(
                #     self.sim_mainFrame.width() - self.sim_label_x,
                # )

                # margin, count = 66, 4
                # if count == 4:
                #     self.sim1_frame2.setFixedSize(
                #         self.sim_mainFrame.width(),
                #         self.sim_title_H
                #         + (self.sim_widget_D + self.sim_skill_frame_H) * 2,
                #     )
                # else:
                #     self.sim1_frame2.setFixedSize(
                #         self.sim_mainFrame.width(),
                #         self.sim_title_H
                #         + (self.sim_widget_D + self.sim_skill_frame_H) * 1,
                #     )
                # for i in range(8):
                #     self.sim_skill_frames[i].move(
                #         self.sim_skill_margin
                #         + self.sim_skill_width * (i % count)
                #         + margin * (i % count),
                #         self.sim1_frame2_labelFrame.height()
                #         + self.sim_widget_D * ((i // count) + 1)
                #         + self.sim_skill_frame_H * (i // count),
                #     )

                # # mainFrame
                # self.sim_mainFrame.setFixedHeight(
                #     self.sim1_frame2.y() + self.sim1_frame2.height(),
                # )

            elif self.simType == 2:  # 시뮬레이터
                self.sim2_frame1.move(deltaWidth // 2, 0)
                # self.sim2_frame1.setFixedWidth(
                #     self.width() - self.scrollBarWidth - self.sim_margin * 2
                # )
                # self.sim2_frame1_labelFrame.setFixedWidth(self.sim2_frame1.width())
                # self.sim2_frame1_label.setFixedWidth(
                #     self.sim2_frame1.width() - self.sim_label_x,
                # )
                self.sim2_frame2.move(
                    deltaWidth // 2,
                    self.sim2_frame1.y() + self.sim2_frame1.height() + self.sim_main_D,
                )
                # self.sim2_frame2.setFixedWidth(
                #     self.width() - self.scrollBarWidth - self.sim_margin * 2
                # )
                # self.sim2_frame2_labelFrame.setFixedWidth(self.sim2_frame2.width())
                # self.sim2_frame2_label.setFixedWidth(
                #     self.sim2_frame2.width() - self.sim_label_x,
                # )

                # for i, (f, t, n) in enumerate(self.sim_power_list):
                #     f.move(
                #         self.sim_powerL_margin
                #         + int(deltaWidth * self.sim_powerL_marginRate)
                #         + (
                #             self.sim_powerL_width
                #             + self.sim_powerL_D
                #             + int(
                #                 deltaWidth
                #                 * (self.sim_powerL_DRate + self.sim_powerL_WRate)
                #             )
                #         )
                #         * i,
                #         self.sim_label_H + self.sim_widget_D,
                #     )
                #     f.setFixedWidth(
                #         self.sim_powerL_width + int(deltaWidth * self.sim_powerL_WRate)
                #     )
                #     t.setFixedWidth(
                #         self.sim_powerL_width + int(deltaWidth * self.sim_powerL_WRate)
                #     )
                #     n.setFixedWidth(
                #         self.sim_powerL_width + int(deltaWidth * self.sim_powerL_WRate)
                #     )

                # for i, (f, c, l, n, d) in enumerate(self.sim_analysis_list):
                #     f.setGeometry(
                #         self.sim_analysis_margin
                #         + int(deltaWidth * self.sim_analysis_marginRate)
                #         + (
                #             self.sim_analysis_width
                #             + self.sim_analysis_D
                #             + int(
                #                 deltaWidth
                #                 * (self.sim_analysis_DRate + self.sim_analysis_WRate)
                #             )
                #         )
                #         * i,
                #         self.sim_label_H + self.sim_widget_D,
                #         self.sim_analysis_width
                #         + int(deltaWidth * self.sim_analysis_WRate),
                #         self.sim_analysis_frame_H,
                #     )
                #     l.setFixedWidth(
                #         self.sim_analysis_widthXC
                #         + int(deltaWidth * self.sim_analysis_WRate)
                #     )
                #     n.setFixedWidth(
                #         self.sim_analysis_widthXC
                #         + int(deltaWidth * self.sim_analysis_WRate)
                #     )

                #     for j, (df, dt, dn) in enumerate(d):
                #         df.setGeometry(
                #             self.sim_analysis_color_W
                #             + int(deltaWidth * self.sim_analysis_DetailRate)
                #             + self.sim_analysis_details_margin
                #             + (
                #                 self.sim_analysis_details_W
                #                 + int(deltaWidth * self.sim_analysis_DetailRate)
                #                 + self.sim_analysis_details_margin
                #             )
                #             * (j % 3)
                #             - 1,
                #             self.sim_analysis_title_H
                #             + self.sim_analysis_number_H
                #             + self.sim_analysis_number_marginH
                #             + self.sim_analysis_details_H * (j // 3),
                #             self.sim_analysis_details_W
                #             + int(deltaWidth * self.sim_analysis_DetailRate),
                #             self.sim_analysis_details_H,
                #         )

                # self.sim_dpsGraph_frame.setGeometry(
                #     self.sim_dps_margin + int(deltaWidth * self.sim_dps_marginRate),
                #     self.sim_label_H
                #     + self.sim_analysis_frame_H
                #     + self.sim_widget_D * 2,
                #     self.sim_dps_width + int(deltaWidth * self.sim_dps_WRate),
                #     self.sim_dps_height,
                # )
                # self.sim_dpsGraph.move(5, 5)
                # self.sim_dpsGraph.resize(
                #     self.sim_dps_width + int(deltaWidth * self.sim_dps_WRate) - 10,
                #     self.sim_dps_height - 10,
                # )

                # self.sim_skillDpsGraph_frame.setGeometry(
                #     self.sim_dps_margin
                #     + self.sim_dps_width
                #     + self.sim_skillDps_margin
                #     + int(deltaWidth * self.sim_skillDps_marginRate)
                #     + int(deltaWidth * self.sim_dps_marginRate)
                #     + int(deltaWidth * self.sim_dps_WRate),
                #     self.sim_label_H
                #     + self.sim_analysis_frame_H
                #     + self.sim_widget_D * 2,
                #     self.sim_skillDps_width + int(deltaWidth * self.sim_skillDps_WRate),
                #     self.sim_skillDps_height,
                # )
                # self.sim_skillDpsGraph.move(10, 10)
                # self.sim_skillDpsGraph.resize(
                #     self.sim_skillDps_width
                #     + int(deltaWidth * self.sim_skillDps_WRate)
                #     - 20,
                #     self.sim_skillDps_height - 20,
                # )

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
                        jsonObject["preset"][i]["name"]
                        for i in range(len(jsonObject["preset"]))
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
            else:
                self.dataMake()
                self.dataLoad()
        except:
            self.dataMake()
            self.dataLoad()

    ## 오류발생, 최초실행 시 데이터 생성
    def dataMake(self):
        jsonObject = {
            "recentPreset": 0,
            "preset": [
                {
                    "name": "스킬 매크로",
                    "skills": {
                        "activeSkills": [-1, -1, -1, -1, -1, -1],
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
                    "activeSkills": [-1, -1, -1, -1, -1, -1],
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
            }
        )

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
        counts, bins = np.histogram(self.data, bins=n_bins)
        bin_width = 0.9 * (bins[1] - bins[0])
        bars = self.ax.bar(bins[:-1], counts, width=bin_width, align="edge", bottom=0)

        # Customizing the plot similar to the image
        self.ax.set_title("DPS 분포")
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
        median_val = np.median(self.data)
        median_idx = np.digitize(median_val, bins) - 1
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


class SkillDpsDistributionCanvas(FigureCanvas):

    def __init__(self, parent, data):
        fig, self.ax = plt.subplots()
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)
        self.data = data
        self.plot()

    def plot(self):
        # Data for the pie chart
        labels = [f"스킬{i+1}: {j}%" for i, j in enumerate(self.data)]
        colors = ["#EF9A9A", "#90CAF9", "#A5D6A7", "#FFEB3B", "#CE93D8", "#FFA386"]

        # Plotting the pie chart
        wedges, texts = self.ax.pie(
            self.data,
            labels=labels,
            colors=colors,
            startangle=140,
            wedgeprops={"edgecolor": "black", "linewidth": 0.5},
        )

        # Customizing the plot
        self.ax.set_title("스킬 DPS")

        # Adjust text size
        for text in texts:
            text.set_fontsize(10)

        self.draw()


class DMGCanvas(FigureCanvas):

    def __init__(self, parent, data, type):
        fig, self.ax = plt.subplots()
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)
        self.data = data
        self.type = type
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
            linewidth=2,
        )
        (self.line3,) = self.ax.plot(
            self.data["time"],
            self.data["min"],
            label="최소",
            color="#80C080",
            linewidth=1,
        )

        if self.type == "time":
            self.ax.set_title("시간 경과에 따른 피해량")
            self.ax.set_ylabel("피해량")
        else:
            self.ax.set_title("누적 피해량")
            self.ax.set_ylabel("피해량")

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
            index = np.argmin(np.abs(self.data["time"] - x))
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

    def __init__(self, parent, data):
        fig, self.ax = plt.subplots(figsize=(8, 6))  # 명시적 크기 설정
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)

        # 캔버스 크기 설정
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        self.data = data

        self.plot()

    def plot(self):
        colors = ["#F38181", "#70AAF9", "#80C080", "#FCE38A", "#95E1D3", "#F4A259"]
        skill_names = ["스킬1", "스킬2", "스킬3", "스킬4", "스킬5", "스킬6"]

        self.lines = []
        for i, skill in enumerate(
            [
                "skill1_sum",
                "skill2_sum",
                "skill3_sum",
                "skill4_sum",
                "skill5_sum",
                "skill6_sum",
            ]
        ):
            (line,) = self.ax.plot(
                self.data["time"],
                self.data[skill],
                label=skill_names[i],
                color=colors[i],
                linewidth=2,
            )
            self.lines.append(line)

        # 영역 채우기
        for i in range(5, 0, -1):  # 4부터 1까지 역순으로
            self.ax.fill_between(
                self.data["time"],
                self.data[f"skill{i}_sum"],
                self.data[f"skill{i+1}_sum"],
                color=colors[i - 1],
            )  # 바로 위 선의 색상 사용

        # 맨 아래 영역 채우기
        self.ax.fill_between(
            self.data["time"], 0, self.data["skill1_sum"], color=colors[0]
        )
        self.ax.fill_between(
            self.data["time"], self.data["skill6_sum"], 1, color=colors[5]
        )

        self.ax.set_title("스킬별 기여도")
        self.ax.set_ylabel("기여도")
        self.ax.set_xlabel("시간 (초)")
        self.ax.grid(True, linestyle="--")
        self.ax.set_ylim(0, 1)  # y축 범위를 0부터 1로 설정
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
            index = np.argmin(np.abs(self.data["time"] - x))
            closest_x = self.data["time"][index]

            values = []
            for name, skill in [
                ("스킬1", "skill1"),
                ("스킬2", "skill2"),
                ("스킬3", "skill3"),
                ("스킬4", "skill4"),
                ("스킬5", "skill5"),
                ("스킬6", "skill6"),
            ]:
                values.append(f"{name}: {self.data[skill][index] * 100:.1f}%")

            self.annotation.xy = (x, y)
            self.annotation.set_text(f"시간: {closest_x:.1f}\n" + "\n".join(values))
            self.annotation.set_visible(True)
            self.draw_idle()
        else:
            self.annotation.set_visible(False)
            self.draw_idle()


if __name__ == "__main__":
    version = "v3.1.0-alpha.1"
    fileDir = "C:\\PDFiles\\PDSkillMacro.json"
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
