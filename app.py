import numpy as np
import streamlit as st
import cv2
from analyzer import analyze_well_image

# -------------------------
# Config
# -------------------------
st.set_page_config(
    page_title="SalivADetector (Prototype)",
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

    st.title("🧪 SalivADetector")
    st.write("This site analyzes the hue change from a single image and compares it to an experimentally calibrated threshold. The output may indicate a potential risk of Alzheimer's Disease")
    st.info("Warning: This test is intended for preliminary screening for Alzheimer’s disease (AD). If the result is positive, please consult a healthcare professional for standardized diagnostic evaluation.")

    st.markdown("**directions:** prepare the picture of the well, taken according to the directions below → analyze → view results")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("start", type="primary", use_container_width=True):
            goto("input")
    with col2:
        if st.button("리셋", use_container_width=True):
            reset_all("start")

    with st.expander("taking photo guide", expanded=True):
        st.markdown(
            "- use a bright, white background"
            "- ensure the image is clear"
            "- center the well in the frame"
              )


# -------------------------
# Step 2: Input
# -------------------------
def render_input():
    render_step_header()

    st.header("Upload your picture")
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
            st.error("After uploading the photo, click Analyze to proceed to the next step.")
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

    st.header("analyzing")
    st.caption("Analyzing the uploaded photo")

    file_bytes = st.session_state.get("uploaded_file_bytes")
    if not file_bytes:
        st.warning("No image was uploaded. Returning to the upload step.")
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
            if st.button("Upload Again", type="primary", use_container_width=True):
                reset_to_input()
        with col2:
            if st.button("Starting Page", use_container_width=True):
                reset_all("start")


# -------------------------
# Step 4: Result
# -------------------------
def render_result():
    render_step_header()

    st.header("Result")
    result = st.session_state.get("result")
    if result is None:
        st.warning("No results. Please try again.")
        if st.button("Return to Upload", type="primary", use_container_width=True):
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
            "**Alzheimer's positive**\n\n"
            "Please seek professional help."
        )
    else:
        st.success(
            "**Alzheimer's negative**\n\n"
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


    with st.expander("How was the data calculated?"):
        td = f"{threshold_deg:.2f}" if threshold_deg is not None else "N/A"
        st.write( "- The calibration curve is adjusted using the positive and negative reference controls captured in the same image. "
        "The sample’s hue value is then mapped onto the adjusted curve. "
        "Because the calculation is based on relative values within the same photo, results are less sensitive to differences in capture conditions (e.g., lighting).\n"
        f"- The threshold is derived from experimental calibration (e.g., `{td}`°).\n"
        "- Lactoferrin is a proposed biomarker associated with Alzheimer’s disease (AD). "
        "An 'Above threshold' result indicates a stronger color change, which may correspond to a higher lactoferrin level in saliva.\n\n"
        "**Important:** This output is intended for preliminary screening only and indicates possibility rather than a definitive diagnosis."
        )

    st.subheader("Next actions")
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("Analyze another image", type="primary", use_container_width=True):
            reset_to_input()
    with a2:
        if st.button("Return to Upload", use_container_width=True):
            goto("input")
    with a3:
        if st.button("Start Page", use_container_width=True):
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





