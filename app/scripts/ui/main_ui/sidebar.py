from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Literal

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
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
from app.scripts.custom_skill_models import CustomScrollDefinition, CustomSkillImport
from app.scripts.data_manager import (
    read_custom_skills_data,
    remove_custom_scroll,
    save_custom_skills,
)
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
from app.scripts.registry.skill_registry import CUSTOM_SKILL_PREFIX, ScrollDef, SkillDef
from app.scripts.ui.popup import (
    CustomSkillAddDialog,
    NoticeKind,
    PopupKind,
    PopupManager,
)

if TYPE_CHECKING:
    from typing import Literal

    from app.scripts.registry.server_registry import ServerSpec
    from app.scripts.registry.skill_registry import ScrollDef
    from app.scripts.ui.main_window import MainWindow
    from app.scripts.ui.popup import HoverCardData


def get_current_scroll_skill_ids(preset: MacroPreset) -> list[str]:
    """현재 장착 무공비급 기준 제공 스킬 ID 목록 반환"""

    return preset.skills.get_available_skill_ids(app_state.macro.current_server)


# 스킬 사용설정 옵션 메타데이터 정의
@dataclass(frozen=True)
class SkillSettingOptionDef:
    key: Literal["usage", "sole", "priority", "solo_swap"]
    title: str
    tooltip: str


# 스킬 카드 위젯 참조 묶음
@dataclass
class SkillSettingCardWidgets:
    skill_id: str
    frame: QFrame
    usage_btn: QPushButton
    sole_btn: QPushButton
    priority_btn: QPushButton
    solo_swap_btn: QPushButton


# 스킬 사용설정 옵션 정의
SKILL_SETTING_OPTION_DEFS: tuple[SkillSettingOptionDef, ...] = (
    SkillSettingOptionDef(
        key="usage",
        title="사용 여부",
        tooltip=(
            "매크로가 작동 중일 때 자동으로 스킬을 사용할지 결정합니다.\n"
            "이동기같이 자신이 직접 사용해야 하는 스킬만 사용을 해제하시는 것을 추천드립니다.\n"
            "연계스킬에는 적용되지 않습니다."
        ),
    ),
    SkillSettingOptionDef(
        key="sole",
        title="단독 사용",
        tooltip=(
            "연계스킬을 대기할 때 다른 스킬들이 준비되는 것을 기다리지 않고 우선적으로 사용할 지 결정합니다.\n"
            "연계스킬 내에서 다른 스킬보다 너무 빠르게 준비되는 스킬은 사용을 해제하시는 것을 추천드립니다.\n"
            "사용여부가 활성화되지 않았다면 단독으로 사용되지 않습니다."
        ),
    ),
    SkillSettingOptionDef(
        key="priority",
        title="우선 순위",
        tooltip=(
            "매크로가 작동 중일 때 여러 스킬이 준비되었더라도 우선순위가 더 높은(숫자가 낮은) 스킬을 먼저 사용합니다.\n"
            "우선순위를 설정하지 않은 스킬들은 준비된 시간 순서대로 사용합니다.\n"
            "버프스킬의 우선순위를 높이는 것을 추천합니다.\n"
            "연계스킬은 우선순위가 적용되지 않습니다."
        ),
    ),
    SkillSettingOptionDef(
        key="solo_swap",
        title="단독 스왑",
        tooltip=(
            "스킬을 사용하기 위해 바로 스왑할지 결정합니다.\n"
            "사용하려는 스킬이 다른 줄에 있고 이 옵션이 활성화되어 있다면 즉시 스왑합니다.\n"
            "연계스킬에는 적용되지 않습니다."
        ),
    ),
)


# 스킬 사용설정 옵션 조회 맵 구성
SKILL_SETTING_OPTION_MAP: dict[
    Literal["usage", "sole", "priority", "solo_swap"], SkillSettingOptionDef
] = {option.key: option for option in SKILL_SETTING_OPTION_DEFS}


