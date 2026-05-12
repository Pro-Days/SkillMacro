from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.scripts import data_manager
from app.scripts.custom_skill_models import CustomSkillImport
from app.scripts.data_manager import (
    CUSTOM_SKILLS_DATA_VERSION,
    DATA_VERSION,
    migrate_macro_data_file,
)
from app.scripts.macro_models import (
    MacroPresetFile,
    MacroPresetRepository,
)


def _make_v4_macros_json() -> dict[str, Any]:
    """v1.0.5가 저장하던 v4 macros.json 원본 구조 생성"""

    # 실제 한월 RPG 서버 기반 (skill_data.json에 존재하는 스킬 사용)
    scroll_id: str = "builtin:한월 RPG:수류검법"
    skill_a: str = "builtin:한월 RPG:수류참"
    skill_b: str = "builtin:한월 RPG:수류섬"

    return {
        "version": 4,
        "theme_mode": "system",
        "recent_preset": 0,
        "custom_power_formulas": [],
        "preset": [
            {
                "name": "테스트 프리셋",
                "skills": {
                    "equipped_scrolls": [scroll_id, "", "", "", "", "", ""],
                    "placed_skills": [
                        skill_a, skill_b, "", "", "", "",
                        "", "", "", "", "", "", "", "",
                    ],
                    "skill_keys": ["2", "3", "4", "5", "6", "7", "8"],
                },
                "settings": {
                    "server_id": "한월 RPG",
                    "custom_delay": 300,
                    "use_custom_delay": False,
                    "custom_cooltime_reduction": 0,
                    "use_custom_cooltime_reduction": False,
                    "custom_start_key": "f9",
                    "use_custom_start_key": False,
                    "custom_swap_key": "h",
                    "use_custom_swap_key": False,
                    "use_default_attack": False,
                },
                "usage_settings": {
                    skill_a: {
                        "use_skill": True,
                        "use_alone": False,
                        "priority": 0,
                        "use_solo_swap": True,
                    },
                    skill_b: {
                        "use_skill": True,
                        "use_alone": False,
                        "priority": 0,
                        "use_solo_swap": False,
                    },
                },
                "link_skills": [
                    {
                        "useType": "manual",
                        "keyType": "off",
                        "key": None,
                        "skills": [skill_a, skill_b],
                    }
                ],
                "info": {
                    "scroll_levels": {scroll_id: 5},
                    "calculator": {
                        "base_stats": {
                            "attack": 0.0, "attack_percent": 0.0,
                            "hp": 0.0, "hp_percent": 0.0,
                            "str": 0.0, "str_percent": 0.0,
                            "dexterity": 0.0, "dexterity_percent": 0.0,
                            "vitality": 0.0, "vitality_percent": 0.0,
                            "luck": 0.0, "luck_percent": 0.0,
                            "skill_damage_percent": 0.0,
                            "final_attack_percent": 0.0,
                            "crit_rate_percent": 0.0,
                            "crit_damage_percent": 110.0,
                            "exp_percent": 0.0,
                            "boss_attack_percent": 0.0,
                            "drop_rate_percent": 0.0,
                            "dodge_percent": 0.0,
                            "potion_heal_percent": 0.0,
                            "resist_percent": 0.0,
                            "skill_speed_percent": 0.0,
                        },
                        "level": 50,
                        "realm_tier": "third_rate",
                        "selected_formula_id": "boss_damage",
                        "distribution": {
                            "strength": 0, "dexterity": 0,
                            "vitality": 0, "luck": 0,
                            "is_locked": False, "use_reset": False,
                        },
                        "target_distribution": {
                            "strength": 0, "dexterity": 0,
                            "vitality": 0, "luck": 0,
                            "is_minimum": False,
                        },
                        "danjeon": {
                            "upper": 0, "middle": 0, "lower": 0,
                            "is_locked": False, "use_reset": False,
                        },
                        "owned_titles": [],
                        "owned_talismans": [],
                        "equipped_state": {
                            "equipped_title_name": None,
                            "equipped_talisman_names": [],
                        },
                        "custom_stat_changes": {
                            "attack": 0.0, "attack_percent": 0.0,
                            "hp": 0.0, "hp_percent": 0.0,
                            "str": 0.0, "str_percent": 0.0,
                            "dexterity": 0.0, "dexterity_percent": 0.0,
                            "vitality": 0.0, "vitality_percent": 0.0,
                            "luck": 0.0, "luck_percent": 0.0,
                            "skill_damage_percent": 0.0,
                            "final_attack_percent": 0.0,
                            "crit_rate_percent": 0.0,
                            "crit_damage_percent": 0.0,
                            "exp_percent": 0.0,
                            "boss_attack_percent": 0.0,
                            "drop_rate_percent": 0.0,
                            "dodge_percent": 0.0,
                            "potion_heal_percent": 0.0,
                            "resist_percent": 0.0,
                            "skill_speed_percent": 0.0,
                        },
                    },
                },
            }
        ],
    }


