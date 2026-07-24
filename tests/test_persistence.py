from __future__ import annotations

import glob
import json
import os
from collections.abc import Iterator
from typing import Any

import pytest

from app.scripts import data_manager
from app.scripts.app_state import app_state
from app.scripts.character_models import (
    CHARACTER_DATA_VERSION,
    CharacterProfile,
    CharacterStore,
)
from app.scripts.calculator_models import (
    CalculatorPresetInput,
    CustomPowerFormula,
    DanjeonState,
    DistributionState,
    OptimizationCandidateGroup,
    OptimizationCandidateOption,
    OptimizationCandidateStat,
    RealmTier,
    StatKey,
    TargetDanjeonState,
    TargetDistributionState,
)
from app.scripts.macro_models import (
    DATA_VERSION,
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    MacroPreset,
    MacroPresetFile,
    MacroPresetRepository,
    SkillUsageSetting,
    ThemeMode,
)
from app.scripts.registry.server_registry import ServerSpec, server_registry
from tests.conftest import make_calculator_input, make_realistic_base_stats


def _write_text(file_path: str, text: str) -> None:
    """저장 경로에 원시 텍스트 기록"""

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)


def _list_backups(data_path: str, stem: str) -> list[str]:
    """지정 파일의 타임스탬프 백업 목록 조회"""

    return glob.glob(os.path.join(data_path, f"{stem}.backup-*.json"))


def test_future_macro_version_is_detected(isolated_data_paths: dict[str, str]) -> None:
    """현재 프로그램보다 높은 저장 버전 감지 검증"""

    # 미래 버전 루트만 가진 최소 파일 구성
    _write_text(
        isolated_data_paths["file_dir"],
        json.dumps({"version": DATA_VERSION + 1}),
    )

    assert data_manager.has_future_macro_data_version() is True


def test_current_or_invalid_version_is_not_future(
    isolated_data_paths: dict[str, str],
) -> None:
    """현재 버전/비정수 버전/손상 파일/파일 부재의 미래 버전 비감지 검증"""

    file_dir: str = isolated_data_paths["file_dir"]

    # 파일 부재 상태 확인
    assert data_manager.has_future_macro_data_version() is False

    # 현재 버전 파일 확인
    _write_text(file_dir, json.dumps({"version": DATA_VERSION}))
    assert data_manager.has_future_macro_data_version() is False

    # 비정수 버전 파일 확인
    _write_text(file_dir, json.dumps({"version": "999"}))
    assert data_manager.has_future_macro_data_version() is False

    # 손상 JSON 파일 확인
    _write_text(file_dir, "{invalid json")
    assert data_manager.has_future_macro_data_version() is False


def test_backup_data_file_moves_original(
    isolated_data_paths: dict[str, str],
) -> None:
    """손상 파일 백업 이동과 알림 대기 상태 반영 검증"""

    file_dir: str = isolated_data_paths["file_dir"]
    original_text: str = json.dumps({"version": 1})
    _write_text(file_dir, original_text)

    backup_path: str | None = data_manager.backup_data_file(file_dir)

    # 원본 제거 및 백업 파일 내용 보존 확인
    assert backup_path is not None
    assert not os.path.isfile(file_dir)
    with open(backup_path, "r", encoding="utf-8") as f:
        assert f.read() == original_text

    # UI 초기화 이후 표시할 백업 알림 대기 상태 확인
    assert app_state.ui.has_pending_backup_notice is True


def test_backup_data_file_returns_none_for_missing_file(
    isolated_data_paths: dict[str, str],
) -> None:
    """백업 대상 파일 부재 시 백업 생략 검증"""

    assert data_manager.backup_data_file(isolated_data_paths["file_dir"]) is None


def test_update_data_recovers_corrupted_file(
    isolated_data_paths: dict[str, str],
) -> None:
    """손상 macros.json 백업 후 기본 데이터 재생성 검증"""

    file_dir: str = isolated_data_paths["file_dir"]
    _write_text(file_dir, "{invalid json{{{")

    data_manager.update_data()

    # 손상 원본의 타임스탬프 백업 생성 확인
    assert len(_list_backups(isolated_data_paths["data_path"], "macros")) == 1

    # 재생성된 기본 파일 로드 가능 여부와 기본 프리셋 구성 확인
    preset_file: MacroPresetFile = MacroPresetRepository(file_dir).load()
    assert preset_file.version == DATA_VERSION
    assert len(preset_file.preset) == 1
    assert preset_file.preset[0].settings.server_id == "한월 RPG"


