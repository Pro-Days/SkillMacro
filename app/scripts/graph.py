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
        """
        히스토그램 그래프 그리기
        """

        # 막대 개수
        self.n_bins = 15

        # 히스토그램 데이터 생성
        self.counts, self.bins = numpy.histogram(self.data, bins=self.n_bins)
        # counts, bins = self.custom_histogram()

        # 성능 최적화를 위한 bin 너비 미리 계산
        self.bin_width_calc: float = self.bins[1] - self.bins[0]

        # 막대 그래프 그리기
        self.bars: list = self.ax.bar(
            self.bins[:-1],
            self.counts,
            width=0.9 * self.bin_width_calc,
            align="edge",
            bottom=0,
        )

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

        # 중앙값 막대 인덱스 찾기
        self.median_idx: int = self.find_median_index(self.bins)
        # 중앙 5개 막대 시작 인덱스 설정
        self.center_start = 5

        # 색상 설정
        self.cursor_color = "#BAD0FD"

        # 인덱스에 따라 색 미리 설정
        self.colors: dict = {bar: "#F38181" for bar in self.bars}

        # 중앙값 막대 색 설정
        self.colors[self.bars[self.median_idx]] = "#4070FF"

        # 중앙 5개 막대 색 설정
        for i in range(self.center_start, self.center_start + 5):
            self.colors[self.bars[i]] = "#75A2FC"

        # 막대 색 설정
        for bar in self.bars:
            bar.set_facecolor(self.colors[bar])

        # 세부 정보 주석
        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(-24, 10),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round,pad=0.3", fc="white", ec="black", lw=1, alpha=0.5
            ),
            # arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        )

        # 처음에는 안보이게
        self.annotation.set_visible(False)

        # 호버된 막대
        self.bar_in_hover = None

        # 마우스 호버 이벤트 연결
        self.mpl_connect("motion_notify_event", self.on_hover)
        self.mpl_connect("figure_leave_event", self.on_figure_leave)

        # 그래프 업데이트
        self.draw()

    # 마우스 이동 시 주석 업데이트
    def on_hover(self, event) -> None:
        # 상태 변경 추적을 위한 플래그
        needs_update = False

        # 마우스가 그래프 밖에 있으면
        if event.inaxes != self.ax:
            # 호버된 막대가 있었다면 색 복원
            if self.bar_in_hover is not None:
                self.bar_in_hover.set_facecolor(self.colors[self.bar_in_hover])
                self.bar_in_hover = None

                needs_update = True

            # 주석이 보이고 있다면 숨기기
            if self.annotation._visible:
                self.annotation.set_visible(False)

                needs_update = True

            # 변경사항이 있으면 그래프 업데이트
            if needs_update:
                self.draw()

            return

        # 마우스가 그래프 안에 있으면
        hovered_bar = None
        hovered_index = -1

        # x 좌표 기반으로 먼저 대략적인 인덱스 추정
        if event.xdata is not None:
            # x 좌표로부터 bin 인덱스 추정
            estimated_idx = int(
                (event.xdata - self.bins[0]) / (self.bins[1] - self.bins[0])
            )
            estimated_idx: int = max(0, min(estimated_idx, len(self.bars) - 1))

            # 추정된 인덱스 주변의 막대들만 확인 (±2 범위)
            search_range = range(
                max(0, estimated_idx - 2), min(len(self.bars), estimated_idx + 3)
            )

            for i in search_range:
                if self.bars[i].contains(event)[0]:
                    hovered_bar = self.bars[i]
                    hovered_index = i

                    break

        # 새로운 막대에 호버되었을 때만 처리
        if hovered_bar != self.bar_in_hover:
            # 이전 막대 색 복원
            if self.bar_in_hover is not None:
                self.bar_in_hover.set_facecolor(self.colors[self.bar_in_hover])

            # 새 막대에 호버된 경우
            if hovered_bar is not None:
                # 막대 색 변경
                hovered_bar.set_facecolor(self.cursor_color)

                # 주석 업데이트
                bin_val = self.bins[hovered_index]
                count_val = self.counts[hovered_index]

                self.annotation.xy = (event.xdata, event.ydata)
                self.annotation.set_text(
                    f"상한 {bin_val + (self.bins[1]-self.bins[0]):,.1f}\n하한 {bin_val:,.1f}\n횟수 {int(count_val):,}"
                )

                if not self.annotation._visible:
                    self.annotation.set_visible(True)

            else:
                # 막대 위에 없으면 주석 숨기기
                if self.annotation._visible:
                    self.annotation.set_visible(False)

            # 호버된 막대 업데이트
            self.bar_in_hover = hovered_bar

            needs_update = True

        # 주석 위치는 항상 마우스를 따라가도록 업데이트 (부드러운 움직임)
        if (
            hovered_bar is not None
            and event.xdata is not None
            and event.ydata is not None
        ):
            if self.annotation._visible:
                self.annotation.xy = (event.xdata, event.ydata)
                # 주석 위치 업데이트는 항상 수행하여 부드러운 움직임 제공
                needs_update = True

        # 변경사항이 있을 때만 그래프 업데이트
        if needs_update:
            self.draw()

    def on_figure_leave(self, event) -> None:
        """
        마우스가 그래프 밖으로 나갔을 때
        """

        # 업데이트할게 없으면 리턴
        if self.bar_in_hover is None and not self.annotation._visible:
            return

        # 주석 숨기기
        if self.annotation._visible:
            self.annotation.set_visible(False)

        # 호버된 막대 색 복원
        if self.bar_in_hover is not None:
            self.bar_in_hover.set_facecolor(self.colors[self.bar_in_hover])

            # 호버된 막대 인덱스 초기화
            self.bar_in_hover = None

        self.draw()

    def find_median_index(self, bins) -> int:
        """
        중앙값이 속하는 막대의 인덱스를 반환
        """

        # 중앙값 계산
        median_val: float = float(numpy.median(self.data))

        # 중앙값이 속하는 막대 인덱스 계산
        median_idx: int = int(numpy.digitize(median_val, bins)) - 1

        return median_idx

    def wheelEvent(self, event) -> None:
        """
        부모 위젯으로 이벤트 전달
        """

        # 이 위젯의 이벤트 무시
        event.ignore()

        # 부모 위젯으로 이벤트 전달
        self.parent().wheelEvent(event)


