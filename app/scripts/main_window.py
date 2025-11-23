from __future__ import annotations

import sys
from threading import Thread
from typing import Any, Literal
from webbrowser import open_new

import requests
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QKeyEvent, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.scripts.config import config
from app.scripts.custom_classes import CustomFont
from app.scripts.data_manager import load_data, update_data, update_skill_data
from app.scripts.misc import convert_resource_path, set_default_fonts
from app.scripts.popup import PopupManager
from app.scripts.run_macro import checking_kb_thread
from app.scripts.shared_data import SharedData, UI_Variable
from app.scripts.ui.main_ui.main_ui import MainUI
from app.scripts.ui.main_ui.sidebar import Sidebar
from app.scripts.ui.sim_ui.simul_ui import SimUI


class MainWindow(QWidget):
    def __init__(self) -> None:
        """
        메인 윈도우 초기화
        """

        super().__init__()

        # 기본 폰트 설정
        set_default_fonts()

        self.shared_data: SharedData = SharedData()
        self.ui_var: UI_Variable = UI_Variable()

        # 프로그램 아이콘 설정
        self.setWindowIcon(
            QIcon(QPixmap(convert_resource_path("resources\\image\\icon.ico")))
        )

        # 매크로 데이터 불러오기
        update_data(self.shared_data)
        update_skill_data(self.shared_data)
        load_data(self.shared_data)

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
        # self.preview_timer: QTimer = QTimer(self)
        # self.preview_timer.singleShot(100, self.tick)

        # 버전 확인 쓰레드
        if self.shared_data.IS_VERSION_CHECK_ENABLED:
            self.version_timer: QTimer = QTimer(self)
            self.version_timer.singleShot(100, self.version_check_thread)

    def change_layout(self, num: Literal[0, 1]) -> None:
        """
        레이아웃 변경

        0: 메인 매크로
        1: 시뮬레이션
        2: 매크로 공유
        """

        self.page_navigator.setCurrentIndex(num)

    def keyPressEvent(self, e: QKeyEvent) -> None:  # type: ignore
        """
        키 입력 시 실행
        """

        # ESC
        if e.key() == Qt.Key.Key_Escape:
            # 매크로 탭 제거 중
            if self.shared_data.is_tab_remove_popup_activated:
                self.main_ui.on_remove_tab_popup_clicked(0, False)

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
                self.main_ui.on_remove_tab_clicked(self.shared_data.recent_preset)

        # Enter
        elif e.key() == Qt.Key.Key_Return:
            # 탭 제거 팝업창이 활성화되어 있을 때 -> 탭 제거 실행
            if self.shared_data.is_tab_remove_popup_activated:
                self.main_ui.on_remove_tab_popup_clicked(self.shared_data.recent_preset)

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

        if config.ui.debug_colors:
            self.page2.setStyleSheet("QFrame { background-color: yellow;}")

        # 팝업 매니저 초기화
        self.popup_manager: PopupManager = PopupManager(self, self.shared_data)

        # 메인 프레임
        self.main_ui: MainUI = MainUI(self, self.shared_data)

        # 사이드바
        self.sidebar: Sidebar = Sidebar(self, self.shared_data)

        # 시뮬레이션 UI
        self.sim_ui: SimUI = SimUI(self, self.page2, self.shared_data)

        # 하단 제작자 라벨 설정
        self.creator_label: QPushButton = CreatorLabel(self)

        self.sidebar.change_sidebar_to_1()

        page1_layout = QHBoxLayout()
        # page1_layout.addWidget(self.sidebar)
        page1_layout.addWidget(self.main_ui, stretch=1)
        page1_layout.setContentsMargins(50, 50, 50, 50)
        page1_layout.setSpacing(0)
        self.page1.setLayout(page1_layout)

        self.page_navigator = QStackedWidget()
        self.page_navigator.addWidget(self.page1)  # 메인 페이지
        self.page_navigator.addWidget(self.page2)  # 시뮬레이션 페이지
        self.page_navigator.setContentsMargins(0, 0, 0, 0)
        self.page_navigator.setCurrentIndex(0)  # 메인 페이지로 시작

        layout = QVBoxLayout()
        layout.addWidget(self.page_navigator)
        layout.addWidget(self.creator_label)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setLayout(layout)

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

        if self.page_navigator.currentIndex() == 0:
            self.main_ui.cancel_skill_selection()

    def get_main_ui(self) -> MainUI:
        """메인 UI 객체 반환"""
        return self.main_ui

    def get_sidebar(self) -> Sidebar:
        """사이드바 객체 반환"""
        return self.sidebar

    def get_popup_manager(self) -> PopupManager:
        """팝업 매니저 객체 반환"""
        return self.popup_manager


class CreatorLabel(QPushButton):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("  제작자: 프로데이즈  |  디스코드: prodays", parent)

        self.setFont(CustomFont(10))
        self.setStyleSheet(
            "QPushButton { background-color: transparent; text-align: left; border: 0px; }"
        )
        self.clicked.connect(lambda: open_new("https://github.com/Pro-Days/SkillMacro"))
        self.setFixedSize(320, 24)


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    window = MainWindow()
    sys.exit(app.exec())
