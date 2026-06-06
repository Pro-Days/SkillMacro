"""영단 탭"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import STAT_SPECS
from app.scripts.character_data import ELIXIR_SPECS
from app.scripts.character_models import MAX_ELIXIR_COUNT, CharacterProfile, Elixir
from app.scripts.custom_classes import CustomFont
from app.scripts.ui.character_ui.edit_session import CharacterEditSession
from app.scripts.ui.character_ui.tabs.base import CharacterTab
from app.scripts.ui.character_ui.widgets import (
    CharCard,
    ColorOrb,
    FlowLayout,
    StepperField,
)

_ELIXIR_COLORS: dict[Elixir, str] = {
    Elixir.HWANGHWANDAN: "#e8c95a",
    Elixir.NOKHWANDAN: "#7bbf6a",
    Elixir.JAHWANDAN: "#a86fd0",
    Elixir.CHEONGHWANDAN: "#4f9bd9",
    Elixir.JEOKHWANDAN: "#d75a5a",
    Elixir.BAEKHWANDAN: "#dcdcdc",
    Elixir.HEUKHWANDAN: "#4a4a4a",
    Elixir.OKHWANDAN: "#6fcabf",
    Elixir.EUNHWANDAN: "#b8c0cc",
    Elixir.GEUMHWANDAN: "#e0b94a",
    Elixir.MAEHWADAN: "#e87fb0",
    Elixir.YONGHYEOLDAN: "#c0392b",
    Elixir.MYEONGWOLDAN: "#cfd6e0",
    Elixir.TAEGEUKDAN: "#d98b3a",
    Elixir.CHEONGYEONGDAN: "#8a7fd0",
    Elixir.SIGONGDAN: "#5ac0c0",
    Elixir.CHEONGRYONGDAN: "#2f8f6f",
    Elixir.BAEKHODAN: "#f0f0f0",
    Elixir.JUJAKDAN: "#d65a3a",
    Elixir.HYEONMUDAN: "#2f5f8f",
}


class _ElixirCard(QFrame):
    """영단 1종 카드"""

    def __init__(
        self,
        parent: QWidget,
        elixir: Elixir,
        color: str,
        on_changed: Callable[[Elixir, int], None],
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charPillCard")
        self.setProperty("on", False)
        self.setFixedWidth(150)

        self._elixir: Elixir = elixir
        self._on_changed: Callable[[Elixir, int], None] = on_changed

        spec = ELIXIR_SPECS[elixir]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 영단 이름 표시
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(ColorOrb(self, color))
        name_label: QLabel = QLabel(spec.name, self)
        name_label.setObjectName("charPillName")
        name_label.setFont(CustomFont(11, bold=True))
        top.addWidget(name_label)
        top.addStretch(1)
        layout.addLayout(top)

        # 영단 효과 표시
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

        # 보유 수 입력
        counter = QHBoxLayout()
        counter.setSpacing(8)

        self._count_field: StepperField = StepperField(self, "0")
        self._count_field.input.setValidator(
            QIntValidator(0, MAX_ELIXIR_COUNT, self._count_field.input)
        )
        self._count_field.value_changed.connect(self._on_count)

        max_label: QLabel = QLabel(f"/ {MAX_ELIXIR_COUNT}", self)
        max_label.setObjectName("charMuted")
        max_label.setFont(CustomFont(9))

        counter.addWidget(self._count_field, 1)
        counter.addWidget(max_label)
        layout.addLayout(counter)

    def set_count(self, count: int) -> None:
        """보유 수 표시 반영"""

        self._count_field.set_number(float(count))
        self.setProperty("on", count > 0)
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_count(self) -> None:
        """입력 보유 수 반영"""

        count: int = max(0, min(MAX_ELIXIR_COUNT, int(self._count_field.number())))
        self.setProperty("on", count > 0)
        self.style().unpolish(self)
        self.style().polish(self)
        self._on_changed(self._elixir, count)


class ElixirTab(CharacterTab):
    """영단 탭"""

    def __init__(self, parent: QWidget, session: CharacterEditSession) -> None:
        super().__init__(parent, session)

        self._profile: CharacterProfile | None = None
        self._loading: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card: CharCard = CharCard(self, "영단")

        grid_container: QFrame = QFrame(self)
        flow: FlowLayout = FlowLayout(grid_container, margin=0, spacing=12, center=True)

        self._cards: dict[Elixir, _ElixirCard] = {}
        for elixir in ELIXIR_SPECS:
            card_widget: _ElixirCard = _ElixirCard(
                grid_container,
                elixir,
                _ELIXIR_COLORS[elixir],
                self._set_count,
            )
            self._cards[elixir] = card_widget
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

        for elixir, card in self._cards.items():
            count: int = 0 if profile is None else profile.elixir.counts.get(elixir, 0)
            card.set_count(count)

        self._loading = False

    def _set_count(self, elixir: Elixir, count: int) -> None:
        """영단 보유 수 모델 반영"""

        if self._profile is None or self._loading:
            return

        if self._profile.elixir.counts.get(elixir, 0) == count:
            return

        if count == 0:
            self._profile.elixir.counts.pop(elixir, None)

        else:
            self._profile.elixir.counts[elixir] = count

        self._session.commit_stats()
