from .shared_data import UI_Variable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLineEdit, QComboBox


class CustomLineEdit(QLineEdit):
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
