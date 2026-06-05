"""부적 탭"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import (
    STAT_SPECS,
    TALISMAN_SPECS,
    TalismanSpec,
)
from app.scripts.character_models import (
    MAX_EQUIPPED_TALISMAN_COUNT,
    MAX_TALISMAN_LEVEL,
    CharacterProfile,
    CharacterTalisman,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.constants import GRADE_COLORS
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    CharComboBox,
    GradeBadge,
    ResponsiveColumnsBox,
    StepperField,
)


class TalismanTab(QFrame):
    """부적 탭"""

    def __init__(self, parent: QWidget, on_changed: Callable[[], None]) -> None:
        super().__init__(parent)

        self._profile: CharacterProfile | None = None
        self._on_changed: Callable[[], None] = on_changed
        self._loading: bool = False
        self._specs_by_name: dict[str, TalismanSpec] = {
            spec.name: spec for spec in TALISMAN_SPECS
        }

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
        self._owned_container: ResponsiveColumnsBox = ResponsiveColumnsBox(
            self,
            min_column_width=420,
            spacing=8,
        )
        self._owned_layout = self._owned_container.flow
        owned_card.add_widget(self._owned_container)

        add_btn: StyledButton = StyledButton(self, "+ 부적 추가", kind="normal", point_size=9)
        add_btn.clicked.connect(self._add_talisman)
        owned_card.add_widget(add_btn)
        layout.addWidget(owned_card)
        layout.addStretch(1)

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        self._loading = True
        self._profile = profile
        self.setEnabled(profile is not None)
        self._render_slots()
        self._render_owned()
        self._loading = False

    def _clear_layout(self, layout) -> None:
        """레이아웃 자식 위젯 제거"""

        while layout.count():
            item = layout.takeAt(0)
            widget: QWidget | None = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_slots(self) -> None:
        """장착 슬롯 3개 갱신"""

        self._clear_layout(self._slot_layout)
        for slot_index in range(MAX_EQUIPPED_TALISMAN_COUNT):
            talisman: CharacterTalisman | None = self._equipped_talisman(slot_index)
            self._slot_layout.addWidget(self._build_slot(talisman))

    def _equipped_talisman(self, slot_index: int) -> CharacterTalisman | None:
        """장착 슬롯의 부적 조회"""

        if self._profile is None:
            return None

        if slot_index >= len(self._profile.equipped.talisman_ids):
            return None

        talisman_id: str = self._profile.equipped.talisman_ids[slot_index]
        for talisman in self._profile.talismans:
            if talisman.id == talisman_id:
                return talisman

        return None

    def _build_slot(self, talisman: CharacterTalisman | None) -> QFrame:
        """장착 슬롯 1칸"""

        slot: QFrame = QFrame(self)
        slot.setObjectName("charTalSlot")
        slot.setProperty("filled", talisman is not None)
        box = QVBoxLayout(slot)
        box.setContentsMargins(14, 14, 14, 14)
        box.setSpacing(8)

        if talisman is None:
            empty_label: QLabel = QLabel("비어 있음", slot)
            empty_label.setObjectName("charMuted")
            empty_label.setFont(CustomFont(10, bold=True))
            box.addWidget(empty_label)
            box.addStretch(1)
            select_btn: StyledButton = StyledButton(
                slot,
                "장착 부적 선택",
                kind="normal",
                point_size=9,
            )
            select_btn.setEnabled(False)
            box.addWidget(select_btn)
            return slot

        spec: TalismanSpec = self._specs_by_name[talisman.talisman_key]
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_row.addWidget(GradeBadge(slot, spec.grade.value, GRADE_COLORS[spec.grade.value]))
        name_label: QLabel = QLabel(spec.name, slot)
        name_label.setObjectName("charTalName")
        name_label.setFont(CustomFont(10, bold=True))
        name_row.addWidget(name_label)
        name_row.addStretch(1)
        box.addLayout(name_row)

        stat_label: QLabel = QLabel(
            f"{STAT_SPECS[spec.stat_key]} +{spec.level_stats[talisman.level]:g}\nLv.{talisman.level}",
            slot,
        )
        stat_label.setObjectName("charTalStat")
        stat_label.setFont(CustomFont(9))
        stat_label.setWordWrap(True)
        box.addWidget(stat_label)
        box.addStretch(1)

        unequip_btn: StyledButton = StyledButton(slot, "장착 해제", kind="normal", point_size=9)
        unequip_btn.clicked.connect(lambda: self._unequip(talisman))
        box.addWidget(unequip_btn)
        return slot

    def _render_owned(self) -> None:
        """보유 목록 갱신"""

        self._clear_layout(self._owned_layout)
        if self._profile is None:
            return

        for talisman in self._profile.talismans:
            self._owned_layout.addWidget(self._build_owned_row(talisman))

    def _build_owned_row(self, talisman: CharacterTalisman) -> QFrame:
        """보유 부적 1행"""

        row: QFrame = QFrame(self)
        row.setObjectName("charTalCard")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        spec: TalismanSpec = self._specs_by_name[talisman.talisman_key]
        layout.addWidget(
            GradeBadge(row, spec.grade.value, GRADE_COLORS[spec.grade.value], dot=True)
        )

        combo: CharComboBox = CharComboBox(row, [spec.name for spec in TALISMAN_SPECS])
        combo.setMaximumWidth(150)
        combo.setCurrentText(spec.name)
        combo.currentTextChanged.connect(
            lambda text, target=talisman: self._change_talisman_key(target, text)
        )
        layout.addWidget(combo)

        stat_label: QLabel = QLabel(self._owned_stat_text(talisman), row)
        stat_label.setObjectName("charTalStat")
        stat_label.setFont(CustomFont(9))
        stat_label.setWordWrap(True)
        stat_label.setMinimumWidth(0)
        layout.addWidget(stat_label, 1)

        level_field: StepperField = StepperField(row, str(talisman.level), unit="Lv", max_width=92)
        level_field.value_changed.connect(
            lambda field=level_field, target=talisman: self._on_level(field, target)
        )
        layout.addWidget(level_field)

        max_label: QLabel = QLabel(f"/ {MAX_TALISMAN_LEVEL}", row)
        max_label.setObjectName("charMuted")
        max_label.setFont(CustomFont(9))
        layout.addWidget(max_label)

        equipped: bool = self._profile is not None and talisman.id in self._profile.equipped.talisman_ids
        equip_btn: StyledButton = StyledButton(
            row,
            "장착중" if equipped else "장착",
            kind="add" if equipped else "normal",
            point_size=9,
        )
        equip_btn.setFixedWidth(58)
        equip_btn.clicked.connect(lambda: self._toggle_equip(talisman))
        layout.addWidget(equip_btn)
        return row

    def _owned_stat_text(self, talisman: CharacterTalisman) -> str:
        """보유 행 스탯 표시 문구"""

        spec: TalismanSpec = self._specs_by_name[talisman.talisman_key]
        return f"{STAT_SPECS[spec.stat_key]}  +{spec.level_stats[talisman.level]:g}"

    def _add_talisman(self) -> None:
        """부적 추가"""

        if self._profile is None:
            return

        first_spec: TalismanSpec = TALISMAN_SPECS[0]
        self._profile.talismans.append(
            CharacterTalisman(
                talisman_key=first_spec.name,
                level=0,
            )
        )
        self._render_owned()
        self._on_changed()

    def _change_talisman_key(self, talisman: CharacterTalisman, name: str) -> None:
        """부적 종류 변경"""

        if self._loading:
            return

        talisman.talisman_key = name
        self._render_slots()
        self._render_owned()
        self._on_changed()

    def _on_level(self, field: StepperField, talisman: CharacterTalisman) -> None:
        """레벨 변경 시 모델 반영"""

        if self._loading:
            return

        talisman.level = max(0, min(MAX_TALISMAN_LEVEL, int(field.number())))
        self._render_slots()
        self._render_owned()
        self._on_changed()

    def _toggle_equip(self, talisman: CharacterTalisman) -> None:
        """장착/해제 토글"""

        if self._profile is None:
            return

        if talisman.id in self._profile.equipped.talisman_ids:
            self._profile.equipped.talisman_ids.remove(talisman.id)

        elif len(self._profile.equipped.talisman_ids) < MAX_EQUIPPED_TALISMAN_COUNT:
            self._profile.equipped.talisman_ids.append(talisman.id)

        self._render_slots()
        self._render_owned()
        self._on_changed()

    def _unequip(self, talisman: CharacterTalisman) -> None:
        """슬롯에서 장착 해제"""

        if self._profile is None:
            return

        if talisman.id in self._profile.equipped.talisman_ids:
            self._profile.equipped.talisman_ids.remove(talisman.id)

        self._render_slots()
        self._render_owned()
        self._on_changed()
