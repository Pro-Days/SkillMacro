"""우측 전체 스탯 패널

공식 전투력과 전체 스탯 그리드를 표시한다. (현재는 정적 샘플 값)
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont
from app.scripts.ui.character_ui import sample_data


class LiveStatsPanel(QFrame):
    """우측 전체 스탯 패널"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setObjectName("charPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 내부 세로 스크롤
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

        # 공식 전투력
        power_row = QHBoxLayout()
        power_row.setContentsMargins(0, 12, 0, 4)

        power_label: QLabel = QLabel("공식 전투력", self)
        power_label.setObjectName("charSub")
        power_label.setFont(CustomFont(9))

        power_value: QLabel = QLabel(sample_data.OFFICIAL_POWER_TEXT, self)
        power_value.setObjectName("charPowerValue")
        power_value.setFont(CustomFont(15, bold=True))
        power_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        power_row.addWidget(power_label)
        power_row.addStretch(1)
        power_row.addWidget(power_value)
        layout.addLayout(power_row)

        # 스탯 그리드 (2열)
        grid = QGridLayout()
        grid.setContentsMargins(0, 14, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        for i, (label, value) in enumerate(sample_data.STAT_ROWS):
            row: int = i // 2
            col: int = i % 2
            grid.addWidget(self._build_cell(label, value), row, col)

        layout.addLayout(grid)
        layout.addStretch(1)

    def _build_cell(self, label: str | None, value: str | None) -> QWidget:
        """스탯 셀 위젯 생성 (label 이 None 이면 빈 셀)"""

        cell: QFrame = QFrame(self)
        if label is None or value is None:
            cell.setObjectName("charStatCellEmpty")
            return cell

        cell.setObjectName("charStatCell")
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(9, 6, 9, 6)
        cell_layout.setSpacing(4)

        name_label: QLabel = QLabel(label, cell)
        name_label.setObjectName("charStatLabel")
        name_label.setFont(CustomFont(8))
        name_label.setWordWrap(True)

        value_label: QLabel = QLabel(value, cell)
        value_label.setObjectName("charStatValue")
        value_label.setFont(CustomFont(8, bold=True))
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        cell_layout.addWidget(name_label)
        cell_layout.addStretch(1)
        cell_layout.addWidget(value_label)

        return cell
