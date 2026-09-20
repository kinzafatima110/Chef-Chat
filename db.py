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
    preferred_cuisine TEXT DEFAULT 'all',
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
    description TEXT,
    prep_time TEXT,
    cook_time TEXT,
    servings TEXT,
    ingredients TEXT,
    instructions TEXT,
    tips TEXT,
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

CREATE TABLE IF NOT EXISTS shopping_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    category TEXT DEFAULT 'produce', -- 'produce', 'meat', 'dairy', 'pantry', 'spices', 'general'
    quantity TEXT,
    is_bought INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_appliances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    appliance_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'owned', -- 'owned' or 'wishlist'
    custom_name TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, appliance_id),
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
    if "preferred_cuisine" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN preferred_cuisine TEXT DEFAULT 'all'")
        conn.commit()

    # Migration: ensure user_appliances table exists
    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_appliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        appliance_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'owned',
        custom_name TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, appliance_id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
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
    for col, col_type in [
        ("description", "TEXT"),
        ("prep_time", "TEXT"),
        ("cook_time", "TEXT"),
        ("servings", "TEXT"),
        ("ingredients", "TEXT"),
        ("instructions", "TEXT"),
        ("tips", "TEXT")
    ]:
        if col not in cd_columns:
            conn.execute(f"ALTER TABLE custom_dishes ADD COLUMN {col} {col_type}")
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


