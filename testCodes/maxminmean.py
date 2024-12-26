import numpy as np

data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

minimum = np.min(data)
maximum = np.max(data)
mean = np.mean(data)
p25 = np.percentile(data, 25)
p50 = np.percentile(data, 50)
p75 = np.percentile(data, 75)

result = {
    "Minimum": minimum,
    "Maximum": maximum,
    "Mean": mean,
    "P25": p25,
    "P50": p50,
    "P75": p75,
}

print(result)