def _make_v3_macros_json() -> dict[str, Any]:
    """v1.0.4 즈음의 v3 macros.json 구조 생성

    v4와의 차이: selected_formula_id가 "boss"/"normal" (v3→v4에서 "boss_damage"로 변환).
    """

    payload: dict[str, Any] = _make_v4_macros_json()
    payload["version"] = 3
    # v3 시점의 선택 공식 식별자는 boss/normal 둘 중 하나
    payload["preset"][0]["info"]["calculator"]["selected_formula_id"] = "boss"
    return payload


def _make_v2_macros_json() -> dict[str, Any]:
    """v1.0.2~v1.0.3 즈음의 v2 macros.json 구조 생성

    v3와의 차이:
    - calculator에 selected_metric 키 사용 (v2→v3에서 selected_formula_id로 변경)
    - custom_power_formulas 루트 필드 없음
    """

    payload: dict[str, Any] = _make_v3_macros_json()
    payload["version"] = 2
    # v3 → v4의 boss → boss_damage 변환과 무관하게,
    # v2 시점에는 selected_metric 키를 사용
    calculator: dict[str, Any] = payload["preset"][0]["info"]["calculator"]
    calculator["selected_metric"] = calculator.pop("selected_formula_id")
    # v2에는 커스텀 공식 루트 필드가 없음
    payload.pop("custom_power_formulas")
    return payload


def _make_v1_macros_json() -> dict[str, Any]:
    """v1.0.1 즈음의 v1 macros.json 구조 생성

    v2와의 차이: theme_mode 루트 필드 없음.
    """

    payload: dict[str, Any] = _make_v2_macros_json()
    payload["version"] = 1
    # v1 → v2에서 theme_mode가 추가되므로 v1에는 존재하지 않음
    payload.pop("theme_mode")
    return payload


def _write_json(path: str, payload: Any) -> None:
    """JSON 파일 기록 헬퍼"""

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)


def _read_json(path: str) -> Any:
    """JSON 파일 읽기 헬퍼"""

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# 각 시작 버전별 픽스처 생성기 매핑
_VERSION_PAYLOAD_BUILDERS: dict[int, Any] = {
    1: _make_v1_macros_json,
    2: _make_v2_macros_json,
    3: _make_v3_macros_json,
    4: _make_v4_macros_json,
}


@pytest.mark.parametrize("start_version", sorted(_VERSION_PAYLOAD_BUILDERS.keys()))
def test_macros_migrates_from_any_version_to_current(
    start_version: int,
    isolated_data_paths: dict[str, str],
) -> None:
    """v1 ~ v4 어느 시작 버전이든 현재 DATA_VERSION까지 정상 승격된다"""

    file_path: str = isolated_data_paths["file_dir"]
    payload: dict[str, Any] = _VERSION_PAYLOAD_BUILDERS[start_version]()
    assert payload["version"] == start_version

    _write_json(file_path, payload)
    migrate_macro_data_file(file_path)

    migrated: dict[str, Any] = _read_json(file_path)
    assert migrated["version"] == DATA_VERSION


