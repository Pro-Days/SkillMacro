"""환 탭"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import STAT_SPECS
from app.scripts.character_data import PILL_SPECS
from app.scripts.character_models import CharacterProfile
from app.scripts.custom_classes import CustomFont
from app.scripts.ui.character_ui.change_handler import CharacterChangeHandler
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.widgets import CharCard, ColorOrb, FlowLayout


class _PillCard(QFrame):
    """환 1종 카드"""

    def __init__(
        self,
        parent: QWidget,
        pill: str,
        on_changed: Callable[[str, bool], None],
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charPillCard")
        self.setProperty("on", False)
        self.setFixedWidth(150)

        self._pill: str = pill
        self._on_changed: Callable[[str, bool], None] = on_changed

        spec = PILL_SPECS[pill]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 환 이름 표시
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(ColorOrb(self, spec.color))
        name_label: QLabel = QLabel(pill, self)
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

        # 사용 여부 버튼 구성
        foot = QHBoxLayout()
        foot.setSpacing(8)
        foot.addStretch(1)

        self._use_button: QPushButton = QPushButton("사용", self)
        self._use_button.setObjectName("charUseToggle")
        self._use_button.setCheckable(True)
        self._use_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._use_button.setFixedHeight(26)
        self._use_button.setMinimumWidth(54)
        self._use_button.setFont(CustomFont(9, bold=True))
        self._use_button.toggled.connect(self._on_toggle)
        foot.addWidget(self._use_button)
        layout.addLayout(foot)

    def set_active(self, active: bool) -> None:
        """사용 여부 표시 반영"""

        with QSignalBlocker(self._use_button):
            self._use_button.setChecked(active)
        self.setProperty("on", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_toggle(self, active: bool) -> None:
        """토글 시 모델 반영"""

        self.setProperty("on", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self._on_changed(self._pill, active)


class PillTab(CharacterTab):
    """환 탭"""

    def __init__(
        self,
        parent: QWidget,
        changes: CharacterChangeHandler,
        profile: CharacterProfile,
    ) -> None:
        super().__init__(parent, changes, profile)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card: CharCard = CharCard(self, "환")

        grid_container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(grid_container, margin=0, spacing=12, center=True)

        self._cards: dict[str, _PillCard] = {}
        for pill in PILL_SPECS:
            card_widget: _PillCard = _PillCard(
                grid_container,
                pill,
                self._set_active,
            )
            self._cards[pill] = card_widget
            flow.addWidget(card_widget)

        grid_container.setLayout(flow)

        card.add_widget(grid_container)
        layout.addWidget(card)
        layout.addStretch(1)

    def set_profile(self, profile: CharacterProfile) -> None:
        """선택 캐릭터 모델 반영"""

        self._profile = profile

        for pill, card in self._cards.items():
            active: bool = pill in profile.pill.active
            card.set_active(active)

    def _set_active(self, pill: str, active: bool) -> None:
        """환 사용 여부 모델 반영"""

        if (pill in self._profile.pill.active) == active:
            return

        if active:
            self._profile.pill.active.add(pill)

        else:
            self._profile.pill.active.discard(pill)

        self._changes.stats_changed()
