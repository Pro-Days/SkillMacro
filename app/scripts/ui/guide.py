from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.calculator_models import (
    BaseStats,
    CalculatorPresetInput,
    DanjeonState,
    DistributionState,
    EquippedState,
    PowerMetric,
    RealmTier,
    STAT_SPECS,
    StatKey,
    TargetDistributionState,
)
from app.scripts.custom_classes import CustomFont
from app.scripts.data_manager import save_data
from app.scripts.ui.themes import theme_manager

if TYPE_CHECKING:
    from app.scripts.macro_models import MacroPreset
    from app.scripts.ui.character_ui.character_page import CharacterPage
    from app.scripts.ui.main_window import MainWindow


GuideEnterAction = Callable[[], None]
GuideTargetResolver = Callable[[], QWidget | None]


def _guide_overlay_color() -> QColor:
    """현재 테마 기준 가이드 배경 필터 색상"""

    return QColor(10, 10, 18, 170) if theme_manager.is_dark else QColor(15, 23, 42, 120)


def _guide_highlight_color() -> QColor:
    """현재 테마 기준 가이드 강조 테두리 색상"""

    return QColor("#8FB3FF") if theme_manager.is_dark else QColor("#4A90D9")


def _guide_recommended_icon() -> QIcon:
    """현재 테마 기준 추천 가이드 표시점 아이콘"""

    pixmap: QPixmap = QPixmap(10, 10)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter: QPainter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_guide_highlight_color())
    painter.drawEllipse(2, 2, 6, 6)
    painter.end()
    return QIcon(pixmap)


@dataclass(frozen=True, slots=True)
class GuideStep:
    title: str
    body: str
    target_id: str | None
    enter_action: GuideEnterAction | None = None


@dataclass(frozen=True, slots=True)
class GuideDefinition:
    guide_id: str
    title: str
    steps: tuple[GuideStep, ...]
    recommended: bool = False


@dataclass(slots=True)
class CalculatorGuideSession:
    preset: MacroPreset
    calculator_input: CalculatorPresetInput
    scroll_levels: dict[str, int]


class GuideTargetRegistry:
    """현재 화면 기준 가이드 대상 위젯 조회"""

    def __init__(self, master: MainWindow) -> None:
        self.master: MainWindow = master
        self._resolvers: dict[str, GuideTargetResolver] = {}
        self._register_targets()

    def resolve(self, target_id: str) -> QWidget | None:
        """대상 ID에 해당하는 현재 위젯 반환"""

        # 등록되지 않은 대상 ID 차단
        resolver: GuideTargetResolver | None = self._resolvers.get(target_id)
        if resolver is None:
            return None

        # 현재 화면 상태 기준 대상 재조회
        target: QWidget | None = resolver()
        if target is None or not target.isVisible():
            return None

        return target

    def _register_targets(self) -> None:
        """대상 ID와 현재 위젯 resolver 연결"""

        # 메인 화면 대상
        self._resolvers.update(
            {
                "main.preview": lambda: self._current_tab().preview,
                "main.scroll_slots": lambda: self._current_tab().available_skills,
                "main.available_skills": lambda: self._current_tab().available_skills,
                "main.placed_skills": lambda: self._current_tab().placed_skills,
                "main.skill_keys": lambda: self._current_tab().placed_skills,
                "main.preset_tabs": lambda: self.master.main_ui.tab_widget.get_tab_bar(),
            }
        )

        # 사이드바 네비게이션 대상
        self._resolvers.update(
            {
                "sidebar.nav.general": lambda: self.master.sidebar.nav_button.buttons[
                    0
                ],
                "sidebar.nav.skill": lambda: self.master.sidebar.nav_button.buttons[1],
                "sidebar.nav.link": lambda: self.master.sidebar.nav_button.buttons[2],
                "sidebar.nav.calculator": lambda: self.master.sidebar.nav_button.buttons[
                    3
                ],
            }
        )

        # 일반 설정 대상
        self._resolvers.update(
            {
                "sidebar.general.server": lambda: self.master.sidebar.general_settings.server_job_setting,
                "sidebar.general.delay": lambda: self.master.sidebar.general_settings.delay_setting,
                "sidebar.general.cooltime": lambda: self.master.sidebar.general_settings.cooltime_setting,
                "sidebar.general.start_key": lambda: self.master.sidebar.general_settings.start_key_setting,
                "sidebar.general.swap_key": lambda: self.master.sidebar.general_settings.swap_key_setting,
                "sidebar.general.click": lambda: self.master.sidebar.general_settings.click_setting,
                "sidebar.general.key_hold": lambda: self.master.sidebar.general_settings.key_hold_setting,
                "sidebar.general.remember_state": lambda: self.master.sidebar.general_settings.remember_state_setting,
            }
        )

        # 스킬 사용설정 대상
        self._resolvers.update(
            {
                "sidebar.skill.selected_scroll": lambda: self.master.sidebar.skill_settings._selected_scroll_button,
                "sidebar.skill.cards": lambda: self.master.sidebar.skill_settings._cards_container,
                "sidebar.skill.usage": self._first_skill_usage_button,
                "sidebar.skill.sole": self._first_skill_sole_button,
                "sidebar.skill.priority": self._first_skill_priority_button,
                "sidebar.skill.custom_actions": lambda: self.master.sidebar.skill_settings._custom_actions_frame,
                "sidebar.skill.scroll_add": lambda: self.master.popup_manager.current_scroll_add_button(),
            }
        )

        # 연계스킬 대상
        self._resolvers.update(
            {
                "sidebar.link.create": lambda: self.master.sidebar.link_skill_settings.create_link_skill_btn,
                "sidebar.link.list": lambda: self.master.sidebar.link_skill_settings._list_container,
                "sidebar.link.editor.type": lambda: self.master.sidebar.link_skill_editor.type_setting,
                "sidebar.link.editor.key": lambda: self.master.sidebar.link_skill_editor.key_setting,
                "sidebar.link.editor.remember": lambda: self.master.sidebar.link_skill_editor.remember_state_setting,
                "sidebar.link.editor.skills": lambda: self.master.sidebar.link_skill_editor._skills_container,
                "sidebar.link.editor.save": lambda: self.master.sidebar.link_skill_editor.save_btn,
            }
        )

        # 계산기 대상
        self._resolvers.update(
            {
                "sim.nav.input": lambda: self.master.sim_ui.nav.buttons[0],
                "sim.nav.simulator": lambda: self.master.sim_ui.nav.buttons[1],
                "sim.nav.results": lambda: self.master.sim_ui.nav.buttons[2],
                "sim.nav.character": lambda: self.master.sim_ui.nav.buttons[3],
                "sim.input.metric": lambda: self.master.sim_ui.input_page.editor.metric_input,
                "sim.input.metric_manage": lambda: self.master.sim_ui.input_page.editor.metric_input,
                "sim.input.base_stats": lambda: self.master.sim_ui.input_page.editor.stats_inputs,
                "sim.input.distribution": lambda: self.master.sim_ui.input_page.editor.distribution_inputs,
                "sim.input.target_distribution": lambda: self.master.sim_ui.input_page.editor.target_distribution_inputs,
                "sim.input.danjeon": lambda: self.master.sim_ui.input_page.editor.danjeon_inputs,
                "sim.input.title": lambda: self.master.sim_ui.input_page.editor.title_inputs,
                "sim.input.talisman": lambda: self.master.sim_ui.input_page.editor.talisman_inputs,
                "sim.input.custom_delta": lambda: self.master.sim_ui.input_page.editor.custom_delta_inputs,
                "sim.graph.page": lambda: self.master.sim_ui.graph_page,
                "sim.results.page": lambda: self.master.sim_ui.results_page,
            }
        )

        # 캐릭터 대상
        self._resolvers.update(
            {
                "character.list": lambda: self.master.sim_ui.character_page._left_panel,
                "character.tab.title": lambda: self.master.sim_ui.character_page._tabs[
                    0
                ],
                "character.tab.equipment": lambda: self.master.sim_ui.character_page._tabs[
                    1
                ],
                "character.tab.distribution": lambda: self.master.sim_ui.character_page._tabs[
                    2
                ],
                "character.tab.display_stand": lambda: self.master.sim_ui.character_page._tabs[
                    3
                ],
                "character.tab.talisman": lambda: self.master.sim_ui.character_page._tabs[
                    4
                ],
                "character.tab.elixir": lambda: self.master.sim_ui.character_page._tabs[
                    5
                ],
                "character.tab.pill": lambda: self.master.sim_ui.character_page._tabs[
                    6
                ],
                "character.live_stats": lambda: self.master.sim_ui.character_page._right_panel,
                "character.use_calculator": lambda: self.master.sim_ui.character_page._use_calculator_btn,
            }
        )

    def _current_tab(self) -> QWidget:
        """현재 매크로 탭 위젯 반환"""

        return self.master.main_ui.tab_widget.get_current_tab()

    def _first_skill_usage_button(self) -> QWidget | None:
        """첫 스킬 카드 사용 여부 버튼 반환"""

        # 현재 표시 중인 첫 스킬 카드 옵션 버튼 조회
        cards = self.master.sidebar.skill_settings._skill_cards
        if not cards:
            return self.master.sidebar.skill_settings._cards_container

        return cards[0].usage_btn

    def _first_skill_sole_button(self) -> QWidget | None:
        """첫 스킬 카드 단독 사용 버튼 반환"""

        # 현재 표시 중인 첫 스킬 카드 옵션 버튼 조회
        cards = self.master.sidebar.skill_settings._skill_cards
        if not cards:
            return self.master.sidebar.skill_settings._cards_container

        return cards[0].sole_btn

    def _first_skill_priority_button(self) -> QWidget | None:
        """첫 스킬 카드 우선순위 버튼 반환"""

        # 현재 표시 중인 첫 스킬 카드 옵션 버튼 조회
        cards = self.master.sidebar.skill_settings._skill_cards
        if not cards:
            return self.master.sidebar.skill_settings._cards_container

        return cards[0].priority_btn