class SkillDpsRatioCanvas(FigureCanvas):
    def __init__(
        self, parent: QWidget, data: list[float], skill_names: list[str]
    ) -> None:
        # init
        fig, self.ax = plt.subplots()
        super().__init__(fig)

        # 배경색 설정
        fig.set_facecolor("#F8F8F8")

        # 부모 위젯 설정
        self.setParent(parent)

        # 데이터 저장
        self.data = data
        self.skill_names: list[str] = skill_names

        # 그래프 그리기
        self.plot()

    def plot(self) -> None:
        # 데이터가 0인 스킬 제거
        data: list[float] = [i for i in self.data if i]

        # 레이블 설정
        labels: list[str] = [
            f"{self.skill_names[i]}" for i, j in enumerate(self.data) if j and i != 6
        ] + ["평타"]

        # colors 설정: 나중에 색 추가해야함
        colors: list[str] = [
            "#EF9A9A",
            "#90CAF9",
            "#A5D6A7",
            "#FFEB3B",
            "#CE93D8",
            "#F0B070",
            "#2196F3",
        ]

        # 파이 차트 그리기
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

        # 타이틀 설정
        self.ax.set_title("스킬 비율", fontsize=14)

        # 텍스트 크기 조정
        for text in texts:
            text.set_fontsize(10)

        self.draw()

    def wheelEvent(self, event) -> None:
        """
        부모 위젯으로 이벤트 전달
        """

        # 이 위젯의 이벤트 무시
        event.ignore()

        # 부모 위젯으로 이벤트 전달
        self.parent().wheelEvent(event)


