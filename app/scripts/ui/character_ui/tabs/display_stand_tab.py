from __future__ import annotations

from PySide6.QtCore import QAbstractItemModel, QModelIndex, QSignalBlocker, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QInputMethodEvent,
    QKeyEvent,
    QKeySequence,
    QPainter,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import STAT_SPECS, StatKey
from app.scripts.character_data import (
    DISPLAY_STAND_COLUMN_STAT_KEYS,
    DISPLAY_STAND_EQUIPMENT_COLUMNS,
    DISPLAY_STAND_SPECS,
    DisplayStandSpec,
    display_stand_set_step,
    display_stand_step_value,
)
from app.scripts.character_models import (
    CharacterProfile,
    DisplayStandColumn,
    DisplayStandInputMode,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.refinement_data import MAX_REFINE_STEP
from app.scripts.ui.character_ui.change_handler import CharacterChangeHandler
from app.scripts.ui.character_ui.constants import DISPLAY_STAND_COLUMNS
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.themes import theme_manager
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    CharComboBox,
    FlowLayout,
    NormalizingLineEdit,
)

_COLUMN_HEADER_STAT_LABELS: dict[DisplayStandColumn, str] = {
    DisplayStandColumn.HELMET: "경험치%",
    DisplayStandColumn.ARMOR: "공격력",
    DisplayStandColumn.BELT: "드랍률%",
    DisplayStandColumn.SHOES: "공격력%",
    DisplayStandColumn.SET: "올스텟%",
}
_DISPLAY_STAND_STEP_OPTIONS: tuple[str, ...] = (
    "미진열",
    *(f"{step}강" for step in range(MAX_REFINE_STEP + 1)),
)
_MISSING_CELL_BACKGROUND_LIGHT: QColor = QColor("#FAFAFA")
_MISSING_CELL_BACKGROUND_DARK: QColor = QColor("#202030")
_MISSING_CELL_ROLE: int = int(Qt.ItemDataRole.UserRole) + 1


def _column_stat_label(column: DisplayStandColumn) -> str:
    """진열대 열의 표시 스탯 이름"""

    return "·".join(
        STAT_SPECS[stat_key] for stat_key in DISPLAY_STAND_COLUMN_STAT_KEYS[column]
    )


def _column_is_percent(column: DisplayStandColumn) -> bool:
    """진열대 열 합계 표시에 % 단위를 붙일지 여부"""

    first_stat_key: StatKey = DISPLAY_STAND_COLUMN_STAT_KEYS[column][0]
    return "(%)" in STAT_SPECS[first_stat_key]


