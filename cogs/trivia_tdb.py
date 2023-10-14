import html
import logging
from typing import List, Dict, Optional
from urllib.parse import urlencode
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from collections import defaultdict
import os
import requests
import json
import random
from cogs.view.answer import AnswerSelection


def fetch_categories() -> Dict[str, int]:
    res: Dict[str, int] = {}
    response = requests.get(os.environ.get("TRIVIA_TDB_CATEGORIES"))

    if response.status_code == 200:
        data = json.loads(response.text)
        trivia_categories = data["trivia_categories"]

        for category in trivia_categories:
            res[category["name"]] = category["id"]

        print(res)
        return res
    else:
        logging.error("Failed to fetch trivia categories")
        return {}


categories: Dict[str, int] = fetch_categories()


class TriviaQuiz(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="triviaquiz", description="Play a trivia quiz!")
    @app_commands.describe(amount="How many questions? (max 10)")
    @app_commands.choices(category=[app_commands.Choice(name=k, value=categories[k]) for k in categories.keys()])
    @app_commands.choices(difficulty=[app_commands.Choice(name=s, value=s.lower()) for s in ["Easy", "Medium", "Hard"]])
    @app_commands.choices(type=[app_commands.Choice(name="Multiple choice", value="multiple"),
                                app_commands.Choice(name="True / False", value="boolean")])
    async def triviaquiz(self,
                         interaction: discord.Interaction, amount: int,
                         category: Optional[app_commands.Choice[int]] = None,
                         difficulty: Optional[app_commands.Choice[str]] = None,
                         type: Optional[app_commands.Choice[str]] = None):
        """Play a trivia quiz alone or with your friends!
        """
        result = {}  # q : view (containing dict with values and all final selections of users)

        params = {
            'amount': min(amount, 10),  # max 10 questions
            'category': category.value if category else None,
            'difficulty': difficulty.value if difficulty else None,
            'type': type.value if type else None,
        }
        url = f"{os.environ.get('TRIVIA_TDB')}?{urlencode({k: v for k, v in params.items() if v is not None})}"

        questions = fetch_questions(url)

        selected_options_list = []
        for k, v in params.items():
            if k == 'category' and category:
                selected_options_list.append(f'{k}: **{category.name}**')
            else:
                selected_options_list.append(f'{k}: **{v if v is not None else "default"}**')

        selected_options = '\n'.join(selected_options_list)

        embed = discord.Embed(
            title="Quiz starting",
            color=discord.Color.random()
        )
        embed.add_field(name="Settings", value=selected_options, inline=False)

        await interaction.response.send_message(embed=embed)

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

            sent_question: discord.Message = await interaction.channel.send(
                question_with_answers, view=view
            )
            remaining_seconds = time_between_questions

            timer: discord.Message = await interaction.channel.send("Timer starting!")

            while remaining_seconds:
                await timer.edit(content=f"Time remaining: {remaining_seconds}")
                remaining_seconds -= 1
                await asyncio.sleep(1)

            await sent_question.edit(view=None)
            await timer.edit(content=f"Correct answer is: {q['correct']+1}")
            await asyncio.sleep(3)
            await interaction.channel.delete_messages([sent_question, timer])

        scoreboard = defaultdict(int)
        for r in result:
            correct_answer = questions[r]["correct"]
            values = result[r].values
            for user in values:
                if (
                        values[user] - 1 == correct_answer
                ):  # buttons 1-4 question indices 0-3
                    scoreboard[user] += 1

        result_response = f"Total questions: {len(questions)}\n\n:crown:"
        for user, score in sorted(
                scoreboard.items(), key=lambda item: item[1], reverse=True
        ):
            result_response += f"{user}: {score}\n"

        embed.add_field(name="Results", value=result_response)

        await interaction.edit_original_response(embed=embed)


def fetch_questions(api_url):
    res = []
    response = requests.get(api_url)

    if response.status_code == 200:
        data = json.loads(response.text)
        if data["response_code"] == 0:
            questions = data["results"]

            for idx, q in enumerate(questions):
                insert_pos = random.randint(0, 3)
                q["incorrect_answers"].insert(insert_pos, q["correct_answer"])
                res.append(
                    {
                        "id": idx,
                        "question": html.unescape(q["question"]),
                        "correct": insert_pos,
                        "answers": [html.unescape(s) for s in q["incorrect_answers"]],
                    }
                )

    else:
        print("Failed to retrieve questions")

    return res


async def setup(client: commands.Bot) -> None:
    await client.add_cog(TriviaQuiz(client))
