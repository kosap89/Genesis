"""Small transactional SQLite store. Every public write is immediately durable."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def ident():
    return uuid.uuid4().hex


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS messages (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                    body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT,
                    body TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind, body):
        body = dict(body)
        body.setdefault('id', ident())
        with self.lock, self.connect() as db:
            db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?)',
                       (kind, body['id'], json.dumps(body)))
        return body

    def batch(self, records, events=()):
        """Commit related lifecycle records and their audit evidence together."""
        with self.lock, self.connect() as db:
            for kind, body in records:
                db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?)',
                           (kind, body['id'], json.dumps(body)))
            for event in events:
                db.execute('INSERT INTO events(task_id,body) VALUES (?,?)',
                           (event.get('task_id'), json.dumps(event)))

    def get(self, kind, record_id):
        with self.connect() as db:
            row = db.execute('SELECT body FROM records WHERE kind=? AND id=?',
                             (kind, record_id)).fetchone()
        return json.loads(row['body']) if row else None

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM records WHERE kind=? ORDER BY rowid', (kind,)).fetchall()
        return [json.loads(r['body']) for r in rows]

    def update(self, kind, record_id, **fields):
        with self.lock:
            body = self.get(kind, record_id)
            if body is None:
                raise KeyError(record_id)
            body.update(fields)
            return self.put(kind, body)

    def message(self, task_id, body):
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO messages(task_id,body) VALUES (?,?)', (task_id, json.dumps(body)))

    def messages(self, task_id):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM messages WHERE task_id=? ORDER BY seq', (task_id,)).fetchall()
        return [json.loads(r['body']) for r in rows]

    def event(self, action, task_id=None, **details):
        event = dict(id=ident(), action=action, task_id=task_id, created_at=now(), **details)
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO events(task_id,body) VALUES (?,?)', (task_id, json.dumps(event)))
        return event

    def events(self, task_id=None, limit=250):
        with self.connect() as db:
            if task_id:
                rows = db.execute('SELECT body FROM events WHERE task_id=? ORDER BY seq DESC LIMIT ?', (task_id, limit)).fetchall()
            else:
                rows = db.execute('SELECT body FROM events ORDER BY seq DESC LIMIT ?', (limit,)).fetchall()
        return [json.loads(r['body']) for r in rows]
