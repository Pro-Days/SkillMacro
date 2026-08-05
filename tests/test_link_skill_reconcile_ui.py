from __future__ import annotations

import os

# 장착 구성 변경 UI 검증의 디스플레이 비의존 실행 보장
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from app.scripts import data_manager
from app.scripts.app_state import SidebarPage, app_state
from app.scripts.custom_skill_models import CustomSkillImport
from app.scripts.macro_models import (
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    MacroPreset,
    SkillUsageSetting,
)
from app.scripts.ui.main_ui.main_ui import Tab
from app.scripts.ui.main_window import MainWindow
from app.scripts.ui.popup import NoticeKind


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


@pytest.fixture
def main_window(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    isolated_data_paths: dict[str, str],
) -> Iterator[MainWindow]:
    """백그라운드 작업과 시작 프롬프트를 제외한 메인 창"""

    monkeypatch.setattr(MainWindow, "activate_thread", lambda self: None)
    monkeypatch.setattr(MainWindow, "_run_startup_prompts", lambda self: None)
    monkeypatch.setattr(MainWindow, "_restore_window_geometry", lambda self: None)
    monkeypatch.setattr(MainWindow, "_confirm_future_data_execution", lambda self: True)

    window: MainWindow = MainWindow()
    window.show()
    qapplication.processEvents()

    yield window

    window.hide()
    window.deleteLater()
    qapplication.processEvents()


def _auto_badges(window: MainWindow) -> list[str]:
    """사이드바 연계 목록에 표시된 자동 사용 배지 문구 수집"""

    layout = window.sidebar.link_skill_settings._list_layout
    badge_texts: list[str] = []

    for index in range(layout.count()):
        item = layout.itemAt(index)
        widget = None if item is None else item.widget()
        if widget is None:
            continue

        label: QLabel
        for label in widget.findChildren(QLabel):
            if label.objectName() in ("badgeAuto", "badgeManual"):
                badge_texts.append(label.text())

    return badge_texts


