from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QPushButton,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.custom_classes import CustomFont, SkillImage
from app.scripts.data_manager import (
    add_preset,
    remove_preset,
    save_data,
    update_recent_preset,
)
from app.scripts.macro_models import EquippedSkillRef
from app.scripts.registry.key_registry import KeyRegistry, KeySpec
from app.scripts.registry.resource_registry import (
    convert_resource_path,
    resource_registry,
)
from app.scripts.registry.skill_registry import ScrollDef
from app.scripts.run_macro import build_preview_task_list, init_macro
from app.scripts.ui.popup import NoticeKind, PopupKind, PopupManager

if TYPE_CHECKING:
    from app.scripts.macro_models import MacroPreset, SkillUsageSetting
    from app.scripts.ui.main_window import MainWindow
    from app.scripts.ui.popup import HoverCardData


class MainUI(QFrame):
    presetChanged = Signal(object, int)

    def __init__(self, master: MainWindow) -> None:
        super().__init__()

        self.master: MainWindow = master
        self.popup_manager: PopupManager = master.get_popup_manager()

        self._preview_timer: QTimer = QTimer(self)
        self._preview_timer.timeout.connect(self._tick_preview_update)
        self._preview_timer.start(10)

        self.tab_widget: TabWidget = TabWidget(self, self.popup_manager)
        self.tab_widget.noticeRequested.connect(self.popup_manager.show_notice)
        self.tab_widget.skillKeyRequested.connect(self.on_skill_key_clicked)
        self.tab_widget.scrollSelectRequested.connect(self.on_scroll_select_requested)
        self.tab_widget.dataChanged.connect(lambda: save_data())

        tab_bar: QTabBar = self.tab_widget.get_tab_bar()
        tab_bar.tabBarClicked.connect(self.on_tab_clicked)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.add_tab_button.clicked.connect(self.on_add_tab_clicked)
        self.tab_widget.tabCloseRequested.connect(self.on_remove_tab_clicked)

        layout: QVBoxLayout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        layout.setContentsMargins(30, 30, 30, 10)
        layout.setSpacing(0)
        self.setLayout(layout)

    def _tick_preview_update(self) -> None:
        """프리뷰 갱신"""

        self.tab_widget.get_current_tab().update_preview()

    def emit_preset_changed(self) -> None:
        """현재 프리셋 전달"""

        index: int = self.tab_widget.currentIndex()
        if not app_state.macro.presets or not 0 <= index < len(app_state.macro.presets):
            return

        self.presetChanged.emit(app_state.macro.presets[index], index)

    def on_tab_changed(self, index: int) -> None:
        """탭 변경 처리"""

        update_recent_preset(index)
        self.tab_widget.get_current_tab().update_from_preset()

        if app_state.macro.presets and 0 <= index < len(app_state.macro.presets):
            self.presetChanged.emit(app_state.macro.presets[index], index)

        self.cancel_skill_selection()

    def on_tab_clicked(self, index: int) -> None:
        """탭 클릭 처리"""

        def apply_tab_name(new_name: str) -> None:
            if app_state.macro.presets and 0 <= index < len(app_state.macro.presets):
                app_state.macro.presets[index].name = new_name

            self.tab_widget.setTabText(index, new_name)
            save_data()

        if self.popup_manager.is_popup_active(PopupKind.TAB_NAME):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        if index != self.tab_widget.currentIndex():
            return

        tab_bar: QTabBar = self.tab_widget.get_tab_bar()
        anchor: QWidget = self._get_tab_header_anchor(tab_bar, index)
        self.popup_manager.make_tab_name_popup(anchor, apply_tab_name)

    def on_add_tab_clicked(self) -> None:
        """탭 추가 처리"""

        self.popup_manager.close_popup()

        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        add_preset()
        preset: MacroPreset = app_state.macro.presets[-1]
        self.tab_widget.add_tab(preset)

    def on_remove_tab_clicked(self, index: int) -> None:
        """탭 제거 처리"""

        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        self.tab_widget.remove_tab(index)
        remove_preset(index)

        if not self.tab_widget.count():
            add_preset()
            preset: MacroPreset = app_state.macro.presets[-1]
            self.tab_widget.add_tab(preset)
            return

        new_index: int = self.tab_widget.currentIndex()
        update_recent_preset(new_index)
        self.tab_widget.get_current_tab().update_from_preset()

    def on_skill_key_clicked(self, index: int) -> None:
        """공용키 변경 팝업"""

        def apply(key: KeySpec) -> None:
            current_tab: Tab = self.tab_widget.get_current_tab()
            if current_tab.apply_key(index, key):
                save_data()

        if self.popup_manager.is_popup_active(PopupKind.SKILL_KEY):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        current_tab: Tab = self.tab_widget.get_current_tab()
        self.popup_manager.make_skill_key_popup(
            self.get_key_button(index),
            current_tab.preset.skills.skill_keys[index],
            apply,
        )

    def on_scroll_select_requested(self, scroll_index: int) -> None:
        """스크롤 선택 팝업"""

        def apply(scroll_id: str) -> None:
            current_tab: Tab = self.tab_widget.get_current_tab()
            if current_tab.apply_scroll(scroll_index, scroll_id):
                save_data()

        if self.popup_manager.is_popup_active(PopupKind.SCROLL_SELECT):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        scroll_defs: list[ScrollDef] = (
            app_state.macro.current_server.skill_registry.get_all_scroll_defs()
        )
        current_tab: Tab = self.tab_widget.get_current_tab()
        current_scroll_id: str = current_tab.preset.skills.equipped_scrolls[
            scroll_index
        ]
        self.popup_manager.make_scroll_select_popup(
            current_tab.get_scroll_button(scroll_index),
            scroll_defs,
            current_tab.preset.skills.equipped_scrolls,
            current_scroll_id,
            apply,
        )

    def cancel_skill_selection(self) -> None:
        """하단 선택 취소"""

        self.tab_widget.cancel_skill_selection()

    def _get_tab_header_anchor(self, tab_bar: QTabBar, tab_index: int) -> QWidget:
        """탭 헤더 앵커 반환"""

        rect: QRect = tab_bar.tabRect(tab_index)
        if rect.isNull() or rect.isEmpty():
            return tab_bar

        anchor: QWidget | None = getattr(self, "_tab_header_anchor", None)
        if anchor is None or anchor.parent() is not tab_bar:
            anchor = QWidget(tab_bar)
            anchor.setObjectName("tabHeaderAnchor")
            anchor.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            anchor.setStyleSheet("background: transparent;")
            anchor.show()
            self._tab_header_anchor: QWidget = anchor

        anchor.setGeometry(rect)
        anchor.raise_()
        return anchor

    def get_key_button(self, index: int) -> QPushButton:
        """공용키 버튼 반환"""

        return self.tab_widget.get_key_button(index)


