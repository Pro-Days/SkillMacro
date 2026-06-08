from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontMetrics, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import REALM_TIER_SPECS
from app.scripts.character_models import CharacterProfile
from app.scripts.custom_classes import CustomFont, StyledButton


class _MiddleElidedLabel(QLabel):
    """가로 폭 기준 가운데 생략 라벨"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._full_text: str = ""
        self.setMinimumWidth(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )

    def setText(self, text: str) -> None:  # type: ignore[override]
        """전체 문구 보관 및 현재 폭 기준 표시 갱신"""

        # 원문 보관 및 툴팁 제공
        self._full_text = text
        self.setToolTip(text)

        # 현재 배치 폭 기준 표시 문구 갱신
        self._refresh_elided_text()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """라벨 폭 변경 시 표시 문구 갱신"""

        # 변경된 폭 기준 가운데 생략 재계산
        self._refresh_elided_text()

        super().resizeEvent(event)

    def _refresh_elided_text(self) -> None:
        """현재 라벨 폭에 맞춘 가운데 생략 문구 적용"""

        # 폰트 기준 실제 표시 가능 폭 계산
        metrics: QFontMetrics = QFontMetrics(self.font())
        available_width: int = max(0, self.width())

        # 원문이 폭을 넘을 때만 가운데 생략 처리
        display_text: str = metrics.elidedText(
            self._full_text,
            Qt.TextElideMode.ElideMiddle,
            available_width,
        )
        super().setText(display_text)


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
        self.name_label: _MiddleElidedLabel = _MiddleElidedLabel(self)
        self.name_label.setObjectName("charRowName")
        self.name_label.setFont(CustomFont(11, bold=True))
        self.name_label.setText(name_text)

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
        on_copy: Callable[[], bool],
        on_paste: Callable[[], bool],
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
        button_grid.setColumnStretch(0, 1)
        button_grid.setColumnStretch(1, 1)

        add_btn: StyledButton = StyledButton(self, "추가", kind="add")
        delete_btn: StyledButton = StyledButton(self, "삭제", kind="danger")
        copy_btn: StyledButton = StyledButton(self, "복사", kind="normal")
        paste_btn: StyledButton = StyledButton(self, "붙여넣기", kind="normal")

        buttons: tuple[StyledButton, ...] = (
            add_btn,
            delete_btn,
            copy_btn,
            paste_btn,
        )
        button_width: int = max(button.sizeHint().width() for button in buttons)
        for button in buttons:
            button.setMinimumWidth(button_width)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

        add_btn.clicked.connect(on_add)
        delete_btn.clicked.connect(on_delete)
        copy_btn.clicked.connect(lambda: self._handle_copy(copy_btn, on_copy))
        paste_btn.clicked.connect(lambda: self._handle_paste(paste_btn, on_paste))

        button_grid.addWidget(add_btn, 0, 0)
        button_grid.addWidget(delete_btn, 0, 1)
        button_grid.addWidget(copy_btn, 1, 0)
        button_grid.addWidget(paste_btn, 1, 1)

        layout.addLayout(button_grid)
        layout.addStretch(1)

    def _handle_copy(
        self,
        button: StyledButton,
        on_copy: Callable[[], bool],
    ) -> None:
        """선택 캐릭터 복사 버튼 피드백 처리"""

        if on_copy():
            self._show_button_feedback(button, "복사됨", "복사")

    def _handle_paste(
        self,
        button: StyledButton,
        on_paste: Callable[[], bool],
    ) -> None:
        """캐릭터 붙여넣기 버튼 피드백 처리"""

        if not on_paste():
            self._show_button_feedback(button, "실패", "붙여넣기")

    def _show_button_feedback(
        self,
        button: StyledButton,
        feedback_text: str,
        default_text: str,
    ) -> None:
        """버튼 텍스트를 잠시 변경한 뒤 원래 문구로 되돌림"""

        button.setText(feedback_text)
        QTimer.singleShot(1500, lambda: button.setText(default_text))

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
