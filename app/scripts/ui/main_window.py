from __future__ import annotations

import sys
from threading import Thread
from typing import Any
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

from app.scripts.app_state import app_state
from app.scripts.config import config
from app.scripts.custom_classes import CustomFont
from app.scripts.data_manager import load_data
from app.scripts.registry.resource_registry import convert_resource_path
from app.scripts.run_macro import checking_kb_thread
from app.scripts.ui.main_ui.main_ui import MainUI
from app.scripts.ui.main_ui.sidebar import Sidebar
from app.scripts.ui.popup import PopupManager
from app.scripts.ui.sim_ui.simul_ui import SimUI


class MainWindow(QWidget):
    def __init__(self) -> None:
        """
        메인 윈도우 초기화
        """

        super().__init__()

        # 프로그램 아이콘 설정
        self.setWindowIcon(
            QIcon(QPixmap(convert_resource_path("resources\\image\\icon.ico")))
        )

        # 매크로 데이터 불러오기
        load_data()

        # 프로그램 화면 설정
        self.init_UI()

        # 서브 쓰레드 활성화
        self.activate_thread()

    def activate_thread(self) -> None:
        """
        서브 쓰레드 활성화
        """

        # 키보드 입력 감지 쓰레드
        Thread(target=checking_kb_thread, daemon=True).start()

        # 버전 확인 쓰레드
        if config.macro.is_version_check_enabled:
            self.version_timer: QTimer = QTimer(self)
            self.version_timer.singleShot(100, self.version_check_thread)

    def change_layout(self, num: int) -> None:
        """
        레이아웃 변경

        0: 메인 매크로
        1: 시뮬레이션
        # 2: 매크로 공유
        """

        self.page_navigator.setCurrentIndex(num)

    def keyPressEvent(self, e: QKeyEvent) -> None:  # type: ignore
        """
        키 입력 시 실행
        """

        # ESC
        if e.key() == Qt.Key.Key_Escape:
            # 에러 팝업창이 있을 때
            if app_state.ui.active_error_popups:
                self.popup_manager.close_notice_popup()

        # Ctrl
        elif e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl + W -> 탭 제거
            if e.key() == Qt.Key.Key_W:
                self.main_ui.on_remove_tab_clicked(app_state.macro.current_preset_index)

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
                app_state.ui.current_version = response.json()["name"]
                app_state.ui.update_url = response.json()["html_url"]

            # 응답이 실패하면 버전 확인 실패로 처리
            else:
                app_state.ui.current_version = "FailedUpdateCheck"
                app_state.ui.update_url = ""

        # 예외 발생 시 버전 확인 실패로 처리
        except Exception:
            app_state.ui.current_version = "FailedUpdateCheck"
            app_state.ui.update_url = ""

        # 버전 확인 결과에 따라 팝업 표시
        if app_state.ui.current_version == "FailedUpdateCheck":
            self.popup_manager.make_notice_popup("FailedUpdateCheck")

        # 현재 버전과 최신 버전이 일치하지 않는 경우
        elif app_state.ui.current_version != config.version:
            self.popup_manager.make_notice_popup("RequireUpdate")

    def init_UI(self) -> None:
        """
        프로그램 처음 UI 설정
        """

        self.setWindowTitle("데이즈 스킬매크로 " + config.version)
        self.setMinimumSize(
            config.ui.DEFAULT_WINDOW_WIDTH,
            config.ui.DEFAULT_WINDOW_HEIGHT,
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
        self.popup_manager: PopupManager = PopupManager(self)

        # 메인 프레임
        self.main_ui: MainUI = MainUI(self)

        # 사이드바
        self.sidebar: Sidebar = Sidebar(
            self,
            app_state.macro.presets[app_state.macro.current_preset_index],
            app_state.macro.current_preset_index,
        )

        # 탭(프리셋) 변경 시 사이드바를 시그널로 동기화
        self.main_ui.presetChanged.connect(self.sidebar.set_current_preset)
        self.main_ui.emit_preset_changed()

        # 메인 UI에서 스킬이 해제되면
        # 사이드바의 스킬 사용설정/연계설정 페이지 새로고침
        self.main_ui.tab_widget.skillUnequipped.connect(
            lambda _: self.sidebar.refresh_skill_related_pages()
        )

        # 사이드바에서 데이터 변경 시 저장은 MainUI 파이프라인(=tab_widget.dataChanged)로 위임
        self.sidebar.dataChanged.connect(self.main_ui.tab_widget.dataChanged.emit)

        # 시뮬레이션 UI
        self.sim_ui: SimUI = SimUI(self, self.page2)

        # 하단 제작자 라벨 설정
        self.creator_label: QPushButton = CreatorLabel(self)

        page1_layout = QHBoxLayout()
        page1_layout.addWidget(self.sidebar)
        page1_layout.addWidget(self.main_ui, stretch=1)
        page1_layout.setContentsMargins(0, 0, 0, 0)
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