def test_update_data_recovers_empty_preset_list(
    isolated_data_paths: dict[str, str],
) -> None:
    """프리셋 목록이 빈 파일의 백업 후 기본 데이터 재생성 검증"""

    file_dir: str = isolated_data_paths["file_dir"]

    # 구조는 유효하지만 프리셋이 비어 있는 파일 구성
    empty_file: MacroPresetFile = MacroPresetFile(preset=[])
    _write_text(file_dir, json.dumps(empty_file.to_dict(), ensure_ascii=False))

    data_manager.update_data()

    assert len(_list_backups(isolated_data_paths["data_path"], "macros")) == 1

    preset_file: MacroPresetFile = MacroPresetRepository(file_dir).load()
    assert len(preset_file.preset) == 1


def test_update_data_recovers_out_of_range_recent_preset(
    isolated_data_paths: dict[str, str],
) -> None:
    """범위를 벗어난 최근 프리셋 번호 복구 검증"""

    file_dir: str = isolated_data_paths["file_dir"]

    # 프리셋 1개에 recent_preset이 5인 비정상 파일 구성
    broken_file: MacroPresetFile = MacroPresetFile(
        recent_preset=5,
        preset=[data_manager.get_default_preset()],
    )
    _write_text(file_dir, json.dumps(broken_file.to_dict(), ensure_ascii=False))

    data_manager.update_data()

    assert len(_list_backups(isolated_data_paths["data_path"], "macros")) == 1

    preset_file: MacroPresetFile = MacroPresetRepository(file_dir).load()
    assert preset_file.recent_preset == 0


def test_load_data_first_run_creates_default_state(
    isolated_data_paths: dict[str, str],
) -> None:
    """최초 실행 시 기본 데이터 파일 생성과 메모리 반영 검증"""

    data_manager.load_data()

    # 기본 데이터 파일 최초 생성 확인 (custom_skills.json은 커스텀 스킬 저장 시점에 생성)
    assert os.path.isfile(isolated_data_paths["file_dir"])
    assert os.path.isfile(isolated_data_paths["characters_file_dir"])

    # 기본 프리셋 1개와 초기 UI 상태 반영 확인
    assert len(app_state.macro.presets) == 1
    assert app_state.macro.current_preset_index == 0
    assert app_state.ui.theme_mode == ThemeMode.SYSTEM


def test_save_then_load_preserves_state(
    isolated_data_paths: dict[str, str],
) -> None:
    """저장 후 재로드 시 프리셋/테마/공식 상태 보존 검증"""

    from app.scripts.calculator_models import CustomPowerFormula

    data_manager.load_data()

    # 사용자 변경 사항 반영
    app_state.ui.theme_mode = ThemeMode.DARK
    app_state.macro.presets[0].name = "보스용 세팅"
    app_state.macro.custom_power_formulas.append(
        CustomPowerFormula(name="내 공식", formula="boss_damage")
    )
    data_manager.save_data()

    # 메모리 상태를 비운 뒤 파일에서 재로드
    app_state.macro.presets = []
    app_state.macro.custom_power_formulas = []
    app_state.ui.theme_mode = ThemeMode.SYSTEM
    data_manager.load_data()

    assert app_state.ui.theme_mode == ThemeMode.DARK
    assert app_state.macro.presets[0].name == "보스용 세팅"
    assert len(app_state.macro.custom_power_formulas) == 1
    assert app_state.macro.custom_power_formulas[0].name == "내 공식"


def test_future_character_version_is_detected(
    isolated_data_paths: dict[str, str],
) -> None:
    """현재 프로그램보다 높은 캐릭터 저장 버전 감지 검증"""

    _write_text(
        isolated_data_paths["characters_file_dir"],
        json.dumps({"version": CHARACTER_DATA_VERSION + 1}),
    )

    assert data_manager.has_future_character_data_version() is True


