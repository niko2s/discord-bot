import discord
from discord.ext import commands
from discord import app_commands
import os
import requests


# serves as example/template for cogs
class urban(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="urban", description="Look up a word!")
    @app_commands.describe(search="What word should I look up?")
    async def urban(self, interaction: discord.Interaction, search: str = None):
        url = os.getenv("URBAN_URL")

        querystring = None

        # if no word was given, look up random word
        if search:
            url += "define"
            querystring = {"term": search}
        else:
            url += "random"

        headers = {
            "X-RapidAPI-Key": os.getenv("URBAN_KEY"),
            "X-RapidAPI-Host": os.getenv("URBAN_HOST"),
        }

        response = requests.get(url, headers=headers, params=querystring)

        if response.status_code == 200:
            data = response.json()
            results = data["list"]

            result = results[0]

            title = result["word"]
            if search is None:
                title = "Random word: " + title
            description = result["definition"]
            example = result["example"]
            thumbs_up = result["thumbs_up"]
            thumbs_down = result["thumbs_down"]
            permalink = result["permalink"]

            embed = discord.Embed(
                title=f"{title}",
                description=description,
                color=discord.Color.from_str("0xDD0000"),
            )

            embed.add_field(name="Example", value=example, inline=False)
            embed.add_field(name=":thumbsup:", value=thumbs_up)
            embed.add_field(name=":thumbsdown:", value=thumbs_down)

            embed.set_footer(text=permalink)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                "Error happened! Status code" + response.status_code
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(urban(client))
