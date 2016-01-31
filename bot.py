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

class Player:

  instances = []

  def __init__(self, username):
    self.__class__.instances.append(self)
    self.username = username
    self.story = None
    #self.stage = 

  @classmethod
  def get_instance_or_create(self, username):
    if len(self.instances) > 0:
      for player in self.instances:
        if player.username == username:
          logging.debug('Using existing Player instance: %r' % player)
          return player
    # no instance found / not existing
    player = Player(username)
    logging.debug('Created new Player instance: %r' % player)
    return player

  def set_story(self, story):
    self.story = story
    self.frotz = DFrotz(Z5Bot.interpreter, self.story.path)

  def __repr__(self):
    if self.story is not None:
      return '<Player %r, playing %r>' % (self.username, self.story.name)

    return '<Player %r>' % self.username

class Z5Bot:

  instances = []
  interpreter = os.path.join('tools', 'dfrotz')

  def __init__(self):
    self.__class__.instances.append(self)
    self.players = []

  @classmethod
  def get_instance_or_create(self):
    if len(self.instances) > 0:
      instance = self.instances[0]
      logging.debug('Using existing z5bot instance: %r' % instance)
    else:
      instance = Z5Bot()
      logging.debug('Created new z5bot instance: %r' % instance)
    return instance

  def add_player(self, player):
    self.players.append(player)

  def get_player_by_username(self, username):
    for player in self.players:
      if player.username == username:
        return player

  def process(self, username, command):
    self.player = self.get_player_by_username(username)
    self.player.frotz.send('%s\r\n' % command)

  def receive(self, username):
    self.player = self.get_player_by_username(username)
    return self.player.frotz.get()


def cmd_start(bot, update):
  text =  'Welcome, %s!\n' % update.message.from_user.first_name
  text += 'Please use the /select command to select a game.\n'
  text += '(You will lose progress on any running game!)'
  bot.sendMessage(update.message.chat_id, text=text)

def cmd_select(bot, update):
  z5bot = Z5Bot.get_instance_or_create()

  username = update.message.from_user.username
  player = Player.get_instance_or_create(username)
  
  text = 'For Zork 1, write /select z1\nMore games soon.'
  if 'z1' in update.message.text: 
    player.set_story(Story(name='Zork 1', abbrev='z1', filename='zork_1-r52.z5'))
    z5bot.add_player(player)
    bot.sendMessage(update.message.chat_id, text=z5bot.receive(update.message.from_user.username))
  else:
    bot.sendMessage(update.message.chat_id, text=text)

def on_message(bot, update):
  z5bot = Z5Bot.get_instance_or_create()

  logging.info('@%s sent: %r' % (update.message.from_user.username, update.message.text[:30]))

  username = update.message.from_user.username
  player = Player.get_instance_or_create(username)

  if player.story is None:
    text = 'Please use the /select command to select a game.'
    bot.sendMessage(update.message.chat_id, text=text)
    return

  # print(player.story)

  #if z5bot.get_player_by_username(username) is None:
  #  logging.debug('Adding Player %r to the bot.' % player)
  #  z5bot.add_player(player)
  z5bot.process(username, update.message.text)

  received = z5bot.receive(username)
  logging.info('Answering @%s: %r' % (update.message.from_user.username, received[:30]))
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