"""
This module defines the Client class for the Discord bot.
It extends the commands.Bot class from discord.py, loads commands from cogs and logs in as the bot.
And provides an entry point to start the bot.
"""

import logging
import os
import discord
from discord.ext import commands
import nest_asyncio
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
        logging.info("Logged on as %s!", self.user)

        nest_asyncio.apply()
        synced = await self.tree.sync()
        logging.info("Synced %s command(s)", len(synced))

if __name__ == "__main__":
    load_dotenv(find_dotenv(), override=True)

    client = Client()
    client.run(os.environ.get("DISCORD_TOKEN"), root_logger=True)
