"""영단 탭 (FlowLayout 카드 그리드)"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont
from app.scripts.ui.character_ui import sample_data
from app.scripts.ui.character_ui.widgets import CharCard, ColorOrb, FlowLayout


class _ElixirCard(QFrame):
    """영단 1종 카드 (구슬 + 이름 + 효과 + 카운터)"""

    def __init__(self, parent: QWidget, data: sample_data.ElixirData) -> None:
        super().__init__(parent)

        self.setObjectName("charPillCard")
        self.setProperty("on", data.count > 0)
        self.setFixedWidth(170)

        self._data: sample_data.ElixirData = data

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 상단: 구슬 + 이름
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(ColorOrb(self, data.color))
        name_label: QLabel = QLabel(data.name, self)
        name_label.setObjectName("charPillName")
        name_label.setFont(CustomFont(11, bold=True))
        top.addWidget(name_label)
        top.addStretch(1)
        layout.addLayout(top)

        # 효과
        effect_label: QLabel = QLabel(data.effect, self)
        effect_label.setObjectName("charPillEff")
        effect_label.setFont(CustomFont(9))
        effect_label.setWordWrap(True)
        effect_label.setMinimumHeight(32)
        layout.addWidget(effect_label)

        # 카운터
        counter = QHBoxLayout()
        counter.setSpacing(8)

        minus_btn: QPushButton = QPushButton("−", self)
        minus_btn.setObjectName("charCounterBtn")
        minus_btn.clicked.connect(lambda: self._add(-1))

        self._count_label: QLabel = QLabel(self._count_text(), self)
        self._count_label.setObjectName("charCounterValue")
        self._count_label.setFont(CustomFont(10, bold=True))
        self._count_label.setAlignment(self._count_label.alignment())

        plus_btn: QPushButton = QPushButton("+", self)
        plus_btn.setObjectName("charCounterBtn")
        plus_btn.clicked.connect(lambda: self._add(1))

        counter.addWidget(minus_btn)
        counter.addWidget(self._count_label, 1)
        counter.addWidget(plus_btn)
        layout.addLayout(counter)

    def _count_text(self) -> str:
        """현재 보유 수 표시 문구"""

        return f"{self._data.count}  / {sample_data.ELIXIR_MAX}"

    def _add(self, delta: int) -> None:
        """보유 수 가감 후 표시·강조 갱신"""

        self._data.count = max(0, min(sample_data.ELIXIR_MAX, self._data.count + delta))
        self._count_label.setText(self._count_text())
        self.setProperty("on", self._data.count > 0)
        self.style().unpolish(self)
        self.style().polish(self)


class ElixirTab(QFrame):
    """영단 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card: CharCard = CharCard(self, "영단")

        grid_container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(grid_container, margin=0, spacing=12)
        for data in sample_data.default_elixirs():
            flow.addWidget(_ElixirCard(grid_container, data))
        grid_container.setLayout(flow)

        card.add_widget(grid_container)
        layout.addWidget(card)
        layout.addStretch(1)
