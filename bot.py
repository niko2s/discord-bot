import discord
from discord.ext import commands
import logging
import os
import nest_asyncio
from datetime import datetime
from dotenv import load_dotenv, find_dotenv


class Client(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("."),
            intents=discord.Intents().all(),
        )

    async def setup_hook(self):
        for file_ in os.listdir("./cogs"):
            if file_.endswith(".py"):
                name = file_[:-3]
                await self.load_extension(f"cogs.{name}")

    async def on_ready(self):
        logging.info(f"Logged on as {self.user}!")

        nest_asyncio.apply()
        synced = await self.tree.sync()
        logging.info(f"Synced {len(synced)} command(s)")


load_dotenv(find_dotenv())

# create logs folder if does not exist
log_folder = 'logs'
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

#use timestamps so logs do not overwrite each other
now = datetime.now()
timestamp_str = now.strftime('%Y-%m-%d_%H-%M-%S')                             
handler = logging.FileHandler(filename=f"{log_folder}/discord_{timestamp_str}.log", encoding="utf-8", mode="w")

client = Client()
client.run(os.environ.get("DISCORD_TOKEN"), log_handler=handler)
