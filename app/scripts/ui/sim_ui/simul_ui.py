from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QRect,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QClipboard,
    QColor,
    QGuiApplication,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
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
    CALCULATOR_SKILL_SPEED_LIMIT_PERCENT,
    DISPLAY_POWER_METRICS,
    POWER_METRIC_LABELS,
    TIMELINE_DAMAGE_INPUT_ERROR_MESSAGE,
    build_calculator_context,
    build_calculator_timeline,
    build_damage_events,
    build_internal_base_stats,
    evaluate_official_power,
    evaluate_arbitrary_stat_delta,
    evaluate_level_up_delta,
    evaluate_next_realm_delta,
    evaluate_scroll_upgrade_deltas,
    evaluate_single_stat_delta,
    CandidateGroupSelectionResult,
    OptimizationFailure,
    optimize_current_selection,
    select_candidate_groups,
)
from app.scripts.calculator_models import (
    OVERALL_STAT_GRID_ROWS,
    OVERALL_STAT_ORDER,
    REALM_TIER_SPECS,
    STAT_SPECS,
    BaseStats,
    CalculatorPresetInput,
    CustomPowerFormula,
    DanjeonState,
    DistributionState,
    OptimizationCandidateGroup,
    StatKey,
    TargetDanjeonState,
    TargetDistributionState,
)
from app.scripts.character_engine import (
    CalculatorInputFill,
    build_calculator_input_fill,
)
from app.scripts.character_models import CharacterProfile
from app.scripts.custom_classes import (
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
    get_theme_image_path,
    resource_registry,
)
from app.scripts.simulate_macro import simulate_random_from_calculator
from app.scripts.ui.sim_ui.candidate_group_inputs import CandidateGroupInputs
from app.scripts.ui.popup import (
    CustomPowerFormulaManageDialog,
    NoticeKind,
    PopupManager,
)
from app.scripts.ui.themes import theme_manager

if TYPE_CHECKING:
    from PIL import Image

    from app.scripts.ui.character_ui import CharacterPage
    from app.scripts.calculator_engine import (
        EvaluationContext,
        FinalStats,
        GraphAnalysis,
        GraphDamageEvent,
        GraphReport,
        DamageEvent,
        LevelUpEvaluation,
        OptimizationResult,
        RealmAdvanceEvaluation,
        ScrollUpgradeEvaluation,
    )
    from app.scripts.calculator_models import (
        RealmTier,
    )
    from app.scripts.macro_models import MacroPreset
    from app.scripts.ocr import OcrStatCandidate
    from app.scripts.registry.server_registry import ServerSpec
    from app.scripts.registry.skill_registry import ScrollDef, SkillDef
    from app.scripts.ui.main_window import MainWindow
    from app.scripts.ui.popup import HoverCardData


def _build_formula_label_map(
    custom_formulas: list[CustomPowerFormula],
) -> dict[str, str]:
    """전역 공식 목록 기준 빌트인/커스텀 공식 ID → 표시명 맵 구성"""

    # 빌트인 공식 표시명을 먼저 고정 순서로 등록
    formula_labels: dict[str, str] = {
        power_metric.value: POWER_METRIC_LABELS[power_metric]
        for power_metric in DISPLAY_POWER_METRICS
    }

    # 전역 저장된 커스텀 공식 표시명을 뒤에 추가
    custom_formula: CustomPowerFormula
    for custom_formula in custom_formulas:
        formula_labels[custom_formula.id] = custom_formula.name

    return formula_labels


def _build_formula_options(
    custom_formulas: list[CustomPowerFormula],
) -> list[str]:
    """전역 공식 목록 기준 공식 드롭다운 순서 목록 구성"""

    # 빌트인 공식 뒤에 커스텀 공식을 저장 순서대로 연결
    formula_ids: list[str] = [
        power_metric.value for power_metric in DISPLAY_POWER_METRICS
    ]
    formula_ids.extend(custom_formula.id for custom_formula in custom_formulas)
    return formula_ids


@dataclass(frozen=True, slots=True)
class _CalculatorResultsCacheKey:
    """계산 결과 페이지 캐시 식별자"""

    server_id: str
    delay_ms: int
    calculator_input_data: str
    equipped_scrolls: tuple[str, ...]
    placed_skills: tuple[str, ...]
    skill_definitions: tuple[tuple[str, tuple[tuple[int, float], ...], float, int], ...]
    scroll_levels: tuple[tuple[str, int], ...]
    usage_settings: tuple[tuple[str, tuple[bool, bool, int]], ...]
    link_skills: tuple[tuple[str, str, str | None, tuple[str, ...]], ...]
    custom_formulas: tuple[tuple[str, str, str], ...]


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
        self.main_frame.setObjectName("simMainFrame")

        self.main_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        # 무공비급바
        self.scroll_area: QScrollArea = QScrollArea(self.parent)
        self.scroll_area.setObjectName("simScrollArea")
        self.scroll_area.setWidget(self.main_frame)
        # 위젯이 무공비급 영역에 맞춰 크기 조절되도록
        self.scroll_area.setWidgetResizable(True)

        # 무공비급바 무공비급 설정
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

        # 계산기 첫 진입 필수 페이지 구성
        self._input_page: InputPage = InputPage(self.main_frame, self.popup_manager)
        self._graph_page: GraphPage | None = None
        self._results_page: ResultsPage | None = None
        self._character_page: CharacterPage | None = None
        self.stacked_layout.addWidget(self._input_page)

        # 네비게이션 인덱스 보존용 지연 페이지 자리 구성
        self._page_placeholders: dict[int, QWidget] = {}
        for page_index in (1, 2, 3):
            placeholder: QWidget = QWidget(self.main_frame)
            self._page_placeholders[page_index] = placeholder
            self.stacked_layout.addWidget(placeholder)

        # 결과 계산 오버레이와 백그라운드 스레드 구성
        self._results_overlay: _CalculationOverlay = _CalculationOverlay(
            self.parent,
            self._cancel_results_calculation,
        )
        self._input_confirm_overlay: _CalculationInputConfirmOverlay = (
            _CalculationInputConfirmOverlay(
                self.parent,
                self._start_results_calculation,
            )
        )
        self._character_apply_confirm_overlay: _CalculationInputConfirmOverlay = (
            _CalculationInputConfirmOverlay(
                self.parent,
                self._apply_character_to_calculator,
                title="계산기에 적용",
                message="이 캐릭터의 스탯을 계산기 입력에 적용합니다.",
                confirm_text="적용",
                show_summary=False,
            )
        )
        self._pending_character_fill: CalculatorInputFill | None = None
        self._calc_thread: _CalculatorThread | None = None
        self._results_cache_key: _CalculatorResultsCacheKey | None = None
        self._results_cache_output_rows: ResultsPage.OutputRows | None = None
        self._pending_results_cache_key: _CalculatorResultsCacheKey | None = None

        self.stacked_layout.setCurrentIndex(0)
        # 스택 레이아웃 설정
        self.main_frame.setLayout(self.stacked_layout)

        self.adjust_main_frame_height()

    @property
    def input_page(self) -> InputPage:
        """계산기 입력 페이지 반환"""

        # 첫 진입 시 즉시 생성된 입력 페이지 재사용
        return self._input_page

    @property
    def graph_page(self) -> GraphPage:
        """그래프 페이지를 최초 접근 시 생성하고 이후 재사용"""

        # 시뮬레이터 탭 최초 진입 시 그래프 페이지 생성
        if self._graph_page is None:
            self._graph_page = GraphPage(self.main_frame)
            self._replace_lazy_page(1, self._graph_page)

        return self._graph_page

    @property
    def results_page(self) -> ResultsPage:
        """결과 페이지를 최초 접근 시 생성하고 이후 재사용"""

        # 결과 계산 최초 요청 시 결과 페이지 생성
        if self._results_page is None:
            self._results_page = ResultsPage(self.main_frame)
            self._replace_lazy_page(2, self._results_page)

        return self._results_page

    @property
    def character_page(self) -> "CharacterPage":
        """캐릭터 페이지를 최초 접근 시 생성하고 이후 재사용"""

        # 캐릭터 탭 최초 진입 시 캐릭터 모듈 로드 및 페이지 생성
        if self._character_page is None:
            from app.scripts.ui.character_ui import CharacterPage

            self._character_page = CharacterPage(
                self.main_frame,
                self._use_character_for_calculator,
            )
            self._replace_lazy_page(3, self._character_page)

        return self._character_page

    def _replace_lazy_page(self, page_index: int, page: QWidget) -> None:
        """지연 페이지 자리 위젯을 실제 페이지로 교체"""

        # 네비게이션 인덱스 유지 상태로 자리 위젯 제거
        placeholder: QWidget = self._page_placeholders.pop(page_index)
        self.stacked_layout.removeWidget(placeholder)
        placeholder.deleteLater()

        # 기존 자리 위치에 실제 페이지 삽입
        self.stacked_layout.insertWidget(page_index, page)

    def _use_character_for_calculator(self, profile: CharacterProfile) -> None:
        """캐릭터 상태를 계산기 입력에 반영하기 전 확인 오버레이 표시"""

        # 적용 시점에 사용할 합산 결과를 미리 계산해 보관
        fill: CalculatorInputFill = build_calculator_input_fill(profile)
        self._pending_character_fill = fill
        self._character_apply_confirm_overlay.show_confirmation()

    def _apply_character_to_calculator(self) -> None:
        """확인 후 캐릭터 상태를 계산기 입력 페이지에 반영"""

        fill: CalculatorInputFill | None = self._pending_character_fill
        if fill is None:
            return

        self._pending_character_fill = None
        calculator_input: CalculatorPresetInput = (
            app_state.macro.current_preset.info.calculator
        )

        # 전체 스탯 입력칸 표시값을 계산기 내부 원시 스탯으로 저장
        resolved_base_stats: BaseStats = BaseStats.from_stat_map(fill.overall_stats)
        calculator_input.base_stats = build_internal_base_stats(resolved_base_stats)

        # 캐릭터 기본 정보와 분배 입력값 반영
        calculator_input.level = fill.level
        calculator_input.realm_tier = fill.realm_tier
        calculator_input.distribution = fill.distribution
        calculator_input.danjeon = fill.danjeon

        save_data()
        self.input_page.editor.apply_character_fill_inputs()
        self.update_nav(0)
        self.stacked_layout.setCurrentIndex(0)
        self.adjust_main_frame_height()

    def on_enter(self) -> None:
        """메인 화면에서 계산기 화면으로 진입

        내부 페이지를 입력 화면으로 되돌리고
        메인 화면에서 변경된 무공비급 레벨 등을 입력 위젯에 동기화
        """
        if self.stacked_layout.currentIndex() != 0:
            self.stacked_layout.setCurrentIndex(0)
            self.update_nav(0)
            self.adjust_main_frame_height()

        self.input_page.editor.on_calculator_enter()

    def change_layout(self, index: int) -> None:
        # 캐릭터 탭은 검증/계산 없이 즉시 전환
        if index == 3:
            if index == self.stacked_layout.currentIndex():
                return

            character_page: CharacterPage = self.character_page
            self.update_nav(3)
            self.stacked_layout.setCurrentWidget(character_page)
            self.adjust_main_frame_height()
            return

        # 결과 페이지 계산 중 중복 진입 차단
        if (
            index == 2
            and self._calc_thread is not None
            and self._calc_thread.isRunning()
        ):
            return

        # 결과 계산 전 현재 입력 검증 및 확인 오버레이 표시
        if index == 2:
            if not self.input_page.editor.prepare_results_inputs():
                self.master.get_popup_manager().show_notice(
                    NoticeKind.SIM_INPUT_ERROR,
                    self.input_page.editor.last_input_error_message,
                )
                return

            self._input_confirm_overlay.show_confirmation(
                app_state.macro.current_preset.info.calculator
            )
            return

        # 입력값 확인
        if index == 1 and not self.input_page.editor.has_valid_navigation_inputs():
            self.master.get_popup_manager().show_notice(
                NoticeKind.SIM_INPUT_ERROR,
                self.input_page.editor.last_input_error_message,
            )
            return

        if index == self.stacked_layout.currentIndex():
            return

        # 전환 대상 페이지 위젯 확인
        target_widget: QWidget = self.stacked_layout.widget(index)

        # 그래프 페이지 진입 직전 현재 계산기 입력 기준 결과 재생성
        if index == 1:
            graph_page: GraphPage = self.graph_page
            graph_page.refresh()
            target_widget = graph_page

        # 네비게이션 버튼 색 변경
        self.update_nav(index)

        # 레이아웃 변경
        self.stacked_layout.setCurrentWidget(target_widget)

        self.adjust_main_frame_height()

    def start_results_calculation_without_confirmation(self) -> bool:
        """입력 확인창 없이 현재 계산기 입력으로 결과 계산 시작"""

        # 현재 입력 검증 및 계산 상태 반영
        if not self.input_page.editor.prepare_results_inputs():
            self.master.get_popup_manager().show_notice(
                NoticeKind.SIM_INPUT_ERROR,
                self.input_page.editor.last_input_error_message,
            )
            return False

        # 기존 확인 오버레이 숨김 후 결과 계산 실행
        self._input_confirm_overlay.hide()
        self._start_results_calculation()

        # 진행 중 결과 페이지를 즉시 표시해 가이드 대상 영역 확보
        if self._calc_thread is not None and self._calc_thread.isRunning():
            results_page: ResultsPage = self.results_page
            self.update_nav(2)
            self.stacked_layout.setCurrentWidget(results_page)
            self.adjust_main_frame_height()
            QTimer.singleShot(0, self.adjust_main_frame_height)

        return True

    def show_results_page(self) -> None:
        """이미 시작된 결과 계산의 결과 페이지로 전환

        결과 페이지는 계산 시작 시점에 로딩/결과 상태를 보유하므로,
        다른 하위 페이지에서 돌아왔을 때 재계산 없이 전환만 수행한다.
        """

        results_page: ResultsPage = self.results_page
        self.update_nav(2)
        self.stacked_layout.setCurrentWidget(results_page)
        self.adjust_main_frame_height()
        QTimer.singleShot(0, self.adjust_main_frame_height)

    def update_nav(self, index: int) -> None:
        """
        내비게이션 버튼 색 업데이트
        """

        for i in range(4):
            btn = self.nav.buttons[i]
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def adjust_main_frame_height(self) -> None:
        """현재 표시 중인 UI 높이에 맞춰 메인 프레임 높이를 동기화."""

        current_widget: QWidget | None = self.stacked_layout.currentWidget()
        if current_widget is None:
            return

        # 캐릭터 페이지는 3분할 셸이 화면을 꽉 채우도록 viewport 높이에 맞춘다
        # (외곽 세로 무공비급은 숨기고, 내부 패널 스크롤만 사용)
        if self._character_page is not None and current_widget is self._character_page:
            self.scroll_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            viewport_height: int = self.scroll_area.viewport().height()
            if viewport_height > 0:
                self.main_frame.setFixedHeight(viewport_height)
            return

        # 그 외 페이지는 기존 세로 무공비급 항상 표시 정책 유지
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )

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

        # 무공비급 위치 범위 보정
        vertical_bar: QScrollBar = self.scroll_area.verticalScrollBar()
        vertical_bar.setValue(min(vertical_bar.value(), vertical_bar.maximum()))
        horizontal_bar: QScrollBar = self.scroll_area.horizontalScrollBar()
        horizontal_bar.setValue(min(horizontal_bar.value(), horizontal_bar.maximum()))

    def on_window_resized(self) -> None:
        """윈도우 크기 변경 시 캐릭터 페이지 높이를 viewport 높이에 다시 맞춘다

        캐릭터 페이지는 메인 프레임 높이를 viewport 높이로 고정하는데,
        창 크기 변경만으로는 이 값이 갱신되지 않아 위아래 크기가 어긋난다.
        """

        if (
            self._character_page is not None
            and self.stacked_layout.currentWidget() is self._character_page
        ):
            self.adjust_main_frame_height()

    def _start_results_calculation(self) -> None:
        """현재 페이지 유지 상태로 결과 페이지 계산 시작"""

        # 중복 계산 요청 차단
        if self._calc_thread is not None and self._calc_thread.isRunning():
            return

        # 현재 입력 기준 계산 결과 캐시 키 구성
        cache_key: _CalculatorResultsCacheKey = self._build_results_cache_key()
        cached_output_rows: ResultsPage.OutputRows | None = (
            self._results_cache_output_rows
        )

        # 동일 입력 캐시가 있으면 백그라운드 계산 없이 결과 페이지 표시
        if self._results_cache_key == cache_key and cached_output_rows is not None:
            results_page: ResultsPage = self.results_page
            results_page.set_output_rows(cached_output_rows)
            self.update_nav(2)
            self.stacked_layout.setCurrentWidget(results_page)
            self.adjust_main_frame_height()
            QTimer.singleShot(0, self.adjust_main_frame_height)
            return

        # 저장된 계산기 입력 기준 계산 인자 복원
        preset: MacroPreset = app_state.macro.current_preset
        calculator_input: CalculatorPresetInput = preset.info.calculator
        base_stats: BaseStats = calculator_input.base_stats
        level: int = calculator_input.level
        selected_formula_id: str = calculator_input.selected_formula_id
        custom_formulas: tuple[CustomPowerFormula, ...] = tuple(
            app_state.macro.custom_power_formulas
        )

        # 결과 페이지 초기 상태와 진행 오버레이 표시
        self._pending_results_cache_key = cache_key
        self.results_page.set_loading_state()
        self._results_overlay.show_overlay(
            "스탯 계산기 결과 준비 중...", "대기 중...", 0
        )

        # 백그라운드 계산 스레드 연결
        self._calc_thread = _CalculatorThread(
            server_spec=app_state.macro.current_server,
            preset=preset,
            delay_ms=app_state.macro.current_delay,
            base_stats=base_stats,
            calculator_input=calculator_input,
            level=level,
            selected_formula_id=selected_formula_id,
            custom_formulas=custom_formulas,
        )
        self._calc_thread.progress_signal.connect(self._on_results_calculation_progress)
        self._calc_thread.finished_signal.connect(self._on_results_calculation_finished)
        self._calc_thread.finished.connect(self._cleanup_calc_thread)
        self._calc_thread.start()

    def _build_results_cache_key(self) -> _CalculatorResultsCacheKey:
        """현재 계산 결과 페이지 입력 기준 캐시 키 구성"""

        # 현재 프리셋과 계산기 입력 상태 복원
        preset: MacroPreset = app_state.macro.current_preset
        calculator_input: CalculatorPresetInput = preset.info.calculator

        # 계산기 입력 저장 구조를 안정적인 문자열 키로 변환
        calculator_input_data: str = json.dumps(
            calculator_input.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
        )

        # 무공비급 레벨 맵을 순서 고정 튜플로 변환
        scroll_levels: tuple[tuple[str, int], ...] = tuple(
            (scroll_id, int(preset.info.scroll_levels[scroll_id]))
            for scroll_id in sorted(preset.info.scroll_levels.keys())
        )

        # 결과 계산에 쓰이는 스킬 정의값을 순서 고정 튜플로 변환
        skill_ids: set[str] = set()
        skill_id: str
        for skill_id in preset.skills.placed_skills:
            if skill_id:
                skill_ids.add(skill_id)

        scroll_id: str
        for scroll_id in preset.skills.equipped_scrolls:
            if not scroll_id:
                continue

            scroll_def: ScrollDef = (
                app_state.macro.current_server.skill_registry.get_scroll(scroll_id)
            )
            skill_ids.update(scroll_def.skills)

        skill_definition_rows: list[
            tuple[str, tuple[tuple[int, float], ...], float, int]
        ] = []
        for skill_id in sorted(skill_ids):
            skill_def: SkillDef = app_state.macro.current_server.skill_registry.get(
                skill_id
            )
            skill_levels: tuple[tuple[int, float], ...] = tuple(
                (int(level), float(damage))
                for level, damage in sorted(skill_def.levels.items())
            )
            skill_definition_rows.append(
                (
                    skill_id,
                    skill_levels,
                    float(skill_def.cooltime),
                    int(skill_def.target_count),
                )
            )

        skill_definitions: tuple[
            tuple[str, tuple[tuple[int, float], ...], float, int],
            ...,
        ] = tuple(skill_definition_rows)

        # 스킬 사용 설정을 스킬 ID 순서로 고정
        usage_settings: tuple[tuple[str, tuple[bool, bool, int]], ...] = tuple(
            (skill_id, preset.usage_settings[skill_id].to_tuple())
            for skill_id in sorted(preset.usage_settings.keys())
        )

        # 자동 연계 계산에 쓰이는 연계스킬 상태 고정
        link_skills: tuple[tuple[str, str, str | None, tuple[str, ...]], ...] = tuple(
            (
                link_skill.use_type.value,
                link_skill.key_type.value,
                link_skill.key,
                tuple(link_skill.skills),
            )
            for link_skill in preset.link_skills
        )

        # 선택 공식 계산과 표시명에 영향을 주는 전역 공식 상태 고정
        custom_formulas: tuple[tuple[str, str, str], ...] = tuple(
            (
                custom_formula.id,
                custom_formula.name,
                custom_formula.formula,
            )
            for custom_formula in app_state.macro.custom_power_formulas
        )

        return _CalculatorResultsCacheKey(
            server_id=preset.settings.server_id,
            delay_ms=app_state.macro.current_delay,
            calculator_input_data=calculator_input_data,
            equipped_scrolls=tuple(preset.skills.equipped_scrolls),
            placed_skills=tuple(preset.skills.placed_skills),
            skill_definitions=skill_definitions,
            scroll_levels=scroll_levels,
            usage_settings=usage_settings,
            link_skills=link_skills,
            custom_formulas=custom_formulas,
        )

    def _cancel_results_calculation(self) -> None:
        """진행 중인 결과 계산 취소 요청"""

        # 실행 중인 계산이 없으면 취소 동작 무시
        if self._calc_thread is None or not self._calc_thread.isRunning():
            return

        # 사용자 취소 의도 즉시 반영
        self._results_overlay.set_cancelling()
        self._calc_thread.cancel()

    def cancel_results_calculation_for_shutdown(self) -> None:
        """프로그램 종료 중 진행 계산 취소 및 스레드 정리"""

        # 종료 시 진행 중인 계산이 없으면 즉시 반환
        if self._calc_thread is None or not self._calc_thread.isRunning():
            return

        # 종료 요청을 계산 스레드와 하위 프로세스 풀까지 전달
        self._calc_thread.cancel()
        self._calc_thread.wait(3000)

    def _on_results_calculation_progress(self, message: str, value: int) -> None:
        """오버레이 진행 상태 갱신"""

        # 백그라운드 계산 단계 문구와 진행률 반영
        self._results_overlay.update_progress(message, value)

    def _on_results_calculation_finished(
        self,
        output_rows: ResultsPage.OutputRows | None,
        is_cancelled: bool,
    ) -> None:
        """백그라운드 계산 종료 후 페이지 전환 처리"""

        # 오버레이 정리 (스레드 참조 해제는 finished 시그널에서 처리)
        self._results_overlay.hide()

        # 사용자 취소 요청이면 현재 페이지 유지
        if is_cancelled:
            self._pending_results_cache_key = None
            return

        # 계산 실패 시 오류 결과 표시 후 결과 페이지 진입
        if output_rows is None:
            self._pending_results_cache_key = None
            results_page: ResultsPage = self.results_page
            results_page.set_error_state()
            self.update_nav(2)
            self.stacked_layout.setCurrentWidget(results_page)
            self.adjust_main_frame_height()
            QTimer.singleShot(0, self.adjust_main_frame_height)
            return

        # 성공한 계산 결과를 동일 입력 재진입용 캐시에 저장
        self._results_cache_key = self._pending_results_cache_key
        self._results_cache_output_rows = output_rows
        self._pending_results_cache_key = None

        # 계산 성공 결과 반영 후 결과 페이지 진입
        results_page: ResultsPage = self.results_page
        results_page.set_output_rows(output_rows)
        self.update_nav(2)
        self.stacked_layout.setCurrentWidget(results_page)
        self.adjust_main_frame_height()
        QTimer.singleShot(0, self.adjust_main_frame_height)

    def _cleanup_calc_thread(self) -> None:
        """QThread 완전 종료 후 참조 해제"""

        if self._calc_thread is not None:
            self._calc_thread.deleteLater()
            self._calc_thread = None


