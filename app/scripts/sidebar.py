from __future__ import annotations

from .data_manager import save_data
from .misc import (
    get_skill_pixmap,
    adjust_font_size,
    is_key_used,
    get_available_skills,
    get_skill_details,
    convert_resource_path,
)
from .shared_data import UI_Variable
from .custom_classes import CustomFont, CustomShadowEffect, SkillImage

import copy
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QWidget


if TYPE_CHECKING:
    from .main_window import MainWindow
    from .shared_data import SharedData


class Sidebar:
    def __init__(
        self,
        master: MainWindow,
        parent: QFrame,
        shared_data: SharedData,
    ):
        self.master: MainWindow = master
        self.parent: QFrame = parent
        self.shared_data: SharedData = shared_data

        self.ui_var = UI_Variable()

        self.make_ui()

    def make_ui(self) -> None:
        # 설정 레이블
        self.frame = QFrame(self.parent)  # 상속받아서 Sidebar: QFrame으로 수정
        self.frame.setFixedSize(300, 790)
        self.frame.setStyleSheet("QFrame { background-color: #FFFFFF; }")
        # self.frame.setPalette(self.backPalette)
        self.scroll_area = QScrollArea(self.parent)
        self.scroll_area.setWidget(self.frame)
        self.scroll_area.setFixedSize(319, self.master.height() - 24)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background-color: #FFFFFF; border: 0px solid black; border-radius: 10px; }"
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        # self.sidebarScrollArea.setPalette(self.backPalette)
        self.scroll_area.show()

        ## 사이드바 옵션 아이콘
        self.option_frame = QFrame(self.parent)
        self.option_frame.setFixedSize(34, 136)
        self.option_frame.move(320, 20)

        self.option_button0 = SideBarButton(self.master, self, self.option_frame, 0)
        self.option_button1 = SideBarButton(self.master, self, self.option_frame, 1)
        self.option_button2 = SideBarButton(self.master, self, self.option_frame, 2)
        self.option_button3 = SideBarButton(self.master, self, self.option_frame, 3)

        self.settings_label = QLabel("", self.frame)
        self.settings_label.setFont(CustomFont(20))
        self.settings_label.setStyleSheet(
            "border: 0px solid black; border-radius: 10px; background-color: #CADEFC;"
        )
        self.settings_label.setFixedSize(200, 100)
        self.settings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.settings_label.move(50, 20)
        self.settings_label.setGraphicsEffect(CustomShadowEffect())

    ## 사이드바 타입 -> 설정으로 변경
    def change_sidebar_to_1(self):
        self.master.get_popup_manager().close_popup()

        match self.shared_data.sidebar_type:
            case 1:
                return
            case 2:
                self.delete_sidebar_2()
            case 3:
                self.delete_sidebar_3()
            case 4:
                self.delete_sidebar_4()

        self.shared_data.sidebar_type = 1

        self.option_button0.setStyleSheet(
            """
            QPushButton {
                background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 8px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

        self.settings_label.setText("설정")
        self.frame.setFixedSize(300, 770)
        self.settingLines = []
        for i in range(4):
            line = QFrame(self.frame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(260, 1)
            line.move(20, 260 + 130 * i)
            line.show()
            self.settingLines.append(line)

        # 서버 - 직업
        self.labelServerJob = self.getSettingName("서버 - 직업", 60, 150)
        self.labelServerJob.setToolTip(
            "서버와 직업을 선택합니다.\n새로운 서버가 오픈될 경우 새 항목이 추가될 수 있습니다."
        )
        self.buttonServerList = self.getSettingButton(
            self.shared_data.server_ID,
            40,
            200,
            self.onServerClick,
        )
        self.buttonJobList = self.getSettingButton(
            self.shared_data.job_ID,
            160,
            200,
            self.onJobClick,
        )

        # 딜레이
        self.labelDelay = self.getSettingName("딜레이", 60, 150 + 130)
        self.labelDelay.setToolTip(
            "스킬을 사용하기 위한 키보드 입력, 마우스 클릭과 같은 동작 사이의 간격을 설정합니다.\n단위는 밀리초(millisecond, 0.001초)를 사용합니다.\n입력 가능한 딜레이의 범위는 50~1000입니다.\n딜레이를 계속해서 조절하며 1분간 매크로를 실행했을 때 놓치는 스킬이 없도록 설정해주세요."
        )
        if self.shared_data.delay_type == 0:
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
            str(self.shared_data.delay_input),
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
        if self.shared_data.cooltime_reduction_type == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultCooltime = self.getSettingCheck(
            "기본: 0", 40, 200 + 130 * 2, self.onDefaultCooltimeClick, disable=temp[0]
        )
        self.buttonInputCooltime = self.getSettingCheck(
            str(self.shared_data.cooltime_reduction_input),
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
        if self.shared_data.start_key_type == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultStartKey = self.getSettingCheck(
            "기본: F9", 40, 200 + 130 * 3, self.onDefaultStartKeyClick, disable=temp[0]
        )
        self.buttonInputStartKey = self.getSettingCheck(
            str(self.shared_data.start_key_input),
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
        if self.shared_data.mouse_click_type == 0:
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
    def change_sidebar_to_2(self):
        self.master.get_popup_manager().close_popup()

        match self.shared_data.sidebar_type:
            case 1:
                self.delete_sidebar_1()
            case 2:
                return
            case 3:
                self.delete_sidebar_3()
            case 4:
                self.delete_sidebar_4()

        self.shared_data.sidebar_type = 2

        self.option_button1.setStyleSheet(
            """
            QPushButton {
                background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

        self.settings_label.setText("스킬 사용설정")
        self.frame.setFixedSize(300, 620)

        self.skillSettingTexts: list[QLabel] = []
        texts: list[str] = ["사용\n여부", "단독\n사용", "콤보\n횟수", "우선\n순위"]
        tooltips: list[str] = [
            "매크로가 작동 중일 때 자동으로 스킬을 사용할지 결정합니다.\n이동기같이 자신이 직접 사용해야 하는 스킬만 사용을 해제하시는 것을 추천드립니다.\n연계스킬에는 적용되지 않습니다.",
            "연계스킬을 대기할 때 다른 스킬들이 준비되는 것을 기다리지 않고 우선적으로 사용할 지 결정합니다.\n연계스킬 내에서 다른 스킬보다 너무 빠르게 준비되는 스킬은 사용을 해제하시는 것을 추천드립니다.\n사용여부가 활성화되지 않았다면 단독으로 사용되지 않습니다.",
            "매크로가 작동 중일 때 한 번에 스킬을 몇 번 사용할 지를 결정합니다.\n콤보가 존재하는 스킬에 사용하는 것을 추천합니다.\n연계스킬에는 적용되지 않습니다.",
            "매크로가 작동 중일 때 여러 스킬이 준비되었더라도 우선순위가 더 높은(숫자가 낮은) 스킬을 먼저 사용합니다.\n우선순위를 설정하지 않은 스킬들은 준비된 시간 순서대로 사용합니다.\n버프스킬의 우선순위를 높이는 것을 추천합니다.\n연계스킬은 우선순위가 적용되지 않습니다.",
        ]
        for i in range(4):
            label = QLabel(texts[i], self.frame)
            label.setToolTip(tooltips[i])
            label.setStyleSheet("QLabel { border: 0px; border-radius: 0px; }")
            label.setFixedSize(50, 50)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.move(75 + 50 * i, 150)
            label.setFont(CustomFont(12))
            label.show()
            self.skillSettingTexts.append(label)

        self.settingLines: list[QFrame] = []
        self.skill_icons: dict[str, SkillImage] = {}
        self.settingSkillUsages: list[QPushButton] = []
        self.settingSkillSingle: list[QPushButton] = []
        self.settingSkillComboCounts: list[QPushButton] = []
        self.skill_sequence: dict[str, QPushButton] = {}
        for i in range(8):
            skill_name = get_available_skills(self.shared_data)[i]

            line = QFrame(self.frame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(260, 1)
            line.move(20, 200 + 51 * i)
            line.show()
            self.settingLines.append(line)

            if skill_name in self.shared_data.equipped_skills:
                pixmap = get_skill_pixmap(
                    shared_data=self.shared_data, skill_name=skill_name
                )
            else:
                pixmap = get_skill_pixmap(
                    shared_data=self.shared_data, skill_name=skill_name, state=-2
                )

            skill_image: SkillImage = SkillImage(
                parent=self.frame,
                pixmap=pixmap,
                size=50,
                x=20,
                y=201 + 51 * i,
            )
            skill_image.show()
            self.skill_icons[skill_name] = skill_image

            button = QPushButton("", self.frame)
            if self.shared_data.is_use_skill[get_available_skills(self.shared_data)[i]]:
                pixmap = QPixmap(
                    convert_resource_path("resources\\image\\checkTrue.png")
                )
            else:
                pixmap = QPixmap(
                    convert_resource_path("resources\\image\\checkFalse.png")
                )
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

            button = QPushButton("", self.frame)
            if self.shared_data.is_use_sole[get_available_skills(self.shared_data)[i]]:
                pixmap = QPixmap(
                    convert_resource_path("resources\\image\\checkTrue.png")
                )
            else:
                pixmap = QPixmap(
                    convert_resource_path("resources\\image\\checkFalse.png")
                )
            button.clicked.connect(partial(lambda x: self.onSkillUseSoleClick(x), i))
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
                f"{self.shared_data.combo_count[get_available_skills(self.shared_data)[i]]} / {get_skill_details(self.shared_data, get_available_skills(self.shared_data)[i])['max_combo_count']}",
                self.frame,
            )
            button.clicked.connect(
                partial(
                    lambda x: self.master.get_popup_manager().onSkillComboCountsClick(
                        x
                    ),
                    i,
                )
            )
            button.setFont(CustomFont(12))
            button.setFixedSize(46, 32)
            button.move(177, 210 + 51 * i)
            button.show()
            self.settingSkillComboCounts.append(button)

            txt = (
                "-"
                if self.shared_data.skill_priority[skill_name] == 0
                else str(self.shared_data.skill_priority[skill_name])
            )
            button = QPushButton(txt, self.frame)
            button.clicked.connect(partial(lambda x: self.onSkillSequencesClick(x), i))
            button.setFont(CustomFont(12))
            button.setFixedSize(46, 32)
            button.move(227, 210 + 51 * i)
            button.show()
            self.skill_sequence[skill_name] = button

    ## 사이드바 타입 -> 연계설정 스킬 목록으로 변경
    def change_sidebar_to_3(self):
        self.master.get_popup_manager().close_popup()

        match self.shared_data.sidebar_type:
            case 1:
                self.delete_sidebar_1()
            case 2:
                self.delete_sidebar_2()
            case 3:
                return
            case 4:
                self.delete_sidebar_4()

        self.shared_data.sidebar_type = 3

        self.option_button2.setStyleSheet(
            """
            QPushButton {
                background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

        self.settings_label.setText("스킬 연계설정")
        self.frame.setFixedSize(300, 220 + 51 * len(self.shared_data.link_skills))

        self.newLinkSkill = QPushButton("새 연계스킬 만들기", self.frame)
        self.newLinkSkill.clicked.connect(self.makeNewLinkSkill)
        self.newLinkSkill.setFixedSize(240, 40)
        self.newLinkSkill.setFont(CustomFont(16))
        self.newLinkSkill.move(30, 150)
        self.newLinkSkill.show()

        self.settingLines = []
        self.settingSkillPreview = []
        self.settingSkillBackground = []
        self.settingSkillKey = []
        self.settingSkillRemove = []
        self.settingAMDP = []
        for i, j in enumerate(self.shared_data.link_skills):
            line = QFrame(self.frame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(264, 1)
            line.move(18, 251 + 51 * i)
            line.show()
            self.settingLines.append(line)

            am_dp = QFrame(self.frame)  # auto, manual 표시 프레임
            if j["useType"] == "manual":
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
                    pixmap = get_skill_pixmap(
                        self.shared_data,
                        j["skills"][k]["name"],
                        j["skills"][k]["count"],
                    )

                    skill = SkillImage(
                        parent=self.frame,
                        pixmap=pixmap,
                        size=50,
                        x=18 + 50 * k,
                        y=201 + 51 * i,
                    )
                    skill.show()
                    self.settingSkillPreview.append(skill)
            elif imageCount <= 6:
                for k in range(len(j["skills"])):
                    pixmap = get_skill_pixmap(
                        self.shared_data,
                        j["skills"][k]["name"],
                        j["skills"][k]["count"],
                    )

                    skill = SkillImage(
                        parent=self.frame,
                        pixmap=pixmap,
                        size=25,
                        x=18 + 25 * k,
                        y=213 + 51 * i,
                    )
                    skill.show()
                    self.settingSkillPreview.append(skill)
            else:
                line2 = imageCount // 2
                line1 = imageCount - line2

                for k in range(line1):
                    # button = QPushButton("", self.frame)
                    # button.setIcon(
                    #     QIcon(
                    #         get_skill_pixmap(
                    #             self.shared_data, j["skills"][k][0], j["skills"][k][1]
                    #         )
                    #     )
                    # )
                    # button.setIconSize(QSize(24, 24))
                    # button.setStyleSheet(
                    #     "QPushButton { background-color: transparent;}"
                    # )
                    # button.setFixedSize(25, 25)
                    # button.move(18 + 25 * k, 201 + 51 * i)
                    # button.show()

                    pixmap = get_skill_pixmap(
                        self.shared_data,
                        j["skills"][k]["name"],
                        j["skills"][k]["count"],
                    )

                    skill = SkillImage(
                        parent=self.frame,
                        pixmap=pixmap,
                        size=25,
                        x=18 + 25 * k,
                        y=201 + 51 * i,
                    )
                    skill.show()
                    self.settingSkillPreview.append(skill)
                for k in range(line2):
                    # button = QPushButton("", self.frame)
                    # button.setIcon(
                    #     QIcon(
                    #         get_skill_pixmap(
                    #             self.shared_data,
                    #             j["skills"][k + line1][0],
                    #             j["skills"][k + line1][1],
                    #         )
                    #     )
                    # )
                    # button.setIconSize(QSize(24, 24))
                    # button.setStyleSheet(
                    #     "QPushButton { background-color: transparent;}"
                    # )
                    # button.setFixedSize(25, 25)
                    # button.move(18 + 25 * k, 226 + 51 * i)
                    # button.show()

                    pixmap = get_skill_pixmap(
                        self.shared_data,
                        j["skills"][k + line1]["name"],
                        j["skills"][k + line1]["count"],
                    )

                    skill = SkillImage(
                        parent=self.frame,
                        pixmap=pixmap,
                        size=25,
                        x=18 + 25 * k,
                        y=226 + 51 * i,
                    )
                    skill.show()
                    self.settingSkillPreview.append(skill)

            if j["keyType"] == "off":
                text = ""
            else:
                text = j["key"]
            button = QPushButton(text, self.frame)
            button.setStyleSheet(
                "QPushButton { background-color: transparent; border: 0px; }"
            )
            button.setFixedSize(50, 50)
            button.move(182, 201 + 51 * i)
            button.show()
            adjust_font_size(button, text, 20)
            self.settingSkillKey.append(button)

            button = QPushButton("", self.frame)
            button.clicked.connect(partial(lambda x: self.editLinkSkill(x), i))
            button.setStyleSheet(
                """QPushButton { background-color: transparent; border: 0px; }
                QPushButton:hover { background-color: rgba(0, 0, 0, 32); border: 0px solid black; border-radius: 8px; }"""
            )
            button.setFixedSize(264, 50)
            button.move(18, 201 + 51 * i)
            button.show()
            self.settingSkillBackground.append(button)

            button = QPushButton("", self.frame)
            button.clicked.connect(partial(lambda x: self.removeLinkSkill(x), i))
            pixmap = QPixmap(convert_resource_path("resources\\image\\x.png"))
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
    def change_sidebar_to_4(self, data):
        self.master.get_popup_manager().close_popup()

        match self.shared_data.sidebar_type:
            case 1:
                self.delete_sidebar_1()
            case 2:
                self.delete_sidebar_2()
            case 3:
                self.delete_sidebar_3()
            case 4:
                return

        self.shared_data.sidebar_type = 4
        self.option_button2.setStyleSheet(
            """
            QPushButton {
                background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )

        self.frame.setFixedSize(300, 390 + 51 * len(data["skills"]))

        self.linkSkillPreviewFrame = QFrame(self.frame)
        self.linkSkillPreviewFrame.setStyleSheet(
            "QFrame { background-color: #ffffff; border-radius :5px; border: 1px solid black; }"
        )
        self.linkSkillPreviewFrame.setFixedSize(288, 48)
        self.linkSkillPreviewFrame.move(6, 140)
        self.linkSkillPreviewFrame.show()

        self.linkSkillPreviewList = []
        self.makeLinkSkillPreview(data)

        self.labelLinkType = QLabel("연계 유형", self.frame)
        self.labelLinkType.setToolTip(
            "자동: 매크로가 실행 중일 때 자동으로 연계 스킬을 사용합니다. 자동 연계스킬에 사용되는 스킬은 다른 자동 연계스킬에 사용될 수 없습니다.\n연계스킬은 매크로 작동 여부와 관계 없이 단축키를 입력해서 작동시킬 수 있습니다."
        )
        self.labelLinkType.setFont(CustomFont(12))
        self.labelLinkType.setFixedSize(80, 30)
        self.labelLinkType.move(40, 200)
        self.labelLinkType.show()

        self.ButtonLinkType0 = QPushButton("자동", self.frame)
        self.ButtonLinkType0.clicked.connect(lambda: self.setLinkSkillToAuto(data))
        if data["useType"] == "manual":
            self.ButtonLinkType0.setStyleSheet("color: #999999;")
        else:
            self.ButtonLinkType0.setStyleSheet("color: #000000;")
        self.ButtonLinkType0.setFont(CustomFont(12))
        self.ButtonLinkType0.setFixedSize(50, 30)
        self.ButtonLinkType0.move(155, 200)
        self.ButtonLinkType0.show()

        self.ButtonLinkType1 = QPushButton("수동", self.frame)
        self.ButtonLinkType1.clicked.connect(lambda: self.setLinkSkillToManual(data))
        if data["useType"] == "manual":
            self.ButtonLinkType1.setStyleSheet("color: #000000;")
        else:
            self.ButtonLinkType1.setStyleSheet("color: #999999;")
        self.ButtonLinkType1.setFont(CustomFont(12))
        self.ButtonLinkType1.setFixedSize(50, 30)
        self.ButtonLinkType1.move(210, 200)
        self.ButtonLinkType1.show()

        self.labelLinkKey = QLabel("단축키", self.frame)
        self.labelLinkKey.setToolTip(
            "매크로가 실행 중이지 않을 때 해당 연계스킬을 작동시킬 단축키입니다."
        )
        self.labelLinkKey.setFont(CustomFont(12))
        self.labelLinkKey.setFixedSize(80, 30)
        self.labelLinkKey.move(40, 235)
        self.labelLinkKey.show()

        self.ButtonLinkKey0 = QPushButton("설정안함", self.frame)
        self.ButtonLinkKey0.clicked.connect(lambda: self.setLinkSkillKey(data, 0))
        self.ButtonLinkKey0.setFixedSize(50, 30)
        self.ButtonLinkKey0.setFont(CustomFont(8))
        if data["keyType"] == "off":
            self.ButtonLinkKey0.setStyleSheet("color: #000000;")
        else:
            self.ButtonLinkKey0.setStyleSheet("color: #999999;")
        self.ButtonLinkKey0.move(155, 235)
        self.ButtonLinkKey0.show()

        self.ButtonLinkKey1 = QPushButton(data["key"], self.frame)
        self.ButtonLinkKey1.clicked.connect(lambda: self.setLinkSkillKey(data, 1))
        self.ButtonLinkKey1.setFixedSize(50, 30)
        adjust_font_size(self.ButtonLinkKey1, data["key"], 30)
        if data["keyType"] == "off":
            self.ButtonLinkKey1.setStyleSheet("color: #999999;")
        else:
            self.ButtonLinkKey1.setStyleSheet("color: #000000;")
        self.ButtonLinkKey1.move(210, 235)
        self.ButtonLinkKey1.show()

        self.linkSkillLineA = QFrame(self.frame)
        self.linkSkillLineA.setStyleSheet("QFrame { background-color: #b4b4b4;}")
        self.linkSkillLineA.setFixedSize(280, 1)
        self.linkSkillLineA.move(10, 274)
        self.linkSkillLineA.show()

        self.linkSkillImageList = []
        self.linkSkillCount = []
        self.linkSkillLineB = []
        self.linkSkillRemove = []
        for i, j in enumerate(data["skills"]):
            skill = QPushButton("", self.frame)
            skill.clicked.connect(
                partial(
                    lambda x: self.master.get_popup_manager().change_link_skill_type(x),
                    (data, i),
                )
            )
            # skill.setStyleSheet("background-color: transparent;")
            skill.setIcon(
                QIcon(get_skill_pixmap(self.shared_data, j["name"], j["count"]))
            )
            skill.setIconSize(QSize(50, 50))
            skill.setFixedSize(50, 50)
            skill.move(40, 281 + 51 * i)
            skill.setToolTip(
                "연계스킬을 구성하는 스킬의 목록과 사용 횟수를 설정할 수 있습니다.\n하나의 스킬이 너무 많이 사용되면 연계가 정상적으로 작동하지 않을 수 있습니다."
            )
            skill.show()
            self.linkSkillImageList.append(skill)

            button = QPushButton(
                f"{j["count"]} / {get_skill_details(self.shared_data, j["name"])['max_combo_count']}",
                self.frame,
            )
            button.clicked.connect(
                partial(
                    lambda x: self.master.get_popup_manager().editLinkSkillCount(x),
                    (data, i),
                )
            )
            button.setFixedSize(50, 30)
            button.setFont(CustomFont(12))
            button.move(210, 290 + 51 * i)
            button.show()
            self.linkSkillCount.append(button)

            remove = QPushButton("", self.frame)
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
            pixmap = QPixmap(convert_resource_path("resources\\image\\xAlpha.png"))
            remove.setIcon(QIcon(pixmap))
            remove.setIconSize(QSize(16, 16))
            remove.setFixedSize(32, 32)
            remove.move(266, 289 + 51 * i)
            remove.show()
            self.linkSkillRemove.append(remove)

            line = QFrame(self.frame)
            line.setStyleSheet("QFrame { background-color: #b4b4b4;}")
            line.setFixedSize(220, 1)
            line.move(40, 331 + 51 * i)
            line.show()
            self.linkSkillLineB.append(line)

        self.linkSkillPlus = QPushButton("", self.frame)
        self.linkSkillPlus.clicked.connect(lambda: self.addLinkSkill(data))
        self.linkSkillPlus.setStyleSheet(
            """QPushButton {
                    background-color: transparent; border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }"""
        )
        pixmap = QPixmap(convert_resource_path("resources\\image\\plus.png"))
        self.linkSkillPlus.setIcon(QIcon(pixmap))
        self.linkSkillPlus.setIconSize(QSize(24, 24))
        self.linkSkillPlus.setFixedSize(36, 36)
        self.linkSkillPlus.move(132, 289 + 51 * len(data["skills"]))
        self.linkSkillPlus.show()

        self.linkSkillCancelButton = QPushButton("취소", self.frame)
        self.linkSkillCancelButton.clicked.connect(self.cancelEditingLinkSkill)
        self.linkSkillCancelButton.setFixedSize(120, 32)
        self.linkSkillCancelButton.setFont(CustomFont(12))
        self.linkSkillCancelButton.move(15, 350 + 51 * len(data["skills"]))
        self.linkSkillCancelButton.show()

        self.linkSkillSaveButton = QPushButton("저장", self.frame)
        self.linkSkillSaveButton.clicked.connect(
            lambda: self.saveEditingLinkSkill(data)
        )
        self.linkSkillSaveButton.setFixedSize(120, 32)
        self.linkSkillSaveButton.setFont(CustomFont(12))
        self.linkSkillSaveButton.move(165, 350 + 51 * len(data["skills"]))
        self.linkSkillSaveButton.show()

    ## 링크스킬 변경 팝업창 클릭시 실행
    def oneLinkSkillTypePopupClick(self, var):
        self.master.get_popup_manager().close_popup()
        data, num, i = var
        skill_name = get_available_skills(self.shared_data)[i]

        if data["skills"][num]["name"] == skill_name:
            return

        data["skills"][num]["name"] = skill_name
        data["skills"][num]["count"] = 1
        data["useType"] = "manual"

        if self.checkLinkSkillExceed(data, i):
            self.master.get_popup_manager().make_notice_popup("exceedMaxLinkSkill")

        self.reload_sidebar4(data)

    ## 링크스킬 목록에서 하나 삭제
    def removeOneLinkSkill(self, var):
        self.master.get_popup_manager().close_popup()
        data, num = var

        if len(data["skills"]) == 1:
            return

        del data["skills"][num]
        data["useType"] = "manual"
        self.reload_sidebar4(data)

    ## 링크스킬 저장
    def saveEditingLinkSkill(self, data):
        self.master.get_popup_manager().close_popup()

        num = data.pop("num")
        if num == -1:
            self.shared_data.link_skills.append(data)
        else:
            self.shared_data.link_skills[num] = data

        save_data(self.shared_data)
        self.delete_sidebar_4()
        self.shared_data.sidebar_type = -1
        self.change_sidebar_to_3()

    ## 링크스킬 취소
    def cancelEditingLinkSkill(self):
        self.master.get_popup_manager().close_popup()

        self.delete_sidebar_4()
        self.shared_data.sidebar_type = -1
        self.change_sidebar_to_3()

    ## 링크스킬 추가
    def addLinkSkill(self, data):
        self.master.get_popup_manager().close_popup()

        data["skills"].append(
            {"name": get_available_skills(self.shared_data)[0], "count": 1}
        )
        data["useType"] = "manual"
        if self.checkLinkSkillExceed(data, 0):
            self.master.get_popup_manager().make_notice_popup("exceedMaxLinkSkill")
        self.reload_sidebar4(data)

    ## 링크스킬 사용 횟수 팝업창 클릭시 실행
    def onLinkSkillCountPopupClick(self, var):
        self.master.get_popup_manager().close_popup()
        data, num, i = var

        data["skills"][num]["count"] = i
        if self.checkLinkSkillExceed(data, i):
            self.master.get_popup_manager().make_notice_popup("exceedMaxLinkSkill")
        data["useType"] = "manual"
        self.reload_sidebar4(data)

    # 연계스킬에서 스킬 사용 횟수가 초과되었는지 확인
    def checkLinkSkillExceed(self, data, skill) -> bool:
        maxSkill = get_skill_details(
            self.shared_data, get_available_skills(self.shared_data)[skill]
        )["max_combo_count"]

        for i in data["skills"]:
            s = i["name"]
            count = i["count"]
            if get_available_skills(self.shared_data)[skill] == s:
                maxSkill -= count

        return maxSkill < 0

    ## 링크스킬 키 설정
    def setLinkSkillKey(self, data, num):
        if num == 0:
            data["keyType"] = "off"
            self.reload_sidebar4(data)
        else:
            self.master.get_popup_manager().activatePopup("settingLinkSkillKey")
            self.master.get_popup_manager().makeKeyboardPopup(("LinkSkill", data))

    ## 링크스킬 자동으로 설정
    def setLinkSkillToAuto(self, data):
        self.master.get_popup_manager().close_popup()
        if data["useType"] == "auto":
            return

        num = data["num"]

        for i in data["skills"]:
            if not (i["name"] in self.shared_data.equipped_skills):
                self.master.get_popup_manager().make_notice_popup("skillNotSelected")
                return

        # 사용여부는 연계스킬에 적용되지 않음
        # for i in data[2]:
        #     if not self.useSkill[i[0]]:
        #         self.makeNoticePopup("skillNotUsing")
        #         return
        if len(self.shared_data.link_skills) != 0:
            prevData = copy.deepcopy(self.shared_data.link_skills[num])
            self.shared_data.link_skills[num] = copy.deepcopy(data)
            self.shared_data.link_skills[num].pop("num")
            autoSkillList = []
            for i in self.shared_data.link_skills:
                if i["useType"] == "auto":
                    for j in range(len(i["skills"])):
                        autoSkillList.append(i["skills"][j]["name"])
            self.shared_data.link_skills[num] = prevData

            for i in range(len(data["skills"])):
                if data["skills"][i]["name"] in autoSkillList:
                    self.master.get_popup_manager().make_notice_popup(
                        "autoAlreadyExist"
                    )
                    return

        data["useType"] = "auto"
        self.reload_sidebar4(data)

    ## 링크스킬 수동으로 설정
    def setLinkSkillToManual(self, data):
        self.master.get_popup_manager().close_popup()
        if data["useType"] == "manual":
            return

        data["useType"] = "manual"
        self.reload_sidebar4(data)

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
                skill.setIcon(
                    QIcon(get_skill_pixmap(self.shared_data, j["name"], j["count"]))
                )
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
                skill.setIcon(
                    QIcon(get_skill_pixmap(self.shared_data, j["name"], j["count"]))
                )
                skill.setIconSize(QSize(size, size))
                skill.setFixedSize(size, size)
                skill.move(size * i, round((48 - size) * 0.5))
                skill.show()

                self.linkSkillPreviewList.append(skill)

    ## 연계스킬 제거
    def removeLinkSkill(self, num):
        self.master.get_popup_manager().close_popup()
        del self.shared_data.link_skills[num]
        self.delete_sidebar_3()
        self.shared_data.sidebar_type = -1
        self.change_sidebar_to_3()
        save_data(self.shared_data)

    ## 연계스킬 설정
    def editLinkSkill(self, num):
        self.master.get_popup_manager().close_popup()
        self.master.get_main_ui().cancel_skill_selection()

        data = copy.deepcopy(self.shared_data.link_skills[num])
        data["num"] = num
        self.delete_sidebar_3()
        self.shared_data.sidebar_type = -1
        self.change_sidebar_to_4(data)

    ## 새 연계스킬 생성
    def makeNewLinkSkill(self):
        def findKey():
            for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if not is_key_used(self.shared_data, char):
                    return char
            return None

        self.master.get_popup_manager().close_popup()
        self.master.get_main_ui().cancel_skill_selection()

        data = {
            "useType": "manual",
            "keyType": "off",
            "key": findKey(),
            "skills": [
                {"name": get_available_skills(self.shared_data)[0], "count": 1},
            ],
            "num": -1,
        }
        self.delete_sidebar_3()
        self.shared_data.sidebar_type = -1
        self.change_sidebar_to_4(data)

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


class SideBarButton(QPushButton):
    def __init__(self, master: MainWindow, sidebar: Sidebar, parent: QWidget, num):
        super().__init__("", parent)  # self.sidebarOptionFrame

        self.sidebar = sidebar
        self.master = master

        match num:
            case 0:
                self.clicked.connect(self.sidebar.change_sidebar_to_1)
                pixmap = QPixmap(convert_resource_path("resources\\image\\setting.png"))
                self.setStyleSheet(
                    """
                        QPushButton {
                            background-color: #dddddd; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 8px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
                        }
                        QPushButton:hover {
                            background-color: #dddddd;
                        }
                    """
                )
                self.move(0, 0)
            case 1:
                self.clicked.connect(self.sidebar.change_sidebar_to_2)
                pixmap = QPixmap(
                    convert_resource_path("resources\\image\\usageSetting.png")
                )
                self.setStyleSheet(
                    """
                        QPushButton {
                            background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
                        }
                        QPushButton:hover {
                            background-color: #dddddd;
                        }
                    """
                )
                self.move(0, 34)
            case 2:
                self.clicked.connect(self.sidebar.change_sidebar_to_3)
                pixmap = QPixmap(
                    convert_resource_path("resources\\image\\linkSetting.png")
                )
                self.setStyleSheet(
                    """
                        QPushButton {
                            background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px
                        }
                        QPushButton:hover {
                            background-color: #dddddd;
                        }
                    """
                )
                self.move(0, 68)
            case 3:
                self.clicked.connect(lambda: self.master.change_layout(1))
                # button.clicked.connect(self.changeLayout)
                pixmap = QPixmap(
                    convert_resource_path("resources\\image\\simulationSidebar.png")
                )
                self.setStyleSheet(
                    """
                        QPushButton {
                            background-color: #ffffff; border: 1px solid #b4b4b4; border-top-left-radius :0px; border-top-right-radius : 0px; border-bottom-left-radius : 0px; border-bottom-right-radius : 8px
                        }
                        QPushButton:hover {
                            background-color: #dddddd;
                        }
                    """
                )
                self.move(0, 102)

            case _:
                return

        self.setIcon(QIcon(pixmap))
        self.setIconSize(QSize(32, 32))
        self.setFixedSize(34, 34)
