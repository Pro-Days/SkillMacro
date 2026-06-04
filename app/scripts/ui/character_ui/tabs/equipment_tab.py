"""장비 탭 (좌: 장비창 9슬롯 / 우: 선택 장비 상세 · 장비 교체 화면)

콘텐츠 규칙은 계획 파일을 따른다:
- 슬롯마다 보유 장비 여러 개를 두고, 장비 교체로 선택해 장착한다
- 재련 = 단계가 아닌 부위별 허용 스탯 입력
- 반지/귀걸이 = 자유 기본 스탯 라인
- 잠재/추가능력 = 투구·갑옷·허리띠·신발만
- 등급(기본/찬란한) = 무기·방어구만
"""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui import sample_data
from app.scripts.ui.character_ui.widgets import (
    CharComboBox,
    FlowLayout,
    ResponsiveColumnsBox,
    StaticValueField,
    StepperField,
)

_ICON_STYLE: str = (
    "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #cbb389, stop:1 #8a6b3f);"
    "border: 1px solid #c8c4be; border-radius: 6px;"
)
_ICON_STYLE_MUTED: str = (
    "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #cfcabf, stop:1 #b6ad9c);"
    "border: 1px solid #c8c4be; border-radius: 6px;"
)

# 장비창 고정 폭
_EQUIP_WINDOW_WIDTH: int = 232
_STACK_THRESHOLD: int = 560


