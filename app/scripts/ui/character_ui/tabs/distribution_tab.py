"""스탯·단전 분배 탭

요약바(분배 가능/사용/남은 + 진행바)는 현재 카드의 입력 합산만 표시한다.
자동 최적화 버튼은 목업대로 두되, 실제 최적화 계산은 연결하지 않는다.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui import sample_data
from app.scripts.ui.character_ui.widgets import CharCard, FlowLayout, QuickChip, StepperField

# 분배 입력 카드 1칸 고정 폭 (폭이 좁으면 FlowLayout 이 자동 줄바꿈)
_STAT_ITEM_WIDTH: int = 196
_DANJEON_ITEM_WIDTH: int = 236

# 표시용 총량 (레벨 180·현경 기준 샘플)
_STAT_TOTAL: int = 900
_DANJEON_TOTAL: int = 37


class _Budget(QFrame):
    """분배 가능/사용/남은 + 진행바 요약 위젯"""

    def __init__(self, parent: QWidget, total_label: str, total: int) -> None:
        super().__init__(parent)

        self.setObjectName("charBudget")
        self._total: int = total

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        layout.addLayout(self._build_item(total_label, str(total), value_key="total"))
        layout.addLayout(self._build_item("사용", "0", value_key="used"))
        layout.addLayout(self._build_item("남은 포인트", str(total), value_key="remain"))

        self.bar: QProgressBar = QProgressBar(self)
        self.bar.setObjectName("charBudgetBar")
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(8)
        layout.addWidget(self.bar, 1)

    def _build_item(self, label: str, value: str, value_key: str) -> QVBoxLayout:
        """라벨 + 값 묶음"""

        box = QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)

        label_widget: QLabel = QLabel(label, self)
        label_widget.setObjectName("charBudgetLabel")
        label_widget.setFont(CustomFont(8, bold=True))

        value_widget: QLabel = QLabel(value, self)
        value_widget.setObjectName("charBudgetValue")
        value_widget.setFont(CustomFont(15, bold=True))

        if value_key == "used":
            self.used_label = value_widget
        elif value_key == "remain":
            self.remain_label = value_widget

        box.addWidget(label_widget)
        box.addWidget(value_widget)
        return box

    def recalc(self, used: float) -> None:
        """사용/남은/진행바 갱신"""

        remain: float = self._total - used
        used_text: str = str(int(used)) if used == int(used) else str(used)
        remain_text: str = str(int(remain)) if remain == int(remain) else str(remain)
        self.used_label.setText(used_text)
        self.remain_label.setText(remain_text)
        self.remain_label.setProperty("over", remain < 0)
        self.remain_label.style().unpolish(self.remain_label)
        self.remain_label.style().polish(self.remain_label)
        ratio: int = 0 if self._total == 0 else min(100, int(used / self._total * 100))
        self.bar.setValue(ratio)


class DistributionTab(QFrame):
    """스탯·단전 분배 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._build_stat_card())
        layout.addWidget(self._build_danjeon_card())
        layout.addStretch(1)

    def _build_stat_card(self) -> CharCard:
        """스탯 분배 카드"""

        card: CharCard = CharCard(self, "스탯 분배")
        optimize_btn: StyledButton = StyledButton(self, "자동 최적화", kind="normal", point_size=9)
        card.add_header_widget(optimize_btn)

        self._stat_budget: _Budget = _Budget(self, "분배 가능", _STAT_TOTAL)
        card.add_widget(self._stat_budget)

        flow_container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(flow_container, margin=0, spacing=14)
        self._stat_fields: list[StepperField] = []
        for _key, label, value in sample_data.STAT_DIST:
            flow.addWidget(self._build_stat_item(label, value))
        flow_container.setLayout(flow)

        card.add_widget(flow_container)
        self._recalc_stat()
        return card

    def _build_stat_item(self, label: str, value: int) -> QWidget:
        """스탯 1종 입력 (라벨 + 스텝퍼 + 빠른가감 칩)"""

        container: QFrame = QFrame(self)
        container.setFixedWidth(_STAT_ITEM_WIDTH)
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        name_label: QLabel = QLabel(label, container)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        box.addWidget(name_label)

        field: StepperField = StepperField(container, str(value), on_changed=self._recalc_stat)
        self._stat_fields.append(field)
        box.addWidget(field)

        quick = QHBoxLayout()
        quick.setSpacing(6)
        for delta in (1, 5, 10, 100):
            chip: QuickChip = QuickChip(
                container, f"+{delta}", lambda d=delta, f=field: self._add_stat(f, d)
            )
            quick.addWidget(chip)
        box.addLayout(quick)

        return container

    def _add_stat(self, field: StepperField, delta: int) -> None:
        """빠른가감 칩 처리"""

        field.add(float(delta))

    def _recalc_stat(self) -> None:
        """스탯 합산 후 요약바 갱신"""

        used: float = sum(field.number() for field in self._stat_fields)
        self._stat_budget.recalc(used)

    def _build_danjeon_card(self) -> CharCard:
        """단전 분배 카드"""

        card: CharCard = CharCard(self, "단전 분배")
        optimize_btn: StyledButton = StyledButton(self, "자동 최적화", kind="normal", point_size=9)
        card.add_header_widget(optimize_btn)

        self._danjeon_budget: _Budget = _Budget(self, "경지 제공", _DANJEON_TOTAL)
        card.add_widget(self._danjeon_budget)

        flow_container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(flow_container, margin=0, spacing=14)
        self._danjeon_fields: list[StepperField] = []
        for _key, label, effect, value in sample_data.DANJEON_DIST:
            flow.addWidget(self._build_danjeon_item(label, effect, value))
        flow_container.setLayout(flow)

        card.add_widget(flow_container)
        self._recalc_danjeon()
        return card

    def _build_danjeon_item(self, label: str, effect: str, value: int) -> QWidget:
        """단전 1종 입력 (라벨 + 스텝퍼 + 효과 설명)"""

        container: QFrame = QFrame(self)
        container.setFixedWidth(_DANJEON_ITEM_WIDTH)
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        name_label: QLabel = QLabel(label, container)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        box.addWidget(name_label)

        field: StepperField = StepperField(container, str(value), on_changed=self._recalc_danjeon)
        self._danjeon_fields.append(field)
        box.addWidget(field)

        effect_label: QLabel = QLabel(effect, container)
        effect_label.setObjectName("charHint")
        effect_label.setFont(CustomFont(8))
        effect_label.setWordWrap(True)
        box.addWidget(effect_label)

        return container

    def _recalc_danjeon(self) -> None:
        """단전 합산 후 요약바 갱신"""

        used: float = sum(field.number() for field in self._danjeon_fields)
        self._danjeon_budget.recalc(used)
