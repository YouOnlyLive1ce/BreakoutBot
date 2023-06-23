from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage

data = MemoryStorage()

class LogInStates(StatesGroup):
    api_key = State()
    secret_key = State()
    logged_in = State()

bot = Bot(token='6234279060:AAFx1KgWvVNg1prHpQfvlS203nZaOt4IH5U')
dp = Dispatcher(bot, storage=MemoryStorage())

## Keyboard
button_authorization = KeyboardButton('Log in 🤳')
button_client_work = KeyboardButton('Add an account to work 🚜')
button_statistics = KeyboardButton('Statistics 💻')

first_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(button_client_work).add(button_statistics)
first_kb_no_admins = ReplyKeyboardMarkup(resize_keyboard=True).add(button_authorization)

def get_debug_kb():

    button_back = KeyboardButton('Back 🔙')
    button_back_to_main = KeyboardButton('Back to main menu 🔙')

    debug_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(button_back).add(button_back_to_main)

    return debug_kb


## Admins
admins = [682751445, 1992272849]


@dp.message_handler(commands=['start'])
async def alarm(message: types.Message):
    if (message.from_user.id in admins):
        await message.answer(f"Greetings, {message.from_user.username}", reply_markup=first_kb)
    else:
        await message.answer(f"Greetings, {message.from_user.username}, log in!", reply_markup=first_kb_no_admins)



@dp.message_handler(state = LogInStates.api_key)
async def return_from_api_state(message: types.Message, state: FSMContext):
    if message.text == 'Back 🔙':
        await message.reply("Main menu", reply_markup=first_kb)
        await state.finish()

    elif message.text == 'Back to main menu 🔙':
        await message.reply("Main menu", reply_markup=first_kb)
        await state.finish()

    else:
        async with state.proxy() as data:
            data['api_key'] = message.text

        await message.reply("Enter SECRET_KEY which is tied to the work account:", reply_markup=get_debug_kb())
        await LogInStates.secret_key.set()


@dp.message_handler(state = LogInStates.secret_key)
async def return_from_secret_state(message: types.Message, state: FSMContext):
    if message.text == 'Back 🔙':
        await message.reply("Add account section.\n"
                        "\n"
                        "Enter API_KEY which is tied to the work account:", reply_markup=get_debug_kb())
        await LogInStates.api_key.set()

    elif message.text == 'Back to main menu 🔙':
        await message.reply("Main menu", reply_markup=first_kb)
        await state.finish()

    else:
        async with state.proxy() as data:
            data['secret_key'] = message.text

        await message.reply(f"Your API_KEY: {data['api_key']}\nYour SECRET_KEY: {data['secret_key']}", reply_markup=get_debug_kb())
        await LogInStates.logged_in.set()


@dp.message_handler(state = LogInStates.logged_in)
async def return_from_loggedin_state(message: types.Message, state: FSMContext):
    if message.text == 'Back 🔙':
        await message.reply("Enter SECRET_KEY which is tied to the work account:", reply_markup=get_debug_kb())
        await LogInStates.secret_key.set()

    elif message.text == 'Back to main menu 🔙':
        await message.reply("Main menu", reply_markup=first_kb)
        await state.finish()



@dp.message_handler(text=['Add an account to work 🚜'])
async def process_client_work_command(message: types.Message):
    await message.reply("Add account section.\n"
                        "\n"
                        "Enter API_KEY which is tied to the work account:", reply_markup=get_debug_kb())
    await LogInStates.api_key.set()




@dp.message_handler()
async def echo(message: types.Message):
    await message.answer("I don't understand you, try again", reply_markup=first_kb)


if __name__ == '__main__':
    executor.start_polling(dp)
