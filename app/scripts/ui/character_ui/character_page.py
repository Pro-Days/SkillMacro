"""캐릭터 창 3분할 셸

좌(캐릭터 선택) · 중(입력 탭) · 우(전체 스탯) 3분할 레이아웃과
좌·우 패널 접기, 중앙 알약 탭 전환을 담당한다.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _TabStack(QWidget):
    """표시/숨김 방식 탭 스택

    QStackedWidget 은 모든 페이지 중 가장 큰 최소높이를 강제해(=가장 긴 탭 기준)
    짧은 탭에서 빈 여백이 생긴다. 현재 탭만 보이고 나머지는 숨겨
    레이아웃이 현재 탭 크기만 반영하도록 한다.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._stack_layout = QVBoxLayout(self)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)
        self._stack_layout.setSpacing(0)
        self._pages: list[QWidget] = []
        self._current: int = 0

    def addWidget(self, widget: QWidget) -> None:
        """탭 페이지 추가 (첫 페이지만 표시)"""

        self._pages.append(widget)
        self._stack_layout.addWidget(widget)
        widget.setVisible(len(self._pages) == 1)

    def setCurrentIndex(self, index: int) -> None:
        """현재 탭만 표시"""

        for i, page in enumerate(self._pages):
            page.setVisible(i == index)
        self._current = index

    def currentWidget(self) -> QWidget | None:
        """현재 탭 위젯"""

        return self._pages[self._current] if self._pages else None

    def widget(self, index: int) -> QWidget:
        """인덱스로 탭 위젯 조회"""

        return self._pages[index]

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(0, 0)


class _BodyContent(QWidget):
    """본문 스크롤 콘텐츠 — 폭이 바뀌면 콜백으로 높이를 다시 계산하게 한다"""

    def __init__(self, on_resize: "Callable[[], None]") -> None:
        super().__init__()
        self._on_resize: "Callable[[], None]" = on_resize

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._on_resize()


from app.scripts.custom_classes import CustomFont
from app.scripts.ui.character_ui import sample_data
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


class CharacterPage(QFrame):
    """계산기 4번째 탭에 들어가는 캐릭터 창"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setObjectName("charRoot")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 좌측 패널 (기본 접힘)
        self._left_panel: CharacterListPanel = CharacterListPanel(
            self, self._on_character_selected
        )
        self._left_panel.setFixedWidth(_LEFT_WIDTH)
        self._left_panel.setMinimumWidth(0)
        self._left_panel.setMaximumWidth(0)
        self._left_collapsed: bool = True
        layout.addWidget(self._left_panel)

        # 중앙
        layout.addWidget(self._build_center(), 1)

        # 우측 패널
        self._right_panel: LiveStatsPanel = LiveStatsPanel(self)
        self._right_panel.setFixedWidth(_RIGHT_WIDTH)
        self._right_panel.setMinimumWidth(0)
        self._right_collapsed: bool = False
        layout.addWidget(self._right_panel)

        self._left_anim: QPropertyAnimation | None = None
        self._right_anim: QPropertyAnimation | None = None
        self._update_toggle_labels()

    def _build_center(self) -> QFrame:
        """중앙 패널 (헤더 + 알약 탭 + 스택)"""

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
        """중앙 헤더 (좌 토글 + 캐릭터명 + 우 토글)"""

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

        # 이름 + 레벨·경지를 한 줄에 표시 (헤더 높이 최소화)
        first: sample_data.CharacterSummary = sample_data.CHARACTERS[0]
        self._title_label: QLabel = QLabel(first.name, header)
        self._title_label.setObjectName("charHeadTitle")
        self._title_label.setFont(CustomFont(13, bold=True))
        self._subtitle_label: QLabel = QLabel(first.meta, header)
        self._subtitle_label.setObjectName("charSub")
        self._subtitle_label.setFont(CustomFont(9))

        layout.addWidget(self._title_label)
        layout.addSpacing(8)
        layout.addWidget(self._subtitle_label, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch(1)

        self._toggle_right_btn: QPushButton = QPushButton("❯", header)
        self._toggle_right_btn.setObjectName("charIconBtn")
        self._toggle_right_btn.setFixedSize(28, 28)
        self._toggle_right_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_right_btn.clicked.connect(lambda: self._toggle_panel("right"))
        layout.addWidget(self._toggle_right_btn)
        return header

    def _build_tab_bar(self) -> QFrame:
        """알약 탭 바"""

        bar: QFrame = QFrame(self)
        bar.setObjectName("charTabBar")
        # 폭이 좁으면 알약 탭이 줄바꿈되도록 FlowLayout 사용
        layout: FlowLayout = FlowLayout(bar, margin=0, spacing=6)
        layout.setContentsMargins(12, 8, 12, 8)

        self._tabs: list[PillTab] = []
        for index, tab in enumerate(sample_data.TABS):
            pill: PillTab = PillTab(bar, tab.label, tab.color, index, self._go)
            self._tabs.append(pill)
            layout.addWidget(pill)
        bar.setLayout(layout)
        return bar

    def _build_stack(self) -> QFrame:
        """중앙 본문 (탭별 페이지 스택, 자체 스크롤)"""

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

        self._body_content: _BodyContent = _BodyContent(self._sync_body_height)
        self._body_content.setObjectName("charBodyContent")
        self._body_margin: int = 16
        content_layout = QVBoxLayout(self._body_content)
        content_layout.setContentsMargins(
            self._body_margin, self._body_margin, self._body_margin, self._body_margin
        )
        content_layout.setSpacing(0)

        self._stack: _TabStack = _TabStack(self._body_content)
        content_layout.addWidget(self._stack)
        scroll.setWidget(self._body_content)

        # 탭 순서와 동일하게 페이지 추가 (TABS: title/equip/dist/shelf/talisman/yeongdan/hwan)
        self._stack.addWidget(TitleTab(self._stack))
        self._stack.addWidget(EquipmentTab(self._stack))
        self._stack.addWidget(DistributionTab(self._stack))
        self._stack.addWidget(DisplayStandTab(self._stack))
        self._stack.addWidget(TalismanTab(self._stack))
        self._stack.addWidget(ElixirTab(self._stack))
        self._stack.addWidget(PillEffectTab(self._stack))

        self._go(0)
        return wrapper

    def _go(self, index: int) -> None:
        """탭 전환"""

        self._stack.setCurrentIndex(index)
        # 현재 페이지 기준 높이로 갱신 (탭 전환 시 빈 여백 제거)
        self._sync_body_height()
        for i, pill in enumerate(self._tabs):
            pill.setChecked(i == index)

    def _sync_body_height(self) -> None:
        """현재 탭의 실제 배치 높이로 본문 콘텐츠 최소 높이를 맞춘다"""

        page: QWidget | None = self._stack.currentWidget()
        if page is None:
            return
        margins: int = self._body_margin * 2
        inner_width: int = self._body_content.width() - margins
        if inner_width <= 0:
            return

        page_layout = page.layout()
        if page_layout is not None and page_layout.hasHeightForWidth():
            height: int = page_layout.heightForWidth(inner_width)
        else:
            height = page.sizeHint().height()
        self._body_content.setMinimumHeight(height + margins)

    def _on_character_selected(self, index: int) -> None:
        """좌측 캐릭터 선택 시 헤더 갱신"""

        summary: sample_data.CharacterSummary = sample_data.CHARACTERS[index]
        self._title_label.setText(summary.name)
        self._subtitle_label.setText(summary.meta)

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
