from __future__ import annotations

import sys
from multiprocessing import freeze_support
from threading import Thread
from typing import Any
from webbrowser import open_new

import requests
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
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
from app.scripts.ui.popup import NoticeKind, PopupManager
from app.scripts.ui.sim_ui.simul_ui import SimUI
from app.scripts.ui.themes import LIGHT_THEME


class MainWindow(QWidget):
    version_check_completed: Signal = Signal(bool, str, str)

    def __init__(self) -> None:
        """
        메인 윈도우 초기화
        """

        super().__init__()

        # 백그라운드 버전 확인 결과 수신 연결
        self.version_check_completed.connect(self._apply_version_check_result)

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
            # 초기 화면 표시 이후 백그라운드 버전 확인 시작
            QTimer.singleShot(100, self._start_version_check_thread)

    def _start_version_check_thread(self) -> None:
        """버전 확인 백그라운드 쓰레드 시작"""

        # UI 프리징 방지를 위한 네트워크 작업 분리
        Thread(target=self.version_check_thread, daemon=True).start()

    def change_layout(self, num: int) -> None:
        """
        레이아웃 변경

        0: 메인 매크로
        1: 시뮬레이션
        # 2: 매크로 공유
        """

        # 계산기 진입 시 입력 화면으로 리셋하고 무공비급 레벨 등 최신 상태 동기화
        if num == 1:
            self.sim_ui.on_enter()

        self.page_navigator.setCurrentIndex(num)

    def keyPressEvent(self, e: QKeyEvent) -> None:  # type: ignore
        """
        키 입력 시 실행
        """

        # ESC
        if e.key() == Qt.Key.Key_Escape:
            # 팝업 닫기
            self.popup_manager.close_popup()
            # 알림 팝업 닫기
            self.popup_manager.close_one_notice()

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
            # GitHub 최신 릴리스 태그 조회
            response: requests.Response = requests.get(
                "https://api.github.com/repos/pro-days/skillmacro/releases/latest",
                timeout=3.0,
            )
            response.raise_for_status()

            # 응답 JSON에서 비교 기준 태그와 이동 URL 추출
            payload: dict[str, Any] = response.json()
            latest_tag: str = str(payload["tag_name"])
            update_url: str = str(payload["html_url"])

        except (requests.RequestException, ValueError, KeyError, TypeError):
            # 실패 결과를 메인 스레드로 전달
            self.version_check_completed.emit(False, "", "")
            return

        # 성공 결과를 메인 스레드로 전달
        self.version_check_completed.emit(True, latest_tag, update_url)

    def _apply_version_check_result(
        self,
        is_success: bool,
        latest_tag: str,
        update_url: str,
    ) -> None:
        """버전 확인 결과 UI 반영"""

        # 실패 상태 초기화 및 알림 표시
        if not is_success:
            app_state.ui.current_version = ""
            app_state.ui.update_url = ""
            self.popup_manager.show_notice(NoticeKind.FAILED_UPDATE_CHECK)
            return

        # 최신 태그와 이동 URL 상태 반영
        app_state.ui.current_version = latest_tag
        app_state.ui.update_url = update_url

        # 현재 태그와 다를 때만 업데이트 안내 표시
        if latest_tag != config.version:
            self.popup_manager.show_notice(NoticeKind.REQUIRE_UPDATE)

    def _show_pending_backup_notices(self) -> None:
        """로딩 중 생성된 데이터 관련 알림 표시"""

        # UI 초기화 전에 만들어진 알림 표시

        # 데이터 파일 백업 알림 표시
        if app_state.ui.has_pending_backup_notice:
            app_state.ui.has_pending_backup_notice = False
            self.popup_manager.show_notice(NoticeKind.DATA_FILE_BACKED_UP)

        # 커스텀 무공비급 중복 정리 알림 표시 블록
        if app_state.ui.has_pending_custom_skill_normalized_notice:
            app_state.ui.has_pending_custom_skill_normalized_notice = False
            self.popup_manager.show_notice(NoticeKind.CUSTOM_SKILLS_NORMALIZED)

    def init_UI(self) -> None:
        """
        프로그램 처음 UI 설정
        """

        self.setObjectName("mainWindow")
        self.setWindowTitle("데이즈 스킬매크로 " + config.version)
        self.setMinimumSize(
            config.ui.DEFAULT_WINDOW_WIDTH,
            config.ui.DEFAULT_WINDOW_HEIGHT,
        )
        # self.setGeometry(0, 0, 960, 540)

        # 글로벌 테마 적용 (다크 모드 색상 반전 방지)
        QApplication.instance().setStyleSheet(LIGHT_THEME)

        # 페이지 프레임 설정
        # 페이지1: 메인 매크로, 페이지2: 시뮬레이션
        self.page1: QFrame = QFrame(self)
        self.page2: QFrame = QFrame(self)

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

        # 커스텀 무공비급 삭제 시 메인 UI 전체 갱신
        self.sidebar.scrollDeleted.connect(
            self.main_ui.tab_widget.get_current_tab().update_from_preset
        )

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

        # 데이터 로딩 중 생성된 백업 알림 표시
        self._show_pending_backup_notices()

        # self.change_layout(1)

    ## 마우스 클릭하면 실행
    def mousePressEvent(self, event) -> None:
        self.popup_manager.close_popup()

        if self.page_navigator.currentIndex() == 0:
            self.main_ui.cancel_skill_selection()

    def resizeEvent(self, event) -> None:
        """윈도우 크기 변경 시 실행"""

        self.popup_manager.update_notice_positions()
        return super().resizeEvent(event)

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

        self.setObjectName("creatorLabel")
        self.setFont(CustomFont(10))
        self.clicked.connect(lambda: open_new("https://github.com/Pro-Days/SkillMacro"))
        self.setFixedSize(320, 24)


if __name__ == "__main__":
    # Windows frozen 멀티프로세싱 재진입 차단 블록
    freeze_support()

    # 고해상도 스케일 정책 적용 블록
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Qt 애플리케이션 실행 블록
    app: QApplication = QApplication(sys.argv)

    window: MainWindow = MainWindow()
    sys.exit(app.exec())