class TabWidget(QTabWidget):
    noticeRequested = Signal(object)
    skillKeyRequested = Signal(int)
    scrollSelectRequested = Signal(int)
    dataChanged = Signal()
    skillUnequipped = Signal(str)

    def __init__(self, master: QWidget, popup_manager: PopupManager) -> None:
        super().__init__(master)

        self.popup_manager: PopupManager = popup_manager
        self.setTabsClosable(True)
        self._setup_add_tab_button()
        self._apply_tab_style()
        self._init_tabs()

        tab_bar: QTabBar | None = self.tabBar()
        if tab_bar is not None:
            tab_bar.setFont(CustomFont(12))

    def _setup_add_tab_button(self) -> None:
        """탭 추가 버튼 구성"""

        self.add_tab_button: QPushButton = QPushButton()
        self.add_tab_button.setIcon(
            QIcon(QPixmap(convert_resource_path("resources\\image\\plus.png")))
        )
        self.add_tab_button.setFixedSize(QSize(26, 26))
        self.add_tab_button.setCursor(Qt.CursorShape.PointingHandCursor)

        corner_container: QWidget = QWidget()
        corner_layout: QVBoxLayout = QVBoxLayout(corner_container)
        corner_layout.setContentsMargins(1, 1, 1, 1)
        corner_layout.addWidget(
            self.add_tab_button,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        self.setCornerWidget(corner_container, Qt.Corner.TopRightCorner)

    def _create_tab(self, preset: MacroPreset, preset_index: int) -> Tab:
        """탭 위젯 생성"""

        return Tab(
            preset=preset,
            preset_index=preset_index,
            popup_manager=self.popup_manager,
        )

    def add_tab(self, preset: MacroPreset) -> None:
        """탭 추가"""

        preset_index: int = self.count()
        new_tab: Tab = self._create_tab(preset, preset_index)
        self._connect_tab_signals(new_tab)
        index: int = self.addTab(new_tab, preset.name)
        self.setCurrentIndex(index)
        update_recent_preset(index)
        new_tab.update_from_preset()

    def _connect_tab_signals(self, tab: Tab) -> None:
        """하위 탭 시그널 연결"""

        tab.noticeRequested.connect(self.noticeRequested.emit)
        tab.skillKeyRequested.connect(self.skillKeyRequested.emit)
        tab.scrollSelectRequested.connect(self.scrollSelectRequested.emit)
        tab.dataChanged.connect(self.dataChanged.emit)
        tab.skillUnequipped.connect(self.skillUnequipped.emit)

    def _init_tabs(self) -> None:
        """초기 탭 구성"""

        for index, preset in enumerate(app_state.macro.presets):
            tab: Tab = self._create_tab(preset, preset_index=index)
            self._connect_tab_signals(tab)
            self.addTab(tab, preset.name)

        self.setCurrentIndex(app_state.macro.current_preset_index)
        self.get_current_tab().update_from_preset()

    def remove_tab(self, index: int) -> None:
        """탭 제거"""

        self.removeTab(index)
        self._reindex_tabs()

    def _reindex_tabs(self) -> None:
        """탭 인덱스 재정렬"""

        for index in range(self.count()):
            tab: Tab = self.widget(index)  # type: ignore[assignment]
            tab.preset_index = index

    def _apply_tab_style(self) -> None:
        """탭 스타일 적용"""

        tab_background_color: str = "#eeeeff"
        tab_border_color: str = "#cccccc"
        tab_default_color: str = "#eeeeee"
        tab_hover_color: str = "#dddddd"

        self.setStyleSheet(
            f"""
        QTabWidget {{
            background: {tab_background_color};
            border: 1px solid {tab_border_color};
            border-radius: 10px;
        }}

        QTabWidget::pane {{
            border: 1px solid {tab_border_color};
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
            border-top-right-radius: 10px;
            background: {tab_background_color};
        }}

        QTabBar::tab {{
            background: {tab_default_color};
            border: 1px solid {tab_border_color};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 10px;
            margin-top: 0px;
        }}

        QTabBar::tab:selected {{
            background: {tab_background_color};
        }}

        QTabBar::tab:hover {{
            background: {tab_hover_color};
        }}

        QTabBar::close-button {{
            image: url({convert_resource_path("resources\\image\\x.png").replace("\\", "/")});
            border-radius: 5px;
        }}

        QTabBar::close-button:hover {{
            background-color: #FF5555;
        }}

        QTabBar::close-button:pressed {{
            background-color: #CC0000;
        }}
        """
        )

        self.add_tab_button.setStyleSheet(
            f"""
            QPushButton {{
                border: 1px solid {tab_border_color};
                background: {tab_background_color};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {tab_hover_color};
            }}
            """
        )

    def get_current_tab(self) -> Tab:
        """현재 탭 반환"""

        return self.currentWidget()  # type: ignore[return-value]

    def cancel_skill_selection(self) -> None:
        """선택 취소"""

        self.get_current_tab().cancel_skill_selection()

    def get_tab_bar(self) -> QTabBar:
        """탭바 반환"""

        tab_bar: QTabBar | None = self.tabBar()
        if tab_bar is None:
            raise RuntimeError("QTabWidget.tabBar() returned None")

        return tab_bar

    def get_key_button(self, index: int) -> QPushButton:
        """공용키 버튼 반환"""

        return self.get_current_tab().get_key_button(index)


class Tab(QFrame):
    noticeRequested = Signal(object)
    skillKeyRequested = Signal(int)
    scrollSelectRequested = Signal(int)
    dataChanged = Signal()
    skillUnequipped = Signal(str)

    def __init__(
        self,
        preset: MacroPreset,
        preset_index: int,
        popup_manager: PopupManager,
    ) -> None:
        super().__init__()

        self.preset: MacroPreset = preset
        self.preset_index: int = preset_index
        self.popup_manager: PopupManager = popup_manager

        self.preview: SkillPreview = SkillPreview()
        self.available_skills: AvailableSkillPanel = AvailableSkillPanel(
            self.popup_manager
        )
        self.placed_skills: PlacedSkillPanel = PlacedSkillPanel(self.popup_manager)

        divider: QFrame = QFrame(self)
        divider.setStyleSheet("QFrame { background-color: #b4b4b4; }")
        divider.setFixedHeight(1)

        self.available_skills.scrollClicked.connect(self.on_scroll_clicked)
        self.available_skills.skillClicked.connect(self.on_available_skill_clicked)
        self.placed_skills.slotClicked.connect(self.on_placed_skill_clicked)
        self.placed_skills.keyClicked.connect(self.on_skill_key_clicked)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.available_skills)
        layout.addWidget(divider)
        layout.addWidget(self.placed_skills)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)
        self.setLayout(layout)

        self.update_from_preset()

    def cancel_skill_selection(self) -> None:
        """하단 배치 선택 취소"""

        self.select_placed_skill(None)

    def on_skill_key_clicked(self, index: int) -> None:
        """공용키 버튼 클릭"""

        if app_state.macro.is_running:
            self.noticeRequested.emit(NoticeKind.MACRO_IS_RUNNING)
            return

        self.skillKeyRequested.emit(index)

    def on_scroll_clicked(self, scroll_index: int) -> None:
        """상단 스크롤 버튼 클릭"""

        if app_state.ui.current_sidebar_page == 4:
            self.noticeRequested.emit(NoticeKind.EDITING_LINK_SKILL)
            return

        if app_state.macro.is_running:
            self.noticeRequested.emit(NoticeKind.MACRO_IS_RUNNING)
            return

        self.scrollSelectRequested.emit(scroll_index)

    def on_placed_skill_clicked(self, skill_ref: EquippedSkillRef) -> None:
        """하단 스킬 슬롯 클릭"""

        if app_state.ui.current_sidebar_page == 4:
            self.cancel_skill_selection()
            self.noticeRequested.emit(NoticeKind.EDITING_LINK_SKILL)
            return

        if app_state.macro.is_running:
            self.cancel_skill_selection()
            self.noticeRequested.emit(NoticeKind.MACRO_IS_RUNNING)
            return

        placed_skill_id: str = self.preset.skills.get_placed_skill_id(
            skill_ref,
        )
        selected_ref: EquippedSkillRef | None = self.get_selected_skill_ref()

        if selected_ref is None:
            self.select_placed_skill(skill_ref)
            return

        if selected_ref != skill_ref:
            self.select_placed_skill(skill_ref)
            return

        if not placed_skill_id:
            self.cancel_skill_selection()
            return

        # 현재 하단 슬롯에서 제거되는 스킬의 파생 설정 정리
        self.clear_placed_skill(placed_skill_id)
        self.set_placed_skill(skill_ref, "")
        self.cancel_skill_selection()
        self.dataChanged.emit()

    def on_available_skill_clicked(self, skill_ref: EquippedSkillRef) -> None:
        """상단 제공 스킬 클릭"""

        if app_state.ui.current_sidebar_page == 4:
            self.cancel_skill_selection()
            self.noticeRequested.emit(NoticeKind.EDITING_LINK_SKILL)
            return

        if app_state.macro.is_running:
            self.cancel_skill_selection()
            self.noticeRequested.emit(NoticeKind.MACRO_IS_RUNNING)
            return

        selected_ref: EquippedSkillRef | None = self.get_selected_skill_ref()
        if selected_ref is None:
            return

        selected_skill_id: str = self.preset.skills.get_available_skill_id(
            app_state.macro.current_server,
            skill_ref,
        )
        if not selected_skill_id:
            return

        # 현재 장착된 스크롤이 제공하는 스킬만 배치 대상으로 허용
        available_skill_ids: list[str] = self.preset.skills.get_available_skill_ids(
            app_state.macro.current_server
        )
        if selected_skill_id not in available_skill_ids:
            self.cancel_skill_selection()
            return

        # 이미 다른 하단 슬롯에 배치된 스킬은 중복 배치 금지
        if selected_skill_id in self.preset.skills.get_placed_skill_ids():
            self.cancel_skill_selection()
            return

        current_skill_id: str = self.preset.skills.get_placed_skill_id(
            selected_ref,
        )
        if current_skill_id:
            # 같은 슬롯 재배치 전 기존 스킬의 파생 설정 우선 정리
            self.clear_placed_skill(current_skill_id)

        self.set_placed_skill(selected_ref, selected_skill_id)
        self.cancel_skill_selection()
        self.dataChanged.emit()

    def apply_scroll(self, scroll_index: int, scroll_id: str) -> bool:
        """스크롤 장착 적용"""

        current_scroll_id: str = self.preset.skills.equipped_scrolls[scroll_index]
        if current_scroll_id == scroll_id:
            return False

        if scroll_id in self.preset.skills.equipped_scrolls:
            return False

        if current_scroll_id:
            # 교체 전 스크롤이 제공하던 두 스킬만 하단 배치에서 제거
            current_scroll_def: ScrollDef = (
                app_state.macro.current_server.skill_registry.get_scroll(
                    current_scroll_id
                )
            )
            for skill_id in current_scroll_def.skills:
                self.clear_skill_if_placed(skill_id)

        self.preset.skills.equipped_scrolls[scroll_index] = scroll_id
        self._sync_to_shared_data()
        self.update_from_preset()
        return True

    def clear_skill_if_placed(self, skill_id: str) -> None:
        """기존 배치 스킬 제거"""

        placed_skill_ids: list[str] = self.preset.skills.get_placed_skill_ids()
        if skill_id not in placed_skill_ids:
            return

        # 스킬 ID 기준 배치 위치를 찾아 실제 슬롯과 파생 설정을 함께 정리
        skill_ref_map: dict[str, EquippedSkillRef] = (
            self.preset.skills.get_placed_skill_ref_map(app_state.macro.current_server)
        )
        target_ref: EquippedSkillRef = skill_ref_map[skill_id]
        self.clear_placed_skill(skill_id)
        self.set_placed_skill(target_ref, "")

    def clear_placed_skill(self, skill_id: str) -> None:
        """배치 해제 파생 설정 정리"""

        for link in self.preset.link_skills:
            if skill_id in link.skills:
                link.set_manual()
                link.clear_key()

        setting: SkillUsageSetting = self.preset.usage_settings[skill_id]
        previous_priority: int = setting.priority

        if previous_priority:
            self.preset.usage_settings[skill_id].priority = 0

            placed_skill_ids: list[str] = self.preset.skills.get_placed_skill_ids()

            for placed_skill_id in placed_skill_ids:
                usage_setting: SkillUsageSetting = self.preset.usage_settings[
                    placed_skill_id
                ]
                if usage_setting.priority > previous_priority:
                    usage_setting.priority -= 1

        self.skillUnequipped.emit(skill_id)

    def select_placed_skill(self, skill_ref: EquippedSkillRef | None) -> None:
        """하단 슬롯 선택"""

        self.placed_skills.select(skill_ref)

    def set_placed_skill(self, skill_ref: EquippedSkillRef, skill_id: str) -> None:
        """하단 슬롯 스킬 적용"""

        # 하단 14칸 수동 배치 상태만 실제 저장 필드에 반영
        self.preset.skills.placed_skills[skill_ref.flat_index] = skill_id
        self._sync_to_shared_data()
        self.update_from_preset()

    def get_selected_skill_ref(self) -> EquippedSkillRef | None:
        """선택된 하단 슬롯 반환"""

        return self.placed_skills.get_selected_skill_ref()

    def get_key_button(self, index: int) -> QPushButton:
        """공용키 버튼 반환"""

        return self.placed_skills.get_key_button(index)

    def get_scroll_button(self, index: int) -> QPushButton:
        """스크롤 버튼 반환"""

        return self.available_skills.get_scroll_button(index)

    def update_preview(self) -> None:
        """프리뷰 갱신"""

        self.preview.update_preview()

    def update_from_preset(self) -> None:
        """프리셋 기준 UI 동기화"""

        selected_ref: EquippedSkillRef | None = self.get_selected_skill_ref()
        self.available_skills.update_from_preset(self.preset)
        self.placed_skills.update_from_preset(self.preset)
        self.placed_skills.select(selected_ref)
        self.update_preview()

    def apply_key(self, index: int, key: KeySpec) -> bool:
        """공용키 적용"""

        if self.preset.skills.skill_keys[index] == key.key_id:
            return False

        self.preset.skills.skill_keys[index] = key.key_id
        self._sync_to_shared_data()
        self.placed_skills.set_key(index, key.display)
        return True

    def _sync_to_shared_data(self) -> None:
        """현재 프리셋 저장 인덱스 동기화"""

        update_recent_preset(self.preset_index)


