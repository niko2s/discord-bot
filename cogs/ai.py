import discord
from discord.ext import commands
from discord import app_commands
import g4f
from g4f.client import Client
import os

MAX_MESSAGE_LENGTH = 2000  # characters


class ai(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.gpt = Client() 


    @app_commands.command(name="ai", description="Chat with AI!")
    @app_commands.describe(prompt="Enter a message")
    async def ai(self, interaction: discord.Interaction, prompt: str):
        """Chat with AI"""
        await interaction.response.defer(thinking=True)
        result = self.gpt.chat.completions.create(
            provider=g4f.Provider.Bing,
            model="gpt-4",
            messages=[
                {"role": "user", "content": os.environ.get("PRE_PROMPT") + prompt}
            ]
        )

        follow_up: discord.Webhook = interaction.followup

        result = f"{interaction.user.mention}: `{prompt}`\n---------------------------------\n" + result.choices[0].message.content

        for i in range(0, len(result), MAX_MESSAGE_LENGTH):
            chunk = result[i: i + MAX_MESSAGE_LENGTH]
            await follow_up.send(content=chunk)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ai(client))
