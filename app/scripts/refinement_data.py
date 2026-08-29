from __future__ import annotations

from dataclasses import dataclass

from app.scripts.calculator_models import RefinementAssist, RefinementEquipment, StatKey

# 최대 재련 단계 (20강에서는 추가 재련 불가)
MAX_REFINE_STEP: int = 20

# 재련 시도가 가능한 단계 수 (0강 → 19강에서 시도)
REFINE_ATTEMPT_STEP_COUNT: int = MAX_REFINE_STEP

# 실패 시 단계 하락 확률 (나머지는 현재 단계 유지)
DOWNGRADE_RATE_ON_FAILURE: float = 0.6

# 재련펫·VIP 재련비 할인율 (동시 적용 시 합연산)
REFINE_PET_DISCOUNT: float = 0.05
VIP_DISCOUNT: float = 0.10

# 강화주머니 1개가 제공하는 강화포인트
POINT_BUNDLE_SIZE: int = 5


@dataclass(frozen=True, slots=True)
class RefinementAssistSpec:
    """재련 보조 사용 스펙"""

    label: str
    points: int
    success_bonus: float


# 보조별 소모 포인트와 성공확률 증가량
REFINEMENT_ASSIST_SPECS: dict[RefinementAssist, RefinementAssistSpec] = {
    RefinementAssist.NONE: RefinementAssistSpec(label="없음", points=0, success_bonus=0.0),
    RefinementAssist.POINT3: RefinementAssistSpec(
        label="3pt",
        points=3,
        success_bonus=0.03,
    ),
    RefinementAssist.POINT7: RefinementAssistSpec(
        label="7pt",
        points=7,
        success_bonus=0.05,
    ),
}


def _expand_step_values(
    bracket_values: tuple[float, ...],
    bracket_bounds: tuple[int, ...],
) -> tuple[float, ...]:
    """구간별 값을 단계별(0~19강 시도) 값으로 전개"""

    # 각 시도 단계가 속한 구간의 값을 그대로 배치
    values: list[float] = []
    for step in range(REFINE_ATTEMPT_STEP_COUNT):
        for bracket_index, upper_bound in enumerate(bracket_bounds):
            if step <= upper_bound:
                values.append(bracket_values[bracket_index])
                break

    return tuple(values)


# 기본 성공확률 구간 (0~3강, 4~7강, 8~11강, 12~19강)
_SUCCESS_RATE_BRACKET_BOUNDS: tuple[int, ...] = (3, 7, 11, 19)
_SUCCESS_RATE_BRACKET_VALUES: tuple[float, ...] = (0.55, 0.45, 0.35, 0.25)

# 단계별 기본 성공확률 (index = 시도하는 현재 단계)
REFINE_BASE_SUCCESS_RATES: tuple[float, ...] = _expand_step_values(
    _SUCCESS_RATE_BRACKET_VALUES,
    _SUCCESS_RATE_BRACKET_BOUNDS,
)


# 재련비 구간 (0~3강, 4~6강, 7~9강, 10~19강)
_COST_BRACKET_BOUNDS: tuple[int, ...] = (3, 6, 9, 19)

# 레벨제별 구간 재련비 (재련펫·VIP 미적용 기준)
_LEVEL_CAP_BRACKET_COSTS: dict[int, tuple[float, ...]] = {
    0: (2000.0, 4000.0, 6000.0, 8000.0),
    20: (2000.0, 4000.0, 8000.0, 10000.0),
    50: (4000.0, 8000.0, 10000.0, 12000.0),
    80: (8000.0, 10000.0, 12000.0, 14000.0),
    110: (10000.0, 12000.0, 14000.0, 16000.0),
    150: (12000.0, 14000.0, 16000.0, 18000.0),
    180: (14000.0, 16000.0, 18000.0, 20000.0),
}

# 선택 가능한 레벨제 목록
REFINE_LEVEL_CAPS: tuple[int, ...] = tuple(sorted(_LEVEL_CAP_BRACKET_COSTS))

# 레벨제별 단계 재련비 (재련펫·VIP 미적용 기준)
REFINE_BASE_COSTS: dict[int, tuple[float, ...]] = {
    level_cap: _expand_step_values(bracket_costs, _COST_BRACKET_BOUNDS)
    for level_cap, bracket_costs in _LEVEL_CAP_BRACKET_COSTS.items()
}

# 모든 기본 재련비의 공약수 (분포 계산 격자 단위)
REFINE_COST_UNIT: float = 2000.0


def refine_cost_multiplier(use_refine_pet: bool, use_vip: bool) -> float:
    """재련펫·VIP 할인이 반영된 재련비 배율 반환"""

    # 재련펫과 VIP 할인은 합연산으로 적용
    discount: float = 0.0
    if use_refine_pet:
        discount += REFINE_PET_DISCOUNT

    if use_vip:
        discount += VIP_DISCOUNT

    return 1.0 - discount


def build_refine_costs(
    level_cap: int,
    use_refine_pet: bool,
    use_vip: bool,
) -> tuple[float, ...]:
    """할인이 반영된 레벨제별 단계 재련비 반환"""

    # 기본 재련비에 할인 배율을 적용
    multiplier: float = refine_cost_multiplier(use_refine_pet, use_vip)
    base_costs: tuple[float, ...] = REFINE_BASE_COSTS[level_cap]
    return tuple(base_cost * multiplier for base_cost in base_costs)


