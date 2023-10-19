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

        # time in seconds
        time_between_questions = 10
        time_to_next_question = 3

        amount_questions = len(questions)
        for idx, q in enumerate(questions, 1):
            question_embed_title = f"{idx}/{amount_questions} **{q['question']}**"
            question_embed_footer = f"{q['category']}, {q['difficulty']}"

            question_embed = discord.Embed(title=question_embed_title,
                                           color=discord.Color.from_rgb(255, 255, 255))

            question_embed.set_footer(text=question_embed_footer)

            possible_answers = ""

            for idx_a, a in enumerate(q["answers"], 1):
                possible_answers += f"{idx_a}. {a}\n"

            question_embed.add_field(name="Answers", value=possible_answers)

            view = AnswerSelection()
            result[q["id"]] = view

            sent_question: discord.Message = await interaction.channel.send(
                embed=question_embed, view=view
            )
            remaining_seconds = time_between_questions

            timer: discord.Message = await interaction.channel.send("Timer starting!")

            while remaining_seconds:
                await timer.edit(content=f"Time remaining: {remaining_seconds}")
                remaining_seconds -= 1
                await asyncio.sleep(1)

            result_embed = discord.Embed(title=question_embed_title,
                                         color=discord.Color.from_rgb(0, 163, 108))

            result_embed.add_field(name="Answers", value=possible_answers)
            result_embed.add_field(name="Correct",
                                   value=f"{q['correct'] + 1}. {q['answers'][q['correct']]}",
                                   inline=False)
            result_embed.set_footer(text=question_embed_footer)

            await sent_question.edit(embed=result_embed, view=None)

            remaining_seconds = time_to_next_question
            next_action_msg = "Next question" if idx != len(questions) else "Results"
            while remaining_seconds:
                await timer.edit(content=f"{next_action_msg} in: {remaining_seconds}")
                remaining_seconds -= 1
                await asyncio.sleep(1)

            await interaction.channel.delete_messages([sent_question, timer])

        # count correct answers for scoreboard
        scoreboard = defaultdict(int)
        for r in result:
            correct_answer = questions[r]["correct"]
            values = result[r].values
            for user in values:
                if values[user] - 1 == correct_answer:  # buttons 1-4 question indices 0-3
                    scoreboard[user] += 1

        # edit first embed to show scoreboard
        result_response = f"Total questions: {len(questions)}\n\n:crown:"
        for user, score in sorted(scoreboard.items(), key=lambda item: item[1], reverse=True):
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

                correct_answer = q["correct_answer"]
                incorrect_answers = q["incorrect_answers"]

                # boolean / multiple choice questions
                if len(incorrect_answers) == 1:
                    correct_pos = 0 if correct_answer == "True" else 1
                else:
                    correct_pos = random.randint(0, 3)

                incorrect_answers.insert(correct_pos, correct_answer)

                # TODO refactor this to class
                res.append(
                    {
                        "id": idx,
                        "category": q["category"],
                        "difficulty": q["difficulty"],
                        "question": html.unescape(q["question"]),
                        "correct": correct_pos,
                        "answers": [html.unescape(s) for s in incorrect_answers],
                    }
                )

    else:
        logging.error("Failed to retrieve questions")
    return res


async def setup(client: commands.Bot) -> None:
    await client.add_cog(TriviaQuiz(client))
