from __future__ import annotations

import random
from functools import lru_cache

from app.scripts.app_state import app_state
from app.scripts.config import config
from app.scripts.custom_classes import (
    SimAnalysis,
    SimAttack,
    SimBuff,
    SimResult,
    SimSkill,
    Stats,
)
from app.scripts.macro_models import EquippedSkillRef, LinkUseType, SkillUsageSetting
from app.scripts.registry.skill_registry import (
    BuffEffect,
    DamageEffect,
    HealEffect,
    LevelEffect,
    get_builtin_skill_id,
)
from app.scripts.run_macro import get_prepared_link_skill_indices


def get_req_stats(powers: list[float], stat_type: str) -> list[float]:
    """
    목표 전투력까지 필요한 스탯 반환
    """

    req_stats: list[float] = [
        calculate_req_stat(power=powers[i], stat_type=stat_type, power_num=i)
        for i in range(4)
    ]

    return req_stats


def calculate_req_stat(power: float, stat_type: str, power_num: int) -> float:
    """
    목표 전투력까지 필요한 스탯 계산
    """

    def is_stat_valid(value: int | float) -> bool:
        """
        스탯이 유효 범위 내에 있는지 확인
        """

        return (
            config.specs.STATS[stat_type].min
            <= value
            <= config.specs.STATS[stat_type].max
        )

    stats: Stats = app_state.simulation.stats.copy()
    base_stat: int | float = stats.get_stat_from_name(stat=stat_type)

    # 현재 전투력 계산
    current_power: float = simulate_deterministic(
        stats=stats,
        sim_details=app_state.simulation.sim_details,
        skills_info=app_state.macro.current_preset.usage_settings,
    ).powers[power_num]

    # 스탯을 증가시키며 최대 범위 알아내기
    low: int | float = 0
    high: int | float = 1
    step: int = 1

    # num으로 무한루프 방지
    num: int = 0
    while current_power < power:
        # 스탯이 유효 범위 내에 있지 않으면 0 반환
        if not is_stat_valid(value=base_stat + low):
            return 0.0

        if num == 10:
            # 10번 반복했는데도 범위를 찾지 못했다면 실패
            return 0.0

        # 스탯 증가
        stats.set_stat_from_name(stat=stat_type, value=base_stat + high)

        # 전투력 계산
        current_power = simulate_deterministic(
            stats=stats,
            sim_details=app_state.simulation.sim_details,
            skills_info=app_state.macro.current_preset.usage_settings,
        ).powers[power_num]

        # 최대값을 알아내면 break
        if current_power >= power:
            break

        # print(f"{low=}, {high=}, {step=}")

        low = high
        high += step

        # step을 두 배로 증가해서 범위를 빠르게 늘림
        step *= 2
        num += 1

    # 범위 내에서 이분탐색
    # low, high의 차이가 0.05 이하가 될 때까지 반복
    epsilon: float = 0.05

    # num으로 무한루프 방지
    num: int = 0
    while high - low > epsilon and num < 15:
        # 스탯이 유효 범위 내에 있지 않으면 0 반환
        if not is_stat_valid(value=base_stat + low):
            return 0.0

        mid: float = (low + high) * 0.5
        # TODO: dataclass로 변경
        stats.set_stat_from_name(stat=stat_type, value=base_stat + mid)

        # 전투력 계산
        current_power = simulate_deterministic(
            stats=stats,
            sim_details=app_state.simulation.sim_details,
            skills_info=app_state.macro.current_preset.usage_settings,
        ).powers[power_num]

        if current_power < power:
            low = mid
        else:
            high = mid

        num += 1

    # ???
    # mid -> low로 변경 고려: 필요한 최소 값
    return (low + high) * 0.5


