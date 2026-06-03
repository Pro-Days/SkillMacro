"""부적 탭 (장착 슬롯 3개 + 보유 목록)"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui import sample_data
from app.scripts.ui.character_ui.widgets import CharCard, CharComboBox, GradeBadge, StepperField


class TalismanTab(QFrame):
    """부적 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._owned: list[sample_data.TalismanData] = sample_data.default_talismans()
        self._equipped: list[int] = list(sample_data.DEFAULT_EQUIPPED_TALISMANS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 장착 부적 카드
        self._slot_card: CharCard = CharCard(self, "장착 부적")
        self._slot_container: QFrame = QFrame(self)
        self._slot_layout = QHBoxLayout(self._slot_container)
        self._slot_layout.setContentsMargins(0, 0, 0, 0)
        self._slot_layout.setSpacing(12)
        self._slot_card.add_widget(self._slot_container)
        layout.addWidget(self._slot_card)

        # 보유 부적 카드
        owned_card: CharCard = CharCard(self, "보유 부적")
        self._owned_container: QFrame = QFrame(self)
        self._owned_layout = QVBoxLayout(self._owned_container)
        self._owned_layout.setContentsMargins(0, 0, 0, 0)
        self._owned_layout.setSpacing(8)
        owned_card.add_widget(self._owned_container)

        add_btn: StyledButton = StyledButton(self, "+ 부적 추가", kind="normal", point_size=9)
        owned_card.add_widget(add_btn)
        layout.addWidget(owned_card)
        layout.addStretch(1)

        self._render_slots()
        self._render_owned()

    def _clear_layout(self, layout) -> None:
        """레이아웃 자식 위젯 제거"""

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_slots(self) -> None:
        """장착 슬롯 3개 갱신"""

        self._clear_layout(self._slot_layout)
        for slot_index in range(3):
            owned_index: int | None = (
                self._equipped[slot_index] if slot_index < len(self._equipped) else None
            )
            self._slot_layout.addWidget(self._build_slot(owned_index))

    def _build_slot(self, owned_index: int | None) -> QFrame:
        """장착 슬롯 1칸"""

        slot: QFrame = QFrame(self)
        slot.setObjectName("charTalSlot")
        slot.setProperty("filled", owned_index is not None)
        box = QVBoxLayout(slot)
        box.setContentsMargins(14, 14, 14, 14)
        box.setSpacing(8)

        if owned_index is None or owned_index >= len(self._owned):
            empty_label: QLabel = QLabel("비어 있음", slot)
            empty_label.setObjectName("charMuted")
            empty_label.setFont(CustomFont(10, bold=True))
            box.addWidget(empty_label)
            box.addStretch(1)
            select_btn: StyledButton = StyledButton(slot, "장착 부적 선택", kind="normal", point_size=9)
            select_btn.setEnabled(False)
            box.addWidget(select_btn)
            return slot

        data: sample_data.TalismanData = self._owned[owned_index]
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_row.addWidget(GradeBadge(slot, data.grade, sample_data.TALISMAN_GRADE_COLORS[data.grade]))
        name_label: QLabel = QLabel(data.name, slot)
        name_label.setObjectName("charTalName")
        name_label.setFont(CustomFont(10, bold=True))
        name_row.addWidget(name_label)
        name_row.addStretch(1)
        box.addLayout(name_row)

        stat_label: QLabel = QLabel(f"{data.stat} +{data.value()} · Lv.{data.level}", slot)
        stat_label.setObjectName("charTalStat")
        stat_label.setFont(CustomFont(9))
        stat_label.setWordWrap(True)
        box.addWidget(stat_label)
        box.addStretch(1)

        unequip_btn: StyledButton = StyledButton(slot, "장착 해제", kind="normal", point_size=9)
        unequip_btn.clicked.connect(lambda: self._unequip(owned_index))
        box.addWidget(unequip_btn)
        return slot

    def _render_owned(self) -> None:
        """보유 목록 갱신"""

        self._clear_layout(self._owned_layout)
        for index, data in enumerate(self._owned):
            self._owned_layout.addWidget(self._build_owned_row(index, data))

    def _build_owned_row(self, index: int, data: sample_data.TalismanData) -> QFrame:
        """보유 부적 1행"""

        row: QFrame = QFrame(self)
        row.setObjectName("charTalCard")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        layout.addWidget(GradeBadge(row, data.grade, sample_data.TALISMAN_GRADE_COLORS[data.grade]))

        combo: CharComboBox = CharComboBox(row, list(sample_data.TALISMAN_TEMPLATES))
        combo.setMaximumWidth(150)
        for i, template in enumerate(sample_data.TALISMAN_TEMPLATES):
            if template.startswith(data.name):
                combo.setCurrentIndex(i)
                break
        layout.addWidget(combo)

        stat_label: QLabel = QLabel(self._owned_stat_text(data), row)
        stat_label.setObjectName("charTalStat")
        stat_label.setFont(CustomFont(9))
        stat_label.setWordWrap(True)
        stat_label.setMinimumWidth(0)
        layout.addWidget(stat_label, 1)

        level_field: StepperField = StepperField(row, str(data.level), unit="Lv", max_width=120)
        level_field.value_changed.connect(
            lambda f=level_field, d=data, s=stat_label: self._on_level(f, d, s)
        )
        layout.addWidget(level_field)

        max_label: QLabel = QLabel("/ 14", row)
        max_label.setObjectName("charMuted")
        max_label.setFont(CustomFont(9))
        layout.addWidget(max_label)

        equipped: bool = index in self._equipped
        equip_btn: StyledButton = StyledButton(
            row, "장착중" if equipped else "장착", kind="add" if equipped else "normal", point_size=9
        )
        equip_btn.clicked.connect(lambda: self._toggle_equip(index))
        layout.addWidget(equip_btn)
        return row

    def _owned_stat_text(self, data: sample_data.TalismanData) -> str:
        """보유 행 스탯 표시 문구"""

        return f"{data.stat}  +{data.value()}"

    def _on_level(self, field: StepperField, data: sample_data.TalismanData, stat_label: QLabel) -> None:
        """레벨 변경 시 스탯 수치 갱신 (0~14 범위)"""

        level: int = max(0, min(14, int(field.number())))
        data.level = level
        stat_label.setText(self._owned_stat_text(data))
        self._render_slots()

    def _toggle_equip(self, index: int) -> None:
        """장착/해제 토글 (최대 3칸)"""

        if index in self._equipped:
            self._equipped.remove(index)
        elif len(self._equipped) < 3:
            self._equipped.append(index)
        self._render_slots()
        self._render_owned()

    def _unequip(self, index: int) -> None:
        """슬롯에서 장착 해제"""

        if index in self._equipped:
            self._equipped.remove(index)
        self._render_slots()
        self._render_owned()
