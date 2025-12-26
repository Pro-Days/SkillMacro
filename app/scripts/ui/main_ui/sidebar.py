from __future__ import annotations

import copy
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayoutItem,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.scripts.config import config
from app.scripts.custom_classes import CustomFont, SkillImage
from app.scripts.data_manager import apply_preset_to_shared_data
from app.scripts.macro_models import MacroPreset, SkillUsageSetting
from app.scripts.misc import (
    convert_resource_path,
    get_available_skills,
    get_skill_details,
    get_skill_pixmap,
    is_key_using,
)
from app.scripts.shared_data import UI_Variable

if TYPE_CHECKING:
    from typing import Literal

    from app.scripts.macro_models import MacroPreset
    from app.scripts.main_window import MainWindow
    from app.scripts.popup import PopupManager
    from app.scripts.shared_data import KeySpec, SharedData


class Sidebar(QFrame):
    """좌측 사이드바 클래스"""

    # 데이터 변경 시그널
    dataChanged = pyqtSignal()

    def __init__(
        self,
        master: MainWindow,
        shared_data: SharedData,
        preset: "MacroPreset",
        preset_index: int,
    ) -> None:
        super().__init__(master)

        self.setStyleSheet("QFrame { background-color: #FFFFFF; }")

        self.master: MainWindow = master
        self.shared_data: SharedData = shared_data

        # Current preset context (set by MainUI when tab changes)
        self.preset: MacroPreset = preset
        self.preset_index: int = preset_index

        self.ui_var = UI_Variable()
        self.popup_manager: PopupManager = self.master.get_popup_manager()

        # 사이드바 페이지들
        self.general_settings = GeneralSettings(
            self.shared_data,
            self.popup_manager,
            on_data_changed=self.dataChanged.emit,
        )
        self.skill_settings = SkillSettings(
            self.shared_data,
            self.popup_manager,
            on_data_changed=self.dataChanged.emit,
        )
        self.link_skill_settings = LinkSkillSettings(
            self.shared_data,
            self.popup_manager,
            on_data_changed=self.dataChanged.emit,
        )
        self.link_skill_editor = LinkSkillEditor(
            self.shared_data,
            self.popup_manager,
            on_data_changed=self.dataChanged.emit,
        )

        # 연계스킬 편집 요청 시그널
        self.link_skill_settings.editRequested.connect(
            self._on_link_skill_edit_requested
        )

        # 연계스킬 편집기 종료/저장 시그널
        self.link_skill_editor.closed.connect(self._on_link_skill_editor_closed)
        self.link_skill_editor.saved.connect(self._on_link_skill_editor_saved)
        self.link_skill_editor.contentResized.connect(self.adjust_stack_height)

        # 네비게이션 버튼
        self.nav_button = NavigationButtons(self.change_page, self.master.change_layout)

        self.page_navigator = QStackedWidget()
        self.page_navigator.addWidget(self.general_settings)
        self.page_navigator.addWidget(self.skill_settings)
        self.page_navigator.addWidget(self.link_skill_settings)
        self.page_navigator.addWidget(self.link_skill_editor)
        self.page_navigator.setContentsMargins(0, 0, 0, 0)
        self.page_navigator.setFixedWidth(300)

        # 초기 페이지 설정
        self.page_navigator.setCurrentIndex(0)
        self.nav_button.set_active_button(0)
        self.adjust_stack_height()

        # 스크롤바
        self.scroll_area: QScrollArea = QScrollArea()
        self.scroll_area.setWidget(self.page_navigator)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                background-color: #FFFFFF;
                border: 0px solid black;
                border-right: 1px solid #bbbbbb;
            }
            """
        )

        # 위젯이 스크롤 영역에 맞춰 크기 조절되도록
        self.scroll_area.setWidgetResizable(True)

        # 스크롤바 스크롤 설정
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        vertical_scroll_bar: QScrollBar = self.scroll_area.verticalScrollBar()  # type: ignore
        scroll_bar_width: int = vertical_scroll_bar.sizeHint().width()
        self.scroll_area.setFixedWidth(300 + scroll_bar_width)

        layout = QHBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.nav_button)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setLayout(layout)

    def _on_link_skill_edit_requested(self, data: dict) -> None:
        """연계스킬 편집 요청 처리: 편집기 로드 후 편집 페이지로 이동."""

        self.link_skill_editor.load(data)
        self.change_page(3)

    def _on_link_skill_editor_closed(self) -> None:
        """연계스킬 편집 페이지 종료(취소/저장 이후) 시 목록 페이지로 복귀."""

        # 목록 UI를 최신 상태로 갱신
        self.link_skill_settings.update_from_preset(self.preset)
        self.change_page(2)

    def _on_link_skill_editor_saved(self) -> None:
        """연계스킬 저장 완료 후 사이드바 전체 갱신."""

        # 외부(메인 UI)에서도 dataChanged를 받아 갱신할 수 있지만,
        # 편집 종료 직후 목록이 바로 업데이트되도록 여기서도 한 번 갱신한다.
        self.link_skill_settings.update_from_preset(self.preset)

    def set_current_preset(self, preset: "MacroPreset", preset_index: int) -> None:
        """프리셋을 사이드바에 설정"""

        self.preset = preset
        self.preset_index = int(preset_index)
        self.update_from_preset()

    def update_from_preset(self) -> None:
        """프리셋을 사이드바 페이지들에 적용"""

        # 링크 스킬 편집 페이지 제외 프리셋 적용
        for page in (
            self.general_settings,
            self.skill_settings,
            self.link_skill_settings,
        ):
            page.update_from_preset(self.preset)

        self.adjust_stack_height()

    def change_page(self, index: Literal[0, 1, 2, 3]) -> None:
        """페이지 변경"""

        self.page_navigator.setCurrentIndex(index)

        # 인덱스 3은 연계스킬 편집 페이지,
        # 버튼 3은 계산기 페이지이므로 활성화하지 않음
        if index != 3:
            self.nav_button.set_active_button(index)

        self.adjust_stack_height()

    def adjust_stack_height(self) -> None:
        """현재 표시 중인 UI 높이에 맞춰 스택 위젯 높이를 동기화."""

        current_widget: QWidget = self.page_navigator.currentWidget()  # type: ignore

        # 크기 조절
        current_widget.adjustSize()

        # 가로 크기는 기존 값으로 고정
        current_widget.setFixedWidth(self.page_navigator.width())

        height: int = current_widget.height()
        self.page_navigator.setFixedHeight(height)


class GeneralSettings(QFrame):
    """사이드바 타입 1 - 일반 설정"""

    def __init__(
        self,
        shared_data: SharedData,
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ) -> None:
        super().__init__()

        # self.setStyleSheet("QFrame { background-color: #FFFFFF; }")

        self.shared_data: SharedData = shared_data
        self.popup_manager: PopupManager = popup_manager
        self._on_data_changed: Callable[[], None] = on_data_changed

        self.title = Title("일반 설정")

        # 서버 - 직업
        self.server_job_setting = self.SettingItem(
            title="서버 - 직업",
            tooltip="서버와 직업을 선택합니다.",
            btn0_text="",
            btn0_enabled=True,
            btn1_text="X",
            btn1_enabled=False,
            func0=self.on_servers_clicked,
            func1=self.popup_manager.close_popup,
        )

        # 딜레이
        self.delay_setting = self.SettingItem(
            title="딜레이",
            tooltip=(
                "스킬을 사용하기 위한 키보드 입력, 마우스 클릭과 같은 동작 사이의 간격을 설정합니다.\n"
                "단위는 밀리초(millisecond, 0.001초)를 사용합니다.\n"
                "입력 가능한 딜레이의 범위는 50~1000입니다.\n"
                "딜레이를 계속해서 조절하며 1분간 매크로를 실행했을 때 놓치는 스킬이 없도록 설정해주세요."
            ),
            btn0_text=f"기본: {self.shared_data.DEFAULT_DELAY}",
            btn0_enabled=True,
            btn1_text="",
            btn1_enabled=False,
            func0=self.on_default_delay_clicked,
            func1=self.on_user_delay_clicked,
        )

        # 쿨타임 감소
        self.cooltime_setting = self.SettingItem(
            title="쿨타임 감소",
            tooltip=(
                "캐릭터의 쿨타임 감소 스탯입니다.\n"
                "입력 가능한 쿨타임 감소 스탯의 범위는 0~50입니다."
            ),
            btn0_text=f"기본: {self.shared_data.DEFAULT_COOLTIME_REDUCTION}",
            btn0_enabled=True,
            btn1_text="",
            btn1_enabled=False,
            func0=self.on_default_cooltime_clicked,
            func1=self.on_user_cooltime_clicked,
        )

        # 시작키 설정
        self.start_key_setting = self.SettingItem(
            title="시작키 설정",
            tooltip=(
                "매크로를 시작하기 위한 키입니다.\n"
                "쓰지 않는 키로 설정한 후, 로지텍 G 허브와 같은 프로그램으로 마우스의 버튼에 매핑하는 것을 추천합니다."
            ),
            btn0_text=f"기본: {self.shared_data.DEFAULT_START_KEY.display}",
            btn0_enabled=True,
            btn1_text="",
            btn1_enabled=False,
            func0=self.on_default_start_key_clicked,
            func1=self.on_user_start_key_clicked,
        )

        # 마우스 클릭
        self.click_setting = self.SettingItem(
            title="마우스 클릭",
            tooltip=(
                "평타 사용 안함: 일반공격을 사용하지 않습니다.\n"
                "평타 사용: 일반공격을 사용하기 위해 마우스를 클릭합니다."
            ),
            btn0_text="평타 사용 안함",
            btn0_enabled=True,
            btn1_text="평타 사용",
            btn1_enabled=False,
            func0=self.on_mouse_type0_clicked,
            func1=self.on_mouse_type1_clicked,
        )

        layout = QVBoxLayout()

        layout.addWidget(self.title)
        layout.addWidget(self.server_job_setting)
        layout.addWidget(self.delay_setting)
        layout.addWidget(self.cooltime_setting)
        layout.addWidget(self.start_key_setting)
        layout.addWidget(self.click_setting)

        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

        self.update_from_preset(self._get_preset())

    def _get_preset(self) -> "MacroPreset":
        """shared_data에서 현재 프리셋을 가져옴"""

        return self.shared_data.presets[self.shared_data.recent_preset]

    def _sync_preset_to_shared_data(self, preset: "MacroPreset") -> None:
        """프리셋을 shared_data에 동기화
        shared_data 구조를 바꿔서 프리셋만을 사용한다면 이 함수는 제거될 예정"""

        apply_preset_to_shared_data(
            self.shared_data,
            preset,
            preset_index=self.shared_data.recent_preset,
            all_presets=self.shared_data.presets,
        )

    def update_from_preset(self, preset: "MacroPreset") -> None:
        """프리셋으로부터 위젯 상태를 업데이트"""

        # 서버 - 직업
        self.server_job_setting.set_left_button_text(preset.settings.server_id)

        # 딜레이
        delay_type, delay_input = preset.settings.delay
        self.delay_setting.set_right_button_text(str(delay_input))
        self.delay_setting.set_buttons_enabled(delay_type == 0, delay_type == 1)

        # 쿨타임 감소
        cool_type, cool_input = preset.settings.cooltime
        self.cooltime_setting.set_right_button_text(str(cool_input))
        self.cooltime_setting.set_buttons_enabled(cool_type == 0, cool_type == 1)

        # 시작키 설정
        start_type, start_key_id = preset.settings.start_key
        start_key_display: str = self.shared_data.KEY_DICT[start_key_id].display
        self.start_key_setting.set_right_button_text(start_key_display)
        self.start_key_setting.set_buttons_enabled(start_type == 0, start_type == 1)

        # 마우스 클릭
        self.click_setting.set_buttons_enabled(
            preset.settings.mouse_click_type == 0, preset.settings.mouse_click_type == 1
        )

    def on_servers_clicked(self) -> None:
        """서버 목록 클릭시 실행"""

        def apply(server_name: str) -> None:
            """적용 함수"""

            preset: MacroPreset = self._get_preset()
            if server_name == preset.settings.server_id:
                return

            preset.settings.server_id = server_name
            self._sync_preset_to_shared_data(preset)
            self.update_from_preset(preset)
            self._on_data_changed()

        self.popup_manager.close_popup()

        self.popup_manager.make_server_popup(self.server_job_setting.left_button, apply)

    def on_default_delay_clicked(self) -> None:
        """기본 딜레이 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        preset: MacroPreset = self._get_preset()

        # 이미 기본 딜레이라면 무시
        if preset.settings.delay[0] == 0:
            return

        # 기본 딜레이로 변경 (입력 값은 유지)
        preset.settings.delay = (0, int(preset.settings.delay[1]))

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def on_user_delay_clicked(self) -> None:
        """유저 딜레이 클릭시 실행"""

        def apply(delay_value: int) -> None:
            """적용 함수"""

            preset: MacroPreset = self._get_preset()

            # 변경 사항이 없으면 무시
            if delay_value == preset.settings.delay[1]:
                return

            preset.settings.delay = (1, int(delay_value))
            self._sync_preset_to_shared_data(preset)
            self.update_from_preset(preset)
            self._on_data_changed()

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        preset: MacroPreset = self._get_preset()

        # 이미 유저 딜레이라면 딜레이 입력 팝업 열기
        if preset.settings.delay[0] == 1:
            self.popup_manager.make_delay_popup(self.delay_setting.right_button, apply)
            return

        # 유저 딜레이로 변경 (입력 값 유지)
        preset.settings.delay = (1, int(preset.settings.delay[1]))
        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def on_default_cooltime_clicked(self) -> None:
        """기본 쿨타임 감소 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        preset: MacroPreset = self._get_preset()

        # 이미 기본 쿨타임 감소라면 무시
        if preset.settings.cooltime[0] == 0:
            return

        # 기본 쿨타임 감소로 변경 (입력 값은 유지)
        preset.settings.cooltime = (0, int(preset.settings.cooltime[1]))

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def on_user_cooltime_clicked(self) -> None:
        """유저 쿨타임 감소 클릭시 실행"""

        def apply(cooltime_value: int) -> None:
            """적용 함수"""

            preset: MacroPreset = self._get_preset()
            if cooltime_value == preset.settings.cooltime[1]:
                return

            preset.settings.cooltime = (1, int(cooltime_value))
            self._sync_preset_to_shared_data(preset)
            self.update_from_preset(preset)
            self._on_data_changed()

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        preset: MacroPreset = self._get_preset()

        # 이미 유저 쿨타임 감소라면 쿨타임 감소 입력 팝업 열기
        if preset.settings.cooltime[0] == 1:
            self.popup_manager.make_cooltime_popup(
                self.cooltime_setting.right_button, apply
            )
            return

        # 유저 쿨타임 감소로 변경 (입력 값 유지)
        preset.settings.cooltime = (1, int(preset.settings.cooltime[1]))
        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def on_default_start_key_clicked(self) -> None:
        """기본 시작키 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        preset: MacroPreset = self._get_preset()

        # 이미 기본 시작키라면 무시
        if preset.settings.start_key[0] == 0:
            return

        default_key: KeySpec = self.shared_data.DEFAULT_START_KEY
        current_input_key_id: str = preset.settings.start_key[1]

        # 유저 입력 키가 기본키와 다르고, 기본키가 다른 용도로 사용 중이면 변경 불가
        if current_input_key_id != default_key.key_id and is_key_using(
            self.shared_data, default_key
        ):
            self.popup_manager.make_notice_popup("StartKeyChangeError")
            return

        # 기본 시작키로 변경 (입력 값은 유지)
        preset.settings.start_key = (0, current_input_key_id)

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def on_user_start_key_clicked(self) -> None:
        """유저 시작키 클릭시 실행"""

        def apply(start_key: KeySpec) -> None:
            """적용 함수"""

            preset: MacroPreset = self._get_preset()
            if start_key.key_id == preset.settings.start_key[1]:
                return

            preset.settings.start_key = (1, start_key.key_id)
            self._sync_preset_to_shared_data(preset)
            self.update_from_preset(preset)
            self._on_data_changed()

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        preset: MacroPreset = self._get_preset()

        # 이미 유저 시작키라면 시작키 입력 팝업 열기
        if preset.settings.start_key[0] == 1:
            self.popup_manager.make_start_key_popup(
                self.start_key_setting.right_button, apply
            )
            return

        default_key: KeySpec = self.shared_data.DEFAULT_START_KEY
        current_input_key_id: str = preset.settings.start_key[1]

        # 유저 입력 키가 기본키와 다르고, 유저키가 다른 용도로 사용 중이면 변경 불가
        if current_input_key_id != default_key.key_id and is_key_using(
            self.shared_data, self.shared_data.KEY_DICT[current_input_key_id]
        ):
            self.popup_manager.make_notice_popup("StartKeyChangeError")
            return

        # 유저 시작키로 변경 (입력 값 유지)
        preset.settings.start_key = (1, preset.settings.start_key[1])
        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def on_mouse_type0_clicked(self) -> None:
        """마우스 클릭 타입0 (스킬 사용 시) 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        preset: MacroPreset = self._get_preset()

        # 이미 타입0 이라면 무시
        if preset.settings.mouse_click_type == 0:
            return

        preset.settings.mouse_click_type = 0
        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def on_mouse_type1_clicked(self) -> None:
        """마우스 클릭 타입1 (평타 포함) 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if self.shared_data.is_activated:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        preset: MacroPreset = self._get_preset()

        # 이미 타입1 이라면 무시
        if preset.settings.mouse_click_type == 1:
            return

        preset.settings.mouse_click_type = 1
        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    class SettingItem(QFrame):
        def __init__(
            self,
            title: str,
            tooltip: str,
            btn0_text: str,
            btn0_enabled: bool,
            btn1_text: str,
            btn1_enabled: bool,
            func0: Callable[[], None],
            func1: Callable[[], None],
        ) -> None:
            super().__init__()

            self.title = QLabel(title)
            self.title.setFont(CustomFont(16))
            self.title.setStyleSheet(
                "QLabel { border: 0px solid black; border-radius: 10px; }"
            )
            if config.ui.debug_colors:
                self.title.setStyleSheet("QLabel { background-color: #FF0000; }")

            self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.title.setToolTip(tooltip)

            button_style = """
                QPushButton[active=true] {
                    color: #000000;
                }
                QPushButton[active=false] {
                    color: #999999;
                }
            """

            self.left_button = QPushButton(btn0_text)
            self.left_button.setFont(CustomFont(12))
            self.left_button.setStyleSheet(button_style)
            self.left_button.setProperty("active", btn0_enabled)
            self.left_button.setFixedWidth(120)
            self.left_button.setEnabled(func0 is not None)

            self.right_button = QPushButton(btn1_text)
            self.right_button.setFont(CustomFont(12))
            self.right_button.setStyleSheet(button_style)
            self.right_button.setProperty("active", btn1_enabled)
            self.right_button.setFixedWidth(120)
            self.right_button.setEnabled(func1 is not None)

            # 함수 연결
            self.left_button.clicked.connect(func0)
            self.right_button.clicked.connect(func1)

            layout = QGridLayout()
            layout.addWidget(self.title, 0, 0, 1, 2)
            layout.addWidget(self.left_button, 1, 0)
            layout.addWidget(self.right_button, 1, 1)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)

            self.setLayout(layout)

        def set_buttons_enabled(self, left_enabled: bool, right_enabled: bool) -> None:
            """양쪽 버튼 활성화 상태 설정"""

            self.left_button.setProperty("active", left_enabled)

            self.left_button.style().unpolish(self.left_button)  # type: ignore
            self.left_button.style().polish(self.left_button)  # type: ignore
            self.left_button.update()

            self.right_button.setProperty("active", right_enabled)

            self.right_button.style().unpolish(self.right_button)  # type: ignore
            self.right_button.style().polish(self.right_button)  # type: ignore
            self.right_button.update()

        def set_right_button_text(self, text: str) -> None:
            """오른쪽 버튼 텍스트 설정"""

            self.right_button.setText(text)

        def set_left_button_text(self, text: str) -> None:
            """왼쪽 버튼 텍스트 설정"""

            self.left_button.setText(text)


