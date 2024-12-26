import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

# 한글 폰트 설정
plt.rcParams["font.family"] = "Malgun Gothic"  # 원하는 한글 폰트로 변경 가능
plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지


class SkillContributionCanvas(FigureCanvas):

    def __init__(self, parent, data):
        fig, self.ax = plt.subplots(figsize=(8, 6))  # 명시적 크기 설정
        fig.set_facecolor("#F8F8F8")
        super().__init__(fig)
        self.setParent(parent)

        # 캔버스 크기 설정
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        self.data = data

        # 여백 조정
        plt.tight_layout()

        self.plot()

    def plot(self):
        colors = ["#F38181", "#70AAF9", "#80C080", "#FCE38A", "#95E1D3", "#F4A259"]
        skill_names = ["스킬1", "스킬2", "스킬3", "스킬4", "스킬5", "스킬6"]

        self.lines = []
        for i, skill in enumerate(
            [
                "skill1_sum",
                "skill2_sum",
                "skill3_sum",
                "skill4_sum",
                "skill5_sum",
                "skill6_sum",
            ]
        ):
            (line,) = self.ax.plot(
                self.data["time"],
                self.data[skill],
                label=skill_names[i],
                color=colors[i],
                linewidth=2,
            )
            self.lines.append(line)

        # 영역 채우기
        for i in range(5, 0, -1):  # 4부터 1까지 역순으로
            self.ax.fill_between(
                self.data["time"],
                self.data[f"skill{i}_sum"],
                self.data[f"skill{i+1}_sum"],
                color=colors[i - 1],
            )  # 바로 위 선의 색상 사용

        # 맨 아래 영역 채우기
        self.ax.fill_between(
            self.data["time"], 0, self.data["skill1_sum"], color=colors[0]
        )
        self.ax.fill_between(
            self.data["time"], self.data["skill6_sum"], 1, color=colors[5]
        )

        self.ax.set_title("스킬별 기여도")
        self.ax.set_ylabel("기여도")
        self.ax.set_xlabel("시간 (초)")
        self.ax.grid(True, linestyle="--")
        self.ax.set_ylim(0, 1)  # y축 범위를 0부터 1로 설정
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
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1),
        )
        self.annotation.set_visible(False)

        # Connect the hover event
        self.mpl_connect("motion_notify_event", self.on_hover)

    def on_hover(self, event):
        if event.inaxes == self.ax:
            x, y = event.xdata, event.ydata
            index = np.argmin(np.abs(self.data["time"] - x))
            closest_x = self.data["time"][index]

            values = []
            for name, skill in [
                ("스킬1", "skill1"),
                ("스킬2", "skill2"),
                ("스킬3", "skill3"),
                ("스킬4", "skill4"),
                ("스킬5", "skill5"),
                ("스킬6", "skill6"),
            ]:
                values.append(f"{name}: {self.data[skill][index] * 100:.1f}%")

            self.annotation.xy = (x, y)
            self.annotation.set_text(f"시간: {closest_x:.1f}\n" + "\n".join(values))
            self.annotation.set_visible(True)
            self.draw_idle()
        else:
            self.annotation.set_visible(False)
            self.draw_idle()
