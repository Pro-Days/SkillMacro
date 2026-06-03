"""좌측 캐릭터 선택 패널

캐릭터 목록과 추가/붙여넣기/복제/삭제 버튼으로 구성한다.
(요청에 따라 스탯·단전 자동 최적화 버튼은 두지 않는다.)
"""

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

from app.scripts.custom_classes import CustomFont, StyledButton
from app.scripts.ui.character_ui import sample_data


class _CharacterRow(QFrame):
    """클릭 가능한 캐릭터 목록 행"""

    def __init__(
        self,
        parent: QWidget,
        summary: sample_data.CharacterSummary,
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

        self.name_label: QLabel = QLabel(summary.name, self)
        self.name_label.setObjectName("charRowName")
        self.name_label.setFont(CustomFont(11, bold=True))

        self.meta_label: QLabel = QLabel(summary.meta, self)
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

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """행 클릭 시 선택 콜백 호출"""

        self._on_click(self._index)
        super().mousePressEvent(event)


class CharacterListPanel(QFrame):
    """좌측 캐릭터 선택 패널"""

    def __init__(self, parent: QWidget, on_select: Callable[[int], None]) -> None:
        super().__init__(parent)

        self.setObjectName("charPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        title: QLabel = QLabel("캐릭터 선택", self)
        title.setObjectName("charPanelTitle")
        title.setFont(CustomFont(15, bold=True))
        layout.addWidget(title)

        # 캐릭터 목록
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(0, 16, 0, 0)
        list_layout.setSpacing(10)

        self._rows: list[_CharacterRow] = []
        self._on_select: Callable[[int], None] = on_select
        for index, summary in enumerate(sample_data.CHARACTERS):
            row: _CharacterRow = _CharacterRow(self, summary, index, self._handle_select)
            self._rows.append(row)
            list_layout.addWidget(row)

        layout.addLayout(list_layout)

        # 버튼 그리드 (2×2)
        button_grid = QGridLayout()
        button_grid.setContentsMargins(0, 16, 0, 0)
        button_grid.setHorizontalSpacing(10)
        button_grid.setVerticalSpacing(10)

        add_btn: StyledButton = StyledButton(self, "추가", kind="add")
        paste_btn: StyledButton = StyledButton(self, "붙여넣기", kind="normal")
        clone_btn: StyledButton = StyledButton(self, "복제", kind="normal")
        delete_btn: StyledButton = StyledButton(self, "삭제", kind="danger")

        button_grid.addWidget(add_btn, 0, 0)
        button_grid.addWidget(paste_btn, 0, 1)
        button_grid.addWidget(clone_btn, 1, 0)
        button_grid.addWidget(delete_btn, 1, 1)

        layout.addLayout(button_grid)
        layout.addStretch(1)

        # 첫 행 기본 선택
        if self._rows:
            self._rows[0].set_active(True)

    def _handle_select(self, index: int) -> None:
        """행 선택 시 활성 표시 갱신 후 콜백 전달"""

        for i, row in enumerate(self._rows):
            row.set_active(i == index)
        self._on_select(index)
