import numpy as np
import streamlit as st
import cv2
from analyzer import analyze_well_image

# -------------------------
# Config
# -------------------------
st.set_page_config(
    page_title="SalivaID (Prototype)",
    page_icon="🧪",
    layout="centered",
)

STEPS = ["start", "input", "analyze", "result"]
STEP_LABEL = {
    "start": "Start",
    "input": "Input",
    "analyze": "Analyze",
    "result": "Result",
}

# -------------------------
# Session state init
# -------------------------
if "step" not in st.session_state:
    st.session_state.step = "start"

def goto(step: str):
    if step not in STEPS:
        step = "start"
    st.session_state.step = step
    st.rerun()

def reset_all(to_step: str = "start"):
    st.session_state.pop("uploaded_file_bytes", None)
    st.session_state.pop("uploaded_file_name", None)
    st.session_state.pop("result", None)
    goto(to_step)

def reset_to_input():
    reset_all(to_step="input")


# -------------------------
# Small UI helper (progress + header)
# -------------------------
def render_step_header():
    step = st.session_state.step
    idx = STEPS.index(step) if step in STEPS else 0
    st.progress((idx + 1) / len(STEPS))
    st.caption(f"Step {idx + 1}/4 · {STEP_LABEL.get(step, 'Start')}")


# -------------------------
# Step 1: Start
# -------------------------
def render_start():
    render_step_header()

    st.title("🧪 SalivaID")
    st.write("한 장의 사진으로 well의 색 변화(Hue)를 분석하는 연구용 프로토타입입니 다.")
    st.info("중요: 본 앱은 의료적 진단 도구가 아니며, 연구/교육 목적의 색 분석 결과를 제공합니다.")

    st.markdown("**사용 방법(1줄):** 사진 업로드 → 분석 → threshold 비교 결과 확인")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("시작하기", type="primary", use_container_width=True):
            goto("input")
    with col2:
        if st.button("리셋", use_container_width=True):
            reset_all("start")

    with st.expander("촬영 가이드(권장)", expanded=True):
        st.markdown(
            "- 동일한 조명(라이트박스/고정 조명 권장)\n"
            "- 그림자/반사(글레어) 최소화\n"
            "- 초점 선명(흔들림 X)\n"
            "- well이 프레임 중앙에 오도록"
        )


# -------------------------
# Step 2: Input
# -------------------------
def render_input():
    render_step_header()

    st.header("사진 업로드")
    st.caption("사진 업로드 후 ‘분석하기’를 눌러야 다음 단계로 넘어갑니 다.")

    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader(
            "Upload an image (JPG/PNG)",
            type=["jpg", "jpeg", "png"],
        )
        submitted = st.form_submit_button("분석하기", type="primary", use_container_width=True)

    if uploaded_file is not None:
        st.subheader("Preview")
        st.image(uploaded_file, caption=uploaded_file.name, use_column_width=True)

    if submitted:
        if uploaded_file is None:
            st.error("사진을 업로드해주세 요.")
            st.stop()

        st.session_state.uploaded_file_bytes = uploaded_file.read()
        st.session_state.uploaded_file_name = uploaded_file.name
        goto("analyze")

    # ✅ 여기서 반드시 col1/col2 둘 다 with로 닫아줘야 함
    col1, col2 = st.columns(2)
    with col1:
        if st.button("시작 화면", use_container_width=True):
            goto("start")
    with col2:
        if st.button("입력 초기화", use_container_width=True):
            reset_to_input()


