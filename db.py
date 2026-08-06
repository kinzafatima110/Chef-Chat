import sqlite3
from datetime import date, datetime

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    onboarded INTEGER NOT NULL DEFAULT 0,
    cooks_daily INTEGER,
    wants_suggestions INTEGER,
    diet_type TEXT,
    diet_rule TEXT,
    household_size INTEGER,
    health_conscious INTEGER,
    track_history INTEGER,
    last_suggested TEXT,
    wa_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    meal_date TEXT NOT NULL,
    dish TEXT NOT NULL,
    category TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS blocked_dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    dish TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, dish),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    # Migration: check and add wa_id column if not exists
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if "wa_id" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN wa_id TEXT")
        conn.commit()
    conn.close()


def get_user_by_id(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(email, password_hash):
    conn = get_conn()
    conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
        (email, password_hash, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return get_user_by_email(email)


def update_user(user_id, **fields):
    if not fields:
        return
    columns = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [user_id]
    conn = get_conn()
    conn.execute(f"UPDATE users SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()


def log_meal(user_id, dish, category=None, meal_date=None):
    meal_date = meal_date or date.today().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO meals (user_id, meal_date, dish, category, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, meal_date, dish, category, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def recent_dishes(user_id, limit=7):
    conn = get_conn()
    rows = conn.execute(
        "SELECT dish, category, meal_date FROM meals WHERE user_id = ? ORDER BY meal_date DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def block_dish(user_id, dish):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO blocked_dishes (user_id, dish, created_at) VALUES (?, ?, ?)",
        (user_id, dish, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def blocked_dishes(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT dish FROM blocked_dishes WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return {row["dish"] for row in rows}


def all_onboarded_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users WHERE onboarded = 1 AND wa_id IS NOT NULL").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_by_wa_id(wa_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE wa_id = ?", (wa_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