class SkillSettings(QFrame):
    """사이드바 타입 2 - 스킬 사용설정"""

    def __init__(
        self,
        shared_data: SharedData,
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ):
        super().__init__()

        self.shared_data: SharedData = shared_data
        self.popup_manager: PopupManager = popup_manager
        self._on_data_changed: Callable[[], None] = on_data_changed

        self.title = Title("스킬 사용설정")

        self._check_btn_style = """
            QPushButton {
                background-color: transparent; border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """

        self._skill_names: list[str] = []
        self._usage_btns: list[QPushButton] = []
        self._sole_btns: list[QPushButton] = []
        self._priority_btns: list[QPushButton] = []

        self._grid_layout = QGridLayout()
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(0)
        self._grid_layout.setVerticalSpacing(15)

        grid_frame = QFrame()
        grid_frame.setLayout(self._grid_layout)

        self._build_header()

        layout = QVBoxLayout()
        layout.addWidget(self.title, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(grid_frame)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.update_from_preset(self._get_preset())

    def _get_preset(self) -> "MacroPreset":
        return self.shared_data.presets[self.shared_data.recent_preset]

    def _sync_preset_to_shared_data(self, preset: "MacroPreset") -> None:
        apply_preset_to_shared_data(
            self.shared_data,
            preset,
            preset_index=self.shared_data.recent_preset,
            all_presets=self.shared_data.presets,
        )

    def _build_header(self) -> None:
        """헤더 행 생성"""

        titles: list[str] = ["사용\n여부", "단독\n사용", "우선\n순위"]
        tooltips: list[str] = [
            (
                "매크로가 작동 중일 때 자동으로 스킬을 사용할지 결정합니다.\n"
                "이동기같이 자신이 직접 사용해야 하는 스킬만 사용을 해제하시는 것을 추천드립니다.\n"
                "연계스킬에는 적용되지 않습니다."
            ),
            (
                "연계스킬을 대기할 때 다른 스킬들이 준비되는 것을 기다리지 않고 우선적으로 사용할 지 결정합니다.\n"
                "연계스킬 내에서 다른 스킬보다 너무 빠르게 준비되는 스킬은 사용을 해제하시는 것을 추천드립니다.\n"
                "사용여부가 활성화되지 않았다면 단독으로 사용되지 않습니다."
            ),
            (
                "매크로가 작동 중일 때 여러 스킬이 준비되었더라도 우선순위가 더 높은(숫자가 낮은) 스킬을 먼저 사용합니다.\n"
                "우선순위를 설정하지 않은 스킬들은 준비된 시간 순서대로 사용합니다.\n"
                "버프스킬의 우선순위를 높이는 것을 추천합니다.\n"
                "연계스킬은 우선순위가 적용되지 않습니다."
            ),
        ]

        for i in range(3):
            label = QLabel(titles[i])
            label.setToolTip(tooltips[i])
            label.setStyleSheet("QLabel { border: 0px; border-radius: 0px; }")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(CustomFont(12))
            label.setFixedSize(40, 40)
            self._grid_layout.addWidget(label, 0, i + 1, Qt.AlignmentFlag.AlignCenter)

    def _clear_rows(self) -> None:
        """기존 행들 제거"""

        for r in range(1, self._grid_layout.rowCount() + 1):
            for c in range(0, 4):
                item: QLayoutItem | None = self._grid_layout.itemAtPosition(r, c)
                if item is None:
                    continue

                w: QWidget | None = item.widget()
                if w is None:
                    continue

                self._grid_layout.removeWidget(w)
                w.deleteLater()

        self._skill_names = []
        self._usage_btns = []
        self._sole_btns = []
        self._priority_btns = []

    def _ensure_rows(self, skill_names: list[str]) -> None:
        """스킬 행 생성"""

        if skill_names == self._skill_names:
            return

        self._clear_rows()
        self._skill_names = skill_names.copy()

        for idx, name in enumerate(self._skill_names):
            # icon
            pixmap: QPixmap = get_skill_pixmap(
                shared_data=self.shared_data, skill_name=name
            )
            skill_image: SkillImage = SkillImage(parent=self, pixmap=pixmap, size=30)
            self._grid_layout.addWidget(
                skill_image, idx + 1, 0, Qt.AlignmentFlag.AlignCenter
            )

            # usage
            usage_btn = QPushButton()
            usage_btn.setStyleSheet(self._check_btn_style)
            usage_btn.setIconSize(QSize(40, 40))
            usage_btn.setFixedSize(30, 30)
            usage_btn.clicked.connect(
                partial(lambda x: self.change_skill_usage(x), idx)
            )
            self._grid_layout.addWidget(
                usage_btn, idx + 1, 1, Qt.AlignmentFlag.AlignCenter
            )
            self._usage_btns.append(usage_btn)

            # sole
            sole_btn = QPushButton()
            sole_btn.setStyleSheet(self._check_btn_style)
            sole_btn.setIconSize(QSize(40, 40))
            sole_btn.setFixedSize(30, 30)
            sole_btn.clicked.connect(partial(lambda x: self.change_use_sole(x), idx))
            self._grid_layout.addWidget(
                sole_btn, idx + 1, 2, Qt.AlignmentFlag.AlignCenter
            )
            self._sole_btns.append(sole_btn)

            # priority
            priority_btn = QPushButton("-")
            priority_btn.setFont(CustomFont(12))
            priority_btn.setFixedWidth(40)
            priority_btn.clicked.connect(
                partial(lambda x: self.change_priority(x), idx)
            )
            self._grid_layout.addWidget(
                priority_btn, idx + 1, 3, Qt.AlignmentFlag.AlignCenter
            )
            self._priority_btns.append(priority_btn)

    def update_from_preset(self, preset: "MacroPreset") -> None:
        """프리셋으로부터 위젯 상태를 업데이트"""

        skill_names: list[str] = self.shared_data.skill_data[preset.settings.server_id][
            "skills"
        ]
        self._ensure_rows(skill_names)

        for idx, name in enumerate(self._skill_names):
            setting: SkillUsageSetting = preset.usage_settings[name]

            usage_icon = QIcon(
                QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{bool(setting.is_use_skill)}.png"
                    )
                )
            )
            sole_icon = QIcon(
                QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{bool(setting.is_use_sole)}.png"
                    )
                )
            )

            self._usage_btns[idx].setIcon(usage_icon)
            self._sole_btns[idx].setIcon(sole_icon)

            p = int(setting.skill_priority)
            self._priority_btns[idx].setText("-" if p == 0 else str(p))

    def change_skill_usage(self, skill_idx: int) -> None:
        """사용 여부 변경"""

        preset: MacroPreset = self._get_preset()
        skill_name: str = self._skill_names[skill_idx]

        setting: SkillUsageSetting = preset.usage_settings[skill_name]

        setting.is_use_skill = not setting.is_use_skill

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def change_use_sole(self, skill_idx: int) -> None:
        """단독 사용 변경"""

        preset: MacroPreset = self._get_preset()
        skill_name: str = self._skill_names[skill_idx]

        setting: SkillUsageSetting | None = preset.usage_settings[skill_name]

        setting.is_use_sole = not setting.is_use_sole

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def change_priority(self, skill_idx: int) -> None:
        """스킬 우선순위 변경"""

        preset: MacroPreset = self._get_preset()
        skill_name: str = self._skill_names[skill_idx]

        # 장착된 스킬이 아니면 무시
        if skill_name not in preset.skills.active_skills:
            return

        setting: SkillUsageSetting = preset.usage_settings[skill_name]

        current = int(setting.skill_priority)

        # 우선순위가 0이었다면: 가장 높은 우선순위(숫자 최대 + 1)
        if current == 0:
            max_priority: int = 0
            for s in preset.usage_settings.values():
                max_priority = max(max_priority, s.skill_priority)

            setting.skill_priority = max_priority + 1

        # 우선순위가 설정되어 있었다면: 제거 + 뒷번호 당기기
        else:
            setting.skill_priority = 0
            for s in preset.usage_settings.values():
                if s.skill_priority > current:
                    s.skill_priority -= 1

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()


