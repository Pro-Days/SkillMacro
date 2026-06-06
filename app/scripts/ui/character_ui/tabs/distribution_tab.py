"""스탯·단전 분배 탭"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import REALM_TIER_SPECS
from app.scripts.character_engine import optimize_danjeon, optimize_stat_distribution
from app.scripts.character_models import CharacterProfile
from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui.constants import (
    DANJEON_DISTRIBUTION_ITEMS,
    STAT_DISTRIBUTION_ITEMS,
)
from app.scripts.ui.character_ui.edit_session import CharacterEditSession
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    ResponsiveColumnsBox,
    StepperField,
)

_ITEM_FIELD_WIDTH: int = 84


class _Budget(QFrame):
    """분배 가능/사용/남은 + 진행바 요약 위젯"""

    def __init__(self, parent: QWidget, total_label: str) -> None:
        super().__init__(parent)

        self.setObjectName("charBudget")
        self._total: int = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        layout.addLayout(self._build_item(total_label, "0", value_key="total"))
        layout.addLayout(self._build_item("사용", "0", value_key="used"))
        layout.addLayout(self._build_item("남은 포인트", "0", value_key="remain"))

        self.bar: QProgressBar = QProgressBar(self)
        self.bar.setObjectName("charBudgetBar")
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(8)
        layout.addWidget(self.bar, 1)

    def _build_item(self, label: str, value: str, value_key: str) -> QVBoxLayout:
        """라벨 + 값 묶음"""

        box = QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)

        label_widget: QLabel = QLabel(label, self)
        label_widget.setObjectName("charBudgetLabel")
        label_widget.setFont(CustomFont(8, bold=True))

        value_widget: QLabel = QLabel(value, self)
        value_widget.setObjectName("charBudgetValue")
        value_widget.setFont(CustomFont(15, bold=True))

        if value_key == "total":
            self.total_label = value_widget
        elif value_key == "used":
            self.used_label = value_widget
        elif value_key == "remain":
            self.remain_label = value_widget

        box.addWidget(label_widget)
        box.addWidget(value_widget)
        return box

    def recalc(self, total: int, used: float) -> None:
        """사용/남은/진행바 갱신"""

        self._total = total
        remain: float = total - used
        used_text: str = str(int(used)) if used == int(used) else str(used)
        remain_text: str = str(int(remain)) if remain == int(remain) else str(remain)

        self.total_label.setText(str(total))
        self.used_label.setText(used_text)
        self.remain_label.setText(remain_text)
        self.remain_label.setProperty("over", remain < 0)
        self.remain_label.style().unpolish(self.remain_label)
        self.remain_label.style().polish(self.remain_label)

        ratio: int = 0 if total == 0 else min(100, int(used / total * 100))
        self.bar.setValue(ratio)


class DistributionTab(CharacterTab):
    """스탯·단전 분배 탭"""

    def __init__(self, parent: QWidget, session: CharacterEditSession) -> None:
        super().__init__(parent, session)

        self._profile: CharacterProfile | None = None
        self._loading: bool = False
        self._session.progression_changed.connect(self._sync_progression)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        cards: ResponsiveColumnsBox = ResponsiveColumnsBox(
            self,
            min_column_width=500,
            spacing=16,
        )
        cards.addWidget(self._build_stat_card())
        cards.addWidget(self._build_danjeon_card())
        layout.addWidget(cards)
        layout.addStretch(1)

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        self._loading = True
        self._profile = profile
        self.setEnabled(profile is not None)

        if profile is None:
            for field in self._stat_fields.values():
                field.set_number(0)

            for field in self._danjeon_fields.values():
                field.set_number(0)

            self._stat_budget.recalc(0, 0)
            self._danjeon_budget.recalc(0, 0)
            self._loading = False
            return

        self._stat_fields["strength"].set_number(float(profile.distribution.strength))
        self._stat_fields["dexterity"].set_number(float(profile.distribution.dexterity))
        self._stat_fields["vitality"].set_number(float(profile.distribution.vitality))
        self._stat_fields["luck"].set_number(float(profile.distribution.luck))

        self._danjeon_fields["upper"].set_number(float(profile.danjeon.upper))
        self._danjeon_fields["middle"].set_number(float(profile.danjeon.middle))
        self._danjeon_fields["lower"].set_number(float(profile.danjeon.lower))

        self._recalc_stat()
        self._recalc_danjeon()
        self._loading = False

    def _build_stat_card(self) -> CharCard:
        """스탯 분배 카드"""

        card: CharCard = CharCard(self, "스탯 분배")
        optimize_btn: StyledButton = StyledButton(
            self,
            "자동 최적화",
            kind="normal",
            point_size=9,
        )
        optimize_btn.clicked.connect(self._optimize_stat)
        card.add_header_widget(optimize_btn)

        self._stat_budget: _Budget = _Budget(self, "분배 가능")
        card.add_widget(self._stat_budget)

        self._stat_fields: dict[str, StepperField] = {}
        items: list[QWidget] = [
            self._build_item(key, label, effect, self._recalc_stat, self._stat_fields)
            for key, label, effect in STAT_DISTRIBUTION_ITEMS
        ]
        card.add_widget(self._build_item_row(items))
        return card

    def _build_danjeon_card(self) -> CharCard:
        """단전 분배 카드"""

        card: CharCard = CharCard(self, "단전 분배")
        optimize_btn: StyledButton = StyledButton(
            self,
            "자동 최적화",
            kind="normal",
            point_size=9,
        )
        optimize_btn.clicked.connect(self._optimize_danjeon)
        card.add_header_widget(optimize_btn)

        self._danjeon_budget: _Budget = _Budget(self, "분배 가능")
        card.add_widget(self._danjeon_budget)

        self._danjeon_fields: dict[str, StepperField] = {}
        items: list[QWidget] = [
            self._build_item(
                key,
                label,
                effect,
                self._recalc_danjeon,
                self._danjeon_fields,
            )
            for key, label, effect in DANJEON_DISTRIBUTION_ITEMS
        ]
        card.add_widget(self._build_item_row(items))
        return card

    def _build_item_row(self, items: list[QWidget]) -> QWidget:
        """항목 가로 배치"""

        row_container: QFrame = QFrame(self)
        row = QHBoxLayout(row_container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        row.addStretch(1)
        for item in items:
            row.addWidget(item)
            row.addStretch(1)

        return row_container

    def _build_item(
        self,
        key: str,
        label: str,
        effect: str,
        on_changed: Callable[[str], None],
        field_store: dict[str, StepperField],
    ) -> QWidget:
        """분배 항목 입력 카드"""

        card: QFrame = QFrame(self)
        box = QVBoxLayout(card)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        name_label: QLabel = QLabel(label, card)
        name_label.setObjectName("charFieldLabel")
        name_label.setFont(CustomFont(9, bold=True))
        name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(name_label)

        field: StepperField = StepperField(card, "0")
        field.input.setValidator(QIntValidator(0, 1_000_000, field.input))
        field.value_changed.connect(lambda target_key=key: on_changed(target_key))
        field.setFixedWidth(_ITEM_FIELD_WIDTH)
        field_store[key] = field
        box.addWidget(field, alignment=Qt.AlignmentFlag.AlignHCenter)

        effect_label: QLabel = QLabel(effect.replace(" · ", "\n"), card)
        effect_label.setObjectName("charHint")
        effect_label.setFont(CustomFont(8))
        effect_label.setWordWrap(True)
        effect_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(effect_label)

        box.addStretch(1)
        return card

    def _recalc_stat(self, changed_key: str | None = None) -> None:
        """스탯 분배 모델 반영 및 요약 갱신"""

        if self._profile is None:
            return

        strength: int = int(self._stat_fields["strength"].number())
        dexterity: int = int(self._stat_fields["dexterity"].number())
        vitality: int = int(self._stat_fields["vitality"].number())
        luck: int = int(self._stat_fields["luck"].number())
        total: int = self._profile.level * 5
        used: int = strength + dexterity + vitality + luck

        if changed_key is not None and used > total:
            other_used: int = used - int(self._stat_fields[changed_key].number())
            clamped_value: int = max(0, total - other_used)
            self._stat_fields[changed_key].set_number(float(clamped_value))
            self._recalc_stat()
            return

        self._stat_budget.recalc(total, float(used))
        if self._loading:
            return

        current_values: tuple[int, int, int, int] = (
            self._profile.distribution.strength,
            self._profile.distribution.dexterity,
            self._profile.distribution.vitality,
            self._profile.distribution.luck,
        )
        if current_values == (strength, dexterity, vitality, luck):
            return

        self._profile.distribution.strength = strength
        self._profile.distribution.dexterity = dexterity
        self._profile.distribution.vitality = vitality
        self._profile.distribution.luck = luck
        self._session.commit_stats()

    def _recalc_danjeon(self, changed_key: str | None = None) -> None:
        """단전 분배 모델 반영 및 요약 갱신"""

        if self._profile is None:
            return

        upper: int = int(self._danjeon_fields["upper"].number())
        middle: int = int(self._danjeon_fields["middle"].number())
        lower: int = int(self._danjeon_fields["lower"].number())
        total: int = REALM_TIER_SPECS[self._profile.realm].danjeon_points
        used: int = upper + middle + lower

        if changed_key is not None and used > total:
            other_used: int = used - int(self._danjeon_fields[changed_key].number())
            clamped_value: int = max(0, total - other_used)
            self._danjeon_fields[changed_key].set_number(float(clamped_value))
            self._recalc_danjeon()
            return

        self._danjeon_budget.recalc(total, float(used))
        if self._loading:
            return

        current_values: tuple[int, int, int] = (
            self._profile.danjeon.upper,
            self._profile.danjeon.middle,
            self._profile.danjeon.lower,
        )
        if current_values == (upper, middle, lower):
            return

        self._profile.danjeon.upper = upper
        self._profile.danjeon.middle = middle
        self._profile.danjeon.lower = lower
        self._session.commit_stats()

    def _optimize_stat(self) -> None:
        """스탯 분배 자동 최적화 적용"""

        if self._profile is None:
            return

        optimized = optimize_stat_distribution(self._profile)
        self._profile.distribution = optimized
        self.set_profile(self._profile)
        self._session.commit_stats()

    def _optimize_danjeon(self) -> None:
        """단전 분배 자동 최적화 적용"""

        if self._profile is None:
            return

        optimized = optimize_danjeon(self._profile)
        self._profile.danjeon = optimized
        self.set_profile(self._profile)
        self._session.commit_stats()

    def _sync_progression(self) -> None:
        """레벨·경지 기준 분배 한도와 보정값 반영"""

        self.set_profile(self._profile)
