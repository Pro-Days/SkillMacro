from __future__ import annotations

import json
import os
from datetime import datetime

from app.scripts.app_state import app_state
from app.scripts.config import config
from app.scripts.custom_skill_models import CustomSkillImport
from app.scripts.macro_models import (
    LinkSkill,
    MacroPreset,
    MacroPresetFile,
    MacroPresetRepository,
    SkillUsageSetting,
    ThemeMode,
)
from app.scripts.registry.server_registry import ServerSpec, server_registry
from app.scripts.registry.skill_registry import ScrollDef, SkillDef

data_version = 2

# todo: 라이브러리를 통해 경로를 설정하도록 변경
local_appdata: str = os.environ.get("LOCALAPPDATA", default="")

data_path: str = os.path.join(local_appdata, "ProDays", "SkillMacro")
file_dir: str = os.path.join(data_path, "macros.json")
custom_skills_file_dir: str = os.path.join(data_path, "custom_skills.json")


def backup_data_file(file_path: str) -> None:
    """오류가 난 데이터 파일을 타임스탬프 백업으로 이동"""

    # 실제 파일이 있을 때만 백업 수행
    if not os.path.isfile(file_path):
        return

    # 원본 이름을 유지한 타임스탬프 백업 경로 구성
    directory_path: str = os.path.dirname(file_path)
    original_name: str = os.path.basename(file_path)
    stem: str
    suffix: str
    stem, suffix = os.path.splitext(original_name)
    timestamp: str = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_name: str = f"{stem}.backup-{timestamp}{suffix}"
    backup_path: str = os.path.join(directory_path, backup_name)

    # 손상 파일을 기본 파일 생성 전에 별도 백업으로 이동
    os.replace(file_path, backup_path)

    # UI 초기화 이후 표시할 백업 알림 대기 상태 반영
    app_state.ui.has_pending_backup_notice = True


def migrate_macro_data_file(file_path: str) -> None:
    """릴리스된 macros.json 저장 구조를 현재 버전으로 승격"""

    try:
        # 원본 JSON 루트 객체 로드 블록
        with open(file_path, "r", encoding="utf-8") as f:
            raw_obj: object = json.load(f)
    except (OSError, json.JSONDecodeError):
        # 손상 파일은 기존 복구 흐름에서 처리되도록 즉시 반환
        return

    # 루트 객체 타입 검증 블록
    if not isinstance(raw_obj, dict):
        return

    raw: dict[str, object] = raw_obj
    migrated: bool = False
    stored_version_obj: object = raw.get("version")

    # v1 -> v2 테마 저장 필드 주입 블록
    if stored_version_obj == 1:
        raw["version"] = data_version
        raw["theme_mode"] = ThemeMode.SYSTEM.value
        migrated = True

    # 마이그레이션 결과 즉시 파일 반영 블록
    if not migrated:
        return

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=4)


def create_default_custom_skills_data() -> None:
    """빈 custom_skills.json 생성"""

    # 커스텀 스킬 저장 디렉토리 보장
    os.makedirs(data_path, exist_ok=True)

    # 비어있는 커스텀 스킬 파일 초기화
    with open(custom_skills_file_dir, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)


