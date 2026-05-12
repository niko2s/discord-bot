import asyncio
from collections import defaultdict
import json
import random
import html
import logging
from typing import Dict, Optional
from urllib.parse import urlencode
import requests
import discord
from discord.ext import commands
from discord import app_commands
from cogs.view.answer import AnswerSelection


TRIVIA_TDB_API = "https://opentdb.com/api.php"
TRIVIA_TDB_CATEGORIES_API = "https://opentdb.com/api_category.php"


def fetch_categories() -> Dict[str, int]:
    res: Dict[str, int] = {}
    response = requests.get(TRIVIA_TDB_CATEGORIES_API, timeout=10)

    if response.status_code == 200:
        data = json.loads(response.text)
        trivia_categories = data["trivia_categories"]

        for category in trivia_categories:
            res[category["name"]] = category["id"]

        return res
    else:
        logging.error("Failed to fetch trivia categories")
        return {}


class TriviaQuiz(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client
        self.categories: Dict[str, int] = {}

    async def cog_load(self) -> None:
        # Fetch off the event loop so a slow/down API can't block bot startup.
        self.categories = await asyncio.to_thread(fetch_categories)

    async def _category_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        current_lower = current.lower()
        matches = [
            app_commands.Choice(name=name, value=cat_id)
            for name, cat_id in self.categories.items()
            if current_lower in name.lower()
        ]
        return matches[:25]

    @app_commands.command(name="triviaquiz", description="Play a trivia quiz!")
    @app_commands.describe(amount="How many questions? (max 10)")
    @app_commands.autocomplete(category=_category_autocomplete)
    @app_commands.choices(
        difficulty=[
            app_commands.Choice(name=s, value=s.lower())
            for s in ["Easy", "Medium", "Hard"]
        ]
    )
    @app_commands.choices(
        choice_type=[
            app_commands.Choice(name="Multiple choice", value="multiple"),
            app_commands.Choice(name="True / False", value="boolean"),
        ]
    )
    async def triviaquiz(
        self,
        interaction: discord.Interaction,
        amount: int,
        category: Optional[int] = None,
        difficulty: Optional[app_commands.Choice[str]] = None,
        choice_type: Optional[app_commands.Choice[str]] = None,
    ):
        """Play a trivia quiz alone or with your friends!"""
        result = (
            {}
        )  # q : view (containing dict with values and all final selections of users)

        params = {
            "amount": min(amount, 10),  # max 10 questions
            "category": category,
            "difficulty": difficulty.value if difficulty else None,
            "type": choice_type.value if choice_type else None,
        }
        url = f"{TRIVIA_TDB_API}?{urlencode({k: v for k, v in params.items() if v is not None})}"

        questions = fetch_questions(url)

        category_name = next(
            (n for n, cid in self.categories.items() if cid == category), None
        )
        selected_options_list = []
        for k, v in params.items():
            if k == "category" and category is not None:
                selected_options_list.append(
                    f"{k}: **{category_name or category}**"
                )
            else:
                selected_options_list.append(
                    f'{k}: **{v if v is not None else "default"}**'
                )

        selected_options = "\n".join(selected_options_list)

        embed = discord.Embed(title="Quiz starting", color=discord.Color.random())
        embed.add_field(name="Settings", value=selected_options, inline=False)

        await interaction.response.send_message(embed=embed)

        await asyncio.sleep(3)

        # time in seconds
        time_between_questions = 10
        time_to_next_question = 3

        amount_questions = len(questions)
        for idx, q in enumerate(questions, 1):
            is_boolean = len(q["answers"]) == 2
            question_embed_title = f"{idx}/{amount_questions} **{q['question']}**"
            question_embed_footer = f"{q['category']}, {q['difficulty']}"

            question_embed = discord.Embed(
                title=question_embed_title, color=discord.Color.from_rgb(255, 255, 255)
            )

            question_embed.set_footer(text=question_embed_footer)

            possible_answers = ""
            if not is_boolean:
                for idx_a, a in enumerate(q["answers"], 1):
                    possible_answers += f"{idx_a}. {a}\n"
                question_embed.add_field(name="Answers", value=possible_answers)

            view = AnswerSelection(boolean=is_boolean)
            result[q["id"]] = view

            sent_question: discord.Message = await interaction.channel.send(
                embed=question_embed, view=view
            )
            timer: discord.Message = await interaction.channel.send("Timer starting!")

            for remaining in range(time_between_questions, -1, -1):
                await timer.edit(content=f"Time remaining: {remaining}")
                await asyncio.sleep(1)

            result_embed = discord.Embed(
                title=question_embed_title, color=discord.Color.from_rgb(0, 163, 108)
            )

            correct_value = q["answers"][q["correct"]]
            if is_boolean:
                correct_display = correct_value
            else:
                result_embed.add_field(name="Answers", value=possible_answers)
                correct_display = f"{q['correct'] + 1}. {correct_value}"
            result_embed.add_field(
                name="Correct",
                value=correct_display,
                inline=False,
            )
            if view.values:
                votes_lines = []
                for user, choice in view.values.items():
                    if 1 <= choice <= len(q["answers"]):
                        voted = q["answers"][choice - 1]
                    else:
                        voted = "?"
                    votes_lines.append(f"{user}: {voted}")
                result_embed.add_field(
                    name="Votes", value="\n".join(votes_lines), inline=False
                )
            result_embed.set_footer(text=question_embed_footer)

            await sent_question.edit(embed=result_embed, view=None)

            next_action_msg = "Next question" if idx != len(questions) else "Results"
            for remaining in range(time_to_next_question, -1, -1):
                await timer.edit(content=f"{next_action_msg} in: {remaining}")
                await asyncio.sleep(1)

            await interaction.channel.delete_messages([sent_question, timer])

        # count correct answers for scoreboard; seed every participant at 0
        scoreboard = defaultdict(int)
        for r in result:  # pylint: disable=consider-using-dict-items
            correct_answer = questions[r]["correct"]
            for user, user_value in result[r].values.items():
                scoreboard.setdefault(user, 0)
                if user_value - 1 == correct_answer:  # buttons 1-4 question indices 0-3
                    scoreboard[user] += 1

        # edit first embed to show scoreboard
        result_response = f"Total questions: {len(questions)}\n\n"
        sorted_scores = sorted(
            scoreboard.items(), key=lambda item: item[1], reverse=True
        )
        top_score = sorted_scores[0][1] if sorted_scores else 0
        for user, score in sorted_scores:
            crown = ":crown: " if score == top_score and score > 0 else ""
            result_response += f"{crown}{user}: {score}\n"

        embed.title = "Quiz finished"
        embed.add_field(name="Results", value=result_response)

        await interaction.edit_original_response(embed=embed)


def fetch_questions(api_url):
    res = []
    response = requests.get(api_url, timeout=10)

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
