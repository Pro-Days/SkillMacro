from __future__ import annotations

import copy
import json
import os
from datetime import datetime
from typing import Any

from app.scripts.app_state import app_state
from app.scripts.character_engine import validate_character_store
from app.scripts.character_models import CHARACTER_DATA_VERSION, CharacterStore
from app.scripts.config import config
from app.scripts.custom_skill_models import CustomSkillImport
from app.scripts.macro_models import (
    DATA_VERSION,
    LinkSkill,
    MacroPreset,
    MacroPresetFile,
    MacroPresetRepository,
    SkillUsageSetting,
    ThemeMode,
)
from app.scripts.registry.server_registry import ServerSpec, server_registry
from app.scripts.registry.skill_registry import ScrollDef, SkillDef

CUSTOM_SKILLS_DATA_VERSION: int = 2

# todo: 라이브러리를 통해 경로를 설정하도록 변경
local_appdata: str = os.environ.get("LOCALAPPDATA", default="")

data_path: str = os.path.join(local_appdata, "ProDays", "SkillMacro")
file_dir: str = os.path.join(data_path, "macros.json")
custom_skills_file_dir: str = os.path.join(data_path, "custom_skills.json")
characters_file_dir: str = os.path.join(data_path, "characters.json")


class DataRecoveryStartupError(Exception):
    """기본 데이터 복구 실패로 시작을 중단해야 하는 오류"""

    def __init__(self, log_text: str) -> None:
        super().__init__(log_text)
        self.log_text: str = log_text


def _format_data_failure_log(
    file_path: str,
    stage: str,
    error: BaseException,
    backup_path: str | None,
) -> str:
    """데이터 파일 복구 실패 로그 문자열 구성"""

    # 사용자가 복사해서 보낼 수 있는 최소 진단 정보 구성
    backup_text: str = backup_path if backup_path is not None else "없음"
    return (
        f"프로그램 버전: {config.version}\n"
        f"파일 경로: {file_path}\n"
        f"단계: {stage}\n"
        f"오류 종류: {type(error).__name__}\n"
        f"오류 내용: {error}\n"
        f"백업 파일: {backup_text}"
    )


def _append_backup_notice_log(
    file_path: str,
    stage: str,
    error: BaseException,
    backup_path: str | None,
) -> None:
    """백업 알림에서 복사할 오류 로그 추가"""

    # 실제 백업이 만들어진 경우에만 알림 로그 축적
    if backup_path is None:
        return

    app_state.ui.backup_notice_logs.append(
        _format_data_failure_log(file_path, stage, error, backup_path)
    )


def _has_future_data_version(data_file_path: str, current_data_version: int) -> bool:
    """현재 프로그램보다 높은 저장 데이터 버전 여부 반환"""

    # 최초 실행 또는 데이터 파일 부재 상태 확인
    if not os.path.isfile(data_file_path):
        return False

    try:
        # 저장 데이터의 루트 버전 값만 확인
        with open(data_file_path, "r", encoding="utf-8") as f:
            raw_obj: Any = json.load(f)

    except (OSError, json.JSONDecodeError):
        return False

    # 루트 객체가 아니면 기존 로드 복구 흐름 사용
    if not isinstance(raw_obj, dict):
        return False

    stored_version_obj: Any = raw_obj.get("version")

    # 정수 버전이 아니면 기존 로드 복구 흐름 사용
    if type(stored_version_obj) is not int:
        return False

    return stored_version_obj > current_data_version


def has_future_macro_data_version() -> bool:
    """현재 프로그램보다 높은 macros.json 저장 버전 여부 반환"""

    # macros.json 저장 버전 확인
    return _has_future_data_version(file_dir, DATA_VERSION)


def has_future_custom_skills_data_version() -> bool:
    """현재 프로그램보다 높은 custom_skills.json 저장 버전 여부 반환"""

    # custom_skills.json 저장 버전 확인
    return _has_future_data_version(
        custom_skills_file_dir,
        CUSTOM_SKILLS_DATA_VERSION,
    )


def has_future_character_data_version() -> bool:
    """현재 프로그램보다 높은 characters.json 저장 버전 여부 반환"""

    # characters.json 저장 버전 확인
    return _has_future_data_version(characters_file_dir, CHARACTER_DATA_VERSION)


