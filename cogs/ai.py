import os
import discord
from discord.ext import commands
from discord import app_commands
import openai
from openai import AsyncOpenAI
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
        self.ai_client = AsyncOpenAI() if os.environ.get("OPENAI_API_KEY") else None
        self.ai_model = "gemini-pro"
        self.img_model = "sdxl"

    @app_commands.command(name="ai", description="Chat with AI!")
    @app_commands.describe(prompt="Enter a message")
    async def ai(self, interaction: discord.Interaction, prompt: str):
        """Chat with AI"""
        if self.ai_client is None:
            await interaction.response.send_message(
                "AI commands are unavailable because OPENAI_API_KEY is not configured.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        quote = f"{interaction.user.mention}: `{prompt}`"

        try:
            result = await self.ai_client.chat.completions.create(
                model=self.ai_model, messages=[{"role": "user", "content": prompt}]
            )

            follow_up: discord.Webhook = interaction.followup
            content = result.choices[0].message.content or "The model returned no text."
            result_text = f"{quote}{BREAK_LINE}{content}"

            for i in range(0, len(result_text), MAX_MESSAGE_LENGTH):
                chunk = result_text[i : i + MAX_MESSAGE_LENGTH]
                await follow_up.send(content=chunk)

        except openai.PermissionDeniedError as e:
            await interaction.followup.send(
                f"{quote}{BREAK_LINE}Permission denied. {api_error_message(e)}"
            )

        except openai.APIError as e:
            await interaction.followup.send(
                content=f"{quote}{BREAK_LINE}API Error. {api_error_message(e)}"
            )

    @app_commands.command(name="img", description="Image with AI!")
    @app_commands.describe(prompt="Enter a prompt")
    async def img(self, interaction: discord.Interaction, prompt: str):
        """Chat with AI"""
        if self.ai_client is None:
            await interaction.response.send_message(
                "AI commands are unavailable because OPENAI_API_KEY is not configured.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        quote = f"{interaction.user.mention}: `{prompt}`"

        try:
            response = await self.ai_client.images.generate(
                model=self.img_model,
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url
            image_data = await download.download_file(image_url) if image_url else None
            if image_data is None:
                await interaction.followup.send(
                    f"{quote}{BREAK_LINE}The generated image could not be downloaded."
                )
                return
            await interaction.followup.send(
                content=f"{quote}", file=discord.File(image_data, "ai_image.png")
            )

        except openai.PermissionDeniedError as e:
            await interaction.followup.send(
                content=f"{quote}{BREAK_LINE}Permission denied. {api_error_message(e)}"
            )

        except openai.APIError as e:
            await interaction.followup.send(
                content=f"{quote}{BREAK_LINE}API Error. {api_error_message(e)}"
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


def api_error_message(error: openai.APIError) -> str:
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        error_type = body.get("type")
        message = body.get("message")
        if error_type and message:
            return f"{error_type} - {message}"
        if message:
            return str(message)
    return str(error)
