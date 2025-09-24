import pyqtgraph as pg
import math

from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtGui import QBrush, QPainter, QFont

from .custom_classes import CustomFont


class DpsDistributionCanvas(pg.PlotWidget):
    def __init__(self, parent: QWidget, data: list[float]) -> None:
        super().__init__(parent=parent)

        # 데이터 저장
        self.data: list[float] = data

        # 안티 에일리어싱 활성화
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # PyQtGraph 전역 안티 에일리어싱 설정
        pg.setConfigOptions(antialias=True)

        # 막대의 개수 설정
        self.num_bins = 15

        # BarGraphItem 객체들을 저장할 리스트
        self.bars: list[None | pg.BarGraphItem] = []

        # 그리드 보이지 않도록 설정
        self.showGrid(x=False, y=False)

        # 제목 설정
        self.setLabel("top", "DPM 분포")

        # 축 숨기기 (제목은 표시)
        self.getAxis("top").setStyle(showValues=False, tickLength=20)
        # 축 선 숨기기
        self.getAxis("top").setPen(None)

        # 제목 폰트 설정
        font = CustomFont(14)
        self.getAxis("top").label.setFont(font)
        # 제목 색상을 검정색으로 설정
        self.getAxis("top").setTextPen("black")

        # 축 설정
        # 아래쪽 축
        axis_bottom: pg.AxisItem = self.getAxis("bottom")
        axis_bottom.setStyle(showValues=True, tickLength=10)

        # 축 폰트 설정
        axis_font = CustomFont(10)
        axis_bottom.setStyle(tickFont=axis_font)
        # 축 라벨 색상을 검정색으로 설정
        axis_bottom.setTextPen("black")

        # self.getAxis("bottom").setStyle(showValues=True, tickAlpha=0)
        # self.getAxis("left").setStyle(showValues=True, tickLength=-20)
        # 왼쪽 축 숨기기
        self.getAxis("left").setVisible(False)

        # 마우스 상호작용 비활성화 (드래그, 줌, 우클릭 메뉴 등)
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)

        # 배경 색상 설정
        self.setBackground("#F8F8F8")

        # 테두리 색상 설정
        self.setStyleSheet("border: 0px solid;")

        # 색상 정의
        self.colors: dict[str, str] = {
            "median": "#4070FF",
            "centers": "#75A2FC",
            "hover": "#BAD0FD",
            "normal": "#F38181",
        }

        # 각 막대의 원래 색상을 저장할 리스트
        self.original_bar_colors: list[str] = []

        # 툴팁 레이블 설정
        self.tooltip_label = QLabel(self)

        # 플래그 설정
        # self.tooltip_label.setWindowFlags(Qt.WindowType.ToolTip)
        # 투명도 설정 (0.0~1.0, 1.0이 완전 불투명)
        # self.tooltip_label.setWindowOpacity(0.8)

        # 스타일 시트 설정 (테두리 제거하고 배경만 사용)
        self.tooltip_label.setStyleSheet(
            """QLabel {
                background-color: rgba(255, 255, 255, 0.8);
                padding: 5px;
                border: 1px solid gray;
                border-radius: 10px;
            }"""
        )
        self.tooltip_label.setFont(CustomFont(10))

        # 히스토그램 생성
        self.create_histogram()

        # 현재 호버 중인 막대의 인덱스를 저장
        self.hovered_bar_index: int = -1

        # 툴팁 라벨 숨김
        self.tooltip_label.hide()

        # 자동 범위 조정 버튼 비활성화
        self.hideButtons()

    def get_bar_color(self, bar_index: int) -> str:
        """
        주어진 인덱스의 막대의 기본 색상을 반환하는 헬퍼 함수
        """

        # 중앙 막대의 인덱스와 중앙 막대에서의 거리 계산
        median_idx: int = self.hist_counts.index(max(self.hist_counts))
        distance_from_center: int = abs(bar_index - (self.num_bins // 2))

        # 기본 색상 설정
        bar_color: str = self.colors["normal"]

        # 막대가 중앙 막대인 경우
        if bar_index == median_idx:
            bar_color = self.colors["median"]

        # 막대가 중앙 막대에서 2칸 이내인 경우
        elif distance_from_center <= 2:
            bar_color = self.colors["centers"]

        return bar_color

    def create_histogram(self) -> None:
        # 지정된 개수의 막대로 히스토그램 생성
        self.hist_counts, self.bin_edges, self.bin_width = self.custom_histogram(
            data=self.data, n_bins=self.num_bins
        )

        # 각 막대의 중앙 위치 계산
        self.bin_centers: list[float] = [
            (self.bin_edges[i] + self.bin_edges[i + 1]) / 2
            for i in range(self.num_bins)
        ]

        # 막대의 패딩 설정
        self.padding: float = self.bin_width * 0.08

        for i in range(self.num_bins):
            # 각 막대의 x 위치와 y 높이 계산
            x: float = self.bin_centers[i]
            y: int = self.hist_counts[i]

            # 패딩을 적용한 너비 계산
            width_padded: float = self.bin_width - self.padding * 2

            # 초기 색상 설정 및 저장
            bar_color: str = self.get_bar_color(i)
            self.original_bar_colors.append(bar_color)

            # y가 0인 경우 막대를 그리지 않음
            if not y:
                self.bars.append(None)
                continue

            # BarGraphItem 생성 및 추가
            bar: pg.BarGraphItem = pg.BarGraphItem(
                x=[x],
                height=[y],
                width=[width_padded],
                brush=pg.mkBrush(bar_color),
                pen=None,  # 테두리 설정
            )
            self.addItem(bar)
            self.bars.append(bar)

        # ViewBox의 여백 제거
        self.getViewBox().setDefaultPadding(0.0)

        # x축 범위 설정
        self.setXRange(
            self.bin_edges[0] - self.padding,
            self.bin_edges[-1] + self.padding,
        )

    def redraw_bar(self, index: int, new_color: str) -> None:
        """
        특정 인덱스의 막대를 제거하고 새로운 색상으로 다시 그리는 함수
        """

        # 기존 막대 제거
        # 이 부분에서 "RuntimeError: wrapped C/C++ object of type BarGraphItem has been deleted"
        # 에러가 발생하는 듯함.
        self.removeItem(self.bars[index])

        # 새 막대 생성
        x: float = self.bin_centers[index]
        y: int = self.hist_counts[index]

        # 패딩을 적용한 너비 계산
        width_padded: float = self.bin_width - self.padding * 2

        # 새로운 BarGraphItem 생성
        new_bar: pg.BarGraphItem = pg.BarGraphItem(
            x=[x],
            height=[y],
            width=[width_padded],
            brush=pg.mkBrush(new_color),
            pen=None,  # 테두리 설정
        )
        self.addItem(new_bar)

        # 리스트의 해당 인덱스를 새 막대로 업데이트
        self.bars[index] = new_bar

    def mouseMoveEvent(self, event) -> None:  # type: ignore
        """
        마우스 이동 이벤트 핸들러
        """

        # 현재 마우스 위치 가져오기
        pos: QPoint = event.pos()

        # QPointF로 변환
        pos_f = QPointF(pos)

        for i in range(len(self.bars)):
            # bar가 None인 경우는 건너뜀
            if self.bars[i] is None:
                continue

            x_min: float = self.bin_edges[i]
            x_max: float = self.bin_edges[i + 1]
            y_max: int = self.hist_counts[i]

            # p1: 마우스 위치를 ViewBox 좌표로 변환
            p1: QPointF = self.getViewBox().mapSceneToView(pos_f)
            mouse_x: float = p1.x()
            mouse_y: float = p1.y()

            # 막대의 x 범위와 y 범위 내에 마우스가 있는지 확인
            # max(y_max, 5)는 y_max가 작은 경우에도 툴팁이 표시되도록 하기 위함
            if x_min <= mouse_x <= x_max and 0 <= mouse_y <= max(y_max, 5):
                # 이전에 호버된 막대가 있었다면 원래 색상으로 복원
                if self.hovered_bar_index != i and self.hovered_bar_index != -1:
                    self.redraw_bar(
                        index=self.hovered_bar_index,
                        new_color=self.original_bar_colors[self.hovered_bar_index],
                    )

                # 현재 막대를 호버 색상으로 변경
                if self.hovered_bar_index != i:
                    # 현재 막대를 호버 색상으로 변경
                    self.redraw_bar(index=i, new_color=self.colors["hover"])

                # 현재 호버된 막대 업데이트
                self.hovered_bar_index = i

                # 툴팁 라벨 업데이트
                self.tooltip_label.setText(
                    f"상한 {self.bin_edges[i+1]:,.1f}\n하한 {self.bin_edges[i]:,.1f}\n횟수 {self.hist_counts[i]}"
                )

                # 툴팁 라벨 크기 조정
                self.tooltip_label.adjustSize()

                # 툴팁 위치 조정
                global_pos: QPoint = event.globalPosition().toPoint()
                local_pos: QPoint = self.mapFromGlobal(global_pos)

                # 툴팁 위치 조정
                # 마우스가 중앙보다 왼쪽에 있는 경우
                if mouse_x <= self.bin_centers[self.num_bins // 2]:
                    self.tooltip_label.move(local_pos + QPoint(10, -38))
                else:
                    self.tooltip_label.move(
                        local_pos + QPoint(-self.tooltip_label.width() - 10, -38)
                    )

                # 툴팁 표시
                self.tooltip_label.show()

                # 툴팁을 맨 위로 올림
                self.tooltip_label.raise_()

                # 호버된 막대를 찾았으므로 루프 종료
                break

        else:
            # 루프가 끝났는데 호버된 막대가 없으면
            # 툴팁 라벨 숨김
            self.tooltip_label.hide()

            # 루프가 끝난 후, 이전에 호버된 막대가 있었는데 현재는 호버되지 않는 경우
            if self.hovered_bar_index != -1:
                self.redraw_bar(
                    self.hovered_bar_index,
                    self.original_bar_colors[self.hovered_bar_index],
                )

                # 호버 상태 해제
                self.hovered_bar_index = -1

        # 부모 클래스의 mouseMoveEvent 호출
        super().mouseMoveEvent(event)

        # ViewBox도 업데이트
        self.getViewBox().update()

    def custom_histogram(
        self, data: list[float], n_bins: int
    ) -> tuple[list[int], list[float], float]:
        """
        히스토그램 생성
        """

        # 최대, 최소 값 계산
        max_val: float = max(data)
        min_val: float = min(data)

        # 막대 너비 계산
        bin_width: float = (max_val - min_val) / n_bins

        # 막대의 경계값 계산
        # n_bins + 1을 하는 이유는 마지막 막대의 오른쪽 경계값을 포함하기 때문
        bin_edges: list[float] = [min_val + i * bin_width for i in range(n_bins + 1)]
        counts: list[int] = [0] * n_bins

        # 각 데이터를 해당 막대에 할당
        for value in data:
            for i in range(n_bins):
                # 각 막대의 경계값에 따라 해당 막대의 카운트를 증가시킴
                if bin_edges[i] <= value < bin_edges[i + 1]:
                    counts[i] += 1
                    break

            # 마지막 막대의 경우, 오른쪽 경계값이 포함되므로 따로 처리
            if value == max_val:
                counts[-1] += 1

        return counts, bin_edges, bin_width

    def wheelEvent(self, event) -> None:  # type: ignore
        """
        이 위젯의 wheelEvent를 부모 위젯으로 전달하는 메서드
        """

        # 이벤트 무시
        event.ignore()

        # 툴팁 라벨 숨김
        self.tooltip_label.hide()

        # 호버된 막대 색상 복원
        if self.hovered_bar_index != -1:
            self.redraw_bar(
                self.hovered_bar_index,
                self.original_bar_colors[self.hovered_bar_index],
            )

            # 호버 상태 해제
            self.hovered_bar_index = -1

        # 부모 위젯의 wheelEvent 호출
        self.parent().wheelEvent(event)  # type: ignore


class SkillDpsRatioCanvas(pg.PlotWidget):
    def __init__(
        self,
        parent: QWidget,
        data: list[float],
        skill_names: list[str],
    ) -> None:
        super().__init__(parent=parent)

        # 데이터와 레이블, 색상, 제목 설정
        # 존재하는 데이터만 필터링
        self.data: list[float] = [i for i in data if i]

        # 레이블은 스킬 이름에서 데이터가 있는 것만 필터링
        self.labels: list[str] = [
            f"{skill_names[i]}" for i, j in enumerate(data) if j and i != 6
        ]

        # 평타 추가
        self.labels.append(f"평타")

        # 색상 설정
        self.colors: list[str] = [
            "#EF9A9A",
            "#90CAF9",
            "#A5D6A7",
            "#FFEB3B",
            "#CE93D8",
            "#F0B070",
            "#2196F3",
        ]

        # PyQtGraph 위젯 생성
        # 원형 비율 유지
        self.setAspectLocked(True)

        # 안티 에일리어싱 활성화
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # PyQtGraph 전역 안티 에일리어싱 설정
        pg.setConfigOptions(antialias=True)

        # 축 숨기기
        self.hideAxis("left")
        self.hideAxis("bottom")

        # 제목 설정
        self.setLabel("top", "스킬 비율")

        # 축 숨기기 (제목은 표시)
        self.getAxis("top").setStyle(showValues=False)
        # 축 선 숨기기
        self.getAxis("top").setPen(None)

        # 제목 폰트 설정
        font = CustomFont(point_size=14)
        self.getAxis("top").label.setFont(font)
        # 제목 색상을 검정색으로 설정
        self.getAxis("top").setTextPen("black")

        # 배경 색상 설정
        self.background_color = "#F8F8F8"
        self.setBackground(self.background_color)

        # 테두리 색상 설정
        self.setStyleSheet("border: 0px solid;")

        # 마우스 상호작용 비활성화 (드래그, 줌, 우클릭 메뉴 등)
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)

        # 파이 차트 그리기
        self.create_interactive_pie_chart()

        # 자동 범위 조정 버튼 비활성화
        self.hideButtons()

    def create_interactive_pie_chart(self) -> None:
        # 각도 계산 (원래 비율대로 꽉 찬 원)
        total: float = sum(self.data)
        angles: list[float] = [360 * value / total for value in self.data]

        self.start_angle: float = -90.0

        # 시작 각도를 12시 방향(-90도)으로 설정
        start_angle: float = self.start_angle

        # 조각 아이템 초기화
        self.pie_items: list[pg.PlotCurveItem] = []

        # 1단계: 꽉 찬 파이 차트 그리기
        for i, (angle, label, color) in enumerate(
            zip(angles, self.labels, self.colors)
        ):
            # 파이 조각의 시작과 끝 각도 (시계방향 회전을 위해 각도를 음수로)
            start_rad: float = math.radians(-start_angle)
            end_rad: float = math.radians(-(start_angle + angle))

            theta_points: list[float] = []
            # 세밀한 곡선을 위해 0부터 100까지 101개 점 설정
            for j in range(101):
                t: float = start_rad + (end_rad - start_rad) * j / 100
                theta_points.append(t)

            # 도넛 차트를 위한 내부 반지름 설정
            # 내부 원의 반지름
            inner_radius: float = 0.4
            # 외부 원의 반지름
            outer_radius: float = 1.0

            x: list[float] = []
            y: list[float] = []

            # 외부 호 그리기 (시계방향)
            for t in theta_points:
                x.append(outer_radius * math.cos(t))
                y.append(outer_radius * math.sin(t))

            # 내부 호 그리기 (반시계방향으로 되돌아가기)
            for t in reversed(theta_points):
                x.append(inner_radius * math.cos(t))
                y.append(inner_radius * math.sin(t))

            # 첫 점으로 돌아가서 닫힌 도형 만들기
            if x:
                x.append(x[0])
                y.append(y[0])

            # 파이 조각 그리기 - 테두리 없이
            brush: QBrush = pg.mkBrush(color=color)

            # 조각 그리기
            curve = pg.PlotCurveItem(
                x, y, brush=brush, fillLevel="enclosed", antialias=True
            )
            self.addItem(curve)
            self.pie_items.append(curve)

            # 각 조각의 레이블 위치 계산 (도넛 중앙에 배치)
            mid_angle: float = math.radians(-(start_angle + angle / 2))
            # 내부와 외부 반지름의 중간 지점에 레이블 배치
            label_radius: float = (inner_radius + outer_radius) / 2
            label_x: float = label_radius * math.cos(mid_angle)
            label_y: float = label_radius * math.sin(mid_angle)

            # 퍼센트 계산
            percentage: float = round(100 * self.data[i] / total, 1)
            # 퍼센트 레이블 생성
            text_item: pg.TextItem = pg.TextItem(
                f"{percentage:.1f}%",
                anchor=(0.5, 0.5),
                color="black",
            )
            # 레이블 위치 설정
            text_item.setPos(label_x, label_y)
            # 폰트 설정
            font = CustomFont(10)
            text_item.setFont(font)
            self.addItem(text_item)

            # 범례 위치 설정 (외부 반지름 밖에 배치)
            legend_radius: float = outer_radius + 0.1
            legend_x: float = legend_radius * math.cos(mid_angle)
            legend_y: float = legend_radius * math.sin(mid_angle)

            # 범례를 위한 외부 레이블
            legend_item: pg.TextItem = pg.TextItem(
                label,
                anchor=(0.0 if legend_x >= 0 else 1.0, 0.5),
                color="black",
            )
            # 범례 레이블 위치 설정
            legend_item.setPos(legend_x, legend_y)
            # 범례 레이블 폰트 설정
            font = CustomFont(10)
            legend_item.setFont(font)
            self.addItem(legend_item)

            # 다음 조각의 시작 각도로 이동
            start_angle += angle

        # 간격을 만들기 위한 배경색 선 그리기
        # 간격 선의 두께
        gap_width: float = 4.0

        # 각도를 12시 방향(-90도)부터 시작
        start_angle = self.start_angle
        for i, angle in enumerate(angles):
            # 각 조각의 끝에서 다음 조각 시작까지 선 그리기 (시계방향)
            boundary_angle: float = start_angle + angle
            boundary_rad: float = math.radians(-boundary_angle)

            # 중심에서 외곽까지 선 그리기
            line_x: list[float] = [0.0, 1.1 * math.cos(boundary_rad)]
            line_y: list[float] = [0.0, 1.1 * math.sin(boundary_rad)]

            # 배경색 선 그리기
            gap_pen = pg.mkPen(color=self.background_color, width=gap_width)
            self.plot(line_x, line_y, pen=gap_pen)

            # 다음 조각의 시작 각도로 이동
            start_angle += angle

    def wheelEvent(self, event) -> None:  # type: ignore
        """
        이 위젯의 wheelEvent를 부모 위젯으로 전달하는 메서드
        """

        # 이벤트 무시
        event.ignore()

        # 부모 위젯의 wheelEvent 호출
        self.parent().wheelEvent(event)  # type: ignore


class DMGCanvas(pg.PlotWidget):
    def __init__(
        self,
        parent: QWidget,
        data: dict[str, list[int] | list[float]],
        title: str,
    ) -> None:
        super().__init__(parent)

        # 데이터와 레이블, 색상, 제목 설정
        self.data: dict[str, list[int] | list[float]] = data

        # 안티 에일리어싱 활성화
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # PyQtGraph 전역 안티 에일리어싱 설정
        pg.setConfigOptions(antialias=True)

        # 제목 설정
        self.setLabel("top", title)

        # 축 숨기기 (제목은 표시)
        self.getAxis("top").setStyle(showValues=False)
        # 축 선 숨기기
        self.getAxis("top").setPen(None)

        # 제목 폰트 설정
        font = CustomFont(point_size=14)
        self.getAxis("top").label.setFont(font)
        # 제목 색상을 검정색으로 설정
        self.getAxis("top").setTextPen("black")

        # 하단 축 텍스트 설정
        font_properties = {
            "font-size": "10pt",
            "font-family": "Noto Sans KR",
        }
        self.setLabel("bottom", "시간", units="초", **font_properties)

        # 하단 축 스타일 설정
        axis_bottom: pg.AxisItem = self.getAxis("bottom")
        # axis_bottom.setStyle(showValues=True, tickLength=10)

        # 축 폰트 설정
        axis_font = CustomFont(point_size=10)
        axis_bottom.setStyle(tickFont=axis_font)
        # 축 라벨 색상을 검정색으로 설정
        axis_bottom.setTextPen("black")

        # 좌측 축 설정 (Y축)
        axis_left: pg.AxisItem = self.getAxis("left")
        axis_left.setStyle(tickFont=axis_font)
        axis_left.setTextPen("black")
        # Y축 선 숨기기 (숫자는 표시하되 축 선은 숨김)
        axis_left.setPen(None)

        # 배경 색상 설정
        self.background_color = "#F8F8F8"
        self.setBackground(self.background_color)

        # 테두리 색상 설정
        self.setStyleSheet("border: 0px solid;")

        # 마우스 상호작용 비활성화 (드래그, 줌, 우클릭 메뉴 등)
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)

        # 자동 범위 조정 버튼 비활성화
        self.hideButtons()

        self.colors: dict[str, str] = {
            "max": "#F38181",
            "mean": "#70AAF9",
            "min": "#80C080",
        }

        # 선 그래프 그리기
        self.create_line_graph()

        # X축 그리드만 표시 (Y축 그리드는 숨김)
        self.showGrid(x=True, y=False, alpha=0.5)

        # ViewBox의 여백 제거
        self.getViewBox().setDefaultPadding(0.0)

        # X축 범위를 명시적으로 설정하여 0과 60이 모두 보이도록 함
        self.setXRange(-1, 61)

        # 데이터 최대값 계산
        self.max_value: float = max(self.data["max"])

        # Y축 범위 설정 (최대값에 따라 자동 조정)
        max_y: float = self.max_value * 1.1  # 최대값에 10% 여유 추가
        self.setYRange(0, max_y)

        self.set_ticks()

    def create_line_graph(self) -> None:
        # 데이터에서 시간, 최대, 평균, 최소 값 추출
        time = self.data["time"]
        max_data = self.data["max"]
        mean_data = self.data["mean"]
        min_data = self.data["min"]

        # 선 그래프 그리기
        self.plot(
            time, max_data, pen=pg.mkPen(self.colors["max"], width=2), name="최대"
        )
        self.plot(
            time, mean_data, pen=pg.mkPen(self.colors["mean"], width=2), name="평균"
        )
        self.plot(
            time, min_data, pen=pg.mkPen(self.colors["min"], width=2), name="최소"
        )

        # 범례 표시
        # self.addLegend()

        # 툴팁 선
        self.tooltip_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen("gray", width=2, style=Qt.PenStyle.DashLine),
        )
        self.addItem(self.tooltip_line)

        # 툴팁 점
        self.tooltip_point = pg.ScatterPlotItem(pen=pg.mkPen(None), size=8)
        self.addItem(self.tooltip_point)

        # 툴팁 레이블 설정
        self.tooltip_label = QLabel(parent=self)

        # 플래그 설정
        # self.tooltip_label.setWindowFlags(Qt.WindowType.ToolTip)
        # 투명도 설정 (0.0~1.0, 1.0이 완전 불투명)
        # self.tooltip_label.setWindowOpacity(0.5)

        # 스타일 시트 설정 (테두리 제거하고 배경만 사용)
        self.tooltip_label.setStyleSheet(
            """QLabel {
                background-color: rgba(255, 255, 255, 0.8);
                padding: 5px;
                border: 1px solid gray;
                border-radius: 10px;
            }"""
        )
        # 폰트 설정
        self.tooltip_label.setFont(CustomFont(point_size=10))

        # 처음에는 숨김
        self.tooltip_line.hide()
        self.tooltip_point.hide()
        self.tooltip_label.hide()

    def set_ticks(self) -> None:
        # x축 눈금 설정 (0부터 60까지 10 간격)
        bottom_axis: pg.AxisItem = self.getAxis("bottom")
        bottom_axis.setTicks([[(i, f"{i}초") for i in range(0, 61, 10)]])

        # 눈금 펜 설정
        bottom_axis.setTickPen(pg.mkPen("gray", width=2, style=Qt.PenStyle.DashLine))

    def mouseMoveEvent(self, event) -> None:  # type: ignore
        """
        마우스 이동 이벤트 핸들러
        """

        # 현재 마우스 위치 가져오기
        pos: QPoint = event.pos()

        # QpointF로 변환
        pos_f: QPointF = QPointF(pos)

        # ViewBox 좌표로 변환
        pos_converted: QPointF = self.getViewBox().mapSceneToView(pos_f)

        # x, y 좌표 추출
        x: float = pos_converted.x()
        y: float = pos_converted.y()

        # 데이터 인덱스 계산
        time = int(x + 0.5)

        # 마우스가 X축 범위 내에 있는지 확인
        if 0 <= time <= 60 and x >= -0.5 and 0 <= y <= self.max_value * 1.1:
            # 툴팁 선 위치 설정
            self.tooltip_line.setPos(x)
            self.tooltip_line.show()

            # 툴팁 레이블 위치 및 내용 설정
            self.tooltip_label.setText(
                f"시간: {time}초\n최대: {self.data['max'][time]:,.1f}\n평균: {self.data['mean'][time]:,.1f}\n최소: {self.data['min'][time]:,.1f}"
            )
            global_pos = event.globalPosition().toPoint()
            local_pos = self.mapFromGlobal(global_pos)

            self.tooltip_label.adjustSize()

            # 툴팁 위치 조정
            if x <= 30:
                self.tooltip_label.move(local_pos + QPoint(15, -30))
            else:
                self.tooltip_label.move(
                    local_pos - QPoint(self.tooltip_label.width() + 15, 30)
                )

            # 툴팁을 맨 위로 올림
            self.tooltip_label.raise_()

            self.tooltip_label.show()

            # 툴팁 점 위치 설정 (실제 데이터 포인트들)
            points_data = [
                [time, self.data["max"][time]],
                [time, self.data["mean"][time]],
                [time, self.data["min"][time]],
            ]
            self.tooltip_point.setData(
                pos=points_data,
                brush=[self.colors["max"], self.colors["mean"], self.colors["min"]],
            )
            self.tooltip_point.show()

        # 범위를 벗어난 경우 툴팁 숨김
        else:
            self.tooltip_line.hide()
            self.tooltip_label.hide()
            self.tooltip_point.hide()

        # 부모 클래스의 mouseMoveEvent 호출
        super().mouseMoveEvent(event)

    def wheelEvent(self, event) -> None:  # type: ignore
        """
        이 위젯의 wheelEvent를 부모 위젯으로 전달하는 메서드
        """

        # 이벤트 무시
        event.ignore()

        # 툴팁 숨김
        self.tooltip_line.hide()
        self.tooltip_label.hide()
        self.tooltip_point.hide()

        # 부모 위젯의 wheelEvent 호출
        self.parent().wheelEvent(event)  # type: ignore