def backup_data_file(file_path: str) -> str | None:
    """오류가 난 데이터 파일을 타임스탬프 백업으로 이동"""

    # 실제 파일이 있을 때만 백업 수행
    if not os.path.isfile(file_path):
        return None

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
    return backup_path


def migrate_macro_data_file(file_path: str) -> None:
    """릴리스된 macros.json 저장 구조를 현재 버전으로 승격"""

    try:
        # 원본 JSON 루트 객체 로드
        with open(file_path, "r", encoding="utf-8") as f:
            raw_obj: object = json.load(f)
    except (OSError, json.JSONDecodeError):
        # 손상 파일은 기존 복구 흐름에서 처리되도록 즉시 반환
        return

    # 루트 객체 타입 검증
    if not isinstance(raw_obj, dict):
        return

    # 저장 버전별 마이그레이션 적용
    try:
        raw: dict[str, Any] = raw_obj
        migrated: bool = False
        stored_version_obj: object = raw.get("version")

        # v1 -> v2 테마 저장 필드 주입
        if stored_version_obj == 1:
            raw["version"] = 2
            raw["theme_mode"] = ThemeMode.SYSTEM.value
            stored_version_obj = 2
            migrated = True

        # v2 -> v3: 선택 공식 필드명 전환 및 커스텀 공식 저장소 초기화
        if stored_version_obj == 2:
            raw_preset: dict[str, Any]
            for raw_preset in raw["preset"]:
                raw_info: dict[str, Any] = raw_preset["info"]
                raw_calculator: dict[str, Any] = raw_info["calculator"]
                raw_selected_metric: Any = raw_calculator.pop("selected_metric")
                raw_calculator["selected_formula_id"] = str(raw_selected_metric)

            # 커스텀 공식 루트 필드 생성
            raw["custom_power_formulas"] = []
            raw["version"] = 3
            stored_version_obj = 3
            migrated = True

        # v3 -> v4: 제거된 보스/일반 전투력 선택값을 보스 데미지로 변경
        if stored_version_obj == 3:
            raw_preset: dict[str, Any]
            for raw_preset in raw["preset"]:
                raw_info: dict[str, Any] = raw_preset["info"]
                raw_calculator: dict[str, Any] = raw_info["calculator"]
                raw_selected_formula_id: str = str(
                    raw_calculator["selected_formula_id"]
                )
                if raw_selected_formula_id in ("boss", "normal"):
                    raw_calculator["selected_formula_id"] = "boss_damage"

            raw["version"] = 4
            stored_version_obj = 4
            migrated = True

        # v4 -> v5: 키 입력 유지 시간 설정, 1번 줄 자동 복귀 설정, 단독 스왑 제거, 연계스킬 쿨타임 동기화
        if stored_version_obj == 4:
            raw_preset: dict[str, Any]
            for raw_preset in raw["preset"]:
                raw_settings: dict[str, Any] = raw_preset["settings"]
                raw_settings["custom_key_hold_seconds"] = (
                    config.specs.KEY_HOLD_SECONDS.default
                )
                raw_settings["use_custom_key_hold_seconds"] = False
                raw_settings["remember_previous_state"] = False
                raw_settings["always_return_to_first_line"] = False

                # 단독 스왑 옵션 제거 (항상 켜진 동작이 기본이 됨)
                raw_usage_settings: dict[str, Any] = raw_preset["usage_settings"]
                for raw_usage_setting in raw_usage_settings.values():
                    raw_usage_setting.pop("use_solo_swap", None)

                # 연계스킬 쿨타임 동기화 옵션 기본값 주입
                for raw_link_skill in raw_preset["link_skills"]:
                    raw_link_skill["remember_state"] = False

            raw["version"] = 5
            stored_version_obj = 5
            migrated = True

        # v5 -> v6: 첫 가이드 안내 처리 상태 추가
        if stored_version_obj == 5:
            raw["guide_prompt_handled"] = False

        # v5 -> v6: 목표 단전 미리보기 기본 구조 주입
        if stored_version_obj == 5:
            raw_preset: dict[str, Any]
            for raw_preset in raw["preset"]:
                raw_info: dict[str, Any] = raw_preset["info"]
                raw_calculator: dict[str, Any] = raw_info["calculator"]
                raw_calculator["target_danjeon"] = {
                    "upper": 0,
                    "middle": 0,
                    "lower": 0,
                    "is_minimum": False,
                }

            raw["version"] = DATA_VERSION
            stored_version_obj = DATA_VERSION
            migrated = True

        # v3 이상 저장 데이터의 목표 분배 필드 누락 보정
        if (
            isinstance(stored_version_obj, int)
            and 3 <= stored_version_obj <= DATA_VERSION
        ):
            raw_preset: dict[str, Any]
            for raw_preset in raw["preset"]:
                raw_info: dict[str, Any] = raw_preset["info"]
                raw_calculator: dict[str, Any] = raw_info["calculator"]
                if "target_distribution" in raw_calculator:
                    continue

                raw_calculator["target_distribution"] = {
                    "strength": 0,
                    "dexterity": 0,
                    "vitality": 0,
                    "luck": 0,
                    "is_minimum": False,
                }
                migrated = True

    except (KeyError, TypeError, ValueError):
        return

    # 마이그레이션 결과 파일 반영
    if not migrated:
        return

    try:
        # 마이그레이션 결과 저장
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=4)
    except OSError as error:
        # 저장 실패 시 시작 중단 오류 구성
        log_text: str = _format_data_failure_log(
            file_path,
            "macros.json 마이그레이션 저장",
            error,
            None,
        )
        raise DataRecoveryStartupError(log_text) from error


