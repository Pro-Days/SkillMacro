from __future__ import annotations

import random
from functools import lru_cache
from typing import TYPE_CHECKING

from app.scripts.custom_classes import (
    SimAnalysis,
    SimAttack,
    SimBuff,
    SimResult,
    SimSkill,
    SimSkillApplyDelay,
    Stats,
)
from app.scripts.misc import get_skill_details
from app.scripts.run_macro import add_task_list, init_macro

if TYPE_CHECKING:
    from app.scripts.shared_data import SharedData


def get_req_stats(
    shared_data: SharedData, powers: list[float], stat_type: str
) -> list[str]:
    """
    목표 전투력까지 필요한 스탯 반환
    """

    req_stats: list[str] = [
        calculate_req_stat(
            shared_data=shared_data, power=powers[i], stat_type=stat_type, power_num=i
        )
        for i in range(4)
    ]

    return req_stats


def calculate_req_stat(
    shared_data: SharedData, power: float, stat_type: str, power_num: int
) -> str:
    """
    목표 전투력까지 필요한 스탯 계산
    """

    def is_stat_valid(stat: int | float) -> bool:
        """
        스탯이 유효 범위 내에 있는지 확인
        """

        return (
            shared_data.STAT_RANGES[stat_type][0]
            <= stat
            <= shared_data.STAT_RANGES[stat_type][1]
        )

    stats: Stats = shared_data.info_stats.copy()
    base_stat: int | float = shared_data.info_stats.get_stat_from_name(stat=stat_type)

    # 현재 전투력 계산
    current_power: float = detSimulate(
        shared_data=shared_data,
        stats=stats,
        sim_details=shared_data.info_sim_details,
    ).powers[power_num]

    # 스탯을 증가시키며 최대 범위 알아내기
    low: int | float = 0
    high: int | float = 1
    step: int = 1

    # num으로 무한루프 방지
    num: int = 0
    while current_power < power:
        # 스탯이 유효 범위 내에 있지 않으면 0 반환
        if not is_stat_valid(stat=base_stat + low):
            return "0"

        if num == 10:
            # 10번 반복했는데도 범위를 찾지 못했다면 실패
            return "0"

        # 스탯 증가
        stats.set_stat_from_name(stat=stat_type, value=base_stat + high)

        # 전투력 계산
        current_power = detSimulate(
            shared_data=shared_data,
            stats=stats,
            sim_details=shared_data.info_sim_details,
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
        if not is_stat_valid(stat=base_stat + low):
            return "0"

        mid: float = (low + high) * 0.5
        stats.set_stat_from_name(stat=stat_type, value=base_stat + mid)

        # print(stats)

        # 전투력 계산
        current_power = detSimulate(
            shared_data=shared_data,
            stats=stats,
            sim_details=shared_data.info_sim_details,
        ).powers[power_num]

        # print(f"{low=}, {high=}, {mid=}")
        # print(f"{current_power=}, {power=}")

        if current_power < power:
            low = mid
        else:
            high = mid

        num += 1

    # print("\n")
    return f"{(low + high) * 0.5:.1f}"


def execute_simulation(
    shared_data: SharedData,
    attack_details: list[SimAttack],
    buff_details: list[SimBuff],
    stats: Stats,
    is_boss: bool,
    mob_naegong: int,
    deterministic: bool = False,
) -> list[SimAttack]:
    """
    시간별 가한 데미지 계산
    """

    # 현재 상태 정보 가져오기
    def get_current_stat(now: float, buff_list: list[SimBuff]) -> Stats:
        # 현재 상태를 복사: dataclass replace 사용
        current_stats: Stats = stats.copy()

        # 현재 시간에 적용되는 버프를 찾아서 상태에 반영
        for buff in buff_list:
            if buff.start_time <= now <= buff.end_time:
                current_stats.apply_buff(buff=buff)

        return current_stats

    def get_naegong_coef(stats: Stats) -> float:
        # 내공 차이 계산
        diff: int = mob_naegong - stats.NAEGONG

        # 내공 차이에 해당하는 배율 반환
        for (low, high), multiplier in shared_data.NAEGONG_DIFF.items():
            if low <= diff <= high:
                return multiplier

        # 범위에 해당하지 않으면 0.0
        return 0.0

    def get_damage(stats: Stats) -> float:
        # print(stats[0])

        # 기본 데미지 계산
        damage: float = (
            stats.ATK  # 공격력
            * (stats.STR + stats.INT)  # 근력 + 지력
            * (1 + stats.PWR * 0.01)  # 파괴력
            * get_naegong_coef(stats=stats)
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
            key: str = buff.skill_name

            # 해당 키가 없으면 새로 생성
            if key not in grouped:
                grouped[key] = []

            # 버프의 시작 시간과 종료 시간을 리스트로 추가
            grouped[key].append(buff)

        # 각 그룹의 겹치는 구간 병합
        merged_buffs: list[SimBuff] = []
        for skill_name, buffs in grouped.items():
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
        current_stats: Stats = get_current_stat(now=attack.time, buff_list=buff_info)

        damage: float = get_damage(stats=current_stats) * attack.damage

        new_attack: SimAttack = SimAttack(
            skill_name=attack.skill_name,
            time=attack.time,
            damage=damage,
        )

        attacks.append(new_attack)

    # if deterministic:
    #     pprint(attacks)
    return attacks


# 최소, 최대, 평균, 표준편차 등을 계산하는 확률론적 시뮬레이션
def randSimulate(
    shared_data: SharedData,
    stats: Stats,
    sim_details: dict[str, int],
) -> SimResult:
    # 시뮬레이션 세부정보를 해시 가능하게 만듦
    sim_details_tuple: tuple = tuple(sorted(sim_details.items()))
    # 스킬 레벨 정보를 추가
    skill_levels_tuple: tuple = tuple(sorted(shared_data.info_skill_levels.items()))

    return simulateMacro(
        shared_data=shared_data,
        stats=stats,
        sim_details_tuple=sim_details_tuple,
        skill_levels_tuple=skill_levels_tuple,
        random_seed=random.random(),
    )


# 전투력 계산을 위한 결정론적 시뮬레이션
# 캐시를 사용하여 성능 향상
def detSimulate(
    shared_data: SharedData,
    stats: Stats,
    sim_details: dict[str, int],
    skill_levels: dict[str, int] | None = None,
) -> SimResult:

    @lru_cache(maxsize=1024)
    def _run(
        sim_details_tuple: tuple[tuple[str, int]],
        skill_levels_tuple: tuple[tuple[str, int]],
    ) -> SimResult:
        return simulateMacro(
            shared_data=shared_data,
            stats=stats,
            sim_details_tuple=sim_details_tuple,
            skill_levels_tuple=skill_levels_tuple,
            random_seed=1.0,
        )

    # 시뮬레이션 세부정보를 튜플로 변환해서 해시 가능하게 만듦
    sim_details_tuple: tuple = tuple(sorted(sim_details.items()))
    # 스킬 레벨 정보를 추가
    if skill_levels is not None:
        skill_levels_tuple: tuple = tuple(sorted(skill_levels.items()))
    else:
        skill_levels_tuple: tuple = tuple(sorted(shared_data.info_skill_levels.items()))

    return _run(sim_details_tuple, skill_levels_tuple)


# 61초 -> 60초로 변경, 처음 0일 때 총 데미지를 0으로 설정
def simulateMacro(
    shared_data: SharedData,
    stats: Stats,
    sim_details_tuple: tuple[tuple[str, int]],
    skill_levels_tuple: tuple[tuple[str, int]],
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
    attack_details, buff_details = getSimulatedSKillList(
        shared_data=shared_data,
        cooltimeReduce=stats.ATK_SPD,
        skill_levels_tuple=skill_levels_tuple,
    )

    # print(attack_details)
    # print(buff_details)

    # 공격 시뮬레이션 실행
    boss_attacks: list[SimAttack] = execute_simulation(
        shared_data=shared_data,
        attack_details=attack_details,
        buff_details=buff_details,
        stats=stats,
        is_boss=True,
        mob_naegong=sim_details["BOSS_NAEGONG"],
        deterministic=True,
    )
    normal_attacks: list[SimAttack] = execute_simulation(
        shared_data=shared_data,
        attack_details=attack_details,
        buff_details=buff_details,
        stats=stats,
        is_boss=False,
        mob_naegong=sim_details["NORMAL_NAEGONG"],
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
        total_boss_damage * shared_data.COEF_BOSS_DMG,
        # 일반데미지
        total_normal_damage * shared_data.COEF_NORMAL_DMG,
        # 보스
        total_boss_damage
        * shared_data.COEF_BOSS_DMG
        * (stats.HP + damage_reduction * 5 + recovery * 5)
        / (1 - stats.DODGE * 0.01)
        * shared_data.COEF_BOSS,
        # 일반
        total_normal_damage
        * shared_data.COEF_NORMAL_DMG
        * (1 + stats.LUK * 0.01)
        * (1 + stats.STATUS_RES * 0.001)
        * (1 + stats.EXP * 0.01)
        * shared_data.COEF_NORMAL,
    ]

    # 전투력만 반환
    if random_seed == 1.0:
        return SimResult(powers=powers)

    # start_time = time.time()

    # 1000회 시뮬레이션 실행
    # 1000회일 경우 멀티프로세싱보다 단일쓰레드에서 실행하는 것이 빠름
    random_boss_attacks: list[list[SimAttack]] = [
        execute_simulation(
            shared_data=shared_data,
            attack_details=attack_details,
            buff_details=buff_details,
            stats=stats,
            is_boss=True,
            mob_naegong=sim_details["BOSS_NAEGONG"],
        )
        for _ in range(1000)
    ]
    random_normal_attacks: list[list[SimAttack]] = [
        execute_simulation(
            shared_data=shared_data,
            attack_details=attack_details,
            buff_details=buff_details,
            stats=stats,
            is_boss=False,
            mob_naegong=sim_details["NORMAL_NAEGONG"],
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


def getSimulatedSKillList(
    shared_data: SharedData,
    cooltimeReduce: int | float,
    skill_levels_tuple: tuple[tuple[str, int]],
) -> tuple[list[SimAttack], list[SimBuff]]:
    """
    사용한 스킬 목록을 반환하는 함수
    스킬 쿨타임 감소 스텟을 증가시키는 스킬이 있을 수 있기 때문에 로직을 수정해야함.
    실제와 다른 경우가 있어서 시뮬레이션 진행할 때 옵션 추가해야함
    """

    def use(skill, additional_time=0) -> None:
        """
        스킬 사용 함수
        """

        used_skills.append(
            SimSkill(skill=skill, time=elapsed_time + additional_time, combo=0)
        )

        skill_apply_delay.skill = skill
        skill_apply_delay.delay = additional_time
        # availableSkillCount[skill] -= 1

        # print(f"{(elapsedTime + additionalTime) * 0.001:.3f} - {skill}")

    # 시뮬레이션 초기 설정
    init_macro(shared_data=shared_data)

    # 시뮬레이션 변수 초기화

    # 지난 시간 (ms)
    elapsed_time: int = 0
    # 다음 테스크 실행까지 대기 시간 (ms)
    delay_to_next_task: int = 0

    # availableSkillCount -= 1까지 남은 시간 (doClick을 할때 delay가 있기 때문)
    # skill = None, delay = None 으로 시작
    skill_apply_delay: SimSkillApplyDelay = SimSkillApplyDelay()

    used_skills: list[SimSkill] = []

    # 스킬 남은 쿨타임 : [0, 0, 0, 0, 0, 0]
    # ms 단위
    # isUsed이면 shared_data.unitTime(x1000)씩 증가, 쿨타임이 지나면 0으로 초기화
    skill_cooltime_timers: list[int] = [0] * shared_data.USABLE_SKILL_COUNT[
        shared_data.server_ID
    ]

    # 스킬 사용 가능 횟수 : [3, 2, 2, 1, 3, 3]
    available_skill_counts: list[int] = [
        (
            get_skill_details(
                shared_data=shared_data, skill_name=shared_data.equipped_skills[i]
            )["max_combo_count"]
            if shared_data.equipped_skills[i]
            else 0
        )
        for i in range(shared_data.USABLE_SKILL_COUNT[shared_data.server_ID])
    ]

    # 스킬 레벨
    skill_levels: dict[str, int] = dict(skill_levels_tuple)

    # 60초 미만 시뮬레이션
    # 0초를 포함하기 때문
    while elapsed_time < 60000:
        add_task_list(shared_data)

        # 스킬 사용
        # 태스크 리스트가 있고 남은 지연 시간이 없으면
        if shared_data.task_list and not delay_to_next_task:
            # 스킬 슬롯
            slot: int = shared_data.task_list.pop(0)

            # 스킬 사용 시 클릭 여부
            is_click: bool = get_skill_details(
                shared_data=shared_data, skill_name=shared_data.equipped_skills[slot]
            )["is_casting"]

            # 스킬 슬롯에 따라 다르게 사용
            if shared_data.selected_item_slot != slot:
                if is_click:  # press -> delay -> click => use
                    use(skill=slot, additional_time=shared_data.delay)
                    shared_data.selected_item_slot = slot

                    delay_to_next_task = shared_data.delay * 2

                else:  # press => use
                    use(skill=slot)
                    shared_data.selected_item_slot = slot

                    delay_to_next_task = shared_data.delay

            else:
                if is_click:  # click => use
                    use(skill=slot)

                    delay_to_next_task = shared_data.delay

                else:  # press => use
                    use(skill=slot)

                    delay_to_next_task = shared_data.delay

        # 스킬 쿨타임
        for slot in range(shared_data.USABLE_SKILL_COUNT[shared_data.server_ID]):  # 0~6
            # 스킬이 장착되어있지 않으면 continue
            if not shared_data.equipped_skills[slot]:
                continue

            # 스킬 사용해서 쿨타임 기다리는 중이면
            if (
                available_skill_counts[slot]
                < get_skill_details(
                    shared_data=shared_data,
                    skill_name=shared_data.equipped_skills[slot],
                )["max_combo_count"]
            ):
                # 쿨타임 타이머 UNIT_TIME(1tick) 100배 만큼 증가
                skill_cooltime_timers[slot] += int(shared_data.UNIT_TIME * 100)

                # 쿨타임이 지나면
                if skill_cooltime_timers[slot] >= int(
                    get_skill_details(
                        shared_data=shared_data,
                        skill_name=shared_data.equipped_skills[slot],
                    )["cooltime"]
                    * (100 - cooltimeReduce)
                ):
                    # 대기열에 추가
                    shared_data.prepared_skills[2].append(slot)
                    # 사용 가능 횟수 증가
                    available_skill_counts[slot] += 1

                    skill_cooltime_timers[slot] = 0  # 쿨타임 초기화
                    # print(f"{(elapsedTime) * 0.001:.3f} - {skill} 쿨타임")

        # 스킬 사용 대기 시간이 지나면
        if skill_apply_delay.delay == 0 and skill_apply_delay.skill is not None:
            # 준비된 스킬 개수 1 감소
            available_skill_counts[skill_apply_delay.skill] -= 1
            # 스킬 사용 대기 시간 초기화
            skill_apply_delay.clear()

        # 스킬 사용 대기 시간이 남아있으면
        if skill_apply_delay.delay is not None:
            # 스킬 사용 대기 시간 감소 (최소 0)
            skill_apply_delay.delay = max(
                0, skill_apply_delay.delay - int(shared_data.UNIT_TIME * 1000)
            )

        # 다음 테스크까지 대기 시간 감소
        delay_to_next_task = max(
            0, delay_to_next_task - int(shared_data.UNIT_TIME * 1000)
        )
        # 현재 시간 증가
        elapsed_time += int(shared_data.UNIT_TIME * 1000)

    used_skills = [skill for skill in used_skills if skill.time < 60000]

    # 1초 이내에 같은 스킬 사용 => 콤보
    for num, skill in enumerate(used_skills):
        # used_skills[num]의 콤보를 변경
        # 이전에 사용한 스킬이 num 스킬의 이전 콤보인지 확인
        # 직전 스킬부터 시작해서 1초 이내에 사용한 스킬인지 확인함.
        # 1초는 임시로 설정한 값이며, 실제 서버에서의 콤보 시간을 설정해야 함.

        # 최대 콤보 수 미리 저장
        max_combo_count: int = get_skill_details(
            shared_data=shared_data,
            skill_name=shared_data.equipped_skills[skill.skill],
        )["max_combo_count"]

        for used_skill in reversed(used_skills[:num]):
            # 1초 이내에 사용한 스킬이 아니면 중단
            if skill.time - used_skill.time > 1000:
                break

            if (
                # 스킬이 같고
                used_skill.skill == skill.skill
                # 콤보가 최대 콤보 수보다 작으면
                and used_skill.combo < max_combo_count
            ):
                # 콤보 증가
                used_skills[num].combo = used_skill.combo + 1
                break

    # 평타 추가

    # 평타 횟수
    num = 0
    # 평타는 1초마다 사용
    # 1초는 임시로 설정한 값이며, 실제 서버에서의 콤보 시간을 설정해야 함.
    # ms 단위로 사용
    delay: int = int((100 - cooltimeReduce) * 10 * 1)
    for t in range(0, 60000, delay):
        # 평타는 스킬 번호 -1로 설정
        used_skills.append(SimSkill(skill=-1, time=t, combo=0))

    # 시간 단위를 1초로 변경
    # 반올림은 0.01초 단위로
    for used_skill in used_skills:
        used_skill.time = round(used_skill.time * 0.001, 2)

    # 스킬 세부사항 모으기
    attack_details: list[SimAttack] = []
    buff_details: list[SimBuff] = []

    for skill in used_skills:
        # 평타
        if skill.skill == -1:
            attack_details.append(
                SimAttack(
                    skill_name="평타",
                    time=skill.time,
                    damage=1.0,
                )
            )
            continue

        # 스킬 효과: 공격 / 버프
        skill_effects: dict = get_skill_details(
            shared_data=shared_data,
            skill_name=shared_data.equipped_skills[skill.skill],
        )["levels"][str(skill_levels[shared_data.equipped_skills[skill.skill]])][
            "combos"
        ][
            skill.combo
        ][
            "effects"
        ]

        # 각 effect에 대해
        # 공격 효과와 버프 효과를 구분하여 처리
        for effect in skill_effects:
            # 공격
            if effect["type"] == "attack":
                attack: SimAttack = SimAttack(
                    skill_name=shared_data.equipped_skills[skill.skill],
                    time=round(skill.time + effect["time"], 2),
                    damage=effect["value"],
                )

                attack_details.append(attack)

            # 버프
            else:
                buff: SimBuff = SimBuff(
                    start_time=round(skill.time + effect["time"], 2),
                    end_time=round(skill.time + effect["time"] + effect["duration"], 2),
                    stat=effect["stat"],
                    value=effect["value"],
                    skill_name=shared_data.equipped_skills[skill.skill],
                )

                buff_details.append(buff)

    # 시간순으로 정렬
    attack_details.sort(key=lambda x: x.time)
    buff_details.sort(key=lambda x: x.start_time)

    return attack_details, buff_details
