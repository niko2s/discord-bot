import discord
from discord.ext import commands
from discord import app_commands


# serves as example/template for cogs
class Hello(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="hello", description="Sends hello to user!")
    async def cog1(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello {interaction.user.name}")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Hello(client))
