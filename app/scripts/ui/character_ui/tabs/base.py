"""캐릭터 입력 탭 공통 베이스"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QWidget

from app.scripts.character_models import CharacterProfile
from app.scripts.ui.character_ui.edit_session import CharacterEditSession


class CharacterTab(QFrame):
    """캐릭터 입력 탭 공통 베이스"""

    def __init__(self, parent: QWidget, session: CharacterEditSession) -> None:
        super().__init__(parent)
        self._session: CharacterEditSession = session

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        raise NotImplementedError
