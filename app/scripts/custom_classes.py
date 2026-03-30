from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CustomLineEdit(QLineEdit):
    """
    유저 입력을 받는 라인에딧 위젯
    """

    def __init__(
        self,
        parent: QWidget,
        connected_function: Callable | None = None,
        text: str = "",
        point_size: int = 14,
        border_radius: int = 4,
    ) -> None:
        super().__init__(text, parent)

        self.setFont(CustomFont(point_size))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setProperty("radius", str(border_radius))

        self.set_valid(True)

        if connected_function:
            self.textChanged.connect(connected_function)

    def set_valid(self, is_valid: bool) -> None:
        """
        입력이 유효한지에 따라 스타일 변경
        """

        self.setProperty("valid", is_valid)
        self.style().unpolish(self)  # type: ignore
        self.style().polish(self)  # type: ignore
        self.update()


class KVInput(QFrame):
    def __init__(
        self,
        parent: QWidget,
        name: str,
        value: str,
        connected_function: Callable[[], None],
        max_width: int = 120,
    ):
        super().__init__(parent)

        # 전체 layout 설정
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # label 생성
        self.label = QLabel(name, self)
        self.label.setFont(CustomFont(10))
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # lineEdit 생성
        self.input = CustomLineEdit(self, connected_function, value)
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input.setMaximumWidth(max_width)

        # layout에 추가
        layout.addWidget(self.label)
        layout.addWidget(self.input)

        # layout 설정
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


class CustomComboBox(QComboBox):
    """
    유저 입력을 받는 콤보박스 위젯
    """

    def __init__(
        self,
        parent: QWidget,
        items: list[str],
        connected_function: Callable[[], None] | None = None,
        point_size: int = 10,
    ) -> None:
        super().__init__(parent)

        self.setFont(CustomFont(point_size))
        self.addItems(items)

        if connected_function:
            self.currentIndexChanged.connect(connected_function)

    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore
        """
        닫힌 상태 휠 변경 방지
        """

        # 드롭다운 펼침 상태에서만 기본 무공비급 동작 허용
        if self.view().isVisible():
            super().wheelEvent(event)

            return

        # 호버 상태 휠 입력 무시
        event.ignore()


class SkillImage(QLabel):
    """
    스킬 아이콘만을 표시하는 위젯
    """

    def __init__(self, parent: QWidget, pixmap: QPixmap, size: int = 0) -> None:
        super().__init__(parent)

        self.setPixmap(pixmap)
        self.setScaledContents(True)

        if size != 0:
            self.setFixedSize(size, size)


class CustomShadowEffect(QGraphicsDropShadowEffect):
    """
    위젯 그림자 효과
    """

    def __init__(self, offset_x=5, offset_y=5, blur_radius=10, transparent=100):
        super().__init__()

        self.setBlurRadius(blur_radius)
        self.setColor(QColor(0, 0, 0, transparent))
        self.setOffset(offset_x, offset_y)


class CustomFont(QFont):
    """
    커스텀 폰트 클래스

    Args:
        point_size: 폰트 크기 (pt)
        font_name:  폰트 이름
        bold:       굵게 여부
    """

    def __init__(
        self,
        point_size: int = 10,
        font_name: str = "Noto Sans KR",
        bold: bool = False,
    ) -> None:
        super().__init__(font_name, point_size)

        if bold:
            self.setBold(True)

        self.setStyleHint(QFont.StyleHint.SansSerif)
        self.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        # 폰트 안티에일리어싱 설정
        self.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)


# 레이아웃 / 컨테이너 헬퍼 위젯


