import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI
from utils import download

MAX_MESSAGE_LENGTH = 2000  # characters


class ai(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.ai_client = OpenAI()


    @app_commands.command(name="ai", description="Chat with AI!")
    @app_commands.describe(prompt="Enter a message")
    async def ai(self, interaction: discord.Interaction, prompt: str):
        """Chat with AI"""
        await interaction.response.defer(thinking=True)
        result = self.ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        follow_up: discord.Webhook = interaction.followup

        result = f"{interaction.user.mention}: `{prompt}`\n---------------------------------\n" + result.choices[0].message.content

        for i in range(0, len(result), MAX_MESSAGE_LENGTH):
            chunk = result[i: i + MAX_MESSAGE_LENGTH]
            await follow_up.send(content=chunk)

    @app_commands.command(name="img", description="Image with AI!")
    @app_commands.describe(prompt="Enter a prompt")
    async def img(self, interaction: discord.Interaction, prompt: str):
        """Chat with AI"""
        await interaction.response.defer(thinking=True)
        response = self.ai_client.images.generate(
          model="sdxl",
          prompt=prompt,
          size="1024x1024",
          quality="standard",
          n=1,
        )


        image_data = await download.download_file(response.data[0].url)
        result = f"{interaction.user.mention}: `{prompt}`"
        await interaction.followup.send(content=result, file=discord.File(image_data, "ai_image.png"))


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ai(client))