class SkillContributionCanvas(pg.PlotWidget):
    def __init__(
        self,
        parent: QWidget,
        data: dict,
        names: list[str],
    ) -> None:
        super().__init__(parent)

        # 데이터와 레이블, 색상, 제목 설정
        self.data: dict = data
        self.skill_names: list[str] = names

        # 데미지가 0인 스킬 제거
        data_0idx = [i for i, j in enumerate(data["data"]) if not j[-1]]
        data_0idx.sort(reverse=True)

        for i in data_0idx:
            self.data["data"].pop(i)
            self.skill_names.pop(i)

        self.skill_names.append("평타")

        # 안티 에일리어싱 활성화
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # PyQtGraph 전역 안티 에일리어싱 설정
        pg.setConfigOptions(antialias=True)

        # 제목 설정
        self.setLabel("top", "스킬별 기여도")

        # 축 숨기기 (제목은 표시)
        self.getAxis("top").setStyle(showValues=False)
        # 축 선 숨기기
        self.getAxis("top").setPen(None)

        # 제목 폰트 설정
        font = CustomFont(point_size=14)
        self.getAxis("top").label.setFont(font)
        # 제목 색상을 검정색으로 설정
        self.getAxis("top").setTextPen("black")

        # 하단 축 텍스트 설정
        font_properties = {
            "font-size": "10pt",
            "font-family": "Noto Sans KR",
        }
        self.setLabel("bottom", "시간", units="초", **font_properties)

        # 하단 축 스타일 설정
        axis_bottom: pg.AxisItem = self.getAxis("bottom")
        # axis_bottom.setStyle(showValues=True, tickLength=10)

        # 축 폰트 설정
        axis_font = CustomFont(point_size=10)
        axis_bottom.setStyle(tickFont=axis_font)
        # 축 라벨 색상을 검정색으로 설정
        axis_bottom.setPen(None)
        axis_bottom.setTextPen("black")

        # 좌측 축 설정 (Y축)
        axis_left: pg.AxisItem = self.getAxis("left")
        axis_left.setStyle(tickFont=axis_font)
        axis_left.setTextPen("black")
        # Y축 선 숨기기
        axis_left.setPen(None)

        # 배경 색상 설정
        self.background_color = "#F8F8F8"
        self.setBackground(self.background_color)

        # 테두리 색상 설정
        self.setStyleSheet("border: 0px solid;")

        # 마우스 상호작용 비활성화 (드래그, 줌, 우클릭 메뉴 등)
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)

        # 자동 범위 조정 버튼 비활성화
        self.hideButtons()

        # 스킬 색상 설정
        self.colors: list[str] = [
            "#EF9A9A",
            "#90CAF9",
            "#A5D6A7",
            "#FFEB3B",
            "#CE93D8",
            "#F0B070",
            "#2196F3",
        ]

        # 눈금 설정
        self.set_ticks()

        # 선 그래프 그리기
        self.create_area_chart()

        # X, Y축 그리드 비활성화
        self.showGrid(x=False, y=False)

        # ViewBox의 여백 제거
        self.getViewBox().setDefaultPadding(0.0)

        # X축 범위를 명시적으로 설정하여 0과 60이 모두 보이도록 함
        self.setXRange(-1, 61)

        # Y축 범위 설정
        self.setYRange(0, 101)

        # Y축 그리드를 100까지만 표시하도록 제한
        # self.getViewBox().setLimits(yMin=0, yMax=100.1, xMin=-1, xMax=617)

    def create_area_chart(self) -> None:
        # 데이터에서 시간, 최대, 평균, 최소 값 추출
        time = self.data["time"]
        datas = self.data["data"]

        # 누적 합계 계산
        self.totals = [
            [sum(datas[j][k] for j in range(i + 1)) for k in range(len(time))]
            for i in range(len(datas))
        ]

        # 선 그래프 그리기
        for i in range(len(datas)):
            # self.plot(
            #     time,
            #     self.totals[i],
            #     pen=pg.mkPen(self.colors[i], width=2),
            #     name=f"스킬 {i + 1}",
            # )
            fill = pg.FillBetweenItem(
                curve1=pg.PlotCurveItem(
                    x=time,
                    y=self.totals[i],
                    pen=pg.mkPen(self.colors[i], width=2),
                ),
                curve2=pg.PlotCurveItem(
                    x=time,
                    y=self.totals[i - 1] if i != 0 else [0] * len(time),
                    pen=pg.mkPen(self.colors[i], width=2),
                ),
                brush=pg.mkBrush(self.colors[i], alpha=100),
            )
            self.addItem(fill)

        # 범례 표시 ******************
        self.addLegend()

        # 툴팁 선 (범위 지정 가능한 선)
        self.tooltip_line = pg.PlotCurveItem(
            pen=pg.mkPen("gray", width=2, style=Qt.PenStyle.DashLine),
        )
        self.addItem(self.tooltip_line)

        # 툴팁 점
        self.tooltip_point = pg.ScatterPlotItem(pen=pg.mkPen("gray", width=1), size=8)
        self.addItem(self.tooltip_point)

        # 툴팁 레이블 설정
        self.tooltip_label = QLabel(parent=self)

        # 플래그 설정
        # self.tooltip_label.setWindowFlags(Qt.WindowType.ToolTip)
        # 투명도 설정 (0.0~1.0, 1.0이 완전 불투명)
        # self.tooltip_label.setWindowOpacity(0.5)

        # 스타일 시트 설정 (테두리 제거하고 배경만 사용)
        self.tooltip_label.setStyleSheet(
            """QLabel {
                background-color: rgba(255, 255, 255, 0.8);
                padding: 5px;
                border: 1px solid gray;
                border-radius: 10px;
            }"""
        )
        # 폰트 설정
        self.tooltip_label.setFont(CustomFont(point_size=10))

        # 처음에는 숨김
        self.tooltip_line.hide()
        self.tooltip_point.hide()
        self.tooltip_label.hide()

    def set_ticks(self) -> None:
        # x축 눈금 설정 (0부터 60까지 10 간격)
        bottom_axis: pg.AxisItem = self.getAxis("bottom")
        bottom_axis.setTicks([[(i, str(i)) for i in range(0, 61, 10)]])

        # y축 눈금 설정 (20%부터 100%까지 20% 간격, 100% 포함)
        left_axis: pg.AxisItem = self.getAxis("left")
        left_axis.setTicks([[(i * 20, f"{i * 20}%") for i in range(6)]])

        # 그리드 라인 추가
        # x축 그리드 라인
        for x in [10, 20, 30, 40, 50]:
            grid_line = pg.PlotCurveItem(
                x=[x, x],
                y=[0, 100],
                pen=pg.mkPen("gray", width=1, style=Qt.PenStyle.DashLine),
            )
            self.addItem(grid_line)

        # y축 그리드 라인
        for y in [20, 40, 60, 80]:
            grid_line = pg.PlotCurveItem(
                x=[0, 60],
                y=[y, y],
                pen=pg.mkPen("gray", width=1, style=Qt.PenStyle.DashLine),
            )
            self.addItem(grid_line)

        # 테두리는 실선으로 추가
        grid_line = pg.PlotCurveItem(
            x=[0, 0],
            y=[0, 100],
            pen=pg.mkPen("gray", width=1, style=Qt.PenStyle.SolidLine),
        )
        self.addItem(grid_line)

        grid_line = pg.PlotCurveItem(
            x=[60, 60],
            y=[0, 100],
            pen=pg.mkPen("gray", width=1, style=Qt.PenStyle.SolidLine),
        )
        self.addItem(grid_line)

        grid_line = pg.PlotCurveItem(
            x=[0, 60],
            y=[100, 100],
            pen=pg.mkPen("gray", width=1, style=Qt.PenStyle.SolidLine),
        )
        self.addItem(grid_line)

        # 0%는 별도로 추가
        grid_line = pg.PlotCurveItem(
            x=[-1, 60],
            y=[0, 0],
            pen=pg.mkPen("gray", width=2, style=Qt.PenStyle.SolidLine),
        )
        self.addItem(grid_line)

    def mouseMoveEvent(self, event) -> None:  # type: ignore
        """
        마우스 이동 이벤트 핸들러
        """

        # 현재 마우스 위치 가져오기
        pos: QPoint = event.pos()

        # QpointF로 변환
        pos_f: QPointF = QPointF(pos)

        # ViewBox 좌표로 변환
        pos_converted: QPointF = self.getViewBox().mapSceneToView(pos_f)

        # x 좌표 추출
        x: float = pos_converted.x()
        y: float = pos_converted.y()

        # 데이터 인덱스 계산
        time = int(x + 0.5)

        # 마우스가 X축 범위 내에 있는지 확인
        if 0 <= time <= 60 and x >= -0.5 and 0 <= y <= 100:
            # 툴팁 선 위치 설정 (수직선, Y축 범위는 0부터 60까지)
            self.tooltip_line.setData(x=[x, x], y=[0, 100])
            self.tooltip_line.show()

            # 툴팁 레이블 위치 및 내용 설정
            self.tooltip_label.setText(
                f"시간: {time}초\n"
                + "\n".join(
                    f"{self.skill_names[i]}: {self.data['data'][i][time]:.2f}%"
                    for i in range(len(self.data["data"]) - 1, -1, -1)  # 역순으로 표시
                )
            )
            global_pos = event.globalPosition().toPoint()
            local_pos = self.mapFromGlobal(global_pos)
            self.tooltip_label.move(local_pos + QPoint(15, 15))

            # 툴팁 레이블 크기 조정
            self.tooltip_label.adjustSize()

            # 툴팁 위치 조정
            if x <= 30:
                self.tooltip_label.move(local_pos + QPoint(15, -30))
            else:
                self.tooltip_label.move(
                    local_pos - QPoint(self.tooltip_label.width() + 15, 30)
                )

            # 툴팁을 맨 위로 올림
            self.tooltip_label.raise_()

            self.tooltip_label.show()

            # 툴팁 점 위치 설정 (실제 데이터 포인트들)
            points_data = [
                [time, self.totals[i][time]] for i in range(len(self.data["data"]) - 1)
            ]
            self.tooltip_point.setData(
                pos=points_data,
                brush=["white" for i in range(len(self.data["data"]) - 1)],
                # brush=[self.colors[i] for i in range(len(self.data["data"]) - 1)],
            )
            self.tooltip_point.show()

        # 범위를 벗어난 경우 툴팁 숨김
        else:
            self.tooltip_line.hide()
            self.tooltip_label.hide()
            self.tooltip_point.hide()

        # 부모 클래스의 mouseMoveEvent 호출
        super().mouseMoveEvent(event)

        # self.update()

    def wheelEvent(self, event) -> None:  # type: ignore
        """
        이 위젯의 wheelEvent를 부모 위젯으로 전달하는 메서드
        """

        # 이벤트 무시
        event.ignore()

        # 툴팁 숨김
        self.tooltip_line.hide()
        self.tooltip_label.hide()
        self.tooltip_point.hide()

        # 부모 위젯의 wheelEvent 호출
        self.parent().wheelEvent(event)  # type: ignore
