import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands
import requests


DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/"


# serves as example/template for cogs
class Dictionary(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="word", description="Look up a word!")
    @app_commands.describe(search="What word should I look up?")
    async def word(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer(thinking=True)
        try:
            response = await asyncio.to_thread(
                requests.get, DICTIONARY_API + search, timeout=10
            )
        except requests.RequestException:
            logging.exception("Dictionary request failed")
            await interaction.followup.send("An error occurred. Try again later.")
            return

        if response.status_code == 200:
            try:
                data = response.json()[0]
                if not isinstance(data, dict):
                    raise TypeError("dictionary entry is not an object")
            except (ValueError, IndexError, TypeError):
                logging.exception("Dictionary returned an invalid response")
                await interaction.followup.send("An error occurred. Try again later.")
                return

            title = str(data.get("word") or "")
            description = str(data.get("origin") or "")
            phonetics = data.get("phonetics", [])
            if phonetics:
                title = title + "   " + phonetics[0].get("text", "")

            embed = discord.Embed(
                title=f"{title}"[:256],
                description=description[:4096],
                color=discord.Color.from_str("0x00CC00"),
            )

            for phonetic in phonetics:
                if len(embed.fields) >= 25:
                    break
                audio = phonetic.get("audio", "")
                if audio:
                    embed.add_field(name="Audio", value=audio[:1024], inline=True)

            meanings = data.get("meanings", [])
            for meaning in meanings:
                if len(embed.fields) >= 25:
                    break
                part_of_speech = meaning.get("partOfSpeech")
                definitions = meaning.get("definitions", [{}])
                definitions_string = ""
                for i in range(min(3, len(definitions))):
                    definition = definitions[i].get("definition")
                    if definition:
                        definitions_string += f"\u2022 {definition} \n"

                if not definitions_string:
                    continue

                embed.add_field(
                    name=f"{part_of_speech}",
                    value=definitions_string[:1024],
                    inline=False,
                )

                synonyms = meaning.get("synonyms", [])
                if synonyms and len(embed.fields) < 25:
                    synonyms_v = ""
                    for i in range(min(2, len(synonyms))):
                        synonyms_v += synonyms[i] + "\n"
                    embed.add_field(name="Synonyms", value=synonyms_v, inline=False)

                antonyms = meaning.get("antonyms", [])
                if antonyms and len(embed.fields) < 25:
                    antonyms_v = ""
                    for i in range(min(2, len(antonyms))):
                        antonyms_v += antonyms[i] + "\n"
                    embed.add_field(name="Antonyms", value=antonyms_v, inline=False)

            await interaction.followup.send(embed=embed)
        elif response.status_code == 404:
            await interaction.followup.send(
                f"Could not find the word `{search}`"
            )
        else:
            logging.error("Dictionary returned status %s", response.status_code)
            await interaction.followup.send(
                "An error occurred. Try again later."
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Dictionary(client))
