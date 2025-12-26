from __future__ import annotations

import datetime
import os
import shutil
from typing import TYPE_CHECKING

from app.scripts.macro_models import (
    MacroPreset,
    MacroPresetFile,
    MacroPresetRepository,
    PresetInfo,
    SkillUsageSetting,
)
from app.scripts.misc import (
    get_available_skills,
    get_every_skills,
    get_skill_details,
    set_var_to_ClassVar,
)

if TYPE_CHECKING:
    from .shared_data import SharedData


data_version = 1

local_appdata: str = os.environ.get("LOCALAPPDATA", default="")

data_path: str = os.path.join(local_appdata, "ProDays", "SkillMacro")
file_dir: str = os.path.join(data_path, "macros.json")


def apply_preset_to_shared_data(
    shared_data: SharedData,
    preset: MacroPreset,
    preset_index: int,
    all_presets: list[MacroPreset],
) -> None:
    """MacroPreset -> SharedData로 값을 반영"""

    shared_data.presets = all_presets
    set_var_to_ClassVar(shared_data.tab_names, [p.name for p in shared_data.presets])

    update_recent_preset(shared_data, preset_index)

    # 장착된 스킬들
    set_var_to_ClassVar(shared_data.equipped_skills, preset.skills.active_skills)
    # 스킬 키(KeySpec)
    set_var_to_ClassVar(
        shared_data.skill_keys,
        [shared_data.KEY_DICT[key_id] for key_id in preset.skills.skill_keys],
    )

    # 서버 설정
    shared_data.server_ID = preset.settings.server_id

    # 딜레이
    shared_data.delay_type = preset.settings.delay[0]
    shared_data.delay_input = preset.settings.delay[1]
    shared_data.delay = (
        shared_data.DEFAULT_DELAY
        if shared_data.delay_type == 0
        else shared_data.delay_input
    )

    # 쿨타임 감소
    shared_data.cooltime_reduction_type = preset.settings.cooltime[0]
    shared_data.cooltime_reduction_input = preset.settings.cooltime[1]
    shared_data.cooltime_reduction = (
        shared_data.DEFAULT_COOLTIME_REDUCTION
        if shared_data.cooltime_reduction_type == 0
        else shared_data.cooltime_reduction_input
    )

    # 시작 키
    shared_data.start_key_type = preset.settings.start_key[0]
    shared_data.start_key_input = shared_data.KEY_DICT[preset.settings.start_key[1]]
    shared_data.start_key = (
        shared_data.DEFAULT_START_KEY
        if shared_data.start_key_type == 0
        else shared_data.start_key_input
    )

    # 마우스 클릭
    shared_data.mouse_click_type = preset.settings.mouse_click_type

    # 스킬 사용설정
    set_var_to_ClassVar(
        shared_data.is_use_skill,
        {
            skill: setting.is_use_skill
            for skill, setting in preset.usage_settings.items()
        },
    )
    set_var_to_ClassVar(
        shared_data.is_use_sole,
        {
            skill: setting.is_use_sole
            for skill, setting in preset.usage_settings.items()
        },
    )
    set_var_to_ClassVar(
        shared_data.skill_priority,
        {
            skill: setting.skill_priority
            for skill, setting in preset.usage_settings.items()
        },
    )

    # 링크 스킬
    set_var_to_ClassVar(shared_data.link_skills, preset.link_settings)

    # 시뮬레이션 정보
    shared_data.info_stats = preset.info.to_stats()
    set_var_to_ClassVar(shared_data.info_skill_levels, preset.info.skill_levels)
    set_var_to_ClassVar(shared_data.info_sim_details, preset.info.sim_details)


def select_preset(shared_data: SharedData, index: int) -> None:
    """메모리 상의 shared_data.presets를 기준으로 프리셋을 선택한다"""

    apply_preset_to_shared_data(
        shared_data,
        shared_data.presets[index],
        preset_index=index,
        all_presets=shared_data.presets,
    )


def load_data(shared_data: SharedData, num: int = -1) -> None:
    """
    실행, 탭 변경 시 데이터 로드

    shared_data: SharedData 인스턴스
    num: 탭 번호, -1이면 최근 탭
    """

    try:
        # 파일이 존재하지 않으면 데이터 생성
        if not os.path.isfile(file_dir):
            create_default_data(shared_data=shared_data)

        repo = MacroPresetRepository(file_dir)
        preset_file: MacroPresetFile = repo.load()

        # num이 -1이면 최근 탭, 아니면 해당 탭 번호
        if num == -1:
            target_index: int = preset_file.recent_preset
        else:
            target_index = num

        presets: list[MacroPreset] = preset_file.preset
        preset: MacroPreset = presets[target_index]

        apply_preset_to_shared_data(
            shared_data,
            preset,
            preset_index=target_index,
            all_presets=presets,
        )

    except Exception:
        print("Error occurred during data loading.")

        # 오류 발생 시 백업 데이터로 복원
        backup_data()

        # 기본 데이터 생성
        create_default_data(shared_data=shared_data)

        # 데이터 다시 로드
        load_data(shared_data=shared_data)


def create_default_data(shared_data: SharedData) -> None:
    """
    오류 발생 또는 최초 실행 시 데이터 생성
    """

    repo = MacroPresetRepository(file_dir)
    preset_file = MacroPresetFile(
        version=data_version,
        recent_preset=0,
        preset=[get_default_preset(shared_data=shared_data)],
    )
    repo.save(preset_file)


