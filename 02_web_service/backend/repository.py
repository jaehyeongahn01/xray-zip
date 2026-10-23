"""게임 기록 저장소 (設計).

GameRecordRepository(추상) + JsonFileRepository(기본, 의존성 없는 JSON 파일).
실제 DB 로 교체할 때는 get_repository() 의 생성부만 바꾸면 되도록 격리한다(FR-3.3/3.5).
"""
import hashlib
import json
import os
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

import config


class GameRecordRepository(ABC):
    """교체 가능한 기록 저장소 인터페이스 (원시 저장/조회만 담당, 통계는 stats.py)."""

    @abstractmethod
    def register_user(self, user_id: str) -> bool:
        """신규면 True, 기존이면 False (멱등)."""

    @abstractmethod
    def user_exists(self, user_id: str) -> bool:
        ...

    @abstractmethod
    def save_game_result(self, user_id: str, game_summary: dict) -> dict:
        """game_id·played_at 을 부여해 저장하고 저장 레코드를 반환한다."""

    @abstractmethod
    def get_user_history(self, user_id: str) -> List[dict]:
        """해당 사용자의 원시 게임 레코드 리스트."""

    @abstractmethod
    def list_all_games(self) -> List[dict]:
        """모든 게임 레코드 (순위 집계용, user_id 포함)."""

    @abstractmethod
    def create_account(self, user_id: str, name: str, occupation: str,
                       password_hash: str, salt: str) -> dict:
        """계정을 생성하고 생성한 계정 레코드를 반환한다."""

    @abstractmethod
    def get_account(self, user_id: str) -> Optional[dict]:
        """계정 레코드(name/occupation 등 포함)를 반환, 없으면 None."""

    @abstractmethod
    def verify_password(self, user_id: str, password: str) -> bool:
        """저장된 해시와 대조해 비밀번호가 맞으면 True, 아니면(계정 없음 포함) False."""


class JsonFileRepository(GameRecordRepository):
    """backend/data/records.json 기반 기본 구현.

    프로세스 내 Lock 으로 read-modify-write 를 직렬화하고, 임시파일 + os.replace 로
    원자적으로 저장한다(쓰다 깨짐 방지). 파일/디렉터리는 없으면 자동 생성한다.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # ---- 내부 입출력 ----
    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {"users": {}, "games": []}
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("users", {})
        data.setdefault("games", [])
        # 과거 포맷 방어: 인증 필드가 없는 user 레코드에 기본값을 채워 안전하게 읽는다.
        for rec in data["users"].values():
            if isinstance(rec, dict):
                rec.setdefault("name", "")
                rec.setdefault("occupation", "")
                rec.setdefault("password_hash", None)
                rec.setdefault("salt", None)
        return data

    def _save(self, data: dict) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = f"{self.path}.{uuid.uuid4().hex}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ---- 인터페이스 구현 ----
    def register_user(self, user_id: str) -> bool:
        with self._lock:
            data = self._load()
            if user_id in data["users"]:
                return False
            data["users"][user_id] = {
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self._save(data)
            return True

    def user_exists(self, user_id: str) -> bool:
        with self._lock:
            data = self._load()
            return user_id in data["users"]

    def save_game_result(self, user_id: str, game_summary: dict) -> dict:
        with self._lock:
            data = self._load()
            record = {
                "game_id": str(uuid.uuid4()),
                "user_id": user_id,
                "played_at": datetime.now(timezone.utc).isoformat(),
                **game_summary,
            }
            data["games"].append(record)
            self._save(data)
            return record

    def get_user_history(self, user_id: str) -> List[dict]:
        with self._lock:
            data = self._load()
            return [g for g in data["games"] if g.get("user_id") == user_id]

    def list_all_games(self) -> List[dict]:
        with self._lock:
            data = self._load()
            return list(data["games"])

    def create_account(self, user_id: str, name: str, occupation: str,
                       password_hash: str, salt: str) -> dict:
        with self._lock:
            data = self._load()
            record = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "name": name,
                "occupation": occupation,
                "password_hash": password_hash,
                "salt": salt,
            }
            data["users"][user_id] = record
            self._save(data)
            return record

    def get_account(self, user_id: str) -> Optional[dict]:
        with self._lock:
            data = self._load()
            rec = data["users"].get(user_id)
            return dict(rec) if rec is not None else None

    def verify_password(self, user_id: str, password: str) -> bool:
        with self._lock:
            data = self._load()
            rec = data["users"].get(user_id)
            if rec is None:
                return False
            salt = rec.get("salt")
            stored = rec.get("password_hash")
            if not salt or not stored:
                return False
            computed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
            return computed == stored


_REPO = None


def get_repository() -> GameRecordRepository:
    """저장소 팩토리.

    ★ 실제 DB 로 교체하는 유일 지점 ★
    GameRecordRepository 를 구현한 새 클래스(예: SqliteRepository)를 만든 뒤
    아래 생성부만 바꾸면 라우트/통계 코드는 그대로 동작한다.
    """
    global _REPO
    if _REPO is None:
        if config.REPOSITORY_BACKEND == "sqlite":
            from sqlite_repository import SQLiteRepository
            _REPO = SQLiteRepository(config.SQLITE_PATH)
            _REPO.migrate_json(config.RECORDS_PATH)
        elif config.REPOSITORY_BACKEND == "json":
            _REPO = JsonFileRepository(config.RECORDS_PATH)
        else:
            raise ValueError("Unknown CXR_REPOSITORY")
    return _REPO


def set_repository(repo: GameRecordRepository) -> None:
    """테스트용 저장소 주입(실데이터 오염 방지)."""
    global _REPO
    _REPO = repo
