"""캐릭터 편집 화면 변경 전파 세션"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.scripts.character_engine import clamp_profile_allocations
from app.scripts.character_models import CharacterProfile


class CharacterEditSession(QObject):
    """선택 캐릭터 편집에 따른 화면 간 변경 전파"""

    profile_bound = Signal(object)
    name_changed = Signal()
    progression_changed = Signal()
    live_stats_invalidated = Signal()
    save_requested = Signal()

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._profile: CharacterProfile | None = None

    def bind_profile(self, profile: CharacterProfile | None) -> None:
        """선택 캐릭터 변경 전파"""

        self._profile = profile
        self.profile_bound.emit(profile)

    def commit_name(self) -> None:
        """캐릭터 이름 변경 전파"""

        self.name_changed.emit()
        self.save_requested.emit()

    def commit_progression(self) -> None:
        """레벨·경지 변경과 분배 한도 보정 전파"""

        if self._profile is None:
            raise ValueError("character profile is not bound")

        # 레벨·경지 기준 분배 상태 보정
        clamp_profile_allocations(self._profile)

        self.progression_changed.emit()
        self.live_stats_invalidated.emit()
        self.save_requested.emit()

    def commit_stats(self) -> None:
        """최종 스탯에 영향을 주는 변경 전파"""

        self.live_stats_invalidated.emit()
        self.save_requested.emit()

    def commit_saved_value(self) -> None:
        """화면 외부 계산에 영향 없는 저장값 변경 전파"""

        self.save_requested.emit()
