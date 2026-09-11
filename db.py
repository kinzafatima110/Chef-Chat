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
    image TEXT,
    cuisine TEXT DEFAULT 'desi',
    is_public INTEGER NOT NULL DEFAULT 0,
    public_status TEXT DEFAULT 'private',
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

CREATE TABLE IF NOT EXISTS tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    is_public INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tip_likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tip_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(tip_id, user_id),
    FOREIGN KEY (tip_id) REFERENCES tips(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tip_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tip_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    comment TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tip_id) REFERENCES tips(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS comment_likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(comment_id, user_id),
    FOREIGN KEY (comment_id) REFERENCES tip_comments(id),
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
    if "suggestion_seed_offset" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN suggestion_seed_offset INTEGER DEFAULT 0")
        conn.commit()
    if "security_question" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
        conn.commit()
    if "security_answer" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN security_answer TEXT")
        conn.commit()

    # Migration: check and add custom_dishes columns if missing
    cursor = conn.execute("PRAGMA table_info(custom_dishes)")
    cd_columns = [row[1] for row in cursor.fetchall()]
    if "image" not in cd_columns:
        conn.execute("ALTER TABLE custom_dishes ADD COLUMN image TEXT")
        conn.commit()
    if "cuisine" not in cd_columns:
        conn.execute("ALTER TABLE custom_dishes ADD COLUMN cuisine TEXT DEFAULT 'desi'")
        conn.commit()
    if "is_public" not in cd_columns:
        conn.execute("ALTER TABLE custom_dishes ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    if "public_status" not in cd_columns:
        conn.execute("ALTER TABLE custom_dishes ADD COLUMN public_status TEXT DEFAULT 'private'")
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

    # Seed starter community kitchen tips if none exist
    try:
        tips_count = conn.execute("SELECT COUNT(*) FROM tips").fetchone()[0]
        if tips_count == 0:
            admin_id_row = conn.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1").fetchone()
            admin_id = admin_id_row[0] if admin_id_row else 1
            now = datetime.utcnow().isoformat()
            starter_tips = [
                ("Melt-in-Mouth Meat Tenderizing Hack", "When cooking tough beef cuts (like Nihari or Pasanday), marinate with 1 tbsp raw papaya paste with skin or 2 tbsp plain yogurt for 45 mins. It softens collagen without breaking the meat fibers!", "Meat & Cooking", 1),
                ("Restore Over-Salted Salan or Daal", "If you accidentally added too much salt to a curry or daal, peel a whole raw potato and drop it into the boiling pot for 10 minutes. The starch absorbs excess sodium like a sponge without changing the flavor!", "Kitchen Hacks", 1),
                ("The Golden 1:2 Water Ratio for Fluffy Rice", "Always soak Basmati rice for exactly 25 minutes before boiling. Drain completely, then use 1 part rice to 1.75 parts boiling water, seal tightly (Dum) on low heat for 12 minutes without opening the lid.", "Rice & Grains", 1)
            ]
            for t_title, t_content, t_cat, t_pub in starter_tips:
                conn.execute(
                    "INSERT INTO tips (user_id, title, content, category, is_public, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (admin_id, t_title, t_content, t_cat, t_pub, now)
                )
            conn.commit()
    except Exception:
        pass

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


def add_custom_dish(user_id, name, type_, serve_with, category, style, course, image=None, cuisine="desi", is_public=0, public_status="private"):
    """
    Adds a custom user dish to their personalized inventory with optional image, cuisine, and public status.
    """
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    try:
        conn.execute(
            """INSERT INTO custom_dishes (
                user_id, name, type, serve_with, category, style, course, image, cuisine, is_public, public_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, name.strip(), type_.strip(), serve_with.strip(), category.strip(),
                style.strip(), course.strip(), (image or "").strip(), (cuisine or "desi").strip().lower(),
                1 if is_public else 0, public_status.strip() if is_public else "private", now
            )
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
        "SELECT id, user_id, name, type, serve_with, category, style, course, image, cuisine, is_public, public_status, created_at FROM custom_dishes WHERE user_id = ? ORDER BY name ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_custom_dish(user_id, dish_name):
    """
    Removes a custom dish from user's inventory.
    """
    conn = get_conn()
    conn.execute("DELETE FROM custom_dishes WHERE user_id = ? AND name = ?", (user_id, dish_name.strip()))
    conn.commit()
    conn.close()
    return True


def get_public_recipes():
    """
    Retrieves all community dishes requested/marked as public.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT cd.id, cd.user_id, cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course,
               cd.image, cd.cuisine, cd.is_public, cd.public_status, cd.created_at,
               u.email AS creator_email
        FROM custom_dishes cd
        JOIN users u ON cd.user_id = u.id
        WHERE cd.is_public = 1
        ORDER BY cd.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recipe_of_the_week():
    """
    Returns the featured Recipe of the Week.
    """
    public = get_public_recipes()
    if public:
        return public[0]
    return {
        "name": "Chicken Manchurian with Fried Rice",
        "type": "nonveg",
        "serve_with": "rice",
        "category": "chinese",
        "style": "light",
        "course": "main",
        "cuisine": "chinese",
        "creator_email": "masterchef@chefchat.com",
        "image": "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/be/Punjabi_Chicken_Karahi.JPG/960px-Punjabi_Chicken_Karahi.JPG"
    }


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
        SELECT cd.id, cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course, cd.image, cd.cuisine, u.email AS creator_email
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


# ==========================================
# Kitchen Tips, Likes & Comments System
# ==========================================

def create_tip(user_id, title, content, category, is_public=1):
    """
    Creates a new kitchen tip/hack.
    """
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        "INSERT INTO tips (user_id, title, content, category, is_public, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, title.strip(), content.strip(), category.strip(), 1 if is_public else 0, now)
    )
    conn.commit()
    tip_id = cursor.lastrowid
    conn.close()
    return tip_id


def toggle_tip_like(tip_id, user_id):
    """
    Toggles like on a tip for a user. Returns (liked: bool, total_likes: int).
    """
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    row = conn.execute("SELECT id FROM tip_likes WHERE tip_id = ? AND user_id = ?", (tip_id, user_id)).fetchone()
    if row:
        conn.execute("DELETE FROM tip_likes WHERE id = ?", (row["id"],))
        liked = False
    else:
        conn.execute("INSERT INTO tip_likes (tip_id, user_id, created_at) VALUES (?, ?, ?)", (tip_id, user_id, now))
        liked = True
    conn.commit()
    count_row = conn.execute("SELECT COUNT(*) AS cnt FROM tip_likes WHERE tip_id = ?", (tip_id,)).fetchone()
    like_count = count_row["cnt"] if count_row else 0
    conn.close()
    return liked, like_count


def toggle_comment_like(comment_id, user_id):
    """
    Toggles upvote/like on a tip comment for a user. Returns (liked: bool, total_likes: int).
    """
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    row = conn.execute("SELECT id FROM comment_likes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id)).fetchone()
    if row:
        conn.execute("DELETE FROM comment_likes WHERE id = ?", (row["id"],))
        liked = False
    else:
        conn.execute("INSERT INTO comment_likes (comment_id, user_id, created_at) VALUES (?, ?, ?)", (comment_id, user_id, now))
        liked = True
    conn.commit()
    count_row = conn.execute("SELECT COUNT(*) AS cnt FROM comment_likes WHERE comment_id = ?", (comment_id,)).fetchone()
    like_count = count_row["cnt"] if count_row else 0
    conn.close()
    return liked, like_count


def add_tip_comment(tip_id, user_id, comment):
    """
    Adds a comment to a tip.
    """
    if not comment or not comment.strip():
        return False
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO tip_comments (tip_id, user_id, comment, created_at) VALUES (?, ?, ?, ?)",
        (tip_id, user_id, comment.strip(), now)
    )
    conn.commit()
    conn.close()
    return True


def delete_tip(tip_id, user_id):
    """
    Deletes a tip owned by user_id along with its likes, comments, and comment upvotes.
    """
    conn = get_conn()
    tip = conn.execute("SELECT id FROM tips WHERE id = ? AND user_id = ?", (tip_id, user_id)).fetchone()
    if not tip:
        conn.close()
        return False

    conn.execute(
        "DELETE FROM comment_likes WHERE comment_id IN (SELECT id FROM tip_comments WHERE tip_id = ?)",
        (tip_id,)
    )
    conn.execute("DELETE FROM tip_likes WHERE tip_id = ?", (tip_id,))
    conn.execute("DELETE FROM tip_comments WHERE tip_id = ?", (tip_id,))
    conn.execute("DELETE FROM tips WHERE id = ? AND user_id = ?", (tip_id, user_id))
    conn.commit()
    conn.close()
    return True


def get_tips(current_user_id=None, sort_by="top"):
    """
    Retrieves public tips and user's private tips with likes, comments, author info, and comment upvotes.
    """
    conn = get_conn()
    query = """
        SELECT t.id, t.user_id, t.title, t.content, t.category, t.is_public, t.created_at,
               u.email AS author_email,
               (SELECT COUNT(*) FROM tip_likes tl WHERE tl.tip_id = t.id) AS like_count,
               (SELECT COUNT(*) FROM tip_comments tc WHERE tc.tip_id = t.id) AS comment_count
        FROM tips t
        JOIN users u ON t.user_id = u.id
        WHERE t.is_public = 1 OR t.user_id = ?
    """
    if sort_by == "recent":
        query += " ORDER BY t.created_at DESC"
    else:
        query += " ORDER BY like_count DESC, t.created_at DESC"

    rows = conn.execute(query, (current_user_id or 0,)).fetchall()
    tips = [dict(r) for r in rows]

    for tip in tips:
        # Check if current user liked tip
        if current_user_id:
            liked_row = conn.execute(
                "SELECT id FROM tip_likes WHERE tip_id = ? AND user_id = ?",
                (tip["id"], current_user_id)
            ).fetchone()
            tip["has_liked"] = bool(liked_row)
        else:
            tip["has_liked"] = False

        # Fetch comments with comment likes count & user liked status
        comment_rows = conn.execute(
            """SELECT tc.id, tc.tip_id, tc.user_id, tc.comment, tc.created_at, u.email AS commenter_email,
                      (SELECT COUNT(*) FROM comment_likes cl WHERE cl.comment_id = tc.id) AS like_count
               FROM tip_comments tc
               JOIN users u ON tc.user_id = u.id
               WHERE tc.tip_id = ?
               ORDER BY tc.created_at ASC""",
            (tip["id"],)
        ).fetchall()

        comments = []
        for c in comment_rows:
            c_dict = dict(c)
            if current_user_id:
                cliked_row = conn.execute(
                    "SELECT id FROM comment_likes WHERE comment_id = ? AND user_id = ?",
                    (c_dict["id"], current_user_id)
                ).fetchone()
                c_dict["has_liked"] = bool(cliked_row)
            else:
                c_dict["has_liked"] = False
            comments.append(c_dict)

        tip["comments"] = comments

    conn.close()
    return tips


def get_tip_of_the_week(current_user_id=None):
    """
    Returns the #1 highest-voted public tip (Tip of the Week).
    """
    tips = get_tips(current_user_id=current_user_id, sort_by="top")
    public_tips = [t for t in tips if t.get("is_public")]
    return public_tips[0] if public_tips else None

