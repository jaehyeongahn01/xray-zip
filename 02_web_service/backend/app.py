"""FastAPI 백엔드 앱 (設計§9).

최상단에서 config 를 가장 먼저 import 해 sys.path 를 준비한 뒤 나머지 모듈을 올린다.
오류는 모두 {"detail": "<한글>"} + 4xx 로 반환하고, 미처리 예외만 500 한글로 매핑한다.
"""
import base64
import hashlib
import io
import logging
import re
import secrets
from contextlib import asynccontextmanager

import config  # noqa: F401  ← 최상단: sys.path 삽입 보장 (設計)
import inference
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, Depends, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from PIL import Image, UnidentifiedImageError

import auth
import reading_history
import game
import predictor
import stats
from repository import get_repository
from schemas import (
    AccountResponse,
    GamesRequest,
    GamesResponse,
    LeaderboardResponse,
    LoginRequest,
    PredictResponse,
    QuestionsResponse,
    RegisterRequest,
    ScoreRequest,
    ScoreResponse,
    StatsResponse,
    UserRequest,
    UserResponse,
)

logger = logging.getLogger("backend")

# 게임 화면 고정 렌더 크기 (overlay 파일 kind)
_ALLOWED_KINDS = {"image", "overlay"}
_ALLOWED_N = {5, 10}


def _ensure_admin():
    """관리자 시드 계정 보장 — 없으면 생성(멱등).

    records.json 을 비우거나 지워도 서버 기동 시 admin 이 항상 되살아난다.
    비밀번호는 salt+sha256 해시로만 저장(평문 미보관). 이미 있으면 건드리지 않는다.
    """
    repo = get_repository()
    if repo.get_account(config.ADMIN_USER_ID) is not None:
        return
    salt = secrets.token_hex(16)
    password_hash = _hash_password(config.ADMIN_PASSWORD, salt)
    repo.create_account(
        config.ADMIN_USER_ID, config.ADMIN_NAME, config.ADMIN_OCCUPATION,
        password_hash, salt,
    )
    logger.info("관리자 계정(%s) 시드 생성", config.ADMIN_USER_ID)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 모델/질문 워밍업 — 실패 시 기동 중단(조용한 실패 방지, 設計)
    predictor.get_predictor()
    game.load_cache()
    _ensure_admin()  # 관리자 시드 계정 보장(영구 보존)
    yield


app = FastAPI(title="CXR 판독·교육 게임 API", lifespan=lifespan)

app.include_router(reading_history.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 전역 예외 핸들러 (設計) ----
@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "입력값이 올바르지 않습니다."})


@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception("미처리 예외")
    return JSONResponse(status_code=500, content={"detail": "서버 오류가 발생했습니다."})


# ---- 유틸 ----
def _hash_password(password: str, salt: str) -> str:
    """salt + password 를 sha256 로 해시(표준 라이브러리만 사용)."""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _np_to_data_url(arr) -> str:
    """numpy uint8 (H,W,3) → PNG → base64 data URL."""
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ---- 엔드포인트 ----
@app.post("/api/predict", response_model=PredictResponse)
async def predict(file: UploadFile = File(...), thresh: str = Form(None), save_history: str = Form("true"), uid=Depends(auth.current_user)):
    ctype = (file.content_type or "").lower()
    name = (file.filename or "").lower()
    ext_ok = name.endswith((".jpg", ".jpeg", ".png"))
    if not ctype.startswith("image/") or not ext_ok:
        raise HTTPException(400, "이미지 파일(jpg/jpeg/png)만 업로드할 수 있어요.")

    # thresh: 미전송/빈문자열 → 기본값, 숫자 아닌 문자열 → 400
    if thresh is None or str(thresh).strip() == "":
        thresh_value = config.DEFAULT_THRESH
    else:
        try:
            thresh_value = float(thresh)
        except (TypeError, ValueError):
            raise HTTPException(400, "문턱값이 올바르지 않습니다.")

    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "이미지는 20MB 이하로 업로드해 주세요.")
    try:
        pil = Image.open(io.BytesIO(raw))
        pil.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "이미지를 열 수 없습니다. 파일을 확인해 주세요.")

    try:
        out, thresh_effective = predictor.run_predict(pil, thresh_value)
    except Exception:
        logger.exception("추론 오류")
        raise HTTPException(500, "추론 중 오류가 발생했습니다.")

    result = {
        "probs": out["probs"].tolist(),
        "pred_idx": int(out["pred_idx"]),
        "pred_kr": out["pred_kr"],
        "class_names_kr": inference.CLASS_NAMES_KR,
        "thresh_effective": thresh_effective,
        "images": {
            "original": _np_to_data_url(out["resized"]),
            "overlay": _np_to_data_url(out["overlay"]),
            "overlay_thresh": _np_to_data_url(out["overlay_thresh"]),
        },
    }

    if save_history.lower() not in {"true", "false"}:
        raise HTTPException(400, "저장 옵션이 올바르지 않습니다.")
    if save_history.lower() == "true":
        try:
            result['reading_id'] = reading_history.save_reading(uid, Path(file.filename).name, pil, result)
        except Exception:
            logger.exception('판독 기록 저장 실패')
            result['history_warning'] = '판독은 완료했지만 기록 저장에 실패했습니다. 잠시 후 다시 업로드해 주세요.'
    return result


