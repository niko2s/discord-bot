"""
This module defines the Client class for the Discord bot.
It extends the commands.Bot class from discord.py, loads commands from cogs and logs in as the bot.
And provides an entry point to start the bot.
"""

import logging
import os
import sys
import discord
from discord.ext import commands
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

        if os.environ.get("SYNC_COMMANDS") == "1":
            guild_id = os.environ.get("SYNC_GUILD_ID")
            if guild_id:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logging.info("Synced %s command(s) to guild %s", len(synced), guild_id)
            else:
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
