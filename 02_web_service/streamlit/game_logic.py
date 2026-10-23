"""교육 게임 로직 모듈.

판독 게임의 '데이터'와 '채점'만 담당한다 (UI는 pages/1_교육_게임.py).
- questions.csv 로드 → 문제 리스트
- 클릭 좌표(표시 이미지 기준) → 원본 CAM 좌표(224)로 환산
- 채점: 클래스 50점 + 위치 50점 = 문제당 100점

채점 설계 (기획서 + 기존 score_click 결합):
- 클래스 정답: 50점 (틀리면 0)
- 위치 점수(폐렴일 때만): Grad-CAM peak(peak_x, peak_y)까지의 거리 d로 계산
    d <= r_full            → 50점 (만점존)
    r_full < d <= r_cam    → 50 → 0 선형 감소 (CAM 영역)
    d > r_cam              → 0점 (CAM 밖)
- 정상(NORMAL) 문제: 위치 클릭 없이 클래스만. 맞으면 100, 틀리면 0.

좌표 기준:
- questions.csv의 peak_x/peak_y, r_full, r_cam, img_size(=224)는 '전처리된 224 정사각' 기준.
- 게임 화면에는 원본 비율로 리사이즈한 이미지를 보여주므로, 사용자의 클릭 좌표를
  표시 크기 → 224 정사각 좌표로 환산해서 채점한다 (map_click_to_cam).
"""
import os

import pandas as pd

# ---- 경로 ----
# webapp/ 기준으로 education_game_review/ 는 프로젝트 루트에 있다.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
GAME_DIR = os.path.normpath(os.path.join(_ROOT, "..", "04_dataset", "education_game_review"))
QUESTIONS_CSV = os.path.join(GAME_DIR, "questions.csv")
IMAGES_DIR = os.path.join(GAME_DIR, "images")
GRADCAM_DIR = os.path.join(GAME_DIR, "gradcam")
OVERLAY_DIR = os.path.join(GAME_DIR, "overlay")

# ---- 클래스 ----
CLASS_KR = ["정상", "세균성 폐렴", "바이러스성 폐렴"]
LABEL_NORMAL = 0  # 정상 라벨 (위치 클릭 불필요)

# ---- 배점 ----
CLASS_POINTS = 50
LOCATION_POINTS = 50
MAX_PER_QUESTION = CLASS_POINTS + LOCATION_POINTS  # 100

# 만점존 반경 = r_cam × 이 비율. (기존엔 고정 r_full=12px였으나 화면상 너무 좁아
# CAM 넓이에 비례하도록 변경. 0.4 = "AI 핵심 영역의 안쪽 40%"면 위치 만점.)
FULL_ZONE_RATIO = 0.4


def load_questions():
    """questions.csv → 문제 dict 리스트. 파일별 로컬 이미지 경로를 붙여준다."""
    df = pd.read_csv(QUESTIONS_CSV, dtype={"id": str})
    questions = []
    for _, r in df.iterrows():
        qid = str(r["id"])
        fname = f"{qid}.png"
        questions.append({
            "id": qid,
            "true_label": int(r["true_label"]),
            "true_label_kr": r["true_label_kr"],
            "pred_label": int(r["pred_label"]),
            "pred_label_kr": r["pred_label_kr"],
            "probs": [float(r["prob_normal"]), float(r["prob_bacteria"]), float(r["prob_virus"])],
            "peak_x": float(r["peak_x"]),
            "peak_y": float(r["peak_y"]),
            "r_full": float(r["r_full"]),
            "r_cam": float(r["r_cam"]),
            "img_size": int(r["img_size"]),
            "image_path": os.path.join(IMAGES_DIR, fname),
            "gradcam_path": os.path.join(GRADCAM_DIR, fname),
            "overlay_path": os.path.join(OVERLAY_DIR, fname),
        })
    return questions


def is_normal(question):
    """정상 문제인가? (위치 클릭이 필요 없는 문제)"""
    return int(question["true_label"]) == LABEL_NORMAL


def map_click_to_cam(click_xy, disp_size, img_size):
    """표시 이미지 좌표(click_xy) → CAM 기준 좌표(img_size, 보통 224)로 환산.

    click_xy: (x, y) 표시 이미지 위 클릭 픽셀
    disp_size: (w, h) 화면에 보여준 이미지 크기
    img_size: CAM 좌표계 한 변 (정사각, 224)
    """
    cx, cy = click_xy
    dw, dh = disp_size
    if dw <= 0 or dh <= 0:
        return 0.0, 0.0
    x = cx / dw * img_size
    y = cy / dh * img_size
    return x, y


def location_score(click_cam_xy, question):
    """CAM 좌표계 클릭 → 위치 점수(0~LOCATION_POINTS)와 거리 반환.

    반환: (score, distance)
    """
    px, py = question["peak_x"], question["peak_y"]
    r_cam = question["r_cam"]
    # 만점존: r_cam에 비례 (문제마다 CAM 넓이에 맞춰 유연). 고정 r_full은 미사용.
    r_full = r_cam * FULL_ZONE_RATIO
    x, y = click_cam_xy
    d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5

    if d <= r_full:
        return float(LOCATION_POINTS), d
    if d <= r_cam:
        # r_full(만점존 끝)에서 50점, r_cam에서 0점으로 선형 감소
        ratio = (r_cam - d) / (r_cam - r_full) if r_cam > r_full else 0.0
        return float(LOCATION_POINTS) * max(0.0, ratio), d
    return 0.0, d


def score_question(question, chosen_label, click_cam_xy=None):
    """한 문제 채점.

    question: load_questions()의 한 항목
    chosen_label: 사용자가 고른 클래스(0/1/2)
    click_cam_xy: CAM 좌표계 클릭 (정상 문제면 None 허용)

    반환 dict:
      class_correct, class_points, location_points, total,
      distance(폐렴일 때만, 아니면 None), needs_click(이 문제가 클릭 필요한지)
    """
    class_correct = int(chosen_label) == int(question["true_label"])
    class_points = CLASS_POINTS if class_correct else 0

    needs_click = not is_normal(question)

    if not needs_click:
        # 정상 문제: 위치 채점 없음. 맞으면 100, 틀리면 0.
        total = MAX_PER_QUESTION if class_correct else 0
        return {
            "class_correct": class_correct,
            "class_points": MAX_PER_QUESTION if class_correct else 0,
            "location_points": 0,
            "total": total,
            "distance": None,
            "needs_click": False,
        }

    # 폐렴 문제: 클래스 + 위치
    loc_points, dist = 0.0, None
    if click_cam_xy is not None:
        loc_points, dist = location_score(click_cam_xy, question)

    return {
        "class_correct": class_correct,
        "class_points": class_points,
        "location_points": round(loc_points, 1),
        "total": round(class_points + loc_points, 1),
        "distance": None if dist is None else round(dist, 1),
        "needs_click": True,
    }
