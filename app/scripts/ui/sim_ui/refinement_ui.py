"""재련 시뮬레이터 화면

왼쪽 열에서 대상·재화·전략을 정하고, 계산 버튼을 누르면 백그라운드에서
계산한 결과를 오른쪽 열에 보여준다. 오른쪽 열은 핵심 지표 카드 네 장과
알약 탭 5개(요약 / 목표·재화 분석 / 전략 관리 / 스탯 효율 / 운빨 분석)로
구성한다.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from statistics import median
from typing import NamedTuple, Protocol

from PySide6.QtCore import (
    QEvent,
    QRect,
    QSignalBlocker,
    QSize,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.calculator_models import (
    STAT_SPECS,
    BaseStats,
    CalculatorPresetInput,
    CustomPowerFormula,
    RefinementEquipment,
    RefinementInput,
    RefinementStrategy,
    RefinementStrategyMode,
    StatKey,
)
from app.scripts.custom_classes import (
    CustomFont,
    CustomLineEdit,
    KVComboInput,
    KVInput,
    SectionCard,
    Separator,
    StyledButton,
)
from app.scripts.data_manager import save_data
from app.scripts.refinement_data import (
    MAX_REFINE_STEP,
    POINT_BUNDLE_SIZE,
    REFINE_ATTEMPT_STEP_COUNT,
    REFINE_LEVEL_CAPS,
    REFINEMENT_EQUIPMENT_LABELS,
)
from app.scripts.refinement_engine import (
    PREPARATION_PROBABILITIES,
    RefinementDistribution,
    RefinementEfficiencyRow,
    RefinementInputError,
    RefinementReport,
    RefinementStrategyChoice,
    RefinementTargetRow,
    build_refinement_report,
    validate_refinement_input,
    validate_strategy_thresholds,
)
from app.scripts.ui.character_ui.widgets import (
    FlowLayout,
    PillTab,
    ResponsiveColumnsBox,
)
from app.scripts.ui.popup import NoticeKind, PopupManager
from app.scripts.ui.sim_ui.formula_options import (
    build_formula_label_map,
    build_formula_options,
)
from app.scripts.ui.sim_ui.graph import get_graph_palette
from app.scripts.ui.sim_ui.refinement_graph import (
    RefinementDistributionCanvas,
    RefinementSignedDeltaBarCanvas,
    RefinementStepBarCanvas,
    RefinementStepLineCanvas,
)

# 재화 입력 상한
_MAX_BUDGET: float = 999_999_999_999.0
_MAX_BUNDLE_PRICE: float = 999_999_999.0

# 양수 변화량의 축 여백 비율
_EFFICIENCY_POSITIVE_RANGE_MARGIN: float = 0.15

# 입력 열 최소 폭 (내용이 더 넓으면 내용에 맞춘다)
_INPUT_COLUMN_MIN_WIDTH: int = 300

# Qt 위젯 폭 상한 (폭 제한을 푸는 용도)
_UNLIMITED_WIDTH: int = 16_777_215

# 비용 분포 그래프의 90% 분위수 배열 위치
_DISTRIBUTION_PERCENTILE_INDEX: int = PREPARATION_PROBABILITIES.index(0.9)

# 단계별 도달 확률 그래프의 강조 눈금
_REACH_PROBABILITY_GUIDE_VALUES: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8, 1.0)

# 확률별 필요량 표 헤더
_PREPARATION_TABLE_HEADERS: tuple[str, ...] = (
    "목표",
    *(f"{int(probability * 100)}%" for probability in PREPARATION_PROBABILITIES),
)

# 결과 탭 이름
_RESULT_TAB_LABELS: tuple[str, ...] = (
    "요약",
    "목표·재화 분석",
    "전략 관리",
    "스탯 효율",
    "운빨 분석",
)

# 준비량 기준 설명 (PREPARATION_PROBABILITIES 순서와 대응)
_PREPARATION_LABELS: tuple[str, ...] = (
    "낙관적",
    "도전적",
    "일반적",
    "안정적",
)


class CalculationOverlay(Protocol):
    """계산 진행 오버레이 인터페이스"""

    def show_overlay(self, message: str, detail: str, value: int) -> None: ...

    def update_progress(self, detail: str, value: int) -> None: ...

    def set_cancelling(self) -> None: ...

    def hide(self) -> None: ...


class _ChipCell(NamedTuple):
    """상태 색이 붙는 표 칸"""

    text: str
    tone: str


def _format_amount(value: float) -> str:
    """재화 수치 표시 문자열 구성"""

    # 게임 내 재화 단위는 전
    return f"{value:,.0f}전"


def _format_points(value: float) -> str:
    """강화포인트 수치 표시 문자열 구성"""

    return f"{value:,.1f}pt" if value != round(value) else f"{value:,.0f}pt"


def _format_probability_value(value: float) -> str:
    """확률의 백분율 숫자 표시 문자열 구성"""

    formatted: str = f"{value * 100:.2f}".rstrip("0").rstrip(".")
    return "0" if formatted == "-0" else formatted


def _format_probability(value: float) -> str:
    """단위가 포함된 확률 표시 문자열 구성"""

    return f"{_format_probability_value(value)}%"


def _format_power(value: float) -> str:
    """전투력 변화량 표시 문자열 구성"""

    return f"{value:+,.2f}".rstrip("0").rstrip(".")


def _stat_delta_parts(stat_delta: dict[StatKey, float]) -> tuple[str, ...]:
    """스탯 상승량을 항목별 문자열로 구성"""

    parts: list[str] = []
    for stat_key, value in stat_delta.items():
        formatted: str = f"{value:,.0f}" if value == round(value) else f"{value:,.2f}"
        parts.append(f"{STAT_SPECS[stat_key]} +{formatted}")

    return tuple(parts)


def _format_stat_delta(stat_delta: dict[StatKey, float]) -> str:
    """스탯 상승량 표시 문자열 구성"""

    parts: tuple[str, ...] = _stat_delta_parts(stat_delta)
    return ", ".join(parts) if parts else "변화 없음"


def _strategy_thresholds(choice: RefinementStrategyChoice) -> tuple[str, ...]:
    """전략 임계 단계 표시 문자열 구성"""

    # 보조를 쓰지 않는 전략은 임계 단계가 없음
    if choice.assist3_step is None or choice.assist7_step is None:
        return ("무보조",)

    return (
        f"3pt {choice.assist3_step}강↑",
        f"7pt {choice.assist7_step}강↑",
    )


def _strategy_name(choice: RefinementStrategyChoice) -> str:
    """전략 이름 표시 문자열 구성"""

    if choice.mode == RefinementStrategyMode.AUTO:
        return "자동 최적"

    if choice.assist3_step is None or choice.assist7_step is None:
        return "무보조"

    return choice.strategy_name


def _clear_layout(target_layout: QLayout) -> None:
    """레이아웃의 기존 위젯 제거"""

    while target_layout.count():
        item: QLayoutItem = target_layout.takeAt(0)
        nested: QLayout | None = item.layout()
        if nested is not None:
            _clear_layout(nested)

        widget: QWidget | None = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


def _stretch_field(field: KVInput | KVComboInput) -> None:
    """입력 위젯이 카드 폭을 가득 채우도록 크기 정책 조정

    KVInput/KVComboInput 은 기본적으로 내용 폭에 맞춰 고정되지만,
    입력 열에서는 칸이 열 폭을 채워야 목업과 같은 형태가 된다.
    """

    field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    inner: QWidget = (
        field.input if isinstance(field, KVInput) else field.combobox
    )
    inner.setMaximumWidth(_UNLIMITED_WIDTH)
    inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


def _parse_amount(text: str) -> float | None:
    """재화 입력 문자열 파싱"""

    # 천 단위 구분 기호와 공백 제거 후 정수 검증
    normalized: str = text.replace(",", "").strip()
    if not normalized:
        return 0.0

    if not normalized.isdigit():
        return None

    return float(normalized)


def _format_amount_input(
    input_widget: CustomLineEdit,
    *,
    preserve_zero_buffer: bool,
) -> None:
    """재화 입력값에 천 단위 구분 기호 적용"""

    text: str = input_widget.text()
    digits: str = text.replace(",", "").strip()
    if not digits or not digits.isdigit():
        return

    # 첫 유효 숫자를 교체하는 동안 선행 쉼표만 숨기고 기존 자릿수 유지
    is_zero_buffer: bool = len(digits) > 1 and not digits.strip("0")
    formatted: str = (
        text.strip().lstrip(",")
        if preserve_zero_buffer and is_zero_buffer
        else f"{int(digits):,}"
    )
    if formatted == text:
        return

    # 입력 위치 왼쪽의 숫자 개수를 기준으로 새 커서 위치 보존
    digit_offset: int = sum(
        character.isdigit() for character in text[: input_widget.cursorPosition()]
    )
    cursor_position: int = 0
    if digit_offset > 0:
        for character in formatted:
            if character.isdigit():
                digit_offset -= 1

            cursor_position += 1
            if digit_offset == 0:
                break

    with QSignalBlocker(input_widget):
        input_widget.setText(formatted)
        input_widget.setCursorPosition(cursor_position)


class _SplitLayout(QLayout):
    """입력 열과 결과 열을 좌우로 배치하는 레이아웃

    입력 열은 내용에 맞춘 고정 폭을 쓰고 결과 열이 남는 폭을 가져간다.
    창이 좁아 결과 열의 최소 폭을 확보하지 못하면 최소 폭을 유지해
    바깥 스크롤 영역이 가로 스크롤을 제공하게 한다.
    """

    def __init__(self, parent: QWidget | None = None, spacing: int = 10) -> None:
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

        self._items: list[QLayoutItem] = []

    def addItem(self, item: QLayoutItem) -> None:  # type: ignore[override]
        self._items.append(item)

    def count(self) -> int:  # type: ignore[override]
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items[index]

        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items.pop(index)

        return None

    def expandingDirections(self) -> Qt.Orientation:  # type: ignore[override]
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        if len(self._items) < 2:
            return QSize(0, 0)

        width: int = (
            self._input_width()
            + self.spacing()
            + self._items[1].minimumSize().width()
        )
        height: int = max(item.sizeHint().height() for item in self._items)
        return QSize(width, height)

    def _input_width(self) -> int:
        """입력 열 배치 폭 (내용이 더 넓으면 내용에 맞춘다)"""

        if not self._items:
            return 0

        return max(_INPUT_COLUMN_MIN_WIDTH, self._items[0].sizeHint().width())

    def _item_height(self, item: QLayoutItem, width: int) -> int:
        """주어진 폭에서의 블록 높이"""

        if item.hasHeightForWidth():
            return item.heightForWidth(width)

        return item.sizeHint().height()

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """좌우 배치 수행 후 총 높이 반환"""

        if len(self._items) < 2:
            return 0

        input_item: QLayoutItem = self._items[0]
        result_item: QLayoutItem = self._items[1]
        spacing: int = self.spacing()
        input_width: int = self._input_width()

        # 결과 열은 남는 폭을 가져가되 최소 폭 아래로는 줄이지 않는다
        result_width: int = max(
            rect.width() - input_width - spacing,
            result_item.minimumSize().width(),
        )
        height: int = max(
            self._item_height(input_item, input_width),
            self._item_height(result_item, result_width),
        )

        if not test_only:
            input_item.setGeometry(QRect(rect.x(), rect.y(), input_width, height))
            result_item.setGeometry(
                QRect(
                    rect.x() + input_width + spacing,
                    rect.y(),
                    result_width,
                    height,
                )
            )

        return height


class _SplitBox(QFrame):
    """_SplitLayout 을 담는 컨테이너

    필요한 높이는 현재 폭과 표시 중인 탭 내용에 따라 달라진다. 폭에 따라
    달라지는 sizeHint 는 부모 레이아웃이 캐시해 갱신되지 않으므로, 계산한
    높이를 스스로 확정하고 값이 바뀔 때만 바깥 레이아웃에 다시 알린다.
    """

    def __init__(self, parent: QWidget, on_height_changed: Callable[[], None]) -> None:
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._split: _SplitLayout = _SplitLayout(self)
        self._on_height_changed: Callable[[], None] = on_height_changed
        self._applied_height: int = -1

    def add_columns(self, input_column: QWidget, result_column: QWidget) -> None:
        """입력 열과 결과 열 배치"""

        self._split.addWidget(input_column)
        self._split.addWidget(result_column)

    def sync_height(self) -> None:
        """현재 폭과 내용 기준 컨테이너 높이 갱신"""

        width: int = self.width()
        if width <= 0:
            return

        required_height: int = self._split.heightForWidth(width)

        # 같은 높이면 다시 알리지 않아 재배치가 반복되지 않는다
        if required_height == self._applied_height:
            return

        self._applied_height = required_height
        self.setFixedHeight(required_height)
        self.updateGeometry()
        self._on_height_changed()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        if self._applied_height >= 0:
            return QSize(self.width(), self._applied_height)

        return self._split.sizeHint()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.sync_height()

    def event(self, event) -> bool:  # type: ignore[override]
        # 탭 전환이나 테마 전환 직후에는 자식 크기가 아직 확정되지 않는다.
        # 자식 배치가 갱신될 때마다 필요한 높이를 다시 계산한다.
        if event.type() == QEvent.Type.LayoutRequest:
            self.sync_height()

        return super().event(event)


class _KpiCard(QFrame):
    """핵심 지표 카드 한 장"""

    def __init__(self, parent: QWidget, title: str, tone: str = "accent") -> None:
        super().__init__(parent)

        self.setObjectName("refinementKpiCard")
        self.setProperty("tone", tone)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(135)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)

        self._title_label: QLabel = QLabel(title, self)
        self._title_label.setObjectName("refinementKpiKey")
        self._title_label.setFont(CustomFont(10))

        value_row: QHBoxLayout = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(3)

        self._value_label: QLabel = QLabel("-", self)
        self._value_label.setObjectName("refinementKpiValue")
        self._value_label.setFont(CustomFont(17, bold=True))

        self._unit_label: QLabel = QLabel("", self)
        self._unit_label.setObjectName("refinementKpiUnit")
        self._unit_label.setFont(CustomFont(10))

        value_row.addWidget(self._value_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addWidget(self._unit_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch(1)

        layout.addWidget(self._title_label)
        layout.addLayout(value_row)

    def set_value(self, value: str, unit: str) -> None:
        """지표 값 갱신"""

        self._value_label.setText(value)
        self._unit_label.setText(unit)

    def clear_value(self) -> None:
        """지표 값 초기화"""

        self.set_value("-", "")


class _KpiRow(ResponsiveColumnsBox):
    """핵심 지표 카드 네 장"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, min_column_width=135, spacing=10, max_columns=4)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.reach_card: _KpiCard = _KpiCard(self, "목표 도달 확률", tone="good")
        self.cost_card: _KpiCard = _KpiCard(self, "기대 재련비")
        self.point_card: _KpiCard = _KpiCard(self, "기대 강화포인트")
        self.power_card: _KpiCard = _KpiCard(self, "전투력 상승")

        for card in (self.reach_card, self.cost_card, self.point_card, self.power_card):
            self.addWidget(card)

    def set_report(self, report: RefinementReport) -> None:
        """계산 결과 기준 지표 갱신"""

        row: RefinementTargetRow = report.target_row

        self.reach_card.set_value(
            _format_probability_value(row.reach_probability),
            "%",
        )
        self.cost_card.set_value(
            f"{row.expected.cost:,.0f}",
            "전",
        )
        self.point_card.set_value(
            f"{row.expected.points:,.1f}",
            "pt",
        )

        if report.power_error is not None or row.power_delta is None:
            self.power_card.set_value("-", "")
            return

        self.power_card.set_value(
            f"{row.power_delta:+,.0f}",
            "",
        )

    def clear_report(self) -> None:
        """지표 표시 초기화"""

        for card in (self.reach_card, self.cost_card, self.point_card, self.power_card):
            card.clear_value()


