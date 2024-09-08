from random import randint

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, CallbackContext, CallbackQueryHandler, CommandHandler, \
    ContextTypes

import json
import pickle
import config
from threading import Lock

lock = Lock()


class User:
    def __init__(self, user_id, current_state):
        self.user_id = user_id
        self.current_state = current_state
        self.dogs_to_sell = 0
        self.tons_to_buy = 0
        self.ref_of = ''
        self.balance = 0
        self.rand_num = 0
        self.first_review = False

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'current_state': self.current_state,
            'dogs_to_sell': self.dogs_to_sell,
            'tons_to_buy': self.tons_to_buy,
            'ref_of': self.ref_of,
            'balance': self.balance,
            'first_review': self.first_review
        }


def load_file(f) -> list:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            return list(json.load(file))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_bot_values(file_path='bot_values.json'):
    with open(file_path, 'r') as file:
        bot_values = json.load(file)
    return bot_values


def save_bot_values(bot_values, file_path='bot_values.json'):
    with open(file_path, 'w') as file:
        json.dump(bot_values, file, indent=4)


def save(users_to_save):
    with lock:
        with open('users.pkl', 'wb') as pkl_file:
            pickle.dump(users_to_save, pkl_file)


def load():
    with lock:
        with open('users.pkl', 'rb') as pkl_file:
            loaded_users = pickle.load(pkl_file)
            return loaded_users


# users = {}
users = load()


