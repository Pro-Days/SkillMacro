"""부적 탭"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import STAT_SPECS, TALISMAN_SPECS, TalismanSpec
from app.scripts.character_models import (
    MAX_EQUIPPED_TALISMAN_COUNT,
    MAX_TALISMAN_LEVEL,
    CharacterProfile,
    CharacterTalisman,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.constants import GRADE_COLORS
from app.scripts.ui.character_ui.edit_session import CharacterEditSession
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    CharComboBox,
    GradeBadge,
    ResponsiveColumnsBox,
    StepperField,
)

_OWNED_TALISMAN_WIDTH: int = 248
_OWNED_TALISMAN_HEIGHT: int = 140
_EQUIPPED_TALISMAN_HEIGHT: int = 132


class TalismanTab(CharacterTab):
    """부적 탭"""

    def __init__(self, parent: QWidget, session: CharacterEditSession) -> None:
        super().__init__(parent, session)

        self._profile: CharacterProfile | None = None
        self._loading: bool = False
        self._specs_by_name: dict[str, TalismanSpec] = {
            spec.name: spec for spec in TALISMAN_SPECS
        }
        self._equipped_stat_labels: dict[str, QLabel] = {}
        self._slot_widgets: list[QFrame] = []
        self._owned_rows: dict[str, QFrame] = {}

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
            min_column_width=_OWNED_TALISMAN_WIDTH,
            spacing=12,
            fill=False,
            center=True,
        )
        self._owned_layout = self._owned_container.flow
        owned_card.add_widget(self._owned_container)

        add_btn: StyledButton = StyledButton(
            self,
            "+ 부적 추가",
            kind="normal",
            point_size=9,
        )
        add_btn.clicked.connect(self._add_talisman)
        owned_card.add_widget(add_btn)
        layout.addWidget(owned_card)
        layout.addStretch(1)

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        self._equipped_stat_labels = {}
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
        self._equipped_stat_labels = {}
        self._slot_widgets = []
        for slot_index in range(MAX_EQUIPPED_TALISMAN_COUNT):
            talisman: CharacterTalisman | None = self._equipped_talisman(slot_index)
            slot_widget: QFrame = self._build_slot(talisman)
            self._slot_widgets.append(slot_widget)
            self._slot_layout.addWidget(slot_widget, 1)

    def _refresh_slots(
        self,
        start_index: int = 0,
        talisman_id: str | None = None,
    ) -> None:
        """영향받은 장착 슬롯 위젯 갱신"""

        if talisman_id is None:
            if self._profile is None:
                self._equipped_stat_labels = {}

            else:
                unaffected_ids: set[str] = set(
                    self._profile.equipped.talisman_ids[:start_index]
                )
                self._equipped_stat_labels = {
                    current_id: label
                    for current_id, label in self._equipped_stat_labels.items()
                    if current_id in unaffected_ids
                }

        else:
            self._equipped_stat_labels.pop(talisman_id, None)

        for slot_index, slot_widget in enumerate(self._slot_widgets):
            if slot_index < start_index:
                continue

            talisman: CharacterTalisman | None = self._equipped_talisman(slot_index)
            if talisman_id is not None and (
                talisman is None or talisman.id != talisman_id
            ):
                continue

            self._slot_layout.removeWidget(slot_widget)
            slot_widget.deleteLater()
            replacement: QFrame = self._build_slot(talisman)
            self._slot_widgets[slot_index] = replacement
            self._slot_layout.insertWidget(slot_index, replacement, 1)

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
        slot.setMinimumHeight(_EQUIPPED_TALISMAN_HEIGHT)
        slot.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
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
        name_row.addWidget(
            GradeBadge(
                slot,
                spec.grade.value,
                GRADE_COLORS[spec.grade.value],
            )
        )
        name_label: QLabel = QLabel(spec.name, slot)
        name_label.setObjectName("charTalName")
        name_label.setFont(CustomFont(10, bold=True))
        name_row.addWidget(name_label)
        name_row.addStretch(1)
        box.addLayout(name_row)

        stat_label: QLabel = QLabel(
            f"{STAT_SPECS[spec.stat_key]} "
            f"+{spec.level_stats[talisman.level]:g}\n"
            f"Lv.{talisman.level}",
            slot,
        )
        stat_label.setObjectName("charTalStat")
        stat_label.setFont(CustomFont(9))
        stat_label.setWordWrap(True)
        self._equipped_stat_labels[talisman.id] = stat_label
        box.addWidget(stat_label)
        box.addStretch(1)

        unequip_btn: StyledButton = StyledButton(
            slot,
            "장착 해제",
            kind="normal",
            point_size=9,
        )
        unequip_btn.clicked.connect(lambda: self._unequip(talisman))
        box.addWidget(unequip_btn)
        return slot

    def _render_owned(self) -> None:
        """보유 목록 갱신"""

        self._clear_layout(self._owned_layout)
        self._owned_rows = {}
        if self._profile is None:
            self._owned_container.sync_height()
            return

        for talisman in self._profile.talismans:
            self._add_owned_row(talisman)

        self._owned_container.sync_height()

    def _add_owned_row(self, talisman: CharacterTalisman) -> None:
        """보유 부적 카드 하나 추가"""

        row: QFrame = self._build_owned_row(talisman)
        self._owned_rows[talisman.id] = row
        self._owned_layout.addWidget(row)
        self._owned_container.sync_height()

    def _replace_owned_row(self, talisman: CharacterTalisman) -> None:
        """보유 부적 카드 하나 교체"""

        current_row: QFrame = self._owned_rows[talisman.id]
        row_index: int = self._owned_layout.indexOf(current_row)
        self._owned_layout.removeWidget(current_row)
        current_row.deleteLater()
        replacement: QFrame = self._build_owned_row(talisman)
        self._owned_rows[talisman.id] = replacement
        self._owned_layout.insertWidget(row_index, replacement)
        self._owned_container.sync_height()

    def _remove_owned_row(self, talisman_id: str) -> None:
        """보유 부적 카드 하나 제거"""

        row: QFrame = self._owned_rows.pop(talisman_id)
        self._owned_layout.removeWidget(row)
        row.deleteLater()
        self._owned_container.sync_height()

    def _build_owned_row(self, talisman: CharacterTalisman) -> QFrame:
        """보유 부적 1개 카드"""

        row: QFrame = QFrame(self)
        row.setObjectName("charTalCard")
        row.setFixedSize(_OWNED_TALISMAN_WIDTH, _OWNED_TALISMAN_HEIGHT)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(10)

        spec: TalismanSpec = self._specs_by_name[talisman.talisman_key]
        head = QHBoxLayout()
        head.setSpacing(8)
        head.addStretch(1)
        head.addWidget(
            GradeBadge(
                row,
                spec.grade.value,
                GRADE_COLORS[spec.grade.value],
            )
        )

        combo: CharComboBox = CharComboBox(row, [spec.name for spec in TALISMAN_SPECS])
        combo.setFixedWidth(154)
        combo.setCurrentText(spec.name)
        combo.currentTextChanged.connect(
            lambda text, target=talisman: self._change_talisman_key(target, text)
        )
        head.addWidget(combo)
        head.addStretch(1)
        layout.addLayout(head)

        middle = QHBoxLayout()
        middle.setSpacing(8)
        middle.addStretch(1)

        stat_label: QLabel = QLabel(self._owned_stat_text(talisman), row)
        stat_label.setObjectName("charTalStat")
        stat_label.setFont(CustomFont(9))
        stat_label.setWordWrap(True)
        stat_label.setMinimumWidth(0)
        stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle.addWidget(stat_label)

        level_row = QHBoxLayout()
        level_row.setSpacing(8)
        # level_row.addStretch(1)
        level_field: StepperField = StepperField(
            row,
            str(talisman.level),
            unit="Lv",
            max_width=80,
        )
        level_field.input.setValidator(
            QIntValidator(0, MAX_TALISMAN_LEVEL, level_field.input)
        )
        level_field.value_changed.connect(
            lambda field=level_field, target=talisman, label=stat_label: self._on_level(
                field,
                target,
                label,
            )
        )
        level_row.addWidget(level_field)

        max_label: QLabel = QLabel(f"/ {MAX_TALISMAN_LEVEL}", row)
        max_label.setObjectName("charMuted")
        max_label.setFont(CustomFont(9))
        level_row.addWidget(max_label)
        # level_row.addStretch(1)
        middle.addLayout(level_row)
        middle.addStretch(1)
        layout.addLayout(middle)

        foot = QHBoxLayout()
        foot.setSpacing(8)
        foot.addStretch(1)

        equipped: bool = (
            self._profile is not None
            and talisman.id in self._profile.equipped.talisman_ids
        )
        equip_btn: StyledButton = StyledButton(
            row,
            "장착중" if equipped else "장착",
            kind="add" if equipped else "normal",
            point_size=9,
        )
        equip_btn.setFixedWidth(58)
        equip_btn.clicked.connect(lambda: self._toggle_equip(talisman))
        foot.addWidget(equip_btn)

        delete_btn: StyledButton = StyledButton(
            row,
            "삭제",
            kind="danger",
            point_size=9,
        )
        delete_btn.setFixedWidth(58)
        delete_btn.clicked.connect(lambda: self._delete_talisman(talisman))
        foot.addWidget(delete_btn)
        foot.addStretch(1)
        layout.addLayout(foot)
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
        self._add_owned_row(self._profile.talismans[-1])
        self._session.commit_saved_value()

    def _change_talisman_key(self, talisman: CharacterTalisman, name: str) -> None:
        """부적 종류 변경"""

        if self._loading:
            return

        if talisman.talisman_key == name:
            return

        talisman.talisman_key = name
        self._refresh_slots(talisman_id=talisman.id)
        self._replace_owned_row(talisman)
        if self._profile is None:
            raise ValueError("character profile is not bound")

        if talisman.id in self._profile.equipped.talisman_ids:
            self._session.commit_stats()

        else:
            self._session.commit_saved_value()

    def _on_level(
        self,
        field: StepperField,
        talisman: CharacterTalisman,
        stat_label: QLabel,
    ) -> None:
        """레벨 변경 시 모델 반영"""

        if self._loading:
            return

        level: int = max(0, min(MAX_TALISMAN_LEVEL, int(field.number())))
        field.set_number(float(level))
        if talisman.level == level:
            return

        talisman.level = level
        self._refresh_talisman_stat_labels(talisman, stat_label)
        if self._profile is None:
            raise ValueError("character profile is not bound")

        if talisman.id in self._profile.equipped.talisman_ids:
            self._session.commit_stats()

        else:
            self._session.commit_saved_value()

    def _refresh_talisman_stat_labels(
        self,
        talisman: CharacterTalisman,
        owned_stat_label: QLabel,
    ) -> None:
        """부적 레벨 표시 라벨 갱신"""

        owned_stat_label.setText(self._owned_stat_text(talisman))

        equipped_stat_label: QLabel | None = self._equipped_stat_labels.get(talisman.id)
        if equipped_stat_label is None:
            return

        spec: TalismanSpec = self._specs_by_name[talisman.talisman_key]
        equipped_stat_label.setText(
            f"{STAT_SPECS[spec.stat_key]} "
            f"+{spec.level_stats[talisman.level]:g}\n"
            f"Lv.{talisman.level}"
        )

    def _toggle_equip(self, talisman: CharacterTalisman) -> None:
        """장착/해제 토글"""

        if self._profile is None:
            return

        changed: bool = False
        if talisman.id in self._profile.equipped.talisman_ids:
            changed_index: int = self._profile.equipped.talisman_ids.index(talisman.id)
            self._profile.equipped.talisman_ids.remove(talisman.id)
            changed = True

        elif len(self._profile.equipped.talisman_ids) < MAX_EQUIPPED_TALISMAN_COUNT:
            changed_index = len(self._profile.equipped.talisman_ids)
            self._profile.equipped.talisman_ids.append(talisman.id)
            changed = True

        if not changed:
            return

        self._refresh_slots(start_index=changed_index)
        self._replace_owned_row(talisman)
        self._session.commit_stats()

    def _delete_talisman(self, talisman: CharacterTalisman) -> None:
        """보유 부적 삭제 및 장착 참조 제거"""

        if self._profile is None:
            return

        # 보유 목록에서 선택 부적 제거
        equipped: bool = talisman.id in self._profile.equipped.talisman_ids
        equipped_index: int | None = (
            self._profile.equipped.talisman_ids.index(talisman.id)
            if equipped
            else None
        )
        self._profile.talismans = [
            current_talisman
            for current_talisman in self._profile.talismans
            if current_talisman.id != talisman.id
        ]

        # 삭제된 부적의 장착 슬롯 참조 제거
        self._profile.equipped.talisman_ids = [
            talisman_id
            for talisman_id in self._profile.equipped.talisman_ids
            if talisman_id != talisman.id
        ]

        if equipped_index is not None:
            self._refresh_slots(start_index=equipped_index)

        self._remove_owned_row(talisman.id)
        if equipped:
            self._session.commit_stats()

        else:
            self._session.commit_saved_value()

    def _unequip(self, talisman: CharacterTalisman) -> None:
        """슬롯에서 장착 해제"""

        if self._profile is None:
            return

        if talisman.id in self._profile.equipped.talisman_ids:
            equipped_index: int = self._profile.equipped.talisman_ids.index(talisman.id)
            self._profile.equipped.talisman_ids.remove(talisman.id)

        else:
            raise ValueError("equipped talisman is not available")

        self._refresh_slots(start_index=equipped_index)
        self._replace_owned_row(talisman)
        self._session.commit_stats()
