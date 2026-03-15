from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.config import config
from app.scripts.registry.resource_registry import convert_resource_path


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

        self.setStyleSheet(
            f"""
            QLineEdit[valid=true] {{
                background-color: #f0f0f0;
                border: 1px solid #D9D9D9;
                border-radius: {border_radius}px;
            }}
            QLineEdit[valid=false] {{
                background-color: #f0f0f0;
                border: 2px solid #FF6060;
                border-radius: {border_radius}px;
            }}
            """
        )

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

        if config.ui.debug_colors:
            self.setStyleSheet(
                "QFrame { background-color: orange; border: 0px solid; }"
            )

        # 전체 layout 설정
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # label 생성
        self.label = QLabel(name, self)
        self.label.setStyleSheet(
            "QLabel { background-color: transparent; border: 0px solid; }"
        )
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
        connected_function=None,
        point_size: int = 10,
    ) -> None:
        super().__init__(parent)

        bg_color = "#f0f0f0"
        border_color = "#D9D9D9"

        style_sheet: str = f"""
        QComboBox {{
            background-color: {bg_color};
            border: 1px solid {border_color};
            border-radius: 4px;
        }}
        QComboBox::drop-down {{
            width: 20px;
            border-left-width: 1px;
            border-left-color: darkgray;
            border-left-style: solid;
        }}
        QComboBox::down-arrow {{
            image: url({convert_resource_path("resources\\image\\down_arrow.png").replace("\\", "/")});
            width: 16px;
            height: 16px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {border_color};
        }}"""

        self.setFont(CustomFont(point_size))
        self.addItems(items)
        self.setStyleSheet(style_sheet)

        if connected_function:
            self.currentIndexChanged.connect(connected_function)


class SkillImage(QLabel):
    """
    스킬 아이콘만을 표시하는 위젯
    """

    def __init__(self, parent: QWidget, pixmap: QPixmap, size: int = 0) -> None:
        super().__init__(parent)

        self.setStyleSheet("QLabel { background-color: transparent; border: 0px; }")

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
    """

    def __init__(self, point_size: int = 10, font_name: str = "Noto Sans KR") -> None:
        super().__init__(font_name, point_size)

        self.setStyleHint(QFont.StyleHint.SansSerif)
        self.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        # 폰트 안티에일리어싱 설정
        self.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)



