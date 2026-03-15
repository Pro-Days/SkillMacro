from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayoutItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.calculator_engine import (
    DISPLAY_POWER_METRICS,
    POWER_METRIC_LABELS,
    CalculatorBaseState,
    CalculatorBaseValidation,
    CalculatorEvaluationContext,
    LevelUpEvaluation,
    RealmAdvanceEvaluation,
    ScrollUpgradeEvaluation,
    build_base_state,
    build_calculator_context,
    evaluate_arbitrary_stat_delta,
    evaluate_level_up_delta,
    evaluate_next_realm_delta,
    evaluate_scroll_upgrade_deltas,
    evaluate_single_stat_delta,
    validate_base_state,
)
from app.scripts.calculator_models import (
    BUILTIN_TALISMAN_TEMPLATES,
    CALCULATOR_STAT_SPECS,
    OVERALL_STAT_GRID_ROWS,
    REALM_TIER_SPECS,
    CalculatorPresetInput,
    CalculatorStatSpec,
    DanjeonState,
    DistributionState,
    EquippedOptimizationState,
    OwnedTalisman,
    OwnedTitle,
    PowerMetric,
    RealmTier,
    StatKey,
    TalismanTemplate,
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
from app.scripts.registry.resource_registry import (
    convert_resource_path,
    resource_registry,
)
from app.scripts.simulate_macro import simulate_deterministic, simulate_random
from app.scripts.ui.popup import NoticeKind
from app.scripts.ui.sim_ui.graph import (
    DMGCanvas,
    DpmDistributionCanvas,
    SkillContributionCanvas,
    SkillDpsRatioCanvas,
)

if TYPE_CHECKING:
    from app.scripts.macro_models import MacroPreset
    from app.scripts.registry.server_registry import ServerSpec
    from app.scripts.ui.main_window import MainWindow


@dataclass(frozen=True)
class SkillLevelInputSpec:
    """스킬 레벨 입력 UI 한 칸의 표시/저장 정보"""

    title: str
    value: int
    scroll_id: str


def build_skill_level_input_specs() -> list[SkillLevelInputSpec]:
    """현재 서버/프리셋 기준 스킬 레벨 입력 목록 구성"""

    # 스크롤 레벨만 입력 대상으로 노출하는 현재 구조 기준 준비
    server: ServerSpec = app_state.macro.current_server
    preset: MacroPreset = app_state.macro.current_preset
    specs: list[SkillLevelInputSpec] = []

    # 스크롤 공용 레벨 입력 칸 우선 구성
    for scroll_def in server.skill_registry.get_all_scroll_defs():
        shared_level: int = preset.info.get_scroll_level(scroll_def.id)
        specs.append(
            SkillLevelInputSpec(
                title=scroll_def.name,
                value=shared_level,
                scroll_id=scroll_def.id,
            )
        )

    return specs


class SimUI:
    def __init__(self, master: MainWindow, parent: QFrame):

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
        self.UI1 = Sim1UI(self.main_frame)
        self.UI2 = Sim2UI(self.main_frame)
        self.UI3 = Sim3UI(self.main_frame)

        # SimUI4 완전히 제거?
        # self.UI4 = Sim4UI(self.main_frame)
        self.stacked_layout.addWidget(self.UI1)
        self.stacked_layout.addWidget(self.UI2)
        self.stacked_layout.addWidget(self.UI3)

        self.stacked_layout.setCurrentIndex(0)
        # 스택 레이아웃 설정
        self.main_frame.setLayout(self.stacked_layout)

        self.adjust_main_frame_height()

    def change_layout(self, index: int) -> None:
        # 입력값 확인
        if index in (1, 2, 3) and not all(
            app_state.simulation.is_input_valid[k]
            for k in ("stat", "skill", "simDetails")
        ):
            self.master.get_popup_manager().show_notice(NoticeKind.SIM_INPUT_ERROR)

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
    def __init__(
        self,
        parent: QFrame,
    ):
        super().__init__(parent)

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: gray;}")

        # 스텟
        self.stats_title: Title = Title(parent=self, text="캐릭터 스탯")
        self.stats = self.Stats(self)

        # 스킬 입력
        self.skills_title: Title = Title(parent=self, text="스킬 레벨")
        self.skills = self.Skills(self)

        # 시뮬레이션 조건 입력
        self.condition_title: Title = Title(parent=self, text="시뮬레이션 조건")
        self.condition = self.Condition(self)

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
        def __init__(
            self,
            parent: QFrame,
        ) -> None:
            super().__init__(parent)

            # 스탯 데이터 생성
            stats_data: dict[str, str] = {
                spec.label: str(app_state.simulation.stats.get_stat_from_name(name_en))
                for name_en, spec in config.specs.STATS.items()
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

            self.input_changed()

        # KVInput에서 bool
        # KVInput에 인덱스, 이름 저장 후 넘기기
        def input_changed(self) -> None:
            # 정상적으로 입력되었는지 확인
            def checkInput(num: int, text: str) -> bool:
                if not text.isdigit():
                    return False

                key: str = list(config.specs.STATS.keys())[num]

                _min: int = config.specs.STATS[key].min
                _max: int = config.specs.STATS[key].max

                return _min <= int(text) <= _max

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
                    app_state.macro.current_preset.info.stats[
                        list(config.specs.STATS.keys())[i]
                    ] = int(j.text())

                save_data()

                app_state.simulation.is_input_valid["stat"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                app_state.simulation.is_input_valid["stat"] = False

    class Skills(QWidget):
        def __init__(
            self,
            parent: QFrame,
        ) -> None:
            super().__init__(parent)

            skill_input_specs: list[SkillLevelInputSpec] = (
                build_skill_level_input_specs()
            )

            # 스크롤 공용 레벨 기준 입력 위젯 생성
            self.skill_inputs: SkillInputs = SkillInputs(
                self,
                skill_input_specs,
                self.input_changed,
            )
            self.inputs: list[CustomLineEdit] = self.skill_inputs.inputs
            self.entries: list[SkillLevelInputSpec] = self.skill_inputs.entries

            # 레이아웃 설정
            layout = QVBoxLayout(self)
            layout.addWidget(self.skill_inputs)
            layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
            layout.setSpacing(0)  # 위젯 간 간격 제거
            self.setLayout(layout)

            # 크기 정책: 가로는 부모 크기 최대, 세로는 내용에 맞게 최소
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            self.input_changed()

        def input_changed(self) -> None:
            # 정상적으로 입력되었는지 확인
            def checkInput(text: str) -> bool:
                if not text.isdigit():
                    return False

                return 1 <= int(text) <= app_state.macro.current_server.max_skill_level

            # 모두 통과 여부 확인
            all_valid: bool = True
            for j in self.inputs:
                is_valid: bool = checkInput(j.text())

                # 스타일 업데이트
                j.set_valid(is_valid)

                # 전체 유효 여부 업데이트
                all_valid: bool = all_valid and is_valid

            # 모두 통과했다면 저장 및 플래그 설정
            if all_valid:
                # 스크롤 공용 레벨 입력값을 스크롤 ID 기준 저장소에 직접 반영
                for _input, entry in zip(self.inputs, self.entries):
                    input_level: int = int(_input.text())

                    app_state.macro.current_preset.info.set_scroll_level(
                        entry.scroll_id,
                        input_level,
                    )

                save_data()

                app_state.simulation.is_input_valid["skill"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                app_state.simulation.is_input_valid["skill"] = False

    class Condition(QWidget):
        def __init__(
            self,
            parent: QFrame,
        ) -> None:
            super().__init__(parent)

            # 시뮬레이션 조건 입력 위젯 생성
            self.condition_inputs = ConditionInputs(
                self,
                {
                    spec.label: str(app_state.simulation.sim_details[name])
                    for name, spec in config.specs.SIM_DETAILS.items()
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

            self.input_changed()

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
                for _input, name in zip(self.inputs, config.specs.SIM_DETAILS.keys()):
                    app_state.simulation.sim_details[name] = int(_input.text())

                save_data()

                app_state.simulation.is_input_valid["simInfo"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                app_state.simulation.is_input_valid["simInfo"] = False


class Sim2UI(QFrame):
    def __init__(
        self,
        parent: QFrame,
    ) -> None:
        super().__init__(parent)

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: gray;}")

        # 처음 생성때 계산하지 않고, 버튼을 누르면 시작.
        # 횟수를 설정할 수 있도록 변경
        # 진행 상황이 실시간으로 보이도록 그래핑 방식도 변경
        # GPU를 사용하는 것도 고려.
        # 레벨을 사용하도록 변경
        sim_result: SimResult = simulate_random(
            app_state.simulation.stats,
            app_state.simulation.sim_details,
        )
        powers: list[float] = sim_result.powers
        analysis: list[SimAnalysis] = sim_result.analysis
        resultDet: list[SimAttack] = sim_result.deterministic_boss_attacks
        results: list[list[SimAttack]] = sim_result.random_boss_attacks
        str_powers: list[str] = sim_result.str_powers

        for i, power in enumerate(powers):
            app_state.simulation.powers[i] = power

        # 전투력
        self.power_title: Title = Title(self, "전투력")
        self.power = PowerLabels(self, str_powers)

        # 분석
        self.analysis_title: Title = Title(self, "분석")
        self.analysis = AnalysisDetails(self, analysis)

        # DPM 분포
        self.DPM_graph = self.DPMGraph(self, results)

        # 스킬 비율
        self.ratio_graph = self.RatioGraph(self, resultDet)

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(self.DPM_graph)
        sub_layout.addWidget(self.ratio_graph)
        sub_layout.setSpacing(10)
        sub_layout.setContentsMargins(10, 10, 10, 10)

        # 시간 경과에 따른 피해량
        self.dps_graph = self.DPSGraph(self, results)

        # 누적 피해량
        self.total_graph = self.TotalGraph(self, results)

        # 스킬별 누적 기여도
        self.contribution_graph = self.ContributionGraph(self, resultDet)

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
            resultDet: list[SimAttack],
        ) -> None:
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = SkillDpsRatioCanvas(
                self,
                resultDet,
                app_state.macro.current_preset.skills.get_placed_skill_ids(),
                app_state.macro.current_server.id,
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
            results: list[list[SimAttack]],
        ) -> None:
            super().__init__(parent)

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
            resultDet: list[SimAttack],
        ) -> None:
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = SkillContributionCanvas(
                self,
                resultDet,
                app_state.macro.current_preset.skills.get_placed_skill_ids(),
                app_state.macro.current_server.id,
            )
            self.graph.setFixedHeight(400)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(self.graph)
            self.setLayout(layout)


class Sim3UI(QFrame):
    def __init__(
        self,
        parent: QFrame,
    ) -> None:
        super().__init__(parent)

        # 초기 전투력 계산
        powers: list[float] = simulate_deterministic(
            stats=app_state.simulation.stats,
            sim_details=app_state.simulation.sim_details,
            skills_info=app_state.macro.current_preset.usage_settings,
        ).powers

        for i, power in enumerate(powers):
            app_state.simulation.powers[i] = power

        # 스탯 효율 계산
        self.efficiency_title: Title = Title(self, "스탯 효율 계산")
        self.efficiency = self.Efficiency(self)

        # 추가 스펙업 계산기
        self.additional_title: Title = Title(self, "추가 스펙업 계산기")
        self.additional = self.Additional(self)

        # 잠재능력 계산기
        self.potential_title: Title = Title(self, "잠재능력 계산기")
        self.potential = self.Potential(self)

        # 잠재능력 옵션 순위
        self.potential_rank_title: Title = Title(self, "잠재능력 옵션 순위")
        self.potential_ranks = PotentialRank(self)

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
        def __init__(
            self,
            parent: QFrame,
        ) -> None:
            super().__init__(parent)

            if config.ui.debug_colors:
                self.setStyleSheet(
                    "QFrame { background-color: green; border: 0px solid; }"
                )
            else:
                self.setStyleSheet(
                    "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
                )

            # 전투력 선택지와 경지 선택지 순서 고정
            self.metric_options: list[PowerMetric] = list(DISPLAY_POWER_METRICS)
            self.realm_options: list[RealmTier] = list(REALM_TIER_SPECS.keys())

            # 계산 기준 입력 UI 구성
            self.metric_title: QLabel = QLabel("기준 전투력", self)
            self.metric_title.setFont(CustomFont(12))
            self.metric_combobox = CustomComboBox(
                self,
                [POWER_METRIC_LABELS[metric] for metric in self.metric_options],
                self.on_base_input_changed,
            )

            self.level_input_widget: KVInput = KVInput(
                self,
                "레벨",
                "0",
                self.on_base_input_changed,
                max_width=100,
            )
            self.level_input: CustomLineEdit = self.level_input_widget.input

            self.realm_title: QLabel = QLabel("경지", self)
            self.realm_title.setFont(CustomFont(12))
            self.realm_combobox = CustomComboBox(
                self,
                [REALM_TIER_SPECS[realm].label for realm in self.realm_options],
                self.on_base_input_changed,
            )

            # 전체 스탯 입력 UI 구성
            self.stats_title: QLabel = QLabel("전체 스탯", self)
            self.stats_title.setFont(CustomFont(12))
            self.stats_inputs = self.OverallStatInputs(
                self,
                self.on_base_input_changed,
                self._get_initial_overall_stats(),
            )

            # 스크롤 레벨 입력 UI 구성
            self.scroll_title: QLabel = QLabel("스크롤 레벨", self)
            self.scroll_title.setFont(CustomFont(12))
            self.skills = SkillInputs(
                self,
                build_skill_level_input_specs(),
                self.on_base_input_changed,
            )

            # 최적화 기준 입력 UI 구성
            self.optimization_title: QLabel = QLabel("현재 선택 입력", self)
            self.optimization_title.setFont(CustomFont(12))
            self.distribution_inputs = self.DistributionInputs(
                self,
                self.on_optimization_input_changed,
            )
            self.danjeon_inputs = self.DanjeonInputs(
                self,
                self.on_optimization_input_changed,
            )
            self.title_inputs = self.TitleInputs(
                self,
                self.on_optimization_input_changed,
            )
            self.talisman_inputs = self.TalismanInputs(
                self,
                self.on_optimization_input_changed,
            )
            self.base_state_title: QLabel = QLabel("기준 상태 분리", self)
            self.base_state_title.setFont(CustomFont(12))
            self.base_state_list = self.ResultList(self)

            # 결과 표시 UI 구성
            self.current_power_title: QLabel = QLabel("현재 전투력", self)
            self.current_power_title.setFont(CustomFont(12))
            self.current_power_list = self.ResultList(self)

            self.stat_efficiency_title: QLabel = QLabel("스탯 1당 효율", self)
            self.stat_efficiency_title.setFont(CustomFont(12))
            self.stat_efficiency_list = self.ResultList(self)

            self.level_up_title: QLabel = QLabel("레벨 1업 효율", self)
            self.level_up_title.setFont(CustomFont(12))
            self.level_up_list = self.ResultList(self)

            self.realm_up_title: QLabel = QLabel("다음 경지 효율", self)
            self.realm_up_title.setFont(CustomFont(12))
            self.realm_up_list = self.ResultList(self)

            self.scroll_efficiency_title: QLabel = QLabel("스크롤 +1 효율", self)
            self.scroll_efficiency_title.setFont(CustomFont(12))
            self.scroll_efficiency_list = self.ResultList(self)

            # 사용자 지정 변화량 입력 UI 구성
            self.custom_delta_title: QLabel = QLabel("사용자 지정 스탯 변화량", self)
            self.custom_delta_title.setFont(CustomFont(12))
            self.custom_delta_inputs = self.OverallStatInputs(
                self,
                self.on_custom_delta_changed,
                self._build_empty_stat_map(),
            )
            self.custom_delta_result_list = self.ResultList(self)

            # 상단 기준 입력 행 구성
            metric_layout = QHBoxLayout()
            metric_layout.addWidget(self.metric_title)
            metric_layout.addWidget(self.metric_combobox)
            metric_layout.addSpacing(20)
            metric_layout.addWidget(self.level_input_widget)
            metric_layout.addSpacing(20)
            metric_layout.addWidget(self.realm_title)
            metric_layout.addWidget(self.realm_combobox)
            metric_layout.addStretch(1)

            layout = QVBoxLayout(self)
            layout.addLayout(metric_layout)
            layout.addWidget(self.stats_title)
            layout.addWidget(self.stats_inputs)
            layout.addWidget(self.scroll_title)
            layout.addWidget(self.skills)
            layout.addWidget(self.optimization_title)
            layout.addWidget(self.distribution_inputs)
            layout.addWidget(self.danjeon_inputs)
            layout.addWidget(self.title_inputs)
            layout.addWidget(self.talisman_inputs)
            layout.addWidget(self.base_state_title)
            layout.addWidget(self.base_state_list)
            layout.addWidget(self.current_power_title)
            layout.addWidget(self.current_power_list)
            layout.addWidget(self.stat_efficiency_title)
            layout.addWidget(self.stat_efficiency_list)
            layout.addWidget(self.level_up_title)
            layout.addWidget(self.level_up_list)
            layout.addWidget(self.realm_up_title)
            layout.addWidget(self.realm_up_list)
            layout.addWidget(self.scroll_efficiency_title)
            layout.addWidget(self.scroll_efficiency_list)
            layout.addWidget(self.custom_delta_title)
            layout.addWidget(self.custom_delta_inputs)
            layout.addWidget(self.custom_delta_result_list)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            # 저장된 경지 선택 상태 동기화
            self.realm_combobox.setCurrentIndex(
                self.realm_options.index(self._get_calculator_realm())
            )
            self._load_optimization_inputs()

            # 초기 계산 결과 반영
            self.on_base_input_changed()
            self.on_custom_delta_changed()

        class OverallStatInputs(QFrame):
            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
                initial_values: dict[StatKey, str],
            ) -> None:
                super().__init__(parent)

                # 전체 스탯 입력칸 맵 구성
                self.inputs: dict[StatKey, CustomLineEdit] = {}
                grid_layout: QGridLayout = QGridLayout(self)

                for row_index, stat_row in enumerate(OVERALL_STAT_GRID_ROWS):
                    for column_index, stat_key in enumerate(stat_row):
                        if stat_key is None:
                            continue

                        # 이미지 표기와 동일한 라벨 구성
                        stat_spec: CalculatorStatSpec = CALCULATOR_STAT_SPECS[stat_key]
                        label: str = stat_spec.label

                        if stat_spec.is_percent:
                            label = f"{label}(%)"

                        item_widget: KVInput = KVInput(
                            self,
                            label,
                            initial_values[stat_key],
                            connected_function,
                            max_width=120,
                        )
                        self.inputs[stat_key] = item_widget.input
                        grid_layout.addWidget(item_widget, row_index, column_index)

                # 2열 배치 간격 고정
                grid_layout.setVerticalSpacing(8)
                grid_layout.setHorizontalSpacing(20)
                self.setLayout(grid_layout)

        class ResultList(QFrame):
            def __init__(self, parent: QWidget) -> None:
                super().__init__(parent)

                # 결과 행을 재구성할 레이아웃 준비
                self._layout: QVBoxLayout = QVBoxLayout(self)
                self._layout.setContentsMargins(0, 0, 0, 0)
                self._layout.setSpacing(6)
                self.setLayout(self._layout)

            def set_rows(self, rows: list[tuple[str, str]]) -> None:
                """결과 행 목록 재렌더링"""

                # 기존 결과 라벨 정리
                while self._layout.count():
                    child_item: QLayoutItem = self._layout.takeAt(0)
                    child_widget: QWidget = child_item.widget()

                    if child_widget is not None:
                        child_widget.deleteLater()

                # 새 결과 행 구성
                for title, value in rows:
                    row_widget: QFrame = QFrame(self)
                    row_layout: QHBoxLayout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(8, 6, 8, 6)
                    row_layout.setSpacing(10)

                    title_label: QLabel = QLabel(title, row_widget)
                    title_label.setFont(CustomFont(11))
                    value_label: QLabel = QLabel(value, row_widget)
                    value_label.setFont(CustomFont(11))
                    value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

                    row_layout.addWidget(title_label)
                    row_layout.addStretch(1)
                    row_layout.addWidget(value_label)
                    self._layout.addWidget(row_widget)

        class DistributionInputs(QFrame):
            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
            ) -> None:
                super().__init__(parent)

                # 현재 스탯 분배 입력 행 구성
                self.inputs: dict[str, CustomLineEdit] = {}
                layout: QHBoxLayout = QHBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(10)

                for field_name, label in (
                    ("strength", "힘"),
                    ("dexterity", "민첩"),
                    ("vitality", "생명력"),
                    ("luck", "행운"),
                ):
                    item_widget: KVInput = KVInput(
                        self,
                        label,
                        "0",
                        connected_function,
                        max_width=80,
                    )
                    self.inputs[field_name] = item_widget.input
                    layout.addWidget(item_widget)

                layout.addStretch(1)
                self.setLayout(layout)

        class DanjeonInputs(QFrame):
            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
            ) -> None:
                super().__init__(parent)

                # 현재 단전 입력 행 구성
                self.inputs: dict[str, CustomLineEdit] = {}
                layout: QHBoxLayout = QHBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(10)

                for field_name, label in (
                    ("upper", "상단전"),
                    ("middle", "중단전"),
                    ("lower", "하단전"),
                ):
                    item_widget: KVInput = KVInput(
                        self,
                        label,
                        "0",
                        connected_function,
                        max_width=80,
                    )
                    self.inputs[field_name] = item_widget.input
                    layout.addWidget(item_widget)

                layout.addStretch(1)
                self.setLayout(layout)

        class TitleInputs(QFrame):
            class TitleStatRow(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    connected_function: Callable[[], None],
                    remove_function: Callable[
                        ["Sim3UI.Efficiency.TitleInputs.TitleStatRow"], None
                    ],
                    stat_key: StatKey | None = None,
                    value: float = 0.0,
                ) -> None:
                    super().__init__(parent)

                    # 스탯 선택/수치/삭제 버튼 구성
                    self._connected_function: Callable[[], None] = connected_function
                    self._remove_function = remove_function
                    self._stat_options: list[StatKey] = list(
                        CALCULATOR_STAT_SPECS.keys()
                    )

                    layout: QHBoxLayout = QHBoxLayout(self)
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(8)

                    self.stat_combobox = CustomComboBox(
                        self,
                        [
                            f"{spec.label}(%)" if spec.is_percent else spec.label
                            for spec in CALCULATOR_STAT_SPECS.values()
                        ],
                        self._connected_function,
                    )
                    if stat_key is not None:
                        self.stat_combobox.setCurrentIndex(
                            self._stat_options.index(stat_key)
                        )

                    self.value_input_widget: KVInput = KVInput(
                        self,
                        "수치",
                        f"{value:g}",
                        self._connected_function,
                        max_width=100,
                    )
                    self.value_input: CustomLineEdit = self.value_input_widget.input

                    self.remove_button: QPushButton = QPushButton("삭제", self)
                    self.remove_button.clicked.connect(self._on_remove_clicked)
                    self.remove_button.setFont(CustomFont(10))

                    layout.addWidget(self.stat_combobox)
                    layout.addWidget(self.value_input_widget)
                    layout.addWidget(self.remove_button)
                    self.setLayout(layout)

                def _on_remove_clicked(self) -> None:
                    """스탯 행 삭제 요청"""

                    self._remove_function(self)

                def get_value(self) -> tuple[bool, StatKey, float]:
                    """행 데이터 복원"""

                    text: str = self.value_input.text()
                    is_valid: bool = True
                    try:
                        value: float = float(text)
                        self.value_input.set_valid(True)

                    except ValueError:
                        value = 0.0
                        is_valid = False
                        self.value_input.set_valid(False)

                    stat_key: StatKey = self._stat_options[
                        self.stat_combobox.currentIndex()
                    ]
                    return is_valid, stat_key, value

            class TitleCard(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    connected_function: Callable[[], None],
                    remove_function: Callable[
                        ["Sim3UI.Efficiency.TitleInputs.TitleCard"], None
                    ],
                    data: OwnedTitle | None = None,
                ) -> None:
                    super().__init__(parent)

                    # 칭호 카드 전체 편집 영역 구성
                    self._connected_function: Callable[[], None] = connected_function
                    self._remove_function: Callable[
                        [Sim3UI.Efficiency.TitleInputs.TitleCard], None
                    ] = remove_function
                    self.stat_rows: list[Sim3UI.Efficiency.TitleInputs.TitleStatRow] = (
                        []
                    )

                    root_layout: QVBoxLayout = QVBoxLayout(self)
                    root_layout.setContentsMargins(8, 8, 8, 8)
                    root_layout.setSpacing(8)

                    self.name_input_widget: KVInput = KVInput(
                        self,
                        "칭호명",
                        data.name if data is not None else "",
                        connected_function,
                        max_width=180,
                    )
                    self.name_input: CustomLineEdit = self.name_input_widget.input
                    root_layout.addWidget(self.name_input_widget)

                    self.stats_container: QWidget = QWidget(self)
                    self.stats_layout: QVBoxLayout = QVBoxLayout(self.stats_container)
                    self.stats_layout.setContentsMargins(0, 0, 0, 0)
                    self.stats_layout.setSpacing(6)
                    root_layout.addWidget(self.stats_container)

                    self.add_stat_button: QPushButton = QPushButton("스탯 추가", self)
                    self.add_stat_button.clicked.connect(self._add_empty_stat_row)
                    self.add_stat_button.setFont(CustomFont(10))
                    root_layout.addWidget(self.add_stat_button)

                    self.remove_button: QPushButton = QPushButton("칭호 삭제", self)
                    self.remove_button.clicked.connect(self._on_remove_clicked)
                    self.remove_button.setFont(CustomFont(10))
                    root_layout.addWidget(self.remove_button)
                    self.setLayout(root_layout)

                    if data is not None and data.stats:
                        for stat_key_text, stat_value in data.stats.items():
                            self._add_stat_row(
                                StatKey(stat_key_text), float(stat_value)
                            )

                    else:
                        self._add_empty_stat_row()

                def _add_stat_row(self, stat_key: StatKey, value: float) -> None:
                    """지정된 스탯 행 추가"""

                    row = Sim3UI.Efficiency.TitleInputs.TitleStatRow(
                        self.stats_container,
                        self._connected_function,
                        self._remove_stat_row,
                        stat_key=stat_key,
                        value=value,
                    )
                    self.stat_rows.append(row)
                    self.stats_layout.addWidget(row)

                def _add_empty_stat_row(self) -> None:
                    """빈 스탯 행 추가"""

                    self._add_stat_row(StatKey.ATTACK, 0.0)
                    self._connected_function()

                def _remove_stat_row(
                    self,
                    target_row: "Sim3UI.Efficiency.TitleInputs.TitleStatRow",
                ) -> None:
                    """스탯 행 제거"""

                    self.stats_layout.removeWidget(target_row)
                    self.stat_rows.remove(target_row)
                    target_row.deleteLater()
                    self._connected_function()

                def _on_remove_clicked(self) -> None:
                    """칭호 카드 삭제 요청"""

                    self._remove_function(self)

                def to_owned_title(self, title_id: str) -> tuple[bool, OwnedTitle]:
                    """카드 데이터를 칭호 모델로 변환"""

                    is_valid: bool = True
                    stats: dict[str, float] = {}
                    for stat_row in self.stat_rows:
                        row_valid: bool
                        stat_key: StatKey
                        stat_value: float
                        row_valid, stat_key, stat_value = stat_row.get_value()
                        is_valid = is_valid and row_valid
                        if stat_value == 0.0:
                            continue

                        current_value: float = stats.get(stat_key.value, 0.0)
                        stats[stat_key.value] = current_value + stat_value

                    name: str = self.name_input.text().strip()
                    owned_title: OwnedTitle = OwnedTitle(
                        title_id=title_id,
                        name=name,
                        stats=stats,
                    )
                    return is_valid, owned_title

            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
            ) -> None:
                super().__init__(parent)

                # 보유 칭호 목록 및 현재 장착 선택 UI 구성
                self._connected_function: Callable[[], None] = connected_function
                self._cards: list[Sim3UI.Efficiency.TitleInputs.TitleCard] = []

                root_layout: QVBoxLayout = QVBoxLayout(self)
                root_layout.setContentsMargins(0, 0, 0, 0)
                root_layout.setSpacing(8)

                equipped_layout: QHBoxLayout = QHBoxLayout()
                equipped_layout.setContentsMargins(0, 0, 0, 0)
                equipped_layout.setSpacing(8)
                self.equipped_title_label: QLabel = QLabel("현재 장착 칭호", self)
                self.equipped_title_label.setFont(CustomFont(11))
                self.equipped_title_combobox = CustomComboBox(
                    self,
                    ["없음"],
                    connected_function,
                )
                equipped_layout.addWidget(self.equipped_title_label)
                equipped_layout.addWidget(self.equipped_title_combobox)
                equipped_layout.addStretch(1)
                root_layout.addLayout(equipped_layout)

                self.cards_container: QWidget = QWidget(self)
                self.cards_layout: QVBoxLayout = QVBoxLayout(self.cards_container)
                self.cards_layout.setContentsMargins(0, 0, 0, 0)
                self.cards_layout.setSpacing(8)
                root_layout.addWidget(self.cards_container)

                self.add_button: QPushButton = QPushButton("칭호 추가", self)
                self.add_button.clicked.connect(self.add_card)
                self.add_button.setFont(CustomFont(10))
                root_layout.addWidget(self.add_button)
                self.setLayout(root_layout)

            def add_card(
                self,
                data: OwnedTitle | None = None,
                emit_change: bool = True,
            ) -> None:
                """칭호 카드 추가"""

                card = Sim3UI.Efficiency.TitleInputs.TitleCard(
                    self.cards_container,
                    self._connected_function,
                    self.remove_card,
                    data=data,
                )
                self._cards.append(card)
                self.cards_layout.addWidget(card)
                self.refresh_equipped_options()
                if emit_change:
                    self._connected_function()

            def remove_card(
                self,
                target_card: "Sim3UI.Efficiency.TitleInputs.TitleCard",
            ) -> None:
                """칭호 카드 제거"""

                self.cards_layout.removeWidget(target_card)
                self._cards.remove(target_card)
                target_card.deleteLater()
                self.refresh_equipped_options()
                self._connected_function()

            def refresh_equipped_options(self) -> None:
                """현재 장착 선택 목록 갱신"""

                current_text: str = self.equipped_title_combobox.currentText()
                self.equipped_title_combobox.blockSignals(True)
                self.equipped_title_combobox.clear()
                options: list[str] = ["없음"]
                for index, card in enumerate(self._cards):
                    title_name: str = card.name_input.text().strip()
                    if not title_name:
                        title_name = f"칭호 {index + 1}"
                    options.append(title_name)
                self.equipped_title_combobox.addItems(options)
                if current_text in options:
                    self.equipped_title_combobox.setCurrentIndex(
                        options.index(current_text)
                    )
                self.equipped_title_combobox.blockSignals(False)

            def load(
                self,
                owned_titles: list[OwnedTitle],
                equipped_title_id: str | None,
            ) -> None:
                """저장된 칭호 입력 상태 로드"""

                for card in self._cards.copy():
                    self.remove_card(card)

                for owned_title in owned_titles:
                    self.add_card(owned_title, emit_change=False)

                self.refresh_equipped_options()
                if equipped_title_id is None:
                    self.equipped_title_combobox.setCurrentIndex(0)
                    return

                for index, owned_title in enumerate(owned_titles, start=1):
                    if owned_title.title_id == equipped_title_id:
                        self.equipped_title_combobox.setCurrentIndex(index)
                        return

            def build_state(self) -> tuple[bool, list[OwnedTitle], str | None]:
                """현재 칭호 입력 상태 복원"""

                is_valid: bool = True
                owned_titles: list[OwnedTitle] = []
                for index, card in enumerate(self._cards):
                    title_id: str = f"title_{index}"
                    card_valid: bool
                    owned_title: OwnedTitle
                    card_valid, owned_title = card.to_owned_title(title_id)
                    is_valid = is_valid and card_valid
                    owned_titles.append(owned_title)

                equipped_index: int = self.equipped_title_combobox.currentIndex()
                equipped_title_id: str | None = None
                if equipped_index > 0 and equipped_index - 1 < len(owned_titles):
                    equipped_title_id = owned_titles[equipped_index - 1].title_id

                return is_valid, owned_titles, equipped_title_id

        class TalismanInputs(QFrame):
            class TalismanRow(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    connected_function: Callable[[], None],
                    remove_function: Callable[
                        ["Sim3UI.Efficiency.TalismanInputs.TalismanRow"], None
                    ],
                    data: OwnedTalisman | None = None,
                ) -> None:
                    super().__init__(parent)

                    # 보유 부적 한 줄 편집 UI 구성
                    self._connected_function: Callable[[], None] = connected_function
                    self._remove_function = remove_function
                    self._templates: list[TalismanTemplate] = list(
                        BUILTIN_TALISMAN_TEMPLATES
                    )

                    layout: QHBoxLayout = QHBoxLayout(self)
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(8)

                    self.template_combobox = CustomComboBox(
                        self,
                        [template.name for template in self._templates],
                        connected_function,
                    )
                    if data is not None:
                        for index, template in enumerate(self._templates):
                            if template.template_id == data.template_id:
                                self.template_combobox.setCurrentIndex(index)
                                break

                    self.level_input_widget: KVInput = KVInput(
                        self,
                        "레벨",
                        f"{data.level if data is not None else 1}",
                        connected_function,
                        max_width=80,
                    )
                    self.level_input: CustomLineEdit = self.level_input_widget.input

                    self.remove_button: QPushButton = QPushButton("삭제", self)
                    self.remove_button.clicked.connect(self._on_remove_clicked)
                    self.remove_button.setFont(CustomFont(10))

                    layout.addWidget(self.template_combobox)
                    layout.addWidget(self.level_input_widget)
                    layout.addWidget(self.remove_button)
                    self.setLayout(layout)

                def _on_remove_clicked(self) -> None:
                    """보유 부적 제거 요청"""

                    self._remove_function(self)

                def to_owned_talisman(
                    self, owned_id: str
                ) -> tuple[bool, OwnedTalisman]:
                    """행 데이터를 보유 부적 모델로 변환"""

                    text: str = self.level_input.text()
                    try:
                        level: int = int(text)
                        is_valid: bool = 1 <= level <= 10
                        self.level_input.set_valid(is_valid)

                    except ValueError:
                        level = 1
                        is_valid = False
                        self.level_input.set_valid(False)

                    template: TalismanTemplate = self._templates[
                        self.template_combobox.currentIndex()
                    ]
                    owned_talisman: OwnedTalisman = OwnedTalisman(
                        owned_id=owned_id,
                        template_id=template.template_id,
                        level=level,
                    )
                    return is_valid, owned_talisman

            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
            ) -> None:
                super().__init__(parent)

                # 보유 부적 목록 및 현재 장착 선택 UI 구성
                self._connected_function: Callable[[], None] = connected_function
                self._rows: list[Sim3UI.Efficiency.TalismanInputs.TalismanRow] = []

                root_layout: QVBoxLayout = QVBoxLayout(self)
                root_layout.setContentsMargins(0, 0, 0, 0)
                root_layout.setSpacing(8)

                self.equipped_comboboxes: list[CustomComboBox] = []
                for slot_index in range(3):
                    equipped_layout: QHBoxLayout = QHBoxLayout()
                    equipped_layout.setContentsMargins(0, 0, 0, 0)
                    equipped_layout.setSpacing(8)
                    label: QLabel = QLabel(f"현재 장착 부적 {slot_index + 1}", self)
                    label.setFont(CustomFont(11))
                    combobox = CustomComboBox(self, ["없음"], connected_function)
                    self.equipped_comboboxes.append(combobox)
                    equipped_layout.addWidget(label)
                    equipped_layout.addWidget(combobox)
                    equipped_layout.addStretch(1)
                    root_layout.addLayout(equipped_layout)

                self.rows_container: QWidget = QWidget(self)
                self.rows_layout: QVBoxLayout = QVBoxLayout(self.rows_container)
                self.rows_layout.setContentsMargins(0, 0, 0, 0)
                self.rows_layout.setSpacing(6)
                root_layout.addWidget(self.rows_container)

                self.add_button: QPushButton = QPushButton("부적 추가", self)
                self.add_button.clicked.connect(self.add_row)
                self.add_button.setFont(CustomFont(10))
                root_layout.addWidget(self.add_button)
                self.setLayout(root_layout)

            def add_row(
                self,
                data: OwnedTalisman | None = None,
                emit_change: bool = True,
            ) -> None:
                """보유 부적 행 추가"""

                row = Sim3UI.Efficiency.TalismanInputs.TalismanRow(
                    self.rows_container,
                    self._connected_function,
                    self.remove_row,
                    data=data,
                )
                self._rows.append(row)
                self.rows_layout.addWidget(row)
                self.refresh_equipped_options()
                if emit_change:
                    self._connected_function()

            def remove_row(
                self,
                target_row: "Sim3UI.Efficiency.TalismanInputs.TalismanRow",
            ) -> None:
                """보유 부적 행 제거"""

                self.rows_layout.removeWidget(target_row)
                self._rows.remove(target_row)
                target_row.deleteLater()
                self.refresh_equipped_options()
                self._connected_function()

            def refresh_equipped_options(self) -> None:
                """현재 장착 부적 선택 목록 갱신"""

                options: list[str] = ["없음"]
                for index, row in enumerate(self._rows):
                    template_name: str = row.template_combobox.currentText()
                    level_text: str = row.level_input.text()
                    options.append(f"{template_name} Lv.{level_text} ({index + 1})")

                for combobox in self.equipped_comboboxes:
                    current_text: str = combobox.currentText()
                    combobox.blockSignals(True)
                    combobox.clear()
                    combobox.addItems(options)
                    if current_text in options:
                        combobox.setCurrentIndex(options.index(current_text))
                    combobox.blockSignals(False)

            def load(
                self,
                owned_talismans: list[OwnedTalisman],
                equipped_ids: list[str],
            ) -> None:
                """저장된 부적 입력 상태 로드"""

                for row in self._rows.copy():
                    self.remove_row(row)

                for owned_talisman in owned_talismans:
                    self.add_row(owned_talisman, emit_change=False)

                self.refresh_equipped_options()
                owned_id_order: list[str] = [
                    owned_talisman.owned_id for owned_talisman in owned_talismans
                ]
                for combobox_index, combobox in enumerate(self.equipped_comboboxes):
                    if combobox_index >= len(equipped_ids):
                        combobox.setCurrentIndex(0)
                        continue

                    equipped_id: str = equipped_ids[combobox_index]
                    if equipped_id not in owned_id_order:
                        combobox.setCurrentIndex(0)
                        continue

                    combobox.setCurrentIndex(owned_id_order.index(equipped_id) + 1)

            def build_state(self) -> tuple[bool, list[OwnedTalisman], list[str]]:
                """현재 부적 입력 상태 복원"""

                is_valid: bool = True
                owned_talismans: list[OwnedTalisman] = []
                for index, row in enumerate(self._rows):
                    owned_id: str = f"talisman_{index}"
                    row_valid: bool
                    owned_talisman: OwnedTalisman
                    row_valid, owned_talisman = row.to_owned_talisman(owned_id)
                    is_valid = is_valid and row_valid
                    owned_talismans.append(owned_talisman)

                equipped_ids: list[str] = []
                for combobox in self.equipped_comboboxes:
                    selected_index: int = combobox.currentIndex()
                    if selected_index <= 0:
                        continue

                    target_index: int = selected_index - 1
                    if target_index >= len(owned_talismans):
                        continue

                    equipped_ids.append(owned_talismans[target_index].owned_id)

                return is_valid, owned_talismans, equipped_ids

        def _get_preset(self) -> "MacroPreset":
            """현재 선택 프리셋 반환"""

            return app_state.macro.current_preset

        def _get_calculator_realm(self) -> RealmTier:
            """저장된 현재 경지 반환"""

            return self._get_preset().info.calculator.realm_tier

        def _get_initial_overall_stats(self) -> dict[StatKey, str]:
            """저장된 전체 스탯 입력 문자열 맵 반환"""

            # 저장된 전체 스탯을 입력 위젯 초기 문자열로 변환
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            values: dict[StatKey, str] = {}
            for stat_key in CALCULATOR_STAT_SPECS.keys():
                values[stat_key] = f"{calculator_input.overall_stats[stat_key.value]:g}"

            return values

        def _build_empty_stat_map(self) -> dict[StatKey, str]:
            """사용자 지정 변화량 초기값 맵 생성"""

            # 변화량 입력은 전부 0에서 시작
            values: dict[StatKey, str] = {}
            for stat_key in CALCULATOR_STAT_SPECS.keys():
                values[stat_key] = "0"

            return values

        def _get_selected_metric(self) -> PowerMetric:
            """현재 선택 전투력 종류 반환"""

            selected_metric: PowerMetric = self.metric_options[
                self.metric_combobox.currentIndex()
            ]
            return selected_metric

        def _load_optimization_inputs(self) -> None:
            """저장된 최적화 입력 상태 로드"""

            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            self.distribution_inputs.inputs["strength"].setText(
                str(calculator_input.distribution.strength)
            )
            self.distribution_inputs.inputs["dexterity"].setText(
                str(calculator_input.distribution.dexterity)
            )
            self.distribution_inputs.inputs["vitality"].setText(
                str(calculator_input.distribution.vitality)
            )
            self.distribution_inputs.inputs["luck"].setText(
                str(calculator_input.distribution.luck)
            )
            self.danjeon_inputs.inputs["upper"].setText(
                str(calculator_input.danjeon.upper)
            )
            self.danjeon_inputs.inputs["middle"].setText(
                str(calculator_input.danjeon.middle)
            )
            self.danjeon_inputs.inputs["lower"].setText(
                str(calculator_input.danjeon.lower)
            )
            self.title_inputs.load(
                calculator_input.owned_titles,
                calculator_input.equipped.equipped_title_id,
            )
            self.talisman_inputs.load(
                calculator_input.owned_talismans,
                calculator_input.equipped.equipped_talisman_ids,
            )

        def _read_distribution_state(self) -> tuple[bool, DistributionState]:
            """현재 스탯 분배 상태 복원"""

            is_valid: bool = True
            values: dict[str, int] = {}
            for field_name, input_widget in self.distribution_inputs.inputs.items():
                text: str = input_widget.text()
                if not text.isdigit():
                    input_widget.set_valid(False)
                    is_valid = False
                    values[field_name] = 0
                    continue

                input_widget.set_valid(True)
                values[field_name] = int(text)

            distribution_state: DistributionState = DistributionState(
                strength=values["strength"],
                dexterity=values["dexterity"],
                vitality=values["vitality"],
                luck=values["luck"],
                is_locked=False,
                use_reset=False,
            )
            return is_valid, distribution_state

        def _read_danjeon_state(self) -> tuple[bool, DanjeonState]:
            """현재 단전 상태 복원"""

            is_valid: bool = True
            values: dict[str, int] = {}
            for field_name, input_widget in self.danjeon_inputs.inputs.items():
                text: str = input_widget.text()
                if not text.isdigit():
                    input_widget.set_valid(False)
                    is_valid = False
                    values[field_name] = 0
                    continue

                input_widget.set_valid(True)
                values[field_name] = int(text)

            danjeon_state: DanjeonState = DanjeonState(
                upper=values["upper"],
                middle=values["middle"],
                lower=values["lower"],
                is_locked=False,
                use_reset=False,
            )
            return is_valid, danjeon_state

        def _read_optimization_state(
            self,
        ) -> tuple[
            bool,
            DistributionState,
            DanjeonState,
            list[OwnedTitle],
            EquippedOptimizationState,
            list[OwnedTalisman],
        ]:
            """현재 최적화 입력 상태 전체 복원"""

            distribution_valid: bool
            distribution_state: DistributionState
            distribution_valid, distribution_state = self._read_distribution_state()

            danjeon_valid: bool
            danjeon_state: DanjeonState
            danjeon_valid, danjeon_state = self._read_danjeon_state()

            title_valid: bool
            owned_titles: list[OwnedTitle]
            equipped_title_id: str | None
            title_valid, owned_titles, equipped_title_id = (
                self.title_inputs.build_state()
            )

            talisman_valid: bool
            owned_talismans: list[OwnedTalisman]
            equipped_talisman_ids: list[str]
            talisman_valid, owned_talismans, equipped_talisman_ids = (
                self.talisman_inputs.build_state()
            )

            equipped_state: EquippedOptimizationState = EquippedOptimizationState(
                equipped_title_id=equipped_title_id,
                equipped_talisman_ids=equipped_talisman_ids,
            )
            is_valid: bool = (
                distribution_valid and danjeon_valid and title_valid and talisman_valid
            )
            return (
                is_valid,
                distribution_state,
                danjeon_state,
                owned_titles,
                equipped_state,
                owned_talismans,
            )

        def _read_overall_stats(self) -> tuple[bool, dict[str, float]]:
            """전체 스탯 입력 복원 및 검증"""

            # 모든 입력칸을 순회하며 실수 입력 복원
            parsed_stats: dict[str, float] = {}
            is_valid: bool = True
            for stat_key, input_widget in self.stats_inputs.inputs.items():
                try:
                    value: float = float(input_widget.text())
                    input_widget.set_valid(True)

                except ValueError:
                    value = 0.0
                    is_valid = False
                    input_widget.set_valid(False)

                parsed_stats[stat_key.value] = value

            return is_valid, parsed_stats

        def _read_custom_stat_changes(self) -> tuple[bool, dict[StatKey, float]]:
            """사용자 지정 스탯 변화량 복원 및 검증"""

            # 0 입력 포함 전체 변화량 맵 구성
            parsed_changes: dict[StatKey, float] = {}
            is_valid: bool = True
            for stat_key, input_widget in self.custom_delta_inputs.inputs.items():
                try:
                    value: float = float(input_widget.text())
                    input_widget.set_valid(True)

                except ValueError:
                    value = 0.0
                    is_valid = False
                    input_widget.set_valid(False)

                if value == 0.0:
                    continue

                parsed_changes[stat_key] = value

            return is_valid, parsed_changes

        def _read_level(self) -> tuple[bool, int]:
            """레벨 입력 복원 및 검증"""

            # 레벨은 정수 입력만 허용
            text: str = self.level_input.text()
            if not text.isdigit():
                self.level_input.set_valid(False)
                return False, 0

            self.level_input.set_valid(True)
            level: int = int(text)
            return True, level

        def _read_scroll_levels(self) -> bool:
            """스크롤 레벨 입력 검증 및 저장"""

            # 모든 스크롤 레벨을 현재 프리셋에 직접 반영
            all_valid: bool = True
            for input_widget, entry in zip(self.skills.inputs, self.skills.entries):
                text: str = input_widget.text()
                is_valid: bool = text.isdigit() and (
                    1 <= int(text) <= app_state.macro.current_server.max_skill_level
                )
                input_widget.set_valid(is_valid)
                all_valid = all_valid and is_valid

                if not is_valid:
                    continue

                self._get_preset().info.set_scroll_level(entry.scroll_id, int(text))

            return all_valid

        def _format_delta(self, value: float) -> str:
            """전투력 변화량 표시 문자열 생성"""

            # 큰 수치도 읽기 쉽게 고정 포맷 적용
            return f"{value:+,.2f}"

        def _format_current_power(self, value: float) -> str:
            """현재 전투력 표시 문자열 생성"""

            return f"{value:,.2f}"

        def _save_base_inputs(
            self,
            overall_stats: dict[str, float],
            level: int,
        ) -> None:
            """기준 입력 상태 저장"""

            # 계산기 입력 블록에 현재 기준 입력 반영
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            calculator_input.overall_stats = overall_stats
            calculator_input.level = level
            calculator_input.realm_tier = self.realm_options[
                self.realm_combobox.currentIndex()
            ]
            save_data()

        def _save_optimization_inputs(
            self,
            distribution_state: DistributionState,
            danjeon_state: DanjeonState,
            owned_titles: list[OwnedTitle],
            equipped_state: EquippedOptimizationState,
            owned_talismans: list[OwnedTalisman],
        ) -> None:
            """최적화 입력 상태 저장"""

            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            calculator_input.distribution = distribution_state
            calculator_input.danjeon = danjeon_state
            calculator_input.owned_titles = owned_titles
            calculator_input.equipped = equipped_state
            calculator_input.owned_talismans = owned_talismans
            save_data()

        def _set_error_outputs(self) -> None:
            """기준 입력 오류 상태 출력"""

            error_rows: list[tuple[str, str]] = [("상태", "오류")]
            self.current_power_list.set_rows(error_rows)
            self.stat_efficiency_list.set_rows(error_rows)
            self.level_up_list.set_rows(error_rows)
            self.realm_up_list.set_rows(error_rows)
            self.scroll_efficiency_list.set_rows(error_rows)
            self.base_state_list.set_rows(error_rows)

        def _refresh_base_outputs(self) -> None:
            """기준 입력 기반 효율 출력 갱신"""

            # 전체 스탯, 레벨, 스크롤 레벨 입력 유효성 확인
            stats_valid: bool
            overall_stats: dict[str, float]
            stats_valid, overall_stats = self._read_overall_stats()

            level_valid: bool
            level: int
            level_valid, level = self._read_level()

            scroll_valid: bool = self._read_scroll_levels()

            if not (stats_valid and level_valid and scroll_valid):
                self._set_error_outputs()
                return

            # 저장 후 현재 프리셋 기준 컨텍스트 계산
            self._save_base_inputs(overall_stats, level)
            context: CalculatorEvaluationContext = build_calculator_context(
                server_spec=app_state.macro.current_server,
                preset=self._get_preset(),
                skills_info=self._get_preset().usage_settings,
                delay_ms=app_state.macro.current_delay,
                overall_stats=overall_stats,
            )
            selected_metric: PowerMetric = self._get_selected_metric()

            # 현재 전투력 표시 행 구성
            current_power_rows: list[tuple[str, str]] = []
            for power_metric in DISPLAY_POWER_METRICS:
                current_power_rows.append(
                    (
                        POWER_METRIC_LABELS[power_metric],
                        self._format_current_power(
                            context.baseline_summary.metrics[power_metric]
                        ),
                    )
                )
            self.current_power_list.set_rows(current_power_rows)

            # 스탯 1당 효율 행 구성
            stat_rows: list[tuple[str, str]] = []
            for stat_key, stat_spec in CALCULATOR_STAT_SPECS.items():
                amount: float = 1.0
                deltas: dict[PowerMetric, float] = evaluate_single_stat_delta(
                    context=context,
                    overall_stats=overall_stats,
                    stat_key=stat_key,
                    amount=amount,
                )

                label: str = stat_spec.label
                if stat_spec.is_percent:
                    label = f"{label}(%) +1"
                else:
                    label = f"{label} +1"

                stat_rows.append((label, self._format_delta(deltas[selected_metric])))

            # 선택 전투력 기준 내림차순 정렬
            stat_rows.sort(
                key=lambda row: float(row[1].replace(",", "")),
                reverse=True,
            )
            self.stat_efficiency_list.set_rows(stat_rows)

            # 레벨 1업 효율 행 구성
            level_up: LevelUpEvaluation = evaluate_level_up_delta(
                context=context,
                overall_stats=overall_stats,
                target_metric=selected_metric,
            )

            level_distribution_text: str = (
                f"힘 {level_up.stat_distribution[StatKey.STR]}, "
                f"민첩 {level_up.stat_distribution[StatKey.DEXTERITY]}, "
                f"생명력 {level_up.stat_distribution[StatKey.VITALITY]}, "
                f"행운 {level_up.stat_distribution[StatKey.LUCK]}"
            )

            self.level_up_list.set_rows(
                [
                    ("레벨 1업", self._format_delta(level_up.deltas[selected_metric])),
                    ("최적 분배", level_distribution_text),
                ]
            )

            # 다음 경지 효율 행 구성
            realm_result: RealmAdvanceEvaluation | None = evaluate_next_realm_delta(
                context=context,
                overall_stats=overall_stats,
                current_realm=self.realm_options[self.realm_combobox.currentIndex()],
                level=level,
                target_metric=selected_metric,
            )

            if realm_result is None:
                self.realm_up_list.set_rows([("다음 경지", "불가")])
            else:
                danjeon_text: str = (
                    f"상 {realm_result.danjeon_distribution[0]}, "
                    f"중 {realm_result.danjeon_distribution[1]}, "
                    f"하 {realm_result.danjeon_distribution[2]}"
                )

                self.realm_up_list.set_rows(
                    [
                        (
                            REALM_TIER_SPECS[realm_result.target_realm].label,
                            self._format_delta(realm_result.deltas[selected_metric]),
                        ),
                        ("최적 분배", danjeon_text),
                    ]
                )

            # 스크롤 +1 효율 행 구성
            scroll_rows: list[tuple[str, str]] = []
            scroll_results: list[ScrollUpgradeEvaluation] = (
                evaluate_scroll_upgrade_deltas(
                    server_spec=app_state.macro.current_server,
                    preset=self._get_preset(),
                    skills_info=self._get_preset().usage_settings,
                    delay_ms=app_state.macro.current_delay,
                    overall_stats=overall_stats,
                )
            )
            for scroll_result in scroll_results:
                scroll_rows.append(
                    (
                        f"{scroll_result.scroll_name} Lv.{scroll_result.next_level}",
                        self._format_delta(scroll_result.deltas[selected_metric]),
                    )
                )

            # 선택 전투력 기준 내림차순 정렬
            scroll_rows.sort(
                key=lambda row: float(row[1].replace(",", "")),
                reverse=True,
            )
            self.scroll_efficiency_list.set_rows(scroll_rows)

            # 현재 선택 입력 기반 기준 상태 분리 결과 표시
            optimization_valid: bool
            distribution_state: DistributionState
            danjeon_state: DanjeonState
            owned_titles: list[OwnedTitle]
            equipped_state: EquippedOptimizationState
            owned_talismans: list[OwnedTalisman]
            (
                optimization_valid,
                distribution_state,
                danjeon_state,
                owned_titles,
                equipped_state,
                owned_talismans,
            ) = self._read_optimization_state()
            if not optimization_valid:
                self.base_state_list.set_rows([("상태", "입력 오류")])
                return

            self._save_optimization_inputs(
                distribution_state=distribution_state,
                danjeon_state=danjeon_state,
                owned_titles=owned_titles,
                equipped_state=equipped_state,
                owned_talismans=owned_talismans,
            )
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            validation: CalculatorBaseValidation = validate_base_state(
                overall_stats=overall_stats,
                calculator_input=calculator_input,
            )
            if not validation.is_valid:
                self.base_state_list.set_rows(
                    [("상태", "오류"), ("사유", validation.message)]
                )
                return

            base_state: CalculatorBaseState = build_base_state(
                overall_stats=overall_stats,
                calculator_input=calculator_input,
            )
            self.base_state_list.set_rows(
                [
                    ("상태", "정상"),
                    (
                        "기준 공격력",
                        self._format_current_power(
                            base_state.base_overall_stats[StatKey.ATTACK.value]
                        ),
                    ),
                    (
                        "기준 체력",
                        self._format_current_power(
                            base_state.base_overall_stats[StatKey.HP.value]
                        ),
                    ),
                ]
            )

        def _refresh_custom_delta_output(self) -> None:
            """사용자 지정 스탯 변화량 출력 갱신"""

            # 기준 입력 또는 변화량 입력이 유효하지 않으면 오류 출력
            stats_valid: bool
            overall_stats: dict[str, float]
            stats_valid, overall_stats = self._read_overall_stats()

            level_valid: bool
            level_valid, _ = self._read_level()

            custom_valid: bool
            custom_changes: dict[StatKey, float]
            custom_valid, custom_changes = self._read_custom_stat_changes()

            scroll_valid: bool = self._read_scroll_levels()

            if not (stats_valid and level_valid and custom_valid and scroll_valid):
                self.custom_delta_result_list.set_rows([("상태", "오류")])
                return

            # 현재 기준 컨텍스트와 변화량 계산 결과 구성
            context: CalculatorEvaluationContext = build_calculator_context(
                server_spec=app_state.macro.current_server,
                preset=self._get_preset(),
                skills_info=self._get_preset().usage_settings,
                delay_ms=app_state.macro.current_delay,
                overall_stats=overall_stats,
            )

            deltas: dict[PowerMetric, float] = evaluate_arbitrary_stat_delta(
                context=context,
                overall_stats=overall_stats,
                stat_changes=custom_changes,
            )
            rows: list[tuple[str, str]] = []
            for power_metric in DISPLAY_POWER_METRICS:
                rows.append(
                    (
                        POWER_METRIC_LABELS[power_metric],
                        self._format_delta(deltas[power_metric]),
                    )
                )
            self.custom_delta_result_list.set_rows(rows)

        def on_optimization_input_changed(self) -> None:
            """최적화 입력 변경 시 기준 상태 분리 갱신"""

            self.title_inputs.refresh_equipped_options()
            self.talisman_inputs.refresh_equipped_options()
            self._refresh_base_outputs()

        def on_base_input_changed(self) -> None:
            """기준 입력 변경 시 전체 효율 출력 갱신"""

            # 기준 입력 변화 시 기준 출력과 사용자 지정 출력 동시 갱신
            self._refresh_base_outputs()
            self._refresh_custom_delta_output()

        def on_custom_delta_changed(self) -> None:
            """사용자 지정 변화량 변경 시 결과 갱신"""

            self._refresh_custom_delta_output()

    class Additional(QFrame):
        def __init__(self, parent: QFrame) -> None:
            super().__init__(parent)

            if config.ui.debug_colors:
                self.setStyleSheet(
                    "QFrame { background-color: green; border: 0px solid; }"
                )
            else:
                self.setStyleSheet(
                    "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
                )

            stat_data: dict[str, str] = {
                spec.label: "0" for spec in config.specs.STATS.values()
            }
            self.stats = StatInputs(self, stat_data, self.on_stat_changed)

            skill_input_specs: list[SkillLevelInputSpec] = (
                build_skill_level_input_specs()
            )
            self.skills: SkillInputs = SkillInputs(
                self,
                skill_input_specs,
                self.on_skill_changed,
            )

            self.power_labels = PowerLabels(self)
            self.update_powers()

            layout = QVBoxLayout(self)
            layout.addWidget(self.stats)
            layout.addWidget(self.skills)
            layout.addWidget(self.power_labels)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # todo: on_stat_changed, on_skill_changed를 합쳐서 하나로 만들기
        def on_stat_changed(self) -> None:
            # 스탯이 정상적으로 입력되었는지 확인
            # 음수도 허용
            def checkInput(num: int, text: str) -> bool:
                try:
                    value = int(text)

                except ValueError:
                    return False

                name: str = list(config.specs.STATS.keys())[num]
                stat: float = (
                    app_state.simulation.stats.get_stat_from_name(name) + value
                )

                return (
                    config.specs.STATS[name].min <= stat <= config.specs.STATS[name].max
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
                app_state.simulation.is_input_valid["sim3_stat"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                app_state.simulation.is_input_valid["sim3_stat"] = False

            self.update_powers()

        def on_skill_changed(self) -> None:
            # 스킬이 정상적으로 입력되었는지 확인
            def checkInput(text: str) -> bool:
                if not text.isdigit():
                    return False

                return 1 <= int(text) <= app_state.macro.current_server.max_skill_level

            # 모두 통과 여부 확인
            all_valid = True
            for j in self.skills.inputs:
                is_valid: bool = checkInput(j.text())

                # 스타일 업데이트
                j.set_valid(is_valid)

                # 전체 유효 여부 업데이트
                all_valid: bool = all_valid and is_valid

            # 모두 통과했다면 저장 및 플래그 설정
            if all_valid:
                app_state.simulation.is_input_valid["sim3_skill"] = True

            # 하나라도 통과하지 못했다면 플래그 설정
            else:
                app_state.simulation.is_input_valid["sim3_skill"] = False

            self.update_powers()

        def update_powers(self) -> None:
            # 입력이 모두 정상인지 확인
            if not all(
                app_state.simulation.is_input_valid[k]
                for k in ("sim3_stat", "sim3_skill")
            ):
                self.power_labels.set_texts("오류")

                return

            # 모든 입력이 정상이라면 계산 시작
            # 스탯 적용
            stats: Stats = app_state.simulation.stats.copy()
            for i in self.stats.inputs:
                stats.add_stat_from_index(self.stats.inputs.index(i), int(i.text()))

            # 스킬 적용
            # todo: 스킬 레벨을 적용시킬 때 다시 사용
            # skills: list[SkillSetting] = [
            #     replace(app_state.skill.settings[skill], level=int(j.text()))
            #     for j, skill in zip(
            #         self.skills.inputs,
            #         app_state.macro.current_server.skill_registry.get_all_skill_ids(),
            #     )
            # ]

            # 전투력 계산
            powers: list[float] = simulate_deterministic(
                stats,
                app_state.simulation.sim_details,
                app_state.macro.current_preset.usage_settings,
            ).powers

            # 차이 계산
            diff_powers: list[float] = [
                powers[i] - app_state.simulation.powers[i] for i in range(4)
            ]

            # 텍스트 설정
            texts: list[str] = [
                f"{int(powers[i]):}\n({diff_powers[i]:+.0f}, {diff_powers[i] / app_state.simulation.powers[i]:+.1%})"
                for i in range(4)
            ]
            self.power_labels.set_texts(texts)

    class Potential(QFrame):
        def __init__(
            self,
            parent: QFrame,
        ) -> None:
            super().__init__(parent)

            if config.ui.debug_colors:
                self.setStyleSheet(
                    "QFrame { background-color: green; border: 0px solid; }"
                )
            else:
                self.setStyleSheet(
                    "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
                )

            potential_options: list[str] = [
                f"{spec.label} +{value}"
                for spec in config.specs.STATS.values()
                if spec.potential
                for value in spec.potential.values
            ]

            self.option_comboboxes: list[CustomComboBox] = [
                CustomComboBox(
                    self,
                    potential_options,
                    self.update_values,
                )
                for _ in range(3)
            ]

            combobox_layout = QVBoxLayout()
            for combobox in self.option_comboboxes:
                combobox_layout.addWidget(combobox)
            combobox_layout.setSpacing(5)
            combobox_layout.setContentsMargins(0, 0, 0, 0)

            self.power_labels = PowerLabels(self)

            layout = QHBoxLayout(self)
            layout.addLayout(combobox_layout)
            layout.addWidget(self.power_labels)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            self.update_values()

        def update_values(self) -> None:
            # 선택된 옵션들 가져오기
            options: list[str] = [
                self.option_comboboxes[i].currentText() for i in range(3)
            ]

            # 스탯에 옵션들 적용
            stats: Stats = app_state.simulation.stats.copy()
            for opt in options:
                # 옵션 파싱
                stat_ko, value = opt.split(" +")
                value_int: int = int(value)

                # 한글 스탯 이름을 영어 이름으로 변환
                stat: str = ""
                for name_en, spec in config.specs.STATS.items():
                    if spec.label == stat_ko:
                        stat: str = name_en
                        break

                if not stat:
                    continue

                # 스탯 적용
                stats.add_stat_from_name(stat, value_int)

            powers: list[float] = simulate_deterministic(
                stats,
                app_state.simulation.sim_details,
                app_state.macro.current_preset.usage_settings,
            ).powers

            diff_powers: list[str] = [
                f"{powers[i] - app_state.simulation.powers[i]:+.0f}" for i in range(4)
            ]

            self.power_labels.set_texts(diff_powers)


class StatInputs(QFrame):
    def __init__(
        self,
        mainframe: QWidget,
        stats_data: dict[str, str],
        connected_function: Callable[[], None],
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
            item_widget = KVInput(self, name, value, connected_function)

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
        entries: list[SkillLevelInputSpec],
        connected_function: Callable[[], None],
    ) -> None:
        super().__init__(mainframe)

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: green; border: 0px solid; }")

        # 그리드 레이아웃 위젯 생성
        grid_layout: QGridLayout = QGridLayout(self)

        # 아이템을 저장할 리스트
        self.entries: list[SkillLevelInputSpec] = entries
        self.inputs: list[CustomLineEdit] = []

        # column 수 설정
        cols: int = 7
        for i, entry in enumerate(self.entries):
            item_widget: SkillInputs.SkillInput = self.SkillInput(
                self,
                entry,
                connected_function,
            )

            # 위치 계산
            row: int = i // cols
            column: int = i % cols

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
            parent: QWidget,
            entry: SkillLevelInputSpec,
            connected_function: Callable[[], None],
        ) -> None:
            super().__init__(parent)

            if config.ui.debug_colors:
                self.setStyleSheet(
                    "QFrame { background-color: orange; border: 0px solid; }"
                )

            # 전체 layout 설정
            grid: QGridLayout = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)

            # 레이블
            label: QLabel = QLabel(entry.title, self)
            label.setStyleSheet(f"QLabel {{ border: 0px solid; border-radius: 4px; }}")
            label.setFont(CustomFont(14))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 레벨 입력
            level_input: KVInput = KVInput(
                self,
                "레벨",
                str(entry.value),
                connected_function,
                max_width=40,
            )

            # 스크롤 아이콘 우선, 없으면 개별 스킬 아이콘 사용
            icon_size: int = level_input.sizeHint().height()
            icon_pixmap: QPixmap = resource_registry.get_scroll_pixmap(entry.scroll_id)
            image: SkillImage = SkillImage(
                self,
                icon_pixmap,
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
        self,
        mainframe: QWidget,
        stats_data: dict[str, str],
        connected_function: Callable[[], None],
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
            item_widget = KVInput(self, name, value, connected_function)

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
                config.simulation.power_titles[i],
                texts[i],
                config.ui.sim_colors4[i],
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
    def __init__(self, mainframe, analysis: list[SimAnalysis]):
        super().__init__(mainframe)

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
                config.simulation.power_details,
                config.ui.sim_colors4[i],
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
            statistics: tuple[str, ...],
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
    def __init__(
        self,
        mainframe: QWidget,
    ) -> None:
        super().__init__(mainframe)

        texts: list[list[list[str]]] = self.get_potential_rank()
        colors: list[str] = ["#8CFFA386", "#59FF9800", "#4D2196F3", "#B3A5D6A7"]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        for i in range(4):
            rank = self.Rank(
                self,
                config.simulation.power_titles[i],
                texts[i],
                config.ui.sim_colors4[i],
                colors[i],
            )

            layout.addWidget(rank)

    def get_potential_rank(
        self,
    ) -> list[list[list[str]]]:
        options: list[list[tuple[str, float]]] = [[], [], [], []]

        for stat, spec in config.specs.STATS.items():
            if not spec.potential:
                continue

            for value in spec.potential.values:
                key: str = f"{spec.label} +{value}"

                stats: Stats = app_state.simulation.stats.copy()
                stats.add_stat_from_name(stat, value)

                powers: list[float] = simulate_deterministic(
                    stats,
                    app_state.simulation.sim_details,
                    app_state.macro.current_preset.usage_settings,
                ).powers

                diff_powers: list[float] = [
                    round(powers[i] - app_state.simulation.powers[i], 5)
                    for i in range(4)
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