@pytest.mark.parametrize("start_version", sorted(_VERSION_PAYLOAD_BUILDERS.keys()))
def test_macros_migrated_file_loads_as_preset_file(
    start_version: int,
    isolated_data_paths: dict[str, str],
) -> None:
    """마이그레이션 후 MacroPresetFile.from_dict가 어느 버전에서도 정상 로드한다"""

    file_path: str = isolated_data_paths["file_dir"]
    payload: dict[str, Any] = _VERSION_PAYLOAD_BUILDERS[start_version]()
    _write_json(file_path, payload)

    migrate_macro_data_file(file_path)

    repo: MacroPresetRepository = MacroPresetRepository(file_path)
    preset_file: MacroPresetFile = repo.load()

    assert preset_file.version == DATA_VERSION
    assert len(preset_file.preset) == 1
    assert preset_file.preset[0].name == "테스트 프리셋"


@pytest.mark.parametrize("start_version", sorted(_VERSION_PAYLOAD_BUILDERS.keys()))
def test_macros_migration_sets_boss_damage_for_legacy_metric(
    start_version: int,
    isolated_data_paths: dict[str, str],
) -> None:
    """v1/v2의 selected_metric=boss, v3의 selected_formula_id=boss 가 모두 boss_damage로 변환된다"""

    file_path: str = isolated_data_paths["file_dir"]
    payload: dict[str, Any] = _VERSION_PAYLOAD_BUILDERS[start_version]()
    _write_json(file_path, payload)

    migrate_macro_data_file(file_path)

    migrated: dict[str, Any] = _read_json(file_path)
    calculator: dict[str, Any] = migrated["preset"][0]["info"]["calculator"]
    assert calculator["selected_formula_id"] == "boss_damage"


def test_v4_migration_adds_new_settings_fields(
    isolated_data_paths: dict[str, str],
) -> None:
    """v4 → v5 마이그레이션이 새 settings 필드를 주입한다"""

    file_path: str = isolated_data_paths["file_dir"]
    _write_json(file_path, _make_v4_macros_json())

    migrate_macro_data_file(file_path)

    migrated: dict[str, Any] = _read_json(file_path)
    settings: dict[str, Any] = migrated["preset"][0]["settings"]
    assert "custom_key_hold_seconds" in settings
    assert "use_custom_key_hold_seconds" in settings
    assert "remember_previous_state" in settings
    assert "always_return_to_first_line" in settings


def test_v4_migration_removes_use_solo_swap(
    isolated_data_paths: dict[str, str],
) -> None:
    """v4 → v5 마이그레이션이 usage_settings의 use_solo_swap을 제거한다"""

    file_path: str = isolated_data_paths["file_dir"]
    _write_json(file_path, _make_v4_macros_json())

    migrate_macro_data_file(file_path)

    migrated: dict[str, Any] = _read_json(file_path)
    usage_settings: dict[str, Any] = migrated["preset"][0]["usage_settings"]
    for setting in usage_settings.values():
        assert "use_solo_swap" not in setting


def test_v4_migration_adds_remember_state_to_link_skills(
    isolated_data_paths: dict[str, str],
) -> None:
    """v4 → v5 마이그레이션이 link_skills에 remember_state=False를 주입한다"""

    file_path: str = isolated_data_paths["file_dir"]
    _write_json(file_path, _make_v4_macros_json())

    migrate_macro_data_file(file_path)

    migrated: dict[str, Any] = _read_json(file_path)
    link_skills: list[dict[str, Any]] = migrated["preset"][0]["link_skills"]
    for link_skill in link_skills:
        assert link_skill["remember_state"] is False


