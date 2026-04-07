from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from app.scripts.calculator_models import CustomPowerFormula
from app.scripts.config import config
from app.scripts.macro_models import (
    EquippedSkillRef,
    LinkKeyType,
    LinkSkill,
    MacroPreset,
    ThemeMode,
)
from app.scripts.registry.key_registry import KeyRegistry, KeySpec
from app.scripts.registry.server_registry import ServerSpec, server_registry

# todo: preset에 종속된 인스턴스들 모두 옮기기


@dataclass
class MacroState:
    is_running: bool = False
    run_id: int = 0

    # 사용 중인 프리셋 번호
    current_preset_index: int = 0

    # 매크로 프리셋 목록
    presets: list[MacroPreset] = field(default_factory=list)

    # 전역 사용자 정의 전투력 공식 목록
    custom_power_formulas: list[CustomPowerFormula] = field(default_factory=list)

    @property
    def current_preset(self) -> MacroPreset:
        """현재 선택된 매크로 프리셋 반환"""
        return self.presets[self.current_preset_index]

    @property
    def current_server(self) -> ServerSpec:
        """현재 매크로 프리셋의 서버 설정 반환"""
        return server_registry.get(self.current_preset.settings.server_id)

    @property
    def current_delay(self) -> int:
        """실제로 사용되는 딜레이 값을 반환"""
        if self.current_preset.settings.use_custom_delay:
            return self.current_preset.settings.custom_delay
        return config.specs.DELAY.default

    @property
    def current_cooltime_reduction(self) -> float:
        """실제로 사용되는 쿨타임 감소 값을 반환"""
        if self.current_preset.settings.use_custom_cooltime_reduction:
            return self.current_preset.settings.custom_cooltime_reduction
        return config.specs.COOLTIME_REDUCTION.default

    @property
    def current_start_key(self) -> KeySpec:
        """실제로 사용되는 시작 키 값을 반환"""
        if self.current_preset.settings.use_custom_start_key:
            return KeyRegistry.get(self.current_preset.settings.custom_start_key)
        return config.specs.DEFAULT_START_KEY

    @property
    def current_swap_key(self) -> KeySpec:
        """실제로 사용되는 스왑 키 값을 반환"""

        if self.current_preset.settings.use_custom_swap_key:
            return KeyRegistry.get(self.current_preset.settings.custom_swap_key)

        return config.specs.DEFAULT_SWAP_KEY

    @property
    def current_use_default_attack(self) -> bool:
        """기본 마우스 클릭 사용 여부 반환"""
        return self.current_preset.settings.use_default_attack

    # 매크로 실행 중 바뀌는 변수들
    # 여러 곳에서 참조되므로 여기에 보관
    task_list: list[EquippedSkillRef] = field(default_factory=list)
    prepared_skills: set[EquippedSkillRef] = field(default_factory=set)

    # 연계스킬 수행에 필요한 스킬 정보 리스트
    link_skills_requirements: list[list[EquippedSkillRef]] = field(default_factory=list)

    # 매크로 작동 중 사용하는 연계스킬 리스트
    using_link_skills: list[list[EquippedSkillRef]] = field(default_factory=list)

    # 연계가 아닌 스킬의 사용 순서
    skill_sequence: list[EquippedSkillRef] = field(default_factory=list)

    # 현재 활성화된 스킬 줄
    current_line_index: int = 0

    # AFK 모드 시작 시간
    afk_started_time: float = 0.0

    # 스킬 쿨타임 타이머
    skill_cooltime_timers: dict[EquippedSkillRef, float] = field(default_factory=dict)

    # 스킬 선입력 보호를 위한 평타 중지 종료 시각
    attack_pause_until: float = 0.0


@dataclass
class UiState:
    # 현재 프로그램 버전
    current_version: str = config.version

    # 현재 선택된 테마 모드
    theme_mode: ThemeMode = ThemeMode.SYSTEM

    # 업데이트 url
    update_url: str = ""

    # 데이터 백업 알림 대기 여부 (팝업 매니저 로딩 전이라 임시)
    has_pending_backup_notice: bool = False

    # 커스텀 무공비급 중복 정리 알림 대기 여부
    has_pending_custom_skill_normalized_notice: bool = False

    # 현재 활성화된 사이드바 페이지 인덱스
    current_sidebar_page: int = 0

    # 시작키 설정 중인지
    # todo: SessionState로 이동 고려
    is_setting_key: bool = False


@dataclass
class AppState:
    # 싱글톤 인스턴스
    # 프로그램 전체에서 단 하나의 상태 객체만 존재하도록 보장
    # 싱글톤 인스턴스라면 field 사용
    # 싱글톤이 아니지만 값이 변하지 않는 클래스라면 ClassVar 사용
    _instance: ClassVar[AppState | None] = None

    macro: MacroState = field(default_factory=MacroState)
    ui: UiState = field(default_factory=UiState)

    def is_key_using(self, key: KeySpec) -> bool:
        """
        키가 사용중인지 확인
        싱글톤 인스턴스에서는 classmethod를 사용하지 않고 인스턴스 메서드를 사용함
        """

        preset: MacroPreset = self.macro.presets[self.macro.current_preset_index]

        # 기본 시작 키
        if (
            not preset.settings.use_custom_start_key
            and key.key_id == config.specs.DEFAULT_START_KEY.key_id
        ):
            return True

        # 유저 시작 키
        if (
            preset.settings.use_custom_start_key
            and key.key_id == preset.settings.custom_start_key
        ):
            return True

        # 스킬 사용 키
        if key.key_id in preset.skills.skill_keys:
            return True

        # 기본 스왑 키
        if (
            not preset.settings.use_custom_swap_key
            and key.key_id == config.specs.DEFAULT_SWAP_KEY.key_id
        ):
            return True

        # 유저 스왑 키
        if (
            preset.settings.use_custom_swap_key
            and key.key_id == preset.settings.custom_swap_key
        ):
            return True

        # 연계 스킬 키
        for link_skill in self.macro.current_preset.link_skills:
            if (
                link_skill.key_type == LinkKeyType.ON
                and link_skill.key is not None
                and key.key_id == KeyRegistry.get(link_skill.key).key_id
            ):
                return True

        return False

    def __new__(cls) -> AppState:
        if cls._instance is None:
            cls._instance = super(AppState, cls).__new__(cls)
        return cls._instance


app_state = AppState()
