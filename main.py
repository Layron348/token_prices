import json, asyncio, os, httpx
from aiogram import Bot, Dispatcher, executor, types
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from fuzzywuzzy import fuzz, process

TOKEN = "None"
FILE_NAME = "index.json"
USER_CHAT_ID = None

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump({"tokens": []}, f, indent=4, ensure_ascii=False)

print("Current working directory:", os.getcwd())
print("index.json path:", os.path.abspath("index.json"))


bot = Bot(TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()


async def get_price(symbol: str):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

        if "lastPrice" not in data:
            raise ValueError("Invalid token")

        price = float(data["lastPrice"])
        percent = float(data["priceChangePercent"])
        return price, percent
    
async def check_matches(token: str):
    url = "https://api.binance.com/api/v3/exchangeInfo"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

        pairs = {
            item["baseAsset"]
            for item in data["symbols"]
            if item["symbol"].endswith("USDT")
        }
        
        if token not in pairs:
            return f"{token.upper()} not found\nCheck token ticker and try again"
    return token

        

def load_data():
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_tokens():
    return load_data().get("tokens", [])


def add_token(token: str):
    token = token.upper() 
    data = load_data()
    tokens = data.get("tokens", [])

    if token not in tokens:
        tokens.append(token)
        data["tokens"] = tokens
        save_data(data)
        return True
    return False


def remove_token(token: str):
    token = token.upper() 
    data = load_data()
    tokens = data.get("tokens", [])

    if token in tokens:
        tokens.remove(token)
        data["tokens"] = tokens
        save_data(data)
        return True
    return False

async def token_list():

    tokens = get_tokens()

    if not tokens:
        return ("Your list is empty.")
    
    text = "Your tokens:\n"
    
    for token in tokens:
        try:
            price, percentage = await get_price(token)
            text += f"- {token}: {price} ({percentage}%)\n"
        except:
            text += f"- {token}: invalid or not found on Binance\n"

    await bot.send_message(USER_CHAT_ID, text)

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    text = (
        "Available commands:\n\n"
        "/add <token> — Add a token (SOL or SOLUSDT).\n"
        "/remove <token> — Remove a token.\n"
        "/check <token> — Check token price.\n"
        "/list — Show all saved tokens.\n"
        "/set_time HH:MM — Set daily time to receive your token list."
    )
    await message.answer(text)

@dp.message_handler(commands=["add"])
async def cmd_add(message: types.Message):
    token = message.text.replace("/add", "").strip().upper()

    if token == "":
        return await message.answer("Error: Token name is empty.")
    
    result = await check_matches(token)

    if isinstance(result, str) and "not found" in result:
        return await message.answer(result)

    token = token + "USDT"

    if add_token(token):
        await message.answer(f"Token {token} added.")
    else:
        await message.answer("Token already exists.")


@dp.message_handler(commands=["remove"])
async def cmd_remove(message: types.Message):
    token = message.text.replace("/remove", "").strip().upper()

    if token == "":
        return await message.answer("Write token to delete.")

    if not token.endswith("USDT"):
        token = token + "USDT"

    if remove_token(token):
        await message.answer(f"Token {token} deleted.")
    else:
        await message.answer("Token is not in your list.")


@dp.message_handler(commands=["list"])
async def cmd_list(message: types.Message):
    text = await token_list()
    await message.answer(text)



@dp.message_handler(commands=["check"])
async def cmd_check(message: types.Message):
    token = message.text.replace("/check", "").strip().upper()

    try:
        if token == "":
            return await message.answer("Error: empty token.")
        
        result = await check_matches(token)

        if isinstance(result, str) and "not found" in result:
            return await message.answer(result)

        token = token + "USDT"

        price, percentage = await get_price(token)
        return await message.answer(f"{token}: {price} ({percentage}%)")

    except:
        return await message.answer("Error. Make sure the token format is correct.")
    
@dp.message_handler(commands=["set_time"])
async def cmd_timer(message: types.Message):
    timer = message.text.replace("/set_time", "").strip()

    if not timer:
        await message.answer("Enter time in format HH:MM")
        return
    try:
        hours, minutes = timer.split(":")
        hours = int(hours)
        minutes = int(minutes)
    except:
        await message.answer("Invalid format. Use HH:MM")
        return
    
    scheduler.add_job(token_list, "cron", hour=hours, minute=minutes)

    await message.answer(f"Timer set for {hours:02d}:{minutes:02d}")


ALLOWED_COMMANDS = {"start", "add", "delete", "list", "set_time"}

@dp.message_handler(lambda m: not (m.text.startswith("/") and m.text[1:].split()[0].lower() in ALLOWED_COMMANDS))
async def cmd_unknown(message: types.Message):
    await message.answer("Command isn't defined, use /start to see all commands")

async def on_startup(dp):
    scheduler.start()

if __name__ == "__main__":
    print("Bot is running...")
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

