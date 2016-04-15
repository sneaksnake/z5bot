import logging
import os

import dfrotz

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

    def has_story(self):
        return self.story is not None

    def set_story(self, story):
        self.story = story
        self.frotz = dfrotz.DFrotz(Z5Bot.interpreter, self.story.path)

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