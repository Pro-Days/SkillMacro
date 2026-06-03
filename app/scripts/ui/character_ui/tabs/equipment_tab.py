"""장비 탭 (좌: 장비창 9슬롯 / 우: 선택 장비 상세)

콘텐츠 규칙은 계획 파일을 따른다:
- 재련 = 단계가 아닌 부위별 허용 스탯 입력
- 반지/귀걸이 = 자유 기본 스탯 라인
- 잠재/추가능력 = 투구·갑옷·허리띠·신발만
- 등급(기본/찬란한) = 무기·방어구만
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui import sample_data
from app.scripts.ui.character_ui.widgets import CharComboBox, SegButton, StepperField

_ICON_STYLE: str = (
    "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #cbb389, stop:1 #8a6b3f);"
    "border: 1px solid #c8c4be; border-radius: 6px;"
)

# 장비창 고정 폭과 세로 스택 전환 임계 폭
_EQUIP_WINDOW_WIDTH: int = 300
_STACK_THRESHOLD: int = 640


class _EquipSlot(QFrame):
    """장비창 슬롯 1칸"""

    def __init__(self, parent: QWidget, data: sample_data.EquipSlotData, index: int, tab: "EquipmentTab") -> None:
        super().__init__(parent)

        self.setObjectName("charEquipSlot")
        self.setProperty("active", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._index: int = index
        self._tab: "EquipmentTab" = tab

        box = QVBoxLayout(self)
        box.setContentsMargins(8, 10, 8, 10)
        box.setSpacing(3)

        icon: QLabel = QLabel(self)
        icon.setFixedSize(38, 38)
        icon.setStyleSheet(_ICON_STYLE)
        box.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        type_label: QLabel = QLabel(data.type, self)
        type_label.setObjectName("charEquipType")
        type_label.setFont(CustomFont(9, bold=True))
        type_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(type_label)

        level_label: QLabel = QLabel(f"Lv {data.level}", self)
        level_label.setObjectName("charEquipMeta")
        level_label.setFont(CustomFont(8))
        level_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(level_label)

    def set_active(self, active: bool) -> None:
        """선택 강조 갱신"""

        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """슬롯 클릭 시 상세 전환"""

        self._tab.select_slot(self._index)
        super().mousePressEvent(event)


class EquipmentTab(QFrame):
    """장비 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._slots_data: list[sample_data.EquipSlotData] = sample_data.default_equip_slots()
        self._active_index: int = 0

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
        """폭이 좁으면 장비창과 상세를 세로 1열로 전환"""

        super().resizeEvent(event)
        self._apply_responsive(self.width())

    def _apply_responsive(self, width: int) -> None:
        """폭 임계값 기준으로 가로/세로 배치 전환"""

        # 장비창(320) + 상세를 나란히 두기 어려운 폭이면 세로 스택
        should_stack: bool = width < _STACK_THRESHOLD
        if should_stack == self._stacked:
            return
        self._stacked = should_stack

        # 장비창은 두 모드 모두 고정 폭을 유지하고, 세로 스택 시 중앙 정렬
        if should_stack:
            self._root_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._root_layout.setAlignment(self._equip_window, Qt.AlignmentFlag.AlignHCenter)
        else:
            self._root_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._root_layout.setAlignment(self._equip_window, Qt.AlignmentFlag.AlignTop)

    # 좌측 장비창

    def _build_equip_window(self) -> QFrame:
        """좌측 장비창 (2열 슬롯)"""

        window: QFrame = QFrame(self)
        window.setObjectName("charEquipWindow")
        window.setFixedWidth(_EQUIP_WINDOW_WIDTH)

        grid = QHBoxLayout(window)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(10)

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
                slot: _EquipSlot = _EquipSlot(self, self._slots_data[index], index, self)
                self._slot_widgets[index] = slot
                column_layout.addWidget(slot)
            column_layout.addStretch(1)
        self._highlight_active()

    def _highlight_active(self) -> None:
        """현재 선택 슬롯 강조"""

        for index, slot in self._slot_widgets.items():
            slot.set_active(index == self._active_index)

    def select_slot(self, index: int) -> None:
        """슬롯 선택 시 상세 갱신"""

        self._active_index = index
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
        """선택 장비 상세 재구성"""

        self._clear_detail()
        data: sample_data.EquipSlotData = self._slots_data[self._active_index]
        has_grade: bool = data.type in sample_data.GRADE_TYPES
        has_potential: bool = data.type in sample_data.POTENTIAL_TYPES

        self._detail_layout.addLayout(self._build_detail_head(data, has_grade))

        if has_grade:
            self._detail_layout.addWidget(self._build_grade_section(data))

        self._detail_layout.addWidget(self._build_base_section(data))

        if data.reforge:
            self._detail_layout.addWidget(self._build_reforge_section(data))

        if data.scroll:
            self._detail_layout.addWidget(self._build_scroll_section(data))

        if has_potential:
            self._detail_layout.addWidget(
                self._build_option_section("잠재능력", sample_data.POTENTIAL_OPTS)
            )
            self._detail_layout.addWidget(
                self._build_option_section("추가능력", sample_data.ADDITIONAL_OPTS)
            )

        self._detail_layout.addStretch(1)

    def _build_detail_head(self, data: sample_data.EquipSlotData, has_grade: bool) -> QHBoxLayout:
        """상세 헤더 (아이콘 + 이름 + 교체 버튼)"""

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 12)
        head.setSpacing(12)

        icon: QLabel = QLabel(self)
        icon.setFixedSize(46, 46)
        icon.setStyleSheet(_ICON_STYLE)
        head.addWidget(icon)

        name_box = QVBoxLayout()
        name_box.setSpacing(2)
        display_name: str = ("찬란한 " if has_grade and data.grade == "찬란한" else "") + data.name
        name_label: QLabel = QLabel(display_name, self)
        name_label.setObjectName("charDetailName")
        name_label.setFont(CustomFont(15, bold=True))
        meta_label: QLabel = QLabel(f"{data.type} · 레벨 {data.level}", self)
        meta_label.setObjectName("charSub")
        meta_label.setFont(CustomFont(9))
        name_box.addWidget(name_label)
        name_box.addWidget(meta_label)
        head.addLayout(name_box)

        head.addStretch(1)
        change_btn: StyledButton = StyledButton(self, "장비 교체", kind="normal", point_size=9)
        head.addWidget(change_btn)
        return head

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

    def _build_grade_section(self, data: sample_data.EquipSlotData) -> QFrame:
        """등급(기본/찬란한) 선택 섹션"""

        section, box = self._section("아이템")

        label: QLabel = QLabel("등급", section)
        label.setObjectName("charFieldLabel")
        label.setFont(CustomFont(9, bold=True))
        box.addWidget(label)

        seg = QHBoxLayout()
        seg.setSpacing(8)
        self._grade_buttons: list[SegButton] = []
        for index, grade in enumerate(("기본", "찬란한")):
            button: SegButton = SegButton(section, grade, index, self._pick_grade)
            button.setChecked(data.grade == grade)
            self._grade_buttons.append(button)
            seg.addWidget(button)
        seg.addStretch(1)
        box.addLayout(seg)
        return section

    def _pick_grade(self, index: int) -> None:
        """등급 선택 시 표시 이름 갱신을 위해 상세 재구성"""

        self._slots_data[self._active_index].grade = "기본" if index == 0 else "찬란한"
        self._render_detail()

    def _build_base_section(self, data: sample_data.EquipSlotData) -> QFrame:
        """기본 스탯 섹션 (방어구/무기 자동 표시 vs 반지/귀걸이 자유 입력)"""

        section, box = self._section("기본 스탯")

        # 반지/귀걸이: 자유 스탯 라인
        if not data.base:
            self._free_rows = QVBoxLayout()
            self._free_rows.setSpacing(8)
            for stat, value in data.free_base:
                self._free_rows.addLayout(self._build_free_stat_row(stat, value))
            box.addLayout(self._free_rows)

            add_btn: StyledButton = StyledButton(section, "+ 스탯 추가", kind="normal", point_size=9)
            add_btn.clicked.connect(self._add_free_stat)
            box.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)
            return section

        # 방어구/무기: 고정 기본 스탯 표시
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for i, (label_text, value) in enumerate(data.base):
            grid.addWidget(self._build_labeled_field(label_text, str(value)), i // 3, i % 3)
        box.addLayout(grid)
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

    def _build_reforge_section(self, data: sample_data.EquipSlotData) -> QFrame:
        """재련 섹션 (부위/목걸이 종류별 허용 스탯 입력)"""

        section, box = self._section("재련")

        key: str = data.necklace_type if data.necklace_type else data.type
        stats: tuple[str, ...] = sample_data.REFORGE_STATS.get(key, ())

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for i, stat in enumerate(stats):
            grid.addWidget(self._build_labeled_field(stat, "0"), i // 3, i % 3)
        box.addLayout(grid)
        return section

    def _build_scroll_section(self, data: sample_data.EquipSlotData) -> QFrame:
        """주문서 섹션 (행=종류, 열=% 단계, 칸=성공 횟수)"""

        section, box = self._section("주문서")

        scroll_set: sample_data.ScrollSet = sample_data.SCROLL_SETS[data.scroll]

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
        head_label: QLabel = QLabel("주문서 종류", table)
        head_label.setObjectName("charScrollHead")
        head_label.setFont(CustomFont(9, bold=True))
        grid.addWidget(head_label, 0, 0)
        for col, tier in enumerate(scroll_set.tiers):
            tier_label: QLabel = QLabel(tier, table)
            tier_label.setObjectName("charScrollHead")
            tier_label.setFont(CustomFont(9, bold=True))
            tier_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(tier_label, 0, col + 1)

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
                    grid.addWidget(dash, row + 1, col + 1)
                else:
                    cell: QLineEdit = QLineEdit("0", table)
                    cell.setObjectName("charMiniNum")
                    cell.setFont(CustomFont(9))
                    cell.setFixedWidth(48)
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setValidator(QDoubleValidator(0.0, 999.0, 0, cell))
                    grid.addWidget(cell, row + 1, col + 1)

        wrap.setWidget(table)
        box.addWidget(wrap)
        return section

    def _build_option_section(self, title: str, options: tuple[str, ...]) -> QFrame:
        """잠재/추가능력 섹션 (3줄 고정)"""

        section, box = self._section(title)
        for _ in range(3):
            row = QHBoxLayout()
            row.setSpacing(10)
            marker: QLabel = QLabel("●", section)
            marker.setObjectName("charOptIndex")
            marker.setFont(CustomFont(9))
            marker.setFixedWidth(24)
            combo: CharComboBox = CharComboBox(section, ["미설정", *options])
            field: StepperField = StepperField(section, "0", max_width=140)
            row.addWidget(marker)
            row.addWidget(combo, 1)
            row.addWidget(field)
            box.addLayout(row)
        return section

    def _build_labeled_field(self, label: str, value: str) -> QWidget:
        """라벨 + 스텝퍼 묶음"""

        container: QFrame = QFrame(self)
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        unit: str = "%" if "%" in label else ""
        name_label: QLabel = QLabel(label, container)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        box.addWidget(name_label)
        box.addWidget(StepperField(container, value, unit=unit))
        return container
