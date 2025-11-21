from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from app.scripts.config import config
from app.scripts.custom_classes import (
    CustomComboBox,
    CustomFont,
    CustomLineEdit,
    KVInput,
    SimAnalysis,
    SimAttack,
    SimResult,
    SkillImage,
    Stats,
)
from app.scripts.data_manager import save_data
from app.scripts.misc import (
    convert_resource_path,
    get_available_skills,
    get_skill_pixmap,
)
from app.scripts.shared_data import UI_Variable
from app.scripts.simulate_macro import detSimulate, get_req_stats, randSimulate
from app.scripts.ui.sim_ui.graph import (
    DMGCanvas,
    DpmDistributionCanvas,
    SkillContributionCanvas,
    SkillDpsRatioCanvas,
)

if TYPE_CHECKING:
    from app.scripts.main_window import MainWindow
    from app.scripts.shared_data import SharedData


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

        # UI{N} 이름을 각각 수행하는 기능을 대표하는 이름으로 변경
        self.UI1 = Sim1UI(self.main_frame, self.shared_data)
        self.UI2 = Sim2UI(self.main_frame, self.shared_data)
        self.UI3 = Sim3UI(self.main_frame, self.shared_data)

        # SimUI4 완전히 제거?
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

        # KVInput에서 bool
        # KVInput에 인덱스, 이름 저장 후 넘기기
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
                for i, j in enumerate(self.inputs):
                    self.shared_data.info_stats.set_stat_from_index(i, int(j.text()))

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
                for _input, name in zip(
                    self.inputs, get_available_skills(self.shared_data)
                ):
                    self.shared_data.info_skill_levels[name] = int(_input.text())

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
                    display: str(self.shared_data.info_sim_details[name])
                    for name, display in self.shared_data.SIM_DETAILS.items()
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
                for _input, name in zip(
                    self.inputs, self.shared_data.SIM_DETAILS.keys()
                ):
                    self.shared_data.info_sim_details[name] = int(_input.text())

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
            for opt in options:
                stat, value = self.shared_data.POTENTIAL_STATS[opt]
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
        # 그리드는 한 줄에 위젯이 부족하면 정렬이 안됨
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
                """QFrame {
                    background-color: #F8F8F8;
                    border: 1px solid #CCCCCC;
                    border-left: 0px solid;
                    border-top-right-radius: 6px;
                    border-bottom-right-radius: 6px;
                    border-top-left-radius: 0px;
                    border-bottom-left-radius: 0px;
                    }"""
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
        options: list[list[tuple[str, float]]] = [[], [], [], []]

        # 각 옵션에 대해 차이 계산
        for key, (stat, value) in shared_data.POTENTIAL_STATS.items():
            stats: Stats = shared_data.info_stats.copy()
            stats.add_stat_from_name(stat, value)

            powers: list[float] = detSimulate(
                shared_data, stats, shared_data.info_sim_details
            ).powers

            diff_powers: list[float] = [
                round(powers[i] - shared_data.powers[i], 5) for i in range(4)
            ]

            for i in range(4):
                options[i].append((key, diff_powers[i]))

        # 전투력 차이로 정렬
        [options[i].sort(key=lambda x: x[1], reverse=True) for i in range(4)]

        texts: list[list[list[str]]] = [[["순위", "옵션", "전투력"]] for _ in range(4)]
        for i in range(4):
            for j, opt in enumerate(options[i], start=1):
                if opt[1] == 0:
                    rank = ["", "", ""]
                else:
                    rank: list[str] = [str(j), opt[0], f"{opt[1]:+.0f}"]

                texts[i].append(rank)

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
        nav_texts: list[str] = ["정보 입력", "시뮬레이터", "스탯 계산기"]

        # 네비게이션바 버튼들
        # 첫 번째 버튼만 활성화 상태로 시작
        self.buttons: list[QPushButton] = [
            Navigation.NavButton(nav_texts[i], self, i == 0, i, func1) for i in range(3)
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

        # 오른쪽 끝에 닫기 버튼 배치
        layout.addStretch()
        layout.addWidget(self.buttons[3])

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
