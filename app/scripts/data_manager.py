from __future__ import annotations

import datetime
import os
import shutil

from app.scripts.app_state import SkillSetting, app_state
from app.scripts.config import config
from app.scripts.macro_models import (
    MacroPreset,
    MacroPresetFile,
    MacroPresetRepository,
    PresetInfo,
    SkillUsageSetting,
)
from app.scripts.registry.key_registry import KeyRegistry
from app.scripts.registry.server_registry import server_registry

data_version = 1

# todo: 라이브러리를 통해 경로를 설정하도록 변경
local_appdata: str = os.environ.get("LOCALAPPDATA", default="")

data_path: str = os.path.join(local_appdata, "ProDays", "SkillMacro")
file_dir: str = os.path.join(data_path, "macros.json")


def apply_preset_to_app_state(
    preset: MacroPreset,
    preset_index: int,
    all_presets: list[MacroPreset],
) -> None:
    """MacroPreset -> AppState로 값을 반영"""

    app_state.macro.presets = all_presets
    app_state.ui.tab_names = [p.name for p in app_state.macro.presets]

    update_recent_preset(preset_index)

    # 스킬 사용설정
    for skill, setting in preset.usage_settings.items():
        app_state.skill.settings[skill] = SkillSetting(
            id=skill,
            use_skill=setting.use_skill,
            use_alone=setting.use_alone,
            priority=setting.priority,
            level=preset.info.skill_levels.get(skill, 1),
        )

    # 링크 스킬
    app_state.skill.link_skills = preset.link_settings.copy()

    # 시뮬레이션 정보
    app_state.simulation.stats = preset.info.to_stats()
    app_state.simulation.sim_details = preset.info.sim_details.copy()


def select_preset(index: int) -> None:
    """메모리 상의 app_state.macro.presets를 기준으로 프리셋을 선택"""

    apply_preset_to_app_state(
        app_state.macro.presets[index],
        preset_index=index,
        all_presets=app_state.macro.presets,
    )


def load_data(num: int = -1) -> None:
    """
    실행, 탭 변경 시 데이터 로드
    num: 탭 번호, -1이면 최근 탭
    """

    try:
        # 파일이 존재하지 않으면 데이터 생성
        if not os.path.isfile(file_dir):
            create_default_data()

        update_data()

        repo = MacroPresetRepository(file_dir)
        preset_file: MacroPresetFile = repo.load()

        # num이 -1이면 최근 탭, 아니면 해당 탭 번호
        if num == -1:
            target_index: int = preset_file.recent_preset
        else:
            target_index = num

        presets: list[MacroPreset] = preset_file.preset
        preset: MacroPreset = presets[target_index]

        apply_preset_to_app_state(
            preset,
            preset_index=target_index,
            all_presets=presets,
        )

    except Exception:
        print("데이터 로드 중 오류 발생")

        # 오류 발생 시 백업 데이터 생성
        backup_data()

        # 기본 데이터 생성
        create_default_data()

        # 데이터 다시 로드
        load_data()


def create_default_data() -> None:
    """
    오류 발생 또는 최초 실행 시 데이터 생성
    """

    repo = MacroPresetRepository(file_dir)
    preset_file = MacroPresetFile(
        version=data_version,
        recent_preset=0,
        preset=[get_default_preset()],
    )
    repo.save(preset_file)


def save_data() -> None:
    """
    데이터 저장
    """

    def apply_to_preset(preset: MacroPreset) -> None:
        """app_state 값을 preset에 반영"""

        # 프리셋 이름 저장
        preset.name = app_state.ui.tab_names[app_state.macro.current_preset_index]

        # 스킬 사용 설정 저장
        skills_all: list[str] = (
            app_state.macro.current_server.skill_registry.get_all_skill_ids()
        )
        preset.usage_settings = {
            skill_id: SkillUsageSetting(
                use_skill=app_state.skill.settings[skill_id].use_skill,
                use_alone=app_state.skill.settings[skill_id].use_alone,
                priority=app_state.skill.settings[skill_id].priority,
            )
            for skill_id in skills_all
        }

        preset.link_settings = app_state.skill.link_skills.copy()

        preset.info = PresetInfo.from_stats(
            app_state.simulation.stats,
            skill_levels={
                skill_id: app_state.skill.settings[skill_id].level
                for skill_id in skills_all
            },
            sim_details=app_state.simulation.sim_details,
        )

    repo = MacroPresetRepository(file_dir)

    apply_to_preset(app_state.macro.presets[app_state.macro.current_preset_index])

    preset_file = MacroPresetFile(
        version=data_version,
        recent_preset=app_state.macro.current_preset_index,
        preset=app_state.macro.presets.copy(),
    )
    repo.save(preset_file)


def update_recent_preset(recent_preset: int) -> None:
    """recent_preset 인덱스 저장"""

    app_state.macro.current_preset_index = recent_preset

    repo = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    preset_file.recent_preset = app_state.macro.current_preset_index
    repo.save(preset_file)


def remove_preset(
    num: int,
) -> None:
    """
    탭 제거시 데이터 삭제
    """

    repo = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    preset_file.preset.pop(num)

    repo.save(preset_file)

    # 메모리 상에도 반영
    app_state.macro.presets.pop(num)

    # tab_names 동기화
    app_state.ui.tab_names = [p.name for p in app_state.macro.presets]


def add_preset() -> None:
    """
    탭 추가시 데이터 생성
    """

    repo = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    new_preset: MacroPreset = get_default_preset()
    preset_file.preset.append(new_preset)
    repo.save(preset_file)

    # 메모리에도 반영
    app_state.macro.presets = preset_file.preset.copy()
    app_state.ui.tab_names = [p.name for p in app_state.macro.presets]


def get_default_preset() -> MacroPreset:
    """기본 프리셋 데이터 생성"""

    server_id: str = config.specs.SERVERS.default.id
    skill_count: int = server_registry.SERVERS[server_id].usable_skill_count
    skills_all: list[str] = server_registry.SERVERS[
        server_id
    ].skill_registry.get_all_skill_ids()

    return MacroPreset.create_default(
        server_id=server_id,
        skill_count=skill_count,
        skills_all=skills_all,
        default_delay=config.specs.DELAY.default,
        default_cooltime_reduction=config.specs.COOLTIME_REDUCTION.default,
        default_start_key_id=config.specs.DEFAULT_START_KEY.key_id,
    )


def update_data() -> None:
    """
    데이터 포맷 업데이트
    """

    try:
        # 데이터가 없으면 새로 생성
        if not os.path.isfile(file_dir):
            create_default_data()
            return

        repo = MacroPresetRepository(file_dir)
        preset_file: MacroPresetFile = repo.load()

        # 데이터 버전이 다르면 (구버전/타버전) 호환하지 않음
        if preset_file.version != data_version:
            pass

        return

    except Exception as e:
        print(f"데이터 업데이트 중 오류 발생: {e}")

        backup_data()

        create_default_data()


def backup_data() -> None:
    """데이터 백업"""

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
