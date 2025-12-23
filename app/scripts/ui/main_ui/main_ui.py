from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt, pyqtSignal
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
from app.scripts.data_manager import add_preset, load_data, remove_preset, save_data
from app.scripts.misc import (
    convert_resource_path,
    get_available_skills,
    get_skill_pixmap,
)
from app.scripts.popup import PopupManager
from app.scripts.run_macro import add_task_list, init_macro
from app.scripts.shared_data import UI_Variable

if TYPE_CHECKING:
    from app.scripts.main_window import MainWindow
    from app.scripts.shared_data import SharedData


class MainUI(QFrame):
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
        self.tab_widget.skillKeyRequested.connect(self.onSkillKeyClick)
        # 데이터 변경 신호
        self.tab_widget.dataChanged.connect(lambda: save_data(self.shared_data))

        # 기능 함수들 연결
        # 탭 클릭시
        self.tab_widget.tabBar().tabBarClicked.connect(self.on_tab_clicked)  # type: ignore
        # 탭 추가버튼 클릭시
        self.tab_widget.add_tab_button.clicked.connect(self.on_add_tab_clicked)
        # 탭 닫기 버튼 클릭시
        self.tab_widget.tabCloseRequested.connect(self.on_remove_tab_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        layout.setContentsMargins(30, 30, 30, 10)
        layout.setSpacing(0)
        self.setLayout(layout)

    def on_tab_clicked(self, index: int) -> None:
        """탭 클릭시 실행"""

        # 활성화 상태인 팝업 닫기
        self.popup_manager.close_popup()

        # 매크로 실행중일 때는 탭 변경 불가
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 같은 탭 클릭시 탭 이름 변경 팝업
        if index == self.tab_widget.currentIndex():
            # 탭 이름 변경 팝업이 활성화되어있지 않을 때만 팝업 생성
            if self.shared_data.active_popup != "changeTabName":
                self.popup_manager.activatePopup("changeTabName")
                self.popup_manager.makePopupInput("tabName", index)

            return

        # 다른 탭 클릭시 탭 변경

        # 데이터 로드
        load_data(self.shared_data, index)

        # 현재 탭 확정 및 UI 갱신
        # (tabBarClicked 시점에 currentIndex가 아직 바뀌지 않았을 수 있어 명시적으로 지정)
        self.tab_widget.setCurrentIndex(index)

        # 사이드바 업데이트
        # self.sidebar.set_index(0)
        # self.sidebar.update_content()

        # 선택중인 스킬이 있었다면 취소
        self.cancel_skill_selection()

        # shared_data 변경사항을 현재 탭 UI에 반영
        self.tab_widget.refresh_current_tab()

        # 사이드바로 이동

        # self.master.get_sidebar().buttonServerList.setText(self.shared_data.server_ID)
        # self.master.get_sidebar().buttonJobList.setText(self.shared_data.job_ID)

        # self.master.get_sidebar().buttonInputDelay.setText(
        #     str(self.shared_data.delay_input)
        # )
        # rgb = 153 if self.shared_data.delay_type == 1 else 0
        # self.master.get_sidebar().buttonDefaultDelay.setStyleSheet(
        #     f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        # )
        # rgb = 153 if self.shared_data.delay_type == 0 else 0
        # self.master.get_sidebar().buttonInputDelay.setStyleSheet(
        #     f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        # )

        # self.master.get_sidebar().buttonInputCooltime.setText(
        #     str(self.shared_data.cooltime_reduction_input)
        # )
        # rgb = 153 if self.shared_data.cooltime_reduction_type == 1 else 0
        # self.master.get_sidebar().buttonDefaultCooltime.setStyleSheet(
        #     f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        # )
        # rgb = 153 if self.shared_data.cooltime_reduction_type == 0 else 0
        # self.master.get_sidebar().buttonInputCooltime.setStyleSheet(
        #     f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        # )

        # self.master.get_sidebar().buttonInputStartKey.setText(
        #     str(self.shared_data.start_key_input)
        # )
        # rgb = 153 if self.shared_data.start_key_type == 1 else 0
        # self.master.get_sidebar().buttonDefaultStartKey.setStyleSheet(
        #     f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        # )
        # rgb = 153 if self.shared_data.start_key_type == 0 else 0
        # self.master.get_sidebar().buttonInputStartKey.setStyleSheet(
        #     f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        # )

        # rgb = 153 if self.shared_data.mouse_click_type == 1 else 0
        # self.master.get_sidebar().button1stMouseType.setStyleSheet(
        #     f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        # )
        # rgb = 153 if self.shared_data.mouse_click_type == 0 else 0
        # self.master.get_sidebar().button2ndMouseType.setStyleSheet(
        #     f"QPushButton {{color: rgb({rgb}, {rgb}, {rgb});}}"
        # )

        # 데이터 저장
        save_data(self.shared_data)

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

        # 데이터 추가
        add_preset(shared_data=self.shared_data)
        index: int = self.tab_widget.count()
        load_data(self.shared_data, index)

        # 탭 추가
        self.tab_widget.add_tab(
            name=self.shared_data.tab_names[-1],
            available_skills=get_available_skills(self.shared_data),
            equipped_skills=self.shared_data.equipped_skills,
            keys=self.shared_data.skill_keys,
        )

    def on_remove_tab_clicked(self, index: int) -> None:
        """탭 닫기 버튼 클릭시 실행"""
        # 탭 닫기 버튼 클릭시 바로 탭이 제거되지 않고, 나중에 다시 열 수 있도록 수정
        # 탭 삭제 / 열기 기능을 추가해야함.
        # 이 방식을 사용하면 탭 제거 팝업을 띄우지 않음.

        # 활성화 상태인 팝업 닫기
        # self.master.get_popup_manager().close_popup()

        # 매크로 실행중일 때는 탭 추가 불가
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

        print(123)

        # 탭이 삭제되면 기존 인덱스와 달리지기 때문에 인덱스 대신 객체를 기반으로 탭을 찾도록 수정 필요

        # 팝업 제거
        # self.remove_confirmation_popup.deleteLater()

        # 탭 제거 팝업 활성화 상태 초기화
        # self.shared_data.is_tab_remove_popup_activated = False

        # 아니오 클릭시 리턴
        if not confirmed:
            return

        # 탭 제거
        self.tab_widget.remove_tab(index)
        remove_preset(index)

        # 삭제 후 인덱스 데이터 로드
        tab_count: int = self.tab_widget.count()
        if tab_count == 0:
            # 탭이 하나도 없으면 새 탭 추가
            self.add_new_tab()
            return

        new_index: int = self.tab_widget.currentIndex()
        load_data(self.shared_data, new_index)

        # 삭제 후 로드된 데이터를 현재 탭 UI에 반영
        self.tab_widget.refresh_current_tab()

        save_data(self.shared_data)

    def cancel_skill_selection(self) -> None:
        """
        스킬 장착 취소. 다른 곳 클릭시 실행됨
        """

        self.tab_widget.cancel_skill_selection()

    ## 스킬 단축키 설정 버튼 클릭
    def onSkillKeyClick(self, num):
        if self.shared_data.is_activated:
            self.master.get_popup_manager().close_popup()
            self.master.get_popup_manager().make_notice_popup("MacroIsRunning")
            return

        if self.shared_data.active_popup == "skillKey":
            self.master.get_popup_manager().close_popup()
            return
        self.master.get_popup_manager().close_popup()

        self.master.get_popup_manager().activatePopup("skillKey")
        self.master.get_popup_manager().makeKeyboardPopup(["skillKey", num])

    # NOTE: clear_equipped_skill / on_equipped_skill_clicked 로직은 Tab으로 이동됨


class TabWidget(QTabWidget):
    # 시그널 정의
    noticeRequested = pyqtSignal(str)
    skillKeyRequested = pyqtSignal(int)
    dataChanged = pyqtSignal()

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

        # self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        tab_bar: QTabBar | None = self.tabBar()
        if tab_bar is not None:
            tab_bar.setFont(CustomFont(12))

    def _setup_add_tab_button(self):
        """
        탭 목록 오른쪽에 고정된 탭 추가 버튼 설정
        """

        self.add_tab_button = QPushButton()
        self.add_tab_button.setIcon(
            QIcon(QPixmap(convert_resource_path("resources\\image\\plus.png")))
        )
        self.add_tab_button.setFixedSize(QSize(26, 26))

        # 탭 추가 버튼을 담을 컨테이너 위젯 생성
        corner_container = QWidget()
        corner_layout = QVBoxLayout(corner_container)
        corner_layout.setContentsMargins(1, 1, 1, 1)
        corner_layout.addWidget(
            self.add_tab_button, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # 우측 상단 코너에 컨테이너 위젯 설정
        self.setCornerWidget(corner_container, Qt.Corner.TopRightCorner)

    def _create_tab(
        self,
        name: str,
        available_skills: list[str],
        equipped_skills: list[str],
        keys: list[str],
    ) -> "Tab":
        """
        새 탭 생성
        """
        return Tab(self.shared_data)

    def add_tab(
        self,
        name: str,
        available_skills: list[str],
        equipped_skills: list[str],
        keys: list[str],
    ):
        """
        새로운 탭 생성 후 QTabWidget에 추가
        """

        self.tab_count += 1

        new_tab: Tab = self._create_tab(name, available_skills, equipped_skills, keys)
        tab_name: str = "스킬매크로"

        # 탭 시그널 연결
        self._connect_tab_signals(new_tab)

        # QTabWidget에 탭 추가
        index: int = self.addTab(new_tab, tab_name)

        # 새로 추가된 탭으로 이동
        self.setCurrentIndex(index)

    def _connect_tab_signals(self, tab: "Tab") -> None:
        tab.noticeRequested.connect(self.noticeRequested.emit)
        tab.skillKeyRequested.connect(self.skillKeyRequested.emit)
        tab.dataChanged.connect(self.dataChanged.emit)

    def _init_tabs(self):
        """
        초기 탭 설정
        """

        self.tab_count: int = 0

        # 탭 데이터 인스턴스를 기반으로 탭 추가하도록 수정
        # 임시로 최근 탭 데이터를 기반으로만 추가하도록 설정함.
        for i in range(len(self.shared_data.tab_names)):
            names: str = self.shared_data.tab_names[i]
            available_skills: list[str] = get_available_skills(self.shared_data)
            equipped_skills: list[str] = self.shared_data.equipped_skills
            keys: list[str] = self.shared_data.skill_keys

            self.add_tab(names, available_skills, equipped_skills, keys)

    def remove_tab(self, index):
        """
        탭 제거
        """

        self.removeTab(index)

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
            border-radius: 7px;
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
        """현재 탭의 스킬 선택 취소 (Tab으로 위임)"""

        tab: Tab = self.get_current_tab()
        tab.cancel_skill_selection()

    def refresh_current_tab(self) -> None:
        """현재 탭 UI 갱신 (Tab으로 위임)"""

        tab: Tab = self.get_current_tab()
        tab.refresh_ui()

    def select_equipped_skill(self, index: int) -> None:
        tab: Tab = self.get_current_tab()
        tab.select_equipped_skill(index)

    def set_equipped_skill(self, index: int, skill_name: str) -> None:
        tab: Tab = self.get_current_tab()
        tab.set_equipped_skill(index, skill_name)

    def display_available_skills(self) -> None:
        tab: Tab = self.get_current_tab()
        tab.display_available_skills()

    def get_selected_index(self) -> int:
        tab: Tab = self.get_current_tab()
        return tab.get_selected_index()


class Tab(QFrame):
    # 시그널 정의
    noticeRequested = pyqtSignal(str)
    skillKeyRequested = pyqtSignal(int)
    dataChanged = pyqtSignal()

    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.preview = SkillPreview(shared_data=self.shared_data)

        self.equippable_skills = EquippableSkill(shared_data=self.shared_data)

        line = QFrame(self)
        line.setStyleSheet("QFrame { background-color: #b4b4b4; }")
        line.setFixedHeight(1)

        self.equipped_skills = EquippedSkill(shared_data=self.shared_data)

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

        # 초기 표시
        self.refresh_ui()

    def refresh_ui(self) -> None:
        """현재 shared_data를 기준으로 탭 UI를 갱신"""

        # self.equippable_skills.display_available_skills()
        self.preview.update_preview()

    def cancel_skill_selection(self) -> None:
        """장착 스킬 선택 취소"""

        self.select_equipped_skill(-1)

    def on_skill_key_clicked(self, index: int) -> None:
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

        equipped_skill: str = self.shared_data.equipped_skills[index]
        selected_index: int = self.get_selected_index()

        # 스킬 선택중이 아닐 때 -> 선택
        if selected_index == -1:
            self.select_equipped_skill(index)
            return

        # 다른 슬롯을 눌렀다면 -> 선택 취소
        if selected_index != index:
            self.cancel_skill_selection()
            return

        # 같은 슬롯 재클릭
        if not equipped_skill:
            self.cancel_skill_selection()
            return

        # 장착된 스킬 해제
        self.set_equipped_skill(index, "")
        self.clear_equipped_skill(skill=equipped_skill)
        self.shared_data.equipped_skills[index] = ""
        self.cancel_skill_selection()

        self.refresh_ui()
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

        selected_slot: int = self.get_selected_index()
        if selected_slot == -1:
            return

        available_skills: list[str] = get_available_skills(self.shared_data)
        if available_index < 0 or available_index >= len(available_skills):
            return

        selected_skill: str = available_skills[available_index]

        # 이미 장착된 스킬을 선택했을 때 -> 취소
        if selected_skill in self.shared_data.equipped_skills:
            self.cancel_skill_selection()
            return

        equipped_skill: str = self.shared_data.equipped_skills[selected_slot]
        if equipped_skill:
            self.clear_equipped_skill(skill=equipped_skill)

        # 선택된 슬롯에 장착
        self.shared_data.equipped_skills[selected_slot] = selected_skill
        self.set_equipped_skill(selected_slot, selected_skill)

        self.cancel_skill_selection()
        self.refresh_ui()
        self.dataChanged.emit()

    def clear_equipped_skill(self, skill: str) -> None:
        """장착된 스킬 초기화(우선순위/연계스킬 등)"""

        # 연계스킬 수동 사용으로 변경
        for link in self.shared_data.link_skills:
            for skill_info in link["skills"]:
                if skill_info["name"] == skill:
                    link["useType"] = "manual"

        # 스킬 사용 우선순위 리로드
        prev_priority: int = self.shared_data.skill_priority.get(skill, 0)

        if prev_priority:
            self.shared_data.skill_priority[skill] = 0

            # 해당 스킬보다 높은 우선순위의 스킬들 우선순위 1 감소
            for sk, pri in self.shared_data.skill_priority.items():
                if pri > prev_priority:
                    self.shared_data.skill_priority[sk] -= 1

    def select_equipped_skill(self, index: int) -> None:
        self.equipped_skills.select(index)

    def set_equipped_skill(self, index: int, skill_name: str) -> None:
        self.equipped_skills.set_skill(index, skill_name)

    def display_available_skills(self) -> None:
        self.equippable_skills.display_available_skills()

    def get_selected_index(self) -> int:
        return self.equipped_skills.get_selected_index()


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
        self.setFixedSize(288, 48)

        self.skill_count = 0
        self.skills: list[QLabel] = []

    def update_preview(self) -> None:
        """프리뷰 업데이트"""

        # 매크로가 실행중이 아니라면 매크로 초반 시뮬레이션 실행
        if not self.shared_data.is_activated:
            init_macro(self.shared_data)
            add_task_list(self.shared_data, print_info=False)

        # 표시할 스킬 개수 (최대 6개)
        count: int = min(len(self.shared_data.task_list), 6)

        # 기존 아이콘 정리
        for icon in self.skills:
            icon.deleteLater()
        self.skills.clear()

        # 각 미리보기 스킬 이미지 추가
        for slot in self.shared_data.task_list[:count]:
            pixmap: QPixmap = get_skill_pixmap(
                self.shared_data,
                skill_name=self.shared_data.equipped_skills[slot],
                state=1 if self.shared_data.is_activated else -2,
            )

            skill: SkillImage = SkillImage(parent=self, pixmap=pixmap, size=48)

            self.skills.append(skill)


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

        # 장착되지 않은 스킬에 빨간 테두리 표시
        for name, skill in zip(get_available_skills(self.shared_data), self.skills):
            skill.set_equipped_style(name in self.shared_data.equipped_skills)

    class Skill(QFrame):
        clicked = pyqtSignal(int)

        def __init__(self, shared_data: SharedData, index: int) -> None:
            super().__init__()

            self.index: int = index

            self.setStyleSheet("QFrame { background-color: transparent; }")

            name: str = get_available_skills(shared_data)[index]

            self.button: QPushButton = QPushButton(self)
            self.button.setStyleSheet("QPushButton { border-radius :10px; }")
            self.button.setFixedSize(48, 48)
            self.button.setIcon(
                QIcon(get_skill_pixmap(shared_data=shared_data, skill_name=name))
            )
            self.button.setIconSize(QSize(48, 48))
            self.button.clicked.connect(lambda: self.clicked.emit(self.index))

            self.name: QLabel = QLabel(name, self)
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

    def set_skill(self, index: int, skill_name: str) -> None:
        """스킬 장착"""

        self.skills[index].set_skill(skill_name)

    def get_selected_index(self) -> int:
        return self.selected_index

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
                QIcon(get_skill_pixmap(shared_data=shared_data, skill_name=name))
            )
            self.button.setIconSize(
                QSize(self._base_button_size, self._base_button_size)
            )
            self.button.clicked.connect(lambda: self.slotClicked.emit(self.index))

            button_layout = QVBoxLayout(self.button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(0)
            button_layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)

            self.key = QPushButton(shared_data.skill_keys[index], self)
            self.key.setFont(CustomFont(10))
            self.key.setFixedWidth(size)
            self.key.clicked.connect(lambda: self.keyClicked.emit(self.index))

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

            # 이미지가 적용되면 보더가 안보임
            # style: dict[bool, str] = {
            #     True: "QPushButton { border-radius: 10px; border: 3px solid red; }",
            #     False: "QPushButton { border-radius: 10px; border: none; }",
            # }

            # self.button.setStyleSheet(style[selected])

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

        def set_skill(self, skill_name: str) -> None:
            """스킬 장착"""

            self.button.setIcon(
                QIcon(
                    get_skill_pixmap(
                        shared_data=self.shared_data, skill_name=skill_name
                    )
                )
            )
