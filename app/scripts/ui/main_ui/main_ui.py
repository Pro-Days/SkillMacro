from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.scripts.custom_classes import CustomFont, SkillImage
from app.scripts.data_manager import (
    add_preset,
    apply_preset_to_shared_data,
    load_data,
    remove_preset,
    save_data,
    select_preset,
    update_recent_preset,
)
from app.scripts.macro_models import LinkUseType, MacroPreset, SkillUsageSetting
from app.scripts.misc import (
    convert_resource_path,
    get_every_skills,
    get_skill_name,
    get_skill_pixmap,
)
from app.scripts.popup import PopupManager
from app.scripts.run_macro import add_task_list, init_macro
from app.scripts.shared_data import UI_Variable

if TYPE_CHECKING:
    from app.scripts.macro_models import MacroPreset
    from app.scripts.main_window import MainWindow
    from app.scripts.shared_data import KeySpec, SharedData


class MainUI(QFrame):
    presetChanged = pyqtSignal(object, int)

    def __init__(
        self,
        master: MainWindow,
        shared_data: SharedData,
    ) -> None:
        super().__init__()

        self.master: MainWindow = master
        self.popup_manager: PopupManager = master.get_popup_manager()

        self.shared_data: SharedData = shared_data
        self.ui_var = UI_Variable()

        self.tab_widget = TabWidget(self, self.shared_data)

        # Tab 내부 이벤트를 MainUI에서 처리
        # 매크로 작동 중 팝업 요청
        self.tab_widget.noticeRequested.connect(self.popup_manager.make_notice_popup)
        # 키 설정 팝업 요청
        self.tab_widget.skillKeyRequested.connect(self.on_skill_key_clicked)
        # 데이터 변경 신호
        self.tab_widget.dataChanged.connect(lambda: save_data(self.shared_data))

        # 기능 함수들 연결
        # 탭 클릭시
        tab_bar: QTabBar = self.tab_widget.get_tab_bar()
        tab_bar.tabBarClicked.connect(self.on_tab_clicked)
        # 탭이 실제로 변경되었을 때(클릭/코드 변경 모두 포함)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        # 탭 추가버튼 클릭시
        self.tab_widget.add_tab_button.clicked.connect(self.on_add_tab_clicked)
        # 탭 닫기 버튼 클릭시
        self.tab_widget.tabCloseRequested.connect(self.on_remove_tab_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        layout.setContentsMargins(30, 30, 30, 10)
        layout.setSpacing(0)
        self.setLayout(layout)

    def emit_preset_changed(self) -> None:
        """Emit presetChanged for the currently selected tab.

        Useful for initial UI sync after other widgets (e.g., Sidebar) connect.
        """

        index: int = self.tab_widget.currentIndex()
        if not self.shared_data.presets or not (
            0 <= index < len(self.shared_data.presets)
        ):
            return

        self.presetChanged.emit(self.shared_data.presets[index], index)

    def on_tab_changed(self, index: int) -> None:
        """탭이 바뀌었을 때 실행"""

        # 프리셋 선택
        select_preset(self.shared_data, index)

        # 마지막으로 선택한 탭이 다음 실행에도 복원되도록 recent_preset만 최소 저장
        update_recent_preset(self.shared_data, index)

        # 로드된 shared_data 기준으로 현재 탭 UI를 갱신
        self.tab_widget.get_current_tab().update_from_preset()

        # 사이드바 등 외부 UI에 현재 preset 컨텍스트 전달
        if self.shared_data.presets and 0 <= index < len(self.shared_data.presets):
            self.presetChanged.emit(self.shared_data.presets[index], index)

        # 탭 제목/내용을 로드된 shared_data 기준으로 동기화
        # self.tab_widget.sync_tab_titles(self.shared_data.tab_names)

        # 사이드바 업데이트
        # self.sidebar.set_index(0)
        # self.sidebar.update_content()

        # 선택중인 스킬이 있었다면 취소
        self.cancel_skill_selection()

    def on_tab_clicked(self, index: int) -> None:
        """탭 클릭시 실행"""

        def apply_tab_name(new_name: str) -> None:
            """탭 이름 적용"""

            # 프리셋/호환 데이터 반영
            if self.shared_data.presets and 0 <= index < len(self.shared_data.presets):
                self.shared_data.presets[index].name = new_name
            if self.shared_data.tab_names and 0 <= index < len(
                self.shared_data.tab_names
            ):
                self.shared_data.tab_names[index] = new_name

            # 탭 라벨 반영
            self.tab_widget.setTabText(index, new_name)

            save_data(self.shared_data)

        # 활성화 상태인 팝업 닫기
        self.popup_manager.close_popup()

        # 매크로 실행중일 때는 탭 변경 불가
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 같은 탭 클릭시 탭 이름 변경 팝업
        if index == self.tab_widget.currentIndex():
            tab_bar: QTabBar = self.tab_widget.get_tab_bar()
            anchor: QWidget = self._get_tab_header_anchor(
                tab_bar=tab_bar, tab_index=index
            )
            self.popup_manager.make_tab_name_popup(anchor, index, apply_tab_name)

            return

    def on_add_tab_clicked(self) -> None:
        """탭 추가버튼 클릭시 실행"""

        # 활성화 상태인 팝업 닫기
        self.popup_manager.close_popup()

        # 매크로 실행중일 때는 탭 추가 불가
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")

            return

        self.add_new_tab()

    def add_new_tab(self) -> None:
        """새 탭 추가 함수"""

        # 데이터 추가(파일 + 메모리 presets 동시 반영)
        add_preset(shared_data=self.shared_data)

        # 탭 추가 (마지막 프리셋)
        preset: MacroPreset = self.shared_data.presets[-1]
        self.tab_widget.add_tab(preset)

    def on_remove_tab_clicked(self, index: int) -> None:
        """탭 닫기 버튼 클릭시 실행"""
        # 탭 닫기 버튼 클릭시 바로 탭이 제거되지 않고, 나중에 다시 열 수 있도록 수정
        # 탭 삭제 / 열기 기능을 추가해야함.
        # 이 방식을 사용하면 탭 제거 팝업을 띄우지 않음.

        # 활성화 상태인 팝업 닫기
        # self.master.get_popup_manager().close_popup()

        # 매크로 실행중일 때는 탭 제거 불가
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")

            return

        # 탭 제거 팝업이 활성화되어있지 않을 때만 팝업 생성
        # if self.shared_data.is_tab_remove_popup_activated:
        #     return

        # self.shared_data.is_tab_remove_popup_activated = True

        # # 탭 제거 팝업 생성
        # self.remove_confirmation_popup = ConfirmRemovePopup(
        #     self, self.tab_widget.tabText(index), index
        # )

        self.on_remove_tab_popup_clicked(index, True)

    def on_remove_tab_popup_clicked(self, index: int, confirmed: bool) -> None:
        """탭 제거 팝업창에서 예/아니오 클릭시 실행"""

        # 탭이 삭제되면 기존 인덱스와 달리지기 때문에 인덱스 대신 객체를 기반으로 탭을 찾도록 수정 필요

        # 팝업 제거
        # self.remove_confirmation_popup.deleteLater()

        # 탭 제거 팝업 활성화 상태 초기화
        # self.shared_data.is_tab_remove_popup_activated = False

        # 아니오 클릭시 리턴
        if not confirmed:
            return

        # 탭 제거(파일 + 메모리 presets 동시 반영)
        self.tab_widget.remove_tab(index)
        remove_preset(index, self.shared_data)

        # 탭이 하나도 없으면 새 탭 추가
        tab_count: int = self.tab_widget.count()
        if not tab_count:
            self.add_new_tab()
            return

        # 삭제 후 현재 탭 프리셋 선택
        new_index: int = self.tab_widget.currentIndex()
        select_preset(self.shared_data, new_index)
        self.tab_widget.get_current_tab().update_from_preset()

    def on_skill_key_clicked(self, index: int) -> None:
        """스킬 단축키 설정 버튼 클릭시 실행"""

        def apply(key: KeySpec) -> None:
            """적용 함수"""

            current_tab: Tab = self.tab_widget.get_current_tab()
            if current_tab.apply_key(index, key):
                save_data(self.shared_data)

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        self.popup_manager.make_skill_key_popup(
            self.get_key_button(index), index, apply
        )

    def cancel_skill_selection(self) -> None:
        """
        스킬 장착 취소. 다른 곳 클릭시 실행됨
        """

        self.tab_widget.cancel_skill_selection()

    def _get_tab_header_anchor(self, tab_bar: QTabBar, tab_index: int) -> QWidget:
        """QTabBar의 특정 탭 영역(tabRect)에 맞춘 앵커 위젯을 반환"""

        rect: QRect = tab_bar.tabRect(tab_index)
        if rect.isNull() or rect.isEmpty():
            return tab_bar

        # 앵커 위젯 생성 및 재사용
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
        """단축키 설정 버튼 반환"""

        return self.tab_widget.get_key_button(index)

    def set_key(self, index: int, key: str) -> None:
        """스킬 단축키 설정"""

        self.tab_widget.set_key(index, key)


class TabWidget(QTabWidget):
    noticeRequested = pyqtSignal(str)
    skillKeyRequested = pyqtSignal(int)
    dataChanged = pyqtSignal()
    skillUnequipped = pyqtSignal(str)

    def __init__(self, master: QWidget, shared_data: SharedData):
        super().__init__(master)

        self.shared_data: SharedData = shared_data

        # 탭 닫기 버튼 활성화
        self.setTabsClosable(True)

        # 우측 상단 탭 추가 버튼 설정
        self._setup_add_tab_button()

        # 탭 및 스타일 초기화
        self._apply_tab_style()

        # 초기 탭 설정
        self._init_tabs()

        tab_bar: QTabBar | None = self.tabBar()
        if tab_bar is not None:
            tab_bar.setFont(CustomFont(12))

    def _setup_add_tab_button(self) -> None:
        """
        탭 목록 오른쪽에 고정된 탭 추가 버튼 설정
        """

        self.add_tab_button = QPushButton()
        self.add_tab_button.setIcon(
            QIcon(QPixmap(convert_resource_path("resources\\image\\plus.png")))
        )
        self.add_tab_button.setFixedSize(QSize(26, 26))
        self.add_tab_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # 탭 추가 버튼을 담을 컨테이너 위젯 생성
        corner_container = QWidget()
        corner_layout = QVBoxLayout(corner_container)
        corner_layout.setContentsMargins(1, 1, 1, 1)
        corner_layout.addWidget(
            self.add_tab_button, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # 우측 상단 코너에 컨테이너 위젯 설정
        self.setCornerWidget(corner_container, Qt.Corner.TopRightCorner)

    def _create_tab(self, preset: "MacroPreset", preset_index: int) -> "Tab":
        """
        새 탭 생성
        """
        return Tab(self.shared_data, preset=preset, preset_index=preset_index)

    def add_tab(self, preset: "MacroPreset") -> None:
        """
        새로운 탭 생성 후 QTabWidget에 추가
        """

        preset_index: int = self.count()
        self.tab_count += 1

        new_tab: Tab = self._create_tab(preset, preset_index=preset_index)

        # 탭 시그널 연결
        self._connect_tab_signals(new_tab)

        # QTabWidget에 탭 추가
        index: int = self.addTab(new_tab, preset.name)

        # 새로 추가된 탭으로 이동
        self.setCurrentIndex(index)

        # 새 탭을 현재 탭으로 만들고 shared_data를 해당 preset으로 동기화
        select_preset(self.shared_data, index)
        new_tab.update_from_preset()

    def _connect_tab_signals(self, tab: "Tab") -> None:
        tab.noticeRequested.connect(self.noticeRequested.emit)
        tab.skillKeyRequested.connect(self.skillKeyRequested.emit)
        tab.dataChanged.connect(self.dataChanged.emit)
        tab.skillUnequipped.connect(self.skillUnequipped.emit)

    def _init_tabs(self) -> None:
        """
        초기 탭 설정
        """

        self.tab_count: int = 0

        # 기존 저장된 preset 목록을 그대로 UI에 반영
        for i, preset in enumerate(self.shared_data.presets):
            self.tab_count += 1
            tab: Tab = self._create_tab(preset, preset_index=i)
            self._connect_tab_signals(tab)
            self.addTab(tab, preset.name)

        self.setCurrentIndex(self.shared_data.recent_preset)
        select_preset(self.shared_data, self.shared_data.recent_preset)
        self.get_current_tab().update_from_preset()

    def remove_tab(self, index: int) -> None:
        """
        탭 제거
        """

        self.removeTab(index)
        self._reindex_tabs()

    def _reindex_tabs(self) -> None:
        """탭 삭제 후 Tab.preset_index 재설정"""

        for i in range(self.count()):
            w: Tab = self.widget(i)  # type: ignore
            w.preset_index = i

    def _apply_tab_style(self):
        """
        탭과 내용 영역에 스타일 시트 적용
        """

        TAB_BACKGROUND_COLOR = "#eeeeff"
        TAB_BORDER_COLOR = "#cccccc"
        TAB_DEFAULT_COLOR = "#eeeeee"
        TAB_HOVER_COLOR = "#dddddd"

        self.setStyleSheet(
            f"""
        /* QTabWidget container */
        QTabWidget {{
            background: {TAB_BACKGROUND_COLOR};
            border: 1px solid {TAB_BORDER_COLOR};
            border-radius: 10px;
        }}
        
        QTabWidget::pane {{
            border: 1px solid {TAB_BORDER_COLOR};
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
            border-top-right-radius: 10px;
            background: {TAB_BACKGROUND_COLOR};
        }}

        /* 탭 기본 설정 */
        QTabBar::tab {{
            background: {TAB_DEFAULT_COLOR};
            border: 1px solid {TAB_BORDER_COLOR};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 10px;
            margin-top: 0px;
        }}

        /* 선택된 탭 */
        QTabBar::tab:selected {{
            background: {TAB_BACKGROUND_COLOR};
        }}

        /* 탭 호버 */
        QTabBar::tab:hover {{
            background: {TAB_HOVER_COLOR};
        }}

        /* 닫기 버튼 */
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
                border: 1px solid {TAB_BORDER_COLOR};
                background: {TAB_BACKGROUND_COLOR};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {TAB_HOVER_COLOR};
            }}
            """
        )

    def get_current_tab(self) -> "Tab":
        return self.currentWidget()  # type: ignore

    def cancel_skill_selection(self) -> None:
        """현재 탭의 스킬 선택 취소"""

        tab: Tab = self.get_current_tab()
        tab.cancel_skill_selection()

    def get_tab_bar(self) -> QTabBar:
        """
        현재 TabWidget의 QTabBar를 반환
        """

        tab_bar: QTabBar | None = self.tabBar()

        if tab_bar is None:
            raise RuntimeError("QTabWidget.tabBar() returned None")

        return tab_bar

    def get_key_button(self, index: int) -> QPushButton:
        """단축키 설정 버튼 반환"""

        return self.get_current_tab().get_key_button(index)

    def set_key(self, index: int, key: str) -> None:
        """스킬 단축키 설정"""

        self.get_current_tab().set_key(index, key)


class Tab(QFrame):
    noticeRequested = pyqtSignal(str)
    skillKeyRequested = pyqtSignal(int)
    dataChanged = pyqtSignal()
    skillUnequipped = pyqtSignal(str)

    def __init__(
        self, shared_data: SharedData, preset: "MacroPreset", preset_index: int
    ) -> None:
        super().__init__()

        self.shared_data: SharedData = shared_data
        self.preset: MacroPreset = preset
        self.preset_index: int = preset_index

        self.preview = SkillPreview(shared_data=self.shared_data)

        self.equippable_skills = EquippableSkill(shared_data=self.shared_data)

        line = QFrame(self)
        line.setStyleSheet("QFrame { background-color: #b4b4b4; }")
        line.setFixedHeight(1)

        self.equipped_skills = EquippedSkill(shared_data=self.shared_data)

        # 없어도 될 수도?
        self.update_from_preset()

        # 하위 위젯 이벤트를 Tab에서 처리
        self.equipped_skills.slotClicked.connect(self.on_equipped_skill_clicked)
        self.equipped_skills.keyClicked.connect(self.on_skill_key_clicked)
        self.equippable_skills.skillClicked.connect(self.on_available_skill_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.equippable_skills)
        layout.addWidget(line)
        layout.addWidget(self.equipped_skills)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)
        self.setLayout(layout)

    def cancel_skill_selection(self) -> None:
        """장착 스킬 선택 취소"""

        self.select_equipped_skill(-1)

    def on_skill_key_clicked(self, index: int) -> None:
        """장착 슬롯 단축키 설정 버튼 클릭"""

        if self.shared_data.is_activated:
            self.noticeRequested.emit("MacroIsRunning")
            return

        self.skillKeyRequested.emit(index)

    def on_equipped_skill_clicked(self, index: int) -> None:
        """하단 장착 슬롯 클릭 처리(선택/해제)"""

        # 연계스킬 편집 중이면 수정 불가능
        if self.shared_data.sidebar_type == 4:
            self.cancel_skill_selection()
            self.noticeRequested.emit("editingLinkSkill")
            return

        # 매크로 실행중이면 수정 불가능
        if self.shared_data.is_activated:
            self.cancel_skill_selection()
            self.noticeRequested.emit("MacroIsRunning")
            return

        equipped_skill: str = self.preset.skills.active_skills[index]
        selected_index: int = self.get_selected_index()

        # 스킬 선택중이 아닐 때: 선택
        if selected_index == -1:
            self.select_equipped_skill(index)
            return

        # 다른 슬롯을 눌렀다면: 선택 취소
        if selected_index != index:
            self.cancel_skill_selection()
            return

        # 같은 슬롯 재클릭

        # 장착된 스킬이 없으면 취소
        if not equipped_skill:
            self.cancel_skill_selection()
            return

        # 장착된 스킬 해제
        self.clear_equipped_skill(skill_id=equipped_skill)
        self.set_equipped_skill(index, "")

        self.cancel_skill_selection()

        self.dataChanged.emit()

    def on_available_skill_clicked(self, available_index: int) -> None:
        """상단(장착 가능) 스킬 클릭 처리(현재 선택된 슬롯에 장착)"""

        # 연계스킬 편집 중이면 수정 불가능
        if self.shared_data.sidebar_type == 4:
            self.cancel_skill_selection()
            self.noticeRequested.emit("editingLinkSkill")
            return

        # 매크로 실행중이면 수정 불가능
        if self.shared_data.is_activated:
            self.cancel_skill_selection()
            self.noticeRequested.emit("MacroIsRunning")
            return

        # 장착 슬롯이 선택되지 않았으면 무시
        selected_slot: int = self.get_selected_index()
        if selected_slot == -1:
            return

        selected_skill: str = get_every_skills(self.shared_data)[available_index]

        # 이미 장착된 스킬을 선택했을 때: 취소
        if selected_skill in self.preset.skills.active_skills:
            self.cancel_skill_selection()
            return

        # 기존에 장착된 스킬이 있으면 해제
        equipped_skill: str = self.preset.skills.active_skills[selected_slot]
        if equipped_skill:
            self.clear_equipped_skill(skill_id=equipped_skill)

        # 선택된 슬롯에 장착
        self.set_equipped_skill(selected_slot, selected_skill)

        self.cancel_skill_selection()
        self.dataChanged.emit()

    def clear_equipped_skill(self, skill_id: str) -> None:
        """장착된 스킬 초기화(우선순위/연계스킬 등)"""

        # 연계스킬 수동 사용으로 변경, 키 초기화
        for link in self.preset.link_settings:
            if skill_id in link.skills:
                link.set_manual()
                link.clear_key()

        # 스킬 사용 우선순위 리로드
        setting: SkillUsageSetting = self.preset.usage_settings[skill_id]
        prev_priority: int = setting.skill_priority

        # 우선순위가 있었다면 초기화
        if prev_priority:
            self.preset.usage_settings[skill_id].skill_priority = 0

            # 해당 스킬보다 높은 우선순위의 스킬들 우선순위 1 감소
            for setting in self.preset.usage_settings.values():
                if setting.skill_priority > prev_priority:
                    setting.skill_priority -= 1

        self._sync_to_shared_data()

        self.skillUnequipped.emit(skill_id)

    def select_equipped_skill(self, index: int) -> None:
        self.equipped_skills.select(index)

    def set_equipped_skill(self, index: int, skill_id: str) -> None:
        self.preset.skills.active_skills[index] = skill_id
        self._sync_to_shared_data()
        self.equipped_skills.set_skill(index, skill_id)
        self.update_preview()

    def display_available_skills(self) -> None:
        self.equippable_skills.display_available_skills()

    def get_selected_index(self) -> int:
        return self.equipped_skills.get_selected_index()

    def get_key_button(self, index: int) -> QPushButton:
        """단축키 설정 버튼 반환"""

        return self.equipped_skills.get_key_button(index)

    def set_key(self, index: int, key: str) -> None:
        """스킬 단축키 설정"""

        self.equipped_skills.set_key(index, key)

    def update_preview(self) -> None:
        """스킬 프리뷰 업데이트(현재 탭일 때만)"""

        self.preview.update_preview()

    def update_from_preset(self) -> None:
        """이 탭이 들고 있는 preset 기준으로 UI를 갱신"""

        self.equipped_skills.update_from_preset(self.preset)
        self.update_preview()

    def apply_key(self, index: int, key: "KeySpec") -> bool:
        """키 설정 변경을 preset에 적용. 변경되었으면 True"""

        if self.preset.skills.skill_keys[index] == key.key_id:
            return False

        self.preset.skills.skill_keys[index] = key.key_id
        self._sync_to_shared_data()
        self.equipped_skills.set_key(index, key.display)

        return True

    def _sync_to_shared_data(self) -> None:
        """preset -> shared_data로 동기화"""

        apply_preset_to_shared_data(
            self.shared_data,
            self.preset,
            preset_index=self.preset_index,
            all_presets=self.shared_data.presets,
        )


class SkillPreview(QFrame):
    """스킬 미리보기 프레임"""

    def __init__(self, shared_data: SharedData) -> None:
        super().__init__()

        self.shared_data: SharedData = shared_data

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

        self.skill_count = 0
        self.skills: list[QLabel] = []

        self.skills_layout: QHBoxLayout = QHBoxLayout()
        self.skills_layout.setContentsMargins(6, 6, 6, 6)
        self.skills_layout.setSpacing(6)
        self.skills_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.skills_layout)

    def update_preview(self) -> None:
        """프리뷰 업데이트"""

        # 매크로가 실행중이 아니라면 매크로 초반 시뮬레이션 실행
        if not self.shared_data.is_activated:
            init_macro(self.shared_data)
            add_task_list(self.shared_data)

        # 표시할 스킬 개수 (최대 6개)
        count: int = min(len(self.shared_data.task_list), 6)

        # 기존 아이콘 정리
        for icon in self.skills:
            icon.deleteLater()
            self.skills_layout.removeWidget(icon)

        self.skills.clear()

        # 각 미리보기 스킬 이미지 추가
        for slot in self.shared_data.task_list[:count]:
            pixmap: QPixmap = get_skill_pixmap(
                self.shared_data, skill_id=self.shared_data.equipped_skills[slot]
            )

            skill: SkillImage = SkillImage(parent=self, pixmap=pixmap, size=44)

            self.skills.append(skill)
            self.skills_layout.addWidget(skill)


