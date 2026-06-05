"""캐릭터 입력 탭 공통 베이스"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame

from app.scripts.character_models import CharacterProfile


class CharacterTab(QFrame):
    """캐릭터 입력 탭 공통 베이스

    모든 입력 탭은 선택 캐릭터 모델을 받아 화면에 반영하는 `set_profile`을 갖는다.
    레벨·경지처럼 다른 탭에서 입력하는 값에 표시가 의존하는 탭은 입력이 바뀔 때마다
    다시 그려야 하므로 `refresh_on_any_change`를 True로 둔다.
    """

    refresh_on_any_change: bool = False

    def set_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 모델 반영"""

        raise NotImplementedError
