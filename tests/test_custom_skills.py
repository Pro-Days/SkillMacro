from __future__ import annotations

import glob
import json
import os
from typing import Any

import pytest

from app.scripts import data_manager
from app.scripts.custom_skill_models import CustomSkillImport, CustomSkillImportError
from app.scripts.registry.server_registry import server_registry
from app.scripts.registry.skill_registry import SkillDef, SkillHitDef, SkillRegistry

# 테스트 커스텀 스킬/무공비급 ID 상수
SKILL_A_ID: str = "custom:한월 RPG:테스트스킬A"
SKILL_B_ID: str = "custom:한월 RPG:테스트스킬B"
SCROLL_ID: str = "custom:한월 RPG:테스트비급"


def _make_import_payload() -> dict[str, Any]:
    """유효한 커스텀 스킬 저장 페이로드 구성"""

    return {
        "skills": [SKILL_A_ID, SKILL_B_ID],
        "scrolls": [
            {
                "scroll_id": SCROLL_ID,
                "name": "테스트비급",
                "skills": [SKILL_A_ID, SKILL_B_ID],
            }
        ],
        "skill_details": {
            SKILL_A_ID: {
                "name": "테스트스킬A",
                "cooltime": 4.5,
                "target_count": 1,
                "levels": {"1": 2.0, "2": 2.1},
            },
            SKILL_B_ID: {
                "name": "테스트스킬B",
                "cooltime": 6.0,
                "target_count": 3,
                "levels": {"1": 3.0},
            },
        },
    }


def test_valid_import_dict_roundtrip_is_stable() -> None:
    """유효 페이로드의 from_dict -> to_dict 라운드트립 안정성 검증"""

    payload: dict[str, Any] = _make_import_payload()
    skill_import: CustomSkillImport = CustomSkillImport.from_dict(payload)

    assert skill_import.to_dict() == payload


def test_custom_skill_damage_normalizes_to_one_immediate_hit() -> None:
    """커스텀 레벨 계수의 사용 즉시 단일 타격 호환 검증"""

    payload: dict[str, Any] = _make_import_payload()
    skill_import: CustomSkillImport = CustomSkillImport.from_dict(payload)
    skill_def: SkillDef = SkillDef.from_custom_definition(
        server_id="한월 RPG",
        definition=skill_import.skill_details[SKILL_A_ID],
    )

    assert skill_def.levels[1] == 2.0
    assert skill_def.hits_by_level[1] == (
        SkillHitDef(offset_ms=0, multiplier=2.0),
    )


@pytest.mark.parametrize(
    "mutate_key, mutate_value",
    [
        # 스킬 ID 중복 입력
        ("skills", [SKILL_A_ID, SKILL_A_ID]),
        # 공백 스킬 ID 입력
        ("skills", [SKILL_A_ID, "  "]),
        # 선언된 스킬의 상세 데이터 누락
        ("skill_details", {}),
        # 무공비급 스킬 개수 오류
        (
            "scrolls",
            [{"scroll_id": SCROLL_ID, "name": "테스트비급", "skills": [SKILL_A_ID]}],
        ),
        # 무공비급의 미정의 스킬 참조
        (
            "scrolls",
            [
                {
                    "scroll_id": SCROLL_ID,
                    "name": "테스트비급",
                    "skills": [SKILL_A_ID, "custom:한월 RPG:없는스킬"],
                }
            ],
        ),
    ],
)
def test_invalid_import_structure_is_rejected(
    mutate_key: str,
    mutate_value: Any,
) -> None:
    """구조 위반 페이로드의 명시적 거부 검증"""

    payload: dict[str, Any] = _make_import_payload()
    payload[mutate_key] = mutate_value

    with pytest.raises(CustomSkillImportError):
        CustomSkillImport.from_dict(payload)


@pytest.mark.parametrize(
    "detail_key, detail_value",
    [
        # 타겟 수 0 입력
        ("target_count", 0),
        # 타겟 수 문자열 입력
        ("target_count", "2"),
        # 쿨타임 비숫자 입력
        ("cooltime", "abc"),
        # 스킬 이름 공백 입력
        ("name", "   "),
        # 레벨 계수 비숫자 입력
        ("levels", {"1": "abc"}),
    ],
)
def test_invalid_skill_detail_is_rejected(
    detail_key: str,
    detail_value: Any,
) -> None:
    """스킬 상세 필드 위반의 명시적 거부 검증"""

    payload: dict[str, Any] = _make_import_payload()
    payload["skill_details"][SKILL_A_ID][detail_key] = detail_value

    with pytest.raises(CustomSkillImportError):
        CustomSkillImport.from_dict(payload)


def test_undefined_extra_skill_detail_is_rejected() -> None:
    """선언되지 않은 잉여 스킬 상세 데이터 거부 검증"""

    payload: dict[str, Any] = _make_import_payload()
    payload["skill_details"]["custom:한월 RPG:잉여스킬"] = {
        "name": "잉여스킬",
        "cooltime": 1.0,
        "target_count": 1,
        "levels": {},
    }

    with pytest.raises(CustomSkillImportError):
        CustomSkillImport.from_dict(payload)


