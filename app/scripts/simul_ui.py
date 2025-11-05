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
from .config import config

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
    QHBoxLayout,
    QSizePolicy,
    QGridLayout,
)

from collections.abc import Callable


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

        self.nav: Navigation = Navigation(
            self.parent, self.change_layout, self.master.change_layout
        )

        # 메인 프레임
        self.main_frame: QFrame = QFrame(self.parent)

        if config.ui.debug_colors:
            self.main_frame.setStyleSheet(
                "QFrame { background-color: rgb(255, 0, 0); border: 0px solid; }"
            )
        else:
            self.main_frame.setStyleSheet(
                "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
            )

        self.main_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        # 스크롤바
        self.scroll_area: QScrollArea = QScrollArea(self.parent)
        self.scroll_area.setWidget(self.main_frame)
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
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.show()

        # page2 레이아웃 설정
        layout = QVBoxLayout(self.parent)
        layout.addWidget(self.nav)
        layout.addWidget(self.scroll_area)
        self.parent.setLayout(layout)

        # 페이지 레이아웃 설정
        self.stacked_layout = QStackedLayout(self.main_frame)

        self.UI1 = Sim1UI(self.main_frame, self.shared_data)
        self.UI2 = Sim2UI(self.main_frame, self.shared_data)
        # self.UI3 = Sim3UI(self.main_frame, self.shared_data)
        # self.UI4 = Sim4UI(self.main_frame, self.shared_data)
        self.stacked_layout.addWidget(self.UI1)
        self.stacked_layout.addWidget(self.UI2)

        self.stacked_layout.setCurrentIndex(0)
        # 스택 레이아웃 설정
        self.main_frame.setLayout(self.stacked_layout)

    def change_layout(self, index: int) -> None:
        # 입력값 확인
        if index in (2, 3) and not all(self.shared_data.is_input_valid.values()):
            self.master.get_popup_manager().make_notice_popup("SimInputError")

            return

        # 네비게이션 버튼 색 변경
        self.update_nav(index)

        # 레이아웃 변경
        self.stacked_layout.setCurrentIndex(index)

    def update_nav(self, index: int) -> None:
        """
        내비게이션 버튼 색 업데이트
        """

        # index에 해당하는 버튼만 색
        border_color: dict[bool, str] = {True: "#9180F7", False: "#FFFFFF"}

        for i in range(4):
            self.nav.buttons[i].setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgb(255, 255, 255); border: none; border-bottom: 2px solid {border_color[i == index]};
                }}
                QPushButton:hover {{
                    background-color: rgb(234, 234, 234);
                }}
                """
            )


class Sim1UI(QFrame):
    def __init__(self, parent: QFrame, shared_data: SharedData):
        super().__init__(parent)

        self.shared_data: SharedData = shared_data

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: gray;}")

        # 스텟
        self.stats_title: Title = Title(parent=self, text="캐릭터 스탯")
        self.stats = self.Stats(self, self.shared_data)

        # 스킬 입력
        self.skills_title: Title = Title(parent=self, text="스킬 레벨")
        self.skills = self.Skills(self, self.shared_data)

        # 시뮬레이션 조건 입력
        self.condition_title: Title = Title(parent=self, text="시뮬레이션 조건")
        self.condition = self.Condition(self, self.shared_data)

        # Tab Order 설정
        tab_orders: list[CustomLineEdit] = (
            self.stats.inputs + self.skills.inputs + self.condition.inputs
        )
        for i in range(len(tab_orders) - 1):
            QWidget.setTabOrder(tab_orders[i], tab_orders[i + 1])

        layout = QVBoxLayout(self)

        layout.addWidget(self.stats_title)
        layout.addWidget(self.stats)
        layout.addWidget(self.skills_title)
        layout.addWidget(self.skills)
        layout.addWidget(self.condition_title)
        layout.addWidget(self.condition)

        # 레이아웃 여백과 간격 설정
        layout.setSpacing(10)  # 위젯들 사이의 간격
        layout.setContentsMargins(10, 10, 10, 10)  # 레이아웃의 여백
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

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
            self.stat_inputs = StatInputs(self, stats_data, self.input_changed)
            self.inputs: list[CustomLineEdit] = self.stat_inputs.inputs

            # 레이아웃 설정
            layout = QVBoxLayout(self)
            layout.addWidget(self.stat_inputs)
            layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
            layout.setSpacing(0)  # 위젯 간 간격 제거
            self.setLayout(layout)

            # 크기 정책: 가로는 부모 크기 최대, 세로는 내용에 맞게 최소
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            # 첫 번째 입력 상자에 포커스 설정
            self.inputs[0].setFocus()

        def input_changed(self) -> None:
            # 정상적으로 입력되었는지 확인
            def checkInput(num: int, text: str) -> bool:
                if not text.isdigit():
                    return False

                a, b = self.shared_data.STAT_RANGES[
                    list(self.shared_data.STATS.keys())[num]
                ]

                return a <= int(text) <= b

            # 모두 통과 여부 확인
            all_valid = True
            for i, j in enumerate(self.inputs):
                is_valid: bool = checkInput(i, j.text())

                # 스타일 업데이트
                j.set_valid(is_valid)

                # 전체 유효 여부 업데이트
                all_valid: bool = all_valid and is_valid

            # 모두 통과했다면 저장 및 플래그 설정
            if all_valid:
                save_data(self.shared_data)
                self.shared_data.is_input_valid["stat"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
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

            # 스킬 입력 위젯 생성
            self.skill_inputs = SkillInputs(
                self,
                self.shared_data,
                skills_data,
                self.input_changed,
            )
            self.inputs: list[CustomLineEdit] = self.skill_inputs.inputs

            # 레이아웃 설정
            layout = QVBoxLayout(self)
            layout.addWidget(self.skill_inputs)
            layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
            layout.setSpacing(0)  # 위젯 간 간격 제거
            self.setLayout(layout)

            # 크기 정책: 가로는 부모 크기 최대, 세로는 내용에 맞게 최소
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        def input_changed(self) -> None:
            # 정상적으로 입력되었는지 확인
            def checkInput(text: str) -> bool:
                if not text.isdigit():
                    return False

                return 1 <= int(text) <= 30

            # 모두 통과 여부 확인
            all_valid = True
            for j in self.inputs:
                is_valid: bool = checkInput(j.text())

                # 스타일 업데이트
                j.set_valid(is_valid)

                # 전체 유효 여부 업데이트
                all_valid: bool = all_valid and is_valid

            # 모두 통과했다면 저장 및 플래그 설정
            if all_valid:
                save_data(self.shared_data)
                self.shared_data.is_input_valid["skill"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                self.shared_data.is_input_valid["skill"] = False

    class Condition(QWidget):
        def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            # 시뮬레이션 조건 입력 위젯 생성
            self.condition_inputs = ConditionInputs(
                self,
                {
                    name: str(self.shared_data.info_sim_details[name])
                    for name in self.shared_data.SIM_DETAILS.keys()
                },
                self.input_changed,
            )
            self.inputs: list[CustomLineEdit] = self.condition_inputs.inputs

            # 레이아웃 설정
            layout = QVBoxLayout(self)
            layout.addWidget(self.condition_inputs)
            layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
            layout.setSpacing(0)  # 위젯 간 간격 제거
            self.setLayout(layout)

            # 크기 정책: 가로는 부모 크기 최대, 세로는 내용에 맞게 최소
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        def input_changed(self) -> None:
            # 정상적으로 입력되었는지 확인
            def checkInput(num, text) -> bool:
                if not text.isdigit():
                    return False

                match num:
                    case 0 | 1:
                        return int(text) != 0
                    case _:
                        return True

            # 모두 통과 여부 확인
            all_valid = True
            for i, j in enumerate(self.inputs):
                is_valid: bool = checkInput(i, j.text())

                # 스타일 업데이트
                j.set_valid(is_valid)

                # 전체 유효 여부 업데이트
                all_valid: bool = all_valid and is_valid

            # 모두 통과했다면 저장 및 플래그 설정
            if all_valid:
                save_data(self.shared_data)
                self.shared_data.is_input_valid["simInfo"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                self.shared_data.is_input_valid["simInfo"] = False


class Sim2UI(QFrame):
    def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
        super().__init__(parent)

        self.shared_data: SharedData = shared_data
        self.ui_var = UI_Variable()

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: gray;}")

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
        self.power_title: Title = Title(self, "전투력")
        self.power = PowerLabels(self, self.shared_data, str_powers)

        # 분석
        self.analysis_title: Title = Title(self, "분석")
        self.analysis = AnalysisDetails(self, self.shared_data, analysis)

        # DPM 분포
        self.DPM_graph = self.DPMGraph(self, results)

        # 스킬 비율
        self.ratio_graph = self.RatioGraph(self, self.shared_data, resultDet)

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(self.DPM_graph)
        sub_layout.addWidget(self.ratio_graph)
        sub_layout.setSpacing(10)
        sub_layout.setContentsMargins(10, 10, 10, 10)

        # 시간 경과에 따른 피해량
        self.dps_graph = self.DPSGraph(self, results)

        # 누적 피해량
        self.total_graph = self.TotalGraph(self, self.shared_data, results)

        # 스킬별 누적 기여도
        self.contribution_graph = self.ContributionGraph(
            self, self.shared_data, resultDet
        )

        layout = QVBoxLayout(self)

        layout.addWidget(self.power_title)
        layout.addWidget(self.power)
        layout.addWidget(self.analysis_title)
        layout.addWidget(self.analysis)
        layout.addLayout(sub_layout)
        layout.addWidget(self.dps_graph)
        layout.addWidget(self.total_graph)
        layout.addWidget(self.contribution_graph)

        # 레이아웃 여백과 간격 설정
        layout.setSpacing(10)  # 위젯들 사이의 간격
        layout.setContentsMargins(10, 10, 10, 10)  # 레이아웃의 여백
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    class DPMGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            results: list[list[SimAttack]],
        ) -> None:
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = DpmDistributionCanvas(self, results)
            self.graph.setFixedHeight(300)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(self.graph)
            self.setLayout(layout)

    class RatioGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            resultDet: list[SimAttack],
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = SkillDpsRatioCanvas(
                self, resultDet, self.shared_data.equipped_skills
            )
            self.graph.setFixedHeight(300)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(self.graph)
            self.setLayout(layout)

    class DPSGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            results: list[list[SimAttack]],
        ) -> None:
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = DMGCanvas(self, results, "시간 경과에 따른 피해량")
            self.graph.setFixedHeight(400)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(self.graph)
            self.setLayout(layout)

    class TotalGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            results: list[list[SimAttack]],
        ) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = DMGCanvas(self, results, "누적 피해량")
            self.graph.setFixedHeight(400)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(self.graph)
            self.setLayout(layout)

    class ContributionGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            shared_data: SharedData,
            resultDet: list[SimAttack],
        ) -> None:
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = SkillContributionCanvas(
                self, resultDet, shared_data.equipped_skills.copy()
            )
            self.graph.setFixedHeight(400)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(self.graph)
            self.setLayout(layout)


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


class StatInputs(QFrame):
    def __init__(
        self, mainframe: QWidget, stats_data: dict[str, str], connected_function
    ):
        super().__init__(mainframe)

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: green; border: 0px solid; }")

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

        # 레이아웃 설정
        self.setLayout(grid_layout)

        # 크기 정책: 가로는 부모 크기 최대, 세로는 내용에 맞게 최소
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)


class SkillInputs(QFrame):
    class SkillInput(QFrame):
        def __init__(
            self,
            parent,
            shared_data: SharedData,
            name: str,
            value: int,
            connected_function=None,
        ):
            super().__init__(parent)

            if config.ui.debug_colors:
                self.setStyleSheet(
                    "QFrame { background-color: orange; border: 0px solid; }"
                )

            # 전체 layout 설정
            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)

            # 레이블
            label = QLabel(name, self)
            label.setStyleSheet(f"QLabel {{ border: 0px solid; border-radius: 4px; }}")
            label.setFont(CustomFont(14))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 레벨 입력
            level_input = KVInput(
                self,
                "레벨",
                str(value),
                connected_function=connected_function,
                expected_type=int,
                max_width=40,
            )

            # 스킬 이미지
            icon_size: int = level_input.sizeHint().height()
            image = SkillImage(
                self,
                get_skill_pixmap(
                    shared_data,
                    name,
                ),
                icon_size,
            )

            # 탭 순서를 설정하기 위해 외부에서 접근 가능하도록 설정
            self.input: CustomLineEdit = level_input.input

            # layout에 추가
            grid.addWidget(label, 0, 0, 1, 2)
            grid.addWidget(image, 1, 0)
            grid.addWidget(level_input, 1, 1)

            # 위젯 사이 간격 설정
            grid.setVerticalSpacing(10)
            grid.setHorizontalSpacing(5)

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

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: green; border: 0px solid; }")

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

        # 레이아웃 설정
        self.setLayout(grid_layout)

        # 크기 정책: 가로는 부모 크기 최대, 세로는 내용에 맞게 최소
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)


class ConditionInputs(QFrame):
    def __init__(
        self, mainframe: QWidget, stats_data: dict[str, str], connected_function
    ):
        super().__init__(mainframe)

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: green; border: 0px solid; }")

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

        # 레이아웃 설정
        self.setLayout(grid_layout)

        # 크기 정책: 가로는 부모 크기 최대, 세로는 내용에 맞게 최소
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)


class PowerLabels(QFrame):
    def __init__(self, mainframe, shared_data: SharedData, texts, font_size=18):
        super().__init__(mainframe)

        if config.ui.debug_colors:
            self.setStyleSheet(
                "QFrame { background-color: purple; border: 0px solid; }"
            )
        else:
            self.setStyleSheet("QFrame { background-color: white; border: 0px solid; }")

        ui_var = UI_Variable()

        # 레이아웃 설정
        layout = QHBoxLayout(self)

        # 전투력 라벨 추가
        for i in range(4):
            power = self.Power(
                self,
                shared_data.POWER_TITLES[i],
                texts[i],
                ui_var.sim_colors4[i],
                font_size,
            )

            layout.addWidget(power)

        # 레이아웃 여백과 간격 설정
        layout.setSpacing(10)  # 위젯들 사이의 간격
        layout.setContentsMargins(10, 10, 10, 10)  # 레이아웃의 여백
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    class Power(QFrame):
        def __init__(self, mainframe, name: str, text, color: str, font_size=18):
            super().__init__(mainframe)

            label = QLabel(name, self)
            label.setStyleSheet(
                f"QLabel {{ background-color: rgb({color}); border: 1px solid rgb({color}); border-bottom: 0px solid; border-top-left-radius: 4px; border-top-right-radius: 4px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; }}"
            )
            label.setFont(CustomFont(14))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedHeight(50)

            self.number = QLabel(text, self)
            self.number.setStyleSheet(
                f"QLabel {{ background-color: rgba({color}, 120); border: 1px solid rgb({color}); border-top: 0px solid; border-top-left-radius: 0px; border-top-right-radius: 0px; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px }}"
            )
            self.number.setFont(CustomFont(font_size))
            self.number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.number.setFixedHeight(90)

            layout = QVBoxLayout(self)
            layout.addWidget(label)
            layout.addWidget(self.number)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class AnalysisDetails(QFrame):
    def __init__(self, mainframe, shared_data: SharedData, analysis: list[SimAnalysis]):
        super().__init__(mainframe)

        ui_var = UI_Variable()

        if config.ui.debug_colors:
            self.setStyleSheet(
                "QFrame { background-color: brown; border: 1px solid #CCCCCC; border-top-left-radius: 0px; border-top-right-radius: 6px; border-bottom-left-radius: 0px; border-bottom-right-radius: 6px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px solid; }"
            )

        self.details: list[AnalysisDetails.Analysis] = [
            self.Analysis(
                self,
                analysis[i],
                shared_data.POWER_DETAILS,
                ui_var.sim_colors4[i],
            )
            for i in range(4)
        ]

        layout = QHBoxLayout(self)
        for detail in self.details:
            layout.addWidget(detail)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    class Analysis(QFrame):
        def __init__(
            self,
            parent: QFrame,
            analysis: SimAnalysis,
            statistics: list[str],
            color: str,
        ) -> None:
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-left: 0px solid; border-top-left-radius: 0px; border-top-right-radius: 6px; border-bottom-left-radius: 0px; border-bottom-right-radius: 6px; }"
            )

            color_frame = QFrame(self)
            color_frame.setStyleSheet(
                f"QFrame {{ background-color: rgb({color}); border: 0px solid; border-radius: 0px; border-left: 1px solid #CCCCCC; }}"
            )
            color_frame.setFixedWidth(3)

            title = QLabel(analysis.title, self)
            title.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            title.setFont(CustomFont(14))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.number = QLabel(analysis.value, self)
            self.number.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            self.number.setFont(CustomFont(18))
            self.number.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.statistics: list[AnalysisDetails.Statistic] = []
            for stat in statistics:
                value: str = analysis.get_data_from_str(stat)
                detail = AnalysisDetails.Statistic(self, stat, value)

                self.statistics.append(detail)

            statistics_layout = QGridLayout()
            for i, stat in enumerate(self.statistics):
                row: int = i // 3
                column: int = i % 3
                statistics_layout.addWidget(stat, row, column)
            statistics_layout.setContentsMargins(5, 5, 5, 5)
            statistics_layout.setSpacing(5)

            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(0, 5, 0, 0)
            content_layout.addWidget(title)
            content_layout.addWidget(self.number)
            content_layout.addLayout(statistics_layout)
            content_layout.setSpacing(15)

            layout = QHBoxLayout(self)
            layout.addWidget(color_frame)
            layout.addLayout(content_layout)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    class Statistic(QFrame):
        def __init__(self, parent: QFrame, name: str, value: str):
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px solid; }"
            )

            title = QLabel(name, self)
            title.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; color: #A0A0A0 }"
            )
            title.setFont(CustomFont(8))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.number = QLabel(value, self)
            self.number.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )
            self.number.setFont(CustomFont(8))
            self.number.setAlignment(Qt.AlignmentFlag.AlignCenter)

            layout = QHBoxLayout(self)
            layout.addWidget(title)
            layout.addWidget(self.number)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


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
            "QLabel { background-color: rgb(255, 255, 255); border: none; border-bottom: 1px solid #bbbbbb; padding: 10px 0; }"
        )
        self.setFont(CustomFont(16))

        # 크기 정책을 설정하여 자동 크기 조절
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 텍스트 줄바꿈 허용
        # self.setWordWrap(True)


class Navigation(QFrame):
    class NavButton(QPushButton):
        def __init__(
            self, text: str, parent: QWidget, is_active, i: int, func: Callable
        ):
            super().__init__(text, parent)

            border_color: dict[bool, str] = {True: "#9180F7", False: "#FFFFFF"}

            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgb(255, 255, 255); border: none; border-bottom: 2px solid {border_color[is_active]}; 
                }}
                QPushButton:hover {{
                    background-color: rgb(234, 234, 234);
                }}
                """
            )

            self.setFont(CustomFont(12))

            # 최소 크기 설정
            self.setMinimumSize(100, 30)

            # 클릭 시 함수 연결
            self.clicked.connect(partial(func, i))

    def __init__(self, parent: QWidget, func1: Callable, func2: Callable):
        super().__init__(parent)

        # 상단 네비게이션바
        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: blue; }")

        layout = QHBoxLayout(self)

        # 네비게이션바 텍스트
        nav_texts: list[str] = ["정보 입력", "시뮬레이터", "스탯 계산기", "캐릭터 카드"]

        # 네비게이션바 버튼들
        # 첫 번째 버튼만 활성화 상태로 시작
        self.buttons: list[QPushButton] = [
            Navigation.NavButton(nav_texts[i], self, i == 0, i, func1) for i in range(4)
        ]

        # 닫기 버튼
        button: QPushButton = QPushButton(self)
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
        button.clicked.connect(lambda: func2(0))

        self.buttons.append(button)

        layout.addWidget(self.buttons[0])
        layout.addWidget(self.buttons[1])
        layout.addWidget(self.buttons[2])
        layout.addWidget(self.buttons[3])

        # 오른쪽 끝에 닫기 버튼 배치
        layout.addStretch()
        layout.addWidget(self.buttons[4])

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
