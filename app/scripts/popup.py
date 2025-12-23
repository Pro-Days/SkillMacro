from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from typing import TYPE_CHECKING, Callable
from webbrowser import open_new

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
from PyQt6.QtGui import QGuiApplication, QIcon, QPixmap, QTransform
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, CustomShadowEffect
from app.scripts.data_manager import save_data
from app.scripts.misc import (
    adjust_font_size,
    convert_resource_path,
    get_available_skills,
    get_every_skills,
    get_skill_details,
    get_skill_pixmap,
    is_key_used,
    set_var_to_ClassVar,
)

if TYPE_CHECKING:
    from app.scripts.main_window import MainWindow
    from app.scripts.shared_data import SharedData
    from app.scripts.ui.main_ui.main_ui import MainUI


class PopupPlacement(Enum):
    """Anchor 기준 팝업을 배치하는 방향"""

    BELOW_LEFT = auto()
    BELOW_RIGHT = auto()
    ABOVE_LEFT = auto()
    ABOVE_RIGHT = auto()


class PopupKind(str, Enum):
    """PopupHost 기반 팝업의 종류(오타 방지용)."""

    SETTING_SERVER = "settingServer"
    SETTING_JOB = "settingJob"


@dataclass(frozen=True)
class PopupOptions:
    """팝업의 표시 옵션"""

    placement: PopupPlacement = PopupPlacement.BELOW_LEFT
    margin: int = 6
    screen_margin: int = 8


@dataclass(frozen=True)
class PopupAction:
    """
    팝업 내의 선택지 하나를 나타냄
    예: "한월 RPG"
    """

    id: str
    text: str
    enabled: bool = True
    is_selected: bool = False
    on_trigger: Callable[[], None] | None = None


