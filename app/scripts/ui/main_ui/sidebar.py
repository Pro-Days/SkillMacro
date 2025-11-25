from __future__ import annotations

import copy
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, LiteralString

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, SkillImage
from app.scripts.data_manager import save_data
from app.scripts.misc import (
    adjust_font_size,
    convert_resource_path,
    get_available_skills,
    get_skill_details,
    get_skill_pixmap,
    is_key_used,
)
from app.scripts.shared_data import UI_Variable

if TYPE_CHECKING:
    from app.scripts.main_window import MainWindow
    from app.scripts.popup import PopupManager
    from app.scripts.shared_data import SharedData
    from app.scripts.ui.main_ui.main_ui import MainUI


class Sidebar(QFrame):
    def __init__(
        self,
        master: MainWindow,
        shared_data: SharedData,
    ):
        super().__init__(master)

        self.master: MainWindow = master
        self.shared_data: SharedData = shared_data

        self.ui_var = UI_Variable()

        general_settings = GeneralSettings(self.shared_data)
        skill_settings = SkillSettings(self.shared_data)
        link_skill_settings = LinkSkillSettings(self.shared_data)
        link_skill_editor = LinkSkillEditor(self.shared_data)

        self.page_navigator = QStackedWidget()
        self.page_navigator.addWidget(general_settings)
        self.page_navigator.addWidget(skill_settings)
        self.page_navigator.addWidget(link_skill_settings)
        self.page_navigator.addWidget(link_skill_editor)
        self.page_navigator.setContentsMargins(0, 0, 0, 0)
        self.page_navigator.setCurrentIndex(0)

        # 스크롤바
        self.scroll_area: QScrollArea = QScrollArea(self)
        self.scroll_area.setWidget(self.page_navigator)
        # 위젯이 스크롤 영역에 맞춰 크기 조절되도록
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background-color: #FFFFFF; border: 0px solid black; border-radius: 10px; }"
        )

        # 스크롤바 스크롤 설정
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.nav_button = NavigationButtons()

        layout = QHBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.nav_button)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setLayout(layout)

    ## 스킬 사용설정 -> 사용 여부 클릭
    def onSkillUsagesClick(self, num):
        skill_name = get_available_skills(self.shared_data)[num]

        self.master.get_popup_manager().close_popup()
        if self.shared_data.is_use_skill[skill_name]:
            pixmap = QPixmap(convert_resource_path("resources\\image\\checkFalse.png"))
            self.settingSkillUsages[num].setIcon(QIcon(pixmap))
            self.shared_data.is_use_skill[skill_name] = False

            # for i, j in enumerate(self.shared_data.linkSkillList):
            #     for k in j[2]:
            #         if k[0] == num:
            #             self.shared_data.linkSkillList[i][0] = 1
        else:
            pixmap = QPixmap(convert_resource_path("resources\\image\\checkTrue.png"))
            self.settingSkillUsages[num].setIcon(QIcon(pixmap))
            self.shared_data.is_use_skill[skill_name] = True
        save_data(self.shared_data)

    ## 스킬 사용설정 -> 콤보 여부 클릭
    def onSkillUseSoleClick(self, num):
        skill_name = get_available_skills(self.shared_data)[num]

        self.master.get_popup_manager().close_popup()

        if self.shared_data.is_use_sole[skill_name]:
            pixmap = QPixmap(convert_resource_path("resources\\image\\checkFalse.png"))
            self.settingSkillSingle[num].setIcon(QIcon(pixmap))
            self.shared_data.is_use_sole[skill_name] = False
        else:
            pixmap = QPixmap(convert_resource_path("resources\\image\\checkTrue.png"))
            self.settingSkillSingle[num].setIcon(QIcon(pixmap))
            self.shared_data.is_use_sole[skill_name] = True

        save_data(self.shared_data)

    ## 스킬 사용설정 -> 사용 순서 클릭
    def onSkillSequencesClick(self, num):
        self.master.get_popup_manager().close_popup()

        skill_name = get_available_skills(self.shared_data)[num]

        if skill_name not in self.shared_data.equipped_skills:
            return

        if self.shared_data.skill_priority[skill_name] == 0:
            minValue = max(self.shared_data.skill_priority.values()) + 1
            self.shared_data.skill_priority[skill_name] = minValue
            self.skill_sequence[skill_name].setText(str(minValue))
        else:
            self.shared_data.skill_priority[skill_name] = 0
            self.skill_sequence[skill_name].setText("-")

            for i in range(1, 7):
                if i not in self.shared_data.skill_priority.values():
                    for j, k in self.shared_data.skill_priority.items():
                        if k > i:
                            self.shared_data.skill_priority[j] -= 1
                            self.skill_sequence[j].setText(str(k - 1))

        save_data(self.shared_data)

    ## 사이드바 타입4 새로고침
    def reload_sidebar4(self, data):
        self.delete_sidebar_4()
        self.shared_data.sidebar_type = -1
        self.change_sidebar_to_4(data)

    ## 사이드바 타입 - 설정 제거
    def delete_sidebar_1(self):
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

        self.option_button0.setStyleSheet(
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
    def delete_sidebar_2(self):
        for i in self.skillSettingTexts:
            i.deleteLater()
        for i in range(8):
            self.settingLines[i].deleteLater()
            self.skill_icons[get_available_skills(self.shared_data)[i]].deleteLater()
            self.settingSkillUsages[i].deleteLater()
            self.settingSkillSingle[i].deleteLater()
            self.settingSkillComboCounts[i].deleteLater()
            self.skill_sequence[get_available_skills(self.shared_data)[i]].deleteLater()

        self.option_button1.setStyleSheet(
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
    def delete_sidebar_3(self):
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

        self.option_button2.setStyleSheet(
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
    def delete_sidebar_4(self):
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

        self.option_button2.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

    ## 사이드바에 사용되는 버튼 리턴
    def getSettingButton(self, text, x, y, cmd) -> QPushButton:
        button = QPushButton(text, self.frame)
        button.clicked.connect(cmd)
        button.setFont(CustomFont(12))
        button.setFixedSize(100, 30)
        button.move(x, y)
        button.show()
        return button

    ## 사이드바에 사용되는 체크버튼 리턴
    def getSettingCheck(self, text, x, y, cmd, disable=False) -> QPushButton:
        button = QPushButton(text, self.frame)
        button.clicked.connect(cmd)
        button.setFont(CustomFont(12))
        rgb = 153 if disable else 0
        button.setStyleSheet(f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}")
        button.setFixedSize(100, 30)
        button.move(x, y)
        button.show()
        return button

    ## 사이드바에 사용되는 라벨 리턴
    def getSettingName(self, text, x, y) -> QLabel:
        label = QLabel(text, self.frame)
        label.setFont(CustomFont(16))
        label.setStyleSheet("QLabel { border: 0px solid black; border-radius: 10px; }")
        label.setFixedSize(180, 40)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.move(x, y)
        label.show()
        return label

    ## 사이드바 설정 - 서버 클릭
    def onServerClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingServer":
            self.master.get_popup_manager().close_popup()
        else:
            self.master.get_popup_manager().make_server_popup()

    ## 사이드바 설정 - 직업 클릭
    def onJobClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingJob":
            self.master.get_popup_manager().close_popup()
        else:
            self.master.get_popup_manager().make_job_popup()

    ## 사이드바 설정 - 기본 딜레이 클릭
    def onDefaultDelayClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        self.master.get_popup_manager().close_popup()

        if self.shared_data.delay_type == 0:
            return

        self.shared_data.delay_type = 0
        self.shared_data.delay = 150

        self.buttonDefaultDelay.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputDelay.setStyleSheet("QPushButton { color: #999999; }")

        save_data(self.shared_data)

    ## 사이드바 설정 -  유저 딜레이 클릭
    def onInputDelayClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingDelay":
            self.master.get_popup_manager().close_popup()
            return
        self.master.get_popup_manager().close_popup()

        if self.shared_data.delay_type == 1:
            self.master.get_popup_manager().activatePopup("settingDelay")

            self.master.get_popup_manager().makePopupInput("delay")
        else:
            self.shared_data.delay_type = 1
            self.shared_data.delay = self.shared_data.delay_input

            self.buttonDefaultDelay.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputDelay.setStyleSheet("QPushButton { color: #000000; }")

            save_data(self.shared_data)

    ## 사이드바 설정 - 기본 쿨타임 감소 클릭
    def onDefaultCooltimeClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        self.master.get_popup_manager().close_popup()

        if self.shared_data.cooltime_reduction_type == 0:
            return

        self.shared_data.cooltime_reduction_type = 0
        self.shared_data.cooltime_reduction = 0

        self.buttonDefaultCooltime.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputCooltime.setStyleSheet("QPushButton { color: #999999; }")

        save_data(self.shared_data)

    ## 사이드바 설정 - 유저 쿨타임 감소 클릭
    def onInputCooltimeClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingCooltime":
            self.master.get_popup_manager().close_popup()
            return
        self.master.get_popup_manager().close_popup()

        if self.shared_data.cooltime_reduction_type == 1:
            self.master.get_popup_manager().activatePopup("settingCooltime")

            self.master.get_popup_manager().makePopupInput("cooltime")
        else:
            self.shared_data.cooltime_reduction_type = 1
            self.shared_data.cooltime_reduction = (
                self.shared_data.cooltime_reduction_input
            )

            self.buttonDefaultCooltime.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputCooltime.setStyleSheet("QPushButton { color: #000000; }")

            save_data(self.shared_data)

    ## 사이드바 설정 - 기본 시작키 클릭
    def onDefaultStartKeyClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        self.master.get_popup_manager().close_popup()

        if self.shared_data.start_key_type == 0:
            return

        if self.shared_data.start_key_input != "F9" and is_key_used(
            self.shared_data, "F9"
        ):
            self.master.get_popup_manager().make_notice_popup("StartKeyChangeError")
            return

        self.shared_data.start_key_type = 0
        self.shared_data.start_key = "F9"

        self.buttonDefaultStartKey.setStyleSheet("QPushButton { color: #000000; }")
        self.buttonInputStartKey.setStyleSheet("QPushButton { color: #999999; }")

        save_data(self.shared_data)

    ## 사이드바 설정 - 유저 시작키 클릭
    def onInputStartKeyClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "settingStartKey":
            self.master.get_popup_manager().close_popup()
            return
        self.master.get_popup_manager().close_popup()

        if self.shared_data.start_key_type == 1:
            self.master.get_popup_manager().activatePopup("settingStartKey")

            self.master.get_popup_manager().makeKeyboardPopup("StartKey")
        else:
            if is_key_used(self.shared_data, self.shared_data.start_key_input) and not (
                self.shared_data.start_key_input == "F9"
            ):
                self.master.get_popup_manager().make_notice_popup("StartKeyChangeError")
                return
            self.shared_data.start_key_type = 1
            self.shared_data.start_key = self.shared_data.start_key_input

            self.buttonDefaultStartKey.setStyleSheet("QPushButton { color: #999999; }")
            self.buttonInputStartKey.setStyleSheet("QPushButton { color: #000000; }")

            save_data(self.shared_data)

    ## 사이드바 설정 - 마우스설정1 클릭
    def on1stMouseTypeClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        self.master.get_popup_manager().close_popup()

        if self.shared_data.mouse_click_type == 0:
            return

        self.shared_data.mouse_click_type = 0

        self.button1stMouseType.setStyleSheet("QPushButton { color: #000000; }")
        self.button2ndMouseType.setStyleSheet("QPushButton { color: #999999; }")

        save_data(self.shared_data)

    ## 사이드바 설정 - 마우스설정2 클릭
    def on2ndMouseTypeClick(self):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        self.master.get_popup_manager().close_popup()

        if self.shared_data.mouse_click_type == 1:
            return

        self.shared_data.mouse_click_type = 1

        self.button1stMouseType.setStyleSheet("QPushButton { color: #999999; }")
        self.button2ndMouseType.setStyleSheet("QPushButton { color: #000000; }")

        save_data(self.shared_data)


class GeneralSettings(QFrame):
    """사이드바 타입 1 - 일반 설정"""

    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.title = Title("일반 설정")

        # 서버 - 직업
        self.server_job_setting = self.SettingItem(
            title="서버 - 직업",
            tooltip="서버와 직업을 선택합니다.\n새로운 서버가 오픈될 경우 새 항목이 추가될 수 있습니다.",
            btn0_text=self.shared_data.server_ID,
            btn0_enabled=True,
            btn1_text=self.shared_data.job_ID,
            btn1_enabled=True,
            func0=self.onServerClick,
            func1=self.onJobClick,
        )

        # 딜레이
        self.delay_setting = self.SettingItem(
            title="딜레이",
            tooltip=(
                "스킬을 사용하기 위한 키보드 입력, 마우스 클릭과 같은 동작 사이의 간격을 설정합니다.\n"
                "단위는 밀리초(millisecond, 0.001초)를 사용합니다.\n"
                "입력 가능한 딜레이의 범위는 50~1000입니다.\n"
                "딜레이를 계속해서 조절하며 1분간 매크로를 실행했을 때 놓치는 스킬이 없도록 설정해주세요."
            ),
            btn0_text="기본: 150",
            btn0_enabled=self.shared_data.delay_type == 0,
            btn1_text=str(self.shared_data.delay_input),
            btn1_enabled=self.shared_data.delay_type == 1,
            func0=self.onDefaultDelayClick,
            func1=self.onInputDelayClick,
        )

        # 쿨타임 감소
        self.cooltime_setting = self.SettingItem(
            title="쿨타임 감소",
            tooltip=(
                "캐릭터의 쿨타임 감소 스탯입니다.\n"
                "입력 가능한 쿨타임 감소 스탯의 범위는 0~50입니다."
            ),
            btn0_text="기본: 0",
            btn0_enabled=self.shared_data.cooltime_reduction_type == 0,
            btn1_text=str(self.shared_data.cooltime_reduction_input),
            btn1_enabled=self.shared_data.cooltime_reduction_type == 1,
            func0=self.onDefaultCooltimeClick,
            func1=self.onInputCooltimeClick,
        )

        # 시작키 설정
        self.start_key_setting = self.SettingItem(
            title="시작키 설정",
            tooltip=(
                "매크로를 시작하기 위한 키입니다.\n"
                "쓰지 않는 키로 설정한 후, 로지텍 G 허브와 같은 프로그램으로 마우스의 버튼에 매핑하는 것을 추천합니다."
            ),
            btn0_text="기본: F9",
            btn0_enabled=self.shared_data.start_key_type == 0,
            btn1_text=str(self.shared_data.start_key_input),
            btn1_enabled=self.shared_data.start_key_type == 1,
            func0=self.onDefaultStartKeyClick,
            func1=self.onInputStartKeyClick,
        )

        # 마우스 클릭
        self.click_setting = self.SettingItem(
            title="마우스 클릭",
            tooltip=(
                "스킬 사용시: 스킬을 사용하기 위해 마우스를 클릭합니다. 평타를 사용하기 위한 클릭은 하지 않습니다.\n"
                "평타 포함: 스킬과 평타를 사용하기 위해 마우스를 클릭합니다."
            ),
            btn0_text="스킬 사용시",
            btn0_enabled=self.shared_data.mouse_click_type == 0,
            btn1_text="평타 포함",
            btn1_enabled=self.shared_data.mouse_click_type == 1,
            func0=self.on1stMouseTypeClick,
            func1=self.on2ndMouseTypeClick,
        )

        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(self.server_job_setting)
        layout.addWidget(self.delay_setting)
        layout.addWidget(self.cooltime_setting)
        layout.addWidget(self.start_key_setting)
        layout.addWidget(self.click_setting)
        # layout.addStretch(1)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setLayout(layout)

    class SettingItem(QFrame):
        def __init__(
            self,
            title: str,
            tooltip: str,
            btn0_text: str,
            btn0_enabled: bool,
            btn1_text: str,
            btn1_enabled: bool,
            func0: Callable,
            func1: Callable,
        ):
            super().__init__()

            self.title = QLabel(title)
            self.title.setFont(CustomFont(16))
            self.title.setStyleSheet(
                "QLabel { border: 0px solid black; border-radius: 10px; }"
            )
            self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # self.title.setToolTip(tooltip)

            self.info_icon = QLabel("ⓘ")
            self.info_icon.setFont(CustomFont(12))
            self.info_icon.setStyleSheet(
                "QLabel { color: #888888; background-color: transparent; }"
            )
            self.info_icon.setToolTip(tooltip)
            self.info_icon.setFixedSize(20, 20)
            self.info_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

            header_layout = QHBoxLayout()
            header_layout.addWidget(self.title)
            header_layout.addWidget(self.info_icon)
            header_layout.setStretch(0, 1)
            header_layout.setStretch(1, 0)

            rgb: dict[bool, str] = {
                True: "#000000",
                False: "#999999",
            }

            self.button0 = QPushButton(btn0_text)
            self.button0.clicked.connect(func0)
            self.button0.setFont(CustomFont(12))
            self.button0.setStyleSheet(f"QPushButton {{color: {rgb[btn0_enabled]};}}")

            self.button1 = QPushButton(btn1_text)
            self.button1.clicked.connect(func1)
            self.button1.setFont(CustomFont(12))
            self.button1.setStyleSheet(f"QPushButton {{color: {rgb[btn1_enabled]};}}")

            layout = QGridLayout()
            layout.addLayout(header_layout, 0, 0, 1, 2)
            layout.addWidget(self.button0, 1, 0)
            layout.addWidget(self.button1, 1, 1)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            self.setLayout(layout)


class SkillSettings(QFrame):
    """사이드바 타입 2 - 스킬 사용설정"""

    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.title = Title("스킬 사용설정")

        skill_setting = self.SkillSetting(self.shared_data)

        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(skill_setting)
        self.setLayout(layout)

    class SkillSetting(QFrame):
        def __init__(self, shared_data: SharedData):
            super().__init__()

            self.shared_data: SharedData = shared_data
            layout = QGridLayout()
            self.setLayout(layout)

            titles: list[str] = ["사용\n여부", "단독\n사용", "콤보\n횟수", "우선\n순위"]
            tooltips: list[str] = [
                (
                    "매크로가 작동 중일 때 자동으로 스킬을 사용할지 결정합니다.\n"
                    "이동기같이 자신이 직접 사용해야 하는 스킬만 사용을 해제하시는 것을 추천드립니다.\n"
                    "연계스킬에는 적용되지 않습니다."
                ),
                (
                    "연계스킬을 대기할 때 다른 스킬들이 준비되는 것을 기다리지 않고 우선적으로 사용할 지 결정합니다.\n"
                    "연계스킬 내에서 다른 스킬보다 너무 빠르게 준비되는 스킬은 사용을 해제하시는 것을 추천드립니다.\n"
                    "사용여부가 활성화되지 않았다면 단독으로 사용되지 않습니다."
                ),
                (
                    "매크로가 작동 중일 때 한 번에 스킬을 몇 번 사용할 지를 결정합니다.\n"
                    "콤보가 존재하는 스킬에 사용하는 것을 추천합니다.\n"
                    "연계스킬에는 적용되지 않습니다."
                ),
                (
                    "매크로가 작동 중일 때 여러 스킬이 준비되었더라도 우선순위가 더 높은(숫자가 낮은) 스킬을 먼저 사용합니다.\n"
                    "우선순위를 설정하지 않은 스킬들은 준비된 시간 순서대로 사용합니다.\n"
                    "버프스킬의 우선순위를 높이는 것을 추천합니다.\n"
                    "연계스킬은 우선순위가 적용되지 않습니다."
                ),
            ]
            for i in range(4):
                label = QLabel(titles[i])
                label.setToolTip(tooltips[i])
                label.setStyleSheet("QLabel { border: 0px; border-radius: 0px; }")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setFont(CustomFont(12))

                layout.addWidget(label, 0, i + 1)

            check_btn_style = """
                QPushButton {
                    background-color: transparent; border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: #dddddd;
                }
            """
            skill_names: list[str] = get_available_skills(self.shared_data)
            for idx, name in enumerate(skill_names):
                pixmap: QPixmap = get_skill_pixmap(
                    shared_data=self.shared_data,
                    skill_name=name,
                    state=-1 if name in self.shared_data.equipped_skills else -2,
                )
                skill_image: SkillImage = SkillImage(
                    parent=self, pixmap=pixmap, size=50
                )
                layout.addWidget(skill_image, idx + 1, 0)

                pixmap = QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{self.shared_data.is_use_skill[name]}.png"
                    )
                )
                usage_btn = QPushButton()
                usage_btn.clicked.connect(
                    partial(lambda x: self.onSkillUsagesClick(x), name)
                )
                usage_btn.setIcon(QIcon(pixmap))
                usage_btn.setIconSize(QSize(32, 32))
                usage_btn.setStyleSheet(check_btn_style)
                layout.addWidget(usage_btn, idx + 1, 1)

                pixmap = QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{self.shared_data.is_use_sole[name]}.png"
                    )
                )
                use_sole_btn = QPushButton()
                use_sole_btn.clicked.connect(
                    partial(lambda x: self.onSkillUseSoleClick(x), name)
                )
                use_sole_btn.setIcon(QIcon(pixmap))
                use_sole_btn.setIconSize(QSize(32, 32))
                use_sole_btn.setStyleSheet(check_btn_style)
                layout.addWidget(use_sole_btn, idx + 1, 2)

                combo_btn = QPushButton(
                    f"{self.shared_data.combo_count[name]} / {get_skill_details(self.shared_data, name)['max_combo_count']}"
                )
                combo_btn.clicked.connect(
                    partial(
                        lambda x: self.master.get_popup_manager().onSkillComboCountsClick(
                            x
                        ),
                        name,
                    )
                )
                combo_btn.setFont(CustomFont(12))
                layout.addWidget(combo_btn, idx + 1, 3)

                priority: int = self.shared_data.skill_priority[name]
                txt: str = "-" if priority == 0 else str(priority)

                priority_btn = QPushButton(txt)
                priority_btn.clicked.connect(
                    partial(lambda x: self.onSkillSequencesClick(x), name)
                )
                priority_btn.setFont(CustomFont(12))
                layout.addWidget(priority_btn, idx + 1, 4)