class SkillPreview(QFrame):
    """다음 실행 스킬 프리뷰"""

    def __init__(self) -> None:
        super().__init__()

        self.setStyleSheet(
            """
            QFrame {
                background-color: #ffffff;
                border-radius: 5px;
                border: 1px solid black;
            }
            """
        )
        self.setFixedHeight(58)
        self.setMinimumWidth(200)

        self.skills: list[SkillImage] = []
        self.previous_task_list: tuple[EquippedSkillRef, ...] = ()

        self.skills_layout: QHBoxLayout = QHBoxLayout()
        self.skills_layout.setContentsMargins(6, 6, 6, 6)
        self.skills_layout.setSpacing(6)
        self.skills_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.skills_layout)

    def update_preview(self) -> None:
        """프리뷰 갱신"""

        if not app_state.macro.is_running:
            init_macro()

        task_list: tuple[EquippedSkillRef, ...] = build_preview_task_list()
        if task_list == self.previous_task_list:
            return

        self.previous_task_list = task_list

        for icon in self.skills:
            icon.deleteLater()
            self.skills_layout.removeWidget(icon)

        self.skills.clear()

        for skill_ref in task_list[:6]:
            skill_id: str = app_state.macro.current_preset.skills.get_placed_skill_id(
                skill_ref
            )
            if not skill_id:
                continue

            skill: SkillImage = SkillImage(
                parent=self,
                pixmap=resource_registry.get_skill_pixmap(skill_id=skill_id),
                size=44,
            )
            self.skills.append(skill)
            self.skills_layout.addWidget(skill)


