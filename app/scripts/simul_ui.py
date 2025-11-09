from __future__ import annotations

from app.scripts.custom_classes import SimAttack, Stats
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
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor
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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
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
        self.UI3 = Sim3UI(self.main_frame, self.shared_data)
        # self.UI4 = Sim4UI(self.main_frame, self.shared_data)
        self.stacked_layout.addWidget(self.UI1)
        self.stacked_layout.addWidget(self.UI2)
        self.stacked_layout.addWidget(self.UI3)

        self.stacked_layout.setCurrentIndex(0)
        # 스택 레이아웃 설정
        self.main_frame.setLayout(self.stacked_layout)

        self.adjust_main_frame_height()

    def change_layout(self, index: int) -> None:
        # 입력값 확인
        if index in (1, 2, 3) and not all(self.shared_data.is_input_valid.values()):
            self.master.get_popup_manager().make_notice_popup("SimInputError")

            return

        if index == self.stacked_layout.currentIndex():
            return

        # 네비게이션 버튼 색 변경
        self.update_nav(index)

        # 레이아웃 변경
        self.stacked_layout.setCurrentIndex(index)

        self.adjust_main_frame_height()

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

    def adjust_main_frame_height(self) -> None:
        """현재 표시 중인 UI 높이에 맞춰 메인 프레임 높이를 동기화."""

        current_widget = self.stacked_layout.currentWidget()
        if current_widget is None:
            return

        current_widget.adjustSize()
        height = current_widget.sizeHint().height()
        if height > 0:
            self.main_frame.setFixedHeight(height)


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

            self.input_changed(None)

        def input_changed(self, _) -> None:
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

            self.input_changed(None)

        def input_changed(self, _) -> None:
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

            self.input_changed(None)

        def input_changed(self, _) -> None:
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

        # 처음 생성때 계산하지 않고, 버튼을 누르면 시작.
        # 횟수를 설정할 수 있도록 변경
        # 진행 상황이 실시간으로 보이도록 그래핑 방식도 변경
        # GPU를 사용하는 것도 고려.
        # 레벨을 사용하도록 변경
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
    def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
        super().__init__(parent)

        self.shared_data: SharedData = shared_data
        self.ui_var = UI_Variable()

        # 초기 전투력 계산
        powers: list[float] = detSimulate(
            self.shared_data,
            self.shared_data.info_stats,
            self.shared_data.info_sim_details,
        ).powers

        for i, power in enumerate(powers):
            self.shared_data.powers[i] = power

        # 스탯 효율 계산
        self.efficiency_title: Title = Title(self, "스탯 효율 계산")
        self.efficiency = self.Efficiency(self, self.shared_data)

        # 추가 스펙업 계산기
        self.additional_title: Title = Title(self, "추가 스펙업 계산기")
        self.additional = self.Additional(self, self.shared_data)

        # 잠재능력 계산기
        self.potential_title: Title = Title(self, "잠재능력 계산기")
        self.potential = self.Potential(self, self.shared_data)

        # 잠재능력 옵션 순위
        self.potential_rank_title: Title = Title(self, "잠재능력 옵션 순위")
        self.potential_ranks = PotentialRank(self, self.shared_data)

        layout = QVBoxLayout(self)

        layout.addWidget(self.efficiency_title)
        layout.addWidget(self.efficiency)
        layout.addWidget(self.additional_title)
        layout.addWidget(self.additional)
        layout.addWidget(self.potential_title)
        layout.addWidget(self.potential)
        layout.addWidget(self.potential_rank_title)
        layout.addWidget(self.potential_ranks)

        # 레이아웃 여백과 간격 설정
        layout.setSpacing(10)  # 위젯들 사이의 간격
        layout.setContentsMargins(10, 10, 10, 10)  # 레이아웃의 여백
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    class Efficiency(QFrame):
        def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data
            self.ui_var = UI_Variable()

            if config.ui.debug_colors:
                self.setStyleSheet(
                    "QFrame { background-color: green; border: 0px solid; }"
                )
            else:
                self.setStyleSheet(
                    "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
                )

            widgets_width: int = 120
            arrow_size: int = 60

            # 왼쪽 콤보박스
            self.combobox_left = CustomComboBox(
                self,
                list(self.shared_data.STATS.values()),
                self.efficiency_changed,
            )
            self.combobox_left.setFixedWidth(widgets_width)

            # 왼쪽 스탯 입력창
            self.input = CustomLineEdit(self, self.efficiency_changed, "10")
            self.input.setFocus()
            self.input.setFixedWidth(widgets_width)

            input_layout = QVBoxLayout()
            input_layout.addStretch()
            input_layout.addWidget(self.combobox_left)
            input_layout.addWidget(self.input)
            input_layout.addStretch()
            input_layout.setSpacing(10)
            input_layout.setContentsMargins(0, 0, 0, 0)

            # 화살표
            self.arrow = QLabel("", self)
            self.arrow.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px solid; }"
            )

            pixmap: QPixmap = QPixmap(
                convert_resource_path("resources\\image\\lineArrow.png")
            )
            pixmap = pixmap.scaled(arrow_size, arrow_size)
            self.arrow.setPixmap(pixmap)
            self.arrow.setFixedSize(arrow_size, arrow_size)

            # 오른쪽 콤보박스
            self.combobox_right = CustomComboBox(
                self,
                list(self.shared_data.STATS.values()),
                self.efficiency_changed,
            )
            self.combobox_right.setFixedWidth(widgets_width)

            self.power_labels = PowerLabels(self, self.shared_data)
            self.power_labels.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )

            layout = QHBoxLayout(self)
            layout.addLayout(input_layout, stretch=0)
            layout.addWidget(self.arrow, stretch=0)
            layout.addWidget(self.combobox_right, stretch=0)
            layout.addWidget(self.power_labels, stretch=1)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            self.update_efficiency()

        def update_efficiency(self) -> None:
            left_index: int = self.combobox_left.currentIndex()
            right_index: int = self.combobox_right.currentIndex()
            value: int = int(self.input.text())

            # 종류가 같다면 동일한 값 출력
            if left_index == right_index:
                self.power_labels.set_texts(f"{value:.2f}")

                return

            # 종류가 다르다면 적용 후 계산
            stats: Stats = self.shared_data.info_stats.copy()
            stats.add_stat_from_index(left_index, value)

            # 적용 후 전투력 계산
            powers: list[float] = detSimulate(
                self.shared_data,
                stats,
                self.shared_data.info_sim_details,
            ).powers

            # 요구량 계산
            reqStats: list[str] = get_req_stats(
                self.shared_data,
                powers,
                list(self.shared_data.STATS.keys())[right_index],
            )

            # 텍스트 설정
            self.power_labels.set_texts(reqStats)

        def efficiency_changed(self) -> None:
            text: str = self.input.text()
            index: int = self.combobox_left.currentIndex()
            stat_name: str = list(self.shared_data.STATS.keys())[index]

            # 입력이 숫자가 아니면 오류
            if not text.isdigit():
                self.power_labels.set_texts("오류")

                return

            stat: int | float = self.shared_data.info_stats.get_stat_from_name(
                stat_name
            ) + int(text)

            # 최소 범위보다 작으면 오류
            if stat < self.shared_data.STAT_RANGES[stat_name][0]:
                self.power_labels.set_texts("오류")

                return

            # 최대 범위가 존재하지 않다면 통과
            if self.shared_data.STAT_RANGES[stat_name][1] == None:
                self.update_efficiency()

                return

            # 최대 범위가 존재한다면 비교 후 통과
            if stat <= self.shared_data.STAT_RANGES[stat_name][1]:
                self.update_efficiency()

                return

            # 최대 범위보다 크면 오류
            self.power_labels.set_texts("오류")

            return

    class Additional(QFrame):
        def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data

            if config.ui.debug_colors:
                self.setStyleSheet(
                    "QFrame { background-color: green; border: 0px solid; }"
                )
            else:
                self.setStyleSheet(
                    "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
                )

            stat_data: dict[str, str] = {
                name_ko: "0" for name_ko in self.shared_data.STATS.keys()
            }
            self.stats = StatInputs(self, stat_data, self.on_stat_changed)

            skills_data: dict[str, int] = {
                name: self.shared_data.info_skill_levels[name]
                for name in get_available_skills(self.shared_data)
            }
            self.skills = SkillInputs(
                self, self.shared_data, skills_data, self.on_skill_changed
            )

            self.power_labels = PowerLabels(self, self.shared_data)

            layout = QVBoxLayout(self)
            layout.addWidget(self.stats)
            layout.addWidget(self.skills)
            layout.addWidget(self.power_labels)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # todo: on_stat_changed, on_skill_changed를 합쳐서 하나로 만들기
        def on_stat_changed(self):
            # 스탯이 정상적으로 입력되었는지 확인
            # 음수도 허용
            def checkInput(num: int, text: str) -> bool:
                try:
                    value = int(text)

                except ValueError:
                    return False

                name: str = list(self.shared_data.STATS.keys())[num]
                stat: float = (
                    self.shared_data.info_stats.get_stat_from_name(name) + value
                )

                return (
                    self.shared_data.STAT_RANGES[name][0]
                    <= stat
                    <= self.shared_data.STAT_RANGES[name][1]
                )

            # 모두 통과 여부 확인
            all_valid = True
            for i, j in enumerate(self.stats.inputs):
                is_valid: bool = checkInput(i, j.text())

                # 스타일 업데이트
                j.set_valid(is_valid)

                # 전체 유효 여부 업데이트
                all_valid: bool = all_valid and is_valid

            # 모두 통과했다면 저장 및 플래그 설정
            if all_valid:
                self.update_powers()
                self.shared_data.is_input_valid["stat"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                self.shared_data.is_input_valid["stat"] = False

        def on_skill_changed(self):
            # 스킬이 정상적으로 입력되었는지 확인
            def checkInput(text: str) -> bool:
                if not text.isdigit():
                    return False

                return (
                    1
                    <= int(text)
                    <= self.shared_data.MAX_SKILL_LEVEL[self.shared_data.server_ID]
                )

            # 모두 통과 여부 확인
            all_valid = True
            for j in self.stats.inputs:
                is_valid: bool = checkInput(j.text())

                # 스타일 업데이트
                j.set_valid(is_valid)

                # 전체 유효 여부 업데이트
                all_valid: bool = all_valid and is_valid

            # 모두 통과했다면 저장 및 플래그 설정
            if all_valid:
                self.update_powers()
                self.shared_data.is_input_valid["skill"] = False

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                self.shared_data.is_input_valid["skill"] = False

        def update_powers(self) -> None:
            # 입력이 모두 정상인지 확인
            if not all(self.shared_data.is_input_valid.values()):
                self.power_labels.set_texts("오류")

                return

            # 모든 입력이 정상이라면 계산 시작
            # 스탯 적용
            stats: Stats = self.shared_data.info_stats.copy()
            for i in self.stats.inputs:
                stats.add_stat_from_index(self.stats.inputs.index(i), int(i.text()))

            # 스킬 적용
            skills: dict[str, int] = {
                skill: int(j.text())
                for j, skill in zip(
                    self.skills.inputs, get_available_skills(self.shared_data)
                )
            }

            # 전투력 계산
            powers: list[float] = detSimulate(
                self.shared_data,
                stats,
                self.shared_data.info_sim_details,
                skills,
            ).powers

            # 차이 계산
            diff_powers: list[float] = [
                powers[i] - self.shared_data.powers[i] for i in range(4)
            ]

            # 텍스트 설정
            texts: list[str] = [
                f"{int(powers[i]):}\n({diff_powers[i]:+.0f}, {diff_powers[i] / self.shared_data.powers[i]:+.1%})"
                for i in range(4)
            ]
            self.power_labels.set_texts(texts)

    class Potential(QFrame):
        def __init__(self, parent: QFrame, shared_data: SharedData) -> None:
            super().__init__(parent)

            self.shared_data: SharedData = shared_data

            if config.ui.debug_colors:
                self.setStyleSheet(
                    "QFrame { background-color: green; border: 0px solid; }"
                )
            else:
                self.setStyleSheet(
                    "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
                )

            self.option_comboboxes: list[CustomComboBox] = [
                CustomComboBox(
                    self,
                    list(self.shared_data.POTENTIAL_STATS.keys()),
                    self.update_values,
                )
                for _ in range(3)
            ]

            combobox_layout = QVBoxLayout()
            for combobox in self.option_comboboxes:
                combobox_layout.addWidget(combobox)
            combobox_layout.setSpacing(5)
            combobox_layout.setContentsMargins(0, 0, 0, 0)

            self.power_labels = PowerLabels(self, self.shared_data)

            layout = QHBoxLayout(self)
            layout.addLayout(combobox_layout)
            layout.addWidget(self.power_labels)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            self.update_values()

        def update_values(self) -> None:
            options: list[str] = [
                self.option_comboboxes[i].currentText() for i in range(3)
            ]

            stats: Stats = self.shared_data.info_stats.copy()
            for i in range(3):
                stat, value = self.shared_data.POTENTIAL_STATS[options[i]]
                stats.add_stat_from_name(stat, value)

            powers: list[float] = detSimulate(
                self.shared_data,
                stats,
                self.shared_data.info_sim_details,
            ).powers

            diff_powers: list[str] = [
                f"{powers[i] - self.shared_data.powers[i]:+.0f}" for i in range(4)
            ]

            self.power_labels.set_texts(diff_powers)


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
    def __init__(
        self,
        mainframe,
        shared_data: SharedData,
        texts: list[str] | str = "0",
        font_size=18,
    ):
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

        self.numbers: list[QLabel] = []

        # texts가 문자열인 경우 4개의 동일한 값으로 변환
        if isinstance(texts, str):
            texts = [texts] * 4

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
            self.numbers.append(power.number)

        # 레이아웃 여백과 간격 설정
        layout.setSpacing(10)  # 위젯들 사이의 간격
        layout.setContentsMargins(10, 10, 10, 10)  # 레이아웃의 여백
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_texts(self, texts: list[str] | str) -> None:
        # texts가 문자열인 경우 4개의 동일한 값으로 변환
        if isinstance(texts, str):
            texts = [texts] * 4

        for i in range(4):
            self.numbers[i].setText(texts[i])

    class Power(QFrame):
        def __init__(self, mainframe, name: str, text: str, color: str, font_size=18):
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


class PotentialRank(QFrame):
    def __init__(self, mainframe: QWidget, shared_data: SharedData) -> None:
        super().__init__(mainframe)

        texts: list[list[list[str]]] = self.get_potential_rank(shared_data)
        colors: list[str] = ["#8CFFA386", "#59FF9800", "#4D2196F3", "#B3A5D6A7"]

        ui_var = UI_Variable()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        for i in range(4):
            rank = self.Rank(
                self,
                shared_data.POWER_TITLES[i],
                texts[i],
                ui_var.sim_colors4[i],
                colors[i],
            )

            layout.addWidget(rank)

    def get_potential_rank(self, shared_data: SharedData) -> list[list[list[str]]]:
        ranks: list[list[tuple[str, float]]] = [[], [], [], []]

        for key, (stat, value) in shared_data.POTENTIAL_STATS.items():
            stats: Stats = shared_data.info_stats.copy()
            stats.add_stat_from_name(stat, value)

            powers: list[float] = detSimulate(
                shared_data,
                stats,
                shared_data.info_sim_details,
            ).powers

            diff_powers: list[float] = [
                round(powers[i] - shared_data.powers[i], 5) for i in range(4)
            ]

            for i in range(4):
                ranks[i].append((key, diff_powers[i]))

        [ranks[i].sort(key=lambda x: x[1], reverse=True) for i in range(4)]

        texts: list[list[list[str]]] = [[["순위", "옵션", "전투력"]] for _ in range(4)]
        for i in range(4):
            for j, rank in enumerate(ranks[i], start=1):
                if rank[1] == 0:
                    texts[i].append(["", "", ""])
                else:
                    texts[i].append([str(j), rank[0], f"{rank[1]:+.0f}"])

        return texts

    class Rank(QFrame):
        def __init__(
            self,
            parent: QFrame,
            name: str,
            data: list[list[str]],
            color: str,
            header_color: str,
        ):
            super().__init__(parent)

            self.setStyleSheet(
                f"QFrame {{ background-color: rgba({color}, 120); border: 1px solid rgb({color}); border-radius: 4px; }}"
            )

            layout = QGridLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.setLayout(layout)

            title = QLabel(name, self)
            title.setStyleSheet(
                f"""QLabel {{
                    background-color: rgb({color});
                    border: 0px solid;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                }}"""
            )
            title.setFont(CustomFont(14))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            layout.addWidget(title, 0, 0, 1, 3)

            ROWS = 16  # 인덱스 포함 16개
            for row in range(ROWS):
                rank = QLabel(data[row][0], self)
                rank.setStyleSheet(
                    f"""QLabel {{
                        background-color: {header_color if row == 0 else "transparent"};
                        border: 0px solid;
                        border-top: 1px solid rgb({color});
                        border-bottom: 0px solid;
                        border-top-left-radius: 0px;
                        border-top-right-radius: 0px;
                        border-bottom-left-radius: {"4" if row == ROWS-1 else "0"}px;
                        border-bottom-right-radius: 0px;
                    }}"""
                )
                rank.setFont(CustomFont(10))
                rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
                rank.setFixedWidth(30)

                label = QLabel(data[row][1], self)
                label.setStyleSheet(
                    f"""QLabel {{
                        background-color: {header_color if row == 0 else "transparent"};
                        border-top: 1px solid rgb({color});
                        border-bottom: 0px solid;
                        border-left: 1px solid rgb({color});
                        border-right: 1px solid rgb({color});
                        border-top-left-radius: 0px;
                        border-top-right-radius: 0px;
                        border-bottom-left-radius: 0px;
                        border-bottom-right-radius: 0px;
                    }}"""
                )
                label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                label.setFont(CustomFont(10))

                power = QLabel(data[row][2], self)
                power.setStyleSheet(
                    f"""QLabel {{
                        background-color: {header_color if row == 0 else "transparent"};
                        border: 0px solid;
                        border-top: 1px solid rgb({color});
                        border-bottom: 0px solid;
                        border-top-left-radius: 0px;
                        border-top-right-radius: 0px;
                        border-bottom-left-radius: 0px;
                        border-bottom-right-radius: {"4" if row == ROWS-1 else "0"}px;
                        }}"""
                )
                power.setFont(CustomFont(10))
                power.setAlignment(Qt.AlignmentFlag.AlignCenter)
                power.setFixedWidth(60)

                layout.addWidget(rank, row + 1, 0)
                layout.addWidget(label, row + 1, 1)
                layout.addWidget(power, row + 1, 2)


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
