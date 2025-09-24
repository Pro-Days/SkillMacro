from __future__ import annotations

from .data_manager import save_data
from .misc import (
    get_skill_pixmap,
    adjust_font_size,
    get_available_skills,
    convert_resource_path,
    set_var_to_ClassVar,
)
from .shared_data import UI_Variable
from .simulate_macro import randSimulate, detSimulate, get_req_stats
from .graph import (
    DpsDistributionCanvas,
    SkillDpsRatioCanvas,
    DMGCanvas,
    SkillContributionCanvas,
)
from .custom_classes import (
    CustomFont,
    CustomLineEdit,
    CustomComboBox,
    SimResult,
    SimAnalysis,
)
from .get_character_data import get_character_info, get_character_card_data

import requests
import os
from functools import partial
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap, QPainter, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QFileDialog,
    QScrollArea,
    QComboBox,
    QWidget,
)


if TYPE_CHECKING:
    from .main_window import MainWindow
    from .shared_data import SharedData


class SimUI:
    def __init__(
        self,
        master: MainWindow,
        parent: QFrame,
        shared_data: SharedData,
    ):
        self.shared_data: SharedData = shared_data
        self.parent: QFrame = parent
        self.master: MainWindow = master

        self.ui_var = UI_Variable()

        self.make_ui()

    def make_ui(self) -> None:
        """
        시뮬레이션 페이지 UI 구성
        """

        # 상단 네비게이션바
        self.sim_nav_frame: QFrame = QFrame(self.parent)
        self.sim_nav_frame.setGeometry(
            self.ui_var.sim_margin,
            self.ui_var.sim_margin,
            self.ui_var.DEFAULT_WINDOW_WIDTH - self.ui_var.sim_margin * 2,
            self.ui_var.sim_navHeight,
        )
        self.sim_nav_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); }"
        )

        self.sim_nav_buttons: list[QPushButton] = []

        # 네비게이션바 텍스트
        nav_texts: list[str] = ["정보 입력", "시뮬레이터", "스탯 계산기", "캐릭터 카드"]
        border_widths: list[int] = [2, 0, 0, 0]

        # 네비게이션 버튼
        for i in range(4):
            button: QPushButton = QPushButton(nav_texts[i], self.sim_nav_frame)

            button.setGeometry(
                self.ui_var.sim_navBWidth * i,
                0,
                self.ui_var.sim_navBWidth,
                self.ui_var.sim_navHeight,
            )
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgb(255, 255, 255); border: none; border-bottom: {border_widths[i]}px solid #9180F7; 
                }}
                QPushButton:hover {{
                    background-color: rgb(234, 234, 234);
                }}
                """
            )
            button.setFont(CustomFont(12))

            self.sim_nav_buttons.append(button)

        # 닫기 버튼
        button: QPushButton = QPushButton(self.sim_nav_frame)
        button.setGeometry(
            890,
            0,
            self.ui_var.sim_navHeight,
            self.ui_var.sim_navHeight,
        )
        button.setStyleSheet(
            """
            QPushButton {
                background-color: rgb(255, 255, 255); border: none; border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgb(234, 234, 234);
            }
            """
        )
        pixmap: QPixmap = QPixmap(convert_resource_path("resources\\image\\x.png"))
        button.setIcon(QIcon(pixmap))
        button.setIconSize(QSize(15, 15))

        self.sim_nav_buttons.append(button)

        self.sim_nav_buttons[0].clicked.connect(self.make_simul_page1)
        self.sim_nav_buttons[1].clicked.connect(self.make_simul_page2)
        self.sim_nav_buttons[2].clicked.connect(self.make_simul_page3)
        self.sim_nav_buttons[3].clicked.connect(self.make_simul_page4)
        self.sim_nav_buttons[4].clicked.connect(lambda: self.master.change_layout(0))

        # 메인 프레임
        self.sim_main_frame: QFrame = QFrame(self.parent)
        self.sim_main_frame.setGeometry(
            self.ui_var.sim_margin,
            self.ui_var.sim_margin
            + self.ui_var.sim_navHeight
            + self.ui_var.sim_main1_D,
            self.master.width()
            - self.ui_var.scrollBarWidth
            - self.ui_var.sim_margin * 2,
            self.master.height()
            - self.master.creator_label.height()
            - self.ui_var.sim_navHeight
            - self.ui_var.sim_margin * 2
            - self.ui_var.sim_main1_D,
        )
        self.sim_main_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        # 스크롤바
        self.sim_main_ScrollArea: QScrollArea = QScrollArea(self.parent)
        self.sim_main_ScrollArea.setWidget(self.sim_main_frame)
        self.sim_main_ScrollArea.setGeometry(
            self.ui_var.sim_margin,
            self.ui_var.sim_margin
            + self.ui_var.sim_navHeight
            + self.ui_var.sim_main1_D,
            self.master.width() - self.ui_var.sim_margin,
            self.master.height()
            - self.master.creator_label.height()
            - self.ui_var.sim_navHeight
            - self.ui_var.sim_margin * 2
            - self.ui_var.sim_main1_D,
        )
        self.sim_main_ScrollArea.setStyleSheet(
            "QScrollArea { background-color: #FFFFFF; border: 0px solid black; border-radius: 10px; }"
        )

        # 스크롤바 스크롤 설정
        self.sim_main_ScrollArea.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.sim_main_ScrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        # self.sim_mainScrollArea.setPalette(self.backPalette)
        self.sim_main_ScrollArea.show()

        self.make_simul_page1()

    def remove_simul_widgets(self) -> None:
        """
        시뮬레이션 페이지 모든 위젯 제거
        """

        # 콤보박스 오류 수정
        if self.shared_data.sim_page_type == 3:
            comboboxList: list[QComboBox] = [
                self.sim3_ui.efficiency_statL,
                self.sim3_ui.efficiency_statR,
                self.sim3_ui.potential_stat0,
                self.sim3_ui.potential_stat1,
                self.sim3_ui.potential_stat2,
            ]
            for i in comboboxList:
                i.showPopup()
                i.hidePopup()

        [i.deleteLater() for i in self.sim_main_frame.findChildren(QWidget)]
        self.shared_data.sim_page_type = 0

        # plt 그래프 모두 닫기
        plt.close("all")
        plt.clf()

    def make_simul_page4(self) -> None:
        """
        시뮬레이션 - 캐릭터 카드 페이지 생성
        """

        # 입력값 체크
        if not all(self.shared_data.is_input_valid.values()):
            self.master.get_popup_manager().make_notice_popup("SimInputError")
            return

        self.remove_simul_widgets()
        self.sim_update_nav_button(3)

        self.shared_data.sim_page_type = 4

        self.sim4_ui = Sim4UI(self.sim_main_frame, self.shared_data)

        # 메인 프레임 크기 조정
        self.sim_main_frame.setFixedHeight(
            self.sim4_ui.info_frame.y()
            + self.sim4_ui.info_frame.height()
            + self.ui_var.sim_mainFrameMargin,
        )
        [i.show() for i in self.parent.findChildren(QWidget)]

        self.update_position()

    def make_simul_page3(self) -> None:
        """
        시뮬레이션 - 스탯 계산기 페이지 생성
        """

        # 입력값 체크
        if not all(self.shared_data.is_input_valid.values()):
            self.master.get_popup_manager().make_notice_popup("SimInputError")
            return

        self.remove_simul_widgets()
        self.sim_update_nav_button(2)

        self.shared_data.sim_page_type = 3

        self.sim3_ui = Sim3UI(self.sim_main_frame, self.shared_data)

        # 메인 프레임 크기 조정
        self.sim_main_frame.setFixedHeight(
            self.sim3_ui.potentialRank_frame.y()
            + self.sim3_ui.potentialRank_frame.height()
            + self.ui_var.sim_mainFrameMargin,
        )
        [i.show() for i in self.sim3_ui.widgetList]

        self.update_position()

    def make_simul_page2(self) -> None:
        """
        시뮬레이션 - 시뮬레이터 페이지 생성
        """

        # 입력값 체크
        if not all(self.shared_data.is_input_valid.values()):
            self.master.get_popup_manager().make_notice_popup("SimInputError")
            return

        self.remove_simul_widgets()
        self.sim_update_nav_button(1)

        self.shared_data.sim_page_type = 2

        self.sim2_ui = Sim2UI(self.sim_main_frame, self.shared_data)

        # 메인 프레임 크기 조정
        self.sim_main_frame.setFixedHeight(
            self.sim2_ui.analysis_frame.y()
            + self.sim2_ui.analysis_frame.height()
            + self.ui_var.sim_mainFrameMargin,
        )
        [i.show() for i in self.parent.findChildren(QWidget)]

        self.update_position()

    def make_simul_page1(self) -> None:
        """
        시뮬레이션 - 정보 입력 페이지 생성
        """

        self.remove_simul_widgets()
        self.sim_update_nav_button(0)

        self.shared_data.sim_page_type = 1

        self.sim1_ui = Sim1UI(self.sim_main_frame, self.shared_data)

        # Tab Order 설정
        tab_orders = (
            self.sim1_ui.stat_inputs.inputs
            + self.sim1_ui.skill_inputs.inputs
            + self.sim1_ui.info_inputs.inputs
        )
        for i in range(len(tab_orders) - 1):
            QWidget.setTabOrder(tab_orders[i], tab_orders[i + 1])

        # 메인 프레임 크기 조정
        self.sim_main_frame.setFixedHeight(
            self.sim1_ui.info_frame.y()
            + self.sim1_ui.info_frame.height()
            + self.ui_var.sim_mainFrameMargin,
        )
        [i.show() for i in self.parent.findChildren(QWidget)]

        self.update_position()
        self.master.get_popup_manager().update_position()

    def sim_update_nav_button(self, num: int) -> None:  # simul_ui로 이동
        """
        시뮬레이션 - 내비게이션 버튼 색 업데이트
        """

        border_widths = [0, 0, 0, 0]
        border_widths[num] = 2

        for i in [0, 1, 2, 3]:
            self.sim_nav_buttons[i].setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgb(255, 255, 255); border: none; border-bottom: {border_widths[i]}px solid #9180F7;
                }}
                QPushButton:hover {{
                    background-color: rgb(234, 234, 234);
                }}
                """
            )

    def update_position(self) -> None:
        deltaWidth = self.master.width() - self.ui_var.DEFAULT_WINDOW_WIDTH

        self.sim_nav_frame.move(
            self.ui_var.sim_margin + deltaWidth // 2, self.ui_var.sim_margin
        )
        self.sim_main_frame.setFixedWidth(
            self.master.width()
            - self.ui_var.scrollBarWidth
            - self.ui_var.sim_margin * 2
        )
        self.sim_main_ScrollArea.setFixedSize(
            self.master.width() - self.ui_var.sim_margin,
            self.master.height()
            - self.master.creator_label.height()
            - self.ui_var.sim_navHeight
            - self.ui_var.sim_margin * 2
            - self.ui_var.sim_main1_D,
        )

        if self.shared_data.sim_page_type == 1:  # 정보 입력
            self.sim1_ui.stat_frame.move(deltaWidth // 2, 0)
            self.sim1_ui.skill_frame.move(
                deltaWidth // 2,
                self.sim1_ui.stat_frame.y()
                + self.sim1_ui.stat_frame.height()
                + self.ui_var.sim_main_D,
            )
            self.sim1_ui.info_frame.move(
                deltaWidth // 2,
                self.sim1_ui.skill_frame.y()
                + self.sim1_ui.skill_frame.height()
                + self.ui_var.sim_main_D,
            )

        elif self.shared_data.sim_page_type == 2:  # 시뮬레이터
            self.sim2_ui.power_frame.move(deltaWidth // 2, 0)
            self.sim2_ui.analysis_frame.move(
                deltaWidth // 2,
                self.sim2_ui.power_frame.y()
                + self.sim2_ui.power_frame.height()
                + self.ui_var.sim_main_D,
            )

        elif self.shared_data.sim_page_type == 3:  # 스탯 계산기
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

        elif self.shared_data.sim_page_type == 4:  # 캐릭터 카드
            self.sim4_ui.mainframe.move(deltaWidth // 2, 0)


class Sim1UI:
    def __init__(self, parent, shared_data: SharedData):
        self.shared_data = shared_data
        self.parent = parent

        self.ui_var = UI_Variable()

        self.makeSim1UI()

    def makeSim1UI(self):
        # 캐릭터 스탯
        self.stat_frame = QFrame(self.parent)
        self.stat_frame.setGeometry(
            0,
            0,
            928,
            self.ui_var.sim_title_H
            + (self.ui_var.sim_widget_D + self.ui_var.sim_stat_frame_H) * 3,
        )
        self.stat_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.stat_title = Title(parent=self.stat_frame, text="캐릭터 스탯")
        self.stat_inputs = StatInput(
            self.stat_frame, self.shared_data, self.stat_inputChanged
        )
        self.stat_inputs.inputs[0].setFocus()

        # 스탯 입력창 위치 조정
        margin, count = 21, 6
        for i in range(18):
            self.stat_inputs.frames[i].move(
                self.ui_var.sim_stat_margin
                + (self.ui_var.sim_stat_width + margin) * (i % count),
                self.stat_title.frame.height()
                + self.ui_var.sim_widget_D * ((i // count) + 1)
                + self.ui_var.sim_stat_frame_H * (i // count),
            )
            self.stat_inputs.labels[i].setGeometry(
                0,
                0,
                self.ui_var.sim_stat_width,
                self.ui_var.sim_stat_label_H,
            )
            self.stat_inputs.inputs[i].setGeometry(
                0,
                self.ui_var.sim_stat_label_H,
                self.ui_var.sim_stat_width,
                self.ui_var.sim_stat_input_H,
            )
            self.stat_inputs.inputs[i].setText(
                str(self.shared_data.info_stats.get_stat_from_index(i))
            )

        # 스킬 레벨
        self.skill_frame = QFrame(self.parent)
        self.skill_frame.setGeometry(
            0,
            self.stat_frame.y() + self.stat_frame.height() + self.ui_var.sim_main_D,
            928,
            self.ui_var.sim_title_H
            + (self.ui_var.sim_widget_D + self.ui_var.sim_skill_frame_H) * 2,
        )
        self.skill_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.skill_title = Title(self.skill_frame, "스킬 레벨")
        self.skill_inputs = SkillInput(
            self.skill_frame, self.shared_data, self.skill_inputChanged
        )

        margin, count = 66, 4
        for i in range(8):
            self.skill_inputs.frames[i].move(
                self.ui_var.sim_skill_margin
                + (self.ui_var.sim_skill_width + margin) * (i % count),
                self.skill_title.frame.height()
                + self.ui_var.sim_widget_D * ((i // count) + 1)
                + self.ui_var.sim_skill_frame_H * (i // count),
            )
            self.skill_inputs.names[i].setGeometry(
                0,
                0,
                self.ui_var.sim_skill_width,
                self.ui_var.sim_skill_name_H,
            )
            self.skill_inputs.labels[i].setGeometry(
                self.ui_var.sim_skill_image_Size,
                self.ui_var.sim_skill_name_H,
                self.ui_var.sim_skill_right_W,
                self.ui_var.sim_skill_level_H,
            )
            self.skill_inputs.inputs[i].setGeometry(
                self.ui_var.sim_skill_image_Size,
                self.ui_var.sim_skill_name_H + self.ui_var.sim_skill_level_H,
                self.ui_var.sim_skill_right_W,
                self.ui_var.sim_skill_input_H,
            )

            self.skill_inputs.inputs[i].setText(
                str(
                    self.shared_data.info_skill_levels[
                        get_available_skills(self.shared_data)[i]
                    ]
                )
            )

        # 추가 정보 입력
        self.info_frame = QFrame(self.parent)
        self.info_frame.setGeometry(
            0,
            self.skill_frame.y() + self.skill_frame.height() + self.ui_var.sim_main_D,
            928,
            self.ui_var.sim_title_H
            + (self.ui_var.sim_widget_D + self.ui_var.sim_simInfo_frame_H) * 1,
        )
        self.info_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.info_title = Title(self.info_frame, "추가 정보 입력")
        self.info_inputs = SimInfoInput(
            self.info_frame, self.shared_data, self.simInfo_inputChanged
        )

        margin = 60
        for i in range(3):
            self.info_inputs.frames[i].move(
                self.ui_var.sim_simInfo_margin
                + (self.ui_var.sim_simInfo_width + margin) * i,
                self.info_title.frame.height() + self.ui_var.sim_widget_D,
            )
            self.info_inputs.labels[i].setGeometry(
                0,
                0,
                self.ui_var.sim_simInfo_width,
                self.ui_var.sim_simInfo_label_H,
            )
            self.info_inputs.inputs[i].setGeometry(
                0,
                self.ui_var.sim_simInfo_label_H,
                self.ui_var.sim_simInfo_width,
                self.ui_var.sim_simInfo_input_H,
            )

            self.info_inputs.inputs[i].setText(
                str(
                    self.shared_data.info_sim_details[
                        list(self.shared_data.SIM_DETAILS.keys())[i]
                    ]
                )
            )

    def stat_inputChanged(self):
        # 스탯이 정상적으로 입력되었는지 확인
        def checkInput(num: int, text: str) -> bool:
            if not text.isdigit():
                return False

            return (
                self.shared_data.STAT_RANGES[list(self.shared_data.STATS.keys())[num]][
                    0
                ]
                <= int(text)
                <= self.shared_data.STAT_RANGES[
                    list(self.shared_data.STATS.keys())[num]
                ][1]
            )

        if not False in [
            checkInput(i, j.text()) for i, j in enumerate(self.stat_inputs.inputs)
        ]:  # 모두 digit
            for i in self.stat_inputs.inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            for i, j in enumerate(self.stat_inputs.inputs):
                self.shared_data.info_stats.set_stat_from_index(i, int(j.text()))

            save_data(self.shared_data)
            self.shared_data.is_input_valid["stat"] = True

        else:  # 하나라도 통과X
            for i, j in enumerate(self.stat_inputs.inputs):
                if not checkInput(i, j.text()):  # 통과X면 빨간색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 2px solid {self.ui_var.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:  # 통과O면 원래색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

            self.shared_data.is_input_valid["stat"] = False

    def skill_inputChanged(self):
        # 스킬이 정상적으로 입력되었는지 확인
        def checkInput(text: str) -> bool:
            if not text.isdigit():
                return False

            return 1 <= int(text) <= 30

        if not False in [
            checkInput(i.text()) for i in self.skill_inputs.inputs
        ]:  # 모두 통과
            for i in self.skill_inputs.inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            for i, j in enumerate(self.skill_inputs.inputs):
                self.shared_data.info_skill_levels[
                    get_available_skills(self.shared_data)[i]
                ] = int(j.text())
            save_data(self.shared_data)
            self.shared_data.is_input_valid["skill"] = True

        else:  # 하나라도 통과X
            for i in self.skill_inputs.inputs:
                if not checkInput(i.text()):  # 통과X면 빨간색
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 2px solid {self.ui_var.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

            self.shared_data.is_input_valid["skill"] = False

    def simInfo_inputChanged(self):
        # 스탯이 정상적으로 입력되었는지 확인
        def checkInput(num, text) -> bool:
            if not text.isdigit():
                return False

            match num:
                case 0 | 1:
                    return int(text) != 0
                case _:
                    return True

        if not False in [
            checkInput(i, j.text()) for i, j in enumerate(self.info_inputs.inputs)
        ]:  # 모두 통과
            for i in self.info_inputs.inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            for i, j in enumerate(self.info_inputs.inputs):
                self.shared_data.info_sim_details[
                    list(self.shared_data.SIM_DETAILS.keys())[i]
                ] = int(j.text())
            save_data(self.shared_data)
            self.shared_data.is_input_valid["simInfo"] = True

        else:  # 하나라도 통과X
            for i, j in enumerate(self.info_inputs.inputs):
                if not checkInput(i, j.text()):  # 통과X면 빨간색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 2px solid {self.ui_var.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

            self.shared_data.is_input_valid["simInfo"] = False


class Sim2UI:
    def __init__(self, parent, shared_data: SharedData):
        self.shared_data = shared_data
        self.parent = parent

        self.ui_var = UI_Variable()

        self.makeSim2UI()

    def makeSim2UI(self):
        sim_result: SimResult = randSimulate(
            self.shared_data,
            self.shared_data.info_stats,
            self.shared_data.info_sim_details,
        )
        powers = sim_result.powers
        analysis = sim_result.analysis
        resultDet = sim_result.deterministic_boss_attacks
        results = sim_result.random_boss_attacks
        str_powers = sim_result.str_powers

        for i, power in enumerate(powers):
            self.shared_data.powers[i] = power

        timeStep, timeStepCount = 1, 60  # 60초까지 시뮬레이션
        times = [i * timeStep for i in range(timeStepCount + 1)]

        dps_list = []
        for result in results:
            dps_list.append([0.0])
            for i in range(timeStepCount):
                dps_list[-1].append(
                    sum(
                        [
                            j.damage
                            for j in result
                            if i * timeStep <= j.time < (i + 1) * timeStep
                        ]
                    )
                )

        # 전투력
        self.power_frame = QFrame(self.parent)
        self.power_frame.setGeometry(
            0,
            0,
            928,
            self.ui_var.sim_title_H
            + (self.ui_var.sim_widget_D + self.ui_var.sim_powerL_frame_H),
        )
        self.power_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.power_title = Title(self.power_frame, "전투력")
        self.power_labels = PowerLabels(self.power_frame, self.shared_data, str_powers)

        for i in range(len(self.power_labels.frames)):
            frame = self.power_labels.frames[i]
            label = self.power_labels.labels[i]
            number = self.power_labels.numbers[i]

            frame.setGeometry(
                self.ui_var.sim_powerL_margin
                + (self.ui_var.sim_powerL_width + self.ui_var.sim_powerL_D) * i,
                self.ui_var.sim_label_H + self.ui_var.sim_widget_D,
                self.ui_var.sim_powerL_width,
                self.ui_var.sim_powerL_frame_H,
            )
            label.setGeometry(
                0,
                0,
                self.ui_var.sim_powerL_width,
                self.ui_var.sim_powerL_title_H,
            )
            number.setGeometry(
                0,
                self.ui_var.sim_powerL_title_H,
                self.ui_var.sim_powerL_width,
                self.ui_var.sim_powerL_number_H,
            )

        # 분석
        self.analysis_frame = QFrame(self.parent)
        self.analysis_frame.setGeometry(
            0,
            self.power_frame.y() + self.power_frame.height() + self.ui_var.sim_main_D,
            928,
            self.ui_var.sim_title_H
            + (
                self.ui_var.sim_widget_D * 5
                + self.ui_var.sim_analysis_frame_H
                + self.ui_var.sim_dps_height
                + self.ui_var.sim_dmg_height * 3
            ),
        )
        self.analysis_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        self.analysis_title = Title(self.analysis_frame, "분석")
        self.analysis_details = [
            AnalysisDetails(
                self.analysis_frame,
                analysis[i],
                self.shared_data.POWER_DETAILS,
            )
            for i in range(4)
        ]

        for i, ad in enumerate(self.analysis_details):
            ad.frame.setGeometry(
                self.ui_var.sim_analysis_margin
                + (self.ui_var.sim_analysis_width + self.ui_var.sim_analysis_D) * i,
                self.ui_var.sim_label_H + self.ui_var.sim_widget_D,
                self.ui_var.sim_analysis_width,
                self.ui_var.sim_analysis_frame_H,
            )
            ad.color.setStyleSheet(
                f"QFrame {{ background-color: rgb({self.ui_var.sim_colors4[i]}); border: 0px solid; border-radius: 0px; border-bottom: 1px solid #CCCCCC; border-left: 1px solid #CCCCCC; border-top: 1px solid #CCCCCC; }}"
            )

        ## DPM 분포
        self.dpsGraph_frame = QFrame(self.analysis_frame)
        self.dpsGraph_frame.setGeometry(
            self.ui_var.sim_dps_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_analysis_frame_H
            + self.ui_var.sim_widget_D * 2,
            self.ui_var.sim_dps_width,
            self.ui_var.sim_dps_height,
        )
        self.dpsGraph_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )

        sums = [sum([i.damage for i in j]) for j in results]

        self.dpsGraph = DpsDistributionCanvas(
            self.dpsGraph_frame, sums
        )  # 시뮬레이션 결과
        self.dpsGraph.move(5, 5)
        self.dpsGraph.resize(
            self.ui_var.sim_dps_width - 10, self.ui_var.sim_dps_height - 10
        )

        ## 스킬 비율
        self.skillRatioGraph_frame = QFrame(self.analysis_frame)
        self.skillRatioGraph_frame.setGeometry(
            self.ui_var.sim_dps_margin
            + self.ui_var.sim_dps_width
            + self.ui_var.sim_skillDps_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_analysis_frame_H
            + self.ui_var.sim_widget_D * 2,
            self.ui_var.sim_skillRatio_width,
            self.ui_var.sim_skillRatio_height,
        )
        self.skillRatioGraph_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )

        ratio_data: list[float] = [
            sum([i.damage for i in resultDet if i.skill_name == skill_name])
            for skill_name in self.shared_data.equipped_skills + ["평타"]
        ]
        # data = [round(total_dmgs[i] / sum(total_dmgs) * 100, 1) for i in range(7)]

        self.skillRatioGraph = SkillDpsRatioCanvas(
            self.skillRatioGraph_frame, ratio_data, self.shared_data.equipped_skills
        )
        self.skillRatioGraph.move(10, 10)
        self.skillRatioGraph.resize(
            self.ui_var.sim_skillRatio_width - 20,
            self.ui_var.sim_skillRatio_height - 20,
        )

        ## 시간 경과에 따른 피해량
        self.dmgTime_frame = QFrame(self.analysis_frame)
        self.dmgTime_frame.setGeometry(
            self.ui_var.sim_dps_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_analysis_frame_H
            + self.ui_var.sim_dps_height
            + self.ui_var.sim_widget_D * 3,
            self.ui_var.sim_dmg_width,
            self.ui_var.sim_dmg_height,
        )
        self.dmgTime_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )

        data = {
            "time": times,
            "max": [max([j[i] for j in dps_list]) for i in range(timeStepCount + 1)],
            "mean": [
                sum([j[i] for j in dps_list]) / len(dps_list)
                for i in range(timeStepCount + 1)
            ],
            "min": [min([j[i] for j in dps_list]) for i in range(timeStepCount + 1)],
        }
        self.dmgTime = DMGCanvas(self.dmgTime_frame, data, "time")  # 시뮬레이션 결과
        self.dmgTime.move(5, 5)
        self.dmgTime.resize(
            self.ui_var.sim_dmg_width - 10, self.ui_var.sim_dmg_height - 10
        )

        ## 누적 피해량
        self.totalDmg_frame = QFrame(self.analysis_frame)
        self.totalDmg_frame.setGeometry(
            self.ui_var.sim_dps_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_analysis_frame_H
            + self.ui_var.sim_dps_height
            + self.ui_var.sim_dmg_height
            + self.ui_var.sim_widget_D * 4,
            self.ui_var.sim_dmg_width,
            self.ui_var.sim_dmg_height,
        )
        self.totalDmg_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )

        total_list = []
        for dps in dps_list:
            total_list.append([])
            for i in range(timeStepCount + 1):
                total = sum([j for j in dps[: i + 1]])
                total_list[-1].append(total)

        means = [
            sum([j[i] for j in total_list]) / len(total_list)
            for i in range(timeStepCount + 1)
        ]
        data = {
            "time": times,
            "max": total_list[sums.index(max(sums))],
            "mean": means,
            "min": total_list[sums.index(min(sums))],
        }

        self.totalDmg = DMGCanvas(
            self.totalDmg_frame, data, "cumulative"
        )  # 시뮬레이션 결과
        self.totalDmg.move(5, 5)
        self.totalDmg.resize(
            self.ui_var.sim_dmg_width - 10, self.ui_var.sim_dmg_height - 10
        )

        ## 스킬별 누적 기여도
        self.skillContribute_frame = QFrame(self.analysis_frame)
        self.skillContribute_frame.setGeometry(
            self.ui_var.sim_dps_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_analysis_frame_H
            + self.ui_var.sim_dps_height
            + self.ui_var.sim_dmg_height * 2
            + self.ui_var.sim_widget_D * 5,
            self.ui_var.sim_dmg_width,
            self.ui_var.sim_dmg_height,
        )
        self.skillContribute_frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
        )

        skillsData = []
        for skill_name in self.shared_data.equipped_skills + ["평타"]:
            skillsData.append([])
            for i in range(timeStepCount + 1):
                skillsData[-1].append(
                    sum(
                        [
                            j.damage
                            for j in resultDet
                            if j.skill_name == skill_name
                            and j.time < (i + 1) * timeStep
                        ]
                    )
                )

        # totalData = []
        # for i in range(timeStepCount):
        #     totalData.append(sum([j[2] for j in resultDet if j[1] < (i + 1) * timeStep]))
        totalData = [
            sum([j.damage for j in resultDet if j.time < (i + 1) * timeStep])
            for i in range(timeStepCount + 1)
        ]

        # data_normalized = []
        # for i in range(7):
        #     data_normalized.append([skillsData[i][j] / totalData[j] for j in range(timeStepCount)])
        data_normalized = [
            [skillsData[i][j] / totalData[j] for j in range(timeStepCount + 1)]
            for i in range(7)
        ]

        data_cumsum = [[0.0 for _ in row] for row in data_normalized]
        for i in range(len(data_normalized)):
            for j in range(len(data_normalized[0])):
                data_cumsum[i][j] = sum(row[j] for row in data_normalized[: i + 1])

        data = {
            "time": times,
            "skills_normalized": data_normalized,
            "skills_sum": data_cumsum,
        }
        self.skillContribute = SkillContributionCanvas(
            self.skillContribute_frame, data, self.shared_data.equipped_skills
        )  # 시뮬레이션 결과
        self.skillContribute.move(5, 5)
        self.skillContribute.resize(
            self.ui_var.sim_dmg_width - 10,
            self.ui_var.sim_dmg_height - 10,
        )


class Sim3UI:
    def __init__(self, parent, shared_data: SharedData):
        self.shared_data = shared_data
        self.parent = parent

        self.ui_var = UI_Variable()

        self.makeSim3UI()

    def makeSim3UI(self):
        powers = detSimulate(
            self.shared_data,
            self.shared_data.info_stats,
            self.shared_data.info_sim_details,
        ).powers

        for i, power in enumerate(powers):
            self.shared_data.powers[i] = power

        self.widgetList = []

        self.shared_data.is_input_valid["stat"] = False
        self.shared_data.is_input_valid["skill"] = False

        ## 스펙업 효율 계산기
        self.efficiency_frame = QFrame(self.parent)
        self.efficiency_frame.setGeometry(
            0,
            0,
            928,
            self.ui_var.sim_title_H
            + (self.ui_var.sim_widget_D + self.ui_var.sim_efficiency_frame_H),
        )
        self.efficiency_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )
        self.widgetList.append(self.efficiency_frame)

        self.efficiency_title = Title(self.efficiency_frame, "스펙업 효율 계산기")
        self.widgetList.append(self.efficiency_title.frame)
        self.widgetList.append(self.efficiency_title.label)

        # 왼쪽 콤보박스
        self.efficiency_statL = CustomComboBox(
            self.efficiency_frame,
            list(self.shared_data.STATS.values()),
            self.efficiency_Changed,
        )
        self.efficiency_statL.setGeometry(
            self.ui_var.sim_efficiency_statL_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_widget_D
            + self.ui_var.sim_efficiency_statL_y,
            self.ui_var.sim_efficiency_statL_W,
            self.ui_var.sim_efficiency_statL_H,
        )
        self.widgetList.append(self.efficiency_statL)

        # 왼쪽 스탯 입력창
        self.efficiency_statInput = CustomLineEdit(
            self.efficiency_frame, self.efficiency_Changed, "10"
        )
        self.efficiency_statInput.setGeometry(
            self.ui_var.sim_efficiency_statInput_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_widget_D
            + self.ui_var.sim_efficiency_statInput_y,
            self.ui_var.sim_efficiency_statInput_W,
            self.ui_var.sim_efficiency_statInput_H,
        )
        self.efficiency_statInput.setFocus()
        self.widgetList.append(self.efficiency_statInput)

        # 화살표
        self.efficiency_arrow = QLabel("", self.efficiency_frame)
        self.efficiency_arrow.setStyleSheet(
            f"QLabel {{ background-color: transparent; border: 0px solid; }}"
        )
        self.efficiency_arrow.setPixmap(
            QPixmap(convert_resource_path("resources\\image\\lineArrow.png")).scaled(
                self.ui_var.sim_efficiency_arrow_W, self.ui_var.sim_efficiency_arrow_H
            )
        )
        self.efficiency_arrow.setGeometry(
            self.ui_var.sim_efficiency_arrow_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_widget_D
            + self.ui_var.sim_efficiency_arrow_y,
            self.ui_var.sim_efficiency_arrow_W,
            self.ui_var.sim_efficiency_arrow_H,
        )
        self.widgetList.append(self.efficiency_arrow)

        # 오른쪽 콤보박스
        self.efficiency_statR = CustomComboBox(
            self.efficiency_frame,
            list(self.shared_data.STATS.values()),
            self.efficiency_Changed,
        )
        self.efficiency_statR.setGeometry(
            self.ui_var.sim_efficiency_statR_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_widget_D
            + self.ui_var.sim_efficiency_statR_y,
            self.ui_var.sim_efficiency_statR_W,
            self.ui_var.sim_efficiency_statR_H,
        )
        self.widgetList.append(self.efficiency_statR)

        self.efficiency_power_labels = PowerLabels(
            self.efficiency_frame, self.shared_data, ["0"] * 4
        )

        for i in range(len(self.efficiency_power_labels.labels)):
            frame = self.efficiency_power_labels.frames[i]
            label = self.efficiency_power_labels.labels[i]
            number = self.efficiency_power_labels.numbers[i]

            frame.setGeometry(
                self.ui_var.sim_powerS_margin
                + (self.ui_var.sim_powerS_width + self.ui_var.sim_powerS_D) * i,
                self.ui_var.sim_label_H + self.ui_var.sim_widget_D,
                self.ui_var.sim_powerS_width,
                self.ui_var.sim_powerS_frame_H,
            )
            label.setGeometry(
                0,
                0,
                self.ui_var.sim_powerS_width,
                self.ui_var.sim_powerS_title_H,
            )
            number.setGeometry(
                0,
                self.ui_var.sim_powerS_title_H,
                self.ui_var.sim_powerS_width,
                self.ui_var.sim_powerS_number_H,
            )

            self.widgetList.append(frame)
            self.widgetList.append(label)
            self.widgetList.append(number)

        self.update_efficiency()

        # 추가 스펙업 계산기
        self.additional_frame = QFrame(self.parent)
        self.additional_frame.setGeometry(
            0,
            self.efficiency_frame.y()
            + self.efficiency_frame.height()
            + self.ui_var.sim_main_D,
            928,
            self.ui_var.sim_title_H
            + (self.ui_var.sim_widget_D + self.ui_var.sim_stat_frame_H) * 3
            + self.ui_var.sim_main_D
            + (self.ui_var.sim_widget_D + self.ui_var.sim_skill_frame_H) * 2
            + self.ui_var.sim_main_D
            + (self.ui_var.sim_widget_D + self.ui_var.sim_powerL_frame_H),
        )
        self.additional_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )
        self.widgetList.append(self.additional_frame)

        self.additional_title = Title(self.additional_frame, "추가 스펙업 계산기")
        self.widgetList.append(self.additional_title.frame)
        self.widgetList.append(self.additional_title.label)

        self.additional_power_labels = PowerLabels(
            self.additional_frame, self.shared_data, ["0"] * 4
        )

        for i in range(len((self.additional_power_labels.labels))):
            frame = self.additional_power_labels.frames[i]
            label = self.additional_power_labels.labels[i]
            number = self.additional_power_labels.numbers[i]

            frame.setGeometry(
                self.ui_var.sim_powerL_margin
                + (self.ui_var.sim_powerL_width + self.ui_var.sim_powerL_D) * i,
                self.ui_var.sim_label_H
                + self.ui_var.sim_widget_D
                + (self.ui_var.sim_widget_D + self.ui_var.sim_stat_frame_H) * 3
                + self.ui_var.sim_main_D
                + (self.ui_var.sim_widget_D + self.ui_var.sim_skill_frame_H) * 2
                + self.ui_var.sim_main_D,
                self.ui_var.sim_powerL_width,
                self.ui_var.sim_powerL_frame_H,
            )
            label.setGeometry(
                0,
                0,
                self.ui_var.sim_powerL_width,
                self.ui_var.sim_powerL_title_H,
            )
            number.setGeometry(
                0,
                self.ui_var.sim_powerL_title_H,
                self.ui_var.sim_powerL_width,
                self.ui_var.sim_powerL_number_H,
            )

            self.widgetList.append(frame)
            self.widgetList.append(label)
            self.widgetList.append(number)

        self.additional_stats = StatInput(
            self.additional_frame, self.shared_data, self.stat_inputChanged
        )

        margin, count = 21, 6
        for i in range(18):
            self.additional_stats.frames[i].move(
                self.ui_var.sim_stat_margin
                + self.ui_var.sim_stat_width * (i % count)
                + margin * (i % count),
                self.additional_title.frame.height()
                + self.ui_var.sim_widget_D * ((i // count) + 1)
                + self.ui_var.sim_stat_frame_H * (i // count),
            )
            self.additional_stats.labels[i].setGeometry(
                0,
                0,
                self.ui_var.sim_stat_width,
                self.ui_var.sim_stat_label_H,
            )
            self.additional_stats.inputs[i].setGeometry(
                0,
                self.ui_var.sim_stat_label_H,
                self.ui_var.sim_stat_width,
                self.ui_var.sim_stat_input_H,
            )

            self.additional_stats.inputs[i].setText("0")

            self.widgetList.append(self.additional_stats.frames[i])
            self.widgetList.append(self.additional_stats.labels[i])
            self.widgetList.append(self.additional_stats.inputs[i])

        self.additional_skills = SkillInput(
            self.additional_frame, self.shared_data, self.skill_inputChanged
        )

        margin, count = 66, 4
        for i in range(8):
            self.additional_skills.frames[i].move(
                self.ui_var.sim_skill_margin
                + self.ui_var.sim_skill_width * (i % count)
                + margin * (i % count),
                self.additional_title.frame.height()
                + self.ui_var.sim_widget_D * ((i // count) + 1)
                + self.ui_var.sim_skill_frame_H * (i // count)
                + (self.ui_var.sim_widget_D + self.ui_var.sim_stat_frame_H) * 3
                + self.ui_var.sim_main_D,
            )
            self.additional_skills.names[i].setGeometry(
                0,
                0,
                self.ui_var.sim_skill_width,
                self.ui_var.sim_skill_name_H,
            )
            self.additional_skills.labels[i].setGeometry(
                self.ui_var.sim_skill_image_Size,
                self.ui_var.sim_skill_name_H,
                self.ui_var.sim_skill_right_W,
                self.ui_var.sim_skill_level_H,
            )
            self.additional_skills.inputs[i].setGeometry(
                self.ui_var.sim_skill_image_Size,
                self.ui_var.sim_skill_name_H + self.ui_var.sim_skill_level_H,
                self.ui_var.sim_skill_right_W,
                self.ui_var.sim_skill_input_H,
            )

            self.additional_skills.inputs[i].setText(
                str(
                    self.shared_data.info_skill_levels[
                        get_available_skills(self.shared_data)[i]
                    ]
                )
            )

            self.widgetList.append(self.additional_skills.frames[i])
            self.widgetList.append(self.additional_skills.names[i])
            self.widgetList.append(self.additional_skills.labels[i])
            self.widgetList.append(self.additional_skills.inputs[i])

        # 잠재능력 계산기
        self.potential_frame = QFrame(self.parent)
        self.potential_frame.setGeometry(
            0,
            self.additional_frame.y()
            + self.additional_frame.height()
            + self.ui_var.sim_main_D,
            928,
            self.ui_var.sim_title_H
            + (self.ui_var.sim_widget_D + self.ui_var.sim_potential_frame_H),
        )
        self.potential_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )
        self.widgetList.append(self.potential_frame)

        self.potential_title = Title(self.potential_frame, "잠재능력 계산기")
        self.widgetList.append(self.potential_title.frame)
        self.widgetList.append(self.potential_title.label)

        self.potential_stat0 = CustomComboBox(
            self.potential_frame,
            list(self.shared_data.POTENTIAL_STATS.keys()),
            self.potential_update,
        )
        self.potential_stat0.setGeometry(
            self.ui_var.sim_potential_stat_margin,
            self.ui_var.sim_label_H + self.ui_var.sim_widget_D,
            self.ui_var.sim_potential_stat_W,
            self.ui_var.sim_potential_stat_H,
        )
        self.widgetList.append(self.potential_stat0)

        self.potential_stat1 = CustomComboBox(
            self.potential_frame,
            list(self.shared_data.POTENTIAL_STATS.keys()),
            self.potential_update,
        )
        self.potential_stat1.setGeometry(
            self.ui_var.sim_potential_stat_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_widget_D
            + (self.ui_var.sim_potential_stat_H + self.ui_var.sim_potential_stat_D),
            self.ui_var.sim_potential_stat_W,
            self.ui_var.sim_potential_stat_H,
        )
        self.widgetList.append(self.potential_stat1)

        self.potential_stat2 = CustomComboBox(
            self.potential_frame,
            list(self.shared_data.POTENTIAL_STATS.keys()),
            self.potential_update,
        )
        self.potential_stat2.setGeometry(
            self.ui_var.sim_potential_stat_margin,
            self.ui_var.sim_label_H
            + self.ui_var.sim_widget_D
            + (self.ui_var.sim_potential_stat_H + self.ui_var.sim_potential_stat_D) * 2,
            self.ui_var.sim_potential_stat_W,
            self.ui_var.sim_potential_stat_H,
        )
        self.widgetList.append(self.potential_stat2)

        self.potential_power_labels = PowerLabels(
            self.potential_frame, self.shared_data, ["0"] * 4
        )

        for i in range(len(self.potential_power_labels.labels)):
            frame = self.potential_power_labels.frames[i]
            label = self.potential_power_labels.labels[i]
            number = self.potential_power_labels.numbers[i]

            frame.setGeometry(
                self.ui_var.sim_powerM_margin
                + (self.ui_var.sim_powerM_width + self.ui_var.sim_powerM_D) * i,
                self.ui_var.sim_label_H + self.ui_var.sim_widget_D,
                self.ui_var.sim_powerM_width,
                self.ui_var.sim_powerM_frame_H,
            )
            label.setGeometry(
                0,
                0,
                self.ui_var.sim_powerM_width,
                self.ui_var.sim_powerM_title_H,
            )
            number.setGeometry(
                0,
                self.ui_var.sim_powerM_title_H,
                self.ui_var.sim_powerM_width,
                self.ui_var.sim_powerM_number_H,
            )

            self.widgetList.append(frame)
            self.widgetList.append(label)
            self.widgetList.append(number)

        self.potential_update()

        # 잠재능력 옵션 순위표
        self.potentialRank_frame = QFrame(self.parent)
        self.potentialRank_frame.setGeometry(
            0,
            self.potential_frame.y()
            + self.potential_frame.height()
            + self.ui_var.sim_main_D,
            928,
            self.ui_var.sim_title_H
            + (self.ui_var.sim_widget_D + self.ui_var.sim_potentialRank_frame_H),
        )
        self.potentialRank_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )
        self.widgetList.append(self.potentialRank_frame)

        self.potentialRank_title = Title(
            self.potentialRank_frame, "잠재능력 옵션 순위표"
        )
        self.widgetList.append(self.potentialRank_title.frame)
        self.widgetList.append(self.potentialRank_title.label)

        self.potentialRanks = PotentialRank(self.potentialRank_frame, self.shared_data)

        for i in range(4):
            self.potentialRanks.frames[i].setGeometry(
                self.ui_var.sim_potentialRank_margin
                + (
                    self.ui_var.sim_potentialRank_width
                    + self.ui_var.sim_potentialRank_D
                )
                * i,
                self.ui_var.sim_label_H + self.ui_var.sim_widget_D,
                self.ui_var.sim_potentialRank_width,
                self.ui_var.sim_potentialRank_frame_H,
            )
            self.potentialRanks.titles[i].setGeometry(
                0,
                0,
                self.ui_var.sim_potentialRank_width,
                self.ui_var.sim_potentialRank_title_H + 1,
            )
            self.potentialRanks.table_frames[i].setGeometry(
                0,
                self.ui_var.sim_potentialRank_title_H,
                self.ui_var.sim_potentialRank_width,
                self.ui_var.sim_potentialRank_ranks_H,
            )

            for j in range(16):
                self.potentialRanks.ranks[i][j].setGeometry(
                    0,
                    self.ui_var.sim_potentialRank_rank_H * j,
                    self.ui_var.sim_potentialRank_rank_ranking_W,
                    self.ui_var.sim_potentialRank_rank_H,
                )
                self.potentialRanks.labels[i][j].setGeometry(
                    self.ui_var.sim_potentialRank_rank_ranking_W,
                    self.ui_var.sim_potentialRank_rank_H * j,
                    self.ui_var.sim_potentialRank_rank_potential_W,
                    self.ui_var.sim_potentialRank_rank_H,
                )
                self.potentialRanks.powers[i][j].setGeometry(
                    self.ui_var.sim_potentialRank_rank_ranking_W
                    + self.ui_var.sim_potentialRank_rank_potential_W,
                    self.ui_var.sim_potentialRank_rank_H * j,
                    self.ui_var.sim_potentialRank_rank_power_W,
                    self.ui_var.sim_potentialRank_rank_H,
                )

            self.widgetList.extend(self.potentialRanks.ranks[i])
            self.widgetList.extend(self.potentialRanks.labels[i])
            self.widgetList.extend(self.potentialRanks.powers[i])

        self.widgetList.extend(self.potentialRanks.frames)
        self.widgetList.extend(self.potentialRanks.titles)
        self.widgetList.extend(self.potentialRanks.table_frames)

    def update_efficiency(self):
        if self.efficiency_statL.currentIndex() == self.efficiency_statR.currentIndex():
            [
                self.efficiency_power_labels.numbers[i].setText(
                    f"{int(self.efficiency_statInput.text()):.2f}"
                )
                for i in range(4)
            ]
            return

        stats = self.shared_data.info_stats.copy()
        stats.add_stat_from_index(
            self.efficiency_statL.currentIndex(), int(self.efficiency_statInput.text())
        )

        powers = detSimulate(
            self.shared_data,
            stats,
            self.shared_data.info_sim_details,
        ).powers
        reqStats = get_req_stats(
            self.shared_data,
            powers,
            list(self.shared_data.STATS.keys())[self.efficiency_statR.currentIndex()],
        )

        [self.efficiency_power_labels.numbers[i].setText(reqStats[i]) for i in range(4)]

    def efficiency_Changed(self):
        text = self.efficiency_statInput.text()
        index = self.efficiency_statL.currentIndex()
        stat_name = list(self.shared_data.STATS.keys())[index]

        if not text.isdigit():
            [self.efficiency_power_labels.labels[i].setText("오류") for i in range(4)]
            return

        stat = self.shared_data.info_stats.get_stat_from_name(stat_name) + int(text)

        if self.shared_data.STAT_RANGES[stat_name][0] <= stat:
            if self.shared_data.STAT_RANGES[stat_name][1] == None:
                self.update_efficiency()
                return

            else:
                if stat <= self.shared_data.STAT_RANGES[stat_name][1]:
                    self.update_efficiency()
                    return

                [
                    self.efficiency_power_labels.numbers[i].setText("오류")
                    for i in range(4)
                ]
                return

        [self.efficiency_power_labels.numbers[i].setText("오류") for i in range(4)]
        return

    def stat_inputChanged(self):
        # 스탯이 정상적으로 입력되었는지 확인
        def checkInput(num, text) -> bool:
            try:
                value = int(text)

            except ValueError:
                return False

            stat_name = list(self.shared_data.STATS.keys())[num]

            stat = self.shared_data.info_stats.get_stat_from_name(stat_name) + value

            return (
                self.shared_data.STAT_RANGES[stat_name][0]
                <= stat
                <= self.shared_data.STAT_RANGES[stat_name][1]
            )

        if not False in [
            checkInput(i, j.text()) for i, j in enumerate(self.additional_stats.inputs)
        ]:  # 모두 digit
            for i in self.additional_stats.inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            self.shared_data.is_input_valid["stat"] = True
            self.update_additional_power_list()

        else:  # 하나라도 통과X
            for i, j in enumerate(self.additional_stats.inputs):
                if not checkInput(i, j.text()):  # 통과X면 빨간색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 2px solid {self.ui_var.sim_input_colorsRed}; border-radius: 4px; }}"
                    )

                else:  # 통과O면 원래색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

            self.shared_data.is_input_valid["stat"] = False

    def skill_inputChanged(self):
        # 스킬이 정상적으로 입력되었는지 확인
        def checkInput(i: int, text: str) -> bool:
            if not text.isdigit():
                return False

            return (
                1
                <= int(text)
                <= self.shared_data.MAX_SKILL_LEVEL[self.shared_data.server_ID]
            )

        if not False in [
            checkInput(i, j.text()) for i, j in enumerate(self.additional_skills.inputs)
        ]:  # 모두 통과
            for i in self.additional_skills.inputs:  # 통과O면 원래색
                i.setStyleSheet(
                    f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                )

            self.shared_data.is_input_valid["skill"] = True
            self.update_additional_power_list()

        else:  # 하나라도 통과X
            for i, j in enumerate(self.additional_skills.inputs):
                if not checkInput(i, j.text()):  # 통과X면 빨간색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 2px solid {self.ui_var.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

            self.shared_data.is_input_valid["skill"] = False

    def update_additional_power_list(self):
        if all(self.shared_data.is_input_valid.values()):
            stats = self.shared_data.info_stats.copy()
            for i in self.additional_stats.inputs:
                stats.add_stat_from_index(
                    self.additional_stats.inputs.index(i), int(i.text())
                )
            # stats = [
            #     stats[i] + int(self.additional_stats.inputs[i].text())
            #     for i in range(len(stats))
            # ]

            skills: dict[str, int] = self.shared_data.info_skill_levels.copy()
            for i, j in enumerate(self.additional_skills.inputs):
                skills[get_available_skills(self.shared_data)[i]] = int(j.text())

            powers = detSimulate(
                self.shared_data,
                stats,
                self.shared_data.info_sim_details,
                skills,
            ).powers

            diff_powers = [powers[i] - self.shared_data.powers[i] for i in range(4)]

            [
                self.additional_power_labels.numbers[i].setText(
                    f"{int(powers[i]):}\n({round(diff_powers[i]):+}, {round(diff_powers[i] / self.shared_data.powers[i] * 100, 2):+.1f}%)"
                )
                for i in range(4)
            ]

        else:
            [self.additional_power_labels.numbers[i].setText("오류") for i in range(4)]

    def potential_update(self):
        indexList = [
            self.potential_stat0.currentText(),
            self.potential_stat1.currentText(),
            self.potential_stat2.currentText(),
        ]

        stats = self.shared_data.info_stats.copy()
        for i in range(3):
            stat, value = self.shared_data.POTENTIAL_STATS[indexList[i]]
            stats.add_stat_from_name(stat, value)

        powers = detSimulate(
            self.shared_data,
            stats,
            self.shared_data.info_sim_details,
        ).powers

        diff_powers = [round(powers[i] - self.shared_data.powers[i]) for i in range(4)]

        [
            self.potential_power_labels.numbers[i].setText(f"{diff_powers[i]:+}")
            for i in range(4)
        ]


class Sim4UI:
    def __init__(self, parent, shared_data: SharedData):
        self.shared_data = shared_data
        self.parent = parent

        self.ui_var = UI_Variable()

        self.makeSim4UI()

    def makeSim4UI(self):
        self.shared_data.is_card_updated = False

        powers = detSimulate(
            self.shared_data,
            self.shared_data.info_stats,
            self.shared_data.info_sim_details,
        ).powers
        for i, power in enumerate(powers):
            self.shared_data.powers[i] = power
        # self.sim_powers = [str(int(i)) for i in self.sim_powers]

        self.name = ""
        self.prev_name = ""
        self.real_name = ""
        self.char_image = None
        self.info_char_data = None

        # 카드 프레임
        self.mainframe = QFrame(self.parent)
        self.mainframe.setGeometry(
            0,
            0,
            928,
            self.ui_var.sim_char_frame_H,
        )
        self.mainframe.setStyleSheet(
            """QFrame {
            background-color: rgb(255, 255, 255);
            border: 0px solid;
        }"""
        )

        ## 캐릭터 정보 입력
        self.info_frame = QFrame(self.mainframe)
        self.info_frame.setGeometry(
            self.ui_var.sim_char_margin,
            self.ui_var.sim_char_margin_y,
            self.ui_var.sim_charInfo_W,
            self.ui_var.sim_charInfo_H,
        )
        self.info_frame.setStyleSheet(
            """QFrame {
            background-color: #F8F8F8;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
        }"""
        )

        # 닉네임 입력
        self.info_name_frame = QFrame(self.info_frame)
        self.info_name_frame.setGeometry(
            self.ui_var.sim_charInfo_marginX,
            self.ui_var.sim_charInfo_marginY,
            self.ui_var.sim_charInfo_frame_W,
            self.ui_var.sim_charInfo_nickname_H,
        )
        self.info_name_frame.setStyleSheet(
            """QFrame {
            background-color: #FFFFFF;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
        }"""
        )

        self.info_name_label = QLabel("닉네임", self.info_name_frame)
        self.info_name_label.setGeometry(
            self.ui_var.sim_charInfo_nickname_input_margin,
            self.ui_var.sim_charInfo_label_y,
            self.ui_var.sim_charInfo_nickname_input_W,
            self.ui_var.sim_charInfo_label_H,
        )
        self.info_name_label.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.info_name_label.setFont(CustomFont(14))
        self.info_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.info_name_input = CustomLineEdit(self.info_name_frame, None, "", 12)
        self.info_name_input.setGeometry(
            self.ui_var.sim_charInfo_nickname_input_margin,
            self.ui_var.sim_charInfo_label_y + self.ui_var.sim_charInfo_label_H,
            self.ui_var.sim_charInfo_nickname_input_W,
            self.ui_var.sim_charInfo_nickname_input_H,
        )
        self.info_name_input.setFocus()

        self.info_name_button = QPushButton("불러오기", self.info_name_frame)
        self.info_name_button.setGeometry(
            self.ui_var.sim_charInfo_nickname_load_margin,
            self.ui_var.sim_charInfo_nickname_load_y,
            self.ui_var.sim_charInfo_nickname_load_W,
            self.ui_var.sim_charInfo_nickname_load_H,
        )
        self.info_name_button.setStyleSheet(
            f"""QPushButton {{
            background-color: #70BB70;
            border: 1px solid {self.ui_var.sim_input_colors[1]};
            border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #60A060;
            }}"""
        )
        self.info_name_button.setFont(CustomFont(10))
        self.info_name_button.clicked.connect(self.load_char_info)

        # 캐릭터 선택
        # 캐릭터 불러오면 시뮬레이션 진행한 직업과 같은 것만 선택 가능하도록
        self.info_char_frame = QFrame(self.info_frame)
        self.info_char_frame.setGeometry(
            self.ui_var.sim_charInfo_marginX,
            self.ui_var.sim_charInfo_marginY * 2 + self.ui_var.sim_charInfo_nickname_H,
            self.ui_var.sim_charInfo_frame_W,
            self.ui_var.sim_charInfo_char_H,
        )
        self.info_char_frame.setStyleSheet(
            """QFrame {
            background-color: #FFFFFF;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
        }"""
        )

        self.info_char_label = QLabel("캐릭터 선택", self.info_char_frame)
        self.info_char_label.setGeometry(
            0,
            self.ui_var.sim_charInfo_label_y,
            self.ui_var.sim_charInfo_frame_W,
            self.ui_var.sim_charInfo_label_H,
        )
        self.info_char_label.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.info_char_label.setFont(CustomFont(14))
        self.info_char_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.info_char_buttons = []
        for i in range(3):
            button = QPushButton("", self.info_char_frame)
            button.setGeometry(
                self.ui_var.sim_charInfo_char_button_margin
                + (
                    self.ui_var.sim_charInfo_char_button_W
                    + self.ui_var.sim_charInfo_char_button_margin
                )
                * i,
                self.ui_var.sim_charInfo_char_button_y,
                self.ui_var.sim_charInfo_char_button_W,
                self.ui_var.sim_charInfo_char_button_H,
            )
            button.setStyleSheet(
                f"""QPushButton {{
                background-color: {self.ui_var.sim_input_colors[0]};
                border: 1px solid {self.ui_var.sim_input_colors[1]};
                border-radius: 8px;
                }}"""
            )
            button.setFont(CustomFont(10))

            self.info_char_buttons.append(button)

        # 전투력 표시
        self.info_power_display = [True, True, True, True]

        self.info_power_frame = QFrame(self.info_frame)
        self.info_power_frame.setGeometry(
            self.ui_var.sim_charInfo_marginX,
            self.ui_var.sim_charInfo_marginY * 3
            + self.ui_var.sim_charInfo_nickname_H
            + self.ui_var.sim_charInfo_char_H,
            self.ui_var.sim_charInfo_frame_W,
            self.ui_var.sim_charInfo_char_H,
        )
        self.info_power_frame.setStyleSheet(
            """QFrame {
            background-color: #FFFFFF;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
        }"""
        )

        self._info_power_label = QLabel("전투력 표시", self.info_power_frame)
        self._info_power_label.setGeometry(
            0,
            self.ui_var.sim_charInfo_label_y,
            self.ui_var.sim_charInfo_frame_W,
            self.ui_var.sim_charInfo_label_H,
        )
        self._info_power_label.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self._info_power_label.setFont(CustomFont(14))
        self._info_power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.info_power_buttons = []
        for i in range(4):
            button = QPushButton(
                self.shared_data.POWER_TITLES[i], self.info_power_frame
            )
            button.setGeometry(
                self.ui_var.sim_charInfo_power_button_margin
                + (
                    self.ui_var.sim_charInfo_power_button_W
                    + self.ui_var.sim_charInfo_power_button_margin
                )
                * i,
                self.ui_var.sim_charInfo_power_button_y,
                self.ui_var.sim_charInfo_power_button_W,
                self.ui_var.sim_charInfo_power_button_H,
            )
            button.setStyleSheet(
                f"""QPushButton {{
                background-color: #FFFFFF;
                border: 1px solid {self.ui_var.sim_input_colors[1]};
                border-radius: 5px;
                }}
                QPushButton:hover {{
                    background-color: #F0F0F0;
                }}"""
            )
            button.setFont(CustomFont(10))
            button.clicked.connect(partial(lambda x: self.info_powers_clicked(x), i))

            self.info_power_buttons.append(button)

        # 입력 완료
        self.info_complete_button = QPushButton("입력 완료", self.info_frame)
        self.info_complete_button.setGeometry(
            self.ui_var.sim_charInfo_complete_margin,
            self.ui_var.sim_charInfo_marginY * 3
            + self.ui_var.sim_charInfo_nickname_H
            + self.ui_var.sim_charInfo_char_H
            + self.ui_var.sim_charInfo_power_H
            + self.ui_var.sim_charInfo_complete_y,
            self.ui_var.sim_charInfo_complete_W,
            self.ui_var.sim_charInfo_complete_H,
        )
        self.info_complete_button.setStyleSheet(
            f"""QPushButton {{
            background-color: #70BB70;
            border: 1px solid {self.ui_var.sim_input_colors[1]};
            border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #60A060;
            }}"""
        )
        self.info_complete_button.setFont(CustomFont(14))
        self.info_complete_button.clicked.connect(self.card_update)

        self.info_save_button = QPushButton("저장", self.info_frame)
        self.info_save_button.setGeometry(
            self.ui_var.sim_charInfo_save_margin,
            self.ui_var.sim_charInfo_marginY * 3
            + self.ui_var.sim_charInfo_nickname_H
            + self.ui_var.sim_charInfo_char_H
            + self.ui_var.sim_charInfo_power_H
            + self.ui_var.sim_charInfo_save_y,
            self.ui_var.sim_charInfo_save_W,
            self.ui_var.sim_charInfo_save_H,
        )
        self.info_save_button.setStyleSheet(
            f"""QPushButton {{
            background-color: #FF8282;
            border: 1px solid {self.ui_var.sim_input_colors[1]};
            border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #FF6060;
            }}"""
        )
        self.info_save_button.setFont(CustomFont(14))
        self.info_save_button.clicked.connect(self.card_save)

        ## 캐릭터 카드
        self.card_frame = QFrame(self.mainframe)
        self.card_frame.setGeometry(
            self.ui_var.sim_char_margin * 3 + self.ui_var.sim_charInfo_W,
            self.ui_var.sim_char_margin_y,
            self.ui_var.sim_charCard_W,
            self.ui_var.sim_charCard_H,
        )
        self.card_frame.setStyleSheet(
            """QFrame {
            background-color: #FFFFFF;
            border: 3px solid #CCCCCC;
            border-radius: 0px;
        }"""
        )

        # 타이틀
        self.card_title = QLabel("한월 캐릭터 카드", self.card_frame)
        self.card_title.setGeometry(
            0,
            0,
            self.ui_var.sim_charCard_W,
            self.ui_var.sim_charCard_title_H,
        )
        self.card_title.setStyleSheet(
            """QLabel {
            background-color: #CADEFC;
            border: 3px solid #CCCCCC;
            border-bottom: 0px solid;
            border-radius: 0px;
        }"""
        )
        self.card_title.setFont(CustomFont(18))
        self.card_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 이미지
        self.card_image_bg = QLabel("", self.card_frame)
        self.card_image_bg.setGeometry(
            self.ui_var.sim_charCard_image_margin,
            self.ui_var.sim_charCard_image_margin + self.ui_var.sim_charCard_title_H,
            self.ui_var.sim_charCard_image_W,
            self.ui_var.sim_charCard_image_H,
        )
        self.card_image_bg.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 5px solid #AAAAAA;
            border-radius: 5px;
        }"""
        )
        self.card_image_bg.setScaledContents(True)

        self.card_image = QLabel("", self.card_frame)
        self.card_image.setGeometry(
            self.ui_var.sim_charCard_image_margin + 15,
            self.ui_var.sim_charCard_image_margin
            + self.ui_var.sim_charCard_title_H
            + 15,
            self.ui_var.sim_charCard_image_W - 30,  # 126
            self.ui_var.sim_charCard_image_H - 30,  # 282
        )
        self.card_image.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.card_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_image.setScaledContents(True)

        # 캐릭터 정보
        self.card_name = QLabel("", self.card_frame)
        self.card_name.setGeometry(
            self.ui_var.sim_charCard_name_margin,
            self.ui_var.sim_charCard_name_y,
            self.ui_var.sim_charCard_name_W,
            self.ui_var.sim_charCard_name_H,
        )
        self.card_name.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.card_name.setFont(CustomFont(18))
        self.card_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card_job = QLabel("", self.card_frame)
        self.card_job.setGeometry(
            self.ui_var.sim_charCard_job_margin,
            self.ui_var.sim_charCard_job_y,
            self.ui_var.sim_charCard_job_W,
            self.ui_var.sim_charCard_job_H,
        )
        self.card_job.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.card_job.setFont(CustomFont(12))
        self.card_job.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card_level = QLabel("", self.card_frame)
        self.card_level.setGeometry(
            self.ui_var.sim_charCard_level_margin,
            self.ui_var.sim_charCard_level_y,
            self.ui_var.sim_charCard_level_W,
            self.ui_var.sim_charCard_level_H,
        )
        self.card_level.setStyleSheet(
            """QLabel {
            background-color: transparent;
            border: 0px solid;
        }"""
        )
        self.card_level.setFont(CustomFont(12))
        self.card_level.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card_name_line = QFrame(self.card_frame)
        self.card_name_line.setGeometry(
            self.ui_var.sim_charCard_name_margin + 10,
            self.ui_var.sim_charCard_name_y + self.ui_var.sim_charCard_name_H,
            self.ui_var.sim_charCard_name_line_W,
            1,
        )
        self.card_name_line.setStyleSheet(
            """QFrame {
            background-color: #CCCCCC;
            border: 0px solid;
        }"""
        )

        self.card_info_line = QFrame(self.card_frame)
        self.card_info_line.setGeometry(
            self.ui_var.sim_charCard_level_margin + 1,
            self.ui_var.sim_charCard_level_y + 12,
            1,
            self.ui_var.sim_charCard_info_line_H,
        )
        self.card_info_line.setStyleSheet(
            """QFrame {
            background-color: #CCCCCC;
            border: 0px solid;
        }"""
        )

        # 전투력
        self.card_powers = [[], [], [], []]
        for i in range(4):
            frame = QFrame(self.card_frame)
            frame.setGeometry(
                self.ui_var.sim_charCard_powerFrame_margin,
                self.ui_var.sim_charCard_powerFrame_y
                + self.ui_var.sim_charCard_powerFrame_H * i,
                self.ui_var.sim_charCard_powerFrame_W,
                self.ui_var.sim_charCard_powerFrame_H,
            )
            frame.setStyleSheet(
                """QFrame {
                background-color: transparent;
                border: 0px solid;
            }"""
            )

            title = QLabel(self.shared_data.POWER_TITLES[i], frame)
            title.setStyleSheet(
                f"""QLabel {{
                    background-color: rgb({self.ui_var.sim_colors4[i]});
                    border: 1px solid rgb({self.ui_var.sim_colors4[i]});
                    border-top-left-radius: 4px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 4px;
                    border-bottom-right-radius: 0px;
                }}"""
            )
            title.setGeometry(
                0,
                0,
                self.ui_var.sim_charCard_power_title_W,
                self.ui_var.sim_charCard_powerFrame_H,
            )
            title.setFont(CustomFont(12))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            number = QLabel("", frame)
            number.setStyleSheet(
                f"""QLabel {{
                    background-color: rgba({self.ui_var.sim_colors4[i]}, 120);
                    border: 1px solid rgb({self.ui_var.sim_colors4[i]});
                    border-left: 0px solid;
                    border-top-left-radius: 0px;
                    border-top-right-radius: 4px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 4px
                }}"""
            )
            number.setGeometry(
                self.ui_var.sim_charCard_power_title_W,
                0,
                self.ui_var.sim_charCard_power_number_W,
                self.ui_var.sim_charCard_powerFrame_H,
            )
            number.setFont(CustomFont(14))
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.card_powers[i].append(frame)
            self.card_powers[i].append(title)
            self.card_powers[i].append(number)

    def load_char_info(self):
        self.info_char_data = None

        try:
            data = get_character_info(self.info_name_input.text())
        except:
            print("error")
            return

        for i, j in enumerate(data):
            job, level = j["job"], j["level"]
            if job == self.shared_data.job_ID:
                self.info_char_buttons[i].setText(f"{job} | Lv.{level}")
                self.info_char_buttons[i].setStyleSheet(
                    f"""QPushButton {{
                    background-color: #FFFFFF;
                    border: 1px solid {self.ui_var.sim_input_colors[1]};
                    border-radius: 8px;
                    color: #000000;
                    }}
                    QPushButton:hover {{
                        background-color: #F0F0F0;
                    }}"""
                )

                self.info_char_buttons[i].clicked.connect(
                    partial(lambda x, y: self.select_char(x, y), i, j)
                )
            else:
                self.info_char_buttons[i].setText(f"{job} | Lv.{level}")
                self.info_char_buttons[i].setStyleSheet(
                    f"""QPushButton {{
                    background-color: #FFFFFF;
                    border: 1px solid {self.ui_var.sim_input_colors[1]};
                    border-radius: 8px;
                    color: rgb(153, 153, 153);
                    }}"""
                )

                try:
                    self.info_char_buttons[i].clicked.disconnect()
                except:
                    pass

    def select_char(self, index, data):
        self.load_char_info()

        self.info_char_data = data

        self.info_char_buttons[index].setStyleSheet(
            f"""QPushButton {{
            background-color: #CCCCCC;
            border: 1px solid {self.ui_var.sim_input_colors[1]};
            border-radius: 8px;
            color: #000000;
            }}"""
        )

    def info_powers_clicked(self, num):
        self.info_power_display[num] = not self.info_power_display[num]

        for i in range(4):
            self.info_power_buttons[i].setStyleSheet(
                f"""QPushButton {{
                background-color: #FFFFFF;
                border: 1px solid {self.ui_var.sim_input_colors[1]};
                border-radius: 5px;
                color: {"#000000" if self.info_power_display[i] else "rgb(153, 153, 153)"};
                }}
                QPushButton:hover {{
                    background-color: #F0F0F0;
                }}"""
            )

    def card_save(self):
        if not self.shared_data.is_card_updated:
            return

        scale_factor = 3
        original_size = self.card_frame.size()
        scaled_size = original_size * scale_factor

        pixmap = QPixmap(scaled_size)
        pixmap.fill()

        painter = QPainter(pixmap)
        painter.scale(scale_factor, scale_factor)
        self.card_frame.render(painter)
        painter.end()

        # Open a file dialog to save the image
        file_dialog = QFileDialog()
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilters(["Images (*.png *.jpg *.bmp)"])
        file_dialog.setDefaultSuffix("png")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            pixmap.save(file_path)
            os.startfile(file_path)

    def card_update(self):
        if self.info_char_data is None:
            self.shared_data.is_card_updated = False
            return

        if not any(self.info_power_display):
            self.shared_data.is_card_updated = False
            return

        self.name = self.info_name_input.text()
        if self.name != self.prev_name:
            try:
                self.real_name, url = get_character_card_data(self.name)
            except:
                self.shared_data.is_card_updated = False
                return

            self.char_image = requests.get(url).content
            self.prev_name = self.name

        pixmap = QPixmap(convert_resource_path("resources\\image\\card_bg.png"))
        self.card_image_bg.setPixmap(pixmap)
        pixmap = QPixmap()
        pixmap.loadFromData(self.char_image)

        h_ratio = 282 / pixmap.height()
        width = round(pixmap.width() * h_ratio)
        dWidth = width - (self.ui_var.sim_charCard_image_W - 30)

        self.card_image.setGeometry(
            self.ui_var.sim_charCard_image_margin + 15 - dWidth // 2,
            self.ui_var.sim_charCard_image_margin
            + self.ui_var.sim_charCard_title_H
            + 15,
            round(pixmap.width() * h_ratio),
            self.ui_var.sim_charCard_image_H - 30,
        )
        self.card_image.setPixmap(pixmap)

        adjust_font_size(self.card_name, self.real_name, 18)
        self.card_job.setText(self.shared_data.job_ID)
        self.card_level.setText(f"Lv.{self.info_char_data['level']}")

        countF = self.info_power_display.count(False)
        count = 0
        for i in range(4):
            if self.info_power_display[i]:
                self.card_powers[i][0].setGeometry(
                    self.ui_var.sim_charCard_powerFrame_margin,
                    self.ui_var.sim_charCard_powerFrame_y
                    + self.ui_var.sim_charCard_powerFrame_H * count
                    + 20 * countF,
                    self.ui_var.sim_charCard_powerFrame_W,
                    self.ui_var.sim_charCard_powerFrame_H,
                )
                self.card_powers[i][2].setText(f"{int(self.shared_data.powers[i])}")

                self.card_powers[i][0].show()
                count += 1

            else:
                self.card_powers[i][0].hide()

        self.shared_data.is_card_updated = True


class StatInput:
    def __init__(self, mainframe, shared_data: SharedData, connected_function):
        self.frames = []
        self.labels = []
        self.inputs = []

        # 스탯 입력창 생성
        for i in range(len(list(shared_data.STATS.values()))):
            frame = QFrame(mainframe)
            frame.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px solid; }"
            )

            label = QLabel(list(shared_data.STATS.values())[i], frame)
            label.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            label.setFont(CustomFont(10))

            lineEdit = CustomLineEdit(frame, connected_function)

            self.frames.append(frame)
            self.labels.append(label)
            self.inputs.append(lineEdit)


class SkillInput:
    def __init__(self, mainframe, shared_data: SharedData, connected_function):
        ui_var = UI_Variable()

        texts = shared_data.skill_data[shared_data.server_ID]["jobs"][
            shared_data.job_ID
        ]["skills"]

        self.frames = []
        self.names = []
        self.images = []
        self.labels = []
        self.inputs = []

        for i in range(8):
            frame = QFrame(mainframe)
            frame.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px solid black; }"
            )

            name = QLabel(texts[i], frame)
            name.setStyleSheet(
                f"QLabel {{ border: 1px solid {ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
            )
            name.setFont(CustomFont(14))
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label = QLabel("레벨", frame)
            label.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            label.setFont(CustomFont(10))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lineEdit = CustomLineEdit(frame, connected_function)

            image = QPushButton(frame)
            image.setGeometry(
                0,
                ui_var.sim_skill_name_H,
                ui_var.sim_skill_image_Size,
                ui_var.sim_skill_image_Size,
            )
            image.setStyleSheet(
                "QPushButton { background-color: transparent; border: 0px solid; }"
            )
            image.setIcon(
                QIcon(
                    get_skill_pixmap(
                        shared_data, skill_name=get_available_skills(shared_data)[i]
                    )
                )
            )
            image.setIconSize(
                QSize(ui_var.sim_skill_image_Size, ui_var.sim_skill_image_Size)
            )

            self.frames.append(frame)
            self.names.append(name)
            self.labels.append(label)
            self.inputs.append(lineEdit)
            self.images.append(image)


class SimInfoInput:
    def __init__(self, mainframe, shared_data: SharedData, connected_function):
        self.frames = []
        self.labels = []
        self.inputs = []

        for i in range(len(shared_data.SIM_DETAILS)):
            frame = QFrame(mainframe)
            frame.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px solid; }"
            )

            label = QLabel(list(shared_data.SIM_DETAILS.values())[i], frame)
            label.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            label.setFont(CustomFont(10))

            lineEdit = CustomLineEdit(frame, connected_function)

            self.frames.append(frame)
            self.labels.append(label)
            self.inputs.append(lineEdit)


class PowerLabels:
    def __init__(self, mainframe, shared_data: SharedData, texts, font_size=18):
        ui_var = UI_Variable()

        self.frames = []
        self.labels = []
        self.numbers = []

        for i in range(4):
            frame = QFrame(mainframe)

            label = QLabel(shared_data.POWER_TITLES[i], frame)
            label.setStyleSheet(
                f"QLabel {{ background-color: rgb({ui_var.sim_colors4[i]}); border: 1px solid rgb({ui_var.sim_colors4[i]}); border-bottom: 0px solid; border-top-left-radius: 4px; border-top-right-radius: 4px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; }}"
            )
            label.setFont(CustomFont(14))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            number = QLabel(texts[i], frame)
            number.setStyleSheet(
                f"QLabel {{ background-color: rgba({ui_var.sim_colors4[i]}, 120); border: 1px solid rgb({ui_var.sim_colors4[i]}); border-top: 0px solid; border-top-left-radius: 0px; border-top-right-radius: 0px; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px }}"
            )
            number.setFont(CustomFont(font_size))
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.frames.append(frame)
            self.labels.append(label)
            self.numbers.append(number)


class AnalysisDetails:
    def __init__(self, mainframe, analysis: SimAnalysis, details):
        ui_var = UI_Variable()

        self.frame = QFrame(mainframe)
        self.frame.setStyleSheet(
            "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-top-left-radius: 0px; border-top-right-radius: 6px; border-bottom-left-radius: 0px; border-bottom-right-radius: 6px; }"
        )

        self.color = QFrame(self.frame)
        self.color.setGeometry(
            0,
            0,
            ui_var.sim_analysis_color_W,
            ui_var.sim_analysis_frame_H,
        )

        self.title = QLabel(analysis.title, self.frame)
        self.title.setGeometry(
            ui_var.sim_analysis_color_W,
            0,
            ui_var.sim_analysis_widthXC,
            ui_var.sim_analysis_title_H,
        )
        self.title.setStyleSheet(
            "QLabel { background-color: transparent; border: 0px solid; }"
        )
        self.title.setFont(CustomFont(14))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.number = QLabel(analysis.value, self.frame)
        self.number.setGeometry(
            ui_var.sim_analysis_color_W,
            ui_var.sim_analysis_title_H,
            ui_var.sim_analysis_widthXC,
            ui_var.sim_analysis_number_H,
        )
        self.number.setStyleSheet(
            "QLabel { background-color: transparent; border: 0px solid; }"
        )
        self.number.setFont(CustomFont(18))
        self.number.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.detail_frames = []
        self.detail_labels = []
        self.detail_numbers = []

        for i in range(6):
            detail_frame = QFrame(self.frame)
            detail_frame.setGeometry(
                ui_var.sim_analysis_color_W
                + ui_var.sim_analysis_details_margin
                + (ui_var.sim_analysis_details_W + ui_var.sim_analysis_details_margin)
                * (i % 3)
                - 1,
                ui_var.sim_analysis_title_H
                + ui_var.sim_analysis_number_H
                + ui_var.sim_analysis_number_marginH
                + ui_var.sim_analysis_details_H * (i // 3),
                ui_var.sim_analysis_details_W,
                ui_var.sim_analysis_details_H,
            )
            detail_frame.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px solid; }"
            )

            detail_title = QLabel(details[i], detail_frame)
            detail_title.setGeometry(
                0,
                0,
                ui_var.sim_analysis_detailsT_W,
                ui_var.sim_analysis_details_H,
            )
            detail_title.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; color: #A0A0A0 }"
            )
            detail_title.setFont(CustomFont(8))
            detail_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            detail_number = QLabel(analysis.get_data_from_str(details[i]), detail_frame)
            detail_number.setGeometry(
                ui_var.sim_analysis_detailsT_W,
                0,
                ui_var.sim_analysis_detailsN_W,
                ui_var.sim_analysis_details_H,
            )
            detail_number.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            detail_number.setFont(CustomFont(8))
            detail_number.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.detail_frames.append(detail_frame)
            self.detail_labels.append(detail_title)
            self.detail_numbers.append(detail_number)


class PotentialRank:
    def __init__(self, mainframe, shared_data: SharedData):
        ui_var = UI_Variable()

        texts = self.get_potential_rank(shared_data)
        colors = ["255, 163, 134", "255, 152, 0", "33, 150, 243", "165, 214, 167"]
        transparencies = ["140", "89", "77", "179"]

        self.frames = []
        self.titles = []
        self.table_frames = []
        self.ranks = [[], [], [], []]
        self.labels = [[], [], [], []]
        self.powers = [[], [], [], []]

        for i in range(4):
            frame = QFrame(mainframe)

            title = QLabel(shared_data.POWER_TITLES[i], frame)
            title.setStyleSheet(
                f"""QLabel {{
                    background-color: rgb({ui_var.sim_colors4[i]});
                    border: 1px solid rgb({ui_var.sim_colors4[i]});
                    border-bottom: 0px solid;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                }}"""
            )
            title.setFont(CustomFont(14))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            table_frame = QFrame(frame)
            table_frame.setStyleSheet(
                f"""QFrame {{
                    background-color: rgba({ui_var.sim_colors4[i]}, 120);
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 4px;
                    border-bottom-right-radius: 4px
                }}"""
            )

            self.frames.append(frame)
            self.titles.append(title)
            self.table_frames.append(table_frame)

            for j in range(16):  # 인덱스 포함 16개
                rank = QLabel(texts[i][j][0], table_frame)
                rank_style = f"""QLabel {{
                        background-color: {f"rgba({colors[i]}, {transparencies[i]})" if j == 0 else "transparent"};
                        border: 1px solid rgb({ui_var.sim_colors4[i]});
                        border-top: 0px solid;
                        border-top-left-radius: 0px;
                        border-top-right-radius: 0px;
                        border-bottom-left-radius: {"4" if j == 15 else "0"}px;
                        border-bottom-right-radius: 0px;
                    }}"""
                rank.setStyleSheet(rank_style)
                rank.setFont(CustomFont(10))
                rank.setAlignment(Qt.AlignmentFlag.AlignCenter)

                label = QLabel(texts[i][j][1], table_frame)
                label_style = f"""QLabel {{
                        background-color: {f"rgba({colors[i]}, {transparencies[i]})" if j == 0 else "transparent"};
                        border: 1px solid rgb({ui_var.sim_colors4[i]});
                        border-top: 0px solid;
                        border-left: 0px solid;
                        border-right: 0px solid;
                        border-top-left-radius: 0px;
                        border-top-right-radius: 0px;
                        border-bottom-left-radius: 0px;
                        border-bottom-right-radius: 0px;
                    }}"""
                label.setStyleSheet(label_style)
                label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                label.setFont(CustomFont(10))

                power = QLabel(texts[i][j][2], table_frame)
                power_style = f"""QLabel {{
                            background-color: {f"rgba({colors[i]}, {transparencies[i]})" if j == 0 else "transparent"};
                            border: 1px solid rgb({ui_var.sim_colors4[i]});
                            border-top: 0px solid;
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-bottom-right-radius: {"4" if j == 15 else "0"}px;
                        }}"""
                power.setStyleSheet(power_style)
                power.setFont(CustomFont(10))
                power.setAlignment(Qt.AlignmentFlag.AlignCenter)

                self.ranks[i].append(rank)
                self.labels[i].append(label)
                self.powers[i].append(power)

    def get_potential_rank(self, shared_data: SharedData):
        texts = [[], [], [], []]
        for key, (stat, value) in shared_data.POTENTIAL_STATS.items():
            stats = shared_data.info_stats.copy()
            stats.add_stat_from_name(stat, value)

            powers = detSimulate(
                shared_data,
                stats,
                shared_data.info_sim_details,
            ).powers
            diff_powers = [
                round(powers[i] - shared_data.powers[i], 5) for i in range(4)
            ]

            for i in range(4):
                texts[i].append([key, diff_powers[i]])

        [texts[i].sort(key=lambda x: x[1], reverse=True) for i in range(4)]

        for i in range(4):
            for j in range(len(shared_data.POTENTIAL_STATS)):
                if texts[i][j][1] == 0:
                    texts[i][j] = ["", "", ""]
                else:
                    texts[i][j][1] = f"+{round(texts[i][j][1])}"
                    texts[i][j].insert(0, str(j + 1))

        [texts[i].insert(0, ["순위", "잠재능력", "전투력"]) for i in range(4)]

        return texts


class Title:
    def __init__(self, parent, text):
        ui_var = UI_Variable()

        self.frame = QFrame(parent)
        self.frame.setGeometry(0, 0, 928, ui_var.sim_title_H)
        self.frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: none; border-bottom: 1px solid #bbbbbb; }"
        )

        self.label = QLabel(text, self.frame)
        self.label.setGeometry(
            ui_var.sim_label_x,
            0,
            928 - ui_var.sim_label_x,
            ui_var.sim_label_H,
        )
        self.label.setFont(CustomFont(16))
