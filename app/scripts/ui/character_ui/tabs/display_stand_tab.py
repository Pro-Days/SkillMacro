"""진열대 탭"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import STAT_SPECS
from app.scripts.character_data import (
    DISPLAY_STAND_COLUMN_STAT_KEYS,
    DISPLAY_STAND_SPECS,
)
from app.scripts.character_models import (
    CharacterProfile,
    DisplayStand,
    DisplayStandColumn,
    DisplayStandEntry,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.constants import DISPLAY_STAND_COLUMNS
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    FlowLayout,
    NormalizingLineEdit,
)


def _column_stat_label(column: DisplayStandColumn) -> str:
    """진열대 열의 표시 스탯 이름 (열→스탯 매핑에서 파생)"""

    return "·".join(
        STAT_SPECS[stat_key] for stat_key in DISPLAY_STAND_COLUMN_STAT_KEYS[column]
    )


def _column_is_percent(column: DisplayStandColumn) -> bool:
    """진열대 열 합계 표시에 % 단위를 붙일지 여부"""

    first_stat_key = DISPLAY_STAND_COLUMN_STAT_KEYS[column][0]
    return "(%)" in STAT_SPECS[first_stat_key]


class _NumericDelegate(QStyledItemDelegate):
    """셀 편집 시 숫자만 허용하는 델리게이트"""

    def createEditor(  # type: ignore[override]
        self,
        parent: QWidget,
        _option: QStyleOptionViewItem,
        _index: QModelIndex,
    ) -> NormalizingLineEdit:
        editor: NormalizingLineEdit = NormalizingLineEdit(parent=parent)
        editor.setValidator(QDoubleValidator(0.0, 1_000_000.0, 1, editor))
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return editor

    def setModelData(  # type: ignore[override]
        self,
        editor: NormalizingLineEdit,
        model: QAbstractItemModel,
        index: QModelIndex,
    ) -> None:
        """편집 종료 시 셀 값 정규화"""

        editor.normalize_to_validator()
        model.setData(index, editor.text())


class DisplayStandTab(QFrame):
    """진열대 탭"""

    def __init__(self, parent: QWidget, on_changed: Callable[[], None]) -> None:
        super().__init__(parent)

        self._profile: CharacterProfile | None = None
        self._on_changed: Callable[[], None] = on_changed
        self._loading: bool = False
        self._column_keys: tuple[DisplayStandColumn, ...] = tuple(
            column for column, _title in DISPLAY_STAND_COLUMNS
        )

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

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        self._loading = True
        self._profile = profile
        self.setEnabled(profile is not None)

        for row_index, spec in enumerate(DISPLAY_STAND_SPECS):
            for col_index, column in enumerate(self._column_keys):
                item: QTableWidgetItem = self._table.item(row_index, col_index)
                value: float = 0.0
                if profile is not None and spec.stand in profile.display_stand.entries:
                    entry: DisplayStandEntry = profile.display_stand.entries[spec.stand]
                    value = entry.values[column] if column in entry.values else 0.0

                item.setText(self._format(value))

        self._loading = False
        self._recalc()

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

        self._value_input: NormalizingLineEdit = NormalizingLineEdit("0", self)
        self._value_input.setObjectName("charMiniNum")
        self._value_input.setFont(CustomFont(10))
        self._value_input.setFixedWidth(64)
        self._value_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_input.setValidator(QDoubleValidator(0.0, 1_000_000.0, 1, self))
        toolbar.addWidget(self._value_input)

        apply_btn: StyledButton = StyledButton(
            self,
            "선택 칸에 적용",
            kind="normal",
            point_size=9,
        )
        apply_btn.clicked.connect(self._apply_to_selection)
        toolbar.addWidget(apply_btn)

        return toolbar

    def _build_table(self) -> QTableWidget:
        """진열대 표 생성"""

        self._table: QTableWidget = QTableWidget(
            len(DISPLAY_STAND_SPECS),
            len(DISPLAY_STAND_COLUMNS),
            self,
        )
        self._table.setObjectName("charShelfTable")
        self._table.setItemDelegate(_NumericDelegate(self._table))
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self._table.setVerticalHeaderLabels([spec.name for spec in DISPLAY_STAND_SPECS])
        self._table.setHorizontalHeaderLabels(
            [
                f"{title}\n{_column_stat_label(column)}"
                for column, title in DISPLAY_STAND_COLUMNS
            ]
        )
        self._table.setMaximumHeight(360)
        self._table.setMinimumWidth(0)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(header.ResizeMode.Stretch)
        header.sectionClicked.connect(self._table.selectColumn)
        header.setCursor(Qt.CursorShape.PointingHandCursor)

        vheader = self._table.verticalHeader()
        vheader.setDefaultSectionSize(34)
        vheader.setSectionResizeMode(vheader.ResizeMode.Fixed)

        self._table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)

        corner: QAbstractButton | None = self._table.findChild(QAbstractButton)
        if corner is not None:
            corner.setCursor(Qt.CursorShape.PointingHandCursor)
            corner.clicked.connect(self._clear_selection)

        for row_index in range(len(DISPLAY_STAND_SPECS)):
            for col_index in range(len(DISPLAY_STAND_COLUMNS)):
                item: QTableWidgetItem = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row_index, col_index, item)

        self._table.itemChanged.connect(self._on_item_changed)
        self._table.itemSelectionChanged.connect(self._update_selection_info)
        return self._table

    def _build_summary(self) -> QFrame:
        """하단 합계 요약"""

        summary: QFrame = QFrame(self)
        summary.setObjectName("charBudget")
        layout: FlowLayout = FlowLayout(summary, margin=0, spacing=18)
        layout.setContentsMargins(16, 12, 16, 12)

        self._summary_values: dict[DisplayStandColumn, QLabel] = {}
        for column in self._column_keys:
            item: QFrame = QFrame(summary)
            box = QVBoxLayout(item)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(2)

            caption: QLabel = QLabel(_column_stat_label(column), item)
            caption.setObjectName("charBudgetLabel")
            caption.setFont(CustomFont(8, bold=True))

            value: QLabel = QLabel("+0", item)
            value.setObjectName("charBudgetValue")
            value.setFont(CustomFont(12, bold=True))

            box.addWidget(caption)
            box.addWidget(value)
            self._summary_values[column] = value
            layout.addWidget(item)

        summary.setLayout(layout)
        return summary

    def _format(self, value: float) -> str:
        """수치 표시"""

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
        for row_index, spec in enumerate(DISPLAY_STAND_SPECS):
            self._table.setRowHidden(row_index, keyword not in spec.name)

    def _apply_to_selection(self) -> None:
        """선택된 셀에 값 일괄 적용"""

        self._value_input.normalize_to_validator()
        value_text: str = self._format(self._parse(self._value_input.text()))
        for item in self._table.selectedItems():
            item.setText(value_text)

    def _clear_selection(self) -> None:
        """좌상단 코너 클릭 시 선택 해제 후 화면 반영"""

        self._table.clearSelection()
        self._table.setCurrentCell(-1, -1)
        self._update_selection_info()
        self._table.horizontalHeader().viewport().update()

    def _update_selection_info(self) -> None:
        """선택 칸 수 갱신"""

        self._selection_label.setText(f"선택 {len(self._table.selectedItems())}칸")
        self._table.viewport().update()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """셀 변경 시 해당 칸만 모델 반영"""

        self._recalc()
        if self._profile is None or self._loading:
            return

        spec = DISPLAY_STAND_SPECS[item.row()]
        column: DisplayStandColumn = self._column_keys[item.column()]
        value: float = self._parse(item.text())
        entries: dict[DisplayStand, DisplayStandEntry] = (
            self._profile.display_stand.entries
        )

        # 0 값은 저장하지 않고, 비어 버린 진열대 엔트리는 제거한다
        if value <= 0.0:
            entry: DisplayStandEntry | None = entries.get(spec.stand)
            if entry is not None:
                entry.values.pop(column, None)
                if not entry.values:
                    entries.pop(spec.stand, None)
        else:
            entries.setdefault(spec.stand, DisplayStandEntry()).values[column] = value

        self._on_changed()

    def _recalc(self) -> None:
        """열별 합계 갱신"""

        sums: dict[DisplayStandColumn, float] = {
            column: 0.0 for column in self._column_keys
        }
        for row_index in range(self._table.rowCount()):
            for col_index, column in enumerate(self._column_keys):
                item: QTableWidgetItem = self._table.item(row_index, col_index)
                sums[column] += self._parse(item.text())

        for column, value_label in self._summary_values.items():
            rounded: float = round(sums[column], 1)
            number: str = str(int(rounded)) if rounded == int(rounded) else str(rounded)
            suffix: str = "%" if _column_is_percent(column) else ""
            value_label.setText(f"+{number}{suffix}")