class Sidebar(QFrame):
    """좌측 사이드바 클래스"""

    dataChanged = Signal()
    scrollDeleted = Signal()

    def __init__(
        self,
        master: MainWindow,
        preset: "MacroPreset",
        preset_index: int,
    ) -> None:
        super().__init__(master)

        self.setObjectName("sidebar")

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

        # 스킬 사용설정 무공비급 변경 시 사이드바 높이 동기화
        self.skill_settings.contentResized.connect(self.adjust_stack_height)

        # 커스텀 무공비급 삭제 시 메인 UI 갱신 시그널 전파
        self.skill_settings.scrollDeleted.connect(self.scrollDeleted.emit)

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

        # 무공비급바
        self.scroll_area: QScrollArea = QScrollArea()
        self.scroll_area.setObjectName("sidebarScrollArea")
        self.scroll_area.setWidget(self.page_navigator)

        # 위젯이 무공비급 영역에 맞춰 크기 조절되도록
        self.scroll_area.setWidgetResizable(True)

        # 무공비급바 무공비급 설정
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
            title=config.specs.COOLTIME_REDUCTION.label,
            tooltip=(
                f"캐릭터의 {config.specs.COOLTIME_REDUCTION.label} 스탯입니다.\n"
                f"입력 가능한 범위는 {config.specs.COOLTIME_REDUCTION.min}~{config.specs.COOLTIME_REDUCTION.max}입니다."
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

        self.swap_key_setting = self.SettingItem(
            title="스왑키 설정",
            tooltip=(
                "2줄 스킬을 사용하기 전에 입력하는 스킬 줄 전환 키입니다.\n"
                "스킬키, 시작키, 연계키와 겹치지 않는 키로 설정해야 합니다."
            ),
            btn0_text=f"기본: {config.specs.DEFAULT_SWAP_KEY.display}",
            btn0_enabled=True,
            btn1_text="",
            btn1_enabled=False,
            func0=self.on_default_swap_key_clicked,
            func1=self.on_user_swap_key_clicked,
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
        layout.addWidget(self.swap_key_setting)
        layout.addWidget(self.click_setting)

        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

        self.update_from_preset(app_state.macro.current_preset)

    def update_from_preset(self, preset: MacroPreset) -> None:
        """프리셋으로부터 위젯 상태를 업데이트"""

        # 서버 - 직업
        self.server_job_setting.set_left_button_text(preset.settings.server_id)

        # 딜레이
        custom_delay: int = preset.settings.custom_delay
        use_custom_delay: bool = preset.settings.use_custom_delay
        self.delay_setting.set_right_button_text(str(custom_delay))
        self.delay_setting.set_buttons_enabled(not use_custom_delay, use_custom_delay)

        # 쿨타임 감소
        custom_cooltime_reduction: float = preset.settings.custom_cooltime_reduction
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
        self.start_key_setting.set_right_button_text(
            KeyRegistry.get(custom_start_key).display
        )
        self.start_key_setting.set_buttons_enabled(
            not use_custom_start_key, use_custom_start_key
        )

        # 스왑키 설정
        custom_swap_key: str = preset.settings.custom_swap_key
        use_custom_swap_key: bool = preset.settings.use_custom_swap_key
        self.swap_key_setting.set_right_button_text(
            KeyRegistry.get(custom_swap_key).display
        )
        self.swap_key_setting.set_buttons_enabled(
            not use_custom_swap_key, use_custom_swap_key
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
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        # close_popup() 을 먼저 호출하면 코드가 실행되지 않음
        if self.popup_manager.is_popup_active(PopupKind.SERVER):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        self.popup_manager.make_server_popup(self.server_job_setting.left_button, apply)

    def on_default_delay_clicked(self) -> None:
        """기본 딜레이 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        # 이미 기본 딜레이라면 무시
        if not app_state.macro.current_preset.settings.use_custom_delay:
            return

        # 기본 딜레이로 변경 (입력 값은 유지)
        app_state.macro.current_preset.settings.use_custom_delay = False
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
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        # close_popup() 을 먼저 호출하면 코드가 실행되지 않음
        if self.popup_manager.is_popup_active(PopupKind.DELAY):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        # 이미 유저 딜레이라면 딜레이 입력 팝업 열기
        if app_state.macro.current_preset.settings.use_custom_delay:
            self.popup_manager.make_delay_popup(self.delay_setting.right_button, apply)
            return

        # 유저 딜레이로 변경 (입력 값 유지)
        app_state.macro.current_preset.settings.use_custom_delay = True
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_default_cooltime_clicked(self) -> None:
        """기본 쿨타임 감소 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        # 이미 기본 쿨타임 감소라면 무시
        if not app_state.macro.current_preset.settings.use_custom_cooltime_reduction:
            return

        # 기본 쿨타임 감소로 변경 (입력 값은 유지)
        app_state.macro.current_preset.settings.use_custom_cooltime_reduction = False
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_user_cooltime_clicked(self) -> None:
        """유저 쿨타임 감소 클릭시 실행"""

        def apply(cooltime_value: float) -> None:
            """적용 함수"""

            if (
                cooltime_value
                == app_state.macro.current_preset.settings.custom_cooltime_reduction
            ):
                return

            app_state.macro.current_preset.settings.custom_cooltime_reduction = (
                cooltime_value
            )
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        # close_popup() 을 먼저 호출하면 코드가 실행되지 않음
        if self.popup_manager.is_popup_active(PopupKind.COOLTIME):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        # 이미 유저 쿨타임 감소라면 쿨타임 감소 입력 팝업 열기
        if app_state.macro.current_preset.settings.use_custom_cooltime_reduction:
            self.popup_manager.make_cooltime_popup(
                self.cooltime_setting.right_button, apply
            )
            return

        # 유저 쿨타임 감소로 변경 (입력 값 유지)
        app_state.macro.current_preset.settings.use_custom_cooltime_reduction = True
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_default_start_key_clicked(self) -> None:
        """기본 시작키 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
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
            self.popup_manager.show_notice(NoticeKind.START_KEY_CHANGE_ERROR)
            return

        # 기본 시작키로 변경 (입력 값은 유지)
        app_state.macro.current_preset.settings.use_custom_start_key = False

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
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        # close_popup() 을 먼저 호출하면 코드가 실행되지 않음
        if self.popup_manager.is_popup_active(PopupKind.START_KEY):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
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
            KeyRegistry.get(current_input_key_id)
        ):
            self.popup_manager.show_notice(NoticeKind.START_KEY_CHANGE_ERROR)
            return

        # 유저 시작키로 변경 (입력 값 유지)
        app_state.macro.current_preset.settings.use_custom_start_key = True
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_mouse_type0_clicked(self) -> None:
        """평타 사용 안함 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        # 이미 False 라면 무시
        if not app_state.macro.current_preset.settings.use_default_attack:
            return

        app_state.macro.current_preset.settings.use_default_attack = False
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_default_swap_key_clicked(self) -> None:
        """기본 스왑키 클릭시 실행"""

        self.popup_manager.close_popup()

        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        if not app_state.macro.current_preset.settings.use_custom_swap_key:
            return

        default_key: KeySpec = config.specs.DEFAULT_SWAP_KEY
        current_input_key_id: str = (
            app_state.macro.current_preset.settings.custom_swap_key
        )

        if current_input_key_id != default_key.key_id and app_state.is_key_using(
            default_key
        ):
            self.popup_manager.show_notice(NoticeKind.SWAP_KEY_CHANGE_ERROR)
            return

        app_state.macro.current_preset.settings.use_custom_swap_key = False
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_user_swap_key_clicked(self) -> None:
        """유저 스왑키 클릭시 실행"""

        def apply(key: KeySpec) -> None:
            """적용 함수"""

            if key.key_id == app_state.macro.current_preset.settings.custom_swap_key:
                return

            app_state.macro.current_preset.settings.custom_swap_key = key.key_id
            self.update_from_preset(app_state.macro.current_preset)
            self._on_data_changed()

        if self.popup_manager.is_popup_active(PopupKind.SKILL_KEY):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        if app_state.macro.current_preset.settings.use_custom_swap_key:
            self.popup_manager.make_skill_key_popup(
                self.swap_key_setting.right_button,
                app_state.macro.current_preset.settings.custom_swap_key,
                apply,
            )
            return

        current_input_key_id: str = (
            app_state.macro.current_preset.settings.custom_swap_key
        )
        if (
            current_input_key_id != config.specs.DEFAULT_SWAP_KEY.key_id
            and app_state.is_key_using(KeyRegistry.get(current_input_key_id))
        ):
            self.popup_manager.show_notice(NoticeKind.SWAP_KEY_CHANGE_ERROR)
            return

        app_state.macro.current_preset.settings.use_custom_swap_key = True
        self.update_from_preset(app_state.macro.current_preset)
        self._on_data_changed()

    def on_mouse_type1_clicked(self) -> None:
        """평타 사용 클릭시 실행"""

        self.popup_manager.close_popup()

        # 매크로 실행 중일 때는 무시
        if app_state.macro.is_running:
            self.popup_manager.show_notice(NoticeKind.MACRO_IS_RUNNING)
            return

        # 이미 타입1 이라면 무시
        if app_state.macro.current_preset.settings.use_default_attack:
            return

        app_state.macro.current_preset.settings.use_default_attack = True
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
            self.title.setObjectName("generalSettingTitle")
            self.title.setFont(CustomFont(16))

            self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.title.setToolTip(tooltip)

            self.left_button = QPushButton(btn0_text)
            self.left_button.setObjectName("generalSettingBtn")
            self.left_button.setFont(CustomFont(12))
            self.left_button.setProperty("active", btn0_enabled)
            self.left_button.setFixedWidth(120)
            self.left_button.setEnabled(func0 is not None)

            self.right_button = QPushButton(btn1_text)
            self.right_button.setObjectName("generalSettingBtn")
            self.right_button.setFont(CustomFont(12))
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

    contentResized = Signal()
    scrollDeleted = Signal()

    def __init__(
        self,
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ) -> None:
        super().__init__()

        self.popup_manager: PopupManager = popup_manager
        self._on_data_changed: Callable[[], None] = on_data_changed

        self.title = Title("스킬 사용설정")

        self._scroll_ids: list[str] = []
        self._selected_scroll_id: str = ""
        self._skill_ids: list[str] = []
        self._skill_cards: list[SkillSettingCardWidgets] = []

        # 선택된 무공비급 요약 카드 구성
        self._selected_scroll_icon: QLabel = QLabel()
        self._selected_scroll_icon.setFixedSize(40, 40)
        self._selected_scroll_icon.setScaledContents(True)
        self._selected_scroll_icon.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self._selected_scroll_name: QLabel = QLabel("")
        self._selected_scroll_name.setFont(CustomFont(14))
        self._selected_scroll_name.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._selected_scroll_name.setWordWrap(True)
        self._selected_scroll_name.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        selected_scroll_layout: QHBoxLayout = QHBoxLayout()
        selected_scroll_layout.addWidget(self._selected_scroll_icon)
        selected_scroll_layout.addWidget(self._selected_scroll_name)
        selected_scroll_layout.setStretch(1, 1)
        selected_scroll_layout.setContentsMargins(12, 10, 12, 10)
        selected_scroll_layout.setSpacing(10)

        self._selected_scroll_button: QPushButton = QPushButton()
        self._selected_scroll_button.setObjectName("selectedScrollButton")
        self._selected_scroll_button.setLayout(selected_scroll_layout)
        self._selected_scroll_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._selected_scroll_button.setMinimumHeight(62)
        self._selected_scroll_button.clicked.connect(self.on_scroll_select_clicked)

        # 선택 무공비급 카드 전역 호버 카드 연결
        self.popup_manager.bind_hover_card(
            self._selected_scroll_button,
            self._build_selected_scroll_hover_card,
        )

        # 커스텀 무공비급 수정/삭제 버튼 (커스텀 무공비급 선택 시에만 표시)
        self._edit_scroll_btn: QPushButton = QPushButton("수정")
        self._edit_scroll_btn.setObjectName("editScrollBtn")
        self._edit_scroll_btn.setFont(CustomFont(10))
        self._edit_scroll_btn.setFixedHeight(26)
        self._edit_scroll_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_scroll_btn.clicked.connect(self._on_edit_custom_scroll)

        self._delete_scroll_btn: QPushButton = QPushButton("삭제")
        self._delete_scroll_btn.setObjectName("deleteScrollBtn")
        self._delete_scroll_btn.setFont(CustomFont(10))
        self._delete_scroll_btn.setFixedHeight(26)
        self._delete_scroll_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_scroll_btn.clicked.connect(self._on_delete_custom_scroll)

        custom_actions_row: QHBoxLayout = QHBoxLayout()
        custom_actions_row.setContentsMargins(0, 0, 0, 0)
        custom_actions_row.setSpacing(6)
        custom_actions_row.addStretch()
        custom_actions_row.addWidget(self._edit_scroll_btn)
        custom_actions_row.addWidget(self._delete_scroll_btn)

        self._custom_actions_frame: QFrame = QFrame()
        self._custom_actions_frame.setLayout(custom_actions_row)
        self._custom_actions_frame.hide()

        # 스킬 카드 목록 레이아웃 구성
        self._cards_container: QWidget = QWidget()
        self._cards_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._cards_layout: QVBoxLayout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)

        layout: QVBoxLayout = QVBoxLayout()
        layout.addWidget(self.title, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._selected_scroll_button)
        layout.addWidget(self._cards_container)
        layout.addWidget(self._custom_actions_frame)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.update_from_preset(self._get_preset())

    def _get_preset(self) -> "MacroPreset":
        """현재 프리셋 반환"""

        # 현재 선택 프리셋 직접 조회
        preset: MacroPreset = app_state.macro.presets[
            app_state.macro.current_preset_index
        ]
        return preset

    def _sync_scroll_ids(self, scroll_defs: list["ScrollDef"]) -> None:
        """현재 서버 무공비급 ID 목록 동기화"""

        # 무공비급 ID 목록 비교용 캐시 구성
        scroll_ids: list[str] = [scroll_def.id for scroll_def in scroll_defs]
        if scroll_ids == self._scroll_ids:
            return

        self._scroll_ids = scroll_ids

    def _sync_selected_scroll(self, scroll_defs: list["ScrollDef"]) -> None:
        """현재 선택 무공비급 상태 보정"""

        # 무공비급이 없는 서버라면 선택 상태 초기화
        if not scroll_defs:
            self._selected_scroll_id = ""
            return

        # 기존 선택이 유효하지 않으면 첫 번째 무공비급 선택
        available_scroll_ids: set[str] = {scroll_def.id for scroll_def in scroll_defs}
        if self._selected_scroll_id not in available_scroll_ids:
            self._selected_scroll_id = scroll_defs[0].id

    def _update_selected_scroll_card(self, scroll_def: "ScrollDef") -> None:
        """선택된 무공비급 요약 카드 갱신"""

        # 선택된 무공비급 아이콘과 이름 동기화
        scroll_pixmap: QPixmap = resource_registry.get_scroll_pixmap(scroll_def.id)
        self._selected_scroll_icon.setPixmap(scroll_pixmap)
        self._selected_scroll_name.setText(scroll_def.name)
        self._selected_scroll_name.setToolTip(scroll_def.name)

        # 커스텀 무공비급이면 수정/삭제 버튼 표시
        is_custom: bool = scroll_def.id.startswith(f"{CUSTOM_SKILL_PREFIX}:")
        self._custom_actions_frame.setVisible(is_custom)

    def _clear_rows(self) -> None:
        """기존 행들 제거"""

        # 기존 스킬 카드 위젯 정리
        card: SkillSettingCardWidgets
        for card in self._skill_cards:
            self._cards_layout.removeWidget(card.frame)
            card.frame.deleteLater()

        self._skill_ids = []
        self._skill_cards = []

    def _build_option_card(
        self,
        title: str,
        tooltip: str,
        button: QPushButton,
    ) -> QFrame:
        """스킬 설정 옵션 카드 생성"""

        # 옵션 제목 라벨 구성
        option_title: QLabel = QLabel(title)
        option_title.setObjectName("optionTitle")
        option_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        option_title.setFont(CustomFont(11))
        option_title.setWordWrap(True)
        option_title.setToolTip(tooltip)

        # 옵션 버튼 정렬 행 구성
        button_row: QHBoxLayout = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(0)
        button_row.addStretch(1)
        button_row.addWidget(button)
        button_row.addStretch(1)

        # 옵션 카드 레이아웃 구성
        option_layout: QVBoxLayout = QVBoxLayout()
        option_layout.setContentsMargins(8, 8, 8, 8)
        option_layout.setSpacing(6)
        option_layout.addWidget(option_title)
        option_layout.addLayout(button_row)

        # 옵션 카드 프레임 구성
        option_frame: QFrame = QFrame()
        option_frame.setObjectName("skillOptionCard")
        option_frame.setToolTip(tooltip)
        option_frame.setLayout(option_layout)
        return option_frame

    def _ensure_rows(self, skill_ids: list[str]) -> None:
        """스킬 행 생성"""

        if skill_ids == self._skill_ids:
            return

        self._clear_rows()
        self._skill_ids = skill_ids.copy()

        for idx, skill_id in enumerate(self._skill_ids):
            # 스킬 헤더 영역 구성
            pixmap: QPixmap = resource_registry.get_skill_pixmap(skill_id=skill_id)
            skill_name: str = app_state.macro.current_server.skill_registry.get(
                skill_id
            ).name
            skill_image: SkillImage = SkillImage(parent=self, pixmap=pixmap, size=34)
            skill_name_label: QLabel = QLabel(skill_name)
            skill_name_label.setFont(CustomFont(12))
            skill_name_label.setToolTip(skill_name)
            skill_name_label.setWordWrap(True)
            skill_name_label.setMinimumHeight(34)
            skill_name_label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

            skill_info_layout: QHBoxLayout = QHBoxLayout()
            skill_info_layout.addWidget(skill_image)
            skill_info_layout.addWidget(skill_name_label)
            skill_info_layout.setContentsMargins(0, 0, 0, 0)
            skill_info_layout.setSpacing(8)

            skill_info_frame: QFrame = QFrame()
            skill_info_frame.setLayout(skill_info_layout)

            # 스킬 정보 영역 전역 호버 카드 연결
            self.popup_manager.bind_hover_card(
                skill_info_frame,
                lambda sid=skill_id: self._build_skill_hover_card(sid),
            )
            self.popup_manager.bind_hover_card(
                skill_image,
                lambda sid=skill_id: self._build_skill_hover_card(sid),
            )
            self.popup_manager.bind_hover_card(
                skill_name_label,
                lambda sid=skill_id: self._build_skill_hover_card(sid),
            )

            # 스킬 사용 여부 버튼 구성
            usage_btn: QPushButton = QPushButton()
            usage_btn.setObjectName("checkBtn")
            usage_btn.setIconSize(QSize(40, 40))
            usage_btn.setFixedSize(30, 30)
            usage_btn.setToolTip(SKILL_SETTING_OPTION_MAP["usage"].tooltip)
            usage_btn.clicked.connect(
                partial(lambda x: self.change_skill_usage(x), idx)
            )
            usage_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # 스킬 단독 사용 여부 버튼 구성
            sole_btn: QPushButton = QPushButton()
            sole_btn.setObjectName("checkBtn")
            sole_btn.setIconSize(QSize(40, 40))
            sole_btn.setFixedSize(30, 30)
            sole_btn.setToolTip(SKILL_SETTING_OPTION_MAP["sole"].tooltip)
            sole_btn.clicked.connect(partial(lambda x: self.change_use_sole(x), idx))
            sole_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # 스킬 우선순위 버튼 구성
            priority_btn: QPushButton = QPushButton("-")
            priority_btn.setFont(CustomFont(12))
            priority_btn.setObjectName("priorityBtn")
            priority_btn.setFixedSize(52, 30)
            priority_btn.setToolTip(SKILL_SETTING_OPTION_MAP["priority"].tooltip)
            priority_btn.clicked.connect(
                partial(lambda x: self.change_priority(x), idx)
            )
            priority_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # 스킬 단독 스왑 여부 버튼 구성
            solo_swap_btn: QPushButton = QPushButton()
            solo_swap_btn.setObjectName("checkBtn")
            solo_swap_btn.setIconSize(QSize(40, 40))
            solo_swap_btn.setFixedSize(30, 30)
            solo_swap_btn.setToolTip(SKILL_SETTING_OPTION_MAP["solo_swap"].tooltip)
            solo_swap_btn.clicked.connect(
                partial(lambda x: self.change_use_solo_swap(x), idx)
            )
            solo_swap_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # 스킬 설정 옵션 그리드 구성
            option_grid: QGridLayout = QGridLayout()
            option_grid.setContentsMargins(0, 0, 0, 0)
            option_grid.setHorizontalSpacing(8)
            option_grid.setVerticalSpacing(8)
            option_grid.setColumnStretch(0, 1)
            option_grid.setColumnStretch(1, 1)
            option_grid.addWidget(
                self._build_option_card(
                    SKILL_SETTING_OPTION_MAP["usage"].title,
                    SKILL_SETTING_OPTION_MAP["usage"].tooltip,
                    usage_btn,
                ),
                0,
                0,
            )
            option_grid.addWidget(
                self._build_option_card(
                    SKILL_SETTING_OPTION_MAP["sole"].title,
                    SKILL_SETTING_OPTION_MAP["sole"].tooltip,
                    sole_btn,
                ),
                0,
                1,
            )
            option_grid.addWidget(
                self._build_option_card(
                    SKILL_SETTING_OPTION_MAP["priority"].title,
                    SKILL_SETTING_OPTION_MAP["priority"].tooltip,
                    priority_btn,
                ),
                1,
                0,
            )
            option_grid.addWidget(
                self._build_option_card(
                    SKILL_SETTING_OPTION_MAP["solo_swap"].title,
                    SKILL_SETTING_OPTION_MAP["solo_swap"].tooltip,
                    solo_swap_btn,
                ),
                1,
                1,
            )

            # 스킬 카드 프레임 구성
            card_layout: QVBoxLayout = QVBoxLayout()
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(10)
            card_layout.addWidget(skill_info_frame)
            card_layout.addLayout(option_grid)

            card_frame: QFrame = QFrame()
            card_frame.setObjectName("skillSettingCard")
            card_frame.setLayout(card_layout)
            card_frame.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

            # 생성 카드 목록 등록
            self._cards_layout.addWidget(card_frame)
            self._skill_cards.append(
                SkillSettingCardWidgets(
                    skill_id=skill_id,
                    frame=card_frame,
                    usage_btn=usage_btn,
                    sole_btn=sole_btn,
                    priority_btn=priority_btn,
                    solo_swap_btn=solo_swap_btn,
                )
            )

    def update_from_preset(self, preset: "MacroPreset") -> None:
        """프리셋으로부터 위젯 상태를 업데이트"""

        # 서버 전체 무공비급 목록과 현재 선택 상태 동기화
        server_spec: "ServerSpec" = app_state.macro.current_server
        scroll_defs: list["ScrollDef"] = (
            server_spec.skill_registry.get_all_scroll_defs()
        )
        self._sync_scroll_ids(scroll_defs)
        self._sync_selected_scroll(scroll_defs)
        if not self._selected_scroll_id:
            self._clear_rows()
            self._selected_scroll_icon.clear()
            self._selected_scroll_name.setText("")
            return

        # 선택된 무공비급 카드와 대상 스킬 행 재구성
        scroll_def: "ScrollDef" = (
            app_state.macro.current_server.skill_registry.get_scroll(
                self._selected_scroll_id
            )
        )
        self._update_selected_scroll_card(scroll_def)

        skill_ids: list[str] = list(scroll_def.skills)
        self._ensure_rows(skill_ids)

        # 카드별 버튼 상태 동기화
        for card in self._skill_cards:
            setting: SkillUsageSetting = preset.usage_settings[card.skill_id]

            # 토글 버튼 아이콘 상태 반영
            usage_icon: QIcon = QIcon(
                QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{bool(setting.use_skill)}.png"
                    )
                )
            )
            sole_icon: QIcon = QIcon(
                QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{bool(setting.use_alone)}.png"
                    )
                )
            )
            solo_swap_icon: QIcon = QIcon(
                QPixmap(
                    convert_resource_path(
                        f"resources\\image\\check{bool(setting.use_solo_swap)}.png"
                    )
                )
            )

            card.usage_btn.setIcon(usage_icon)
            card.sole_btn.setIcon(sole_icon)
            card.solo_swap_btn.setIcon(solo_swap_icon)

            # 우선순위 숫자 텍스트 반영
            p: int = int(setting.priority)
            card.priority_btn.setText("-" if p == 0 else str(p))

    def _build_selected_scroll_hover_card(self) -> HoverCardData | None:
        """선택된 무공비급 카드 기준 호버 카드 구성"""

        # 선택 무공비급이 없는 초기 상태는 카드 미표시
        if not self._selected_scroll_id:
            return None

        # 현재 선택 무공비급과 저장 레벨 기준으로 카드 내용 구성
        scroll_def: "ScrollDef" = (
            app_state.macro.current_server.skill_registry.get_scroll(
                self._selected_scroll_id
            )
        )
        preset: MacroPreset = self._get_preset()
        level: int = preset.info.get_scroll_level(self._selected_scroll_id)
        return self.popup_manager.build_scroll_hover_card(scroll_def, level)

    def _build_skill_hover_card(self, skill_id: str) -> HoverCardData:
        """스킬 행 기준 호버 카드 구성"""

        # 현재 프리셋 저장 레벨 기준으로 동일한 스킬 상세 구성
        preset: MacroPreset = self._get_preset()
        level: int = preset.info.get_skill_level(
            app_state.macro.current_server,
            skill_id,
        )
        return self.popup_manager.build_skill_hover_card(skill_id, level)

    def on_scroll_select_clicked(self) -> None:
        """무공비급 선택 팝업 표시"""

        # 동일 팝업이 열려 있으면 토글 종료
        if self.popup_manager.is_popup_active(PopupKind.SCROLL_SELECT):
            self.popup_manager.close_popup()
            return

        # 현재 서버의 전체 무공비급 목록 준비
        server_spec: "ServerSpec" = app_state.macro.current_server
        scroll_defs: list["ScrollDef"] = (
            server_spec.skill_registry.get_all_scroll_defs()
        )

        # 팝업 선택 결과를 현재 선택 무공비급에 반영
        def apply(scroll_id: str) -> None:
            self._selected_scroll_id = scroll_id
            self.update_from_preset(self._get_preset())
            self.contentResized.emit()

        self.popup_manager.close_popup()
        self.popup_manager.make_scroll_select_popup(
            self._selected_scroll_button,
            scroll_defs,
            [],
            self._selected_scroll_id,
            apply,
            on_add_skill=self.on_scroll_select_clicked,
        )

    def _on_edit_custom_scroll(self) -> None:
        """커스텀 무공비급 수정 다이얼로그 열기"""

        server_spec = app_state.macro.current_server
        scroll_def: ScrollDef = server_spec.skill_registry.get_scroll(
            self._selected_scroll_id
        )

        existing_skills: dict = {}
        # 검증된 커스텀 스킬 원본에서 기존 서버 스킬 상세 조회
        existing_raw: dict[str, dict] = read_custom_skills_data()
        if server_spec.id in existing_raw:
            existing_skills = dict(
                CustomSkillImport.from_dict(existing_raw[server_spec.id]).skill_details
            )

        existing_scroll = CustomScrollDefinition(
            scroll_id=scroll_def.id,
            name=scroll_def.name,
            skills=scroll_def.skills,
        )

        dialog: CustomSkillAddDialog = CustomSkillAddDialog(
            server_id=server_spec.id,
            max_skill_level=server_spec.max_skill_level,
            existing_scroll=existing_scroll,
            existing_skills=existing_skills,
            parent=self._selected_scroll_button,
        )

        def _on_edited(skill_import: CustomSkillImport) -> None:
            # 현재 세션 레지스트리 반영
            for sid in skill_import.skills:
                detail = skill_import.skill_details[sid]
                server_spec.skill_registry.add_skill_def(
                    SkillDef.from_detail_dict(sid, server_spec.id, detail.to_dict())
                )

            for scroll in skill_import.scrolls:
                server_spec.skill_registry.add_scroll_def(
                    ScrollDef(
                        id=scroll.scroll_id,
                        server_id=server_spec.id,
                        name=scroll.name,
                        skills=scroll.skills,
                    )
                )

            # 수정 결과를 기존 저장 구조와 병합
            existing: dict[str, dict] = read_custom_skills_data()
            server_data: dict = existing.get(
                server_spec.id, {"skills": [], "scrolls": [], "skill_details": {}}
            )
            for sid in skill_import.skills:
                if sid not in server_data["skills"]:
                    server_data["skills"].append(sid)
                server_data["skill_details"][sid] = skill_import.skill_details[
                    sid
                ].to_dict()
            server_data["scrolls"] = [
                s
                for s in server_data["scrolls"]
                if s["scroll_id"] != self._selected_scroll_id
            ] + [s.to_dict() for s in skill_import.scrolls]

            # 검증된 병합 결과를 저장 파일에 반영
            merged_import: CustomSkillImport = CustomSkillImport.from_dict(server_data)
            save_custom_skills(server_spec.id, merged_import)

            self.update_from_preset(self._get_preset())

        dialog.skill_added.connect(_on_edited)
        dialog.exec()

    def _on_delete_custom_scroll(self) -> None:
        """커스텀 무공비급 삭제"""

        scroll_id: str = self._selected_scroll_id
        server_spec = app_state.macro.current_server
        scroll_def = server_spec.skill_registry.get_scroll(scroll_id)
        deleted_skill_ids: set[str] = set(scroll_def.skills)

        remove_custom_scroll(server_spec.id, scroll_id)

        # 모든 프리셋에서 삭제된 무공비급/스킬 관련 데이터 정리
        for preset in app_state.macro.presets:
            # 장착 무공비급 슬롯에서 제거
            for i, sid in enumerate(preset.skills.equipped_scrolls):
                if sid == scroll_id:
                    preset.skills.equipped_scrolls[i] = ""

            # 하단 배치 슬롯에서 제거
            for i, sid in enumerate(preset.skills.placed_skills):
                if sid in deleted_skill_ids:
                    preset.skills.placed_skills[i] = ""

            # 사용설정에서 제거
            for skill_id in deleted_skill_ids:
                preset.usage_settings.pop(skill_id, None)

            # 무공비급 레벨 저장값 제거
            preset.info.scroll_levels.pop(scroll_id, None)

            # 해당 스킬을 포함하는 연계스킬 제거
            preset.link_skills = [
                ls
                for ls in preset.link_skills
                if not deleted_skill_ids.intersection(ls.skills)
            ]

        self._selected_scroll_id = ""
        self.update_from_preset(self._get_preset())
        self._on_data_changed()
        self.scrollDeleted.emit()
        self.contentResized.emit()

    def change_skill_usage(self, skill_idx: int) -> None:
        """사용 여부 변경"""

        # 현재 선택된 스킬의 사용 여부 토글
        preset: MacroPreset = self._get_preset()
        skill_id: str = self._skill_ids[skill_idx]

        setting: SkillUsageSetting = preset.usage_settings[skill_id]

        setting.use_skill = not setting.use_skill
        self.update_from_preset(preset)
        self._on_data_changed()

    def change_use_sole(self, skill_idx: int) -> None:
        """단독 사용 변경"""

        # 현재 선택된 스킬의 단독 사용 여부 토글
        preset: MacroPreset = self._get_preset()
        skill_id: str = self._skill_ids[skill_idx]

        setting: SkillUsageSetting = preset.usage_settings[skill_id]

        setting.use_alone = not setting.use_alone
        self.update_from_preset(preset)
        self._on_data_changed()

    def change_use_solo_swap(self, skill_idx: int) -> None:
        """단독 스왑 변경"""

        # 현재 선택된 스킬의 단독 스왑 여부 토글
        preset: MacroPreset = self._get_preset()
        skill_id: str = self._skill_ids[skill_idx]

        setting: SkillUsageSetting = preset.usage_settings[skill_id]

        setting.use_solo_swap = not setting.use_solo_swap
        self.update_from_preset(preset)
        self._on_data_changed()

    def change_priority(self, skill_idx: int) -> None:
        """스킬 우선순위 변경"""

        # 현재 선택된 스킬과 배치 상태 조회
        preset: MacroPreset = self._get_preset()
        skill_id: str = self._skill_ids[skill_idx]
        placed_skill_ids: list[str] = preset.skills.get_placed_skill_ids()

        if skill_id not in placed_skill_ids:
            return

        setting: SkillUsageSetting = preset.usage_settings[skill_id]

        current: int = int(setting.priority)

        # 우선순위가 0이었다면: 가장 높은 우선순위(숫자 최대 + 1)
        if current == 0:
            max_priority: int = 0
            for placed_skill_id in placed_skill_ids:
                max_priority = max(
                    max_priority,
                    preset.usage_settings[placed_skill_id].priority,
                )

            setting.priority = max_priority + 1

        # 우선순위가 설정되어 있었다면: 제거 + 뒷번호 당기기
        else:
            setting.priority = 0
            for placed_skill_id in placed_skill_ids:
                s: SkillUsageSetting = preset.usage_settings[placed_skill_id]
                if s.priority > current:
                    s.priority -= 1

        self.update_from_preset(preset)
        self._on_data_changed()