def create_default_custom_skills_data() -> None:
    """빈 custom_skills.json 생성"""

    # 커스텀 스킬 저장 디렉토리 보장
    os.makedirs(data_path, exist_ok=True)

    # 비어있는 커스텀 스킬 파일 초기화
    with open(custom_skills_file_dir, "w", encoding="utf-8") as f:
        json.dump(
            {
                "version": CUSTOM_SKILLS_DATA_VERSION,
                "servers": {},
            },
            f,
            ensure_ascii=False,
            indent=4,
        )


def create_default_characters_data() -> None:
    """기본 characters.json 생성"""

    # 캐릭터 저장 디렉토리 보장
    os.makedirs(data_path, exist_ok=True)

    # 최초 실행용 기본 캐릭터 저장소 초기화
    default_store: CharacterStore = CharacterStore.create_default()

    with open(characters_file_dir, "w", encoding="utf-8") as f:
        json.dump(default_store.to_dict(), f, ensure_ascii=False, indent=4)


def load_characters() -> CharacterStore:
    """characters.json 로드 후 전역 캐릭터 상태에 반영"""

    # 최초 실행 시 빈 캐릭터 저장소 파일 생성
    if not os.path.isfile(characters_file_dir):
        create_default_characters_data()

    try:
        # 캐릭터 저장 루트 로드
        with open(characters_file_dir, "r", encoding="utf-8") as f:
            raw_obj: Any = json.load(f)

        if not isinstance(raw_obj, dict):
            raise TypeError("characters root must be a dict")

        character_store: CharacterStore = CharacterStore.from_dict(raw_obj)
        validate_character_store(character_store)

    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        # 손상된 캐릭터 파일 백업 후 빈 저장소로 복구
        try:
            backup_path: str | None = backup_data_file(characters_file_dir)

        except Exception as backup_error:
            log_text: str = "\n\n".join(
                [
                    _format_data_failure_log(
                        characters_file_dir,
                        "characters.json 읽기",
                        error,
                        None,
                    ),
                    _format_data_failure_log(
                        characters_file_dir,
                        "characters.json 백업 생성",
                        backup_error,
                        None,
                    ),
                ]
            )
            raise DataRecoveryStartupError(log_text) from backup_error

        _append_backup_notice_log(
            characters_file_dir,
            "characters.json 읽기",
            error,
            backup_path,
        )

        try:
            create_default_characters_data()

        except Exception as default_error:
            log_text = "\n\n".join(
                [
                    _format_data_failure_log(
                        characters_file_dir,
                        "characters.json 읽기",
                        error,
                        backup_path,
                    ),
                    _format_data_failure_log(
                        characters_file_dir,
                        "characters.json 기본 데이터 생성",
                        default_error,
                        None,
                    ),
                ]
            )
            raise DataRecoveryStartupError(log_text) from default_error

        character_store = CharacterStore.create_default()

    app_state.character_store = character_store
    return character_store


