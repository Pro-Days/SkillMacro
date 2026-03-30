from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from html import escape
from typing import TYPE_CHECKING, Literal
from webbrowser import open_new

from pynput import keyboard as pynput_keyboard
from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QObject,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QCursor, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.calculator_models import StatKey, get_stat_label
from app.scripts.config import config
from app.scripts.custom_classes import CustomFont, CustomLineEdit, CustomShadowEffect
from app.scripts.custom_skill_models import (
    BuffEffectPayload,
    CustomScrollDefinition,
    CustomSkillDefinition,
    CustomSkillImport,
    CustomSkillImportError,
    DamageEffectPayload,
    HealEffectPayload,
    SkillEffectType,
)
from app.scripts.data_manager import read_custom_skills_data, save_custom_skills
from app.scripts.macro_models import SkillUsageSetting
from app.scripts.registry.key_registry import KeyRegistry
from app.scripts.registry.resource_registry import (
    convert_resource_path,
    get_theme_image_path,
    resource_registry,
)
from app.scripts.registry.server_registry import ServerSpec, server_registry
from app.scripts.registry.skill_registry import (
    CUSTOM_SKILL_PREFIX,
    BuffEffect,
    DamageEffect,
    HealEffect,
    LevelEffect,
    ScrollDef,
    SkillDef,
)
from app.scripts.ui.themes import theme_manager

if TYPE_CHECKING:
    from app.scripts.registry.key_registry import KeySpec
    from app.scripts.ui.main_window import MainWindow


class PopupPlacement(Enum):
    """Anchor 기준 팝업을 배치하는 방향"""

    ABOVE = auto()
    RIGHT = auto()
    BELOW = auto()
    LEFT = auto()


class PopupKind(str, Enum):
    """PopupHost 기반 팝업의 종류"""

    SERVER = "settingServer"
    DELAY = "settingDelay"
    COOLTIME = "settingCooltime"
    START_KEY = "settingStartKey"
    TAB_NAME = "tabName"
    SKILL_KEY = "skillKey"
    SCROLL_SELECT = "scrollSelect"
    LINK_SKILL_KEY = "linkSkillKey"
    LINK_SKILL_SELECT = "linkSkillSelect"


class NoticeKind(Enum):
    """알림 팝업의 종류"""

    # 동작 관련
    MACRO_IS_RUNNING = auto()  # 매크로 작동중
    EDITING_LINK_SKILL = auto()  # 연계스킬 수정중

    # 스킬 관련
    SKILL_NOT_SELECTED = auto()  # 스킬 미선택
    AUTO_ALREADY_EXIST = auto()  # 이미 자동 사용중
    EXCEED_MAX_LINK_SKILL = auto()  # 연계 스킬 개수 초과

    # 입력 검증
    DELAY_INPUT_ERROR = auto()  # 딜레이 입력 오류
    COOLTIME_INPUT_ERROR = auto()  # 쿨타임 입력 오류
    START_KEY_CHANGE_ERROR = auto()  # 매크로 시작키 변경 오류
    SWAP_KEY_CHANGE_ERROR = auto()  # 스왑키 변경 오류

    # 업데이트/설정
    REQUIRE_UPDATE = auto()  # 업데이트 필요
    FAILED_UPDATE_CHECK = auto()  # 업데이트 확인 실패
    DATA_FILE_BACKED_UP = auto()  # 데이터 파일 백업 완료
    CUSTOM_SKILLS_NORMALIZED = auto()  # 커스텀 무공비급 중복 정리 완료

    # 시뮬레이션
    SIM_INPUT_ERROR = auto()  # 시뮬레이션 정보 입력 오류
    SIM_CHAR_LOAD_ERROR = auto()  # 캐릭터 로드 실패
    SIM_CARD_ERROR = auto()  # 카드 생성 오류
    SIM_CARD_POWER_ERROR = auto()  # 전투력 미선택
    SIM_CARD_NOT_UPDATED = auto()  # 입력 완료 필요


@dataclass
class NoticeData:
    text: str
    icon: str = "error"
    extra_action: tuple[str, Callable] | None = None
    height: int = 70


@dataclass(frozen=True)
class PopupOptions:
    """팝업의 표시 옵션"""

    placement: PopupPlacement = PopupPlacement.BELOW
    margin: int = 3
    x_offset: int = 0


@dataclass(frozen=True)
class HoverCardLine:
    """호버 카드 본문 한 줄 데이터"""

    text: str
    color: str = "#D9D5E3"
    point_size: int = 10


@dataclass(frozen=True)
class HoverCardData:
    """호버 카드 전체 데이터"""

    title: str
    lines: tuple[HoverCardLine, ...]


HoverCardSupplier = Callable[[], HoverCardData | None]


@dataclass(frozen=True)
class PopupAction:
    """
    팝업 내의 선택지 하나
    예: 서버 -> "한월 RPG" 선택지
    """

    id: str
    text: str
    enabled: bool = True
    is_selected: bool = False
    on_trigger: Callable[[], None] | None = None


@dataclass(frozen=True)
class SkillLevelInputRow:
    """레벨별 효과 입력 행 위젯 묶음"""

    type_combo: QComboBox
    amount_input: CustomLineEdit
    stat_combo: QComboBox
    duration_input: CustomLineEdit


class PopupContent(QFrame):
    """팝업 내용의 기본 클래스"""

    def __init__(self, fixed_width: int) -> None:
        super().__init__()

        self.setFixedWidth(fixed_width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


class HoverCardContent(QFrame):
    """호버 카드 내용"""

    def __init__(self) -> None:
        super().__init__()

        # 호버 카드 기본 레이아웃 구성
        self._layout: QVBoxLayout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(2)

        # 제목 라벨 고정 배치
        self._title_label: QLabel = QLabel("", self)
        self._title_label.setObjectName("hoverCardTitle")
        self._title_label.setFont(CustomFont(11))
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layout.addWidget(self._title_label)

        # 본문 라벨 고정 배치
        self._body_label: QLabel = QLabel("", self)
        self._body_label.setObjectName("hoverCardBody")
        self._body_label.setFont(CustomFont(10))
        self._body_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._body_label.setTextFormat(Qt.TextFormat.RichText)
        self._body_label.setWordWrap(True)
        self._layout.addWidget(self._body_label)

    def set_data(self, data: HoverCardData) -> None:
        """호버 카드 데이터 반영"""

        # 제목 텍스트 즉시 갱신
        self._title_label.setText(data.title)

        # 색상별 줄바꿈 표현을 유지하기 위해 HTML 본문 조합
        body_lines: list[str] = []
        for line in data.lines:
            body_lines.append(
                (
                    f'<span style="color:{line.color}; font-size:{line.point_size}pt;">'
                    f"{escape(line.text)}"
                    "</span>"
                )
            )

        body_html: str = "<br/>".join(body_lines)
        self._body_label.setText(body_html)
        self._body_label.setVisible(bool(body_lines))

        # 텍스트 반영 직후 레이아웃 재계산 강제
        self._layout.activate()
        self.updateGeometry()
        self.adjustSize()


class HoverCardHost(QFrame):
    """호버 카드 호스트"""

    _CURSOR_OFFSET: QPoint = QPoint(18, 18)
    _VIEWPORT_PADDING: int = 8

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.master: QWidget = parent

        # 마우스 입력을 가로채지 않는 투명 오버레이 구성
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

        # 그림자 여백을 포함한 외부 레이아웃 구성
        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        # 실제 카드 외형 컨테이너 구성
        self._container: QFrame = QFrame(self)
        self._container.setObjectName("hoverCardContainer")
        self._container.setGraphicsEffect(CustomShadowEffect(0, 4, 18, 160))
        root.addWidget(self._container)

        # 카드 내용 위젯 결합
        container_layout: QVBoxLayout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        self._content: HoverCardContent = HoverCardContent()
        container_layout.addWidget(self._content)

        # 전역 입력 감지용 이벤트 필터 설치
        app: QCoreApplication | None = QGuiApplication.instance()

        if app is not None:
            app.installEventFilter(self)

    def show_at_cursor(self, data: HoverCardData, global_pos: QPoint) -> None:
        """지정된 마우스 위치 근처에 호버 카드 표시"""

        # 최신 카드 내용 반영 및 크기 계산
        self._content.set_data(data)
        self._content.updateGeometry()
        self._content.adjustSize()
        self._container.layout().activate()  # type: ignore
        self._container.adjustSize()
        self.layout().activate()  # type: ignore
        self.updateGeometry()
        self.adjustSize()

        # 전역 좌표를 부모 기준 좌표로 변환
        cursor_pos: QPoint = self.master.mapFromGlobal(global_pos)
        target_pos: QPoint = cursor_pos + self._CURSOR_OFFSET
        viewport: QRect = self.master.rect().adjusted(
            self._VIEWPORT_PADDING,
            self._VIEWPORT_PADDING,
            -self._VIEWPORT_PADDING,
            -self._VIEWPORT_PADDING,
        )

        # 카드가 화면 밖으로 나가지 않도록 위치 보정
        max_x: int = max(viewport.left(), viewport.right() - self.width())
        max_y: int = max(viewport.top(), viewport.bottom() - self.height())
        x: int = min(max(target_pos.x(), viewport.left()), max_x)
        y: int = min(max(target_pos.y(), viewport.top()), max_y)

        self.move(x, y)
        self.raise_()
        self.show()

    def hide_card(self) -> None:
        """호버 카드 숨김"""

        self.hide()

    def eventFilter(self, watched, event) -> bool:  # type: ignore
        """전역 입력 발생 시 호버 카드 자동 숨김"""

        if event is None:
            return super().eventFilter(watched, event)

        if not self.isVisible():
            return super().eventFilter(watched, event)

        # 클릭, 휠, 비활성화 시 카드 숨김
        if event.type() in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.Wheel,
            QEvent.Type.WindowDeactivate,
        }:
            self.hide_card()

        return super().eventFilter(watched, event)


