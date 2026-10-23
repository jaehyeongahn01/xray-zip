"""CXR 폐렴 3분류 판독 보조 웹앱 (Streamlit).
이미지 업로드 → 3분류 확률 + Grad-CAM 히트맵 + 한계 고지.
UI: Dark Editorial Tech (미드나이트 네이비 + 코랄 핑크).

실행: streamlit run app.py
"""
import os

import numpy as np
from PIL import Image
import streamlit as st

from inference import Predictor, CLASS_NAMES_KR, IMG_SIZE
from theme import inject_theme

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "03_model_and_results", "best_model.pth")

st.set_page_config(page_title="CXR 폐렴 판독 보조", page_icon="🫁", layout="wide")


# ============================================================
# Dark Editorial Tech 테마 (공유 CSS 주입)
# ============================================================
inject_theme()


@st.cache_resource
def get_predictor():
    """모델은 한 번만 로드 (캐시)."""
    return Predictor(MODEL_PATH)


# ---- 헤더 ----
st.markdown('<div class="app-title">흉부 X선 폐렴 판독 보조</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-sub">ResNet18 · 3분류(정상 / 세균성 / 바이러스성) · Grad-CAM 근거 시각화</div>',
    unsafe_allow_html=True,
)

# 사이드바: 설정
with st.sidebar:
    st.header("설정")
    thresh = st.slider("Grad-CAM 핵심영역 문턱값", 0.3, 0.9, 0.7, 0.05,
                       help="높일수록 '가장 빨간 핵심'만 좁게 표시")
    st.markdown("---")
    st.markdown("**모델**: ResNet18 (ImageNet 사전학습)")
    st.markdown("**성능**: test macro-F1 0.866")

uploaded = st.file_uploader("흉부 X선 이미지를 업로드하세요 (jpg / jpeg / png)",
                            type=["jpg", "jpeg", "png"])

# 업로드 파일이 바뀌면 보기 모드를 원본으로 초기화
if uploaded is not None and st.session_state.get("_fname") != uploaded.name:
    st.session_state["_fname"] = uploaded.name
    st.session_state["view_mode"] = "원본"

if uploaded is None:
    st.info("이미지를 올리면 원본 CXR이 표시됩니다. 사진 아래 버튼으로 AI의 판단 근거(Grad-CAM)를 볼 수 있어요.")
else:
    pil = Image.open(uploaded)
    try:
        predictor = get_predictor()
        with st.spinner("분석 중..."):
            out = predictor.predict(pil, thresh=thresh)
    except Exception as e:
        st.error(f"모델 로드/추론 실패: {e}")
        st.stop()

    probs = out["probs"]
    pred_kr = out["pred_kr"]

    # ---- 예측 결과 pill ----
    st.markdown(
        f'<div style="margin:0.5rem 0 1.2rem 0;">예측 &nbsp; '
        f'<span class="pred-pill">{pred_kr} · {probs[out["pred_idx"]]*100:.1f}%</span></div>',
        unsafe_allow_html=True,
    )

    # ---- 이미지: 업로드 박스 전체 폭의 정확한 중앙에 배치 ----
    # 양쪽 여백을 동일한 비율(1:8:1)로 지정하면 이미지 중심이
    # 업로드 박스(메인 컨테이너)의 중심과 일치합니다.
    view = st.session_state.get("view_mode", "원본")
    image_cols = st.columns([1, 8, 1], gap="small")
    with image_cols[1]:
        if view == "원본":
            st.image(out["resized"], caption="원본 흉부 X선", use_container_width=True)
        elif view == "Grad-CAM 전체":
            st.image(out["overlay"], caption="Grad-CAM (전체) — 모델이 주목한 정도", use_container_width=True)
        else:  # 핵심 영역
            st.image(out["overlay_thresh"],
                     caption=f"핵심 영역 (cam ≥ {thresh}) — 가장 강하게 주목한 곳",
                     use_container_width=True)

    # ---- 버튼: 업로드 박스와 같은 부모 폭을 3등분 ----
    # 첫 버튼의 왼쪽 / 마지막 버튼의 오른쪽이 업로드 박스의 양 끝과 일치합니다.
    options = ["원본", "Grad-CAM 전체", "핵심 영역"]
    cols = st.columns(3, gap="small")
    for i, opt in enumerate(options):
        with cols[i]:
            is_sel = (view == opt)
            if st.button(
                opt,
                key=f"btn_{i}",
                type="primary" if is_sel else "secondary",
                use_container_width=True,
            ):
                st.session_state["view_mode"] = opt
                st.rerun()

    # ---- 확률 막대 ----
    st.markdown("### 클래스별 확률")
    for i, kr in enumerate(CLASS_NAMES_KR):
        st.write(f"{kr}  —  {probs[i]*100:.1f}%")
        st.progress(float(probs[i]))

    # ---- 한계 고지 (HITL) ----
    st.markdown("---")
    st.warning(
        "⚠️ **한계 고지**: 본 도구는 교육·연구용 PoC입니다. 실제 의료 진단이 아니며, "
        "공개 데이터(jpg)로 학습한 참고용 결과입니다. 임상 판단은 반드시 의료 전문가가 수행해야 합니다. "
        "Grad-CAM은 '모델이 주목한 영역'이지 의학적 병변 위치가 아닙니다."
    )
