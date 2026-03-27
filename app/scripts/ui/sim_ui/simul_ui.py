from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.calculator_engine import (
    DISPLAY_POWER_METRICS,
    POWER_METRIC_LABELS,
    build_calculator_context,
    build_internal_base_stats,
    evaluate_arbitrary_stat_delta,
    evaluate_level_up_delta,
    evaluate_next_realm_delta,
    evaluate_scroll_upgrade_deltas,
    evaluate_single_stat_delta,
    optimize_current_selection,
)
from app.scripts.calculator_models import (
    OVERALL_STAT_GRID_ROWS,
    OVERALL_STAT_ORDER,
    REALM_TIER_SPECS,
    STAT_SPECS,
    TALISMAN_SPECS,
    TITLE_STAT_SLOT_COUNT,
    BaseStats,
    DanjeonState,
    DistributionState,
    EquippedState,
    OwnedTalisman,
    OwnedTitle,
    OwnedTitleStat,
    StatKey,
    TalismanGrade,
)
from app.scripts.config import config
from app.scripts.custom_classes import (
    CustomComboBox,
    CustomFont,
    CustomLineEdit,
    KVComboInput,
    KVInput,
    SectionCard,
    SkillImage,
    StyledButton,
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
    from app.scripts.registry.skill_registry import ScrollDef
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

        # 결과 계산 오버레이와 백그라운드 스레드 구성
        self._results_overlay: _CalculationOverlay = _CalculationOverlay(
            self.parent,
            self._cancel_results_calculation,
        )
        self._calc_thread: _CalculatorThread | None = None

        self.stacked_layout.setCurrentIndex(0)
        # 스택 레이아웃 설정
        self.main_frame.setLayout(self.stacked_layout)

        self.adjust_main_frame_height()

    def on_enter(self) -> None:
        """메인 화면에서 계산기 화면으로 진입

        내부 페이지를 입력 화면으로 되돌리고
        메인 화면에서 변경된 스크롤 레벨 등을 입력 위젯에 동기화
        """
        if self.stacked_layout.currentIndex() != 0:
            self.stacked_layout.setCurrentIndex(0)
            self.update_nav(0)
            self.adjust_main_frame_height()

        self.input_page.editor.load_from_preset_state()

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

        # 결과 페이지 진입 요청 시 현재 페이지 유지 상태로 백그라운드 계산 시작
        if index == 2:
            self._start_results_calculation()
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

        current_widget: QWidget | None = self.stacked_layout.currentWidget()
        if current_widget is None:
            return

        current_layout: QLayout | None = current_widget.layout()
        if current_layout is not None:
            # 현재 페이지 레이아웃 최신 sizeHint 반영
            current_layout.invalidate()
            current_layout.activate()

        # 현재 페이지 geometry 재계산
        current_widget.updateGeometry()
        current_widget.adjustSize()
        height: int = current_widget.sizeHint().height()
        if height > 0:
            self.main_frame.setFixedHeight(height)

        # 스크롤 위치 범위 보정
        vertical_bar: QScrollBar = self.scroll_area.verticalScrollBar()
        vertical_bar.setValue(min(vertical_bar.value(), vertical_bar.maximum()))
        horizontal_bar: QScrollBar = self.scroll_area.horizontalScrollBar()
        horizontal_bar.setValue(min(horizontal_bar.value(), horizontal_bar.maximum()))

    def _start_results_calculation(self) -> None:
        """현재 페이지 유지 상태로 결과 페이지 계산 시작"""

        # 중복 계산 요청 차단 블록
        if self._calc_thread is not None and self._calc_thread.isRunning():
            return

        # 저장된 계산기 입력 기준 계산 인자 복원 블록
        preset: MacroPreset = app_state.macro.current_preset
        calculator_input: CalculatorPresetInput = preset.info.calculator
        base_stats: BaseStats = calculator_input.base_stats
        level: int = calculator_input.level
        selected_metric: PowerMetric = calculator_input.selected_metric

        # 결과 페이지 초기 상태와 진행 오버레이 표시 블록
        self.results_page.set_loading_state()
        self._results_overlay.show_overlay(
            "스탯 계산기 결과 준비 중...", "대기 중...", 0
        )

        # 백그라운드 계산 스레드 연결 블록
        self._calc_thread = _CalculatorThread(
            server_spec=app_state.macro.current_server,
            preset=preset,
            delay_ms=app_state.macro.current_delay,
            base_stats=base_stats,
            calculator_input=calculator_input,
            level=level,
            selected_metric=selected_metric,
        )
        self._calc_thread.progress_signal.connect(self._on_results_calculation_progress)
        self._calc_thread.finished_signal.connect(self._on_results_calculation_finished)
        self._calc_thread.start()

    def _cancel_results_calculation(self) -> None:
        """진행 중인 결과 계산 취소 요청"""

        # 실행 중인 계산이 없으면 취소 동작 무시 블록
        if self._calc_thread is None or not self._calc_thread.isRunning():
            return

        # 사용자 취소 의도 즉시 반영 블록
        self._results_overlay.set_cancelling()
        self._calc_thread.cancel()

    def _on_results_calculation_progress(self, message: str, value: int) -> None:
        """오버레이 진행 상태 갱신"""

        # 백그라운드 계산 단계 문구와 진행률 반영 블록
        self._results_overlay.update_progress(message, value)

    def _on_results_calculation_finished(
        self,
        output_rows: ResultsPage.OutputRows | None,
        is_cancelled: bool,
    ) -> None:
        """백그라운드 계산 종료 후 페이지 전환 처리"""

        # 완료 스레드 참조 해제와 오버레이 정리 블록
        self._calc_thread = None
        self._results_overlay.hide()

        # 사용자 취소 요청이면 현재 페이지 유지 블록
        if is_cancelled:
            return

        # 계산 실패 시 오류 결과 표시 후 결과 페이지 진입 블록
        if output_rows is None:
            self.results_page.set_error_state()
            self.update_nav(2)
            self.stacked_layout.setCurrentIndex(2)
            self.adjust_main_frame_height()
            return

        # 계산 성공 결과 반영 후 결과 페이지 진입 블록
        self.results_page.set_output_rows(output_rows)
        self.update_nav(2)
        self.stacked_layout.setCurrentIndex(2)
        self.adjust_main_frame_height()


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


class _CalculationOverlay(QFrame):
    def __init__(
        self,
        parent: QWidget,
        cancel_handler: Callable[[], None],
    ) -> None:
        super().__init__(parent)

        # 부모 전체를 덮는 반투명 오버레이 기본 설정 블록
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QFrame { background-color: rgba(15, 23, 42, 110); }")
        self.setGeometry(parent.rect())
        self.hide()
        parent.installEventFilter(self)

        # 오버레이 중앙 카드 구성 블록
        container: QFrame = QFrame(self)
        container.setFixedWidth(360)
        container.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #D8DEE8; border-radius: 16px; }"
        )

        title_label: QLabel = QLabel("계산 중", container)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(CustomFont(15, bold=True))
        title_label.setStyleSheet(
            "QLabel { background-color: transparent; border: 0px; color: #111827; }"
        )

        self._message_label: QLabel = QLabel(container)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setFont(CustomFont(12, bold=True))
        self._message_label.setStyleSheet(
            "QLabel { background-color: transparent; border: 0px; color: #1F2937; }"
        )

        self._detail_label: QLabel = QLabel(container)
        self._detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_label.setFont(CustomFont(11))
        self._detail_label.setStyleSheet(
            "QLabel { background-color: transparent; border: 0px; color: #6B7280; }"
        )

        self._progress_label: QLabel = QLabel(container)
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setFont(CustomFont(11))
        self._progress_label.setStyleSheet(
            "QLabel { background-color: transparent; border: 0px; color: #4B5563; }"
        )

        self._progress_bar: QProgressBar = QProgressBar(container)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(12)
        self._progress_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #E5E7EB;
                border: 0px;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #9180F7;
                border-radius: 6px;
            }
            """
        )

        self._cancel_button: QPushButton = QPushButton("취소", container)
        self._cancel_button.setFont(CustomFont(11, bold=True))
        self._cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_button.setFixedHeight(40)
        self._cancel_button.setStyleSheet(
            """
            QPushButton {
                background-color: #F3F4F6;
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                color: #111827;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
            QPushButton:disabled {
                background-color: #E5E7EB;
                color: #9CA3AF;
            }
            """
        )
        self._cancel_button.clicked.connect(cancel_handler)

        # 중앙 카드 내부 정렬 블록
        container_layout: QVBoxLayout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(12)
        container_layout.addWidget(title_label)
        container_layout.addWidget(self._message_label)
        container_layout.addWidget(self._detail_label)
        container_layout.addWidget(self._progress_bar)
        container_layout.addWidget(self._progress_label)
        container_layout.addSpacing(4)
        container_layout.addWidget(self._cancel_button)
        container.setLayout(container_layout)

        # 오버레이 전체 중앙 배치 블록
        overlay_layout: QVBoxLayout = QVBoxLayout(self)
        overlay_layout.setContentsMargins(24, 24, 24, 24)
        overlay_layout.addStretch(1)
        overlay_layout.addWidget(container, alignment=Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addStretch(1)
        self.setLayout(overlay_layout)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """부모 리사이즈 시 오버레이 영역 동기화"""

        # 부모 크기 변경 시 오버레이 전체 영역 재배치 블록
        if watched is self.parent() and event.type() == QEvent.Type.Resize:
            parent_widget: QWidget = self.parentWidget()
            self.setGeometry(parent_widget.rect())

        return super().eventFilter(watched, event)

    def show_overlay(self, message: str, detail: str, value: int) -> None:
        """초기 진행 상태와 함께 오버레이 표시"""

        # 취소 버튼 활성화와 초기 진행 상태 반영 블록
        self._cancel_button.setEnabled(True)
        self._message_label.setText(message)
        self.update_progress(detail, value)

        # 최상단 오버레이 표시 블록
        self.show()
        self.raise_()

    def update_progress(self, detail: str, value: int) -> None:
        """진행 문구와 진행률 갱신"""

        # 진행 문구와 백분율 레이블 동기화 블록
        clamped_value: int = max(0, min(100, value))
        self._detail_label.setText(detail)
        self._progress_label.setText(f"{clamped_value}%")
        self._progress_bar.setValue(clamped_value)

    def set_cancelling(self) -> None:
        """취소 요청 직후 오버레이 상태 갱신"""

        # 중복 취소 방지와 취소 진행 상태 표기 블록
        self._cancel_button.setEnabled(False)
        self._detail_label.setText("취소 요청 처리 중...")


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


class _CalculationCancelledError(Exception):
    """계산 취소 요청 전달용 내부 예외"""


class _CalculatorThread(QThread):
    """백그라운드에서 계산기 연산을 수행하는 스레드"""

    finished_signal = Signal(object, bool)
    progress_signal = Signal(str, int)

    def __init__(
        self,
        server_spec: "ServerSpec",
        preset: "MacroPreset",
        delay_ms: int,
        base_stats: BaseStats,
        calculator_input: "CalculatorPresetInput",
        level: int,
        selected_metric: "PowerMetric",
    ) -> None:
        super().__init__()
        self._server_spec = server_spec
        self._preset = preset
        self._delay_ms = delay_ms
        self._base_stats = base_stats
        self._calculator_input = calculator_input
        self._level = level
        self._selected_metric = selected_metric
        self._is_cancel_requested: bool = False

    def cancel(self) -> None:
        """계산 취소 요청 기록"""

        # 스레드 인터럽트와 내부 취소 플래그 동시 반영 블록
        self._is_cancel_requested = True
        self.requestInterruption()

    def _emit_progress(self, message: str, value: int) -> None:
        """진행 상태 시그널 방출"""

        # 취소 여부 확인 이후 진행 상태 전파 블록
        self._ensure_not_cancelled()
        self.progress_signal.emit(message, value)

    def _ensure_not_cancelled(self) -> None:
        """취소 요청 시 내부 예외 발생"""

        # 스레드 인터럽트 또는 명시적 취소 요청 감지 블록
        if self._is_cancel_requested or self.isInterruptionRequested():
            raise _CalculationCancelledError()

    def run(self) -> None:
        try:
            # 계산 컨텍스트 선행 구성 블록
            self._emit_progress("컨텍스트 생성 중...", 0)
            context: EvaluationContext = build_calculator_context(
                server_spec=self._server_spec,
                preset=self._preset,
                skills_info=self._preset.usage_settings,
                delay_ms=self._delay_ms,
                base_stats=self._base_stats,
            )

            # 결과 행 전체 계산 블록
            self._emit_progress("결과 정리 준비 중...", 0)
            output_rows: ResultsPage.OutputRows = ResultsPage._build_output_rows(
                server_spec=self._server_spec,
                preset=self._preset,
                delay_ms=self._delay_ms,
                base_stats=self._base_stats,
                level=self._level,
                selected_metric=self._selected_metric,
                current_realm=self._calculator_input.realm_tier,
                calculator_input=self._calculator_input,
                context=context,
                progress_callback=self._emit_progress,
                cancel_checker=self._ensure_not_cancelled,
            )

            # 완료 직전 취소 여부 재확인 블록
            self._ensure_not_cancelled()
            self.progress_signal.emit("완료됨", 100)
            self.finished_signal.emit(output_rows, False)
        except _CalculationCancelledError:
            self.finished_signal.emit(None, True)
        except Exception:
            self.finished_signal.emit(None, False)


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
        optimization_result: list[tuple[str, str]]
        has_custom_delta: bool
        optimized_base_stats: BaseStats | None
        selected_metric: "PowerMetric"

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
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_loading_state(self) -> None:
        """결과 페이지 로딩 출력 반영"""

        # 결과 카드 공통 로딩 상태 반영 블록
        self.view.set_loading_outputs()

    def set_error_state(self) -> None:
        """결과 페이지 오류 출력 반영"""

        # 결과 카드 공통 오류 상태 반영 블록
        self.view.set_error_outputs()

    def set_output_rows(self, output_rows: "ResultsPage.OutputRows") -> None:
        """계산 완료 결과 반영"""

        # 계산 완료 결과 행을 결과 카드에 반영 블록
        self.view.set_output_rows(output_rows)

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
        progress_callback: Callable[[str, int], None] | None = None,
        cancel_checker: Callable[[], None] | None = None,
    ) -> "ResultsPage.OutputRows":
        """공용 계산기 결과 행 구성"""

        # 현재 전투력 구성 직전 진행 단계 반영 블록
        if progress_callback is not None:
            progress_callback("현재 전투력 정리 중...", 0)

        if cancel_checker is not None:
            cancel_checker()

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

        # 스탯 효율 계산 시작 단계 반영 블록
        if progress_callback is not None:
            progress_callback("스탯 효율 계산 중...", 0)

        # 스탯 1당 효율 출력 행 구성
        stat_rows: list[tuple[str, str]] = []
        stat_count: int = len(STAT_SPECS)
        stat_index: int
        stat_key: StatKey
        stat_label: str
        for stat_index, (stat_key, stat_label) in enumerate(
            STAT_SPECS.items(), start=1
        ):
            if cancel_checker is not None:
                cancel_checker()

            deltas: dict[PowerMetric, float] = evaluate_single_stat_delta(
                context=context,
                stat_key=stat_key,
                amount=1.0,
            )
            label: str = f"{stat_label} +1"

            stat_rows.append((label, cls._format_delta(deltas[selected_metric])))

            if progress_callback is not None:
                stat_progress: int = 0
                progress_callback("스탯 효율 계산 중...", stat_progress)

        stat_rows.sort(
            key=lambda row: float(row[1].replace(",", "")),
            reverse=True,
        )

        # 레벨업 효율 계산 단계 반영 블록
        if progress_callback is not None:
            progress_callback("레벨 효율 계산 중...", 0)

        if cancel_checker is not None:
            cancel_checker()

        # 레벨 1업 효율 출력 행 구성
        level_up: LevelUpEvaluation = evaluate_level_up_delta(
            context=context,
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

        # 경지 효율 계산 단계 반영 블록
        if progress_callback is not None:
            progress_callback("경지 효율 계산 중...", 0)

        if cancel_checker is not None:
            cancel_checker()

        # 다음 경지 효율 출력 행 구성
        realm_result: RealmAdvanceEvaluation | None = evaluate_next_realm_delta(
            context=context,
            current_realm=current_realm,
            level=level,
            target_metric=selected_metric,
        )
        if realm_result is None:
            realm_rows: list[tuple[str, str]] = [
                ("다음 경지", "불가능"),
                ("최적 분배", "불가능"),
            ]
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

        # 스크롤 효율 계산 단계 반영 블록
        if progress_callback is not None:
            progress_callback("스크롤 효율 계산 중...", 0)

        if cancel_checker is not None:
            cancel_checker()

        # 스크롤 +1 효율 출력 행 구성
        scroll_rows: list[tuple[str, str]] = []
        scroll_results: list[ScrollUpgradeEvaluation] = evaluate_scroll_upgrade_deltas(
            server_spec=server_spec,
            preset=preset,
            skills_info=preset.usage_settings,
            delay_ms=delay_ms,
            base_stats=base_stats,
        )
        scroll_count: int = max(1, len(scroll_results))
        scroll_index: int
        scroll_result: ScrollUpgradeEvaluation
        for scroll_index, scroll_result in enumerate(scroll_results, start=1):
            if cancel_checker is not None:
                cancel_checker()

            scroll_rows.append(
                (
                    f"{scroll_result.scroll_name} Lv.{scroll_result.next_level}",
                    cls._format_delta(scroll_result.deltas[selected_metric]),
                )
            )

            if progress_callback is not None:
                scroll_progress: int = 0
                progress_callback("스크롤 효율 계산 중...", scroll_progress)

        scroll_rows.sort(
            key=lambda row: float(row[1].replace(",", "")),
            reverse=True,
        )

        # 사용자 지정 변화량 계산 단계 반영 블록
        if progress_callback is not None:
            progress_callback("사용자 지정 변화량 계산 중...", 0)

        if cancel_checker is not None:
            cancel_checker()

        # 사용자 지정 변화량 결과 행 공용 구성
        custom_rows: list[tuple[str, str]] = cls._build_custom_delta_rows(
            calculator_input=calculator_input,
            context=context,
        )

        # 사용자 지정 변화량 입력 여부
        has_custom_delta: bool = any(
            v != 0.0 for v in calculator_input.custom_stat_changes.values()
        )

        # 최적화 결과 계산 단계 반영 블록
        if progress_callback is not None:
            progress_callback("최적화 결과 계산 중...", 0)

        if cancel_checker is not None:
            cancel_checker()

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
            progress_callback=progress_callback,
            cancel_checker=cancel_checker,
        )
        if optimization_result is None:
            optimization_rows: list[tuple[str, str]] = [("상태", "불가")]
        else:
            title_text: str = "없음"
            if optimization_result.candidate.equipped_title_name is not None:
                for owned_title in calculator_input.owned_titles:
                    if (
                        owned_title.name
                        == optimization_result.candidate.equipped_title_name
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
                talisman_name_map[talisman_name]
                for talisman_name in optimization_result.candidate.equipped_talisman_names
                if talisman_name in talisman_name_map
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

        # 결과 반환 직전 완료 단계 반영 블록
        if progress_callback is not None:
            progress_callback("결과 화면 준비 중...", 100)

        if cancel_checker is not None:
            cancel_checker()

        return cls.OutputRows(
            current_power=current_power_rows,
            stat_efficiency=stat_rows,
            level_up=level_up_rows,
            realm_up=realm_rows,
            scroll_efficiency=scroll_rows,
            custom_delta=custom_rows,
            optimization_result=optimization_rows,
            has_custom_delta=has_custom_delta,
            optimized_base_stats=(
                optimization_result.base_stats
                if optimization_result is not None
                else None
            ),
            selected_metric=selected_metric,
        )

    @classmethod
    def _build_custom_delta_rows(
        cls,
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

            # 기준 입력 위젯 구성 — KVComboInput 으로 KVInput(레벨)과 레이아웃 통일
            self.metric_input = KVComboInput(
                self,
                "기준 전투력",
                [POWER_METRIC_LABELS[metric] for metric in self.metric_options],
                self.on_base_input_changed,
            )
            self.metric_combobox = (
                self.metric_input.combobox
            )  # load_from_preset_state 참조용

            self.level_input_widget: KVInput = KVInput(
                self,
                "레벨",
                "0",
                self.on_base_input_changed,
                max_width=100,
            )
            self.level_input: CustomLineEdit = self.level_input_widget.input

            self.realm_input = KVComboInput(
                self,
                "경지",
                [REALM_TIER_SPECS[realm].label for realm in self.realm_options],
                self.on_base_input_changed,
            )
            self.realm_combobox = (
                self.realm_input.combobox
            )  # load_from_preset_state 참조용

            # 전체 스탯 입력 UI 구성
            self.stats_inputs = self.OverallStatInputs(
                self,
                self.on_base_input_changed,
                self._get_initial_base_stats(),
            )

            # 스크롤 레벨 입력 UI 구성
            self.skills = SkillInputs(
                self,
                SkillInputs.build_entries(),
                self.on_base_input_changed,
                self.popup_manager,
            )

            # 최적화 기준 입력 UI 구성
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

            # 사용자 지정 변화량 입력 UI 구성
            self.custom_delta_inputs = self.OverallStatInputs(
                self,
                self.on_custom_delta_changed,
                self._build_empty_stat_map(),
            )

            # 섹션 카드 조립
            base_card = SectionCard(self, "기준 입력")
            base_row = QHBoxLayout()
            base_row.setContentsMargins(0, 0, 0, 0)
            base_row.setSpacing(20)
            base_row.addWidget(self.metric_input)
            base_row.addWidget(self.level_input_widget)
            base_row.addWidget(self.realm_input)
            base_row.addStretch(1)
            base_card.add_layout(base_row)

            stats_card = SectionCard(self, "전체 스탯")
            stats_card.add_widget(self.stats_inputs)

            scroll_card = SectionCard(self, "스크롤 레벨")
            scroll_card.add_widget(self.skills)

            delta_card = SectionCard(self, "사용자 지정 스탯 변화량")
            delta_card.add_widget(self.custom_delta_inputs)

            opt_card = SectionCard(self, "현재 선택 입력")
            opt_card.add_sub_title("스탯 분배")
            opt_card.add_widget(self.distribution_inputs)
            opt_card.add_separator()
            opt_card.add_sub_title("단전")
            opt_card.add_widget(self.danjeon_inputs)
            opt_card.add_separator()
            opt_card.add_sub_title("칭호 목록")
            opt_card.add_widget(self.title_inputs)
            opt_card.add_separator()
            opt_card.add_sub_title("부적 목록")
            opt_card.add_widget(self.talisman_inputs)

            layout = QVBoxLayout(self)
            layout.addWidget(base_card)
            layout.addWidget(stats_card)
            layout.addWidget(scroll_card)
            layout.addWidget(delta_card)
            layout.addWidget(opt_card)
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

            # 저장된 원시 베이스 스탯의 최종 표시값 복원 블록
            display_base_stats: dict[StatKey, str] = self._get_initial_base_stats()
            for stat_key in STAT_SPECS.keys():
                self.stats_inputs.inputs[stat_key].setText(display_base_stats[stat_key])
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
            COLUMN_COUNT: int = 4

            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
                initial_values: dict[StatKey, str],
            ) -> None:
                super().__init__(parent)
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px solid; }"
                )

                # 전체 스탯 입력칸 맵 구성
                self.inputs: dict[StatKey, CustomLineEdit] = {}
                grid_layout: QGridLayout = QGridLayout(self)

                # 4열 기준 전체 스탯 표시 순서 평탄화
                stat_keys: list[StatKey] = list(OVERALL_STAT_ORDER)
                for item_index, stat_key in enumerate(stat_keys):

                    # 4열 그리드 좌표 계산
                    row_index: int = item_index // self.COLUMN_COUNT
                    column_index: int = item_index % self.COLUMN_COUNT

                    # 이미지 표기와 동일한 라벨 구성
                    stat_spec: str = STAT_SPECS[stat_key]
                    label: str = stat_spec

                    # 스탯 입력 위젯 생성 및 위치 배치
                    item_widget: KVInput = KVInput(
                        self,
                        label,
                        initial_values[stat_key],
                        connected_function,
                        max_width=120,
                    )
                    self.inputs[stat_key] = item_widget.input
                    grid_layout.addWidget(item_widget, row_index, column_index)

                # 4열 배치 간격 고정
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

                    # +/- 부호 기준 색상 코딩
                    try:
                        numeric: float = float(value.replace(",", ""))
                        if numeric > 0:
                            value_label.setStyleSheet("QLabel { color: #27AE60; }")
                        elif numeric < 0:
                            value_label.setStyleSheet("QLabel { color: #E74C3C; }")
                    except ValueError:
                        pass

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
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px solid; }"
                )

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
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px solid; }"
                )

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
                    slot_index: int,
                    data: OwnedTitleStat | None = None,
                ) -> None:
                    super().__init__(parent)
                    self.setStyleSheet(
                        "QFrame { background-color: transparent; border: 0px solid; }"
                    )

                    # 스탯 슬롯 콜백 및 옵션 구성
                    self._connected_function: Callable[[], None] = connected_function
                    self._stat_options: list[StatKey | None] = [None] + list(
                        STAT_SPECS.keys()
                    )

                    # 슬롯 라벨과 입력 위젯 배치
                    layout: QHBoxLayout = QHBoxLayout(self)
                    layout.setContentsMargins(0, 0, 12, 0)
                    layout.setSpacing(4)

                    self.slot_label: QLabel = QLabel(f"스탯 {slot_index}", self)
                    self.slot_label.setFont(CustomFont(10, bold=True))
                    self.slot_label.setMinimumWidth(42)

                    # 수치 라벨 제거 및 콤보박스 높이 정렬
                    self.value_input: CustomLineEdit = CustomLineEdit(
                        self,
                        self._connected_function,
                        "" if data is None else f"{data.value:g}",
                        point_size=10,
                    )
                    self.value_input.setMaximumWidth(100)
                    self.value_input.setFixedHeight(32)

                    # 콤보박스 초기 인덱스 설정 후 시그널 연결
                    self.stat_combobox = CustomComboBox(
                        self,
                        ["미설정"] + list(STAT_SPECS.values()),
                    )
                    self.stat_combobox.setMinimumHeight(32)
                    if data is not None:
                        self.stat_combobox.setCurrentIndex(
                            self._stat_options.index(data.stat_key)
                        )

                    self.stat_combobox.currentIndexChanged.connect(
                        self._on_stat_changed
                    )

                    layout.addWidget(self.slot_label)
                    layout.addWidget(self.stat_combobox)
                    layout.addWidget(self.value_input)
                    self.setLayout(layout)
                    self._apply_slot_state()

                def _on_stat_changed(self) -> None:
                    """스탯 슬롯 선택 변경 처리"""

                    # 슬롯 활성 상태 갱신 후 상위 콜백 전달
                    self._apply_slot_state()
                    self._connected_function()

                def _apply_slot_state(self) -> None:
                    """미설정 슬롯의 입력 상태 반영"""

                    # 미설정 슬롯은 수치 입력 비활성화
                    is_enabled: bool = (
                        self._stat_options[self.stat_combobox.currentIndex()]
                        is not None
                    )
                    self.value_input.setEnabled(is_enabled)
                    if is_enabled:
                        self.value_input.set_valid(True)
                        return

                    self.value_input.setText("")
                    self.value_input.set_valid(True)

                def get_value(self) -> tuple[bool, OwnedTitleStat | None]:
                    """행 데이터 복원"""

                    # 현재 슬롯이 미설정인 경우 None 반환
                    stat_key: StatKey | None = self._stat_options[
                        self.stat_combobox.currentIndex()
                    ]
                    if stat_key is None:
                        self.value_input.set_valid(True)
                        return True, None

                    # 수치 입력 유효성 검증
                    text: str = self.value_input.text()
                    try:
                        value: float = float(text)
                        self.value_input.set_valid(True)
                        return True, OwnedTitleStat(stat_key=stat_key, value=value)

                    except ValueError:
                        self.value_input.set_valid(False)
                        return False, None

            class TitleListItem(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    select_function: Callable[
                        ["ResultsPage.Efficiency.TitleInputs.TitleCard"], None
                    ],
                    equip_function: Callable[
                        ["ResultsPage.Efficiency.TitleInputs.TitleCard"], None
                    ],
                    remove_function: Callable[
                        ["ResultsPage.Efficiency.TitleInputs.TitleCard"], None
                    ],
                    target_card: "ResultsPage.Efficiency.TitleInputs.TitleCard",
                ) -> None:
                    super().__init__(parent)

                    # 목록 항목 대상 카드 및 콜백 보관
                    self._select_function: Callable[
                        [ResultsPage.Efficiency.TitleInputs.TitleCard], None
                    ] = select_function
                    self._equip_function: Callable[
                        [ResultsPage.Efficiency.TitleInputs.TitleCard], None
                    ] = equip_function
                    self._remove_function: Callable[
                        [ResultsPage.Efficiency.TitleInputs.TitleCard], None
                    ] = remove_function
                    self._target_card: ResultsPage.Efficiency.TitleInputs.TitleCard = (
                        target_card
                    )

                    # 목록 항목 전체 레이아웃 구성
                    self.setStyleSheet(
                        "QFrame { background-color: transparent; border: 0px; }"
                    )
                    self.setMinimumHeight(48)
                    layout: QGridLayout = QGridLayout(self)
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(0)

                    # 칭호 선택 버튼 구성
                    self.select_button: QPushButton = QPushButton("", self)
                    self.select_button.setCheckable(True)
                    self.select_button.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.select_button.setMinimumHeight(48)
                    self.select_button.setFont(CustomFont(10, bold=True))
                    self.select_button.setStyleSheet(
                        """
                        QPushButton {
                            background-color: #FFFFFF;
                            color: #2C3E50;
                            border: 1px solid #D9E0EA;
                            border-radius: 6px;
                            padding: 0px 124px 0px 12px;
                            text-align: left;
                        }
                        QPushButton:hover {
                            background-color: #F6FAFF;
                            border: 1px solid #BFD4EC;
                        }
                        QPushButton:checked {
                            background-color: #E8F2FF;
                            border: 1px solid #4A90E2;
                            color: #1F4E79;
                        }
                        """
                    )
                    self.select_button.clicked.connect(self._on_select_clicked)

                    # 목록 상단 액션 버튼 컨테이너 구성
                    self.actions_widget: QWidget = QWidget(self)
                    self.actions_widget.setStyleSheet(
                        "QWidget { background-color: transparent; border: 0px; }"
                    )
                    actions_layout: QHBoxLayout = QHBoxLayout(self.actions_widget)
                    actions_layout.setContentsMargins(0, 0, 8, 0)
                    actions_layout.setSpacing(6)

                    # 목록 상단 장착 버튼 구성
                    self.equip_button: QPushButton = QPushButton("장착 설정", self)
                    self.equip_button.setFixedHeight(24)
                    self.equip_button.setMinimumWidth(74)
                    self.equip_button.setFont(CustomFont(8, bold=True))
                    self.equip_button.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.equip_button.clicked.connect(self._on_equip_clicked)

                    # 목록 상단 삭제 버튼 구성
                    self.remove_button: StyledButton = StyledButton(
                        self, "삭제", kind="danger", point_size=8
                    )
                    self.remove_button.setFixedHeight(24)
                    self.remove_button.clicked.connect(self._on_remove_clicked)

                    actions_layout.addWidget(self.equip_button)
                    actions_layout.addWidget(self.remove_button)
                    self.actions_widget.setLayout(actions_layout)

                    # 칭호 버튼 위 액션 버튼 겹치기 배치
                    layout.addWidget(self.select_button, 0, 0)
                    layout.addWidget(
                        self.actions_widget,
                        0,
                        0,
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                    )
                    self.setLayout(layout)

                    # 장착 버튼 기본 상태 반영
                    self.set_equipped_state(False)

                def _on_select_clicked(self, _checked: bool) -> None:
                    """목록 항목 선택 전달"""

                    self._select_function(self._target_card)

                def _on_equip_clicked(self) -> None:
                    """목록 항목 장착 토글 전달"""

                    self._equip_function(self._target_card)

                def _on_remove_clicked(self) -> None:
                    """목록 항목 삭제 전달"""

                    self._remove_function(self._target_card)

                def set_title_text(self, text: str) -> None:
                    """목록 버튼 표시명 반영"""

                    self.select_button.setText(text)

                def set_selected_state(self, is_selected: bool) -> None:
                    """목록 버튼 선택 상태 반영"""

                    self.select_button.setChecked(is_selected)

                def set_equipped_state(self, is_equipped: bool) -> None:
                    """장착 상태에 맞는 버튼 스타일 반영"""

                    # 장착 상태별 버튼 문구 및 색상 반영
                    if is_equipped:
                        self.equip_button.setText("장착 해제")
                        self.equip_button.setStyleSheet(
                            """
                            QPushButton {
                                background-color: #C97A2B;
                                color: white;
                                border: 0px;
                                border-radius: 4px;
                                padding: 4px 12px;
                            }
                            QPushButton:hover {
                                background-color: #AD6420;
                            }
                            QPushButton:pressed {
                                background-color: #AD6420;
                            }
                            """
                        )
                        return

                    self.equip_button.setText("장착 설정")
                    self.equip_button.setStyleSheet(
                        """
                        QPushButton {
                            background-color: #4A90E2;
                            color: white;
                            border: 0px;
                            border-radius: 4px;
                            padding: 4px 12px;
                        }
                        QPushButton:hover {
                            background-color: #357ABD;
                        }
                        QPushButton:pressed {
                            background-color: #357ABD;
                        }
                        """
                    )

            class TitleCard(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    connected_function: Callable[[], None],
                    data: OwnedTitle | None = None,
                ) -> None:
                    super().__init__(parent)

                    # 우측 편집 카드 외곽 스타일 구성
                    self.setObjectName("TitleCard")
                    self.setStyleSheet(
                        """
                        QFrame#TitleCard {
                            background-color: #F8FAFC;
                            border: 1px solid #DDE5EF;
                            border-radius: 8px;
                        }
                        """
                    )

                    # 편집 카드 콜백 및 슬롯 행 목록 초기화
                    self._connected_function: Callable[[], None] = connected_function
                    self.stat_rows: list[
                        ResultsPage.Efficiency.TitleInputs.TitleStatRow
                    ] = []

                    # 카드 본문 레이아웃 구성
                    root_layout: QVBoxLayout = QVBoxLayout(self)
                    root_layout.setContentsMargins(12, 12, 12, 12)
                    root_layout.setSpacing(8)

                    # 칭호 이름 입력 배치
                    self.name_input_widget: KVInput = KVInput(
                        self,
                        "칭호명",
                        data.name if data is not None else "",
                        connected_function,
                        max_width=220,
                    )
                    self.name_input: CustomLineEdit = self.name_input_widget.input
                    root_layout.addWidget(self.name_input_widget)

                    # 스탯 행 컨테이너 배치
                    self.stats_container: QWidget = QWidget(self)
                    self.stats_container.setStyleSheet("background-color: transparent;")
                    self.stats_layout: QVBoxLayout = QVBoxLayout(self.stats_container)
                    self.stats_layout.setContentsMargins(0, 0, 0, 0)
                    self.stats_layout.setSpacing(6)
                    root_layout.addWidget(self.stats_container)
                    self.setLayout(root_layout)

                    # 3칸 고정 스탯 슬롯 행 구성
                    slot_data_list: list[OwnedTitleStat | None]
                    if data is not None:
                        slot_data_list = data.stats

                    else:
                        slot_data_list = [None] * TITLE_STAT_SLOT_COUNT

                    for slot_index, slot_data in enumerate(slot_data_list, start=1):
                        row = ResultsPage.Efficiency.TitleInputs.TitleStatRow(
                            self.stats_container,
                            self._connected_function,
                            slot_index=slot_index,
                            data=slot_data,
                        )
                        self.stat_rows.append(row)
                        self.stats_layout.addWidget(row)

                def get_display_name(self, fallback_index: int) -> str:
                    """목록/요약용 칭호명 반환"""

                    # 빈 이름 입력 시 임시 표시명 반환
                    name: str = self.name_input.text().strip()
                    if name:
                        return name

                    return f"칭호 {fallback_index}"

                def build_preview_stats(self) -> list[str]:
                    """요약 표시용 스탯 문자열 목록 반환"""

                    # 현재 슬롯 기준 설정된 스탯 문자열 수집
                    preview_lines: list[str] = []
                    for stat_row in self.stat_rows:
                        row_valid: bool
                        title_stat: OwnedTitleStat | None
                        row_valid, title_stat = stat_row.get_value()
                        if not row_valid or title_stat is None:
                            continue

                        stat_label: str = STAT_SPECS[title_stat.stat_key]
                        stat_value_text: str = f"{title_stat.value:+g}"
                        preview_lines.append(f"{stat_label} {stat_value_text}")

                    return preview_lines

                def to_owned_title(self) -> tuple[bool, OwnedTitle]:
                    """카드 데이터를 칭호 모델로 변환"""

                    # 3칸 슬롯 유효성 및 직렬화 데이터 구성
                    is_valid: bool = True
                    stats: list[OwnedTitleStat | None] = []
                    for stat_row in self.stat_rows:
                        row_valid: bool
                        title_stat: OwnedTitleStat | None
                        row_valid, title_stat = stat_row.get_value()
                        is_valid = is_valid and row_valid
                        stats.append(title_stat)

                    # 칭호명과 3칸 슬롯 기반 모델 구성
                    name: str = self.name_input.text().strip()
                    owned_title: OwnedTitle = OwnedTitle(
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
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px solid; }"
                )
                self.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )

                # 칭호 입력 전체 상태 참조 초기화
                self._connected_function: Callable[[], None] = connected_function
                self._cards: list[ResultsPage.Efficiency.TitleInputs.TitleCard] = []
                self._card_items: dict[
                    ResultsPage.Efficiency.TitleInputs.TitleCard,
                    ResultsPage.Efficiency.TitleInputs.TitleListItem,
                ] = {}
                self._selected_card: (
                    ResultsPage.Efficiency.TitleInputs.TitleCard | None
                ) = None
                self._equipped_card: (
                    ResultsPage.Efficiency.TitleInputs.TitleCard | None
                ) = None

                # 3단 패널 레이아웃 구성
                root_layout: QHBoxLayout = QHBoxLayout(self)
                root_layout.setContentsMargins(0, 0, 0, 0)
                root_layout.setSpacing(12)

                # 좌측 장착 요약 패널 구성
                self.equipped_panel: QFrame = QFrame(self)
                self.equipped_panel.setObjectName("TitleEquippedPanel")
                self.equipped_panel.setStyleSheet(
                    """
                    QFrame#TitleEquippedPanel {
                        background-color: #FBFCFE;
                        border: 1px solid #DDE5EF;
                        border-radius: 8px;
                    }
                    """
                )
                self.equipped_panel.setMinimumWidth(230)
                equipped_layout: QVBoxLayout = QVBoxLayout(self.equipped_panel)
                equipped_layout.setContentsMargins(14, 14, 14, 14)
                equipped_layout.setSpacing(10)

                equipped_title: QLabel = QLabel("장착된 칭호", self.equipped_panel)
                equipped_title.setFont(CustomFont(11, bold=True))
                equipped_layout.addWidget(equipped_title)

                self.equipped_name_label: QLabel = QLabel(
                    "장착된 칭호 없음", self.equipped_panel
                )
                self.equipped_name_label.setFont(CustomFont(12, bold=True))
                self.equipped_name_label.setStyleSheet(
                    "QLabel { color: #2C3E50; border: 0px; }"
                )
                equipped_layout.addWidget(self.equipped_name_label)

                self.equipped_stats_container: QWidget = QWidget(self.equipped_panel)
                self.equipped_stats_container.setStyleSheet(
                    "background-color: transparent;"
                )
                self.equipped_stats_layout: QVBoxLayout = QVBoxLayout(
                    self.equipped_stats_container
                )
                self.equipped_stats_layout.setContentsMargins(0, 0, 0, 0)
                self.equipped_stats_layout.setSpacing(6)
                equipped_layout.addWidget(self.equipped_stats_container)
                equipped_layout.addStretch(1)

                self.unequip_button: StyledButton = StyledButton(
                    self.equipped_panel, "장착 해제", kind="normal"
                )
                self.unequip_button.clicked.connect(self._on_unequip_clicked)
                equipped_layout.addWidget(self.unequip_button)

                # 중앙 목록 패널 구성
                self.list_panel: QFrame = QFrame(self)
                self.list_panel.setObjectName("TitleListPanel")
                self.list_panel.setStyleSheet(
                    """
                    QFrame#TitleListPanel {
                        background-color: #FBFCFE;
                        border: 1px solid #DDE5EF;
                        border-radius: 8px;
                    }
                    """
                )
                self.list_panel.setMinimumWidth(220)
                list_layout: QVBoxLayout = QVBoxLayout(self.list_panel)
                list_layout.setContentsMargins(14, 14, 14, 14)
                list_layout.setSpacing(10)

                list_title: QLabel = QLabel("칭호 목록", self.list_panel)
                list_title.setFont(CustomFont(11, bold=True))
                list_layout.addWidget(list_title)

                self.list_scroll_area: QScrollArea = QScrollArea(self.list_panel)
                self.list_scroll_area.setWidgetResizable(True)
                self.list_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
                self.list_scroll_area.setMinimumHeight(180)
                self.list_scroll_area.setStyleSheet(
                    """
                    QScrollArea {
                        background-color: transparent;
                        border: 0px;
                    }
                    """
                )

                self.list_scroll_content: QWidget = QWidget(self.list_scroll_area)
                self.list_scroll_content.setStyleSheet("background-color: transparent;")
                self.title_list_layout: QVBoxLayout = QVBoxLayout(
                    self.list_scroll_content
                )
                self.title_list_layout.setContentsMargins(0, 0, 0, 0)
                self.title_list_layout.setSpacing(8)
                self.title_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                self.list_scroll_content.setLayout(self.title_list_layout)
                self.list_scroll_area.setWidget(self.list_scroll_content)
                list_layout.addWidget(self.list_scroll_area)

                self.add_button: StyledButton = StyledButton(
                    self.list_panel, "칭호 추가", kind="add"
                )
                self.add_button.clicked.connect(lambda _checked=False: self.add_card())
                list_layout.addWidget(self.add_button)

                # 우측 상세 편집 패널 구성
                self.detail_panel: QFrame = QFrame(self)
                self.detail_panel.setObjectName("TitleDetailPanel")
                self.detail_panel.setStyleSheet(
                    """
                    QFrame#TitleDetailPanel {
                        background-color: #FBFCFE;
                        border: 1px solid #DDE5EF;
                        border-radius: 8px;
                    }
                    """
                )
                self.detail_panel.setMinimumWidth(340)
                self.detail_panel.setMinimumHeight(300)
                detail_layout: QVBoxLayout = QVBoxLayout(self.detail_panel)
                detail_layout.setContentsMargins(14, 14, 14, 14)
                detail_layout.setSpacing(10)

                detail_title: QLabel = QLabel("선택된 칭호 설정", self.detail_panel)
                detail_title.setFont(CustomFont(11, bold=True))
                detail_layout.addWidget(detail_title)

                self.detail_stack_host: QWidget = QWidget(self.detail_panel)
                self.detail_stack: QStackedLayout = QStackedLayout(
                    self.detail_stack_host
                )
                self.detail_stack_host.setLayout(self.detail_stack)

                self.empty_detail_label: QLabel = QLabel(
                    "중앙 목록에서 칭호를 선택하세요.", self.detail_stack_host
                )
                self.empty_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.empty_detail_label.setFont(CustomFont(11))
                self.empty_detail_label.setStyleSheet(
                    "QLabel { color: #7A8795; border: 0px; }"
                )
                self.detail_stack.addWidget(self.empty_detail_label)
                detail_layout.addWidget(self.detail_stack_host)

                root_layout.addWidget(self.equipped_panel, 3)
                root_layout.addWidget(self.list_panel, 3)
                root_layout.addWidget(self.detail_panel, 4)
                self.setLayout(root_layout)

                # 초기 비어 있는 장착/상세 상태 반영
                self.refresh_equipped_options()

            def _notify_change(self) -> None:
                """상위 입력 변경 콜백 전달"""

                self._connected_function()

            def _on_card_content_changed(self) -> None:
                """칭호 내용 변경 시 요약/목록 동기화"""

                self.refresh_equipped_options()
                self._notify_change()

            def _on_unequip_clicked(self) -> None:
                """좌측 패널 장착 해제 처리"""

                if self._equipped_card is None:
                    return

                self._equipped_card = None
                self.refresh_equipped_options()
                self._notify_change()

            def _toggle_equipped_card(
                self,
                target_card: "ResultsPage.Efficiency.TitleInputs.TitleCard",
            ) -> None:
                """우측 패널 장착 토글 처리"""

                # 동일 카드 재선택 시 장착 해제 처리
                if self._equipped_card is target_card:
                    self._equipped_card = None

                else:
                    self._equipped_card = target_card

                self.refresh_equipped_options()
                self._notify_change()

            def select_card(
                self,
                target_card: "ResultsPage.Efficiency.TitleInputs.TitleCard",
            ) -> None:
                """중앙 목록 기준 선택 카드 전환"""

                self._selected_card = target_card
                self.refresh_equipped_options()

            def add_card(
                self,
                data: OwnedTitle | None = None,
                emit_change: bool = True,
            ) -> None:
                """칭호 카드 추가"""

                # 신규 편집 카드와 목록 항목 동시 생성
                card = ResultsPage.Efficiency.TitleInputs.TitleCard(
                    self.detail_stack_host,
                    self._on_card_content_changed,
                    data=data,
                )
                list_item = ResultsPage.Efficiency.TitleInputs.TitleListItem(
                    self.list_scroll_content,
                    self.select_card,
                    self._toggle_equipped_card,
                    self.remove_card,
                    card,
                )

                # 내부 카드/목록 참조 등록
                self._cards.append(card)
                self._card_items[card] = list_item
                self.title_list_layout.addWidget(list_item)
                self.detail_stack.addWidget(card)

                # 신규 추가 칭호 기본 선택 처리
                self._selected_card = card
                self.refresh_equipped_options()
                if emit_change:
                    self._notify_change()

            def remove_card(
                self,
                target_card: "ResultsPage.Efficiency.TitleInputs.TitleCard",
                emit_change: bool = True,
            ) -> None:
                """칭호 카드 제거"""

                # 제거 전 현재 인덱스 기반 대체 선택 후보 계산
                target_index: int = self._cards.index(target_card)
                next_selected_card: (
                    ResultsPage.Efficiency.TitleInputs.TitleCard | None
                ) = None
                if len(self._cards) > 1:
                    fallback_index: int = min(target_index, len(self._cards) - 2)
                    next_selected_card = self._cards[fallback_index]

                # 목록 항목과 상세 카드 위젯 제거
                list_item: ResultsPage.Efficiency.TitleInputs.TitleListItem = (
                    self._card_items.pop(target_card)
                )
                self.title_list_layout.removeWidget(list_item)
                list_item.deleteLater()
                self.detail_stack.removeWidget(target_card)

                # 내부 상태 참조에서 대상 카드 제거
                self._cards.remove(target_card)
                target_card.deleteLater()

                # 장착/선택 참조 정리
                if self._equipped_card is target_card:
                    self._equipped_card = None

                if self._selected_card is target_card:
                    self._selected_card = next_selected_card

                self.refresh_equipped_options()
                if emit_change:
                    self._notify_change()

            def refresh_equipped_options(self) -> None:
                """목록 선택/장착/요약 패널 동기화"""

                # 현재 참조 유효성 정리
                if self._selected_card not in self._cards:
                    self._selected_card = self._cards[0] if self._cards else None

                if self._equipped_card not in self._cards:
                    self._equipped_card = None

                # 목록 항목 문구 및 선택 상태 갱신
                for index, card in enumerate(self._cards, start=1):
                    display_name: str = card.get_display_name(index)
                    list_item: ResultsPage.Efficiency.TitleInputs.TitleListItem = (
                        self._card_items[card]
                    )
                    list_item.set_title_text(display_name)
                    list_item.set_selected_state(card is self._selected_card)
                    list_item.set_equipped_state(card is self._equipped_card)

                # 우측 상세 카드 표시 상태 갱신
                if self._selected_card is None:
                    self.detail_stack.setCurrentWidget(self.empty_detail_label)

                else:
                    self.detail_stack.setCurrentWidget(self._selected_card)

                # 좌측 장착 요약 패널 내용 갱신
                self._refresh_equipped_summary()

            def _refresh_equipped_summary(self) -> None:
                """좌측 장착 칭호 요약 패널 갱신"""

                # 기존 장착 스탯 라벨 제거
                while self.equipped_stats_layout.count() > 0:
                    item: QLayoutItem = self.equipped_stats_layout.takeAt(0)
                    widget: QWidget | None = item.widget()
                    if widget is None:
                        continue

                    widget.deleteLater()

                # 장착 칭호 부재 상태 표시
                if self._equipped_card is None:
                    self.equipped_name_label.setText("장착된 칭호 없음")
                    empty_label: QLabel = QLabel(
                        "선택된 장착 칭호가 없습니다.", self.equipped_stats_container
                    )
                    empty_label.setFont(CustomFont(10))
                    empty_label.setStyleSheet("QLabel { color: #7A8795; border: 0px; }")
                    self.equipped_stats_layout.addWidget(empty_label)
                    self.unequip_button.setEnabled(False)
                    return

                # 장착 칭호명 및 스탯 요약 반영
                equipped_index: int = self._cards.index(self._equipped_card) + 1
                equipped_name: str = self._equipped_card.get_display_name(
                    equipped_index
                )
                self.equipped_name_label.setText(equipped_name)
                preview_lines: list[str] = self._equipped_card.build_preview_stats()
                if not preview_lines:
                    empty_stats_label: QLabel = QLabel(
                        "적용된 스탯이 없습니다.", self.equipped_stats_container
                    )
                    empty_stats_label.setFont(CustomFont(10))
                    empty_stats_label.setStyleSheet(
                        "QLabel { color: #7A8795; border: 0px; }"
                    )
                    self.equipped_stats_layout.addWidget(empty_stats_label)

                else:
                    for line in preview_lines:
                        stat_label: QLabel = QLabel(line, self.equipped_stats_container)
                        stat_label.setFont(CustomFont(10, bold=True))
                        stat_label.setStyleSheet(
                            "QLabel { color: #2C3E50; border: 0px; }"
                        )
                        self.equipped_stats_layout.addWidget(stat_label)

                self.unequip_button.setEnabled(True)

            def load(
                self,
                owned_titles: list[OwnedTitle],
                equipped_title_name: str | None,
            ) -> None:
                """저장된 칭호 입력 상태 로드"""

                # 기존 카드 전부 제거
                for card in self._cards.copy():
                    self.remove_card(card, emit_change=False)

                # 저장된 칭호 카드 순서대로 복원
                equipped_card: ResultsPage.Efficiency.TitleInputs.TitleCard | None = (
                    None
                )
                for owned_title in owned_titles:
                    self.add_card(owned_title, emit_change=False)
                    latest_card: ResultsPage.Efficiency.TitleInputs.TitleCard = (
                        self._cards[-1]
                    )
                    if (
                        equipped_title_name is not None
                        and owned_title.name == equipped_title_name
                        and equipped_card is None
                    ):
                        equipped_card = latest_card

                # 선택/장착 초기 상태 반영
                self._selected_card = self._cards[0] if self._cards else None
                self._equipped_card = equipped_card
                self.refresh_equipped_options()

            def build_state(self) -> tuple[bool, list[OwnedTitle], str | None]:
                """현재 칭호 입력 상태 복원"""

                # 카드 목록 기준 보유 칭호 직렬화
                is_valid: bool = True
                owned_titles: list[OwnedTitle] = []
                equipped_title_name: str | None = None
                for card in self._cards:
                    card_valid: bool
                    owned_title: OwnedTitle
                    card_valid, owned_title = card.to_owned_title()
                    is_valid = is_valid and card_valid
                    owned_titles.append(owned_title)
                    if card is self._equipped_card:
                        equipped_title_name = owned_title.name

                return is_valid, owned_titles, equipped_title_name

        class TalismanInputs(QFrame):
            class EquippedSlotPanel(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    slot_index: int,
                    equip_function: Callable[[int], None],
                    unequip_function: Callable[[int], None],
                ) -> None:
                    super().__init__(parent)

                    # 슬롯 패널 고정 인덱스 및 콜백 참조 보관
                    self._slot_index: int = slot_index
                    self._equip_function: Callable[[int], None] = equip_function
                    self._unequip_function: Callable[[int], None] = unequip_function

                    # 슬롯 패널 외곽 스타일 구성
                    self.setObjectName("TalismanEquippedSlotPanel")
                    self.setStyleSheet(
                        """
                        QFrame#TalismanEquippedSlotPanel {
                            background-color: #FFFFFF;
                            border: 1px solid #D9E0EA;
                            border-radius: 6px;
                        }
                        """
                    )

                    # 슬롯 패널 본문 레이아웃 구성
                    root_layout: QVBoxLayout = QVBoxLayout(self)
                    root_layout.setContentsMargins(12, 12, 12, 12)
                    root_layout.setSpacing(8)

                    # 슬롯 번호 안내 라벨 구성
                    self.slot_title_label: QLabel = QLabel(
                        f"부적 슬롯 {slot_index + 1}", self
                    )
                    self.slot_title_label.setFont(CustomFont(10, bold=True))
                    self.slot_title_label.setStyleSheet(
                        "QLabel { color: #5C6B7A; border: 0px; }"
                    )
                    root_layout.addWidget(self.slot_title_label)

                    # 장착 부적 이름 표시 라벨 구성
                    self.name_label: QLabel = QLabel("장착된 부적 없음", self)
                    self.name_label.setFont(CustomFont(11, bold=True))
                    self.name_label.setStyleSheet(
                        "QLabel { color: #2C3E50; border: 0px; }"
                    )
                    root_layout.addWidget(self.name_label)

                    # 장착 부적 스탯 요약 라벨 구성
                    self.stat_label: QLabel = QLabel(
                        "선택된 장착 부적이 없습니다.", self
                    )
                    self.stat_label.setWordWrap(True)
                    self.stat_label.setFont(CustomFont(10))
                    self.stat_label.setStyleSheet(
                        "QLabel { color: #7A8795; border: 0px; }"
                    )
                    root_layout.addWidget(self.stat_label)

                    # 슬롯 장착/해제 버튼 행 구성
                    action_layout: QHBoxLayout = QHBoxLayout()
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    action_layout.setSpacing(6)

                    self.equip_button: QPushButton = QPushButton("선택 부적 장착", self)
                    self.equip_button.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.equip_button.setMinimumHeight(28)
                    self.equip_button.setFont(CustomFont(9, bold=True))
                    self.equip_button.setStyleSheet(
                        """
                        QPushButton {
                            background-color: #4A90E2;
                            color: white;
                            border: 0px;
                            border-radius: 4px;
                            padding: 4px 12px;
                        }
                        QPushButton:hover {
                            background-color: #357ABD;
                        }
                        QPushButton:pressed {
                            background-color: #357ABD;
                        }
                        QPushButton:disabled {
                            background-color: #C9D7E6;
                            color: #F7FAFC;
                        }
                        """
                    )
                    self.equip_button.clicked.connect(self._on_equip_clicked)

                    self.unequip_button: StyledButton = StyledButton(
                        self, "장착 해제", kind="normal", point_size=9
                    )
                    self.unequip_button.setMinimumHeight(28)
                    self.unequip_button.clicked.connect(self._on_unequip_clicked)

                    action_layout.addWidget(self.equip_button)
                    action_layout.addWidget(self.unequip_button)
                    root_layout.addLayout(action_layout)
                    self.setLayout(root_layout)

                def _on_equip_clicked(self) -> None:
                    """선택 카드 슬롯 장착 요청"""

                    self._equip_function(self._slot_index)

                def _on_unequip_clicked(self) -> None:
                    """슬롯 장착 해제 요청"""

                    self._unequip_function(self._slot_index)

                def set_slot_state(
                    self,
                    display_name: str,
                    stat_text: str,
                    has_equipped_card: bool,
                    can_equip_selected_card: bool,
                    is_selected_card_equipped: bool,
                ) -> None:
                    """슬롯 표시 상태 일괄 반영"""

                    # 슬롯 이름 및 스탯 안내 문구 반영
                    self.name_label.setText(display_name)
                    self.stat_label.setText(stat_text)

                    # 장착 유무에 맞는 스탯 문구 색상 반영
                    if has_equipped_card:
                        self.stat_label.setStyleSheet(
                            "QLabel { color: #2C3E50; border: 0px; }"
                        )

                    else:
                        self.stat_label.setStyleSheet(
                            "QLabel { color: #7A8795; border: 0px; }"
                        )

                    # 선택 카드 기준 슬롯 장착 버튼 상태 반영
                    if is_selected_card_equipped:
                        self.equip_button.setText("선택 부적 장착중")
                        self.equip_button.setEnabled(False)

                    elif can_equip_selected_card:
                        self.equip_button.setText("선택 부적 장착")
                        self.equip_button.setEnabled(True)

                    else:
                        self.equip_button.setText("부적 선택 필요")
                        self.equip_button.setEnabled(False)

                    # 현재 슬롯 장착 해제 버튼 활성화 반영
                    self.unequip_button.setEnabled(has_equipped_card)

            class TalismanListItem(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    select_function: Callable[
                        ["ResultsPage.Efficiency.TalismanInputs.TalismanCard"], None
                    ],
                    remove_function: Callable[
                        ["ResultsPage.Efficiency.TalismanInputs.TalismanCard"], None
                    ],
                    target_card: "ResultsPage.Efficiency.TalismanInputs.TalismanCard",
                ) -> None:
                    super().__init__(parent)

                    # 목록 항목 대상 카드 및 콜백 참조 보관
                    self._select_function: Callable[
                        [ResultsPage.Efficiency.TalismanInputs.TalismanCard], None
                    ] = select_function
                    self._remove_function: Callable[
                        [ResultsPage.Efficiency.TalismanInputs.TalismanCard], None
                    ] = remove_function
                    self._target_card: (
                        ResultsPage.Efficiency.TalismanInputs.TalismanCard
                    ) = target_card

                    # 목록 항목 전체 레이아웃 구성
                    self.setStyleSheet(
                        "QFrame { background-color: transparent; border: 0px; }"
                    )
                    self.setMinimumHeight(48)
                    layout: QGridLayout = QGridLayout(self)
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(0)

                    # 목록 선택 버튼 구성
                    self.select_button: QPushButton = QPushButton("", self)
                    self.select_button.setCheckable(True)
                    self.select_button.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.select_button.setMinimumHeight(48)
                    self.select_button.setFont(CustomFont(10, bold=True))
                    self.select_button.setStyleSheet(
                        """
                        QPushButton {
                            background-color: #FFFFFF;
                            color: #2C3E50;
                            border: 1px solid #D9E0EA;
                            border-radius: 6px;
                            padding: 0px 118px 0px 12px;
                            text-align: left;
                        }
                        QPushButton:hover {
                            background-color: #F6FAFF;
                            border: 1px solid #BFD4EC;
                        }
                        QPushButton:checked {
                            background-color: #E8F2FF;
                            border: 1px solid #4A90E2;
                            color: #1F4E79;
                        }
                        """
                    )
                    self.select_button.clicked.connect(self._on_select_clicked)

                    # 목록 우측 상태/삭제 컨테이너 구성
                    self.actions_widget: QWidget = QWidget(self)
                    self.actions_widget.setStyleSheet(
                        "QWidget { background-color: transparent; border: 0px; }"
                    )
                    actions_layout: QHBoxLayout = QHBoxLayout(self.actions_widget)
                    actions_layout.setContentsMargins(0, 0, 8, 0)
                    actions_layout.setSpacing(6)

                    # 장착 슬롯 요약 라벨 구성
                    self.equipped_state_label: QLabel = QLabel("미장착", self)
                    self.equipped_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.equipped_state_label.setMinimumWidth(58)
                    self.equipped_state_label.setFont(CustomFont(8, bold=True))
                    self.equipped_state_label.setStyleSheet(
                        """
                        QLabel {
                            background-color: #EEF2F7;
                            color: #5C6B7A;
                            border: 0px;
                            border-radius: 4px;
                            padding: 4px 8px;
                        }
                        """
                    )
                    actions_layout.addWidget(self.equipped_state_label)

                    # 목록 삭제 버튼 구성
                    self.remove_button: StyledButton = StyledButton(
                        self, "삭제", kind="danger", point_size=8
                    )
                    self.remove_button.setFixedHeight(24)
                    self.remove_button.clicked.connect(self._on_remove_clicked)
                    actions_layout.addWidget(self.remove_button)
                    self.actions_widget.setLayout(actions_layout)

                    # 목록 선택 버튼 위 상태/삭제 컨테이너 겹치기 배치
                    layout.addWidget(self.select_button, 0, 0)
                    layout.addWidget(
                        self.actions_widget,
                        0,
                        0,
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                    )
                    self.setLayout(layout)

                def _on_select_clicked(self, _checked: bool) -> None:
                    """목록 항목 선택 전달"""

                    self._select_function(self._target_card)

                def _on_remove_clicked(self) -> None:
                    """목록 항목 삭제 전달"""

                    self._remove_function(self._target_card)

                def set_title_text(self, text: str) -> None:
                    """목록 버튼 표시명 반영"""

                    self.select_button.setText(text)

                def set_selected_state(self, is_selected: bool) -> None:
                    """목록 버튼 선택 상태 반영"""

                    self.select_button.setChecked(is_selected)

                def set_equipped_slots(self, slot_indexes: list[int]) -> None:
                    """장착 슬롯 요약 문구 반영"""

                    # 미장착 상태 문구 및 색상 반영
                    if not slot_indexes:
                        self.equipped_state_label.setText("미장착")
                        self.equipped_state_label.setStyleSheet(
                            """
                            QLabel {
                                background-color: #EEF2F7;
                                color: #5C6B7A;
                                border: 0px;
                                border-radius: 4px;
                                padding: 4px 8px;
                            }
                            """
                        )
                        return

                    # 장착 슬롯 번호 기반 상태 문구 반영
                    slot_text: str = ", ".join(
                        f"{slot_index + 1}번" for slot_index in slot_indexes
                    )
                    self.equipped_state_label.setText(slot_text)
                    self.equipped_state_label.setStyleSheet(
                        """
                        QLabel {
                            background-color: #EAF5EA;
                            color: #2F855A;
                            border: 0px;
                            border-radius: 4px;
                            padding: 4px 8px;
                        }
                        """
                    )

            class TalismanCard(QFrame):
                def __init__(
                    self,
                    parent: QWidget,
                    connected_function: Callable[[], None],
                    data: OwnedTalisman | None = None,
                ) -> None:
                    super().__init__(parent)

                    # 우측 편집 카드 외곽 스타일 구성
                    self.setObjectName("TalismanCard")
                    self.setStyleSheet(
                        """
                        QFrame#TalismanCard {
                            background-color: #F8FAFC;
                            border: 1px solid #DDE5EF;
                            border-radius: 8px;
                        }
                        """
                    )

                    # 편집 카드 부적 정의와 현재 선택 상태 보관
                    self._connected_function: Callable[[], None] = connected_function
                    self._templates: list[TalismanSpec] = list(TALISMAN_SPECS)
                    self._grade_order: list[TalismanGrade] = []
                    self._templates_by_grade: dict[
                        TalismanGrade,
                        list[TalismanSpec],
                    ] = {}

                    # 데이터에 존재하는 등급 순서대로 그룹 구성
                    grade: TalismanGrade
                    for grade in (
                        TalismanGrade.NORMAL,
                        TalismanGrade.ADVANCED,
                        TalismanGrade.RARE,
                        TalismanGrade.HEROIC,
                        TalismanGrade.LEGENDARY,
                    ):
                        grade_templates: list[TalismanSpec] = [
                            template
                            for template in self._templates
                            if template.grade is grade
                        ]
                        if not grade_templates:
                            continue

                        self._grade_order.append(grade)
                        self._templates_by_grade[grade] = grade_templates

                    # 초기 선택 부적과 등급 상태 결정
                    initial_template: TalismanSpec = self._templates[0]
                    if data is not None:
                        template: TalismanSpec
                        for template in self._templates:
                            if template.name != data.name:
                                continue

                            initial_template = template
                            break

                    self._selected_grade: TalismanGrade = initial_template.grade
                    self._selected_template: TalismanSpec = initial_template
                    self._grade_buttons: dict[TalismanGrade, QPushButton] = {}
                    self._template_buttons: dict[str, QPushButton] = {}

                    # 카드 본문 레이아웃 구성
                    root_layout: QVBoxLayout = QVBoxLayout(self)
                    root_layout.setContentsMargins(12, 12, 12, 12)
                    root_layout.setSpacing(6)

                    # 등급 라벨과 버튼 간격 축소용 섹션 레이아웃 구성
                    grade_section_layout: QVBoxLayout = QVBoxLayout()
                    grade_section_layout.setContentsMargins(0, 0, 0, 0)
                    grade_section_layout.setSpacing(3)

                    # 등급 선택 버튼 영역 구성
                    grade_title: QLabel = QLabel("등급", self)
                    grade_title.setFont(CustomFont(11, bold=True))
                    grade_section_layout.addWidget(grade_title)

                    self.grade_buttons_widget: QWidget = QWidget(self)
                    self.grade_buttons_widget.setStyleSheet(
                        "background-color: transparent;"
                    )
                    grade_layout: QHBoxLayout = QHBoxLayout(self.grade_buttons_widget)
                    grade_layout.setContentsMargins(0, 0, 0, 0)
                    grade_layout.setSpacing(6)

                    for grade in self._grade_order:
                        grade_button: QPushButton = QPushButton(grade.value, self)
                        grade_button.setCheckable(True)
                        grade_button.setCursor(Qt.CursorShape.PointingHandCursor)
                        grade_button.setMinimumHeight(30)
                        grade_button.setFont(CustomFont(9, bold=True))
                        grade_button.clicked.connect(
                            partial(self._set_selected_grade, grade, True)
                        )
                        self._grade_buttons[grade] = grade_button
                        grade_layout.addWidget(grade_button)

                    grade_layout.addStretch(1)
                    self.grade_buttons_widget.setLayout(grade_layout)
                    grade_section_layout.addWidget(self.grade_buttons_widget)
                    root_layout.addLayout(grade_section_layout)

                    # 부적 선택 라벨과 목록 간격 축소용 섹션 레이아웃 구성
                    template_section_layout: QVBoxLayout = QVBoxLayout()
                    template_section_layout.setContentsMargins(0, 0, 0, 0)
                    template_section_layout.setSpacing(3)

                    # 부적 선택 스크롤 영역 구성
                    template_title: QLabel = QLabel("부적 선택", self)
                    template_title.setFont(CustomFont(11, bold=True))
                    template_section_layout.addWidget(template_title)

                    self.template_scroll_area: QScrollArea = QScrollArea(self)
                    self.template_scroll_area.setWidgetResizable(True)
                    self.template_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
                    self.template_scroll_area.setMinimumHeight(150)
                    self.template_scroll_area.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Expanding,
                    )
                    self.template_scroll_area.setStyleSheet(
                        """
                        QScrollArea {
                            background-color: #FFFFFF;
                            border: 1px solid #D9E0EA;
                            border-radius: 6px;
                        }
                        """
                    )

                    self.template_scroll_content: QWidget = QWidget(
                        self.template_scroll_area
                    )
                    self.template_scroll_content.setStyleSheet(
                        "background-color: transparent;"
                    )
                    self.template_list_layout: QVBoxLayout = QVBoxLayout(
                        self.template_scroll_content
                    )
                    self.template_list_layout.setContentsMargins(8, 8, 8, 8)
                    self.template_list_layout.setSpacing(6)
                    self.template_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                    self.template_scroll_content.setLayout(self.template_list_layout)
                    self.template_scroll_area.setWidget(self.template_scroll_content)
                    template_section_layout.addWidget(self.template_scroll_area, 1)
                    root_layout.addLayout(template_section_layout, 1)

                    # 부적 레벨 입력과 스탯 미리보기 가로 배치 구성
                    level_row_layout: QHBoxLayout = QHBoxLayout()
                    level_row_layout.setContentsMargins(0, 0, 0, 0)
                    level_row_layout.setSpacing(10)

                    # 부적 레벨 입력 구성
                    self.level_input_widget: KVInput = KVInput(
                        self,
                        "레벨",
                        f"{data.level if data is not None else 0}",
                        connected_function,
                        max_width=100,
                    )
                    self.level_input: CustomLineEdit = self.level_input_widget.input
                    level_row_layout.addWidget(self.level_input_widget)

                    # 스탯 미리보기 안내 라벨 구성
                    self.preview_label: QLabel = QLabel("", self)
                    self.preview_label.setFont(CustomFont(10))
                    self.preview_label.setWordWrap(True)
                    self.preview_label.setMinimumHeight(
                        self.level_input.sizeHint().height()
                    )
                    self.preview_label.setAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                    self.preview_label.setStyleSheet(
                        "QLabel { color: #5C6B7A; border: 0px; }"
                    )
                    level_row_layout.addWidget(
                        self.preview_label,
                        1,
                        Qt.AlignmentFlag.AlignBottom,
                    )
                    root_layout.addLayout(level_row_layout)
                    self.setLayout(root_layout)

                    # 초기 등급/부적 버튼 상태와 미리보기 반영
                    self._refresh_grade_buttons()
                    self._rebuild_template_buttons()
                    self.refresh_preview_text()

                    # 레벨 변경 시 미리보기 재계산 연결
                    self.level_input.textChanged.connect(self.refresh_preview_text)

                def _set_selected_grade(
                    self,
                    target_grade: TalismanGrade,
                    emit_change: bool = True,
                    _checked: bool = False,
                ) -> None:
                    """등급 버튼 선택 상태 전환"""

                    # 동일 등급 재선택 시 불필요한 갱신 차단
                    if self._selected_grade is target_grade:
                        return

                    # 등급 전환 시 첫 부적 자동 선택 적용
                    self._selected_grade = target_grade
                    self._selected_template = self._templates_by_grade[target_grade][0]
                    self._refresh_grade_buttons()
                    self._rebuild_template_buttons()
                    self.refresh_preview_text()
                    if emit_change:
                        self._connected_function()

                def _set_selected_template(
                    self,
                    target_template: TalismanSpec,
                    emit_change: bool = True,
                    _checked: bool = False,
                ) -> None:
                    """등급 내 부적 선택 상태 전환"""

                    # 동일 부적 재선택 시 불필요한 갱신 차단
                    if self._selected_template.name == target_template.name:
                        return

                    # 부적 변경 시 현재 등급과 미리보기 동기화
                    self._selected_grade = target_template.grade
                    self._selected_template = target_template
                    self._refresh_grade_buttons()
                    self._rebuild_template_buttons()
                    self.refresh_preview_text()
                    if emit_change:
                        self._connected_function()

                def _refresh_grade_buttons(self) -> None:
                    """등급 버튼 선택 상태 스타일 갱신"""

                    # 각 등급 버튼의 체크 상태와 스타일 반영
                    grade: TalismanGrade
                    for grade, grade_button in self._grade_buttons.items():
                        grade_button.setChecked(grade is self._selected_grade)
                        grade_button.setStyleSheet(
                            """
                            QPushButton {
                                background-color: #FFFFFF;
                                color: #2C3E50;
                                border: 1px solid #D9E0EA;
                                border-radius: 6px;
                                padding: 6px 12px;
                            }
                            QPushButton:hover {
                                background-color: #F6FAFF;
                                border: 1px solid #BFD4EC;
                            }
                            QPushButton:checked {
                                background-color: #E8F2FF;
                                border: 1px solid #4A90E2;
                                color: #1F4E79;
                            }
                            """
                        )

                def _rebuild_template_buttons(self) -> None:
                    """선택 등급 기준 부적 선택 버튼 목록 재구성"""

                    # 기존 부적 선택 버튼 위젯 전부 제거
                    while self.template_list_layout.count() > 0:
                        item: QLayoutItem = self.template_list_layout.takeAt(0)
                        widget: QWidget | None = item.widget()
                        if widget is None:
                            continue

                        widget.deleteLater()

                    self._template_buttons.clear()

                    # 현재 등급 부적만 버튼 목록으로 재구성
                    template: TalismanSpec
                    for template in self._templates_by_grade[self._selected_grade]:
                        option_button: QPushButton = QPushButton(
                            self._build_template_option_text(template),
                            self.template_scroll_content,
                        )
                        option_button.setCheckable(True)
                        option_button.setCursor(Qt.CursorShape.PointingHandCursor)
                        option_button.setMinimumHeight(38)
                        option_button.setFont(CustomFont(10, bold=True))
                        option_button.setStyleSheet(
                            """
                            QPushButton {
                                background-color: #FFFFFF;
                                color: #2C3E50;
                                border: 1px solid #D9E0EA;
                                border-radius: 6px;
                                padding: 0px 12px;
                                text-align: left;
                            }
                            QPushButton:hover {
                                background-color: #F6FAFF;
                                border: 1px solid #BFD4EC;
                            }
                            QPushButton:checked {
                                background-color: #E8F2FF;
                                border: 1px solid #4A90E2;
                                color: #1F4E79;
                            }
                            """
                        )
                        option_button.clicked.connect(
                            partial(self._set_selected_template, template, True)
                        )
                        option_button.setChecked(
                            template.name == self._selected_template.name
                        )
                        self._template_buttons[template.name] = option_button
                        self.template_list_layout.addWidget(option_button)

                    self.template_list_layout.addStretch(1)

                def _build_template_option_text(self, template: TalismanSpec) -> str:
                    """부적 선택 버튼 표시 문자열 구성"""

                    # 부적명과 스탯 라벨 결합 문자열 반환
                    stat_label: str = STAT_SPECS[template.stat_key]
                    return f"{template.name} - {stat_label}"

                def refresh_preview_text(self, _text: str = "") -> None:
                    """편집 카드 하단 스탯 미리보기 갱신"""

                    # 현재 부적 설정 기준 스탯 요약 문구 계산
                    preview_text: str = self.build_preview_stat_text()
                    self.preview_label.setText(f"적용 스탯: {preview_text}")

                def get_selected_name(self) -> str:
                    """현재 선택된 부적명 반환"""

                    return self._selected_template.name

                def get_display_name(self, fallback_index: int) -> str:
                    """목록/요약용 부적명 반환"""

                    # 현재 선택된 부적명 우선 반환
                    name: str = self.get_selected_name().strip()
                    if name:
                        return name

                    return f"부적 {fallback_index}"

                def build_preview_stat_text(self) -> str:
                    """요약 표시용 부적 스탯 문자열 반환"""

                    # 현재 입력값 유효성 및 직렬화 데이터 복원
                    is_valid: bool
                    owned_talisman: OwnedTalisman
                    is_valid, owned_talisman = self.to_owned_talisman()
                    if not is_valid:
                        return "레벨 입력 오류"

                    # 선택 부적 정의 기준 스탯 라벨과 수치 계산
                    stat_label: str = STAT_SPECS[self._selected_template.stat_key]
                    stat_value: float = self._selected_template.level_stats[
                        owned_talisman.level
                    ]
                    return f"{stat_label} {stat_value:+g}"

                def to_owned_talisman(self) -> tuple[bool, OwnedTalisman]:
                    """카드 데이터를 보유 부적 모델로 변환"""

                    # 레벨 입력 유효성 검증 및 기본값 보정
                    text: str = self.level_input.text()
                    try:
                        level: int = int(text)
                        is_valid: bool = 0 <= level <= 14
                        self.level_input.set_valid(is_valid)

                    except ValueError:
                        level = 0
                        is_valid = False
                        self.level_input.set_valid(False)

                    # 현재 선택 부적 정의 기반 직렬화 모델 구성
                    owned_talisman: OwnedTalisman = OwnedTalisman(
                        name=self._selected_template.name,
                        level=level,
                    )
                    return is_valid, owned_talisman

            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
            ) -> None:
                super().__init__(parent)
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px solid; }"
                )
                self.setMinimumHeight(300)

                # 부적 입력 전체 상태 참조 초기화
                self._connected_function: Callable[[], None] = connected_function
                self._cards: list[
                    ResultsPage.Efficiency.TalismanInputs.TalismanCard
                ] = []
                self._card_items: dict[
                    ResultsPage.Efficiency.TalismanInputs.TalismanCard,
                    ResultsPage.Efficiency.TalismanInputs.TalismanListItem,
                ] = {}
                self._selected_card: (
                    ResultsPage.Efficiency.TalismanInputs.TalismanCard | None
                ) = None
                self._equipped_cards: list[
                    ResultsPage.Efficiency.TalismanInputs.TalismanCard | None
                ] = [None, None, None]

                # 3단 패널 레이아웃 구성
                root_layout: QHBoxLayout = QHBoxLayout(self)
                root_layout.setContentsMargins(0, 0, 0, 0)
                root_layout.setSpacing(12)

                # 좌측 장착 요약 패널 구성
                self.equipped_panel: QFrame = QFrame(self)
                self.equipped_panel.setObjectName("TalismanEquippedPanel")
                self.equipped_panel.setStyleSheet(
                    """
                    QFrame#TalismanEquippedPanel {
                        background-color: #FBFCFE;
                        border: 1px solid #DDE5EF;
                        border-radius: 8px;
                    }
                    """
                )
                self.equipped_panel.setMinimumWidth(250)
                equipped_layout: QVBoxLayout = QVBoxLayout(self.equipped_panel)
                equipped_layout.setContentsMargins(14, 14, 14, 14)
                equipped_layout.setSpacing(10)

                equipped_title: QLabel = QLabel("장착된 부적", self.equipped_panel)
                equipped_title.setFont(CustomFont(11, bold=True))
                equipped_layout.addWidget(equipped_title)

                # 3개 장착 슬롯 패널 순차 배치
                self.equipped_slot_panels: list[
                    ResultsPage.Efficiency.TalismanInputs.EquippedSlotPanel
                ] = []
                for slot_index in range(3):
                    slot_panel: (
                        ResultsPage.Efficiency.TalismanInputs.EquippedSlotPanel
                    ) = ResultsPage.Efficiency.TalismanInputs.EquippedSlotPanel(
                        self.equipped_panel,
                        slot_index,
                        self._equip_selected_card_to_slot,
                        self._unequip_slot,
                    )
                    self.equipped_slot_panels.append(slot_panel)
                    equipped_layout.addWidget(slot_panel)

                equipped_layout.addStretch(1)

                # 중앙 목록 패널 구성
                self.list_panel: QFrame = QFrame(self)
                self.list_panel.setObjectName("TalismanListPanel")
                self.list_panel.setStyleSheet(
                    """
                    QFrame#TalismanListPanel {
                        background-color: #FBFCFE;
                        border: 1px solid #DDE5EF;
                        border-radius: 8px;
                    }
                    """
                )
                self.list_panel.setMinimumWidth(220)
                list_layout: QVBoxLayout = QVBoxLayout(self.list_panel)
                list_layout.setContentsMargins(14, 14, 14, 14)
                list_layout.setSpacing(10)

                list_title: QLabel = QLabel("부적 목록", self.list_panel)
                list_title.setFont(CustomFont(11, bold=True))
                list_layout.addWidget(list_title)

                self.list_scroll_area: QScrollArea = QScrollArea(self.list_panel)
                self.list_scroll_area.setWidgetResizable(True)
                self.list_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
                self.list_scroll_area.setMinimumHeight(180)
                self.list_scroll_area.setStyleSheet(
                    """
                    QScrollArea {
                        background-color: transparent;
                        border: 0px;
                    }
                    """
                )

                self.list_scroll_content: QWidget = QWidget(self.list_scroll_area)
                self.list_scroll_content.setStyleSheet("background-color: transparent;")
                self.talisman_list_layout: QVBoxLayout = QVBoxLayout(
                    self.list_scroll_content
                )
                self.talisman_list_layout.setContentsMargins(0, 0, 0, 0)
                self.talisman_list_layout.setSpacing(8)
                self.talisman_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                self.list_scroll_content.setLayout(self.talisman_list_layout)
                self.list_scroll_area.setWidget(self.list_scroll_content)
                list_layout.addWidget(self.list_scroll_area)

                self.add_button: StyledButton = StyledButton(
                    self.list_panel, "부적 추가", kind="add"
                )
                self.add_button.clicked.connect(lambda _checked=False: self.add_card())
                list_layout.addWidget(self.add_button)

                # 우측 상세 편집 패널 구성
                self.detail_panel: QFrame = QFrame(self)
                self.detail_panel.setObjectName("TalismanDetailPanel")
                self.detail_panel.setStyleSheet(
                    """
                    QFrame#TalismanDetailPanel {
                        background-color: #FBFCFE;
                        border: 1px solid #DDE5EF;
                        border-radius: 8px;
                    }
                    """
                )
                self.detail_panel.setMinimumWidth(320)
                detail_layout: QVBoxLayout = QVBoxLayout(self.detail_panel)
                detail_layout.setContentsMargins(14, 14, 14, 14)
                detail_layout.setSpacing(10)

                detail_title: QLabel = QLabel("선택된 부적 설정", self.detail_panel)
                detail_title.setFont(CustomFont(11, bold=True))
                detail_layout.addWidget(detail_title)

                self.detail_stack_host: QWidget = QWidget(self.detail_panel)
                self.detail_stack: QStackedLayout = QStackedLayout(
                    self.detail_stack_host
                )
                self.detail_stack_host.setLayout(self.detail_stack)

                self.empty_detail_label: QLabel = QLabel(
                    "중앙 목록에서 부적을 선택하세요.", self.detail_stack_host
                )
                self.empty_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.empty_detail_label.setFont(CustomFont(11))
                self.empty_detail_label.setStyleSheet(
                    "QLabel { color: #7A8795; border: 0px; }"
                )
                self.detail_stack.addWidget(self.empty_detail_label)
                detail_layout.addWidget(self.detail_stack_host)

                root_layout.addWidget(self.equipped_panel, 3)
                root_layout.addWidget(self.list_panel, 3)
                root_layout.addWidget(self.detail_panel, 4)
                self.setLayout(root_layout)

                # 좌측 장착 패널 필요 높이 기준 전체 패널 높이 동기화
                equipped_layout.activate()
                panel_height: int = max(self.equipped_panel.sizeHint().height(), 360)
                self.setFixedHeight(panel_height)
                self.equipped_panel.setFixedHeight(panel_height)
                self.list_panel.setFixedHeight(panel_height)
                self.detail_panel.setFixedHeight(panel_height)

                # 초기 비어 있는 장착/상세 상태 반영
                self.refresh_equipped_options()

            def _notify_change(self) -> None:
                """상위 입력 변경 콜백 전달"""

                self._connected_function()

            def _on_card_content_changed(self) -> None:
                """부적 내용 변경 시 요약/목록 동기화"""

                self.refresh_equipped_options()
                self._notify_change()

            def _equip_selected_card_to_slot(self, slot_index: int) -> None:
                """선택된 부적 카드를 지정 슬롯에 장착"""

                # 선택 카드 부재 시 장착 처리 중단
                if self._selected_card is None:
                    return

                # 기존 슬롯에 있던 동일 카드 참조 우선 제거
                current_slot_index: int
                for current_slot_index, equipped_card in enumerate(
                    self._equipped_cards
                ):
                    if equipped_card is not self._selected_card:
                        continue

                    self._equipped_cards[current_slot_index] = None

                # 대상 슬롯에 선택 카드 장착 후 화면 갱신
                self._equipped_cards[slot_index] = self._selected_card
                self.refresh_equipped_options()
                self._notify_change()

            def _unequip_slot(self, slot_index: int) -> None:
                """지정 슬롯 장착 카드 해제"""

                # 빈 슬롯 해제 요청 차단
                if self._equipped_cards[slot_index] is None:
                    return

                # 슬롯 카드 제거 후 화면 갱신
                self._equipped_cards[slot_index] = None
                self.refresh_equipped_options()
                self._notify_change()

            def select_card(
                self,
                target_card: "ResultsPage.Efficiency.TalismanInputs.TalismanCard",
            ) -> None:
                """중앙 목록 기준 선택 카드 전환"""

                self._selected_card = target_card
                self.refresh_equipped_options()

            def add_card(
                self,
                data: OwnedTalisman | None = None,
                emit_change: bool = True,
            ) -> None:
                """부적 카드 추가"""

                # 신규 편집 카드와 목록 항목 동시 생성
                card: ResultsPage.Efficiency.TalismanInputs.TalismanCard = (
                    ResultsPage.Efficiency.TalismanInputs.TalismanCard(
                        self.detail_stack_host,
                        self._on_card_content_changed,
                        data=data,
                    )
                )
                list_item: ResultsPage.Efficiency.TalismanInputs.TalismanListItem = (
                    ResultsPage.Efficiency.TalismanInputs.TalismanListItem(
                        self.list_scroll_content,
                        self.select_card,
                        self.remove_card,
                        card,
                    )
                )

                # 내부 카드/목록 참조 등록
                self._cards.append(card)
                self._card_items[card] = list_item
                self.talisman_list_layout.addWidget(list_item)
                self.detail_stack.addWidget(card)

                # 신규 추가 부적 기본 선택 처리
                self._selected_card = card
                self.refresh_equipped_options()
                if emit_change:
                    self._notify_change()

            def remove_card(
                self,
                target_card: "ResultsPage.Efficiency.TalismanInputs.TalismanCard",
                emit_change: bool = True,
            ) -> None:
                """부적 카드 제거"""

                # 제거 전 현재 인덱스 기반 대체 선택 후보 계산
                target_index: int = self._cards.index(target_card)
                next_selected_card: (
                    ResultsPage.Efficiency.TalismanInputs.TalismanCard | None
                ) = None
                if len(self._cards) > 1:
                    fallback_index: int = min(target_index, len(self._cards) - 2)
                    next_selected_card = self._cards[fallback_index]

                # 목록 항목과 상세 카드 위젯 제거
                list_item: ResultsPage.Efficiency.TalismanInputs.TalismanListItem = (
                    self._card_items.pop(target_card)
                )
                self.talisman_list_layout.removeWidget(list_item)
                list_item.deleteLater()
                self.detail_stack.removeWidget(target_card)

                # 내부 상태 참조에서 대상 카드 제거
                self._cards.remove(target_card)
                target_card.deleteLater()

                # 장착 슬롯 내 대상 카드 참조 정리
                slot_index: int
                for slot_index, equipped_card in enumerate(self._equipped_cards):
                    if equipped_card is target_card:
                        self._equipped_cards[slot_index] = None

                # 선택 카드 참조 정리
                if self._selected_card is target_card:
                    self._selected_card = next_selected_card

                self.refresh_equipped_options()
                if emit_change:
                    self._notify_change()

            def refresh_equipped_options(self) -> None:
                """목록 선택/장착/요약 패널 동기화"""

                # 현재 선택 카드 참조 유효성 정리
                if self._selected_card not in self._cards:
                    self._selected_card = self._cards[0] if self._cards else None

                # 현재 장착 슬롯 카드 참조 유효성 정리
                slot_index: int
                for slot_index, equipped_card in enumerate(self._equipped_cards):
                    if equipped_card in self._cards:
                        continue

                    self._equipped_cards[slot_index] = None

                # 중앙 목록 표시명 및 장착 슬롯 상태 갱신
                for index, card in enumerate(self._cards, start=1):
                    display_name: str = card.get_display_name(index)
                    list_item: (
                        ResultsPage.Efficiency.TalismanInputs.TalismanListItem
                    ) = self._card_items[card]
                    equipped_slots: list[int] = [
                        slot_position
                        for slot_position, equipped_card in enumerate(
                            self._equipped_cards
                        )
                        if equipped_card is card
                    ]
                    list_item.set_title_text(display_name)
                    list_item.set_selected_state(card is self._selected_card)
                    list_item.set_equipped_slots(equipped_slots)

                # 우측 상세 카드 표시 상태 갱신
                if self._selected_card is None:
                    self.detail_stack.setCurrentWidget(self.empty_detail_label)

                else:
                    self.detail_stack.setCurrentWidget(self._selected_card)

                # 좌측 장착 슬롯 패널 내용 갱신
                self._refresh_equipped_summary()

            def _refresh_equipped_summary(self) -> None:
                """좌측 장착 부적 슬롯 요약 패널 갱신"""

                # 각 슬롯별 장착 부적명과 스탯 요약 반영
                slot_index: int
                for slot_index, slot_panel in enumerate(self.equipped_slot_panels):
                    equipped_card: (
                        ResultsPage.Efficiency.TalismanInputs.TalismanCard | None
                    ) = self._equipped_cards[slot_index]

                    # 빈 슬롯 상태 문구 및 버튼 상태 반영
                    if equipped_card is None:
                        slot_panel.set_slot_state(
                            "장착된 부적 없음",
                            "선택된 장착 부적이 없습니다.",
                            has_equipped_card=False,
                            can_equip_selected_card=(self._selected_card is not None),
                            is_selected_card_equipped=False,
                        )
                        continue

                    # 장착된 카드 이름과 단일 스탯 요약 계산
                    equipped_index: int = self._cards.index(equipped_card) + 1
                    display_name: str = equipped_card.get_display_name(equipped_index)
                    stat_text: str = equipped_card.build_preview_stat_text()
                    slot_panel.set_slot_state(
                        display_name,
                        stat_text,
                        has_equipped_card=True,
                        can_equip_selected_card=(
                            self._selected_card is not None
                            and equipped_card is not self._selected_card
                        ),
                        is_selected_card_equipped=(
                            equipped_card is self._selected_card
                        ),
                    )

            def load(
                self,
                owned_talismans: list[OwnedTalisman],
                equipped_names: list[str],
            ) -> None:
                """저장된 부적 입력 상태 로드"""

                # 기존 카드 전부 제거
                for card in self._cards.copy():
                    self.remove_card(card, emit_change=False)

                # 저장된 부적 카드 순서대로 복원
                for owned_talisman in owned_talismans:
                    self.add_card(owned_talisman, emit_change=False)

                # 저장된 장착 슬롯 이름 기준 카드 참조 복원
                self._equipped_cards = [None, None, None]
                used_cards: list[ResultsPage.Efficiency.TalismanInputs.TalismanCard] = (
                    []
                )
                slot_index: int
                for slot_index in range(min(len(equipped_names), 3)):
                    equipped_name: str = equipped_names[slot_index]
                    if not equipped_name:
                        continue

                    card: ResultsPage.Efficiency.TalismanInputs.TalismanCard
                    for card in self._cards:
                        # 이미 다른 슬롯에 복원된 카드 재사용 방지
                        if any(used_card is card for used_card in used_cards):
                            continue

                        if card.get_selected_name() != equipped_name:
                            continue

                        self._equipped_cards[slot_index] = card
                        used_cards.append(card)
                        break

                # 초기 선택 상태 및 화면 반영
                self._selected_card = self._cards[0] if self._cards else None
                self.refresh_equipped_options()

            def build_state(self) -> tuple[bool, list[OwnedTalisman], list[str]]:
                """현재 부적 입력 상태 복원"""

                # 카드 목록 기준 보유 부적 직렬화
                is_valid: bool = True
                owned_talismans: list[OwnedTalisman] = []
                for card in self._cards:
                    card_valid: bool
                    owned_talisman: OwnedTalisman
                    card_valid, owned_talisman = card.to_owned_talisman()
                    is_valid = is_valid and card_valid
                    owned_talismans.append(owned_talisman)

                # 3칸 슬롯 순서를 유지한 장착 부적 이름 배열 구성
                equipped_names: list[str] = []
                equipped_card: ResultsPage.Efficiency.TalismanInputs.TalismanCard | None
                for equipped_card in self._equipped_cards:
                    if equipped_card is None:
                        equipped_names.append("")
                        continue

                    card_valid: bool
                    owned_talisman: OwnedTalisman
                    card_valid, owned_talisman = equipped_card.to_owned_talisman()
                    is_valid = is_valid and card_valid
                    equipped_names.append(owned_talisman.name)

                return is_valid, owned_talismans, equipped_names

        def _get_preset(self) -> "MacroPreset":
            """현재 선택 프리셋 반환"""

            return app_state.macro.current_preset

        def _get_calculator_realm(self) -> RealmTier:
            """저장된 현재 경지 반환"""

            return self._get_preset().info.calculator.realm_tier

        def _get_initial_base_stats(self) -> dict[StatKey, str]:
            """저장된 베이스 스탯 입력 문자열 맵 반환"""

            # 저장된 원시 베이스 스탯의 최종 표시값 복원 블록
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            resolved_values: dict[StatKey, float] = (
                calculator_input.base_stats.resolve().values
            )
            values: dict[StatKey, str] = {}
            for stat_key in STAT_SPECS.keys():
                values[stat_key] = f"{resolved_values[stat_key]:g}"

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
                calculator_input.equipped_state.equipped_title_name,
            )
            self.talisman_inputs.load(
                calculator_input.owned_talismans,
                calculator_input.equipped_state.equipped_talisman_names,
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
            equipped_title_name: str | None
            title_valid, owned_titles, equipped_title_name = (
                self.title_inputs.build_state()
            )

            talisman_valid: bool
            owned_talismans: list[OwnedTalisman]
            equipped_talisman_names: list[str]
            talisman_valid, owned_talismans, equipped_talisman_names = (
                self.talisman_inputs.build_state()
            )

            equipped_state: EquippedState = EquippedState(
                equipped_title_name=equipped_title_name,
                equipped_talisman_names=equipped_talisman_names,
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

            # 모든 입력칸을 순회하며 최종 표시 스탯 복원 블록
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

            # 최종 표시 스탯의 원시 베이스 스탯 환산 블록
            resolved_input: BaseStats = BaseStats(values=parsed_stats)
            return is_valid, build_internal_base_stats(resolved_input)

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
        @staticmethod
        def _clear_layout_widgets(target_layout: QLayout) -> None:
            """결과 레이아웃 위젯 즉시 분리 및 삭제 예약"""

            while target_layout.count():
                child_item: QLayoutItem = target_layout.takeAt(0)
                child_widget: QWidget | None = child_item.widget()
                child_layout: QLayout | None = child_item.layout()

                # 중첩 레이아웃 내부 항목 순차 제거
                if child_layout is not None:
                    ResultsPage.ResultsView._clear_layout_widgets(child_layout)

                # 기존 위젯 부모 분리 및 삭제 예약
                if child_widget is not None:
                    child_widget.hide()
                    child_widget.setParent(None)
                    child_widget.deleteLater()

        @staticmethod
        def _refresh_widget_geometry(target_widget: QWidget) -> None:
            """현재 콘텐츠 기준 위젯 geometry 재계산"""

            target_layout: QLayout | None = target_widget.layout()
            if target_layout is not None:
                # 최신 콘텐츠 기준 레이아웃 재계산
                target_layout.invalidate()
                target_layout.activate()

            # 최신 sizeHint 반영
            target_widget.updateGeometry()
            target_widget.adjustSize()

        @staticmethod
        def _sync_stack_host_height(start_widget: QWidget) -> None:
            """동적 결과 목록 변경 후 상위 스택/스크롤 높이 재동기화"""

            ancestor: QWidget | None = start_widget
            scroll_area: QScrollArea | None = None
            stack_host: QWidget | None = None
            current_page: QWidget | None = None

            while ancestor is not None:
                # 스크롤 영역 도달 시 탐색 중단 — 스크롤 영역 자체는 리사이즈 불필요
                if isinstance(ancestor, QScrollArea):
                    scroll_area = ancestor
                    break

                ancestor_layout: QLayout | None = ancestor.layout()

                # 메인 스택 호스트 탐색 — adjustSize 전에 식별
                if isinstance(ancestor_layout, QStackedLayout):
                    stack_host = ancestor
                    current_page = ancestor_layout.currentWidget()

                if ancestor_layout is not None:
                    # 부모 레이아웃 sizeHint 무효화 및 재계산
                    ancestor_layout.invalidate()
                    ancestor_layout.activate()

                # sizeHint 변경만 전파 — adjustSize 는 생략하여
                # 스크롤 위치가 중간 리사이즈로 틀어지는 것을 방지
                ancestor.updateGeometry()

                ancestor = ancestor.parentWidget()

            # 현재 페이지 기준 메인 프레임 높이 재고정
            if stack_host is not None and current_page is not None:
                current_layout: QLayout | None = current_page.layout()
                if current_layout is not None:
                    current_layout.invalidate()
                    current_layout.activate()

                current_page.updateGeometry()
                current_height: int = current_page.sizeHint().height()
                if current_height > 0:
                    stack_host.setFixedHeight(current_height)

            # 스크롤바 범위 재조정 후 현재 위치 보정
            if scroll_area is not None:
                vertical_bar: QScrollBar = scroll_area.verticalScrollBar()
                vertical_bar.setValue(min(vertical_bar.value(), vertical_bar.maximum()))
                horizontal_bar: QScrollBar = scroll_area.horizontalScrollBar()
                horizontal_bar.setValue(
                    min(horizontal_bar.value(), horizontal_bar.maximum())
                )

        class PowerResultList(QFrame):
            """현재 전투력 전용 목록 — selected_metric 행 강조"""

            def __init__(self, parent: QWidget) -> None:
                super().__init__(parent)
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px; }"
                )
                self.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred,
                )
                self._layout: QVBoxLayout = QVBoxLayout(self)
                self._layout.setContentsMargins(0, 0, 0, 0)
                self._layout.setSpacing(4)
                self.setLayout(self._layout)

            def set_rows(
                self,
                rows: list[tuple[str, str]],
                selected_label: str = "",
            ) -> None:
                # 이전 결과 행 즉시 제거
                ResultsPage.ResultsView._clear_layout_widgets(self._layout)

                for title, value in rows:
                    is_selected: bool = title == selected_label
                    font_size: int = 13 if is_selected else 11

                    row_widget: QFrame = QFrame(self)
                    if is_selected:
                        row_widget.setStyleSheet(
                            "QFrame { background-color: #EBF5FB;"
                            " border-radius: 4px; border: 0px; }"
                        )
                    else:
                        row_widget.setStyleSheet(
                            "QFrame { background-color: transparent; border: 0px; }"
                        )
                    row_layout: QHBoxLayout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(
                        8, 8 if is_selected else 5, 8, 8 if is_selected else 5
                    )
                    row_layout.setSpacing(10)

                    title_label: QLabel = QLabel(title, row_widget)
                    title_label.setFont(CustomFont(font_size, bold=is_selected))
                    title_label.setStyleSheet(
                        "QLabel { background: transparent; border: 0px; color: #2C3E50; }"
                    )

                    value_label: QLabel = QLabel(value, row_widget)
                    value_label.setFont(CustomFont(font_size, bold=is_selected))
                    value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                    value_label.setStyleSheet(
                        "QLabel { background: transparent; border: 0px; color: #2C3E50; }"
                    )

                    # 행 최소 높이 확보
                    row_widget.setMinimumHeight(
                        max(
                            title_label.sizeHint().height(),
                            value_label.sizeHint().height(),
                        )
                        + 16
                    )
                    row_layout.addWidget(title_label)
                    row_layout.addStretch(1)
                    row_layout.addWidget(value_label)
                    self._layout.addWidget(row_widget)

                # 결과 목록 높이 재고정
                ResultsPage.ResultsView._refresh_widget_geometry(self)

        class RankedResultList(QFrame):
            """순위형 결과 목록 — 미니 바 및 1위 배지 표시"""

            def __init__(self, parent: QWidget) -> None:
                super().__init__(parent)
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px; }"
                )
                self.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred,
                )
                self._rows: list[tuple[str, str]] = []
                self._content_layout: QVBoxLayout = QVBoxLayout(self)
                self._content_layout.setContentsMargins(0, 0, 0, 0)
                self._content_layout.setSpacing(4)
                self.setLayout(self._content_layout)

            def set_rows(self, rows: list[tuple[str, str]]) -> None:
                self._rows = rows
                self._render()

            def _render(self) -> None:
                # 이전 순위 행 즉시 제거
                ResultsPage.ResultsView._clear_layout_widgets(self._content_layout)

                if not self._rows:
                    # 빈 결과 상태 높이 재계산
                    ResultsPage.ResultsView._refresh_widget_geometry(self)
                    return

                # 값 파싱 및 최대 절대값 계산
                numeric_vals: list[float] = []
                max_abs: float = 0.0
                for _, value in self._rows:
                    try:
                        nv: float = float(value.replace(",", ""))
                        numeric_vals.append(nv)
                        if abs(nv) > max_abs:
                            max_abs = abs(nv)
                    except ValueError:
                        numeric_vals.append(0.0)

                for i, (title, value) in enumerate(self._rows):
                    nv = numeric_vals[i]
                    is_best: bool = i == 0 and len(self._rows) > 1

                    row_widget: QFrame = QFrame(self)
                    row_widget.setStyleSheet(
                        "QFrame { background-color: transparent; border: 0px; }"
                    )
                    row_layout: QHBoxLayout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(8, 4, 8, 4)
                    row_layout.setSpacing(8)

                    # 1위 배지
                    badge_label: QLabel = QLabel("★" if is_best else "", row_widget)
                    badge_label.setFixedWidth(14)
                    badge_label.setFont(CustomFont(10))
                    badge_label.setStyleSheet(
                        "QLabel { color: #F39C12; background: transparent; border: 0px; }"
                    )
                    row_layout.addWidget(badge_label)

                    # 항목 이름 — 최소 폭만 보장하고 남는 공간 확장
                    title_label: QLabel = QLabel(title, row_widget)
                    title_label.setFont(CustomFont(11))
                    title_label.setStyleSheet(
                        "QLabel { background: transparent; border: 0px; }"
                    )
                    title_label.setFixedWidth(160)
                    row_layout.addWidget(title_label)

                    row_layout.addStretch(1)

                    # 미니 바 — stretch 오른쪽에 위치해 값과 붙어있음
                    bar_container: QFrame = QFrame(row_widget)
                    bar_container.setFixedSize(80, 10)
                    bar_container.setStyleSheet(
                        "QFrame { background-color: #E8E8E8; border-radius: 3px; border: 0px; }"
                    )
                    if max_abs > 0:
                        bar_fill: QFrame = QFrame(bar_container)
                        bar_fill.setFixedHeight(10)
                        bar_fill.setFixedWidth(max(1, int(80 * abs(nv) / max_abs)))
                        bar_color: str = "#27AE60" if nv >= 0 else "#E74C3C"
                        bar_fill.setStyleSheet(
                            f"QFrame {{ background-color: {bar_color}; border-radius: 3px; border: 0px; }}"
                        )
                    row_layout.addWidget(bar_container)

                    # 값 — 바 바로 오른쪽에 고정폭으로 배치
                    value_label: QLabel = QLabel(value, row_widget)
                    value_label.setFont(CustomFont(11))
                    value_label.setFixedWidth(90)
                    value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                    value_style: str = "background: transparent; border: 0px;"
                    if nv > 0:
                        value_style += " color: #27AE60;"
                    elif nv < 0:
                        value_style += " color: #E74C3C;"
                    value_label.setStyleSheet(f"QLabel {{ {value_style} }}")
                    row_layout.addWidget(value_label)

                    # 순위 행 최소 높이 확보
                    row_widget.setMinimumHeight(
                        max(
                            title_label.sizeHint().height(),
                            value_label.sizeHint().height(),
                        )
                        + 12
                    )
                    self._content_layout.addWidget(row_widget)

                # 순위 목록 높이 재고정
                ResultsPage.ResultsView._refresh_widget_geometry(self)

        class OptimizedStatsGrid(QFrame):
            """최적화 후 전체 스탯 읽기 전용 2열 그리드"""

            def __init__(self, parent: QWidget) -> None:
                super().__init__(parent)
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px; }"
                )
                self.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred,
                )
                self._grid: QGridLayout = QGridLayout(self)
                self._grid.setVerticalSpacing(6)
                self._grid.setHorizontalSpacing(12)
                self.setLayout(self._grid)

            def set_stats(self, base_stats: BaseStats | None) -> None:
                # 이전 스탯 셀 즉시 제거
                ResultsPage.ResultsView._clear_layout_widgets(self._grid)

                if base_stats is None:
                    unavail: QLabel = QLabel("최적화 불가", self)
                    unavail.setFont(CustomFont(11))
                    unavail.setStyleSheet(
                        "QLabel { color: #888888; background: transparent; border: 0px; }"
                    )
                    self._grid.addWidget(unavail, 0, 0)
                    ResultsPage.ResultsView._refresh_widget_geometry(self)
                    return

                final_stats = base_stats.resolve()
                for row_idx, (left_key, right_key) in enumerate(OVERALL_STAT_GRID_ROWS):
                    for col_idx, stat_key in enumerate((left_key, right_key)):
                        if stat_key is None:
                            continue
                        label_text: str = STAT_SPECS[stat_key]
                        value_text: str = f"{final_stats.values[stat_key]:,.2f}"

                        cell: QFrame = QFrame(self)
                        cell.setStyleSheet(
                            "QFrame { background-color: #F5F5F5;"
                            " border-radius: 4px; border: 0px; }"
                        )
                        cell_layout: QHBoxLayout = QHBoxLayout(cell)
                        cell_layout.setContentsMargins(8, 4, 8, 4)
                        cell_layout.setSpacing(6)

                        lbl: QLabel = QLabel(label_text, cell)
                        lbl.setFont(CustomFont(10))
                        lbl.setStyleSheet(
                            "QLabel { color: #555555; background: transparent; border: 0px; }"
                        )

                        val: QLabel = QLabel(value_text, cell)
                        val.setFont(CustomFont(10))
                        val.setAlignment(Qt.AlignmentFlag.AlignRight)
                        val.setStyleSheet(
                            "QLabel { color: #2C3E50; background: transparent; border: 0px; }"
                        )

                        # 스탯 셀 최소 높이 확보
                        cell.setMinimumHeight(
                            max(lbl.sizeHint().height(), val.sizeHint().height()) + 12
                        )
                        cell_layout.addWidget(lbl)
                        cell_layout.addStretch(1)
                        cell_layout.addWidget(val)
                        self._grid.addWidget(cell, row_idx, col_idx)

                # 전체 스탯 그리드 높이 재고정
                ResultsPage.ResultsView._refresh_widget_geometry(self)

        def __init__(
            self,
            parent: QFrame,
        ) -> None:
            super().__init__(parent)
            self.setStyleSheet("QFrame { background-color: transparent; border: 0px; }")

            # 현재 전투력 카드
            self._power_list: ResultsPage.ResultsView.PowerResultList = (
                ResultsPage.ResultsView.PowerResultList(self)
            )
            self._power_card: SectionCard = SectionCard(self, "현재 전투력")
            self._power_card.add_widget(self._power_list)

            # 스탯 1당 효율 + 스크롤 +1 효율 통합 카드
            self._stat_list: ResultsPage.ResultsView.RankedResultList = (
                ResultsPage.ResultsView.RankedResultList(self)
            )
            self._scroll_list: ResultsPage.ResultsView.RankedResultList = (
                ResultsPage.ResultsView.RankedResultList(self)
            )
            _vsep = QFrame(self)
            _vsep.setFixedWidth(1)
            _vsep.setStyleSheet("QFrame { background-color: #E0E0E0; border: 0px; }")
            _vsep.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
            _scroll_wrapper = QWidget(self)
            _scroll_wrapper.setStyleSheet(
                "QWidget { background-color: transparent; border: 0px; }"
            )
            _scroll_wrapper_layout = QVBoxLayout(_scroll_wrapper)
            _scroll_wrapper_layout.setContentsMargins(0, 0, 0, 0)
            _scroll_wrapper_layout.setSpacing(0)
            _scroll_wrapper_layout.addWidget(self._scroll_list)
            _scroll_wrapper_layout.addStretch(1)
            _scroll_wrapper.setLayout(_scroll_wrapper_layout)

            _eff_row: QHBoxLayout = QHBoxLayout()
            _eff_row.setContentsMargins(0, 0, 0, 0)
            _eff_row.setSpacing(10)
            _eff_row.addWidget(self._stat_list)
            _eff_row.addWidget(_vsep)
            _eff_row.addWidget(_scroll_wrapper)
            self._stat_scroll_card: SectionCard = SectionCard(self, "효율 비교")
            self._stat_scroll_card.add_layout(_eff_row)

            # 성장 효율 카드 (레벨업 + 경지)
            self._level_up_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )
            self._realm_up_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            def _make_sub_title(text: str, parent: QWidget) -> QLabel:
                lbl = QLabel(text, parent)
                lbl.setFont(CustomFont(11, bold=True))
                lbl.setStyleSheet(
                    "QLabel { background-color: transparent; border: 0px;"
                    " color: #555555; }"
                )
                return lbl

            _level_wrapper = QWidget(self)
            _level_wrapper.setStyleSheet(
                "QWidget { background-color: transparent; border: 0px; }"
            )
            _level_wrapper_layout = QVBoxLayout(_level_wrapper)
            _level_wrapper_layout.setContentsMargins(0, 0, 0, 0)
            _level_wrapper_layout.setSpacing(6)
            _level_wrapper_layout.addWidget(_make_sub_title("레벨 1업", _level_wrapper))
            _level_wrapper_layout.addWidget(self._level_up_list)
            _level_wrapper_layout.addStretch(1)
            _level_wrapper.setLayout(_level_wrapper_layout)

            _realm_wrapper = QWidget(self)
            _realm_wrapper.setStyleSheet(
                "QWidget { background-color: transparent; border: 0px; }"
            )
            _realm_wrapper_layout = QVBoxLayout(_realm_wrapper)
            _realm_wrapper_layout.setContentsMargins(0, 0, 0, 0)
            _realm_wrapper_layout.setSpacing(6)
            _realm_wrapper_layout.addWidget(
                _make_sub_title("다음 경지", _realm_wrapper)
            )
            _realm_wrapper_layout.addWidget(self._realm_up_list)
            _realm_wrapper_layout.addStretch(1)
            _realm_wrapper.setLayout(_realm_wrapper_layout)

            _growth_vsep = QFrame(self)
            _growth_vsep.setFixedWidth(1)
            _growth_vsep.setStyleSheet(
                "QFrame { background-color: #E0E0E0; border: 0px; }"
            )
            _growth_vsep.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )

            _growth_row: QHBoxLayout = QHBoxLayout()
            _growth_row.setContentsMargins(0, 0, 0, 0)
            _growth_row.setSpacing(10)
            _growth_row.addWidget(_level_wrapper)
            _growth_row.addWidget(_growth_vsep)
            _growth_row.addWidget(_realm_wrapper)

            self._growth_card: SectionCard = SectionCard(self, "성장 효율")
            self._growth_card.add_layout(_growth_row)

            # 사용자 지정 변화량 카드 (조건부 표시)
            self._custom_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )
            self._custom_card: SectionCard = SectionCard(
                self, "사용자 지정 변화량 결과"
            )
            self._custom_card.add_widget(self._custom_list)
            self._custom_card.setVisible(False)

            # 최적화 결과 카드
            self._opt_result_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )
            self._opt_stats_grid: ResultsPage.ResultsView.OptimizedStatsGrid = (
                ResultsPage.ResultsView.OptimizedStatsGrid(self)
            )
            self._opt_card: SectionCard = SectionCard(self, "최적화 결과")
            self._opt_card.add_widget(self._opt_result_list)
            self._opt_card.add_separator()
            self._opt_card.add_sub_title("최적화 후 전체 스탯")
            self._opt_card.add_widget(self._opt_stats_grid)

            layout: QVBoxLayout = QVBoxLayout(self)
            layout.addWidget(self._power_card)
            layout.addWidget(self._stat_scroll_card)
            layout.addWidget(self._growth_card)
            layout.addWidget(self._custom_card)
            layout.addWidget(self._opt_card)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        def set_error_outputs(self) -> None:
            """결과 페이지 오류 상태 출력"""

            error_rows: list[tuple[str, str]] = [("상태", "오류")]
            self._power_list.set_rows(error_rows)
            self._stat_list.set_rows(error_rows)
            self._level_up_list.set_rows(error_rows)
            self._realm_up_list.set_rows(error_rows)
            self._scroll_list.set_rows(error_rows)
            self._custom_card.setVisible(False)
            self._opt_result_list.set_rows(error_rows)
            self._opt_stats_grid.set_stats(None)

        def set_loading_outputs(self) -> None:
            """계산 시작 시 로딩 상태 출력"""

            loading_rows: list[tuple[str, str]] = [("상태", "계산 중...")]
            self._power_list.set_rows(loading_rows)
            self._stat_list.set_rows(loading_rows)
            self._level_up_list.set_rows(loading_rows)
            self._realm_up_list.set_rows(loading_rows)
            self._scroll_list.set_rows(loading_rows)
            self._custom_card.setVisible(False)
            self._opt_result_list.set_rows(loading_rows)
            self._opt_stats_grid.set_stats(None)

        def set_output_rows(self, output_rows: ResultsPage.OutputRows) -> None:
            """백그라운드 계산 완료 결과 UI 반영"""

            # 완료된 결과 구조를 각 카드에 반영 블록
            selected_label: str = POWER_METRIC_LABELS[output_rows.selected_metric]
            self._power_list.set_rows(output_rows.current_power, selected_label)
            self._stat_list.set_rows(output_rows.stat_efficiency)
            self._level_up_list.set_rows(output_rows.level_up)
            self._realm_up_list.set_rows(output_rows.realm_up)
            self._scroll_list.set_rows(output_rows.scroll_efficiency)
            self._custom_card.setVisible(output_rows.has_custom_delta)
            if output_rows.has_custom_delta:
                self._custom_list.set_rows(output_rows.custom_delta)
            self._opt_result_list.set_rows(output_rows.optimization_result)
            self._opt_stats_grid.set_stats(output_rows.optimized_base_stats)


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
        else:
            self.setStyleSheet("QFrame { background-color: transparent; border: 0px; }")

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
            else:
                self.setStyleSheet(
                    "QFrame { background-color: transparent; border: 0px; }"
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
