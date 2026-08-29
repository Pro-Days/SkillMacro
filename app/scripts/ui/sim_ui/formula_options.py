"""전투력 공식 선택 목록 구성 헬퍼

계산기 입력 화면과 재련 화면이 같은 공식 순서와 표시명을 사용하도록
빌트인 공식과 전역 커스텀 공식을 한 곳에서 조합한다.
"""

from __future__ import annotations

from app.scripts.calculator_engine import DISPLAY_POWER_METRICS, POWER_METRIC_LABELS
from app.scripts.calculator_models import CustomPowerFormula


def build_formula_label_map(
    custom_formulas: list[CustomPowerFormula],
) -> dict[str, str]:
    """전역 공식 목록 기준 빌트인/커스텀 공식 ID → 표시명 맵 구성"""

    # 빌트인 공식 표시명을 먼저 고정 순서로 등록
    formula_labels: dict[str, str] = {
        power_metric.value: POWER_METRIC_LABELS[power_metric]
        for power_metric in DISPLAY_POWER_METRICS
    }

    # 전역 저장된 커스텀 공식 표시명을 뒤에 추가
    custom_formula: CustomPowerFormula
    for custom_formula in custom_formulas:
        formula_labels[custom_formula.id] = custom_formula.name

    return formula_labels


def build_formula_options(
    custom_formulas: list[CustomPowerFormula],
) -> list[str]:
    """전역 공식 목록 기준 공식 드롭다운 순서 목록 구성"""

    # 빌트인 공식 뒤에 커스텀 공식을 저장 순서대로 연결
    formula_ids: list[str] = [
        power_metric.value for power_metric in DISPLAY_POWER_METRICS
    ]
    formula_ids.extend(custom_formula.id for custom_formula in custom_formulas)
    return formula_ids
