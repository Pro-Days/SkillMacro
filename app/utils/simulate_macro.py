import random
import time
from functools import lru_cache
from .run_macro import initMacro, addTaskList


def getRequiredStat(shared_data, powers, stat_num):
    reqStats = []
    reqStats.append(calculateRequiredStat(shared_data, powers[0], stat_num, 0))
    reqStats.append(calculateRequiredStat(shared_data, powers[1], stat_num, 1))
    reqStats.append(calculateRequiredStat(shared_data, powers[2], stat_num, 2))
    reqStats.append(calculateRequiredStat(shared_data, powers[3], stat_num, 3))

    return reqStats


def calculateRequiredStat(shared_data, power, stat_num, power_num):
    def checkInput(stat, stat_num) -> bool:
        if shared_data.STAT_RANGE_LIST[stat_num][0] <= stat:
            if shared_data.STAT_RANGE_LIST[stat_num][1] == None:
                return True
            else:
                if stat <= shared_data.STAT_RANGE_LIST[stat_num][1]:
                    return True
                return False
        return False

    constants = (
        shared_data.SKILL_COMBO_COUNT_LIST,
        shared_data.serverID,
        shared_data.jobID,
        shared_data.selectedSkillList,
        shared_data.SKILL_ATTACK_DATA,
        shared_data.NAEGONG_DIFF,
        shared_data.COEF_BOSS_DMG,
        shared_data.COEF_NORMAL_DMG,
        shared_data.COEF_BOSS,
        shared_data.COEF_NORMAL,
    )

    stats = shared_data.info_stats.copy()
    baseStat = shared_data.info_stats[stat_num]
    current_power = simulateMacro(
        shared_data, tuple(stats), tuple(shared_data.info_skills), tuple(shared_data.info_simInfo), 1
    )[power_num]

    # 1씩 증가시키며 범위 알아내기
    low, high = 0, 1
    step = 1
    num = 0
    stime = time.time()
    while current_power < power and num < 10:
        if not checkInput(baseStat + low, stat_num):
            return "0"
        stats[stat_num] = baseStat + high
        if stat_num == 12:
            stats[stat_num] = int(stats[stat_num])

        current_power = simulateMacro(
            shared_data, tuple(stats), tuple(shared_data.info_skills), tuple(shared_data.info_simInfo), 1
        )[power_num]

        if current_power >= power:
            break

        # print(f"{low=}, {high=}, {step=}")

        low = high
        high += step
        step *= 2
        num += 1

    if num == 10:
        return "0"

    # 범위 내에서 이분탐색
    epsilon = 0.05
    num = 0
    while high - low > epsilon and num < 15:
        if not checkInput(baseStat + low, stat_num):
            return "0"
        mid = (low + high) * 0.5
        stats[stat_num] = baseStat + mid
        if stat_num == 12:
            stats[stat_num] = int(stats[stat_num])
        # print(tuple(stats), tuple(shared_data.info_skills), tuple(shared_data.info_simInfo))
        current_power = simulateMacro(
            shared_data, tuple(stats), tuple(shared_data.info_skills), tuple(shared_data.info_simInfo), 1
        )[power_num]

        # print(f"{low=}, {high=}, {mid=}")

        if current_power < power:
            low = mid
        else:
            high = mid

        num += 1

    # print("\n")
    return f"{(low + high) * 0.5:.1f}"


