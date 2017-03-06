import json
import logging
import re
from collections import OrderedDict
from functools import wraps
from pprint import pprint
from typing import List, Dict

from telegram import ReplyKeyboardRemove

import const
from custemoji import Emoji
from telegram import ChatAction, ReplyKeyboardHide
from telegram import ParseMode
import time

from model.group import Group


def track_groups(func):
    """
    Decorator that stores all groups that the bot has been added to
    """

    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        try:
            if update.message.chat.type == 'group':
                Group.from_telegram_object(update.message.chat)
        except (NameError, AttributeError):
            try:
                if update.callback_query.message.chat.type == 'group':
                    Group.from_telegram_object(update.callback_query.message.chat)
            except (NameError, AttributeError):
                try:
                    if update.message.new_chat_member.id == const.SELF_BOT_ID:
                        Group.from_telegram_object(update.callback_query.message.chat)
                except (NameError, AttributeError):
                    logging.error("No chat_id available in update.")
        return func(bot, update, *args, **kwargs)
    return wrapped


def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        try:
            chat_id = update.message.from_user.id
        except (NameError, AttributeError):
            try:
                chat_id = update.inline_query.from_user.id
            except (NameError, AttributeError):
                try:
                    chat_id = update.chosen_inline_result.from_user.id
                except (NameError, AttributeError):
                    try:
                        chat_id = update.callback_query.from_user.id
                    except (NameError, AttributeError):
                        logging.error("No chat_id available in update.")
        if chat_id not in const.ADMINS:
            print("Unauthorized access denied for {}.".format(chat_id))
            return
        return func(bot, update, *args, **kwargs)

    return wrapped


def private_chat_only(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        if (update.message and update.message.chat.type == 'private') or (
                    update.callback_query and update.callback_query.message.chat.type == 'private'):
            return func(bot, update, *args, **kwargs)
        else:
            pass

    return wrapped


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print('%r (%r, %r) %2.2f sec' % (method.__name__, args, kw, te - ts))
        return result

    return timed


def build_menu(buttons: List,
               n_cols,
               header_buttons: List = None,
               footer_buttons: List = None):
    menu = list()
    for i in range(0, len(buttons)):
        item = buttons[i]
        if i % n_cols == 0:
            menu.append([item])
        else:
            menu[int(i / n_cols)].append(item)
    if header_buttons:
        menu.insert(0, header_buttons)
    if header_buttons:
        menu.append(footer_buttons)
    return menu


def cid_from_update(update):
    """
    Extract the chat id from update
    :param update: `telegram.Update`
    :return: chat_id extracted from the update
    """
    chat_id = None
    try:
        chat_id = update.message.chat_id
    except (NameError, AttributeError):
        try:
            chat_id = update.callback_query.message.chat_id
        except (NameError, AttributeError):
            logging.error("No chat_id available in update.")
    return chat_id


def uid_from_update(update):
    """
    Extract the user id from update
    :param update: `telegram.Update`
    :return: user_id extracted from the update
    """
    chat_id = None
    try:
        chat_id = update.message.from_user.id
    except (NameError, AttributeError):
        try:
            chat_id = update.inline_query.from_user.id
        except (NameError, AttributeError):
            try:
                chat_id = update.chosen_inline_result.from_user.id
            except (NameError, AttributeError):
                try:
                    chat_id = update.callback_query.from_user.id
                except (NameError, AttributeError):
                    logging.error("No user_id available in update.")
    return chat_id


def callback_for_action(action: object, params: object = None) -> object:
    callback_data = {'a': action}
    if params:
        for key, value in params.items():
            callback_data[key] = value
    return callback_str_from_dict(callback_data)


def callback_data_from_update(update):
    try:
        data = update.callback_query.data
        return json.loads(data)
    except:
        return {}


def is_inline_message(update):
    try:
        im_id = update.callback_query.inline_message_id
        if im_id and im_id != '':
            return True
        else:
            return False
    except (NameError, AttributeError):
        return False


def message_text_from_update(update):
    try:
        return update.message.text
    except (NameError, AttributeError):
        try:
            return update.callback_query.message.text
        except (NameError, AttributeError):
            return None


def mid_from_update(update):
    try:
        return update.callback_query.message.message_id
    except (NameError, AttributeError):
        try:
            message_id = update.callback_query.inline_message_id
            return message_id if message_id != '' else None
        except (NameError, AttributeError):
            return None


def escape_markdown(text):
    """Helper function to escape telegram markup symbols"""
    escape_chars = '\*_`\['
    return re.sub(r'([%s])' % escape_chars, r'\\\1', text)


def callback_str_from_dict(d):
    dumped = json.dumps(d, separators=(',', ':'))
    assert len(dumped) <= 64
    return dumped


def wait(bot, update, t=1.5):
    chat_id = uid_from_update(update)
    bot.sendChatAction(chat_id, ChatAction.TYPING)
    time.sleep(t)


def order_dict_lexi(d):
    res = OrderedDict()
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            res[k] = order_dict_lexi(v)
        else:
            res[k] = v
    return res


def send_or_edit_md_message(bot, chat_id, text, to_edit=None, **kwargs):
    if to_edit:
        return bot.editMessageText(text, chat_id=chat_id, message_id=to_edit, parse_mode=ParseMode.MARKDOWN,
                                   **kwargs)

    return send_md_message(bot, chat_id, text=text, **kwargs)


def send_md_message(bot, chat_id, text: str, **kwargs):
    return bot.sendMessage(chat_id, text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, **kwargs)


def send_message_success(bot, chat_id, text: str, add_punctuation=True, reply_markup=None, **kwargs):
    if add_punctuation:
        if text[-1] != '.':
            text += '.'

    if not reply_markup:
        reply_markup = ReplyKeyboardRemove()
    return bot.sendMessage(chat_id, success(text), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
                           reply_markup=reply_markup,
                           **kwargs)


def send_message_failure(bot, chat_id, text: str, **kwargs):
    text = str.strip(text)
    if text[-1] != '.':
        text += '.'
    return bot.sendMessage(chat_id, failure(text), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
                           **kwargs)


def send_action_hint(bot, chat_id, text: str, **kwargs):
    if text[-1] == '.':
        text = text[0:-1]
    return bot.sendMessage(chat_id, action_hint(text), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
                           **kwargs)


def success(text):
    return '{} {}'.format(Emoji.WHITE_HEAVY_CHECK_MARK, text, hide_keyboard=True)


def failure(text):
    return '{} {}'.format(Emoji.CROSS_MARK, text)


def action_hint(text):
    return '{} {}'.format(Emoji.THOUGHT_BALLOON, text)
