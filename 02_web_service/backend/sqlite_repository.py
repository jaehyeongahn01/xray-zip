"""SQLite persistence. Connections are short-lived, writes transactional."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from repository import GameRecordRepository


def now():
    return datetime.now(timezone.utc).isoformat()


class SQLiteRepository(GameRecordRepository):
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
            CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS games (game_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id), data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS games_user ON games(user_id);
            CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id), expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS readings (id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id), created_at TEXT NOT NULL, pred_idx INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS readings_user_date ON readings(user_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY);
            ''')
        os.chmod(path, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def get_account(self, user_id):
        with self.connect() as db:
            row = db.execute('SELECT data FROM users WHERE user_id=?', (user_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def user_exists(self, user_id):
        return self.get_account(user_id) is not None

    def register_user(self, user_id):
        with self.connect() as db:
            return db.execute('INSERT OR IGNORE INTO users VALUES (?,?)', (user_id, json.dumps({'created_at': now()}))).rowcount == 1

    def create_account(self, user_id, name, occupation, password_hash, salt):
        record = dict(created_at=now(), name=name, occupation=occupation, password_hash=password_hash, salt=salt)
        with self.connect() as db:
            try:
                db.execute('INSERT INTO users VALUES (?,?)', (user_id, json.dumps(record)))
            except sqlite3.IntegrityError:
                raise ValueError('이미 존재하는 사용자 ID입니다.')
        return record

    def verify_password(self, user_id, password):
        rec = self.get_account(user_id)
        return bool(rec and rec.get('salt') and rec.get('password_hash') and hmac.compare_digest(
            hashlib.sha256((rec['salt'] + password).encode()).hexdigest(), rec['password_hash']))

    def save_game_result(self, user_id, game_summary):
        rec = {**game_summary, 'game_id': str(uuid.uuid4()), 'user_id': user_id, 'played_at': now()}
        with self.connect() as db:
            db.execute('INSERT INTO games VALUES (?,?,?)', (rec['game_id'], user_id, json.dumps(rec)))
        return rec

    def get_user_history(self, user_id):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT data FROM games WHERE user_id=? ORDER BY rowid', (user_id,))]

    def list_all_games(self):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT data FROM games ORDER BY rowid')]

    def migrate_json(self, path):
        if not os.path.exists(path):
            return
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM migrations WHERE name='json-v1'").fetchone():
                return
            with open(path) as file:
                old = json.load(file)
            for uid, data in old['users'].items():
                db.execute('INSERT INTO users VALUES (?,?)', (uid, json.dumps(data)))
            for rec in old['games']:
                db.execute('INSERT INTO games VALUES (?,?,?)', (rec['game_id'], rec['user_id'], json.dumps(rec)))
            db.execute("INSERT INTO migrations VALUES ('json-v1')")

    def create_session(self, user_id):
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time()+86400*7))
        return token

    def session_user(self, token):
        with self.connect() as db:
            row = db.execute('SELECT user_id FROM sessions WHERE token_hash=? AND expires>?',
                (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        return row[0] if row else None

    def logout(self, token):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def save_reading(self, uid, record):
        with self.connect() as db:
            db.execute('INSERT INTO readings VALUES (?,?,?,?,?)', (record['id'], uid, record['created_at'], record['pred_idx'], json.dumps(record)))

    def get_reading(self, uid, rid):
        with self.connect() as db:
            row = db.execute('SELECT data FROM readings WHERE id=? AND user_id=?', (rid, uid)).fetchone()
        return json.loads(row[0]) if row else None

    def list_readings(self, uid, start=None, end=None, label=None, offset=0):
        sql, args = 'SELECT data FROM readings WHERE user_id=?', [uid]
        for clause, value in [('created_at>=?', start), ('created_at<?', end), ('pred_idx=?', label)]:
            if value is not None:
                sql += ' AND ' + clause
                args.append(value)
        with self.connect() as db:
            rows = db.execute(sql+' ORDER BY created_at DESC, id DESC LIMIT 51 OFFSET ?', [*args, offset]).fetchall()
        return [json.loads(r[0]) for r in rows]
