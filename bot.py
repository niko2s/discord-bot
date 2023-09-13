# This example requires the 'message_content' intent.

import discord
from discord.ui import Button, View
from discord.ext import commands
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
MAX_MESSAGE_LENGTH = 2000 #characters
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')


@bot.event
async def on_ready():
    print(f"Logged on as {bot.user}!")
    nest_asyncio.apply()

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


@bot.command()
async def ai(ctx: commands.Context, *args):
    """Chat with AI

    Args:
        ctx (commands.Context): _description_
    """
    await ctx.defer()
    result = g4f.ChatCompletion.create(
        model="gpt-3.5-turbo",
        provider=g4f.Provider.DeepAi,
        messages=[{"role": "user", "content": "".join(args)}],
    )
    
    for i in range(0, len(result), MAX_MESSAGE_LENGTH):
        chunk = result[i:i+MAX_MESSAGE_LENGTH]
        await ctx.send(chunk)
    
@bot.command()
async def quiz(ctx: commands.Context, *args):
    """Play a trivia quiz alone or with your friends!

    Args:
        ctx (commands.Context): _description_
    """
    result = (
        {}
    )  # q : view (containing dict with values and all final selections of users)

    questions = trivia.fetchQuestions(os.environ.get("TRIVIA_API"))
    await ctx.send("Quiz starting!")
    await asyncio.sleep(3)

    for q in questions:
        questionWithAnswers = ">>> "

        questionWithAnswers += f'**{q["question"]}**\n'

        for idx, a in enumerate(q["answers"], 1):
            questionWithAnswers += f"{idx}. {a}\n"

        questionWithAnswers += ""

        view = AnswerSelection()
        result[q["id"]] = view
        sent_msg = await ctx.send(questionWithAnswers, view=view)
        await asyncio.sleep(10)
        await sent_msg.delete()
    
    
    
    scoreboard = defaultdict(int)
    for r in result:
        correct_answer = questions[r]["correct"]
        values = result[r].values
        for user in values:
            if values[user]-1 == correct_answer: #buttons 1-4 question indizes 0-3
                scoreboard[user] += 1
        
        
    result_response = ">>> *Results!*\n"
    result_response += f'Total questions: {len(questions)}\n\n'
    for user,score in sorted(scoreboard.items(), key=lambda item: item[1], reverse=True):
        result_response += f"{user}: {score}\n"
    
    await ctx.send(result_response)
    
    


bot.run(os.environ.get("DISCORD_TOKEN"), log_handler=handler)
