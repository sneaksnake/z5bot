import json
import logging
import os

import redis
import telegram.ext

import parser
from dfrotz import DFrotz

logging.basicConfig(
  format='%(asctime)s-%(name)s-%(levelname)s - %(message)s',
  datefmt='%Y-%m-%d %H:%M:%S',
  level=logging.DEBUG,
)
logging.getLogger('telegram').setLevel(logging.WARNING)


def cmd_start(bot, update):
  text =  'Welcome, %s!\n' % update.message.from_user.first_name
  text += 'Please use the /select command to select a game.\n'
  text += '(You will lose progress on any running game!)'
  bot.sendMessage(update.message.chat_id, text=text)

def cmd_select(bot, update):
  z5bot = Z5Bot.get_instance_or_create()

  id = update.message.chat_id
  chat = Chat.get_instance_or_create(id)
  
  selection = 'For "%s", write /select %s.'
  msg_parts = []
  for story in Story.instances:
    part = selection % (story.name, story.abbrev)
    msg_parts.append(part)
  text = '\n'.join(msg_parts)

  for story in Story.instances:
    if story.abbrev in update.message.text:
      chat.set_story(Story.get_instance_by_abbrev(story.abbrev))
      z5bot.add_chat(chat)
      bot.sendMessage(update.message.chat_id, text='Starting "%s"...' % story.name)
      notice  = 'Your progress will be saved automatically.'
      bot.sendMessage(update.message.chat_id, text=notice)
      bot.sendMessage(update.message.chat_id, text=z5bot.receive(update.message.chat_id))
      if z5bot.redis.exists(update.message.chat_id):
        notice  = 'Some progress already exists. Use /load to restore it '
        notice += 'or /clear to reset your recorded actions.'
        bot.sendMessage(update.message.chat_id, text=notice)
      return

  bot.sendMessage(update.message.chat_id, text=text)

def on_message(bot, update):
  logging.info('@%s[%d] sent: %r' % (
    update.message.from_user.username,
    update.message.from_user.id,
    update.message.text[:30])
  )

  if update.message.text.strip() == 'load':
    text = 'Please use /load.'
    bot.sendMessage(update.message.chat_id, text=text)
    return

  if update.message.text.strip() == 'save':
    text = 'Your progress is being saved automatically. But /load is available.'
    bot.sendMessage(update.message.chat_id, text=text)
    return

  z5bot = Z5Bot.get_instance_or_create()


  id = update.message.chat_id
  chat = Chat.get_instance_or_create(id)

  if chat.story is None:
    text = 'Please use the /select command to select a game.'
    bot.sendMessage(update.message.chat_id, text=text)
    return

  # here, stuff is sent to the interpreter
  z5bot.redis.rpush(update.message.chat_id, update.message.text)
  z5bot.process(id, update.message.text)

  received = z5bot.receive(id)
  logging.info('Answering @%s[%d]: %r' % (
    update.message.from_user.username,
    update.message.from_user.id,
    received[:30])
  )
  bot.sendMessage(update.message.chat_id, text=received)
  if ' return ' in received.lower() or ' enter ' in received.lower():
    notice = '(Note: You are able to do use the return key by typing /enter.)'
    bot.sendMessage(update.message.chat_id, text=notice)

def cmd_load(bot, update):
  z5bot = Z5Bot.get_instance_or_create()

  chat = Chat.get_instance_or_create(update.message.chat_id)
  if chat.story is None:
    text = 'You have to select a game first.'
    bot.sendMessage(update.message.chat_id, text=text)
    return

  if not z5bot.redis.exists(update.message.chat_id):
    text = 'There is no progress to load.'
    bot.sendMessage(update.message.chat_id, text=text)
    return

  text = 'Restoring %d messages. Please wait.' % z5bot.redis.llen(update.message.chat_id)
  bot.sendMessage(update.message.chat_id, text=text)

  messages = z5bot.redis.lrange(update.message.chat_id, 0, -1)

  for index, message in enumerate(messages):
    z5bot.process(update.message.chat_id, message.decode('utf-8'))
    if index == len(messages)-2:
      z5bot.receive(update.message.chat_id) # clear buffer
  bot.sendMessage(update.message.chat_id, text='Done.')
  bot.sendMessage(update.message.chat_id, text=z5bot.receive(update.message.chat_id))

def cmd_clear(bot, update):
  z5bot = Z5Bot.get_instance_or_create()

  if not z5bot.redis.exists(update.message.chat_id):
    text = 'There is no progress to clear.'
    bot.sendMessage(update.message.chat_id, text=text)
    return

  text = 'Deleting %d messages. Please wait.' % z5bot.redis.llen(update.message.chat_id)
  bot.sendMessage(update.message.chat_id, text)

  z5bot.redis.delete(update.message.chat_id)
  bot.sendMessage(update.message.chat_id, text='Done.')

def key_enter(bot, update):
  z5bot = Z5Bot.get_instance_or_create()
  chat = Chat.get_instance_or_create(update.message.chat_id)
  if chat.story is None:
    return
  command = '' # \r\n is automatically added by the Frotz abstraction layer
  z5bot.redis.rpush(update.message.chat_id, command)
  z5bot.process(update.message.chat_id, command)
  bot.sendMessage(update.message.chat_id, text=z5bot.receive(update.message.chat_id))

def let_ignore(bot, update):
  return

def on_error(bot, update, error):
  logger = logging.getLogger(__name__)
  logger.warn('Update %r caused error %r!' % (update, error))
  print(error)


if __name__ == '__main__':
  with open('config.json', 'r') as f:
    config = json.load(f)

  api_key = config['api_key']
  logging.info('Logging in with api key %r' % api_key)

  for story in config['stories']:
    Story(name=story['name'],
      abbrev=story['abbrev'],
      filename=story['filename'])

  print(Story.instances)

  z5bot = Z5Bot.get_instance_or_create()
  r = redis.StrictRedis(
    host=config['redis']['host'],
    port=config['redis']['port'],
    db=config['redis']['db']
  )
  z5bot.add_redis(r)

  updater = telegram.ext.Updater(api_key)

  job_queue = updater.job_queue

  dispatcher = updater.dispatcher
  dispatcher.addTelegramCommandHandler('start', cmd_start)
  dispatcher.addTelegramCommandHandler('select', cmd_select)
  dispatcher.addTelegramCommandHandler('load', cmd_load)
  dispatcher.addTelegramCommandHandler('clear', cmd_clear)
  dispatcher.addTelegramCommandHandler('enter', key_enter)
  dispatcher.addTelegramCommandHandler('i', let_ignore)
  dispatcher.addTelegramMessageHandler(on_message)
  dispatcher.addErrorHandler(on_error)


  updater.start_polling()
  updater.idle()