class InputPage(QFrame):
    def __init__(
        self,
        parent: QFrame,
        popup_manager: PopupManager,
    ) -> None:
        super().__init__(parent)

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


class ScreenCaptureSelectionDialog(QDialog):
    """사용자가 화면 영역을 드래그 선택하는 오버레이"""

    _MIN_SELECTION_SIZE: int = 20

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._drag_start_global: QPoint | None = None
        self._drag_current_global: QPoint | None = None
        self._selected_rect: QRect | None = None

        self.setModal(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setGeometry(self._virtual_geometry())

    def selected_rect(self) -> QRect | None:
        """확정된 전역 화면 좌표 선택 영역 반환"""

        return self._selected_rect

    def showEvent(self, event: QShowEvent) -> None:  # type: ignore
        super().showEvent(event)
        self.activateWindow()
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return

        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.reject()
            return

        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        point = event.globalPosition().toPoint()
        self._drag_start_global = point
        self._drag_current_global = point
        self._selected_rect = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start_global is None:
            super().mouseMoveEvent(event)
            return

        self._drag_current_global = event.globalPosition().toPoint()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() != Qt.MouseButton.LeftButton
            or self._drag_start_global is None
        ):
            super().mouseReleaseEvent(event)
            return

        self._drag_current_global = event.globalPosition().toPoint()
        selection_rect = self._current_selection_rect()
        self._drag_start_global = None
        self._drag_current_global = None

        if selection_rect is None:
            self.update()
            return

        if (
            selection_rect.width() < self._MIN_SELECTION_SIZE
            or selection_rect.height() < self._MIN_SELECTION_SIZE
        ):
            self.update()
            return

        self._selected_rect = selection_rect
        self.accept()

    def paintEvent(self, _event: QPaintEvent) -> None:  # type: ignore
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

        selection_rect = self._current_selection_rect()

        if selection_rect is not None:
            local_rect = QRect(
                self.mapFromGlobal(selection_rect.topLeft()),
                self.mapFromGlobal(selection_rect.bottomRight()),
            ).normalized()
            painter.fillRect(local_rect, QColor(255, 255, 255, 25))
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawRect(local_rect)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(CustomFont(11, bold=True))
        painter.drawText(
            self.rect().adjusted(24, 24, -24, -24),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            "전체 스탯 영역을 드래그하세요. Esc 또는 우클릭으로 취소할 수 있습니다.",
        )

    def _current_selection_rect(self) -> QRect | None:
        if self._drag_start_global is None or self._drag_current_global is None:
            return self._selected_rect
        return QRect(self._drag_start_global, self._drag_current_global).normalized()

    @staticmethod
    def _virtual_geometry() -> QRect:
        geometry = QRect()
        for screen in QGuiApplication.screens():
            screen_geometry = screen.geometry()
            geometry = (
                screen_geometry
                if geometry.isNull()
                else geometry.united(screen_geometry)
            )
        return geometry