class LinkSkillSettings(QFrame):
    """사이드바 타입 3 - 연계설정 스킬 목록"""

    editRequested = Signal(int, object)
    contentResized = Signal()

    def __init__(
        self,
        popup_manager: PopupManager,
        on_data_changed: Callable[[], None],
    ) -> None:
        super().__init__()

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

        for i, data in enumerate(preset.link_skills):
            link_skill: LinkSkillSettings.LinkSkillWidget = self.LinkSkillWidget(
                data,
                i,
                self.popup_manager,
                self.edit,
                self.remove,
            )
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
            data: LinkSkill = copy.deepcopy(preset.link_skills[num])
        else:
            data = copy.deepcopy(draft)

        # 편집 요청 전달
        self.editRequested.emit(num, data)

    def remove(self, num: int) -> None:
        """연계스킬 제거"""

        self.popup_manager.close_popup()

        preset: MacroPreset = self._get_preset()
        del preset.link_skills[num]

        self.update_from_preset(preset)
        self._on_data_changed()

        QTimer.singleShot(0, self.contentResized.emit)

    class LinkSkillWidget(QFrame):
        def __init__(
            self,
            data: LinkSkill,
            idx: int,
            popup_manager: PopupManager,
            edit_func: Callable[[int], None],
            remove_func: Callable[[int], None],
        ) -> None:
            super().__init__()

            self.popup_manager: PopupManager = popup_manager
            self.setObjectName("linkSkillWidget")
            self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
            self.setMaximumWidth(270)

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
                    skill_id: str = data.skills[i]
                    slot_frame = QFrame()
                    slot_frame.setFixedSize(icon_size, icon_size)
                    slot_layout = QVBoxLayout(slot_frame)
                    slot_layout.setContentsMargins(0, 0, 0, 0)

                    pixmap: QPixmap = resource_registry.get_skill_pixmap(
                        skill_id=skill_id,
                    )

                    skill = SkillImage(parent=slot_frame, pixmap=pixmap, size=icon_size)

                    # 연계 목록 아이콘 영역 전체에 공용 호버 카드 연결
                    self.popup_manager.bind_hover_card(
                        slot_frame,
                        lambda sid=skill_id: self._build_skill_hover_card(sid),
                    )
                    self.popup_manager.bind_hover_card(
                        skill,
                        lambda sid=skill_id: self._build_skill_hover_card(sid),
                    )

                    slot_layout.addWidget(skill, alignment=Qt.AlignmentFlag.AlignCenter)

                    skill_row.addWidget(slot_frame)

                skill_row.addStretch(1)

            # 구분선
            line = QFrame()
            line.setObjectName("linkDivider")
            line.setFixedHeight(1)
            root.addWidget(line)

            # 연계 유형, 시작 키 표시 컨테이너
            info_container = QHBoxLayout()
            info_container.setContentsMargins(0, 5, 0, 5)
            root.addLayout(info_container)

            is_auto: bool = data.use_type == LinkUseType.AUTO
            badge_text: str = "자동 모드" if is_auto else "수동 모드"

            use_type_display = QLabel(badge_text)
            use_type_display.setObjectName("badgeAuto" if is_auto else "badgeManual")
            use_type_display.setFont(CustomFont(10))
            use_type_display.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
            )
            info_container.addWidget(use_type_display)

            info_container.addStretch(1)

            # 시작 키 표시 컨테이너
            key_container = QWidget()

            key_layout = QHBoxLayout(key_container)
            key_layout.setContentsMargins(0, 0, 0, 0)
            key_layout.setSpacing(6)

            start_key_title = QLabel("시작 키:")
            start_key_title.setObjectName("startKeyTitle")

            start_key_value = QLabel()
            if data.key_type == LinkKeyType.ON and data.key is not None:
                key_val: str = KeyRegistry.get(data.key).display
                start_key_value.setText(key_val)
                start_key_value.setObjectName("startKeyValueSet")
            else:
                start_key_value.setText("미설정")
                start_key_value.setObjectName("startKeyValueUnset")

            key_layout.addWidget(start_key_title)
            key_layout.addWidget(start_key_value)
            info_container.addWidget(key_container)

            # 수정, 삭제 버튼 컨테이너
            btn_container = QHBoxLayout()
            btn_container.setSpacing(8)
            root.addLayout(btn_container)

            # 수정 버튼
            edit_btn = QPushButton("수정하기")
            edit_btn.setObjectName("linkEditBtn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda _, i=idx: edit_func(i))
            btn_container.addWidget(edit_btn)

            # 삭제 버튼
            remove_btn = QPushButton("삭제")
            remove_btn.setObjectName("linkRemoveBtn")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(lambda _, i=idx: remove_func(i))
            btn_container.addWidget(remove_btn)

        def _build_skill_hover_card(self, skill_id: str) -> HoverCardData:
            """연계 목록 아이콘 기준 호버 카드 구성"""

            # 현재 프리셋 레벨 기준으로 동일한 스킬 상세 구성
            level: int = app_state.macro.current_preset.info.get_skill_level(
                app_state.macro.current_server,
                skill_id,
            )
            return self.popup_manager.build_skill_hover_card(skill_id, level)


class LinkSkillEditor(QFrame):
    """사이드바 타입 4 - 연계설정 편집"""

    # 편집 종료(취소/저장) 후 목록으로 돌아가기 위한 시그널
    closed = Signal()
    saved = Signal()
    contentResized = Signal()

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
        self.add_skill_btn.setObjectName("addSkillBtn")
        self.add_skill_btn.clicked.connect(self.add_skill)
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
        if key_type == LinkKeyType.ON and self.data.key is not None:
            key_text: str = KeyRegistry.get(self.data.key).display
        else:
            key_text = ""

        self.key_setting.set_right_button_text(key_text)
        self.key_setting.set_buttons_enabled(
            key_type == LinkKeyType.OFF, key_type == LinkKeyType.ON
        )

    def _get_all_skill_ids(self) -> list[str]:
        """현재 장착 무공비급 기준 제공 스킬 ID 목록을 반환"""

        preset: MacroPreset = self._get_preset()
        return get_current_scroll_skill_ids(preset)

    def _refresh_skill_items(self) -> None:
        """self.data['skills']로 스킬 구성 UI를 다시 그림"""

        # 기존 위젯 제거
        for widget in self._skill_item_widgets:
            self._skills_layout.removeWidget(widget)
            widget.deleteLater()

        # 캐시 리스트 초기화
        self._skill_item_widgets = []

        for idx, name in enumerate(self.data.skills):
            skill_widget: LinkSkillEditor.SkillItem = self.SkillItem(
                index=idx,
                name=name,
                popup_manager=self.popup_manager,
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

        def apply(skill_id: str) -> None:
            self.change_skill(i, skill_id)

        # close_popup() 을 먼저 호출하면 코드가 실행되지 않음
        if self.popup_manager.is_popup_active(PopupKind.LINK_SKILL_SELECT):
            self.popup_manager.close_popup()
            return

        self.popup_manager.close_popup()

        # anchor: i번째 SkillItem의 스킬 버튼
        anchor_btn: QPushButton = self._skill_item_widgets[i].skill

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
        placed_skill_ids: list[str] = preset.skills.get_placed_skill_ids()

        if not all(skill_id in placed_skill_ids for skill_id in self.data.skills):
            self.popup_manager.show_notice(NoticeKind.SKILL_NOT_SELECTED)
            return

        # 지금 수정 중인 연계스킬의 인덱스
        num: int = self._editing_index

        # 자동 연계스킬 스킬 중복 검사
        auto_skills: list[str] = []
        for i, link_skill in enumerate(preset.link_skills):
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
                self.popup_manager.show_notice(NoticeKind.AUTO_ALREADY_EXIST)
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

        # close_popup() 을 먼저 호출하면 코드가 실행되지 않음
        if self.popup_manager.is_popup_active(PopupKind.LINK_SKILL_KEY):
            self.popup_manager.close_popup()
            return

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

        if skill_id not in self._get_all_skill_ids():
            return

        # 스킬명 설정 초기화
        self.data.skills[i] = skill_id

        # 수동 사용으로 변경
        self.data.set_manual()

        if self.is_skill_exceeded(skill_id):
            self.popup_manager.show_notice(NoticeKind.EXCEED_MAX_LINK_SKILL)

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
        if not all_skills:
            return

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
            self.popup_manager.show_notice(NoticeKind.EXCEED_MAX_LINK_SKILL)

        self._after_data_changed(update_skills=True)

    def cancel(self) -> None:
        """편집 취소"""

        self.popup_manager.close_popup()
        self.closed.emit()

    def save(self) -> None:
        """편집 저장"""

        self.popup_manager.close_popup()

        allowed_skill_ids: set[str] = set(self._get_all_skill_ids())
        self.data.skills = [
            skill_id for skill_id in self.data.skills if skill_id in allowed_skill_ids
        ]

        # 스킬을 하나도 추가하지 않은 경우 취소
        if not self.data.skills:
            self.cancel()
            return

        preset: MacroPreset = self._get_preset()

        # 수정하던 연계스킬의 인덱스
        index: int = self._editing_index

        # 새로 만드는 경우
        if index == -1:
            preset.link_skills.append(self.data)
            self._editing_index = len(preset.link_skills) - 1

        # 기존 연계스킬 수정하는 경우
        else:
            preset.link_skills[index] = self.data
            self._editing_index = index

        self._on_data_changed()

        self.saved.emit()
        self.closed.emit()

    def is_skill_exceeded(self, skill_id: str) -> bool:
        """연계스킬에서 특정 스킬의 최대 사용 횟수를 초과하는지 확인"""

        count: int = self.data.skills.count(skill_id)

        # 최대 사용 횟수 초과 여부 반환
        return count > 1

    class SkillItem(QFrame):
        changeRequested = Signal(int)
        removeRequested = Signal(int)

        def __init__(
            self,
            index: int,
            name: str,
            popup_manager: PopupManager,
        ) -> None:
            super().__init__()

            self.index: int = int(index)
            self.popup_manager: PopupManager = popup_manager
            self.skill_id: str = name

            self.skill = QPushButton()
            self.skill.setObjectName("skillItemBtn")
            self.skill.clicked.connect(self._emit_change)
            self.skill.setIcon(QIcon(resource_registry.get_skill_pixmap(self.skill_id)))
            # skill.setIconSize(QSize(50, 50))
            self.skill.setIconSize(QSize(36, 36))
            self.skill.setFixedSize(44, 44)
            self.skill.setToolTip(
                "연계스킬을 구성하는 스킬의 목록과 사용 횟수를 설정할 수 있습니다.\n"
                "하나의 스킬이 너무 많이 사용되면 연계가 정상적으로 작동하지 않을 수 있습니다."
            )
            self.skill.setCursor(Qt.CursorShape.PointingHandCursor)

            # 연계 편집 스킬 버튼에 공용 호버 카드 연결
            self.popup_manager.bind_hover_card(
                self.skill,
                self._build_skill_hover_card,
            )

            self.remove = QPushButton()
            self.remove.setObjectName("skillItemRemoveBtn")
            self.remove.clicked.connect(self._emit_remove)
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

        def _build_skill_hover_card(self) -> HoverCardData:
            """연계 편집 버튼 기준 호버 카드 구성"""

            # 현재 프리셋 레벨 기준으로 동일한 스킬 상세 구성
            level: int = app_state.macro.current_preset.info.get_skill_level(
                app_state.macro.current_server,
                self.skill_id,
            )
            return self.popup_manager.build_skill_hover_card(self.skill_id, level)

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

            self.left_button = QPushButton(btn0_text)
            self.left_button.setObjectName("settingItemBtn")
            self.left_button.clicked.connect(lambda: func0())
            self.left_button.setProperty("active", is_btn0_enabled)
            self.left_button.setFont(CustomFont(12))
            self.left_button.setCursor(Qt.CursorShape.PointingHandCursor)

            self.right_button = QPushButton(btn1_text)
            self.right_button.setObjectName("settingItemBtn")
            self.right_button.clicked.connect(lambda: func1())
            self.right_button.setProperty("active", is_btn1_enabled)
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

            self.left_button.setProperty("active", left_enabled)
            self.left_button.style().unpolish(self.left_button)  # type: ignore
            self.left_button.style().polish(self.left_button)  # type: ignore
            self.left_button.update()

            self.right_button.setProperty("active", right_enabled)
            self.right_button.style().unpolish(self.right_button)  # type: ignore
            self.right_button.style().polish(self.right_button)  # type: ignore
            self.right_button.update()

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

        self.setObjectName("navButtonsFrame")
        self.change_page: Callable[[Literal[0, 1, 2, 3]], None] = change_page
        self.change_layout: Callable[[int], None] = change_layout

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
        self.buttons: list[NavigationButtons.NavigationButton] = [
            self.NavigationButton(
                icon=icons[i],
                variant=str(i),
            )
            for i in range(4)
        ]

        # 계산기 버튼은 임시로 비활성화
        # calculator_button: NavigationButtons.NavigationButton = self.buttons[3]
        # calculator_button.setEnabled(False)
        # calculator_button.setCursor(Qt.CursorShape.ArrowCursor)

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
        def __init__(self, icon: QPixmap, variant: str) -> None:
            super().__init__()
            self.setObjectName("sidebarNavButton")
            self.setProperty("variant", variant)
            self.setProperty("active", False)

            self.setIcon(QIcon(icon))
            self.setIconSize(QSize(32, 32))

            self.setCursor(Qt.CursorShape.PointingHandCursor)

        def set_active(self, active: bool) -> None:
            """버튼 활성화 상태 설정"""
            self.setProperty("active", active)
            self.style().unpolish(self)  # type: ignore
            self.style().polish(self)  # type: ignore
            self.update()


class Title(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("sidebarTitle")
        self.setFont(CustomFont(20))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(250, 80)
