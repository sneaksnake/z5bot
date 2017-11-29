import json
import logging
import os
import sys
import time

import telegram.ext

from dfrotz import DFrotz
import models
import parser

logging.basicConfig(
    format='[%(asctime)s-%(name)s-%(levelname)s]\n%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
)
logging.getLogger('telegram').setLevel(logging.WARNING)

def log_dialog(in_message, out_message):
    logging.info('@%s[%d] sent: %r' % (
        in_message.from_user.username,
        in_message.from_user.id,
        in_message.text[:40])
    )
    logging.info('Answering @%s[%d]: %r' % (
        in_message.from_user.username,
        in_message.from_user.id,
        out_message.text[:40] if out_message is not None else '[None]')
    )

def on_error(bot, update, error):
    logger = logging.getLogger(__name__)
    logger.warn('Update %r caused error %r!' % (update, error))
    print(error)

def cmd_default(bot, message, z5bot, chat):
    # gameplay messages will be sent here
    if message.text.strip().lower() == 'load':
        text = 'Please use /load.'
        return bot.sendMessage(message.chat_id, text)

    if message.text.strip().lower() == 'save':
        text = 'Your progress is being saved automatically. But /load is available.'
        return bot.sendMessage(message.chat_id, text)

    if not chat.has_story():
        text = 'Please use the /select command to select a game.'
        return bot.sendMessage(message.chat_id, text)

    # here, stuff is sent to the interpreter
    z5bot.process(message.chat_id, message.text)

    received = z5bot.receive(message.chat_id)
    reply = bot.sendMessage(message.chat_id, received)
    log_dialog(message, reply)

    if ' return ' in received.lower() or ' enter ' in received.lower():
        notice = '(Note: You are able to do use the return key by typing /enter.)'
        return bot.sendMessage(message.chat_id, notice)

def cmd_start(bot, message, *args):
    text =  'Welcome, %s!\n' % message.from_user.first_name
    text += 'Please use the /select command to select a game.\n'
    return bot.sendMessage(message.chat_id, text)

def cmd_select(bot, message, z5bot, chat):
    selection = 'For "%s", write /select %s.'
    msg_parts = []
    for story in models.Story.instances:
        part = selection % (story.name, story.abbrev)
        msg_parts.append(part)
    text = '\n'.join(msg_parts)

    for story in models.Story.instances:
        if ' ' in message.text and message.text.strip().lower().split(' ')[1] == story.abbrev:
            chat.set_story(models.Story.get_instance_by_abbrev(story.abbrev))
            z5bot.add_chat(chat)
            reply = bot.sendMessage(message.chat_id, 'Starting "%s"...' % story.name)
            log_dialog(message, reply)
            notice  = 'Your progress will be saved automatically.'
            reply = bot.sendMessage(message.chat_id, notice)
            log_dialog(message, reply)
            reply = bot.sendMessage(message.chat_id, z5bot.receive(message.chat_id))
            log_dialog(message, reply)
            return

    return bot.sendMessage(message.chat_id, text)

def cmd_load(bot, message, z5bot, chat):
    if not chat.has_story():
        text = 'You have to select a game first.'
        return bot.sendMessage(message.chat_id, text)

    return bot.sendMessage(message.chat_id, "This is a stub.")


def cmd_clear(bot, message, z5bot, chat):
    return bot.sendMessage(message.chat_id, "This is a stub.")

def cmd_enter(bot, message, z5bot, chat):
    if not chat.has_story():
        return

    command = '' # \r\n is automatically added by the Frotz abstraction layer
    z5bot.process(message.chat_id, command)
    return bot.sendMessage(message.chat_id, z5bot.receive(message.chat_id))

def cmd_ignore(*args):
    return

def cmd_ping(bot, message, *args):
    return bot.sendMessage(message.chat_id, 'Pong!')


def on_message(bot, update):
    message = update.message
    z5bot = models.Z5Bot.get_instance_or_create()
    func = z5bot.parser.get_function(message.text)
    chat = models.Chat.get_instance_or_create(message.chat_id)

    out_message = func(bot, message, z5bot, chat)

    log_dialog(message, out_message)

if __name__ == '__main__':
    with open('config.json', 'r') as f:
        config = json.load(f)

    api_key = config['api_key']
    logging.info('Logging in with api key %r.' % api_key)
    if len(sys.argv) > 1:
        logging.info('Broadcasting is available! Send /broadcast.')

    for story in config['stories']:
        models.Story(
            name=story['name'],
            abbrev=story['abbrev'],
            filename=story['filename']
        )

    z5bot = models.Z5Bot.get_instance_or_create()

    p = parser.Parser()
    p.add_default(cmd_default)
    p.add_command('/start', cmd_start)
    p.add_command('/select', cmd_select)
    p.add_command('/load', cmd_load)
    p.add_command('/clear', cmd_clear)
    p.add_command('/enter', cmd_enter)
    p.add_command('/i', cmd_ignore)
    p.add_command('/ping', cmd_ping)
    z5bot.add_parser(p)


    updater = telegram.ext.Updater(api_key)
    dispatcher = updater.dispatcher
    # Make sure the user's messages get redirected to our parser,
    # with or without a slash in front of them.
    dispatcher.add_handler(telegram.ext.MessageHandler(filters=[], callback=on_message))
    dispatcher.add_error_handler(callback=on_error)
    updater.start_polling()