def save_characters() -> None:
    """characters.json에 전역 캐릭터 저장"""

    # 현재 앱 상태의 캐릭터 저장소 사용
    target_store: CharacterStore = app_state.character_store
    target_store.version = CHARACTER_DATA_VERSION
    validate_character_store(target_store)

    # 검증된 캐릭터 저장소를 독립 파일에 기록
    os.makedirs(data_path, exist_ok=True)

    with open(characters_file_dir, "w", encoding="utf-8") as f:
        json.dump(target_store.to_dict(), f, ensure_ascii=False, indent=4)


def _build_custom_skills_payload(servers: dict[str, dict]) -> dict[str, Any]:
    """커스텀 스킬 저장 루트 페이로드 구성"""

    # 독립 버전과 서버별 커스텀 스킬 데이터 묶음 구성
    payload: dict[str, Any] = {
        "version": CUSTOM_SKILLS_DATA_VERSION,
        "servers": servers,
    }
    return payload


def _normalize_custom_skill_level(raw_level_detail: Any) -> float:
    """이전 효과 목록을 단일 데미지 계수로 정규화"""

    # 직전 단일 레벨 구조는 데미지 계수만 추출
    if isinstance(raw_level_detail, dict):
        return float(raw_level_detail["damage"])

    # 이전 효과 목록은 데미지 효과만 합산하고 힐/버프는 제거
    if not isinstance(raw_level_detail, list):
        return float(raw_level_detail)

    damage: float = 0.0
    raw_effect: Any
    for raw_effect in raw_level_detail:
        if not isinstance(raw_effect, dict):
            raise TypeError("skill effect must be a dict")

        if str(raw_effect["type"]) != "damage":
            continue

        damage += float(raw_effect["damage"])

    return damage


def _normalize_custom_skill_import_data(import_data: dict[str, Any]) -> dict[str, Any]:
    """커스텀 스킬 서버 데이터 정규화"""

    # 중복 무공비급 제거 및 참조 스킬 순서 재구성
    scrolls_obj: Any = import_data.get("scrolls", [])
    if not isinstance(scrolls_obj, list):
        raise TypeError("scrolls must be a list")

    scrolls: list[dict] = []
    seen_scroll_ids: set[str] = set()
    scroll_obj: Any
    for scroll_obj in scrolls_obj:
        if not isinstance(scroll_obj, dict):
            raise TypeError("scroll must be a dict")

        scroll_id: str = str(scroll_obj["scroll_id"]).strip()
        if scroll_id in seen_scroll_ids:
            continue

        seen_scroll_ids.add(scroll_id)
        scrolls.append(scroll_obj)

    skill_ids: list[str] = []
    seen_skill_ids: set[str] = set()
    scroll: dict
    for scroll in scrolls:
        skill_id_obj: Any
        for skill_id_obj in scroll["skills"]:
            skill_id: str = str(skill_id_obj).strip()
            if skill_id in seen_skill_ids:
                continue

            seen_skill_ids.add(skill_id)
            skill_ids.append(skill_id)

    # 선언된 스킬만 새 단일 데미지 구조로 변환
    raw_skill_details_obj: Any = import_data["skill_details"]
    if not isinstance(raw_skill_details_obj, dict):
        raise TypeError("skill_details must be a dict")

    raw_skill_details: dict[str, Any] = raw_skill_details_obj
    skill_details: dict[str, dict[str, Any]] = {}
    skill_id: str
    for skill_id in skill_ids:
        raw_detail_obj: Any = raw_skill_details[skill_id]
        if not isinstance(raw_detail_obj, dict):
            raise TypeError("skill detail must be a dict")

        raw_detail: dict[str, Any] = raw_detail_obj
        raw_levels_obj: Any = raw_detail.get("levels", {})
        if not isinstance(raw_levels_obj, dict):
            raise TypeError("levels must be a dict")

        levels: dict[str, float] = {}
        raw_level: Any
        raw_level_detail: Any
        for raw_level, raw_level_detail in raw_levels_obj.items():
            levels[str(raw_level)] = _normalize_custom_skill_level(raw_level_detail)

        # 저장 구조 기준 타겟 수 조회 및 이전 데이터 기본값 적용
        target_count: int = raw_detail.get("target_count", 1)
        if type(target_count) is not int:
            raise ValueError("target_count must be an integer")

        if target_count < 1:
            raise ValueError("target_count must be greater than 0")

        skill_details[skill_id] = {
            "name": str(raw_detail["name"]),
            "cooltime": float(raw_detail["cooltime"]),
            "target_count": target_count,
            "levels": levels,
        }

    normalized_import_data: dict[str, Any] = {
        "skills": skill_ids,
        "scrolls": scrolls,
        "skill_details": skill_details,
    }
    return normalized_import_data


