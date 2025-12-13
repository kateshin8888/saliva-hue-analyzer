import streamlit as st
import cv2
from analyzer import analyze_well_image

# -------------------------
# Config
# -------------------------
st.set_page_config(
    page_title="SalivADetector (Prototype)",
    page_icon=None,
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
st.session_state.setdefault("step", "start")

def goto(step: str):
    """Set step only (no rerun here)."""
    if step not in STEPS:
        step = "start"
    st.session_state.step = step

def navigate(step: str):
    """Set step + rerun + hard stop (prevents duplicate rendering)."""
    goto(step)
    st.rerun()
    st.stop()

def reset_all(to_step: str = "start"):
    st.session_state.pop("uploaded_file_bytes", None)
    st.session_state.pop("uploaded_file_name", None)
    st.session_state.pop("result", None)
    navigate(to_step)

def reset_to_input():
    reset_all(to_step="input")

def bgr_to_rgb(img_bgr):
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

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

    st.title("SalivADetector")
    st.write(
        "This site analyzes the color change from a single image and compares it to an experimentally calibrated threshold. "
        "The output may indicate a potential risk of Alzheimer's Disease."
    )
    st.info(
        "Warning: This test is intended for preliminary screening for Alzheimer’s disease (AD). "
        "If the result is positive, please consult a healthcare professional for standardized diagnostic evaluation."
    )

    st.markdown("**Directions:** Prepare a photo taken according to the guide below → Analyze → View results")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start", type="primary", use_container_width=True):
            navigate("input")
    with col2:
        if st.button("Reset", use_container_width=True):
            reset_all("start")

    with st.expander("Photo guide", expanded=True):
        st.markdown(
            "- Use a bright, white background\n"
            "- Ensure the image is clear and in focus\n"
            "- Center the target area in the frame\n"
        )

# -------------------------
# Step 2: Input
# -------------------------
def render_input():
    render_step_header()

    st.header("Upload your picture")
    st.caption("After uploading the photo, click 'Analyze' to proceed to the next step.")

    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader(
            "Upload an image (JPG/PNG)",
            type=["jpg", "jpeg", "png"],
        )
        submitted = st.form_submit_button("Analyze", type="primary", use_container_width=True)

    if uploaded_file is not None:
        st.subheader("Preview")
        st.image(uploaded_file, caption=uploaded_file.name, use_column_width=True)

    if submitted:
        if uploaded_file is None:
            st.error("After uploading the photo, click Analyze to proceed to the next step.")
            st.stop()

        st.session_state.uploaded_file_bytes = uploaded_file.read()
        st.session_state.uploaded_file_name = uploaded_file.name
        navigate("analyze")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start page", use_container_width=True):
            navigate("start")
    with col2:
        if st.button("Clear input", use_container_width=True):
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
        navigate("input")

    try:
        with st.spinner("Analyzing image..."):
            result = analyze_well_image(file_bytes)

        st.session_state.result = result
        navigate("result")

    except Exception as e:
        st.error(f"Error during analysis: {e}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Upload Again", type="primary", use_container_width=True):
                reset_to_input()
        with col2:
            if st.button("Start page", use_container_width=True):
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

    # ---- Decision flag (prefer concentration-based flag if you add it in analyzer.py) ----
    screening_positive = result.get("screening_positive", None)
    if screening_positive is None:
        # fallback to whatever you used before
        screening_positive = result.get("above_threshold", None)

    # ---- Show ONLY the screening conclusion by default ----
    if screening_positive is True:
        st.warning("**Alzheimer's positive**\n\nPlease seek professional help.")
    elif screening_positive is False:
        st.success("**Alzheimer's negative**\n\n")
    else:
        st.info("**Result unavailable**\n\nMissing decision output.")

    # =========================
    # EVERYTHING ELSE IS HIDDEN
    # =========================
    with st.expander("See more info", expanded=False):

        # Image
        img_bgr = result.get("img_bgr")
        if img_bgr is not None:
            st.subheader("Input image")
            st.image(bgr_to_rgb(img_bgr), use_column_width=True)

        # Main values
        concentration_est = result.get("concentration_est")
        concentration_raw = result.get("concentration_raw", concentration_est)
        threshold_concentration = result.get("threshold_concentration")

        below_range = result.get("below_range", False)
        above_range = result.get("above_range", False)
        out_of_range = result.get("out_of_range", False)

        # Display-safe concentration (never show negative)
        conc_display = None
        try:
            if concentration_est is not None:
                conc_display = float(concentration_est)
                if conc_display < 0:
                    conc_display = 0.0
                    below_range = True
                    out_of_range = True
        except Exception:
            conc_display = None

        st.subheader("Key metrics")
        st.metric(
            "Estimated concentration",
            f"{conc_display:.4f}" if conc_display is not None else "N/A"
        )
        st.metric(
            "Threshold concentration",
            f"{float(threshold_concentration):.4f}" if threshold_concentration is not None else "N/A"
        )

        # Range messaging (clear + defensible)
        if below_range:
            st.info("Estimated concentration is below the calibration range (reported as 0).")
        if above_range:
            st.warning("Estimated concentration is above the calibration range (may be capped).")
        if out_of_range and not (below_range or above_range):
            st.warning("Estimated concentration may be out of the valid calibration range.")

        # Technical Hue details (no nested expanders)
        avg_h_cv = result.get("avg_h_cv")
        avg_h_deg = result.get("avg_h_deg")
        threshold_deg = result.get("threshold_deg")
        threshold_cv = result.get("threshold_cv")

        st.subheader("Technical details")
        st.write(f"**Average Hue (deg):** `{avg_h_deg:.2f}`" if avg_h_deg is not None else "**Average Hue (deg):** N/A")
        st.write(f"**Threshold Hue (deg):** `{threshold_deg:.2f}`" if threshold_deg is not None else "**Threshold Hue (deg):** N/A")
        st.write(f"**Average Hue (OpenCV 0–179):** `{avg_h_cv:.2f}`" if avg_h_cv is not None else "**Average Hue (OpenCV 0–179):** N/A")
        st.write(f"**Threshold Hue (OpenCV):** `{threshold_cv:.2f}`" if threshold_cv is not None else "**Threshold Hue (OpenCV):** N/A")

        st.subheader("How was the data calculated?")
        td = f"{threshold_deg:.2f}" if threshold_deg is not None else "N/A"
        st.write(
            "- The hue value is computed from the uploaded image and converted to concentration using an experimentally derived calibration curve.\n"
            f"- The threshold is derived from experimental calibration (e.g., `{td}`°).\n"
            "- Lactoferrin is a proposed biomarker associated with Alzheimer’s disease (AD). "
            "An 'Above threshold' result indicates a stronger color change, which may correspond to a higher lactoferrin level in saliva.\n\n"
            "**Important:** This output is intended for preliminary screening only and indicates possibility rather than a definitive diagnosis."
        )

        # Optional: show raw numbers for debugging
        if concentration_raw is not None:
            try:
                st.caption(f"Debug: concentration_raw = {float(concentration_raw):.4f}")
            except Exception:
                pass

    # Keep your action buttons visible (if you want these hidden too, move them into the expander)
    st.subheader("Next actions")
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("Analyze another image", type="primary", use_container_width=True):
            reset_to_input()
    with a2:
        if st.button("Return to Upload", use_container_width=True):
            navigate("input")
    with a3:
        if st.button("Start page", use_container_width=True):
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







