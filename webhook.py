import os
import hmac
import hashlib
import asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from database import get_transaction, mark_as_paid
from unifi import create_voucher

load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

webhook_app = Flask(__name__)

# These are set by bot.py when it starts, so the webhook can send Telegram messages
telegram_bot = None
bot_loop = None


def set_bot_instance(bot, loop):
    """Called from bot.py to give this module access to the running bot and its event loop."""
    global telegram_bot, bot_loop
    telegram_bot = bot
    bot_loop = loop


def verify_signature(payload_body, signature_header):
    """Recomputes the HMAC-SHA512 signature and compares it to Paystack's header."""
    if not signature_header:
        return False

    computed_hash = hmac.new(
        PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload_body,
        hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(computed_hash, signature_header)


@webhook_app.route("/paystack-webhook", methods=["POST"])
def paystack_webhook():
    signature = request.headers.get("x-paystack-signature")
    raw_body = request.get_data()

    if not verify_signature(raw_body, signature):
        # Request did not come from Paystack — reject it
        return jsonify({"status": "invalid signature"}), 401

    event = request.get_json()

    if event.get("event") != "charge.success":
        # We only care about successful charges; acknowledge anything else and ignore it
        return jsonify({"status": "ignored"}), 200

    reference = event["data"]["reference"]
    transaction = get_transaction(reference)

    if not transaction:
        return jsonify({"status": "transaction not found"}), 404

    if transaction["status"] == "paid":
        # Already processed (maybe customer also tapped "Verify" manually) — avoid duplicate voucher
        return jsonify({"status": "already processed"}), 200

    mark_as_paid(reference)

    voucher_code = create_voucher(
        plan_data=transaction["plan_data"],
        validity=transaction["validity"],
        note=f"ayosco_{reference}"
    )

    user_id = transaction["user_id"]

    if voucher_code:
        formatted_code = f"{voucher_code[:5]}-{voucher_code[5:]}"
        message = (
            f"✅ Payment confirmed!\n\n"
            f"📦 {transaction['plan_data']} for ₦{transaction['price']:,}\n"
            f"⏳ Valid for {transaction['validity']}\n\n"
            f"🎫 Your voucher code:\n"
            f"`{formatted_code}`\n\n"
            f"Connect to AyoscoHub WiFi and enter this code to get online!"
        )
    else:
        message = (
            f"✅ Payment confirmed!\n\n"
            f"⚠️ We couldn't auto-generate your voucher right now. "
            f"Please contact support with reference: {reference}"
        )

    # Send the Telegram message from this sync Flask route into the bot's async loop
    if telegram_bot and bot_loop:
        asyncio.run_coroutine_threadsafe(
            telegram_bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown"),
            bot_loop
        )

    return jsonify({"status": "success"}), 200