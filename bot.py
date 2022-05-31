import os
import sqlite3
import telebot
from datetime import datetime
from datetime import timedelta
from telebot.types import WebAppInfo
from telebot.util import extract_arguments
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton

GROUP_ID = os.getenv("GROUP_ID")
API_TOKEN = os.getenv("API_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

database = sqlite3.connect("telebot-captcha.db")
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=["start"])
def start(message):
	if extract_arguments(message.text) == "captcha":
		bot.send_message(message.chat.id, "<b><i>In order to remove restrictions,\
please complete the verification.</i></b>", reply_markup=InlineKeyboardMarkup(
		).row(InlineKeyboardButton("CLICK HERE TO VERIFY ✅",
		web_app=WebAppInfo("https://telebot-captcha.cf/captcha"))))
	else:
		bot.send_message(message.chat.id, "<b><i>Hi, I manage all CAPTCHA verifications! 🤖</i></b>")


@bot.message_handler(content_types=['new_chat_members'])
def new_member(message):
	telegram_id = message.new_chat_members[0].id
	if message.from_user.username:
		user_name = message.new_chat_members[0].username
	else:
		user_name = message.new_chat_members[0].first_name
	database = sqlite3.connect("telebot-captcha.db")
	cursor = database.cursor()
	cursor.execute("INSERT INTO captcha(user_id, name, timeout) values(?, ?, ?)",
	(telegram_id, user_name, int(datetime.timestamp(datetime.now() + timedelta(minutes=5)))))
	database.commit()
	bot.restrict_chat_member(
			message.chat.id,
			telegram_id,
			can_send_messages=False,
			can_send_media_messages=False,
			can_send_polls=False,
			can_send_other_messages=False,
			can_add_web_page_previews=False,
			can_change_info=False,
			can_invite_users=False,
			can_pin_messages=False,
		)
	bot.send_message(message.chat.id, "<b><i>In order to prevent spam,\
	we require all members to pass a CAPTCHA.</i></b>",
	reply_markup=InlineKeyboardMarkup().row(InlineKeyboardButton(
		"COMPLETE VERIFICATION ✅", url=f"http://t.me/{BOT_USERNAME}?start=captcha")))


@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):

	if call.data[:10] == "unrestrict":
		user_id = int(call.data[10:])
		if call.message.from_user.username:
			user_name = call.message.from_user.username
		else:
			user_name = call.message.from_user.first_name
		bot.restrict_chat_member(
            GROUP_ID,
            user_id,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
        )
		bot.delete_message(call.message.chat.id, call.message.id)
		bot.send_message(call.message.chat.id, "<b><i>Restrictions removed ✅</i></b>")
		bot.send_message(GROUP_ID, f"<b>[<a href='tg://user?id={user_id}'>{user_name}</a>] passed CAPTCHA ✅\n\
			\n<i>All restrictions removed! ✌🏻</i></b>")

bot.infinity_polling(skip_pending=True)