def _extract_custom_skill_servers(raw: dict[str, Any]) -> tuple[dict[str, dict], bool]:
    """커스텀 스킬 저장 루트에서 서버별 데이터 추출"""

    # 파일 갱신 필요 여부 추적
    changed: bool = False

    # 버전 루트가 없는 기존 파일은 전체 객체를 서버 데이터로 간주
    if "version" in raw and "servers" in raw:
        raw_version: int = int(raw["version"])
        if raw_version > CUSTOM_SKILLS_DATA_VERSION:
            raise ValueError("custom_skills version is newer than supported")

        raw_servers_obj: Any = raw["servers"]
        if not isinstance(raw_servers_obj, dict):
            raise TypeError("custom_skills servers must be a dict")

        raw_servers: dict[str, Any] = raw_servers_obj
        changed = raw_version != CUSTOM_SKILLS_DATA_VERSION
    else:
        raw_servers = raw
        changed = True

    normalized_servers: dict[str, dict] = {}
    server_id: str
    import_data_obj: Any
    for server_id, import_data_obj in raw_servers.items():
        if not isinstance(server_id, str):
            raise TypeError("server_id must be a string")

        if not isinstance(import_data_obj, dict):
            raise TypeError("custom skill import must be a dict")

        normalized_import_data: dict[str, Any] = _normalize_custom_skill_import_data(
            import_data_obj
        )
        if normalized_import_data != import_data_obj:
            changed = True

        normalized_servers[server_id] = normalized_import_data

    return normalized_servers, changed


def _write_custom_skills_data(servers: dict[str, dict]) -> None:
    """커스텀 스킬 서버 데이터 저장"""

    # 독립 버전 루트에 서버별 데이터를 감싸서 저장
    os.makedirs(data_path, exist_ok=True)
    with open(custom_skills_file_dir, "w", encoding="utf-8") as f:
        json.dump(
            _build_custom_skills_payload(servers),
            f,
            ensure_ascii=False,
            indent=4,
        )


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

        raw: dict[str, Any] = raw_obj

        normalized_raw: dict[str, dict]
        changed: bool
        normalized_raw, changed = _extract_custom_skill_servers(raw)

        # 서버별 커스텀 스킬 구조 사전 검증
        server_id: str
        import_data: dict
        for server_id, import_data in normalized_raw.items():
            CustomSkillImport.from_dict(import_data)

        # 파일 갱신이 필요하면 즉시 저장
        if changed:
            _write_custom_skills_data(normalized_raw)

        raw = normalized_raw
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        # 손상된 커스텀 스킬 파일 백업 후 초기화
        try:
            backup_path: str | None = backup_data_file(custom_skills_file_dir)
        except Exception as backup_error:
            log_text: str = "\n\n".join(
                [
                    _format_data_failure_log(
                        custom_skills_file_dir,
                        "custom_skills.json 읽기",
                        error,
                        None,
                    ),
                    _format_data_failure_log(
                        custom_skills_file_dir,
                        "custom_skills.json 백업 생성",
                        backup_error,
                        None,
                    ),
                ]
            )
            raise DataRecoveryStartupError(log_text) from backup_error

        _append_backup_notice_log(
            custom_skills_file_dir,
            "custom_skills.json 읽기",
            error,
            backup_path,
        )
        try:
            create_default_custom_skills_data()
        except Exception as default_error:
            log_text = "\n\n".join(
                [
                    _format_data_failure_log(
                        custom_skills_file_dir,
                        "custom_skills.json 읽기",
                        error,
                        backup_path,
                    ),
                    _format_data_failure_log(
                        custom_skills_file_dir,
                        "custom_skills.json 기본 데이터 생성",
                        default_error,
                        None,
                    ),
                ]
            )
            raise DataRecoveryStartupError(log_text) from default_error

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
    except (KeyError, TypeError, ValueError) as error:
        # 레지스트리에 반영할 수 없는 커스텀 스킬 파일 백업 후 초기화
        try:
            backup_path: str | None = backup_data_file(custom_skills_file_dir)
        except Exception as backup_error:
            log_text = "\n\n".join(
                [
                    _format_data_failure_log(
                        custom_skills_file_dir,
                        "custom_skills.json 레지스트리 반영",
                        error,
                        None,
                    ),
                    _format_data_failure_log(
                        custom_skills_file_dir,
                        "custom_skills.json 백업 생성",
                        backup_error,
                        None,
                    ),
                ]
            )
            raise DataRecoveryStartupError(log_text) from backup_error

        _append_backup_notice_log(
            custom_skills_file_dir,
            "custom_skills.json 레지스트리 반영",
            error,
            backup_path,
        )
        try:
            create_default_custom_skills_data()
        except Exception as default_error:
            log_text = "\n\n".join(
                [
                    _format_data_failure_log(
                        custom_skills_file_dir,
                        "custom_skills.json 레지스트리 반영",
                        error,
                        backup_path,
                    ),
                    _format_data_failure_log(
                        custom_skills_file_dir,
                        "custom_skills.json 기본 데이터 생성",
                        default_error,
                        None,
                    ),
                ]
            )
            raise DataRecoveryStartupError(log_text) from default_error

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
    _write_custom_skills_data(existing)


