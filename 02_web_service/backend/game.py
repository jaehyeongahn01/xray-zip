"""교육 게임 래퍼 (設計).

game_logic.load_questions / map_click_to_cam / score_question 를 무수정 import 해
질문 캐시 로드·출제·채점만 담당한다. 치팅 방지: 출제 응답에는 id 만 노출한다.
"""
import random

import config  # noqa: F401  (sys.path 삽입 보장)
import game_logic

_QUESTIONS = []          # 전체 질문 dict 리스트 (서버 전용, 정답/peak 포함)
_BY_ID = {}              # {id: question}


def load_cache():
    """startup 에서 1회 호출: questions.csv 를 로드해 전역 캐시를 채운다."""
    global _QUESTIONS, _BY_ID
    _QUESTIONS = game_logic.load_questions()
    _BY_ID = {q["id"]: q for q in _QUESTIONS}
    return len(_QUESTIONS)


def sample_questions(n):
    """무작위 n개를 공개형(id 만)으로 반환 — 치팅 방지(FR-2.4)."""
    chosen = random.sample(_QUESTIONS, min(n, len(_QUESTIONS)))
    return [{"id": q["id"]} for q in chosen]


def get_question(qid):
    """내부 전체 dict (없으면 None). 서버 전용."""
    return _BY_ID.get(qid)


def grade(qid, chosen_label, click=None, display_size=None):
    """한 문제 채점. click 이 있으면 map_click_to_cam 환산 후 score_question 호출.

    click: (x, y) 표시 이미지 좌표 또는 None
    display_size: (w, h) 또는 None
    반환: score_question 의 반환 dict 그대로.
    """
    q = get_question(qid)
    if q is None:
        return None
    click_cam = None
    if click is not None and display_size is not None:
        click_cam = game_logic.map_click_to_cam(click, display_size, q["img_size"])
    return game_logic.score_question(q, chosen_label, click_cam)


def peak_display(q, display_w, display_h):
    """peak_cam → peak_display 축별 독립 환산 (設計)."""
    img_size = q["img_size"]
    x = q["peak_x"] / img_size * display_w
    y = q["peak_y"] / img_size * display_h
    return x, y
