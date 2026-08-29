from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.scripts.calculator_engine import (
    evaluate_builtin_power_metric,
    evaluate_official_power,
)
from app.scripts.calculator_models import BaseStats, FinalStats, PowerMetric, StatKey

# 골든 케이스 데이터 경로
GOLDEN_PATH: Path = (
    Path(__file__).resolve().parents[1] / "data" / "golden" / "power_formula_cases.json"
)


def _load_cases() -> list[dict[str, Any]]:
    """전투력 공식 골든 케이스 로드"""

    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        payload: dict[str, Any] = json.load(f)

    return payload["cases"]


def _case_ids() -> list[str]:
    """케이스 이름 기반 테스트 ID 구성"""

    return [case["name"] for case in _load_cases()]


@pytest.mark.parametrize("case", _load_cases(), ids=_case_ids())
def test_builtin_metrics_match_golden_values(case: dict[str, Any]) -> None:
    """내장 전투력 공식의 골든값 일치 검증

    기대값 출처는 케이스의 basis 필드에 기록한다.
    인게임 대조를 마치면 basis를 실측 기준으로 갱신한다.
    """

    # 기대값 미기록 케이스 안내 (스탯 붙여넣기 직후 상태)
    if case.get("expected_metrics") is None:
        pytest.fail(
            f"'{case['name']}' 케이스의 기대값이 비어 있습니다. "
            "tests/update_golden_snapshots.py 실행으로 스냅샷을 채운 뒤 "
            "인게임 수치와 대조하세요."
        )

    resolved: FinalStats = BaseStats.from_dict(case["base_stats"]).resolve()

    # 케이스에 기록된 공식별 기대값 전체 비교
    for formula_id, expected_value in case["expected_metrics"].items():
        power_metric: PowerMetric = PowerMetric(formula_id)
        if power_metric == PowerMetric.OFFICIAL:
            actual_value: float = evaluate_official_power(resolved)
        else:
            actual_value = evaluate_builtin_power_metric(resolved, power_metric)

        # 기대값이 소수 둘째 자리 반올림 저장이므로 반올림 오차만 허용
        assert actual_value == pytest.approx(expected_value, abs=0.011), (
            f"{case['name']} - {formula_id} 공식 값이 골든값과 다릅니다. "
            f"(근거: {case['basis']})"
        )


def test_official_power_hand_computed_reference() -> None:
    """공식 전투력의 손계산 기준값 일치 검증

    공식 전투력 = floor(10*공격력 + 0.5*체력 + 20*치확 + 10*치공 + 10*물약회복
                  + 40*(스킬피해 + 최종공격력 + 보스공격력 + 회피 + 스킬속도))
    공격력 10, 치명타 공격력 110 입력 기준 10*10 + 10*110 = 1200
    """

    base_stats: BaseStats = BaseStats.create_default().with_changes(
        {StatKey.ATTACK: 10.0}
    )

    assert evaluate_official_power(base_stats.resolve()) == 1200.0