class _StageEditor(QLineEdit):
    """키보드 숫자로 진열 단계와 단위를 입력하는 셀 편집기"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._stage: int | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._update_text()

    def set_stage(self, stage: int | None) -> None:
        """편집할 단계를 반영"""

        self._stage = stage
        self._update_text()
        self.selectAll()

    def stage(self) -> int | None:
        """현재 편집 단계 반환"""

        return self._stage

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        """숫자는 단계로 입력하고 Backspace는 마지막 자리만 제거"""

        if event.matches(QKeySequence.StandardKey.Paste):
            event.accept()
            return

        if event.key() == Qt.Key.Key_Backspace:
            if self._stage is not None:
                digits: str = str(self._stage)
                self._stage = int(digits[:-1]) if len(digits) > 1 else None
                self._update_text()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Delete:
            event.accept()
            return

        digit: str = event.text()
        if digit and digit in "0123456789":
            if self.hasSelectedText() or self._stage is None:
                candidate_text: str = digit
            else:
                candidate_text = f"{self._stage}{digit}"

            candidate: int = int(candidate_text)
            if candidate <= MAX_REFINE_STEP:
                self._stage = candidate
                self._update_text()
            event.accept()
            return

        if event.text():
            event.accept()
            return

        super().keyPressEvent(event)

    def paste(self) -> None:
        """클립보드 붙여넣기 무시"""

        return

    def inputMethodEvent(  # type: ignore[override]
        self,
        event: QInputMethodEvent,
    ) -> None:
        """입력기를 통한 텍스트 입력 무시"""

        event.accept()

    def _update_text(self) -> None:
        """현재 단계의 편집 문자열 갱신"""

        text: str = "" if self._stage is None else f"{self._stage}강"
        self.setText(text)
        if self._stage is not None:
            self.setCursorPosition(len(str(self._stage)))


class _DisplayStandDelegate(QStyledItemDelegate):
    """직접 입력과 단계 입력을 현재 모드에 맞춰 제공하는 델리게이트"""

    def __init__(self, tab: DisplayStandTab) -> None:
        super().__init__(tab._table)
        self._tab: DisplayStandTab = tab

    def paint(  # type: ignore[override]
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """스타일시트 위에 미진열 셀 배경을 표시"""

        super().paint(painter, option, index)
        if not index.data(_MISSING_CELL_ROLE):
            return

        if option.state & QStyle.StateFlag.State_Selected:
            return

        background: QColor = (
            _MISSING_CELL_BACKGROUND_DARK
            if theme_manager.is_dark
            else _MISSING_CELL_BACKGROUND_LIGHT
        )
        painter.save()
        painter.fillRect(option.rect, background)
        painter.restore()

    def createEditor(  # type: ignore[override]
        self,
        parent: QWidget,
        _option: QStyleOptionViewItem,
        _index: QModelIndex,
    ) -> QWidget:
        if self._tab._is_manual_mode():
            editor: NormalizingLineEdit = NormalizingLineEdit("", parent)
            editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return editor

        return _StageEditor(parent)

    def setEditorData(  # type: ignore[override]
        self,
        editor: QWidget,
        index: QModelIndex,
    ) -> None:
        """현재 셀의 직접 입력값 또는 단계를 편집기에 반영"""

        if isinstance(editor, NormalizingLineEdit):
            editor.setText(str(index.data(Qt.ItemDataRole.EditRole)))
            editor.selectAll()
            return

        if not isinstance(editor, _StageEditor):
            raise TypeError("unsupported display stand editor")

        editor.set_stage(self._tab._step_at(index.row(), index.column()))

    def setModelData(  # type: ignore[override]
        self,
        editor: QWidget,
        model: QAbstractItemModel,
        index: QModelIndex,
    ) -> None:
        """편집 종료 시 현재 입력 방식의 모델에 반영"""

        if isinstance(editor, NormalizingLineEdit):
            editor.normalize_to_validator()
            model.setData(index, editor.text())
            return

        if not isinstance(editor, _StageEditor):
            raise TypeError("unsupported display stand editor")

        self._tab._commit_step(index.row(), index.column(), editor.stage())


class DisplayStandTab(CharacterTab):
    """진열대 탭"""

    def __init__(
        self,
        parent: QWidget,
        changes: CharacterChangeHandler,
        profile: CharacterProfile,
    ) -> None:
        super().__init__(parent, changes, profile)
        self._column_keys: tuple[DisplayStandColumn, ...] = tuple(
            column for column, _title in DISPLAY_STAND_COLUMNS
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card: CharCard = CharCard(self, "진열대")
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        card.add_layout(self._build_toolbar())
        card.add_widget(self._build_table())
        card.add_widget(self._build_summary())

        layout.addWidget(card, 1)

        self._sync_input_widgets()
        self._render_table()
        self._recalc()
        self._update_selection_info()

    def set_profile(self, profile: CharacterProfile) -> None:
        """선택 캐릭터 모델 반영"""

        self._profile = profile
        with QSignalBlocker(self._manual_checkbox):
            self._manual_checkbox.setChecked(self._is_manual_mode())

        self._sync_input_widgets()
        self._render_table()
        self._recalc()

    def _build_toolbar(self) -> QHBoxLayout:
        """검색 / 입력 방식 / 선택 정보 / 값 / 적용 버튼 툴바"""

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self._search: QLineEdit = QLineEdit(self)
        self._search.setObjectName("charSearch")
        self._search.setPlaceholderText("진열대 이름 검색")
        self._search.setFont(CustomFont(10))
        self._search.textChanged.connect(self._filter)
        toolbar.addWidget(self._search, 1)

        self._manual_checkbox: QCheckBox = QCheckBox("직접 입력", self)
        self._manual_checkbox.setFont(CustomFont(9))
        self._manual_checkbox.setChecked(self._is_manual_mode())
        self._manual_checkbox.toggled.connect(self._set_manual_mode)
        toolbar.addWidget(self._manual_checkbox)

        self._selection_label: QLabel = QLabel("선택 0칸", self)
        self._selection_label.setObjectName("charHint")
        self._selection_label.setFont(CustomFont(9))
        toolbar.addWidget(self._selection_label)

        self._value_input: NormalizingLineEdit = NormalizingLineEdit("0", self)
        self._value_input.setObjectName("charMiniNum")
        self._value_input.setFont(CustomFont(10))
        self._value_input.setFixedWidth(64)
        self._value_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self._value_input)

        self._step_input: CharComboBox = CharComboBox(
            self,
            list(_DISPLAY_STAND_STEP_OPTIONS),
            point_size=9,
        )
        self._step_input.setFixedWidth(84)
        toolbar.addWidget(self._step_input)

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

        self._table = QTableWidget(
            len(DISPLAY_STAND_SPECS),
            len(DISPLAY_STAND_COLUMNS),
            self,
        )
        self._table.setObjectName("charShelfTable")
        self._table.setItemDelegate(_DisplayStandDelegate(self))
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self._table.setVerticalHeaderLabels([spec.name for spec in DISPLAY_STAND_SPECS])
        self._table.setHorizontalHeaderLabels(
            [
                f"{title}\n{_COLUMN_HEADER_STAT_LABELS[column]}"
                for column, title in DISPLAY_STAND_COLUMNS
            ]
        )
        self._table.setMinimumWidth(0)
        self._table.setMinimumHeight(220)
        self._table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(header.ResizeMode.Stretch)
        header.sectionClicked.connect(self._table.selectColumn)
        header.setCursor(Qt.CursorShape.PointingHandCursor)

        vheader = self._table.verticalHeader()
        vheader.setDefaultSectionSize(34)
        vheader.setSectionResizeMode(vheader.ResizeMode.Fixed)

        self._table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)

        corner: QAbstractButton | None = self._table.findChild(  # type: ignore[assignment]
            QAbstractButton
        )
        if corner is not None:
            corner.setCursor(Qt.CursorShape.PointingHandCursor)
            corner.clicked.connect(self._clear_selection)

        for row_index in range(len(DISPLAY_STAND_SPECS)):
            for col_index in range(len(DISPLAY_STAND_COLUMNS)):
                item: QTableWidgetItem = QTableWidgetItem()
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

    def _is_manual_mode(self) -> bool:
        """현재 진열대 직접 입력 여부 반환"""

        return self._profile.display_stand.input_mode == DisplayStandInputMode.MANUAL

    def _set_manual_mode(self, manual: bool) -> None:
        """진열대 입력 방식 전환"""

        input_mode: DisplayStandInputMode = (
            DisplayStandInputMode.MANUAL if manual else DisplayStandInputMode.STEP
        )
        if self._profile.display_stand.input_mode == input_mode:
            return

        self._profile.display_stand.input_mode = input_mode
        self._sync_input_widgets()
        self._render_table()
        self._recalc()
        self._changes.stats_changed()

    def _sync_input_widgets(self) -> None:
        """현재 입력 방식에 맞는 상단 일괄 입력기 표시"""

        manual: bool = self._is_manual_mode()
        self._value_input.setVisible(manual)
        self._step_input.setVisible(not manual)

    def _render_table(self) -> None:
        """현재 입력 방식의 전체 진열대 값을 표에 표시"""

        with QSignalBlocker(self._table):
            for row_index, spec in enumerate(DISPLAY_STAND_SPECS):
                for col_index, column in enumerate(self._column_keys):
                    self._refresh_item(spec, column, row_index, col_index)

    def _refresh_item(
        self,
        spec: DisplayStandSpec,
        column: DisplayStandColumn,
        row_index: int,
        col_index: int,
    ) -> None:
        """현재 입력 방식의 단일 셀 표시 갱신"""

        item: QTableWidgetItem = self._table.item(row_index, col_index)
        if self._is_manual_mode():
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setBackground(QBrush())
            item.setData(_MISSING_CELL_ROLE, False)
            entry: dict[DisplayStandColumn, float] | None = (
                self._profile.display_stand.entries.get(spec.name)
            )
            value: float = 0.0 if entry is None else entry.get(column, 0.0)
            item.setText(self._format(value))
            return

        step: int | None = self._step_at(row_index, col_index)
        if column == DisplayStandColumn.SET:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        else:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

        missing_background: QColor = (
            _MISSING_CELL_BACKGROUND_DARK
            if theme_manager.is_dark
            else _MISSING_CELL_BACKGROUND_LIGHT
        )
        item.setBackground(QBrush(missing_background) if step is None else QBrush())
        item.setData(_MISSING_CELL_ROLE, step is None)
        item.setText(self._format_step(column, step))

    def _format(self, value: float) -> str:
        """수치 표시"""

        return str(int(value)) if value == int(value) else str(value)

    def _parse(self, text: str) -> float:
        """셀 텍스트 숫자 변환"""

        try:
            return float(text.replace(",", "").strip())
        except ValueError:
            return 0.0

    def _format_step(
        self,
        column: DisplayStandColumn,
        step: int | None,
    ) -> str:
        """자동 입력 셀의 단계와 수치 표시"""

        if step is None:
            return ""

        value: float = display_stand_step_value(column, step)
        suffix: str = "%" if _column_is_percent(column) else ""
        return f"{step}강 +{self._format(value)}{suffix}"

    def _filter(self, query: str) -> None:
        """이름 검색으로 행 숨김/표시"""

        keyword: str = query.strip()
        for row_index, spec in enumerate(DISPLAY_STAND_SPECS):
            self._table.setRowHidden(row_index, keyword not in spec.name)

    def _apply_to_selection(self) -> None:
        """선택된 셀에 현재 입력기의 값 일괄 적용"""

        selected_items: list[QTableWidgetItem] = self._table.selectedItems()
        changed: bool = False
        if self._is_manual_mode():
            self._value_input.normalize_to_validator()
            value: float = self._parse(self._value_input.text())
            for item in selected_items:
                spec: DisplayStandSpec = DISPLAY_STAND_SPECS[item.row()]
                column: DisplayStandColumn = self._column_keys[item.column()]
                changed = self._set_manual_value(spec, column, value) or changed
        else:
            step: int | None = (
                None
                if self._step_input.currentIndex() == 0
                else self._step_input.currentIndex() - 1
            )
            for item in selected_items:
                spec = DISPLAY_STAND_SPECS[item.row()]
                column = self._column_keys[item.column()]
                if column == DisplayStandColumn.SET:
                    continue

                changed = self._set_step(spec, column, step) or changed

        self._render_table()
        self._recalc()
        if changed:
            self._changes.stats_changed()

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
        """직접 입력 셀 변경 시 해당 칸만 모델 반영"""

        if not self._is_manual_mode():
            return

        spec: DisplayStandSpec = DISPLAY_STAND_SPECS[item.row()]
        column: DisplayStandColumn = self._column_keys[item.column()]
        value: float = self._parse(item.text())
        if not self._set_manual_value(spec, column, value):
            return

        self._recalc()
        self._changes.stats_changed()

    def _set_manual_value(
        self,
        spec: DisplayStandSpec,
        column: DisplayStandColumn,
        value: float,
    ) -> bool:
        """진열대 직접 입력 단일 칸 모델 반영 여부 반환"""

        entries: dict[str, dict[DisplayStandColumn, float]] = (
            self._profile.display_stand.entries
        )
        entry: dict[DisplayStandColumn, float] | None = entries.get(spec.name)
        current_value: float = 0.0 if entry is None else entry.get(column, 0.0)
        if current_value == value:
            return False

        if value <= 0.0:
            if entry is not None:
                entry.pop(column, None)
                if not entry:
                    entries.pop(spec.name, None)
        else:
            if entry is None:
                entry = {}
                entries[spec.name] = entry
            entry[column] = value

        return True

    def _step_at(self, row_index: int, col_index: int) -> int | None:
        """표 위치에 저장된 자동 진열 단계 반환"""

        spec: DisplayStandSpec = DISPLAY_STAND_SPECS[row_index]
        column: DisplayStandColumn = self._column_keys[col_index]
        entry: dict[DisplayStandColumn, int] | None = (
            self._profile.display_stand.step_entries.get(spec.name)
        )
        if column == DisplayStandColumn.SET:
            return None if entry is None else display_stand_set_step(entry)

        return None if entry is None else entry.get(column)

    def _commit_step(
        self,
        row_index: int,
        col_index: int,
        step: int | None,
    ) -> None:
        """자동 단계 셀 편집 결과 반영"""

        spec: DisplayStandSpec = DISPLAY_STAND_SPECS[row_index]
        column: DisplayStandColumn = self._column_keys[col_index]
        if not self._set_step(spec, column, step):
            return

        with QSignalBlocker(self._table):
            self._refresh_item(spec, column, row_index, col_index)
            set_col_index: int = self._column_keys.index(DisplayStandColumn.SET)
            self._refresh_item(
                spec,
                DisplayStandColumn.SET,
                row_index,
                set_col_index,
            )
        self._recalc()
        self._changes.stats_changed()

    def _set_step(
        self,
        spec: DisplayStandSpec,
        column: DisplayStandColumn,
        step: int | None,
    ) -> bool:
        """진열대 자동 단계 단일 칸 모델 반영 여부 반환"""

        if column == DisplayStandColumn.SET:
            raise ValueError("display stand set step is derived")

        entries: dict[str, dict[DisplayStandColumn, int]] = (
            self._profile.display_stand.step_entries
        )
        entry: dict[DisplayStandColumn, int] | None = entries.get(spec.name)
        current_step: int | None = None if entry is None else entry.get(column)
        if current_step == step:
            return False

        if step is None:
            if entry is not None:
                entry.pop(column, None)
                if not entry:
                    entries.pop(spec.name, None)
        else:
            if entry is None:
                entry = {}
                entries[spec.name] = entry
            entry[column] = step

        return True

    def _recalc(self) -> None:
        """현재 입력 방식의 열별 합계 갱신"""

        sums: dict[DisplayStandColumn, float] = {
            column: 0.0 for column in self._column_keys
        }
        if self._is_manual_mode():
            for entry in self._profile.display_stand.entries.values():
                for column, value in entry.items():
                    sums[column] += value
        else:
            for entry in self._profile.display_stand.step_entries.values():
                for column in DISPLAY_STAND_EQUIPMENT_COLUMNS:
                    if column not in entry:
                        continue

                    step: int = entry[column]
                    sums[column] += display_stand_step_value(column, step)

                set_step: int | None = display_stand_set_step(entry)
                if set_step is not None:
                    sums[DisplayStandColumn.SET] += display_stand_step_value(
                        DisplayStandColumn.SET,
                        set_step,
                    )

        for column, value_label in self._summary_values.items():
            rounded: float = round(sums[column], 1)
            number: str = self._format(rounded)
            suffix: str = "%" if _column_is_percent(column) else ""
            value_label.setText(f"+{number}{suffix}")