@app.get("/api/questions", response_model=QuestionsResponse)
async def questions(n: int = 5, uid=Depends(auth.current_user)):
    if n not in _ALLOWED_N:
        raise HTTPException(400, "문제 수는 5 또는 10이어야 합니다.")
    return {"questions": game.sample_questions(n)}


@app.get("/api/game-image/{qid}/{kind}")
async def game_image(qid: str, kind: str):
    q = game.get_question(qid)
    if q is None or kind not in _ALLOWED_KINDS:
        raise HTTPException(404, "요청한 이미지를 찾을 수 없습니다.")
    path = q["image_path"] if kind == "image" else q["overlay_path"]
    import os
    if not os.path.exists(path):
        raise HTTPException(404, "요청한 이미지를 찾을 수 없습니다.")
    return FileResponse(path, media_type="image/png")


@app.post("/api/score", response_model=ScoreResponse)
async def score(req: ScoreRequest, uid=Depends(auth.current_user)):
    q = game.get_question(req.question_id)
    if q is None:
        raise HTTPException(404, "존재하지 않는 문제입니다.")

    click = None
    display_size = None
    if req.click is not None:
        if req.display_size is None or req.display_size.w <= 0 or req.display_size.h <= 0:
            raise HTTPException(400, "표시 크기가 올바르지 않습니다.")
        click = (req.click.x, req.click.y)
        display_size = (req.display_size.w, req.display_size.h)
    elif req.display_size is not None and (req.display_size.w <= 0 or req.display_size.h <= 0):
        raise HTTPException(400, "표시 크기가 올바르지 않습니다.")

    sc = game.grade(req.question_id, req.chosen_label, click, display_size)

    # 제한시간 초과: 미제출로 간주해 점수를 모두 0으로 강제한다(reveal 은 그대로 제공).
    if req.timed_out:
        sc = {
            "class_correct": False,
            "class_points": 0,
            "location_points": 0,
            "total": 0,
            "distance": None,
            "needs_click": sc["needs_click"] if sc else False,
        }

    # peak_display 는 display_size 가 있으면 그 크기로, 없으면 img_size 기준(=peak_cam)
    if display_size is not None:
        disp_w, disp_h = display_size
    else:
        disp_w = disp_h = q["img_size"]
    pdx, pdy = game.peak_display(q, disp_w, disp_h)

    return {
        "score": sc,
        "reveal": {
            "true_label": q["true_label"],
            "true_label_kr": q["true_label_kr"],
            "ai_pred_label": q["pred_label"],
            "ai_pred_kr": q["pred_label_kr"],
            "ai_probs": q["probs"],
            "peak_display": {"x": pdx, "y": pdy},
            "peak_cam": {"x": q["peak_x"], "y": q["peak_y"]},
            "img_size": q["img_size"],
            "display_size": {"w": disp_w, "h": disp_h},
        },
    }


@app.post("/api/users", response_model=UserResponse)
async def users(req: UserRequest, current=Depends(auth.current_user)):
    uid = (req.user_id or "").strip()
    if not uid or len(uid) > 64:
        raise HTTPException(400, "사용자 ID를 입력해 주세요.")
    if uid != current:
        raise HTTPException(403, "본인의 계정만 사용할 수 있습니다.")
    created = get_repository().register_user(uid)
    return {"user_id": uid, "created": created}


