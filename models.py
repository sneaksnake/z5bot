import logging
import os

import dfrotz

class Story:
    """
    The Story class acts as a model for
    collecting metadata about the story files.
    The class is always keeping track
    of its instances.
    """

    instances = []

    def __init__(self, name, abbrev, filename):
        """
        Every Story instance is created by being
        supplied with a name (the full game title),
        an abbreviation (so the user may select it
        quickly) and a filename, respectively.
        """
        self.__class__.instances.append(self)
        self.name = name
        self.abbrev = abbrev
        self.path = os.path.join('stories', filename)

    @classmethod
    def get_instance_by_abbrev(self, abbrev):
        """
        Returns a Story instance for the associated
        abbreviation - or None.
        """
        for story in self.instances:
            if story.abbrev == abbrev:
                return story
        return None

    def __repr__(self):
        return '<Story: %s [%s]>' % (self.abbrev, self.path)

class Chat:
    """
    The Chat class acts as a model for
    keeping track of a Telegram (group) chat
    involving the bot.
    In addition, the class is always keeping track
    of its instances.
    """

    instances = []

    def __init__(self, id):
        """
        Every Chat instance is created by being
        supplied with an ID (usually just Telegram's
        chat id).
        """
        self.__class__.instances.append(self)
        self.id = id
        self.story = None
        #self.stage = 

    @classmethod
    def get_instance_or_create(self, id):
        """
        Returns a Chat instance for the given
        Telegram chat id - or creates an instance,
        if it's not existing.
        """
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
        """
        Returns True if a Story instance is
        linked to the Chat instance via
        self.set_story.
        """
        return self.story is not None

    def set_story(self, story):
        """
        Links a Story instance to the calling
        Chat instance. Implicitly runs the
        Frotz interpreter for the linked Story's
        game file.
        """
        self.story = story
        self.frotz = dfrotz.DFrotz(Z5Bot.interpreter, self.story.path)

    def __repr__(self):
        if self.story is not None:
            return '<Chat: %d, playing %r>' % (self.id, self.story.name)

        return '<Chat: %d>' % self.id

class Z5Bot:
    """
    The Z5Bot class keeps track of
    linked Chat instances and provides
    various methods for communicating
    with the game.
    """

    instances = []
    interpreter = os.path.join('tools', 'dfrotz')

    def __init__(self):
        """
        No arguments are needed for creating
        a Z5Bot instance.
        """
        self.__class__.instances.append(self)
        self.broadcasted = False
        self.chats = []
        self.parser = None
        self.redis = None

    @classmethod
    def get_instance_or_create(self):
        """
        Returns a Z5Bot instance if there's already
        an active one. Else, the class will create
        one.
        """
        if len(self.instances) > 0:
            instance = self.instances[0]
            logging.debug('Using %r!' % instance)
        else:
            instance = Z5Bot()
            logging.debug('Created new Z5Bot instance!')
        return instance

    def add_parser(self, parser):
        """
        Links a parser.Parser instance
        to the calling Z5Bot instance.
        """
        self.parser = parser

    def add_redis(self, redis):
        """
        Links a redis-py instance to the
        calling Z5Bot instance.
        """
        self.redis = redis

    def add_chat(self, new_chat):
        """
        Links a Chat instance to the calling
        Z5Bot instance.
        """
        for chat in self.chats:
            if chat.id == new_chat.id:
                self.chats.remove(chat)
        self.chats.append(new_chat)

    def get_chat_by_id(self, id):
        """
        Returns a Chat instance for the given
        Telegram chat id - or None if there
        is no matching Chat instance.
        """
        for chat in self.chats:
            if chat.id == id:
                return chat
        else:
            return None

    def process(self, id, command):
        """
        Takes user input and redirects it
        to the Frotz interpreter.
        """
        self.chat = self.get_chat_by_id(id)
        self.chat.frotz.send('%s\r\n' % command)

    def receive(self, id):
        """
        Returns Frotz' buffered output.
        """
        self.chat = self.get_chat_by_id(id)
        return self.chat.frotz.get()

    def __repr__(self):
        return '<Z5Bot, %d chats>' % len(self.chats)
