import asyncio
import logging
import requests
import discord
from discord.ext import commands
from discord import app_commands
from utils import download


CAT_API = "https://api.thecatapi.com/v1/images/search"


class Cat(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="cat", description="Sends random cat picture!")
    async def cat(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            response = await asyncio.to_thread(requests.get, CAT_API, timeout=10)
            response.raise_for_status()
            image_url = response.json()[0]["url"]
            file_data = await download.download_file(image_url)
            if file_data is None:
                raise ValueError("cat image download failed")
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            logging.exception("Failed to retrieve cat picture")
            await interaction.followup.send("Failed to retrieve cat picture")
            return

        await interaction.followup.send(file=discord.File(file_data, "cat.jpg"))


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Cat(client))