def test_save_then_load_characters_preserves_state(
    isolated_data_paths: dict[str, str],
) -> None:
    """캐릭터 저장 후 재로드 시 전체 저장소 상태 보존 검증"""

    store: CharacterStore = CharacterStore.create_default()
    store.characters[0].name = "첫 번째 캐릭터"
    store.characters[0].level = 120
    second_character: CharacterProfile = CharacterStore.create_default().characters[0]
    second_character.name = "두 번째 캐릭터"
    second_character.level = 80
    store.characters.append(second_character)
    store.selected_index = 1
    app_state.character_store = store

    data_manager.save_characters()

    app_state.character_store = CharacterStore.create_default()
    loaded: CharacterStore = data_manager.load_characters()

    assert loaded is app_state.character_store
    assert loaded.version == CHARACTER_DATA_VERSION
    assert loaded.selected_index == 1
    assert [character.name for character in loaded.characters] == [
        "첫 번째 캐릭터",
        "두 번째 캐릭터",
    ]
    assert [character.level for character in loaded.characters] == [120, 80]
    assert os.path.isfile(isolated_data_paths["characters_file_dir"])


def test_load_characters_recovers_corrupted_file(
    isolated_data_paths: dict[str, str],
) -> None:
    """손상 characters.json 백업 후 기본 캐릭터 복구 검증"""

    file_dir: str = isolated_data_paths["characters_file_dir"]
    corrupted_text: str = "{invalid character json{{{"
    _write_text(file_dir, corrupted_text)

    loaded: CharacterStore = data_manager.load_characters()

    backups: list[str] = _list_backups(
        isolated_data_paths["data_path"],
        "characters",
    )
    assert len(backups) == 1
    with open(backups[0], "r", encoding="utf-8") as f:
        assert f.read() == corrupted_text

    assert loaded.version == CHARACTER_DATA_VERSION
    assert len(loaded.characters) == 1
    assert loaded.characters[0].name == "새 캐릭터"
    assert loaded.selected_index == 0
    assert loaded is app_state.character_store
    assert app_state.ui.has_pending_backup_notice is True

    with open(file_dir, "r", encoding="utf-8") as f:
        rewritten: dict[str, Any] = json.load(f)
    rewritten_store: CharacterStore = CharacterStore.from_dict(rewritten)
    assert rewritten_store.version == loaded.version
    assert rewritten_store.selected_index == loaded.selected_index
    assert [character.name for character in rewritten_store.characters] == [
        character.name for character in loaded.characters
    ]


def test_load_characters_recovers_invalid_store(
    isolated_data_paths: dict[str, str],
) -> None:
    """구조는 유효하지만 invariant를 위반한 캐릭터 저장소 복구 검증"""

    invalid_store: CharacterStore = CharacterStore(characters=[], selected_index=0)
    _write_text(
        isolated_data_paths["characters_file_dir"],
        json.dumps(invalid_store.to_dict(), ensure_ascii=False),
    )

    loaded: CharacterStore = data_manager.load_characters()

    assert len(_list_backups(isolated_data_paths["data_path"], "characters")) == 1
    assert len(loaded.characters) == 1
    assert loaded.selected_index == 0


def test_save_characters_rejects_invalid_store_without_overwriting(
    isolated_data_paths: dict[str, str],
) -> None:
    """잘못된 캐릭터 상태 저장 거부와 기존 파일 보존 검증"""

    file_dir: str = isolated_data_paths["characters_file_dir"]
    original_store: CharacterStore = CharacterStore.create_default()
    original_store.characters[0].name = "보존 대상"
    app_state.character_store = original_store
    data_manager.save_characters()

    with open(file_dir, "r", encoding="utf-8") as f:
        original_text: str = f.read()

    app_state.character_store = CharacterStore(characters=[], selected_index=0)
    with pytest.raises(ValueError):
        data_manager.save_characters()

    with open(file_dir, "r", encoding="utf-8") as f:
        assert f.read() == original_text


def _make_candidate_group() -> OptimizationCandidateGroup:
    return OptimizationCandidateGroup(
        name="칭호",
        selection_count=1,
        candidates=[
            OptimizationCandidateOption(
                name="공격 후보",
                stats=[
                    OptimizationCandidateStat(stat_key=StatKey.ATTACK, value=100.0)
                ],
            ),
            OptimizationCandidateOption(
                name="보스 후보",
                stats=[
                    OptimizationCandidateStat(
                        stat_key=StatKey.BOSS_ATTACK_PERCENT,
                        value=5.0,
                    )
                ],
            ),
        ],
    )


