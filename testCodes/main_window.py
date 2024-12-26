from PyQt6.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget
from graph import SkillContributionCanvas
import numpy as np
import sys


def moving_average(data, window_size):
    window = np.ones(window_size) / window_size
    return np.convolve(data, window, mode="same")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("스킬 기여도 그래프")

        # 5개의 스킬에 대한 데이터 생성
        time = np.linspace(0, 60, 121)
        num_skills = 6
        data_raw = np.random.rand(num_skills, 121)  # 5x100 랜덤 데이터

        def moving_average(data, window_size):
            window = np.ones(window_size) / window_size
            return np.convolve(data, window, mode="same")

        # 이동 평균을 사용하여 데이터 스무딩
        window_size = 11  # 윈도우 크기 (홀수를 사용하는 것이 좋음)
        smoothed_data = np.array([moving_average(row, window_size) for row in data_raw])

        # 각 시점에서 합이 1이 되도록 정규화
        data_normalized = smoothed_data / smoothed_data.sum(axis=0)
        # 누적 합 계산
        data_cumsum = np.cumsum(data_normalized, axis=0)

        # 데이터 딕셔너리 생성
        data = {
            "time": time,
            "skill1": data_normalized[0],
            "skill2": data_normalized[1],
            "skill3": data_normalized[2],
            "skill4": data_normalized[3],
            "skill5": data_normalized[4],
            "skill6": data_normalized[5],
            "skill1_sum": data_normalized[0],
            "skill2_sum": data_cumsum[0],
            "skill3_sum": data_cumsum[1],
            "skill4_sum": data_cumsum[2],
            "skill5_sum": data_cumsum[3],
            "skill6_sum": data_cumsum[4],
        }

        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 그래프 캔버스 추가
        canvas = SkillContributionCanvas(self, data)
        layout.addWidget(canvas)

        self.resize(800, 600)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