class LinkSkillSettings(QFrame):
    """사이드바 타입 3 - 연계설정 스킬 목록"""

    # draft_data
    editRequested = pyqtSignal(dict)

    def __init__(
        self,
        shared_data: SharedData,
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ) -> None:
        super().__init__()

        # self.setStyleSheet("QFrame { background-color: #FFFFFF; }")

        self.shared_data: SharedData = shared_data
        self.popup_manager: PopupManager = popup_manager
        self._on_data_changed: Callable[[], None] = on_data_changed

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.title = Title("스킬 연계설정")
        layout.addWidget(self.title)

        self.create_link_skill_btn = QPushButton("새 연계스킬 만들기")
        self.create_link_skill_btn.clicked.connect(self.create_new)
        self.create_link_skill_btn.setFont(CustomFont(16))
        layout.addWidget(self.create_link_skill_btn)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(12)
        layout.addWidget(self._list_container)

        self.update_from_preset(self._get_preset())

    def _get_preset(self) -> "MacroPreset":
        return self.shared_data.presets[self.shared_data.recent_preset]

    def _sync_preset_to_shared_data(self, preset: "MacroPreset") -> None:
        apply_preset_to_shared_data(
            self.shared_data,
            preset,
            preset_index=self.shared_data.recent_preset,
            all_presets=self.shared_data.presets,
        )

    def update_from_preset(self, preset: "MacroPreset") -> None:
        """프리셋으로부터 위젯 상태를 업데이트"""

        # 기존 목록 제거
        while self._list_layout.count():
            item: QLayoutItem | None = self._list_layout.takeAt(0)
            if item is None:
                continue

            w: QWidget | None = item.widget()
            if w is not None:
                w.deleteLater()

        for i, data in enumerate(preset.link_settings):
            link_skill = self.LinkSkill(
                self.shared_data, data, i, self.edit, self.remove
            )
            self._list_layout.addWidget(link_skill)

    def create_new(self) -> None:
        """새 연계스킬 만들기"""

        def get_unused_alpha_key() -> str:
            """알파벳 키 중에서 사용되지 않는 키를 반환"""

            for ch in "abcdefghijklmnopqrstuvwxyz":
                if not is_key_using(self.shared_data, self.shared_data.KEY_DICT[ch]):
                    return ch
            return ""

        self.popup_manager.close_popup()

        # 새 연계스킬 데이터 생성
        data: dict = {
            "useType": "manual",
            "keyType": "off",
            "key": get_unused_alpha_key(),
            "skills": [],
            "num": -1,
        }

        self.edit(-1, draft=data)

    def edit(self, num: int, draft: dict | None = None):
        """
        연계스킬 편집

        num: 편집할 연계스킬 번호 (-1이면 새로 만들기)
        draft: 임시 데이터 (주어지면 해당 데이터를 편집, 아니면 preset에서 불러옴)
        """

        self.popup_manager.close_popup()

        preset: MacroPreset = self._get_preset()

        # draft가 주어졌으면 그대로 편집(새로 만들기), 아니면 현재 데이터 복사
        if draft is not None:
            data: dict = copy.deepcopy(draft)
        else:
            data = copy.deepcopy(preset.link_settings[num])

        # 편집 요청 전달
        self.editRequested.emit(data)

    def remove(self, num: int) -> None:
        """연계스킬 제거"""

        self.popup_manager.close_popup()

        preset: MacroPreset = self._get_preset()
        del preset.link_settings[num]

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    class LinkSkill(QFrame):
        def __init__(
            self,
            shared_data: SharedData,
            data: dict,
            idx: int,
            edit_func: Callable[[int], None],
            remove_func: Callable[[int], None],
        ) -> None:
            super().__init__()

            self.shared_data: SharedData = shared_data

            edit_btn = QPushButton()
            edit_btn.clicked.connect(partial(lambda x: edit_func(x), idx))
            edit_btn.setStyleSheet(
                """QPushButton { background-color: transparent; border: 0px; }
                QPushButton:hover { background-color: rgba(0, 0, 0, 32); border: 0px solid black; border-radius: 8px; }"""
            )

            layout = QHBoxLayout()
            edit_btn.setLayout(layout)

            # 사용 스킬 개수: 최대 6개
            skill_count: int = min(len(data["skills"]), 6)
            for i in range(skill_count):
                pixmap: QPixmap = get_skill_pixmap(
                    shared_data=self.shared_data,
                    skill_name=data["skills"][i],
                )

                skill = SkillImage(
                    parent=self,
                    pixmap=pixmap,
                )
                layout.addWidget(skill)

            # layout.addStretch(1)

            if data.get("keyType") == "off":
                key_text: str = ""
            else:
                key_text = self.shared_data.KEY_DICT[data["key"]].display

            key_btn = QLabel(key_text)
            key_btn.setStyleSheet(
                "QLabel { background-color: transparent; border: 0px; }"
            )
            layout.addWidget(key_btn)

            remove_btn = QPushButton("")
            remove_btn.clicked.connect(partial(lambda x: remove_func(x), idx))
            pixmap = QPixmap(convert_resource_path("resources\\image\\x.png"))
            remove_btn.setIcon(QIcon(pixmap))
            remove_btn.setStyleSheet(
                """QPushButton { background-color: transparent; border: 0px; }
                QPushButton:hover { background-color: #dddddd; border: 0px solid black; border-radius: 18px; }"""
            )
            layout.addWidget(remove_btn)

            use_type_display = QFrame()
            use_type_display.setStyleSheet(
                f"QFrame {{ background-color: {"#0000ff" if data["useType"] == "manual" else "#ff0000"}; border: 0px solid black; border-radius: 2px; }}"
            )
            layout.addWidget(use_type_display)


