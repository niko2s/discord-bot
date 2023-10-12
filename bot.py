import discord
from discord.ext import commands
import logging
import os
import nest_asyncio
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
import sys

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
                          
handler = logging.StreamHandler(sys.stdout)

client = Client()
client.run(os.environ.get("DISCORD_TOKEN"), log_handler=handler)
