import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PyQt6.QtWidgets import QWidget

import numpy


class DpsDistributionCanvas(FigureCanvas):

    def __init__(self, parent: QWidget, data: list[float]) -> None:
        # init
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)

        # 부모 위젯 설정
        self.setParent(parent)

        # 데이터 저장
        self.data: list[float] = data

        # 그래프 그리기
        self.plot()

    def plot(self) -> None:
        self.colors: dict[str, str] = {
            "median": "#4070FF",
            "center5": "#75A2FC",
            "cursor": "#BAD0FD",
            "normal": "#F38181",
        }

        # 막대 개수
        self.n_bins = 15

        # 히스토그램 데이터 생성
        counts, bins = numpy.histogram(self.data, bins=self.n_bins)
        # counts, bins = self.custom_histogram()

        # 막대 너비
        bin_width: float = 0.9 * (bins[1] - bins[0])

        # 막대 그래프 그리기
        bars = self.ax.bar(bins[:-1], counts, width=bin_width, align="edge", bottom=0)

        # 타이틀 설정
        self.ax.set_title("DPM 분포")

        # y축 눈금을 정수로 설정
        self.ax.yaxis.set_major_locator(mtick.MaxNLocator(integer=True))
        # self.ax.set_xlabel("DPM")
        # self.ax.set_ylabel("반복 횟수")

        # 테두리 제거
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)

        # 배경색 설정
        self.ax.set_facecolor("#F8F8F8")
        self.fig.set_facecolor("#F8F8F8")

        # 막대 색상 설정
        for bar in bars:
            bar.set_facecolor(self.colors["normal"])

        # 중앙 5개 막대 색상 변경
        center_start = 5
        for i in range(center_start, center_start + 5):
            bars[i].set_facecolor(self.colors["center5"])

        # 중앙값 막대 색상 변경
        median_idx: int = self.find_median_index(bins)
        bars[median_idx].set_facecolor(self.colors["median"])

        # Create the annotation
        annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(-24, 10),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round,pad=0.3", fc="white", ec="black", lw=1, alpha=0.5
            ),
            # arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        )
        annotation.set_visible(False)

        def on_hover(event):
            try:
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
                                f"상한 {bin_val + (bins[1]-bins[0]):.1f}\n하한 {bin_val:.1f}\n횟수 {int(count_val)}"
                            )
                            if not annotation._visible:
                                annotation.set_visible(True)
                            self.draw()
                            break
                    else:
                        if annotation._visible:
                            annotation.set_visible(False)
                            for bar in bars:
                                bar.set_facecolor(self.colors["normal"])
                            for i in range(center_start, center_start + 5):
                                bars[i].set_facecolor(self.colors["center5"])
                            bars[median_idx].set_facecolor(self.colors["median"])
                            self.draw()
                else:
                    if annotation._visible:
                        annotation.set_visible(False)
                        for bar in bars:
                            bar.set_facecolor(self.colors["normal"])
                        for i in range(center_start, center_start + 5):
                            bars[i].set_facecolor(self.colors["center5"])
                        bars[median_idx].set_facecolor(self.colors["median"])

            except Exception as e:
                print(f"Error in on_hover: {e}")

        def on_figure_leave(event):
            try:
                annotation.set_visible(False)
                for bar in bars:
                    bar.set_facecolor(self.colors["normal"])
                for i in range(center_start, center_start + 5):
                    bars[i].set_facecolor(self.colors["center5"])
                bars[median_idx].set_facecolor(self.colors["median"])
                self.draw()

            except Exception as e:
                print(f"Error in on_figure_leave: {e}")

        self.mpl_connect("motion_notify_event", on_hover)
        self.mpl_connect("figure_leave_event", on_figure_leave)
        self.draw()

    # def calculate_median(self, data):
    #     """
    #     Calculate the median of a list of numbers without using numpy.
    #     """
    #     sorted_data = sorted(data)
    #     n = len(sorted_data)

    #     if n % 2 == 1:  # Odd number of elements
    #         return sorted_data[n // 2]
    #     else:  # Even number of elements
    #         mid1, mid2 = sorted_data[n // 2 - 1], sorted_data[n // 2]
    #         return (mid1 + mid2) / 2

    # def custom_digitize(self, value, bins) -> int:
    #     """
    #     Find the index of the bin into which the value falls.
    #     Equivalent to numpy.digitize.
    #     """
    #     for idx, b in enumerate(bins):
    #         if value <= b:
    #             return idx
    #     return len(bins)

    def find_median_index(self, bins) -> int:
        """
        중앙값이 속하는 막대의 인덱스를 반환
        """

        # 중앙값 계산
        median_val: float = float(numpy.median(self.data))

        # 중앙값이 속하는 막대 인덱스 계산
        median_idx: int = int(numpy.digitize(median_val, bins)) - 1

        return median_idx

    # def custom_histogram(self):
    #     """
    #     numpy
    #     """
    #     min_val, max_val = min(self.data), max(self.data)
    #     bin_width = (max_val - min_val) / self.n_bins
    #     bins = [min_val + i * bin_width for i in range(self.n_bins + 1)]
    #     counts = [0] * self.n_bins

    #     for value in self.data:
    #         for i in range(self.n_bins):
    #             if bins[i] <= value < bins[i + 1]:
    #                 counts[i] += 1
    #                 break
    #         if value == max_val:  # Include the rightmost edge
    #             counts[-1] += 1

    #     return counts, bins

    def wheelEvent(self, event):
        """Override wheelEvent to propagate to the parent widget."""
        event.ignore()  # Ignore this event in FigureCanvas
        self.parent().wheelEvent(event)  # Pass the event to the parent widget