class EquippableSkill(QFrame):
    """장착 가능한 스킬 프레임 (상단)"""

    skillClicked = pyqtSignal(int)

    def __init__(self, shared_data: SharedData) -> None:
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.setStyleSheet("QFrame { background-color: transparent; }")

        layout = QGridLayout()

        # 스킬 모음
        self.skills: list[EquippableSkill.Skill] = []
        COLS = 4
        for i in range(8):
            skill = self.Skill(shared_data=self.shared_data, index=i)
            self.skills.append(skill)

            skill.clicked.connect(self.skillClicked.emit)

            row: int = i // COLS
            col: int = i % COLS
            layout.addWidget(skill, row, col)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

    def display_available_skills(self):
        """
        장착 가능한 스킬 목록 표시
        장착되지 않은 스킬에 빨간 테두리 표시
        """
        skill_ids: list[str] = get_every_skills(self.shared_data)

        for index, skill_widget in enumerate(self.skills):
            skill_id: str = skill_ids[index]
            skill_widget.set_equipped_style(
                skill_id in self.shared_data.equipped_skills
            )

    class Skill(QFrame):
        clicked = pyqtSignal(int)

        def __init__(self, shared_data: SharedData, index: int) -> None:
            super().__init__()

            self.index: int = index
            self.shared_data: SharedData = shared_data

            self.setStyleSheet("QFrame { background-color: transparent; }")

            skill_id: str = get_every_skills(shared_data)[index]

            self.button: QPushButton = QPushButton(self)
            self.button.setStyleSheet("QPushButton { border-radius :10px; }")
            self.button.setFixedSize(48, 48)
            self.button.setIcon(
                QIcon(get_skill_pixmap(shared_data=shared_data, skill_id=skill_id))
            )
            self.button.setIconSize(QSize(48, 48))
            self.button.clicked.connect(lambda: self.clicked.emit(self.index))
            self.button.setCursor(Qt.CursorShape.PointingHandCursor)

            display_name: str = get_skill_name(shared_data, skill_id)
            self.name: QLabel = QLabel(display_name, self)
            self.name.setStyleSheet(
                "QLabel { background-color: transparent; border-radius :0px; }"
            )
            self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name.setFont(CustomFont(12))

            layout = QVBoxLayout()
            layout.addWidget(self.button)
            layout.addWidget(self.name)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.setLayout(layout)

        def set_equipped_style(self, is_equipped: bool) -> None:
            """장착 여부에 따른 버튼 테두리 표시"""

            border: str = "border: none;" if is_equipped else "border: 1px solid red;"

            # 기존 radius 스타일이 덮어씌워지지 않도록 함께 설정
            self.button.setStyleSheet(
                f"QPushButton {{ border-radius :10px; {border} }}"
            )