class _TagList(QFrame):
    """줄바꿈되는 태그 목록"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._flow: FlowLayout = FlowLayout(self, margin=0, spacing=5)
        self._flow.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._flow)

    def set_tags(self, tags: tuple[tuple[str, bool], ...]) -> None:
        """태그 전체 갱신"""

        _clear_layout(self._flow)

        for text, is_primary in tags:
            tag_label: QLabel = QLabel(text, self)
            tag_label.setObjectName("refinementTag")
            tag_label.setProperty("primary", is_primary)
            tag_label.setFont(CustomFont(10, bold=is_primary))
            self._flow.addWidget(tag_label)

        self._sync_height()

    def _sync_height(self) -> None:
        """현재 폭 기준 높이 갱신

        태그가 줄바꿈되면 필요한 높이가 달라지는데, 부모 격자 레이아웃은
        heightForWidth 를 반영하지 않아 내용이 잘린다.
        """

        width: int = self.width()
        if width <= 0:
            self.updateGeometry()
            return

        self.setMinimumHeight(self._flow.heightForWidth(width))
        self.updateGeometry()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._sync_height()


class _GraphLegend(QFrame):
    """그래프 아래 색상 범례"""

    def __init__(
        self,
        parent: QWidget,
        entries: tuple[tuple[str, str, bool], ...],
    ) -> None:
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        for text, color, is_outline in entries:
            swatch: QFrame = QFrame(self)
            swatch.setFixedSize(10, 10)
            if is_outline:
                swatch.setStyleSheet(
                    f"background-color: transparent;"
                    f"border: 2px solid {color}; border-radius: 2px;"
                )

            else:
                swatch.setStyleSheet(
                    f"background-color: {color}; border: 0px; border-radius: 2px;"
                )

            caption: QLabel = QLabel(text, self)
            caption.setObjectName("resultsSubTitle")
            caption.setFont(CustomFont(9))

            entry_row: QHBoxLayout = QHBoxLayout()
            entry_row.setContentsMargins(0, 0, 0, 0)
            entry_row.setSpacing(5)
            entry_row.addWidget(swatch, 0, Qt.AlignmentFlag.AlignVCenter)
            entry_row.addWidget(caption)
            layout.addLayout(entry_row)

        layout.addStretch(1)


class _EfficiencyDeltaSeries(NamedTuple):
    """단계별 효율 변화량 그래프 데이터"""

    steps: tuple[int, ...]
    values: tuple[float, ...]
    high_efficiency_steps: tuple[int, ...]
    value_range: tuple[float, float]


def _build_efficiency_delta_series(
    report: RefinementReport,
) -> _EfficiencyDeltaSeries | None:
    """로그 총비용 기준 단계별 효율 변화량 구성"""

    # 전투력 상승량이 계산된 목표 단계만 효율 계산에 포함
    power_rows: tuple[RefinementEfficiencyRow, ...] = tuple(
        efficiency_row
        for efficiency_row in report.efficiency_rows
        if efficiency_row.power_delta is not None
    )
    if not power_rows:
        return None

    # 유효한 최저 단계의 효율을 0으로 두고 각 단계의 누적 효율 계산
    efficiency_values: tuple[float, ...] = (0.0,) + tuple(
        efficiency_row.power_delta
        / math.log10(efficiency_row.expected_economic_cost)
        for efficiency_row in power_rows
    )

    # 기준 다음 단계부터 n강−(n−1)강까지 변화량과 표시 단계 구성
    steps: tuple[int, ...] = tuple(
        efficiency_row.target_step for efficiency_row in power_rows
    )
    values: tuple[float, ...] = tuple(
        current - previous
        for previous, current in zip(efficiency_values, efficiency_values[1:])
    )

    # 양수 중앙값을 넘으면서 인접 단계보다 높은 지점을 상대 고효율로 구분
    positive_values: tuple[float, ...] = tuple(
        value for value in values if value > 0.0
    )
    high_efficiency_steps: tuple[int, ...] = ()
    if positive_values:
        positive_median: float = median(positive_values)
        last_index: int = len(values) - 1
        high_efficiency_steps = tuple(
            step
            for index, (step, value) in enumerate(zip(steps, values))
            if value > positive_median
            and (index == 0 or value > values[index - 1])
            and (index == last_index or value > values[index + 1])
        )

    # 양수 최대값 기준 공통 여백 계산
    minimum: float = min(values)
    maximum: float = max(values)
    positive_margin: float = (
        maximum * _EFFICIENCY_POSITIVE_RANGE_MARGIN
        if maximum > 0.0
        else 1.0
    )
    # 최소값과 0 중 작은 값을 기준으로 아래쪽 양수 여백 적용
    lower: float = min(0.0, minimum) - positive_margin
    upper: float = maximum + positive_margin if maximum > 0.0 else 0.0

    if lower == upper:
        upper = 1.0

    return _EfficiencyDeltaSeries(
        steps,
        values,
        high_efficiency_steps,
        (lower, upper),
    )


def _build_distribution_canvas(
    parent: QWidget,
    distribution: RefinementDistribution,
    expected_value: float,
    percentile_value: float,
    minimum_unit: float,
    result_marker: tuple[str, float] | None,
) -> RefinementDistributionCanvas:
    """목표·재화 분석과 운빨 분석이 공유하는 비용 분포 그래프 구성"""

    common_markers: tuple[tuple[str, float], ...] = (
        ("기대값", expected_value),
        ("90%", percentile_value),
    )
    markers: tuple[tuple[str, float], ...] = (
        common_markers
        if result_marker is None
        else common_markers + (result_marker,)
    )

    return RefinementDistributionCanvas(
        parent,
        "",
        distribution,
        _format_amount,
        minimum_unit,
        markers,
    )


def _add_efficiency_delta_graph(
    layout: QVBoxLayout,
    parent: QWidget,
    report: RefinementReport,
) -> None:
    """요약·스탯 효율 탭에 동일한 단계별 효율 그래프 추가"""

    # 공통 효율 데이터와 표시 범위 구성
    series: _EfficiencyDeltaSeries | None = _build_efficiency_delta_series(report)
    if series is None:
        notice: QLabel = QLabel(
            "전투력 변화량을 계산할 수 없어 단계별 효율 그래프를 표시하지 않습니다.",
            parent,
        )
        notice.setObjectName("resultsSubTitle")
        notice.setFont(CustomFont(10))
        layout.addWidget(notice)
        return

    # 상대 고효율과 변화 방향을 함께 표시하는 막대 구성
    layout.addWidget(
        RefinementSignedDeltaBarCanvas(
            parent,
            "",
            series.steps,
            series.values,
            lambda value: f"{value:+,.2f}",
            series.high_efficiency_steps,
            value_range=series.value_range,
        )
    )

    # 상대 고효율 범례 구성
    palette = get_graph_palette()
    layout.addWidget(
        _GraphLegend(
            parent,
            (("상대 고효율", palette.efficiency_high_bar, False),),
        )
    )


class _HeroValue(QFrame):
    """가장 중요한 숫자 하나를 크게 보여주는 블록"""

    def __init__(self, parent: QWidget, title: str) -> None:
        super().__init__(parent)

        self.setObjectName("refinementHeroBox")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)

        title_label: QLabel = QLabel(title, self)
        title_label.setObjectName("refinementHeroKey")
        title_label.setFont(CustomFont(10))

        value_row: QHBoxLayout = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(3)

        self._value_label: QLabel = QLabel("-", self)
        self._value_label.setObjectName("refinementHeroValue")
        self._value_label.setFont(CustomFont(20, bold=True))

        self._unit_label: QLabel = QLabel("", self)
        self._unit_label.setObjectName("refinementHeroUnit")
        self._unit_label.setFont(CustomFont(11))

        value_row.addWidget(self._value_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addWidget(self._unit_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch(1)

        self._sub_container: QFrame = QFrame(self)
        self._sub_layout: QVBoxLayout = QVBoxLayout(self._sub_container)
        self._sub_layout.setContentsMargins(0, 4, 0, 0)
        self._sub_layout.setSpacing(1)

        layout.addStretch(1)
        layout.addWidget(title_label)
        layout.addLayout(value_row)
        layout.addWidget(self._sub_container)
        layout.addStretch(1)

    def set_value(self, value: str, unit: str, sub_lines: tuple[str, ...]) -> None:
        """값과 보조 설명 갱신"""

        self._value_label.setText(value)
        self._unit_label.setText(unit)

        _clear_layout(self._sub_layout)
        for line in sub_lines:
            sub_label: QLabel = QLabel(line, self._sub_container)
            sub_label.setObjectName("refinementHeroSub")
            sub_label.setFont(CustomFont(9))
            self._sub_layout.addWidget(sub_label)


class _TabStack(QWidget):
    """표시/숨김 방식 결과 탭 스택"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._stack_layout: QVBoxLayout = QVBoxLayout(self)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)
        self._stack_layout.setSpacing(0)

        self._pages: list[QWidget] = []

    def add_page(self, widget: QWidget) -> None:
        """결과 페이지 추가"""

        self._pages.append(widget)
        self._stack_layout.addWidget(widget)
        widget.setVisible(len(self._pages) == 1)

    def set_current_index(self, index: int) -> None:
        """표시할 결과 페이지 전환"""

        for page_index, page in enumerate(self._pages):
            page.setVisible(page_index == index)

        self.updateGeometry()


