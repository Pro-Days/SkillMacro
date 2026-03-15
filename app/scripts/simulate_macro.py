from __future__ import annotations

import random
from typing import TYPE_CHECKING

from app.scripts.calculator_engine import (
    CalculatorDamageEvent,
    CalculatorEvaluationContext,
    DISPLAY_POWER_METRICS,
    build_calculator_context,
    build_damage_events,
)
from app.scripts.custom_classes import (
    SimAnalysis,
    SimAttack,
    SimResult,
)
from app.scripts.macro_models import SkillUsageSetting

if TYPE_CHECKING:
    from app.scripts.macro_models import MacroPreset
    from app.scripts.registry.server_registry import ServerSpec


def simulate_random_from_calculator(
    server_spec: "ServerSpec",
    preset: "MacroPreset",
    skills_info: dict[str, SkillUsageSetting],
    delay_ms: int,
    overall_stats: dict[str, float],
) -> SimResult:
    """계산기 입력 기준 그래프용 시뮬레이션 결과 구성"""

    # 계산기 기준 타임라인과 5종 전투력 요약 구성
    context: CalculatorEvaluationContext = build_calculator_context(
        server_spec=server_spec,
        preset=preset,
        skills_info=skills_info,
        delay_ms=delay_ms,
        overall_stats=overall_stats,
    )

    # 결정론 기준 보스/일반 공격 이벤트 생성
    deterministic_boss_events: list[CalculatorDamageEvent] = build_damage_events(
        timeline=context.timeline,
        resolved_stats=context.baseline_stats,
        is_boss=True,
        deterministic=True,
    )
    deterministic_normal_events: list[CalculatorDamageEvent] = build_damage_events(
        timeline=context.timeline,
        resolved_stats=context.baseline_stats,
        is_boss=False,
        deterministic=True,
    )

    # 그래프 위젯 재사용을 위한 기존 공격 DTO 변환
    deterministic_boss_attacks: list[SimAttack] = [
        SimAttack(
            skill_id=event.skill_id,
            time=event.time,
            damage=event.damage,
        )
        for event in deterministic_boss_events
    ]

    # 확률 분포 분석용 랜덤 보스/일반 공격 이벤트 반복 생성
    random_boss_attacks: list[list[SimAttack]] = []
    random_normal_attacks: list[list[SimAttack]] = []
    for _ in range(1000):
        boss_seed: float = random.random()
        normal_seed: float = random.random()
        boss_events: list[CalculatorDamageEvent] = build_damage_events(
            timeline=context.timeline,
            resolved_stats=context.baseline_stats,
            is_boss=True,
            deterministic=False,
            random_seed=boss_seed,
        )
        normal_events: list[CalculatorDamageEvent] = build_damage_events(
            timeline=context.timeline,
            resolved_stats=context.baseline_stats,
            is_boss=False,
            deterministic=False,
            random_seed=normal_seed,
        )
        random_boss_attacks.append(
            [
                SimAttack(
                    skill_id=event.skill_id,
                    time=event.time,
                    damage=event.damage,
                )
                for event in boss_events
            ]
        )
        random_normal_attacks.append(
            [
                SimAttack(
                    skill_id=event.skill_id,
                    time=event.time,
                    damage=event.damage,
                )
                for event in normal_events
            ]
        )

    # 확률 통계 계산용 총 피해량 집계
    total_boss_damage: float = sum(
        attack.damage for attack in deterministic_boss_attacks
    )
    total_normal_damage: float = sum(
        event.damage for event in deterministic_normal_events
    )
    total_boss_damages: list[float] = [
        sum(attack.damage for attack in attack_list)
        for attack_list in random_boss_attacks
    ]
    total_normal_damages: list[float] = [
        sum(attack.damage for attack in attack_list)
        for attack_list in random_normal_attacks
    ]

    # 백분위수 계산용 내부 정렬 기반 보간 함수
    def calculate_percentile(data: list[float], percentile: int) -> float:
        sorted_data: list[float] = sorted(data)
        rank: float = (percentile * 0.01) * (len(data) - 1) + 1
        lower_index: int = int(rank) - 1
        fraction: float = rank - int(rank)
        if lower_index + 1 < len(data):
            result: float = sorted_data[lower_index] + fraction * (
                sorted_data[lower_index + 1] - sorted_data[lower_index]
            )
            return result

        return sorted_data[lower_index]

    # 표준편차 계산용 평균 기준 편차 제곱합 함수
    def calculate_std(data: list[float]) -> float:
        mean: float = sum(data) / len(data)
        squared_differences: list[float] = [(value - mean) ** 2 for value in data]
        variance: float = sum(squared_differences) / len(data)
        return variance**0.5

    # 보스/일반 피해량 분석 카드 데이터 구성
    analysis: list[SimAnalysis] = [
        SimAnalysis(
            title="초당 보스피해량",
            value=f"{int(total_boss_damage / 60)}",
            min=f"{int(min(total_boss_damages) / 60)}",
            max=f"{int(max(total_boss_damages) / 60)}",
            std=f"{calculate_std(total_boss_damages) / 60:.1f}",
            p25=f"{int(calculate_percentile(total_boss_damages, 25) / 60)}",
            p50=f"{int(calculate_percentile(total_boss_damages, 50) / 60)}",
            p75=f"{int(calculate_percentile(total_boss_damages, 75) / 60)}",
        ),
        SimAnalysis(
            title="총 보스피해량",
            value=f"{int(total_boss_damage)}",
            min=f"{int(min(total_boss_damages))}",
            max=f"{int(max(total_boss_damages))}",
            std=f"{calculate_std(total_boss_damages):.1f}",
            p25=f"{int(calculate_percentile(total_boss_damages, 25))}",
            p50=f"{int(calculate_percentile(total_boss_damages, 50))}",
            p75=f"{int(calculate_percentile(total_boss_damages, 75))}",
        ),
        SimAnalysis(
            title="초당 피해량",
            value=f"{int(total_normal_damage / 60)}",
            min=f"{int(min(total_normal_damages) / 60)}",
            max=f"{int(max(total_normal_damages) / 60)}",
            std=f"{calculate_std(total_normal_damages) / 60:.1f}",
            p25=f"{int(calculate_percentile(total_normal_damages, 25) / 60)}",
            p50=f"{int(calculate_percentile(total_normal_damages, 50) / 60)}",
            p75=f"{int(calculate_percentile(total_normal_damages, 75) / 60)}",
        ),
        SimAnalysis(
            title="총 피해량",
            value=f"{int(total_normal_damage)}",
            min=f"{int(min(total_normal_damages))}",
            max=f"{int(max(total_normal_damages))}",
            std=f"{calculate_std(total_normal_damages):.1f}",
            p25=f"{int(calculate_percentile(total_normal_damages, 25))}",
            p50=f"{int(calculate_percentile(total_normal_damages, 50))}",
            p75=f"{int(calculate_percentile(total_normal_damages, 75))}",
        ),
    ]

    # 계산기 전투력 순서 기준 5칸 전투력 목록 구성
    powers: list[float] = [
        context.baseline_summary.metrics[power_metric]
        for power_metric in DISPLAY_POWER_METRICS
    ]
    return SimResult(
        powers=powers,
        analysis=analysis,
        deterministic_boss_attacks=deterministic_boss_attacks,
        random_boss_attacks=random_boss_attacks,
    )
