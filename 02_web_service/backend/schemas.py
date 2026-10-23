"""Pydantic 요청/응답 계약 (設計).

점수 숫자 필드는 float 로 선언해 int·float 혼재(정상=int, 폐렴=round float)를
그대로 수용한다(設計 finding #4). 값은 가공하지 않는다(NFR-2).
"""
from typing import List, Optional

from pydantic import BaseModel, Field


# ---- 좌표 ----
class Point(BaseModel):
    x: float
    y: float


class DisplaySize(BaseModel):
    w: float
    h: float


# ---- /api/predict ----
class PredictImages(BaseModel):
    original: str
    overlay: str
    overlay_thresh: str


class PredictResponse(BaseModel):
    reading_id: Optional[str] = None
    history_warning: Optional[str] = None
    probs: List[float]
    pred_idx: int
    pred_kr: str
    class_names_kr: List[str]
    thresh_effective: float
    images: PredictImages


# ---- /api/questions ----
class QuestionPublic(BaseModel):
    id: str


class QuestionsResponse(BaseModel):
    questions: List[QuestionPublic]


# ---- /api/score ----
class ScoreRequest(BaseModel):
    question_id: str
    chosen_label: int = Field(..., ge=0, le=2)
    click: Optional[Point] = None
    display_size: Optional[DisplaySize] = None
    # 제한시간(10초) 초과로 미제출된 경우 True. 서버는 점수를 모두 0으로 강제하되
    # reveal(정답/AI예측/peak)은 정상 제공한다(교육 목적).
    timed_out: bool = False


class ScoreDetail(BaseModel):
    class_correct: bool
    # 점수 필드는 int·float 혼재 수용
    class_points: float
    location_points: float
    total: float
    distance: Optional[float] = None
    needs_click: bool


class Reveal(BaseModel):
    true_label: int
    true_label_kr: str
    ai_pred_label: int
    ai_pred_kr: str
    ai_probs: List[float]
    peak_display: Point
    peak_cam: Point
    img_size: int
    display_size: DisplaySize


class ScoreResponse(BaseModel):
    score: ScoreDetail
    reveal: Reveal


# ---- /api/users ----
class UserRequest(BaseModel):
    user_id: str


class UserResponse(BaseModel):
    user_id: str
    created: bool


# ---- /api/register, /api/login (인증) ----
class RegisterRequest(BaseModel):
    # 이름(name)은 사용하지 않는다(화면 표시는 user_id 기준). 한글 IME 입력 이슈 회피 겸 단순화.
    user_id: str
    password: str
    password_confirm: str
    occupation: str


class LoginRequest(BaseModel):
    user_id: str
    password: str


class AccountResponse(BaseModel):
    # 비번 관련 필드(password/password_hash/salt)는 절대 포함하지 않는다.
    user_id: str
    occupation: str


# ---- /api/games ----
class PerQuestionSummary(BaseModel):
    question_id: str
    true_label: int
    chosen_label: int
    class_correct: bool
    location_points: float
    total: float
    needs_click: bool


class GamesRequest(BaseModel):
    # 집계값(total_score/average/num_correct)은 받지 않는다 — 서버가 재계산
    user_id: str
    per_question_summary: List[PerQuestionSummary]


class GamesResponse(BaseModel):
    saved: bool
    game_id: str
    played_at: str
    total_score: float
    average: float
    num_questions: int
    num_correct: int


# ---- /api/users/{id}/stats ----
class ClassAccuracy(BaseModel):
    total: int
    correct: int
    accuracy: float


class ClassAccuracyMap(BaseModel):
    normal: ClassAccuracy
    bacteria: ClassAccuracy
    virus: ClassAccuracy


class StatsResponse(BaseModel):
    user_id: str
    plays: int
    avg_score: float
    best_score: float
    class_accuracy: ClassAccuracyMap
    recent_trend: List[float]


# ---- /api/leaderboard ----
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    best_average: float
    avg_average: float
    plays: int


class LeaderboardResponse(BaseModel):
    sort: str
    entries: List[LeaderboardEntry]
