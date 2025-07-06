from .data_manager import *
from .shared_data import *
from .run_macro import *
from .graph import *
from .get_character_data import *
from .misc import *
from .simulate_macro import *
from .simul_ui import *
from .main_ui import MainUI
from .sidebar import Sidebar
from .popup import *

import sys
import requests

from threading import Thread
from webbrowser import open_new

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QPen,
    QFont,
    QIcon,
    QColor,
    QPixmap,
    QPainter,
    QPalette,
    QKeyEvent,
)
from PyQt6.QtWidgets import (
    QFrame,
    QWidget,
    QPushButton,
    QApplication,
    QStackedLayout,
)


class MainWindow(QWidget):
    def __init__(self) -> None:
        """
        메인 윈도우 초기화
        """

        super().__init__()

        # 기본 폰트 설정
        set_default_fonts()

        # 자주 쓰는 변수 초기화
        self.shared_data: SharedData = SharedData()
        self.ui_var: UI_Variable = UI_Variable()

        # 프로그램 아이콘 설정
        self.setWindowIcon(
            QIcon(QPixmap(convertResourcePath("resources\\image\\icon.ico")))
        )

        # 매크로 데이터 불러오기
        data_update()
        data_load(shared_data=self.shared_data)

        # 프로그램 화면 설정
        self.init_UI()

        # 서브 쓰레드 활성화
        self.activate_thread()

    def activate_thread(self) -> None:
        """
        서브 쓰레드 활성화
        """

        # 키보드 입력 감지
        Thread(target=check_kb_pressed, args=[self.shared_data], daemon=True).start()

        # 스킬 미리보기 쓰레드
        self.preview_timer: QTimer = QTimer(self)
        self.preview_timer.singleShot(100, self.tick)  # type: ignore

        # 버전 확인 쓰레드
        if self.shared_data.IS_VERSION_CHECK_ENABLED:
            self.version_timer: QTimer = QTimer(self)
            self.version_timer.singleShot(100, self.version_check_thread)  # type: ignore

    def change_layout(self, num: int) -> None:
        """
        레이아웃 변경

        0: 메인 매크로
        1: 시뮬레이션
        2: 매크로 공유
        """

        # 레이아웃 변경
        self.window_layout.setCurrentIndex(num)
        self.shared_data.layout_type = num

        # self.update_position()

        # 페이지마다 세부 설정
        if num == 0:
            # self.sim_ui.remove_simul_widgets()

            # # 모든 위젯 삭제
            # [i.deleteLater() for i in self.page2.findChildren(QWidget)]

            # self.update_position()
            pass

        elif num == 1:
            self.sim_ui.make_simul_page1()

        elif num == 2:
            pass

    def keyPressEvent(self, e: QKeyEvent) -> None:  # type: ignore
        """
        키 입력 시 실행
        """

        # ESC
        if e.key() == Qt.Key.Key_Escape:
            if self.shared_data.is_tab_remove_popup_activated:
                self.main_ui.onTabRemovePopupClick(0, False)

            elif self.shared_data.active_error_popup_count >= 1:
                self.popup_manager.removeNoticePopup()

            elif self.shared_data.active_popup != "":
                self.popup_manager.disablePopup()

        # Ctrl
        elif e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if (
                e.key() == Qt.Key.Key_W
                and not self.shared_data.is_tab_remove_popup_activated
            ):
                self.main_ui.onTabRemoveClick(self.shared_data.recentPreset)

        # Enter
        elif e.key() == Qt.Key.Key_Return:
            if self.shared_data.is_tab_remove_popup_activated:
                self.main_ui.onTabRemovePopupClick(self.shared_data.recentPreset)

            elif self.shared_data.active_popup == "settingDelay":
                self.popup_manager.onInputPopupClick("delay")

            elif self.shared_data.active_popup == "settingCooltime":
                self.popup_manager.onInputPopupClick("cooltime")

            elif self.shared_data.active_popup == "changeTabName":
                self.popup_manager.onInputPopupClick(
                    ("tabName", self.shared_data.recentPreset)
                )

        # 테스트 용 키입력
        # elif e.key() == Qt.Key.Key_L:
        #     print(self.getSimulatedSKillList())

    def version_check_thread(self) -> None:
        """
        최신버전 확인 쓰레드
        """

        try:
            response: requests.Response = requests.get(
                "https://api.github.com/repos/pro-days/skillmacro/releases/latest"
            )

            if response.status_code == 200:
                self.shared_data.recent_version = response.json()["name"]
                self.shared_data.update_url = response.json()["html_url"]

            else:
                self.shared_data.recent_version = "FailedUpdateCheck"
                self.shared_data.update_url = ""

        except:
            self.shared_data.recent_version = "FailedUpdateCheck"
            self.shared_data.update_url = ""

        if self.shared_data.recent_version == "FailedUpdateCheck":
            self.popup_manager.make_notice_popup("FailedUpdateCheck")

        elif self.shared_data.recent_version != self.shared_data.VERSION:
            self.popup_manager.make_notice_popup("RequireUpdate")

    def init_UI(self) -> None:
        """
        프로그램 처음 UI 설정
        """

        self.setWindowTitle("데이즈 스킬매크로 " + self.shared_data.VERSION)
        self.setMinimumSize(
            self.ui_var.DEFAULT_WINDOW_WIDTH,
            self.ui_var.DEFAULT_WINDOW_HEIGHT,
        )
        # self.setGeometry(0, 0, 960, 540)

        self.setStyleSheet("*:focus { outline: none; }")  # 포커스 시 테두리 제거

        self.back_palette: QPalette = self.palette()
        self.back_palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        self.setPalette(self.back_palette)

        self.page1: QFrame = QFrame(self)
        self.page2: QFrame = QFrame(self)

        self.creator_label: QPushButton = QPushButton(
            "  제작자: 프로데이즈  |  디스코드: prodays", self
        )
        self.creator_label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.creator_label.setStyleSheet(
            "QPushButton { background-color: transparent; text-align: left; border: 0px; }"
        )
        self.creator_label.clicked.connect(
            lambda: open_new("https://github.com/Pro-Days")
        )
        self.creator_label.setFixedSize(320, 24)
        self.creator_label.move(2, self.height() - 25)

        # 메인 프레임
        self.main_ui: MainUI = MainUI(self, self.page1, self.shared_data)

        # 사이드바
        self.sidebar: Sidebar = Sidebar(self, self.page1, self.shared_data)

        # 시뮬레이션 UI
        self.sim_ui: SimUI = SimUI(self, self.page2, self.shared_data)

        # 팝업 매니저 초기화
        self.popup_manager: PopupManager = PopupManager(self, self.shared_data)

        self.sidebar.change_sidebar_to_1()

        self.window_layout: QStackedLayout = QStackedLayout()
        self.window_layout.addWidget(self.page1)  # 메인 페이지
        self.window_layout.addWidget(self.page2)  # 시뮬레이션 페이지

        self.setLayout(self.window_layout)
        self.window_layout.setCurrentIndex(0)  # 메인 페이지로 시작

        self.show()

        # self.change_layout(1)

    def tick(self) -> None:  # main_ui로 이동
        """
        스킬 미리보기 표시
        """

        self.preview_timer.singleShot(100, self.tick)
        self.main_ui.show_preview_skills()

    ## 마우스 클릭하면 실행
    def mousePressEvent(self, a0):
        self.popup_manager.disablePopup()
        if self.shared_data.layout_type == 0:
            self.main_ui.cancel_skill_selection()

    ## 사이드바 구분선 생성
    def paintEvent(self, a0):
        if self.shared_data.layout_type == 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setPen(QPen(QColor(180, 180, 180), 1, Qt.PenStyle.SolidLine))
            painter.drawLine(320, 0, 320, self.height())

    ## 창 크기 조절시 실행
    def resizeEvent(self, a0):
        self.update()
        self.update_position()

    ## 창 크기 조절시 위젯 위치, 크기 조절
    def update_position(self):
        self.main_ui.update_position()
        self.popup_manager.update_position()
        self.sim_ui.update_position()

        # 항상 업데이트
        self.creator_label.move(2, self.height() - 25)

    def get_main_ui(self) -> MainUI:
        """
        메인 UI 객체 반환
        """
        return self.main_ui

    def get_sidebar(self) -> Sidebar:
        """
        사이드바 객체 반환
        """
        return self.sidebar

    def get_popup_manager(self) -> PopupManager:
        """
        팝업 매니저 객체 반환
        """
        return self.popup_manager


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
