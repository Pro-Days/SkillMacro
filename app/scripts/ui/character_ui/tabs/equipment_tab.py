"""장비 탭 (좌: 장비창 9슬롯 / 우: 선택 장비 상세 · 장비 교체 화면)

콘텐츠 규칙은 계획 파일을 따른다:
- 슬롯마다 보유 장비 여러 개를 두고, 장비 교체로 선택해 장착한다
- 재련 = 단계가 아닌 부위별 허용 스탯 입력
- 반지/귀걸이 = 자유 기본 스탯 라인
- 잠재/추가능력 = 투구·갑옷·허리띠·신발만
- 등급(기본/찬란한) = 무기·방어구만
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import STAT_SPECS, StatKey
from app.scripts.character_data import (
    ADDITIONAL_OPTION_SPECS,
    ARMOR_SLOT_STAT_KEYS,
    EQUIPMENT_ITEM_SPECS,
    EQUIPMENT_REFORGE_STAT_KEYS,
    EQUIPMENT_SCROLL_EFFECTS,
    EQUIPMENT_SCROLL_LIMITS,
    FREE_BASE_STAT_EQUIPMENT_SLOTS,
    NECKLACE_REFORGE_STAT_KEYS,
    POTENTIAL_EQUIPMENT_SLOTS,
    POTENTIAL_OPTION_SPECS,
    EquipmentItemSpec,
    OptionSpec,
    ValueRange,
)
from app.scripts.character_engine import (
    create_equipment,
    equip_equipment,
    equipment_item_spec,
    list_equippable_equipment,
    remove_equipment,
    rename_equipment,
    unequip_equipment,
)
from app.scripts.character_models import (
    EQUIPMENT_OPTION_SLOT_COUNT,
    EQUIPMENT_SLOT_KIND,
    MAX_REFORGE_STEP,
    AdditionalLine,
    AdditionalOption,
    CharacterProfile,
    EquipmentFreeStatLine,
    EquipmentGrade,
    EquipmentKind,
    EquipmentScrollLine,
    EquipmentSlot,
    OwnedEquipment,
    PotentialLine,
    PotentialOption,
    ScrollTier,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.change_handler import CharacterChangeHandler
from app.scripts.ui.character_ui.constants import (
    EQUIPMENT_COL_LEFT,
    EQUIPMENT_COL_RIGHT,
    EQUIPMENT_SLOT_LABELS,
    STAT_CHOICE_LABELS,
    STAT_LABEL_TO_KEY,
)
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.widgets import (
    CharComboBox,
    ChoiceListPanels,
    FlowLayout,
    ResponsiveActionCard,
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

_EQUIP_WINDOW_WIDTH: int = 232
_STACK_THRESHOLD: int = 550

_SLOT_ORDER: tuple[EquipmentSlot, ...] = (*EQUIPMENT_COL_LEFT, *EQUIPMENT_COL_RIGHT)
_EQUIP_COL_LEFT: tuple[int, ...] = tuple(range(len(EQUIPMENT_COL_LEFT)))
_EQUIP_COL_RIGHT: tuple[int, ...] = tuple(
    range(len(EQUIPMENT_COL_LEFT), len(_SLOT_ORDER))
)
_NECKLACE_TYPES: tuple[str, ...] = tuple(NECKLACE_REFORGE_STAT_KEYS.keys())
_ARMOR_SLOT_NAME_SUFFIX: dict[EquipmentSlot, str] = {
    EquipmentSlot.HELMET: "투구",
    EquipmentSlot.ARMOR: "갑옷",
    EquipmentSlot.BELT: "대",
    EquipmentSlot.SHOES: "신",
}
_REFORGE_EQUIPMENT_SLOTS: tuple[EquipmentSlot, ...] = tuple(
    slot for slot, stat_keys in EQUIPMENT_REFORGE_STAT_KEYS.items() if stat_keys
) + (EquipmentSlot.NECKLACE,)
_SCROLL_TIER_LABELS: dict[ScrollTier, str] = {
    tier: f"{tier.value}%" for tier in ScrollTier
}


def _reforge_stat_keys(
    slot: EquipmentSlot, necklace_type: str | None
) -> tuple[StatKey, ...]:
    """부위/목걸이 종류별 재련 허용 스탯 키 조회"""

    if slot == EquipmentSlot.NECKLACE:
        if necklace_type is None:
            return ()

        return NECKLACE_REFORGE_STAT_KEYS[necklace_type]

    return EQUIPMENT_REFORGE_STAT_KEYS[slot]


def _option_label(spec: OptionSpec) -> str:
    """옵션 표시 라벨 구성 (스탯 이름 + 값 범위)"""

    value_range = spec.value_range
    return (
        f"{STAT_SPECS[spec.stat_key]} "
        f"({value_range.minimum:g}~{value_range.maximum:g})"
    )


_POTENTIAL_OPTION_TO_LABEL: dict[PotentialOption, str] = {
    option: _option_label(spec) for option, spec in POTENTIAL_OPTION_SPECS.items()
}
_POTENTIAL_LABEL_TO_OPTION: dict[str, PotentialOption] = {
    label: option for option, label in _POTENTIAL_OPTION_TO_LABEL.items()
}
_POTENTIAL_OPTIONS: tuple[str, ...] = tuple(_POTENTIAL_OPTION_TO_LABEL.values())

_ADDITIONAL_OPTION_TO_LABEL: dict[AdditionalOption, str] = {
    option: _option_label(spec) for option, spec in ADDITIONAL_OPTION_SPECS.items()
}
_ADDITIONAL_LABEL_TO_OPTION: dict[str, AdditionalOption] = {
    label: option for option, label in _ADDITIONAL_OPTION_TO_LABEL.items()
}
_ADDITIONAL_OPTIONS: tuple[str, ...] = tuple(_ADDITIONAL_OPTION_TO_LABEL.values())


class _OptionSectionKind(Enum):
    """장비 옵션 섹션 종류"""

    POTENTIAL = auto()
    ADDITIONAL = auto()


@dataclass(frozen=True, slots=True)
class _EquipmentOptionSection:
    """장비 옵션 섹션 표시 데이터"""

    title: str
    kind: _OptionSectionKind
    labels: tuple[str, ...]


_POTENTIAL_SECTION: _EquipmentOptionSection = _EquipmentOptionSection(
    title="잠재능력",
    kind=_OptionSectionKind.POTENTIAL,
    labels=_POTENTIAL_OPTIONS,
)
_ADDITIONAL_SECTION: _EquipmentOptionSection = _EquipmentOptionSection(
    title="추가능력",
    kind=_OptionSectionKind.ADDITIONAL,
    labels=_ADDITIONAL_OPTIONS,
)


@dataclass(frozen=True, slots=True)
class _ScrollSet:
    """주문서 표 표시 데이터"""

    stat_keys: tuple[StatKey, ...]
    tiers: tuple[ScrollTier, ...]


def _build_scroll_sets() -> dict[EquipmentSlot, _ScrollSet]:
    """부위별 주문서 표 구성 (주문서 효과 데이터 파생)"""

    sets: dict[EquipmentSlot, _ScrollSet] = {}
    for slot, stat_effects in EQUIPMENT_SCROLL_EFFECTS.items():
        if not stat_effects:
            continue

        tiers: list[ScrollTier] = []
        for tier_map in stat_effects.values():
            for tier in tier_map:
                if tier not in tiers:
                    tiers.append(tier)
        tiers.sort(key=lambda tier: int(tier.value))

        sets[slot] = _ScrollSet(
            stat_keys=tuple(stat_effects.keys()),
            tiers=tuple(tiers),
        )
    return sets


_SCROLL_SETS: dict[EquipmentSlot, _ScrollSet] = _build_scroll_sets()


def _equipment_levels(slot: EquipmentSlot) -> tuple[int, ...]:
    """슬롯에 존재하는 실제 장비 레벨 목록"""

    # 장비 카탈로그 기준 레벨 중복 제거
    levels: set[int] = {
        item_spec.level for item_spec in EQUIPMENT_ITEM_SPECS if slot in item_spec.slots
    }

    # 콤보박스 표시 순서 고정
    return tuple(sorted(levels))


def _equipment_tiers(slot: EquipmentSlot, level: int) -> tuple[int, ...]:
    """슬롯과 레벨에 존재하는 실제 장비 티어 목록"""

    # 장비 카탈로그 기준 티어 중복 제거
    tiers: set[int] = {
        item_spec.tier
        for item_spec in EQUIPMENT_ITEM_SPECS
        if slot in item_spec.slots and item_spec.level == level
    }

    # 콤보박스 표시 순서 고정
    return tuple(sorted(tiers))


def _equipment_scroll_limit(
    slot: EquipmentSlot,
    equipment: OwnedEquipment,
) -> int | None:
    """장비 레벨 기준 주문서 최대 성공 횟수 조회"""

    # 반지처럼 총합 제한이 없는 슬롯은 입력칸 개별 제한만 적용
    limit_map: dict[int, int] | None = EQUIPMENT_SCROLL_LIMITS[slot]
    if limit_map is None:
        return None

    # 레벨별 제한이 있는 슬롯은 실제 장비 스펙 레벨로 한도 조회
    item_spec: EquipmentItemSpec | None = equipment_item_spec(equipment)
    if item_spec is None:
        raise ValueError("scroll-limited equipment requires item spec")

    return limit_map[item_spec.level]


def _has_grade(item_spec: EquipmentItemSpec | None) -> bool:
    """장비 스펙 기준 등급 선택 가능 여부"""

    # 반지·귀걸이처럼 카탈로그 스펙이 없는 장비 제외
    if item_spec is None:
        return False

    # 기본/찬란한 등급 스탯을 가진 장비만 등급 입력 표시
    return EquipmentGrade.BASIC in item_spec.grade_stats


def _make_icon(parent: QWidget, size: int, muted: bool = False) -> QLabel:
    """장비 아이콘 라벨 생성"""

    icon: QLabel = QLabel(parent)
    icon.setFixedSize(size, size)
    icon.setStyleSheet(_ICON_STYLE_MUTED if muted else _ICON_STYLE)
    return icon


def _field_caption(parent: QWidget, text: str) -> QLabel:
    """입력 필드 캡션 라벨 생성"""

    caption: QLabel = QLabel(text, parent)
    caption.setObjectName("charFieldLabel")
    caption.setFont(CustomFont(9, bold=True))
    return caption


def _equipment_name(equipment: OwnedEquipment, slot: EquipmentSlot) -> str:
    """장비 표시 이름 구성"""

    # 카탈로그 장비 이름과 방어구 부위 접미사 결합
    item_spec: EquipmentItemSpec | None = equipment_item_spec(equipment)
    if item_spec is not None:
        return item_spec.name + _ARMOR_SLOT_NAME_SUFFIX.get(slot, "")

    # 반지·귀걸이 사용자 지정 이름 표시
    return equipment.name


def _equipment_base_rows(
    equipment: OwnedEquipment, slot: EquipmentSlot
) -> list[tuple[str, float]]:
    """장비 스펙 기반 기본 스탯 표시 행 구성"""

    # 반지·귀걸이 자유 입력 장비 제외
    item_spec: EquipmentItemSpec | None = equipment_item_spec(equipment)
    if item_spec is None:
        return []

    # 장비 등급별 고정 기본 스탯 조회
    grade: EquipmentGrade | None = equipment.grade
    values: dict[StatKey, float] = dict(item_spec.grade_stats[grade])
    if slot not in ARMOR_SLOT_STAT_KEYS:
        return [(STAT_SPECS[stat_key], value) for stat_key, value in values.items()]

    # 방어구 부위별 주스탯 추가
    if grade is None:
        raise ValueError("armor equipment grade is required")

    values[ARMOR_SLOT_STAT_KEYS[slot]] = item_spec.armor_stat_values[grade]
    return [(STAT_SPECS[stat_key], value) for stat_key, value in values.items()]


def _equipment_display_name(
    equipment: OwnedEquipment, slot: EquipmentSlot, has_grade: bool
) -> str:
    """장비 이름 표시 문자열 구성"""

    # 찬란한 장비 접두어 구성
    if has_grade and equipment.grade == EquipmentGrade.RADIANT:
        return f"찬란한 {_equipment_name(equipment, slot)}"

    return _equipment_name(equipment, slot)


def _equipment_pick_info_rows(
    equipment: OwnedEquipment,
) -> list[tuple[str, list[str]]]:
    """장비 선택 카드 요약 행 구성"""

    info_rows: list[tuple[str, list[str]]] = []

    # 주문서 종류와 확률별 성공 횟수 요약
    scroll_totals: dict[tuple[StatKey, ScrollTier], int] = {}
    for scroll in equipment.scrolls:
        scroll_key: tuple[StatKey, ScrollTier] = (scroll.stat_key, scroll.tier)
        scroll_totals[scroll_key] = scroll_totals.get(scroll_key, 0) + scroll.count

    scroll_tokens: list[str] = []
    for scroll_key, total_count in scroll_totals.items():
        if total_count <= 0:
            continue

        stat_key, tier = scroll_key
        scroll_tokens.append(
            f"{STAT_SPECS[stat_key]} {_SCROLL_TIER_LABELS[tier]} · {total_count:g}회"
        )

    if scroll_tokens:
        info_rows.append(("주문서", scroll_tokens))

    # 잠재능력 입력 요약
    potential_tokens: list[str] = [
        f"{STAT_SPECS[POTENTIAL_OPTION_SPECS[line.option].stat_key]} {line.value:g}"
        for line in equipment.potentials
        if line is not None
    ]
    if potential_tokens:
        info_rows.append(("잠재능력", potential_tokens))

    # 추가능력 입력 요약
    additional_tokens: list[str] = [
        f"{STAT_SPECS[ADDITIONAL_OPTION_SPECS[line.option].stat_key]} {line.value:g}"
        for line in equipment.additionals
        if line is not None
    ]
    if additional_tokens:
        info_rows.append(("추가능력", additional_tokens))

    return info_rows


@dataclass(slots=True)
class _EquipSlotData:
    """장비 슬롯 UI 데이터"""

    slot: EquipmentSlot
    owned: list[OwnedEquipment]
    equipped_index: int
    unavailable_names: set[str]

    def equipped(self) -> OwnedEquipment | None:
        """현재 장착 장비"""

        if self.equipped_index == -1:
            return None

        return self.owned[self.equipped_index]


@dataclass(slots=True)
class _ItemSection:
    """아이템 선택 컨트롤 참조"""

    widget: QFrame
    level: CharComboBox | None = None
    tier: CharComboBox | None = None
    grade: QPushButton | None = None
    necklace_type: CharComboBox | None = None

    def update_tiers(self, slot: EquipmentSlot, item: OwnedEquipment) -> None:
        """레벨에 맞는 티어 선택지 갱신"""

        if self.tier is None:
            raise ValueError("tier field is not available")

        # 티어 목록 교체 중 신호 차단
        with QSignalBlocker(self.tier):
            self.tier.clear()
            self.tier.addItems(
                [str(tier) for tier in _equipment_tiers(slot, item.level)]
            )
            self.tier.setCurrentText(str(item.tier))


@dataclass(slots=True)
class _BaseSection:
    """기본 스탯 섹션 참조"""

    widget: QFrame
    free_rows: QVBoxLayout | None = None
    static_flow: FlowLayout | None = None
    static_fields: dict[str, tuple[QWidget, StaticValueField]] | None = None
    make_static_field: (
        Callable[[str, float], tuple[QWidget, StaticValueField]] | None
    ) = None

    def update_values(self, slot: EquipmentSlot, item: OwnedEquipment) -> None:
        """자동 기본 스탯 표시값 갱신"""

        if self.static_fields is None:
            return

        rows: list[tuple[str, float]] = _equipment_base_rows(item, slot)
        if [label for label, _value in rows] != list(self.static_fields):
            self._rebuild_static_fields(rows)
            return

        values: dict[str, float] = dict(rows)
        for label, (_container, field) in self.static_fields.items():
            field.set_number(values[label])

    def _rebuild_static_fields(self, rows: list[tuple[str, float]]) -> None:
        """기본 스탯 항목 구성이 바뀐 경우 내부 필드 동기화"""

        if (
            self.static_flow is None
            or self.static_fields is None
            or self.make_static_field is None
        ):
            raise ValueError("static base stat fields are not available")

        for container, _field in self.static_fields.values():
            self.static_flow.removeWidget(container)
            container.deleteLater()
        self.static_fields.clear()

        for label, value in rows:
            container, field = self.make_static_field(label, value)
            self.static_fields[label] = (container, field)
            self.static_flow.addWidget(container)
        self.widget.updateGeometry()


@dataclass(slots=True)
class _ScrollRow:
    """적용 주문서 행 참조"""

    line_id: str
    widget: QFrame
    title_label: QLabel
    effect_label: QLabel
    count_field: StepperField


@dataclass(slots=True)
class _ScrollSection:
    """주문서 섹션 참조"""

    widget: QFrame
    selector_panel: QFrame
    list_panel: QFrame
    stat_buttons: dict[StatKey, QPushButton]
    tier_content: QWidget
    tier_layout: QVBoxLayout
    tier_buttons: dict[ScrollTier, QPushButton]
    add_button: StyledButton
    list_content: QWidget
    list_layout: QVBoxLayout
    rows: dict[str, _ScrollRow]
    row_ids: tuple[str, ...]

    def update_selector(
        self,
        selected_stat_key: StatKey | None,
        selected_tier: ScrollTier | None,
        stat_enabled: dict[StatKey, bool],
        tier_effects: dict[ScrollTier, dict[StatKey, float]],
        tier_enabled: dict[ScrollTier, bool],
        add_button_text: str,
        add_enabled: bool,
        tier_button_text: Callable[[ScrollTier, dict[StatKey, float]], str],
        make_tier_button: Callable[
            [ScrollTier, dict[StatKey, float]],
            QPushButton,
        ],
    ) -> None:
        """주문서 선택 상태와 확률 버튼 목록 동기화"""

        for stat_key, button in self.stat_buttons.items():
            button.setEnabled(stat_enabled[stat_key])
            button.setChecked(stat_key is selected_stat_key)

        tier_keys: tuple[ScrollTier, ...] = tuple(tier_effects)
        if tuple(self.tier_buttons) != tier_keys:
            for button in self.tier_buttons.values():
                self.tier_layout.removeWidget(button)
                button.deleteLater()
            self.tier_buttons.clear()

            for tier, effects in tier_effects.items():
                button = make_tier_button(tier, effects)
                self.tier_buttons[tier] = button
                self.tier_layout.insertWidget(
                    max(0, self.tier_layout.count() - 1),
                    button,
                )
            self.tier_content.updateGeometry()

        for tier, button in self.tier_buttons.items():
            button.setText(tier_button_text(tier, tier_effects[tier]))
            button.setEnabled(tier_enabled[tier])
            button.setChecked(tier is selected_tier)

        self.add_button.setText(add_button_text)
        self.add_button.setEnabled(add_enabled)

    def update_rows(
        self,
        entries: list[tuple[EquipmentScrollLine, dict[StatKey, float]]],
        selected_line_id: str | None,
        row_title: Callable[[EquipmentScrollLine], str],
        effect_text: Callable[[dict[StatKey, float]], str],
        make_row: Callable[
            [EquipmentScrollLine, dict[StatKey, float]],
            _ScrollRow,
        ],
    ) -> None:
        """적용 주문서 행 구성과 횟수 입력값 동기화"""

        row_ids: tuple[str, ...] = tuple(line.id for line, _effects in entries)
        if row_ids != self.row_ids:
            for row in self.rows.values():
                self.list_layout.removeWidget(row.widget)
                row.widget.deleteLater()
            self.rows.clear()

            for line, effects in entries:
                row = make_row(line, effects)
                self.rows[line.id] = row
                self.list_layout.insertWidget(
                    max(0, self.list_layout.count() - 1),
                    row.widget,
                )
            self.row_ids = row_ids
            self.list_content.updateGeometry()

        for line, effects in entries:
            row = self.rows[line.id]
            selected: bool = line.id == selected_line_id
            row.widget.setProperty("selected", selected)
            row.widget.style().unpolish(row.widget)
            row.widget.style().polish(row.widget)
            row.title_label.setText(row_title(line))
            row.effect_label.setText(effect_text(effects))
            row.count_field.set_number(float(line.count))


@dataclass(slots=True)
class _ReforgeSection:
    """재련 섹션과 종류별 스탯 입력칸"""

    widget: QFrame
    flow: FlowLayout
    stat_fields: dict[StatKey, QWidget]
    make_stat_field: Callable[[StatKey, float], QWidget]

    def update_stat_fields(self, slot: EquipmentSlot, item: OwnedEquipment) -> None:
        """장비 종류에 맞는 재련 스탯 입력칸 동기화"""

        for container in self.stat_fields.values():
            self.flow.removeWidget(container)
            container.deleteLater()
        self.stat_fields.clear()

        for stat_key in _reforge_stat_keys(slot, item.item_name):
            container: QWidget = self.make_stat_field(
                stat_key,
                item.reforge_stats.get(stat_key, 0.0),
            )
            self.stat_fields[stat_key] = container
            self.flow.addWidget(container)
        self.widget.updateGeometry()


@dataclass(slots=True)
class _EquipmentDetailView:
    """현재 장착 장비 상세 페이지와 기능별 위젯 참조"""

    item: OwnedEquipment
    slot: EquipmentSlot
    page: QFrame
    display_name_label: QLabel
    item_section: _ItemSection | None
    base_section: _BaseSection | None
    reforge_section: _ReforgeSection | None
    scroll_section: _ScrollSection | None

    def update_display_name(self) -> None:
        """장비 종류 표시 갱신"""

        has_grade: bool = _has_grade(equipment_item_spec(self.item))
        self.display_name_label.setText(
            _equipment_display_name(self.item, self.slot, has_grade)
        )


class _DetailStack(QWidget):
    """현재 장비 상세 페이지만 높이에 반영하는 고정 페이지 스택"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._pages: list[QWidget] = []

    def addWidget(self, page: QWidget) -> None:
        """페이지 추가"""

        self._pages.append(page)
        self._layout.addWidget(page)
        page.setVisible(len(self._pages) == 1)

    def removeWidget(self, page: QWidget) -> None:
        """페이지 제거"""

        self._layout.removeWidget(page)
        self._pages.remove(page)
        page.setVisible(False)

    def setCurrentWidget(self, current: QWidget) -> None:
        """현재 페이지만 표시"""

        if current not in self._pages:
            raise ValueError("detail page is not attached")

        for page in self._pages:
            page.setVisible(page is current)
        self.updateGeometry()