def read_custom_skills_data() -> dict[str, dict]:
    """custom_skills.json 원본 데이터 반환"""

    # 커스텀 스킬 파일이 없으면 빈 데이터 반환
    if not os.path.isfile(custom_skills_file_dir):
        return {}

    try:
        # 커스텀 스킬 JSON 원본 로드
        with open(custom_skills_file_dir, "r", encoding="utf-8") as f:
            raw_obj: object = json.load(f)

        # 루트 객체 타입 검증
        if not isinstance(raw_obj, dict):
            raise TypeError("custom_skills root must be a dict")

        raw: dict[str, dict] = raw_obj

        normalized_raw: dict[str, dict] = {}
        normalized_any: bool = False

        # 서버별 커스텀 스킬 구조 사전 검증
        for server_id, import_data in raw.items():
            if not isinstance(server_id, str):
                raise TypeError("server_id must be a string")

            if not isinstance(import_data, dict):
                raise TypeError("custom skill import must be a dict")

            # 중복 무공비급은 첫 항목만 유지하는 블록
            scrolls_obj: object = import_data.get("scrolls", [])
            if not isinstance(scrolls_obj, list):
                raise TypeError("scrolls must be a list")

            scrolls: list[dict] = []
            seen_scroll_ids: set[str] = set()
            scroll_obj: object
            for scroll_obj in scrolls_obj:
                if not isinstance(scroll_obj, dict):
                    raise TypeError("scroll must be a dict")

                scroll_id: str = str(scroll_obj["scroll_id"]).strip()
                if scroll_id in seen_scroll_ids:
                    normalized_any = True
                    continue

                seen_scroll_ids.add(scroll_id)
                scrolls.append(scroll_obj)

            if len(scrolls) != len(scrolls_obj):
                skill_ids: list[str] = []
                seen_skill_ids: set[str] = set()
                for scroll in scrolls:
                    for skill_id in scroll["skills"]:
                        if skill_id in seen_skill_ids:
                            continue

                        seen_skill_ids.add(skill_id)
                        skill_ids.append(skill_id)

                import_data = {
                    "skills": skill_ids,
                    "scrolls": scrolls,
                    "skill_details": {
                        skill_id: import_data["skill_details"][skill_id]
                        for skill_id in skill_ids
                    },
                }

            CustomSkillImport.from_dict(import_data)
            normalized_raw[server_id] = import_data

        # 정규화 결과를 원본 파일에 즉시 반영
        if normalized_any:
            app_state.ui.has_pending_custom_skill_normalized_notice = True
            os.makedirs(data_path, exist_ok=True)
            with open(custom_skills_file_dir, "w", encoding="utf-8") as f:
                json.dump(normalized_raw, f, ensure_ascii=False, indent=4)

        raw = normalized_raw
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        # 손상된 커스텀 스킬 파일 백업 후 초기화
        backup_data_file(custom_skills_file_dir)
        create_default_custom_skills_data()
        return {}

    return raw


def load_custom_skills() -> None:
    """custom_skills.json 불러와 각 서버 SkillRegistry에 주입"""

    # 검증된 커스텀 스킬 원본 확보
    raw: dict[str, dict] = read_custom_skills_data()

    try:
        # 레지스트리 반영 전 전체 구조 파싱
        parsed_imports: dict[str, tuple[ServerSpec, CustomSkillImport]] = {}
        for server_id, import_data in raw.items():
            server_spec: ServerSpec = server_registry.get(server_id)
            skill_import: CustomSkillImport = CustomSkillImport.from_dict(import_data)
            parsed_imports[server_id] = (server_spec, skill_import)
    except (KeyError, TypeError, ValueError):
        # 레지스트리에 반영할 수 없는 커스텀 스킬 파일 백업 후 초기화
        backup_data_file(custom_skills_file_dir)
        create_default_custom_skills_data()
        return

    # 검증이 끝난 커스텀 스킬만 레지스트리에 반영
    for server_id, parsed in parsed_imports.items():
        server_spec: ServerSpec = parsed[0]
        skill_import: CustomSkillImport = parsed[1]

        for skill_id in skill_import.skills:
            skill_def_data: dict = skill_import.skill_details[skill_id].to_dict()
            skill_def: SkillDef = SkillDef.from_detail_dict(
                skill_id, server_id, skill_def_data
            )
            server_spec.skill_registry.add_skill_def(skill_def)

        for scroll in skill_import.scrolls:
            scroll_def: ScrollDef = ScrollDef(
                id=scroll.scroll_id,
                server_id=server_id,
                name=scroll.name,
                skills=scroll.skills,
            )
            server_spec.skill_registry.add_scroll_def(scroll_def)