class SkillDpsRatioCanvas(FigureCanvas):

    def __init__(self, parent, data, skill_name):
        fig, self.ax = plt.subplots()
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)
        self.data = data
        self.skill_name = skill_name
        self.plot()

    def plot(self):
        # Data for the pie chart
        data = [i for i in self.data if i]
        labels = [
            f"{self.skill_name[i]}" for i, j in enumerate(self.data) if j and i != 6
        ]
        labels.append(f"평타")
        colors = [
            "#EF9A9A",
            "#90CAF9",
            "#A5D6A7",
            "#FFEB3B",
            "#CE93D8",
            "#F0B070",
            "#2196F3",
        ]

        # Plotting the pie chart
        wedges, texts, autotexts = self.ax.pie(
            data,
            labels=labels,
            colors=colors[: len(labels)],
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={"width": 0.7, "edgecolor": "#F8F8F8", "linewidth": 2},
            # textprops={"verticalalignment": "center"},
            pctdistance=0.65,
        )

        # Customizing the plot
        self.ax.set_title("스킬 비율", fontsize=14)

        # Adjust text size
        for text in texts:
            text.set_fontsize(10)

        self.draw()

    def wheelEvent(self, event):
        """Override wheelEvent to propagate to the parent widget."""
        event.ignore()  # Ignore this event in FigureCanvas
        self.parent().wheelEvent(event)  # Pass the event to the parent widget


class DMGCanvas(FigureCanvas):

    def __init__(self, parent, data, canvas_type):
        fig, self.ax = plt.subplots()
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)
        self.data = data
        self.canvas_type = canvas_type
        self.plot()

    def plot(self):
        (self.line1,) = self.ax.plot(
            self.data["time"],
            self.data["max"],
            label="최대",
            color="#F38181",
            linewidth=1,
        )
        (self.line2,) = self.ax.plot(
            self.data["time"],
            self.data["mean"],
            label="평균",
            color="#70AAF9",
            linewidth=1,
        )
        (self.line3,) = self.ax.plot(
            self.data["time"],
            self.data["min"],
            label="최소",
            color="#80C080",
            linewidth=1,
        )

        if self.canvas_type == "time":
            self.ax.set_title("시간 경과에 따른 피해량")
            # self.ax.set_ylabel("피해량", rotation=0, labelpad=20)
        else:
            self.ax.set_title("누적 피해량")
            # self.ax.set_ylabel("피해량", rotation=0, labelpad=20)

        self.ax.set_xlabel("시간 (초)")
        self.ax.grid(True, linestyle="--")  # 격자를 점선으로 변경
        self.ax.set_ylim(bottom=0)  # y축 범위를 0부터 시작하도록 설정
        self.ax.set_xlim(left=0, right=60)  # x축 범위를 0부터 시작하도록 설정
        self.ax.legend()

        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)

        self.ax.set_facecolor("#F8F8F8")

        # Interactive annotations
        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(-24, 10),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round,pad=0.3", fc="white", ec="black", lw=1, alpha=0.5
            ),
        )
        self.annotation.set_visible(False)

        # Connect the hover event
        self.mpl_connect("motion_notify_event", self.on_hover)
        self.mpl_connect("figure_leave_event", self.on_figure_leave)

    def on_hover(self, event):
        if event.inaxes == self.ax:
            x, y = event.xdata, event.ydata
            index = abs(self.data["time"] - x).argmin()
            closest_x = self.data["time"][index]
            max_val = self.data["max"][index]
            mean_val = self.data["mean"][index]
            min_val = self.data["min"][index]

            self.annotation.xy = (x, y)
            self.annotation.set_text(
                f"시간: {closest_x:.1f}\n최대: {max_val:.1f}\n평균: {mean_val:.1f}\n최소: {min_val:.1f}"
            )
            self.annotation.set_visible(True)
            self.draw()
        else:
            self.annotation.set_visible(False)
            self.draw()

    def on_figure_leave(self, event):
        self.annotation.set_visible(False)
        self.draw()

    def wheelEvent(self, event):
        """Override wheelEvent to propagate to the parent widget."""
        event.ignore()  # Ignore this event in FigureCanvas
        self.parent().wheelEvent(event)  # Pass the event to the parent widget


