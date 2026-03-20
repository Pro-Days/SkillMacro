from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
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
    build_base_state,
    build_calculator_context,
    evaluate_arbitrary_stat_delta,
    evaluate_level_up_delta,
    evaluate_next_realm_delta,
    evaluate_scroll_upgrade_deltas,
    evaluate_single_stat_delta,
    optimize_current_selection,
    validate_base_state,
)
from app.scripts.calculator_models import (
    OVERALL_STAT_GRID_ROWS,
    REALM_TIER_SPECS,
    STAT_SPECS,
    TALISMAN_SPECS,
    BaseStats,
    DanjeonState,
    DistributionState,
    EquippedState,
    OwnedTalisman,
    OwnedTitle,
    StatKey,
)
from app.scripts.config import config
from app.scripts.custom_classes import (
    CustomComboBox,
    CustomFont,
    CustomLineEdit,
    KVInput,
    SkillImage,
)
from app.scripts.data_manager import save_data
from app.scripts.registry.resource_registry import (
    convert_resource_path,
    resource_registry,
)
from app.scripts.simulate_macro import simulate_random_from_calculator
from app.scripts.ui.popup import NoticeKind, PopupManager
from app.scripts.ui.sim_ui.graph import (
    DMGCanvas,
    DpmDistributionCanvas,
    SkillContributionCanvas,
    SkillDpsRatioCanvas,
)

if TYPE_CHECKING:
    from app.scripts.calculator_engine import (
        BaseState,
        BaseValidation,
        EvaluationContext,
        GraphAnalysis,
        GraphDamageEvent,
        GraphReport,
        LevelUpEvaluation,
        OptimizationResult,
        RealmAdvanceEvaluation,
        ScrollUpgradeEvaluation,
    )
    from app.scripts.calculator_models import (
        CalculatorPresetInput,
        PowerMetric,
        RealmTier,
        TalismanSpec,
    )
    from app.scripts.macro_models import MacroPreset
    from app.scripts.registry.server_registry import ServerSpec
    from app.scripts.ui.main_window import MainWindow
    from app.scripts.ui.popup import HoverCardData


class SimUI:
    def __init__(self, master: MainWindow, parent: QFrame):

        # parent: page2
        self.parent: QFrame = parent
        self.master: MainWindow = master
        self.popup_manager: PopupManager = self.master.get_popup_manager()

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

        self.input_page = InputPage(self.main_frame, self.popup_manager)
        self.graph_page = GraphPage(self.main_frame)
        self.results_page = ResultsPage(self.main_frame)

        self.stacked_layout.addWidget(self.input_page)
        self.stacked_layout.addWidget(self.graph_page)
        self.stacked_layout.addWidget(self.results_page)

        self.stacked_layout.setCurrentIndex(0)
        # 스택 레이아웃 설정
        self.main_frame.setLayout(self.stacked_layout)

        self.adjust_main_frame_height()

    def change_layout(self, index: int) -> None:
        # 입력값 확인
        if (
            index in (1, 2, 3)
            and not self.input_page.editor.has_valid_navigation_inputs()
        ):
            self.master.get_popup_manager().show_notice(NoticeKind.SIM_INPUT_ERROR)

            return

        if index == self.stacked_layout.currentIndex():
            return

        # 그래프 페이지 진입 직전 현재 계산기 입력 기준 결과 재생성
        if index == 1:
            self.graph_page.refresh()

        # 결과 페이지 진입 직전 저장된 계산기 상태 기준 재동기화
        if index == 2:
            self.results_page.sync_from_preset()

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


