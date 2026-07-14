import asyncio
import logging
import os
import discord
from discord.ext import commands
from discord import app_commands
import requests


URBAN_HOST = "urban-dictionary7.p.rapidapi.com"
URBAN_BASE_URL = f"https://{URBAN_HOST}/v0/"


# serves as example/template for cogs
class Urban(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="urban", description="Look up a word!")
    @app_commands.describe(search="What word should I look up?")
    async def urban(self, interaction: discord.Interaction, search: str = None):
        api_key = os.getenv("URBAN_KEY")
        if not api_key:
            await interaction.response.send_message(
                "Urban Dictionary is unavailable because URBAN_KEY is not configured.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        querystring = None

        # if no word was given, look up random word
        if search:
            url = URBAN_BASE_URL + "define"
            querystring = {"term": search}
        else:
            url = URBAN_BASE_URL + "random"

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": URBAN_HOST,
        }

        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers=headers,
                params=querystring,
                timeout=10,
            )
        except requests.RequestException:
            logging.exception("Urban Dictionary request failed")
            await interaction.followup.send("Urban Dictionary request failed.")
            return

        if response.status_code == 200:
            try:
                result = response.json()["list"][0]
                title = str(result["word"])
                description = str(result["definition"])
                example = str(result["example"])
                thumbs_up = result["thumbs_up"]
                thumbs_down = result["thumbs_down"]
                permalink = str(result["permalink"])
            except (ValueError, KeyError, IndexError, TypeError):
                await interaction.followup.send("No definition was found.")
                return

            if search is None:
                title = "Random word: " + title

            embed = discord.Embed(
                title=f"{title}"[:256],
                description=description[:4096],
                color=discord.Color.from_str("0xDD0000"),
            )

            embed.add_field(name="Example", value=example[:1024] or "-", inline=False)
            embed.add_field(name=":thumbsup:", value=thumbs_up)
            embed.add_field(name=":thumbsdown:", value=thumbs_down)

            embed.set_footer(text=permalink[:2048])

            await interaction.followup.send(embed=embed)
        else:
            logging.error("Urban Dictionary returned status %s", response.status_code)
            await interaction.followup.send(
                "Error happened! Status code: " + str(response.status_code)
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Urban(client))
