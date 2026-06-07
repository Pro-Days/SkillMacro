from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.calculator_models import REALM_TIER_SPECS
from app.scripts.character_engine import (
    clamp_profile_allocations,
    compute_live_view,
    deserialize_character_profile,
    serialize_character_profile,
)
from app.scripts.character_models import (
    DEFAULT_CHARACTER_NAME,
    CharacterProfile,
    CharacterStore,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.data_manager import save_characters
from app.scripts.ui.character_ui.change_handler import CharacterChangeHandler
from app.scripts.ui.character_ui.panels.character_list import CharacterListPanel
from app.scripts.ui.character_ui.panels.live_stats import LiveStatsPanel
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.tabs.display_stand_tab import DisplayStandTab
from app.scripts.ui.character_ui.tabs.distribution_tab import DistributionTab
from app.scripts.ui.character_ui.tabs.elixir_tab import ElixirTab
from app.scripts.ui.character_ui.tabs.equipment_tab import EquipmentTab
from app.scripts.ui.character_ui.tabs.pill_tab import PillTab as PillEffectTab
from app.scripts.ui.character_ui.tabs.talisman_tab import TalismanTab
from app.scripts.ui.character_ui.tabs.title_tab import TitleTab
from app.scripts.ui.character_ui.widgets import FlowLayout, PillTab

_LEFT_WIDTH: int = 236
_RIGHT_WIDTH: int = 340
_SAVE_DELAY_MS: int = 400

_CHARACTER_TABS: tuple[tuple[str, type[CharacterTab]], ...] = (
    ("기본정보", TitleTab),
    ("장비", EquipmentTab),
    ("스탯·단전 분배", DistributionTab),
    ("진열대", DisplayStandTab),
    ("부적", TalismanTab),
    ("영단", ElixirTab),
    ("환", PillEffectTab),
)


class _TabStack(QWidget):
    """표시/숨김 방식 탭 스택"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._stack_layout = QVBoxLayout(self)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)
        self._stack_layout.setSpacing(0)

        self._pages: list[QWidget] = []
        self._current: int = 0

    def addWidget(self, widget: QWidget) -> None:
        self._pages.append(widget)
        self._stack_layout.addWidget(widget)
        widget.setVisible(len(self._pages) == 1)

    def setCurrentIndex(self, index: int) -> None:
        for page_index, page in enumerate(self._pages):
            page.setVisible(page_index == index)

        self._current = index
        self.updateGeometry()

    def currentWidget(self) -> QWidget | None:
        return self._pages[self._current] if self._pages else None


class CharacterPage(QFrame):
    """계산기 4번째 탭에 들어가는 캐릭터 창"""

    def __init__(
        self,
        parent: QWidget,
        on_use_calculator: Callable[[CharacterProfile], None],
    ) -> None:
        super().__init__(parent)

        # 캐릭터 상태 계산기 입력 페이지에 반영하는 함수
        self._on_use_calculator: Callable[[CharacterProfile], None] = on_use_calculator

        self._save_timer: QTimer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current_store)
        self._changes: CharacterChangeHandler = CharacterChangeHandler(
            self._commit_name,
            self._commit_progression,
            self._live_stats_changed,
            self._commit_saved_value,
        )

        self.setObjectName("charRoot")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 좌측 캐릭터 목록 패널
        self._left_panel: CharacterListPanel = CharacterListPanel(
            self,
            self._on_character_selected,
            self._add_character,
            self.copy_selected_character,
            self._paste_character,
            self._delete_character,
        )
        self._left_panel.setFixedWidth(_LEFT_WIDTH)
        self._left_panel.setMinimumWidth(0)
        self._left_panel.setMaximumWidth(0)
        self._left_collapsed: bool = True
        layout.addWidget(self._left_panel)

        layout.addWidget(self._build_center(), 1)

        # 우측 전체 스탯 패널
        self._right_panel: LiveStatsPanel = LiveStatsPanel(self)
        self._right_panel.setFixedWidth(_RIGHT_WIDTH)
        self._right_panel.setMinimumWidth(0)
        self._right_collapsed: bool = False
        layout.addWidget(self._right_panel)

        self._left_anim: QPropertyAnimation | None = None
        self._right_anim: QPropertyAnimation | None = None

        self._update_toggle_labels()
        self.refresh_from_store()

    def _build_center(self) -> QFrame:
        """중앙 패널 구성"""

        center: QFrame = QFrame(self)
        center.setObjectName("charPanel")

        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        center_layout.addWidget(self._build_header())
        center_layout.addWidget(self._build_tab_bar())
        center_layout.addWidget(self._build_stack(), 1)

        return center

    def _build_header(self) -> QFrame:
        """중앙 헤더 구성"""

        header: QFrame = QFrame(self)
        header.setObjectName("charCenterHead")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(10)

        # 좌측 패널 토글 버튼
        self._toggle_left_btn: QPushButton = QPushButton("❮", header)
        self._toggle_left_btn.setObjectName("charIconBtn")
        self._toggle_left_btn.setFixedSize(28, 28)
        self._toggle_left_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_left_btn.clicked.connect(lambda: self._toggle_panel("left"))
        layout.addWidget(self._toggle_left_btn)

        self._title_label: QLabel = QLabel(DEFAULT_CHARACTER_NAME, header)
        self._title_label.setObjectName("charHeadTitle")
        self._title_label.setFont(CustomFont(13, bold=True))

        self._subtitle_label: QLabel = QLabel("미입력", header)
        self._subtitle_label.setObjectName("charSub")
        self._subtitle_label.setFont(CustomFont(9))

        layout.addWidget(self._title_label)
        layout.addSpacing(8)
        layout.addWidget(self._subtitle_label, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch(1)

        self._use_calculator_btn: StyledButton = StyledButton(
            header,
            "계산기에 사용",
            kind="normal",
            point_size=9,
        )
        self._use_calculator_btn.clicked.connect(self._use_selected_character)
        layout.addWidget(self._use_calculator_btn)

        # 우측 패널 토글 버튼
        self._toggle_right_btn: QPushButton = QPushButton("❯", header)
        self._toggle_right_btn.setObjectName("charIconBtn")
        self._toggle_right_btn.setFixedSize(28, 28)
        self._toggle_right_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_right_btn.clicked.connect(lambda: self._toggle_panel("right"))
        layout.addWidget(self._toggle_right_btn)

        return header

    def _build_tab_bar(self) -> QFrame:
        """알약 탭 바 구성"""

        bar = QFrame(self)
        bar.setObjectName("charTabBar")

        layout: FlowLayout = FlowLayout(bar, margin=0, spacing=6)
        layout.setContentsMargins(12, 8, 12, 8)

        self._tabs: list[PillTab] = []
        for index, (tab_label, _tab_factory) in enumerate(_CHARACTER_TABS):
            pill: PillTab = PillTab(bar, tab_label, index, self._go)
            self._tabs.append(pill)
            layout.addWidget(pill)

        bar.setLayout(layout)
        return bar

    def _build_stack(self) -> QFrame:
        """중앙 본문 스택 구성"""

        wrapper: QFrame = QFrame(self)
        wrapper.setObjectName("charBody")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        scroll: QScrollArea = QScrollArea(wrapper)
        scroll.setObjectName("charBodyScroll")
        scroll.setWidgetResizable(True)
        wrapper_layout.addWidget(scroll)

        self._body_content = QWidget()
        self._body_content.setObjectName("charBodyContent")
        self._body_content.setMinimumWidth(0)
        self._body_margin: int = 16
        content_layout = QVBoxLayout(self._body_content)
        content_layout.setContentsMargins(
            self._body_margin,
            self._body_margin,
            self._body_margin,
            self._body_margin,
        )
        content_layout.setSpacing(0)

        self._stack: _TabStack = _TabStack(self._body_content)
        self._stack.setMinimumWidth(0)
        self._stack.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        content_layout.addWidget(self._stack)
        scroll.setWidget(self._body_content)

        initial_profile: CharacterProfile = self._selected_profile()
        self._tab_pages: list[CharacterTab] = []
        for _tab_label, tab_factory in _CHARACTER_TABS:
            page: CharacterTab = tab_factory(
                self._stack,
                self._changes,
                initial_profile,
            )
            self._tab_pages.append(page)
            self._stack.addWidget(page)

        self._go(0)

        return wrapper

    def refresh_from_store(self) -> None:
        """전역 캐릭터 저장소 기준 화면 갱신"""

        store: CharacterStore = app_state.character_store
        self._left_panel.set_characters(store.characters, store.selected_index)
        self._refresh_selected_profile()

    def _refresh_selected_profile(self) -> None:
        """선택 캐릭터 기준 헤더, 스탯, 입력 탭 갱신"""

        profile: CharacterProfile = self._selected_profile()
        name_text: str = profile.name if profile.name.strip() else "이름 없음"
        realm_label: str = REALM_TIER_SPECS[profile.realm].label
        self._title_label.setText(name_text)
        self._subtitle_label.setText(f"Lv. {profile.level} · {realm_label}")
        self._use_calculator_btn.setEnabled(True)
        self._right_panel.set_live_view(compute_live_view(profile))

        for page in self._tab_pages:
            page.set_profile(profile)

    def _selected_profile(self) -> CharacterProfile:
        """현재 선택 캐릭터 조회"""

        store: CharacterStore = app_state.character_store
        return store.characters[store.selected_index]

    def _on_character_selected(self, index: int) -> None:
        """좌측 캐릭터 선택 처리"""

        app_state.character_store.selected_index = index
        self._schedule_save()
        self._refresh_selected_profile()

    def _add_character(self) -> None:
        """새 캐릭터 추가"""

        store: CharacterStore = app_state.character_store
        new_character: CharacterProfile = CharacterProfile(name="새 캐릭터")
        store.characters.append(new_character)
        store.selected_index = len(store.characters) - 1

        save_characters()
        self._left_panel.append_character(new_character, store.selected_index)
        self._refresh_selected_profile()

    def _paste_character(self) -> bool:
        """클립보드 캐릭터 붙여넣기"""

        clipboard: QClipboard = QApplication.clipboard()
        text: str = clipboard.text()
        if not text:
            return False

        try:
            pasted: CharacterProfile = deserialize_character_profile(text)

        except (KeyError, TypeError, ValueError):
            return False

        store: CharacterStore = app_state.character_store
        store.characters.append(pasted)
        store.selected_index = len(store.characters) - 1

        save_characters()
        self._left_panel.append_character(pasted, store.selected_index)
        self._refresh_selected_profile()
        return True

    def _delete_character(self) -> None:
        """선택 캐릭터 삭제"""

        store: CharacterStore = app_state.character_store
        removed_index: int = store.selected_index
        store.characters.pop(removed_index)

        if not store.characters:
            store.characters.append(CharacterProfile(name=DEFAULT_CHARACTER_NAME))
            store.selected_index = 0

        elif removed_index >= len(store.characters):
            store.selected_index = len(store.characters) - 1

        else:
            store.selected_index = removed_index

        save_characters()
        self._left_panel.set_characters(store.characters, store.selected_index)
        self._refresh_selected_profile()

    def copy_selected_character(self) -> bool:
        """선택 캐릭터 클립보드 복사"""

        profile: CharacterProfile = self._selected_profile()
        QApplication.clipboard().setText(serialize_character_profile(profile))
        return True

    def _refresh_name(self) -> None:
        """캐릭터 이름 표시 갱신"""

        profile: CharacterProfile = self._selected_profile()
        self._title_label.setText(profile.name if profile.name.strip() else "이름 없음")
        self._left_panel.update_selected_name(profile)

    def _refresh_progression(self) -> None:
        """캐릭터 레벨·경지 표시 갱신"""

        profile: CharacterProfile = self._selected_profile()
        self._subtitle_label.setText(
            f"Lv. {profile.level} · {REALM_TIER_SPECS[profile.realm].label}"
        )
        self._left_panel.update_selected_meta(profile)

    def _refresh_live_stats(self) -> None:
        """선택 캐릭터 실시간 스탯 갱신"""

        profile: CharacterProfile = self._selected_profile()
        self._right_panel.set_live_view(compute_live_view(profile))

    def _schedule_save(self) -> None:
        """캐릭터 저장 예약"""

        self._save_timer.start(_SAVE_DELAY_MS)

    def _commit_name(self) -> None:
        """캐릭터 이름 변경 반영"""

        self._refresh_name()
        self._schedule_save()

    def _commit_progression(self) -> None:
        """레벨·경지 변경 반영"""

        profile: CharacterProfile = self._selected_profile()
        clamp_profile_allocations(profile)
        self._refresh_progression()
        for page in self._tab_pages:
            page.on_progression_changed()

        self._live_stats_changed()

    def _live_stats_changed(self) -> None:
        """실시간 스탯 변경 반영"""

        self._refresh_live_stats()
        self._schedule_save()

    def _commit_saved_value(self) -> None:
        """화면 외부 계산에 영향 없는 저장값 변경 반영"""

        self._schedule_save()

    def _save_current_store(self) -> None:
        save_characters()

    def _use_selected_character(self) -> None:
        """선택 캐릭터를 계산기 입력에 반영"""

        profile: CharacterProfile = self._selected_profile()
        self._save_current_store()
        self._on_use_calculator(profile)

    def _go(self, index: int) -> None:
        """탭 전환"""

        self._stack.setCurrentIndex(index)
        for tab_index, pill in enumerate(self._tabs):
            pill.setChecked(tab_index == index)

    def _toggle_panel(self, side: str) -> None:
        """좌/우 패널 접기·펼치기 애니메이션"""

        if side == "left":
            self._left_collapsed = not self._left_collapsed
            target: int = 0 if self._left_collapsed else _LEFT_WIDTH
            self._left_anim = self._animate_width(self._left_panel, target)

        else:
            self._right_collapsed = not self._right_collapsed
            target = 0 if self._right_collapsed else _RIGHT_WIDTH
            self._right_anim = self._animate_width(self._right_panel, target)

        self._update_toggle_labels()

    def _animate_width(self, panel: QWidget, target: int) -> QPropertyAnimation:
        """패널 최대 폭 애니메이션"""

        animation: QPropertyAnimation = QPropertyAnimation(panel, b"maximumWidth", self)
        animation.setDuration(280)
        animation.setStartValue(panel.maximumWidth())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.start()
        return animation

    def _update_toggle_labels(self) -> None:
        """토글 버튼 화살표 갱신"""

        self._toggle_left_btn.setText("❯" if self._left_collapsed else "❮")
        self._toggle_right_btn.setText("❮" if self._right_collapsed else "❯")
