from .shared_data import UI_Variable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QColor
from PyQt6.QtWidgets import (
    QLineEdit,
    QComboBox,
    QLabel,
    QWidget,
    QGraphicsDropShadowEffect,
)


class CustomLineEdit(QLineEdit):
    """
    유저 입력을 받는 라인에딧 위젯
    """

    def __init__(self, parent, connected_function=None, text="", font_size=14):
        super().__init__(text, parent)

        ui_var = UI_Variable()

        self.setFont(QFont("나눔스퀘어라운드 Bold", font_size))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"QLineEdit {{ background-color: {ui_var.sim_input_colors[0]}; border: 1px solid {ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
        )

        if connected_function is None:
            return

        self.textChanged.connect(connected_function)


class CustomComboBox(QComboBox):
    """
    유저 입력을 받는 콤보박스 위젯
    """

    def __init__(
        self,
        parent,
        items,
        connected_function,
        font_size=10,
    ):
        super().__init__(parent)

        ui_var = UI_Variable()

        self.setFont(QFont("나눔스퀘어라운드 Bold", font_size))
        self.addItems(items)
        self.setStyleSheet(ui_var.comboboxStyle)
        self.currentIndexChanged.connect(connected_function)


class SkillImage(QLabel):
    """
    스킬 아이콘만을 표시하는 위젯
    """

    def __init__(self, parent: QWidget, pixmap: QPixmap, size: int, x: int, y: int):
        super().__init__(parent)

        self.setStyleSheet("QLabel { background-color: transparent; border: 0px; }")

        pixmap = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.setPixmap(pixmap)
        self.setFixedSize(size, size)
        self.move(x, y)


class CustomShadowEffect(QGraphicsDropShadowEffect):
    """
    위젯 그림자 효과
    """

    def __init__(self, offset_x=5, offset_y=5, blur_radius=10, transparent=100):
        super().__init__()

        self.setBlurRadius(blur_radius)
        self.setColor(QColor(0, 0, 0, transparent))
        self.setOffset(offset_x, offset_y)