class _EquipSlot(QFrame):
    """장비창 슬롯 1칸 (장착 장비 또는 빈 상태 표시)"""

    def __init__(
        self,
        parent: QWidget,
        slot: _EquipSlotData,
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

        self._icon: QLabel = _make_icon(self, 34)
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

    def update_from_slot(self, slot: _EquipSlotData) -> None:
        """슬롯 상태(장착 장비/빈 상태)에 맞춰 표시 갱신"""

        item = slot.equipped()
        empty: bool = item is None
        label: str = EQUIPMENT_SLOT_LABELS[slot.slot]
        self._icon.setStyleSheet(_ICON_STYLE_MUTED if empty else _ICON_STYLE)
        if empty:
            self._type_label.setText(label)
            self._meta_label.setText("비어 있음")
        else:
            # 찬란한 장비는 좌측 타일 이름에도 접두어를 붙인다
            has_grade: bool = _has_grade(equipment_item_spec(item))
            self._type_label.setText(
                _equipment_display_name(item, slot.slot, has_grade)
            )
            self._meta_label.setText(label)
        self.setProperty("empty", empty)
        self.style().unpolish(self)
        self.style().polish(self)
        self.style().unpolish(self._type_label)
        self.style().polish(self._type_label)
        self.style().unpolish(self._meta_label)
        self.style().polish(self._meta_label)

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
        tab: "EquipmentTab",
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charEquipPick")
        self._index: int = -1
        self._selectable: bool = False
        self._tab: "EquipmentTab" = tab

        card = QVBoxLayout(self)
        card.setContentsMargins(14, 14, 14, 14)
        card.setSpacing(7)

        head = QHBoxLayout()
        head.setSpacing(14)

        icon: QLabel = _make_icon(self, 44)
        head.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)

        name_box = QVBoxLayout()
        name_box.setSpacing(3)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        # 저장 장비 이름 표시
        self._name_label: QLabel = QLabel(self)
        self._name_label.setObjectName("charDetailName")
        self._name_label.setFont(CustomFont(13, bold=True))
        name_row.addWidget(self._name_label)

        self._reforge_label: QLabel = QLabel(self)
        self._reforge_label.setObjectName("charPickReforge")
        self._reforge_label.setFont(CustomFont(10, bold=True))
        name_row.addWidget(self._reforge_label)
        name_row.addStretch(1)
        name_box.addLayout(name_row)

        # 현재 스펙 기준 인게임 이름 표시
        self._display_name_label: QLabel = QLabel(self)
        self._display_name_label.setObjectName("charSub")
        self._display_name_label.setFont(CustomFont(9))
        name_box.addWidget(self._display_name_label)
        head.addLayout(name_box, 1)

        del_btn: StyledButton = StyledButton(self, "삭제", kind="danger", point_size=9)
        del_btn.clicked.connect(self._remove)
        head.addWidget(del_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        card.addLayout(head)

        self._info_box = QVBoxLayout()
        self._info_box.setContentsMargins(58, 0, 0, 0)
        self._info_box.setSpacing(7)
        card.addLayout(self._info_box)

    def update_from_slot(
        self,
        slot: _EquipSlotData,
        item: OwnedEquipment,
        index: int,
    ) -> None:
        """보유 장비 모델 기준 카드 표시 갱신"""

        self._index = index
        self._selectable = item.name not in slot.unavailable_names
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if self._selectable
            else Qt.CursorShape.ForbiddenCursor
        )
        self.setProperty("current", index == slot.equipped_index)
        self.style().unpolish(self)
        self.style().polish(self)

        has_grade: bool = _has_grade(equipment_item_spec(item))
        self._name_label.setText(item.name)
        self._display_name_label.setText(
            _equipment_display_name(item, slot.slot, has_grade)
        )
        self._reforge_label.setVisible(slot.slot in _REFORGE_EQUIPMENT_SLOTS)
        self._reforge_label.setText(f"+{item.reforge_step}")

        while self._info_box.count():
            layout_item = self._info_box.takeAt(0)
            layout = layout_item.layout()
            if layout is not None:
                self._clear_info_row(layout)

        info_rows: list[tuple[str, list[str]]] = _equipment_pick_info_rows(item)
        for key_text, tokens in info_rows:
            self._info_box.addLayout(self._info_row(key_text, tokens))
        self.updateGeometry()

    def _clear_info_row(self, layout: QLayout) -> None:
        """요약 행 위젯 정리"""

        while layout.count():
            item = layout.takeAt(0)
            widget: QWidget | None = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _remove(self) -> None:
        """현재 카드 장비 삭제"""

        self._tab.remove_owned(self._index)

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

        if not self._selectable:
            super().mousePressEvent(event)
            return

        self._tab.select_owned(self._index)
        super().mousePressEvent(event)


