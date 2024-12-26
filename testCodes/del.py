import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
import sip


class Example(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.button = QPushButton("Click me", self)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)

        self.button.clicked.connect(self.delete_button)

        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle("Widget Deletion Check")
        self.show()

    def delete_button(self):
        self.layout.removeWidget(self.button)
        self.button.deleteLater()

    def check_widget(self):
        if self.button is None:
            print("Button is deleted.")
        else:
            print("Button is not deleted.")

        # Using sip to check if the widget is deleted
        try:
            if sip.isdeleted(self.button):
                print("Button is deleted (sip check).")
            else:
                print("Button is not deleted (sip check).")
        except Exception as e:
            print("Button is None or already deleted.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = Example()

    ex.check_widget()  # Check before deletion
    ex.delete_button()  # Delete the button
    ex.check_widget()  # Check after deletion

    sys.exit(app.exec_())
