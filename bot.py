import requests
import json
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


# =========================================================
# CONFIGURATION
# =========================================================

BOT_TOKEN = "8958671174:AAGCu6Uk2HbfrUPb5iE_MP84s7cySoOLiP4"

EXTERNAL_API_URL = "https://backemdhub.zone.id/api/osint/num?mobile=8002549931&key=JhjXT2HUtmjGlme_ugMEXQ"

# Put your Telegram numeric User ID here
# Example: ADMIN_ID = "123456789"
ADMIN_ID = "5017811608"

PHONE_BUTTON = "📱 Phone Lookup"


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Telegram bot is running.")

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = {
                "status": "ok",
                "telegram_bot": "running"
            }

            self.wfile.write(
                json.dumps(response).encode("utf-8")
            )

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_web_server():
    port = int(os.environ.get("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print("HTTP server started on port:", port)

    server.serve_forever()


# =========================================================
# TELEGRAM FUNCTIONS
# =========================================================

def telegram_api_url(method):
    return (
        "https://api.telegram.org/bot"
        + BOT_TOKEN
        + "/"
        + method
    )


def send_message(chat_id, text, reply_markup=None):
    url = telegram_api_url("sendMessage")

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup is not None:
        data["reply_markup"] = json.dumps(reply_markup)

    try:
        response = requests.post(
            url,
            data=data,
            timeout=30
        )

        return response.json()

    except (requests.RequestException, ValueError):
        return None


def get_updates(offset):
    url = telegram_api_url("getUpdates")

    params = {
        "offset": offset,
        "timeout": 30
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=35
        )

        return response.json()

    except (requests.RequestException, ValueError):
        return None


# =========================================================
# EXTERNAL API
# =========================================================

def phone_lookup(phone_number):

    if not EXTERNAL_API_URL:
        return {
            "error": "External API URL is not configured."
        }

    try:
        response = requests.get(
            EXTERNAL_API_URL,
            params={
                "phone": phone_number
            },
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        return {
            "error": "External API request failed.",
            "details": str(error)
        }

    except ValueError:

        return {
            "error": "External API returned invalid JSON."
        }


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id):

    if not ADMIN_ID:
        return False

    return str(user_id) == str(ADMIN_ID)


# =========================================================
# MAIN BOT
# =========================================================

def main():

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN is empty.")
        return

    keyboard = {
        "keyboard": [
            [
                {
                    "text": PHONE_BUTTON
                }
            ]
        ],
        "resize_keyboard": True
    }

    offset = 0

    print("Telegram bot started.")

    while True:

        updates = get_updates(offset)

        if updates is None:
            time.sleep(3)
            continue

        if not updates.get("ok"):
            print("Telegram API error.")
            time.sleep(3)
            continue

        for update in updates.get("result", []):

            offset = update["update_id"] + 1

            message = update.get("message")

            if not message:
                continue

            chat = message.get("chat")

            if not chat:
                continue

            chat_id = chat.get("id")

            user = message.get("from", {})

            user_id = user.get("id")

            text = message.get("text", "").strip()

            if not text:
                continue

            # =================================================
            # /start
            # =================================================

            if text == "/start":

                welcome_message = (
                    "👋 Welcome!\n\n"
                    "Use the button below to continue."
                )

                send_message(
                    chat_id,
                    welcome_message,
                    keyboard
                )

                continue

            # =================================================
            # ADMIN COMMAND
            # =================================================

            if text == "/admin":

                if is_admin(user_id):

                    admin_message = (
                        "🔐 Admin Panel\n\n"
                        "Your Telegram User ID:\n"
                        + str(user_id)
                        + "\n\n"
                        "Admin access: ENABLED"
                    )

                    send_message(
                        chat_id,
                        admin_message,
                        keyboard
                    )

                else:

                    send_message(
                        chat_id,
                        "❌ You are not authorized as admin.",
                        keyboard
                    )

                continue

            # =================================================
            # PHONE LOOKUP BUTTON
            # =================================================

            if text == PHONE_BUTTON:

                send_message(
                    chat_id,
                    "📞 Send 10 digit mobile number:",
                    keyboard
                )

                continue

            # =================================================
            # PHONE NUMBER VALIDATION
            # =================================================

            if text.isdigit():

                if len(text) != 10:

                    send_message(
                        chat_id,
                        "❌ Invalid number.\n\n"
                        "Please send exactly 10 digits.",
                        keyboard
                    )

                    continue

                # Call external API
                result = phone_lookup(text)

                # Format JSON
                formatted_json = json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False
                )

                telegram_message = (
                    "<pre>"
                    + formatted_json
                    + "</pre>"
                )

                send_message(
                    chat_id,
                    telegram_message,
                    keyboard
                )

                continue

            # =================================================
            # INVALID INPUT
            # =================================================

            send_message(
                chat_id,
                "❌ Invalid input.\n\n"
                "Please press "
                + PHONE_BUTTON
                + " and send a 10 digit number.",
                keyboard
            )

        time.sleep(1)


# =========================================================
# START EVERYTHING
# =========================================================

if __name__ == "__main__":

    # Start Render HTTP server in background
    server_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    server_thread.start()

    # Start Telegram long polling
    main()