def _clamp_rect_to_screen(rect: QRect, screen_rect: QRect, margin: int) -> QRect:
    """팝업이 화면 밖으로 나가지 않도록 위치 보정"""

    x = rect.x()
    y = rect.y()

    min_x = screen_rect.left() + margin
    max_x = screen_rect.right() - margin - rect.width() + 1
    min_y = screen_rect.top() + margin
    max_y = screen_rect.bottom() - margin - rect.height() + 1

    if x < min_x:
        x = min_x
    elif x > max_x:
        x = max_x

    if y < min_y:
        y = min_y
    elif y > max_y:
        y = max_y

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
        fixed_width: int = 130,
    ) -> None:
        super().__init__()

        # Content(=PopupHost 안의 내용물) 폭을 명확히 고정해
        # 스크롤바 오른쪽(또는 스크롤바가 없을 때도) 불필요한 빈 공간이 생기지 않게 한다.
        self.setFixedWidth(fixed_width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self.setStyleSheet(
            """
            QFrame { background-color: white; }
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

        # 스크롤바 없이 전체 항목을 나열한다.
        v = QVBoxLayout(self)
        v.setContentsMargins(5, 5, 5, 5)
        v.setSpacing(5)

        row_height = 30
        for act in actions:
            btn = QPushButton(act.text, self)
            btn.setFont(CustomFont(12))
            btn.setEnabled(act.enabled)

            # 폭은 컨테이너에 맞춰 자동으로 늘어나게 한다.
            btn.setFixedHeight(row_height)
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            btn.setProperty("selected", act.is_selected)
            btn.clicked.connect(lambda _, act_id=act.id: self.triggered.emit(act_id))

            v.addWidget(btn)


class PopupHost(QDialog):
    """공통 팝업 껍데기: 배치/클릭-아웃/ESC/그림자 등을 일원화."""

    closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Popup 대신 Tool 윈도우 사용 (일반 윈도우 렌더링 사용)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # 포커스를 잃으면 자동으로 닫히도록 설정
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._container = QFrame(self)
        self._container.setStyleSheet(
            "QFrame { background-color: white; border-radius: 10px; }"
        )
        self._container.setGraphicsEffect(CustomShadowEffect(0, 5, 30, 150))

        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._container)

        self._content: QWidget | None = None

        # 스크롤 이벤트를 감지하기 위한 이벤트 필터 설치
        app: QCoreApplication | None = QGuiApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def set_content(self, content: QWidget) -> None:
        if self._content is not None:
            self._container_layout.removeWidget(self._content)
            self._content.setParent(None)

        self._content = content
        content.setParent(self._container)
        self._container_layout.addWidget(content)

    def show_for(self, anchor: QWidget, options: PopupOptions = PopupOptions()) -> None:
        if self._content is None:
            raise RuntimeError("PopupHost.show_for() called without content")

        self._container.adjustSize()
        self.adjustSize()

        anchor_top_left = anchor.mapToGlobal(QPoint(0, 0))
        anchor_rect = QRect(anchor_top_left, anchor.size())

        popup_size = self.sizeHint()
        w, h = popup_size.width(), popup_size.height()

        # 배치 계산
        if options.placement == PopupPlacement.BELOW_LEFT:
            x = anchor_rect.left()
            y = anchor_rect.bottom() + options.margin
        elif options.placement == PopupPlacement.BELOW_RIGHT:
            x = anchor_rect.right() - w + 1
            y = anchor_rect.bottom() + options.margin
        elif options.placement == PopupPlacement.ABOVE_LEFT:
            x = anchor_rect.left()
            y = anchor_rect.top() - h - options.margin
        else:  # ABOVE_RIGHT
            x = anchor_rect.right() - w + 1
            y = anchor_rect.top() - h - options.margin

        desired = QRect(x, y, w, h)

        screen = QGuiApplication.screenAt(anchor_rect.center())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        screen_rect = (
            screen.availableGeometry()
            if screen is not None
            else QRect(0, 0, 1920, 1080)
        )

        clamped = _clamp_rect_to_screen(desired, screen_rect, options.screen_margin)
        self.move(clamped.topLeft())

        self.show()
        self.raise_()
        self.activateWindow()

        # 포커스를 팝업으로 가져와서 클릭 외부 감지
        self.setFocus()

    def eventFilter(self, obj, event: QEvent) -> bool:  # type: ignore
        """부모 위젯의 이벤트를 감지 (스크롤 등)"""

        # 스크롤 이벤트 감지
        if self.isVisible() and event.type() == QEvent.Type.Wheel:
            # 휠 이벤트는 원래 대상 위젯으로 계속 전달되게 두고,
            # 팝업만 닫아 UX를 자연스럽게 만든다.
            self.close()
            return False

        return super().eventFilter(obj, event)

    def focusOutEvent(self, a0) -> None:
        """
        포커스를 잃으면 클릭 이벤트가 처리되기 위해
        약간의 지연을 두고 팝업 닫기
        """

        QTimer.singleShot(1, self.close)
        super().focusOutEvent(a0)

    def closeEvent(self, a0):
        self.closed.emit()
        super().closeEvent(a0)


class PopupController:
    """단일 PopupHost를 재사용하며 content 교체로 팝업을 표시한다."""

    def __init__(self, parent: QWidget | None = None) -> None:
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
        options: PopupOptions = PopupOptions(),
    ) -> None:
        self._actions_by_id = {a.id: a for a in actions}

        content = ActionListContent(actions)
        content.triggered.connect(self._on_triggered)

        self._host.set_content(content)
        self._host.show_for(anchor, options)

    def _on_triggered(self, action_id: str) -> None:
        act = self._actions_by_id.get(action_id)
        self.close()

        if act is None:
            return
        if act.on_trigger is not None:
            act.on_trigger()


class PopupManager:
    """
    팝업을 관리하는 클래스
    """

    def __init__(
        self,
        master: MainWindow,
        shared_data: SharedData,
    ):
        self.master: MainWindow = master
        self.shared_data: SharedData = shared_data

        self._popup_controller: PopupController = PopupController(parent=self.master)
        self._popup_controller.host.closed.connect(self._on_popup_host_closed)
        self._active_popup: PopupKind | None = None

    def _on_popup_host_closed(self) -> None:
        self._active_popup = None

    def is_popup_open(self, kind: PopupKind | None = None) -> bool:
        """특정 종류의 팝업이 열려있는지 확인"""

        if not self._popup_controller.is_visible():
            return False

        if kind is None:
            return True

        return self._active_popup == kind

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
                text = f"딜레이는 {self.shared_data.MIN_DELAY}~{self.shared_data.MAX_DELAY}까지의 수를 입력해야 합니다."
                icon = "error"

            case "cooltimeInputError":
                text = f"쿨타임은 {self.shared_data.MIN_COOLTIME_REDUCTION}~{self.shared_data.MAX_COOLTIME_REDUCTION}까지의 수를 입력해야 합니다."
                icon = "error"

            case "StartKeyChangeError":
                text = "해당 키는 이미 사용중입니다."
                icon = "error"

            case "RequireUpdate":
                text = f"프로그램이 최신버전이 아닙니다.\n현재 버전: {self.shared_data.VERSION}, 최신버전: {self.shared_data.recent_version}"
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
                button.clicked.connect(lambda: open_new(self.shared_data.update_url))
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

        noticePopup.setStyleSheet("background-color: white; border-radius: 10px;")
        noticePopup.setFixedSize(400, frameHeight)
        noticePopup.move(
            self.master.width() - 420,
            self.master.height()
            - frameHeight
            - 15
            - self.shared_data.active_error_popup_count * 10,
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
                self.shared_data.active_error_popup_count,
            )
        )
        pixmap = QPixmap(convert_resource_path("resources\\image\\x.png"))
        noticePopupRemove.setIcon(QIcon(pixmap))
        noticePopupRemove.setIconSize(QSize(24, 24))
        noticePopupRemove.show()

        self.shared_data.active_error_popup.append(
            [noticePopup, frameHeight, self.shared_data.active_error_popup_count]
        )
        self.shared_data.active_error_popup_count += 1

    ## 알림 창 제거
    def close_notice_popup(self, num=-1):
        if num != -1:
            for i, j in enumerate(self.shared_data.active_error_popup):
                if num == j[2]:
                    j[0].deleteLater()
                    self.shared_data.active_error_popup.pop(i)
        else:
            self.shared_data.active_error_popup[-1][0].deleteLater()
            self.shared_data.active_error_popup.pop()
        # self.activeErrorPopup[num][0].deleteLater()
        # self.activeErrorPopup.pop(0)
        self.shared_data.active_error_popup_count -= 1
        self.update_position()

    ## 인풋 팝업 생성
    def makePopupInput(self, popup_type: str, var: int | None = None) -> None:
        match popup_type:
            case "delay":
                x = 140
                y = 370
                width = 140

                frame = self.master.get_sidebar().frame

            case "cooltime":
                x = 140
                y = 500
                width = 140

                frame = self.master.get_sidebar().frame

            case "tabName":
                x = 360 + 200 * self.shared_data.recent_preset
                y = 80
                width = 200

                frame = self.master

            case _:
                return

        self.settingPopupFrame = QFrame(frame)
        self.settingPopupFrame.setStyleSheet(
            "background-color: white; border-radius: 10px;"
        )
        self.settingPopupFrame.setFixedSize(width, 40)
        self.settingPopupFrame.move(x, y)
        self.settingPopupFrame.setGraphicsEffect(CustomShadowEffect(0, 0, 30, 150))
        self.settingPopupFrame.show()

        match popup_type:
            case "delay":
                default = str(self.shared_data.delay_input)

            case "cooltime":
                default = str(self.shared_data.cooltime_reduction_input)

            case "tabName":
                default = self.shared_data.tab_names[self.shared_data.recent_preset]

        self.settingPopupInput = QLineEdit(default, self.settingPopupFrame)
        self.settingPopupInput.setFont(CustomFont(12))
        self.settingPopupInput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.settingPopupInput.setStyleSheet(
            "border: 1px solid black; border-radius: 10px;"
        )
        self.settingPopupInput.setFixedSize(width - 70, 30)
        self.settingPopupInput.move(5, 5)
        self.settingPopupInput.setFocus()

        self.settingPopupButton = QPushButton("적용", self.settingPopupFrame)
        self.settingPopupButton.setFont(CustomFont(12))
        self.settingPopupButton.clicked.connect(
            lambda: self.on_input_popup_clicked(popup_type, var)
        )
        self.settingPopupButton.setStyleSheet(
            """
                            QPushButton {
                                background-color: "white"; border-radius: 10px; border: 1px solid black;
                            }
                            QPushButton:hover {
                                background-color: #cccccc;
                            }
                        """
        )
        self.settingPopupButton.setFixedSize(50, 30)
        self.settingPopupButton.move(width - 60, 5)
        # self.settingServerFrame.setGraphicsEffect(CustomShadowEffect(0, 5))

        self.settingPopupButton.show()
        self.settingPopupInput.show()

        # self.update()
        self.update_position()

    ## 인풋 팝업 확인 클릭시 실행
    def on_input_popup_clicked(self, input_type: str, var: int | None = None) -> None:
        text = self.settingPopupInput.text()

        match input_type:
            case "delay":
                try:
                    text = int(text)

                except:
                    self.close_popup()
                    self.make_notice_popup("delayInputError")
                    return

                if not (
                    self.shared_data.MIN_DELAY <= text <= self.shared_data.MAX_DELAY
                ):
                    self.close_popup()
                    self.make_notice_popup("delayInputError")
                    return

                self.master.get_sidebar().buttonInputDelay.setText(str(text))
                self.shared_data.delay_input = text
                self.shared_data.delay = text

            case "cooltime":
                try:
                    text = int(text)

                except Exception:
                    self.close_popup()
                    self.make_notice_popup("cooltimeInputError")
                    return

                if not (
                    self.shared_data.MIN_COOLTIME_REDUCTION
                    <= text
                    <= self.shared_data.MAX_COOLTIME_REDUCTION
                ):
                    self.close_popup()
                    self.make_notice_popup("cooltimeInputError")
                    return

                self.master.get_sidebar().buttonInputCooltime.setText(str(text))
                self.shared_data.cooltime_reduction_input = text
                self.shared_data.cooltime_reduction = text

            case "tabName":
                if var is None:
                    self.close_popup()
                    return

                # self.master.get_main_ui().tab_buttons[var].setText(
                #     adjust_text_length(
                #         " " + text, self.master.get_main_ui().tab_buttons[var]
                #     )
                # )
                self.shared_data.tab_names[var] = text

        save_data(self.shared_data)
        self.close_popup()

        # self.update()
        self.update_position()

    ## 가상키보드 생성
    def makeKeyboardPopup(self, kb_type):
        def makePresetKey(key, row, column, disabled=False):
            button = QPushButton(key, self.settingPopupFrame)
            match kb_type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, kb_type[1]
                        )
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(
                            key, disabled, kb_type[1]
                        )
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 5px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(30, 30)
            match column:
                case 0:
                    defaultX = 115
                case 1:
                    defaultX = 5
                case 2:
                    defaultX = 50
                case 3:
                    defaultX = 60
                case 4:
                    defaultX = 80
                case _:
                    return

            defaultY = 5

            adjust_font_size(button, key, 20)
            button.move(
                defaultX + row * 35,
                defaultY + column * 35,
            )
            button.show()

        def makeKey(key, x, y, width, height, disabled=False):
            button = QPushButton(key, self.settingPopupFrame)
            match kb_type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, kb_type[1]
                        )
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(
                            key, disabled, kb_type[1]
                        )
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 5px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(width, height)
            adjust_font_size(button, key, 20)
            button.move(x, y)
            button.show()

        def makeImageKey(key, x, y, width, height, image, size, rot, disabled=False):
            button = QPushButton(self.settingPopupFrame)
            pixmap = QPixmap(image)
            pixmap = pixmap.transformed(QTransform().rotate(rot))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(size, size))
            match kb_type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, kb_type[1]
                        )
                    )
                case ("LinkSkill", _):
                    button.clicked.connect(
                        lambda: self.onLinkSkillKeyPopupKeyboardClick(
                            key, disabled, kb_type[1]
                        )
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 5px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(width, height)
            button.move(x, y)
            button.show()

        self.settingPopupFrame = QFrame(self.master)
        self.settingPopupFrame.setStyleSheet(
            "background-color: white; border-radius: 10px;"
        )
        self.settingPopupFrame.setFixedSize(635, 215)
        self.settingPopupFrame.move(30, 30)
        self.settingPopupFrame.setGraphicsEffect(CustomShadowEffect(0, 0, 30, 150))
        self.settingPopupFrame.show()

        k0 = [
            "Esc",
            "F1",
            "F2",
            "F3",
            "F4",
            "F5",
            "F6",
            "F7",
            "F8",
            "F9",
            "F10",
            "F11",
            "F12",
        ]
        k1 = ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]
        k2 = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"]
        k3 = ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'"]
        k4 = ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"]

        for i, key in enumerate(k0):
            x = 5 + 35 * i
            if i >= 1:
                x += 15
            if i >= 5:
                x += 15
            if i >= 9:
                x += 15

            if key == "Esc":
                makeKey(
                    key,
                    x,
                    5,
                    30,
                    30,
                    True,
                )
            else:
                makeKey(
                    key,
                    x,
                    5,
                    30,
                    30,
                    is_key_used(self.shared_data, key),
                )

        row = 0
        column = 1
        for key in k1:
            makePresetKey(key, row, column, is_key_used(self.shared_data, key))
            row += 1
        makeKey(
            "Back",
            460,
            40,
            40,
            30,
            True,
        )

        makeKey(
            "Tab",
            5,
            75,
            40,
            30,
            is_key_used(self.shared_data, "Tab"),
        )
        row = 0
        column += 1
        for key in k2:
            makePresetKey(key, row, column, is_key_used(self.shared_data, key))
            row += 1

        makeKey(
            "Caps Lock",
            5,
            110,
            50,
            30,
            True,
        )
        row = 0
        column += 1
        for key in k3:
            makePresetKey(key, row, column, is_key_used(self.shared_data, key))
            row += 1
        makeKey(
            "Enter",
            445,
            110,
            55,
            30,
            is_key_used(self.shared_data, "Enter"),
        )

        makeKey(
            "Shift",
            5,
            145,
            70,
            30,
            is_key_used(self.shared_data, "Shift"),
        )
        row = 0
        column += 1
        for key in k4:
            makePresetKey(key, row, column, is_key_used(self.shared_data, key))
            row += 1
        makeKey(
            "Shift",
            430,
            145,
            70,
            30,
            is_key_used(self.shared_data, "Shift"),
        )

        makeKey(
            "Ctrl",
            5,
            180,
            45,
            30,
            is_key_used(self.shared_data, "Ctrl"),
        )
        makeImageKey(
            "Window",
            55,
            180,
            45,
            30,
            convert_resource_path("resources\\image\\window.png"),
            32,
            0,
            True,
        )
        makeKey(
            "Alt",
            105,
            180,
            45,
            30,
            is_key_used(self.shared_data, "Alt"),
        )
        makeKey(
            "Space",
            155,
            180,
            145,
            30,
            is_key_used(self.shared_data, "Space"),
        )
        makeKey(
            "Alt",
            305,
            180,
            45,
            30,
            is_key_used(self.shared_data, "Alt"),
        )
        makeImageKey(
            "Window",
            355,
            180,
            45,
            30,
            convert_resource_path("resources\\image\\window.png"),
            32,
            0,
            True,
        )
        makeKey(
            "Fn",
            405,
            180,
            45,
            30,
            True,
        )
        makeKey(
            "Ctrl",
            455,
            180,
            45,
            30,
            is_key_used(self.shared_data, "Ctrl"),
        )

        k5 = [
            ["PrtSc", "ScrLk", "Pause"],
            ["Insert", "Home", """Page\nUp"""],
            ["Delete", "End", "Page\nDown"],
        ]
        for i1, i2 in enumerate(k5):
            for j1, j2 in enumerate(i2):
                makeKey(
                    j2,
                    530 + j1 * 35,
                    5 + 35 * i1,
                    30,
                    30,
                    is_key_used(self.shared_data, j2),
                )

        makeImageKey(
            "Up",
            565,
            145,
            30,
            30,
            convert_resource_path("resources\\image\\arrow.png"),
            16,
            0,
            is_key_used(self.shared_data, "Up"),
        )
        makeImageKey(
            "Left",
            530,
            180,
            30,
            30,
            convert_resource_path("resources\\image\\arrow.png"),
            16,
            270,
            is_key_used(self.shared_data, "Left"),
        )
        makeImageKey(
            "Down",
            565,
            180,
            30,
            30,
            convert_resource_path("resources\\image\\arrow.png"),
            16,
            180,
            is_key_used(self.shared_data, "Down"),
        )
        makeImageKey(
            "Right",
            600,
            180,
            30,
            30,
            convert_resource_path("resources\\image\\arrow.png"),
            16,
            90,
            is_key_used(self.shared_data, "Right"),
        )

    ## 시작키 설정용 가상키보드 키 클릭시 실행
    def onStartKeyPopupKeyboardClick(self, key, disabled):
        if self.shared_data.is_activated:
            self.close_popup()
            self.make_notice_popup("MacroIsRunning")
            return

        match key:
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        self.master.get_sidebar().buttonInputStartKey.setText(key)
        self.shared_data.start_key_input = key
        self.shared_data.start_key = key

        save_data(self.shared_data)
        self.close_popup()

    ## 링크스킬 단축키용 가상키보드 키 클릭시 실행
    def onLinkSkillKeyPopupKeyboardClick(self, key, disabled, data):
        if self.shared_data.is_activated:
            self.close_popup()
            self.make_notice_popup("MacroIsRunning")
            return

        match key:
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        self.close_popup()

        data["key"] = key
        data["keyType"] = 1
        self.master.get_sidebar().reload_sidebar4(data)

    ## 스킬 단축키용 가상키보드 키 클릭시 실행
    def onSkillKeyPopupKeyboardClick(self, key, disabled, num):
        if self.shared_data.is_activated:
            self.close_popup()
            self.make_notice_popup("MacroIsRunning")
            return

        match key:
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        # self.master.get_main_ui().equipped_skill_keys[num].setText(key)
        # adjust_font_size(self.master.get_main_ui().equipped_skill_keys[num], key, 24)
        self.shared_data.skill_keys[num] = key

        save_data(self.shared_data)
        self.close_popup()

    def update_position(self):
        for i, j in enumerate(self.shared_data.active_error_popup):
            j[0].move(
                self.master.width() - 420,
                self.master.height() - j[1] - 15 - i * 10,
            )
            for i in self.shared_data.active_error_popup:
                i[0].raise_()

    def close_popup(self):
        pass

    def make_popup(
        self,
        kind: PopupKind,
        anchor: QWidget,
        actions: list[PopupAction],
        placement: PopupPlacement,
    ) -> None:
        """팝업 생성 공통 부분"""

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.make_notice_popup("MacroIsRunning")
            return

        self._active_popup = kind

        self._popup_controller.show_action_list(
            anchor=anchor,
            actions=actions,
            options=PopupOptions(placement=placement),
        )

    def make_server_popup(
        self,
        anchor: QWidget,
        on_selected: Callable[[str], None],
    ) -> None:
        """서버 선택 팝업"""

        current_server: str = self.shared_data.server_ID

        actions: list[PopupAction] = [
            PopupAction(
                id=server_name,
                text=server_name,
                enabled=True,
                is_selected=(server_name == current_server),
                on_trigger=lambda s=server_name: on_selected(s),
            )
            for server_name in self.shared_data.SERVERS
        ]

        self.make_popup(
            kind=PopupKind.SETTING_SERVER,
            anchor=anchor,
            actions=actions,
            placement=PopupPlacement.BELOW_LEFT,
        )

    def make_job_popup(
        self,
        anchor: QWidget,
        on_selected: Callable[[str], None],
    ) -> None:
        """직업 선택 팝업"""

        current_server: str = self.shared_data.server_ID
        jobs: list[str] = self.shared_data.JOBS[current_server]
        current_job: str = self.shared_data.job_ID

        actions: list[PopupAction] = [
            PopupAction(
                id=job_name,
                text=job_name,
                enabled=True,
                is_selected=(job_name == current_job),
                on_trigger=lambda j=job_name: on_selected(j),
            )
            for job_name in jobs
        ]

        self.make_popup(
            kind=PopupKind.SETTING_JOB,
            anchor=anchor,
            actions=actions,
            placement=PopupPlacement.BELOW_LEFT,
        )

    ## 사이드바 직업 목록 팝업창 클릭시 실행
    def onJobPopupClick(self, num):
        job_name = self.shared_data.JOBS[self.shared_data.server_ID][num]

        if self.shared_data.job_ID != job_name:
            self.shared_data.job_ID = job_name

            for i in range(len(self.shared_data.equipped_skills)):
                self.shared_data.equipped_skills[i] = ""

            set_var_to_ClassVar(
                self.shared_data.skill_priority,
                {i: 0 for i in get_every_skills(self.shared_data)},
            )
            self.shared_data.link_skills.clear()

            self.master.sidebar.buttonJobList.setText(job_name)

            for skill in get_available_skills(self.shared_data):
                self.shared_data.combo_count[skill] = get_skill_details(
                    self.shared_data, skill
                )["max_combo_count"]

            for i in range(8):
                self.master.get_main_ui().equippable_skill_buttons[i].setIcon(
                    QIcon(
                        get_skill_pixmap(
                            self.shared_data, get_available_skills(self.shared_data)[i]
                        )
                    )
                )
                self.master.get_main_ui().equippable_skill_names[i].setText(
                    self.shared_data.skill_data[self.shared_data.server_ID]["jobs"][
                        self.shared_data.job_ID
                    ]["skills"][i]
                )

            for i in range(6):
                self.master.get_main_ui().equipped_skill_buttons[i].setIcon(
                    QIcon(
                        get_skill_pixmap(
                            self.shared_data, self.shared_data.equipped_skills[i]
                        )
                    )
                )

            self.master.get_main_ui().update_position()

            save_data(self.shared_data)
        self.close_popup()

    ## 스킬 사용설정 -> 콤보 횟수 클릭
    def onSkillComboCountsClick(self, num):
        skill_name = get_available_skills(self.shared_data)[num]

        combo = get_skill_details(self.shared_data, skill_name)["max_combo_count"]

        if self.shared_data.active_popup == "SkillComboCounts":
            self.close_popup()
            return

        self.close_popup()
        self.activatePopup("SkillComboCounts")

        self.settingPopupFrame = QFrame(self.master.get_sidebar().frame)
        self.settingPopupFrame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 5px; }"
        )
        width = 4 + 36 * combo
        self.settingPopupFrame.setFixedSize(width, 40)
        self.settingPopupFrame.move(170 - width, 206 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(CustomShadowEffect(0, 0, 30, 150))
        self.settingPopupFrame.show()

        for i in range(1, combo + 1):
            button = QPushButton(str(i), self.settingPopupFrame)
            button.clicked.connect(
                partial(lambda x: self.onSkillComboCountsPopupClick(x), (num, i))
            )
            button.setFont(CustomFont(12))
            button.setFixedSize(32, 32)
            button.move(36 * i - 32, 4)
            button.show()

    ## 콤보 횟수 팝업 버튼 클릭
    def onSkillComboCountsPopupClick(self, var):
        num, count = var

        skill_name = get_available_skills(self.shared_data)[num]

        self.shared_data.combo_count[skill_name] = count
        self.master.get_sidebar().settingSkillComboCounts[num].setText(
            f"{count} / {get_skill_details(
            self.shared_data, skill_name
        )["max_combo_count"]}"
        )

        save_data(self.shared_data)
        self.close_popup()

    def change_link_skill_type(self, var: tuple[dict, int]) -> None:
        """
        링크스킬 스킬 변경
        """

        data: dict = var[0]
        num: int = var[1]

        if self.shared_data.active_popup == "editLinkSkillType":
            self.close_popup()
            return

        self.activatePopup("editLinkSkillType")

        self.settingPopupFrame = QFrame(self.master.get_sidebar().frame)
        self.settingPopupFrame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 10px; }"
        )
        self.settingPopupFrame.setFixedSize(185, 95)
        self.settingPopupFrame.move(100, 285 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(CustomShadowEffect(0, 5, 30, 150))
        self.settingPopupFrame.show()

        for i in range(8):
            button = QPushButton("", self.settingPopupFrame)
            button.setIcon(
                QIcon(
                    get_skill_pixmap(self.shared_data, i)
                    if i in self.shared_data.equipped_skills
                    else get_skill_pixmap(
                        self.shared_data, get_available_skills(self.shared_data)[i], -2
                    )
                )
            )
            button.setIconSize(QSize(40, 40))
            button.clicked.connect(
                partial(
                    lambda x: self.master.get_sidebar().oneLinkSkillTypePopupClick(x),
                    (data, num, i),
                )
            )
            button.setFixedSize(40, 40)
            # button.setStyleSheet("background-color: transparent;")
            button.move(45 * (i % 4) + 5, 5 + (i // 4) * 45)

            button.show()

    ## 링크스킬 사용 횟수 설정
    def editLinkSkillCount(self, var):
        data, num = var

        if self.shared_data.active_popup == "editLinkSkillCount":
            self.close_popup()
            return
        self.activatePopup("editLinkSkillCount")

        count = get_skill_details(
            self.shared_data,
            data["skills"][num]["name"],
        )["max_combo_count"]

        self.settingPopupFrame = QFrame(self.master.get_sidebar().frame)
        self.settingPopupFrame.setStyleSheet(
            "QFrame { background-color: white; border-radius: 10px; }"
        )
        self.settingPopupFrame.setFixedSize(5 + 35 * count, 40)
        self.settingPopupFrame.move(200 - 35 * count, 285 + 51 * num)
        self.settingPopupFrame.setGraphicsEffect(CustomShadowEffect(0, 5, 30, 150))
        self.settingPopupFrame.show()

        for i in range(1, count + 1):
            button = QPushButton(str(i), self.settingPopupFrame)
            button.setFont(CustomFont(12))
            button.clicked.connect(
                partial(
                    lambda x: self.master.get_sidebar().onLinkSkillCountPopupClick(x),
                    (data, num, i),
                )
            )
            button.setFixedSize(30, 30)
            button.move(35 * i - 30, 5)

            button.show()


class ConfirmRemovePopup(QFrame):
    def __init__(self, master: MainUI, tab_name: str, tab_index: int):
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

    def on_yes_clicked(self):
        self.master.on_remove_tab_popup_clicked(
            index=self.tab_index,
            confirmed=True,
        )

    def on_no_clicked(self):
        self.master.on_remove_tab_popup_clicked(
            index=self.tab_index,
            confirmed=False,
        )
