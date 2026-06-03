"""환 탭 (FlowLayout 카드 그리드)"""

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
from app.scripts.ui.character_ui.widgets import CharCard, ColorOrb, FlowLayout, ToggleSwitch


class _PillCard(QFrame):
    """환 1종 카드 (구슬 + 이름 + 효과 + 토글 스위치)"""

    def __init__(self, parent: QWidget, data: sample_data.PillData) -> None:
        super().__init__(parent)

        self.setObjectName("charPillCard")
        self.setProperty("on", data.active)
        self.setFixedWidth(170)

        self._data: sample_data.PillData = data

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

        # 하단: 사용 라벨 + 스위치
        foot = QHBoxLayout()
        foot.setSpacing(8)

        use_label: QLabel = QLabel("사용", self)
        use_label.setObjectName("charHint")
        use_label.setFont(CustomFont(9))
        foot.addWidget(use_label)
        foot.addStretch(1)
        foot.addWidget(ToggleSwitch(self, data.active, self._on_toggle))
        layout.addLayout(foot)

    def _on_toggle(self, active: bool) -> None:
        """토글 시 강조 갱신"""

        self._data.active = active
        self.setProperty("on", active)
        self.style().unpolish(self)
        self.style().polish(self)


class PillTab(QFrame):
    """환 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card: CharCard = CharCard(self, "환")

        grid_container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(grid_container, margin=0, spacing=12)
        for data in sample_data.default_pills():
            flow.addWidget(_PillCard(grid_container, data))
        grid_container.setLayout(flow)

        card.add_widget(grid_container)
        layout.addWidget(card)
        layout.addStretch(1)