# 무기 단계별 누적 재련 스탯 (공격력, 공격력%, 스킬 피해량%)
_WEAPON_CUMULATIVE_VALUES: tuple[tuple[float, float, float], ...] = (
    (0.0, 0.0, 0.0),
    (3.0, 0.0, 0.0),
    (6.0, 0.0, 0.0),
    (9.0, 0.0, 1.0),
    (12.0, 0.0, 1.0),
    (15.0, 0.0, 1.0),
    (18.0, 0.0, 2.0),
    (21.0, 0.0, 2.0),
    (24.0, 0.0, 2.0),
    (27.0, 0.0, 3.0),
    (30.0, 1.0, 3.0),
    (33.0, 1.0, 3.0),
    (36.0, 1.0, 4.0),
    (39.0, 2.0, 4.0),
    (42.0, 2.0, 4.0),
    (45.0, 2.0, 5.0),
    (48.0, 3.0, 5.0),
    (51.0, 3.0, 5.0),
    (54.0, 3.0, 6.0),
    (57.0, 4.0, 6.0),
    (60.0, 4.0, 7.0),
)

# 방어구 단계별 누적 재련 스탯 (부위 주스탯, 부위 주스탯%, 경험치 획득량%)
_ARMOR_CUMULATIVE_VALUES: tuple[tuple[float, float, float], ...] = (
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (2.0, 0.0, 0.0),
    (3.0, 1.0, 0.0),
    (5.0, 1.0, 0.0),
    (7.0, 1.0, 0.0),
    (9.0, 2.0, 0.0),
    (12.0, 2.0, 0.0),
    (15.0, 2.0, 0.0),
    (18.0, 3.0, 0.0),
    (22.0, 3.0, 1.0),
    (26.0, 3.0, 1.0),
    (30.0, 4.0, 1.0),
    (35.0, 4.0, 1.0),
    (40.0, 4.0, 1.0),
    (45.0, 5.0, 1.0),
    (51.0, 5.0, 1.0),
    (57.0, 5.0, 1.0),
    (63.0, 6.0, 1.0),
    (70.0, 6.0, 2.0),
    (77.0, 7.0, 2.0),
)


# 장비 종류별 재련 상승 스탯 키 (누적표 열 순서와 일치)
REFINEMENT_STAT_KEYS: dict[RefinementEquipment, tuple[StatKey, StatKey, StatKey]] = {
    RefinementEquipment.WEAPON: (
        StatKey.ATTACK,
        StatKey.ATTACK_PERCENT,
        StatKey.SKILL_DAMAGE_PERCENT,
    ),
    RefinementEquipment.HELMET: (
        StatKey.LUCK,
        StatKey.LUCK_PERCENT,
        StatKey.EXP_PERCENT,
    ),
    RefinementEquipment.ARMOR: (
        StatKey.STR,
        StatKey.STR_PERCENT,
        StatKey.EXP_PERCENT,
    ),
    RefinementEquipment.BELT: (
        StatKey.VITALITY,
        StatKey.VITALITY_PERCENT,
        StatKey.EXP_PERCENT,
    ),
    RefinementEquipment.SHOES: (
        StatKey.DEXTERITY,
        StatKey.DEXTERITY_PERCENT,
        StatKey.EXP_PERCENT,
    ),
}


# 장비 종류 표시 이름
REFINEMENT_EQUIPMENT_LABELS: dict[RefinementEquipment, str] = {
    RefinementEquipment.WEAPON: "무기",
    RefinementEquipment.HELMET: "투구",
    RefinementEquipment.ARMOR: "갑옷",
    RefinementEquipment.BELT: "허리띠",
    RefinementEquipment.SHOES: "신발",
}


def _build_cumulative_stats(
    equipment: RefinementEquipment,
) -> tuple[dict[StatKey, float], ...]:
    """장비 종류별 단계 누적 스탯 맵 구성"""

    # 무기와 방어구는 서로 다른 누적표를 사용
    cumulative_values: tuple[tuple[float, float, float], ...] = (
        _WEAPON_CUMULATIVE_VALUES
        if equipment == RefinementEquipment.WEAPON
        else _ARMOR_CUMULATIVE_VALUES
    )
    stat_keys: tuple[StatKey, StatKey, StatKey] = REFINEMENT_STAT_KEYS[equipment]

    # 단계별로 스탯 키와 누적 수치를 묶어 저장
    step_stats: list[dict[StatKey, float]] = []
    for step_values in cumulative_values:
        step_stats.append(
            {
                stat_key: value
                for stat_key, value in zip(stat_keys, step_values)
            }
        )

    return tuple(step_stats)


# 장비 종류별 단계 누적 재련 스탯
REFINEMENT_CUMULATIVE_STATS: dict[
    RefinementEquipment, tuple[dict[StatKey, float], ...]
] = {equipment: _build_cumulative_stats(equipment) for equipment in RefinementEquipment}


def refinement_cumulative_stats(
    equipment: RefinementEquipment,
    step: int,
) -> dict[StatKey, float]:
    """지정 단계의 누적 재련 스탯 반환"""

    # 저장된 누적표를 복사해 호출자 변경으로부터 보호
    return dict(REFINEMENT_CUMULATIVE_STATS[equipment][step])


def refinement_stat_delta(
    equipment: RefinementEquipment,
    start_step: int,
    target_step: int,
) -> dict[StatKey, float]:
    """시작 단계 대비 목표 단계의 재련 스탯 증가량 반환"""

    # 현재 입력 스탯에는 시작 단계 효과가 포함되어 있으므로 누적 차이만 사용
    start_stats: dict[StatKey, float] = REFINEMENT_CUMULATIVE_STATS[equipment][
        start_step
    ]
    target_stats: dict[StatKey, float] = REFINEMENT_CUMULATIVE_STATS[equipment][
        target_step
    ]

    delta: dict[StatKey, float] = {}
    for stat_key, target_value in target_stats.items():
        difference: float = target_value - start_stats[stat_key]
        if difference == 0.0:
            continue

        delta[stat_key] = difference

    return delta
