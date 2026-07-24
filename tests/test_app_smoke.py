from __future__ import annotations

import importlib
import os
import pkgutil
from collections.abc import Iterator

# 창 생성 smoke 테스트의 디스플레이 비의존 실행 보장
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import app.scripts


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

    assert os.path.isfile(isolated_data_paths["file_dir"])
    assert os.path.isfile(isolated_data_paths["characters_file_dir"])
    assert window.main_ui is not None
    assert window.sidebar is not None
    assert simulator.input_page is not None
    assert isinstance(character_page, CharacterPage)
    assert isinstance(graph_page, GraphPage)
    assert isinstance(results_page, ResultsPage)

    # 지연 페이지의 스택 연결과 재접근 시 동일 객체 재사용 확인
    assert simulator.stacked_layout.widget(1) is graph_page
    assert simulator.stacked_layout.widget(2) is results_page
    assert simulator.stacked_layout.widget(3) is character_page
    assert simulator.graph_page is graph_page
    assert simulator.results_page is results_page
    assert simulator.character_page is character_page

    window.hide()
    window.deleteLater()
    qapplication.processEvents()