async def cancel_dogs(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    rand = job.data[0]
    global users
    num_to_check = users[job.data[1]].rand_num
    if num_to_check == rand:
        users[job.data[1]].dogs_to_sell = 0
        users[job.data[1]].current_state = 'started'
        if users[job.data[1]].rand_num != 0:
            await context.bot.send_animation(chat_id=job.data[1], animation='animations/forgot_dogs.mp4',
                                             caption='Вы забыли продолжить продажу DOGS. Выбери \"Продать DOGS\" снова и следуй указаниям от бота')


async def check(update: Update, context: CallbackContext):
    admins = load_file('admins.json')

    if update.effective_chat.id in admins:
        bot_values = load_bot_values()
        text = ''
        for i in bot_values.keys():
            s = f"{i} = {bot_values[i]}\n"
            text += s
        await context.bot.send_message(update.effective_chat.id, text=text, disable_web_page_preview=True)


async def start(update: Update, context: CallbackContext):
    bot_values = load_bot_values()
    is_in_grp = await context.bot.get_chat_member(chat_id=bot_values["group"], user_id=update.effective_message.chat_id)
    if is_in_grp.status in ['member', 'creator', 'administrator']:
        keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                    [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                    [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]
        if update.effective_chat.id not in users:
            users[update.effective_chat.id] = User(update.effective_chat.id, 'started')
            ref_id = update.message.text[7:]
            if not ref_id == '':
                users[update.effective_chat.id].ref_of = int(ref_id)
        else:
            users[update.effective_chat.id].current_state = 'started'
            save(users)
        await context.bot.send_message(update.effective_chat.id,
                                       text=f"Привет. Вы попали в обменник валюты \"DOGS\". Наша команда занимается помощью в продаже вашей валюты. В меню выберите услугу, которая вас интересует. \n\nОтзывы: [тут]({bot_values['link_for_reviews']})",
                                       reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                        one_time_keyboard=True),
                                       parse_mode=ParseMode.MARKDOWN)
    else:
        if update.effective_chat.id not in users:
            users[update.effective_chat.id] = User(update.effective_chat.id, 'not started')
            ref_id = update.message.text[7:]
            if not ref_id == '':
                users[update.effective_chat.id].ref_of = int(ref_id)
        else:
            users[update.effective_chat.id].current_state = 'not started'
            save(users)
        keyboard = [[InlineKeyboardButton("Подписаться", url=bot_values['link_for_group'])]]
        await context.bot.send_message(update.effective_chat.id,
                                       text="Вы должны быть подписаны на наш Telegram канал для связи",
                                       reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_private_messages(update: Update, context: CallbackContext):
    text = update.message.text
    bot_values = load_bot_values()
    if users[update.effective_chat.id].current_state == 'not started':
        keyboard = [[InlineKeyboardButton("Подписаться", url=bot_values['link_for_group'])]]
        await context.bot.send_message(update.effective_chat.id,
                                       text="Вы должны быть подписаны на наш Telegram канал для связи",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
        return 0
    if update.message.text and update.effective_chat.id in [5276000599, 836446595, 506712122] and text.count('=') == 1:
        replaced_text = update.message.text.replace(' ', '')
        delimeter = replaced_text.find("=")
        key = replaced_text[0:delimeter]
        if key in bot_values.keys():
            bot_values[key] = replaced_text[delimeter + 1:]
            save_bot_values(bot_values)
            await context.bot.send_message(update.effective_chat.id, text="Успешно изменено!")
        else:
            await context.bot.send_message(update.effective_chat.id, text="Где-то ошибка")

    if users[update.effective_chat.id].current_state == 'send_screen':
        if not update.message.document and not update.message.video and not update.message.photo:
            keyboard = []
            admins = load_file('admins.json')
            for i in admins:
                try:
                    keyboard.append(
                        [InlineKeyboardButton(f"Связаться с менеджером {admins.index(i) + 1}",
                                              url=f"tg://user?id={i}")])
                except Exception as e:
                    print(e)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Предоставьте сначала скриншот\\запись перевода DOGS. Если потеряли наличие доказательств перевода, свяжитесь с менеджером.',
                                           reply_markup=InlineKeyboardMarkup(keyboard))
            return 0

    if users[update.effective_chat.id].current_state == 'input_dogs':
        if text.isdigit() and float(text) > 0:
            users[update.effective_chat.id].dogs_to_sell = float(text)
            users[update.effective_chat.id].current_state = 'confirm_dogs'
            keyboard = [[KeyboardButton("Подтвердить")]]
            await update.message.reply_text(
                f"🧐 Вы уверены, что хотите продать *{text} DOGS*?\n(убедитесь, что вводите верное число!)",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
                parse_mode=ParseMode.MARKDOWN)
            num = randint(1, 99999)
            users[update.effective_chat.id].rand_num = num if users[update.effective_chat.id].rand_num != num else \
                users[update.effective_chat.id].rand_num + randint(1, 99999)

            context.job_queue.run_once(cancel_dogs, 10 * 60, chat_id=update.effective_chat.id,
                                       data=[users[update.effective_chat.id].rand_num, update.effective_chat.id])

        else:
            await update.message.reply_text(f"Предоставьте число")

    elif users[update.effective_chat.id].current_state == 'leave first comment':
        if text == "Не оставлять отзыв":
            keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                        [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                        [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]
            users[update.effective_chat.id].current_state = 'started'
            await context.bot.send_message(update.effective_chat.id,
                                           text=f"Привет. Вы попали в обменник валюты \"DOGS\". Наша команда занимается помощью в продаже вашей валюты. В меню выберите услугу, которая вас интересует. \n\nОтзывы: [тут]({bot_values['link_for_reviews']})",
                                           reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                            one_time_keyboard=True),
                                           parse_mode=ParseMode.MARKDOWN)
        else:
            id = update.effective_chat.id
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")],
                        [InlineKeyboardButton("✅", callback_data=f"yes to first|{id}"),
                         InlineKeyboardButton("❌", callback_data=f"no to first|{id}")]]

            keyboard = InlineKeyboardMarkup(keyboard)
            print(update.effective_chat.id)

            msg = update.message
            if msg.document:
                fileID = msg.document.file_id
                if msg.caption:
                    await context.bot.send_document(bot_values["chat_2"], document=fileID,
                                                    reply_markup=keyboard,
                                                    caption=msg.caption)
                else:
                    await context.bot.send_document(bot_values["chat_2"], document=fileID,
                                                    reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))
                users[update.effective_chat.id].current_state = 'sent_comment'

            elif msg.photo:

                fileID = msg.photo[-1].file_id
                if msg.caption:
                    await context.bot.send_photo(bot_values["chat_2"], photo=fileID, reply_markup=keyboard,
                                                 caption=msg.caption)
                else:
                    await context.bot.send_photo(bot_values["chat_2"], photo=fileID, reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))
                users[update.effective_chat.id].current_state = 'sent_comment'


            elif msg.video:
                fileID = msg.video.file_id
                if msg.caption:
                    await context.bot.send_video(bot_values["chat_2"], video=fileID, reply_markup=keyboard,
                                                 caption=msg.caption)

                else:
                    await context.bot.send_video(bot_values["chat_2"], video=fileID, reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))

                users[update.effective_chat.id].current_state = 'sent_comment'
            elif msg.text:
                await context.bot.send_message(bot_values["chat_2"], text=msg.text, reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))

                users[update.effective_chat.id].current_state = 'sent_comment'
            elif msg.voice:
                await context.bot.send_voice(bot_values["chat_2"], voice=msg.voice, reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))

                users[update.effective_chat.id].current_state = 'sent_comment'
            elif msg.video_note:
                await context.bot.send_video_note(bot_values["chat_2"], video_note=msg.video_note,
                                                  reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))

                users[update.effective_chat.id].current_state = 'sent_comment'
            users[update.effective_chat.id].first_review = True



    elif users[update.effective_chat.id].current_state == 'leave comment':
        if text == "Не оставлять отзыв":
            keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                        [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                        [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]
            users[update.effective_chat.id].current_state = 'started'
            await context.bot.send_message(update.effective_chat.id,
                                           text=f"Привет. Вы попали в обменник валюты \"DOGS\". Наша команда занимается помощью в продаже вашей валюты. В меню выберите услугу, которая вас интересует. \n\nОтзывы: [тут]({bot_values['link_for_reviews']})",
                                           reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                            one_time_keyboard=True),
                                           parse_mode=ParseMode.MARKDOWN)
        else:
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={update.effective_chat.id}")]]
            keyboard = InlineKeyboardMarkup(keyboard)
            msg = update.message
            if msg.document:
                fileID = msg.document.file_id
                if msg.caption:
                    await context.bot.send_document(bot_values["chat_2"], document=fileID,
                                                    reply_markup=keyboard,
                                                    caption=msg.caption)
                else:
                    await context.bot.send_document(bot_values["chat_2"], document=fileID,
                                                    reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))
                users[update.effective_chat.id].current_state = 'sent_comment'

            elif msg.photo:

                fileID = msg.photo[-1].file_id
                if msg.caption:
                    await context.bot.send_photo(bot_values["chat_2"], photo=fileID, reply_markup=keyboard,
                                                 caption=msg.caption)
                else:
                    await context.bot.send_photo(bot_values["chat_2"], photo=fileID, reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))
                users[update.effective_chat.id].current_state = 'sent_comment'


            elif msg.video:
                fileID = msg.video.file_id
                if msg.caption:
                    await context.bot.send_video(bot_values["chat_2"], video=fileID, reply_markup=keyboard,
                                                 caption=msg.caption)

                else:
                    await context.bot.send_video(bot_values["chat_2"], video=fileID, reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))

                users[update.effective_chat.id].current_state = 'sent_comment'
            elif msg.text:
                await context.bot.send_message(bot_values["chat_2"], text=msg.text, reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))

                users[update.effective_chat.id].current_state = 'sent_comment'
            elif msg.voice:
                await context.bot.send_voice(bot_values["chat_2"], voice=msg.voice, reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))

                users[update.effective_chat.id].current_state = 'sent_comment'
            elif msg.video_note:
                await context.bot.send_video_note(bot_values["chat_2"], video_note=msg.video_note,
                                                  reply_markup=keyboard)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Сообщение отправлено!',
                                               reply_markup=InlineKeyboardMarkup(
                                                   [[InlineKeyboardButton('Перейти к началу',
                                                                          callback_data='go to begin')]]))

                users[update.effective_chat.id].current_state = 'sent_comment'

    elif users[update.effective_chat.id].current_state == 'cancel and send comment':
        keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={update.effective_chat.id}")]]
        keyboard = InlineKeyboardMarkup(keyboard)
        msg = update.message
        if msg.document:
            fileID = msg.document.file_id
            if msg.caption:
                await context.bot.send_document(bot_values["chat_3"], document=fileID,
                                                reply_markup=keyboard,
                                                caption=msg.caption)
            else:
                await context.bot.send_document(bot_values["chat_3"], document=fileID,
                                                reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))
            users[update.effective_chat.id].current_state = 'commented'

        elif msg.photo:

            fileID = msg.photo[-1].file_id
            if msg.caption:
                await context.bot.send_photo(bot_values["chat_3"], photo=fileID, reply_markup=keyboard,
                                             caption=msg.caption)
            else:
                await context.bot.send_photo(bot_values["chat_3"], photo=fileID, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))
            users[update.effective_chat.id].current_state = 'commented'


        elif msg.video:
            fileID = msg.video.file_id
            if msg.caption:
                await context.bot.send_video(bot_values["chat_3"], video=fileID, reply_markup=keyboard,
                                             caption=msg.caption)

            else:
                await context.bot.send_video(bot_values["chat_3"], video=fileID, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'commented'
        elif msg.text:
            await context.bot.send_message(bot_values["chat_3"], text=msg.text, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'commented'
        elif msg.voice:
            await context.bot.send_voice(bot_values["chat_3"], voice=msg.voice, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'commented'
        elif msg.video_note:
            await context.bot.send_video_note(bot_values["chat_3"], video_note=msg.video_note, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'commented'

    elif users[update.effective_chat.id].current_state == 'buy_ton':
        keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={update.effective_chat.id}")]]
        keyboard = InlineKeyboardMarkup(keyboard)
        print(update.effective_chat.id)
        msg = update.message
        if msg.document:
            fileID = msg.document.file_id
            if msg.caption:
                await context.bot.send_document(bot_values["chat_2"], document=fileID,
                                                reply_markup=keyboard,
                                                caption=msg.caption)
            else:
                await context.bot.send_document(bot_values["chat_2"], document=fileID,
                                                reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))
            users[update.effective_chat.id].current_state = 'bought_ton'

        elif msg.photo:

            fileID = msg.photo[-1].file_id
            if msg.caption:
                await context.bot.send_photo(bot_values["chat_2"], photo=fileID, reply_markup=keyboard,
                                             caption=msg.caption)
            else:
                await context.bot.send_photo(bot_values["chat_2"], photo=fileID, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))
            users[update.effective_chat.id].current_state = 'bought_ton'


        elif msg.video:
            fileID = msg.video.file_id
            if msg.caption:
                await context.bot.send_video(bot_values["chat_2"], video=fileID, reply_markup=keyboard,
                                             caption=msg.caption)

            else:
                await context.bot.send_video(bot_values["chat_2"], video=fileID, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'bought_ton'
        elif msg.text:
            await context.bot.send_message(bot_values["chat_2"], text=msg.text, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'bought_ton'
        elif msg.voice:
            await context.bot.send_voice(bot_values["chat_2"], voice=msg.voice, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'bought_ton'
        elif msg.video_note:
            await context.bot.send_video_note(bot_values["chat_2"], video_note=msg.video_note, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'bought_ton'


    elif users[update.effective_chat.id].current_state == 'help of manager':
        keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={update.effective_chat.id}")]]
        keyboard = InlineKeyboardMarkup(keyboard)
        msg = update.message
        if msg.document:
            fileID = msg.document.file_id
            if msg.caption:
                await context.bot.send_document(bot_values["chat_2"], document=fileID,
                                                reply_markup=keyboard,
                                                caption=msg.caption)
            else:
                await context.bot.send_document(bot_values["chat_2"], document=fileID,
                                                reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))
            users[update.effective_chat.id].current_state = 'confirmed_dogs'

        elif msg.photo:

            fileID = msg.photo[-1].file_id
            if msg.caption:
                await context.bot.send_photo(bot_values["chat_2"], photo=fileID, reply_markup=keyboard,
                                             caption=msg.caption)
            else:
                await context.bot.send_photo(bot_values["chat_2"], photo=fileID, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))
            users[update.effective_chat.id].current_state = 'confirmed_dogs'


        elif msg.video:
            fileID = msg.video.file_id
            if msg.caption:
                await context.bot.send_video(bot_values["chat_2"], video=fileID, reply_markup=keyboard,
                                             caption=msg.caption)

            else:
                await context.bot.send_video(bot_values["chat_2"], video=fileID, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'confirmed_dogs'
        elif msg.text:
            await context.bot.send_message(bot_values["chat_2"], text=msg.text, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'confirmed_dogs'
        elif msg.voice:
            await context.bot.send_voice(bot_values["chat_2"], voice=msg.voice, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'confirmed_dogs'
        elif msg.video_note:
            await context.bot.send_video_note(bot_values["chat_2"], video_note=msg.video_note, reply_markup=keyboard)
            await context.bot.send_message(update.effective_chat.id,
                                           text='Сообщение отправлено!',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'confirmed_dogs'



    elif users[update.effective_chat.id].current_state == 'confirm_dogs':

        users[update.effective_chat.id].current_state = 'confirmed_dogs'
        current_price = "{:.4f}".format(1 / float(bot_values['DOGS'])).rstrip('0').rstrip('.')
        formatted_number = "{:.4f}".format(
            float(users[update.effective_chat.id].dogs_to_sell) / float(current_price)).rstrip('0').rstrip('.')
        keyboard = [[KeyboardButton("Продать")]]
        await update.message.reply_animation(animation='animations/currency.mp4',
                                             caption=f"⚡️ По курсу: *1 USDT = {current_price} DOGS*\n💎 Получается, что ваши *{users[update.effective_chat.id].dogs_to_sell} DOGS* это *{formatted_number} USDT*\n\n(курс DOGS меняется каждые 2 часа)",
                                             parse_mode=ParseMode.MARKDOWN,
                                             reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                              one_time_keyboard=True))

    elif users[update.effective_chat.id].current_state == 'send_screen':
        msg = update.message
        keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={update.effective_chat.id}")], [
            InlineKeyboardButton("Одобрить платеж", callback_data=f'confirm_payment|{update.effective_chat.id}')]]
        keyboard = InlineKeyboardMarkup(keyboard)
        if msg.document:
            fileID = msg.document.file_id
            if msg.caption:
                await context.bot.send_document(bot_values["chat_1"], document=fileID,
                                                reply_markup=keyboard,
                                                caption=msg.caption + f'\n\nОтправил {users[update.effective_chat.id].dogs_to_sell} DOGS')
            else:
                await context.bot.send_document(bot_values["chat_1"], document=fileID,
                                                reply_markup=keyboard,
                                                caption=f'\n\nОтправил {users[update.effective_chat.id].dogs_to_sell} DOGS')
            await context.bot.send_message(update.effective_chat.id,
                                           text='Всё супер. Проверяем актуальность перевода, это занимает обычно от 10 минут до 24 часов.\n\nЕсли в течении 24 часов перевод не будет совершён, свяжитесь, пожалуйста с нами, для выяснения обстоятельств',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Помощь менеджера',
                                                                                                    callback_data='help of manager')],
                                                                              [InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))
            users[update.effective_chat.id].current_state = 'confirmed_dogs'


        elif msg.photo:
            fileID = msg.photo[-1].file_id
            if msg.caption:
                await context.bot.send_photo(bot_values["chat_1"], photo=fileID, reply_markup=keyboard,
                                             caption=msg.caption + f'\n\nОтправил {users[update.effective_chat.id].dogs_to_sell} DOGS')
            else:
                await context.bot.send_photo(bot_values["chat_1"], photo=fileID, reply_markup=keyboard,
                                             caption=f'\n\nОтправил {users[update.effective_chat.id].dogs_to_sell} DOGS')
            await context.bot.send_message(update.effective_chat.id,
                                           text='Всё супер. Проверяем актуальность перевода, это занимает обычно от 10 минут до 24 часов.\n\nЕсли в течении 24 часов перевод не будет совершён, свяжитесь, пожалуйста с нами, для выяснения обстоятельств',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Помощь менеджера',
                                                                                                    callback_data='help of manager')],
                                                                              [InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))

            users[update.effective_chat.id].current_state = 'confirmed_dogs'




        elif msg.video:
            fileID = msg.video.file_id
            if msg.caption:
                await context.bot.send_video(bot_values["chat_1"], video=fileID, reply_markup=keyboard,
                                             caption=msg.caption + f'\n\nОтправил {users[update.effective_chat.id].dogs_to_sell} DOGS')

            else:
                await context.bot.send_video(bot_values["chat_1"], video=fileID, reply_markup=keyboard,
                                             caption=f'\n\nОтправил {users[update.effective_chat.id].dogs_to_sell} ODGS')
            await context.bot.send_message(update.effective_chat.id,
                                           text='Всё супер. Проверяем актуальность перевода, это занимает обычно от 10 минут до 24 часов.\n\nЕсли в течении 24 часов перевод не будет совершён, свяжитесь, пожалуйста с нами, для выяснения обстоятельств',
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Помощь менеджера',
                                                                                                    callback_data='help of manager')],
                                                                              [InlineKeyboardButton('Перейти к началу',
                                                                                                    callback_data='go to begin')]]))
            users[update.effective_chat.id].current_state = 'confirmed_dogs'



        else:
            await update.message.reply_text('Предоставьте скриншот/запись перевода')

        save(users)

    if text == "Продать DOGS":
        await update.message.reply_text(
            "🤑 *Напишите количество DOGS, которые вы хотите продать.*\n Укажите точное число.",
            parse_mode=ParseMode.MARKDOWN)
        users[update.effective_chat.id].current_state = 'input_dogs'
    elif text == "Да, я уверен":
        keyboard = [[KeyboardButton("Сделал перевод по инструкции")]]
        await context.bot.send_animation(chat_id=update.effective_chat.id, animation='animations/okay_continue.mp4',
                                         caption=f"*Хорошо, тогда продолжим.*\nСкидываю вам реквизит, куда кидать свои DOGS\n\n⚠️Обязательно сделайте *скриншот/запись перевода.* Вы должны *совершить перевод в течении часа*, иначе сделка будет отменена и ваше место займут другие! \n\nЕсли нужно, то вот инструкция перевода DOGS: {bot_values["link_for_telegraph"]}\n\n\nАдрес:\nEQDD8dqOzaj4zUK6ziJOo_G2lx6qf1TEktTRkFJ7T1c_fPQb\nОбязательный комментарий:\n10146109",
                                         reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                          one_time_keyboard=True),
                                         parse_mode=ParseMode.MARKDOWN)

    elif text == "Нет, у меня нет TON":
        keyboard = [[KeyboardButton("Взять TON в займ")]]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='К сожалению, TON обязателен для оплаты комиссии. Комиссия небольшая, это условная формальность. Вам вернут деньги вместе с DOGS\n\nПредлагаем вам взять TON у нас в займ, *бесплатно*',
                                       parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                        one_time_keyboard=True))

    elif text == "Взять TON в займ":
        keyboard = [[KeyboardButton("У меня бан в Telegram"), KeyboardButton("Перейти к началу")]]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Для того, чтобы взять TON, отпишите нашему менеджеру в личные сообщения:\n@dogscoin_sell\n@dogscoin_sell\n@dogscoin_sell\n\n(прошу писать по делу, одним сообщением, чтобы не создавать нагрузку и спам. Спасибо за понимание! Мы стараемся улучшить наш сервис и делать всё быстро и качественно)',
                                       reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                        one_time_keyboard=True))

    elif text == 'Вывести баланс':
        if float(users[update.effective_chat.id].balance) >= float(bot_values['min_balance']):
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={update.effective_chat.id}")], [
                InlineKeyboardButton("Одобрить платеж", callback_data=f'confirm_balance|{update.effective_chat.id}')]]
            await context.bot.send_message(chat_id=bot_values["chat_1"],
                                           text=f'Юзер желает вывести баланс ({users[update.effective_chat.id].balance}$)',
                                           reply_markup=InlineKeyboardMarkup(keyboard))
            users[update.effective_chat.id].balance = 0
            save(users)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Запрос на вывод отправлен!")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"Деньги можно выводить только имея на балансе больше {bot_values['min_balance']}$")


    elif text == "Мой Баланс":
        keyboard = [[KeyboardButton("Вывести баланс"), KeyboardButton("Подключить рефералов")],
                    [KeyboardButton("Перейти к началу")]]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Текущий баланс от рефералов: {users[update.effective_chat.id].balance}$",
                                       reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                        one_time_keyboard=True))

    elif text == "У меня бан в Telegram":
        keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                    [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                    [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Мы вас услышали, соответствующее сообщение было отправлено менеджеру. Добавьте его в контакты и ждите, пока вам напишут первыми!\n@dogscoin_sell',
                                       reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                        one_time_keyboard=True))

    elif text == "Перейти к началу":
        users[update.effective_chat.id].current_state = 'started'
        keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                    [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                    [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]
        await context.bot.send_message(update.effective_chat.id,
                                       text=f"Привет. Вы попали в обменник валюты \"DOGS\". Наша команда занимается помощью в продаже вашей валюты. В меню выберите услугу, которая вас интересует. \n\nОтзывы: [тут]({bot_values['link_for_reviews']})",
                                       reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                        one_time_keyboard=True),
                                       parse_mode=ParseMode.MARKDOWN)

    elif text == "Подключить рефералов":
        me = await context.bot.get_me()
        keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                    [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                    [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]

        await context.bot.send_message(update.effective_chat.id,
                                       text=f"💸 Зарабатывай 10% от суммы сделки твоего друга! \nПодключай рефералов по своей уникальной ссылке: \n\nhttps://t.me/{me.username}?start={update.effective_message.chat_id}",
                                       reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True,
                                                                        resize_keyboard=True))

    elif text == "Отменить сделку":
        if float(users[update.effective_chat.id].dogs_to_sell) > 0:
            current_price = "{:.4f}".format(1 / float(bot_values['DOGS'])).rstrip('0').rstrip('.')
            formatted_number = "{:.4f}".format(
                float(users[update.effective_chat.id].dogs_to_sell) / float(current_price)).rstrip('0').rstrip('.')
            keyboard = [[KeyboardButton("Продолжить сделку"), KeyboardButton("Отменить сделку!")]]
            await context.bot.send_message(update.effective_chat.id,
                                           text=f"Вы уверены, что хотите потерять {formatted_number} USDT? \n\nСегодня лучшая возможность продать DOGS по лучшей цене. Обдумайте решение ещё раз",
                                           reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                            one_time_keyboard=True),
                                           parse_mode=ParseMode.MARKDOWN)
    elif text == "Отменить сделку!":
        if float(users[update.effective_chat.id].dogs_to_sell) > 0:
            users[update.effective_chat.id].dogs_to_sell = 0
            users[update.effective_chat.id].rand_num = 0
            keyboard = [[InlineKeyboardButton("Не оставлять отзыв", callback_data="no comment")]]
            await context.bot.send_message(update.effective_chat.id,
                                           text='Расскажите, пожалуйста, вкратце, почему вы решили отменить сделку?\n\nВаш отзыв очень поможет улучшить нам наш сервис! Спасибо!',
                                           reply_markup=InlineKeyboardMarkup(keyboard))
            users[update.effective_chat.id].current_state = 'cancel and send comment'
    elif text == "Продолжить сделку":
        if float(users[update.effective_chat.id].dogs_to_sell) > 0:
            keyboard = [[KeyboardButton("Сделал перевод по инструкции")]]
            await context.bot.send_animation(chat_id=update.effective_chat.id, animation='animations/okay_continue.mp4',
                                             caption=f"*Хорошо, тогда продолжим.*\nСкидываю вам реквизит, куда кидать свои DOGS\n\n⚠️Обязательно сделайте *скриншот/запись перевода.* Вы должны *совершить перевод в течении часа*, иначе сделка будет отменена и ваше место займут другие! \n\nЕсли нужно, то вот инструкция перевода DOGS: https://example/com\n\n\nАдрес:\nEQDD8dqOzaj4zUK6ziJOo_G2lx6qf1TEktTRkFJ7T1c_fPQb\nОбязательный комментарий:\n10146109",
                                             reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                              one_time_keyboard=True),
                                             parse_mode=ParseMode.MARKDOWN)


    elif text == '+40':
        users[update.effective_chat.id].balance += 40

    elif text == "Сделал перевод по инструкции":
        if float(users[update.effective_chat.id].dogs_to_sell) > 0:
            users[update.effective_chat.id].current_state = 'send_screen'
            await context.bot.send_message(update.effective_chat.id,
                                           text=f"Отлично, вроде бы вижу какой-то перевод, но от вас ли он?\n\nПрикрепите, пожалуйста, доказательства перевода в виде скриншота/записи",
                                           parse_mode=ParseMode.MARKDOWN)

    elif text == "Продать":
        if float(users[update.effective_chat.id].dogs_to_sell) > 0:
            current_price = "{:.4f}".format(1 / float(bot_values['DOGS'])).rstrip('0').rstrip('.')
            formatted_number = "{:.4f}".format(
                float(users[update.effective_chat.id].dogs_to_sell) / float(current_price)).rstrip('0').rstrip('.')
            keyboard = [[KeyboardButton("Да, я уверен"), KeyboardButton("Нет, у меня нет TON")],
                        [KeyboardButton("Отменить сделку")]]
            await context.bot.send_message(update.effective_chat.id,
                                           text=f"Отлично. Для продажи вам нужно перевести все указанные ранее DOGS на эти реквизиты по сети \"TON\". \n\n*Вы уверены, что хотите продать {users[update.effective_chat.id].dogs_to_sell} DOGS и получить {formatted_number} USDT?*\n\nПримечение: (У вас на балансе должно быть хоть какое-то количество TON для перевода)",
                                           reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                            one_time_keyboard=True),
                                           parse_mode=ParseMode.MARKDOWN)


    elif text == "Купить TON":
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Отлично! Отпишите, сколько вы хотите купить TON, с вами свяжутся наши менеджеры')
        users[update.effective_chat.id].current_state = 'buy_ton'


    elif text == "Помощь менеджера":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data='cancel_to_start')]])
        await context.bot.send_animation(chat_id=update.effective_chat.id, animation='animations/tell_us.mp4',
                                         caption='🖖 Опишите, *пожалуйста, суть обращения*, чтобы мы могли среагировать *быстрее и перейти скорее к решению вашего вопроса*, тем самым это позволит ускорить процесс нашего сервиса! ⏳',
                                         reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

        users[update.effective_chat.id].current_state = 'leave comment'

    elif text == "Оставить отзыв":
        keyboard = [[KeyboardButton("Не оставлять отзыв")]]
        if not users[update.effective_chat.id].first_review:
            await context.bot.send_animation(chat_id=update.effective_chat.id, animation='animations/first_review.mp4',
                                             caption='🌟 *Оставьте отзыв* - получите копеечку в подарок 💸',
                                             parse_mode=ParseMode.MARKDOWN,
                                             reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True,
                                                                              resize_keyboard=True))
            users[update.effective_chat.id].current_state = 'leave first comment'

        else:
            await context.bot.send_animation(chat_id=update.effective_chat.id, animation='animations/tell_us.mp4',
                                             caption='Оставьте отзыв по поводу нашего сервиса! Будем рады услышать вас!',
                                             reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True,
                                                                              resize_keyboard=True))
            users[update.effective_chat.id].current_state = 'leave comment'


