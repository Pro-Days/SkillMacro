"""스탯·단전 분배 탭

요약바(분배 가능/사용/남은 + 진행바)는 현재 카드의 입력 합산만 표시한다.
자동 최적화 버튼은 목업대로 두되, 실제 최적화 계산은 연결하지 않는다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
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
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    ResponsiveColumnsBox,
    StepperField,
)

# 분배 항목 입력칸 폭 (가운데 정렬, 남는 공간은 항목 사이 간격으로)
_ITEM_FIELD_WIDTH: int = 84

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
        layout.addLayout(
            self._build_item("남은 포인트", str(total), value_key="remain")
        )

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

        # 폭이 넓으면 스탯 분배 오른쪽에 단전 분배를 나란히 배치
        cards: ResponsiveColumnsBox = ResponsiveColumnsBox(
            self, min_column_width=500, spacing=16
        )
        cards.addWidget(self._build_stat_card())
        cards.addWidget(self._build_danjeon_card())
        layout.addWidget(cards)
        layout.addStretch(1)

    def _build_stat_card(self) -> CharCard:
        """스탯 분배 카드"""

        card: CharCard = CharCard(self, "스탯 분배")
        optimize_btn: StyledButton = StyledButton(
            self, "자동 최적화", kind="normal", point_size=9
        )
        card.add_header_widget(optimize_btn)

        self._stat_budget: _Budget = _Budget(self, "분배 가능", _STAT_TOTAL)
        card.add_widget(self._stat_budget)

        self._stat_fields: list[StepperField] = []
        items: list[QWidget] = [
            self._build_item(label, effect, value, self._recalc_stat, self._stat_fields)
            for _key, label, effect, value in sample_data.STAT_DIST
        ]
        card.add_widget(self._build_item_row(items))
        self._recalc_stat()
        return card

    def _build_item_row(self, items: list[QWidget]) -> QWidget:
        """항목들을 가로 가운데 정렬하고, 남는 공간은 항목 사이 간격으로 분배"""

        row_container: QFrame = QFrame(self)
        row = QHBoxLayout(row_container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        # 양끝과 항목 사이마다 동일 stretch → 가운데 정렬 + 균등 간격
        row.addStretch(1)
        for item in items:
            row.addWidget(item)
            row.addStretch(1)
        return row_container

    def _build_item(
        self,
        label: str,
        effect: str,
        value: int,
        on_changed,
        field_store: list[StepperField],
    ) -> QWidget:
        """분배 1종 카드 (라벨 위 / 입력칸 / 올라가는 스탯 아래, 모두 가운데 정렬)"""

        card: QFrame = QFrame(self)
        box = QVBoxLayout(card)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        name_label: QLabel = QLabel(label, card)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(name_label)

        field: StepperField = StepperField(card, str(value), on_changed=on_changed)
        field.setFixedWidth(_ITEM_FIELD_WIDTH)
        field_store.append(field)
        box.addWidget(field, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 종류가 다른 스탯은 줄을 나눠 표시
        effect_label: QLabel = QLabel(effect.replace(" · ", "\n"), card)
        effect_label.setObjectName("charHint")
        effect_label.setFont(CustomFont(8))
        effect_label.setWordWrap(True)
        effect_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(effect_label)

        # 줄 수가 다른 카드끼리도 내용이 위쪽에 정렬되도록 남는 공간을 아래로 보낸다
        box.addStretch(1)

        return card

    def _recalc_stat(self) -> None:
        """스탯 합산 후 요약바 갱신"""

        used: float = sum(field.number() for field in self._stat_fields)
        self._stat_budget.recalc(used)

    def _build_danjeon_card(self) -> CharCard:
        """단전 분배 카드"""

        card: CharCard = CharCard(self, "단전 분배")
        optimize_btn: StyledButton = StyledButton(
            self, "자동 최적화", kind="normal", point_size=9
        )
        card.add_header_widget(optimize_btn)

        self._danjeon_budget: _Budget = _Budget(self, "분배 가능", _DANJEON_TOTAL)
        card.add_widget(self._danjeon_budget)

        self._danjeon_fields: list[StepperField] = []
        items: list[QWidget] = [
            self._build_item(
                label, effect, value, self._recalc_danjeon, self._danjeon_fields
            )
            for _key, label, effect, value in sample_data.DANJEON_DIST
        ]
        card.add_widget(self._build_item_row(items))
        self._recalc_danjeon()
        return card

    def _recalc_danjeon(self) -> None:
        """단전 합산 후 요약바 갱신"""

        used: float = sum(field.number() for field in self._danjeon_fields)
        self._danjeon_budget.recalc(used)