def runSimul(attackDetails, buffDetails, stats, boss, simInfo, naegongDiff, deterministic=False):
    def getStatus(stats, nowTime, buff_list):
        status = list(stats).copy()
        for buff in buff_list:
            if buff[0] <= nowTime <= buff[1]:
                status[buff[2]] += buff[3]
        return status

    def getNaegongDiff(stats, naegong, naegongDiff):
        diff = naegong - stats[12]
        for (low, high), multiplier in naegongDiff.items():
            if low <= diff <= high:
                return multiplier

    def getDMG(stats, boss, naegong, naegongDiff, deterministic):
        # print(stats[0])
        dmg = (
            stats[0]  # 공격력
            * (stats[3] + stats[4])  # 근력 + 지력
            * (1 + stats[2] * 0.01)  # 파괴력
            * getNaegongDiff(stats, naegong, naegongDiff)
            * ((1 + stats[8] * 0.01) if boss else 1)
            * 0.01  # 보정계수
        )

        if deterministic:
            crit_prob = stats[6] if stats[6] <= 100 else 100
            dmg *= 1 + crit_prob * stats[7] * 0.0001
            dmg *= 1.1  # 최소, 최대데미지 중간
            return dmg

        dmg *= random.uniform(1, 1.2)  # 최소, 최대데미지
        return dmg * (1 + stats[7] * 0.01) if random.random() < stats[6] * 0.01 else dmg

    def merge_buff(data):
        # 지속 시간이 끝나는 시간 추가
        intervals = [
            [start, round(start + duration, 2), buff_type, value]
            for start, buff_type, value, duration in data
        ]

        # 종류와 값을 기준으로 그룹화
        grouped = {}
        for start, end, buff_type, value in intervals:
            key = (buff_type, value)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append([start, end])

        # 각 그룹의 겹치는 구간 병합
        merged_intervals = []
        for (buff_type, value), times in grouped.items():
            times.sort()  # 시작 시간을 기준으로 정렬
            merged = [times[0]]
            for current in times[1:]:
                prev = merged[-1]
                if current[0] <= prev[1]:  # 겹침 확인
                    prev[1] = max(prev[1], current[1])  # 병합
                else:
                    merged.append(current)
            for start, end in merged:
                merged_intervals.append((start, end, buff_type, value))

        # 시작 시간 기준으로 정렬
        merged_intervals.sort()
        return tuple(merged_intervals)

    buffInfo = merge_buff(buffDetails)  # [[start, type, value, duration], ...]
    attacks = []  # [type, time, damage]
    naegong = simInfo[1] if boss else simInfo[0]
    ## 시뮬레이션 시작
    for attack in attackDetails:
        status = getStatus(stats, attack[1], buffInfo)
        dmg = round(getDMG(status, boss, naegong, naegongDiff, deterministic) * attack[2], 5)
        attacks.append([attack[0], attack[1], dmg])

    # if deterministic:
    #     pprint(attacks)
    return attacks


def runSimulBatch(batch_args):
    return [runSimul(*args) for args in batch_args]


