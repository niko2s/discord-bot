import discord
from discord.ext import commands
from discord import app_commands
import openai
from openai import OpenAI
from utils import download

MAX_MESSAGE_LENGTH = 2000  # characters
BREAK_LINE = "\n---------------------------------\n"
AI_MODELS = [
    "GPT-3.5-TURBO-0125",
    "GEMINI-PRO",
    "GEMINI-1.5-PRO-LATEST",
    "LLAMA-2-70B-CHAT",
    "MIXTRAL-8X22B-INSTRUCT",
    "CLAUDE-3-HAIKU-20240307"
]
IMG_MODELS = [
    "SDXL",
    "PLAYGROUND-V2.5",
    "KANDINSKY-3.1"
]


class Ai(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.ai_client = OpenAI()
        self.ai_model = "gemini-pro"
        self.img_model = "sdxl"

    @app_commands.command(name="ai", description="Chat with AI!")
    @app_commands.describe(prompt="Enter a message")
    async def ai(self, interaction: discord.Interaction, prompt: str):
        """Chat with AI"""
        await interaction.response.defer(thinking=True)
        quote = f"{interaction.user.mention}: `{prompt}`"

        try:
            result = self.ai_client.chat.completions.create(
                model=self.ai_model, messages=[{"role": "user", "content": prompt}]
            )

            follow_up: discord.Webhook = interaction.followup
            result = f"{quote}{BREAK_LINE}" + result.choices[0].message.content

            for i in range(0, len(result), MAX_MESSAGE_LENGTH):
                chunk = result[i : i + MAX_MESSAGE_LENGTH]
                await follow_up.send(content=chunk)

        except openai.PermissionDeniedError as e:
            await interaction.followup.send(
            f"{quote}{BREAK_LINE}Permission denied. Reason: "
            f"{e.body['type']} - {e.body['message']}"
        )

        except openai.APIError as e:
            await interaction.followup.send(
                content=(
                    f"{quote}{BREAK_LINE}API Error. "
                    f"{e.body['type']} - {e.body['message']}")
            )

    @app_commands.command(name="img", description="Image with AI!")
    @app_commands.describe(prompt="Enter a prompt")
    async def img(self, interaction: discord.Interaction, prompt: str):
        """Chat with AI"""
        await interaction.response.defer(thinking=True)
        quote = f"{interaction.user.mention}: `{prompt}`"

        try:
            response = self.ai_client.images.generate(
                model=self.img_model,
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n="1",
            )

            image_data = await download.download_file(response.data[0].url)
            await interaction.followup.send(
                content=f"{quote}", file=discord.File(image_data, "ai_image.png")
            )

        except openai.PermissionDeniedError as e:
            await interaction.followup.send(
                content=(
                f"{quote}{BREAK_LINE}Permission denied."
                f"Reason: {e.body['type']} - {e.body['message']}"
                )
            )

        except openai.APIError as e:
            await interaction.followup.send(
                content=f"{quote}{BREAK_LINE}API Error. {e.body['type']} - {e.body['message']}"
            )

    @app_commands.command(name="setai", description="Set the AI model!")
    @app_commands.choices(
        model_name=[app_commands.Choice(name=s, value=s.lower()) for s in AI_MODELS]
    )
    async def set_model(self, interaction: discord.Interaction, model_name: str):
        """Set the AI model"""
        await interaction.response.defer(thinking=True)
        self.ai_model = model_name
        await interaction.followup.send(
            content=f"AI model has been set to {model_name}"
        )

    @app_commands.command(name="setaiimg", description="Set the image model!")
    @app_commands.choices(
        model_name=[app_commands.Choice(name=s, value=s.lower()) for s in IMG_MODELS]
    )
    async def set_image_model(self, interaction: discord.Interaction, model_name: str):
        """Set the image model"""
        await interaction.response.defer(thinking=True)
        self.img_model = model_name
        await interaction.followup.send(content="Image parameters have been updated.")

    @app_commands.command(name="getai", description="Get the current AI settings!")
    async def get_settings(self, interaction: discord.Interaction):
        """Get the current settings"""
        await interaction.response.send_message(
            f"AI Model: {self.ai_model}\nImage Model: {self.img_model}"
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Ai(client))