class AvailableSkillPanel(QFrame):
    """상단 장착 스크롤과 사용 가능 스킬 패널"""

    scrollClicked = Signal(int)
    skillClicked = Signal(object)

    def __init__(self, popup_manager: PopupManager) -> None:
        super().__init__()

        self.popup_manager: PopupManager = popup_manager
        self.columns: list[AvailableSkillPanel.Column] = []
        self.setStyleSheet("QFrame { background-color: transparent; }")

        layout: QHBoxLayout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        for scroll_index in range(app_state.macro.current_server.scroll_slot_count):
            column: AvailableSkillPanel.Column = AvailableSkillPanel.Column(
                scroll_index=scroll_index,
                popup_manager=self.popup_manager,
            )
            column.scrollClicked.connect(self.scrollClicked.emit)
            column.skillClicked.connect(self.skillClicked.emit)
            self.columns.append(column)
            layout.addWidget(column)

        self.setLayout(layout)

    def update_from_preset(
        self,
        preset: MacroPreset,
    ) -> None:
        """프리셋 기준 표시 갱신"""

        for column in self.columns:
            column.update_from_preset(preset)

    def get_scroll_button(self, index: int) -> QPushButton:
        """스크롤 버튼 반환"""

        return self.columns[index].scroll_button

    class Column(QFrame):
        scrollClicked = Signal(int)
        skillClicked = Signal(object)

        def __init__(
            self,
            scroll_index: int,
            popup_manager: PopupManager,
        ) -> None:
            super().__init__()

            self.scroll_index: int = scroll_index
            self.popup_manager: PopupManager = popup_manager
            self.setStyleSheet("QFrame { background-color: transparent; }")

            self.scroll_button: QPushButton = QPushButton(self)
            self.scroll_button.setFixedSize(48, 48)
            self.scroll_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.scroll_button.clicked.connect(
                lambda: self.scrollClicked.emit(self.scroll_index)
            )
            self.popup_manager.bind_hover_card(
                self.scroll_button,
                self._build_scroll_hover_card,
            )

            self.skill_buttons: list[QPushButton] = []
            for line_index in range(app_state.macro.current_server.skill_line_count):
                button: QPushButton = QPushButton(self)
                button.setFixedSize(48, 48)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                skill_ref: EquippedSkillRef = EquippedSkillRef(
                    scroll_index=self.scroll_index,
                    line_index=line_index,
                )
                button.clicked.connect(
                    lambda _, ref=skill_ref: self.skillClicked.emit(ref)
                )
                self.popup_manager.bind_hover_card(
                    button,
                    lambda ref=skill_ref: self._build_available_skill_hover_card(ref),
                )
                self.skill_buttons.append(button)

            layout: QVBoxLayout = QVBoxLayout()
            layout.addWidget(self.scroll_button, alignment=Qt.AlignmentFlag.AlignCenter)
            for button in self.skill_buttons:
                layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)
            self.setLayout(layout)

        def update_from_preset(
            self,
            preset: MacroPreset,
        ) -> None:
            """컬럼 표시 갱신"""

            scroll_id: str = preset.skills.equipped_scrolls[self.scroll_index]
            self.scroll_button.setIcon(
                QIcon(resource_registry.get_scroll_pixmap(scroll_id or None))
            )
            self.scroll_button.setIconSize(QSize(48, 48))
            self.scroll_button.setStyleSheet(
                "QPushButton { border: 0px; background-color: transparent; }"
            )

            for line_index, button in enumerate(self.skill_buttons):
                skill_ref: EquippedSkillRef = EquippedSkillRef(
                    scroll_index=self.scroll_index,
                    line_index=line_index,
                )
                skill_id: str = preset.skills.get_available_skill_id(
                    app_state.macro.current_server,
                    skill_ref,
                )
                button.setIcon(
                    QIcon(resource_registry.get_skill_pixmap(skill_id or None))
                )
                button.setIconSize(QSize(48, 48))
                button.setStyleSheet(
                    "QPushButton { border: 0px; background-color: transparent; }"
                )

        def _build_scroll_hover_card(self) -> HoverCardData | None:
            """현재 컬럼 스크롤 기준 호버 카드 구성"""

            # 스크롤 미장착 상태에서는 카드 대신 기본 안내 숨김 처리
            preset: MacroPreset = app_state.macro.current_preset
            scroll_id: str = preset.skills.equipped_scrolls[self.scroll_index]

            if not scroll_id:
                return None

            scroll_def: ScrollDef = (
                app_state.macro.current_server.skill_registry.get_scroll(scroll_id)
            )
            level: int = preset.info.get_scroll_level(scroll_def.id)
            return self.popup_manager.build_scroll_hover_card(scroll_def, level)

        def _build_available_skill_hover_card(
            self,
            skill_ref: EquippedSkillRef,
        ) -> HoverCardData | None:
            """상단 제공 스킬 기준 호버 카드 구성"""

            # 현재 프리셋에 실제로 노출되는 스킬만 카드 표시
            preset: MacroPreset = app_state.macro.current_preset
            skill_id: str = preset.skills.get_available_skill_id(
                app_state.macro.current_server,
                skill_ref,
            )

            if not skill_id:
                return None

            level: int = preset.info.get_skill_level(
                app_state.macro.current_server,
                skill_id,
            )
            return self.popup_manager.build_skill_hover_card(skill_id, level)


