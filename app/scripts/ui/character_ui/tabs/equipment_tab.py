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

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
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

from app.scripts.calculator_models import STAT_SPECS, StatKey
from app.scripts.character_data import (
    ADDITIONAL_OPTION_SPECS,
    ARMOR_SLOT_STAT_KEYS,
    EQUIPMENT_ITEM_SPECS,
    EQUIPMENT_REFORGE_STAT_KEYS,
    EQUIPMENT_SCROLL_EFFECTS,
    FREE_BASE_STAT_EQUIPMENT_SLOTS,
    NECKLACE_REFORGE_STAT_KEYS,
    POTENTIAL_EQUIPMENT_SLOTS,
    POTENTIAL_OPTION_SPECS,
    EquipmentItemSpec,
    OptionSpec,
)
from app.scripts.character_engine import (
    create_equipment,
    equip_equipment,
    list_equippable_equipment,
    remove_equipment,
    rename_equipment,
    unequip_equipment,
)
from app.scripts.character_models import (
    MAX_REFORGE_STEP,
    AdditionalLine,
    AdditionalOption,
    CharacterProfile,
    EquipmentFreeStatLine,
    EquipmentGrade,
    EquipmentKind,
    EquipmentSlot,
    OwnedEquipment,
    PotentialLine,
    PotentialOption,
    ScrollTier,
)
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.constants import EQUIPMENT_SLOT_LABELS
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
_STACK_THRESHOLD: int = 550

_SLOT_ORDER: tuple[EquipmentSlot, ...] = (
    EquipmentSlot.WEAPON,
    EquipmentSlot.HELMET,
    EquipmentSlot.ARMOR,
    EquipmentSlot.BELT,
    EquipmentSlot.SHOES,
    EquipmentSlot.RING1,
    EquipmentSlot.RING2,
    EquipmentSlot.NECKLACE,
    EquipmentSlot.EARRING,
)
_EQUIP_COL_LEFT: tuple[int, ...] = (0, 1, 2, 3, 4)
_EQUIP_COL_RIGHT: tuple[int, ...] = (5, 6, 7, 8)
_GRADE_TYPES: tuple[str, ...] = ("무기", "투구", "갑옷", "허리띠", "신발")
_POTENTIAL_TYPES: tuple[str, ...] = ("투구", "갑옷", "허리띠", "신발")
_NECKLACE_TYPES: tuple[str, ...] = tuple(NECKLACE_REFORGE_STAT_KEYS.keys())
# 방어구는 카탈로그 이름 뒤에 부위 접미사를 붙여 표시한다 (예: 적령 → 적령투구·적령대)
_ARMOR_SLOT_NAME_SUFFIX: dict[EquipmentSlot, str] = {
    EquipmentSlot.HELMET: "투구",
    EquipmentSlot.ARMOR: "갑옷",
    EquipmentSlot.BELT: "대",
    EquipmentSlot.SHOES: "신",
}
_EQUIP_LEVELS: tuple[int, ...] = (0, 20, 50, 80, 110, 150, 180)
_EQUIP_TIERS: tuple[int, ...] = (1, 2, 3, 4, 5)
_TITLE_STATS: tuple[str, ...] = (
    "미설정",
    "공격력",
    "공격력(%)",
    "체력",
    "체력(%)",
    "힘",
    "힘(%)",
    "민첩",
    "민첩(%)",
    "생명력",
    "생명력(%)",
    "행운",
    "행운(%)",
    "스킬 피해량(%)",
    "최종 공격력(%)",
    "치명타 확률(%)",
    "치명타 공격력%",
    "경험치 획득량(%)",
    "보스 공격력(%)",
    "드랍률(%)",
    "회피(%)",
    "물약 회복량(%)",
    "저항(%)",
    "스킬속도(%)",
)
_STAT_LABEL_TO_KEY: dict[str, StatKey] = {
    **{label: stat_key for stat_key, label in STAT_SPECS.items()},
    "힘%": StatKey.STR_PERCENT,
    "민첩%": StatKey.DEXTERITY_PERCENT,
    "생명력%": StatKey.VITALITY_PERCENT,
    "행운%": StatKey.LUCK_PERCENT,
    "공격력%": StatKey.ATTACK_PERCENT,
    "체력%": StatKey.HP_PERCENT,
    "경험치%": StatKey.EXP_PERCENT,
    "저항%": StatKey.RESIST_PERCENT,
    "스킬속도%": StatKey.SKILL_SPEED_PERCENT,
    "최종 공격력%": StatKey.FINAL_ATTACK_PERCENT,
    "치명타 공격력%": StatKey.CRIT_DAMAGE_PERCENT,
    "치명타 확률%": StatKey.CRIT_RATE_PERCENT,
    "보스 공격력%": StatKey.BOSS_ATTACK_PERCENT,
    "드랍률%": StatKey.DROP_RATE_PERCENT,
    "물약 회복량%": StatKey.POTION_HEAL_PERCENT,
}
_STAT_KEY_TO_LABEL: dict[StatKey, str] = {
    stat_key: label for label, stat_key in _STAT_LABEL_TO_KEY.items()
}
_TITLE_STAT_KEY_TO_LABEL: dict[StatKey, str] = {
    stat_key: label for stat_key, label in STAT_SPECS.items()
}
_TITLE_STAT_KEY_TO_LABEL[StatKey.CRIT_DAMAGE_PERCENT] = "치명타 공격력%"
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
        f"{_STAT_KEY_TO_LABEL[spec.stat_key]} "
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