class _EquipSlot(QFrame):
    """장비창 슬롯 1칸 (장착 장비 또는 빈 상태 표시)"""

    def __init__(
        self,
        parent: QWidget,
        slot: sample_data.EquipSlotData,
        index: int,
        tab: "EquipmentTab",
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charEquipSlot")
        self.setProperty("active", False)
        self.setProperty("empty", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._index: int = index
        self._tab: "EquipmentTab" = tab

        box = QVBoxLayout(self)
        box.setContentsMargins(6, 8, 6, 8)
        box.setSpacing(3)

        self._icon: QLabel = QLabel(self)
        self._icon.setFixedSize(34, 34)
        box.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._type_label: QLabel = QLabel(self)
        self._type_label.setObjectName("charEquipType")
        self._type_label.setFont(CustomFont(9, bold=True))
        self._type_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(self._type_label)

        self._meta_label: QLabel = QLabel(self)
        self._meta_label.setObjectName("charEquipMeta")
        self._meta_label.setFont(CustomFont(8))
        self._meta_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(self._meta_label)

        self.update_from_slot(slot)

    def update_from_slot(self, slot: sample_data.EquipSlotData) -> None:
        """슬롯 상태(장착 장비/빈 상태)에 맞춰 표시 갱신"""

        item = slot.equipped()
        empty: bool = item is None
        self._icon.setStyleSheet(_ICON_STYLE_MUTED if empty else _ICON_STYLE)
        self._type_label.setText(slot.type)
        self._meta_label.setText("비어 있음" if empty else f"Lv {item.level}")
        self.setProperty("empty", empty)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_active(self, active: bool) -> None:
        """선택 강조 갱신"""

        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """슬롯 클릭 시 상세 전환"""

        self._tab.select_slot(self._index)
        super().mousePressEvent(event)


class _EquipPickCard(QFrame):
    """장비 교체 화면의 보유 장비 카드 (클릭 시 장착)"""

    def __init__(
        self,
        parent: QWidget,
        slot: sample_data.EquipSlotData,
        item: sample_data.EquipItemData,
        index: int,
        tab: "EquipmentTab",
        has_grade: bool,
        removable: bool,
        current: bool,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charEquipPick")
        self.setProperty("current", current)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._index: int = index
        self._tab: "EquipmentTab" = tab

        card = QVBoxLayout(self)
        card.setContentsMargins(14, 14, 14, 14)
        card.setSpacing(7)

        head = QHBoxLayout()
        head.setSpacing(14)

        icon: QLabel = QLabel(self)
        icon.setFixedSize(44, 44)
        icon.setStyleSheet(_ICON_STYLE)
        head.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        display_name: str = (
            "찬란한 " if has_grade and item.grade == "찬란한" else ""
        ) + item.name
        name_label: QLabel = QLabel(display_name, self)
        name_label.setObjectName("charDetailName")
        name_label.setFont(CustomFont(13, bold=True))
        name_row.addWidget(name_label)
        if slot.reforge:
            reforge_label: QLabel = QLabel(f"+{item.reforge_step}", self)
            reforge_label.setObjectName("charPickReforge")
            reforge_label.setFont(CustomFont(10, bold=True))
            name_row.addWidget(reforge_label)
        name_row.addStretch(1)
        head.addLayout(name_row, 1)

        if removable:
            del_btn: StyledButton = StyledButton(
                self, "삭제", kind="danger", point_size=9
            )
            del_btn.clicked.connect(lambda: tab.remove_owned(index))
            head.addWidget(del_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        card.addLayout(head)

        info_rows: list[tuple[str, list[str]]] = []
        if item.scroll_stat:
            info_rows.append(("주문서", item.scroll_stat))
        if item.potential:
            info_rows.append(("잠재능력", item.potential))
        if item.additional:
            info_rows.append(("추가능력", item.additional))
        if info_rows:
            info_box = QVBoxLayout()
            info_box.setContentsMargins(58, 0, 0, 0)
            info_box.setSpacing(7)
            for key_text, tokens in info_rows:
                info_box.addLayout(self._info_row(key_text, tokens))
            card.addLayout(info_box)

    def _info_row(self, key_text: str, tokens: list[str]) -> QHBoxLayout:
        """라벨 + 스탯 값 줄바꿈 행"""

        line = QHBoxLayout()
        line.setSpacing(8)

        key_label: QLabel = QLabel(key_text, self)
        key_label.setObjectName("charPickInfoKey")
        key_label.setFont(CustomFont(9, bold=True))
        key_label.setFixedWidth(52)

        value_text: str = "   ".join(token.replace(" ", " ") for token in tokens)
        value_label: QLabel = QLabel(value_text, self)
        value_label.setObjectName("charPickInfoVal")
        value_label.setFont(CustomFont(9))
        value_label.setWordWrap(True)
        value_label.setMinimumWidth(0)

        line.addWidget(key_label, 0, Qt.AlignmentFlag.AlignTop)
        line.addWidget(value_label, 1)
        return line

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """카드 클릭 시 해당 장비 장착"""

        self._tab.select_owned(self._index)
        super().mousePressEvent(event)


class EquipmentTab(QFrame):
    """장비 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._slots_data: list[sample_data.EquipSlotData] = (
            sample_data.default_equip_slots()
        )
        self._active_index: int = 0
        self._picker_open: bool = False

        self._root_layout: QHBoxLayout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(18)
        self._root_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._equip_window: QFrame = self._build_equip_window()
        self._root_layout.addWidget(self._equip_window)
        self._root_layout.addWidget(self._build_detail_area(), 1)

        self._stacked: bool = False
        self._render_slots()
        self._render_detail()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """중앙 폭이 좁아지면 장비창과 상세를 세로 1열로 전환"""

        super().resizeEvent(event)
        self._apply_responsive(self.width())

    def _apply_responsive(self, width: int) -> None:
        """기본 상태 중앙 폭보다 좁으면 세로 1열, 넓으면 가로 2열"""

        should_stack: bool = width < _STACK_THRESHOLD
        if should_stack == self._stacked:
            return
        self._stacked = should_stack

        # 장비창은 두 모드 모두 고정 폭 유지, 세로 1열일 때만 위쪽 중앙 배치
        if should_stack:
            self._root_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._root_layout.setAlignment(
                self._equip_window, Qt.AlignmentFlag.AlignHCenter
            )
        else:
            self._root_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._root_layout.setAlignment(
                self._equip_window, Qt.AlignmentFlag.AlignTop
            )

    # 좌측 장비창

    def _build_equip_window(self) -> QFrame:
        """좌측 장비창 (2열 슬롯)"""

        window: QFrame = QFrame(self)
        window.setObjectName("charEquipWindow")
        window.setFixedWidth(_EQUIP_WINDOW_WIDTH)

        grid = QHBoxLayout(window)
        grid.setContentsMargins(12, 14, 12, 14)
        grid.setSpacing(8)

        self._left_col = QVBoxLayout()
        self._left_col.setSpacing(10)
        self._right_col = QVBoxLayout()
        self._right_col.setSpacing(10)

        grid.addLayout(self._left_col, 1)
        grid.addLayout(self._right_col, 1)

        self._slot_widgets: dict[int, _EquipSlot] = {}
        return window

    def _render_slots(self) -> None:
        """슬롯 위젯 배치"""

        for column_layout, indices in (
            (self._left_col, sample_data.EQUIP_COL_LEFT),
            (self._right_col, sample_data.EQUIP_COL_RIGHT),
        ):
            for index in indices:
                slot: _EquipSlot = _EquipSlot(
                    self, self._slots_data[index], index, self
                )
                self._slot_widgets[index] = slot
                column_layout.addWidget(slot)
            column_layout.addStretch(1)
        self._highlight_active()

    def _highlight_active(self) -> None:
        """현재 선택 슬롯 강조"""

        for index, slot in self._slot_widgets.items():
            slot.set_active(index == self._active_index)

    def _refresh_active_slot(self) -> None:
        """장착 변경 후 현재 슬롯 타일 표시 갱신"""

        slot_widget = self._slot_widgets.get(self._active_index)
        if slot_widget is not None:
            slot_widget.update_from_slot(self._slots_data[self._active_index])

    def select_slot(self, index: int) -> None:
        """슬롯 선택 시 상세 갱신 (선택 화면은 닫는다)"""

        self._active_index = index
        self._picker_open = False
        self._highlight_active()
        self._render_detail()

    # 우측 상세

    def _build_detail_area(self) -> QFrame:
        """우측 상세 카드 (별도 스크롤 없이 본문 스크롤을 장비창과 공유)"""

        self._detail_content: QFrame = QFrame(self)
        self._detail_content.setObjectName("charCard")
        self._detail_layout = QVBoxLayout(self._detail_content)
        self._detail_layout.setContentsMargins(18, 18, 18, 18)
        self._detail_layout.setSpacing(0)
        return self._detail_content

    def _clear_detail(self) -> None:
        """상세 레이아웃 비우기"""

        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self._clear_sub_layout(item.layout())

    def _clear_sub_layout(self, layout) -> None:
        """중첩 레이아웃 정리"""

        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self._clear_sub_layout(item.layout())

    def _render_detail(self) -> None:
        """선택 장비 상세 / 장비 교체 화면 / 빈 상태 재구성"""

        self._clear_detail()
        slot: sample_data.EquipSlotData = self._slots_data[self._active_index]

        if self._picker_open:
            self._render_picker(slot)
            return

        item = slot.equipped()
        if item is None:
            self._render_empty(slot)
            return

        has_grade: bool = slot.type in sample_data.GRADE_TYPES
        has_potential: bool = slot.type in sample_data.POTENTIAL_TYPES

        self._detail_layout.addLayout(self._build_detail_head(slot, item, has_grade))

        self._detail_layout.addWidget(self._build_item_section(slot, item, has_grade))

        # 기본 스탯 + 재련: 공간이 남으면 기본 스탯 오른쪽에 재련을 나란히 배치
        base_group: ResponsiveColumnsBox = ResponsiveColumnsBox(
            self._detail_content, min_column_width=300, spacing=18
        )
        base_group.addWidget(self._build_base_section(slot, item))
        if slot.reforge:
            base_group.addWidget(self._build_reforge_section(slot, item))
        self._detail_layout.addWidget(base_group)

        if slot.scroll:
            self._detail_layout.addWidget(self._build_scroll_section(slot))

        # 잠재능력 + 추가능력: 공간이 남으면 나란히 배치
        if has_potential:
            option_group: ResponsiveColumnsBox = ResponsiveColumnsBox(
                self._detail_content, min_column_width=300, spacing=18
            )
            option_group.addWidget(
                self._build_option_section("잠재능력", sample_data.POTENTIAL_OPTS)
            )
            option_group.addWidget(
                self._build_option_section("추가능력", sample_data.ADDITIONAL_OPTS)
            )
            self._detail_layout.addWidget(option_group)

        self._detail_layout.addStretch(1)

    def _build_detail_head(
        self,
        slot: sample_data.EquipSlotData,
        item: sample_data.EquipItemData,
        has_grade: bool,
    ) -> QHBoxLayout:
        """상세 헤더 (아이콘 + 이름 + 교체 버튼)"""

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 12)
        head.setSpacing(12)

        icon: QLabel = QLabel(self)
        icon.setFixedSize(46, 46)
        icon.setStyleSheet(_ICON_STYLE)
        head.addWidget(icon)

        name_box = QVBoxLayout()
        name_box.setSpacing(4)
        display_name: str = (
            "찬란한 " if has_grade and item.grade == "찬란한" else ""
        ) + item.name
        name_label: QLabel = QLabel(display_name, self)
        name_label.setObjectName("charDetailName")
        name_label.setFont(CustomFont(15, bold=True))
        meta_label: QLabel = QLabel(slot.type, self)
        meta_label.setObjectName("charSub")
        meta_label.setFont(CustomFont(9))
        name_box.addWidget(name_label)
        name_box.addWidget(meta_label)
        head.addLayout(name_box)

        head.addStretch(1)
        change_btn: StyledButton = StyledButton(
            self, "장비 교체", kind="normal", point_size=9
        )
        change_btn.clicked.connect(self.open_picker)
        head.addWidget(change_btn)
        return head

    def _build_level_tier_row(self, item: sample_data.EquipItemData) -> QHBoxLayout:
        """레벨/티어 콤보박스 선택 행"""

        controls = QHBoxLayout()
        controls.setSpacing(8)

        level_caption: QLabel = QLabel("레벨", self)
        level_caption.setObjectName("charFieldLabel")
        level_caption.setFont(CustomFont(9, bold=True))
        controls.addWidget(level_caption)
        level_combo: CharComboBox = CharComboBox(
            self, [str(level) for level in sample_data.EQUIP_LEVELS], point_size=9
        )
        if item.level in sample_data.EQUIP_LEVELS:
            level_combo.setCurrentIndex(sample_data.EQUIP_LEVELS.index(item.level))
        level_combo.currentTextChanged.connect(self._pick_level)
        controls.addWidget(level_combo)

        controls.addSpacing(8)

        tier_caption: QLabel = QLabel("티어", self)
        tier_caption.setObjectName("charFieldLabel")
        tier_caption.setFont(CustomFont(9, bold=True))
        controls.addWidget(tier_caption)
        tier_combo: CharComboBox = CharComboBox(
            self, [str(tier) for tier in sample_data.EQUIP_TIERS], point_size=9
        )
        if item.tier in sample_data.EQUIP_TIERS:
            tier_combo.setCurrentIndex(sample_data.EQUIP_TIERS.index(item.tier))
        tier_combo.currentTextChanged.connect(self._pick_tier)
        controls.addWidget(tier_combo)

        controls.addStretch(1)
        return controls

    def _current_item(self) -> sample_data.EquipItemData | None:
        """현재 슬롯의 장착 장비"""

        return self._slots_data[self._active_index].equipped()

    def _pick_level(self, text: str) -> None:
        """선택한 장비 레벨을 현재 장비에 반영"""

        item = self._current_item()
        if item is not None:
            item.level = int(text)

    def _pick_tier(self, text: str) -> None:
        """선택한 장비 티어를 현재 장비에 반영"""

        item = self._current_item()
        if item is not None:
            item.tier = int(text)

    def _section(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        """제목이 있는 상세 섹션 컨테이너"""

        section: QFrame = QFrame(self)
        section.setObjectName("charEdSection")
        box = QVBoxLayout(section)
        box.setContentsMargins(0, 14, 0, 0)
        box.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        accent: QLabel = QLabel(section)
        accent.setObjectName("charEdAccent")
        accent.setFixedSize(4, 14)
        title_label: QLabel = QLabel(title, section)
        title_label.setObjectName("charEdTitle")
        title_label.setFont(CustomFont(10, bold=True))
        title_row.addWidget(accent)
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        box.addLayout(title_row)
        return section, box

    def _build_item_section(
        self,
        slot: sample_data.EquipSlotData,
        item: sample_data.EquipItemData,
        has_grade: bool,
    ) -> QFrame:
        """아이템 섹션 (레벨/티어 + 등급)"""

        section, box = self._section("아이템")

        # 등급(기본/찬란한)은 무기·방어구만. 공간이 남으면 레벨·티어 오른쪽에 등급을 배치
        if not has_grade:
            box.addLayout(self._build_level_tier_row(item))
            return section

        fields_group: ResponsiveColumnsBox = ResponsiveColumnsBox(
            section, min_column_width=160, spacing=18, fill=False
        )

        level_tier_block: QFrame = QFrame(section)
        level_tier_box = QVBoxLayout(level_tier_block)
        level_tier_box.setContentsMargins(0, 0, 0, 0)
        level_tier_box.setSpacing(0)
        level_tier_box.addLayout(self._build_level_tier_row(item))
        fields_group.addWidget(level_tier_block)

        grade_block: QFrame = QFrame(section)
        grade_box = QVBoxLayout(grade_block)
        grade_box.setContentsMargins(0, 0, 0, 0)
        grade_box.setSpacing(0)
        grade_box.addLayout(self._build_grade_row(item))
        fields_group.addWidget(grade_block)

        box.addWidget(fields_group)
        return section

    def _build_grade_row(self, item: sample_data.EquipItemData) -> QHBoxLayout:
        """등급 행 (레벨/티어처럼 라벨 + 찬란한 토글 버튼, ON 시 강조색)"""

        controls = QHBoxLayout()
        controls.setSpacing(8)

        caption: QLabel = QLabel("등급", self)
        caption.setObjectName("charFieldLabel")
        caption.setFont(CustomFont(9, bold=True))
        controls.addWidget(caption)

        grade_btn: QPushButton = QPushButton("찬란한", self)
        grade_btn.setObjectName("charEquipToggle")
        grade_btn.setFont(CustomFont(9))
        grade_btn.setCheckable(True)
        grade_btn.setChecked(item.grade == "찬란한")
        grade_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        grade_btn.clicked.connect(self._on_grade_toggle)
        controls.addWidget(grade_btn)

        controls.addStretch(1)
        return controls

    def _on_grade_toggle(self, active: bool) -> None:
        """찬란한 버튼 토글 시 등급 반영 및 표시 이름 갱신"""

        item = self._current_item()
        if item is not None:
            item.grade = "찬란한" if active else "기본"
        self._render_detail()

    def _build_base_section(
        self, slot: sample_data.EquipSlotData, item: sample_data.EquipItemData
    ) -> QFrame:
        """기본 스탯 섹션 (방어구/무기 자동 표시 vs 반지/귀걸이 자유 입력)"""

        section, box = self._section("기본 스탯")

        # 반지/귀걸이: 자유 스탯 라인
        if not item.base:
            self._free_rows = QVBoxLayout()
            self._free_rows.setSpacing(8)
            for stat, value in item.free_base:
                self._free_rows.addLayout(self._build_free_stat_row(stat, value))
            box.addLayout(self._free_rows)

            add_btn: StyledButton = StyledButton(
                section, "+ 스탯 추가", kind="normal", point_size=9
            )
            add_btn.clicked.connect(self._add_free_stat)
            box.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)
            return section

        # 무기·방어구: 자동 제공되는 읽기 전용 스탯 / 그 외(목걸이 등): 직접 입력
        auto_provided: bool = slot.type in sample_data.GRADE_TYPES

        flow: FlowLayout = FlowLayout(spacing=14)
        for label_text, value in item.base:
            flow.addWidget(
                self._build_labeled_field(label_text, str(value), readonly=auto_provided)
            )
        box.addLayout(flow)
        return section

    def _build_free_stat_row(self, stat: str | None, value: str) -> QHBoxLayout:
        """반지/귀걸이 자유 스탯 한 줄 (콤보 + 값)"""

        row = QHBoxLayout()
        row.setSpacing(10)
        combo: CharComboBox = CharComboBox(self, list(sample_data.TITLE_STATS))
        if stat and stat in sample_data.TITLE_STATS:
            combo.setCurrentText(stat)
        field: StepperField = StepperField(self, value or "0", max_width=140)
        row.addWidget(combo, 1)
        row.addWidget(field)
        return row

    def _add_free_stat(self) -> None:
        """자유 스탯 라인 추가"""

        self._free_rows.addLayout(self._build_free_stat_row(None, "0"))

    def _build_reforge_section(
        self, slot: sample_data.EquipSlotData, item: sample_data.EquipItemData
    ) -> QFrame:
        """재련 섹션 (부위/목걸이 종류별 허용 스탯 입력)"""

        section, box = self._section("재련")

        key: str = item.necklace_type if item.necklace_type else slot.type
        stats: tuple[str, ...] = sample_data.REFORGE_STATS.get(key, ())

        flow: FlowLayout = FlowLayout(spacing=14)
        # 맨 처음에 재련 단계(0~20강) 입력칸
        flow.addWidget(self._build_step_field(item.reforge_step))
        for stat in stats:
            flow.addWidget(self._build_labeled_field(stat, "0"))
        box.addLayout(flow)
        return section

    def _build_step_field(self, step: int) -> QWidget:
        """재련 단계(0~20강) 입력 묶음"""

        container: QFrame = QFrame(self)
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        name_label: QLabel = QLabel("단계", container)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        box.addWidget(name_label)

        field: StepperField = StepperField(container, str(step), unit="강")
        field.setFixedWidth(84)
        field.input.setValidator(QIntValidator(0, 20, field))
        box.addWidget(field)
        return container

    def _build_scroll_section(self, slot: sample_data.EquipSlotData) -> QFrame:
        """주문서 섹션 (행=종류, 열=% 단계, 칸=성공 횟수)"""

        section, box = self._section("주문서")

        scroll_set: sample_data.ScrollSet = sample_data.SCROLL_SETS[slot.scroll]

        wrap: QScrollArea = QScrollArea(section)
        wrap.setObjectName("charScrollTableWrap")
        wrap.setWidgetResizable(True)
        wrap.setFixedHeight(40 + len(scroll_set.stats) * 38)
        wrap.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        table: QFrame = QFrame()
        table.setObjectName("charScrollTable")
        grid = QGridLayout(table)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        # 머리글
        head_label: QLabel = QLabel("주문서", table)
        head_label.setObjectName("charScrollHead")
        head_label.setFont(CustomFont(9, bold=True))
        grid.addWidget(head_label, 0, 0)
        for col, tier in enumerate(scroll_set.tiers):
            tier_label: QLabel = QLabel(tier, table)
            tier_label.setObjectName("charScrollHead")
            tier_label.setFont(CustomFont(9, bold=True))
            tier_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(tier_label, 0, col + 2)

        # 본문
        for row, stat in enumerate(scroll_set.stats):
            stat_label: QLabel = QLabel(stat, table)
            stat_label.setObjectName("charScrollStat")
            stat_label.setFont(CustomFont(9, bold=True))
            grid.addWidget(stat_label, row + 1, 0)
            for col, tier in enumerate(scroll_set.tiers):
                # 공격력% 주문서는 40% 단계에서만 사용 가능
                disabled: bool = stat == "공격력%" and tier != "40%"
                if disabled:
                    dash: QLabel = QLabel("—", table)
                    dash.setObjectName("charMuted")
                    dash.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    grid.addWidget(dash, row + 1, col + 2)
                else:
                    cell: QLineEdit = QLineEdit("0", table)
                    cell.setObjectName("charMiniNum")
                    cell.setFont(CustomFont(9))
                    cell.setFixedWidth(30)
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setValidator(QDoubleValidator(0.0, 999.0, 0, cell))
                    grid.addWidget(cell, row + 1, col + 2)

        # 종류 텍스트와 입력칸 사이 간격
        grid.setColumnMinimumWidth(1, 16)
        # 잉여 가로 공간을 마지막 열 뒤로 몰아 입력칸을 종류 라벨 쪽에 붙인다
        grid.setColumnStretch(len(scroll_set.tiers) + 2, 1)

        wrap.setWidget(table)
        box.addWidget(wrap)
        return section

    def _build_option_section(self, title: str, options: tuple[str, ...]) -> QFrame:
        """잠재/추가능력 섹션 (3줄 고정)"""

        section, box = self._section(title)
        for _ in range(3):
            row = QHBoxLayout()
            row.setSpacing(10)
            combo: CharComboBox = CharComboBox(section, ["미설정", *options])
            # 입력칸은 고정 폭으로 두어 창 크기에 따라 늘어나지 않게 한다
            field: StepperField = StepperField(section, "0")
            field.setFixedWidth(100)
            row.addWidget(combo, 1)
            row.addWidget(field)
            box.addLayout(row)
        return section

    def _build_labeled_field(
        self, label: str, value: str, readonly: bool = False
    ) -> QWidget:
        """라벨 + 수치 묶음 (readonly 면 입력 대신 읽기 전용 표시)"""

        container: QFrame = QFrame(self)
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        unit: str = "%" if "%" in label else ""
        name_label: QLabel = QLabel(label, container)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        box.addWidget(name_label)

        # %스탯과 일반 스탯 모두 동일한 칸 폭으로 통일
        field: QWidget = (
            StaticValueField(container, value, unit=unit)
            if readonly
            else StepperField(container, value, unit=unit)
        )
        field.setFixedWidth(84)
        box.addWidget(field)
        return container

    # 장비 교체 (선택) 화면

    def open_picker(self) -> None:
        """장비 교체 화면 열기"""

        self._picker_open = True
        self._render_detail()

    def close_picker(self) -> None:
        """장비 교체 화면 닫고 상세로 복귀"""

        self._picker_open = False
        self._render_detail()

    def select_owned(self, index: int) -> None:
        """선택한 장비를 슬롯에 장착하고 상세로 복귀"""

        self._slots_data[self._active_index].equipped_index = index
        self._picker_open = False
        self._refresh_active_slot()
        self._render_detail()

    def unequip(self) -> None:
        """슬롯 장착 해제 후 빈 상태로 복귀"""

        self._slots_data[self._active_index].equipped_index = -1
        self._picker_open = False
        self._refresh_active_slot()
        self._render_detail()

    def add_owned(self) -> None:
        """현재 장비를 복제해 새 장비로 추가 (선택 화면 유지)"""

        slot: sample_data.EquipSlotData = self._slots_data[self._active_index]
        source = slot.equipped() if slot.equipped() is not None else slot.owned[0]
        new_item = deepcopy(source)
        new_item.name = "새 " + slot.type
        slot.owned.append(new_item)
        self._render_detail()

    def remove_owned(self, index: int) -> None:
        """보유 장비 삭제 (마지막 1개는 삭제 불가)"""

        slot: sample_data.EquipSlotData = self._slots_data[self._active_index]
        if len(slot.owned) <= 1:
            return
        slot.owned.pop(index)
        if slot.equipped_index >= len(slot.owned):
            slot.equipped_index = len(slot.owned) - 1
        elif 0 <= slot.equipped_index and index < slot.equipped_index:
            slot.equipped_index -= 1
        self._refresh_active_slot()
        self._render_detail()

    def _render_picker(self, slot: sample_data.EquipSlotData) -> None:
        """장비 교체 화면 구성 (보유 장비 카드 목록)"""

        self._detail_layout.addLayout(self._build_picker_head())

        has_grade: bool = slot.type in sample_data.GRADE_TYPES
        removable: bool = len(slot.owned) > 1
        list_box = QVBoxLayout()
        list_box.setContentsMargins(0, 4, 0, 0)
        list_box.setSpacing(10)
        for index, item in enumerate(slot.owned):
            card: _EquipPickCard = _EquipPickCard(
                self._detail_content,
                slot,
                item,
                index,
                self,
                has_grade,
                removable,
                index == slot.equipped_index,
            )
            list_box.addWidget(card)
        self._detail_layout.addLayout(list_box)
        self._detail_layout.addStretch(1)

    def _build_picker_head(self) -> QHBoxLayout:
        """장비 교체 화면 헤더 (뒤로 + 제목 + 새 장비/해제)"""

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 12)
        head.setSpacing(10)

        back_btn: QPushButton = QPushButton("❮", self)
        back_btn.setObjectName("charIconBtn")
        back_btn.setFont(CustomFont(11))
        back_btn.setFixedSize(34, 34)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.close_picker)
        head.addWidget(back_btn)

        title_label: QLabel = QLabel("장비 선택", self)
        title_label.setObjectName("charDetailName")
        title_label.setFont(CustomFont(15, bold=True))
        head.addWidget(title_label)

        head.addStretch(1)

        add_btn: StyledButton = StyledButton(
            self, "+ 새 장비", kind="normal", point_size=9
        )
        add_btn.clicked.connect(self.add_owned)
        head.addWidget(add_btn)

        unequip_btn: StyledButton = StyledButton(
            self, "해제", kind="normal", point_size=9
        )
        unequip_btn.clicked.connect(self.unequip)
        head.addWidget(unequip_btn)
        return head

    def _render_empty(self, slot: sample_data.EquipSlotData) -> None:
        """장착 장비가 없는 빈 상태 화면"""

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 12)
        head.setSpacing(12)

        icon: QLabel = QLabel(self)
        icon.setFixedSize(46, 46)
        icon.setStyleSheet(_ICON_STYLE_MUTED)
        head.addWidget(icon)

        name_box = QVBoxLayout()
        name_box.setSpacing(4)
        title_label: QLabel = QLabel(slot.type, self)
        title_label.setObjectName("charMuted")
        title_label.setFont(CustomFont(15, bold=True))
        sub_label: QLabel = QLabel("장착된 장비가 없습니다", self)
        sub_label.setObjectName("charSub")
        sub_label.setFont(CustomFont(9))
        name_box.addWidget(title_label)
        name_box.addWidget(sub_label)
        head.addLayout(name_box)

        head.addStretch(1)
        select_btn: StyledButton = StyledButton(
            self, "장비 선택", kind="normal", point_size=9
        )
        select_btn.clicked.connect(self.open_picker)
        head.addWidget(select_btn)
        self._detail_layout.addLayout(head)

        hint: QLabel = QLabel(
            "장비 교체로 보유 장비를 선택하거나 새 장비를 추가하세요.", self
        )
        hint.setObjectName("charEquipPickEmpty")
        hint.setFont(CustomFont(9))
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_layout.addWidget(hint)
        self._detail_layout.addStretch(1)