class SkillContributionCanvas(FigureCanvas):

    def __init__(self, parent, data, names):
        fig, self.ax = plt.subplots(figsize=(8, 6))  # 명시적 크기 설정
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)

        # 캔버스 크기 설정
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        self.data = data
        self.skill_names = names.copy()

        self.plot()

    def plot(self):
        colors = [
            "#EF9A9A",
            "#90CAF9",
            "#A5D6A7",
            "#FFEB3B",
            "#CE93D8",
            "#F0B070",
            "#2196F3",
        ]

        data_normLast = [i[-1] for i in self.data["skills_normalized"]]

        # 데미지가 0인 스킬 제거
        data_0idx = [i for i, j in enumerate(data_normLast) if not j]
        data_0idx.sort(reverse=True)

        for i in data_0idx:
            self.data["skills_normalized"].pop(i)
            self.data["skills_sum"].pop(i)
            self.skill_names.pop(i)

        self.skill_names.append("평타")

        self.skillCount = len(self.data["skills_normalized"])
        self.lines = []
        for i in reversed(range(self.skillCount)):
            (line,) = self.ax.plot(
                self.data["time"],
                self.data["skills_sum"][i],
                label=self.skill_names[i],
                color=colors[i],
                linewidth=2,
            )
            self.lines.append(line)

        # 영역 채우기
        for i in range(1, self.skillCount):
            self.ax.fill_between(
                self.data["time"],
                self.data["skills_sum"][i - 1],
                self.data["skills_sum"][i],
                color=colors[i],
            )  # 바로 위 선의 색상 사용

        # 맨 아래 영역 채우기
        self.ax.fill_between(
            self.data["time"], 0, self.data["skills_sum"][0], color=colors[0]
        )

        self.ax.set_title("스킬별 기여도")
        self.ax.set_xlabel("시간 (초)")
        self.ax.grid(True, linestyle="--")
        self.ax.set_ylim(0, 1)  # y축 범위를 0부터 1로 설정
        self.ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        self.ax.set_xlim(left=0, right=60)  # x축 범위를 0부터 60으로 설정
        self.ax.legend()

        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)

        self.ax.set_facecolor("#F8F8F8")

        # Interactive annotations
        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(-24, 10),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round,pad=0.3", fc="white", ec="black", lw=1, alpha=0.5
            ),
        )
        self.annotation.set_visible(False)

        # Connect the hover event
        self.mpl_connect("motion_notify_event", self.on_hover)
        self.mpl_connect("figure_leave_event", self.on_figure_leave)

    def on_hover(self, event):
        if event.inaxes == self.ax:
            x, y = event.xdata, event.ydata
            self.annotation.xy = (x, y)

            index = abs(self.data["time"] - x).argmin()
            closest_x = self.data["time"][index]

            values = []
            for i in reversed(range(self.skillCount)):
                values.append(
                    f"{self.skill_names[i]}: {self.data["skills_normalized"][i][index] * 100:.1f}%"
                )

            self.annotation.set_text(f"시간: {closest_x:.1f}\n\n" + "\n".join(values))

            self.annotation.set_visible(True)
            self.draw()
        else:
            self.annotation.set_visible(False)
            self.draw()

    def on_figure_leave(self, event):
        self.annotation.set_visible(False)
        self.draw()

    def wheelEvent(self, event):
        """Override wheelEvent to propagate to the parent widget."""
        event.ignore()  # Ignore this event in FigureCanvas
        self.parent().wheelEvent(event)  # Pass the event to the parent widget