class LinkSkillEditor(QFrame):
    """사이드바 타입 4 - 연계설정 편집"""

    # 편집 종료(취소/저장) 후 목록으로 돌아가기 위한 시그널
    closed = pyqtSignal()
    saved = pyqtSignal()
    contentResized = pyqtSignal()

    # todo: 링크스킬 데이터를 클래스로 관리하도록 수정
    def __init__(
        self,
        shared_data: SharedData,
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ) -> None:
        super().__init__()

        self.shared_data: SharedData = shared_data
        self.popup_manager: PopupManager = popup_manager
        self._on_data_changed: Callable[[], None] = on_data_changed

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(5)
        self.setLayout(layout)

        self.title = Title("연계스킬 편집")
        layout.addWidget(self.title, 0, Qt.AlignmentFlag.AlignCenter)

        self.type_setting = self.SettingItem(
            title="연계 유형",
            tooltip=(
                "자동: 매크로가 실행 중일 때 자동으로 연계 스킬을 사용합니다. 자동 연계스킬에 사용되는 스킬은 다른 자동 연계스킬에 사용될 수 없습니다.\n"
                "연계스킬은 매크로 작동 여부와 관계 없이 단축키를 입력해서 작동시킬 수 있습니다."
            ),
            btn0_text="자동",
            btn1_text="수동",
            is_btn0_enabled=True,
            is_btn1_enabled=False,
            func0=self.set_auto,
            func1=self.set_manual,
        )
        layout.addWidget(self.type_setting)

        self.key_setting = self.SettingItem(
            title="단축키",
            tooltip=(
                "매크로가 실행 중이지 않을 때 해당 연계스킬을 작동시킬 단축키입니다."
            ),
            btn0_text="설정안함",
            btn1_text="",
            is_btn0_enabled=True,
            is_btn1_enabled=False,
            func0=self.clear_key,
            func1=self.on_key_btn_clicked,
        )
        layout.addWidget(self.key_setting)

        # 연계 스킬 구성 목록
        self._skills_container = QWidget(self)
        self._skills_layout = QVBoxLayout(self._skills_container)
        self._skills_layout.setContentsMargins(0, 10, 0, 10)
        self._skills_layout.setSpacing(6)
        layout.addWidget(self._skills_container)

        # 현재 화면에 그려진 SkillItem 위젯들
        self._skill_item_widgets: list[LinkSkillEditor.SkillItem] = []

        self.add_skill_btn = QPushButton()
        self.add_skill_btn.clicked.connect(self.add_skill)
        self.add_skill_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent; border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
            """
        )
        pixmap = QPixmap(convert_resource_path("resources\\image\\plus.png"))
        self.add_skill_btn.setIcon(QIcon(pixmap))
        self.add_skill_btn.setIconSize(QSize(24, 24))
        layout.addWidget(self.add_skill_btn)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.setFont(CustomFont(12))
        layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("저장")
        self.save_btn.clicked.connect(self.save)
        self.save_btn.setFont(CustomFont(12))
        layout.addWidget(self.save_btn)

        self.data: dict = {}

    def _get_preset(self) -> "MacroPreset":
        return self.shared_data.presets[self.shared_data.recent_preset]

    def _sync_preset_to_shared_data(self, preset: "MacroPreset") -> None:
        apply_preset_to_shared_data(
            self.shared_data,
            preset,
            preset_index=self.shared_data.recent_preset,
            all_presets=self.shared_data.presets,
        )

    def load(self, data: dict) -> None:
        """연계스킬 데이터 로드"""

        self.data = data

        self._after_data_changed(update_skills=True)

    def _after_data_changed(self, update_skills: bool) -> None:
        """self.data 변경 이후 UI 갱신을 한 곳으로 모음."""

        self._refresh_ui()
        if update_skills:
            self._refresh_skill_items()

    def _refresh_ui(self) -> None:
        """현재 self.data 상태에 맞춰 UI(버튼 색/텍스트)를 동기화."""

        # 연계 유형 버튼
        use_type: str = self.data["useType"]
        self.type_setting.set_buttons_enabled(use_type == "auto", use_type == "manual")

        # 단축키 버튼
        key_type: str = self.data["keyType"]
        if key_type == "on":
            key_text: str = self.shared_data.KEY_DICT[self.data["key"]].display
        else:
            key_text = ""

        self.key_setting.set_right_button_text(key_text)
        self.key_setting.set_buttons_enabled(key_type == "off", key_type == "on")

    def _get_all_skill_names(self) -> list[str]:
        """프리셋의 전체 스킬 목록을 반환"""

        preset: MacroPreset = self._get_preset()
        return self.shared_data.skill_data[preset.settings.server_id]["skills"]

    def _refresh_skill_items(self) -> None:
        """self.data['skills']로 스킬 구성 UI를 다시 그림"""

        # 기존 위젯 제거
        for widget in self._skill_item_widgets:
            self._skills_layout.removeWidget(widget)
            widget.deleteLater()

        # 캐시 리스트 초기화
        self._skill_item_widgets = []

        for idx, name in enumerate(self.data["skills"]):
            skill_widget = self.SkillItem(
                index=idx,
                name=name,
                shared_data=self.shared_data,
            )
            skill_widget.changeRequested.connect(self._open_skill_select_popup)
            skill_widget.removeRequested.connect(self._remove_skill_and_refresh)

            self._skills_layout.addWidget(skill_widget)
            self._skill_item_widgets.append(skill_widget)

        # 페이지 크기 갱신
        QTimer.singleShot(0, self.contentResized.emit)

    def _remove_skill_and_refresh(self, i: int) -> None:
        """i번째 스킬 제거 후 UI 갱신"""

        # remove_skill 내부에서 UI 갱신을 수행하므로 중복 갱신을 피한다.
        self.remove_skill(i)

    def _open_skill_select_popup(self, i: int) -> None:
        """i번째 스킬 변경용 스킬 선택 팝업 열기"""

        self.popup_manager.close_popup()

        # anchor: i번째 SkillItem의 스킬 버튼
        anchor_btn: QPushButton = self._skill_item_widgets[i].skill

        def apply(skill_name: str) -> None:
            self.change_skill(i, skill_name)

        self.popup_manager.make_link_skill_select_popup(
            anchor=anchor_btn,
            skill_names=self._get_all_skill_names(),
            on_selected=apply,
        )

    def set_auto(self) -> None:
        """연계스킬을 자동 사용으로 설정"""

        self.popup_manager.close_popup()

        # 이미 자동이면 무시
        if self.data["useType"] == "auto":
            return

        preset: MacroPreset = self._get_preset()

        # 모든 스킬이 장착되어 있는지 확인
        if not all(i in preset.skills.active_skills for i in self.data["skills"]):
            self.popup_manager.make_notice_popup("skillNotSelected")
            return

        # 지금 수정 중인 연계스킬의 인덱스
        # todo: 리스트 reference로 변경 후 제거
        num: int = self.data["num"]

        # 자동 연계스킬 스킬 중복 검사
        auto_skills: list[str] = []
        for i, link_skill in enumerate(preset.link_settings):
            # 자기 자신은 무시
            if i == num:
                continue

            # 자동 연계스킬인 경우
            if link_skill["useType"] == "auto":
                for j in link_skill["skills"]:
                    auto_skills.append(j)

        # 중복되는 스킬이 있으면 알림 팝업 생성 후 종료
        for i in self.data["skills"]:
            if i in auto_skills:
                self.popup_manager.make_notice_popup("autoAlreadyExist")
                return

        # 중복되는 스킬이 없으면 자동으로 변경
        self.data["useType"] = "auto"
        self._after_data_changed(update_skills=False)

    def set_manual(self) -> None:
        """연계스킬을 수동 사용으로 설정"""

        self.popup_manager.close_popup()

        # 이미 수동이면 무시
        if self.data["useType"] == "manual":
            return

        # 수동으로 변경
        self.data["useType"] = "manual"
        self._after_data_changed(update_skills=False)

    def clear_key(self) -> None:
        """단축키 설정 해제"""

        self.popup_manager.close_popup()

        self.data["keyType"] = "off"
        self._after_data_changed(update_skills=False)

    def on_key_btn_clicked(self) -> None:
        """연계스킬 단축키 설정 버튼 클릭 시"""

        def apply(key: KeySpec) -> None:
            """적용 함수"""

            self.data["keyType"] = "on"
            self.data["key"] = key.key_id
            self._after_data_changed(update_skills=False)

        self.popup_manager.close_popup()
        self.popup_manager.make_link_skill_key_popup(
            self.key_setting.right_button,
            self.shared_data.KEY_DICT[self.data["key"]],
            apply,
        )

    def change_skill(self, i: int, skill_name: str) -> None:
        """i번째 스킬을 skill_name으로 변경"""

        self.popup_manager.close_popup()

        # 동일 스킬 선택 시 무시
        if self.data["skills"][i] == skill_name:
            return

        # 스킬명 설정, 사용횟수 초기화
        self.data["skills"][i] = skill_name

        # 수동 사용으로 변경
        self.data["useType"] = "manual"

        if self.is_skill_exceeded(skill_name):
            self.popup_manager.make_notice_popup("exceedMaxLinkSkill")

        self._after_data_changed(update_skills=True)

    def remove_skill(self, i: int) -> None:
        """i번째 스킬 제거"""

        self.popup_manager.close_popup()

        # 스킬 제거
        self.data["skills"].pop(i)

        # 수동 사용으로 변경
        self.data["useType"] = "manual"

        self._after_data_changed(update_skills=True)

    def add_skill(self) -> None:
        """스킬 추가"""

        self.popup_manager.close_popup()

        preset: MacroPreset = self._get_preset()

        name: str = self.shared_data.skill_data[preset.settings.server_id]["skills"][0]
        self.data["skills"].append(name)

        # 수동 사용으로 변경
        self.data["useType"] = "manual"

        # 최대 사용 횟수 초과 시 알림 팝업 생성
        if self.is_skill_exceeded(name):
            self.popup_manager.make_notice_popup("exceedMaxLinkSkill")

        # 추가 직후 바로 선택 팝업을 띄워서 변경할 수 있게 한다.
        self._after_data_changed(update_skills=True)
        self._open_skill_select_popup(len(self.data["skills"]) - 1)

    def cancel(self) -> None:
        """편집 취소"""

        self.popup_manager.close_popup()
        self.closed.emit()

    def save(self) -> None:
        """편집 저장"""

        self.popup_manager.close_popup()

        preset: MacroPreset = self._get_preset()

        # 수정하던 연계스킬의 인덱스
        index: int = self.data["num"]

        # 저장 시 편집용 필드 제거
        store_data: dict = self.data
        store_data.pop("num", None)

        # 새로 만드는 경우
        if index == -1:
            preset.link_settings.append(store_data)

        # 기존 연계스킬 수정하는 경우
        else:
            preset.link_settings[index] = store_data

        self._sync_preset_to_shared_data(preset)
        self._on_data_changed()

        self.saved.emit()
        self.closed.emit()

    def is_skill_exceeded(self, skill_name: str) -> bool:
        """연계스킬에서 특정 스킬의 최대 사용 횟수를 초과하는지 확인"""

        count: int = self.data["skills"].count(skill_name)

        # 최대 사용 횟수 초과 여부 반환
        return count > 1

    class SkillItem(QFrame):
        changeRequested = pyqtSignal(int)
        removeRequested = pyqtSignal(int)

        def __init__(
            self,
            index: int,
            name: str,
            shared_data: SharedData,
        ) -> None:
            super().__init__()

            self.index: int = int(index)

            self.skill = QPushButton()
            self.skill.clicked.connect(self._emit_change)
            self.skill.setIcon(QIcon(get_skill_pixmap(shared_data, name)))
            # skill.setIconSize(QSize(50, 50))
            self.skill.setIconSize(QSize(36, 36))
            self.skill.setFixedSize(44, 44)
            self.skill.setToolTip(
                "연계스킬을 구성하는 스킬의 목록과 사용 횟수를 설정할 수 있습니다.\n하나의 스킬이 너무 많이 사용되면 연계가 정상적으로 작동하지 않을 수 있습니다."
            )

            self.remove = QPushButton()
            self.remove.clicked.connect(self._emit_remove)
            self.remove.setStyleSheet(
                """QPushButton {
                    background-color: transparent; border-radius: 16px;
                }
                QPushButton:hover {
                    background-color: #eeeeee;
                }"""
            )
            pixmap = QPixmap(convert_resource_path("resources\\image\\xAlpha.png"))
            self.remove.setIcon(QIcon(pixmap))
            self.remove.setIconSize(QSize(16, 16))
            self.remove.setFixedSize(32, 32)

            layout = QHBoxLayout()
            layout.addWidget(self.skill)
            layout.addStretch(1)
            layout.addWidget(self.remove)
            layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(layout)

        def _emit_change(self) -> None:
            self.changeRequested.emit(self.index)

        def _emit_remove(self) -> None:
            self.removeRequested.emit(self.index)

    class SettingItem(QFrame):
        def __init__(
            self,
            title: str,
            tooltip: str,
            btn0_text: str,
            btn1_text: str,
            is_btn0_enabled: bool,
            is_btn1_enabled: bool,
            func0: Callable[[], None],
            func1: Callable[[], None],
        ) -> None:
            super().__init__()

            self.title = QLabel(title)
            self.title.setToolTip(tooltip)
            self.title.setFont(CustomFont(12))

            self._color_dict: dict[bool, str] = {
                True: "#000000",
                False: "#999999",
            }

            self.left_button = QPushButton(btn0_text)
            self.left_button.clicked.connect(lambda: func0())
            self.left_button.setStyleSheet(
                f"color: {self._color_dict[is_btn0_enabled]};"
            )
            self.left_button.setFont(CustomFont(12))

            self.right_button = QPushButton(btn1_text)
            self.right_button.clicked.connect(lambda: func1())
            self.right_button.setStyleSheet(
                f"color: {self._color_dict[is_btn1_enabled]};"
            )
            self.right_button.setFont(CustomFont(12))

            layout = QHBoxLayout()
            layout.addWidget(self.title)
            layout.addStretch(1)
            layout.addWidget(self.left_button)
            layout.addWidget(self.right_button)
            self.setLayout(layout)

        def set_buttons_enabled(self, left_enabled: bool, right_enabled: bool) -> None:
            """양쪽 버튼 활성화(강조) 상태를 설정 (기능 enable/disable이 아니라 색상 표시)."""

            self.left_button.setStyleSheet(f"color: {self._color_dict[left_enabled]};")
            self.right_button.setStyleSheet(
                f"color: {self._color_dict[right_enabled]};"
            )

        def set_left_button_text(self, text: str) -> None:
            """왼쪽 버튼 텍스트 설정"""

            self.left_button.setText(text)

        def set_right_button_text(self, text: str) -> None:
            """오른쪽 버튼 텍스트 설정"""

            self.right_button.setText(text)


class NavigationButtons(QFrame):
    def __init__(
        self,
        change_page: Callable[[Literal[0, 1, 2, 3]], None],
        change_layout: Callable[[int], None],
    ) -> None:
        super().__init__()

        self.change_page: Callable[[Literal[0, 1, 2, 3]], None] = change_page
        self.change_layout: Callable[[int], None] = change_layout

        self.setStyleSheet(
            """
            QFrame {
                background-color: #ffffff; 
            }
            """
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 30, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        icons: list[QPixmap] = [
            QPixmap(convert_resource_path("resources\\image\\setting.png")),
            QPixmap(convert_resource_path("resources\\image\\usageSetting.png")),
            QPixmap(convert_resource_path("resources\\image\\linkSetting.png")),
            QPixmap(convert_resource_path("resources\\image\\simulationSidebar.png")),
        ]
        border_widthes: list[list[int]] = [
            [0, 8, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 8],
        ]
        border_widths: list[list[int]] = [
            # top, right, bottom, left
            [1, 1, 1, 0],
            [0, 1, 1, 0],
            [0, 1, 1, 0],
            [0, 1, 1, 0],
        ]

        self.buttons: list[NavigationButtons.NavigationButton] = [
            self.NavigationButton(
                icon=icons[i],
                border_radius=border_widthes[i],
                border_width=border_widths[i],
            )
            for i in range(4)
        ]

        for idx, button in enumerate(self.buttons):
            layout.addWidget(button)

            if idx != 3:
                button.clicked.connect(partial(lambda x: self.change_page(x), idx))
            else:
                button.clicked.connect(lambda: self.change_layout(1))

        layout.addStretch(1)

    def set_active_button(self, index: int) -> None:
        """활성화된 버튼 설정"""

        for i, button in enumerate(self.buttons):
            button.set_active(i == index)

    class NavigationButton(QPushButton):
        def __init__(
            self, icon: QPixmap, border_radius: list[int], border_width: list[int]
        ) -> None:
            super().__init__()

            self.base_style: str = f"""
                QPushButton {{
                    background-color: #FFFFFF; 
                    border: 0px solid #b4b4b4;
                    border-top-width: {border_width[0]}px;
                    border-right-width: {border_width[1]}px;
                    border-bottom-width: {border_width[2]}px;
                    border-left-width: {border_width[3]}px;
                    border-top-left-radius: {border_radius[0]}px; 
                    border-top-right-radius: {border_radius[1]}px; 
                    border-bottom-left-radius: {border_radius[2]}px; 
                    border-bottom-right-radius: {border_radius[3]}px;
                }}
                QPushButton:hover {{
                    background-color: #F0F0F0;
                }}
            """

            self.active_style: str = (
                self.base_style + "QPushButton { background-color: #E0E0E0; }"
            )

            self.setStyleSheet(self.base_style)

            self.setIcon(QIcon(icon))
            self.setIconSize(QSize(32, 32))

        def set_active(self, active: bool) -> None:
            """버튼 활성화 상태 설정"""

            if active:
                self.setStyleSheet(self.active_style)
            else:
                self.setStyleSheet(self.base_style)


class Title(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setFont(CustomFont(20))
        self.setStyleSheet(
            "border: 0px solid black; border-radius: 10px; background-color: #CADEFC;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setFixedSize(250, 80)