async def handle_buttons(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    bot_values = load_bot_values()

    await query.answer()
    if str(query.message.chat.id) in [bot_values["chat_1"], bot_values["chat_2"], bot_values["chat_3"]]:
        if 'confirm_payment' in query.data:
            id = int(query.data.split('|', maxsplit=1)[1])
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")],
                        [InlineKeyboardButton("✅", callback_data=f'confirm|{id}'),
                         InlineKeyboardButton("❌", callback_data=f'decline|{id}')]]
            await context.bot.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard),
                                                        message_id=query.message.message_id,
                                                        chat_id=query.message.chat.id)

        elif 'confirm' in query.data and 'confirm_payment' not in query.data and 'balance' not in query.data:
            id = int(query.data.split('|', maxsplit=1)[1])
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")]]
            if users[id].ref_of != '':
                sum = (float(users[id].dogs_to_sell) * 0.2) * 0.1
                current_price = "{:.4f}".format(1 / float(bot_values['DOGS'])).rstrip('0').rstrip('.')
                sum = sum / float(current_price)
                users[users[id].ref_of].balance += sum
                users[users[id].ref_of].balance = float("{:.4f}".format(
                    users[users[id].ref_of].balance).rstrip('0').rstrip('.'))
            users[id].dogs_to_sell = 0
            users[id].rand_num = 0

            await context.bot.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard),
                                                        message_id=query.message.message_id,
                                                        chat_id=query.message.chat.id)


        elif 'decline' in query.data and 'balance' not in query.data:
            id = int(query.data.split('|', maxsplit=1)[1])
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")], [
                InlineKeyboardButton("Одобрить платеж", callback_data=f'confirm_payment|{id}')]]

            await context.bot.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard),
                                                        message_id=query.message.message_id,
                                                        chat_id=query.message.chat.id)

        elif 'confirm_balance' in query.data:
            id = int(query.data.split('|', maxsplit=1)[1])
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")],
                        [InlineKeyboardButton("✅", callback_data=f'balance_confirm|{id}'),
                         InlineKeyboardButton("❌", callback_data=f'balance_decline|{id}')]]
            await context.bot.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard),
                                                        message_id=query.message.message_id,
                                                        chat_id=query.message.chat.id)
        elif 'balance_confirm' in query.data:
            id = int(query.data.split('|', maxsplit=1)[1])
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")]]
            await context.bot.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard),
                                                        message_id=query.message.message_id,
                                                        chat_id=query.message.chat.id)
        elif 'balance_decline' in query.data:
            id = int(query.data.split('|', maxsplit=1)[1])
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")], [
                InlineKeyboardButton("Одобрить платеж", callback_data=f'confirm_payment|{id}')]]

            await context.bot.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard),
                                                        message_id=query.message.message_id,
                                                        chat_id=query.message.chat.id)

        elif 'yes to first' in query.data:
            id = int(query.data.split('|', maxsplit=1)[1])
            users[id].balance += 1
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")],
                        [InlineKeyboardButton("Одобрено ✅", callback_data=' ')]]
            await context.bot.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard),
                                                        message_id=query.message.message_id,
                                                        chat_id=query.message.chat.id)
        elif 'no to first' in query.data:
            id = int(query.data.split('|', maxsplit=1)[1])
            users[id].first_review = False
            keyboard = [[InlineKeyboardButton("Типа тип", url=f"tg://user?id={id}")],
                        [InlineKeyboardButton("Не одобрено ❌", callback_data=' ')]]
            await context.bot.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard),
                                                        message_id=query.message.message_id,
                                                        chat_id=query.message.chat.id)



    else:
        if users[query.from_user.id].current_state == 'send_screen':
            if not update.message.document or not update.message.video or not update.message.photo:
                keyboard = []
                admins = load_file('admins.json')

                for i in admins:
                    try:
                        keyboard.append([InlineKeyboardButton(f"Связаться с менеджером {admins.index(i) + 1}",
                                                              url=f"tg://user?id={i}")])
                    except Exception as e:
                        print(e)
                await context.bot.send_message(update.effective_chat.id,
                                               text='Предоставьте сначала скриншот\\запись перевода DOGS. Если потеряли наличие доказательств перевода, свяжитесь с менеджером.',
                                               reply_markup=InlineKeyboardMarkup(keyboard))
                return 0

        if query.data == 'help of manager':
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data='cancel')]])
            await context.bot.send_message(chat_id=query.from_user.id,
                                           text='Опишите, пожалуйста, суть проблемы вкратце, чтобы наша команда команда помогла вам её решить',
                                           reply_markup=keyboard)
            users[query.from_user.id].current_state = 'help of manager'


        elif query.data == 'cancel_to_start':
            await context.bot.edit_message_reply_markup(chat_id=query.from_user.id, message_id=query.message.message_id,
                                                        reply_markup=None)
            users[query.from_user.id].current_state = 'canceled'
            keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                        [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                        [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]
            await context.bot.send_message(update.effective_chat.id,
                                           text=f"Привет. Вы попали в обменник валюты \"DOGS\". Наша команда занимается помощью в продаже вашей валюты. В меню выберите услугу, которая вас интересует. \n\nОтзывы: [тут]({bot_values['link_for_reviews']})",
                                           reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                            one_time_keyboard=True),
                                           parse_mode=ParseMode.MARKDOWN)
        elif query.data == 'cancel first':
            if not users[update.effective_chat.id].first_review:
                users[update.effective_chat.id].first_review = True
            await context.bot.edit_message_reply_markup(chat_id=query.from_user.id, message_id=query.message.message_id,
                                                        reply_markup=None)
            users[query.from_user.id].current_state = 'canceled'
            keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                        [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                        [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]
            await context.bot.send_message(update.effective_chat.id,
                                           text=f"Привет. Вы попали в обменник валюты \"DOGS\". Наша команда занимается помощью в продаже вашей валюты. В меню выберите услугу, которая вас интересует. \n\nОтзывы: [тут]({bot_values['link_for_reviews']})",
                                           reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                            one_time_keyboard=True),
                                           parse_mode=ParseMode.MARKDOWN)


        elif query.data == 'cancel':
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Помощь менеджера', callback_data='help of manager')],
                 [InlineKeyboardButton('Перейти к началу', callback_data='go to begin')]]))
            users[query.from_user.id].current_state = 'confirmed_dogs'
        elif query.data == 'go to begin':
            users[update.effective_chat.id].current_state = 'started'
            keyboard = [[KeyboardButton("Продать DOGS"), KeyboardButton("Купить TON")],
                        [KeyboardButton("Помощь менеджера"), KeyboardButton("Оставить отзыв")],
                        [KeyboardButton("Подключить рефералов"), KeyboardButton("Мой Баланс")]]
            await context.bot.send_message(update.effective_chat.id,
                                           text=f"Привет. Вы попали в обменник валюты \"DOGS\". Наша команда занимается помощью в продаже вашей валюты. В меню выберите услугу, которая вас интересует. \n\nОтзывы: [тут]({bot_values['link_for_reviews']})",
                                           reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                            one_time_keyboard=True),
                                           parse_mode=ParseMode.MARKDOWN)
        elif query.data == 'no comment':
            keyboard = [[InlineKeyboardButton("Перейти к началу", callback_data='go to begin')]]
            await context.bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id,
                                                        reply_markup=InlineKeyboardMarkup(keyboard))
            users[update.effective_chat.id].current_state = 'declined comment'


api_token = config.API_TOKEN
application = Application.builder().token(api_token).build()
application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
application.add_handler(CommandHandler("check", check, filters=filters.ChatType.PRIVATE))
application.add_handler(MessageHandler(filters.ChatType.PRIVATE, handle_private_messages))
application.add_handler(CallbackQueryHandler(handle_buttons))

application.run_polling()