def execute_simulation(
    attack_details: list[SimAttack],
    buff_details: list[SimBuff],
    stats: Stats,
    is_boss: bool,
    deterministic: bool = False,
) -> list[SimAttack]:
    """
    시간별 가한 데미지 계산
    """

    # 현재 상태 정보 가져오기
    def get_current_stat(current_time: float, buff_list: list[SimBuff]) -> Stats:
        # 현재 상태를 복사: dataclass replace 사용
        current_stats: Stats = stats.copy()

        # 현재 시간에 적용되는 버프를 찾아서 상태에 반영
        for buff in buff_list:
            if buff.start_time <= current_time <= buff.end_time:
                current_stats.apply_buff(buff=buff)

        return current_stats

    def get_damage(stats: Stats) -> float:

        # 기본 데미지 계산
        damage: float = (
            stats.ATK  # 공격력
            * (stats.STR + stats.INT)  # 근력 + 지력
            * (1 + stats.PWR * 0.01)  # 파괴력
            * 0.01  # 보정계수
        )

        # 보스면 보스 데미지 적용
        if is_boss:
            damage *= 1 + stats.BOSS_DMG * 0.01

        if deterministic:
            # 치확, 치뎀에 따라 데미지 계산
            crit_prob: int | float = min(stats.CRIT_RATE, 100)
            damage *= 1 + crit_prob * stats.CRIT_DMG * 0.0001

            # 최소, 최대데미지 중간
            # 최소데미지: 1.0, 최대데미지: 1.2 라고 가정
            damage *= 1.1

            return damage

        damage *= random.uniform(1, 1.2)  # 최소데미지: 1.0, 최대데미지: 1.2 라고 가정

        # 치명타 여부에 따라 치명타 데미지 적용
        if random.random() < stats.CRIT_RATE * 0.01:
            damage *= 1 + stats.CRIT_DMG * 0.01

        return damage

    def merge_buff(buff_details: list[SimBuff]) -> list[SimBuff]:
        # 종류와 값을 기준으로 그룹화 -> 스킬을 기준으로 변경
        grouped: dict[str, list[SimBuff]] = {}

        for buff in buff_details:
            # 버프 종류와 값을 튜플로 묶음
            key: str = buff.skill_id

            # 해당 키가 없으면 새로 생성
            if key not in grouped:
                grouped[key] = []

            # 버프의 시작 시간과 종료 시간을 리스트로 추가
            grouped[key].append(buff)

        # 각 그룹의 겹치는 구간 병합
        merged_buffs: list[SimBuff] = []
        for buffs in grouped.values():
            # 시작 시간을 기준으로 정렬
            buffs.sort(key=lambda x: x.start_time)

            # 첫 번째 버프부터 병합 시작
            merged: list[SimBuff] = [buffs[0]]

            for buff in buffs[1:]:
                # 이전 버프와 겹치는지 확인
                # 버프 시작 시간이 이전 버프의 종료 시간보다 작거나 같으면 병합
                if buff.start_time <= merged[-1].end_time:
                    merged[-1].end_time = buff.end_time

                # 겹치지 않으면 새로운 버프로 추가
                else:
                    merged.append(buff)

            # 병합된 버프를 최종 리스트에 추가
            merged_buffs.extend(merged)

        # 시작 시간 기준으로 정렬
        merged_buffs.sort(key=lambda x: x.start_time)

        return merged_buffs

    # 버프 정보 병합
    buff_info: list[SimBuff] = merge_buff(buff_details=buff_details)
    attacks: list[SimAttack] = []

    # 공격 데이터 정리
    for attack in attack_details:
        # 스탯 정보 가져오기
        current_stats: Stats = get_current_stat(
            current_time=attack.time, buff_list=buff_info
        )

        damage: float = get_damage(stats=current_stats) * attack.damage

        new_attack: SimAttack = SimAttack(
            skill_id=attack.skill_id,
            time=attack.time,
            damage=damage,
        )

        attacks.append(new_attack)

    return attacks


def simulate_random(
    stats: Stats,
    sim_details: dict[str, int],
) -> SimResult:
    """최소, 최대, 평균, 표준편차 등을 계산하는 확률론적 시뮬레이션"""

    # 시뮬레이션 세부정보를 해시 가능하게 만듦
    sim_details_tuple: tuple = tuple(sorted(sim_details.items()))
    # 스킬 레벨 정보를 추가
    # todo: 꼭 필요한 정보만 키로 사용하도록 수정
    skills_info_tuple: tuple[tuple[str, tuple[bool, bool, int]], ...] = tuple(
        sorted(
            (k, v.to_tuple())
            for k, v in app_state.macro.current_preset.usage_settings.items()
        )
    )

    return simulate(
        stats=stats,
        sim_details_tuple=sim_details_tuple,
        skills_info_tuple=skills_info_tuple,
        random_seed=random.random(),
    )