def remove_custom_scroll(server_id: str, scroll_id: str) -> None:
    """custom_skills.json에서 무공비급 및 연결 스킬 제거, SkillRegistry에서도 제거"""

    server_spec: ServerSpec = server_registry.get(server_id)
    scroll_def: ScrollDef = server_spec.skill_registry.get_scroll(scroll_id)

    for skill_id in scroll_def.skills:
        server_spec.skill_registry.remove_skill_def(skill_id)
    server_spec.skill_registry.remove_scroll_def(scroll_id)

    if not os.path.isfile(custom_skills_file_dir):
        return

    # 검증된 커스텀 스킬 원본 조회
    existing: dict[str, dict] = read_custom_skills_data()

    if server_id not in existing:
        return

    data: dict = existing[server_id]
    skill_ids: tuple = scroll_def.skills
    data["skills"] = [s for s in data["skills"] if s not in skill_ids]
    data["scrolls"] = [s for s in data["scrolls"] if s["scroll_id"] != scroll_id]
    for skill_id in skill_ids:
        data["skill_details"].pop(skill_id, None)

    existing[server_id] = data
    with open(custom_skills_file_dir, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=4)


def save_custom_skills(server_id: str, skill_import: CustomSkillImport) -> None:
    """custom_skills.json에 서버별 커스텀 스킬 저장"""

    # 검증된 기존 커스텀 스킬 원본 조회
    existing: dict[str, dict] = read_custom_skills_data()

    existing[server_id] = skill_import.to_dict()

    os.makedirs(data_path, exist_ok=True)
    with open(custom_skills_file_dir, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=4)


def sanitize_preset_registry_references(preset: MacroPreset) -> bool:
    """레지스트리에 없는 무공비급/스킬 참조를 프리셋에서 제거"""

    server: ServerSpec = server_registry.get(preset.settings.server_id)
    valid_scroll_ids: set[str] = set(server.skill_registry.get_all_scroll_ids())
    valid_skill_ids: set[str] = set(server.skill_registry.get_all_skill_ids())
    changed: bool = False

    # 존재하지 않는 장착 무공비급 참조 제거 블록
    scroll_index: int
    for scroll_index, scroll_id in enumerate(preset.skills.equipped_scrolls):
        if not scroll_id or scroll_id in valid_scroll_ids:
            continue

        preset.skills.equipped_scrolls[scroll_index] = ""
        changed = True

    # 존재하지 않는 하단 배치 스킬 참조 제거 블록
    skill_index: int
    for skill_index, skill_id in enumerate(preset.skills.placed_skills):
        if not skill_id or skill_id in valid_skill_ids:
            continue

        preset.skills.placed_skills[skill_index] = ""
        changed = True

    # 존재하지 않는 무공비급 레벨 저장값 제거 블록
    stale_scroll_ids: list[str] = [
        scroll_id
        for scroll_id in list(preset.info.scroll_levels.keys())
        if scroll_id not in valid_scroll_ids
    ]
    stale_scroll_id: str
    for stale_scroll_id in stale_scroll_ids:
        preset.info.scroll_levels.pop(stale_scroll_id, None)
        changed = True

    # 존재하지 않는 스킬 사용설정 제거 블록
    stale_skill_ids: list[str] = [
        skill_id
        for skill_id in list(preset.usage_settings.keys())
        if skill_id not in valid_skill_ids
    ]
    stale_skill_id: str
    for stale_skill_id in stale_skill_ids:
        preset.usage_settings.pop(stale_skill_id, None)
        changed = True

    # 존재하지 않는 스킬이 포함된 연계스킬 정리 블록
    filtered_link_skills: list[LinkSkill] = []
    link_skill: LinkSkill
    for link_skill in preset.link_skills:
        filtered_skill_ids: list[str] = [
            skill_id for skill_id in link_skill.skills if skill_id in valid_skill_ids
        ]

        if not filtered_skill_ids:
            changed = True
            continue

        if filtered_skill_ids != link_skill.skills:
            link_skill.skills = filtered_skill_ids
            link_skill.set_manual()
            link_skill.clear_key()
            changed = True

        filtered_link_skills.append(link_skill)

    # 필터링 결과를 프리셋에 반영하는 블록
    if filtered_link_skills != preset.link_skills:
        preset.link_skills = filtered_link_skills

    return changed