class HoverCardTrigger(QObject):
    """특정 위젯에 호버 카드 동작을 연결하는 이벤트 필터"""

    def __init__(
        self,
        widget: QWidget,
        popup_manager: PopupManager,
        supplier: HoverCardSupplier,
    ) -> None:
        super().__init__(widget)

        self._widget: QWidget = widget
        self._popup_manager: PopupManager = popup_manager
        self._supplier: HoverCardSupplier = supplier

        # 마우스 이동 추적 활성화 및 이벤트 필터 설치
        self._widget.setMouseTracking(True)
        self._widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # type: ignore
        """호버 진입/이동/이탈에 맞춰 카드 표시 제어"""

        if event is None or watched is not self._widget:
            return super().eventFilter(watched, event)

        # 진입 및 이동 시 최신 데이터로 카드 갱신
        if event.type() in {
            QEvent.Type.Enter,
            QEvent.Type.MouseMove,
            QEvent.Type.HoverMove,
        }:
            data: HoverCardData | None = self._supplier()

            if data is None:
                self._popup_manager.hide_hover_card()
                return super().eventFilter(watched, event)

            self._popup_manager.show_hover_card(data, QCursor.pos())

            return super().eventFilter(watched, event)

        # 이탈 및 숨김 시 카드 제거
        if event.type() in {
            QEvent.Type.Leave,
            QEvent.Type.HoverLeave,
            QEvent.Type.Hide,
            QEvent.Type.Close,
        }:
            self._popup_manager.hide_hover_card()

        return super().eventFilter(watched, event)


