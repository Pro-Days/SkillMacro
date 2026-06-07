from __future__ import annotations

from PySide6.QtWidgets import QFrame, QWidget

from app.scripts.character_models import CharacterProfile
from app.scripts.ui.character_ui.change_handler import CharacterChangeHandler


class CharacterTab(QFrame):
    """캐릭터 입력 탭 공통 베이스"""

    def __init__(
        self,
        parent: QWidget,
        changes: CharacterChangeHandler,
    ) -> None:
        super().__init__(parent)
        self._changes: CharacterChangeHandler = changes

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        raise NotImplementedError

    def on_progression_changed(self) -> None:
        """레벨·경지 변경 반영"""

        pass
