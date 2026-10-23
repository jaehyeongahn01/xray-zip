"""판독 교육 게임 (Streamlit 멀티페이지).

흐름: 시작(문제 수 선택) → 문제풀이(클래스 선택 + 위치 클릭) →
      정답 공개(AI 예측·Grad-CAM 비교·점수) → 다음 → 종료(총점·요약).

채점/데이터 로직은 game_logic.py, 테마는 theme.py를 재사용한다.
클릭 좌표는 streamlit-image-coordinates 컴포넌트로 수집한다.

프레이밍(중요): 위치 점수는 'AI가 주목한 영역(Grad-CAM)과의 일치도'이며
실제 의학적 병변 발견 정확도가 아니다. 교육·연구용 PoC.
"""
import os
import random
import sys

from PIL import Image, ImageDraw
import streamlit as st

# webapp/ 를 import 경로에 추가 (pages/ 하위에서 상위 모듈 참조)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from theme import inject_theme
from game_logic import (
    load_questions,
    is_normal,
    map_click_to_cam,
    score_question,
    CLASS_KR,
)

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    HAS_COORD = True
except ImportError:
    HAS_COORD = False

st.set_page_config(page_title="CXR 판독 교육 게임", page_icon="🎮", layout="wide")
inject_theme()

DISPLAY_SIZE = 512  # 게임 화면에 보여줄 정사각 이미지 한 변(px)


# ============================================================
# 세션 상태 초기화
# ============================================================
def init_state():
    ss = st.session_state
    ss.setdefault("phase", "start")   # start / playing / revealed / finished
    ss.setdefault("questions", [])    # 이번 게임에 뽑힌 문제들
    ss.setdefault("idx", 0)           # 현재 문제 번호
    ss.setdefault("results", [])      # 문제별 채점 결과 기록
    ss.setdefault("chosen", None)     # 현재 문제에서 고른 클래스
    ss.setdefault("click", None)      # 현재 문제 클릭 (표시좌표 x,y)
    ss.setdefault("last_score", None) # 방금 채점 결과 dict
    ss.setdefault("click_nonce", 0)   # 클릭 위젯 key용 (문제 넘어갈 때 위젯 리셋)


init_state()
ss = st.session_state


def start_game(n):
    all_q = load_questions()
    random.shuffle(all_q)
    ss.questions = all_q[:n]
    ss.idx = 0
    ss.results = []
    ss.chosen = None
    ss.click = None
    ss.last_score = None
    ss.click_nonce += 1
    ss.phase = "playing"


def reset_for_next():
    ss.chosen = None
    ss.click = None
    ss.last_score = None
    # 클릭 위젯 key를 바꿔서 이전 문제의 좌표가 새 문제로 새지 않게 한다.
    ss.click_nonce += 1


# ============================================================
# 헤더
# ============================================================
st.markdown('<div class="app-title">CXR 판독 교육 게임</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-sub">직접 판독하고 AI(Grad-CAM)와 비교하며 배우는 연습 — '
    '위치 점수는 "AI가 주목한 영역과의 일치도"이지 의학적 정답이 아닙니다.</div>',
    unsafe_allow_html=True,
)

if not HAS_COORD:
    st.error(
        "클릭 좌표 수집 컴포넌트가 없습니다. 아래 명령으로 설치 후 다시 실행하세요:\n\n"
        "`pip install streamlit-image-coordinates`"
    )
    st.stop()


# ============================================================
# 1) 시작 화면
# ============================================================
if ss.phase == "start":
    st.markdown("### 게임 설정")
    st.write("문제 수를 고르고 **시작하기**를 누르세요. 문제는 무작위로 출제됩니다.")

    ss.setdefault("num_q", 5)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("5문제", key="pick5",
                     type="primary" if ss.num_q == 5 else "secondary",
                     use_container_width=True):
            ss.num_q = 5
            st.rerun()
    with c2:
        if st.button("10문제", key="pick10",
                     type="primary" if ss.num_q == 10 else "secondary",
                     use_container_width=True):
            ss.num_q = 10
            st.rerun()

    st.markdown(
        f'<div style="margin:0.4rem 0 1rem 0;" class="muted">선택된 문제 수: '
        f'<b style="color:var(--text);">{ss.num_q}문제</b></div>',
        unsafe_allow_html=True,
    )
    if st.button("시작하기", key="go", type="primary", use_container_width=True):
        start_game(ss.num_q)
        st.rerun()

    st.markdown("---")
    st.markdown(
        "**진행 방식**\n"
        "- 흉부 X선을 보고 **정상 / 세균성 폐렴 / 바이러스성 폐렴** 중 하나를 고릅니다.\n"
        "- **폐렴**을 골랐다면 이상 소견이 의심되는 지점을 이미지에서 **클릭**하세요 (제출 조건).\n"
        "- **정상**은 클릭 없이 바로 제출할 수 있습니다.\n"
        "- 제출하면 실제 라벨·AI 예측·Grad-CAM과 비교해 점수를 매깁니다.\n\n"
        "**점수** — 문제당 100점: 클래스 정답 50점 + 위치 일치도 50점 "
        "(정상 문제는 클래스만, 맞으면 100점)."
    )
    st.stop()


