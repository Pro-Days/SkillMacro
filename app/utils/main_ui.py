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

    class SideBarButton(QPushButton):
        def __init__(self, parent, num):
            super().__init__("", parent)  # self.sidebarOptionFrame

            match num:
                case 0:
                    self.clicked.connect(self.changeSettingTo0)
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
                skill.setIcon(getSkillImage(self.shared_data, i))
            else:
                skill.setIcon(getSkillImage(self.shared_data, i, "off"))

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
                    button.setIcon(getSkillImage(self.shared_data, j["skills"][k][0], j["skills"][k][1]))
                    button.setIconSize(QSize(48, 48))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(50, 50)
                    button.move(18 + 50 * k, 201 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)
            elif imageCount <= 6:
                for k in range(len(j["skills"])):
                    button = QPushButton("", self.sidebarFrame)
                    button.setIcon(getSkillImage(self.shared_data, j["skills"][k][0], j["skills"][k][1]))
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
                    button.setIcon(getSkillImage(self.shared_data, j["skills"][k][0], j["skills"][k][1]))
                    button.setIconSize(QSize(24, 24))
                    button.setStyleSheet("QPushButton { background-color: transparent;}")
                    button.setFixedSize(25, 25)
                    button.move(18 + 25 * k, 201 + 51 * i)
                    button.show()
                    self.settingSkillPreview.append(button)
                for k in range(line2):
                    button = QPushButton("", self.sidebarFrame)
                    button.setIcon(
                        getSkillImage(self.shared_data, j["skills"][k + line1][0], j["skills"][k + line1][1])
                    )
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
            adjustFontSize(button, text, 20)
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
        adjustFontSize(self.ButtonLinkKey1, data["key"], 30)
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
            skill.setIcon(getSkillImage(self.shared_data, j[0], j[1]))
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