def _customize_preset(preset: MacroPreset, server_spec: ServerSpec) -> MacroPreset:
    skill_ids: list[str] = server_spec.skill_registry.get_all_skill_ids()
    scroll_id: str = server_spec.skill_registry.get_all_scroll_ids()[0]
    preset.usage_settings[skill_ids[0]] = SkillUsageSetting(
        use_skill=False,
        use_alone=True,
        priority=3,
    )
    preset.link_skills.append(
        LinkSkill(
            use_type=LinkUseType.AUTO,
            key_type=LinkKeyType.ON,
            key="q",
            skills=[skill_ids[0], skill_ids[2]],
            remember_state=True,
        )
    )
    preset.info.scroll_levels[scroll_id] = 5
    preset.settings.custom_delay = 450
    preset.settings.use_custom_delay = True
    return preset


def test_macro_preset_serialization_roundtrip(
    synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    preset: MacroPreset = _customize_preset(full_preset, synthetic_server)
    payload: dict[str, Any] = preset.to_dict()

    assert MacroPreset.from_dict(payload).to_dict() == payload

    preset_file: MacroPresetFile = MacroPresetFile(
        version=DATA_VERSION,
        theme_mode=ThemeMode.DARK,
        guide_prompt_handled=True,
        last_app_version="v1.0.9",
        custom_power_formulas=[
            CustomPowerFormula(name="테스트 공식", formula="boss_damage * 2")
        ],
        preset=[preset],
    )
    file_payload: dict[str, Any] = preset_file.to_dict()
    assert MacroPresetFile.from_dict(file_payload).to_dict() == file_payload


def test_calculator_and_character_serialization_roundtrip() -> None:
    calculator_input: CalculatorPresetInput = make_calculator_input(
        level=150,
        realm_tier=RealmTier.PEAK,
        distribution=DistributionState(
            strength=100,
            dexterity=50,
            vitality=30,
            luck=20,
            is_locked=True,
        ),
        danjeon=DanjeonState(upper=10, middle=20, lower=30, use_reset=True),
        base_stats=make_realistic_base_stats(),
    )
    calculator_input.target_distribution = TargetDistributionState(
        strength=120,
        dexterity=60,
        vitality=10,
        luck=10,
        is_minimum=True,
    )
    calculator_input.target_danjeon = TargetDanjeonState(
        upper=15,
        middle=25,
        lower=20,
        is_minimum=True,
    )
    calculator_input.candidate_groups = [_make_candidate_group()]
    calculator_input.custom_stat_changes[StatKey.ATTACK.value] = 100.0
    calculator_payload: dict[str, Any] = calculator_input.to_dict()
    restored_calculator: CalculatorPresetInput = CalculatorPresetInput.from_dict(
        calculator_payload
    )
    assert restored_calculator.to_dict() == calculator_payload

    store: CharacterStore = CharacterStore.create_default()
    store.characters[0].name = "테스트 캐릭터"
    store.characters[0].level = 120
    store.characters[0].realm = RealmTier.PEAK
    store.characters[0].distribution.strength = 200
    store_payload: dict[str, Any] = store.to_dict()
    assert CharacterStore.from_dict(store_payload).to_dict() == store_payload


@pytest.mark.parametrize(
    ("payload", "expected_exception"),
    [
        (
            {"name": "칭호", "selection_count": 0, "candidates": []},
            ValueError,
        ),
        (
            {"name": "칭호", "selection_count": 1, "candidates": {}},
            TypeError,
        ),
    ],
)
def test_candidate_group_rejects_invalid_payload(
    payload: dict[str, Any],
    expected_exception: type[Exception],
) -> None:
    with pytest.raises(expected_exception):
        OptimizationCandidateGroup.from_dict(payload)


@pytest.fixture
def registered_synthetic_server(synthetic_server: ServerSpec) -> Iterator[ServerSpec]:
    server_registry._SERVERS[synthetic_server.id] = synthetic_server
    yield synthetic_server
    server_registry._SERVERS.pop(synthetic_server.id, None)


def test_sanitize_removes_stale_registry_references(
    registered_synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    stale_scroll_id: str = "custom:test_server:삭제된비급"
    stale_skill_id: str = "custom:test_server:삭제된스킬"
    valid_skill_id: str = full_preset.skills.placed_skills[2]
    full_preset.skills.equipped_scrolls[0] = stale_scroll_id
    full_preset.skills.placed_skills[0] = stale_skill_id
    full_preset.info.scroll_levels[stale_scroll_id] = 9
    full_preset.usage_settings[stale_skill_id] = SkillUsageSetting(priority=2)
    partially_valid_link: LinkSkill = LinkSkill(
        use_type=LinkUseType.AUTO,
        key_type=LinkKeyType.ON,
        key="q",
        skills=[valid_skill_id, stale_skill_id],
        remember_state=True,
    )
    full_preset.link_skills = [
        partially_valid_link,
        LinkSkill(skills=[stale_skill_id]),
    ]

    assert data_manager.sanitize_preset_registry_references(full_preset) is True
    assert full_preset.skills.equipped_scrolls[0] == ""
    assert full_preset.skills.placed_skills[0] == ""
    assert stale_scroll_id not in full_preset.info.scroll_levels
    assert stale_skill_id not in full_preset.usage_settings
    assert full_preset.link_skills == [partially_valid_link]
    assert partially_valid_link.skills == [valid_skill_id]
    assert partially_valid_link.use_type == LinkUseType.MANUAL
    assert partially_valid_link.key is None
    assert partially_valid_link.remember_state is True


def test_sanitize_leaves_valid_preset_unchanged(
    registered_synthetic_server: ServerSpec,
    full_preset: MacroPreset,
) -> None:
    original: dict[str, Any] = full_preset.to_dict()

    assert data_manager.sanitize_preset_registry_references(full_preset) is False
    assert full_preset.to_dict() == original


def test_load_data_persists_sanitized_registry_references(
    registered_synthetic_server: ServerSpec,
    full_preset: MacroPreset,
    isolated_data_paths: dict[str, str],
) -> None:
    stale_scroll_id: str = "custom:test_server:사라진비급"
    stale_skill_id: str = "custom:test_server:사라진스킬"
    full_preset.skills.equipped_scrolls[1] = stale_scroll_id
    full_preset.skills.placed_skills[2] = stale_skill_id
    full_preset.info.scroll_levels[stale_scroll_id] = 5
    full_preset.usage_settings[stale_skill_id] = SkillUsageSetting(use_alone=True)
    repository: MacroPresetRepository = MacroPresetRepository(
        isolated_data_paths["file_dir"]
    )
    repository.save(MacroPresetFile(preset=[full_preset]))

    data_manager.load_data()

    for preset in (app_state.macro.presets[0], repository.load().preset[0]):
        assert preset.skills.equipped_scrolls[1] == ""
        assert preset.skills.placed_skills[2] == ""
        assert stale_scroll_id not in preset.info.scroll_levels
        assert stale_skill_id not in preset.usage_settings


def test_preset_lifecycle_persists_independent_copies(
    isolated_data_paths: dict[str, str],
) -> None:
    data_manager.load_data()
    source: MacroPreset = app_state.macro.presets[0]
    source.name = "원본"
    server: ServerSpec = app_state.macro.current_server
    scroll_id: str = server.skill_registry.get_all_scroll_ids()[0]
    skill_id: str = server.skill_registry.get_scroll(scroll_id).skills[0]
    source.skills.equipped_scrolls[0] = scroll_id
    source.skills.placed_skills[0] = skill_id
    link_skill: LinkSkill = LinkSkill(skills=[skill_id])
    link_skill.skill_timers[skill_id] = 123.0
    source.link_skills.append(link_skill)

    data_manager.copy_preset(0)

    copied: MacroPreset = app_state.macro.presets[1]
    assert copied is not source
    assert copied.to_dict() == source.to_dict()
    assert copied.link_skills[0].skill_timers == {}
    copied.name = "복사본"
    copied.link_skills[0].skills.clear()
    assert source.name == "원본"
    assert source.link_skills[0].skills != []

    data_manager.add_preset()
    assert len(app_state.macro.presets) == 3
    data_manager.remove_preset(2)
    assert len(app_state.macro.presets) == 2
    persisted: MacroPresetFile = MacroPresetRepository(
        isolated_data_paths["file_dir"]
    ).load()
    assert [preset.name for preset in persisted.preset] == ["원본", "복사본"]
