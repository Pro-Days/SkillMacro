from __future__ import annotations

import importlib
import os
import pkgutil
from collections.abc import Iterator

# 창 생성 smoke 테스트의 디스플레이 비의존 실행 보장
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabBar

import app.scripts
import app.scripts.run_macro as run_macro
from app.scripts import data_manager
from app.scripts.app_state import SidebarPage, app_state
from app.scripts.config import config
from app.scripts.macro_models import LinkSkill, LinkUseType
from app.scripts.ui.popup import (
    InputConfirmContent,
    NoticeKind,
    PopupAction,
    PopupKind,
    PopupPlacement,
)


def _collect_module_names() -> list[str]:
    """app.scripts 하위 전체 모듈 이름 수집"""

    module_names: list[str] = []
    for module_info in pkgutil.walk_packages(
        app.scripts.__path__,
        prefix="app.scripts.",
    ):
        module_names.append(module_info.name)

    return sorted(module_names)


@pytest.mark.parametrize("module_name", _collect_module_names())
def test_module_imports_cleanly(module_name: str) -> None:
    """UI 포함 전체 모듈의 임포트 오류 부재 검증"""

    importlib.import_module(module_name)


@pytest.fixture(scope="session")
def qapplication() -> Iterator[QApplication]:
    """Qt 위젯 생성 테스트가 공유하는 단일 QApplication"""

    application = QApplication.instance()
    owns_application: bool = application is None
    if application is None:
        application = QApplication([])

    assert isinstance(application, QApplication)
    application.setQuitOnLastWindowClosed(False)
    yield application

    if owns_application:
        application.quit()


