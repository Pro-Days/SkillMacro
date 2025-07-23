from .misc import convert_resource_path
from .simul_ui import SimUI
from .main_ui import MainUI
from .sidebar import Sidebar
from .misc import set_default_fonts
from .popup import PopupManager
from .shared_data import SharedData, UI_Variable
from .data_manager import update_data, load_data, update_skill_data
from .run_macro import checking_kb_thread
from .custom_classes import CustomFont

import sys
import requests

from threading import Thread
from webbrowser import open_new
from typing import Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QPen,
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
            QIcon(QPixmap(convert_resource_path("resources\\image\\icon.ico")))
        )

        # 매크로 데이터 불러오기
        update_data(shared_data=self.shared_data)
        update_skill_data(shared_data=self.shared_data)
        load_data(shared_data=self.shared_data)

        # 프로그램 화면 설정
        self.init_UI()

        # 서브 쓰레드 활성화
        self.activate_thread()

    def activate_thread(self) -> None:
        """
        서브 쓰레드 활성화
        """

        # 키보드 입력 감지
        Thread(target=checking_kb_thread, args=[self.shared_data], daemon=True).start()

        # 스킬 미리보기 쓰레드
        self.preview_timer: QTimer = QTimer(self)
        self.preview_timer.singleShot(100, self.tick)

        # 버전 확인 쓰레드
        if self.shared_data.IS_VERSION_CHECK_ENABLED:
            self.version_timer: QTimer = QTimer(self)
            self.version_timer.singleShot(100, self.version_check_thread)

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
            # 매크로 탭 제거 중
            if self.shared_data.is_tab_remove_popup_activated:
                self.main_ui.on_tab_remove_popup_clicked(0, False)

            # 에러 팝업창이 있을 때
            elif self.shared_data.active_error_popup_count >= 1:
                self.popup_manager.close_notice_popup()

            # 일반 팝업창이 있을 때
            elif self.shared_data.active_popup != "":
                self.popup_manager.close_popup()

        # Ctrl
        elif e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl + W -> 탭 제거
            if (
                e.key() == Qt.Key.Key_W
                and not self.shared_data.is_tab_remove_popup_activated
            ):
                self.main_ui.on_tab_remove_clicked(self.shared_data.recent_preset)

        # Enter
        elif e.key() == Qt.Key.Key_Return:
            # 탭 제거 팝업창이 활성화되어 있을 때 -> 탭 제거 실행
            if self.shared_data.is_tab_remove_popup_activated:
                self.main_ui.on_tab_remove_popup_clicked(self.shared_data.recent_preset)

            # 일반 팝업창이 활성화되어 있을 때 -> 팝업창 클릭
            elif self.shared_data.active_popup == "settingDelay":
                self.popup_manager.on_input_popup_clicked("delay")

            # 일반 팝업창이 활성화되어 있을 때 -> 팝업창 클릭
            elif self.shared_data.active_popup == "settingCooltime":
                self.popup_manager.on_input_popup_clicked("cooltime")

            # 매크로 탭 이름 변경 팝업창이 활성화되어 있을 때 -> 탭 이름 변경 실행
            elif self.shared_data.active_popup == "changeTabName":
                self.popup_manager.on_input_popup_clicked(
                    "tabName", self.shared_data.recent_preset
                )

        # 테스트 용 키입력
        # elif e.key() == Qt.Key.Key_L:
        #     print(self.getSimulatedSKillList())

    def version_check_thread(self) -> None:
        """
        최신버전 확인 쓰레드
        """

        try:
            # GitHub API를 통해 최신 버전 확인
            response: requests.Response = requests.get(
                "https://api.github.com/repos/pro-days/skillmacro/releases/latest"
            )

            # 응답이 성공적이면 최신 버전 정보 저장
            if response.status_code == 200:
                self.shared_data.recent_version = response.json()["name"]
                self.shared_data.update_url = response.json()["html_url"]

            # 응답이 실패하면 버전 확인 실패로 처리
            else:
                self.shared_data.recent_version = "FailedUpdateCheck"
                self.shared_data.update_url = ""

        # 예외 발생 시 버전 확인 실패로 처리
        except Exception:
            self.shared_data.recent_version = "FailedUpdateCheck"
            self.shared_data.update_url = ""

        # 버전 확인 결과에 따라 팝업 표시
        if self.shared_data.recent_version == "FailedUpdateCheck":
            self.popup_manager.make_notice_popup("FailedUpdateCheck")

        # 현재 버전과 최신 버전이 일치하지 않는 경우
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

        # 포커스 시 테두리 제거
        self.setStyleSheet("*:focus { outline: none; }")

        # 배경 팔레트 설정
        self.background_palette: QPalette = self.palette()
        self.background_palette.setColor(
            QPalette.ColorRole.Window, QColor(255, 255, 255)
        )
        self.setPalette(self.background_palette)

        # 페이지 프레임 설정
        # 페이지1: 메인 매크로, 페이지2: 시뮬레이션
        self.page1: QFrame = QFrame(self)
        self.page2: QFrame = QFrame(self)

        # 하단 제작자 라벨 설정
        self.creator_label: QPushButton = QPushButton(
            "  제작자: 프로데이즈  |  디스코드: prodays", self
        )
        self.creator_label.setFont(CustomFont(10))
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

        # 팝업 매니저 초기화
        self.popup_manager: PopupManager = PopupManager(self, self.shared_data)

        # 시뮬레이션 UI
        self.sim_ui: SimUI = SimUI(self, self.page2, self.shared_data)

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
    def mousePressEvent(self, a0: Any) -> None:
        self.popup_manager.close_popup()
        if self.shared_data.layout_type == 0:
            self.main_ui.cancel_skill_selection()

    ## 사이드바 구분선 생성
    def paintEvent(self, a0: Any) -> None:
        if self.shared_data.layout_type == 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setPen(QPen(QColor(180, 180, 180), 1, Qt.PenStyle.SolidLine))
            painter.drawLine(320, 0, 320, self.height())

    ## 창 크기 조절시 실행
    def resizeEvent(self, a0: Any) -> None:
        self.update()
        self.update_position()

    ## 창 크기 조절시 위젯 위치, 크기 조절
    def update_position(self) -> None:
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
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    window = MainWindow()
    sys.exit(app.exec())
