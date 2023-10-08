import discord
from discord.ui import Button, View
from discord.ext import commands
from discord import app_commands
import asyncio
from collections import defaultdict
import os
import requests
import json
import random


class quiz(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="quiz", description="Play a trivia quiz!")
    async def quiz(self, interaction: discord.Interaction):
        """Play a trivia quiz alone or with your friends!

        Args:
            ctx (commands.Context): _description_
        """
        result = (
            {}
        )  # q : view (containing dict with values and all final selections of users)

        questions = fetchQuestions(os.environ.get("TRIVIA_API"))
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
                if (
                    values[user] - 1 == correct_answer
                ):  # buttons 1-4 question indizes 0-3
                    scoreboard[user] += 1

        result_response = ">>> *Results!*\n"
        result_response += f"Total questions: {len(questions)}\n\n"
        for user, score in sorted(
            scoreboard.items(), key=lambda item: item[1], reverse=True
        ):
            result_response += f"{user}: {score}\n"

        await first_msg.edit(content=result_response)


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


def fetchQuestions(api_url):
    res = []
    response = requests.get(api_url)

    if response.status_code == 200:
        questions = json.loads(response.text)
        for idx, q in enumerate(questions):
            insert_pos = random.randint(0, 3)
            q["incorrectAnswers"].insert(insert_pos, q["correctAnswer"])
            res.append(
                {
                    "id": idx,
                    "question": q["question"]["text"],
                    "correct": insert_pos,
                    "answers": q["incorrectAnswers"],
                }
            )

    else:
        print("Failed to retrieve questions")

    return res


async def setup(client: commands.Bot) -> None:
    await client.add_cog(quiz(client))
