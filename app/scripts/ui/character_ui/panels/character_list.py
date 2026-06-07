from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import REALM_TIER_SPECS
from app.scripts.character_models import CharacterProfile
from app.scripts.custom_classes import CustomFont, StyledButton


class _CharacterRow(QFrame):
    """클릭 가능한 캐릭터 목록 행"""

    def __init__(
        self,
        parent: QWidget,
        character: CharacterProfile,
        index: int,
        on_click: Callable[[int], None],
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charRow")
        self.setProperty("active", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        # 캐릭터 이름 표시
        name_text: str = character.name if character.name.strip() else "이름 없음"
        self.name_label: QLabel = QLabel(name_text, self)
        self.name_label.setObjectName("charRowName")
        self.name_label.setFont(CustomFont(11, bold=True))

        # 레벨과 경지 요약 표시
        realm_label: str = REALM_TIER_SPECS[character.realm].label
        meta_text: str = (
            "미입력"
            if character.level <= 0
            else f"Lv. {character.level} · {realm_label}"
        )
        self.meta_label: QLabel = QLabel(meta_text, self)
        self.meta_label.setObjectName("charRowMeta")
        self.meta_label.setFont(CustomFont(9))

        layout.addWidget(self.name_label)
        layout.addWidget(self.meta_label)

        self._index: int = index
        self._on_click: Callable[[int], None] = on_click

    def set_active(self, active: bool) -> None:
        """활성 상태 스타일 갱신"""

        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_index(self, index: int) -> None:
        """목록 구조 변경 후 클릭 인덱스 갱신"""

        self._index = index

    def update_name(self, character: CharacterProfile) -> None:
        """캐릭터 이름 표시 갱신"""

        name_text: str = character.name if character.name.strip() else "이름 없음"
        self.name_label.setText(name_text)

    def update_meta(self, character: CharacterProfile) -> None:
        """캐릭터 레벨·경지 표시 갱신"""

        realm_label: str = REALM_TIER_SPECS[character.realm].label
        meta_text: str = (
            "미입력"
            if character.level <= 0
            else f"Lv. {character.level} · {realm_label}"
        )
        self.meta_label.setText(meta_text)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """행 클릭 시 선택 콜백 호출"""

        self._on_click(self._index)
        super().mousePressEvent(event)


class CharacterListPanel(QFrame):
    """좌측 캐릭터 선택 패널"""

    def __init__(
        self,
        parent: QWidget,
        on_select: Callable[[int], None],
        on_add: Callable[[], None],
        on_paste: Callable[[], None],
        on_clone: Callable[[], None],
        on_delete: Callable[[], None],
    ) -> None:
        super().__init__(parent)

        self.setObjectName("charPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        title: QLabel = QLabel("캐릭터 선택", self)
        title.setObjectName("charPanelTitle")
        title.setFont(CustomFont(15, bold=True))
        layout.addWidget(title)

        # 캐릭터 행 목록 영역
        self._list_layout = QVBoxLayout()
        self._list_layout.setContentsMargins(0, 16, 0, 0)
        self._list_layout.setSpacing(10)
        layout.addLayout(self._list_layout)

        self._rows: list[_CharacterRow] = []
        self._selected_index: int = -1
        self._on_select: Callable[[int], None] = on_select

        # 캐릭터 관리 버튼 영역
        button_grid = QGridLayout()
        button_grid.setContentsMargins(0, 16, 0, 0)
        button_grid.setHorizontalSpacing(10)
        button_grid.setVerticalSpacing(10)

        add_btn: StyledButton = StyledButton(self, "추가", kind="add")
        paste_btn: StyledButton = StyledButton(self, "붙여넣기", kind="normal")
        clone_btn: StyledButton = StyledButton(self, "복제", kind="normal")
        delete_btn: StyledButton = StyledButton(self, "삭제", kind="danger")

        add_btn.clicked.connect(on_add)
        paste_btn.clicked.connect(on_paste)
        clone_btn.clicked.connect(on_clone)
        delete_btn.clicked.connect(on_delete)

        button_grid.addWidget(add_btn, 0, 0)
        button_grid.addWidget(paste_btn, 0, 1)
        button_grid.addWidget(clone_btn, 1, 0)
        button_grid.addWidget(delete_btn, 1, 1)

        layout.addLayout(button_grid)
        layout.addStretch(1)

    def set_characters(
        self,
        characters: list[CharacterProfile],
        selected_index: int,
    ) -> None:
        """캐릭터 목록 재구성"""

        # 기존 행 위젯 제거
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget: QWidget | None = item.widget()
            if widget is not None:
                widget.deleteLater()

        # 현재 저장소 기준 행 생성
        self._rows = []
        self._selected_index = selected_index
        for index, character in enumerate(characters):
            row: _CharacterRow = _CharacterRow(
                self,
                character,
                index,
                self._handle_select,
            )
            row.set_active(index == selected_index)
            self._rows.append(row)
            self._list_layout.addWidget(row)

    def _handle_select(self, index: int) -> None:
        """행 선택 시 활성 표시 갱신 후 콜백 전달"""

        self.set_selected_index(index)
        self._on_select(index)

    def append_character(
        self, character: CharacterProfile, selected_index: int
    ) -> None:
        """새 캐릭터 행 하나 추가"""

        row = _CharacterRow(
            self,
            character,
            len(self._rows),
            self._handle_select,
        )
        self._rows.append(row)
        self._list_layout.addWidget(row)
        self.set_selected_index(selected_index)

    def remove_character(self, index: int, selected_index: int) -> None:
        """삭제된 캐릭터 행 하나 제거"""

        row: _CharacterRow = self._rows.pop(index)
        self._list_layout.removeWidget(row)
        row.deleteLater()
        for row_index, current_row in enumerate(self._rows):
            current_row.set_index(row_index)

        self.set_selected_index(selected_index)

    def set_selected_index(self, index: int) -> None:
        """선택 행 강조 갱신"""

        self._selected_index = index
        for row_index, row in enumerate(self._rows):
            row.set_active(row_index == index)

    def update_selected_name(self, character: CharacterProfile) -> None:
        """선택 캐릭터 행 이름 갱신"""

        self._rows[self._selected_index].update_name(character)

    def update_selected_meta(self, character: CharacterProfile) -> None:
        """선택 캐릭터 행 요약 갱신"""

        self._rows[self._selected_index].update_meta(character)
