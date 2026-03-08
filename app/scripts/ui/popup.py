from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from typing import TYPE_CHECKING, Literal
from webbrowser import open_new

from pynput import keyboard as pynput_keyboard
from PyQt6.QtCore import (
    QCoreApplication,
    QEvent,
    QPoint,
    QRect,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QGuiApplication, QIcon, QPixmap, QScreen
from PyQt6.QtWidgets import (
    QApplication,
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
from app.scripts.config import config
from app.scripts.custom_classes import CustomFont, CustomLineEdit, CustomShadowEffect
from app.scripts.registry.key_registry import KeyRegistry
from app.scripts.registry.resource_registry import (
    convert_resource_path,
    resource_registry,
)
from app.scripts.registry.server_registry import ServerSpec, server_registry
from app.scripts.registry.skill_registry import ScrollDef

if TYPE_CHECKING:
    from app.scripts.registry.key_registry import KeySpec
    from app.scripts.ui.main_ui.main_ui import MainUI
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

    # 시뮬레이션
    SIM_INPUT_ERROR = auto()  # 시뮬레이션 정보 입력 오류
    SIM_CHAR_LOAD_ERROR = auto()  # 캐릭터 로드 실패
    SIM_CARD_ERROR = auto()  # 카드 생성 오류
    SIM_CARD_POWER_ERROR = auto()  # 전투력 미선택
    SIM_CARD_NOT_UPDATED = auto()  # 입력 완료 필요


@dataclass
class NoticeData:
    text: str
    icon: str = "error"  # 기본값
    extra_action: tuple[str, Callable] | None = None
    height: int = 70


@dataclass(frozen=True)
class PopupOptions:
    """팝업의 표시 옵션"""

    placement: PopupPlacement = PopupPlacement.BELOW
    margin: int = 3


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


class PopupContent(QFrame):
    """팝업 내용의 기본 클래스"""

    def __init__(self, fixed_width: int) -> None:
        super().__init__()

        self.setFixedWidth(fixed_width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("QFrame { background-color: transparent; }")


class NoticeContent(PopupContent):

    closed = pyqtSignal()

    def __init__(self, data: NoticeData) -> None:
        super().__init__(350)

        # 높이 설정
        # self.setFixedHeight(data.height)

        # 프레임 스타일 설정
        self.setStyleSheet("background-color: white; border-radius: 10px;")
        # 그림자 효과 설정
        self.setGraphicsEffect(CustomShadowEffect(0, 5, 30, 150))

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setLayout(layout)

        icon = QLabel()
        icon.setStyleSheet("background-color: transparent;")
        icon.setFixedSize(24, 24)
        pixmap = QPixmap(convert_resource_path(f"resources\\image\\{data.icon}.png"))
        icon.setPixmap(pixmap)
        icon.setScaledContents(True)
        icon_layout = QVBoxLayout()
        icon_layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(icon_layout)

        label = QLabel(data.text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setFont(CustomFont(12))
        label.setStyleSheet("background-color: white; border-radius: 10px;")
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        content_layout = QVBoxLayout()
        content_layout.addWidget(label)
        content_layout.setSpacing(10)
        layout.addLayout(content_layout)

        if data.extra_action:
            action_text, action_callback = data.extra_action

            action_button = QPushButton(action_text)
            action_button.setFont(CustomFont(12))
            action_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #86A7FC; border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #6498f0;
                }
                """
            )
            action_button.setFixedSize(120, 32)
            action_button.clicked.connect(action_callback)
            action_button.setCursor(Qt.CursorShape.PointingHandCursor)

            content_layout.addWidget(action_button)

        remove_btn = QPushButton()
        remove_btn.setStyleSheet(
            """
            QPushButton {
                background-color: white; border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
            """
        )
        remove_btn.setFixedSize(24, 24)
        remove_btn.clicked.connect(self.closed.emit)
        pixmap = QPixmap(convert_resource_path("resources\\image\\x.png"))
        remove_btn.setIcon(QIcon(pixmap))
        remove_btn.setIconSize(QSize(20, 20))
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        remove_layout = QVBoxLayout()
        remove_layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(remove_layout)


class ActionListContent(PopupContent):
    """
    서버/직업 같은 목록 선택용 content
    PopupAction 리스트를 받아 버튼 목록을 생성
    """

    triggered = pyqtSignal(str)

    def __init__(
        self,
        actions: list[PopupAction],
    ) -> None:
        super().__init__(130)

        self.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                border-radius: 10px;
                border: none;
                padding: 2px;
                margin: 2px;
            }
            QPushButton[selected=true] { background-color: #dddddd; }
            QPushButton:hover { background-color: #cccccc; }
            QPushButton:!enabled { background-color: #f0f0f0; }
            """
        )

        # 스크롤바 없이 전체 항목을 나열
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

    submitted = pyqtSignal(str)

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
        self._btn.setFont(CustomFont(12))
        self._btn.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #bbbbbb;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
            """
        )
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

    submitted = pyqtSignal(object)  # KeySpec | None
    _key_received = pyqtSignal(object)

    def __init__(self, default_key: KeySpec | None = None) -> None:
        super().__init__(200)

        self._current_key: KeySpec | None = default_key

        self._label = QLabel(self)
        self._label.setFont(CustomFont(12))
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            "QLabel { background-color: white; border-radius: 10px; border: 1px solid #bbbbbb; padding: 2px; }"
        )
        self._label.setFixedHeight(30)
        self._label.setText("키를 입력해주세요")

        self._btn = QPushButton("확인", self)
        self._btn.setFont(CustomFont(12))
        self._btn.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #bbbbbb;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
            """
        )
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

    closed = pyqtSignal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.master: QWidget = parent

        # 배경 투명화
        self.setStyleSheet("background: transparent;")

        # 팝업 내용이 들어가는 컨테이너
        self._container = QFrame(self)
        self._container.setObjectName("popupContainer")
        self._container.setStyleSheet(
            "QFrame#popupContainer { background-color: white; border-radius: 10px; border: none; }"
        )

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

        # 스크롤 이벤트를 감지하기 위한 이벤트 필터 설치
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

        # 팝업 위치 설정 및 표시
        self.move(x, y)

    def eventFilter(self, obj, event: QEvent) -> bool:  # type: ignore
        """부모 위젯의 스크롤 이벤트를 감지"""

        # 스크롤 이벤트 감지 및 팝업 닫기
        if self.isVisible() and event.type() == QEvent.Type.Wheel:
            self.close()
            return False

        return super().eventFilter(obj, event)

    def focusOutEvent(self, a0) -> None:
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

        super().focusOutEvent(a0)

    def closeEvent(self, a0) -> None:
        """팝업이 닫힐 때 호출"""
        self.closed.emit()
        super().closeEvent(a0)


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

    def focusOutEvent(self, a0) -> None:
        """포커스를 잃어도 닫히지 않도록"""
        pass

    def eventFilter(self, obj, event: QEvent) -> bool:  # type: ignore
        """부모 위젯의 스크롤 이벤트를 감지"""

        # 스크롤 이벤트 감지
        if event.type() == QEvent.Type.Wheel:
            return False

        return super().eventFilter(obj, event)


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
                    f"쿨타임은 {config.specs.COOLTIME_REDUCTION.min}~{config.specs.COOLTIME_REDUCTION.max}까지의 수를 입력해야 합니다."
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

        self._popup_controller.close()

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
        on_selected: Callable[[int], None],
    ) -> None:
        """쿨타임 감소 입력 팝업"""

        default_text = str(app_state.macro.current_cooltime_reduction)
        content = InputConfirmContent(default_text=default_text)

        def _submit(raw: str) -> None:
            self.close_popup()

            try:
                value = int(raw)

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
    ) -> None:
        """스크롤 선택 팝업"""

        if app_state.macro.is_running:
            self.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        if self._popup_controller.is_visible():
            self._popup_controller.close()

        self._active_popup = PopupKind.SCROLL_SELECT

        content: ScrollGridSelectContent = ScrollGridSelectContent(
            scroll_defs=scroll_defs,
            equipped_scroll_ids=equipped_scroll_ids,
            current_scroll_id=current_scroll_id,
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

        content = SkillGridSelectContent(skill_ids=skill_ids)

        def _picked(skill_id: str) -> None:
            self.close_popup()
            on_selected(skill_id)

        content.selected.connect(_picked)

        self._popup_controller.show_content(
            anchor=anchor,
            content=content,
            options=PopupOptions(placement=PopupPlacement.BELOW),
        )


class SkillGridSelectContent(QFrame):
    """스킬 선택용 그리드 컨텐츠"""

    # todo: 스킬 이름을 확인할 수 있도록 개선
    # todo: 스킬을 선택하는 모든 팝업에 재사용 가능하도록 수정

    selected = pyqtSignal(str)

    def __init__(
        self,
        skill_ids: list[str],
    ) -> None:
        super().__init__()

        columns: int = 5
        margin = 8
        spacing = 6
        icon_size: int = 40
        button_size: int = 44
        max_visible_rows: int = 6

        # 전체 컨테이너
        root = QVBoxLayout(self)
        root.setContentsMargins(margin, margin, margin, margin)
        root.setSpacing(spacing)

        # 스크롤 영역
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(scroll)
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(spacing)
        grid.setVerticalSpacing(spacing)

        # 버튼들
        # todo: 마지막 줄 가운데 정렬로 변경
        for idx, skill_id in enumerate(skill_ids):
            r: int = idx // columns
            c: int = idx % columns

            btn = QPushButton(container)
            btn.setFixedSize(button_size, button_size)
            btn.setIcon(QIcon(resource_registry.get_skill_pixmap(skill_id)))
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setToolTip(
                app_state.macro.current_server.skill_registry.get(skill_id).name
            )
            btn.setStyleSheet(
                """
                QPushButton { background-color: white; border-radius: 10px; border: 1px solid #dddddd; }
                QPushButton:hover { background-color: #eeeeee; }
                """
            )
            btn.clicked.connect(lambda _, sid=skill_id: self.selected.emit(sid))

            grid.addWidget(btn, r, c)

        # 마지막 줄 정렬용 stretch
        grid.setColumnStretch(columns, 1)

        container.setLayout(grid)
        scroll.setWidget(container)
        root.addWidget(scroll)
        self.setLayout(root)

        # 보여줄 최대 행 수만큼 높이 제한(스크롤로 나머지 보기)
        visible_rows: int = min(
            max_visible_rows,
            (len(skill_ids) + columns - 1) // columns,
        )
        estimated_h: int = margin * 2 + visible_rows * (button_size + spacing) - spacing
        scroll.setFixedHeight(estimated_h)


class ScrollGridSelectContent(QFrame):
    """스크롤 선택용 그리드 컨텐츠"""

    selected = pyqtSignal(str)

    def __init__(
        self,
        scroll_defs: list[ScrollDef],
        equipped_scroll_ids: list[str],
        current_scroll_id: str,
    ) -> None:
        super().__init__()

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
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container: QWidget = QWidget(scroll_area)
        grid: QGridLayout = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(spacing)
        grid.setVerticalSpacing(spacing)

        for idx, scroll_def in enumerate(scroll_defs):
            row: int = idx // columns
            column: int = idx % columns

            is_selected: bool = scroll_def.id == current_scroll_id
            is_disabled: bool = scroll_def.id in occupied_scroll_ids

            tooltip_lines: list[str] = [scroll_def.name]

            if is_disabled:
                tooltip_lines.append("이미 다른 칸에 장착됨")

            btn: QPushButton = QPushButton(container)
            btn.setFixedSize(button_size, button_size)
            btn.setIcon(QIcon(resource_registry.get_scroll_pixmap(scroll_def.id)))
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setToolTip("\n".join(tooltip_lines))
            btn.setEnabled(not is_disabled)

            border_color: str = "#2563EB" if is_selected else "#DDDDDD"
            border_width: int = 2 if is_selected else 1
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: white;
                    border-radius: 10px;
                    border: {border_width}px solid {border_color};
                }}
                QPushButton:hover:enabled {{
                    background-color: #EEEEEE;
                }}
                QPushButton:disabled {{
                    background-color: #F2F2F2;
                }}
                """
            )
            btn.clicked.connect(
                lambda _, scroll_id=scroll_def.id: self.selected.emit(scroll_id)
            )

            grid.addWidget(btn, row, column)

        grid.setColumnStretch(columns, 1)

        container.setLayout(grid)
        scroll_area.setWidget(container)
        root.addWidget(scroll_area)
        self.setLayout(root)

        visible_rows: int = min(
            max_visible_rows,
            (len(scroll_defs) + columns - 1) // columns,
        )
        estimated_height: int = (
            margin * 2 + visible_rows * (button_size + spacing) - spacing
        )
        scroll_area.setFixedHeight(estimated_height)
