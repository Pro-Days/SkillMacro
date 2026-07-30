from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPaintEvent,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.config import config
from app.scripts.custom_classes import CustomFont
from app.scripts.data_manager import mark_current_app_version_seen, save_data
from app.scripts.registry.resource_registry import (
    get_theme_image_path,
    resource_registry,
)
from app.scripts.registry.server_registry import ServerSpec
from app.scripts.registry.skill_registry import ScrollDef, SkillDef
from app.scripts.skill_migration import (
    MigrationPair,
    apply_skill_migration,
    get_builtin_scroll_defs,
    get_custom_scroll_defs,
    has_custom_scrolls,
)
from app.scripts.ui.themes import theme_manager

if TYPE_CHECKING:
    from app.scripts.ui.main_window import MainWindow
    from app.scripts.ui.popup import HoverCardData


# 목록 아이콘 표시 크기
_LIST_ICON_SIZE: int = 48

# 선택 상세 커스텀/기본 구분 강조 색상
_CUSTOM_ACCENT_COLOR: str = "#E08A2B"
_BUILTIN_ACCENT_COLOR: str = "#4A90D9"


def _overlay_color() -> QColor:
    """현재 테마 기준 오버레이 배경 필터 색상"""

    return QColor(10, 10, 18, 170) if theme_manager.is_dark else QColor(15, 23, 42, 120)


def _format_number(value: float) -> str:
    """소수점을 제거한 숫자 표기"""

    return f"{value:g}"


def _scroll_icon(scroll_id: str) -> QIcon:
    """무공비급 아이콘 반환"""

    return QIcon(resource_registry.get_scroll_pixmap(scroll_id))


def _resolved_damage(skill_def: SkillDef, level: int) -> float:
    """요청 레벨 기준 데미지 반환"""

    levels: dict[int, float] = skill_def.levels
    if level in levels:
        return levels[level]

    # 보유한 레벨 중 요청 레벨 이하의 최고 레벨, 없으면 최저 레벨 사용
    available: list[int] = sorted(levels)
    below: list[int] = [value for value in available if value <= level]
    chosen: int = below[-1] if below else available[0]
    return levels[chosen]


def _scroll_detail_html(
    server_spec: ServerSpec,
    scroll_def: ScrollDef,
    level: int,
    accent_color: str,
    accent_label: str,
    is_dark: bool,
) -> str:
    """무공비급 이름과 보유 스킬 상세 정보를 리치 텍스트로 구성"""

    primary: str = "#E8E8F0" if is_dark else "#222222"
    secondary: str = "#9AA4B2" if is_dark else "#6B7280"

    rows: list[str] = [
        f"<span style='color:{accent_color};font-weight:bold;'>{accent_label}</span>"
        f"&nbsp;&nbsp;"
        f"<span style='color:{primary};font-weight:bold;'>{scroll_def.name}</span>"
        f"&nbsp;&nbsp;<span style='color:{secondary};'>Lv {level}</span>"
    ]

    for skill_id in scroll_def.skills:
        skill_def: SkillDef = server_spec.skill_registry.get(skill_id)
        damage: float = _resolved_damage(skill_def, level)

        rows.append(
            f"<span style='color:{primary};'>{skill_def.name}</span>"
            f"&nbsp;&nbsp;<span style='color:{secondary};'>"
            f"쿨 {_format_number(skill_def.cooltime)}초"
            f"&nbsp;·&nbsp;타겟 {skill_def.target_count}"
            f"&nbsp;·&nbsp;데미지 {_format_number(damage)}</span>"
        )

    return "<br>".join(rows)


