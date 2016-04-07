import json
import logging
import os

import redis
import telegram.ext

from dfrotz import DFrotz

logging.basicConfig(
  format='%(asctime)s-%(name)s-%(levelname)s - %(message)s',
  datefmt='%Y-%m-%d %H:%M:%S',
  level=logging.DEBUG,
)
logging.getLogger('telegram').setLevel(logging.WARNING)


class Story:

  instances = []

  def __init__(self, name, abbrev, filename):
    self.__class__.instances.append(self)
    self.name = name
    self.abbrev = abbrev
    self.path = os.path.join('stories', filename)

  @classmethod
  def get_instance_by_abbrev(self, abbrev):
    for story in self.instances:
      if story.abbrev == abbrev:
        return story
    return None

  def __repr__(self):
    return '<Story: %s [%s]>' % (self.abbrev, self.path)

class Chat:

  instances = []

  def __init__(self, id):
    self.__class__.instances.append(self)
    self.id = id
    self.story = None
    #self.stage = 

  @classmethod
  def get_instance_or_create(self, id):
    if len(self.instances) > 0:
      for chat in self.instances:
        if chat.id == id:
          logging.debug('Using existing Chat instance: %r' % chat)
          return chat
    # no instance found / not existing
    chat = Chat(id)
    logging.debug('Created new Chat instance: %r' % chat)
    return chat

  def set_story(self, story):
    self.story = story
    self.frotz = DFrotz(Z5Bot.interpreter, self.story.path)

  def __repr__(self):
    if self.story is not None:
      return '<Chat: %d, playing %r>' % (self.id, self.story.name)

    return '<Chat: %d>' % self.id

class Z5Bot:

  instances = []
  interpreter = os.path.join('tools', 'dfrotz')

  def __init__(self):
    self.__class__.instances.append(self)
    self.chats = []
    self.redis = None

  @classmethod
  def get_instance_or_create(self):
    if len(self.instances) > 0:
      instance = self.instances[0]
      logging.debug('Using existing Z5Bot instance: %r' % instance)
    else:
      instance = Z5Bot()
      logging.debug('Created new Z5Bot instance: %r' % instance)
    return instance

  def add_redis(self, redis):
    self.redis = redis

  def add_chat(self, chat):
    self.chats.append(chat)

  def get_chat_by_id(self, id):
    for chat in self.chats:
      if chat.id == id:
        return chat

  def process(self, id, command):
    self.chat = self.get_chat_by_id(id)
    self.chat.frotz.send('%s\r\n' % command)

  def receive(self, id):
    self.chat = self.get_chat_by_id(id)
    return self.chat.frotz.get()

  def __repr__(self):
    return '<Z5Bot, chats running: %d>' % len(self.chats)


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
      if z5bot.redis is None:
        # TODO: make it configurable. for now on, just edit this file
        r = redis.StrictRedis(host='192.168.178.53', port=6379, db=1)
        z5bot.add_redis(r)
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
  if 'return' in received.lower() or 'enter' in received.lower():
    notice = '(Note: You are able to do that by typing /enter.)'
    bot.sendMessage(update.message.chat_id, text=received)

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

  updater = telegram.ext.Updater(api_key)

  job_queue = updater.job_queue

  dispatcher = updater.dispatcher
  dispatcher.addTelegramCommandHandler('start', cmd_start)
  dispatcher.addTelegramCommandHandler('select', cmd_select)
  dispatcher.addTelegramCommandHandler('load', cmd_load)
  dispatcher.addTelegramCommandHandler('clear', cmd_clear)
  dispatcher.addTelegramCommandHandler('enter', key_enter)
  dispatcher.addTelegramMessageHandler(on_message)
  dispatcher.addErrorHandler(on_error)


  updater.start_polling()
  updater.idle()