import os
import flask
import sqlite3
import telebot
import schedule
import threading
from time import time
from time import sleep
from flask import redirect
from datetime import datetime
from datetime import timedelta
from utils import parse_web_app_data
from telebot.types import WebAppInfo
from utils import validate_web_app_data
from telebot.util import extract_arguments
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton
from telebot.types import InputTextMessageContent
from telebot.types import InlineQueryResultArticle

GROUP_ID = os.getenv("GROUP_ID")
API_TOKEN = os.getenv("API_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

app = flask.Flask(__name__)
database = sqlite3.connect("telebot-captcha.db")
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

cursor = database.cursor()
cursor.execute(
	"""
		CREATE TABLE IF NOT EXISTS captcha(
			user_id INTEGER NOT NULL PRIMARY KEY,
			name VARCHAR(128) NOT NULL,
			timeout TIMESTAMP NOT NULL
		)
	"""
)
database.commit()

def captcha_timeout():
	database = sqlite3.connect("telebot-captcha.db")
	cursor = database.cursor()
	records = cursor.execute("SELECT * FROM captcha").fetchall()
	for _ in records:
		if int(_[-1]) <= int(time()):
			try:
				user_id = int(-[0])
				bot.send_message(GROUP_ID, f"<b>[<a href='tg://user?id={user_id}'>{_[1]}</a>] was banned!\n\
					\n<i>Reason: CAPTCHA timeout ⌛</i></b>")
				bot.ban_chat_member(GROUP_ID, user_id, int(datetime.timestamp(
					datetime.now() + timedelta(days=1))), False)
				cursor.execute(f"DELETE * FROM captcha WHERE user_id = {user_id}")
				database.commit()
			except:
				pass

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


@app.route('/')
def home():
	return "HEllo"


@app.errorhandler(404)
def error_404(e):
	return redirect("/")


@app.route('/captcha')
def captcha():
	return flask.render_template("index.html")


@app.route('/verify', methods=['POST'])
def verify():
	
	raw_data = flask.request.get_json()

	isbot = raw_data["isbot"]
	data = raw_data["data"]
	attempts = raw_data["attempts"]

	isValid = validate_web_app_data(API_TOKEN, data)

	if isValid:		
		if not isbot:
			initData = parse_web_app_data(API_TOKEN, data)
			query_id = initData["query_id"]
			user_id = initData["user"].id
			bot.answer_web_app_query(query_id, InlineQueryResultArticle(
				id=query_id, title="VERIFICATION PASSED!",
				input_message_content=InputTextMessageContent(
					"<b><i>Captcha verification passed ✅\n\
					\nClick the button to remove all restrictions 👇🏻</i></b>",
					parse_mode="HTML"), reply_markup=InlineKeyboardMarkup().row(
						InlineKeyboardButton("🟢 REMOVE RESTRICTIONS 🟢",
						callback_data=f"unrestrict::{user_id}"))))
		else:
			if attempts == 3:
				initData = parse_web_app_data(API_TOKEN, data)
				query_id = initData["query_id"]
				user_id = initData["user"].id
				if initData["user"].username:
					user_name = initData["user"].username
				else:
					user_name = initData["user"].first_name
				bot.answer_web_app_query(query_id, InlineQueryResultArticle(
					id=query_id, title="VERIFICATION FAILED!",
					input_message_content=InputTextMessageContent(
						"<b><i>Captcha verification failed ❌</i></b>")))

				bot.send_message(GROUP_ID, f"<b>[<a href='tg://user?id={user_id}'>{user_name}</a>] was banned!\n\
					\n<i>Reason: Could not complete CAPTCHA 🤖</i></b>")
				bot.ban_chat_member(GROUP_ID, user_id, int(datetime.timestamp(
					datetime.now() + timedelta(days=1))), False)					
				bot.send_message(user_id, "<b>You are banned from our group for now. ☹️\n\
				\nDon't worry you can try again tommorow! ✌🏻</b>")

	return ""

def polling():
	bot.infinity_polling()

schedule.every(1).minutes.do(captcha_timeout)

def captcha_timeout_thread():
    while True:
        schedule.run_pending()
        sleep(1)

polling_thread = threading.Thread(target=polling)
captcha_thread = threading.Thread(target=captcha_timeout_thread)

if __name__ == '__main__':
	polling_thread.start()
	captcha_thread.start()
	app.run(debug=True)