def save_custom_skills(server_id: str, skill_import: CustomSkillImport) -> None:
    """custom_skills.json에 서버별 커스텀 스킬 저장"""

    # 검증된 기존 커스텀 스킬 원본 조회
    existing: dict[str, dict] = read_custom_skills_data()

    existing[server_id] = skill_import.to_dict()

    _write_custom_skills_data(existing)


def sanitize_preset_registry_references(preset: MacroPreset) -> bool:
    """레지스트리에 없는 무공비급/스킬 참조를 프리셋에서 제거"""

    server: ServerSpec = server_registry.get(preset.settings.server_id)
    valid_scroll_ids: set[str] = set(server.skill_registry.get_all_scroll_ids())
    valid_skill_ids: set[str] = set(server.skill_registry.get_all_skill_ids())
    changed: bool = False

    # 존재하지 않는 장착 무공비급 참조 제거
    scroll_index: int
    for scroll_index, scroll_id in enumerate(preset.skills.equipped_scrolls):
        if not scroll_id or scroll_id in valid_scroll_ids:
            continue

        preset.skills.equipped_scrolls[scroll_index] = ""
        changed = True

    # 존재하지 않는 하단 배치 스킬 참조 제거
    skill_index: int
    for skill_index, skill_id in enumerate(preset.skills.placed_skills):
        if not skill_id or skill_id in valid_skill_ids:
            continue

        preset.skills.placed_skills[skill_index] = ""
        changed = True

    # 존재하지 않는 무공비급 레벨 저장값 제거
    stale_scroll_ids: list[str] = [
        scroll_id
        for scroll_id in list(preset.info.scroll_levels.keys())
        if scroll_id not in valid_scroll_ids
    ]
    stale_scroll_id: str
    for stale_scroll_id in stale_scroll_ids:
        preset.info.scroll_levels.pop(stale_scroll_id, None)
        changed = True

    # 존재하지 않는 스킬 사용설정 제거
    stale_skill_ids: list[str] = [
        skill_id
        for skill_id in list(preset.usage_settings.keys())
        if skill_id not in valid_skill_ids
    ]
    stale_skill_id: str
    for stale_skill_id in stale_skill_ids:
        preset.usage_settings.pop(stale_skill_id, None)
        changed = True

    # 존재하지 않는 스킬이 포함된 연계스킬 정리
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

    # 정리된 연계스킬 목록 반영
    if filtered_link_skills != preset.link_skills:
        preset.link_skills = filtered_link_skills

    return changed


