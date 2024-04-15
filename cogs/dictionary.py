import os
import discord
from discord.ext import commands
from discord import app_commands
import requests


# serves as example/template for cogs
class Dictionary(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="word", description="Look up a word!")
    @app_commands.describe(search="What word should I look up?")
    async def word(self, interaction: discord.Interaction, search: str):
        api = os.getenv("DICTIONARY_API")

        response = requests.get(api + search, timeout=10)
        if response.status_code == 200:
            data = response.json()[0]

            title = data.get("word", "")
            description = data.get("origin", "")
            phonetics = data.get("phonetics", [])
            if phonetics:
                title = title + "   " + phonetics[0].get("text", "")

            embed = discord.Embed(
                title=f"{title}",
                description=description,
                color=discord.Color.from_str("0x00CC00"),
            )

            for phonetic in phonetics:
                audio = phonetic.get("audio", "")
                if audio:
                    embed.add_field(name="Audio", value=audio, inline=True)

            meanings = data.get("meanings", [])
            for meaning in meanings:
                part_of_speech = meaning.get("partOfSpeech")
                definitions = meaning.get("definitions", [{}])
                definitions_string = ""
                for i in range(min(3, len(definitions))):
                    definitions_string += f'\u2022 {definitions[i]["definition"]} \n'

                embed.add_field(
                    name=f"{part_of_speech}",
                    value=f"{definitions_string}",
                    inline=False,
                )

                synonyms = meaning.get("synonyms", [])
                if synonyms:
                    synonyms_v = ""
                    for i in range(min(2, len(synonyms))):
                        synonyms_v += synonyms[i] + "\n"
                    embed.add_field(name="Synonyms", value=synonyms_v, inline=False)

                antonyms = meaning.get("antonyms", [])
                if antonyms:
                    antonyms_v = ""
                    for i in range(min(2, len(antonyms))):
                        antonyms_v += antonyms[i] + "\n"
                    embed.add_field(name="Antonyms", value=antonyms_v, inline=False)

            await interaction.response.send_message(embed=embed)
        elif response.status_code == 404:
            await interaction.response.send_message(
                f"Could not find the word `{search}`"
            )
        else:
            # add error logging
            await interaction.response.send_message(
                "An error occured. Try again later."
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Dictionary(client))
