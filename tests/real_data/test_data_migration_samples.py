from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from app.scripts.calculator_models import (
    CalculatorPresetInput,
    RealmTier,
    RefinementEquipment,
    RefinementInput,
    RefinementStrategyMode,
    StatKey,
)
from app.scripts.data_manager import migrate_macro_data_file
from app.scripts.macro_models import (
    DATA_VERSION,
    LinkUseType,
    MacroPreset,
    MacroPresetFile,
    MacroPresetRepository,
    ThemeMode,
)

# 버전별 릴리스 저장 구조 샘플 디렉터리
SAMPLE_DIR: Path = Path(__file__).resolve().parents[1] / "data"

# 풀 장착 프리셋 참조 ID (실제 한월 RPG 데이터 기준)
FULL_SCROLL_IDS: tuple[str, ...] = (
    "builtin:한월 RPG:마혼검결",
    "builtin:한월 RPG:매화중검",
    "builtin:한월 RPG:부화검결",
    "builtin:한월 RPG:빙천검법",
    "builtin:한월 RPG:사혼검결",
    "builtin:한월 RPG:섬멸검법",
    "builtin:한월 RPG:수류검법",
)
PRIORITY_SKILL_ID: str = "builtin:한월 RPG:귀섬보"
DISABLED_SKILL_ID: str = "builtin:한월 RPG:폭부검"

# 단순 프리셋 참조 ID
SIMPLE_SCROLL_ID: str = "builtin:한월 RPG:수류검법"
SIMPLE_SKILL_A_ID: str = "builtin:한월 RPG:수류참"


def _sample_path(version: int) -> Path:
    """버전별 macros.json 샘플 경로 조회"""

    return SAMPLE_DIR / f"macros_v{version}.json"


def _read_json(path: str) -> Any:
    """JSON 파일 로드"""

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _migrate_sample(version: int, isolated_data_paths: dict[str, str]) -> str:
    """버전 샘플을 격리 경로에 복사 후 마이그레이션 수행"""

    file_dir: str = isolated_data_paths["file_dir"]
    os.makedirs(isolated_data_paths["data_path"], exist_ok=True)
    shutil.copyfile(_sample_path(version), file_dir)

    migrate_macro_data_file(file_dir)
    return file_dir


@pytest.mark.parametrize("version", range(1, DATA_VERSION + 1))
def test_every_released_version_has_sample_file(version: int) -> None:
    """DATA_VERSION까지 모든 버전 샘플 존재 검증

    DATA_VERSION을 올리면 tests/data/macros_v{N}.json 샘플과
    마이그레이션 코드를 함께 추가해야 이 테스트가 통과한다.
    """

    assert _sample_path(version).is_file(), (
        f"macros_v{version}.json 샘플이 없습니다. "
        "새 저장 버전을 추가했다면 해당 버전의 저장 구조 샘플을 tests/data에 추가하세요."
    )


@pytest.mark.parametrize("version", range(1, DATA_VERSION + 1))
def test_sample_migrates_to_current_version(
    version: int,
    isolated_data_paths: dict[str, str],
) -> None:
    """버전별 샘플의 현재 버전 승격과 로드 검증"""

    file_dir: str = _migrate_sample(version, isolated_data_paths)

    # 루트 버전 승격 확인
    migrated: dict[str, Any] = _read_json(file_dir)
    assert migrated["version"] == DATA_VERSION

    # 현재 모델 로드 가능 여부 확인
    preset_file: MacroPresetFile = MacroPresetRepository(file_dir).load()
    assert len(preset_file.preset) == 2


