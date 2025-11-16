from app.scripts.shared_data import SharedData
from .misc import convert_resource_path

from .data_manager import save_data, load_data, add_preset, remove_preset
from .misc import (
    get_skill_pixmap,
    adjust_font_size,
    adjust_text_length,
    get_available_skills,
)
from .shared_data import UI_Variable
from .custom_classes import (
    CustomShadowEffect,
    SkillImage,
    CustomFont,
)
from .run_macro import init_macro, add_task_list

from functools import partial

from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QSizePolicy,
    QLayout,
)


if TYPE_CHECKING:
    from .main_window import MainWindow
    from .shared_data import SharedData


class MainUI(QFrame):
    def __init__(
        self,
        master,
        shared_data: SharedData,
    ) -> None:
        super().__init__()

        self.master = master

        self.shared_data: SharedData = shared_data
        self.ui_var = UI_Variable()

        self.macro_tab = TabWidget(self, self.shared_data)

        layout = QVBoxLayout()
        layout.addWidget(self.macro_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

    ## 탭 변경
    def changeTab(self, num: int) -> None:
        load_data(self.shared_data, num)

        if self.shared_data.sidebar_type != 1:
            self.master.get_sidebar().change_sidebar_to_1()

        for tabNum in range(len(self.shared_data.tab_names)):
            if tabNum == self.shared_data.recent_preset:
                self.tab_backgrounds[tabNum].setStyleSheet(
                    """background-color: #eeeeff; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )
            else:
                self.tab_backgrounds[tabNum].setStyleSheet(
                    """background-color: #dddddd; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )

            if tabNum == self.shared_data.recent_preset:
                self.tab_buttons[tabNum].setStyleSheet(
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
                self.tab_buttons[tabNum].setStyleSheet(
                    """
                    QPushButton {
                        background-color: #dddddd; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #eeeeee;
                    }
                """
                )
            if tabNum == self.shared_data.recent_preset:
                self.tab_remove_buttons[tabNum].setStyleSheet(
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
                self.tab_remove_buttons[tabNum].setStyleSheet(
                    """
                    QPushButton {
                        background-color: transparent; border-radius: 20px;
                    }
                    QPushButton:hover {
                        background-color: #eeeeee;
                    }
                """
                )

        self.cancel_skill_selection()
        for i in range(8):
            self.equippable_skill_buttons[i].setIcon(
                QIcon(
                    get_skill_pixmap(
                        self.shared_data,
                        skill_name=get_available_skills(self.shared_data)[i],
                    )
                )
            )
            self.equippable_skill_names[i].setText(
                self.shared_data.skill_data[self.shared_data.server_ID]["jobs"][
                    self.shared_data.job_ID
                ]["skills"][i]
            )
        for i in range(6):
            self.equipped_skill_buttons[i].setIcon(
                QIcon(
                    get_skill_pixmap(
                        self.shared_data, self.shared_data.equipped_skills[i]
                    )
                )
            )

        self.master.get_sidebar().buttonServerList.setText(self.shared_data.server_ID)
        self.master.get_sidebar().buttonJobList.setText(self.shared_data.job_ID)

        self.master.get_sidebar().buttonInputDelay.setText(
            str(self.shared_data.delay_input)
        )
        rgb = 153 if self.shared_data.delay_type == 1 else 0
        self.master.get_sidebar().buttonDefaultDelay.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )
        rgb = 153 if self.shared_data.delay_type == 0 else 0
        self.master.get_sidebar().buttonInputDelay.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )

        self.master.get_sidebar().buttonInputCooltime.setText(
            str(self.shared_data.cooltime_reduction_input)
        )
        rgb = 153 if self.shared_data.cooltime_reduction_type == 1 else 0
        self.master.get_sidebar().buttonDefaultCooltime.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )
        rgb = 153 if self.shared_data.cooltime_reduction_type == 0 else 0
        self.master.get_sidebar().buttonInputCooltime.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )

        self.master.get_sidebar().buttonInputStartKey.setText(
            str(self.shared_data.start_key_input)
        )
        rgb = 153 if self.shared_data.start_key_type == 1 else 0
        self.master.get_sidebar().buttonDefaultStartKey.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )
        rgb = 153 if self.shared_data.start_key_type == 0 else 0
        self.master.get_sidebar().buttonInputStartKey.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )

        rgb = 153 if self.shared_data.mouse_click_type == 1 else 0
        self.master.get_sidebar().button1stMouseType.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )
        rgb = 153 if self.shared_data.mouse_click_type == 0 else 0
        self.master.get_sidebar().button2ndMouseType.setStyleSheet(
            f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        )

        # self.update()
        self.update_position()
        save_data(self.shared_data)

    ## 탭 클릭
    def onTabClick(self, num: int) -> None:
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        if self.shared_data.recent_preset == num:
            if self.shared_data.active_popup == "changeTabName":
                self.master.get_popup_manager().close_popup()
            else:
                self.master.get_popup_manager().activatePopup("changeTabName")
                self.master.get_popup_manager().makePopupInput("tabName", num)
            return
        self.master.get_popup_manager().close_popup()

        self.changeTab(num)

    ## 탭 추가버튼 클릭
    def onTabAddClick(self) -> None:
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")

            return

        self.master.get_popup_manager().close_popup()

        add_preset(shared_data=self.shared_data)

        tabNum: int = len(self.shared_data.tab_names)
        load_data(self.shared_data, tabNum)

        tabBackground = QLabel("", self.parent)
        tabBackground.setStyleSheet(
            """background-color: #eeeef5; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
        )
        tabBackground.setFixedSize(250, 50)
        tabBackground.move(340 + 250 * tabNum, 20)
        tabBackground.setGraphicsEffect(CustomShadowEffect(5, -2))
        tabBackground.show()

        tabButton = QPushButton(f" {self.shared_data.tab_names[tabNum]}", self.parent)
        tabButton.clicked.connect(lambda: self.onTabClick(tabNum))
        tabButton.setFont(CustomFont(12))
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

        tabRemoveButton = QPushButton("", self.parent)
        tabRemoveButton.clicked.connect(lambda: self.on_tab_remove_clicked(tabNum))
        tabRemoveButton.setFont(CustomFont(16))
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
        pixmap = QPixmap(convert_resource_path("resources\\image\\x.png"))
        tabRemoveButton.setIcon(QIcon(pixmap))
        tabRemoveButton.setFixedSize(40, 40)
        tabRemoveButton.move(545 + 250 * tabNum, 25)
        tabRemoveButton.show()

        self.tab_buttons.append(tabButton)
        self.tab_backgrounds.append(tabBackground)
        self.tab_remove_buttons.append(tabRemoveButton)

        self.tab_add_button.move(350 + 250 * len(self.shared_data.tab_names), 25)

        self.changeTab(tabNum)

    ## 탭 제거버튼 클릭
    def on_tab_remove_clicked(self, num: int) -> None:
        self.shared_data.is_tab_remove_popup_activated = True
        self.tabRemoveBackground = QFrame(self.parent)
        self.tabRemoveBackground.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        self.tabRemoveBackground.setFixedSize(self.master.width(), self.master.height())
        self.tabRemoveBackground.show()

        self.tabRemoveFrame = QFrame(self.tabRemoveBackground)
        self.tabRemoveFrame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 20px; }"
        )
        self.tabRemoveFrame.setFixedSize(340, 140)
        self.tabRemoveFrame.move(
            round(self.master.width() * 0.5 - 170),
            round(self.master.height() * 0.5 - 60),
        )
        self.tabRemoveFrame.setGraphicsEffect(CustomShadowEffect(2, 2, 20))
        self.tabRemoveFrame.show()

        self.tabRemoveNameLabel = QLabel("", self.tabRemoveFrame)
        self.tabRemoveNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabRemoveNameLabel.setFont(CustomFont(12))
        self.tabRemoveNameLabel.setFixedSize(330, 30)
        self.tabRemoveNameLabel.setText(
            adjust_text_length(
                f'정말 "{self.shared_data.tab_names[num]}',
                self.tabRemoveNameLabel,
                margin=5,
            )
            + '"'
        )
        self.tabRemoveNameLabel.move(5, 10)
        self.tabRemoveNameLabel.show()

        self.tabRemoveLabel = QLabel("탭을 삭제하시겠습니까?", self.tabRemoveFrame)
        self.tabRemoveLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabRemoveLabel.setFont(CustomFont(12))
        self.tabRemoveLabel.setFixedSize(330, 30)
        self.tabRemoveLabel.move(5, 40)
        self.tabRemoveLabel.show()

        self.settingJobButton = QPushButton("예", self.tabRemoveFrame)
        self.settingJobButton.setFont(CustomFont(12))
        self.settingJobButton.clicked.connect(
            lambda: self.on_tab_remove_popup_clicked(num)
        )
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
        self.settingJobButton.setGraphicsEffect(CustomShadowEffect(2, 2, 20))
        self.settingJobButton.show()

        self.settingJobButton = QPushButton("아니오", self.tabRemoveFrame)
        self.settingJobButton.setFont(CustomFont(12))
        self.settingJobButton.clicked.connect(
            lambda: self.on_tab_remove_popup_clicked(num, False)
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
        self.settingJobButton.setGraphicsEffect(CustomShadowEffect(2, 2, 20))
        self.settingJobButton.show()

    def on_tab_remove_popup_clicked(self, num: int = 0, remove: bool = True) -> None:
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        self.master.get_popup_manager().close_popup()
        self.tabRemoveBackground.deleteLater()
        self.shared_data.is_tab_remove_popup_activated = False

        if not remove:
            return

        tabCount = len(self.shared_data.tab_names)

        if tabCount != 1:
            if self.shared_data.recent_preset == num:
                if (tabCount - 1) > num:
                    self.shared_data.tab_names.pop(num)
                    remove_preset(num)
                    self.tab_buttons[num].deleteLater()
                    self.tab_buttons.pop(num)
                    self.tab_backgrounds[num].deleteLater()
                    self.tab_backgrounds.pop(num)
                    self.tab_remove_buttons[num].deleteLater()
                    self.tab_remove_buttons.pop(num)

                    # print(self.tabButtonList)

                    for i, j in enumerate(self.tab_buttons):
                        j.clicked.disconnect()
                        j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                        self.tab_remove_buttons[i].clicked.disconnect()
                        self.tab_remove_buttons[i].clicked.connect(
                            partial(lambda x: self.on_tab_remove_clicked(x), i)
                        )

                        self.tab_backgrounds[i].move(340 + 250 * i, 20)
                        self.tab_buttons[i].move(345 + 250 * i, 25)
                        self.tab_remove_buttons[i].move(545 + 250 * i, 25)
                    self.tab_add_button.move(
                        350 + 250 * len(self.shared_data.tab_names), 25
                    )

                    self.changeTab(num)
                else:
                    self.shared_data.tab_names.pop(num)
                    remove_preset(num)
                    self.tab_buttons[num].deleteLater()
                    self.tab_buttons.pop(num)
                    self.tab_backgrounds[num].deleteLater()
                    self.tab_backgrounds.pop(num)
                    self.tab_remove_buttons[num].deleteLater()
                    self.tab_remove_buttons.pop(num)

                    self.tab_add_button.move(
                        350 + 250 * len(self.shared_data.tab_names), 25
                    )

                    self.changeTab(num - 1)
                    self.shared_data.recent_preset = num - 1
            elif self.shared_data.recent_preset > num:
                self.shared_data.tab_names.pop(num)
                remove_preset(num)
                self.tab_buttons[num].deleteLater()
                self.tab_buttons.pop(num)
                self.tab_backgrounds[num].deleteLater()
                self.tab_backgrounds.pop(num)
                self.tab_remove_buttons[num].deleteLater()
                self.tab_remove_buttons.pop(num)

                for i, j in enumerate(self.tab_buttons):
                    j.clicked.disconnect()
                    j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                    self.tab_remove_buttons[i].clicked.disconnect()
                    self.tab_remove_buttons[i].clicked.connect(
                        partial(lambda x: self.on_tab_remove_clicked(x), i)
                    )

                    self.tab_backgrounds[i].move(340 + 250 * i, 20)
                    self.tab_buttons[i].move(345 + 250 * i, 25)
                    self.tab_remove_buttons[i].move(545 + 250 * i, 25)
                self.tab_add_button.move(
                    350 + 250 * len(self.shared_data.tab_names), 25
                )

                self.changeTab(self.shared_data.recent_preset - 1)
            elif self.shared_data.recent_preset < num:
                # print(self.shared_data.tabNames)
                # print(num)
                self.shared_data.tab_names.pop(num)
                remove_preset(num)
                self.tab_buttons[num].deleteLater()
                self.tab_buttons.pop(num)
                self.tab_backgrounds[num].deleteLater()
                self.tab_backgrounds.pop(num)
                self.tab_remove_buttons[num].deleteLater()
                self.tab_remove_buttons.pop(num)

                for i, j in enumerate(self.tab_buttons):
                    j.clicked.disconnect()
                    j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                    self.tab_remove_buttons[i].clicked.disconnect()
                    self.tab_remove_buttons[i].clicked.connect(
                        partial(lambda x: self.on_tab_remove_clicked(x), i)
                    )

                    self.tab_backgrounds[i].move(340 + 250 * i, 20)
                    self.tab_buttons[i].move(345 + 250 * i, 25)
                    self.tab_remove_buttons[i].move(545 + 250 * i, 25)
                self.tab_add_button.move(
                    350 + 250 * len(self.shared_data.tab_names), 25
                )
        else:
            remove_preset(0)
            load_data(self.shared_data, 0)
            self.changeTab(0)
            self.tab_buttons[0].setText(" " + self.shared_data.tab_names[0])

        # self.update()
        self.update_position()
        save_data(self.shared_data)

    def cancel_skill_selection(self) -> None:  # main_ui로 이동
        """
        스킬 장착 취소. 다른 곳 클릭시 실행됨
        """

        self.shared_data.selected_skill = -1

        for i in range(6):
            self.equipped_skill_buttons[i].setStyleSheet(
                "QPushButton { background-color: #bbbbbb; border-radius :10px; }"
            )
            # self.selected_skill_buttons[i].setStyleSheet(
            #     f"QPushButton {{ background-color: {self.selected_skill_colors[i]}; border-radius :10px; }}"
            # )

        for i in range(8):
            self.equippable_skill_buttons[i].setStyleSheet(
                "QPushButton { background-color: #bbbbbb; border-radius :10px; }"
            )

    def on_equipped_skill_clicked(self, num: int) -> None:
        """
        하단 스킬 아이콘 클릭시 실행됨
        """

        # print(self.shared_data.selectedSkillList[num])

        # 연계스킬 편집 중이면 수정 불가능
        if self.shared_data.sidebar_type == 4:
            self.cancel_skill_selection()
            self.master.get_popup_manager().make_notice_popup("editingLinkSkill")
            return

        # 매크로가 실행중이면 수정 불가능
        if self.shared_data.is_activated:
            self.cancel_skill_selection()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        # 이전에 선택된 스킬
        equipped_skill: str = self.shared_data.equipped_skills[num]

        # 선택된 스킬을 다시 클릭했을 때 -> 해제
        if self.shared_data.selected_skill == num and equipped_skill:
            # 빈 스킬 아이콘으로 변경
            self.equipped_skill_buttons[num].setIcon(
                QIcon(get_skill_pixmap(shared_data=self.shared_data))
            )

            self.clear_equipped_skill(skill=equipped_skill)

            self.shared_data.equipped_skills[num] = ""
            self.cancel_skill_selection()
            save_data(self.shared_data)
            return

        # 이전 선택 칸과 지금이 다르고, 이전이 빈 스킬 이었다면 -> 취소
        if self.shared_data.selected_skill != -1:
            self.cancel_skill_selection()
            return

        # 스킬 선택중이 아니었다면
        self.shared_data.selected_skill = num

        # 선택된 스킬 아이콘 변경
        self.equipped_skill_buttons[num].setStyleSheet(
            "QPushButton { background-color: #bbbbbb; border-radius :10px; border: 4px solid red; }"
        )

        # 장착 가능한 스킬 아이콘들 변경. 이미 장착된 스킬은 변경 X
        for i in range(8):
            if (
                get_available_skills(shared_data=self.shared_data)[i]
                not in self.shared_data.equipped_skills
            ):
                self.equippable_skill_buttons[i].setStyleSheet(
                    "QPushButton { background-color: #bbbbbb; border-radius :10px; border: 4px solid #00b000; }"
                )

    def on_equippable_skill_clicked(self, num: int) -> None:  # main_ui로 이동
        """
        상단 스킬 아이콘 클릭 (8개)
        """

        # 선택된 스킬
        selected_skill: str = get_available_skills(shared_data=self.shared_data)[num]
        # 선택된 칸에 장착되어있던 스킬
        equipped_skill: str = self.shared_data.equipped_skills[
            self.shared_data.selected_skill
        ]

        # 연계스킬 편집 중이면 수정 불가능
        if self.shared_data.sidebar_type == 4:
            self.cancel_skill_selection()
            return

        # 스킬 선택중이 아닐 때 -> 아무것도 하지 않음
        if self.shared_data.selected_skill == -1:
            return

        # 이미 선택된 스킬을 선택했을 때 -> 취소
        if selected_skill in self.shared_data.equipped_skills:
            self.cancel_skill_selection()
            return

        # 이미 스킬이 장착된 칸의 스킬을 변경하는 경우
        if equipped_skill:
            self.clear_equipped_skill(skill=equipped_skill)

        # 선택된 스킬칸에 새로운 스킬 장착
        self.shared_data.equipped_skills[self.shared_data.selected_skill] = (
            get_available_skills(shared_data=self.shared_data)[num]
        )

        self.equipped_skill_buttons[self.shared_data.selected_skill].setIcon(
            QIcon(
                get_skill_pixmap(
                    shared_data=self.shared_data, skill_name=selected_skill
                )
            )
        )

        if self.shared_data.sidebar_type == 2:
            self.master.get_sidebar().skill_icons[selected_skill].setPixmap(
                get_skill_pixmap(
                    shared_data=self.shared_data, skill_name=selected_skill
                )
            )

        self.shared_data.selected_skill = -1
        save_data(self.shared_data)
        self.cancel_skill_selection()

    ## 스킬 단축키 설정 버튼 클릭
    def onSkillKeyClick(self, num):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "skillKey":
            self.master.get_popup_manager().close_popup()
            return
        self.master.get_popup_manager().close_popup()

        self.master.get_popup_manager().activatePopup("skillKey")
        self.master.get_popup_manager().makeKeyboardPopup(["skillKey", num])

    def clear_equipped_skill(self, skill: str):
        """
        장착된 스킬 초기화
        """

        # 연계스킬 수동 사용으로 변경
        for i, j in enumerate(self.shared_data.link_skills):
            for k in j["skills"]:
                if k["name"] == skill:
                    self.shared_data.link_skills[i]["useType"] = "manual"

        # 스킬 사용 우선순위 리로드
        prev_priority: int = self.shared_data.skill_priority[skill]

        # 해제되는 스킬의 우선순위가 있다면
        if prev_priority:
            self.shared_data.skill_priority[skill] = 0

            # 해당 스킬보다 높은 우선순위의 스킬들 우선순위 -1
            for j, k in self.shared_data.skill_priority.items():  # str, int
                if k > prev_priority:
                    self.shared_data.skill_priority[j] -= 1

                    if self.shared_data.sidebar_type == 2:
                        self.master.get_sidebar().skill_sequence[j].setText(str(k - 1))

        # 스킬 연계설정이라면 -> 리로드
        if self.shared_data.sidebar_type == 3:
            self.master.get_sidebar().delete_sidebar_3()
            self.shared_data.sidebar_type = -1
            self.master.get_sidebar().change_sidebar_to_3()

        # 사이드바가 스킬 사용설정이라면
        if self.shared_data.sidebar_type == 2:
            self.master.get_sidebar().skill_icons[skill].setPixmap(
                get_skill_pixmap(
                    shared_data=self.shared_data,
                    skill_name=skill,
                    state=-2,
                )
            )

            self.master.get_sidebar().skill_sequence[skill].setText("-")

    def show_preview_skills(self) -> None:
        """
        스킬 미리보기 프레임에 스킬 아이콘 설정
        """

        # 매크로가 실행중이 아니라면 매크로 초반 시뮬레이션 실행
        if not self.shared_data.is_activated:
            init_macro(self.shared_data)
            add_task_list(self.shared_data, print_info=False)
            # self.printMacroInfo(True)
            # print(self.shared_data.taskList)

        # 이전 미리보기 스킬 버튼 삭제
        for i in self.shared_data.preview_skills:
            i.deleteLater()

        self.shared_data.preview_skills.clear()

        fwidth: int = self.skill_preview_frame.width()
        width: int = self.skill_preview_frame.width() // 6
        size: int = self.skill_preview_frame.height()

        count: int = min(len(self.shared_data.task_list), 6)

        # 각 미리보기 스킬 이미지 추가
        for i in range(count):
            pixmap: QPixmap = get_skill_pixmap(
                self.shared_data,
                self.shared_data.equipped_skills[self.shared_data.task_list[i]],
                1 if self.shared_data.is_activated else -2,
            )

            skill: SkillImage = SkillImage(
                parent=self.skill_preview_frame,
                pixmap=pixmap,
                size=size,
                x=(fwidth - width * count) // 2 + width * i,
                y=0,
            )
            skill.show()

            self.shared_data.preview_skills.append(skill)

    ## 창 크기 조절시 위젯 위치, 크기 조절 => 각 클래스로 분리
    def update_position(self):
        self.master.get_sidebar().scroll_area.setFixedSize(
            319, self.master.height() - 24
        )
        xAddedSize = self.master.width() - 960
        xMultSize = ((self.master.width() - 400) / 560 - 1) * 0.5
        yAddedSize = self.master.height() - 540
        yMultSize = ((self.master.height() - 90) / 450 - 1) * 0.5
        self.background.setFixedSize(
            self.master.width() - 400, self.master.height() - 90
        )

        self.skill_preview_frame.move(
            round(136 + xAddedSize * 0.5 - 288 * xMultSize * 0.5),
            round(10 + yAddedSize * 0.1 - 48 * yMultSize * 0.5),
        )
        self.skill_preview_frame.setFixedSize(
            round(288 * (xMultSize + 1)), round(48 * (yMultSize + 1))
        )
        for i, j in enumerate(self.shared_data.preview_skills):
            j.setFixedSize(
                round((288 * (xMultSize + 1) / 6)), round(48 * (yMultSize + 1))
            )
            j.move(
                round(
                    (
                        self.skill_preview_frame.width()
                        - j.width() * len(self.shared_data.preview_skills)
                    )
                    * 0.5
                )
                + j.width() * i,
                0,
            )
            # j.setIconSize(QSize(min(j.width(), j.height()), min(j.width(), j.height())))

        for i, j in enumerate(self.equippable_skill_frames):
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

        for i in self.equippable_skill_buttons:
            i.setFixedSize(round(64 * (xMultSize + 1)), round(64 * (yMultSize + 1)))
            i.setIconSize(QSize(min(i.width(), i.height()), min(i.width(), i.height())))

        for i, j in enumerate(self.equippable_skill_names):
            j.move(0, round(64 * (yMultSize + 1)))
            j.setFixedSize(round(64 * (xMultSize + 1)), round(24 * (yMultSize + 1)))
            j.setText(
                self.shared_data.skill_data[self.shared_data.server_ID]["jobs"][
                    self.shared_data.job_ID
                ]["skills"][i]
            )
            j.setFont(CustomFont(12))

        self.skill_selection_line.move(20, round(309 + yAddedSize * 0.7))
        self.skill_selection_line.setFixedSize(520 + xAddedSize, 1)
        for i, j in enumerate(self.equipped_skill_frames):
            j.move(
                round(
                    (38 + xAddedSize * 0.1)
                    + (64 + (20 + xAddedSize * 0.16)) * i
                    - 64 * xMultSize * 0.5
                ),
                round(330 + yAddedSize * 0.9 - 96 * yMultSize * 0.5),
            )
            j.setFixedSize(round(64 * (xMultSize + 1)), round(96 * (yMultSize + 1)))
        for i in self.equipped_skill_buttons:
            i.setFixedSize(round(64 * (xMultSize + 1)), round(64 * (yMultSize + 1)))
            i.setIconSize(QSize(min(i.width(), i.height()), min(i.width(), i.height())))
        for i, j in enumerate(self.equipped_skill_keys):
            j.move(0, round(72 * (yMultSize + 1)))
            j.setFixedSize(round(64 * (xMultSize + 1)), round(24 * (yMultSize + 1)))
            adjust_font_size(j, self.shared_data.skill_keys[i], 20)

        if 460 + 200 * len(self.shared_data.tab_names) <= self.master.width():
            for tabNum in range(len(self.shared_data.tab_names)):
                self.tab_backgrounds[tabNum].move(360 + 200 * tabNum, 20)
                self.tab_backgrounds[tabNum].setFixedSize(200, 50)
                self.tab_buttons[tabNum].move(365 + 200 * tabNum, 25)
                self.tab_buttons[tabNum].setFixedSize(190, 40)
                self.tab_buttons[tabNum].setText(
                    adjust_text_length(
                        f" {self.shared_data.tab_names[tabNum]}",
                        self.tab_buttons[tabNum],
                    )
                )
                self.tab_remove_buttons[tabNum].move(515 + 200 * tabNum, 25)
                self.tab_add_button.move(
                    370 + 200 * len(self.shared_data.tab_names), 25
                )

                if self.shared_data.active_popup == "changeTabName":
                    self.master.get_popup_manager().settingPopupFrame.move(
                        360 + 200 * self.shared_data.recent_preset, 80
                    )
        else:
            width = round((self.master.width() - 460) / len(self.shared_data.tab_names))
            for tabNum in range(len(self.shared_data.tab_names)):
                self.tab_backgrounds[tabNum].move(360 + width * tabNum, 20)
                self.tab_backgrounds[tabNum].setFixedSize(width, 50)
                self.tab_buttons[tabNum].move(365 + width * tabNum, 25)
                self.tab_buttons[tabNum].setFixedSize(width - 10, 40)
                self.tab_buttons[tabNum].setText(
                    adjust_text_length(
                        f" {self.shared_data.tab_names[tabNum]}",
                        self.tab_buttons[tabNum],
                    )
                )
                self.tab_remove_buttons[tabNum].move(315 + width * (tabNum + 1), 25)
                self.tab_add_button.move(self.master.width() - 80, 25)
                # self.tabAddButton.move(350 + width * len(self.shared_data.tabNames), 25)
            if self.shared_data.active_popup == "changeTabName":
                self.master.get_popup_manager().settingPopupFrame.move(
                    360 + width * self.shared_data.recent_preset, 80
                )

        if self.shared_data.is_tab_remove_popup_activated:
            self.tabRemoveBackground.setFixedSize(
                self.master.width(), self.master.height()
            )
            self.tabRemoveFrame.move(
                round(self.master.width() * 0.5 - 170),
                round(self.master.height() * 0.5 - 60),
            )
            self.tabRemoveBackground.raise_()


class TabWidget(QTabWidget):
    def __init__(self, main_frame: QWidget, shared_data: SharedData):
        super().__init__(main_frame)

        self.shared_data: SharedData = shared_data

        self.TAB_BACKGROUND_COLOR = "#eeeeff"
        self.TAB_BORDER_COLOR = "#cccccc"
        self.TAB_DEFAULT_COLOR = "#eeeeee"
        self.TAB_HOVER_COLOR = "#dddddd"

        # 탭 닫기 버튼 활성화
        self.setTabsClosable(True)

        # 탭 제거 시그널 연결
        self.tabCloseRequested.connect(self._remove_tab_by_index)

        # 탭 및 스타일 초기화
        self._apply_tab_style()

        # 우측 상단 탭 추가 버튼 설정
        self._setup_add_tab_button()

        # 초기 탭 설정
        self._set_tabs()

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        tab_bar = self.tabBar()
        if tab_bar is not None:
            tab_bar.setFont(CustomFont(12))

    def _setup_add_tab_button(self):
        """
        탭 목록 오른쪽에 고정된 탭 추가 버튼 설정
        """

        self.add_tab_button = QPushButton()
        self.add_tab_button.setIcon(
            QIcon(QPixmap(convert_resource_path("resources\\image\\plus.png")))
        )
        self.add_tab_button.setFixedSize(QSize(26, 26))
        self.add_tab_button.setStyleSheet(
            f"""
            QPushButton {{
                border: 1px solid {self.TAB_BORDER_COLOR};
                background: {self.TAB_BACKGROUND_COLOR};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {self.TAB_HOVER_COLOR};
            }}
            """
        )

        # 탭 추가 버튼을 담을 컨테이너 위젯 생성
        corner_container = QWidget()
        corner_layout = QVBoxLayout(corner_container)
        corner_layout.setContentsMargins(1, 1, 1, 1)
        corner_layout.addWidget(
            self.add_tab_button, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # 우측 상단 코너에 컨테이너 위젯 설정
        self.setCornerWidget(corner_container, Qt.Corner.TopRightCorner)

        # 탭 추가 버튼 클릭 시그널 연결
        self.add_tab_button.clicked.connect(self._add_tab)

    def _create_tab(
        self,
        name: str,
        available_skills: list[str],
        equipped_skills: list[str],
        keys: list[str],
    ) -> "Tab":
        """
        새 탭 생성
        """
        return Tab(self.shared_data)

    def _add_tab(
        self,
        name: str,
        available_skills: list[str],
        equipped_skills: list[str],
        keys: list[str],
    ):
        """
        새로운 탭 생성 후 QTabWidget에 추가
        """
        self.tab_count += 1

        new_tab: Tab = self._create_tab(name, available_skills, equipped_skills, keys)
        tab_name: str = "탭 " + str(self.tab_count)

        # QTabWidget에 탭 추가
        index: int = self.addTab(new_tab, tab_name)

        # 새로 추가된 탭으로 이동
        self.setCurrentIndex(index)

    def _set_tabs(self):
        """
        초기 탭 설정
        """
        self.tab_count: int = 0

        # 탭 데이터 인스턴스를 기반으로 탭 추가하도록 수정
        # 임시로 최근 탭 데이터를 기반으로만 추가하도록 설정함.
        for i in range(len(self.shared_data.tab_names)):
            names: str = self.shared_data.tab_names[i]
            available_skills: list[str] = get_available_skills(self.shared_data)
            equipped_skills: list[str] = self.shared_data.equipped_skills
            keys: list[str] = self.shared_data.skill_keys

            self._add_tab(names, available_skills, equipped_skills, keys)

    def _remove_tab_by_index(self, index):
        """
        탭 제거
        """
        self.removeTab(index)

    def _apply_tab_style(self):
        """
        탭과 내용 영역에 스타일 시트 적용
        """

        self.setStyleSheet(
            f"""
        /* QTabWidget container */
        QTabWidget {{
            background: {self.TAB_BACKGROUND_COLOR};
            border: 1px solid {self.TAB_BORDER_COLOR};
            border-radius: 10px;
        }}
        
        QTabWidget::pane {{
            border: 1px solid {self.TAB_BORDER_COLOR};
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
            background: {self.TAB_BACKGROUND_COLOR};
        }}

        /* 탭 기본 설정 */
        QTabBar::tab {{
            background: {self.TAB_DEFAULT_COLOR};
            border: 1px solid {self.TAB_BORDER_COLOR};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 10px;
            margin-top: 0px;
        }}

        /* 선택된 탭 */
        QTabBar::tab:selected {{
            background: {self.TAB_BACKGROUND_COLOR};
        }}

        /* 탭 호버 */
        QTabBar::tab:hover {{
            background: {self.TAB_HOVER_COLOR};
        }}

        /* 닫기 버튼 */
        QTabBar::close-button {{
            image: url({convert_resource_path("resources\\image\\x.png").replace("\\", "/")});
            border-radius: 7px;
        }}

        QTabBar::close-button:hover {{
            background-color: #FF5555;
        }}

        QTabBar::close-button:pressed {{
            background-color: #CC0000;
        }}
        """
        )


class Tab(QFrame):
    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        preview = SkillPreview(shared_data=self.shared_data)

        equippable_skill_frame = EquippableSkill(shared_data=self.shared_data)

        line = QFrame(self)
        line.setStyleSheet("QFrame { background-color: #b4b4b4; }")
        line.setFixedHeight(1)

        equipped_skill_frame = EquippedSkill(shared_data=self.shared_data)

        layout = QVBoxLayout(self)
        layout.addWidget(preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(equippable_skill_frame)
        layout.addWidget(line)
        layout.addWidget(equipped_skill_frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)
        self.setLayout(layout)


class SkillPreview(QFrame):
    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.setStyleSheet(
            """
            QFrame { 
                background-color: #ffffff;
                border-radius: 5px;
                border: 1px solid black;
            }
            """
        )
        self.setFixedSize(288, 48)

        self.skill_count = 0
        self.images: list[QLabel] = []


class EquippableSkill(QFrame):
    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.setStyleSheet("QFrame { background-color: transparent; }")

        layout = QGridLayout()

        self.skills: list[EquippableSkill.Skill] = []
        COLS = 4
        for i in range(8):
            skill = self.Skill(shared_data=self.shared_data, index=i)
            self.skills.append(skill)

            row: int = i // COLS
            col: int = i % COLS

            layout.addWidget(skill, row, col)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

    class Skill(QFrame):
        def __init__(self, shared_data: SharedData, index: int):
            super().__init__()

            self.setStyleSheet("QFrame { background-color: transparent; }")

            name: str = get_available_skills(shared_data)[index]

            self.button: QPushButton = QPushButton(self)
            self.button.setStyleSheet("QPushButton { border-radius :10px; }")
            self.button.setFixedSize(48, 48)
            self.button.setIcon(
                QIcon(
                    get_skill_pixmap(
                        shared_data=shared_data,
                        skill_name=name,
                    )
                )
            )
            self.button.setIconSize(QSize(48, 48))
            # self.button.clicked.connect(
            #     partial(lambda x: self.on_equippable_skill_clicked(x), i)
            # )

            self.name: QLabel = QLabel(name, self)
            self.name.setStyleSheet(
                "QLabel { background-color: transparent; border-radius :0px; }"
            )
            self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name.setFont(CustomFont(12))

            layout = QVBoxLayout()
            layout.addWidget(self.button)
            layout.addWidget(self.name)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.setLayout(layout)


class EquippedSkill(QFrame):
    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.setStyleSheet("QFrame { background-color: transparent; }")

        layout = QHBoxLayout()

        self.skills: list[EquippedSkill.Skill] = []
        for i in range(6):
            skill = self.Skill(shared_data=self.shared_data, index=i)
            self.skills.append(skill)

            layout.addWidget(skill)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

    class Skill(QFrame):
        def __init__(self, shared_data: SharedData, index: int):
            super().__init__()

            self.setStyleSheet("QFrame { background-color: transparent; }")

            name: str = shared_data.equipped_skills[index]

            self.button: QPushButton = QPushButton(self)
            self.button.setStyleSheet("QPushButton { border-radius :10px; }")
            self.button.setFixedSize(64, 64)
            self.button.setIcon(
                QIcon(
                    get_skill_pixmap(
                        shared_data=shared_data,
                        skill_name=name,
                    )
                )
            )
            self.button.setIconSize(QSize(64, 64))
            # self.button.clicked.connect(
            #     partial(lambda x: self.on_equipped_skill_clicked(x), i)
            # )

            self.key = QPushButton(shared_data.skill_keys[index], self)
            self.key.setFont(CustomFont(10))
            self.key.setFixedWidth(64)
            # self.key_button.clicked.connect(partial(lambda x: self.onSkillKeyClick(x), i))

            layout = QVBoxLayout()
            layout.addWidget(self.button)
            layout.addWidget(self.key)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

            self.setLayout(layout)
