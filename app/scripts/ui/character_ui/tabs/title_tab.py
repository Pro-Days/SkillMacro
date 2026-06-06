"""기본정보와 칭호 탭"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import (
    REALM_TIER_SPECS,
    STAT_SPECS,
    RealmTier,
    StatKey,
)
from app.scripts.character_models import (
    TITLE_STAT_SLOT_COUNT,
    CharacterProfile,
    CharacterTitle,
    TitleStatSlot,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.constants import STAT_CHOICE_LABELS, STAT_LABEL_TO_KEY
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    CharComboBox,
    FlowLayout,
    ResponsiveColumnsBox,
    SegButton,
    StepperField,
)

_TITLE_ITEM_WIDTH: int = 360
_TITLE_ITEM_HEIGHT: int = 210


class _TitleItem(QFrame):
    """칭호 1개 입력 카드"""

    def __init__(
        self,
        parent: QWidget,
        title: CharacterTitle,
        equipped: bool,
        equip_group: QButtonGroup,
        on_changed: Callable[[], None],
        on_equip: Callable[[CharacterTitle], None],
        on_delete: Callable[[CharacterTitle], None],
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charTitleItem")
        self.setProperty("equipped", equipped)
        self.setFixedSize(_TITLE_ITEM_WIDTH, _TITLE_ITEM_HEIGHT)

        self._title: CharacterTitle = title
        self._on_changed: Callable[[], None] = on_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 칭호명과 장착/삭제 버튼 구성
        head = QHBoxLayout()
        head.setSpacing(10)

        name_edit: QLineEdit = QLineEdit(title.name, self)
        name_edit.setObjectName("charTitleName")
        name_edit.setFont(CustomFont(12, bold=True))
        name_edit.editingFinished.connect(
            lambda field=name_edit: self._on_name_changed(field.text())
        )

        self.equip_radio: QPushButton = QPushButton("장착", self)
        self.equip_radio.setObjectName("charEquipToggle")
        self.equip_radio.setFont(CustomFont(10))
        self.equip_radio.setCheckable(True)
        self.equip_radio.setChecked(equipped)
        self.equip_radio.setCursor(Qt.CursorShape.PointingHandCursor)
        equip_group.addButton(self.equip_radio)
        self.equip_radio.clicked.connect(lambda: on_equip(title))

        delete_btn: StyledButton = StyledButton(
            self, "삭제", kind="danger", point_size=9
        )
        delete_btn.clicked.connect(lambda: on_delete(title))

        head.addWidget(name_edit, 1)
        head.addWidget(self.equip_radio)
        head.addWidget(delete_btn)
        layout.addLayout(head)

        # 칭호 스탯 3슬롯 구성
        self._slot_combos: list[CharComboBox] = []
        self._slot_fields: list[StepperField] = []
        for slot_index in range(TITLE_STAT_SLOT_COUNT):
            layout.addLayout(self._build_slot_row(slot_index))

    def _build_slot_row(self, slot_index: int) -> QHBoxLayout:
        """칭호 스탯 한 줄 구성"""

        row = QHBoxLayout()
        row.setSpacing(10)

        index_label: QLabel = QLabel(str(slot_index + 1), self)
        index_label.setObjectName("charOptIndex")
        index_label.setFont(CustomFont(9, bold=True))
        index_label.setFixedWidth(24)

        combo: CharComboBox = CharComboBox(
            self,
            list(STAT_CHOICE_LABELS),
        )

        slot: TitleStatSlot | None = self._title.slots[slot_index]
        if slot is not None:
            combo.setCurrentText(STAT_SPECS[slot.stat_key])

        value_text: str = "0" if slot is None else f"{slot.value:g}"
        value_field: StepperField = StepperField(self, value_text, max_width=140)

        combo.currentIndexChanged.connect(lambda _index: self._sync_slots())
        value_field.value_changed.connect(self._sync_slots)

        self._slot_combos.append(combo)
        self._slot_fields.append(value_field)

        row.addWidget(index_label)
        row.addWidget(combo, 1)
        row.addWidget(value_field)
        return row

    def _on_name_changed(self, text: str) -> None:
        """칭호명 모델 반영"""

        self._title.name = text
        self._on_changed()

    def _sync_slots(self) -> None:
        """칭호 스탯 슬롯 모델 반영"""

        slots: list[TitleStatSlot | None] = []
        for combo, field in zip(self._slot_combos, self._slot_fields):
            if combo.currentIndex() == 0:
                slots.append(None)
                continue

            stat_key: StatKey = STAT_LABEL_TO_KEY[combo.currentText()]
            slots.append(TitleStatSlot(stat_key=stat_key, value=field.number()))

        self._title.slots = tuple(slots)
        self._on_changed()

    def set_equipped_style(self, equipped: bool) -> None:
        """장착 강조 스타일 갱신"""

        self.setProperty("equipped", equipped)
        self.equip_radio.setChecked(equipped)
        self.style().unpolish(self)
        self.style().polish(self)


class TitleTab(CharacterTab):
    """기본정보와 칭호 탭"""

    def __init__(self, parent: QWidget, on_changed: Callable[[], None]) -> None:
        super().__init__(parent)

        self._profile: CharacterProfile | None = None
        self._on_changed: Callable[[], None] = on_changed
        self._loading: bool = False

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(16)

        self._build()

    def _build(self) -> None:
        """탭 기본 위젯 구성"""

        # 레벨·경지·이름 카드 구성
        realm_card: CharCard = CharCard(self, "레벨 · 경지")

        name_label: QLabel = QLabel("캐릭터 이름", self)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        realm_card.add_widget(name_label)

        self._name_edit: QLineEdit = QLineEdit(self)
        self._name_edit.setObjectName("charTitleName")
        self._name_edit.setFont(CustomFont(12, bold=True))
        self._name_edit.editingFinished.connect(
            lambda field=self._name_edit: self._on_name_changed(field.text())
        )
        realm_card.add_widget(self._name_edit)

        level_label: QLabel = QLabel("캐릭터 레벨", self)
        level_label.setObjectName("charFieldLabel")
        level_label.setFont(CustomFont(9, bold=True))
        realm_card.add_widget(level_label)

        self._level_field: StepperField = StepperField(
            self, "0", unit="Lv", max_width=100
        )
        self._level_field.input.setValidator(QIntValidator(0, 1_000_000, self))
        self._level_field.value_changed.connect(self._on_level_changed)
        realm_card.add_widget(self._level_field)

        seg_label: QLabel = QLabel("경지", self)
        seg_label.setObjectName("charFieldLabel")
        seg_label.setFont(CustomFont(9, bold=True))
        realm_card.add_widget(seg_label)

        realm_card.add_widget(self._build_realm_seg())
        self._layout.addWidget(realm_card)

        # 칭호 목록 카드 구성
        self._title_card: CharCard = CharCard(self, "칭호")
        self._equip_group: QButtonGroup = QButtonGroup(self)
        self._equip_group.setExclusive(True)
        self._title_items: list[_TitleItem] = []

        self._titles_container: ResponsiveColumnsBox = ResponsiveColumnsBox(
            self,
            min_column_width=_TITLE_ITEM_WIDTH,
            spacing=12,
            fill=False,
            center=True,
        )
        self._title_card.add_widget(self._titles_container)

        add_title_btn: StyledButton = StyledButton(
            self, "+ 칭호 추가", kind="normal", point_size=9
        )
        add_title_btn.clicked.connect(self._add_title)
        self._title_card.add_widget(add_title_btn)
        self._layout.addWidget(self._title_card)

        self._layout.addStretch(1)

    def _build_realm_seg(self) -> QWidget:
        """경지 세그먼트 버튼 그룹"""

        container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(container, margin=0, spacing=8)

        self._realm_buttons: list[SegButton] = []
        for index, realm in enumerate(REALM_TIER_SPECS):
            spec = REALM_TIER_SPECS[realm]
            sub: str = f"Lv {spec.min_level}+ · 단전 {spec.danjeon_points}"
            button: SegButton = SegButton(
                container,
                spec.label,
                index,
                self._pick_realm,
                sub_text=sub,
            )
            self._realm_buttons.append(button)
            flow.addWidget(button)

        container.setLayout(flow)

        uniform_width: int = max(
            button.sizeHint().width() for button in self._realm_buttons
        )
        for button in self._realm_buttons:
            button.setFixedWidth(uniform_width)

        return container

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        self._loading = True
        self._profile = profile

        if profile is None:
            self.setEnabled(False)
            self._name_edit.setText("")
            self._level_field.set_number(0)
            self._render_titles()
            self._loading = False
            return

        self.setEnabled(True)
        self._name_edit.setText(profile.name)
        self._level_field.set_number(float(profile.level))
        self._sync_realm_buttons()
        self._render_titles()
        self._loading = False

    def _sync_realm_buttons(self) -> None:
        """모델 경지 기준 버튼 상태 동기화"""

        if self._profile is None:
            return

        realm_values: list[RealmTier] = list(REALM_TIER_SPECS.keys())
        current_index: int = realm_values.index(self._profile.realm)
        for index, button in enumerate(self._realm_buttons):
            button.setChecked(index == current_index)

    def _render_titles(self) -> None:
        """칭호 목록 재구성"""

        while self._titles_container.flow.count():
            item = self._titles_container.flow.takeAt(0)
            widget: QWidget | None = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._title_items = []
        if self._profile is None:
            self._titles_container.sync_height()
            return

        for title in self._profile.titles:
            item = _TitleItem(
                self,
                title,
                title.id == self._profile.equipped.title_id,
                self._equip_group,
                self._notify_changed,
                self._equip_title,
                self._delete_title,
            )
            self._title_items.append(item)
            self._titles_container.addWidget(item)

        self._titles_container.sync_height()

    def _notify_changed(self) -> None:
        """외부 변경 콜백 호출"""

        if self._loading:
            return

        self._on_changed()

    def _on_name_changed(self, text: str) -> None:
        """캐릭터 이름 모델 반영"""

        if self._profile is None or self._loading:
            return

        self._profile.name = text
        self._on_changed()

    def _on_level_changed(self) -> None:
        """캐릭터 레벨 모델 반영"""

        if self._profile is None or self._loading:
            return

        self._profile.level = int(self._level_field.number())
        self._on_changed()

    def _pick_realm(self, index: int) -> None:
        """경지 선택 모델 반영"""

        if self._profile is None:
            return

        realm_values: list[RealmTier] = list(REALM_TIER_SPECS.keys())
        self._profile.realm = realm_values[index]
        self._sync_realm_buttons()
        self._on_changed()

    def _add_title(self) -> None:
        """칭호 추가"""

        if self._profile is None:
            return

        title: CharacterTitle = CharacterTitle(name="새 칭호")
        self._profile.titles.append(title)
        if self._profile.equipped.title_id is None:
            self._profile.equipped.title_id = title.id

        self._render_titles()
        self._on_changed()

    def _equip_title(self, title: CharacterTitle) -> None:
        """칭호 장착"""

        if self._profile is None:
            return

        self._profile.equipped.title_id = title.id
        for item in self._title_items:
            item.set_equipped_style(item._title is title)

        self._on_changed()

    def _delete_title(self, title: CharacterTitle) -> None:
        """칭호 삭제"""

        if self._profile is None:
            return

        self._profile.titles = [
            current_title
            for current_title in self._profile.titles
            if current_title.id != title.id
        ]
        if self._profile.equipped.title_id == title.id:
            self._profile.equipped.title_id = None

        self._render_titles()
        self._on_changed()