# ============================================================
# 종료 화면
# ============================================================
if ss.phase == "finished":
    n = len(ss.results)
    total = sum(r["score"]["total"] for r in ss.results)
    # 최종 점수 = 문제당 100점 만점의 평균 (문제 수와 무관하게 0~100)
    avg = (total / n) if n else 0
    n_correct = sum(1 for r in ss.results if r["score"]["class_correct"])
    pct = avg  # 득점률(%)과 평균점수는 둘 다 0~100 척도로 동일

    st.markdown("### 게임 종료")
    st.markdown(
        f'<div style="margin:0.6rem 0 1.2rem 0;">최종 점수 &nbsp;'
        f'<span class="score-pill">{avg:.1f}</span>'
        f'<span class="muted"> / 100 (문제 평균)</span></div>',
        unsafe_allow_html=True,
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("득점률", f"{pct:.0f}%")
    m2.metric("클래스 정답", f"{n_correct} / {n}")
    m3.metric("문제 수", f"{n}")

    st.markdown("---")
    st.markdown("#### 문제별 요약")
    for i, r in enumerate(ss.results, 1):
        q = r["question"]
        sc = r["score"]
        ok = "✅" if sc["class_correct"] else "❌"
        chosen_kr = CLASS_KR[r["chosen"]]
        loc = ""
        if sc["needs_click"]:
            loc = f" · 위치 {sc['location_points']:.0f}/50"
            if sc["distance"] is not None:
                loc += f" (거리 {sc['distance']:.0f}px)"
        st.markdown(
            f"**Q{i}** {ok} 정답: **{q['true_label_kr']}** / 내 선택: {chosen_kr} "
            f"· 점수 **{sc['total']:.0f}/100**{loc}"
        )

    st.markdown("---")
    if st.button("다시 시작", type="primary"):
        ss.phase = "start"
        st.rerun()
    st.stop()


# ============================================================
# 공통: 현재 문제
# ============================================================
q = ss.questions[ss.idx]
total_q = len(ss.questions)
base_img = Image.open(q["image_path"]).convert("RGB").resize((DISPLAY_SIZE, DISPLAY_SIZE))

st.markdown(f"#### 문제 {ss.idx + 1} / {total_q}")
running = sum(r["score"]["total"] for r in ss.results)
st.markdown(f'<span class="muted">현재까지 점수: {running:.0f}점</span>', unsafe_allow_html=True)


def draw_marker(img, xy, color=(247, 138, 159)):
    """표시 이미지 위에 클릭 마커(원+십자)를 그린다."""
    im = img.copy()
    d = ImageDraw.Draw(im)
    x, y = xy
    r = 12
    d.ellipse([x - r, y - r, x + r, y + r], outline=color, width=3)
    d.line([x - r - 6, y, x + r + 6, y], fill=color, width=2)
    d.line([x, y - r - 6, x, y + r + 6], fill=color, width=2)
    return im


# ============================================================
# 2) 문제 풀이 화면
# ============================================================
if ss.phase == "playing":
    left, right = st.columns([3, 2], gap="large")

    with left:
        # 클릭 마커를 반영한 이미지 (폐렴 선택 시에만 클릭 의미 있음)
        show_img = base_img
        if ss.click is not None:
            show_img = draw_marker(base_img, ss.click)

        # key에 nonce를 넣어, 다음 문제로 넘어가면 위젯이 새로 생성되어
        # 이전 문제의 클릭 좌표가 남지 않는다.
        coords = streamlit_image_coordinates(
            show_img, key=f"img_{ss.idx}_{ss.click_nonce}"
        )
        if coords is not None:
            new_click = (coords["x"], coords["y"])
            if new_click != ss.click:
                ss.click = new_click
                st.rerun()
        st.markdown(
            '<span class="muted">세균성·바이러스성을 골랐다면 이상 소견이 의심되는 '
            '지점을 클릭하세요. 다시 클릭하면 위치가 바뀝니다.</span>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("**이 영상을 어떻게 판독하시겠어요?**")
        for li, kr in enumerate(CLASS_KR):
            sel = (ss.chosen == li)
            if st.button(kr, key=f"cls_{ss.idx}_{li}",
                         type="primary" if sel else "secondary",
                         use_container_width=True):
                ss.chosen = li
                st.rerun()

        st.markdown("---")
        # 제출 가능 조건
        chosen = ss.chosen
        can_submit = False
        hint = ""
        if chosen is None:
            hint = "클래스를 먼저 선택하세요."
        elif chosen == 0:  # 정상
            can_submit = True
        else:  # 폐렴
            if ss.click is None:
                hint = "폐렴을 선택했어요. 이상 소견 지점을 이미지에서 클릭해야 제출할 수 있어요."
            else:
                can_submit = True

        if hint:
            st.markdown(f'<span class="muted">{hint}</span>', unsafe_allow_html=True)

        if st.button("정답 제출", type="primary", use_container_width=True,
                     disabled=not can_submit):
            # 채점
            click_cam = None
            if chosen != 0 and ss.click is not None:
                click_cam = map_click_to_cam(
                    ss.click, (DISPLAY_SIZE, DISPLAY_SIZE), q["img_size"]
                )
            sc = score_question(q, chosen, click_cam)
            ss.last_score = sc
            ss.results.append({
                "question": q,
                "chosen": chosen,
                "click": ss.click,
                "score": sc,
            })
            ss.phase = "revealed"
            st.rerun()
    st.stop()


# ============================================================
# 3) 정답 공개 화면
# ============================================================
if ss.phase == "revealed":
    sc = ss.last_score
    rec = ss.results[-1]
    chosen = rec["chosen"]
    click = rec["click"]

    left, right = st.columns([3, 2], gap="large")

    with left:
        # Grad-CAM overlay + 내 클릭 위치 함께 표시
        overlay = Image.open(q["overlay_path"]).convert("RGB").resize((DISPLAY_SIZE, DISPLAY_SIZE))
        # AI peak 위치 (CAM 224 → 표시좌표)
        scale = DISPLAY_SIZE / q["img_size"]
        peak_disp = (q["peak_x"] * scale, q["peak_y"] * scale)
        shown = overlay
        # AI가 가장 주목한 지점(초록)
        shown = draw_marker(shown, peak_disp, color=(124, 227, 139))
        # 내 클릭(코랄)
        if click is not None:
            shown = draw_marker(shown, click, color=(247, 138, 159))
        st.image(shown, caption="Grad-CAM 오버레이 · 초록=AI 주목 지점, 분홍=내 선택",
                 use_container_width=True)

    with right:
        # 클래스 결과
        if sc["class_correct"]:
            st.markdown('<span class="badge-ok">● 클래스 정답</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-no">● 클래스 오답</span>', unsafe_allow_html=True)
        st.markdown(
            f"- 실제 라벨: **{q['true_label_kr']}**\n"
            f"- 내 선택: **{CLASS_KR[chosen]}**\n"
            f"- AI 예측: **{q['pred_label_kr']}** "
            f"({q['probs'][q['pred_label']]*100:.1f}%)"
        )

        # 점수
        st.markdown("---")
        if sc["needs_click"]:
            st.markdown(
                f"- 클래스 점수: **{sc['class_points']} / 50**\n"
                f"- 위치 점수: **{sc['location_points']:.0f} / 50**"
                + (f" (AI 주목 지점까지 {sc['distance']:.0f}px)" if sc["distance"] is not None else "")
            )
        else:
            st.markdown(f"- 정상 문제: 클래스만 채점 → **{sc['class_points']} / 100**")

        st.markdown(
            f'<div style="margin:0.6rem 0;">이 문제 점수 &nbsp;'
            f'<span class="score-pill">{sc["total"]:.0f}</span>'
            f'<span class="muted"> / 100</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")
        last = (ss.idx + 1 >= total_q)
        label = "결과 보기" if last else "다음 문제"
        if st.button(label, type="primary", use_container_width=True):
            if last:
                ss.phase = "finished"
            else:
                ss.idx += 1
                reset_for_next()
                ss.phase = "playing"
            st.rerun()

    st.caption(
        "위치 점수는 Grad-CAM(AI가 주목한 영역)과의 일치도이며 의학적 병변 위치의 정답이 아닙니다. "
        "교육·연구용 PoC입니다."
    )
    st.stop()
