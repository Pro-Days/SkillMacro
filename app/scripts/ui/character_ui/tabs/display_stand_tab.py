"""진열대 탭 (QTableWidget 스프레드시트형 다중선택)"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui import sample_data
from app.scripts.ui.character_ui.widgets import CharCard, FlowLayout

_COLUMN_COUNT: int = 5


class _NumericDelegate(QStyledItemDelegate):
    """셀 편집 시 숫자만 허용하는 델리게이트"""

    def createEditor(self, parent, option, index):  # type: ignore[override]
        editor: QLineEdit = QLineEdit(parent)
        editor.setValidator(QDoubleValidator(0.0, 1_000_000.0, 1, editor))
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return editor


class DisplayStandTab(QFrame):
    """진열대 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card: CharCard = CharCard(self, "진열대")

        card.add_layout(self._build_toolbar())
        card.add_widget(self._build_table())
        card.add_widget(self._build_summary())

        layout.addWidget(card)
        layout.addStretch(1)

        self._recalc()
        self._update_selection_info()

    def _build_toolbar(self) -> QHBoxLayout:
        """검색 / 선택 정보 / 값 / 적용 버튼 툴바"""

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self._search: QLineEdit = QLineEdit(self)
        self._search.setObjectName("charSearch")
        self._search.setPlaceholderText("진열대 이름 검색…")
        self._search.setFont(CustomFont(10))
        self._search.textChanged.connect(self._filter)
        toolbar.addWidget(self._search, 1)

        self._selection_label: QLabel = QLabel("선택 0칸", self)
        self._selection_label.setObjectName("charHint")
        self._selection_label.setFont(CustomFont(9))
        toolbar.addWidget(self._selection_label)

        self._value_input: QLineEdit = QLineEdit("0", self)
        self._value_input.setObjectName("charMiniNum")
        self._value_input.setFont(CustomFont(10))
        self._value_input.setFixedWidth(64)
        self._value_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_input.setValidator(QDoubleValidator(0.0, 1_000_000.0, 1, self))
        toolbar.addWidget(self._value_input)

        apply_btn: StyledButton = StyledButton(
            self, "선택 칸에 적용", kind="normal", point_size=9
        )
        apply_btn.clicked.connect(self._apply_to_selection)
        toolbar.addWidget(apply_btn)

        return toolbar

    def _build_table(self) -> QTableWidget:
        """진열대 표 생성"""

        rows: list[tuple[str, list[float]]] = sample_data.shelf_rows()

        self._table: QTableWidget = QTableWidget(len(rows), _COLUMN_COUNT, self)
        self._table.setObjectName("charShelfTable")
        self._table.setItemDelegate(_NumericDelegate(self._table))
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self._table.setVerticalHeaderLabels([name for name, _ in rows])
        self._table.setHorizontalHeaderLabels(
            [f"{title}\n{desc}" for title, desc in sample_data.SHELF_COLUMNS]
        )
        self._table.setMaximumHeight(360)
        # 표가 좁아지면 페이지가 아니라 표 내부에서 가로 스크롤
        self._table.setMinimumWidth(0)

        # 열 머리글 클릭 시 해당 열 전체 선택 (클릭 가능 표시로 손가락 커서)
        header: QHeaderView = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.sectionClicked.connect(self._table.selectColumn)
        header.setCursor(Qt.CursorShape.PointingHandCursor)

        # 행 높이는 사용자가 드래그로 바꾸지 못하도록 고정
        vheader: QHeaderView = self._table.verticalHeader()
        vheader.setDefaultSectionSize(34)
        vheader.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        # 셀(뷰포트)도 선택 가능 표시로 손가락 커서
        self._table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)

        # 좌상단 코너 클릭 시 선택 해제가 화면에 반영되도록 직접 처리
        corner: QAbstractButton | None = self._table.findChild(QAbstractButton)
        if corner is not None:
            corner.setCursor(Qt.CursorShape.PointingHandCursor)
            corner.clicked.connect(self._clear_selection)

        for row_index, (_name, values) in enumerate(rows):
            for col_index in range(_COLUMN_COUNT):
                item: QTableWidgetItem = QTableWidgetItem(
                    self._format(values[col_index])
                )
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row_index, col_index, item)

        self._table.itemChanged.connect(self._recalc)
        self._table.itemSelectionChanged.connect(self._update_selection_info)
        return self._table

    def _build_summary(self) -> QFrame:
        """하단 합계 요약"""

        summary: QFrame = QFrame(self)
        summary.setObjectName("charBudget")
        # 폭이 좁으면 합계 항목이 줄바꿈되도록 FlowLayout 사용
        layout: FlowLayout = FlowLayout(summary, margin=0, spacing=18)
        layout.setContentsMargins(16, 12, 16, 12)

        labels: tuple[str, ...] = (
            "경험치 획득량%",
            "공격력",
            "드랍률%",
            "공격력%",
            "세트효과(힘·민·생·행%)",
        )
        self._summary_values: list[QLabel] = []
        for label_text in labels:
            item: QFrame = QFrame(summary)
            box = QVBoxLayout(item)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(2)
            caption: QLabel = QLabel(label_text, item)
            caption.setObjectName("charBudgetLabel")
            caption.setFont(CustomFont(8, bold=True))
            value: QLabel = QLabel("+0", item)
            value.setObjectName("charBudgetValue")
            value.setFont(CustomFont(12, bold=True))
            box.addWidget(caption)
            box.addWidget(value)
            self._summary_values.append(value)
            layout.addWidget(item)
        summary.setLayout(layout)
        return summary

    def _format(self, value: float) -> str:
        """수치 표시 (정수면 정수)"""

        return str(int(value)) if value == int(value) else str(value)

    def _parse(self, text: str) -> float:
        """셀 텍스트 숫자 변환"""

        try:
            return float(text.replace(",", "").strip())
        except ValueError:
            return 0.0

    def _filter(self, query: str) -> None:
        """이름 검색으로 행 숨김/표시"""

        keyword: str = query.strip()
        for row_index in range(self._table.rowCount()):
            name: str = sample_data.SHELF_NAMES[row_index]
            self._table.setRowHidden(row_index, keyword not in name)

    def _apply_to_selection(self) -> None:
        """선택된 셀에 값 일괄 적용"""

        value_text: str = self._format(self._parse(self._value_input.text()))
        for item in self._table.selectedItems():
            item.setText(value_text)

    def _clear_selection(self) -> None:
        """좌상단 코너 클릭 시 선택 해제 후 화면 반영"""

        self._table.clearSelection()
        self._table.setCurrentCell(-1, -1)
        # 선택 변경 시그널에 의존하지 않고 라벨·헤더 볼드·셀을 즉시 갱신
        self._update_selection_info()
        self._table.horizontalHeader().viewport().update()

    def _update_selection_info(self) -> None:
        """선택 칸 수 갱신"""

        self._selection_label.setText(f"선택 {len(self._table.selectedItems())}칸")
        # 선택 상태 변화가 즉시 표에 반영되도록 다시 그린다
        self._table.viewport().update()

    def _recalc(self) -> None:
        """열별 합계 갱신"""

        sums: list[float] = [0.0] * _COLUMN_COUNT
        for row_index in range(self._table.rowCount()):
            for col_index in range(_COLUMN_COUNT):
                item: QTableWidgetItem | None = self._table.item(row_index, col_index)
                if item is not None:
                    sums[col_index] += self._parse(item.text())

        # 표시: 경험치%/공격력/드랍률%/공격력%/세트 순
        suffixes: tuple[str, ...] = ("%", "", "%", "%", "%")
        for i, value_label in enumerate(self._summary_values):
            rounded: float = round(sums[i], 1)
            number: str = str(int(rounded)) if rounded == int(rounded) else str(rounded)
            value_label.setText(f"+{number}{suffixes[i]}")