def test_unplacing_skill_disables_auto_and_notifies(
    qapplication: QApplication,
    main_window: MainWindow,
) -> None:
    """배치 해제 시 순서·단축키 유지, 자동 해제 알림, 목록 갱신 검증"""

    preset: MacroPreset = app_state.macro.current_preset
    tab: Tab = main_window.main_ui.tab_widget.get_current_tab()
    registry = app_state.macro.current_server.skill_registry
    scroll_ids: list[str] = registry.get_all_scroll_ids()
    first_skill_id: str = registry.get_scroll(scroll_ids[0]).skills[0]
    second_skill_id: str = registry.get_scroll(scroll_ids[1]).skills[0]

    preset.skills.equipped_scrolls[0] = scroll_ids[0]
    preset.skills.equipped_scrolls[1] = scroll_ids[1]
    preset.skills.placed_skills[0] = first_skill_id
    preset.skills.placed_skills[1] = second_skill_id
    preset.link_skills = [
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.ON,
            key="q",
            skills=[second_skill_id, first_skill_id],
        )
    ]
    tab.update_from_preset()
    main_window.sidebar.update_from_preset()
    main_window.sidebar.change_page(SidebarPage.LINK_SKILL)
    qapplication.processEvents()

    notices: list[NoticeKind] = []
    tab.noticeRequested.connect(notices.append)

    # 선택 후 재클릭으로 첫 슬롯 배치 해제
    slot_button = tab.placed_skills.columns[0].buttons[0]
    QTest.mouseClick(slot_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(slot_button, Qt.MouseButton.LeftButton)
    qapplication.processEvents()

    link_skill: LinkSkill = preset.link_skills[0]
    assert preset.skills.placed_skills[0] == ""
    assert notices == [NoticeKind.LINK_SKILL_AUTO_DISABLED]
    assert link_skill.skills == [second_skill_id, first_skill_id]
    assert link_skill.use_type == LinkUseType.MANUAL
    assert link_skill.key_type == LinkKeyType.ON
    assert link_skill.key == "q"
    assert _auto_badges(main_window) == ["자동 OFF"]


def test_unequipping_scroll_reconciles_link_skills_and_notifies(
    qapplication: QApplication,
    main_window: MainWindow,
) -> None:
    """무공비급 해제 시 연계 삭제·구성 정리와 실행 가능한 자동 연계 유지 검증"""

    preset: MacroPreset = app_state.macro.current_preset
    tab: Tab = main_window.main_ui.tab_widget.get_current_tab()
    registry = app_state.macro.current_server.skill_registry
    scroll_ids: list[str] = registry.get_all_scroll_ids()
    removed_skill_id: str = registry.get_scroll(scroll_ids[0]).skills[0]
    kept_skill_id: str = registry.get_scroll(scroll_ids[1]).skills[0]
    unrelated_skill_id: str = registry.get_scroll(scroll_ids[2]).skills[0]

    preset.skills.equipped_scrolls[0] = scroll_ids[0]
    preset.skills.equipped_scrolls[1] = scroll_ids[1]
    preset.skills.equipped_scrolls[2] = scroll_ids[2]
    preset.skills.placed_skills[0] = removed_skill_id
    preset.skills.placed_skills[1] = kept_skill_id
    preset.skills.placed_skills[2] = unrelated_skill_id
    preset.link_skills = [
        # 해제 대상 스킬이 빠져 구성만 바뀌는 연계
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.ON,
            key="q",
            skills=[kept_skill_id, removed_skill_id],
        ),
        # 남는 스킬이 없어 통째로 사라지는 연계
        LinkSkill(
            use_type=LinkUseType.MANUAL,
            key_type=LinkKeyType.ON,
            key="e",
            skills=[removed_skill_id],
        ),
        # 해제 영향을 받지 않는 자동 연계
        LinkSkill(use_type=LinkUseType.AUTO, skills=[unrelated_skill_id]),
    ]
    tab.update_from_preset()
    main_window.sidebar.update_from_preset()
    main_window.sidebar.change_page(SidebarPage.LINK_SKILL)
    qapplication.processEvents()

    notices: list[NoticeKind] = []
    tab.noticeRequested.connect(notices.append)

    # 장착된 무공비급 슬롯 재클릭으로 장착 해제
    QTest.mouseClick(
        tab.available_skills.get_scroll_button(0),
        Qt.MouseButton.LeftButton,
    )
    qapplication.processEvents()

    assert preset.skills.equipped_scrolls[0] == ""
    assert notices == [NoticeKind.LINK_SKILL_ADJUSTED]

    # 구성이 바뀌어도 남은 스킬이 모두 배치되어 있으면 순서·단축키·자동 사용 유지
    adjusted_link: LinkSkill = preset.link_skills[0]
    assert adjusted_link.skills == [kept_skill_id]
    assert adjusted_link.use_type == LinkUseType.AUTO
    assert adjusted_link.key_type == LinkKeyType.ON
    assert adjusted_link.key == "q"

    # 영향을 받지 않은 연계는 자동 유지
    assert len(preset.link_skills) == 2
    assert preset.link_skills[1].use_type == LinkUseType.AUTO
    assert _auto_badges(main_window) == ["자동 ON", "자동 ON"]


