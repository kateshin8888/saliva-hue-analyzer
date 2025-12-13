import cv2
import numpy as np

# Threshold in degree scale (0–360)
THRESHOLD_HUE_DEG = 293.0
S_MIN = 30
V_MIN = 30

# ====== (추가) 표준곡선 계수 ======
# Hue_deg = CAL_M * concentration + CAL_B
# 네 표준곡선으로 바꾸시오.
CAL_M = -3.0353
CAL_B = 298.78
# =================================

def hue_to_concentration(hue_deg: float) -> float:
    """Hue(deg)를 표준곡선 역산으로 concentration으로 변환."""
    if abs(CAL_M) < 1e-12:
        raise ValueError("CAL_M(기울기)가 0에 가깝습니다. 표준곡선을 확인하시오.")
    return (hue_deg - CAL_B) / CAL_M


def analyze_well_image(file_bytes):
    """
    업로드된 이미지 bytes에서 평균 Hue를 계산하고
    (옵션) 표준곡선으로 concentration 추정값을 반환.
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

    # ====== (추가) Hue -> concentration 역산 ======
    concentration_est = hue_to_concentration(mean_h_deg)
    threshold_concentration = hue_to_concentration(THRESHOLD_HUE_DEG)
    # ============================================

    # (선택) 표준곡선 범위 밖 표시 (원하면 사용)
    out_of_range = False
    # 예: 농도는 0 이상만 의미 있다면
    if concentration_est < 0:
        out_of_range = True

    return {
        "avg_h_cv": mean_h_cv,                 # 0~179
        "avg_h_deg": mean_h_deg,               # 0~360
        "threshold_deg": THRESHOLD_HUE_DEG,
        "threshold_cv": thr_h_cv,
        "above_threshold": above_threshold,
        "img_bgr": img,

        # ====== (추가 반환) ======
        "concentration_est": float(concentration_est),
        "threshold_concentration": float(threshold_concentration),
        "calibration": {"m": float(CAL_M), "b": float(CAL_B)},
        "out_of_range": bool(out_of_range),
    }

