from app.scripts.popup import PopupManager
from app.scripts.shared_data import SharedData
from .misc import convert_resource_path

from .data_manager import save_data, load_data, add_preset, remove_preset
from .misc import (
    get_skill_pixmap,
    adjust_font_size,
    adjust_text_length,
    get_available_skills,
)
from .shared_data import UI_Variable
from .custom_classes import (
    CustomShadowEffect,
    SkillImage,
    CustomFont,
)
from .run_macro import init_macro, add_task_list

from functools import partial

from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QTabBar,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QSizePolicy,
    QLayout,
)


if TYPE_CHECKING:
    from .main_window import MainWindow
    from .shared_data import SharedData


class MainUI(QFrame):
    """
    탭위젯, 사이드바를 포함하는 메인 UI 프레임
    """

    def __init__(
        self,
        master: "MainWindow",
        shared_data: SharedData,
    ) -> None:
        super().__init__()

        self.master: MainWindow = master
        self.popup_manager: PopupManager = master.get_popup_manager()

        self.shared_data: SharedData = shared_data
        self.ui_var = UI_Variable()

        self.tab_widget = TabWidget(self, self.shared_data)

        # 기능 함수들 연결
        # 탭 클릭시
        self.tab_widget.tabBar().tabBarClicked.connect(self.on_tab_clicked)  # type: ignore
        # 탭 추가버튼 클릭시
        self.tab_widget.add_tab_button.clicked.connect(self.on_add_tab_clicked)
        # 탭 닫기 버튼 클릭시
        self.tab_widget.tabCloseRequested.connect(self.on_remove_tab_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        layout.setContentsMargins(0, 0, 0, 0)
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

        # 사이드바 업데이트
        # self.sidebar.set_index(0)
        # self.sidebar.update_content()

        # 선택중인 스킬이 있었다면 취소
        self.cancel_skill_selection()

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

        # 활성화 상태인 팝업 닫기
        self.master.get_popup_manager().close_popup()

        # 매크로 실행중일 때는 탭 추가 불가
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")

            return

        # 탭 제거 팝업이 활성화되어있지 않을 때만 팝업 생성
        if self.shared_data.is_tab_remove_popup_activated:
            return

        self.shared_data.is_tab_remove_popup_activated = True

        # 탭 제거 팝업 생성
        self.confirm_remove = ConfirmRemovePopup(
            self, self.tab_widget.tabText(index), index
        )

    def on_remove_tab_popup_clicked(self, index: int, confirmed: bool) -> None:
        """탭 제거 팝업창에서 예/아니오 클릭시 실행"""

        # 탭이 삭제되면 기존 인덱스와 달리지기 때문에 인덱스 대신 객체를 기반으로 탭을 찾도록 수정 필요

        # 팝업 제거
        self.confirm_remove.deleteLater()

        # 탭 제거 팝업 활성화 상태 초기화
        self.shared_data.is_tab_remove_popup_activated = False

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

        save_data(self.shared_data)

    def cancel_skill_selection(self) -> None:
        """
        스킬 장착 취소. 다른 곳 클릭시 실행됨
        """

        self.tab_widget.select_equipped_skill(-1)

    def on_equipped_skill_clicked(self, index: int) -> None:
        """
        하단 스킬 아이콘 클릭시 실행
        """

        # print(self.shared_data.selectedSkillList[index])

        # 연계스킬 편집 중이면 수정 불가능
        if self.shared_data.sidebar_type == 4:
            self.cancel_skill_selection()
            self.popup_manager.make_notice_popup("editingLinkSkill")

            return

        # 매크로가 실행중이면 수정 불가능
        if self.shared_data.is_activated:
            self.cancel_skill_selection()
            self.popup_manager.make_notice_popup("MacroIsRunning")

            return

        # 지금 선택한 슬롯에 장착되어있던 스킬
        equipped_skill: str = self.shared_data.equipped_skills[index]
        # 이전에 선택된 스킬 인덱스
        selected_index: int = self.tab_widget.get_selected_index()

        # 스킬 선택중이 아닐 때 -> 선택
        if selected_index == -1:
            self.tab_widget.select_equipped_skill(index)

            return

        # 지금 선택한 슬롯과 다를 때
        if selected_index != index:
            # 이전에 빈 스킬이 장착되어있었다면 -> 취소
            self.cancel_skill_selection()

            return

        # 선택된 스킬을 다시 클릭했을 때

        # 장착이 되어있지 않았다면 -> 취소
        if not equipped_skill:
            self.cancel_skill_selection()

            return

        # 스킬이 장착되어있다면 -> 해제

        # 빈 스킬 아이콘으로 변경
        self.tab_widget.set_equipped_skill(index, "")

        # 장착된 스킬 설정 초기화
        self.clear_equipped_skill(skill=equipped_skill)

        # 데이터 초기화
        self.shared_data.equipped_skills[index] = ""

        # 선택 취소
        self.cancel_skill_selection()

        # 데이터 저장
        save_data(self.shared_data)

    def on_equippable_skill_clicked(self, index: int) -> None:
        """
        상단 스킬 아이콘 클릭 (8개)
        """

        # 선택된 스킬
        selected_skill: str = get_available_skills(shared_data=self.shared_data)[index]
        selected_index: int = self.tab_widget.get_selected_index()
        # 선택된 칸에 장착되어있던 스킬
        equipped_skill: str = self.shared_data.equipped_skills[selected_index]

        # 연계스킬 편집 중이면 수정 불가능
        if self.shared_data.sidebar_type == 4:
            self.cancel_skill_selection()
            return

        # 스킬 선택중이 아닐 때 -> 아무것도 하지 않음
        if selected_index == -1:
            return

        # 이미 장착된 스킬을 선택했을 때 -> 취소
        if selected_skill in self.shared_data.equipped_skills:
            self.cancel_skill_selection()
            return

        # 이미 스킬이 장착된 칸의 스킬을 변경하는 경우 -> 기존 스킬 초기화
        if equipped_skill:
            self.clear_equipped_skill(skill=equipped_skill)

        # 선택된 스킬칸에 새로운 스킬 장착
        self.shared_data.equipped_skills[selected_index] = get_available_skills(
            shared_data=self.shared_data
        )[index]

        # 스킬 아이콘 변경
        self.tab_widget.set_equipped_skill(selected_index, selected_skill)

        # 사이드바가 스킬 사용설정이라면 아이콘 변경
        # if self.shared_data.sidebar_type == 2:
        #     self.sidebar.skill_icons[selected_skill].setPixmap(
        #         get_skill_pixmap(
        #             shared_data=self.shared_data, skill_name=selected_skill
        #         )
        #     )

        # 선택 취소
        self.cancel_skill_selection()

        # 데이터 저장
        save_data(self.shared_data)

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

    def clear_equipped_skill(self, skill: str):
        """
        장착된 스킬 초기화
        """

        # 연계스킬 수동 사용으로 변경
        for link in self.shared_data.link_skills:
            for skill_info in link["skills"]:
                if skill_info["name"] == skill:
                    link["useType"] = "manual"

        # 스킬 사용 우선순위 리로드
        prev_priority: int = self.shared_data.skill_priority[skill]

        # 해제되는 스킬의 우선순위가 있다면
        if prev_priority:
            self.shared_data.skill_priority[skill] = 0

            # 해당 스킬보다 높은 우선순위의 스킬들 우선순위 1 감소
            for sk, pri in self.shared_data.skill_priority.items():
                if pri > prev_priority:
                    self.shared_data.skill_priority[sk] -= 1

                    # if self.shared_data.sidebar_type == 2:
                    #     self.sidebar.skill_sequence[sk].setText(
                    #         str(pri - 1)
                    #     )

        # 스킬 연계설정이라면 -> 리로드
        # if self.shared_data.sidebar_type == 3:
        #     self.master.get_sidebar().delete_sidebar_3()
        #     self.shared_data.sidebar_type = -1
        #     self.master.get_sidebar().change_sidebar_to_3()

        # 사이드바가 스킬 사용설정이라면
        # if self.shared_data.sidebar_type == 2:
        #     self.sidebar.skill_icons[skill].setPixmap(
        #         get_skill_pixmap(
        #             shared_data=self.shared_data,
        #             skill_name=skill,
        #             state=-2,
        #         )
        #     )

        #     self.master.get_sidebar().skill_sequence[skill].setText("-")


class TabWidget(QTabWidget):
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

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

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
        tab_name: str = "탭 " + str(self.tab_count)

        # QTabWidget에 탭 추가
        index: int = self.addTab(new_tab, tab_name)

        # 새로 추가된 탭으로 이동
        self.setCurrentIndex(index)

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
    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.preview = SkillPreview(shared_data=self.shared_data)

        self.equippable_skills = EquippableSkill(shared_data=self.shared_data)

        line = QFrame(self)
        line.setStyleSheet("QFrame { background-color: #b4b4b4; }")
        line.setFixedHeight(1)

        self.equipped_skills = EquippedSkill(shared_data=self.shared_data)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.equippable_skills)
        layout.addWidget(line)
        layout.addWidget(self.equipped_skills)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)
        self.setLayout(layout)

    def select_equipped_skill(self, index: int) -> None:
        self.equipped_skills.select(index)

    def set_equipped_skill(self, index: int, skill_name: str) -> None:
        self.equipped_skills.set_skill(index, skill_name)

    def display_available_skills(self) -> None:
        self.equippable_skills.display_available_skills()

    def get_selected_index(self) -> int:
        return self.equipped_skills.get_selected_index()