class SkillMigrationOverlay(QFrame):
    """스킬 마이그레이션 선택 오버레이"""

    def __init__(
        self,
        master: MainWindow,
        server_spec: ServerSpec,
        on_apply: Callable[[list[MigrationPair]], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)

        self.master: MainWindow = master
        self._server_spec: ServerSpec = server_spec
        self._on_apply: Callable[[list[MigrationPair]], None] = on_apply
        self._on_close: Callable[[], None] = on_close

        self._custom_scrolls: list[ScrollDef] = get_custom_scroll_defs(server_spec)
        self._builtin_scrolls: list[ScrollDef] = get_builtin_scroll_defs(server_spec)

        self._selected_custom_id: str | None = None
        self._selected_builtin_id: str | None = None
        self._pairs: list[MigrationPair] = []

        self._custom_buttons: dict[str, QPushButton] = {}
        self._builtin_buttons: dict[str, QPushButton] = {}
        self._scroll_badges: dict[str, QLabel] = {}
        self._pair_rows: list[QWidget] = []

        self.setObjectName("guideOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        self._build_ui()
        self._refresh_detail()
        self._refresh_pair_list()
        self._refresh_used_state()
        self._update_buttons_enabled()

    def _build_ui(self) -> None:
        """오버레이 내부 구성 (3분할 가로 배치)"""

        self._card: QFrame = QFrame(self)
        self._card.setObjectName("guideSelectionCard")

        layout: QVBoxLayout = QVBoxLayout(self._card)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        title_label: QLabel = QLabel("스킬 데이터 이전", self._card)
        title_label.setObjectName("guideDialogTitle")
        title_label.setFont(CustomFont(14, bold=True))
        layout.addWidget(title_label)

        # 본문: 커스텀 목록 | 기본 목록 | 우측 패널
        body_layout: QHBoxLayout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)

        body_layout.addLayout(
            self._build_scroll_column(
                "기존 커스텀 무공비급",
                self._custom_scrolls,
                is_custom=True,
            ),
            stretch=1,
        )
        body_layout.addLayout(
            self._build_scroll_column(
                "교체할 기본 무공비급",
                self._builtin_scrolls,
                is_custom=False,
            ),
            stretch=1,
        )
        body_layout.addWidget(self._build_side_panel())

        layout.addLayout(body_layout, stretch=1)

        # 하단 버튼
        button_layout: QHBoxLayout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()

        close_button: QPushButton = QPushButton("닫기", self._card)
        close_button.setObjectName("guideSecondaryButton")
        close_button.setFont(CustomFont(11))
        close_button.clicked.connect(self._handle_close)
        button_layout.addWidget(close_button)

        self._apply_button: QPushButton = QPushButton("적용", self._card)
        self._apply_button.setObjectName("guidePrimaryButton")
        self._apply_button.setFont(CustomFont(11))
        self._apply_button.clicked.connect(self._handle_apply)
        button_layout.addWidget(self._apply_button)

        layout.addLayout(button_layout)

    def _build_side_panel(self) -> QWidget:
        """우측 패널 구성 (선택 스킬 정보 + 교체 목록 + 추가/제거)"""

        panel: QWidget = QWidget(self._card)
        panel.setFixedWidth(290)

        panel_layout: QVBoxLayout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(8)

        # 선택 스킬 정보 영역
        detail_title: QLabel = QLabel("선택 스킬 정보", panel)
        detail_title.setObjectName("guideDialogBody")
        detail_title.setFont(CustomFont(11, bold=True))
        panel_layout.addWidget(detail_title)

        self._detail_card: QFrame = QFrame(panel)
        self._detail_card.setObjectName("migrationDetailCard")
        self._detail_card.setFixedHeight(140)
        detail_layout: QVBoxLayout = QVBoxLayout(self._detail_card)
        detail_layout.setContentsMargins(12, 10, 12, 10)
        detail_layout.setSpacing(8)

        self._custom_detail_label: QLabel = QLabel(self._detail_card)
        self._custom_detail_label.setObjectName("guideDialogBody")
        self._custom_detail_label.setFont(CustomFont(10))
        self._custom_detail_label.setWordWrap(True)
        self._custom_detail_label.setTextFormat(Qt.TextFormat.RichText)
        self._custom_detail_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        detail_layout.addWidget(self._custom_detail_label)

        self._builtin_detail_label: QLabel = QLabel(self._detail_card)
        self._builtin_detail_label.setObjectName("guideDialogBody")
        self._builtin_detail_label.setFont(CustomFont(10))
        self._builtin_detail_label.setWordWrap(True)
        self._builtin_detail_label.setTextFormat(Qt.TextFormat.RichText)
        self._builtin_detail_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        detail_layout.addWidget(self._builtin_detail_label)
        detail_layout.addStretch()

        panel_layout.addWidget(self._detail_card)

        self._add_button: QPushButton = QPushButton("교체 목록에 추가", panel)
        self._add_button.setObjectName("guidePrimaryButton")
        self._add_button.setFont(CustomFont(11))
        self._add_button.clicked.connect(self._handle_add_pair)
        panel_layout.addWidget(self._add_button)

        # 교체 목록 영역
        pair_title: QLabel = QLabel("교체 목록", panel)
        pair_title.setObjectName("guideDialogBody")
        pair_title.setFont(CustomFont(11, bold=True))
        panel_layout.addWidget(pair_title)

        self._pair_scroll: QScrollArea = QScrollArea(panel)
        self._pair_scroll.setObjectName("migrationScroll")
        self._pair_scroll.setWidgetResizable(True)
        self._pair_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._pair_scroll.setMinimumHeight(72)
        self._pair_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._pair_container: QWidget = QWidget()
        self._pair_container.setObjectName("migrationScrollContent")
        self._pair_layout: QVBoxLayout = QVBoxLayout(self._pair_container)
        self._pair_layout.setContentsMargins(6, 6, 6, 6)
        self._pair_layout.setSpacing(6)
        self._pair_layout.addStretch()
        self._pair_scroll.setWidget(self._pair_container)
        panel_layout.addWidget(self._pair_scroll, stretch=1)

        return panel

    def _build_scroll_column(
        self,
        title: str,
        scroll_defs: list[ScrollDef],
        is_custom: bool,
    ) -> QVBoxLayout:
        """무공비급 선택 컬럼 구성"""

        column_layout: QVBoxLayout = QVBoxLayout()
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(6)

        column_title: QLabel = QLabel(title, self._card)
        column_title.setObjectName("guideDialogBody")
        column_title.setFont(CustomFont(11, bold=True))
        column_layout.addWidget(column_title)

        scroll_area: QScrollArea = QScrollArea(self._card)
        scroll_area.setObjectName("migrationScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setMinimumHeight(120)
        scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        container: QWidget = QWidget()
        container.setObjectName("migrationScrollContent")
        list_layout: QVBoxLayout = QVBoxLayout(container)
        list_layout.setContentsMargins(6, 6, 6, 6)
        list_layout.setSpacing(6)

        target_buttons: dict[str, QPushButton] = (
            self._custom_buttons if is_custom else self._builtin_buttons
        )

        for scroll_def in scroll_defs:
            button: QPushButton = QPushButton(scroll_def.name, container)
            button.setObjectName("guideListButton")
            button.setFont(CustomFont(11))
            button.setCheckable(True)
            button.setIcon(_scroll_icon(scroll_def.id))
            button.setIconSize(QSize(_LIST_ICON_SIZE, _LIST_ICON_SIZE))
            scroll_id: str = scroll_def.id
            button.clicked.connect(
                lambda _checked, sid=scroll_id, custom=is_custom: self._handle_scroll_clicked(
                    sid, custom
                )
            )
            self.master.popup_manager.bind_hover_card(
                button,
                lambda definition=scroll_def: self._build_scroll_hover_card(definition),
            )

            # 교체 목록 등록 표시용 우측 ✓ 배지 (기본 숨김)
            badge_layout: QHBoxLayout = QHBoxLayout(button)
            badge_layout.setContentsMargins(0, 0, 10, 0)
            badge_layout.addStretch()
            badge: QLabel = QLabel(button)
            badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            badge.setPixmap(
                QPixmap(
                    get_theme_image_path("checkTrue.png", theme_manager.is_dark)
                ).scaled(
                    18,
                    18,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            badge.setVisible(False)
            badge_layout.addWidget(badge)

            list_layout.addWidget(button)
            target_buttons[scroll_def.id] = button
            self._scroll_badges[scroll_def.id] = badge

        list_layout.addStretch()
        scroll_area.setWidget(container)
        column_layout.addWidget(scroll_area)

        return column_layout

    def _handle_scroll_clicked(self, scroll_id: str, is_custom: bool) -> None:
        """무공비급 선택 처리"""

        if is_custom:
            self._selected_custom_id = scroll_id
            for sid, button in self._custom_buttons.items():
                button.setChecked(sid == scroll_id)
        else:
            self._selected_builtin_id = scroll_id
            for sid, button in self._builtin_buttons.items():
                button.setChecked(sid == scroll_id)

        self._refresh_detail()
        self._update_buttons_enabled()

    def _build_scroll_hover_card(self, scroll_def: ScrollDef) -> "HoverCardData":
        """무공비급 버튼 호버 카드 구성"""

        # 무공비급 ID를 공용 레벨 키로 사용, 없으면 1성 기준
        level: int = app_state.macro.current_preset.info.scroll_levels.get(
            scroll_def.id, 1
        )
        return self.master.popup_manager.build_scroll_hover_card(scroll_def, level)

    def _reference_level(self) -> int:
        """데미지 표시에 사용할 기존(커스텀) 무공비급 레벨 반환"""

        scroll_levels: dict[str, int] = (
            app_state.macro.current_preset.info.scroll_levels
        )

        # 커스텀이 선택돼 있으면 그 레벨, 없으면 선택된 기본 무공비급 레벨로 보정
        if self._selected_custom_id is not None:
            return scroll_levels.get(self._selected_custom_id, 1)

        if self._selected_builtin_id is not None:
            return scroll_levels.get(self._selected_builtin_id, 1)

        return 1

    def _refresh_detail(self) -> None:
        """선택 스킬 정보 영역 갱신"""

        is_dark: bool = theme_manager.is_dark
        level: int = self._reference_level()

        if self._selected_custom_id is None:
            self._custom_detail_label.clear()
        else:
            scroll_def: ScrollDef = self._server_spec.skill_registry.get_scroll(
                self._selected_custom_id
            )
            self._custom_detail_label.setText(
                _scroll_detail_html(
                    self._server_spec,
                    scroll_def,
                    level,
                    _CUSTOM_ACCENT_COLOR,
                    "커스텀",
                    is_dark,
                )
            )

        if self._selected_builtin_id is None:
            self._builtin_detail_label.clear()
        else:
            scroll_def = self._server_spec.skill_registry.get_scroll(
                self._selected_builtin_id
            )
            self._builtin_detail_label.setText(
                _scroll_detail_html(
                    self._server_spec,
                    scroll_def,
                    level,
                    _BUILTIN_ACCENT_COLOR,
                    "기본",
                    is_dark,
                )
            )

    def _handle_add_pair(self) -> None:
        """선택한 쌍을 교체 목록에 추가"""

        custom_id: str | None = self._selected_custom_id
        builtin_id: str | None = self._selected_builtin_id
        if custom_id is None or builtin_id is None:
            return

        # 동일 커스텀/기본 무공비급 중복 등록 방지
        for pair in self._pairs:
            if pair.custom_scroll_id == custom_id:
                return
            if pair.builtin_scroll_id == builtin_id:
                return

        self._pairs.append(
            MigrationPair.create(self._server_spec, custom_id, builtin_id)
        )

        # 추가 후 선택 해제 (비활성 항목이 선택 상태로 남지 않도록)
        self._selected_custom_id = None
        self._selected_builtin_id = None
        for button in self._custom_buttons.values():
            button.setChecked(False)
        for button in self._builtin_buttons.values():
            button.setChecked(False)

        self._refresh_detail()
        self._refresh_pair_list()
        self._refresh_used_state()
        self._update_buttons_enabled()

    def _handle_remove_pair(self, index: int) -> None:
        """지정한 교체 쌍 제거"""

        if not (0 <= index < len(self._pairs)):
            return

        self._pairs.pop(index)
        self._refresh_pair_list()
        self._refresh_used_state()
        self._update_buttons_enabled()

    def _refresh_used_state(self) -> None:
        """교체 목록에 등록된 무공비급 항목을 비활성·반투명·✓ 표시로 갱신"""

        used_custom_ids: set[str] = {pair.custom_scroll_id for pair in self._pairs}
        used_builtin_ids: set[str] = {pair.builtin_scroll_id for pair in self._pairs}

        self._apply_used_state(self._custom_buttons, used_custom_ids)
        self._apply_used_state(self._builtin_buttons, used_builtin_ids)

    def _apply_used_state(
        self,
        buttons: dict[str, QPushButton],
        used_ids: set[str],
    ) -> None:
        """버튼 묶음에 등록 여부 상태 반영"""

        for scroll_id, button in buttons.items():
            is_used: bool = scroll_id in used_ids

            button.setEnabled(not is_used)

            badge: QLabel | None = self._scroll_badges.get(scroll_id)
            if badge is not None:
                badge.setVisible(is_used)

            # 등록된 항목은 반투명 처리, 해제되면 효과 제거
            if is_used:
                effect: QGraphicsOpacityEffect = QGraphicsOpacityEffect(button)
                effect.setOpacity(0.45)
                button.setGraphicsEffect(effect)
            else:
                button.setGraphicsEffect(None)  # type: ignore

    def _refresh_pair_list(self) -> None:
        """교체 목록 영역 갱신"""

        # 기존 행 제거
        for row_ in self._pair_rows:
            self._pair_layout.removeWidget(row_)
            row_.deleteLater()
        self._pair_rows.clear()

        for index, pair in enumerate(self._pairs):
            custom_def: ScrollDef = self._server_spec.skill_registry.get_scroll(
                pair.custom_scroll_id
            )
            builtin_def: ScrollDef = self._server_spec.skill_registry.get_scroll(
                pair.builtin_scroll_id
            )

            # 텍스트 + 우측 삭제 아이콘으로 구성된 단일 항목 카드
            row: QFrame = QFrame(self._pair_container)
            row.setObjectName("migrationPairItem")
            row_layout: QHBoxLayout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 4, 6, 4)
            row_layout.setSpacing(6)

            label: QLabel = QLabel(f"{custom_def.name}  →  {builtin_def.name}", row)
            label.setObjectName("migrationPairText")
            label.setFont(CustomFont(11))
            row_layout.addWidget(label, stretch=1)

            remove_button: QPushButton = QPushButton(row)
            remove_button.setObjectName("skillItemRemoveBtn")
            remove_button.setIcon(
                QIcon(
                    QPixmap(get_theme_image_path("xAlpha.png", theme_manager.is_dark))
                )
            )
            remove_button.setIconSize(QSize(14, 14))
            remove_button.setFixedSize(28, 28)
            remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_button.clicked.connect(
                lambda _checked, i=index: self._handle_remove_pair(i)
            )
            row_layout.addWidget(remove_button)

            self._pair_layout.insertWidget(self._pair_layout.count() - 1, row)
            self._pair_rows.append(row)

    def _update_buttons_enabled(self) -> None:
        """버튼 활성화 상태 갱신"""

        can_add: bool = (
            self._selected_custom_id is not None
            and self._selected_builtin_id is not None
        )

        # 이미 등록된 무공비급은 추가 불가
        if can_add:
            for pair in self._pairs:
                if pair.custom_scroll_id == self._selected_custom_id:
                    can_add = False
                    break
                if pair.builtin_scroll_id == self._selected_builtin_id:
                    can_add = False
                    break

        self._add_button.setEnabled(can_add)
        self._apply_button.setEnabled(bool(self._pairs))

    def _handle_apply(self) -> None:
        """교체 적용"""

        self._on_apply(list(self._pairs))

    def _handle_close(self) -> None:
        """마이그레이션 화면 닫기"""

        self._on_close()

    def show_overlay(self) -> None:
        """오버레이 표시"""

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

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore
        """반투명 배경 그리기"""

        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), _overlay_color())
        super().paintEvent(event)

    def _place_card(self) -> None:
        """선택 카드를 창 크기에 맞춰 중앙 배치"""

        card_width: int = min(900, max(420, self.width() - 40))
        card_height: int = min(720, max(320, self.height() - 40))
        self._card.setFixedSize(card_width, card_height)

        x: int = max(20, (self.width() - card_width) // 2)
        y: int = max(20, (self.height() - card_height) // 2)
        self._card.move(x, y)


class SkillMigrationManager:
    """스킬 마이그레이션 시작 흐름 관리"""

    def __init__(self, master: MainWindow) -> None:
        self.master: MainWindow = master
        self._overlay: SkillMigrationOverlay | None = None
        self._on_finished: Callable[[], None] | None = None
        self._mark_version_on_finish: bool = True

    def show_if_needed(self, on_finished: Callable[[], None]) -> None:
        """업데이트 후 첫 실행이고 커스텀 무공비급이 있으면 마이그레이션 화면 표시"""

        self._on_finished = on_finished
        self._mark_version_on_finish = True

        server_spec: ServerSpec = app_state.macro.current_server
        version_changed: bool = app_state.ui.last_app_version != config.version

        if version_changed and has_custom_scrolls(server_spec):
            self._show_overlay(server_spec)
            return

        # 표시 조건 미충족 시 현재 버전 기록 후 다음 안내로 진행
        mark_current_app_version_seen()
        self._finish()

    def show_manual(self) -> None:
        """커스텀 무공비급 이전 화면 수동 표시"""

        if self.master.get_popup_manager().reject_if_input_sequence_active():
            return

        server_spec: ServerSpec = app_state.macro.current_server
        if not has_custom_scrolls(server_spec):
            return

        self._on_finished = None
        self._mark_version_on_finish = False
        self._show_overlay(server_spec)

    def refresh_visible_overlay(self) -> None:
        """창 크기 변경 시 표시 중인 오버레이 재배치"""

        if self._overlay is not None and self._overlay.isVisible():
            self._overlay.refresh_layout()

    def _show_overlay(self, server_spec: ServerSpec) -> None:
        """마이그레이션 오버레이 표시"""

        self._overlay = SkillMigrationOverlay(
            self.master,
            server_spec,
            on_apply=self._handle_apply,
            on_close=self._handle_close,
        )
        self._overlay.setStyleSheet(self.master.styleSheet())
        self._overlay.show_overlay()

    def _handle_apply(self, pairs: list[MigrationPair]) -> None:
        """선택한 교체 쌍 적용"""

        if self.master.get_popup_manager().reject_if_input_sequence_active():
            return

        server_id: str = app_state.macro.current_preset.settings.server_id
        apply_skill_migration(app_state.macro.presets, server_id, pairs)

        # 마이그레이션 결과 저장
        if self._mark_version_on_finish:
            mark_current_app_version_seen()
        else:
            save_data()

        # 변경된 참조를 메인 UI와 사이드바에 반영
        self.master.sidebar.update_from_preset()
        self.master.main_ui.tab_widget.get_current_tab().update_from_preset(
            force_preview=True
        )

        self._teardown_overlay()
        self._finish()

    def _handle_close(self) -> None:
        """마이그레이션 없이 화면 닫기"""

        if self._mark_version_on_finish:
            mark_current_app_version_seen()

        self._teardown_overlay()
        self._finish()

    def _teardown_overlay(self) -> None:
        """오버레이 정리"""

        if self._overlay is not None:
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None

    def _finish(self) -> None:
        """다음 시작 안내로 진행"""

        callback: Callable[[], None] | None = self._on_finished
        self._on_finished = None
        if callback is not None:
            callback()
