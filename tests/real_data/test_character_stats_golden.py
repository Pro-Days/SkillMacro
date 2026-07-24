from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.scripts.character_engine import LiveStatView, compute_live_view
from app.scripts.character_models import CharacterProfile

# 골든 케이스 데이터 경로
GOLDEN_PATH: Path = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "golden"
    / "character_stats_cases.json"
)


def _load_cases() -> list[dict[str, Any]]:
    """캐릭터 스탯 합산 골든 케이스 로드"""

    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        payload: dict[str, Any] = json.load(f)

    return payload["cases"]


def _case_ids() -> list[str]:
    """케이스 이름 기반 테스트 ID 구성"""

    return [case["name"] for case in _load_cases()]


@pytest.mark.parametrize("case", _load_cases(), ids=_case_ids())
def test_live_stats_match_golden_values(case: dict[str, Any]) -> None:
    """캐릭터 전체 스탯 합산의 골든값 일치 검증

    기대값 출처는 케이스의 basis 필드에 기록한다.
    인게임 스탯창 대조를 마치면 basis를 실측 기준으로 갱신한다.
    """

    # 기대값 미기록 케이스 안내 (복사 붙여넣기 직후 상태)
    if case.get("expected") is None:
        pytest.fail(
            f"'{case['name']}' 케이스의 기대값이 비어 있습니다. "
            "tests/update_golden_snapshots.py 실행으로 스냅샷을 채운 뒤 "
            "인게임 스탯창과 대조하세요."
        )

    profile: CharacterProfile = CharacterProfile.from_dict(case["profile"])
    live: LiveStatView = compute_live_view(profile)

    # 최종 스탯 전체 항목 비교 (기대값이 소수 둘째 자리 반올림 저장이므로 반올림 오차만 허용)
    expected_final: dict[str, float] = case["expected"]["final_stats"]
    for stat_key, actual_value in live.final.values.items():
        expected_value: float = expected_final[stat_key.value]
        assert actual_value == pytest.approx(expected_value, abs=0.011), (
            f"{case['name']} - {stat_key.value} 합산 결과가 골든값과 다릅니다. "
            f"(근거: {case['basis']})"
        )

    # 공식 전투력 비교
    assert live.official_power == pytest.approx(
        case["expected"]["official_power"], abs=0.011
    )