class SkillPreview(QFrame):
    def __init__(self, shared_data: SharedData):
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

    def set_icons(self) -> None:
        """
        스킬 미리보기 프레임에 스킬 아이콘 설정
        """

        # 매크로가 실행중이 아니라면 매크로 초반 시뮬레이션 실행
        if not self.shared_data.is_activated:
            init_macro(self.shared_data)
            add_task_list(self.shared_data, print_info=False)
            # self.printMacroInfo(True)
            # print(self.shared_data.taskList)

        count: int = min(len(self.shared_data.task_list), 6)

        # 각 미리보기 스킬 이미지 추가
        for i in range(count):
            pixmap: QPixmap = get_skill_pixmap(
                self.shared_data,
                self.shared_data.equipped_skills[self.shared_data.task_list[i]],
                1 if self.shared_data.is_activated else -2,
            )

            skill: SkillImage = SkillImage(parent=self, pixmap=pixmap, size=48)

            self.skills.append(skill)


class EquippableSkill(QFrame):
    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.setStyleSheet("QFrame { background-color: transparent; }")

        layout = QGridLayout()

        self.skills: list[EquippableSkill.Skill] = []
        COLS = 4
        for i in range(8):
            skill = self.Skill(shared_data=self.shared_data, index=i)
            self.skills.append(skill)

            row: int = i // COLS
            col: int = i % COLS

            layout.addWidget(skill, row, col)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

    def display_available_skills(self):
        for i in range(8):
            name: str = get_available_skills(self.shared_data)[i]

            # 장착되지 않은 스킬에 빨간 테두리 표시
            if name in self.shared_data.equipped_skills:
                self.skills[i].button.setStyleSheet("QPushButton { border: none; }")
            else:
                self.skills[i].button.setStyleSheet(
                    "QPushButton { border: 1px solid red; }"
                )

    class Skill(QFrame):
        def __init__(self, shared_data: SharedData, index: int):
            super().__init__()

            self.setStyleSheet("QFrame { background-color: transparent; }")

            name: str = get_available_skills(shared_data)[index]

            self.button: QPushButton = QPushButton(self)
            self.button.setStyleSheet("QPushButton { border-radius :10px; }")
            self.button.setFixedSize(48, 48)
            self.button.setIcon(
                QIcon(
                    get_skill_pixmap(
                        shared_data=shared_data,
                        skill_name=name,
                    )
                )
            )
            self.button.setIconSize(QSize(48, 48))
            # self.button.clicked.connect(
            #     partial(lambda x: self.on_equippable_skill_clicked(x), i)
            # )

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