def simulate_deterministic(
    stats: Stats,
    sim_details: dict[str, int],
    skills_info: dict[str, SkillUsageSetting],
) -> SimResult:
    """
    전투력 계산을 위한 결정론적 시뮬레이션
    캐시를 사용하여 성능 향상
    """
    # todo: 스킬 레벨도 포함시키도록 수정

    @lru_cache(maxsize=1024)
    def _run(
        sim_details_tuple: tuple[tuple[str, int]],
        skills_info_tuple: tuple[tuple[str, tuple[bool, bool, int]], ...],
    ) -> SimResult:
        return simulate(
            stats=stats,
            sim_details_tuple=sim_details_tuple,
            skills_info_tuple=skills_info_tuple,
            random_seed=1.0,
        )

    # 시뮬레이션 세부정보를 튜플로 변환해서 해시 가능하게 만듦
    sim_details_tuple: tuple[tuple[str, int], ...] = tuple(sorted(sim_details.items()))
    # 스킬 정보를 추가
    skills_info_tuple: tuple[tuple[str, tuple[bool, bool, int]], ...] = tuple(
        sorted((k, v.to_tuple()) for k, v in skills_info.items())
    )

    return _run(sim_details_tuple, skills_info_tuple)


# 61초 -> 60초로 변경, 처음 0일 때 총 데미지를 0으로 설정
def simulate(
    stats: Stats,
    sim_details_tuple: tuple[tuple[str, int], ...],
    skills_info_tuple: tuple[tuple[str, tuple[bool, bool, int]], ...],
    random_seed: float,
) -> SimResult:

    # 백분위수 계산 함수
    def calculate_percentile(data: list[float], percentile: int) -> float:
        # 백분위수 계산을 위해 데이터를 정렬
        sorted_data: list[float] = sorted(data)

        # 백분위수 순위를 계산
        rank: float = (percentile * 0.01) * (len(data) - 1) + 1
        lower_index: int = int(rank) - 1
        fraction: float = rank - int(rank)

        # 선형 보간을 사용하여 백분위수 계산
        if lower_index + 1 < len(data):
            result: float = sorted_data[lower_index] + fraction * (
                sorted_data[lower_index + 1] - sorted_data[lower_index]
            )

        else:
            result: float = sorted_data[lower_index]

        return result

    # 표준편차 계산 함수
    def calculate_std(data: list[float]) -> float:
        # 평균 계산
        mean: float = sum(data) / len(data)

        # 각 데이터에서 평균을 뺀 제곱의 합 계산
        squared_differences: list[float] = [(x - mean) ** 2 for x in data]

        # 분산 계산
        variance: float = sum(squared_differences) / len(data)

        # 표준편차 계산
        std_dev: float = variance**0.5

        return std_dev

    # 튜플로 변환된 시뮬레이션 세부정보를 딕셔너리로 변환
    sim_details: dict[str, int] = dict(sim_details_tuple)

    # 랜덤 시드 설정
    # 랜덤 시드가 1이면 결정론적 시뮬레이션, 아니면 랜덤 시뮬레이션
    if random_seed != 1.0:
        random.seed(random_seed)

    # 사용한 스킬 목록
    attack_details, buff_details = get_simulated_skills(
        cooltimeReduce=stats.ATK_SPD,
        skills_info_tuple=skills_info_tuple,
    )

    # 공격 시뮬레이션 실행
    boss_attacks: list[SimAttack] = execute_simulation(
        attack_details=attack_details,
        buff_details=buff_details,
        stats=stats,
        is_boss=True,
        deterministic=True,
    )
    normal_attacks: list[SimAttack] = execute_simulation(
        attack_details=attack_details,
        buff_details=buff_details,
        stats=stats,
        is_boss=False,
        deterministic=True,
    )

    # 총 데미지 계산
    total_boss_damage: float = sum([i.damage for i in boss_attacks])
    total_normal_damage: float = sum([i.damage for i in normal_attacks])

    # 데미지감소 = 방어력 * 0.5 + 체력 * 경도 * 0.001
    damage_reduction: float = stats.DEF * 0.5 + stats.HP * stats.RES * 0.001
    # dmgReduction = stats[1] * 0.8 + stats[13] * stats[5] * 0.0004
    # 초당 회복량 = 체력 * 자연회복 * 0.2 + 포션회복(=포션회복량 * (1 + 포션회복력)) * 0.5
    recovery: float = (
        stats.HP * 0.1 * 0.2
        + sim_details["POTION_HEAL"] * (1 + stats.POT_HEAL * 0.01) * 0.5
    )

    # 전투력 계산s
    powers: list[float] = [
        # 보스데미지
        total_boss_damage * config.simulation.coef_boss_dmg,
        # 일반데미지
        total_normal_damage * config.simulation.coef_normal_dmg,
        # 보스
        total_boss_damage
        * config.simulation.coef_boss_dmg
        * (stats.HP + damage_reduction * 5 + recovery * 5)
        / (1 - stats.DODGE * 0.01)
        * config.simulation.coef_boss,
        # 일반
        total_normal_damage
        * config.simulation.coef_normal_dmg
        * (1 + stats.LUK * 0.01)
        * (1 + stats.STATUS_RES * 0.001)
        * (1 + stats.EXP * 0.01)
        * config.simulation.coef_normal,
    ]

    # 전투력만 반환
    if random_seed == 1.0:
        return SimResult(powers=powers)

    # start_time = time.time()

    # 1000회 시뮬레이션 실행
    # 1000회일 경우 멀티프로세싱보다 단일쓰레드에서 실행하는 것이 빠름
    random_boss_attacks: list[list[SimAttack]] = [
        execute_simulation(
            attack_details=attack_details,
            buff_details=buff_details,
            stats=stats,
            is_boss=True,
        )
        for _ in range(1000)
    ]
    random_normal_attacks: list[list[SimAttack]] = [
        execute_simulation(
            attack_details=attack_details,
            buff_details=buff_details,
            stats=stats,
            is_boss=False,
        )
        for _ in range(1000)
    ]

    # 총 데미지 계산
    total_boss_damages: list[float] = [
        sum([attack.damage for attack in random_boss_attack])
        for random_boss_attack in random_boss_attacks
    ]
    total_normal_damages: list[float] = [
        sum([attack.damage for attack in random_normal_attack])
        for random_normal_attack in random_normal_attacks
    ]

    # 보스 데미지 통계
    min_boss_damage: float = min(total_boss_damages)
    max_boss_damage: float = max(total_boss_damages)
    std_boss_damage: float = calculate_std(total_boss_damages)
    p25_boss_damage: float = calculate_percentile(total_boss_damages, 25)
    p50_boss_damage: float = calculate_percentile(total_boss_damages, 50)
    p75_boss_damage: float = calculate_percentile(total_boss_damages, 75)

    # 일반 데미지 통계
    min_normal_damage: float = min(total_normal_damages)
    max_normal_damage: float = max(total_normal_damages)
    std_normal_damage: float = calculate_std(total_normal_damages)
    p25_normal_damage: float = calculate_percentile(total_normal_damages, 25)
    p50_normal_damage: float = calculate_percentile(total_normal_damages, 50)
    p75_normal_damage: float = calculate_percentile(total_normal_damages, 75)

    # 시뮬레이션 결과 반환
    analysis: list[SimAnalysis] = [
        SimAnalysis(
            title="초당 보스피해량",
            value=f"{int(total_boss_damage / 60)}",
            min=f"{int(min_boss_damage / 60)}",
            max=f"{int(max_boss_damage / 60)}",
            std=f"{std_boss_damage / 60:.1f}",
            p25=f"{int(p25_boss_damage / 60)}",
            p50=f"{int(p50_boss_damage / 60)}",
            p75=f"{int(p75_boss_damage / 60)}",
        ),
        SimAnalysis(
            title="총 보스피해량",
            value=f"{int(total_boss_damage)}",
            min=f"{int(min_boss_damage)}",
            max=f"{int(max_boss_damage)}",
            std=f"{std_boss_damage:.1f}",
            p25=f"{int(p25_boss_damage)}",
            p50=f"{int(p50_boss_damage)}",
            p75=f"{int(p75_boss_damage)}",
        ),
        SimAnalysis(
            title="초당 피해량",
            value=f"{int(total_normal_damage / 60)}",
            min=f"{int(min_normal_damage / 60)}",
            max=f"{int(max_normal_damage / 60)}",
            std=f"{std_normal_damage / 60:.1f}",
            p25=f"{int(p25_normal_damage / 60)}",
            p50=f"{int(p50_normal_damage / 60)}",
            p75=f"{int(p75_normal_damage / 60)}",
        ),
        SimAnalysis(
            title="총 피해량",
            value=f"{int(total_normal_damage)}",
            min=f"{int(min_normal_damage)}",
            max=f"{int(max_normal_damage)}",
            std=f"{std_normal_damage:.1f}",
            p25=f"{int(p25_normal_damage)}",
            p50=f"{int(p50_normal_damage)}",
            p75=f"{int(p75_normal_damage)}",
        ),
    ]

    return SimResult(
        powers=powers,
        analysis=analysis,
        deterministic_boss_attacks=boss_attacks,
        random_boss_attacks=random_boss_attacks,
    )