def test_save_and_read_custom_skills_roundtrip(
    isolated_data_paths: dict[str, str],
) -> None:
    """저장 후 재읽기 시 버전 루트 구조와 내용 보존 검증"""

    payload: dict[str, Any] = _make_import_payload()
    skill_import: CustomSkillImport = CustomSkillImport.from_dict(payload)

    data_manager.save_custom_skills("한월 RPG", skill_import)

    # 저장 파일의 독립 버전 루트 구조 확인
    with open(
        isolated_data_paths["custom_skills_file_dir"], "r", encoding="utf-8"
    ) as f:
        raw: dict[str, Any] = json.load(f)

    assert raw["version"] == data_manager.CUSTOM_SKILLS_DATA_VERSION
    assert "한월 RPG" in raw["servers"]

    # 재읽기 결과의 서버별 데이터 보존 확인
    loaded: dict[str, dict] = data_manager.read_custom_skills_data()
    assert loaded["한월 RPG"] == payload


def test_legacy_format_is_normalized_and_rewritten(
    isolated_data_paths: dict[str, str],
) -> None:
    """버전 루트가 없는 이전 저장 구조의 정규화와 파일 재저장 검증"""

    # 이전 구조: 루트에 서버 데이터 직접 저장 + 레벨 효과 목록 형식 + target_count 부재
    legacy_raw: dict[str, Any] = {
        "한월 RPG": {
            "scrolls": [
                {
                    "scroll_id": SCROLL_ID,
                    "name": "테스트비급",
                    "skills": [SKILL_A_ID, SKILL_B_ID],
                }
            ],
            "skill_details": {
                SKILL_A_ID: {
                    "name": "테스트스킬A",
                    "cooltime": 4.5,
                    "levels": {
                        "1": [
                            {"type": "damage", "damage": 1.5},
                            {"type": "heal", "heal": 10.0},
                            {"type": "damage", "damage": 0.5},
                        ]
                    },
                },
                SKILL_B_ID: {
                    "name": "테스트스킬B",
                    "cooltime": 6.0,
                    "levels": {"1": {"damage": 3.0}},
                },
            },
        }
    }
    with open(
        isolated_data_paths["custom_skills_file_dir"], "w", encoding="utf-8"
    ) as f:
        json.dump(legacy_raw, f, ensure_ascii=False)

    loaded: dict[str, dict] = data_manager.read_custom_skills_data()

    # 데미지 효과 합산 및 힐 효과 제거 확인
    detail_a: dict[str, Any] = loaded["한월 RPG"]["skill_details"][SKILL_A_ID]
    assert detail_a["levels"] == {"1": 2.0}
    assert detail_a["target_count"] == 1

    # 단일 데미지 dict 구조 정규화 확인
    detail_b: dict[str, Any] = loaded["한월 RPG"]["skill_details"][SKILL_B_ID]
    assert detail_b["levels"] == {"1": 3.0}

    # 무공비급 참조 기반 스킬 목록 재구성 확인
    assert loaded["한월 RPG"]["skills"] == [SKILL_A_ID, SKILL_B_ID]

    # 정규화 결과의 새 버전 루트 구조 재저장 확인
    with open(
        isolated_data_paths["custom_skills_file_dir"], "r", encoding="utf-8"
    ) as f:
        rewritten: dict[str, Any] = json.load(f)

    assert rewritten["version"] == data_manager.CUSTOM_SKILLS_DATA_VERSION
    assert "한월 RPG" in rewritten["servers"]


def test_corrupted_custom_skills_file_is_backed_up_and_reset(
    isolated_data_paths: dict[str, str],
) -> None:
    """손상 custom_skills.json 백업 후 빈 기본 파일 재생성 검증"""

    file_dir: str = isolated_data_paths["custom_skills_file_dir"]
    corrupted_text: str = "{invalid json{{{"
    os.makedirs(isolated_data_paths["data_path"], exist_ok=True)
    with open(file_dir, "w", encoding="utf-8") as f:
        f.write(corrupted_text)

    loaded: dict[str, dict] = data_manager.read_custom_skills_data()

    # 손상 파일은 빈 데이터로 복구
    assert loaded == {}

    # 원본 손상 데이터의 타임스탬프 백업 생성과 내용 보존 확인
    backup_paths: list[str] = glob.glob(
        os.path.join(
            isolated_data_paths["data_path"],
            "custom_skills.backup-*.json",
        )
    )
    assert len(backup_paths) == 1
    with open(backup_paths[0], "r", encoding="utf-8") as f:
        assert f.read() == corrupted_text

    # 빈 기본 파일 재생성 확인
    with open(file_dir, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)

    assert raw == {
        "version": data_manager.CUSTOM_SKILLS_DATA_VERSION,
        "servers": {},
    }


def test_remove_custom_scroll_updates_registry_and_file(
    isolated_data_paths: dict[str, str],
) -> None:
    server_id: str = "한월 RPG"
    skill_import: CustomSkillImport = CustomSkillImport.from_dict(
        _make_import_payload()
    )
    data_manager.save_custom_skills(server_id, skill_import)
    data_manager.load_custom_skills()
    registry: SkillRegistry = server_registry.get(server_id).skill_registry
    assert SCROLL_ID in registry.get_all_scroll_ids()

    data_manager.remove_custom_scroll(server_id, SCROLL_ID)

    assert SCROLL_ID not in registry.get_all_scroll_ids()
    assert SKILL_A_ID not in registry.get_all_skill_ids()
    assert SKILL_B_ID not in registry.get_all_skill_ids()
    saved: dict[str, dict] = data_manager.read_custom_skills_data()
    assert saved[server_id] == {
        "skills": [],
        "scrolls": [],
        "skill_details": {},
    }