class EquippedSkill(QFrame):
    def __init__(self, shared_data: SharedData):
        super().__init__()

        self.shared_data: SharedData = shared_data

        self.setStyleSheet("QFrame { background-color: transparent; }")

        layout = QHBoxLayout()

        self.skills: list[EquippedSkill.Skill] = []
        for i in range(6):
            skill = self.Skill(shared_data=self.shared_data, index=i)
            self.skills.append(skill)

            layout.addWidget(skill)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)
        self.setLayout(layout)

        self.selected_index: int = -1

    def select(self, index: int) -> None:
        for i in range(6):
            self.skills[i].button.setStyleSheet("QPushButton { border: none; }")

        if index != -1:
            self.skills[index].button.setStyleSheet(
                "QPushButton { border: 1px solid red;}"
            )

        self.selected_index = index

    def set_key(self, index: int, key: str) -> None:

        self.skills[index].key.setText(key)

    def set_skill(self, index: int, skill_name: str) -> None:
        self.skills[index].button.setIcon(
            QIcon(get_skill_pixmap(shared_data=self.shared_data, skill_name=skill_name))
        )

    def get_selected_index(self) -> int:
        return self.selected_index

    class Skill(QFrame):
        def __init__(self, shared_data: SharedData, index: int):
            super().__init__()

            self.setStyleSheet("QFrame { background-color: transparent; }")

            size = 48
            name: str = shared_data.equipped_skills[index]

            self.button: QPushButton = QPushButton(self)
            self.button.setStyleSheet("QPushButton { border-radius :10px; }")
            self.button.setFixedSize(size, size)
            self.button.setIcon(
                QIcon(
                    get_skill_pixmap(
                        shared_data=shared_data,
                        skill_name=name,
                    )
                )
            )
            self.button.setIconSize(QSize(size, size))
            # self.button.clicked.connect(
            #     partial(lambda x: self.on_equipped_skill_clicked(x), i)
            # )

            self.key = QPushButton(shared_data.skill_keys[index], self)
            self.key.setFont(CustomFont(10))
            self.key.setFixedWidth(size)
            # self.key_button.clicked.connect(partial(lambda x: self.onSkillKeyClick(x), i))

            layout = QVBoxLayout()
            layout.addWidget(self.button)
            layout.addWidget(self.key)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

            self.setLayout(layout)
