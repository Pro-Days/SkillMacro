from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from typing import TYPE_CHECKING
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

    SETTING_SERVER = "settingServer"
    SETTING_JOB = "settingJob"
    SETTING_DELAY = "settingDelay"
    SETTING_COOLTIME = "settingCooltime"
    SETTING_START_KEY = "settingStartKey"
    TAB_NAME = "tabName"
    SKILL_KEY = "skillKey"
    LINK_SKILL_KEY = "linkSkillKey"
    LINK_SKILL_SELECT = "linkSkillSelect"


@dataclass(frozen=True)
class PopupOptions:
    """팝업의 표시 옵션"""

    placement: PopupPlacement = PopupPlacement.BELOW
    margin: int = 3
    screen_margin: int = 8


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


def _get_fit_position(rect: QRect, screen_rect: QRect, margin: int) -> QRect:
    """팝업이 화면 밖으로 나가지 않도록 위치 보정"""

    x: int = rect.x()
    y: int = rect.y()

    min_x: int = screen_rect.left() + margin
    max_x: int = screen_rect.right() - margin - rect.width() + 1
    min_y: int = screen_rect.top() + margin
    max_y: int = screen_rect.bottom() - margin - rect.height() + 1

    x = max(min_x, min(x, max_x))
    y = max(min_y, min(y, max_y))

    return QRect(x, y, rect.width(), rect.height())


