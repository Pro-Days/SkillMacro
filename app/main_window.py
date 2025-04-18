from .utils.data_manager import *
from .utils.shared_data import *
from .utils.run_macro import *
from .utils.graph import *
from .utils.get_character_data import *
from .utils.misc import *
from .utils.simulate_macro import *
from .utils.simul_ui import *
from .utils.main_ui import *

import os
import sys
import copy
import requests

from threading import Thread
from webbrowser import open_new
from functools import partial

import matplotlib.pyplot as plt

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import (
    QPen,
    QFont,
    QIcon,
    QColor,
    QPixmap,
    QPainter,
    QPalette,
    QTransform,
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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        set_default_fonts()
        self.shared_data = SharedData()
        self.ui_var = UI_Variable()
        self.setWindowIcon(QIcon(QPixmap(convertResourcePath("resources\\image\\icon.ico"))))

        dataUpdate()
        dataLoad(self.shared_data)

        self.initUI()

        self.activateThread()

    ## 서브 쓰레드 실행
    def activateThread(self):
        Thread(target=check_kb_pressed, args=[self.shared_data], daemon=True).start()

        self.preview_timer = QTimer(self)
        self.preview_timer.singleShot(100, self.tick)

        self.version_timer = QTimer(self)
        self.version_timer.singleShot(100, self.checkVersionThread)

    def changeLayout(self, num):
        self.window_layout.setCurrentIndex(num)
        self.shared_data.layout_type = num

        if num == 0:
            self.removeSimulWidgets()
            [i.deleteLater() for i in self.page2.findChildren(QWidget)]
            self.updatePosition()

        elif num == 1:
            self.makePage2()

    def makePage2(self):
        # 상단바
        self.sim_navFrame = QFrame(self.page2)
        self.sim_navFrame.setGeometry(
            self.ui_var.sim_margin,
            self.ui_var.sim_margin,
            self.width() - self.ui_var.sim_margin * 2,
            self.ui_var.sim_navHeight,
        )
        self.sim_navFrame.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); }")

        self.sim_navButtons = []
        texts = ["정보 입력", "시뮬레이터", "스탯 계산기", "캐릭터 카드"]

        for i in range(4):
            button = QPushButton(texts[i], self.sim_navFrame)
            button.setGeometry(
                self.ui_var.sim_navBWidth * i, 0, self.ui_var.sim_navBWidth, self.ui_var.sim_navHeight
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
            self.ui_var.sim_navHeight,
            self.ui_var.sim_navHeight,
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
            self.ui_var.sim_margin,
            self.ui_var.sim_margin + self.ui_var.sim_navHeight + self.ui_var.sim_main1_D,
            self.width() - self.ui_var.scrollBarWidth - self.ui_var.sim_margin * 2,
            self.height()
            - self.creator_label.height()
            - self.ui_var.sim_navHeight
            - self.ui_var.sim_margin * 2
            - self.ui_var.sim_main1_D,
        )
        self.sim_mainFrame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.sim_mainScrollArea = QScrollArea(self.page2)
        self.sim_mainScrollArea.setWidget(self.sim_mainFrame)
        self.sim_mainScrollArea.setGeometry(
            self.ui_var.sim_margin,
            self.ui_var.sim_margin + self.ui_var.sim_navHeight + self.ui_var.sim_main1_D,
            self.width() - self.ui_var.sim_margin,
            self.height()
            - self.creator_label.height()
            - self.ui_var.sim_navHeight
            - self.ui_var.sim_margin * 2
            - self.ui_var.sim_main1_D,
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
        # 콤보박스 오류 수정
        if self.shared_data.sim_type == 3:
            comboboxList = [
                self.sim3_ui.efficiency_statL,
                self.sim3_ui.efficiency_statR,
                self.sim3_ui.potential_stat0,
                self.sim3_ui.potential_stat1,
                self.sim3_ui.potential_stat2,
            ]
            for i in comboboxList:
                i.showPopup()
                i.hidePopup()

        [i.deleteLater() for i in self.sim_mainFrame.findChildren(QWidget)]
        self.shared_data.sim_type = 0

        plt.close("all")
        plt.clf()

    def makeSimulType4(self):
        if not all(self.shared_data.inputCheck.values()):
            self.makeNoticePopup("SimInputError")
            return

        self.removeSimulWidgets()
        self.sim_updateNavButton(3)

        self.shared_data.sim_type = 4

        self.sim4_ui = Sim4UI(self.sim_mainFrame, self.shared_data)

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim4_ui.info_frame.y() + self.sim4_ui.info_frame.height() + self.ui_var.sim_mainFrameMargin,
        )
        [i.show() for i in self.page2.findChildren(QWidget)]
        self.updatePosition()

    def makeSimulType3(self):
        if not all(self.shared_data.inputCheck.values()):
            self.makeNoticePopup("SimInputError")
            return

        self.removeSimulWidgets()
        self.sim_updateNavButton(2)

        self.shared_data.sim_type = 3

        self.sim3_ui = Sim3UI(self.sim_mainFrame, self.shared_data)

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim3_ui.potentialRank_frame.y()
            + self.sim3_ui.potentialRank_frame.height()
            + self.ui_var.sim_mainFrameMargin,
        )
        [i.show() for i in self.sim3_ui.widgetList]
        self.updatePosition()

    def makeSimulType2(self):
        if not all(self.shared_data.inputCheck.values()):
            self.makeNoticePopup("SimInputError")
            return

        self.removeSimulWidgets()
        self.sim_updateNavButton(1)

        self.shared_data.sim_type = 2

        self.sim2_ui = Sim2UI(self.sim_mainFrame, self.shared_data)

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim2_ui.analysis_frame.y()
            + self.sim2_ui.analysis_frame.height()
            + self.ui_var.sim_mainFrameMargin,
        )
        [i.show() for i in self.page2.findChildren(QWidget)]
        self.updatePosition()

    def makeSimulType1(self):
        self.removeSimulWidgets()
        self.sim_updateNavButton(0)

        self.shared_data.sim_type = 1

        self.sim1_ui = Sim1UI(self.sim_mainFrame, self.shared_data)

        # Tab Order 설정
        tabOrders = (
            self.sim1_ui.stat_inputs.inputs
            + self.sim1_ui.skill_inputs.inputs
            + self.sim1_ui.info_inputs.inputs
        )
        for i in range(len(tabOrders) - 1):
            QWidget.setTabOrder(tabOrders[i], tabOrders[i + 1])

        # 메인 프레임 크기 조정
        self.sim_mainFrame.setFixedHeight(
            self.sim1_ui.info_frame.y() + self.sim1_ui.info_frame.height() + self.ui_var.sim_mainFrameMargin,
        )
        [i.show() for i in self.page2.findChildren(QWidget)]
        self.updatePosition()

    def sim_updateNavButton(self, num):
        for i in [0, 1, 2, 3]:
            self.sim_navButtons[i].setStyleSheet(
                f"""
                QPushButton {{ background-color: rgb(255, 255, 255); border: none; border-bottom: {"2" if i == num else "0"}px solid #9180F7; }}
                QPushButton:hover {{ background-color: rgb(234, 234, 234); }}
                """
            )

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

    def checkVersionThread(self):
        try:
            response = requests.get("https://api.github.com/repos/pro-days/skillmacro/releases/latest")
            if response.status_code == 200:
                self.recentVersion = response.json()["name"]
                self.updateUrl = response.json()["html_url"]
            else:
                self.recentVersion = "FailedUpdateCheck"
        except:
            self.recentVersion = "FailedUpdateCheck"

        if self.recentVersion == "FailedUpdateCheck":
            self.makeNoticePopup("FailedUpdateCheck")

        elif self.recentVersion != self.shared_data.VERSION:
            self.makeNoticePopup("RequireUpdate")

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
        self.back_palette = self.palette()
        self.back_palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        self.setPalette(self.back_palette)

        self.page1 = QFrame(self)
        self.page2 = QFrame(self)

        self.creator_label = QPushButton("  제작자: 프로데이즈  |  디스코드: prodays", self)
        self.creator_label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.creator_label.setStyleSheet("background-color: transparent; text-align: left; border: 0px;")
        self.creator_label.clicked.connect(lambda: open_new("https://github.com/Pro-Days"))
        self.creator_label.setFixedSize(320, 24)
        self.creator_label.move(2, self.height() - 25)

        # 메인 프레임 생성
        self.main_macro_ui = MainMacroUI(self.page1, self.shared_data)

        # 사이트바
        self.sidebar = Sidebar(self.page1, self.shared_data)

        self.changeSettingTo0()

        self.window_layout = QStackedLayout()
        self.window_layout.addWidget(self.page1)
        self.window_layout.addWidget(self.page2)
        self.setLayout(self.window_layout)
        self.window_layout.setCurrentIndex(0)

        self.show()

        self.changeLayout(1)

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
                self.settingSkillImages[self.shared_data.selectedSkillList[num]].setIcon(
                    getSkillImage(self.shared_data, self.shared_data.selectedSkillList[num], "off")
                )
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
                self.settingSkillImages[
                    self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting]
                ].setIcon(
                    getSkillImage(
                        self.shared_data,
                        self.shared_data.selectedSkillList[self.shared_data.is_skill_selecting],
                        "off",
                    )
                )
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
        self.selectedSkillImageButton[self.shared_data.is_skill_selecting].setIcon(
            getSkillImage(self.shared_data, num)
        )

        if self.shared_data.setting_type == 1:
            self.settingSkillImages[num].setIcon(getSkillImage(self.shared_data, num))

        self.shared_data.is_skill_selecting = -1
        dataSave(self.shared_data)

    def tick(self):
        self.preview_timer.singleShot(100, self.tick)
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
                skill.setIcon(
                    getSkillImage(
                        self.shared_data,
                        self.shared_data.selectedSkillList[self.shared_data.taskList[i][0]],
                        "off",
                    )
                )
            else:
                skill.setIcon(
                    getSkillImage(
                        self.shared_data,
                        self.shared_data.selectedSkillList[self.shared_data.taskList[i][0]],
                        1,
                    )
                )
            skill.setIconSize(QSize(min(width, height), min(width, height)))
            skill.setFixedSize(width, height)
            skill.move(round((fwidth - width * count) * 0.5) + width * i, 0)
            skill.show()

            self.shared_data.skill_preview_list.append(skill)

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
            button.setIcon(
                getSkillImage(self.shared_data, i)
                if i in self.shared_data.selectedSkillList
                else getSkillImage(self.shared_data, i, "off")
            )
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
                skill.setIcon(getSkillImage(self.shared_data, j[0], j[1]))
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
                skill.setIcon(getSkillImage(self.shared_data, j[0], j[1]))
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
            self.selectableSkillImageButton[i].setIcon(getSkillImage(self.shared_data, i))
            self.selectableSkillImageName[i].setText(
                self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][i]
            )
        for i in range(6):
            self.selectedSkillImageButton[i].setIcon(getSkillImage(self.shared_data.selectedSkillList[i]))

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
                self.selectableSkillImageButton[i].setIcon(getSkillImage(self.shared_data, i))
                self.selectableSkillImageName[i].setText(
                    self.shared_data.SKILL_NAME_LIST[self.shared_data.serverID][self.shared_data.jobID][i]
                )

            for i in range(6):
                self.selectedSkillImageButton[i].setIcon(
                    getSkillImage(self.shared_data, self.shared_data.selectedSkillList[i])
                )

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

            adjustFontSize(button, key, 20)
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
            adjustFontSize(button, key, 20)
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
        adjustFontSize(self.selectedSkillKey[num], key, 24)
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
                adjustFontSize(j, self.shared_data.skillKeys[i], 20)

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

            self.sim_navFrame.move(self.ui_var.sim_margin + deltaWidth // 2, self.ui_var.sim_margin)
            self.sim_mainFrame.setFixedWidth(
                self.width() - self.ui_var.scrollBarWidth - self.ui_var.sim_margin * 2
            )
            self.sim_mainScrollArea.setFixedSize(
                self.width() - self.ui_var.sim_margin,
                self.height()
                - self.creator_label.height()
                - self.ui_var.sim_navHeight
                - self.ui_var.sim_margin * 2
                - self.ui_var.sim_main1_D,
            )

            if self.shared_data.sim_type == 1:  # 정보 입력
                self.sim1_ui.stat_frame.move(deltaWidth // 2, 0)
                self.sim1_ui.skill_frame.move(
                    deltaWidth // 2,
                    self.sim1_ui.stat_frame.y() + self.sim1_ui.stat_frame.height() + self.ui_var.sim_main_D,
                )
                self.sim1_ui.info_frame.move(
                    deltaWidth // 2,
                    self.sim1_ui.skill_frame.y() + self.sim1_ui.skill_frame.height() + self.ui_var.sim_main_D,
                )

            elif self.shared_data.sim_type == 2:  # 시뮬레이터
                self.sim2_ui.power_frame.move(deltaWidth // 2, 0)
                self.sim2_ui.analysis_frame.move(
                    deltaWidth // 2,
                    self.sim2_ui.power_frame.y() + self.sim2_ui.power_frame.height() + self.ui_var.sim_main_D,
                )

            elif self.shared_data.sim_type == 3:  # 스탯 계산기
                self.sim3_ui.efficiency_frame.move(deltaWidth // 2, 0)
                self.sim3_ui.additional_frame.move(
                    deltaWidth // 2,
                    self.sim3_ui.efficiency_frame.y()
                    + self.sim3_ui.efficiency_frame.height()
                    + self.ui_var.sim_main_D,
                )
                self.sim3_ui.potential_frame.move(
                    deltaWidth // 2,
                    self.sim3_ui.additional_frame.y()
                    + self.sim3_ui.additional_frame.height()
                    + self.ui_var.sim_main_D,
                )
                self.sim3_ui.potentialRank_frame.move(
                    deltaWidth // 2,
                    self.sim3_ui.potential_frame.y()
                    + self.sim3_ui.potential_frame.height()
                    + self.ui_var.sim_main_D,
                )

            elif self.shared_data.sim_type == 4:  # 캐릭터 카드
                self.sim4_ui.mainframe.move(deltaWidth // 2, 0)

        # 항상 업데이트
        self.creator_label.move(2, self.height() - 25)
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
