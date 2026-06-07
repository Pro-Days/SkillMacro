"""부적 탭"""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import (
    STAT_SPECS,
    TALISMAN_SPECS,
    TalismanGrade,
    TalismanSpec,
)
from app.scripts.character_models import (
    MAX_EQUIPPED_TALISMAN_COUNT,
    MAX_TALISMAN_LEVEL,
    CharacterProfile,
    CharacterTalisman,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.change_handler import CharacterChangeHandler
from app.scripts.ui.character_ui.constants import GRADE_COLORS
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    ChoiceListPanels,
    ResponsiveColumnsBox,
    StepperField,
)

_OWNED_TALISMAN_WIDTH: int = 360
_EQUIPPED_TALISMAN_HEIGHT: int = 132
_GRADE_ORDER: tuple[TalismanGrade, ...] = (
    TalismanGrade.NORMAL,
    TalismanGrade.ADVANCED,
    TalismanGrade.RARE,
    TalismanGrade.HEROIC,
    TalismanGrade.LEGENDARY,
)


class GradeBadge(QLabel):
    """부적 등급 색 뱃지"""

    def __init__(self, parent: QWidget, grade: str, color: str) -> None:
        super().__init__(grade, parent)

        self.setObjectName("charGradeBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.setFont(CustomFont(8, bold=True))
        self.setStyleSheet(
            f"background-color: {color}; color: white;"
            "border-radius: 8px; padding: 2px 8px;"
        )


class TalismanTab(CharacterTab):
    """부적 탭"""

    def __init__(
        self,
        parent: QWidget,
        changes: CharacterChangeHandler,
        profile: CharacterProfile,
    ) -> None:
        super().__init__(parent, changes, profile)

        self._selected_talisman_id: str | None = None
        self._selected_grade: TalismanGrade = TALISMAN_SPECS[0].grade
        self._specs_by_name: dict[str, TalismanSpec] = {
            spec.name: spec for spec in TALISMAN_SPECS
        }
        self._specs_by_grade: dict[TalismanGrade, list[TalismanSpec]] = {
            grade: [spec for spec in TALISMAN_SPECS if spec.grade is grade]
            for grade in _GRADE_ORDER
        }
        self._grade_buttons: dict[TalismanGrade, QPushButton] = {}
        self._template_buttons: dict[str, QPushButton] = {}
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
        owned_columns: ResponsiveColumnsBox = ResponsiveColumnsBox(
            owned_card, min_column_width=280, spacing=12
        )

        self._selector_panel: QFrame = self._build_selector_panel()
        self._owned_panel: QFrame = self._build_owned_panel()
        self._selector_panel.setMinimumWidth(260)
        self._owned_panel.setMinimumWidth(260)
        owned_columns.addWidget(self._selector_panel)
        owned_columns.addWidget(self._owned_panel)
        owned_card.add_widget(owned_columns)
        layout.addWidget(owned_card)
        layout.addStretch(1)

    def set_profile(self, profile: CharacterProfile) -> None:
        """선택 캐릭터 모델 반영"""

        self._equipped_stat_labels = {}
        self._profile = profile

        if not profile.talismans:
            self._selected_talisman_id = None
            self._selected_grade = TALISMAN_SPECS[0].grade

        elif self._selected_talisman_id not in {item.id for item in profile.talismans}:
            first_talisman: CharacterTalisman = profile.talismans[0]
            self._selected_talisman_id = first_talisman.id
            self._selected_grade = self._specs_by_name[
                first_talisman.talisman_key
            ].grade

        self._render_slots()
        self._render_owned()
        self._render_selector()

    def _clear_layout(self, layout: QLayout) -> None:
        """레이아웃 자식 위젯 제거"""

        while layout.count():
            item = layout.takeAt(0)
            widget: QWidget | None = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _build_selector_panel(self) -> QFrame:
        """부적 선택 패널 구성"""

        self._choice_panels = ChoiceListPanels(
            self,
            selector_title="부적 선택",
            list_title="부적 목록",
            add_text="+ 부적 추가",
            add_clicked=self._add_talisman,
            option_title="종류",
            selector_min_width=320,
            list_min_width=_OWNED_TALISMAN_WIDTH,
            selector_scroll_min_height=210,
            list_scroll_min_height=210,
        )
        for grade in _GRADE_ORDER:
            if not self._specs_by_grade[grade]:
                continue

            grade_button: QPushButton = self._choice_panels.make_choice_button(
                self._choice_panels.selector_panel,
                grade.value,
                "charTalChoiceBtn",
            )
            grade_button.clicked.connect(partial(self._select_grade, grade))
            self._grade_buttons[grade] = grade_button
            self._choice_panels.group_layout.addWidget(grade_button)

        self._choice_panels.group_layout.addStretch(1)
        return self._choice_panels.selector_panel

    def _build_owned_panel(self) -> QFrame:
        """보유 부적 목록 패널 구성"""

        return self._choice_panels.list_panel

    def _selected_talisman(self) -> CharacterTalisman | None:
        """현재 선택된 보유 부적 조회"""

        if self._selected_talisman_id is None:
            return None

        for talisman in self._profile.talismans:
            if talisman.id == self._selected_talisman_id:
                return talisman

        return None

    def _render_selector(self) -> None:
        """선택된 보유 부적 기준 선택 패널 갱신"""

        selected_talisman: CharacterTalisman | None = self._selected_talisman()
        if selected_talisman is not None:
            self._selected_grade = self._specs_by_name[
                selected_talisman.talisman_key
            ].grade

        has_selected_talisman: bool = selected_talisman is not None
        self._choice_panels.group_container.setEnabled(has_selected_talisman)
        self._choice_panels.option_scroll_area.setEnabled(has_selected_talisman)
        self._choice_panels.add_button.setEnabled(
            self._first_available_spec() is not None
        )

        for grade, grade_button in self._grade_buttons.items():
            with QSignalBlocker(grade_button):
                grade_button.setChecked(grade is self._selected_grade)

        self._rebuild_template_buttons(selected_talisman)

    def _rebuild_template_buttons(
        self,
        selected_talisman: CharacterTalisman | None,
    ) -> None:
        """선택 등급 기준 부적 종류 버튼 갱신"""

        self._clear_layout(self._choice_panels.option_layout)
        self._template_buttons.clear()

        for template in self._specs_by_grade[self._selected_grade]:
            is_blocked: bool = (
                selected_talisman is not None
                and not self._can_use_talisman_key(
                    selected_talisman,
                    template.name,
                )
            )
            option_button: QPushButton = self._choice_panels.make_choice_button(
                self._choice_panels.option_scroll_content,
                self._template_option_text(template),
                "charTalChoiceBtn",
                minimum_height=36,
                enabled=not is_blocked,
            )
            option_button.clicked.connect(
                partial(self._change_selected_talisman, template)
            )
            option_button.setChecked(
                selected_talisman is not None
                and selected_talisman.talisman_key == template.name
            )
            self._template_buttons[template.name] = option_button
            self._choice_panels.option_layout.addWidget(option_button)

        self._choice_panels.option_layout.addStretch(1)

    def _template_option_text(self, template: TalismanSpec) -> str:
        """부적 종류 선택 버튼 표시 문자열"""

        stat_label: str = STAT_SPECS[template.stat_key]
        max_level_value: float = template.level_stats[MAX_TALISMAN_LEVEL]
        return (
            f"{template.name} - {stat_label} "
            f"({MAX_TALISMAN_LEVEL}렙) {max_level_value:g}"
        )

    def _select_grade(self, grade: TalismanGrade, _checked: bool = False) -> None:
        """부적 선택 등급 변경"""

        if grade is self._selected_grade:
            return

        selected_talisman: CharacterTalisman | None = self._selected_talisman()
        if selected_talisman is None:
            return

        first_spec: TalismanSpec | None = self._first_selectable_spec_for_grade(
            selected_talisman,
            grade,
        )
        if first_spec is None:
            return

        selected_talisman.talisman_key = first_spec.name
        self._selected_grade = grade
        self._render_selector()

        # 장착 중인 부적만 장착 슬롯 표시 갱신
        is_equipped: bool = selected_talisman.id in self._profile.equipped.talisman_ids
        if is_equipped:
            self._render_slots()

        self._render_owned()
        if is_equipped:
            self._changes.stats_changed()

        else:
            self._changes.saved_value_changed()

    def _change_selected_talisman(
        self,
        template: TalismanSpec,
        _checked: bool = False,
    ) -> None:
        """선택된 보유 부적 종류 변경"""

        selected_talisman: CharacterTalisman | None = self._selected_talisman()
        if selected_talisman is None:
            return

        if selected_talisman.talisman_key == template.name:
            return

        if not self._can_use_talisman_key(selected_talisman, template.name):
            return

        selected_talisman.talisman_key = template.name
        self._selected_grade = template.grade
        self._render_selector()

        # 장착 중인 부적만 장착 슬롯 표시 갱신
        is_equipped: bool = selected_talisman.id in self._profile.equipped.talisman_ids
        if is_equipped:
            self._render_slots()

        self._render_owned()
        if is_equipped:
            self._changes.stats_changed()

        else:
            self._changes.saved_value_changed()

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

    def _first_selectable_spec_for_grade(
        self,
        talisman: CharacterTalisman,
        grade: TalismanGrade,
    ) -> TalismanSpec | None:
        """등급 내 장착 중복 없는 첫 부적 정의 조회"""

        for spec in self._specs_by_grade[grade]:
            if self._can_use_talisman_key(talisman, spec.name):
                return spec

        return None

    def _can_use_talisman_key(
        self,
        talisman: CharacterTalisman,
        talisman_key: str,
    ) -> bool:
        """부적 종류 변경 가능 여부"""

        for owned_talisman in self._profile.talismans:
            if owned_talisman.id == talisman.id:
                continue

            if owned_talisman.talisman_key == talisman_key:
                return False

        return True

    def _first_available_spec(self) -> TalismanSpec | None:
        """보유하지 않은 첫 부적 정의 조회"""

        used_keys: set[str] = {
            talisman.talisman_key for talisman in self._profile.talismans
        }
        for spec in TALISMAN_SPECS:
            if spec.name not in used_keys:
                return spec

        return None

    def _has_equipped_talisman_key(
        self,
        talisman: CharacterTalisman,
        talisman_key: str,
    ) -> bool:
        """다른 장착 슬롯의 같은 부적 종류 존재 여부"""

        for equipped_id in self._profile.equipped.talisman_ids:
            if equipped_id == talisman.id:
                continue

            equipped_talisman: CharacterTalisman | None = self._talisman_by_id(
                equipped_id
            )
            if equipped_talisman is None:
                continue

            if equipped_talisman.talisman_key == talisman_key:
                return True

        return False

    def _talisman_by_id(self, talisman_id: str) -> CharacterTalisman | None:
        """식별자 기준 보유 부적 조회"""

        for talisman in self._profile.talismans:
            if talisman.id == talisman_id:
                return talisman

        return None

    def _equipped_talisman(self, slot_index: int) -> CharacterTalisman | None:
        """장착 슬롯의 부적 조회"""

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

        self._clear_layout(self._choice_panels.list_layout)
        self._owned_rows = {}
        for talisman in self._profile.talismans:
            self._add_owned_row(talisman)

    def _add_owned_row(self, talisman: CharacterTalisman) -> None:
        """보유 부적 카드 하나 추가"""

        row: QFrame = self._build_owned_row(talisman)
        self._owned_rows[talisman.id] = row
        self._choice_panels.list_layout.addWidget(row)

    def _replace_owned_row(self, talisman: CharacterTalisman) -> None:
        """보유 부적 카드 하나 교체"""

        current_row: QFrame = self._owned_rows[talisman.id]
        row_index: int = self._choice_panels.list_layout.indexOf(current_row)
        self._choice_panels.list_layout.removeWidget(current_row)
        current_row.deleteLater()
        replacement: QFrame = self._build_owned_row(talisman)
        self._owned_rows[talisman.id] = replacement
        self._choice_panels.list_layout.insertWidget(row_index, replacement)

    def _remove_owned_row(self, talisman_id: str) -> None:
        """보유 부적 카드 하나 제거"""

        row: QFrame = self._owned_rows.pop(talisman_id)
        self._choice_panels.list_layout.removeWidget(row)
        row.deleteLater()

    def _refresh_owned_selection(self) -> None:
        """보유 부적 카드 선택 표시만 갱신"""

        for talisman_id, row in self._owned_rows.items():
            # 행 선택 속성 갱신
            selected: bool = talisman_id == self._selected_talisman_id
            row.setProperty("selected", selected)
            row.style().unpolish(row)
            row.style().polish(row)

            # 선택 버튼 checked 상태 갱신
            select_button: QPushButton | None = row.findChild(
                QPushButton,
                "charTalListSelectBtn",
            )
            if select_button is None:
                raise ValueError("talisman select button is not bound")

            select_button.setChecked(selected)

    def _build_owned_row(self, talisman: CharacterTalisman) -> QFrame:
        """보유 부적 1개 카드"""

        row: QFrame = QFrame(self)
        row.setObjectName("charTalCard")
        row.setProperty("selected", talisman.id == self._selected_talisman_id)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        spec: TalismanSpec = self._specs_by_name[talisman.talisman_key]
        head = QHBoxLayout()
        head.setSpacing(8)
        head.addWidget(
            GradeBadge(
                row,
                spec.grade.value,
                GRADE_COLORS[spec.grade.value],
            )
        )

        select_btn: QPushButton = self._choice_panels.make_choice_button(
            row,
            spec.name,
            "charTalListSelectBtn",
            point_size=10,
            checked=talisman.id == self._selected_talisman_id,
        )
        select_btn.clicked.connect(lambda: self._select_talisman(talisman))
        head.addWidget(select_btn, 1)
        layout.addLayout(head)

        stat_label: QLabel = QLabel(self._owned_stat_text(talisman), row)
        stat_label.setObjectName("charTalStat")
        stat_label.setFont(CustomFont(9))
        stat_label.setWordWrap(True)
        layout.addWidget(stat_label)

        foot = QHBoxLayout()
        foot.setSpacing(8)

        level_field: StepperField = StepperField(
            row,
            str(talisman.level),
            unit="Lv",
            max_width=80,
            integer=True,
        )
        level_field.value_changed.connect(
            lambda field=level_field, target=talisman, label=stat_label: self._on_level(
                field,
                target,
                label,
            )
        )
        level_field.input.editingFinished.connect(
            lambda field=level_field, target=talisman, label=stat_label: self._finish_level(
                field,
                target,
                label,
            )
        )
        foot.addWidget(level_field)

        max_label: QLabel = QLabel(f"/ {MAX_TALISMAN_LEVEL}", row)
        max_label.setObjectName("charMuted")
        max_label.setFont(CustomFont(9))
        foot.addWidget(max_label)
        foot.addStretch(1)

        equipped: bool = talisman.id in self._profile.equipped.talisman_ids
        can_equip: bool = equipped or (
            len(self._profile.equipped.talisman_ids) < MAX_EQUIPPED_TALISMAN_COUNT
            and not self._has_equipped_talisman_key(
                talisman,
                talisman.talisman_key,
            )
        )
        equip_btn: StyledButton = StyledButton(
            row,
            "장착중" if equipped else "장착",
            kind="add" if equipped else "normal",
            point_size=9,
        )
        equip_btn.setFixedWidth(58)
        equip_btn.setEnabled(can_equip)
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
        layout.addLayout(foot)
        return row

    def _owned_stat_text(self, talisman: CharacterTalisman) -> str:
        """보유 행 스탯 표시 문구"""

        spec: TalismanSpec = self._specs_by_name[talisman.talisman_key]
        return f"{STAT_SPECS[spec.stat_key]} +{spec.level_stats[talisman.level]:g}"

    def _add_talisman(self) -> None:
        """기본 부적 추가"""

        first_spec: TalismanSpec | None = self._first_available_spec()
        if first_spec is None:
            return

        talisman = CharacterTalisman(
            talisman_key=first_spec.name,
            level=0,
        )
        self._profile.talismans.append(talisman)
        self._selected_talisman_id = talisman.id
        self._selected_grade = first_spec.grade
        self._render_selector()
        self._render_owned()
        self._changes.saved_value_changed()

    def _select_talisman(self, talisman: CharacterTalisman) -> None:
        """보유 목록 선택 부적 전환"""

        if self._selected_talisman_id == talisman.id:
            return

        self._selected_talisman_id = talisman.id
        self._selected_grade = self._specs_by_name[talisman.talisman_key].grade
        self._render_selector()
        self._refresh_owned_selection()

    def _on_level(
        self,
        field: StepperField,
        talisman: CharacterTalisman,
        stat_label: QLabel,
    ) -> None:
        """레벨 변경 시 모델 반영"""

        level: int = max(0, min(MAX_TALISMAN_LEVEL, int(field.number())))
        field.set_number(float(level))
        if talisman.level == level:
            return

        talisman.level = level
        self._refresh_talisman_stat_labels(talisman, stat_label)

        if talisman.id in self._profile.equipped.talisman_ids:
            self._changes.stats_changed()

        else:
            self._changes.saved_value_changed()

    def _finish_level(
        self,
        field: StepperField,
        talisman: CharacterTalisman,
        stat_label: QLabel,
    ) -> None:
        """레벨 입력 종료 시 표시값 정규화"""

        field.set_number(float(talisman.level))
        self._refresh_talisman_stat_labels(talisman, stat_label)

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

        changed: bool = False
        if talisman.id in self._profile.equipped.talisman_ids:
            changed_index: int = self._profile.equipped.talisman_ids.index(talisman.id)
            self._profile.equipped.talisman_ids.remove(talisman.id)
            changed = True

        elif len(
            self._profile.equipped.talisman_ids
        ) < MAX_EQUIPPED_TALISMAN_COUNT and not self._has_equipped_talisman_key(
            talisman,
            talisman.talisman_key,
        ):
            changed_index = len(self._profile.equipped.talisman_ids)
            self._profile.equipped.talisman_ids.append(talisman.id)
            changed = True

        if not changed:
            return

        self._refresh_slots(start_index=changed_index)
        self._render_owned()
        self._changes.stats_changed()

    def _delete_talisman(self, talisman: CharacterTalisman) -> None:
        """보유 부적 삭제 및 장착 참조 제거"""

        equipped: bool = talisman.id in self._profile.equipped.talisman_ids
        equipped_index: int | None = (
            self._profile.equipped.talisman_ids.index(talisman.id) if equipped else None
        )
        removed_index: int = self._profile.talismans.index(talisman)
        self._profile.talismans = [
            current_talisman
            for current_talisman in self._profile.talismans
            if current_talisman.id != talisman.id
        ]

        self._profile.equipped.talisman_ids = [
            talisman_id
            for talisman_id in self._profile.equipped.talisman_ids
            if talisman_id != talisman.id
        ]

        if self._selected_talisman_id == talisman.id:
            next_index: int = min(removed_index, len(self._profile.talismans) - 1)
            self._selected_talisman_id = (
                self._profile.talismans[next_index].id
                if self._profile.talismans
                else None
            )

        if equipped_index is not None:
            self._refresh_slots(start_index=equipped_index)

        self._render_selector()
        self._render_owned()
        if equipped:
            self._changes.stats_changed()

        else:
            self._changes.saved_value_changed()

    def _unequip(self, talisman: CharacterTalisman) -> None:
        """슬롯에서 장착 해제"""

        if talisman.id in self._profile.equipped.talisman_ids:
            equipped_index: int = self._profile.equipped.talisman_ids.index(talisman.id)
            self._profile.equipped.talisman_ids.remove(talisman.id)

        else:
            raise ValueError("equipped talisman is not available")

        self._refresh_slots(start_index=equipped_index)
        self._render_owned()
        self._changes.stats_changed()
