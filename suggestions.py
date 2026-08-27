import csv
import random
from datetime import date
from pathlib import Path

from db import block_dish, blocked_dishes, recent_dishes, update_user, get_custom_dishes, get_dish_ingredients_from_db

DISHES_PATH = Path(__file__).parent / "data" / "dishes.csv"

SERVE_WITH_PHRASE = {"rice": "rice", "roti": "roti", "both": "rice or roti"}


def _load_dishes():
    with open(DISHES_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


DISHES = _load_dishes()


def get_personalized_inventory(user_id):
    """
    Returns the combined list of global dishes and user custom dishes.
    """
    custom = get_custom_dishes(user_id)
    return [dict(d) for d in DISHES] + custom


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


def suggest_dish(user, as_dict=False):
    category = today_category(user)
    inventory = get_personalized_inventory(user["id"])
    pool = [d for d in inventory if d["type"] == category and d["course"] == "main"]

    blocked = {b.lower() for b in blocked_dishes(user["id"])}
    pool = [d for d in pool if d["name"].lower() not in blocked]

    if not pool:
        if as_dict:
            return {
                "name": f"Out of {category} dishes",
                "category": category,
                "serve_phrase": ""
            }
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

    # Deterministically shuffle pool by date so random daily order is preserved
    day_rng = random.Random(f"{user['id']}-{date.today().isoformat()}")
    shuffled_pool = list(pool)
    day_rng.shuffle(shuffled_pool)

    # Use seed offset to cycle sequentially through the shuffled list (guarantees no repeats!)
    offset = user.get("suggestion_seed_offset") or 0
    index = offset % len(shuffled_pool)
    dish = shuffled_pool[index]
    
    update_user(user["id"], last_suggested=dish["name"])
    serve_with = SERVE_WITH_PHRASE.get(dish["serve_with"])
    serve_phrase = f", served with {serve_with}" if serve_with else ""
    
    if as_dict:
        return {
            "name": dish["name"],
            "category": category,
            "serve_phrase": serve_phrase
        }
    return f"How about {dish['name']} today{serve_phrase}? ({category})"


def block_last_suggestion(user):
    dish = user.get("last_suggested")
    if not dish:
        return "Sure — just tell me after I suggest something if you don't want to see it again."

    block_dish(user["id"], dish)
    update_user(user["id"], last_suggested=None)
    return f"Got it, I won't suggest {dish} again."


def suggest_by_quiz(user_id, protein, serve_with, style, courses=None, meal_slot="any", include_sides=False, limit=5):
    # Establish strict base pool matching only strict constraints: Protein and Course Type
    inventory = get_personalized_inventory(user_id)
    pool = inventory
    
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
    else:
        # Default: if a meat eater ran out of specific protein choices, keep all non-veg
        pool = [d for d in pool if d["type"] == "nonveg"]

    courses = list(courses or [])
    if not courses:
        courses = ["main"]
    
    if "any" not in courses:
        pool = [d for d in pool if d["course"] in courses]

    # Exclude blocked dishes strictly
    blocked = {b.lower() for b in blocked_dishes(user_id)}
    pool = [d for d in pool if d["name"].lower() not in blocked]

    # Apply soft filters progressively (relaxing them if they make the pool too small)
    candidate_pool = list(pool)
    
    # Soft Filter 1: Serve with (Rice vs Roti)
    serve_with = (serve_with or "").lower().strip()
    if serve_with == "rice":
        filtered = [d for d in candidate_pool if d["serve_with"] in ("rice", "both")]
        if len(filtered) >= limit:
            candidate_pool = filtered
    elif serve_with == "roti":
        filtered = [d for d in candidate_pool if d["serve_with"] in ("roti", "both")]
        if len(filtered) >= limit:
            candidate_pool = filtered

    # Soft Filter 2: Style (Rich vs Light)
    style = (style or "").lower().strip()
    if style in ("rich", "light"):
        filtered = [d for d in candidate_pool if d["style"] == style]
        if len(filtered) >= limit:
            candidate_pool = filtered

    # Soft Filter 3: Meal Slot (Breakfast vs Lunch/Dinner)
    meal_slot = (meal_slot or "").lower().strip()
    if meal_slot == "breakfast":
        filtered = [d for d in candidate_pool if d["category"] in ("breakfast", "quick")]
        if len(filtered) >= limit:
            candidate_pool = filtered
    elif meal_slot == "lunch_dinner":
        filtered = [d for d in candidate_pool if d["category"] != "breakfast"]
        if len(filtered) >= limit:
            candidate_pool = filtered

    # Soft Filter 4: Recent Dishes (not eaten in last 7 days)
    recent_names = {m["dish"].strip().lower() for m in recent_dishes(user_id, limit=7)}
    fresh_pool = [d for d in candidate_pool if d["name"].lower() not in recent_names]
    final_pool = fresh_pool if len(fresh_pool) >= limit else candidate_pool

    # If the pool is still empty, fall back to the strict base pool (ignoring soft preferences)
    if not final_pool:
        final_pool = pool

    # Shuffle and pick limit
    random.shuffle(final_pool)
    selected_dishes = final_pool[:limit]

    # Make copy of dictionaries to avoid mutating global configuration
    results = [dict(d) for d in selected_dishes]

    # 6. Smart Side Pairing
    if include_sides:
        # Load side dishes pool (also strictly respecting veg/nonveg!)
        side_pool = [d for d in inventory if d["course"] == "side" and d["name"].lower() not in blocked]
        if protein == "veg":
            side_pool = [s for s in side_pool if s["type"] == "veg"]
        else:
            side_pool = [s for s in side_pool if s["type"] == "nonveg"]
            
        recent_sides = {m["dish"].strip().lower() for m in recent_dishes(user_id, limit=7)}
        fresh_sides = [d for d in side_pool if d["name"].lower() not in recent_sides]
        final_sides = fresh_sides if fresh_sides else side_pool

        for dish in results:
            if dish["course"] == "main" and final_sides:
                side_item = random.choice(final_sides)
                dish["side_pairing"] = side_item["name"]

    return results


def generate_weekly_plan(user_id, start_type, pattern):
    import db
    blocked = {b.lower() for b in blocked_dishes(user_id)}
    inventory = get_personalized_inventory(user_id)
    
    # Filter pools of main dishes
    veg_pool = [d for d in inventory if d["type"] == "veg" and d["course"] == "main" and d["name"].lower() not in blocked]
    nonveg_pool = [d for d in inventory if d["type"] == "nonveg" and d["course"] == "main" and d["name"].lower() not in blocked]
    
    # Shuffle pools
    random.shuffle(veg_pool)
    random.shuffle(nonveg_pool)

    # Determine 7-day pattern
    # DAYS mapping
    DAYS = [
        {"name": "Monday", "index": 0},
        {"name": "Tuesday", "index": 1},
        {"name": "Wednesday", "index": 2},
        {"name": "Thursday", "index": 3},
        {"name": "Friday", "index": 4},
        {"name": "Saturday", "index": 5},
        {"name": "Sunday", "index": 6}
    ]

    meal_sequence = []
    
    if pattern == "all_veg":
        meal_sequence = ["veg"] * 7
    elif pattern == "all_gosht":
        meal_sequence = ["nonveg"] * 7
    elif pattern == "alternate":
        current = start_type.lower()
        for i in range(7):
            meal_sequence.append(current)
            current = "nonveg" if current == "veg" else "veg"
    elif pattern == "2nv_1v":
        seq = ["nonveg", "nonveg", "veg"]
        for i in range(7):
            meal_sequence.append(seq[i % 3])
    elif pattern == "1nv_2v":
        seq = ["nonveg", "veg", "veg"]
        for i in range(7):
            meal_sequence.append(seq[i % 3])
    elif pattern == "both":
        meal_sequence = ["both"] * 7

    plan_days = []
    for day in DAYS:
        day_type = meal_sequence[day["index"]]
        
        if day_type == "both":
            if not veg_pool:
                veg_pool = [d for d in inventory if d["type"] == "veg" and d["course"] == "main" and d["name"].lower() not in blocked]
                random.shuffle(veg_pool)
            if not nonveg_pool:
                nonveg_pool = [d for d in inventory if d["type"] == "nonveg" and d["course"] == "main" and d["name"].lower() not in blocked]
                random.shuffle(nonveg_pool)
                
            veg_dish = veg_pool.pop(0)
            nv_dish = nonveg_pool.pop(0)
            
            dish_name = f"{veg_dish['name']} & {nv_dish['name']}"
            side_pairing = "Roti or Rice"
        else:
            pool_to_use = veg_pool if day_type == "veg" else nonveg_pool
            if not pool_to_use:
                refill = [d for d in inventory if d["type"] == day_type and d["course"] == "main" and d["name"].lower() not in blocked]
                random.shuffle(refill)
                if day_type == "veg":
                    veg_pool = refill
                    pool_to_use = veg_pool
                else:
                    nonveg_pool = refill
                    pool_to_use = nonveg_pool
            
            dish_item = pool_to_use.pop(0)
            dish_name = dish_item["name"]
            
            if dish_item["serve_with"] == "rice":
                side_pairing = "Rice"
            elif dish_item["serve_with"] == "roti":
                side_pairing = "Roti"
            else:
                side_pairing = "Roti or Rice"

        plan_days.append({
            "day_name": day["name"],
            "day_index": day["index"],
            "dish": dish_name,
            "side_pairing": side_pairing,
            "meal_type": day_type
        })
        
    db.save_weekly_plan(user_id, plan_days)
    return plan_days


def reroll_weekly_day(user_id, day_index, start_type, pattern):
    import db
    current_plan = db.get_weekly_plan(user_id)
    if not current_plan:
        return generate_weekly_plan(user_id, start_type, pattern)

    target_day = None
    for day in current_plan:
        if day["day_index"] == day_index:
            target_day = day
            break
            
    if not target_day:
        return current_plan

    day_type = target_day["meal_type"]
    blocked = {b.lower() for b in blocked_dishes(user_id)}
    inventory = get_personalized_inventory(user_id)
    
    active_dishes = set()
    for day in current_plan:
        if day["day_index"] != day_index:
            if " & " in day["dish"]:
                for name in day["dish"].split(" & "):
                    active_dishes.add(name.strip().lower())
            else:
                active_dishes.add(day["dish"].strip().lower())

    if day_type == "both":
        veg_candidates = [d for d in inventory if d["type"] == "veg" and d["course"] == "main" and d["name"].lower() not in blocked and d["name"].lower() not in active_dishes]
        nv_candidates = [d for d in inventory if d["type"] == "nonveg" and d["course"] == "main" and d["name"].lower() not in blocked and d["name"].lower() not in active_dishes]
        
        if not veg_candidates:
            veg_candidates = [d for d in inventory if d["type"] == "veg" and d["course"] == "main" and d["name"].lower() not in blocked]
        if not nv_candidates:
            nv_candidates = [d for d in inventory if d["type"] == "nonveg" and d["course"] == "main" and d["name"].lower() not in blocked]
            
        new_veg = random.choice(veg_candidates)
        new_nv = random.choice(nv_candidates)
        
        new_dish = f"{new_veg['name']} & {new_nv['name']}"
        new_side = "Roti or Rice"
    else:
        candidates = [d for d in inventory if d["type"] == day_type and d["course"] == "main" and d["name"].lower() not in blocked and d["name"].lower() not in active_dishes]
        if not candidates:
            candidates = [d for d in inventory if d["type"] == day_type and d["course"] == "main" and d["name"].lower() not in blocked]
            
        selected = random.choice(candidates)
        new_dish = selected["name"]
        
        if selected["serve_with"] == "rice":
            new_side = "Rice"
        elif selected["serve_with"] == "roti":
            new_side = "Roti"
        else:
            new_side = "Roti or Rice"

    db.update_weekly_day(user_id, day_index, new_dish, new_side)
    return db.get_weekly_plan(user_id)


def get_dish_fallback_ingredients(dish_name):
    """
    Returns a list of default clean ingredient keywords based on the dish name,
    used if the scraper hasn't run or is unavailable.
    """
    name = dish_name.lower()
    ingredients = []
    
    # Protein/Veg core matching
    if "chicken" in name:
        ingredients.append("chicken")
    if "beef" in name:
        ingredients.append("beef")
    if "mutton" in name or "lamb" in name:
        ingredients.append("mutton")
    if "paneer" in name:
        ingredients.append("paneer")
    if "daal" in name or "lentil" in name:
        ingredients.append("lentils")
    if "pulao" in name or "biryani" in name or "rice" in name:
        ingredients.append("rice")
    if "aloo" in name or "potato" in name:
        ingredients.append("potato")
    if "bhindi" in name or "okra" in name:
        ingredients.append("okra")
    if "matar" in name or "peas" in name:
        ingredients.append("peas")
    if "karela" in name or "bitter gourd" in name:
        ingredients.append("karela")
    if "spinach" in name or "palak" in name or "saag" in name:
        ingredients.append("spinach")
    if "egg" in name or "omelette" in name or "anda" in name:
        ingredients.append("egg")
    if "fish" in name or "shrimp" in name or "jheenga" in name or "prawn" in name:
        ingredients.append("fish")
    if "tinday" in name or "tinda" in name:
        ingredients.append("tinda")
    if "shalgam" in name or "turnip" in name:
        ingredients.append("turnip")
    if "gobi" in name or "gobhi" in name or "cauliflower" in name:
        ingredients.append("cauliflower")
    if "baingan" in name or "eggplant" in name or "brinjal" in name:
        ingredients.append("eggplant")
    if "kofta" in name or "keema" in name or "kebab" in name or "kabab" in name:
        ingredients.append("minced meat")
    if "chana" in name or "chole" in name or "chickpea" in name:
        ingredients.append("chana")
        
    return ingredients


def match_dishes_by_ingredients(user_id, available_items):
    """
    Matches the user's available ingredients against their personalized inventory
    using both real scraped ingredients from DB and name-based fallback.
    Returns list of matches: [{'dish': dish, 'matching_ingredients': [...], 'matched_from': 'scraped'|'fallback'}]
    """
    if not available_items:
        return []
        
    inventory = get_personalized_inventory(user_id)
    # Lazy load blocked_dishes to avoid circular import issues
    from db import blocked_dishes
    blocked = {b.lower() for b in blocked_dishes(user_id)}
    
    matches = []
    
    for dish in inventory:
        if dish["name"].lower() in blocked:
            continue
            
        dish_name = dish["name"]
        
        # 1. Try to load real scraped ingredients from DB
        db_ingredients_str = get_dish_ingredients_from_db(dish_name)
        
        matched_ingredients = []
        matched_from = "fallback"
        
        if db_ingredients_str:
            matched_from = "scraped"
            # Split and clean scraped ingredients
            scraped_list = [ing.strip().lower() for ing in db_ingredients_str.split(",") if ing.strip()]
            for item in available_items:
                item_cleaned = item.strip().lower()
                # Check if item name is a substring or word inside any scraped ingredient
                for scraped_ing in scraped_list:
                    if item_cleaned in scraped_ing or scraped_ing in item_cleaned:
                        if item_cleaned not in matched_ingredients:
                            matched_ingredients.append(item_cleaned)
        else:
            # 2. Fall back to name-based keyword extraction
            fallback_list = get_dish_fallback_ingredients(dish_name)
            for item in available_items:
                item_cleaned = item.strip().lower()
                for fallback_ing in fallback_list:
                    if item_cleaned in fallback_ing or fallback_ing in item_cleaned:
                        if item_cleaned not in matched_ingredients:
                            matched_ingredients.append(item_cleaned)
                            
        if matched_ingredients:
            matches.append({
                "dish": dish,
                "matching_ingredients": matched_ingredients,
                "matched_from": matched_from
            })
            
    # Sort matches by number of matching ingredients descending, then by dish name
    matches.sort(key=lambda m: (-len(m["matching_ingredients"]), m["dish"]["name"]))
    return matches

