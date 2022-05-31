import os
import flask
import sqlite3
import telebot
import pymysql
from flask import redirect
from datetime import datetime
from datetime import timedelta
from utils import parse_web_app_data
from utils import validate_web_app_data
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton
from telebot.types import InputTextMessageContent
from telebot.types import InlineQueryResultArticle

GROUP_ID = os.getenv("GROUP_ID")
API_TOKEN = os.getenv("API_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

app = flask.Flask(__name__)
# database = sqlite3.connect("telebot-captcha.db")
database = pymysql.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"), 
    port=os.getenv("MYSQLPORT"),
    db=os.getenv("MYSQLDATABASE"),
    password=os.getenv("MYSQLPASSWORD")
)

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


if __name__ == '__main__':
	app.run(debug=True)
