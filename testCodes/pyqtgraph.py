import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyqtgraph as pg
import numpy as np


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Interactive Line Graph with PyQt6")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.plot_widget = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.plot_widget)

        self.plot = self.plot_widget.addPlot()
        self.plot_data()

    def plot_data(self):
        # Sample data
        x = np.linspace(0, 10, 100)
        y = np.sin(x)

        # Plotting data
        self.curve = self.plot.plot(x, y, pen=pg.mkPen("b", width=2))

        # Adding mouse hover event
        self.plot.scene().sigMouseMoved.connect(self.on_mouse_moved)

        # Text item to display data points
        self.text_item = pg.TextItem("", anchor=(0.5, 1.5), color=(255, 0, 0))
        self.plot.addItem(self.text_item)

    def on_mouse_moved(self, pos):
        mouse_point = self.plot.vb.mapSceneToView(pos)
        x = mouse_point.x()
        y = mouse_point.y()

        # Find the nearest data point
        index = np.argmin(np.abs(self.curve.xData - x))
        x_closest = self.curve.xData[index]
        y_closest = self.curve.yData[index]

        self.text_item.setText(f"x: {x_closest:.2f}, y: {y_closest:.2f}")
        self.text_item.setPos(x_closest, y_closest)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