def _restore_macro_data_after_failure(
    repo: MacroPresetRepository,
    stage: str,
    error: BaseException,
) -> MacroPresetFile:
    """macros.json 백업 및 기본 데이터 재읽기"""

    try:
        # 손상 파일 백업 시도
        backup_path: str | None = backup_data_file(file_dir)
    except Exception as backup_error:
        # 백업을 만들 수 없으면 시작 중단 오류 구성
        log_text: str = "\n\n".join(
            [
                _format_data_failure_log(file_dir, stage, error, None),
                _format_data_failure_log(
                    file_dir,
                    "macros.json 백업 생성",
                    backup_error,
                    None,
                ),
            ]
        )
        raise DataRecoveryStartupError(log_text) from backup_error

    # 백업 알림 로그 기록
    _append_backup_notice_log(file_dir, stage, error, backup_path)

    try:
        # 현재 스키마 기본 데이터 생성
        create_default_data()
    except Exception as default_error:
        # 기본 파일을 만들 수 없으면 시작 중단 오류 구성
        log_text: str = "\n\n".join(
            [
                _format_data_failure_log(file_dir, stage, error, backup_path),
                _format_data_failure_log(
                    file_dir,
                    "macros.json 기본 데이터 생성",
                    default_error,
                    None,
                ),
            ]
        )
        raise DataRecoveryStartupError(log_text) from default_error

    try:
        # 기본 데이터가 실제로 읽히는지 확인
        preset_file: MacroPresetFile = repo.load()
    except Exception as reload_error:
        # 기본 파일 재읽기 실패 시 시작 중단 오류 구성
        log_text = "\n\n".join(
            [
                _format_data_failure_log(file_dir, stage, error, backup_path),
                _format_data_failure_log(
                    file_dir,
                    "macros.json 기본 데이터 재읽기",
                    reload_error,
                    None,
                ),
            ]
        )
        raise DataRecoveryStartupError(log_text) from reload_error

    return preset_file


def load_data(num: int = -1) -> None:
    """
    실행, 탭 변경 시 데이터 로드
    num: 탭 번호, -1이면 최근 탭
    """

    update_data()
    load_custom_skills()
    load_characters()

    repo: MacroPresetRepository = MacroPresetRepository(file_dir)
    preset_was_sanitized: bool = False

    try:
        # 매크로 프리셋 파일 로드
        preset_file: MacroPresetFile = repo.load()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        # 손상된 매크로 프리셋 파일 백업 후 초기화
        preset_file = _restore_macro_data_after_failure(
            repo,
            "macros.json 읽기",
            error,
        )

    try:
        # 파일에 저장되지 않은 기본값 항목을 인-메모리로 복원
        for preset in preset_file.preset:
            # 현재 레지스트리에 없는 참조 정리
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
    except (KeyError, TypeError, ValueError) as error:
        # 후처리 불가능한 프리셋 파일 백업 후 초기화
        preset_file = _restore_macro_data_after_failure(
            repo,
            "macros.json 후처리",
            error,
        )
        target_index = 0

    # 프리셋/전역 공식 메모리 반영
    app_state.macro.presets = preset_file.preset
    app_state.macro.custom_power_formulas = preset_file.custom_power_formulas
    app_state.macro.current_preset_index = target_index
    app_state.ui.theme_mode = preset_file.theme_mode
    app_state.ui.guide_prompt_handled = preset_file.guide_prompt_handled

    # 정리 결과와 현재 선택 인덱스 저장 반영
    if preset_was_sanitized or preset_file.recent_preset != target_index:
        preset_file.recent_preset = target_index
        try:
            # 시작 중 자동 정리된 프리셋 파일 저장
            repo.save(preset_file)
        except OSError as error:
            # 정리 결과 저장 실패 시 시작 중단 오류 구성
            log_text: str = _format_data_failure_log(
                file_dir,
                "macros.json 정리 결과 저장",
                error,
                None,
            )
            raise DataRecoveryStartupError(log_text) from error


