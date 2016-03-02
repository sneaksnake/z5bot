import logging
import os

import telegram

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

  @classmethod
  def get_instance_or_create(self):
    if len(self.instances) > 0:
      instance = self.instances[0]
      logging.debug('Using existing Z5Bot instance: %r' % instance)
    else:
      instance = Z5Bot()
      logging.debug('Created new Z5Bot instance: %r' % instance)
    return instance

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
  
  text = 'For Zork 1, write /select z1\nMore games soon.'
  if 'z1' in update.message.text: 
    chat.set_story(Story(name='Zork 1', abbrev='z1', filename='zork_1-r52.z5'))
    z5bot.add_chat(chat)
    bot.sendMessage(update.message.chat_id, text=z5bot.receive(update.message.chat_id))
  else:
    bot.sendMessage(update.message.chat_id, text=text)

def on_message(bot, update):
  z5bot = Z5Bot.get_instance_or_create()

  logging.info('@%s[%d] sent: %r' % (update.message.from_user.username, update.message.from_user.id, update.message.text[:30]))

  id = update.message.chat_id
  chat = Chat.get_instance_or_create(id)

  if chat.story is None:
    text = 'Please use the /select command to select a game.'
    bot.sendMessage(update.message.chat_id, text=text)
    return

  z5bot.process(id, update.message.text)

  received = z5bot.receive(id)
  logging.info('Answering @%s[%d]: %r' % (update.message.from_user.username, update.message.from_user.id, received[:30]))
  bot.sendMessage(update.message.chat_id, text=received)

def on_error(bot, update, error):
  logger = logging.getLogger(__name__)
  logger.warn('Update %r caused error %r!' % (update, error))
  print(error)


if __name__ == '__main__':
  with open('config.txt', 'r') as config_file:
    api_key = config_file.read().replace('\n', '')
    print('api key: ' + api_key)
    updater = telegram.Updater(api_key)
  dispatcher = updater.dispatcher

  dispatcher.addTelegramCommandHandler('start', cmd_start)
  dispatcher.addTelegramCommandHandler('select', cmd_select)
  dispatcher.addTelegramMessageHandler(on_message)
  dispatcher.addErrorHandler(on_error)
  updater.start_polling()
  updater.idle()