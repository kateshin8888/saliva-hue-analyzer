import streamlit as st
import cv2
from analyzer import analyze_well_image

# 페이지 기본 설정
st.set_page_config(
    page_title="Saliva Hue Analyzer",
    page_icon="🧪",
    layout="centered",
)

# 제목 & 설명
st.title("🧪 Saliva Color Analyzer")
st.write(
    "Upload a photo of the saliva reaction well. "
    "This app calculates the average hue and compares it to a threshold (293°)."
)

# 파일 업로드 UI
uploaded_file = st.file_uploader(
    "Upload an image (JPG/PNG)",
    type=["jpg", "jpeg", "png"],
)

if uploaded_file is not None:
    st.subheader("1. Uploaded Image")
    st.image(uploaded_file, caption="Uploaded sample", use_column_width=True)

    if st.button("Analyze image"):
        try:
            # hue 분석 실행
            result = analyze_well_image(uploaded_file.read())

            avg_h_cv = result["avg_h_cv"]
            avg_h_deg = result["avg_h_deg"]
            threshold_deg = result["threshold_deg"]
            threshold_cv = result["threshold_cv"]
            above_threshold = result["above_threshold"]
            img_bgr = result["img_bgr"]

            # BGR -> RGB 변환
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

            st.subheader("2. Analysis Result")

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Average Hue (OpenCV 0–179):** `{avg_h_cv:.2f}`")
                st.write(f"**Average Hue (Degrees 0–360):** `{avg_h_deg:.2f}`")
                st.write(f"**Threshold Hue (Degrees):** `{threshold_deg:.2f}`")

                if above_threshold:
                    st.success("🟢 Hue is ABOVE threshold (>= 293°).")
                else:
                    st.error("🔴 Hue is BELOW threshold (< 293°).")

            with col2:
                st.image(img_rgb, caption="Image used for analysis", use_column_width=True)

            with st.expander("How to interpret this"):
                st.write(
                    "- Hue is computed only from pixels with enough saturation and brightness.\n"
                    "- Threshold 293° comes from your experimental calibration.\n"
                    "- Above threshold = stronger color change in the well.\n"
                    "\n"
                    "**Note:** This is a research prototype, not a medical diagnosis tool."
                )

        except Exception as e:
            st.error(f"Error during analysis: {e}")
else:
    st.info("Upload an image to begin.")

