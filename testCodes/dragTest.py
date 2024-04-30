import sys
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QFrame


class DraggableFrame(QFrame):
    def __init__(self, parent=None):
        super(DraggableFrame, self).__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setGeometry(100, 100, 200, 150)
        self.setMouseTracking(True)

        # 초기 위치 저장
        self.start_pos = None

        # 이동 가능한 x좌표의 범위
        self.min_x = -100
        self.max_x = 300

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # 마우스 클릭 시 시작 위치를 저장
            self.start_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        # 마우스 이동 시 x좌표만 이동, 범위 내에서만 이동
        if event.buttons() == Qt.LeftButton and self.start_pos:
            delta = event.x() - self.start_pos.x()
            new_x = self.x() + delta

            # 이동 가능한 범위 내에서만 이동
            new_x = min(max(new_x, self.min_x), self.max_x)

            self.move(new_x, self.y())

    def mouseReleaseEvent(self, event: QMouseEvent):
        # 마우스 릴리스 시 시작 위치 초기화
        self.start_pos = None


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 400, 300)
        self.setWindowTitle("Draggable QFrame Example")

        frame = DraggableFrame(self)
        self.setCentralWidget(frame)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
