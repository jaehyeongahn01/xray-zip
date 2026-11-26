import base64
import io
import logging
import re
import uuid
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo

import boto3
from fastapi import APIRouter, Depends, HTTPException, Query, Response
import config
from auth import current_user
from repository import get_repository

router = APIRouter()
log = logging.getLogger(__name__)

def s3_client():
    return boto3.client('s3', region_name=config.AWS_REGION)

def save_reading(uid, filename, pil, result):
    if not config.S3_BUCKET:
        raise RuntimeError("Configure CXR_S3_BUCKET to enable reading history storage.")
    rid = str(uuid.uuid4())
    # 회원가입에서 ID를 영문/숫자/-/_ 로 제한하므로 원문을 S3 폴더명으로 그대로 쓴다
    # (S3 콘솔에서 폴더만 보고 누구 것인지 바로 구분 가능). 방어적으로 한 번 더 검증한다.
    if not re.fullmatch(r'[A-Za-z0-9_-]+', uid):
        raise ValueError('S3 폴더명으로 쓸 수 없는 사용자 ID입니다.')
    prefix = f'{config.S3_PREFIX}/{uid}/{rid}'
    keys = {kind: f'{prefix}/{kind}.png' for kind in result['images']}
    buf = io.BytesIO()
    pil.convert('RGB').save(buf, format='PNG')
    payloads = {kind: base64.b64decode(value.split(',', 1)[1]) for kind, value in result['images'].items()}
    payloads['original'] = buf.getvalue()
    client = s3_client()
    uploaded = []
    try:
        for kind, body in payloads.items():
            client.put_object(Bucket=config.S3_BUCKET, Key=keys[kind], Body=body, ContentType='image/png', ServerSideEncryption='AES256')
            uploaded.append(keys[kind])
        record = {k: v for k, v in result.items() if k != 'images'}
        record.update(id=rid, created_at=datetime.now(timezone.utc).isoformat(), filename=filename,
                      model_version='resnet18-v4-batch16-20261014', bucket=config.S3_BUCKET, keys=keys)
        get_repository().save_reading(uid, record)
        return rid
    except Exception:
        for key in uploaded:
            try:
                client.delete_object(Bucket=config.S3_BUCKET, Key=key)
            except Exception:
                log.exception('S3 rollback failed for reading %s', rid)
        raise

def public_record(rec):
    return {k: v for k, v in rec.items() if k not in {'bucket', 'keys'}}

@router.get('/api/readings')
def readings(start: date | None = None, end: date | None = None,
             label: int | None = Query(None, ge=0, le=2), offset: int = Query(0, ge=0), uid=Depends(current_user)):
    if start and end and start > end:
        raise HTTPException(400, '날짜 범위를 확인해 주세요.')
    def utc(d):
        return datetime.combine(d, datetime.min.time(), tzinfo=ZoneInfo('Asia/Seoul')).astimezone(timezone.utc).isoformat()
    rows = get_repository().list_readings(uid, utc(start) if start else None,
        utc(end+timedelta(days=1)) if end else None, label, offset)
    return {'items': [public_record(r) for r in rows[:50]], 'has_more': len(rows)>50}

@router.get('/api/readings/{rid}')
def detail(rid: str, uid=Depends(current_user)):
    rec = get_repository().get_reading(uid, rid)
    if not rec:
        raise HTTPException(404, '판독 기록을 찾을 수 없습니다.')
    return {**public_record(rec), 'images': {kind: f'/api/readings/{rid}/images/{kind}' for kind in rec['keys']}}

@router.get('/api/readings/{rid}/images/{kind}')
def image(rid: str, kind: str, uid=Depends(current_user)):
    rec = get_repository().get_reading(uid, rid)
    if not rec or kind not in rec['keys']:
        raise HTTPException(404, '이미지를 찾을 수 없습니다.')
    try:
        obj = s3_client().get_object(Bucket=rec['bucket'], Key=rec['keys'][kind])
        body = obj['Body'].read()
        obj['Body'].close()
    except Exception:
        log.exception('History image load failed')
        raise HTTPException(503, '이미지를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.')
    return Response(body, media_type='image/png', headers={'Cache-Control': 'private, no-store'})