class EquippedSkill(QFrame):
    """장착된 스킬 프레임 (하단)"""

    slotClicked = pyqtSignal(int)
    keyClicked = pyqtSignal(int)

    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.setStyleSheet("QFrame { background-color: transparent; }")

        layout = QHBoxLayout()

        # 슬롯 모음
        self.skills: list[EquippedSkill.Skill] = []
        for i in range(6):
            skill = self.Skill(shared_data=self.shared_data, index=i)
            self.skills.append(skill)

            # 시그널 연결
            skill.slotClicked.connect(self.slotClicked.emit)
            skill.keyClicked.connect(self.keyClicked.emit)

            layout.addWidget(skill)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)
        self.setLayout(layout)

        # 선택된 스킬 인덱스
        # -1: 선택된 스킬 없음
        self.selected_index: int = -1

    def select(self, index: int) -> None:
        """슬롯 선택"""

        for i in range(6):
            self.skills[i].set_selected_style(i == index)

        self.selected_index = index

    def set_key(self, index: int, key: str) -> None:
        """스킬 단축키 설정"""

        self.skills[index].set_key(key)

    def set_skill(self, index: int, skill_id: str) -> None:
        """스킬 장착"""

        self.skills[index].set_skill(skill_id)

    def get_selected_index(self) -> int:
        return self.selected_index

    def get_key_button(self, index: int) -> QPushButton:
        """단축키 설정 버튼 반환"""

        return self.skills[index].get_key_button()

    def update_from_preset(self, preset: "MacroPreset") -> None:
        """preset 기준으로 슬롯 아이콘/키 텍스트를 동기화"""

        for index, name in enumerate(preset.skills.active_skills):
            self.set_skill(index, name)

        for index, key_id in enumerate(preset.skills.skill_keys):
            self.set_key(index, self.shared_data.KEY_DICT[key_id].display)

    class Skill(QFrame):
        slotClicked = pyqtSignal(int)
        keyClicked = pyqtSignal(int)

        def __init__(self, shared_data: SharedData, index: int):
            super().__init__()

            self.shared_data: SharedData = shared_data
            self.index: int = index

            self.setStyleSheet("QFrame { background-color: transparent; }")

            size = 48
            self._base_button_size: int = size
            self._selected_button_size: int = size + 8

            # 그림자 효과 설정
            self._shadow_blur_radius: int = 8
            self._shadow_offset_y: int = 2
            self._shadow_padding: int = 4

            name: str = shared_data.equipped_skills[index]

            self.button_container = QFrame(self)
            self.button_container.setStyleSheet(
                "QFrame { background-color: transparent; }"
            )
            container_size: int = self._selected_button_size + (
                self._shadow_padding * 2
            )
            self.button_container.setFixedSize(container_size, container_size)

            self.button: QPushButton = QPushButton(self.button_container)
            self.button.setStyleSheet("QPushButton { border-radius: 10px; }")
            self.button.setFixedSize(self._base_button_size, self._base_button_size)
            self.button.setIcon(
                QIcon(get_skill_pixmap(shared_data=shared_data, skill_id=name))
            )
            self.button.setIconSize(
                QSize(self._base_button_size, self._base_button_size)
            )
            self.button.clicked.connect(lambda: self.slotClicked.emit(self.index))
            self.button.setCursor(Qt.CursorShape.PointingHandCursor)

            button_layout = QVBoxLayout(self.button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(0)
            button_layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)

            self.key = QPushButton(shared_data.skill_keys[index].display, self)
            self.key.setFont(CustomFont(10))
            self.key.setFixedWidth(size)
            self.key.clicked.connect(lambda: self.keyClicked.emit(self.index))
            self.key.setCursor(Qt.CursorShape.PointingHandCursor)

            layout = QVBoxLayout()
            layout.addWidget(
                self.button_container, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(self.key, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

            self.setLayout(layout)

        def set_selected_style(self, selected: bool) -> None:
            """슬롯 선택"""

            # 선택 시: 아이콘 확대 + 그림자
            if selected:
                self.button.setFixedSize(
                    self._selected_button_size, self._selected_button_size
                )
                self.button.setIconSize(
                    QSize(self._selected_button_size, self._selected_button_size)
                )

                shadow = QGraphicsDropShadowEffect(self.button)
                shadow.setBlurRadius(self._shadow_blur_radius)
                shadow.setOffset(0, self._shadow_offset_y)
                shadow.setColor(QColor(0, 0, 0, 160))
                self.button.setGraphicsEffect(shadow)

            else:
                self.button.setFixedSize(self._base_button_size, self._base_button_size)
                self.button.setIconSize(
                    QSize(self._base_button_size, self._base_button_size)
                )
                self.button.setGraphicsEffect(None)

        def set_key(self, key: str) -> None:
            """스킬 단축키 설정"""

            self.key.setText(key)

        def set_skill(self, skill_id: str) -> None:
            """스킬 장착"""

            self.button.setIcon(
                QIcon(get_skill_pixmap(shared_data=self.shared_data, skill_id=skill_id))
            )

        def get_key_button(self) -> QPushButton:
            """단축키 설정 버튼 반환"""
            return self.key