def add_custom_dish(
    user_id, name, type_, serve_with, category, style, course,
    image=None, cuisine="desi", description=None, prep_time="15 mins",
    cook_time="30 mins", servings="4 servings", ingredients=None,
    instructions=None, tips=None, is_public=0, public_status="private"
):
    """
    Adds a custom user dish to their personalized inventory with optional image, written ingredients, instructions, and metadata.
    """
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    try:
        conn.execute(
            """INSERT INTO custom_dishes (
                user_id, name, type, serve_with, category, style, course, image, cuisine,
                description, prep_time, cook_time, servings, ingredients, instructions, tips,
                is_public, public_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, name.strip(), type_.strip(), serve_with.strip(), category.strip(),
                style.strip(), course.strip(), (image or "").strip(), (cuisine or "desi").strip().lower(),
                (description or "").strip(), (prep_time or "15 mins").strip(), (cook_time or "30 mins").strip(),
                (servings or "4 servings").strip(), (ingredients or "").strip(), (instructions or "").strip(),
                (tips or "").strip(), 1 if is_public else 0, public_status.strip() if is_public else "private", now
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
    Retrieves all custom dishes created by the user with full written recipe metadata.
    """
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, user_id, name, type, serve_with, category, style, course, image, cuisine,
                  description, prep_time, cook_time, servings, ingredients, instructions, tips,
                  is_public, public_status, created_at 
           FROM custom_dishes WHERE user_id = ? ORDER BY name ASC""",
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
    Retrieves all community dishes requested/marked as public with full written recipe metadata.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT cd.id, cd.user_id, cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course,
               cd.image, cd.cuisine, cd.description, cd.prep_time, cd.cook_time, cd.servings,
               cd.ingredients, cd.instructions, cd.tips, cd.is_public, cd.public_status, cd.created_at,
               u.email AS creator_email
        FROM custom_dishes cd
        JOIN users u ON cd.user_id = u.id
        WHERE cd.is_public = 1
        ORDER BY cd.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recipe_by_id(recipe_id):
    """
    Retrieves full details for a recipe by ID.
    """
    conn = get_conn()
    row = conn.execute(
        """
        SELECT cd.id, cd.user_id, cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course,
               cd.image, cd.cuisine, cd.description, cd.prep_time, cd.cook_time, cd.servings,
               cd.ingredients, cd.instructions, cd.tips, cd.is_public, cd.public_status, cd.created_at,
               u.email AS creator_email
        FROM custom_dishes cd
        JOIN users u ON cd.user_id = u.id
        WHERE cd.id = ?
        """,
        (int(recipe_id),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_dish_recipe_card(dish_name, user_id=None):
    """
    Constructs a rich Kitchn-style recipe card for ANY dish (custom or core menu).
    """
    conn = get_conn()
    clean_name = dish_name.strip()
    
    # Check if exists in custom dishes first
    if user_id:
        custom_row = conn.execute(
            """SELECT cd.id, cd.user_id, cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course,
                      cd.image, cd.cuisine, cd.description, cd.prep_time, cd.cook_time, cd.servings,
                      cd.ingredients, cd.instructions, cd.tips, cd.is_public, cd.public_status, cd.created_at,
                      u.email AS creator_email
               FROM custom_dishes cd
               JOIN users u ON cd.user_id = u.id
               WHERE LOWER(cd.name) = LOWER(?) AND (cd.user_id = ? OR cd.is_public = 1)""",
            (clean_name, user_id)
        ).fetchone()
        if custom_row:
            conn.close()
            return dict(custom_row)
            
    # Check public dishes generally
    pub_row = conn.execute(
        """SELECT cd.id, cd.user_id, cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course,
                  cd.image, cd.cuisine, cd.description, cd.prep_time, cd.cook_time, cd.servings,
                  cd.ingredients, cd.instructions, cd.tips, cd.is_public, cd.public_status, cd.created_at,
                  u.email AS creator_email
           FROM custom_dishes cd
           JOIN users u ON cd.user_id = u.id
           WHERE LOWER(cd.name) = LOWER(?) AND cd.is_public = 1""",
        (clean_name,)
    ).fetchone()
    if pub_row:
        conn.close()
        return dict(pub_row)

    # Core menu fallback: generate rich recipe card using dish_ingredients
    ing_row = conn.execute(
        "SELECT ingredients FROM dish_ingredients WHERE LOWER(dish_name) = LOWER(?)",
        (clean_name,)
    ).fetchone()
    conn.close()

    from suggestions import DISHES, get_dish_image
    core_dish = next((d for d in DISHES if d["name"].lower() == clean_name.lower()), None)
    
    ing_str = ing_row["ingredients"] if ing_row and ing_row["ingredients"] else ""
    if not ing_str and core_dish:
        ing_str = f"{core_dish['name']} fresh cuts or main produce, cooking oil, onions, ginger garlic paste, salt & traditional spices"
        
    # Build default professional step-by-step instructions
    inst_lines = [
        f"Gather and prepare all fresh ingredients and spices as listed.",
        f"Heat cooking oil in a pan or deep pot over medium heat. Sauté aromatics (onions, ginger, garlic) until fragrant and golden.",
        f"Add the main ingredients and seasonings. Cook thoroughly until tender, aromatic, and flavorful.",
        f"Simmer on low heat (dum) for 5-10 minutes until the gravy reaches the desired rich consistency.",
        f"Garnish with freshly chopped coriander and julienned ginger. Serve hot with roti or steamed basmati rice!"
    ]
    
    return {
        "id": None,
        "name": clean_name,
        "type": core_dish["type"] if core_dish else "nonveg",
        "serve_with": core_dish["serve_with"] if core_dish else "both",
        "category": core_dish["category"] if core_dish else "curry",
        "style": core_dish["style"] if core_dish else "rich",
        "course": core_dish["course"] if core_dish else "main",
        "cuisine": core_dish.get("cuisine", "desi") if core_dish else "desi",
        "image": get_dish_image(core_dish or {"name": clean_name}),
        "description": f"Classic and authentic {clean_name} prepared with home-style spices and rich aromatics.",
        "prep_time": "15 mins",
        "cook_time": "30-40 mins",
        "servings": "4-6 servings",
        "ingredients": ing_str,
        "instructions": "\n".join(inst_lines),
        "tips": "For best flavor, allow the spices to bloom gently in oil before adding proteins or vegetables.",
        "is_public": 1,
        "creator_email": "Chef Chat Editorial",
        "created_at": datetime.utcnow().isoformat()
    }


def get_recipe_of_the_week():
    """
    Returns the featured Recipe of the Week.
    """
    public = get_public_recipes()
    if public:
        return public[0]
    return get_dish_recipe_card("Chicken Manchurian with Fried Rice")


def get_nearby_marts():
    """
    Returns curated nearby grocery marts and supermarkets with location and online ordering links.
    """
    return [
        {
            "name": "Imtiaz Super Market",
            "type": "Superstore / Hypermarket",
            "icon": "storefront",
            "timing": "9:00 AM - 12:00 AM",
            "delivery": "Same-day Delivery Available",
            "url": "https://www.google.com/maps/search/Imtiaz+Super+Market+near+me",
            "badge": "Popular Mart ⭐"
        },
        {
            "name": "PandaMart (Foodpanda Groceries)",
            "type": "Express Grocery Delivery",
            "icon": "delivery_dining",
            "timing": "24/7 Delivery (15-30 mins)",
            "delivery": "Instant 20-min Delivery",
            "url": "https://www.foodpanda.pk/darkstore",
            "badge": "Fastest ⚡"
        },
        {
            "name": "Carrefour Hypermarket",
            "type": "Hypermarket & Fresh Produce",
            "icon": "shopping_cart",
            "timing": "10:00 AM - 11:30 PM",
            "delivery": "Online App & Store Pickup",
            "url": "https://www.google.com/maps/search/Carrefour+near+me",
            "badge": "Fresh Meats & Veggies 🥦"
        },
        {
            "name": "Metro Cash & Carry",
            "type": "Wholesale & Bulk Rashan",
            "icon": "inventory_2",
            "timing": "9:00 AM - 11:00 PM",
            "delivery": "Wholesale Bulk Rashan",
            "url": "https://www.google.com/maps/search/Metro+Cash+and+Carry+near+me",
            "badge": "Best for Monthly Rashan 🌾"
        },
        {
            "name": "Local Butcher & Meat Shop",
            "type": "Fresh Halal Meats & Chicken",
            "icon": "egg",
            "timing": "7:00 AM - 10:00 PM",
            "delivery": "Fresh Cuts & Mince",
            "url": "https://www.google.com/maps/search/meat+shop+or+butcher+near+me",
            "badge": "Fresh Cuts 🍗"
        },
        {
            "name": "Local Green Grocer & Sabzi Mandi",
            "type": "Fresh Daily Vegetables & Herbs",
            "icon": "eco",
            "timing": "7:00 AM - 11:00 PM",
            "delivery": "Daily Morning Farm Fresh",
            "url": "https://www.google.com/maps/search/vegetable+shop+near+me",
            "badge": "Fresh Farm Produce 🍅"
        }
    ]


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
# Instagram-Style Chef Network & Following System
# ==========================================

CHEF_TITLES = [
    "Master Chef & Biryani Specialist 🍛",
    "Executive Home Chef & Karahi Maestro 🍳",
    "Gourmet Bistro Artisan 🥩",
    "Asian Wok & Stir-Fry Virtuoso 🥢",
    "Healthy Meal Prep & Diet Specialist 🥗",
    "Traditional Desi Dum Specialist 🫓",
    "Culinary Creator & Spice Explorer 🌶️"
]


def format_chef_name(email):
    """
    Generates a stylized chef display name from an email.
    """
    if not email:
        return "Chef Guest"
    username = email.split("@")[0]
    clean = "".join(c if c.isalpha() else " " for c in username).strip()
    words = [w.capitalize() for w in clean.split() if w]
    name_str = " ".join(words) if words else username.capitalize()
    return f"Chef {name_str}"


def get_chef_title_for_user(user_id, recipe_count=0):
    """
    Assigns a prestigious chef title based on user id and recipe count.
    """
    if recipe_count >= 10:
        return "Executive Grand Master Chef 🌟👨‍🍳"
    elif recipe_count >= 5:
        return "Senior Culinary Specialist 🏆"
    idx = user_id % len(CHEF_TITLES)
    return CHEF_TITLES[idx]


def get_chef_profile(user_id):
    """
    Retrieves comprehensive chef profile metrics for a user.
    """
    conn = get_conn()
    user_row = conn.execute("SELECT id, email, created_at, preferred_cuisine, diet_type FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user_row:
        conn.close()
        return None

    email = user_row["email"]
    recipe_count = conn.execute("SELECT COUNT(*) FROM custom_dishes WHERE user_id = ?", (user_id,)).fetchone()[0]
    public_recipe_count = conn.execute("SELECT COUNT(*) FROM custom_dishes WHERE user_id = ? AND is_public = 1", (user_id,)).fetchone()[0]
    following_count = conn.execute("SELECT COUNT(*) FROM friendships WHERE user_id = ? AND status = 'accepted'", (user_id,)).fetchone()[0]
    followers_count = conn.execute("SELECT COUNT(*) FROM friendships WHERE friend_id = ? AND status = 'accepted'", (user_id,)).fetchone()[0]
    appliances_count = conn.execute("SELECT COUNT(*) FROM user_appliances WHERE user_id = ? AND status = 'owned'", (user_id,)).fetchone()[0]
    tips_count = conn.execute("SELECT COUNT(*) FROM tips WHERE user_id = ?", (user_id,)).fetchone()[0]
    conn.close()

    return {
        "id": user_id,
        "email": email,
        "chef_name": format_chef_name(email),
        "handle": f"@{email.split('@')[0]}",
        "title": get_chef_title_for_user(user_id, recipe_count),
        "bio": "Culinary explorer on Chef Chat • Sharing handcrafted recipes, kitchen tips, and daily meal inspirations.",
        "recipe_count": recipe_count,
        "public_recipe_count": public_recipe_count,
        "following_count": following_count,
        "followers_count": followers_count,
        "appliances_count": appliances_count,
        "tips_count": tips_count,
        "created_at": user_row["created_at"]
    }


def follow_chef(user_id, target_chef_id):
    """
    Follows a chef. Creates an accepted following relationship.
    """
    if int(user_id) == int(target_chef_id):
        return False, "You cannot follow your own chef profile!"
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO friendships (user_id, friend_id, status, created_at) VALUES (?, ?, 'accepted', ?)",
        (int(user_id), int(target_chef_id), now)
    )
    conn.commit()
    target_row = conn.execute("SELECT email FROM users WHERE id = ?", (int(target_chef_id),)).fetchone()
    conn.close()
    chef_name = format_chef_name(target_row["email"]) if target_row else "Chef"
    return True, f"You are now following {chef_name}! 👨‍🍳✨"


def unfollow_chef(user_id, target_chef_id):
    """
    Unfollows a chef.
    """
    conn = get_conn()
    conn.execute(
        "DELETE FROM friendships WHERE user_id = ? AND friend_id = ?",
        (int(user_id), int(target_chef_id))
    )
    conn.commit()
    target_row = conn.execute("SELECT email FROM users WHERE id = ?", (int(target_chef_id),)).fetchone()
    conn.close()
    chef_name = format_chef_name(target_row["email"]) if target_row else "Chef"
    return True, f"Unfollowed {chef_name}."


def toggle_follow_chef(user_id, target_chef_id):
    """
    Toggles following status for a target chef. Returns (is_following: bool, message: str).
    """
    if int(user_id) == int(target_chef_id):
        return False, "You cannot follow yourself."
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM friendships WHERE user_id = ? AND friend_id = ? AND status = 'accepted'",
        (int(user_id), int(target_chef_id))
    ).fetchone()
    conn.close()
    if row:
        _, msg = unfollow_chef(user_id, target_chef_id)
        return False, msg
    else:
        _, msg = follow_chef(user_id, target_chef_id)
        return True, msg


def follow_chef_by_email(user_id, target_email):
    """
    Looks up a chef by email and follows them.
    """
    clean_email = (target_email or "").strip().lower()
    if not clean_email:
        return False, "Please enter a valid chef email address."
    conn = get_conn()
    row = conn.execute("SELECT id, email FROM users WHERE LOWER(email) = ?", (clean_email,)).fetchone()
    conn.close()
    if not row:
        return False, f"No registered chef found with email '{clean_email}'. Invite them to join Chef Chat!"
    if row["id"] == user_id:
        return False, "You cannot follow yourself!"
    return follow_chef(user_id, row["id"])


def get_following_chefs(user_id):
    """
    Retrieves all chefs followed by user_id with rich profile info.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT u.id, u.email, u.created_at, f.created_at AS followed_at,
               (SELECT COUNT(*) FROM custom_dishes cd WHERE cd.user_id = u.id) AS recipe_count,
               (SELECT COUNT(*) FROM friendships f2 WHERE f2.friend_id = u.id AND f2.status = 'accepted') AS followers_count,
               (SELECT COUNT(*) FROM friendships f3 WHERE f3.user_id = u.id AND f3.friend_id = ? AND f3.status = 'accepted') AS follows_you
        FROM friendships f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = ? AND f.status = 'accepted'
        ORDER BY f.created_at DESC
        """,
        (user_id, user_id)
    ).fetchall()

    chefs = []
    for r in rows:
        c_dict = dict(r)
        c_dict["chef_name"] = format_chef_name(c_dict["email"])
        c_dict["handle"] = f"@{c_dict['email'].split('@')[0]}"
        c_dict["title"] = get_chef_title_for_user(c_dict["id"], c_dict["recipe_count"])
        c_dict["is_following"] = True
        c_dict["follows_you"] = bool(c_dict["follows_you"])

        # Fetch recent 3 dishes
        dish_rows = conn.execute(
            "SELECT name, cuisine, image, type FROM custom_dishes WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
            (c_dict["id"],)
        ).fetchall()
        c_dict["recent_dishes"] = [dict(d) for d in dish_rows]
        chefs.append(c_dict)

    conn.close()
    return chefs


def get_chef_followers(user_id):
    """
    Retrieves all followers of user_id with reciprocal status.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT u.id, u.email, u.created_at, f.created_at AS followed_at,
               (SELECT COUNT(*) FROM custom_dishes cd WHERE cd.user_id = u.id) AS recipe_count,
               (SELECT COUNT(*) FROM friendships f2 WHERE f2.friend_id = u.id AND f2.status = 'accepted') AS followers_count,
               (SELECT COUNT(*) FROM friendships f3 WHERE f3.user_id = ? AND f3.friend_id = u.id AND f3.status = 'accepted') AS is_following
        FROM friendships f
        JOIN users u ON f.user_id = u.id
        WHERE f.friend_id = ? AND f.status = 'accepted'
        ORDER BY f.created_at DESC
        """,
        (user_id, user_id)
    ).fetchall()

    followers = []
    for r in rows:
        f_dict = dict(r)
        f_dict["chef_name"] = format_chef_name(f_dict["email"])
        f_dict["handle"] = f"@{f_dict['email'].split('@')[0]}"
        f_dict["title"] = get_chef_title_for_user(f_dict["id"], f_dict["recipe_count"])
        f_dict["is_following"] = bool(f_dict["is_following"])
        f_dict["follows_you"] = True

        dish_rows = conn.execute(
            "SELECT name, cuisine, image, type FROM custom_dishes WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
            (f_dict["id"],)
        ).fetchall()
        f_dict["recent_dishes"] = [dict(d) for d in dish_rows]
        followers.append(f_dict)

    conn.close()
    return followers


def get_discover_chefs(user_id, limit=12):
    """
    Discovers other chefs in the Chef Chat network not yet followed by user_id.
    Also injects starter community master chefs if user pool is growing.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT u.id, u.email, u.created_at,
               (SELECT COUNT(*) FROM custom_dishes cd WHERE cd.user_id = u.id) AS recipe_count,
               (SELECT COUNT(*) FROM friendships f2 WHERE f2.friend_id = u.id AND f2.status = 'accepted') AS followers_count,
               (SELECT COUNT(*) FROM friendships f3 WHERE f3.user_id = u.id AND f3.friend_id = ? AND f3.status = 'accepted') AS follows_you
        FROM users u
        WHERE u.id != ? AND u.id NOT IN (
            SELECT friend_id FROM friendships WHERE user_id = ? AND status = 'accepted'
        )
        ORDER BY recipe_count DESC, followers_count DESC, u.id ASC
        LIMIT ?
        """,
        (user_id, user_id, user_id, limit)
    ).fetchall()

    discover = []
    for r in rows:
        d_dict = dict(r)
        d_dict["chef_name"] = format_chef_name(d_dict["email"])
        d_dict["handle"] = f"@{d_dict['email'].split('@')[0]}"
        d_dict["title"] = get_chef_title_for_user(d_dict["id"], d_dict["recipe_count"])
        d_dict["is_following"] = False
        d_dict["follows_you"] = bool(d_dict["follows_you"])
        d_dict["is_virtual"] = False

        dish_rows = conn.execute(
            "SELECT name, cuisine, image, type FROM custom_dishes WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
            (d_dict["id"],)
        ).fetchall()
        d_dict["recent_dishes"] = [dict(d) for d in dish_rows]
        discover.append(d_dict)

    conn.close()

    # Curated trending community master chefs to make the discover feed rich and inspiring
    curated_chefs = [
        {
            "id": 9991,
            "email": "fatima.masterchef@chefchat.com",
            "chef_name": "Chef Fatima Noor",
            "handle": "@fatima_culinary",
            "title": "Grand Master Chef • Royal Mughlai & Dum Biryanis 👑🍛",
            "recipe_count": 18,
            "followers_count": 240,
            "is_following": False,
            "follows_you": False,
            "is_virtual": True,
            "specialty": "Slow Dum Biryanis & Velvet Kormas",
            "recent_dishes": [
                {"name": "Hyderabadi Dum Biryani", "cuisine": "desi", "type": "nonveg", "image": "images/biryani.jpg"},
                {"name": "Shahi Mutton Korma", "cuisine": "desi", "type": "nonveg", "image": "images/korma.jpg"},
                {"name": "Zafrani Kheer", "cuisine": "desi", "type": "veg", "image": "images/halwa.jpg"}
            ]
        },
        {
            "id": 9992,
            "email": "tariq.karahi@chefchat.com",
            "chef_name": "Chef Tariq Gourmet",
            "handle": "@tariq_wok_grill",
            "title": "Shinwari Karahi & BBQ Grill Artisan 🍢",
            "recipe_count": 14,
            "followers_count": 185,
            "is_following": False,
            "follows_you": False,
            "is_virtual": True,
            "specialty": "Namkeen Karahi, BBQ Tikka & Tandoor",
            "recent_dishes": [
                {"name": "Peshawari Shinwari Karahi", "cuisine": "desi", "type": "nonveg", "image": "images/chicken_karahi.jpg"},
                {"name": "Melt-in-Mouth Seekh Kabab", "cuisine": "desi", "type": "nonveg", "image": "images/tikka.jpg"},
                {"name": "Charred Chicken Tikka Boti", "cuisine": "desi", "type": "nonveg", "image": "images/tikka.jpg"}
            ]
        },
        {
            "id": 9993,
            "email": "ayesha.healthy@chefchat.com",
            "chef_name": "Chef Ayesha Green",
            "handle": "@ayesha_healthy_bites",
            "title": "Clean Eating & Diet Macro Specialist 🥗🥑",
            "recipe_count": 12,
            "followers_count": 310,
            "is_following": False,
            "follows_you": False,
            "is_virtual": True,
            "specialty": "High Protein Salads & Low-Oil Curries",
            "recent_dishes": [
                {"name": "Grilled Lemon Herb Chicken Bowl", "cuisine": "diet", "type": "nonveg", "image": "images/tikka.jpg"},
                {"name": "Crispy Air-Fryer Falafel & Hummus", "cuisine": "diet", "type": "veg", "image": "images/daal.jpg"},
                {"name": "Quinoa Veggie Power Bowl", "cuisine": "diet", "type": "veg", "image": "images/salad.jpg"}
            ]
        },
        {
            "id": 9994,
            "email": "saad.bistro@chefchat.com",
            "chef_name": "Chef Saad Bistro",
            "handle": "@saad_continental",
            "title": "Italian Pastas & Continental Steaks 🍝🥩",
            "recipe_count": 15,
            "followers_count": 195,
            "is_following": False,
            "follows_you": False,
            "is_virtual": True,
            "specialty": "Creamy Fettuccine Alfredo & Sizzling Steaks",
            "recent_dishes": [
                {"name": "Fettuccine Alfredo with Grilled Chicken", "cuisine": "continental", "type": "nonveg", "image": "images/pasta.jpg"},
                {"name": "Black Pepper Beef Steak", "cuisine": "continental", "type": "nonveg", "image": "images/chicken_karahi.jpg"},
                {"name": "Crispy Garlic Butter Prawns", "cuisine": "continental", "type": "nonveg", "image": "images/fish.jpg"}
            ]
        }
    ]

    # Combine discover users
    existing_emails = {d["email"].lower() for d in discover}
    for c in curated_chefs:
        if c["email"].lower() not in existing_emails:
            discover.append(c)

    return discover


def get_chef_activity_feed(user_id):
    """
    Returns an Instagram-style feed of recent recipes posted by followed chefs and featured creators.
    """
    conn = get_conn()
    # Recipes from followed chefs
    followed_rows = conn.execute(
        """
        SELECT cd.id, cd.user_id, cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course,
               cd.image, cd.cuisine, cd.description, cd.prep_time, cd.cook_time, cd.servings,
               cd.ingredients, cd.instructions, cd.tips, cd.created_at, u.email AS creator_email,
               1 AS is_followed_creator
        FROM custom_dishes cd
        JOIN users u ON cd.user_id = u.id
        WHERE cd.user_id IN (
            SELECT friend_id FROM friendships WHERE user_id = ? AND status = 'accepted'
        )
        ORDER BY cd.created_at DESC
        LIMIT 20
        """,
        (user_id,)
    ).fetchall()

    # Public community recipes as supplemental feed
    public_rows = conn.execute(
        """
        SELECT cd.id, cd.user_id, cd.name, cd.type, cd.serve_with, cd.category, cd.style, cd.course,
               cd.image, cd.cuisine, cd.description, cd.prep_time, cd.cook_time, cd.servings,
               cd.ingredients, cd.instructions, cd.tips, cd.created_at, u.email AS creator_email,
               (SELECT COUNT(*) FROM friendships WHERE user_id = ? AND friend_id = cd.user_id AND status = 'accepted') AS is_followed_creator
        FROM custom_dishes cd
        JOIN users u ON cd.user_id = u.id
        WHERE cd.is_public = 1 AND cd.user_id != ?
        ORDER BY cd.created_at DESC
        LIMIT 15
        """,
        (user_id, user_id)
    ).fetchall()

    conn.close()

    feed_items = []
    seen_ids = set()

    for r in list(followed_rows) + list(public_rows):
        d = dict(r)
        if d["id"] not in seen_ids:
            seen_ids.add(d["id"])
            d["creator_chef_name"] = format_chef_name(d["creator_email"])
            d["creator_handle"] = f"@{d['creator_email'].split('@')[0]}"
            d["is_followed_creator"] = bool(d["is_followed_creator"])
            feed_items.append(d)

    # Sort feed items by creation date
    feed_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return feed_items


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


def add_shopping_item(user_id, item_name, category="produce", quantity=""):
    """
    Adds an item to the user's shopping list. If item already exists and not bought, update quantity.
    """
    import datetime
    conn = get_conn()
    item_clean = item_name.strip()
    if not item_clean:
        conn.close()
        return False
        
    now = datetime.datetime.now().isoformat()
    existing = conn.execute(
        "SELECT id, quantity FROM shopping_list WHERE user_id = ? AND LOWER(item_name) = LOWER(?) AND is_bought = 0",
        (user_id, item_clean)
    ).fetchone()
    
    if existing:
        new_qty = quantity.strip() if quantity else existing["quantity"]
        conn.execute(
            "UPDATE shopping_list SET quantity = ?, category = ? WHERE id = ?",
            (new_qty, category.strip().lower(), existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO shopping_list (user_id, item_name, category, quantity, is_bought, created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (user_id, item_clean, category.strip().lower(), quantity.strip(), now)
        )
    conn.commit()
    conn.close()
    return True


def get_shopping_list(user_id):
    """
    Returns all shopping items for a user, ordered by is_bought ASC, id DESC.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, item_name, category, quantity, is_bought, created_at FROM shopping_list WHERE user_id = ? ORDER BY is_bought ASC, id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_shopping_item(user_id, item_id):
    """
    Toggles is_bought status of a shopping list item.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT is_bought FROM shopping_list WHERE user_id = ? AND id = ?",
        (user_id, int(item_id))
    ).fetchone()
    if row:
        new_status = 0 if row["is_bought"] == 1 else 1
        conn.execute(
            "UPDATE shopping_list SET is_bought = ? WHERE user_id = ? AND id = ?",
            (new_status, user_id, int(item_id))
        )
        conn.commit()
    conn.close()
    return True


def delete_shopping_item(user_id, item_id):
    """
    Deletes a shopping list item.
    """
    conn = get_conn()
    conn.execute(
        "DELETE FROM shopping_list WHERE user_id = ? AND id = ?",
        (user_id, int(item_id))
    )
    conn.commit()
    conn.close()
    return True


def clear_bought_shopping_items(user_id):
    """
    Clears all bought items from user's shopping list.
    """
    conn = get_conn()
    conn.execute(
        "DELETE FROM shopping_list WHERE user_id = ? AND is_bought = 1",
        (user_id,)
    )
    conn.commit()
    conn.close()
    return True


def move_shopping_to_fridge(user_id, item_id, location="fridge"):
    """
    Moves a shopping item directly into fridge_inventory and removes it from the shopping list.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT item_name, quantity FROM shopping_list WHERE user_id = ? AND id = ?",
        (user_id, int(item_id))
    ).fetchone()
    
    if row:
        item_name = row["item_name"]
        quantity = row["quantity"] or "1 pack"
        conn.execute("DELETE FROM shopping_list WHERE user_id = ? AND id = ?", (user_id, int(item_id)))
        conn.commit()
        conn.close()
        add_fridge_item(user_id, item_name, location, quantity)
        return True, item_name
    conn.close()
    return False, ""


