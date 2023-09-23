# This example requires the 'message_content' intent.

import discord
from discord.ui import Button, View
from discord.ext import commands
from discord import app_commands
import requests
import trivia
import time
import logging
import g4f
import os
import asyncio
import nest_asyncio
from collections import defaultdict
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
MAX_MESSAGE_LENGTH = 2000  # characters
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")


@bot.event
async def on_ready():
    print(f"Logged on as {bot.user}!")
    nest_asyncio.apply()

    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)")


class AnswerSelection(View):
    def __init__(self):
        super().__init__()
        self.values = {}  # user: selected

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def option1(self, interaction: discord.Interaction, button: Button):
        self.values[interaction.user.global_name] = 1
        print(self.values)
        await interaction.response.defer()

    @discord.ui.button(label="2", style=discord.ButtonStyle.green)
    async def option2(self, interaction: discord.Interaction, button: Button):
        self.values[interaction.user.global_name] = 2
        print(self.values)
        await interaction.response.defer()

    @discord.ui.button(label="3", style=discord.ButtonStyle.gray)
    async def option3(self, interaction: discord.Interaction, button: Button):
        self.values[interaction.user.global_name] = 3
        print(self.values)
        await interaction.response.defer()

    @discord.ui.button(label="4", style=discord.ButtonStyle.red)
    async def option4(self, interaction: discord.Interaction, button: Button):
        self.values[interaction.user.global_name] = 4
        print(self.values)
        await interaction.response.defer()


@bot.tree.command(name="ai")
@app_commands.describe(prompt="Enter a message")
async def ai(interaction: discord.Interaction, prompt: str):
    """Chat with AI

    Args:
        ctx (commands.Context): _description_
    """
    await interaction.response.defer(thinking=True)
    result = g4f.ChatCompletion.create(
        model="gpt-3.5-turbo",
        provider=g4f.Provider.DeepAi,
        messages=[{"role": "user", "content": os.environ.get("PRE_PROMPT") + prompt}],
    )

    msg = await interaction.original_response()

    for i in range(0, len(result), MAX_MESSAGE_LENGTH):
        chunk = result[i : i + MAX_MESSAGE_LENGTH]
        if i == 0:
            await msg.edit(content=chunk)
        else:
            await interaction.channel.send(content=chunk)


@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello {interaction.user.name}")


@bot.tree.command(name="say")
@app_commands.describe(thing_to_say="What should I say?")
async def say(interaction: discord.Interaction, thing_to_say: str):
    await interaction.response.defer()
    await asyncio.sleep(3)
    msg = await interaction.original_response()
    await msg.edit(content=thing_to_say)
    await interaction.channel.send("Hello")


@bot.tree.command(name="word")
@app_commands.describe(search="What word should I look up?")
async def word(interaction: discord.Interaction, search: str):
    api = os.getenv("DICTIONARY_API")

    response = requests.get(api + search)
    print(response.status_code)
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
            color=discord.Color.from_str("0x00CC00")
        )

        for phonetic in phonetics:
            audio = phonetic.get("audio", "")
            if audio:
                embed.add_field(name="Audio", value=audio, inline=True)

        meanings = data.get("meanings", [])
        for meaning in meanings:
            partOfSpeech = meaning.get("partOfSpeech")
            definitions = meaning.get("definitions", [{}])
            definitions_string = ""
            for i in range(min(3, len(definitions))):
                definitions_string += f'\u2022 {definitions[i]["definition"]} \n'

            embed.add_field(
                name=f"{partOfSpeech}",
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
        await interaction.response.send_message(f"Could not find the word `{search}`")
    else:
        #add error logging
        await interaction.response.send_message("An error occured. Try again later.")


@bot.tree.command(name="quiz")
async def quiz(interaction: discord.Interaction):
    """Play a trivia quiz alone or with your friends!

    Args:
        ctx (commands.Context): _description_
    """
    result = (
        {}
    )  # q : view (containing dict with values and all final selections of users)

    questions = trivia.fetchQuestions(os.environ.get("TRIVIA_API"))
    await interaction.response.send_message("Quiz starting!")
    first_msg = await interaction.original_response()

    await asyncio.sleep(3)
    time_between_questions = 10
    for q in questions:
        questionWithAnswers = ">>> "

        questionWithAnswers += f'**{q["question"]}**\n'

        for idx, a in enumerate(q["answers"], 1):
            questionWithAnswers += f"{idx}. {a}\n"

        questionWithAnswers += ""

        view = AnswerSelection()
        result[q["id"]] = view

        await interaction.channel.send(
            questionWithAnswers, view=view, delete_after=time_between_questions
        )
        await asyncio.sleep(time_between_questions)

    scoreboard = defaultdict(int)
    for r in result:
        correct_answer = questions[r]["correct"]
        values = result[r].values
        for user in values:
            if values[user] - 1 == correct_answer:  # buttons 1-4 question indizes 0-3
                scoreboard[user] += 1

    result_response = ">>> *Results!*\n"
    result_response += f"Total questions: {len(questions)}\n\n"
    for user, score in sorted(
        scoreboard.items(), key=lambda item: item[1], reverse=True
    ):
        result_response += f"{user}: {score}\n"

    await first_msg.edit(content=result_response)


bot.run(os.environ.get("DISCORD_TOKEN"), log_handler=handler)
