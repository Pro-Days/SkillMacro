from __future__ import annotations

from app.scripts.custom_classes import SimAttack
from app.scripts.shared_data import SharedData

from .data_manager import save_data
from .misc import (
    get_skill_pixmap,
    adjust_font_size,
    get_available_skills,
    convert_resource_path,
)
from .shared_data import UI_Variable
from .simulate_macro import randSimulate, detSimulate, get_req_stats
from .graph import (
    DpmDistributionCanvas,
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
    KVInput,
    SkillImage,
)
from .get_character_data import get_character_info, get_character_card_data

import requests
import os
import sys
from functools import partial
from typing import TYPE_CHECKING
import threading

# import matplotlib.pyplot as plt

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap, QPainter, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QFileDialog,
    QScrollArea,
    QWidget,
    QStackedLayout,
    QVBoxLayout,
    QSizePolicy,
    QGridLayout,
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

        # parent: page2
        self.parent: QFrame = parent
        self.master: MainWindow = master

        self.ui_var = UI_Variable()

        self.make_ui()

    def make_ui(self) -> None:
        """
        시뮬레이션 페이지 UI 구성
        """

        self.nav: Navigation = Navigation(self.parent)

        self.nav.buttons[0].clicked.connect(lambda: self.change_layout(0))
        self.nav.buttons[1].clicked.connect(lambda: self.change_layout(1))
        self.nav.buttons[2].clicked.connect(lambda: self.change_layout(2))
        self.nav.buttons[3].clicked.connect(lambda: self.change_layout(3))
        self.nav.buttons[4].clicked.connect(lambda: self.master.change_layout(0))
        # self.nav.buttons[0].clicked.connect(self.make_simul_page1)
        # self.nav.buttons[1].clicked.connect(self.make_simul_page2)
        # self.nav.buttons[2].clicked.connect(self.make_simul_page3)
        # self.nav.buttons[3].clicked.connect(self.make_simul_page4)
        # self.nav.buttons[4].clicked.connect(lambda: self.master.change_layout(0))

        # 메인 프레임
        self.main_frame: QFrame = QFrame(self.parent)
        self.main_frame.setGeometry(
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
        self.main_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        # 스크롤바
        self.scroll_area: QScrollArea = QScrollArea(self.parent)
        self.scroll_area.setWidget(self.main_frame)
        self.scroll_area.setGeometry(
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
        # self.sim_mainScrollArea.setPalette(self.backPalette)
        self.scroll_area.show()

        # 페이지 레이아웃 설정
        # 페이지를 전환할 때마다 새로 만들지 말고
        # 레이아웃을 전환하는 방식으로 변경
        self.layout = QStackedLayout(self.main_frame)
        self.layout.setSizeConstraint(QStackedLayout.SizeConstraint.SetFixedSize)

        self.UI1 = Sim1UI(self.main_frame, self.shared_data)
        self.UI2 = Sim2UI(self.main_frame, self.shared_data)
        # self.UI3 = Sim3UI(self.main_frame, self.shared_data)
        # self.UI4 = Sim4UI(self.main_frame, self.shared_data)
        self.layout.addWidget(self.UI1)
        self.layout.addWidget(self.UI2)

        self.layout.setCurrentIndex(0)
        self.layout.currentChanged.connect(self._on_current_widget_changed)
        self._on_current_widget_changed(0)

        # self.make_simul_page1()

    def _on_current_widget_changed(self, index: int) -> None:
        """
        현재 표시되는 위젯이 변경될 때 main_frame의 크기를 조절합니다.
        """
        current_widget = self.layout.widget(index)
        if current_widget:
            self.main_frame.setFixedHeight(
                current_widget.height() + self.ui_var.sim_mainFrameMargin
            )

            print(f"current widget height: {current_widget.height()}, index: {index}")
            print(f"ui1 height: {self.UI1.height()}")

    ## change_layout 시작
    # def remove_simul_widgets(self) -> None:
    #     """
    #     시뮬레이션 페이지 모든 위젯 제거
    #     """

    #     # 콤보박스 오류 수정
    #     if self.shared_data.sim_page_type == 3:
    #         comboboxList: list[QComboBox] = [
    #             self.sim3_ui.efficiency_statL,
    #             self.sim3_ui.efficiency_statR,
    #             self.sim3_ui.potential_stat0,
    #             self.sim3_ui.potential_stat1,
    #             self.sim3_ui.potential_stat2,
    #         ]
    #         for i in comboboxList:
    #             i.showPopup()
    #             i.hidePopup()

    #     [i.deleteLater() for i in self.main_frame.findChildren(QWidget)]
    #     self.shared_data.sim_page_type = 0

    #     # plt.close("all")
    #     # plt.clf()

    # def make_simul_page4(self) -> None:
    #     """
    #     시뮬레이션 - 캐릭터 카드 페이지 생성
    #     """

    #     # 입력값 체크
    #     if not all(self.shared_data.is_input_valid.values()):
    #         self.master.get_popup_manager().make_notice_popup("SimInputError")
    #         return

    #     self.remove_simul_widgets()
    #     self.sim_update_nav_button(3)

    #     self.shared_data.sim_page_type = 4

    #     self.sim4_ui = Sim4UI(self.main_frame, self.shared_data)

    #     # 메인 프레임 크기 조정
    #     self.main_frame.setFixedHeight(
    #         self.sim4_ui.info_frame.y()
    #         + self.sim4_ui.info_frame.height()
    #         + self.ui_var.sim_mainFrameMargin,
    #     )
    #     [i.show() for i in self.parent.findChildren(QWidget)]

    #     self.update_position()

    # def make_simul_page3(self) -> None:
    #     """
    #     시뮬레이션 - 스탯 계산기 페이지 생성
    #     """

    #     # 입력값 체크
    #     if not all(self.shared_data.is_input_valid.values()):
    #         self.master.get_popup_manager().make_notice_popup("SimInputError")
    #         return

    #     self.remove_simul_widgets()
    #     self.sim_update_nav_button(2)

    #     self.shared_data.sim_page_type = 3

    #     self.sim3_ui = Sim3UI(self.main_frame, self.shared_data)

    #     # 메인 프레임 크기 조정
    #     self.main_frame.setFixedHeight(
    #         self.sim3_ui.potentialRank_frame.y()
    #         + self.sim3_ui.potentialRank_frame.height()
    #         + self.ui_var.sim_mainFrameMargin,
    #     )
    #     [i.show() for i in self.sim3_ui.widgetList]

    #     self.update_position()

    # def make_simul_page2(self) -> None:
    #     """
    #     시뮬레이션 - 시뮬레이터 페이지 생성
    #     """

    #     # 입력값 체크
    #     if not all(self.shared_data.is_input_valid.values()):
    #         self.master.get_popup_manager().make_notice_popup("SimInputError")
    #         return

    #     self.remove_simul_widgets()
    #     self.sim_update_nav_button(1)

    #     self.shared_data.sim_page_type = 2

    #     self.sim2_ui = Sim2UI(self.main_frame, self.shared_data)

    #     # 메인 프레임 크기 조정
    #     self.main_frame.setFixedHeight(
    #         self.sim2_ui.analysis_frame.y()
    #         + self.sim2_ui.analysis_frame.height()
    #         + self.ui_var.sim_mainFrameMargin
    #     )
    #     # [i.show() for i in self.parent.findChildren(QWidget)]

    #     self.update_position()

    # def make_simul_page1(self) -> None:
    #     """
    #     시뮬레이션 - 정보 입력 페이지 생성
    #     """

    #     self.remove_simul_widgets()
    #     self.sim_update_nav_button(0)

    #     self.shared_data.sim_page_type = 1

    #     self.sim1_ui = Sim1UI(self.main_frame, self.shared_data)

    #     # 메인 프레임 크기 조정
    #     self.main_frame.setFixedHeight(
    #         self.sim1_ui.infos.y()
    #         + self.sim1_ui.infos.height()
    #         + self.ui_var.sim_mainFrameMargin,
    #     )
    #     [i.show() for i in self.parent.findChildren(QWidget)]

    #     self.update_position()
    #     self.master.get_popup_manager().update_position()

    # def sim_update_nav_button(self, num: int) -> None:  # simul_ui로 이동
    #     """
    #     시뮬레이션 - 내비게이션 버튼 색 업데이트
    #     """

    #     border_widths = [0, 0, 0, 0]
    #     border_widths[num] = 2

    #     for i in [0, 1, 2, 3]:
    #         self.nav.buttons[i].setStyleSheet(
    #             f"""
    #             QPushButton {{
    #                 background-color: rgb(255, 255, 255); border: none; border-bottom: {border_widths[i]}px solid #9180F7;
    #             }}
    #             QPushButton:hover {{
    #                 background-color: rgb(234, 234, 234);
    #             }}
    #             """
    #         )
    ## change_layout 끝

    def change_layout(self, index: int) -> None:
        print(f"change_layout1: {self.UI2.height()=}")

        # 입력값 확인
        if index in (2, 3) and not all(self.shared_data.is_input_valid.values()):
            self.master.get_popup_manager().make_notice_popup("SimInputError")
            return

        # 네비게이션 버튼 색 변경
        self.update_nav(index)
        print(f"change_layout2: {self.UI2.height()=}")

        # 레이아웃 변경
        self.layout.setCurrentIndex(index)
        print(f"change_layout3: {self.UI2.height()=}")

        # 나중에 삭제
        self.update_position()
        print(f"change_layout4: {self.UI2.height()=}")

    def update_nav(self, index: int) -> None:
        """
        내비게이션 버튼 색 업데이트
        """

        widths: list[int] = [0] * 4

        # index에 해당하는 버튼만 색
        widths[index] = 2

        for i in range(4):
            self.nav.buttons[i].setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgb(255, 255, 255); border: none; border-bottom: {widths[i]}px solid #9180F7;
                }}
                QPushButton:hover {{
                    background-color: rgb(234, 234, 234);
                }}
                """
            )

    def update_position(self) -> None:
        print(f"{self.UI2.height()=}")
        deltaWidth: int = (self.master.width() - self.ui_var.DEFAULT_WINDOW_WIDTH) // 2

        self.nav.frame.move(self.ui_var.sim_margin + deltaWidth, self.ui_var.sim_margin)
        self.main_frame.setFixedWidth(
            self.master.width()
            - self.ui_var.scrollBarWidth
            - self.ui_var.sim_margin * 2
        )
        self.scroll_area.setFixedSize(
            self.master.width() - self.ui_var.sim_margin,
            self.master.height()
            - self.master.creator_label.height()
            - self.ui_var.sim_navHeight
            - self.ui_var.sim_margin * 2
            - self.ui_var.sim_main1_D,
        )

        if self.layout.currentIndex() == 0:
            self.UI1.stats.move(deltaWidth, 0)
            self.UI1.skills.move(
                deltaWidth,
                self.UI1.stats.y() + self.UI1.stats.height() + self.ui_var.sim_main_D,
            )
            self.UI1.condition.move(
                deltaWidth,
                self.UI1.skills.y() + self.UI1.skills.height() + self.ui_var.sim_main_D,
            )

        elif self.layout.currentIndex() == 1:
            # self.UI2.power.move(deltaWidth, 0)
            # self.UI2.analysis.move(
            #     deltaWidth,
            #     self.UI2.power.y() + self.UI2.power.height() + self.ui_var.sim_main_D,
            # )

            print(
                f"{self.UI2.power.y()=}, {self.UI2.analysis.y()=}, {self.UI2.DPM_graph.y()=}, {self.UI2.ratio_graph.y()=}, {self.UI2.dps_graph.y()=}, {self.UI2.total_graph.y()=}, {self.UI2.contribution_graph.y()=}"
            )

        elif self.layout.currentIndex() == 2:
            self.UI3.efficiency_frame.move(deltaWidth, 0)
            self.UI3.additional_frame.move(
                deltaWidth,
                self.UI3.efficiency_frame.y()
                + self.UI3.efficiency_frame.height()
                + self.ui_var.sim_main_D,
            )
            self.UI3.potential_frame.move(
                deltaWidth,
                self.UI3.additional_frame.y()
                + self.UI3.additional_frame.height()
                + self.ui_var.sim_main_D,
            )
            self.UI3.potentialRank_frame.move(
                deltaWidth,
                self.UI3.potential_frame.y()
                + self.UI3.potential_frame.height()
                + self.ui_var.sim_main_D,
            )

        elif self.layout.currentIndex() == 3:
            self.UI4.mainframe.move(deltaWidth, 0)


class Sim1UI(QFrame):
    def __init__(self, parent: QFrame, shared_data: SharedData):
        super().__init__(parent)

        self.shared_data: SharedData = shared_data
        self.ui_var: UI_Variable = UI_Variable()

        layout = QVBoxLayout(self)

        # 스텟
        self.stats_title: Title = Title(parent=self, text="캐릭터 스탯")
        self.stats = self.Stats(self, self.shared_data)

        # 스킬 입력
        self.skills_title: Title = Title(parent=self, text="스킬 레벨")
        self.skills = self.Skills(self, self.shared_data)

        # 시뮬레이션 조건 입력
        self.condition_title: Title = Title(parent=self, text="시뮬레이션 조건")
        self.condition = self.Condition(self, self.shared_data)

        # height = self.condition.y() + self.condition.height()
        # self.setGeometry(0, 0, 928, height)
        # self.setMinimumSize(928, height)

        # print(f"{self.height()=}")

        # Tab Order 설정
        tab_orders: list[CustomLineEdit] = (
            self.stats.inputs + self.skills.inputs + self.condition.inputs
        )
        for i in range(len(tab_orders) - 1):
            QWidget.setTabOrder(tab_orders[i], tab_orders[i + 1])

        layout.addWidget(self.stats_title)
        layout.addWidget(self.stats)
        layout.addWidget(self.skills_title)
        layout.addWidget(self.skills)
        layout.addWidget(self.condition_title)
        layout.addWidget(self.condition)

        self.setLayout(layout)

    class Stats(QWidget):
        def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            # 스탯 데이터 생성
            stats_data: dict[str, str] = {
                name_ko: str(self.shared_data.info_stats.get_stat_from_name(name_en))
                for name_en, name_ko in self.shared_data.STATS.items()
            }

            # 스탯 입력 위젯 생성
            self.inputs: list[CustomLineEdit] = StatInputs(
                self, stats_data, self.input_changed
            ).inputs

            # 첫 번째 입력 상자에 포커스 설정
            self.inputs[0].setFocus()

        def input_changed(self) -> None:
            # 스탯이 정상적으로 입력되었는지 확인
            def checkInput(num: int, text: str) -> bool:
                if not text.isdigit():
                    return False

                a, b = self.shared_data.STAT_RANGES[
                    list(self.shared_data.STATS.keys())[num]
                ]

                return a <= int(text) <= b

            # todo: for 1개로 변경하기
            # 모두 digit 이고 범위 내에 있으면
            if all(checkInput(i, j.text()) for i, j in enumerate(self.inputs)):
                # 통과O면 원래색
                for i in self.inputs:
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

                for i, j in enumerate(self.inputs):
                    self.shared_data.info_stats.set_stat_from_index(i, int(j.text()))

                save_data(self.shared_data)
                self.shared_data.is_input_valid["stat"] = True

                return

            # 하나라도 통과X
            for i, j in enumerate(self.inputs):
                # 통과X면 빨간색
                if not checkInput(i, j.text()):
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 2px solid {self.ui_var.sim_input_colorsRed}; border-radius: 4px; }}"
                    )

                # 통과O면 원래색
                else:
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

            self.shared_data.is_input_valid["stat"] = False

    class Skills(QWidget):
        def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var: UI_Variable = UI_Variable()

            skills_data: dict[str, int] = {
                name: self.shared_data.info_skill_levels[name]
                for name in get_available_skills(self.shared_data)
            }

            self.inputs: list[CustomLineEdit] = SkillInputs(
                self,
                self.shared_data,
                skills_data,
                self.input_changed,
            ).inputs

        def input_changed(self):
            # 스킬이 정상적으로 입력되었는지 확인
            def checkInput(text: str) -> bool:
                if not text.isdigit():
                    return False

                return 1 <= int(text) <= 30

            if all(checkInput(i.text()) for i in self.inputs):  # 모두 통과
                for i in self.inputs:  # 통과O면 원래색
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

                for i, j in enumerate(self.inputs):
                    self.shared_data.info_skill_levels[
                        get_available_skills(self.shared_data)[i]
                    ] = int(j.text())

                save_data(self.shared_data)
                self.shared_data.is_input_valid["skill"] = True

                return

            # 하나라도 통과X
            for i in self.inputs:
                if not checkInput(i.text()):  # 통과X면 빨간색
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 2px solid {self.ui_var.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

            self.shared_data.is_input_valid["skill"] = False

    class Condition(QWidget):
        def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.inputs: list[CustomLineEdit] = ConditionInputs(
                self,
                {
                    name: str(self.shared_data.info_sim_details[name])
                    for name in self.shared_data.SIM_DETAILS.keys()
                },
                self.input_changed,
            ).inputs

        def input_changed(self) -> None:
            # 스탯이 정상적으로 입력되었는지 확인
            def checkInput(num, text) -> bool:
                if not text.isdigit():
                    return False

                match num:
                    case 0 | 1:
                        return int(text) != 0
                    case _:
                        return True

            if all(
                checkInput(i, j.text()) for i, j in enumerate(self.inputs)
            ):  # 모두 통과
                for i in self.inputs:  # 통과O면 원래색
                    i.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

                for i, j in enumerate(self.inputs):
                    self.shared_data.info_sim_details[
                        list(self.shared_data.SIM_DETAILS.keys())[i]
                    ] = int(j.text())

                save_data(self.shared_data)
                self.shared_data.is_input_valid["simInfo"] = True

                return

            # 하나라도 통과X
            for i, j in enumerate(self.inputs):
                if not checkInput(i, j.text()):  # 통과X면 빨간색
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 2px solid {self.ui_var.sim_input_colorsRed}; border-radius: 4px; }}"
                    )
                else:
                    j.setStyleSheet(
                        f"QLineEdit {{ background-color: {self.ui_var.sim_input_colors[0]}; border: 1px solid {self.ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
                    )

            self.shared_data.is_input_valid["simInfo"] = False


class Sim2UI(QFrame):
    class Power(QFrame):
        def __init__(
            self, parent: QFrame, shared_data: SharedData, str_powers: list[str]
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.setGeometry(
                0,
                0,
                928,
                self.ui_var.sim_title_H
                + (self.ui_var.sim_widget_D + self.ui_var.sim_powerL_frame_H),
            )
            self.setStyleSheet(
                "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
            )

            self.title: Title = Title(self, "전투력")
            self.label = PowerLabels(self, self.shared_data, str_powers)

            for i, (frame, label, number) in enumerate(
                zip(self.label.frames, self.label.labels, self.label.numbers)
            ):
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

    class Analysis(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            power: Sim2UI.Power,
            analysis: list[SimAnalysis],
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.setGeometry(
                0,
                power.y() + power.height() + self.ui_var.sim_main_D,
                928,
                self.ui_var.sim_widget_D + self.ui_var.sim_analysis_frame_H,
            )
            self.setStyleSheet(
                "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
            )

            self.title: Title = Title(self, "분석")
            self.details: list[AnalysisDetails] = [
                AnalysisDetails(
                    self,
                    analysis[i],
                    self.shared_data.POWER_DETAILS,
                )
                for i in range(4)
            ]

            for i, detail in enumerate(self.details):
                detail.frame.setGeometry(
                    self.ui_var.sim_analysis_margin
                    + (self.ui_var.sim_analysis_width + self.ui_var.sim_analysis_D) * i,
                    self.ui_var.sim_label_H + self.ui_var.sim_widget_D,
                    self.ui_var.sim_analysis_width,
                    self.ui_var.sim_analysis_frame_H,
                )
                detail.color.setStyleSheet(
                    f"QFrame {{ background-color: rgb({self.ui_var.sim_colors4[i]}); border: 0px solid; border-radius: 0px; border-bottom: 1px solid #CCCCCC; border-left: 1px solid #CCCCCC; border-top: 1px solid #CCCCCC; }}"
                )

    class DPMGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            analysis: Sim2UI.Analysis,
            results: list[list[SimAttack]],
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.setGeometry(
                self.ui_var.sim_dps_margin,
                analysis.y() + analysis.height() + self.ui_var.sim_main_D,
                self.ui_var.sim_dps_width,
                self.ui_var.sim_dps_height,
            )
            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            sums_for_results: list[float] = [
                sum([i.damage for i in result]) for result in results
            ]

            self.graph = DpmDistributionCanvas(self, sums_for_results)
            self.graph.move(5, 5)
            self.graph.resize(
                self.ui_var.sim_dps_width - 10, self.ui_var.sim_dps_height - 10
            )

    class RatioGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            analysis: Sim2UI.Analysis,
            resultDet: list[SimAttack],
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.setGeometry(
                self.ui_var.sim_dps_margin
                + self.ui_var.sim_dps_width
                + self.ui_var.sim_skillDps_margin,
                analysis.y() + analysis.height() + self.ui_var.sim_widget_D,
                self.ui_var.sim_skillRatio_width,
                self.ui_var.sim_skillRatio_height,
            )
            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            ratio_data: list[float] = [
                sum(
                    skill.damage
                    for skill in resultDet
                    if skill.skill_name == skill_name
                )
                for skill_name in self.shared_data.equipped_skills + ["평타"]
            ]
            # data = [round(total_dmgs[i] / sum(total_dmgs) * 100, 1) for i in range(7)]

            self.graph = SkillDpsRatioCanvas(
                self, ratio_data, self.shared_data.equipped_skills
            )
            self.graph.move(10, 10)
            self.graph.resize(
                self.ui_var.sim_skillRatio_width - 20,
                self.ui_var.sim_skillRatio_height - 20,
            )

    class DPSGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            distribution: Sim2UI.DPMGraph,
            results: list[list[SimAttack]],
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.setGeometry(
                self.ui_var.sim_dps_margin,
                distribution.y() + distribution.height() + self.ui_var.sim_main_D,
                self.ui_var.sim_dmg_width,
                self.ui_var.sim_dmg_height,
            )
            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            step, count = 1, 60
            times: list[int] = [i * step for i in range(count + 1)]

            dmg_sec_for_results: list[list[float]] = [
                [0.0]
                + [
                    sum(
                        [
                            j.damage
                            for j in result
                            if i * step <= j.time < (i + 1) * step
                        ]
                    )
                    for i in range(count)
                ]
                for result in results
            ]

            data = {
                "time": times,
                "max": [
                    max([j[i] for j in dmg_sec_for_results]) for i in range(count + 1)
                ],
                "mean": [
                    sum([j[i] for j in dmg_sec_for_results]) / len(dmg_sec_for_results)
                    for i in range(count + 1)
                ],
                "min": [
                    min([j[i] for j in dmg_sec_for_results]) for i in range(count + 1)
                ],
            }

            self.graph = DMGCanvas(self, data, "시간 경과에 따른 피해량")
            self.graph.move(5, 5)
            self.graph.resize(
                self.ui_var.sim_dmg_width - 10, self.ui_var.sim_dmg_height - 10
            )

    class TotalGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            dps_graph: Sim2UI.DPSGraph,
            results: list[list[SimAttack]],
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.setGeometry(
                self.ui_var.sim_dps_margin,
                dps_graph.y() + dps_graph.height() + self.ui_var.sim_main_D,
                self.ui_var.sim_dmg_width,
                self.ui_var.sim_dmg_height,
            )
            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            step, count = 1, 60
            times: list[int] = [i * step for i in range(count + 1)]

            dmg_sec_for_results: list[list[float]] = [
                [0.0]
                + [
                    sum(
                        [
                            j.damage
                            for j in result
                            if i * step <= j.time < (i + 1) * step
                        ]
                    )
                    for i in range(count)
                ]
                for result in results
            ]

            total_list: list[list[float]] = [
                [sum([j for j in dmg_sec[: i + 1]]) for i in range(count + 1)]
                for dmg_sec in dmg_sec_for_results
            ]

            data = {
                "time": times,
                "max": [max([j[i] for j in total_list]) for i in range(count + 1)],
                "mean": [
                    sum([j[i] for j in total_list]) / len(total_list)
                    for i in range(count + 1)
                ],
                "min": [min([j[i] for j in total_list]) for i in range(count + 1)],
            }

            self.graph = DMGCanvas(self, data, "누적 피해량")
            self.graph.move(5, 5)
            self.graph.resize(
                self.ui_var.sim_dmg_width - 10, self.ui_var.sim_dmg_height - 10
            )

    class ContributionGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            cumulative_graph: Sim2UI.TotalGraph,
            resultDet: list[SimAttack],
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.setGeometry(
                self.ui_var.sim_dps_margin,
                cumulative_graph.y()
                + cumulative_graph.height()
                + self.ui_var.sim_main_D,
                self.ui_var.sim_dmg_width,
                self.ui_var.sim_dmg_height,
            )
            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            step, count = 1, 60
            times: list[int] = [i * step for i in range(count + 1)]

            skillsData: list[list[float]] = [
                [0.0]
                + [
                    sum(
                        [
                            j.damage
                            for j in resultDet
                            if j.skill_name == skill_name and j.time < (i + 1) * step
                        ]
                    )
                    for i in range(count)
                ]
                for skill_name in self.shared_data.equipped_skills + ["평타"]
            ]

            # totalData = []
            # for i in range(timeStepCount):
            #     totalData.append(sum([j[2] for j in resultDet if j[1] < (i + 1) * timeStep]))
            totalData: list[float] = [0.0] + [
                sum([j.damage for j in resultDet if j.time < (i + 1) * step])
                for i in range(count)
            ]

            # data_normalized = []
            # for i in range(7):
            #     data_normalized.append([skillsData[i][j] / totalData[j] for j in range(timeStepCount)])
            data_normalized: list[list[float]] = [
                [0.0] + [skillsData[i][j] / totalData[j] for j in range(1, count + 1)]
                for i in range(7)
            ]

            data_cumsum: list[list[float]] = [
                [0.0 for _ in row] for row in data_normalized
            ]
            for i in range(len(data_normalized)):
                for j in range(len(data_normalized[0])):
                    data_cumsum[i][j] = sum(row[j] for row in data_normalized[: i + 1])

            data = {
                "time": times,
                "data": data_normalized,
            }
            self.graph = SkillContributionCanvas(
                self, data, self.shared_data.equipped_skills.copy()
            )
            self.graph.move(20, 20)
            self.graph.resize(
                self.ui_var.sim_dmg_width - 40,
                self.ui_var.sim_dmg_height - 40,
            )

    def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
        super().__init__(parent)

        self.shared_data: SharedData = shared_data
        self.ui_var = UI_Variable()

        # 처음 생성때는 계산하지 않기
        sim_result: SimResult = randSimulate(
            self.shared_data,
            self.shared_data.info_stats,
            self.shared_data.info_sim_details,
        )
        powers: list[float] = sim_result.powers
        analysis: list[SimAnalysis] = sim_result.analysis
        resultDet: list[SimAttack] = sim_result.deterministic_boss_attacks
        results: list[list[SimAttack]] = sim_result.random_boss_attacks
        str_powers: list[str] = sim_result.str_powers

        for i, power in enumerate(powers):
            self.shared_data.powers[i] = power

        # 전투력
        self.power: Sim2UI.Power = self.Power(self, self.shared_data, str_powers)

        # 분석
        self.analysis: Sim2UI.Analysis = self.Analysis(
            self, self.shared_data, self.power, analysis
        )

        # DPM 분포
        self.DPM_graph: Sim2UI.DPMGraph = self.DPMGraph(
            self, self.shared_data, self.analysis, results
        )

        # 스킬 비율
        self.ratio_graph: Sim2UI.RatioGraph = self.RatioGraph(
            self, self.shared_data, self.analysis, resultDet
        )

        # 시간 경과에 따른 피해량
        self.dps_graph: Sim2UI.DPSGraph = self.DPSGraph(
            self, self.shared_data, self.DPM_graph, results
        )

        # 누적 피해량
        self.total_graph: Sim2UI.TotalGraph = self.TotalGraph(
            self, self.shared_data, self.dps_graph, results
        )

        # 스킬별 누적 기여도
        self.contribution_graph: Sim2UI.ContributionGraph = self.ContributionGraph(
            self, self.shared_data, self.total_graph, resultDet
        )

        height = self.contribution_graph.y() + self.contribution_graph.height()
        self.setGeometry(0, 0, 928, height)
        self.setMinimumSize(928, height)

        # print(
        #     f"{self.power.y()=}, {self.analysis.y()=}, {self.DPM_graph.y()=}, {self.ratio_graph.y()=}, {self.dps_graph.y()=}, {self.total_graph.y()=}, {self.contribution_graph.y()=}"
        # )

        # def temp():
        #     while True:
        #         print(f"{self.height()=}")

        # threading.Thread(target=temp, daemon=True).start()


class Sim3UI(QFrame):
    class Efficiency(QFrame):
        def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            self.setGeometry(
                0,
                0,
                928,
                self.ui_var.sim_title_H
                + (self.ui_var.sim_widget_D + self.ui_var.sim_efficiency_frame_H),
            )
            self.setStyleSheet(
                "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
            )

            self.title: Title = Title(self, "스펙업 효율 계산기")

            # 왼쪽 콤보박스
            self.combobox_L = CustomComboBox(
                self,
                list(self.shared_data.STATS.values()),
                self.efficiency_Changed,
            )
            self.combobox_L.setGeometry(
                self.ui_var.sim_efficiency_statL_margin,
                self.ui_var.sim_label_H
                + self.ui_var.sim_widget_D
                + self.ui_var.sim_efficiency_statL_y,
                self.ui_var.sim_efficiency_statL_W,
                self.ui_var.sim_efficiency_statL_H,
            )

            # 왼쪽 스탯 입력창
            self.efficiency_statInput = CustomLineEdit(
                self, self.efficiency_Changed, "10"
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
                QPixmap(
                    convert_resource_path("resources\\image\\lineArrow.png")
                ).scaled(
                    self.ui_var.sim_efficiency_arrow_W,
                    self.ui_var.sim_efficiency_arrow_H,
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

    def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
        super().__init__(parent)

        self.shared_data: SharedData = shared_data
        self.ui_var = UI_Variable()

        # 계산
        powers: list[float] = detSimulate(
            self.shared_data,
            self.shared_data.info_stats,
            self.shared_data.info_sim_details,
        ).powers

        # 저장
        for i, power in enumerate(powers):
            self.shared_data.powers[i] = power

        # 레이아웃 시스템으로 변경할 때 제거
        self.widgetList = []

        # ???
        self.shared_data.is_input_valid["stat"] = False
        self.shared_data.is_input_valid["skill"] = False

        ## 스펙업 효율 계산기
        self.efficiency = self.Efficiency()

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

        self.additional_stats = StatInputs(
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

        self.additional_skills = SkillInputs(
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


class StatInputs(QWidget):
    def __init__(
        self, mainframe: QWidget, stats_data: dict[str, str], connected_function
    ):
        super().__init__(mainframe)

        # 그리드 레이아웃 위젯 생성
        grid_layout = QGridLayout(self)

        # 아이템을 저장할 리스트
        self.inputs: list[CustomLineEdit] = []

        # column 수 설정
        # 서버가 많아지면 스탯 개수에 따라 자동으로 조절하는 기능 추가 필요
        # QVBoxLayout에 각 행마다 QHBoxLayout을 추가하는 방식
        COLS = 6
        for i, (name, value) in enumerate(stats_data.items()):
            item_widget = KVInput(self, name, value, connected_function, float)

            # 위치 계산
            row: int = i // COLS
            column: int = i % COLS

            # 그리드에 추가
            grid_layout.addWidget(item_widget, row, column)

            # 아이템 위젯을 리스트에 저장
            self.inputs.append(item_widget.input)

        # 그리드 레이아웃 간격 설정
        grid_layout.setVerticalSpacing(10)
        grid_layout.setHorizontalSpacing(20)


class SkillInputs(QWidget):
    class SkillInput(QWidget):
        def __init__(
            self,
            parent,
            shared_data: SharedData,
            name: str,
            value: int,
            connected_function=None,
        ):
            super().__init__(parent)

            ui_var = UI_Variable()

            # 전체 layout 설정
            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)

            # 레이블
            label = QLabel(name, self)
            label.setStyleSheet(f"QLabel {{ border: 0px solid; border-radius: 4px; }}")
            label.setFont(CustomFont(14))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 스킬 이미지
            image = SkillImage(
                self,
                get_skill_pixmap(
                    shared_data,
                    name,
                ),
                ui_var.sim_skill_image_Size,
            )

            # 레벨 입력
            level_input = KVInput(
                self,
                "레벨",
                str(value),
                connected_function=connected_function,
                expected_type=int,
            )

            # 탭 순서를 설정하기 위해 외부에서 접근 가능하도록 설정
            self.input: CustomLineEdit = level_input.input

            # layout에 추가
            grid.addWidget(label, 0, 0, 2, 1)
            grid.addWidget(image, 1, 0)
            grid.addWidget(level_input, 1, 1)

            # layout 설정
            self.setLayout(grid)

    def __init__(
        self,
        mainframe: QWidget,
        shared_data: SharedData,
        skills_data: dict[str, int],
        connected_function,
    ):
        super().__init__(mainframe)

        # 그리드 레이아웃 위젯 생성
        grid_layout = QGridLayout(self)

        # 아이템을 저장할 리스트
        self.inputs: list[CustomLineEdit] = []

        # column 수 설정
        COLS = 7
        for i, (name, value) in enumerate(skills_data.items()):
            item_widget = self.SkillInput(
                self, shared_data, name, value, connected_function
            )

            # 위치 계산
            row: int = i // COLS
            column: int = i % COLS

            # 그리드에 추가
            grid_layout.addWidget(item_widget, row, column)

            # 아이템 위젯을 리스트에 저장
            self.inputs.append(item_widget.input)

        # 그리드 레이아웃 간격 설정
        grid_layout.setVerticalSpacing(10)
        grid_layout.setHorizontalSpacing(20)


class ConditionInputs(QWidget):
    def __init__(
        self, mainframe: QWidget, stats_data: dict[str, str], connected_function
    ):
        super().__init__(mainframe)

        # 그리드 레이아웃 위젯 생성
        grid_layout = QGridLayout(self)

        # 아이템을 저장할 리스트
        self.inputs: list[CustomLineEdit] = []

        # column 수 설정
        COLS = 6
        for i, (name, value) in enumerate(stats_data.items()):
            # 위젯 생성
            item_widget = KVInput(self, name, value, connected_function, int)

            # 위치 계산
            # 시뮬 조건 항목이 많아지면 스탯 입력과 같이 조절 필요
            row: int = i // COLS
            column: int = i % COLS

            # 그리드에 추가
            grid_layout.addWidget(item_widget, row, column)

            # 아이템 위젯을 리스트에 저장
            self.inputs.append(item_widget.input)

        # 그리드 레이아웃 간격 설정
        grid_layout.setVerticalSpacing(10)
        grid_layout.setHorizontalSpacing(20)


class PowerLabels:
    def __init__(self, mainframe, shared_data: SharedData, texts, font_size=18):
        ui_var = UI_Variable()

        self.frames = []
        self.labels = []
        self.numbers = []

        for i in range(4):
            frame = QFrame(mainframe)
            frame.show()

            label = QLabel(shared_data.POWER_TITLES[i], frame)
            label.setStyleSheet(
                f"QLabel {{ background-color: rgb({ui_var.sim_colors4[i]}); border: 1px solid rgb({ui_var.sim_colors4[i]}); border-bottom: 0px solid; border-top-left-radius: 4px; border-top-right-radius: 4px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; }}"
            )
            label.setFont(CustomFont(14))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.show()

            number = QLabel(texts[i], frame)
            number.setStyleSheet(
                f"QLabel {{ background-color: rgba({ui_var.sim_colors4[i]}, 120); border: 1px solid rgb({ui_var.sim_colors4[i]}); border-top: 0px solid; border-top-left-radius: 0px; border-top-right-radius: 0px; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px }}"
            )
            number.setFont(CustomFont(font_size))
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            number.show()

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
        self.frame.show()

        self.color = QFrame(self.frame)
        self.color.setGeometry(
            0,
            0,
            ui_var.sim_analysis_color_W,
            ui_var.sim_analysis_frame_H,
        )
        self.color.show()

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
        self.title.show()

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
        self.number.show()

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
            detail_frame.show()

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
            detail_title.show()

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
            detail_number.show()

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


class Title(QLabel):
    def __init__(self, parent, text):
        super().__init__(text, parent)
        self.setStyleSheet(
            "QLabel { background-color: rgb(255, 255, 255); border: none; border-bottom: 1px solid #bbbbbb; }"
        )
        self.setFont(CustomFont(16))


class Navigation:
    class NavButton(QPushButton):
        def __init__(self, text, parent, i, border_width):
            ui_var = UI_Variable()

            super().__init__(text, parent)

            self.setGeometry(
                ui_var.sim_navBWidth * i,
                0,
                ui_var.sim_navBWidth,
                ui_var.sim_navHeight,
            )
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgb(255, 255, 255); border: none; border-bottom: {border_width}px solid #9180F7; 
                }}
                QPushButton:hover {{
                    background-color: rgb(234, 234, 234);
                }}
                """
            )
            self.setFont(CustomFont(12))

    def __init__(self, parent):
        ui_var = UI_Variable()

        # 상단 네비게이션바
        self.frame: QFrame = QFrame(parent)
        self.frame.setGeometry(
            ui_var.sim_margin,
            ui_var.sim_margin,
            ui_var.DEFAULT_WINDOW_WIDTH - ui_var.sim_margin * 2,
            ui_var.sim_navHeight,
        )
        self.frame.setStyleSheet("QFrame { background-color: rgb(255, 255, 255); }")

        # 네비게이션바 텍스트
        nav_texts: list[str] = ["정보 입력", "시뮬레이터", "스탯 계산기", "캐릭터 카드"]
        border_widths: list[int] = [2, 0, 0, 0]

        self.buttons: list[QPushButton] = [
            Navigation.NavButton(nav_texts[i], self.frame, i, border_widths[i])
            for i in range(4)
        ]

        # 닫기 버튼
        button: QPushButton = QPushButton(self.frame)
        button.setGeometry(
            890,
            0,
            ui_var.sim_navHeight,
            ui_var.sim_navHeight,
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

        self.buttons.append(button)
