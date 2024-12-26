import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


class PlotCanvas(FigureCanvas):

    def __init__(self, parent=None):
        fig, self.ax = plt.subplots()
        super().__init__(fig)
        self.setParent(parent)
        self.plot()

    def plot(self):
        # Generate example data
        data = np.random.normal(12000, 1000, 1000)
        n_bins = 30

        # Calculate bins and width
        counts, bins = np.histogram(data, bins=n_bins)
        bin_width = 0.9 * (bins[1] - bins[0])

        # Plot the histogram
        offset = 50  # Offset above the bottom line
        bars = self.ax.bar(
            bins[:-1], counts, width=bin_width, align="edge", bottom=offset
        )

        # Customizing the plot similar to the image
        self.ax.set_title("DPS 분포")
        self.ax.set_xlabel("DPS")
        self.ax.set_ylabel("반복 횟수")

        # Change colors of the bars
        for bar in bars:
            bar.set_facecolor("yellow")

        # Center 5 bars
        center_start = len(bars) // 2 - 2
        for i in range(center_start, center_start + 5):
            bars[i].set_facecolor("blue")

        # Find the median value
        median_val = np.median(data)
        median_idx = np.digitize(median_val, bins) - 1
        bars[median_idx].set_facecolor("red")

        # Add rounded border to the plot area
        background = patches.FancyBboxPatch(
            (0, 0),
            1,
            1,
            boxstyle="round,pad=0.1,rounding_size=10",
            transform=self.ax.transAxes,
            facecolor="white",
            edgecolor="black",
        )
        self.ax.add_patch(background)
        background.set_zorder(-1)

        # Create the annotation
        annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="black", lw=1.5),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        )
        annotation.set_visible(False)

        def on_hover(event):
            # Check if the cursor is in the plot area
            if event.inaxes == self.ax:
                annotation.set_visible(False)
                for bar in bars:
                    bar.set_facecolor("yellow")
                for i in range(center_start, center_start + 5):
                    bars[i].set_facecolor("blue")
                bars[median_idx].set_facecolor("red")

                # Find the bar under the cursor
                for i, bar in enumerate(bars):
                    if bar.contains(event)[0]:
                        bar.set_facecolor("green")
                        bin_val = bins[i]
                        count_val = counts[i]
                        annotation.xy = (event.xdata, event.ydata)
                        annotation.set_text(
                            f"상한 {bin_val + (bins[1]-bins[0])}\n하한 {bin_val}\n횟수 {int(count_val)}"
                        )
                        annotation.set_visible(True)
                        break
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

        self.plot_canvas = PlotCanvas(self)
        layout.addWidget(self.plot_canvas)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