class GuideStartOverlay(QFrame):
    """첫 실행 가이드 시작 여부 오버레이"""

    def __init__(
        self,
        master: MainWindow,
        on_start: Callable[[], None],
        on_skip: Callable[[], None],
    ) -> None:
        super().__init__(master)

        self.master: MainWindow = master
        self.setObjectName("guideOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        # 선택 카드 구성
        self._card: QFrame = QFrame(self)
        self._card.setObjectName("guideOverlayCard")

        layout: QVBoxLayout = QVBoxLayout(self._card)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)

        title_label: QLabel = QLabel("시작 가이드를 진행할까요?", self._card)
        title_label.setObjectName("guideDialogTitle")
        title_label.setFont(CustomFont(14, bold=True))
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        body_label: QLabel = QLabel(
            "프로그램을 사용하는 가이드를 진행합니다. 나중에 언제든지 가이드를 다시 볼 수 있습니다.",
            self._card,
        )
        body_label.setObjectName("guideDialogBody")
        body_label.setFont(CustomFont(11))
        body_label.setWordWrap(True)
        layout.addWidget(body_label)

        button_layout: QHBoxLayout = QHBoxLayout()
        button_layout.addStretch()

        skip_button: QPushButton = QPushButton("스킵", self._card)
        skip_button.setObjectName("guideSecondaryButton")
        skip_button.clicked.connect(on_skip)
        button_layout.addWidget(skip_button)

        start_button: QPushButton = QPushButton("시작", self._card)
        start_button.setObjectName("guidePrimaryButton")
        start_button.clicked.connect(on_start)
        button_layout.addWidget(start_button)

        layout.addLayout(button_layout)

    def show_overlay(self) -> None:
        """시작 안내 오버레이 표시"""

        # 오버레이 전체 영역 동기화
        self.refresh_layout()
        self.raise_()
        self.show()

    def refresh_layout(self) -> None:
        """현재 창 크기 기준 오버레이 재배치"""

        self.setGeometry(self.master.rect())
        self._place_card()
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """오버레이 크기 변경 시 카드 위치 재계산"""

        self._place_card()
        return super().resizeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """반투명 배경 그리기"""

        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), _guide_overlay_color())
        super().paintEvent(event)

    def _place_card(self) -> None:
        """시작 안내 카드 중앙 배치"""

        card_width: int = min(420, max(320, self.width() - 40))
        self._card.setFixedWidth(card_width)
        self._card.adjustSize()
        card_height: int = self._card.sizeHint().height()
        x: int = max(20, (self.width() - card_width) // 2)
        y: int = max(20, (self.height() - card_height) // 2)
        self._card.setGeometry(x, y, card_width, card_height)


class GuideSelectionOverlay(QFrame):
    """가이드 선택 오버레이"""

    def __init__(
        self,
        master: MainWindow,
        definitions: tuple[GuideDefinition, ...],
        on_selected: Callable[[GuideDefinition], None],
        on_closed: Callable[[], None],
    ) -> None:
        super().__init__(master)

        self.master: MainWindow = master
        self._on_closed: Callable[[], None] = on_closed
        self.setObjectName("guideOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        # 선택 카드 구성
        self._card: QFrame = QFrame(self)
        self._card.setObjectName("guideSelectionCard")

        layout: QVBoxLayout = QVBoxLayout(self._card)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        title_label: QLabel = QLabel("가이드 선택", self._card)
        title_label.setObjectName("guideDialogTitle")
        title_label.setFont(CustomFont(14, bold=True))
        layout.addWidget(title_label)

        body_label: QLabel = QLabel("확인할 가이드를 선택하세요.", self._card)
        body_label.setObjectName("guideDialogBody")
        body_label.setFont(CustomFont(11))
        layout.addWidget(body_label)

        # 가이드 목록 버튼 구성
        for definition in definitions:
            button: QPushButton = QPushButton(definition.title, self._card)
            button.setObjectName(
                "guideRecommendedListButton"
                if definition.recommended
                else "guideListButton"
            )
            button.setFont(CustomFont(11))
            if definition.recommended:
                button.setIcon(_guide_recommended_icon())
                button.setIconSize(QSize(10, 10))
            button.clicked.connect(lambda _, item=definition: on_selected(item))
            layout.addWidget(button)

        close_button: QPushButton = QPushButton("닫기", self._card)
        close_button.setObjectName("guideSecondaryButton")
        close_button.clicked.connect(self.close_overlay)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

    def show_overlay(self) -> None:
        """가이드 선택 오버레이 표시"""

        # 오버레이 전체 영역 동기화
        self.refresh_layout()
        self.raise_()
        self.show()

    def refresh_layout(self) -> None:
        """현재 창 크기 기준 오버레이 재배치"""

        self.setGeometry(self.master.rect())
        self._place_card()
        self.update()

    def close_overlay(self) -> None:
        """가이드 선택 오버레이 닫기"""

        self.hide()
        self._on_closed()
        self.deleteLater()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """오버레이 크기 변경 시 카드 위치 재계산"""

        self._place_card()
        return super().resizeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """반투명 배경 그리기"""

        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), _guide_overlay_color())
        super().paintEvent(event)

    def _place_card(self) -> None:
        """가이드 선택 카드 중앙 배치"""

        card_width: int = min(460, max(320, self.width() - 40))
        self._card.setFixedWidth(card_width)
        self._card.adjustSize()
        card_height: int = self._card.sizeHint().height()
        x: int = max(20, (self.width() - card_width) // 2)
        y: int = max(20, (self.height() - card_height) // 2)
        self._card.setGeometry(x, y, card_width, card_height)


class GuideOverlay(QFrame):
    """가이드 단계 오버레이"""

    def __init__(self, master: MainWindow, manager: GuideManager) -> None:
        super().__init__(master)

        self.master: MainWindow = master
        self._manager: GuideManager = manager
        self._target_rect: QRect | None = None

        self.setObjectName("guideOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        # 설명 카드 구성
        self._card: QFrame = QFrame(self)
        self._card.setObjectName("guideOverlayCard")

        card_layout: QVBoxLayout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(18, 16, 18, 14)
        card_layout.setSpacing(10)

        self._title_label: QLabel = QLabel(self._card)
        self._title_label.setObjectName("guideOverlayTitle")
        self._title_label.setFont(CustomFont(13, bold=True))
        self._title_label.setWordWrap(True)
        card_layout.addWidget(self._title_label)

        self._body_label: QLabel = QLabel(self._card)
        self._body_label.setObjectName("guideOverlayBody")
        self._body_label.setFont(CustomFont(11))
        self._body_label.setWordWrap(True)
        card_layout.addWidget(self._body_label)

        button_layout: QHBoxLayout = QHBoxLayout()
        button_layout.setSpacing(8)

        self._previous_button: QPushButton = QPushButton("이전", self._card)
        self._previous_button.setObjectName("guideSecondaryButton")
        self._previous_button.clicked.connect(self._manager.previous_step)
        button_layout.addWidget(self._previous_button)

        button_layout.addStretch()

        self._exit_button: QPushButton = QPushButton("가이드 종료", self._card)
        self._exit_button.setObjectName("guideSecondaryButton")
        self._exit_button.clicked.connect(self._manager.finish_current_guide)
        button_layout.addWidget(self._exit_button)

        self._next_button: QPushButton = QPushButton("다음", self._card)
        self._next_button.setObjectName("guidePrimaryButton")
        self._next_button.clicked.connect(self._manager.next_step)
        button_layout.addWidget(self._next_button)

        card_layout.addLayout(button_layout)

    def show_step(
        self,
        definition: GuideDefinition,
        step: GuideStep,
        step_index: int,
        target: QWidget | None,
        error_message: str | None,
    ) -> None:
        """현재 가이드 단계 표시"""

        # 오버레이 전체 영역 동기화
        self.refresh_layout()
        self.raise_()
        self.show()

        # 설명 문구 구성
        total_count: int = len(definition.steps)
        self._title_label.setText(
            f"{definition.title} · {step_index + 1}/{total_count}\n{step.title}"
        )
        if error_message is None:
            self._body_label.setText(step.body)
        else:
            self._body_label.setText(f"{step.body}\n\n{error_message}")

        # 진행 버튼 상태 갱신
        self._previous_button.setEnabled(step_index > 0)
        self._next_button.setText(
            "선택 화면으로" if step_index == total_count - 1 else "다음"
        )

        # 대상 강조 위치 갱신
        if target is None:
            self._target_rect = None
        else:
            top_left: QPoint = target.mapTo(self.master, QPoint(0, 0))
            self._target_rect = QRect(top_left, target.size()).adjusted(-6, -6, 6, 6)

        self._place_card()
        self.update()

    def refresh_layout(self) -> None:
        """현재 창 크기 기준 오버레이 재배치"""

        self.setGeometry(self.master.rect())
        self._place_card()
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """오버레이 크기 변경 시 카드 위치 재계산"""

        self._place_card()
        return super().resizeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """반투명 배경과 대상 강조 테두리 그리기"""

        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        overlay_color: QColor = _guide_overlay_color()

        # 대상 없는 단계의 전체 배경 필터
        if self._target_rect is None:
            painter.fillRect(self.rect(), overlay_color)
            super().paintEvent(event)
            return

        # 강조 대상 영역을 제외한 배경 필터
        overlay_path: QPainterPath = QPainterPath()
        overlay_path.addRect(QRectF(self.rect()))
        overlay_path.addRoundedRect(QRectF(self._target_rect), 8, 8)
        overlay_path.setFillRule(Qt.FillRule.OddEvenFill)
        painter.fillPath(overlay_path, overlay_color)

        # 대상 강조 테두리 표시
        painter.setPen(QPen(_guide_highlight_color(), 3))
        painter.drawRoundedRect(self._target_rect, 8, 8)

        super().paintEvent(event)

    def _place_card(self) -> None:
        """대상 위치 기준 설명 카드 배치"""

        # 카드 기본 크기 계산
        card_width: int = min(420, max(320, self.width() - 40))
        self._card.setFixedWidth(card_width)
        self._card.adjustSize()
        card_height: int = self._card.sizeHint().height()

        # 대상이 있으면 대상과 겹치지 않는 후보 위치 선택
        if self._target_rect is not None:
            self._card.setGeometry(self._best_card_rect(card_width, card_height))
            return

        # 대상이 없으면 화면 중앙 배치
        x = max(20, (self.width() - card_width) // 2)
        y = max(20, (self.height() - card_height) // 2)
        self._card.setGeometry(x, y, card_width, card_height)

    def _best_card_rect(self, card_width: int, card_height: int) -> QRect:
        """강조 대상과 겹침이 가장 적은 카드 위치 계산"""

        # 화면 여백과 배치 한계 계산
        margin: int = 20
        target: QRect = self._target_rect if self._target_rect is not None else QRect()
        max_x: int = max(margin, self.width() - card_width - margin)
        max_y: int = max(margin, self.height() - card_height - margin)

        # 대상 주변 후보 위치 구성
        centered_x: int = target.center().x() - card_width // 2
        right_x: int = target.right() + 14
        left_x: int = target.left() - card_width - 14
        below_y: int = target.bottom() + 14
        above_y: int = target.top() - card_height - 14
        centered_y: int = target.center().y() - card_height // 2

        raw_candidates: tuple[tuple[int, int], ...] = (
            (right_x, centered_y),
            (left_x, centered_y),
            (centered_x, below_y),
            (centered_x, above_y),
            (margin, margin),
            (max_x, margin),
            (margin, max_y),
            (max_x, max_y),
            ((self.width() - card_width) // 2, (self.height() - card_height) // 2),
        )

        # 화면 안쪽으로 보정한 후보 사각형 생성
        candidates: list[QRect] = []
        for raw_x, raw_y in raw_candidates:
            x: int = min(max(margin, raw_x), max_x)
            y: int = min(max(margin, raw_y), max_y)
            candidate: QRect = QRect(x, y, card_width, card_height)
            if candidate not in candidates:
                candidates.append(candidate)

        # 대상과의 겹침 면적이 가장 작은 후보 선택
        best_rect: QRect = candidates[0]
        best_overlap: int = self._overlap_area(best_rect, target)
        for candidate in candidates[1:]:
            overlap: int = self._overlap_area(candidate, target)
            if overlap >= best_overlap:
                continue

            best_rect = candidate
            best_overlap = overlap

        return best_rect

    @staticmethod
    def _overlap_area(first: QRect, second: QRect) -> int:
        """두 사각형의 겹침 면적 계산"""

        intersection: QRect = first.intersected(second)
        if intersection.isNull():
            return 0

        return intersection.width() * intersection.height()


class GuideManager:
    """튜토리얼형 가이드 흐름 관리"""

    def __init__(self, master: MainWindow) -> None:
        self.master: MainWindow = master
        self._target_registry: GuideTargetRegistry = GuideTargetRegistry(master)
        self._definitions: tuple[GuideDefinition, ...] = self._build_definitions()
        self._selection_overlay: GuideSelectionOverlay | None = None
        self._start_overlay: GuideStartOverlay | None = None
        self._overlay: GuideOverlay | None = None
        self._current_definition: GuideDefinition | None = None
        self._current_step_index: int = 0
        self._opened_link_editor: bool = False
        self._opened_custom_scroll_popup: bool = False
        self._calculator_guide_session: CalculatorGuideSession | None = None
        self._calculator_results_requested: bool = False

    def show_start_prompt_if_needed(self) -> None:
        """첫 가이드 안내 필요 시 시작 여부 창 표시"""

        # 이미 처리한 사용자 자동 안내 생략
        if app_state.ui.guide_prompt_handled:
            return

        # 시작 여부 오버레이 구성
        self._start_overlay = GuideStartOverlay(
            self.master,
            self._handle_prompt_start,
            self._handle_prompt_skip,
        )
        self._apply_overlay_theme(self._start_overlay)
        self._start_overlay.show_overlay()

    def refresh_visible_overlays(self) -> None:
        """창 크기 변경 후 표시 중인 가이드 레이어 갱신"""

        # 시작 안내 오버레이 크기 동기화
        if self._start_overlay is not None and self._start_overlay.isVisible():
            self._start_overlay.refresh_layout()

        # 선택 오버레이 크기 동기화
        if self._selection_overlay is not None and self._selection_overlay.isVisible():
            self._selection_overlay.refresh_layout()

        # 진행 오버레이 대상 좌표 재조회
        if self._overlay is not None and self._overlay.isVisible():
            self._show_current_step()

    def open_selection(self) -> None:
        """가이드 선택 화면 열기"""

        # 기존 선택 오버레이 정리
        if self._selection_overlay is not None:
            self._selection_overlay.hide()
            self._selection_overlay.deleteLater()
            self._selection_overlay = None

        # 선택 오버레이 표시
        self._selection_overlay = GuideSelectionOverlay(
            self.master,
            self._definitions,
            self._start_guide,
            self._clear_selection_overlay,
        )
        self._apply_overlay_theme(self._selection_overlay)
        self._selection_overlay.show_overlay()

    def previous_step(self) -> None:
        """이전 가이드 단계로 이동"""

        # 첫 단계에서는 이전 이동 차단
        if self._current_step_index == 0:
            return

        self._current_step_index -= 1
        self._show_current_step()

    def next_step(self) -> None:
        """다음 가이드 단계로 이동"""

        # 마지막 단계에서는 선택 화면으로 복귀
        definition: GuideDefinition | None = self._current_definition
        if definition is None:
            return

        if self._current_step_index == len(definition.steps) - 1:
            self.finish_current_guide()
            return

        self._current_step_index += 1
        self._show_current_step()

    def finish_current_guide(self) -> None:
        """현재 가이드 종료 후 선택 화면 복귀"""

        # 임시 연계스킬 편집 화면 정리
        if self._opened_link_editor:
            self.master.sidebar.link_skill_editor.cancel()
            self._opened_link_editor = False

        # 임시 커스텀 무공비급 선택 팝업 정리
        if self._opened_custom_scroll_popup:
            self.master.popup_manager.close_popup()
            self._opened_custom_scroll_popup = False

        # 계산기 예시 입력 복원
        self._restore_calculator_guide_input()

        # 오버레이 정리
        if self._overlay is not None:
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None

        self._current_definition = None
        self._current_step_index = 0
        self.open_selection()

    def _handle_prompt_start(self) -> None:
        """첫 안내 시작 처리"""

        # 안내 처리 상태 저장
        app_state.ui.guide_prompt_handled = True
        save_data()

        # 시작 여부 오버레이 정리 후 선택 화면 표시
        if self._start_overlay is not None:
            self._start_overlay.hide()
            self._start_overlay.deleteLater()
            self._start_overlay = None

        self.open_selection()

    def _handle_prompt_skip(self) -> None:
        """첫 안내 스킵 처리"""

        # 안내 처리 상태 저장
        app_state.ui.guide_prompt_handled = True
        save_data()

        # 시작 여부 오버레이 닫기
        if self._start_overlay is not None:
            self._start_overlay.hide()
            self._start_overlay.deleteLater()
            self._start_overlay = None

    def _start_guide(self, definition: GuideDefinition) -> None:
        """선택한 가이드 실행"""

        # 실행 중 매크로와 편집 중 화면 차단
        if not self._can_start_guide():
            return

        # 선택 오버레이 정리
        if self._selection_overlay is not None:
            self._selection_overlay.hide()
            self._selection_overlay.deleteLater()
            self._selection_overlay = None

        # 가이드 상태 초기화
        self._current_definition = definition
        self._current_step_index = 0
        self._overlay = GuideOverlay(self.master, self)
        self._apply_overlay_theme(self._overlay)

        # 계산기 가이드 전용 임시 입력 세션 구성
        if definition.guide_id == "calculator":
            self._begin_calculator_guide_input()

        self._show_current_step()

    def _clear_selection_overlay(self) -> None:
        """가이드 선택 오버레이 참조 정리"""

        self._selection_overlay = None

    def _can_start_guide(self) -> bool:
        """가이드 시작 가능 여부 확인"""

        # 매크로 실행 중 설정 화면 이동 차단
        if app_state.macro.is_running:
            self._show_blocked_dialog("매크로 실행 중에는 가이드를 시작할 수 없습니다.")
            return False

        # 사용자가 편집 중인 연계스킬 보호
        if self.master.sidebar.page_navigator.currentIndex() == 3:
            self._show_blocked_dialog(
                "연계스킬 편집을 마친 뒤 가이드를 시작할 수 있습니다."
            )
            return False

        return True

    def _show_current_step(self) -> None:
        """현재 단계 진입 동작과 오버레이 표시"""

        definition: GuideDefinition | None = self._current_definition
        overlay: GuideOverlay | None = self._overlay
        if definition is None or overlay is None:
            return

        step: GuideStep = definition.steps[self._current_step_index]

        # 단계별 화면 진입 동작 실행
        if step.enter_action is not None:
            step.enter_action()

        QTimer.singleShot(0, lambda: self._render_step(definition, step, overlay))

    def _render_step(
        self,
        definition: GuideDefinition,
        step: GuideStep,
        overlay: GuideOverlay,
    ) -> None:
        """대상 조회 후 현재 단계 렌더링"""

        # 대상 없는 설명 단계 처리
        if step.target_id is None:
            overlay.show_step(
                definition,
                step,
                self._current_step_index,
                None,
                None,
            )
            return

        # 현재 화면 기준 대상 조회
        target: QWidget | None = self._target_registry.resolve(step.target_id)
        error_message: str | None = None
        if target is None:
            error_message = (
                "가이드 대상을 찾을 수 없습니다. 화면을 다시 열고 시도하세요."
            )
        else:
            self._ensure_target_visible(target)

        overlay.show_step(
            definition,
            step,
            self._current_step_index,
            target,
            error_message,
        )

    def _ensure_target_visible(self, target: QWidget) -> None:
        """대상 위젯이 보이도록 부모 스크롤 영역 이동"""

        # 상위 스크롤 영역 탐색
        parent: QWidget | None = target.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                parent.ensureWidgetVisible(target, 20, 20)
                return

            parent = parent.parentWidget()

    def _main_page(self) -> None:
        """메인 매크로 페이지 진입"""

        self.master.popup_manager.close_popup()
        self.master.change_layout(0)

    def _sidebar_page(self, index: int) -> None:
        """사이드바 페이지 진입"""

        self._main_page()
        self.master.sidebar.change_page(index)

    def _link_editor_page(self) -> None:
        """임시 연계스킬 편집 페이지 진입"""

        self._sidebar_page(2)
        if self.master.sidebar.page_navigator.currentIndex() == 3:
            return

        self.master.sidebar.link_skill_settings.create_new()
        self._opened_link_editor = True

    def _custom_scroll_add_button_page(self) -> None:
        """커스텀 무공비급 추가 버튼 표시"""

        # 이미 대상 팝업이 열린 상태면 현재 화면 유지
        add_button: QPushButton | None = (
            self.master.popup_manager.current_scroll_add_button()
        )
        if (
            self.master.page_navigator.currentIndex() == 0
            and self.master.sidebar.page_navigator.currentIndex() == 1
            and add_button is not None
        ):
            return

        # 무공비급 사용 설정 화면 진입
        self._sidebar_page(1)

        # 선택 무공비급 영역 기준 팝업 표시
        self.master.sidebar.skill_settings.on_scroll_select_clicked()
        self._opened_custom_scroll_popup = True

    def _close_link_editor_page(self) -> None:
        """임시 연계스킬 편집 페이지 취소 후 목록 진입"""

        if self._opened_link_editor:
            self.master.sidebar.link_skill_editor.cancel()
            self._opened_link_editor = False
            return

        self._sidebar_page(2)

    def _sim_input_page(self) -> None:
        """계산기 정보 입력 페이지 진입"""

        # 계산기 가이드 예시 입력 보장
        self._ensure_calculator_guide_input()

        self.master.popup_manager.close_popup()
        self.master.change_layout(1)
        self.master.sim_ui.change_layout(0)

    def _sim_graph_page(self) -> None:
        """계산기 시뮬레이터 페이지 진입"""

        # 계산기 가이드 예시 입력 보장
        self._ensure_calculator_guide_input()

        self.master.popup_manager.close_popup()
        self.master.change_layout(1)
        if self.master.sim_ui.input_page.editor.has_valid_navigation_inputs():
            self.master.sim_ui.change_layout(1)

    def _sim_results_page(self) -> None:
        """계산기 결과 페이지 진입"""

        # 계산기 가이드 예시 입력 보장
        self._ensure_calculator_guide_input()

        self.master.popup_manager.close_popup()

        # 결과 계산 중복 요청 방지
        if self._calculator_results_requested:
            self.master.page_navigator.setCurrentIndex(1)
            return

        # 계산기 화면 진입 후 예시 결과 계산 시작
        self.master.change_layout(1)
        self._calculator_results_requested = (
            self.master.sim_ui.start_results_calculation_without_confirmation()
        )

    def _sim_character_page(
        self,
        tab_index: int,
        show_character_list: bool,
        show_live_stats: bool,
    ) -> None:
        """캐릭터 페이지 진입"""

        self.master.popup_manager.close_popup()
        self.master.change_layout(1)
        self.master.sim_ui.change_layout(3)

        character_page: CharacterPage = self.master.sim_ui.character_page
        character_page._go(tab_index)

        if show_character_list:
            character_page.show_character_list_panel()

        if show_live_stats:
            character_page.show_live_stats_panel()

        self.master.sim_ui.adjust_main_frame_height()

    def _begin_calculator_guide_input(self) -> None:
        """계산기 가이드 예시 입력 세션 시작"""

        # 현재 프리셋 기준 세션 재사용
        current_preset: MacroPreset = app_state.macro.current_preset
        current_session: CalculatorGuideSession | None = (
            self._calculator_guide_session
        )
        if current_session is not None and current_session.preset is current_preset:
            return

        # 다른 프리셋 세션 잔여 상태 복원
        if current_session is not None:
            self._restore_calculator_guide_input()

        # 현재 사용자 입력과 무공비급 레벨 메모리 백업
        self._calculator_guide_session = CalculatorGuideSession(
            preset=current_preset,
            calculator_input=copy.deepcopy(current_preset.info.calculator),
            scroll_levels=current_preset.info.scroll_levels.copy(),
        )

        # 예시 입력 주입 및 저장 차단
        current_preset.info.calculator = self._build_calculator_guide_input()
        self.master.sim_ui.input_page.editor.set_persist_enabled(False)
        self._calculator_results_requested = False

    def _ensure_calculator_guide_input(self) -> None:
        """계산기 가이드 단계에서 예시 입력 세션 유지"""

        # 계산기 가이드 외 단계에서는 입력 주입 생략
        current_definition: GuideDefinition | None = self._current_definition
        if current_definition is None or current_definition.guide_id != "calculator":
            return

        self._begin_calculator_guide_input()

    def _restore_calculator_guide_input(self) -> None:
        """계산기 가이드 예시 입력 세션 복원"""

        # 세션이 없으면 복원 대상 없음
        current_session: CalculatorGuideSession | None = self._calculator_guide_session
        if current_session is None:
            return

        # 진행 중 계산 중단 후 원래 입력 복구
        self.master.sim_ui.cancel_results_calculation_for_shutdown()
        current_session.preset.info.calculator = current_session.calculator_input
        current_session.preset.info.scroll_levels = current_session.scroll_levels
        self.master.sim_ui.input_page.editor.set_persist_enabled(True)

        # 현재 화면이 복원 대상 프리셋일 때만 입력 UI 재동기화
        if app_state.macro.current_preset is current_session.preset:
            self.master.sim_ui.input_page.editor.load_from_preset_state()

        # 예시 세션 상태 초기화
        self._calculator_guide_session = None
        self._calculator_results_requested = False

    def _build_calculator_guide_input(self) -> CalculatorPresetInput:
        """계산기 가이드용 예시 입력 구성"""

        # 기본 계산기 입력 구조 생성
        calculator_input: CalculatorPresetInput = CalculatorPresetInput.create_default()
        base_stats: BaseStats = BaseStats.create_default()

        # 그래프와 결과 계산이 가능한 최소 공격 관련 스탯 구성
        base_stats.values[StatKey.ATTACK.value] = 820.0
        base_stats.values[StatKey.ATTACK_PERCENT.value] = 45.0
        base_stats.values[StatKey.HP.value] = 2400.0
        base_stats.values[StatKey.HP_PERCENT.value] = 20.0
        base_stats.values[StatKey.STR.value] = 120.0
        base_stats.values[StatKey.STR_PERCENT.value] = 15.0
        base_stats.values[StatKey.DEXTERITY.value] = 110.0
        base_stats.values[StatKey.DEXTERITY_PERCENT.value] = 12.0
        base_stats.values[StatKey.VITALITY.value] = 105.0
        base_stats.values[StatKey.VITALITY_PERCENT.value] = 10.0
        base_stats.values[StatKey.LUCK.value] = 95.0
        base_stats.values[StatKey.LUCK_PERCENT.value] = 8.0
        base_stats.values[StatKey.SKILL_DAMAGE_PERCENT.value] = 32.0
        base_stats.values[StatKey.FINAL_ATTACK_PERCENT.value] = 18.0
        base_stats.values[StatKey.CRIT_RATE_PERCENT.value] = 22.0
        base_stats.values[StatKey.CRIT_DAMAGE_PERCENT.value] = 130.0
        base_stats.values[StatKey.BOSS_ATTACK_PERCENT.value] = 80.0
        base_stats.values[StatKey.RESIST_PERCENT.value] = 8.0
        base_stats.values[StatKey.SKILL_SPEED_PERCENT.value] = 15.0

        # 계산기 예시의 기본 기준값 지정
        calculator_input.base_stats = base_stats
        calculator_input.level = 35
        calculator_input.realm_tier = RealmTier.THIRD_RATE
        calculator_input.selected_formula_id = PowerMetric.BOSS_DAMAGE.value

        # 결과 계산 부담을 줄이는 잠금된 분배/단전 예시 구성
        calculator_input.distribution = DistributionState(
            strength=10,
            dexterity=8,
            vitality=7,
            luck=6,
            is_locked=True,
            use_reset=False,
        )
        calculator_input.target_distribution = TargetDistributionState(
            strength=12,
            dexterity=9,
            vitality=8,
            luck=7,
            is_minimum=False,
        )
        calculator_input.danjeon = DanjeonState(
            upper=2,
            middle=3,
            lower=1,
            is_locked=True,
            use_reset=False,
        )

        # 선택형 장비 데이터 없는 기본 예시 상태 구성
        calculator_input.owned_titles = []
        calculator_input.owned_talismans = []
        calculator_input.equipped_state = EquippedState()
        calculator_input.custom_stat_changes = {
            stat_key.value: 0.0 for stat_key in STAT_SPECS.keys()
        }
        calculator_input.custom_stat_changes[StatKey.ATTACK.value] = 20.0
        return calculator_input

    def cleanup_for_shutdown(self) -> None:
        """프로그램 종료 전 가이드 임시 상태 정리"""

        # 계산기 예시 입력 복원
        self._restore_calculator_guide_input()

    def _show_blocked_dialog(self, message: str) -> None:
        """가이드 시작 불가 안내 표시"""

        dialog: QDialog = QDialog(self.master)
        dialog.setObjectName("guideDialog")
        dialog.setWindowTitle("가이드 실행 불가")
        dialog.setModal(True)
        dialog.setFixedWidth(380)

        layout: QVBoxLayout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        title_label: QLabel = QLabel("가이드를 시작할 수 없습니다.", dialog)
        title_label.setObjectName("guideDialogTitle")
        title_label.setFont(CustomFont(13, bold=True))
        layout.addWidget(title_label)

        body_label: QLabel = QLabel(message, dialog)
        body_label.setObjectName("guideDialogBody")
        body_label.setFont(CustomFont(11))
        body_label.setWordWrap(True)
        layout.addWidget(body_label)

        close_button: QPushButton = QPushButton("확인", dialog)
        close_button.setObjectName("guidePrimaryButton")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

        self._apply_dialog_theme(dialog)
        dialog.exec()

    def _apply_dialog_theme(self, dialog: QDialog) -> None:
        """현재 프로그램 테마를 가이드 다이얼로그에 적용"""

        dialog.setStyleSheet(self.master.styleSheet())

    def _apply_overlay_theme(self, overlay: QWidget) -> None:
        """현재 프로그램 테마를 가이드 오버레이에 적용"""

        overlay.setStyleSheet(self.master.styleSheet())

    def _build_definitions(self) -> tuple[GuideDefinition, ...]:
        """1차 제공 가이드 정의 구성"""

        return (
            GuideDefinition(
                guide_id="macro",
                title="매크로 사용",
                recommended=True,
                steps=(
                    GuideStep(
                        "현재 화면 구조 확인",
                        "현재 화면은 프리셋 단위로 설정을 관리합니다. 프리셋마다 서버, 무공비급, 스킬 배치, 계산기 입력이 따로 저장됩니다.",
                        "main.preset_tabs",
                        lambda: self._sidebar_page(0),
                    ),
                    GuideStep(
                        "서버와 직업 확인",
                        "먼저 현재 프리셋에서 사용할 서버와 직업을 확인합니다. 이 값이 바뀌면 선택 가능한 무공비급과 스킬 목록도 바뀝니다.",
                        "sidebar.general.server",
                        lambda: self._sidebar_page(0),
                    ),
                    GuideStep(
                        "딜레이 확인",
                        "딜레이는 입력 간격입니다. 너무 낮으면 스킬이 누락될 수 있고, 너무 높으면 반응이 느려집니다.",
                        "sidebar.general.delay",
                        lambda: self._sidebar_page(0),
                    ),
                    GuideStep(
                        "스킬속도 확인",
                        "캐릭터의 스킬속도 값을 입력하면 쿨타임 계산에 반영됩니다.",
                        "sidebar.general.cooltime",
                        lambda: self._sidebar_page(0),
                    ),
                    GuideStep(
                        "시작키 확인",
                        "시작키는 매크로를 시작하고 중지하는 키입니다. 다른 기능에서 이미 쓰는 키와 겹치지 않는지 확인합니다.",
                        "sidebar.general.start_key",
                        lambda: self._sidebar_page(0),
                    ),
                    GuideStep(
                        "스왑 키 확인",
                        "스왑 키는 1줄과 2줄 스킬을 오갈 때 사용됩니다. 실제 게임 키 설정과 맞아야 합니다.",
                        "sidebar.general.swap_key",
                        lambda: self._sidebar_page(0),
                    ),
                    GuideStep(
                        "마우스 클릭 설정 확인",
                        "일반 공격 입력을 함께 사용할지 정합니다. 스킬만 사용할 때는 끄고, 평타를 섞어야 하면 켭니다.",
                        "sidebar.general.click",
                        lambda: self._sidebar_page(0),
                    ),
                    GuideStep(
                        "무공비급 슬롯 확인",
                        "상단 영역은 장착한 무공비급과 해당 무공비급이 제공하는 스킬을 보여줍니다.",
                        "main.scroll_slots",
                        self._main_page,
                    ),
                    GuideStep(
                        "무공비급 선택 방법",
                        "빈 무공비급 슬롯을 누르면 선택 팝업이 열립니다. 원하는 무공비급을 선택하면 슬롯에 장착됩니다.",
                        "main.scroll_slots",
                        self._main_page,
                    ),
                    GuideStep(
                        "사용 가능 스킬 확인",
                        "무공비급을 장착하면 아래에 사용 가능한 스킬이 표시됩니다. 이 영역의 스킬은 아직 실제 사용 순서에 들어간 것이 아닙니다.",
                        "main.available_skills",
                        self._main_page,
                    ),
                    GuideStep(
                        "배치 슬롯 선택",
                        "하단 영역은 실제 매크로가 사용할 스킬 배치입니다. 먼저 넣을 위치를 선택한 뒤 상단의 스킬을 고릅니다.",
                        "main.placed_skills",
                        self._main_page,
                    ),
                    GuideStep(
                        "스킬 배치 흐름",
                        "하단 슬롯을 선택한 상태에서 상단 스킬을 누르면 해당 슬롯에 스킬이 배치됩니다.",
                        "main.available_skills",
                        self._main_page,
                    ),
                    GuideStep(
                        "스킬 제거 방법",
                        "이미 배치된 스킬 슬롯을 다시 선택하면 해당 스킬을 제거할 수 있습니다.",
                        "main.placed_skills",
                        self._main_page,
                    ),
                    GuideStep(
                        "입력키 확인",
                        "하단의 키 버튼은 각 줄에서 실제로 누를 키입니다. 게임 안의 스킬 위치와 맞게 설정해야 합니다.",
                        "main.skill_keys",
                        self._main_page,
                    ),
                    GuideStep(
                        "실행 순서 미리보기",
                        "미리보기는 현재 설정 기준으로 다음에 사용할 스킬 순서를 보여줍니다. 설정을 바꾼 뒤 이 영역으로 흐름을 확인합니다.",
                        "main.preview",
                        self._main_page,
                    ),
                    GuideStep(
                        "마무리",
                        "기본 설정, 무공비급 장착, 스킬 배치, 입력키가 맞으면 시작키로 매크로를 실행할 준비가 끝납니다.",
                        "main.preview",
                        self._main_page,
                    ),
                ),
            ),
            GuideDefinition(
                guide_id="custom_scroll",
                title="커스텀 무공비급 추가",
                steps=(
                    GuideStep(
                        "커스텀 무공비급 진입 위치",
                        "커스텀 무공비급은 스킬 사용설정의 선택 무공비급 목록에서 추가할 수 있습니다.",
                        "sidebar.skill.selected_scroll",
                        lambda: self._sidebar_page(1),
                    ),
                    GuideStep(
                        "무공비급 선택 팝업 열기",
                        "선택 무공비급 영역을 누르면 현재 서버에서 사용할 수 있는 무공비급 목록이 열립니다.",
                        "sidebar.skill.selected_scroll",
                        lambda: self._sidebar_page(1),
                    ),
                    GuideStep(
                        "새 스킬 추가 위치",
                        "목록 아래의 + 새 스킬 추가를 누르면 커스텀 무공비급과 스킬을 입력하는 창이 열립니다. 가이드에서는 버튼 위치만 확인합니다.",
                        "sidebar.skill.scroll_add",
                        self._custom_scroll_add_button_page,
                    ),
                    GuideStep(
                        "입력 항목 확인",
                        "추가 창에서는 무공비급 이름, 스킬 이름, 레벨별 데미지, 쿨타임을 입력합니다. 이 버튼을 직접 눌렀을 때만 창이 열립니다.",
                        "sidebar.skill.scroll_add",
                        self._custom_scroll_add_button_page,
                    ),
                    GuideStep(
                        "마무리",
                        "추가된 무공비급은 기존 무공비급처럼 선택하고 배치할 수 있습니다.",
                        "sidebar.skill.selected_scroll",
                        lambda: self._sidebar_page(1),
                    ),
                ),
            ),
            GuideDefinition(
                guide_id="link",
                title="연계스킬 만들기",
                steps=(
                    GuideStep(
                        "연계설정 위치 확인",
                        "연계설정은 여러 스킬을 하나의 묶음으로 사용하는 기능입니다.",
                        "sidebar.nav.link",
                        lambda: self._sidebar_page(2),
                    ),
                    GuideStep(
                        "연계스킬 목록 확인",
                        "만들어둔 연계스킬은 이 목록에 표시됩니다. 각 항목에서 포함된 스킬과 사용 방식이 요약됩니다.",
                        "sidebar.link.list",
                        lambda: self._sidebar_page(2),
                    ),
                    GuideStep(
                        "새 연계스킬 만들기",
                        "새 연계스킬을 만들려면 이 버튼을 누릅니다. 버튼을 누르면 편집 화면으로 이동합니다.",
                        "sidebar.link.create",
                        lambda: self._sidebar_page(2),
                    ),
                    GuideStep(
                        "자동 사용과 수동 사용",
                        "자동 사용은 조건이 맞으면 매크로가 연계스킬을 사용합니다. 수동 사용은 지정한 시작키 입력을 기준으로 동작합니다.",
                        "sidebar.link.editor.type",
                        self._link_editor_page,
                    ),
                    GuideStep(
                        "시작키 설정",
                        "수동 연계스킬은 시작키가 중요합니다. 이미 다른 기능에서 쓰는 키와 겹치면 정상적으로 입력하기 어렵습니다.",
                        "sidebar.link.editor.key",
                        self._link_editor_page,
                    ),
                    GuideStep(
                        "쿨타임 동기화",
                        "연계스킬을 직접 실행할 때 쿨타임 준비 상태를 이어갈지 정하는 설정입니다.",
                        "sidebar.link.editor.remember",
                        self._link_editor_page,
                    ),
                    GuideStep(
                        "포함할 스킬 선택",
                        "연계스킬에 들어갈 스킬을 선택합니다. 현재 프리셋에 장착된 스킬만 안정적으로 사용할 수 있습니다.",
                        "sidebar.link.editor.skills",
                        self._link_editor_page,
                    ),
                    GuideStep(
                        "저장 위치 확인",
                        "저장 버튼은 연계스킬을 실제 목록에 반영하는 위치입니다. 1차 가이드에서는 버튼 위치만 안내하고 저장은 누르지 않습니다.",
                        "sidebar.link.editor.save",
                        self._link_editor_page,
                    ),
                    GuideStep(
                        "목록으로 돌아가기",
                        "가이드를 종료하면 임시 편집 화면을 취소하고 기존 연계스킬 목록으로 돌아갑니다.",
                        "sidebar.link.list",
                        self._close_link_editor_page,
                    ),
                    GuideStep(
                        "마무리",
                        "연계스킬은 일반 스킬 배치와 함께 실행 흐름에 영향을 줍니다. 설정 위치를 확인한 뒤 미리보기와 실제 실행 흐름의 관계를 이해합니다.",
                        "main.preview",
                        self._main_page,
                    ),
                ),
            ),
            GuideDefinition(
                guide_id="calculator",
                title="계산기",
                recommended=True,
                steps=(
                    GuideStep(
                        "계산기 화면 진입",
                        "계산기는 캐릭터 정보와 스킬 정보를 기준으로 시뮬레이션과 스탯 효율을 확인하는 화면입니다.",
                        "sim.nav.input",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "예시 입력 적용",
                        "가이드 중에는 예시 입력을 임시로 보여줍니다. 가이드를 종료하면 기존 계산기 입력으로 돌아갑니다.",
                        "sim.input.base_stats",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "전투력 공식 선택",
                        "현재 전투력을 계산할 기준 공식을 선택합니다. 기본 공식과 사용자 정의 공식이 함께 표시됩니다.",
                        "sim.input.metric",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "전투력 공식 관리",
                        "새 전투력 공식을 추가하거나 기존 공식을 관리할 수 있습니다. 공식이 여러 서버나 세팅 기준을 다룰 때 유용합니다.",
                        "sim.input.metric_manage",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "기본 스탯 입력",
                        "캐릭터의 전체 스탯을 입력합니다. 예시 입력에서는 결과를 볼 수 있도록 공격 관련 값이 채워져 있습니다.",
                        "sim.input.base_stats",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "현재 스탯 분배",
                        "현재 분배된 스탯을 입력합니다. 잠금과 초기화 옵션은 계산에서 조정 가능한 범위를 정합니다.",
                        "sim.input.distribution",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "목표 분배 미리보기",
                        "목표 분배는 현재 분배와 비교해 전투력 변화량을 확인하는 데 사용됩니다.",
                        "sim.input.target_distribution",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "단전 입력",
                        "상단전, 중단전, 하단전 값을 입력합니다. 단전도 잠금과 초기화 조건에 따라 최적화 대상이 달라집니다.",
                        "sim.input.danjeon",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "칭호 입력",
                        "보유 칭호를 추가하고 장착할 칭호를 선택합니다. 칭호별 스탯은 계산 결과에 반영됩니다.",
                        "sim.input.title",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "부적 입력",
                        "보유 부적과 장착 슬롯을 설정합니다. 부적 등급과 레벨에 따라 적용 스탯이 달라집니다.",
                        "sim.input.talisman",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "사용자 지정 변화량",
                        "특정 스탯이 바뀌었을 때 전투력이 얼마나 변하는지 따로 확인할 수 있습니다.",
                        "sim.input.custom_delta",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "시뮬레이터 탭",
                        "시뮬레이터는 현재 매크로 설정을 기준으로 전투 흐름과 스킬 기여도를 그래프로 보여줍니다.",
                        "sim.nav.simulator",
                        self._sim_input_page,
                    ),
                    GuideStep(
                        "시뮬레이터 결과",
                        "결과에는 DPM 분포, 스킬 비율, DPS 흐름, 총 피해량, 스킬 기여도 그래프가 포함됩니다.",
                        "sim.graph.page",
                        self._sim_graph_page,
                    ),
                    GuideStep(
                        "스탯 계산기 실행",
                        "예시 입력으로 스탯 계산기 결과를 불러옵니다. 계산이 진행 중이면 잠시 기다린 뒤 결과가 표시됩니다.",
                        "sim.nav.results",
                        self._sim_results_page,
                    ),
                    GuideStep(
                        "결과 화면 확인",
                        "결과 화면에서는 현재 전투력, 스탯 효율, 성장 효율, 최적화 결과를 함께 확인합니다.",
                        "sim.results.page",
                        self._sim_results_page,
                    ),
                    GuideStep(
                        "현재 전투력",
                        "선택한 전투력 공식 기준으로 현재 입력값을 계산한 결과입니다. 어떤 공식으로 나온 값인지 함께 확인합니다.",
                        "sim.results.page",
                        self._sim_results_page,
                    ),
                    GuideStep(
                        "스탯 효율",
                        "힘, 민첩, 생명력, 행운 같은 기본 스탯을 1 올렸을 때 전투력이 얼마나 변하는지 비교합니다.",
                        "sim.results.page",
                        self._sim_results_page,
                    ),
                    GuideStep(
                        "최적화 결과",
                        "현재 입력값, 잠금 조건, 보유 칭호, 보유 부적, 스탯 분배, 단전 조건을 기준으로 가장 좋은 조합을 계산합니다.",
                        "sim.results.page",
                        self._sim_results_page,
                    ),
                    GuideStep(
                        "마무리",
                        "가이드를 종료하면 예시 입력은 사라지고 기존 계산기 입력으로 돌아갑니다.",
                        "sim.results.page",
                        self._sim_results_page,
                    ),
                ),
            ),
            GuideDefinition(
                guide_id="character",
                title="캐릭터 시스템",
                recommended=True,
                steps=(
                    GuideStep(
                        "캐릭터 화면 진입",
                        "캐릭터는 장비와 성장 정보를 캐릭터 단위로 저장하고 전체 스탯으로 합산하는 화면입니다.",
                        "sim.nav.character",
                        lambda: self._sim_character_page(0, False, False),
                    ),
                    GuideStep(
                        "캐릭터 목록",
                        "왼쪽 목록에서 캐릭터를 고릅니다. 추가, 삭제, 복사, 붙여넣기로 여러 캐릭터나 세팅을 나눠 관리할 수 있습니다.",
                        "character.list",
                        lambda: self._sim_character_page(0, True, False),
                    ),
                    GuideStep(
                        "기본정보 탭",
                        "기본정보에서는 캐릭터 이름, 레벨, 경지, VIP, 칭호를 입력합니다.",
                        "character.tab.title",
                        lambda: self._sim_character_page(0, True, False),
                    ),
                    GuideStep(
                        "장비 탭",
                        "장비에서는 장착 장비와 보유 장비를 관리합니다.",
                        "character.tab.equipment",
                        lambda: self._sim_character_page(1, True, False),
                    ),
                    GuideStep(
                        "스탯·단전 분배 탭",
                        "스탯·단전 분배에서는 현재 레벨과 경지 기준으로 분배값을 입력합니다. 자동 최적화로 현재 기준의 추천 분배도 확인할 수 있습니다.",
                        "character.tab.distribution",
                        lambda: self._sim_character_page(2, True, False),
                    ),
                    GuideStep(
                        "진열대 탭",
                        "진열대에서는 진열대에 올린 항목의 스탯을 입력합니다.",
                        "character.tab.display_stand",
                        lambda: self._sim_character_page(3, True, False),
                    ),
                    GuideStep(
                        "부적 탭",
                        "부적에서는 보유 부적과 장착 부적을 관리합니다.",
                        "character.tab.talisman",
                        lambda: self._sim_character_page(4, True, False),
                    ),
                    GuideStep(
                        "영단 탭",
                        "영단에서는 영단으로 얻은 누적 효과를 입력합니다.",
                        "character.tab.elixir",
                        lambda: self._sim_character_page(5, True, False),
                    ),
                    GuideStep(
                        "환 탭",
                        "환에서는 보유한 환 효과를 입력합니다.",
                        "character.tab.pill",
                        lambda: self._sim_character_page(6, True, False),
                    ),
                    GuideStep(
                        "실시간 전체 스탯",
                        "오른쪽 전체 스탯은 입력이 바뀔 때마다 즉시 갱신됩니다. 현재 캐릭터의 전투력과 최종 스탯을 여기서 확인합니다.",
                        "character.live_stats",
                        lambda: self._sim_character_page(0, True, True),
                    ),
                    GuideStep(
                        "계산기에 사용",
                        "계산기에 사용을 누르면 선택한 캐릭터의 현재 스탯을 계산기 입력에 적용합니다.",
                        "character.use_calculator",
                        lambda: self._sim_character_page(0, True, True),
                    ),
                    GuideStep(
                        "마무리",
                        "캐릭터 정보를 먼저 관리해 두면 같은 캐릭터를 여러 계산에 다시 사용할 수 있습니다. 입력값을 바꾼 뒤 전체 스탯을 확인하고 필요할 때 계산기에 적용합니다.",
                        "character.use_calculator",
                        lambda: self._sim_character_page(0, True, True),
                    ),
                ),
            ),
            GuideDefinition(
                guide_id="skill_settings",
                title="스킬 사용 설정",
                steps=(
                    GuideStep(
                        "스킬 사용설정 위치",
                        "스킬 사용설정은 장착한 무공비급의 스킬별 동작 방식을 정하는 곳입니다.",
                        "sidebar.nav.skill",
                        lambda: self._sidebar_page(1),
                    ),
                    GuideStep(
                        "설정할 무공비급 선택",
                        "현재 선택한 무공비급의 스킬만 아래 카드에 표시됩니다. 다른 무공비급을 설정하려면 이 영역에서 선택합니다.",
                        "sidebar.skill.selected_scroll",
                        lambda: self._sidebar_page(1),
                    ),
                    GuideStep(
                        "스킬 카드 목록",
                        "각 카드 하나가 스킬 하나의 설정입니다. 스킬 이름과 아이콘, 사용 옵션이 함께 표시됩니다.",
                        "sidebar.skill.cards",
                        lambda: self._sidebar_page(1),
                    ),
                    GuideStep(
                        "사용 여부",
                        "사용 여부를 끄면 매크로가 해당 스킬을 자동으로 사용하지 않습니다.",
                        "sidebar.skill.usage",
                        lambda: self._sidebar_page(1),
                    ),
                    GuideStep(
                        "단독 사용",
                        "단독 사용은 자동 연계스킬에 포함된 스킬이 다른 스킬을 기다리지 않고 이 스킬을 우선적으로 사용할지 정하는 설정입니다.",
                        "sidebar.skill.sole",
                        lambda: self._sidebar_page(1),
                    ),
                    GuideStep(
                        "우선순위",
                        "여러 스킬이 동시에 준비되면 우선순위 번호가 낮은 스킬을 먼저 사용합니다.",
                        "sidebar.skill.priority",
                        lambda: self._sidebar_page(1),
                    ),
                    GuideStep(
                        "마무리",
                        "사용 여부, 단독 사용, 우선순위를 바꾼 뒤에는 미리보기로 다음 사용 순서를 확인합니다.",
                        "main.preview",
                        self._main_page,
                    ),
                ),
            ),
        )
