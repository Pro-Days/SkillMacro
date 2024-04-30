import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout


class MyWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("툴팁 배경 설정 예제")

        button1 = QPushButton("버튼 1")
        button1.setToolTip("버튼 1입니다.")

        button2 = QPushButton("버튼 2")
        button2.setToolTip("버튼 2입니다.")

        layout = QVBoxLayout()
        layout.addWidget(button1)
        layout.addWidget(button2)

        self.setLayout(layout)

        # 스타일 시트를 사용하여 툴팁의 배경색 변경
        # self.setStyleSheet("QToolTip { background-color: blue; }")

        self.show()


def main():
    app = QApplication(sys.argv)
    ex = MyWidget()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
