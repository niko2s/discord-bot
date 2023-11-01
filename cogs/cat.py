import discord
from discord.ext import commands
from discord import app_commands
from utils import download
import logging
import requests
import os


class Cat(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="cat", description="Sends random cat picture!")
    async def cat(self, interaction: discord.Interaction):
        response = requests.get(os.environ.get("CAT_API"))
        if response.status_code == 200:
            data = response.json()[0]
            file_data = await download.download_file(data["url"])
            await interaction.response.send_message(file=discord.File(file_data, "cat.jpg"))
        else:
            logging.error(f"Error at cat command. response status code: {response.status_code}")
            await interaction.response.send_message("Failed to retrieve cat picture")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Cat(client))
