import os
import sqlite3
import telebot
import schedule
from time import time
from time import sleep
from datetime import datetime
from datetime import timedelta


GROUP_ID = os.getenv("GROUP_ID")
API_TOKEN = os.getenv("API_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

database = sqlite3.connect("telebot-captcha.db")
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

cursor = database.cursor()

def captcha_timeout():

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

schedule.every(1).minutes.do(captcha_timeout)

while True:
    schedule.run_pending()
    sleep(1)