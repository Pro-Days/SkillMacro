"""캐릭터 창 3분할 셸"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.calculator_models import REALM_TIER_SPECS
from app.scripts.character_engine import (
    clone_character_profile,
    compute_live_view,
    deserialize_character_profile,
    serialize_character_profile,
    validate_character_store,
)
from app.scripts.character_models import CharacterProfile, CharacterStore
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.data_manager import save_characters
from app.scripts.ui.character_ui.constants import CHARACTER_TABS
from app.scripts.ui.character_ui.panels.character_list import CharacterListPanel
from app.scripts.ui.character_ui.panels.live_stats import LiveStatsPanel
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


class _TabStack(QWidget):
    """표시/숨김 방식 탭 스택

    QStackedWidget 은 항상 가장 큰 페이지 높이를 예약하지만, 이 스택은 본문
    스크롤 영역을 공유하므로 현재 페이지 높이에만 맞아야 한다. 숨긴 페이지가
    레이아웃 높이에 기여하지 않도록 단순 표시/숨김으로 직접 구현한다.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._stack_layout = QVBoxLayout(self)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)
        self._stack_layout.setSpacing(0)
        self._pages: list[QWidget] = []
        self._current: int = 0

    def addWidget(self, widget: QWidget) -> None:
        """탭 페이지 추가"""

        self._pages.append(widget)
        self._stack_layout.addWidget(widget)
        widget.setVisible(len(self._pages) == 1)

    def setCurrentIndex(self, index: int) -> None:
        """현재 탭만 표시"""

        for page_index, page in enumerate(self._pages):
            page.setVisible(page_index == index)

        self._current = index
        self.updateGeometry()

    def currentWidget(self) -> QWidget | None:
        """현재 탭 위젯"""

        return self._pages[self._current] if self._pages else None


