import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QFrame,
    QScrollArea,
    QPushButton,
)


class ScrollableFrameExample(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Scrollable QFrame Example")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()
        scroll_area = QScrollArea()

        # Scrollable content widget
        content_widget = QFrame()

        # Add some buttons to demonstrate scrolling
        for i in range(4):
            btn = QPushButton(f"Button {i+1}", content_widget)
            btn.move(0, 100 * i)

        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout.addWidget(scroll_area)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScrollableFrameExample()
    window.show()
    sys.exit(app.exec())