class NoticeContent(PopupContent):

    closed = Signal()
    _CONTENT_WIDTH: int = 350
    _CARD_MARGIN: int = 10
    _ITEM_SPACING: int = 10
    _ACCENT_WIDTH: int = 6
    _ICON_SIZE: int = 24
    _REMOVE_BUTTON_SIZE: int = 24

    def __init__(self, data: NoticeData) -> None:
        super().__init__(self._CONTENT_WIDTH)

        # 알림 카드 외곽선을 호스트 컨테이너에서 표현하도록 내부 배경 투명화

        # 카드 내부 여백과 요소 간 간격 구성
        layout: QHBoxLayout = QHBoxLayout()
        layout.setContentsMargins(
            self._CARD_MARGIN,
            self._CARD_MARGIN,
            self._CARD_MARGIN,
            self._CARD_MARGIN,
        )
        layout.setSpacing(self._ITEM_SPACING)
        self.setLayout(layout)

        # 배경과 구분되는 좌측 강조 바 구성
        accent_bar: QFrame = QFrame()
        accent_bar.setObjectName("noticeAccentBar")
        accent_bar.setProperty("kind", data.icon)
        accent_bar.setFixedWidth(self._ACCENT_WIDTH)
        accent_bar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        layout.addWidget(accent_bar)

        # 알림 아이콘 영역 구성
        icon: QLabel = QLabel()
        icon.setFixedSize(self._ICON_SIZE, self._ICON_SIZE)
        pixmap: QPixmap = QPixmap(
            convert_resource_path(f"resources\\image\\{data.icon}.png")
        )
        icon.setPixmap(pixmap)
        icon.setScaledContents(True)
        icon_layout: QVBoxLayout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(icon_layout)

        # 알림 본문을 카드 배경과 자연스럽게 이어지도록 투명 라벨 구성
        label: QLabel = QLabel(data.text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setFont(CustomFont(12))
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # 본문과 추가 액션을 세로로 배치
        content_layout: QVBoxLayout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(label)
        content_layout.setSpacing(self._ITEM_SPACING)
        layout.addLayout(content_layout)

        # 줄바꿈 본문 높이를 폭 기준으로 선계산하여 하단 잘림 방지
        label_width: int = (
            self._CONTENT_WIDTH
            - (self._CARD_MARGIN * 2)
            - self._ACCENT_WIDTH
            - self._ICON_SIZE
            - self._REMOVE_BUTTON_SIZE
            - (self._ITEM_SPACING * 3)
        )
        label.setFixedWidth(label_width)
        label.setMinimumHeight(label.heightForWidth(label_width))

        if data.extra_action:
            # 사용자가 즉시 반응할 수 있도록 액션 버튼 구성
            action_text: str
            action_callback: Callable
            action_text, action_callback = data.extra_action

            action_button: QPushButton = QPushButton(action_text)
            action_button.setObjectName("noticeActionButton")
            action_button.setFont(CustomFont(12))
            action_button.setFixedSize(120, 32)
            action_button.clicked.connect(action_callback)
            action_button.setCursor(Qt.CursorShape.PointingHandCursor)
            content_layout.addWidget(action_button)

        # 닫기 버튼을 카드 배경 위에 자연스럽게 배치
        remove_btn: QPushButton = QPushButton()
        remove_btn.setObjectName("noticeRemoveBtn")
        remove_btn.setFixedSize(self._REMOVE_BUTTON_SIZE, self._REMOVE_BUTTON_SIZE)
        remove_btn.clicked.connect(self.closed.emit)
        # 현재 테마 기준 닫기 아이콘 경로 선택
        pixmap: QPixmap = QPixmap(get_theme_image_path("x.png", theme_manager.is_dark))
        remove_btn.setIcon(QIcon(pixmap))
        remove_btn.setIconSize(QSize(20, 20))
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # 닫기 버튼을 우상단에 고정
        remove_layout: QVBoxLayout = QVBoxLayout()
        remove_layout.setContentsMargins(0, 0, 0, 0)
        remove_layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(remove_layout)


class ActionListContent(PopupContent):
    """
    서버/직업 같은 목록 선택용 content
    PopupAction 리스트를 받아 버튼 목록을 생성
    """

    triggered = Signal(str)

    def __init__(
        self,
        actions: list[PopupAction],
    ) -> None:
        super().__init__(130)

        self.setObjectName("actionListContent")

        # 무공비급바 없이 전체 항목을 나열
        v = QVBoxLayout(self)
        v.setContentsMargins(5, 5, 5, 5)
        v.setSpacing(5)

        row_height = 30
        for act in actions:
            btn = QPushButton(act.text, self)
            btn.setFont(CustomFont(12))
            btn.setEnabled(act.enabled)

            # 폭은 컨테이너에 맞춰 자동으로 늘어나도록
            btn.setFixedHeight(row_height)
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            btn.setProperty("selected", act.is_selected)
            btn.clicked.connect(lambda _, act_id=act.id: self.triggered.emit(act_id))

            v.addWidget(btn)


class InputConfirmContent(PopupContent):
    """라인에딧 & 확인 버튼 형태의 팝업"""

    submitted = Signal(str)

    def __init__(
        self,
        default_text: str,
    ) -> None:
        super().__init__(170)
        # 라인에딧
        self._edit = CustomLineEdit(
            self, text=default_text, point_size=12, border_radius=10
        )
        self._edit.setFixedHeight(30)
        self._edit.returnPressed.connect(self._emit_submit)

        # 확인 버튼
        self._btn = QPushButton("확인", self)
        self._btn.setObjectName("popupConfirmBtn")
        self._btn.setFont(CustomFont(12))
        self._btn.setFixedSize(50, 30)
        self._btn.clicked.connect(self._emit_submit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addWidget(self._edit)
        layout.addWidget(self._btn)
        self.setLayout(layout)

    def _emit_submit(self) -> None:
        self.submitted.emit(self._edit.text())


class KeyCaptureContent(PopupContent):
    """QLabel & 확인 버튼 형태의 시작키 입력 팝업"""

    submitted = Signal(object)  # KeySpec | None
    _key_received = Signal(object)

    def __init__(self, default_key: KeySpec | None = None) -> None:
        super().__init__(200)

        self._current_key: KeySpec | None = default_key

        self._label = QLabel(self)
        self._label.setObjectName("keyCaptureLabel")
        self._label.setFont(CustomFont(12))
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFixedHeight(30)
        self._label.setText("키를 입력해주세요")

        self._btn = QPushButton("확인", self)
        self._btn.setObjectName("popupConfirmBtn")
        self._btn.setFont(CustomFont(12))
        self._btn.setFixedSize(50, 30)
        self._btn.clicked.connect(self._emit_submit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addWidget(self._label)
        layout.addWidget(self._btn)
        self.setLayout(layout)

        self._key_received.connect(self._apply_key)

    def set_key(self, key: KeySpec) -> None:
        """외부 리스너에서 호출 -> 현재 키를 업데이트"""

        self._key_received.emit(key)

    def _apply_key(self, key: KeySpec) -> None:
        self._current_key = key
        self._label.setText(key.display)

    def _emit_submit(self) -> None:
        self.submitted.emit(self._current_key)


class PopupHost(QWidget):
    """
    화면에 뜨는 팝업 창
    팝업 내용을 설정하고, 앵커 위젯 기준으로 위치를 계산하여 표시
    """

    closed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.master: QWidget = parent

        # 팝업 내용이 들어가는 컨테이너
        self._container = QFrame(self)
        self._container.setObjectName("popupContainer")

        # 그림자가 그려질 공간 확보
        shadow_offset_x = 0
        shadow_offset_y = 5
        shadow_blur = 25
        self._container.setGraphicsEffect(
            CustomShadowEffect(shadow_offset_x, shadow_offset_y, shadow_blur, 150)
        )

        # 컨테이너 레이아웃 적용
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)

        # 그림자가 잘리는 것을 방지하기 위한 외부 레이아웃
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 20)
        root.addWidget(self._container)

        # 팝업 내용 위젯
        self._content: QWidget | None = None

        # 무공비급 이벤트를 감지하기 위한 이벤트 필터 설치
        app: QCoreApplication | None = QGuiApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def set_content(self, content: QWidget) -> None:
        """팝업 내용 설정"""

        # 기존 내용 제거
        if self._content is not None:
            self._container_layout.removeWidget(self._content)
            self._content.setParent(None)

        self._content = content
        content.setParent(self._container)
        self._container_layout.addWidget(content)

    def show_for(self) -> None:
        """팝업 표시 (기존 위치 유지)"""
        if self._content is None:
            raise RuntimeError("PopupHost.show_for() called without content")

        # 크기 조정
        self._container.adjustSize()
        self.adjustSize()

        # 팝업 표시
        self.raise_()
        self.show()

    def show_at_anchor(self, anchor: QWidget, options: PopupOptions) -> None:
        """팝업 표시"""

        self.show_for()

        # 앵커 위치 계산
        anchor_top_left: QPoint = anchor.mapTo(self.master, QPoint(0, 0))
        anchor_rect = QRect(anchor_top_left, anchor.size())

        # 팝업 크기 계산
        popup_size: QSize = self.sizeHint()
        w: int = popup_size.width()
        h: int = popup_size.height()

        # 위치 계산
        if options.placement == PopupPlacement.BELOW:
            x: int = anchor_rect.left() + (anchor_rect.width() - w) // 2
            y: int = anchor_rect.bottom() + options.margin
        elif options.placement == PopupPlacement.LEFT:
            x = anchor_rect.left() - w - options.margin
            y = anchor_rect.top() + (anchor_rect.height() - h) // 2
        elif options.placement == PopupPlacement.ABOVE:
            x = anchor_rect.left() + (anchor_rect.width() - w) // 2
            y = anchor_rect.top() - h - options.margin
        else:  # PopupPlacement.RIGHT
            x = anchor_rect.right() + options.margin
            y = anchor_rect.top() + (anchor_rect.height() - h) // 2

        x += options.x_offset

        # 팝업 위치 설정 및 표시
        self.move(x, y)

    def eventFilter(self, obj, event: QEvent) -> bool:  # type: ignore
        """부모 위젯의 무공비급 이벤트를 감지"""

        # 무공비급 이벤트 감지 및 팝업 닫기
        if self.isVisible() and event.type() == QEvent.Type.Wheel:
            self.close()
            return False

        return super().eventFilter(obj, event)

    def focusOutEvent(self, event) -> None:
        """
        포커스를 잃었을 때 팝업 내부 클릭인지 확인 후 팝업 닫기
        """

        fw: QWidget | None = QApplication.focusWidget()

        if (
            self.isVisible()
            and fw is not None
            and fw is not self
            and not self.isAncestorOf(fw)
        ):
            self.close()

        super().focusOutEvent(event)

    def closeEvent(self, event) -> None:
        """팝업이 닫힐 때 호출"""
        self.closed.emit()
        super().closeEvent(event)


class PopupController:
    """
    팝업 호스트 관리 클래스
    (팝업 표시를 관리함)
    PopupHost를 재사용하며 content 교체로 팝업을 표시
    """

    def __init__(self, parent: QWidget) -> None:
        self._host = PopupHost(parent)

        # action list에서 사용하는 액션 매핑
        self._actions_by_id: dict[str, PopupAction] = {}

    @property
    def host(self) -> PopupHost:
        return self._host

    def is_visible(self) -> bool:
        return self._host.isVisible()

    def close(self) -> None:
        self._host.close()

    def show_action_list(
        self,
        anchor: QWidget,
        actions: list[PopupAction],
        options: PopupOptions,
    ) -> None:
        """ActionList 형태의 팝업 표시"""

        self._actions_by_id = {a.id: a for a in actions}

        content = ActionListContent(actions)
        content.triggered.connect(self._on_triggered)

        self._host.set_content(content)
        self._host.show_at_anchor(anchor, options)

    def show_content(
        self,
        anchor: QWidget,
        content: QWidget,
        options: PopupOptions,
    ) -> None:
        """ActionList가 아닌 content(입력 팝업 등)를 표시"""

        # 기존 액션 매핑 제거
        self._actions_by_id.clear()

        self._host.set_content(content)
        self._host.show_at_anchor(anchor, options)

    def _on_triggered(self, action_id: str) -> None:
        """액션 선택시 호출"""

        act: PopupAction = self._actions_by_id[action_id]
        self.close()

        if act.on_trigger is not None:
            act.on_trigger()


class NoticeHost(PopupHost):
    """알림 팝업 호스트 클래스"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        # 알림 카드를 메인 배경에서 띄워 보이게 하는 전용 외곽선과 그림자 구성
        self._container.setObjectName("noticeContainer")
        self._container.setGraphicsEffect(CustomShadowEffect(0, 10, 34, 185))

    def focusOutEvent(self, event) -> None:
        """포커스를 잃어도 닫히지 않도록"""
        pass

    def eventFilter(self, watched, event: QEvent) -> bool:  # type: ignore
        """부모 위젯의 무공비급 이벤트를 감지"""

        # 무공비급 이벤트 감지
        if event.type() == QEvent.Type.Wheel:
            return False

        return super().eventFilter(watched, event)


class NoticeController:
    """
    알림 호스트 관리 클래스
    (알림 표시를 관리함)
    NoticeHost를 재사용하며 content 교체로 팝업을 표시
    """

    def __init__(self, parent: QWidget) -> None:
        self.parent: QWidget = parent

        # 활성화된 알림 목록
        self._hosts: list[NoticeHost] = []

    def _get_notice_data(self, kind: NoticeKind) -> NoticeData:
        """알림 종류에 따른 데이터 반환"""

        match kind:

            # 정적 메시지
            case NoticeKind.MACRO_IS_RUNNING:
                return NoticeData("매크로가 작동중이기 때문에 수정할 수 없습니다.")

            case NoticeKind.EDITING_LINK_SKILL:
                return NoticeData(
                    "연계스킬을 수정중이기 때문에 장착스킬을 변경할 수 없습니다."
                )

            case NoticeKind.SKILL_NOT_SELECTED:
                return NoticeData(
                    "해당 연계스킬에 장착중이지 않은 스킬이 포함되어있습니다."
                )

            case NoticeKind.AUTO_ALREADY_EXIST:
                return NoticeData(
                    "해당 연계스킬에 이미 자동으로 사용중인 스킬이 포함되어있습니다."
                )

            case NoticeKind.EXCEED_MAX_LINK_SKILL:
                return NoticeData(
                    "해당 스킬이 너무 많이 사용되어 연계가 정상적으로 작동하지 않을 수 있습니다."
                )

            case NoticeKind.START_KEY_CHANGE_ERROR:
                return NoticeData("해당 키는 이미 사용중입니다.")

            case NoticeKind.SWAP_KEY_CHANGE_ERROR:
                return NoticeData("해당 키는 이미 사용중입니다.")

            case NoticeKind.FAILED_UPDATE_CHECK:
                return NoticeData("프로그램 업데이트 확인에 실패하였습니다.", "warning")

            case NoticeKind.DATA_FILE_BACKED_UP:
                return NoticeData(
                    "데이터 파일 오류가 발생하여 백업 파일을 생성했습니다.",
                    "warning",
                )

            case NoticeKind.CUSTOM_SKILLS_NORMALIZED:
                return NoticeData(
                    "중복된 커스텀 무공비급이 발견되어 자동 정리했습니다.",
                    "warning",
                )

            case NoticeKind.SIM_INPUT_ERROR:
                return NoticeData("시뮬레이션 정보가 올바르게 입력되지 않았습니다.")

            case NoticeKind.SIM_CHAR_LOAD_ERROR:
                return NoticeData("캐릭터를 불러올 수 없습니다. 닉네임을 확인해주세요.")

            case NoticeKind.SIM_CARD_ERROR:
                return NoticeData(
                    "카드를 생성할 수 없습니다. 닉네임과 캐릭터를 확인해주세요."
                )

            case NoticeKind.SIM_CARD_POWER_ERROR:
                return NoticeData("표시할 전투력 종류를 선택해주세요.")

            case NoticeKind.SIM_CARD_NOT_UPDATED:
                return NoticeData(
                    "캐릭터 정보를 입력하고 '입력완료' 버튼을 눌러주세요."
                )

            # 동적 메시지
            case NoticeKind.DELAY_INPUT_ERROR:
                return NoticeData(
                    f"딜레이는 {config.specs.DELAY.min}~{config.specs.DELAY.max}까지의 수를 입력해야 합니다."
                )

            case NoticeKind.COOLTIME_INPUT_ERROR:
                return NoticeData(
                    f"{config.specs.COOLTIME_REDUCTION.label}은(는) {config.specs.COOLTIME_REDUCTION.min}~{config.specs.COOLTIME_REDUCTION.max}까지의 수를 입력해야 합니다."
                )

            case NoticeKind.REQUIRE_UPDATE:
                msg: str = (
                    f"버전 불일치: {config.version} -> {app_state.ui.current_version}"
                )

                action: tuple[Literal["다운로드"], Callable[[], bool]] = (
                    "다운로드",
                    lambda: open_new(app_state.ui.update_url),
                )

                return NoticeData(msg, "warning", action)

    def show(self, kind: NoticeKind) -> None:
        """알림 팝업 표시"""

        # 알림 데이터 가져오기
        data: NoticeData = self._get_notice_data(kind)

        # 내용과 호스트 생성
        content = NoticeContent(data)
        host = NoticeHost(self.parent)
        host.set_content(content)

        # 닫기 시그널 연결
        content.closed.connect(lambda: self._close_notice(host))

        # 호스트 목록에 추가 및 표시
        self._hosts.append(host)
        host.show_for()

        # 위치 업데이트
        self.update_positions()

    def _close_notice(self, host: NoticeHost) -> None:
        """알림 팝업 닫기"""

        if host in self._hosts:
            self._hosts.remove(host)
            host.close()
            self.update_positions()

    def close_one_notice(self) -> None:
        """가장 최근에 표시된 알림 팝업 하나 닫기"""

        if self._hosts:
            host: NoticeHost = self._hosts.pop()
            host.close()
            self.update_positions()

    def update_positions(self) -> None:
        """알림 팝업 위치 업데이트"""

        bottom_margin = 15
        right_margin = 20
        spacing = 15

        current_y: int = self.parent.height() - bottom_margin

        # 역순으로 배치
        for host in reversed(self._hosts):
            w: int = host.width()

            # 부모 위젯 기준 좌표 계산
            x: int = self.parent.width() - w - right_margin
            host.move(x, current_y - host.height())

            current_y -= spacing


class PopupManager:
    """
    팝업을 관리하는 클래스
    (어떤 팝업을 표시할지 결정하고, 팝업 표시 요청을 처리함)
    """

    def __init__(self, master: MainWindow) -> None:
        self.master: MainWindow = master

        # 팝업 컨트롤러
        self._popup_controller: PopupController = PopupController(master)
        self._popup_controller.host.closed.connect(self._on_popup_host_closed)
        self._active_popup: PopupKind | None = None

        # 마우스 호버 카드 호스트 및 바인딩 목록 초기화
        self._hover_card_host: HoverCardHost = HoverCardHost(master)
        self._hover_bindings: list[HoverCardTrigger] = []

        # 알림 컨트롤러
        self._notice_controller: NoticeController = NoticeController(master)

        # 시작키 입력 리스너(pynput)
        self._key_listener: pynput_keyboard.Listener | None = None

    def is_popup_active(self, kind: PopupKind) -> bool:
        """특정 팝업이 활성화되어있는지 여부 반환"""
        return self._active_popup == kind

    def close_one_notice(self) -> None:
        """가장 최근에 표시된 알림 팝업 하나 닫기"""
        self._notice_controller.close_one_notice()

    def update_notice_positions(self) -> None:
        """알림 팝업 위치 업데이트"""
        self._notice_controller.update_positions()

    def _on_popup_host_closed(self) -> None:
        """팝업 호스트가 닫혔을 때 호출"""

        self._active_popup = None
        self.hide_hover_card()
        self._stop_key_listener()

    def _stop_key_listener(self) -> None:
        """키 입력 리스너 중지"""

        listener: pynput_keyboard.Listener | None = self._key_listener

        # 리스너를 None으로 설정
        self._key_listener = None

        # 키 입력 중 플래그 해제
        app_state.ui.is_setting_key = False

        # 리스너가 동작 중이면 중지
        if listener is not None:
            listener.stop()

    def show_notice(self, kind: NoticeKind) -> None:
        """알림 팝업 표시"""
        self._notice_controller.show(kind)

    def close_popup(self) -> None:
        """PopupHost 기반 팝업 닫기"""

        # 팝업 닫힘 시 함께 떠있는 호버 카드 정리
        self.hide_hover_card()
        self._popup_controller.close()

    def bind_hover_card(
        self,
        widget: QWidget,
        supplier: HoverCardSupplier,
    ) -> None:
        """위젯에 동적 호버 카드 동작 연결"""

        # 네이티브 툴팁과 중복되지 않도록 기존 텍스트 제거
        widget.setToolTip("")

        # 이벤트 필터 인스턴스를 보관하여 가비지 컬렉션 방지
        trigger: HoverCardTrigger = HoverCardTrigger(widget, self, supplier)
        self._hover_bindings.append(trigger)

    def show_hover_card(self, data: HoverCardData, global_pos: QPoint) -> None:
        """호버 카드 표시"""

        self._hover_card_host.show_at_cursor(data, global_pos)

    def hide_hover_card(self) -> None:
        """호버 카드 숨김"""

        self._hover_card_host.hide_card()

    def build_skill_hover_card(self, skill_id: str, level: int) -> HoverCardData:
        """스킬 정보 호버 카드 데이터 구성"""

        # 현재 서버 레지스트리에서 스킬 정의 조회
        skill_def: SkillDef = app_state.macro.current_server.skill_registry.get(
            skill_id
        )
        resolved_level: int = self._resolve_skill_level(skill_def, level)

        effect_lines: list[HoverCardLine] = self._build_effect_hover_lines(
            skill_def.levels[resolved_level]
        )

        lines: list[HoverCardLine] = [
            HoverCardLine(f"레벨 {resolved_level}", color="#F0EAD6"),
            HoverCardLine(
                f"쿨타임 {self._format_number(skill_def.cooltime)}초",
                color="#B8B4C7",
            ),
        ]
        lines.extend(effect_lines)

        return HoverCardData(title=skill_def.name, lines=tuple(lines))

    def build_scroll_hover_card(
        self,
        scroll_def: ScrollDef,
        level: int,
    ) -> HoverCardData:
        """무공비급 정보 호버 카드 데이터 구성"""

        # 무공비급 공용 레벨 표시 라인 먼저 구성
        lines: list[HoverCardLine] = [
            HoverCardLine(f"레벨 {level}", color="#F0EAD6"),
        ]

        # 포함된 두 스킬의 핵심 요약 순차 추가
        for skill_id in scroll_def.skills:
            skill_def: SkillDef = app_state.macro.current_server.skill_registry.get(
                skill_id
            )

            resolved_level: int = self._resolve_skill_level(skill_def, level)

            summary: str = self._build_effect_summary(skill_def.levels[resolved_level])

            lines.append(
                HoverCardLine(
                    f"{skill_def.name} | 쿨타임 {self._format_number(skill_def.cooltime)}초",
                    color="#EAE7F2",
                )
            )

            if summary:
                lines.append(HoverCardLine(summary, color="#B8B4C7"))

        return HoverCardData(title=scroll_def.name, lines=tuple(lines))

    def _resolve_skill_level(self, skill_def: SkillDef, level: int) -> int:
        """요청 레벨을 실제 보유 레벨 범위에 맞춰 보정"""

        # 원하는 스킬 레벨 데이터가 없으면, 보유한 레벨 중 가장 높은 레벨로 보정
        available_levels: list[int] = sorted(skill_def.levels.keys())

        if level in skill_def.levels:
            return level

        lower_levels: list[int] = [
            candidate_level
            for candidate_level in available_levels
            if candidate_level <= level
        ]

        if lower_levels:
            return lower_levels[-1]

        return available_levels[0]

    def _build_effect_hover_lines(
        self,
        effects: list[LevelEffect],
    ) -> list[HoverCardLine]:
        """효과 목록을 카드 본문 라인으로 변환"""

        # 현재 레벨의 각 효과를 한 줄씩 가독성 있게 구성
        lines: list[HoverCardLine] = []

        for effect in effects:
            text: str
            color: str

            if isinstance(effect, DamageEffect):
                text = (
                    f"{self._format_number(effect.time)}초: "
                    f"데미지 {self._format_number(effect.damage)}"
                )
                color = "#FFB36A"

            elif isinstance(effect, HealEffect):
                text = (
                    f"{self._format_number(effect.time)}초: "
                    f"회복 {self._format_number(effect.heal)}"
                )
                color = "#8FE9FF"

            elif isinstance(effect, BuffEffect):
                buff_effect: BuffEffect = effect
                stat_label: str = get_stat_label(buff_effect.stat)

                text = (
                    f"{self._format_number(buff_effect.time)}초: "
                    f"{stat_label} {self._format_number(buff_effect.value)} "
                    f"({self._format_number(buff_effect.duration)}초)"
                )
                color = "#9DDF8B"

            else:
                continue

            lines.append(HoverCardLine(text=text, color=color))

        return lines

    def _build_effect_summary(self, effects: list[LevelEffect]) -> str:
        """무공비급 카드용 짧은 효과 요약 구성"""

        # 여러 효과를 한 줄 요약으로 합쳐 무공비급 카드 높이 최소화
        summaries: list[str] = []

        for effect in effects:
            if isinstance(effect, DamageEffect):
                summaries.append(
                    f"{self._format_number(effect.time)}초 데미지 {self._format_number(effect.damage)}"
                )

            elif isinstance(effect, HealEffect):
                summaries.append(
                    f"{self._format_number(effect.time)}초 회복 {self._format_number(effect.heal)}"
                )

            elif isinstance(effect, BuffEffect):
                buff_effect: BuffEffect = effect
                stat_label: str = get_stat_label(buff_effect.stat)
                summaries.append(
                    f"{self._format_number(buff_effect.time)}초 {stat_label} {self._format_number(buff_effect.value)}"
                )

            else:
                continue

        return " / ".join(summaries)

    def _format_number(self, value: int | float) -> str:
        """정수형 표기는 간결하게, 실수형 표기는 필요한 자리만 유지"""

        # 불필요한 소수점 0 제거
        number: float = float(value)

        if number.is_integer():
            return str(int(number))

        return f"{number:.2f}".rstrip("0").rstrip(".")

    def make_action_list_popup(
        self,
        kind: PopupKind,
        anchor: QWidget,
        actions: list[PopupAction],
        placement: PopupPlacement,
    ) -> None:
        """ActionList 팝업 생성 공통 부분"""

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        if self._popup_controller.is_visible():
            self._popup_controller.close()

        self._active_popup = kind

        self._popup_controller.show_action_list(
            anchor=anchor,
            actions=actions,
            options=PopupOptions(placement=placement),
        )

    def make_input_popup(
        self,
        kind: PopupKind,
        anchor: QWidget,
        content: QWidget,
        placement: PopupPlacement,
    ) -> None:
        """Input 팝업 생성 공통 부분"""

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        if self._popup_controller.is_visible():
            self._popup_controller.close()

        self._active_popup = kind

        self._popup_controller.show_content(
            anchor=anchor,
            content=content,
            options=PopupOptions(placement=placement),
        )

    def make_server_popup(
        self,
        anchor: QWidget,
        on_selected: Callable[[ServerSpec], None],
    ) -> None:
        """서버 선택 팝업"""

        current_server: ServerSpec = app_state.macro.current_server

        actions: list[PopupAction] = [
            PopupAction(
                id=server.id,
                text=server.id,
                enabled=True,
                is_selected=(server == current_server),
                on_trigger=lambda s=server: on_selected(s),
            )
            for server in server_registry.get_all_servers()
        ]

        self.make_action_list_popup(
            kind=PopupKind.SERVER,
            anchor=anchor,
            actions=actions,
            placement=PopupPlacement.BELOW,
        )

    def make_delay_popup(
        self,
        anchor: QWidget,
        on_selected: Callable[[int], None],
    ) -> None:
        """딜레이 입력 팝업"""

        default_text = str(app_state.macro.current_delay)
        content = InputConfirmContent(default_text=default_text)

        def _submit(raw: str) -> None:
            self.close_popup()

            try:
                value = int(raw)

            except Exception:
                self.show_notice(NoticeKind.DELAY_INPUT_ERROR)
                return

            if not (config.specs.DELAY.min <= value <= config.specs.DELAY.max):
                self.show_notice(NoticeKind.DELAY_INPUT_ERROR)
                return

            # 콜백 실행
            on_selected(value)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.DELAY,
            anchor=anchor,
            content=content,
            placement=PopupPlacement.BELOW,
        )

    def make_cooltime_popup(
        self,
        anchor: QWidget,
        on_selected: Callable[[float], None],
    ) -> None:
        """쿨타임 감소 입력 팝업"""

        default_text = str(app_state.macro.current_cooltime_reduction)
        content = InputConfirmContent(default_text=default_text)

        def _submit(raw: str) -> None:
            self.close_popup()

            try:
                value = round(float(raw), 2)

            except Exception:
                self.show_notice(NoticeKind.COOLTIME_INPUT_ERROR)
                return

            if not (
                config.specs.COOLTIME_REDUCTION.min
                <= value
                <= config.specs.COOLTIME_REDUCTION.max
            ):
                self.show_notice(NoticeKind.COOLTIME_INPUT_ERROR)
                return

            # 콜백 실행
            on_selected(value)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.COOLTIME,
            anchor=anchor,
            content=content,
            placement=PopupPlacement.BELOW,
        )

    def make_start_key_popup(
        self,
        anchor: QWidget,
        on_selected: Callable[[KeySpec], None],
    ) -> None:
        """시작키 입력 팝업"""

        self._stop_key_listener()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        default_key: KeySpec = app_state.macro.current_start_key

        content = KeyCaptureContent(default_key=default_key)

        def _submit(key: KeySpec | None) -> None:
            self.close_popup()

            # 변경 없음
            if key is None or key == default_key:
                return

            # 키가 이미 사용중인 경우
            if app_state.is_key_using(key):
                self.show_notice(NoticeKind.START_KEY_CHANGE_ERROR)
                return

            on_selected(key)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.START_KEY,
            anchor=anchor,
            content=content,
            placement=PopupPlacement.BELOW,
        )

        def _on_press(k: pynput_keyboard.Key | pynput_keyboard.KeyCode | None) -> None:
            if not k:
                return

            key: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(k)

            if not key:
                return

            content.set_key(key)

        listener = pynput_keyboard.Listener(on_press=_on_press)
        listener.daemon = True
        listener.start()
        self._key_listener = listener
        app_state.ui.is_setting_key = True

    def make_tab_name_popup(
        self,
        anchor: QWidget,
        on_submitted: Callable[[str], None],
    ) -> None:
        """탭 이름 변경 팝업"""

        default_text: str = app_state.macro.current_preset.name
        content = InputConfirmContent(default_text=default_text)

        def _submit(text: str) -> None:
            self.close_popup()
            on_submitted(text)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.TAB_NAME,
            anchor=anchor,
            content=content,
            placement=PopupPlacement.BELOW,
        )

    def make_skill_key_popup(
        self,
        anchor: QWidget,
        default_key_id: str,
        on_selected: Callable[[KeySpec], None],
    ) -> None:
        """스킬키 입력 팝업"""

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        self._stop_key_listener()

        default_key: KeySpec = KeyRegistry.get(default_key_id)
        content: KeyCaptureContent = KeyCaptureContent(default_key=default_key)

        def _submit(key: KeySpec | None) -> None:
            self.close_popup()

            # 변경 없음
            if key is None or key == default_key:
                return

            # 키가 이미 사용중인 경우
            if app_state.is_key_using(key):
                self.show_notice(NoticeKind.START_KEY_CHANGE_ERROR)
                return

            on_selected(key)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.SKILL_KEY,
            anchor=anchor,
            content=content,
            placement=PopupPlacement.BELOW,
        )

        def _on_press(k: pynput_keyboard.Key | pynput_keyboard.KeyCode | None) -> None:
            if not k:
                return

            key: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(k)

            if not key:
                return

            content.set_key(key)

        listener: pynput_keyboard.Listener = pynput_keyboard.Listener(
            on_press=_on_press
        )
        listener.daemon = True
        listener.start()
        self._key_listener = listener
        app_state.ui.is_setting_key = True

    def make_scroll_select_popup(
        self,
        anchor: QWidget,
        scroll_defs: list[ScrollDef],
        equipped_scroll_ids: list[str],
        current_scroll_id: str,
        on_selected: Callable[[str], None],
        on_add_skill: Callable[[], None] | None = None,
    ) -> None:
        """무공비급 선택 팝업"""

        if app_state.macro.is_running:
            self.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        if self._popup_controller.is_visible():
            self._popup_controller.close()

        self._active_popup = PopupKind.SCROLL_SELECT

        def _open_add_dialog() -> None:
            server_spec: ServerSpec = app_state.macro.current_server
            dialog: CustomSkillAddDialog = CustomSkillAddDialog(
                server_id=server_spec.id,
                max_skill_level=server_spec.max_skill_level,
                parent=anchor,
            )

            def _on_added(skill_import: CustomSkillImport) -> None:
                # SkillRegistry에 주입
                for skill_id in skill_import.skills:
                    detail = skill_import.skill_details[skill_id]
                    skill_def: SkillDef = SkillDef.from_detail_dict(
                        skill_id, server_spec.id, detail.to_dict()
                    )
                    server_spec.skill_registry.add_skill_def(skill_def)

                for scroll in skill_import.scrolls:
                    scroll_def: ScrollDef = ScrollDef(
                        id=scroll.scroll_id,
                        server_id=server_spec.id,
                        name=scroll.name,
                        skills=scroll.skills,
                    )
                    server_spec.skill_registry.add_scroll_def(scroll_def)

                # 기존 custom_skills.json과 병합 저장
                existing_import: CustomSkillImport | None = None
                # 검증된 커스텀 스킬 원본에서 기존 서버 데이터 조회
                existing_raw: dict[str, dict] = read_custom_skills_data()
                if server_spec.id in existing_raw:
                    existing_import = CustomSkillImport.from_dict(
                        existing_raw[server_spec.id]
                    )

                if existing_import is not None:
                    merged_skills = tuple(
                        dict.fromkeys(existing_import.skills + skill_import.skills)
                    )
                    merged_scrolls = existing_import.scrolls + skill_import.scrolls
                    merged_details = {
                        **existing_import.skill_details,
                        **skill_import.skill_details,
                    }
                    merged = CustomSkillImport(
                        skills=merged_skills,
                        scrolls=merged_scrolls,
                        skill_details=merged_details,
                    )
                else:
                    merged = skill_import

                save_custom_skills(server_spec.id, merged)

                # 현재 세션 인-메모리에 새 무공비급/스킬 기본값 반영
                for preset in app_state.macro.presets:
                    for scroll in skill_import.scrolls:
                        preset.info.scroll_levels.setdefault(scroll.scroll_id, 1)
                    for skill_id in skill_import.skills:
                        preset.usage_settings.setdefault(skill_id, SkillUsageSetting())

                self.close_popup()
                if on_add_skill is not None:
                    on_add_skill()

            dialog.skill_added.connect(_on_added)
            dialog.exec()

        content: ScrollGridSelectContent = ScrollGridSelectContent(
            popup_manager=self,
            scroll_defs=scroll_defs,
            equipped_scroll_ids=equipped_scroll_ids,
            current_scroll_id=current_scroll_id,
            on_add_skill=_open_add_dialog,
        )

        def _picked(scroll_id: str) -> None:
            self.close_popup()
            on_selected(scroll_id)

        content.selected.connect(_picked)

        self._popup_controller.show_content(
            anchor=anchor,
            content=content,
            options=PopupOptions(placement=PopupPlacement.BELOW),
        )

    def make_link_skill_key_popup(
        self,
        anchor: QWidget,
        on_selected: Callable[[KeySpec], None],
    ) -> None:
        """연계스킬 키 입력 팝업"""

        self._stop_key_listener()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        content = KeyCaptureContent()

        def _submit(key: KeySpec | None) -> None:
            self.close_popup()

            if key is None:
                return

            # 키가 이미 사용중인 경우
            if app_state.is_key_using(key):
                self.show_notice(NoticeKind.START_KEY_CHANGE_ERROR)
                return

            on_selected(key)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.LINK_SKILL_KEY,
            anchor=anchor,
            content=content,
            placement=PopupPlacement.BELOW,
        )

        def _on_press(k: pynput_keyboard.Key | pynput_keyboard.KeyCode | None) -> None:
            if not k:
                return

            key: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(k)

            if not key:
                return

            content.set_key(key)

        listener = pynput_keyboard.Listener(on_press=_on_press)
        listener.daemon = True
        listener.start()
        self._key_listener = listener
        app_state.ui.is_setting_key = True

    def make_link_skill_select_popup(
        self,
        anchor: QWidget,
        skill_ids: list[str],
        on_selected: Callable[[str], None],
    ) -> None:
        """연계스킬 편집 페이지 스킬 선택 팝업"""

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        if self._popup_controller.is_visible():
            self._popup_controller.close()

        self._active_popup = PopupKind.LINK_SKILL_SELECT

        content: SkillGridSelectContent = SkillGridSelectContent(
            popup_manager=self,
            skill_ids=skill_ids,
        )

        def _picked(skill_id: str) -> None:
            self.close_popup()
            on_selected(skill_id)

        content.selected.connect(_picked)

        self._popup_controller.show_content(
            anchor=anchor,
            content=content,
            options=PopupOptions(placement=PopupPlacement.BELOW, x_offset=40),
        )


class SkillGridSelectContent(QFrame):
    """스킬 선택용 그리드 컨텐츠"""

    # todo: 스킬 이름을 확인할 수 있도록 개선
    # todo: 스킬을 선택하는 모든 팝업에 재사용 가능하도록 수정

    selected = Signal(str)

    def __init__(
        self,
        popup_manager: PopupManager,
        skill_ids: list[str],
    ) -> None:
        super().__init__()

        # 스킬 선택 팝업 루트 식별자 지정
        self.setObjectName("skillScrollSelectPopup")

        self.popup_manager: PopupManager = popup_manager
        columns: int = 5
        margin: int = 8
        spacing: int = 6
        icon_size: int = 40
        button_size: int = 44
        max_visible_rows: int = 6

        # 전체 컨테이너
        root = QVBoxLayout(self)
        root.setContentsMargins(margin, margin, margin, margin)
        root.setSpacing(spacing)

        # 무공비급 영역
        scroll = QScrollArea(self)
        # 공용 그리드 팝업 스타일 재사용 설정
        scroll.setObjectName("popupGridScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(scroll)
        # 공용 그리드 컨텐츠 배경 스타일 재사용 설정
        container.setObjectName("popupGridContent")
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(spacing)
        grid.setVerticalSpacing(spacing)

        # 버튼들
        # todo: 마지막 줄 가운데 정렬로 변경
        for idx, skill_id in enumerate(skill_ids):
            r: int = idx // columns
            c: int = idx % columns

            btn: QPushButton = QPushButton(container)
            btn.setObjectName("gridSelectBtn")
            btn.setFixedSize(button_size, button_size)
            btn.setIcon(QIcon(resource_registry.get_skill_pixmap(skill_id)))
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.clicked.connect(lambda _, sid=skill_id: self.selected.emit(sid))
            self.popup_manager.bind_hover_card(
                btn,
                lambda sid=skill_id: self._build_skill_hover_card(sid),
            )

            grid.addWidget(btn, r, c)

        # 마지막 줄 정렬용 stretch
        grid.setColumnStretch(columns, 1)

        container.setLayout(grid)
        scroll.setWidget(container)
        root.addWidget(scroll)
        self.setLayout(root)

        # 보여줄 최대 행 수만큼 높이 제한(무공비급로 나머지 보기)
        visible_rows: int = min(
            max_visible_rows,
            (len(skill_ids) + columns - 1) // columns,
        )
        estimated_h: int = margin * 2 + visible_rows * (button_size + spacing) - spacing
        scroll.setFixedHeight(estimated_h)

    def _build_skill_hover_card(self, skill_id: str) -> HoverCardData | None:
        """선택 가능한 스킬 버튼 기준 호버 카드 구성"""

        # 현재 프리셋 저장 레벨 기준으로 카드 내용 구성
        level: int = app_state.macro.current_preset.info.get_skill_level(
            app_state.macro.current_server,
            skill_id,
        )
        return self.popup_manager.build_skill_hover_card(skill_id, level)


class ScrollGridSelectContent(QFrame):
    """무공비급 선택용 그리드 컨텐츠"""

    selected = Signal(str)

    def __init__(
        self,
        popup_manager: PopupManager,
        scroll_defs: list[ScrollDef],
        equipped_scroll_ids: list[str],
        current_scroll_id: str,
        on_add_skill: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        # 무공비급 선택 팝업 루트 식별자 지정
        self.setObjectName("skillScrollSelectPopup")

        self.popup_manager: PopupManager = popup_manager
        columns: int = 5
        margin: int = 8
        spacing: int = 6
        icon_size: int = 40
        button_size: int = 44
        max_visible_rows: int = 6
        occupied_scroll_ids: set[str] = {
            scroll_id
            for scroll_id in equipped_scroll_ids
            if scroll_id and scroll_id != current_scroll_id
        }

        root: QVBoxLayout = QVBoxLayout(self)
        root.setContentsMargins(margin, margin, margin, margin)
        root.setSpacing(spacing)

        scroll_area: QScrollArea = QScrollArea(self)
        scroll_area.setObjectName("popupGridScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container: QWidget = QWidget(scroll_area)
        container.setObjectName("popupGridContent")
        grid: QGridLayout = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(spacing)
        grid.setVerticalSpacing(spacing)

        for idx, scroll_def in enumerate(scroll_defs):
            row: int = idx // columns
            column: int = idx % columns

            is_selected: bool = scroll_def.id == current_scroll_id
            is_occupied: bool = scroll_def.id in occupied_scroll_ids

            btn: QPushButton = QPushButton(container)
            btn.setObjectName("gridSelectBtn")
            btn.setFixedSize(button_size, button_size)
            btn.setIcon(QIcon(resource_registry.get_scroll_pixmap(scroll_def.id)))
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setCursor(
                Qt.CursorShape.ArrowCursor
                if is_occupied
                else Qt.CursorShape.PointingHandCursor
            )

            btn.clicked.connect(
                lambda _, scroll_id=scroll_def.id, occupied=is_occupied: self._emit_scroll_selected(
                    scroll_id,
                    occupied,
                )
            )
            self.popup_manager.bind_hover_card(
                btn,
                lambda scroll_definition=scroll_def: self._build_scroll_hover_card(
                    scroll_definition
                ),
            )

            grid.addWidget(btn, row, column)

        grid.setColumnStretch(columns, 1)

        container.setLayout(grid)
        scroll_area.setWidget(container)
        root.addWidget(scroll_area)

        if on_add_skill is not None:
            add_btn: QPushButton = QPushButton("+ 새 스킬 추가", self)
            add_btn.setObjectName("gridAddBtn")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(on_add_skill)
            root.addWidget(add_btn)

        self.setLayout(root)

        visible_rows: int = min(
            max_visible_rows,
            (len(scroll_defs) + columns - 1) // columns,
        )
        estimated_height: int = (
            margin * 2 + visible_rows * (button_size + spacing) - spacing
        )
        scroll_area.setFixedHeight(estimated_height)

    def _emit_scroll_selected(self, scroll_id: str, is_occupied: bool) -> None:
        """점유 여부를 확인한 뒤 무공비급 선택 이벤트 전달"""

        # 다른 칸에서 사용 중인 무공비급은 선택만 차단
        if is_occupied:
            return

        self.selected.emit(scroll_id)

    def _build_scroll_hover_card(
        self,
        scroll_def: ScrollDef,
    ) -> HoverCardData | None:
        """무공비급 버튼 기준 호버 카드 구성"""

        # 무공비급 ID 자체를 공용 레벨 저장 키로 직접 사용
        level: int = app_state.macro.current_preset.info.get_scroll_level(scroll_def.id)
        return self.popup_manager.build_scroll_hover_card(scroll_def, level)


class CustomSkillAddDialog(QDialog):
    """커스텀 무공비급/스킬 추가·수정 폼 다이얼로그"""

    skill_added = Signal(CustomSkillImport)

    def __init__(
        self,
        server_id: str,
        max_skill_level: int,
        existing_scroll: CustomScrollDefinition | None = None,
        existing_skills: dict[str, CustomSkillDefinition] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.server_id: str = server_id
        self.max_skill_level: int = max_skill_level
        self._existing_scroll = existing_scroll

        is_edit: bool = existing_scroll is not None
        self.setObjectName("customSkillDialog")
        self.setWindowTitle("무공비급 수정" if is_edit else "무공비급 추가")
        self.setFixedSize(400, 520)

        # 기존 값 준비
        scroll_name_init: str = existing_scroll.name if existing_scroll else ""
        skill1_id: str = existing_scroll.skills[0] if existing_scroll else ""
        skill2_id: str = existing_scroll.skills[1] if existing_scroll else ""
        skill1_def = (existing_skills or {}).get(skill1_id)
        skill2_def = (existing_skills or {}).get(skill2_id)
        skill1_name_init: str = skill1_def.name if skill1_def else ""
        skill2_name_init: str = skill2_def.name if skill2_def else ""
        skill1_ct_init: str = str(skill1_def.cooltime) if skill1_def else ""
        skill2_ct_init: str = str(skill2_def.cooltime) if skill2_def else ""
        skill1_levels_init = skill1_def.levels if skill1_def else {}
        skill2_levels_init = skill2_def.levels if skill2_def else {}

        # ── 전체 컨텐츠를 QScrollArea로 감쌈 ──
        outer: QVBoxLayout = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        main_scroll: QScrollArea = QScrollArea(self)
        main_scroll.setObjectName("dialogScrollArea")
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(main_scroll)

        # 다이얼로그 스크롤 뷰포트 배경 식별자 지정
        dialog_viewport: QWidget = main_scroll.viewport()
        dialog_viewport.setObjectName("dialogScrollViewport")

        content_widget: QWidget = QWidget()
        # 다이얼로그 스크롤 컨텐츠 배경 식별자 지정
        content_widget.setObjectName("dialogScrollContent")
        main_scroll.setWidget(content_widget)

        root: QVBoxLayout = QVBoxLayout(content_widget)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ── 무공비급 카드 ──
        scroll_card, (self._scroll_name_input,) = self._make_card(
            "무공비급",
            [("이름", scroll_name_init)],
        )
        root.addWidget(scroll_card)

        # ── 스킬 1 카드 ──
        (
            skill1_card,
            self._skill1_name_input,
            self._skill1_ct_input,
            self._skill1_level_inputs,
        ) = self._make_skill_card(
            "스킬 1", skill1_name_init, skill1_ct_init, 1, skill1_levels_init
        )
        root.addWidget(skill1_card)

        # ── 스킬 2 카드 (7강 미만은 데미지 0 고정) ──
        (
            skill2_card,
            self._skill2_name_input,
            self._skill2_ct_input,
            self._skill2_level_inputs,
        ) = self._make_skill_card(
            "스킬 2", skill2_name_init, skill2_ct_init, 7, skill2_levels_init
        )
        root.addWidget(skill2_card)
        root.addStretch()

        # ── 에러 라벨 (무공비급 영역 밖, 하단 고정) ──
        self._error_label: QLabel = QLabel(self)
        self._error_label.setObjectName("dialogErrorLabel")
        self._error_label.setFont(CustomFont(10))
        self._error_label.setWordWrap(True)
        self._error_label.setContentsMargins(20, 0, 20, 0)
        self._error_label.hide()
        outer.addWidget(self._error_label)

        # ── 버튼 행 (무공비급 영역 밖, 하단 고정) ──
        btn_row: QHBoxLayout = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setContentsMargins(20, 8, 20, 16)

        cancel_btn: QPushButton = QPushButton("취소", self)
        cancel_btn.setObjectName("dialogCancelBtn")
        cancel_btn.setFont(CustomFont(11))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        confirm_btn: QPushButton = QPushButton("저장" if is_edit else "추가", self)
        confirm_btn.setObjectName("dialogConfirmBtn")
        confirm_btn.setFont(CustomFont(11))
        confirm_btn.setFixedHeight(36)
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        outer.addLayout(btn_row)

    def _make_card(
        self, title: str, fields: list[tuple[str, str]]
    ) -> tuple[QFrame, list[CustomLineEdit]]:
        """제목 + 필드 목록으로 카드 위젯 생성. 입력 위젯 리스트 반환."""
        card: QFrame = QFrame(self)
        card.setObjectName("dialogCard")

        layout: QVBoxLayout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_lbl: QLabel = QLabel(title, card)
        title_lbl.setObjectName("dialogSectionTitle")
        title_lbl.setFont(CustomFont(11))
        layout.addWidget(title_lbl)

        inputs: list[CustomLineEdit] = []
        for label_text, init_value in fields:
            row: QHBoxLayout = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)

            lbl: QLabel = QLabel(label_text, card)
            lbl.setObjectName("dialogFieldLabel")
            lbl.setFont(CustomFont(10))
            lbl.setFixedWidth(74)

            inp: CustomLineEdit = CustomLineEdit(
                card, text=init_value, point_size=11, border_radius=6
            )
            inp.setFixedHeight(32)
            inp.set_valid(True)

            row.addWidget(lbl)
            row.addWidget(inp)
            layout.addLayout(row)
            inputs.append(inp)

        return card, inputs

    def _make_skill_card(
        self,
        title: str,
        name_init: str,
        ct_init: str,
        level_start: int,
        existing_levels: dict | None = None,
    ) -> tuple[QFrame, CustomLineEdit, CustomLineEdit, dict[int, SkillLevelInputRow]]:
        """스킬 카드 + 레벨별 효과 입력 (기본 숨김) 생성."""
        card: QFrame = QFrame(self)
        card.setObjectName("dialogCard")

        layout: QVBoxLayout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_lbl: QLabel = QLabel(title, card)
        title_lbl.setObjectName("dialogSectionTitle")
        title_lbl.setFont(CustomFont(11))
        layout.addWidget(title_lbl)

        def _make_row(label_text: str, init_value: str) -> CustomLineEdit:
            row: QHBoxLayout = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)
            lbl: QLabel = QLabel(label_text, card)
            lbl.setObjectName("dialogFieldLabel")
            lbl.setFont(CustomFont(10))
            lbl.setFixedWidth(74)
            inp: CustomLineEdit = CustomLineEdit(
                card, text=init_value, point_size=11, border_radius=6
            )
            inp.setFixedHeight(32)
            inp.set_valid(True)
            row.addWidget(lbl)
            row.addWidget(inp)
            layout.addLayout(row)
            return inp

        name_input: CustomLineEdit = _make_row("이름", name_init)
        ct_input: CustomLineEdit = _make_row("쿨타임 (초)", ct_init)

        # ── 레벨별 효과 토글 버튼 ──
        toggle_btn: QPushButton = QPushButton("레벨별 효과 설정 ▼", card)
        toggle_btn.setFont(CustomFont(10))
        toggle_btn.setFixedHeight(26)
        toggle_btn.setObjectName("dialogToggleBtn")
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(toggle_btn)

        # ── 레벨 입력 영역 (기본 숨김) ──
        level_widget: QWidget = QWidget(card)
        level_widget.setVisible(False)
        level_layout: QVBoxLayout = QVBoxLayout(level_widget)
        level_layout.setContentsMargins(0, 2, 0, 2)
        level_layout.setSpacing(3)

        # 레벨별 입력 위젯 묶음 구성
        level_inputs: dict[int, SkillLevelInputRow] = {}

        for lvl in range(level_start, self.max_skill_level + 1):
            row: QHBoxLayout = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(5)

            lv_lbl: QLabel = QLabel(f"Lv.{lvl}", level_widget)
            lv_lbl.setObjectName("dialogFieldLabel")
            lv_lbl.setFont(CustomFont(9))
            lv_lbl.setFixedWidth(30)

            type_combo: QComboBox = QComboBox(level_widget)
            type_combo.addItems(["데미지", "힐", "버프"])
            type_combo.setFont(CustomFont(9))
            type_combo.setFixedHeight(24)
            type_combo.setFixedWidth(58)

            amount_inp: CustomLineEdit = CustomLineEdit(
                level_widget, text="0", point_size=9
            )
            amount_inp.setFixedHeight(24)
            amount_inp.setFixedWidth(56)
            amount_inp.set_valid(True)

            # 버프 대상 스탯 선택 콤보 구성
            stat_combo: QComboBox = QComboBox(level_widget)
            stat_key: StatKey
            for stat_key in StatKey:
                stat_combo.addItem(get_stat_label(stat_key), stat_key.value)

            stat_combo.setFont(CustomFont(9))
            stat_combo.setFixedHeight(24)
            stat_combo.setFixedWidth(118)
            stat_combo.setVisible(False)

            duration_inp: CustomLineEdit = CustomLineEdit(
                level_widget, text="0", point_size=9
            )
            duration_inp.setPlaceholderText("지속(초)")
            duration_inp.setFixedHeight(24)
            duration_inp.setFixedWidth(52)
            duration_inp.set_valid(True)
            duration_inp.setVisible(False)

            # 기존 레벨 데이터 로드
            if existing_levels and lvl in existing_levels:
                effects = existing_levels[lvl]
                if effects:
                    effect = effects[0]
                    if effect.type == SkillEffectType.HEAL:
                        type_combo.setCurrentIndex(1)
                        amount_inp.setText(str(effect.heal))  # type: ignore[union-attr]
                    elif effect.type == SkillEffectType.BUFF:
                        type_combo.setCurrentIndex(2)
                        amount_inp.setText(str(effect.value))  # type: ignore[union-attr]
                        # 저장된 스탯 키 기반 선택 상태 복원
                        buff_stat_key: StatKey = StatKey(str(effect.stat))  # type: ignore[union-attr]
                        stat_combo.setCurrentIndex(
                            stat_combo.findData(buff_stat_key.value)
                        )
                        duration_inp.setText(str(effect.duration))  # type: ignore[union-attr]
                        stat_combo.setVisible(True)
                        duration_inp.setVisible(True)
                    else:
                        amount_inp.setText(str(effect.damage))  # type: ignore[union-attr]

            def _on_type_change(
                idx: int,
                sc: QComboBox = stat_combo,
                di: CustomLineEdit = duration_inp,
            ) -> None:
                # 버프 타입 선택 시 추가 입력 위젯 노출
                is_buff = idx == 2
                sc.setVisible(is_buff)
                di.setVisible(is_buff)

            type_combo.currentIndexChanged.connect(_on_type_change)

            row.addWidget(lv_lbl)
            row.addWidget(type_combo)
            row.addWidget(amount_inp)
            row.addWidget(stat_combo)
            row.addWidget(duration_inp)
            row.addStretch()
            level_layout.addLayout(row)
            level_inputs[lvl] = SkillLevelInputRow(
                type_combo=type_combo,
                amount_input=amount_inp,
                stat_combo=stat_combo,
                duration_input=duration_inp,
            )

        layout.addWidget(level_widget)

        def _toggle_levels() -> None:
            visible: bool = not level_widget.isVisible()
            level_widget.setVisible(visible)
            toggle_btn.setText(
                "레벨별 효과 설정 ▲" if visible else "레벨별 효과 설정 ▼"
            )

        toggle_btn.clicked.connect(_toggle_levels)

        return card, name_input, ct_input, level_inputs

    def _build_levels(
        self,
        level_inputs: dict[int, SkillLevelInputRow],
        level_start: int,
    ) -> dict:
        """레벨 입력 위젯에서 levels dict 생성. level_start 미만은 데미지 0 고정."""
        levels: dict = {}

        # 시작 레벨 이전 구간 기본 데미지 효과 구성
        for lvl in range(1, level_start):
            levels[str(lvl)] = [{"time": 0.0, "type": "damage", "damage": 0.0}]

        # 레벨별 선택 타입에 맞는 저장 페이로드 구성
        for lvl, input_row in level_inputs.items():
            type_idx: int = input_row.type_combo.currentIndex()
            try:
                amount: float = float(input_row.amount_input.text().strip() or "0")
            except ValueError:
                amount = 0.0

            if type_idx == 1:  # 힐
                levels[str(lvl)] = [{"time": 0.0, "type": "heal", "heal": amount}]
            elif type_idx == 2:  # 버프
                # 선택형 콤보의 현재 스탯 키 저장
                stat: str = str(input_row.stat_combo.currentData())
                try:
                    duration: float = float(
                        input_row.duration_input.text().strip() or "0"
                    )
                except ValueError:
                    duration = 0.0
                levels[str(lvl)] = [
                    {
                        "time": 0.0,
                        "type": "buff",
                        "stat": stat,
                        "value": amount,
                        "duration": duration,
                    }
                ]
            else:  # 데미지
                levels[str(lvl)] = [{"time": 0.0, "type": "damage", "damage": amount}]
        return levels

    def _validate_duplicate_names(
        self,
        scroll_name: str,
        skill1_name: str,
        skill2_name: str,
    ) -> bool:
        """이름 기반 중복 입력 검증"""

        # 같은 무공비급 내부 스킬 이름 중복 차단 블록
        if skill1_name == skill2_name:
            self._skill1_name_input.set_valid(False)
            self._skill2_name_input.set_valid(False)
            self._show_error("스킬 1과 스킬 2의 이름은 서로 달라야 합니다.")
            return False

        self._skill1_name_input.set_valid(True)
        self._skill2_name_input.set_valid(True)

        # 동일 서버 내 커스텀 무공비급 이름 중복 차단 블록
        server_spec: ServerSpec = server_registry.get(self.server_id)
        current_scroll_id: str = ""
        if self._existing_scroll is not None:
            current_scroll_id = self._existing_scroll.scroll_id

        scroll_def: ScrollDef
        for scroll_def in server_spec.skill_registry.get_all_scroll_defs():
            if not scroll_def.id.startswith(f"{CUSTOM_SKILL_PREFIX}:"):
                continue

            if scroll_def.id == current_scroll_id:
                continue

            if scroll_def.name != scroll_name:
                continue

            self._scroll_name_input.set_valid(False)
            self._show_error("같은 이름의 커스텀 무공비급이 이미 존재합니다.")
            return False

        self._scroll_name_input.set_valid(True)
        return True

    def _on_confirm(self) -> None:
        scroll_name: str = self._scroll_name_input.text().strip()
        skill1_name: str = self._skill1_name_input.text().strip()
        skill1_ct_text: str = self._skill1_ct_input.text().strip()
        skill2_name: str = self._skill2_name_input.text().strip()
        skill2_ct_text: str = self._skill2_ct_input.text().strip()

        # 필드 유효성 검사
        valid: bool = True
        for inp, value, msg in [
            (self._scroll_name_input, scroll_name, "무공비급 이름을 입력해주세요."),
            (self._skill1_name_input, skill1_name, "스킬 1 이름을 입력해주세요."),
            (self._skill2_name_input, skill2_name, "스킬 2 이름을 입력해주세요."),
        ]:
            if not value:
                inp.set_valid(False)
                if valid:
                    self._show_error(msg)
                valid = False
            else:
                inp.set_valid(True)

        skill1_ct: float = 0.0
        skill2_ct: float = 0.0
        try:
            skill1_ct = float(skill1_ct_text)
            self._skill1_ct_input.set_valid(True)
        except ValueError:
            self._skill1_ct_input.set_valid(False)
            if valid:
                self._show_error("스킬 1 쿨타임은 숫자여야 합니다.")
            valid = False

        try:
            skill2_ct = float(skill2_ct_text)
            self._skill2_ct_input.set_valid(True)
        except ValueError:
            self._skill2_ct_input.set_valid(False)
            if valid:
                self._show_error("스킬 2 쿨타임은 숫자여야 합니다.")
            valid = False

        if not valid:
            return

        # 이름 기반 ID 충돌을 유발하는 중복 입력 차단 블록
        if not self._validate_duplicate_names(scroll_name, skill1_name, skill2_name):
            return

        # 수정 모드면 기존 ID 유지, 신규면 이름 기반 ID 생성
        if self._existing_scroll is not None:
            scroll_id: str = self._existing_scroll.scroll_id
            skill1_id: str = self._existing_scroll.skills[0]
            skill2_id: str = self._existing_scroll.skills[1]
        else:
            scroll_id = f"custom:{self.server_id}:{scroll_name}"
            skill1_id = f"custom:{self.server_id}:{scroll_name}:{skill1_name}"
            skill2_id = f"custom:{self.server_id}:{scroll_name}:{skill2_name}"

        skill1_levels: dict = self._build_levels(self._skill1_level_inputs, 1)
        skill2_levels: dict = self._build_levels(self._skill2_level_inputs, 7)

        raw: dict = {
            "skills": [skill1_id, skill2_id],
            "scrolls": [
                {
                    "scroll_id": scroll_id,
                    "name": scroll_name,
                    "skills": [skill1_id, skill2_id],
                }
            ],
            "skill_details": {
                skill1_id: {
                    "name": skill1_name,
                    "cooltime": skill1_ct,
                    "levels": skill1_levels,
                },
                skill2_id: {
                    "name": skill2_name,
                    "cooltime": skill2_ct,
                    "levels": skill2_levels,
                },
            },
        }

        try:
            skill_import: CustomSkillImport = CustomSkillImport.from_dict(raw)
        except (CustomSkillImportError, KeyError, ValueError) as exc:
            self._show_error(str(exc))
            return

        self._error_label.hide()
        self.skill_added.emit(skill_import)
        self.accept()

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()