@lru_cache
def simulateMacro(shared_data, stats: tuple, skillLevels: tuple, simInfo: tuple, randomSeed):
    def calculate_percentile(data, percentile):
        data_sorted = sorted(data)
        rank = (percentile * 0.01) * (len(data) - 1) + 1
        lower_index = int(rank) - 1
        fraction = rank - int(rank)
        if lower_index + 1 < len(data):
            result = data_sorted[lower_index] + fraction * (
                data_sorted[lower_index + 1] - data_sorted[lower_index]
            )
        else:
            result = data_sorted[lower_index]
        return result

    def calculate_std(data):
        # Step 1: 평균 계산
        mean = sum(data) / len(data)

        # Step 2: 각 데이터에서 평균을 뺀 제곱의 합 계산
        squared_differences = [(x - mean) ** 2 for x in data]

        # Step 3: 분산 계산
        variance = sum(squared_differences) / len(data)

        # Step 4: 표준편차 계산
        std_dev = variance**0.5

        return std_dev

    if randomSeed != 1:
        random.seed(randomSeed)
    simulatedSkills = getSimulatedSKillList(shared_data, stats[14])

    # 1초 이내에 같은 스킬 사용 => 콤보
    for num, skill in enumerate(simulatedSkills):
        i = 1
        while (num >= i) and (skill[1] - simulatedSkills[num - i][1] <= 1000):

            if (simulatedSkills[num - i][0] == skill[0]) and (
                simulatedSkills[num - i][2]
                < shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][shared_data.jobID][
                    shared_data.selectedSkillList[skill[0]]
                ]
            ):
                simulatedSkills[num].append(simulatedSkills[num - i][2] + 1)
                break

            i += 1

        # 콤보가 아닌 경우 0번콤보
        if len(simulatedSkills[num]) == 2:
            simulatedSkills[num].append(0)

    # 평타 추가
    num, delay = 0, 1
    while (t := num * (100 - stats[14]) * 10 * delay) <= 61000:
        simulatedSkills.append([-1, t])
        num += 1

    # 시간 단위를 1초로 변경
    for i in range(len(simulatedSkills)):
        simulatedSkills[i][1] = round(simulatedSkills[i][1] * 0.001, 2)

    # 스킬 세부사항 모으기
    attackDetails = []  # [스킬 번호, 시간, 데미지]
    buffDetails = []  #
    for attack in simulatedSkills:
        # 평타
        if attack[0] == -1:
            attackDetails.append(tuple(attack + [1.0]))
            continue

        # 스킬
        skillLevels = [0] * 8  # temp: shared_data.info_skills -> info_skills = 0 * 8

        # [[0.0, [0, 0.5]], [0.1, [0, 0.5]], [0.2, [0, 0.5]], [0.3, [0, 0.5]], [0.4, [0, 0.5]]]
        skills = shared_data.SKILL_ATTACK_DATA[shared_data.serverID][shared_data.jobID][
            shared_data.selectedSkillList[attack[0]]
        ][skillLevels[shared_data.selectedSkillList[attack[0]]]][attack[2]]

        for skill in skills:
            # [time, [type(0: damage, 1: buff), [buff_type, buff_value, buff_duration] or damage_value]]
            if skill[1][0] == 0:  # 공격
                attackDetails.append(
                    (
                        attack[0],  # 스킬 번호
                        round(attack[1] + skill[0], 2),  # 시간
                        skill[1][1],  # 데미지
                    )
                )
            else:  # 버프
                buffDetails.append(
                    (
                        round(attack[1] + skill[0], 2),  # 시간
                        skill[1][1][0],  # 버프 종류
                        skill[1][1][1],  # 버프 값
                        skill[1][1][2],  # 버프 지속시간
                    )
                )

    # 시간순으로 정렬
    attackDetails.sort(key=lambda x: x[1])
    buffDetails.sort(key=lambda x: x[0])
    buffDetails = tuple(buffDetails)
    naegongDiff = shared_data.NAEGONG_DIFF

    # print(attackDetails)
    # print(buffDetails)

    ## 전투력
    # 기본데미지 = 공격력 * (근력 + 지력) * (1 + 파괴력 * 0.01) * 내공계수
    # 0공, 1방, 2파괴력, 3근력, 4지력, 5경도, 6치확, 7치뎀, 8보뎀, 9명중, 10회피, 11상태이상저항, 12내공, 13체력, 14공속, 15포션회복, 16운, 17경험치
    boss_attacks = runSimul(attackDetails, buffDetails, stats, True, simInfo, naegongDiff, deterministic=True)
    normal_attacks = runSimul(
        attackDetails, buffDetails, stats, False, simInfo, naegongDiff, deterministic=True
    )
    sum_BossDMG = sum([i[2] for i in boss_attacks])
    sum_NormalDMG = sum([i[2] for i in normal_attacks])

    # 데미지감소 = 방어력 * 0.5 + 체력 * 경도 * 0.001
    dmgReduction = stats[1] * 0.5 + stats[13] * stats[5] * 0.001
    # dmgReduction = stats[1] * 0.8 + stats[13] * stats[5] * 0.0004
    # 초당 회복량 = 체력 * 자연회복 * 0.2 + 포션회복 * 0.5
    recovery = stats[13] * 0.1 * 0.2 + simInfo[2] * (1 + stats[15] * 0.01) * 0.5

    powers = [
        sum_BossDMG * shared_data.COEF_BOSS_DMG,  # 보스데미지
        sum_NormalDMG * shared_data.COEF_NORMAL_DMG,  # 일반데미지
        sum_BossDMG * shared_data.COEF_BOSS_DMG  # 보스데미지
        # * (stats[13] ** 0.5)  # 체력 ** 0.5
        # * (dmgReduction + recovery)  # 뎀감 + 초당회복량 = 초당 버틸 수 있는 체력
        * (
            stats[13] + dmgReduction * 5 + recovery * 5
        )  # 5초마다 한 번씩 피해를 입는다는 가정에서의 버틸 수 있는 체력
        / (1 - stats[10] * 0.01)
        * shared_data.COEF_BOSS,  # 회피
        sum_NormalDMG
        * shared_data.COEF_NORMAL_DMG  # 일반데미지
        * (1 + stats[16] * 0.01)  # 운
        * (1 + stats[11] * 0.001)  # 상태이상저항
        * (1 + stats[17] * 0.01)  # 경험치
        * shared_data.COEF_NORMAL,
    ]
    if randomSeed == 1:
        return powers

    powers = [str(int(i)) for i in powers]

    # start_time = time.time()

    simuls_boss = []
    simuls_normal = []
    for i in range(1000):  # 1000회일 경우 멀티프로세싱보다 단일쓰레드에서 실행하는 것이 빠름
        simuls_boss.append(runSimul(attackDetails, buffDetails, stats, True, simInfo, naegongDiff))
        simuls_normal.append(runSimul(attackDetails, buffDetails, stats, False, simInfo, naegongDiff))

    # iterations = 1000
    # batch_size = 100  # 한번에 처리할 작업 개수
    # num_processes = multiprocessing.cpu_count()

    # boss_args = [(attackDetails, buffDetails, stats, True, simInfo, naegongDiff) for _ in range(iterations)]
    # normal_args = [
    #     (attackDetails, buffDetails, stats, False, simInfo, naegongDiff) for _ in range(iterations)
    # ]

    # # 작업을 배치로 나눔
    # boss_batches = [boss_args[i : i + batch_size] for i in range(0, len(boss_args), batch_size)]
    # normal_batches = [normal_args[i : i + batch_size] for i in range(0, len(normal_args), batch_size)]

    # with multiprocessing.Pool(processes=num_processes) as pool:
    #     simuls_boss = pool.map(runSimulBatch, boss_batches)
    #     simuls_normal = pool.map(runSimulBatch, normal_batches)

    # # Flatten 결과 리스트
    # simuls_boss = [result for batch in simuls_boss for result in batch]
    # simuls_normal = [result for batch in simuls_normal for result in batch]

    # print(f"실행 시간: {time.time() - start_time:.2f}초")

    sums_simulBossDMG = [sum([i[2] for i in j]) for j in simuls_boss]
    sums_simulNormalDMG = [sum([i[2] for i in j]) for j in simuls_normal]

    min_bossDMG = min(sums_simulBossDMG)
    max_bossDMG = max(sums_simulBossDMG)
    std_bossDMG = calculate_std(sums_simulBossDMG)
    p25_bossDMG = calculate_percentile(sums_simulBossDMG, 25)
    p50_bossDMG = calculate_percentile(sums_simulBossDMG, 50)
    p75_bossDMG = calculate_percentile(sums_simulBossDMG, 75)
    min_normalDMG = min(sums_simulNormalDMG)
    max_normalDMG = max(sums_simulNormalDMG)
    std_normalDMG = calculate_std(sums_simulNormalDMG)
    p25_normalDMG = calculate_percentile(sums_simulNormalDMG, 25)
    p50_normalDMG = calculate_percentile(sums_simulNormalDMG, 50)
    p75_normalDMG = calculate_percentile(sums_simulNormalDMG, 75)

    analysis = [
        {
            "title": "초당 보스피해량",
            "number": f"{int(sum_BossDMG / 61)}",
            "min": f"{int(min_bossDMG / 61)}",
            "max": f"{int(max_bossDMG / 61)}",
            "std": f"{std_bossDMG / 61:.1f}",
            "p25": f"{int(p25_bossDMG / 61)}",
            "p50": f"{int(p50_bossDMG / 61)}",
            "p75": f"{int(p75_bossDMG / 61)}",
        },
        {
            "title": "총 보스피해량",
            "number": f"{int(sum_BossDMG)}",
            "min": f"{int(min_bossDMG)}",
            "max": f"{int(max_bossDMG)}",
            "std": f"{std_bossDMG:.1f}",
            "p25": f"{int(p25_bossDMG)}",
            "p50": f"{int(p50_bossDMG)}",
            "p75": f"{int(p75_bossDMG)}",
        },
        {
            "title": "초당 피해량",
            "number": f"{int(sum_NormalDMG / 61)}",
            "min": f"{int(min_normalDMG / 61)}",
            "max": f"{int(max_normalDMG / 61)}",
            "std": f"{std_normalDMG / 61:.1f}",
            "p25": f"{int(p25_normalDMG / 61)}",
            "p50": f"{int(p50_normalDMG / 61)}",
            "p75": f"{int(p75_normalDMG / 61)}",
        },
        {
            "title": "총 피해량",
            "number": f"{int(sum_NormalDMG)}",
            "min": f"{int(min_normalDMG)}",
            "max": f"{int(max_normalDMG)}",
            "std": f"{std_normalDMG:.1f}",
            "p25": f"{int(p25_normalDMG)}",
            "p50": f"{int(p50_normalDMG)}",
            "p75": f"{int(p75_normalDMG)}",
        },
    ]

    return powers, analysis, boss_attacks, simuls_boss


