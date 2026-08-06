from flask import Flask, redirect, render_template, request, session, url_for

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


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", error=None, email="")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")

    if not is_valid_email(email):
        error = "Enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif password != confirm:
        error = "Passwords don't match."
    elif get_user_by_email(email):
        error = "An account with this email already exists."
    else:
        error = None

    if error:
        return render_template("signup.html", error=error, email=email)

    user = create_user(email, hash_password(password))
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
    suggestion = suggestions.suggest_dish(user)
    # Reload user to get updated last_suggested
    user = current_user()
    last_suggested = user.get("last_suggested")
    history = recent_dishes(user["id"], limit=7)
    return render_template(
        "dashboard.html",
        suggestion=suggestion,
        last_suggested=last_suggested,
        history=history,
        email=user["email"]
    )


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


if __name__ == "__main__":
    app.run(port=5050)
