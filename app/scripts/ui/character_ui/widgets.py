"""캐릭터 창 전용 공용 위젯

목업 고유 컴포넌트(KV 스텝퍼, 빠른가감 칩, 알약 탭, 세그 버튼, 등급 뱃지,
색 구슬, 토글 스위치)와 카드 자동 래핑용 FlowLayout 을 정의한다.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QDoubleValidator,
    QFocusEvent,
    QIntValidator,
    QValidator,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, StyledButton


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


class NormalizingLineEdit(QLineEdit):
    """validator 기준 편집 종료 정규화 입력칸"""

    value_committed = Signal()

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)

        self._committed_text: str = text
        self.editingFinished.connect(self._commit_value)

    def normalize_to_validator(self) -> None:
        """입력 종료 시 validator 범위로 표시값 정리"""

        validator: QValidator | None = self.validator()
        if isinstance(validator, QIntValidator):
            int_value: int = int(self._number())
            int_value = min(max(int_value, validator.bottom()), validator.top())
            self.setText(str(int_value))
            return

        if isinstance(validator, QDoubleValidator):
            float_value: float = self._number()
            float_value = min(max(float_value, validator.bottom()), validator.top())
            decimals: int = validator.decimals()
            if decimals >= 0:
                float_value = round(float_value, decimals)

            self.setText(self._format_number(float_value))

    def _number(self) -> float:
        """현재 텍스트 숫자 변환"""

        text: str = self.text().replace(",", "").strip()
        try:
            return float(text)

        except ValueError:
            return 0.0

    def _format_number(self, value: float) -> str:
        """정수값은 정수 형태로 표시"""

        return str(int(value)) if value == int(value) else str(value)

    def set_committed_text(self, text: str) -> None:
        """표시값과 확정값을 함께 설정"""

        self.setText(text)
        self._committed_text = text

    def _commit_value(self) -> None:
        """정규화 후 실제로 달라진 값만 확정"""

        self.normalize_to_validator()
        text: str = self.text()
        if text == self._committed_text:
            return

        self._committed_text = text
        self.value_committed.emit()

    def focusOutEvent(self, event: QFocusEvent) -> None:  # type: ignore[override]
        """포커스 이탈 시 validator 상태와 무관하게 표시값 정리"""

        self.normalize_to_validator()
        super().focusOutEvent(event)


class StepperField(QFrame):
    """값 [단위] 형태의 수치 입력 필드 (목업 .kv .field)"""

    value_changed = Signal()

    _UNIT_WIDTH: int = 16

    def __init__(
        self,
        parent: QWidget,
        value: str = "0",
        unit: str = "",
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
        self.input: NormalizingLineEdit = NormalizingLineEdit(value, self)
        self.input.setObjectName("charKVInput")
        self.input.setFont(CustomFont(11))
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input.setMinimumWidth(0)
        self.input.setValidator(QDoubleValidator(0.0, 1_000_000.0, 2, self))
        self.input.value_committed.connect(self.value_changed)
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
        self.input.set_committed_text(text)


class StaticValueField(QFrame):
    """읽기 전용 수치 표시 (자동 제공되는 기본 스탯 등)

    StepperField 와 같은 폭·정렬을 유지하되 입력이 아닌 표시 전용이다.
    """

    _UNIT_WIDTH: int = 16

    def __init__(self, parent: QWidget, value: str = "0", unit: str = "") -> None:
        super().__init__(parent)

        self.setObjectName("charBaseField")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(0)

        # 단위가 있으면 좌측에 동일 폭 여백을 두어 숫자가 전체 폭 기준 가운데 정렬되게 한다
        if unit:
            left_spacer: QWidget = QWidget(self)
            left_spacer.setFixedWidth(self._UNIT_WIDTH)
            layout.addWidget(left_spacer)

        self.value_label: QLabel = QLabel(value, self)
        self.value_label.setObjectName("charBaseValue")
        self.value_label.setFont(CustomFont(11))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label, 1)

        if unit:
            unit_label: QLabel = QLabel(unit, self)
            unit_label.setObjectName("charBaseUnit")
            unit_label.setFont(CustomFont(9))
            unit_label.setFixedWidth(self._UNIT_WIDTH)
            unit_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            layout.addWidget(unit_label)

        self.setFixedHeight(34)
        self.setMaximumWidth(132)

    def set_number(self, value: float) -> None:
        """표시 수치 갱신"""

        text: str = str(int(value)) if value == int(value) else str(value)
        self.value_label.setText(text)


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


class ChoiceListPanels:
    """선택 패널과 목록 패널 공용 구성"""

    def __init__(
        self,
        parent: QWidget,
        selector_title: str,
        list_title: str,
        panel_object_name: str,
        scroll_area_object_name: str,
        scroll_content_object_name: str,
        add_text: str,
        add_clicked: Callable[[], None],
        option_title: str = "",
        selector_min_width: int = 0,
        list_min_width: int = 0,
        selector_scroll_min_height: int = 150,
        list_scroll_min_height: int = 150,
    ) -> None:
        self.selector_panel: QFrame = QFrame(parent)
        self.selector_panel.setObjectName(panel_object_name)
        if selector_min_width:
            self.selector_panel.setMinimumWidth(selector_min_width)

        selector_layout = QVBoxLayout(self.selector_panel)
        selector_layout.setContentsMargins(12, 12, 12, 12)
        selector_layout.setSpacing(10)
        selector_layout.addWidget(
            self._title_label(self.selector_panel, selector_title)
        )

        self.group_container: QFrame = QFrame(self.selector_panel)
        self.group_layout = QHBoxLayout(self.group_container)
        self.group_layout.setContentsMargins(0, 0, 0, 0)
        self.group_layout.setSpacing(6)
        selector_layout.addWidget(self.group_container)

        if option_title:
            selector_layout.addWidget(
                self._title_label(self.selector_panel, option_title, point_size=10)
            )

        (
            self.option_scroll_area,
            self.option_scroll_content,
            self.option_layout,
        ) = self._scroll_box(
            self.selector_panel,
            scroll_area_object_name,
            scroll_content_object_name,
            selector_scroll_min_height,
            6,
        )
        selector_layout.addWidget(self.option_scroll_area, 1)

        self.add_button: StyledButton = StyledButton(
            self.selector_panel,
            add_text,
            kind="normal",
            point_size=9,
        )
        self.add_button.clicked.connect(add_clicked)
        selector_layout.addWidget(self.add_button)

        self.list_panel: QFrame = QFrame(parent)
        self.list_panel.setObjectName(panel_object_name)
        if list_min_width:
            self.list_panel.setMinimumWidth(list_min_width)

        list_panel_layout = QVBoxLayout(self.list_panel)
        list_panel_layout.setContentsMargins(12, 12, 12, 12)
        list_panel_layout.setSpacing(10)
        list_panel_layout.addWidget(self._title_label(self.list_panel, list_title))

        (
            self.list_scroll_area,
            self.list_scroll_content,
            self.list_layout,
        ) = self._scroll_box(
            self.list_panel,
            scroll_area_object_name,
            scroll_content_object_name,
            list_scroll_min_height,
            8,
        )
        list_panel_layout.addWidget(self.list_scroll_area, 1)

    def make_choice_button(
        self,
        parent: QWidget,
        text: str,
        object_name: str,
        point_size: int = 9,
        minimum_height: int = 30,
        checked: bool = False,
        enabled: bool = True,
    ) -> QPushButton:
        """선택형 버튼 생성"""

        button = QPushButton(text, parent)
        button.setObjectName(object_name)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setEnabled(enabled)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFont(CustomFont(point_size, bold=True))
        button.setMinimumHeight(minimum_height)
        return button

    def _title_label(
        self,
        parent: QWidget,
        text: str,
        point_size: int = 11,
    ) -> QLabel:
        """패널 제목 라벨 생성"""

        title_label: QLabel = QLabel(text, parent)
        title_label.setObjectName("charEdTitle")
        title_label.setFont(CustomFont(point_size, bold=True))
        return title_label

    def _scroll_box(
        self,
        parent: QWidget,
        area_object_name: str,
        content_object_name: str,
        minimum_height: int,
        spacing: int,
    ) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        """스크롤 영역과 콘텐츠 레이아웃 생성"""

        scroll_area: QScrollArea = QScrollArea(parent)
        scroll_area.setObjectName(area_object_name)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setMinimumHeight(minimum_height)

        scroll_content: QWidget = QWidget(scroll_area)
        scroll_content.setObjectName(content_object_name)
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(spacing)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        return scroll_area, scroll_content, scroll_layout


class PillTab(QPushButton):
    """라벨만 표시하는 알약 탭 버튼"""

    def __init__(
        self,
        parent: QWidget,
        label: str,
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


class ResponsiveColumns(QLayout):
    """공간이 넓으면 여러 열, 좁으면 한 열로 블록을 배치하는 레이아웃

    각 블록을 자신의 최소 폭(블록 최소폭과 min_column_width 중 큰 값)으로 좌→우로
    채우다가 폭이 모자라면 줄을 바꾼다. 한 줄에 들어간 블록들은 남는 폭을 나눠 가져
    빈 공간을 남기지 않는다. 따라서 두 블록을 나란히 둘 최소 공간이 생기는 즉시
    2열로 전환된다. 본문 스크롤 높이 계산을 위해 heightForWidth 를 정확히 보고한다.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        min_column_width: int = 320,
        spacing: int = 16,
        max_columns: int = 0,
        fill: bool = True,
        center: bool = False,
    ) -> None:
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

        self._items: list[QLayoutItem] = []
        self._min_column_width: int = min_column_width
        self._max_columns: int = max_columns
        # 행 내부 블록의 폭 채움 여부와 남는 폭의 중앙 정렬 여부
        self._fill: bool = fill
        self._center: bool = center

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
        width: int = 0
        height: int = 0
        spacing: int = self.spacing()
        # 한 열로 쌓았을 때 기준: 폭은 가장 넓은 블록의 배치 폭, 높이는 합
        for index, item in enumerate(self._items):
            width = max(width, self._target_width(item))
            if index > 0:
                height += spacing
            height += item.sizeHint().height()
        margins: QMargins = self.contentsMargins()
        return QSize(
            width + margins.left() + margins.right(),
            height + margins.top() + margins.bottom(),
        )

    def _target_width(self, item: QLayoutItem) -> int:
        """블록을 배치할 최소 폭 (블록 최소폭과 하한값 중 큰 값)"""

        return max(item.minimumSize().width(), self._min_column_width)

    def _pack_rows(self, available: int) -> list[list[QLayoutItem]]:
        """블록을 최소 폭 기준으로 좌→우로 채워 줄 단위로 묶는다"""

        spacing: int = self.spacing()
        rows: list[list[QLayoutItem]] = []
        current: list[QLayoutItem] = []
        used: int = 0
        for item in self._items:
            target: int = self._target_width(item)
            added: int = target if not current else spacing + target
            if current and used + added > available:
                rows.append(current)
                current = []
                used = 0
                added = target
            current.append(item)
            used += added
            if self._max_columns and len(current) >= self._max_columns:
                rows.append(current)
                current = []
                used = 0
        if current:
            rows.append(current)
        return rows

    def _item_height(self, item: QLayoutItem, width: int) -> int:
        """주어진 폭에서의 블록 높이"""

        if item.hasHeightForWidth():
            return item.heightForWidth(width)
        return item.sizeHint().height()

    def _row_widths(self, row: list[QLayoutItem], available: int) -> list[int]:
        """한 줄 블록들이 남는 폭을 나눠 갖도록 각 블록 폭을 계산한다"""

        targets: list[int] = [self._target_width(item) for item in row]
        if not self._fill:
            return targets
        count: int = len(row)
        if count == 1:
            return [available]
        spacing: int = self.spacing()
        leftover: int = max(0, available - sum(targets) - spacing * (count - 1))
        share: int = leftover // count
        widths: list[int] = [target + share for target in targets]
        # 정수 나눗셈 잔여 폭은 마지막 블록에 더해 줄 폭을 정확히 채운다
        widths[-1] += available - (sum(widths) + spacing * (count - 1))
        return widths

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """줄 단위 배치 수행 후 총 높이 반환"""

        margins: QMargins = self.contentsMargins()
        effective: QRect = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        spacing: int = self.spacing()
        available: int = effective.width()

        y: int = effective.y()
        first_row: bool = True
        for row in self._pack_rows(available):
            if not first_row:
                y += spacing
            first_row = False

            widths: list[int] = self._row_widths(row, available)
            row_height: int = 0
            for item, width in zip(row, widths):
                row_height = max(row_height, self._item_height(item, width))

            if not test_only:
                row_width: int = sum(widths) + spacing * (len(widths) - 1)
                if self._center:
                    x: int = effective.x() + max(0, (available - row_width) // 2)
                else:
                    x = effective.x()
                for item, width in zip(row, widths):
                    item.setGeometry(
                        QRect(
                            QPoint(x, y),
                            QSize(width, row_height),
                        )
                    )
                    x += width + spacing
            y += row_height

        return y - rect.y() + margins.bottom()


class ResponsiveColumnsBox(QFrame):
    """ResponsiveColumns 를 담는 컨테이너

    폭이 바뀌면 줄바꿈 수가 달라져 필요한 높이도 변하는데, 부모 레이아웃이
    이전 폭 기준 높이를 그대로 할당해 내용이 잘리는 문제가 있다. 폭이 바뀔 때마다
    현재 폭의 heightForWidth 로 자기 최소 높이를 직접 맞춰 부모가 올바른 높이를
    할당하게 한다.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        min_column_width: int = 320,
        spacing: int = 16,
        max_columns: int = 0,
        fill: bool = True,
        center: bool = False,
    ) -> None:
        super().__init__(parent)

        self._flow: ResponsiveColumns = ResponsiveColumns(
            self, min_column_width, spacing, max_columns, fill, center
        )

    @property
    def flow(self) -> ResponsiveColumns:
        """내부 ResponsiveColumns 레이아웃"""

        return self._flow

    def addWidget(self, widget: QWidget) -> None:
        """블록 추가"""

        self._flow.addWidget(widget)
        self.sync_height()

    def sync_height(self) -> None:
        """현재 폭 기준 컨테이너 높이 갱신"""

        width: int = self.width()
        if width <= 0:
            self.updateGeometry()
            return

        self.setMinimumHeight(self._flow.heightForWidth(width))
        self.updateGeometry()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.sync_height()