class _KeyValueList(QFrame):
    """제목-값 형태의 요약 목록"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._grid: QGridLayout = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(16)
        self._grid.setVerticalSpacing(6)
        self._grid.setColumnStretch(1, 1)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_rows(
        self,
        rows: tuple[tuple[str, str], ...],
        chips: dict[int, _ChipCell] | None = None,
        positive_rows: tuple[int, ...] = (),
    ) -> None:
        """요약 행 전체 갱신

        chips 는 값 오른쪽에 붙일 상태 칩, positive_rows 는 상승값처럼
        긍정 색으로 표시할 행 번호다.
        """

        _clear_layout(self._grid)

        for row_index, (title, value) in enumerate(rows):
            title_label: QLabel = QLabel(title, self)
            title_label.setObjectName("resultsSubTitle")
            title_label.setFont(CustomFont(11))
            title_label.setMinimumWidth(120)

            value_label: QLabel = QLabel(value, self)
            value_label.setFont(CustomFont(12, bold=True))
            value_label.setWordWrap(True)
            if row_index in positive_rows:
                value_label.setObjectName("resultValueLabel")
                value_label.setProperty("sign", "positive")

            else:
                value_label.setObjectName("powerResultLabel")

            self._grid.addWidget(title_label, row_index, 0, Qt.AlignmentFlag.AlignTop)

            chip: _ChipCell | None = (chips or {}).get(row_index)
            if chip is None:
                self._grid.addWidget(value_label, row_index, 1)
                continue

            chip_label: QLabel = QLabel(chip.text, self)
            chip_label.setObjectName("refinementChip")
            chip_label.setProperty("tone", chip.tone)
            chip_label.setFont(CustomFont(9))

            value_row: QHBoxLayout = QHBoxLayout()
            value_row.setContentsMargins(0, 0, 0, 0)
            value_row.setSpacing(8)
            value_row.addWidget(value_label)
            value_row.addWidget(chip_label)
            value_row.addStretch(1)
            self._grid.addLayout(value_row, row_index, 1)


class _ResultTable(QFrame):
    """헤더가 있는 결과 표"""

    def __init__(
        self,
        parent: QWidget,
        headers: tuple[str, ...],
        text_columns: tuple[int, ...] = (),
    ) -> None:
        super().__init__(parent)

        self._headers: tuple[str, ...] = headers
        self._text_columns: tuple[int, ...] = text_columns
        self._grid: QGridLayout = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(6)

        # 줄무늬가 끊기지 않도록 행 사이 간격을 두지 않고 칸 안쪽 여백만 쓴다
        self._grid.setVerticalSpacing(0)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.set_rows(())

    def _alignment(self, column: int) -> Qt.AlignmentFlag:
        """열 정렬 방식 반환"""

        # 첫 열과 지정한 텍스트 열은 왼쪽, 나머지 수치 열은 오른쪽 정렬
        if column == 0 or column in self._text_columns:
            return Qt.AlignmentFlag.AlignLeft

        return Qt.AlignmentFlag.AlignRight

    def set_rows(
        self,
        rows: tuple[tuple[str | _ChipCell, ...], ...],
        highlight_index: int | None = None,
    ) -> None:
        """표 내용 전체 갱신"""

        _clear_layout(self._grid)

        # 헤더 행 구성
        for column, header in enumerate(self._headers):
            header_label: QLabel = QLabel(header, self)
            header_label.setObjectName("refinementTableHeader")
            header_label.setFont(CustomFont(11, bold=True))
            header_label.setAlignment(self._alignment(column))
            self._grid.addWidget(header_label, 0, column)

        # 헤더 구분선
        separator: Separator = Separator(self)
        self._grid.addWidget(separator, 1, 0, 1, len(self._headers))

        # 데이터 행 구성
        for row_index, row in enumerate(rows):
            grid_row: int = row_index + 2
            is_highlighted: bool = row_index == highlight_index

            # 줄무늬 배경을 행 전체에 먼저 깔고 그 위에 칸을 얹는다
            self._grid.addWidget(
                self._build_row_background(row_index, is_highlighted),
                grid_row,
                0,
                1,
                len(self._headers),
            )

            for column, cell in enumerate(row):
                if isinstance(cell, _ChipCell):
                    # 칸 폭 전체로 늘어나지 않도록 정렬을 배치 인자로 지정
                    self._grid.addWidget(
                        self._build_chip(cell),
                        grid_row,
                        column,
                        self._alignment(column) | Qt.AlignmentFlag.AlignVCenter,
                    )
                    continue

                self._grid.addWidget(
                    self._build_text_cell(cell, column, is_highlighted),
                    grid_row,
                    column,
                )

        # 열 폭을 고르게 분배해 값이 한쪽으로 몰리지 않게 유지
        for column in range(len(self._headers)):
            self._grid.setColumnStretch(column, 1)

    def _build_row_background(self, row_index: int, is_highlighted: bool) -> QFrame:
        """행 배경 위젯 구성"""

        background: QFrame = QFrame(self)
        background.setObjectName("refinementTableRow")
        if is_highlighted:
            background.setProperty("row", "hi")

        else:
            background.setProperty("row", "odd" if row_index % 2 == 0 else "even")

        # 배경이 행 높이를 늘리지 않도록 최소 크기만 차지하게 한다
        background.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        background.setMinimumSize(0, 0)
        return background

    def _build_chip(self, cell: _ChipCell) -> QLabel:
        """상태 색이 붙는 칸 위젯 구성"""

        chip_label: QLabel = QLabel(cell.text, self)
        chip_label.setObjectName("refinementChip")
        chip_label.setProperty("tone", cell.tone)
        chip_label.setFont(CustomFont(10))
        return chip_label

    def _build_text_cell(
        self,
        text: str,
        column: int,
        is_highlighted: bool,
    ) -> QLabel:
        """일반 텍스트 칸 위젯 구성"""

        cell_label: QLabel = QLabel(text, self)
        cell_label.setObjectName("refinementCell")
        cell_label.setFont(CustomFont(11, bold=is_highlighted))
        cell_label.setAlignment(self._alignment(column))
        return cell_label


class _ResultSection(QFrame):
    """결과 탭 공통 베이스"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._layout: QVBoxLayout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

        # 계산 전 안내 라벨
        self._empty_label: QLabel = QLabel(
            "계산하기를 누르면 결과가 표시됩니다.",
            self,
        )
        self._empty_label.setObjectName("panelEmptyLabel")
        self._empty_label.setFont(CustomFont(11))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._empty_label)

        self._content: QFrame = QFrame(self)
        self._content_layout: QVBoxLayout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._content.hide()
        self._layout.addWidget(self._content)

    def set_report(self, report: RefinementReport) -> None:
        """계산 결과 반영"""

        self._empty_label.hide()
        self._content.show()
        self.apply_report(report)

    def clear_report(self) -> None:
        """표시 중인 계산 결과 제거"""

        # 다른 기준으로 계산된 결과가 남지 않도록 초기 안내로 되돌림
        self._content.hide()
        self._empty_label.show()

    def apply_report(self, report: RefinementReport) -> None:
        """하위 클래스별 결과 반영"""

        raise NotImplementedError