class LinkSkillSettings(QFrame):
    """사이드바 타입 3 - 연계설정 스킬 목록"""

    def __init__(
        self,
        shared_data: SharedData,
        popup_manager: PopupManager,
        cancel_skill_selection: Callable,
    ):
        super().__init__()

        self.shared_data: SharedData = shared_data
        self.popup_manager: PopupManager = popup_manager
        self.cancel_skill_selection: Callable = cancel_skill_selection

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.title = Title("스킬 연계설정")
        layout.addWidget(self.title)

        self.create_link_skill_btn = QPushButton("새 연계스킬 만들기")
        self.create_link_skill_btn.clicked.connect(self.create_new)
        self.create_link_skill_btn.setFont(CustomFont(16))
        layout.addWidget(self.create_link_skill_btn)

        for i, data in enumerate(self.shared_data.link_skills):
            link_skill = self.LinkSkill(self.shared_data, data, i)
            layout.addWidget(link_skill)

    def create_new(self):
        """새 연계스킬 만들기"""

        def get_key() -> LiteralString | None:
            """사용되지 않는 단축키 반환"""

            for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if not is_key_used(self.shared_data, char):
                    return char
            return None

        self.popup_manager.close_popup()

        # 스킬 장착 선택 중이었으면 취소
        self.cancel_skill_selection()

        # 새 연계스킬 데이터 생성
        data = {
            "useType": "manual",
            "keyType": "off",
            "key": get_key(),
            "skills": [
                {"name": get_available_skills(self.shared_data)[0], "count": 1},
            ],
            "num": -1,
        }

        # 연계스킬 편집 레이아웃으로 변경

    def edit(self, num: int):
        """연계스킬 편집"""

        self.popup_manager.close_popup()

        # 스킬 장착 선택 중이었으면 취소
        self.cancel_skill_selection()

        # 연계스킬 데이터 복사
        data = copy.deepcopy(self.shared_data.link_skills[num])
        data["num"] = num

        # 연계스킬 편집 레이아웃으로 변경

    def remove(self, num: int):
        """연계스킬 제거"""

        self.popup_manager.close_popup()

        # 연계스킬 제거
        del self.shared_data.link_skills[num]

        # 데이터 저장
        save_data(self.shared_data)

    class LinkSkill(QFrame):
        def __init__(self, shared_data: SharedData, data, idx: int):
            super().__init__()

            self.shared_data: SharedData = shared_data

            edit_btn = QPushButton()
            edit_btn.clicked.connect(partial(lambda x: self.editLinkSkill(x), idx))
            edit_btn.setStyleSheet(
                """QPushButton { background-color: transparent; border: 0px; }
                QPushButton:hover { background-color: rgba(0, 0, 0, 32); border: 0px solid black; border-radius: 8px; }"""
            )

            layout = QHBoxLayout()
            edit_btn.setLayout(layout)

            # 사용 스킬 개수: 최대 12개
            skill_count: int = min(len(data["skills"]), 6)
            for i in range(skill_count):
                pixmap: QPixmap = get_skill_pixmap(
                    shared_data=self.shared_data,
                    skill_name=data["skills"][i]["name"],
                    state=data["skills"][i]["count"],
                )

                skill = SkillImage(
                    parent=self,
                    pixmap=pixmap,
                )
                layout.addWidget(skill)

            layout.addStretch(1)

            text: str = "" if data["keyType"] == "off" else data["key"]
            key_btn = QLabel(text)
            key_btn.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px; }"
            )
            layout.addWidget(key_btn)

            remove_btn = QPushButton("")
            remove_btn.clicked.connect(partial(lambda x: self.removeLinkSkill(x), idx))
            pixmap = QPixmap(convert_resource_path("resources\\image\\x.png"))
            remove_btn.setIcon(QIcon(pixmap))
            remove_btn.setStyleSheet(
                """QPushButton { background-color: transparent; border: 0px; }
                QPushButton:hover { background-color: #dddddd; border: 0px solid black; border-radius: 18px; }"""
            )
            layout.addWidget(remove_btn)

            use_type_display = QFrame()
            use_type_display.setStyleSheet(
                f"QFrame {{ background-color: {"#0000ff" if data["useType"] == "manual" else "#ff0000"}; border: 0px solid black; border-radius: 2px; }}"
            )
            layout.addWidget(use_type_display)


