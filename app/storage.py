import sqlite3
from typing import Optional, List, Tuple, Any
from datetime import datetime
import threading
from . import config

_lock = threading.Lock()


def get_conn():
    url = config.DATABASE_URL
    # support formats like sqlite:////data/app.db
    if url.startswith('sqlite:'):
        # extract file path after 'sqlite:'
        rem = url[len('sqlite:'):]
        # common forms:
        # sqlite:////data/app.db -> rem = ////data/app.db -> want /data/app.db
        # sqlite:///relative/path.db -> rem = ///relative/path.db -> want /relative/path.db
        if rem.startswith('////'):
            file_path = rem[3:]
        elif rem.startswith('///'):
            file_path = rem[2:]
        else:
            # fallback strip one leading ':' or slash
            file_path = rem.lstrip(':')
        return sqlite3.connect(file_path, check_same_thread=False)
    raise ValueError('DATABASE_URL must be sqlite')


def init_db():
    with _lock:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    from_msisdn TEXT NOT NULL,
                    to_msisdn TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    text TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.commit()
        finally:
            conn.close()


def insert_message(message_id: str, from_msisdn: str, to_msisdn: str, ts: str, text: Optional[str]) -> str:
    """Insert a message. Return 'created' or 'duplicate'."""
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = get_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at) VALUES (?,?,?,?,?,?)",
                (message_id, from_msisdn, to_msisdn, ts, text, now),
            )
            conn.commit()
            return 'created'
        except sqlite3.IntegrityError:
            return 'duplicate'
    finally:
        conn.close()


def query_messages(limit: int, offset: int, from_msisdn: Optional[str], since: Optional[str], q: Optional[str]) -> Tuple[List[Tuple[Any, ...]], int]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        filters = []
        params: list = []
        if from_msisdn:
            filters.append('from_msisdn = ?')
            params.append(from_msisdn)
        if since:
            filters.append('ts >= ?')
            params.append(since)
        if q:
            filters.append('LOWER(text) LIKE ?')
            params.append(f'%{q.lower()}%')
        where = 'WHERE ' + ' AND '.join(filters) if filters else ''
        total_q = f"SELECT COUNT(*) FROM messages {where}"
        cur.execute(total_q, params)
        total = cur.fetchone()[0]
        q_sql = f"SELECT message_id, from_msisdn, to_msisdn, ts, text, created_at FROM messages {where} ORDER BY ts ASC, message_id ASC LIMIT ? OFFSET ?"
        cur.execute(q_sql, params + [limit, offset])
        rows = cur.fetchall()
        return rows, total
    finally:
        conn.close()


def stats() -> dict:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM messages")
        total_messages = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT from_msisdn) FROM messages")
        senders_count = cur.fetchone()[0]
        cur.execute("SELECT from_msisdn, COUNT(*) as c FROM messages GROUP BY from_msisdn ORDER BY c DESC LIMIT 10")
        rows = cur.fetchall()
        messages_per_sender = [{"from": r[0], "count": r[1]} for r in rows]
        cur.execute("SELECT MIN(ts), MAX(ts) FROM messages")
        minmax = cur.fetchone()
        first_ts, last_ts = minmax[0], minmax[1]
        return {
            "total_messages": total_messages,
            "senders_count": senders_count,
            "messages_per_sender": messages_per_sender,
            "first_message_ts": first_ts,
            "last_message_ts": last_ts,
        }
    finally:
        conn.close()


def db_ready() -> bool:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        row = cur.fetchone()
        conn.close()
        return row is not None
    except Exception:
        return False