class OcrReviewDialog(QDialog):
    """OCR 인식 결과 적용 전 검토 다이얼로그"""

    def __init__(
        self, parent: QWidget, candidates: dict[StatKey, OcrStatCandidate]
    ) -> None:
        super().__init__(parent)

        self._retry_requested: bool = False
        self._value_inputs: dict[StatKey, CustomLineEdit] = {}

        self.setObjectName("customSkillDialog")
        self.setWindowTitle("OCR 결과 확인")
        self.setModal(True)

        root_layout: QVBoxLayout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 16)
        root_layout.setSpacing(12)

        result_card: QFrame = QFrame(self)
        result_card.setObjectName("dialogCard")
        result_layout: QVBoxLayout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(16, 14, 16, 14)
        result_layout.setSpacing(6)

        section_label: QLabel = QLabel("인식 결과", result_card)
        section_label.setObjectName("dialogSectionTitle")
        section_label.setFont(CustomFont(11))
        result_layout.addWidget(section_label)

        grid: QGridLayout = QGridLayout()
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        for row_index, (left_key, right_key) in enumerate(OVERALL_STAT_GRID_ROWS):
            for col, stat_key in enumerate((left_key, right_key)):
                if stat_key is None:
                    continue

                candidate = candidates.get(stat_key)

                cell_widget: QFrame = QFrame(result_card)
                cell_layout: QHBoxLayout = QHBoxLayout(cell_widget)
                cell_layout.setContentsMargins(0, 3, 0, 3)
                cell_layout.setSpacing(8)

                label_widget: QLabel = QLabel(STAT_SPECS[stat_key], cell_widget)
                label_widget.setFont(CustomFont(10))

                # OCR 후보값의 음수 오인식 0 정규화
                candidate_value: float = (
                    0.0 if candidate is None else max(candidate.value, 0.0)
                )
                value_text: str = f"{candidate_value:,g}"
                value_input: CustomLineEdit = CustomLineEdit(
                    cell_widget,
                    text=value_text,
                    point_size=10,
                )
                value_input.setAlignment(Qt.AlignmentFlag.AlignRight)
                value_input.setFixedWidth(100)
                value_input.setPlaceholderText("0")
                value_input.textChanged.connect(
                    lambda _text, current_key=stat_key: self._on_value_changed(
                        current_key
                    )
                )
                self._value_inputs[stat_key] = value_input

                cell_layout.addWidget(label_widget, 1)
                cell_layout.addWidget(value_input)
                grid.addWidget(cell_widget, row_index, col)

        result_layout.addLayout(grid)

        # 검토 중인 스탯값 기준 공식 전투력 미리보기 구성
        power_row: QHBoxLayout = QHBoxLayout()
        power_row.setContentsMargins(0, 10, 0, 0)
        power_row.setSpacing(8)

        power_label: QLabel = QLabel("공식 전투력", result_card)
        power_label.setFont(CustomFont(10, bold=True))

        self._power_value_label = QLabel("0", result_card)
        self._power_value_label.setFont(CustomFont(12, bold=True))
        self._power_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        power_row.addWidget(power_label)
        power_row.addStretch(1)
        power_row.addWidget(self._power_value_label)
        result_layout.addLayout(power_row)

        power_hint_label: QLabel = QLabel(
            "게임에 표시된 공식 전투력과 비교해 인식값이 맞는지 확인하세요.",
            result_card,
        )
        power_hint_label.setFont(CustomFont(9))
        power_hint_label.setWordWrap(True)
        result_layout.addWidget(power_hint_label)

        root_layout.addWidget(result_card)

        btn_row: QHBoxLayout = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        cancel_btn: QPushButton = QPushButton("취소", self)
        cancel_btn.setObjectName("dialogCancelBtn")
        cancel_btn.setFont(CustomFont(11))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        retry_btn: QPushButton = QPushButton("재시도", self)
        retry_btn.setObjectName("dialogCancelBtn")
        retry_btn.setFont(CustomFont(11))
        retry_btn.setFixedHeight(36)
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.clicked.connect(self._request_retry)

        confirm_btn: QPushButton = QPushButton("적용", self)
        confirm_btn.setObjectName("dialogConfirmBtn")
        confirm_btn.setFont(CustomFont(11))
        confirm_btn.setFixedHeight(36)
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.clicked.connect(self.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(retry_btn)
        btn_row.addWidget(confirm_btn)
        root_layout.addLayout(btn_row)

        self._update_power_preview()
        self.adjustSize()
        self.setFixedSize(self.size())

    def confirmed_stats(self) -> dict[StatKey, float]:
        """확정된 OCR 결과를 값 맵으로 반환"""

        confirmed: dict[StatKey, float] = {}
        for stat_key in OVERALL_STAT_ORDER:
            confirmed[stat_key] = self._normalize_ocr_value_text(
                self._value_inputs[stat_key].text()
            )

        return confirmed

    def retry_requested(self) -> bool:
        """OCR 재시도 요청 여부 반환"""

        return self._retry_requested

    def _request_retry(self) -> None:
        """현재 다이얼로그를 닫고 OCR 을 다시 수행하도록 요청"""

        self._retry_requested = True
        self.reject()

    def _on_value_changed(self, stat_key: StatKey) -> None:
        """수동 수정 시 OCR 입력값과 전투력 미리보기 갱신"""

        # 수정된 OCR 입력칸의 적용 가능한 숫자 정규화
        self._normalize_value_input(stat_key)
        self._update_power_preview()

    def _update_power_preview(self) -> None:
        """검토 중인 스탯값 기준 공식 전투력 표시 갱신"""

        # 계산기와 같은 내부 원시 스탯 환산 경로로 공식 전투력 계산
        preview_base_stats: BaseStats = BaseStats.from_stat_map(self.confirmed_stats())
        internal_base_stats: BaseStats = build_internal_base_stats(preview_base_stats)

        official_power: float = evaluate_official_power(internal_base_stats.resolve())

        self._power_value_label.setText(f"{official_power:,.0f}")

    def _normalize_value_input(self, stat_key: StatKey) -> None:
        """OCR 스탯 입력칸의 적용값 기준 텍스트 정규화"""

        # 입력 텍스트의 0 보정 필요 여부 확인
        value_input = self._value_inputs[stat_key]
        sanitized_text: str = value_input.text().strip().replace(",", "")
        if not sanitized_text:
            value_input.setText("0")

            return

        try:
            parsed_value: float = float(sanitized_text)
        except ValueError:
            value_input.setText("0")

            return

        # OCR 스탯값의 게임 표시 불가능 음수 입력 보정
        if not parsed_value >= 0.0:
            value_input.setText("0")

    @staticmethod
    def _normalize_ocr_value_text(text: str) -> float:
        """OCR 입력 텍스트의 적용값 정규화"""

        sanitized_text: str = text.strip().replace(",", "")
        if not sanitized_text:
            return 0.0

        try:
            parsed_value: float = float(sanitized_text)
        except ValueError:
            return 0.0

        return max(parsed_value, 0.0)


class _CalculationOverlay(QFrame):
    def __init__(
        self,
        parent: QWidget,
        cancel_handler: Callable[[], None],
    ) -> None:
        super().__init__(parent)

        # 부모 전체를 덮는 반투명 오버레이 기본 설정
        self.setObjectName("calcOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setGeometry(parent.rect())
        self.hide()
        parent.installEventFilter(self)

        # 오버레이 중앙 카드 구성
        container: QFrame = QFrame(self)
        container.setObjectName("calcOverlayCard")
        container.setFixedWidth(360)

        title_label: QLabel = QLabel("계산 중", container)
        title_label.setObjectName("calcOverlayTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(CustomFont(15, bold=True))

        self._message_label: QLabel = QLabel(container)
        self._message_label.setObjectName("calcOverlayMessage")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setFont(CustomFont(12, bold=True))

        self._detail_label: QLabel = QLabel(container)
        self._detail_label.setObjectName("calcOverlayDetail")
        self._detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_label.setFont(CustomFont(11))

        self._progress_label: QLabel = QLabel(container)
        self._progress_label.setObjectName("calcOverlayProgress")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setFont(CustomFont(11))

        self._progress_bar: QProgressBar = QProgressBar(container)
        self._progress_bar.setObjectName("calcProgressBar")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(12)

        self._cancel_button: QPushButton = QPushButton("취소", container)
        self._cancel_button.setObjectName("calcCancelBtn")
        self._cancel_button.setFont(CustomFont(11, bold=True))
        self._cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_button.setFixedHeight(40)
        self._cancel_button.clicked.connect(cancel_handler)

        # 중앙 카드 내부 정렬
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

        # 오버레이 전체 중앙 배치
        overlay_layout: QVBoxLayout = QVBoxLayout(self)
        overlay_layout.setContentsMargins(24, 24, 24, 24)
        overlay_layout.addStretch(1)
        overlay_layout.addWidget(container, alignment=Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addStretch(1)
        self.setLayout(overlay_layout)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """부모 리사이즈 시 오버레이 영역 동기화"""

        # 부모 크기 변경 시 오버레이 전체 영역 재배치
        if watched is self.parent() and event.type() == QEvent.Type.Resize:
            parent_widget: QWidget = self.parentWidget()
            self.setGeometry(parent_widget.rect())

        return super().eventFilter(watched, event)

    def show_overlay(self, message: str, detail: str, value: int) -> None:
        """초기 진행 상태와 함께 오버레이 표시"""

        # 취소 버튼 활성화와 초기 진행 상태 반영
        self._cancel_button.setEnabled(True)
        self._message_label.setText(message)
        self.update_progress(detail, value)

        # 최상단 오버레이 표시
        self.show()
        self.raise_()

    def update_progress(self, detail: str, value: int) -> None:
        """진행 문구와 진행률 갱신"""

        # 진행 문구와 백분율 레이블 동기화
        clamped_value: int = max(0, min(100, value))
        self._detail_label.setText(detail)
        self._progress_label.setText(f"{clamped_value}%")
        self._progress_bar.setValue(clamped_value)

    def set_cancelling(self) -> None:
        """취소 요청 직후 오버레이 상태 갱신"""

        # 중복 취소 방지와 취소 진행 상태 표기
        self._cancel_button.setEnabled(False)
        self._detail_label.setText("취소 요청 처리 중...")


class _CalculationInputConfirmOverlay(QFrame):
    _SUMMARY_VALUE_WIDTH: int = 250

    def __init__(
        self,
        parent: QWidget,
        confirm_handler: Callable[[], None],
        title: str = "계산 전 입력 확인",
        message: str = "입력한 내용이 맞으면 계산을 시작하세요.",
        confirm_text: str = "계산 시작",
        show_summary: bool = True,
    ) -> None:
        super().__init__(parent)

        # 부모 전체를 덮는 입력 확인 오버레이 기본 설정
        self._confirm_handler: Callable[[], None] = confirm_handler
        self._show_summary: bool = show_summary
        self.setObjectName("calcOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setGeometry(parent.rect())
        self.hide()
        parent.installEventFilter(self)

        # 입력 확인 카드 구성
        card_width: int = 400
        card_horizontal_margin: int = 24
        content_width: int = card_width - card_horizontal_margin * 2
        container: QFrame = QFrame(self)
        container.setObjectName("calcOverlayCard")
        container.setFixedWidth(card_width)

        title_label: QLabel = QLabel(title, container)
        title_label.setObjectName("calcOverlayTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(CustomFont(14, bold=True))

        message_label: QLabel = QLabel(message, container)
        message_label.setObjectName("calcConfirmMessage")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setFont(CustomFont(12))
        message_label.setFixedWidth(content_width)
        # 카드 내부 폭 기준 메시지 줄바꿈 높이 확보
        message_label.setMinimumHeight(message_label.heightForWidth(content_width))

        # 주요 계산 입력 요약 그리드 구성 (요약 표시 시에만 구성)
        self._summary_grid: QGridLayout = QGridLayout()
        self._summary_grid.setContentsMargins(0, 8, 0, 8)
        self._summary_grid.setHorizontalSpacing(12)
        self._summary_grid.setVerticalSpacing(12)
        self._value_labels: dict[str, QLabel] = {}
        if self._show_summary:
            self._add_summary_row(0, "레벨", "level", container)
            self._add_summary_row(1, "경지", "realm", container)
            self._add_summary_row(2, "스탯 분배", "distribution", container)
            self._add_summary_row(3, "단전", "danjeon", container)
            self._add_summary_row(4, "후보", "candidates", container)

        # 확인과 취소 버튼 구성
        cancel_button: QPushButton = QPushButton("취소", container)
        cancel_button.setObjectName("calcCancelBtn")
        cancel_button.setFont(CustomFont(11, bold=True))
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.setFixedHeight(40)
        cancel_button.clicked.connect(self.hide)

        confirm_button: QPushButton = QPushButton(confirm_text, container)
        confirm_button.setObjectName("calcConfirmBtn")
        confirm_button.setFont(CustomFont(11, bold=True))
        confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_button.setFixedHeight(40)
        confirm_button.clicked.connect(self._accept)

        button_layout: QHBoxLayout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)

        # 카드 내부 레이아웃 구성
        container_layout: QVBoxLayout = QVBoxLayout(container)
        container_layout.setContentsMargins(
            card_horizontal_margin, 22, card_horizontal_margin, 22
        )
        container_layout.setSpacing(10)
        container_layout.addWidget(title_label)
        container_layout.addWidget(message_label)
        if self._show_summary:
            container_layout.addLayout(self._summary_grid)
        container_layout.addSpacing(4)
        container_layout.addLayout(button_layout)
        # 카드가 내용 높이만큼 늘어나도록 최소 크기 제약 적용
        container_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        container.setLayout(container_layout)

        # 오버레이 전체 중앙 배치
        overlay_layout: QVBoxLayout = QVBoxLayout(self)
        overlay_layout.setContentsMargins(24, 24, 24, 24)
        overlay_layout.addStretch(1)
        overlay_layout.addWidget(container, alignment=Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addStretch(1)
        self.setLayout(overlay_layout)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """부모 리사이즈 시 오버레이 영역 동기화"""

        # 부모 크기 변경 시 오버레이 전체 영역 재배치
        if watched is self.parent() and event.type() == QEvent.Type.Resize:
            parent_widget: QWidget = self.parentWidget()
            self.setGeometry(parent_widget.rect())

        return super().eventFilter(watched, event)

    def show_confirmation(
        self,
        calculator_input: "CalculatorPresetInput | CalculatorInputFill | None" = None,
    ) -> None:
        """현재 계산 입력 요약 표시"""

        # 요약을 사용하는 오버레이만 기준 입력 문구 반영
        if self._show_summary and calculator_input is not None:
            realm_label: str = REALM_TIER_SPECS[calculator_input.realm_tier].label
            self._value_labels["level"].setText(str(calculator_input.level))
            self._value_labels["realm"].setText(realm_label)

            # 최적화 입력 요약 문구 반영
            self._value_labels["distribution"].setText(
                self._format_distribution_state(calculator_input.distribution)
            )
            self._value_labels["danjeon"].setText(
                self._format_danjeon_state(calculator_input.danjeon)
            )
            self._value_labels["candidates"].setText(
                self._format_candidate_groups(calculator_input.candidate_groups)
            )

            # 줄바꿈 값 라벨은 텍스트 적용 후 최소 높이를 잡아야 카드가 잘리지 않는다
            for value_label in self._value_labels.values():
                value_label.setMinimumHeight(
                    value_label.heightForWidth(self._SUMMARY_VALUE_WIDTH)
                )

        # 최상단 확인 오버레이 표시
        self.show()
        self.raise_()

    def _accept(self) -> None:
        """확인 후 결과 계산 시작"""

        # 확인 오버레이 정리 후 기존 계산 흐름 실행
        self.hide()
        self._confirm_handler()

    def _add_summary_row(
        self,
        row_index: int,
        label_text: str,
        value_key: str,
        parent: QWidget,
    ) -> None:
        """입력 확인 요약 행 추가"""

        # 요약 항목 이름 라벨 구성
        key_label: QLabel = QLabel(label_text, parent)
        key_label.setObjectName("calcConfirmKey")
        key_label.setFont(CustomFont(11, bold=True))
        key_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        key_label.setFixedWidth(82)

        # 요약 항목 값 라벨 구성
        value_label: QLabel = QLabel(parent)
        value_label.setObjectName("calcConfirmValue")
        value_label.setFont(CustomFont(11))
        value_label.setWordWrap(True)
        value_label.setFixedWidth(self._SUMMARY_VALUE_WIDTH)
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._value_labels[value_key] = value_label

        self._summary_grid.addWidget(key_label, row_index, 0)
        self._summary_grid.addWidget(value_label, row_index, 1)

    @staticmethod
    def _format_distribution_state(distribution: DistributionState) -> str:
        """스탯 분배 확인 문구 구성"""

        # 스탯 분배 수치와 옵션 상태 결합
        option_text: str = _CalculationInputConfirmOverlay._format_option_state(
            distribution.is_locked,
            distribution.use_reset,
        )
        summary: str = (
            f"힘 {distribution.strength} / "
            f"민첩 {distribution.dexterity}\n"
            f"생명력 {distribution.vitality} / "
            f"행운 {distribution.luck}\n"
            f"{option_text}"
        )
        return summary

    @staticmethod
    def _format_danjeon_state(danjeon: DanjeonState) -> str:
        """단전 확인 문구 구성"""

        # 단전 수치와 옵션 상태 결합
        option_text: str = _CalculationInputConfirmOverlay._format_option_state(
            danjeon.is_locked,
            danjeon.use_reset,
        )
        summary: str = (
            f"상단전 {danjeon.upper} / "
            f"중단전 {danjeon.middle} / "
            f"하단전 {danjeon.lower}\n"
            f"{option_text}"
        )
        return summary

    @staticmethod
    def _format_option_state(is_locked: bool, use_reset: bool) -> str:
        """잠금과 초기화 옵션 확인 문구 구성"""

        # 체크박스 상태를 사용자가 확인하기 쉬운 문구로 변환
        lock_text: str = "잠금 켜짐" if is_locked else "잠금 꺼짐"
        reset_text: str = "초기화 켜짐" if use_reset else "초기화 꺼짐"
        return f"{lock_text} / {reset_text}"

    @staticmethod
    def _format_candidate_groups(
        candidate_groups: list[OptimizationCandidateGroup],
    ) -> str:
        """후보 그룹 확인 문구 구성"""

        # 후보 그룹 부재 상태 문구 구성
        if not candidate_groups:
            return "후보 그룹 없음"

        # 그룹별 선택 개수와 후보 수 요약
        summary_lines: list[str] = []
        for candidate_group in candidate_groups:
            summary_lines.append(
                f"{candidate_group.name}: 선택 {candidate_group.selection_count}개 / "
                f"후보 {len(candidate_group.candidates)}개"
            )

        return "\n".join(summary_lines)


class GraphPage(QFrame):
    def __init__(
        self,
        parent: QFrame,
    ) -> None:
        super().__init__(parent)

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
        analysis: list[GraphAnalysis] = list(graph_report.analysis)
        deterministic_attacks: list[GraphDamageEvent] = list(
            graph_report.deterministic_boss_attacks
        )
        results: list[list[GraphDamageEvent]] = [
            list(result_row) for result_row in graph_report.random_boss_attacks
        ]

        # 분석/그래프 위젯 재생성
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

            self.setObjectName("graphCard")

            # 그래프 탭 최초 구성 시 pyqtgraph 기반 캔버스 로드
            from app.scripts.ui.sim_ui.graph import DpmDistributionCanvas

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

            self.setObjectName("graphCard")

            # 그래프 탭 최초 구성 시 pyqtgraph 기반 캔버스 로드
            from app.scripts.ui.sim_ui.graph import SkillDpsRatioCanvas

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

            self.setObjectName("graphCard")

            # 초 단위 피해량 그래프 구성
            from app.scripts.ui.sim_ui.graph import DamageGraphMode, DMGCanvas

            self.graph = DMGCanvas(
                self,
                results,
                "시간 경과에 따른 피해량",
                DamageGraphMode.PER_SECOND,
            )
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

            self.setObjectName("graphCard")

            # 누적 피해량 그래프 구성
            from app.scripts.ui.sim_ui.graph import DamageGraphMode, DMGCanvas

            self.graph = DMGCanvas(
                self,
                results,
                "누적 피해량",
                DamageGraphMode.CUMULATIVE,
            )
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

            self.setObjectName("graphCard")

            # 그래프 탭 최초 구성 시 pyqtgraph 기반 캔버스 로드
            from app.scripts.ui.sim_ui.graph import SkillContributionCanvas

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
        selected_formula_id: str,
        custom_formulas: tuple[CustomPowerFormula, ...],
    ) -> None:
        super().__init__()
        self._server_spec = server_spec
        self._preset = preset
        self._delay_ms = delay_ms
        self._base_stats = base_stats
        self._calculator_input = calculator_input
        self._level = level
        self._selected_formula_id = selected_formula_id
        self._custom_formulas: tuple[CustomPowerFormula, ...] = custom_formulas
        self._is_cancel_requested: bool = False

    def cancel(self) -> None:
        """계산 취소 요청 기록"""

        # 스레드 인터럽트와 내부 취소 플래그 동시 반영
        self._is_cancel_requested = True
        self.requestInterruption()

    def _emit_progress(self, message: str, value: int) -> None:
        """진행 상태 시그널 방출"""

        # 취소 여부 확인 이후 진행 상태 전파
        self._ensure_not_cancelled()
        self.progress_signal.emit(message, value)

    def _ensure_not_cancelled(self) -> None:
        """취소 요청 시 내부 예외 발생"""

        # 스레드 인터럽트 또는 명시적 취소 요청 감지
        if self._is_cancel_requested or self.isInterruptionRequested():
            raise _CalculationCancelledError()

    def run(self) -> None:
        try:
            # 계산 컨텍스트 선행 구성
            self._emit_progress("컨텍스트 생성 중...", 0)
            context: EvaluationContext = build_calculator_context(
                server_spec=self._server_spec,
                preset=self._preset,
                skills_info=self._preset.usage_settings,
                delay_ms=self._delay_ms,
                base_stats=self._base_stats,
                target_formula_id=self._selected_formula_id,
                custom_formulas=self._custom_formulas,
            )

            # 결과 행 전체 계산
            self._emit_progress("결과 정리 준비 중...", 0)
            output_rows: ResultsPage.OutputRows = ResultsPage._build_output_rows(
                server_spec=self._server_spec,
                preset=self._preset,
                delay_ms=self._delay_ms,
                base_stats=self._base_stats,
                level=self._level,
                selected_formula_id=self._selected_formula_id,
                current_realm=self._calculator_input.realm_tier,
                calculator_input=self._calculator_input,
                context=context,
                progress_callback=self._emit_progress,
                cancel_checker=self._ensure_not_cancelled,
            )

            # 완료 직전 취소 여부 재확인
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

        current_power: tuple[str, str]
        stat_efficiency: list[tuple[str, str]]
        level_up: list[tuple[str, str]]
        realm_up: list[tuple[str, str]]
        scroll_efficiency: list[tuple[str, str]]
        custom_delta: tuple[str, str] | None
        target_distribution_summary: tuple[str, str] | None
        target_delta: tuple[str, str] | None
        target_danjeon_summary: tuple[str, str] | None
        target_danjeon_delta: tuple[str, str] | None
        optimization_result: list[tuple[str, str]]
        candidate_selection_result: list[tuple[str, str]] | None
        custom_base_stats: BaseStats | None
        target_base_stats: BaseStats | None
        target_danjeon_base_stats: BaseStats | None
        optimized_base_stats: BaseStats | None
        candidate_selection_base_stats: BaseStats | None

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

        # 결과 카드 공통 로딩 상태 반영
        self.view.set_loading_outputs()

    def set_error_state(self) -> None:
        """결과 페이지 오류 출력 반영"""

        # 결과 카드 공통 오류 상태 반영
        self.view.set_error_outputs()

    def set_output_rows(self, output_rows: "ResultsPage.OutputRows") -> None:
        """계산 완료 결과 반영"""

        # 계산 완료 결과 행을 결과 카드에 반영
        self.view.set_output_rows(output_rows)

    @staticmethod
    def _format_delta(value: float) -> str:
        """전투력 변화량 표시 문자열 생성"""

        return f"{value:+,.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _format_current_power(value: float) -> str:
        """현재 전투력 표시 문자열 생성"""

        return f"{value:,.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _result_sort_key(row: tuple[str, str]) -> float:
        """결과 행의 숫자 문자열 정렬 키 반환"""

        # 결과 문자열을 정렬용 숫자로 직접 변환
        return float(row[1].replace(",", ""))

    @classmethod
    def _build_output_rows(
        cls,
        server_spec: "ServerSpec",
        preset: "MacroPreset",
        delay_ms: int,
        base_stats: BaseStats,
        level: int,
        selected_formula_id: str,
        current_realm: "RealmTier",
        calculator_input: CalculatorPresetInput,
        context: "EvaluationContext",
        cancel_checker: Callable[[], None],
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> "ResultsPage.OutputRows":
        """공용 계산기 결과 행 구성"""

        # 현재 전투력 구성 직전 진행 단계 반영
        if progress_callback is not None:
            progress_callback("현재 전투력 정리 중...", 0)

        cancel_checker()

        # 현재 전투력 출력 행 구성
        formula_labels: dict[str, str] = _build_formula_label_map(
            app_state.macro.custom_power_formulas
        )
        current_power_row: tuple[str, str] = (
            formula_labels[selected_formula_id],
            cls._format_current_power(context.baseline_power),
        )

        # 스탯 효율 계산 시작 단계 반영
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
            cancel_checker()

            metric_delta: float = evaluate_single_stat_delta(
                context=context,
                stat_key=stat_key,
                amount=1.0,
                target_formula_id=selected_formula_id,
            )
            label: str = f"{stat_label} +1"

            stat_rows.append((label, cls._format_delta(metric_delta)))

            if progress_callback is not None:
                stat_progress: int = 0
                progress_callback("스탯 효율 계산 중...", stat_progress)

        stat_rows.sort(
            key=cls._result_sort_key,
            reverse=True,
        )

        # 레벨업 효율 계산 단계 반영
        if progress_callback is not None:
            progress_callback("레벨 효율 계산 중...", 0)

        cancel_checker()

        # 레벨 1업 효율 출력 행 구성
        level_up: LevelUpEvaluation = evaluate_level_up_delta(
            context=context,
            target_formula_id=selected_formula_id,
        )
        level_distribution_text: str = (
            f"힘 {level_up.stat_distribution[StatKey.STR]}, "
            f"민첩 {level_up.stat_distribution[StatKey.DEXTERITY]}, "
            f"생명력 {level_up.stat_distribution[StatKey.VITALITY]}, "
            f"행운 {level_up.stat_distribution[StatKey.LUCK]}"
        )
        level_up_rows: list[tuple[str, str]] = [
            (
                "레벨 1업",
                cls._format_delta(level_up.delta),
            ),
            ("최적 분배", level_distribution_text),
        ]

        # 경지 효율 계산 단계 반영
        if progress_callback is not None:
            progress_callback("경지 효율 계산 중...", 0)

        cancel_checker()

        # 다음 경지 효율 출력 행 구성
        realm_result: RealmAdvanceEvaluation | None = evaluate_next_realm_delta(
            context=context,
            current_realm=current_realm,
            level=level,
            target_formula_id=selected_formula_id,
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
                    cls._format_delta(realm_result.delta),
                ),
                ("최적 분배", danjeon_text),
            ]

        # 무공비급 효율 계산 단계 반영
        if progress_callback is not None:
            progress_callback("무공비급 효율 계산 중...", 0)

        cancel_checker()

        # 무공비급 +1 효율 출력 행 구성
        scroll_rows: list[tuple[str, str]] = []
        scroll_results: list[ScrollUpgradeEvaluation] = evaluate_scroll_upgrade_deltas(
            server_spec=server_spec,
            preset=preset,
            skills_info=preset.usage_settings,
            delay_ms=delay_ms,
            baseline_context=context,
            target_formula_id=selected_formula_id,
        )
        scroll_index: int
        scroll_result: ScrollUpgradeEvaluation
        for scroll_index, scroll_result in enumerate(scroll_results, start=1):
            cancel_checker()

            scroll_rows.append(
                (
                    f"{scroll_result.scroll_name} Lv.{scroll_result.next_level}",
                    cls._format_delta(scroll_result.delta),
                )
            )

            if progress_callback is not None:
                scroll_progress: int = 0
                progress_callback("무공비급 효율 계산 중...", scroll_progress)

        scroll_rows.sort(
            key=cls._result_sort_key,
            reverse=True,
        )

        # 사용자 지정 변화량 계산 단계 반영
        if progress_callback is not None:
            progress_callback("사용자 지정 변화량 계산 중...", 0)

        cancel_checker()

        # 사용자 지정 변화량 맵 1회 구성 및 빈 입력 분기
        custom_changes: dict[StatKey, float] = cls._build_custom_stat_change_map(
            calculator_input
        )
        custom_delta_row: tuple[str, str] | None = None
        custom_base_stats: BaseStats | None = None
        if custom_changes:
            custom_delta_row = cls._build_custom_delta_row(
                context=context,
                selected_formula_id=selected_formula_id,
                custom_changes=custom_changes,
            )
            custom_base_stats = base_stats.with_changes(custom_changes)

        target_changes: dict[StatKey, float] = cls._build_target_distribution_delta(
            calculator_input
        )
        target_distribution_summary: tuple[str, str] | None = None
        target_delta_row: tuple[str, str] | None = None
        target_base_stats: BaseStats | None = None

        # 목표 분배 결과 표시 행 구성
        if target_changes:
            # 목표 분배 수치 요약 행 구성
            target_distribution_summary = cls._build_target_distribution_summary_row(
                calculator_input
            )

            # 목표 분배 기준 전투력 변화량 행 구성
            target_delta_row = cls._build_target_distribution_row(
                context=context,
                selected_formula_id=selected_formula_id,
                target_changes=target_changes,
            )

            # 목표 분배 적용 후 전체 스탯 구성
            target_base_stats = base_stats.with_changes(target_changes)

        target_danjeon_changes: dict[StatKey, float] = cls._build_target_danjeon_delta(
            calculator_input
        )
        target_danjeon_summary: tuple[str, str] | None = None
        target_danjeon_delta_row: tuple[str, str] | None = None
        target_danjeon_base_stats: BaseStats | None = None

        # 목표 단전 결과 표시 행 구성
        if target_danjeon_changes:
            # 목표 단전 수치 요약 행 구성
            target_danjeon_summary = cls._build_target_danjeon_summary_row(
                calculator_input
            )

            # 목표 단전 기준 전투력 변화량 행 구성
            formula_labels: dict[str, str] = _build_formula_label_map(
                app_state.macro.custom_power_formulas
            )
            target_danjeon_delta: float = evaluate_arbitrary_stat_delta(
                context=context,
                stat_changes=target_danjeon_changes,
                target_formula_id=selected_formula_id,
            )
            target_danjeon_delta_row = (
                formula_labels[selected_formula_id],
                cls._format_delta(target_danjeon_delta),
            )

            # 목표 단전 적용 후 전체 스탯 구성
            target_danjeon_base_stats = base_stats.with_changes(target_danjeon_changes)

        # 최적화 결과 계산 단계 반영
        if progress_callback is not None:
            progress_callback("최적화 결과 계산 중...", 0)

        cancel_checker()

        # 최적화 결과 행 구성
        optimization_result: OptimizationResult | OptimizationFailure = (
            optimize_current_selection(
                server_spec=server_spec,
                preset=preset,
                skills_info=preset.usage_settings,
                delay_ms=delay_ms,
                context=context,
                base_stats=base_stats,
                calculator_input=calculator_input,
                target_formula_id=selected_formula_id,
                progress_callback=progress_callback,
                cancel_checker=cancel_checker,
            )
        )
        optimized_base_stats: BaseStats | None = None
        candidate_selection_rows: list[tuple[str, str]] | None = None
        candidate_selection_base_stats: BaseStats | None = None
        if isinstance(optimization_result, OptimizationFailure):
            optimization_rows: list[tuple[str, str]] = [
                ("상태", optimization_result.message)
            ]
        else:
            optimized_base_stats = optimization_result.base_stats
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
                    cls._format_delta(optimization_result.delta),
                ),
                ("최적 스탯 분배", distribution_text),
                ("최적 단전", danjeon_text),
            ]

        # 현재 입력 기준 후보 그룹 선택 결과 별도 계산
        candidate_selection_result: (
            CandidateGroupSelectionResult | OptimizationFailure | None
        ) = select_candidate_groups(
            server_spec=server_spec,
            preset=preset,
            skills_info=preset.usage_settings,
            delay_ms=delay_ms,
            context=context,
            base_stats=base_stats,
            calculator_input=calculator_input,
            target_formula_id=selected_formula_id,
            progress_callback=progress_callback,
            cancel_checker=cancel_checker,
        )
        if isinstance(candidate_selection_result, OptimizationFailure):
            candidate_selection_rows = [("상태", candidate_selection_result.message)]
        elif candidate_selection_result is not None:
            candidate_selection_base_stats = candidate_selection_result.base_stats
            candidate_selection_rows = [
                (
                    "선택 전투력 증가",
                    cls._format_delta(candidate_selection_result.delta),
                )
            ]
            for group_selection in candidate_selection_result.group_selections:
                selected_text: str = ", ".join(group_selection.selected_candidate_names)
                if not selected_text:
                    selected_text = "선택된 후보 없음"

                candidate_selection_rows.append(
                    (f"선택 후보 - {group_selection.group_name}", selected_text)
                )

        # 결과 반환 직전 완료 단계 반영
        if progress_callback is not None:
            progress_callback("결과 화면 준비 중...", 100)

        cancel_checker()

        return cls.OutputRows(
            current_power=current_power_row,
            stat_efficiency=stat_rows,
            level_up=level_up_rows,
            realm_up=realm_rows,
            scroll_efficiency=scroll_rows,
            custom_delta=custom_delta_row,
            target_distribution_summary=target_distribution_summary,
            target_delta=target_delta_row,
            target_danjeon_summary=target_danjeon_summary,
            target_danjeon_delta=target_danjeon_delta_row,
            optimization_result=optimization_rows,
            candidate_selection_result=candidate_selection_rows,
            custom_base_stats=custom_base_stats,
            target_base_stats=target_base_stats,
            target_danjeon_base_stats=target_danjeon_base_stats,
            optimized_base_stats=optimized_base_stats,
            candidate_selection_base_stats=candidate_selection_base_stats,
        )

    @staticmethod
    def _build_custom_stat_change_map(
        calculator_input: CalculatorPresetInput,
    ) -> dict[StatKey, float]:
        """저장된 사용자 지정 변화량 맵 복원"""

        # 0이 아닌 사용자 지정 변화량만 enum 키 기준으로 재구성
        custom_changes: dict[StatKey, float] = {}
        stat_key: StatKey
        for stat_key in STAT_SPECS.keys():
            change_value: float = calculator_input.custom_stat_changes[stat_key.value]
            if change_value == 0.0:
                continue

            custom_changes[stat_key] = change_value

        return custom_changes

    @classmethod
    def _build_custom_delta_row(
        cls,
        context: "EvaluationContext",
        selected_formula_id: str,
        custom_changes: dict[StatKey, float],
    ) -> tuple[str, str]:
        """사용자 지정 변화량 결과 행 공용 구성"""

        # 사용자 지정 변화량 기준 선택 공식 전투력 변화량 계산
        formula_labels: dict[str, str] = _build_formula_label_map(
            app_state.macro.custom_power_formulas
        )
        custom_delta: float = evaluate_arbitrary_stat_delta(
            context=context,
            stat_changes=custom_changes,
            target_formula_id=selected_formula_id,
        )
        return (
            formula_labels[selected_formula_id],
            cls._format_delta(custom_delta),
        )

    @classmethod
    def _build_target_distribution_delta(
        cls,
        calculator_input: "CalculatorPresetInput",
    ) -> dict[StatKey, float]:
        """현재 분배 대비 목표 분배 차이 계산"""

        current: DistributionState = calculator_input.distribution
        target: "TargetDistributionState" = calculator_input.target_distribution
        delta: dict[StatKey, float] = {}
        diff_str: int = target.strength - current.strength
        diff_dex: int = target.dexterity - current.dexterity
        diff_vit: int = target.vitality - current.vitality
        diff_luck: int = target.luck - current.luck
        if diff_str != 0:
            delta[StatKey.STR] = float(diff_str)
        if diff_dex != 0:
            delta[StatKey.DEXTERITY] = float(diff_dex)
        if diff_vit != 0:
            delta[StatKey.VITALITY] = float(diff_vit)
        if diff_luck != 0:
            delta[StatKey.LUCK] = float(diff_luck)
        return delta

    @classmethod
    def _build_target_distribution_row(
        cls,
        context: "EvaluationContext",
        selected_formula_id: str,
        target_changes: dict[StatKey, float],
    ) -> tuple[str, str]:
        """목표 분배 결과를 선택된 전투력 공식 기준 단일 행으로 구성"""

        formula_labels: dict[str, str] = _build_formula_label_map(
            app_state.macro.custom_power_formulas
        )
        target_delta: float = evaluate_arbitrary_stat_delta(
            context=context,
            stat_changes=target_changes,
            target_formula_id=selected_formula_id,
        )
        return (
            formula_labels[selected_formula_id],
            cls._format_delta(target_delta),
        )

    @staticmethod
    def _build_target_distribution_summary_row(
        calculator_input: "CalculatorPresetInput",
    ) -> tuple[str, str]:
        """목표 분배 수치 요약 행 구성"""

        # 목표 분배 상태 참조
        target: "TargetDistributionState" = calculator_input.target_distribution

        # 목표 분배 표시 문자열 구성
        summary: str = (
            f"힘 {target.strength} / "
            f"민첩 {target.dexterity} / "
            f"생명력 {target.vitality} / "
            f"행운 {target.luck}"
        )
        return ("목표 분배", summary)

    @staticmethod
    def _build_target_danjeon_delta(
        calculator_input: "CalculatorPresetInput",
    ) -> dict[StatKey, float]:
        """현재 단전 대비 목표 단전 차이 계산"""

        current: DanjeonState = calculator_input.danjeon
        target: "TargetDanjeonState" = calculator_input.target_danjeon
        delta: dict[StatKey, float] = {}
        diff_upper: int = target.upper - current.upper
        diff_middle: int = target.middle - current.middle
        diff_lower: int = target.lower - current.lower
        if diff_upper != 0:
            delta[StatKey.HP_PERCENT] = float(diff_upper * 3)
            delta[StatKey.RESIST_PERCENT] = float(diff_upper)
        if diff_middle != 0:
            delta[StatKey.ATTACK_PERCENT] = float(diff_middle)
        if diff_lower != 0:
            delta[StatKey.DROP_RATE_PERCENT] = float(diff_lower * 1.5)
            delta[StatKey.EXP_PERCENT] = float(diff_lower * 0.5)
        return delta

    @staticmethod
    def _build_target_danjeon_summary_row(
        calculator_input: "CalculatorPresetInput",
    ) -> tuple[str, str]:
        """목표 단전 수치 요약 행 구성"""

        # 목표 단전 상태 참조
        target: "TargetDanjeonState" = calculator_input.target_danjeon

        # 목표 단전 표시 문자열 구성
        summary: str = (
            f"상단전 {target.upper} / "
            f"중단전 {target.middle} / "
            f"하단전 {target.lower}"
        )
        return ("목표 단전", summary)

    class Efficiency(QFrame):
        def __init__(
            self,
            parent: QFrame,
            popup_manager: PopupManager,
        ) -> None:
            super().__init__(parent)
            self.setObjectName("simEfficiency")

            # 저장 상태 로드 중 이벤트 억제 플래그 구성
            self._is_loading_state: bool = False
            self._is_persist_enabled: bool = True
            self.last_input_error_message: str | None = None
            self.popup_manager: PopupManager = popup_manager

            # 마지막으로 전체 로드한 계산기 입력 객체와 그때의 장착 무공비급 목록
            # 재진입 시 입력 객체 교체(프리셋 변경/가이드) 여부와
            # 장착 목록 변경 여부 판별에 사용
            self._loaded_calculator_input: "CalculatorPresetInput | None" = None
            self._loaded_equipped_scrolls: tuple[str, ...] = ()

            # 전투력 선택지와 경지 선택지 순서 구성
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            formula_labels: dict[str, str] = _build_formula_label_map(
                app_state.macro.custom_power_formulas
            )
            self.metric_options: list[str] = _build_formula_options(
                app_state.macro.custom_power_formulas
            )
            self.realm_options: list[RealmTier] = list(REALM_TIER_SPECS.keys())

            # OCR 실행 중 중복 클릭 차단 플래그
            self._is_ocr_running: bool = False

            # 기준 입력 위젯 구성 — KVComboInput 으로 KVInput(레벨)과 레이아웃 통일
            self.metric_input = KVComboInput(
                self,
                "기준 전투력",
                [formula_labels[formula_id] for formula_id in self.metric_options],
                self.on_base_input_changed,
            )
            self.metric_combobox = (
                self.metric_input.combobox
            )  # load_from_preset_state 참조용

            self.metric_manage_button: StyledButton = StyledButton(
                self,
                "공식 관리",
                point_size=10,
            )
            self.metric_manage_button.setFixedHeight(32)
            self.metric_manage_button.clicked.connect(self._open_formula_manager)

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

            # 무공비급 레벨 입력 UI 구성
            self.skills = SkillInputs(
                self,
                SkillInputs.build_entries(),
                self.on_base_input_changed,
                self.popup_manager,
            )

            # 최적화 기준 입력 UI 구성
            self.distribution_inputs = self.AllocationInputs(
                self,
                self.on_optimization_input_changed,
                (
                    ("strength", "힘"),
                    ("dexterity", "민첩"),
                    ("vitality", "생명력"),
                    ("luck", "행운"),
                ),
            )
            self.target_distribution_inputs = self.TargetMinimumInputs(
                self,
                self.on_optimization_input_changed,
                (
                    ("strength", "힘"),
                    ("dexterity", "민첩"),
                    ("vitality", "생명력"),
                    ("luck", "행운"),
                ),
            )
            self.danjeon_inputs = self.AllocationInputs(
                self,
                self.on_optimization_input_changed,
                (
                    ("upper", "상단전"),
                    ("middle", "중단전"),
                    ("lower", "하단전"),
                ),
            )
            self.target_danjeon_inputs = self.TargetMinimumInputs(
                self,
                self.on_optimization_input_changed,
                (
                    ("upper", "상단전"),
                    ("middle", "중단전"),
                    ("lower", "하단전"),
                ),
            )
            self.candidate_group_inputs = CandidateGroupInputs(
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
            base_row.addWidget(self.metric_manage_button)
            base_row.addWidget(self.level_input_widget)
            base_row.addWidget(self.realm_input)
            base_row.addStretch(1)
            base_card.add_layout(base_row)

            stats_card = SectionCard(self, "전체 스탯")
            paste_btn: StyledButton = StyledButton(
                self, "전체 스탯 붙여넣기", kind="normal", point_size=9
            )
            paste_btn.clicked.connect(self._paste_stats_from_clipboard)
            ocr_btn: StyledButton = StyledButton(
                self, "화면에서 불러오기", kind="normal", point_size=9
            )
            ocr_btn.clicked.connect(self._ocr_stats_from_screen)
            paste_btn_row: QHBoxLayout = QHBoxLayout()
            paste_btn_row.setContentsMargins(0, 0, 0, 0)
            paste_btn_row.addStretch(1)
            paste_btn_row.addWidget(ocr_btn)
            paste_btn_row.addWidget(paste_btn)
            stats_card.add_layout(paste_btn_row)
            self._paste_btn: StyledButton = paste_btn
            self._ocr_btn: StyledButton = ocr_btn
            stats_card.add_widget(self.stats_inputs)

            scroll_card = SectionCard(self, "무공비급 레벨")
            scroll_card.add_widget(self.skills)

            delta_card = SectionCard(self, "사용자 지정 스탯 변화량")
            delta_card.add_widget(self.custom_delta_inputs)

            opt_card = SectionCard(self, "현재 선택 입력")
            opt_card.add_sub_title("스탯 분배")
            opt_card.add_widget(self.distribution_inputs)
            opt_card.add_sub_title("목표 분배 미리보기")
            opt_card.add_widget(self.target_distribution_inputs)
            # 최소분배 공통 안내 문구
            minimum_tip_label: QLabel = QLabel(
                "팁: 최소분배에 예상 최솟값을 넣어두면 계산이 훨씬 빨라집니다. "
                "결과가 그 값과 같다면 조금 낮춰 다시 계산해 주세요.",
                opt_card,
            )
            minimum_tip_label.setObjectName("dialogFieldLabel")
            minimum_tip_label.setFont(CustomFont(9))
            minimum_tip_label.setWordWrap(True)
            opt_card.add_widget(minimum_tip_label)
            opt_card.add_separator()
            opt_card.add_sub_title("단전")
            opt_card.add_widget(self.danjeon_inputs)
            opt_card.add_sub_title("목표 단전 미리보기")
            opt_card.add_widget(self.target_danjeon_inputs)
            opt_card.add_separator()
            opt_card.add_sub_title("후보 그룹")
            opt_card.add_widget(self.candidate_group_inputs)

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

        def set_persist_enabled(self, is_enabled: bool) -> None:
            """계산기 입력 변경의 파일 저장 허용 여부 설정"""

            # 가이드 임시 입력 중 파일 저장 차단
            self._is_persist_enabled = is_enabled

        def has_valid_navigation_inputs(self) -> bool:
            """페이지 이동에 필요한 입력 유효성 반환"""

            # 이전 그래프 진입 입력 오류 메시지 초기화
            self.last_input_error_message = None

            stats_valid: bool
            base_stats: BaseStats
            level_valid: bool
            # 기본 입력과 원시 베이스 스탯 복원
            stats_valid, base_stats = self._read_base_stats()
            level_valid, _ = self._read_level()

            # 무공비급 레벨 입력 검증
            scroll_valid: bool = self._read_scroll_levels(save_levels=False)
            if not (stats_valid and level_valid and scroll_valid):
                return False

            # 그래프 계산 가능한 공격 입력 조건 검증
            if not self._has_valid_attack_inputs(base_stats):
                return False

            # 실제 그래프 피해량이 없는 입력 차단
            if not self._has_positive_graph_damage(base_stats):
                self.last_input_error_message = TIMELINE_DAMAGE_INPUT_ERROR_MESSAGE
                return False

            return True

        def prepare_results_inputs(self) -> bool:
            """결과 계산에 사용할 현재 입력 검증 및 저장"""

            # 이전 결과 계산 입력 오류 메시지 초기화
            self.last_input_error_message = None

            # 기준 스탯과 레벨 입력 검증
            stats_valid: bool
            base_stats: BaseStats
            stats_valid, base_stats = self._read_base_stats()

            level_valid: bool
            level: int
            level_valid, level = self._read_level()

            scroll_valid: bool = self._read_scroll_levels(save_levels=False)
            if not (stats_valid and level_valid and scroll_valid):
                return False

            # 선택 전투력 공식의 추가 입력 요구 조건 확인
            try:
                build_calculator_context(
                    server_spec=app_state.macro.current_server,
                    preset=app_state.macro.current_preset,
                    skills_info=app_state.macro.current_preset.usage_settings,
                    delay_ms=app_state.macro.current_delay,
                    base_stats=base_stats,
                    target_formula_id=self._get_selected_formula_id(),
                    custom_formulas=tuple(app_state.macro.custom_power_formulas),
                )

            except ValueError as exc:
                self.last_input_error_message = str(exc)
                return False

            # 결과 계산 공통 공격 입력 조건 확인
            if not self._has_valid_attack_inputs(base_stats):
                return False

            # 현재 선택 입력 전체 검증
            optimization_valid: bool
            distribution_state: DistributionState
            target_distribution_state: TargetDistributionState
            danjeon_state: DanjeonState
            target_danjeon_state: TargetDanjeonState
            candidate_groups: list[OptimizationCandidateGroup]
            (
                optimization_valid,
                distribution_state,
                target_distribution_state,
                danjeon_state,
                target_danjeon_state,
                candidate_groups,
            ) = self._read_optimization_state()
            if not optimization_valid:
                return False

            # 사용자 지정 변화량 입력 검증
            custom_valid: bool
            custom_changes: dict[StatKey, float]
            custom_valid, custom_changes = self._read_custom_stat_changes()
            if not custom_valid:
                return False

            # 사용자 지정 변화량 적용 후 계산 가능한 스킬속도 상한 검증
            custom_resolved_stats: FinalStats = base_stats.resolve(custom_changes)
            custom_skill_speed_percent: float = custom_resolved_stats.values[
                StatKey.SKILL_SPEED_PERCENT
            ]
            custom_skill_speed_valid: bool = (
                custom_skill_speed_percent <= CALCULATOR_SKILL_SPEED_LIMIT_PERCENT
            )
            self.custom_delta_inputs.inputs[StatKey.SKILL_SPEED_PERCENT].set_valid(
                custom_skill_speed_valid
            )
            if not custom_skill_speed_valid:
                self.last_input_error_message = (
                    f"스킬속도는 {CALCULATOR_SKILL_SPEED_LIMIT_PERCENT:g}% "
                    "이하여야 합니다."
                )
                return False

            # 검증된 현재 입력을 계산 직전 상태로 일괄 저장
            self._save_base_inputs(
                base_stats=base_stats,
                level=level,
                persist=False,
            )
            self._read_scroll_levels(save_levels=True)
            self._save_optimization_inputs(
                distribution_state=distribution_state,
                target_distribution_state=target_distribution_state,
                danjeon_state=danjeon_state,
                target_danjeon_state=target_danjeon_state,
                candidate_groups=candidate_groups,
                persist=False,
            )
            self._save_custom_stat_changes(
                custom_changes=custom_changes,
                persist=False,
            )
            self._save_data_if_enabled()
            return True

        def _has_valid_attack_inputs(self, base_stats: BaseStats) -> bool:
            """전투력 계산에 필요한 공격 입력 조건 검증"""

            # 최종 공격 관련 스탯과 배율 복원
            resolved_stats: FinalStats = base_stats.resolve()
            attack_power: float = resolved_stats.values[StatKey.ATTACK]
            final_attack_multiplier: float = 1.0 + (
                resolved_stats.values[StatKey.FINAL_ATTACK_PERCENT] * 0.01
            )
            boss_attack_multiplier: float = 1.0 + (
                resolved_stats.values[StatKey.BOSS_ATTACK_PERCENT] * 0.01
            )
            skill_damage_multiplier: float = 1.0 + (
                resolved_stats.values[StatKey.SKILL_DAMAGE_PERCENT] * 0.01
            )
            skill_speed_percent: float = resolved_stats.values[
                StatKey.SKILL_SPEED_PERCENT
            ]

            # 공격 관련 입력칸 강조 상태 동기화
            attack_input_valid: bool = attack_power > 0.0
            final_attack_input_valid: bool = final_attack_multiplier > 0.0
            boss_attack_input_valid: bool = boss_attack_multiplier > 0.0
            skill_damage_input_valid: bool = skill_damage_multiplier > 0.0
            skill_speed_input_valid: bool = (
                skill_speed_percent <= CALCULATOR_SKILL_SPEED_LIMIT_PERCENT
            )
            self.stats_inputs.inputs[StatKey.ATTACK].set_valid(attack_input_valid)
            self.stats_inputs.inputs[StatKey.FINAL_ATTACK_PERCENT].set_valid(
                final_attack_input_valid
            )
            self.stats_inputs.inputs[StatKey.BOSS_ATTACK_PERCENT].set_valid(
                boss_attack_input_valid
            )
            self.stats_inputs.inputs[StatKey.SKILL_DAMAGE_PERCENT].set_valid(
                skill_damage_input_valid
            )
            self.stats_inputs.inputs[StatKey.SKILL_SPEED_PERCENT].set_valid(
                skill_speed_input_valid
            )

            # 전투력 계산 가능한 공격 입력 여부 반환
            return (
                attack_input_valid
                and final_attack_input_valid
                and boss_attack_input_valid
                and skill_damage_input_valid
                and skill_speed_input_valid
            )

        def _has_positive_graph_damage(self, base_stats: BaseStats) -> bool:
            """그래프 출력 가능한 양수 피해 이벤트 존재 여부 반환"""

            # 현재 입력 스탯 기준 최종 스탯과 스킬 타임라인 구성
            resolved_stats: FinalStats = base_stats.resolve()
            hit_events = build_calculator_timeline(
                server_spec=app_state.macro.current_server,
                preset=app_state.macro.current_preset,
                skills_info=app_state.macro.current_preset.usage_settings,
                delay_ms=app_state.macro.current_delay,
                cooltime_reduction=resolved_stats.values[StatKey.SKILL_SPEED_PERCENT],
            )

            # 보스 기준 결정론 피해 계산
            damage_events: list[DamageEvent] = build_damage_events(
                hit_events=hit_events,
                resolved_stats=resolved_stats,
                is_boss=True,
                deterministic=True,
            )

            # 실제 피해가 있는 공격만 유효 출력으로 인정
            return any(attack.damage > 0.0 for attack in damage_events)

        def load_from_preset_state(self) -> None:
            """저장된 계산기 상태 전체를 현재 입력 위젯에 반영"""

            # 프리셋 반영 중 입력 이벤트 기반 저장/재계산 억제
            self._is_loading_state = True
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator

            self._load_metric_input(calculator_input)
            self._load_level_realm_inputs(calculator_input)
            self._load_overall_stat_inputs()
            self._load_custom_delta_inputs(calculator_input)
            self._load_scroll_inputs()
            self._sync_loaded_input_validation()
            self._load_distribution_danjeon_inputs()
            self.candidate_group_inputs.load(calculator_input.candidate_groups)

            # 이번 전체 로드 기준 계산기 입력 객체와 장착 무공비급 목록 기록
            self._loaded_calculator_input = calculator_input
            self._is_loading_state = False

        def on_calculator_enter(self) -> None:
            """계산기 재진입 시 변경된 부분만 입력 위젯에 반영

            계산기 입력 객체가 교체된 경우(프리셋 변경/가이드 예시·복원)에만
            전체 로드하고, 같은 입력 객체면 메인 화면에서 바뀔 수 있는
            장착 무공비급 목록 변경만 갱신한다.
            """

            # 계산기 입력 객체가 교체됐으면(프리셋 변경/가이드) 후보 그룹 포함 전체 로드
            if self._loaded_calculator_input is not self._get_preset().info.calculator:
                self.load_from_preset_state()
                return

            # 같은 입력 객체면 장착 무공비급 목록 변경 여부만 확인
            current_scrolls: tuple[str, ...] = tuple(
                self._get_preset().skills.equipped_scrolls
            )
            if current_scrolls == self._loaded_equipped_scrolls:
                return

            # 장착 목록이 달라졌으면 무공비급 입력 위젯만 재구성
            self._is_loading_state = True
            self._load_scroll_inputs()
            self._read_scroll_levels(save_levels=False)
            self._is_loading_state = False

        def apply_character_fill_inputs(self) -> None:
            """캐릭터 적용 결과를 스탯/레벨/경지/분배/단전 입력에만 반영

            무공비급 입력과 후보 그룹은 건드리지 않는다.
            """

            self._is_loading_state = True
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator

            self._load_level_realm_inputs(calculator_input)
            self._load_overall_stat_inputs()
            self._load_distribution_danjeon_inputs()
            self._sync_loaded_input_validation()
            self._is_loading_state = False

        def _load_metric_input(self, calculator_input: CalculatorPresetInput) -> None:
            """기준 전투력 공식 입력 복원"""

            self._refresh_formula_options()
            self.metric_combobox.setCurrentIndex(
                self.metric_options.index(calculator_input.selected_formula_id)
            )

        def _load_level_realm_inputs(
            self, calculator_input: CalculatorPresetInput
        ) -> None:
            """레벨/경지 입력 복원"""

            self.level_input.setText(str(calculator_input.level))
            self.realm_combobox.setCurrentIndex(
                self.realm_options.index(calculator_input.realm_tier)
            )

        def _load_overall_stat_inputs(self) -> None:
            """저장된 원시 베이스 스탯의 최종 표시값 복원"""

            display_base_stats: dict[StatKey, str] = self._get_initial_base_stats()
            for stat_key in STAT_SPECS.keys():
                self.stats_inputs.inputs[stat_key].setText(display_base_stats[stat_key])

        def _load_custom_delta_inputs(
            self, calculator_input: CalculatorPresetInput
        ) -> None:
            """추가 스탯 변화 입력 복원"""

            for stat_key in STAT_SPECS.keys():
                self.custom_delta_inputs.inputs[stat_key].setText(
                    f"{calculator_input.custom_stat_changes[stat_key.value]:g}"
                )

        def _load_scroll_inputs(self) -> None:
            """현재 장착 무공비급 기준 입력칸 재구성 및 저장 레벨 반영"""

            self.skills.rebuild_entries(
                SkillInputs.build_entries(),
                self.on_base_input_changed,
            )

            # 저장된 무공비급 레벨 입력값 재반영
            for input_widget, entry in zip(self.skills.inputs, self.skills.entries):
                input_widget.setText(
                    str(self._get_preset().info.get_scroll_level(entry.scroll_id))
                )

            # 이번에 반영한 장착 무공비급 목록 기록
            self._loaded_equipped_scrolls = tuple(
                self._get_preset().skills.equipped_scrolls
            )

        def _sync_loaded_input_validation(self) -> None:
            """로드된 입력값 기준 검증 스타일 동기화"""

            stats_valid: bool
            base_stats: BaseStats
            stats_valid, base_stats = self._read_base_stats()
            self._read_custom_stat_changes()
            self._read_level()
            self._read_scroll_levels(save_levels=False)
            if stats_valid:
                self._has_valid_attack_inputs(base_stats)

        class OverallStatInputs(QFrame):
            COLUMN_COUNT: int = 4

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
                    value_label.setObjectName("resultValueLabel")
                    value_label.setFont(CustomFont(11))
                    value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

                    # +/- 부호 기준 색상 코딩
                    try:
                        numeric: float = float(value.replace(",", ""))
                        if numeric > 0:
                            sign: str = "positive"
                        elif numeric < 0:
                            sign = "negative"
                        else:
                            sign = "neutral"
                    except ValueError:
                        sign = "neutral"
                    value_label.setProperty("sign", sign)

                    # 스타일 즉시 적용
                    value_label.style().unpolish(value_label)
                    value_label.style().polish(value_label)

                    row_layout.addWidget(title_label)
                    row_layout.addStretch(1)
                    row_layout.addWidget(value_label)
                    self._layout.addWidget(row_widget)

        class AllocationInputs(QFrame):
            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
                fields: tuple[tuple[str, str], ...],
            ) -> None:
                super().__init__(parent)

                # 현재 포인트 입력 행 구성
                self.inputs: dict[str, CustomLineEdit] = {}
                layout: QHBoxLayout = QHBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(10)

                for field_name, label in fields:
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

        class TargetMinimumInputs(QFrame):
            def __init__(
                self,
                parent: QWidget,
                connected_function: Callable[[], None],
                fields: tuple[tuple[str, str], ...],
            ) -> None:
                super().__init__(parent)

                # 목표 입력 행 구성
                self.inputs: dict[str, CustomLineEdit] = {}
                layout: QHBoxLayout = QHBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(10)

                for field_name, label in fields:
                    item_widget: KVInput = KVInput(
                        self,
                        label,
                        "0",
                        connected_function,
                        max_width=80,
                    )
                    self.inputs[field_name] = item_widget.input
                    layout.addWidget(item_widget)

                # 최소분배 옵션 체크박스 구성
                self.minimum_checkbox: QCheckBox = QCheckBox(
                    "최적화에 최소분배로 반영", self
                )
                self.minimum_checkbox.stateChanged.connect(connected_function)
                layout.addWidget(self.minimum_checkbox)
                layout.addStretch(1)
                self.setLayout(layout)

        def _get_preset(self) -> "MacroPreset":
            """현재 선택 프리셋 반환"""

            return app_state.macro.current_preset

        def _get_calculator_realm(self) -> RealmTier:
            """저장된 현재 경지 반환"""

            return self._get_preset().info.calculator.realm_tier

        def _get_initial_base_stats(self) -> dict[StatKey, str]:
            """저장된 베이스 스탯 입력 문자열 맵 반환"""

            # 저장된 원시 베이스 스탯의 최종 표시값 복원
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            resolved_values: dict[StatKey, float] = (
                calculator_input.base_stats.resolve().values
            )
            values: dict[StatKey, str] = {}
            for stat_key in STAT_SPECS.keys():
                values[stat_key] = f"{resolved_values[stat_key]:.2f}".rstrip(
                    "0"
                ).rstrip(".")

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

        def _refresh_formula_options(self) -> None:
            """전역 빌트인/커스텀 공식 목록을 콤보박스에 재반영"""

            # 전역 공식 목록과 표시명 맵을 다시 구성하는
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            formula_labels: dict[str, str] = _build_formula_label_map(
                app_state.macro.custom_power_formulas
            )
            self.metric_options = _build_formula_options(
                app_state.macro.custom_power_formulas
            )

            # 저장된 선택 공식 유지 상태로 콤보박스 항목 재구성
            self.metric_combobox.blockSignals(True)
            self.metric_combobox.clear()
            formula_names: list[str] = [
                formula_labels[formula_id] for formula_id in self.metric_options
            ]
            self.metric_combobox.addItems(formula_names)
            self.metric_combobox.setCurrentIndex(
                self.metric_options.index(calculator_input.selected_formula_id)
            )

            # 커스텀 공식 이름 길이를 반영한 콤보박스 최소 폭 재계산
            longest_item_width: int = 0
            formula_name: str
            for formula_name in formula_names:
                item_width: int = self.metric_combobox.fontMetrics().horizontalAdvance(
                    formula_name
                )
                if item_width > longest_item_width:
                    longest_item_width = item_width

            minimum_combobox_width: int = longest_item_width + 44
            self.metric_combobox.setMinimumWidth(minimum_combobox_width)
            self.metric_input.setMinimumWidth(minimum_combobox_width)
            self.metric_combobox.blockSignals(False)

        def _open_formula_manager(self) -> None:
            """사용자 정의 전투력 공식 관리 다이얼로그 열기"""

            # 다이얼로그 저장 결과를 현재 콤보박스 목록에 즉시 반영
            formula_dialog: CustomPowerFormulaManageDialog = (
                CustomPowerFormulaManageDialog(parent=self)
            )
            formula_dialog.exec()
            self._refresh_formula_options()

        def _get_selected_formula_id(self) -> str:
            """현재 선택 전투력 공식 ID 반환"""

            # 콤보박스 현재 인덱스를 공식 ID 목록에 매핑
            selected_formula_id: str = self.metric_options[
                self.metric_combobox.currentIndex()
            ]
            return selected_formula_id

        def _load_distribution_danjeon_inputs(self) -> None:
            """저장된 분배/단전 입력 상태 로드"""

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
            self.target_distribution_inputs.inputs["strength"].setText(
                str(calculator_input.target_distribution.strength)
            )
            self.target_distribution_inputs.inputs["dexterity"].setText(
                str(calculator_input.target_distribution.dexterity)
            )
            self.target_distribution_inputs.inputs["vitality"].setText(
                str(calculator_input.target_distribution.vitality)
            )
            self.target_distribution_inputs.inputs["luck"].setText(
                str(calculator_input.target_distribution.luck)
            )

            # 최소분배 체크박스 상태 복원
            self.target_distribution_inputs.minimum_checkbox.setChecked(
                calculator_input.target_distribution.is_minimum
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
            self.target_danjeon_inputs.inputs["upper"].setText(
                str(calculator_input.target_danjeon.upper)
            )
            self.target_danjeon_inputs.inputs["middle"].setText(
                str(calculator_input.target_danjeon.middle)
            )
            self.target_danjeon_inputs.inputs["lower"].setText(
                str(calculator_input.target_danjeon.lower)
            )
            self.target_danjeon_inputs.minimum_checkbox.setChecked(
                calculator_input.target_danjeon.is_minimum
            )

        @staticmethod
        def _read_integer_inputs(
            inputs: dict[str, CustomLineEdit],
        ) -> tuple[bool, dict[str, int]]:
            """정수 입력 묶음 복원 및 검증"""

            # 숫자 문자열 입력값을 정수 맵으로 변환
            is_valid: bool = True
            values: dict[str, int] = {}
            for field_name, input_widget in inputs.items():
                text: str = input_widget.text()
                if not text.isdigit():
                    input_widget.set_valid(False)
                    is_valid = False
                    values[field_name] = 0
                    continue

                input_widget.set_valid(True)
                values[field_name] = int(text)

            return is_valid, values

        def _read_distribution_state(self) -> tuple[bool, DistributionState]:
            """현재 스탯 분배 상태 복원"""

            is_valid: bool
            values: dict[str, int]
            is_valid, values = self._read_integer_inputs(
                self.distribution_inputs.inputs
            )

            distribution_state: DistributionState = DistributionState(
                strength=values["strength"],
                dexterity=values["dexterity"],
                vitality=values["vitality"],
                luck=values["luck"],
                is_locked=self.distribution_inputs.lock_checkbox.isChecked(),
                use_reset=self.distribution_inputs.reset_checkbox.isChecked(),
            )
            return is_valid, distribution_state

        def _read_target_distribution_state(
            self,
        ) -> tuple[bool, TargetDistributionState]:
            """목표 스탯 분배 상태 복원"""

            is_valid: bool
            values: dict[str, int]
            is_valid, values = self._read_integer_inputs(
                self.target_distribution_inputs.inputs
            )

            # 최소분배 체크 상태 확인
            is_minimum: bool = (
                self.target_distribution_inputs.minimum_checkbox.isChecked()
            )

            target_distribution_state: TargetDistributionState = (
                TargetDistributionState(
                    strength=values["strength"],
                    dexterity=values["dexterity"],
                    vitality=values["vitality"],
                    luck=values["luck"],
                    is_minimum=is_minimum,
                )
            )
            return is_valid, target_distribution_state

        def _read_danjeon_state(self) -> tuple[bool, DanjeonState]:
            """현재 단전 상태 복원"""

            is_valid: bool
            values: dict[str, int]
            is_valid, values = self._read_integer_inputs(self.danjeon_inputs.inputs)

            danjeon_state: DanjeonState = DanjeonState(
                upper=values["upper"],
                middle=values["middle"],
                lower=values["lower"],
                is_locked=self.danjeon_inputs.lock_checkbox.isChecked(),
                use_reset=self.danjeon_inputs.reset_checkbox.isChecked(),
            )
            return is_valid, danjeon_state

        def _read_target_danjeon_state(self) -> tuple[bool, TargetDanjeonState]:
            """목표 단전 상태 복원"""

            is_valid: bool
            values: dict[str, int]
            is_valid, values = self._read_integer_inputs(
                self.target_danjeon_inputs.inputs
            )

            # 최소분배 체크 상태 확인
            is_minimum: bool = self.target_danjeon_inputs.minimum_checkbox.isChecked()

            target_danjeon_state: TargetDanjeonState = TargetDanjeonState(
                upper=values["upper"],
                middle=values["middle"],
                lower=values["lower"],
                is_minimum=is_minimum,
            )
            return is_valid, target_danjeon_state

        def _read_optimization_state(
            self,
        ) -> tuple[
            bool,
            DistributionState,
            TargetDistributionState,
            DanjeonState,
            TargetDanjeonState,
            list[OptimizationCandidateGroup],
        ]:
            """현재 최적화 입력 상태 전체 복원"""

            distribution_valid: bool
            distribution_state: DistributionState
            distribution_valid, distribution_state = self._read_distribution_state()

            target_distribution_valid: bool
            target_distribution_state: TargetDistributionState
            target_distribution_valid, target_distribution_state = (
                self._read_target_distribution_state()
            )

            danjeon_valid: bool
            danjeon_state: DanjeonState
            danjeon_valid, danjeon_state = self._read_danjeon_state()

            target_danjeon_valid: bool
            target_danjeon_state: TargetDanjeonState
            target_danjeon_valid, target_danjeon_state = (
                self._read_target_danjeon_state()
            )

            # 후보 그룹 입력은 항상 유효하게 보정되므로 검증 대상에서 제외
            candidate_groups: list[OptimizationCandidateGroup] = (
                self.candidate_group_inputs.build_state()
            )
            is_valid: bool = (
                distribution_valid
                and target_distribution_valid
                and danjeon_valid
                and target_danjeon_valid
            )
            return (
                is_valid,
                distribution_state,
                target_distribution_state,
                danjeon_state,
                target_danjeon_state,
                candidate_groups,
            )

        def _read_base_stats(self) -> tuple[bool, BaseStats]:
            """베이스 스탯 입력 복원 및 검증"""

            # 모든 입력칸을 순회하며 최종 표시 스탯 복원
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

            # 최종 표시 스탯의 원시 베이스 스탯 환산
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
            """무공비급 레벨 입력 검증 및 저장"""

            # 모든 무공비급 레벨을 검증하고 필요 시 현재 프리셋에 반영
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

            # 계산기 입력에 현재 기준 입력 반영
            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            calculator_input.base_stats = base_stats
            calculator_input.level = level
            calculator_input.realm_tier = self.realm_options[
                self.realm_combobox.currentIndex()
            ]
            calculator_input.selected_formula_id = self._get_selected_formula_id()
            if persist:
                self._save_data_if_enabled()

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
                self._save_data_if_enabled()

        def _save_optimization_inputs(
            self,
            distribution_state: DistributionState,
            target_distribution_state: TargetDistributionState,
            danjeon_state: DanjeonState,
            target_danjeon_state: TargetDanjeonState,
            candidate_groups: list[OptimizationCandidateGroup],
            persist: bool = True,
        ) -> None:
            """최적화 입력 상태 저장"""

            calculator_input: CalculatorPresetInput = self._get_preset().info.calculator
            calculator_input.distribution = distribution_state
            calculator_input.target_distribution = target_distribution_state
            calculator_input.danjeon = danjeon_state
            calculator_input.target_danjeon = target_danjeon_state
            calculator_input.candidate_groups = candidate_groups
            if persist:
                self._save_data_if_enabled()

        def _save_data_if_enabled(self) -> None:
            """현재 계산기 입력 저장이 허용된 경우 파일 저장"""

            # 가이드 임시 입력은 현재 세션 메모리에만 유지
            if self._is_persist_enabled:
                save_data()

        def on_optimization_input_changed(self) -> None:
            """최적화 입력 변경 시 기준 상태 분리 갱신"""

            if self._is_loading_state:
                return

            optimization_valid: bool
            distribution_state: DistributionState
            target_distribution_state: TargetDistributionState
            danjeon_state: DanjeonState
            target_danjeon_state: TargetDanjeonState
            candidate_groups: list[OptimizationCandidateGroup]
            (
                optimization_valid,
                distribution_state,
                target_distribution_state,
                danjeon_state,
                target_danjeon_state,
                candidate_groups,
            ) = self._read_optimization_state()
            if not optimization_valid:
                return

            self._save_optimization_inputs(
                distribution_state=distribution_state,
                target_distribution_state=target_distribution_state,
                danjeon_state=danjeon_state,
                target_danjeon_state=target_danjeon_state,
                candidate_groups=candidate_groups,
                persist=True,
            )

        def _ocr_stats_from_screen(self) -> None:
            """사용자가 드래그한 화면 영역을 OCR 로 인식해 검토창에 표시"""

            # OCR 중복 실행 방지 및 버튼 비활성화에 따른 포커스 이동 차단
            if self._is_ocr_running:
                return

            # OCR 실행 상태 진입 및 사용자 피드백 갱신
            self._is_ocr_running = True
            self._ocr_btn.setText("영역 선택...")

            selection_dialog: ScreenCaptureSelectionDialog = (
                ScreenCaptureSelectionDialog(self)
            )
            if selection_dialog.exec() != QDialog.DialogCode.Accepted:
                self._ocr_btn.setText("선택 취소")
                self._is_ocr_running = False
                QTimer.singleShot(
                    2000, lambda: self._ocr_btn.setText("화면에서 불러오기")
                )
                return

            selected_rect: QRect = selection_dialog.selected_rect()  # type: ignore[assignment]

            margin: int = int(selected_rect.height() * 0.05)
            padded_rect: QRect = selected_rect.adjusted(
                -margin, -margin, margin, margin
            )

            from app.scripts.ocr import capture_screen_region

            image = capture_screen_region(
                padded_rect.x(),
                padded_rect.y(),
                padded_rect.width(),
                padded_rect.height(),
            )

            self._ocr_btn.setText("인식 중...")

            worker = self._OcrWorker(self, image)
            worker.result_ready.connect(self._on_ocr_finished)
            worker.error.connect(self._on_ocr_error)
            self._ocr_worker: QThread | None = worker
            worker.start()

        def _cleanup_ocr_worker(self) -> None:
            """OCR 워커 스레드 완전 종료 후 참조 해제"""

            if self._ocr_worker is not None:
                self._ocr_worker.deleteLater()
                self._ocr_worker = None

        def _on_ocr_finished(self, candidates: dict[StatKey, OcrStatCandidate]) -> None:
            """OCR 성공 시 검토 다이얼로그를 띄우고 승인된 값만 반영"""

            self._cleanup_ocr_worker()
            review_dialog: OcrReviewDialog = OcrReviewDialog(self, candidates)
            if review_dialog.exec() != QDialog.DialogCode.Accepted:
                if review_dialog.retry_requested():
                    self._is_ocr_running = False
                    self._ocr_stats_from_screen()
                    return

                self._ocr_btn.setText("적용 취소")
                self._is_ocr_running = False
                QTimer.singleShot(
                    2000, lambda: self._ocr_btn.setText("화면에서 불러오기")
                )
                return

            stats = review_dialog.confirmed_stats()

            parsed_count: int = 0
            for stat_key, value in stats.items():
                if stat_key not in self.stats_inputs.inputs:
                    continue
                value_str: str = f"{value:g}"
                self.stats_inputs.inputs[stat_key].setText(value_str)
                parsed_count += 1

            if parsed_count > 0:
                self.on_base_input_changed()
                self._ocr_btn.setText(f"인식 완료! ({parsed_count}개)")
            else:
                self._ocr_btn.setText("인식된 스탯 없음")

            self._is_ocr_running = False
            QTimer.singleShot(2000, lambda: self._ocr_btn.setText("화면에서 불러오기"))

        def _on_ocr_error(self) -> None:
            """OCR 실패 시 에러 피드백"""

            self._cleanup_ocr_worker()
            self._ocr_btn.setText("인식 실패")
            self._is_ocr_running = False
            QTimer.singleShot(2000, lambda: self._ocr_btn.setText("화면에서 불러오기"))

        class _OcrWorker(QThread):
            """게임 화면 OCR 을 백그라운드에서 수행하는 워커 스레드"""

            result_ready = Signal(dict)
            error = Signal()

            def __init__(self, parent: QWidget, image: Image.Image) -> None:
                super().__init__(parent)
                self._image: Image.Image = image

            def run(self) -> None:
                try:
                    from app.scripts.ocr import extract_stat_candidates_from_image

                    candidates: dict[StatKey, OcrStatCandidate] = (
                        extract_stat_candidates_from_image(self._image)
                    )
                    if not candidates:
                        self.error.emit()
                        return

                    self.result_ready.emit(candidates)
                except Exception:
                    self.error.emit()

        def _paste_stats_from_clipboard(self) -> None:
            """클립보드의 전체 스탯 텍스트를 입력칸에 붙여넣기"""

            clipboard: QClipboard = QApplication.clipboard()
            if clipboard is None:
                return

            text: str = clipboard.text()
            if not text:
                return

            # STAT_SPECS 역매핑: 라벨 → StatKey
            label_to_key: dict[str, StatKey] = {
                label: key for key, label in STAT_SPECS.items()
            }

            # 탭 구분 형식 파싱
            parsed_count: int = 0
            for line in text.strip().splitlines():
                parts: list[str] = line.split("\t")
                if len(parts) != 2:
                    continue

                label: str = parts[0].strip()
                value_str: str = parts[1].strip()
                stat_key: StatKey | None = label_to_key.get(label)

                if stat_key is None or stat_key not in self.stats_inputs.inputs:
                    continue

                try:
                    float(value_str)
                except ValueError:
                    continue

                self.stats_inputs.inputs[stat_key].setText(value_str)
                parsed_count += 1

            if parsed_count > 0:
                self.on_base_input_changed()

                # 붙여넣기 완료 피드백
                self._paste_btn.setText("붙여넣기 완료!")

                QTimer.singleShot(
                    1500, lambda: self._paste_btn.setText("전체 스탯 붙여넣기")
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
            """동적 결과 목록 변경 후 상위 스택/무공비급 높이 재동기화"""

            ancestor: QWidget | None = start_widget
            scroll_area: QScrollArea | None = None
            stack_host: QWidget | None = None
            current_page: QWidget | None = None

            while ancestor is not None:
                # 무공비급 영역 도달 시 탐색 중단 — 무공비급 영역 자체는 리사이즈 불필요
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
                # 무공비급 위치가 중간 리사이즈로 틀어지는 것을 방지
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

            # 무공비급바 범위 재조정 후 현재 위치 보정
            if scroll_area is not None:
                vertical_bar: QScrollBar = scroll_area.verticalScrollBar()
                vertical_bar.setValue(min(vertical_bar.value(), vertical_bar.maximum()))
                horizontal_bar: QScrollBar = scroll_area.horizontalScrollBar()
                horizontal_bar.setValue(
                    min(horizontal_bar.value(), horizontal_bar.maximum())
                )

        class PowerResultList(QFrame):
            """현재 전투력 전용 목록"""

            def __init__(self, parent: QWidget) -> None:
                super().__init__(parent)
                self.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred,
                )
                self._layout: QVBoxLayout = QVBoxLayout(self)
                self._layout.setContentsMargins(0, 0, 0, 0)
                self._layout.setSpacing(4)
                self.setLayout(self._layout)

            def set_row(
                self,
                row: tuple[str, str],
            ) -> None:
                # 이전 결과 행 즉시 제거
                ResultsPage.ResultsView._clear_layout_widgets(self._layout)

                title: str
                value: str
                title, value = row
                row_widget: QFrame = QFrame(self)
                row_widget.setObjectName("powerResultRow")
                row_widget.setProperty("selected", True)
                row_widget.style().unpolish(row_widget)
                row_widget.style().polish(row_widget)
                row_layout: QHBoxLayout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(8, 8, 8, 8)
                row_layout.setSpacing(10)

                title_label: QLabel = QLabel(title, row_widget)
                title_label.setObjectName("powerResultLabel")
                title_label.setFont(CustomFont(13, bold=True))

                value_label: QLabel = QLabel(value, row_widget)
                value_label.setObjectName("powerResultLabel")
                value_label.setFont(CustomFont(13, bold=True))
                value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

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
                self.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred,
                )
                self._rows: list[tuple[str, str]] = []
                self._relative_mode: bool = False
                self._content_layout: QVBoxLayout = QVBoxLayout(self)
                self._content_layout.setContentsMargins(0, 0, 0, 0)
                self._content_layout.setSpacing(4)
                self.setLayout(self._content_layout)

            def set_rows(self, rows: list[tuple[str, str]]) -> None:
                self._rows = rows
                self._render()

            def set_relative_mode(self, enabled: bool) -> None:
                """최고 효율 100 기준 상대값 표시 모드 토글"""

                if self._relative_mode == enabled:
                    return
                self._relative_mode = enabled
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
                is_numeric_flags: list[bool] = []
                max_abs: float = 0.0
                for _, value in self._rows:
                    try:
                        nv: float = float(value.replace(",", ""))
                        numeric_vals.append(nv)
                        is_numeric_flags.append(True)
                        if abs(nv) > max_abs:
                            max_abs = abs(nv)
                    except ValueError:
                        numeric_vals.append(0.0)
                        is_numeric_flags.append(False)

                # 상대 효율 표시 모드 적용 가능 여부 판정
                apply_relative: bool = (
                    self._relative_mode and max_abs > 0 and all(is_numeric_flags)
                )

                # 표시용 값 문자열 사전 구성
                display_values: list[str] = []
                for i, (_, original_value) in enumerate(self._rows):
                    if apply_relative:
                        relative_value: float = (numeric_vals[i] / max_abs) * 100.0
                        display_values.append(
                            f"{relative_value:.2f}".rstrip("0").rstrip(".")
                        )
                    else:
                        display_values.append(original_value)

                for i, (title, _) in enumerate(self._rows):
                    value: str = display_values[i]
                    nv = numeric_vals[i]
                    is_best: bool = i == 0 and len(self._rows) > 1

                    row_widget: QFrame = QFrame(self)
                    row_layout: QHBoxLayout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(8, 4, 8, 4)
                    row_layout.setSpacing(8)

                    # 1위 배지
                    badge_label: QLabel = QLabel("★" if is_best else "", row_widget)
                    badge_label.setObjectName("rankedBadgeLabel")
                    badge_label.setFixedWidth(14)
                    badge_label.setFont(CustomFont(10))
                    row_layout.addWidget(badge_label)

                    # 항목 이름 — 최소 폭만 보장하고 남는 공간 확장
                    title_label: QLabel = QLabel(title, row_widget)
                    title_label.setObjectName("rankedTitleLabel")
                    title_label.setFont(CustomFont(11))
                    title_label.setFixedWidth(160)
                    row_layout.addWidget(title_label)

                    row_layout.addStretch(1)

                    # 미니 바 — stretch 오른쪽에 위치해 값과 붙어있음
                    bar_container: QFrame = QFrame(row_widget)
                    bar_container.setObjectName("rankedBarContainer")
                    bar_container.setFixedSize(80, 10)
                    if max_abs > 0:
                        bar_fill: QFrame = QFrame(bar_container)
                        bar_fill.setObjectName("rankedBarFill")
                        bar_fill.setProperty(
                            "sign",
                            "positive" if nv >= 0 else "negative",
                        )
                        bar_fill.setFixedHeight(10)
                        bar_fill.setFixedWidth(max(1, int(80 * abs(nv) / max_abs)))
                    row_layout.addWidget(bar_container)

                    # 값 — 바 바로 오른쪽에 고정폭으로 배치
                    value_label: QLabel = QLabel(value, row_widget)
                    value_label.setObjectName("resultValueLabel")
                    value_label.setFont(CustomFont(11))
                    value_label.setFixedWidth(90)
                    value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                    if nv > 0:
                        ranked_sign: str = "positive"
                    elif nv < 0:
                        ranked_sign = "negative"
                    else:
                        ranked_sign = "neutral"
                    value_label.setProperty("sign", ranked_sign)
                    value_label.style().unpolish(value_label)
                    value_label.style().polish(value_label)
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

        class OverallStatsGrid(QFrame):
            """결과 카드 공용 전체 스탯 읽기 전용 2열 그리드"""

            def __init__(self, parent: QWidget) -> None:
                super().__init__(parent)
                self.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred,
                )
                self._current_final_stats: FinalStats | None = None

                main_layout: QVBoxLayout = QVBoxLayout(self)
                main_layout.setContentsMargins(0, 0, 0, 0)
                main_layout.setSpacing(6)

                # 스탯 셀 그리드
                grid_frame: QFrame = QFrame(self)
                self._grid: QGridLayout = QGridLayout(grid_frame)
                self._grid.setVerticalSpacing(6)
                self._grid.setHorizontalSpacing(12)
                grid_frame.setLayout(self._grid)
                main_layout.addWidget(grid_frame)

                # 복사 버튼
                self._copy_btn: StyledButton = StyledButton(
                    self, "전체 스탯 복사", kind="normal", point_size=9
                )
                self._copy_btn.clicked.connect(self._copy_stats_to_clipboard)
                self._copy_btn.setVisible(False)
                btn_row: QHBoxLayout = QHBoxLayout()
                btn_row.setContentsMargins(0, 2, 0, 0)
                btn_row.addStretch(1)
                btn_row.addWidget(self._copy_btn)
                main_layout.addLayout(btn_row)

                self.setLayout(main_layout)

            def _copy_stats_to_clipboard(self) -> None:
                """현재 표시 중인 전체 스탯을 클립보드에 복사"""

                if self._current_final_stats is None:
                    return

                lines: list[str] = []
                for stat_key in OVERALL_STAT_ORDER:
                    label: str = STAT_SPECS[stat_key]
                    value: float = self._current_final_stats.values[stat_key]
                    value_text: str = f"{value:.2f}".rstrip("0").rstrip(".")
                    lines.append(f"{label}\t{value_text}")

                clipboard: QClipboard = QApplication.clipboard()
                if clipboard is not None:
                    clipboard.setText("\n".join(lines))

                # 복사 완료 피드백
                self._copy_btn.setText("복사됨!")

                QTimer.singleShot(
                    1500, lambda: self._copy_btn.setText("전체 스탯 복사")
                )

            def set_stats(self, base_stats: BaseStats | None) -> None:
                # 이전 스탯 셀 즉시 제거
                ResultsPage.ResultsView._clear_layout_widgets(self._grid)

                # 전체 스탯 표시 불가 상태 문구 출력
                if base_stats is None:
                    self._current_final_stats = None
                    self._copy_btn.setVisible(False)
                    unavail: QLabel = QLabel("표시 불가", self)
                    unavail.setObjectName("statsGridUnavailLabel")
                    unavail.setFont(CustomFont(11))
                    self._grid.addWidget(unavail, 0, 0)
                    ResultsPage.ResultsView._refresh_widget_geometry(self)
                    return

                # 베이스 스탯 해석 결과를 2열 그리드로 배치
                final_stats: "FinalStats" = base_stats.resolve()
                self._current_final_stats = final_stats
                self._copy_btn.setVisible(True)
                for row_idx, (left_key, right_key) in enumerate(OVERALL_STAT_GRID_ROWS):
                    for col_idx, stat_key in enumerate((left_key, right_key)):
                        if stat_key is None:
                            continue
                        label_text: str = STAT_SPECS[stat_key]
                        value_text: str = f"{final_stats.values[stat_key]:,.2f}".rstrip(
                            "0"
                        ).rstrip(".")

                        cell: QFrame = QFrame(self)
                        cell.setObjectName("statsGridCell")
                        cell_layout: QHBoxLayout = QHBoxLayout(cell)
                        cell_layout.setContentsMargins(8, 4, 8, 4)
                        cell_layout.setSpacing(6)

                        lbl: QLabel = QLabel(label_text, cell)
                        lbl.setObjectName("statsGridCellLabel")
                        lbl.setFont(CustomFont(10))

                        val: QLabel = QLabel(value_text, cell)
                        val.setObjectName("statsGridCellValue")
                        val.setFont(CustomFont(10))
                        val.setAlignment(Qt.AlignmentFlag.AlignRight)

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

            # 현재 전투력 카드
            self._power_list: ResultsPage.ResultsView.PowerResultList = (
                ResultsPage.ResultsView.PowerResultList(self)
            )
            self._power_card: SectionCard = SectionCard(self, "현재 전투력")
            self._power_card.add_widget(self._power_list)

            # 스탯 1당 효율 + 무공비급 +1 효율 통합 카드
            self._stat_list: ResultsPage.ResultsView.RankedResultList = (
                ResultsPage.ResultsView.RankedResultList(self)
            )
            self._scroll_list: ResultsPage.ResultsView.RankedResultList = (
                ResultsPage.ResultsView.RankedResultList(self)
            )
            _vsep: QFrame = QFrame(self)
            _vsep.setObjectName("resultsVSep")
            _vsep.setFixedWidth(1)
            _vsep.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
            _scroll_wrapper: QWidget = QWidget(self)
            _scroll_wrapper_layout: QVBoxLayout = QVBoxLayout(_scroll_wrapper)
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

            # 스탯/스킬 효율 상대 표시 토글 체크박스 — 헤더 오른쪽에 배치
            self._relative_efficiency_checkbox: QCheckBox = QCheckBox(
                "최고 효율을 100으로 표시", self._stat_scroll_card
            )
            self._relative_efficiency_checkbox.stateChanged.connect(
                self._on_relative_efficiency_toggled
            )
            self._stat_scroll_card.add_header_widget(self._relative_efficiency_checkbox)

            # 최적화 결과 카드
            self._opt_result_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )
            self._opt_stats_grid: ResultsPage.ResultsView.OverallStatsGrid = (
                ResultsPage.ResultsView.OverallStatsGrid(self)
            )
            self._opt_card: SectionCard = SectionCard(self, "최적화 결과")
            self._opt_card.add_widget(self._opt_result_list)
            self._opt_card.add_separator()
            self._opt_card.add_sub_title("최적화 후 전체 스탯")
            self._opt_card.add_widget(self._opt_stats_grid)

            # 후보 선택 결과 카드
            self._candidate_selection_result_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )
            self._candidate_selection_stats_grid: (
                ResultsPage.ResultsView.OverallStatsGrid
            ) = ResultsPage.ResultsView.OverallStatsGrid(self)
            self._candidate_selection_card: SectionCard = SectionCard(
                self, "후보 선택 결과"
            )
            self._candidate_selection_card.add_widget(
                self._candidate_selection_result_list
            )
            self._candidate_selection_card.add_separator()
            self._candidate_selection_card.add_sub_title("후보 선택 후 전체 스탯")
            self._candidate_selection_card.add_widget(
                self._candidate_selection_stats_grid
            )
            self._candidate_selection_card.setVisible(False)

            # 성장 효율 카드 (레벨업 + 경지)
            self._level_up_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )
            self._realm_up_list: ResultsPage.Efficiency.ResultList = (
                ResultsPage.Efficiency.ResultList(self)
            )

            def _make_sub_title(text: str, parent: QWidget) -> QLabel:
                lbl = QLabel(text, parent)
                lbl.setObjectName("resultsSubTitle")
                lbl.setFont(CustomFont(11, bold=True))
                return lbl

            _level_wrapper = QWidget(self)
            _level_wrapper_layout = QVBoxLayout(_level_wrapper)
            _level_wrapper_layout.setContentsMargins(0, 0, 0, 0)
            _level_wrapper_layout.setSpacing(6)
            _level_wrapper_layout.addWidget(_make_sub_title("레벨 1업", _level_wrapper))
            _level_wrapper_layout.addWidget(self._level_up_list)
            _level_wrapper_layout.addStretch(1)
            _level_wrapper.setLayout(_level_wrapper_layout)

            _realm_wrapper = QWidget(self)
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
            _growth_vsep.setObjectName("resultsVSep")
            _growth_vsep.setFixedWidth(1)
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
            self._custom_stats_grid: ResultsPage.ResultsView.OverallStatsGrid = (
                ResultsPage.ResultsView.OverallStatsGrid(self)
            )
            self._custom_card: SectionCard = SectionCard(
                self, "사용자 지정 변화량 결과"
            )
            self._custom_card.add_widget(self._custom_list)
            self._custom_card.add_separator()
            self._custom_card.add_sub_title("변화 적용 후 전체 스탯")
            self._custom_card.add_widget(self._custom_stats_grid)
            self._custom_card.setVisible(False)

            def _make_preview_card(
                title: str,
                stats_title: str,
            ) -> tuple[
                SectionCard,
                "ResultsPage.Efficiency.ResultList",
                "ResultsPage.ResultsView.OverallStatsGrid",
            ]:
                # 미리보기 공통 카드 구성
                result_list: ResultsPage.Efficiency.ResultList = (
                    ResultsPage.Efficiency.ResultList(self)
                )
                stats_grid: ResultsPage.ResultsView.OverallStatsGrid = (
                    ResultsPage.ResultsView.OverallStatsGrid(self)
                )
                card: SectionCard = SectionCard(self, title)
                card.add_widget(result_list)
                card.add_separator()
                card.add_sub_title(stats_title)
                card.add_widget(stats_grid)
                card.setVisible(False)
                return card, result_list, stats_grid

            # 목표 미리보기 결과 카드
            (
                self._target_card,
                self._target_list,
                self._target_stats_grid,
            ) = _make_preview_card(
                "목표 분배 미리보기",
                "목표 분배 적용 후 전체 스탯",
            )
            (
                self._target_danjeon_card,
                self._target_danjeon_list,
                self._target_danjeon_stats_grid,
            ) = _make_preview_card(
                "목표 단전 미리보기",
                "목표 단전 적용 후 전체 스탯",
            )

            layout: QVBoxLayout = QVBoxLayout(self)
            layout.addWidget(self._power_card)
            layout.addWidget(self._stat_scroll_card)
            layout.addWidget(self._opt_card)
            layout.addWidget(self._candidate_selection_card)
            layout.addWidget(self._growth_card)
            layout.addWidget(self._custom_card)
            layout.addWidget(self._target_card)
            layout.addWidget(self._target_danjeon_card)
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)
            self.setLayout(layout)

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        def _set_preview_card(
            self,
            card: SectionCard,
            result_list: "ResultsPage.Efficiency.ResultList",
            stats_grid: "ResultsPage.ResultsView.OverallStatsGrid",
            summary_row: tuple[str, str] | None,
            delta_row: tuple[str, str] | None,
            base_stats: BaseStats | None,
        ) -> None:
            """미리보기 결과 카드 표시 상태 반영"""

            # 미리보기 결과 존재 여부 확인
            has_result: bool = summary_row is not None and delta_row is not None
            card.setVisible(has_result)
            if not has_result:
                stats_grid.set_stats(None)
                return

            # 미리보기 요약/전투력 변화량/전체 스탯 동기화
            result_list.set_rows([summary_row, delta_row])
            stats_grid.set_stats(base_stats)

        def set_error_outputs(self) -> None:
            """결과 페이지 오류 상태 출력"""

            error_rows: list[tuple[str, str]] = [("상태", "오류")]
            error_row: tuple[str, str] = ("상태", "오류")
            self._power_list.set_row(error_row)
            self._stat_list.set_rows(error_rows)
            self._level_up_list.set_rows(error_rows)
            self._realm_up_list.set_rows(error_rows)
            self._scroll_list.set_rows(error_rows)
            self._custom_card.setVisible(False)

            # 사용자 지정 변화량 전체 스탯 표시 초기화
            self._custom_stats_grid.set_stats(None)
            self._set_preview_card(
                self._target_card,
                self._target_list,
                self._target_stats_grid,
                None,
                None,
                None,
            )
            self._set_preview_card(
                self._target_danjeon_card,
                self._target_danjeon_list,
                self._target_danjeon_stats_grid,
                None,
                None,
                None,
            )
            self._opt_result_list.set_rows(error_rows)
            self._opt_stats_grid.set_stats(None)
            self._candidate_selection_card.setVisible(False)
            self._candidate_selection_stats_grid.set_stats(None)

        def set_loading_outputs(self) -> None:
            """계산 시작 시 로딩 상태 출력"""

            loading_rows: list[tuple[str, str]] = [("상태", "계산 중...")]
            loading_row: tuple[str, str] = ("상태", "계산 중...")
            self._power_list.set_row(loading_row)
            self._stat_list.set_rows(loading_rows)
            self._level_up_list.set_rows(loading_rows)
            self._realm_up_list.set_rows(loading_rows)
            self._scroll_list.set_rows(loading_rows)
            self._custom_card.setVisible(False)

            # 사용자 지정 변화량 전체 스탯 표시 초기화
            self._custom_stats_grid.set_stats(None)
            self._set_preview_card(
                self._target_card,
                self._target_list,
                self._target_stats_grid,
                None,
                None,
                None,
            )
            self._set_preview_card(
                self._target_danjeon_card,
                self._target_danjeon_list,
                self._target_danjeon_stats_grid,
                None,
                None,
                None,
            )
            self._opt_result_list.set_rows(loading_rows)
            self._opt_stats_grid.set_stats(None)
            self._candidate_selection_card.setVisible(False)
            self._candidate_selection_stats_grid.set_stats(None)

        def _on_relative_efficiency_toggled(self) -> None:
            """스탯/스킬 효율 상대 표시 체크박스 토글 반영"""

            enabled: bool = self._relative_efficiency_checkbox.isChecked()
            self._stat_list.set_relative_mode(enabled)
            self._scroll_list.set_relative_mode(enabled)

        def set_output_rows(self, output_rows: ResultsPage.OutputRows) -> None:
            """백그라운드 계산 완료 결과 UI 반영"""

            # 완료된 결과 구조를 각 카드에 반영
            self._power_list.set_row(output_rows.current_power)
            self._stat_list.set_rows(output_rows.stat_efficiency)
            self._level_up_list.set_rows(output_rows.level_up)
            self._realm_up_list.set_rows(output_rows.realm_up)
            self._scroll_list.set_rows(output_rows.scroll_efficiency)
            self._custom_card.setVisible(output_rows.custom_delta is not None)
            if output_rows.custom_delta is not None:
                # 사용자 지정 변화량 결과 카드 하위 섹션 동기화
                self._custom_list.set_rows([output_rows.custom_delta])
                self._custom_stats_grid.set_stats(output_rows.custom_base_stats)
            else:
                # 사용자 지정 변화량 미입력 시 이전 전체 스탯 표시 제거
                self._custom_stats_grid.set_stats(None)

            # 목표 분배/단전 미리보기 결과 카드 동기화
            self._set_preview_card(
                self._target_card,
                self._target_list,
                self._target_stats_grid,
                output_rows.target_distribution_summary,
                output_rows.target_delta,
                output_rows.target_base_stats,
            )
            self._set_preview_card(
                self._target_danjeon_card,
                self._target_danjeon_list,
                self._target_danjeon_stats_grid,
                output_rows.target_danjeon_summary,
                output_rows.target_danjeon_delta,
                output_rows.target_danjeon_base_stats,
            )
            self._opt_result_list.set_rows(output_rows.optimization_result)
            self._opt_stats_grid.set_stats(output_rows.optimized_base_stats)
            self._candidate_selection_card.setVisible(
                output_rows.candidate_selection_result is not None
            )
            if output_rows.candidate_selection_result is not None:
                self._candidate_selection_result_list.set_rows(
                    output_rows.candidate_selection_result
                )
                self._candidate_selection_stats_grid.set_stats(
                    output_rows.candidate_selection_base_stats
                )
            else:
                self._candidate_selection_stats_grid.set_stats(None)