def save_data(shared_data: SharedData) -> None:
    """
    데이터 저장
    """

    def apply_current_shared_state_into_preset(preset: MacroPreset) -> None:
        """shared_data 값을 preset에 반영"""

        # 이름은 tab_names가 단일 출처가 아니므로 presets 기반을 우선하고, 없으면 tab_names 사용
        if shared_data.tab_names and 0 <= shared_data.recent_preset < len(
            shared_data.tab_names
        ):
            preset.name = shared_data.tab_names[shared_data.recent_preset]

        preset.skills.active_skills = list(shared_data.equipped_skills)
        preset.skills.skill_keys = [key.key_id for key in shared_data.skill_keys]

        preset.settings.server_id = shared_data.server_ID
        preset.settings.delay = (shared_data.delay_type, shared_data.delay_input)
        preset.settings.cooltime = (
            shared_data.cooltime_reduction_type,
            shared_data.cooltime_reduction_input,
        )
        preset.settings.start_key = (
            shared_data.start_key_type,
            shared_data.start_key_input.key_id,
        )
        preset.settings.mouse_click_type = shared_data.mouse_click_type

        # 스킬 사용 설정 저장
        for skill in shared_data.skill_data[shared_data.server_ID]["skills"]:
            preset.usage_settings[skill] = SkillUsageSetting(
                is_use_skill=shared_data.is_use_skill[skill],
                is_use_sole=shared_data.is_use_sole[skill],
                skill_priority=shared_data.skill_priority[skill],
            )

        preset.link_settings = list(shared_data.link_skills)

        preset.info = PresetInfo.from_stats(
            shared_data.info_stats,
            skill_levels=shared_data.info_skill_levels,
            sim_details=shared_data.info_sim_details,
        )

    repo = MacroPresetRepository(file_dir)

    apply_current_shared_state_into_preset(
        shared_data.presets[shared_data.recent_preset]
    )

    preset_file = MacroPresetFile(
        version=data_version,
        recent_preset=shared_data.recent_preset,
        preset=list(shared_data.presets),
    )
    repo.save(preset_file)


def update_recent_preset(shared_data: SharedData, recent_preset: int) -> None:
    """recent_preset 인덱스 저장"""

    shared_data.recent_preset = recent_preset

    repo = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    preset_file.recent_preset = shared_data.recent_preset
    repo.save(preset_file)


def remove_preset(num: int, shared_data: SharedData) -> None:
    """
    탭 제거시 데이터 삭제
    """

    repo = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    preset_file.preset.pop(num)

    repo.save(preset_file)

    # 메모리 상에도 반영
    shared_data.presets.pop(num)

    # tab_names 동기화
    set_var_to_ClassVar(shared_data.tab_names, [p.name for p in shared_data.presets])


def add_preset(shared_data: SharedData) -> None:
    """
    탭 추가시 데이터 생성
    """

    if not os.path.isfile(file_dir):
        create_default_data(shared_data=shared_data)

    repo = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    new_preset: MacroPreset = get_default_preset(shared_data=shared_data)
    preset_file.preset.append(new_preset)
    repo.save(preset_file)

    # 메모리 상에도 반영(현재 메모리에 없는 경우까지 고려해 전체를 동기화)
    shared_data.presets = list(preset_file.preset)
    set_var_to_ClassVar(shared_data.tab_names, [p.name for p in shared_data.presets])


def get_default_preset(shared_data: SharedData) -> MacroPreset:
    """기본 프리셋 데이터 생성"""

    server_id: str = shared_data.DEFAULT_SERVER_ID
    skill_count: int = shared_data.USABLE_SKILL_COUNT[server_id]
    skills_all: list[str] = get_every_skills(shared_data=shared_data)

    return MacroPreset.create_default(
        server_id=server_id,
        skill_count=skill_count,
        skills_all=skills_all,
        default_delay=shared_data.DEFAULT_DELAY,
        default_cooltime_reduction=shared_data.DEFAULT_COOLTIME_REDUCTION,
        default_start_key_id=shared_data.DEFAULT_START_KEY.key_id,
    )


def update_data(shared_data: SharedData) -> None:
    """
    데이터 업데이트
    """

    try:
        # 데이터가 없으면 새로 생성
        if not os.path.isfile(file_dir):
            create_default_data(shared_data=shared_data)
            return

        repo = MacroPresetRepository(file_dir)
        preset_file: MacroPresetFile = repo.load()

        # 데이터 버전이 다르면 업데이트
        # 버전 업데이트 함수 작성 필요
        if preset_file.version != data_version:
            preset_file.version = data_version

        repo.save(preset_file)

    except Exception as e:
        print(f"Error occurred: {e}")

        backup_data()

        create_default_data(shared_data=shared_data)


def update_skill_data(shared_data: SharedData) -> None:
    if not os.path.isfile(file_dir):
        create_default_data(shared_data=shared_data)
        return

    repo = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    skills_all: list[str] = get_every_skills(shared_data=shared_data)

    for preset in preset_file.preset:
        for skill in skills_all:
            preset.usage_settings.setdefault(
                skill,
                SkillUsageSetting(
                    is_use_skill=True, is_use_sole=False, skill_priority=0
                ),
            )
            preset.info.skill_levels.setdefault(skill, 1)

    repo.save(preset_file)


def backup_data() -> None:
    """
    데이터 백업
    """

    # 백업 폴더가 없으면 생성
    backup_path: str = os.path.join(data_path, "backup")
    os.makedirs(backup_path, exist_ok=True)

    # 백업 파일 경로 설정
    backup_file: str = os.path.join(
        backup_path,
        f"macros_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    # 파일이 존재하면 복사
    if os.path.isfile(file_dir):
        shutil.copy2(file_dir, backup_file)


"""
데이터 버전 기록
...
"""