class _SummarySection(_ResultSection):
    """요약 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._content_layout.addWidget(self._build_highlight_card())
        self._content_layout.addWidget(self._build_preparation_card())
        self._content_layout.addWidget(self._build_graph_card())

    def _build_highlight_card(self) -> SectionCard:
        """선택된 전략과 기대 소모량 카드 구성"""

        card: SectionCard = SectionCard(self._content, "선택된 전략과 기대 소모량")

        self._hero: _HeroValue = _HeroValue(card, "총 비용 기댓값")

        detail: QFrame = QFrame(card)
        detail_grid: QGridLayout = QGridLayout(detail)
        detail_grid.setContentsMargins(0, 0, 0, 0)
        detail_grid.setHorizontalSpacing(14)
        detail_grid.setVerticalSpacing(8)
        detail_grid.setColumnStretch(1, 1)

        self._strategy_tags: _TagList = _TagList(detail)
        self._stat_tags: _TagList = _TagList(detail)

        self._power_before_label: QLabel = QLabel("-", detail)
        self._power_before_label.setObjectName("powerResultLabel")
        self._power_before_label.setFont(CustomFont(11))

        self._power_after_label: QLabel = QLabel("", detail)
        self._power_after_label.setObjectName("powerResultLabel")
        self._power_after_label.setFont(CustomFont(11, bold=True))

        self._power_delta_label: QLabel = QLabel("", detail)
        self._power_delta_label.setObjectName("resultValueLabel")
        self._power_delta_label.setProperty("sign", "positive")
        self._power_delta_label.setFont(CustomFont(11, bold=True))

        power_row: QHBoxLayout = QHBoxLayout()
        power_row.setContentsMargins(0, 0, 0, 0)
        power_row.setSpacing(8)
        power_row.addWidget(self._power_before_label)
        power_row.addWidget(self._power_after_label)
        power_row.addWidget(self._power_delta_label)
        power_row.addStretch(1)

        for row_index, title in enumerate(
            ("전략", "목표 단계 스탯 변화량", "재련 전후 전투력")
        ):
            title_label: QLabel = QLabel(title, detail)
            title_label.setObjectName("resultsSubTitle")
            title_label.setFont(CustomFont(10))
            detail_grid.addWidget(
                title_label,
                row_index,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

        detail_grid.addWidget(
            self._strategy_tags,
            0,
            1,
            Qt.AlignmentFlag.AlignVCenter,
        )
        detail_grid.addWidget(
            self._stat_tags,
            1,
            1,
            Qt.AlignmentFlag.AlignVCenter,
        )
        detail_grid.addLayout(power_row, 2, 1)

        body: QHBoxLayout = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(14)
        body.addWidget(self._hero, 0)
        body.addWidget(detail, 1)
        card.add_layout(body)

        return card

    def _build_preparation_card(self) -> SectionCard:
        """준비량 카드 구성"""

        card: SectionCard = SectionCard(self._content, "준비량")
        self._preparation_table: _ResultTable = _ResultTable(
            card,
            ("기준", "필요 재련비", "필요 강화포인트", "도달 가능 단계", "현재 재화"),
        )
        card.add_widget(self._preparation_table)

        return card

    def _build_graph_card(self) -> SectionCard:
        """단계별 효율 그래프 카드 구성"""

        card: SectionCard = SectionCard(self._content, "단계별 효율")
        self._graph_container: QFrame = QFrame(card)
        self._graph_layout: QVBoxLayout = QVBoxLayout(self._graph_container)
        self._graph_layout.setContentsMargins(0, 0, 0, 0)
        self._graph_layout.setSpacing(8)
        card.add_widget(self._graph_container)

        return card

    def apply_report(self, report: RefinementReport) -> None:
        """요약 정보 갱신"""

        row: RefinementTargetRow = report.target_row

        # 총 비용 기댓값과 구성 요소
        self._hero.set_value(
            f"{row.expected.economic_cost:,.0f}",
            "전",
            (
                f"재련비 {_format_amount(row.expected.cost)}",
                f"포인트 {_format_points(row.expected.points)} → "
                f"{_format_amount(row.expected.points * report.point_price)}",
            ),
        )

        # 전략과 스탯 태그
        self._strategy_tags.set_tags(
            ((_strategy_name(report.strategy), True),)
            + tuple(
                (threshold, False)
                for threshold in _strategy_thresholds(report.strategy)
            )
        )
        stat_parts: tuple[str, ...] = _stat_delta_parts(row.stat_delta)
        self._stat_tags.set_tags(
            tuple((part, False) for part in stat_parts)
            if stat_parts
            else (("변화 없음", False),)
        )

        self._apply_power(report, row)
        self._apply_preparation(report, row)
        self._apply_graph(report)

    def _apply_power(
        self,
        report: RefinementReport,
        row: RefinementTargetRow,
    ) -> None:
        """재련 전후 전투력 표시 갱신"""

        if report.power_error is not None or row.power_delta is None:
            self._power_before_label.setText(f"계산 불가 ({report.power_error})")
            self._power_after_label.setText("")
            self._power_delta_label.setText("")
            return

        baseline: float = report.baseline_power or 0.0
        self._power_before_label.setText(f"{baseline:,.2f}  →")
        self._power_after_label.setText(f"{baseline + row.power_delta:,.2f}")
        self._power_delta_label.setText(_format_power(row.power_delta))

    def _apply_preparation(
        self,
        report: RefinementReport,
        row: RefinementTargetRow,
    ) -> None:
        """준비량 표 갱신"""

        reachable_map: dict[float, int] = dict(report.reachable_steps)
        preparation_rows: list[tuple[str | _ChipCell, ...]] = []
        for index, probability in enumerate(PREPARATION_PROBABILITIES):
            reachable_step: int = reachable_map[probability]
            required_cost: float = row.cost_quantiles[index]
            preparation_rows.append(
                (
                    f"{int(probability * 100)}% {_PREPARATION_LABELS[index]}",
                    _format_amount(required_cost),
                    _format_points(row.point_quantiles[index]),
                    f"{reachable_step}강",
                    _budget_chip(report.budget - required_cost),
                )
            )

        self._preparation_table.set_rows(tuple(preparation_rows))

    def _apply_graph(self, report: RefinementReport) -> None:
        """단계별 효율 그래프 재구성"""

        _clear_layout(self._graph_layout)
        _add_efficiency_delta_graph(
            self._graph_layout,
            self._graph_container,
            report,
        )


def _budget_chip(difference: float) -> _ChipCell:
    """보유 재화 대비 여유·부족 칸 구성"""

    if difference >= 0.0:
        return _ChipCell("여유", "ok")

    return _ChipCell("부족", "bad")


class _TargetAnalysisSection(_ResultSection):
    """목표·재화 분석 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._reach_probability_card: SectionCard = SectionCard(
            self._content,
            "단계별 도달 확률",
        )
        self._reach_probability_container: QFrame = QFrame(
            self._reach_probability_card
        )
        self._reach_probability_layout: QVBoxLayout = QVBoxLayout(
            self._reach_probability_container
        )
        self._reach_probability_layout.setContentsMargins(0, 0, 0, 0)
        self._reach_probability_layout.setSpacing(10)
        self._reach_probability_card.add_widget(self._reach_probability_container)
        self._content_layout.addWidget(self._reach_probability_card)

        self._distribution_card: SectionCard = SectionCard(
            self._content,
            "총 비용",
        )
        self._distribution_container: QFrame = QFrame(self._distribution_card)
        self._distribution_layout: QVBoxLayout = QVBoxLayout(
            self._distribution_container
        )
        self._distribution_layout.setContentsMargins(0, 0, 0, 0)
        self._distribution_layout.setSpacing(0)
        self._distribution_card.add_widget(self._distribution_container)
        self._content_layout.addWidget(self._distribution_card)

        total_cost_card: SectionCard = SectionCard(
            self._content,
            "단계별 총 비용 그래프",
        )
        self._total_cost_container: QFrame = QFrame(total_cost_card)
        self._total_cost_layout: QVBoxLayout = QVBoxLayout(
            self._total_cost_container
        )
        self._total_cost_layout.setContentsMargins(0, 0, 0, 0)
        self._total_cost_layout.setSpacing(10)
        total_cost_card.add_widget(self._total_cost_container)
        self._content_layout.addWidget(total_cost_card)

        expectation_card: SectionCard = SectionCard(
            self._content,
            "단계별 도달 확률과 기대 소모량",
        )
        self._expectation_table: _ResultTable = _ResultTable(
            expectation_card,
            (
                "목표",
                "도달 확률",
                "기대 재련비",
                "강화포인트",
                "총 비용",
                "현재 재화 대비",
            ),
        )
        expectation_card.add_widget(self._expectation_table)
        self._content_layout.addWidget(expectation_card)

        cost_card: SectionCard = SectionCard(self._content, "확률별 필요 재련비")
        self._cost_table: _ResultTable = _ResultTable(
            cost_card,
            _PREPARATION_TABLE_HEADERS,
        )
        cost_card.add_widget(self._cost_table)
        self._content_layout.addWidget(cost_card)

        point_card: SectionCard = SectionCard(self._content, "확률별 필요 강화포인트")
        self._point_table: _ResultTable = _ResultTable(
            point_card,
            _PREPARATION_TABLE_HEADERS,
        )
        point_card.add_widget(self._point_table)
        self._content_layout.addWidget(point_card)

    def apply_report(self, report: RefinementReport) -> None:
        """단계별 표와 분포 그래프 갱신"""

        highlight_index: int | None = None
        expectation_rows: list[tuple[str | _ChipCell, ...]] = []
        cost_rows: list[tuple[str | _ChipCell, ...]] = []
        point_rows: list[tuple[str | _ChipCell, ...]] = []

        for row_index, row in enumerate(report.rows):
            if row.target_step == report.target_step:
                highlight_index = row_index

            expectation_rows.append(
                (
                    f"{row.target_step}강",
                    _format_probability(row.reach_probability),
                    _format_amount(row.expected.cost),
                    _format_points(row.expected.points),
                    _format_amount(row.expected.economic_cost),
                    _budget_chip(report.budget - row.expected.cost),
                )
            )
            cost_rows.append(
                (
                    f"{row.target_step}강",
                    *(_format_amount(value) for value in row.cost_quantiles),
                )
            )
            point_rows.append(
                (
                    f"{row.target_step}강",
                    *(_format_points(value) for value in row.point_quantiles),
                )
            )

        self._expectation_table.set_rows(tuple(expectation_rows), highlight_index)
        self._cost_table.set_rows(tuple(cost_rows), highlight_index)
        self._point_table.set_rows(tuple(point_rows), highlight_index)

        self._distribution_card.set_title(f"{report.target_step}강 총 비용")
        self._apply_graphs(report)

    def _apply_graphs(self, report: RefinementReport) -> None:
        """총 비용 분포와 단계별 도달 확률·총 비용 그래프 재구성"""

        _clear_layout(self._distribution_layout)
        _clear_layout(self._reach_probability_layout)
        _clear_layout(self._total_cost_layout)
        row: RefinementTargetRow = report.target_row

        economic_distribution: RefinementDistribution = (
            report.economic_cost_distribution
        )
        minimum_economic_cost: float = min(
            cost + points * report.point_price
            for cost, points in zip(report.plan.costs, report.plan.assist_points)
        )
        self._distribution_layout.addWidget(
            _build_distribution_canvas(
                self._distribution_container,
                economic_distribution,
                row.expected.economic_cost,
                economic_distribution.quantile(
                    PREPARATION_PROBABILITIES[_DISTRIBUTION_PERCENTILE_INDEX]
                ),
                minimum_economic_cost,
                ("보유 재화", report.budget) if report.budget > 0.0 else None,
            )
        )

        target_steps: tuple[int, ...] = tuple(
            target_row.target_step for target_row in report.rows
        )
        reach_probabilities: tuple[float, ...] = tuple(
            target_row.reach_probability for target_row in report.rows
        )
        self._reach_probability_layout.addWidget(
            RefinementStepLineCanvas(
                self._reach_probability_container,
                "",
                target_steps,
                reach_probabilities,
                _format_probability,
                _REACH_PROBABILITY_GUIDE_VALUES,
                highlight_step=report.target_step,
                value_axis_formatter=lambda value: f"{value * 100:.0f}%",
                value_range=(0.0, 1.05),
            )
        )
        self._reach_probability_layout.addWidget(
            _GraphLegend(
                self._reach_probability_container,
                (("선택한 목표", get_graph_palette().dpm_median_bar, True),),
            )
        )

        total_costs: tuple[float, ...] = tuple(
            target_row.expected.economic_cost for target_row in report.rows
        )
        self._total_cost_layout.addWidget(
            RefinementStepBarCanvas(
                self._total_cost_container,
                "",
                target_steps,
                total_costs,
                _format_amount,
            )
        )