class PlacedSkillPanel(QFrame):
    """하단 실제 배치 스킬 패널"""

    SLOT_BUTTON_SIZE: int = 48
    SLOT_SELECTED_BUTTON_SIZE: int = 56
    slotClicked = Signal(object)
    keyClicked = Signal(int)

    def __init__(self, popup_manager: PopupManager) -> None:
        super().__init__()

        self.popup_manager: PopupManager = popup_manager
        self.selected_ref: EquippedSkillRef | None = None
        self.columns: list[PlacedSkillPanel.Column] = []
        self.setStyleSheet("QFrame { background-color: transparent; }")

        layout: QHBoxLayout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        for scroll_index in range(app_state.macro.current_server.scroll_slot_count):
            column: PlacedSkillPanel.Column = PlacedSkillPanel.Column(
                scroll_index=scroll_index,
                popup_manager=self.popup_manager,
            )
            column.slotClicked.connect(self.slotClicked.emit)
            column.keyClicked.connect(self.keyClicked.emit)
            self.columns.append(column)
            layout.addWidget(column)

        self.setLayout(layout)

    def select(self, skill_ref: EquippedSkillRef | None) -> None:
        """선택 상태 반영"""

        self.selected_ref = skill_ref
        for column in self.columns:
            column.set_selected(skill_ref)

    def get_selected_skill_ref(self) -> EquippedSkillRef | None:
        """선택된 슬롯 반환"""

        return self.selected_ref

    def set_key(self, index: int, key: str) -> None:
        """공용키 텍스트 반영"""

        self.columns[index].set_key(key)

    def get_key_button(self, index: int) -> QPushButton:
        """공용키 버튼 반환"""

        return self.columns[index].get_key_button()

    def update_from_preset(self, preset: MacroPreset) -> None:
        """프리셋 기준 표시 갱신"""

        for scroll_index, column in enumerate(self.columns):
            column.update_from_preset(preset, scroll_index)

    class Column(QFrame):
        slotClicked = Signal(object)
        keyClicked = Signal(int)

        def __init__(
            self,
            scroll_index: int,
            popup_manager: PopupManager,
        ) -> None:
            super().__init__()

            self.scroll_index: int = scroll_index
            self.popup_manager: PopupManager = popup_manager
            self.buttons: list[QPushButton] = []
            self.button_containers: list[QWidget] = []

            self.setStyleSheet("QFrame { background-color: transparent; }")

            layout: QVBoxLayout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            for line_index in range(app_state.macro.current_server.skill_line_count):
                # 선택 강조 최대 크기만큼 슬롯 영역 선점
                button_container: QWidget = QWidget(self)
                button_container.setFixedSize(
                    PlacedSkillPanel.SLOT_SELECTED_BUTTON_SIZE,
                    PlacedSkillPanel.SLOT_SELECTED_BUTTON_SIZE,
                )

                # 기본 상태에서는 기존과 동일한 48px 버튼 유지
                container_layout: QVBoxLayout = QVBoxLayout(button_container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(0)
                button: QPushButton = QPushButton(self)
                button.setFixedSize(
                    PlacedSkillPanel.SLOT_BUTTON_SIZE,
                    PlacedSkillPanel.SLOT_BUTTON_SIZE,
                )
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                skill_ref: EquippedSkillRef = EquippedSkillRef(
                    scroll_index=self.scroll_index,
                    line_index=line_index,
                )
                button.clicked.connect(
                    lambda _, ref=skill_ref: self.slotClicked.emit(ref)
                )
                self.popup_manager.bind_hover_card(
                    button,
                    lambda ref=skill_ref: self._build_placed_skill_hover_card(ref),
                )

                self.buttons.append(button)
                self.button_containers.append(button_container)
                container_layout.addWidget(
                    button,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                )
                layout.addWidget(
                    button_container,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                )

            self.key_button: QPushButton = QPushButton("", self)
            self.key_button.setFont(CustomFont(10))
            self.key_button.setFixedWidth(48)
            self.key_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.key_button.clicked.connect(
                lambda: self.keyClicked.emit(self.scroll_index)
            )
            layout.addWidget(self.key_button, alignment=Qt.AlignmentFlag.AlignCenter)
            self.setLayout(layout)

        def update_from_preset(self, preset: MacroPreset, scroll_index: int) -> None:
            """컬럼 아이콘/키 갱신"""

            for line_index, button in enumerate(self.buttons):
                skill_ref: EquippedSkillRef = EquippedSkillRef(
                    scroll_index=scroll_index,
                    line_index=line_index,
                )
                skill_id: str = preset.skills.get_placed_skill_id(
                    skill_ref,
                )
                button.setIcon(
                    QIcon(resource_registry.get_skill_pixmap(skill_id or None))
                )
                button.setIconSize(QSize(48, 48))
                button.setStyleSheet(
                    "QPushButton { border: 0px; background-color: transparent; }"
                )

            self.set_key(
                KeyRegistry.get(preset.skills.skill_keys[scroll_index]).display
            )

        def _build_placed_skill_hover_card(
            self,
            skill_ref: EquippedSkillRef,
        ) -> HoverCardData | None:
            """하단 배치 슬롯 기준 호버 카드 구성"""

            # 실제 배치된 스킬이 있는 슬롯에서만 카드 표시
            preset: MacroPreset = app_state.macro.current_preset
            skill_id: str = preset.skills.get_placed_skill_id(skill_ref)

            if not skill_id:
                return None

            level: int = preset.info.get_skill_level(
                app_state.macro.current_server,
                skill_id,
            )
            return self.popup_manager.build_skill_hover_card(skill_id, level)

        def set_selected(self, selected_ref: EquippedSkillRef | None) -> None:
            """선택 강조 반영"""

            for line_index, button in enumerate(self.buttons):
                skill_ref: EquippedSkillRef = EquippedSkillRef(
                    scroll_index=self.scroll_index,
                    line_index=line_index,
                )
                is_selected: bool = (
                    selected_ref is not None and selected_ref == skill_ref
                )

                if is_selected:
                    # 고정 슬롯 내부에서만 선택 강조 크기 확대
                    button.setFixedSize(
                        PlacedSkillPanel.SLOT_SELECTED_BUTTON_SIZE,
                        PlacedSkillPanel.SLOT_SELECTED_BUTTON_SIZE,
                    )
                    button.setIconSize(
                        QSize(
                            PlacedSkillPanel.SLOT_SELECTED_BUTTON_SIZE,
                            PlacedSkillPanel.SLOT_SELECTED_BUTTON_SIZE,
                        )
                    )

                    shadow = QGraphicsDropShadowEffect(button)
                    shadow.setBlurRadius(8)
                    shadow.setOffset(2, 2)
                    shadow.setColor(QColor(0, 0, 0, 160))
                    button.setGraphicsEffect(shadow)

                else:
                    # 비선택 상태 기본 크기 복원
                    button.setFixedSize(
                        PlacedSkillPanel.SLOT_BUTTON_SIZE,
                        PlacedSkillPanel.SLOT_BUTTON_SIZE,
                    )
                    button.setIconSize(
                        QSize(
                            PlacedSkillPanel.SLOT_BUTTON_SIZE,
                            PlacedSkillPanel.SLOT_BUTTON_SIZE,
                        )
                    )

                    button.setGraphicsEffect(None)  # type: ignore

        def set_key(self, key: str) -> None:
            """공용키 텍스트 반영"""

            self.key_button.setText(key)

        def get_key_button(self) -> QPushButton:
            """공용키 버튼 반환"""

            return self.key_button
