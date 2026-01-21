from __future__ import annotations

import copy
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Literal

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayoutItem,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.scripts.app_state import app_state
from app.scripts.config import config
from app.scripts.custom_classes import CustomFont, SkillImage
from app.scripts.data_manager import apply_preset_to_app_state
from app.scripts.macro_models import (
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    MacroPreset,
    SkillUsageSetting,
)
from app.scripts.registry.key_registry import KeyRegistry, KeySpec
from app.scripts.registry.resource_registry import (
    convert_resource_path,
    resource_registry,
)

if TYPE_CHECKING:
    from typing import Literal

    from app.scripts.registry.server_registry import ServerSpec
    from app.scripts.ui.main_window import MainWindow
    from app.scripts.ui.popup import PopupManager


class Sidebar(QFrame):
    """좌측 사이드바 클래스"""

    dataChanged = pyqtSignal()

    def __init__(
        self,
        master: MainWindow,
        preset: "MacroPreset",
        preset_index: int,
    ) -> None:
        super().__init__(master)

        self.setStyleSheet("QFrame { background-color: #FFFFFF; }")

        self.master: MainWindow = master

        self.preset: MacroPreset = preset
        self.preset_index: int = preset_index

        self.popup_manager: PopupManager = self.master.get_popup_manager()

        # 사이드바 페이지들
        self.general_settings = GeneralSettings(
            self.popup_manager,
            on_data_changed=self.dataChanged.emit,
        )
        self.skill_settings = SkillSettings(
            self.popup_manager,
            on_data_changed=self.dataChanged.emit,
        )
        self.link_skill_settings = LinkSkillSettings(
            self.popup_manager,
            on_data_changed=self.dataChanged.emit,
        )
        self.link_skill_editor = LinkSkillEditor(
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

        # 연계스킬 목록 내용 변화(추가/삭제/갱신) 시 사이드바 높이 동기화
        self.link_skill_settings.contentResized.connect(self.adjust_stack_height)

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

    def _on_link_skill_edit_requested(self, index: int, data: LinkSkill) -> None:
        """연계스킬 편집 요청 처리: 편집기 로드 후 편집 페이지로 이동."""

        self.link_skill_editor.load(data, int(index))
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

        if self.page_navigator.currentIndex() == 3:
            self.link_skill_editor.cancel()

        self.update_from_preset()

        self.change_page(0)

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

    def refresh_skill_related_pages(self) -> None:
        """
        스킬 장착/해제에 영향 받는 페이지만 업데이트

        - 스킬 사용설정(우선순위/사용여부 등)
        - 연계설정(자동/수동 표시 등)
        """

        self.skill_settings.update_from_preset(self.preset)
        self.link_skill_settings.update_from_preset(self.preset)

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
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ) -> None:
        super().__init__()

        # self.setStyleSheet("QFrame { background-color: #FFFFFF; }")

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
            btn0_text=f"기본: {config.specs.DELAY.default}",
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
            btn0_text=f"기본: {config.specs.COOLTIME_REDUCTION.default}",
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
            btn0_text=f"기본: {config.specs.DEFAULT_START_KEY.display}",
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

        self.update_from_preset(app_state.macro.current_preset)

    def _sync_preset_to_app_state(self, preset: "MacroPreset") -> None:
        """프리셋을 app_state에 동기화"""

        apply_preset_to_app_state(
            preset,
            preset_index=app_state.macro.current_preset_index,
            all_presets=app_state.macro.presets,
        )

    def update_from_preset(self, preset: "MacroPreset") -> None:
        """프리셋으로부터 위젯 상태를 업데이트"""

        # 서버 - 직업
        self.server_job_setting.set_left_button_text(preset.settings.server_id)

        # 딜레이
        custom_delay: int = preset.settings.custom_delay
        use_custom_delay: bool = preset.settings.use_custom_delay
        self.delay_setting.set_right_button_text(str(custom_delay))
        self.delay_setting.set_buttons_enabled(not use_custom_delay, use_custom_delay)

        # 쿨타임 감소
        custom_cooltime_reduction: int = preset.settings.custom_cooltime_reduction
        use_custom_cooltime_reduction: bool = (
            preset.settings.use_custom_cooltime_reduction
        )
        self.cooltime_setting.set_right_button_text(str(custom_cooltime_reduction))
        self.cooltime_setting.set_buttons_enabled(
            not use_custom_cooltime_reduction, use_custom_cooltime_reduction
        )

        # 시작키 설정
        custom_start_key: str = preset.settings.custom_start_key
        use_custom_start_key: bool = preset.settings.use_custom_start_key
        self.start_key_setting.set_right_button_text(custom_start_key)
        self.start_key_setting.set_buttons_enabled(
            not use_custom_start_key, use_custom_start_key
        )

        # 마우스 클릭
        self.click_setting.set_buttons_enabled(
            preset.settings.use_default_attack == 0,
            preset.settings.use_default_attack == 1,
        )

    def on_servers_clicked(self) -> None:
        """서버 목록 클릭시 실행"""

        def apply(server: ServerSpec) -> None:
            """적용 함수"""

            if server.id == app_state.macro.current_preset.settings.server_id:
                return

            app_state.macro.current_preset.settings.server_id = server.id
            self._sync_preset_to_app_state(app_state.macro.current_preset)
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        self.popup_manager.close_popup()

        self.popup_manager.make_server_popup(self.server_job_setting.left_button, apply)

    def on_default_delay_clicked(self) -> None:
        """기본 딜레이 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 이미 기본 딜레이라면 무시
        if not app_state.macro.current_preset.settings.use_custom_delay:
            return

        # 기본 딜레이로 변경 (입력 값은 유지)
        app_state.macro.current_preset.settings.use_custom_delay = False
        self._sync_preset_to_app_state(app_state.macro.current_preset)
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_user_delay_clicked(self) -> None:
        """유저 딜레이 클릭시 실행"""

        def apply(delay_value: int) -> None:
            """적용 함수"""

            # 변경 사항이 없으면 무시
            if delay_value == app_state.macro.current_preset.settings.custom_delay:
                return

            app_state.macro.current_preset.settings.custom_delay = int(delay_value)
            app_state.macro.current_preset.settings.use_custom_delay = True
            self._sync_preset_to_app_state(app_state.macro.current_preset)
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 이미 유저 딜레이라면 딜레이 입력 팝업 열기
        if app_state.macro.current_preset.settings.use_custom_delay:
            self.popup_manager.make_delay_popup(self.delay_setting.right_button, apply)
            return

        # 유저 딜레이로 변경 (입력 값 유지)
        app_state.macro.current_preset.settings.use_custom_delay = True
        self._sync_preset_to_app_state(app_state.macro.current_preset)
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_default_cooltime_clicked(self) -> None:
        """기본 쿨타임 감소 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 이미 기본 쿨타임 감소라면 무시
        if not app_state.macro.current_preset.settings.use_custom_cooltime_reduction:
            return

        # 기본 쿨타임 감소로 변경 (입력 값은 유지)
        app_state.macro.current_preset.settings.use_custom_cooltime_reduction = False
        self._sync_preset_to_app_state(app_state.macro.current_preset)
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_user_cooltime_clicked(self) -> None:
        """유저 쿨타임 감소 클릭시 실행"""

        def apply(cooltime_value: int) -> None:
            """적용 함수"""

            if (
                cooltime_value
                == app_state.macro.current_preset.settings.custom_cooltime_reduction
            ):
                return

            app_state.macro.current_preset.settings.custom_cooltime_reduction = int(
                cooltime_value
            )
            self._sync_preset_to_app_state(app_state.macro.current_preset)
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 이미 유저 쿨타임 감소라면 쿨타임 감소 입력 팝업 열기
        if app_state.macro.current_preset.settings.use_custom_cooltime_reduction:
            self.popup_manager.make_cooltime_popup(
                self.cooltime_setting.right_button, apply
            )
            return

        # 유저 쿨타임 감소로 변경 (입력 값 유지)
        app_state.macro.current_preset.settings.use_custom_cooltime_reduction = True
        self._sync_preset_to_app_state(app_state.macro.current_preset)
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_default_start_key_clicked(self) -> None:
        """기본 시작키 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 이미 기본 시작키라면 무시
        if not app_state.macro.current_preset.settings.use_custom_start_key:
            return

        default_key: KeySpec = config.specs.DEFAULT_START_KEY

        # 유저 입력 키가 기본키와 다르고, 기본키가 다른 용도로 사용 중이면 변경 불가
        if (
            app_state.macro.current_preset.settings.custom_start_key
            != default_key.key_id
            and app_state.is_key_using(default_key)
        ):
            self.popup_manager.make_notice_popup("StartKeyChangeError")
            return

        # 기본 시작키로 변경 (입력 값은 유지)
        app_state.macro.current_preset.settings.use_custom_start_key = False

        self._sync_preset_to_app_state(app_state.macro.current_preset)
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_user_start_key_clicked(self) -> None:
        """유저 시작키 클릭시 실행"""

        def apply(start_key: KeySpec) -> None:
            """적용 함수"""

            if (
                start_key.key_id
                == app_state.macro.current_preset.settings.custom_start_key
            ):
                return

            app_state.macro.current_preset.settings.custom_start_key = start_key.key_id
            self._sync_preset_to_app_state(app_state.macro.current_preset)
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 이미 유저 시작키라면 시작키 입력 팝업 열기
        if app_state.macro.current_preset.settings.use_custom_start_key:
            self.popup_manager.make_start_key_popup(
                self.start_key_setting.right_button, apply
            )
            return

        default_key: KeySpec = config.specs.DEFAULT_START_KEY
        current_input_key_id: str = (
            app_state.macro.current_preset.settings.custom_start_key
        )

        # 유저 입력 키가 기본키와 다르고, 유저키가 다른 용도로 사용 중이면 변경 불가
        if current_input_key_id != default_key.key_id and app_state.is_key_using(
            KeyRegistry.MAP[current_input_key_id]
        ):
            self.popup_manager.make_notice_popup("StartKeyChangeError")
            return

        # 유저 시작키로 변경 (입력 값 유지)
        app_state.macro.current_preset.settings.use_custom_start_key = True
        self._sync_preset_to_app_state(app_state.macro.current_preset)
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_mouse_type0_clicked(self) -> None:
        """평타 사용 안함 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 이미 False 라면 무시
        if not app_state.macro.current_preset.settings.use_default_attack:
            return

        app_state.macro.current_preset.settings.use_default_attack = False
        self._sync_preset_to_app_state(app_state.macro.current_preset)
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_mouse_type1_clicked(self) -> None:
        """평타 사용 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.make_notice_popup("MacroIsRunning")
            return

        # 이미 타입1 이라면 무시
        if app_state.macro.current_preset.settings.use_default_attack:
            return

        app_state.macro.current_preset.settings.use_default_attack = True
        self._sync_preset_to_app_state(app_state.macro.current_preset)
        self.update_from_preset(app_state.macro.current_preset)
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

            # 마우스 포인터 설정
            self.left_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.right_button.setCursor(Qt.CursorShape.PointingHandCursor)

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
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ):
        super().__init__()

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

        self._skill_ids: list[str] = []
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
        return app_state.macro.presets[app_state.macro.current_preset_index]

    def _sync_preset_to_shared_data(self, preset: "MacroPreset") -> None:
        apply_preset_to_app_state(
            preset,
            preset_index=app_state.macro.current_preset_index,
            all_presets=app_state.macro.presets,
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

        self._skill_ids = []
        self._usage_btns = []
        self._sole_btns = []
        self._priority_btns = []

    def _ensure_rows(self, skill_ids: list[str]) -> None:
        """스킬 행 생성"""

        if skill_ids == self._skill_ids:
            return

        self._clear_rows()
        self._skill_ids = skill_ids.copy()

        for idx, skill_id in enumerate(self._skill_ids):
            # 스킬 아이콘
            # todo: 스킬 이름을 표시하도록 변경
            pixmap: QPixmap = resource_registry.get_skill_pixmap(skill_id=skill_id)
            skill_image: SkillImage = SkillImage(parent=self, pixmap=pixmap, size=30)
            self._grid_layout.addWidget(
                skill_image, idx + 1, 0, Qt.AlignmentFlag.AlignCenter
            )

            # 스킬 사용 여부
            usage_btn = QPushButton()
            usage_btn.setStyleSheet(self._check_btn_style)
            usage_btn.setIconSize(QSize(40, 40))
            usage_btn.setFixedSize(30, 30)
            usage_btn.clicked.connect(
                partial(lambda x: self.change_skill_usage(x), idx)
            )
            usage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._grid_layout.addWidget(
                usage_btn, idx + 1, 1, Qt.AlignmentFlag.AlignCenter
            )
            self._usage_btns.append(usage_btn)

            # 스킬 단독 사용 여부
            sole_btn = QPushButton()
            sole_btn.setStyleSheet(self._check_btn_style)
            sole_btn.setIconSize(QSize(40, 40))
            sole_btn.setFixedSize(30, 30)
            sole_btn.clicked.connect(partial(lambda x: self.change_use_sole(x), idx))
            sole_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._grid_layout.addWidget(
                sole_btn, idx + 1, 2, Qt.AlignmentFlag.AlignCenter
            )
            self._sole_btns.append(sole_btn)

            # 스킬 우선순위
            priority_btn = QPushButton("-")
            priority_btn.setFont(CustomFont(12))
            priority_btn.setFixedWidth(40)
            priority_btn.clicked.connect(
                partial(lambda x: self.change_priority(x), idx)
            )
            priority_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._grid_layout.addWidget(
                priority_btn, idx + 1, 3, Qt.AlignmentFlag.AlignCenter
            )
            self._priority_btns.append(priority_btn)

    def update_from_preset(self, preset: "MacroPreset") -> None:
        """프리셋으로부터 위젯 상태를 업데이트"""

        skill_ids: list[str] = (
            app_state.macro.current_server.skill_registry.get_all_skill_ids()
        )
        self._ensure_rows(skill_ids)

        for idx, skill_id in enumerate(self._skill_ids):
            setting: SkillUsageSetting = preset.usage_settings[skill_id]

            usage_icon = QIcon(
                QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{bool(setting.use_skill)}.png"
                    )
                )
            )
            sole_icon = QIcon(
                QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{bool(setting.use_alone)}.png"
                    )
                )
            )

            self._usage_btns[idx].setIcon(usage_icon)
            self._sole_btns[idx].setIcon(sole_icon)

            p = int(setting.priority)
            self._priority_btns[idx].setText("-" if p == 0 else str(p))

    def change_skill_usage(self, skill_idx: int) -> None:
        """사용 여부 변경"""

        preset: MacroPreset = self._get_preset()
        skill_id: str = self._skill_ids[skill_idx]

        setting: SkillUsageSetting = preset.usage_settings[skill_id]

        setting.use_skill = not setting.use_skill

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def change_use_sole(self, skill_idx: int) -> None:
        """단독 사용 변경"""

        preset: MacroPreset = self._get_preset()
        skill_id: str = self._skill_ids[skill_idx]

        setting: SkillUsageSetting = preset.usage_settings[skill_id]

        setting.use_alone = not setting.use_alone

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

    def change_priority(self, skill_idx: int) -> None:
        """스킬 우선순위 변경"""

        preset: MacroPreset = self._get_preset()
        skill_id: str = self._skill_ids[skill_idx]

        # 장착된 스킬이 아니면 무시
        if skill_id not in preset.skills.equipped_skills:
            return

        setting: SkillUsageSetting = preset.usage_settings[skill_id]

        current = int(setting.priority)

        # 우선순위가 0이었다면: 가장 높은 우선순위(숫자 최대 + 1)
        if current == 0:
            max_priority: int = 0
            for s in preset.usage_settings.values():
                max_priority = max(max_priority, s.priority)

            setting.priority = max_priority + 1

        # 우선순위가 설정되어 있었다면: 제거 + 뒷번호 당기기
        else:
            setting.priority = 0
            for s in preset.usage_settings.values():
                if s.priority > current:
                    s.priority -= 1

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()


class LinkSkillSettings(QFrame):
    """사이드바 타입 3 - 연계설정 스킬 목록"""

    editRequested = pyqtSignal(int, object)
    contentResized = pyqtSignal()

    def __init__(
        self,
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ) -> None:
        super().__init__()

        # self.setStyleSheet("QFrame { background-color: #FFFFFF; }")

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
        self.create_link_skill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.create_link_skill_btn)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(20)
        layout.addWidget(self._list_container)

        self.update_from_preset(self._get_preset())

    def _get_preset(self) -> "MacroPreset":
        return app_state.macro.presets[app_state.macro.current_preset_index]

    def _sync_preset_to_shared_data(self, preset: "MacroPreset") -> None:
        apply_preset_to_app_state(
            preset,
            preset_index=app_state.macro.current_preset_index,
            all_presets=app_state.macro.presets,
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
            link_skill = self.LinkSkillWidget(data, i, self.edit, self.remove)
            self._list_layout.addWidget(link_skill)

        QTimer.singleShot(0, self.contentResized.emit)

    def create_new(self) -> None:
        """새 연계스킬 만들기"""

        self.popup_manager.close_popup()

        # 새 연계스킬 데이터 생성
        data: LinkSkill = LinkSkill(
            use_type=LinkUseType.MANUAL,
            key_type=LinkKeyType.OFF,
            key=None,
            skills=[],
        )

        self.edit(-1, draft=data)

    def edit(self, num: int, draft: LinkSkill | None = None) -> None:
        """
        연계스킬 편집

        num: 편집할 연계스킬 번호 (-1이면 새로 만들기)
        draft: 임시 데이터 (주어지면 해당 데이터를 편집, 아니면 preset에서 불러옴)
        """

        self.popup_manager.close_popup()

        preset: MacroPreset = self._get_preset()

        # draft가 주어졌으면 그대로 편집(새로 만들기), 아니면 현재 데이터 복사
        if draft is None:
            data: LinkSkill = copy.deepcopy(preset.link_settings[num])
        else:
            data = copy.deepcopy(draft)

        # 편집 요청 전달
        self.editRequested.emit(num, data)

    def remove(self, num: int) -> None:
        """연계스킬 제거"""

        self.popup_manager.close_popup()

        preset: MacroPreset = self._get_preset()
        del preset.link_settings[num]

        self._sync_preset_to_shared_data(preset)
        self.update_from_preset(preset)
        self._on_data_changed()

        QTimer.singleShot(0, self.contentResized.emit)

    class LinkSkillWidget(QFrame):
        def __init__(
            self,
            data: LinkSkill,
            idx: int,
            edit_func: Callable[[int], None],
            remove_func: Callable[[int], None],
        ) -> None:
            super().__init__()

            self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
            self.setMaximumWidth(270)

            self.setStyleSheet(
                "QFrame { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px; }"
            )

            # 그림자 효과 추가 (카드 입체감)
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(15)
            shadow.setXOffset(0)
            shadow.setYOffset(4)
            shadow.setColor(QColor(0, 0, 0, 20))
            self.setGraphicsEffect(shadow)

            # 전체 레이아웃
            root = QVBoxLayout()
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(10)
            self.setLayout(root)

            # 스킬 표시 컨테이너
            skill_container = QFrame()
            skill_container.setStyleSheet(
                "QFrame { background-color: transparent; border: 0px; }"
            )

            skill_layout = QVBoxLayout()
            skill_layout.setContentsMargins(0, 0, 0, 0)
            skill_layout.setSpacing(4)
            skill_container.setLayout(skill_layout)
            root.addWidget(skill_container)

            icon_size = 28
            skill_count: int = len(data.skills)
            rows: int = (skill_count - 1) // 7 + 1

            for r in range(rows):
                skill_row = QHBoxLayout()
                skill_row.setContentsMargins(0, 0, 0, 0)
                skill_row.setSpacing(4)
                skill_row.addStretch(1)
                skill_layout.addLayout(skill_row)

                for i in range(r * 7, min((r + 1) * 7, skill_count)):
                    slot_frame = QFrame()
                    slot_frame.setFixedSize(icon_size, icon_size)
                    slot_frame.setStyleSheet(
                        """
                        QFrame {
                            background-color: #F8F9FA;
                            border: 0px solid;
                            border-radius: 2px;
                        }
                    """
                    )
                    slot_layout = QVBoxLayout(slot_frame)
                    slot_layout.setContentsMargins(0, 0, 0, 0)

                    pixmap: QPixmap = resource_registry.get_skill_pixmap(
                        skill_id=data.skills[i],
                    )

                    skill = SkillImage(parent=slot_frame, pixmap=pixmap, size=icon_size)
                    slot_layout.addWidget(skill, alignment=Qt.AlignmentFlag.AlignCenter)

                    skill_row.addWidget(slot_frame)

                skill_row.addStretch(1)

            # 구분선
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet("QFrame { background-color: #F1F3F5; border: 0px; }")
            root.addWidget(line)

            # 연계 유형, 시작 키 표시 컨테이너
            info_container = QHBoxLayout()
            info_container.setContentsMargins(0, 5, 0, 5)
            root.addLayout(info_container)

            is_auto: bool = data.use_type == LinkUseType.AUTO
            badge_text: str = "자동 모드" if is_auto else "수동 모드"

            # 색상 테마 설정
            if is_auto:
                # 초록색 테마 (Auto)
                badge_style = """
                    QLabel {
                        background-color: #E8F5E9; 
                        color: #2E7D32; 
                        border: 1px solid #C8E6C9;
                        border-radius: 8px;
                    }
                """
            else:
                # 회색 테마 (Manual)
                badge_style = """
                    QLabel {
                        background-color: #F1F3F5; 
                        color: #495057; 
                        border: 1px solid #DEE2E6;
                        border-radius: 8px;
                    }
                """

            use_type_display = QLabel(badge_text)
            use_type_display.setFont(CustomFont(10))
            use_type_display.setStyleSheet(badge_style)
            use_type_display.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
            )
            info_container.addWidget(use_type_display)

            info_container.addStretch(1)

            # 시작 키 표시 컨테이너
            key_container = QWidget()
            key_container.setStyleSheet("background: transparent; border: 0px;")

            key_layout = QHBoxLayout(key_container)
            key_layout.setContentsMargins(0, 0, 0, 0)
            key_layout.setSpacing(6)

            start_key_title = QLabel("시작 키:")
            start_key_title.setStyleSheet(
                "QLabel { color: #868E96; font-size: 12px; background: transparent; border: 0px; }"
            )

            start_key_value = QLabel()
            if data.key_type == LinkKeyType.ON and data.key is not None:
                key_val: str = KeyRegistry.MAP[data.key].display
                start_key_value.setText(key_val)
                start_key_value.setStyleSheet(
                    "QLabel { background-color: #343A40; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 12px; }"
                )
            else:
                start_key_value.setText("미설정")
                start_key_value.setStyleSheet(
                    "QLabel { color: #ADB5BD; font-size: 12px; background: transparent; border: 0px; }"
                )

            key_layout.addWidget(start_key_title)
            key_layout.addWidget(start_key_value)
            info_container.addWidget(key_container)

            # 수정, 삭제 버튼 컨테이너
            btn_container = QHBoxLayout()
            btn_container.setSpacing(8)
            root.addLayout(btn_container)

            # 수정 버튼
            edit_btn = QPushButton("수정하기")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda _, i=idx: edit_func(i))
            edit_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #1f618d;
                }
            """
            )
            btn_container.addWidget(edit_btn)

            # 삭제 버튼
            remove_btn = QPushButton("삭제")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(lambda _, i=idx: remove_func(i))
            remove_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #e74c3c;
                    border: 1px solid #e74c3c;
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e74c3c;
                    color: white;
                }
            """
            )
            btn_container.addWidget(remove_btn)


class LinkSkillEditor(QFrame):
    """사이드바 타입 4 - 연계설정 편집"""

    # 편집 종료(취소/저장) 후 목록으로 돌아가기 위한 시그널
    closed = pyqtSignal()
    saved = pyqtSignal()
    contentResized = pyqtSignal()

    # todo: 링크스킬 데이터를 클래스로 관리하도록 수정
    def __init__(
        self,
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ) -> None:
        super().__init__()

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
        self.add_skill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.add_skill_btn)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.setFont(CustomFont(12))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("저장")
        self.save_btn.clicked.connect(self.save)
        self.save_btn.setFont(CustomFont(12))
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.save_btn)

        self.data: LinkSkill = LinkSkill()
        # 편집 중인 연계스킬의 인덱스 (-1이면 새로 만들기)
        self._editing_index: int = -1

    def _get_preset(self) -> "MacroPreset":
        return app_state.macro.presets[app_state.macro.current_preset_index]

    def _sync_preset_to_shared_data(self, preset: "MacroPreset") -> None:
        apply_preset_to_app_state(
            preset,
            preset_index=app_state.macro.current_preset_index,
            all_presets=app_state.macro.presets,
        )

    def load(self, data: LinkSkill, index: int) -> None:
        """연계스킬 데이터 로드"""

        self.data = data
        self._editing_index = index

        self._after_data_changed(update_skills=True)

    def _after_data_changed(self, update_skills: bool) -> None:
        """self.data 변경 이후 UI 갱신을 한 곳으로 모음."""

        self._refresh_ui()
        if update_skills:
            self._refresh_skill_items()

    def _refresh_ui(self) -> None:
        """현재 self.data 상태에 맞춰 UI(버튼 색/텍스트)를 동기화."""

        # 연계 유형 버튼
        use_type: LinkUseType = self.data.use_type
        self.type_setting.set_buttons_enabled(
            use_type == LinkUseType.AUTO, use_type == LinkUseType.MANUAL
        )

        # 단축키 버튼
        key_type: LinkKeyType = self.data.key_type
        if (
            key_type == LinkKeyType.ON
            and self.data.key is not None
            and self.data.key in KeyRegistry.MAP
        ):
            key_text: str = KeyRegistry.MAP[self.data.key].display
        else:
            key_text = ""

        self.key_setting.set_right_button_text(key_text)
        self.key_setting.set_buttons_enabled(
            key_type == LinkKeyType.OFF, key_type == LinkKeyType.ON
        )

    def _get_all_skill_ids(self) -> list[str]:
        """프리셋 서버의 전체 스킬 ID 목록을 반환"""

        preset: MacroPreset = self._get_preset()
        return app_state.macro.current_server.skill_registry.get_all_skill_ids()

    def _refresh_skill_items(self) -> None:
        """self.data['skills']로 스킬 구성 UI를 다시 그림"""

        # 기존 위젯 제거
        for widget in self._skill_item_widgets:
            self._skills_layout.removeWidget(widget)
            widget.deleteLater()

        # 캐시 리스트 초기화
        self._skill_item_widgets = []

        for idx, name in enumerate(self.data.skills):
            skill_widget = self.SkillItem(
                index=idx,
                name=name,
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

        def apply(skill_id: str) -> None:
            self.change_skill(i, skill_id)

        self.popup_manager.make_link_skill_select_popup(
            anchor=anchor_btn,
            skill_ids=self._get_all_skill_ids(),
            on_selected=apply,
        )

    def set_auto(self) -> None:
        """연계스킬을 자동 사용으로 설정"""

        self.popup_manager.close_popup()

        # 이미 자동이면 무시
        if self.data.use_type == LinkUseType.AUTO:
            return

        preset: MacroPreset = self._get_preset()

        # 모든 스킬이 장착되어 있는지 확인
        if not all(i in preset.skills.equipped_skills for i in self.data.skills):
            self.popup_manager.make_notice_popup("skillNotSelected")
            return

        # 지금 수정 중인 연계스킬의 인덱스
        num: int = self._editing_index

        # 자동 연계스킬 스킬 중복 검사
        auto_skills: list[str] = []
        for i, link_skill in enumerate(preset.link_settings):
            # 자기 자신은 무시
            if i == num:
                continue

            # 자동 연계스킬인 경우
            if link_skill.use_type == LinkUseType.AUTO:
                for j in link_skill.skills:
                    auto_skills.append(j)

        # 중복되는 스킬이 있으면 알림 팝업 생성 후 종료
        for i in self.data.skills:
            if i in auto_skills:
                self.popup_manager.make_notice_popup("autoAlreadyExist")
                return

        # 중복되는 스킬이 없으면 자동으로 변경
        self.data.set_auto()
        self._after_data_changed(update_skills=False)

    def set_manual(self) -> None:
        """연계스킬을 수동 사용으로 설정"""

        self.popup_manager.close_popup()

        # 이미 수동이면 무시
        if self.data.use_type == LinkUseType.MANUAL:
            return

        # 수동으로 변경
        self.data.set_manual()
        self._after_data_changed(update_skills=False)

    def clear_key(self) -> None:
        """단축키 설정 해제"""

        self.popup_manager.close_popup()

        self.data.clear_key()
        self._after_data_changed(update_skills=False)

    def on_key_btn_clicked(self) -> None:
        """연계스킬 단축키 설정 버튼 클릭 시"""

        def apply(key: KeySpec) -> None:
            """적용 함수"""

            self.data.set_key(key.key_id)
            self._after_data_changed(update_skills=False)

        self.popup_manager.close_popup()
        self.popup_manager.make_link_skill_key_popup(
            self.key_setting.right_button,
            apply,
        )

    def change_skill(self, i: int, skill_id: str) -> None:
        """i번째 스킬을 skill_id로 변경"""

        self.popup_manager.close_popup()

        # 동일 스킬 선택 시 무시
        if self.data.skills[i] == skill_id:
            return

        # 스킬명 설정 초기화
        self.data.skills[i] = skill_id

        # 수동 사용으로 변경
        self.data.set_manual()

        if self.is_skill_exceeded(skill_id):
            self.popup_manager.make_notice_popup("exceedMaxLinkSkill")

        self._after_data_changed(update_skills=True)

    def remove_skill(self, i: int) -> None:
        """i번째 스킬 제거"""

        self.popup_manager.close_popup()

        # 스킬 제거
        self.data.skills.pop(i)

        # 수동 사용으로 변경
        self.data.set_manual()

        self._after_data_changed(update_skills=True)

    def add_skill(self) -> None:
        """스킬 추가"""

        self.popup_manager.close_popup()

        all_skills: list[str] = self._get_all_skill_ids()
        for i in all_skills:
            # 아직 추가되지 않은 스킬이면 추가
            if i not in self.data.skills:
                skill_id: str = i
                break
        else:
            # 모든 스킬이 추가되어 있으면 첫 번째 스킬 추가
            skill_id = all_skills[0]

        self.data.skills.append(skill_id)

        # 수동 사용으로 변경
        self.data.set_manual()

        # 최대 사용 횟수 초과 시 알림 팝업 생성
        if self.is_skill_exceeded(skill_id):
            self.popup_manager.make_notice_popup("exceedMaxLinkSkill")

        self._after_data_changed(update_skills=True)

    def cancel(self) -> None:
        """편집 취소"""

        self.popup_manager.close_popup()
        self.closed.emit()

    def save(self) -> None:
        """편집 저장"""

        self.popup_manager.close_popup()

        # 스킬을 하나도 추가하지 않은 경우 취소
        if not self.data.skills:
            self.cancel()
            return

        preset: MacroPreset = self._get_preset()

        # 수정하던 연계스킬의 인덱스
        index: int = self._editing_index

        # 새로 만드는 경우
        if index == -1:
            preset.link_settings.append(self.data)
            self._editing_index = len(preset.link_settings) - 1

        # 기존 연계스킬 수정하는 경우
        else:
            preset.link_settings[index] = self.data
            self._editing_index = index

        self._sync_preset_to_shared_data(preset)
        self._on_data_changed()

        self.saved.emit()
        self.closed.emit()

    def is_skill_exceeded(self, skill_id: str) -> bool:
        """연계스킬에서 특정 스킬의 최대 사용 횟수를 초과하는지 확인"""

        count: int = self.data.skills.count(skill_id)

        # 최대 사용 횟수 초과 여부 반환
        return count > 1

    class SkillItem(QFrame):
        changeRequested = pyqtSignal(int)
        removeRequested = pyqtSignal(int)

        def __init__(
            self,
            index: int,
            name: str,
        ) -> None:
            super().__init__()

            self.index: int = int(index)

            skill_id: str = name

            self.skill = QPushButton()
            self.skill.clicked.connect(self._emit_change)
            self.skill.setIcon(QIcon(resource_registry.get_skill_pixmap(skill_id)))
            # skill.setIconSize(QSize(50, 50))
            self.skill.setIconSize(QSize(36, 36))
            self.skill.setFixedSize(44, 44)
            self.skill.setToolTip(
                "연계스킬을 구성하는 스킬의 목록과 사용 횟수를 설정할 수 있습니다.\n"
                "하나의 스킬이 너무 많이 사용되면 연계가 정상적으로 작동하지 않을 수 있습니다."
            )
            self.skill.setCursor(Qt.CursorShape.PointingHandCursor)

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
            self.remove.setCursor(Qt.CursorShape.PointingHandCursor)

            layout = QHBoxLayout()
            layout.addWidget(self.skill)
            # layout.addStretch(1)
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
            self.left_button.setCursor(Qt.CursorShape.PointingHandCursor)

            self.right_button = QPushButton(btn1_text)
            self.right_button.clicked.connect(lambda: func1())
            self.right_button.setStyleSheet(
                f"color: {self._color_dict[is_btn1_enabled]};"
            )
            self.right_button.setFont(CustomFont(12))
            self.right_button.setCursor(Qt.CursorShape.PointingHandCursor)

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

            self.setCursor(Qt.CursorShape.PointingHandCursor)

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
