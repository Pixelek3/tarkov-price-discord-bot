import discord
from discord.ext import commands
import os
import asyncio
import logging
import sys
from dotenv import load_dotenv

logger = logging.getLogger("TarkovBot")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a')
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

if logger.hasHandlers():
    logger.handlers.clear()

logger.addHandler(file_handler)
logger.addHandler(console_handler)


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class TarkovBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        extension_name = "market"
        try:
            await self.load_extension(extension_name)
            logger.info(f"Extension '{extension_name}' loaded successfully.")
        except commands.ExtensionNotFound:
            try:
                extension_name = "cogs.market"
                await self.load_extension(extension_name)
                logger.info(f"Extension '{extension_name}' loaded successfully.")
            except Exception as e:
                logger.critical(f"Could not load extension. Make sure 'market.py' exists! Error: {e}")
        except Exception as e:
            logger.exception(f"Error during setup_hook: {e}")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.change_presence(activity=discord.Game(name="Checking Flea prices"))

async def main():
    if not TOKEN:
        logger.critical("DISCORD_TOKEN not found in .env environment.")
        return
        
    bot = TarkovBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")