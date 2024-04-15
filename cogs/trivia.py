import asyncio
from collections import defaultdict
import os
import json
import random
import discord
from discord.ext import commands
from discord import app_commands
import requests
from cogs.view.answer import AnswerSelection


class Quiz(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="quiz", description="Play a trivia quiz!")
    async def quiz(self, interaction: discord.Interaction):
        """Play a trivia quiz alone or with your friends!"""
        result = (
            {}
        )  # q : view (containing dict with values and all final selections of users)

        questions = fetch_questions(os.environ.get("TRIVIA_API"))
        await interaction.response.send_message("Quiz starting!")
        first_msg = await interaction.original_response()

        await asyncio.sleep(3)
        time_between_questions = 10
        for q in questions:
            question_with_answers = ">>> "

            question_with_answers += f'**{q["question"]}**\n'

            for idx, a in enumerate(q["answers"], 1):
                question_with_answers += f"{idx}. {a}\n"

            question_with_answers += ""

            view = AnswerSelection()
            result[q["id"]] = view

            await interaction.channel.send(
                question_with_answers, view=view, delete_after=time_between_questions
            )
            await asyncio.sleep(time_between_questions)

        scoreboard = defaultdict(int)
        for r in result: # pylint: disable=consider-using-dict-items
            correct_answer = questions[r]["correct"]
            for user, user_value in result[r].items():
                if user_value - 1 == correct_answer:  # buttons 1-4 question indices 0-3
                    scoreboard[user] += 1

        result_response = ">>> *Results!*\n"
        result_response += f"Total questions: {len(questions)}\n\n"
        for user, score in sorted(
            scoreboard.items(), key=lambda item: item[1], reverse=True
        ):
            result_response += f"{user}: {score}\n"

        await first_msg.edit(content=result_response)


def fetch_questions(api_url):
    res = []
    response = requests.get(api_url, timeout=10)

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

    return res


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Quiz(client))
