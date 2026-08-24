"""재련 시뮬레이터 그래프 캔버스

단계별 값 비교 막대그래프와 소모량 분포 선그래프를 제공한다.
색상은 계산기 그래프와 동일한 테마 팔레트를 사용한다.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QCoreApplication, QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QWheelEvent
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget

from app.scripts.custom_classes import CustomFont
from app.scripts.refinement_engine import RefinementDistribution
from app.scripts.ui.sim_ui.graph import get_graph_palette
from app.scripts.ui.themes import GraphPalette, theme_manager

# 분포 그래프 표시 구간 상한 확률과 표본 지점 수
_DISTRIBUTION_UPPER_PROBABILITY: float = 0.99
_DISTRIBUTION_BIN_COUNT: int = 240

# 기준선 뒤쪽에 확보할 가로 여백 비율
_RANGE_MARGIN_RATIO: float = 0.02

# 분포 선 아래 채움 불투명도
_AREA_FILL_ALPHA: int = 44

# 기준선 라벨을 번갈아 놓을 세로 위치
_MARKER_LABEL_POSITIONS: tuple[float, ...] = (0.94, 0.80, 0.66)

# 그래프 기본 높이
_CANVAS_HEIGHT: int = 260

# 좌측 값 축 고정 폭
# 자동 확장에 맡기면 첫 그리기에서 눈금 숫자가 표시되지 않는다.
_VALUE_AXIS_WIDTH: int = 76


class _DistributionSamples:
    """분포 표시용 표본 지점 묶음"""

    __slots__ = ("centers", "probabilities", "edges", "cumulative", "bin_width")

    def __init__(
        self,
        centers: np.ndarray,
        probabilities: np.ndarray,
        edges: np.ndarray,
        cumulative: np.ndarray,
        bin_width: float,
    ) -> None:
        self.centers: np.ndarray = centers
        self.probabilities: np.ndarray = probabilities
        self.edges: np.ndarray = edges
        self.cumulative: np.ndarray = cumulative
        self.bin_width: float = bin_width


def _sample_distribution(
    distribution: RefinementDistribution,
    display_upper_value: float | None = None,
) -> _DistributionSamples:
    """분포를 표시용 구간 확률과 누적 확률로 집계"""

    pmf: np.ndarray = distribution.pmf
    unit_value: float = distribution.unit_value

    # 화면 표시 범위가 있으면 해당 범위를 우선 샘플링
    upper_value: float = (
        distribution.quantile(_DISTRIBUTION_UPPER_PROBABILITY)
        if display_upper_value is None
        else display_upper_value
    )
    if upper_value <= 0.0:
        # 소모량이 0에 몰린 분포는 단일 지점으로 표시
        single: np.ndarray = np.array([float(pmf[0])], dtype=np.float64)
        return _DistributionSamples(
            np.array([0.0], dtype=np.float64),
            single,
            np.array([1.0], dtype=np.float64),
            single.copy(),
            1.0,
        )

    upper_index: int = min(pmf.size, int(upper_value / unit_value) + 1)
    bin_size: int = max(1, upper_index // _DISTRIBUTION_BIN_COUNT)
    bin_count: int = max(1, upper_index // bin_size)

    # 구간 단위로 확률 합산
    boundaries: np.ndarray = np.arange(bin_count, dtype=np.int64) * bin_size
    probabilities: np.ndarray = np.add.reduceat(pmf[: bin_count * bin_size], boundaries)

    bin_width: float = bin_size * unit_value
    centers: np.ndarray = (boundaries + bin_size / 2.0) * unit_value

    # 구간 오른쪽 끝에서의 누적 확률
    edges: np.ndarray = (boundaries + bin_size) * unit_value
    cumulative: np.ndarray = np.cumsum(probabilities)

    return _DistributionSamples(centers, probabilities, edges, cumulative, bin_width)


class _RefinementCanvasBase(pg.PlotWidget):
    """재련 그래프 공통 축·툴팁 구성"""

    def __init__(self, parent: QWidget, title: str) -> None:
        super().__init__(parent=parent)

        self.setObjectName("refinementCanvas")
        self.graph_palette: GraphPalette = get_graph_palette()
        self._title: str = title

        # 렌더링 품질과 상호작용 정책 설정
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)
        self.hideButtons()
        self.showGrid(x=False, y=True, alpha=0.15)
        self.setFixedHeight(_CANVAS_HEIGHT)

        # 상단 제목 축 구성 (제목이 없으면 여백만 남긴다)
        top_axis: pg.AxisItem = self.getAxis("top")
        top_axis.setStyle(showValues=False, tickLength=14 if title else 4)
        top_axis.setPen(None)
        top_axis.enableAutoSIPrefix(False)
        if title:
            self.setLabel("top", title)
            top_axis.label.setFont(CustomFont(12))

        # 값 축과 항목 축 폰트 구성
        for axis_name in ("bottom", "left"):
            axis: pg.AxisItem = self.getAxis(axis_name)
            axis.setStyle(tickFont=CustomFont(9))
            axis.enableAutoSIPrefix(False)

        # 좌측 값 축 폭 고정 (첫 그리기부터 눈금 숫자 표시)
        value_axis: pg.AxisItem = self.getAxis("left")
        value_axis.setStyle(autoExpandTextSpace=False)
        value_axis.setWidth(_VALUE_AXIS_WIDTH)

        # 툴팁 라벨 구성
        self.tooltip_label: QLabel = QLabel(self)
        self.tooltip_label.setObjectName("graphTooltipLabel")
        self.tooltip_label.setFont(CustomFont(10))
        self.tooltip_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.tooltip_label.hide()

        self._apply_palette()
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _apply_palette(self) -> None:
        """현재 팔레트 기준 축·배경 색상 반영"""

        self.setBackground(self.graph_palette.canvas_background)
        self.getAxis("top").setTextPen(self.graph_palette.title_text)
        self.getAxis("bottom").setTextPen(self.graph_palette.axis_text)
        self.getAxis("left").setTextPen(self.graph_palette.axis_text)

    def _on_theme_changed(self, _dark: bool) -> None:
        """테마 전환 시 그래프 재구성"""

        # 현재 테마 기준 팔레트 재적용 후 내용 다시 그리기
        self.graph_palette = get_graph_palette()
        self._apply_palette()
        self.tooltip_label.hide()
        self.redraw()

    def redraw(self) -> None:
        """현재 데이터 기준 그래프 다시 그리기"""

        raise NotImplementedError

    def _show_tooltip(self, text: str, position: QPoint) -> None:
        """마우스 위치 근처에 툴팁 표시"""

        # 현재 팔레트 기준 툴팁 스타일 적용
        self.tooltip_label.setStyleSheet(
            f"background-color: {self.graph_palette.tooltip_background};"
            f"color: {self.graph_palette.tooltip_text};"
            f"border: 1px solid {self.graph_palette.tooltip_border};"
            "border-radius: 4px; padding: 4px 6px;"
        )
        self.tooltip_label.setText(text)
        self.tooltip_label.adjustSize()

        # 캔버스 밖으로 나가지 않도록 위치 보정
        x: int = min(position.x() + 12, self.width() - self.tooltip_label.width() - 4)
        y: int = min(position.y() + 12, self.height() - self.tooltip_label.height() - 4)
        self.tooltip_label.move(max(4, x), max(4, y))
        self.tooltip_label.show()

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        """캔버스를 벗어나면 툴팁 숨김"""

        self.tooltip_label.hide()
        super().leaveEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore[override]
        """휠 입력을 바깥 페이지 스크롤 영역으로 전달"""

        ancestor: QWidget | None = self.parentWidget()
        while ancestor is not None:
            if isinstance(ancestor, QScrollArea):
                QCoreApplication.sendEvent(ancestor.verticalScrollBar(), event)
                return

            ancestor = ancestor.parentWidget()

        event.ignore()


class _RefinementStepCanvasBase(_RefinementCanvasBase):
    """단계별 그래프 공통 축·범위·툴팁 구성"""

    def __init__(
        self,
        parent: QWidget,
        title: str,
        steps: tuple[int, ...],
        values: tuple[float, ...],
        value_formatter: Callable[[float], str],
        highlight_step: int | None = None,
        value_axis_formatter: Callable[[float], str] | None = None,
        value_range: tuple[float, float] | None = None,
    ) -> None:
        super().__init__(parent, title)

        self._steps: tuple[int, ...] = steps
        self._values: tuple[float, ...] = values
        self._value_formatter: Callable[[float], str] = value_formatter
        self._highlight_step: int | None = highlight_step
        self._value_range: tuple[float, float] | None = value_range

        # 단계 축 눈금을 강 단위로 표시
        bottom_axis: pg.AxisItem = self.getAxis("bottom")
        bottom_axis.setTicks([[(step, f"{step}강") for step in steps]])

        # 값 축은 사람이 읽기 쉬운 형태로 표시
        left_axis: pg.AxisItem = self.getAxis("left")
        axis_formatter: Callable[[float], str] = (
            _format_axis_number
            if value_axis_formatter is None
            else value_axis_formatter
        )
        left_axis.tickStrings = lambda values, scale, spacing: [  # type: ignore[method-assign]
            axis_formatter(value) for value in values
        ]

    def _apply_ranges(self) -> None:
        """단계와 값의 표시 범위 적용"""

        if self._value_range is None:
            max_value: float = max(self._values) if self._values else 0.0
            min_value: float = min(self._values) if self._values else 0.0
            upper: float = max_value * 1.15 if max_value > 0.0 else 1.0
            lower: float = min(0.0, min_value * 1.15)
        else:
            lower, upper = self._value_range

        self.setYRange(lower, upper, padding=0.0)
        self.setXRange(self._steps[0] - 0.7, self._steps[-1] + 0.7, padding=0.0)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """가장 가까운 단계의 값 툴팁 표시"""

        super().mouseMoveEvent(event)

        if not self._steps:
            return

        # 마우스 위치를 데이터 좌표로 변환
        scene_position = self.plotItem.vb.mapSceneToView(event.position())
        step_position: float = float(scene_position.x())

        nearest_index: int = int(
            np.argmin([abs(step - step_position) for step in self._steps])
        )
        if abs(self._steps[nearest_index] - step_position) > 0.5:
            self.tooltip_label.hide()
            return

        self._show_tooltip(
            f"{self._steps[nearest_index]}강\n"
            f"{self._value_formatter(self._values[nearest_index])}",
            event.position().toPoint(),
        )


class RefinementStepBarCanvas(_RefinementStepCanvasBase):
    """목표 단계별 값 비교 막대그래프"""

    def __init__(
        self,
        parent: QWidget,
        title: str,
        steps: tuple[int, ...],
        values: tuple[float, ...],
        value_formatter: Callable[[float], str],
        highlight_step: int | None = None,
        rising_steps: tuple[int, ...] = (),
        value_axis_formatter: Callable[[float], str] | None = None,
        value_range: tuple[float, float] | None = None,
    ) -> None:
        self._rising_steps: frozenset[int] = frozenset(rising_steps)
        super().__init__(
            parent,
            title,
            steps,
            values,
            value_formatter,
            highlight_step,
            value_axis_formatter,
            value_range,
        )
        self.redraw()

    def redraw(self) -> None:
        """단계별 막대 다시 그리기"""

        self.clear()
        if not self._steps:
            return

        # 직전 단계보다 값이 오르는 구간은 채움 색으로 구분
        brushes: list[str] = [
            self.graph_palette.dpm_center_bar
            if step in self._rising_steps
            else self.graph_palette.dpm_normal_bar
            for step in self._steps
        ]

        # 선택한 목표 단계는 테두리로 표시해 채움 색 구분과 겹치지 않게 한다
        highlight_pen = pg.mkPen(self.graph_palette.dpm_median_bar, width=2)
        pens: list = [
            highlight_pen if step == self._highlight_step else pg.mkPen(None)
            for step in self._steps
        ]

        bar_item: pg.BarGraphItem = pg.BarGraphItem(
            x=list(self._steps),
            height=list(self._values),
            width=0.72,
            brushes=brushes,
            pens=pens,
        )
        self.addItem(bar_item)
        self._apply_ranges()


class RefinementSignedDeltaBarCanvas(_RefinementStepCanvasBase):
    """단계별 변화량과 상대 고효율 단계를 색상으로 표시하는 막대그래프"""

    def __init__(
        self,
        parent: QWidget,
        title: str,
        steps: tuple[int, ...],
        values: tuple[float, ...],
        value_formatter: Callable[[float], str],
        high_efficiency_steps: tuple[int, ...],
        highlight_step: int | None = None,
        value_axis_formatter: Callable[[float], str] | None = None,
        value_range: tuple[float, float] | None = None,
    ) -> None:
        self._high_efficiency_steps: frozenset[int] = frozenset(
            high_efficiency_steps
        )
        super().__init__(
            parent,
            title,
            steps,
            values,
            value_formatter,
            highlight_step,
            value_axis_formatter,
            value_range,
        )
        self.redraw()

    def redraw(self) -> None:
        """부호와 상대 효율 색상으로 변화량 막대 다시 그리기"""

        self.clear()
        if not self._steps:
            return

        # 양수 중앙값을 넘는 단계는 연두색, 나머지는 부호별 색상으로 구분
        brushes: list[str] = [
            (
                self.graph_palette.efficiency_high_bar
                if step in self._high_efficiency_steps
                else self.graph_palette.dpm_normal_bar
                if value >= 0.0
                else self.graph_palette.dpm_center_bar
            )
            for step, value in zip(self._steps, self._values)
        ]

        # 선택한 목표 단계는 테두리로 표시해 현재 선택값 강조
        highlight_pen = pg.mkPen(self.graph_palette.dpm_median_bar, width=2)
        pens: list = [
            highlight_pen if step == self._highlight_step else pg.mkPen(None)
            for step in self._steps
        ]

        # 0 기준으로 양수·음수 막대가 각각 위·아래로 확장되도록 구성
        bar_item: pg.BarGraphItem = pg.BarGraphItem(
            x=list(self._steps),
            height=list(self._values),
            width=0.72,
            brushes=brushes,
            pens=pens,
        )
        self.addItem(bar_item)
        self._apply_ranges()


class RefinementStepLineCanvas(_RefinementStepCanvasBase):
    """목표 단계별 값 비교 선그래프"""

    def __init__(
        self,
        parent: QWidget,
        title: str,
        steps: tuple[int, ...],
        values: tuple[float, ...],
        value_formatter: Callable[[float], str],
        guide_values: tuple[float, ...],
        highlight_step: int | None = None,
        value_axis_formatter: Callable[[float], str] | None = None,
        value_range: tuple[float, float] | None = None,
    ) -> None:
        self._guide_values: tuple[float, ...] = guide_values
        super().__init__(
            parent,
            title,
            steps,
            values,
            value_formatter,
            highlight_step,
            value_axis_formatter,
            value_range,
        )
        self.redraw()

    def redraw(self) -> None:
        """단계별 선과 선택 목표 지점 다시 그리기"""

        self.clear()
        if not self._steps:
            return

        # 주요 확률 눈금을 기본 격자보다 선명한 실선으로 구성
        for guide_value in self._guide_values:
            guide_line: pg.InfiniteLine = pg.InfiniteLine(
                pos=guide_value,
                angle=0,
                pen=pg.mkPen(
                    self.graph_palette.guide_line,
                    width=1.5,
                ),
            )
            guide_line.setZValue(-1)
            self.addItem(guide_line)

        line_color: str = self.graph_palette.dpm_normal_bar
        self.plot(
            list(self._steps),
            list(self._values),
            pen=pg.mkPen(line_color, width=2),
            symbol="o",
            symbolSize=7,
            symbolPen=pg.mkPen(line_color, width=1.5),
            symbolBrush=pg.mkBrush(self.graph_palette.canvas_background),
            antialias=True,
        )

        if self._highlight_step in self._steps:
            highlight_index: int = self._steps.index(self._highlight_step)
            self.addItem(
                pg.ScatterPlotItem(
                    [self._steps[highlight_index]],
                    [self._values[highlight_index]],
                    symbol="o",
                    size=11,
                    pen=pg.mkPen(self.graph_palette.dpm_median_bar, width=2),
                    brush=pg.mkBrush(self.graph_palette.canvas_background),
                )
            )

        self._apply_ranges()


class _RefinementCurveCanvasBase(_RefinementCanvasBase):
    """분포 계열 선그래프 공통 구성"""

    def __init__(
        self,
        parent: QWidget,
        title: str,
        distribution: RefinementDistribution,
        value_formatter: Callable[[float], str],
        markers: tuple[tuple[str, float], ...],
    ) -> None:
        super().__init__(parent, title)

        self._value_formatter: Callable[[float], str] = value_formatter
        self._markers: tuple[tuple[str, float], ...] = markers
        self._range_right_edge: float | None = (
            max(value * (1.0 + _RANGE_MARGIN_RATIO) for _, value in markers)
            if markers
            else None
        )
        self._samples: _DistributionSamples = _sample_distribution(
            distribution,
            self._range_right_edge,
        )

        # 값 축 눈금 표기 구성
        bottom_axis: pg.AxisItem = self.getAxis("bottom")
        bottom_axis.tickStrings = lambda values, scale, spacing: [  # type: ignore[method-assign]
            _format_axis_number(value) for value in values
        ]

    def _draw_curve(self, x_values: np.ndarray, y_values: np.ndarray, color: str) -> None:
        """선과 아래쪽 채움 영역 그리기"""

        curve: pg.PlotDataItem = self.plot(
            x_values,
            y_values,
            pen=pg.mkPen(color, width=2),
            antialias=True,
        )
        baseline: pg.PlotDataItem = self.plot(
            x_values,
            np.zeros_like(y_values),
            pen=pg.mkPen(None),
        )

        fill_color: QColor = QColor(color)
        fill_color.setAlpha(_AREA_FILL_ALPHA)
        fill: pg.FillBetweenItem = pg.FillBetweenItem(
            curve,
            baseline,
            brush=pg.mkBrush(fill_color),
        )

        # 채움이 선을 가리지 않도록 뒤쪽에 배치
        fill.setZValue(-1)
        self.addItem(fill)

    def _draw_markers(self) -> None:
        """기준선과 라벨 그리기"""

        for index, (label, value) in enumerate(self._markers):
            line: pg.InfiniteLine = pg.InfiniteLine(
                pos=value,
                angle=90,
                pen=pg.mkPen(
                    self.graph_palette.dpm_median_bar,
                    width=1,
                    style=Qt.PenStyle.DashLine,
                ),
                label=f"{label} {self._value_formatter(value)}",
                labelOpts={
                    # 기준선이 가까울 때 라벨이 겹치지 않도록 높이를 번갈아 둔다
                    "position": _MARKER_LABEL_POSITIONS[
                        index % len(_MARKER_LABEL_POSITIONS)
                    ],
                    "color": self.graph_palette.axis_text,
                    "movable": False,
                    # 좌우 가장자리에서는 라벨을 그래프 안쪽으로 전환
                    "anchors": ((0.0, 0.5), (1.0, 0.5)),
                },
            )
            self.addItem(line)

    def _x_range(self) -> tuple[float, float]:
        """지정 기준선에 여백을 더한 가로 표시 범위 반환"""

        if self._range_right_edge is None:
            return 0.0, float(self._samples.edges[-1])

        return 0.0, self._range_right_edge

    def _nearest_index(self, event) -> int | None:
        """마우스 위치에 대응하는 표본 구간 조회"""

        centers: np.ndarray = self._samples.centers
        if centers.size == 0:
            return None

        scene_position = self.plotItem.vb.mapSceneToView(event.position())
        value_position: float = float(scene_position.x())
        nearest_index: int = int(np.argmin(np.abs(centers - value_position)))
        if abs(float(centers[nearest_index]) - value_position) > self._samples.bin_width:
            return None

        return nearest_index


class RefinementDistributionCanvas(_RefinementCurveCanvasBase):
    """소모량 구간 확률과 누적 확률을 함께 표시하는 선그래프"""

    def __init__(
        self,
        parent: QWidget,
        title: str,
        distribution: RefinementDistribution,
        value_formatter: Callable[[float], str],
        markers: tuple[tuple[str, float], ...] = (),
    ) -> None:
        super().__init__(
            parent,
            title,
            distribution,
            value_formatter,
            markers,
        )

        left_axis: pg.AxisItem = self.getAxis("left")
        left_axis.tickStrings = lambda values, scale, spacing: [  # type: ignore[method-assign]
            f"{value * 100:.1f}%" for value in values
        ]

        # 누적 확률은 구간 확률과 척도가 달라 독립된 오른쪽 축에 표시
        plot_item: pg.PlotItem = self.getPlotItem()
        primary_view: pg.ViewBox = plot_item.vb
        self._cumulative_view: pg.ViewBox = pg.ViewBox()
        plot_item.scene().addItem(self._cumulative_view)
        plot_item.showAxis("right")

        right_axis: pg.AxisItem = plot_item.getAxis("right")
        right_axis.linkToView(self._cumulative_view)
        right_axis.setLabel("누적 확률")
        right_axis.label.setFont(CustomFont(9))
        right_axis.setStyle(
            autoExpandTextSpace=False,
            textFillLimits=[(0, 1.0)],
            tickFont=CustomFont(9),
        )
        right_axis.setWidth(_VALUE_AXIS_WIDTH)
        right_axis.enableAutoSIPrefix(False)

        self._cumulative_view.setXLink(primary_view)
        self._cumulative_view.setMouseEnabled(x=False, y=False)
        primary_view.sigResized.connect(self._sync_cumulative_view_geometry)
        self._sync_cumulative_view_geometry()

        self.redraw()

    def _sync_cumulative_view_geometry(self) -> None:
        """오른쪽 축 뷰를 주 분포 그래프 영역에 맞춤"""

        primary_view: pg.ViewBox = self.getPlotItem().vb
        self._cumulative_view.setGeometry(primary_view.sceneBoundingRect())
        self._cumulative_view.linkedViewChanged(
            primary_view,
            self._cumulative_view.XAxis,
        )

    def redraw(self) -> None:
        """분포·누적 곡선과 기준선 다시 그리기"""

        self.clear()
        self._cumulative_view.clear()
        if self._samples.centers.size == 0:
            return

        self._draw_curve(
            self._samples.centers,
            self._samples.probabilities,
            self.graph_palette.dpm_normal_bar,
        )

        # 첫 구간 전의 0% 지점부터 이어지는 누적 확률선 구성
        cumulative_x: np.ndarray = np.concatenate(
            (np.array([0.0], dtype=np.float64), self._samples.edges)
        )
        cumulative_y: np.ndarray = np.concatenate(
            (np.array([0.0], dtype=np.float64), self._samples.cumulative)
        )
        self._cumulative_view.addItem(
            pg.PlotDataItem(
                cumulative_x,
                cumulative_y,
                pen=pg.mkPen(self.graph_palette.dpm_median_bar, width=2),
                antialias=True,
            )
        )
        self._draw_markers()

        left_edge, right_edge = self._x_range()
        self.setXRange(left_edge, right_edge, padding=0.0)
        self.setYRange(0.0, float(self._samples.probabilities.max()) * 1.2, padding=0.0)
        self._cumulative_view.setYRange(0.0, 1.0, padding=0.04)

        right_axis: pg.AxisItem = self.getAxis("right")
        right_axis.setLabel(
            "누적 확률",
            color=self.graph_palette.dpm_median_bar,
        )
        right_axis.setPen(self.graph_palette.dpm_median_bar)
        right_axis.setTextPen(self.graph_palette.dpm_median_bar)
        right_axis.setTicks(
            [[(value / 100.0, f"{value}%") for value in range(0, 101, 20)]]
        )

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """가장 가까운 구간까지의 누적 확률 툴팁 표시"""

        super().mouseMoveEvent(event)

        nearest_index: int | None = self._nearest_index(event)
        if nearest_index is None:
            self.tooltip_label.hide()
            return

        center: float = float(self._samples.centers[nearest_index])
        half_width: float = self._samples.bin_width / 2.0
        cumulative: float = float(self._samples.cumulative[nearest_index])

        self._show_tooltip(
            f"{self._value_formatter(center - half_width)} ~ "
            f"{self._value_formatter(center + half_width)}\n"
            f"누적 확률 {cumulative * 100:.2f}%",
            event.position().toPoint(),
        )


def _format_axis_number(value: float) -> str:
    """축 눈금 숫자 표기 구성"""

    # 큰 값은 만/억 단위로 축약해 눈금이 겹치지 않도록 표시
    absolute: float = abs(value)
    if absolute >= 100_000_000.0:
        return f"{value / 100_000_000.0:,.1f}억"

    if absolute >= 10_000.0:
        return f"{value / 10_000.0:,.0f}만"

    if absolute >= 1.0 or value == 0.0:
        return f"{value:,.0f}"

    return f"{value:,.3g}"
