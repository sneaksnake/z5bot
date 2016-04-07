# Z5Bot
A script to glue the Telegram Bot API and Frotz together.  
Maybe an instance is running [right now](http://telegram.me/z5bot)!

## Why?
Playing games by using this bot has these advantages:

- portability: play at home, then continue your game on the bus (e.g. via phone)
- collaboration: you can add the bot to a Telegram group and play games together!
- ease of use: you don't need an interpreter or game files, just Telegram

[Even a Raspberry Pi 2 is able to handle 30 different chats at the same time with ease!](https://i.imgur.com/GK3amYn.png)

## Screenshot
![it is actually able to run](https://raw.githubusercontent.com/sneaksnake/z5bot/master/media/demo-screenshot.png)  

At the time of writing, full documentation doesn't exist
and most stuff is hardcoded.
But if you want to give it a try anyway...

## Installation
Put bot.py, dfrotz.py in a directory. Rename config.json.example to config.json.  
Additionally, place create  
- e.g. stories/zork_1-r52.z5 (z5 file containing Zork I)
- tools/dfrotz (Frotz compiled in dumb-mode / see Frotz Makefile)  
and amend config.json.  

Install python-telegram-bot and run bot.py.

Have fun. :D