class KVComboInput(QFrame):
    """
    KVInput 과 동일한 레이아웃(라벨 위, 콤보박스 아래)의 드롭다운 위젯

    KVInput 은 텍스트 입력에, KVComboInput 은 선택 입력에 사용
    두 위젯이 나란히 놓여도 시각적으로 일관된 형태를 유지
    """

    def __init__(
        self,
        parent: QWidget,
        name: str,
        items: list[str],
        connected_function: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 라벨 — KVInput 과 동일한 스타일
        self.label = QLabel(name, self)
        self.label.setFont(CustomFont(10))
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # 콤보박스
        self.combobox = CustomComboBox(self, items, connected_function)

        # 가장 긴 항목 문자열 기준 최소 폭 계산
        content_metrics: QFontMetrics = QFontMetrics(self.combobox.font())
        longest_item_width: int = 0
        for item_text in items:
            item_width: int = content_metrics.horizontalAdvance(item_text)
            if item_width > longest_item_width:
                longest_item_width = item_width

        # 드롭다운 버튼과 좌우 여백까지 포함한 콤보박스 최소 폭 반영
        minimum_combobox_width: int = longest_item_width + 44
        self.combobox.setMinimumWidth(minimum_combobox_width)
        self.setMinimumWidth(minimum_combobox_width)

        layout.addWidget(self.label)
        layout.addWidget(self.combobox)
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


class Separator(QFrame):
    """
    서브섹션 사이에 넣는 수평 구분선
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setObjectName("separator")
        self.setFixedHeight(1)


class SectionCard(QFrame):
    """
    섹션 제목과 내용을 카드 형태로 묶는 컨테이너 위젯

    구조:
        ┌─────────────────────────────────────┐
        │ ▍ 섹션 제목                          │  ← 헤더 (accent bar + 제목 + 구분선)
        ├─────────────────────────────────────┤
        │  (내용 위젯들 — add_widget 으로 추가)  │  ← 콘텐츠 영역
        └─────────────────────────────────────┘

    서브섹션이 필요할 때는 add_sub_title / add_separator 를 함께 사용
    """

    # 헤더 왼쪽 강조 바 색상
    _ACCENT_COLOR = "#4A90E2"

    def __init__(self, parent: QWidget, title: str) -> None:
        super().__init__(parent)

        # 카드 외곽 스타일 — 서브클래스 이름으로 선택자를 한정해
        # 내부 QFrame 에 스타일이 새어 나가지 않도록 한다.
        self.setObjectName("SectionCard")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 헤더 영역
        main_layout.addWidget(self._build_header(title))

        # 헤더-콘텐츠 구분선
        main_layout.addWidget(Separator(self))

        # 콘텐츠 영역
        content_wrapper = QWidget(self)
        content_wrapper.setObjectName("SectionCardContent")

        self._content_layout = QVBoxLayout(content_wrapper)
        self._content_layout.setContentsMargins(14, 10, 14, 14)
        self._content_layout.setSpacing(8)
        content_wrapper.setLayout(self._content_layout)

        main_layout.addWidget(content_wrapper)
        self.setLayout(main_layout)

    # 헤더 빌더

    def _build_header(self, title: str) -> QWidget:
        """강조 바 + 제목 텍스트로 구성된 헤더 위젯 생성"""

        header = QWidget(self)
        header.setObjectName("SectionCardHeader")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        # 왼쪽 강조 바
        accent_bar = QFrame(header)
        accent_bar.setObjectName("sectionCardAccentBar")
        accent_bar.setFixedSize(4, 16)

        # 제목 레이블
        title_label = QLabel(title, header)
        title_label.setObjectName("sectionCardTitle")
        title_label.setFont(CustomFont(12, bold=True))

        layout.addWidget(accent_bar)
        layout.addWidget(title_label)
        layout.addStretch(1)
        header.setLayout(layout)

        return header

    # 콘텐츠 추가 메서드

    def add_widget(self, widget: QWidget) -> None:
        """콘텐츠 영역에 위젯 추가"""
        self._content_layout.addWidget(widget)

    def add_layout(self, layout: QHBoxLayout | QVBoxLayout) -> None:
        """콘텐츠 영역에 레이아웃 추가"""
        self._content_layout.addLayout(layout)

    def add_sub_title(self, text: str) -> None:
        """서브섹션 제목 라벨 추가 (11pt, 회색)"""
        label = QLabel(text, self)
        label.setObjectName("sectionCardSubTitle")
        label.setFont(CustomFont(11, bold=True))
        self._content_layout.addWidget(label)

    def add_separator(self) -> None:
        """서브섹션 사이에 수평 구분선 추가"""
        # 구분선 위아래에 여백이 생기도록 마진이 있는 래퍼로 감싼다.
        wrapper = QWidget(self)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 4, 0, 4)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(Separator(wrapper))
        wrapper.setLayout(wrapper_layout)
        self._content_layout.addWidget(wrapper)


# 버튼 헬퍼


class StyledButton(QPushButton):
    """
    색상과 hover 효과가 있는 스타일 버튼.

    kind 값에 따라 색상이 결정된다:
        "add"    — 초록
        "danger" — 빨강
        "normal" — 회색
    """

    def __init__(
        self,
        parent: QWidget,
        text: str,
        kind: str = "normal",
        point_size: int = 10,
    ) -> None:
        super().__init__(text, parent)

        self.setObjectName(f"styledButton{kind.capitalize()}")
        self.setFont(CustomFont(point_size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