def test_v3_missing_target_distribution_is_added(
    isolated_data_paths: dict[str, str],
) -> None:
    """v3 파일에 target_distribution이 없으면 기본값으로 채워진다"""

    file_path: str = isolated_data_paths["file_dir"]
    v3_payload: dict[str, Any] = _make_v4_macros_json()
    v3_payload["version"] = 3
    # v3 파일에서 target_distribution이 없는 상황 재현
    v3_payload["preset"][0]["info"]["calculator"].pop("target_distribution")
    _write_json(file_path, v3_payload)

    migrate_macro_data_file(file_path)

    migrated: dict[str, Any] = _read_json(file_path)
    target_dist: dict[str, Any] = (
        migrated["preset"][0]["info"]["calculator"]["target_distribution"]
    )
    assert target_dist == {
        "strength": 0,
        "dexterity": 0,
        "vitality": 0,
        "luck": 0,
        "is_minimum": False,
    }


def test_save_and_reload_round_trip(
    isolated_data_paths: dict[str, str],
) -> None:
    """현재 버전 파일 저장 후 다시 로드해도 동일한 핵심 필드 유지"""

    file_path: str = isolated_data_paths["file_dir"]
    _write_json(file_path, _make_v4_macros_json())
    migrate_macro_data_file(file_path)

    repo: MacroPresetRepository = MacroPresetRepository(file_path)
    first_load: MacroPresetFile = repo.load()
    repo.save(first_load)
    second_load: MacroPresetFile = repo.load()

    assert first_load.to_dict() == second_load.to_dict()


def _make_legacy_custom_skills_json() -> dict[str, Any]:
    """v1.0.5 이전 list-of-effects 구조의 custom_skills.json 생성"""

    return {
        "version": CUSTOM_SKILLS_DATA_VERSION,
        "servers": {
            "한월 RPG": {
                "skills": [
                    "custom:한월 RPG:테스트:공격1",
                    "custom:한월 RPG:테스트:공격2",
                ],
                "scrolls": [
                    {
                        "scroll_id": "custom:한월 RPG:테스트",
                        "name": "테스트",
                        "skills": [
                            "custom:한월 RPG:테스트:공격1",
                            "custom:한월 RPG:테스트:공격2",
                        ],
                    }
                ],
                "skill_details": {
                    "custom:한월 RPG:테스트:공격1": {
                        "name": "공격1",
                        "cooltime": 5.0,
                        # 이전 list 구조 (effects 목록) + target_count 누락
                        "levels": {
                            "1": [
                                {"time": 0.0, "type": "damage", "damage": 3.0},
                                {"time": 0.5, "type": "damage", "damage": 1.0},
                            ],
                            "2": [
                                {"time": 0.0, "type": "damage", "damage": 4.0},
                            ],
                        },
                    },
                    "custom:한월 RPG:테스트:공격2": {
                        "name": "공격2",
                        "cooltime": 7.0,
                        "target_count": 3,
                        "levels": {
                            "1": [
                                {"time": 0.0, "type": "heal", "heal": 10.0},
                                {"time": 0.5, "type": "damage", "damage": 2.0},
                            ],
                        },
                    },
                },
            },
        },
    }


def test_custom_skills_normalization_sums_damage_effects(
    isolated_data_paths: dict[str, str],
) -> None:
    """list 효과 구조에서 damage 효과만 합산되어 단일 float로 정규화된다"""

    file_path: str = isolated_data_paths["custom_skills_file_dir"]
    _write_json(file_path, _make_legacy_custom_skills_json())

    raw: dict[str, dict] = data_manager.read_custom_skills_data()
    skill_details: dict[str, Any] = raw["한월 RPG"]["skill_details"]

    # 공격1 1레벨: 3.0 + 1.0 = 4.0
    assert skill_details["custom:한월 RPG:테스트:공격1"]["levels"]["1"] == 4.0
    # 공격1 2레벨: 4.0
    assert skill_details["custom:한월 RPG:테스트:공격1"]["levels"]["2"] == 4.0