class DMGCanvas(FigureCanvas):
    def __init__(self, parent: QWidget, data: dict, title: str) -> None:
        # init
        fig, self.ax = plt.subplots()
        super().__init__(fig)

        # 배경색 설정
        fig.set_facecolor("#F8F8F8")

        # 부모 위젯 설정
        self.setParent(parent)

        # 데이터 저장
        self.data: dict[str, list[float]] = data
        self.title: str = title

        # 그래프 그리기
        self.plot()

    def plot(self) -> None:
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

        # 타이틀 설정
        self.ax.set_title(self.title)
        # self.ax.set_ylabel("피해량", rotation=0, labelpad=20)

        # x축 레이블 설정
        self.ax.set_xlabel("시간 (초)")

        # 격자를 점선으로 변경
        self.ax.grid(True, linestyle="--")

        # y축 범위를 0부터 시작하도록 설정
        self.ax.set_ylim(bottom=0)

        # x축 범위를 0~60으로 설정
        self.ax.set_xlim(left=-0.5, right=60.5)

        # 범례 표시
        self.ax.legend()

        # 테두리 제거
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)

        # 배경색 설정
        self.ax.set_facecolor("#F8F8F8")

        # 세로 선 설정 (호버 시 표시될 세로선)
        self.vline = self.ax.axvline(
            x=0, color="gray", linestyle="--", alpha=0.7, visible=False
        )

        # 데이터 포인트들 설정 (호버 시 표시될 점들)
        self.data_points = []
        colors: list[str] = ["#F38181", "#70AAF9", "#80C080"]  # max, mean, min 순서
        for i, color in enumerate(colors):
            (point,) = self.ax.plot(
                [],
                [],
                "o",
                color=color,
                markersize=6,
                visible=False,
                zorder=10,
            )
            self.data_points.append(point)

        # 주석 설정
        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, -20),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round,pad=0.3", fc="white", ec="black", lw=1, alpha=0.5
            ),
        )
        # 처음에는 안보이게
        self.annotation.set_visible(False)

        # 호버 이벤트 연결
        self.mpl_connect("motion_notify_event", self.on_hover)
        self.mpl_connect("figure_leave_event", self.on_figure_leave)

    def on_hover(self, event) -> None:
        # 마우스가 그래프 밖에 있고 주석이 보이는 경우 숨기기
        # x, y 좌표가 None인 경우도 그래프 밖으로 간 것으로 간주
        if (event.inaxes != self.ax and self.annotation._visible) or (
            event.xdata is None or event.ydata is None
        ):
            self.annotation.set_visible(False)
            self.vline.set_visible(False)
            for point in self.data_points:
                point.set_visible(False)

            self.draw()
            return

        # 마우스가 그래프 안에 있으면
        if not self.annotation._visible:
            self.annotation.set_visible(True)

        # 좌표 가져오기
        x, y = event.xdata, event.ydata

        # 가장 가까운 x 좌표 찾기
        index: int = round(x)
        closest_x: float = self.data["time"][index]

        # 해당 x 좌표에서 y 값 가져오기
        max_val: float = self.data["max"][index]
        mean_val: float = self.data["mean"][index]
        min_val: float = self.data["min"][index]

        # 세로선 업데이트
        self.vline.set_xdata([closest_x, closest_x])
        self.vline.set_visible(True)

        # 데이터 포인트들 업데이트
        y_values: list[float] = [max_val, mean_val, min_val]
        for i, (point, y_val) in enumerate(zip(self.data_points, y_values)):
            # 데이터 설정 및 표시
            point.set_data([closest_x], [y_val])
            point.set_visible(True)

        # 주석 업데이트
        # 텍스트를 먼저 설정
        self.annotation.set_text(
            f"시간 {closest_x:.1f}\n최대 {max_val:,.1f}\n평균 {mean_val:,.1f}\n최소 {min_val:,.1f}"
        )

        # 주석 위치 설정
        self.annotation.xy = (x, y)

        self.draw()

    def on_figure_leave(self, event) -> None:
        # 주석, 세로선, 데이터 포인트 숨기기
        if self.annotation._visible:
            self.annotation.set_visible(False)

            self.vline.set_visible(False)

            for point in self.data_points:
                point.set_visible(False)

            self.draw()

    def wheelEvent(self, event) -> None:
        """
        부모 위젯으로 이벤트 전달
        """

        # 이 위젯의 이벤트 무시
        event.ignore()

        # 부모 위젯으로 이벤트 전달
        self.parent().wheelEvent(event)