def _get_skill_sequence() -> tuple[EquippedSkillRef, ...]:
    """
    스킬 사용 순서 반환
    """

    skill_ref_map: dict[str, EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_ref_map(
            app_state.macro.current_server
        )
    )
    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )
    skill_sequence: list[EquippedSkillRef] = []

    for target_priority in range(1, len(placed_refs) + 1):
        for skill_id, setting in app_state.macro.current_preset.usage_settings.items():
            if setting.priority == target_priority:
                skill_ref: EquippedSkillRef | None = skill_ref_map.get(skill_id)
                if skill_ref is not None:
                    skill_sequence.append(skill_ref)

    for skill_ref in placed_refs:
        if skill_ref not in skill_sequence:
            skill_sequence.append(skill_ref)

    return tuple(skill_sequence)


def _get_task_list(
    prepared_skills: set[EquippedSkillRef],
    link_skills_requirements: list[list[EquippedSkillRef]],
    using_link_skills: list[list[EquippedSkillRef]],
) -> list[EquippedSkillRef]:

    task_list: list[EquippedSkillRef] = []

    prepared_link_skill_indices: list[int] = get_prepared_link_skill_indices(
        prepared_skills=prepared_skills,
        link_skills_requirements=link_skills_requirements,
    )

    skill_sequence: tuple[EquippedSkillRef, ...] = _get_skill_sequence()

    if prepared_link_skill_indices:
        for skill_ref in using_link_skills[prepared_link_skill_indices[0]]:
            prepared_skills.discard(skill_ref)
            task_list.append(skill_ref)

        return task_list

    link_skill_reqs: list[EquippedSkillRef] = [
        skill_ref
        for requirements in link_skills_requirements
        for skill_ref in requirements
    ]

    for skill_ref in skill_sequence:
        skill_id: str = app_state.macro.current_preset.skills.get_placed_skill_id(
            skill_ref,
        )
        if not skill_id:
            continue

        if (
            skill_ref in prepared_skills
            and skill_ref in link_skill_reqs
            and app_state.macro.current_preset.usage_settings[skill_id].use_alone
        ):
            task_list.append(skill_ref)
            prepared_skills.discard(skill_ref)

            return task_list

        elif (
            skill_ref in prepared_skills
            and skill_ref not in link_skill_reqs
            and app_state.macro.current_preset.usage_settings[skill_id].use_skill
        ):
            task_list.append(skill_ref)
            prepared_skills.discard(skill_ref)

            return task_list

    return task_list