class CharacterPage(QFrame):
    """계산기 4번째 탭에 들어가는 캐릭터 창"""

    def __init__(
        self,
        parent: QWidget,
        on_use_calculator: Callable[[CharacterProfile], None],
    ) -> None:
        super().__init__(parent)

        self._on_use_calculator: Callable[[CharacterProfile], None] = on_use_calculator
        self._save_timer: QTimer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current_store)

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
            self._paste_character,
            self._clone_character,
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

        self._toggle_left_btn: QPushButton = QPushButton("❮", header)
        self._toggle_left_btn.setObjectName("charIconBtn")
        self._toggle_left_btn.setFixedSize(28, 28)
        self._toggle_left_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_left_btn.clicked.connect(lambda: self._toggle_panel("left"))
        layout.addWidget(self._toggle_left_btn)

        self._title_label: QLabel = QLabel("캐릭터 없음", header)
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

        self._toggle_right_btn: QPushButton = QPushButton("❯", header)
        self._toggle_right_btn.setObjectName("charIconBtn")
        self._toggle_right_btn.setFixedSize(28, 28)
        self._toggle_right_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_right_btn.clicked.connect(lambda: self._toggle_panel("right"))
        layout.addWidget(self._toggle_right_btn)
        return header

    def _build_tab_bar(self) -> QFrame:
        """알약 탭 바 구성"""

        bar: QFrame = QFrame(self)
        bar.setObjectName("charTabBar")
        layout: FlowLayout = FlowLayout(bar, margin=0, spacing=6)
        layout.setContentsMargins(12, 8, 12, 8)

        self._tabs: list[PillTab] = []
        for index, tab in enumerate(CHARACTER_TABS):
            pill: PillTab = PillTab(bar, tab.label, tab.color, index, self._go)
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

        from PySide6.QtWidgets import QScrollArea

        scroll: QScrollArea = QScrollArea(wrapper)
        scroll.setObjectName("charBodyScroll")
        scroll.setWidgetResizable(True)
        wrapper_layout.addWidget(scroll)

        self._body_content: QWidget = QWidget()
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

        self._profile_tabs: list[QWidget] = [
            TitleTab(self._stack, self._on_profile_changed),
            EquipmentTab(self._stack, self._on_profile_changed),
            DistributionTab(self._stack, self._on_profile_changed),
            DisplayStandTab(self._stack, self._on_profile_changed),
            TalismanTab(self._stack, self._on_profile_changed),
            ElixirTab(self._stack, self._on_profile_changed),
            PillEffectTab(self._stack, self._on_profile_changed),
        ]
        for page in self._profile_tabs:
            self._stack.addWidget(page)

        self._go(0)
        return wrapper

    def refresh_from_store(self) -> None:
        """전역 캐릭터 저장소 기준 화면 갱신"""

        store: CharacterStore = app_state.character_store
        self._left_panel.set_characters(store.characters, store.selected_index)
        profile: CharacterProfile | None = self._selected_profile()

        if profile is None:
            self._title_label.setText("캐릭터 없음")
            self._subtitle_label.setText("미입력")
            self._use_calculator_btn.setEnabled(False)
            self._right_panel.set_live_view(None)

        else:
            name_text: str = profile.name if profile.name.strip() else "이름 없음"
            realm_label: str = REALM_TIER_SPECS[profile.realm].label
            self._title_label.setText(name_text)
            self._subtitle_label.setText(f"Lv. {profile.level} · {realm_label}")
            self._use_calculator_btn.setEnabled(True)
            self._right_panel.set_live_view(compute_live_view(profile))

        for page in self._profile_tabs:
            if hasattr(page, "set_profile"):
                page.set_profile(profile)

    def _selected_profile(self) -> CharacterProfile | None:
        """현재 선택 캐릭터 조회"""

        store: CharacterStore = app_state.character_store
        if store.selected_index == -1:
            return None

        return store.characters[store.selected_index]

    def _on_character_selected(self, index: int) -> None:
        """좌측 캐릭터 선택 처리"""

        app_state.character_store.selected_index = index
        save_characters()
        self.refresh_from_store()

    def _add_character(self) -> None:
        """새 캐릭터 추가"""

        store: CharacterStore = app_state.character_store
        new_character: CharacterProfile = CharacterProfile(name="새 캐릭터")
        store.characters.append(new_character)
        store.selected_index = len(store.characters) - 1
        save_characters()
        self.refresh_from_store()

    def _clone_character(self) -> None:
        """선택 캐릭터 복제"""

        profile: CharacterProfile | None = self._selected_profile()
        if profile is None:
            return

        store: CharacterStore = app_state.character_store
        cloned: CharacterProfile = clone_character_profile(profile)
        cloned.name = f"{profile.name} 복사"
        store.characters.append(cloned)
        store.selected_index = len(store.characters) - 1
        save_characters()
        self.refresh_from_store()

    def _paste_character(self) -> None:
        """클립보드 캐릭터 붙여넣기"""

        clipboard = QApplication.clipboard()
        text: str = clipboard.text()
        if not text:
            return

        store: CharacterStore = app_state.character_store
        pasted: CharacterProfile = deserialize_character_profile(text)
        store.characters.append(pasted)
        store.selected_index = len(store.characters) - 1
        save_characters()
        self.refresh_from_store()

    def _delete_character(self) -> None:
        """선택 캐릭터 삭제"""

        store: CharacterStore = app_state.character_store
        if store.selected_index == -1:
            return

        store.characters.pop(store.selected_index)
        if not store.characters:
            store.selected_index = -1

        elif store.selected_index >= len(store.characters):
            store.selected_index = len(store.characters) - 1

        save_characters()
        self.refresh_from_store()

    def copy_selected_character(self) -> None:
        """선택 캐릭터 클립보드 복사"""

        profile: CharacterProfile | None = self._selected_profile()
        if profile is None:
            return

        QApplication.clipboard().setText(serialize_character_profile(profile))

    def _on_profile_changed(self) -> None:
        """입력 변경 후 저장 예약 및 실시간 표시 갱신"""

        profile: CharacterProfile | None = self._selected_profile()
        if profile is None:
            return

        self._clamp_profile_allocations(profile)
        self._title_label.setText(profile.name if profile.name.strip() else "이름 없음")
        self._subtitle_label.setText(
            f"Lv. {profile.level} · {REALM_TIER_SPECS[profile.realm].label}"
        )
        self._left_panel.set_characters(
            app_state.character_store.characters,
            app_state.character_store.selected_index,
        )
        self._right_panel.set_live_view(compute_live_view(profile))
        for page in self._profile_tabs:
            if isinstance(page, DistributionTab):
                page.set_profile(profile)

        self._save_timer.start(_SAVE_DELAY_MS)

    def _clamp_profile_allocations(self, profile: CharacterProfile) -> None:
        """레벨·경지 변경 후 분배 한도 초과값 정리"""

        # 스탯 분배 한도 기준 순차 보존
        remaining_stat_points: int = profile.level * 5
        profile.distribution.strength = min(
            profile.distribution.strength,
            remaining_stat_points,
        )
        remaining_stat_points -= profile.distribution.strength
        profile.distribution.dexterity = min(
            profile.distribution.dexterity,
            remaining_stat_points,
        )
        remaining_stat_points -= profile.distribution.dexterity
        profile.distribution.vitality = min(
            profile.distribution.vitality,
            remaining_stat_points,
        )
        remaining_stat_points -= profile.distribution.vitality
        profile.distribution.luck = min(
            profile.distribution.luck,
            remaining_stat_points,
        )

        # 단전 분배 한도 기준 순차 보존
        remaining_danjeon_points: int = REALM_TIER_SPECS[profile.realm].danjeon_points
        profile.danjeon.upper = min(profile.danjeon.upper, remaining_danjeon_points)
        remaining_danjeon_points -= profile.danjeon.upper
        profile.danjeon.middle = min(profile.danjeon.middle, remaining_danjeon_points)
        remaining_danjeon_points -= profile.danjeon.middle
        profile.danjeon.lower = min(profile.danjeon.lower, remaining_danjeon_points)

    def _save_current_store(self) -> None:
        """현재 캐릭터 저장소 검증 및 저장"""

        validate_character_store(app_state.character_store)
        save_characters()

    def _use_selected_character(self) -> None:
        """선택 캐릭터를 계산기 입력에 반영"""

        profile: CharacterProfile | None = self._selected_profile()
        if profile is None:
            return

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