def get_smart_grocery_recommendations(user_id):
    """
    Analyzes upcoming weekly plan meals and current fridge inventory to suggest what to buy.
    """
    conn = get_conn()
    inventory = conn.execute("SELECT LOWER(item_name) as name FROM fridge_inventory WHERE user_id = ?", (user_id,)).fetchall()
    fridge_names = {r["name"] for r in inventory}
    
    shopping = conn.execute("SELECT LOWER(item_name) as name FROM shopping_list WHERE user_id = ? AND is_bought = 0", (user_id,)).fetchall()
    shopping_names = {r["name"] for r in shopping}
    
    weekly = conn.execute("SELECT day_index, dish, day_name FROM weekly_plans WHERE user_id = ? ORDER BY day_index ASC", (user_id,)).fetchall()
    
    recommendations = []
    seen_recs = set()
    
    for plan in weekly:
        dish_name = plan["dish"]
        day_name = plan["day_name"] if "day_name" in plan.keys() else f"Day {plan['day_index']+1}"
        
        # Get ingredients for this dish
        ing_row = conn.execute("SELECT ingredients FROM dish_ingredients WHERE LOWER(dish_name) = LOWER(?)", (dish_name,)).fetchone()
        if ing_row and ing_row["ingredients"]:
            raw_ings = [i.strip() for i in ing_row["ingredients"].split(",") if i.strip()]
            for ing in raw_ings:
                ing_lower = ing.lower()
                # Skip if already in fridge, on shopping list, or in seen recommendations
                if not any(f in ing_lower or ing_lower in f for f in fridge_names) and ing_lower not in shopping_names and ing_lower not in seen_recs:
                    seen_recs.add(ing_lower)
                    
                    cat = "produce"
                    if any(m in ing_lower for m in ["chicken", "beef", "mutton", "meat", "fish", "prawn", "keema", "gosht"]):
                        cat = "meat"
                    elif any(d in ing_lower for d in ["milk", "yogurt", "cheese", "cream", "butter", "dahi", "paneer"]):
                        cat = "dairy"
                    elif any(p in ing_lower for p in ["rice", "daal", "lentil", "flour", "atta", "oil", "ghee", "pasta", "noodles"]):
                        cat = "pantry"
                    elif any(s in ing_lower for s in ["chili", "masala", "garam", "turmeric", "cumin", "coriander", "salt", "pepper", "sauce"]):
                        cat = "spices"
                        
                    recommendations.append({
                        "item_name": ing.title(),
                        "category": cat,
                        "reason": f"Needed for {day_name}'s {dish_name}"
                    })
                    if len(recommendations) >= 8:
                        break
        if len(recommendations) >= 8:
            break
            
    # If recommendations are few, add common kitchen essentials not currently in fridge/shopping list
    if len(recommendations) < 5:
        staples = [
            ("Fresh Tomatoes", "produce", "Essential Kitchen Staple"),
            ("Onions", "produce", "Base for Gravies & Curries"),
            ("Ginger Garlic Paste", "produce", "Aromatic Core Staple"),
            ("Green Chilies & Fresh Coriander", "produce", "Fresh Garnish Staple"),
            ("Plain Yogurt (Dahi)", "dairy", "Cooking & Raita Staple"),
            ("Cooking Oil / Desi Ghee", "pantry", "Essential Cooking Medium"),
            ("Basmati Rice", "pantry", "Daily Grains Staple"),
            ("Eggs", "dairy", "Quick Breakfast & Cooking Staple")
        ]
        for name, cat, reason in staples:
            name_lower = name.lower()
            if not any(f in name_lower or name_lower in f for f in fridge_names) and name_lower not in shopping_names and name_lower not in seen_recs:
                seen_recs.add(name_lower)
                recommendations.append({
                    "item_name": name,
                    "category": cat,
                    "reason": reason
                })
                if len(recommendations) >= 8:
                    break
                    
    conn.close()
    return recommendations


