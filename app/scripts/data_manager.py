from __future__ import annotations

import os

from app.scripts.app_state import app_state
from app.scripts.config import config
from app.scripts.macro_models import MacroPreset, MacroPresetFile, MacroPresetRepository
from app.scripts.registry.server_registry import ServerSpec, server_registry

data_version = 1

# todo: 라이브러리를 통해 경로를 설정하도록 변경
local_appdata: str = os.environ.get("LOCALAPPDATA", default="")

data_path: str = os.path.join(local_appdata, "ProDays", "SkillMacro")
file_dir: str = os.path.join(data_path, "macros_calculator_temp.json")


def load_data(num: int = -1) -> None:
    """
    실행, 탭 변경 시 데이터 로드
    num: 탭 번호, -1이면 최근 탭
    """

    update_data()

    repo: MacroPresetRepository = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    # num이 -1이면 최근 탭, 아니면 해당 탭 번호
    if num == -1:
        target_index: int = preset_file.recent_preset
    else:
        target_index: int = num

    # 프리셋 업데이트
    app_state.macro.presets = preset_file.preset
    app_state.macro.current_preset_index = target_index

    # 현재 선택 프리셋 인덱스만 즉시 반영
    if preset_file.recent_preset != target_index:
        preset_file.recent_preset = target_index
        repo.save(preset_file)


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

    repo: MacroPresetRepository = MacroPresetRepository(file_dir)

    preset_file: MacroPresetFile = MacroPresetFile(
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


def get_default_preset() -> MacroPreset:
    """기본 프리셋 데이터 생성"""

    server_id: str = config.specs.DEFAULT_SERVER_ID
    server: ServerSpec = server_registry.get(server_id)
    scroll_ids: list[str] = server.skill_registry.get_all_scroll_ids()
    skills_all: list[str] = server.skill_registry.get_all_skill_ids()

    return MacroPreset.create_default(
        server_id=server_id,
        scroll_slot_count=server.scroll_slot_count,
        scroll_ids=scroll_ids,
        skills_all=skills_all,
        default_delay=config.specs.DELAY.default,
        default_cooltime_reduction=config.specs.COOLTIME_REDUCTION.default,
        default_start_key_id=config.specs.DEFAULT_START_KEY.key_id,
        default_swap_key_id=config.specs.DEFAULT_SWAP_KEY.key_id,
    )


def update_data() -> None:
    """
    데이터 포맷 업데이트
    """

    # 데이터가 없을 때만 현재 스키마 기본 파일 생성
    if not os.path.isfile(file_dir):
        create_default_data()
        return


"""
데이터 버전 기록
...
"""
