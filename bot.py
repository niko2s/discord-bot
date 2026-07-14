"""
This module defines the Client class for the Discord bot.
It extends the commands.Bot class from discord.py, loads commands from cogs and logs in as the bot.
And provides an entry point to start the bot.
"""

import logging
import os
from pathlib import Path
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv


class Client(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("."),
            intents=discord.Intents.default(),
        )

    async def setup_hook(self):
        cogs_dir = Path(__file__).parent / "cogs"
        for file_ in os.listdir(cogs_dir):
            if file_.endswith(".py"):
                name = file_[:-3]
                await self.load_extension(f"cogs.{name}")

        synced = await self.tree.sync()
        logging.info("Synced %s command(s) globally", len(synced))

    async def on_ready(self):
        logging.info("Logged on as %s!", self.user)


if __name__ == "__main__":
    from secrets_loader import load_secret_from_aws

    # AWS Secrets Manager (production) takes precedence; .env fills any gaps for local dev.
    load_secret_from_aws()
    load_dotenv(find_dotenv(), override=False)

    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN is not set. Aborting.")

    client = Client()
    client.run(token, root_logger=True)