@app.post("/api/register", response_model=AccountResponse)
async def register(req: RegisterRequest, response: Response):
    uid = (req.user_id or "").strip()
    if not uid or len(uid) > 64:
        raise HTTPException(400, "사용자 ID를 입력해 주세요.")
    # ID 는 영문/숫자/-/_ 만 허용(S3 폴더명으로 원문 사용하기 위한 안전 제약).
    if not re.fullmatch(r"[A-Za-z0-9_-]+", uid):
        raise HTTPException(400, "사용자 ID는 영문·숫자·-·_만 사용할 수 있습니다.")
    repo = get_repository()
    if repo.get_account(uid) is not None or repo.user_exists(uid):
        raise HTTPException(400, "이미 존재하는 사용자 ID입니다.")
    if not re.fullmatch(r"\d{4}", req.password):
        raise HTTPException(400, "비밀번호는 숫자 4자리여야 합니다.")
    if req.password != req.password_confirm:
        raise HTTPException(400, "비밀번호가 일치하지 않습니다.")
    if req.occupation not in {"의사", "학생", "무직", "기타"}:
        raise HTTPException(400, "직업 선택이 올바르지 않습니다.")

    salt = secrets.token_hex(16)
    password_hash = _hash_password(req.password, salt)
    try:
        # 이름은 사용하지 않으므로 저장소에는 빈 문자열로 둔다(저장소/DB 시그니처는 유지).
        repo.create_account(uid, "", req.occupation, password_hash, salt)
    except ValueError:
        raise HTTPException(400, "이미 존재하는 사용자 ID입니다.")
    auth.issue_session(response, uid)
    return {"user_id": uid, "occupation": req.occupation}


@app.post("/api/login", response_model=AccountResponse)
async def login(req: LoginRequest, response: Response):
    uid = (req.user_id or "").strip()
    repo = get_repository()
    if not repo.verify_password(uid, req.password):
        # 계정 미존재/비번 오답을 동일 메시지로(존재 여부 과노출 방지).
        raise HTTPException(401, "ID 또는 비밀번호가 올바르지 않습니다.")
    auth.issue_session(response, uid)
    acct = repo.get_account(uid)
    return {
        "user_id": uid,
        "occupation": acct.get("occupation", ""),
    }


@app.post("/api/games", response_model=GamesResponse)
async def games(req: GamesRequest, current=Depends(auth.current_user)):
    uid = (req.user_id or "").strip()
    if uid != current:
        raise HTTPException(403, "본인의 기록만 저장할 수 있습니다.")
    repo = get_repository()
    if not repo.user_exists(uid):
        raise HTTPException(400, "등록되지 않은 사용자입니다.")

    summary = req.per_question_summary
    num_questions = len(summary)
    if num_questions not in _ALLOWED_N:
        raise HTTPException(400, "게임 결과가 올바르지 않습니다.")
    for pq in summary:
        if pq.total < 0 or pq.total > 100:
            raise HTTPException(400, "게임 결과가 올바르지 않습니다.")

    total_score = sum(pq.total for pq in summary)
    average = total_score / num_questions
    num_correct = sum(1 for pq in summary if pq.class_correct)

    game_summary = {
        "total_score": total_score,
        "average": average,
        "num_questions": num_questions,
        "num_correct": num_correct,
        "per_question_summary": [pq.model_dump() for pq in summary],
    }
    record = repo.save_game_result(uid, game_summary)

    return {
        "saved": True,
        "game_id": record["game_id"],
        "played_at": record["played_at"],
        "total_score": total_score,
        "average": average,
        "num_questions": num_questions,
        "num_correct": num_correct,
    }


@app.get("/api/users/{uid}/stats", response_model=StatsResponse)
async def user_stats(uid: str, current=Depends(auth.current_user)):
    if uid != current:
        raise HTTPException(403, "본인의 기록만 조회할 수 있습니다.")
    history = get_repository().get_user_history(uid)
    s = stats.compute_user_stats(history)
    return {"user_id": uid, **s}


@app.get("/api/leaderboard", response_model=LeaderboardResponse)
async def leaderboard(limit: int = 10, uid=Depends(auth.current_user)):
    if limit < 1 or limit > 100:
        raise HTTPException(400, "limit 은 1~100 사이여야 합니다.")
    entries = stats.compute_leaderboard(get_repository().list_all_games(), limit)
    return {
        "sort": "best_average desc, avg_average desc, plays desc, user_id asc",
        "entries": entries,
    }


@app.get("/api/me")
async def me(uid=Depends(auth.current_user)):
    account = get_repository().get_account(uid)
    return {'user_id': uid, 'occupation': account.get('occupation', '')}


@app.post("/api/logout")
async def logout(request: Request, response: Response):
    get_repository().logout(request.cookies.get(auth.COOKIE, ''))
    response.delete_cookie(auth.COOKIE, path='/')
    return {'ok': True}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# API routes precede the SPA fallback; unknown API/assets must remain 404.
_dist = Path(config.FRONTEND_DIST)
if (_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str):
    if path not in {"", "x-ai", "x-play", "x-play/game", "x-play/rank", "x-lab"}:
        raise HTTPException(404, "페이지를 찾을 수 없습니다.")
    index = _dist / "index.html"
    if not index.is_file():
        raise HTTPException(503, "프론트엔드 빌드가 필요합니다.")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
