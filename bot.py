import os
import requests
import threading
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import uuid
from database import init_db, save_transaction, get_transaction, mark_as_paid
from unifi import create_voucher
import webhook  # our Flask webhook receiver

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PORT = int(os.getenv("PORT", 8080))

PLANS = {
    "daily": {
        "label": "📅 Daily Plans (24hrs)",
        "options": [
            {"id": "d1", "text": "₦100 - 300MB", "price": 100, "data": "300MB", "validity": "24 hours"},
            {"id": "d2", "text": "₦200 - 750MB", "price": 200, "data": "750MB", "validity": "24 hours"},
            {"id": "d3", "text": "₦300 - 1.5GB", "price": 300, "data": "1.5GB", "validity": "24 hours"},
            {"id": "d4", "text": "₦500 - 2.5GB", "price": 500, "data": "2.5GB", "validity": "24 hours"},
            {"id": "d5", "text": "₦1,000 - 5GB", "price": 1000, "data": "5GB", "validity": "24 hours"},
        ]
    },
    "weekly": {
        "label": "📆 Weekly Plans (7 days)",
        "options": [
            {"id": "w1", "text": "₦1,000 - 4GB", "price": 1000, "data": "4GB", "validity": "7 days"},
            {"id": "w2", "text": "₦1,500 - 7.5GB", "price": 1500, "data": "7.5GB", "validity": "7 days"},
            {"id": "w3", "text": "₦2,000 - 12GB", "price": 2000, "data": "12GB", "validity": "7 days"},
        ]
    },
    "monthly": {
        "label": "🗓️ Monthly Plan",
        "options": [
            {"id": "m1", "text": "₦20,000 - Unlimited", "price": 20000, "data": "Unlimited", "validity": "30 days"},
        ]
    }
}

def create_payment_link(email: str, amount_naira: int, reference: str):
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "amount": amount_naira * 100,
        "reference": reference,
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def verify_payment(reference: str):
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    response = requests.get(url, headers=headers)
    return response.json()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Ayosco hub! 👋\nType /buy to see our data plans, or /help for more info."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Here's how it works:\n"
        "1. Type /buy and choose a category\n"
        "2. Pick your plan\n"
        "3. Enter your email address\n"
        "4. Pay securely\n"
        "5. Get your voucher instantly"
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(PLANS[key]["label"], callback_data=f"cat_{key}")]
        for key in PLANS
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a category:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        options = PLANS[category]["options"]
        keyboard = [
            [InlineKeyboardButton(opt["text"], callback_data=f"plan_{category}_{opt['id']}")]
            for opt in options
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_categories")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"{PLANS[category]['label']}\nSelect a plan:", reply_markup=reply_markup)

    elif data.startswith("plan_"):
        _, category, plan_id = data.split("_")
        plan = next(opt for opt in PLANS[category]["options"] if opt["id"] == plan_id)

        # Store the selected plan in user context, then ask for email
        context.user_data["pending_plan"] = plan
        context.user_data["awaiting_email"] = True

        await query.edit_message_text(
            f"You selected:\n"
            f"📦 {plan['data']} for ₦{plan['price']:,}\n"
            f"⏳ Valid for {plan['validity']}\n\n"
            f"📧 Please type your email address to continue:"
        )

    elif data.startswith("verify_"):
        reference = data.replace("verify_", "")
        transaction = get_transaction(reference)

        if not transaction:
            await query.edit_message_text("⚠️ Transaction not found. Please start again with /buy.")
            return

        if transaction["status"] == "paid":
            # Already processed — likely the webhook beat the manual tap to it
            await query.edit_message_text("✅ This payment was already confirmed and processed.")
            return

        result = verify_payment(reference)

        if result.get("status") and result["data"]["status"] == "success":
            mark_as_paid(reference)

            voucher_code = create_voucher(
                plan_data=transaction["plan_data"],
                validity=transaction["validity"],
                note=f"ayosco_{reference}"
            )

            if voucher_code:
                formatted_code = f"{voucher_code[:5]}-{voucher_code[5:]}"
                await query.edit_message_text(
                    f"✅ Payment confirmed!\n\n"
                    f"📦 {transaction['plan_data']} for ₦{transaction['price']:,}\n"
                    f"⏳ Valid for {transaction['validity']}\n\n"
                    f"🎫 Your voucher code:\n"
                    f"`{formatted_code}`\n\n"
                    f"Connect to AyoscoHub WiFi and enter this code to get online!",
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    f"✅ Payment confirmed!\n\n"
                    f"⚠️ We couldn't auto-generate your voucher right now. "
                    f"Please contact support with reference: {reference}"
                )
        else:
            await query.edit_message_text(
                "❌ Payment not confirmed yet. If you've already paid, wait a few seconds and try again, "
                "or contact support if this persists."
            )

    elif data == "back_to_categories":
        keyboard = [
            [InlineKeyboardButton(PLANS[key]["label"], callback_data=f"cat_{key}")]
            for key in PLANS
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose a category:", reply_markup=reply_markup)


async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the customer's email input after selecting a plan."""

    # Only process if we're actually waiting for an email
    if not context.user_data.get("awaiting_email"):
        return

    email = update.message.text.strip()

    # Basic email validation
    if "@" not in email or "." not in email.split("@")[-1]:
        await update.message.reply_text(
            "⚠️ That doesn't look like a valid email address. Please try again:"
        )
        return

    plan = context.user_data.get("pending_plan")
    if not plan:
        await update.message.reply_text("⚠️ Something went wrong. Please start again with /buy.")
        context.user_data.clear()
        return

    # Clear the waiting state
    context.user_data["awaiting_email"] = False
    context.user_data["pending_plan"] = None

    reference = f"ayosco_{uuid.uuid4().hex[:12]}"
    result = create_payment_link(email, plan["price"], reference)

    if result.get("status"):
        payment_url = result["data"]["authorization_url"]

        save_transaction(reference, update.effective_user.id, plan)

        keyboard = [
            [InlineKeyboardButton("💳 Pay Now", url=payment_url)],
            [InlineKeyboardButton("✅ I've Paid - Verify", callback_data=f"verify_{reference}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Email saved: {email}\n\n"
            f"📦 {plan['data']} for ₦{plan['price']:,}\n"
            f"⏳ Valid for {plan['validity']}\n\n"
            f"Tap below to pay, then tap Verify once done:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "⚠️ Something went wrong creating your payment link. Please try again with /buy."
        )


def run_webhook_server():
    """Runs the Flask webhook server in a background thread."""
    webhook.webhook_app.run(host="0.0.0.0", port=PORT, use_reloader=False)


async def post_init(application):
    """Captures the running event loop so the webhook thread can schedule Telegram messages onto it."""
    loop = asyncio.get_running_loop()
    webhook.set_bot_instance(application.bot, loop)


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Email handler — must come after command handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, email_handler))

    # Start Flask webhook server in a background thread alongside Telegram polling
    webhook_thread = threading.Thread(target=run_webhook_server, daemon=True)
    webhook_thread.start()
    print(f"Webhook server running on port {PORT}...")

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()