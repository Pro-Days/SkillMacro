from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayoutItem,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from app.scripts.calculator_models import (
    STAT_SPECS,
    OptimizationCandidateGroup,
    OptimizationCandidateOption,
    OptimizationCandidateStat,
    StatKey,
)
from app.scripts.custom_classes import (
    CustomComboBox,
    CustomFont,
    CustomLineEdit,
    StyledButton,
)


class CandidateGroupInputs(QFrame):
    @dataclass(slots=True)
    class CandidateGroupState:
        """후보 그룹 UI 상태"""

        item: "CandidateGroupInputs.GroupListItem"
        candidates: list["CandidateGroupInputs.CandidateCard"]
        candidate_items: dict[
            "CandidateGroupInputs.CandidateCard",
            "CandidateGroupInputs.CandidateListItem",
        ]
        selected_candidate: "CandidateGroupInputs.CandidateCard | None"

    class CandidateStatRow(QFrame):
        def __init__(
            self,
            parent: QWidget,
            connected_function: Callable[[], None],
            remove_function: Callable[
                ["CandidateGroupInputs.CandidateStatRow"],
                None,
            ],
            data: OptimizationCandidateStat | None = None,
        ) -> None:
            super().__init__(parent)

            # 스탯 행 입력 위젯 구성
            self._connected_function: Callable[[], None] = connected_function
            self._remove_function = remove_function
            self._stat_options: list[StatKey] = list(STAT_SPECS.keys())
            layout: QHBoxLayout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            self.stat_combobox = CustomComboBox(self, list(STAT_SPECS.values()))
            self.stat_combobox.setMinimumHeight(32)
            self.stat_combobox.setMinimumWidth(150)
            if data is not None:
                self.stat_combobox.setCurrentIndex(
                    self._stat_options.index(data.stat_key)
                )
            self.stat_combobox.currentIndexChanged.connect(
                lambda _index: self._connected_function()
            )

            self._last_valid_value: str = "0" if data is None else f"{data.value:g}"
            self.value_input: CustomLineEdit = CustomLineEdit(
                self,
                connected_function,
                "" if data is None else f"{data.value:g}",
                point_size=10,
            )
            self.value_input.setFixedWidth(64)
            self.value_input.setFixedHeight(32)
            self.value_input.editingFinished.connect(self._correct_value)

            remove_button: StyledButton = StyledButton(
                self, "삭제", kind="danger", point_size=8
            )
            remove_button.setFixedHeight(28)
            remove_button.clicked.connect(
                lambda _checked=False: self._remove_function(self)
            )

            layout.addWidget(self.stat_combobox, 1)
            layout.addWidget(self.value_input)
            layout.addWidget(remove_button)
            self.setLayout(layout)

        def _correct_value(self) -> None:
            """수치가 비정상이면 직전 유효값으로 보정"""

            # 실수로 해석 가능하면 유효값 갱신, 아니면 이전 값 복원
            try:
                float(self.value_input.text())
            except ValueError:
                self.value_input.setText(self._last_valid_value)
                return

            self._last_valid_value = self.value_input.text()

        def get_value(self) -> OptimizationCandidateStat:
            """스탯 행 데이터 복원"""

            # 비정상 수치는 직전 유효값으로 대체해 항상 유효한 스탯 반환
            stat_key: StatKey = self._stat_options[self.stat_combobox.currentIndex()]
            try:
                value: float = float(self.value_input.text())
            except ValueError:
                value = float(self._last_valid_value)

            return OptimizationCandidateStat(stat_key=stat_key, value=value)

    class GroupListItem(QFrame):
        def __init__(
            self,
            parent: QWidget,
            select_function: Callable[
                ["CandidateGroupInputs.GroupListItem"],
                None,
            ],
            remove_function: Callable[
                ["CandidateGroupInputs.GroupListItem"],
                None,
            ],
            name_changed_function: Callable[
                ["CandidateGroupInputs.GroupListItem"],
                None,
            ],
            selection_changed_function: Callable[
                ["CandidateGroupInputs.GroupListItem"],
                None,
            ],
            default_name: str,
            data: OptimizationCandidateGroup | None = None,
        ) -> None:
            super().__init__(parent)

            # 그룹 목록 카드 입력 구성
            self._select_function = select_function
            self._remove_function = remove_function
            self._name_changed_function = name_changed_function
            self._selection_changed_function = selection_changed_function
            self.setObjectName("candidateGroupItem")
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            layout: QVBoxLayout = QVBoxLayout(self)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(8)

            # 그룹명 행: 라벨과 입력칸을 가로로 배치 (비울 수 없어 신규 그룹은 기본명으로 시작)
            initial_name: str = data.name if data is not None else default_name
            self._last_valid_name: str = initial_name
            name_label: QLabel = QLabel("그룹명", self)
            name_label.setFont(CustomFont(10))
            # 두 행 라벨 폭을 더 긴 '그룹명' 기준으로 통일해 입력칸 시작점 정렬
            label_width: int = name_label.sizeHint().width()
            name_label.setFixedWidth(label_width)
            self.name_input: CustomLineEdit = CustomLineEdit(
                self,
                lambda: self._name_changed_function(self),
                initial_name,
                point_size=10,
            )
            self.name_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.name_input.setFixedHeight(30)
            self.name_input.editingFinished.connect(self._restore_name_if_empty)
            remove_button: StyledButton = StyledButton(
                self, "삭제", kind="danger", point_size=8
            )
            remove_button.setFixedHeight(28)
            remove_button.clicked.connect(
                lambda _checked=False: self._remove_function(self)
            )
            name_row: QHBoxLayout = QHBoxLayout()
            name_row.setContentsMargins(0, 0, 0, 0)
            name_row.setSpacing(6)
            name_row.addWidget(name_label, 0, Qt.AlignmentFlag.AlignVCenter)
            name_row.addWidget(self.name_input, 1)
            name_row.addWidget(remove_button, 0, Qt.AlignmentFlag.AlignVCenter)

            # 선택 개수 행: 선택 개수 입력과 후보 수 표시
            selection_text: str = "1" if data is None else str(data.selection_count)
            self._last_valid_selection: str = selection_text
            selection_label: QLabel = QLabel("선택", self)
            selection_label.setFont(CustomFont(10))
            selection_label.setFixedWidth(label_width)
            self.selection_input: CustomLineEdit = CustomLineEdit(
                self,
                lambda: self._selection_changed_function(self),
                selection_text,
                point_size=10,
            )
            self.selection_input.setFixedHeight(30)
            self.selection_input.setFixedWidth(48)
            self.selection_input.editingFinished.connect(self._correct_selection)
            self.candidate_count_label: QLabel = QLabel("/ 후보 0개", self)
            self.candidate_count_label.setObjectName("candidateCountLabel")
            self.candidate_count_label.setFont(CustomFont(10))

            meta_row: QHBoxLayout = QHBoxLayout()
            meta_row.setContentsMargins(0, 0, 0, 0)
            meta_row.setSpacing(6)
            meta_row.addWidget(selection_label, 0, Qt.AlignmentFlag.AlignVCenter)
            meta_row.addWidget(self.selection_input, 0, Qt.AlignmentFlag.AlignVCenter)
            meta_row.addWidget(
                self.candidate_count_label, 0, Qt.AlignmentFlag.AlignVCenter
            )
            meta_row.addStretch(1)

            layout.addLayout(name_row)
            layout.addLayout(meta_row)
            self.installEventFilter(self)
            self.name_input.installEventFilter(self)
            self.selection_input.installEventFilter(self)

        def set_candidate_count(self, count: int) -> None:
            """후보 수 표시 갱신"""

            # 카드에 현재 그룹의 후보 수 반영
            self.candidate_count_label.setText(f"/ 후보 {count}개")

        def eventFilter(self, watched: QObject, event: QEvent) -> bool:
            """그룹 항목 클릭 선택 처리"""

            # 입력칸 클릭도 현재 그룹 선택으로 반영
            if event.type() == QEvent.Type.MouseButtonPress:
                self._select_function(self)

            return super().eventFilter(watched, event)

        def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore
            """그룹 항목 배경 클릭 선택 처리"""

            # 카드 배경 클릭 선택 처리
            self._select_function(self)
            return super().mousePressEvent(event)

        def set_selected_state(self, is_selected: bool) -> None:
            """그룹 선택 표시 반영"""

            # 선택 상태 속성 갱신
            self.setProperty("selected", is_selected)
            self.style().unpolish(self)
            self.style().polish(self)

        def _correct_selection(self) -> None:
            """선택 개수가 비정상이면 직전 유효값으로 보정"""

            # 1 이상 정수가 아니면 이전 값 복원, 맞으면 유효값 갱신
            selection_text: str = self.selection_input.text()
            if selection_text.isdigit() and int(selection_text) >= 1:
                self._last_valid_selection = selection_text
                return

            self.selection_input.setText(self._last_valid_selection)

        def _restore_name_if_empty(self) -> None:
            """그룹명이 비면 직전 유효값으로 복원"""

            # 비어 있으면 이전 입력값 복원, 아니면 유효값 갱신
            current_name: str = self.name_input.text().strip()
            if not current_name:
                self.name_input.setText(self._last_valid_name)
                return

            self._last_valid_name = current_name

        def build_group_header(self) -> tuple[str, int]:
            """그룹 이름과 선택 개수 복원"""

            # 빈 그룹명은 직전 유효값으로 대체해 비지 않도록 보장
            group_name: str = self.name_input.text().strip() or self._last_valid_name

            # 비정상 선택 개수는 직전 유효값으로 대체
            selection_text: str = self.selection_input.text()
            if selection_text.isdigit() and int(selection_text) >= 1:
                return group_name, int(selection_text)

            return group_name, int(self._last_valid_selection)

    class CandidateListItem(QFrame):
        def __init__(
            self,
            parent: QWidget,
            select_function: Callable[
                ["CandidateGroupInputs.CandidateCard"],
                None,
            ],
            remove_function: Callable[
                ["CandidateGroupInputs.CandidateCard"],
                None,
            ],
            target_card: "CandidateGroupInputs.CandidateCard",
        ) -> None:
            super().__init__(parent)

            # 후보 목록 행 구성
            self._target_card = target_card
            self._select_function = select_function
            self._remove_function = remove_function
            self.setMinimumHeight(48)
            layout: QGridLayout = QGridLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            self.select_button: QPushButton = QPushButton("", self)
            self.select_button.setObjectName("candidateListSelectBtn")
            self.select_button.setCheckable(True)
            self.select_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.select_button.setMinimumHeight(48)
            self.select_button.setFont(CustomFont(10, bold=True))
            self.select_button.clicked.connect(
                lambda _checked=False: self._select_function(self._target_card)
            )

            actions_widget: QWidget = QWidget(self)
            actions_layout: QHBoxLayout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 8, 0)
            actions_layout.setSpacing(6)
            remove_button: StyledButton = StyledButton(
                self, "삭제", kind="danger", point_size=8
            )
            remove_button.setFixedHeight(24)
            remove_button.clicked.connect(
                lambda _checked=False: self._remove_function(self._target_card)
            )
            actions_layout.addWidget(remove_button)
            actions_widget.setLayout(actions_layout)

            layout.addWidget(self.select_button, 0, 0)
            layout.addWidget(
                actions_widget,
                0,
                0,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
            )
            self.setLayout(layout)

        def set_title_text(self, text: str) -> None:
            """후보 목록 표시명 반영"""

            # 후보 버튼 문구 갱신
            self.select_button.setText(text)

        def set_selected_state(self, is_selected: bool) -> None:
            """후보 선택 표시 반영"""

            # 후보 버튼 선택 상태 갱신
            self.select_button.setChecked(is_selected)

    class CandidateCard(QFrame):
        def __init__(
            self,
            parent: QWidget,
            value_changed_function: Callable[[], None],
            name_changed_function: Callable[
                ["CandidateGroupInputs.CandidateCard"],
                None,
            ],
            default_name: str,
            data: OptimizationCandidateOption | None = None,
        ) -> None:
            super().__init__(parent)

            # 후보 상세 편집 카드 구성
            self.setObjectName("candidateDetailCard")
            self._value_changed_function: Callable[[], None] = value_changed_function
            self._name_changed_function = name_changed_function
            self.stat_rows: list[CandidateGroupInputs.CandidateStatRow] = []
            root_layout: QVBoxLayout = QVBoxLayout(self)
            root_layout.setContentsMargins(12, 12, 12, 12)
            root_layout.setSpacing(8)

            # 후보명 행: 라벨과 입력칸을 가로로 배치 (비울 수 없어 신규/빈 이름은 기본명으로 시작)
            initial_name: str = (
                data.name if (data is not None and data.name.strip()) else default_name
            )
            self._last_valid_name: str = initial_name
            name_label: QLabel = QLabel("후보명", self)
            name_label.setFont(CustomFont(10))
            self.name_input: CustomLineEdit = CustomLineEdit(
                self,
                lambda: self._name_changed_function(self),
                initial_name,
                point_size=10,
            )
            self.name_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.name_input.setFixedHeight(30)
            self.name_input.editingFinished.connect(self._restore_name_if_empty)
            name_row: QHBoxLayout = QHBoxLayout()
            name_row.setContentsMargins(0, 0, 0, 0)
            name_row.setSpacing(6)
            name_row.addWidget(name_label, 0, Qt.AlignmentFlag.AlignVCenter)
            name_row.addWidget(self.name_input, 1)
            root_layout.addLayout(name_row)

            title_row: QHBoxLayout = QHBoxLayout()
            title_row.setContentsMargins(0, 0, 0, 0)
            title_label: QLabel = QLabel("스탯", self)
            title_label.setFont(CustomFont(11, bold=True))
            title_row.addWidget(title_label)
            title_row.addStretch(1)
            add_button: StyledButton = StyledButton(
                self, "스탯 추가", kind="add", point_size=9
            )
            add_button.setFixedHeight(28)
            add_button.clicked.connect(lambda _checked=False: self.add_stat_row())
            title_row.addWidget(add_button)
            root_layout.addLayout(title_row)

            # 스탯 행이 많아지면 스크롤되도록 스크롤 영역에 배치
            self.stats_container: QWidget = QWidget()
            self.stats_container.setObjectName("candidateStatScrollContent")
            self.stats_layout: QVBoxLayout = QVBoxLayout(self.stats_container)
            self.stats_layout.setContentsMargins(0, 0, 0, 0)
            self.stats_layout.setSpacing(6)
            self.stats_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.stats_scroll_area: QScrollArea = QScrollArea(self)
            self.stats_scroll_area.setObjectName("candidateStatScrollArea")
            self.stats_scroll_area.setWidgetResizable(True)
            self.stats_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            # 스크롤바가 생겨도 행 가로폭이 변하지 않도록 세로 스크롤바 영역 고정
            self.stats_scroll_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOn
            )
            self.stats_scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.stats_scroll_area.setWidget(self.stats_container)
            root_layout.addWidget(self.stats_scroll_area, 1)

            # 저장된 스탯 행 복원
            if data is not None:
                for candidate_stat in data.stats:
                    self.add_stat_row(candidate_stat, emit_change=False)

        def add_stat_row(
            self,
            data: OptimizationCandidateStat | None = None,
            emit_change: bool = True,
        ) -> None:
            """후보 스탯 행 추가"""

            # 새 스탯 행 생성
            row = CandidateGroupInputs.CandidateStatRow(
                self.stats_container,
                self._value_changed_function,
                self.remove_stat_row,
                data=data,
            )
            self.stat_rows.append(row)
            self.stats_layout.addWidget(row)
            if emit_change:
                self._value_changed_function()

        def remove_stat_row(
            self,
            target_row: "CandidateGroupInputs.CandidateStatRow",
        ) -> None:
            """후보 스탯 행 제거"""

            # 스탯 행 위젯 제거
            self.stats_layout.removeWidget(target_row)
            self.stat_rows.remove(target_row)
            target_row.deleteLater()
            self._value_changed_function()

        def _restore_name_if_empty(self) -> None:
            """후보명이 비면 직전 유효값으로 복원"""

            # 비어 있으면 이전 입력값 복원, 아니면 유효값 갱신
            current_name: str = self.name_input.text().strip()
            if not current_name:
                self.name_input.setText(self._last_valid_name)
                return

            self._last_valid_name = current_name

        def get_display_name(self) -> str:
            """후보 표시명 반환"""

            # 후보명은 비울 수 없으므로 빈 입력은 직전 유효값으로 대체
            return self.name_input.text().strip() or self._last_valid_name

        def to_candidate_option(self) -> OptimizationCandidateOption:
            """후보 카드 데이터 복원"""

            # 후보명과 스탯 행 모델 구성 (이름·값 모두 항상 유효하게 보정됨)
            stats: list[OptimizationCandidateStat] = [
                stat_row.get_value() for stat_row in self.stat_rows
            ]
            return OptimizationCandidateOption(
                name=self.name_input.text().strip() or self._last_valid_name,
                stats=stats,
            )

    def __init__(self, parent: QWidget, connected_function: Callable[[], None]) -> None:
        super().__init__(parent)
        self.setMinimumHeight(360)

        # 후보 그룹 전체 상태 초기화
        self._connected_function: Callable[[], None] = connected_function
        self._groups: list[CandidateGroupInputs.CandidateGroupState] = []
        self._selected_group: CandidateGroupInputs.CandidateGroupState | None = None

        # 3분할 패널 구성
        root_layout: QHBoxLayout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        self.group_panel: QFrame = QFrame(self)
        self.group_panel.setObjectName("candidateGroupPanel")
        self.group_panel.setMinimumWidth(250)
        group_layout: QVBoxLayout = QVBoxLayout(self.group_panel)
        group_layout.setContentsMargins(14, 14, 14, 14)
        group_layout.setSpacing(10)
        group_title: QLabel = QLabel("후보 그룹", self.group_panel)
        group_title.setFont(CustomFont(11, bold=True))
        group_layout.addWidget(group_title)
        self.group_scroll_area: QScrollArea = QScrollArea(self.group_panel)
        self.group_scroll_area.setObjectName("candidateGroupScrollArea")
        self.group_scroll_area.setWidgetResizable(True)
        self.group_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.group_scroll_area.setMinimumHeight(220)
        # 스크롤바가 생겨도 항목 가로폭이 변하지 않도록 세로 스크롤바 영역 고정
        self.group_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.group_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.group_scroll_content: QWidget = QWidget(self.group_scroll_area)
        self.group_scroll_content.setObjectName("candidateGroupScrollContent")
        self.group_list_layout: QVBoxLayout = QVBoxLayout(self.group_scroll_content)
        self.group_list_layout.setContentsMargins(0, 0, 0, 0)
        self.group_list_layout.setSpacing(8)
        self.group_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.group_scroll_content.setLayout(self.group_list_layout)
        self.group_scroll_area.setWidget(self.group_scroll_content)
        group_layout.addWidget(self.group_scroll_area, 1)
        self.add_group_button: StyledButton = StyledButton(
            self.group_panel, "그룹 추가", kind="add"
        )
        self.add_group_button.clicked.connect(lambda _checked=False: self.add_group())
        group_layout.addWidget(self.add_group_button)

        self.list_panel: QFrame = QFrame(self)
        self.list_panel.setObjectName("candidateListPanel")
        self.list_panel.setMinimumWidth(220)
        list_layout: QVBoxLayout = QVBoxLayout(self.list_panel)
        list_layout.setContentsMargins(14, 14, 14, 14)
        list_layout.setSpacing(10)
        list_title: QLabel = QLabel("후보 목록", self.list_panel)
        list_title.setFont(CustomFont(11, bold=True))
        list_layout.addWidget(list_title)
        self.list_scroll_area: QScrollArea = QScrollArea(self.list_panel)
        self.list_scroll_area.setObjectName("candidateListScrollArea")
        self.list_scroll_area.setWidgetResizable(True)
        self.list_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.list_scroll_area.setMinimumHeight(220)
        # 스크롤바가 생겨도 항목 가로폭이 변하지 않도록 세로 스크롤바 영역 고정
        self.list_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.list_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.list_scroll_content: QWidget = QWidget(self.list_scroll_area)
        self.list_scroll_content.setObjectName("candidateListScrollContent")
        self.candidate_list_layout: QVBoxLayout = QVBoxLayout(self.list_scroll_content)
        self.candidate_list_layout.setContentsMargins(0, 0, 0, 0)
        self.candidate_list_layout.setSpacing(8)
        self.candidate_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_scroll_content.setLayout(self.candidate_list_layout)
        self.list_scroll_area.setWidget(self.list_scroll_content)
        list_layout.addWidget(self.list_scroll_area, 1)
        self.add_candidate_button: StyledButton = StyledButton(
            self.list_panel, "후보 추가", kind="add"
        )
        self.add_candidate_button.clicked.connect(
            lambda _checked=False: self.add_candidate()
        )
        list_layout.addWidget(self.add_candidate_button)

        self.detail_panel: QFrame = QFrame(self)
        self.detail_panel.setObjectName("candidateDetailPanel")
        self.detail_panel.setMinimumWidth(340)
        detail_layout: QVBoxLayout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(14, 14, 14, 14)
        detail_layout.setSpacing(10)
        detail_title: QLabel = QLabel("선택된 후보 설정", self.detail_panel)
        detail_title.setFont(CustomFont(11, bold=True))
        detail_layout.addWidget(detail_title)
        self.detail_stack_host: QWidget = QWidget(self.detail_panel)
        self.detail_stack: QStackedLayout = QStackedLayout(self.detail_stack_host)
        self.detail_stack_host.setLayout(self.detail_stack)
        self.empty_group_label: QLabel = QLabel(
            "왼쪽에서 후보 그룹을 선택하세요.", self.detail_stack_host
        )
        self.empty_group_label.setObjectName("panelEmptyLabel")
        self.empty_group_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_group_label.setFont(CustomFont(11))
        self.detail_stack.addWidget(self.empty_group_label)
        self.empty_candidate_label: QLabel = QLabel(
            "중앙 목록에서 후보를 선택하세요.", self.detail_stack_host
        )
        self.empty_candidate_label.setObjectName("panelEmptyLabel")
        self.empty_candidate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_candidate_label.setFont(CustomFont(11))
        self.detail_stack.addWidget(self.empty_candidate_label)
        detail_layout.addWidget(self.detail_stack_host)

        root_layout.addWidget(self.group_panel, 3)
        root_layout.addWidget(self.list_panel, 3)
        root_layout.addWidget(self.detail_panel, 4)
        self.setLayout(root_layout)
        self.refresh_options()

    @staticmethod
    def _next_available_numbered_name(prefix: str, existing_names: set[str]) -> str:
        """번호형 기본명 중 사용 가능한 가장 낮은 이름 생성"""

        # 현재 기본명 규칙과 일치하는 양수 번호 수집
        used_numbers: set[int] = set()
        marker: str = f"{prefix} "
        for existing_name in existing_names:
            if not existing_name.startswith(marker):
                continue

            suffix: str = existing_name.removeprefix(marker)
            if suffix.isdecimal() and int(suffix) >= 1:
                used_numbers.add(int(suffix))

        # 1부터 시작해 비어 있는 첫 번호 선택
        number: int = 1
        while number in used_numbers:
            number += 1

        return f"{prefix} {number}"

    def _on_value_changed(self) -> None:
        """값 입력 변경 처리"""

        # 목록 구조에 영향 없는 변경은 저장만 수행
        self._connected_function()

    def _on_candidate_name_changed(self, card: CandidateCard) -> None:
        """후보명 변경 처리"""

        # 해당 후보 목록 항목 표시명만 갱신 후 저장
        group_state = self._group_by_candidate(card)
        if group_state is self._selected_group:
            list_item = group_state.candidate_items.get(card)
            if list_item is not None:
                list_item.set_title_text(card.get_display_name())
        self._connected_function()

    def _on_group_name_changed(self, item: GroupListItem) -> None:
        """그룹명 변경 처리"""

        # 그룹명은 카드 내에서 직접 표시되므로 저장만 수행
        self._connected_function()

    def _on_group_selection_changed(self, item: GroupListItem) -> None:
        """선택 개수 변경 처리"""

        # 비정상 입력은 포커스 아웃 시 보정되므로 저장만 수행
        self._connected_function()

    def _state_by_item(self, target_item: GroupListItem) -> CandidateGroupState:
        """그룹 항목 기준 상태 조회"""

        # 등록된 그룹 항목 조회
        for group_state in self._groups:
            if group_state.item is target_item:
                return group_state

        raise ValueError("candidate group item is not registered")

    def select_group(self, target_item: GroupListItem) -> None:
        """후보 그룹 선택"""

        # 선택 그룹 전환
        self._selected_group = self._state_by_item(target_item)
        self.refresh_options()

    def add_group(
        self,
        data: OptimizationCandidateGroup | None = None,
        emit_change: bool = True,
    ) -> None:
        """후보 그룹 추가"""

        # 그룹 항목과 상태 등록 (신규 그룹은 빈 그룹명 방지를 위해 기본명 부여)
        existing_names: set[str] = {
            group_state.item.build_group_header()[0] for group_state in self._groups
        }
        default_name: str = self._next_available_numbered_name(
            "후보 그룹", existing_names
        )
        item = CandidateGroupInputs.GroupListItem(
            self.group_scroll_content,
            self.select_group,
            self.remove_group,
            self._on_group_name_changed,
            self._on_group_selection_changed,
            default_name,
            data=data,
        )
        group_state = CandidateGroupInputs.CandidateGroupState(
            item=item,
            candidates=[],
            candidate_items={},
            selected_candidate=None,
        )
        self._groups.append(group_state)
        self.group_list_layout.addWidget(item)
        if data is not None:
            for candidate in data.candidates:
                self.add_candidate(candidate, group_state, emit_change=False)

        self._selected_group = group_state
        self.refresh_options()
        if emit_change:
            self._connected_function()

    def remove_group(
        self,
        target_item: GroupListItem,
        emit_change: bool = True,
    ) -> None:
        """후보 그룹 제거"""

        # 그룹과 하위 후보 제거
        group_state = self._state_by_item(target_item)
        target_index: int = self._groups.index(group_state)
        next_group: CandidateGroupInputs.CandidateGroupState | None = None
        if len(self._groups) > 1:
            next_group = self._groups[min(target_index, len(self._groups) - 2)]
        for candidate_card in group_state.candidates.copy():
            self.remove_candidate(candidate_card, group_state, emit_change=False)
        self.group_list_layout.removeWidget(group_state.item)
        group_state.item.deleteLater()
        self._groups.remove(group_state)
        if self._selected_group is group_state:
            self._selected_group = next_group
        self.refresh_options()
        if emit_change:
            self._connected_function()

    def _group_by_candidate(self, target_card: CandidateCard) -> CandidateGroupState:
        """후보 카드 기준 그룹 조회"""

        # 후보가 속한 그룹 조회
        for group_state in self._groups:
            if target_card in group_state.candidates:
                return group_state

        raise ValueError("candidate card is not registered")

    def select_candidate(self, target_card: CandidateCard) -> None:
        """후보 선택"""

        # 선택 후보 전환
        group_state = self._group_by_candidate(target_card)
        self._selected_group = group_state
        group_state.selected_candidate = target_card
        self.refresh_options()

    def add_candidate(
        self,
        data: OptimizationCandidateOption | None = None,
        group_state: CandidateGroupState | None = None,
        emit_change: bool = True,
    ) -> None:
        """후보 추가"""

        # 선택 그룹에 후보 생성
        target_group: CandidateGroupInputs.CandidateGroupState | None = (
            group_state if group_state is not None else self._selected_group
        )
        if target_group is None:
            return

        # 선택 그룹 내 기존 후보명과 겹치지 않는 기본명 부여
        existing_names: set[str] = {
            candidate_card.get_display_name()
            for candidate_card in target_group.candidates
        }
        default_name: str = self._next_available_numbered_name("후보", existing_names)
        card = CandidateGroupInputs.CandidateCard(
            self.detail_stack_host,
            self._on_value_changed,
            self._on_candidate_name_changed,
            default_name,
            data=data,
        )
        list_item = CandidateGroupInputs.CandidateListItem(
            self.list_scroll_content,
            self.select_candidate,
            self.remove_candidate,
            card,
        )
        target_group.candidates.append(card)
        target_group.candidate_items[card] = list_item
        self.detail_stack.addWidget(card)
        target_group.selected_candidate = card
        self.refresh_options()
        if emit_change:
            self._connected_function()

    def remove_candidate(
        self,
        target_card: CandidateCard,
        group_state: CandidateGroupState | None = None,
        emit_change: bool = True,
    ) -> None:
        """후보 제거"""

        # 후보 목록 항목과 상세 카드 제거
        target_group: CandidateGroupInputs.CandidateGroupState = (
            group_state
            if group_state is not None
            else self._group_by_candidate(target_card)
        )
        target_index: int = target_group.candidates.index(target_card)
        next_candidate: CandidateGroupInputs.CandidateCard | None = None
        if len(target_group.candidates) > 1:
            next_candidate = target_group.candidates[
                min(target_index, len(target_group.candidates) - 2)
            ]
        list_item: CandidateGroupInputs.CandidateListItem = (
            target_group.candidate_items.pop(target_card)
        )
        self.candidate_list_layout.removeWidget(list_item)
        list_item.deleteLater()
        self.detail_stack.removeWidget(target_card)
        target_group.candidates.remove(target_card)
        target_card.deleteLater()
        if target_group.selected_candidate is target_card:
            target_group.selected_candidate = next_candidate
        self.refresh_options()
        if emit_change:
            self._connected_function()

    def refresh_options(self) -> None:
        """후보 그룹과 후보 목록 표시 동기화"""

        # 선택 참조 유효성 정리
        if self._selected_group not in self._groups:
            self._selected_group = self._groups[0] if self._groups else None
        for group_state in self._groups:
            group_state.item.set_selected_state(group_state is self._selected_group)
            group_state.item.set_candidate_count(len(group_state.candidates))

        # 중앙 후보 목록 갱신
        while self.candidate_list_layout.count() > 0:
            item: QLayoutItem = self.candidate_list_layout.takeAt(0)
            widget: QWidget | None = item.widget()
            if widget is not None:
                widget.hide()
        if self._selected_group is not None:
            if (
                self._selected_group.selected_candidate
                not in self._selected_group.candidates
            ):
                self._selected_group.selected_candidate = (
                    self._selected_group.candidates[0]
                    if self._selected_group.candidates
                    else None
                )
            for candidate_card in self._selected_group.candidates:
                list_item = self._selected_group.candidate_items[candidate_card]
                list_item.set_title_text(candidate_card.get_display_name())
                list_item.set_selected_state(
                    candidate_card is self._selected_group.selected_candidate
                )
                self.candidate_list_layout.addWidget(list_item)
                list_item.show()
        self.add_candidate_button.setEnabled(self._selected_group is not None)

        # 상세 패널 표시 전환
        if self._selected_group is None:
            self.detail_stack.setCurrentWidget(self.empty_group_label)
            return
        if self._selected_group.selected_candidate is None:
            self.detail_stack.setCurrentWidget(self.empty_candidate_label)
            return
        self.detail_stack.setCurrentWidget(self._selected_group.selected_candidate)

    def load(self, candidate_groups: list[OptimizationCandidateGroup]) -> None:
        """저장된 후보 그룹 입력 상태 로드"""

        # 기존 그룹 제거 후 저장 상태 복원
        for group_state in self._groups.copy():
            self.remove_group(group_state.item, emit_change=False)
        for candidate_group in candidate_groups:
            self.add_group(candidate_group, emit_change=False)
        self._selected_group = self._groups[0] if self._groups else None
        self.refresh_options()

    def build_state(self) -> list[OptimizationCandidateGroup]:
        """현재 후보 그룹 입력 상태 복원"""

        # 입력값이 항상 유효하게 보정되므로 그대로 직렬화
        candidate_groups: list[OptimizationCandidateGroup] = []
        for group_state in self._groups:
            group_name: str
            selection_count: int
            group_name, selection_count = group_state.item.build_group_header()
            candidates: list[OptimizationCandidateOption] = [
                candidate_card.to_candidate_option()
                for candidate_card in group_state.candidates
            ]
            candidate_groups.append(
                OptimizationCandidateGroup(
                    name=group_name,
                    selection_count=selection_count,
                    candidates=candidates,
                )
            )
        return candidate_groups