@pytest.mark.parametrize("version", range(1, DATA_VERSION + 1))
def test_migration_preserves_user_content(
    version: int,
    isolated_data_paths: dict[str, str],
) -> None:
    """마이그레이션 전후 사용자 설정 의미 보존 검증"""

    file_dir: str = _migrate_sample(version, isolated_data_paths)
    preset_file: MacroPresetFile = MacroPresetRepository(file_dir).load()

    # 루트 상태 보존 확인 (v1은 테마 필드가 없어 기본값 주입)
    assert preset_file.recent_preset == 1
    expected_theme: ThemeMode = ThemeMode.SYSTEM if version == 1 else ThemeMode.DARK
    assert preset_file.theme_mode == expected_theme

    # 첫 가이드 안내 상태 보존/주입 확인 (v6부터 저장)
    assert preset_file.guide_prompt_handled is (version >= 6)

    # 마지막 실행 버전 보존/주입 확인 (v7부터 저장)
    expected_last_app_version: str = "v1.0.9" if version >= 7 else ""
    assert preset_file.last_app_version == expected_last_app_version

    # 사용자 정의 공식 보존 확인 (v3부터 저장)
    if version >= 3:
        assert len(preset_file.custom_power_formulas) == 1
        assert preset_file.custom_power_formulas[0].formula == "boss_damage * 2"
    else:
        assert preset_file.custom_power_formulas == []

    full_preset: MacroPreset = preset_file.preset[0]
    simple_preset: MacroPreset = preset_file.preset[1]
    assert full_preset.name == "풀 장착 프리셋"
    assert simple_preset.name == "단순 프리셋"

    # 풀 장착 프리셋 장착/배치 보존 확인
    assert tuple(full_preset.skills.equipped_scrolls) == FULL_SCROLL_IDS
    assert full_preset.skills.placed_skills[0] == PRIORITY_SKILL_ID
    assert len(full_preset.skills.get_placed_skill_ids()) == 14

    # 비기본 매크로 설정 보존 확인
    assert full_preset.settings.custom_delay == 450
    assert full_preset.settings.use_custom_delay is True
    assert full_preset.settings.custom_cooltime_reduction == 30
    assert full_preset.settings.custom_start_key == "f5"
    assert full_preset.settings.use_custom_start_key is True
    assert full_preset.settings.custom_swap_key == "g"
    assert full_preset.settings.use_default_attack is True

    # v8 신규 쿨타임 추가 대기 설정 보존/주입 확인
    expected_extra_wait: int = 350 if version >= 8 else 200
    assert full_preset.settings.custom_cooltime_extra_wait == expected_extra_wait
    assert full_preset.settings.use_custom_cooltime_extra_wait is (version >= 8)

    # v5 신규 설정 보존/주입 확인
    if version >= 5:
        assert full_preset.settings.custom_key_hold_seconds == 0.5
        assert full_preset.settings.use_custom_key_hold_seconds is True
        assert full_preset.settings.remember_previous_state is True
        assert full_preset.settings.always_return_to_first_line is True
    else:
        assert full_preset.settings.use_custom_key_hold_seconds is False
        assert full_preset.settings.remember_previous_state is False

    # 스킬 사용설정 보존 확인 (단독 스왑 제거 후에도 우선순위/단독 사용 유지)
    assert full_preset.usage_settings[PRIORITY_SKILL_ID].priority == 1
    assert full_preset.usage_settings[PRIORITY_SKILL_ID].use_alone is True
    assert full_preset.usage_settings[DISABLED_SKILL_ID].use_skill is False

    # 연계스킬 보존 확인 (자동 + 단축키 유지)
    assert len(full_preset.link_skills) == 2
    auto_link = full_preset.link_skills[0]
    assert auto_link.use_type == LinkUseType.AUTO
    assert auto_link.key == "q"
    assert auto_link.skills[0] == PRIORITY_SKILL_ID

    # 연계 쿨타임 동기화 보존/주입 확인 (v5부터 저장)
    assert auto_link.remember_state is (version >= 5)

    # 무공비급 레벨 보존 확인
    assert full_preset.info.scroll_levels[FULL_SCROLL_IDS[0]] == 15
    assert full_preset.info.scroll_levels[FULL_SCROLL_IDS[1]] == 5
    assert full_preset.info.scroll_levels[FULL_SCROLL_IDS[2]] == 3

    # 계산기 입력 보존 확인
    calculator: CalculatorPresetInput = full_preset.info.calculator
    assert calculator.level == 100
    assert calculator.realm_tier == RealmTier.PEAK
    assert calculator.selected_formula_id == "boss_damage"
    assert calculator.base_stats.values[StatKey.ATTACK.value] == 5000.0
    assert calculator.base_stats.values[StatKey.CRIT_DAMAGE_PERCENT.value] == 180.0

    # 분배/단전 상태 보존 확인 (잠금/초기화 플래그 포함)
    assert calculator.distribution.strength == 100
    assert calculator.distribution.dexterity == 50
    assert calculator.distribution.is_locked is True
    assert calculator.danjeon.upper == 3
    assert calculator.danjeon.middle == 5
    assert calculator.danjeon.lower == 2
    assert calculator.danjeon.use_reset is True

    # 사용자 지정 스탯 변화량 보존 확인
    assert calculator.custom_stat_changes[StatKey.ATTACK.value] == 100.0
    assert calculator.custom_stat_changes[StatKey.SKILL_DAMAGE_PERCENT.value] == 5.0

    # 목표 분배 보존/주입 확인 (v3 이하 파일은 필드 부재 -> 기본값 주입)
    if version >= 4:
        assert calculator.target_distribution.strength == 120
        assert calculator.target_distribution.is_minimum is True
    else:
        assert calculator.target_distribution.strength == 0
        assert calculator.target_distribution.is_minimum is False

    # 목표 단전 보존/주입 확인 (v6부터 저장)
    if version >= 6:
        assert calculator.target_danjeon.upper == 1
        assert calculator.target_danjeon.middle == 2
        assert calculator.target_danjeon.is_minimum is True
    else:
        assert calculator.target_danjeon.upper == 0
        assert calculator.target_danjeon.is_minimum is False

    # 재련 입력 보존/주입 확인 (v9부터 저장)
    refinement: RefinementInput = calculator.refinement
    if version >= 9:
        assert refinement.equipment == RefinementEquipment.HELMET
        assert refinement.level_cap == 110
        assert refinement.start_step == 5
        assert refinement.target_step == 16
        assert refinement.budget == 12000000.0
        assert refinement.use_refine_pet is True
        assert refinement.use_vip is True
        assert refinement.point_bundle_price == 250000.0
        assert refinement.strategy_mode == RefinementStrategyMode.USER
        assert refinement.selected_strategy_id == "sample-strategy-1"
        assert refinement.actual_cost == 8500000.0

        assert len(preset_file.refinement_strategies) == 1
        assert preset_file.refinement_strategies[0].name == "안전 재련"
        assert preset_file.refinement_strategies[0].assist3_step == 4
        assert preset_file.refinement_strategies[0].assist7_step == 12
    else:
        assert refinement.equipment == RefinementEquipment.WEAPON
        assert refinement.level_cap == 180
        assert refinement.start_step == 0
        assert refinement.target_step == 20
        assert refinement.strategy_mode == RefinementStrategyMode.AUTO
        assert preset_file.refinement_strategies == []

    # 후보 그룹 보존/주입 확인 (v7부터 저장, v6 이하 칭호/부적 입력은 빈 그룹으로 대체)
    if version >= 7:
        assert len(calculator.candidate_groups) == 1
        assert calculator.candidate_groups[0].name == "칭호"
        assert len(calculator.candidate_groups[0].candidates) == 2
    else:
        assert calculator.candidate_groups == []

    # 단순 프리셋 보존 확인
    assert simple_preset.skills.equipped_scrolls[0] == SIMPLE_SCROLL_ID
    assert simple_preset.skills.placed_skills[0] == SIMPLE_SKILL_A_ID
    assert simple_preset.info.scroll_levels[SIMPLE_SCROLL_ID] == 5
    assert simple_preset.info.calculator.level == 50