@dataclass(slots=True)
class _EquipItemData:
    """보유 장비 모델 UI 어댑터"""

    equipment: OwnedEquipment
    slot: EquipmentSlot

    @property
    def name(self) -> str:
        """상세 헤더 표시 장비명"""

        item_spec: EquipmentItemSpec | None = self.item_spec()
        if item_spec is not None:
            return item_spec.name + _ARMOR_SLOT_NAME_SUFFIX.get(self.slot, "")

        return self.equipment.name

    @name.setter
    def name(self, value: str) -> None:
        """보유 장비 식별 이름 반영"""

        self.equipment.name = value

    @property
    def level(self) -> int:
        """장비 레벨"""

        return self.equipment.level

    @level.setter
    def level(self, value: int) -> None:
        """장비 레벨 반영"""

        self.equipment.level = value

    @property
    def grade(self) -> str:
        """장비 등급 표시값"""

        if self.equipment.grade == EquipmentGrade.RADIANT:
            return "찬란한"

        return "기본"

    @grade.setter
    def grade(self, value: str) -> None:
        """장비 등급 반영"""

        self.equipment.grade = (
            EquipmentGrade.RADIANT if value == "찬란한" else EquipmentGrade.BASIC
        )

    @property
    def tier(self) -> int:
        """장비 티어"""

        return self.equipment.tier

    @tier.setter
    def tier(self, value: int) -> None:
        """장비 티어 반영"""

        self.equipment.tier = value

    @property
    def base(self) -> list[tuple[str, float]]:
        """기본 스탯 표시값"""

        item_spec: EquipmentItemSpec | None = self.item_spec()
        if item_spec is None:
            return []

        values: dict[StatKey, float] = dict(item_spec.grade_stats[self.equipment.grade])
        if self.slot in ARMOR_SLOT_STAT_KEYS:
            if self.equipment.grade is None:
                raise ValueError("armor equipment grade is required")

            values[ARMOR_SLOT_STAT_KEYS[self.slot]] = item_spec.armor_stat_values[
                self.equipment.grade
            ]

        return [
            (_STAT_KEY_TO_LABEL[stat_key], value) for stat_key, value in values.items()
        ]

    @property
    def free_base(self) -> list[tuple[str | None, str]]:
        """자유 기본 스탯 표시값"""

        return [
            (_TITLE_STAT_KEY_TO_LABEL[line.stat_key], f"{line.value:g}")
            for line in self.equipment.base_stat_lines
        ]

    @property
    def necklace_type(self) -> str | None:
        """목걸이 종류"""

        return self.equipment.item_name

    @property
    def reforge_step(self) -> int:
        """재련 단계(강)"""

        return self.equipment.reforge_step

    @reforge_step.setter
    def reforge_step(self, value: int) -> None:
        """재련 단계 반영"""

        self.equipment.reforge_step = value

    @property
    def scroll_stat(self) -> list[str]:
        """주문서 요약 표시값"""

        tokens: list[str] = []
        for stat_key, tier_counts in self.equipment.scrolls.items():
            total_count: int = sum(tier_counts.values())
            if total_count <= 0:
                continue

            tokens.append(f"{_STAT_KEY_TO_LABEL[stat_key]} {total_count:g}")

        return tokens

    @property
    def potential(self) -> list[str]:
        """잠재능력 요약 표시값"""

        return [
            f"{_POTENTIAL_OPTION_TO_LABEL[line.option].split(' ')[0]} {line.value:g}"
            for line in self.equipment.potentials
            if line is not None
        ]

    @property
    def additional(self) -> list[str]:
        """추가능력 요약 표시값"""

        return [
            f"{_ADDITIONAL_OPTION_TO_LABEL[line.option].split(' ')[0]} {line.value:g}"
            for line in self.equipment.additionals
            if line is not None
        ]

    def item_spec(self) -> EquipmentItemSpec | None:
        """장비 정적 스펙 조회"""

        if self.equipment.kind in (EquipmentKind.RING, EquipmentKind.EARRING):
            return None

        for item_spec in EQUIPMENT_ITEM_SPECS:
            if self.equipment.kind == EquipmentKind.NECKLACE:
                if item_spec.name == self.equipment.item_name:
                    return item_spec

                continue

            if (
                item_spec.level == self.equipment.level
                and item_spec.tier == self.equipment.tier
                and self.slot in item_spec.slots
            ):
                return item_spec

        raise ValueError("equipment item spec does not exist")


