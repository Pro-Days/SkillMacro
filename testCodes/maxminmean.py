import numpy as np


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
    if len(data) == 0:
        raise ValueError("Data list cannot be empty")

    # Step 1: 평균 계산
    mean = sum(data) / len(data)

    # Step 2: 각 데이터에서 평균을 뺀 제곱의 합 계산
    squared_differences = [(x - mean) ** 2 for x in data]

    # Step 3: 분산 계산
    variance = sum(squared_differences) / len(data)

    # Step 4: 표준편차 계산
    std_dev = variance**0.5

    return std_dev


data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

minimum = np.min(data)
maximum = np.max(data)
mean = np.mean(data)
p25 = np.percentile(data, 25)
p50 = np.percentile(data, 50)
p75 = np.percentile(data, 75)
p25_ = calculate_percentile(data, 25)
p50_ = calculate_percentile(data, 50)
p75_ = calculate_percentile(data, 75)
std = np.std(data)
std_ = calculate_std(data)

result = {
    "Minimum": minimum,
    "Maximum": maximum,
    "Mean": mean,
    "P25": p25,
    "P50": p50,
    "P75": p75,
    "P25_": p25_,
    "P50_": p50_,
    "P75_": p75_,
    "Std": std,
    "Std_": std_,
}

print(result)