# -------------------------
# Step 3: Analyze
# -------------------------
def render_analyze():
    render_step_header()

    st.header("분석 중")
    st.caption("이미지를 분석하고 있습니 다...")

    file_bytes = st.session_state.get("uploaded_file_bytes")
    if not file_bytes:
        st.warning("업로드된 이미지가 없습니다. 입력 단계로 이동합니 다.")
        goto("input")

    try:
        with st.spinner("Analyzing image..."):
            result = analyze_well_image(file_bytes)

        st.session_state.result = result
        goto("result")

    except Exception as e:
        st.error(f"Error during analysis: {e}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("다시 업로드", type="primary", use_container_width=True):
                reset_to_input()
        with col2:
            if st.button("시작 화면", use_container_width=True):
                reset_all("start")


# -------------------------
# Step 4: Result
# -------------------------
def render_result():
    render_step_header()

    st.header("결과")
    result = st.session_state.get("result")
    if result is None:
        st.warning("결과가 없습니다. 다시 분석해주세 요.")
        if st.button("업로드로 돌아가기", type="primary", use_container_width=True):
            reset_to_input()
        return

    avg_h_cv = result.get("avg_h_cv")
    avg_h_deg = result.get("avg_h_deg")
    threshold_deg = result.get("threshold_deg")
    threshold_cv = result.get("threshold_cv")
    above_threshold = result.get("above_threshold")
    img_bgr = result.get("img_bgr")

    img_rgb = None
    if img_bgr is not None:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    if above_threshold:
        st.warning(
            "**Above threshold**\n\n"
            "색 변화가 임계값보다 큽니 다. 촬영 조건을 점검한 뒤 재측정/추가 확인을 권장합니 다."
        )
    else:
        st.success(
            "**Below threshold**\n\n"
            "색 변화가 임계값보다 작습니 다. 단, 촬영 조건(조명/초점/반사)에 따라 값이 달라질 수 있습니 다."
        )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Key metrics")
        st.metric("Average Hue (deg)", f"{avg_h_deg:.2f}" if avg_h_deg is not None else "N/A")
        st.metric("Threshold (deg)", f"{threshold_deg:.2f}" if threshold_deg is not None else "N/A")

        with st.expander("Show technical details"):
            st.write(
                f"**Average Hue (OpenCV 0–179):** `{avg_h_cv:.2f}`"
                if avg_h_cv is not None else
                "**Average Hue (OpenCV 0–179):** N/A"
            )
            st.write(
                f"**Threshold Hue (OpenCV):** `{threshold_cv:.2f}`"
                if threshold_cv is not None else
                "**Threshold Hue (OpenCV):** N/A"
            )

    with col2:
        st.subheader("Image used")

        # ✅ 오버레이는 result/img_bgr/img_rgb가 존재하는 여기(render_result) 안에서만 가능
        mask = result.get("mask", None)
        roi_bbox = result.get("roi_bbox", None)

        overlay_rgb = None
        used_pct = None

        if img_bgr is not None and (mask is not None or roi_bbox is not None):
            try:
                overlay_bgr = img_bgr.copy()

                if mask is not None:
                    if len(mask.shape) == 3:
                        mask_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
                    else:
                        mask_gray = mask

                    if mask_gray.shape[:2] != overlay_bgr.shape[:2]:
                        mask_gray = cv2.resize(
                            mask_gray,
                            (overlay_bgr.shape[1], overlay_bgr.shape[0]),
                            interpolation=cv2.INTER_NEAREST,
                        )

                    mask_bin = mask_gray > 0
                    used_pct = float(np.mean(mask_bin) * 100.0)

                    color = np.zeros_like(overlay_bgr)
                    color[:] = (0, 255, 0)

                    blended = cv2.addWeighted(overlay_bgr, 0.55, color, 0.45, 0)
                    overlay_bgr[mask_bin] = blended[mask_bin]

                if roi_bbox is not None and len(roi_bbox) == 4:
                    x, y, w, h = roi_bbox
                    cv2.rectangle(overlay_bgr, (x, y), (x + w, y + h), (0, 255, 255), 2)

                overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)

            except Exception:
                overlay_rgb = None

        tab1, tab2 = st.tabs(["Original", "ROI/Mask overlay"])

        with tab1:
            if img_rgb is not None:
                st.image(img_rgb, caption="Original image", use_column_width=True)
            else:
                st.info("표시할 원본 이미지가 없습니다.")

        with tab2:
            if overlay_rgb is not None:
                st.image(overlay_rgb, caption="Pixels used for hue computation", use_column_width=True)
                if used_pct is not None:
                    st.caption(f"Used pixels: {used_pct:.1f}%")
            else:
                st.info("mask/ROI 정보가 없어 오버레이를 표시할 수 없습니다.")

    with st.expander("How to interpret this"):
        td = f"{threshold_deg:.2f}" if threshold_deg is not None else "N/A"
        st.write(
            "- Hue는 충분한 saturation/brightness를 가진 픽셀에서 계산됩니다.\n"
            f"- Threshold는 실험적 calibration 값에서 도출됩니다. (예: `{td}`°)\n"
            "- Above threshold는 색 변화가 더 강하다는 의미입니다.\n\n"
            "**Important:** 본 결과는 연구/교육 목적의 색 분석이며, 의료적 진단이 아닙니다."
        )

    st.subheader("Next actions")
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("다른 이미지 분석", type="primary", use_container_width=True):
            reset_to_input()
    with a2:
        if st.button("입력으로 돌아가기", use_container_width=True):
            goto("input")
    with a3:
        if st.button("시작 화면", use_container_width=True):
            reset_all("start")


# -------------------------
# Router
# -------------------------
step = st.session_state.step
if step == "start":
    render_start()
elif step == "input":
    render_input()
elif step == "analyze":
    render_analyze()
elif step == "result":
    render_result()
else:
    reset_all("start")




