from flask import Flask, flash, redirect, render_template, request, session, url_for

import suggestions
from auth import current_user, hash_password, is_valid_email, login_required, verify_password
from config import SECRET_KEY, VERIFY_TOKEN
from db import (
    create_user,
    get_user_by_email,
    get_user_by_wa_id,
    init_db,
    log_meal,
    recent_dishes,
    update_user,
)
import whatsapp_client

app = Flask(__name__)
app.secret_key = SECRET_KEY
init_db()


@app.context_processor
def inject_user():
    return dict(user=current_user())


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", error=None, email="")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")
    security_question = request.form.get("security_question", "").strip()
    security_answer = request.form.get("security_answer", "").strip().lower()

    if not is_valid_email(email):
        error = "Enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif password != confirm:
        error = "Passwords don't match."
    elif not security_question or not security_answer:
        error = "Security question and answer are required for password recovery."
    elif get_user_by_email(email):
        error = "An account with this email already exists."
    else:
        error = None

    if error:
        return render_template("signup.html", error=error, email=email)

    user = create_user(email, hash_password(password), security_question, security_answer)
    session["user_id"] = user["id"]
    return redirect(url_for("quiz_form"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None, email="")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = get_user_by_email(email)

    if not user or not verify_password(password, user["password_hash"]):
        return render_template("login.html", error="Incorrect email or password.", email=email)

    session["user_id"] = user["id"]
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html", step="email", email="", error=None)

    step = request.form.get("step")
    email = request.form.get("email", "").strip().lower()

    if step == "verify_email":
        if not email:
            return render_template("forgot_password.html", step="email", email="", error="Please enter your email.")
        
        user = get_user_by_email(email)
        if not user:
            return render_template("forgot_password.html", step="email", email=email, error="No account found with this email.")
        
        # Determine if they have a security question configured
        has_security_question = bool(user.get("security_question"))
        return render_template(
            "forgot_password.html",
            step="verify",
            email=email,
            has_security_question=has_security_question,
            security_question=user.get("security_question"),
            error=None
        )

    elif step == "reset":
        user = get_user_by_email(email)
        if not user:
            return render_template("forgot_password.html", step="email", email="", error="Session expired or invalid user. Please start again.")
        
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        # Verify identity first
        has_security_question = bool(user.get("security_question"))
        verified = False
        
        if has_security_question:
            answer = request.form.get("security_answer", "").strip().lower()
            correct_answer = (user.get("security_answer") or "").strip().lower()
            if answer and answer == correct_answer:
                verified = True
        else:
            submitted_wa = request.form.get("wa_id", "").strip().replace(" ", "").replace("+", "").replace("-", "")
            saved_wa = (user.get("wa_id") or "").strip().replace(" ", "").replace("+", "").replace("-", "")
            if submitted_wa and submitted_wa == saved_wa:
                verified = True

        if not verified:
            error_msg = "Incorrect security answer." if has_security_question else "Incorrect registered WhatsApp number."
            return render_template(
                "forgot_password.html",
                step="verify",
                email=email,
                has_security_question=has_security_question,
                security_question=user.get("security_question"),
                error=error_msg
            )
            
        if len(new_password) < 8:
            return render_template(
                "forgot_password.html",
                step="verify",
                email=email,
                has_security_question=has_security_question,
                security_question=user.get("security_question"),
                error="Password must be at least 8 characters long."
            )
            
        if new_password != confirm_password:
            return render_template(
                "forgot_password.html",
                step="verify",
                email=email,
                has_security_question=has_security_question,
                security_question=user.get("security_question"),
                error="Passwords do not match."
            )
            
        # Update user password in DB
        update_user(user["id"], password_hash=hash_password(new_password))
        flash("Password reset successfully! Please log in with your new password.")
        return redirect(url_for("login"))

    return redirect(url_for("login"))


@app.route("/quiz", methods=["GET"])
@login_required
def quiz_form():
    return render_template("quiz.html")


@app.route("/quiz", methods=["POST"])
@login_required
def quiz_submit():
    user = current_user()
    wa_id = request.form.get("wa_id", "").strip().replace(" ", "").replace("+", "").replace("-", "")
    update_user(
        user["id"],
        cooks_daily=1 if request.form.get("cooks_daily") == "yes" else 0,
        wants_suggestions=1 if request.form.get("wants_suggestions") == "yes" else 0,
        diet_type=request.form.get("diet_type"),
        diet_rule=request.form.get("diet_rule", "").strip() or None,
        household_size=int(request.form.get("household_size") or 0),
        health_conscious=1 if request.form.get("health_conscious") == "healthy" else 0,
        track_history=1 if request.form.get("track_history") == "yes" else 0,
        wa_id=wa_id or None,
        onboarded=1,
    )
    return redirect(url_for("dashboard"))


@app.route("/", methods=["GET"])
@login_required
def dashboard():
    user = current_user()
    if not user["onboarded"]:
        return redirect(url_for("quiz_form"))
    suggestion = suggestions.suggest_dish(user, as_dict=True)
    # Reload user to get updated last_suggested
    user = current_user()
    last_suggested = user.get("last_suggested")
    history = recent_dishes(user["id"], limit=7)
    
    # Calculate active pool size
    category = suggestions.today_category(user)
    inventory = suggestions.get_personalized_inventory(user["id"])
    pool = [d for d in inventory if d["type"] == category and d["course"] == "main"]
    from db import blocked_dishes
    blocked = {b.lower() for b in blocked_dishes(user["id"])}
    pool = [d for d in pool if d["name"].lower() not in blocked]
    if user.get("health_conscious"):
        pool = [d for d in pool if d["style"] == "light"] or pool
    pool_size = len(pool)
    
    import datetime
    today_str = datetime.date.today().isoformat()
    today_logged_meal = None
    for meal in history:
        if meal["meal_date"] == today_str:
            today_logged_meal = meal["dish"]
            break
            
    current_day_name = datetime.date.today().strftime("%A")
    
    return render_template(
        "dashboard.html",
        suggestion=suggestion,
        last_suggested=last_suggested,
        history=history,
        pool_size=pool_size,
        category=category,
        current_day_name=current_day_name,
        today_logged_meal=today_logged_meal,
        email=user["email"]
    )


@app.route("/weekly", methods=["GET"])
@login_required
def weekly_plan_view():
    user = current_user()
    if not user["onboarded"]:
        return redirect(url_for("quiz_form"))
    from db import get_weekly_plan
    weekly_plan = get_weekly_plan(user["id"])
    return render_template(
        "weekly.html",
        weekly_plan=weekly_plan,
        email=user["email"]
    )


@app.route("/weekly/generate", methods=["POST"])
@login_required
def generate_weekly():
    user = current_user()
    start_type = request.form.get("start_type", "nonveg")
    pattern = request.form.get("pattern", "alternate")
    
    suggestions.generate_weekly_plan(user["id"], start_type, pattern)
    return redirect(url_for("weekly_plan_view"))


@app.route("/weekly/reroll", methods=["POST"])
@login_required
def reroll_weekly():
    user = current_user()
    day_index = int(request.form.get("day_index"))
    
    suggestions.reroll_weekly_day(user["id"], day_index, None, None)
    return redirect(url_for("weekly_plan_view"))


@app.route("/reroll_today", methods=["POST"])
@login_required
def reroll_today():
    user = current_user()
    current_offset = user.get("suggestion_seed_offset") or 0
    from db import update_user
    update_user(user["id"], suggestion_seed_offset=current_offset + 1)
    return redirect(url_for("dashboard"))


@app.route("/custom_dish", methods=["GET"])
@login_required
def custom_dish_view():
    user = current_user()
    if not user["onboarded"]:
        return redirect(url_for("quiz_form"))
    from db import get_custom_dishes, get_blocked_dishes, get_friends, get_pending_friend_requests, get_friend_dish_suggestions
    custom_dishes = get_custom_dishes(user["id"])
    blocked_dishes_list = get_blocked_dishes(user["id"])
    inventory = suggestions.get_personalized_inventory(user["id"])
    existing_names = [d["name"] for d in inventory]
    
    # Load social network metrics
    friends = get_friends(user["id"])
    friend_requests = get_pending_friend_requests(user["id"])
    raw_suggestions = get_friend_dish_suggestions(user["id"])
    
    # Filter out suggestions that are already in core static CSV menu
    core_names = {d["name"].lower() for d in suggestions.DISHES}
    friend_suggestions = [d for d in raw_suggestions if d["name"].lower() not in core_names]
    
    return render_template(
        "custom_dish.html",
        custom_dishes=custom_dishes,
        blocked_dishes=blocked_dishes_list,
        existing_names=existing_names,
        friends=friends,
        friend_requests=friend_requests,
        friend_suggestions=friend_suggestions,
        email=user["email"]
    )


@app.route("/unblock", methods=["POST"])
@login_required
def unblock():
    user = current_user()
    dish = request.form.get("dish")
    if dish:
        from db import unblock_dish
        unblock_dish(user["id"], dish)
    return redirect(request.referrer or url_for("custom_dish_view"))


@app.route("/custom_dish/add", methods=["POST"])
@login_required
def add_custom():
    user = current_user()
    name = request.form.get("name")
    type_ = request.form.get("type")
    serve_with = request.form.get("serve_with", "both")
    category = request.form.get("category", "curry")
    style = request.form.get("style", "rich")
    course = request.form.get("course", "main")
    
    from db import add_custom_dish
    success = add_custom_dish(user["id"], name, type_, serve_with, category, style, course)
    
    from flask import flash
    if not success:
        flash(f"Failed to add '{name}'. It might already exist in your custom inventory!")
    else:
        flash(f"Successfully added '{name}' to your kitchen menu!")
        
    return redirect(url_for("custom_dish_view"))


@app.route("/quick_quiz", methods=["GET", "POST"])
@login_required
def quick_quiz():
    user = current_user()
    if request.method == "GET":
        return render_template("quick_quiz.html", suggestions=None, preferences=None)

    protein = request.form.get("protein")
    serve_with = request.form.get("serve_with")
    style = request.form.get("style")
    meal_slot = request.form.get("meal_slot", "any")
    courses = request.form.getlist("course")
    include_sides = True if request.form.get("include_sides") == "yes" else False

    preferences = {
        "protein": protein,
        "serve_with": serve_with,
        "style": style,
        "meal_slot": meal_slot,
        "courses": courses,
        "include_sides": include_sides
    }

    results = suggestions.suggest_by_quiz(
        user["id"],
        protein=protein,
        serve_with=serve_with,
        style=style,
        courses=courses,
        meal_slot=meal_slot,
        include_sides=include_sides,
        limit=5
    )
    return render_template("quick_quiz.html", suggestions=results, preferences=preferences)


@app.route("/reject", methods=["POST"])
@login_required
def reject():
    user = current_user()
    dish = request.form.get("dish")
    if dish:
        from db import block_dish
        block_dish(user["id"], dish)
    else:
        suggestions.block_last_suggestion(user)
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/log", methods=["POST"])
@login_required
def log():
    user = current_user()
    dish = request.form.get("dish", "").strip()
    category = request.form.get("category") or suggestions.today_category(user)
    if dish:
        log_meal(user["id"], dish, category=category)
    return redirect(url_for("dashboard"))


@app.route("/webhook", methods=["GET"])
def webhook_verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403
    return "Bad Request", 400


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    data = request.get_json()
    if not data:
        return "OK", 200

    print("Received WhatsApp webhook:", data)

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    sender = msg.get("from")  # SENDER_WA_ID
                    msg_type = msg.get("type")
                    text_content = ""

                    if msg_type == "button":
                        text_content = msg.get("button", {}).get("text", "").strip()
                    elif msg_type == "text":
                        text_content = msg.get("text", {}).get("body", "").strip()

                    if sender and text_content:
                        user = get_user_by_wa_id(sender)
                        if user:
                            meal_logged = text_content
                            clean_meal = meal_logged
                            for emoji in ["🥗", "🍗", "🚗", "✅", "🎲"]:
                                clean_meal = clean_meal.replace(emoji, "")
                            clean_meal = clean_meal.strip()

                            if "Log Veg" in clean_meal or "Veg Meal" in clean_meal:
                                category = "veg"
                                dish = user.get("last_suggested") or "Vegetarian Dish"
                            elif "Log Non-Veg" in clean_meal or "Non-Veg Meal" in clean_meal:
                                category = "nonveg"
                                dish = user.get("last_suggested") or "Non-Vegetarian Dish"
                            elif "Log Ordered" in clean_meal or "Ordered Out" in clean_meal:
                                category = "veg"
                                dish = "Ordered Out"
                            elif "Confirm" in clean_meal:
                                category = suggestions.today_category(user)
                                dish = user.get("last_suggested") or "Configured Menu"
                            elif "Generate" in clean_meal or "New Plan" in clean_meal or "Reroll" in clean_meal:
                                new_dish = suggestions.suggest_dish(user)
                                whatsapp_client.send_text_message(sender, f"🎲 Sure! Here is a new idea: {new_dish}. Reply to log it!")
                                return "OK", 200
                            else:
                                category = suggestions.today_category(user)
                                dish = clean_meal

                            log_meal(user["id"], dish, category=category)
                            whatsapp_client.send_text_message(sender, f"🍳 Got it! Logged \"{dish}\" in your kitchen history. Tomorrow I'll suggest something fresh!")
                        else:
                            whatsapp_client.send_text_message(sender, "Hi! I couldn't find your number registered in Chef Chat. Please visit our web setup to complete onboarding!")
    except Exception as e:
        print("Error parsing webhook:", e)

    return "OK", 200


@app.route("/fridge", methods=["GET"])
@login_required
def fridge_view():
    user = current_user()
    if not user["onboarded"]:
        return redirect(url_for("quiz_form"))
        
    from db import get_fridge_inventory
    inventory = get_fridge_inventory(user["id"])
    
    # Extract list of available item names for recipe matching
    available_items = [item["item_name"] for item in inventory]
    
    # Run the ingredient matcher
    from suggestions import match_dishes_by_ingredients
    matches = match_dishes_by_ingredients(user["id"], available_items)
    
    # Group inventory items by location
    fridge_items = [item for item in inventory if item["location"] == "fridge"]
    freezer_items = [item for item in inventory if item["location"] == "freezer"]
    pantry_items = [item for item in inventory if item["location"] == "pantry"]
    
    return render_template(
        "fridge.html",
        fridge_items=fridge_items,
        freezer_items=freezer_items,
        pantry_items=pantry_items,
        matches=matches,
        email=user["email"]
    )


@app.route("/fridge/add", methods=["POST"])
@login_required
def fridge_add():
    user = current_user()
    item_name = request.form.get("item_name")
    location = request.form.get("location")
    quantity = request.form.get("quantity")
    
    if item_name and location:
        from db import add_fridge_item
        add_fridge_item(user["id"], item_name, location, quantity)
        
    return redirect(url_for("fridge_view"))


@app.route("/fridge/update", methods=["POST"])
@login_required
def fridge_update():
    user = current_user()
    item_id = request.form.get("item_id")
    quantity = request.form.get("quantity")
    
    if item_id:
        from db import update_fridge_item
        update_fridge_item(user["id"], int(item_id), quantity)
        
    return redirect(url_for("fridge_view"))


@app.route("/fridge/delete", methods=["POST"])
@login_required
def fridge_delete():
    user = current_user()
    item_id = request.form.get("item_id")
    
    if item_id:
        from db import delete_fridge_item
        delete_fridge_item(user["id"], int(item_id))
        
    return redirect(url_for("fridge_view"))


@app.route("/tips", methods=["GET"])
@login_required
def tips_view():
    user = current_user()
    if not user["onboarded"]:
        return redirect(url_for("quiz_form"))
        
    return render_template("tips.html", email=user["email"])


@app.route("/friends/request", methods=["POST"])
@login_required
def send_friend_request_route():
    user = current_user()
    friend_email = request.form.get("friend_email")
    if friend_email:
        from db import add_friend_request
        success, msg = add_friend_request(user["id"], friend_email)
        flash(msg)
    else:
        flash("Please enter a valid email address.")
    return redirect(url_for("custom_dish_view"))


@app.route("/friends/accept", methods=["POST"])
@login_required
def accept_friend_request_route():
    user = current_user()
    requester_id = request.form.get("requester_id")
    if requester_id:
        from db import accept_friend_request
        accept_friend_request(user["id"], int(requester_id))
        flash("Friend request accepted! 🤝 You can now see each other's custom recipes!")
    return redirect(url_for("custom_dish_view"))


@app.route("/friends/reject", methods=["POST"])
@login_required
def reject_friend_request_route():
    user = current_user()
    requester_id = request.form.get("requester_id")
    if requester_id:
        from db import reject_friend_request
        reject_friend_request(user["id"], int(requester_id))
        flash("Friend request declined/cancelled.")
    return redirect(url_for("custom_dish_view"))


@app.route("/custom_dish/add_friend_suggestion", methods=["POST"])
@login_required
def add_friend_suggestion_route():
    user = current_user()
    name = request.form.get("name")
    type_ = request.form.get("type")
    serve_with = request.form.get("serve_with")
    category = request.form.get("category")
    style = request.form.get("style")
    course = request.form.get("course")
    
    if name and type_ and serve_with and category and style and course:
        from db import add_custom_dish
        success = add_custom_dish(user["id"], name, type_, serve_with, category, style, course)
        if success:
            flash(f"Added \"{name}\" to your private menu inventory! ➕")
        else:
            flash("Failed to add dish. It might already be in your menu.")
    return redirect(url_for("custom_dish_view"))


if __name__ == "__main__":
    app.run(port=5050)