# 쿨타임 지난 스킬들 업데이트
def _update_skill_cooltimes(
    placed_refs: list[EquippedSkillRef],
    skill_cooltime_timers_ms: dict[EquippedSkillRef, int],
    skill_cooltimes_ms: dict[EquippedSkillRef, int],
    elapsed_time_ms: int,
    prepared_skills: set[EquippedSkillRef],
) -> None:
    """
    쿨타임이 지난 스킬들을 준비된 스킬 리스트에 추가
    """

    for skill_ref in placed_refs:
        if (
            skill_ref not in prepared_skills
            and (elapsed_time_ms - skill_cooltime_timers_ms[skill_ref])
            >= skill_cooltimes_ms[skill_ref]
        ):
            prepared_skills.add(skill_ref)


def get_simulated_skills(
    cooltimeReduce: int | float,
    skills_info_tuple: tuple[tuple[str, tuple[bool, bool, int]], ...],
) -> tuple[list[SimAttack], list[SimBuff]]:
    """
    사용한 스킬 목록을 반환하는 함수
    스킬 쿨타임 감소 스텟을 증가시키는 스킬이 있을 수 있기 때문에 로직을 수정해야함
    실제와 다른 경우가 있어서 시뮬레이션 진행할 때 옵션 추가해야함
    """

    # 스킬 세부사항 모으기
    attack_details: list[SimAttack] = []
    buff_details: list[SimBuff] = []

    # 평타 (임시)1초마다 사용
    default_delay_ms: int = 1000
    delay_ms: int = int((100 - cooltimeReduce) * 0.01 * default_delay_ms)

    # 평타 스킬 ID
    basic_attack_skill_id: str = get_builtin_skill_id(
        app_state.macro.current_server.id, "평타"
    )
    for t in range(0, 60000, delay_ms):
        attack_details.append(
            SimAttack(
                skill_id=basic_attack_skill_id,
                time=round(t * 0.001, 2),
                damage=1.0,
            )
        )

    placed_refs: list[EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_refs(
            app_state.macro.current_server
        )
    )

    if not placed_refs:
        return attack_details, buff_details

    prepared_skills: set[EquippedSkillRef] = set(placed_refs)
    skill_ref_map: dict[str, EquippedSkillRef] = (
        app_state.macro.current_preset.skills.get_placed_skill_ref_map(
            app_state.macro.current_server
        )
    )
    using_link_skills: list[list[EquippedSkillRef]] = [
        [skill_ref_map[name] for name in link_skill.skills]
        for link_skill in app_state.macro.current_preset.link_skills
        if link_skill.use_type == LinkUseType.AUTO
        and all(name in skill_ref_map for name in link_skill.skills)
    ]
    link_skills_requirements: list[list[EquippedSkillRef]] = [
        [skill_ref for skill_ref in link_skill] for link_skill in using_link_skills
    ]
    skill_cooltime_timers_ms: dict[EquippedSkillRef, int] = {
        skill_ref: 0 for skill_ref in placed_refs
    }
    skill_cooltimes_ms: dict[EquippedSkillRef, int] = {
        skill_ref: int(
            app_state.macro.current_server.skill_registry.get(
                app_state.macro.current_preset.skills.get_placed_skill_id(skill_ref)
            ).cooltime
            * (100 - app_state.macro.current_cooltime_reduction)
            * 10
        )
        for skill_ref in placed_refs
    }

    # 스크롤 레벨
    # scroll_levels: dict[str, int] = {
    #     scroll_id: level for current preset
    # }

    task_list: list[EquippedSkillRef] = []
    used_skills: list[SimSkill] = []
    elapsed_time_ms: int = 0

    while elapsed_time_ms < 60000:
        if not task_list:
            _update_skill_cooltimes(
                placed_refs=placed_refs,
                skill_cooltime_timers_ms=skill_cooltime_timers_ms,
                skill_cooltimes_ms=skill_cooltimes_ms,
                elapsed_time_ms=elapsed_time_ms,
                prepared_skills=prepared_skills,
            )

            task_list = _get_task_list(
                prepared_skills=prepared_skills,
                link_skills_requirements=link_skills_requirements,
                using_link_skills=using_link_skills,
            )

        if task_list:
            skill_ref: EquippedSkillRef = task_list.pop(0)
            skill_id: str = app_state.macro.current_preset.skills.get_placed_skill_id(
                skill_ref,
            )

            used_skills.append(SimSkill(skill_id=skill_id, time=elapsed_time_ms))

            skill_cooltime_timers_ms[skill_ref] = elapsed_time_ms
            elapsed_time_ms += int(app_state.macro.current_delay)

        else:
            waiting_refs: list[EquippedSkillRef] = [
                skill_ref
                for skill_ref in placed_refs
                if skill_ref not in prepared_skills
            ]
            if not waiting_refs:
                break

            next_cooltime_ms: int = min(
                skill_cooltimes_ms[skill_ref]
                - (elapsed_time_ms - skill_cooltime_timers_ms[skill_ref])
                for skill_ref in waiting_refs
            )

            elapsed_time_ms += next_cooltime_ms

    for used_skill in used_skills:
        used_skill.time = round(used_skill.time * 0.001, 2)

    skills_effects: dict[str, list[LevelEffect]] = {
        skill_id: app_state.macro.current_server.skill_registry.get(skill_id).levels[1]
        for skill_id in app_state.macro.current_preset.skills.get_placed_skill_ids()
    }

    for skill in used_skills:
        effects: list[LevelEffect] = skills_effects[skill.skill_id]

        for effect in effects:
            if isinstance(effect, DamageEffect):
                attack: SimAttack = SimAttack(
                    skill_id=skill.skill_id,
                    time=round(skill.time + effect.time, 2),
                    damage=effect.damage,
                )

                attack_details.append(attack)

            elif isinstance(effect, BuffEffect):
                buff: SimBuff = SimBuff(
                    start_time=round(skill.time + effect.time, 2),
                    end_time=round(skill.time + effect.time + effect.duration, 2),
                    stat=effect.stat,
                    value=effect.value,
                    skill_id=skill.skill_id,
                )

                buff_details.append(buff)

    attack_details.sort(key=lambda x: x.time)
    buff_details.sort(key=lambda x: x.start_time)

    return attack_details, buff_details