class ActionListContent(QFrame):
    """
    서버/직업 같은 목록 선택용 content
    PopupAction 리스트를 받아 버튼 목록을 생성
    """

    triggered = pyqtSignal(str)

    def __init__(
        self,
        actions: list[PopupAction],
    ) -> None:
        super().__init__()

        self.setFixedWidth(130)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self.setStyleSheet(
            """
            QFrame { background-color: transparent; }
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


class InputConfirmContent(QFrame):
    """라인에딧 & 확인 버튼 형태의 팝업"""

    submitted = pyqtSignal(str)

    def __init__(
        self,
        default_text: str,
        fixed_width: int = 170,
    ) -> None:
        super().__init__()

        self.setFixedWidth(fixed_width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.setStyleSheet("QFrame { background-color: transparent; }")

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


class KeyCaptureContent(QFrame):
    """QLabel & 확인 버튼 형태의 시작키 입력 팝업"""

    submitted = pyqtSignal(object)  # KeySpec | None
    _key_received = pyqtSignal(object)

    def __init__(
        self,
        default_key: KeySpec | None = None,
    ) -> None:
        super().__init__()

        self.setFixedWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("QFrame { background-color: transparent; }")

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
        self._label.setText(str(key))

    def _emit_submit(self) -> None:
        self.submitted.emit(self._current_key)


class PopupHost(QDialog):
    """공통 팝업 창 호스트"""

    closed = pyqtSignal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        # 팝업 창 설정
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        # 배경 투명화
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        # 포커스를 잃으면 자동으로 닫히도록 설정
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

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

        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)

        # 그림자가 잘리는 것을 방지하기 위한 외부 레이아웃
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 20)
        root.addWidget(self._container)

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

    def show_for(self, anchor: QWidget, options: PopupOptions) -> None:
        """팝업 표시"""

        # 내용이 설정되지 않은 경우 예외
        if self._content is None:
            raise RuntimeError("PopupHost.show_for() called without content")

        # 크기 조정
        self._container.adjustSize()
        self.adjustSize()

        # 앵커 위치 계산
        anchor_top_left: QPoint = anchor.mapToGlobal(QPoint(0, 0))
        anchor_rect = QRect(anchor_top_left, anchor.size())

        # 팝업 크기 계산
        popup_size: QSize = self.sizeHint()
        w: int = popup_size.width()
        h: int = popup_size.height()

        # 배치 계산
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

        # 화면 경계 내로 위치 보정
        screen: QScreen | None = QGuiApplication.screenAt(anchor_rect.center())
        if screen is None:
            screen = QGuiApplication.primaryScreen()

        screen_rect: QRect = (
            screen.availableGeometry()
            if screen is not None
            else QRect(0, 0, 1920, 1080)
        )

        desired = QRect(x, y, w, h)

        # 보정된 위치 계산
        fitted: QRect = _get_fit_position(desired, screen_rect, options.screen_margin)

        # 팝업 위치 설정
        self.move(fitted.topLeft())

        # 팝업 표시 및 포커스 설정
        self.show()
        self.raise_()
        self.activateWindow()

        # 포커스를 팝업으로 가져와서 클릭 외부 감지
        self.setFocus()

    def eventFilter(self, obj, event: QEvent) -> bool:  # type: ignore
        """부모 위젯의 스크롤 이벤트를 감지"""

        # 스크롤 이벤트 감지
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
        self.closed.emit()
        super().closeEvent(a0)


class PopupController:
    """PopupHost를 재사용하며 content 교체로 팝업을 표시"""

    def __init__(self, parent: QWidget) -> None:
        self._host = PopupHost(parent)
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
        self._host.show_for(anchor, options)

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
        self._host.show_for(anchor, options)

    def _on_triggered(self, action_id: str) -> None:
        """액션 선택시 호출"""

        act: PopupAction = self._actions_by_id[action_id]
        self.close()

        if act.on_trigger is not None:
            act.on_trigger()


class PopupManager:
    """
    팝업을 관리하는 클래스
    """

    def __init__(self, master: MainWindow) -> None:
        self.master: MainWindow = master

        self._popup_controller: PopupController = PopupController(parent=self.master)
        self._popup_controller.host.closed.connect(self._on_popup_host_closed)
        self._active_popup: PopupKind | None = None

        # 시작키 입력 리스너(pynput)
        self._key_listener: pynput_keyboard.Listener | None = None

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

    ## 알림 창 생성
    # pyqtSignal을 이용하도록 수정
    def make_notice_popup(self, e: str) -> None:
        """
        MacroIsRunning: 매크로 작동중
        editingLinkSkill: 연계스킬 수정중
        skillNotSelected: 연계스킬에 장착중이지 않은 스킬이 포함되어있음
        autoAlreadyExist: 이미 자동으로 사용중인 스킬이 포함되어있음
        exceedMaxLinkSkill: 연계스킬이 너무 많이 사용되어 연계가 정상적으로 작동하지 않을 수 있음
        delayInputError: 딜레이 입력 오류
        cooltimeInputError: 쿨타임 입력 오류
        StartKeyChangeError: 시작키 변경 오류
        RequireUpdate: 업데이트 필요
        FailedUpdateCheck: 업데이트 확인 실패
        SimInputError: 시뮬레이션 정보 입력 오류
        SimCharLoadError: 캐릭터 데이터 불러오기 실패
        SimCardError: 카드 생성 오류
        SimCardPowerError: 카드 전투력 선택 안함
        SimCardNotUpdated: 카드 정보 업데이트 필요

        str에서 클래스로 바꾸는 것도 고려
        """

        noticePopup = QFrame(self.master)

        frameHeight = 78
        match e:
            case "MacroIsRunning":
                text = "매크로가 작동중이기 때문에 수정할 수 없습니다."
                icon = "error"

            case "editingLinkSkill":
                text = "연계스킬을 수정중이기 때문에 장착스킬을 변경할 수 없습니다."
                icon = "error"

            case "skillNotSelected":
                text = "해당 연계스킬에 장착중이지 않은 스킬이 포함되어있습니다."
                icon = "error"

            case "autoAlreadyExist":
                text = "해당 연계스킬에 이미 자동으로 사용중인 스킬이 포함되어있습니다."
                icon = "error"

            case "exceedMaxLinkSkill":
                text = "해당 스킬이 너무 많이 사용되어 연계가 정상적으로 작동하지 않을 수 있습니다."
                icon = "warning"

            case "delayInputError":
                text = f"딜레이는 {config.specs.DELAY.min}~{config.specs.DELAY.max}까지의 수를 입력해야 합니다."
                icon = "error"

            case "cooltimeInputError":
                text = f"쿨타임은 {config.specs.COOLTIME_REDUCTION.min}~{config.specs.COOLTIME_REDUCTION.max}까지의 수를 입력해야 합니다."
                icon = "error"

            case "StartKeyChangeError":
                text = "해당 키는 이미 사용중입니다."
                icon = "error"

            case "RequireUpdate":
                text = f"프로그램이 최신버전이 아닙니다.\n현재 버전: {config.version}, 최신버전: {app_state.ui.current_version}"
                icon = "warning"

                button = QPushButton("다운로드 링크", noticePopup)
                button.setFont(CustomFont(12))
                button.setStyleSheet(
                    """
                                QPushButton {
                                    background-color: #86A7FC; border-radius: 4px;
                                }
                                QPushButton:hover {
                                    background-color: #6498f0;
                                }
                            """
                )
                button.setFixedSize(150, 32)
                button.move(48, 86)
                button.clicked.connect(lambda: open_new(app_state.ui.update_url))
                button.show()

                frameHeight = 134

            case "FailedUpdateCheck":
                text = f"프로그램 업데이트 확인에 실패하였습니다."
                icon = "warning"

            case "SimInputError":
                text = f"시뮬레이션 정보가 올바르게 입력되지 않았습니다."
                icon = "error"

            case "SimCharLoadError":
                text = f"캐릭터를 불러올 수 없습니다. 닉네임을 확인해주세요."
                icon = "error"

            case "SimCardError":
                text = f"카드를 생성할 수 없습니다. 닉네임과 캐릭터를 확인해주세요."
                icon = "error"

            case "SimCardPowerError":
                text = f"표시할 전투력 종류를 선택해주세요."
                icon = "error"

            case "SimCardNotUpdated":
                text = f"캐릭터 정보를 입력하고 '입력완료' 버튼을 눌러주세요."
                icon = "error"

            case _:
                return

        count: int = len(app_state.ui.active_error_popups)

        noticePopup.setStyleSheet("background-color: white; border-radius: 10px;")
        noticePopup.setFixedSize(400, frameHeight)
        noticePopup.move(
            self.master.width() - 420,
            self.master.height() - frameHeight - 15 - count * 10,
        )
        noticePopup.setGraphicsEffect(CustomShadowEffect(0, 5, 30, 150))
        noticePopup.show()

        noticePopupIcon = QPushButton(noticePopup)
        noticePopupIcon.setStyleSheet("background-color: transparent;")
        noticePopupIcon.setFixedSize(24, 24)
        noticePopupIcon.move(13, 15)
        pixmap = QPixmap(convert_resource_path(f"resources\\image\\{icon}.png"))
        noticePopupIcon.setIcon(QIcon(pixmap))
        noticePopupIcon.setIconSize(QSize(24, 24))
        noticePopupIcon.show()

        noticePopupLabel = QLabel(text, noticePopup)
        noticePopupLabel.setWordWrap(True)
        noticePopupLabel.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        noticePopupLabel.setFont(CustomFont(12))
        noticePopupLabel.setStyleSheet("background-color: white; border-radius: 10px;")
        noticePopupLabel.setFixedSize(304, frameHeight - 24)
        noticePopupLabel.move(48, 12)
        noticePopupLabel.show()

        if e == "RequireUpdate":
            button.raise_()  # type: ignore

        noticePopupRemove = QPushButton(noticePopup)
        noticePopupRemove.setStyleSheet(
            """
                        QPushButton {
                            background-color: white; border-radius: 16px;
                        }
                        QPushButton:hover {
                            background-color: #dddddd;
                        }
                    """
        )
        noticePopupRemove.setFixedSize(32, 32)
        noticePopupRemove.move(355, 12)
        noticePopupRemove.clicked.connect(
            partial(
                lambda x: self.close_notice_popup(x),
                count,
            )
        )
        pixmap = QPixmap(convert_resource_path("resources\\image\\x.png"))
        noticePopupRemove.setIcon(QIcon(pixmap))
        noticePopupRemove.setIconSize(QSize(24, 24))
        noticePopupRemove.show()

        app_state.ui.active_error_popups.append((noticePopup, frameHeight, count))

    ## 알림 창 제거
    def close_notice_popup(self, num=-1) -> None:
        if num != -1:
            for i, j in enumerate(app_state.ui.active_error_popups):
                if num == j[2]:
                    j[0].deleteLater()  # type: ignore
                    app_state.ui.active_error_popups.pop(i)
        else:
            app_state.ui.active_error_popups[-1][0].deleteLater()  # type: ignore
            app_state.ui.active_error_popups.pop()

        self.update_position()

    def update_position(self) -> None:
        for i, j in enumerate(app_state.ui.active_error_popups):
            j[0].move(  # type: ignore
                self.master.width() - 420,
                self.master.height() - j[1] - 15 - i * 10,
            )
            for i in app_state.ui.active_error_popups:
                i[0].raise_()  # type: ignore

    def close_popup(self) -> None:
        # PopupHost 기반 팝업 닫기
        # self._stop_key_listener()
        self._popup_controller.close()
        # self._active_popup = None

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
            self.make_notice_popup("MacroIsRunning")
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
            self.make_notice_popup("MacroIsRunning")
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
            kind=PopupKind.SETTING_SERVER,
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
                self.make_notice_popup("delayInputError")
                return

            if not (config.specs.DELAY.min <= value <= config.specs.DELAY.max):
                self.make_notice_popup("delayInputError")
                return

            # 콜백 실행
            on_selected(value)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.SETTING_DELAY,
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
                self.make_notice_popup("cooltimeInputError")
                return

            if not (
                config.specs.COOLTIME_REDUCTION.min
                <= value
                <= config.specs.COOLTIME_REDUCTION.max
            ):
                self.make_notice_popup("cooltimeInputError")
                return

            # 콜백 실행
            on_selected(value)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.SETTING_COOLTIME,
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

        # 기존 팝업/리스너 정리
        if self._popup_controller.is_visible():
            self._popup_controller.close()

        self._stop_key_listener()

        default_key: KeySpec = app_state.macro.current_start_key

        content = KeyCaptureContent(default_key=default_key)

        def _submit(key: KeySpec | None) -> None:
            self.close_popup()

            # 변경 없음
            if key is None or key == default_key:
                return

            # 키가 이미 사용중인 경우
            if app_state.is_key_using(key):
                self.make_notice_popup("StartKeyChangeError")
                return

            on_selected(key)

        content.submitted.connect(_submit)

        self.make_input_popup(
            kind=PopupKind.SETTING_START_KEY,
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
        content = InputConfirmContent(default_text=default_text, fixed_width=200)

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
        index: int,
        on_selected: Callable[[KeySpec], None],
    ) -> None:
        """시작키 입력 팝업"""

        # 기존 팝업/리스너 정리
        if self._popup_controller.is_visible():
            self._popup_controller.close()

        self._stop_key_listener()

        default_key: KeySpec = KeyRegistry.get(
            app_state.macro.current_preset.skills.skill_keys[index]
        )
        content = KeyCaptureContent(default_key=default_key)

        def _submit(key: KeySpec) -> None:
            self.close_popup()

            # 변경 없음
            if key is None or key == default_key:
                return

            print(app_state.is_key_using(key))

            # 키가 이미 사용중인 경우
            if app_state.is_key_using(key):
                self.make_notice_popup("StartKeyChangeError")
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

        listener = pynput_keyboard.Listener(on_press=_on_press)
        listener.daemon = True
        listener.start()
        self._key_listener = listener
        app_state.ui.is_setting_key = True

    def make_link_skill_key_popup(
        self,
        anchor: QWidget,
        on_selected: Callable[[KeySpec], None],
    ) -> None:
        """연계스킬 키 입력 팝업"""
        # todo: 중복 코드 정리

        # 기존 팝업/리스너 정리
        if self._popup_controller.is_visible():
            self._popup_controller.close()

        self._stop_key_listener()

        content = KeyCaptureContent()

        def _submit(key: KeySpec | None) -> None:
            self.close_popup()

            if key is None:
                return

            # 키가 이미 사용중인 경우
            if app_state.is_key_using(key):
                self.make_notice_popup("StartKeyChangeError")
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
            self.make_notice_popup("MacroIsRunning")
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


class ConfirmRemovePopup(QFrame):
    """탭 삭제 확인 팝업 (사용되지 않음)"""

    def __init__(self, master: MainUI, tab_name: str, tab_index: int) -> None:
        # QFrame의 부모를 master(MainUI)의 master(MainWindow)로 설정
        super().__init__(master.master)

        self.setStyleSheet("QFrame { background-color: rgba(0, 0, 0, 100); }")

        self.master: MainUI = master
        self.tab_index: int = tab_index

        popup_frame = QFrame(self)
        popup_frame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 20px; }"
        )
        popup_frame.setGraphicsEffect(CustomShadowEffect(2, 2, 20))

        name = QLabel("", popup_frame)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setFont(CustomFont(12))
        name.setText(f'정말 "{tab_name}"\n 탭을 삭제하시겠습니까?')

        yes_button = QPushButton("예", popup_frame)
        yes_button.setFont(CustomFont(12))
        yes_button.clicked.connect(self.on_yes_clicked)
        yes_button.setStyleSheet(
            """
                QPushButton {
                    background-color: #86A7FC; border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #6498f0;
                }
            """
        )
        yes_button.setGraphicsEffect(CustomShadowEffect(2, 2, 20))

        no_button = QPushButton("아니오", popup_frame)
        no_button.setFont(CustomFont(12))
        no_button.clicked.connect(self.on_no_clicked)
        no_button.setStyleSheet(
            """
                QPushButton {
                    background-color: #ffffff; border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #eeeeee;
                }
            """
        )
        no_button.setGraphicsEffect(CustomShadowEffect(2, 2, 20))

        layout = QGridLayout(popup_frame)
        layout.addWidget(name, 0, 0, 1, 2)
        layout.addWidget(yes_button, 1, 0)
        layout.addWidget(no_button, 1, 1)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        popup_frame.setLayout(layout)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(popup_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def on_yes_clicked(self) -> None:
        self.master.on_remove_tab_popup_clicked(
            index=self.tab_index,
            confirmed=True,
        )

    def on_no_clicked(self) -> None:
        self.master.on_remove_tab_popup_clicked(
            index=self.tab_index,
            confirmed=False,
        )