def test_custom_skills_normalization_drops_heal_and_buff(
    isolated_data_paths: dict[str, str],
) -> None:
    """heal/buff 효과는 정규화 단계에서 제거되어 damage만 살아남는다"""

    file_path: str = isolated_data_paths["custom_skills_file_dir"]
    _write_json(file_path, _make_legacy_custom_skills_json())

    raw: dict[str, dict] = data_manager.read_custom_skills_data()
    skill_details: dict[str, Any] = raw["한월 RPG"]["skill_details"]

    # 공격2 1레벨: heal 10.0은 무시, damage 2.0만 합산
    assert skill_details["custom:한월 RPG:테스트:공격2"]["levels"]["1"] == 2.0


def test_custom_skills_normalization_defaults_target_count(
    isolated_data_paths: dict[str, str],
) -> None:
    """target_count가 없는 이전 데이터는 1로 기본값 채움"""

    file_path: str = isolated_data_paths["custom_skills_file_dir"]
    _write_json(file_path, _make_legacy_custom_skills_json())

    raw: dict[str, dict] = data_manager.read_custom_skills_data()
    skill_details: dict[str, Any] = raw["한월 RPG"]["skill_details"]

    # 공격1은 target_count 없음 → 1
    assert skill_details["custom:한월 RPG:테스트:공격1"]["target_count"] == 1
    # 공격2는 target_count=3 명시 → 3 유지
    assert skill_details["custom:한월 RPG:테스트:공격2"]["target_count"] == 3


def test_custom_skills_normalization_persists_to_disk(
    isolated_data_paths: dict[str, str],
) -> None:
    """정규화 결과가 디스크에 저장되어 다음 읽기에서 동일하게 유지된다"""

    file_path: str = isolated_data_paths["custom_skills_file_dir"]
    _write_json(file_path, _make_legacy_custom_skills_json())

    raw_first: dict[str, dict] = data_manager.read_custom_skills_data()
    raw_second: dict[str, dict] = data_manager.read_custom_skills_data()

    assert raw_first == raw_second


def test_custom_skills_validates_as_import(
    isolated_data_paths: dict[str, str],
) -> None:
    """정규화된 데이터는 CustomSkillImport.from_dict로 검증 가능하다"""

    file_path: str = isolated_data_paths["custom_skills_file_dir"]
    _write_json(file_path, _make_legacy_custom_skills_json())

    raw: dict[str, dict] = data_manager.read_custom_skills_data()
    skill_import: CustomSkillImport = CustomSkillImport.from_dict(raw["한월 RPG"])

    # 스킬 2개 정의 확인
    assert len(skill_import.skills) == 2
    assert len(skill_import.skill_details) == 2


def test_future_macro_data_version_detected(
    isolated_data_paths: dict[str, str],
) -> None:
    """미래 버전 macros.json은 has_future_macro_data_version로 감지된다"""

    file_path: str = isolated_data_paths["file_dir"]
    future_payload: dict[str, Any] = _make_v4_macros_json()
    future_payload["version"] = DATA_VERSION + 1
    _write_json(file_path, future_payload)

    assert data_manager.has_future_macro_data_version() is True


def test_future_custom_skills_data_version_detected(
    isolated_data_paths: dict[str, str],
) -> None:
    """미래 버전 custom_skills.json도 has_future_custom_skills_data_version로 감지된다"""

    file_path: str = isolated_data_paths["custom_skills_file_dir"]
    future_payload: dict[str, Any] = _make_legacy_custom_skills_json()
    future_payload["version"] = CUSTOM_SKILLS_DATA_VERSION + 1
    _write_json(file_path, future_payload)

    assert data_manager.has_future_custom_skills_data_version() is True