class InputPage(QFrame):
    def __init__(
        self,
        parent: QFrame,
        popup_manager: PopupManager,
    ) -> None:
        super().__init__(parent)

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: gray;}")

        # 계산기 입력 화면 구성
        self.input_title: Title = Title(parent=self, text="계산기 입력")
        self.editor: ResultsPage.Efficiency = ResultsPage.Efficiency(
            self,
            popup_manager,
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.input_title)
        layout.addWidget(self.editor)

        # 레이아웃 여백과 간격 설정
        layout.setSpacing(10)  # 위젯들 사이의 간격
        layout.setContentsMargins(10, 10, 10, 10)  # 레이아웃의 여백
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class GraphPage(QFrame):
    def __init__(
        self,
        parent: QFrame,
    ) -> None:
        super().__init__(parent)

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: gray;}")

        # 그래프 페이지 전체 레이아웃 준비
        self.main_layout: QVBoxLayout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.main_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _clear_layout(self, target_layout: QVBoxLayout | QHBoxLayout) -> None:
        """기존 그래프 페이지 위젯 정리"""

        # 중첩 레이아웃까지 포함한 기존 위젯 트리 순차 제거
        while target_layout.count():
            child_item: QLayoutItem = target_layout.takeAt(0)
            child_widget: QWidget | None = child_item.widget()
            child_layout: QLayoutItem | None = None
            nested_layout: QLayout | None = child_item.layout()

            if nested_layout is not None:
                while nested_layout.count():
                    child_layout = nested_layout.takeAt(0)
                    nested_widget: QWidget | None = child_layout.widget()
                    if nested_widget is not None:
                        nested_widget.deleteLater()

            if child_widget is not None:
                child_widget.deleteLater()

    def refresh(self) -> None:
        """현재 계산기 입력 기준 그래프 페이지 재구성"""

        # 직전 그래프/라벨 위젯 전부 제거
        self._clear_layout(self.main_layout)

        # 현재 프리셋 계산기 입력 기준 시뮬레이션 결과 계산
        calculator_input: CalculatorPresetInput = (
            app_state.macro.current_preset.info.calculator
        )
        graph_report: GraphReport = simulate_random_from_calculator(
            server_spec=app_state.macro.current_server,
            preset=app_state.macro.current_preset,
            skills_info=app_state.macro.current_preset.usage_settings,
            delay_ms=app_state.macro.current_delay,
            base_stats=calculator_input.base_stats,
        )
        powers: list[float] = [
            graph_report.metrics[power_metric] for power_metric in DISPLAY_POWER_METRICS
        ]
        analysis: list[GraphAnalysis] = list(graph_report.analysis)
        deterministic_attacks: list[GraphDamageEvent] = list(
            graph_report.deterministic_boss_attacks
        )
        results: list[list[GraphDamageEvent]] = [
            list(result_row) for result_row in graph_report.random_boss_attacks
        ]
        str_powers: list[str] = [str(int(power)) for power in powers]
        power_titles: list[str] = [
            POWER_METRIC_LABELS[power_metric] for power_metric in DISPLAY_POWER_METRICS
        ]

        # 전투력/분석/그래프 위젯 재생성
        power_title: Title = Title(self, "전투력")
        power: PowerLabels = PowerLabels(self, power_titles, str_powers)
        analysis_title: Title = Title(self, "분석")
        analysis_widget: AnalysisDetails = AnalysisDetails(self, analysis)
        dpm_graph: GraphPage.DPMGraph = self.DPMGraph(self, results)
        ratio_graph: GraphPage.RatioGraph = self.RatioGraph(self, deterministic_attacks)
        dps_graph: GraphPage.DPSGraph = self.DPSGraph(self, results)
        total_graph: GraphPage.TotalGraph = self.TotalGraph(self, results)
        contribution_graph: GraphPage.ContributionGraph = self.ContributionGraph(
            self,
            deterministic_attacks,
        )

        # 상단 2개 그래프 묶음 레이아웃 구성
        sub_layout: QHBoxLayout = QHBoxLayout()
        sub_layout.addWidget(dpm_graph)
        sub_layout.addWidget(ratio_graph)
        sub_layout.setSpacing(10)
        sub_layout.setContentsMargins(10, 10, 10, 10)

        # 메인 레이아웃에 최신 위젯 트리 추가
        self.main_layout.addWidget(power_title)
        self.main_layout.addWidget(power)
        self.main_layout.addWidget(analysis_title)
        self.main_layout.addWidget(analysis_widget)
        self.main_layout.addLayout(sub_layout)
        self.main_layout.addWidget(dps_graph)
        self.main_layout.addWidget(total_graph)
        self.main_layout.addWidget(contribution_graph)

    class DPMGraph(QFrame):
        def __init__(
            self,
            parent: QFrame,
            results: list[list[GraphDamageEvent]],
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
            deterministic_attacks: list[GraphDamageEvent],
        ) -> None:
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = SkillDpsRatioCanvas(
                self,
                deterministic_attacks,
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
            results: list[list[GraphDamageEvent]],
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
            results: list[list[GraphDamageEvent]],
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
            deterministic_attacks: list[GraphDamageEvent],
        ) -> None:
            super().__init__(parent)

            self.setStyleSheet(
                "QFrame { background-color: #F8F8F8; border: 1px solid #CCCCCC; border-radius: 10px; }"
            )

            self.graph = SkillContributionCanvas(
                self,
                deterministic_attacks,
                app_state.macro.current_preset.skills.get_placed_skill_ids(),
                app_state.macro.current_server.id,
            )
            self.graph.setFixedHeight(400)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(self.graph)
            self.setLayout(layout)


