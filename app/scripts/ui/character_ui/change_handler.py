from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CharacterChangeHandler:
    """캐릭터 탭 변경을 상위 화면에 전달하는 일반 메서드 모음"""

    _name_changed: Callable[[], None]
    _progression_changed: Callable[[], None]
    _stats_changed: Callable[[], None]
    _saved_value_changed: Callable[[], None]

    def name_changed(self) -> None:
        """캐릭터 이름 변경 전달"""

        self._name_changed()

    def progression_changed(self) -> None:
        """레벨·경지 변경 전달"""

        self._progression_changed()

    def stats_changed(self) -> None:
        """최종 스탯 영향 변경 전달"""

        self._stats_changed()

    def saved_value_changed(self) -> None:
        """저장만 필요한 변경 전달"""

        self._saved_value_changed()
