from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import STAT_SPECS, StatKey
from app.scripts.character_models import (
    AdditionalStatGroup,
    AdditionalStatLine,
    CharacterProfile,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.change_handler import CharacterChangeHandler
from app.scripts.ui.character_ui.constants import STAT_LABEL_TO_KEY
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.widgets import CharCard, CharComboBox, StepperField


class _AdditionalStatGroupItem(QFrame):
    """추가 스탯 그룹 입력 카드"""

    def __init__(
        self,
        parent: QWidget,
        index: int,
        group: AdditionalStatGroup,
        changes: CharacterChangeHandler,
        on_delete: Callable[[int], None],
        on_rebuild: Callable[[], None],
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charStatGroupItem")
        self._group: AdditionalStatGroup = group
        self._changes: CharacterChangeHandler = changes
        self._on_rebuild: Callable[[], None] = on_rebuild

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(10)

        self._name_edit: QLineEdit = QLineEdit(group.name, self)
        self._name_edit.setObjectName("charTitleName")
        self._name_edit.setFont(CustomFont(12, bold=True))
        self._name_edit.editingFinished.connect(self._commit_name)

        delete_group_btn: StyledButton = StyledButton(
            self,
            "그룹 삭제",
            kind="danger",
            point_size=9,
        )
        delete_group_btn.clicked.connect(
            lambda _checked=False, group_index=index: on_delete(group_index)
        )

        head.addWidget(self._name_edit, 1)
        head.addWidget(delete_group_btn)
        layout.addLayout(head)

        for stat_index, stat in enumerate(group.stats):
            layout.addLayout(self._build_stat_row(stat_index, stat))

        add_stat_btn: StyledButton = StyledButton(
            self,
            "+ 스탯 추가",
            kind="normal",
            point_size=9,
        )
        add_stat_btn.clicked.connect(self._add_stat)
        layout.addWidget(add_stat_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def _build_stat_row(
        self,
        index: int,
        stat: AdditionalStatLine,
    ) -> QHBoxLayout:
        """추가 스탯 입력 행 구성"""

        row = QHBoxLayout()
        row.setSpacing(10)

        combo: CharComboBox = CharComboBox(self, list(STAT_SPECS.values()))
        combo.setCurrentText(STAT_SPECS[stat.stat_key])

        value_field: StepperField = StepperField(
            self,
            f"{stat.value:g}",
            max_width=160,
        )

        combo.currentTextChanged.connect(
            lambda text, target=stat: self._set_stat_key(target, text)
        )
        value_field.value_changed.connect(
            lambda target=stat, field=value_field: self._set_stat_value(
                target,
                field.number(),
            )
        )

        delete_btn: StyledButton = StyledButton(
            self,
            "삭제",
            kind="danger",
            point_size=9,
        )
        delete_btn.setFixedWidth(54)
        delete_btn.clicked.connect(
            lambda _checked=False, row_index=index: self._remove_stat(row_index)
        )

        row.addWidget(combo, 1)
        row.addWidget(value_field)
        row.addWidget(delete_btn)
        return row

    def _commit_name(self) -> None:
        """그룹명 변경 반영"""

        name: str = self._name_edit.text().strip()
        if not name:
            self._name_edit.setText(self._group.name)
            return

        if self._group.name == name:
            return

        self._group.name = name
        self._name_edit.setText(name)
        self._changes.saved_value_changed()

    def _set_stat_key(self, stat: AdditionalStatLine, label: str) -> None:
        """추가 스탯 종류 변경 반영"""

        stat_key: StatKey = STAT_LABEL_TO_KEY[label]
        if stat.stat_key == stat_key:
            return

        stat.stat_key = stat_key
        self._changes.stats_changed()

    def _set_stat_value(self, stat: AdditionalStatLine, value: float) -> None:
        """추가 스탯 값 변경 반영"""

        if stat.value == value:
            return

        stat.value = value
        self._changes.stats_changed()

    def _add_stat(self) -> None:
        """추가 스탯 입력 행 생성"""

        self._group.stats.append(
            AdditionalStatLine(stat_key=StatKey.ATTACK, value=0.0)
        )
        self._on_rebuild()
        self._changes.saved_value_changed()

    def _remove_stat(self, index: int) -> None:
        """추가 스탯 입력 행 삭제"""

        removed: AdditionalStatLine = self._group.stats.pop(index)
        self._on_rebuild()
        if removed.value == 0.0:
            self._changes.saved_value_changed()
            return

        self._changes.stats_changed()


class AdditionalStatsTab(CharacterTab):
    """추가 스탯 그룹 탭"""

    def __init__(
        self,
        parent: QWidget,
        changes: CharacterChangeHandler,
        profile: CharacterProfile,
    ) -> None:
        super().__init__(parent, changes, profile)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card: CharCard = CharCard(self, "추가 스탯 그룹")
        add_group_btn: StyledButton = StyledButton(
            self,
            "+ 그룹 추가",
            kind="normal",
            point_size=9,
        )
        add_group_btn.clicked.connect(self._add_group)
        card.add_header_widget(add_group_btn)

        self._groups_container: QWidget = QWidget(self)
        self._groups_layout = QVBoxLayout(self._groups_container)
        self._groups_layout.setContentsMargins(0, 0, 0, 0)
        self._groups_layout.setSpacing(10)
        card.add_widget(self._groups_container)

        layout.addWidget(card)
        layout.addStretch(1)

        self._render_groups()

    def set_profile(self, profile: CharacterProfile) -> None:
        """선택 캐릭터 모델 반영"""

        self._profile = profile
        self._render_groups()

    def _render_groups(self) -> None:
        """추가 스탯 그룹 목록 재구성"""

        while self._groups_layout.count():
            item = self._groups_layout.takeAt(0)
            widget: QWidget | None = item.widget()  # type: ignore[assignment]
            if widget is not None:
                widget.deleteLater()

        if not self._profile.additional_stat_groups:
            empty_label: QLabel = QLabel("비어 있음", self._groups_container)
            empty_label.setObjectName("charMuted")
            empty_label.setFont(CustomFont(10, bold=True))
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._groups_layout.addWidget(empty_label)
            return

        for index, group in enumerate(self._profile.additional_stat_groups):
            self._groups_layout.addWidget(
                _AdditionalStatGroupItem(
                    self._groups_container,
                    index,
                    group,
                    self._changes,
                    self._delete_group,
                    self._render_groups,
                )
            )

    def _add_group(self) -> None:
        """추가 스탯 그룹 생성"""

        existing_names: set[str] = {
            group.name for group in self._profile.additional_stat_groups
        }
        index: int = 1
        name: str = f"추가 스탯 그룹 {index}"
        while name in existing_names:
            index += 1
            name = f"추가 스탯 그룹 {index}"

        self._profile.additional_stat_groups.append(AdditionalStatGroup(name=name))
        self._render_groups()
        self._changes.saved_value_changed()

    def _delete_group(self, index: int) -> None:
        """추가 스탯 그룹 삭제"""

        removed: AdditionalStatGroup = self._profile.additional_stat_groups.pop(index)
        self._render_groups()
        if any(stat.value != 0.0 for stat in removed.stats):
            self._changes.stats_changed()
            return

        self._changes.saved_value_changed()
