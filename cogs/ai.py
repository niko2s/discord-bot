import discord
from discord.ext import commands
from discord import app_commands
import g4f
import os

MAX_MESSAGE_LENGTH = 2000  # characters


class ai(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="ai", description="Chat with AI!")
    @app_commands.describe(prompt="Enter a message")
    async def ai(self, interaction: discord.Interaction, prompt: str):
        """Chat with AI"""
        await interaction.response.defer(thinking=True)
        result = g4f.ChatCompletion.create(
            model="gpt-3.5-turbo",
            provider=g4f.Provider.GptGo,
            messages=[
                {"role": "user", "content": os.environ.get("PRE_PROMPT") + prompt}
            ],
        )

        follow_up: discord.Webhook = interaction.followup

        result = f"{interaction.user.mention}: `{prompt}`\n---------------------------------\n" + result

        for i in range(0, len(result), MAX_MESSAGE_LENGTH):
            chunk = result[i: i + MAX_MESSAGE_LENGTH]
            await follow_up.send(content=chunk)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ai(client))