class SkillContributionCanvas(FigureCanvas):
    def __init__(self, parent: QWidget, data: dict, names: list[str]) -> None:
        # init
        fig, self.ax = plt.subplots(figsize=(8, 6))
        super().__init__(fig)

        # 배경색 설정
        fig.set_facecolor("#F8F8F8")

        # 부모 위젯 설정
        self.setParent(parent)

        # 캔버스 크기 설정
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        # 데이터 저장
        self.data: dict[str, list[list[float]]] = data
        self.skill_names: list[str] = names.copy()

        # 그래프 그리기
        self.plot()

    def plot(self) -> None:
        # 색 설정: 나중에 색 추가해야함
        colors: list[str] = [
            "#EF9A9A",
            "#90CAF9",
            "#A5D6A7",
            "#FFEB3B",
            "#CE93D8",
            "#F0B070",
            "#2196F3",
        ]

        # 데미지가 0인 스킬 제거
        # 데이터의 마지막 값만 저장
        data_normLast: list[float] = [i[-1] for i in self.data["skills_normalized"]]

        # 데미지가 0인 스킬 인덱스 저장
        data_0idx: list[int] = [i for i, j in enumerate(data_normLast) if not j]
        # 정렬
        data_0idx.sort(reverse=True)

        # 데이터가 꼬이지 않도록 뒤에서부터 제거
        for i in data_0idx:  # 코드 최적화 필요
            self.data["skills_normalized"].pop(i)
            self.data["skills_sum"].pop(i)
            self.skill_names.pop(i)

        # 평타 추가
        self.skill_names.append("평타")

        # 스킬 개수
        self.skillCount: int = len(self.data["skills_normalized"])

        # 선 그리기
        self.lines = []
        for i in range(self.skillCount - 1, -1, -1):
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

        # 타이틀 및 레이블 설정
        self.ax.set_title("스킬별 기여도")
        self.ax.set_xlabel("시간 (초)")

        # 격자를 점선으로 변경
        self.ax.grid(True, linestyle="--")
        # y축 범위를 0부터 1로 설정
        self.ax.set_ylim(0, 1)
        # y축 레이블 포맷 설정
        self.ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        # x축 범위를 0부터 60으로 설정
        self.ax.set_xlim(left=-0.5, right=60.5)

        # 범례 표시
        self.ax.legend()

        # 테두리 제거
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)

        # 배경색 설정
        self.ax.set_facecolor("#F8F8F8")

        # 세로 선 설정 (호버 시 표시될 세로선)
        self.vline = self.ax.axvline(
            x=0, color="gray", linestyle="--", alpha=0.7, visible=False
        )

        # 데이터 포인트들 설정 (호버 시 표시될 점들)
        self.data_points = []
        for i, color in enumerate(colors[: self.skillCount - 1]):
            (point,) = self.ax.plot(
                [],
                [],
                "o",
                color=color,
                markeredgecolor="gray",
                markeredgewidth=0.5,
                markersize=6,
                visible=False,
                zorder=10,
            )
            self.data_points.append(point)

        # 주석 설정
        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, -20),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round,pad=0.3", fc="white", ec="black", lw=1, alpha=0.5
            ),
        )
        # 처음에는 안보이게
        self.annotation.set_visible(False)

        # 호버 이벤트 연결
        self.mpl_connect("motion_notify_event", self.on_hover)
        self.mpl_connect("figure_leave_event", self.on_figure_leave)

    def on_hover(self, event) -> None:
        # 마우스가 그래프 밖에 있고 주석이 보이는 경우 숨기기
        # x, y 좌표가 None인 경우도 그래프 밖으로 간 것으로 간주
        if (event.inaxes != self.ax and self.annotation._visible) or (
            event.xdata is None or event.ydata is None
        ):
            self.annotation.set_visible(False)
            self.vline.set_visible(False)
            for point in self.data_points:
                point.set_visible(False)

            self.draw()
            return

        # 마우스가 그래프 안에 있으면
        if not self.annotation._visible:
            self.annotation.set_visible(True)

        # 좌표 가져오기
        x, y = event.xdata, event.ydata

        # 가장 가까운 x 좌표 찾기
        index: int = round(x)
        closest_x: list[float] = self.data["time"][index]

        # 세로선 업데이트
        self.vline.set_xdata([closest_x, closest_x])
        self.vline.set_visible(True)

        # 데이터 포인트들 업데이트
        y_values: list[float] = [
            self.data["skills_sum"][i][index] for i in range(self.skillCount)
        ]
        for i, (point, y_val) in enumerate(zip(self.data_points, y_values)):
            # 데이터 설정 및 표시
            point.set_data([closest_x], [y_val])
            point.set_visible(True)

        values = []
        for i in reversed(range(self.skillCount)):
            values.append(
                f"{self.skill_names[i]} {self.data["skills_normalized"][i][index] * 100:.1f}%"
            )

        # 인덱스가 바뀌었을 때만 텍스트 업데이트
        self.annotation.set_text(f"시간 {closest_x:.1f}\n\n" + "\n".join(values))

        # 주석 위치 설정
        self.annotation.xy = (x, y)

        self.draw()

    def on_figure_leave(self, event) -> None:
        # 주석, 세로선, 데이터 포인트 숨기기
        if self.annotation._visible:
            self.annotation.set_visible(False)

            self.vline.set_visible(False)

            for point in self.data_points:
                point.set_visible(False)

            self.draw()

    def wheelEvent(self, event) -> None:
        """
        부모 위젯으로 이벤트 전달
        """

        # 이 위젯의 이벤트 무시
        event.ignore()

        # 부모 위젯으로 이벤트 전달
        self.parent().wheelEvent(event)
