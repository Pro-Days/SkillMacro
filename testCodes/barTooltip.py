import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib import font_manager as fm
import matplotlib.pyplot as plt
import numpy as np


plt.style.use("seaborn-v0_8-pastel")
font_path = "font\\NSR_B.ttf"
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = prop.get_name()


class PlotCanvas(FigureCanvas):

    def __init__(self, parent, data):
        fig, self.ax = plt.subplots()
        super().__init__(fig)
        self.setParent(parent)
        self.data = data
        self.plot()

    def plot(self):
        self.colors = {
            "median": "#4070FF",
            "center5": "#75A2FC",
            "cursor": "#BAD0FD",
            "normal": "#F38181",
        }

        n_bins = 15
        counts, bins = np.histogram(self.data, bins=n_bins)
        bin_width = 0.9 * (bins[1] - bins[0])
        bars = self.ax.bar(bins[:-1], counts, width=bin_width, align="edge", bottom=0)

        # Customizing the plot similar to the image
        self.ax.set_title("DPS 분포")
        self.ax.set_xlabel("DPS")
        self.ax.set_ylabel("반복 횟수")

        # Change colors of the bars
        for bar in bars:
            bar.set_facecolor(self.colors["normal"])

        # Center 5 bars
        center_start = len(bars) // 2 - 2
        for i in range(center_start, center_start + 5):
            bars[i].set_facecolor(self.colors["center5"])

        # Highest bar
        median_val = np.median(self.data)
        median_idx = np.digitize(median_val, bins) - 1
        bars[median_idx].set_facecolor(self.colors["median"])

        # Create the annotation
        annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        )
        annotation.set_visible(False)

        def on_hover(event):
            # Check if the cursor is in the plot area
            if event.inaxes == self.ax:
                for bar in bars:
                    bar.set_facecolor(self.colors["normal"])
                for i in range(center_start, center_start + 5):
                    bars[i].set_facecolor(self.colors["center5"])
                bars[median_idx].set_facecolor(self.colors["median"])

                # Find the bar under the cursor
                for i, bar in enumerate(bars):
                    if bar.contains(event)[0]:
                        bar.set_facecolor(self.colors["cursor"])
                        bin_val = bins[i]
                        count_val = counts[i]
                        annotation.xy = (event.xdata, event.ydata)
                        annotation.set_text(
                            f"상한 {bin_val + (bins[1]-bins[0]):.2f}\n하한 {bin_val:.2f}\n횟수 {int(count_val)}"
                        )
                        if not annotation._visible:
                            annotation.set_visible(True)
                        self.draw()
                        break
                else:
                    if annotation._visible:
                        annotation.set_visible(False)
                        self.draw()
            else:
                if annotation._visible:
                    annotation.set_visible(False)
                    self.draw()

        self.mpl_connect("motion_notify_event", on_hover)
        self.draw()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("DPS Distribution")
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout(main_widget)

        data = np.random.normal(12000, 1000, 1000)
        self.plot_canvas = PlotCanvas(self, data)
        # layout.addWidget(self.plot_canvas)
        self.plot_canvas.move(0, 0)
        self.plot_canvas.resize(1200, 600)
        self.plot_canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
