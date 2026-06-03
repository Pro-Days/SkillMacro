"""칭호·레벨·경지 탭"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui import sample_data
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    CharComboBox,
    FlowLayout,
    SegButton,
    StepperField,
)


class _TitleItem(QFrame):
    """칭호 1개 (이름 + 스탯 3슬롯 + 장착/삭제)"""

    def __init__(
        self,
        parent: QWidget,
        data: sample_data.TitleData,
        equip_group: QButtonGroup,
        on_equip: "TitleTab",
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charTitleItem")
        self.setProperty("equipped", data.equipped)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 헤더: 이름 입력 + 장착 라디오 + 삭제
        head = QHBoxLayout()
        head.setSpacing(10)

        name_edit: QLineEdit = QLineEdit(data.name, self)
        name_edit.setObjectName("charTitleName")
        name_edit.setFont(CustomFont(12, bold=True))

        self.equip_radio: QRadioButton = QRadioButton("장착", self)
        self.equip_radio.setObjectName("charEquipToggle")
        self.equip_radio.setFont(CustomFont(10))
        self.equip_radio.setChecked(data.equipped)
        equip_group.addButton(self.equip_radio)
        self.equip_radio.clicked.connect(lambda: on_equip.set_equipped(self))

        delete_btn: StyledButton = StyledButton(self, "삭제", kind="danger", point_size=9)

        head.addWidget(name_edit, 1)
        head.addWidget(self.equip_radio)
        head.addWidget(delete_btn)
        layout.addLayout(head)

        # 스탯 3슬롯
        for slot_index in range(3):
            stat, value = data.slots[slot_index] if slot_index < len(data.slots) else (None, "")
            layout.addLayout(self._build_slot_row(slot_index + 1, stat, value))

    def _build_slot_row(self, number: int, stat: str | None, value: str) -> QHBoxLayout:
        """스탯 슬롯 한 줄 (번호 + 콤보 + 수치)"""

        row = QHBoxLayout()
        row.setSpacing(10)

        index_label: QLabel = QLabel(str(number), self)
        index_label.setObjectName("charOptIndex")
        index_label.setFont(CustomFont(9, bold=True))
        index_label.setFixedWidth(24)

        combo: CharComboBox = CharComboBox(self, list(sample_data.TITLE_STATS))
        if stat and stat in sample_data.TITLE_STATS:
            combo.setCurrentText(stat)

        value_field: StepperField = StepperField(self, value or "0", max_width=140)

        row.addWidget(index_label)
        row.addWidget(combo, 1)
        row.addWidget(value_field)
        return row

    def set_equipped_style(self, equipped: bool) -> None:
        """장착 강조 스타일 갱신"""

        self.setProperty("equipped", equipped)
        self.style().unpolish(self)
        self.style().polish(self)


class TitleTab(QFrame):
    """칭호·레벨·경지 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 레벨 · 경지 카드
        realm_card: CharCard = CharCard(self, "레벨 · 경지")

        level_label: QLabel = QLabel("캐릭터 레벨", self)
        level_label.setObjectName("charFieldLabel")
        level_label.setFont(CustomFont(9, bold=True))
        realm_card.add_widget(level_label)

        level_field: StepperField = StepperField(self, "180", unit="Lv", max_width=240)
        realm_card.add_widget(level_field)

        seg_label: QLabel = QLabel("경지", self)
        seg_label.setObjectName("charFieldLabel")
        seg_label.setFont(CustomFont(9, bold=True))
        realm_card.add_widget(seg_label)

        realm_card.add_widget(self._build_realm_seg())
        layout.addWidget(realm_card)

        # 칭호 카드
        self._title_card: CharCard = CharCard(self, "칭호")
        self._equip_group: QButtonGroup = QButtonGroup(self)
        self._equip_group.setExclusive(True)
        self._title_items: list[_TitleItem] = []

        for data in sample_data.default_titles():
            item: _TitleItem = _TitleItem(self, data, self._equip_group, self)
            self._title_items.append(item)
            self._title_card.add_widget(item)

        add_title_btn: StyledButton = StyledButton(self, "+ 칭호 추가", kind="normal", point_size=9)
        self._title_card.add_widget(add_title_btn)
        layout.addWidget(self._title_card)

        layout.addStretch(1)

    def _build_realm_seg(self) -> QWidget:
        """경지 세그먼트 버튼 그룹"""

        container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(container, margin=0, spacing=8)

        # 폭이 좁으면 자동 줄바꿈
        self._realm_buttons: list[SegButton] = []
        for index, realm in enumerate(sample_data.REALMS):
            sub: str = f"Lv {realm.min_level}+ · 단전 {realm.danjeon}"
            button: SegButton = SegButton(container, realm.label, index, self._pick_realm, sub_text=sub)
            button.setChecked(index == sample_data.DEFAULT_REALM_INDEX)
            self._realm_buttons.append(button)
            flow.addWidget(button)
        container.setLayout(flow)
        return container

    def _pick_realm(self, index: int) -> None:
        """경지 선택 시 활성 버튼 갱신"""

        for i, button in enumerate(self._realm_buttons):
            button.setChecked(i == index)

    def set_equipped(self, item: _TitleItem) -> None:
        """장착 칭호 단일 선택 강조 처리"""

        for title_item in self._title_items:
            title_item.set_equipped_style(title_item is item)