class SkillInputs(QFrame):
    @dataclass(frozen=True)
    class Entry:
        """무공비급 레벨 입력 UI 한 칸의 표시/저장 정보"""

        title: str
        value: int
        scroll_id: str

    @staticmethod
    def build_entries() -> list["SkillInputs.Entry"]:
        """현재 서버/프리셋 기준 무공비급 레벨 입력 목록 구성"""

        preset: MacroPreset = app_state.macro.current_preset
        entries: list[SkillInputs.Entry] = []

        # 현재 프리셋 장착 순서 기준 무공비급 입력 목록 구성
        scroll_id: str
        for scroll_id in preset.skills.equipped_scrolls:
            # 빈 무공비급 슬롯 제외
            if not scroll_id:
                continue

            # 장착 무공비급 정의 조회 및 저장 레벨 연결
            scroll_def: ScrollDef = (
                app_state.macro.current_server.skill_registry.get_scroll(scroll_id)
            )
            entries.append(
                SkillInputs.Entry(
                    title=scroll_def.name,
                    value=preset.info.get_scroll_level(scroll_id),
                    scroll_id=scroll_id,
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

        # 그리드 레이아웃 위젯 생성
        self._grid_layout: QGridLayout = QGridLayout(self)

        # 아이템을 저장할 리스트
        self.entries: list[SkillInputs.Entry] = entries
        self.inputs: list[CustomLineEdit] = []
        self._images: list[SkillImage] = []
        self.popup_manager: PopupManager = popup_manager

        # 초기 입력 목록 기준 그리드 구성
        self._rebuild_grid_items(connected_function)

        # 그리드 레이아웃 간격 설정
        self._grid_layout.setVerticalSpacing(10)
        self._grid_layout.setHorizontalSpacing(20)

        # 레이아웃 설정
        self.setLayout(self._grid_layout)

        # 크기 정책: 가로는 부모 크기 최대, 세로는 내용에 맞게 최소
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def rebuild_entries(
        self,
        entries: list["SkillInputs.Entry"],
        connected_function: Callable[[], None],
    ) -> None:
        """현재 장착 무공비급 기준 입력 위젯 재구성"""

        # 기존 입력 위젯 제거 및 내부 참조 초기화
        while self._grid_layout.count():
            child_item: QLayoutItem | None = self._grid_layout.takeAt(0)
            if child_item is None:
                continue

            child_widget: QWidget | None = child_item.widget()
            if child_widget is None:
                continue

            child_widget.deleteLater()

        # 새 장착 무공비급 입력 목록 반영
        self.entries = entries
        self.inputs = []
        self._images = []
        self._rebuild_grid_items(connected_function)

    def _rebuild_grid_items(self, connected_function: Callable[[], None]) -> None:
        """현재 entries 기준 입력 그리드 구성"""

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
            self._grid_layout.addWidget(item_widget, row, column)

            # 아이템 위젯을 리스트에 저장
            self.inputs.append(item_widget.input)
            self._images.append(item_widget.image)

    def refresh_icons(self) -> None:
        """현재 테마 기준 무공비급 아이콘 갱신"""

        # 캐시 갱신 이후 계산기 입력 아이콘 재요청
        for entry, image in zip(self.entries, self._images, strict=True):
            icon_pixmap: QPixmap = resource_registry.get_scroll_pixmap(entry.scroll_id)
            image.setPixmap(icon_pixmap)

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

            # 전체 layout 설정
            grid: QGridLayout = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)

            # 레이블
            label: QLabel = QLabel(entry.title, self)
            label.setObjectName("skillInputLabel")
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

            # 무공비급 아이콘 우선, 없으면 개별 스킬 아이콘 사용
            icon_size: int = level_input.sizeHint().height()
            icon_pixmap: QPixmap = resource_registry.get_scroll_pixmap(entry.scroll_id)
            self.image: SkillImage = SkillImage(
                self,
                icon_pixmap,
                icon_size,
            )

            # 계산기 무공비급 레벨 아이콘에 공용 호버 카드 연결
            self.popup_manager.bind_hover_card(
                self.image,
                self._build_scroll_hover_card,
            )

            # 탭 순서를 설정하기 위해 외부에서 접근 가능하도록 설정
            self.input: CustomLineEdit = level_input.input

            # layout에 추가
            grid.addWidget(label, 0, 0, 1, 2)
            grid.addWidget(self.image, 1, 0)
            grid.addWidget(level_input, 1, 1)

            # 위젯 사이 간격 설정
            grid.setVerticalSpacing(10)
            grid.setHorizontalSpacing(5)

            # layout 설정
            self.setLayout(grid)

        def _build_scroll_hover_card(self) -> HoverCardData:
            """계산기 무공비급 아이콘 기준 호버 카드 구성"""

            # 현재 서버 무공비급 정의와 저장 레벨 기준으로 카드 내용 구성
            scroll_def: "ScrollDef" = (
                app_state.macro.current_server.skill_registry.get_scroll(
                    self.entry.scroll_id
                )
            )
            level: int = app_state.macro.current_preset.info.get_scroll_level(
                self.entry.scroll_id
            )
            return self.popup_manager.build_scroll_hover_card(scroll_def, level)


class AnalysisDetails(QFrame):
    DETAIL_KEYS: tuple[str, ...] = (
        "min",
        "max",
        "p25",
        "p75",
    )

    def __init__(
        self,
        mainframe: QWidget,
        analysis: list[GraphAnalysis],
    ) -> None:
        super().__init__(mainframe)

        self.details: list[AnalysisDetails.Analysis] = [
            self.Analysis(
                self,
                analysis[i],
                self.DETAIL_KEYS,
                str(i),
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
            slot: str,
        ) -> None:
            super().__init__(parent)

            self.setObjectName("analysisCard")

            color_frame = QFrame(self)
            color_frame.setObjectName("analysisAccentBar")
            color_frame.setProperty("slot", slot)
            color_frame.setFixedWidth(3)

            title = QLabel(analysis.title, self)
            title.setObjectName("analysisCardLabel")
            title.setFont(CustomFont(14))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.number = QLabel(analysis.value, self)
            self.number.setObjectName("analysisCardLabel")
            self.number.setFont(CustomFont(18))
            self.number.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.statistics: list[AnalysisDetails.Statistic] = []
            for stat in statistics:
                value: str = analysis.get_data_from_str(stat)
                detail = AnalysisDetails.Statistic(self, stat, value)

                self.statistics.append(detail)

            statistics_layout = QGridLayout()
            for i, stat in enumerate(self.statistics):
                row: int = i // 2
                column: int = i % 2

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

            title = QLabel(name, self)
            title.setObjectName("statisticNameLabel")
            title.setFont(CustomFont(8))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.number = QLabel(value, self)
            self.number.setObjectName("statisticValueLabel")
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
        self.setObjectName("simTitle")
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

            self.setObjectName("navBtn")
            self.setProperty("active", is_active)
            self.setFont(CustomFont(12))

            # 최소 크기 설정
            self.setMinimumSize(100, 30)

            # 클릭 시 함수 연결
            self.clicked.connect(partial(func, i))

    def __init__(self, parent: QWidget, func1: Callable, func2: Callable):
        super().__init__(parent)

        layout = QHBoxLayout(self)

        # 네비게이션바 텍스트
        nav_texts: list[str] = ["정보 입력", "시뮬레이터", "스탯 계산기", "캐릭터"]

        # 네비게이션바 버튼들
        # 첫 번째 버튼만 활성화 상태로 시작
        self.buttons: list[QPushButton] = [
            Navigation.NavButton(nav_texts[i], self, i == 0, i, func1)
            for i in range(len(nav_texts))
        ]

        # 닫기 버튼
        self.close_button: QPushButton = QPushButton(self)
        self.close_button.setObjectName("simNavCloseBtn")
        self.close_button.setIcon(QIcon(self._load_close_icon(theme_manager.is_dark)))
        self.close_button.setIconSize(QSize(15, 15))
        self.close_button.clicked.connect(lambda: func2(0))

        self.buttons.append(self.close_button)

        for nav_index in range(len(nav_texts)):
            layout.addWidget(self.buttons[nav_index])

        # 오른쪽 끝에 닫기 버튼 배치
        layout.addStretch()
        layout.addWidget(self.close_button)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 테마 전환 시 닫기 버튼 아이콘 동기화
        theme_manager.theme_changed.connect(self._on_theme_changed)

    @staticmethod
    def _load_close_icon(dark: bool) -> QPixmap:
        """현재 테마 기준 계산기 닫기 아이콘 로드"""

        # 현재 테마 기준 닫기 아이콘 로드
        return QPixmap(get_theme_image_path("x.png", dark))

    def _on_theme_changed(self, dark: bool) -> None:
        """테마 전환 시 계산기 닫기 버튼 아이콘 갱신"""

        # 현재 테마 기준 아이콘 재적용
        self.close_button.setIcon(QIcon(self._load_close_icon(dark)))
