import cv2
import numpy as np

# Threshold in degree scale (0–360)
THRESHOLD_HUE_DEG = 293.0  # 네가 정한 기준값
S_MIN = 30                 # 채도 최소
V_MIN = 30                 # 밝기 최소


def analyze_well_image(file_bytes):
    """
    업로드된 이미지 bytes에서 평균 Hue를 계산하고 threshold와 비교.
    결과를 dict 형태로 반환.
    """

    # 1) bytes -> OpenCV 이미지로 디코딩
    file_array = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(file_array, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("이미지를 읽을 수 없습니다.")

    # 2) BGR -> HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)  # h: 0~179, s/v: 0~255

    # 3) 너무 어둡거나 채도가 낮은 픽셀 제외
    mask_valid = (s >= S_MIN) & (v >= V_MIN)
    if not np.any(mask_valid):
        raise ValueError("유효 픽셀이 없습니다 (이미지가 너무 어둡거나 채도가 낮음).")

    valid_h = h[mask_valid].astype(np.float32)

    # 4) 평균 Hue (OpenCV 스케일 0~179)
    mean_h_cv = float(np.mean(valid_h))

    # 5) 0~360 도(degree)로 환산
    mean_h_deg = mean_h_cv * 2.0

    # 6) threshold도 OpenCV 스케일로 변환해서 비교
    thr_h_cv = THRESHOLD_HUE_DEG / 2.0
    above_threshold = mean_h_cv >= thr_h_cv

    # 7) 결과 묶어서 반환
    return {
        "avg_h_cv": mean_h_cv,           # 0~179
        "avg_h_deg": mean_h_deg,         # 0~360
        "threshold_deg": THRESHOLD_HUE_DEG,
        "threshold_cv": thr_h_cv,
        "above_threshold": above_threshold,
        "img_bgr": img,
    }
