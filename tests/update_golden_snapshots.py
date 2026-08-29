"""골든 케이스의 비어 있는 기대값을 현재 코드 계산 결과로 채우는 도구

사용 방법:
    ./.venv/Scripts/python.exe tests/update_golden_snapshots.py

동작 규칙:
- expected(또는 expected_metrics)가 null인 케이스만 계산해서 채운다.
- 이미 값이 있는 케이스는 절대 덮어쓰지 않는다.
  의도한 로직 변경으로 재생성이 필요하면 해당 케이스의 기대값을 null로 바꾼 뒤 실행한다.
- basis가 null이면 "코드 스냅샷" 근거를 기록한다.
  채워진 값은 회귀 감지용 스냅샷이므로, 인게임 대조를 마치면 basis를 실측 기준으로 갱신한다.

캐릭터 케이스 추가 방법:
- 캐릭터 페이지의 "복사" 버튼으로 클립보드에 담긴 JSON을
  character_stats_cases.json의 새 케이스 "profile" 필드에 붙여넣고
  "name"을 적은 뒤 이 스크립트를 실행하면 expected가 채워진다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# 프로젝트 루트를 import 경로에 보장
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.scripts.calculator_engine import (
    build_calculator_context,
    evaluate_builtin_power_metric,
    evaluate_official_power,
)
from app.scripts.calculator_models import BaseStats, FinalStats, PowerMetric
from app.scripts.character_engine import LiveStatView, compute_live_view
from app.scripts.character_models import CharacterProfile
from app.scripts.config import config
from tests.conftest import build_full_equipped_preset, build_synthetic_server, make_realistic_base_stats

GOLDEN_DIR: Path = PROJECT_ROOT / "tests" / "data" / "golden"

SNAPSHOT_BASIS: str = f"코드 스냅샷 ({config.version} 기준, 인게임 대조 전)"

# 스탯만으로 계산 가능한 골든 대상 공식 목록
STAT_ONLY_METRICS: tuple[PowerMetric, ...] = (
    PowerMetric.OFFICIAL,
    PowerMetric.DAMAGE_CHECK,
    PowerMetric.BOSS_DAMAGE_CHECK,
    PowerMetric.SKILL_SPEED_DAMAGE_CHECK,
    PowerMetric.SKILL_SPEED_BOSS_DAMAGE_CHECK,
    PowerMetric.PATTERN_SKIP_DAMAGE_CHECK,
)


def _round2(value: float) -> float:
    """기대값 저장용 소수 둘째 자리 반올림

    앱의 FinalStats 표시 규칙과 동일한 정밀도로 저장해
    사람이 인게임 수치와 직접 대조할 수 있게 한다.
    """

    return round(value, 2)


def _load(path: Path) -> dict[str, Any]:
    """골든 파일 로드"""

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, payload: dict[str, Any]) -> None:
    """골든 파일 저장"""

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)


def _fill_basis(case: dict[str, Any]) -> None:
    """근거 미기록 케이스에 코드 스냅샷 근거 기록"""

    if not case.get("basis"):
        case["basis"] = SNAPSHOT_BASIS


def update_power_formula_cases() -> int:
    """전투력 공식 골든의 빈 기대값 채움"""

    path: Path = GOLDEN_DIR / "power_formula_cases.json"
    payload: dict[str, Any] = _load(path)

    filled_count: int = 0
    for case in payload["cases"]:
        if case.get("expected_metrics") is not None:
            continue

        # 케이스 입력 스탯 기준 공식별 스냅샷 계산
        resolved: FinalStats = BaseStats.from_dict(case["base_stats"]).resolve()
        metrics: dict[str, float] = {}
        for metric in STAT_ONLY_METRICS:
            if metric == PowerMetric.OFFICIAL:
                metrics[metric.value] = _round2(evaluate_official_power(resolved))
            else:
                metrics[metric.value] = _round2(
                    evaluate_builtin_power_metric(resolved, metric)
                )

        case["expected_metrics"] = metrics
        _fill_basis(case)
        filled_count += 1
        print(f"[power_formula] '{case['name']}' 기대값 채움")

    if filled_count:
        _save(path, payload)

    return filled_count


def update_character_stats_cases() -> int:
    """캐릭터 스탯 합산 골든의 빈 기대값 채움"""

    path: Path = GOLDEN_DIR / "character_stats_cases.json"
    payload: dict[str, Any] = _load(path)

    filled_count: int = 0
    for case in payload["cases"]:
        if case.get("expected") is not None:
            continue

        # 케이스 프로필 기준 실시간 합산 스냅샷 계산
        profile: CharacterProfile = CharacterProfile.from_dict(case["profile"])
        live: LiveStatView = compute_live_view(profile)
        case["expected"] = {
            "final_stats": {
                stat_key.value: _round2(value)
                for stat_key, value in live.final.values.items()
            },
            "official_power": _round2(live.official_power),
        }
        _fill_basis(case)
        filled_count += 1
        print(f"[character_stats] '{case['name']}' 기대값 채움")

    if filled_count:
        _save(path, payload)

    return filled_count


def update_timeline_damage_cases() -> int:
    """60초 타임라인 스냅샷의 빈 기대값 채움"""

    path: Path = GOLDEN_DIR / "timeline_damage_cases.json"
    payload: dict[str, Any] = _load(path)

    filled_count: int = 0
    for case in payload["cases"]:
        if case.get("expected") is not None:
            continue

        # 테스트와 동일한 합성 서버/풀 장착/현실 스탯 조건으로 계산
        server_spec = build_synthetic_server()
        preset = build_full_equipped_preset(server_spec)
        base_stats: BaseStats = make_realistic_base_stats()
        delay_ms: int = int(case["delay_ms"])

        context_boss = build_calculator_context(
            server_spec=server_spec,
            preset=preset,
            skills_info=preset.usage_settings,
            delay_ms=delay_ms,
            base_stats=base_stats,
            target_formula_id=PowerMetric.BOSS_DAMAGE.value,
            custom_formulas=(),
        )
        context_normal = build_calculator_context(
            server_spec=server_spec,
            preset=preset,
            skills_info=preset.usage_settings,
            delay_ms=delay_ms,
            base_stats=base_stats,
            target_formula_id=PowerMetric.NORMAL_DAMAGE.value,
            custom_formulas=(),
        )

        case["expected"] = {
            "hit_event_count": len(context_boss.timeline_artifacts.hit_events),
            "boss_damage_power": _round2(context_boss.baseline_power),
            "normal_damage_power": _round2(context_normal.baseline_power),
        }

        # 타임라인 스냅샷은 인게임 대조가 불가능한 회귀 감지 전용 값
        if not case.get("basis"):
            case["basis"] = f"코드 스냅샷 ({config.version} 기준, 로직 회귀 감지 전용)"

        filled_count += 1
        print(f"[timeline_damage] '{case['name']}' 기대값 채움")

    if filled_count:
        _save(path, payload)

    return filled_count


if __name__ == "__main__":
    total: int = (
        update_power_formula_cases()
        + update_character_stats_cases()
        + update_timeline_damage_cases()
    )
    if total == 0:
        print("비어 있는 기대값이 없습니다. 재생성이 필요하면 대상 케이스의 기대값을 null로 바꾼 뒤 실행하세요.")
