import requests

from config import ACCESS_TOKEN, API_VERSION, PHONE_NUMBER_ID

BASE_URL = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def send_text_message(to, body):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    response = requests.post(BASE_URL, headers=HEADERS, json=payload)
    return response.status_code, response.json()


def send_template_message(to, template_name, params=None, language="en", namespace=None):
    template = {
        "name": template_name,
        "language": {"code": language, "policy": "deterministic"},
    }
    if namespace:
        template["namespace"] = namespace
    if params:
        template["components"] = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "parameter_name": name, "text": value}
                    for name, value in params.items()
                ],
            }
        ]
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template,
    }
    response = requests.post(BASE_URL, headers=HEADERS, json=payload)
    return response.status_code, response.json()
