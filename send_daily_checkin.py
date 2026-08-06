from db import all_onboarded_users, init_db
from whatsapp_client import send_template_message

CHECKIN_TEMPLATE_NAME = "daily_meal_checkin"


def main():
    init_db()
    for user in all_onboarded_users():
        # Pass a friendly prompt into the variable slot of the template
        status, response = send_template_message(
            user["wa_id"],
            CHECKIN_TEMPLATE_NAME,
            params={"quiz_link": "Select below or type your dish:"}
        )
        print(user["wa_id"], status, response)


if __name__ == "__main__":
    main()