def get_curated_appliances():
    """
    Returns curated catalog of modern kitchen machineries, smart cookers, and appliances.
    """
    return [
        {
            "id": "nutricook_smart_pot",
            "name": "Nutricook Smart Pot 2 (Multi-Cooker 9-in-1)",
            "brand": "Nutricook",
            "category": "smart_cooking",
            "category_label": "Smart Cookers & Air Fryers ⚡",
            "icon": "skillet",
            "badge": "Top Essential ⭐",
            "image": "https://images.unsplash.com/photo-1544233726-9f1d2b27be8b?w=600&auto=format&fit=crop&q=80",
            "tagline": "Replaces 9 kitchen appliances in one. Cooks pressure curries & biryanis 70% faster.",
            "specs": ["6L / 8L Capacity", "1000W Smart Heating", "9-in-1: Pressure, Slow Cook, Rice, Sauté, Steamer, Yogurt", "Smart Lid with Auto Pressure Release"],
            "best_for": "Dum Biryani, Haleem, Beef Nihari, Mutton Kunna, Dal Tadka, Bone Broths",
            "compatible_dishes": ["Chicken Biryani", "Beef Nihari", "Haleem", "Daal Chawal", "Mutton Karahi", "Chicken Pulao", "Aloo Gosht", "Daal Makhani"],
            "buy_url": "https://www.google.com/search?q=nutricook+smart+pot+2+buy+online"
        },
        {
            "id": "nutricook_air_fryer",
            "name": "Nutricook Rapid Air Fryer 5.7L",
            "brand": "Nutricook",
            "category": "smart_cooking",
            "category_label": "Smart Cookers & Air Fryers ⚡",
            "icon": "airware",
            "badge": "Healthy & Fast 🥗",
            "image": "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=600&auto=format&fit=crop&q=80",
            "tagline": "Guilt-free frying with 85% less oil. Perfectly crispy texture in half the time.",
            "specs": ["5.7L XL Basket", "1700W Rapid Air Circulation", "10 One-Touch Cooking Presets", "Shake Reminder & Auto Shut-off"],
            "best_for": "Crispy Chicken Roast, Seekh Kababs, Samosas, Fish Fry, Chicken Nuggets, Roasted Vegetables",
            "compatible_dishes": ["Chicken Tikka", "Seekh Kabab", "Grilled Chicken Steak", "Fish and Chips", "French Fries", "Chicken Manchurian", "Crispy Roast Chicken"],
            "buy_url": "https://www.google.com/search?q=nutricook+air+fryer+buy+online"
        },
        {
            "id": "automatic_roti_maker",
            "name": "Automatic Electric Roti Maker & Press",
            "brand": "Chef Master",
            "category": "roti_dough",
            "category_label": "Roti & Dough Makers 🫓",
            "icon": "cookie",
            "badge": "Daily Essential 🫓",
            "image": "https://images.unsplash.com/photo-1626074353765-517a681e40be?w=600&auto=format&fit=crop&q=80",
            "tagline": "Presses and cooks round, soft, puffed phulkas and rotis in under 60 seconds with zero rolling.",
            "specs": ["Non-Stick Double Heating Plates", "Thermostatically Controlled 900W", "Heavy-Duty Handle Press", "Lightweight & Portable Design"],
            "best_for": "Soft Phulkas, Daily Chapatis, Parathas, Tortillas, Poori Pressing",
            "compatible_dishes": ["Roti", "Paratha", "Chapati", "Poori", "Aloo Paratha"],
            "buy_url": "https://www.google.com/search?q=automatic+electric+roti+maker+machine"
        },
        {
            "id": "atta_kneader_stand_mixer",
            "name": "Electric Stand Mixer & Automatic Atta Dough Kneader",
            "brand": "KitchenPro",
            "category": "roti_dough",
            "category_label": "Roti & Dough Makers 🫓",
            "icon": "blender",
            "badge": "Game Changer ⚡",
            "image": "https://images.unsplash.com/photo-1594221708779-94832f4320d1?w=600&auto=format&fit=crop&q=80",
            "tagline": "Effortlessly kneads 1-2 kg of smooth, soft whole wheat atta dough in just 3 minutes.",
            "specs": ["5L Stainless Steel Bowl", "1200W High-Torque Pure Copper Motor", "Planetary Mixing Action", "Dough Hook, Whisk & Beater Attachments"],
            "best_for": "Soft Atta Dough for Rotis, Naan Dough, Pizza Crust, Cake Batters, Bread Loaves",
            "compatible_dishes": ["Roti", "Naan", "Paratha", "Pizza", "Cake", "Puri"],
            "buy_url": "https://www.google.com/search?q=electric+atta+kneader+stand+mixer+buy+online"
        },
        {
            "id": "electric_chopper_processor",
            "name": "Electric Quad-Blade Chopper & Multi Food Processor",
            "brand": "MultiCut",
            "category": "choppers",
            "category_label": "Choppers & Processors 🔪",
            "icon": "restaurant",
            "badge": "Prep Lifesaver ⏱️",
            "image": "https://images.unsplash.com/photo-1570222094114-d054a817e56b?w=600&auto=format&fit=crop&q=80",
            "tagline": "Chops onions tear-free, minces keema, shreds vegetables, and purees tomatoes in 5 seconds.",
            "specs": ["2L Glass / Steel Bowl", "4 Bi-Level Stainless Steel Blades", "500W Powerful Pulse Motor", "BPA-Free Food-Grade Materials"],
            "best_for": "Keema Mincing, Onion Dicing, Ginger-Garlic Paste, Tomato Puree, Salad Shredding",
            "compatible_dishes": ["Keema Matar", "Seekh Kabab", "Chicken Manchurian", "Beef Burger", "Chicken Chow Mein", "Shami Kabab"],
            "buy_url": "https://www.google.com/search?q=electric+food+chopper+meat+grinder"
        },
        {
            "id": "immersion_hand_blender",
            "name": "Immersion Hand Blender & Emulsifier Set (3-in-1)",
            "brand": "BlendPro",
            "category": "blenders_grinders",
            "category_label": "Blenders & Grinders 🌪️",
            "icon": "blender",
            "badge": "Chef Favorite 👨‍🍳",
            "image": "https://images.unsplash.com/photo-1574269909862-7e1d70bb8078?w=600&auto=format&fit=crop&q=80",
            "tagline": "Blend directly inside hot cooking pots without messy transfers. Creates velvety smooth gravies.",
            "specs": ["Stainless Steel Immersion Wand", "800W Turbo Speed Motor", "Whisk & Mini Chopper Attachments", "Anti-Splash Design"],
            "best_for": "Handi Gravies, Creamy Alfredo Sauce, Dal Pureeing, Mint Raita Chutney, Fresh Lassi & Smoothies",
            "compatible_dishes": ["Chicken Handi", "Alfredo Pasta", "Daal Makhani", "Palak Paneer", "Hot & Sour Soup", "Mango Lassi"],
            "buy_url": "https://www.google.com/search?q=hand+blender+immersion+set+buy+online"
        },
        {
            "id": "electric_tandoor_bbq",
            "name": "Electric Smokeless Tandoor & Indoor BBQ Grill",
            "brand": "GrillMaster",
            "category": "grills_tandoor",
            "category_label": "Smokeless Grills & Tandoors 🍢",
            "icon": "outdoor_grill",
            "badge": "BBQ Specialist 🍢",
            "image": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&auto=format&fit=crop&q=80",
            "tagline": "Authentic charred tandoori flavor and char-marks right in your kitchen without smoke or charcoal.",
            "specs": ["2000W Infrared Radiant Heating", "Smokeless Drip Tray Technology", "Non-Stick Ribbed Grill & Flat Griddle", "Adjustable Thermostat up to 250°C"],
            "best_for": "Chicken Tikka, Malai Boti, Seekh Kababs, Grilled Fish, Tandoori Roti & Naan",
            "compatible_dishes": ["Chicken Tikka", "Seekh Kabab", "Grilled Chicken Steak", "Fish Tikka", "Tandoori Roti"],
            "buy_url": "https://www.google.com/search?q=electric+smokeless+indoor+grill+tandoor"
        },
        {
            "id": "spice_coffee_grinder",
            "name": "Electric Stainless Steel Dry Spice & Masala Grinder",
            "brand": "SpiceKing",
            "category": "blenders_grinders",
            "category_label": "Blenders & Grinders 🌪️",
            "icon": "grain",
            "badge": "Aroma Booster 🌶️",
            "image": "https://images.unsplash.com/photo-1588854337236-6889d631faa8?w=600&auto=format&fit=crop&q=80",
            "tagline": "Grind whole cumin, cardamom, and cinnamon into fresh, fragrant spice powders in 10 seconds.",
            "specs": ["Heavy Duty Stainless Steel Cup", "High-Speed 28000 RPM Motor", "One-Touch Push-Down Pulse Operation", "Safety Lock Lid"],
            "best_for": "Fresh Garam Masala, Roasted Cumin Powder, Biryani Spices, Coriander Powder, Coffee Beans",
            "compatible_dishes": ["Chicken Biryani", "Mutton Karahi", "Beef Nihari", "Chicken Korma", "Chana Chaat"],
            "buy_url": "https://www.google.com/search?q=electric+dry+masala+spice+grinder"
        },
        {
            "id": "digital_kitchen_scale",
            "name": "Digital Kitchen Food Scale & Precision Timer (0.1g)",
            "brand": "AccuScale",
            "category": "prep_precision",
            "category_label": "Precision & Prep ⚖️",
            "icon": "scale",
            "badge": "Diet & Baking 🥗",
            "image": "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80",
            "tagline": "Exact gram precision for macro tracking, healthy diet portioning, and flawless baking consistency.",
            "specs": ["High-Precision Sensor (0.1g - 5000g)", "Tare Function (Zeroes Container Weight)", "Backlit LCD Display in g/oz/ml", "Tempered Glass Waterproof Surface"],
            "best_for": "Diet Macro Tracking, Protein Portioning, Cake & Bread Baking, Exact Spice Formulations",
            "compatible_dishes": ["Grilled Chicken Salad", "Oatmeal Bowl", "Steamed Fish", "Caesar Salad", "Pancake Batter"],
            "buy_url": "https://www.google.com/search?q=digital+kitchen+food+scale+buy+online"
        },
        {
            "id": "electric_kettle",
            "name": "Rapid Boil Stainless Steel Electric Kettle (1.8L)",
            "brand": "QuickBoil",
            "category": "prep_precision",
            "category_label": "Precision & Prep ⚖️",
            "icon": "coffee",
            "badge": "Speed Essential ⚡",
            "image": "https://images.unsplash.com/photo-1594834749740-74b3f6764be4?w=600&auto=format&fit=crop&q=80",
            "tagline": "Boils water in 90 seconds. Speeds up curries, gravies, pasta boiling, and chai prep.",
            "specs": ["1.8L Large Capacity", "1500W Rapid Boil Element", "Auto Shut-Off & Boil-Dry Protection", "Food Grade 304 Stainless Steel"],
            "best_for": "Instant Hot Water for Stocks, Curries, Rice Soaking, Instant Noodles, Green Tea & Chai",
            "compatible_dishes": ["Chicken Chow Mein", "Hot & Sour Soup", "Alfredo Pasta", "Daal Chawal"],
            "buy_url": "https://www.google.com/search?q=electric+kettle+stainless+steel+buy+online"
        },
        {
            "id": "sandwich_panini_press",
            "name": "Electric Non-Stick Panini Press & Sandwich Grill",
            "brand": "ToastPro",
            "category": "grills_tandoor",
            "category_label": "Smokeless Grills & Tandoors 🍢",
            "icon": "lunch_dining",
            "badge": "Quick Breakfast 🥪",
            "image": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&auto=format&fit=crop&q=80",
            "tagline": "Toasts crispy golden sandwiches, club sandwiches, wraps, and quesadillas with melt-in-the-middle cheese.",
            "specs": ["Floating Hinge for Thick Sandwiches", "Non-Stick Easy Clean Plates", "1000W Rapid Dual Heating", "Upright Storage Design"],
            "best_for": "Club Sandwiches, Chicken Cheese Paninis, Breakfast Toasties, Paratha Rolls, Shawarmas",
            "compatible_dishes": ["Club Sandwich", "Chicken Cheese Wrap", "Grilled Cheese", "Quesadilla"],
            "buy_url": "https://www.google.com/search?q=electric+panini+press+sandwich+maker"
        },
        {
            "id": "slow_cooker_pot",
            "name": "Ceramic Slow Cooker & Tender Stew Pot (4.5L)",
            "brand": "SlowChef",
            "category": "smart_cooking",
            "category_label": "Smart Cookers & Air Fryers ⚡",
            "icon": "soup_kitchen",
            "badge": "Melt-in-Mouth 🍲",
            "image": "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&auto=format&fit=crop&q=80",
            "tagline": "Simmers meat on gentle low heat for hours, extracting rich gelatinous bone broths and tender curries.",
            "specs": ["4.5L Removable Ceramic Pot", "Low, High & Auto Keep-Warm Settings", "Tempered Glass Lid", "Low Energy Consumption (220W)"],
            "best_for": "Mutton Paya, Beef Kunna, Slow-Cooked Haleem, Chicken Stew, Bone Broth",
            "compatible_dishes": ["Haleem", "Beef Nihari", "Mutton Kunna", "Aloo Gosht", "Chicken Stew"],
            "buy_url": "https://www.google.com/search?q=ceramic+slow+cooker+buy+online"
        }
    ]


