import sqlite3
import sys
from datetime import datetime
from config import DB_PATH
from whatsapp_client import send_text_message, send_template_message

def main():
    # Calculate tomorrow's day index (0 = Monday, 6 = Sunday)
    tomorrow_index = (datetime.now().weekday() + 1) % 7
    print(f"Running ingredient alerts. Tomorrow's day index: {tomorrow_index}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Query all users with an active plan for tomorrow and a registered wa_id
    query = """
    SELECT users.id as user_id, users.wa_id, users.email, weekly_plans.dish 
    FROM users 
    JOIN weekly_plans ON users.id = weekly_plans.user_id 
    WHERE weekly_plans.day_index = ? AND users.wa_id IS NOT NULL;
    """
    
    rows = conn.execute(query, (tomorrow_index,)).fetchall()
    conn.close()

    print(f"Found {len(rows)} users to alert.")

    for row in rows:
        wa_id = row["wa_id"]
        dish = row["dish"]
        email = row["email"]
        
        message_body = f"Hey! Just a check-in from Chef Chat. 🍳 You are scheduled to cook *{dish}* tomorrow. Be sure to bring all ingredients home! 🛒🥗"
        print(f"Sending alert to {email} ({wa_id}) for tomorrow's dish: {dish}")
        
        # 1. Try sending custom text message first
        status, response = send_text_message(wa_id, message_body)
        print(f"Text message status: {status}, Response: {response}")
        
        # 2. If it fails (usually due to 24h window restriction), send template message
        if status != 200:
            print("Direct text message failed. Attempting template message fallback...")
            template_param = f"Tomorrow's dish is {dish}! Get your ingredients ready."
            t_status, t_response = send_template_message(
                to=wa_id,
                template_name="daily_meal_checkin",
                params={"quiz_link": template_param}
            )
            print(f"Template message status: {t_status}, Response: {t_response}")

if __name__ == "__main__":
    main()