@dataclass(slots=True)
class _EquipSlotData:
    """장비 슬롯 UI 데이터"""

    slot: EquipmentSlot
    profile: CharacterProfile | None
    type: str
    scroll: EquipmentSlot | None
    reforge: bool
    owned: list[_EquipItemData]
    equipped_index: int

    def equipped(self) -> _EquipItemData | None:
        """현재 장착 장비"""

        if self.equipped_index == -1:
            return None

        return self.owned[self.equipped_index]


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

    def update_from_slot(self, slot: _EquipSlotData) -> None:
        """슬롯 상태(장착 장비/빈 상태)에 맞춰 표시 갱신"""

        item = slot.equipped()
        empty: bool = item is None
        self._icon.setStyleSheet(_ICON_STYLE_MUTED if empty else _ICON_STYLE)
        if empty:
            self._type_label.setText(slot.type)
            self._meta_label.setText("비어 있음")
        else:
            self._type_label.setText(item.name)
            self._meta_label.setText(slot.type)
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
        slot: _EquipSlotData,
        item: _EquipItemData,
        index: int,
        tab: "EquipmentTab",
        has_grade: bool,
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

        del_btn: StyledButton = StyledButton(self, "삭제", kind="danger", point_size=9)
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

    def __init__(self, parent: QWidget, on_changed: Callable[[], None]) -> None:
        super().__init__(parent)

        self._profile: CharacterProfile | None = None
        self._on_changed: Callable[[], None] = on_changed
        self._slots_data: list[_EquipSlotData] = self._build_slots_data(None)
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

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        self._profile = profile
        self._slots_data = self._build_slots_data(profile)
        self.setEnabled(profile is not None)
        self._refresh_slots()
        self._render_detail()

    def _build_slots_data(
        self,
        profile: CharacterProfile | None,
    ) -> list[_EquipSlotData]:
        """실제 장비 모델 기준 슬롯 데이터 구성"""

        slots_data: list[_EquipSlotData] = []
        for slot in _SLOT_ORDER:
            if profile is None:
                slots_data.append(
                    _EquipSlotData(
                        slot=slot,
                        profile=None,
                        type=EQUIPMENT_SLOT_LABELS[slot],
                        scroll=slot if slot in _SCROLL_SETS else None,
                        reforge=slot in self._reforge_slots(),
                        owned=[],
                        equipped_index=-1,
                    )
                )
                continue

            owned: list[_EquipItemData] = [
                _EquipItemData(equipment=equipment, slot=slot)
                for equipment in list_equippable_equipment(profile, slot)
            ]
            equipped_name: str | None = profile.equipment.equipped[slot]
            equipped_index: int = -1
            for index, item in enumerate(owned):
                if item.equipment.name != equipped_name:
                    continue

                equipped_index = index
                break

            slots_data.append(
                _EquipSlotData(
                    slot=slot,
                    profile=profile,
                    type=EQUIPMENT_SLOT_LABELS[slot],
                    scroll=slot if slot in _SCROLL_SETS else None,
                    reforge=slot in self._reforge_slots(),
                    owned=owned,
                    equipped_index=equipped_index,
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
        slot: _EquipSlotData = self._slots_data[self._active_index]

        if self._picker_open:
            self._render_picker(slot)
            return

        item = slot.equipped()
        if item is None:
            self._render_empty(slot)
            return

        has_grade: bool = slot.type in _GRADE_TYPES
        has_potential: bool = slot.type in _POTENTIAL_TYPES
        is_necklace: bool = slot.slot == EquipmentSlot.NECKLACE
        is_free_stat: bool = item.equipment.kind in (
            EquipmentKind.RING,
            EquipmentKind.EARRING,
        )

        self._detail_layout.addLayout(self._build_detail_head(slot, item, has_grade))

        # 아이템 섹션: 무기·방어구(레벨/티어/등급) 또는 목걸이(종류). 반지·귀걸이는 표시하지 않는다
        if not is_free_stat:
            self._detail_layout.addWidget(
                self._build_item_section(slot, item, has_grade)
            )

        # 기본 스탯 + 재련: 공간이 남으면 기본 스탯 오른쪽에 재련을 나란히 배치
        base_group: ResponsiveColumnsBox = ResponsiveColumnsBox(
            self._detail_content, min_column_width=300, spacing=18
        )
        # 목걸이는 기본 스탯 없이 재련만 입력한다
        if not is_necklace:
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
                self._build_option_section("잠재능력", _POTENTIAL_OPTIONS)
            )
            option_group.addWidget(
                self._build_option_section("추가능력", _ADDITIONAL_OPTIONS)
            )
            self._detail_layout.addWidget(option_group)

        self._detail_layout.addStretch(1)

    def _build_detail_head(
        self,
        slot: _EquipSlotData,
        item: _EquipItemData,
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
        # 반지·귀걸이는 사용자가 직접 이름을 정한다 (그 외 부위는 카탈로그/종류 이름 표시)
        if item.equipment.kind in (EquipmentKind.RING, EquipmentKind.EARRING):
            name_edit: QLineEdit = QLineEdit(item.name, self)
            name_edit.setObjectName("charTitleName")
            name_edit.setFont(CustomFont(15, bold=True))
            name_edit.editingFinished.connect(
                lambda field=name_edit, target=item: self._rename_current(field, target)
            )
            name_box.addWidget(name_edit)
        else:
            display_name: str = (
                "찬란한 " if has_grade and item.grade == "찬란한" else ""
            ) + item.name
            name_label: QLabel = QLabel(display_name, self)
            name_label.setObjectName("charDetailName")
            name_label.setFont(CustomFont(15, bold=True))
            name_box.addWidget(name_label)
        meta_label: QLabel = QLabel(slot.type, self)
        meta_label.setObjectName("charSub")
        meta_label.setFont(CustomFont(9))
        name_box.addWidget(meta_label)
        head.addLayout(name_box)

        head.addStretch(1)
        change_btn: StyledButton = StyledButton(
            self, "장비 교체", kind="normal", point_size=9
        )
        change_btn.clicked.connect(self.open_picker)
        head.addWidget(change_btn)
        return head

    def _build_level_tier_row(self, item: _EquipItemData) -> QHBoxLayout:
        """레벨/티어 콤보박스 선택 행"""

        controls = QHBoxLayout()
        controls.setSpacing(8)

        level_caption: QLabel = QLabel("레벨", self)
        level_caption.setObjectName("charFieldLabel")
        level_caption.setFont(CustomFont(9, bold=True))
        controls.addWidget(level_caption)
        level_combo: CharComboBox = CharComboBox(
            self, [str(level) for level in _EQUIP_LEVELS], point_size=9
        )
        if item.level in _EQUIP_LEVELS:
            level_combo.setCurrentIndex(_EQUIP_LEVELS.index(item.level))
        level_combo.currentTextChanged.connect(self._pick_level)
        controls.addWidget(level_combo)

        controls.addSpacing(8)

        tier_caption: QLabel = QLabel("티어", self)
        tier_caption.setObjectName("charFieldLabel")
        tier_caption.setFont(CustomFont(9, bold=True))
        controls.addWidget(tier_caption)
        tier_combo: CharComboBox = CharComboBox(
            self, [str(tier) for tier in _EQUIP_TIERS], point_size=9
        )
        if item.tier in _EQUIP_TIERS:
            tier_combo.setCurrentIndex(_EQUIP_TIERS.index(item.tier))
        tier_combo.currentTextChanged.connect(self._pick_tier)
        controls.addWidget(tier_combo)

        controls.addStretch(1)
        return controls

    def _build_necklace_type_row(self, item: _EquipItemData) -> QHBoxLayout:
        """목걸이 종류 선택 행"""

        controls = QHBoxLayout()
        controls.setSpacing(8)

        caption: QLabel = QLabel("종류", self)
        caption.setObjectName("charFieldLabel")
        caption.setFont(CustomFont(9, bold=True))
        controls.addWidget(caption)

        type_combo: CharComboBox = CharComboBox(
            self, list(_NECKLACE_TYPES), point_size=9
        )
        if item.necklace_type in _NECKLACE_TYPES:
            type_combo.setCurrentIndex(_NECKLACE_TYPES.index(item.necklace_type))
        type_combo.currentTextChanged.connect(self._pick_necklace_type)
        controls.addWidget(type_combo)

        controls.addStretch(1)
        return controls

    def _current_item(self) -> _EquipItemData | None:
        """현재 슬롯의 장착 장비"""

        return self._slots_data[self._active_index].equipped()

    def _pick_level(self, text: str) -> None:
        """선택한 장비 레벨을 현재 장비에 반영"""

        item = self._current_item()
        if item is not None:
            item.level = int(text)
            self._refresh_active_slot()
            self._render_detail()
            self._on_changed()

    def _pick_tier(self, text: str) -> None:
        """선택한 장비 티어를 현재 장비에 반영"""

        item = self._current_item()
        if item is not None:
            item.tier = int(text)
            self._render_detail()
            self._on_changed()

    def _rename_current(self, field: QLineEdit, item: _EquipItemData) -> None:
        """반지·귀걸이 이름 변경 (장착 참조·유일성 유지)"""

        if self._profile is None:
            return

        old_name: str = item.equipment.name
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

        self._slots_data = self._build_slots_data(self._profile)
        self._refresh_active_slot()
        self._on_changed()

    def _pick_necklace_type(self, text: str) -> None:
        """목걸이 종류 변경 (종류별 허용 재련 스탯으로 정리)"""

        item = self._current_item()
        if item is None:
            return

        item.equipment.item_name = text
        allowed_keys: tuple[StatKey, ...] = NECKLACE_REFORGE_STAT_KEYS[text]
        item.equipment.reforge_stats = {
            stat_key: value
            for stat_key, value in item.equipment.reforge_stats.items()
            if stat_key in allowed_keys
        }
        self._slots_data = self._build_slots_data(self._profile)
        self._refresh_active_slot()
        self._render_detail()
        self._on_changed()

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
        item: _EquipItemData,
        has_grade: bool,
    ) -> QFrame:
        """아이템 섹션 (레벨/티어 + 등급)"""

        section, box = self._section("아이템")

        # 목걸이는 레벨·티어 대신 종류를 선택한다
        if slot.slot == EquipmentSlot.NECKLACE:
            box.addLayout(self._build_necklace_type_row(item))
            return section

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

    def _build_grade_row(self, item: _EquipItemData) -> QHBoxLayout:
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
        self._on_changed()

    def _build_base_section(self, slot: _EquipSlotData, item: _EquipItemData) -> QFrame:
        """기본 스탯 섹션 (방어구/무기 자동 표시 vs 반지/귀걸이 자유 입력)"""

        section, box = self._section("기본 스탯")

        # 반지/귀걸이: 자유 스탯 라인
        if not item.base:
            self._free_rows = QVBoxLayout()
            self._free_rows.setSpacing(8)
            for index, (stat, value) in enumerate(item.free_base):
                self._free_rows.addLayout(
                    self._build_free_stat_row(item, index, stat, value)
                )
            box.addLayout(self._free_rows)

            add_btn: StyledButton = StyledButton(
                section, "+ 스탯 추가", kind="normal", point_size=9
            )
            add_btn.clicked.connect(lambda: self._add_free_stat(item))
            box.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)
            return section

        # 무기·방어구: 자동 제공되는 읽기 전용 스탯 / 그 외(목걸이 등): 직접 입력
        auto_provided: bool = slot.type in _GRADE_TYPES

        flow: FlowLayout = FlowLayout(spacing=14)
        for label_text, value in item.base:
            flow.addWidget(
                self._build_labeled_field(
                    label_text, str(value), readonly=auto_provided
                )
            )
        box.addLayout(flow)
        return section

    def _build_free_stat_row(
        self,
        item: _EquipItemData,
        index: int,
        stat: str | None,
        value: str,
    ) -> QHBoxLayout:
        """반지/귀걸이 자유 스탯 한 줄 (콤보 + 값)"""

        row = QHBoxLayout()
        row.setSpacing(10)
        combo: CharComboBox = CharComboBox(self, list(_TITLE_STATS))
        if stat and stat in _TITLE_STATS:
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

    def _add_free_stat(self, item: _EquipItemData) -> None:
        """자유 스탯 라인 추가"""

        item.equipment.base_stat_lines.append(
            EquipmentFreeStatLine(stat_key=StatKey.ATTACK, value=0.0)
        )
        self._render_detail()
        self._on_changed()

    def _set_free_stat_line(
        self,
        item: _EquipItemData,
        index: int,
        stat: str,
        value: float,
    ) -> None:
        """자유 기본 스탯 라인 모델 반영"""

        if stat == "미설정":
            return

        item.equipment.base_stat_lines[index] = EquipmentFreeStatLine(
            stat_key=_STAT_LABEL_TO_KEY[stat],
            value=value,
        )
        self._on_changed()

    def _build_reforge_section(
        self, slot: _EquipSlotData, item: _EquipItemData
    ) -> QFrame:
        """재련 섹션 (부위/목걸이 종류별 허용 스탯 입력)"""

        section, box = self._section("재련")

        stat_keys: tuple[StatKey, ...] = _reforge_stat_keys(
            slot.slot, item.necklace_type
        )

        flow: FlowLayout = FlowLayout(spacing=14)
        # 맨 처음에 재련 단계(0~20강) 입력칸
        flow.addWidget(self._build_step_field(item))
        for stat_key in stat_keys:
            label: str = _STAT_KEY_TO_LABEL[stat_key]
            value: float = item.equipment.reforge_stats.get(stat_key, 0.0)
            flow.addWidget(
                self._build_labeled_field(
                    label,
                    f"{value:g}",
                    on_changed=lambda field, key=stat_key, target=item: self._set_reforge_stat(
                        target,
                        key,
                        field.number(),
                    ),
                )
            )
        box.addLayout(flow)
        return section

    def _build_step_field(self, item: _EquipItemData) -> QWidget:
        """재련 단계(0~20강) 입력 묶음"""

        container: QFrame = QFrame(self)
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        name_label: QLabel = QLabel("단계", container)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        box.addWidget(name_label)

        field: StepperField = StepperField(container, str(item.reforge_step), unit="강")
        field.setFixedWidth(84)
        field.input.setValidator(QIntValidator(0, MAX_REFORGE_STEP, field))
        field.value_changed.connect(
            lambda target=item, value_field=field: self._set_reforge_step(
                target,
                value_field,
            )
        )
        box.addWidget(field)
        return container

    def _set_reforge_step(self, item: _EquipItemData, field: StepperField) -> None:
        """재련 단계 모델 반영"""

        item.reforge_step = int(field.number())
        self._on_changed()

    def _build_scroll_section(self, slot: _EquipSlotData) -> QFrame:
        """주문서 섹션 (행=종류, 열=% 단계, 칸=성공 횟수)"""

        section, box = self._section("주문서")

        if slot.scroll is None:
            raise ValueError("scroll slot is required")

        item: _EquipItemData | None = slot.equipped()
        if item is None:
            raise ValueError("equipped item is required")

        scroll_set: _ScrollSet = _SCROLL_SETS[slot.scroll]

        wrap: QScrollArea = QScrollArea(section)
        wrap.setObjectName("charScrollTableWrap")
        wrap.setWidgetResizable(True)
        wrap.setFixedHeight(40 + len(scroll_set.stat_keys) * 38)
        wrap.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        table: QFrame = QFrame()
        table.setObjectName("charScrollTable")
        grid = QGridLayout(table)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        slot_effects: dict[StatKey, dict[ScrollTier, dict[StatKey, float]]] = (
            EQUIPMENT_SCROLL_EFFECTS[slot.scroll]
        )

        # 머리글
        head_label: QLabel = QLabel("주문서", table)
        head_label.setObjectName("charScrollHead")
        head_label.setFont(CustomFont(9, bold=True))
        grid.addWidget(head_label, 0, 0)
        for col, tier in enumerate(scroll_set.tiers):
            tier_label: QLabel = QLabel(_SCROLL_TIER_LABELS[tier], table)
            tier_label.setObjectName("charScrollHead")
            tier_label.setFont(CustomFont(9, bold=True))
            tier_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(tier_label, 0, col + 2)

        # 본문
        for row, stat_key in enumerate(scroll_set.stat_keys):
            stat_label: QLabel = QLabel(_STAT_KEY_TO_LABEL[stat_key], table)
            stat_label.setObjectName("charScrollStat")
            stat_label.setFont(CustomFont(9, bold=True))
            grid.addWidget(stat_label, row + 1, 0)
            for col, tier in enumerate(scroll_set.tiers):
                # 해당 스탯이 지원하지 않는 단계는 입력칸을 두지 않는다
                if tier not in slot_effects[stat_key]:
                    dash: QLabel = QLabel("—", table)
                    dash.setObjectName("charMuted")
                    dash.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    grid.addWidget(dash, row + 1, col + 2)
                else:
                    count: int = item.equipment.scrolls.get(stat_key, {}).get(
                        tier,
                        0,
                    )
                    cell: QLineEdit = QLineEdit(str(count), table)
                    cell.setObjectName("charMiniNum")
                    cell.setFont(CustomFont(9))
                    cell.setFixedWidth(30)
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setValidator(QIntValidator(0, 999, cell))
                    cell.textChanged.connect(
                        lambda text, target=item, key=stat_key, scroll_key=tier: self._set_scroll_count(
                            target,
                            key,
                            scroll_key,
                            text,
                        )
                    )
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
        item: _EquipItemData | None = self._current_item()
        if item is None:
            raise ValueError("equipped item is required")

        for index in range(3):
            row = QHBoxLayout()
            row.setSpacing(10)
            combo: CharComboBox = CharComboBox(section, ["미설정", *options])
            # 입력칸은 고정 폭으로 두어 창 크기에 따라 늘어나지 않게 한다
            field: StepperField = StepperField(section, "0")
            field.setFixedWidth(100)
            if title == "잠재능력":
                line: PotentialLine | None = item.equipment.potentials[index]
                if line is not None:
                    combo.setCurrentText(_POTENTIAL_OPTION_TO_LABEL[line.option])
                    field.set_number(line.value)

                combo.currentTextChanged.connect(
                    lambda text, target=item, line_index=index, value_field=field: self._set_potential_line(
                        target,
                        line_index,
                        text,
                        value_field,
                        sync_field=True,
                    )
                )
                field.value_changed.connect(
                    lambda target=item, line_index=index, option_combo=combo, value_field=field: self._set_potential_line(
                        target,
                        line_index,
                        option_combo.currentText(),
                        value_field,
                        sync_field=False,
                    )
                )
                field.input.editingFinished.connect(
                    lambda target=item, line_index=index, option_combo=combo, value_field=field: self._set_potential_line(
                        target,
                        line_index,
                        option_combo.currentText(),
                        value_field,
                        sync_field=True,
                    )
                )
            else:
                additional_line: AdditionalLine | None = item.equipment.additionals[
                    index
                ]
                if additional_line is not None:
                    combo.setCurrentText(
                        _ADDITIONAL_OPTION_TO_LABEL[additional_line.option]
                    )
                    field.set_number(additional_line.value)

                combo.currentTextChanged.connect(
                    lambda text, target=item, line_index=index, value_field=field: self._set_additional_line(
                        target,
                        line_index,
                        text,
                        value_field,
                        sync_field=True,
                    )
                )
                field.value_changed.connect(
                    lambda target=item, line_index=index, option_combo=combo, value_field=field: self._set_additional_line(
                        target,
                        line_index,
                        option_combo.currentText(),
                        value_field,
                        sync_field=False,
                    )
                )
                field.input.editingFinished.connect(
                    lambda target=item, line_index=index, option_combo=combo, value_field=field: self._set_additional_line(
                        target,
                        line_index,
                        option_combo.currentText(),
                        value_field,
                        sync_field=True,
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
        if isinstance(field, StepperField) and on_changed is not None:
            field.value_changed.connect(lambda target=field: on_changed(target))

        field.setFixedWidth(84)
        box.addWidget(field)
        return container

    def _set_reforge_stat(
        self,
        item: _EquipItemData,
        stat_key: StatKey,
        value: float,
    ) -> None:
        """재련 스탯 모델 반영"""

        if value <= 0.0:
            item.equipment.reforge_stats.pop(stat_key, None)
        else:
            item.equipment.reforge_stats[stat_key] = value

        self._on_changed()

    def _set_scroll_count(
        self,
        item: _EquipItemData,
        stat_key: StatKey,
        tier: ScrollTier,
        text: str,
    ) -> None:
        """주문서 성공 횟수 모델 반영"""

        count: int = 0 if not text.strip() else int(text)
        tier_counts: dict[ScrollTier, int] = item.equipment.scrolls.setdefault(
            stat_key,
            {},
        )
        if count <= 0:
            tier_counts.pop(tier, None)
        else:
            tier_counts[tier] = count

        if not tier_counts:
            item.equipment.scrolls.pop(stat_key, None)

        self._on_changed()

    def _set_potential_line(
        self,
        item: _EquipItemData,
        index: int,
        label: str,
        field: StepperField,
        sync_field: bool,
    ) -> None:
        """잠재능력 라인 모델 반영

        입력 도중에는 칸을 건드리지 않아 자유롭게 지우고 다시 칠 수 있게 하고,
        모델에는 허용 범위로 보정한 값만 저장한다. 종류 변경·입력 확정(sync_field)
        시에만 칸 표시를 보정 값으로 맞춘다.
        """

        lines: list[PotentialLine | None] = list(item.equipment.potentials)
        if label == "미설정":
            lines[index] = None
            item.equipment.potentials = tuple(lines)
            self._on_changed()
            return

        option: PotentialOption = _POTENTIAL_LABEL_TO_OPTION[label]
        option_range = POTENTIAL_OPTION_SPECS[option].value_range
        value: float = min(
            max(field.number(), option_range.minimum),
            option_range.maximum,
        )
        if sync_field:
            field.set_number(value)

        lines[index] = PotentialLine(option=option, value=value)
        item.equipment.potentials = tuple(lines)
        self._on_changed()

    def _set_additional_line(
        self,
        item: _EquipItemData,
        index: int,
        label: str,
        field: StepperField,
        sync_field: bool,
    ) -> None:
        """추가능력 라인 모델 반영

        입력 도중에는 칸을 건드리지 않아 자유롭게 지우고 다시 칠 수 있게 하고,
        모델에는 허용 범위로 보정한 값만 저장한다. 종류 변경·입력 확정(sync_field)
        시에만 칸 표시를 보정 값으로 맞춘다.
        """

        lines: list[AdditionalLine | None] = list(item.equipment.additionals)
        if label == "미설정":
            lines[index] = None
            item.equipment.additionals = tuple(lines)
            self._on_changed()
            return

        option: AdditionalOption = _ADDITIONAL_LABEL_TO_OPTION[label]
        option_range = ADDITIONAL_OPTION_SPECS[option].value_range
        value: float = min(
            max(field.number(), option_range.minimum),
            option_range.maximum,
        )
        if sync_field:
            field.set_number(value)

        lines[index] = AdditionalLine(option=option, value=value)
        item.equipment.additionals = tuple(lines)
        self._on_changed()

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

        if self._profile is None:
            return

        slot: _EquipSlotData = self._slots_data[self._active_index]
        equipment: _EquipItemData = slot.owned[index]
        equip_equipment(self._profile, slot.slot, equipment.equipment.name)
        self._slots_data = self._build_slots_data(self._profile)
        self._picker_open = False
        self._refresh_active_slot()
        self._render_detail()
        self._on_changed()

    def unequip(self) -> None:
        """슬롯 장착 해제 후 빈 상태로 복귀"""

        if self._profile is None:
            return

        slot: _EquipSlotData = self._slots_data[self._active_index]
        unequip_equipment(self._profile, slot.slot)
        self._slots_data = self._build_slots_data(self._profile)
        self._picker_open = False
        self._refresh_active_slot()
        self._render_detail()
        self._on_changed()

    def add_owned(self) -> None:
        """새 기본 장비를 추가 (선택 화면 유지)"""

        if self._profile is None:
            return

        slot: _EquipSlotData = self._slots_data[self._active_index]
        create_equipment(self._profile, self._default_equipment_for_slot(slot.slot))

        self._slots_data = self._build_slots_data(self._profile)
        self._render_detail()
        self._on_changed()

    def remove_owned(self, index: int) -> None:
        """보유 장비 삭제"""

        if self._profile is None:
            return

        slot: _EquipSlotData = self._slots_data[self._active_index]
        removed_name: str = slot.owned[index].equipment.name
        was_equipped: bool = slot.equipped_index == index
        remaining_names: list[str] = [
            item.equipment.name
            for item_index, item in enumerate(slot.owned)
            if item_index != index
        ]
        remove_equipment(self._profile, removed_name)
        if was_equipped and remaining_names:
            next_index: int = min(index, len(remaining_names) - 1)
            equip_equipment(self._profile, slot.slot, remaining_names[next_index])

        self._slots_data = self._build_slots_data(self._profile)
        self._refresh_active_slot()
        self._render_detail()
        self._on_changed()

    def _render_picker(self, slot: _EquipSlotData) -> None:
        """장비 교체 화면 구성 (보유 장비 카드 목록)"""

        self._detail_layout.addLayout(self._build_picker_head())

        has_grade: bool = slot.type in _GRADE_TYPES
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

    def _render_empty(self, slot: _EquipSlotData) -> None:
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

    def _reforge_slots(self) -> tuple[EquipmentSlot, ...]:
        """재련 섹션 표시 슬롯 목록"""

        return (
            EquipmentSlot.HELMET,
            EquipmentSlot.ARMOR,
            EquipmentSlot.BELT,
            EquipmentSlot.SHOES,
            EquipmentSlot.WEAPON,
            EquipmentSlot.NECKLACE,
        )

    def _default_equipment_for_slot(self, slot: EquipmentSlot) -> OwnedEquipment:
        """슬롯별 새 장비 기본 모델 생성"""

        if slot in (EquipmentSlot.RING1, EquipmentSlot.RING2):
            return OwnedEquipment(
                name=self._unique_equipment_name("새 반지"),
                kind=EquipmentKind.RING,
            )

        if slot == EquipmentSlot.EARRING:
            return OwnedEquipment(
                name=self._unique_equipment_name("새 귀걸이"),
                kind=EquipmentKind.EARRING,
            )

        item_spec: EquipmentItemSpec = next(
            spec for spec in EQUIPMENT_ITEM_SPECS if slot in spec.slots
        )
        return OwnedEquipment(
            name=self._unique_equipment_name(item_spec.name),
            kind=EquipmentKind(slot.value),
            item_name=item_spec.name if slot == EquipmentSlot.NECKLACE else None,
            level=item_spec.level,
            tier=item_spec.tier,
            grade=(
                EquipmentGrade.BASIC
                if EquipmentGrade.BASIC in item_spec.grade_stats
                else None
            ),
        )

    def _unique_equipment_name(self, base_name: str) -> str:
        """캐릭터 내부 유일 장비명 생성"""

        if self._profile is None:
            return base_name

        existing_names: set[str] = {
            equipment.name for equipment in self._profile.equipment.owned
        }
        if base_name not in existing_names:
            return base_name

        suffix: int = 2
        while f"{base_name} {suffix}" in existing_names:
            suffix += 1

        return f"{base_name} {suffix}"