def get_user_appliances(user_id):
    """
    Returns a dictionary of user's appliance statuses: {appliance_id: {"status": 'owned' | 'wishlist', "created_at": ...}}
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT appliance_id, status, custom_name, created_at FROM user_appliances WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()
    return {row["appliance_id"]: dict(row) for row in rows}


def toggle_user_appliance(user_id, appliance_id, status=None, custom_name=None):
    """
    Toggles or sets the status of an appliance for a user.
    If status is None or 'remove', deletes the row.
    Otherwise sets status to 'owned' or 'wishlist'.
    """
    conn = get_conn()
    now_str = datetime.now().isoformat()
    if not status or status == "remove":
        conn.execute(
            "DELETE FROM user_appliances WHERE user_id = ? AND appliance_id = ?",
            (user_id, appliance_id)
        )
    else:
        conn.execute("""
            INSERT INTO user_appliances (user_id, appliance_id, status, custom_name, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, appliance_id) DO UPDATE SET status = excluded.status, custom_name = excluded.custom_name
        """, (user_id, appliance_id, status, custom_name, now_str))
    conn.commit()
    conn.close()


def get_appliance_compatible_dishes(user_id):
    """
    Returns a list of compatible dishes that can be prepared with the user's owned appliances.
    """
    user_apps = get_user_appliances(user_id)
    owned_ids = {app_id for app_id, data in user_apps.items() if data.get("status") == "owned"}
    
    curated = get_curated_appliances()
    matched_dish_names = set()
    appliance_dish_map = {}
    
    for app in curated:
        if app["id"] in owned_ids:
            for d in app["compatible_dishes"]:
                matched_dish_names.add(d)
                if d not in appliance_dish_map:
                    appliance_dish_map[d] = []
                appliance_dish_map[d].append(app["name"])
                
    return [
        {"name": dish_name, "appliances": appliance_dish_map[dish_name]}
        for dish_name in sorted(matched_dish_names)
    ]


