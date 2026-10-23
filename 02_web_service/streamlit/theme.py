"""공유 테마 (Dark Editorial Tech).

판독기(app.py)와 교육 게임(pages/)이 같은 CSS를 쓰도록 분리했다.
미드나이트 네이비 + 코랄 핑크.
"""
import streamlit as st

THEME_CSS = """
<style>
/* ---- 색 변수 ---- */
:root {
    --bg: #191A2B;
    --bg2: #30253D;
    --accent: #E45D7B;
    --accent2: #F78A9F;
    --text: #ECE8F1;
    --muted: #9B93AD;
}

/* ---- 전체 배경: 미드나이트 네이비 → 차콜 퍼플 은은한 그라데이션 ---- */
.stApp {
    background: linear-gradient(160deg, #191A2B 0%, #211d33 55%, #30253D 100%);
    color: var(--text);
}

/* 메인 컨테이너 폭 제한 (너무 넓게 퍼지지 않게) */
.block-container {
    max-width: 1100px;
    padding-top: 2.5rem;
}

/* ---- 타이포 ---- */
h1, h2, h3 { color: var(--text); font-weight: 700; letter-spacing: -0.3px; }
.app-title {
    font-size: 2.1rem; font-weight: 800; margin-bottom: 0.2rem;
    background: linear-gradient(90deg, #F78A9F, #E45D7B);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.app-sub { color: var(--muted); font-size: 0.95rem; margin-bottom: 1.5rem; }

/* ---- 카드 ---- */
.card {
    background: rgba(48, 37, 61, 0.55);
    border: 1px solid rgba(247, 138, 159, 0.12);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}

/* ---- 이미지: 중앙 이미지 컬럼 내에서 크기를 유지하고 중앙 배치 ---- */
div[data-testid="stImage"] {
    width: 100%;
    text-align: center;
}
div[data-testid="stImage"] img {
    display: block;
    width: 100%;
    height: auto;
    max-height: 640px;
    object-fit: contain;
    margin-inline: auto;
    border-radius: 12px;
    background: #0e0f1a;
    padding: 10px;
    box-sizing: border-box;
    box-shadow: 0 8px 30px rgba(0,0,0,0.45);
}
div[data-testid="stImageCaption"] {
    text-align: center !important;
    width: 100%;
}

/* 버튼 공통 */
div[data-testid="stButton"] > button {
    width: 100%;
    min-height: 56px;
    white-space: nowrap;
    border-radius: 14px;
    padding: 0.9rem 0.5rem;
    font-size: 1rem; font-weight: 600;
    background: rgba(48, 37, 61, 0.6);
    color: var(--text);
    border: 1.5px solid rgba(247, 138, 159, 0.18);
    transition: all 0.18s ease;
}
div[data-testid="stButton"] > button:hover {
    border-color: var(--accent2);
    transform: translateY(-2px);
}
/* 선택된 박스: 코랄 핑크 강조 (type="primary") */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, rgba(228,93,123,0.25), rgba(247,138,159,0.15));
    border: 1.5px solid var(--accent);
    color: #fff;
    box-shadow: 0 6px 22px rgba(228, 93, 123, 0.35);
}

/* ---- 확률 막대 (progress) 코랄 핑크 ---- */
div[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #E45D7B, #F78A9F);
}

/* ---- 업로더 ---- */
section[data-testid="stFileUploaderDropzone"] {
    background: rgba(48, 37, 61, 0.4);
    border: 1.5px dashed rgba(247, 138, 159, 0.3);
    border-radius: 14px;
}

/* 예측 결과 pill */
.pred-pill {
    display: inline-block;
    background: linear-gradient(135deg, #E45D7B, #F78A9F);
    color: #fff; font-weight: 700; font-size: 1.15rem;
    padding: 0.5rem 1.2rem; border-radius: 999px;
    box-shadow: 0 6px 20px rgba(228,93,123,0.35);
}

/* 점수 pill (게임용 - 큰 숫자) */
.score-pill {
    display: inline-block;
    background: linear-gradient(135deg, #E45D7B, #F78A9F);
    color: #fff; font-weight: 800; font-size: 1.6rem;
    padding: 0.6rem 1.6rem; border-radius: 999px;
    box-shadow: 0 6px 20px rgba(228,93,123,0.35);
}

/* 결과 배지 */
.badge-ok { color: #7CE38B; font-weight: 700; }
.badge-no { color: #F78A9F; font-weight: 700; }
.muted { color: var(--muted); }
</style>
"""


def inject_theme():
    """현재 페이지에 공유 테마 CSS를 주입한다."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)