class EquipmentTab(CharacterTab):
    """장비 탭"""

    def __init__(
        self,
        parent: QWidget,
        changes: CharacterChangeHandler,
        profile: CharacterProfile,
    ) -> None:
        super().__init__(parent, changes, profile)

        self._slots_data: list[_EquipSlotData] = self._build_slots_data(profile)
        self._active_index: int = 0
        self._picker_open: bool = False
        self._selected_scroll_id: str | None = None

        self._root_layout: QHBoxLayout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(18)
        self._root_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._equip_window: QFrame = self._build_equip_window()
        self._root_layout.addWidget(self._equip_window)
        self._root_layout.addWidget(self._build_detail_area(), 1)

        self._stacked: bool = False
        self._render_slots()
        self._show_detail()

    def set_profile(self, profile: CharacterProfile) -> None:
        """선택 캐릭터 모델 반영"""

        self._profile = profile
        self._slots_data = self._build_slots_data(profile)
        self._clear_equipped_views()
        self._clear_picker_cards()
        self._refresh_slots()
        self._show_detail()

    def _build_slots_data(
        self,
        profile: CharacterProfile,
    ) -> list[_EquipSlotData]:
        """실제 장비 모델 기준 슬롯 데이터 구성"""

        slots_data: list[_EquipSlotData] = []
        for slot in _SLOT_ORDER:
            # 다른 슬롯에 장착된 장비의 선택 차단 목록 구성
            other_equipped_names: set[str] = {
                equipment_name
                for equipped_slot, equipment_name in profile.equipment.equipped.items()
                if equipped_slot != slot and equipment_name is not None
            }
            owned: list[OwnedEquipment] = list_equippable_equipment(profile, slot)
            equipped_name: str | None = profile.equipment.equipped[slot]
            equipped_index: int = -1
            for index, equipment in enumerate(owned):
                if equipment.name != equipped_name:
                    continue

                equipped_index = index
                break

            slots_data.append(
                _EquipSlotData(
                    slot=slot,
                    owned=owned,
                    equipped_index=equipped_index,
                    unavailable_names=other_equipped_names,
                )
            )

        return slots_data

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
            (self._left_col, _EQUIP_COL_LEFT),
            (self._right_col, _EQUIP_COL_RIGHT),
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

    def _refresh_slots(self) -> None:
        """전체 슬롯 타일 표시 갱신"""

        for index, slot_widget in self._slot_widgets.items():
            slot_widget.update_from_slot(self._slots_data[index])

        self._highlight_active()

    def _refresh_active_slot(self) -> None:
        """장착 변경 후 현재 슬롯 타일 표시 갱신"""

        # 현재 슬롯 위젯 구성 불변식에 따른 직접 갱신
        slot_widget: _EquipSlot = self._slot_widgets[self._active_index]
        slot_widget.update_from_slot(self._slots_data[self._active_index])

    def select_slot(self, index: int) -> None:
        """슬롯 선택 시 상세 갱신 (선택 화면은 닫는다)"""

        self._active_index = index
        self._picker_open = False
        self._highlight_active()
        self._show_detail()

    # 우측 상세

    def _build_detail_area(self) -> QFrame:
        """우측 상세 카드 (별도 스크롤 없이 본문 스크롤을 장비창과 공유)"""

        self._detail_content: QFrame = QFrame(self)
        self._detail_content.setObjectName("charCard")
        self._detail_layout = QVBoxLayout(self._detail_content)
        self._detail_layout.setContentsMargins(18, 18, 18, 18)
        self._detail_layout.setSpacing(0)

        self._detail_stack: _DetailStack = _DetailStack(self._detail_content)
        self._equipped_stack: _DetailStack = _DetailStack(self._detail_stack)
        self._equipped_view: _EquipmentDetailView | None = None
        self._slot_views: dict[EquipmentSlot, list[_EquipmentDetailView]] = {
            slot: [] for slot in EquipmentSlot
        }
        self._picker_cards: list[_EquipPickCard] = []
        self._picker_page: QFrame = self._build_picker_page()
        self._empty_page: QFrame = self._build_empty_page()

        self._detail_stack.addWidget(self._equipped_stack)
        self._detail_stack.addWidget(self._picker_page)
        self._detail_stack.addWidget(self._empty_page)
        self._detail_layout.addWidget(self._detail_stack)
        return self._detail_content

    def _show_detail(self) -> None:
        """현재 상태에 맞는 고정 상세 페이지 표시"""

        slot: _EquipSlotData = self._slots_data[self._active_index]

        if self._picker_open:
            self._equipped_view = None
            self._sync_picker_list(slot)
            self._detail_stack.setCurrentWidget(self._picker_page)
            return

        item = slot.equipped()
        if item is None:
            self._equipped_view = None
            self._empty_title_label.setText(EQUIPMENT_SLOT_LABELS[slot.slot])
            self._detail_stack.setCurrentWidget(self._empty_page)
            return

        view: _EquipmentDetailView = self._bind_equipped_view(slot, item)
        self._equipped_stack.setCurrentWidget(view.page)
        self._detail_stack.setCurrentWidget(self._equipped_stack)
        self._detail_content.updateGeometry()
        self.updateGeometry()

    def _bind_equipped_view(
        self,
        slot: _EquipSlotData,
        item: OwnedEquipment,
    ) -> _EquipmentDetailView:
        """현재 장비가 바뀐 경우에만 상세 페이지 바인딩"""

        for view in self._slot_views[slot.slot]:
            if view.item is item:
                self._equipped_view = view
                return view

        view: _EquipmentDetailView = self._build_equipped_view(slot, item)
        self._slot_views[slot.slot].append(view)
        self._equipped_view = view
        self._equipped_stack.addWidget(view.page)
        return view

    def _build_equipped_view(
        self,
        slot: _EquipSlotData,
        item: OwnedEquipment,
    ) -> _EquipmentDetailView:
        """장착 장비 상세 페이지 최초 구성"""

        page: QFrame = QFrame(self._equipped_stack)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        item_spec: EquipmentItemSpec | None = equipment_item_spec(item)
        has_grade: bool = _has_grade(item_spec)
        has_potential: bool = slot.slot in POTENTIAL_EQUIPMENT_SLOTS
        is_free_stat: bool = item.kind in (
            EquipmentKind.RING,
            EquipmentKind.EARRING,
        )

        head, display_name_label = self._build_detail_head(slot, item, has_grade)
        layout.addWidget(head)

        item_section: _ItemSection | None = None
        if not is_free_stat:
            item_section = self._build_item_section(slot, item, has_grade)
            layout.addWidget(item_section.widget)

        base_group, base_section, reforge_section = self._build_base_group(slot, item)
        layout.addWidget(base_group)

        scroll_section: _ScrollSection | None = None
        if slot.slot in _SCROLL_SETS:
            scroll_section = self._build_scroll_section(slot)
            layout.addWidget(scroll_section.widget)

        if has_potential:
            layout.addWidget(self._build_option_group())

        layout.addStretch(1)
        return _EquipmentDetailView(
            item=item,
            slot=slot.slot,
            page=page,
            display_name_label=display_name_label,
            item_section=item_section,
            base_section=base_section,
            reforge_section=reforge_section,
            scroll_section=scroll_section,
        )

    def _build_detail_head(
        self,
        slot: _EquipSlotData,
        item: OwnedEquipment,
        has_grade: bool,
    ) -> tuple[QFrame, QLabel]:
        """상세 헤더 (아이콘 + 저장 이름 + 인게임 이름 + 교체 버튼)"""

        container: QFrame = QFrame(self)
        head = QHBoxLayout(container)
        head.setContentsMargins(0, 0, 0, 12)
        head.setSpacing(12)

        icon: QLabel = _make_icon(self, 46)
        head.addWidget(icon)

        name_box = QVBoxLayout()
        name_box.setSpacing(4)

        # 저장 참조 이름 직접 입력
        name_edit: QLineEdit = QLineEdit(item.name, self)
        name_edit.setObjectName("charTitleName")
        name_edit.setFont(CustomFont(15, bold=True))
        name_edit.editingFinished.connect(
            lambda field=name_edit, target=item: self._rename_current(field, target)
        )
        name_box.addWidget(name_edit)

        # 현재 스펙 기준 인게임 이름 표시
        display_name: str = _equipment_display_name(item, slot.slot, has_grade)
        display_name_label: QLabel = QLabel(display_name, self)
        display_name_label.setObjectName("charSub")
        display_name_label.setFont(CustomFont(9))
        name_box.addWidget(display_name_label)
        head.addLayout(name_box)

        head.addStretch(1)
        change_btn: StyledButton = StyledButton(
            self, "장비 교체", kind="normal", point_size=9
        )
        change_btn.clicked.connect(self.open_picker)
        head.addWidget(change_btn)
        return container, display_name_label

    def _build_base_group(
        self,
        slot: _EquipSlotData,
        item: OwnedEquipment,
    ) -> tuple[
        ResponsiveColumnsBox,
        _BaseSection | None,
        _ReforgeSection | None,
    ]:
        """기본 스탯과 재련 섹션 그룹 구성"""

        group: ResponsiveColumnsBox = ResponsiveColumnsBox(
            self._detail_content, min_column_width=300, spacing=18
        )
        base_section: _BaseSection | None = None
        reforge_section: _ReforgeSection | None = None
        if slot.slot != EquipmentSlot.NECKLACE:
            base_section = self._build_base_section(slot, item)
            group.addWidget(base_section.widget)
        if slot.slot in _REFORGE_EQUIPMENT_SLOTS:
            reforge_section = self._build_reforge_section(slot, item)
            group.addWidget(reforge_section.widget)
        return group, base_section, reforge_section

    def _build_option_group(self) -> ResponsiveColumnsBox:
        """잠재능력과 추가능력 섹션 그룹 구성"""

        group: ResponsiveColumnsBox = ResponsiveColumnsBox(
            self._detail_content, min_column_width=300, spacing=18
        )
        group.addWidget(self._build_option_section(_POTENTIAL_SECTION))
        group.addWidget(self._build_option_section(_ADDITIONAL_SECTION))
        return group

    def _require_equipped_view(self, item: OwnedEquipment) -> _EquipmentDetailView:
        """현재 장비에 바인딩된 상세 조회"""

        view: _EquipmentDetailView | None = self._equipped_view
        if view is None or view.item is not item:
            raise ValueError("current equipment detail is not bound")
        return view

    def _discard_equipment_views(self, item: OwnedEquipment) -> None:
        """삭제된 장비의 상세 페이지 정리"""

        for slot, views in tuple(self._slot_views.items()):
            matching_views: list[_EquipmentDetailView] = [
                view for view in views if view.item is item
            ]
            for view in matching_views:
                views.remove(view)
                self._equipped_stack.removeWidget(view.page)
                view.page.deleteLater()
                if self._equipped_view is view:
                    self._equipped_view = None

    def _clear_equipped_views(self) -> None:
        """프로필에 종속된 슬롯 상세 페이지 정리"""

        for views in self._slot_views.values():
            for view in views:
                self._equipped_stack.removeWidget(view.page)
                view.page.deleteLater()
        self._slot_views = {slot: [] for slot in EquipmentSlot}
        self._equipped_view = None

    def _clear_picker_cards(self) -> None:
        """장비 선택 카드 목록 정리"""

        for card in self._picker_cards:
            self._picker_list.removeWidget(card)
            card.deleteLater()
        self._picker_cards = []

    def _build_level_tier_row(
        self, item: OwnedEquipment, slot: EquipmentSlot
    ) -> tuple[QHBoxLayout, CharComboBox, CharComboBox]:
        """레벨/티어 콤보박스 선택 행"""

        controls = QHBoxLayout()
        controls.setSpacing(8)

        controls.addWidget(_field_caption(self, "레벨"))
        level_values: tuple[int, ...] = _equipment_levels(slot)
        level_combo: CharComboBox = CharComboBox(
            self, [str(level) for level in level_values], point_size=9
        )
        level_combo.setCurrentIndex(level_values.index(item.level))
        level_combo.currentTextChanged.connect(self._pick_level)
        controls.addWidget(level_combo)

        controls.addSpacing(8)

        controls.addWidget(_field_caption(self, "티어"))
        tier_values: tuple[int, ...] = _equipment_tiers(slot, item.level)
        tier_combo: CharComboBox = CharComboBox(
            self, [str(tier) for tier in tier_values], point_size=9
        )
        tier_combo.setCurrentIndex(tier_values.index(item.tier))
        tier_combo.currentTextChanged.connect(self._pick_tier)
        controls.addWidget(tier_combo)

        controls.addStretch(1)
        return controls, level_combo, tier_combo

    def _build_necklace_type_row(
        self,
        item: OwnedEquipment,
    ) -> tuple[QHBoxLayout, CharComboBox]:
        """목걸이 종류 선택 행"""

        controls = QHBoxLayout()
        controls.setSpacing(8)

        controls.addWidget(_field_caption(self, "종류"))

        type_combo: CharComboBox = CharComboBox(
            self, list(_NECKLACE_TYPES), point_size=9
        )
        item_name: str | None = item.item_name
        if item_name is not None and item_name in _NECKLACE_TYPES:
            type_combo.setCurrentIndex(_NECKLACE_TYPES.index(item_name))
        type_combo.currentTextChanged.connect(self._pick_necklace_type)
        controls.addWidget(type_combo)

        controls.addStretch(1)
        return controls, type_combo

    def _current_item(self) -> OwnedEquipment | None:
        """현재 슬롯의 장착 장비"""

        return self._slots_data[self._active_index].equipped()

    def _commit_active_item(self) -> None:
        """현재 장비 변경 후 슬롯 타일과 실시간 표시 갱신"""

        self._refresh_active_slot()
        self._changes.stats_changed()

    def _pick_level(self, text: str) -> None:
        """선택한 장비 레벨을 현재 장비에 반영"""

        item = self._current_item()
        if item is not None:
            item.level = int(text)

            # 레벨 변경 시 티어와 주문서 입력 상태 초기화
            item.tier = 1
            item.scrolls = []
            self._selected_scroll_id = None
            view: _EquipmentDetailView = self._require_equipped_view(item)
            if view.item_section is None:
                raise ValueError("item section is not available")
            view.item_section.update_tiers(view.slot, item)
            view.update_display_name()
            if view.base_section is not None:
                view.base_section.update_values(view.slot, item)
            if view.scroll_section is not None:
                self._refresh_scroll_section(item)
            self._commit_active_item()

    def _pick_tier(self, text: str) -> None:
        """선택한 장비 티어를 현재 장비에 반영"""

        item = self._current_item()
        if item is not None:
            item.tier = int(text)
            view: _EquipmentDetailView = self._require_equipped_view(item)
            view.update_display_name()
            if view.base_section is not None:
                view.base_section.update_values(view.slot, item)
            self._commit_active_item()

    def _rename_current(self, field: QLineEdit, item: OwnedEquipment) -> None:
        """장비 저장 이름 변경 및 장착 참조 유지"""

        old_name: str = item.name
        new_name: str = field.text().strip()
        if new_name == old_name:
            return

        if not new_name:
            field.setText(old_name)
            return

        try:
            rename_equipment(self._profile, old_name, new_name)
        except ValueError:
            # 이름 중복 등 무효 입력은 이전 이름으로 되돌린다
            field.setText(old_name)
            return

        view: _EquipmentDetailView = self._require_equipped_view(item)
        view.update_display_name()

        self._refresh_active_slot()
        self._changes.saved_value_changed()

    def _pick_necklace_type(self, text: str) -> None:
        """목걸이 종류 변경 (종류별 허용 재련 스탯으로 정리)"""

        item = self._current_item()
        if item is None:
            return

        item.item_name = text
        allowed_keys: tuple[StatKey, ...] = NECKLACE_REFORGE_STAT_KEYS[text]
        item.reforge_stats = {
            stat_key: value
            for stat_key, value in item.reforge_stats.items()
            if stat_key in allowed_keys
        }
        view: _EquipmentDetailView = self._require_equipped_view(item)
        view.update_display_name()
        if view.reforge_section is None:
            raise ValueError("reforge section is not available")
        view.reforge_section.update_stat_fields(view.slot, item)
        self._commit_active_item()

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
        slot: _EquipSlotData,
        item: OwnedEquipment,
        has_grade: bool,
    ) -> _ItemSection:
        """아이템 섹션 (레벨/티어 + 등급)"""

        section, box = self._section("아이템")

        # 목걸이는 레벨·티어 대신 종류를 선택한다
        if slot.slot == EquipmentSlot.NECKLACE:
            row, type_combo = self._build_necklace_type_row(item)
            box.addLayout(row)
            return _ItemSection(widget=section, necklace_type=type_combo)

        # 등급(기본/찬란한)은 무기·방어구만. 공간이 남으면 레벨·티어 오른쪽에 등급을 배치
        if not has_grade:
            row, level_combo, tier_combo = self._build_level_tier_row(item, slot.slot)
            box.addLayout(row)
            return _ItemSection(
                widget=section,
                level=level_combo,
                tier=tier_combo,
            )

        fields_group: ResponsiveColumnsBox = ResponsiveColumnsBox(
            section, min_column_width=160, spacing=18, fill=False
        )

        level_tier_block: QFrame = QFrame(section)
        level_tier_box = QVBoxLayout(level_tier_block)
        level_tier_box.setContentsMargins(0, 0, 0, 0)
        level_tier_box.setSpacing(0)
        level_tier_row, level_combo, tier_combo = self._build_level_tier_row(
            item, slot.slot
        )
        level_tier_box.addLayout(level_tier_row)
        fields_group.addWidget(level_tier_block)

        grade_block: QFrame = QFrame(section)
        grade_box = QVBoxLayout(grade_block)
        grade_box.setContentsMargins(0, 0, 0, 0)
        grade_box.setSpacing(0)
        grade_row, grade_button = self._build_grade_row(item)
        grade_box.addLayout(grade_row)
        fields_group.addWidget(grade_block)

        box.addWidget(fields_group)
        return _ItemSection(
            widget=section,
            level=level_combo,
            tier=tier_combo,
            grade=grade_button,
        )

    def _build_grade_row(
        self,
        item: OwnedEquipment,
    ) -> tuple[QHBoxLayout, QPushButton]:
        """등급 행 (레벨/티어처럼 라벨 + 찬란한 토글 버튼, ON 시 강조색)"""

        controls = QHBoxLayout()
        controls.setSpacing(8)

        controls.addWidget(_field_caption(self, "등급"))

        grade_btn: QPushButton = QPushButton("찬란한", self)
        grade_btn.setObjectName("charEquipToggle")
        grade_btn.setFont(CustomFont(9))
        grade_btn.setCheckable(True)
        grade_btn.setChecked(item.grade == EquipmentGrade.RADIANT)
        grade_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        grade_btn.clicked.connect(self._on_grade_toggle)
        controls.addWidget(grade_btn)

        controls.addStretch(1)
        return controls, grade_btn

    def _on_grade_toggle(self, active: bool) -> None:
        """찬란한 버튼 토글 시 등급 반영 및 표시 이름 갱신"""

        item = self._current_item()
        if item is not None:
            item.grade = EquipmentGrade.RADIANT if active else EquipmentGrade.BASIC
            view: _EquipmentDetailView = self._require_equipped_view(item)
            view.update_display_name()
            if view.base_section is not None:
                view.base_section.update_values(view.slot, item)
            self._commit_active_item()

    def _build_base_section(
        self,
        slot: _EquipSlotData,
        item: OwnedEquipment,
    ) -> _BaseSection:
        """기본 스탯 섹션 (방어구/무기 자동 표시 vs 반지/귀걸이 자유 입력)"""

        section, box = self._section("기본 스탯")

        # 반지/귀걸이: 자유 스탯 라인
        if slot.slot in FREE_BASE_STAT_EQUIPMENT_SLOTS:
            free_rows = QVBoxLayout()
            free_rows.setSpacing(8)
            # 저장된 자유 기본 스탯 라인 표시값 구성
            for index, line in enumerate(item.base_stat_lines):
                stat: str = STAT_SPECS[line.stat_key]
                value: str = f"{line.value:g}"
                free_rows.addLayout(self._build_free_stat_row(item, index, stat, value))
            box.addLayout(free_rows)

            add_btn: StyledButton = StyledButton(
                section, "+ 스탯 추가", kind="normal", point_size=9
            )
            add_btn.clicked.connect(lambda: self._add_free_stat(item))
            box.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)
            return _BaseSection(widget=section, free_rows=free_rows)

        # 무기·방어구: 자동 제공되는 읽기 전용 스탯 / 그 외(목걸이 등): 직접 입력
        base_rows: list[tuple[str, float]] = _equipment_base_rows(item, slot.slot)
        auto_provided: bool = _has_grade(equipment_item_spec(item))
        static_fields: dict[str, tuple[QWidget, StaticValueField]] = {}

        flow: FlowLayout = FlowLayout(spacing=14)

        def make_static_field(
            label: str,
            value: float,
        ) -> tuple[QWidget, StaticValueField]:
            container, field = self._build_labeled_field(
                label,
                str(value),
                readonly=auto_provided,
            )
            if not isinstance(field, StaticValueField):
                raise ValueError("automatic base stat must be read-only")
            return container, field

        for label_text, v in base_rows:
            container, field = make_static_field(label_text, v)
            flow.addWidget(container)
            static_fields[label_text] = (container, field)
        box.addLayout(flow)
        return _BaseSection(
            widget=section,
            static_flow=flow,
            static_fields=static_fields,
            make_static_field=make_static_field,
        )

    def _build_free_stat_row(
        self,
        item: OwnedEquipment,
        index: int,
        stat: str,
        value: str,
    ) -> QHBoxLayout:
        """반지/귀걸이 자유 스탯 한 줄 (콤보 + 값)"""

        row = QHBoxLayout()
        row.setSpacing(10)
        combo: CharComboBox = CharComboBox(self, list(STAT_CHOICE_LABELS))
        if stat in STAT_CHOICE_LABELS:
            combo.setCurrentText(stat)
        field: StepperField = StepperField(self, value or "0", max_width=140)
        combo.currentTextChanged.connect(
            lambda text, field=field: self._set_free_stat_line(
                item,
                index,
                text,
                field.number(),
            )
        )
        field.value_changed.connect(
            lambda combo=combo, field=field: self._set_free_stat_line(
                item,
                index,
                combo.currentText(),
                field.number(),
            )
        )
        row.addWidget(combo, 1)
        row.addWidget(field)
        return row

    def _add_free_stat(self, item: OwnedEquipment) -> None:
        """자유 스탯 라인 추가"""

        item.base_stat_lines.append(
            EquipmentFreeStatLine(stat_key=StatKey.ATTACK, value=0.0)
        )
        index: int = len(item.base_stat_lines) - 1
        view: _EquipmentDetailView | None = self._equipped_view
        if (
            view is None
            or view.item is not item
            or view.base_section is None
            or view.base_section.free_rows is None
        ):
            raise ValueError("free stat detail is not bound")

        free_rows: QVBoxLayout = view.base_section.free_rows
        free_rows.addLayout(
            self._build_free_stat_row(item, index, STAT_SPECS[StatKey.ATTACK], "0")
        )
        self._changes.saved_value_changed()

    def _set_free_stat_line(
        self,
        item: OwnedEquipment,
        index: int,
        stat: str,
        value: float,
    ) -> None:
        """자유 기본 스탯 라인 모델 반영"""

        if stat == "미설정":
            return

        item.base_stat_lines[index] = EquipmentFreeStatLine(
            stat_key=STAT_LABEL_TO_KEY[stat],
            value=value,
        )
        self._changes.stats_changed()

    def _build_reforge_section(
        self, slot: _EquipSlotData, item: OwnedEquipment
    ) -> _ReforgeSection:
        """재련 섹션 (부위/목걸이 종류별 허용 스탯 입력)"""

        section, box = self._section("재련")

        flow: FlowLayout = FlowLayout(spacing=14)
        # 맨 처음에 재련 단계(0~20강) 입력칸
        flow.addWidget(self._build_step_field(item))
        stat_fields: dict[StatKey, QWidget] = {}

        def make_stat_field(stat_key: StatKey, value: float) -> QWidget:
            label: str = STAT_SPECS[stat_key]
            container, _field = self._build_labeled_field(
                label,
                f"{value:g}",
                on_changed=lambda field, key=stat_key, target=item: self._set_reforge_stat(
                    target,
                    key,
                    field.number(),
                ),
            )
            return container

        for stat_key in _reforge_stat_keys(slot.slot, item.item_name):
            container: QWidget = make_stat_field(
                stat_key,
                item.reforge_stats.get(stat_key, 0.0),
            )
            stat_fields[stat_key] = container
            flow.addWidget(container)
        box.addLayout(flow)
        return _ReforgeSection(
            widget=section,
            flow=flow,
            stat_fields=stat_fields,
            make_stat_field=make_stat_field,
        )

    def _build_step_field(self, item: OwnedEquipment) -> QWidget:
        """재련 단계(0~20강) 입력 묶음"""

        container: QFrame = QFrame(self)
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        box.addWidget(_field_caption(container, "단계"))

        field: StepperField = StepperField(
            container,
            str(item.reforge_step),
            unit="강",
            integer=True,
        )
        field.setFixedWidth(84)
        field.value_changed.connect(
            lambda target=item, value_field=field: self._set_reforge_step(
                target,
                value_field,
            )
        )
        box.addWidget(field)
        return container

    def _set_reforge_step(self, item: OwnedEquipment, field: StepperField) -> None:
        """재련 단계 모델 반영"""

        step: int = max(0, min(MAX_REFORGE_STEP, int(field.number())))
        field.set_number(float(step))
        if item.reforge_step == step:
            return

        item.reforge_step = step
        self._changes.stats_changed()

    def _build_scroll_section(self, slot: _EquipSlotData) -> _ScrollSection:
        """주문서 섹션 (좌: 선택 / 우: 적용 목록)"""

        section, box = self._section("주문서")

        if slot.slot not in _SCROLL_SETS:
            raise ValueError("scroll slot is required")

        item: OwnedEquipment | None = slot.equipped()
        if item is None:
            raise ValueError("equipped item is required")

        scroll_set: _ScrollSet = _SCROLL_SETS[slot.slot]
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = (
            EQUIPMENT_SCROLL_EFFECTS[slot.slot]
        )
        self._ensure_selected_scroll_id(item)
        selected_line: EquipmentScrollLine | None = self._selected_scroll_line(item)
        selected_stat_key, selected_tier, stat_enabled, tier_effects, tier_enabled = (
            self._scroll_selector_state(
                item,
                scroll_set,
                slot_effects,
                selected_line,
            )
        )

        scroll_columns: ResponsiveColumnsBox = ResponsiveColumnsBox(
            section, min_column_width=280, spacing=12
        )
        (
            selector_panel,
            list_panel,
            stat_buttons,
            tier_content,
            tier_layout,
            tier_buttons,
            add_button,
            list_content,
            list_layout,
            rows,
            row_ids,
        ) = self._build_scroll_panels(
            slot,
            item,
            scroll_set,
            slot_effects,
            selected_stat_key,
            selected_tier,
            stat_enabled,
            tier_effects,
            tier_enabled,
        )
        selector_panel.setMinimumWidth(260)
        list_panel.setMinimumWidth(260)
        scroll_columns.addWidget(selector_panel)
        scroll_columns.addWidget(list_panel)
        box.addWidget(scroll_columns)

        return _ScrollSection(
            widget=section,
            selector_panel=selector_panel,
            list_panel=list_panel,
            stat_buttons=stat_buttons,
            tier_content=tier_content,
            tier_layout=tier_layout,
            tier_buttons=tier_buttons,
            add_button=add_button,
            list_content=list_content,
            list_layout=list_layout,
            rows=rows,
            row_ids=row_ids,
        )

    def _refresh_scroll_section(self, item: OwnedEquipment) -> None:
        """현재 장비 주문서 섹션 갱신"""

        view: _EquipmentDetailView = self._require_equipped_view(item)
        scroll_section: _ScrollSection | None = view.scroll_section
        if scroll_section is None:
            raise ValueError("scroll section is not available")

        slot: _EquipSlotData = self._slots_data[self._active_index]
        if slot.equipped() is not item:
            raise ValueError("active equipment is not bound")

        scroll_set: _ScrollSet = _SCROLL_SETS[slot.slot]
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = (
            EQUIPMENT_SCROLL_EFFECTS[slot.slot]
        )
        self._ensure_selected_scroll_id(item)
        selected_line: EquipmentScrollLine | None = self._selected_scroll_line(item)
        selected_stat_key, selected_tier, stat_enabled, tier_effects, tier_enabled = (
            self._scroll_selector_state(
                item,
                scroll_set,
                slot_effects,
                selected_line,
            )
        )
        scroll_section.update_selector(
            selected_stat_key,
            selected_tier,
            stat_enabled,
            tier_effects,
            tier_enabled,
            self._scroll_add_button_text(slot.slot, item),
            self._can_add_scroll_line(slot.slot, item, scroll_set, slot_effects),
            self._scroll_option_text,
            lambda tier, effects: self._build_scroll_tier_button(
                scroll_section.tier_content,
                tier,
                effects,
            ),
        )
        scroll_section.update_rows(
            self._scroll_row_entries(item, scroll_set, slot_effects),
            self._selected_scroll_id,
            self._scroll_row_title,
            self._scroll_effect_text,
            lambda line, effects: self._build_scroll_row(
                scroll_section.list_content,
                slot.slot,
                item,
                line,
                effects,
            ),
        )
        scroll_section.widget.updateGeometry()

    def _ensure_selected_scroll_id(self, item: OwnedEquipment) -> None:
        """현재 장비의 선택 주문서 라인 보정"""

        if self._selected_scroll_id in {scroll.id for scroll in item.scrolls}:
            return

        self._selected_scroll_id = item.scrolls[0].id if item.scrolls else None

    def _selected_scroll_line(
        self,
        item: OwnedEquipment,
    ) -> EquipmentScrollLine | None:
        """현재 선택 주문서 라인 조회"""

        if self._selected_scroll_id is None:
            return None

        for scroll in item.scrolls:
            if scroll.id == self._selected_scroll_id:
                return scroll

        return None

    def _scroll_selector_state(
        self,
        item: OwnedEquipment,
        scroll_set: _ScrollSet,
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]],
        selected_line: EquipmentScrollLine | None,
    ) -> tuple[
        StatKey | None,
        ScrollTier | None,
        dict[StatKey, bool],
        dict[ScrollTier, dict[StatKey, float]],
        dict[ScrollTier, bool],
    ]:
        """선택 주문서 라인 기준 선택 패널 상태 구성"""

        selected_stat_key: StatKey | None = (
            selected_line.stat_key if selected_line is not None else None
        )
        selected_tier: ScrollTier | None = (
            selected_line.tier if selected_line is not None else None
        )
        stat_enabled: dict[StatKey, bool] = {
            stat_key: (
                selected_line is not None
                and self._first_available_scroll_tier(
                    item,
                    selected_line,
                    stat_key,
                    slot_effects,
                )
                is not None
            )
            for stat_key in scroll_set.stat_keys
        }
        tier_effects: dict[ScrollTier, dict[StatKey, float]] = (
            slot_effects[selected_stat_key] if selected_stat_key is not None else {}
        )
        tier_enabled: dict[ScrollTier, bool] = {
            tier: (
                selected_line is not None
                and self._can_use_scroll_key(
                    item,
                    selected_line,
                    selected_stat_key,
                    tier,
                )
            )
            for tier in tier_effects
        }
        return (
            selected_stat_key,
            selected_tier,
            stat_enabled,
            tier_effects,
            tier_enabled,
        )

    def _build_scroll_panels(
        self,
        slot: _EquipSlotData,
        item: OwnedEquipment,
        scroll_set: _ScrollSet,
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]],
        selected_stat_key: StatKey | None,
        selected_tier: ScrollTier | None,
        stat_enabled: dict[StatKey, bool],
        tier_effects: dict[ScrollTier, dict[StatKey, float]],
        tier_enabled: dict[ScrollTier, bool],
    ) -> tuple[
        QFrame,
        QFrame,
        dict[StatKey, QPushButton],
        QWidget,
        QVBoxLayout,
        dict[ScrollTier, QPushButton],
        StyledButton,
        QWidget,
        QVBoxLayout,
        dict[str, _ScrollRow],
        tuple[str, ...],
    ]:
        """주문서 선택 패널과 목록 패널 구성"""

        panels = ChoiceListPanels(
            self,
            selector_title="주문서 선택",
            list_title="적용된 주문서",
            add_text=self._scroll_add_button_text(slot.slot, item),
            add_clicked=lambda: self._add_selected_scroll(slot.slot, item),
            option_title="확률",
            selector_scroll_min_height=150,
            list_scroll_min_height=150,
        )
        stat_buttons: dict[StatKey, QPushButton] = {}
        for stat_key in scroll_set.stat_keys:
            stat_button: QPushButton = panels.make_choice_button(
                panels.selector_panel,
                STAT_SPECS[stat_key],
                "charScrollChoiceBtn",
                checked=stat_key is selected_stat_key,
                enabled=stat_enabled[stat_key],
            )
            stat_button.clicked.connect(
                lambda _checked=False, key=stat_key: self._select_scroll_stat(
                    key,
                    slot.slot,
                )
            )
            stat_buttons[stat_key] = stat_button
            panels.group_layout.addWidget(stat_button)

        panels.group_layout.addStretch(1)
        tier_buttons: dict[ScrollTier, QPushButton] = {}
        for tier, effects in tier_effects.items():
            tier_button: QPushButton = self._build_scroll_tier_button(
                panels.option_scroll_content,
                tier,
                effects,
            )
            tier_button.setChecked(tier is selected_tier)
            tier_button.setEnabled(tier_enabled[tier])
            tier_buttons[tier] = tier_button
            panels.option_layout.addWidget(tier_button)

        panels.option_layout.addStretch(1)
        panels.add_button.setEnabled(
            self._can_add_scroll_line(slot.slot, item, scroll_set, slot_effects)
        )
        rows: dict[str, _ScrollRow] = {}
        row_ids: list[str] = []
        for line, effects in self._scroll_row_entries(
            item,
            scroll_set,
            slot_effects,
        ):
            row = self._build_scroll_row(
                panels.list_scroll_content,
                slot.slot,
                item,
                line,
                effects,
            )
            rows[line.id] = row
            row_ids.append(line.id)
            panels.list_layout.addWidget(row.widget)

        panels.list_layout.addStretch(1)
        return (
            panels.selector_panel,
            panels.list_panel,
            stat_buttons,
            panels.option_scroll_content,
            panels.option_layout,
            tier_buttons,
            panels.add_button,
            panels.list_scroll_content,
            panels.list_layout,
            rows,
            tuple(row_ids),
        )

    def _build_scroll_tier_button(
        self,
        parent: QWidget,
        tier: ScrollTier,
        effects: dict[StatKey, float],
    ) -> QPushButton:
        """주문서 확률 선택 버튼 구성"""

        tier_button: QPushButton = QPushButton(
            self._scroll_option_text(tier, effects),
            parent,
        )
        tier_button.setObjectName("charScrollChoiceBtn")
        tier_button.setCheckable(True)
        tier_button.setCursor(Qt.CursorShape.PointingHandCursor)
        tier_button.setFont(CustomFont(9, bold=True))
        tier_button.setMinimumHeight(36)
        tier_button.clicked.connect(
            lambda _checked=False, scroll_tier=tier: self._select_scroll_tier(
                scroll_tier
            )
        )
        return tier_button

    def _scroll_row_entries(
        self,
        item: OwnedEquipment,
        scroll_set: _ScrollSet,
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]],
    ) -> list[tuple[EquipmentScrollLine, dict[StatKey, float]]]:
        """적용 주문서 행 표시 데이터 구성"""

        entries: list[tuple[EquipmentScrollLine, dict[StatKey, float]]] = []
        for scroll in item.scrolls:
            entries.append(
                (
                    scroll,
                    slot_effects[scroll.stat_key][scroll.tier],
                )
            )
        return entries

    def _build_scroll_row(
        self,
        parent: QWidget,
        slot: EquipmentSlot,
        item: OwnedEquipment,
        line: EquipmentScrollLine,
        effects: dict[StatKey, float],
    ) -> _ScrollRow:
        """적용 주문서 행 구성"""

        row = ResponsiveActionCard(parent, "charScrollCard", stack_threshold=340)
        row.setProperty("selected", line.id == self._selected_scroll_id)
        row.clicked.connect(lambda: self._select_scroll_line(item, line))

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_label: QLabel = QLabel(
            self._scroll_row_title(line),
            row,
        )
        title_label.setObjectName("charScrollName")
        title_label.setFont(CustomFont(10, bold=True))
        title_label.setWordWrap(True)
        title_row.addWidget(title_label, 1)
        row.info_layout.addLayout(title_row)

        effect_label: QLabel = QLabel(self._scroll_effect_text(effects), row)
        effect_label.setObjectName("charScrollEffect")
        effect_label.setFont(CustomFont(9))
        effect_label.setWordWrap(True)
        row.info_layout.addWidget(effect_label)

        scroll_limit: int | None = _equipment_scroll_limit(slot, item)
        count_field: StepperField = StepperField(
            row,
            str(line.count),
            unit="회",
            max_width=74,
            min_value=1,
            integer=True,
        )
        count_field.value_changed.connect(
            lambda target=item, target_line=line, field=count_field: self._set_scroll_count_from_field(
                target,
                target_line,
                field,
            )
        )
        count_field.input.editingFinished.connect(
            lambda target=item, slot_key=slot, target_line=line, field=count_field: self._finish_scroll_count(
                target,
                slot_key,
                target_line,
                field,
            )
        )
        row.action_layout.addWidget(count_field)
        row.action_layout.addSpacing(14)
        row.action_layout.addStretch(1)
        remove_btn: StyledButton = StyledButton(
            row, "삭제", kind="danger", point_size=9
        )
        remove_btn.setFixedWidth(54)
        remove_btn.clicked.connect(lambda: self._remove_scroll_entry(item, line))
        row.action_layout.addWidget(remove_btn)
        return _ScrollRow(
            line_id=line.id,
            widget=row,
            title_label=title_label,
            effect_label=effect_label,
            count_field=count_field,
        )

    def _build_option_section(self, option_section: _EquipmentOptionSection) -> QFrame:
        """잠재/추가능력 섹션 (3줄 고정)"""

        section, box = self._section(option_section.title)
        item: OwnedEquipment | None = self._current_item()
        if item is None:
            raise ValueError("equipped item is required")

        for index in range(EQUIPMENT_OPTION_SLOT_COUNT):
            row = QHBoxLayout()
            row.setSpacing(10)
            combo: CharComboBox = CharComboBox(
                section,
                ["미설정", *option_section.labels],
            )
            # 입력칸은 고정 폭으로 두어 창 크기에 따라 늘어나지 않게 한다
            field: StepperField = StepperField(section, "0")
            field.setFixedWidth(100)

            # 옵션 종류별 저장 라인 표시
            if option_section.kind == _OptionSectionKind.POTENTIAL:
                potential_line: PotentialLine | None = item.potentials[index]
                if potential_line is not None:
                    combo.setCurrentText(
                        _POTENTIAL_OPTION_TO_LABEL[potential_line.option]
                    )
                    field.set_number(potential_line.value)

            else:
                additional_line: AdditionalLine | None = item.additionals[index]
                if additional_line is not None:
                    combo.setCurrentText(
                        _ADDITIONAL_OPTION_TO_LABEL[additional_line.option]
                    )
                    field.set_number(additional_line.value)

            combo.currentTextChanged.connect(
                lambda text, target=item, line_index=index, value_field=field, kind=option_section.kind: self._set_option_line(
                    target,
                    kind,
                    line_index,
                    text,
                    value_field,
                )
            )
            field.value_changed.connect(
                lambda target=item, line_index=index, option_combo=combo, value_field=field, kind=option_section.kind: self._set_option_line(
                    target,
                    kind,
                    line_index,
                    option_combo.currentText(),
                    value_field,
                )
            )

            row.addWidget(combo, 1)
            row.addWidget(field)
            box.addLayout(row)
        return section

    def _build_labeled_field(
        self,
        label: str,
        value: str,
        readonly: bool = False,
        on_changed: Callable[[StepperField], None] | None = None,
    ) -> tuple[QWidget, QWidget]:
        """라벨 + 수치 묶음 (readonly 면 입력 대신 읽기 전용 표시)"""

        container: QFrame = QFrame(self)
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        unit: str = "%" if "%" in label else ""
        box.addWidget(_field_caption(container, label))

        # %스탯과 일반 스탯 모두 동일한 칸 폭으로 통일
        field: QWidget = (
            StaticValueField(container, value, unit=unit)
            if readonly
            else StepperField(container, value, unit=unit)
        )
        if isinstance(field, StepperField) and on_changed is not None:
            field.value_changed.connect(lambda target=field: on_changed(target))

        field.setFixedWidth(84)
        box.addWidget(field)
        return container, field

    def _set_reforge_stat(
        self,
        item: OwnedEquipment,
        stat_key: StatKey,
        value: float,
    ) -> None:
        """재련 스탯 모델 반영"""

        if value <= 0.0:
            item.reforge_stats.pop(stat_key, None)
        else:
            item.reforge_stats[stat_key] = value

        self._changes.stats_changed()

    def _scroll_effect_text(self, effects: dict[StatKey, float]) -> str:
        """주문서 효과 표시 문자열"""

        return ", ".join(
            f"{STAT_SPECS[stat_key]} {value:+g}" for stat_key, value in effects.items()
        )

    def _scroll_option_text(
        self,
        tier: ScrollTier,
        effects: dict[StatKey, float],
    ) -> str:
        """주문서 확률 선택 버튼 표시 문자열"""

        return f"{_SCROLL_TIER_LABELS[tier]} - {self._scroll_effect_text(effects)}"

    def _scroll_total_count(self, item: OwnedEquipment) -> int:
        """장비 주문서 총 적용 횟수 계산"""

        return sum(scroll.count for scroll in item.scrolls)

    def _scroll_add_button_text(
        self,
        slot: EquipmentSlot,
        item: OwnedEquipment,
    ) -> str:
        """주문서 추가 버튼 문구 구성"""

        scroll_limit: int | None = _equipment_scroll_limit(slot, item)
        if scroll_limit is None:
            return "주문서 추가"

        return f"주문서 추가 ({self._scroll_total_count(item)} / {scroll_limit})"

    def _select_scroll_stat(self, stat_key: StatKey, slot: EquipmentSlot) -> None:
        """주문서 종류 선택"""

        item: OwnedEquipment | None = self._current_item()
        if item is None:
            return

        selected_line: EquipmentScrollLine | None = self._selected_scroll_line(item)
        if selected_line is None:
            return

        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = (
            EQUIPMENT_SCROLL_EFFECTS[slot]
        )
        tier: ScrollTier | None = self._first_available_scroll_tier(
            item,
            selected_line,
            stat_key,
            slot_effects,
        )
        if tier is None:
            self._refresh_scroll_section(item)
            return

        selected_line.stat_key = stat_key
        selected_line.tier = tier
        self._refresh_scroll_section(item)
        self._changes.stats_changed()

    def _select_scroll_tier(self, tier: ScrollTier) -> None:
        """주문서 확률 선택"""

        item: OwnedEquipment | None = self._current_item()
        if item is None:
            return

        selected_line: EquipmentScrollLine | None = self._selected_scroll_line(item)
        if selected_line is None:
            return

        if not self._can_use_scroll_key(
            item,
            selected_line,
            selected_line.stat_key,
            tier,
        ):
            self._refresh_scroll_section(item)
            return

        selected_line.tier = tier
        self._refresh_scroll_section(item)
        self._changes.stats_changed()

    def _select_scroll_line(
        self,
        item: OwnedEquipment,
        line: EquipmentScrollLine,
    ) -> None:
        """적용 주문서 라인 선택"""

        self._selected_scroll_id = line.id
        self._refresh_scroll_section(item)

    def _can_use_scroll_key(
        self,
        item: OwnedEquipment,
        selected_line: EquipmentScrollLine,
        stat_key: StatKey | None,
        tier: ScrollTier,
    ) -> bool:
        """선택 주문서 라인의 조합 변경 가능 여부"""

        if stat_key is None:
            return False

        for scroll in item.scrolls:
            if scroll.id == selected_line.id:
                continue

            if scroll.stat_key == stat_key and scroll.tier == tier:
                return False

        return True

    def _first_available_scroll_tier(
        self,
        item: OwnedEquipment,
        selected_line: EquipmentScrollLine,
        stat_key: StatKey,
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]],
    ) -> ScrollTier | None:
        """종류 변경 시 선택 가능한 첫 주문서 확률 조회"""

        for tier in slot_effects[stat_key]:
            if self._can_use_scroll_key(item, selected_line, stat_key, tier):
                return tier

        return None

    def _first_available_scroll_line(
        self,
        item: OwnedEquipment,
        scroll_set: _ScrollSet,
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]],
    ) -> tuple[StatKey, ScrollTier] | None:
        """아직 적용되지 않은 첫 주문서 조합 조회"""

        used_keys: set[tuple[StatKey, ScrollTier]] = {
            (scroll.stat_key, scroll.tier) for scroll in item.scrolls
        }
        for stat_key in scroll_set.stat_keys:
            for tier in slot_effects[stat_key]:
                if (stat_key, tier) not in used_keys:
                    return stat_key, tier

        return None

    def _can_add_scroll_line(
        self,
        slot: EquipmentSlot,
        item: OwnedEquipment,
        scroll_set: _ScrollSet,
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]],
    ) -> bool:
        """주문서 라인 추가 가능 여부"""

        scroll_limit: int | None = _equipment_scroll_limit(slot, item)
        if scroll_limit is not None and self._scroll_total_count(item) >= scroll_limit:
            return False

        return (
            self._first_available_scroll_line(
                item,
                scroll_set,
                slot_effects,
            )
            is not None
        )

    def _scroll_row_title(self, line: EquipmentScrollLine) -> str:
        """적용 주문서 행 제목 구성"""

        return f"{STAT_SPECS[line.stat_key]} {_SCROLL_TIER_LABELS[line.tier]}"

    def _set_scroll_count(
        self,
        item: OwnedEquipment,
        line: EquipmentScrollLine,
        count: int,
    ) -> None:
        """주문서 성공 횟수 모델 반영"""

        if count <= 0:
            item.scrolls = [scroll for scroll in item.scrolls if scroll.id != line.id]
            if self._selected_scroll_id == line.id:
                self._selected_scroll_id = item.scrolls[0].id if item.scrolls else None
        else:
            line.count = count

    def _set_scroll_count_from_field(
        self,
        item: OwnedEquipment,
        line: EquipmentScrollLine,
        field: StepperField,
    ) -> None:
        """주문서 횟수 입력값 모델 반영"""

        text: str = field.input.text().strip()
        if not text:
            return

        count: int = max(1, int(field.number()))
        self._set_scroll_count(item, line, count)

    def _finish_scroll_count(
        self,
        item: OwnedEquipment,
        slot: EquipmentSlot,
        line: EquipmentScrollLine,
        field: StepperField,
    ) -> None:
        """주문서 입력 종료 시 최대 성공 횟수 기준 보정"""

        field.input.normalize_to_validator()
        self._set_scroll_count_from_field(
            item,
            line,
            field,
        )

        scroll_limit: int | None = _equipment_scroll_limit(slot, item)
        if scroll_limit is None:
            self._refresh_scroll_section(item)
            self._changes.stats_changed()
            return

        total_count: int = self._scroll_total_count(item)
        overflow_count: int = total_count - scroll_limit
        if overflow_count <= 0:
            self._refresh_scroll_section(item)
            self._changes.stats_changed()
            return

        current_count: int = line.count
        adjusted_count: int = max(0, current_count - overflow_count)
        if adjusted_count <= 0:
            self._set_scroll_count(item, line, 0)
            self._refresh_scroll_section(item)
            self._changes.stats_changed()
            return

        field.set_number(float(adjusted_count))
        self._set_scroll_count_from_field(
            item,
            line,
            field,
        )
        self._refresh_scroll_section(item)
        self._changes.stats_changed()

    def _add_selected_scroll(self, slot: EquipmentSlot, item: OwnedEquipment) -> None:
        """첫 미적용 주문서 라인 추가"""

        scroll_limit: int | None = _equipment_scroll_limit(slot, item)
        if scroll_limit is not None and self._scroll_total_count(item) >= scroll_limit:
            return

        scroll_set: _ScrollSet = _SCROLL_SETS[slot]
        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = (
            EQUIPMENT_SCROLL_EFFECTS[slot]
        )
        scroll_key: tuple[StatKey, ScrollTier] | None = (
            self._first_available_scroll_line(item, scroll_set, slot_effects)
        )
        if scroll_key is None:
            return

        stat_key, tier = scroll_key
        scroll = EquipmentScrollLine(stat_key=stat_key, tier=tier, count=1)
        item.scrolls.append(scroll)
        self._selected_scroll_id = scroll.id
        self._refresh_scroll_section(item)
        self._changes.stats_changed()

    def _remove_scroll_entry(
        self,
        item: OwnedEquipment,
        line: EquipmentScrollLine,
    ) -> None:
        """적용 주문서 항목 삭제"""

        self._set_scroll_count(item, line, 0)
        self._refresh_scroll_section(item)
        self._changes.stats_changed()

    def _set_option_line(
        self,
        item: OwnedEquipment,
        kind: _OptionSectionKind,
        index: int,
        label: str,
        field: StepperField,
    ) -> None:
        """잠재/추가능력 라인 모델 반영"""

        # 옵션 종류별 모델 라인 갱신
        if kind == _OptionSectionKind.POTENTIAL:
            potential_lines: list[PotentialLine | None] = list(item.potentials)

            # 잠재능력 미설정 또는 선택 라인 반영
            if label == "미설정":
                potential_lines[index] = None

            else:
                potential_option: PotentialOption = _POTENTIAL_LABEL_TO_OPTION[label]
                option_range: ValueRange = POTENTIAL_OPTION_SPECS[
                    potential_option
                ].value_range
                value: float = min(
                    max(field.number(), option_range.minimum),
                    option_range.maximum,
                )
                field.set_number(value)
                potential_lines[index] = PotentialLine(potential_option, value)

            item.potentials = tuple(potential_lines)

        else:
            additional_lines: list[AdditionalLine | None] = list(item.additionals)

            # 추가능력 미설정 또는 선택 라인 반영
            if label == "미설정":
                additional_lines[index] = None

            else:
                additional_option: AdditionalOption = _ADDITIONAL_LABEL_TO_OPTION[label]
                option_range: ValueRange = ADDITIONAL_OPTION_SPECS[
                    additional_option
                ].value_range
                value: float = min(
                    max(field.number(), option_range.minimum),
                    option_range.maximum,
                )
                field.set_number(value)
                additional_lines[index] = AdditionalLine(additional_option, value)

            item.additionals = tuple(additional_lines)

        self._changes.stats_changed()

    # 장비 교체 (선택) 화면

    def open_picker(self) -> None:
        """장비 교체 화면 열기"""

        self._picker_open = True
        self._show_detail()

    def close_picker(self) -> None:
        """장비 교체 화면 닫고 상세로 복귀"""

        self._picker_open = False
        self._show_detail()

    def _commit_owned_change(
        self,
        refresh_slots: bool = True,
        stats_changed: bool = True,
    ) -> None:
        """보유 목록·장착이 바뀐 뒤 슬롯 데이터를 다시 만들고 화면을 갱신"""

        # 장비 추가/삭제/장착/해제는 (반지처럼) 두 슬롯이 공유하는 보유 목록에
        # 영향을 줄 수 있으므로 전체 슬롯 데이터를 다시 구성한다.
        self._slots_data = self._build_slots_data(self._profile)
        if refresh_slots:
            self._refresh_slots()

        self._show_detail()
        if stats_changed:
            self._changes.stats_changed()

        else:
            self._changes.saved_value_changed()

    def select_owned(self, index: int) -> None:
        """선택한 장비를 슬롯에 장착하고 상세로 복귀"""

        slot: _EquipSlotData = self._slots_data[self._active_index]
        equipment: OwnedEquipment = slot.owned[index]
        equip_equipment(self._profile, slot.slot, equipment.name)
        self._picker_open = False
        self._commit_owned_change()

    def unequip(self) -> None:
        """슬롯 장착 해제 후 빈 상태로 복귀"""

        slot: _EquipSlotData = self._slots_data[self._active_index]
        unequip_equipment(self._profile, slot.slot)
        self._picker_open = False
        self._commit_owned_change()

    def add_owned(self) -> None:
        """새 기본 장비를 추가 (선택 화면 유지)"""

        slot: _EquipSlotData = self._slots_data[self._active_index]
        create_equipment(self._profile, self._default_equipment_for_slot(slot.slot))

        # 새 장비는 장착되지 않으므로 장착 타일은 그대로다
        self._commit_owned_change(refresh_slots=False, stats_changed=False)

    def remove_owned(self, index: int) -> None:
        """보유 장비 삭제"""

        slot: _EquipSlotData = self._slots_data[self._active_index]
        removed_item: OwnedEquipment = slot.owned[index]
        removed_name: str = removed_item.name
        was_equipped: bool = removed_name in self._profile.equipment.equipped.values()
        remaining_names: list[str] = [
            item.name
            for item_index, item in enumerate(slot.owned)
            if item_index != index and item.name not in slot.unavailable_names
        ]
        remove_equipment(self._profile, removed_name)
        if was_equipped and remaining_names:
            next_index: int = min(index, len(remaining_names) - 1)
            equip_equipment(self._profile, slot.slot, remaining_names[next_index])

        self._discard_equipment_views(removed_item)
        self._commit_owned_change(stats_changed=was_equipped)

    def _build_picker_page(self) -> QFrame:
        """장비 교체 고정 페이지 구성"""

        page: QFrame = QFrame(self._detail_stack)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(self._build_picker_head())

        self._picker_list = QVBoxLayout()
        self._picker_list.setContentsMargins(0, 4, 0, 0)
        self._picker_list.setSpacing(10)
        layout.addLayout(self._picker_list)
        layout.addStretch(1)
        return page

    def _sync_picker_list(self, slot: _EquipSlotData) -> None:
        """현재 슬롯 보유 장비 카드 목록 동기화"""

        while len(self._picker_cards) > len(slot.owned):
            card: _EquipPickCard = self._picker_cards.pop()
            self._picker_list.removeWidget(card)
            card.deleteLater()

        for index, item in enumerate(slot.owned):
            if index == len(self._picker_cards):
                card = _EquipPickCard(self._picker_page, self)
                self._picker_cards.append(card)
                self._picker_list.addWidget(card)

            self._picker_cards[index].update_from_slot(slot, item, index)

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

    def _build_empty_page(self) -> QFrame:
        """장착 장비가 없는 고정 페이지 구성"""

        page: QFrame = QFrame(self._detail_stack)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 12)
        head.setSpacing(12)

        icon: QLabel = _make_icon(page, 46, muted=True)
        head.addWidget(icon)

        name_box = QVBoxLayout()
        name_box.setSpacing(4)
        name_label: QLabel | None = None
        self._empty_title_label: QLabel = QLabel(page)
        self._empty_title_label.setObjectName("charMuted")
        self._empty_title_label.setFont(CustomFont(15, bold=True))
        sub_label: QLabel = QLabel("장착된 장비가 없습니다", page)
        sub_label.setObjectName("charSub")
        sub_label.setFont(CustomFont(9))
        name_box.addWidget(self._empty_title_label)
        name_box.addWidget(sub_label)
        head.addLayout(name_box)

        head.addStretch(1)
        select_btn: StyledButton = StyledButton(
            self, "장비 선택", kind="normal", point_size=9
        )
        select_btn.clicked.connect(self.open_picker)
        head.addWidget(select_btn)
        layout.addLayout(head)

        hint: QLabel = QLabel(
            "장비 교체로 보유 장비를 선택하거나 새 장비를 추가하세요.", page
        )
        hint.setObjectName("charEquipPickEmpty")
        hint.setFont(CustomFont(9))
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        layout.addStretch(1)
        return page

    def _default_equipment_for_slot(self, slot: EquipmentSlot) -> OwnedEquipment:
        """슬롯별 새 장비 기본 모델 생성"""

        if slot in (EquipmentSlot.RING1, EquipmentSlot.RING2):
            return OwnedEquipment(
                name=self._unique_equipment_name(slot),
                kind=EquipmentKind.RING,
            )

        if slot == EquipmentSlot.EARRING:
            return OwnedEquipment(
                name=self._unique_equipment_name(slot),
                kind=EquipmentKind.EARRING,
            )

        item_spec: EquipmentItemSpec = next(
            spec for spec in EQUIPMENT_ITEM_SPECS if slot in spec.slots
        )
        return OwnedEquipment(
            name=self._unique_equipment_name(slot),
            kind=EQUIPMENT_SLOT_KIND[slot],
            item_name=item_spec.name if slot == EquipmentSlot.NECKLACE else None,
            level=item_spec.level,
            tier=item_spec.tier,
            grade=(
                EquipmentGrade.BASIC
                if EquipmentGrade.BASIC in item_spec.grade_stats
                else None
            ),
        )

    def _unique_equipment_name(self, slot: EquipmentSlot) -> str:
        """슬롯 기준 새 장비 저장 이름 생성"""

        # 현재 캐릭터의 보유 장비 이름 수집
        existing_names: set[str] = {
            equipment.name for equipment in self._profile.equipment.owned
        }
        base_name: str = f"새 {EQUIPMENT_SLOT_LABELS[slot]}"
        suffix: int = 1

        # 중복되지 않는 가장 작은 자연수 선택
        while f"{base_name} {suffix}" in existing_names:
            suffix += 1

        return f"{base_name} {suffix}"
