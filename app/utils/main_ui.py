from .data_manager import dataSave
from .misc import getSkillImage, convertResourcePath, adjustFontSize
from .shared_data import UI_Variable
from .simulate_macro import randSimulate, detSimulate, getRequiredStat
from .graph import DpsDistributionCanvas, SkillDpsRatioCanvas, DMGCanvas, SkillContributionCanvas
from .custom_widgets import *
from .get_character_data import get_character_info, get_character_card_data

import os
import requests
from functools import partial

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QPixmap, QPainter, QIcon
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QFileDialog, QScrollArea


class MainMacroUI:
    def __init__(self, parent, shared_data):
        self.shared_data = shared_data
        self.parent = parent

        self.ui_var = UI_Variable()

        self.make_ui()

    def make_ui(self):
        self.background = QFrame(self.parent)
        self.background.setStyleSheet(
            """QFrame { background-color: #eeeeff; border-top-left-radius :0px; border-top-right-radius : 30px; border-bottom-left-radius : 30px; border-bottom-right-radius : 30px }"""
        )
        self.background.setFixedSize(560, 450)
        self.background.move(360, 69)
        self.background.setGraphicsEffect(self.getShadow(0, 5, 20, 100))  # 나중에 수정

        self.tab_buttons = []
        self.tab_backgrounds = []
        self.tab_remove_buttons = []

        for tabNum in range(len(self.shared_data.tabNames)):
            # 탭 선택 버튼 배경
            background = QFrame("", self.parent)  # 나중에 self.background으로 수정
            background.setStyleSheet(
                f"""QFrame {{
                    background-color: {"#eeeeff" if tabNum == self.shared_data.recentPreset else "#dddddd"};
                    border-top-left-radius :20px;
                    border-top-right-radius : 20px;
                    border-bottom-left-radius : 0px;
                    border-bottom-right-radius : 0px;
                }}"""
            )
            background.setFixedSize(250, 50)
            background.move(360 + 250 * tabNum, 20)
            background.setGraphicsEffect(self.getShadow(5, -2))

            tab_button = QPushButton("", self.page1)  # 나중에 self.background으로 수정
            tab_button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 12))
            tab_button.setText(
                self.limitText(f" {self.shared_data.tabNames[tabNum]}", tab_button)
            )  # 나중에 수정
            tab_button.clicked.connect(partial(lambda x: self.onTabClick(x), tabNum))
            tab_button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {"#eeeeff" if tabNum == self.shared_data.recentPreset else "#dddddd"}; border-radius: 15px; text-align: left;
                    }}
                    QPushButton:hover {{
                        background-color: {"#fafaff" if tabNum == self.shared_data.recentPreset else "#eeeeee"};
                    }}
                """
            )
            tab_button.setFixedSize(240, 40)
            tab_button.move(365 + 250 * tabNum, 25)

            tab_remove_button = QPushButton("", self.page1)  # 나중에 self.background으로 수정
            tab_remove_button.clicked.connect(partial(lambda x: self.onTabRemoveClick(x), tabNum))
            tab_remove_button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 16))

            tab_remove_button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: transparent; border-radius: 20px;
                    }}
                    QPushButton:hover {{
                        background-color: {"#fafaff" if tabNum == self.shared_data.recentPreset else "#eeeeee"};
                    }}
                """
            )

            pixmap = QPixmap(convertResourcePath("resources\\image\\x.png"))
            tab_remove_button.setIcon(QIcon(pixmap))
            tab_remove_button.setFixedSize(40, 40)
            tab_remove_button.move(565 + 250 * tabNum, 25)

            self.tab_buttons.append(tab_button)
            self.tab_backgrounds.append(background)
            self.tab_remove_buttons.append(tab_remove_button)

        self.tab_add_button = QPushButton("", self.page1)  # 나중에 self.background으로 수정
        self.tab_add_button.clicked.connect(self.onTabAddClick)
        self.tab_add_button.setFont(QFont("나눔스퀘어라운드 ExtraBold", 16))
        self.tab_add_button.setStyleSheet(
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
        self.tab_add_button.setIcon(QIcon(pixmap))
        self.tab_add_button.setFixedSize(40, 40)
        self.tab_add_button.move(370 + 250 * len(self.shared_data.tabNames), 25)

        self.shared_data.layout_type = 0

        self.skill_preview_frame = QFrame(self.background)
        self.skill_preview_frame.setStyleSheet(
            "QFrame { background-color: #ffffff; border-radius :5px; border: 1px solid black; }"
        )
        self.skill_preview_frame.setFixedSize(288, 48)
        self.skill_preview_frame.move(136, 10)
        self.skill_preview_frame.show()
        # self.showSkillPreview()

        self.selectable_skill_frames = []
        for i in range(8):
            frame = QFrame(self.background)
            frame.setStyleSheet("QFrame { background-color: transparent; border-radius :0px; }")
            frame.setFixedSize(64, 88)
            frame.move(50 + 132 * (i % 4), 80 + 120 * (i // 4))
            frame.show()
            self.selectable_skill_frames.append(frame)

        self.selectable_skill_buttons = []
        self.selectable_skill_names = []
        for i, j in enumerate(self.selectable_skill_frames):
            button = QPushButton(j)
            button.setStyleSheet("QPushButton { background-color: #bbbbbb; border-radius :10px; }")
            button.clicked.connect(partial(lambda x: self.onSelectableSkillClick(x), i))
            button.setFixedSize(64, 64)
            button.setIcon(getSkillImage(self.shared_data, i))
            button.setIconSize(QSize(64, 64))
            button.show()

            label = QLabel(
                self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][i], j
            )
            label.setStyleSheet("QLabel { background-color: transparent; border-radius :0px; }")
            label.setFixedSize(64, 24)
            label.move(0, 64)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.show()

            self.selectable_skill_buttons.append(button)
            self.selectable_skill_names.append(label)

        self.selection_skill_line = QFrame(self.background)
        self.selection_skill_line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
        self.selection_skill_line.setFixedSize(520, 1)
        self.selection_skill_line.move(20, 309)
        self.selection_skill_line.show()

        self.selected_skill_frames = []
        for i in range(6):
            frame = QFrame(self.background)
            frame.setStyleSheet("QFrame { background-color: transparent; border-radius :0px; }")
            frame.setFixedSize(64, 96)
            frame.move(38 + 84 * i, 330)
            frame.show()
            self.selected_skill_frames.append(frame)

        self.selected_skill_buttons = []
        self.selected_skill_keys = []
        for i, j in enumerate(self.selected_skill_frames):
            button = QPushButton(j)
            button.setStyleSheet("QPushButton { background-color: #BBBBBB; border-radius :10px; }")
            button.clicked.connect(partial(lambda x: self.onSelectedSkillClick(x), i))
            button.setFixedSize(64, 64)
            button.setIcon(getSkillImage(self.shared_data, self.shared_data.selectedSkillList[i]))
            button.setIconSize(QSize(64, 64))
            button.show()

            button = QPushButton(self.shared_data.skillKeys[i], j)
            button.clicked.connect(partial(lambda x: self.onSkillKeyClick(x), i))
            button.setFixedSize(64, 24)
            button.move(0, 72)
            button.show()

            self.selected_skill_buttons.append(button)
            self.selected_skill_keys.append(button)


class Sidebar:
    def __init__(self, parent, shared_data):
        self.shared_data = shared_data
        self.parent = parent

        self.ui_var = UI_Variable()

        self.make_ui()

    def make_ui(self):
        # 설정 레이블
        self.frame = QFrame(self.page1)
        self.frame.setFixedSize(300, 790)
        self.frame.setStyleSheet("QFrame { background-color: #FFFFFF; }")
        # self.sidebarFrame.setPalette(self.backPalette)
        self.scroll_area = QScrollArea(self.page1)
        self.scroll_area.setWidget(self.frame)
        self.scroll_area.setFixedSize(319, self.height() - 24)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background-color: #FFFFFF; border: 0px solid black; border-radius: 10px; }"
        )
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        # self.sidebarScrollArea.setPalette(self.backPalette)
        self.scroll_area.show()

        ## 사이드바 옵션 아이콘
        self.option_frame = QFrame(self.page1)
        self.option_frame.setFixedSize(34, 136)
        self.option_frame.move(320, 20)

        self.option_button0 = self.getSidebarButton(0)
        self.option_button1 = self.getSidebarButton(1)
        self.option_button2 = self.getSidebarButton(2)
        self.option_button3 = self.getSidebarButton(3)

        self.settings_label = QLabel("", self.frame)
        self.settings_label.setFont(QFont("나눔스퀘어라운드 ExtraBold", 20))
        self.settings_label.setStyleSheet(
            "border: 0px solid black; border-radius: 10px; background-color: #CADEFC;"
        )
        self.settings_label.setFixedSize(200, 100)
        self.settings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.settings_label.move(50, 20)
        self.settings_label.setGraphicsEffect(self.getShadow())