def create_default_data() -> None:
    """
    오류 발생 또는 최초 실행 시 데이터 생성
    """

    # 새 기본 데이터 생성 시 남아 있는 쿨타임 상태 제거
    if not app_state.macro.is_running:
        app_state.macro.clear_cooltime_state()

    repo = MacroPresetRepository(file_dir)
    preset_file = MacroPresetFile(
        version=DATA_VERSION,
        theme_mode=app_state.ui.theme_mode,
        guide_prompt_handled=app_state.ui.guide_prompt_handled,
        recent_preset=0,
        custom_power_formulas=[],
        preset=[get_default_preset()],
    )
    repo.save(preset_file)


def save_data() -> None:
    """
    데이터 저장
    """

    # 비실행 중 저장되는 설정 변경은 다음 시작 쿨타임 초기화로 처리
    if not app_state.macro.is_running:
        app_state.macro.clear_cooltime_state()

    repo: MacroPresetRepository = MacroPresetRepository(file_dir)

    preset_file: MacroPresetFile = MacroPresetFile(
        version=DATA_VERSION,
        theme_mode=app_state.ui.theme_mode,
        guide_prompt_handled=app_state.ui.guide_prompt_handled,
        recent_preset=app_state.macro.current_preset_index,
        custom_power_formulas=app_state.macro.custom_power_formulas.copy(),
        preset=app_state.macro.presets.copy(),
    )

    repo.save(preset_file)


def update_recent_preset(recent_preset: int) -> None:
    """recent_preset 인덱스 저장"""

    # 현재 프리셋 전환 상태 반영
    app_state.macro.current_preset_index = recent_preset

    # 프리셋이 바뀌면 이전 프리셋의 쿨타임 상태 제거
    if not app_state.macro.is_running:
        app_state.macro.clear_cooltime_state()

    repo = MacroPresetRepository(file_dir)
    preset_file: MacroPresetFile = repo.load()

    preset_file.recent_preset = app_state.macro.current_preset_index
    repo.save(preset_file)


def remove_preset(
    num: int,
) -> None:
    """
    탭 제거 시 데이터 삭제
    """

    # 프리셋 삭제 시 남아 있는 쿨타임 상태 제거
    if not app_state.macro.is_running:
        app_state.macro.clear_cooltime_state()

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


def copy_preset(source_index: int) -> None:
    """
    선택 프리셋 복사 생성
    """

    # 프리셋 상태 전체 딥카피
    copied_preset: MacroPreset = copy.deepcopy(app_state.macro.presets[source_index])
    for link_skill in copied_preset.link_skills:
        link_skill.skill_timers.clear()

    app_state.macro.presets.append(copied_preset)

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
        try:
            # 최초 실행 기본 데이터 생성
            create_default_data()
        except Exception as error:
            # 최초 기본 데이터 생성 실패 시 시작 중단 오류 구성
            log_text: str = _format_data_failure_log(
                file_dir,
                "macros.json 최초 기본 데이터 생성",
                error,
                None,
            )
            raise DataRecoveryStartupError(log_text) from error

        return

    # 릴리스 버전 저장 포맷 승격
    migrate_macro_data_file(file_dir)

    repo: MacroPresetRepository = MacroPresetRepository(file_dir)
    try:
        # 기존 프리셋 파일 기본 구조 검증
        preset_file: MacroPresetFile = repo.load()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        # 손상된 프리셋 파일 백업 후 기본값 재생성
        _restore_macro_data_after_failure(repo, "macros.json 구조 검증", error)
        return

    # 비어있는 프리셋 목록 복구
    if not preset_file.preset:
        # 비정상 프리셋 파일 백업 후 기본값 재생성
        empty_preset_error: ValueError = ValueError("프리셋 목록이 비어 있습니다.")
        _restore_macro_data_after_failure(
            repo,
            "macros.json 프리셋 목록 검증",
            empty_preset_error,
        )
        return

    # 최근 프리셋 인덱스 범위 복구
    if not (0 <= preset_file.recent_preset < len(preset_file.preset)):
        # 비정상 프리셋 파일 백업 후 기본값 재생성
        recent_preset_error: ValueError = ValueError(
            f"최근 프리셋 번호가 범위를 벗어났습니다: {preset_file.recent_preset}"
        )
        _restore_macro_data_after_failure(
            repo,
            "macros.json 최근 프리셋 번호 검증",
            recent_preset_error,
        )
        return
