"""환 탭"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import STAT_SPECS
from app.scripts.character_data import PILL_SPECS
from app.scripts.character_models import CharacterProfile, Pill
from app.scripts.custom_classes import CustomFont
from app.scripts.ui.character_ui.widgets import CharCard, ColorOrb, FlowLayout, ToggleSwitch

_PILL_COLORS: tuple[str, ...] = (
    "#7bbf6a",
    "#c8a04a",
    "#d75a5a",
    "#9aa86a",
    "#7a9a5a",
    "#5a8a4a",
    "#c0392b",
    "#4f9bd9",
    "#d98b3a",
    "#a86fd0",
    "#6fcabf",
    "#e87fb0",
    "#e0b94a",
)


class _PillCard(QFrame):
    """환 1종 카드"""

    def __init__(
        self,
        parent: QWidget,
        pill: Pill,
        color: str,
        on_changed: Callable[[Pill, bool], None],
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charPillCard")
        self.setProperty("on", False)
        self.setFixedWidth(150)

        self._pill: Pill = pill
        self._on_changed: Callable[[Pill, bool], None] = on_changed

        spec = PILL_SPECS[pill]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 환 이름 표시
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(ColorOrb(self, color))
        name_label: QLabel = QLabel(spec.name, self)
        name_label.setObjectName("charPillName")
        name_label.setFont(CustomFont(11, bold=True))
        top.addWidget(name_label)
        top.addStretch(1)
        layout.addLayout(top)

        # 환 효과 표시
        effect_text: str = ", ".join(
            f"{STAT_SPECS[stat_key]} +{value:g}"
            for stat_key, value in spec.effects.items()
        )
        effect_label: QLabel = QLabel(effect_text, self)
        effect_label.setObjectName("charPillEff")
        effect_label.setFont(CustomFont(9))
        effect_label.setWordWrap(True)
        effect_label.setMinimumHeight(32)
        layout.addWidget(effect_label)

        # 사용 토글 구성
        foot = QHBoxLayout()
        foot.setSpacing(8)

        use_label: QLabel = QLabel("사용", self)
        use_label.setObjectName("charHint")
        use_label.setFont(CustomFont(9))
        foot.addWidget(use_label)
        foot.addStretch(1)

        self._toggle: ToggleSwitch = ToggleSwitch(self, False, self._on_toggle)
        foot.addWidget(self._toggle)
        layout.addLayout(foot)

    def set_active(self, active: bool) -> None:
        """사용 여부 표시 반영"""

        self._toggle.setChecked(active)
        self.setProperty("on", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_toggle(self, active: bool) -> None:
        """토글 시 모델 반영"""

        self.setProperty("on", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self._on_changed(self._pill, active)


class PillTab(QFrame):
    """환 탭"""

    def __init__(self, parent: QWidget, on_changed: Callable[[], None]) -> None:
        super().__init__(parent)

        self._profile: CharacterProfile | None = None
        self._on_changed: Callable[[], None] = on_changed
        self._loading: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card: CharCard = CharCard(self, "환")

        grid_container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(grid_container, margin=0, spacing=12, center=True)

        self._cards: dict[Pill, _PillCard] = {}
        for index, pill in enumerate(PILL_SPECS):
            card_widget: _PillCard = _PillCard(
                grid_container,
                pill,
                _PILL_COLORS[index],
                self._set_active,
            )
            self._cards[pill] = card_widget
            flow.addWidget(card_widget)

        grid_container.setLayout(flow)

        card.add_widget(grid_container)
        layout.addWidget(card)
        layout.addStretch(1)

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        self._loading = True
        self._profile = profile
        self.setEnabled(profile is not None)

        for pill, card in self._cards.items():
            active: bool = False if profile is None else pill in profile.pill.active
            card.set_active(active)

        self._loading = False

    def _set_active(self, pill: Pill, active: bool) -> None:
        """환 사용 여부 모델 반영"""

        if self._profile is None or self._loading:
            return

        if active:
            self._profile.pill.active.add(pill)

        else:
            self._profile.pill.active.discard(pill)

        self._on_changed()
