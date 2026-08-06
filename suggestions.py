import csv
import random
from datetime import date
from pathlib import Path

from db import block_dish, blocked_dishes, recent_dishes, update_user

DISHES_PATH = Path(__file__).parent / "data" / "dishes.csv"

SERVE_WITH_PHRASE = {"rice": "rice", "roti": "roti", "both": "rice or roti"}


def _load_dishes():
    with open(DISHES_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


DISHES = _load_dishes()


def today_category(user, today=None):
    diet_type = user.get("diet_type")
    if diet_type == "veg":
        return "veg"
    if diet_type == "nonveg":
        return "nonveg"

    today = today or date.today()
    day_name = today.strftime("%A").lower()
    rule = (user.get("diet_rule") or "").lower()
    is_weekend_rule = "weekend" in rule and day_name in ("saturday", "sunday")
    return "nonveg" if day_name in rule or is_weekend_rule else "veg"


def suggest_dish(user):
    category = today_category(user)
    pool = [d for d in DISHES if d["type"] == category]

    blocked = {b.lower() for b in blocked_dishes(user["id"])}
    pool = [d for d in pool if d["name"].lower() not in blocked]

    if not pool:
        return (
            f"I'm out of {category} dishes you haven't ruled out — tell me what "
            "you're in the mood for!"
        )

    if user.get("health_conscious"):
        light_pool = [d for d in pool if d["style"] == "light"]
        pool = light_pool or pool

    recent_names = {m["dish"].strip().lower() for m in recent_dishes(user["id"], limit=7)}
    fresh_pool = [d for d in pool if d["name"].lower() not in recent_names]
    pool = fresh_pool or pool

    rng = random.Random(f"{user['id']}-{date.today().isoformat()}")
    dish = rng.choice(pool)
    update_user(user["id"], last_suggested=dish["name"])
    serve_with = SERVE_WITH_PHRASE.get(dish["serve_with"])
    serve_phrase = f", served with {serve_with}" if serve_with else ""
    return f"How about {dish['name']} today{serve_phrase}? ({category})"


def block_last_suggestion(user):
    dish = user.get("last_suggested")
    if not dish:
        return "Sure — just tell me after I suggest something if you don't want to see it again."

    block_dish(user["id"], dish)
    update_user(user["id"], last_suggested=None)
    return f"Got it, I won't suggest {dish} again."


def suggest_by_quiz(user_id, protein, serve_with, style, courses=None, meal_slot="any", include_sides=False, limit=5):
    pool = DISHES
    
    # 1. Protein/Type filtering
    protein = (protein or "").lower().strip()
    if protein == "veg":
        pool = [d for d in pool if d["type"] == "veg"]
    elif protein == "chicken":
        pool = [d for d in pool if "chicken" in d["name"].lower()]
    elif protein == "beef":
        pool = [d for d in pool if "beef" in d["name"].lower()]
    elif protein == "mutton":
        pool = [d for d in pool if "mutton" in d["name"].lower() or "gosht" in d["name"].lower()]
    elif protein == "fish":
        pool = [d for d in pool if "fish" in d["name"].lower() or "shrimp" in d["name"].lower()]

    # 2. Side (Serve with) filtering
    serve_with = (serve_with or "").lower().strip()
    if serve_with == "rice":
        pool = [d for d in pool if d["serve_with"] in ("rice", "both")]
    elif serve_with == "roti":
        pool = [d for d in pool if d["serve_with"] in ("roti", "both")]

    # 3. Style filtering
    style = (style or "").lower().strip()
    if style in ("rich", "light"):
        pool = [d for d in pool if d["style"] == style]

    # 4. Meal Slot filtering
    meal_slot = (meal_slot or "").lower().strip()
    if meal_slot == "breakfast":
        pool = [d for d in pool if d["category"] in ("breakfast", "quick")]
    elif meal_slot == "lunch_dinner":
        pool = [d for d in pool if d["category"] != "breakfast"]

    # 5. Course (Multi-select) filtering
    courses = list(courses or [])
    if not courses:
        courses = ["main"]
    
    if "any" not in courses:
        pool = [d for d in pool if d["course"] in courses]

    # Exclude blocked dishes
    blocked = {b.lower() for b in blocked_dishes(user_id)}
    pool = [d for d in pool if d["name"].lower() not in blocked]

    # Exclude recent dishes
    recent_names = {m["dish"].strip().lower() for m in recent_dishes(user_id, limit=7)}
    fresh_pool = [d for d in pool if d["name"].lower() not in recent_names]
    
    # Fallback to general pool if fresh pool is too small
    final_pool = fresh_pool if len(fresh_pool) >= limit else pool
    
    # If still no results, fallback to all dishes matching the selected courses
    if not final_pool:
        fallback_pool = [d for d in DISHES if d["course"] in courses]
        final_pool = [d for d in fallback_pool if d["name"].lower() not in blocked]

    # Shuffle and pick limit
    random.shuffle(final_pool)
    selected_dishes = final_pool[:limit]

    # Make copy of dictionaries to avoid mutating global DISHES config
    results = [dict(d) for d in selected_dishes]

    # 6. Smart Side Pairing
    if include_sides:
        # Load side dishes pool
        side_pool = [d for d in DISHES if d["course"] == "side" and d["name"].lower() not in blocked]
        recent_sides = {m["dish"].strip().lower() for m in recent_dishes(user_id, limit=7)}
        fresh_sides = [d for d in side_pool if d["name"].lower() not in recent_sides]
        final_sides = fresh_sides if fresh_sides else side_pool

        for dish in results:
            if dish["course"] == "main" and final_sides:
                # Find matching side based on veg/nonveg compatibility
                compatible = []
                if dish["type"] == "veg":
                    # Veg main course requires a veg side
                    compatible = [s for s in final_sides if s["type"] == "veg"]
                else:
                    # Nonveg main course can have any side
                    compatible = final_sides
                
                if compatible:
                    side_item = random.choice(compatible)
                    dish["side_pairing"] = side_item["name"]

    return results


