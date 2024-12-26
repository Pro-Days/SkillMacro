from PIL import Image
import numpy as np

# 이미지 파일을 엽니다
image_path = "200.png"
image = Image.open(image_path)

# 이미지를 numpy 배열로 변환합니다
image_np = np.array(image)

# 각 채널의 평균을 계산합니다
mean_color = image_np.mean(axis=(0, 1))

# 결과 출력
print("Mean color (RGB):", mean_color)