def load_data(num: int = -1) -> None:
    """
    실행, 탭 변경 시 데이터 로드
    num: 탭 번호, -1이면 최근 탭
    """

    update_data()
    load_custom_skills()

    repo: MacroPresetRepository = MacroPresetRepository(file_dir)
    preset_was_sanitized: bool = False

    try:
        # 매크로 프리셋 파일 로드
        preset_file: MacroPresetFile = repo.load()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        # 손상된 매크로 프리셋 파일 백업 후 초기화
        backup_data_file(file_dir)
        create_default_data()
        preset_file = repo.load()

    try:
        # 파일에 저장되지 않은 기본값 항목을 인-메모리로 복원
        for preset in preset_file.preset:
            # 현재 레지스트리에 없는 고아 참조 정리 블록
            if sanitize_preset_registry_references(preset):
                preset_was_sanitized = True

            server: ServerSpec = server_registry.get(preset.settings.server_id)
            for scroll_id in server.skill_registry.get_all_scroll_ids():
                preset.info.scroll_levels.setdefault(scroll_id, 1)
            for skill_id in server.skill_registry.get_all_skill_ids():
                preset.usage_settings.setdefault(skill_id, SkillUsageSetting())

        # num이 -1이면 최근 탭, 아니면 해당 탭 번호
        if num == -1:
            target_index: int = preset_file.recent_preset
        else:
            target_index = num
    except (KeyError, TypeError, ValueError):
        # 후처리 불가능한 프리셋 파일 백업 후 초기화
        backup_data_file(file_dir)
        create_default_data()
        preset_file = repo.load()
        target_index = 0

    # 프리셋 업데이트
    app_state.macro.presets = preset_file.preset
    app_state.macro.current_preset_index = target_index
    app_state.ui.theme_mode = preset_file.theme_mode

    # 정리된 프리셋/현재 선택 인덱스 저장 반영 블록
    if preset_was_sanitized or preset_file.recent_preset != target_index:
        preset_file.recent_preset = target_index
        repo.save(preset_file)


def create_default_data() -> None:
    """
    오류 발생 또는 최초 실행 시 데이터 생성
    """

    repo = MacroPresetRepository(file_dir)
    preset_file = MacroPresetFile(
        version=data_version,
        theme_mode=app_state.ui.theme_mode,
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
        theme_mode=app_state.ui.theme_mode,
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

    new_preset: MacroPreset = get_default_preset()

    # 기존 프리셋 객체 참조를 유지한 채 새 프리셋만 메모리에 추가
    app_state.macro.presets.append(new_preset)

    # 현재 메모리 상태 전체를 저장 파일에 반영
    save_data()


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

    # 릴리스 버전 저장 포맷 승격 블록
    migrate_macro_data_file(file_dir)

    repo: MacroPresetRepository = MacroPresetRepository(file_dir)
    try:
        # 기존 프리셋 파일 기본 구조 검증
        preset_file: MacroPresetFile = repo.load()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        # 손상된 프리셋 파일 백업 후 기본값 재생성
        backup_data_file(file_dir)
        create_default_data()
        return

    # 비어있는 프리셋 목록 복구
    if not preset_file.preset:
        # 비정상 프리셋 파일 백업 후 기본값 재생성
        backup_data_file(file_dir)
        create_default_data()
        return

    # 최근 프리셋 인덱스 범위 복구
    if not (0 <= preset_file.recent_preset < len(preset_file.preset)):
        # 비정상 프리셋 파일 백업 후 기본값 재생성
        backup_data_file(file_dir)
        create_default_data()
        return


"""
데이터 버전 기록
...
"""
