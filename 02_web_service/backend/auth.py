from fastapi import HTTPException, Request, Response
import config
from repository import get_repository

COOKIE = 'cxr_session'

def current_user(request: Request):
    token = request.cookies.get(COOKIE, '')
    uid = get_repository().session_user(token) if token else None
    if not uid:
        raise HTTPException(401, '로그인이 필요합니다. 다시 로그인해 주세요.')
    return uid

def issue_session(response: Response, uid):
    token = get_repository().create_session(uid)
    response.set_cookie(COOKIE, token, httponly=True, secure=config.COOKIE_SECURE,
                        samesite='strict', max_age=86400*7, path='/')