class _StatEfficiencySection(_ResultSection):
    """스탯 효율 탭"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        graph_card: SectionCard = SectionCard(self._content, "단계별 효율")
        self._graph_container: QFrame = QFrame(graph_card)
        self._graph_layout: QVBoxLayout = QVBoxLayout(self._graph_container)
        self._graph_layout.setContentsMargins(0, 0, 0, 0)
        self._graph_layout.setSpacing(10)
        graph_card.add_widget(self._graph_container)
        self._content_layout.addWidget(graph_card)

        power_card: SectionCard = SectionCard(self._content, "재련 전후 전투력")
        self._summary_list: _KeyValueList = _KeyValueList(power_card)
        power_card.add_widget(self._summary_list)
        self._content_layout.addWidget(power_card)

        table_card: SectionCard = SectionCard(self._content, "단계별 스탯")
        self._table: _ResultTable = _ResultTable(
            table_card,
            ("목표", "누적 스탯 상승", "전투력 상승", "총 비용"),
            text_columns=(1,),
        )
        table_card.add_widget(self._table)
        self._content_layout.addWidget(table_card)

    def apply_report(self, report: RefinementReport) -> None:
        """스탯 정보 갱신"""

        row: RefinementTargetRow = report.target_row
        equipment_label: str = REFINEMENT_EQUIPMENT_LABELS[report.equipment]

        # 재련 전후 전투력 요약
        if report.power_error is not None:
            power_rows: tuple[tuple[str, str], ...] = (
                ("기준 전투력", report.formula_label),
                ("재련 대상", f"{equipment_label} · {report.level_cap}제"),
                ("전투력 계산", f"계산 불가 ({report.power_error})"),
            )
            self._summary_list.set_rows(power_rows)

        else:
            baseline: float = report.baseline_power or 0.0
            delta: float = row.power_delta or 0.0
            power_rows = (
                ("기준 전투력", report.formula_label),
                ("재련 대상", f"{equipment_label} · {report.level_cap}제"),
                ("재련 전", f"{baseline:,.2f}"),
                ("재련 후", f"{baseline + delta:,.2f}"),
                ("상승", _format_power(delta)),
            )
            self._summary_list.set_rows(power_rows, positive_rows=(4,))

        # 단계별 스탯 표 구성
        highlight_index: int | None = None
        table_rows: list[tuple[str | _ChipCell, ...]] = []
        for row_index, target_row in enumerate(report.rows):
            if target_row.target_step == report.target_step:
                highlight_index = row_index

            table_rows.append(
                (
                    f"{target_row.target_step}강",
                    _format_stat_delta(target_row.stat_delta),
                    "-"
                    if target_row.power_delta is None
                    else _format_power(target_row.power_delta),
                    _format_amount(target_row.expected.economic_cost),
                )
            )

        self._table.set_rows(tuple(table_rows), highlight_index)

        # 단계별 효율 그래프 재구성
        _clear_layout(self._graph_layout)
        _add_efficiency_delta_graph(
            self._graph_layout,
            self._graph_container,
            report,
        )


class _LuckSection(_ResultSection):
    """운빨 분석 탭"""

    def __init__(
        self,
        parent: QWidget,
        on_actual_changed: Callable[[float], None],
    ) -> None:
        super().__init__(parent)

        self._on_actual_changed: Callable[[float], None] = on_actual_changed
        self._report: RefinementReport | None = None
        self._is_loading: bool = False

        # 사용 결과 입력 구성
        input_card: SectionCard = SectionCard(self._content, "사용 재련 결과 입력")
        self._cost_input: KVInput = KVInput(
            input_card,
            "사용 재련비 (전)",
            "0",
            self._on_input_changed,
            max_width=160,
            point_size=12,
        )
        _stretch_field(self._cost_input)
        self._cost_input.input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._cost_input.input.editingFinished.connect(
            lambda: _format_amount_input(
                self._cost_input.input,
                preserve_zero_buffer=False,
            )
        )
        input_card.add_widget(self._cost_input)
        self._content_layout.addWidget(input_card)

        cost_card: SectionCard = SectionCard(self._content, "재련비")
        self._cost_list: _KeyValueList = _KeyValueList(cost_card)
        cost_card.add_widget(self._cost_list)

        self._graph_container: QFrame = QFrame(cost_card)
        self._graph_layout: QVBoxLayout = QVBoxLayout(self._graph_container)
        self._graph_layout.setContentsMargins(0, 0, 0, 0)
        self._graph_layout.setSpacing(0)
        cost_card.add_widget(self._graph_container)
        self._content_layout.addWidget(cost_card)

    def load_inputs(self, refinement: RefinementInput) -> None:
        """저장된 사용 결과 입력 반영"""

        self._is_loading = True
        with QSignalBlocker(self._cost_input.input):
            self._cost_input.input.setText(f"{refinement.actual_cost:,.0f}")

        self._is_loading = False

    def apply_report(self, report: RefinementReport) -> None:
        """분포 기준 백분위 갱신"""

        self._report = report
        self._refresh_result()

    def clear_report(self) -> None:
        """비교 기준 분포 제거"""

        # 이전 계산 분포로 백분위가 갱신되지 않도록 참조까지 정리
        self._report = None
        _clear_layout(self._graph_layout)
        super().clear_report()

    def _on_input_changed(self) -> None:
        """사용 결과 입력 변경 처리"""

        if self._is_loading:
            return

        _format_amount_input(
            self._cost_input.input,
            preserve_zero_buffer=True,
        )

        actual_cost: float | None = _parse_amount(self._cost_input.input.text())

        self._cost_input.input.set_valid(
            actual_cost is not None and actual_cost <= _MAX_BUDGET
        )

        if actual_cost is None:
            return

        if actual_cost > _MAX_BUDGET:
            return

        self._on_actual_changed(actual_cost)
        self._refresh_result()

    def _refresh_result(self) -> None:
        """입력값 기준 백분위 결과 재구성"""

        report: RefinementReport | None = self._report
        if report is None:
            return

        actual_cost: float | None = _parse_amount(self._cost_input.input.text())
        if actual_cost is None:
            return

        row: RefinementTargetRow = report.target_row

        # 재련비 백분위 계산
        cost_ratio: float = report.cost_distribution.probability_at_most(actual_cost)
        self._cost_list.set_rows(
            (
                ("사용", _format_amount(actual_cost)),
                ("기대값", _format_amount(row.expected.cost)),
            ),
            chips={0: _luck_chip(cost_ratio)},
        )

        # 분포 위 내 결과 위치 그래프 재구성
        _clear_layout(self._graph_layout)
        self._graph_layout.addWidget(
            _build_distribution_canvas(
                self._graph_container,
                report.cost_distribution,
                row.expected.cost,
                row.cost_quantiles[_DISTRIBUTION_PERCENTILE_INDEX],
                min(report.plan.costs),
                ("사용 재련비", actual_cost),
            )
        )


def _luck_chip(ratio: float) -> _ChipCell:
    """백분위와 운 평가를 담은 칩 구성"""

    return _ChipCell(
        f"상위 {ratio * 100:.1f}% · {_luck_comment(ratio)}",
        _luck_tone(ratio),
    )


def _luck_tone(ratio: float) -> str:
    """백분위 기준 칩 색 반환"""

    # 적게 쓸수록 운이 좋은 결과
    if ratio <= 0.25:
        return "ok"

    if ratio <= 0.75:
        return "neutral"

    return "bad"


def _luck_comment(ratio: float) -> str:
    """백분위 기준 운 평가 문구 반환"""

    # 적게 쓸수록 운이 좋은 결과
    if ratio <= 0.25:
        return "운이 좋은 편"

    if ratio <= 0.75:
        return "평균 수준"

    return "운이 나쁜 편"


class _StrategySection(QFrame):
    """전략 관리 탭"""

    def __init__(
        self,
        parent: QWidget,
        on_strategies_changed: Callable[[], None],
        on_input_error: Callable[[str], None],
    ) -> None:
        super().__init__(parent)

        self._on_strategies_changed: Callable[[], None] = on_strategies_changed
        self._on_input_error: Callable[[str], None] = on_input_error
        self._editing_strategy_id: str | None = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 자동 최적 결과 표시
        auto_card: SectionCard = SectionCard(self, "자동 최적 전략")
        self._auto_empty_label: QLabel = QLabel(
            "자동 최적 전략을 선택하고 계산하면 결과가 표시됩니다.",
            auto_card,
        )
        self._auto_empty_label.setObjectName("panelEmptyLabel")
        self._auto_empty_label.setFont(CustomFont(11))
        self._auto_empty_label.setWordWrap(True)
        auto_card.add_widget(self._auto_empty_label)

        self._auto_list: _KeyValueList = _KeyValueList(auto_card)
        self._auto_list.hide()
        auto_card.add_widget(self._auto_list)
        layout.addWidget(auto_card)

        # 저장한 전략 목록
        list_card: SectionCard = SectionCard(self, "저장한 전략")
        self._list_container: QFrame = QFrame(list_card)
        self._list_layout: QVBoxLayout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        list_card.add_widget(self._list_container)
        layout.addWidget(list_card)

        # 전략 편집 폼
        self._editor_card: SectionCard = SectionCard(self, "전략 추가")
        self._name_input: KVInput = KVInput(
            self._editor_card,
            "전략 이름",
            "",
            self._on_form_changed,
            max_width=200,
            point_size=12,
        )
        self._assist3_input: KVComboInput = KVComboInput(
            self._editor_card,
            "3pt 시작 단계",
            [f"{step}강" for step in range(REFINE_ATTEMPT_STEP_COUNT)],
            self._on_form_changed,
        )
        self._assist7_input: KVComboInput = KVComboInput(
            self._editor_card,
            "7pt 시작 단계",
            [f"{step}강" for step in range(REFINE_ATTEMPT_STEP_COUNT)],
            self._on_form_changed,
        )

        self._save_button: StyledButton = StyledButton(
            self._editor_card,
            "전략 추가",
            kind="add",
            point_size=10,
        )
        self._save_button.setFixedHeight(32)
        self._save_button.clicked.connect(self._on_save_clicked)

        self._cancel_button: StyledButton = StyledButton(
            self._editor_card,
            "편집 취소",
            kind="normal",
            point_size=10,
        )
        self._cancel_button.setFixedHeight(32)
        self._cancel_button.clicked.connect(self._reset_form)
        self._cancel_button.hide()

        for field in (self._name_input, self._assist3_input, self._assist7_input):
            _stretch_field(field)

        form_grid: QGridLayout = QGridLayout()
        form_grid.setContentsMargins(0, 0, 0, 0)
        form_grid.setHorizontalSpacing(12)
        form_grid.setVerticalSpacing(10)
        form_grid.addWidget(self._name_input, 0, 0, 1, 2)
        form_grid.addWidget(self._assist3_input, 1, 0)
        form_grid.addWidget(self._assist7_input, 1, 1)
        form_grid.setColumnStretch(0, 1)
        form_grid.setColumnStretch(1, 1)
        self._editor_card.add_layout(form_grid)

        button_row: QHBoxLayout = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.addWidget(self._save_button)
        button_row.addWidget(self._cancel_button)
        button_row.addStretch(1)
        self._editor_card.add_layout(button_row)
        layout.addWidget(self._editor_card)

        # 편집 폼 초기 상태는 위젯 구성이 끝난 뒤에 적용
        self._reset_form()
        self.refresh_list()

    def set_report(self, report: RefinementReport) -> None:
        """자동 최적 결과 표시 갱신"""

        if report.strategy.mode != RefinementStrategyMode.AUTO:
            self.clear_report()
            return

        self._auto_list.set_rows(
            (
                ("선택 결과", " / ".join(_strategy_thresholds(report.strategy))),
                (
                    "기준",
                    f"{report.start_step}강 → {report.target_step}강",
                ),
                (
                    "총 비용 기댓값",
                    _format_amount(report.target_row.expected.economic_cost),
                ),
            )
        )
        self._auto_empty_label.hide()
        self._auto_list.show()

    def clear_report(self) -> None:
        """자동 최적 결과 표시 초기화"""

        self._auto_list.hide()
        self._auto_empty_label.show()

    def refresh_list(self) -> None:
        """저장한 전략 목록 재구성"""

        _clear_layout(self._list_layout)

        strategies: list[RefinementStrategy] = app_state.macro.refinement_strategies
        if not strategies:
            empty_label: QLabel = QLabel(
                "저장한 전략이 없습니다. 아래에서 전략을 추가해 주세요.",
                self._list_container,
            )
            empty_label.setObjectName("panelEmptyLabel")
            empty_label.setFont(CustomFont(10))
            self._list_layout.addWidget(empty_label)
            return

        for strategy in strategies:
            self._list_layout.addWidget(self._build_strategy_row(strategy))

    def _build_strategy_row(self, strategy: RefinementStrategy) -> QFrame:
        """전략 한 줄 위젯 구성"""

        row: QFrame = QFrame(self._list_container)
        row.setObjectName("powerResultRow")
        row.setProperty("selected", True)

        row_layout: QHBoxLayout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 6, 10, 6)
        row_layout.setSpacing(10)

        name_label: QLabel = QLabel(
            strategy.name if strategy.name.strip() else "이름 없음",
            row,
        )
        name_label.setObjectName("powerResultLabel")
        name_label.setFont(CustomFont(11, bold=True))

        detail_label: QLabel = QLabel(
            f"3pt {strategy.assist3_step}강↑ / 7pt {strategy.assist7_step}강↑",
            row,
        )
        detail_label.setObjectName("resultsSubTitle")
        detail_label.setFont(CustomFont(10))

        edit_button: StyledButton = StyledButton(row, "수정", point_size=9)
        edit_button.setFixedHeight(26)
        edit_button.clicked.connect(lambda: self._start_edit(strategy))

        delete_button: StyledButton = StyledButton(
            row,
            "삭제",
            kind="danger",
            point_size=9,
        )
        delete_button.setFixedHeight(26)
        delete_button.clicked.connect(lambda: self._delete_strategy(strategy))

        row_layout.addWidget(name_label)
        row_layout.addWidget(detail_label)
        row_layout.addStretch(1)
        row_layout.addWidget(edit_button)
        row_layout.addWidget(delete_button)

        return row

    def _start_edit(self, strategy: RefinementStrategy) -> None:
        """선택 전략을 편집 폼에 로드"""

        self._editing_strategy_id = strategy.id
        self._name_input.input.setText(strategy.name)
        self._assist3_input.combobox.setCurrentIndex(strategy.assist3_step)
        self._assist7_input.combobox.setCurrentIndex(strategy.assist7_step)
        self._save_button.setText("전략 저장")
        self._cancel_button.show()
        self._on_form_changed()

    def _reset_form(self) -> None:
        """편집 폼 초기화"""

        self._editing_strategy_id = None
        self._name_input.input.setText("")
        self._assist3_input.combobox.setCurrentIndex(0)
        self._assist7_input.combobox.setCurrentIndex(1)
        self._save_button.setText("전략 추가")
        self._cancel_button.hide()
        self._on_form_changed()

    def _on_form_changed(self) -> None:
        """전략 이름 입력 오류 표시 해제"""

        if self._name_input.input.text().strip():
            self._name_input.input.set_valid(True)

    def _current_form_error(self) -> str | None:
        """현재 편집 폼 입력 오류 반환"""

        if not self._name_input.input.text().strip():
            return "전략 이름을 입력해 주세요."

        return validate_strategy_thresholds(
            self._assist3_input.combobox.currentIndex(),
            self._assist7_input.combobox.currentIndex(),
        )

    def _on_save_clicked(self) -> None:
        """전략 추가 또는 수정 저장"""

        # 입력 오류는 알림으로 알리고 저장하지 않음
        error: str | None = self._current_form_error()
        if error is not None:
            self._name_input.input.set_valid(
                bool(self._name_input.input.text().strip())
            )
            self._on_input_error(error)
            return

        name: str = self._name_input.input.text().strip()
        assist3_step: int = self._assist3_input.combobox.currentIndex()
        assist7_step: int = self._assist7_input.combobox.currentIndex()

        # 편집 중이면 기존 전략을 갱신
        if self._editing_strategy_id is not None:
            for strategy in app_state.macro.refinement_strategies:
                if strategy.id != self._editing_strategy_id:
                    continue

                strategy.name = name
                strategy.assist3_step = assist3_step
                strategy.assist7_step = assist7_step
                break

        else:
            app_state.macro.refinement_strategies.append(
                RefinementStrategy(
                    name=name,
                    assist3_step=assist3_step,
                    assist7_step=assist7_step,
                )
            )

        save_data()
        self._reset_form()
        self.refresh_list()
        self._on_strategies_changed()

    def _delete_strategy(self, strategy: RefinementStrategy) -> None:
        """전략 삭제 및 모든 프리셋 선택 상태 복구"""

        app_state.macro.refinement_strategies.remove(strategy)

        # 삭제된 전략을 참조하는 프리셋을 유효한 기본 전략 모드로 복구
        for preset in app_state.macro.presets:
            refinement: RefinementInput = preset.info.calculator.refinement
            if refinement.selected_strategy_id == strategy.id:
                refinement.strategy_mode = RefinementStrategyMode.AUTO
                refinement.selected_strategy_id = ""

        # 편집 중이던 전략이 삭제되면 폼도 초기화
        if self._editing_strategy_id == strategy.id:
            self._reset_form()

        save_data()
        self.refresh_list()
        self._on_strategies_changed()


class _RefinementCancelledError(Exception):
    """재련 계산 취소 요청 전달용 내부 예외"""


class _RefinementThread(QThread):
    """백그라운드에서 재련 계산을 수행하는 스레드"""

    finished_signal = Signal(object, bool, str)
    progress_signal = Signal(str, int)

    def __init__(
        self,
        server_spec: object,
        preset: object,
        skills_info: dict,
        delay_ms: int,
        base_stats: BaseStats,
        custom_formulas: tuple[CustomPowerFormula, ...],
        refinement: RefinementInput,
        strategies: tuple[RefinementStrategy, ...],
        formula_label: str,
    ) -> None:
        super().__init__()

        self._server_spec = server_spec
        self._preset = preset
        self._skills_info = skills_info
        self._delay_ms = delay_ms
        self._base_stats = base_stats
        self._custom_formulas = custom_formulas
        self._refinement = refinement
        self._strategies = strategies
        self._formula_label = formula_label
        self._is_cancel_requested: bool = False

    def cancel(self) -> None:
        """계산 취소 요청 기록"""

        # 스레드 인터럽트와 내부 취소 플래그 동시 반영
        self._is_cancel_requested = True
        self.requestInterruption()

    def _ensure_not_cancelled(self) -> None:
        """취소 요청 시 내부 예외 발생"""

        if self._is_cancel_requested or self.isInterruptionRequested():
            raise _RefinementCancelledError()

    def _emit_progress(self, message: str, value: int) -> None:
        """진행 상태 시그널 방출"""

        self._ensure_not_cancelled()
        self.progress_signal.emit(message, value)

    def run(self) -> None:
        try:
            report: RefinementReport = build_refinement_report(
                server_spec=self._server_spec,  # type: ignore[arg-type]
                preset=self._preset,  # type: ignore[arg-type]
                skills_info=self._skills_info,
                delay_ms=self._delay_ms,
                base_stats=self._base_stats,
                custom_formulas=self._custom_formulas,
                refinement=self._refinement,
                strategies=self._strategies,
                formula_label=self._formula_label,
                progress_callback=self._emit_progress,
                cancel_checker=self._ensure_not_cancelled,
            )

            self._ensure_not_cancelled()
            self.progress_signal.emit("완료됨", 100)
            self.finished_signal.emit(report, False, "")

        except _RefinementCancelledError:
            self.finished_signal.emit(None, True, "")

        except RefinementInputError as error:
            self.finished_signal.emit(None, False, str(error))

        except Exception:
            self.finished_signal.emit(None, False, "재련 결과를 계산하지 못했습니다.")


class RefinementPage(QFrame):
    """계산기 5번째 탭에 들어가는 재련 시뮬레이터 화면"""

    def __init__(
        self,
        parent: QWidget,
        popup_manager: PopupManager,
        overlay: CalculationOverlay,
        on_content_resized: Callable[[], None],
    ) -> None:
        super().__init__(parent)

        self._popup_manager: PopupManager = popup_manager
        self._overlay: CalculationOverlay = overlay
        self._on_content_resized: Callable[[], None] = on_content_resized

        self._is_loading_state: bool = False
        self._thread: _RefinementThread | None = None
        self._report: RefinementReport | None = None
        self._report_preset_index: int | None = None
        self._formula_options: list[str] = []
        self._strategy_ids: list[str] = []

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title_label: QLabel = QLabel("재련 시뮬레이터", self)
        title_label.setObjectName("simTitle")
        title_label.setFont(CustomFont(16))
        layout.addWidget(title_label)

        self._split_box: _SplitBox = _SplitBox(self, self._on_content_resized)
        self._split_box.add_columns(
            self._build_input_column(self._split_box),
            self._build_result_column(self._split_box),
        )
        layout.addWidget(self._split_box)

        self.load_from_state()

    def _build_input_column(self, parent: QWidget) -> QWidget:
        """왼쪽 입력 열 구성"""

        column: QFrame = QFrame(parent)
        column.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )

        column_layout: QVBoxLayout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(10)

        column_layout.addWidget(self._build_target_card(column))
        column_layout.addWidget(self._build_resource_card(column))
        column_layout.addWidget(self._build_strategy_card(column))

        # 계산 버튼
        self._calculate_button: StyledButton = StyledButton(
            column,
            "계산하기",
            kind="add",
            point_size=12,
        )
        self._calculate_button.setFixedHeight(40)
        self._calculate_button.clicked.connect(self._on_calculate_clicked)
        column_layout.addWidget(self._calculate_button)

        column_layout.addStretch(1)

        return column

    def _build_target_card(self, parent: QWidget) -> SectionCard:
        """재련 대상 입력 카드 구성"""

        card: SectionCard = SectionCard(parent, "재련 대상")

        self._equipment_input: KVComboInput = KVComboInput(
            card,
            "장비 종류",
            [
                REFINEMENT_EQUIPMENT_LABELS[equipment]
                for equipment in RefinementEquipment
            ],
            self._on_input_changed,
        )
        self._level_cap_input: KVComboInput = KVComboInput(
            card,
            "레벨제",
            [f"{level_cap}제" for level_cap in REFINE_LEVEL_CAPS],
            self._on_input_changed,
        )
        self._start_step_input: KVComboInput = KVComboInput(
            card,
            "시작 단계",
            [f"{step}강" for step in range(MAX_REFINE_STEP)],
            self._on_start_step_changed,
        )
        self._target_step_input: KVComboInput = KVComboInput(
            card,
            "목표 단계",
            [f"{step}강" for step in range(1, MAX_REFINE_STEP + 1)],
            self._on_target_step_changed,
        )

        grid: QGridLayout = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.addWidget(self._equipment_input, 0, 0)
        grid.addWidget(self._level_cap_input, 0, 1)
        grid.addWidget(self._start_step_input, 1, 0)
        grid.addWidget(self._target_step_input, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        card.add_layout(grid)

        for field in (
            self._equipment_input,
            self._level_cap_input,
            self._start_step_input,
            self._target_step_input,
        ):
            _stretch_field(field)

        return card

    def _build_resource_card(self, parent: QWidget) -> SectionCard:
        """재화와 할인 입력 카드 구성"""

        card: SectionCard = SectionCard(parent, "재화와 할인")

        self._budget_input: KVInput = KVInput(
            card,
            "보유 재화 (전)",
            "0",
            lambda: self._on_amount_input_changed(self._budget_input.input),
            max_width=260,
            point_size=12,
        )
        self._bundle_price_input: KVInput = KVInput(
            card,
            f"강화주머니(+{POINT_BUNDLE_SIZE}pt) 가격 (전)",
            "0",
            lambda: self._on_amount_input_changed(self._bundle_price_input.input),
            max_width=260,
            point_size=12,
        )

        self._refine_pet_check: QCheckBox = QCheckBox("재련펫 (-5%)", card)
        self._refine_pet_check.setFont(CustomFont(11))
        self._refine_pet_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refine_pet_check.stateChanged.connect(self._on_input_changed)

        self._vip_check: QCheckBox = QCheckBox("VIP (-10%)", card)
        self._vip_check.setFont(CustomFont(11))
        self._vip_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self._vip_check.stateChanged.connect(self._on_input_changed)

        for field in (self._budget_input, self._bundle_price_input):
            _stretch_field(field)
            field.input.setAlignment(Qt.AlignmentFlag.AlignRight)
            field.input.editingFinished.connect(
                lambda input_widget=field.input: _format_amount_input(
                    input_widget,
                    preserve_zero_buffer=False,
                )
            )

        card.add_widget(self._budget_input)
        card.add_widget(self._bundle_price_input)
        card.add_widget(self._refine_pet_check)
        card.add_widget(self._vip_check)

        return card

    def _build_strategy_card(self, parent: QWidget) -> SectionCard:
        """전략과 전투력 공식 입력 카드 구성"""

        card: SectionCard = SectionCard(parent, "전략과 기준 전투력")

        self._strategy_mode_input: KVComboInput = KVComboInput(
            card,
            "전략",
            ["무보조", "자동 최적", "사용자 전략"],
            self._on_strategy_mode_changed,
        )
        self._strategy_input: KVComboInput = KVComboInput(
            card,
            "사용자 전략",
            [""],
            self._on_input_changed,
        )
        self._formula_input: KVComboInput = KVComboInput(
            card,
            "기준 전투력",
            [""],
            self._on_input_changed,
        )

        for field in (
            self._strategy_mode_input,
            self._strategy_input,
            self._formula_input,
        ):
            _stretch_field(field)

        card.add_widget(self._strategy_mode_input)
        card.add_widget(self._strategy_input)
        card.add_widget(self._formula_input)

        return card

    def _build_result_column(self, parent: QWidget) -> QWidget:
        """오른쪽 결과 열 구성"""

        column: QFrame = QFrame(parent)
        column.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        column_layout: QVBoxLayout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(10)

        self._kpi_row: _KpiRow = _KpiRow(column)
        column_layout.addWidget(self._kpi_row)

        # 알약 탭 바 구성
        tab_bar: QFrame = QFrame(column)
        tab_bar.setObjectName("refinementTabBar")
        tab_layout: FlowLayout = FlowLayout(tab_bar, margin=0, spacing=6)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self._tabs: list[PillTab] = []
        for index, label in enumerate(_RESULT_TAB_LABELS):
            pill: PillTab = PillTab(tab_bar, label, index, self._go_tab)
            self._tabs.append(pill)
            tab_layout.addWidget(pill)

        tab_bar.setLayout(tab_layout)
        column_layout.addWidget(tab_bar)

        # 결과 섹션 구성
        self._stack: _TabStack = _TabStack(column)
        self._summary_section: _SummarySection = _SummarySection(self._stack)
        self._target_section: _TargetAnalysisSection = _TargetAnalysisSection(
            self._stack
        )
        self._strategy_section: _StrategySection = _StrategySection(
            self._stack,
            self._on_strategies_changed,
            self._show_input_error,
        )
        self._stat_section: _StatEfficiencySection = _StatEfficiencySection(self._stack)
        self._luck_section: _LuckSection = _LuckSection(
            self._stack,
            self._on_actual_result_changed,
        )

        self._stack.add_page(self._summary_section)
        self._stack.add_page(self._target_section)
        self._stack.add_page(self._strategy_section)
        self._stack.add_page(self._stat_section)
        self._stack.add_page(self._luck_section)
        column_layout.addWidget(self._stack)
        column_layout.addStretch(1)

        self._go_tab(0)
        return column

    def _go_tab(self, index: int) -> None:
        """결과 탭 전환"""

        self._stack.set_current_index(index)
        for tab_index, pill in enumerate(self._tabs):
            pill.setChecked(tab_index == index)

        self._sync_content_height()

    def _sync_content_height(self) -> None:
        """내용 변경 후 화면 높이 재계산"""

        # 탭 전환이나 결과 반영으로 필요한 높이가 달라진다
        self._split_box.sync_height()
        self._on_content_resized()

    def _get_refinement_input(self) -> RefinementInput:
        """현재 프리셋의 재련 입력 상태 조회"""

        calculator_input: CalculatorPresetInput = (
            app_state.macro.current_preset.info.calculator
        )
        return calculator_input.refinement

    def on_enter(self) -> None:
        """재련 화면 진입 시 저장 상태 동기화"""

        # 다른 프리셋의 스탯으로 계산된 결과는 유지하지 않음
        if (
            self._report is not None
            and self._report_preset_index != app_state.macro.current_preset_index
        ):
            self._clear_report()

        self.load_from_state()

    def _clear_report(self) -> None:
        """표시 중인 계산 결과 제거"""

        self._report = None
        self._report_preset_index = None
        self._kpi_row.clear_report()
        self._summary_section.clear_report()
        self._target_section.clear_report()
        self._strategy_section.clear_report()
        self._stat_section.clear_report()
        self._luck_section.clear_report()
        self._sync_content_height()

    def load_from_state(self) -> None:
        """저장된 입력 상태를 위젯에 반영"""

        self._is_loading_state = True

        refinement: RefinementInput = self._get_refinement_input()

        # 장비·레벨제·단계 선택 반영
        equipment_index: int = list(RefinementEquipment).index(refinement.equipment)
        self._equipment_input.combobox.setCurrentIndex(equipment_index)
        self._level_cap_input.combobox.setCurrentIndex(
            REFINE_LEVEL_CAPS.index(refinement.level_cap)
        )
        self._start_step_input.combobox.setCurrentIndex(refinement.start_step)
        self._target_step_input.combobox.setCurrentIndex(refinement.target_step - 1)

        # 재화와 할인 반영
        self._budget_input.input.setText(f"{refinement.budget:,.0f}")
        self._bundle_price_input.input.setText(
            f"{refinement.point_bundle_price:,.0f}"
        )
        self._refine_pet_check.setChecked(refinement.use_refine_pet)
        self._vip_check.setChecked(refinement.use_vip)

        # 전략 선택지 반영
        mode_index: int = list(RefinementStrategyMode).index(refinement.strategy_mode)
        self._strategy_mode_input.combobox.setCurrentIndex(mode_index)
        self._refresh_strategy_options()

        # 전투력 공식 선택지 반영
        self._refresh_formula_options()

        # 운빨 분석 입력 반영
        self._luck_section.load_inputs(refinement)

        self._is_loading_state = False

        self._update_strategy_enabled()

    def _refresh_strategy_options(self) -> None:
        """사용자 전략 드롭다운 갱신"""

        refinement: RefinementInput = self._get_refinement_input()
        strategies: list[RefinementStrategy] = app_state.macro.refinement_strategies
        self._strategy_ids = [strategy.id for strategy in strategies]

        combobox = self._strategy_input.combobox
        with QSignalBlocker(combobox):
            combobox.clear()
            if not strategies:
                combobox.addItem("저장한 전략 없음")

            else:
                combobox.addItems(
                    [
                        strategy.name if strategy.name.strip() else "이름 없음"
                        for strategy in strategies
                    ]
                )

                # 저장된 선택 전략 복원
                if refinement.selected_strategy_id in self._strategy_ids:
                    combobox.setCurrentIndex(
                        self._strategy_ids.index(refinement.selected_strategy_id)
                    )

        # 전략 이름 길이에 맞춰 드롭다운 폭 재계산
        self._strategy_input.sync_width_to_items()

    def _refresh_formula_options(self) -> None:
        """전투력 공식 드롭다운 갱신"""

        refinement: RefinementInput = self._get_refinement_input()
        formula_labels: dict[str, str] = build_formula_label_map(
            app_state.macro.custom_power_formulas
        )
        self._formula_options = build_formula_options(
            app_state.macro.custom_power_formulas
        )

        combobox = self._formula_input.combobox
        with QSignalBlocker(combobox):
            combobox.clear()
            combobox.addItems(
                [formula_labels[formula_id] for formula_id in self._formula_options]
            )

            # 저장된 선택 공식 복원 (삭제된 공식은 첫 항목으로 대체)
            if refinement.selected_formula_id in self._formula_options:
                combobox.setCurrentIndex(
                    self._formula_options.index(refinement.selected_formula_id)
                )

            else:
                combobox.setCurrentIndex(0)

        # 공식 이름 길이에 맞춰 드롭다운 폭 재계산
        self._formula_input.sync_width_to_items()

    def _update_strategy_enabled(self) -> None:
        """전략 방식에 따른 사용자 전략 선택 활성화"""

        is_user_mode: bool = (
            self._strategy_mode_input.combobox.currentIndex()
            == list(RefinementStrategyMode).index(RefinementStrategyMode.USER)
        )
        self._strategy_input.combobox.setEnabled(
            is_user_mode and bool(self._strategy_ids)
        )

    def _on_start_step_changed(self) -> None:
        """시작 단계 변경 처리"""

        if self._is_loading_state:
            return

        # 목표 단계가 시작 단계 이하가 되지 않도록 보정
        start_step: int = self._start_step_input.combobox.currentIndex()
        target_step: int = self._target_step_input.combobox.currentIndex() + 1
        if target_step <= start_step:
            with QSignalBlocker(self._target_step_input.combobox):
                self._target_step_input.combobox.setCurrentIndex(start_step)

        self._on_input_changed()

    def _on_target_step_changed(self) -> None:
        """목표 단계 변경 처리"""

        if self._is_loading_state:
            return

        # 시작 단계가 목표 단계 이상이 되지 않도록 보정
        start_step: int = self._start_step_input.combobox.currentIndex()
        target_step: int = self._target_step_input.combobox.currentIndex() + 1
        if target_step <= start_step:
            with QSignalBlocker(self._start_step_input.combobox):
                self._start_step_input.combobox.setCurrentIndex(target_step - 1)

        self._on_input_changed()

    def _on_strategy_mode_changed(self) -> None:
        """전략 방식 변경 처리"""

        if self._is_loading_state:
            return

        self._update_strategy_enabled()
        self._on_input_changed()

    def _on_strategies_changed(self) -> None:
        """전략 목록 변경 후 선택지 동기화"""

        refinement: RefinementInput = self._get_refinement_input()
        self._is_loading_state = True
        self._strategy_mode_input.combobox.setCurrentIndex(
            list(RefinementStrategyMode).index(refinement.strategy_mode)
        )
        self._refresh_strategy_options()
        self._is_loading_state = False

        self._update_strategy_enabled()
        if refinement.strategy_mode == RefinementStrategyMode.USER:
            self._on_input_changed()

        self._sync_content_height()

    def _on_actual_result_changed(self, actual_cost: float) -> None:
        """운빨 분석 입력 저장"""

        refinement: RefinementInput = self._get_refinement_input()
        refinement.actual_cost = actual_cost
        save_data()

    def _on_amount_input_changed(self, input_widget: CustomLineEdit) -> None:
        """재화 입력 서식 적용 후 상태 반영"""

        _format_amount_input(input_widget, preserve_zero_buffer=True)
        self._on_input_changed()

    def _on_input_changed(self) -> None:
        """입력 변경 시 저장 상태 반영"""

        if self._is_loading_state:
            return

        refinement: RefinementInput = self._get_refinement_input()

        # 선택형 입력 반영
        refinement.equipment = list(RefinementEquipment)[
            self._equipment_input.combobox.currentIndex()
        ]
        refinement.level_cap = REFINE_LEVEL_CAPS[
            self._level_cap_input.combobox.currentIndex()
        ]
        refinement.start_step = self._start_step_input.combobox.currentIndex()
        refinement.target_step = self._target_step_input.combobox.currentIndex() + 1
        refinement.use_refine_pet = self._refine_pet_check.isChecked()
        refinement.use_vip = self._vip_check.isChecked()
        refinement.strategy_mode = list(RefinementStrategyMode)[
            self._strategy_mode_input.combobox.currentIndex()
        ]

        # 사용자 전략 선택 반영
        strategy_index: int = self._strategy_input.combobox.currentIndex()
        if 0 <= strategy_index < len(self._strategy_ids):
            refinement.selected_strategy_id = self._strategy_ids[strategy_index]

        else:
            refinement.selected_strategy_id = ""

        # 전투력 공식 선택 반영
        formula_index: int = self._formula_input.combobox.currentIndex()
        if 0 <= formula_index < len(self._formula_options):
            refinement.selected_formula_id = self._formula_options[formula_index]

        # 수치 입력 검증 후 반영
        budget: float | None = _parse_amount(self._budget_input.input.text())
        is_budget_valid: bool = budget is not None and budget <= _MAX_BUDGET
        self._budget_input.input.set_valid(is_budget_valid)
        if is_budget_valid and budget is not None:
            refinement.budget = budget

        bundle_price: float | None = _parse_amount(
            self._bundle_price_input.input.text()
        )
        is_price_valid: bool = (
            bundle_price is not None and bundle_price <= _MAX_BUNDLE_PRICE
        )
        self._bundle_price_input.input.set_valid(is_price_valid)
        if is_price_valid and bundle_price is not None:
            refinement.point_bundle_price = bundle_price

        save_data()

    def _on_calculate_clicked(self) -> None:
        """계산 시작 요청 처리"""

        # 계산 중 중복 실행 차단
        if self._thread is not None and self._thread.isRunning():
            return

        refinement: RefinementInput = self._get_refinement_input()
        strategies: tuple[RefinementStrategy, ...] = tuple(
            app_state.macro.refinement_strategies
        )

        # 수치 입력 오류 확인
        if not self._budget_input.input.property("valid"):
            self._show_input_error("보유 재화는 숫자로 입력해 주세요.")
            return

        if not self._bundle_price_input.input.property("valid"):
            self._show_input_error("강화주머니 가격은 숫자로 입력해 주세요.")
            return

        input_error: str | None = validate_refinement_input(refinement, strategies)
        if input_error is not None:
            self._show_input_error(input_error)
            return

        formula_labels: dict[str, str] = build_formula_label_map(
            app_state.macro.custom_power_formulas
        )
        formula_label: str = formula_labels.get(
            refinement.selected_formula_id,
            "기준 전투력",
        )

        preset = app_state.macro.current_preset
        self._thread = _RefinementThread(
            server_spec=app_state.macro.current_server,
            preset=preset,
            skills_info=preset.usage_settings,
            delay_ms=app_state.macro.current_delay,
            base_stats=preset.info.calculator.base_stats,
            custom_formulas=tuple(app_state.macro.custom_power_formulas),
            refinement=refinement,
            strategies=strategies,
            formula_label=formula_label,
        )
        self._thread.progress_signal.connect(self._on_progress)
        self._thread.finished_signal.connect(self._on_finished)
        self._thread.finished.connect(self._cleanup_thread)

        self._calculate_button.setEnabled(False)
        self._overlay.show_overlay("재련 결과 계산 중...", "대기 중...", 0)
        self._thread.start()

    def _show_input_error(self, message: str) -> None:
        """입력 오류 알림 표시"""

        self._popup_manager.show_notice(NoticeKind.SIM_INPUT_ERROR, message)

    def _on_progress(self, message: str, value: int) -> None:
        """계산 진행 상태 반영"""

        self._overlay.update_progress(message, value)

    def _on_finished(
        self,
        report: object,
        is_cancelled: bool,
        error_message: str,
    ) -> None:
        """계산 완료 결과 반영"""

        self._overlay.hide()
        self._calculate_button.setEnabled(True)

        if is_cancelled:
            return

        if not isinstance(report, RefinementReport):
            self._show_input_error(
                error_message or "재련 결과를 계산하지 못했습니다."
            )
            return

        self._report = report
        self._report_preset_index = app_state.macro.current_preset_index
        self._kpi_row.set_report(report)
        self._summary_section.set_report(report)
        self._target_section.set_report(report)
        self._strategy_section.set_report(report)
        self._stat_section.set_report(report)
        self._luck_section.set_report(report)

        self._go_tab(0)

    def _cleanup_thread(self) -> None:
        """QThread 완전 종료 후 참조 정리"""

        if self._thread is None:
            return

        self._thread.progress_signal.disconnect()
        self._thread.finished_signal.disconnect()
        self._thread.deleteLater()
        self._thread = None

    def cancel_calculation(self) -> None:
        """진행 중인 계산 취소 요청"""

        if self._thread is None or not self._thread.isRunning():
            return

        self._overlay.set_cancelling()
        self._thread.cancel()

    def cancel_calculation_for_shutdown(self) -> None:
        """프로그램 종료 전 계산 스레드 정리"""

        if self._thread is None:
            return

        # 종료 시에는 결과 반영 없이 스레드 종료를 기다림
        if self._thread.isRunning():
            self._thread.cancel()
            self._thread.wait(3000)
