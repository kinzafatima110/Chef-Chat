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
    suggestion_seed_offset INTEGER DEFAULT 0,
    security_question TEXT,
    security_answer TEXT,
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

CREATE TABLE IF NOT EXISTS weekly_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    day_index INTEGER NOT NULL,
    dish TEXT NOT NULL,
    side_pairing TEXT,
    meal_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, day_index),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS custom_dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    serve_with TEXT NOT NULL,
    category TEXT NOT NULL,
    style TEXT NOT NULL,
    course TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, name),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS fridge_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    location TEXT NOT NULL, -- 'fridge', 'freezer', 'pantry'
    quantity TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, item_name, location),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS dish_ingredients (
    dish_name TEXT PRIMARY KEY,
    ingredients TEXT NOT NULL,
    raw_ingredients TEXT
);
CREATE TABLE IF NOT EXISTS friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    friend_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'accepted'
    created_at TEXT NOT NULL,
    UNIQUE(user_id, friend_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (friend_id) REFERENCES users(id)
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
    if "suggestion_seed_offset" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN suggestion_seed_offset INTEGER DEFAULT 0")
        conn.commit()
    if "security_question" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
        conn.commit()
    if "security_answer" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN security_answer TEXT")
        conn.commit()

    # Automatically seed master user accounts so deployments never lock you out
    from werkzeug.security import generate_password_hash
    default_users = [
        ("kinza.fatima.noorani@gmail.com", "Password123", "What is your favorite home-cooked dish?", "biryani"),
        ("admin@chefchat.com", "Password123", "What is your favorite home-cooked dish?", "biryani")
    ]
    for email, pwd, sec_q, sec_a in default_users:
        cursor = conn.execute("SELECT id FROM users WHERE email = ?", (email.lower(),))
        existing_row = cursor.fetchone()
        pwd_hash = generate_password_hash(pwd, method="pbkdf2:sha256")
        now = datetime.utcnow().isoformat()
        if not existing_row:
            conn.execute(
                """INSERT INTO users (
                    email, password_hash, onboarded, cooks_daily, wants_suggestions, 
                    diet_type, household_size, health_conscious, track_history, 
                    security_question, security_answer, created_at
                ) VALUES (?, ?, 1, 1, 1, 'nonveg', 4, 1, 1, ?, ?, ?)""",
                (email.lower(), pwd_hash, sec_q, sec_a.lower(), now)
            )
            conn.commit()
        else:
            conn.execute(
                "UPDATE users SET password_hash = ?, onboarded = 1, security_question = COALESCE(security_question, ?), security_answer = COALESCE(security_answer, ?) WHERE id = ?",
                (pwd_hash, sec_q, sec_a.lower(), existing_row[0])
            )
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


def create_user(email, password_hash, security_question=None, security_answer=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO users (email, password_hash, security_question, security_answer, created_at) VALUES (?, ?, ?, ?, ?)",
        (email.strip().lower(), password_hash, security_question, security_answer, datetime.utcnow().isoformat()),
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


def unblock_dish(user_id, dish):
    conn = get_conn()
    conn.execute(
        "DELETE FROM blocked_dishes WHERE user_id = ? AND dish = ?",
        (user_id, dish),
    )
    conn.commit()
    conn.close()


def get_blocked_dishes(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT dish FROM blocked_dishes WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]


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


def save_weekly_plan(user_id, plan_days):
    """
    Saves or overwrites a weekly plan.
    plan_days: List of dicts, e.g. [{"day_name": "Monday", "day_index": 0, "dish": "Chicken Karahi", "side_pairing": "Roti", "meal_type": "nonveg"}]
    """
    conn = get_conn()
    conn.execute("DELETE FROM weekly_plans WHERE user_id = ?", (user_id,))
    now = datetime.utcnow().isoformat()
    for day in plan_days:
        conn.execute(
            "INSERT INTO weekly_plans (user_id, day_name, day_index, dish, side_pairing, meal_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, day["day_name"], day["day_index"], day["dish"], day.get("side_pairing"), day["meal_type"], now)
        )
    conn.commit()
    conn.close()


def get_weekly_plan(user_id):
    """
    Returns the weekly plan ordered by day index.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM weekly_plans WHERE user_id = ? ORDER BY day_index ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_weekly_day(user_id, day_index, new_dish, new_side=None):
    """
    Updates a single day's plan.
    """
    conn = get_conn()
    conn.execute(
        "UPDATE weekly_plans SET dish = ?, side_pairing = ? WHERE user_id = ? AND day_index = ?",
        (new_dish, new_side, user_id, day_index)
    )
    conn.commit()
    conn.close()


def add_custom_dish(user_id, name, type_, serve_with, category, style, course):
    """
    Adds a custom user dish to their personalized inventory.
    """
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    try:
        conn.execute(
            "INSERT INTO custom_dishes (user_id, name, type, serve_with, category, style, course, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name.strip(), type_.strip(), serve_with.strip(), category.strip(), style.strip(), course.strip(), now)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success


def get_custom_dishes(user_id):
    """
    Retrieves all custom dishes created by the user.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT name, type, serve_with, category, style, course FROM custom_dishes WHERE user_id = ? ORDER BY name ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_fridge_item(user_id, item_name, location, quantity):
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    try:
        conn.execute(
            "INSERT INTO fridge_inventory (user_id, item_name, location, quantity, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, item_name.strip(), location.strip().lower(), quantity.strip() if quantity else "", now)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # If it already exists, let's update it!
        conn.execute(
            "UPDATE fridge_inventory SET quantity = ?, updated_at = ? WHERE user_id = ? AND item_name = ? AND location = ?",
            (quantity.strip() if quantity else "", now, user_id, item_name.strip(), location.strip().lower())
        )
        conn.commit()
        success = True
    conn.close()
    return success


def get_fridge_inventory(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, item_name, location, quantity, updated_at FROM fridge_inventory WHERE user_id = ? ORDER BY item_name ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_fridge_item(user_id, item_id):
    conn = get_conn()
    conn.execute(
        "DELETE FROM fridge_inventory WHERE user_id = ? AND id = ?",
        (user_id, item_id)
    )
    conn.commit()
    conn.close()


def update_fridge_item(user_id, item_id, quantity):
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE fridge_inventory SET quantity = ?, updated_at = ? WHERE user_id = ? AND id = ?",
        (quantity.strip() if quantity else "", now, user_id, item_id)
    )
    conn.commit()
    conn.close()


def save_dish_ingredients(dish_name, ingredients, raw_ingredients=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO dish_ingredients (dish_name, ingredients, raw_ingredients) VALUES (?, ?, ?)",
        (dish_name.strip(), ingredients.strip(), raw_ingredients.strip() if raw_ingredients else None)
    )
    conn.commit()
    conn.close()


def get_dish_ingredients_from_db(dish_name):
    conn = get_conn()
    row = conn.execute(
        "SELECT ingredients FROM dish_ingredients WHERE LOWER(dish_name) = LOWER(?)",
        (dish_name.strip(),)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def add_friend_request(user_id, friend_email):
    """
    Sends a pending friend request to another user by email.
    """
    conn = get_conn()
    friend = conn.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (friend_email.strip(),)).fetchone()
    if not friend:
        conn.close()
        return False, "User not found with that email."
        
    friend_id = friend["id"]
    if friend_id == user_id:
        conn.close()
        return False, "You cannot send a friend request to yourself!"
        
    # Check if a friendship or request already exists
    existing = conn.execute(
        "SELECT status FROM friendships WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)",
        (user_id, friend_id, friend_id, user_id)
    ).fetchone()
    
    if existing:
        conn.close()
        if existing["status"] == "accepted":
            return False, "You are already friends!"
        else:
            return False, "A friend request is already pending between you two."
            
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO friendships (user_id, friend_id, status, created_at) VALUES (?, ?, 'pending', ?)",
        (user_id, friend_id, now)
    )
    conn.commit()
    conn.close()
    return True, "Friend request sent successfully!"


def accept_friend_request(user_id, requester_id):
    """
    Accepts an incoming friend request and creates a mutual accepted friendship.
    """
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    # Update requester -> current user friendship to accepted
    conn.execute(
        "UPDATE friendships SET status = 'accepted' WHERE user_id = ? AND friend_id = ?",
        (requester_id, user_id)
    )
    # Insert mutual current user -> requester friendship
    conn.execute(
        "INSERT OR REPLACE INTO friendships (user_id, friend_id, status, created_at) VALUES (?, ?, 'accepted', ?)",
        (user_id, requester_id, now)
    )
    conn.commit()
    conn.close()


def reject_friend_request(user_id, requester_id):
    """
    Rejects or cancels a friend request.
    """
    conn = get_conn()
    conn.execute(
        "DELETE FROM friendships WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)",
        (requester_id, user_id, user_id, requester_id)
    )
    conn.commit()
    conn.close()


def get_friends(user_id):
    """
    Retrieves list of accepted friends.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT u.id, u.email FROM users u JOIN friendships f ON u.id = f.friend_id WHERE f.user_id = ? AND f.status = 'accepted' ORDER BY u.email ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_pending_friend_requests(user_id):
    """
    Retrieves incoming pending friend requests.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT u.id, u.email FROM users u JOIN friendships f ON u.id = f.user_id WHERE f.friend_id = ? AND f.status = 'pending' ORDER BY f.created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_friend_dish_suggestions(user_id):
    """
    Retrieves custom dishes created by friends that this user does not already have in their custom inventory.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course, u.email AS creator_email
        FROM custom_dishes cd
        JOIN users u ON cd.user_id = u.id
        WHERE cd.user_id IN (
            SELECT friend_id FROM friendships WHERE user_id = ? AND status = 'accepted'
        )
        AND LOWER(cd.name) NOT IN (
            SELECT LOWER(name) FROM custom_dishes WHERE user_id = ?
        )
        ORDER BY cd.created_at DESC
        """,
        (user_id, user_id)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
