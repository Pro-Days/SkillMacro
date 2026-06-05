"""우측 전체 스탯 패널"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import (
    OVERALL_STAT_GRID_ROWS,
    OVERALL_STAT_ORDER,
    STAT_SPECS,
    StatKey,
)
from app.scripts.character_engine import LiveStatView
from app.scripts.custom_classes import CustomFont, StyledButton


class LiveStatsPanel(QFrame):
    """우측 전체 스탯 패널"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setObjectName("charPanel")
        self._current_live_view: LiveStatView | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 내부 세로 스크롤 구성
        scroll: QScrollArea = QScrollArea(self)
        scroll.setObjectName("charPanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content: QWidget = QWidget()
        content.setObjectName("charPanelContent")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(0)

        title: QLabel = QLabel("전체 스탯", self)
        title.setObjectName("charPanelTitle")
        title.setFont(CustomFont(14, bold=True))
        layout.addWidget(title)

        # 공식 전투력 표시 행
        power_row = QHBoxLayout()
        power_row.setContentsMargins(0, 12, 0, 4)

        power_label: QLabel = QLabel("공식 전투력", self)
        power_label.setObjectName("charSub")
        power_label.setFont(CustomFont(9))

        self._power_value: QLabel = QLabel("-", self)
        self._power_value.setObjectName("charPowerValue")
        self._power_value.setFont(CustomFont(15, bold=True))
        self._power_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        power_row.addWidget(power_label)
        power_row.addStretch(1)
        power_row.addWidget(self._power_value)
        layout.addLayout(power_row)

        # 전체 스탯 그리드 구성
        grid = QGridLayout()
        grid.setContentsMargins(0, 14, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        self._value_labels: dict[StatKey, QLabel] = {}
        for row_index, row_spec in enumerate(OVERALL_STAT_GRID_ROWS):
            for col_index, stat_key in enumerate(row_spec):
                grid.addWidget(self._build_cell(stat_key), row_index, col_index)

        layout.addLayout(grid)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 14, 0, 0)
        button_row.addStretch(1)

        self._copy_button: StyledButton = StyledButton(
            self,
            "전체 스탯 복사",
            kind="normal",
            point_size=9,
        )
        self._copy_button.setEnabled(False)
        self._copy_button.clicked.connect(self._copy_stats_to_clipboard)
        button_row.addWidget(self._copy_button)
        layout.addLayout(button_row)

        layout.addStretch(1)

    def _build_cell(self, stat_key: StatKey | None) -> QWidget:
        """스탯 셀 위젯 생성"""

        cell: QFrame = QFrame(self)
        if stat_key is None:
            cell.setObjectName("charStatCellEmpty")
            return cell

        cell.setObjectName("charStatCell")
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(9, 6, 9, 6)
        cell_layout.setSpacing(4)

        name_label: QLabel = QLabel(STAT_SPECS[stat_key], cell)
        name_label.setObjectName("charStatLabel")
        name_label.setFont(CustomFont(8))
        name_label.setWordWrap(True)

        value_label: QLabel = QLabel("0", cell)
        value_label.setObjectName("charStatValue")
        value_label.setFont(CustomFont(8, bold=True))
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._value_labels[stat_key] = value_label

        cell_layout.addWidget(name_label)
        cell_layout.addStretch(1)
        cell_layout.addWidget(value_label)

        return cell

    def set_live_view(self, live_view: LiveStatView | None) -> None:
        """실시간 계산 결과 표시"""

        self._current_live_view = live_view

        # 선택 캐릭터가 없는 경우 빈 값 표시
        if live_view is None:
            self._power_value.setText("-")
            for value_label in self._value_labels.values():
                value_label.setText("0")

            self._copy_button.setEnabled(False)
            return

        # 공식 전투력 표시
        self._power_value.setText(f"{live_view.official_power:,.0f}")
        self._copy_button.setEnabled(True)

        # 최종 스탯 표시
        for stat_key, value_label in self._value_labels.items():
            value: float = live_view.final.values[stat_key]
            value_label.setText(f"{value:g}")

    def _copy_stats_to_clipboard(self) -> None:
        """현재 전체 스탯 클립보드 복사"""

        if self._current_live_view is None:
            return

        lines: list[str] = []
        for stat_key in OVERALL_STAT_ORDER:
            label: str = STAT_SPECS[stat_key]
            value: float = self._current_live_view.final.values[stat_key]
            value_text: str = f"{value:.2f}".rstrip("0").rstrip(".")
            lines.append(f"{label}\t{value_text}")

        clipboard: QClipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText("\n".join(lines))

        self._copy_button.setText("복사됨!")
        QTimer.singleShot(
            1500,
            lambda: self._copy_button.setText("전체 스탯 복사"),
        )
