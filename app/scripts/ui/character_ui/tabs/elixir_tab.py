"""영단 탭 (FlowLayout 카드 그리드)"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont
from app.scripts.ui.character_ui import sample_data
from app.scripts.ui.character_ui.widgets import CharCard, ColorOrb, FlowLayout, StepperField


class _ElixirCard(QFrame):
    """영단 1종 카드 (구슬 + 이름 + 효과 + 카운터)"""

    def __init__(self, parent: QWidget, data: sample_data.ElixirData) -> None:
        super().__init__(parent)

        self.setObjectName("charPillCard")
        self.setProperty("on", data.count > 0)
        self.setFixedWidth(150)

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

        # 카운터 (숫자 입력 + 최대 보유 수 표시)
        counter = QHBoxLayout()
        counter.setSpacing(8)

        self._count_field: StepperField = StepperField(self, str(self._data.count))
        self._count_field.value_changed.connect(self._on_count)

        max_label: QLabel = QLabel(f"/ {sample_data.ELIXIR_MAX}", self)
        max_label.setObjectName("charMuted")
        max_label.setFont(CustomFont(9))

        counter.addWidget(self._count_field, 1)
        counter.addWidget(max_label)
        layout.addLayout(counter)

    def _on_count(self) -> None:
        """입력 보유 수 반영 후 강조 갱신 (0~최대 범위)"""

        count: int = max(0, min(sample_data.ELIXIR_MAX, int(self._count_field.number())))
        self._data.count = count
        self.setProperty("on", count > 0)
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
        flow: FlowLayout = FlowLayout(grid_container, margin=0, spacing=12, center=True)
        for data in sample_data.default_elixirs():
            flow.addWidget(_ElixirCard(grid_container, data))
        grid_container.setLayout(flow)

        card.add_widget(grid_container)
        layout.addWidget(card)
        layout.addStretch(1)