# 매크로 시뮬레이션 => 스킬 리스트
def getSimulatedSKillList(shared_data, cooltimeReduce):
    # 실제와 다른 경우가 있어서 시뮬레이션 진행할 때 옵션 추가해야함
    def use(skill, additionalTime=0):
        usedSkillList.append([skill, (elapsedTime + additionalTime)])

        minusSkillCount[0], minusSkillCount[1] = (skill, additionalTime)
        # availableSkillCount[skill] -= 1

        # print(f"{(elapsedTime + additionalTime) * 0.001:.3f} - {skill}")

    initMacro(shared_data)
    elapsedTime = 0  # 1000배
    simWaitTime = 0  # 다음 테스크 실행까지 대기 시간 (1000배)
    minusSkillCount = [
        None,
        None,
    ]  # availableSkillCount -= 1까지 남은 시간: [skill, time] (doClick을 할때 delay가 있기 때문)
    usedSkillList = []

    # 스킬 남은 쿨타임 : [0, 0, 0, 0, 0, 0]  # 초 1000배
    skillCoolTimers = [0] * shared_data.USABLE_SKILL_COUNT[
        shared_data.serverID
    ]  # isUsed이면 shared_data.unitTime(x1000)씩 증가, 쿨타임이 지나면 0으로 초기화

    # 스킬 사용 가능 횟수 : [3, 2, 2, 1, 3, 3]
    availableSkillCount = [
        shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][shared_data.jobID][
            shared_data.selectedSkillList[i]
        ]
        for i in range(shared_data.USABLE_SKILL_COUNT[shared_data.serverID])
    ]

    while elapsedTime <= 62000:  # 65000
        addTaskList(shared_data)

        # 스킬 사용
        if len(shared_data.taskList) != 0 and simWaitTime == 0:
            skill = shared_data.taskList[0][0]  # skill = slot
            doClick = shared_data.taskList[0][1]  # T, F

            if shared_data.selected_item_slot != skill:
                if doClick:  # press -> delay -> click => use
                    use(skill, shared_data.delay)
                    shared_data.selected_item_slot = skill

                    simWaitTime = shared_data.delay * 2
                else:  # press => use
                    use(skill)
                    shared_data.selected_item_slot = skill

                    simWaitTime = shared_data.delay
            else:
                if doClick:  # click => use
                    use(skill)

                    simWaitTime = shared_data.delay
                else:  # press => use
                    use(skill)

                    simWaitTime = shared_data.delay

            shared_data.taskList.pop(0)

        for skill in range(shared_data.USABLE_SKILL_COUNT[shared_data.serverID]):  # 0~6
            if (
                availableSkillCount[skill]
                < shared_data.SKILL_COMBO_COUNT_LIST[shared_data.serverID][shared_data.jobID][
                    shared_data.selectedSkillList[skill]
                ]
            ):  # 스킬 사용해서 쿨타임 기다리는 중이면
                skillCoolTimers[skill] += int(shared_data.UNIT_TIME * 100)

                if skillCoolTimers[skill] >= int(
                    shared_data.SKILL_COOLTIME_LIST[shared_data.serverID][shared_data.jobID][
                        shared_data.selectedSkillList[skill]
                    ]
                    * (100 - cooltimeReduce)
                ):  # 쿨타임이 지나면
                    shared_data.preparedSkillList[2].append(skill)  # 대기열에 추가
                    availableSkillCount[skill] += 1  # 사용 가능 횟수 증가

                    skillCoolTimers[skill] = 0  # 쿨타임 초기화
                    # print(f"{(elapsedTime) * 0.001:.3f} - {skill} 쿨타임")

        if minusSkillCount[1] == 0:
            availableSkillCount[minusSkillCount[0]] -= 1
            minusSkillCount = [None, None]

        if minusSkillCount[1] != None:
            minusSkillCount[1] = max(0, minusSkillCount[1] - int(shared_data.UNIT_TIME * 1000))
        simWaitTime = max(0, simWaitTime - int(shared_data.UNIT_TIME * 1000))
        elapsedTime += int(shared_data.UNIT_TIME * 1000)

    usedSkillList = [i for i in usedSkillList if i[1] <= 61000]
    # 1초마다 평타도 추가시켜야함 => 데미지 계산 할 때 추가시키기
    return usedSkillList