@pytest.mark.parametrize("version", range(1, 4))
def test_legacy_metric_converts_to_boss_damage(
    version: int,
    isolated_data_paths: dict[str, str],
) -> None:
    """v1~v3의 보스/일반 선택값이 모두 boss_damage로 전환되는지 검증"""

    file_dir: str = _migrate_sample(version, isolated_data_paths)

    # 풀 장착(boss)과 단순(normal) 두 변환 경로 모두 확인
    migrated: dict[str, Any] = _read_json(file_dir)
    for raw_preset in migrated["preset"]:
        calculator: dict[str, Any] = raw_preset["info"]["calculator"]
        assert calculator["selected_formula_id"] == "boss_damage"


def test_v6_migration_replaces_owned_inputs_with_candidate_groups(
    isolated_data_paths: dict[str, str],
) -> None:
    """v6 -> v7 전환 시 칭호/부적 입력의 후보 그룹 구조 대체 검증

    v6 샘플의 칭호/부적 입력에는 실제 내용이 들어 있으며,
    내용이 있는 상태에서도 전환이 안전하게 수행되어야 한다.
    """

    # 전환 전 샘플의 칭호/부적 입력 내용 존재 선행 확인
    original: dict[str, Any] = _read_json(str(_sample_path(6)))
    original_calculator: dict[str, Any] = original["preset"][0]["info"]["calculator"]
    assert len(original_calculator["owned_titles"]) == 1
    assert len(original_calculator["owned_talismans"]) == 2
    assert original_calculator["equipped_state"]["equipped_title_name"] == "원양어선"

    file_dir: str = _migrate_sample(6, isolated_data_paths)
    migrated: dict[str, Any] = _read_json(file_dir)

    for raw_preset in migrated["preset"]:
        calculator: dict[str, Any] = raw_preset["info"]["calculator"]

        # 제거 대상 구버전 입력 필드 부재 확인
        assert "owned_titles" not in calculator
        assert "owned_talismans" not in calculator
        assert "equipped_state" not in calculator

        # 신규 후보 그룹 필드 주입 확인
        assert calculator["candidate_groups"] == []


def test_current_version_sample_is_not_modified(
    isolated_data_paths: dict[str, str],
) -> None:
    """현재 버전 샘플의 마이그레이션 무변경 검증"""

    file_dir: str = isolated_data_paths["file_dir"]
    os.makedirs(isolated_data_paths["data_path"], exist_ok=True)
    shutil.copyfile(_sample_path(DATA_VERSION), file_dir)

    original: dict[str, Any] = _read_json(file_dir)
    migrate_macro_data_file(file_dir)

    assert _read_json(file_dir) == original