def test_main_window_and_lazy_pages_construct_offscreen(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    isolated_data_paths: dict[str, str],
) -> None:
    """백그라운드 작업 없이 메인 창과 계산기 지연 페이지 실제 생성 검증"""

    from app.scripts.ui.character_ui import CharacterPage
    from app.scripts.ui.main_window import MainWindow
    from app.scripts.ui.sim_ui.refinement_ui import RefinementPage
    from app.scripts.ui.sim_ui.simul_ui import GraphPage, ResultsPage, SimUI

    def skip_background_threads(self: MainWindow) -> None:
        return None

    def skip_startup_prompts(self: MainWindow) -> None:
        return None

    def skip_saved_geometry(self: MainWindow) -> None:
        return None

    def allow_current_data(self: MainWindow) -> bool:
        return True

    monkeypatch.setattr(MainWindow, "activate_thread", skip_background_threads)
    monkeypatch.setattr(MainWindow, "_run_startup_prompts", skip_startup_prompts)
    monkeypatch.setattr(MainWindow, "_restore_window_geometry", skip_saved_geometry)
    monkeypatch.setattr(
        MainWindow,
        "_confirm_future_data_execution",
        allow_current_data,
    )

    window: MainWindow = MainWindow()
    simulator: SimUI = window.sim_ui
    character_page: CharacterPage = simulator.character_page
    graph_page: GraphPage = simulator.graph_page
    results_page: ResultsPage = simulator.results_page
    refinement_page: RefinementPage = simulator.refinement_page

    assert os.path.isfile(isolated_data_paths["file_dir"])
    assert os.path.isfile(isolated_data_paths["characters_file_dir"])
    assert window.main_ui is not None
    assert window.sidebar is not None
    assert simulator.input_page is not None
    assert isinstance(character_page, CharacterPage)
    assert isinstance(graph_page, GraphPage)
    assert isinstance(results_page, ResultsPage)
    assert isinstance(refinement_page, RefinementPage)

    # 지연 페이지의 스택 연결과 재접근 시 동일 객체 재사용 확인
    assert simulator.stacked_layout.widget(1) is graph_page
    assert simulator.stacked_layout.widget(2) is results_page
    assert simulator.stacked_layout.widget(3) is character_page
    assert simulator.stacked_layout.widget(4) is refinement_page
    assert simulator.graph_page is graph_page
    assert simulator.results_page is results_page
    assert simulator.character_page is character_page
    assert simulator.refinement_page is refinement_page

    # 연계 편집 중 스킬·무공비급 변경 차단과 저장 시 자동 상태 보정
    preset = app_state.macro.current_preset
    current_tab = window.main_ui.tab_widget.get_current_tab()
    server = app_state.macro.current_server
    scroll_id: str = server.skill_registry.get_all_scroll_ids()[0]
    skill_id: str = server.skill_registry.get_scroll(scroll_id).skills[0]
    preset.skills.equipped_scrolls[0] = scroll_id
    preset.skills.placed_skills[0] = skill_id
    preset.link_skills = [LinkSkill(use_type=LinkUseType.AUTO, skills=[skill_id])]
    current_tab.update_from_preset()
    window.sidebar.update_from_preset()

    popup_manager = window.get_popup_manager()
    editing_notices: list[NoticeKind] = []
    current_tab.noticeRequested.connect(editing_notices.append)
    monkeypatch.setattr(
        popup_manager._notice_controller,
        "show",
        lambda _kind, _text=None: None,
    )

    window.show()
    qapplication.processEvents()
    window.sidebar.link_skill_settings.edit(0)
    assert app_state.ui.current_sidebar_page == SidebarPage.LINK_SKILL_EDITOR

    QTest.mouseClick(
        current_tab.placed_skills.columns[0].buttons[0],
        Qt.MouseButton.LeftButton,
    )
    QTest.mouseClick(
        current_tab.available_skills.columns[0].skill_buttons[0],
        Qt.MouseButton.LeftButton,
    )
    QTest.mouseClick(
        current_tab.available_skills.get_scroll_button(0),
        Qt.MouseButton.LeftButton,
    )
    QTest.mouseClick(
        current_tab.available_skills.get_scroll_button(1),
        Qt.MouseButton.LeftButton,
    )
    qapplication.processEvents()

    assert preset.skills.placed_skills[0] == skill_id
    assert preset.skills.equipped_scrolls[0] == scroll_id
    assert preset.skills.equipped_scrolls[1] == ""
    assert current_tab.get_selected_skill_ref() is None
    assert not popup_manager.is_popup_active(PopupKind.SCROLL_SELECT)
    assert editing_notices == [NoticeKind.EDITING_LINK_SKILL] * 4

    # 편집 외부에서 배치 상태가 달라져도 실행 불가능한 AUTO 저장 방지
    preset.skills.placed_skills[0] = ""
    window.sidebar.link_skill_editor.save()
    assert preset.link_skills[0].use_type == LinkUseType.MANUAL
    assert app_state.ui.current_sidebar_page == SidebarPage.LINK_SKILL

    # 수동 연계 입력 중 프리셋 전환 차단 확인
    data_manager.add_preset()
    window.main_ui.tab_widget.add_tab(app_state.macro.presets[-1])
    window.main_ui.tab_widget.setCurrentIndex(0)
    window.show()
    qapplication.processEvents()
    assert app_state.macro.current_preset_index == 0

    tab_bar: QTabBar = window.main_ui.tab_widget.get_tab_bar()
    popup_manager = window.get_popup_manager()

    # 메뉴를 연 뒤 수동 연계가 시작되어도 액션 콜백 실행 차단
    blocked_action_calls: list[bool] = []
    popup_manager.make_action_list_popup(
        PopupKind.PRESET_ADD,
        window.main_ui.tab_widget.add_tab_button,
        [
            PopupAction(
                id="blockedAction",
                text="차단 확인",
                on_trigger=lambda: blocked_action_calls.append(True),
            )
        ],
        PopupPlacement.BELOW,
    )
    run_macro.is_input_sequence_running = True
    try:
        popup_manager._popup_controller._on_triggered("blockedAction")
        qapplication.processEvents()
        assert blocked_action_calls == []
    finally:
        run_macro.is_input_sequence_running = False

    # 팝업을 연 뒤 수동 연계가 시작되어도 제출 시점 변경 차단
    settings = app_state.macro.current_preset.settings
    settings.use_custom_delay = True
    window.sidebar.general_settings.update_from_preset(app_state.macro.current_preset)
    window.sidebar.general_settings.on_user_delay_clicked()

    popup_content = popup_manager._popup_controller.host.current_content()
    assert isinstance(popup_content, InputConfirmContent)

    original_delay: int = settings.custom_delay
    blocked_delay: int = (
        config.specs.DELAY.min
        if original_delay != config.specs.DELAY.min
        else config.specs.DELAY.max
    )

    run_macro.is_input_sequence_running = True
    try:
        popup_content.submitted.emit(str(blocked_delay))
        qapplication.processEvents()
        assert settings.custom_delay == original_delay

        # 직접 설정 버튼과 프리셋 탭도 같은 실행 경계에서 차단
        window.sidebar.general_settings.on_default_delay_clicked()
        assert settings.use_custom_delay is True

        QTest.mouseClick(
            tab_bar,
            Qt.MouseButton.LeftButton,
            pos=tab_bar.tabRect(1).center(),
        )
        qapplication.processEvents()
        assert window.main_ui.tab_widget.currentIndex() == 0
        assert app_state.macro.current_preset_index == 0
    finally:
        run_macro.is_input_sequence_running = False

    QTest.mouseClick(
        tab_bar,
        Qt.MouseButton.LeftButton,
        pos=tab_bar.tabRect(1).center(),
    )
    qapplication.processEvents()
    assert window.main_ui.tab_widget.currentIndex() == 1
    assert app_state.macro.current_preset_index == 1

    # 입력 감지 스레드의 실행 불가 연계 알림을 UI 스레드에서 1회 소비
    shown_notices: list[NoticeKind] = []
    monkeypatch.setattr(
        popup_manager,
        "show_notice",
        lambda kind, _text=None: shown_notices.append(kind),
    )
    app_state.macro.has_pending_link_skill_unavailable_notice = True
    window.main_ui._tick_preview_update()
    assert shown_notices == [NoticeKind.LINK_SKILL_NOT_RUNNABLE]
    assert app_state.macro.has_pending_link_skill_unavailable_notice is False

    window.hide()
    window.deleteLater()
    qapplication.processEvents()