def test_deleting_custom_scroll_preserves_remaining_link_skill(
    main_window: MainWindow,
) -> None:
    """커스텀 비급 삭제 시 남은 연계 보존과 실행 가능성별 자동 상태 검증"""

    server = app_state.macro.current_server
    registry = server.skill_registry
    custom_scroll_id: str = f"custom:{server.id}:연계삭제테스트비급"
    custom_skill_a_id: str = f"custom:{server.id}:연계삭제테스트A"
    custom_skill_b_id: str = f"custom:{server.id}:연계삭제테스트B"
    custom_import: CustomSkillImport = CustomSkillImport.from_dict(
        {
            "skills": [custom_skill_a_id, custom_skill_b_id],
            "scrolls": [
                {
                    "scroll_id": custom_scroll_id,
                    "name": "연계삭제테스트비급",
                    "skills": [custom_skill_a_id, custom_skill_b_id],
                }
            ],
            "skill_details": {
                custom_skill_a_id: {
                    "name": "연계삭제테스트A",
                    "cooltime": 4.0,
                    "target_count": 1,
                    "levels": {"1": 1.0},
                },
                custom_skill_b_id: {
                    "name": "연계삭제테스트B",
                    "cooltime": 5.0,
                    "target_count": 1,
                    "levels": {"1": 1.0},
                },
            },
        }
    )
    data_manager.save_custom_skills(server.id, custom_import)
    data_manager.load_custom_skills()

    builtin_scroll_id: str = next(
        scroll_id
        for scroll_id in registry.get_all_scroll_ids()
        if scroll_id != custom_scroll_id
    )
    builtin_skill_id: str = registry.get_scroll(builtin_scroll_id).skills[0]
    unplaced_builtin_skill_id: str = registry.get_scroll(builtin_scroll_id).skills[1]
    preset: MacroPreset = app_state.macro.current_preset
    preset.skills.equipped_scrolls[0] = custom_scroll_id
    preset.skills.equipped_scrolls[1] = builtin_scroll_id
    preset.skills.placed_skills[0] = custom_skill_a_id
    preset.skills.placed_skills[1] = builtin_skill_id
    preset.usage_settings[custom_skill_a_id] = SkillUsageSetting()
    preset.usage_settings[custom_skill_b_id] = SkillUsageSetting()
    preset.info.scroll_levels[custom_scroll_id] = 1
    preset.link_skills = [
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.ON,
            key="q",
            skills=[custom_skill_a_id, builtin_skill_id],
        ),
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.ON,
            key="e",
            skills=[custom_skill_b_id, unplaced_builtin_skill_id],
        ),
        LinkSkill(
            use_type=LinkUseType.MANUAL,
            key_type=LinkKeyType.ON,
            key="r",
            skills=[custom_skill_b_id],
        ),
    ]

    main_window.sidebar.skill_settings._selected_scroll_id = custom_scroll_id
    main_window.sidebar.skill_settings._on_delete_custom_scroll()

    assert custom_scroll_id not in registry.get_all_scroll_ids()
    assert custom_skill_a_id not in registry.get_all_skill_ids()
    assert custom_skill_b_id not in registry.get_all_skill_ids()
    assert custom_scroll_id not in preset.skills.equipped_scrolls
    assert custom_skill_a_id not in preset.skills.placed_skills
    assert custom_skill_a_id not in preset.usage_settings
    assert custom_skill_b_id not in preset.usage_settings
    assert custom_scroll_id not in preset.info.scroll_levels

    assert len(preset.link_skills) == 2

    runnable_link: LinkSkill = preset.link_skills[0]
    assert runnable_link.skills == [builtin_skill_id]
    assert runnable_link.use_type == LinkUseType.AUTO
    assert runnable_link.key_type == LinkKeyType.ON
    assert runnable_link.key == "q"

    unrunnable_link: LinkSkill = preset.link_skills[1]
    assert unrunnable_link.skills == [unplaced_builtin_skill_id]
    assert unrunnable_link.use_type == LinkUseType.MANUAL
    assert unrunnable_link.key_type == LinkKeyType.ON
    assert unrunnable_link.key == "e"


def test_sidebar_page_state_tracks_navigation(
    qapplication: QApplication,
    main_window: MainWindow,
) -> None:
    """연계 편집 중 변경 차단이 의존하는 사이드바 페이지 상태 동기화 검증"""

    # 네비게이션 버튼 경로
    QTest.mouseClick(
        main_window.sidebar.nav_button.buttons[SidebarPage.SKILL],
        Qt.MouseButton.LeftButton,
    )
    qapplication.processEvents()
    assert app_state.ui.current_sidebar_page == SidebarPage.SKILL

    # 가이드 경로
    main_window.guide_manager._sidebar_page(SidebarPage.LINK_SKILL)
    assert (
        main_window.sidebar.page_navigator.currentIndex() == SidebarPage.LINK_SKILL
    )
    assert app_state.ui.current_sidebar_page == SidebarPage.LINK_SKILL

    # 연계스킬 편집 진입 및 복귀
    registry = app_state.macro.current_server.skill_registry
    skill_id: str = registry.get_scroll(registry.get_all_scroll_ids()[0]).skills[0]
    app_state.macro.current_preset.link_skills = [LinkSkill(skills=[skill_id])]
    main_window.sidebar.link_skill_settings.edit(0)
    assert app_state.ui.current_sidebar_page == SidebarPage.LINK_SKILL_EDITOR

    main_window.sidebar.link_skill_editor.cancel()
    assert app_state.ui.current_sidebar_page == SidebarPage.LINK_SKILL