class ResultsPage(QFrame):
    @dataclass(frozen=True)
    class OutputRows:
        """계산기 결과 섹션별 출력 행 묶음"""

        current_power: list[tuple[str, str]]
        stat_efficiency: list[tuple[str, str]]
        level_up: list[tuple[str, str]]
        realm_up: list[tuple[str, str]]
        scroll_efficiency: list[tuple[str, str]]
        custom_delta: list[tuple[str, str]]
        base_state: list[tuple[str, str]]
        optimization_result: list[tuple[str, str]]

    def __init__(
        self,
        parent: QFrame,
    ) -> None:
        super().__init__(parent)

        # 스탯 효율 계산
        self.efficiency_title: Title = Title(self, "스탯 효율 계산")
        self.view: ResultsPage.ResultsView = self.ResultsView(self)

        layout = QVBoxLayout(self)

        layout.addWidget(self.efficiency_title)
        layout.addWidget(self.view)

        # 레이아웃 여백과 간격 설정
        layout.setSpacing(10)  # 위젯들 사이의 간격
        layout.setContentsMargins(10, 10, 10, 10)  # 레이아웃의 여백
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sync_from_preset(self) -> None:
        """저장된 계산기 상태를 결과 페이지에 동기화"""

        self.view.refresh_from_preset()

    @staticmethod
    def _format_delta(value: float) -> str:
        """전투력 변화량 표시 문자열 생성"""

        return f"{value:+,.2f}"

    @staticmethod
    def _format_current_power(value: float) -> str:
        """현재 전투력 표시 문자열 생성"""

        return f"{value:,.2f}"

    @classmethod
    def _build_output_rows(
        cls,
        server_spec: "ServerSpec",
        preset: "MacroPreset",
        delay_ms: int,
        base_stats: BaseStats,
        level: int,
        selected_metric: "PowerMetric",
        current_realm: "RealmTier",
        calculator_input: CalculatorPresetInput,
        context: "EvaluationContext",
    ) -> "ResultsPage.OutputRows":
        """공용 계산기 결과 행 구성"""

        # 현재 전투력 출력 행 구성
        current_power_rows: list[tuple[str, str]] = []
        for power_metric in DISPLAY_POWER_METRICS:
            current_power_rows.append(
                (
                    POWER_METRIC_LABELS[power_metric],
                    cls._format_current_power(
                        context.baseline_summary.metrics[power_metric]
                    ),
                )
            )

        # 스탯 1당 효율 출력 행 구성
        stat_rows: list[tuple[str, str]] = []
        for stat_key, stat_label in STAT_SPECS.items():
            deltas: dict[PowerMetric, float] = evaluate_single_stat_delta(
                context=context,
                base_stats=base_stats,
                stat_key=stat_key,
                amount=1.0,
            )
            label: str = f"{stat_label} +1"

            stat_rows.append((label, cls._format_delta(deltas[selected_metric])))

        stat_rows.sort(
            key=lambda row: float(row[1].replace(",", "")),
            reverse=True,
        )

        # 레벨 1업 효율 출력 행 구성
        level_up: LevelUpEvaluation = evaluate_level_up_delta(
            context=context,
            base_stats=base_stats,
            target_metric=selected_metric,
        )
        level_distribution_text: str = (
            f"힘 {level_up.stat_distribution[StatKey.STR]}, "
            f"민첩 {level_up.stat_distribution[StatKey.DEXTERITY]}, "
            f"생명력 {level_up.stat_distribution[StatKey.VITALITY]}, "
            f"행운 {level_up.stat_distribution[StatKey.LUCK]}"
        )
        level_up_rows: list[tuple[str, str]] = [
            ("레벨 1업", cls._format_delta(level_up.deltas[selected_metric])),
            ("최적 분배", level_distribution_text),
        ]

        # 다음 경지 효율 출력 행 구성
        realm_result: RealmAdvanceEvaluation | None = evaluate_next_realm_delta(
            context=context,
            base_stats=base_stats,
            current_realm=current_realm,
            level=level,
            target_metric=selected_metric,
        )
        if realm_result is None:
            realm_rows: list[tuple[str, str]] = [("다음 경지", "불가")]
        else:
            danjeon_text: str = (
                f"상 {realm_result.danjeon_distribution[0]}, "
                f"중 {realm_result.danjeon_distribution[1]}, "
                f"하 {realm_result.danjeon_distribution[2]}"
            )
            realm_rows = [
                (
                    REALM_TIER_SPECS[realm_result.target_realm].label,
                    cls._format_delta(realm_result.deltas[selected_metric]),
                ),
                ("최적 분배", danjeon_text),
            ]

        # 스크롤 +1 효율 출력 행 구성
        scroll_rows: list[tuple[str, str]] = []
        scroll_results: list[ScrollUpgradeEvaluation] = evaluate_scroll_upgrade_deltas(
            server_spec=server_spec,
            preset=preset,
            skills_info=preset.usage_settings,
            delay_ms=delay_ms,
            base_stats=base_stats,
        )
        for scroll_result in scroll_results:
            scroll_rows.append(
                (
                    f"{scroll_result.scroll_name} Lv.{scroll_result.next_level}",
                    cls._format_delta(scroll_result.deltas[selected_metric]),
                )
            )

        scroll_rows.sort(
            key=lambda row: float(row[1].replace(",", "")),
            reverse=True,
        )

        # 사용자 지정 변화량 결과 행 공용 구성
        custom_rows: list[tuple[str, str]] = cls._build_custom_delta_rows(
            base_stats=base_stats,
            calculator_input=calculator_input,
            context=context,
        )

        # 기준 상태 분리 결과 행 구성
        validation: BaseValidation = validate_base_state(
            base_stats=base_stats,
            calculator_input=calculator_input,
        )
        if not validation.is_valid:
            return cls.OutputRows(
                current_power=current_power_rows,
                stat_efficiency=stat_rows,
                level_up=level_up_rows,
                realm_up=realm_rows,
                scroll_efficiency=scroll_rows,
                custom_delta=custom_rows,
                base_state=[("상태", "오류"), ("사유", validation.message)],
                optimization_result=[("상태", "불가")],
            )

        base_state: BaseState = build_base_state(
            base_stats=base_stats,
            calculator_input=calculator_input,
        )
        base_state_rows: list[tuple[str, str]] = [
            ("상태", "정상"),
            (
                "기준 공격력",
                cls._format_current_power(
                    base_state.final_stats.values[StatKey.ATTACK]
                ),
            ),
            (
                "기준 체력",
                cls._format_current_power(base_state.final_stats.values[StatKey.HP]),
            ),
        ]

        # 최적화 결과 행 구성
        optimization_result: OptimizationResult | None = optimize_current_selection(
            server_spec=server_spec,
            preset=preset,
            skills_info=preset.usage_settings,
            delay_ms=delay_ms,
            context=context,
            base_stats=base_stats,
            calculator_input=calculator_input,
            target_metric=selected_metric,
        )
        if optimization_result is None:
            optimization_rows: list[tuple[str, str]] = [("상태", "불가")]
        else:
            title_text: str = "없음"
            if optimization_result.candidate.equipped_title_id is not None:
                for owned_title in calculator_input.owned_titles:
                    if (
                        owned_title.name
                        == optimization_result.candidate.equipped_title_id
                    ):
                        title_text = owned_title.name
                        break

            talisman_name_map: dict[str, str] = {}
            for owned_talisman in calculator_input.owned_talismans:
                for template in TALISMAN_SPECS:
                    if template.name != owned_talisman.name:
                        continue

                    talisman_name_map[owned_talisman.name] = (
                        f"{template.name} Lv.{owned_talisman.level}"
                    )
                    break

            talisman_text: str = ", ".join(
                talisman_name_map[talisman_id]
                for talisman_id in optimization_result.candidate.equipped_talisman_ids
                if talisman_id in talisman_name_map
            )
            if not talisman_text:
                talisman_text = "없음"

            distribution_text: str = (
                f"힘 {optimization_result.candidate.distribution.strength}, "
                f"민첩 {optimization_result.candidate.distribution.dexterity}, "
                f"생명력 {optimization_result.candidate.distribution.vitality}, "
                f"행운 {optimization_result.candidate.distribution.luck}"
            )
            danjeon_text: str = (
                f"상 {optimization_result.candidate.danjeon.upper}, "
                f"중 {optimization_result.candidate.danjeon.middle}, "
                f"하 {optimization_result.candidate.danjeon.lower}"
            )
            optimization_rows = [
                (
                    "선택 전투력 증가",
                    cls._format_delta(optimization_result.deltas[selected_metric]),
                ),
                ("최적 스탯 분배", distribution_text),
                ("최적 단전", danjeon_text),
                ("최적 칭호", title_text),
                ("최적 부적", talisman_text),
            ]

        return cls.OutputRows(
            current_power=current_power_rows,
            stat_efficiency=stat_rows,
            level_up=level_up_rows,
            realm_up=realm_rows,
            scroll_efficiency=scroll_rows,
            custom_delta=custom_rows,
            base_state=base_state_rows,
            optimization_result=optimization_rows,
        )

    @classmethod
    def _build_custom_delta_rows(
        cls,
        base_stats: BaseStats,
        calculator_input: CalculatorPresetInput,
        context: "EvaluationContext",
    ) -> list[tuple[str, str]]:
        """사용자 지정 변화량 결과 행 공용 구성"""

        # 저장된 사용자 지정 변화량 맵 복원
        custom_changes: dict[StatKey, float] = {}
        for stat_key in STAT_SPECS.keys():
            change_value: float = calculator_input.custom_stat_changes[stat_key.value]
            if change_value == 0.0:
                continue

            custom_changes[stat_key] = change_value

        # 사용자 지정 변화량 기준 5종 전투력 변화량 계산
        custom_deltas: dict[PowerMetric, float] = evaluate_arbitrary_stat_delta(
            context=context,
            base_stats=base_stats,
            stat_changes=custom_changes,
        )
        custom_rows: list[tuple[str, str]] = []
        for power_metric in DISPLAY_POWER_METRICS:
            custom_rows.append(
                (
                    POWER_METRIC_LABELS[power_metric],
                    cls._format_delta(custom_deltas[power_metric]),
                )
            )

        return custom_rows

    class Efficiency(QFrame):
        def __init__(
            self,
            parent: QFrame,
            popup_manager: PopupManager,
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

            # 저장 상태 로드 중 이벤트 억제 플래그 구성
            self._is_loading_state: bool = False
            self.popup_manager: PopupManager = popup_manager

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
                self._get_initial_base_stats(),
            )

            # 스크롤 레벨 입력 UI 구성
            self.scroll_title: QLabel = QLabel("스크롤 레벨", self)
            self.scroll_title.setFont(CustomFont(12))
            self.skills = SkillInputs(
                self,
                SkillInputs.build_entries(),
                self.on_base_input_changed,
                self.popup_manager,
            )

            # 최적화 기준 입력 UI 구성
            self.optimization_title: QLabel = QLabel("현재 선택 입력", self)
            self.optimization_title.setFont(CustomFont(12))
            self.distribution_title: QLabel = QLabel("스탯 분배", self)
            self.distribution_title.setFont(CustomFont(11))
            self.distribution_inputs = self.DistributionInputs(
                self,
                self.on_optimization_input_changed,
            )
            self.danjeon_title: QLabel = QLabel("단전", self)
            self.danjeon_title.setFont(CustomFont(11))
            self.danjeon_inputs = self.DanjeonInputs(
                self,
                self.on_optimization_input_changed,
            )
            self.title_list_title: QLabel = QLabel("칭호 목록", self)
            self.title_list_title.setFont(CustomFont(11))
            self.title_inputs = self.TitleInputs(
                self,
                self.on_optimization_input_changed,
            )
            self.talisman_title: QLabel = QLabel("부적 목록", self)
            self.talisman_title.setFont(CustomFont(11))
            self.talisman_inputs = self.TalismanInputs(
                self,
                self.on_optimization_input_changed,
            )

            # 사용자 지정 변화량 입력 UI 구성
            self.custom_delta_title: QLabel = QLabel("사용자 지정 스탯 변화량", self)
            self.custom_delta_title.setFont(CustomFont(12))
            self.custom_delta_inputs = self.OverallStatInputs(
                self,
                self.on_custom_delta_changed,
                self._build_empty_stat_map(),
            )

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

            # 최적화 섹션 구성
            optimization_section: QWidget = QWidget(self)
            optimization_section_layout: QVBoxLayout = QVBoxLayout(optimization_section)
            optimization_section_layout.setContentsMargins(0, 0, 0, 0)
            optimization_section_layout.setSpacing(10)
            optimization_section_layout.addWidget(self.optimization_title)
            optimization_section_layout.addWidget(self.distribution_title)
            optimization_section_layout.addWidget(self.distribution_inputs)
            optimization_section_layout.addWidget(self.danjeon_title)
            optimization_section_layout.addWidget(self.danjeon_inputs)
            optimization_section_layout.addWidget(self.title_list_title)
            optimization_section_layout.addWidget(self.title_inputs)
            optimization_section_layout.addWidget(self.talisman_title)
            optimization_section_layout.addWidget(self.talisman_inputs)

            layout = QVBoxLayout(self)
            layout.addLayout(metric_layout)
            layout.addWidget(self.stats_title)
            layout.addWidget(self.stats_inputs)
            layout.addWidget(self.scroll_title)
            layout.addWidget(self.skills)
            layout.addWidget(self.custom_delta_title)
            layout.addWidget(self.custom_delta_inputs)
            layout.addWidget(optimization_section)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            # 저장된 경지 선택 상태 동기화
            self.load_from_preset_state()

        def has_valid_navigation_inputs(self) -> bool:
            """페이지 이동에 필요한 입력 유효성 반환"""

            stats_valid: bool
            level_valid: bool
            stats_valid, _ = self._read_base_stats()
            level_valid, _ = self._read_level()
            scroll_valid: bool = self._read_scroll_levels(save_levels=False)
            return stats_valid and level_valid and scroll_valid

        def load_from_preset_state(self) -> None:
            """저장된 계산기 상태를 현재 입력 위젯에 반영"""

            # 프리셋 반영 중 입력 이벤트 기반 저장/재계산 억제
            self._is_loading_state = True
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            self.metric_combobox.setCurrentIndex(
                self.metric_options.index(calculator_input.selected_metric)
            )
            self.level_input.setText(str(calculator_input.level))
            self.realm_combobox.setCurrentIndex(
                self.realm_options.index(calculator_input.realm_tier)
            )

            for stat_key in STAT_SPECS.keys():
                self.stats_inputs.inputs[stat_key].setText(
                    f"{calculator_input.base_stats.values[stat_key.value]:g}"
                )
                self.custom_delta_inputs.inputs[stat_key].setText(
                    f"{calculator_input.custom_stat_changes[stat_key.value]:g}"
                )

            for input_widget, entry in zip(self.skills.inputs, self.skills.entries):
                input_widget.setText(
                    str(self._get_preset().info.get_scroll_level(entry.scroll_id))
                )

            self._load_optimization_inputs()
            self._is_loading_state = False

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
                        stat_spec: str = STAT_SPECS[stat_key]
                        label: str = stat_spec

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

                # 잠금/초기화 토글 구성
                self.lock_checkbox: QCheckBox = QCheckBox("잠금", self)
                self.lock_checkbox.stateChanged.connect(connected_function)
                self.reset_checkbox: QCheckBox = QCheckBox("초기화", self)
                self.reset_checkbox.stateChanged.connect(connected_function)
                layout.addWidget(self.lock_checkbox)
                layout.addWidget(self.reset_checkbox)
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

                # 잠금/초기화 토글 구성
                self.lock_checkbox: QCheckBox = QCheckBox("잠금", self)
                self.lock_checkbox.stateChanged.connect(connected_function)
                self.reset_checkbox: QCheckBox = QCheckBox("초기화", self)
                self.reset_checkbox.stateChanged.connect(connected_function)
                layout.addWidget(self.lock_checkbox)
                layout.addWidget(self.reset_checkbox)
                layout.addStretch(1)
                self.setLayout(layout)

        class TitleInputs(QFrame):
            class TitleStatRow(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    connected_function: Callable[[], None],
                    remove_function: Callable[
                        ["ResultsPage.Efficiency.TitleInputs.TitleStatRow"], None
                    ],
                    stat_key: StatKey | None = None,
                    value: float = 0.0,
                ) -> None:
                    super().__init__(parent)

                    # 스탯 선택/수치/삭제 버튼 구성
                    self._connected_function: Callable[[], None] = connected_function
                    self._remove_function = remove_function
                    self._stat_options: list[StatKey] = list(STAT_SPECS.keys())

                    layout: QHBoxLayout = QHBoxLayout(self)
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(8)

                    self.stat_combobox = CustomComboBox(
                        self,
                        list(STAT_SPECS.values()),
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
                        ["ResultsPage.Efficiency.TitleInputs.TitleCard"], None
                    ],
                    data: OwnedTitle | None = None,
                ) -> None:
                    super().__init__(parent)

                    # 칭호 카드 전체 편집 영역 구성
                    self._connected_function: Callable[[], None] = connected_function
                    self._remove_function: Callable[
                        [ResultsPage.Efficiency.TitleInputs.TitleCard], None
                    ] = remove_function
                    self.stat_rows: list[
                        ResultsPage.Efficiency.TitleInputs.TitleStatRow
                    ] = []

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

                    row = ResultsPage.Efficiency.TitleInputs.TitleStatRow(
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
                    target_row: "ResultsPage.Efficiency.TitleInputs.TitleStatRow",
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
                self._cards: list[ResultsPage.Efficiency.TitleInputs.TitleCard] = []

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

                card = ResultsPage.Efficiency.TitleInputs.TitleCard(
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
                target_card: "ResultsPage.Efficiency.TitleInputs.TitleCard",
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
                        ["ResultsPage.Efficiency.TalismanInputs.TalismanRow"], None
                    ],
                    data: OwnedTalisman | None = None,
                ) -> None:
                    super().__init__(parent)

                    # 보유 부적 한 줄 편집 UI 구성
                    self._connected_function: Callable[[], None] = connected_function
                    self._remove_function = remove_function
                    self._templates: list[TalismanSpec] = list(TALISMAN_SPECS)

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

                    template: TalismanSpec = self._templates[
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
                self._rows: list[ResultsPage.Efficiency.TalismanInputs.TalismanRow] = []

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

                row = ResultsPage.Efficiency.TalismanInputs.TalismanRow(
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
                target_row: "ResultsPage.Efficiency.TalismanInputs.TalismanRow",
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
                seen_ids: set[str] = set()
                for combobox in self.equipped_comboboxes:
                    selected_index: int = combobox.currentIndex()
                    if selected_index <= 0:
                        continue

                    target_index: int = selected_index - 1
                    if target_index >= len(owned_talismans):
                        continue

                    target_owned_id: str = owned_talismans[target_index].owned_id
                    if target_owned_id in seen_ids:
                        continue

                    seen_ids.add(target_owned_id)
                    equipped_ids.append(target_owned_id)

                return is_valid, owned_talismans, equipped_ids

        def _get_preset(self) -> "MacroPreset":
            """현재 선택 프리셋 반환"""

            return app_state.macro.current_preset

        def _get_calculator_realm(self) -> RealmTier:
            """저장된 현재 경지 반환"""

            return self._get_preset().info.calculator.realm_tier

        def _get_initial_base_stats(self) -> dict[StatKey, str]:
            """저장된 베이스 스탯 입력 문자열 맵 반환"""

            # 저장된 베이스 스탯을 입력 위젯 초기 문자열로 변환
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            values: dict[StatKey, str] = {}
            for stat_key in STAT_SPECS.keys():
                values[stat_key] = (
                    f"{calculator_input.base_stats.values[stat_key.value]:g}"
                )

            return values

        def _build_empty_stat_map(self) -> dict[StatKey, str]:
            """사용자 지정 변화량 초기값 맵 생성"""

            # 저장된 변화량 입력을 위젯 초기 문자열로 변환
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            values: dict[StatKey, str] = {}
            for stat_key in STAT_SPECS.keys():
                values[stat_key] = (
                    f"{calculator_input.custom_stat_changes[stat_key.value]:g}"
                )

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
            self.distribution_inputs.lock_checkbox.setChecked(
                calculator_input.distribution.is_locked
            )
            self.distribution_inputs.reset_checkbox.setChecked(
                calculator_input.distribution.use_reset
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
            self.danjeon_inputs.lock_checkbox.setChecked(
                calculator_input.danjeon.is_locked
            )
            self.danjeon_inputs.reset_checkbox.setChecked(
                calculator_input.danjeon.use_reset
            )
            self.title_inputs.load(
                calculator_input.owned_titles,
                calculator_input.equipped_state.equipped_title_id,
            )
            self.talisman_inputs.load(
                calculator_input.owned_talismans,
                calculator_input.equipped_state.equipped_talisman_ids,
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
                is_locked=self.distribution_inputs.lock_checkbox.isChecked(),
                use_reset=self.distribution_inputs.reset_checkbox.isChecked(),
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
                is_locked=self.danjeon_inputs.lock_checkbox.isChecked(),
                use_reset=self.danjeon_inputs.reset_checkbox.isChecked(),
            )
            return is_valid, danjeon_state

        def _read_optimization_state(
            self,
        ) -> tuple[
            bool,
            DistributionState,
            DanjeonState,
            list[OwnedTitle],
            EquippedState,
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

            equipped_state: EquippedState = EquippedState(
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

        def _read_base_stats(self) -> tuple[bool, BaseStats]:
            """베이스 스탯 입력 복원 및 검증"""

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

            return is_valid, BaseStats(values=parsed_stats)

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

        def _read_scroll_levels(self, save_levels: bool = True) -> bool:
            """스크롤 레벨 입력 검증 및 저장"""

            # 모든 스크롤 레벨을 검증하고 필요 시 현재 프리셋에 반영
            all_valid: bool = True
            for input_widget, entry in zip(self.skills.inputs, self.skills.entries):
                text: str = input_widget.text()
                is_valid: bool = text.isdigit() and (
                    1 <= int(text) <= app_state.macro.current_server.max_skill_level
                )
                input_widget.set_valid(is_valid)
                all_valid = all_valid and is_valid

                if not (is_valid and save_levels):
                    continue

                self._get_preset().info.set_scroll_level(entry.scroll_id, int(text))

            return all_valid

        def _save_base_inputs(
            self,
            base_stats: BaseStats,
            level: int,
            persist: bool = True,
        ) -> None:
            """기준 입력 상태 저장"""

            # 계산기 입력 블록에 현재 기준 입력 반영
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            calculator_input.base_stats = base_stats
            calculator_input.level = level
            calculator_input.realm_tier = self.realm_options[
                self.realm_combobox.currentIndex()
            ]
            calculator_input.selected_metric = self._get_selected_metric()
            if persist:
                save_data()

        def _save_custom_stat_changes(
            self,
            custom_changes: dict[StatKey, float],
            persist: bool = True,
        ) -> None:
            """사용자 지정 변화량 입력 상태 저장"""

            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            calculator_input.custom_stat_changes = {
                stat_key.value: custom_changes.get(stat_key, 0.0)
                for stat_key in STAT_SPECS.keys()
            }
            if persist:
                save_data()

        def _save_optimization_inputs(
            self,
            distribution_state: DistributionState,
            danjeon_state: DanjeonState,
            owned_titles: list[OwnedTitle],
            equipped_state: EquippedState,
            owned_talismans: list[OwnedTalisman],
            persist: bool = True,
        ) -> None:
            """최적화 입력 상태 저장"""

            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            calculator_input.distribution = distribution_state
            calculator_input.danjeon = danjeon_state
            calculator_input.owned_titles = owned_titles
            calculator_input.equipped_state = equipped_state
            calculator_input.owned_talismans = owned_talismans
            if persist:
                save_data()

        def on_optimization_input_changed(self) -> None:
            """최적화 입력 변경 시 기준 상태 분리 갱신"""

            if self._is_loading_state:
                return

            self.title_inputs.refresh_equipped_options()
            self.talisman_inputs.refresh_equipped_options()
            optimization_valid: bool
            distribution_state: DistributionState
            danjeon_state: DanjeonState
            owned_titles: list[OwnedTitle]
            equipped_state: EquippedState
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
                return

            self._save_optimization_inputs(
                distribution_state=distribution_state,
                danjeon_state=danjeon_state,
                owned_titles=owned_titles,
                equipped_state=equipped_state,
                owned_talismans=owned_talismans,
                persist=True,
            )

        def on_base_input_changed(self) -> None:
            """기준 입력 변경 시 전체 효율 출력 갱신"""

            if self._is_loading_state:
                return

            stats_valid: bool
            base_stats: BaseStats
            stats_valid, base_stats = self._read_base_stats()

            level_valid: bool
            level: int
            level_valid, level = self._read_level()

            scroll_valid: bool = self._read_scroll_levels()

            if not (stats_valid and level_valid and scroll_valid):
                return

            self._save_base_inputs(
                base_stats=base_stats,
                level=level,
                persist=True,
            )

        def on_custom_delta_changed(self) -> None:
            """사용자 지정 변화량 변경 시 결과 갱신"""

            if self._is_loading_state:
                return

            custom_valid: bool
            custom_changes: dict[StatKey, float]
            custom_valid, custom_changes = self._read_custom_stat_changes()
            if not custom_valid:
                return

            self._save_custom_stat_changes(
                custom_changes=custom_changes,
                persist=True,
            )

    class ResultsView(QFrame):
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

            # 결과 전용 출력 위젯 구성
            self.current_power_title: QLabel = QLabel("현재 전투력", self)
            self.current_power_title.setFont(CustomFont(12))
            self.current_power_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            self.stat_efficiency_title: QLabel = QLabel("스탯 1당 효율", self)
            self.stat_efficiency_title.setFont(CustomFont(12))
            self.stat_efficiency_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            self.level_up_title: QLabel = QLabel("레벨 1업 효율", self)
            self.level_up_title.setFont(CustomFont(12))
            self.level_up_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            self.realm_up_title: QLabel = QLabel("다음 경지 효율", self)
            self.realm_up_title.setFont(CustomFont(12))
            self.realm_up_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            self.scroll_efficiency_title: QLabel = QLabel("스크롤 +1 효율", self)
            self.scroll_efficiency_title.setFont(CustomFont(12))
            self.scroll_efficiency_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            self.custom_delta_result_title: QLabel = QLabel(
                "사용자 지정 변화량 결과", self
            )
            self.custom_delta_result_title.setFont(CustomFont(12))
            self.custom_delta_result_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            self.base_state_title: QLabel = QLabel("기준 상태 분리", self)
            self.base_state_title.setFont(CustomFont(12))
            self.base_state_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            self.optimization_result_title: QLabel = QLabel("최적화 결과", self)
            self.optimization_result_title.setFont(CustomFont(12))
            self.optimization_result_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            # 결과 섹션 묶음 레이아웃 구성
            base_section: QWidget = QWidget(self)
            base_section_layout: QVBoxLayout = QVBoxLayout(base_section)
            base_section_layout.setContentsMargins(0, 0, 0, 0)
            base_section_layout.setSpacing(10)
            base_section_layout.addWidget(self.current_power_title)
            base_section_layout.addWidget(self.current_power_list)
            base_section_layout.addWidget(self.stat_efficiency_title)
            base_section_layout.addWidget(self.stat_efficiency_list)
            base_section_layout.addWidget(self.level_up_title)
            base_section_layout.addWidget(self.level_up_list)
            base_section_layout.addWidget(self.realm_up_title)
            base_section_layout.addWidget(self.realm_up_list)
            base_section_layout.addWidget(self.scroll_efficiency_title)
            base_section_layout.addWidget(self.scroll_efficiency_list)
            base_section_layout.addWidget(self.custom_delta_result_title)
            base_section_layout.addWidget(self.custom_delta_result_list)

            optimization_section: QWidget = QWidget(self)
            optimization_section_layout: QVBoxLayout = QVBoxLayout(optimization_section)
            optimization_section_layout.setContentsMargins(0, 0, 0, 0)
            optimization_section_layout.setSpacing(10)
            optimization_section_layout.addWidget(self.base_state_title)
            optimization_section_layout.addWidget(self.base_state_list)
            optimization_section_layout.addWidget(self.optimization_result_title)
            optimization_section_layout.addWidget(self.optimization_result_list)

            layout = QVBoxLayout(self)
            layout.addWidget(base_section)
            layout.addWidget(optimization_section)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        def _get_preset(self) -> "MacroPreset":
            """현재 선택 프리셋 반환"""

            return app_state.macro.current_preset

        def _set_error_outputs(self) -> None:
            """결과 페이지 오류 상태 출력"""

            error_rows: list[tuple[str, str]] = [("상태", "오류")]
            self.current_power_list.set_rows(error_rows)
            self.stat_efficiency_list.set_rows(error_rows)
            self.level_up_list.set_rows(error_rows)
            self.realm_up_list.set_rows(error_rows)
            self.scroll_efficiency_list.set_rows(error_rows)
            self.custom_delta_result_list.set_rows(error_rows)
            self.base_state_list.set_rows(error_rows)
            self.optimization_result_list.set_rows(error_rows)

        def refresh_from_preset(self) -> None:
            """저장된 계산기 상태 기준 결과 전용 출력 재구성"""

            # 저장된 계산기 입력 상태 직접 조회
            preset: MacroPreset = self._get_preset()
            calculator_input: CalculatorPresetInput = preset.info.calculator
            base_stats: BaseStats = calculator_input.base_stats
            level: int = calculator_input.level
            selected_metric: PowerMetric = calculator_input.selected_metric

            # 저장된 스크롤 레벨 유효성 사전 확인
            scroll_is_valid: bool = True
            for entry in SkillInputs.build_entries():
                scroll_level: int = preset.info.get_scroll_level(entry.scroll_id)
                if not (
                    1 <= scroll_level <= app_state.macro.current_server.max_skill_level
                ):
                    scroll_is_valid = False
                    break

            if not scroll_is_valid:
                self._set_error_outputs()
                return

            # 저장된 기준 입력 기준 전투력 컨텍스트 재구성
            context: EvaluationContext = build_calculator_context(
                server_spec=app_state.macro.current_server,
                preset=preset,
                skills_info=preset.usage_settings,
                delay_ms=app_state.macro.current_delay,
                base_stats=base_stats,
            )
            output_rows: ResultsPage.OutputRows = ResultsPage._build_output_rows(
                server_spec=app_state.macro.current_server,
                preset=preset,
                delay_ms=app_state.macro.current_delay,
                base_stats=base_stats,
                calculator_input=calculator_input,
                level=level,
                selected_metric=selected_metric,
                current_realm=calculator_input.realm_tier,
                context=context,
            )
            self.current_power_list.set_rows(output_rows.current_power)
            self.stat_efficiency_list.set_rows(output_rows.stat_efficiency)
            self.level_up_list.set_rows(output_rows.level_up)
            self.realm_up_list.set_rows(output_rows.realm_up)
            self.scroll_efficiency_list.set_rows(output_rows.scroll_efficiency)
            self.custom_delta_result_list.set_rows(output_rows.custom_delta)
            self.base_state_list.set_rows(output_rows.base_state)
            self.optimization_result_list.set_rows(output_rows.optimization_result)


class SkillInputs(QFrame):
    @dataclass(frozen=True)
    class Entry:
        """스크롤 레벨 입력 UI 한 칸의 표시/저장 정보"""

        title: str
        value: int
        scroll_id: str

    @staticmethod
    def build_entries() -> list["SkillInputs.Entry"]:
        """현재 서버/프리셋 기준 스크롤 레벨 입력 목록 구성"""

        server: ServerSpec = app_state.macro.current_server
        preset: MacroPreset = app_state.macro.current_preset
        entries: list[SkillInputs.Entry] = []

        for scroll_def in server.skill_registry.get_all_scroll_defs():
            entries.append(
                SkillInputs.Entry(
                    title=scroll_def.name,
                    value=preset.info.get_scroll_level(scroll_def.id),
                    scroll_id=scroll_def.id,
                )
            )

        return entries

    def __init__(
        self,
        mainframe: QWidget,
        entries: list["SkillInputs.Entry"],
        connected_function: Callable[[], None],
        popup_manager: PopupManager,
    ) -> None:
        super().__init__(mainframe)

        if config.ui.debug_colors:
            self.setStyleSheet("QFrame { background-color: green; border: 0px solid; }")

        # 그리드 레이아웃 위젯 생성
        grid_layout: QGridLayout = QGridLayout(self)

        # 아이템을 저장할 리스트
        self.entries: list[SkillInputs.Entry] = entries
        self.inputs: list[CustomLineEdit] = []
        self.popup_manager: PopupManager = popup_manager

        # column 수 설정
        cols: int = 7
        for i, entry in enumerate(self.entries):
            item_widget: SkillInputs.SkillInput = self.SkillInput(
                self,
                entry,
                connected_function,
                self.popup_manager,
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
            entry: "SkillInputs.Entry",
            connected_function: Callable[[], None],
            popup_manager: PopupManager,
        ) -> None:
            super().__init__(parent)

            self.entry: SkillInputs.Entry = entry
            self.popup_manager: PopupManager = popup_manager
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

            # 계산기 스크롤 레벨 아이콘에 공용 호버 카드 연결
            self.popup_manager.bind_hover_card(
                image,
                self._build_scroll_hover_card,
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

        def _build_scroll_hover_card(self) -> HoverCardData:
            """계산기 스크롤 아이콘 기준 호버 카드 구성"""

            # 현재 서버 스크롤 정의와 저장 레벨 기준으로 카드 내용 구성
            scroll_def: "ScrollDef" = (
                app_state.macro.current_server.skill_registry.get_scroll(
                    self.entry.scroll_id
                )
            )
            level: int = app_state.macro.current_preset.info.get_scroll_level(
                self.entry.scroll_id
            )
            return self.popup_manager.build_scroll_hover_card(scroll_def, level)


class PowerLabels(QFrame):
    def __init__(
        self,
        mainframe: QWidget,
        titles: list[str],
        texts: list[str] | str = "0",
        font_size: int = 18,
    ) -> None:
        super().__init__(mainframe)

        if config.ui.debug_colors:
            self.setStyleSheet(
                "QFrame { background-color: purple; border: 0px solid; }"
            )
        else:
            self.setStyleSheet("QFrame { background-color: white; border: 0px solid; }")

        # 레이아웃 설정
        layout: QHBoxLayout = QHBoxLayout(self)

        self.numbers: list[QLabel] = []
        self.titles: list[str] = titles
        self.colors: tuple[str, ...] = (
            "255, 130, 130",
            "255, 230, 140",
            "170, 230, 255",
            "150, 225, 210",
            "210, 180, 255",
        )

        # 단일 문자열 입력 시 현재 전투력 칸 수만큼 동일 값 확장
        if isinstance(texts, str):
            texts = [texts] * len(self.titles)

        # 현재 전투력 종류 수만큼 카드 생성
        for i, title in enumerate(self.titles):
            power: PowerLabels.Power = self.Power(
                self,
                title,
                texts[i],
                self.colors[i],
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
        # 단일 문자열 입력 시 현재 전투력 칸 수만큼 동일 값 확장
        if isinstance(texts, str):
            texts = [texts] * len(self.numbers)

        for i in range(len(self.numbers)):
            self.numbers[i].setText(texts[i])

    class Power(QFrame):
        def __init__(
            self,
            mainframe: QWidget,
            name: str,
            text: str,
            color: str,
            font_size: int = 18,
        ) -> None:
            super().__init__(mainframe)

            label: QLabel = QLabel(name, self)
            label.setStyleSheet(
                f"QLabel {{ background-color: rgb({color}); border: 1px solid rgb({color}); border-bottom: 0px solid; border-top-left-radius: 4px; border-top-right-radius: 4px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; }}"
            )
            label.setFont(CustomFont(14))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedHeight(50)

            self.number: QLabel = QLabel(text, self)
            self.number.setStyleSheet(
                f"QLabel {{ background-color: rgba({color}, 120); border: 1px solid rgb({color}); border-top: 0px solid; border-top-left-radius: 0px; border-top-right-radius: 0px; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px }}"
            )
            self.number.setFont(CustomFont(font_size))
            self.number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.number.setFixedHeight(90)

            layout: QVBoxLayout = QVBoxLayout(self)
            layout.addWidget(label)
            layout.addWidget(self.number)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class AnalysisDetails(QFrame):
    DETAIL_KEYS: tuple[str, ...] = (
        "min",
        "max",
        "std",
        "p25",
        "p50",
        "p75",
    )

    def __init__(
        self,
        mainframe: QWidget,
        analysis: list[GraphAnalysis],
    ) -> None:
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
                self.DETAIL_KEYS,
                config.ui.analysis_card_colors[i],
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
            analysis: GraphAnalysis,
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
