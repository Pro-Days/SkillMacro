"""캐릭터 창 전용 공용 위젯

목업 고유 컴포넌트(KV 스텝퍼, 빠른가감 칩, 알약 탭, 세그 버튼, 등급 뱃지,
색 구슬, 토글 스위치)와 카드 자동 래핑용 FlowLayout 을 정의한다.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QDoubleValidator, QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont


class CharComboBox(QComboBox):
    """캐릭터 창 전용 콤보박스 (신규 UI 스타일에 맞춘 외형)"""

    def __init__(self, parent: QWidget, items: list[str], point_size: int = 10) -> None:
        super().__init__(parent)

        self.setObjectName("charCombo")
        self.setFont(CustomFont(point_size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.addItems(items)

    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore[override]
        """닫힌 상태에서는 휠 변경 무시"""

        if self.view().isVisible():
            super().wheelEvent(event)
            return
        event.ignore()


class StepperField(QFrame):
    """값 [단위] 형태의 수치 입력 필드 (목업 .kv .field)"""

    value_changed = Signal()

    _UNIT_WIDTH: int = 16

    def __init__(
        self,
        parent: QWidget,
        value: str = "0",
        unit: str = "",
        on_changed: Callable[[], None] | None = None,
        max_width: int = 0,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charKVField")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(0)

        # 단위가 있으면 좌측에 동일 폭 여백을 두어 숫자가 전체 폭 기준 가운데 정렬되게 한다
        if unit:
            left_spacer: QWidget = QWidget(self)
            left_spacer.setFixedWidth(self._UNIT_WIDTH)
            layout.addWidget(left_spacer)

        # 수치 입력
        self.input: QLineEdit = QLineEdit(value, self)
        self.input.setObjectName("charKVInput")
        self.input.setFont(CustomFont(11))
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input.setMinimumWidth(0)
        self.input.setValidator(QDoubleValidator(0.0, 1_000_000.0, 2, self))
        self.input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.input, 1)

        # 단위 라벨 (좌측 여백과 동일 폭으로 좌우 대칭 유지)
        if unit:
            unit_label: QLabel = QLabel(unit, self)
            unit_label.setObjectName("charKVUnit")
            unit_label.setFont(CustomFont(9))
            unit_label.setFixedWidth(self._UNIT_WIDTH)
            unit_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            layout.addWidget(unit_label)

        self.setFixedHeight(34)
        self.setMaximumWidth(max_width if max_width else 132)

        self._on_changed: Callable[[], None] | None = on_changed
        if on_changed:
            self.value_changed.connect(on_changed)

    def number(self) -> float:
        """현재 입력 수치 (숫자 변환 실패 시 0)"""

        text: str = self.input.text().replace(",", "").strip()
        try:
            return float(text)
        except ValueError:
            return 0.0

    def set_number(self, value: float) -> None:
        """수치 설정 (정수면 정수 형태로 표시)"""

        text: str = str(int(value)) if value == int(value) else str(value)
        self.input.setText(text)

    def add(self, delta: float) -> None:
        """현재 값에 가감"""

        self.set_number(max(0.0, self.number() + delta))

    def _on_text_changed(self, _text: str) -> None:
        """입력 변경 시그널 전달"""

        self.value_changed.emit()


class CharCard(QFrame):
    """캐릭터 탭 내부 카드 컨테이너 (제목 헤더 + 콘텐츠 영역)"""

    def __init__(self, parent: QWidget, title: str) -> None:
        super().__init__(parent)

        self.setObjectName("charCard")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 18, 18, 18)
        self._layout.setSpacing(12)

        # 헤더 (제목 + 우측 추가 위젯)
        self._head = QHBoxLayout()
        self._head.setContentsMargins(0, 0, 0, 0)
        self._head.setSpacing(10)

        self._title_label: QLabel = QLabel(title, self)
        self._title_label.setObjectName("charCardTitle")
        self._title_label.setFont(CustomFont(13, bold=True))
        self._head.addWidget(self._title_label)
        self._head.addStretch(1)

        self._layout.addLayout(self._head)

    def add_header_widget(self, widget: QWidget) -> None:
        """헤더 우측에 위젯 추가"""

        self._head.addWidget(widget)

    def add_widget(self, widget: QWidget) -> None:
        """콘텐츠 영역에 위젯 추가"""

        self._layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        """콘텐츠 영역에 레이아웃 추가"""

        self._layout.addLayout(layout)


class QuickChip(QPushButton):
    """+1/+5/+10/+100 빠른 가감 칩"""

    def __init__(
        self, parent: QWidget, text: str, on_click: Callable[[], None]
    ) -> None:
        super().__init__(text, parent)

        self.setObjectName("charChip")
        self.setFont(CustomFont(9))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(on_click)


class PillTab(QPushButton):
    """라벨만 표시하는 알약 탭 버튼"""

    def __init__(
        self,
        parent: QWidget,
        label: str,
        dot_color: str,
        index: int,
        on_click: Callable[[int], None],
    ) -> None:
        super().__init__(label, parent)

        self.setObjectName("charTab")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(CustomFont(10))

        self.clicked.connect(lambda: on_click(index))


class SegButton(QFrame):
    """세그먼트 버튼 (경지/등급 선택). sub_text 가 있으면 작은 보조 라벨 표시

    QPushButton 내부 라벨이 표시되지 않는 문제를 피하기 위해 QFrame 기반으로 구현.
    """

    def __init__(
        self,
        parent: QWidget,
        text: str,
        index: int,
        on_click: Callable[[int], None],
        sub_text: str = "",
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charSegBtn")
        self.setProperty("checked", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._index: int = index
        self._on_click: Callable[[int], None] = on_click

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(1)

        main_label: QLabel = QLabel(text, self)
        main_label.setObjectName("charSegMain")
        main_label.setFont(CustomFont(10, bold=True))
        main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(main_label)

        if sub_text:
            self.sub_label: QLabel = QLabel(sub_text, self)
            self.sub_label.setObjectName("charSegSub")
            self.sub_label.setFont(CustomFont(8))
            self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.sub_label)

    def setChecked(self, checked: bool) -> None:
        """선택 상태 스타일 갱신"""

        self.setProperty("checked", checked)
        self.style().unpolish(self)
        self.style().polish(self)

    def isChecked(self) -> bool:
        """선택 상태 반환"""

        return bool(self.property("checked"))

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """클릭 시 선택 콜백 호출"""

        self._on_click(self._index)
        super().mousePressEvent(event)


class GradeBadge(QLabel):
    """등급 색 뱃지"""

    def __init__(
        self, parent: QWidget, grade: str, color: str, dot: bool = False
    ) -> None:
        super().__init__("" if dot else grade, parent)

        self.setObjectName("charGradeBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # 텍스트 없이 색 점만 표시하는 모드
        if dot:
            size: int = 12
            self.setFixedSize(size, size)
            self.setStyleSheet(
                f"background-color: {color}; border-radius: {size // 2}px;"
            )
            return

        self.setFont(CustomFont(8, bold=True))
        self.setStyleSheet(
            f"background-color: {color}; color: white;"
            "border-radius: 8px; padding: 2px 8px;"
        )


class ColorOrb(QLabel):
    """영단/환 색 구슬"""

    def __init__(self, parent: QWidget, color: str, size: int = 26) -> None:
        super().__init__(parent)

        self.setFixedSize(size, size)
        radius: int = size // 2
        # 단순 radial gradient 로 입체감 표현 (QSS 범위 내)
        self.setStyleSheet(
            "background: qradialgradient(cx:0.35, cy:0.3, radius:0.8, "
            f"fx:0.35, fy:0.3, stop:0 #ffffff, stop:1 {color});"
            f"border-radius: {radius}px; border: 1px solid rgba(0,0,0,0.15);"
        )


class ToggleSwitch(QPushButton):
    """on/off 토글 스위치 (환 사용 여부)"""

    def __init__(
        self,
        parent: QWidget,
        active: bool,
        on_toggle: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charSwitch")
        self.setCheckable(True)
        self.setChecked(active)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(42, 24)
        self._on_toggle: Callable[[bool], None] | None = on_toggle
        self._sync_text()
        self.clicked.connect(self._handle_toggle)

    def _handle_toggle(self) -> None:
        """토글 시 상태 반영"""

        self._sync_text()
        if self._on_toggle:
            self._on_toggle(self.isChecked())

    def _sync_text(self) -> None:
        """on/off 표시용 텍스트 (핸들 위치 표현)"""

        self.setText("　●" if self.isChecked() else "●　")


class FlowLayout(QLayout):
    """폭에 따라 자식 위젯을 자동 줄바꿈하는 레이아웃 (Qt 공식 예제 이식)"""

    def __init__(
        self,
        parent: QWidget | None = None,
        margin: int = 0,
        spacing: int = 12,
        center: bool = False,
    ) -> None:
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

        self._items: list[QLayoutItem] = []
        self._center: bool = center

    def __del__(self) -> None:
        while self._items:
            self._items.pop()

    def addItem(self, item: QLayoutItem) -> None:  # type: ignore[override]
        self._items.append(item)

    def count(self) -> int:  # type: ignore[override]
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # type: ignore[override]
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        size: QSize = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """줄바꿈 배치 수행 후 총 높이 반환"""

        margins: QMargins = self.contentsMargins()
        effective: QRect = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        spacing: int = self.spacing()

        # 1) 한 줄에 들어갈 아이템들을 행 단위로 묶는다
        rows: list[tuple[list[QLayoutItem], int, int]] = []
        current: list[QLayoutItem] = []
        row_width: int = 0
        row_height: int = 0
        for item in self._items:
            item_width: int = item.sizeHint().width()
            item_height: int = item.sizeHint().height()
            added_width: int = item_width if not current else spacing + item_width
            if current and row_width + added_width > effective.width():
                rows.append((current, row_width, row_height))
                current = []
                row_width = 0
                row_height = 0
                added_width = item_width
            current.append(item)
            row_width += added_width
            row_height = max(row_height, item_height)

        if current:
            rows.append((current, row_width, row_height))

        # 2) 행별로 배치 (center 모드면 행을 가로 가운데 정렬)
        y: int = effective.y()
        for index, (items, line_width, line_height) in enumerate(rows):
            if index > 0:
                y += spacing
            if self._center:
                x: int = effective.x() + max(0, (effective.width() - line_width) // 2)
            else:
                x = effective.x()
            for item in items:
                if not test_only:
                    item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                x += item.sizeHint().width() + spacing
            y += line_height

        return y - rect.y() + margins.bottom()