class LinkSkillEditor(QFrame):
    """사이드바 타입 4 - 연계설정 편집"""

    # todo: 링크스킬 데이터를 클래스로 관리하도록 수정
    def __init__(self, shared_data: SharedData, popup_manager: PopupManager):
        super().__init__()

        self.shared_data: SharedData = shared_data
        self.popup_manager: PopupManager = popup_manager

        layout = QVBoxLayout()
        self.setLayout(layout)

        type_setting = self.SettingItem(
            title="연계 유형",
            tooltip=(
                "자동: 매크로가 실행 중일 때 자동으로 연계 스킬을 사용합니다. 자동 연계스킬에 사용되는 스킬은 다른 자동 연계스킬에 사용될 수 없습니다.\n"
                "연계스킬은 매크로 작동 여부와 관계 없이 단축키를 입력해서 작동시킬 수 있습니다."
            ),
            btn0_text="자동",
            btn1_text="수동",
            is_btn0_enabled=True,
            func0=self.set_auto,
            func1=self.set_manual,
        )
        layout.addWidget(type_setting)

        key_setting = self.SettingItem(
            title="단축키",
            tooltip=(
                "매크로가 실행 중이지 않을 때 해당 연계스킬을 작동시킬 단축키입니다."
            ),
            btn0_text="설정안함",
            btn1_text="",
            is_btn0_enabled=True,  # data["keyType"] == "off"
            func0=self.clear_key,
            func1=self.on_key_btn_clicked,
        )
        layout.addWidget(key_setting)

        # skill_item = self.SkillItem(
        #     name=j["name"],
        #     count=j["count"],
        #     shared_data=self.shared_data,
        # )

        add_skill_btn = QPushButton()
        # add_skill_btn.clicked.connect(lambda: self.addLinkSkill(data))
        add_skill_btn.setStyleSheet(
            """QPushButton {
                    background-color: transparent; border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }"""
        )
        pixmap = QPixmap(convert_resource_path("resources\\image\\plus.png"))
        add_skill_btn.setIcon(QIcon(pixmap))
        add_skill_btn.setIconSize(QSize(24, 24))
        layout.addWidget(add_skill_btn)

        cancel_btn = QPushButton("취소")
        # cancel_btn.clicked.connect(self.cancelEditingLinkSkill)
        cancel_btn.setFont(CustomFont(12))
        layout.addWidget(cancel_btn)

        save_btn = QPushButton("저장")
        # save_btn.clicked.connect(
        #     lambda: self.saveEditingLinkSkill(data)
        # )
        save_btn.setFont(CustomFont(12))
        layout.addWidget(save_btn)

        self.data = {}

    def set_auto(self):
        """연계스킬을 자동 사용으로 설정"""

        self.popup_manager.close_popup()

        # 이미 자동이면 무시
        if self.data["useType"] == "auto":
            return

        # 모든 스킬이 장착되어 있는지 확인
        if not all(
            i["name"] in self.shared_data.equipped_skills for i in self.data["skills"]
        ):
            self.popup_manager.make_notice_popup("skillNotSelected")
            return

        # 지금 수정 중인 연계스킬의 인덱스
        num: int = self.data["num"]

        # 연계스킬을 수정 중이거나
        # 연계스킬이 1개 이상 존재하는 경우
        if self.shared_data.link_skills:
            # 모든 연계 스킬 중 자동으로 사용하는 스킬 목록
            auto_skills = []
            for i, link_skill in enumerate(self.shared_data.link_skills):
                # 현재 수정 중인 스킬은 제외
                if i == num:
                    continue

                if link_skill["useType"] == "auto":
                    for j in link_skill["skills"]:
                        # 자동 연계스킬에서 사용하는 스킬 이름 추가
                        auto_skills.append(j["name"])

            # 자동 연계스킬에 이미 사용 중인 스킬이 있는지 확인
            for i in self.data["skills"]:
                # 이미 사용 중이라면 알림 팝업 생성 후 종료
                if i["name"] in auto_skills:
                    self.popup_manager.make_notice_popup("autoAlreadyExist")
                    return

        # 자동으로 변경
        self.data["useType"] = "auto"

    def set_manual(self):
        """연계스킬을 수동 사용으로 설정"""

        self.popup_manager.close_popup()

        # 이미 수동이면 무시
        if self.data["useType"] == "manual":
            return

        # 수동으로 변경
        self.data["useType"] = "manual"

    def clear_key(self):
        """단축키 설정 해제"""

        self.data["keyType"] = "off"

    def on_key_btn_clicked(self):
        """연계스킬 단축키 설정 버튼 클릭 시"""

        self.popup_manager.activatePopup("settingLinkSkillKey")
        self.popup_manager.makeKeyboardPopup(("LinkSkill", self.data))

    def change_skill(self, i: int, skill_name: str):
        """i번째 스킬을 skill_name으로 변경"""
        # data 관리 클래스로 이동해도 좋을듯

        self.popup_manager.close_popup()

        # 동일 스킬 선택 시 무시
        if self.data["skills"][i]["name"] == skill_name:
            return

        # 스킬명 설정, 사용횟수 초기화
        # todo: data 클래스에서 값이 변경되면 자동으로 UI에 반영되도록 변경하기
        self.data["skills"][i]["name"] = skill_name
        self.data["skills"][i]["count"] = 1

        # 수동 사용으로 변경
        self.data["useType"] = "manual"

        if self.is_skill_exceeded(skill_name):
            self.popup_manager.make_notice_popup("exceedMaxLinkSkill")

    def change_skill_count(self, i: int, count: int):
        """스킬 사용 횟수 변경"""

        self.popup_manager.close_popup()

        # 사용 횟수 변경
        self.data["skills"][i]["count"] = count

        # 수동 사용으로 변경
        self.data["useType"] = "manual"

        # 최대 사용 횟수 초과 시 알림 팝업 생성
        if self.is_skill_exceeded(self.data["skills"][i]["name"]):
            self.popup_manager.make_notice_popup("exceedMaxLinkSkill")

    def remove_skill(self, i: int):
        """i번째 스킬 제거"""

        self.popup_manager.close_popup()

        # 스킬 제거
        del self.data["skills"][i]

        # 수동 사용으로 변경
        self.data["useType"] = "manual"

    def add_skill(self):
        """스킬 추가"""

        self.popup_manager.close_popup()

        # 스킬 추가
        name: str = get_available_skills(self.shared_data)[0]
        self.data["skills"].append({"name": name, "count": 1})

        # 수동 사용으로 변경
        self.data["useType"] = "manual"

        # 최대 사용 횟수 초과 시 알림 팝업 생성
        if self.is_skill_exceeded(name):
            self.popup_manager.make_notice_popup("exceedMaxLinkSkill")

    def cancel(self):
        """편집 취소"""

        self.popup_manager.close_popup()
        # 사이드바 연계설정 목록으로 변경

    def save(self):
        """편집 저장"""

        self.popup_manager.close_popup()

        # 수정하던 연계스킬의 인덱스
        index = self.data["index"]

        # 새로 만드는 경우
        if index == -1:
            self.shared_data.link_skills.append(self.data)

        # 기존 연계스킬 수정하는 경우
        else:
            self.shared_data.link_skills[index] = self.data

        save_data(self.shared_data)
        # 사이드바 연계설정 목록으로 변경

    def is_skill_exceeded(self, skill_name: str) -> bool:
        """연계스킬에서 특정 스킬의 최대 사용 횟수를 초과하는지 확인"""

        # 스킬 사용 가능 최대 횟수
        max_combo: int = get_skill_details(self.shared_data, skill_name)[
            "max_combo_count"
        ]

        combo_count = 0
        # 연계스킬에서 해당 스킬의 사용 횟수 합산
        for skill in self.data["skills"]:
            name: str = skill["name"]
            count: int = skill["count"]

            if skill_name == name:
                combo_count += count

        # 최대 사용 횟수 초과 여부 반환
        return combo_count > max_combo

    class SkillItem(QFrame):
        def __init__(
            self,
            name: str,
            count: int,
            shared_data: SharedData,
        ):
            super().__init__()

            skill = QPushButton()
            # skill.clicked.connect(
            #     partial(
            #         lambda x: self.master.get_popup_manager().change_link_skill_type(x),
            #         (data, i),
            #     )
            # )
            skill.setIcon(QIcon(get_skill_pixmap(shared_data, name, count)))
            # skill.setIconSize(QSize(50, 50))
            skill.setToolTip(
                "연계스킬을 구성하는 스킬의 목록과 사용 횟수를 설정할 수 있습니다.\n하나의 스킬이 너무 많이 사용되면 연계가 정상적으로 작동하지 않을 수 있습니다."
            )

            button = QPushButton(
                f"{count} / {get_skill_details(shared_data, name)['max_combo_count']}",
            )
            # button.clicked.connect(
            #     partial(
            #         lambda x: self.master.get_popup_manager().editLinkSkillCount(x),
            #         (data, i),
            #     )
            # )
            # button.setFixedSize(50, 30)
            button.setFont(CustomFont(12))

            remove = QPushButton()
            # remove.clicked.connect(
            #     partial(lambda x: self.removeOneLinkSkill(x), (data, i))
            # )
            remove.setStyleSheet(
                """QPushButton {
                    background-color: transparent; border-radius: 16px;
                }
                QPushButton:hover {
                    background-color: #eeeeee;
                }"""
            )
            pixmap = QPixmap(convert_resource_path("resources\\image\\xAlpha.png"))
            remove.setIcon(QIcon(pixmap))
            remove.setIconSize(QSize(16, 16))

            layout = QHBoxLayout()
            layout.addWidget(skill)
            layout.addWidget(button)
            layout.addWidget(remove)
            self.setLayout(layout)

    class SettingItem(QFrame):
        def __init__(
            self,
            title: str,
            tooltip: str,
            btn0_text: str,
            btn1_text: str,
            is_btn0_enabled: bool,
            func0: Callable,
            func1: Callable,
            # data,
        ):
            super().__init__()

            type_label = QLabel(title)
            type_label.setToolTip(tooltip)
            type_label.setFont(CustomFont(12))

            btn0 = QPushButton(btn0_text)
            # btn0.clicked.connect(lambda: func0(data))
            btn0.setStyleSheet(f"color: {"#999999" if is_btn0_enabled else "#000000"};")
            btn0.setFont(CustomFont(12))

            btn1 = QPushButton(btn1_text)
            # btn1.clicked.connect(lambda: func1(data))
            btn1.setStyleSheet(
                f"color: {"#999999" if not is_btn0_enabled else "#000000"};"
            )
            btn1.setFont(CustomFont(12))

            layout = QHBoxLayout()
            layout.addWidget(type_label)
            layout.addStretch(1)
            layout.addWidget(btn0)
            layout.addWidget(btn1)
            self.setLayout(layout)


class NavigationButtons(QFrame):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(
            """QFrame { 
                background-color: #f0f0f0;
                border: 0px solid;
            }"""
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        icon_paths: list[str] = [
            convert_resource_path("resources\\image\\setting.png"),
            convert_resource_path("resources\\image\\usageSetting.png"),
            convert_resource_path("resources\\image\\linkSetting.png"),
            convert_resource_path("resources\\image\\simulationSidebar.png"),
        ]
        border_radiuses: list[list[int]] = [
            [0, 8, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 8],
        ]

        for i in range(4):
            button = self.NavigationButton(
                icon_path=icon_paths[i],
                border_radius=border_radiuses[i],
            )
            layout.addWidget(button)

    class NavigationButton(QPushButton):
        def __init__(self, icon_path: str, border_radius: list[int]):
            super().__init__()

            pixmap = QPixmap(icon_path)
            self.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: #dddddd; 
                        border: 1px solid #b4b4b4; 
                        border-top-left-radius :{border_radius[0]}px; 
                        border-top-right-radius : {border_radius[1]}px; 
                        border-bottom-left-radius : {border_radius[2]}px; 
                        border-bottom-right-radius : {border_radius[3]}px;
                    }}
                    QPushButton:hover {{
                        background-color: #dddddd;
                    }}
                """
            )

            self.setIcon(QIcon(pixmap))
            self.setIconSize(QSize(32, 32))


class Title(QLabel):
    def __init__(self, text: str):
        super().__init__(text, None)

        self = QLabel("", self)
        self.setFont(CustomFont(20))
        self.setStyleSheet(
            "border: 0px solid black; border-radius: 10px; background-color: #CADEFC;"
        )
        # self.title.setFixedSize(200, 100)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
