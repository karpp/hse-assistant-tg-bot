import database
import asyncio
import logging
import re
from random import randrange

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor, exceptions
from config import TOKEN

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('broadcast')


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply("Привет!\nЭто демоверсия, чтобы посмотреть доступные команды отправь /help ")


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await message.reply("В этом боте на данный момент ты можешь выполнить следующие команды:\n"
                        "/get_id - получить ID чата и пользователя\n"
                        "/sub CHAT_ID - оформить подписку на чат с указанным ID\n"
                        "/cancel_sub CHAT_ID - отменить подписку на чат с указанным ID\n"
                        "/info - показать количество отслеживаемых чатов")


@dp.message_handler(commands=['info'])
async def process_info_command(message: types.Message):
    await message.reply(f"Всего отслеживаемых чатов: "
                        f"{len(database.get_tg_subscriptions_by_user(message.from_user.id))}")


async def send_message(user_id: int, text: str, disable_notification: bool = False) -> bool:
    """
    Safe messages sender
    :param user_id:
    :param text:
    :param disable_notification:
    :return:
    """
    try:
        await bot.send_message(user_id, text, disable_notification=disable_notification)
    except exceptions.BotBlocked:
        log.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        log.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        log.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await send_message(user_id, text)  # Recursive call
    except exceptions.UserDeactivated:
        log.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        log.exception(f"Target [ID:{user_id}]: failed")
    else:
        log.info(f"Target [ID:{user_id}]: success")
        return True
    return False

# подписка на чат


@dp.message_handler(commands=['get_id'])
async def process_get_id_command(message: types.Message):
    await message.reply(f"ID чата: {message.chat.id}, USER_ID: {message.from_user.id}")


@dp.message_handler(commands=['sub'])
async def process_subscribe_command(message: types.Message):
    await message.reply(f"Для того, чтобы подписаться на обновления беседы, пригласите в нее бота, "
                        f"если он еще в ней не состоит. Далее сюда нужно будет прислать ID чата, "
                        f"который вы хотите отслеживать. "
                        f"Узнать его можно написав в нужной беседе команду /get_id ;)")
    input_id = re.split(' ', message.text, maxsplit=3)
    try:
        input_id = int(input_id[1])
    except ValueError:
        return await message.reply(f"Вы неверно ввели ID. Попробуйте еще раз :)")

    # check if suitable
    database.create_tg_subscription(message.from_user.id, input_id)
    await message.reply(f"Вы успешно подписались на чат со следующим ID: {input_id}")


@dp.message_handler(commands=['cancel_sub'])
async def process_cancel_subscription_command(message: types.Message):
    await message.reply(f"Для того, чтобы отписаться от обновлений чата, пришлите сюда ID чата "
                        f"за которым вы не хотите больше следить. "
                        f"Узнать его можно написав в нужной беседе команду /get_id ;)")
    input_id = re.split(' ', message.text, maxsplit=3)
    try:
        input_id = int(input_id[1])
    except ValueError:
        return await message.reply(f"Вы неверно ввели ID. Попробуйте еще раз :)")

    # check if suitable
    database.remove_tg_subscription(message.from_user.id, input_id)
    await message.reply(f"Вы успешно отписались от чата со следующим ID: {input_id}")


@dp.message_handler(lambda message: len(database.get_tg_subscriptions_by_chat(message.chat.id)))
async def process_forward_command(message: types.Message):
    subscriptions = database.get_tg_subscriptions_by_chat(message.chat.id)
    print(subscriptions)
    if randrange(10) % 3 == 0:
        for user in subscriptions:
            await send_message(user.user_id, message.text)


@dp.message_handler(commands=['try'])
async def process_spam_command(message: types.Message):
    await send_message(message.from_user.id, 'for testing')


if __name__ == '__main__':
    executor.start_polling(dp)
